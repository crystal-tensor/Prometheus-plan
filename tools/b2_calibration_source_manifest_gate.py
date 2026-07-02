#!/usr/bin/env python3
"""T-B2-010d/T-B7-012: calibrated-trace source manifest gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b2_calibration_source_manifest_gate_v0"
STATUS = "calibration_source_manifest_open_missing_artifact"
MODEL_STATUS = "calibration_source_manifest_required_before_calibrated_trace_rows"
VERSION = "0.1"
EXPECTED_MANIFEST_ID = "B2-T5-calibration-source-manifest"
EXPECTED_DOWNSTREAM_PACKET_ID = "B2-T5-calibrated-flag-observation-rows"
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
    priority_gate = load_json(args.priority_packet_gate)
    b7_credit = load_json(args.b7_dependency_credit_gate)
    priority_summary = priority_gate["summary"]
    b7_summary = b7_credit["summary"]
    submission_path = args.submission_dir / f"{EXPECTED_MANIFEST_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None
    required_keys = [
        "manifest_id",
        "downstream_packet_id",
        "calibration_source_type",
        "backend_or_dataset_name",
        "acquisition_window_utc",
        "detector_trace_hashes",
        "flag_event_schema_hash",
        "confusion_matrix_plan_hash",
        "holdout_partition_hash",
        "replay_command_hash",
        "claim_boundary",
    ]
    production_required_keys = [
        "calibration_source_type",
        "backend_or_dataset_name",
        "acquisition_window_utc",
        "detector_trace_hashes",
        "flag_event_schema_hash",
        "holdout_partition_hash",
        "replay_command_hash",
    ]
    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    production_present = [
        key for key in production_required_keys if submitted is not None and submitted.get(key) is not None
    ]
    source_backed = submitted is not None and submitted.get("source_evidence_files_present") is True
    downstream_bound = (
        submitted is not None
        and submitted.get("downstream_packet_id") == EXPECTED_DOWNSTREAM_PACKET_ID
    )
    replay_bound = submitted is not None and bool(submitted.get("detector_trace_hashes")) and bool(
        submitted.get("replay_command_hash")
    )

    manifest_packet = {
        "manifest_id": EXPECTED_MANIFEST_ID,
        "downstream_packet_id": EXPECTED_DOWNSTREAM_PACKET_ID,
        "submission_artifact_path": str(submission_path),
        "source_priority_packet_gate": str(args.priority_packet_gate),
        "source_b7_dependency_credit_gate": str(args.b7_dependency_credit_gate),
        "required_keys": required_keys,
        "production_required_keys": production_required_keys,
        "required_evidence_files": [
            "calibration_source_manifest",
            "backend_or_dataset_access_note",
            "acquisition_window_source",
            "detector_trace_hash_manifest",
            "flag_event_schema_note",
            "confusion_matrix_or_labeling_plan",
            "holdout_partition_manifest",
            "replay_command_and_claim_boundary",
        ],
        "accepted_only_if": [
            "manifest_id equals B2-T5-calibration-source-manifest",
            "downstream_packet_id equals B2-T5-calibrated-flag-observation-rows",
            "calibration source type, backend/dataset name, acquisition window, detector trace hashes, flag schema hash, holdout partition hash, and replay command hash are present",
            "manifest preserves the 3-challenge / 576-trace / 864 holdout profile-shot shape or declares a reviewed replacement denominator",
            "source evidence files are present and hash-bound",
            "claim_boundary forbids production decoder, threshold, calibrated-device, hardware-result, new-code, quantum-advantage, and B7 credit claims",
        ],
    }
    manifest_packet["manifest_hash"] = stable_hash(manifest_packet)

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
            "Priority calibrated-trace packet remains valid and blocked only on P6/P7/P8",
            priority_gate.get("method") == "b2_calibrated_trace_priority_packet_gate_v0"
            and priority_summary.get("validation_error_count") == 0
            and priority_summary.get("failed_priority_requirement_ids") == ["P6", "P7", "P8"],
            {
                "source_status": priority_gate.get("status"),
                "failed_priority_requirement_ids": priority_summary.get("failed_priority_requirement_ids"),
                "validation_error_count": priority_summary.get("validation_error_count"),
            },
        ),
        requirement(
            "P2",
            "Source manifest is bound to the calibrated flag observation row packet",
            priority_summary.get("priority_packet_id") == EXPECTED_DOWNSTREAM_PACKET_ID
            and priority_summary.get("accepted_priority_trace_rows") == 0,
            {
                "downstream_packet_id": priority_summary.get("priority_packet_id"),
                "accepted_priority_trace_rows": priority_summary.get("accepted_priority_trace_rows"),
            },
        ),
        requirement(
            "P3",
            "Manifest packet carries locked schema and evidence file classes",
            len(required_keys) == 11
            and len(production_required_keys) == 7
            and len(manifest_packet["required_evidence_files"]) == 8,
            {
                "required_key_count": len(required_keys),
                "production_required_key_count": len(production_required_keys),
                "required_evidence_file_count": len(manifest_packet["required_evidence_files"]),
            },
        ),
        requirement(
            "P4",
            "Existing B2 trace denominator shape is preserved",
            priority_summary.get("challenge_count") == 3
            and priority_summary.get("source_trace_count") == 576
            and priority_summary.get("holdout_profile_shots") == 864,
            {
                "challenge_count": priority_summary.get("challenge_count"),
                "source_trace_count": priority_summary.get("source_trace_count"),
                "holdout_profile_shots": priority_summary.get("holdout_profile_shots"),
            },
        ),
        requirement(
            "P5",
            "B7 dependency credit remains blocked before calibrated source evidence",
            b7_summary.get("dependency_credit_allowed") is False
            and b7_summary.get("calibrated_flag_data_used") is False
            and b7_summary.get("real_hardware_trace_used") is False
            and b7_summary.get("holdout_improvement_gate_passed") is False,
            {
                "dependency_credit_allowed": b7_summary.get("dependency_credit_allowed"),
                "calibrated_flag_data_used": b7_summary.get("calibrated_flag_data_used"),
                "real_hardware_trace_used": b7_summary.get("real_hardware_trace_used"),
                "holdout_improvement_gate_passed": b7_summary.get("holdout_improvement_gate_passed"),
            },
        ),
        requirement(
            "P6",
            "Calibration source manifest artifact has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted manifest satisfies the locked source schema",
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
            "Submitted manifest is source-backed, downstream-bound, and replay-bound",
            source_backed and downstream_bound and replay_bound,
            {
                "source_evidence_files_present": source_backed,
                "downstream_bound": downstream_bound,
                "replay_bound": replay_bound,
            },
        ),
        requirement(
            "P9",
            "Forbidden decoder, threshold, hardware, advantage, and B7-credit claims remain false",
            all(priority_summary.get(key) is False for key in forbidden_claims)
            and b7_summary.get("dependency_credit_allowed") is False,
            {**{key: priority_summary.get(key) for key in forbidden_claims}, "b7_dependency_credit_allowed": b7_summary.get("dependency_credit_allowed")},
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected calibration source manifest failures: {failed_ids}")
    if submitted_exists:
        validation_errors.append("gate expected no submitted manifest until a hardware-data PR supplies one")

    summary = {
        "manifest_id": EXPECTED_MANIFEST_ID,
        "downstream_packet_id": EXPECTED_DOWNSTREAM_PACKET_ID,
        "manifest_hash": manifest_packet["manifest_hash"],
        "manifest_requirement_count": len(requirements),
        "manifest_requirements_passed": passed,
        "manifest_requirements_failed": len(requirements) - passed,
        "failed_manifest_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "production_required_key_count": len(production_required_keys),
        "required_evidence_file_count": len(manifest_packet["required_evidence_files"]),
        "challenge_count": priority_summary.get("challenge_count"),
        "source_trace_count": priority_summary.get("source_trace_count"),
        "holdout_profile_shots": priority_summary.get("holdout_profile_shots"),
        "submitted_manifest_exists": submitted_exists,
        "missing_key_count": len(missing_keys),
        "production_keys_present_count": len(production_present),
        "accepted_priority_trace_rows": priority_summary.get("accepted_priority_trace_rows"),
        "b7_dependency_credit_allowed": b7_summary.get("dependency_credit_allowed"),
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
        "problem_id": 22,
        "title": "B2 Calibration Source Manifest Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_priority_packet_gate": str(args.priority_packet_gate),
        "source_b7_dependency_credit_gate": str(args.b7_dependency_credit_gate),
        "summary": summary,
        "calibration_source_manifest_packet": manifest_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "The B2 calibrated-trace route now has a concrete source-manifest packet that must be "
                "accepted before calibrated flag observation rows or B7 dependency credit can be considered."
            ),
            "what_is_not_supported": (
                "No calibration source manifest or calibrated trace row has been submitted or accepted; "
                "no production decoder, threshold, hardware result, calibrated-device result, new-code "
                "result, quantum advantage, or B7 resource credit is supported."
            ),
            "next_gate": (
                "Submit B2-T5-calibration-source-manifest with calibration source type, backend/dataset "
                "name, acquisition window, detector trace hashes, flag schema hash, holdout partition "
                "hash, replay command hash, and claim boundary."
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
    packet = payload["calibration_source_manifest_packet"]
    lines = [
        "# B2 Calibration Source Manifest Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Manifest: `{summary['manifest_id']}`",
        f"- Downstream packet: `{summary['downstream_packet_id']}`",
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
        "## Manifest Packet",
        "",
        f"- Submission path: `{packet['submission_artifact_path']}`",
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
        "--priority-packet-gate",
        type=Path,
        default=Path("results/B2_calibrated_trace_priority_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--b7-dependency-credit-gate",
        type=Path,
        default=Path("results/B7_B2_calibrated_dependency_credit_gate_v0.json"),
    )
    parser.add_argument(
        "--submission-dir",
        type=Path,
        default=Path("results/B2_calibration_source_manifest_submissions"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B2_calibration_source_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B2_calibration_source_manifest_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-02")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, pretty=args.pretty)
    write_markdown(payload, args.markdown_output)
    print(json.dumps(payload["summary"], indent=2 if args.pretty else None, sort_keys=True))
    if payload["validation_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
