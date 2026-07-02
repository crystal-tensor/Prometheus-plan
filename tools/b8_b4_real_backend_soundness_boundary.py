#!/usr/bin/env python3
"""T-B8-003s/T-B4-002o: B8 view of the B4/B8 real-backend transcript row gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b8_b4_real_backend_soundness_boundary_v0"
STATUS = "b8_b4_real_backend_soundness_boundary_synced"
MODEL_STATUS = "b8_zero_credit_soundness_boundary_after_real_backend_transcript_row_gate"
VERSION = "0.1"
EXPECTED_METHOD = "b4_b8_real_backend_transcript_row_acceptance_packet_gate_v0"
EXPECTED_ACCEPTANCE_PACKET_ID = "B4B8-M6-real-backend-transcript-row-acceptance-packet"
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
    source = load_json(args.acceptance_packet_gate)
    summary = source["summary"]

    boundary_packet = {
        "boundary_id": "B8-B4-real-backend-soundness-boundary",
        "source_acceptance_packet_gate": str(args.acceptance_packet_gate),
        "source_method": source.get("method"),
        "acceptance_packet_id": summary.get("acceptance_packet_id"),
        "acceptance_packet_hash": summary.get("acceptance_packet_hash"),
        "transcript_packet_id": summary.get("transcript_packet_id"),
        "replay_validation_manifest_id": summary.get("replay_validation_manifest_id"),
        "replay_validation_manifest_hash": summary.get("replay_validation_manifest_hash"),
        "holdout_row_count": summary.get("holdout_row_count"),
        "no_leak_allowed_accepts_per_160": summary.get("no_leak_allowed_accepts_per_160"),
        "full_leak_allowed_accepts_per_160": summary.get("full_leak_allowed_accepts_per_160"),
        "real_backend_transcript_rows": summary.get("real_backend_transcript_rows"),
        "accepted_priority_transcript_rows": summary.get("accepted_priority_transcript_rows"),
        "b8_protocol_soundness_credit_allowed": False,
        "b8_cryptographic_soundness_credit_allowed": False,
        "b8_sampling_hardness_credit_allowed": False,
        "b4_verifiable_advantage_credit_allowed": False,
        "b10_t2_credit_allowed": False,
        "required_downstream_before_b8_soundness_credit": [
            "submitted B4B8-M6-real-backend-transcript-row-acceptance-packet",
            "source-backed backend properties, circuit, job, counts, and postprocess replay",
            "accepted real-backend transcript rows over the locked 160-row holdout",
            "leakage-blind no-leak margin retest with accepts <= 16/160",
            "full-leak containment or explicit exclusion with accepts <= 40/160 when included",
            "spoofer replay against leakage-separated fitted or generative attackers",
            "B10 zero-credit boundary upgraded only after transcript rows are accepted",
            "claim boundary forbidding protocol soundness, cryptographic soundness, sampling hardness, quantum advantage, and BQP separation before acceptance",
        ],
    }
    boundary_packet["boundary_hash"] = stable_hash(boundary_packet)

    no_forbidden_claims = all(
        summary.get(key) is False
        for key in [
            "protocol_soundness_proved",
            "cryptographic_soundness_proved",
            "sampling_hardness_proved",
            "quantum_advantage_claimed",
            "bqp_separation_claimed",
            "b10_soundness_credit_allowed",
            "b10_bqp_separation_credit_allowed",
        ]
    )

    requirements = [
        requirement(
            "S1",
            "Source B4/B8 real-backend transcript row acceptance gate is present and current",
            source.get("method") == EXPECTED_METHOD
            and summary.get("acceptance_packet_id") == EXPECTED_ACCEPTANCE_PACKET_ID
            and summary.get("transcript_packet_id") == EXPECTED_TRANSCRIPT_PACKET_ID
            and summary.get("validation_error_count") == 0,
            {
                "source_method": source.get("method"),
                "acceptance_packet_id": summary.get("acceptance_packet_id"),
                "transcript_packet_id": summary.get("transcript_packet_id"),
                "validation_error_count": summary.get("validation_error_count"),
            },
        ),
        requirement(
            "S2",
            "Source acceptance gate remains blocked on missing submitted packet evidence",
            summary.get("failed_acceptance_requirement_ids") == EXPECTED_FAILED_IDS
            and summary.get("submitted_acceptance_packet_exists") is False,
            {
                "failed_acceptance_requirement_ids": summary.get(
                    "failed_acceptance_requirement_ids"
                ),
                "submitted_acceptance_packet_exists": summary.get(
                    "submitted_acceptance_packet_exists"
                ),
            },
        ),
        requirement(
            "S3",
            "B8 real-backend verifier denominator scope is preserved",
            summary.get("holdout_row_count") == 160
            and summary.get("no_leak_allowed_accepts_per_160") == 16
            and summary.get("full_leak_allowed_accepts_per_160") == 40,
            {
                "holdout_row_count": summary.get("holdout_row_count"),
                "no_leak_allowed_accepts_per_160": summary.get(
                    "no_leak_allowed_accepts_per_160"
                ),
                "full_leak_allowed_accepts_per_160": summary.get(
                    "full_leak_allowed_accepts_per_160"
                ),
            },
        ),
        requirement(
            "S4",
            "No real-backend transcript row has been accepted",
            summary.get("real_backend_transcript_rows") == 0
            and summary.get("accepted_priority_transcript_rows") == 0,
            {
                "real_backend_transcript_rows": summary.get("real_backend_transcript_rows"),
                "accepted_priority_transcript_rows": summary.get(
                    "accepted_priority_transcript_rows"
                ),
            },
        ),
        requirement(
            "S5",
            "B8/B4/B10 soundness, hardness, advantage, and BQP credits remain disabled",
            boundary_packet["b8_protocol_soundness_credit_allowed"] is False
            and boundary_packet["b8_cryptographic_soundness_credit_allowed"] is False
            and boundary_packet["b8_sampling_hardness_credit_allowed"] is False
            and boundary_packet["b4_verifiable_advantage_credit_allowed"] is False
            and boundary_packet["b10_t2_credit_allowed"] is False,
            {
                "b8_protocol_soundness_credit_allowed": boundary_packet[
                    "b8_protocol_soundness_credit_allowed"
                ],
                "b8_cryptographic_soundness_credit_allowed": boundary_packet[
                    "b8_cryptographic_soundness_credit_allowed"
                ],
                "b8_sampling_hardness_credit_allowed": boundary_packet[
                    "b8_sampling_hardness_credit_allowed"
                ],
                "b4_verifiable_advantage_credit_allowed": boundary_packet[
                    "b4_verifiable_advantage_credit_allowed"
                ],
                "b10_t2_credit_allowed": boundary_packet["b10_t2_credit_allowed"],
            },
        ),
        requirement(
            "S6",
            "Forbidden protocol, hardness, advantage, and BQP claims remain absent",
            no_forbidden_claims,
            {
                "protocol_soundness_proved": summary.get("protocol_soundness_proved"),
                "cryptographic_soundness_proved": summary.get(
                    "cryptographic_soundness_proved"
                ),
                "sampling_hardness_proved": summary.get("sampling_hardness_proved"),
                "quantum_advantage_claimed": summary.get("quantum_advantage_claimed"),
                "bqp_separation_claimed": summary.get("bqp_separation_claimed"),
                "b10_soundness_credit_allowed": summary.get("b10_soundness_credit_allowed"),
                "b10_bqp_separation_credit_allowed": summary.get(
                    "b10_bqp_separation_credit_allowed"
                ),
            },
        ),
        requirement(
            "S7",
            "Boundary records downstream evidence required before B8 soundness credit",
            len(boundary_packet["required_downstream_before_b8_soundness_credit"]) == 8,
            {
                "required_downstream_before_b8_soundness_credit": boundary_packet[
                    "required_downstream_before_b8_soundness_credit"
                ]
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors = []
    if failed_ids:
        validation_errors.append(f"B8/B4 real-backend soundness boundary failed: {failed_ids}")

    payload_summary = {
        "boundary_id": boundary_packet["boundary_id"],
        "boundary_hash": boundary_packet["boundary_hash"],
        "source_acceptance_packet_hash": summary.get("acceptance_packet_hash"),
        "acceptance_packet_id": summary.get("acceptance_packet_id"),
        "transcript_packet_id": summary.get("transcript_packet_id"),
        "replay_validation_manifest_id": summary.get("replay_validation_manifest_id"),
        "requirement_count": len(requirements),
        "requirements_passed": passed,
        "requirements_failed": len(requirements) - passed,
        "failed_requirement_ids": failed_ids,
        "source_failed_acceptance_requirement_ids": summary.get(
            "failed_acceptance_requirement_ids"
        ),
        "submitted_acceptance_packet_exists": summary.get("submitted_acceptance_packet_exists"),
        "holdout_row_count": summary.get("holdout_row_count"),
        "no_leak_allowed_accepts_per_160": summary.get("no_leak_allowed_accepts_per_160"),
        "full_leak_allowed_accepts_per_160": summary.get("full_leak_allowed_accepts_per_160"),
        "real_backend_transcript_rows": summary.get("real_backend_transcript_rows"),
        "accepted_priority_transcript_rows": summary.get("accepted_priority_transcript_rows"),
        "b8_protocol_soundness_credit_allowed": False,
        "b8_cryptographic_soundness_credit_allowed": False,
        "b8_sampling_hardness_credit_allowed": False,
        "b4_verifiable_advantage_credit_allowed": False,
        "b10_t2_credit_allowed": False,
        "protocol_soundness_proved": False,
        "cryptographic_soundness_proved": False,
        "sampling_hardness_proved": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "validation_error_count": len(validation_errors),
    }
    return {
        "benchmark_id": "B8",
        "linked_benchmark_id": "B4",
        "source_target_id": "T-B8-003s/T-B4-002o",
        "title": "B8/B4 Real-Backend Soundness Boundary",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_acceptance_packet_gate": str(args.acceptance_packet_gate),
        "summary": payload_summary,
        "boundary_packet": boundary_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "B8 is synchronized to the B4/B8 real-backend transcript row acceptance "
                "packet as a zero-credit protocol-soundness boundary."
            ),
            "what_is_not_supported": (
                "No real-backend transcript row, protocol soundness, cryptographic soundness, "
                "sampling hardness, quantum advantage, BQP separation, or B10-T2 credit is supported."
            ),
            "next_gate": (
                "Submit and accept the real-backend transcript row acceptance packet with "
                "source-backed backend properties, counts, postprocess replay, no-leak and "
                "full-leak margin retests, spoofer replay, B10 boundary, and claim boundary."
            ),
            "b8_protocol_soundness_credit_allowed": False,
            "b8_sampling_hardness_credit_allowed": False,
            "b10_t2_credit_allowed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    packet = payload["boundary_packet"]
    lines = [
        "# B8/B4 Real-Backend Soundness Boundary",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Boundary: `{summary['boundary_id']}`",
        f"- Boundary hash: `{summary['boundary_hash']}`",
        f"- Source acceptance packet: `{summary['acceptance_packet_id']}`",
        f"- Source acceptance packet hash: `{summary['source_acceptance_packet_hash']}`",
        f"- Transcript packet: `{summary['transcript_packet_id']}`",
        f"- Replay-validation manifest: `{summary['replay_validation_manifest_id']}`",
        f"- Requirements passed/failed: `{summary['requirements_passed']}` / `{summary['requirements_failed']}`",
        f"- Failed requirement IDs: `{summary['failed_requirement_ids']}`",
        f"- Source failed acceptance IDs: `{summary['source_failed_acceptance_requirement_ids']}`",
        f"- Holdout rows / no-leak budget / full-leak budget: `{summary['holdout_row_count']}` / `{summary['no_leak_allowed_accepts_per_160']}` / `{summary['full_leak_allowed_accepts_per_160']}`",
        f"- Real-backend rows / accepted transcript rows: `{summary['real_backend_transcript_rows']}` / `{summary['accepted_priority_transcript_rows']}`",
        f"- B8 protocol / sampling / B10-T2 credit allowed: `{summary['b8_protocol_soundness_credit_allowed']}` / `{summary['b8_sampling_hardness_credit_allowed']}` / `{summary['b10_t2_credit_allowed']}`",
        f"- validation_error_count: `{summary['validation_error_count']}`",
        "",
        "## Required Downstream Evidence Before B8 Soundness Credit",
        "",
    ]
    for item in packet["required_downstream_before_b8_soundness_credit"]:
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
            f"- b8_protocol_soundness_credit_allowed: {payload['claim_boundary']['b8_protocol_soundness_credit_allowed']}",
            f"- b8_sampling_hardness_credit_allowed: {payload['claim_boundary']['b8_sampling_hardness_credit_allowed']}",
            f"- b10_t2_credit_allowed: {payload['claim_boundary']['b10_t2_credit_allowed']}",
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
        "--acceptance-packet-gate",
        type=Path,
        default=Path("results/B4_B8_real_backend_transcript_row_acceptance_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B8_B4_real_backend_soundness_boundary_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B8_B4_real_backend_soundness_boundary.md"),
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
