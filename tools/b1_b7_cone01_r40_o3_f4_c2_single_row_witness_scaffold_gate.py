#!/usr/bin/env python3
"""T-B1-004ep/T-B7-013y: R40 O3-F4 C2 single-row witness scaffold gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r40_o3_f4_c2_single_row_witness_scaffold_gate_v0"
STATUS = "cone01_r40_o3_f4_c2_single_row_witness_scaffold_partial_rejected"
MODEL_STATUS = "o3_f4_c2_single_row_witness_schema_ready_no_c2_acceptance"
VERSION = "0.1"
TARGET_ID = "T-B1-004ep/T-B7-013y"
UPSTREAM_TARGET_ID = "T-B1-004eo/T-B7-013x"
FAMILY_ID = "O3-F4"
CANDIDATE_ID = "NL-C02"
CHALLENGE_ID = "O3-F4-C01"
STRICT_TOLERANCE = 1.0e-8
WITNESS_SCHEMA = "source_backed_unitary_equivalence_v1"
WITNESS_VERIFIER = "r40_schema_dry_run_verifier_not_certificate"
FILE_ARTIFACT_FIELDS = [
    "replay_stdout_file",
    "source_circuit_file",
    "candidate_circuit_file",
    "same_unitary_witness_file",
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


def requirement(
    requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def verify_materialized_files(row: dict[str, Any], root: Path) -> bool:
    artifacts = row.get("execution_artifacts", {})
    for field in FILE_ARTIFACT_FIELDS:
        path_value = artifacts.get(field)
        expected_hash = artifacts.get(field.replace("_file", "_hash"))
        path = root / path_value if isinstance(path_value, str) else None
        if not path or not path.exists() or not path.is_file():
            return False
        if file_hash(path) != expected_hash:
            return False
    return True


def row_source_provenance_passed(row: dict[str, Any], root: Path) -> bool:
    for file_field, hash_field in [
        ("source_dataset_file", "source_dataset_sha256"),
        ("source_trace_file", "source_trace_sha256"),
        ("replay_environment_file", "replay_environment_sha256"),
    ]:
        path_value = row.get(file_field)
        expected_hash = row.get(hash_field)
        path = root / path_value if isinstance(path_value, str) else None
        if not path or not path.exists() or not path.is_file():
            return False
        if file_hash(path) != expected_hash:
            return False
    return bool(row.get("source_dataset_id")) and bool(row.get("source_trace_id"))


def write_witness_scaffold_files(
    root: Path, output_dir: Path, row: dict[str, Any]
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    schema = {
        "artifact": "R40 same-unitary witness schema scaffold",
        "challenge_id": CHALLENGE_ID,
        "schema": WITNESS_SCHEMA,
        "scope": "schema_only_not_same_unitary_certificate",
        "required_witness_fields": [
            "source_circuit_sha256",
            "candidate_circuit_sha256",
            "unitary_distance_metric",
            "strict_tolerance",
            "max_unitary_replay_error",
            "verifier_command",
            "source_dataset_sha256",
            "source_trace_sha256",
        ],
        "source_dataset_sha256": row["source_dataset_sha256"],
        "source_trace_sha256": row["source_trace_sha256"],
        "strict_tolerance": STRICT_TOLERANCE,
    }
    verifier = {
        "artifact": "R40 dry-run witness verifier scaffold",
        "challenge_id": CHALLENGE_ID,
        "verifier": WITNESS_VERIFIER,
        "scope": "checks_schema_shape_only_not_unitary_equivalence",
        "acceptance_disabled_until": [
            "source_backed_replay_true",
            "same_unitary_certificate_true",
            "non_smoke_witness_file",
            "replay_command_executable",
        ],
        "dry_run_checks": [
            "schema string present",
            "verifier name present",
            "source provenance hashes match files",
            "zero-credit claim boundary remains present",
        ],
    }
    files = {
        f"{CHALLENGE_ID}.witness_schema.json": schema,
        f"{CHALLENGE_ID}.witness_verifier.json": verifier,
    }
    result: dict[str, Any] = {}
    for name, payload in files.items():
        path = output_dir / name
        write_json(path, payload, pretty=True)
        key = name.replace(f"{CHALLENGE_ID}.", "").replace(".json", "")
        result[f"{key}_file"] = str(path.relative_to(root))
        result[f"{key}_sha256"] = file_hash(path)
    return result


def augment_fixture(
    fixture: dict[str, Any], root: Path, witness_dir: Path
) -> dict[str, Any]:
    rows = []
    for row in fixture["rows"]:
        new_row = json.loads(json.dumps(row))
        if new_row.get("challenge_id") == CHALLENGE_ID:
            witness = write_witness_scaffold_files(root, witness_dir, new_row)
            new_row.update(
                {
                    "same_unitary_witness_schema": WITNESS_SCHEMA,
                    "same_unitary_witness_verifier": WITNESS_VERIFIER,
                    "same_unitary_witness_schema_file": witness["witness_schema_file"],
                    "same_unitary_witness_schema_sha256": witness[
                        "witness_schema_sha256"
                    ],
                    "same_unitary_witness_verifier_file": witness[
                        "witness_verifier_file"
                    ],
                    "same_unitary_witness_verifier_sha256": witness[
                        "witness_verifier_sha256"
                    ],
                    "source_backed_replay": False,
                    "same_unitary_certificate": False,
                    "smoke_only_not_c2_acceptance": True,
                }
            )
        rows.append(new_row)
    augmented = {
        "artifact_id": "B1-B7-cone01-O3-F4-C2-single-row-witness-scaffold.fixture",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_fixture_hash": fixture["fixture_hash"],
        "contract_hash": fixture["contract_hash"],
        "strict_tolerance": STRICT_TOLERANCE,
        "rows": rows,
        "o3_closed": False,
        "reroute_allowed": False,
        "b7_credit_delta": 0,
    }
    augmented["fixture_hash"] = stable_hash(augmented)
    return augmented


def row_witness_schema_passed(row: dict[str, Any], root: Path) -> bool:
    if row.get("same_unitary_witness_schema") != WITNESS_SCHEMA:
        return False
    if row.get("same_unitary_witness_verifier") != WITNESS_VERIFIER:
        return False
    for file_field, hash_field in [
        ("same_unitary_witness_schema_file", "same_unitary_witness_schema_sha256"),
        (
            "same_unitary_witness_verifier_file",
            "same_unitary_witness_verifier_sha256",
        ),
    ]:
        path_value = row.get(file_field)
        expected_hash = row.get(hash_field)
        path = root / path_value if isinstance(path_value, str) else None
        if not path or not path.exists() or not path.is_file():
            return False
        if file_hash(path) != expected_hash:
            return False
    return True


def evaluate_fixture(fixture: dict[str, Any], root: Path, fixture_path: Path) -> dict[str, Any]:
    row_results = []
    for row in fixture["rows"]:
        provenance_passed = row_source_provenance_passed(row, root)
        witness_schema_passed = row_witness_schema_passed(row, root)
        source_backed_flags_passed = (
            row.get("source_backed_replay") is True
            and row.get("same_unitary_certificate") is True
            and row.get("smoke_only_not_c2_acceptance") is False
        )
        materialized_files_passed = verify_materialized_files(row, root)
        accepted = (
            materialized_files_passed
            and provenance_passed
            and witness_schema_passed
            and source_backed_flags_passed
        )
        failed_reasons = []
        if not provenance_passed:
            failed_reasons.append("source_provenance_missing_or_hash_mismatch")
        if not witness_schema_passed:
            failed_reasons.append("same_unitary_witness_schema_or_verifier_missing")
        if not source_backed_flags_passed:
            failed_reasons.append("source_backed_flags_not_satisfied")
        row_results.append(
            {
                "challenge_id": row["challenge_id"],
                "materialized_files_passed": materialized_files_passed,
                "source_provenance_passed": provenance_passed,
                "witness_schema_passed": witness_schema_passed,
                "source_backed_flags_passed": source_backed_flags_passed,
                "source_backed_replay": row.get("source_backed_replay") is True,
                "same_unitary_certificate": row.get("same_unitary_certificate") is True,
                "smoke_only_not_c2_acceptance": row.get(
                    "smoke_only_not_c2_acceptance"
                )
                is True,
                "accepted": accepted,
                "failed_reasons": failed_reasons,
            }
        )
    evaluation = {
        "input_artifact": str(fixture_path),
        "input_artifact_sha256": file_hash(fixture_path),
        "fixture_hash": fixture["fixture_hash"],
        "row_count": len(row_results),
        "row_results": row_results,
        "materialized_rows_passed": sum(
            1 for row in row_results if row["materialized_files_passed"]
        ),
        "source_provenance_rows_passed": sum(
            1 for row in row_results if row["source_provenance_passed"]
        ),
        "source_provenance_failures": sum(
            1 for row in row_results if not row["source_provenance_passed"]
        ),
        "witness_schema_rows_passed": sum(
            1 for row in row_results if row["witness_schema_passed"]
        ),
        "witness_schema_failures": sum(
            1 for row in row_results if not row["witness_schema_passed"]
        ),
        "source_backed_rows_passed": sum(1 for row in row_results if row["accepted"]),
        "source_backed_flag_failures": sum(
            1 for row in row_results if not row["source_backed_flags_passed"]
        ),
        "smoke_only_row_count": sum(
            1 for row in row_results if row["smoke_only_not_c2_acceptance"]
        ),
        "accepted": False,
    }
    evaluation["accepted"] = (
        evaluation["source_backed_rows_passed"] == 8
        and fixture.get("o3_closed") is False
        and fixture.get("reroute_allowed") is False
        and fixture.get("b7_credit_delta") == 0
    )
    evaluation["evaluation_hash"] = stable_hash(evaluation)
    return evaluation


def build_payload(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.time()
    r39 = load_json(args.r39_result)
    source_fixture = load_json(args.r39_fixture)
    augmented_fixture = augment_fixture(source_fixture, args.root, args.witness_dir)
    write_json(args.fixture_output, augmented_fixture, pretty=True)
    evaluation = evaluate_fixture(augmented_fixture, args.root, args.fixture_output)
    requirements = [
        requirement(
            "S1",
            "R39 source-provenance gate is validation-clean with one provenance row",
            r39["summary"].get("validation_error_count") == 0
            and r39["summary"].get("source_provenance_rows_passed") == 1
            and r39["summary"].get("witness_schema_failures") == 8,
            {
                "r39_validation_error_count": r39["summary"].get(
                    "validation_error_count"
                ),
                "r39_source_provenance_rows_passed": r39["summary"].get(
                    "source_provenance_rows_passed"
                ),
                "r39_witness_schema_failures": r39["summary"].get(
                    "witness_schema_failures"
                ),
            },
        ),
        requirement(
            "S2",
            "R40 emits witness schema and dry-run verifier files for one row",
            evaluation["witness_schema_rows_passed"] == 1
            and evaluation["witness_schema_failures"] == 7,
            {
                "witness_schema_rows_passed": evaluation[
                    "witness_schema_rows_passed"
                ],
                "witness_schema_failures": evaluation["witness_schema_failures"],
            },
        ),
        requirement(
            "S3",
            "The enriched row keeps source provenance intact",
            evaluation["source_provenance_rows_passed"] == 1
            and evaluation["source_provenance_failures"] == 7,
            {
                "source_provenance_rows_passed": evaluation[
                    "source_provenance_rows_passed"
                ],
                "source_provenance_failures": evaluation[
                    "source_provenance_failures"
                ],
            },
        ),
        requirement(
            "S4",
            "All materialized C2 files remain hash-valid",
            evaluation["materialized_rows_passed"] == 8,
            {"materialized_rows_passed": evaluation["materialized_rows_passed"]},
        ),
        requirement(
            "S5",
            "R40 does not claim source-backed replay or same-unitary acceptance",
            evaluation["source_backed_rows_passed"] == 0
            and evaluation["source_backed_flag_failures"] == 8,
            {
                "source_backed_rows_passed": evaluation["source_backed_rows_passed"],
                "source_backed_flag_failures": evaluation[
                    "source_backed_flag_failures"
                ],
            },
        ),
        requirement(
            "S6",
            "R40 keeps C2/O3/reroute/B7 zero-credit boundaries",
            augmented_fixture.get("o3_closed") is False
            and augmented_fixture.get("reroute_allowed") is False
            and augmented_fixture.get("b7_credit_delta") == 0,
            {
                "o3_closed": augmented_fixture.get("o3_closed"),
                "reroute_allowed": augmented_fixture.get("reroute_allowed"),
                "b7_credit_delta": augmented_fixture.get("b7_credit_delta"),
            },
        ),
        requirement(
            "S7",
            "R40 claims no C3-C7 or ledger progress",
            True,
            {"c3_c7_progress_claimed": False, "b7_ledger_credit_claimed": False},
        ),
        requirement(
            "S8",
            "R40 output is hash-bound",
            bool(augmented_fixture["fixture_hash"]) and bool(evaluation["evaluation_hash"]),
            {
                "fixture_hash": augmented_fixture["fixture_hash"],
                "evaluation_hash": evaluation["evaluation_hash"],
            },
        ),
    ]
    failed_requirements = [
        item["requirement_id"] for item in requirements if not item["passed"]
    ]
    summary = {
        "candidate_id": CANDIDATE_ID,
        "family_id": FAMILY_ID,
        "challenge_id": CHALLENGE_ID,
        "source_r39_evaluation_hash": r39["summary"]["evaluation_hash"],
        "source_r39_fixture_hash": r39["summary"][
            "single_row_source_provenance_fixture_hash"
        ],
        "source_r39_file_sha256": file_hash(args.r39_result),
        "single_row_witness_scaffold_fixture_hash": augmented_fixture["fixture_hash"],
        "single_row_witness_scaffold_fixture_file_sha256": file_hash(
            args.fixture_output
        ),
        "evaluation_hash": evaluation["evaluation_hash"],
        "strict_tolerance": STRICT_TOLERANCE,
        "template_row_count": evaluation["row_count"],
        "materialized_rows_passed": evaluation["materialized_rows_passed"],
        "source_provenance_rows_passed": evaluation["source_provenance_rows_passed"],
        "source_provenance_failures": evaluation["source_provenance_failures"],
        "witness_schema_rows_passed": evaluation["witness_schema_rows_passed"],
        "witness_schema_failures": evaluation["witness_schema_failures"],
        "source_backed_rows_passed": evaluation["source_backed_rows_passed"],
        "source_backed_flag_failures": evaluation["source_backed_flag_failures"],
        "smoke_only_row_count": evaluation["smoke_only_row_count"],
        "single_row_witness_scaffold_ready": True,
        "single_row_source_provenance_ready": True,
        "source_backed_discriminator_ready": True,
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
            "turn_R40_schema_dry_run_into_real_same_unitary_verifier",
            "replace_smoke_flags_with_real_source_backed_replay_flags",
            "provide_source_provenance_for_remaining_7_rows",
            "provide_witness_schema_and_verifier_for_remaining_7_rows",
            "pass_C2_source_backed_discriminator_for_all_rows",
            "C3_same_unitary_replay_certificate",
            "C4_C5_same_access_denominator_comparison",
            "C6_leakage_free_optimizer_trace",
            "C7_machine_check_replay_bundle",
        ],
        "remaining_open_obligation_count": 9,
        "requirement_count": len(requirements),
        "requirements_passed": len(requirements) - len(failed_requirements),
        "requirements_failed": len(failed_requirements),
        "failed_requirement_ids": failed_requirements,
        "validation_error_count": len(failed_requirements),
    }
    payload = {
        "title": "B1/B7 Cone01 R40 O3-F4 C2 Single-Row Witness Scaffold Gate",
        "version": VERSION,
        "last_updated": "2026-07-08",
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "o3_f4_c2_single_row_witness_scaffold_packet": {
            "source_r39_result": str(args.r39_result),
            "source_r39_fixture": str(args.r39_fixture),
            "witness_dir": str(args.witness_dir),
            "fixture_output": str(args.fixture_output),
            "evaluation": evaluation,
        },
        "requirements": requirements,
        "summary": summary,
        "claim_boundary": {
            "what_is_supported": (
                "R40 adds a hash-verifiable witness schema and dry-run verifier "
                "scaffold for one C2 row, reducing witness-schema failures from "
                "8 to 7 while preserving the R39 source-provenance packet."
            ),
            "what_is_not_supported": (
                "R40 does not turn the dry-run verifier into a real same-unitary "
                "certificate, does not mark the row source-backed, does not accept "
                "C2, does not close O3, and does not permit reroute, B7 credit, "
                "STV credit, or resource-saving claims."
            ),
            "next_gate": (
                "Turn the dry-run schema scaffold into a real same-unitary verifier "
                "for O3-F4-C01, then replace smoke flags with source-backed replay "
                "flags and repeat provenance/witness packets for the remaining rows."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": failed_requirements,
        "runtime_seconds": round(time.time() - started, 6),
    }
    return payload, augmented_fixture


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone01 R40 O3-F4 C2 Single-Row Witness Scaffold Gate",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Upstream target: `{payload['upstream_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Fixture hash: `{summary['single_row_witness_scaffold_fixture_hash']}`",
        f"- Evaluation hash: `{summary['evaluation_hash']}`",
        "",
        "## Result",
        "",
        (
            f"R40 passes {summary['requirements_passed']}/"
            f"{summary['requirement_count']} requirements by adding one witness "
            "schema/verifier scaffold while keeping C2 rejected."
        ),
        "",
        "## Rejection Surface",
        "",
        f"- Materialized rows passed: `{summary['materialized_rows_passed']}`",
        f"- Source-provenance rows passed: `{summary['source_provenance_rows_passed']}`",
        f"- Witness-schema rows passed: `{summary['witness_schema_rows_passed']}`",
        f"- Witness-schema failures: `{summary['witness_schema_failures']}`",
        f"- Source-backed rows passed: `{summary['source_backed_rows_passed']}`",
        f"- Source-backed flag failures: `{summary['source_backed_flag_failures']}`",
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
        "--r39-result",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_R39_o3_f4_c2_single_row_source_provenance_gate_v0.json"
        ),
    )
    parser.add_argument(
        "--r39-fixture",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/"
            "B1-B7-cone01-O3-F4-C2-single-row-source-provenance.fixture.json"
        ),
    )
    parser.add_argument(
        "--witness-dir",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/"
            "witness_scaffolds/r40_c01"
        ),
    )
    parser.add_argument(
        "--fixture-output",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/"
            "B1-B7-cone01-O3-F4-C2-single-row-witness-scaffold.fixture.json"
        ),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_R40_o3_f4_c2_single_row_witness_scaffold_gate_v0.json"
        ),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path(
            "research/B1_B7_cone01_R40_o3_f4_c2_single_row_witness_scaffold_gate.md"
        ),
    )
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload, _fixture = build_payload(args)
    write_json(args.json_output, payload, pretty=True)
    write_markdown(args.markdown_output, payload)
    if args.pretty:
        summary = payload["summary"]
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "fixture_hash": summary[
                        "single_row_witness_scaffold_fixture_hash"
                    ],
                    "evaluation_hash": summary["evaluation_hash"],
                    "requirements_passed": summary["requirements_passed"],
                    "requirements_failed": summary["requirements_failed"],
                    "source_provenance_rows_passed": summary[
                        "source_provenance_rows_passed"
                    ],
                    "witness_schema_rows_passed": summary[
                        "witness_schema_rows_passed"
                    ],
                    "witness_schema_failures": summary["witness_schema_failures"],
                    "source_backed_rows_passed": summary[
                        "source_backed_rows_passed"
                    ],
                    "c2_strict_replay_rows_accepted": summary[
                        "c2_strict_replay_rows_accepted"
                    ],
                    "o3_closed": summary["o3_closed"],
                    "reroute_allowed": summary["reroute_allowed"],
                    "b7_credit_delta": summary["b7_credit_delta"],
                    "json_output": str(args.json_output),
                    "fixture_output": str(args.fixture_output),
                    "markdown_output": str(args.markdown_output),
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
