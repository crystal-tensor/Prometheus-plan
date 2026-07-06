#!/usr/bin/env python3
"""T-B1-004do/T-B7-012x: R13 NL-C02 source-domain binding gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r13_nlc02_source_domain_binding_gate_v0"
STATUS = "cone01_r13_nlc02_source_domain_binding_ready_not_full_lemma"
MODEL_STATUS = "nlc02_o4_source_domain_binding_closed_for_current_hash_chain"
VERSION = "0.1"
TARGET_ID = "T-B1-004do/T-B7-012x"
BINDING_ID = "B1-B7-cone01-R13-NL-C02-source-domain-binding"
CANDIDATE_ID = "NL-C02"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def requirement(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def row_list_name(size: int) -> str:
    return {
        1: "line1381_leave_one_out_parameter_rows",
        2: "line1381_leave_two_out_parameter_rows",
        3: "line1381_leave_three_out_parameter_rows",
        4: "line1381_leave_four_out_parameter_rows",
        5: "line1381_leave_five_out_parameter_rows",
    }[size]


def fixed_indices(row: dict[str, Any]) -> list[int]:
    if "fixed_parameter_indices" in row:
        return [int(v) for v in row["fixed_parameter_indices"]]
    if "all_grid_fixed_parameter_indices" in row:
        return [int(v) for v in row["all_grid_fixed_parameter_indices"]]
    return [int(row["fixed_parameter_index"])]


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    r7 = load_json(args.r7_contract)
    r8 = load_json(args.r8_preflight)
    r9 = load_json(args.r9_pressure)
    r11 = load_json(args.r11_skeleton)
    r12 = load_json(args.r12_bridge)
    r7s = r7["summary"]
    r8s = r8["summary"]
    r9s = r9["summary"]
    r11s = r11["summary"]
    r12s = r12["summary"]

    leave_paths = [
        args.leave_one,
        args.leave_two,
        args.leave_three,
        args.leave_four,
        args.leave_five,
    ]
    leave_payloads = [load_json(path) for path in leave_paths]
    leave_summaries = [payload["summary"] for payload in leave_payloads]

    canonical_indices = leave_summaries[0]["current_off_grid_parameter_indices"]
    canonical_values = leave_summaries[0]["current_off_grid_parameter_values"]
    canonical_tolerance = leave_summaries[0]["exact_tolerance"]
    canonical_domain_rows = []
    for index, value in zip(canonical_indices, canonical_values):
        canonical_domain_rows.append(
            {
                "line": 1381,
                "parameter_index": index,
                "off_grid_value": value,
                "domain_role": "current_line1381_off_grid_parameter",
            }
        )

    leave_domain_rows = []
    normalized_subset_keys = set()
    for size, (path, payload) in enumerate(zip(leave_paths, leave_payloads), start=1):
        summary = payload["summary"]
        rows = payload[row_list_name(size)]
        for row in rows:
            indices = fixed_indices(row)
            normalized_subset_keys.add(",".join(str(v) for v in indices))
        leave_domain_rows.append(
            {
                "source_path": str(path),
                "source_sha256": file_hash(path),
                "method": payload["method"],
                "status": payload["status"],
                "validation_error_count": summary["validation_error_count"],
                "current_off_grid_parameter_count": summary["current_off_grid_parameter_count"],
                "current_off_grid_parameter_indices": summary["current_off_grid_parameter_indices"],
                "current_off_grid_parameter_values": summary["current_off_grid_parameter_values"],
                "exact_tolerance": summary["exact_tolerance"],
                "row_count": len(rows),
            }
        )

    chain_rows = [
        {
            "stage": "R7",
            "path": str(args.r7_contract),
            "method": r7["method"],
            "file_sha256": file_hash(args.r7_contract),
            "artifact_hash": r7s["contract_hash"],
            "domain_count": r7s["line1381_off_grid_parameter_count"],
        },
        {
            "stage": "R8",
            "path": str(args.r8_preflight),
            "method": r8["method"],
            "file_sha256": file_hash(args.r8_preflight),
            "artifact_hash": r8s["preflight_hash"],
            "source_contract_hash": r8s["r7_contract_hash"],
            "domain_count": r8s["line1381_remaining_off_grid_parameter_count"],
        },
        {
            "stage": "R9",
            "path": str(args.r9_pressure),
            "method": r9["method"],
            "file_sha256": file_hash(args.r9_pressure),
            "artifact_hash": r9s["pressure_hash"],
            "source_preflight_hash": r9s["r8_preflight_hash"],
            "leave_attempt_row_count": r9s["leave_attempt_row_count"],
        },
        {
            "stage": "R11",
            "path": str(args.r11_skeleton),
            "method": r11["method"],
            "file_sha256": file_hash(args.r11_skeleton),
            "artifact_hash": r11s["skeleton_hash"],
            "source_r9_pressure_hash": r11s["source_r9_pressure_hash"],
            "row_table_hash": r11s["row_table_hash"],
            "covered_parameter_count": r11s["covered_parameter_count"],
        },
        {
            "stage": "R12",
            "path": str(args.r12_bridge),
            "method": r12["method"],
            "file_sha256": file_hash(args.r12_bridge),
            "artifact_hash": r12s["bridge_hash"],
            "source_r11_skeleton_hash": r12s["source_r11_skeleton_hash"],
            "source_r11_row_table_hash": r12s["source_r11_row_table_hash"],
            "bridge_row_count": r12s["bridge_row_count"],
        },
    ]

    domain_binding_packet = {
        "binding_id": BINDING_ID,
        "source_target_id": TARGET_ID,
        "candidate_id": CANDIDATE_ID,
        "canonical_domain": {
            "line": 1381,
            "parameter_count": len(canonical_indices),
            "parameter_indices": canonical_indices,
            "parameter_values": canonical_values,
            "exact_tolerance": canonical_tolerance,
            "domain_rows": canonical_domain_rows,
        },
        "hash_chain": chain_rows,
        "leave_out_domain_sources": leave_domain_rows,
        "normalized_subset_key_count": len(normalized_subset_keys),
        "source_domain_statement": (
            "For the current R7-R12 hash chain, NL-C02 refers to the same five line1381 "
            "off-grid parameters [3, 4, 9, 16, 17] and the same 31 leave-out subset rows."
        ),
        "remaining_open_obligations": ["O1", "O3"],
        "decision": {
            "o4_closed_for_current_hash_chain": True,
            "checked_negative_lemma_present": False,
            "nlc02_full_lemma_ready": False,
            "reroute_allowed": False,
            "why": (
                "O4 is source-bound for the current hash chain, but O1 optimizer completeness and "
                "O3 parameterization invariance remain open."
            ),
        },
    }
    domain_binding_packet["domain_hash"] = stable_hash(domain_binding_packet["canonical_domain"])
    domain_binding_packet["binding_hash"] = stable_hash(domain_binding_packet)

    all_leave_domains_match = all(
        row["current_off_grid_parameter_indices"] == canonical_indices
        and row["current_off_grid_parameter_values"] == canonical_values
        and row["exact_tolerance"] == canonical_tolerance
        for row in leave_domain_rows
    )
    all_leave_sources_clean = all(row["validation_error_count"] == 0 for row in leave_domain_rows)
    all_leave_sources_hashed = all(row["source_sha256"] for row in leave_domain_rows)
    chain_hashes_present = all(row.get("file_sha256") and row.get("artifact_hash") for row in chain_rows)
    hash_chain_consistent = (
        r8s["r7_contract_hash"] == r7s["contract_hash"]
        and r9s["r8_preflight_hash"] == r8s["preflight_hash"]
        and r11s["source_r9_pressure_hash"] == r9s["pressure_hash"]
        and r12s["source_r11_skeleton_hash"] == r11s["skeleton_hash"]
        and r12s["source_r11_row_table_hash"] == r11s["row_table_hash"]
    )

    requirements = [
        requirement(
            "D1",
            "R7-R12 source artifacts are validation-clean where summaries expose validation counts",
            all(
                summary.get("validation_error_count") == 0
                for summary in [r7s, r8s, r9s, r11s, r12s]
            ),
            {
                "validation_error_counts": [
                    r7s.get("validation_error_count"),
                    r8s.get("validation_error_count"),
                    r9s.get("validation_error_count"),
                    r11s.get("validation_error_count"),
                    r12s.get("validation_error_count"),
                ]
            },
        ),
        requirement(
            "D2",
            "R7-R12 hash chain is consistent",
            hash_chain_consistent,
            {
                "r7_contract_hash": r7s["contract_hash"],
                "r8_source_contract_hash": r8s["r7_contract_hash"],
                "r8_preflight_hash": r8s["preflight_hash"],
                "r9_source_preflight_hash": r9s["r8_preflight_hash"],
                "r9_pressure_hash": r9s["pressure_hash"],
                "r11_source_pressure_hash": r11s["source_r9_pressure_hash"],
                "r11_skeleton_hash": r11s["skeleton_hash"],
                "r12_source_skeleton_hash": r12s["source_r11_skeleton_hash"],
            },
        ),
        requirement(
            "D3",
            "Canonical domain is the five current line1381 off-grid parameters",
            canonical_indices == [3, 4, 9, 16, 17]
            and len(canonical_values) == 5
            and canonical_tolerance == 1e-8,
            {
                "canonical_indices": canonical_indices,
                "canonical_values": canonical_values,
                "canonical_tolerance": canonical_tolerance,
            },
        ),
        requirement(
            "D4",
            "R7 and R8 domain counts match the canonical five-parameter domain",
            r7s["line1381_off_grid_parameter_count"] == 5
            and r8s["line1381_remaining_off_grid_parameter_count"] == 5
            and r11s["covered_parameter_count"] == 5,
            {
                "r7_count": r7s["line1381_off_grid_parameter_count"],
                "r8_count": r8s["line1381_remaining_off_grid_parameter_count"],
                "r11_count": r11s["covered_parameter_count"],
            },
        ),
        requirement(
            "D5",
            "All five leave-out source files expose identical parameter indices, values, and tolerance",
            all_leave_domains_match,
            {"leave_out_domain_sources": leave_domain_rows},
        ),
        requirement(
            "D6",
            "Leave-out sources are validation-clean and hash-bound",
            all_leave_sources_clean and all_leave_sources_hashed,
            {
                "leave_source_count": len(leave_domain_rows),
                "all_leave_sources_clean": all_leave_sources_clean,
                "all_leave_sources_hashed": all_leave_sources_hashed,
            },
        ),
        requirement(
            "D7",
            "R9/R11/R12 row counts bind to the same 31 leave-out rows",
            r9s["leave_attempt_row_count"] == 31
            and r11s["leave_out_row_count"] == 31
            and r12s["bridge_row_count"] == 31
            and len(normalized_subset_keys) == 31,
            {
                "r9_leave_attempt_row_count": r9s["leave_attempt_row_count"],
                "r11_leave_out_row_count": r11s["leave_out_row_count"],
                "r12_bridge_row_count": r12s["bridge_row_count"],
                "normalized_subset_key_count": len(normalized_subset_keys),
            },
        ),
        requirement(
            "D8",
            "All R7-R12 stage files are file-hash and artifact-hash bound",
            chain_hashes_present,
            {"chain_rows": chain_rows},
        ),
        requirement(
            "D9",
            "O4 is closed only for the current hash chain while O1/O3 remain open",
            domain_binding_packet["decision"]["o4_closed_for_current_hash_chain"] is True
            and domain_binding_packet["remaining_open_obligations"] == ["O1", "O3"],
            {
                "remaining_open_obligations": domain_binding_packet["remaining_open_obligations"],
                "decision": domain_binding_packet["decision"],
            },
        ),
        requirement(
            "D10",
            "Binding is not upgraded into a checked negative lemma or reroute",
            domain_binding_packet["decision"]["checked_negative_lemma_present"] is False
            and domain_binding_packet["decision"]["nlc02_full_lemma_ready"] is False
            and domain_binding_packet["decision"]["reroute_allowed"] is False,
            domain_binding_packet["decision"],
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids:
        validation_errors.append(f"unexpected R13 source-domain binding failures: {failed_ids}")

    summary = {
        "binding_id": BINDING_ID,
        "binding_hash": domain_binding_packet["binding_hash"],
        "domain_hash": domain_binding_packet["domain_hash"],
        "candidate_id": CANDIDATE_ID,
        "source_r7_contract_hash": r7s["contract_hash"],
        "source_r8_preflight_hash": r8s["preflight_hash"],
        "source_r9_pressure_hash": r9s["pressure_hash"],
        "source_r11_skeleton_hash": r11s["skeleton_hash"],
        "source_r12_bridge_hash": r12s["bridge_hash"],
        "canonical_line": 1381,
        "canonical_parameter_count": len(canonical_indices),
        "canonical_parameter_indices": canonical_indices,
        "canonical_exact_tolerance": canonical_tolerance,
        "leave_out_source_count": len(leave_domain_rows),
        "normalized_subset_key_count": len(normalized_subset_keys),
        "hash_chain_stage_count": len(chain_rows),
        "o4_closed_for_current_hash_chain": True,
        "remaining_open_obligations": ["O1", "O3"],
        "remaining_open_obligation_count": 2,
        "checked_negative_lemma_present": False,
        "nlc02_full_lemma_ready": False,
        "reroute_allowed": False,
        "accepted_route_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "b7_credit_delta": 0,
        "b7_space_time_volume_credit": 0,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "requirement_count": len(requirements),
        "requirements_passed": passed,
        "requirements_failed": len(requirements) - passed,
        "failed_requirement_ids": failed_ids,
        "validation_error_count": len(validation_errors),
    }

    return {
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "source_target_id": TARGET_ID,
        "title": "B1/B7 Cone01 R13 NL-C02 Source-Domain Binding Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "summary": summary,
        "nlc02_source_domain_binding_packet": domain_binding_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "R13 closes O4 for the current R7-R12 hash chain by binding NL-C02 to the same "
                "line1381 five-parameter domain and the same 31 leave-out subset rows."
            ),
            "what_is_not_supported": (
                "R13 does not close optimizer completeness or parameterization invariance. NL-C02 is "
                "still not a checked negative lemma. No R5 reroute, R1 solution, occurrence removal, "
                "proxy-T reduction, B7 credit, resource saving, or impossibility theorem is supported."
            ),
            "next_gate": (
                "Close O1 or O3; or falsify the binding with a source hash mismatch, domain drift, "
                "or a leave-out source whose parameter indices, values, or tolerance differ."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    packet = payload["nlc02_source_domain_binding_packet"]
    lines = [
        f"# {payload['title']}",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Candidate: `{s['candidate_id']}`",
        f"- Binding hash: `{s['binding_hash']}`",
        f"- Domain hash: `{s['domain_hash']}`",
        "",
        "## Result",
        "",
        (
            f"The R13 source-domain binding gate passes {s['requirements_passed']}/{s['requirement_count']} "
            "requirements. It closes O4 for the current hash chain, but does not make NL-C02 a checked negative lemma."
        ),
        "",
        "## Domain",
        "",
        f"- Canonical line: `{s['canonical_line']}`",
        f"- Parameter indices: `{s['canonical_parameter_indices']}`",
        f"- Parameter count: `{s['canonical_parameter_count']}`",
        f"- Exact tolerance: `{s['canonical_exact_tolerance']}`",
        f"- Leave-out source count: `{s['leave_out_source_count']}`",
        f"- Normalized subset keys: `{s['normalized_subset_key_count']}`",
        "",
        "## Hash Chain",
        "",
    ]
    for row in packet["hash_chain"]:
        lines.append(f"- `{row['stage']}` {row['method']}: `{row['artifact_hash']}`")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- O4 closed for current hash chain: `{s['o4_closed_for_current_hash_chain']}`",
            f"- Remaining open obligations: `{s['remaining_open_obligations']}`",
            f"- Checked negative lemma present: `{s['checked_negative_lemma_present']}`",
            f"- NL-C02 full lemma ready: `{s['nlc02_full_lemma_ready']}`",
            f"- Reroute allowed: `{s['reroute_allowed']}`",
            "",
            "## Requirement Results",
            "",
        ]
    )
    for row in payload["requirements"]:
        marker = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- `{row['requirement_id']}` {marker}: {row['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            "",
            "This source-domain binding gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a checked impossibility theorem, an R5 reroute, or a solved B1/B7 problem.",
            "",
            "## Validation",
            "",
            f"- validation_error_count: `{s['validation_error_count']}`",
        ]
    )
    for error in payload["validation_errors"]:
        lines.append(f"- {error}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--r7-contract",
        type=Path,
        default=Path("results/B1_B7_cone01_R7_r1_submission_contract_gate_v0.json"),
    )
    parser.add_argument(
        "--r8-preflight",
        type=Path,
        default=Path("results/B1_B7_cone01_R8_r1_contract_preflight_gate_v0.json"),
    )
    parser.add_argument(
        "--r9-pressure",
        type=Path,
        default=Path("results/B1_B7_cone01_R9_r1_reroute_pressure_gate_v0.json"),
    )
    parser.add_argument(
        "--r11-skeleton",
        type=Path,
        default=Path("results/B1_B7_cone01_R11_nlc02_leaveout_proof_skeleton_gate_v0.json"),
    )
    parser.add_argument(
        "--r12-bridge",
        type=Path,
        default=Path("results/B1_B7_cone01_R12_nlc02_tolerance_bridge_gate_v0.json"),
    )
    parser.add_argument(
        "--leave-one",
        type=Path,
        default=Path("results/B1_B7_cone01_line1381_leave_one_out_parameter_gate_v0.json"),
    )
    parser.add_argument(
        "--leave-two",
        type=Path,
        default=Path("results/B1_B7_cone01_line1381_leave_two_out_parameter_gate_v0.json"),
    )
    parser.add_argument(
        "--leave-three",
        type=Path,
        default=Path("results/B1_B7_cone01_line1381_leave_three_out_parameter_gate_v0.json"),
    )
    parser.add_argument(
        "--leave-four",
        type=Path,
        default=Path("results/B1_B7_cone01_line1381_leave_four_out_parameter_gate_v0.json"),
    )
    parser.add_argument(
        "--leave-five",
        type=Path,
        default=Path("results/B1_B7_cone01_line1381_leave_five_out_parameter_gate_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_R13_nlc02_source_domain_binding_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_R13_nlc02_source_domain_binding_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-06")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "binding_hash": payload["summary"]["binding_hash"],
                "domain_hash": payload["summary"]["domain_hash"],
                "canonical_parameter_indices": payload["summary"]["canonical_parameter_indices"],
                "normalized_subset_key_count": payload["summary"]["normalized_subset_key_count"],
                "remaining_open_obligations": payload["summary"]["remaining_open_obligations"],
                "reroute_allowed": payload["summary"]["reroute_allowed"],
                "requirements_passed": payload["summary"]["requirements_passed"],
                "requirements_failed": payload["summary"]["requirements_failed"],
                "validation_error_count": payload["summary"]["validation_error_count"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if payload["validation_errors"]:
        raise SystemExit("B1/B7 R13 source-domain binding gate validation failed")


if __name__ == "__main__":
    main()
