#!/usr/bin/env python3
"""Evaluate frozen P057 AMR forecasting denominators on a 2023 holdout.

This packet compares last observation carried forward with a country-specific
logit-linear time trend.  It evaluates denominators only: no candidate model,
clinical action, prescribing recommendation, or frontier-solution claim is made.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P057_AMR_baseline_eval_v1.json"
DEFAULT_SNAPSHOT = ROOT / "results/P057_P058_source_snapshot_v1.json"
DEFAULT_PREFLIGHT = ROOT / "results/P057_P058_data_preflight_v1.json"
DEFAULT_RESULT = ROOT / "results/P057_AMR_baseline_eval_v1.json"
DEFAULT_REPORT = ROOT / "research/P057_AMR_baseline_eval_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/P057_AMR_baseline_discussion_v1.md"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def rounded(value: float, digits: int = 10) -> float:
    return round(float(value), digits)


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def inverse_logit(value: float) -> float:
    if value >= 0:
        decay = math.exp(-value)
        return 1.0 / (1.0 + decay)
    growth = math.exp(value)
    return growth / (1.0 + growth)


def fit_predictions(
    training: list[tuple[int, float]], holdout_year: int, epsilon: float
) -> dict[str, float]:
    ordered = sorted(training)
    if len(ordered) < 3:
        raise ValueError("country-logit baseline requires at least three training rows")
    locf = ordered[-1][1]
    years = [float(year) for year, _ in ordered]
    logits = []
    for _, value in ordered:
        probability = min(1.0 - epsilon, max(epsilon, value / 100.0))
        logits.append(math.log(probability / (1.0 - probability)))
    center = statistics.fmean(years)
    logit_center = statistics.fmean(logits)
    denominator = sum((year - center) ** 2 for year in years)
    if denominator == 0.0:
        raise ValueError("training years do not vary")
    slope = sum(
        (year - center) * (value - logit_center)
        for year, value in zip(years, logits, strict=True)
    ) / denominator
    predicted_logit = logit_center + slope * (holdout_year - center)
    country_logit = 100.0 * inverse_logit(predicted_logit)
    return {
        "locf": locf,
        "country_logit": country_logit,
        "country_logit_slope_per_year": slope,
    }


def run_synthetic_controls(epsilon: float) -> dict[str, Any]:
    years = [2016, 2018, 2020, 2022]
    exact_training = []
    for year in years:
        latent = -0.7 + 0.12 * (year - 2016)
        exact_training.append((year, 100.0 * inverse_logit(latent)))
    exact_prediction = 100.0 * inverse_logit(-0.7 + 0.12 * (2023 - 2016))
    recovered = fit_predictions(exact_training, 2023, epsilon)["country_logit"]
    constant_training = [(2016, 42.0), (2018, 42.0), (2020, 42.0), (2022, 42.0)]
    constant = fit_predictions(constant_training, 2023, epsilon)
    return {
        "positive_logit_linear": {
            "expected_percent": rounded(exact_prediction, 12),
            "observed_percent": rounded(recovered, 12),
            "absolute_error_pp": rounded(abs(recovered - exact_prediction), 14),
            "passed": abs(recovered - exact_prediction) <= 1e-10,
        },
        "negative_constant": {
            "locf_percent": rounded(constant["locf"], 12),
            "country_logit_percent": rounded(constant["country_logit"], 12),
            "absolute_difference_pp": rounded(
                abs(constant["country_logit"] - constant["locf"]), 14
            ),
            "passed": abs(constant["country_logit"] - constant["locf"]) <= 1e-10,
        },
    }


def build_snapshot_index(
    snapshot: dict[str, Any],
) -> dict[tuple[str, str], dict[int, float]]:
    index: dict[tuple[str, str], dict[int, float]] = {}
    for row in snapshot["p057"]["records"]:
        key = (str(row["indicator_code"]), str(row["m49"]))
        year = int(row["year"])
        values = index.setdefault(key, {})
        if year in values:
            raise ValueError(f"duplicate source row for {key} year {year}")
        values[year] = float(row["value_percent"])
    return index


def build_evaluation_rows(
    benchmark: dict[str, Any],
    snapshot: dict[str, Any],
    preflight: dict[str, Any],
) -> tuple[list[dict[str, Any]], bool]:
    contract = benchmark["data_contract"]
    training_years = {int(year) for year in contract["training_years"]}
    holdout_year = int(contract["holdout_year"])
    allowed_codes = set(contract["indicator_codes"])
    epsilon = float(
        benchmark["baselines"]["country_specific_logit_time_trend"][
            "probability_clip_epsilon"
        ]
    )
    minimum_training = int(benchmark["eligibility"]["minimum_observed_training_years"])
    source_index = build_snapshot_index(snapshot)
    matrix_matches_snapshot = True
    rows: list[dict[str, Any]] = []
    for matrix_row in preflight["p057"]["coverage_matrix"]:
        code = str(matrix_row["indicator_code"])
        if code not in allowed_codes:
            continue
        m49 = str(matrix_row["m49"])
        source_values = source_index.get((code, m49), {})
        matrix_values = {
            int(year): float(value)
            for year, value in matrix_row["values_percent"].items()
            if value is not None
        }
        if source_values != matrix_values:
            matrix_matches_snapshot = False
        training = sorted(
            (year, value)
            for year, value in source_values.items()
            if year in training_years
        )
        if holdout_year not in source_values or len(training) < minimum_training:
            continue
        predictions = fit_predictions(training, holdout_year, epsilon)
        observed = source_values[holdout_year]
        row = {
            "indicator_code": code,
            "m49": m49,
            "iso3": str(matrix_row["iso3"]),
            "entity": str(matrix_row["entity"]),
            "completeness_stratum": str(matrix_row["completeness_stratum"]),
            "training_years": [year for year, _ in training],
            "training_values_percent": [rounded(value) for _, value in training],
            "holdout_year": holdout_year,
            "observed_percent": rounded(observed),
            "predictions_percent": {
                "locf": rounded(predictions["locf"]),
                "country_logit": rounded(predictions["country_logit"]),
            },
            "errors_percent": {
                "locf_signed": rounded(predictions["locf"] - observed),
                "locf_absolute": rounded(abs(predictions["locf"] - observed)),
                "country_logit_signed": rounded(
                    predictions["country_logit"] - observed
                ),
                "country_logit_absolute": rounded(
                    abs(predictions["country_logit"] - observed)
                ),
            },
            "country_logit_slope_per_year": rounded(
                predictions["country_logit_slope_per_year"], 12
            ),
        }
        rows.append(row)
    rows.sort(key=lambda row: (row["indicator_code"], row["m49"]))
    return rows, matrix_matches_snapshot


def metric_summary(rows: list[dict[str, Any]], baseline: str) -> dict[str, Any]:
    signed = [float(row["errors_percent"][f"{baseline}_signed"]) for row in rows]
    absolute = [abs(value) for value in signed]
    return {
        "n": len(rows),
        "equal_entity_weighted_absolute_error_pp": rounded(
            statistics.fmean(absolute)
        ),
        "signed_calibration_bias_pp": rounded(statistics.fmean(signed)),
        "absolute_calibration_bias_pp": rounded(abs(statistics.fmean(signed))),
        "root_mean_squared_error_pp": rounded(
            math.sqrt(statistics.fmean(value * value for value in signed))
        ),
        "median_absolute_error_pp": rounded(statistics.median(absolute)),
    }


def percentile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("cannot take a percentile of no values")
    position = probability * (len(sorted_values) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def paired_bootstrap(
    rows: list[dict[str, Any]], label: str, config: dict[str, Any]
) -> dict[str, Any]:
    differences = [
        float(row["errors_percent"]["country_logit_absolute"])
        - float(row["errors_percent"]["locf_absolute"])
        for row in rows
    ]
    digest = int(hashlib.sha256(label.encode("utf-8")).hexdigest()[:8], 16)
    seed = (int(config["base_seed"]) + digest) % (2**32)
    rng = random.Random(seed)
    count = len(differences)
    resamples = int(config["resamples"])
    draws = []
    for _ in range(resamples):
        draws.append(statistics.fmean(differences[rng.randrange(count)] for _ in range(count)))
    draws.sort()
    alpha = 1.0 - float(config["confidence_level"])
    tolerance = 1e-12
    country_logit_better = sum(value < -tolerance for value in differences)
    ties = sum(abs(value) <= tolerance for value in differences)
    locf_better = len(differences) - country_logit_better - ties
    return {
        "contrast": "country_logit_absolute_error_minus_locf_absolute_error",
        "mean_difference_pp": rounded(statistics.fmean(differences)),
        "confidence_interval_pp": [
            rounded(percentile(draws, alpha / 2.0)),
            rounded(percentile(draws, 1.0 - alpha / 2.0)),
        ],
        "confidence_level": float(config["confidence_level"]),
        "resamples": resamples,
        "seed": seed,
        "row_level_counts": {
            "country_logit_lower_error": country_logit_better,
            "tie": ties,
            "locf_lower_error": locf_better,
        },
    }


def slice_definitions(
    rows: list[dict[str, Any]], indicator_codes: list[str]
) -> list[tuple[str, list[dict[str, Any]]]]:
    slices: list[tuple[str, list[dict[str, Any]]]] = [
        ("pooled_overall", rows),
        (
            "pooled_partial",
            [row for row in rows if row["completeness_stratum"] == "partial"],
        ),
        (
            "pooled_dense",
            [row for row in rows if row["completeness_stratum"] == "dense"],
        ),
    ]
    for code in indicator_codes:
        indicator_rows = [row for row in rows if row["indicator_code"] == code]
        slices.extend(
            [
                (f"{code}__overall", indicator_rows),
                (
                    f"{code}__partial",
                    [
                        row
                        for row in indicator_rows
                        if row["completeness_stratum"] == "partial"
                    ],
                ),
                (
                    f"{code}__dense",
                    [
                        row
                        for row in indicator_rows
                        if row["completeness_stratum"] == "dense"
                    ],
                ),
            ]
        )
    return slices


def evaluate_slices(
    rows: list[dict[str, Any]], benchmark: dict[str, Any]
) -> dict[str, Any]:
    output: dict[str, Any] = {}
    tolerance = float(benchmark["metrics"]["tie_tolerance"])
    for label, selected in slice_definitions(
        rows, list(benchmark["data_contract"]["indicator_codes"])
    ):
        locf = metric_summary(selected, "locf")
        country_logit = metric_summary(selected, "country_logit")
        difference = (
            country_logit["equal_entity_weighted_absolute_error_pp"]
            - locf["equal_entity_weighted_absolute_error_pp"]
        )
        if difference < -tolerance:
            winner = "country_logit"
        elif difference > tolerance:
            winner = "locf"
        else:
            winner = "tie"
        output[label] = {
            "row_count": len(selected),
            "baselines": {"locf": locf, "country_logit": country_logit},
            "primary_metric_winner": winner,
            "paired_uncertainty": paired_bootstrap(
                selected, label, benchmark["uncertainty"]
            ),
        }
    return output


def expected_count_map(benchmark: dict[str, Any]) -> dict[tuple[str, str], int]:
    expected = benchmark["eligibility"]["expected_counts"]
    output: dict[tuple[str, str], int] = {}
    for code in benchmark["data_contract"]["indicator_codes"]:
        output[(code, "partial")] = int(expected[code]["partial"])
        output[(code, "dense")] = int(expected[code]["dense"])
        output[(code, "total")] = int(expected[code]["total"])
    return output


def observed_count_map(rows: list[dict[str, Any]]) -> dict[tuple[str, str], int]:
    output: dict[tuple[str, str], int] = {}
    for code in sorted({row["indicator_code"] for row in rows}):
        code_rows = [row for row in rows if row["indicator_code"] == code]
        output[(code, "partial")] = sum(
            row["completeness_stratum"] == "partial" for row in code_rows
        )
        output[(code, "dense")] = sum(
            row["completeness_stratum"] == "dense" for row in code_rows
        )
        output[(code, "total")] = len(code_rows)
    return output


def validate(
    benchmark: dict[str, Any],
    benchmark_path: Path,
    snapshot_path: Path,
    preflight_path: Path,
    preflight: dict[str, Any],
    rows: list[dict[str, Any]],
    matrix_matches_snapshot: bool,
    slices: dict[str, Any],
    controls: dict[str, Any],
) -> list[dict[str, Any]]:
    contract = benchmark["data_contract"]
    expected_counts = expected_count_map(benchmark)
    observed_counts = observed_count_map(rows)
    values_finite = all(
        math.isfinite(float(value))
        for row in rows
        for group in ("predictions_percent", "errors_percent")
        for value in row[group].values()
    )
    predictions_bounded = all(
        0.0 <= float(value) <= 100.0
        for row in rows
        for value in row["predictions_percent"].values()
    )
    minimum_training = int(benchmark["eligibility"]["minimum_observed_training_years"])
    required_slice_names = {
        label
        for label, _ in slice_definitions(rows, list(contract["indicator_codes"]))
    }
    checks = [
        check(
            "schema_version",
            benchmark["schema_version"] == "p057_amr_baseline_eval_v1",
            f"Observed {benchmark['schema_version']}.",
        ),
        check(
            "exact_problem_scope",
            benchmark["scope"]["included_catalog_problem_ids"] == [57],
            "Only catalog problem #057 is included.",
        ),
        check(
            "benchmark_is_current_file",
            benchmark_path.resolve() == DEFAULT_BENCHMARK.resolve(),
            str(benchmark_path),
        ),
        check(
            "source_snapshot_hash",
            sha256_path(snapshot_path)
            == benchmark["inputs"]["source_snapshot"]["sha256"],
            sha256_path(snapshot_path),
        ),
        check(
            "upstream_preflight_hash",
            sha256_path(preflight_path)
            == benchmark["inputs"]["upstream_preflight"]["sha256"],
            sha256_path(preflight_path),
        ),
        check(
            "upstream_preflight_status",
            preflight["status"]
            == benchmark["inputs"]["upstream_preflight"]["required_status"]
            and preflight["p057"]["status"]
            == benchmark["inputs"]["upstream_preflight"]["required_p057_status"],
            f"{preflight['status']} / {preflight['p057']['status']}",
        ),
        check(
            "frozen_indicator_set",
            sorted({row["indicator_code"] for row in rows})
            == sorted(contract["indicator_codes"]),
            ", ".join(sorted({row["indicator_code"] for row in rows})),
        ),
        check(
            "holdout_year_is_2023",
            int(contract["holdout_year"]) == 2023
            and all(row["holdout_year"] == 2023 for row in rows),
            "All targets are 2023.",
        ),
        check(
            "training_stops_before_holdout",
            all(max(row["training_years"]) <= 2022 for row in rows),
            "No training row is later than 2022.",
        ),
        check(
            "minimum_training_rows",
            all(len(row["training_years"]) >= minimum_training for row in rows),
            f"Every row has at least {minimum_training} observed training years.",
        ),
        check(
            "frozen_eligibility_counts",
            observed_counts == expected_counts
            and len(rows)
            == int(benchmark["eligibility"]["expected_counts"]["pooled_total"]),
            f"Observed {len(rows)} rows with the frozen indicator/stratum counts.",
        ),
        check(
            "eligible_strata_only",
            {row["completeness_stratum"] for row in rows} == {"partial", "dense"},
            ", ".join(sorted({row["completeness_stratum"] for row in rows})),
        ),
        check(
            "partial_is_lowest_eligible_stratum",
            benchmark["completeness_strata"][
                "lowest_completeness_eligible_stratum"
            ]
            == "partial",
            "The frozen lowest eligible stratum is partial.",
        ),
        check(
            "matrix_matches_source_snapshot",
            matrix_matches_snapshot,
            "Every non-null matrix value matches the hashed source snapshot.",
        ),
        check(
            "same_rows_for_both_baselines",
            all(
                set(row["predictions_percent"]) == {"locf", "country_logit"}
                for row in rows
            ),
            f"Both baselines score the same {len(rows)} rows.",
        ),
        check(
            "finite_outputs",
            values_finite,
            "All predictions and errors are finite.",
        ),
        check(
            "bounded_predictions",
            predictions_bounded,
            "All predictions lie in [0, 100].",
        ),
        check(
            "positive_control",
            controls["positive_logit_linear"]["passed"],
            f"Error {controls['positive_logit_linear']['absolute_error_pp']:.3e} pp.",
        ),
        check(
            "negative_control",
            controls["negative_constant"]["passed"],
            f"Difference {controls['negative_constant']['absolute_difference_pp']:.3e} pp.",
        ),
        check(
            "all_declared_slices_present",
            set(slices) == required_slice_names
            and all(value["row_count"] > 0 for value in slices.values()),
            f"Observed {len(slices)} nonempty slices.",
        ),
        check(
            "candidate_not_executed",
            benchmark["future_candidate_gate"]["executed_in_this_packet"] is False,
            "This packet establishes denominators only.",
        ),
        check(
            "no_post_outcome_exclusions",
            contract["post_outcome_exclusions_allowed"] is False
            and benchmark["eligibility"][
                "uses_2023_value_for_selection_beyond_presence"
            ]
            is False,
            "Eligibility uses holdout presence, never the held-out value.",
        ),
    ]
    return checks


def build_result(
    benchmark_path: Path,
    snapshot_path: Path,
    preflight_path: Path,
    protocol_commit: str,
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    snapshot = read_json(snapshot_path)
    preflight = read_json(preflight_path)
    rows, matrix_matches_snapshot = build_evaluation_rows(
        benchmark, snapshot, preflight
    )
    controls = run_synthetic_controls(
        float(
            benchmark["baselines"]["country_specific_logit_time_trend"][
                "probability_clip_epsilon"
            ]
        )
    )
    slices = evaluate_slices(rows, benchmark)
    checks = validate(
        benchmark,
        benchmark_path,
        snapshot_path,
        preflight_path,
        preflight,
        rows,
        matrix_matches_snapshot,
        slices,
        controls,
    )
    passed = sum(item["passed"] for item in checks)
    return {
        "schema_version": benchmark["schema_version"],
        "status": "pass" if passed == len(checks) else "fail",
        "scientific_status": "baseline_denominators_established",
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "source_snapshot": str(snapshot_path.relative_to(ROOT)),
            "source_snapshot_sha256": sha256_path(snapshot_path),
            "upstream_preflight": str(preflight_path.relative_to(ROOT)),
            "upstream_preflight_sha256": sha256_path(preflight_path),
            "tool": str(Path(__file__).resolve().relative_to(ROOT)),
            "tool_sha256": sha256_path(Path(__file__).resolve()),
            "protocol_commit": protocol_commit,
        },
        "environment": {"python": platform.python_version()},
        "summary": {
            "check_count": len(checks),
            "passed_checks": passed,
            "failed_checks": [item["name"] for item in checks if not item["passed"]],
            "evaluated_row_count": len(rows),
            "candidate_executed": False,
            "holdout_year": int(benchmark["data_contract"]["holdout_year"]),
            "lowest_completeness_eligible_stratum": benchmark[
                "completeness_strata"
            ]["lowest_completeness_eligible_stratum"],
        },
        "controls": controls,
        "checks": checks,
        "slices": slices,
        "rows": rows,
        "claim_boundary": benchmark["interpretation_boundaries"],
    }


def baseline_sentence(slice_result: dict[str, Any]) -> str:
    locf = slice_result["baselines"]["locf"][
        "equal_entity_weighted_absolute_error_pp"
    ]
    trend = slice_result["baselines"]["country_logit"][
        "equal_entity_weighted_absolute_error_pp"
    ]
    winner = slice_result["primary_metric_winner"]
    if winner == "locf":
        conclusion = "LOCF is the harder denominator"
    elif winner == "country_logit":
        conclusion = "the country-logit trend is the harder denominator"
    else:
        conclusion = "the two denominators tie"
    return (
        f"LOCF MAE `{locf:.2f}` pp; country-logit MAE `{trend:.2f}` pp; "
        f"{conclusion}."
    )


def render_report(result: dict[str, Any]) -> str:
    slices = result["slices"]
    e_coli = slices["AMR_INFECT_ECOLI__overall"]
    mrsa = slices["AMR_INFECT_MRSA__overall"]
    e_coli_partial = slices["AMR_INFECT_ECOLI__partial"]
    mrsa_partial = slices["AMR_INFECT_MRSA__partial"]
    pooled = slices["pooled_overall"]
    lines = [
        "# Problem `#057` AMR Frozen-Baseline Evaluation v1",
        "",
        "Date: 2026-07-30",
        "",
        "Status: **the two preregistered denominators are now scored on the frozen",
        "2023 holdout; no candidate model is evaluated.**",
        "",
        "This packet remains strictly inside catalog problem `#057`. It does not",
        "estimate resistance for non-reporting entities, recommend antibiotics, issue",
        "a clinical or public-health action, or claim the frontier problem is solved.",
        "",
        "## Machine-check summary",
        "",
        f"- Contract checks: `{result['summary']['passed_checks']}/{result['summary']['check_count']}` passed.",
        f"- Evaluated rows: `{result['summary']['evaluated_row_count']}` on the 2023 holdout.",
        f"- Protocol commit: `{result['source']['protocol_commit']}`.",
        "- Candidate model executed: `false`.",
        "",
        "## Does a trend beat yesterday's value?",
        "",
        "| Slice | n | LOCF MAE | Country-logit MAE | Winner | Paired difference (trend − LOCF) | 95% bootstrap interval |",
        "|---|---:|---:|---:|---|---:|---:|",
    ]
    ordered_slices = [
        ("Pooled overall", "pooled_overall"),
        ("Pooled partial", "pooled_partial"),
        ("Pooled dense", "pooled_dense"),
        ("E. coli overall", "AMR_INFECT_ECOLI__overall"),
        ("E. coli partial", "AMR_INFECT_ECOLI__partial"),
        ("E. coli dense", "AMR_INFECT_ECOLI__dense"),
        ("MRSA overall", "AMR_INFECT_MRSA__overall"),
        ("MRSA partial", "AMR_INFECT_MRSA__partial"),
        ("MRSA dense", "AMR_INFECT_MRSA__dense"),
    ]
    for display, key in ordered_slices:
        value = slices[key]
        locf = value["baselines"]["locf"][
            "equal_entity_weighted_absolute_error_pp"
        ]
        trend = value["baselines"]["country_logit"][
            "equal_entity_weighted_absolute_error_pp"
        ]
        contrast = value["paired_uncertainty"]["mean_difference_pp"]
        lower, upper = value["paired_uncertainty"]["confidence_interval_pp"]
        lines.append(
            f"| {display} | {value['row_count']} | {locf:.2f} pp | "
            f"{trend:.2f} pp | `{value['primary_metric_winner']}` | "
            f"{contrast:+.2f} pp | [{lower:+.2f}, {upper:+.2f}] pp |"
        )
    lines.extend(
        [
            "",
            "A positive paired difference means the country-logit trend has larger",
            "absolute error. The bootstrap interval is descriptive and does not alter any",
            "gate. Equal entity weights are used because the frozen public rates do not",
            "carry a comparable observation denominator for every entity-year.",
            "",
            "### Indicator-level reading",
            "",
            f"- **E. coli overall (`n={e_coli['row_count']}`):** {baseline_sentence(e_coli)}",
            f"- **E. coli partial (`n={e_coli_partial['row_count']}`):** {baseline_sentence(e_coli_partial)}",
            f"- **MRSA overall (`n={mrsa['row_count']}`):** {baseline_sentence(mrsa)}",
            f"- **MRSA partial (`n={mrsa_partial['row_count']}`):** {baseline_sentence(mrsa_partial)}",
            "",
            "The `partial` slice is the lowest-completeness stratum that can satisfy the",
            "predeclared requirement of an observed 2023 holdout plus at least three",
            "observed training years. Calling it `sparse` would silently change the frozen",
            "stratification after eligibility was known.",
            "",
            "## Calibration boundary",
            "",
            "| Indicator / slice | LOCF signed bias | Country-logit signed bias | LOCF absolute bias | Country-logit absolute bias |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for display, key in [
        ("E. coli overall", "AMR_INFECT_ECOLI__overall"),
        ("E. coli partial", "AMR_INFECT_ECOLI__partial"),
        ("MRSA overall", "AMR_INFECT_MRSA__overall"),
        ("MRSA partial", "AMR_INFECT_MRSA__partial"),
    ]:
        value = slices[key]["baselines"]
        lines.append(
            f"| {display} | {value['locf']['signed_calibration_bias_pp']:+.2f} pp | "
            f"{value['country_logit']['signed_calibration_bias_pp']:+.2f} pp | "
            f"{value['locf']['absolute_calibration_bias_pp']:.2f} pp | "
            f"{value['country_logit']['absolute_calibration_bias_pp']:.2f} pp |"
        )
    lines.extend(
        [
            "",
            "Calibration-in-the-large is reported because a low absolute error can coexist",
            "with systematic over- or under-prediction. A future candidate must beat both",
            "baselines on absolute error in each indicator overall and in `partial`, while",
            "its absolute bias stays within the frozen two-percentage-point guardrail.",
            "",
            "## Leakage and missingness audit",
            "",
            "- Every trend and LOCF prediction uses observations from 2016–2022 only.",
            "- The held-out 2023 value is used only as the final target; eligibility uses",
            "  its presence, never its magnitude.",
            "- All 141 preregistered eligible rows are retained: 72 E. coli and 69 MRSA.",
            "- The comparison remains conditional on 2023 reporters. The earlier Manski",
            "  bounds still govern any claim about all 245 frozen entities.",
            "",
            "## Official evidence",
            "",
            "- WHO AMR dashboard: [Antimicrobial Resistance profile]",
            "(https://data.who.int/dashboards/amr/antimicrobial-resistance-profile).",
            "- WHO E. coli indicator: [third-generation cephalosporin resistance]",
            "(https://data.who.int/indicators/i/918081E/745F475).",
            "- WHO MRSA indicator: [methicillin resistance]",
            "(https://data.who.int/indicators/i/918081E/5DD9606).",
            "",
            "## Next falsifier",
            "",
            "Admit one explicitly specified candidate only after its features, fitting",
            "window, hyperparameters, and missingness handling are committed. Score it on",
            "these exact 141 rows; it must beat both frozen denominators for each indicator",
            "overall and in `partial`, without changing the cohort or calibration guardrail.",
            "",
            "## Claim boundary",
            "",
            "This is a denominator study on country/entity-level surveillance percentages.",
            "It is not a clinical forecast, resistance estimate for missing countries,",
            "causal analysis, treatment recommendation, pathogen-design result, or solution",
            "to catalog problem `#057`.",
            "",
        ]
    )
    return "\n".join(lines)


def render_discussion(result: dict[str, Any]) -> str:
    slices = result["slices"]
    pooled = slices["pooled_overall"]
    partial = slices["pooled_partial"]
    pooled_locf = pooled["baselines"]["locf"][
        "equal_entity_weighted_absolute_error_pp"
    ]
    pooled_trend = pooled["baselines"]["country_logit"][
        "equal_entity_weighted_absolute_error_pp"
    ]
    partial_locf = partial["baselines"]["locf"][
        "equal_entity_weighted_absolute_error_pp"
    ]
    partial_trend = partial["baselines"]["country_logit"][
        "equal_entity_weighted_absolute_error_pp"
    ]
    return "\n".join(
        [
            "# When does a trend become weaker than simply remembering the last value?",
            "",
            "The frozen `#057` AMR denominator study now scores 141 entity-indicator rows",
            "on a 2023 holdout. No candidate model has been admitted yet.",
            "",
            f"- Across all rows, LOCF has `{pooled_locf:.2f}` percentage-point MAE and the",
            f"  country-specific logit trend has `{pooled_trend:.2f}`.",
            f"- In the lowest-completeness eligible stratum (`partial`, n={partial['row_count']}),",
            f"  LOCF has `{partial_locf:.2f}` MAE and the trend has `{partial_trend:.2f}`.",
            "- The comparison uses equal entity weights, holds every 2023 value out of",
            "  fitting, and retains all preregistered eligible rows.",
            "",
            "The heuristic question is: **if a more structured baseline loses to memory,",
            "should a frontier candidate have to explain why its extra structure helps",
            "before it receives credit for a lower average error?**",
            "",
            "Three prompts for collaborators:",
            "",
            "1. Should a future candidate be required to beat the stronger baseline",
            "   separately for E. coli and MRSA, or is a pooled win ever defensible?",
            "2. Without comparable isolate counts in every public row, is equal-country",
            "   weighting the least misleading choice, or should uncertainty be modeled",
            "   through an explicit denominator-missing sensitivity analysis?",
            "3. Which candidate is worth freezing first: hierarchical shrinkage, a robust",
            "   state-space model, or a deliberately simple pooled logit trend?",
            "",
            "Important boundary: these results apply only to entities with an observed 2023",
            "value and at least three training years. They do not estimate resistance for",
            "non-reporters and produce no prescribing or clinical recommendation.",
            "",
            "Research packet: `research/P057_AMR_baseline_eval_v1.md`",
            "",
        ]
    )


def self_test(benchmark_path: Path) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    epsilon = float(
        benchmark["baselines"]["country_specific_logit_time_trend"][
            "probability_clip_epsilon"
        ]
    )
    controls = run_synthetic_controls(epsilon)
    if not all(value["passed"] for value in controls.values()):
        raise SystemExit("synthetic control failure")
    return {"status": "pass", "controls": controls}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--preflight", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument("--protocol-commit")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        print(pretty_json(self_test(args.benchmark)).strip())
        return

    protocol_commit = args.protocol_commit
    if args.check_only:
        existing = read_json(args.result)
        protocol_commit = existing["source"]["protocol_commit"]
    if not protocol_commit:
        raise SystemExit("--protocol-commit is required for a formal evaluation")

    result = build_result(
        args.benchmark, args.snapshot, args.preflight, protocol_commit
    )
    report = render_report(result) + "\n"
    discussion = render_discussion(result) + "\n"
    result_text = pretty_json(result)

    if args.check_only:
        comparisons = {
            str(args.result): args.result.read_text(encoding="utf-8") == result_text,
            str(args.report): args.report.read_text(encoding="utf-8") == report,
            str(args.discussion): args.discussion.read_text(encoding="utf-8")
            == discussion,
        }
        if not all(comparisons.values()):
            raise SystemExit(f"replay mismatch: {comparisons}")
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "passed_checks": result["summary"]["passed_checks"],
                    "check_count": result["summary"]["check_count"],
                    "evaluated_rows": result["summary"]["evaluated_row_count"],
                    "byte_identical": comparisons,
                },
                sort_keys=True,
            )
        )
        return

    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.discussion.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(result_text, encoding="utf-8")
    args.report.write_text(report, encoding="utf-8")
    args.discussion.write_text(discussion, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "passed_checks": result["summary"]["passed_checks"],
                "check_count": result["summary"]["check_count"],
                "evaluated_rows": result["summary"]["evaluated_row_count"],
                "candidate_executed": result["summary"]["candidate_executed"],
                "result": str(args.result),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
