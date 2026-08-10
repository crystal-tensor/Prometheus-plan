#!/usr/bin/env python3
"""Capture and audit the frozen P056 ImmPort study shortlist."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import platform
import re
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P056_immport_study_shortlist_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P056_immport_study_shortlist_source_v1"
DEFAULT_RESULT = ROOT / "results/P056_immport_study_shortlist_v1.json"
CAPTURE_MANIFEST = "capture_manifest.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0.0.0 Safari/537.36"
)


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


def normalize_html(payload: bytes) -> bytes:
    soup = BeautifulSoup(payload, "html.parser")
    for tag in soup.find_all(
        [
            "script",
            "style",
            "noscript",
            "svg",
            "img",
            "video",
            "audio",
            "canvas",
            "iframe",
        ]
    ):
        tag.decompose()
    root = soup.find("main") or soup.body or soup
    for tag in root.find_all(True):
        tag.attrs = {}
    return ("<!doctype html>\n" + str(root)).encode("utf-8")


def normalize_json(payload: bytes) -> bytes:
    value = json.loads(payload.decode("utf-8"))
    return pretty_json(value).encode("utf-8")


def fetch_source(
    url: str, *, attempts: int = 5, timeout: int = 90
) -> tuple[bytes, int, str, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json,text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            if response.status_code >= 500:
                raise RuntimeError(f"server returned HTTP {response.status_code}")
            return (
                response.content,
                response.status_code,
                response.url,
                response.headers.get("content-type", ""),
            )
        except Exception as exc:  # pragma: no cover - network path
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(attempt + 1)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def capture_sources(
    benchmark_path: Path,
    benchmark: dict[str, Any],
    source_dir: Path,
) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, spec in benchmark["sources"].items():
        raw, status, final_url, content_type = fetch_source(spec["url"])
        normalized = (
            normalize_json(raw) if spec["format"] == "json" else normalize_html(raw)
        )
        path = source_dir / f"{name}.{extension(spec)}.gz"
        path.write_bytes(gzip.compress(normalized, compresslevel=9, mtime=0))
        entries.append(
            {
                "name": name,
                "requested_url": spec["url"],
                "final_url": final_url,
                "format": spec["format"],
                "expected_status": spec["expected_status"],
                "observed_status": status,
                "content_type": content_type,
                "path": str(path.relative_to(ROOT)),
                "raw_bytes": len(raw),
                "raw_sha256": sha256_bytes(raw),
                "normalized_bytes": len(normalized),
                "normalized_sha256": sha256_bytes(normalized),
                "gzip_bytes": path.stat().st_size,
                "gzip_sha256": sha256_path(path),
            }
        )
    manifest = {
        "schema_version": "p056_immport_normalized_capture_manifest_v1",
        "as_of_date": benchmark["as_of_date"],
        "benchmark": str(benchmark_path.relative_to(ROOT)),
        "benchmark_sha256": sha256_path(benchmark_path),
        "normalization": (
            "Canonical sorted JSON or BeautifulSoup semantic HTML; scripts, styles, "
            "media, and attributes removed; raw transfer hashes retained."
        ),
        "sources": entries,
    }
    (source_dir / CAPTURE_MANIFEST).write_text(
        pretty_json(manifest), encoding="utf-8"
    )


def load_sources(
    benchmark: dict[str, Any], source_dir: Path
) -> tuple[dict[str, bytes], dict[str, Any]]:
    manifest = read_json(source_dir / CAPTURE_MANIFEST)
    sources = {}
    for name, spec in benchmark["sources"].items():
        path = source_dir / f"{name}.{extension(spec)}.gz"
        sources[name] = gzip.decompress(path.read_bytes())
    return sources, manifest


def html_text(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="replace")
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def search_hit(payload: bytes, study_accession: str) -> dict[str, Any]:
    document = json.loads(payload.decode("utf-8"))
    exact = [
        hit.get("_source", {})
        for hit in document.get("hits", {}).get("hits", [])
        if hit.get("_source", {}).get("study_accession") == study_accession
    ]
    if len(exact) != 1:
        raise ValueError(
            f"expected one exact search hit for {study_accession}, observed {len(exact)}"
        )
    return exact[0]


def assay_counts(hit: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in hit.get("assay_method_count", []) or []:
        match = re.fullmatch(r"(.+?)\s*\((\d+)\)", str(item).strip())
        if match:
            counts[match.group(1).strip()] = int(match.group(2))
    return counts


def method_positive(counts: dict[str, int], methods: list[str]) -> bool:
    return any(counts.get(method, 0) > 0 for method in methods)


def formal_check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def inventory_check(
    benchmark: dict[str, Any], source_dir: Path, manifest: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]]]:
    by_name = {entry["name"]: entry for entry in manifest.get("sources", [])}
    rows = []
    valid = set(by_name) == set(benchmark["sources"])
    for name, spec in benchmark["sources"].items():
        path = source_dir / f"{name}.{extension(spec)}.gz"
        entry = by_name.get(name, {})
        observed_gzip = sha256_path(path) if path.exists() else None
        observed_normalized = (
            sha256_bytes(gzip.decompress(path.read_bytes())) if path.exists() else None
        )
        row_valid = (
            entry.get("requested_url") == spec["url"]
            and entry.get("format") == spec["format"]
            and entry.get("expected_status") == spec["expected_status"]
            and entry.get("observed_status") == spec["expected_status"]
            and entry.get("gzip_sha256") == observed_gzip
            and entry.get("normalized_sha256") == observed_normalized
            and bool(re.fullmatch(r"[0-9a-f]{64}", entry.get("raw_sha256", "")))
        )
        valid = valid and row_valid
        rows.append(
            {
                "name": name,
                "observed_status": entry.get("observed_status"),
                "expected_status": spec["expected_status"],
                "raw_sha256": entry.get("raw_sha256"),
                "normalized_sha256": observed_normalized,
                "gzip_sha256": observed_gzip,
                "valid": row_valid,
            }
        )
    return valid, rows


def contains_arm_token(hit: dict[str, Any], token: str) -> bool:
    arm_text = " | ".join(str(value) for value in hit.get("arm_name", []) or [])
    return token.casefold() in arm_text.casefold()


def public_metadata_check(
    contract: dict[str, Any], hit: dict[str, Any]
) -> tuple[bool, dict[str, Any]]:
    counts = assay_counts(hit)
    methods = hit.get("assay_method", []) or []
    visits = max(hit.get("planned_visit_total_count", []) or [0])
    checks = {
        "title": hit.get("brief_title") == contract["expected_title"],
        "clinical_trial": hit.get("clinical_trial")
        == contract["expected_clinical_trial"],
        "species": contract["expected_species"] in (hit.get("species", []) or []),
        "minimum_visits": visits >= contract["expected_minimum_visits"],
        "arm_tokens": all(
            contains_arm_token(hit, token)
            for token in contract.get("required_arm_tokens", [])
        ),
        "release": hit.get("latest_data_release_version")
        == contract["expected_release"],
    }
    if "required_positive_assays" in contract:
        checks["positive_assays"] = all(
            counts.get(method, 0) > 0
            for method in contract["required_positive_assays"]
        )
    if "required_zero_result_assays" in contract:
        checks["zero_result_assays"] = all(
            method in methods and counts.get(method) == 0
            for method in contract["required_zero_result_assays"]
        )
    if "required_absent_assay_methods" in contract:
        checks["absent_assay_methods"] = all(
            method not in methods for method in contract["required_absent_assay_methods"]
        )
    return all(checks.values()), {
        "checks": checks,
        "study_accession": hit.get("study_accession"),
        "title": hit.get("brief_title"),
        "clinical_trial": hit.get("clinical_trial"),
        "species": hit.get("species", []),
        "actual_enrollment": hit.get("actual_enrollment"),
        "arm_accession": hit.get("arm_accession", []),
        "arm_name": hit.get("arm_name", []),
        "planned_visit_total_count": hit.get("planned_visit_total_count", []),
        "has_lab_test": hit.get("has_lab_test"),
        "lab_test_panel_count": hit.get("lab_test_panel_count", []),
        "assay_method": methods,
        "assay_counts": counts,
        "biosample_type": hit.get("biosample_type", []),
        "latest_data_release_version": hit.get("latest_data_release_version"),
        "latest_data_release_date": hit.get("latest_data_release_date"),
        "doi": hit.get("doi"),
    }


def detail_status(manifest: dict[str, Any], name: str) -> int | None:
    for entry in manifest.get("sources", []):
        if entry.get("name") == name:
            return entry.get("observed_status")
    return None


def completeness_matrix(
    sid: str, hit: dict[str, Any], manifest: dict[str, Any]
) -> list[dict[str, str]]:
    counts = assay_counts(hit)
    prefix = sid.casefold()
    demographic_locked = detail_status(manifest, f"{prefix}_demographic") == 401
    biosample_locked = detail_status(manifest, f"{prefix}_biosample") == 401
    intervention_locked = detail_status(manifest, f"{prefix}_intervention") == 401
    visit_locked = detail_status(manifest, f"{prefix}_planned_visit") == 401
    adverse_locked = detail_status(manifest, f"{prefix}_adverse_event") == 401
    visits = max(hit.get("planned_visit_total_count", []) or [0])
    arms = hit.get("arm_name", []) or []
    cell_positive = method_positive(counts, ["Flow Cytometry", "CyTOF"])
    cytokine_positive = method_positive(
        counts,
        [
            "Luminex xMAP",
            "ELISA",
            "Meso Scale Discovery ECL",
            "Cytokine Bead Array",
        ],
    )

    def row(dimension: str, status: str, evidence: str) -> dict[str, str]:
        return {"dimension": dimension, "status": status, "evidence": evidence}

    return [
        row(
            "donor_key",
            "unavailable_authenticated_detail"
            if demographic_locked and biosample_locked
            else "not_confirmed_method_absent",
            "Study-detail demographic and biosample endpoints returned HTTP 401; "
            "study accession and arm accession are not donor keys.",
        ),
        row(
            "intervention_and_dose",
            "partial_public_detail_locked"
            if arms and intervention_locked
            else "not_confirmed_method_absent",
            f"Public arm labels expose {len(arms)} contrasts; the per-subject intervention "
            "endpoint returned HTTP 401, so dose/route/timing are not confirmed.",
        ),
        row(
            "baseline_response_link",
            "partial_public_detail_locked"
            if visits >= 2 and visit_locked
            else "not_confirmed_method_absent",
            f"The directory reports {visits} planned visits; the actual planned-visit and "
            "subject linkage endpoint returned HTTP 401.",
        ),
        row(
            "target_cell_state",
            "confirmed_public" if cell_positive else "not_confirmed_zero_result_rows",
            "Positive public Flow Cytometry/CyTOF result count."
            if cell_positive
            else "No positive public Flow Cytometry/CyTOF result count.",
        ),
        row(
            "cytokine_guardrail",
            "confirmed_public"
            if cytokine_positive
            else "not_confirmed_method_absent",
            "Positive public cytokine-assay result count."
            if cytokine_positive
            else "No positive public cytokine-assay result count.",
        ),
        row(
            "off_target_cell_state_guardrail",
            "confirmed_public" if cell_positive else "not_confirmed_zero_result_rows",
            "Positive public Flow Cytometry/CyTOF result count; an off-target phenotype "
            "still must be frozen after authenticated row access."
            if cell_positive
            else "No positive public Flow Cytometry/CyTOF result count.",
        ),
        row(
            "adverse_event_guardrail",
            "unavailable_authenticated_detail"
            if adverse_locked
            else "not_confirmed_method_absent",
            "The same-study adverse-event endpoint returned HTTP 401; unavailable is not "
            "absent and does not imply safety.",
        ),
    ]


def summarize_statuses(matrix: list[dict[str, str]]) -> dict[str, int]:
    vocabulary = [
        "confirmed_public",
        "partial_public_detail_locked",
        "unavailable_authenticated_detail",
        "not_confirmed_zero_result_rows",
        "not_confirmed_method_absent",
    ]
    return {
        status: sum(row["status"] == status for row in matrix)
        for status in vocabulary
    }


def build_result(
    benchmark_path: Path,
    benchmark: dict[str, Any],
    source_dir: Path,
    sources: dict[str, bytes],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    inventory_valid, inventory = inventory_check(benchmark, source_dir, manifest)
    checks.append(
        formal_check(
            "scope_is_only_catalog_problem_056",
            benchmark["scope"]["included_catalog_problem_ids"] == [56],
            str(benchmark["scope"]),
        )
    )
    checks.append(
        formal_check(
            "candidate_roles_are_frozen",
            [row["study_accession"] for row in benchmark["candidate_contract"]]
            == ["SDY113", "SDY180", "SDY1058", "SDY1439"],
            "Two shortlist candidates, one zero-row reject, and one no-borrow safety near-miss.",
        )
    )
    checks.append(
        formal_check(
            "seven_completeness_dimensions_are_frozen",
            len(benchmark["required_completeness_dimensions"]) == 7
            and len(
                {
                    row["id"]
                    for row in benchmark["required_completeness_dimensions"]
                }
            )
            == 7,
            ", ".join(
                row["id"] for row in benchmark["required_completeness_dimensions"]
            ),
        )
    )
    checks.append(
        formal_check(
            "source_inventory_and_statuses_are_hash_valid",
            inventory_valid,
            f"{sum(row['valid'] for row in inventory)}/{len(inventory)} source rows valid",
        )
    )

    documentation = {}
    for name, phrases in benchmark["documentation_assertions"].items():
        text = html_text(sources[name])
        missing = [phrase for phrase in phrases if phrase.casefold() not in text.casefold()]
        documentation[name] = {
            "required_phrases": phrases,
            "missing_phrases": missing,
            "passed": not missing,
        }
        checks.append(
            formal_check(
                f"{name}_documents_required_boundary",
                not missing,
                "all phrases present" if not missing else f"missing: {missing}",
            )
        )

    candidates = {}
    for contract in benchmark["candidate_contract"]:
        sid = contract["study_accession"]
        hit = search_hit(sources[f"search_{sid.casefold()}"], sid)
        metadata_valid, public = public_metadata_check(contract, hit)
        candidate = {
            "role": contract["role"],
            "public_metadata": public,
            "expected_decision": contract["expected_decision"],
        }
        checks.append(
            formal_check(
                f"{sid}_public_metadata_matches_frozen_contract",
                metadata_valid,
                f"{sum(public['checks'].values())}/{len(public['checks'])} metadata checks pass",
            )
        )
        if contract["role"] == "shortlist":
            matrix = completeness_matrix(sid, hit, manifest)
            summary = summarize_statuses(matrix)
            observed_decision = (
                "shortlisted_access_blocked"
                if summary == {
                    "confirmed_public": 3,
                    "partial_public_detail_locked": 2,
                    "unavailable_authenticated_detail": 2,
                    "not_confirmed_zero_result_rows": 0,
                    "not_confirmed_method_absent": 0,
                }
                else "unexpected_completeness_state"
            )
            candidate["completeness_matrix"] = matrix
            candidate["status_counts"] = summary
            candidate["observed_decision"] = observed_decision
            checks.append(
                formal_check(
                    f"{sid}_seven_layer_matrix_is_fail_closed",
                    len(matrix) == 7
                    and observed_decision == contract["expected_decision"],
                    str(summary),
                )
            )
        elif sid == "SDY1058":
            counts = assay_counts(hit)
            observed_decision = (
                "rejected_zero_cell_state_results"
                if counts.get("Flow Cytometry") == 0 and counts.get("CyTOF") == 0
                else "unexpected_screening_state"
            )
            candidate["observed_decision"] = observed_decision
            checks.append(
                formal_check(
                    "SDY1058_method_names_do_not_override_zero_result_counts",
                    observed_decision == contract["expected_decision"],
                    f"Flow Cytometry={counts.get('Flow Cytometry')}; CyTOF={counts.get('CyTOF')}",
                )
            )
        else:
            methods = set(hit.get("assay_method", []) or [])
            prohibited = set(contract["required_absent_assay_methods"])
            adverse_title = "adverse event" in hit.get("brief_title", "").casefold()
            observed_decision = (
                "near_miss_no_cross_study_borrowing"
                if adverse_title and not (methods & prohibited)
                else "unexpected_screening_state"
            )
            candidate["observed_decision"] = observed_decision
            checks.append(
                formal_check(
                    "SDY1439_adverse_event_title_is_not_borrowed_across_studies",
                    observed_decision == contract["expected_decision"],
                    f"adverse_title={adverse_title}; qualifying_methods={sorted(methods & prohibited)}",
                )
            )
        candidates[sid] = candidate

    detail_probes = []
    for sid in benchmark["selection_rule"]["shortlist"]:
        for endpoint in [
            "demographic",
            "biosample",
            "intervention",
            "planned_visit",
            "adverse_event",
        ]:
            name = f"{sid.casefold()}_{endpoint}"
            status = detail_status(manifest, name)
            detail_probes.append(
                {
                    "study_accession": sid,
                    "endpoint": endpoint,
                    "source_name": name,
                    "observed_status": status,
                    "interpretation": (
                        "authenticated detail unavailable in this unauthenticated capture; "
                        "not evidence of absence or safety"
                    ),
                }
            )
            checks.append(
                formal_check(
                    f"{name}_fails_closed_at_unauthenticated_boundary",
                    status == 401,
                    f"HTTP {status}",
                )
            )

    observed_decision = {
        "label": benchmark["expected_decision"]["label"],
        "shortlist": [
            sid
            for sid, row in candidates.items()
            if row.get("observed_decision") == "shortlisted_access_blocked"
        ],
        "activation_ready": False,
        "model_opened": False,
        "cross_study_join_allowed": False,
        "reason": (
            "Both public shortlist candidates confirm cell-state and cytokine assay layers, "
            "but donor keys, per-subject intervention/dose, actual baseline-response links, "
            "and subject-linked adverse events are not jointly confirmed."
        ),
        "next_falsifier": (
            "After lawful authenticated access, reconstruct all seven layers for SDY113 "
            "first, freeze one target phenotype plus distinct cytokine and off-target panels, "
            "and reject the study if any retained donor lacks an intervention/dose, actual "
            "baseline-response pair, or adverse-event linkage."
        ),
    }
    checks.append(
        formal_check(
            "overall_decision_matches_frozen_contract",
            {
                key: observed_decision[key]
                for key in [
                    "label",
                    "shortlist",
                    "activation_ready",
                    "model_opened",
                    "cross_study_join_allowed",
                ]
            }
            == benchmark["expected_decision"],
            observed_decision["label"],
        )
    )
    checks.append(
        formal_check(
            "safety_boundary_forbids_clinical_control_claims",
            all(
                phrase in benchmark["safety_boundary"].casefold()
                for phrase in ["no dose", "no vaccine", "no treatment recommendation"]
            ),
            benchmark["safety_boundary"],
        )
    )

    return {
        "schema_version": "p056_immport_study_shortlist_result_v1",
        "as_of_date": benchmark["as_of_date"],
        "runtime": {
            "python": platform.python_version(),
            "requests": requests.__version__,
            "beautifulsoup4": __import__("bs4").__version__,
        },
        "benchmark": str(benchmark_path.relative_to(ROOT)),
        "benchmark_sha256": sha256_path(benchmark_path),
        "source_manifest": str(
            (source_dir / CAPTURE_MANIFEST).relative_to(ROOT)
        ),
        "source_manifest_sha256": sha256_path(source_dir / CAPTURE_MANIFEST),
        "source_inventory": inventory,
        "documentation": documentation,
        "candidates": candidates,
        "detail_probes": detail_probes,
        "decision": observed_decision,
        "safety_boundary": benchmark["safety_boundary"],
        "formal_checks": checks,
        "formal_check_summary": {
            "passed": sum(check["passed"] for check in checks),
            "total": len(checks),
            "failed": [check["name"] for check in checks if not check["passed"]],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Fetch and normalize the frozen sources before evaluating them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    benchmark = read_json(args.benchmark)
    if args.capture:
        capture_sources(args.benchmark, benchmark, args.source_dir)
    sources, manifest = load_sources(benchmark, args.source_dir)
    result = build_result(
        args.benchmark, benchmark, args.source_dir, sources, manifest
    )
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(pretty_json(result), encoding="utf-8")
    summary = result["formal_check_summary"]
    print(
        f"P056 ImmPort shortlist: {summary['passed']}/{summary['total']} checks pass; "
        f"decision={result['decision']['label']}"
    )
    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
