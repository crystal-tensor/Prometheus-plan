#!/usr/bin/env python3
"""T-B4-002q/T-B8-003u/T-B10-009i: H1 provider/session replay packet gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b4_b8_h1_provider_session_replay_packet_gate_v0"
STATUS = "h1_provider_session_replay_packet_open_missing_artifact"
MODEL_STATUS = "h1_provider_session_device_property_replay_contract_ready_no_credit"
VERSION = "0.1"
EXPECTED_PACKET_ID = "B4B8-H1-provider-session-device-property-replay"
EXPECTED_PROVIDER_PACKET_ID = "B4B8-M6-provider-session-manifest"
EXPECTED_TRANSCRIPT_PACKET_ID = "B4B8-M6-real-backend-transcript-rows"
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
    triage = load_json(args.post_boundary_triage)
    provider_gate = load_json(args.provider_manifest_gate)
    triage_summary = triage["summary"]
    provider_summary = provider_gate["summary"]
    submission_path = args.submission_dir / f"{EXPECTED_PACKET_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None

    required_keys = [
        "packet_id",
        "source_triage_id",
        "source_provider_packet_id",
        "provider_name",
        "backend_name",
        "access_mode",
        "session_or_queue_id_hash",
        "calibration_window_utc",
        "backend_properties_hash",
        "device_properties_snapshot_hash",
        "runnable_circuit_manifest_hash",
        "shot_budget",
        "private_predicate_handling_hash",
        "redaction_policy_hash",
        "claim_boundary",
    ]
    production_required_keys = [
        "provider_name",
        "backend_name",
        "access_mode",
        "session_or_queue_id_hash",
        "calibration_window_utc",
        "backend_properties_hash",
        "device_properties_snapshot_hash",
        "runnable_circuit_manifest_hash",
        "shot_budget",
        "claim_boundary",
    ]
    required_evidence_files = [
        "provider_access_manifest",
        "session_or_queue_receipt_hash",
        "backend_properties_snapshot",
        "device_properties_snapshot",
        "calibration_window_source",
        "runnable_circuit_manifest",
        "shot_budget_or_job_plan",
        "private_predicate_handling_plan",
        "hashing_and_redaction_manifest",
        "hardware_execution_exclusion_note",
        "claim_boundary_note",
    ]

    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    production_present = [
        key for key in production_required_keys if submitted is not None and submitted.get(key) is not None
    ]
    source_backed = submitted is not None and submitted.get("source_evidence_files_present") is True
    provider_bound = (
        submitted is not None
        and submitted.get("source_provider_packet_id") == EXPECTED_PROVIDER_PACKET_ID
    )
    transcript_bound = (
        submitted is not None
        and submitted.get("downstream_transcript_packet_id") == EXPECTED_TRANSCRIPT_PACKET_ID
    )
    budget_sufficient = (
        submitted is not None
        and isinstance(submitted.get("shot_budget"), int)
        and submitted.get("shot_budget", 0) >= triage_summary.get("holdout_row_count", 160)
    )

    h1_packet = {
        "packet_id": EXPECTED_PACKET_ID,
        "work_packet_id": "H1",
        "source_post_boundary_triage": str(args.post_boundary_triage),
        "source_provider_manifest_gate": str(args.provider_manifest_gate),
        "source_triage_hash": triage_summary.get("triage_hash"),
        "source_provider_packet_hash": provider_summary.get("packet_hash"),
        "source_provider_packet_id": EXPECTED_PROVIDER_PACKET_ID,
        "blocks_transcript_packet": EXPECTED_TRANSCRIPT_PACKET_ID,
        "submission_artifact_path": str(submission_path),
        "required_keys": required_keys,
        "production_required_keys": production_required_keys,
        "required_evidence_files": required_evidence_files,
        "accepted_only_if": [
            "packet_id equals B4B8-H1-provider-session-device-property-replay",
            "source_provider_packet_id equals B4B8-M6-provider-session-manifest",
            "downstream_transcript_packet_id equals B4B8-M6-real-backend-transcript-rows",
            "provider, backend, access mode, session hash, calibration window, backend properties hash, device properties snapshot hash, runnable circuit manifest hash, and shot budget are present",
            "shot_budget covers at least the locked 160-row denominator or declares a reviewed replacement denominator",
            "source evidence files are present and hash-bound",
            "claim_boundary explicitly forbids hardware execution, accepted transcript rows, protocol soundness, quantum advantage, sampling hardness, cryptographic soundness, and BQP separation claims",
        ],
        "margin_retest_budgets": {
            "holdout_row_count": triage_summary.get("holdout_row_count"),
            "leakage_blind_no_leak_allowed_accepts_per_160": triage_summary.get(
                "no_leak_allowed_accepts_per_160"
            ),
            "full_private_material_leak_allowed_accepts_per_160": triage_summary.get(
                "full_leak_allowed_accepts_per_160"
            ),
        },
    }
    h1_packet["packet_hash"] = stable_hash(h1_packet)

    requirements = [
        requirement(
            "P1",
            "Post-boundary triage is valid and exposes H1 as a ready PR packet",
            triage.get("method") == "b4_b8_real_backend_transcript_post_boundary_submission_triage_v0"
            and triage_summary.get("validation_error_count") == 0
            and "H1" in triage_summary.get("ready_packet_ids", []),
            {
                "source_method": triage.get("method"),
                "ready_packet_ids": triage_summary.get("ready_packet_ids"),
                "validation_error_count": triage_summary.get("validation_error_count"),
            },
        ),
        requirement(
            "P2",
            "H5 remains blocked while transcript rows and accepted rows are zero",
            triage_summary.get("blocked_packet_ids") == ["H5"]
            and triage_summary.get("real_backend_transcript_rows") == 0
            and triage_summary.get("accepted_priority_transcript_rows") == 0,
            {
                "blocked_packet_ids": triage_summary.get("blocked_packet_ids"),
                "real_backend_transcript_rows": triage_summary.get("real_backend_transcript_rows"),
                "accepted_priority_transcript_rows": triage_summary.get(
                    "accepted_priority_transcript_rows"
                ),
            },
        ),
        requirement(
            "P3",
            "Existing provider manifest gate is still the H1 source and remains open on P6/P7/P8",
            provider_gate.get("method") == "b4_b8_real_backend_provider_manifest_gate_v0"
            and provider_summary.get("priority_packet_id") == EXPECTED_PROVIDER_PACKET_ID
            and provider_summary.get("failed_priority_requirement_ids") == EXPECTED_FAILED_IDS,
            {
                "source_method": provider_gate.get("method"),
                "priority_packet_id": provider_summary.get("priority_packet_id"),
                "failed_priority_requirement_ids": provider_summary.get(
                    "failed_priority_requirement_ids"
                ),
                "packet_hash": provider_summary.get("packet_hash"),
            },
        ),
        requirement(
            "P4",
            "Locked B4/B8 transcript budgets are preserved",
            triage_summary.get("holdout_row_count") == 160
            and triage_summary.get("no_leak_allowed_accepts_per_160") == 16
            and triage_summary.get("full_leak_allowed_accepts_per_160") == 40,
            {
                "holdout_row_count": triage_summary.get("holdout_row_count"),
                "no_leak_allowed_accepts_per_160": triage_summary.get(
                    "no_leak_allowed_accepts_per_160"
                ),
                "full_leak_allowed_accepts_per_160": triage_summary.get(
                    "full_leak_allowed_accepts_per_160"
                ),
            },
        ),
        requirement(
            "P5",
            "H1 packet schema and evidence classes are locked",
            len(required_keys) == 15
            and len(production_required_keys) == 10
            and len(required_evidence_files) == 11,
            {
                "required_key_count": len(required_keys),
                "production_required_key_count": len(production_required_keys),
                "required_evidence_file_count": len(required_evidence_files),
            },
        ),
        requirement(
            "P6",
            "H1 provider/session/device-property replay artifact has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted H1 replay artifact satisfies the locked schema",
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
            "Submitted H1 replay artifact is source-backed, provider-bound, transcript-bound, and budget-sufficient",
            source_backed and provider_bound and transcript_bound and budget_sufficient,
            {
                "source_evidence_files_present": source_backed,
                "provider_bound": provider_bound,
                "transcript_bound": transcript_bound,
                "budget_sufficient": budget_sufficient,
                "shot_budget": submitted.get("shot_budget") if submitted else None,
            },
        ),
        requirement(
            "P9",
            "Forbidden B8/B4/B10 soundness, advantage, and BQP claims remain false",
            triage_summary.get("b8_protocol_soundness_credit_allowed") is False
            and triage_summary.get("b4_verifiable_advantage_credit_allowed") is False
            and triage_summary.get("b10_t2_credit_allowed") is False
            and triage_summary.get("b10_bqp_separation_credit_allowed") is False,
            {
                "b8_protocol_soundness_credit_allowed": triage_summary.get(
                    "b8_protocol_soundness_credit_allowed"
                ),
                "b4_verifiable_advantage_credit_allowed": triage_summary.get(
                    "b4_verifiable_advantage_credit_allowed"
                ),
                "b10_t2_credit_allowed": triage_summary.get("b10_t2_credit_allowed"),
                "b10_bqp_separation_credit_allowed": triage_summary.get(
                    "b10_bqp_separation_credit_allowed"
                ),
            },
        ),
    ]
    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected H1 replay packet failures: {failed_ids}")
    if submitted_exists:
        validation_errors.append("gate expected no submitted H1 replay artifact until a hardware PR supplies one")

    summary = {
        "h1_packet_id": EXPECTED_PACKET_ID,
        "h1_packet_hash": h1_packet["packet_hash"],
        "source_triage_hash": triage_summary.get("triage_hash"),
        "source_provider_packet_hash": provider_summary.get("packet_hash"),
        "source_provider_packet_id": EXPECTED_PROVIDER_PACKET_ID,
        "downstream_transcript_packet_id": EXPECTED_TRANSCRIPT_PACKET_ID,
        "requirement_count": len(requirements),
        "requirements_passed": passed,
        "requirements_failed": len(requirements) - passed,
        "failed_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "production_required_key_count": len(production_required_keys),
        "required_evidence_file_count": len(required_evidence_files),
        "holdout_row_count": triage_summary.get("holdout_row_count"),
        "no_leak_allowed_accepts_per_160": triage_summary.get(
            "no_leak_allowed_accepts_per_160"
        ),
        "full_leak_allowed_accepts_per_160": triage_summary.get(
            "full_leak_allowed_accepts_per_160"
        ),
        "real_backend_transcript_rows": triage_summary.get("real_backend_transcript_rows"),
        "accepted_priority_transcript_rows": triage_summary.get(
            "accepted_priority_transcript_rows"
        ),
        "submitted_h1_artifact_exists": submitted_exists,
        "missing_key_count": len(missing_keys),
        "production_keys_present_count": len(production_present),
        "h1_provider_session_replay_accepted": False,
        "b8_protocol_soundness_credit_allowed": False,
        "b4_verifiable_advantage_credit_allowed": False,
        "b10_t2_credit_allowed": False,
        "b10_bqp_separation_credit_allowed": False,
        "protocol_soundness_proved": False,
        "cryptographic_soundness_proved": False,
        "sampling_hardness_proved": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "validation_error_count": len(validation_errors),
    }

    return {
        "benchmark_id": "B4",
        "linked_benchmark_ids": ["B8", "B10"],
        "source_target_id": "T-B4-002q/T-B8-003u/T-B10-009i",
        "title": "B4/B8 H1 Provider Session Replay Packet Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_post_boundary_triage": str(args.post_boundary_triage),
        "source_provider_manifest_gate": str(args.provider_manifest_gate),
        "summary": summary,
        "h1_replay_packet": h1_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": "H1 now has a locked provider/session/device-property replay packet schema and acceptance boundary.",
            "what_is_not_supported": "No H1 replay artifact, real-backend transcript row, accepted transcript row, soundness credit, advantage credit, or BQP boundary claim is supported.",
            "next_gate": "Submit the H1 replay artifact with source-backed provider access, session hash, backend/device snapshots, runnable circuit manifest, shot budget, private-predicate handling, redaction policy, and claim boundary.",
            "protocol_soundness_proved": False,
            "cryptographic_soundness_proved": False,
            "sampling_hardness_proved": False,
            "quantum_advantage_claimed": False,
            "bqp_separation_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    p = payload["h1_replay_packet"]
    lines = [
        f"# {payload['title']}",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- H1 packet: `{s['h1_packet_id']}`",
        f"- H1 packet hash: `{s['h1_packet_hash']}`",
        f"- Source triage hash: `{s['source_triage_hash']}`",
        f"- Source provider packet hash: `{s['source_provider_packet_hash']}`",
        "",
        "## Result",
        "",
        (
            f"The H1 gate passes {s['requirements_passed']}/{s['requirement_count']} "
            f"requirements and intentionally fails {s['failed_requirement_ids']} because no "
            "source-backed provider/session/device-property replay artifact has been submitted."
        ),
        "",
        "## Locked H1 Packet",
        "",
        f"- Submission path: `{p['submission_artifact_path']}`",
        f"- Required keys: `{s['required_key_count']}`",
        f"- Production required keys: `{s['production_required_key_count']}`",
        f"- Evidence file classes: `{s['required_evidence_file_count']}`",
        "",
        "Required evidence files:",
        "",
    ]
    for item in p["required_evidence_files"]:
        lines.append(f"- {item}")
    lines.extend(["", "Acceptance predicates:", ""])
    for item in p["accepted_only_if"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            f"- Downstream transcript packet: `{s['downstream_transcript_packet_id']}`",
            f"- Holdout rows: `{s['holdout_row_count']}`",
            f"- No-leak / full-leak budgets per 160: `{s['no_leak_allowed_accepts_per_160']}` / `{s['full_leak_allowed_accepts_per_160']}`",
            f"- Real backend transcript rows: `{s['real_backend_transcript_rows']}`",
            f"- Accepted transcript rows: `{s['accepted_priority_transcript_rows']}`",
            f"- H1 accepted: `{s['h1_provider_session_replay_accepted']}`",
            f"- B8 soundness / B4 advantage / B10-T2 credit: `{s['b8_protocol_soundness_credit_allowed']}` / `{s['b4_verifiable_advantage_credit_allowed']}` / `{s['b10_t2_credit_allowed']}`",
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
            "This packet gate does not claim hardware execution, protocol soundness, cryptographic soundness, sampling hardness, quantum advantage, B4 advantage, B10-T2 credit, or BQP separation.",
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
        "--post-boundary-triage",
        type=Path,
        default=Path("results/B4_B8_real_backend_transcript_post_boundary_submission_triage_v0.json"),
    )
    parser.add_argument(
        "--provider-manifest-gate",
        type=Path,
        default=Path("results/B4_B8_real_backend_provider_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--submission-dir",
        type=Path,
        default=Path("results/B4_B8_H1_provider_session_replay_submissions"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B4_B8_H1_provider_session_replay_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B4_B8_H1_provider_session_replay_packet_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-03")
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
                "h1_packet_hash": payload["summary"]["h1_packet_hash"],
                "requirements_passed": payload["summary"]["requirements_passed"],
                "requirements_failed": payload["summary"]["requirements_failed"],
                "failed_requirement_ids": payload["summary"]["failed_requirement_ids"],
                "validation_error_count": payload["summary"]["validation_error_count"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if payload["validation_errors"]:
        raise SystemExit("B4/B8 H1 provider/session replay packet gate validation failed")


if __name__ == "__main__":
    main()
