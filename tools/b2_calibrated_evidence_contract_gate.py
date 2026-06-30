#!/usr/bin/env python3
"""Build the B2 calibrated-evidence contract after the transfer guardrail fails."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b2_calibrated_evidence_contract_gate_v0"
STATUS = "calibrated_evidence_contract_open_missing_hardware_data"
MODEL_STATUS = "calibration_transfer_blockers_decomposed_for_data_prs"
VERSION = "0.1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
        sort_keys=True,
    )
    path.write_text(text + "\n", encoding="utf-8")


def contract_gate(
    gate_id: str,
    label: str,
    passed: bool,
    evidence: dict[str, Any],
    acceptance_rule: str,
    pr_packet: str,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
        "acceptance_rule": acceptance_rule,
        "pr_packet": pr_packet,
    }


def build_contract_packets(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "packet_id": "B2-C4-calibrated-flag-data",
            "blocks_gate": "K4",
            "owner_role": "hardware_data_or_calibration_agent",
            "required_artifacts": [
                "per-shot detector bitstrings using the existing B2 trace schema",
                "per-shot observable bitstrings or logical labels",
                "detector-tick-indexed leakage/erasure/flag events",
                "calibrated flag confusion matrix with provenance",
                "calibration date, backend family, noise slice, and shot count metadata",
            ],
            "acceptance_rule": (
                "calibrated_flag_data_used must become true without changing the "
                "per-shot decoder interface or claiming hardware advantage."
            ),
        },
        {
            "packet_id": "B2-C5-hardware-trace-replay",
            "blocks_gate": "K5",
            "owner_role": "hardware_trace_replay_agent",
            "required_artifacts": [
                "independent real or provider-calibrated trace rows",
                "same decoder replay command used for synthetic B2 traces",
                "source-to-result trace hash ledger",
                "explicit separation between calibration, model-selection, and holdout slices",
            ],
            "acceptance_rule": (
                "real_hardware_trace_used must become true and replay must produce "
                "the same summary fields as the current guardrail."
            ),
        },
        {
            "packet_id": "B2-C6-holdout-improvement",
            "blocks_gate": "K6",
            "owner_role": "decoder_baseline_adversary_agent",
            "required_artifacts": [
                "strict holdout baseline logical failure count",
                "strict holdout injected logical failure count",
                "all-challenge non-regression table",
                "runtime and changed-prediction audit",
                "negative-control profile where flags are shuffled or withheld",
            ],
            "acceptance_rule": (
                "best_profile_holdout_injected_failures must be strictly lower "
                f"than the current baseline {summary['best_profile_holdout_baseline_failures']} "
                "while introduced failures remain zero."
            ),
        },
    ]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    source = load_json(args.guardrail_result)
    source_summary = source["summary"]
    source_claims = source["claim_boundary"]

    missing_source_gates = source_summary["missing_calibration_gate_ids"]
    contract_packets = build_contract_packets(source_summary)
    packet_ids = [packet["packet_id"] for packet in contract_packets]

    contract_requirements = [
        contract_gate(
            "K1",
            "Source guardrail is a valid negative calibration-transfer boundary",
            source.get("benchmark_id") == "B2"
            and source.get("method") == "b2_calibration_transfer_guardrail_gate_v0"
            and len(source.get("validation_errors", [])) == 0
            and missing_source_gates == ["C4", "C5", "C6"],
            {
                "source_method": source.get("method"),
                "source_status": source.get("status"),
                "source_validation_error_count": len(source.get("validation_errors", [])),
                "missing_source_gates": missing_source_gates,
            },
            "The source guardrail must stay valid and fail only C4/C5/C6.",
            "source-audit",
        ),
        contract_gate(
            "K2",
            "Replayable per-shot trace schema remains available",
            source_summary["source_trace_count"] == 576
            and source_summary["source_challenge_count"] == 3,
            {
                "source_challenge_count": source_summary["source_challenge_count"],
                "source_trace_count": source_summary["source_trace_count"],
            },
            "Keep at least the current three-challenge / 576-trace replay shape.",
            "trace-schema",
        ),
        contract_gate(
            "K3",
            "PR packets exist for every failed calibration-transfer gate",
            [packet["blocks_gate"] for packet in contract_packets] == ["K4", "K5", "K6"],
            {
                "contract_packet_count": len(contract_packets),
                "contract_packet_ids": packet_ids,
            },
            "Every failed blocker must map to a concrete PR packet.",
            "packet-index",
        ),
        contract_gate(
            "K4",
            "Calibrated flag-data packet has been satisfied",
            bool(source_summary["calibrated_flag_data_used"]),
            {
                "source_gate": "C4",
                "calibrated_flag_data_used": source_summary["calibrated_flag_data_used"],
            },
            "Submit calibrated leakage/erasure flag observations with confusion metadata.",
            "B2-C4-calibrated-flag-data",
        ),
        contract_gate(
            "K5",
            "Real hardware trace-replay packet has been satisfied",
            bool(source_summary["real_hardware_trace_used"]),
            {
                "source_gate": "C5",
                "real_hardware_trace_used": source_summary["real_hardware_trace_used"],
            },
            "Submit real or independently calibrated hardware traces replayed by the same decoder.",
            "B2-C5-hardware-trace-replay",
        ),
        contract_gate(
            "K6",
            "Holdout improvement packet has been satisfied",
            bool(source_summary["holdout_improvement_gate_passed"]),
            {
                "source_gate": "C6",
                "best_profile": source_summary["best_profile"],
                "holdout_baseline_failures": source_summary[
                    "best_profile_holdout_baseline_failures"
                ],
                "holdout_injected_failures": source_summary[
                    "best_profile_holdout_injected_failures"
                ],
                "holdout_failure_delta": source_summary[
                    "best_profile_holdout_failure_delta"
                ],
            },
            "Show strictly fewer holdout logical failures under calibrated injection.",
            "B2-C6-holdout-improvement",
        ),
        contract_gate(
            "K7",
            "Holdout non-regression remains preserved",
            bool(source_summary["holdout_nonregression_gate_passed"]),
            {
                "holdout_nonregression_gate_passed": source_summary[
                    "holdout_nonregression_gate_passed"
                ],
                "stress_profile_no_introduced_failures": source_summary[
                    "stress_profile_no_introduced_failures"
                ],
            },
            "Keep non-regression true after C4/C5 data are introduced.",
            "holdout-nonregression",
        ),
        contract_gate(
            "K8",
            "Forbidden production, threshold, hardware, and advantage claims remain absent",
            not any(
                bool(source_claims[key])
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
                "production_decoder_claimed": source_claims["production_decoder_claimed"],
                "threshold_claimed": source_claims["threshold_claimed"],
                "new_code_claimed": source_claims["new_code_claimed"],
                "hardware_result_claimed": source_claims["hardware_result_claimed"],
                "calibrated_device_claimed": source_claims["calibrated_device_claimed"],
                "quantum_advantage_claimed": source_claims["quantum_advantage_claimed"],
            },
            "Do not promote B2 until K4-K6 pass under replayable evidence.",
            "claim-boundary",
        ),
    ]

    passed_count = sum(1 for item in contract_requirements if item["passed"])
    failed_count = len(contract_requirements) - passed_count
    failed_ids = [item["gate_id"] for item in contract_requirements if not item["passed"]]

    summary = {
        "source_method": source.get("method"),
        "source_status": source.get("status"),
        "source_missing_gate_ids": missing_source_gates,
        "source_challenge_count": source_summary["source_challenge_count"],
        "source_trace_count": source_summary["source_trace_count"],
        "observation_profile_count": source_summary["observation_profile_count"],
        "profile_result_count": source_summary["profile_result_count"],
        "total_profile_shots": source_summary["total_profile_shots"],
        "holdout_profile_shots": source_summary["holdout_profile_shots"],
        "best_profile": source_summary["best_profile"],
        "best_profile_model_flag_events": source_summary[
            "best_profile_model_flag_events"
        ],
        "stress_profile_model_flag_events": source_summary[
            "stress_profile_model_flag_events"
        ],
        "best_profile_holdout_baseline_failures": source_summary[
            "best_profile_holdout_baseline_failures"
        ],
        "best_profile_holdout_injected_failures": source_summary[
            "best_profile_holdout_injected_failures"
        ],
        "best_profile_holdout_failure_delta": source_summary[
            "best_profile_holdout_failure_delta"
        ],
        "contract_requirement_count": len(contract_requirements),
        "passed_contract_requirement_count": passed_count,
        "failed_contract_requirement_count": failed_count,
        "failed_contract_requirement_ids": failed_ids,
        "contract_packet_count": len(contract_packets),
        "contract_packet_ids": packet_ids,
        "calibrated_flag_data_required": True,
        "real_hardware_trace_required": True,
        "holdout_improvement_required": True,
        "calibrated_flag_data_used": source_summary["calibrated_flag_data_used"],
        "real_hardware_trace_used": source_summary["real_hardware_trace_used"],
        "holdout_improvement_gate_passed": source_summary[
            "holdout_improvement_gate_passed"
        ],
        "holdout_nonregression_gate_passed": source_summary[
            "holdout_nonregression_gate_passed"
        ],
        "calibration_transfer_ready": False,
        "production_decoder_ready": False,
        "threshold_claim_supported": False,
        "data_contract_ready_for_prs": True,
    }

    report = {
        "benchmark_id": "B2",
        "problem_id": 22,
        "title": "B2 calibrated evidence contract gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "status": STATUS,
        "method": METHOD,
        "model_status": MODEL_STATUS,
        "toolchain": (
            "Consumes the B2 calibration-transfer guardrail and decomposes its "
            "C4/C5/C6 blockers into PR-ready data contracts for calibrated "
            "flag data, hardware trace replay, and strict holdout improvement."
        ),
        "sources": {"guardrail_result": str(args.guardrail_result)},
        "summary": summary,
        "contract_requirements": contract_requirements,
        "contract_packets": contract_packets,
        "claim_boundary": {
            "calibrated_evidence_contract_built": True,
            "calibration_transfer_ready": False,
            "production_decoder_claimed": False,
            "threshold_claimed": False,
            "new_code_claimed": False,
            "hardware_result_claimed": False,
            "calibrated_device_claimed": False,
            "quantum_advantage_claimed": False,
            "what_is_supported": (
                "B2 now has explicit PR packets for the three blockers that "
                "prevent calibration transfer: calibrated flag data, real or "
                "independently calibrated hardware traces, and strict holdout "
                "improvement with non-regression."
            ),
            "what_is_not_supported": (
                "No new calibrated flag data, real hardware trace, holdout "
                "improvement, production decoder, threshold, or low-overhead "
                "QEC claim is established by this contract gate."
            ),
        },
        "elapsed_seconds": time.time() - started,
    }
    report["validation_errors"] = validate(report)
    return report


def validate(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = report["summary"]
    claims = report["claim_boundary"]

    if summary["source_missing_gate_ids"] != ["C4", "C5", "C6"]:
        errors.append("source missing gates must remain C4/C5/C6")
    if summary["source_challenge_count"] != 3:
        errors.append("expected three source challenges")
    if summary["source_trace_count"] != 576:
        errors.append("expected 576 source traces")
    if summary["contract_requirement_count"] != 8:
        errors.append("expected eight contract requirements")
    if summary["passed_contract_requirement_count"] != 5:
        errors.append("current contract should pass five requirements")
    if summary["failed_contract_requirement_count"] != 3:
        errors.append("current contract should fail three requirements")
    if summary["failed_contract_requirement_ids"] != ["K4", "K5", "K6"]:
        errors.append("current failed contract ids should be K4/K5/K6")
    if summary["contract_packet_count"] != 3:
        errors.append("expected three contract packets")
    if summary["contract_packet_ids"] != [
        "B2-C4-calibrated-flag-data",
        "B2-C5-hardware-trace-replay",
        "B2-C6-holdout-improvement",
    ]:
        errors.append("unexpected contract packet ids")
    for key in [
        "calibrated_flag_data_required",
        "real_hardware_trace_required",
        "holdout_improvement_required",
        "holdout_nonregression_gate_passed",
        "data_contract_ready_for_prs",
    ]:
        if summary.get(key) is not True:
            errors.append(f"{key} must be true")
    for key in [
        "calibrated_flag_data_used",
        "real_hardware_trace_used",
        "holdout_improvement_gate_passed",
        "calibration_transfer_ready",
        "production_decoder_ready",
        "threshold_claim_supported",
    ]:
        if summary.get(key) is not False:
            errors.append(f"{key} must remain false")
    if summary["best_profile_holdout_baseline_failures"] != 16:
        errors.append("expected current holdout baseline failures to remain 16")
    if summary["best_profile_holdout_injected_failures"] != 16:
        errors.append("expected current holdout injected failures to remain 16")
    if summary["best_profile_holdout_failure_delta"] != 0:
        errors.append("expected current holdout failure delta to remain 0")
    if claims.get("calibrated_evidence_contract_built") is not True:
        errors.append("claim boundary must disclose calibrated evidence contract")
    if claims.get("calibration_transfer_ready") is not False:
        errors.append("contract must not claim calibration transfer readiness")
    for key in [
        "production_decoder_claimed",
        "threshold_claimed",
        "new_code_claimed",
        "hardware_result_claimed",
        "calibrated_device_claimed",
        "quantum_advantage_claimed",
    ]:
        if claims.get(key) is not False:
            errors.append(f"{key} must remain false")
    return errors


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# B2 Calibrated Evidence Contract Gate v0.1",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Summary",
        "",
        f"- Method: {report['method']}",
        f"- Model status: {report['model_status']}",
        f"- Source guardrail method: {summary['source_method']}",
        f"- Source missing gates: {', '.join(summary['source_missing_gate_ids'])}",
        f"- Source challenge count / trace count: {summary['source_challenge_count']} / {summary['source_trace_count']}",
        f"- Observation profiles / profile rows: {summary['observation_profile_count']} / {summary['profile_result_count']}",
        f"- Total profile shots / holdout shots: {summary['total_profile_shots']} / {summary['holdout_profile_shots']}",
        f"- Best profile: {summary['best_profile']}",
        f"- Best-profile model flag events: {summary['best_profile_model_flag_events']}",
        f"- Stress-profile model flag events: {summary['stress_profile_model_flag_events']}",
        f"- Best-profile holdout baseline / injected / delta: {summary['best_profile_holdout_baseline_failures']} / {summary['best_profile_holdout_injected_failures']} / {summary['best_profile_holdout_failure_delta']}",
        f"- Contract requirements passed / failed: {summary['passed_contract_requirement_count']} / {summary['failed_contract_requirement_count']}",
        f"- Failed contract requirement ids: {', '.join(summary['failed_contract_requirement_ids'])}",
        f"- Contract packets: {', '.join(summary['contract_packet_ids'])}",
        f"- Data contract ready for PRs: {summary['data_contract_ready_for_prs']}",
        f"- Calibration transfer ready: {summary['calibration_transfer_ready']}",
        f"- Production decoder ready: {summary['production_decoder_ready']}",
        f"- Threshold claim supported: {summary['threshold_claim_supported']}",
        f"- Validation errors: {report['validation_errors']}",
        "",
        "## Contract Requirements",
        "",
        "| gate | passed | label | PR packet | acceptance rule |",
        "|---|---:|---|---|---|",
    ]
    for item in report["contract_requirements"]:
        lines.append(
            f"| {item['gate_id']} | {item['passed']} | {item['label']} | "
            f"{item['pr_packet']} | {item['acceptance_rule']} |"
        )

    lines.extend(["", "## PR Packets", ""])
    for packet in report["contract_packets"]:
        lines.extend(
            [
                f"### {packet['packet_id']}",
                "",
                f"- Blocks gate: {packet['blocks_gate']}",
                f"- Owner role: {packet['owner_role']}",
                f"- Acceptance rule: {packet['acceptance_rule']}",
                "- Required artifacts:",
            ]
        )
        for artifact in packet["required_artifacts"]:
            lines.append(f"  - {artifact}")
        lines.append("")

    lines.extend(["## Claim Boundary", ""])
    for key, value in report["claim_boundary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            "A future B2 PR must satisfy K4-K6 together: calibrated flag data,",
            "real or independently calibrated hardware trace replay, and strictly",
            "lower holdout logical failures with non-regression preserved. Until",
            "then, B2 remains a disciplined negative boundary rather than a",
            "low-overhead QEC claim.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--guardrail-result",
        type=Path,
        default=Path("results/B2_calibration_transfer_guardrail_gate_v0.json"),
    )
    parser.add_argument("--last-updated", default="2026-07-01")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B2_calibrated_evidence_contract_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B2_calibrated_evidence_contract_gate.md"),
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    report = build_report(args)
    write_json(args.json_output, report, args.pretty)
    write_markdown(report, args.markdown_output)
    print(
        json.dumps(
            {
                "status": report["status"],
                "method": report["method"],
                **report["summary"],
                "validation_errors": report["validation_errors"],
            },
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
