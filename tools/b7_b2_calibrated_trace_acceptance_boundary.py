#!/usr/bin/env python3
"""T-B7-012h/T-B2-010h: B7 view of the B2 calibrated trace acceptance packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b7_b2_calibrated_trace_acceptance_boundary_v0"
STATUS = "b7_b2_calibrated_trace_acceptance_boundary_synced"
MODEL_STATUS = "b7_zero_credit_boundary_after_b2_calibrated_trace_acceptance_packet_gate"
VERSION = "0.1"
EXPECTED_METHOD = "b2_calibrated_trace_row_acceptance_packet_gate_v0"
EXPECTED_ACCEPTANCE_PACKET_ID = "B2-T5-calibrated-trace-row-acceptance-packet"
EXPECTED_TRACE_PACKET_ID = "B2-T5-calibrated-flag-observation-rows"
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
        "boundary_id": "B7-B2-calibrated-trace-acceptance-boundary",
        "source_acceptance_packet_gate": str(args.acceptance_packet_gate),
        "source_method": source.get("method"),
        "acceptance_packet_id": summary.get("acceptance_packet_id"),
        "acceptance_packet_hash": summary.get("acceptance_packet_hash"),
        "trace_packet_id": summary.get("trace_packet_id"),
        "replay_validation_manifest_id": summary.get("replay_validation_manifest_id"),
        "challenge_count": summary.get("challenge_count"),
        "source_trace_count": summary.get("source_trace_count"),
        "holdout_profile_shots": summary.get("holdout_profile_shots"),
        "accepted_priority_trace_rows": summary.get("accepted_priority_trace_rows"),
        "source_b7_dependency_credit_allowed": summary.get("b7_dependency_credit_allowed"),
        "source_b7_credit_delta": summary.get("b7_credit_delta"),
        "b7_dependency_credit_allowed": False,
        "b7_ft_ledger_credit_allowed": False,
        "b7_resource_credit_allowed": False,
        "b7_space_time_volume_reduction_credit": 0,
        "b7_logical_error_improvement_credit": 0,
        "required_downstream_before_b7_credit": [
            "submitted B2-T5-calibrated-trace-row-acceptance-packet",
            "source-backed row batch, detector trace, decoder profile, posterior, prediction, and holdout artifacts",
            "positive accepted_trace_row_count",
            "all-challenge non-regression proof",
            "real or independently calibrated trace replay",
            "strict holdout improvement under the same decoder path",
            "B7 zero-credit boundary note updated to a nonzero-credit acceptance ledger",
            "claim boundary that still forbids decoder, threshold, hardware-result, calibrated-device, quantum-advantage, and unpriced FT-resource claims",
        ],
    }
    boundary_packet["boundary_hash"] = stable_hash(boundary_packet)

    no_forbidden_claims = all(
        summary.get(key) is False
        for key in [
            "production_decoder_claimed",
            "threshold_claimed",
            "new_code_claimed",
            "hardware_result_claimed",
            "calibrated_device_claimed",
            "quantum_advantage_claimed",
        ]
    )

    requirements = [
        requirement(
            "S1",
            "Source B2 calibrated trace acceptance packet gate is present and current",
            source.get("method") == EXPECTED_METHOD
            and summary.get("acceptance_packet_id") == EXPECTED_ACCEPTANCE_PACKET_ID
            and summary.get("trace_packet_id") == EXPECTED_TRACE_PACKET_ID
            and summary.get("validation_error_count") == 0,
            {
                "source_method": source.get("method"),
                "acceptance_packet_id": summary.get("acceptance_packet_id"),
                "trace_packet_id": summary.get("trace_packet_id"),
                "validation_error_count": summary.get("validation_error_count"),
            },
        ),
        requirement(
            "S2",
            "Source acceptance gate remains blocked on missing submitted packet evidence",
            summary.get("failed_acceptance_requirement_ids") == EXPECTED_FAILED_IDS
            and summary.get("submitted_acceptance_packet_exists") is False,
            {
                "failed_acceptance_requirement_ids": summary.get("failed_acceptance_requirement_ids"),
                "submitted_acceptance_packet_exists": summary.get("submitted_acceptance_packet_exists"),
            },
        ),
        requirement(
            "S3",
            "B2 calibrated trace scope is preserved for the B7 dependency view",
            summary.get("challenge_count") == 3
            and summary.get("source_trace_count") == 576
            and summary.get("holdout_profile_shots") == 864,
            {
                "challenge_count": summary.get("challenge_count"),
                "source_trace_count": summary.get("source_trace_count"),
                "holdout_profile_shots": summary.get("holdout_profile_shots"),
            },
        ),
        requirement(
            "S4",
            "No calibrated rows have been accepted for B7 dependency credit",
            summary.get("accepted_priority_trace_rows") == 0
            and summary.get("b7_dependency_credit_allowed") is False
            and summary.get("b7_credit_delta") == 0,
            {
                "accepted_priority_trace_rows": summary.get("accepted_priority_trace_rows"),
                "source_b7_dependency_credit_allowed": summary.get("b7_dependency_credit_allowed"),
                "source_b7_credit_delta": summary.get("b7_credit_delta"),
            },
        ),
        requirement(
            "S5",
            "B7 FT ledger and resource credit remain explicitly disabled",
            boundary_packet["b7_dependency_credit_allowed"] is False
            and boundary_packet["b7_ft_ledger_credit_allowed"] is False
            and boundary_packet["b7_resource_credit_allowed"] is False
            and boundary_packet["b7_space_time_volume_reduction_credit"] == 0
            and boundary_packet["b7_logical_error_improvement_credit"] == 0,
            {
                "b7_dependency_credit_allowed": boundary_packet["b7_dependency_credit_allowed"],
                "b7_ft_ledger_credit_allowed": boundary_packet["b7_ft_ledger_credit_allowed"],
                "b7_resource_credit_allowed": boundary_packet["b7_resource_credit_allowed"],
                "b7_space_time_volume_reduction_credit": boundary_packet[
                    "b7_space_time_volume_reduction_credit"
                ],
                "b7_logical_error_improvement_credit": boundary_packet[
                    "b7_logical_error_improvement_credit"
                ],
            },
        ),
        requirement(
            "S6",
            "Forbidden decoder, threshold, hardware, advantage, and FT-resource claims remain absent",
            no_forbidden_claims,
            {
                "production_decoder_claimed": summary.get("production_decoder_claimed"),
                "threshold_claimed": summary.get("threshold_claimed"),
                "new_code_claimed": summary.get("new_code_claimed"),
                "hardware_result_claimed": summary.get("hardware_result_claimed"),
                "calibrated_device_claimed": summary.get("calibrated_device_claimed"),
                "quantum_advantage_claimed": summary.get("quantum_advantage_claimed"),
                "b7_resource_credit_allowed": boundary_packet["b7_resource_credit_allowed"],
            },
        ),
        requirement(
            "S7",
            "Boundary records the downstream evidence required before B7 can count credit",
            len(boundary_packet["required_downstream_before_b7_credit"]) == 8,
            {"required_downstream_before_b7_credit": boundary_packet["required_downstream_before_b7_credit"]},
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors = []
    if failed_ids:
        validation_errors.append(f"B7/B2 calibrated trace acceptance boundary failed: {failed_ids}")

    payload_summary = {
        "boundary_id": boundary_packet["boundary_id"],
        "boundary_hash": boundary_packet["boundary_hash"],
        "source_acceptance_packet_hash": summary.get("acceptance_packet_hash"),
        "acceptance_packet_id": summary.get("acceptance_packet_id"),
        "trace_packet_id": summary.get("trace_packet_id"),
        "replay_validation_manifest_id": summary.get("replay_validation_manifest_id"),
        "challenge_count": summary.get("challenge_count"),
        "source_trace_count": summary.get("source_trace_count"),
        "holdout_profile_shots": summary.get("holdout_profile_shots"),
        "requirement_count": len(requirements),
        "requirements_passed": passed,
        "requirements_failed": len(requirements) - passed,
        "failed_requirement_ids": failed_ids,
        "source_failed_acceptance_requirement_ids": summary.get("failed_acceptance_requirement_ids"),
        "submitted_acceptance_packet_exists": summary.get("submitted_acceptance_packet_exists"),
        "accepted_priority_trace_rows": summary.get("accepted_priority_trace_rows"),
        "b7_dependency_credit_allowed": False,
        "b7_ft_ledger_credit_allowed": False,
        "b7_resource_credit_allowed": False,
        "b7_credit_delta": 0,
        "b7_space_time_volume_reduction_credit": 0,
        "b7_logical_error_improvement_credit": 0,
        "production_decoder_claimed": False,
        "threshold_claimed": False,
        "new_code_claimed": False,
        "hardware_result_claimed": False,
        "calibrated_device_claimed": False,
        "quantum_advantage_claimed": False,
        "validation_error_count": len(validation_errors),
    }
    return {
        "benchmark_id": "B7",
        "linked_benchmark_id": "B2",
        "source_target_id": "T-B7-012h/T-B2-010h",
        "title": "B7/B2 Calibrated Trace Acceptance Boundary",
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
                "B7 is now explicitly synchronized to the B2 calibrated trace row "
                "acceptance packet as a zero-credit dependency boundary."
            ),
            "what_is_not_supported": (
                "No calibrated B2 row, FT ledger improvement, logical error improvement, "
                "space-time-volume reduction, hardware result, threshold result, quantum "
                "advantage, or B7 resource credit is supported."
            ),
            "next_gate": (
                "Submit and accept the B2 calibrated trace row acceptance packet, then "
                "provide source-backed accepted rows, all-challenge non-regression, real "
                "or independently calibrated replay, strict holdout improvement, and a "
                "nonzero B7 credit ledger before B7 can count dependency credit."
            ),
            "b7_dependency_credit_allowed": False,
            "b7_ft_ledger_credit_allowed": False,
            "b7_resource_credit_allowed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    packet = payload["boundary_packet"]
    lines = [
        "# B7/B2 Calibrated Trace Acceptance Boundary",
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
        f"- Trace packet: `{summary['trace_packet_id']}`",
        f"- Replay-validation manifest: `{summary['replay_validation_manifest_id']}`",
        f"- Challenge count / source traces / holdout profile shots: `{summary['challenge_count']}` / `{summary['source_trace_count']}` / `{summary['holdout_profile_shots']}`",
        f"- Requirements passed/failed: `{summary['requirements_passed']}` / `{summary['requirements_failed']}`",
        f"- Failed requirement IDs: `{summary['failed_requirement_ids']}`",
        f"- Source failed acceptance IDs: `{summary['source_failed_acceptance_requirement_ids']}`",
        f"- Submitted acceptance packet exists: `{summary['submitted_acceptance_packet_exists']}`",
        f"- Accepted priority trace rows: `{summary['accepted_priority_trace_rows']}`",
        f"- B7 dependency / FT ledger / resource credit allowed: `{summary['b7_dependency_credit_allowed']}` / `{summary['b7_ft_ledger_credit_allowed']}` / `{summary['b7_resource_credit_allowed']}`",
        f"- B7 credit delta / STV credit / logical-error credit: `{summary['b7_credit_delta']}` / `{summary['b7_space_time_volume_reduction_credit']}` / `{summary['b7_logical_error_improvement_credit']}`",
        f"- validation_error_count: `{summary['validation_error_count']}`",
        "",
        "## Required Downstream Evidence Before B7 Credit",
        "",
    ]
    for item in packet["required_downstream_before_b7_credit"]:
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
            f"- b7_dependency_credit_allowed: {payload['claim_boundary']['b7_dependency_credit_allowed']}",
            f"- b7_ft_ledger_credit_allowed: {payload['claim_boundary']['b7_ft_ledger_credit_allowed']}",
            f"- b7_resource_credit_allowed: {payload['claim_boundary']['b7_resource_credit_allowed']}",
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
        default=Path("results/B2_calibrated_trace_row_acceptance_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B7_B2_calibrated_trace_acceptance_boundary_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B7_B2_calibrated_trace_acceptance_boundary.md"),
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
