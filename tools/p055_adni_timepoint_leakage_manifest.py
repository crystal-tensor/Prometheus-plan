#!/usr/bin/env python3
"""Capture and audit the public P055 ADNI timepoint/leakage manifest."""

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
DEFAULT_BENCHMARK = ROOT / "benchmarks/P055_adni_timepoint_leakage_manifest_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P055_adni_timepoint_leakage_source_v1"
DEFAULT_RESULT = ROOT / "results/P055_adni_timepoint_leakage_manifest_v1.json"
DEFAULT_REPORT = ROOT / "research/P055_adni_timepoint_leakage_manifest_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/P055_adni_timepoint_leakage_discussion_v1.md"
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


def fetch_bytes(url: str, attempts: int = 5, timeout: int = 90) -> tuple[bytes, str]:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.content, response.url
        except Exception as exc:  # pragma: no cover - network path
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(attempt + 1)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def normalize_html(payload: bytes) -> bytes:
    """Retain semantic HTML while dropping embedded media and application chrome."""
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
    normalized = "<!doctype html>\n" + str(root)
    return normalized.encode("utf-8")


def write_gzip(path: Path, payload: bytes) -> None:
    path.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))


def read_gzip(path: Path) -> bytes:
    return gzip.decompress(path.read_bytes())


def capture_sources(
    benchmark_path: Path,
    benchmark: dict[str, Any],
    source_dir: Path,
) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, url in benchmark["sources"].items():
        raw, final_url = fetch_bytes(url)
        normalized = normalize_html(raw)
        path = source_dir / f"{name}.html.gz"
        write_gzip(path, normalized)
        entries.append(
            {
                "name": name,
                "requested_url": url,
                "final_url": final_url,
                "path": str(path.relative_to(ROOT)),
                "raw_bytes": len(raw),
                "raw_sha256": sha256_bytes(raw),
                "normalized_html_bytes": len(normalized),
                "normalized_html_sha256": sha256_bytes(normalized),
                "gzip_bytes": path.stat().st_size,
                "gzip_sha256": sha256_path(path),
            }
        )
    manifest = {
        "schema_version": "p055_adni_normalized_capture_manifest_v1",
        "as_of_date": benchmark["as_of_date"],
        "benchmark": str(benchmark_path.relative_to(ROOT)),
        "benchmark_sha256": sha256_path(benchmark_path),
        "normalization": (
            "BeautifulSoup semantic HTML; script/style/media removed; attributes removed; "
            "raw transfer hashes retained in this manifest."
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
    sources = {
        name: read_gzip(source_dir / f"{name}.html.gz")
        for name in benchmark["sources"]
    }
    return sources, manifest


def html_text(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="replace")
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def parse_dictionary(payload: bytes) -> list[dict[str, str]]:
    soup = BeautifulSoup(payload, "html.parser")
    for table in soup.find_all("table"):
        headers = [
            re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip()
            for cell in table.find_all("th")
        ]
        if headers[:6] != ["Term", "Definition", "Code", "Phase", "Table", "CRF"]:
            continue
        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all("td")
            if len(cells) < 6:
                continue
            values = [
                re.sub(r"\s+", " ", cell.get_text(" ", strip=True)).strip()
                for cell in cells[:6]
            ]
            rows.append(
                dict(zip(["term", "definition", "code", "phase", "table", "crf"], values))
            )
        return rows
    return []


def exact_rows(
    rows: list[dict[str, str]], term: str, table: str | None = None
) -> list[dict[str, str]]:
    selected = [row for row in rows if row["term"].casefold() == term.casefold()]
    if table is not None:
        selected = [row for row in selected if row["table"] == table]
    return selected


def contains_all(text: str, phrases: list[str]) -> bool:
    folded = text.casefold()
    return all(phrase.casefold() in folded for phrase in phrases)


def formal_check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def source_inventory_valid(
    benchmark: dict[str, Any], source_dir: Path, manifest: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]]]:
    by_name = {entry["name"]: entry for entry in manifest["sources"]}
    checked = []
    valid = len(by_name) == len(benchmark["sources"])
    for name, url in benchmark["sources"].items():
        path = source_dir / f"{name}.html.gz"
        entry = by_name.get(name, {})
        observed_gzip_hash = sha256_path(path) if path.exists() else None
        observed_normalized_hash = (
            sha256_bytes(read_gzip(path)) if path.exists() else None
        )
        row_valid = (
            entry.get("requested_url") == url
            and entry.get("path") == str(path.relative_to(ROOT))
            and entry.get("gzip_sha256") == observed_gzip_hash
            and entry.get("normalized_html_sha256") == observed_normalized_hash
            and bool(re.fullmatch(r"[0-9a-f]{64}", entry.get("raw_sha256", "")))
        )
        valid = valid and row_valid
        checked.append(
            {
                "name": name,
                "path": str(path.relative_to(ROOT)),
                "requested_url": url,
                "raw_sha256": entry.get("raw_sha256"),
                "normalized_html_sha256": observed_normalized_hash,
                "gzip_sha256": observed_gzip_hash,
                "valid": row_valid,
            }
        )
    return valid, checked


