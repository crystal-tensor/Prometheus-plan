#!/usr/bin/env python3
"""Capture and audit the public P054 ITP endpoint/safety ontology."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import platform
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P054_itp_endpoint_safety_ontology_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P054_itp_endpoint_safety_source_v1"
DEFAULT_RESULT = ROOT / "results/P054_itp_endpoint_safety_ontology_v1.json"
DEFAULT_AUDIT = ROOT / "results/P054_itp_endpoint_safety_ontology_audit_v1.json"
DEFAULT_REPORT = ROOT / "research/P054_itp_endpoint_safety_ontology_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/P054_itp_endpoint_safety_discussion_v1.md"
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


def write_gzip(path: Path, payload: bytes) -> None:
    path.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))


def read_gzip(path: Path) -> bytes:
    return gzip.decompress(path.read_bytes())


def fetch_bytes(url: str, attempts: int = 4, timeout: int = 90) -> bytes:
    last_error: Exception | None = None
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    for attempt in range(attempts):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.content
        except Exception as exc:  # pragma: no cover - network path
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1 + attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def capture_sources(benchmark: dict[str, Any], source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    for name, url in benchmark["sources"].items():
        write_gzip(source_dir / f"{name}.html.gz", fetch_bytes(url))


def load_sources(
    benchmark: dict[str, Any], source_dir: Path
) -> dict[str, bytes]:
    return {
        name: read_gzip(source_dir / f"{name}.html.gz")
        for name in benchmark["sources"]
    }


def source_inventory(source_dir: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256_path(path),
        }
        for path in sorted(source_dir.iterdir())
        if path.is_file()
    ]


def html_text(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<script.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def normalized_label(value: str) -> str:
    return value.lstrip("•").strip()


def parse_portal(payload: bytes, base_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(payload, "html.parser")
    table = soup.select_one("table#table_white")
    if table is None:
        raise RuntimeError("ITP portal result table not found")
    rows = []
    for tr in table.select("tbody tr"):
        cells = tr.find_all("td", recursive=False)
        if len(cells) != 7:
            raise RuntimeError(f"unexpected ITP row width: {len(cells)}")
        links = [
            {
                "label": normalized_label(anchor.get_text(" ", strip=True)),
                "url": urljoin(base_url, str(anchor.get("href") or "")),
            }
            for anchor in cells[5].find_all("a")
        ]
        survival_anchor = cells[4].find("a", href=True)
        rows.append(
            {
                "compound": cells[0].get_text(" ", strip=True),
                "cohort": cells[1].get_text(" ", strip=True),
                "dose_in_food": cells[2].get_text(" ", strip=True),
                "age_at_initiation": cells[3].get_text(" ", strip=True),
                "lifespan_summary": cells[4].get_text(" ", strip=True),
                "survival_url": urljoin(
                    base_url,
                    str(survival_anchor.get("href") if survival_anchor else ""),
                ),
                "other_phenotypes": links,
                "reference": cells[6].get_text(" ", strip=True),
            }
        )
    supplementary = [
        {
            "label": anchor.get_text(" ", strip=True),
            "url": urljoin(base_url, str(anchor.get("href") or "")),
        }
        for anchor in soup.find_all("a", href=True)
        if "supplementary file" in anchor.get_text(" ", strip=True)
    ]
    protocol_title = soup.find(
        lambda tag: tag.name == "h4"
        and "Interventions Testing Program: Effects" in tag.get_text(" ", strip=True)
    )
    title_text = protocol_title.get_text(" ", strip=True) if protocol_title else ""
    year_match = re.search(r"\((\d{4}-\d{4})\)", title_text)
    return {
        "study_title": title_text,
        "study_year_span": year_match.group(1) if year_match else None,
        "rows": rows,
        "supplementary_workbooks": supplementary,
    }


def parse_pathology(payload: bytes) -> list[dict[str, Any]]:
    soup = BeautifulSoup(payload, "html.parser")
    rows: list[dict[str, Any]] = []
    for button in soup.find_all("button"):
        label = button.get_text(" ", strip=True)
        match = re.fullmatch(r"Analysis details -- (Female|Male)", label)
        if not match:
            continue
        table = button.find_next("table")
        if table is None:
            continue
        for tr in table.find_all("tr")[1:]:
            cells = tr.find_all("td")
            if len(cells) != 3:
                continue
            rows.append(
                {
                    "sex": match.group(1).lower(),
                    "organ_or_condition": cells[0].get_text(" ", strip=True),
                    "odds_ratio": float(cells[1].get_text(" ", strip=True)),
                    "p_value": float(cells[2].get_text(" ", strip=True)),
                }
            )
    return rows


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def has_phrase(text: str, phrase: str) -> bool:
    return phrase.casefold() in text.casefold()


def portal_coverage(
    rows: list[dict[str, Any]], mapping: dict[str, list[str]]
) -> dict[str, Any]:
    function_labels = set(mapping["physical_function"])
    physiology_labels = set(mapping["physiology_and_body_composition"])
    pathology_labels = set(mapping["pathology_and_tumor"])
    toxicity_labels = set(mapping["exposure_and_pilot_toxicity"])
    enriched = []
    for row in rows:
        labels = {item["label"] for item in row["other_phenotypes"]}
        classes = {
            "survival_and_censoring": bool(row["survival_url"]),
            "physical_function": bool(labels & function_labels),
            "physiology_and_body_composition": bool(labels & physiology_labels),
            "pathology_and_tumor": bool(labels & pathology_labels),
            "exposure_and_pilot_toxicity": bool(labels & toxicity_labels),
        }
        enriched.append(
            {
                "compound": row["compound"],
                "cohort": row["cohort"],
                "linked_labels": sorted(labels),
                "linked_classes": sorted(
                    name for name, present in classes.items() if present
                ),
                "survival_function_pathology": (
                    classes["survival_and_censoring"]
                    and classes["physical_function"]
                    and classes["pathology_and_tumor"]
                ),
                "full_linked_gate": all(
                    classes[name]
                    for name in [
                        "survival_and_censoring",
                        "physical_function",
                        "pathology_and_tumor",
                        "exposure_and_pilot_toxicity",
                    ]
                ),
            }
        )
    return {
        "rows": enriched,
        "rows_with_survival": sum(
            "survival_and_censoring" in row["linked_classes"]
            for row in enriched
        ),
        "rows_with_any_other_phenotype": sum(
            bool(row["linked_labels"]) for row in enriched
        ),
        "rows_with_physical_function": sum(
            "physical_function" in row["linked_classes"]
            for row in enriched
        ),
        "rows_with_physiology": sum(
            "physiology_and_body_composition" in row["linked_classes"]
            for row in enriched
        ),
        "rows_with_pathology": sum(
            "pathology_and_tumor" in row["linked_classes"]
            for row in enriched
        ),
        "rows_with_linked_pilot_toxicity": sum(
            "exposure_and_pilot_toxicity" in row["linked_classes"]
            for row in enriched
        ),
        "rows_with_survival_function_pathology": sum(
            row["survival_function_pathology"] for row in enriched
        ),
        "rows_with_full_linked_gate": sum(
            row["full_linked_gate"] for row in enriched
        ),
    }


def build_result(
    benchmark_path: Path,
    benchmark: dict[str, Any],
    source_dir: Path,
    sources: dict[str, bytes],
    protocol_commit: str,
) -> dict[str, Any]:
    portal = parse_portal(
        sources["jax_itp_portal"], benchmark["sources"]["jax_itp_portal"]
    )
    portal_rows = portal["rows"]
    pathology_rows = parse_pathology(sources["jax_acarbose_pathology"])
    texts = {name: html_text(payload) for name, payload in sources.items()}
    expected = benchmark["expected_public_portal"]
    label_counts = Counter(
        item["label"]
        for row in portal_rows
        for item in row["other_phenotypes"]
    )
    unique_compounds = {row["compound"] for row in portal_rows}
    unique_cohorts = {row["cohort"] for row in portal_rows}
    unique_keys = {(row["compound"], row["cohort"]) for row in portal_rows}
    coverage = portal_coverage(portal_rows, benchmark["portal_label_mapping"])
    acarbose = next(
        row
        for row in portal_rows
        if row["compound"] == benchmark["acarbose_c2013_sentinel"]["compound"]
        and row["cohort"] == benchmark["acarbose_c2013_sentinel"]["cohort"]
    )
    acarbose_labels = {
        item["label"] for item in acarbose["other_phenotypes"]
    }
    pathology_conditions = {
        row["organ_or_condition"] for row in pathology_rows
    }
    male_lung_tumor = next(
        row
        for row in pathology_rows
        if row["sex"] == "male"
        and row["organ_or_condition"] == "Lung tumor"
    )
    rows_without_other = [
        row for row in portal_rows if not row["other_phenotypes"]
    ]
    controls = {
        "positive": {
            "passed": (
                set(
                    benchmark["acarbose_c2013_sentinel"][
                        "expected_other_phenotype_labels"
                    ]
                )
                == acarbose_labels
                and any(
                    row["compound"] == acarbose["compound"]
                    and row["cohort"] == acarbose["cohort"]
                    and row["survival_function_pathology"]
                    for row in coverage["rows"]
                )
            ),
            "detail": "Acarbose C2013 links survival, physical function, physiology, and pathology.",
        },
        "negative": {
            "passed": bool(rows_without_other)
            and all(not row["other_phenotypes"] for row in rows_without_other),
            "detail": (
                f"{len(rows_without_other)} rows retain an empty/not-linked "
                "other-phenotype state; none is recoded as no harm."
            ),
        },
    }
    expected_label_counts = expected["other_phenotype_label_counts"]
    inventory = source_inventory(source_dir)
    nia_about = texts["nia_about_itp"]
    nia_application = texts["nia_application_instructions"]
    jax_protocol = texts["jax_itp_protocol"]
    portal_snapshot = {
        "study_identifier": expected["study_identifier"],
        "study_title": portal["study_title"],
        "study_year_span": portal["study_year_span"],
        "compound_cohort_rows": len(portal_rows),
        "unique_compounds": len(unique_compounds),
        "unique_cohorts": len(unique_cohorts),
        "survival_links": sum(bool(row["survival_url"]) for row in portal_rows),
        "rows_with_other_phenotype_links": sum(
            bool(row["other_phenotypes"]) for row in portal_rows
        ),
        "other_phenotype_links": sum(
            len(row["other_phenotypes"]) for row in portal_rows
        ),
        "other_phenotype_label_counts": dict(sorted(label_counts.items())),
        "supplementary_workbook_links": len(
            portal["supplementary_workbooks"]
        ),
        "portal_rows": portal_rows,
        "supplementary_workbooks": portal["supplementary_workbooks"],
    }
    expected_snapshot = {
        key: expected[key]
        for key in [
            "study_identifier",
            "study_year_span",
            "compound_cohort_rows",
            "unique_compounds",
            "unique_cohorts",
            "survival_links",
            "rows_with_other_phenotype_links",
            "other_phenotype_links",
            "supplementary_workbook_links",
        ]
    }
    observed_snapshot = {
        key: portal_snapshot[key] for key in expected_snapshot
    }
    checks = [
        check(
            "schema_version",
            benchmark["schema_version"]
            == "p054_itp_endpoint_safety_ontology_v1",
            benchmark["schema_version"],
        ),
        check(
            "scope_only_p054",
            benchmark["scope"]["included_catalog_problem_ids"] == [54],
            "Only catalog problem #054 is included.",
        ),
        check(
            "protocol_commit",
            bool(re.fullmatch(r"[0-9a-f]{40}", protocol_commit)),
            protocol_commit,
        ),
        check(
            "source_inventory",
            len(inventory) == len(benchmark["sources"]) == 5,
            f"{len(inventory)} official HTML snapshots retained.",
        ),
        check(
            "nia_three_site_um_het3",
            all(
                has_phrase(nia_about, phrase)
                for phrase in [
                    "three testing sites",
                    "University of Michigan",
                    "Jackson Lab",
                    "University of Texas Health Science Center at San Antonio",
                    "male and female mice of the UM-HET3 stock",
                ]
            ),
            "NIA three-site, both-sex, genetically heterogeneous design found.",
        ),
        check(
            "nia_pilot_toxicity",
            all(
                has_phrase(nia_about, phrase)
                for phrase in [
                    "initial pilot testing",
                    "stability in rodent chow",
                    "plasma levels",
                    "toxicity following eight weeks of treatment",
                ]
            ),
            "NIA pilot exposure/toxicity components found.",
        ),
        check(
            "nia_power_boundary",
            has_phrase(nia_about, "80% power to detect a 10% increase in lifespan"),
            "Stage I power statement found.",
        ),
        check(
            "nia_stage_two_expansion",
            has_phrase(nia_about, "Stage II")
            and has_phrase(
                nia_about, "measures of health, pathology, and biochemical mechanism"
            ),
            "Stage II health/pathology/mechanism expansion found.",
        ),
        check(
            "nia_publication_boundary",
            has_phrase(
                nia_about, "All lifespan results, both positive and negative"
            )
            and has_phrase(nia_about, "following publication"),
            "Publication-dependent public release boundary found.",
        ),
        check(
            "nia_application_safety",
            has_phrase(nia_application, "Safety Information")
            and has_phrase(nia_application, "harmful side effects")
            and has_phrase(nia_application, "toxicities noted"),
            "Application safety/toxicity disclosure requirement found.",
        ),
        check(
            "jax_subset_boundary",
            has_phrase(jax_protocol, "MPD houses data for a subset of ITP studies")
            and has_phrase(jax_protocol, "more data will be added over time"),
            "Portal absence is bounded as subset/release coverage.",
        ),
        check(
            "jax_two_stage_design",
            has_phrase(jax_protocol, "Stage 1: Focuses on lifespan")
            and has_phrase(jax_protocol, "Stage 2: Studies follow-up")
            and has_phrase(jax_protocol, "cross-sectional pathology analysis"),
            "JAX Stage I/II endpoint distinction found.",
        ),
        check(
            "portal_snapshot_exact",
            observed_snapshot == expected_snapshot,
            pretty_json(observed_snapshot).strip(),
        ),
        check(
            "portal_rows_unique",
            len(unique_keys) == len(portal_rows),
            f"{len(unique_keys)}/{len(portal_rows)} unique compound-cohort keys.",
        ),
        check(
            "portal_label_counts_exact",
            dict(label_counts) == expected_label_counts,
            pretty_json(dict(sorted(label_counts.items()))).strip(),
        ),
        check(
            "lifespan_coverage",
            coverage["rows_with_survival"] == 74,
            f"{coverage['rows_with_survival']}/74 rows link survival.",
        ),
        check(
            "other_phenotype_coverage",
            coverage["rows_with_any_other_phenotype"] == 22,
            f"{coverage['rows_with_any_other_phenotype']}/74 rows link another phenotype.",
        ),
        check(
            "function_coverage",
            coverage["rows_with_physical_function"] == 2,
            f"{coverage['rows_with_physical_function']}/74 rows link physical function.",
        ),
        check(
            "pathology_coverage",
            coverage["rows_with_pathology"] == 1,
            f"{coverage['rows_with_pathology']}/74 rows link pathology.",
        ),
        check(
            "pilot_toxicity_link_absent",
            coverage["rows_with_linked_pilot_toxicity"] == 0,
            "0/74 portal rows expose a per-row pilot-toxicity link.",
        ),
        check(
            "joint_public_gate",
            coverage["rows_with_survival_function_pathology"]
            == benchmark["coverage_gate"][
                "expected_rows_with_survival_function_pathology"
            ]
            == 1
            and coverage["rows_with_full_linked_gate"]
            == benchmark["coverage_gate"]["expected_rows_with_full_linked_gate"]
            == 0,
            (
                f"survival+function+pathology="
                f"{coverage['rows_with_survival_function_pathology']}/74; "
                f"full linked gate={coverage['rows_with_full_linked_gate']}/74."
            ),
        ),
        check(
            "humane_signs_retained",
            all(
                has_phrase(jax_protocol, phrase)
                for phrase in benchmark["humane_endpoint_ontology"]["moribund_signs"]
            ),
            "All five moribund clinical signs retained.",
        ),
        check(
            "removal_categories_retained",
            all(
                has_phrase(jax_protocol, phrase)
                for phrase in benchmark["humane_endpoint_ontology"][
                    "non_natural_death_removal_categories"
                ]
            ),
            "All four non-natural-death removal categories retained.",
        ),
        check(
            "acarbose_positive_control",
            controls["positive"]["passed"],
            controls["positive"]["detail"],
        ),
        check(
            "missing_not_no_harm_control",
            controls["negative"]["passed"],
            controls["negative"]["detail"],
        ),
        check(
            "pathology_conditions_exact",
            pathology_conditions
            == set(
                benchmark["acarbose_c2013_sentinel"][
                    "expected_pathology_conditions"
                ]
            )
            and len(pathology_rows)
            == benchmark["acarbose_c2013_sentinel"]["expected_pathology_rows"],
            f"{len(pathology_rows)} sex-condition rows / {len(pathology_conditions)} conditions.",
        ),
        check(
            "male_lung_tumor_sentinel",
            male_lung_tumor["odds_ratio"]
            == benchmark["acarbose_c2013_sentinel"][
                "male_lung_tumor_odds_ratio"
            ]
            and male_lung_tumor["p_value"]
            == benchmark["acarbose_c2013_sentinel"][
                "male_lung_tumor_p_value"
            ],
            pretty_json(male_lung_tumor).strip(),
        ),
        check(
            "no_execution",
            benchmark["readiness_decision"]["animal_experiment_executed"]
            is False
            and benchmark["readiness_decision"][
                "individual_mouse_analysis_executed"
            ]
            is False
            and benchmark["readiness_decision"][
                "supplementary_workbooks_parsed"
            ]
            is False,
            "No animal experiment, individual-mouse analysis, or workbook parsing was executed.",
        ),
    ]
    if not all(item["passed"] for item in checks):
        failed = [item["name"] for item in checks if not item["passed"]]
        raise RuntimeError(f"formal checks failed: {failed}")

    ontology_ready = (
        observed_snapshot == expected_snapshot
        and dict(label_counts) == expected_label_counts
        and controls["positive"]["passed"]
        and controls["negative"]["passed"]
    )
    decision = (
        benchmark["readiness_decision"]["ontology_ready_label"]
        if ontology_ready
        else benchmark["readiness_decision"]["ontology_blocked_label"]
    )
    return {
        "schema_version": "p054_itp_endpoint_safety_ontology_result_v1",
        "as_of_date": benchmark["as_of_date"],
        "status": "pass",
        "decision": decision,
        "question": benchmark["question"],
        "program_snapshot": {
            "three_test_sites": [
                "The Jackson Laboratory",
                "University of Michigan",
                "University of Texas Health Science Center at San Antonio",
            ],
            "mouse_stock": "UM-HET3",
            "sexes": ["female", "male"],
            "pilot_components": [
                "chow stability",
                "plasma levels",
                "eight-week toxicity",
                "optional pharmacodynamic effects",
            ],
            "stage_one_primary_endpoint": "lifespan",
            "stage_one_power": "80% power to detect a 10% lifespan increase for either sex pooling sites",
            "stage_two_expansion": ["health", "pathology", "biochemical mechanism", "lifespan"],
            "release_boundary": "Public following publication; all positive and negative lifespan results are submitted for publication.",
        },
        "portal_snapshot": portal_snapshot,
        "coverage": {
            key: value for key, value in coverage.items() if key != "rows"
        },
        "coverage_rows": coverage["rows"],
        "endpoint_ontology": benchmark["endpoint_ontology"],
        "portal_label_mapping": benchmark["portal_label_mapping"],
        "humane_endpoint_ontology": benchmark["humane_endpoint_ontology"],
        "acarbose_c2013_sentinel": {
            "portal_row": acarbose,
            "pathology_rows": pathology_rows,
            "male_lung_tumor": male_lung_tumor,
            "interpretation_boundary": benchmark["acarbose_c2013_sentinel"][
                "interpretation_boundary"
            ],
        },
        "missingness_rule": benchmark["coverage_gate"]["missing_semantics"],
        "subset_boundary": benchmark["coverage_gate"]["subset_boundary"],
        "controls": controls,
        "formal_checks": checks,
        "summary": {
            "check_count": len(checks),
            "passed_checks": sum(item["passed"] for item in checks),
            "failed_checks": sum(not item["passed"] for item in checks),
            "portal_rows": len(portal_rows),
            "public_gate_executable": False,
            "animal_experiment_executed": False,
            "individual_mouse_analysis_executed": False,
            "supplementary_workbooks_parsed": False,
            "human_anti_aging_claim_ready": False,
        },
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "protocol_commit": protocol_commit,
            "source_directory": str(source_dir.relative_to(ROOT)),
            "retained_files": inventory,
            "tool": "tools/p054_itp_endpoint_safety_ontology.py",
            "python": platform.python_version(),
        },
        "interpretation_boundaries": benchmark["interpretation_boundaries"],
    }


def render_report(result: dict[str, Any]) -> str:
    portal = result["portal_snapshot"]
    coverage = result["coverage"]
    checks = result["summary"]
    sentinel = result["acarbose_c2013_sentinel"]
    male_lung = sentinel["male_lung_tumor"]
    ontology_rows = []
    for row in result["endpoint_ontology"]:
        ontology_rows.append(
            f"| `{row['class']}` | {row['public_evidence']} | "
            f"{', '.join(row['minimum_executable_fields'])} |"
        )
    return "\n".join(
        [
            "# P054 ITP endpoint and safety ontology v1",
            "",
            f"**Decision:** `{result['decision']}`.",
            "",
            "## What the public portal can actually support",
            "",
            f"The current ITP1 portal exposes `{portal['compound_cohort_rows']}` compound-cohort rows covering `{portal['unique_compounds']}` named compounds and `{portal['unique_cohorts']}` cohorts. Every row links a lifespan analysis, but only `{coverage['rows_with_any_other_phenotype']}` rows link any other phenotype.",
            "",
            "| Public linkage layer | Rows | Share of 74 |",
            "|---|---:|---:|",
            f"| Survival analysis | {coverage['rows_with_survival']} | {coverage['rows_with_survival'] / portal['compound_cohort_rows']:.1%} |",
            f"| Any other phenotype | {coverage['rows_with_any_other_phenotype']} | {coverage['rows_with_any_other_phenotype'] / portal['compound_cohort_rows']:.1%} |",
            f"| Physical function | {coverage['rows_with_physical_function']} | {coverage['rows_with_physical_function'] / portal['compound_cohort_rows']:.1%} |",
            f"| Pathology | {coverage['rows_with_pathology']} | {coverage['rows_with_pathology'] / portal['compound_cohort_rows']:.1%} |",
            f"| Per-row pilot-toxicity link | {coverage['rows_with_linked_pilot_toxicity']} | {coverage['rows_with_linked_pilot_toxicity'] / portal['compound_cohort_rows']:.1%} |",
            f"| Survival + function + pathology | {coverage['rows_with_survival_function_pathology']} | {coverage['rows_with_survival_function_pathology'] / portal['compound_cohort_rows']:.1%} |",
            f"| Full linked gate | {coverage['rows_with_full_linked_gate']} | {coverage['rows_with_full_linked_gate'] / portal['compound_cohort_rows']:.1%} |",
            "",
            "This is a coverage audit, not a claim that ITP failed to measure the missing layers. The JAX protocol explicitly says MPD houses a subset of ITP studies and will add more data. A blank portal cell therefore means `not linked in this snapshot`, never `no harm`.",
            "",
            "## Frozen endpoint ontology",
            "",
            "| Evidence class | Current public anchor | Minimum executable fields |",
            "|---|---|---|",
            *ontology_rows,
            "",
            "## Why lifespan cannot grade its own safety",
            "",
            "NIA describes a staged program: pilot chow stability, exposure and eight-week toxicity; Stage I lifespan; and Stage II health, pathology, biochemical mechanism and additional lifespan work. Those layers are complementary, not interchangeable.",
            "",
            f"Acarbose C2013 is the only portal row linking survival, physical function and pathology. Its pathology page contains eight sex-condition rows. The displayed male `Lung tumor` row reports an odds ratio of `{male_lung['odds_ratio']}` and `p={male_lung['p_value']}`. This is retained as a safety sentinel, not interpreted as causal toxicity: the page-level display does not by itself resolve necropsy denominators, multiplicity, or analysis-plan context.",
            "",
            "## Humane endpoints are analysis fields",
            "",
            "The JAX protocol lists five moribund clinical signs and four non-natural-death removal categories. Fighting, humane removal, physiological/behavioral removal, and technical loss must remain distinct event states. Collapsing them into natural death—or deleting them—can change a survival estimand and erase safety information.",
            "",
            "## Reproducibility and next falsifier",
            "",
            f"The formal packet passes `{checks['passed_checks']}/{checks['check_count']}` checks and hash-retains five official HTML snapshots. Supplementary workbook links are inventoried but their cell contents are not parsed or used in this result.",
            "",
            "The next falsifier is a row-level public manifest joining each compound, cohort, site and sex to survival status, function, pathology/tumor, pilot toxicity/exposure, denominators, missingness reasons and multiplicity rules. Until then, the frozen survival-plus-function-plus-safety gate is not executable across the portal.",
            "",
            "## Official sources",
            "",
            "- [NIA — About the ITP](https://www.nia.nih.gov/research/dab/interventions-testing-program-itp/about-itp)",
            "- [NIA — ITP application instructions](https://www.nia.nih.gov/research/dab/interventions-testing-program-itp/application-instructions)",
            "- [JAX Mouse Phenome Database — ITP portal](https://phenome.jax.org/centers/ITP)",
            "- [JAX — ITP1 project protocol](https://phenome.jax.org/projects/ITP1/protocol)",
            "- [JAX — Acarbose C2013 pathology](https://phenome.jax.org/itp/othpheno/ACA/pathology/C2013)",
            "",
            "No animal experiment, individual-mouse analysis, compound ranking, efficacy recommendation, causal toxicity conclusion, human anti-aging advice, dosing, treatment, rejuvenation, reversal, regulatory, or solved-frontier claim is made.",
            "",
        ]
    )


def render_discussion(result: dict[str, Any]) -> str:
    portal = result["portal_snapshot"]
    coverage = result["coverage"]
    checks = result["summary"]
    male_lung = result["acarbose_c2013_sentinel"]["male_lung_tumor"]
    return "\n".join(
        [
            "If a mouse lives longer but its pathology worsens, did aging reverse?",
            "",
            "A lifespan curve is seductive because it produces one clean endpoint. But what happens when function, pathology, humane removal, and pilot toxicity do not live in the same public row?",
            "",
            f"The #054 audit freezes the current ITP1 portal: `{portal['compound_cohort_rows']}` compound-cohort rows, `{portal['unique_compounds']}` named compounds, and `{portal['unique_cohorts']}` cohorts. All `{coverage['rows_with_survival']}` rows link survival, yet only `{coverage['rows_with_any_other_phenotype']}` link any other phenotype, `{coverage['rows_with_physical_function']}` link physical function, `{coverage['rows_with_pathology']}` links pathology, and `0` expose a per-row pilot-toxicity link.",
            "",
            "Only acarbose C2013 links survival, physical function, and pathology in the portal. Its displayed male `Lung tumor` row reports "
            f"OR `{male_lung['odds_ratio']}` and `p={male_lung['p_value']}`. That number is not being promoted to a causal toxicity conclusion—it is the reason a safety guardrail must remain separate from the lifespan endpoint, with denominators, multiplicity, and analysis-plan context attached.",
            "",
            "The missingness rule may be even more important: JAX says MPD holds a subset of ITP studies. An empty phenotype cell therefore means `not linked here`, not `no adverse event`, `no pathology`, or `not measured`.",
            "",
            "What minimum public row would you demand before calling an intervention a healthspan success: survival status and censor reason, a prespecified functional assay, complete necropsy/tumor denominators, pilot exposure/toxicity, and a multiplicity rule? Which one is non-negotiable, and how would you score missingness without rewarding silence?",
            "",
            "A useful contribution is a falsifiable field definition, missingness state, multiplicity rule, or link to a public ITP analysis plan—not a supplement recommendation or human dosing claim.",
            "",
            f"Reproducibility: `{checks['passed_checks']}/{checks['check_count']}` formal checks; a separate parser must independently reconstruct the portal and pathology coverage. Supplementary workbooks are link-inventoried but not parsed. No animal experiment, individual-mouse analysis, compound ranking, causal toxicity conclusion, human anti-aging advice, rejuvenation, reversal, regulatory, or solved-frontier claim is made.",
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
        capture_sources(benchmark, source_dir)
    sources = load_sources(benchmark, source_dir)
    result = build_result(
        benchmark_path,
        benchmark,
        source_dir,
        sources,
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
                "portal_rows": result["summary"]["portal_rows"],
                "result": str(args.result),
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
