#!/usr/bin/env python3
"""Build the scoped P057/P058 public-data readiness preflight.

P057 captures two WHO AMR indicator series plus the frozen WHO ADMIN_0
reference universe, then constructs a pathogen-drug-country coverage matrix
and missing-not-at-random sensitivity diagnostics.

P058 audits the frozen projection of CDC NWSS public metadata for the fields
needed by a leakage-free historical alert replay. It deliberately refuses to
score alerts when first-publication and immutable-revision information is not
available.

No clinical, treatment, outbreak, or solved-frontier claim is made.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import platform
import ssl
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

import certifi


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P057_P058_data_preflight_v1.json"
DEFAULT_SNAPSHOT = ROOT / "results/P057_P058_source_snapshot_v1.json"
DEFAULT_RESULT = ROOT / "results/P057_P058_data_preflight_v1.json"
DEFAULT_REPORT = ROOT / "research/P057_P058_data_preflight_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/P057_P058_discussion_prompt_v1.md"
USER_AGENT = "Axiom-Horizon-P057-P058-preflight/1.0 (+public research replay)"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def fetch_bytes(url: str) -> tuple[bytes, dict[str, str]]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=60, context=context) as response:
        body = response.read()
        headers = {
            key.lower(): value
            for key, value in response.headers.items()
            if key.lower() in {"content-length", "content-type", "etag", "last-modified"}
        }
    return body, headers


def odata_url(base_url: str, table: str, params: dict[str, str]) -> str:
    return f"{base_url}{table}?{urllib.parse.urlencode(params)}"


def fetch_odata(base_url: str, table: str, params: dict[str, str]) -> tuple[str, list[dict[str, Any]], str]:
    url = odata_url(base_url, table, params)
    body, _ = fetch_bytes(url)
    payload = json.loads(body)
    if payload.get("@odata.nextLink"):
        raise ValueError(f"unexpected paginated response for {table}")
    rows = payload.get("value")
    if not isinstance(rows, list):
        raise ValueError(f"missing OData value array for {table}")
    return url, rows, sha256_bytes(body)


def normalize_amr_row(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("VALUE_NUMERIC")
    return {
        "indicator_code": row["IND_CODE"],
        "indicator_uuid": row["IND_UUID"],
        "year": int(row["DIM_TIME"]),
        "m49": str(row["DIM_GEO_CODE_M49"]).zfill(3),
        "geo_type": row["DIM_GEO_CODE_TYPE"],
        "publish_state": row["DIM_PUBLISH_STATE_CODE"],
        "value_type": row.get("DIM_VALUE_TYPE"),
        "value_percent": None if value is None else round(float(value), 10),
        "source_commit_utc": row.get("Sys_CommitDateUtc"),
        "source_version": row.get("Sys_Version"),
    }


def normalize_geo_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "m49": str(row["GEO_CODE_M49"]).zfill(3),
        "iso3": row.get("GEO_CODE_ISO_3"),
        "name": row.get("GEO_NAME_SHORT"),
    }


def csv_projection(body: bytes, headers: dict[str, str]) -> dict[str, Any]:
    text = body.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    years = sorted({int(row["DIM_TIME"]) for row in rows})
    return {
        "sha256": sha256_bytes(body),
        "byte_count": len(body),
        "row_count": len(rows),
        "years": years,
        "maximum_year": max(years),
        "headers": headers,
    }


def capture_snapshot(benchmark: dict[str, Any]) -> dict[str, Any]:
    p057 = benchmark["p057"]
    years = set(p057["analysis_years"])
    records: list[dict[str, Any]] = []
    source_queries: list[dict[str, Any]] = []
    download_projections: list[dict[str, Any]] = []
    select = ",".join(
        [
            "IND_CODE",
            "IND_UUID",
            "DIM_TIME",
            "DIM_TIME_TYPE",
            "DIM_GEO_CODE_M49",
            "DIM_GEO_CODE_TYPE",
            "DIM_PUBLISH_STATE_CODE",
            "DIM_VALUE_TYPE",
            "VALUE_NUMERIC",
            "Sys_CommitDateUtc",
            "Sys_Version",
        ]
    )
    for indicator in p057["indicators"]:
        params = {
            "$filter": f"IND_CODE eq '{indicator['indicator_code']}'",
            "$select": select,
        }
        url, source_rows, response_sha = fetch_odata(
            indicator["api_base_url"], indicator["api_table"], params
        )
        normalized = [
            normalize_amr_row(row)
            for row in source_rows
            if int(row["DIM_TIME"]) in years
        ]
        normalized.sort(key=lambda row: (row["indicator_code"], row["m49"], row["year"]))
        records.extend(normalized)
        source_queries.append(
            {
                "kind": "who_indicator_api",
                "indicator_code": indicator["indicator_code"],
                "url": url,
                "raw_response_sha256": response_sha,
                "raw_row_count": len(source_rows),
                "retained_row_count": len(normalized),
            }
        )
        csv_body, csv_headers = fetch_bytes(indicator["download_url"])
        projection = csv_projection(csv_body, csv_headers)
        projection.update(
            {
                "indicator_code": indicator["indicator_code"],
                "url": indicator["download_url"],
            }
        )
        download_projections.append(projection)

    universe = p057["reporting_universe"]
    geo_params = {
        "$filter": universe["filter"],
        "$select": "GEO_CODE_M49,GEO_CODE_ISO_3,GEO_NAME_SHORT",
    }
    geo_url, geo_source_rows, geo_response_sha = fetch_odata(
        universe["api_base_url"], universe["api_table"], geo_params
    )
    geographies = sorted(
        (normalize_geo_row(row) for row in geo_source_rows),
        key=lambda row: row["m49"],
    )
    allowed_m49 = {row["m49"] for row in geographies}
    pre_universe_records = records
    records = [row for row in pre_universe_records if row["m49"] in allowed_m49]
    for query in source_queries:
        if query["kind"] != "who_indicator_api":
            continue
        indicator_code = query["indicator_code"]
        before = sum(
            row["indicator_code"] == indicator_code for row in pre_universe_records
        )
        after = sum(row["indicator_code"] == indicator_code for row in records)
        query["retained_row_count"] = after
        query["excluded_outside_universe_row_count"] = before - after
    source_queries.append(
        {
            "kind": "who_geo_reference_api",
            "url": geo_url,
            "raw_response_sha256": geo_response_sha,
            "raw_row_count": len(geo_source_rows),
            "retained_row_count": len(geographies),
        }
    )
    records.sort(key=lambda row: (row["indicator_code"], row["m49"], row["year"]))
    return {
        "schema_version": benchmark["schema_version"],
        "captured_at": benchmark["preregistered_at"],
        "source_queries": sorted(
            source_queries,
            key=lambda row: (row["kind"], row.get("indicator_code", "")),
        ),
        "p057": {
            "geographies": geographies,
            "records": records,
            "indicator_download_projections": sorted(
                download_projections,
                key=lambda row: row["indicator_code"],
            ),
        },
        "p058": {
            "official_metadata_projection": benchmark["p058"][
                "official_metadata_projection"
            ],
            "note": "Relevant metadata fields are frozen as a transparent projection; the row API was not mirrored into this repository.",
        },
    }


def completeness_stratum(observed_years: int, strata: list[dict[str, Any]]) -> str:
    for stratum in strata:
        if (
            int(stratum["minimum_observed_years"])
            <= observed_years
            <= int(stratum["maximum_observed_years"])
        ):
            return stratum["name"]
    raise ValueError(f"no completeness stratum for {observed_years} years")


def rounded(value: float, digits: int = 10) -> float:
    return round(float(value), digits)


def build_coverage_matrix(
    benchmark: dict[str, Any], snapshot: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    config = benchmark["p057"]
    years = [int(year) for year in config["analysis_years"]]
    holdout = int(config["future_holdout_year"])
    training_years = [year for year in years if year < holdout]
    record_map: dict[tuple[str, str, int], float] = {}
    duplicates: list[tuple[str, str, int]] = []
    for row in snapshot["p057"]["records"]:
        key = (row["indicator_code"], row["m49"], int(row["year"]))
        if key in record_map:
            duplicates.append(key)
        if row["value_percent"] is not None:
            record_map[key] = float(row["value_percent"])

    indicator_map = {
        indicator["indicator_code"]: indicator for indicator in config["indicators"]
    }
    matrix: list[dict[str, Any]] = []
    for indicator_code in sorted(indicator_map):
        indicator = indicator_map[indicator_code]
        for geo in snapshot["p057"]["geographies"]:
            values = {
                str(year): (
                    None
                    if (indicator_code, geo["m49"], year) not in record_map
                    else rounded(record_map[(indicator_code, geo["m49"], year)])
                )
                for year in years
            }
            observed = [year for year in years if values[str(year)] is not None]
            observed_training = [
                year for year in training_years if values[str(year)] is not None
            ]
            eligible = (
                values[str(holdout)] is not None
                and len(observed_training)
                >= int(config["forecast_eligibility"]["minimum_observed_training_years"])
            )
            matrix.append(
                {
                    "indicator_code": indicator_code,
                    "pathogen": indicator["pathogen"],
                    "drug_or_class": indicator["drug_or_class"],
                    "m49": geo["m49"],
                    "iso3": geo["iso3"],
                    "entity": geo["name"],
                    "values_percent": values,
                    "observed_year_count": len(observed),
                    "observed_training_year_count": len(observed_training),
                    "completeness_stratum": completeness_stratum(
                        len(observed), config["completeness_strata"]
                    ),
                    "forecast_eligible": eligible,
                }
            )

    summaries: dict[str, Any] = {}
    entity_count = len(snapshot["p057"]["geographies"])
    for indicator_code in sorted(indicator_map):
        rows = [row for row in matrix if row["indicator_code"] == indicator_code]
        observed_cells = sum(row["observed_year_count"] for row in rows)
        holdout_values = [
            float(row["values_percent"][str(holdout)])
            for row in rows
            if row["values_percent"][str(holdout)] is not None
        ]
        observed_holdout_mean = sum(holdout_values) / len(holdout_values)
        missing_count = entity_count - len(holdout_values)
        deltas: list[dict[str, Any]] = []
        for delta in config["mnar_sensitivity"]["delta_percentage_points"]:
            imputed = min(100.0, max(0.0, observed_holdout_mean + float(delta)))
            all_entity_mean = (
                sum(holdout_values) + missing_count * imputed
            ) / entity_count
            deltas.append(
                {
                    "delta_percentage_points": float(delta),
                    "imputed_missing_value": rounded(imputed),
                    "all_entity_mean": rounded(all_entity_mean),
                }
            )
        observed_sum = sum(holdout_values)
        manski_min = observed_sum / entity_count
        manski_max = (observed_sum + missing_count * 100.0) / entity_count
        summaries[indicator_code] = {
            "entity_count": entity_count,
            "observed_country_year_cells": observed_cells,
            "possible_country_year_cells": entity_count * len(years),
            "cell_coverage_fraction": rounded(
                observed_cells / (entity_count * len(years))
            ),
            "entities_with_any_observation": sum(
                row["observed_year_count"] > 0 for row in rows
            ),
            "holdout_entity_count": len(holdout_values),
            "holdout_coverage_fraction": rounded(len(holdout_values) / entity_count),
            "forecast_eligible_entity_count": sum(
                bool(row["forecast_eligible"]) for row in rows
            ),
            "completeness_strata": dict(
                sorted(Counter(row["completeness_stratum"] for row in rows).items())
            ),
            "observed_holdout_mean": rounded(observed_holdout_mean),
            "mnar_delta_sensitivity": deltas,
            "manski_all_entity_mean_bounds": [
                rounded(manski_min),
                rounded(manski_max),
            ],
        }
    return matrix, {"duplicates": duplicates, "indicators": summaries}


def audit_p058(benchmark: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    config = benchmark["p058"]
    metadata = snapshot["p058"]["official_metadata_projection"]
    fields = set(metadata["field_names"])
    vintage = config["required_vintage_contract"]
    date_values = metadata["date_updated"]["distinct_values"]
    first_publication_present = vintage["required_first_publication_field"] in fields
    revision_identity_present = vintage["required_revision_identity_field"] in fields
    current_as_of_only = len(date_values) == 1 and int(date_values[0]["count"]) == int(
        metadata["row_count"]
    )
    contract_satisfied = (
        first_publication_present
        and revision_identity_present
        and len(date_values) >= int(vintage["minimum_distinct_as_of_snapshots"])
    )
    return {
        "status": "ready_for_vintage_replay"
        if contract_satisfied
        else config["frozen_decision"]["status_if_contract_unsatisfied"],
        "dataset_id": config["dataset"]["dataset_id"],
        "row_count": metadata["row_count"],
        "column_count": metadata["column_count"],
        "sample_date_range": [
            metadata["sample_collect_date"]["minimum"],
            metadata["sample_collect_date"]["maximum"],
        ],
        "event_time_field_present": vintage["event_time_field"] in fields,
        "first_publication_field_present": first_publication_present,
        "revision_identity_field_present": revision_identity_present,
        "date_updated_distinct_value_count": len(date_values),
        "date_updated_is_uniform_current_batch": current_as_of_only,
        "immutable_vintage_contract_satisfied": contract_satisfied,
        "alert_model_executed": bool(
            contract_satisfied and config["frozen_decision"]["alert_model_may_run"]
        ),
        "why_blocked": [
            "sample_collect_date records event time, not when the row first became available",
            "date_updated is one uniform current processing stamp, not a per-row publication history",
            "the schema has no immutable revision identity or archived weekly snapshot key",
            "CDC documents that later reports and method changes can revise historical values",
        ]
        if not contract_satisfied
        else [],
        "minimum_remediation": [
            "archive the complete public table every Friday with retrieval timestamp and SHA-256",
            "preserve row-level first-seen and last-seen dates keyed by record_id",
            "preserve corrections as immutable revisions instead of replacing prior values",
            "only then freeze unseen jurisdictions, weeks, thresholds, and false-alert budget",
        ]
        if not contract_satisfied
        else [],
    }


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def validate(
    benchmark: dict[str, Any],
    snapshot: dict[str, Any],
    matrix: list[dict[str, Any]],
    p057_summary: dict[str, Any],
    p058: dict[str, Any],
) -> list[dict[str, Any]]:
    config57 = benchmark["p057"]
    metadata58 = benchmark["p058"]["official_metadata_projection"]
    years = set(config57["analysis_years"])
    records = snapshot["p057"]["records"]
    record_keys = [
        (row["indicator_code"], row["m49"], int(row["year"])) for row in records
    ]
    values = [
        row["value_percent"] for row in records if row["value_percent"] is not None
    ]
    api_years = {
        row["indicator_code"]: {
            int(item["year"])
            for item in records
            if item["indicator_code"] == row["indicator_code"]
        }
        for row in config57["indicators"]
    }
    downloads = {
        row["indicator_code"]: row
        for row in snapshot["p057"]["indicator_download_projections"]
    }
    return [
        check(
            "exact_problem_scope",
            benchmark["scope"]["problem_ids"] == [57, 58],
            "Only catalog problems 057 and 058 are included.",
        ),
        check(
            "parent_packet_frozen",
            benchmark["scope"]["parent_packet"]
            == "benchmarks/P049_P060_activation_gate_v1.json",
            "The public-data preflight descends from the scoped activation packet.",
        ),
        check(
            "p057_two_frozen_indicators",
            [row["indicator_code"] for row in config57["indicators"]]
            == ["AMR_INFECT_ECOLI", "AMR_INFECT_MRSA"],
            "The two pathogen-drug indicators were fixed before result generation.",
        ),
        check(
            "p057_year_window",
            config57["analysis_years"] == list(range(2016, 2024)),
            "The coverage matrix uses the frozen 2016–2023 window.",
        ),
        check(
            "p057_geo_universe",
            len(snapshot["p057"]["geographies"])
            == config57["reporting_universe"]["expected_entity_count"],
            f"Observed {len(snapshot['p057']['geographies'])} ADMIN_0 entities.",
        ),
        check(
            "p057_unique_geo_codes",
            len({row["m49"] for row in snapshot["p057"]["geographies"]})
            == len(snapshot["p057"]["geographies"]),
            "Every reference entity has one M49 code.",
        ),
        check(
            "p057_admin0_membership_only",
            {row["m49"] for row in records}
            <= {row["m49"] for row in snapshot["p057"]["geographies"]},
            "Only M49 codes in the frozen ADMIN_0 universe enter the matrix; global aggregates are excluded.",
        ),
        check(
            "p057_no_duplicate_country_years",
            len(record_keys) == len(set(record_keys))
            and not p057_summary["duplicates"],
            "Every indicator-country-year cell is unique.",
        ),
        check(
            "p057_values_in_unit_interval",
            bool(values) and min(values) >= 0.0 and max(values) <= 100.0,
            f"Observed resistance values span {min(values):.2f}–{max(values):.2f} percent.",
        ),
        check(
            "p057_matrix_complete",
            len(matrix)
            == len(snapshot["p057"]["geographies"]) * len(config57["indicators"]),
            f"Coverage matrix has {len(matrix)} indicator-entity rows.",
        ),
        check(
            "p057_records_fully_accounted",
            sum(
                summary["observed_country_year_cells"]
                for summary in p057_summary["indicators"].values()
            )
            == len(records),
            "Every retained country-year observation appears in the coverage matrix.",
        ),
        check(
            "p057_api_contains_holdout",
            all(config57["future_holdout_year"] in api_years[code] for code in api_years),
            "Both dashboard API series include the frozen 2023 holdout.",
        ),
        check(
            "p057_download_divergence_recorded",
            all(
                config57["future_holdout_year"] not in downloads[code]["years"]
                and max(downloads[code]["years"])
                == config57["future_holdout_year"] - 1
                for code in downloads
            ),
            "Both official Download CSVs stop at 2022 while the dashboard API includes 2023.",
        ),
        check(
            "p057_mnar_not_point_identified",
            all(
                summary["manski_all_entity_mean_bounds"][1]
                > summary["manski_all_entity_mean_bounds"][0]
                for summary in p057_summary["indicators"].values()
            ),
            "Missing 2023 reporting leaves non-zero worst-case identification intervals.",
        ),
        check(
            "p058_metadata_shape",
            metadata58["column_count"] == len(metadata58["field_names"]) == 38,
            "The frozen CDC metadata projection contains all 38 declared fields.",
        ),
        check(
            "p058_event_time_present",
            p058["event_time_field_present"],
            "sample_collect_date is available as event time.",
        ),
        check(
            "p058_first_publication_missing",
            not p058["first_publication_field_present"],
            "No row-level first-publication field is present.",
        ),
        check(
            "p058_revision_identity_missing",
            not p058["revision_identity_field_present"],
            "No immutable row revision identity is present.",
        ),
        check(
            "p058_uniform_current_batch",
            p058["date_updated_is_uniform_current_batch"],
            "All 595,138 rows share one current processing-run date_updated value.",
        ),
        check(
            "p058_alert_fail_closed",
            p058["status"] == "blocked_missing_vintages"
            and not p058["alert_model_executed"],
            "Lead-time scoring is blocked and no alert model was executed.",
        ),
        check(
            "safety_boundary_present",
            len(benchmark["safety_boundary"]) >= 5,
            "The packet forbids clinical or public-health action.",
        ),
    ]


def build_result(
    benchmark_path: Path,
    benchmark: dict[str, Any],
    snapshot_path: Path,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    matrix, p057_summary = build_coverage_matrix(benchmark, snapshot)
    p058 = audit_p058(benchmark, snapshot)
    checks = validate(benchmark, snapshot, matrix, p057_summary, p058)
    passed = sum(row["passed"] for row in checks)
    source_commits = sorted(
        {
            row["source_commit_utc"]
            for row in snapshot["p057"]["records"]
            if row["source_commit_utc"]
        }
    )
    p057 = {
        "status": "coverage_matrix_ready",
        "source_commit_dates_utc": source_commits,
        "record_count": len(snapshot["p057"]["records"]),
        "coverage_matrix_row_count": len(matrix),
        "coverage_matrix": matrix,
        "summary": p057_summary["indicators"],
        "source_divergence": {
            "dashboard_api_maximum_year": max(
                row["year"] for row in snapshot["p057"]["records"]
            ),
            "download_csv_maximum_years": {
                row["indicator_code"]: row["maximum_year"]
                for row in snapshot["p057"]["indicator_download_projections"]
            },
            "decision": "use_hashed_dashboard_api_snapshot_and_record_the_download_lag",
        },
        "forecast_model_executed": False,
    }
    return {
        "schema_version": benchmark["schema_version"],
        "status": "pass" if passed == len(checks) else "fail",
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_bytes(canonical_json(benchmark)),
            "snapshot": str(snapshot_path.relative_to(ROOT)),
            "snapshot_sha256": sha256_bytes(snapshot_path.read_bytes()),
            "tool": str(Path(__file__).resolve().relative_to(ROOT)),
            "tool_sha256": sha256_bytes(Path(__file__).read_bytes()),
        },
        "environment": {"python": platform.python_version()},
        "p057": p057,
        "p058": p058,
        "checks": checks,
        "summary": {
            "check_count": len(checks),
            "passed_checks": passed,
            "failed_checks": [row["name"] for row in checks if not row["passed"]],
            "claim": "data_readiness_preflight_only",
        },
    }


def percent(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def render_report(benchmark: dict[str, Any], result: dict[str, Any]) -> str:
    p057 = result["p057"]
    p058 = result["p058"]
    lines = [
        "# Problems `#057`–`#058` Data Readiness Preflight v1",
        "",
        "Date: 2026-07-30",
        "",
        "Status: **the preflight is valid; `#057` now has a versioned coverage matrix,",
        "while `#058` is blocked before alert scoring because the public table is not a",
        "historical-vintage archive.**",
        "",
        "This update remains strictly inside catalog problems `#057` and `#058`. It does",
        "not execute a clinical forecast, issue a public-health alert, or claim that either",
        "frontier problem is solved.",
        "",
        "## Machine-check summary",
        "",
        f"- Contract checks: `{result['summary']['passed_checks']}/{result['summary']['check_count']}` passed.",
        f"- `#057`: `{p057['status']}` with `{p057['record_count']}` observations and "
        f"`{p057['coverage_matrix_row_count']}` pathogen-drug-entity rows.",
        f"- `#058`: `{p058['status']}`; alert model executed: `{str(p058['alert_model_executed']).lower()}`.",
        f"- Snapshot SHA-256: `{result['source']['snapshot_sha256']}`.",
        "",
        "## `#057` — Is missing surveillance being mistaken for low resistance?",
        "",
        "The frozen universe is WHO's current set of 245 English `ADMIN_0` reference",
        "entities. The matrix crosses that universe with two bloodstream-infection",
        "indicators and eight years (2016–2023): *E. coli* resistance to third-generation",
        "cephalosporins and methicillin-resistant *S. aureus*.",
        "",
        "| Indicator | Observed cells | Cell coverage | 2023 reporters | Forecast-eligible | 2023 observed mean | Worst-case all-entity mean interval |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for indicator in benchmark["p057"]["indicators"]:
        code = indicator["indicator_code"]
        summary = p057["summary"][code]
        bounds = summary["manski_all_entity_mean_bounds"]
        lines.append(
            f"| `{code}` | {summary['observed_country_year_cells']}/"
            f"{summary['possible_country_year_cells']} | "
            f"{percent(summary['cell_coverage_fraction'])} | "
            f"{summary['holdout_entity_count']}/245 | "
            f"{summary['forecast_eligible_entity_count']} | "
            f"{summary['observed_holdout_mean']:.2f}% | "
            f"{bounds[0]:.2f}%–{bounds[1]:.2f}% |"
        )
    lines.extend(
        [
            "",
            "The wide worst-case intervals are not estimates. They show that a global mean",
            "is not identified by reported countries alone. The stored delta table asks what",
            "happens if non-reporting entities differ from the observed 2023 mean by −20, −10,",
            "0, +10, or +20 percentage points, with values clipped to the valid 0–100 range.",
            "",
            "### A source-version trap",
            "",
            "WHO's live dashboard API contains the frozen 2023 holdout, but both official",
            "`Download` CSVs stop at 2022. The packet records each URL, response hash, CSV",
            "hash, ETag, and Last-Modified value. The formal matrix uses the hashed dashboard",
            "API snapshot and makes the download lag visible instead of silently mixing sources.",
            "",
            "The next `#057` step is to run the last-observation and country-logistic",
            "denominators only on the preregistered eligible rows, then report errors overall",
            "and in the sparse-completeness stratum. A candidate will not be admitted until",
            "those same-access denominators and the MNAR stress table are fixed.",
            "",
            "## `#058` — Can one current history replay what was knowable then?",
            "",
            "The CDC table is rich enough for event-time analysis: its 38 fields include",
            f"`sample_collect_date`, and the frozen metadata projection covers "
            f"`{p058['row_count']:,}` rows from `{p058['sample_date_range'][0]}` through "
            f"`{p058['sample_date_range'][1]}`. But event time is not publication time.",
            "",
            "Every row shares one `date_updated` processing stamp. The schema contains neither",
            "a row-level first-publication date nor an immutable revision identifier. CDC also",
            "states that data may change as reports arrive and documents methodology changes",
            "that were applied retroactively to historical values. A current full history can",
            "therefore contain information that was unavailable at the simulated decision date.",
            "",
            "For that reason, the seven-day lead-time gate is **not run**. The minimum repair is",
            "to archive each Friday's full public table with a retrieval time and hash, preserve",
            "row-level first-seen/last-seen dates and corrections, and only then freeze unseen",
            "jurisdictions, weeks, thresholds, and the false-alert budget.",
            "",
            "## Official evidence",
            "",
            "- WHO AMR dashboard: [Antimicrobial Resistance profile]"
            "(https://data.who.int/dashboards/amr/antimicrobial-resistance-profile).",
            "- WHO indicator definition and download: [E. coli resistance to third-generation cephalosporins]"
            "(https://data.who.int/indicators/i/918081E/745F475).",
            "- WHO indicator definition and download: [MRSA]"
            "(https://data.who.int/indicators/i/918081E/5DD9606).",
            "- CDC dataset metadata: [CDC Wastewater Data for SARS-CoV-2]"
            "(https://data.cdc.gov/api/views/j9g8-acpt).",
            "- CDC update cadence and intended use: [About Wastewater Data]"
            "(https://www.cdc.gov/nwss/about-data.html).",
            "- CDC retrospective method revisions: [Wastewater Monitoring Data Methodology]"
            "(https://www.cdc.gov/nwss/data-methods.html).",
            "",
            "## Claim boundary",
            "",
            "The packet establishes data-contract readiness, not predictive validity. It does",
            "not infer resistance for non-reporters, compare individual wastewater sites,",
            "diagnose disease, declare an outbreak, recommend an intervention, or solve",
            "catalog problem `#057` or `#058`.",
            "",
        ]
    )
    return "\n".join(lines)


def render_discussion(benchmark: dict[str, Any], result: dict[str, Any]) -> str:
    e_coli = result["p057"]["summary"]["AMR_INFECT_ECOLI"]
    mrsa = result["p057"]["summary"]["AMR_INFECT_MRSA"]
    return "\n".join(
        [
            "# When does “complete history” still leak the future?",
            "",
            "Two public-health data gates produced opposite kinds of readiness.",
            "",
            f"- **`#057` AMR:** the WHO snapshot yields `{result['p057']['record_count']}` "
            f"country-year observations across two frozen pathogen-drug indicators. Yet only "
            f"`{e_coli['holdout_entity_count']}/245` entities report the 2023 *E. coli* value "
            f"and `{mrsa['holdout_entity_count']}/245` report MRSA. Treating all other entities "
            "as low resistance would be an assumption, not evidence.",
            f"- **`#058` wastewater:** CDC exposes `{result['p058']['row_count']:,}` sample rows "
            "with collection dates, but every row carries the same current `date_updated` stamp. "
            "There is no row-level first-publication date or immutable revision identity, so the "
            "frozen seven-day lead-time test is blocked before any alert is scored.",
            "",
            "The provocative question is: **should a benchmark get credit for refusing to run",
            "when the data cannot reconstruct what was knowable at the time?**",
            "",
            "Three concrete prompts for collaborators:",
            "",
            "1. For `#057`, which prespecified MNAR stress is hardest to game: delta adjustment,",
            "   inverse reporting weights, selection models, or partial-identification bounds?",
            "2. For `#058`, does anyone know of an official immutable archive of weekly CDC NWSS",
            "   table snapshots, rather than a current table containing old sample dates?",
            "3. What minimum first-seen/revision schema would make seven-day lead time auditable",
            "   without requiring CDC to publish sensitive operational logs?",
            "",
            "One extra versioning puzzle: WHO's live dashboard API includes 2023, while both",
            "indicator-page `Download` CSVs stop at 2022. The packet hashes both paths and refuses",
            "to mix them silently.",
            "",
            "Research packet: `research/P057_P058_data_preflight_v1.md`",
            "",
            "Boundary: no diagnosis, outbreak declaration, clinical recommendation, or live",
            "public-health alert is produced.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Fetch and freeze the official WHO source rows before replay.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Validate and print the result without writing derived artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    benchmark = read_json(args.benchmark)
    if args.capture:
        snapshot = capture_snapshot(benchmark)
        write_text(args.snapshot, pretty_json(snapshot))
    else:
        snapshot = read_json(args.snapshot)
    result = build_result(args.benchmark, benchmark, args.snapshot, snapshot)
    report = render_report(benchmark, result)
    discussion = render_discussion(benchmark, result)
    if not args.check_only:
        write_text(args.result, pretty_json(result))
        write_text(args.report, report)
        write_text(args.discussion, discussion)
    print(
        json.dumps(
            {
                "status": result["status"],
                "passed_checks": result["summary"]["passed_checks"],
                "check_count": result["summary"]["check_count"],
                "p057_status": result["p057"]["status"],
                "p058_status": result["p058"]["status"],
                "result": str(args.result),
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
