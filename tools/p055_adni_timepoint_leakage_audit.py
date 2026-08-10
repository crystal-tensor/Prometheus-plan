#!/usr/bin/env python3
"""Independently audit the frozen P055 ADNI timepoint/leakage packet."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P055_adni_timepoint_leakage_manifest_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P055_adni_timepoint_leakage_source_v1"
DEFAULT_RESULT = ROOT / "results/P055_adni_timepoint_leakage_manifest_v1.json"
DEFAULT_AUDIT = ROOT / "results/P055_adni_timepoint_leakage_audit_v1.json"
CAPTURE_MANIFEST = "capture_manifest.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def normalize_text(parts: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


class SemanticHTMLParser(HTMLParser):
    """Collect visible text and table cells using only the standard library."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text_parts: list[str] = []
        self.in_table = False
        self.table_depth = 0
        self.current_table: list[list[str]] | None = None
        self.current_row: list[str] | None = None
        self.current_cell: list[str] | None = None
        self.tables: list[list[list[str]]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        if tag == "table" and not self.in_table:
            self.in_table = True
            self.table_depth = 1
            self.current_table = []
        elif tag == "table" and self.in_table:
            self.table_depth += 1
        elif tag == "tr" and self.in_table:
            self.current_row = []
        elif tag in {"td", "th"} and self.in_table and self.current_row is not None:
            self.current_cell = []

    def handle_data(self, data: str) -> None:
        self.text_parts.append(data)
        if self.current_cell is not None:
            self.current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if (
            tag in {"td", "th"}
            and self.in_table
            and self.current_row is not None
            and self.current_cell is not None
        ):
            self.current_row.append(normalize_text(self.current_cell))
            self.current_cell = None
        elif tag == "tr" and self.in_table and self.current_row is not None:
            if self.current_row and self.current_table is not None:
                self.current_table.append(self.current_row)
            self.current_row = None
            self.current_cell = None
        if tag == "table" and self.in_table:
            self.table_depth -= 1
            if self.table_depth == 0:
                if self.current_table:
                    self.tables.append(self.current_table)
                self.in_table = False
                self.current_table = None


def load_parser(source_dir: Path, name: str) -> SemanticHTMLParser:
    payload = gzip.decompress((source_dir / f"{name}.html.gz").read_bytes())
    parser = SemanticHTMLParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    return parser


def dictionary_rows(source_dir: Path, name: str) -> list[dict[str, str]]:
    parser = load_parser(source_dir, name)
    keys = ["term", "definition", "code", "phase", "table", "crf"]
    for table in parser.tables:
        if not table:
            continue
        if table[0][:6] != ["Term", "Definition", "Code", "Phase", "Table", "CRF"]:
            continue
        return [dict(zip(keys, row[:6])) for row in table[1:] if len(row) >= 6]
    return []


def visible_text(source_dir: Path, name: str) -> str:
    return normalize_text(load_parser(source_dir, name).text_parts)


def exact_rows(
    rows: list[dict[str, str]], term: str, table: str | None = None
) -> list[dict[str, str]]:
    selected = [row for row in rows if row["term"].casefold() == term.casefold()]
    if table is not None:
        selected = [row for row in selected if row["table"] == table]
    return selected


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def build_audit(
    benchmark_path: Path, source_dir: Path, result_path: Path
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    result = read_json(result_path)
    capture = read_json(source_dir / CAPTURE_MANIFEST)
    by_name = {entry["name"]: entry for entry in capture["sources"]}
    source_rows = []
    source_hashes_valid = len(by_name) == len(benchmark["sources"]) == 15
    for name, url in benchmark["sources"].items():
        path = source_dir / f"{name}.html.gz"
        gzip_hash = sha256_path(path)
        normalized_hash = sha256_bytes(gzip.decompress(path.read_bytes()))
        entry = by_name.get(name, {})
        valid = (
            entry.get("requested_url") == url
            and entry.get("gzip_sha256") == gzip_hash
            and entry.get("normalized_html_sha256") == normalized_hash
            and bool(re.fullmatch(r"[0-9a-f]{64}", entry.get("raw_sha256", "")))
        )
        source_hashes_valid = source_hashes_valid and valid
        source_rows.append(
            {
                "name": name,
                "gzip_sha256": gzip_hash,
                "normalized_html_sha256": normalized_hash,
                "raw_sha256": entry.get("raw_sha256"),
                "valid": valid,
            }
        )

    d_ptau = dictionary_rows(source_dir, "dictionary_ptau217")
    d_total = dictionary_rows(source_dir, "dictionary_total13")
    d_age = dictionary_rows(source_dir, "dictionary_age_baseline")
    d_sex = dictionary_rows(source_dir, "dictionary_ptgender")
    d_apoe = dictionary_rows(source_dir, "dictionary_genotype")
    d_dx = dictionary_rows(source_dir, "dictionary_diagnosis")
    d_family = dictionary_rows(source_dir, "dictionary_familyid")
    expected = benchmark["expected_dictionary"]
    ptau = [
        row
        for row in d_ptau
        if row["table"] == expected["ptau217_table"]["table"]
    ]
    total = exact_rows(d_total, "TOTAL13", "ADAS")
    age = exact_rows(d_age, "AGE", "ADNIMERGE")
    sex = exact_rows(d_sex, "PTGENDER", "PTDEMOG")
    apoe = exact_rows(d_apoe, "GENOTYPE", "APOERES")
    diagnosis = exact_rows(d_dx, "DIAGNOSIS", "DXSUM")
    family = exact_rows(d_family, "FAMILYID")
    phase_total = " ".join(row["phase"] for row in total)
    phase_sex = " ".join(row["phase"] for row in sex)
    phase_apoe = " ".join(row["phase"] for row in apoe)
    ptau_fields = [row["term"] for row in ptau]
    doc_about = visible_text(source_dir, "adni_about")
    doc_anatomy = visible_text(source_dir, "adni_anatomy")
    doc_access = visible_text(source_dir, "adni_data_access")
    contract = benchmark["frozen_prediction_contract"]
    independently_expected_manifest_rows = (
        5  # participant, primary site, procedure site, schedule label, actual date
        + 1  # mechanism signature
        + len(contract["denominator"])
        + 1  # future outcome
        + 1  # unresolved family group
    )
    independent_coverage = {
        "manifest_rows": independently_expected_manifest_rows,
        "rows_with_public_anchor": independently_expected_manifest_rows - 1,
        "rows_without_public_anchor": 1,
        "ptau217_dictionary_rows": len(ptau),
        "total13_phase_rows": len(total),
        "familyid_exact_dictionary_rows": len(family),
        "leakage_sentinels": len(benchmark["post_baseline_leakage_sentinels"]),
        "eligible_participant_count_known": False,
        "site_holdout_executable": False,
        "family_separation_executable": False,
        "model_executable": False,
    }
    checks = [
        check(
            "audit_schema_and_scope",
            result["schema_version"]
            == "p055_adni_timepoint_leakage_manifest_result_v1"
            and benchmark["scope"]["included_catalog_problem_ids"] == [55],
            "Independent audit is restricted to catalog problem #055.",
        ),
        check(
            "benchmark_hash",
            result["source"]["benchmark_sha256"] == sha256_path(benchmark_path)
            == capture["benchmark_sha256"],
            sha256_path(benchmark_path),
        ),
        check(
            "source_hashes",
            source_hashes_valid,
            f"{sum(row['valid'] for row in source_rows)}/15 sources independently hash-verified.",
        ),
        check(
            "access_boundary",
            all(
                phrase.casefold() in doc_access.casefold()
                for phrase in [
                    "LONI Image and Data Archive",
                    "approved researchers",
                    "Data Use Agreement",
                ]
            ),
            "Approved IDA access boundary independently recovered.",
        ),
        check(
            "study_design",
            all(
                phrase.casefold() in doc_about.casefold()
                for phrase in ["longitudinal", "multi-site", "observational"]
            ),
            "Longitudinal, multi-site, observational design independently recovered.",
        ),
        check(
            "structural_time_fields",
            all(
                phrase.casefold() in doc_anatomy.casefold()
                for phrase in ["RID", "PTID", "SITEID", "VISCODE2", "EXAMDATE"]
            ),
            "Structural participant/site/time fields independently recovered.",
        ),
        check(
            "ptau_table",
            len(ptau) == expected["ptau217_table"]["expected_row_count"]
            and ptau_fields == expected["ptau217_table"]["expected_fields"],
            f"{len(ptau)} ordered pTau217-table rows.",
        ),
        check(
            "signature_field",
            any(
                row["term"] == "pT217_AB42_F"
                and row["definition"] == "pTau217/ABeta42 ratio measured by fujirebio"
                and row["code"] == "-4=Insufficient sample"
                for row in ptau
            ),
            "Frozen signature definition and missing code independently recovered.",
        ),
        check(
            "total13_rows",
            len(total) == 3
            and all(token in phase_total for token in ["ADNI1", "ADNIGO", "ADNI2", "ADNI3", "ADNI4"]),
            f"{len(total)} exact TOTAL13 phase rows.",
        ),
        check(
            "baseline_denominator_rows",
            len(age) == 1
            and age[0]["definition"] == "Age at baseline"
            and len(sex) == 4
            and all(token in phase_sex for token in ["ADNI1", "ADNIGO", "ADNI2", "ADNI3", "ADNI4"])
            and len(apoe) == 1
            and all(token in phase_apoe for token in ["ADNI1", "ADNIGO", "ADNI2", "ADNI3", "ADNI4"]),
            f"age={len(age)}, sex={len(sex)}, APOE={len(apoe)} exact rows.",
        ),
        check(
            "diagnosis_rows",
            len(diagnosis) >= 2
            and all(code in " ".join(row["code"] for row in diagnosis) for code in ["1", "2", "3"]),
            f"{len(diagnosis)} current DXSUM rows; phase harmonization remains required.",
        ),
        check(
            "family_unresolved",
            len(family) == 0,
            "0 exact FAMILYID rows; absence remains an unresolved public state.",
        ),
        check(
            "manifest_row_count",
            len(result["manifest_rows"]) == independently_expected_manifest_rows == 13
            and sum(row["public_anchor"] for row in result["manifest_rows"]) == 12,
            "13 roles reconstructed independently; 12 have public anchors.",
        ),
        check(
            "coverage_agreement",
            result["coverage"] == independent_coverage,
            pretty_json(independent_coverage).strip(),
        ),
        check(
            "time_and_leakage_contract",
            contract["outcome"]["target_month"] == 24
            and contract["outcome"]["allowed_month_window"] == [18, 30]
            and [row["id"] for row in benchmark["post_baseline_leakage_sentinels"]]
            == [f"L{i:02d}" for i in range(1, 10)],
            "Month-24 target and nine ordered leakage sentinels independently recovered.",
        ),
        check(
            "decision_and_no_execution",
            result["decision"]
            == "adni_timepoint_leakage_manifest_ready_execution_blocked_by_ida_access_and_family_group"
            and result["summary"]["model_executed"] is False
            and result["summary"]["participant_analysis_executed"] is False
            and result["summary"]["root_cause_claim_ready"] is False
            and result["summary"]["treatment_effect_claim_ready"] is False,
            result["decision"],
        ),
    ]
    failed = [item["name"] for item in checks if not item["passed"]]
    if failed:
        raise RuntimeError(f"independent audit failed: {failed}")
    return {
        "schema_version": "p055_adni_timepoint_leakage_audit_v1",
        "as_of_date": benchmark["as_of_date"],
        "status": "pass",
        "decision": result["decision"],
        "scope": {"included_catalog_problem_ids": [55]},
        "parser_independence": {
            "main_parser": "BeautifulSoup HTML parser",
            "audit_parser": "Python standard-library html.parser state machine",
            "imports_main_tool": False,
        },
        "observed_dictionary": {
            "ptau217_rows": ptau,
            "total13_rows": total,
            "age_rows": age,
            "sex_rows": sex,
            "apoe_rows": apoe,
            "diagnosis_rows": diagnosis,
            "familyid_exact_rows": family,
        },
        "observed_coverage": independent_coverage,
        "source_hashes": source_rows,
        "formal_checks": checks,
        "summary": {
            "check_count": len(checks),
            "passed_checks": len(checks),
            "failed_checks": 0,
        },
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "main_result": str(result_path.relative_to(ROOT)),
            "main_result_sha256": sha256_path(result_path),
            "source_directory": str(source_dir.relative_to(ROOT)),
            "tool": "tools/p055_adni_timepoint_leakage_audit.py",
            "protocol_commit": result["source"]["protocol_commit"],
        },
        "interpretation_boundary": (
            "This independently reconstructs public schema and timepoint readiness only. "
            "It does not inspect participant rows or establish cause, diagnosis, or treatment effect."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = build_audit(
        args.benchmark.resolve(), args.source_dir.resolve(), args.result.resolve()
    )
    rendered = pretty_json(audit)
    if args.check_only:
        if rendered != args.audit.read_text(encoding="utf-8"):
            raise SystemExit("check-only mismatch: rebuilt audit differs")
    else:
        args.audit.parent.mkdir(parents=True, exist_ok=True)
        args.audit.write_text(rendered, encoding="utf-8")
    print(
        pretty_json(
            {
                "status": audit["status"],
                "checks": audit["summary"]["check_count"],
                "audit_sha256": sha256_path(args.audit) if args.audit.exists() else None,
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
