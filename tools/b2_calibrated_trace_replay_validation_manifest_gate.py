#!/usr/bin/env python3
"""T-B2-010f/T-B7-012d: calibrated-trace replay-validation manifest gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b2_calibrated_trace_replay_validation_manifest_gate_v0"
STATUS = "calibrated_trace_replay_validation_manifest_open_missing_artifact"
MODEL_STATUS = "trace_replay_validation_manifest_required_before_b2_b7_credit"
VERSION = "0.1"
EXPECTED_SOURCE_MANIFEST_ID = "B2-T5-calibration-source-manifest"
EXPECTED_TRACE_PACKET_ID = "B2-T5-calibrated-flag-observation-rows"
EXPECTED_PROVENANCE_MANIFEST_ID = "B2-T5-calibrated-trace-row-provenance-manifest"
EXPECTED_REPLAY_MANIFEST_ID = "B2-T5-calibrated-trace-row-replay-validation-manifest"
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
    provenance = load_json(args.trace_provenance_manifest_gate)
    b7_credit = load_json(args.b7_dependency_credit_gate)
    provenance_summary = provenance["summary"]
    provenance_packet = provenance["calibrated_trace_provenance_manifest_packet"]
    b7_summary = b7_credit["summary"]
    submission_path = args.submission_dir / f"{EXPECTED_REPLAY_MANIFEST_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None

    required_keys = [
        "manifest_id",
        "provenance_manifest_id",
        "calibration_source_manifest_id",
        "trace_packet_id",
        "calibration_source_manifest_hash",
        "provenance_manifest_hash",
        "row_batch_replay_hash",
        "detector_trace_replay_hash",
        "decoder_profile_replay_hash",
        "confusion_matrix_replay_hash",
        "posterior_likelihood_replay_hash",
        "baseline_prediction_replay_hash",
        "injected_prediction_replay_hash",
        "holdout_partition_replay_hash",
        "holdout_nonregression_replay_hash",
        "all_challenge_coverage_replay_hash",
        "b7_credit_boundary",
        "claim_boundary",
    ]
    production_required_keys = [
        "provenance_manifest_hash",
        "row_batch_replay_hash",
        "detector_trace_replay_hash",
        "decoder_profile_replay_hash",
        "confusion_matrix_replay_hash",
        "posterior_likelihood_replay_hash",
        "baseline_prediction_replay_hash",
        "injected_prediction_replay_hash",
        "holdout_partition_replay_hash",
        "holdout_nonregression_replay_hash",
        "all_challenge_coverage_replay_hash",
        "b7_credit_boundary",
        "claim_boundary",
    ]
    evidence_files = [
        "accepted_calibrated_trace_provenance_manifest",
        "row_batch_replay_manifest",
        "detector_trace_replay_manifest",
        "decoder_profile_replay_manifest",
        "confusion_matrix_replay_artifact",
        "posterior_likelihood_replay_table",
        "baseline_prediction_replay_manifest",
        "injected_prediction_replay_manifest",
        "holdout_partition_replay_manifest",
        "holdout_nonregression_replay_table",
        "all_challenge_coverage_replay_table",
        "b7_credit_boundary_note",
        "claim_boundary_note",
    ]

    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    production_present = [
        key for key in production_required_keys if submitted is not None and submitted.get(key) is not None
    ]
    replay_hashes = submitted.get("replay_hashes") if submitted else None
    replay_bound = (
        isinstance(replay_hashes, dict)
        and replay_hashes.get("provenance_manifest_hash") == provenance_summary.get("manifest_hash")
        and replay_hashes.get("calibration_source_manifest_hash")
        == provenance_summary.get("calibration_source_manifest_hash")
        and replay_hashes.get("trace_packet_id") == EXPECTED_TRACE_PACKET_ID
    )
    source_backed = submitted is not None and submitted.get("source_evidence_files_present") is True
    manifest_bound = (
        submitted is not None
        and submitted.get("manifest_id") == EXPECTED_REPLAY_MANIFEST_ID
        and submitted.get("provenance_manifest_id") == EXPECTED_PROVENANCE_MANIFEST_ID
        and submitted.get("calibration_source_manifest_id") == EXPECTED_SOURCE_MANIFEST_ID
        and submitted.get("trace_packet_id") == EXPECTED_TRACE_PACKET_ID
        and submitted.get("calibration_source_manifest_hash")
        == provenance_summary.get("calibration_source_manifest_hash")
        and submitted.get("provenance_manifest_hash") == provenance_summary.get("manifest_hash")
    )
    b7_boundary_declared = (
        submitted is not None
        and isinstance(submitted.get("b7_credit_boundary"), dict)
        and submitted["b7_credit_boundary"].get("dependency_credit_allowed") is False
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

    replay_packet = {
        "manifest_id": EXPECTED_REPLAY_MANIFEST_ID,
        "provenance_manifest_id": EXPECTED_PROVENANCE_MANIFEST_ID,
        "calibration_source_manifest_id": EXPECTED_SOURCE_MANIFEST_ID,
        "trace_packet_id": EXPECTED_TRACE_PACKET_ID,
        "source_trace_provenance_manifest_gate": str(args.trace_provenance_manifest_gate),
        "source_b7_dependency_credit_gate": str(args.b7_dependency_credit_gate),
        "submission_artifact_path": str(submission_path),
        "calibration_source_manifest_hash": provenance_summary.get("calibration_source_manifest_hash"),
        "provenance_manifest_hash": provenance_summary.get("manifest_hash"),
        "challenge_count": provenance_summary.get("challenge_count"),
        "source_trace_count": provenance_summary.get("source_trace_count"),
        "holdout_profile_shots": provenance_summary.get("holdout_profile_shots"),
        "required_keys": required_keys,
        "production_required_keys": production_required_keys,
        "required_evidence_files": evidence_files,
        "accepted_only_if": [
            "manifest_id equals B2-T5-calibrated-trace-row-replay-validation-manifest",
            "provenance_manifest_id equals B2-T5-calibrated-trace-row-provenance-manifest",
            "calibration_source_manifest_id and trace_packet_id match the source gates",
            "calibration_source_manifest_hash and provenance_manifest_hash match the accepted source gates",
            "row batch, detector trace, decoder profile, confusion matrix, posterior likelihood, baseline prediction, injected prediction, and holdout partition replays are hash-bound",
            "holdout non-regression and all-challenge coverage replay tables are hash-bound",
            "b7_credit_boundary keeps dependency_credit_allowed false until accepted calibrated rows and all-challenge non-regression exist",
            "source evidence files are present and replay_hashes bind provenance, calibration source, and trace identifiers",
            "claim_boundary forbids production decoder, threshold, calibrated-device, hardware-result, new-code, quantum-advantage, and B7 resource-credit claims",
        ],
    }
    replay_packet["manifest_hash"] = stable_hash(replay_packet)

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
            "Calibrated trace provenance manifest remains valid and blocked only on P6/P7/P8",
            provenance.get("method") == "b2_calibrated_trace_provenance_manifest_gate_v0"
            and provenance_summary.get("validation_error_count") == 0
            and provenance_summary.get("failed_manifest_requirement_ids") == ["P6", "P7", "P8"],
            {
                "source_status": provenance.get("status"),
                "failed_manifest_requirement_ids": provenance_summary.get("failed_manifest_requirement_ids"),
                "validation_error_count": provenance_summary.get("validation_error_count"),
            },
        ),
        requirement(
            "P2",
            "Replay manifest is bound to source, provenance, and calibrated trace packet",
            provenance_summary.get("manifest_id") == EXPECTED_PROVENANCE_MANIFEST_ID
            and provenance_summary.get("calibration_source_manifest_id") == EXPECTED_SOURCE_MANIFEST_ID
            and provenance_summary.get("trace_packet_id") == EXPECTED_TRACE_PACKET_ID
            and provenance_packet.get("manifest_hash") == provenance_summary.get("manifest_hash"),
            {
                "provenance_manifest_id": provenance_summary.get("manifest_id"),
                "calibration_source_manifest_id": provenance_summary.get("calibration_source_manifest_id"),
                "trace_packet_id": provenance_summary.get("trace_packet_id"),
                "provenance_manifest_hash": provenance_summary.get("manifest_hash"),
            },
        ),
        requirement(
            "P3",
            "Replay manifest packet carries locked replay schema and evidence classes",
            len(required_keys) == 18
            and len(production_required_keys) == 13
            and len(evidence_files) == 13,
            {
                "required_key_count": len(required_keys),
                "production_required_key_count": len(production_required_keys),
                "required_evidence_file_count": len(evidence_files),
            },
        ),
        requirement(
            "P4",
            "Existing calibrated trace denominator shape is preserved",
            provenance_summary.get("challenge_count") == 3
            and provenance_summary.get("source_trace_count") == 576
            and provenance_summary.get("holdout_profile_shots") == 864,
            {
                "challenge_count": provenance_summary.get("challenge_count"),
                "source_trace_count": provenance_summary.get("source_trace_count"),
                "holdout_profile_shots": provenance_summary.get("holdout_profile_shots"),
            },
        ),
        requirement(
            "P5",
            "B7 dependency credit remains blocked before accepted replay-validated rows",
            b7_summary.get("dependency_credit_allowed") is False
            and provenance_summary.get("b7_dependency_credit_allowed") is False
            and provenance_summary.get("accepted_priority_trace_rows") == 0,
            {
                "b7_dependency_credit_allowed": b7_summary.get("dependency_credit_allowed"),
                "provenance_b7_dependency_credit_allowed": provenance_summary.get(
                    "b7_dependency_credit_allowed"
                ),
                "accepted_priority_trace_rows": provenance_summary.get("accepted_priority_trace_rows"),
            },
        ),
        requirement(
            "P6",
            "Calibrated trace replay-validation manifest artifact has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted replay manifest satisfies the locked calibrated-trace replay schema",
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
            "Submitted replay manifest is source-backed, manifest-bound, replay-bound, B7-boundary-bound, and claim-boundary-bound",
            source_backed
            and manifest_bound
            and replay_bound
            and b7_boundary_declared
            and claim_boundary_bound,
            {
                "source_evidence_files_present": source_backed,
                "manifest_bound": manifest_bound,
                "replay_bound": replay_bound,
                "b7_boundary_declared": b7_boundary_declared,
                "claim_boundary_bound": claim_boundary_bound,
            },
        ),
        requirement(
            "P9",
            "Forbidden decoder, threshold, hardware, advantage, and B7-credit claims remain false",
            all(provenance_summary.get(key) is False for key in forbidden_claims)
            and b7_summary.get("dependency_credit_allowed") is False,
            {
                **{key: provenance_summary.get(key) for key in forbidden_claims},
                "b7_dependency_credit_allowed": b7_summary.get("dependency_credit_allowed"),
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected trace replay manifest failures: {failed_ids}")
    if submitted_exists:
        validation_errors.append("gate expected no submitted replay manifest until a hardware-data PR supplies one")

    summary = {
        "manifest_id": EXPECTED_REPLAY_MANIFEST_ID,
        "provenance_manifest_id": EXPECTED_PROVENANCE_MANIFEST_ID,
        "calibration_source_manifest_id": EXPECTED_SOURCE_MANIFEST_ID,
        "trace_packet_id": EXPECTED_TRACE_PACKET_ID,
        "calibration_source_manifest_hash": provenance_summary.get("calibration_source_manifest_hash"),
        "provenance_manifest_hash": provenance_summary.get("manifest_hash"),
        "manifest_hash": replay_packet["manifest_hash"],
        "manifest_requirement_count": len(requirements),
        "manifest_requirements_passed": passed,
        "manifest_requirements_failed": len(requirements) - passed,
        "failed_manifest_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "production_required_key_count": len(production_required_keys),
        "required_evidence_file_count": len(evidence_files),
        "challenge_count": provenance_summary.get("challenge_count"),
        "source_trace_count": provenance_summary.get("source_trace_count"),
        "holdout_profile_shots": provenance_summary.get("holdout_profile_shots"),
        "submitted_manifest_exists": submitted_exists,
        "submitted_key_count": len(submitted) if submitted else 0,
        "missing_key_count": len(missing_keys),
        "production_keys_present_count": len(production_present),
        "accepted_priority_trace_rows": provenance_summary.get("accepted_priority_trace_rows"),
        "b7_dependency_credit_allowed": False,
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
        "title": "B2 Calibrated Trace Replay-Validation Manifest Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_trace_provenance_manifest_gate": str(args.trace_provenance_manifest_gate),
        "source_b7_dependency_credit_gate": str(args.b7_dependency_credit_gate),
        "summary": summary,
        "calibrated_trace_replay_validation_manifest_packet": replay_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "The B2/B7 calibrated-trace path now has a replay-validation manifest packet "
                "that must bind row, detector, decoder, posterior, prediction, holdout, all-challenge, "
                "and B7 zero-credit replay evidence before calibrated rows can count."
            ),
            "what_is_not_supported": (
                "No calibrated trace replay-validation manifest or calibrated trace row has been "
                "submitted or accepted; no production decoder, threshold, hardware result, "
                "calibrated-device result, new-code result, quantum advantage, or B7 resource credit is supported."
            ),
            "next_gate": (
                "Submit B2-T5-calibrated-trace-row-replay-validation-manifest with the accepted "
                "trace provenance hash, row/detector/decoder replay hashes, holdout non-regression, "
                "all-challenge coverage, and explicit B7 zero-credit boundary."
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
    packet = payload["calibrated_trace_replay_validation_manifest_packet"]
    lines = [
        "# B2 Calibrated Trace Replay-Validation Manifest Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Manifest: `{summary['manifest_id']}`",
        f"- Provenance manifest: `{summary['provenance_manifest_id']}`",
        f"- Calibration source manifest: `{summary['calibration_source_manifest_id']}`",
        f"- Trace packet: `{summary['trace_packet_id']}`",
        f"- Calibration source manifest hash: `{summary['calibration_source_manifest_hash']}`",
        f"- Provenance manifest hash: `{summary['provenance_manifest_hash']}`",
        f"- Manifest hash: `{summary['manifest_hash']}`",
        f"- Requirements passed/failed: `{summary['manifest_requirements_passed']}` / `{summary['manifest_requirements_failed']}`",
        f"- Failed requirement IDs: `{summary['failed_manifest_requirement_ids']}`",
        f"- Required key / production key / evidence file count: `{summary['required_key_count']}` / `{summary['production_required_key_count']}` / `{summary['required_evidence_file_count']}`",
        f"- Challenge count / source traces / holdout profile shots: `{summary['challenge_count']}` / `{summary['source_trace_count']}` / `{summary['holdout_profile_shots']}`",
        f"- Submitted manifest exists: `{summary['submitted_manifest_exists']}`",
        f"- Accepted priority trace rows: `{summary['accepted_priority_trace_rows']}`",
        f"- B7 dependency credit allowed: `{summary['b7_dependency_credit_allowed']}`",
        f"- validation_error_count: `{summary['validation_error_count']}`",
        "",
        "## Replay-Validation Manifest Packet",
        "",
        f"- Submission path: `{packet['submission_artifact_path']}`",
        f"- Provenance manifest hash: `{packet['provenance_manifest_hash']}`",
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
        "--trace-provenance-manifest-gate",
        type=Path,
        default=Path("results/B2_calibrated_trace_provenance_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--b7-dependency-credit-gate",
        type=Path,
        default=Path("results/B7_B2_calibrated_dependency_credit_gate_v0.json"),
    )
    parser.add_argument(
        "--submission-dir",
        type=Path,
        default=Path("results/B2_calibrated_trace_replay_validation_manifest_submissions"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B2_calibrated_trace_replay_validation_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B2_calibrated_trace_replay_validation_manifest_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-02")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    write_markdown(payload, args.markdown_output)
    print(json.dumps(payload["summary"], indent=2 if args.pretty else None, sort_keys=True))
    if payload["validation_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
