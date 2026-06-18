#!/usr/bin/env python3
"""Stress heralded-erasure B2 rows under flag false positives."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from b2_stim_heralded_erasure_stress import (
    best_for_target,
    metric_value,
    parse_float_list,
    parse_int_list,
    parse_str_list,
    run_config,
)


METHOD = "b2_heralded_erasure_false_positive_stress_v0"
STATUS = "heralded_erasure_false_positive_boundary_not_shot_conditioned_decoder"


def overhead_for_false_positive(
    base_flag_overhead: float,
    leakage_rate: float,
    false_positive_rate: float,
    false_positive_overhead_scale: float,
) -> float:
    if leakage_rate <= 0:
        return base_flag_overhead
    relative_extra_flags = false_positive_rate / leakage_rate
    return base_flag_overhead * (1.0 + false_positive_overhead_scale * relative_extra_flags)


def compare_targets_with_false_positives(
    rows: list[dict[str, Any]],
    targets: list[float],
    criterion: str,
    base_flag_overhead: float,
    false_positive_overhead_scale: float,
) -> list[dict[str, Any]]:
    bases = sorted({row["memory_basis"] for row in rows})
    physical_errors = sorted({float(row["physical_error"]) for row in rows})
    leakage_rates = sorted({float(row["leakage_rate_per_tick"]) for row in rows})
    false_positive_rates = sorted({float(row["false_positive_rate_per_tick"]) for row in rows})
    comparisons = []
    for basis in bases:
        for physical_error in physical_errors:
            for leakage_rate in leakage_rates:
                for false_positive_rate in false_positive_rates:
                    flag_overhead = overhead_for_false_positive(
                        base_flag_overhead=base_flag_overhead,
                        leakage_rate=leakage_rate,
                        false_positive_rate=false_positive_rate,
                        false_positive_overhead_scale=false_positive_overhead_scale,
                    )
                    for target in targets:
                        baseline = best_for_target(
                            rows,
                            mode="unheralded_depolarizing_leakage_proxy",
                            basis=basis,
                            physical_error=physical_error,
                            leakage_rate=leakage_rate,
                            target=target,
                            criterion=criterion,
                            volume_overhead=1.0,
                        )
                        candidate_rows = [
                            row
                            for row in rows
                            if row["mode"] == "heralded_erasure_proxy_with_false_positive_flags"
                            and row["memory_basis"] == basis
                            and float(row["physical_error"]) == physical_error
                            and float(row["leakage_rate_per_tick"]) == leakage_rate
                            and float(row["false_positive_rate_per_tick"]) == false_positive_rate
                            and metric_value(row, criterion) <= target
                        ]
                        candidate = None
                        if candidate_rows:
                            candidate = min(
                                (
                                    {
                                        **row,
                                        "overhead_adjusted_space_time_volume": (
                                            row["space_time_volume"] * flag_overhead
                                        ),
                                    }
                                    for row in candidate_rows
                                ),
                                key=lambda row: (
                                    row["overhead_adjusted_space_time_volume"],
                                    row["distance"],
                                    metric_value(row, criterion),
                                ),
                            )
                        baseline_volume = baseline["space_time_volume"] if baseline else None
                        candidate_volume = (
                            candidate["overhead_adjusted_space_time_volume"] if candidate else None
                        )
                        reduction = (
                            baseline_volume / candidate_volume
                            if baseline_volume is not None and candidate_volume is not None
                            else None
                        )
                        comparisons.append(
                            {
                                "memory_basis": basis,
                                "physical_error": physical_error,
                                "leakage_rate_per_tick": leakage_rate,
                                "false_positive_rate_per_tick": false_positive_rate,
                                "effective_candidate_erasure_rate_per_tick": leakage_rate + false_positive_rate,
                                "target_logical_error": target,
                                "criterion": criterion,
                                "baseline_met": baseline is not None,
                                "baseline_distance": baseline["distance"] if baseline else None,
                                "baseline_metric_value": metric_value(baseline, criterion) if baseline else None,
                                "baseline_space_time_volume": baseline_volume,
                                "candidate_met": candidate is not None,
                                "candidate_distance": candidate["distance"] if candidate else None,
                                "candidate_metric_value": metric_value(candidate, criterion) if candidate else None,
                                "candidate_raw_space_time_volume": (
                                    candidate["space_time_volume"] if candidate else None
                                ),
                                "candidate_space_time_volume": candidate_volume,
                                "flag_overhead": flag_overhead,
                                "volume_reduction_vs_baseline": reduction,
                                "improved_volume": bool(reduction is not None and reduction > 1.0),
                                "candidate_only_meets_target": candidate is not None and baseline is None,
                                "candidate_distance_5_or_7": (
                                    candidate["distance"] in {5, 7} if candidate else False
                                ),
                            }
                        )
    return comparisons


def summarize(rows: list[dict[str, Any]], comparisons: list[dict[str, Any]]) -> dict[str, Any]:
    improved = [row for row in comparisons if row["improved_volume"]]
    fp_positive = [row for row in improved if row["false_positive_rate_per_tick"] > 0.0]
    fp_by_rate = {}
    for rate in sorted({row["false_positive_rate_per_tick"] for row in comparisons}):
        subset = [row for row in comparisons if row["false_positive_rate_per_tick"] == rate]
        improved_subset = [row for row in subset if row["improved_volume"]]
        reductions = [row["volume_reduction_vs_baseline"] for row in improved_subset]
        fp_by_rate[f"{rate:g}"] = {
            "target_comparisons": len(subset),
            "candidate_met_count": sum(1 for row in subset if row["candidate_met"]),
            "improved_volume_count": len(improved_subset),
            "distance_5_7_improved_count": sum(
                1 for row in improved_subset if row["candidate_distance_5_or_7"]
            ),
            "max_volume_reduction": max(reductions) if reductions else None,
            "mean_volume_reduction_on_improved": (
                sum(reductions) / len(reductions) if reductions else None
            ),
        }
    return {
        "configuration_count": len(rows),
        "total_shots": sum(row["shots"] for row in rows),
        "target_comparisons": len(comparisons),
        "false_positive_rates_per_tick": sorted(
            {float(row["false_positive_rate_per_tick"]) for row in rows}
        ),
        "candidate_met_count": sum(1 for row in comparisons if row["candidate_met"]),
        "improved_volume_count": len(improved),
        "false_positive_positive_improved_volume_count": len(fp_positive),
        "distance_5_7_improved_count": sum(1 for row in improved if row["candidate_distance_5_or_7"]),
        "false_positive_positive_d5_d7_improved_count": sum(
            1 for row in fp_positive if row["candidate_distance_5_or_7"]
        ),
        "max_volume_reduction": (
            max(row["volume_reduction_vs_baseline"] for row in improved) if improved else None
        ),
        "mean_volume_reduction_on_improved": (
            sum(row["volume_reduction_vs_baseline"] for row in improved) / len(improved)
            if improved
            else None
        ),
        "by_false_positive_rate": fp_by_rate,
        "distances": sorted({row["distance"] for row in rows}),
        "physical_errors": sorted({float(row["physical_error"]) for row in rows}),
        "leakage_rates_per_tick": sorted({float(row["leakage_rate_per_tick"]) for row in rows}),
        "memory_bases": sorted({row["memory_basis"] for row in rows}),
    }


def validate(report: dict[str, Any]) -> list[str]:
    errors = []
    summary = report["summary"]
    claims = report["claim_boundary"]
    if summary["configuration_count"] <= 0:
        errors.append("configuration_count must be positive")
    if not any(rate > 0.0 for rate in summary["false_positive_rates_per_tick"]):
        errors.append("must include at least one positive false-positive rate")
    if summary["false_positive_positive_improved_volume_count"] <= 0:
        errors.append("expected at least one improved row to survive positive false-positive stress")
    if summary["false_positive_positive_d5_d7_improved_count"] <= 0:
        errors.append("expected at least one d=5/d=7 improvement to survive positive false-positive stress")
    for key in [
        "new_code_claimed",
        "threshold_claimed",
        "calibrated_device_claimed",
        "full_physical_leakage_decoder_claimed",
        "shot_conditioned_erasure_decoder_claimed",
    ]:
        if claims.get(key) is not False:
            errors.append(f"{key} must remain False")
    if claims.get("false_positive_overhead_stress_performed") is not True:
        errors.append("false-positive overhead stress must be disclosed")
    if claims.get("reduced_rounds_used") is not False:
        errors.append("must not use reduced rounds")
    if claims.get("distance_3_candidate_used") is not False:
        errors.append("must not use distance-3 candidates")
    return errors


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    rows = []
    config_index = 0
    for basis in parse_str_list(args.bases):
        for physical_error in parse_float_list(args.physical_errors):
            for leakage_rate in parse_float_list(args.leakage_rates):
                for distance in parse_int_list(args.distances):
                    config_index += 1
                    baseline = run_config(
                        mode="unheralded_depolarizing_leakage_proxy",
                        distance=distance,
                        physical_error=physical_error,
                        leakage_rate=leakage_rate,
                        basis=basis,
                        shots=args.shots,
                        seed=args.seed + config_index,
                    )
                    baseline["false_positive_rate_per_tick"] = 0.0
                    baseline["effective_candidate_erasure_rate_per_tick"] = None
                    rows.append(baseline)
                    for false_positive_rate in parse_float_list(args.false_positive_rates):
                        config_index += 1
                        candidate = run_config(
                            mode="heralded_erasure_proxy",
                            distance=distance,
                            physical_error=physical_error,
                            leakage_rate=leakage_rate + false_positive_rate,
                            basis=basis,
                            shots=args.shots,
                            seed=args.seed + config_index,
                        )
                        candidate["mode"] = "heralded_erasure_proxy_with_false_positive_flags"
                        candidate["leakage_rate_per_tick"] = leakage_rate
                        candidate["false_positive_rate_per_tick"] = false_positive_rate
                        candidate["effective_candidate_erasure_rate_per_tick"] = (
                            leakage_rate + false_positive_rate
                        )
                        rows.append(candidate)
    targets = parse_float_list(args.targets)
    comparisons = compare_targets_with_false_positives(
        rows=rows,
        targets=targets,
        criterion=args.criterion,
        base_flag_overhead=args.base_flag_overhead,
        false_positive_overhead_scale=args.false_positive_overhead_scale,
    )
    report = {
        "benchmark_id": "B2",
        "problem_id": 22,
        "title": "B2 heralded-erasure false-positive overhead stress",
        "version": "0.1",
        "last_updated": args.last_updated,
        "status": STATUS,
        "method": METHOD,
        "model_status": (
            "stim_generated_surface_code_with_tick_level_heralded_erasure_false_positive_stress"
        ),
        "toolchain": (
            "Stim HERALDED_ERASE / DEPOLARIZE1 plus PyMatching detector-error-model decoder; "
            "candidate erasure rate is leakage_rate + false_positive_rate"
        ),
        "criterion": args.criterion,
        "base_flag_overhead": args.base_flag_overhead,
        "false_positive_overhead_scale": args.false_positive_overhead_scale,
        "shots_per_configuration": args.shots,
        "parameters": {
            "distances": parse_int_list(args.distances),
            "physical_errors": parse_float_list(args.physical_errors),
            "leakage_rates_per_tick": parse_float_list(args.leakage_rates),
            "false_positive_rates_per_tick": parse_float_list(args.false_positive_rates),
            "memory_bases": parse_str_list(args.bases),
            "targets": targets,
            "seed": args.seed,
        },
        "summary": summarize(rows, comparisons),
        "claim_boundary": {
            "new_code_claimed": False,
            "threshold_claimed": False,
            "calibrated_device_claimed": False,
            "full_physical_leakage_decoder_claimed": False,
            "shot_conditioned_erasure_decoder_claimed": False,
            "false_positive_overhead_stress_performed": True,
            "circuit_derived_stim_evidence": True,
            "reduced_rounds_used": False,
            "distance_3_candidate_used": False,
            "what_is_supported": (
                "Under a Stim generated rotated-surface-code memory circuit, some "
                "heralded-erasure target-volume improvements survive positive false-positive "
                "flag rates after explicit overhead penalties."
            ),
            "what_is_not_supported": (
                "This is not a full shot-conditioned erasure decoder, calibrated leakage model, "
                "threshold estimate, new code, hardware result, or production QEC design."
            ),
        },
        "results": rows,
        "comparisons": comparisons,
    }
    report["validation_errors"] = validate(report)
    return report


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    improved = [row for row in report["comparisons"] if row["improved_volume"]]
    improved.sort(
        key=lambda row: (
            row["false_positive_rate_per_tick"],
            -(row["volume_reduction_vs_baseline"] or 0.0),
            row["physical_error"],
            row["leakage_rate_per_tick"],
            row["target_logical_error"],
            row["memory_basis"],
        )
    )
    lines = [
        "# B2 Heralded-Erasure False-Positive Stress v0.1",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Summary",
        "",
        f"- Method: {report['method']}",
        f"- Model status: {report['model_status']}",
        f"- Toolchain: {report['toolchain']}",
        f"- Configurations: {summary['configuration_count']}",
        f"- Total shots: {summary['total_shots']}",
        f"- Target comparisons: {summary['target_comparisons']}",
        f"- False-positive rates per tick: {summary['false_positive_rates_per_tick']}",
        f"- Candidate met count: {summary['candidate_met_count']}",
        f"- Improved target-volume rows: {summary['improved_volume_count']}",
        f"- Improved rows at positive false-positive rates: {summary['false_positive_positive_improved_volume_count']}",
        f"- Positive false-positive d=5/d=7 improved rows: {summary['false_positive_positive_d5_d7_improved_count']}",
        f"- Max volume reduction after overhead: {summary['max_volume_reduction']}",
        f"- Mean volume reduction on improved rows: {summary['mean_volume_reduction_on_improved']}",
        f"- Validation errors: {report['validation_errors']}",
        "",
        "## False-Positive Rate Breakdown",
        "",
        "| false-positive/tick | comparisons | candidate met | improved rows | d=5/7 improved | max reduction | mean reduction |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for rate, row in summary["by_false_positive_rate"].items():
        max_reduction = row["max_volume_reduction"]
        mean_reduction = row["mean_volume_reduction_on_improved"]
        lines.append(
            f"| {rate} | {row['target_comparisons']} | {row['candidate_met_count']} | "
            f"{row['improved_volume_count']} | {row['distance_5_7_improved_count']} | "
            f"{max_reduction:.3f}x | {mean_reduction:.3f}x |"
            if max_reduction is not None and mean_reduction is not None
            else (
                f"| {rate} | {row['target_comparisons']} | {row['candidate_met_count']} | "
                f"{row['improved_volume_count']} | {row['distance_5_7_improved_count']} | n/a | n/a |"
            )
        )
    lines.extend(
        [
            "",
            "## Improved Target-Volume Rows",
            "",
            "| fp/tick | basis | p | leakage/tick | effective erasure/tick | target | baseline d | candidate d | baseline volume | candidate volume | reduction |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in improved[:30]:
        lines.append(
            f"| {row['false_positive_rate_per_tick']:.4g} | {row['memory_basis']} | "
            f"{row['physical_error']:.4g} | {row['leakage_rate_per_tick']:.4g} | "
            f"{row['effective_candidate_erasure_rate_per_tick']:.4g} | "
            f"{row['target_logical_error']:.4g} | {row['baseline_distance']} | "
            f"{row['candidate_distance']} | {row['baseline_space_time_volume']:.2f} | "
            f"{row['candidate_space_time_volume']:.2f} | "
            f"{row['volume_reduction_vs_baseline']:.3f}x |"
        )
    if not improved:
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
    lines.extend(["", "## Claim Boundary", ""])
    for key, value in report["claim_boundary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            "This artifact is a stronger false-positive stress boundary, not a full",
            "shot-conditioned erasure decoder. The next B2 gate should either add real",
            "shot-conditioned decoding or demote the heralded-erasure route if surviving",
            "d=5/d=7 rows disappear under calibrated leakage and flag-noise data.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distances", default="5,7,9")
    parser.add_argument("--physical-errors", default="0.001,0.003,0.005")
    parser.add_argument("--leakage-rates", default="0.003,0.005,0.01")
    parser.add_argument("--false-positive-rates", default="0,0.001,0.003,0.005")
    parser.add_argument("--bases", default="x,z")
    parser.add_argument("--targets", default="0.1,0.05,0.02,0.01")
    parser.add_argument(
        "--criterion",
        choices=["wilson_95_high", "observed_logical_error_rate"],
        default="wilson_95_high",
    )
    parser.add_argument("--base-flag-overhead", type=float, default=1.15)
    parser.add_argument("--false-positive-overhead-scale", type=float, default=0.25)
    parser.add_argument("--shots", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=220705)
    parser.add_argument("--last-updated", default="2026-06-18")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B2_heralded_erasure_false_positive_stress_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B2_heralded_erasure_false_positive_stress.md"),
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
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
