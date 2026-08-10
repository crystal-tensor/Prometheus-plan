#!/usr/bin/env python3
"""Independently audit the frozen P059 HCP-YA 2025 public packet."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P059_hcp_ya2025_family_qc_denominator_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P059_hcp_ya2025_family_qc_source_v1"
DEFAULT_RESULT = ROOT / "results/P059_hcp_ya2025_family_qc_denominator_v1.json"
DEFAULT_AUDIT = ROOT / "results/P059_hcp_ya2025_family_qc_audit_v1.json"
CAPTURE_MANIFEST = "capture_manifest.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def folded(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def contains(text: str, *phrases: str) -> bool:
    value = folded(text)
    return all(folded(phrase) in value for phrase in phrases)


def suffix(source_format: str) -> str:
    return "csv" if source_format == "csv" else "txt"


def load_text(source_dir: Path, name: str, source_format: str) -> str:
    path = source_dir / f"{name}.{suffix(source_format)}.gz"
    return gzip.decompress(path.read_bytes()).decode("utf-8", errors="replace")


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def build_audit(
    benchmark_path: Path, source_dir: Path, result_path: Path
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    capture = read_json(source_dir / CAPTURE_MANIFEST)
    result = read_json(result_path)
    sources = {
        name: load_text(source_dir, name, spec["format"])
        for name, spec in benchmark["sources"].items()
    }
    capture_by_name = {entry["name"]: entry for entry in capture["sources"]}
    source_rows: list[dict[str, Any]] = []
    source_valid = len(capture_by_name) == len(benchmark["sources"]) == 15
    for name, spec in benchmark["sources"].items():
        path = source_dir / f"{name}.{suffix(spec['format'])}.gz"
        entry = capture_by_name.get(name, {})
        gzip_hash = sha256_path(path)
        normalized_hash = sha256_bytes(gzip.decompress(path.read_bytes()))
        valid = (
            entry.get("format") == spec["format"]
            and entry.get("requested_url") == spec["url"]
            and entry.get("gzip_sha256") == gzip_hash
            and entry.get("normalized_sha256") == normalized_hash
            and bool(re.fullmatch(r"[0-9a-f]{64}", entry.get("raw_sha256", "")))
        )
        if spec["format"] == "pdf":
            valid = valid and entry.get("pdf_pages") == 121
        source_valid = source_valid and valid
        source_rows.append(
            {
                "name": name,
                "raw_sha256": entry.get("raw_sha256"),
                "normalized_sha256": normalized_hash,
                "gzip_sha256": gzip_hash,
                "valid": valid,
            }
        )

    dictionary = list(
        csv.DictReader(io.StringIO(sources["data_dictionary"], newline=""))
    )
    fields = {row.get("columnHeader", "") for row in dictionary}
    by_field = {
        field: [row for row in dictionary if row.get("columnHeader") == field]
        for field in fields
    }
    endpoint = by_field.get("CogFluidComp_Unadj", [{}])[0]
    family = by_field.get("Family_ID", [{}])[0]
    thickness = sorted(
        field
        for field in fields
        if field.startswith(("FS_L_", "FS_R_")) and field.endswith("_Thck")
    )

    retest_reader = csv.reader(
        io.StringIO(sources["retest_interval_csv"], newline="")
    )
    next(retest_reader, None)
    retest_pairs = [
        (row[0].strip(), int(row[1].strip()))
        for row in retest_reader
        if len(row) >= 2 and row[0].strip().isdigit() and row[1].strip().isdigit()
    ]
    retest_bins = Counter(month for _, month in retest_pairs)
    expected_bins = Counter(
        {
            int(month): count
            for month, count in benchmark["split_and_evaluation_contract"]["retest_role"]["legacy_month_bin_counts"].items()
        }
    )
    release = sources["release_2025"].replace(",", "")
    release_index = sources["data_releases"].replace(",", "")
    qc = sources["qc_issues"]
    known = sources["known_issues"]
    appendix = sources["appendix_iii"]
    mmp = sources["mmp_article"]
    frozen = benchmark["frozen_manifest"]
    connectome = benchmark["frozen_connectome_candidate"]
    evaluation = benchmark["split_and_evaluation_contract"]
    decision = benchmark["readiness_decision"]
    required_fields = set(benchmark["dictionary_expectations"]["required_fields"])
    exact_run_products = [
        f"rfMRI_{run}_Atlas_MSMAll_hp2000_clean_rclean_tclean.dtseries.nii"
        for run in connectome["runs"]
    ]
    independent = {
        "release_counts": {
            "processed": 1071 if "1071 subjects" in release else None,
            "imaging": 1113 if "1113 subjects" in release else None,
            "phenotypic": 1206 if "1206" in release_index else None,
            "processed_retest": 45 if "45 retest subjects" in release else None,
        },
        "dictionary_rows": len(dictionary),
        "dictionary_columns": list(dictionary[0]) if dictionary else [],
        "required_fields_present": len(required_fields & fields),
        "thickness_fields": len(thickness),
        "legacy_retest_subjects": len({subject for subject, _ in retest_pairs}),
        "legacy_retest_bins": {str(k): retest_bins[k] for k in sorted(retest_bins)},
        "appendix_pages": capture_by_name["appendix_iii"].get("pdf_pages"),
        "motion_file_counts": {
            name: appendix.count(name)
            for name in [
                "Movement_AbsoluteRMS_mean.txt",
                "Movement_RelativeRMS_mean.txt",
            ]
        },
        "per_run_products": {
            name: name in appendix for name in exact_run_products
        },
        "undirected_edges": 360 * 359 // 2,
        "model_executed": False,
    }
    checks = [
        check(
            "audit_scope",
            benchmark["scope"]["included_catalog_problem_ids"] == [59]
            and result["scope"]["included_catalog_problem_ids"] == [59],
            "Independent audit is restricted to catalog problem #059.",
        ),
        check(
            "benchmark_hash",
            sha256_path(benchmark_path)
            == capture["benchmark_sha256"]
            == result["source"]["benchmark_sha256"],
            sha256_path(benchmark_path),
        ),
        check(
            "source_hashes",
            source_valid,
            f"{sum(row['valid'] for row in source_rows)}/15 sources independently hash-verified.",
        ),
        check(
            "release_counts_and_nonmixing",
            independent["release_counts"]
            == {
                "processed": 1071,
                "imaging": 1113,
                "phenotypic": 1206,
                "processed_retest": 45,
            }
            and contains(release, "should not be mixed", "S1200", "2017"),
            json.dumps(independent["release_counts"], sort_keys=True),
        ),
        check(
            "release_processing",
            contains(
                release,
                "SEBASED",
                "Elimination of the regression of movement regressors",
                "multi-run FIX",
                "Reclean",
                "Temporal ICA",
            ),
            "Five 2025 processing changes independently recovered.",
        ),
        check(
            "dictionary_shape",
            len(dictionary) == 813
            and list(dictionary[0])
            == [
                "fullDisplayName",
                "category",
                "assessment",
                "columnHeader",
                "description",
            ],
            f"{len(dictionary)} rows.",
        ),
        check(
            "endpoint_and_family_fields",
            len(required_fields & fields) == len(required_fields)
            and contains(
                endpoint.get("description", ""),
                "Fluid Cognition Composite",
                "Higher scores indicate higher levels of functioning",
                "Unadjusted Scale Score",
            )
            and contains(
                family.get("description", ""),
                "share at least one parent",
                "does not indicate that siblings grew up in the same household",
            ),
            f"{len(required_fields & fields)}/{len(required_fields)} required fields.",
        ),
        check(
            "access_boundary",
            contains(sources["restricted_usage"], "family structure", "exact age")
            and contains(sources["data_use_terms"], "register an account", "Open Access Data Use Terms")
            and contains(sources["summary_demographics"], "recruited as families", "restricted data access"),
            "Registration and restricted-family boundaries independently recovered.",
        ),
        check(
            "anatomy_denominator",
            len(thickness) == 68
            and "FS_IntraCranial_Vol" in fields
            and frozen["nuisance_only_denominator"]["anatomy"]["regional_thickness_count"] == 68,
            "ICV plus 68 bilateral cortical-thickness fields.",
        ),
        check(
            "qc_semantics",
            contains(
                qc,
                "157 subjects",
                "Issue code A: Anatomical anomalies",
                "Issue code B: Segmentation and Surface QC",
                "Issue code C",
                "head coil",
                "Issue code D",
                "prominent artifact",
                "Issue code E",
                "manual reclassification",
                "absence of an issues code",
                "does not imply",
                "very rarely excluded for motion",
            ),
            "QC A-E, non-completeness, and motion warning independently recovered.",
        ),
        check(
            "reconstruction_signature",
            "fMRI_3T_ReconVrs" in fields
            and contains(known, "r177", "r227", "notable signature"),
            "Acquisition reconstruction signature independently recovered.",
        ),
        check(
            "legacy_retest",
            len(retest_pairs) == 46
            and len({subject for subject, _ in retest_pairs}) == 46
            and retest_bins == expected_bins,
            json.dumps(independent["legacy_retest_bins"], sort_keys=True),
        ),
        check(
            "current_retest_discrepancy",
            contains(release, "45 retest subjects")
            and contains(sources["balsa_retest"], "46 HCP subjects were retested", "separate project")
            and evaluation["retest_role"]["exact_current_crosswalk_publicly_resolved"] is False,
            "Legacy 46 and current processed 45 are kept distinct.",
        ),
        check(
            "appendix_products",
            independent["appendix_pages"] == 121
            and connectome["input_product"] in appendix
            and all(independent["per_run_products"].values())
            and all(value >= 4 for value in independent["motion_file_counts"].values()),
            "Current combined/run products and both motion files independently recovered.",
        ),
        check(
            "parcellation_and_edges",
            contains(mmp, "180 region per hemisphere", "210 HCP subjects", "HCP_MMP1.0")
            and connectome["total_cortical_parcels"] == 360
            and connectome["undirected_edge_count"] == independent["undirected_edges"] == 64620,
            "180 per hemisphere and 64,620 edges independently verified.",
        ),
        check(
            "denominator_separation",
            "every functional-connectivity edge"
            in frozen["nuisance_only_denominator"]["forbidden"]
            and "CogFluidComp_Unadj" not in json.dumps(frozen["nuisance_only_denominator"])
            and frozen["endpoint"]["field"] == "CogFluidComp_Unadj",
            "Outcome and connectome remain outside the nuisance-only feature set.",
        ),
        check(
            "split_and_falsifiers",
            evaluation["primary_partition"]["group"] == "Family_ID"
            and evaluation["primary_partition"]["family_crossing_allowed"] is False
            and "0.40" in evaluation["reliability_floor"]["edge_acceptance"]
            and "80%" in evaluation["motion_matched_replay"]["acceptance"]
            and frozen["family_group"]["missing_rule"].startswith("reject_unresolved"),
            "Family split, reliability floor, and motion replay independently frozen.",
        ),
        check(
            "result_agreement",
            result["formal_checks"]["all_passed"] is True
            and result["observed"]["dictionary"]["rows"] == independent["dictionary_rows"]
            and result["observed"]["dictionary"]["cortical_thickness_field_count"] == independent["thickness_fields"]
            and result["observed"]["retest"]["legacy_unique_subjects"] == independent["legacy_retest_subjects"]
            and result["observed"]["parcellation"]["undirected_edges"] == independent["undirected_edges"],
            "Independent counts agree with the primary result.",
        ),
        check(
            "execution_and_decision",
            decision["ready_label"] == result["readiness_decision"]["ready_label"]
            and all(
                decision[key] is False
                for key in [
                    "registered_open_access_available",
                    "restricted_family_access_available",
                    "current_processed_subject_roster_available",
                    "eligible_participant_count_known",
                    "model_executed",
                    "participant_analysis_executed",
                    "cognitive_prediction_claim_ready",
                    "causal_cognition_claim_ready",
                ]
            ),
            decision["ready_label"],
        ),
    ]
    passed = sum(item["passed"] for item in checks)
    return {
        "schema_version": "p059_hcp_ya2025_family_qc_independent_audit_v1",
        "as_of_date": benchmark["as_of_date"],
        "scope": {"included_catalog_problem_ids": [59]},
        "source": {
            "benchmark_sha256": sha256_path(benchmark_path),
            "capture_manifest_sha256": sha256_path(source_dir / CAPTURE_MANIFEST),
            "result_sha256": sha256_path(result_path),
            "snapshots": source_rows,
        },
        "independent_observations": independent,
        "decision": decision["ready_label"],
        "audit_checks": {
            "passed": passed,
            "total": len(checks),
            "all_passed": passed == len(checks),
            "checks": checks,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audit = build_audit(args.benchmark, args.source_dir, args.result)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(pretty_json(audit), encoding="utf-8")
    print(
        f"P059 independent audit: {audit['audit_checks']['passed']}/{audit['audit_checks']['total']} "
        f"decision={audit['decision']}"
    )
    return 0 if audit["audit_checks"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
