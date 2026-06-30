#!/usr/bin/env python3
"""Audit whether the B2 hardware-like leakage model can transfer to calibrated claims."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b2_calibration_transfer_guardrail_gate_v0"
STATUS = "calibration_transfer_guardrail_failed"
MODEL_STATUS = "hardware_like_model_has_no_calibrated_or_hardware_transfer_evidence"
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


def gate(
    gate_id: str,
    label: str,
    passed: bool,
    evidence: dict[str, Any],
    missing_to_promote: str,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
        "missing_to_promote": missing_to_promote,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    hardware = load_json(args.hardware_like_result)
    per_shot = load_json(args.per_shot_trace_result)
    posterior = load_json(args.posterior_injection_result)
    dem = load_json(args.dem_edge_result)

    hardware_summary = hardware["summary"]
    per_shot_summary = per_shot["summary"]
    posterior_summary = posterior["summary"]
    dem_summary = dem["summary"]
    claims = hardware["claim_boundary"]
    by_profile = hardware_summary["by_profile"]
    stress_profile = by_profile["stress_hardware_like_leakage"]

    calibrated_flag_data_used = bool(hardware_summary["calibrated_flag_data_used"])
    real_hardware_trace_used = bool(hardware_summary["real_hardware_trace_used"])
    holdout_improvement_gate_passed = bool(hardware_summary["holdout_improvement_gate_passed"])
    holdout_nonregression_gate_passed = bool(
        hardware_summary["holdout_nonregression_gate_passed"]
    )
    stress_profile_no_introduced_failures = int(stress_profile["introduced_failures"]) == 0
    posterior_route_demoted = bool(posterior_summary["route_demotion_recommended"])
    dem_route_demoted = bool(dem_summary["route_demotion_recommended"])
    hardware_route_demoted = bool(hardware_summary["route_demotion_recommended"])

    calibration_requirements = [
        gate(
            "C1",
            "Per-shot detector and observable traces are persisted",
            bool(per_shot_summary["per_shot_detector_bitstrings_persisted"])
            and bool(per_shot_summary["stim_observable_bitstrings_persisted"]),
            {
                "total_shot_traces": per_shot_summary["total_shot_traces"],
                "max_detector_count": per_shot_summary["max_detector_count"],
                "per_shot_detector_bitstrings_persisted": per_shot_summary[
                    "per_shot_detector_bitstrings_persisted"
                ],
                "stim_observable_bitstrings_persisted": per_shot_summary[
                    "stim_observable_bitstrings_persisted"
                ],
            },
            "Keep the same per-shot schema for calibrated device exports.",
        ),
        gate(
            "C2",
            "Hardware-like model consumes detector bitstrings",
            bool(hardware_summary["hardware_like_leakage_model_used"])
            and bool(hardware_summary["detector_bitstrings_consumed"]),
            {
                "hardware_like_leakage_model_used": hardware_summary[
                    "hardware_like_leakage_model_used"
                ],
                "detector_bitstrings_consumed": hardware_summary[
                    "detector_bitstrings_consumed"
                ],
                "synthetic_flag_fixture_consumed": hardware_summary[
                    "synthetic_flag_fixture_consumed"
                ],
            },
            "Preserve detector-bitstring input when replacing the toy observation model.",
        ),
        gate(
            "C3",
            "Profile sweep and holdout split are present",
            int(hardware_summary["observation_profile_count"]) == 3
            and int(hardware_summary["profile_result_count"]) == 9
            and int(hardware_summary["holdout_profile_shots"]) == 864,
            {
                "observation_profile_count": hardware_summary["observation_profile_count"],
                "profile_result_count": hardware_summary["profile_result_count"],
                "total_profile_shots": hardware_summary["total_profile_shots"],
                "holdout_profile_shots": hardware_summary["holdout_profile_shots"],
            },
            "Retain model-selection/holdout separation for real calibration sweeps.",
        ),
        gate(
            "C4",
            "Calibrated flag data is available",
            calibrated_flag_data_used,
            {
                "calibrated_flag_data_used": calibrated_flag_data_used,
                "per_shot_real_hardware_or_calibrated_flag_events": per_shot_summary[
                    "real_hardware_or_calibrated_flag_events"
                ],
            },
            "Add calibrated leakage/erasure flag observations with a confusion matrix.",
        ),
        gate(
            "C5",
            "Real hardware traces are available",
            real_hardware_trace_used,
            {
                "real_hardware_trace_used": real_hardware_trace_used,
                "hardware_result_claimed": claims["hardware_result_claimed"],
            },
            "Run the same decoder interface on real or independently calibrated hardware traces.",
        ),
        gate(
            "C6",
            "Holdout improvement is observed",
            holdout_improvement_gate_passed,
            {
                "best_profile": hardware_summary["best_profile"],
                "best_profile_holdout_baseline_failures": hardware_summary[
                    "best_profile_holdout_baseline_failures"
                ],
                "best_profile_holdout_injected_failures": hardware_summary[
                    "best_profile_holdout_injected_failures"
                ],
                "best_profile_holdout_failure_delta": hardware_summary[
                    "best_profile_holdout_failure_delta"
                ],
            },
            "Show strictly fewer holdout logical failures under calibrated injection.",
        ),
        gate(
            "C7",
            "Holdout non-regression is preserved",
            holdout_nonregression_gate_passed,
            {
                "holdout_nonregression_gate_passed": holdout_nonregression_gate_passed,
                "best_profile_holdout_introduced_failures": hardware_summary[
                    "best_profile_holdout_introduced_failures"
                ],
            },
            "Maintain non-regression after replacing the model with calibrated data.",
        ),
        gate(
            "C8",
            "Stress profile does not introduce failures",
            stress_profile_no_introduced_failures,
            {
                "stress_profile": "stress_hardware_like_leakage",
                "stress_profile_injected_failures": stress_profile["injected_failures"],
                "stress_profile_introduced_failures": stress_profile[
                    "introduced_failures"
                ],
                "stress_profile_model_flag_events": stress_profile["model_flag_events"],
            },
            "Re-check this guardrail on real high-leakage slices.",
        ),
        gate(
            "C9",
            "No forbidden production or threshold claim is made",
            not any(
                bool(claims[key])
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
                "production_decoder_claimed": claims["production_decoder_claimed"],
                "threshold_claimed": claims["threshold_claimed"],
                "new_code_claimed": claims["new_code_claimed"],
                "hardware_result_claimed": claims["hardware_result_claimed"],
                "calibrated_device_claimed": claims["calibrated_device_claimed"],
                "quantum_advantage_claimed": claims["quantum_advantage_claimed"],
            },
            "Keep B2 as a negative-boundary result until C4-C6 pass on stronger data.",
        ),
    ]

    passed_gate_count = sum(1 for item in calibration_requirements if item["passed"])
    failed_gate_count = len(calibration_requirements) - passed_gate_count
    missing_calibration_gate_ids = [
        item["gate_id"] for item in calibration_requirements if not item["passed"]
    ]

    summary = {
        "source_challenge_count": hardware_summary["source_challenge_count"],
        "source_trace_count": per_shot_summary["total_shot_traces"],
        "observation_profile_count": hardware_summary["observation_profile_count"],
        "profile_result_count": hardware_summary["profile_result_count"],
        "total_profile_shots": hardware_summary["total_profile_shots"],
        "holdout_profile_shots": hardware_summary["holdout_profile_shots"],
        "best_profile": hardware_summary["best_profile"],
        "best_profile_model_flag_events": hardware_summary[
            "best_profile_model_flag_events"
        ],
        "stress_profile_model_flag_events": stress_profile["model_flag_events"],
        "best_profile_holdout_baseline_failures": hardware_summary[
            "best_profile_holdout_baseline_failures"
        ],
        "best_profile_holdout_injected_failures": hardware_summary[
            "best_profile_holdout_injected_failures"
        ],
        "best_profile_holdout_failure_delta": hardware_summary[
            "best_profile_holdout_failure_delta"
        ],
        "calibration_requirement_count": len(calibration_requirements),
        "passed_calibration_requirement_count": passed_gate_count,
        "failed_calibration_requirement_count": failed_gate_count,
        "missing_calibration_gate_ids": missing_calibration_gate_ids,
        "calibrated_flag_data_used": calibrated_flag_data_used,
        "real_hardware_trace_used": real_hardware_trace_used,
        "holdout_improvement_gate_passed": holdout_improvement_gate_passed,
        "holdout_nonregression_gate_passed": holdout_nonregression_gate_passed,
        "stress_profile_no_introduced_failures": stress_profile_no_introduced_failures,
        "posterior_route_demotion_recommended": posterior_route_demoted,
        "dem_route_demotion_recommended": dem_route_demoted,
        "hardware_route_demotion_recommended": hardware_route_demoted,
        "calibration_transfer_ready": False,
        "production_decoder_ready": False,
        "threshold_claim_supported": False,
    }

    report = {
        "benchmark_id": "B2",
        "problem_id": 22,
        "title": "B2 calibration transfer guardrail gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "status": STATUS,
        "method": METHOD,
        "model_status": MODEL_STATUS,
        "toolchain": (
            "Consumes the B2 per-shot trace packet, posterior injection gate, "
            "DEM-informed edge semantics gate, and hardware-like leakage gate; "
            "checks whether the model has enough calibration-transfer evidence "
            "to support production-decoder, threshold, or hardware claims."
        ),
        "sources": {
            "per_shot_trace_result": str(args.per_shot_trace_result),
            "posterior_injection_result": str(args.posterior_injection_result),
            "dem_edge_result": str(args.dem_edge_result),
            "hardware_like_result": str(args.hardware_like_result),
        },
        "summary": summary,
        "calibration_requirements": calibration_requirements,
        "claim_boundary": {
            "calibration_transfer_guardrail_built": True,
            "calibration_transfer_ready": False,
            "production_decoder_claimed": False,
            "threshold_claimed": False,
            "new_code_claimed": False,
            "hardware_result_claimed": False,
            "calibrated_device_claimed": False,
            "quantum_advantage_claimed": False,
            "what_is_supported": (
                "The current B2 pipeline has per-shot traces, detector-bitstring "
                "input, profile sweeps, holdout accounting, and non-regression "
                "under the best hardware-like model."
            ),
            "what_is_not_supported": (
                "The route has no calibrated flag data, no real hardware trace, "
                "and no holdout improvement, so it cannot support a production "
                "decoder, threshold, low-overhead QEC, or hardware claim."
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
    if summary["source_challenge_count"] != 3:
        errors.append("expected three B2 challenge rows")
    if summary["source_trace_count"] != 576:
        errors.append("expected 576 per-shot traces")
    if summary["observation_profile_count"] != 3:
        errors.append("expected three hardware-like observation profiles")
    if summary["profile_result_count"] != 9:
        errors.append("expected nine challenge/profile rows")
    if summary["total_profile_shots"] != 1728:
        errors.append("expected 1728 profile shots")
    if summary["holdout_profile_shots"] != 864:
        errors.append("expected 864 holdout profile shots")
    if summary["calibration_requirement_count"] != 9:
        errors.append("expected nine calibration-transfer requirements")
    if summary["passed_calibration_requirement_count"] != 6:
        errors.append("current guardrail should pass exactly six requirements")
    if summary["failed_calibration_requirement_count"] != 3:
        errors.append("current guardrail should fail exactly three requirements")
    if summary["missing_calibration_gate_ids"] != ["C4", "C5", "C6"]:
        errors.append("current missing calibration gates should be C4/C5/C6")
    if summary["calibrated_flag_data_used"] is not False:
        errors.append("calibrated flag data must remain absent")
    if summary["real_hardware_trace_used"] is not False:
        errors.append("real hardware traces must remain absent")
    if summary["holdout_improvement_gate_passed"] is not False:
        errors.append("holdout improvement must remain false")
    if summary["holdout_nonregression_gate_passed"] is not True:
        errors.append("holdout non-regression should remain true")
    if summary["stress_profile_no_introduced_failures"] is not True:
        errors.append("hardware-like stress profile should introduce no failures")
    for key in [
        "posterior_route_demotion_recommended",
        "dem_route_demotion_recommended",
        "hardware_route_demotion_recommended",
    ]:
        if summary[key] is not True:
            errors.append(f"{key} must remain true")
    if summary["calibration_transfer_ready"] is not False:
        errors.append("calibration transfer must not be ready")
    if summary["production_decoder_ready"] is not False:
        errors.append("production decoder must not be ready")
    if summary["threshold_claim_supported"] is not False:
        errors.append("threshold claim must not be supported")
    for key in [
        "production_decoder_claimed",
        "threshold_claimed",
        "new_code_claimed",
        "hardware_result_claimed",
        "calibrated_device_claimed",
        "quantum_advantage_claimed",
    ]:
        if claims.get(key) is not False:
            errors.append(f"{key} must remain False")
    if claims.get("calibration_transfer_guardrail_built") is not True:
        errors.append("claim boundary must disclose guardrail construction")
    if claims.get("calibration_transfer_ready") is not False:
        errors.append("claim boundary must keep calibration transfer false")
    return errors


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# B2 Calibration Transfer Guardrail Gate v0.1",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Summary",
        "",
        f"- Method: {report['method']}",
        f"- Model status: {report['model_status']}",
        f"- Source challenge count: {summary['source_challenge_count']}",
        f"- Source trace count: {summary['source_trace_count']}",
        f"- Observation profiles / profile rows: {summary['observation_profile_count']} / {summary['profile_result_count']}",
        f"- Total profile shots / holdout shots: {summary['total_profile_shots']} / {summary['holdout_profile_shots']}",
        f"- Best profile: {summary['best_profile']}",
        f"- Best-profile model flag events: {summary['best_profile_model_flag_events']}",
        f"- Stress-profile model flag events: {summary['stress_profile_model_flag_events']}",
        f"- Best-profile holdout baseline / injected / delta: {summary['best_profile_holdout_baseline_failures']} / {summary['best_profile_holdout_injected_failures']} / {summary['best_profile_holdout_failure_delta']}",
        f"- Calibration requirements passed / failed: {summary['passed_calibration_requirement_count']} / {summary['failed_calibration_requirement_count']}",
        f"- Missing calibration gate ids: {', '.join(summary['missing_calibration_gate_ids'])}",
        f"- Calibrated flag data used: {summary['calibrated_flag_data_used']}",
        f"- Real hardware trace used: {summary['real_hardware_trace_used']}",
        f"- Holdout improvement gate passed: {summary['holdout_improvement_gate_passed']}",
        f"- Holdout non-regression gate passed: {summary['holdout_nonregression_gate_passed']}",
        f"- Calibration transfer ready: {summary['calibration_transfer_ready']}",
        f"- Production decoder ready: {summary['production_decoder_ready']}",
        f"- Threshold claim supported: {summary['threshold_claim_supported']}",
        f"- Validation errors: {report['validation_errors']}",
        "",
        "## Calibration Requirements",
        "",
        "| gate | passed | label | missing to promote |",
        "|---|---:|---|---|",
    ]
    for item in report["calibration_requirements"]:
        lines.append(
            f"| {item['gate_id']} | {item['passed']} | {item['label']} | "
            f"{item['missing_to_promote']} |"
        )
    lines.extend(["", "## Claim Boundary", ""])
    for key, value in report["claim_boundary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            "The next B2 gate must replace the model-derived leakage observations",
            "with calibrated flag data or real hardware traces, then show holdout",
            "logical-failure improvement while preserving non-regression.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--per-shot-trace-result",
        type=Path,
        default=Path("results/B2_per_shot_decoder_trace_packet_v0.json"),
    )
    parser.add_argument(
        "--posterior-injection-result",
        type=Path,
        default=Path("results/B2_posterior_likelihood_decoder_injection_gate_v0.json"),
    )
    parser.add_argument(
        "--dem-edge-result",
        type=Path,
        default=Path("results/B2_dem_informed_detector_edge_semantics_gate_v0.json"),
    )
    parser.add_argument(
        "--hardware-like-result",
        type=Path,
        default=Path("results/B2_hardware_like_leakage_model_gate_v0.json"),
    )
    parser.add_argument("--last-updated", default="2026-06-30")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B2_calibration_transfer_guardrail_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B2_calibration_transfer_guardrail_gate.md"),
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
