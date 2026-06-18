#!/usr/bin/env python3
"""Posterior-weighted decoder-risk ledger for B2 heralded-erasure rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


METHOD = "b2_posterior_weighted_decoder_risk_ledger_v0"
STATUS = "posterior_weighted_decoder_risk_boundary_not_production_decoder"

RISK_BUDGETS = [
    {
        "name": "mild_decoder_penalty",
        "missed_leakage_weight": 0.25,
        "false_positive_weight": 0.10,
        "posterior_shortfall_weight": 1.0,
        "minimum_adjusted_reduction": 1.0,
    },
    {
        "name": "nominal_decoder_penalty",
        "missed_leakage_weight": 0.50,
        "false_positive_weight": 0.25,
        "posterior_shortfall_weight": 1.0,
        "minimum_adjusted_reduction": 1.0,
    },
    {
        "name": "conservative_decoder_penalty",
        "missed_leakage_weight": 0.75,
        "false_positive_weight": 0.50,
        "posterior_shortfall_weight": 1.0,
        "minimum_adjusted_reduction": 1.0,
    },
    {
        "name": "strict_decoder_penalty",
        "missed_leakage_weight": 1.00,
        "false_positive_weight": 0.50,
        "posterior_shortfall_weight": 1.5,
        "minimum_adjusted_reduction": 1.0,
    },
]


def safe_ratio(value: float | None, denominator: float | None) -> float:
    if value is None or denominator is None or denominator <= 0:
        return 0.0
    return max(0.0, float(value) / float(denominator))


def posterior_shortfall(row: dict[str, Any]) -> float:
    posterior = row.get("posterior_leakage_probability_given_flag")
    threshold = float(row.get("posterior_threshold", 0.0))
    if posterior is None or threshold <= 0:
        return 1.0
    return max(0.0, threshold - float(posterior)) / threshold


def adjusted_row(row: dict[str, Any], budget: dict[str, Any]) -> dict[str, Any]:
    missed_ratio = safe_ratio(
        row.get("missed_leakage_rate_per_tick"),
        row.get("max_missed_leakage_rate_per_tick"),
    )
    false_positive_ratio = safe_ratio(
        row.get("false_positive_rate_per_tick"),
        row.get("max_false_positive_rate_per_tick"),
    )
    shortfall = posterior_shortfall(row)
    risk_multiplier = (
        1.0
        + float(budget["missed_leakage_weight"]) * missed_ratio
        + float(budget["false_positive_weight"]) * false_positive_ratio
        + float(budget["posterior_shortfall_weight"]) * shortfall
    )
    candidate_volume = row.get("candidate_space_time_volume")
    baseline_volume = row.get("baseline_space_time_volume")
    adjusted_candidate_volume = (
        float(candidate_volume) * risk_multiplier if candidate_volume is not None else None
    )
    adjusted_reduction = (
        float(baseline_volume) / adjusted_candidate_volume
        if baseline_volume is not None and adjusted_candidate_volume not in (None, 0.0)
        else None
    )
    adjusted_survivor = bool(
        row.get("shot_conditioned_accept")
        and row.get("surviving_d5_d7_improvement")
        and adjusted_reduction is not None
        and adjusted_reduction > float(budget["minimum_adjusted_reduction"])
    )
    return {
        "risk_budget": budget["name"],
        "profile": row["profile"],
        "memory_basis": row["memory_basis"],
        "physical_error": row["physical_error"],
        "leakage_rate_per_tick": row["leakage_rate_per_tick"],
        "false_positive_rate_per_tick": row["false_positive_rate_per_tick"],
        "target_logical_error": row["target_logical_error"],
        "baseline_distance": row["baseline_distance"],
        "candidate_distance": row["candidate_distance"],
        "baseline_space_time_volume": row["baseline_space_time_volume"],
        "candidate_space_time_volume": row["candidate_space_time_volume"],
        "raw_volume_reduction_vs_baseline": row["volume_reduction_vs_baseline"],
        "posterior_leakage_probability_given_flag": row[
            "posterior_leakage_probability_given_flag"
        ],
        "posterior_threshold": row["posterior_threshold"],
        "missed_leakage_rate_per_tick": row["missed_leakage_rate_per_tick"],
        "max_missed_leakage_rate_per_tick": row["max_missed_leakage_rate_per_tick"],
        "max_false_positive_rate_per_tick": row["max_false_positive_rate_per_tick"],
        "missed_leakage_ratio": missed_ratio,
        "false_positive_ratio": false_positive_ratio,
        "posterior_shortfall_ratio": shortfall,
        "decoder_risk_multiplier": risk_multiplier,
        "decoder_adjusted_candidate_space_time_volume": adjusted_candidate_volume,
        "decoder_adjusted_volume_reduction": adjusted_reduction,
        "shot_conditioned_accept": row["shot_conditioned_accept"],
        "raw_surviving_d5_d7_improvement": row["surviving_d5_d7_improvement"],
        "decoder_adjusted_surviving_d5_d7_improvement": adjusted_survivor,
    }


def summarize(rows: list[dict[str, Any]], source_survivor_count: int) -> dict[str, Any]:
    by_budget: dict[str, dict[str, Any]] = {}
    for budget in RISK_BUDGETS:
        subset = [row for row in rows if row["risk_budget"] == budget["name"]]
        survivors = [
            row for row in subset if row["decoder_adjusted_surviving_d5_d7_improvement"]
        ]
        reductions = [
            row["decoder_adjusted_volume_reduction"]
            for row in survivors
            if row["decoder_adjusted_volume_reduction"] is not None
        ]
        by_profile = {}
        for profile in sorted({row["profile"] for row in subset}):
            profile_rows = [row for row in subset if row["profile"] == profile]
            profile_survivors = [
                row
                for row in profile_rows
                if row["decoder_adjusted_surviving_d5_d7_improvement"]
            ]
            by_profile[profile] = {
                "evaluated_rows": len(profile_rows),
                "adjusted_surviving_d5_d7_rows": len(profile_survivors),
            }
        by_budget[budget["name"]] = {
            "evaluated_rows": len(subset),
            "source_raw_surviving_d5_d7_rows": source_survivor_count,
            "adjusted_surviving_d5_d7_rows": len(survivors),
            "survivor_loss_vs_source": source_survivor_count - len(survivors),
            "profiles_with_adjusted_survivors": sum(
                1 for row in by_profile.values() if row["adjusted_surviving_d5_d7_rows"] > 0
            ),
            "strict_high_purity_adjusted_survivors": by_profile.get(
                "strict_high_purity_0p95", {}
            ).get("adjusted_surviving_d5_d7_rows", 0),
            "robust_all_profile_adjusted_survival": all(
                row["adjusted_surviving_d5_d7_rows"] > 0 for row in by_profile.values()
            ),
            "max_decoder_adjusted_reduction": max(reductions) if reductions else None,
            "mean_decoder_adjusted_reduction": (
                sum(reductions) / len(reductions) if reductions else None
            ),
            "by_profile": by_profile,
        }
    strict = by_budget["strict_decoder_penalty"]
    conservative = by_budget["conservative_decoder_penalty"]
    return {
        "risk_budget_count": len(RISK_BUDGETS),
        "evaluated_budget_profile_rows": len(rows),
        "source_raw_surviving_d5_d7_rows": source_survivor_count,
        "mild_adjusted_surviving_d5_d7_rows": by_budget["mild_decoder_penalty"][
            "adjusted_surviving_d5_d7_rows"
        ],
        "nominal_adjusted_surviving_d5_d7_rows": by_budget["nominal_decoder_penalty"][
            "adjusted_surviving_d5_d7_rows"
        ],
        "conservative_adjusted_surviving_d5_d7_rows": conservative[
            "adjusted_surviving_d5_d7_rows"
        ],
        "strict_adjusted_surviving_d5_d7_rows": strict[
            "adjusted_surviving_d5_d7_rows"
        ],
        "strict_high_purity_adjusted_survivors": strict[
            "strict_high_purity_adjusted_survivors"
        ],
        "robust_all_profile_adjusted_survival": all(
            row["robust_all_profile_adjusted_survival"] for row in by_budget.values()
        ),
        "conservative_max_decoder_adjusted_reduction": conservative[
            "max_decoder_adjusted_reduction"
        ],
        "strict_max_decoder_adjusted_reduction": strict["max_decoder_adjusted_reduction"],
        "by_budget": by_budget,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    source_payload = json.loads(args.source_result.read_text(encoding="utf-8"))
    source_evaluations = source_payload["evaluations"]
    source_survivors = [
        row for row in source_evaluations if row["surviving_d5_d7_improvement"]
    ]
    adjusted_rows = [
        adjusted_row(row, budget)
        for budget in RISK_BUDGETS
        for row in source_evaluations
    ]
    summary = summarize(adjusted_rows, source_survivor_count=len(source_survivors))
    adjusted_survivor_rows = [
        row for row in adjusted_rows if row["decoder_adjusted_surviving_d5_d7_improvement"]
    ]
    report = {
        "benchmark_id": "B2",
        "problem_id": 22,
        "title": "B2 posterior-weighted decoder-risk ledger",
        "version": "0.1",
        "last_updated": args.last_updated,
        "status": STATUS,
        "method": METHOD,
        "model_status": "posterior_weighted_risk_ledger_not_circuit_level_decoder",
        "toolchain": (
            "Post-processes T-B2-006 posterior-calibrated profile rows with explicit "
            "missed-leakage, false-positive, and posterior-shortfall risk multipliers."
        ),
        "source_result": str(args.source_result),
        "source_method": source_payload["method"],
        "source_status": source_payload["status"],
        "summary": summary,
        "risk_budgets": RISK_BUDGETS,
        "claim_boundary": {
            "new_code_claimed": False,
            "threshold_claimed": False,
            "calibrated_device_claimed": False,
            "full_physical_leakage_decoder_claimed": False,
            "production_decoder_claimed": False,
            "circuit_level_decoder_claimed": False,
            "hardware_result_claimed": False,
            "shot_conditioned_erasure_decoder_claimed": False,
            "posterior_weighted_decoder_risk_model_performed": True,
            "reduced_rounds_used": False,
            "distance_3_candidate_used": False,
            "what_is_supported": (
                "Posterior-calibrated rows can be re-costed with explicit decoder-risk "
                "multipliers; the surviving signal shrinks under conservative and strict "
                "risk budgets and still lacks all-profile robustness."
            ),
            "what_is_not_supported": (
                "This is not a circuit-level shot-conditioned decoder, production decoder, "
                "hardware-calibrated leakage model, threshold result, new code, or hardware QEC result."
            ),
        },
        "adjusted_survivor_rows": adjusted_survivor_rows,
    }
    report["validation_errors"] = validate(report)
    return report


def validate(report: dict[str, Any]) -> list[str]:
    errors = []
    summary = report["summary"]
    claims = report["claim_boundary"]
    if report.get("source_method") != "b2_shot_conditioned_erasure_decoder_boundary_v0":
        errors.append("source must be T-B2-006 shot-conditioned boundary")
    if summary["risk_budget_count"] != 4:
        errors.append("expected four decoder risk budgets")
    if summary["evaluated_budget_profile_rows"] != 4608:
        errors.append("expected 4608 budget/profile rows")
    if summary["source_raw_surviving_d5_d7_rows"] != 6:
        errors.append("expected six source raw profile-survivor rows")
    if summary["conservative_adjusted_surviving_d5_d7_rows"] >= summary[
        "source_raw_surviving_d5_d7_rows"
    ]:
        errors.append("conservative decoder-risk ledger should shrink raw survivor count")
    if summary["strict_high_purity_adjusted_survivors"] != 0:
        errors.append("strict high-purity profile must still have zero adjusted survivors")
    if summary["robust_all_profile_adjusted_survival"] is not False:
        errors.append("must not claim robust all-profile adjusted survival")
    if claims.get("posterior_weighted_decoder_risk_model_performed") is not True:
        errors.append("must disclose posterior-weighted decoder-risk modeling")
    for key in [
        "new_code_claimed",
        "threshold_claimed",
        "calibrated_device_claimed",
        "full_physical_leakage_decoder_claimed",
        "production_decoder_claimed",
        "circuit_level_decoder_claimed",
        "hardware_result_claimed",
        "shot_conditioned_erasure_decoder_claimed",
        "reduced_rounds_used",
        "distance_3_candidate_used",
    ]:
        if claims.get(key) is not False:
            errors.append(f"{key} must remain False")
    return errors


def format_optional_float(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# B2 Posterior-Weighted Decoder-Risk Ledger v0.1",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Summary",
        "",
        f"- Method: {report['method']}",
        f"- Model status: {report['model_status']}",
        f"- Source result: {report['source_result']}",
        f"- Risk budgets: {summary['risk_budget_count']}",
        f"- Evaluated budget/profile rows: {summary['evaluated_budget_profile_rows']}",
        f"- Source raw surviving d=5/d=7 profile rows: {summary['source_raw_surviving_d5_d7_rows']}",
        f"- Mild adjusted survivors: {summary['mild_adjusted_surviving_d5_d7_rows']}",
        f"- Nominal adjusted survivors: {summary['nominal_adjusted_surviving_d5_d7_rows']}",
        f"- Conservative adjusted survivors: {summary['conservative_adjusted_surviving_d5_d7_rows']}",
        f"- Strict adjusted survivors: {summary['strict_adjusted_surviving_d5_d7_rows']}",
        f"- Strict high-purity adjusted survivors: {summary['strict_high_purity_adjusted_survivors']}",
        f"- Robust all-profile adjusted survival: {summary['robust_all_profile_adjusted_survival']}",
        f"- Validation errors: {report['validation_errors']}",
        "",
        "## Decoder-Risk Budgets",
        "",
        "| budget | adjusted survivors | survivor loss | profiles with survivors | strict high-purity survivors | max adjusted reduction | mean adjusted reduction | robust all-profile |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for budget_name, row in summary["by_budget"].items():
        lines.append(
            f"| {budget_name} | {row['adjusted_surviving_d5_d7_rows']} | "
            f"{row['survivor_loss_vs_source']} | {row['profiles_with_adjusted_survivors']} | "
            f"{row['strict_high_purity_adjusted_survivors']} | "
            f"{format_optional_float(row['max_decoder_adjusted_reduction'])} | "
            f"{format_optional_float(row['mean_decoder_adjusted_reduction'])} | "
            f"{row['robust_all_profile_adjusted_survival']} |"
        )
    survivors = [
        row
        for row in report["adjusted_survivor_rows"]
    ]
    survivors.sort(
        key=lambda row: (
            row["risk_budget"],
            row["profile"],
            -(row["decoder_adjusted_volume_reduction"] or 0.0),
        )
    )
    lines.extend(
        [
            "",
            "## Adjusted Surviving Rows",
            "",
            "| budget | profile | basis | p | leakage/tick | fp/tick | target | d | posterior | risk x | adjusted reduction |",
            "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in survivors:
        lines.append(
            f"| {row['risk_budget']} | {row['profile']} | {row['memory_basis']} | "
            f"{row['physical_error']:.4g} | {row['leakage_rate_per_tick']:.4g} | "
            f"{row['false_positive_rate_per_tick']:.4g} | {row['target_logical_error']:.4g} | "
            f"{row['candidate_distance']} | "
            f"{format_optional_float(row['posterior_leakage_probability_given_flag'])} | "
            f"{row['decoder_risk_multiplier']:.3f} | "
            f"{format_optional_float(row['decoder_adjusted_volume_reduction'])} |"
        )
    if not survivors:
        lines.append("| n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |")
    lines.extend(["", "## Claim Boundary", ""])
    for key, value in report["claim_boundary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            "The ledger keeps a small number of adjusted survivors under some risk budgets,",
            "but strict high-purity and all-profile robustness still fail. The next B2 gate",
            "must either implement a real circuit-level shot-conditioned decoder with these",
            "posterior weights as decoder inputs, or demote the heralded-erasure route until",
            "calibrated leakage and flag data support it.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-result",
        type=Path,
        default=Path("results/B2_shot_conditioned_erasure_decoder_boundary_v0.json"),
    )
    parser.add_argument("--last-updated", default="2026-06-18")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B2_posterior_weighted_decoder_risk_ledger_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B2_posterior_weighted_decoder_risk_ledger.md"),
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
