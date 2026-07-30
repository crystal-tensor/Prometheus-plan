#!/usr/bin/env python3
"""Independent NumPy audit of the P057 frozen AMR baseline evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P057_AMR_baseline_eval_v1.json"
DEFAULT_SNAPSHOT = ROOT / "results/P057_P058_source_snapshot_v1.json"
DEFAULT_PREFLIGHT = ROOT / "results/P057_P058_data_preflight_v1.json"
DEFAULT_RESULT = ROOT / "results/P057_AMR_baseline_eval_v1.json"
DEFAULT_AUDIT = ROOT / "results/P057_AMR_baseline_audit_v1.json"


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


def independent_predictions(
    training: list[tuple[int, float]], holdout_year: int, epsilon: float
) -> tuple[float, float, float]:
    years = np.asarray([year for year, _ in training], dtype=float)
    values = np.asarray([value for _, value in training], dtype=float)
    probabilities = np.clip(values / 100.0, epsilon, 1.0 - epsilon)
    logits = np.log(probabilities / (1.0 - probabilities))
    centered = years - years.mean()
    design = np.column_stack([np.ones_like(centered), centered])
    coefficients, _, _, _ = np.linalg.lstsq(design, logits, rcond=None)
    target = np.asarray([1.0, holdout_year - years.mean()], dtype=float)
    target_logit = float(target @ coefficients)
    trend = 100.0 / (1.0 + math.exp(-target_logit))
    return float(values[-1]), trend, float(coefficients[1])


def rebuild_rows(
    benchmark: dict[str, Any],
    snapshot: dict[str, Any],
    preflight: dict[str, Any],
) -> list[dict[str, Any]]:
    training_years = {int(year) for year in benchmark["data_contract"]["training_years"]}
    holdout_year = int(benchmark["data_contract"]["holdout_year"])
    indicators = set(benchmark["data_contract"]["indicator_codes"])
    minimum = int(benchmark["eligibility"]["minimum_observed_training_years"])
    epsilon = float(
        benchmark["baselines"]["country_specific_logit_time_trend"][
            "probability_clip_epsilon"
        ]
    )
    values_by_key: dict[tuple[str, str], dict[int, float]] = {}
    for row in snapshot["p057"]["records"]:
        key = (str(row["indicator_code"]), str(row["m49"]))
        values_by_key.setdefault(key, {})[int(row["year"])] = float(
            row["value_percent"]
        )
    metadata = {
        (str(row["indicator_code"]), str(row["m49"])): row
        for row in preflight["p057"]["coverage_matrix"]
        if row["indicator_code"] in indicators
    }
    rebuilt = []
    for (code, m49), values in values_by_key.items():
        if code not in indicators or holdout_year not in values:
            continue
        training = sorted(
            (year, value)
            for year, value in values.items()
            if year in training_years
        )
        if len(training) < minimum:
            continue
        locf, trend, slope = independent_predictions(
            training, holdout_year, epsilon
        )
        actual = values[holdout_year]
        meta = metadata[(code, m49)]
        rebuilt.append(
            {
                "indicator_code": code,
                "m49": m49,
                "iso3": str(meta["iso3"]),
                "entity": str(meta["entity"]),
                "completeness_stratum": str(meta["completeness_stratum"]),
                "training_years": [year for year, _ in training],
                "training_values_percent": [rounded(value) for _, value in training],
                "holdout_year": holdout_year,
                "observed_percent": rounded(actual),
                "predictions_percent": {
                    "locf": rounded(locf),
                    "country_logit": rounded(trend),
                },
                "errors_percent": {
                    "locf_signed": rounded(locf - actual),
                    "locf_absolute": rounded(abs(locf - actual)),
                    "country_logit_signed": rounded(trend - actual),
                    "country_logit_absolute": rounded(abs(trend - actual)),
                },
                "country_logit_slope_per_year": rounded(slope, 12),
            }
        )
    rebuilt.sort(key=lambda row: (row["indicator_code"], row["m49"]))
    return rebuilt


def metric_summary(rows: list[dict[str, Any]], baseline: str) -> dict[str, Any]:
    signed = np.asarray(
        [row["errors_percent"][f"{baseline}_signed"] for row in rows], dtype=float
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
        selected = [row for row in rows if row["indicator_code"] == code]
        output[f"{code}__overall"] = selected
        output[f"{code}__partial"] = [
            row for row in selected if row["completeness_stratum"] == "partial"
        ]
        output[f"{code}__dense"] = [
            row for row in selected if row["completeness_stratum"] == "dense"
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
            (max_numeric_difference(a, b) for a, b in zip(left, right, strict=True)),
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
    preflight_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    snapshot = read_json(snapshot_path)
    preflight = read_json(preflight_path)
    result = read_json(result_path)
    rebuilt = rebuild_rows(benchmark, snapshot, preflight)
    recorded = result["rows"]
    row_difference = max_numeric_difference(rebuilt, recorded)
    rebuilt_slices = slice_rows(rebuilt)
    metric_differences = []
    count_matches = True
    for label, selected in rebuilt_slices.items():
        recorded_slice = result["slices"].get(label)
        if recorded_slice is None or recorded_slice["row_count"] != len(selected):
            count_matches = False
            continue
        for baseline in ("locf", "country_logit"):
            expected = metric_summary(selected, baseline)
            observed = recorded_slice["baselines"][baseline]
            metric_differences.append(max_numeric_difference(expected, observed))
    max_metric_difference = max(metric_differences, default=math.inf)
    expected_keys = [
        (row["indicator_code"], row["m49"]) for row in rebuilt
    ]
    recorded_keys = [
        (row["indicator_code"], row["m49"]) for row in recorded
    ]
    checks = [
        check(
            "formal_result_passed",
            result["status"] == "pass",
            f"Formal result status is {result['status']}.",
        ),
        check(
            "protocol_commit_recorded",
            len(result["source"]["protocol_commit"]) >= 8,
            result["source"]["protocol_commit"],
        ),
        check(
            "row_identity_matches",
            expected_keys == recorded_keys,
            f"Compared {len(expected_keys)} ordered indicator-entity keys.",
        ),
        check(
            "independent_row_values_match",
            row_difference <= 1e-9,
            f"Maximum numeric difference {row_difference:.3e}.",
        ),
        check(
            "slice_counts_match",
            count_matches and set(rebuilt_slices) == set(result["slices"]),
            f"Compared {len(rebuilt_slices)} slices.",
        ),
        check(
            "independent_metrics_match",
            max_metric_difference <= 1e-9,
            f"Maximum metric difference {max_metric_difference:.3e}.",
        ),
        check(
            "all_rows_retained",
            len(rebuilt) == 141 == result["summary"]["evaluated_row_count"],
            f"Observed {len(rebuilt)} rows.",
        ),
        check(
            "candidate_not_executed",
            result["summary"]["candidate_executed"] is False,
            "The result establishes denominators only.",
        ),
        check(
            "holdout_is_2023",
            all(row["holdout_year"] == 2023 for row in rebuilt),
            "All audited targets are 2023.",
        ),
        check(
            "training_precedes_holdout",
            all(max(row["training_years"]) <= 2022 for row in rebuilt),
            "All audited training rows stop by 2022.",
        ),
    ]
    passed = sum(item["passed"] for item in checks)
    return {
        "schema_version": "p057_amr_baseline_audit_v1",
        "status": "pass" if passed == len(checks) else "fail",
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "source_snapshot": str(snapshot_path.relative_to(ROOT)),
            "source_snapshot_sha256": sha256_path(snapshot_path),
            "upstream_preflight": str(preflight_path.relative_to(ROOT)),
            "upstream_preflight_sha256": sha256_path(preflight_path),
            "formal_result": str(result_path.relative_to(ROOT)),
            "formal_result_sha256": sha256_path(result_path),
            "audit_tool": str(Path(__file__).resolve().relative_to(ROOT)),
            "audit_tool_sha256": sha256_path(Path(__file__).resolve()),
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "summary": {
            "check_count": len(checks),
            "passed_checks": passed,
            "failed_checks": [item["name"] for item in checks if not item["passed"]],
            "audited_rows": len(rebuilt),
            "max_row_numeric_difference": rounded(row_difference, 14),
            "max_metric_numeric_difference": rounded(max_metric_difference, 14),
        },
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--preflight", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    audit = build_audit(
        args.benchmark, args.snapshot, args.preflight, args.result
    )
    text = pretty_json(audit)
    if args.check_only:
        if args.audit.read_text(encoding="utf-8") != text:
            raise SystemExit("audit replay mismatch")
        print(
            json.dumps(
                {
                    "status": audit["status"],
                    "passed_checks": audit["summary"]["passed_checks"],
                    "check_count": audit["summary"]["check_count"],
                    "audited_rows": audit["summary"]["audited_rows"],
                    "byte_identical": True,
                },
                sort_keys=True,
            )
        )
        return
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": audit["status"],
                "passed_checks": audit["summary"]["passed_checks"],
                "check_count": audit["summary"]["check_count"],
                "audited_rows": audit["summary"]["audited_rows"],
                "audit": str(args.audit),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
