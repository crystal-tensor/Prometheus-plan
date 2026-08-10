#!/usr/bin/env python3
"""Capture and audit the public P059 HCP-YA 2025 family/QC contract."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import re
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests
import urllib3
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P059_hcp_ya2025_family_qc_denominator_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P059_hcp_ya2025_family_qc_source_v1"
DEFAULT_RESULT = ROOT / "results/P059_hcp_ya2025_family_qc_denominator_v1.json"
DEFAULT_REPORT = ROOT / "research/P059_hcp_ya2025_family_qc_denominator_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/P059_hcp_ya2025_family_qc_discussion_v1.md"
CAPTURE_MANIFEST = "capture_manifest.json"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def fold(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def contains_all(text: str, phrases: list[str]) -> bool:
    folded = fold(text)
    return all(fold(phrase) in folded for phrase in phrases)


def fetch_bytes(url: str, attempts: int = 5, timeout: int = 120) -> tuple[bytes, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/pdf,text/csv,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    last_error: Exception | None = None
    # The desktop transport terminates TLS at a local proxy whose CA is not in the
    # bundled Python trust store. Raw hashes are retained and this boundary is
    # recorded in the capture manifest instead of silently weakening provenance.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    for attempt in range(attempts):
        try:
            response = requests.get(
                url, headers=headers, timeout=timeout, verify=False, allow_redirects=True
            )
            response.raise_for_status()
            if not response.content:
                raise RuntimeError("empty response")
            return response.content, response.url
        except Exception as exc:  # pragma: no cover - network path
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(attempt + 1)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def normalize_html(payload: bytes) -> bytes:
    soup = BeautifulSoup(payload, "html.parser")
    for tag in soup.find_all(["script", "style", "noscript", "svg", "img", "video", "audio", "canvas", "iframe"]):
        tag.decompose()
    root = soup.find("main") or soup.body or soup
    text = "\n".join(root.stripped_strings)
    return (re.sub(r"[ \t]+", " ", text).strip() + "\n").encode("utf-8")


def normalize_csv(payload: bytes) -> bytes:
    text = payload.decode("utf-8-sig", errors="strict")
    return (text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n").encode("utf-8")


def extract_pdf_text(pdf_path: Path) -> tuple[bytes, int]:
    info = subprocess.run(
        ["pdfinfo", str(pdf_path)], check=True, capture_output=True, text=True
    ).stdout
    match = re.search(r"^Pages:\s+(\d+)\s*$", info, flags=re.MULTILINE)
    if not match:
        raise RuntimeError("pdfinfo did not report a page count")
    pages = int(match.group(1))
    completed = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        check=True,
        capture_output=True,
    )
    text = completed.stdout.decode("utf-8", errors="replace")
    normalized = (text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n") + "\n").encode("utf-8")
    return normalized, pages


def write_gzip(path: Path, payload: bytes) -> None:
    path.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))


def read_gzip(path: Path) -> bytes:
    return gzip.decompress(path.read_bytes())


def source_suffix(source_format: str) -> str:
    return "csv" if source_format == "csv" else "txt"


def capture_sources(
    benchmark_path: Path,
    benchmark: dict[str, Any],
    source_dir: Path,
    appendix_pdf: Path | None,
) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for name, spec in benchmark["sources"].items():
        source_format = spec["format"]
        page_count: int | None = None
        if source_format == "pdf" and appendix_pdf is not None:
            raw = appendix_pdf.read_bytes()
            final_url = spec["url"]
            local_input = str(appendix_pdf.resolve())
        else:
            raw, final_url = fetch_bytes(spec["url"])
            local_input = None

        if source_format == "html":
            normalized = normalize_html(raw)
        elif source_format == "csv":
            normalized = normalize_csv(raw)
        elif source_format == "pdf":
            if not raw.startswith(b"%PDF"):
                raise RuntimeError(f"{name} did not return a PDF")
            with tempfile.NamedTemporaryFile(suffix=".pdf") as handle:
                handle.write(raw)
                handle.flush()
                normalized, page_count = extract_pdf_text(Path(handle.name))
        else:  # pragma: no cover - benchmark schema guard
            raise ValueError(f"unsupported source format: {source_format}")

        suffix = source_suffix(source_format)
        path = source_dir / f"{name}.{suffix}.gz"
        write_gzip(path, normalized)
        entry = {
            "name": name,
            "format": source_format,
            "requested_url": spec["url"],
            "final_url": final_url,
            "path": str(path.relative_to(ROOT)),
            "raw_bytes": len(raw),
            "raw_sha256": sha256_bytes(raw),
            "normalized_bytes": len(normalized),
            "normalized_sha256": sha256_bytes(normalized),
            "gzip_bytes": path.stat().st_size,
            "gzip_sha256": sha256_path(path),
        }
        if page_count is not None:
            entry["pdf_pages"] = page_count
        if local_input is not None:
            entry["capture_input"] = "local_verified_download"
        entries.append(entry)

    manifest = {
        "schema_version": "p059_hcp_ya2025_normalized_capture_manifest_v1",
        "as_of_date": benchmark["as_of_date"],
        "benchmark": str(benchmark_path.relative_to(ROOT)),
        "benchmark_sha256": sha256_path(benchmark_path),
        "transport_boundary": "TLS terminated by the Codex desktop local proxy; Python certificate verification disabled and raw official-URL transfer hashes retained.",
        "normalization": "Visible HTML text, newline-normalized CSV, or pdftotext -layout output; deterministic gzip mtime=0.",
        "sources": entries,
    }
    (source_dir / CAPTURE_MANIFEST).write_text(pretty_json(manifest), encoding="utf-8")


def load_sources(
    benchmark: dict[str, Any], source_dir: Path
) -> tuple[dict[str, str], dict[str, Any]]:
    capture = read_json(source_dir / CAPTURE_MANIFEST)
    sources: dict[str, str] = {}
    for name, spec in benchmark["sources"].items():
        suffix = source_suffix(spec["format"])
        sources[name] = read_gzip(source_dir / f"{name}.{suffix}.gz").decode(
            "utf-8", errors="replace"
        )
    return sources, capture


def parse_dictionary(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text, newline="")))


def dictionary_row(rows: list[dict[str, str]], field: str) -> dict[str, str] | None:
    matches = [row for row in rows if row.get("columnHeader") == field]
    return matches[0] if len(matches) == 1 else None


def parse_retest_csv(text: str) -> list[tuple[str, int]]:
    rows = csv.reader(io.StringIO(text, newline=""))
    next(rows, None)
    pairs: list[tuple[str, int]] = []
    for row in rows:
        if len(row) >= 2 and row[0].strip().isdigit() and row[1].strip().isdigit():
            pairs.append((row[0].strip(), int(row[1].strip())))
    return pairs


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def source_inventory_valid(
    benchmark: dict[str, Any], source_dir: Path, capture: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]]]:
    by_name = {entry["name"]: entry for entry in capture["sources"]}
    valid = len(by_name) == len(benchmark["sources"])
    rows: list[dict[str, Any]] = []
    for name, spec in benchmark["sources"].items():
        suffix = source_suffix(spec["format"])
        path = source_dir / f"{name}.{suffix}.gz"
        entry = by_name.get(name, {})
        gzip_hash = sha256_path(path) if path.exists() else None
        normalized_hash = sha256_bytes(read_gzip(path)) if path.exists() else None
        row_valid = (
            entry.get("format") == spec["format"]
            and entry.get("requested_url") == spec["url"]
            and entry.get("path") == str(path.relative_to(ROOT))
            and entry.get("gzip_sha256") == gzip_hash
            and entry.get("normalized_sha256") == normalized_hash
            and bool(re.fullmatch(r"[0-9a-f]{64}", entry.get("raw_sha256", "")))
        )
        if spec["format"] == "pdf":
            row_valid = row_valid and entry.get("pdf_pages") == 121
        valid = valid and row_valid
        rows.append(
            {
                "name": name,
                "format": spec["format"],
                "raw_sha256": entry.get("raw_sha256"),
                "normalized_sha256": normalized_hash,
                "gzip_sha256": gzip_hash,
                "valid": row_valid,
            }
        )
    return valid, rows


def build_result(
    benchmark_path: Path,
    benchmark: dict[str, Any],
    source_dir: Path,
) -> dict[str, Any]:
    sources, capture = load_sources(benchmark, source_dir)
    source_valid, source_rows = source_inventory_valid(benchmark, source_dir, capture)
    dictionary = parse_dictionary(sources["data_dictionary"])
    expected_dictionary = benchmark["dictionary_expectations"]
    fields = {row.get("columnHeader", "") for row in dictionary}
    thickness_fields = sorted(
        field
        for field in fields
        if field.startswith(("FS_L_", "FS_R_")) and field.endswith("_Thck")
    )
    family_row = dictionary_row(dictionary, "Family_ID") or {}
    endpoint_row = dictionary_row(dictionary, "CogFluidComp_Unadj") or {}
    retest_pairs = parse_retest_csv(sources["retest_interval_csv"])
    retest_bins = Counter(month for _, month in retest_pairs)
    expected_bins = {
        int(month): count
        for month, count in benchmark["split_and_evaluation_contract"]["retest_role"]["legacy_month_bin_counts"].items()
    }
    release_digits = sources["release_2025"].replace(",", "")
    data_release_digits = sources["data_releases"].replace(",", "")
    appendix = sources["appendix_iii"]
    qc_text = sources["qc_issues"]
    known_text = sources["known_issues"]
    mmp_text = sources["mmp_article"]
    release_expected = benchmark["official_release_expectations"]
    contract = benchmark["frozen_manifest"]
    connectome = benchmark["frozen_connectome_candidate"]
    evaluation = benchmark["split_and_evaluation_contract"]
    decision = benchmark["readiness_decision"]

    exact_run_products = [
        f"rfMRI_{run}_Atlas_MSMAll_hp2000_clean_rclean_tclean.dtseries.nii"
        for run in connectome["runs"]
    ]
    motion_file_counts = {
        filename: appendix.count(filename)
        for filename in contract["nuisance_only_denominator"]["motion_per_run"]
    }
    observed = {
        "official_release": {
            "processed_subjects": 1071 if "1071 subjects" in release_digits else None,
            "unprocessed_imaging_subjects": 1113 if "1113 subjects" in release_digits else None,
            "phenotypic_subjects": 1206 if "1206" in data_release_digits else None,
            "processed_retest_subjects": 45 if "45 retest subjects" in release_digits else None,
            "no_2017_processing_mix": contains_all(
                sources["release_2025"], ["should not be mixed", "S1200", "2017"]
            ),
        },
        "dictionary": {
            "rows": len(dictionary),
            "columns": list(dictionary[0]) if dictionary else [],
            "required_fields_present": sorted(set(expected_dictionary["required_fields"]) & fields),
            "cortical_thickness_fields": thickness_fields,
            "cortical_thickness_field_count": len(thickness_fields),
            "family_id_description": family_row.get("description"),
            "endpoint_description": endpoint_row.get("description"),
        },
        "qc": {
            "coded_subjects_s1200": 157 if "157 subjects" in fold(qc_text) else None,
            "codes": ["A", "B", "C", "D", "E"],
            "absence_is_not_clean_bill": contains_all(
                qc_text, ["absence of an issues code", "does not imply", "no issues"]
            ),
            "motion_rarely_excluded": contains_all(
                qc_text, ["fMRI and dMRI scans", "very rarely excluded for motion"]
            ),
            "reconstruction_versions": ["r177", "r227"]
            if contains_all(known_text, ["r177", "r227", "notable signature"])
            else [],
        },
        "retest": {
            "legacy_csv_rows": len(retest_pairs),
            "legacy_unique_subjects": len({subject for subject, _ in retest_pairs}),
            "legacy_month_bin_counts": {str(k): retest_bins[k] for k in sorted(retest_bins)},
            "current_processed_subjects": 45,
            "roster_difference": len({subject for subject, _ in retest_pairs}) - 45,
            "exact_current_crosswalk_publicly_resolved": False,
        },
        "package_files": {
            "appendix_pages": next(
                entry.get("pdf_pages")
                for entry in capture["sources"]
                if entry["name"] == "appendix_iii"
            ),
            "combined_product_present": connectome["input_product"] in appendix,
            "per_run_products_present": {
                product: product in appendix for product in exact_run_products
            },
            "motion_file_occurrences": motion_file_counts,
        },
        "parcellation": {
            "areas_per_hemisphere": 180
            if contains_all(mmp_text, ["180 region per hemisphere", "210 HCP subjects"])
            else None,
            "total_parcels": connectome["total_cortical_parcels"],
            "undirected_edges": connectome["undirected_edge_count"],
        },
    }

    denominator_flat = json.dumps(
        contract["nuisance_only_denominator"], sort_keys=True
    ).casefold()
    checks = [
        check(
            "schema_and_scope",
            benchmark["scope"]["included_catalog_problem_ids"] == [59]
            and benchmark["scope"]["excluded_catalog_problem_ids"]
            == [49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 60],
            "Packet is restricted to catalog problem #059.",
        ),
        check(
            "benchmark_hash",
            capture["benchmark_sha256"] == sha256_path(benchmark_path),
            sha256_path(benchmark_path),
        ),
        check(
            "source_inventory",
            source_valid,
            f"{sum(row['valid'] for row in source_rows)}/{len(source_rows)} normalized official snapshots hash-verified.",
        ),
        check(
            "release_date",
            contains_all(sources["data_releases"], ["August 11, 2025", "HCP-YA 2025"]),
            "2025 release date recovered from the official release index.",
        ),
        check(
            "release_counts",
            observed["official_release"]
            == {
                "processed_subjects": release_expected["processed_subjects"],
                "unprocessed_imaging_subjects": release_expected["unprocessed_imaging_subjects"],
                "phenotypic_subjects": release_expected["phenotypic_subjects"],
                "processed_retest_subjects": release_expected["processed_retest_subjects"],
                "no_2017_processing_mix": True,
            },
            "1071 processed, 1113 imaging, 1206 phenotypic, and 45 processed-retest subjects recovered.",
        ),
        check(
            "processing_changes",
            contains_all(sources["release_2025"], release_expected["required_processing_changes"]),
            "SEBASED, movement-regressor removal, multi-run FIX, Reclean, and temporal ICA recovered.",
        ),
        check(
            "processing_nonmixing",
            observed["official_release"]["no_2017_processing_mix"],
            "Official 2025/S1200-2017 non-mixing warning recovered.",
        ),
        check(
            "dictionary_shape",
            len(dictionary) == expected_dictionary["row_count"]
            and list(dictionary[0]) == expected_dictionary["columns"],
            f"{len(dictionary)} rows and {len(dictionary[0]) if dictionary else 0} columns.",
        ),
        check(
            "required_dictionary_fields",
            set(expected_dictionary["required_fields"]).issubset(fields),
            f"{len(set(expected_dictionary['required_fields']) & fields)}/{len(expected_dictionary['required_fields'])} fields present.",
        ),
        check(
            "endpoint_semantics",
            contains_all(endpoint_row.get("description", ""), expected_dictionary["endpoint_required_description_tokens"]),
            "Unadjusted NIH Toolbox Fluid Cognition Composite semantics recovered.",
        ),
        check(
            "family_semantics",
            contains_all(family_row.get("description", ""), expected_dictionary["family_id_required_description_tokens"]),
            "Biological sibling grouping and rearing-environment boundary recovered.",
        ),
        check(
            "family_verification_fields",
            all(field in fields for field in ["Mother_ID", "Father_ID", "HasGT", "ZygosityGT"]),
            "Four family-verification fields recovered.",
        ),
        check(
            "restricted_family_access",
            contains_all(sources["restricted_usage"], ["family structure", "exact age", "restricted"])
            and contains_all(sources["summary_demographics"], ["recruited as families", "restricted data access"]),
            "Family structure and exact age require restricted access.",
        ),
        check(
            "open_imaging_and_anatomy",
            contains_all(sources["quick_reference"], ["image data", "open access", "Freesurfer Summary Stats", "Freesurfer Surface Thickness"]),
            "Open imaging and FreeSurfer anatomy boundary recovered.",
        ),
        check(
            "data_use_registration",
            contains_all(sources["data_use_terms"], ["register an account", "Open Access Data Use Terms"]),
            "Registered open-access terms recovered.",
        ),
        check(
            "cortical_thickness_fields",
            len(thickness_fields) == expected_dictionary["cortical_thickness_field_count"],
            f"{len(thickness_fields)} bilateral regional thickness fields recovered.",
        ),
        check(
            "qc_codes_and_count",
            contains_all(qc_text, ["157 subjects", "focal anatomical anomaly", "focal segmentation", "head coil", "manual reclassification"]),
            "QC A-E semantics and 157 coded S1200 imaging subjects recovered.",
        ),
        check(
            "qc_not_clean_bill",
            observed["qc"]["absence_is_not_clean_bill"],
            "Absence of a QC code is explicitly not a clean bill of health.",
        ),
        check(
            "motion_was_rarely_excluded",
            observed["qc"]["motion_rarely_excluded"],
            "HCP warns that fMRI/dMRI were only very rarely excluded for motion.",
        ),
        check(
            "reconstruction_signature",
            observed["qc"]["reconstruction_versions"] == ["r177", "r227"]
            and "fMRI_3T_ReconVrs" in fields,
            "r177/r227 signature and its dictionary field recovered.",
        ),
        check(
            "legacy_retest_roster",
            len(retest_pairs) == 46 and len({subject for subject, _ in retest_pairs}) == 46,
            "46 unique legacy retest rows recovered.",
        ),
        check(
            "legacy_retest_bins",
            retest_bins == Counter(expected_bins),
            json.dumps({str(k): retest_bins[k] for k in sorted(retest_bins)}, sort_keys=True),
        ),
        check(
            "current_retest_count",
            contains_all(sources["release_2025"], ["45 retest subjects"])
            and contains_all(sources["balsa_retest"], ["46 HCP subjects were retested", "separate project"]),
            "46 collected/legacy subjects and 45 currently processed subjects remain distinct.",
        ),
        check(
            "retest_crosswalk_fail_closed",
            evaluation["retest_role"]["exact_current_crosswalk_publicly_resolved"] is False
            and evaluation["retest_role"]["exclude_from_primary_prediction"] is True,
            "Legacy roster cannot silently become the current processed roster.",
        ),
        check(
            "appendix_page_count",
            observed["package_files"]["appendix_pages"] == 121,
            "Official Appendix III has 121 pages.",
        ),
        check(
            "current_connectome_product",
            observed["package_files"]["combined_product_present"]
            and all(observed["package_files"]["per_run_products_present"].values()),
            "Combined and all four per-run 2025 Reclean+tICA products recovered.",
        ),
        check(
            "motion_files",
            all(count >= 4 for count in motion_file_counts.values()),
            json.dumps(motion_file_counts, sort_keys=True),
        ),
        check(
            "mmp_parcellation",
            observed["parcellation"]["areas_per_hemisphere"] == 180
            and "HCP_MMP1.0" in mmp_text,
            "Official HCP article supports 180 cortical regions per hemisphere.",
        ),
        check(
            "edge_arithmetic",
            connectome["total_cortical_parcels"] == 360
            and connectome["undirected_edge_count"]
            == 360 * (360 - 1) // 2,
            "360 choose 2 = 64,620 undirected edges.",
        ),
        check(
            "denominator_has_no_edges",
            "every functional-connectivity edge" in denominator_flat
            and all(field not in denominator_flat for field in ["64620", "pearson", "fisher z"]),
            "Connectivity is explicitly forbidden from the nuisance-only denominator.",
        ),
        check(
            "family_split",
            evaluation["primary_partition"]["group"] == "Family_ID"
            and evaluation["primary_partition"]["family_crossing_allowed"] is False
            and contract["family_group"]["missing_rule"]
            == "reject_unresolved_family_group_never_assign_a_synthetic_singleton",
            "Family grouping is deterministic and fail-closed.",
        ),
        check(
            "primary_metric",
            evaluation["primary_metric"]["name"] == "delta_mae"
            and evaluation["primary_metric"]["better_direction"] == "positive"
            and "greater than zero" in evaluation["primary_metric"]["acceptance"],
            "Family-held-out delta MAE and clustered interval frozen.",
        ),
        check(
            "reliability_floor",
            "0.40" in evaluation["reliability_floor"]["edge_acceptance"]
            and "greater than zero" in evaluation["reliability_floor"]["identity_free_acceptance"],
            "Median edgewise ICC and within-versus-between similarity gates frozen.",
        ),
        check(
            "motion_matched_replay",
            "80%" in evaluation["motion_matched_replay"]["acceptance"]
            and "no cognition or connectivity" in evaluation["motion_matched_replay"]["matching_inputs"],
            "Outcome-free matching and 20% degradation limit frozen.",
        ),
        check(
            "current_roster_not_inferred",
            contract["current_roster_rules"]["eligible_count_publicly_known"] is False
            and contract["current_roster_rules"]["legacy_2017_session_summary_is_current_roster"] is False,
            "The 1,071 release count is not presented as an eligible cohort.",
        ),
        check(
            "execution_boundary",
            all(
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
            "No participant row, image, connectome, cognition outcome, or model was opened.",
        ),
        check(
            "decision",
            decision["ready_label"]
            == "hcp_ya2025_public_contract_ready_execution_blocked_by_registered_data_access_restricted_family_fields_and_current_processed_roster",
            decision["ready_label"],
        ),
    ]

    passed = sum(item["passed"] for item in checks)
    return {
        "schema_version": "p059_hcp_ya2025_family_qc_denominator_result_v1",
        "as_of_date": benchmark["as_of_date"],
        "scope": benchmark["scope"],
        "question": benchmark["question"],
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "capture_manifest": str((source_dir / CAPTURE_MANIFEST).relative_to(ROOT)),
            "capture_manifest_sha256": sha256_path(source_dir / CAPTURE_MANIFEST),
            "snapshots": source_rows,
        },
        "observed": observed,
        "frozen_manifest": benchmark["frozen_manifest"],
        "frozen_connectome_candidate": benchmark["frozen_connectome_candidate"],
        "split_and_evaluation_contract": benchmark["split_and_evaluation_contract"],
        "readiness_decision": benchmark["readiness_decision"],
        "interpretation_boundaries": benchmark["interpretation_boundaries"],
        "formal_checks": {
            "passed": passed,
            "total": len(checks),
            "all_passed": passed == len(checks),
            "checks": checks,
        },
    }


def write_report(result: dict[str, Any], path: Path) -> None:
    checks = result["formal_checks"]
    observed = result["observed"]
    decision = result["readiness_decision"]["ready_label"]
    retest_bins = observed["retest"]["legacy_month_bin_counts"]
    text = f"""# P059 HCP-YA 2025 subject-family/QC manifest and nuisance-only denominator v1

