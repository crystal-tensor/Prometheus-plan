#!/usr/bin/env python3
"""Independent audit for the frozen P057 shrinkage candidate screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P057_AMR_shrinkage_candidate_v1.json"
DEFAULT_SNAPSHOT = ROOT / "results/P057_P058_source_snapshot_v1.json"
DEFAULT_BASELINE = ROOT / "results/P057_AMR_baseline_eval_v1.json"
DEFAULT_RESULT = ROOT / "results/P057_AMR_shrinkage_candidate_v1.json"
DEFAULT_AUDIT = ROOT / "results/P057_AMR_shrinkage_audit_v1.json"


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


def build_index(snapshot: dict[str, Any]) -> dict[str, dict[str, dict[int, float]]]:
    output: dict[str, dict[str, dict[int, float]]] = {}
    for row in snapshot["p057"]["records"]:
        output.setdefault(str(row["indicator_code"]), {}).setdefault(
            str(row["m49"]), {}
        )[int(row["year"])] = float(row["value_percent"])
    return output


def audit_fit(
    rows: list[tuple[str, int, float]],
    ridge_lambda: float,
    epsilon: float,
    center_year: float,
) -> tuple[np.ndarray, dict[str, int]]:
    entities = sorted({entity for entity, _, _ in rows})
    positions = {entity: index for index, entity in enumerate(entities)}
    design = np.zeros((len(rows), len(entities) + 2), dtype=float)
    response = np.zeros(len(rows), dtype=float)
    for index, (entity, year, value) in enumerate(rows):
        design[index, 0] = 1.0
        design[index, 1] = year - center_year
        design[index, positions[entity] + 2] = 1.0
        probability = np.clip(value / 100.0, epsilon, 1.0 - epsilon)
        response[index] = np.log(probability / (1.0 - probability))
    augmented_design = np.vstack(
        [
            design,
            np.column_stack(
                [
                    np.zeros((len(entities), 2), dtype=float),
                    np.sqrt(ridge_lambda) * np.eye(len(entities), dtype=float),
                ]
            ),
        ]
    )
    augmented_response = np.concatenate(
        [response, np.zeros(len(entities), dtype=float)]
    )
    coefficients, _, _, _ = np.linalg.lstsq(
        augmented_design, augmented_response, rcond=None
    )
    return coefficients, positions


def audit_predict(
    coefficients: np.ndarray,
    positions: dict[str, int],
    entity: str,
    year: int,
    center_year: float,
) -> float:
    latent = coefficients[0] + coefficients[1] * (year - center_year)
    if entity in positions:
        latent += coefficients[positions[entity] + 2]
    if latent >= 0:
        probability = 1.0 / (1.0 + math.exp(-float(latent)))
    else:
        growth = math.exp(float(latent))
        probability = growth / (1.0 + growth)
    return 100.0 * probability


def training_rows(
    index: dict[str, dict[int, float]], before_year: int
) -> list[tuple[str, int, float]]:
    return sorted(
        (entity, year, value)
        for entity, values in index.items()
        for year, value in values.items()
        if year < before_year
    )


def validation_rows(
    index: dict[str, dict[int, float]], year: int
) -> list[tuple[str, int, float]]:
    return sorted(
        (entity, year, values[year])
        for entity, values in index.items()
        if year in values
    )


def independently_select(
    index: dict[str, dict[int, float]], benchmark: dict[str, Any]
) -> tuple[float, dict[float, float]]:
    candidate = benchmark["candidate"]
    selection = benchmark["hyperparameter_selection"]
    epsilon = float(candidate["probability_clip_epsilon"])
    center = float(candidate["time_center_year"])
    pooled: dict[float, float] = {}
    for ridge_lambda in [float(value) for value in selection["lambda_grid"]]:
        absolute_errors = []
        for year in [int(value) for value in selection["validation_years"]]:
            coefficients, positions = audit_fit(
                training_rows(index, year), ridge_lambda, epsilon, center
            )
            for entity, _, observed in validation_rows(index, year):
                predicted = audit_predict(
                    coefficients, positions, entity, year, center
                )
                absolute_errors.append(abs(predicted - observed))
        pooled[ridge_lambda] = float(np.mean(absolute_errors))
    best = min(pooled.values())
    tolerance = float(selection["tie_tolerance"])
    selected = max(
        ridge_lambda
        for ridge_lambda, error in pooled.items()
        if abs(error - best) <= tolerance
    )
    return selected, pooled


def candidate_metric(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    signed = np.asarray(
        [row["candidate_signed_error_pp"] for row in rows], dtype=float
    )
    return {
        "n": len(rows),
        "equal_entity_weighted_absolute_error_pp": rounded(
            np.mean(np.abs(signed))
        ),
        "signed_calibration_bias_pp": rounded(np.mean(signed)),
        "absolute_calibration_bias_pp": rounded(abs(np.mean(signed))),
        "root_mean_squared_error_pp": rounded(np.sqrt(np.mean(signed**2))),
        "median_absolute_error_pp": rounded(np.median(np.abs(signed))),
    }


def slice_rows(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
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
        indicator = [row for row in rows if row["indicator_code"] == code]
        output[f"{code}__overall"] = indicator
        output[f"{code}__partial"] = [
            row for row in indicator if row["completeness_stratum"] == "partial"
        ]
        output[f"{code}__dense"] = [
            row for row in indicator if row["completeness_stratum"] == "dense"
        ]
    return output


def max_numeric_difference(left: Any, right: Any) -> float:
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return math.inf
        return max(
            (max_numeric_difference(left[key], right[key]) for key in left),
            default=0.0,
        )
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return math.inf
        return max(
            (
                max_numeric_difference(a, b)
                for a, b in zip(left, right, strict=True)
            ),
            default=0.0,
        )
    if (
        isinstance(left, (int, float))
        and not isinstance(left, bool)
        and isinstance(right, (int, float))
        and not isinstance(right, bool)
    ):
        return abs(float(left) - float(right))
    return 0.0 if left == right else math.inf


def build_audit(
    benchmark_path: Path,
    snapshot_path: Path,
    baseline_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    snapshot = read_json(snapshot_path)
    baseline = read_json(baseline_path)
    result = read_json(result_path)
    index = build_index(snapshot)
    independent_selected: dict[str, float] = {}
    selection_differences = []
    for code in benchmark["data_contract"]["indicator_codes"]:
        selected, pooled = independently_select(index[code], benchmark)
        independent_selected[code] = selected
        recorded_grid = {
            float(row["lambda"]): float(
                row["pooled_mean_absolute_error_pp"]
            )
            for row in result["selection"][code]["grid_results"]
        }
        for ridge_lambda, error in pooled.items():
            selection_differences.append(
                abs(error - recorded_grid[ridge_lambda])
            )
    center = float(benchmark["candidate"]["time_center_year"])
    epsilon = float(benchmark["candidate"]["probability_clip_epsilon"])
    training_years = set(benchmark["data_contract"]["training_years"])
    models = {}
    for code in benchmark["data_contract"]["indicator_codes"]:
        rows = sorted(
            (entity, year, value)
            for entity, values in index[code].items()
            for year, value in values.items()
            if year in training_years
        )
        models[code] = audit_fit(
            rows, independent_selected[code], epsilon, center
        )
    baseline_by_key = {
        (row["indicator_code"], row["m49"]): row for row in baseline["rows"]
    }
    rebuilt_rows = []
    for recorded in result["rows"]:
        code = recorded["indicator_code"]
        entity = recorded["m49"]
        coefficients, positions = models[code]
        predicted = audit_predict(
            coefficients,
            positions,
            entity,
            benchmark["data_contract"]["holdout_year"],
            center,
        )
        observed = float(baseline_by_key[(code, entity)]["observed_percent"])
        rebuilt = dict(recorded)
        rebuilt["candidate_prediction_percent"] = rounded(predicted)
        rebuilt["candidate_signed_error_pp"] = rounded(predicted - observed)
        rebuilt["candidate_absolute_error_pp"] = rounded(
            abs(predicted - observed)
        )
        rebuilt_rows.append(rebuilt)
    row_difference = max_numeric_difference(rebuilt_rows, result["rows"])
    rebuilt_slices = slice_rows(rebuilt_rows)
    metric_differences = []
    for label, rows in rebuilt_slices.items():
        metric_differences.append(
            max_numeric_difference(
                candidate_metric(rows), result["slices"][label]["candidate"]
            )
        )
    independent_gate_rows = []
    gate_config = benchmark["frozen_gate"]
    for label in gate_config["required_slices"]:
        candidate = candidate_metric(rebuilt_slices[label])
        denominators = baseline["slices"][label]["baselines"]
        candidate_mae = float(
            candidate["equal_entity_weighted_absolute_error_pp"]
        )
        primary = (
            candidate_mae
            < float(
                denominators["locf"][
                    "equal_entity_weighted_absolute_error_pp"
                ]
            )
            - float(gate_config["primary_tie_tolerance"])
            and candidate_mae
            < float(
                denominators["country_logit"][
                    "equal_entity_weighted_absolute_error_pp"
                ]
            )
            - float(gate_config["primary_tie_tolerance"])
        )
        bias_floor = min(
            float(denominators["locf"]["absolute_calibration_bias_pp"]),
            float(
                denominators["country_logit"]["absolute_calibration_bias_pp"]
            ),
        )
        calibration = (
            float(candidate["absolute_calibration_bias_pp"])
            <= bias_floor + float(gate_config["calibration_margin_pp"])
            + float(gate_config["primary_tie_tolerance"])
        )
        independent_gate_rows.append((primary, calibration))
    independent_gate_pass = all(
        primary and calibration
        for primary, calibration in independent_gate_rows
    )
    independent_decision = (
        "provisional_retrospective_screen_pass"
        if independent_gate_pass
        else "reject_candidate"
    )
    checks = [
        check(
            "formal_result_passed",
            result["status"] == "pass",
            result["status"],
        ),
        check(
            "protocol_commit_recorded",
            len(result["source"]["protocol_commit"]) == 40,
            result["source"]["protocol_commit"],
        ),
        check(
            "independent_selected_lambdas_match",
            independent_selected
            == {
                code: result["selection"][code]["selected_lambda"]
                for code in independent_selected
            },
            str(independent_selected),
        ),
        check(
            "independent_validation_errors_match",
            max(selection_differences, default=math.inf) <= 1e-9,
            f"Maximum difference {max(selection_differences, default=math.inf):.3e}.",
        ),
        check(
            "independent_row_predictions_match",
            row_difference <= 1e-9,
            f"Maximum numeric difference {row_difference:.3e}.",
        ),
        check(
            "independent_slice_metrics_match",
            max(metric_differences, default=math.inf) <= 1e-9,
            f"Maximum metric difference {max(metric_differences, default=math.inf):.3e}.",
        ),
        check(
            "independent_gate_decision_matches",
            independent_decision == result["gate"]["decision"],
            independent_decision,
        ),
        check(
            "ordered_rows_match_frozen_baseline",
            [
                (row["indicator_code"], row["m49"])
                for row in result["rows"]
            ]
            == [
                (row["indicator_code"], row["m49"])
                for row in baseline["rows"]
            ],
            f"Compared {len(result['rows'])} ordered keys.",
        ),
        check(
            "holdout_exposure_is_explicit",
            result["summary"]["confirmation_status"]
            in {
                "requires_untouched_future_year_or_vintage",
                "candidate_rejected",
            },
            result["summary"]["confirmation_status"],
        ),
        check(
            "input_hashes_match",
            result["source"]["benchmark_sha256"]
            == sha256_path(benchmark_path)
            and result["source"]["source_snapshot_sha256"]
            == sha256_path(snapshot_path)
            and result["source"]["frozen_baseline_result_sha256"]
            == sha256_path(baseline_path),
            "Benchmark, snapshot, and baseline hashes rechecked.",
        ),
    ]
    passed = sum(item["passed"] for item in checks)
    return {
        "schema_version": "p057_amr_shrinkage_candidate_audit_v1",
        "status": "pass" if passed == len(checks) else "fail",
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "source_snapshot": str(snapshot_path.relative_to(ROOT)),
            "source_snapshot_sha256": sha256_path(snapshot_path),
            "frozen_baseline_result": str(baseline_path.relative_to(ROOT)),
            "frozen_baseline_result_sha256": sha256_path(baseline_path),
            "formal_result": str(result_path.relative_to(ROOT)),
            "formal_result_sha256": sha256_path(result_path),
            "audit_tool": str(Path(__file__).resolve().relative_to(ROOT)),
            "audit_tool_sha256": sha256_path(Path(__file__).resolve()),
            "protocol_commit": result["source"]["protocol_commit"],
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "independent_selected_lambdas": independent_selected,
        "independent_gate_decision": independent_decision,
        "maximum_differences": {
            "selection_mae_pp": rounded(
                max(selection_differences, default=math.inf), 14
            ),
            "row_values": rounded(row_difference, 14),
            "slice_metrics": rounded(
                max(metric_differences, default=math.inf), 14
            ),
        },
        "checks": checks,
        "summary": {
            "passed_checks": passed,
            "check_count": len(checks),
            "failed_checks": [
                item["name"] for item in checks if not item["passed"]
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = build_audit(
        args.benchmark.resolve(),
        args.snapshot.resolve(),
        args.baseline.resolve(),
        args.result.resolve(),
    )
    if args.check_only:
        recorded = read_json(args.audit.resolve())
        if pretty_json(audit) != pretty_json(recorded):
            raise SystemExit("check-only mismatch: rebuilt audit differs")
        print(
            pretty_json(
                {
                    "status": "pass",
                    "audit_sha256": sha256_path(args.audit),
                }
            ),
            end="",
        )
        return
    args.audit.write_text(pretty_json(audit), encoding="utf-8")
    print(
        pretty_json(
            {
                "status": audit["status"],
                "audit": str(args.audit),
                "checks": audit["summary"],
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