def build_manifest_rows(contract: dict[str, Any]) -> list[dict[str, Any]]:
    signature = contract["mechanism_signature"]
    outcome = contract["outcome"]
    rows = [
        {
            "concept": "participant group",
            "table_or_source": "cross-table structural field",
            "field": "RID",
            "time_role": "all time points / grouping only",
            "public_anchor": True,
        },
        {
            "concept": "primary site holdout",
            "table_or_source": "PTID enrollment-site prefix",
            "field": "PTID",
            "time_role": "initial enrollment site / grouping only",
            "public_anchor": True,
        },
        {
            "concept": "procedure-site sensitivity",
            "table_or_source": "cross-table structural field",
            "field": "SITEID",
            "time_role": "procedure-specific / phase-aware",
            "public_anchor": True,
        },
        {
            "concept": "schedule label",
            "table_or_source": "cross-table structural field",
            "field": "VISCODE2",
            "time_role": "schedule alignment only",
            "public_anchor": True,
        },
        {
            "concept": "actual observation date",
            "table_or_source": "table-specific structural field",
            "field": "EXAMDATE | VISDATE | COLDATE",
            "time_role": "index cutoff and horizon",
            "public_anchor": True,
        },
        {
            "concept": "mechanism signature",
            "table_or_source": signature["table"],
            "field": signature["field"],
            "time_role": "baseline feature only",
            "public_anchor": True,
        },
    ]
    rows.extend(
        {
            "concept": item["concept"],
            "table_or_source": item["table"],
            "field": item["field"],
            "time_role": item["allowed_role"],
            "public_anchor": True,
        }
        for item in contract["denominator"]
    )
    rows.extend(
        [
            {
                "concept": "future outcome",
                "table_or_source": outcome["table"],
                "field": outcome["field"],
                "time_role": "18-30 months after index; target month 24",
                "public_anchor": True,
            },
            {
                "concept": "family group",
                "table_or_source": "unresolved public dictionary state",
                "field": "FAMILYID or lawful relatedness cluster",
                "time_role": "grouping only",
                "public_anchor": False,
            },
        ]
    )
    return rows