**Decision:** `{decision}`.

## Can a connectome predict cognition after its easiest shortcuts are removed?

The #059 activation gate is now executable as a contract but not as a participant analysis. The frozen target is `CogFluidComp_Unadj`, the NIH Toolbox Fluid Cognition Composite on its unadjusted scale. Exact age, gender, and education enter the nuisance denominator instead of hiding age adjustment inside the outcome.

The official 2025 release reports **1,071 processed subjects**, including **45 processed retest subjects**, **1,113 subjects with imaging**, and **1,206 with phenotypic data**. Those are release counts, not an eligible cohort. The primary cohort still requires all four resting-state runs, the current cleaned product, both mean motion files per run, resolved family membership, allowed QC state, anatomy fields, and a complete outcome.

## What must be beaten before one edge can count?

The nuisance-only denominator contains:

- restricted exact age, gender, and education;
- per-run mean absolute and relative RMS motion, four-run availability, and across-run summaries;
- fMRI reconstruction version, resting-state completeness, and separate QC A-E indicators; and
- intracranial volume plus all **68** bilateral FreeSurfer regional cortical-thickness fields.

No functional-connectivity edge, subject ID, family ID, retest-derived feature, or test-family outcome may enter this denominator. Both the nuisance model and the nuisance-plus-connectome model use ridge regression; every imputation, scaling, threshold, and penalty is fit inside training families only.

