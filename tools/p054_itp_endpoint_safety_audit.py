#!/usr/bin/env python3
"""Independently audit the frozen P054 ITP endpoint/safety packet."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P054_itp_endpoint_safety_ontology_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P054_itp_endpoint_safety_source_v1"
DEFAULT_RESULT = ROOT / "results/P054_itp_endpoint_safety_ontology_v1.json"
DEFAULT_AUDIT = ROOT / "results/P054_itp_endpoint_safety_ontology_audit_v1.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize_text(parts: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def normalize_label(value: str) -> str:
    return value.lstrip("•").strip()


class PortalTableParser(HTMLParser):
    """Extract the portal table without BeautifulSoup or main-tool code."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_target = False
        self.target_table_depth = 0
        self.current_row: list[dict[str, Any]] | None = None
        self.current_cell: dict[str, Any] | None = None
        self.current_link: dict[str, Any] | None = None
        self.rows: list[list[dict[str, Any]]] = []
        self.all_links: list[dict[str, str]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attr = dict(attrs)
        if tag == "table":
            if self.in_target:
                self.target_table_depth += 1
            elif attr.get("id") == "table_white":
                self.in_target = True
                self.target_table_depth = 1
        if self.in_target and tag == "tr" and self.current_row is None:
            self.current_row = []
        elif self.in_target and tag == "td" and self.current_row is not None:
            self.current_cell = {"text_parts": [], "links": []}
        if tag == "a":
            self.current_link = {
                "href": attr.get("href") or "",
                "text_parts": [],
            }

    def handle_data(self, data: str) -> None:
        if self.current_cell is not None:
            self.current_cell["text_parts"].append(data)
        if self.current_link is not None:
            self.current_link["text_parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self.current_link is not None:
            link = {
                "href": self.current_link["href"],
                "label": normalize_label(
                    normalize_text(self.current_link["text_parts"])
                ),
            }
            self.all_links.append(link)
            if self.current_cell is not None:
                self.current_cell["links"].append(link)
            self.current_link = None
        elif (
            tag == "td"
            and self.in_target
            and self.current_row is not None
            and self.current_cell is not None
        ):
            self.current_cell["text"] = normalize_text(
                self.current_cell.pop("text_parts")
            )
            self.current_row.append(self.current_cell)
            self.current_cell = None
        elif tag == "tr" and self.in_target and self.current_row is not None:
            if len(self.current_row) == 7:
                self.rows.append(self.current_row)
            self.current_row = None
            self.current_cell = None
        if tag == "table" and self.in_target:
            self.target_table_depth -= 1
            if self.target_table_depth == 0:
                self.in_target = False


class PathologyTableParser(HTMLParser):
    """Extract sex-specific pathology tables as a separate state machine."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_button = False
        self.button_parts: list[str] = []
        self.pending_sex: str | None = None
        self.in_table = False
        self.table_depth = 0
        self.current_row: list[str] | None = None
        self.current_cell_parts: list[str] | None = None
        self.rows: list[dict[str, Any]] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        del attrs
        if tag == "button":
            self.in_button = True
            self.button_parts = []
        elif tag == "table" and self.pending_sex and not self.in_table:
            self.in_table = True
            self.table_depth = 1
        elif tag == "table" and self.in_table:
            self.table_depth += 1
        elif tag == "tr" and self.in_table:
            self.current_row = []
        elif tag == "td" and self.in_table and self.current_row is not None:
            self.current_cell_parts = []

    def handle_data(self, data: str) -> None:
        if self.in_button:
            self.button_parts.append(data)
        if self.current_cell_parts is not None:
            self.current_cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "button" and self.in_button:
            label = normalize_text(self.button_parts)
            match = re.fullmatch(r"Analysis details -- (Female|Male)", label)
            if match:
                self.pending_sex = match.group(1).lower()
            self.in_button = False
        elif (
            tag == "td"
            and self.in_table
            and self.current_row is not None
            and self.current_cell_parts is not None
        ):
            self.current_row.append(normalize_text(self.current_cell_parts))
            self.current_cell_parts = None
        elif tag == "tr" and self.in_table and self.current_row is not None:
            if len(self.current_row) == 3:
                try:
                    self.rows.append(
                        {
                            "sex": self.pending_sex,
                            "organ_or_condition": self.current_row[0],
                            "odds_ratio": float(self.current_row[1]),
                            "p_value": float(self.current_row[2]),
                        }
                    )
                except ValueError:
                    pass
            self.current_row = None
            self.current_cell_parts = None
        if tag == "table" and self.in_table:
            self.table_depth -= 1
            if self.table_depth == 0:
                self.in_table = False
                self.pending_sex = None


def load_html(source_dir: Path, name: str) -> str:
    payload = gzip.decompress((source_dir / f"{name}.html.gz").read_bytes())
    return payload.decode("utf-8", errors="replace")


def parse_portal(source_dir: Path) -> tuple[list[dict[str, Any]], int]:
    parser = PortalTableParser()
    parser.feed(load_html(source_dir, "jax_itp_portal"))
    rows = []
    for cells in parser.rows:
        survival_links = cells[4]["links"]
        rows.append(
            {
                "compound": cells[0]["text"],
                "cohort": cells[1]["text"],
                "survival_links": len(survival_links),
                "other_labels": [link["label"] for link in cells[5]["links"]],
            }
        )
    supplementary = sum(
        "supplementary file" in link["label"].casefold()
        for link in parser.all_links
    )
    return rows, supplementary


def parse_pathology(source_dir: Path) -> list[dict[str, Any]]:
    parser = PathologyTableParser()
    parser.feed(load_html(source_dir, "jax_acarbose_pathology"))
    return parser.rows


def formal_check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def build_audit(
    benchmark_path: Path,
    source_dir: Path,
    result_path: Path,
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    result = read_json(result_path)
    expected = benchmark["expected_public_portal"]
    rows, supplementary = parse_portal(source_dir)
    pathology = parse_pathology(source_dir)
    labels = Counter(label for row in rows for label in row["other_labels"])
    function_labels = set(benchmark["portal_label_mapping"]["physical_function"])
    pathology_labels = set(benchmark["portal_label_mapping"]["pathology_and_tumor"])
    toxicity_labels = set(
        benchmark["portal_label_mapping"]["exposure_and_pilot_toxicity"]
    )

    def linked(row: dict[str, Any], vocabulary: set[str]) -> bool:
        return bool(set(row["other_labels"]) & vocabulary)

    function_rows = [row for row in rows if linked(row, function_labels)]
    pathology_rows = [row for row in rows if linked(row, pathology_labels)]
    toxicity_rows = [row for row in rows if linked(row, toxicity_labels)]
    joint_rows = [
        row
        for row in rows
        if row["survival_links"]
        and linked(row, function_labels)
        and linked(row, pathology_labels)
    ]
    full_rows = [
        row
        for row in joint_rows
        if linked(row, toxicity_labels)
    ]
    acarbose = next(
        row
        for row in rows
        if row["compound"] == benchmark["acarbose_c2013_sentinel"]["compound"]
        and row["cohort"] == benchmark["acarbose_c2013_sentinel"]["cohort"]
    )
    male_lung = next(
        row
        for row in pathology
        if row["sex"] == "male" and row["organ_or_condition"] == "Lung tumor"
    )
    retained = result["source"]["retained_files"]
    retained_by_path = {entry["path"]: entry for entry in retained}
    actual_source_paths = sorted(source_dir.glob("*.html.gz"))
    source_hashes_match = len(actual_source_paths) == 5 and all(
        retained_by_path.get(str(path.relative_to(ROOT)), {}).get("sha256")
        == sha256_path(path)
        for path in actual_source_paths
    )
    expected_snapshot = {
        "compound_cohort_rows": len(rows),
        "unique_compounds": len({row["compound"] for row in rows}),
        "unique_cohorts": len({row["cohort"] for row in rows}),
        "survival_links": sum(row["survival_links"] for row in rows),
        "rows_with_other_phenotype_links": sum(
            bool(row["other_labels"]) for row in rows
        ),
        "other_phenotype_links": sum(len(row["other_labels"]) for row in rows),
        "supplementary_workbook_links": supplementary,
    }
    expected_subset = {key: expected[key] for key in expected_snapshot}
    result_snapshot = {
        key: result["portal_snapshot"][key] for key in expected_snapshot
    }
    coverage = {
        "rows_with_survival": sum(bool(row["survival_links"]) for row in rows),
        "rows_with_any_other_phenotype": sum(
            bool(row["other_labels"]) for row in rows
        ),
        "rows_with_physical_function": len(function_rows),
        "rows_with_pathology": len(pathology_rows),
        "rows_with_linked_pilot_toxicity": len(toxicity_rows),
        "rows_with_survival_function_pathology": len(joint_rows),
        "rows_with_full_linked_gate": len(full_rows),
    }
    checks = [
        formal_check(
            "audit_schema_and_scope",
            benchmark["scope"]["included_catalog_problem_ids"] == [54]
            and result["schema_version"]
            == "p054_itp_endpoint_safety_ontology_result_v1",
            "Independent audit is restricted to catalog problem #054.",
        ),
        formal_check(
            "benchmark_hash",
            result["source"]["benchmark_sha256"] == sha256_path(benchmark_path),
            sha256_path(benchmark_path),
        ),
        formal_check(
            "source_hashes",
            source_hashes_match,
            f"{len(actual_source_paths)}/5 retained source files independently hashed.",
        ),
        formal_check(
            "portal_counts_against_benchmark",
            expected_snapshot == expected_subset,
            pretty_json(expected_snapshot).strip(),
        ),
        formal_check(
            "portal_counts_against_result",
            expected_snapshot == result_snapshot,
            "Independent HTMLParser counts match the main result.",
        ),
        formal_check(
            "portal_row_keys_unique",
            len({(row["compound"], row["cohort"]) for row in rows}) == len(rows),
            f"{len(rows)} unique compound-cohort rows.",
        ),
        formal_check(
            "portal_label_counts",
            dict(labels) == expected["other_phenotype_label_counts"]
            == result["portal_snapshot"]["other_phenotype_label_counts"],
            pretty_json(dict(sorted(labels.items()))).strip(),
        ),
        formal_check(
            "coverage_exact",
            coverage["rows_with_survival"] == 74
            and coverage["rows_with_any_other_phenotype"] == 22
            and coverage["rows_with_physical_function"] == 2
            and coverage["rows_with_pathology"] == 1
            and coverage["rows_with_linked_pilot_toxicity"] == 0,
            pretty_json(coverage).strip(),
        ),
        formal_check(
            "coverage_against_result",
            all(result["coverage"][key] == value for key, value in coverage.items()),
            "Independent coverage vector matches the main result.",
        ),
        formal_check(
            "joint_gate",
            len(joint_rows) == 1 and len(full_rows) == 0,
            "1/74 rows link survival+function+pathology; 0/74 link the full gate.",
        ),
        formal_check(
            "acarbose_c2013_labels",
            set(acarbose["other_labels"])
            == set(
                benchmark["acarbose_c2013_sentinel"][
                    "expected_other_phenotype_labels"
                ]
            ),
            f"{len(acarbose['other_labels'])} expected other-phenotype labels.",
        ),
        formal_check(
            "pathology_rows_and_conditions",
            len(pathology)
            == benchmark["acarbose_c2013_sentinel"]["expected_pathology_rows"]
            and {row["organ_or_condition"] for row in pathology}
            == set(
                benchmark["acarbose_c2013_sentinel"][
                    "expected_pathology_conditions"
                ]
            ),
            f"{len(pathology)} sex-condition rows independently parsed.",
        ),
        formal_check(
            "male_lung_tumor_sentinel",
            male_lung["odds_ratio"]
            == benchmark["acarbose_c2013_sentinel"][
                "male_lung_tumor_odds_ratio"
            ]
            and male_lung["p_value"]
            == benchmark["acarbose_c2013_sentinel"]["male_lung_tumor_p_value"],
            pretty_json(male_lung).strip(),
        ),
        formal_check(
            "positive_and_negative_controls",
            result["controls"]["positive"]["passed"]
            and result["controls"]["negative"]["passed"]
            and any(not row["other_labels"] for row in rows),
            "Acarbose C2013 is found; blank phenotype rows remain missing/not linked.",
        ),
        formal_check(
            "decision_boundary",
            result["decision"]
            == "endpoint_safety_ontology_ready_public_gate_not_executable"
            and result["summary"]["public_gate_executable"] is False,
            result["decision"],
        ),
        formal_check(
            "no_execution_or_human_claim",
            result["summary"]["animal_experiment_executed"] is False
            and result["summary"]["individual_mouse_analysis_executed"] is False
            and result["summary"]["supplementary_workbooks_parsed"] is False
            and result["summary"]["human_anti_aging_claim_ready"] is False,
            "No experiment, individual-level analysis, workbook parsing, or human claim.",
        ),
    ]
    failed = [item["name"] for item in checks if not item["passed"]]
    if failed:
        raise RuntimeError(f"independent audit failed: {failed}")
    return {
        "schema_version": "p054_itp_endpoint_safety_ontology_audit_v1",
        "as_of_date": benchmark["as_of_date"],
        "status": "pass",
        "decision": result["decision"],
        "scope": {"included_catalog_problem_ids": [54]},
        "parser_independence": {
            "main_parser": "BeautifulSoup HTML parser",
            "audit_parser": "Python standard-library html.parser state machines",
            "imports_main_tool": False,
        },
        "observed_portal": expected_snapshot,
        "observed_label_counts": dict(sorted(labels.items())),
        "observed_coverage": coverage,
        "observed_pathology": {
            "rows": pathology,
            "male_lung_tumor_sentinel": male_lung,
        },
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
            "tool": "tools/p054_itp_endpoint_safety_audit.py",
            "protocol_commit": result["source"]["protocol_commit"],
        },
        "interpretation_boundary": (
            "This independently reconstructs public linkage coverage only. "
            "Missing links are not evidence of no harm or non-measurement."
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
        args.benchmark.resolve(),
        args.source_dir.resolve(),
        args.result.resolve(),
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
                "audit_sha256": (
                    sha256_path(args.audit) if args.audit.exists() else None
                ),
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