def build_result(
    benchmark_path: Path,
    benchmark: dict[str, Any],
    source_dir: Path,
    sources: dict[str, bytes],
    capture_manifest: dict[str, Any],
    protocol_commit: str,
) -> dict[str, Any]:
    texts = {name: html_text(payload) for name, payload in sources.items()}
    dictionaries = {
        name: parse_dictionary(payload)
        for name, payload in sources.items()
        if name.startswith("dictionary_")
    }
    expected = benchmark["expected_dictionary"]
    ptau_table_rows = [
        row
        for row in dictionaries["dictionary_ptau217"]
        if row["table"] == expected["ptau217_table"]["table"]
    ]
    total13_rows = exact_rows(
        dictionaries["dictionary_total13"],
        expected["total13"]["field"],
        expected["total13"]["table"],
    )
    age_rows = exact_rows(
        dictionaries["dictionary_age_baseline"],
        expected["age"]["field"],
        expected["age"]["table"],
    )
    sex_rows = exact_rows(
        dictionaries["dictionary_ptgender"],
        expected["sex"]["field"],
        expected["sex"]["table"],
    )
    sex_rows = [row for row in sex_rows if row["phase"] != "TEAM"]
    apoe_rows = exact_rows(
        dictionaries["dictionary_genotype"],
        expected["apoe"]["field"],
        expected["apoe"]["table"],
    )
    diagnosis_rows = exact_rows(
        dictionaries["dictionary_diagnosis"],
        expected["diagnosis"]["field"],
        expected["diagnosis"]["table"],
    )
    family_rows = exact_rows(
        dictionaries["dictionary_familyid"], expected["family_id"]["query"]
    )
    inventory_valid, inventory = source_inventory_valid(
        benchmark, source_dir, capture_manifest
    )
    contract = benchmark["frozen_prediction_contract"]
    manifest_rows = build_manifest_rows(contract)
    ptau_fields = [row["term"] for row in ptau_table_rows]
    total13_phase_text = " ".join(row["phase"] for row in total13_rows)
    sex_phase_text = " ".join(row["phase"] for row in sex_rows)
    apoe_phase_text = " ".join(row["phase"] for row in apoe_rows)
    diagnosis_code_text = " ".join(row["code"] for row in diagnosis_rows)
    admin_fields = ["USERDATE", "USERDATE2", "update_stamp", "ID", "record_ID"]
    leakage_ids = [row["id"] for row in benchmark["post_baseline_leakage_sentinels"]]
    checks = [
        formal_check(
            "schema_version",
            benchmark["schema_version"] == "p055_adni_timepoint_leakage_manifest_v1",
            benchmark["schema_version"],
        ),
        formal_check(
            "scope_only_p055",
            benchmark["scope"]["included_catalog_problem_ids"] == [55],
            "Only catalog problem #055 is included.",
        ),
        formal_check(
            "protocol_commit",
            bool(re.fullmatch(r"[0-9a-f]{40}", protocol_commit)),
            protocol_commit,
        ),
        formal_check(
            "capture_inventory",
            inventory_valid
            and len(inventory) == len(benchmark["sources"]) == 15
            and capture_manifest["benchmark_sha256"] == sha256_path(benchmark_path),
            f"{len(inventory)}/15 normalized official snapshots hash-verified.",
        ),
        formal_check(
            "approved_access_boundary",
            contains_all(
                texts["adni_data_access"],
                [
                    "All ADNI data are shared through the LONI Image and Data Archive",
                    "approved researchers",
                    "Data Use Agreement",
                    "online application form",
                ],
            ),
            "Public schema is visible, but row-level data require approved IDA access.",
        ),
        formal_check(
            "longitudinal_multisite_observational",
            contains_all(
                texts["adni_about"],
                ["Longitudinal", "Multi-Site", "over 60 clinical sites", "Observational"],
            ),
            "Longitudinal, 60+ site, observational design found.",
        ),
        formal_check(
            "schedule_variation",
            contains_all(
                texts["adni_schedules"],
                [
                    "schedules can vary",
                    "new participants and rollovers",
                    "diagnostic groups",
                    "M6 = month 6 follow-up",
                ],
            ),
            "Phase, rollover, and diagnostic-group schedule variation retained.",
        ),
        formal_check(
            "structural_identifiers",
            contains_all(
                texts["adni_anatomy"],
                ["RID", "PTID", "SITEID", "VISCODE2", "EXAMDATE"],
            ),
            "Participant, site, visit-label, and actual-date identifiers found.",
        ),
        formal_check(
            "administrative_fields_forbidden",
            contains_all(texts["adni_anatomy"], admin_fields)
            and contains_all(
                texts["adni_anatomy"],
                ["NO consistent relationship", "should not be used in analysis"],
            ),
            "Administrative timestamps and record IDs remain forbidden predictors.",
        ),
        formal_check(
            "viscode_phase_collision",
            contains_all(
                texts["adni_anatomy"],
                [
                    "reconciling tables based on VISCODE alone may lead to erroneous merging",
                    "same VISCODE",
                    "different EXAMDATEs",
                ],
            ),
            "VISCODE-only merges fail closed; actual dates are required.",
        ),
        formal_check(
            "site_identifier_boundary",
            contains_all(
                texts["adni_anatomy"],
                [
                    "SITEID codes used in ADNI1 are inconsistent",
                    "leading digits of the PTID",
                    "initial enrollment site",
                ],
            ),
            "PTID enrollment-site holdout and SITEID sensitivity are kept distinct.",
        ),
        formal_check(
            "ptau217_table_exact",
            len(ptau_table_rows)
            == expected["ptau217_table"]["expected_row_count"]
            and ptau_fields == expected["ptau217_table"]["expected_fields"]
            and {row["phase"] for row in ptau_table_rows}
            == {expected["ptau217_table"]["expected_phase_text"]},
            f"{len(ptau_table_rows)} rows / {len(ptau_fields)} ordered fields.",
        ),
        formal_check(
            "signature_field_exact",
            any(
                row["term"] == contract["mechanism_signature"]["field"]
                and row["definition"].casefold()
                == contract["mechanism_signature"]["definition"].casefold()
                and row["code"] == contract["mechanism_signature"]["missing_code"]
                for row in ptau_table_rows
            ),
            "pT217_AB42_F definition and insufficient-sample code found.",
        ),
        formal_check(
            "total13_phase_coverage",
            len(total13_rows) == expected["total13"]["expected_exact_rows"]
            and all(
                token in total13_phase_text
                for token in expected["total13"]["required_phase_tokens"]
            ),
            f"{len(total13_rows)} exact TOTAL13 rows cover ADNI1-GO-2-3-4.",
        ),
        formal_check(
            "baseline_age_exact",
            len(age_rows) == expected["age"]["expected_exact_rows"]
            and age_rows[0]["definition"] == expected["age"]["definition"],
            pretty_json(age_rows).strip(),
        ),
        formal_check(
            "sex_phase_coverage",
            len(sex_rows) == expected["sex"]["expected_exact_rows"]
            and all(
                token in sex_phase_text
                for token in expected["sex"]["required_phase_tokens"]
            ),
            f"{len(sex_rows)} PTDEMOG rows cover ADNI1-GO-2-3-4.",
        ),
        formal_check(
            "apoe_phase_coverage",
            len(apoe_rows) == expected["apoe"]["expected_exact_rows"]
            and all(
                token in apoe_phase_text
                for token in expected["apoe"]["required_phase_tokens"]
            ),
            pretty_json(apoe_rows).strip(),
        ),
        formal_check(
            "diagnosis_current_codes",
            len(diagnosis_rows) >= 2
            and all(
                code in diagnosis_code_text
                for code in expected["diagnosis"]["required_current_codes"]
            )
            and contains_all(
                texts["adni_diagnostic"],
                [
                    "DIAGNOSIS is the field",
                    "DXCURREN and DXCHANGE are older fields",
                    "translated into the DIAGNOSIS field",
                ],
            ),
            f"{len(diagnosis_rows)} current DXSUM dictionary rows; cross-phase harmonization retained.",
        ),
        formal_check(
            "family_group_unresolved",
            len(family_rows) == expected["family_id"]["expected_exact_rows"] == 0,
            "0 exact FAMILYID public dictionary rows; unresolved is not unrelated.",
        ),
        formal_check(
            "clinical_instrument_continuity",
            contains_all(
                texts["adni_clinical"],
                ["ADAS-COG 13", "ADNI1", "ADNIGO", "ADNI2", "ADNI3", "ADNI4"],
            ),
            "ADAS-Cog13 presence across study phases found.",
        ),
        formal_check(
            "plasma_biomarker_anchor",
            contains_all(
                texts["adni_domain"],
                ["ptau 217", "amyloid beta 40 and 42", "ADNI Biomarker Core"],
            ),
            "Public plasma pTau217 and amyloid biomarker anchor found.",
        ),
        formal_check(
            "missingness_heterogeneity",
            contains_all(
                texts["adni_faq"],
                ["-1", "-4", "NA entries", "empty strings", "0"],
            ),
            "Table- and phase-specific missingness encodings retained.",
        ),
        formal_check(
            "cdr_diagnosis_dependence",
            contains_all(
                texts["adni_domain"],
                ["CDR is an important component", "diagnostic protocol", "mindful of this dependence"],
            ),
            "CDR cannot independently grade a diagnosis that uses CDR criteria.",
        ),
        formal_check(
            "time_contract_frozen",
            contract["time_contract"]["baseline_alignment_window_days"] == [-90, 90]
            and contract["outcome"]["target_month"] == 24
            and contract["outcome"]["allowed_month_window"] == [18, 30]
            and contract["time_contract"][
                "schedule_label_is_not_a_substitute_for_actual_date"
            ]
            is True,
            "Baseline ±90 days; future outcome month 24 within months 18-30.",
        ),
        formal_check(
            "leakage_sentinels_frozen",
            leakage_ids == [f"L{i:02d}" for i in range(1, 10)]
            and len(set(leakage_ids)) == 9,
            "Nine ordered post-baseline leakage sentinels retained.",
        ),
        formal_check(
            "positive_control",
            contract["mechanism_signature"]["allowed_role"]
            == "baseline_feature_only"
            and contract["outcome"]["estimand"]
            == "future TOTAL13 minus baseline TOTAL13",
            "Baseline signature and future outcome have non-overlapping roles.",
        ),
        formal_check(
            "negative_control",
            any("after index_date" in row["rule"] for row in benchmark["post_baseline_leakage_sentinels"])
            and any("USERDATE" in row["rule"] for row in benchmark["post_baseline_leakage_sentinels"])
            and any("VISCODE alone" in row["rule"] for row in benchmark["post_baseline_leakage_sentinels"]),
            "Post-index, administrative, and VISCODE-only leakage routes fail closed.",
        ),
        formal_check(
            "execution_and_claim_boundary",
            benchmark["readiness_decision"]["row_level_access_available"] is False
            and benchmark["readiness_decision"]["family_group_resolved"] is False
            and benchmark["readiness_decision"]["model_executed"] is False
            and benchmark["readiness_decision"]["participant_analysis_executed"] is False
            and benchmark["readiness_decision"]["root_cause_claim_ready"] is False
            and benchmark["readiness_decision"]["treatment_effect_claim_ready"] is False,
            "No row-level access, model, participant analysis, root-cause, or treatment claim.",
        ),
    ]
    failed = [item["name"] for item in checks if not item["passed"]]
    if failed:
        raise RuntimeError(f"formal checks failed: {failed}")
    ready = all(item["passed"] for item in checks)
    decision = (
        benchmark["readiness_decision"]["ready_label"]
        if ready
        else benchmark["readiness_decision"]["blocked_label"]
    )
    return {
        "schema_version": "p055_adni_timepoint_leakage_manifest_result_v1",
        "as_of_date": benchmark["as_of_date"],
        "status": "pass",
        "decision": decision,
        "question": benchmark["question"],
        "frozen_prediction_contract": contract,
        "manifest_rows": manifest_rows,
        "dictionary_snapshot": {
            "ptau217_table_rows": ptau_table_rows,
            "total13_rows": total13_rows,
            "age_rows": age_rows,
            "sex_rows": sex_rows,
            "apoe_rows": apoe_rows,
            "diagnosis_rows": diagnosis_rows,
            "familyid_exact_rows": family_rows,
        },
        "coverage": {
            "manifest_rows": len(manifest_rows),
            "rows_with_public_anchor": sum(row["public_anchor"] for row in manifest_rows),
            "rows_without_public_anchor": sum(not row["public_anchor"] for row in manifest_rows),
            "ptau217_dictionary_rows": len(ptau_table_rows),
            "total13_phase_rows": len(total13_rows),
            "familyid_exact_dictionary_rows": len(family_rows),
            "leakage_sentinels": len(leakage_ids),
            "eligible_participant_count_known": False,
            "site_holdout_executable": False,
            "family_separation_executable": False,
            "model_executable": False,
        },
        "post_baseline_leakage_sentinels": benchmark[
            "post_baseline_leakage_sentinels"
        ],
        "controls": {
            "positive": {
                "passed": True,
                "detail": "Baseline pT217_AB42_F and future TOTAL13 change remain role-separated.",
            },
            "negative": {
                "passed": True,
                "detail": "Post-index clinical data, administrative timestamps, and VISCODE-only joins remain forbidden.",
            },
        },
        "formal_checks": checks,
        "summary": {
            "check_count": len(checks),
            "passed_checks": len(checks),
            "failed_checks": 0,
            "normalized_source_snapshots": len(inventory),
            "model_executed": False,
            "participant_analysis_executed": False,
            "root_cause_claim_ready": False,
            "treatment_effect_claim_ready": False,
        },
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "protocol_commit": protocol_commit,
            "source_directory": str(source_dir.relative_to(ROOT)),
            "capture_manifest": str((source_dir / CAPTURE_MANIFEST).relative_to(ROOT)),
            "retained_normalized_sources": inventory,
            "tool": "tools/p055_adni_timepoint_leakage_manifest.py",
            "python": platform.python_version(),
        },
        "interpretation_boundaries": benchmark["interpretation_boundaries"],
    }


