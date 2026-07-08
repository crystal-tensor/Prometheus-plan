#!/usr/bin/env python3
"""T-B1-004en/T-B7-013w: R38 O3-F4 C2 source-backed discriminator gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r38_o3_f4_c2_source_backed_discriminator_gate_v0"
STATUS = "cone01_r38_o3_f4_c2_source_backed_discriminator_rejects_smoke"
MODEL_STATUS = "o3_f4_c2_source_backed_discriminator_ready_no_c2_acceptance"
VERSION = "0.1"
TARGET_ID = "T-B1-004en/T-B7-013w"
UPSTREAM_TARGET_ID = "T-B1-004em/T-B7-013v"
FAMILY_ID = "O3-F4"
CANDIDATE_ID = "NL-C02"
STRICT_TOLERANCE = 1.0e-8
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FILE_ARTIFACT_FIELDS = [
    "replay_stdout_file",
    "source_circuit_file",
    "candidate_circuit_file",
    "same_unitary_witness_file",
]
SOURCE_BACKED_REQUIRED_FIELDS = [
    "source_backed_replay",
    "same_unitary_certificate",
    "smoke_only_not_c2_acceptance",
    "source_dataset_id",
    "source_dataset_sha256",
    "source_trace_id",
    "source_trace_sha256",
    "replay_environment_sha256",
    "same_unitary_witness_schema",
    "same_unitary_witness_verifier",
]


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


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def requirement(
    requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def build_replacement_contract(r37: dict[str, Any], r33: dict[str, Any]) -> dict[str, Any]:
    r33_contract = r33["o3_f4_c2_provenance_binding_contract_packet"]["contract"]
    contract = {
        "contract_id": "B1-B7-cone01-O3-F4-C2-source-backed-replacement-contract",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "candidate_id": CANDIDATE_ID,
        "family_id": FAMILY_ID,
        "strict_tolerance": STRICT_TOLERANCE,
        "required_row_count": 8,
        "source_r33_contract_hash": r33_contract["contract_hash"],
        "source_r37_preflight_hash": r37["summary"]["preflight_hash"],
        "source_r37_fixture_hash": r37["summary"]["fixture_hash"],
        "inherited_binding_fields": r33_contract["binding_fields"],
        "required_execution_artifacts": r33_contract["required_execution_artifacts"],
        "file_artifact_fields": FILE_ARTIFACT_FIELDS,
        "source_backed_required_fields": SOURCE_BACKED_REQUIRED_FIELDS,
        "hard_reject_if": [
            "smoke_only_not_c2_acceptance is true",
            "source_backed_replay is not true",
            "same_unitary_certificate is not true",
            "any source-backed provenance hash is missing or invalid",
            "any materialized file is missing or hash-mismatched",
            "same-unitary witness schema is not source_backed_unitary_equivalence_v1",
            "zero-credit claim boundary is missing before C2 acceptance",
        ],
        "acceptance_statement": (
            "C2 can only become accepted after all 8 rows are materialized, "
            "source-backed, same-unitary-certified, hash-matched, provenance-bound, "
            "within strict tolerance, and still zero-credit before downstream gates."
        ),
    }
    contract["contract_hash"] = stable_hash(contract)
    return contract


def verify_materialized_files(row: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    artifacts = row.get("execution_artifacts", {})
    results = []
    for field in FILE_ARTIFACT_FIELDS:
        path_value = artifacts.get(field)
        expected_hash = artifacts.get(field.replace("_file", "_hash"))
        path = root / path_value if isinstance(path_value, str) else None
        exists = bool(path and path.exists() and path.is_file())
        actual_hash = file_hash(path) if exists else None
        results.append(
            {
                "field": field,
                "path": path_value,
                "exists": exists,
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
                "hash_matches": exists and actual_hash == expected_hash,
            }
        )
    return results


def verify_row(row: dict[str, Any], contract: dict[str, Any], root: Path) -> dict[str, Any]:
    artifacts = row.get("execution_artifacts", {})
    binding_payload = row.get("binding_payload", {})
    file_results = verify_materialized_files(row, root)
    missing_source_fields = [
        field for field in contract["source_backed_required_fields"] if field not in row
    ]
    invalid_source_hash_fields = [
        field
        for field in [
            "source_dataset_sha256",
            "source_trace_sha256",
            "replay_environment_sha256",
        ]
        if field in row and not is_sha256(row.get(field))
    ]
    binding_hash_matches = (
        row.get("declared_provenance_binding_hash") == stable_hash(binding_payload)
        and artifacts.get("provenance_binding_hash")
        == row.get("declared_provenance_binding_hash")
    )
    try:
        replay_error = float(row.get("max_unitary_replay_error"))
        replay_error_within_tolerance = replay_error <= STRICT_TOLERANCE
    except (TypeError, ValueError):
        replay_error = None
        replay_error_within_tolerance = False
    materialized_files_passed = all(
        item["exists"] and item["hash_matches"] for item in file_results
    )
    source_backed_flags_passed = (
        row.get("source_backed_replay") is True
        and row.get("same_unitary_certificate") is True
        and row.get("smoke_only_not_c2_acceptance") is False
    )
    witness_schema_passed = (
        row.get("same_unitary_witness_schema")
        == "source_backed_unitary_equivalence_v1"
        and isinstance(row.get("same_unitary_witness_verifier"), str)
        and row.get("same_unitary_witness_verifier") != ""
    )
    source_provenance_passed = (
        not missing_source_fields and not invalid_source_hash_fields
    )
    zero_credit_boundary_present = all(
        token in str(row.get("claim_boundary", ""))
        for token in ["no C2", "O3", "reroute", "B7", "STV"]
    )
    accepted = (
        materialized_files_passed
        and binding_hash_matches
        and replay_error_within_tolerance
        and source_backed_flags_passed
        and witness_schema_passed
        and source_provenance_passed
        and zero_credit_boundary_present
    )
    failed_reasons = []
    if not materialized_files_passed:
        failed_reasons.append("materialized_file_missing_or_hash_mismatch")
    if not binding_hash_matches:
        failed_reasons.append("provenance_binding_hash_mismatch")
    if not replay_error_within_tolerance:
        failed_reasons.append("replay_error_not_within_tolerance")
    if not source_backed_flags_passed:
        failed_reasons.append("source_backed_flags_not_satisfied")
    if not witness_schema_passed:
        failed_reasons.append("same_unitary_witness_schema_or_verifier_missing")
    if not source_provenance_passed:
        failed_reasons.append("source_backed_provenance_missing_or_invalid")
    if not zero_credit_boundary_present:
        failed_reasons.append("zero_credit_boundary_missing")
    return {
        "challenge_id": row.get("challenge_id"),
        "accepted": accepted,
        "failed_reasons": failed_reasons,
        "materialized_files_passed": materialized_files_passed,
        "file_results": file_results,
        "binding_hash_matches": binding_hash_matches,
        "max_unitary_replay_error": replay_error,
        "replay_error_within_tolerance": replay_error_within_tolerance,
        "source_backed_flags_passed": source_backed_flags_passed,
        "source_backed_replay": row.get("source_backed_replay") is True,
        "same_unitary_certificate": row.get("same_unitary_certificate") is True,
        "smoke_only_not_c2_acceptance": row.get("smoke_only_not_c2_acceptance") is True,
        "missing_source_fields": missing_source_fields,
        "invalid_source_hash_fields": invalid_source_hash_fields,
        "witness_schema_passed": witness_schema_passed,
        "source_provenance_passed": source_provenance_passed,
        "zero_credit_boundary_present": zero_credit_boundary_present,
    }


def evaluate_fixture(
    fixture: dict[str, Any], contract: dict[str, Any], root: Path, fixture_path: Path
) -> dict[str, Any]:
    row_results = [verify_row(row, contract, root) for row in fixture.get("rows", [])]
    evaluation = {
        "input_artifact": str(fixture_path),
        "input_artifact_sha256": file_hash(fixture_path),
        "fixture_hash": fixture.get("fixture_hash"),
        "contract_hash": contract["contract_hash"],
        "row_count": len(row_results),
        "required_row_count": contract["required_row_count"],
        "row_results": row_results,
        "materialized_rows_passed": sum(
            1 for row in row_results if row["materialized_files_passed"]
        ),
        "source_backed_rows_passed": sum(
            1 for row in row_results if row["accepted"]
        ),
        "smoke_only_row_count": sum(
            1 for row in row_results if row["smoke_only_not_c2_acceptance"]
        ),
        "source_backed_flag_failures": sum(
            1 for row in row_results if not row["source_backed_flags_passed"]
        ),
        "source_provenance_failures": sum(
            1 for row in row_results if not row["source_provenance_passed"]
        ),
        "witness_schema_failures": sum(
            1 for row in row_results if not row["witness_schema_passed"]
        ),
        "binding_mismatch_count": sum(
            1 for row in row_results if not row["binding_hash_matches"]
        ),
        "accepted": False,
    }
    evaluation["accepted"] = (
        evaluation["row_count"] == evaluation["required_row_count"]
        and evaluation["source_backed_rows_passed"] == evaluation["required_row_count"]
        and fixture.get("o3_closed") is False
        and fixture.get("reroute_allowed") is False
        and fixture.get("b7_credit_delta") == 0
    )
    evaluation["failed_reasons"] = []
    if evaluation["smoke_only_row_count"]:
        evaluation["failed_reasons"].append("smoke_rows_present")
    if evaluation["source_backed_flag_failures"]:
        evaluation["failed_reasons"].append("source_backed_flags_not_satisfied")
    if evaluation["source_provenance_failures"]:
        evaluation["failed_reasons"].append("source_backed_provenance_missing_or_invalid")
    if evaluation["witness_schema_failures"]:
        evaluation["failed_reasons"].append("same_unitary_witness_schema_or_verifier_missing")
    if evaluation["binding_mismatch_count"]:
        evaluation["failed_reasons"].append("provenance_binding_hash_mismatch")
    evaluation["discriminator_hash"] = stable_hash(evaluation)
    return evaluation


def build_payload(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.time()
    r37 = load_json(args.r37_result)
    r33 = load_json(args.r33_contract)
    fixture = load_json(args.fixture_input)
    contract = build_replacement_contract(r37, r33)
    write_json(args.contract_output, contract, pretty=True)
    evaluation = evaluate_fixture(fixture, contract, args.root, args.fixture_input)
    requirements = [
        requirement(
            "S1",
            "R37 source gate is validation-clean and all rows are materialized",
            r37["summary"].get("validation_error_count") == 0
            and r37["summary"].get("materialized_rows_passed") == 8
            and r37["summary"].get("missing_materialized_file_count") == 0,
            {
                "r37_validation_error_count": r37["summary"].get(
                    "validation_error_count"
                ),
                "r37_materialized_rows_passed": r37["summary"].get(
                    "materialized_rows_passed"
                ),
                "r37_missing_materialized_file_count": r37["summary"].get(
                    "missing_materialized_file_count"
                ),
            },
        ),
        requirement(
            "S2",
            "R38 emits a source-backed replacement contract",
            contract["required_row_count"] == 8
            and len(contract["source_backed_required_fields"]) == len(
                SOURCE_BACKED_REQUIRED_FIELDS
            ),
            {
                "contract_hash": contract["contract_hash"],
                "source_backed_required_field_count": len(
                    contract["source_backed_required_fields"]
                ),
            },
        ),
        requirement(
            "S3",
            "Current R37 fixture remains fully materialized under R38",
            evaluation["materialized_rows_passed"] == 8,
            {"materialized_rows_passed": evaluation["materialized_rows_passed"]},
        ),
        requirement(
            "S4",
            "R38 rejects every current row as non-source-backed smoke",
            evaluation["source_backed_rows_passed"] == 0
            and evaluation["smoke_only_row_count"] == 8
            and evaluation["accepted"] is False,
            {
                "source_backed_rows_passed": evaluation["source_backed_rows_passed"],
                "smoke_only_row_count": evaluation["smoke_only_row_count"],
                "accepted": evaluation["accepted"],
                "failed_reasons": evaluation["failed_reasons"],
            },
        ),
        requirement(
            "S5",
            "Source-backed provenance and witness requirements are enforced",
            evaluation["source_provenance_failures"] == 8
            and evaluation["witness_schema_failures"] == 8,
            {
                "source_provenance_failures": evaluation[
                    "source_provenance_failures"
                ],
                "witness_schema_failures": evaluation["witness_schema_failures"],
            },
        ),
        requirement(
            "S6",
            "Existing provenance binding still recomputes for smoke rows",
            evaluation["binding_mismatch_count"] == 0,
            {"binding_mismatch_count": evaluation["binding_mismatch_count"]},
        ),
        requirement(
            "S7",
            "R38 preserves zero-credit B1/B7 boundaries",
            fixture.get("o3_closed") is False
            and fixture.get("reroute_allowed") is False
            and fixture.get("b7_credit_delta") == 0,
            {
                "o3_closed": fixture.get("o3_closed"),
                "reroute_allowed": fixture.get("reroute_allowed"),
                "b7_credit_delta": fixture.get("b7_credit_delta"),
            },
        ),
        requirement(
            "S8",
            "R38 claims no C3-C7 or B7 ledger progress",
            True,
            {
                "c3_c7_progress_claimed": False,
                "b7_ledger_credit_claimed": False,
            },
        ),
    ]
    failed_requirements = [
        item["requirement_id"] for item in requirements if not item["passed"]
    ]
    summary = {
        "candidate_id": CANDIDATE_ID,
        "family_id": FAMILY_ID,
        "source_r37_preflight_hash": r37["summary"]["preflight_hash"],
        "source_r37_fixture_hash": r37["summary"]["fixture_hash"],
        "source_r37_file_sha256": file_hash(args.r37_result),
        "source_r33_contract_hash": contract["source_r33_contract_hash"],
        "replacement_contract_hash": contract["contract_hash"],
        "replacement_contract_file_sha256": file_hash(args.contract_output),
        "discriminator_hash": evaluation["discriminator_hash"],
        "strict_tolerance": STRICT_TOLERANCE,
        "template_row_count": evaluation["row_count"],
        "materialized_rows_passed": evaluation["materialized_rows_passed"],
        "source_backed_rows_passed": evaluation["source_backed_rows_passed"],
        "smoke_only_row_count": evaluation["smoke_only_row_count"],
        "source_backed_flag_failures": evaluation["source_backed_flag_failures"],
        "source_provenance_failures": evaluation["source_provenance_failures"],
        "witness_schema_failures": evaluation["witness_schema_failures"],
        "binding_mismatch_count": evaluation["binding_mismatch_count"],
        "source_backed_discriminator_ready": True,
        "all_rows_materialized_smoke_ready": True,
        "artifact_materialization_gate_ready": True,
        "binding_preflight_verifier_ready": True,
        "c2_provenance_binding_contract_ready": True,
        "c2_source_backed_replacement_contract_ready": True,
        "c2_provenance_submission_accepted": False,
        "c2_strict_replay_rows_accepted": False,
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
            "replace_8_smoke_rows_with_source_backed_replay_outputs",
            "provide_source_dataset_and_trace_hashes_for_all_rows",
            "provide_same_unitary_witness_schema_and_verifier_for_all_rows",
            "pass_C2_source_backed_discriminator_for_all_rows",
            "C3_same_unitary_replay_certificate",
            "C4_C5_same_access_denominator_comparison",
            "C6_leakage_free_optimizer_trace",
            "C7_machine_check_replay_bundle",
        ],
        "remaining_open_obligation_count": 8,
        "requirement_count": len(requirements),
        "requirements_passed": len(requirements) - len(failed_requirements),
        "requirements_failed": len(failed_requirements),
        "failed_requirement_ids": failed_requirements,
        "validation_error_count": len(failed_requirements),
    }
    payload = {
        "title": "B1/B7 Cone01 R38 O3-F4 C2 Source-Backed Discriminator Gate",
        "version": VERSION,
        "last_updated": "2026-07-08",
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "o3_f4_c2_source_backed_discriminator_packet": {
            "source_r37_result": str(args.r37_result),
            "source_r33_contract": str(args.r33_contract),
            "fixture_input": str(args.fixture_input),
            "replacement_contract_output": str(args.contract_output),
            "replacement_contract": contract,
            "evaluation": evaluation,
        },
        "requirements": requirements,
        "summary": summary,
        "claim_boundary": {
            "what_is_supported": (
                "R38 defines and runs the source-backed C2 discriminator. It proves "
                "the current all-row materialized R37 fixture is still rejected "
                "because every row is smoke-only and lacks source-backed provenance "
                "plus same-unitary witness schema/verifier evidence."
            ),
            "what_is_not_supported": (
                "R38 does not accept C2, does not replace any smoke row with real "
                "source-backed replay, does not close O3, and does not permit reroute, "
                "B7 credit, STV credit, or resource-saving claims."
            ),
            "next_gate": (
                "Submit at least one row that satisfies the source-backed replacement "
                "contract, then scale to all 8 rows before C3-C7."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": failed_requirements,
        "runtime_seconds": round(time.time() - started, 6),
    }
    return payload, contract


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone01 R38 O3-F4 C2 Source-Backed Discriminator Gate",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Upstream target: `{payload['upstream_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Replacement contract hash: `{summary['replacement_contract_hash']}`",
        f"- Discriminator hash: `{summary['discriminator_hash']}`",
        "",
        "## Result",
        "",
        (
            f"R38 passes {summary['requirements_passed']}/"
            f"{summary['requirement_count']} requirements by proving that all 8 "
            "R37 materialized rows are still non-source-backed smoke rows."
        ),
        "",
        "## Rejection Surface",
        "",
        f"- Materialized rows passed: `{summary['materialized_rows_passed']}`",
        f"- Source-backed rows passed: `{summary['source_backed_rows_passed']}`",
        f"- Smoke-only rows: `{summary['smoke_only_row_count']}`",
        f"- Source-backed flag failures: `{summary['source_backed_flag_failures']}`",
        f"- Source provenance failures: `{summary['source_provenance_failures']}`",
        f"- Witness schema failures: `{summary['witness_schema_failures']}`",
        f"- Binding mismatch count: `{summary['binding_mismatch_count']}`",
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
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--r37-result",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_R37_o3_f4_c2_all_rows_materialized_smoke_gate_v0.json"
        ),
    )
    parser.add_argument(
        "--r33-contract",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_R33_o3_f4_c2_provenance_binding_contract_gate_v0.json"
        ),
    )
    parser.add_argument(
        "--fixture-input",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/"
            "B1-B7-cone01-O3-F4-C2-all-rows-materialized-smoke.fixture.json"
        ),
    )
    parser.add_argument(
        "--contract-output",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/"
            "B1-B7-cone01-O3-F4-C2-source-backed-replacement.contract.json"
        ),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_R38_o3_f4_c2_source_backed_discriminator_gate_v0.json"
        ),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path(
            "research/B1_B7_cone01_R38_o3_f4_c2_source_backed_discriminator_gate.md"
        ),
    )
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload, _contract = build_payload(args)
    write_json(args.json_output, payload, pretty=True)
    write_markdown(args.markdown_output, payload)
    if args.pretty:
        summary = payload["summary"]
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "replacement_contract_hash": summary[
                        "replacement_contract_hash"
                    ],
                    "discriminator_hash": summary["discriminator_hash"],
                    "requirements_passed": summary["requirements_passed"],
                    "requirements_failed": summary["requirements_failed"],
                    "materialized_rows_passed": summary["materialized_rows_passed"],
                    "source_backed_rows_passed": summary[
                        "source_backed_rows_passed"
                    ],
                    "smoke_only_row_count": summary["smoke_only_row_count"],
                    "source_provenance_failures": summary[
                        "source_provenance_failures"
                    ],
                    "witness_schema_failures": summary["witness_schema_failures"],
                    "c2_strict_replay_rows_accepted": summary[
                        "c2_strict_replay_rows_accepted"
                    ],
                    "o3_closed": summary["o3_closed"],
                    "reroute_allowed": summary["reroute_allowed"],
                    "b7_credit_delta": summary["b7_credit_delta"],
                    "json_output": str(args.json_output),
                    "contract_output": str(args.contract_output),
                    "markdown_output": str(args.markdown_output),
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
