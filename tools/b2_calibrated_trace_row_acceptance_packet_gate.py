#!/usr/bin/env python3
"""T-B2-010g/T-B7-012f: calibrated-trace row acceptance packet gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b2_calibrated_trace_row_acceptance_packet_gate_v0"
STATUS = "calibrated_trace_row_acceptance_packet_open_missing_artifact"
MODEL_STATUS = "trace_row_acceptance_packet_required_before_b2_b7_credit"
VERSION = "0.1"
EXPECTED_TRACE_PACKET_ID = "B2-T5-calibrated-flag-observation-rows"
EXPECTED_SOURCE_MANIFEST_ID = "B2-T5-calibration-source-manifest"
EXPECTED_PROVENANCE_MANIFEST_ID = "B2-T5-calibrated-trace-row-provenance-manifest"
EXPECTED_REPLAY_MANIFEST_ID = "B2-T5-calibrated-trace-row-replay-validation-manifest"
EXPECTED_ACCEPTANCE_PACKET_ID = "B2-T5-calibrated-trace-row-acceptance-packet"
EXPECTED_FAILED_IDS = ["P6", "P7", "P8"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2 if pretty else None, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def requirement(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    replay = load_json(args.trace_replay_validation_manifest_gate)
    priority = load_json(args.trace_priority_packet_gate)
    replay_summary = replay["summary"]
    priority_summary = priority["summary"]
    submission_path = args.submission_dir / f"{EXPECTED_ACCEPTANCE_PACKET_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None

    required_keys = [
        "acceptance_packet_id",
        "trace_packet_id",
        "calibration_source_manifest_id",
        "provenance_manifest_id",
        "replay_validation_manifest_id",
        "calibration_source_manifest_hash",
        "provenance_manifest_hash",
        "replay_validation_manifest_hash",
        "priority_packet_hash",
        "row_batch_manifest_hash",
        "detector_trace_manifest_hash",
        "decoder_profile_manifest_hash",
        "confusion_matrix_table_hash",
        "posterior_likelihood_table_hash",
        "baseline_prediction_table_hash",
        "injected_prediction_table_hash",
        "holdout_partition_hash",
        "holdout_nonregression_table_hash",
        "all_challenge_coverage_table_hash",
        "accepted_trace_row_count",
        "all_challenge_nonregression_passed",
        "b7_credit_boundary",
        "claim_boundary",
        "source_evidence_files_present",
    ]
    production_required_keys = [
        "replay_validation_manifest_hash",
        "priority_packet_hash",
        "row_batch_manifest_hash",
        "detector_trace_manifest_hash",
        "decoder_profile_manifest_hash",
        "confusion_matrix_table_hash",
        "posterior_likelihood_table_hash",
        "baseline_prediction_table_hash",
        "injected_prediction_table_hash",
        "holdout_partition_hash",
        "holdout_nonregression_table_hash",
        "all_challenge_coverage_table_hash",
        "accepted_trace_row_count",
        "all_challenge_nonregression_passed",
        "b7_credit_boundary",
        "claim_boundary",
    ]
    evidence_files = [
        "accepted_replay_validation_manifest",
        "priority_trace_row_packet",
        "row_batch_manifest",
        "detector_trace_manifest",
        "decoder_profile_manifest",
        "confusion_matrix_table",
        "posterior_likelihood_table",
        "baseline_prediction_table",
        "injected_prediction_table",
        "holdout_partition_manifest",
        "holdout_nonregression_table",
        "all_challenge_coverage_table",
        "calibrated_row_acceptance_ledger",
        "b7_zero_credit_boundary_note",
        "claim_boundary_note",
    ]

    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    production_present = [
        key for key in production_required_keys if submitted is not None and submitted.get(key) is not None
    ]
    manifest_bound = (
        submitted is not None
        and submitted.get("acceptance_packet_id") == EXPECTED_ACCEPTANCE_PACKET_ID
        and submitted.get("trace_packet_id") == EXPECTED_TRACE_PACKET_ID
        and submitted.get("calibration_source_manifest_id") == EXPECTED_SOURCE_MANIFEST_ID
        and submitted.get("provenance_manifest_id") == EXPECTED_PROVENANCE_MANIFEST_ID
        and submitted.get("replay_validation_manifest_id") == EXPECTED_REPLAY_MANIFEST_ID
        and submitted.get("calibration_source_manifest_hash")
        == replay_summary.get("calibration_source_manifest_hash")
        and submitted.get("provenance_manifest_hash") == replay_summary.get("provenance_manifest_hash")
        and submitted.get("replay_validation_manifest_hash") == replay_summary.get("manifest_hash")
        and submitted.get("priority_packet_hash") == priority_summary.get("packet_hash")
    )
    b7_boundary_bound = (
        submitted is not None
        and isinstance(submitted.get("b7_credit_boundary"), dict)
        and submitted["b7_credit_boundary"].get("dependency_credit_allowed") is False
        and submitted["b7_credit_boundary"].get("b7_credit_delta") == 0
    )
    claim_boundary_bound = (
        submitted is not None
        and isinstance(submitted.get("claim_boundary"), dict)
        and submitted["claim_boundary"].get("production_decoder_claimed") is False
        and submitted["claim_boundary"].get("threshold_claimed") is False
        and submitted["claim_boundary"].get("hardware_result_claimed") is False
        and submitted["claim_boundary"].get("calibrated_device_claimed") is False
        and submitted["claim_boundary"].get("quantum_advantage_claimed") is False
    )
    source_backed = submitted is not None and submitted.get("source_evidence_files_present") is True
    row_acceptance_valid = (
        submitted is not None
        and submitted.get("accepted_trace_row_count", -1) > 0
        and submitted.get("all_challenge_nonregression_passed") is True
    )

    acceptance_packet = {
        "acceptance_packet_id": EXPECTED_ACCEPTANCE_PACKET_ID,
        "trace_packet_id": EXPECTED_TRACE_PACKET_ID,
        "calibration_source_manifest_id": EXPECTED_SOURCE_MANIFEST_ID,
        "provenance_manifest_id": EXPECTED_PROVENANCE_MANIFEST_ID,
        "replay_validation_manifest_id": EXPECTED_REPLAY_MANIFEST_ID,
        "source_trace_replay_validation_manifest_gate": str(args.trace_replay_validation_manifest_gate),
        "source_trace_priority_packet_gate": str(args.trace_priority_packet_gate),
        "submission_artifact_path": str(submission_path),
        "calibration_source_manifest_hash": replay_summary.get("calibration_source_manifest_hash"),
        "provenance_manifest_hash": replay_summary.get("provenance_manifest_hash"),
        "replay_validation_manifest_hash": replay_summary.get("manifest_hash"),
        "priority_packet_hash": priority_summary.get("packet_hash"),
        "challenge_count": replay_summary.get("challenge_count"),
        "source_trace_count": replay_summary.get("source_trace_count"),
        "holdout_profile_shots": replay_summary.get("holdout_profile_shots"),
        "required_keys": required_keys,
        "production_required_keys": production_required_keys,
        "required_evidence_files": evidence_files,
        "accepted_only_if": [
            "acceptance_packet_id equals B2-T5-calibrated-trace-row-acceptance-packet",
            "trace, calibration-source, provenance, and replay-validation IDs match source gates",
            "calibration, provenance, replay-validation, and priority-packet hashes match source gates",
            "row batch, detector trace, decoder profile, confusion, posterior, prediction, holdout, and coverage artifacts are hash-bound",
            "accepted_trace_row_count is positive only after all-challenge non-regression passes",
            "B7 dependency credit remains zero until accepted calibrated rows and independent all-challenge evidence exist",
            "claim_boundary forbids production-decoder, threshold, hardware-result, calibrated-device, quantum-advantage, and B7 resource-credit claims",
        ],
    }
    acceptance_packet["packet_hash"] = stable_hash(acceptance_packet)

    forbidden_claims = [
        "production_decoder_claimed",
        "threshold_claimed",
        "new_code_claimed",
        "hardware_result_claimed",
        "calibrated_device_claimed",
        "quantum_advantage_claimed",
    ]
    requirements = [
        requirement(
            "P1",
            "Replay-validation manifest gate remains valid and blocked only on P6/P7/P8",
            replay.get("method") == "b2_calibrated_trace_replay_validation_manifest_gate_v0"
            and replay_summary.get("validation_error_count") == 0
            and replay_summary.get("failed_manifest_requirement_ids") == EXPECTED_FAILED_IDS,
            {
                "source_status": replay.get("status"),
                "failed_manifest_requirement_ids": replay_summary.get("failed_manifest_requirement_ids"),
                "validation_error_count": replay_summary.get("validation_error_count"),
            },
        ),
        requirement(
            "P2",
            "Priority trace packet remains fixed and source-shaped",
            priority.get("method") == "b2_calibrated_trace_priority_packet_gate_v0"
            and priority_summary.get("priority_packet_id") == EXPECTED_TRACE_PACKET_ID
            and priority_summary.get("validation_error_count") == 0
            and priority_summary.get("failed_priority_requirement_ids") == EXPECTED_FAILED_IDS,
            {
                "priority_packet_id": priority_summary.get("priority_packet_id"),
                "packet_hash": priority_summary.get("packet_hash"),
                "failed_priority_requirement_ids": priority_summary.get("failed_priority_requirement_ids"),
            },
        ),
        requirement(
            "P3",
            "Acceptance packet carries locked row acceptance schema and evidence classes",
            len(required_keys) == 24
            and len(production_required_keys) == 16
            and len(evidence_files) == 15,
            {
                "required_key_count": len(required_keys),
                "production_required_key_count": len(production_required_keys),
                "required_evidence_file_count": len(evidence_files),
            },
        ),
        requirement(
            "P4",
            "Existing calibrated trace scope is preserved",
            replay_summary.get("challenge_count") == 3
            and replay_summary.get("source_trace_count") == 576
            and replay_summary.get("holdout_profile_shots") == 864,
            {
                "challenge_count": replay_summary.get("challenge_count"),
                "source_trace_count": replay_summary.get("source_trace_count"),
                "holdout_profile_shots": replay_summary.get("holdout_profile_shots"),
            },
        ),
        requirement(
            "P5",
            "B7 dependency credit remains blocked before accepted calibrated trace rows",
            replay_summary.get("b7_dependency_credit_allowed") is False
            and replay_summary.get("accepted_priority_trace_rows") == 0,
            {
                "b7_dependency_credit_allowed": replay_summary.get("b7_dependency_credit_allowed"),
                "accepted_priority_trace_rows": replay_summary.get("accepted_priority_trace_rows"),
            },
        ),
        requirement(
            "P6",
            "Calibrated trace row acceptance packet has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted acceptance packet satisfies the locked calibrated-trace row schema",
            submitted_exists and not missing_keys and len(production_present) == len(production_required_keys),
            {
                "missing_keys": missing_keys,
                "production_keys_present": production_present,
                "production_required_keys": production_required_keys,
                "submitted_key_count": len(submitted) if submitted else 0,
            },
        ),
        requirement(
            "P8",
            "Submitted acceptance packet is source-backed, manifest-bound, row-valid, B7-boundary-bound, and claim-boundary-bound",
            source_backed and manifest_bound and row_acceptance_valid and b7_boundary_bound and claim_boundary_bound,
            {
                "source_backed": source_backed,
                "manifest_bound": manifest_bound,
                "row_acceptance_valid": row_acceptance_valid,
                "b7_boundary_bound": b7_boundary_bound,
                "claim_boundary_bound": claim_boundary_bound,
            },
        ),
        requirement(
            "P9",
            "Forbidden decoder, threshold, hardware, advantage, and B7-credit claims remain false",
            all(replay_summary.get(key) is False for key in forbidden_claims)
            and replay_summary.get("b7_dependency_credit_allowed") is False,
            {
                **{key: replay_summary.get(key) for key in forbidden_claims},
                "b7_dependency_credit_allowed": replay_summary.get("b7_dependency_credit_allowed"),
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected trace row acceptance packet failures: {failed_ids}")
    if submitted_exists:
        validation_errors.append("gate expected no submitted acceptance packet until a hardware-data PR supplies one")

    summary = {
        "acceptance_packet_id": EXPECTED_ACCEPTANCE_PACKET_ID,
        "trace_packet_id": EXPECTED_TRACE_PACKET_ID,
        "calibration_source_manifest_id": EXPECTED_SOURCE_MANIFEST_ID,
        "provenance_manifest_id": EXPECTED_PROVENANCE_MANIFEST_ID,
        "replay_validation_manifest_id": EXPECTED_REPLAY_MANIFEST_ID,
        "calibration_source_manifest_hash": replay_summary.get("calibration_source_manifest_hash"),
        "provenance_manifest_hash": replay_summary.get("provenance_manifest_hash"),
        "replay_validation_manifest_hash": replay_summary.get("manifest_hash"),
        "priority_packet_hash": priority_summary.get("packet_hash"),
        "acceptance_packet_hash": acceptance_packet["packet_hash"],
        "acceptance_requirement_count": len(requirements),
        "acceptance_requirements_passed": passed,
        "acceptance_requirements_failed": len(requirements) - passed,
        "failed_acceptance_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "production_required_key_count": len(production_required_keys),
        "required_evidence_file_count": len(evidence_files),
        "challenge_count": replay_summary.get("challenge_count"),
        "source_trace_count": replay_summary.get("source_trace_count"),
        "holdout_profile_shots": replay_summary.get("holdout_profile_shots"),
        "submitted_acceptance_packet_exists": submitted_exists,
        "submitted_key_count": len(submitted) if submitted else 0,
        "missing_key_count": len(missing_keys),
        "production_keys_present_count": len(production_present),
        "accepted_priority_trace_rows": 0,
        "b7_dependency_credit_allowed": False,
        "b7_credit_delta": 0,
        "production_decoder_claimed": False,
        "threshold_claimed": False,
        "new_code_claimed": False,
        "hardware_result_claimed": False,
        "calibrated_device_claimed": False,
        "quantum_advantage_claimed": False,
        "validation_error_count": len(validation_errors),
    }
    return {
        "benchmark_id": "B2",
        "linked_benchmark_id": "B7",
        "problem_id": 22,
        "title": "B2 Calibrated Trace Row Acceptance Packet Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_trace_replay_validation_manifest_gate": str(args.trace_replay_validation_manifest_gate),
        "source_trace_priority_packet_gate": str(args.trace_priority_packet_gate),
        "summary": summary,
        "calibrated_trace_row_acceptance_packet": acceptance_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "The B2/B7 calibrated-trace path now has a row acceptance packet that binds "
                "the replay-validation manifest, priority packet hash, row batch, detector traces, "
                "decoder profiles, holdout non-regression, all-challenge coverage, and B7 zero-credit boundary."
            ),
            "what_is_not_supported": (
                "No calibrated trace row acceptance packet or calibrated row artifact has been submitted or "
                "accepted; no production decoder, threshold, hardware result, calibrated-device result, "
                "quantum advantage, or B7 resource credit is supported."
            ),
            "next_gate": (
                "Submit B2-T5-calibrated-trace-row-acceptance-packet with accepted replay manifest hash, "
                "source-backed row batch replay, all-challenge non-regression, calibrated row acceptance "
                "ledger, B7 zero-credit boundary, and claim boundary."
            ),
            "production_decoder_claimed": False,
            "threshold_claimed": False,
            "new_code_claimed": False,
            "hardware_result_claimed": False,
            "calibrated_device_claimed": False,
            "quantum_advantage_claimed": False,
            "b7_dependency_credit_allowed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    packet = payload["calibrated_trace_row_acceptance_packet"]
    lines = [
        "# B2 Calibrated Trace Row Acceptance Packet Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Acceptance packet: `{summary['acceptance_packet_id']}`",
        f"- Trace packet: `{summary['trace_packet_id']}`",
        f"- Replay-validation manifest: `{summary['replay_validation_manifest_id']}`",
        f"- Replay-validation manifest hash: `{summary['replay_validation_manifest_hash']}`",
        f"- Priority packet hash: `{summary['priority_packet_hash']}`",
        f"- Acceptance packet hash: `{summary['acceptance_packet_hash']}`",
        f"- Requirements passed/failed: `{summary['acceptance_requirements_passed']}` / `{summary['acceptance_requirements_failed']}`",
        f"- Failed requirement IDs: `{summary['failed_acceptance_requirement_ids']}`",
        f"- Required key / production key / evidence file count: `{summary['required_key_count']}` / `{summary['production_required_key_count']}` / `{summary['required_evidence_file_count']}`",
        f"- Challenge count / source traces / holdout profile shots: `{summary['challenge_count']}` / `{summary['source_trace_count']}` / `{summary['holdout_profile_shots']}`",
        f"- Submitted acceptance packet exists: `{summary['submitted_acceptance_packet_exists']}`",
        f"- Accepted priority trace rows: `{summary['accepted_priority_trace_rows']}`",
        f"- B7 dependency credit allowed: `{summary['b7_dependency_credit_allowed']}`",
        f"- validation_error_count: `{summary['validation_error_count']}`",
        "",
        "## Acceptance Packet",
        "",
        f"- Submission path: `{packet['submission_artifact_path']}`",
        f"- Packet hash: `{packet['packet_hash']}`",
        "",
        "Required evidence files:",
        "",
    ]
    for item in packet["required_evidence_files"]:
        lines.append(f"- {item}")
    lines.extend(["", "Acceptance predicates:", ""])
    for item in packet["accepted_only_if"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Requirement Results", ""])
    for row in payload["requirements"]:
        state = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- {row['requirement_id']} [{state}]: {row['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            f"- production_decoder_claimed: {payload['claim_boundary']['production_decoder_claimed']}",
            f"- threshold_claimed: {payload['claim_boundary']['threshold_claimed']}",
            f"- hardware_result_claimed: {payload['claim_boundary']['hardware_result_claimed']}",
            f"- calibrated_device_claimed: {payload['claim_boundary']['calibrated_device_claimed']}",
            f"- quantum_advantage_claimed: {payload['claim_boundary']['quantum_advantage_claimed']}",
            f"- b7_dependency_credit_allowed: {payload['claim_boundary']['b7_dependency_credit_allowed']}",
            "",
            "## Validation",
            "",
            f"- validation_error_count: {summary['validation_error_count']}",
        ]
    )
    if payload["validation_errors"]:
        for error in payload["validation_errors"]:
            lines.append(f"- {error}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--trace-replay-validation-manifest-gate",
        type=Path,
        default=Path("results/B2_calibrated_trace_replay_validation_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--trace-priority-packet-gate",
        type=Path,
        default=Path("results/B2_calibrated_trace_priority_packet_gate_v0.json"),
    )
    parser.add_argument("--submission-dir", type=Path, default=Path("research/submissions"))
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B2_calibrated_trace_row_acceptance_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B2_calibrated_trace_row_acceptance_packet_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-03")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    write_markdown(payload, args.markdown_output)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    if payload["validation_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