## Which connectome is actually frozen?

The feature source is the 2025 product `rfMRI_REST_Atlas_MSMAll_hp2000_clean_rclean_tclean.dtseries.nii`, not the 2017 S1200 processing. Official Appendix III exposes the combined file, all four run-specific files, and `Movement_AbsoluteRMS_mean.txt` plus `Movement_RelativeRMS_mean.txt` for each run.

The candidate averages time series within the HCP-MMP1.0 atlas, which has **180 cortical areas per hemisphere**. It then concatenates run-wise demeaned data, computes Pearson correlations, and applies Fisher z, producing **360 choose 2 = 64,620** undirected edges. The 2025 release explicitly warns against mixing its processing with S1200 2017.

## Family structure is a split key, not a nuisance label

`Family_ID` groups biological siblings sharing at least one parent; HCP explicitly warns that it does not establish a shared rearing environment. `Mother_ID`, `Father_ID`, `HasGT`, and `ZygosityGT` remain verification fields. Family structure and exact age require restricted approval.

Every `Family_ID` is assigned deterministically to a 70/15/15 train/validation/test partition. Missing or unresolved family IDs are rejected; they are never converted into synthetic singletons. Retest participants are excluded from primary cognition prediction and used only for reliability.

## Why 46 is not 45

The public 2017 retest interval CSV contains **46 unique subjects**, with month-bin counts `{json.dumps(retest_bins, sort_keys=True)}`. The separate BALSA retest project also says 46 subjects were retested. The 2025 release, however, exposes only **45 processed retest subjects** meeting its processing condition. The exact current 45-of-46 crosswalk is not established by the unauthenticated public evidence, so the legacy roster cannot be silently reused.

