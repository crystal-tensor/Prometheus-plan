#!/usr/bin/env python3
"""T-B2-010a: scout calibrated-trace evidence without promoting synthetic data."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b2_calibrated_trace_scout_v0"
STATUS = "calibrated_trace_scout_failed_missing_real_calibration"
MODEL_STATUS = "synthetic_trace_and_hardware_like_profiles_mapped_not_calibrated_decoder"
VERSION = "0.1"
EXPECTED_FAILED_IDS = ["S5", "S6", "S7"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2 if pretty else None, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def stable_hash(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def requirement(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def challenge_rows(trace_packet: dict[str, Any], profile_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_challenge: dict[str, list[dict[str, Any]]] = {}
    for row in profile_results:
        by_challenge.setdefault(row["challenge_id"], []).append(row)

    rows: list[dict[str, Any]] = []
    for packet in trace_packet.get("challenge_packets", []):
        challenge = packet["challenge"]
        traces = packet.get("shot_traces", [])
        challenge_id = challenge["challenge_id"]
        profile_rows = by_challenge.get(challenge_id, [])
        synthetic_events = sum(len(trace.get("synthetic_flag_events", [])) for trace in traces)
        logical_failures = sum(1 for trace in traces if trace.get("logical_failure"))
        holdout_failures = sum(
            int(row.get("partitions", {}).get("holdout", {}).get("baseline_failures", 0))
            for row in profile_rows
        )
        holdout_injected_failures = sum(
            int(row.get("partitions", {}).get("holdout", {}).get("injected_failures", 0))
            for row in profile_rows
        )
        model_flag_events = sum(int(row.get("model_flag_events", 0)) for row in profile_rows)
        rows.append(
            {
                "challenge_id": challenge_id,
                "challenge_trace_hash": stable_hash(
                    {
                        "challenge": challenge,
                        "trace_count": len(traces),
                        "first_detector_bitstring": traces[0].get("detector_bitstring") if traces else None,
                        "last_detector_bitstring": traces[-1].get("detector_bitstring") if traces else None,
                    }
                ),
                "candidate_distance": int(challenge["candidate_distance"]),
                "baseline_distance": int(challenge["baseline_distance"]),
                "physical_error": float(challenge["physical_error"]),
                "leakage_rate_per_tick": float(challenge["leakage_rate_per_tick"]),
                "false_positive_rate_per_tick": float(challenge["false_positive_rate_per_tick"]),
                "shots": len(traces),
                "synthetic_flag_events": synthetic_events,
                "logical_failures": logical_failures,
                "profile_result_rows": len(profile_rows),
                "hardware_like_model_flag_events": model_flag_events,
                "holdout_baseline_failures_across_profiles": holdout_failures,
                "holdout_injected_failures_across_profiles": holdout_injected_failures,
                "calibrated_flag_observation_rows": 0,
                "real_hardware_trace_rows": 0,
                "strict_holdout_improvement_rows": 0,
                "synthetic_trace_promoted_to_hardware": False,
            }
        )
    return rows


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    contract = load_json(args.contract_gate)
    guardrail = load_json(args.guardrail_gate)
    trace_packet = load_json(args.trace_packet)
    hardware_like = load_json(args.hardware_like_gate)

    contract_summary = contract["summary"]
    guardrail_summary = guardrail["summary"]
    trace_summary = trace_packet["summary"]
    hardware_summary = hardware_like["summary"]
    hardware_claims = hardware_like["claim_boundary"]
    profile_results = hardware_like.get("profile_results", [])
    rows = challenge_rows(trace_packet, profile_results)

    calibrated_flag_observation_rows = sum(row["calibrated_flag_observation_rows"] for row in rows)
    real_hardware_trace_rows = sum(row["real_hardware_trace_rows"] for row in rows)
    strict_holdout_improvement_rows = sum(row["strict_holdout_improvement_rows"] for row in rows)
    synthetic_trace_count = sum(row["shots"] for row in rows)
    synthetic_flag_events = sum(row["synthetic_flag_events"] for row in rows)
    trace_hash_rows = sum(bool(row["challenge_trace_hash"]) for row in rows)

    requirements = [
        requirement(
            "S1",
            "Calibrated-evidence contract source remains valid and open on K4-K6",
            contract.get("status") == "calibrated_evidence_contract_open_missing_hardware_data"
            and contract_summary.get("failed_contract_requirement_ids") == ["K4", "K5", "K6"]
            and contract_summary.get("data_contract_ready_for_prs") is True,
            {
                "source_status": contract.get("status"),
                "failed_contract_requirement_ids": contract_summary.get(
                    "failed_contract_requirement_ids"
                ),
                "data_contract_ready_for_prs": contract_summary.get("data_contract_ready_for_prs"),
            },
        ),
        requirement(
            "S2",
            "Per-shot synthetic trace packet is replayable",
            trace_summary.get("total_shot_traces") == 576
            and trace_summary.get("challenge_count") == 3
            and trace_hash_rows == 3,
            {
                "challenge_count": trace_summary.get("challenge_count"),
                "total_shot_traces": trace_summary.get("total_shot_traces"),
                "challenge_trace_hash_rows": trace_hash_rows,
            },
        ),
        requirement(
            "S3",
            "Hardware-like model profiles are mapped to challenge rows",
            hardware_summary.get("profile_result_count") == 9
            and hardware_summary.get("observation_profile_count") == 3,
            {
                "observation_profile_count": hardware_summary.get("observation_profile_count"),
                "profile_result_count": hardware_summary.get("profile_result_count"),
                "total_profile_shots": hardware_summary.get("total_profile_shots"),
                "holdout_profile_shots": hardware_summary.get("holdout_profile_shots"),
            },
        ),
        requirement(
            "S4",
            "Synthetic flag and hardware-like model pressure are visible",
            synthetic_flag_events == trace_summary.get("total_synthetic_flag_events")
            and guardrail_summary.get("best_profile_model_flag_events") == 415
            and guardrail_summary.get("stress_profile_model_flag_events") == 727,
            {
                "synthetic_flag_events": synthetic_flag_events,
                "best_profile_model_flag_events": guardrail_summary.get(
                    "best_profile_model_flag_events"
                ),
                "stress_profile_model_flag_events": guardrail_summary.get(
                    "stress_profile_model_flag_events"
                ),
            },
        ),
        requirement(
            "S5",
            "Calibrated leakage/flag observation rows are present",
            calibrated_flag_observation_rows > 0,
            {
                "calibrated_flag_observation_rows": calibrated_flag_observation_rows,
                "required_packet": "B2-C4-calibrated-flag-data",
            },
        ),
        requirement(
            "S6",
            "Real or independently calibrated hardware trace rows are present",
            real_hardware_trace_rows > 0,
            {
                "real_hardware_trace_rows": real_hardware_trace_rows,
                "required_packet": "B2-C5-hardware-trace-replay",
            },
        ),
        requirement(
            "S7",
            "Strict holdout improvement is demonstrated",
            guardrail_summary.get("holdout_improvement_gate_passed") is True
            and strict_holdout_improvement_rows == len(rows),
            {
                "best_profile": guardrail_summary.get("best_profile"),
                "best_profile_holdout_baseline_failures": guardrail_summary.get(
                    "best_profile_holdout_baseline_failures"
                ),
                "best_profile_holdout_injected_failures": guardrail_summary.get(
                    "best_profile_holdout_injected_failures"
                ),
                "best_profile_holdout_failure_delta": guardrail_summary.get(
                    "best_profile_holdout_failure_delta"
                ),
                "strict_holdout_improvement_rows": strict_holdout_improvement_rows,
            },
        ),
        requirement(
            "S8",
            "Forbidden claims remain false and synthetic traces are not promoted",
            not any(
                bool(hardware_claims.get(key))
                for key in [
                    "production_decoder_claimed",
                    "threshold_claimed",
                    "new_code_claimed",
                    "hardware_result_claimed",
                    "calibrated_device_claimed",
                    "quantum_advantage_claimed",
                ]
            )
            and all(row["synthetic_trace_promoted_to_hardware"] is False for row in rows),
            {
                "production_decoder_claimed": hardware_claims.get("production_decoder_claimed"),
                "threshold_claimed": hardware_claims.get("threshold_claimed"),
                "new_code_claimed": hardware_claims.get("new_code_claimed"),
                "hardware_result_claimed": hardware_claims.get("hardware_result_claimed"),
                "calibrated_device_claimed": hardware_claims.get("calibrated_device_claimed"),
                "quantum_advantage_claimed": hardware_claims.get("quantum_advantage_claimed"),
                "synthetic_trace_promoted_to_hardware_rows": sum(
                    row["synthetic_trace_promoted_to_hardware"] for row in rows
                ),
            },
        ),
    ]
    passed = sum(1 for item in requirements if item["passed"])
    failed_ids = [item["requirement_id"] for item in requirements if not item["passed"]]

    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected failed trace-scout requirements: {failed_ids}")
    if synthetic_trace_count != 576:
        validation_errors.append("expected 576 synthetic trace rows")
    if calibrated_flag_observation_rows != 0 or real_hardware_trace_rows != 0:
        validation_errors.append("synthetic scout must not contain real calibration/hardware rows")

    summary = {
        "source_contract_status": contract.get("status"),
        "source_guardrail_status": guardrail.get("status"),
        "trace_scout_requirement_count": len(requirements),
        "trace_scout_requirements_passed": passed,
        "trace_scout_requirements_failed": len(requirements) - passed,
        "failed_trace_scout_requirement_ids": failed_ids,
        "contract_packet_ids": contract_summary.get("contract_packet_ids"),
        "challenge_count": len(rows),
        "synthetic_trace_count": synthetic_trace_count,
        "challenge_trace_hash_rows": trace_hash_rows,
        "synthetic_flag_event_count": synthetic_flag_events,
        "hardware_like_profile_result_count": hardware_summary.get("profile_result_count"),
        "observation_profile_count": hardware_summary.get("observation_profile_count"),
        "total_profile_shots": hardware_summary.get("total_profile_shots"),
        "holdout_profile_shots": hardware_summary.get("holdout_profile_shots"),
        "best_profile": guardrail_summary.get("best_profile"),
        "best_profile_model_flag_events": guardrail_summary.get("best_profile_model_flag_events"),
        "stress_profile_model_flag_events": guardrail_summary.get("stress_profile_model_flag_events"),
        "best_profile_holdout_baseline_failures": guardrail_summary.get(
            "best_profile_holdout_baseline_failures"
        ),
        "best_profile_holdout_injected_failures": guardrail_summary.get(
            "best_profile_holdout_injected_failures"
        ),
        "best_profile_holdout_failure_delta": guardrail_summary.get(
            "best_profile_holdout_failure_delta"
        ),
        "calibrated_flag_observation_rows": calibrated_flag_observation_rows,
        "real_hardware_trace_rows": real_hardware_trace_rows,
        "strict_holdout_improvement_rows": strict_holdout_improvement_rows,
        "calibrated_trace_scout_ready": False,
        "calibration_transfer_ready": False,
        "production_decoder_ready": False,
        "threshold_claim_supported": False,
        "new_code_claimed": False,
        "threshold_claimed": False,
        "calibrated_device_claimed": False,
        "production_decoder_claimed": False,
        "hardware_result_claimed": False,
        "quantum_advantage_claimed": False,
        "validation_error_count": len(validation_errors),
    }

    return {
        "benchmark_id": "B2",
        "problem_id": 22,
        "title": "B2 calibrated trace scout v0",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_contract_gate_result": str(args.contract_gate),
        "source_guardrail_gate_result": str(args.guardrail_gate),
        "source_trace_packet_result": str(args.trace_packet),
        "source_hardware_like_gate_result": str(args.hardware_like_gate),
        "toolchain": (
            "Maps existing synthetic B2 trace fixtures and hardware-like profile rows "
            "to the calibrated-evidence contract without treating them as calibrated hardware data."
        ),
        "summary": summary,
        "requirements": requirements,
        "rows": rows,
        "claim_boundary": {
            "calibrated_trace_scout_built": True,
            "synthetic_trace_fixture_used": True,
            "hardware_like_model_used": True,
            "calibrated_flag_data_used": False,
            "real_hardware_trace_used": False,
            "holdout_improvement_gate_passed": False,
            "production_decoder_claimed": False,
            "threshold_claimed": False,
            "new_code_claimed": False,
            "hardware_result_claimed": False,
            "calibrated_device_claimed": False,
            "quantum_advantage_claimed": False,
            "what_is_supported": (
                "The existing synthetic trace fixture and hardware-like profile results are now mapped "
                "row by row to the B2 calibrated-evidence contract."
            ),
            "what_is_not_supported": (
                "This is not calibrated leakage data, not real hardware trace replay, not strict holdout "
                "improvement, not a production decoder, not a threshold result, and not a hardware claim."
            ),
            "next_gate": (
                "Submit B2-C4 calibrated flag data, B2-C5 hardware trace replay, and B2-C6 strict holdout "
                "improvement without changing the per-shot trace schema."
            ),
        },
        "validation_errors": validation_errors,
        "elapsed_seconds": time.time() - started,
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# B2 Calibrated Trace Scout v0.1",
        "",
        f"Status: **{payload['status']}**",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Model status: `{payload['model_status']}`",
        f"- Requirements passed/failed: {summary['trace_scout_requirements_passed']} / {summary['trace_scout_requirements_failed']}",
        f"- Failed requirement IDs: {', '.join(summary['failed_trace_scout_requirement_ids'])}",
        f"- Synthetic trace rows: {summary['synthetic_trace_count']}",
        f"- Challenge trace hashes: {summary['challenge_trace_hash_rows']}",
        f"- Synthetic flag events: {summary['synthetic_flag_event_count']}",
        f"- Hardware-like profile results: {summary['hardware_like_profile_result_count']}",
        f"- Holdout profile shots: {summary['holdout_profile_shots']}",
        f"- Best holdout baseline/injected/delta: {summary['best_profile_holdout_baseline_failures']} / {summary['best_profile_holdout_injected_failures']} / {summary['best_profile_holdout_failure_delta']}",
        f"- Calibrated flag observation rows: {summary['calibrated_flag_observation_rows']}",
        f"- Real hardware trace rows: {summary['real_hardware_trace_rows']}",
        f"- Strict holdout improvement rows: {summary['strict_holdout_improvement_rows']}",
        "",
        "## Requirement Results",
        "",
    ]
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
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract-gate", type=Path, default=Path("results/B2_calibrated_evidence_contract_gate_v0.json"))
    parser.add_argument("--guardrail-gate", type=Path, default=Path("results/B2_calibration_transfer_guardrail_gate_v0.json"))
    parser.add_argument("--trace-packet", type=Path, default=Path("results/B2_per_shot_decoder_trace_packet_v0.json"))
    parser.add_argument("--hardware-like-gate", type=Path, default=Path("results/B2_hardware_like_leakage_model_gate_v0.json"))
    parser.add_argument("--json-output", type=Path, default=Path("results/B2_calibrated_trace_scout_v0.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("research/B2_calibrated_trace_scout.md"))
    parser.add_argument("--last-updated", default="2026-07-01")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    write_markdown(payload, args.markdown_output)
    print(payload["status"])
    print(
        payload["summary"]["trace_scout_requirements_passed"],
        payload["summary"]["trace_scout_requirements_failed"],
        payload["summary"]["failed_trace_scout_requirement_ids"],
    )


if __name__ == "__main__":
    main()
