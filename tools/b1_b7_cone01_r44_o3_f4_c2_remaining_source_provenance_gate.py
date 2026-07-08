#!/usr/bin/env python3
"""T-B1-004et/T-B7-014c: R44 O3-F4 C2 remaining-row source-provenance gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r44_o3_f4_c2_remaining_source_provenance_gate_v0"
STATUS = "cone01_r44_o3_f4_c2_remaining_source_provenance_bound_rejected"
MODEL_STATUS = "o3_f4_c2_all_rows_source_provenance_bound_no_source_backed_acceptance"
VERSION = "0.1"
TARGET_ID = "T-B1-004et/T-B7-014c"
UPSTREAM_TARGET_ID = "T-B1-004es/T-B7-014b"
FAMILY_ID = "O3-F4"
CANDIDATE_ID = "NL-C02"
STRICT_TOLERANCE = 1.0e-8
WITNESS_SCHEMA = "source_backed_unitary_equivalence_v1"
UNITARY_DISTANCE_METRIC = "one_qubit_rz_operator_norm"
FILE_ARTIFACT_FIELDS = [
    "replay_stdout_file",
    "source_circuit_file",
    "candidate_circuit_file",
    "same_unitary_witness_file",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_file_hash(root: Path, path_value: Any, expected_hash: Any) -> bool:
    path = root / path_value if isinstance(path_value, str) else None
    return bool(
        path
        and path.exists()
        and path.is_file()
        and isinstance(expected_hash, str)
        and file_hash(path) == expected_hash
    )


def verify_materialized_files(row: dict[str, Any], root: Path) -> bool:
    artifacts = row.get("execution_artifacts", {})
    return all(
        verify_file_hash(root, artifacts.get(field), artifacts.get(field.replace("_file", "_hash")))
        for field in FILE_ARTIFACT_FIELDS
    )


def row_source_provenance_passed(row: dict[str, Any], root: Path) -> bool:
    return (
        bool(row.get("source_dataset_id"))
        and bool(row.get("source_trace_id"))
        and verify_file_hash(root, row.get("source_dataset_file"), row.get("source_dataset_sha256"))
        and verify_file_hash(root, row.get("source_trace_file"), row.get("source_trace_sha256"))
        and verify_file_hash(root, row.get("replay_environment_file"), row.get("replay_environment_sha256"))
    )


def row_witness_schema_passed(row: dict[str, Any], root: Path) -> bool:
    return (
        row.get("same_unitary_witness_schema") == WITNESS_SCHEMA
        and bool(row.get("same_unitary_witness_verifier"))
        and verify_file_hash(root, row.get("same_unitary_witness_schema_file"), row.get("same_unitary_witness_schema_sha256"))
        and verify_file_hash(root, row.get("same_unitary_witness_verifier_file"), row.get("same_unitary_witness_verifier_sha256"))
    )


def row_witness_preflight_passed(row: dict[str, Any], root: Path) -> bool:
    return (
        row.get("witness_preflight_passed") is True
        and verify_file_hash(root, row.get("same_unitary_witness_preflight_file"), row.get("same_unitary_witness_preflight_sha256"))
        and verify_file_hash(root, row.get("same_unitary_witness_preflight_command_file"), row.get("same_unitary_witness_preflight_command_sha256"))
    )


def row_unitary_distance_passed(row: dict[str, Any], root: Path) -> bool:
    return (
        row.get("unitary_distance_passed") is True
        and row.get("unitary_distance_metric") == UNITARY_DISTANCE_METRIC
        and isinstance(row.get("computed_unitary_distance"), (int, float))
        and row.get("computed_unitary_distance") <= STRICT_TOLERANCE
        and verify_file_hash(root, row.get("same_unitary_unitary_distance_witness_file"), row.get("same_unitary_unitary_distance_witness_sha256"))
        and verify_file_hash(root, row.get("same_unitary_unitary_distance_transcript_file"), row.get("same_unitary_unitary_distance_transcript_sha256"))
    )


def write_provenance_files(root: Path, output_dir: Path, row: dict[str, Any]) -> dict[str, Any]:
    challenge_id = row["challenge_id"]
    artifacts = row["execution_artifacts"]
    source_path = root / artifacts["source_circuit_file"]
    candidate_path = root / artifacts["candidate_circuit_file"]
    witness_path = root / row["same_unitary_unitary_distance_witness_file"]
    transcript_path = root / row["same_unitary_unitary_distance_transcript_file"]
    dataset = {
        "artifact": "R44 remaining-row source dataset",
        "dataset_id": f"qasmbench_medium_exact/gcm_h6.qasm::line1381::{challenge_id}::r44_source_provenance",
        "challenge_id": challenge_id,
        "source_circuit_file": artifacts["source_circuit_file"],
        "source_circuit_sha256": file_hash(source_path),
        "candidate_circuit_file": artifacts["candidate_circuit_file"],
        "candidate_circuit_sha256": file_hash(candidate_path),
        "unitary_distance_witness_file": row["same_unitary_unitary_distance_witness_file"],
        "unitary_distance_witness_sha256": file_hash(witness_path),
        "unitary_distance_transcript_file": row["same_unitary_unitary_distance_transcript_file"],
        "unitary_distance_transcript_sha256": file_hash(transcript_path),
        "provenance_scope": "materialized_smoke_source_lineage_not_source_backed_replay",
        "source_backed_replay": False,
    }
    dataset["dataset_hash"] = stable_hash(dataset)
    trace = {
        "artifact": "R44 remaining-row source trace",
        "trace_id": f"{challenge_id}::r44_lineage_trace",
        "challenge_id": challenge_id,
        "lineage": [
            "R37 materialized all-row smoke artifacts",
            "R43 all-row unitary-distance smoke witness",
            "R44 remaining-row source-provenance binding",
        ],
        "binding_inputs": {
            "source_circuit_sha256": dataset["source_circuit_sha256"],
            "candidate_circuit_sha256": dataset["candidate_circuit_sha256"],
            "unitary_distance_witness_sha256": dataset["unitary_distance_witness_sha256"],
            "unitary_distance_transcript_sha256": dataset["unitary_distance_transcript_sha256"],
        },
        "provenance_scope": "trace_binds_current_artifacts_but_does_not_upgrade_to_source_backed_acceptance",
        "source_backed_replay": False,
    }
    trace["trace_hash"] = stable_hash(trace)
    environment = {
        "artifact": "R44 remaining-row replay environment",
        "challenge_id": challenge_id,
        "openqasm_version": "3.0",
        "qasm_parser_scope": "single_qubit_rz_smoke_rows",
        "unitary_distance_metric": UNITARY_DISTANCE_METRIC,
        "strict_tolerance": STRICT_TOLERANCE,
        "command": "python3 tools/b1_b7_cone01_r44_o3_f4_c2_remaining_source_provenance_gate.py --verify-only",
        "deterministic": True,
        "source_backed_replay": False,
        "claim_boundary": "environment records replay conditions but is not a source-backed C2 certificate",
    }
    environment["environment_hash"] = stable_hash(environment)
    files = {
        f"{challenge_id}.source_dataset.json": dataset,
        f"{challenge_id}.source_trace.json": trace,
        f"{challenge_id}.replay_environment.json": environment,
    }
    packet: dict[str, Any] = {
        "source_dataset_id": dataset["dataset_id"],
        "source_trace_id": trace["trace_id"],
    }
    for name, payload in files.items():
        path = output_dir / name
        write_json(path, payload)
        stem = name.replace(f"{challenge_id}.", "").replace(".json", "")
        packet[f"{stem}_file"] = str(path.relative_to(root))
        packet[f"{stem}_sha256"] = file_hash(path)
    return packet


def augment_fixture(fixture: dict[str, Any], root: Path, provenance_dir: Path) -> dict[str, Any]:
    rows = []
    newly_bound = []
    for row in fixture["rows"]:
        new_row = json.loads(json.dumps(row))
        if not row_source_provenance_passed(new_row, root):
            packet = write_provenance_files(root, provenance_dir, new_row)
            new_row.update(packet)
            newly_bound.append(new_row["challenge_id"])
        new_row.update(
            {
                "source_backed_replay": False,
                "same_unitary_certificate": False,
                "smoke_only_not_c2_acceptance": True,
            }
        )
        rows.append(new_row)
    augmented = {
        "artifact_id": "B1-B7-cone01-O3-F4-C2-remaining-source-provenance.fixture",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_fixture_hash": fixture["fixture_hash"],
        "contract_hash": fixture["contract_hash"],
        "strict_tolerance": STRICT_TOLERANCE,
        "newly_bound_challenge_ids": newly_bound,
        "rows": rows,
        "o3_closed": False,
        "reroute_allowed": False,
        "b7_credit_delta": 0,
    }
    augmented["fixture_hash"] = stable_hash(augmented)
    return augmented


def evaluate_fixture(fixture: dict[str, Any], root: Path, fixture_path: Path) -> dict[str, Any]:
    row_results = []
    for row in fixture["rows"]:
        source_backed_flags_passed = (
            row.get("source_backed_replay") is True
            and row.get("same_unitary_certificate") is True
            and row.get("smoke_only_not_c2_acceptance") is False
        )
        accepted = (
            verify_materialized_files(row, root)
            and row_source_provenance_passed(row, root)
            and row_witness_schema_passed(row, root)
            and row_witness_preflight_passed(row, root)
            and row_unitary_distance_passed(row, root)
            and source_backed_flags_passed
        )
        row_results.append(
            {
                "challenge_id": row["challenge_id"],
                "materialized_files_passed": verify_materialized_files(row, root),
                "source_provenance_passed": row_source_provenance_passed(row, root),
                "witness_schema_passed": row_witness_schema_passed(row, root),
                "witness_preflight_passed": row_witness_preflight_passed(row, root),
                "unitary_distance_passed": row_unitary_distance_passed(row, root),
                "source_backed_flags_passed": source_backed_flags_passed,
                "accepted": accepted,
            }
        )
    evaluation = {
        "input_artifact": str(fixture_path),
        "input_artifact_sha256": file_hash(fixture_path),
        "fixture_hash": fixture["fixture_hash"],
        "row_count": len(row_results),
        "row_results": row_results,
        "materialized_rows_passed": sum(1 for row in row_results if row["materialized_files_passed"]),
        "source_provenance_rows_passed": sum(1 for row in row_results if row["source_provenance_passed"]),
        "source_provenance_failures": sum(1 for row in row_results if not row["source_provenance_passed"]),
        "witness_schema_rows_passed": sum(1 for row in row_results if row["witness_schema_passed"]),
        "witness_schema_failures": sum(1 for row in row_results if not row["witness_schema_passed"]),
        "witness_preflight_rows_passed": sum(1 for row in row_results if row["witness_preflight_passed"]),
        "witness_preflight_failures": sum(1 for row in row_results if not row["witness_preflight_passed"]),
        "unitary_distance_rows_passed": sum(1 for row in row_results if row["unitary_distance_passed"]),
        "unitary_distance_failures": sum(1 for row in row_results if not row["unitary_distance_passed"]),
        "source_backed_rows_passed": sum(1 for row in row_results if row["accepted"]),
        "source_backed_flag_failures": sum(1 for row in row_results if not row["source_backed_flags_passed"]),
        "accepted": False,
    }
    evaluation["evaluation_hash"] = stable_hash(evaluation)
    return evaluation


def req(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"requirement_id": requirement_id, "label": label, "passed": bool(passed), "evidence": evidence}


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    r43 = load_json(args.r43_result)
    source_fixture = load_json(args.r43_fixture)
    augmented_fixture = augment_fixture(source_fixture, args.root, args.provenance_dir)
    write_json(args.fixture_output, augmented_fixture)
    evaluation = evaluate_fixture(augmented_fixture, args.root, args.fixture_output)
    requirements = [
        req(
            "S1",
            "R43 all-row unitary-distance smoke gate is validation-clean",
            r43["summary"].get("validation_error_count") == 0
            and r43["summary"].get("unitary_distance_rows_passed") == 8
            and r43["summary"].get("source_backed_rows_passed") == 0,
            {
                "r43_validation_error_count": r43["summary"].get("validation_error_count"),
                "r43_unitary_distance_rows_passed": r43["summary"].get("unitary_distance_rows_passed"),
                "r43_source_backed_rows_passed": r43["summary"].get("source_backed_rows_passed"),
            },
        ),
        req(
            "S2",
            "R44 binds source provenance for all 8 rows",
            evaluation["source_provenance_rows_passed"] == 8
            and evaluation["source_provenance_failures"] == 0
            and len(augmented_fixture["newly_bound_challenge_ids"]) == 7,
            {
                "source_provenance_rows_passed": evaluation["source_provenance_rows_passed"],
                "source_provenance_failures": evaluation["source_provenance_failures"],
                "newly_bound_challenge_ids": augmented_fixture["newly_bound_challenge_ids"],
            },
        ),
        req(
            "S3",
            "R44 preserves the current witness-schema and preflight blockers",
            evaluation["witness_schema_rows_passed"] == 1
            and evaluation["witness_preflight_rows_passed"] == 1
            and evaluation["witness_schema_failures"] == 7
            and evaluation["witness_preflight_failures"] == 7,
            {
                "witness_schema_rows_passed": evaluation["witness_schema_rows_passed"],
                "witness_preflight_rows_passed": evaluation["witness_preflight_rows_passed"],
                "witness_schema_failures": evaluation["witness_schema_failures"],
                "witness_preflight_failures": evaluation["witness_preflight_failures"],
            },
        ),
        req("S4", "All materialized and unitary-distance files remain hash-valid", evaluation["materialized_rows_passed"] == 8 and evaluation["unitary_distance_rows_passed"] == 8, {"materialized_rows_passed": evaluation["materialized_rows_passed"], "unitary_distance_rows_passed": evaluation["unitary_distance_rows_passed"]}),
        req("S5", "R44 does not claim source-backed replay or same-unitary acceptance", evaluation["source_backed_rows_passed"] == 0 and evaluation["source_backed_flag_failures"] == 8, {"source_backed_rows_passed": evaluation["source_backed_rows_passed"], "source_backed_flag_failures": evaluation["source_backed_flag_failures"]}),
        req("S6", "R44 keeps C2/O3/reroute/B7 zero-credit boundaries", augmented_fixture.get("o3_closed") is False and augmented_fixture.get("reroute_allowed") is False and augmented_fixture.get("b7_credit_delta") == 0, {"o3_closed": augmented_fixture.get("o3_closed"), "reroute_allowed": augmented_fixture.get("reroute_allowed"), "b7_credit_delta": augmented_fixture.get("b7_credit_delta")}),
        req("S7", "R44 claims no C3-C7 or ledger progress", True, {"c3_c7_progress_claimed": False, "b7_ledger_credit_claimed": False}),
        req("S8", "R44 output is hash-bound", bool(augmented_fixture["fixture_hash"]) and bool(evaluation["evaluation_hash"]), {"fixture_hash": augmented_fixture["fixture_hash"], "evaluation_hash": evaluation["evaluation_hash"]}),
    ]
    failed = [item["requirement_id"] for item in requirements if not item["passed"]]
    summary = {
        "candidate_id": CANDIDATE_ID,
        "family_id": FAMILY_ID,
        "source_r43_evaluation_hash": r43["summary"]["evaluation_hash"],
        "source_r43_fixture_hash": r43["summary"]["all_rows_unitary_distance_fixture_hash"],
        "source_r43_file_sha256": file_hash(args.r43_result),
        "remaining_source_provenance_fixture_hash": augmented_fixture["fixture_hash"],
        "remaining_source_provenance_fixture_file_sha256": file_hash(args.fixture_output),
        "evaluation_hash": evaluation["evaluation_hash"],
        "strict_tolerance": STRICT_TOLERANCE,
        "newly_bound_challenge_ids": augmented_fixture["newly_bound_challenge_ids"],
        "newly_bound_challenge_count": len(augmented_fixture["newly_bound_challenge_ids"]),
        "template_row_count": evaluation["row_count"],
        "materialized_rows_passed": evaluation["materialized_rows_passed"],
        "source_provenance_rows_passed": evaluation["source_provenance_rows_passed"],
        "source_provenance_failures": evaluation["source_provenance_failures"],
        "witness_schema_rows_passed": evaluation["witness_schema_rows_passed"],
        "witness_schema_failures": evaluation["witness_schema_failures"],
        "witness_preflight_rows_passed": evaluation["witness_preflight_rows_passed"],
        "witness_preflight_failures": evaluation["witness_preflight_failures"],
        "unitary_distance_rows_passed": evaluation["unitary_distance_rows_passed"],
        "unitary_distance_failures": evaluation["unitary_distance_failures"],
        "source_backed_rows_passed": evaluation["source_backed_rows_passed"],
        "source_backed_flag_failures": evaluation["source_backed_flag_failures"],
        "all_rows_source_provenance_ready": True,
        "all_rows_unitary_distance_ready": True,
        "single_row_witness_scaffold_ready": True,
        "single_row_witness_preflight_ready": True,
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
            "provide_witness_schema_for_remaining_7_rows",
            "provide_executable_witness_preflight_for_remaining_7_rows",
            "replace_smoke_rows_with_real_source_backed_replay_flags",
            "pass_C2_source_backed_discriminator_for_all_rows",
            "C3_same_unitary_replay_certificate",
            "C4_C5_same_access_denominator_comparison",
            "C6_leakage_free_optimizer_trace",
            "C7_machine_check_replay_bundle",
        ],
        "remaining_open_obligation_count": 8,
        "requirement_count": len(requirements),
        "requirements_passed": len(requirements) - len(failed),
        "requirements_failed": len(failed),
        "failed_requirement_ids": failed,
        "validation_error_count": len(failed),
    }
    return {
        "title": "B1/B7 Cone01 R44 O3-F4 C2 Remaining Source-Provenance Gate",
        "version": VERSION,
        "last_updated": "2026-07-08",
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "o3_f4_c2_remaining_source_provenance_packet": {
            "source_r43_result": str(args.r43_result),
            "source_r43_fixture": str(args.r43_fixture),
            "provenance_dir": str(args.provenance_dir),
            "fixture_output": str(args.fixture_output),
            "evaluation": evaluation,
        },
        "requirements": requirements,
        "summary": summary,
        "claim_boundary": {
            "what_is_supported": "R44 adds hash-bound source dataset, source trace, and replay-environment files for the 7 rows that lacked provenance after R43.",
            "what_is_not_supported": "R44 does not provide witness schemas or executable preflights for those 7 rows, does not mark any row source-backed, does not accept C2, does not close O3, and does not permit reroute, B7 credit, STV credit, or resource-saving claims.",
            "next_gate": "Add witness schemas and executable preflights for O3-F4-C02 through O3-F4-C08, then rerun the source-backed discriminator before C3-C7.",
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": failed,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    s = payload["summary"]
    lines = [
        "# B1/B7 Cone01 R44 O3-F4 C2 Remaining Source-Provenance Gate",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Upstream target: `{payload['upstream_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Fixture hash: `{s['remaining_source_provenance_fixture_hash']}`",
        f"- Evaluation hash: `{s['evaluation_hash']}`",
        "",
        "## Result",
        "",
        f"R44 passes {s['requirements_passed']}/{s['requirement_count']} requirements by binding source provenance for the 7 rows that lacked it while keeping C2 rejected.",
        "",
        "## Rejection Surface",
        "",
        f"- Newly bound rows: `{s['newly_bound_challenge_count']}`",
        f"- Source-provenance rows passed: `{s['source_provenance_rows_passed']}`",
        f"- Witness-schema rows passed: `{s['witness_schema_rows_passed']}`",
        f"- Witness-preflight rows passed: `{s['witness_preflight_rows_passed']}`",
        f"- Unitary-distance rows passed: `{s['unitary_distance_rows_passed']}`",
        f"- Source-backed rows passed: `{s['source_backed_rows_passed']}`",
        f"- Source-backed flag failures: `{s['source_backed_flag_failures']}`",
        f"- C2 accepted: `{s['c2_strict_replay_rows_accepted']}`",
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
            f"- validation_error_count: `{s['validation_error_count']}`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--r43-result", type=Path, default=Path("results/B1_B7_cone01_R43_o3_f4_c2_all_rows_unitary_distance_smoke_gate_v0.json"))
    parser.add_argument("--r43-fixture", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/B1-B7-cone01-O3-F4-C2-all-rows-unitary-distance-smoke.fixture.json"))
    parser.add_argument("--provenance-dir", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_provenance/r44_remaining_rows"))
    parser.add_argument("--fixture-output", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/B1-B7-cone01-O3-F4-C2-remaining-source-provenance.fixture.json"))
    parser.add_argument("--json-output", type=Path, default=Path("results/B1_B7_cone01_R44_o3_f4_c2_remaining_source_provenance_gate_v0.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("research/B1_B7_cone01_R44_o3_f4_c2_remaining_source_provenance_gate.md"))
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.verify_only:
        fixture = load_json(args.r43_fixture)
        packets = [
            write_provenance_files(args.root, args.provenance_dir, row)
            for row in fixture["rows"]
            if not row_source_provenance_passed(row, args.root)
        ]
        print(json.dumps(packets, indent=2, sort_keys=True))
        return
    payload = build_payload(args)
    write_json(args.json_output, payload)
    write_markdown(args.markdown_output, payload)
    if args.pretty:
        s = payload["summary"]
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "fixture_hash": s["remaining_source_provenance_fixture_hash"],
                    "evaluation_hash": s["evaluation_hash"],
                    "requirements_passed": s["requirements_passed"],
                    "requirements_failed": s["requirements_failed"],
                    "newly_bound_challenge_count": s["newly_bound_challenge_count"],
                    "source_provenance_rows_passed": s["source_provenance_rows_passed"],
                    "witness_schema_rows_passed": s["witness_schema_rows_passed"],
                    "witness_preflight_rows_passed": s["witness_preflight_rows_passed"],
                    "source_backed_rows_passed": s["source_backed_rows_passed"],
                    "c2_strict_replay_rows_accepted": s["c2_strict_replay_rows_accepted"],
                    "o3_closed": s["o3_closed"],
                    "reroute_allowed": s["reroute_allowed"],
                    "b7_credit_delta": s["b7_credit_delta"],
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