## QC codes are not a clean-bill field

The S1200 QC page reports 157 imaging subjects with one or more A-E codes and warns that absence of a code does not imply absence of an issue. It also says fMRI and dMRI were only very rarely excluded for motion.

The primary manifest excludes A (focal anatomical anomaly), B (segmentation/surface error), and C (head-coil instability). D and E may remain only when the frozen 2025 cleaned product is present, with their indicators retained in the nuisance denominator. A sensitivity replay drops every A-E-coded subject. Reconstruction versions `r177` and `r227` are also retained because HCP documents a notable fMRI signature.

## The falsifiable gate

The primary statistic is `delta_mae = MAE(nuisance-only) - MAE(nuisance-plus-connectome)` on untouched test families. It passes only if the family-clustered 95% bootstrap interval has a lower bound above zero.

Two reliability checks must also pass: median edgewise ICC(2,1) across the current test/retest cohort must be at least **0.40**, and the family-clustered lower bound for within-subject minus between-subject connectome similarity must exceed zero. The 0.40 threshold is a preregistered engineering floor, not a clinical standard.

A motion-matched replay may use motion, run availability, reconstruction version, and QC only—never cognition or connectivity. Its `delta_mae` interval must remain above zero and its point estimate must retain at least 80% of the primary gain.

## What is and is not ready

