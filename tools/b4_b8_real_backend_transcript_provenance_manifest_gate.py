#!/usr/bin/env python3
"""T-B4-002l/T-B8-003p/T-B10-009d: real-backend transcript provenance manifest gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b4_b8_real_backend_transcript_provenance_manifest_gate_v0"
STATUS = "real_backend_transcript_provenance_manifest_open_missing_artifact"
MODEL_STATUS = "transcript_provenance_manifest_required_before_real_backend_rows"
VERSION = "0.1"
EXPECTED_MANIFEST_ID = "B4B8-M6-real-backend-transcript-provenance-manifest"
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
    provider_gate = load_json(args.provider_manifest_gate)
    summary = provider_gate["summary"]
    provider_packet = provider_gate["provider_manifest_packet"]
    submission_path = args.submission_dir / f"{EXPECTED_MANIFEST_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None

    required_keys = [
        "manifest_id",
        "provider_packet_id",
        "transcript_packet_id",
        "provider_manifest_hash",
        "backend_properties_hash",
        "runnable_circuit_manifest_hash",
        "job_metadata_manifest_hash",
        "raw_counts_manifest_hash",
        "postprocess_script_hash",
        "calibration_window_utc",
        "shot_allocation_hash",
        "private_predicate_commitment_hash",
        "hashing_redaction_manifest_hash",
        "claim_boundary",
    ]
    production_required_keys = [
        "provider_manifest_hash",
        "backend_properties_hash",
        "runnable_circuit_manifest_hash",
        "job_metadata_manifest_hash",
        "raw_counts_manifest_hash",
        "postprocess_script_hash",
        "shot_allocation_hash",
        "private_predicate_commitment_hash",
        "hashing_redaction_manifest_hash",
    ]
    evidence_files = [
        "accepted_provider_session_manifest",
        "backend_properties_snapshot",
        "runnable_circuit_manifest",
        "hashed_backend_job_metadata",
        "raw_counts_artifact_manifest",
        "postprocess_script_manifest",
        "private_predicate_commitment_manifest",
        "shot_allocation_or_job_plan",
        "hashing_and_redaction_manifest",
        "claim_boundary_note",
    ]

    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    production_present = [
        key for key in production_required_keys if submitted is not None and submitted.get(key) is not None
    ]
    replay_hashes = submitted.get("replay_hashes") if submitted else None
    replay_bound = (
        isinstance(replay_hashes, dict)
        and replay_hashes.get("provider_packet_id") == EXPECTED_PROVIDER_PACKET_ID
        and replay_hashes.get("transcript_packet_id") == EXPECTED_TRANSCRIPT_PACKET_ID
        and replay_hashes.get("provider_packet_hash") == summary.get("packet_hash")
    )
    source_backed = submitted is not None and submitted.get("source_evidence_files_present") is True
    manifest_bound = (
        submitted is not None
        and submitted.get("manifest_id") == EXPECTED_MANIFEST_ID
        and submitted.get("provider_packet_id") == EXPECTED_PROVIDER_PACKET_ID
        and submitted.get("transcript_packet_id") == EXPECTED_TRANSCRIPT_PACKET_ID
        and submitted.get("provider_manifest_hash") == summary.get("packet_hash")
    )

    manifest_packet = {
        "manifest_id": EXPECTED_MANIFEST_ID,
        "provider_packet_id": EXPECTED_PROVIDER_PACKET_ID,
        "transcript_packet_id": EXPECTED_TRANSCRIPT_PACKET_ID,
        "source_provider_manifest_gate": str(args.provider_manifest_gate),
        "submission_artifact_path": str(submission_path),
        "provider_packet_hash": summary.get("packet_hash"),
        "holdout_row_count": summary.get("holdout_row_count"),
        "no_leak_allowed_accepts_per_160": summary.get("no_leak_allowed_accepts_per_160"),
        "full_leak_allowed_accepts_per_160": summary.get("full_leak_allowed_accepts_per_160"),
        "required_keys": required_keys,
        "production_required_keys": production_required_keys,
        "required_evidence_files": evidence_files,
        "accepted_only_if": [
            "manifest_id equals B4B8-M6-real-backend-transcript-provenance-manifest",
            "provider_packet_id equals B4B8-M6-provider-session-manifest",
            "transcript_packet_id equals B4B8-M6-real-backend-transcript-rows",
            "provider_manifest_hash matches the accepted provider/session manifest packet hash",
            "backend properties, runnable circuit, job metadata, raw counts, postprocess, shot allocation, private predicate commitment, and redaction hashes are present",
            "replay_hashes bind provider_packet_id, transcript_packet_id, and provider_packet_hash",
            "source evidence files are present and hash-bound",
            "claim_boundary forbids protocol soundness, quantum advantage, sampling hardness, cryptographic soundness, and BQP separation claims",
        ],
    }
    manifest_packet["manifest_hash"] = stable_hash(manifest_packet)

    forbidden_claims = [
        "protocol_soundness_proved",
        "cryptographic_soundness_proved",
        "sampling_hardness_proved",
        "quantum_advantage_claimed",
        "bqp_separation_claimed",
    ]
    requirements = [
        requirement(
            "P1",
            "Provider manifest gate remains valid and blocked only on P6/P7/P8",
            provider_gate.get("method") == "b4_b8_real_backend_provider_manifest_gate_v0"
            and summary.get("validation_error_count") == 0
            and summary.get("failed_priority_requirement_ids") == ["P6", "P7", "P8"],
            {
                "source_status": provider_gate.get("status"),
                "failed_priority_requirement_ids": summary.get("failed_priority_requirement_ids"),
                "validation_error_count": summary.get("validation_error_count"),
            },
        ),
        requirement(
            "P2",
            "Transcript provenance manifest is bound to the provider and transcript packets",
            summary.get("priority_packet_id") == EXPECTED_PROVIDER_PACKET_ID
            and summary.get("downstream_transcript_packet_id") == EXPECTED_TRANSCRIPT_PACKET_ID
            and provider_packet.get("blocks_transcript_packet") == EXPECTED_TRANSCRIPT_PACKET_ID,
            {
                "provider_packet_id": summary.get("priority_packet_id"),
                "downstream_transcript_packet_id": summary.get("downstream_transcript_packet_id"),
                "blocks_transcript_packet": provider_packet.get("blocks_transcript_packet"),
            },
        ),
        requirement(
            "P3",
            "Manifest packet carries locked provenance schema and evidence file classes",
            len(required_keys) == 14 and len(production_required_keys) == 9 and len(evidence_files) == 10,
            {
                "required_key_count": len(required_keys),
                "production_required_key_count": len(production_required_keys),
                "required_evidence_file_count": len(evidence_files),
            },
        ),
        requirement(
            "P4",
            "Locked margin budgets and zero transcript rows are preserved",
            summary.get("holdout_row_count") == 160
            and summary.get("no_leak_allowed_accepts_per_160") == 16
            and summary.get("full_leak_allowed_accepts_per_160") == 40
            and summary.get("real_backend_transcript_rows") == 0,
            {
                "holdout_row_count": summary.get("holdout_row_count"),
                "no_leak_allowed_accepts_per_160": summary.get("no_leak_allowed_accepts_per_160"),
                "full_leak_allowed_accepts_per_160": summary.get("full_leak_allowed_accepts_per_160"),
                "real_backend_transcript_rows": summary.get("real_backend_transcript_rows"),
            },
        ),
        requirement(
            "P5",
            "Current state has no accepted provider manifest, transcript row, or soundness credit",
            summary.get("provider_manifest_accepted") is False
            and summary.get("accepted_priority_transcript_rows") == 0
            and all(summary.get(key) is False for key in forbidden_claims),
            {
                "provider_manifest_accepted": summary.get("provider_manifest_accepted"),
                "accepted_priority_transcript_rows": summary.get("accepted_priority_transcript_rows"),
                **{key: summary.get(key) for key in forbidden_claims},
            },
        ),
        requirement(
            "P6",
            "Transcript provenance manifest artifact has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted manifest satisfies the locked transcript provenance schema",
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
            "Submitted manifest is source-backed, packet-bound, and replay-hash-bound",
            source_backed and manifest_bound and replay_bound,
            {
                "source_evidence_files_present": source_backed,
                "manifest_bound": manifest_bound,
                "replay_bound": replay_bound,
            },
        ),
        requirement(
            "P9",
            "Forbidden soundness, advantage, and BQP claims remain false",
            all(summary.get(key) is False for key in forbidden_claims),
            {key: summary.get(key) for key in forbidden_claims},
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected transcript provenance manifest failures: {failed_ids}")
    if submitted_exists:
        validation_errors.append("gate expected no submitted provenance manifest until a hardware PR supplies one")

    payload_summary = {
        "manifest_id": EXPECTED_MANIFEST_ID,
        "provider_packet_id": EXPECTED_PROVIDER_PACKET_ID,
        "transcript_packet_id": EXPECTED_TRANSCRIPT_PACKET_ID,
        "provider_packet_hash": summary.get("packet_hash"),
        "manifest_hash": manifest_packet["manifest_hash"],
        "manifest_requirement_count": len(requirements),
        "manifest_requirements_passed": passed,
        "manifest_requirements_failed": len(requirements) - passed,
        "failed_manifest_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "production_required_key_count": len(production_required_keys),
        "required_evidence_file_count": len(evidence_files),
        "holdout_row_count": summary.get("holdout_row_count"),
        "no_leak_allowed_accepts_per_160": summary.get("no_leak_allowed_accepts_per_160"),
        "full_leak_allowed_accepts_per_160": summary.get("full_leak_allowed_accepts_per_160"),
        "real_backend_transcript_rows": summary.get("real_backend_transcript_rows"),
        "provider_manifest_accepted": False,
        "submitted_manifest_exists": submitted_exists,
        "submitted_key_count": len(submitted) if submitted else 0,
        "missing_key_count": len(missing_keys),
        "production_keys_present_count": len(production_present),
        "accepted_priority_transcript_rows": 0,
        "protocol_soundness_proved": False,
        "cryptographic_soundness_proved": False,
        "sampling_hardness_proved": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "validation_error_count": len(validation_errors),
    }

    return {
        "benchmark": "B4/B8",
        "benchmark_id": "B4_B8",
        "linked_benchmark_id": "B10",
        "source_target_id": "B10-T2",
        "dependency_benchmarks": ["B4", "B8", "B10"],
        "title": "B4/B8 Real-Backend Transcript Provenance Manifest Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_provider_manifest_gate": str(args.provider_manifest_gate),
        "summary": payload_summary,
        "transcript_provenance_manifest_packet": manifest_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "The B4/B8 real-backend transcript route now has a provenance manifest "
                "packet that must bind accepted provider/session evidence, backend "
                "properties, runnable circuit, job metadata, raw counts, postprocess, "
                "shot allocation, private-predicate commitment, and redaction hashes."
            ),
            "what_is_not_supported": (
                "No transcript provenance manifest, provider manifest, or real-backend "
                "transcript row has been submitted or accepted; no protocol soundness, "
                "quantum advantage, sampling hardness, cryptographic soundness, or BQP "
                "separation claim is supported."
            ),
            "next_gate": (
                f"Submit {submission_path}, then the real-backend transcript rows, before "
                "rerunning the B4/B8 real-backend margin gate."
            ),
            "protocol_soundness_proved": False,
            "cryptographic_soundness_proved": False,
            "sampling_hardness_proved": False,
            "quantum_advantage_claimed": False,
            "bqp_separation_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    packet = payload["transcript_provenance_manifest_packet"]
    lines = [
        "# B4/B8 Real-Backend Transcript Provenance Manifest Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Manifest: `{summary['manifest_id']}`",
        f"- Provider packet: `{summary['provider_packet_id']}`",
        f"- Transcript packet: `{summary['transcript_packet_id']}`",
        f"- Manifest hash: `{summary['manifest_hash']}`",
        f"- Requirements passed/failed: `{summary['manifest_requirements_passed']}` / `{summary['manifest_requirements_failed']}`",
        f"- Failed requirement IDs: `{summary['failed_manifest_requirement_ids']}`",
        f"- Required key / production key / evidence file count: `{summary['required_key_count']}` / `{summary['production_required_key_count']}` / `{summary['required_evidence_file_count']}`",
        f"- Holdout row count: `{summary['holdout_row_count']}`",
        f"- No-leak / full-leak accepts per 160: `{summary['no_leak_allowed_accepts_per_160']}` / `{summary['full_leak_allowed_accepts_per_160']}`",
        f"- Real-backend transcript rows: `{summary['real_backend_transcript_rows']}`",
        f"- Provider manifest accepted: `{summary['provider_manifest_accepted']}`",
        f"- Submitted manifest exists: `{summary['submitted_manifest_exists']}`",
        f"- validation_error_count: `{summary['validation_error_count']}`",
        "",
        "## Provenance Manifest Packet",
        "",
        f"- Submission path: `{packet['submission_artifact_path']}`",
        f"- Provider packet hash: `{packet['provider_packet_hash']}`",
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
    for item in payload["requirements"]:
        state = "PASS" if item["passed"] else "FAIL"
        lines.append(f"- {item['requirement_id']} [{state}]: {item['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            f"- protocol_soundness_proved: {payload['claim_boundary']['protocol_soundness_proved']}",
            f"- cryptographic_soundness_proved: {payload['claim_boundary']['cryptographic_soundness_proved']}",
            f"- sampling_hardness_proved: {payload['claim_boundary']['sampling_hardness_proved']}",
            f"- quantum_advantage_claimed: {payload['claim_boundary']['quantum_advantage_claimed']}",
            f"- bqp_separation_claimed: {payload['claim_boundary']['bqp_separation_claimed']}",
            "",
            "## Validation",
            "",
            f"- validation_error_count: {summary['validation_error_count']}",
        ]
    )
    if payload["validation_errors"]:
        lines.extend(f"- {error}" for error in payload["validation_errors"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider-manifest-gate",
        type=Path,
        default=Path("results/B4_B8_real_backend_provider_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--submission-dir",
        type=Path,
        default=Path("results/B4_B8_real_backend_transcript_provenance_manifest_submissions"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B4_B8_real_backend_transcript_provenance_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B4_B8_real_backend_transcript_provenance_manifest_gate.md"),
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