def render_report(result: dict[str, Any]) -> str:
    coverage = result["coverage"]
    summary = result["summary"]
    contract = result["frozen_prediction_contract"]
    manifest_lines = [
        f"| {row['concept']} | `{row['table_or_source']}` | `{row['field']}` | {row['time_role']} | {'yes' if row['public_anchor'] else 'no — unresolved'} |"
        for row in result["manifest_rows"]
    ]
    leakage_lines = [
        f"| `{row['id']}` | {row['rule']} |"
        for row in result["post_baseline_leakage_sentinels"]
    ]
    return "\n".join(
        [
            "# P055 ADNI variable/timepoint manifest and leakage sentinel v1",
            "",
            f"**Decision:** `{result['decision']}`.",
            "",
            "## The prospective question is now concrete",
            "",
            "The frozen candidate is deliberately narrow: use the baseline plasma `pT217_AB42_F` ratio to predict future `TOTAL13` change near month 24, only after age, sex, APOE genotype, baseline diagnosis, and baseline `TOTAL13` have entered the denominator. The outcome window is months 18-30, and the index date is the latest actual date among retained baseline inputs.",
            "",
            "| Role | Table or source | Field | Time rule | Public anchor |",
            "|---|---|---|---|---|",
            *manifest_lines,
            "",
            f"The public manifest contains `{coverage['manifest_rows']}` rows. `{coverage['rows_with_public_anchor']}` have a public dictionary or documentation anchor; the family grouping row remains unresolved. That missing row blocks execution rather than being silently treated as unrelated participants.",
            "",
            "## What the public dictionary establishes",
            "",
            f"The pTau217 search exposes `{coverage['ptau217_dictionary_rows']}` ordered rows for `UPENN_PLASMA_FUJIREBIO_QUANTERIX`, including participant/visit/date fields and the frozen `pT217_AB42_F` assay field across ADNI1, GO, 2, 3, and 4. `TOTAL13` has `{coverage['total13_phase_rows']}` exact phase-specific dictionary rows spanning the same five phases.",
            "",
            "This is schema evidence, not an eligible cohort. Actual rows, dates, assay completeness, site counts, and participant overlap live behind approved IDA access. The public `FAMILYID` search returns zero exact rows; that is an unresolved dictionary state, not evidence that ADNI participants are unrelated.",
            "",
            "## A visit label is not a timestamp",
            "",
            "ADNI documents that VISCODE meanings vary by phase, different actual dates can share a VISCODE, and VISCODE-only reconciliation can produce erroneous merges. `VISCODE2` is retained as a schedule label, while `EXAMDATE`, `VISDATE`, or `COLDATE` controls the feature cutoff and outcome horizon. `USERDATE`, `USERDATE2`, `update_stamp`, `ID`, and `record_ID` remain administrative fields and are never model features.",
            "",
            "The primary site split uses the stable enrollment-site prefix in `PTID`; procedure-level `SITEID` is a sensitivity analysis because ADNI1 site codes differ from later phases. All preprocessing must be fit inside training sites.",
            "",
            "## Nine fail-closed leakage sentinels",
            "",
            "| ID | Rule |",
            "|---|---|",
            *leakage_lines,
            "",
            "## Why the model remains unopened",
            "",
            "ADNI row-level data require an approved IDA account and Data Use Agreement. Without those rows, this packet cannot count eligible participants, adjudicate table-specific missingness, construct the family grouping, open site holdouts, or estimate prediction error. The public schema is ready; the experiment is not.",
            "",
            f"The formal packet passes `{summary['passed_checks']}/{summary['check_count']}` checks and hash-binds `{summary['normalized_source_snapshots']}` normalized official HTML snapshots. Raw transfer hashes are recorded in the capture manifest; embedded media and application scripts are intentionally not retained.",
            "",
            "## Next falsifier",
            "",
            "After lawful IDA access, reconstruct this exact 13-row manifest before opening outcomes: resolve a family/relatedness cluster, enumerate complete baseline and month-24 rows by enrollment site and sex, preserve missingness reasons, freeze the site split, and fail if any post-index byte enters a feature matrix. Only then may the denominator and denominator-plus-signature models be compared.",
            "",
            "## Official sources",
            "",
            "- [ADNI data access](https://adni.loni.usc.edu/data-samples/adni-data/)",
            "- [ADNI documentation — study design](https://adni.loni.usc.edu/quick-start-guide-asset101625/about.html)",
            "- [ADNI documentation — table anatomy and time identifiers](https://adni.loni.usc.edu/quick-start-guide-asset101625/anatomy2.html)",
            "- [ADNI documentation — diagnosis](https://adni.loni.usc.edu/quick-start-guide-asset101625/diagnostic.html)",
            "- [ADNI documentation — clinical assessments](https://adni.loni.usc.edu/quick-start-guide-asset101625/clinical.html)",
            "- [ADNI documentation — major biomarker tables](https://adni.loni.usc.edu/quick-start-guide-asset101625/domain.html)",
            "- [ADNI data dictionary search](https://adni.loni.usc.edu/data-samples/data-dictionary-search/)",
            "",
            "No participant data, model training, biomarker threshold, diagnosis, root-cause, treatment-effect, clinical-utility, regulatory, or solved-frontier claim is made.",
            "",
        ]
    )


