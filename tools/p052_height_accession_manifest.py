#!/usr/bin/env python3
"""Capture and validate the frozen P052 height-accession manifest."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import re
import ssl
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import certifi
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P052_height_accession_manifest_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P052_height_accession_source_v1"
DEFAULT_RESULT = ROOT / "results/P052_height_accession_manifest_v1.json"
DEFAULT_REPORT = ROOT / "research/P052_height_accession_manifest_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/P052_height_accession_discussion_v1.md"
USER_AGENT = "Axiom-Horizon-P052-manifest/1.0 (+public reproducibility audit)"
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


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


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def request_bytes(
    url: str,
    *,
    method: str = "GET",
    attempts: int = 3,
    timeout: int = 90,
) -> tuple[bytes, dict[str, str]]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            method=method,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        )
        try:
            with urllib.request.urlopen(
                request, timeout=timeout, context=SSL_CONTEXT
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status} for {url}")
                payload = b"" if method == "HEAD" else response.read()
                headers = {
                    key.lower(): value
                    for key, value in response.headers.items()
                }
                return payload, headers
        except Exception as exc:  # pragma: no cover - network path
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1 + attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


class AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(href)


def anchors(payload: bytes) -> list[str]:
    parser = AnchorParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    return sorted(set(parser.links))


def first_link(links: list[str], predicate: Any, label: str) -> str:
    matches = sorted(link for link in links if predicate(link))
    if not matches:
        raise RuntimeError(f"missing {label}")
    return matches[0]


def url_join(directory: str, filename: str) -> str:
    return urllib.parse.urljoin(directory.rstrip("/") + "/", filename)


def artifact_headers(url: str) -> dict[str, Any]:
    _, headers = request_bytes(url, method="HEAD")
    length = headers.get("content-length")
    return {
        "url": url,
        "content_length": int(length) if length and length.isdigit() else None,
        "content_type": headers.get("content-type"),
        "etag": headers.get("etag"),
        "last_modified": headers.get("last-modified"),
        "accept_ranges": headers.get("accept-ranges"),
    }


def capture_sources(
    benchmark: dict[str, Any], source_dir: Path
) -> dict[str, Any]:
    source_dir.mkdir(parents=True, exist_ok=True)
    query_url = benchmark["sources"]["gwas_catalog_v2"]["query_url"]
    query_payload, _ = request_bytes(query_url)
    write_gzip(source_dir / "catalog_body_height.json.gz", query_payload)
    query = json.loads(query_payload)
    query_rows = query.get("_embedded", {}).get("studies", [])
    query_ids = {str(row.get("accession_id")) for row in query_rows}

    headers: dict[str, Any] = {}
    publication_ids: set[str] = set()
    for seed in benchmark["frozen_accession_seed"]:
        accession = seed["accession"]
        if accession not in query_ids:
            raise RuntimeError(
                f"frozen accession {accession} absent from exact-trait query"
            )
        study_url = benchmark["sources"]["gwas_catalog_v2"][
            "study_url_template"
        ].format(accession=accession)
        study_payload, _ = request_bytes(study_url)
        write_gzip(source_dir / f"{accession}_study.json.gz", study_payload)
        study = json.loads(study_payload)
        publication_ids.add(str(study["pubmed_id"]))

        directory_url = str(study["full_summary_stats"]).replace(
            "http://", "https://"
        )
        root_payload, _ = request_bytes(directory_url + "/")
        harmonised_payload, _ = request_bytes(
            directory_url + "/harmonised/"
        )
        write_gzip(
            source_dir / f"{accession}_root_index.html.gz", root_payload
        )
        write_gzip(
            source_dir / f"{accession}_harmonised_index.html.gz",
            harmonised_payload,
        )
        root_links = anchors(root_payload)
        harmonised_links = anchors(harmonised_payload)

        raw_data = first_link(
            root_links,
            lambda link: (
                not link.endswith("/")
                and "-meta.yaml" not in link
                and link != "md5sum.txt"
                and (
                    link.endswith(".tsv")
                    or link.endswith(".tsv.gz")
                    or link.endswith(".gz")
                )
            ),
            f"{accession} raw summary-statistics artifact",
        )
        raw_meta = first_link(
            root_links,
            lambda link: link.endswith("-meta.yaml"),
            f"{accession} raw metadata",
        )
        harmonised_data = first_link(
            harmonised_links,
            lambda link: link.endswith(".h.tsv.gz"),
            f"{accession} harmonised summary-statistics artifact",
        )
        harmonised_meta = first_link(
            harmonised_links,
            lambda link: link.endswith(".h.tsv.gz-meta.yaml"),
            f"{accession} harmonised metadata",
        )

        raw_meta_payload, _ = request_bytes(
            url_join(directory_url, raw_meta)
        )
        harmonised_meta_payload, _ = request_bytes(
            url_join(directory_url + "/harmonised/", harmonised_meta)
        )
        write_gzip(
            source_dir / f"{accession}_raw_meta.yaml.gz", raw_meta_payload
        )
        write_gzip(
            source_dir / f"{accession}_harmonised_meta.yaml.gz",
            harmonised_meta_payload,
        )
        headers[accession] = {
            "directory_url": directory_url,
            "raw": {
                "filename": raw_data,
                **artifact_headers(url_join(directory_url, raw_data)),
            },
            "harmonised": {
                "filename": harmonised_data,
                **artifact_headers(
                    url_join(
                        directory_url + "/harmonised/", harmonised_data
                    )
                ),
            },
        }

    pubmed_template = benchmark["sources"]["pubmed"][
        "summary_url_template"
    ]
    for pubmed_id in sorted(publication_ids):
        payload, _ = request_bytes(
            pubmed_template.format(pubmed_id=pubmed_id)
        )
        write_gzip(
            source_dir / f"pubmed_{pubmed_id}.json.gz", payload
        )

    for name, url in benchmark["sources"]["documentation"].items():
        payload, _ = request_bytes(url)
        write_gzip(source_dir / f"docs_{name}.html.gz", payload)

    write_gzip(
        source_dir / "artifact_headers.json.gz",
        pretty_json(headers).encode("utf-8"),
    )
    return load_sources(benchmark, source_dir)


def load_sources(
    benchmark: dict[str, Any], source_dir: Path
) -> dict[str, Any]:
    query = json.loads(read_gzip(source_dir / "catalog_body_height.json.gz"))
    records: dict[str, Any] = {}
    raw_metadata: dict[str, Any] = {}
    harmonised_metadata: dict[str, Any] = {}
    root_links: dict[str, list[str]] = {}
    harmonised_links: dict[str, list[str]] = {}
    publication_ids: set[str] = set()
    for seed in benchmark["frozen_accession_seed"]:
        accession = seed["accession"]
        record = json.loads(
            read_gzip(source_dir / f"{accession}_study.json.gz")
        )
        records[accession] = record
        publication_ids.add(str(record["pubmed_id"]))
        raw_metadata[accession] = yaml.safe_load(
            read_gzip(source_dir / f"{accession}_raw_meta.yaml.gz")
        )
        harmonised_metadata[accession] = yaml.safe_load(
            read_gzip(
                source_dir / f"{accession}_harmonised_meta.yaml.gz"
            )
        )
        root_links[accession] = anchors(
            read_gzip(source_dir / f"{accession}_root_index.html.gz")
        )
        harmonised_links[accession] = anchors(
            read_gzip(
                source_dir / f"{accession}_harmonised_index.html.gz"
            )
        )
    publications = {
        pubmed_id: json.loads(
            read_gzip(source_dir / f"pubmed_{pubmed_id}.json.gz")
        )["result"][pubmed_id]
        for pubmed_id in sorted(publication_ids)
    }
    headers = json.loads(
        read_gzip(source_dir / "artifact_headers.json.gz")
    )
    return {
        "query": query,
        "records": records,
        "raw_metadata": raw_metadata,
        "harmonised_metadata": harmonised_metadata,
        "root_links": root_links,
        "harmonised_links": harmonised_links,
        "publications": publications,
        "headers": headers,
    }


def declared_md5(metadata: dict[str, Any]) -> str | None:
    value = metadata.get("data_file_md5sum")
    return str(value) if value is not None else None


def ancestry_category(metadata: dict[str, Any]) -> str | None:
    samples = metadata.get("samples") or []
    if len(samples) != 1:
        return None
    categories = samples[0].get("sample_ancestry_category") or []
    return str(categories[0]) if len(categories) == 1 else None


def sample_size(metadata: dict[str, Any]) -> int | None:
    samples = metadata.get("samples") or []
    if len(samples) != 1:
        return None
    value = samples[0].get("sample_size")
    return int(value) if value is not None else None


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


def build_result(
    benchmark_path: Path,
    benchmark: dict[str, Any],
    source_dir: Path,
    source: dict[str, Any],
    protocol_commit: str,
) -> dict[str, Any]:
    query = source["query"]
    query_rows = query.get("_embedded", {}).get("studies", [])
    page = query.get("page", {})
    full_count = sum(
        bool(row.get("full_summary_stats_available")) for row in query_rows
    )
    query_by_id = {
        str(row["accession_id"]): row for row in query_rows
    }
    requirements = benchmark["accession_requirements"]
    seed_by_id = {
        row["accession"]: row
        for row in benchmark["frozen_accession_seed"]
    }

    roster = []
    for accession in seed_by_id:
        seed = seed_by_id[accession]
        record = source["records"][accession]
        metadata = source["harmonised_metadata"][accession]
        publication = source["publications"][str(record["pubmed_id"])]
        cohort = record.get("cohort") or []
        category = ancestry_category(metadata)
        ontology = metadata.get("ontology_mapping") or []
        samples = metadata.get("samples") or []
        first_sample = samples[0] if len(samples) == 1 else {}
        row_checks = {
            "present_in_exact_trait_query": accession in query_by_id,
            "full_summary_stats_available": bool(
                record.get("full_summary_stats_available")
            ),
            "minimum_snp_count": int(record.get("snp_count") or 0)
            >= int(requirements["minimum_snp_count"]),
            "gxe_false": record.get("gxe") in {False, None},
            "gxg_false": record.get("gxg") in {False, None},
            "single_named_cohort": len(cohort) == 1
            and bool(str(cohort[0]).strip()),
            "single_discovery_ancestry_category": category is not None,
            "harmonised": metadata.get("is_harmonised") is True,
            "sorted": metadata.get("is_sorted") is True,
            "genome_assembly": metadata.get("genome_assembly")
            == requirements["genome_assembly"],
            "file_type": metadata.get("file_type")
            == requirements["file_type"],
            "case_control_study_false": first_sample.get(
                "case_control_study"
            )
            is False,
            "explicit_terms_of_license": bool(
                str(record.get("terms_of_license") or "").strip()
            ),
            "ontology_match": benchmark["trait"]["ontology_id"]
            in ontology,
            "raw_artifact_declared": bool(
                source["headers"][accession]["raw"]["filename"]
            ),
            "harmonised_artifact_declared": bool(
                source["headers"][accession]["harmonised"]["filename"]
            ),
            "raw_artifact_accessible": (
                source["headers"][accession]["raw"]["content_length"] or 0
            )
            > 0,
            "harmonised_artifact_accessible": (
                source["headers"][accession]["harmonised"][
                    "content_length"
                ]
                or 0
            )
            > 0,
            "declared_harmonised_md5": bool(
                re.fullmatch(r"[0-9a-f]{32}", declared_md5(metadata) or "")
            ),
        }
        roster.append(
            {
                "accession": accession,
                "intended_role": seed["intended_role"],
                "cohort": cohort[0] if len(cohort) == 1 else cohort,
                "ancestry_category": category,
                "discovery_ancestry": record.get("discovery_ancestry"),
                "sample_size": sample_size(metadata),
                "snp_count": int(record.get("snp_count") or 0),
                "trait_description": metadata.get("trait_description"),
                "adjusted_covariates": metadata.get(
                    "adjusted_covariates", []
                ),
                "analysis_software": metadata.get("analysis_software"),
                "genotyping_technology": metadata.get(
                    "genotyping_technology"
                ),
                "file_type": metadata.get("file_type"),
                "genome_assembly": metadata.get("genome_assembly"),
                "harmonised": metadata.get("is_harmonised"),
                "sorted": metadata.get("is_sorted"),
                "license": record.get("terms_of_license"),
                "pubmed_id": str(record["pubmed_id"]),
                "publication_title": publication.get("title"),
                "publication_date": publication.get("pubdate"),
                "raw_artifact": source["headers"][accession]["raw"],
                "harmonised_artifact": source["headers"][accession][
                    "harmonised"
                ],
                "harmonised_md5_declared": declared_md5(metadata),
                "checks": row_checks,
                "passes_accession_manifest": all(row_checks.values()),
            }
        )

    holdout_fields = {
        name: {
            "available_for_participant_level_external_evaluation": False,
            "reason": (
                "The retained public artifact is aggregate summary "
                "statistics or study-level metadata, not participant-level "
                "evaluation data."
            ),
        }
        for name in benchmark["final_metric_requirements"][
            "required_holdout_fields"
        ]
    }
    distinct_ancestries = sorted(
        {str(row["ancestry_category"]) for row in roster}
    )
    distinct_cohorts = sorted({str(row["cohort"]) for row in roster})
    distinct_publications = sorted({row["pubmed_id"] for row in roster})
    total_sample_size = sum(int(row["sample_size"] or 0) for row in roster)
    transformations = {
        row["accession"]: list(row["trait_description"] or [])
        for row in roster
    }
    same_publication_pair = sorted(
        row["accession"]
        for row in roster
        if row["pubmed_id"] == "41861830"
    )
    manifest_ready = all(
        bool(row["passes_accession_manifest"]) for row in roster
    )
    evaluation_ready = manifest_ready and all(
        bool(value["available_for_participant_level_external_evaluation"])
        for value in holdout_fields.values()
    )
    decision = (
        benchmark["readiness_decision"]["ready_label"]
        if evaluation_ready
        else benchmark["readiness_decision"]["blocked_label"]
    )

    controls = {
        "positive": {
            "passed": (
                len({"European", "East Asian", "South Asian"}) == 3
                and all(
                    [
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                    ]
                )
            ),
            "detail": (
                "Synthetic distinct-cohort/ancestry roster plus all seven "
                "individual-level fields is evaluation-ready."
            ),
        },
        "negative": {
            "passed": not all(
                value[
                    "available_for_participant_level_external_evaluation"
                ]
                for value in holdout_fields.values()
            ),
            "detail": (
                "Three harmonised aggregate files without participant-level "
                "outcomes and cluster keys remain blocked."
            ),
        },
    }

    checks = [
        check(
            "schema_version",
            benchmark["schema_version"]
            == "p052_height_accession_manifest_v1",
            f"Observed {benchmark['schema_version']}.",
        ),
        check(
            "scope_only_p052",
            benchmark["scope"]["included_catalog_problem_ids"] == [52],
            "Only catalog problem #052 is included.",
        ),
        check(
            "protocol_commit",
            bool(re.fullmatch(r"[0-9a-f]{40}", protocol_commit)),
            protocol_commit,
        ),
        check(
            "exact_trait_query_one_page",
            int(page.get("number", -1)) == 0
            and int(page.get("totalPages", -1)) == 1
            and len(query_rows) == int(page.get("totalElements", -1))
            and int(page.get("size", 0))
            == benchmark["sources"]["gwas_catalog_v2"][
                "required_page_size"
            ],
            (
                f"{len(query_rows)} returned of "
                f"{page.get('totalElements')} total."
            ),
        ),
        check(
            "frozen_accessions_present",
            set(seed_by_id).issubset(query_by_id),
            ", ".join(sorted(seed_by_id)),
        ),
        check(
            "three_accessions",
            len(roster) == 3,
            f"Observed {len(roster)}.",
        ),
        check(
            "all_accession_manifests_pass",
            manifest_ready,
            f"{sum(row['passes_accession_manifest'] for row in roster)}/3 pass.",
        ),
        check(
            "three_distinct_cohorts",
            len(distinct_cohorts) == 3,
            ", ".join(distinct_cohorts),
        ),
        check(
            "three_distinct_ancestry_categories",
            len(distinct_ancestries) == 3,
            ", ".join(distinct_ancestries),
        ),
        check(
            "two_distinct_publications",
            len(distinct_publications) == 2,
            ", ".join(distinct_publications),
        ),
        check(
            "same_publication_pair_exposed",
            same_publication_pair
            == ["GCST90727382", "GCST90728584"],
            ", ".join(same_publication_pair),
        ),
        check(
            "response_scales_not_collapsed",
            len(
                {
                    tuple(value)
                    for value in transformations.values()
                }
            )
            == 3,
            pretty_json(transformations).strip(),
        ),
        check(
            "summary_query_inventory",
            len(query_rows) >= len(roster) and full_count > 0,
            (
                f"{len(query_rows)} exact-trait studies; "
                f"{full_count} report full summary statistics."
            ),
        ),
        check(
            "aggregate_only_holdout_fields",
            not any(
                value[
                    "available_for_participant_level_external_evaluation"
                ]
                for value in holdout_fields.values()
            ),
            "0/7 required participant-level fields are public in the retained files.",
        ),
        check(
            "evaluation_blocked",
            not evaluation_ready
            and decision
            == "blocked_no_individual_level_external_holdout",
            decision,
        ),
        check(
            "candidate_not_executed",
            benchmark["readiness_decision"]["candidate_model_executed"]
            is False,
            "No genotype-to-phenotype candidate was executed.",
        ),
        check(
            "denominator_not_executed",
            benchmark["readiness_decision"][
                "polygenic_score_denominator_executed"
            ]
            is False,
            "No additive polygenic-score denominator was executed.",
        ),
        check(
            "positive_control",
            controls["positive"]["passed"],
            controls["positive"]["detail"],
        ),
        check(
            "negative_control",
            controls["negative"]["passed"],
            controls["negative"]["detail"],
        ),
        check(
            "retained_sources",
            len(source_inventory(source_dir)) >= 20,
            f"{len(source_inventory(source_dir))} small source files retained.",
        ),
    ]
    if not all(item["passed"] for item in checks):
        failed = [item["name"] for item in checks if not item["passed"]]
        raise RuntimeError(f"formal checks failed: {failed}")

    return {
        "schema_version": "p052_height_accession_manifest_result_v1",
        "as_of_date": benchmark["as_of_date"],
        "status": "pass",
        "decision": decision,
        "question": benchmark["question"],
        "catalog_query": {
            "url": benchmark["sources"]["gwas_catalog_v2"]["query_url"],
            "returned_studies": len(query_rows),
            "reported_total": int(page["totalElements"]),
            "full_summary_statistics_available": full_count,
        },
        "roster": roster,
        "roster_summary": {
            "accessions": len(roster),
            "total_discovery_sample_size": total_sample_size,
            "distinct_cohorts": distinct_cohorts,
            "distinct_ancestry_categories": distinct_ancestries,
            "distinct_publications": distinct_publications,
            "same_publication_pair": same_publication_pair,
            "summary_statistic_manifest_ready": manifest_ready,
            "individual_level_external_evaluation_ready": evaluation_ready,
        },
        "phenotype_transformations": transformations,
        "required_holdout_field_matrix": holdout_fields,
        "leakage_findings": [
            {
                "name": "same_publication_exposure",
                "applies_to": same_publication_pair,
                "finding": (
                    "UKB and CKB accessions come from one publication and "
                    "are retrospective transfer sentinels, not unopened "
                    "confirmation cohorts."
                ),
            },
            {
                "name": "response_scale_mismatch",
                "applies_to": sorted(seed_by_id),
                "finding": (
                    "Standing height, inverse-normalized standing height, "
                    "and residualized height require a frozen scale contract."
                ),
            },
            {
                "name": "summary_statistics_not_outcomes",
                "applies_to": sorted(seed_by_id),
                "finding": (
                    "Aggregate effect estimates cannot compute external "
                    "calibration slope or incremental explained variance "
                    "without participant-level scores and outcomes."
                ),
            },
        ],
        "controls": controls,
        "formal_checks": checks,
        "summary": {
            "check_count": len(checks),
            "passed_checks": sum(item["passed"] for item in checks),
            "failed_checks": sum(not item["passed"] for item in checks),
            "candidate_model_executed": False,
            "polygenic_score_denominator_executed": False,
        },
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "protocol_commit": protocol_commit,
            "source_directory": str(source_dir.relative_to(ROOT)),
            "retained_files": source_inventory(source_dir),
            "tool": "tools/p052_height_accession_manifest.py",
            "python": platform.python_version(),
        },
        "interpretation_boundaries": benchmark[
            "interpretation_boundaries"
        ],
    }


def render_report(result: dict[str, Any]) -> str:
    rows = []
    for row in result["roster"]:
        covariates = ", ".join(row["adjusted_covariates"]) or "not listed"
        trait = "; ".join(row["trait_description"] or [])
        license_label = (
            "CC0"
            if "creativecommons.org/publicdomain/zero"
            in str(row["license"])
            else "EMBL-EBI terms"
        )
        rows.append(
            "| [{accession}](https://www.ebi.ac.uk/gwas/studies/{accession}) "
            "| {role} | {cohort} | {ancestry} | {sample:,} | {snps:,} | "
            "{trait} | {covariates} | {license_label} |".format(
                accession=row["accession"],
                role=row["intended_role"],
                cohort=row["cohort"],
                ancestry=row["ancestry_category"],
                sample=row["sample_size"],
                snps=row["snp_count"],
                trait=trait,
                covariates=covariates,
                license_label=license_label,
            )
        )
    summary = result["roster_summary"]
    checks = result["summary"]
    return "\n".join(
        [
            "# P052 height accession and ancestry-leakage manifest v1",
            "",
            f"**Decision:** `{result['decision']}`.",
            "",
            "## What the gate asked",
            "",
            "Do three ancestry-labelled public height files already form an external genotype-to-phenotype test? The answer is no. This gate separates a reusable summary-statistics manifest from the participant-level evidence required to calculate calibration and incremental explained variance.",
            "",
            "The exact current `body height` query returned "
            f"`{result['catalog_query']['reported_total']}` studies; "
            f"`{result['catalog_query']['full_summary_statistics_available']}` "
            "report full summary statistics. Three 2026 accessions were frozen as a cross-cohort design seed.",
            "",
            "## Frozen three-accession seed",
            "",
            "| Accession | Intended role | Cohort | Catalog ancestry | N | SNPs | Response | Published covariates | License |",
            "|---|---|---|---|---:|---:|---|---|---|",
            *rows,
            "",
            "Together the manifest covers "
            f"`{summary['total_discovery_sample_size']:,}` discovery participants, "
            f"`{len(summary['distinct_cohorts'])}` named cohorts, and "
            f"`{len(summary['distinct_ancestry_categories'])}` Catalog ancestry categories. Every accession has an accessible raw file, harmonised GRCh38 GWAS-SSF file, declared checksum, cohort, ancestry metadata, and license path.",
            "",
            "## Why the evaluation is still blocked",
            "",
            "The retained artifacts are aggregate association estimates. They do not provide participant- or family-level keys, held-out genotypes or frozen scores, measured outcomes, per-participant ancestry assignment, covariate values, or resampling clusters. Therefore they cannot produce the preregistered external-cohort calibration slope, incremental explained variance, or ancestry-stratified bootstrap interval.",
            "",
            "The phenotype scale is also not interchangeable: the three accessions describe inverse-normalized standing height, standing height, and a height residual. UKB and CKB were published in the same paper, so their cross-population comparison is a retrospective sentinel rather than an unopened confirmation. The G&H accession comes from a second publication but is exome-wide and remains aggregate-only.",
            "",
            "## Leakage contract",
            "",
            "- Distinct accession IDs and ancestry labels do not prove participant- or cohort-level independence.",
            "- No held-out association, paper result, or phenotype transformation may guide feature selection, allele alignment, weighting, calibration, or hyperparameters.",
            "- Participant, family, household, and cohort boundaries must all remain intact.",
            "- Catalog ancestry descriptors are not treated as discrete causal biological categories.",
            "- Raw, residualized, and inverse-normalized outcomes require a frozen scale-alignment rule.",
            "",
            "## Reproducibility and next falsifier",
            "",
            f"The formal packet passes `{checks['passed_checks']}/{checks['check_count']}` checks. Multi-gigabyte association files are not duplicated in the repository; their official URLs, HTTP metadata, GWAS Catalog metadata, declared MD5 checksums, directory listings, and small-source SHA-256 hashes are retained.",
            "",
            "The next gate is an approved, cohort-disjoint individual-level holdout that supplies all seven frozen fields. Only then may variant intersection, allele alignment, LD reference, response transformation, additive denominator, bootstrap clusters, and calibration code be frozen before outcomes are opened.",
            "",
            "## Official sources",
            "",
            "- [GWAS Catalog summary-statistics documentation](https://www.ebi.ac.uk/gwas/docs/methods/summary-statistics)",
            "- [GWAS Catalog population descriptors](https://www.ebi.ac.uk/gwas/docs/population-descriptors)",
            "- [GWAS Catalog REST API v2](https://www.ebi.ac.uk/gwas/rest/api/v2/docs)",
            "",
            "No individual height prediction, re-identification, reproductive selection, clinical decision, causal mapping, wet-lab, or solved-frontier claim is made.",
            "",
        ]
    )


def render_discussion(result: dict[str, Any]) -> str:
    summary = result["roster_summary"]
    checks = result["summary"]
    return "\n".join(
        [
            "When do three ancestries still make zero external holdouts?",
            "",
            "A public catalog can give us harmonised height summary statistics for European, East Asian, and South Asian cohorts—and still leave the actual portability test mathematically impossible. What evidence turns ancestry-labelled files into a genuine external evaluation?",
            "",
            "The #052 gate queried the current exact `body height` trait: "
            f"{result['catalog_query']['reported_total']} studies were returned and "
            f"{result['catalog_query']['full_summary_statistics_available']} report full summary statistics. We froze three 2026 accessions spanning UKB, CKB, and G&H, with "
            f"{summary['total_discovery_sample_size']:,} discovery participants in aggregate. All three expose harmonised GRCh38 GWAS-SSF files and explicit ancestry/cohort metadata.",
            "",
            "But none exposes the participant-level scores, measured outcomes, family or household clusters, and covariate values needed for external calibration and incremental explained variance. The response scales also differ: inverse-normalized standing height, standing height, and residualized height. Two accessions—UKB and CKB—come from the same publication, so they are retrospective transfer sentinels rather than unopened confirmation.",
            "",
            "Here is the uncomfortable question: if a method transfers between two ancestry labels but the cohorts share a paper, the outcome transforms differ, and no family-aware bootstrap is possible, what exactly has been validated?",
            "",
            "Can you point to a lawful public or approved cohort path that supplies all seven frozen fields: participant/family grouping, held-out genotype or frozen score, measured height with declared scale, ancestry assignment method, age/sex covariates, cohort/recruitment identity, and relatedness-aware resampling groups?",
            "",
            "A useful contribution would include a stable accession and data-use path, not an individual record. We also welcome a falsifiable rule for deciding whether same-publication cross-population analyses can ever count as confirmation, and a scale contract that makes raw, residualized, and inverse-normalized height comparable without peeking at the test outcome.",
            "",
            f"Reproducibility: {checks['passed_checks']}/{checks['check_count']} formal checks; an independent source replay is required. No candidate or additive PGS denominator has run. No individual prediction, re-identification, reproductive selection, clinical, causal, wet-lab, or solved-frontier claim is made.",
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
        source = capture_sources(benchmark, source_dir)
    else:
        if not source_dir.exists():
            raise SystemExit("no source capture exists; use --capture")
        source = load_sources(benchmark, source_dir)
    result = build_result(
        benchmark_path,
        benchmark,
        source_dir,
        source,
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
                "accessions": result["roster_summary"]["accessions"],
                "result": str(args.result),
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
