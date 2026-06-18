#!/usr/bin/env python3
"""Replay verifier scaffold for B1/B7 cone_01 shared-theta objects.

This verifier checks that the shared-theta object proposals can be replayed
against the source QASM and the parameter-transfer angle groups.  It verifies
object coverage, line-number consistency, parsed RY(theta) values, and theta
group membership.  It does not verify a semantic rewrite and does not remove
any occurrence from the B7 ledger.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_shared_theta_replay_verifier_gate_v0"
STATUS = "cone01_shared_theta_replay_verifier_scaffold"
MODEL_STATUS = "shared_theta_replay_verified_without_semantic_rewrite"
VERSION = "0.1"
ANGLE_GROUP_TOLERANCE_DECIMALS = 12
RY_PATTERN = re.compile(r"^ry\((?P<theta>[^)]+)\)\s+q\[(?P<qubit>\d+)\];$")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def display_path(path: Path) -> str:
    root = Path(__file__).resolve().parents[1]
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(root))
    except ValueError:
        return str(path)


def canonical_angle(theta: float) -> float:
    value = (theta + math.pi) % (2.0 * math.pi) - math.pi
    return round(value, ANGLE_GROUP_TOLERANCE_DECIMALS)


def parse_angle(text: str) -> float:
    expr = text.strip()
    if "pi" not in expr:
        return float(expr)
    safe_expr = expr.replace("pi", f"({math.pi})")
    return float(eval(safe_expr, {"__builtins__": {}}, {}))


def parse_qasm_ry_lines(path: Path) -> dict[int, dict[str, Any]]:
    output: dict[int, dict[str, Any]] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = raw.strip()
        match = RY_PATTERN.match(text)
        if not match:
            continue
        theta = parse_angle(match.group("theta"))
        output[line_number] = {
            "line_number": line_number,
            "text": text,
            "theta": theta,
            "canonical_theta": canonical_angle(theta),
            "qubit": int(match.group("qubit")),
        }
    return output


def build_group_map(parameter_transfer: dict[str, Any]) -> dict[float, list[int]]:
    return {
        float(group["canonical_theta"]): list(group["line_numbers"])
        for group in parameter_transfer["angle_groups"]
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    shared = read_json(args.shared_object_gate)
    parameter_transfer = read_json(args.parameter_transfer_gate)
    qasm_rows = parse_qasm_ry_lines(args.qasm)
    group_map = build_group_map(parameter_transfer)
    objects = shared["shared_theta_synthesis_objects"]

    rows = []
    all_lines: list[int] = []
    line_theta_mismatches = 0
    missing_qasm_lines = 0
    object_group_mismatches = 0
    duplicate_lines = 0
    verified_objects = 0
    verified_occurrences = 0

    seen_lines: set[int] = set()
    for obj in objects:
        object_lines = list(obj["covered_line_numbers"])
        canonical_theta = float(obj["canonical_theta"])
        expected_group_lines = sorted(group_map.get(canonical_theta, []))
        object_lines_sorted = sorted(object_lines)
        group_match = object_lines_sorted == expected_group_lines
        if not group_match:
            object_group_mismatches += 1

        replayed_lines = []
        object_missing = 0
        object_mismatch = 0
        for line in object_lines_sorted:
            if line in seen_lines:
                duplicate_lines += 1
            seen_lines.add(line)
            all_lines.append(line)
            qasm_row = qasm_rows.get(line)
            if not qasm_row:
                missing_qasm_lines += 1
                object_missing += 1
                replayed_lines.append(
                    {
                        "line_number": line,
                        "qasm_line_found": False,
                        "canonical_theta_matches_object": False,
                    }
                )
                continue
            theta_match = qasm_row["canonical_theta"] == canonical_theta
            if not theta_match:
                line_theta_mismatches += 1
                object_mismatch += 1
            replayed_lines.append(
                {
                    "line_number": line,
                    "qasm_line_found": True,
                    "qasm_text": qasm_row["text"],
                    "parsed_theta": qasm_row["theta"],
                    "parsed_canonical_theta": qasm_row["canonical_theta"],
                    "object_canonical_theta": canonical_theta,
                    "canonical_theta_matches_object": theta_match,
                    "qubit": qasm_row["qubit"],
                }
            )

        object_verified = group_match and object_missing == 0 and object_mismatch == 0
        if object_verified:
            verified_objects += 1
            verified_occurrences += len(object_lines_sorted)
        rows.append(
            {
                "object_id": obj["object_id"],
                "canonical_theta": canonical_theta,
                "covered_line_count": len(object_lines_sorted),
                "expected_group_line_count": len(expected_group_lines),
                "object_group_lines_match_parameter_transfer": group_match,
                "missing_qasm_line_count": object_missing,
                "theta_mismatch_count": object_mismatch,
                "ledger_replay_verified": object_verified,
                "semantic_rewrite_verified": False,
                "occurrence_ledger_removed_occurrences": 0,
                "replayed_lines": replayed_lines,
            }
        )

    expected_lines = sorted({line for lines in group_map.values() for line in lines})
    all_lines_sorted = sorted(all_lines)
    coverage_matches_parameter_transfer = all_lines_sorted == expected_lines
    replay_gate_passed = (
        verified_objects == len(objects)
        and verified_occurrences == int(shared["summary"]["candidate_window_count"])
        and coverage_matches_parameter_transfer
        and duplicate_lines == 0
        and missing_qasm_lines == 0
        and line_theta_mismatches == 0
        and object_group_mismatches == 0
    )

    payload = {
        "benchmark_id": "B1",
        "problem_id": 25,
        "linked_b7_problem_id": 21,
        "title": "B1/B7 cone_01 shared-theta replay verifier scaffold",
        "version": VERSION,
        "last_updated": args.last_updated,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "method": METHOD,
        "source_qasm": display_path(args.qasm),
        "source_parameter_transfer_gate": display_path(args.parameter_transfer_gate),
        "source_shared_theta_synthesis_object_gate": display_path(args.shared_object_gate),
        "workload": "qasmbench_medium_exact/gcm_h6.qasm",
        "summary": {
            "candidate_window_count": int(shared["summary"]["candidate_window_count"]),
            "shared_synthesis_object_count": len(objects),
            "replay_verified_object_count": verified_objects,
            "replayed_occurrence_count": verified_occurrences,
            "parameter_transfer_expected_occurrence_count": len(expected_lines),
            "coverage_matches_parameter_transfer": coverage_matches_parameter_transfer,
            "duplicate_line_count": duplicate_lines,
            "missing_qasm_line_count": missing_qasm_lines,
            "line_theta_mismatch_count": line_theta_mismatches,
            "object_group_mismatch_count": object_group_mismatches,
            "shared_theta_replay_gate_passed": replay_gate_passed,
            "semantic_rewrite_verified": False,
            "semantic_certificate_claimed": False,
            "occurrence_ledger_removed_occurrences": 0,
            "occurrence_ledger_proxy_t_reduction": 0,
            "cost_model_accepted": False,
            "rewrite_claimed": False,
            "resource_saving_claimed": False,
            "physical_resource_reduction_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "validation_error_count": None,
        },
        "object_replay_rows": rows,
        "claim_boundary": {
            "cost_model_accepted": False,
            "semantic_rewrite_verified": False,
            "rewrite_claimed": False,
            "resource_saving_claimed": False,
            "semantic_certificate_claimed": False,
            "physical_resource_reduction_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "supported_claim": (
                "The shared-theta object proposals replay cleanly against the source QASM "
                "and parameter-transfer theta groups for all 35 cone_01 windows."
            ),
            "unsupported_claims": [
                "No occurrence-removing semantic rewrite is verified.",
                "No semantic certificate is produced.",
                "No physical layout, factory, or error-budget evidence is produced.",
                "No B7 ledger reduction is counted.",
            ],
            "next_gate": (
                "Use this replay scaffold as CM-03 evidence, then build CM-04 layout/routing "
                "and CM-05/CM-06 cost evidence before any physical cost model can be accepted."
            ),
        },
    }
    errors = validate(payload)
    payload["summary"]["validation_error_count"] = len(errors)
    payload["validation_errors"] = errors
    return payload


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = payload["summary"]
    claims = payload["claim_boundary"]
    if payload.get("method") != METHOD:
        errors.append("method mismatch")
    if payload.get("status") != STATUS:
        errors.append("status mismatch")
    if payload.get("model_status") != MODEL_STATUS:
        errors.append("model_status mismatch")
    if summary["candidate_window_count"] != 35:
        errors.append("expected 35 candidate windows")
    if summary["shared_synthesis_object_count"] != 4:
        errors.append("expected 4 shared synthesis objects")
    if summary["replay_verified_object_count"] != 4:
        errors.append("expected 4 replay-verified objects")
    if summary["replayed_occurrence_count"] != 35:
        errors.append("expected 35 replayed occurrences")
    if summary["parameter_transfer_expected_occurrence_count"] != 35:
        errors.append("expected 35 parameter-transfer occurrences")
    for field in [
        "duplicate_line_count",
        "missing_qasm_line_count",
        "line_theta_mismatch_count",
        "object_group_mismatch_count",
        "occurrence_ledger_removed_occurrences",
        "occurrence_ledger_proxy_t_reduction",
    ]:
        if summary[field] != 0:
            errors.append(f"{field} must be 0")
    if summary["coverage_matches_parameter_transfer"] is not True:
        errors.append("coverage should match parameter-transfer groups")
    if summary["shared_theta_replay_gate_passed"] is not True:
        errors.append("shared-theta replay gate should pass")
    for field in [
        "semantic_rewrite_verified",
        "semantic_certificate_claimed",
        "cost_model_accepted",
        "rewrite_claimed",
        "resource_saving_claimed",
        "physical_resource_reduction_claimed",
        "b7_ledger_improvement_claimed",
    ]:
        if summary[field] is not False:
            errors.append(f"{field} must remain false")
        if claims.get(field) is not False:
            errors.append(f"claim boundary {field} must remain false")
    for row in payload["object_replay_rows"]:
        if row["ledger_replay_verified"] is not True:
            errors.append(f"{row['object_id']} should be ledger-replay verified")
        if row["semantic_rewrite_verified"] is not False:
            errors.append(f"{row['object_id']} semantic rewrite must remain false")
        if row["occurrence_ledger_removed_occurrences"] != 0:
            errors.append(f"{row['object_id']} occurrence removal must remain 0")
    return errors


def markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone_01 Shared-Theta Replay Verifier Scaffold",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This artifact replay-checks the shared-theta object proposals against the "
        "source QASM and the parameter-transfer theta groups. It verifies coverage "
        "and line-level theta consistency. It does not verify an occurrence-removing "
        "semantic rewrite and does not count any B7 resource reduction.",
        "",
        "## Summary",
        "",
        f"- Candidate windows: `{summary['candidate_window_count']}`",
        f"- Shared synthesis objects: `{summary['shared_synthesis_object_count']}`",
        f"- Replay-verified objects: `{summary['replay_verified_object_count']}`",
        f"- Replayed occurrences: `{summary['replayed_occurrence_count']}`",
        f"- Coverage matches parameter-transfer groups: `{summary['coverage_matches_parameter_transfer']}`",
        f"- Duplicate line count: `{summary['duplicate_line_count']}`",
        f"- Missing QASM line count: `{summary['missing_qasm_line_count']}`",
        f"- Line theta mismatch count: `{summary['line_theta_mismatch_count']}`",
        f"- Object group mismatch count: `{summary['object_group_mismatch_count']}`",
        f"- Shared-theta replay gate passed: `{summary['shared_theta_replay_gate_passed']}`",
        f"- Semantic rewrite verified: `{summary['semantic_rewrite_verified']}`",
        f"- Occurrence-ledger removed occurrences: `{summary['occurrence_ledger_removed_occurrences']}`",
        f"- Cost model accepted: `{summary['cost_model_accepted']}`",
        f"- Validation errors: `{summary['validation_error_count']}`",
        "",
        "## Object Replay Rows",
        "",
        "| object | theta | covered lines | expected lines | replay verified | theta mismatches |",
        "|---|---:|---:|---:|---|---:|",
    ]
    for row in payload["object_replay_rows"]:
        lines.append(
            f"| `{row['object_id']}` | `{row['canonical_theta']}` | "
            f"{row['covered_line_count']} | {row['expected_group_line_count']} | "
            f"`{row['ledger_replay_verified']}` | {row['theta_mismatch_count']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The shared-theta proposals now have replayable line-level evidence. This is "
            "useful CM-03 scaffolding, but it is intentionally weaker than a semantic "
            "rewrite certificate. The next hard gates are physical layout/routing, "
            "factory-amortization evidence, shared-error budgeting, independent "
            "baseline pressure, and a refreshed B7 ledger.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--qasm",
        type=Path,
        default=root / "results" / "b1_u3_phase_factored_optimizer" / "qasmbench_medium_exact" / "gcm_h6.qasm",
    )
    parser.add_argument(
        "--parameter-transfer-gate",
        type=Path,
        default=root / "results" / "B1_B7_cone01_parameter_transfer_gate_v0.json",
    )
    parser.add_argument(
        "--shared-object-gate",
        type=Path,
        default=root / "results" / "B1_B7_cone01_shared_theta_synthesis_object_gate_v0.json",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=root / "results" / "B1_B7_cone01_shared_theta_replay_verifier_gate_v0.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=root / "research" / "B1_B7_cone01_shared_theta_replay_verifier_gate.md",
    )
    parser.add_argument("--last-updated", default="2026-06-18")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    write_text(args.markdown_output, markdown(payload))
    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Wrote {args.json_output}")
        print(f"Wrote {args.markdown_output}")


if __name__ == "__main__":
    main()
