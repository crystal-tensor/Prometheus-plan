#!/usr/bin/env python3
"""T-B1-004eg/T-B7-013p: R31 O3-F4 C2 numeric-only overclaim sentinel."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r31_o3_f4_c2_numeric_only_overclaim_sentinel_gate_v0"
STATUS = "cone01_r31_o3_f4_c2_numeric_only_fixture_rejected"
MODEL_STATUS = "o3_f4_c2_numeric_tolerance_alone_rejected_no_c2_acceptance"
VERSION = "0.1"
TARGET_ID = "T-B1-004eg/T-B7-013p"
UPSTREAM_TARGET_ID = "T-B1-004ef/T-B7-013o"
FAMILY_ID = "O3-F4"
CANDIDATE_ID = "NL-C02"
STRICT_TOLERANCE = 1.0e-8
REQUIRED_ROW_KEYS = [
    "challenge_id",
    "parameter_indices",
    "source_initial_values",
    "submitted_parameter_values",
    "strict_tolerance",
    "max_unitary_replay_error",
    "unitary_distance_metric",
    "same_unitary_witness_hash",
    "source_circuit_hash",
    "candidate_circuit_hash",
    "replay_command",
    "replay_stdout_hash",
    "verifier_version",
]
HASH_FIELDS = [
    "same_unitary_witness_hash",
    "source_circuit_hash",
    "candidate_circuit_hash",
    "replay_stdout_hash",
]
PLACEHOLDER_TOKENS = ("<", ">", "placeholder", "numeric-only")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def requirement(
    requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def contains_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        lower = value.lower()
        return any(token in lower for token in PLACEHOLDER_TOKENS)
    if isinstance(value, list):
        return any(contains_placeholder(item) for item in value)
    if isinstance(value, dict):
        return any(contains_placeholder(item) for item in value.values())
    return False


def build_numeric_only_fixture(template: dict[str, Any], r30: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for idx, row in enumerate(template["rows"]):
        rows.append(
            {
                **row,
                "submitted_parameter_values": row["source_initial_values"],
                "max_unitary_replay_error": 1.0e-10 * (idx + 1),
                "unitary_distance_metric": "statevector_span_bound",
                "same_unitary_witness_hash": "numeric-only-placeholder-no-witness",
                "source_circuit_hash": "numeric-only-placeholder-source-hash",
                "candidate_circuit_hash": "numeric-only-placeholder-candidate-hash",
                "replay_command": "python3 tools/<missing-real-replay-command>.py",
                "replay_stdout_hash": "numeric-only-placeholder-stdout-hash",
                "verifier_version": "numeric-only-fixture-v0",
            }
        )
    fixture = {
        "artifact_id": "B1-B7-cone01-O3-F4-C2-numeric-only-overclaim.fixture",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "family_id": FAMILY_ID,
        "candidate_id": CANDIDATE_ID,
        "source_r30_template_hash": r30["summary"]["template_hash"],
        "source_r30_row_table_hash": r30["summary"]["row_table_hash"],
        "source_r30_preflight_hash": r30["summary"]["preflight_hash"],
        "strict_tolerance": STRICT_TOLERANCE,
        "rows": rows,
        "claim_boundary": {
            "supported": "negative sentinel only: numeric replay values alone are insufficient for C2 acceptance",
            "not_supported": "C2 acceptance, O3 closure, R5 reroute, B7 credit, STV credit, or resource savings",
        },
        "o3_closed": False,
        "reroute_allowed": False,
        "b7_credit_delta": 0,
    }
    fixture["fixture_row_table_hash"] = stable_hash(rows)
    fixture["fixture_hash"] = stable_hash(fixture)
    return fixture


def evaluate_fixture(fixture: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    expected_ids = [row["challenge_id"] for row in template["rows"]]
    rows = fixture.get("rows", [])
    actual_ids = [row.get("challenge_id") for row in rows if isinstance(row, dict)]
    missing_ids = [challenge_id for challenge_id in expected_ids if challenge_id not in actual_ids]
    extra_ids = [challenge_id for challenge_id in actual_ids if challenge_id not in expected_ids]
    missing_key_rows = {
        row.get("challenge_id", f"row_{idx}"): [
            key for key in REQUIRED_ROW_KEYS if key not in row
        ]
        for idx, row in enumerate(rows)
        if isinstance(row, dict)
    }
    missing_key_rows = {key: value for key, value in missing_key_rows.items() if value}
    numeric_errors = [
        float(row["max_unitary_replay_error"])
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("max_unitary_replay_error"), (int, float))
    ]
    tolerance_pass_count = sum(error <= STRICT_TOLERANCE for error in numeric_errors)
    invalid_hash_cells = []
    placeholder_cells = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        challenge_id = row.get("challenge_id")
        for field in HASH_FIELDS:
            value = row.get(field)
            if not is_sha256(value):
                invalid_hash_cells.append(f"{challenge_id}:{field}")
            if contains_placeholder(value):
                placeholder_cells.append(f"{challenge_id}:{field}")
        if contains_placeholder(row.get("replay_command")):
            placeholder_cells.append(f"{challenge_id}:replay_command")
    surface_pass = (
        len(rows) == 8
        and not missing_ids
        and not extra_ids
        and not missing_key_rows
        and len(numeric_errors) == 8
        and tolerance_pass_count == 8
    )
    evidence_pass = not invalid_hash_cells and not placeholder_cells
    accepted = surface_pass and evidence_pass
    result = {
        "accepted": accepted,
        "surface_pass": surface_pass,
        "evidence_pass": evidence_pass,
        "row_count": len(rows),
        "expected_row_count": 8,
        "missing_challenge_ids": missing_ids,
        "extra_challenge_ids": extra_ids,
        "missing_key_rows": missing_key_rows,
        "numeric_replay_error_count": len(numeric_errors),
        "tolerance_pass_count": tolerance_pass_count,
        "max_observed_replay_error": max(numeric_errors) if numeric_errors else None,
        "strict_tolerance": STRICT_TOLERANCE,
        "invalid_hash_cell_count": len(invalid_hash_cells),
        "invalid_hash_cells": invalid_hash_cells,
        "placeholder_cell_count": len(placeholder_cells),
        "placeholder_cells": placeholder_cells,
        "claim_boundary_zero_credit": fixture.get("o3_closed") is False
        and fixture.get("reroute_allowed") is False
        and fixture.get("b7_credit_delta") == 0,
    }
    result["preflight_hash"] = stable_hash(result)
    return result


def build_payload(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.time()
    r30 = load_json(args.r30_intake)
    template = load_json(args.c2_template)
    fixture = build_numeric_only_fixture(template, r30)
    preflight = evaluate_fixture(fixture, template)
    requirements = [
        requirement(
            "S1",
            "R30 source is validation-clean and template hash matches",
            r30["summary"].get("validation_error_count") == 0
            and r30["summary"].get("template_hash") == template.get("template_hash"),
            {
                "r30_validation_error_count": r30["summary"].get("validation_error_count"),
                "r30_template_hash": r30["summary"].get("template_hash"),
                "template_hash": template.get("template_hash"),
            },
        ),
        requirement(
            "S2",
            "Numeric-only fixture covers all 8 C2 rows with required fields",
            preflight["row_count"] == 8
            and not preflight["missing_challenge_ids"]
            and not preflight["extra_challenge_ids"]
            and not preflight["missing_key_rows"],
            {
                "row_count": preflight["row_count"],
                "missing_challenge_ids": preflight["missing_challenge_ids"],
                "missing_key_rows": preflight["missing_key_rows"],
            },
        ),
        requirement(
            "S3",
            "Numeric-only fixture passes the numeric tolerance surface",
            preflight["numeric_replay_error_count"] == 8
            and preflight["tolerance_pass_count"] == 8
            and preflight["max_observed_replay_error"] <= STRICT_TOLERANCE,
            {
                "numeric_replay_error_count": preflight["numeric_replay_error_count"],
                "tolerance_pass_count": preflight["tolerance_pass_count"],
                "max_observed_replay_error": preflight["max_observed_replay_error"],
                "strict_tolerance": STRICT_TOLERANCE,
            },
        ),
        requirement(
            "S4",
            "Numeric tolerance alone is rejected without witness and hash provenance",
            preflight["accepted"] is False
            and preflight["surface_pass"] is True
            and preflight["evidence_pass"] is False
            and preflight["invalid_hash_cell_count"] == 32,
            {
                "accepted": preflight["accepted"],
                "surface_pass": preflight["surface_pass"],
                "evidence_pass": preflight["evidence_pass"],
                "invalid_hash_cell_count": preflight["invalid_hash_cell_count"],
            },
        ),
        requirement(
            "S5",
            "Fixture keeps C2, O3, reroute, and B7 credit unaccepted",
            fixture["o3_closed"] is False
            and fixture["reroute_allowed"] is False
            and fixture["b7_credit_delta"] == 0
            and preflight["accepted"] is False,
            {
                "c2_accepted": preflight["accepted"],
                "o3_closed": fixture["o3_closed"],
                "reroute_allowed": fixture["reroute_allowed"],
                "b7_credit_delta": fixture["b7_credit_delta"],
            },
        ),
        requirement(
            "S6",
            "Fixture and preflight are hash-bound",
            bool(fixture["fixture_hash"])
            and bool(fixture["fixture_row_table_hash"])
            and bool(preflight["preflight_hash"]),
            {
                "fixture_hash": fixture["fixture_hash"],
                "fixture_row_table_hash": fixture["fixture_row_table_hash"],
                "preflight_hash": preflight["preflight_hash"],
            },
        ),
        requirement(
            "S7",
            "R31 does not claim C3-C7 progress",
            all(
                not fixture.get(flag, False)
                for flag in [
                    "same_unitary_replay_certificate_complete",
                    "same_access_denominator_comparison_complete",
                    "leakage_free_optimizer_trace_complete",
                    "machine_check_replay_complete",
                ]
            ),
            {
                "scope": "C2 numeric-only sentinel",
                "c3_c7_progress_claimed": False,
            },
        ),
        requirement(
            "S8",
            "Sentinel preserves the R30 challenge-row identity",
            fixture["source_r30_row_table_hash"] == r30["summary"]["row_table_hash"],
            {
                "source_r30_row_table_hash": fixture["source_r30_row_table_hash"],
                "r30_row_table_hash": r30["summary"]["row_table_hash"],
            },
        ),
    ]
    failed_requirements = [
        item["requirement_id"] for item in requirements if not item["passed"]
    ]
    template_file_sha256 = file_hash(args.c2_template)
    summary = {
        "candidate_id": CANDIDATE_ID,
        "family_id": FAMILY_ID,
        "source_r30_template_hash": r30["summary"]["template_hash"],
        "source_r30_row_table_hash": r30["summary"]["row_table_hash"],
        "source_r30_preflight_hash": r30["summary"]["preflight_hash"],
        "source_c2_template_file_sha256": template_file_sha256,
        "fixture_hash": fixture["fixture_hash"],
        "fixture_row_table_hash": fixture["fixture_row_table_hash"],
        "preflight_hash": preflight["preflight_hash"],
        "strict_tolerance": STRICT_TOLERANCE,
        "row_count": preflight["row_count"],
        "numeric_replay_error_count": preflight["numeric_replay_error_count"],
        "tolerance_pass_count": preflight["tolerance_pass_count"],
        "max_observed_replay_error": preflight["max_observed_replay_error"],
        "invalid_hash_cell_count": preflight["invalid_hash_cell_count"],
        "placeholder_cell_count": preflight["placeholder_cell_count"],
        "surface_pass": preflight["surface_pass"],
        "evidence_pass": preflight["evidence_pass"],
        "c2_strict_replay_rows_accepted": False,
        "c2_numeric_only_fixture_accepted": False,
        "o3_f4_artifact_accepted": False,
        "same_unitary_replay_certificate_complete": False,
        "same_access_denominator_comparison_complete": False,
        "leakage_free_optimizer_trace_complete": False,
        "machine_check_replay_complete": False,
        "o3_closed": False,
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
        "remaining_open_obligations": [
            "C2_valid_sha256_witness_and_circuit_hashes",
            "C2_real_replay_command_and_stdout_hash",
            "C3_same_unitary_replay_certificate",
            "C4_C5_same_access_denominator_comparison",
            "C6_leakage_free_optimizer_trace",
            "C7_machine_check_replay_bundle",
        ],
        "remaining_open_obligation_count": 6,
        "requirement_count": len(requirements),
        "requirements_passed": len(requirements) - len(failed_requirements),
        "requirements_failed": len(failed_requirements),
        "failed_requirement_ids": failed_requirements,
        "validation_error_count": len(failed_requirements),
    }
    payload = {
        "title": "B1/B7 Cone01 R31 O3-F4 C2 Numeric-Only Overclaim Sentinel",
        "version": VERSION,
        "last_updated": "2026-07-08",
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "o3_f4_c2_numeric_only_overclaim_sentinel_packet": {
            "source_r30_intake": str(args.r30_intake),
            "source_c2_template": str(args.c2_template),
            "fixture_output": str(args.fixture_output),
            "fixture": fixture,
            "preflight_result": preflight,
        },
        "requirements": requirements,
        "summary": summary,
        "claim_boundary": {
            "what_is_supported": (
                "R31 proves numeric replay errors under tolerance are not enough "
                "for C2 acceptance without valid same-unitary witness hashes, "
                "source/candidate circuit hashes, replay command provenance, "
                "and stdout hashes."
            ),
            "what_is_not_supported": (
                "R31 does not accept C2, does not complete the certificate triad, "
                "does not close O3, and does not permit reroute, B7 credit, STV "
                "credit, or resource-saving claims."
            ),
            "next_gate": (
                "Replace the numeric-only fixture placeholders with valid sha256 "
                "witness/circuit/stdout hashes and a real replay command while "
                "keeping all 8 numeric replay errors <= 1e-08."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": failed_requirements,
        "runtime_seconds": round(time.time() - started, 6),
    }
    return payload, fixture


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone01 R31 O3-F4 C2 Numeric-Only Overclaim Sentinel",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Upstream target: `{payload['upstream_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Fixture hash: `{summary['fixture_hash']}`",
        f"- Fixture row-table hash: `{summary['fixture_row_table_hash']}`",
        f"- Preflight hash: `{summary['preflight_hash']}`",
        "",
        "## Result",
        "",
        (
            f"R31 passes {summary['requirements_passed']}/"
            f"{summary['requirement_count']} requirements by rejecting a "
            "numeric-only C2 fixture that passes the tolerance surface but lacks "
            "valid witness and hash provenance."
        ),
        "",
        "## Sentinel Outcome",
        "",
        f"- Row count: `{summary['row_count']}`",
        f"- Numeric replay error count: `{summary['numeric_replay_error_count']}`",
        f"- Tolerance pass count: `{summary['tolerance_pass_count']}`",
        f"- Max observed replay error: `{summary['max_observed_replay_error']}`",
        f"- Invalid hash cell count: `{summary['invalid_hash_cell_count']}`",
        f"- Surface pass: `{summary['surface_pass']}`",
        f"- Evidence pass: `{summary['evidence_pass']}`",
        f"- C2 accepted: `{summary['c2_strict_replay_rows_accepted']}`",
        "",
        "## Requirement Results",
        "",
    ]
    for item in payload["requirements"]:
        mark = "PASS" if item["passed"] else "FAIL"
        lines.append(f"- `{item['requirement_id']}` {mark}: {item['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            "",
            f"- validation_error_count: `{summary['validation_error_count']}`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--r30-intake",
        type=Path,
        default=Path("results/B1_B7_cone01_R30_o3_f4_c2_strict_replay_row_intake_gate_v0.json"),
    )
    parser.add_argument(
        "--c2-template",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/"
            "B1-B7-cone01-O3-F4-C2-strict-replay-rows.template.json"
        ),
    )
    parser.add_argument(
        "--fixture-output",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/"
            "B1-B7-cone01-O3-F4-C2-numeric-only-overclaim.fixture.json"
        ),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_R31_o3_f4_c2_numeric_only_overclaim_sentinel_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_R31_o3_f4_c2_numeric_only_overclaim_sentinel_gate.md"),
    )
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload, fixture = build_payload(args)
    write_json(args.fixture_output, fixture, pretty=True)
    write_json(args.json_output, payload, pretty=True)
    write_markdown(args.markdown_output, payload)
    if args.pretty:
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "requirements_passed": payload["summary"]["requirements_passed"],
                    "requirements_failed": payload["summary"]["requirements_failed"],
                    "fixture_hash": payload["summary"]["fixture_hash"],
                    "fixture_row_table_hash": payload["summary"]["fixture_row_table_hash"],
                    "preflight_hash": payload["summary"]["preflight_hash"],
                    "surface_pass": payload["summary"]["surface_pass"],
                    "evidence_pass": payload["summary"]["evidence_pass"],
                    "numeric_replay_error_count": payload["summary"][
                        "numeric_replay_error_count"
                    ],
                    "tolerance_pass_count": payload["summary"]["tolerance_pass_count"],
                    "invalid_hash_cell_count": payload["summary"]["invalid_hash_cell_count"],
                    "c2_strict_replay_rows_accepted": payload["summary"][
                        "c2_strict_replay_rows_accepted"
                    ],
                    "o3_closed": payload["summary"]["o3_closed"],
                    "reroute_allowed": payload["summary"]["reroute_allowed"],
                    "b7_credit_delta": payload["summary"]["b7_credit_delta"],
                    "fixture_output": str(args.fixture_output),
                    "json_output": str(args.json_output),
                    "markdown_output": str(args.markdown_output),
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
