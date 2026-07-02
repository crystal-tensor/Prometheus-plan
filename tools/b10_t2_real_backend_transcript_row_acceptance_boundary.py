#!/usr/bin/env python3
"""T-B10-009g: B10-T2 view of the B4/B8 real-backend transcript row acceptance gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b10_t2_real_backend_transcript_row_acceptance_boundary_v0"
STATUS = "b10_t2_real_backend_transcript_row_acceptance_boundary_synced"
MODEL_STATUS = "b10_t2_zero_credit_boundary_after_b4_b8_row_acceptance_packet_gate"
VERSION = "0.1"
EXPECTED_METHOD = "b4_b8_real_backend_transcript_row_acceptance_packet_gate_v0"
EXPECTED_ACCEPTANCE_PACKET_ID = "B4B8-M6-real-backend-transcript-row-acceptance-packet"


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
        "boundary_id": "B10-T2-real-backend-transcript-row-acceptance-boundary",
        "source_acceptance_packet_gate": str(args.acceptance_packet_gate),
        "source_method": source.get("method"),
        "acceptance_packet_id": summary.get("acceptance_packet_id"),
        "acceptance_packet_hash": summary.get("acceptance_packet_hash"),
        "transcript_packet_id": summary.get("transcript_packet_id"),
        "holdout_row_count": summary.get("holdout_row_count"),
        "no_leak_allowed_accepts_per_160": summary.get("no_leak_allowed_accepts_per_160"),
        "full_leak_allowed_accepts_per_160": summary.get("full_leak_allowed_accepts_per_160"),
        "accepted_priority_transcript_rows": summary.get("accepted_priority_transcript_rows"),
        "real_backend_transcript_rows": summary.get("real_backend_transcript_rows"),
        "b10_soundness_credit_allowed": summary.get("b10_soundness_credit_allowed"),
        "b10_bqp_separation_credit_allowed": summary.get("b10_bqp_separation_credit_allowed"),
        "quantum_advantage_claimed": summary.get("quantum_advantage_claimed"),
        "bqp_separation_claimed": summary.get("bqp_separation_claimed"),
        "required_downstream_before_credit": [
            "accepted B4B8-M6-provider-session-manifest",
            "accepted B4B8-M6-real-backend-transcript-provenance-manifest",
            "accepted B4B8-M6-real-backend-transcript-replay-validation-manifest",
            "accepted B4B8-M6-real-backend-transcript-row-acceptance-packet",
            "nonzero real backend transcript rows",
            "leakage-blind no-leak retest <=16/160",
            "full-leak retest <=40/160 or explicit exclusion",
            "spoofer attack replay table",
            "B10 zero-credit boundary note replaced by an accepted credit boundary",
        ],
    }
    boundary_packet["boundary_hash"] = stable_hash(boundary_packet)

    requirements = [
        requirement(
            "S1",
            "Source B4/B8 row acceptance packet gate is present and current",
            source.get("method") == EXPECTED_METHOD
            and summary.get("acceptance_packet_id") == EXPECTED_ACCEPTANCE_PACKET_ID
            and summary.get("validation_error_count") == 0,
            {
                "source_method": source.get("method"),
                "acceptance_packet_id": summary.get("acceptance_packet_id"),
                "validation_error_count": summary.get("validation_error_count"),
            },
        ),
        requirement(
            "S2",
            "Source gate remains blocked on the missing submitted packet only",
            summary.get("failed_acceptance_requirement_ids") == ["P6", "P7", "P8"]
            and summary.get("submitted_acceptance_packet_exists") is False,
            {
                "failed_acceptance_requirement_ids": summary.get("failed_acceptance_requirement_ids"),
                "submitted_acceptance_packet_exists": summary.get("submitted_acceptance_packet_exists"),
            },
        ),
        requirement(
            "S3",
            "B10-T2 margin budgets are preserved",
            summary.get("holdout_row_count") == 160
            and summary.get("no_leak_allowed_accepts_per_160") == 16
            and summary.get("full_leak_allowed_accepts_per_160") == 40,
            {
                "holdout_row_count": summary.get("holdout_row_count"),
                "no_leak_allowed_accepts_per_160": summary.get("no_leak_allowed_accepts_per_160"),
                "full_leak_allowed_accepts_per_160": summary.get("full_leak_allowed_accepts_per_160"),
            },
        ),
        requirement(
            "S4",
            "No real backend transcript rows or accepted transcript rows are present",
            summary.get("real_backend_transcript_rows") == 0
            and summary.get("accepted_priority_transcript_rows") == 0,
            {
                "real_backend_transcript_rows": summary.get("real_backend_transcript_rows"),
                "accepted_priority_transcript_rows": summary.get("accepted_priority_transcript_rows"),
            },
        ),
        requirement(
            "S5",
            "B10 soundness and BQP separation credit remain explicitly disabled",
            summary.get("b10_soundness_credit_allowed") is False
            and summary.get("b10_bqp_separation_credit_allowed") is False,
            {
                "b10_soundness_credit_allowed": summary.get("b10_soundness_credit_allowed"),
                "b10_bqp_separation_credit_allowed": summary.get("b10_bqp_separation_credit_allowed"),
            },
        ),
        requirement(
            "S6",
            "Forbidden soundness, hardness, advantage, and BQP claims remain false",
            summary.get("protocol_soundness_proved") is False
            and summary.get("cryptographic_soundness_proved") is False
            and summary.get("sampling_hardness_proved") is False
            and summary.get("quantum_advantage_claimed") is False
            and summary.get("bqp_separation_claimed") is False,
            {
                "protocol_soundness_proved": summary.get("protocol_soundness_proved"),
                "cryptographic_soundness_proved": summary.get("cryptographic_soundness_proved"),
                "sampling_hardness_proved": summary.get("sampling_hardness_proved"),
                "quantum_advantage_claimed": summary.get("quantum_advantage_claimed"),
                "bqp_separation_claimed": summary.get("bqp_separation_claimed"),
            },
        ),
        requirement(
            "S7",
            "B10 boundary packet records the required downstream evidence before credit",
            len(boundary_packet["required_downstream_before_credit"]) == 9,
            {"required_downstream_before_credit": boundary_packet["required_downstream_before_credit"]},
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors = []
    if failed_ids:
        validation_errors.append(f"B10-T2 transcript row acceptance boundary failed: {failed_ids}")

    payload_summary = {
        "boundary_id": boundary_packet["boundary_id"],
        "boundary_hash": boundary_packet["boundary_hash"],
        "source_acceptance_packet_hash": summary.get("acceptance_packet_hash"),
        "acceptance_packet_id": summary.get("acceptance_packet_id"),
        "transcript_packet_id": summary.get("transcript_packet_id"),
        "requirement_count": len(requirements),
        "requirements_passed": passed,
        "requirements_failed": len(requirements) - passed,
        "failed_requirement_ids": failed_ids,
        "holdout_row_count": summary.get("holdout_row_count"),
        "no_leak_allowed_accepts_per_160": summary.get("no_leak_allowed_accepts_per_160"),
        "full_leak_allowed_accepts_per_160": summary.get("full_leak_allowed_accepts_per_160"),
        "submitted_acceptance_packet_exists": summary.get("submitted_acceptance_packet_exists"),
        "real_backend_transcript_rows": summary.get("real_backend_transcript_rows"),
        "accepted_priority_transcript_rows": summary.get("accepted_priority_transcript_rows"),
        "b10_soundness_credit_allowed": False,
        "b10_bqp_separation_credit_allowed": False,
        "protocol_soundness_proved": False,
        "cryptographic_soundness_proved": False,
        "sampling_hardness_proved": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "validation_error_count": len(validation_errors),
    }
    return {
        "benchmark_id": "B10",
        "linked_benchmark_id": "B4_B8",
        "source_target_id": "B10-T2",
        "title": "B10-T2 Real-Backend Transcript Row Acceptance Boundary",
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
                "B10-T2 is now explicitly synchronized to the B4/B8 real-backend "
                "transcript row acceptance packet gate as the current zero-credit boundary."
            ),
            "what_is_not_supported": (
                "No real backend transcript row, protocol soundness result, quantum "
                "advantage, or BQP separation is supported."
            ),
            "next_gate": (
                "Submit the provider/session manifest, transcript provenance manifest, "
                "transcript replay-validation manifest, row acceptance packet, and real "
                "backend transcript rows before B10-T2 can leave zero-credit status."
            ),
            "b10_soundness_credit_allowed": False,
            "b10_bqp_separation_credit_allowed": False,
            "quantum_advantage_claimed": False,
            "bqp_separation_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    packet = payload["boundary_packet"]
    lines = [
        "# B10-T2 Real-Backend Transcript Row Acceptance Boundary",
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
        f"- Requirements passed/failed: `{summary['requirements_passed']}` / `{summary['requirements_failed']}`",
        f"- Failed requirement IDs: `{summary['failed_requirement_ids']}`",
        f"- Holdout rows: `{summary['holdout_row_count']}`",
        f"- Leakage-blind / full-leak budgets per 160: `{summary['no_leak_allowed_accepts_per_160']}` / `{summary['full_leak_allowed_accepts_per_160']}`",
        f"- Submitted acceptance packet exists: `{summary['submitted_acceptance_packet_exists']}`",
        f"- Real backend / accepted transcript rows: `{summary['real_backend_transcript_rows']}` / `{summary['accepted_priority_transcript_rows']}`",
        f"- B10 soundness / BQP credit allowed: `{summary['b10_soundness_credit_allowed']}` / `{summary['b10_bqp_separation_credit_allowed']}`",
        f"- validation_error_count: `{summary['validation_error_count']}`",
        "",
        "## Required Downstream Evidence Before Credit",
        "",
    ]
    for item in packet["required_downstream_before_credit"]:
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
            f"- b10_soundness_credit_allowed: {payload['claim_boundary']['b10_soundness_credit_allowed']}",
            f"- b10_bqp_separation_credit_allowed: {payload['claim_boundary']['b10_bqp_separation_credit_allowed']}",
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
        "--acceptance-packet-gate",
        type=Path,
        default=Path("results/B4_B8_real_backend_transcript_row_acceptance_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B10_T2_real_backend_transcript_row_acceptance_boundary_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B10_T2_real_backend_transcript_row_acceptance_boundary.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-03")
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
