#!/usr/bin/env python3
"""T-B1-004ez/T-B7-014i: R50 C01 hash-matched pre-submission gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r50_o3_f4_c2_c01_hash_matched_presubmission_gate_v0"
STATUS = "cone01_r50_o3_f4_c2_c01_hash_matched_presubmission_rejected_on_source_backed_flags"
MODEL_STATUS = "o3_f4_c2_c01_file_hash_surface_closed_flags_still_block"
VERSION = "0.1"
TARGET_ID = "T-B1-004ez/T-B7-014i"
UPSTREAM_TARGET_ID = "T-B1-004ey/T-B7-014h"
SELECTED_CHALLENGE_ID = "O3-F4-C01"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
FILE_HASH_PAIRS = [
    ("source_dataset_file", "source_dataset_sha256"),
    ("source_trace_file", "source_trace_sha256"),
    ("replay_environment_file", "replay_environment_sha256"),
    ("source_circuit_file", "source_circuit_sha256"),
    ("candidate_circuit_file", "candidate_circuit_sha256"),
    ("replay_stdout_file", "replay_stdout_sha256"),
    ("same_unitary_witness_file", "same_unitary_witness_sha256"),
    ("verifier_signature_file", "verifier_signature_sha256"),
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def str_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def rel(path: Path) -> str:
    return path.as_posix()


def req(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def verify_row(row: dict[str, Any], contract: dict[str, Any], spec: dict[str, Any], root: Path) -> dict[str, Any]:
    missing_keys = [key for key in contract["required_keys"] if key not in row]
    empty_production_keys = [
        key
        for key in contract["production_required_keys"]
        if key not in row or row.get(key) in (None, "", False)
    ]
    malformed_sha_fields = [
        hash_key
        for _, hash_key in FILE_HASH_PAIRS
        if hash_key in row and row.get(hash_key) is not None and not is_sha256(row.get(hash_key))
    ]
    file_results = []
    for path_key, hash_key in FILE_HASH_PAIRS:
        path_value = row.get(path_key)
        expected_hash = row.get(hash_key)
        path = root / path_value if isinstance(path_value, str) else None
        exists = bool(path and path.exists() and path.is_file())
        actual_hash = file_hash(path) if exists else None
        file_results.append(
            {
                "path_key": path_key,
                "hash_key": hash_key,
                "path": path_value,
                "expected_hash": expected_hash,
                "exists": exists,
                "actual_hash": actual_hash,
                "hash_matches": exists and actual_hash == expected_hash,
            }
        )
    file_hash_failures = [
        item["path_key"]
        for item in file_results
        if not item["exists"] or not item["hash_matches"]
    ]
    flag_failures = [
        key
        for key, expected in spec["required_boolean_state"].items()
        if row.get(key) is not expected
    ]
    schema_passed = row.get("same_unitary_witness_schema") == spec["required_schema"]
    boundary_tokens_present = all(
        token in str(row.get("claim_boundary", "")) for token in spec["required_claim_boundary_tokens"]
    )
    accepted = (
        not missing_keys
        and not empty_production_keys
        and not malformed_sha_fields
        and not file_hash_failures
        and not flag_failures
        and schema_passed
        and boundary_tokens_present
    )
    return {
        "challenge_id": row.get("challenge_id"),
        "accepted": accepted,
        "missing_key_count": len(missing_keys),
        "empty_production_key_count": len(empty_production_keys),
        "malformed_sha_field_count": len(malformed_sha_fields),
        "file_hash_failure_count": len(file_hash_failures),
        "flag_failure_count": len(flag_failures),
        "schema_passed": schema_passed,
        "boundary_tokens_present": boundary_tokens_present,
        "missing_keys": missing_keys,
        "empty_production_keys": empty_production_keys,
        "malformed_sha_fields": malformed_sha_fields,
        "file_hash_failures": file_hash_failures,
        "flag_failures": flag_failures,
        "file_results": file_results,
    }


def build_presubmission_row(args: argparse.Namespace) -> dict[str, Any]:
    source_dataset = args.root / "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_provenance/r39_c01/O3-F4-C01.source_dataset.json"
    source_trace = args.root / "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_provenance/r39_c01/O3-F4-C01.source_trace.json"
    replay_environment = args.root / "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_provenance/r39_c01/O3-F4-C01.replay_environment.json"
    source_circuit = args.root / "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/materialized_artifacts/r37_smoke/O3-F4-C01.source.qasm"
    candidate_circuit = args.root / "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/materialized_artifacts/r37_smoke/O3-F4-C01.candidate.qasm"
    replay_stdout = args.root / "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/materialized_artifacts/r37_smoke/O3-F4-C01.stdout.txt"
    same_unitary_witness = args.root / "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/unitary_distance/r43_all_rows/O3-F4-C01.unitary_distance_witness.json"
    same_unitary_verifier = "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/witness_scaffolds/r40_c01/O3-F4-C01.witness_verifier.json"
    signature_blocker = args.root / "results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_backed_rows/O3-F4-C01.verifier_signature_blocker.json"
    external_lineage_note = (
        "R50 binds the existing R39 source-provenance dataset and trace, R37 "
        "materialized OpenQASM 3.0 source/candidate/stdout files, and R43 "
        "unitary-distance smoke witness for O3-F4-C01. This is a hash-matched "
        "pre-submission evidence surface, not source-backed replay acceptance."
    )
    signature_blocker_payload = {
        "artifact": "R50 verifier signature blocker note",
        "challenge_id": SELECTED_CHALLENGE_ID,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "scope": "not_a_verifier_signature_not_a_same_unitary_certificate",
        "why_signature_is_blocked": [
            "same_unitary_witness_file is a smoke unitary-distance witness",
            "same_unitary_witness_verifier is an R40 dry-run schema verifier",
            "source_backed_replay remains false",
            "same_unitary_certificate remains false",
            "smoke_only_not_c2_acceptance remains true",
        ],
        "claim_boundary": "no C2; O3 remains open; no reroute; no B7 credit; no STV credit",
    }
    write_json(signature_blocker, signature_blocker_payload)
    row = {
        "artifact_id": "B1-B7-cone01-O3-F4-C2-C01-hash-matched-presubmission-row",
        "challenge_id": SELECTED_CHALLENGE_ID,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_dataset_id": "qasmbench_medium_exact/gcm_h6.qasm::line1381::O3-F4-C01::r39_source_provenance",
        "source_dataset_file": rel(source_dataset.relative_to(args.root)),
        "source_dataset_sha256": file_hash(source_dataset),
        "source_trace_id": "O3-F4-C01::r39_lineage_trace",
        "source_trace_file": rel(source_trace.relative_to(args.root)),
        "source_trace_sha256": file_hash(source_trace),
        "external_lineage_note": external_lineage_note,
        "external_lineage_sha256": str_hash(external_lineage_note),
        "replay_environment_file": rel(replay_environment.relative_to(args.root)),
        "replay_environment_sha256": file_hash(replay_environment),
        "source_circuit_file": rel(source_circuit.relative_to(args.root)),
        "source_circuit_sha256": file_hash(source_circuit),
        "candidate_circuit_file": rel(candidate_circuit.relative_to(args.root)),
        "candidate_circuit_sha256": file_hash(candidate_circuit),
        "replay_stdout_file": rel(replay_stdout.relative_to(args.root)),
        "replay_stdout_sha256": file_hash(replay_stdout),
        "same_unitary_witness_file": rel(same_unitary_witness.relative_to(args.root)),
        "same_unitary_witness_sha256": file_hash(same_unitary_witness),
        "same_unitary_witness_schema": "source_backed_unitary_equivalence_v1",
        "same_unitary_witness_verifier": same_unitary_verifier,
        "verifier_signature_file": rel(signature_blocker.relative_to(args.root)),
        "verifier_signature_sha256": file_hash(signature_blocker),
        "source_backed_replay": False,
        "same_unitary_certificate": False,
        "smoke_only_not_c2_acceptance": True,
        "claim_boundary": "no C2; O3 remains open; no reroute; no B7 credit; no STV credit",
    }
    row["presubmission_row_hash"] = stable_hash(row)
    return row


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    r49 = load_json(args.r49_result)
    contract = load_json(args.contract_input)
    verifier = load_json(args.r49_verifier)
    baseline = r49["summary"]
    row = build_presubmission_row(args)
    write_json(args.presubmission_output, row)
    verification = verify_row(row, contract, verifier, args.root)
    evaluation = {
        "source_r49_verifier_hash": verifier["verifier_hash"],
        "presubmission_row_hash": row["presubmission_row_hash"],
        "presubmission_file_sha256": file_hash(args.presubmission_output),
        "verification": verification,
        "accepted_source_backed_row_count": 1 if verification["accepted"] else 0,
        "presubmission_rejected": verification["accepted"] is False,
    }
    evaluation["evaluation_hash"] = stable_hash(evaluation)
    requirements = [
        req(
            "S1",
            "R49 baseline is clean and still rejects the placeholder template",
            baseline.get("requirements_passed") == 8
            and baseline.get("requirements_failed") == 0
            and baseline.get("file_hash_failure_count") == 8
            and baseline.get("accepted_source_backed_row_count") == 0,
            {
                "r49_requirements_passed": baseline.get("requirements_passed"),
                "r49_requirements_failed": baseline.get("requirements_failed"),
                "r49_file_hash_failure_count": baseline.get("file_hash_failure_count"),
                "r49_accepted_source_backed_row_count": baseline.get("accepted_source_backed_row_count"),
            },
        ),
        req(
            "S2",
            "R50 emits a row with every R48/R49 required key present",
            all(key in row for key in contract["required_keys"]),
            {
                "required_key_count": len(contract["required_keys"]),
                "present_required_key_count": sum(1 for key in contract["required_keys"] if key in row),
            },
        ),
        req(
            "S3",
            "R50 closes the file/hash surface for C01",
            verification["file_hash_failure_count"] == 0
            and verification["malformed_sha_field_count"] == 0,
            {
                "file_hash_pair_count": len(FILE_HASH_PAIRS),
                "file_hash_failure_count": verification["file_hash_failure_count"],
                "malformed_sha_field_count": verification["malformed_sha_field_count"],
            },
        ),
        req(
            "S4",
            "R50 narrows R49 rejection from missing files to source-backed flags",
            baseline.get("file_hash_failure_count") == 8
            and verification["file_hash_failure_count"] == 0
            and verification["empty_production_key_count"] == 2
            and verification["flag_failure_count"] == 3,
            {
                "r49_file_hash_failure_count": baseline.get("file_hash_failure_count"),
                "r50_file_hash_failure_count": verification["file_hash_failure_count"],
                "r50_empty_production_key_count": verification["empty_production_key_count"],
                "r50_flag_failure_count": verification["flag_failure_count"],
                "r50_flag_failures": verification["flag_failures"],
            },
        ),
        req(
            "S5",
            "R50 remains rejected and does not accept a source-backed row",
            evaluation["presubmission_rejected"] is True
            and evaluation["accepted_source_backed_row_count"] == 0,
            {
                "presubmission_rejected": evaluation["presubmission_rejected"],
                "accepted_source_backed_row_count": evaluation["accepted_source_backed_row_count"],
            },
        ),
        req(
            "S6",
            "R50 preserves witness schema and zero-credit boundary tokens",
            verification["schema_passed"] is True and verification["boundary_tokens_present"] is True,
            {
                "schema_passed": verification["schema_passed"],
                "boundary_tokens_present": verification["boundary_tokens_present"],
            },
        ),
        req(
            "S7",
            "R50 signature artifact is explicitly a blocker note, not a certificate",
            "not_a_verifier_signature" in load_json(args.root / row["verifier_signature_file"]).get("scope", ""),
            {
                "verifier_signature_file": row["verifier_signature_file"],
                "verifier_signature_sha256": row["verifier_signature_sha256"],
            },
        ),
        req(
            "S8",
            "R50 claims no C2, O3, reroute, B7, STV, C3-C7, or resource progress",
            True,
            {
                "c2_accepted": False,
                "o3_closed": False,
                "reroute_allowed": False,
                "b7_credit_delta": 0,
                "b7_space_time_volume_credit": 0,
                "c3_c7_progress_claimed": False,
                "resource_saving_claimed": False,
            },
        ),
    ]
    failed = [item["requirement_id"] for item in requirements if not item["passed"]]
    summary = {
        "source_r49_verifier_hash": verifier["verifier_hash"],
        "source_r49_evaluation_hash": baseline["evaluation_hash"],
        "selected_challenge_id": SELECTED_CHALLENGE_ID,
        "presubmission_row_hash": row["presubmission_row_hash"],
        "presubmission_file_sha256": file_hash(args.presubmission_output),
        "evaluation_hash": evaluation["evaluation_hash"],
        "required_key_count": len(contract["required_keys"]),
        "production_required_key_count": len(contract["production_required_keys"]),
        "file_hash_pair_count": len(FILE_HASH_PAIRS),
        "file_hash_failure_count": verification["file_hash_failure_count"],
        "r49_baseline_file_hash_failure_count": baseline["file_hash_failure_count"],
        "empty_production_key_count": verification["empty_production_key_count"],
        "flag_failure_count": verification["flag_failure_count"],
        "flag_failures": verification["flag_failures"],
        "schema_passed": verification["schema_passed"],
        "boundary_tokens_present": verification["boundary_tokens_present"],
        "presubmission_rejected": evaluation["presubmission_rejected"],
        "accepted_source_backed_row_count": evaluation["accepted_source_backed_row_count"],
        "source_backed_replay": row["source_backed_replay"],
        "same_unitary_certificate": row["same_unitary_certificate"],
        "smoke_only_not_c2_acceptance": row["smoke_only_not_c2_acceptance"],
        "c2_strict_replay_rows_accepted": False,
        "o3_closed": False,
        "reroute_allowed": False,
        "b7_credit_delta": 0,
        "b7_space_time_volume_credit": 0,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "remaining_open_obligations": [
            "replace_smoke_unitary_distance_witness_with_source_backed_replay_witness",
            "replace_r40_dry_run_verifier_with_real_same_unitary_verifier",
            "replace_signature_blocker_note_with_verifier_signature",
            "set_source_backed_replay_true_only_after_real_replay",
            "set_same_unitary_certificate_true_only_after_real_verifier",
            "set_smoke_only_not_c2_acceptance_false_only_after_non_smoke_evidence",
            "rerun_R49_then_R47_after_flag_evidence",
        ],
        "remaining_open_obligation_count": 7,
        "requirement_count": len(requirements),
        "requirements_passed": len(requirements) - len(failed),
        "requirements_failed": len(failed),
        "failed_requirement_ids": failed,
        "validation_error_count": len(failed),
    }
    return {
        "title": "B1/B7 Cone01 R50 O3-F4 C2 C01 Hash-Matched Pre-Submission Gate",
        "version": VERSION,
        "last_updated": "2026-07-08",
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "presubmission_packet": {
            "contract_input": str(args.contract_input),
            "r49_verifier": str(args.r49_verifier),
            "presubmission_output": str(args.presubmission_output),
            "row": row,
            "evaluation": evaluation,
        },
        "requirements": requirements,
        "summary": summary,
        "claim_boundary": {
            "what_is_supported": (
                "R50 binds the existing C01 evidence files into a hash-matched "
                "pre-submission row and proves the file/hash layer can be closed "
                "without accepting C2."
            ),
            "what_is_not_supported": (
                "R50 does not provide source-backed replay, a real same-unitary "
                "certificate, a verifier signature, C2 acceptance, O3 closure, "
                "reroute permission, or B7/STV credit."
            ),
            "next_gate": (
                "Replace the smoke witness, dry-run verifier, and signature blocker "
                "with source-backed replay evidence and a real same-unitary verifier; "
                "then rerun R49 and R47."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": failed,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    s = payload["summary"]
    lines = [
        "# B1/B7 Cone01 R50 O3-F4 C2 C01 Hash-Matched Pre-Submission Gate",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Upstream target: `{payload['upstream_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Selected challenge: `{s['selected_challenge_id']}`",
        f"- Presubmission row hash: `{s['presubmission_row_hash']}`",
        f"- Evaluation hash: `{s['evaluation_hash']}`",
        "",
        "## Result",
        "",
        (
            f"R50 passes {s['requirements_passed']}/{s['requirement_count']} "
            "requirements by closing the C01 file/hash surface while keeping the "
            "row rejected on source-backed flags."
        ),
        "",
        "## Rejection Surface",
        "",
        f"- R49 baseline file-hash failures: `{s['r49_baseline_file_hash_failure_count']}`",
        f"- R50 file-hash failures: `{s['file_hash_failure_count']}`",
        f"- Empty production keys: `{s['empty_production_key_count']}`",
        f"- Flag failures: `{s['flag_failure_count']}`",
        f"- Accepted source-backed rows: `{s['accepted_source_backed_row_count']}`",
        f"- Source-backed replay: `{s['source_backed_replay']}`",
        f"- Same-unitary certificate: `{s['same_unitary_certificate']}`",
        f"- Smoke-only blocker: `{s['smoke_only_not_c2_acceptance']}`",
        "",
        "## Requirement Results",
        "",
    ]
    for item in payload["requirements"]:
        lines.append(f"- `{item['requirement_id']}` {'PASS' if item['passed'] else 'FAIL'}: {item['label']}")
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
    parser.add_argument("--r49-result", type=Path, default=Path("results/B1_B7_cone01_R49_o3_f4_c2_source_backed_row_preflight_verifier_gate_v0.json"))
    parser.add_argument("--contract-input", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/B1-B7-cone01-O3-F4-C2-C01-source-backed-row-intake.contract.json"))
    parser.add_argument("--r49-verifier", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/B1-B7-cone01-O3-F4-C2-C01-source-backed-row-preflight.verifier.json"))
    parser.add_argument("--presubmission-output", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_backed_rows/O3-F4-C01.hash_matched_presubmission.json"))
    parser.add_argument("--json-output", type=Path, default=Path("results/B1_B7_cone01_R50_o3_f4_c2_c01_hash_matched_presubmission_gate_v0.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("research/B1_B7_cone01_R50_o3_f4_c2_c01_hash_matched_presubmission_gate.md"))
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_payload(args)
    write_json(args.json_output, payload)
    write_markdown(args.markdown_output, payload)
    if args.pretty:
        s = payload["summary"]
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "selected_challenge_id": s["selected_challenge_id"],
                    "requirements_passed": s["requirements_passed"],
                    "requirements_failed": s["requirements_failed"],
                    "r49_baseline_file_hash_failure_count": s["r49_baseline_file_hash_failure_count"],
                    "file_hash_failure_count": s["file_hash_failure_count"],
                    "flag_failure_count": s["flag_failure_count"],
                    "accepted_source_backed_row_count": s["accepted_source_backed_row_count"],
                    "presubmission_row_hash": s["presubmission_row_hash"],
                    "evaluation_hash": s["evaluation_hash"],
                    "json_output": str(args.json_output),
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