def render_discussion(result: dict[str, Any]) -> str:
    coverage = result["coverage"]
    summary = result["summary"]
    return "\n".join(
        [
            "Can a biomarker predict the future if its timestamp already knows the answer?",
            "",
            "A neurodegeneration model can look impressively accurate for the wrong reason: a lab value was collected after baseline, a diagnosis code came from a later visit, two phases reused the same VISCODE, or one enrollment site leaked into both train and test.",
            "",
            "The #055 contract now freezes one testable question. Does baseline plasma `pT217_AB42_F` improve site-held-out prediction of ADAS-Cog13 `TOTAL13` change near month 24 beyond age, sex, APOE genotype, baseline diagnosis, and baseline cognition? The outcome window is months 18-30, and every feature must be dated no later than the latest retained baseline input.",
            "",
            f"The public ADNI dictionary exposes `{coverage['ptau217_dictionary_rows']}` ordered fields for the cross-phase pTau217 table and `{coverage['total13_phase_rows']}` phase-specific `TOTAL13` rows. The resulting manifest has `{coverage['manifest_rows']}` roles and `{coverage['leakage_sentinels']}` fail-closed leakage sentinels. But the exact public `FAMILYID` search yields `0` rows, and row-level data require approved IDA access. So the schema is frozen while the model remains unopened.",
            "",
            "The most dangerous ambiguity may be the clock itself. ADNI warns that VISCODE meanings vary by phase, that different actual dates can share a visit code, and that VISCODE-only joins can be wrong. This contract therefore uses actual examination or collection dates for the feature cutoff and outcome horizon; administrative timestamps are forbidden.",
            "",
            "Which rule would you make non-negotiable before trusting an ADNI progression model: a site-held-out split, a family/relatedness cluster, actual-date reconciliation, an untouched month-24 outcome, or train-only preprocessing? And what evidence would convince you that a missing family identifier has been resolved rather than ignored?",
            "",
            "A useful contribution is a falsifiable join rule, lawful relatedness field, missingness state, site-split invariant, or phase-specific data-dictionary correction—not a diagnosis or treatment recommendation.",
            "",
            f"Reproducibility: `{summary['passed_checks']}/{summary['check_count']}` formal checks over `{summary['normalized_source_snapshots']}` normalized official snapshots; a separate standard-library parser must independently reconstruct the dictionary rows, source hashes, manifest roles, and decision. No participant analysis, model, biomarker threshold, diagnosis, root-cause, treatment-effect, clinical-utility, regulatory, or solved-frontier claim is made.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument("--protocol-commit")
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    benchmark_path = args.benchmark.resolve()
    source_dir = args.source_dir.resolve()
    benchmark = read_json(benchmark_path)
    if not args.protocol_commit:
        raise SystemExit("--protocol-commit is required for a formal run")
    if args.capture:
        capture_sources(benchmark_path, benchmark, source_dir)
    sources, capture_manifest = load_sources(benchmark, source_dir)
    result = build_result(
        benchmark_path,
        benchmark,
        source_dir,
        sources,
        capture_manifest,
        args.protocol_commit,
    )
    report = render_report(result)
    discussion = render_discussion(result)
    if args.check_only:
        if pretty_json(result) != args.result.read_text(encoding="utf-8"):
            raise SystemExit("check-only mismatch: rebuilt result differs")
        if report != args.report.read_text(encoding="utf-8"):
            raise SystemExit("check-only mismatch: rebuilt report differs")
        if discussion != args.discussion.read_text(encoding="utf-8"):
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
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.discussion.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(pretty_json(result), encoding="utf-8")
    args.report.write_text(report, encoding="utf-8")
    args.discussion.write_text(discussion, encoding="utf-8")
    print(
        pretty_json(
            {
                "status": result["status"],
                "decision": result["decision"],
                "checks": result["summary"]["check_count"],
                "result": str(args.result),
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