The formal parser passes **{checks['passed']}/{checks['total']}** checks over **{len(result['source']['snapshots'])}** hash-bound official snapshots. The public contract is ready. Execution remains blocked by registered imaging access, approved restricted family/demographic access, and reconstruction of the exact current processed roster. No participant row, image, connectome, cognition outcome, model, diagnosis, identity inference, causal cognition, clinical-utility, or solved-frontier claim is produced.

## Official sources

- [HCP-YA 2025 release](https://www.humanconnectome.org/study/hcp-young-adult/document/hcp-young-adult-2025-release)
- [HCP-YA data releases](https://humanconnectome.org/study/hcp-young-adult/data-releases)
- [HCP-YA data dictionary CSV](https://wiki.humanconnectome.org/docs/assets/HCP_S1200_DataDictionary_Oct_30_2023.csv)
- [Family-structure and retest update](https://www.humanconnectome.org/study/hcp-young-adult/article/s1200-family-structure-test-retest-interval-updates)
- [HCP-YA QC issue codes](https://wiki.humanconnectome.org/docs/HCP%20Subjects%20with%20Identified%20Quality%20Control%20Issues%20%28QC_Issue%20measure%20codes%20explained%29.html)
- [HCP-YA known issues](https://wiki.humanconnectome.org/docs/HCP%20Data%20Release%20Updates%20Known%20Issues%20and%20Planned%20fixes.html)
- [Open and restricted data-use terms](https://www.humanconnectome.org/study/hcp-young-adult/data-use-terms)
- [HCP-MMP1.0 overview](https://humanconnectome.org/study/hcp-young-adult/article/nature-article-cortical-brain-maps-at-the-highest-resolution-to-date)
- [HCP-YA 2025 Appendix III](https://humanconnectome.org/storage/app/media/documentation/HCP-YA2025/HCP-YA_2025_Release_Appendix_III.pdf)
"""
    path.write_text(text, encoding="utf-8")


def write_discussion(result: dict[str, Any], path: Path) -> None:
    checks = result["formal_checks"]
    text = f"""Can a connectome predict cognition—or only family resemblance, head motion, and scanner history?

The seductive result in connectomics is an accurate cognitive predictor. The dangerous result looks identical until relatives, motion, reconstruction version, regional anatomy, and preprocessing are forced into the room first.

The #059 HCP-YA 2025 contract now freezes that confrontation. The target is the unadjusted NIH Toolbox Fluid Cognition Composite. The nuisance-only model gets exact age, gender, education, four-run motion summaries, run availability, reconstruction version, QC A-E indicators, intracranial volume, and all 68 regional cortical-thickness fields. It gets **zero connectivity edges**.

Only then may a second ridge model add 64,620 Fisher-z edges from a 360-area HCP-MMP1.0 connectome built from the 2025 Reclean+tICA resting-state product. No S1200 2017 processing may be mixed in. Entire biological families—not subjects or scans—enter a deterministic 70/15/15 split.

The public evidence exposes an uncomfortable retest mismatch: the 2017 interval table and BALSA project describe 46 retested subjects, while the 2025 processed release contains 45. Without an exact current crosswalk, which single subject would you drop—and what evidence would make that choice non-arbitrary?

The prediction gate is intentionally severe:

- family-held-out `delta_mae` must have a clustered 95% lower bound above zero;
- median edgewise test/retest ICC(2,1) must reach the preregistered 0.40 engineering floor;
- within-subject connectome similarity must beat between-subject similarity; and
- a cognition-blind motion-matched replay must preserve a positive interval and at least 80% of the gain.

Which failure would change your mind fastest?

1. the gain vanishes when twins and siblings cannot cross the split;
2. the gain survives family separation but collapses after motion matching;
3. prediction improves while edge reliability stays below 0.40;
4. the 45-subject current retest roster cannot be reconstructed without guessing; or
5. anatomy alone explains nearly everything attributed to connectivity?

And a harder design question: should QC-D/E subjects remain in the primary cohort when HCP says FIX-cleaned scans are reasonable, or should every A-E code be excluded even at the cost of power?

Useful contributions are falsifiable: a lawful current-roster crosswalk, a correction to the frozen fields, a better cognition-blind motion matching rule, a family-safe split audit, or a reliability threshold you can defend before seeing outcomes.

Reproducibility: **{checks['passed']}/{checks['total']}** formal checks over **{len(result['source']['snapshots'])}** hash-bound official snapshots; an independent parser is run separately. No participant data, image, connectome, cognition outcome, model, diagnosis, identity inference, causal cognition, clinical utility, or solved-frontier claim is made.
"""
    path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--appendix-pdf", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    benchmark = read_json(args.benchmark)
    if args.capture:
        capture_sources(args.benchmark, benchmark, args.source_dir, args.appendix_pdf)
    result = build_result(args.benchmark, benchmark, args.source_dir)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(pretty_json(result), encoding="utf-8")
    write_report(result, args.report)
    write_discussion(result, args.discussion)
    print(
        f"P059 formal checks: {result['formal_checks']['passed']}/{result['formal_checks']['total']} "
        f"decision={result['readiness_decision']['ready_label']}"
    )
    return 0 if result["formal_checks"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
