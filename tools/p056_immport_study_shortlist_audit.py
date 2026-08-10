#!/usr/bin/env python3
"""Independently audit the frozen P056 ImmPort shortlist packet."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P056_immport_study_shortlist_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P056_immport_study_shortlist_source_v1"
DEFAULT_RESULT = ROOT / "results/P056_immport_study_shortlist_v1.json"
DEFAULT_AUDIT = ROOT / "results/P056_immport_study_shortlist_audit_v1.json"
CAPTURE_MANIFEST = "capture_manifest.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def extension(spec: dict[str, Any]) -> str:
    return "json" if spec["format"] == "json" else "html"


def source_bytes(source_dir: Path, name: str, spec: dict[str, Any]) -> bytes:
    path = source_dir / f"{name}.{extension(spec)}.gz"
    return gzip.decompress(path.read_bytes())


def exact_hit(payload: bytes, sid: str) -> dict[str, Any]:
    document = json.loads(payload.decode("utf-8"))
    hits = [
        hit.get("_source", {})
        for hit in document.get("hits", {}).get("hits", [])
        if hit.get("_source", {}).get("study_accession") == sid
    ]
    if len(hits) != 1:
        raise ValueError(f"expected one exact hit for {sid}, observed {len(hits)}")
    return hits[0]


def counts(hit: dict[str, Any]) -> dict[str, int]:
    observed = {}
    for item in hit.get("assay_method_count", []) or []:
        match = re.fullmatch(r"(.+?)\s*\((\d+)\)", str(item).strip())
        if match:
            observed[match.group(1).strip()] = int(match.group(2))
    return observed


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def build_audit(
    benchmark_path: Path,
    source_dir: Path,
    result_path: Path,
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    manifest_path = source_dir / CAPTURE_MANIFEST
    manifest = read_json(manifest_path)
    result = read_json(result_path)
    checks: list[dict[str, Any]] = []

    checks.append(
        check(
            "scope_reconstructs_as_only_056",
            benchmark["scope"]["included_catalog_problem_ids"] == [56]
            and 56 not in benchmark["scope"]["excluded_catalog_problem_ids"],
            str(benchmark["scope"]),
        )
    )
    checks.append(
        check(
            "benchmark_hash_matches_result_and_manifest",
            result.get("benchmark_sha256") == sha256_path(benchmark_path)
            and manifest.get("benchmark_sha256") == sha256_path(benchmark_path),
            sha256_path(benchmark_path),
        )
    )
    checks.append(
        check(
            "capture_manifest_hash_matches_result",
            result.get("source_manifest_sha256") == sha256_path(manifest_path),
            sha256_path(manifest_path),
        )
    )

    entries = {row["name"]: row for row in manifest.get("sources", [])}
    source_valid = set(entries) == set(benchmark["sources"])
    source_rows = []
    for name, spec in benchmark["sources"].items():
        path = source_dir / f"{name}.{extension(spec)}.gz"
        entry = entries.get(name, {})
        normalized = source_bytes(source_dir, name, spec) if path.exists() else b""
        row_valid = (
            entry.get("requested_url") == spec["url"]
            and entry.get("observed_status") == spec["expected_status"]
            and entry.get("gzip_sha256") == sha256_path(path)
            and entry.get("normalized_sha256") == sha256_bytes(normalized)
        )
        source_valid = source_valid and row_valid
        source_rows.append(
            {
                "name": name,
                "status": entry.get("observed_status"),
                "valid": row_valid,
            }
        )
    checks.append(
        check(
            "all_source_files_and_http_statuses_reconstruct",
            source_valid,
            f"{sum(row['valid'] for row in source_rows)}/{len(source_rows)} valid",
        )
    )

    reconstructed = {}
    for contract in benchmark["candidate_contract"]:
        sid = contract["study_accession"]
        spec_name = f"search_{sid.casefold()}"
        hit = exact_hit(
            source_bytes(source_dir, spec_name, benchmark["sources"][spec_name]), sid
        )
        assay_counts = counts(hit)
        visits = max(hit.get("planned_visit_total_count", []) or [0])
        metadata_ok = (
            hit.get("brief_title") == contract["expected_title"]
            and hit.get("clinical_trial") == contract["expected_clinical_trial"]
            and contract["expected_species"] in (hit.get("species", []) or [])
            and visits >= contract["expected_minimum_visits"]
            and hit.get("latest_data_release_version")
            == contract["expected_release"]
        )
        if contract["role"] == "shortlist":
            metadata_ok = metadata_ok and all(
                assay_counts.get(method, 0) > 0
                for method in contract["required_positive_assays"]
            )
        elif sid == "SDY1058":
            metadata_ok = metadata_ok and all(
                assay_counts.get(method) == 0
                for method in contract["required_zero_result_assays"]
            )
        else:
            methods = set(hit.get("assay_method", []) or [])
            metadata_ok = metadata_ok and not (
                methods & set(contract["required_absent_assay_methods"])
            )
        reconstructed[sid] = {
            "role": contract["role"],
            "visits": visits,
            "assay_counts": assay_counts,
            "metadata_valid": metadata_ok,
        }
        checks.append(
            check(
                f"{sid}_exact_public_record_reconstructs",
                metadata_ok,
                f"visits={visits}; assays={assay_counts}",
            )
        )

    expected_shortlist_counts = Counter(
        {
            "confirmed_public": 3,
            "partial_public_detail_locked": 2,
            "unavailable_authenticated_detail": 2,
        }
    )
    for sid in benchmark["selection_rule"]["shortlist"]:
        matrix = result["candidates"][sid]["completeness_matrix"]
        observed_counts = Counter(row["status"] for row in matrix)
        exact_dimensions = [row["dimension"] for row in matrix] == [
            row["id"] for row in benchmark["required_completeness_dimensions"]
        ]
        checks.append(
            check(
                f"{sid}_matrix_has_three_confirmed_two_partial_two_locked",
                exact_dimensions and observed_counts == expected_shortlist_counts,
                str(dict(observed_counts)),
            )
        )

    probes = result.get("detail_probes", [])
    probe_keys = {
        (row.get("study_accession"), row.get("endpoint")): row.get(
            "observed_status"
        )
        for row in probes
    }
    expected_probe_keys = {
        (sid, endpoint)
        for sid in benchmark["selection_rule"]["shortlist"]
        for endpoint in [
            "demographic",
            "biosample",
            "intervention",
            "planned_visit",
            "adverse_event",
        ]
    }
    checks.append(
        check(
            "ten_authenticated_detail_probes_fail_closed_at_401",
            set(probe_keys) == expected_probe_keys
            and all(status == 401 for status in probe_keys.values()),
            f"{sum(status == 401 for status in probe_keys.values())}/{len(expected_probe_keys)} HTTP 401",
        )
    )
    checks.append(
        check(
            "zero_count_candidate_is_rejected_not_promoted",
            result["candidates"]["SDY1058"].get("observed_decision")
            == "rejected_zero_cell_state_results"
            and reconstructed["SDY1058"]["assay_counts"].get("Flow Cytometry")
            == 0
            and reconstructed["SDY1058"]["assay_counts"].get("CyTOF") == 0,
            "Assay method names cannot substitute for positive result counts.",
        )
    )
    checks.append(
        check(
            "adverse_event_near_miss_is_not_joined_to_another_study",
            result["candidates"]["SDY1439"].get("observed_decision")
            == "near_miss_no_cross_study_borrowing"
            and result["decision"].get("cross_study_join_allowed") is False,
            "SDY1439 title evidence stays inside SDY1439.",
        )
    )
    decision_projection = {
        key: result["decision"].get(key)
        for key in [
            "label",
            "shortlist",
            "activation_ready",
            "model_opened",
            "cross_study_join_allowed",
        ]
    }
    checks.append(
        check(
            "final_decision_matches_frozen_benchmark",
            decision_projection == benchmark["expected_decision"],
            result["decision"].get("label", ""),
        )
    )
    checks.append(
        check(
            "main_tool_reported_no_failed_formal_checks",
            not result["formal_check_summary"].get("failed")
            and result["formal_check_summary"].get("passed")
            == result["formal_check_summary"].get("total"),
            str(result["formal_check_summary"]),
        )
    )

    summary = {
        "passed": sum(row["passed"] for row in checks),
        "total": len(checks),
        "failed": [row["name"] for row in checks if not row["passed"]],
    }
    return {
        "schema_version": "p056_immport_study_shortlist_independent_audit_v1",
        "benchmark": str(benchmark_path.relative_to(ROOT)),
        "benchmark_sha256": sha256_path(benchmark_path),
        "result": str(result_path.relative_to(ROOT)),
        "result_sha256": sha256_path(result_path),
        "capture_manifest": str(manifest_path.relative_to(ROOT)),
        "capture_manifest_sha256": sha256_path(manifest_path),
        "independence": (
            "Standard-library JSON/gzip/hash/re parser; does not import the main tool or "
            "reuse its candidate, assay-count, matrix, or decision functions."
        ),
        "source_rows": source_rows,
        "reconstructed_candidates": reconstructed,
        "checks": checks,
        "summary": summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
    summary = audit["summary"]
    print(
        f"P056 independent audit: {summary['passed']}/{summary['total']} checks pass"
    )
    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
