#!/usr/bin/env python3
"""Build calibrated-trace intake packets for the open B2 calibration blockers."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b2_calibrated_trace_intake_template_gate_v0"
STATUS = "calibrated_trace_intake_template_open_missing_rows"
MODEL_STATUS = "calibrated_trace_schema_and_holdout_packets_built_no_calibrated_rows"
VERSION = "0.1"
EXPECTED_FAILED_IDS = ["T5", "T6", "T7"]
REQUIRED_ROW_KEYS = [
    "trace_id",
    "challenge_id",
    "challenge_trace_hash",
    "backend_or_calibration_source",
    "backend_properties_hash",
    "shot_index",
    "detector_bitstring_hash",
    "observable_bit",
    "calibrated_flag_events_hash",
    "flag_confusion_matrix_hash",
    "leakage_rate_per_tick",
    "false_positive_rate_per_tick",
    "decoder_profile",
    "baseline_prediction",
    "injected_prediction",
    "logical_label",
    "holdout_partition",
    "decoder_runtime_seconds",
    "raw_trace_artifact_sha256",
    "postprocess_script_sha256",
    "claim_boundary",
]
PRODUCTION_REQUIRED_KEYS = [
    "backend_or_calibration_source",
    "backend_properties_hash",
    "detector_bitstring_hash",
    "calibrated_flag_events_hash",
    "flag_confusion_matrix_hash",
    "decoder_profile",
    "baseline_prediction",
    "injected_prediction",
    "raw_trace_artifact_sha256",
    "postprocess_script_sha256",
]


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


def packet(
    packet_id: str,
    blocks_contract_gate: str,
    blocks_scout_gate: str,
    owner_role: str,
    acceptance_rule: str,
    current_evidence: dict[str, Any],
) -> dict[str, Any]:
    row = {
        "packet_id": packet_id,
        "blocks_contract_gate": blocks_contract_gate,
        "blocks_scout_gate": blocks_scout_gate,
        "owner_role": owner_role,
        "acceptance_rule": acceptance_rule,
        "current_evidence": current_evidence,
        "required_row_keys": REQUIRED_ROW_KEYS,
        "production_required_keys": PRODUCTION_REQUIRED_KEYS,
        "submitted_calibrated_rows": 0,
        "accepted_calibrated_rows": 0,
        "ready_for_calibration_retest": False,
    }
    row["template_hash"] = stable_hash(
        {
            "packet_id": packet_id,
            "blocks_contract_gate": blocks_contract_gate,
            "blocks_scout_gate": blocks_scout_gate,
            "required_row_keys": REQUIRED_ROW_KEYS,
            "production_required_keys": PRODUCTION_REQUIRED_KEYS,
            "acceptance_rule": acceptance_rule,
        }
    )
    return row


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    contract = load_json(args.contract_gate)
    scout = load_json(args.trace_scout)
    contract_summary = contract["summary"]
    scout_summary = scout["summary"]

    failed_contract_ids = contract_summary["failed_contract_requirement_ids"]
    failed_scout_ids = scout_summary["failed_trace_scout_requirement_ids"]
    source_trace_count = int(scout_summary["synthetic_trace_count"])
    challenge_count = int(scout_summary["challenge_count"])
    holdout_profile_shots = int(scout_summary["holdout_profile_shots"])

    packets = [
        packet(
            "B2-T5-calibrated-flag-observation-rows",
            "K4",
            "S5",
            "hardware_data_or_calibration_agent",
            "Submit calibrated leakage/erasure flag observation rows using the 21-key trace schema and preserve the existing challenge trace hashes.",
            {
                "current_calibrated_flag_observation_rows": scout_summary[
                    "calibrated_flag_observation_rows"
                ],
                "synthetic_flag_event_count": scout_summary["synthetic_flag_event_count"],
                "challenge_trace_hash_rows": scout_summary["challenge_trace_hash_rows"],
            },
        ),
        packet(
            "B2-T6-real-or-independent-trace-replay",
            "K5",
            "S6",
            "hardware_trace_replay_agent",
            "Submit real or independently calibrated trace rows and replay them through the same decoder interface without changing the per-shot schema.",
            {
                "current_real_hardware_trace_rows": scout_summary["real_hardware_trace_rows"],
                "source_trace_count": source_trace_count,
                "challenge_count": challenge_count,
            },
        ),
        packet(
            "B2-T7-strict-holdout-improvement",
            "K6",
            "S7",
            "decoder_baseline_adversary_agent",
            "Show strict holdout improvement: injected failures must be below the baseline 16 while all challenge rows preserve non-regression.",
            {
                "best_profile": scout_summary["best_profile"],
                "best_profile_holdout_baseline_failures": scout_summary[
                    "best_profile_holdout_baseline_failures"
                ],
                "best_profile_holdout_injected_failures": scout_summary[
                    "best_profile_holdout_injected_failures"
                ],
                "best_profile_holdout_failure_delta": scout_summary[
                    "best_profile_holdout_failure_delta"
                ],
                "strict_holdout_improvement_rows": scout_summary[
                    "strict_holdout_improvement_rows"
                ],
            },
        ),
    ]

    submitted_rows = sum(row["submitted_calibrated_rows"] for row in packets)
    accepted_rows = sum(row["accepted_calibrated_rows"] for row in packets)
    template_table_hash = stable_hash(packets)

    requirements = [
        requirement(
            "T1",
            "Calibrated evidence contract is open on K4-K6",
            contract.get("method") == "b2_calibrated_evidence_contract_gate_v0"
            and failed_contract_ids == ["K4", "K5", "K6"]
            and contract_summary["data_contract_ready_for_prs"] is True,
            {
                "source_method": contract.get("method"),
                "source_status": contract.get("status"),
                "failed_contract_requirement_ids": failed_contract_ids,
            },
        ),
        requirement(
            "T2",
            "Trace scout is open on S5-S7 and preserves synthetic-only boundaries",
            scout.get("method") == "b2_calibrated_trace_scout_v0"
            and failed_scout_ids == ["S5", "S6", "S7"]
            and scout_summary["calibrated_flag_observation_rows"] == 0
            and scout_summary["real_hardware_trace_rows"] == 0,
            {
                "source_method": scout.get("method"),
                "source_status": scout.get("status"),
                "failed_trace_scout_requirement_ids": failed_scout_ids,
                "calibrated_flag_observation_rows": scout_summary[
                    "calibrated_flag_observation_rows"
                ],
                "real_hardware_trace_rows": scout_summary["real_hardware_trace_rows"],
            },
        ),
        requirement(
            "T3",
            "Three calibrated-trace intake packets map one-to-one to blockers",
            [row["blocks_contract_gate"] for row in packets] == failed_contract_ids
            and [row["blocks_scout_gate"] for row in packets] == failed_scout_ids,
            {
                "packet_count": len(packets),
                "packet_ids": [row["packet_id"] for row in packets],
                "contract_gate_sequence": [row["blocks_contract_gate"] for row in packets],
                "scout_gate_sequence": [row["blocks_scout_gate"] for row in packets],
            },
        ),
        requirement(
            "T4",
            "Trace row schema is explicit and hashable",
            len(REQUIRED_ROW_KEYS) == 21 and len(PRODUCTION_REQUIRED_KEYS) == 10,
            {
                "required_row_key_count": len(REQUIRED_ROW_KEYS),
                "production_required_key_count": len(PRODUCTION_REQUIRED_KEYS),
                "template_table_hash": template_table_hash,
            },
        ),
        requirement(
            "T5",
            "Submitted calibrated trace rows are present",
            submitted_rows > 0,
            {"submitted_calibrated_rows": submitted_rows},
        ),
        requirement(
            "T6",
            "Accepted calibrated trace rows cover all packets",
            accepted_rows >= len(packets),
            {"accepted_calibrated_rows": accepted_rows, "required_packet_count": len(packets)},
        ),
        requirement(
            "T7",
            "Calibration retest is ready",
            all(row["ready_for_calibration_retest"] for row in packets),
            {
                "ready_packet_count": sum(row["ready_for_calibration_retest"] for row in packets),
                "required_packet_count": len(packets),
            },
        ),
        requirement(
            "T8",
            "Forbidden production, threshold, hardware, and advantage claims remain false",
            all(
                scout["claim_boundary"].get(key) is False
                for key in [
                    "production_decoder_claimed",
                    "threshold_claimed",
                    "new_code_claimed",
                    "hardware_result_claimed",
                    "calibrated_device_claimed",
                    "quantum_advantage_claimed",
                ]
            ),
            {
                "production_decoder_claimed": scout["claim_boundary"].get(
                    "production_decoder_claimed"
                ),
                "threshold_claimed": scout["claim_boundary"].get("threshold_claimed"),
                "hardware_result_claimed": scout["claim_boundary"].get("hardware_result_claimed"),
                "calibrated_device_claimed": scout["claim_boundary"].get(
                    "calibrated_device_claimed"
                ),
                "quantum_advantage_claimed": scout["claim_boundary"].get(
                    "quantum_advantage_claimed"
                ),
            },
        ),
    ]

    passed_count = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected calibrated-trace intake failures: {failed_ids}")
    if submitted_rows != 0 or accepted_rows != 0:
        validation_errors.append("intake template must not fabricate calibrated rows")
    if source_trace_count != 576 or challenge_count != 3:
        validation_errors.append("intake template must preserve the existing B2 trace shape")

    summary = {
        "source_contract_status": contract.get("status"),
        "source_trace_scout_status": scout.get("status"),
        "intake_requirement_count": len(requirements),
        "intake_requirements_passed": passed_count,
        "intake_requirements_failed": len(requirements) - passed_count,
        "failed_intake_requirement_ids": failed_ids,
        "failed_contract_requirement_ids": failed_contract_ids,
        "failed_trace_scout_requirement_ids": failed_scout_ids,
        "packet_count": len(packets),
        "packet_ids": [row["packet_id"] for row in packets],
        "required_row_key_count": len(REQUIRED_ROW_KEYS),
        "production_required_key_count": len(PRODUCTION_REQUIRED_KEYS),
        "template_table_hash": template_table_hash,
        "challenge_count": challenge_count,
        "source_trace_count": source_trace_count,
        "holdout_profile_shots": holdout_profile_shots,
        "synthetic_flag_event_count": scout_summary["synthetic_flag_event_count"],
        "calibrated_flag_observation_rows": scout_summary["calibrated_flag_observation_rows"],
        "real_hardware_trace_rows": scout_summary["real_hardware_trace_rows"],
        "strict_holdout_improvement_rows": scout_summary["strict_holdout_improvement_rows"],
        "best_profile_holdout_baseline_failures": scout_summary[
            "best_profile_holdout_baseline_failures"
        ],
        "best_profile_holdout_injected_failures": scout_summary[
            "best_profile_holdout_injected_failures"
        ],
        "best_profile_holdout_failure_delta": scout_summary[
            "best_profile_holdout_failure_delta"
        ],
        "submitted_calibrated_rows": submitted_rows,
        "accepted_calibrated_rows": accepted_rows,
        "calibrated_trace_intake_ready": False,
        "calibration_retest_ready": False,
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
        "title": "B2 Calibrated Trace Intake Template Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_contract_gate_result": str(args.contract_gate),
        "source_trace_scout_result": str(args.trace_scout),
        "summary": summary,
        "requirements": requirements,
        "required_row_keys": REQUIRED_ROW_KEYS,
        "production_required_keys": PRODUCTION_REQUIRED_KEYS,
        "intake_packets": packets,
        "claim_boundary": {
            "what_is_supported": (
                "The open B2 calibration blockers K4/S5, K5/S6, and K6/S7 are converted "
                "into hashable calibrated-trace intake packets with explicit row keys."
            ),
            "what_is_not_supported": (
                "No calibrated rows are submitted or accepted, no calibration retest is ready, "
                "and there is no production decoder, threshold, hardware, new-code, or "
                "quantum-advantage claim."
            ),
            "next_gate": (
                "Submit calibrated flag rows, real or independently calibrated trace replay "
                "rows, and strict holdout-improvement evidence while preserving the 3-challenge "
                "/ 576-trace shape."
            ),
            "production_decoder_claimed": False,
            "threshold_claimed": False,
            "new_code_claimed": False,
            "hardware_result_claimed": False,
            "calibrated_device_claimed": False,
            "quantum_advantage_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": time.time() - started,
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# B2 Calibrated Trace Intake Template Gate",
        "",
        f"Status: **{payload['status']}**",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Model status: `{payload['model_status']}`",
        f"- Intake requirements passed/failed: {summary['intake_requirements_passed']} / {summary['intake_requirements_failed']}",
        f"- Failed intake requirement IDs: {summary['failed_intake_requirement_ids']}",
        f"- Contract blockers: {summary['failed_contract_requirement_ids']}",
        f"- Trace-scout blockers: {summary['failed_trace_scout_requirement_ids']}",
        f"- Challenge count / source traces: {summary['challenge_count']} / {summary['source_trace_count']}",
        f"- Holdout profile shots: {summary['holdout_profile_shots']}",
        f"- Required row keys / production-required keys: {summary['required_row_key_count']} / {summary['production_required_key_count']}",
        f"- Template table hash: `{summary['template_table_hash']}`",
        f"- Calibrated flag rows / real hardware rows / strict improvement rows: {summary['calibrated_flag_observation_rows']} / {summary['real_hardware_trace_rows']} / {summary['strict_holdout_improvement_rows']}",
        "",
        "## Intake Packets",
        "",
        "| Packet | Blocks contract | Blocks scout | Owner | Submitted rows | Accepted rows | Ready |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for row in payload["intake_packets"]:
        lines.append(
            f"| {row['packet_id']} | {row['blocks_contract_gate']} | {row['blocks_scout_gate']} | "
            f"{row['owner_role']} | {row['submitted_calibrated_rows']} | "
            f"{row['accepted_calibrated_rows']} | {row['ready_for_calibration_retest']} |"
        )
    lines.extend(
        [
            "",
            "## Trace Row Schema",
            "",
            ", ".join(payload["required_row_keys"]),
            "",
            "## Requirement Results",
            "",
        ]
    )
    for row in payload["requirements"]:
        status = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- {row['requirement_id']} [{status}]: {row['label']}")
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
            f"- quantum_advantage_claimed: {payload['claim_boundary']['quantum_advantage_claimed']}",
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
        "--contract-gate",
        type=Path,
        default=Path("results/B2_calibrated_evidence_contract_gate_v0.json"),
    )
    parser.add_argument(
        "--trace-scout",
        type=Path,
        default=Path("results/B2_calibrated_trace_scout_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B2_calibrated_trace_intake_template_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B2_calibrated_trace_intake_template_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-01")
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
