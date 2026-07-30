#!/usr/bin/env python3
"""Run the frozen P057 shared-slope, shrunk-intercept candidate screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P057_AMR_shrinkage_candidate_v1.json"
DEFAULT_SNAPSHOT = ROOT / "results/P057_P058_source_snapshot_v1.json"
DEFAULT_PREFLIGHT = ROOT / "results/P057_P058_data_preflight_v1.json"
DEFAULT_BASELINE = ROOT / "results/P057_AMR_baseline_eval_v1.json"
DEFAULT_RESULT = ROOT / "results/P057_AMR_shrinkage_candidate_v1.json"
DEFAULT_REPORT = ROOT / "research/P057_AMR_shrinkage_candidate_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/P057_AMR_shrinkage_discussion_v1.md"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def rounded(value: float, digits: int = 10) -> float:
    return round(float(value), digits)


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def inverse_logit(values: np.ndarray) -> np.ndarray:
    positive = values >= 0
    output = np.empty_like(values, dtype=float)
    output[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    growth = np.exp(values[~positive])
    output[~positive] = growth / (1.0 + growth)
    return output


def git_head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def build_source_index(
    snapshot: dict[str, Any],
) -> dict[str, dict[str, dict[int, float]]]:
    index: dict[str, dict[str, dict[int, float]]] = {}
    for row in snapshot["p057"]["records"]:
        code = str(row["indicator_code"])
        entity = str(row["m49"])
        year = int(row["year"])
        values = index.setdefault(code, {}).setdefault(entity, {})
        if year in values:
            raise ValueError(f"duplicate source row for {code}/{entity}/{year}")
        values[year] = float(row["value_percent"])
    return index


def fit_panel(
    rows: list[tuple[str, int, float]],
    ridge_lambda: float,
    epsilon: float,
    center_year: float,
) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot fit an empty panel")
    entities = sorted({entity for entity, _, _ in rows})
    entity_columns = {entity: position for position, entity in enumerate(entities)}
    design = np.zeros((len(rows), 2 + len(entities)), dtype=float)
    response = np.zeros(len(rows), dtype=float)
    for row_index, (entity, year, value) in enumerate(rows):
        design[row_index, 0] = 1.0
        design[row_index, 1] = float(year) - center_year
        design[row_index, 2 + entity_columns[entity]] = 1.0
        probability = min(1.0 - epsilon, max(epsilon, value / 100.0))
        response[row_index] = math.log(probability / (1.0 - probability))
    penalty = np.zeros(design.shape[1], dtype=float)
    penalty[2:] = ridge_lambda
    normal = design.T @ design + np.diag(penalty)
    target = design.T @ response
    try:
        coefficients = np.linalg.solve(normal, target)
    except np.linalg.LinAlgError:
        coefficients, _, _, _ = np.linalg.lstsq(normal, target, rcond=None)
    return {
        "intercept": float(coefficients[0]),
        "slope_per_year": float(coefficients[1]),
        "entity_deviations": {
            entity: float(coefficients[2 + entity_columns[entity]])
            for entity in entities
        },
        "training_row_count": len(rows),
        "training_entity_count": len(entities),
    }


def predict_percent(model: dict[str, Any], entity: str, year: int, center_year: float) -> float:
    latent = (
        float(model["intercept"])
        + float(model["slope_per_year"]) * (float(year) - center_year)
        + float(model["entity_deviations"].get(entity, 0.0))
    )
    return float(100.0 * inverse_logit(np.asarray([latent], dtype=float))[0])


def rows_before_year(
    indicator_index: dict[str, dict[int, float]], year: int
) -> list[tuple[str, int, float]]:
    return sorted(
        (entity, observed_year, value)
        for entity, values in indicator_index.items()
        for observed_year, value in values.items()
        if observed_year < year
    )


def rows_in_year(
    indicator_index: dict[str, dict[int, float]], year: int
) -> list[tuple[str, int, float]]:
    return sorted(
        (entity, year, values[year])
        for entity, values in indicator_index.items()
        if year in values
    )


def select_lambda(
    indicator_index: dict[str, dict[int, float]],
    config: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    epsilon = float(candidate["probability_clip_epsilon"])
    center_year = float(candidate["time_center_year"])
    tolerance = float(config["tie_tolerance"])
    candidates = []
    for ridge_lambda in [float(value) for value in config["lambda_grid"]]:
        fold_rows = []
        for validation_year in [int(value) for value in config["validation_years"]]:
            training = rows_before_year(indicator_index, validation_year)
            validation = rows_in_year(indicator_index, validation_year)
            model = fit_panel(training, ridge_lambda, epsilon, center_year)
            signed = [
                predict_percent(model, entity, validation_year, center_year) - observed
                for entity, _, observed in validation
            ]
            fold_rows.append(
                {
                    "validation_year": validation_year,
                    "training_row_count": len(training),
                    "training_entity_count": len(
                        {entity for entity, _, _ in training}
                    ),
                    "validation_row_count": len(validation),
                    "unseen_validation_entity_count": sum(
                        entity not in model["entity_deviations"]
                        for entity, _, _ in validation
                    ),
                    "mean_absolute_error_pp": rounded(
                        float(np.mean(np.abs(np.asarray(signed, dtype=float))))
                    ),
                }
            )
        pooled_weighted_error = sum(
            fold["mean_absolute_error_pp"] * fold["validation_row_count"]
            for fold in fold_rows
        ) / sum(fold["validation_row_count"] for fold in fold_rows)
        candidates.append(
            {
                "lambda": ridge_lambda,
                "pooled_mean_absolute_error_pp": rounded(pooled_weighted_error),
                "folds": fold_rows,
            }
        )
    best_error = min(row["pooled_mean_absolute_error_pp"] for row in candidates)
    tied = [
        row["lambda"]
        for row in candidates
        if abs(row["pooled_mean_absolute_error_pp"] - best_error) <= tolerance
    ]
    return {
        "selected_lambda": max(tied),
        "selected_pooled_mean_absolute_error_pp": rounded(best_error),
        "tie_break": "larger_lambda",
        "grid_results": candidates,
    }


def evaluation_rows(
    source_index: dict[str, dict[str, dict[int, float]]],
    baseline: dict[str, Any],
    selected: dict[str, dict[str, Any]],
    benchmark: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    candidate = benchmark["candidate"]
    contract = benchmark["data_contract"]
    holdout_year = int(contract["holdout_year"])
    training_years = {int(year) for year in contract["training_years"]}
    epsilon = float(candidate["probability_clip_epsilon"])
    center_year = float(candidate["time_center_year"])
    final_models: dict[str, Any] = {}
    for code in contract["indicator_codes"]:
        training = sorted(
            (entity, year, value)
            for entity, values in source_index[code].items()
            for year, value in values.items()
            if year in training_years
        )
        final_models[code] = fit_panel(
            training,
            float(selected[code]["selected_lambda"]),
            epsilon,
            center_year,
        )
    baseline_by_key = {
        (str(row["indicator_code"]), str(row["m49"])): row
        for row in baseline["rows"]
    }
    output = []
    for baseline_row in baseline["rows"]:
        code = str(baseline_row["indicator_code"])
        entity = str(baseline_row["m49"])
        observed = float(baseline_row["observed_percent"])
        prediction = predict_percent(
            final_models[code], entity, holdout_year, center_year
        )
        output.append(
            {
                "indicator_code": code,
                "m49": entity,
                "iso3": str(baseline_row["iso3"]),
                "entity": str(baseline_row["entity"]),
                "completeness_stratum": str(
                    baseline_row["completeness_stratum"]
                ),
                "training_years": list(baseline_row["training_years"]),
                "holdout_year": holdout_year,
                "observed_percent": rounded(observed),
                "candidate_prediction_percent": rounded(prediction),
                "candidate_signed_error_pp": rounded(prediction - observed),
                "candidate_absolute_error_pp": rounded(abs(prediction - observed)),
                "baseline_predictions_percent": dict(
                    baseline_by_key[(code, entity)]["predictions_percent"]
                ),
            }
        )
    model_summary = {
        code: {
            "selected_lambda": float(selected[code]["selected_lambda"]),
            "intercept": rounded(final_models[code]["intercept"], 12),
            "shared_slope_per_year": rounded(
                final_models[code]["slope_per_year"], 12
            ),
            "training_row_count": final_models[code]["training_row_count"],
            "training_entity_count": final_models[code]["training_entity_count"],
            "target_entities_unseen_in_training": sum(
                row["indicator_code"] == code
                and row["m49"] not in final_models[code]["entity_deviations"]
                for row in output
            ),
        }
        for code in contract["indicator_codes"]
    }
    return output, model_summary


def metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    signed = np.asarray(
        [row["candidate_signed_error_pp"] for row in rows], dtype=float
    )
    absolute = np.abs(signed)
    return {
        "n": len(rows),
        "equal_entity_weighted_absolute_error_pp": rounded(absolute.mean()),
        "signed_calibration_bias_pp": rounded(signed.mean()),
        "absolute_calibration_bias_pp": rounded(abs(signed.mean())),
        "root_mean_squared_error_pp": rounded(np.sqrt(np.mean(signed**2))),
        "median_absolute_error_pp": rounded(np.median(absolute)),
    }


def sliced(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    output = {
        "pooled_overall": rows,
        "pooled_partial": [
            row for row in rows if row["completeness_stratum"] == "partial"
        ],
        "pooled_dense": [
            row for row in rows if row["completeness_stratum"] == "dense"
        ],
    }
    for code in sorted({row["indicator_code"] for row in rows}):
        selected = [row for row in rows if row["indicator_code"] == code]
        output[f"{code}__overall"] = selected
        output[f"{code}__partial"] = [
            row for row in selected if row["completeness_stratum"] == "partial"
        ]
        output[f"{code}__dense"] = [
            row for row in selected if row["completeness_stratum"] == "dense"
        ]
    return output


def evaluate_gate(
    slices: dict[str, Any], baseline: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    comparisons = []
    for label in config["required_slices"]:
        candidate = slices[label]["candidate"]
        denominators = baseline["slices"][label]["baselines"]
        candidate_mae = float(
            candidate["equal_entity_weighted_absolute_error_pp"]
        )
        locf_mae = float(
            denominators["locf"]["equal_entity_weighted_absolute_error_pp"]
        )
        trend_mae = float(
            denominators["country_logit"][
                "equal_entity_weighted_absolute_error_pp"
            ]
        )
        tolerance = float(config["primary_tie_tolerance"])
        primary_pass = (
            candidate_mae < locf_mae - tolerance
            and candidate_mae < trend_mae - tolerance
        )
        candidate_bias = float(candidate["absolute_calibration_bias_pp"])
        baseline_bias_floor = min(
            float(denominators["locf"]["absolute_calibration_bias_pp"]),
            float(
                denominators["country_logit"]["absolute_calibration_bias_pp"]
            ),
        )
        calibration_limit = baseline_bias_floor + float(
            config["calibration_margin_pp"]
        )
        calibration_pass = candidate_bias <= calibration_limit + tolerance
        comparisons.append(
            {
                "slice": label,
                "candidate_mae_pp": rounded(candidate_mae),
                "locf_mae_pp": rounded(locf_mae),
                "country_logit_mae_pp": rounded(trend_mae),
                "primary_passed": primary_pass,
                "candidate_absolute_bias_pp": rounded(candidate_bias),
                "baseline_absolute_bias_floor_pp": rounded(baseline_bias_floor),
                "calibration_limit_pp": rounded(calibration_limit),
                "calibration_passed": calibration_pass,
            }
        )
    passed = all(
        row["primary_passed"] and row["calibration_passed"]
        for row in comparisons
    )
    return {
        "passed": passed,
        "decision": (
            "provisional_retrospective_screen_pass"
            if passed
            else "reject_candidate"
        ),
        "comparisons": comparisons,
    }


def synthetic_controls(candidate: dict[str, Any]) -> dict[str, Any]:
    epsilon = float(candidate["probability_clip_epsilon"])
    center = float(candidate["time_center_year"])
    constant_rows = [
        (entity, year, 42.0)
        for entity in ("001", "002", "003")
        for year in (2016, 2018, 2020, 2022)
    ]
    constant_model = fit_panel(constant_rows, 10.0, epsilon, center)
    constant_predictions = [
        predict_percent(constant_model, entity, 2023, center)
        for entity in ("001", "002", "003")
    ]
    exact_rows = []
    offsets = {"001": -0.4, "002": 0.1, "003": 0.5}
    for entity, offset in offsets.items():
        for year in (2016, 2018, 2020, 2022):
            latent = -0.8 + 0.09 * (year - center) + offset
            exact_rows.append(
                (
                    entity,
                    year,
                    float(100.0 * inverse_logit(np.asarray([latent]))[0]),
                )
            )
    exact_model = fit_panel(exact_rows, 0.0, epsilon, center)
    exact_errors = []
    for entity, offset in offsets.items():
        expected = float(
            100.0
            * inverse_logit(
                np.asarray([-0.8 + 0.09 * (2023 - center) + offset])
            )[0]
        )
        observed = predict_percent(exact_model, entity, 2023, center)
        exact_errors.append(abs(observed - expected))
    return {
        "constant_series": {
            "maximum_absolute_error_pp": rounded(
                max(abs(value - 42.0) for value in constant_predictions), 14
            ),
            "passed": max(abs(value - 42.0) for value in constant_predictions)
            <= 1e-10,
        },
        "exact_unpenalized_shared_slope": {
            "maximum_absolute_error_pp": rounded(max(exact_errors), 14),
            "passed": max(exact_errors) <= 1e-10,
        },
    }


def build_result(
    benchmark_path: Path,
    snapshot_path: Path,
    preflight_path: Path,
    baseline_path: Path,
    protocol_commit: str,
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    snapshot = read_json(snapshot_path)
    preflight = read_json(preflight_path)
    baseline = read_json(baseline_path)
    source_index = build_source_index(snapshot)
    selected = {
        code: select_lambda(
            source_index[code],
            benchmark["hyperparameter_selection"],
            benchmark["candidate"],
        )
        for code in benchmark["data_contract"]["indicator_codes"]
    }
    rows, model_summary = evaluation_rows(
        source_index, baseline, selected, benchmark
    )
    selected_rows = sliced(rows)
    slices = {
        label: {"row_count": len(items), "candidate": metric_summary(items)}
        for label, items in selected_rows.items()
    }
    gate = evaluate_gate(slices, baseline, benchmark["frozen_gate"])
    controls = synthetic_controls(benchmark["candidate"])
    baseline_keys = [
        (str(row["indicator_code"]), str(row["m49"]))
        for row in baseline["rows"]
    ]
    candidate_keys = [
        (str(row["indicator_code"]), str(row["m49"])) for row in rows
    ]
    checks = [
        check(
            "scope_is_exactly_p057",
            benchmark["scope"]["included_catalog_problem_ids"] == [57],
            "Only catalog problem #057 is included.",
        ),
        check(
            "source_snapshot_hash_matches",
            sha256_path(snapshot_path)
            == benchmark["inputs"]["source_snapshot"]["sha256"],
            sha256_path(snapshot_path),
        ),
        check(
            "preflight_hash_matches",
            sha256_path(preflight_path)
            == benchmark["inputs"]["upstream_preflight"]["sha256"],
            sha256_path(preflight_path),
        ),
        check(
            "baseline_hash_matches",
            sha256_path(baseline_path)
            == benchmark["inputs"]["frozen_baseline_result"]["sha256"],
            sha256_path(baseline_path),
        ),
        check(
            "upstream_preflight_ready",
            preflight["status"] == "pass"
            and preflight["p057"]["status"]
            == benchmark["inputs"]["upstream_preflight"][
                "required_p057_status"
            ],
            f"{preflight['status']}/{preflight['p057']['status']}",
        ),
        check(
            "baseline_status_and_protocol_frozen",
            baseline["status"] == "pass"
            and baseline["source"]["protocol_commit"]
            == benchmark["inputs"]["frozen_baseline_result"][
                "required_protocol_commit"
            ],
            baseline["source"]["protocol_commit"],
        ),
        check(
            "protocol_commit_recorded",
            len(protocol_commit) == 40,
            protocol_commit,
        ),
        check(
            "rolling_validation_excludes_holdout",
            max(benchmark["hyperparameter_selection"]["validation_years"])
            < benchmark["data_contract"]["holdout_year"],
            str(benchmark["hyperparameter_selection"]["validation_years"]),
        ),
        check(
            "lambda_grid_and_tie_break_frozen",
            benchmark["hyperparameter_selection"]["lambda_grid"]
            == [0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]
            and benchmark["hyperparameter_selection"]["tie_break"]
            == "choose the larger lambda",
            str(benchmark["hyperparameter_selection"]["lambda_grid"]),
        ),
        check(
            "evaluation_row_identity_matches_baseline",
            candidate_keys == baseline_keys,
            f"Compared {len(candidate_keys)} ordered keys.",
        ),
        check(
            "evaluation_row_count_is_141",
            len(rows) == 141,
            f"Observed {len(rows)} rows.",
        ),
        check(
            "holdout_is_2023",
            all(row["holdout_year"] == 2023 for row in rows),
            "All target rows use 2023.",
        ),
        check(
            "target_training_precedes_holdout",
            all(max(row["training_years"]) <= 2022 for row in rows),
            "All target-specific training lists stop by 2022.",
        ),
        check(
            "predictions_are_finite_and_bounded",
            all(
                math.isfinite(row["candidate_prediction_percent"])
                and 0.0 <= row["candidate_prediction_percent"] <= 100.0
                for row in rows
            ),
            "Every candidate prediction lies in [0, 100].",
        ),
        check(
            "selected_lambdas_belong_to_grid",
            all(
                selected[code]["selected_lambda"]
                in benchmark["hyperparameter_selection"]["lambda_grid"]
                for code in selected
            ),
            str(
                {
                    code: selected[code]["selected_lambda"]
                    for code in selected
                }
            ),
        ),
        check(
            "all_validation_folds_populated",
            all(
                fold["training_row_count"] > 0
                and fold["validation_row_count"] > 0
                for value in selected.values()
                for candidate_row in value["grid_results"]
                for fold in candidate_row["folds"]
            ),
            "Every indicator/lambda/year fold has training and validation rows.",
        ),
        check(
            "required_gate_slices_present",
            all(
                label in slices
                and label in baseline["slices"]
                for label in benchmark["frozen_gate"]["required_slices"]
            ),
            str(benchmark["frozen_gate"]["required_slices"]),
        ),
        check(
            "gate_decision_is_deterministic",
            gate["decision"]
            in {
                "provisional_retrospective_screen_pass",
                "reject_candidate",
            },
            gate["decision"],
        ),
        check(
            "constant_series_control_passed",
            controls["constant_series"]["passed"],
            str(controls["constant_series"]),
        ),
        check(
            "shared_slope_control_passed",
            controls["exact_unpenalized_shared_slope"]["passed"],
            str(controls["exact_unpenalized_shared_slope"]),
        ),
        check(
            "exposed_holdout_boundary_recorded",
            benchmark["confirmation_boundary"]["forbidden_label"]
            == "pristine_confirmatory_validation",
            benchmark["confirmation_boundary"]["holdout_exposure"],
        ),
        check(
            "no_post_holdout_retuning",
            benchmark["hyperparameter_selection"][
                "post_holdout_retuning_allowed"
            ]
            is False,
            "The candidate is screened exactly once under the frozen gate.",
        ),
    ]
    passed_checks = sum(item["passed"] for item in checks)
    result_status = "pass" if passed_checks == len(checks) else "fail"
    return {
        "schema_version": "p057_amr_shrinkage_candidate_result_v1",
        "status": result_status,
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "source_snapshot": str(snapshot_path.relative_to(ROOT)),
            "source_snapshot_sha256": sha256_path(snapshot_path),
            "upstream_preflight": str(preflight_path.relative_to(ROOT)),
            "upstream_preflight_sha256": sha256_path(preflight_path),
            "frozen_baseline_result": str(baseline_path.relative_to(ROOT)),
            "frozen_baseline_result_sha256": sha256_path(baseline_path),
            "tool": str(Path(__file__).resolve().relative_to(ROOT)),
            "tool_sha256": sha256_path(Path(__file__).resolve()),
            "protocol_commit": protocol_commit,
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "selection": selected,
        "final_models": model_summary,
        "slices": slices,
        "gate": gate,
        "controls": controls,
        "checks": checks,
        "rows": rows,
        "summary": {
            "evaluated_row_count": len(rows),
            "holdout_year": benchmark["data_contract"]["holdout_year"],
            "selected_lambdas": {
                code: selected[code]["selected_lambda"]
                for code in selected
            },
            "gate_decision": gate["decision"],
            "candidate_screen_passed": gate["passed"],
            "confirmation_status": (
                "requires_untouched_future_year_or_vintage"
                if gate["passed"]
                else "candidate_rejected"
            ),
            "passed_checks": passed_checks,
            "check_count": len(checks),
            "failed_checks": [
                item["name"] for item in checks if not item["passed"]
            ],
        },
    }


def format_metric(value: float) -> str:
    return f"{value:.3f}"


def render_report(result: dict[str, Any]) -> str:
    decision = result["gate"]["decision"]
    selected = result["summary"]["selected_lambdas"]
    pooled = result["slices"]["pooled_overall"]["candidate"]
    lines = [
        "# P057 AMR shared-slope shrinkage candidate screen",
        "",
        f"**Decision:** `{decision}`.",
        "",
        "## What was frozen",
        "",
        "For each indicator, the candidate fits one shared logit-time slope and ridge-shrunk entity intercept deviations. The ridge penalty was selected only from 2019–2022 rolling-origin validation; no 2023 outcome entered selection.",
        "",
        f"- E. coli selected λ: `{selected['AMR_INFECT_ECOLI']}`",
        f"- MRSA selected λ: `{selected['AMR_INFECT_MRSA']}`",
        f"- Evaluated 2023 rows: `{result['summary']['evaluated_row_count']}`",
        "",
        "## 2023 candidate screen",
        "",
        "| Slice | Candidate MAE | LOCF MAE | Country-logit MAE | Candidate abs. bias | Calibration limit | Primary | Calibration |",
        "|---|---:|---:|---:|---:|---:|:---:|:---:|",
    ]
    for row in result["gate"]["comparisons"]:
        lines.append(
            "| {slice} | {candidate} | {locf} | {trend} | {bias} | {limit} | {primary} | {calibration} |".format(
                slice=row["slice"],
                candidate=format_metric(row["candidate_mae_pp"]),
                locf=format_metric(row["locf_mae_pp"]),
                trend=format_metric(row["country_logit_mae_pp"]),
                bias=format_metric(row["candidate_absolute_bias_pp"]),
                limit=format_metric(row["calibration_limit_pp"]),
                primary="pass" if row["primary_passed"] else "fail",
                calibration="pass" if row["calibration_passed"] else "fail",
            )
        )
    lines.extend(
        [
            "",
            f"Pooled descriptive candidate MAE was **{format_metric(pooled['equal_entity_weighted_absolute_error_pp'])} pp** with absolute calibration bias **{format_metric(pooled['absolute_calibration_bias_pp'])} pp**. The frozen gate is decided only by the four indicator-overall/partial slice comparisons above.",
            "",
            "## Confirmation boundary",
            "",
            "The 2023 outcomes had already been summarized in the published baseline evaluation before this candidate protocol was frozen. Therefore, a gate pass could only be called a provisional retrospective screen pass, never pristine confirmatory validation. A pass would still require an untouched future year or data vintage; a failure rejects this exact candidate without post-hoc retuning.",
            "",
            "## Reproducibility and limits",
            "",
            f"- Formal checks: `{result['summary']['passed_checks']}/{result['summary']['check_count']}`",
            f"- Protocol commit: `{result['source']['protocol_commit']}`",
            "- Aggregate public resistance rates are forecasting targets, not individual-level clinical outcomes.",
            "- No patient, prescribing, treatment, pathogen-manipulation, or intervention recommendation is supported.",
            "- This screen does not solve catalog problem #057.",
            "",
        ]
    )
    return "\n".join(lines)


def render_discussion(result: dict[str, Any]) -> str:
    decision = result["gate"]["decision"]
    selected = result["summary"]["selected_lambdas"]
    failed_primary = [
        row["slice"]
        for row in result["gate"]["comparisons"]
        if not row["primary_passed"]
    ]
    outcome = (
        "The candidate cleared every frozen comparison, but the already-exposed 2023 holdout makes this only provisional."
        if result["gate"]["passed"]
        else "The candidate failed the frozen accuracy gate and is rejected without post-hoc retuning."
    )
    prompt = (
        "If simple memory already beats country-by-country extrapolation, is partial pooling the right next inductive bias—or should the next preregistered candidate model shocks rather than slopes?"
    )
    return "\n".join(
        [
            "Can shrinkage rescue a trend after memory wins?",
            "",
            prompt,
            "",
            f"The #057 screen fitted one shared logit-time slope plus ridge-shrunk entity intercepts. Training-only rolling validation selected λ={selected['AMR_INFECT_ECOLI']} for E. coli and λ={selected['AMR_INFECT_MRSA']} for MRSA. {outcome}",
            "",
            "Frozen 2023 comparisons:",
            "",
            *[
                f"- `{row['slice']}`: candidate MAE {row['candidate_mae_pp']:.3f} pp vs LOCF {row['locf_mae_pp']:.3f} and country-logit {row['country_logit_mae_pp']:.3f}; accuracy {'pass' if row['primary_passed'] else 'fail'}, calibration {'pass' if row['calibration_passed'] else 'fail'}."
                for row in result["gate"]["comparisons"]
            ],
            "",
            (
                "No required accuracy slices failed."
                if not failed_primary
                else "Failed accuracy slices: "
                + ", ".join(f"`{label}`" for label in failed_primary)
                + "."
            ),
            "",
            "The interesting design question is not how to tune this model after seeing 2023—that is forbidden—but which qualitatively different, fully preregistered structure deserves the next test. Would you choose robust shocks, region-level pooling, or a changepoint rule, and what falsification gate would you freeze first?",
            "",
            "Boundary: 2023 was already exposed by the baseline report, so even a pass is not pristine confirmation. These are aggregate public rates; no clinical, prescribing, treatment, pathogen-manipulation, or intervention claim is made.",
            "",
        ]
    )


def self_test() -> None:
    benchmark = read_json(DEFAULT_BENCHMARK)
    controls = synthetic_controls(benchmark["candidate"])
    if not all(item["passed"] for item in controls.values()):
        raise SystemExit(f"self-test failed: {controls}")
    synthetic_index = {
        entity: {
            year: 100.0
            * float(
                inverse_logit(
                    np.asarray(
                        [-0.5 + 0.08 * (year - 2019) + int(entity) / 50.0]
                    )
                )[0]
            )
            for year in range(2016, 2023)
        }
        for entity in ("001", "002", "003")
    }
    selection = select_lambda(
        synthetic_index,
        benchmark["hyperparameter_selection"],
        benchmark["candidate"],
    )
    if selection["selected_lambda"] not in benchmark["hyperparameter_selection"][
        "lambda_grid"
    ]:
        raise SystemExit("self-test selected a lambda outside the grid")
    print(pretty_json({"status": "pass", "controls": controls}), end="")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--preflight", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument("--protocol-commit")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.self_test:
        self_test()
        return
    if not args.protocol_commit:
        raise SystemExit("--protocol-commit is required for a formal run")
    result = build_result(
        args.benchmark.resolve(),
        args.snapshot.resolve(),
        args.preflight.resolve(),
        args.baseline.resolve(),
        args.protocol_commit,
    )
    if args.check_only:
        recorded = read_json(args.result.resolve())
        if pretty_json(result) != pretty_json(recorded):
            raise SystemExit("check-only mismatch: rebuilt result differs")
        if render_report(result) != args.report.read_text(encoding="utf-8"):
            raise SystemExit("check-only mismatch: rebuilt report differs")
        if render_discussion(result) != args.discussion.read_text(encoding="utf-8"):
            raise SystemExit("check-only mismatch: rebuilt discussion differs")
        print(
            pretty_json(
                {
                    "status": "pass",
                    "result_sha256": sha256_path(args.result),
                    "report_sha256": sha256_path(args.report),
                    "discussion_sha256": sha256_path(args.discussion),
                }
            ),
            end="",
        )
        return
    args.result.write_text(pretty_json(result), encoding="utf-8")
    args.report.write_text(render_report(result), encoding="utf-8")
    args.discussion.write_text(render_discussion(result), encoding="utf-8")
    print(
        pretty_json(
            {
                "status": result["status"],
                "gate_decision": result["gate"]["decision"],
                "result": str(args.result),
                "report": str(args.report),
                "discussion": str(args.discussion),
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
