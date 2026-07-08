#!/usr/bin/env python3
"""T-B1-004ek/T-B7-013t: R35 O3-F4 C2 artifact materialization sentinel gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r35_o3_f4_c2_artifact_materialization_sentinel_gate_v0"
STATUS = "cone01_r35_o3_f4_c2_artifact_materialization_sentinel_rejected"
MODEL_STATUS = "o3_f4_c2_materialized_artifact_gate_ready_no_c2_acceptance"
VERSION = "0.1"
TARGET_ID = "T-B1-004ek/T-B7-013t"
UPSTREAM_TARGET_ID = "T-B1-004ej/T-B7-013s"
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


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


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


def build_surface_clean_fixture(contract: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for index in range(8):
        challenge_id = f"O3-F4-C{index + 1:02d}"
        replay_stdout_hash = sha256_text(f"{challenge_id}:missing-replay-stdout")
        source_hash = sha256_text(f"{challenge_id}:missing-source-circuit")
        candidate_hash = sha256_text(f"{challenge_id}:missing-candidate-circuit")
        witness_hash = sha256_text(f"{challenge_id}:missing-unitary-witness")
        replay_error = (index + 1) * 1.0e-10
        binding_payload = {
            "challenge_id": challenge_id,
            "parameter_indices": [1381, index],
            "submitted_parameter_values": [f"theta_{index}_a", f"theta_{index}_b"],
            "strict_tolerance": STRICT_TOLERANCE,
            "max_unitary_replay_error": replay_error,
            "unitary_distance_metric": "operator_norm",
            "source_circuit_hash": source_hash,
            "candidate_circuit_hash": candidate_hash,
            "replay_command": (
                "python3 tools/b1_b7_cone01_c2_replay.py "
                f"--challenge-id {challenge_id}"
            ),
            "replay_stdout_hash": replay_stdout_hash,
            "verifier_version": METHOD,
        }
        provenance_binding_hash = stable_hash(binding_payload)
        rows.append(
            {
                "challenge_id": challenge_id,
                "binding_payload": binding_payload,
                "declared_provenance_binding_hash": provenance_binding_hash,
                "execution_artifacts": {
                    "replay_stdout_file": (
                        "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/"
                        f"materialized_artifacts/missing/{challenge_id}.stdout.txt"
                    ),
                    "replay_stdout_hash": replay_stdout_hash,
                    "source_circuit_file": (
                        "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/"
                        f"materialized_artifacts/missing/{challenge_id}.source.qasm"
                    ),
                    "source_circuit_hash": source_hash,
                    "candidate_circuit_file": (
                        "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/"
                        f"materialized_artifacts/missing/{challenge_id}.candidate.qasm"
                    ),
                    "candidate_circuit_hash": candidate_hash,
                    "same_unitary_witness_file": (
                        "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/"
                        f"materialized_artifacts/missing/{challenge_id}.witness.json"
                    ),
                    "same_unitary_witness_hash": witness_hash,
                    "provenance_binding_hash": provenance_binding_hash,
                },
                "max_unitary_replay_error": replay_error,
                "claim_boundary": "no C2/O3/reroute/B7/STV credit before acceptance",
            }
        )
    fixture = {
        "artifact_id": "B1-B7-cone01-O3-F4-C2-materialization-sentinel.fixture",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "strict_tolerance": STRICT_TOLERANCE,
        "rows": rows,
        "o3_closed": False,
        "reroute_allowed": False,
        "b7_credit_delta": 0,
    }
    fixture["fixture_hash"] = stable_hash(fixture)
    return fixture


def verify_surface(row: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    binding_payload = row.get("binding_payload", {})
    execution_artifacts = row.get("execution_artifacts", {})
    missing_binding_fields = [
        field for field in contract["binding_fields"] if field not in binding_payload
    ]
    missing_execution_artifacts = [
        field
        for field in contract["required_execution_artifacts"]
        if field not in execution_artifacts
    ]
    hash_cells = {
        "declared_provenance_binding_hash": row.get(
            "declared_provenance_binding_hash"
        ),
        "binding_payload.source_circuit_hash": binding_payload.get(
            "source_circuit_hash"
        ),
        "binding_payload.candidate_circuit_hash": binding_payload.get(
            "candidate_circuit_hash"
        ),
        "binding_payload.replay_stdout_hash": binding_payload.get(
            "replay_stdout_hash"
        ),
        "execution_artifacts.replay_stdout_hash": execution_artifacts.get(
            "replay_stdout_hash"
        ),
        "execution_artifacts.source_circuit_hash": execution_artifacts.get(
            "source_circuit_hash"
        ),
        "execution_artifacts.candidate_circuit_hash": execution_artifacts.get(
            "candidate_circuit_hash"
        ),
        "execution_artifacts.same_unitary_witness_hash": execution_artifacts.get(
            "same_unitary_witness_hash"
        ),
        "execution_artifacts.provenance_binding_hash": execution_artifacts.get(
            "provenance_binding_hash"
        ),
    }
    invalid_hash_cells = [key for key, value in hash_cells.items() if not is_sha256(value)]
    binding_hash_matches = (
        row.get("declared_provenance_binding_hash") == stable_hash(binding_payload)
        and execution_artifacts.get("provenance_binding_hash")
        == row.get("declared_provenance_binding_hash")
    )
    try:
        replay_error = float(row.get("max_unitary_replay_error"))
        replay_error_within_tolerance = replay_error <= STRICT_TOLERANCE
    except (TypeError, ValueError):
        replay_error = None
        replay_error_within_tolerance = False
    zero_credit_boundary_present = all(
        token in str(row.get("claim_boundary", ""))
        for token in ["no C2", "O3", "reroute", "B7", "STV"]
    )
    passed = (
        not missing_binding_fields
        and not missing_execution_artifacts
        and not invalid_hash_cells
        and binding_hash_matches
        and replay_error_within_tolerance
        and zero_credit_boundary_present
    )
    return {
        "challenge_id": row.get("challenge_id"),
        "surface_passed": passed,
        "missing_binding_fields": missing_binding_fields,
        "missing_execution_artifacts": missing_execution_artifacts,
        "invalid_hash_cells": invalid_hash_cells,
        "binding_hash_matches": binding_hash_matches,
        "max_unitary_replay_error": replay_error,
        "replay_error_within_tolerance": replay_error_within_tolerance,
        "zero_credit_boundary_present": zero_credit_boundary_present,
    }


def verify_materialization(row: dict[str, Any], root: Path) -> dict[str, Any]:
    execution_artifacts = row.get("execution_artifacts", {})
    file_results = []
    for field in FILE_ARTIFACT_FIELDS:
        rel_path = execution_artifacts.get(field)
        expected_hash_field = field.replace("_file", "_hash")
        expected_hash = execution_artifacts.get(expected_hash_field)
        if not isinstance(rel_path, str):
            exists = False
            actual_hash = None
            hash_matches = False
        else:
            path = root / rel_path
            exists = path.exists() and path.is_file()
            actual_hash = file_hash(path) if exists else None
            hash_matches = exists and actual_hash == expected_hash
        file_results.append(
            {
                "field": field,
                "path": rel_path,
                "expected_hash": expected_hash,
                "exists": exists,
                "actual_hash": actual_hash,
                "hash_matches": hash_matches,
            }
        )
    materialized = all(item["exists"] and item["hash_matches"] for item in file_results)
    return {
        "challenge_id": row.get("challenge_id"),
        "materialized_passed": materialized,
        "file_results": file_results,
        "missing_file_count": sum(1 for item in file_results if not item["exists"]),
        "hash_mismatch_count": sum(
            1 for item in file_results if item["exists"] and not item["hash_matches"]
        ),
    }


def evaluate_fixture(
    fixture: dict[str, Any],
    contract: dict[str, Any],
    root: Path,
    fixture_path: Path,
) -> dict[str, Any]:
    rows = fixture.get("rows", [])
    surface_results = [verify_surface(row, contract) for row in rows]
    materialization_results = [verify_materialization(row, root) for row in rows]
    evaluation = {
        "input_artifact": str(fixture_path),
        "input_artifact_sha256": file_hash(fixture_path),
        "fixture_hash": fixture["fixture_hash"],
        "contract_hash": contract["contract_hash"],
        "row_count": len(rows),
        "required_row_count": contract["required_row_count"],
        "surface_rows_passed": sum(
            1 for row in surface_results if row["surface_passed"]
        ),
        "surface_rows_failed": sum(
            1 for row in surface_results if not row["surface_passed"]
        ),
        "materialized_rows_passed": sum(
            1 for row in materialization_results if row["materialized_passed"]
        ),
        "materialized_rows_failed": sum(
            1 for row in materialization_results if not row["materialized_passed"]
        ),
        "missing_materialized_file_count": sum(
            row["missing_file_count"] for row in materialization_results
        ),
        "materialized_hash_mismatch_count": sum(
            row["hash_mismatch_count"] for row in materialization_results
        ),
        "surface_results": surface_results,
        "materialization_results": materialization_results,
        "accepted": False,
    }
    evaluation["accepted"] = (
        evaluation["row_count"] == evaluation["required_row_count"]
        and evaluation["surface_rows_passed"] == evaluation["required_row_count"]
        and evaluation["materialized_rows_passed"] == evaluation["required_row_count"]
        and fixture.get("o3_closed") is False
        and fixture.get("reroute_allowed") is False
        and fixture.get("b7_credit_delta") == 0
    )
    evaluation["failed_reasons"] = []
    if evaluation["surface_rows_failed"]:
        evaluation["failed_reasons"].append("surface_preflight_failed")
    if evaluation["missing_materialized_file_count"]:
        evaluation["failed_reasons"].append("missing_materialized_files")
    if evaluation["materialized_hash_mismatch_count"]:
        evaluation["failed_reasons"].append("materialized_file_hash_mismatch")
    evaluation["preflight_hash"] = stable_hash(evaluation)
    return evaluation


def build_payload(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.time()
    r34 = load_json(args.r34_verifier)
    r33 = load_json(args.r33_contract)
    contract = r33["o3_f4_c2_provenance_binding_contract_packet"]["contract"]
    fixture = build_surface_clean_fixture(contract)
    write_json(args.fixture_output, fixture, pretty=True)
    evaluation = evaluate_fixture(fixture, contract, args.root, args.fixture_output)
    requirements = [
        requirement(
            "S1",
            "R34 source verifier is validation-clean and still accepts no C2 row",
            r34["summary"].get("validation_error_count") == 0
            and r34["summary"].get("binding_preflight_verifier_ready") is True
            and r34["summary"].get("c2_strict_replay_rows_accepted") is False,
            {
                "r34_validation_error_count": r34["summary"].get(
                    "validation_error_count"
                ),
                "binding_preflight_verifier_ready": r34["summary"].get(
                    "binding_preflight_verifier_ready"
                ),
                "c2_strict_replay_rows_accepted": r34["summary"].get(
                    "c2_strict_replay_rows_accepted"
                ),
            },
        ),
        requirement(
            "S2",
            "Sentinel fixture passes the metadata surface before materialization",
            evaluation["surface_rows_passed"] == 8
            and evaluation["surface_rows_failed"] == 0,
            {
                "surface_rows_passed": evaluation["surface_rows_passed"],
                "surface_rows_failed": evaluation["surface_rows_failed"],
            },
        ),
        requirement(
            "S3",
            "Materialization check rejects every row with missing execution files",
            evaluation["materialized_rows_passed"] == 0
            and evaluation["materialized_rows_failed"] == 8
            and evaluation["missing_materialized_file_count"] == 32,
            {
                "materialized_rows_passed": evaluation["materialized_rows_passed"],
                "materialized_rows_failed": evaluation["materialized_rows_failed"],
                "missing_materialized_file_count": evaluation[
                    "missing_materialized_file_count"
                ],
            },
        ),
        requirement(
            "S4",
            "Fixture keeps valid hashes, recomputed bindings, and numeric strict replay errors",
            all(row["binding_hash_matches"] for row in evaluation["surface_results"])
            and all(row["replay_error_within_tolerance"] for row in evaluation["surface_results"]),
            {
                "binding_mismatch_count": sum(
                    1
                    for row in evaluation["surface_results"]
                    if not row["binding_hash_matches"]
                ),
                "strict_tolerance_failures": sum(
                    1
                    for row in evaluation["surface_results"]
                    if not row["replay_error_within_tolerance"]
                ),
            },
        ),
        requirement(
            "S5",
            "R35 blocks metadata-only evidence even when R34 surface requirements pass",
            evaluation["accepted"] is False
            and evaluation["surface_rows_passed"] == 8
            and evaluation["materialized_rows_passed"] == 0,
            {
                "accepted": evaluation["accepted"],
                "failed_reasons": evaluation["failed_reasons"],
            },
        ),
        requirement(
            "S6",
            "Fixture and preflight are hash-bound",
            bool(fixture["fixture_hash"]) and bool(evaluation["preflight_hash"]),
            {
                "fixture_hash": fixture["fixture_hash"],
                "preflight_hash": evaluation["preflight_hash"],
            },
        ),
        requirement(
            "S7",
            "R35 preserves zero-credit B1/B7 boundaries",
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
            "R35 remains scoped to C2 materialization and claims no C3-C7 progress",
            True,
            {"scope": "C2 materialized execution artifact gate", "c3_c7_progress_claimed": False},
        ),
    ]
    failed_requirements = [
        item["requirement_id"] for item in requirements if not item["passed"]
    ]
    summary = {
        "candidate_id": CANDIDATE_ID,
        "family_id": FAMILY_ID,
        "source_r34_preflight_hash": r34["summary"]["preflight_hash"],
        "source_r34_file_sha256": file_hash(args.r34_verifier),
        "source_r33_contract_hash": contract["contract_hash"],
        "fixture_hash": fixture["fixture_hash"],
        "fixture_file_sha256": file_hash(args.fixture_output),
        "preflight_hash": evaluation["preflight_hash"],
        "strict_tolerance": STRICT_TOLERANCE,
        "binding_field_count": len(contract["binding_fields"]),
        "required_execution_artifact_count": len(
            contract["required_execution_artifacts"]
        ),
        "file_artifact_field_count": len(FILE_ARTIFACT_FIELDS),
        "template_row_count": evaluation["row_count"],
        "surface_rows_passed": evaluation["surface_rows_passed"],
        "surface_rows_failed": evaluation["surface_rows_failed"],
        "materialized_rows_passed": evaluation["materialized_rows_passed"],
        "materialized_rows_failed": evaluation["materialized_rows_failed"],
        "missing_materialized_file_count": evaluation[
            "missing_materialized_file_count"
        ],
        "materialized_hash_mismatch_count": evaluation[
            "materialized_hash_mismatch_count"
        ],
        "artifact_materialization_gate_ready": True,
        "binding_preflight_verifier_ready": True,
        "c2_provenance_binding_contract_ready": True,
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
            "C2_materialized_replay_stdout_files",
            "C2_materialized_source_circuit_files",
            "C2_materialized_candidate_circuit_files",
            "C2_materialized_same_unitary_witness_files",
            "C2_file_hashes_match_declared_hashes",
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
        "title": "B1/B7 Cone01 R35 O3-F4 C2 Artifact Materialization Sentinel Gate",
        "version": VERSION,
        "last_updated": "2026-07-08",
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "o3_f4_c2_artifact_materialization_packet": {
            "source_r34_verifier": str(args.r34_verifier),
            "source_r33_contract": str(args.r33_contract),
            "fixture_output": str(args.fixture_output),
            "evaluation": evaluation,
        },
        "requirements": requirements,
        "summary": summary,
        "claim_boundary": {
            "what_is_supported": (
                "R35 proves that metadata-clean C2 rows are still rejected unless "
                "the replay stdout, source circuit, candidate circuit, and witness "
                "files are materialized and hash-matched."
            ),
            "what_is_not_supported": (
                "R35 does not accept a C2 submission, does not close O3, and does "
                "not permit reroute, B7 credit, STV credit, or resource-saving claims."
            ),
            "next_gate": (
                "Submit materialized C2 execution files whose sha256 hashes match "
                "the declared row artifacts, then rerun the materialization verifier."
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
        "# B1/B7 Cone01 R35 O3-F4 C2 Artifact Materialization Sentinel Gate",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Upstream target: `{payload['upstream_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Fixture hash: `{summary['fixture_hash']}`",
        f"- Preflight hash: `{summary['preflight_hash']}`",
        "",
        "## Result",
        "",
        (
            f"R35 passes {summary['requirements_passed']}/"
            f"{summary['requirement_count']} requirements by building a "
            "metadata-clean sentinel fixture and rejecting it because execution "
            "artifact files are not materialized."
        ),
        "",
        "## Rejection Surface",
        "",
        f"- Surface rows passed / failed: `{summary['surface_rows_passed']}` / `{summary['surface_rows_failed']}`",
        f"- Materialized rows passed / failed: `{summary['materialized_rows_passed']}` / `{summary['materialized_rows_failed']}`",
        f"- Missing materialized files: `{summary['missing_materialized_file_count']}`",
        f"- Materialized hash mismatches: `{summary['materialized_hash_mismatch_count']}`",
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
        "--r34-verifier",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_R34_o3_f4_c2_binding_preflight_verifier_gate_v0.json"
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
        "--fixture-output",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/"
            "B1-B7-cone01-O3-F4-C2-artifact-materialization-sentinel.fixture.json"
        ),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_R35_o3_f4_c2_artifact_materialization_sentinel_gate_v0.json"
        ),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path(
            "research/B1_B7_cone01_R35_o3_f4_c2_artifact_materialization_sentinel_gate.md"
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
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "requirements_passed": payload["summary"]["requirements_passed"],
                    "requirements_failed": payload["summary"]["requirements_failed"],
                    "fixture_hash": payload["summary"]["fixture_hash"],
                    "preflight_hash": payload["summary"]["preflight_hash"],
                    "surface_rows_passed": payload["summary"][
                        "surface_rows_passed"
                    ],
                    "materialized_rows_passed": payload["summary"][
                        "materialized_rows_passed"
                    ],
                    "missing_materialized_file_count": payload["summary"][
                        "missing_materialized_file_count"
                    ],
                    "c2_strict_replay_rows_accepted": payload["summary"][
                        "c2_strict_replay_rows_accepted"
                    ],
                    "o3_closed": payload["summary"]["o3_closed"],
                    "reroute_allowed": payload["summary"]["reroute_allowed"],
                    "b7_credit_delta": payload["summary"]["b7_credit_delta"],
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
