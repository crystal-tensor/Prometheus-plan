#!/usr/bin/env python3
"""Independent replay audit for the P052 height-accession manifest."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import re
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P052_height_accession_manifest_v1.json"
DEFAULT_RESULT = ROOT / "results/P052_height_accession_manifest_v1.json"
DEFAULT_AUDIT = ROOT / "results/P052_height_accession_manifest_audit_v1.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_gzip_json(path: Path) -> dict[str, Any]:
    return json.loads(gzip.decompress(path.read_bytes()))


def read_gzip_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(gzip.decompress(path.read_bytes()))


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def independent_links(path: Path) -> list[str]:
    text = gzip.decompress(path.read_bytes()).decode(
        "utf-8", errors="replace"
    )
    return sorted(set(re.findall(r'href="([^"]+)"', text)))


def one_sample(metadata: dict[str, Any]) -> dict[str, Any]:
    samples = metadata.get("samples") or []
    return samples[0] if len(samples) == 1 else {}


def independent_response_label(
    raw_metadata: dict[str, Any], harmonised_metadata: dict[str, Any]
) -> str | None:
    notes = str(raw_metadata.get("author_notes") or "")
    match = re.search(r"Height\.residual", notes, flags=re.I)
    if match:
        return "Height.residual"
    descriptions = harmonised_metadata.get("trait_description") or []
    return str(descriptions[0]) if len(descriptions) == 1 else None


def source_hashes(source_dir: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256_path(path),
        }
        for path in sorted(source_dir.iterdir())
        if path.is_file()
    ]


def build_audit(
    benchmark_path: Path, result_path: Path
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    result = read_json(result_path)
    source_dir = ROOT / result["source"]["source_directory"]
    query = read_gzip_json(source_dir / "catalog_body_height.json.gz")
    query_rows = query.get("_embedded", {}).get("studies", [])
    query_by_id = {
        str(row["accession_id"]): row for row in query_rows
    }
    frozen_ids = [
        row["accession"] for row in benchmark["frozen_accession_seed"]
    ]
    headers = read_gzip_json(source_dir / "artifact_headers.json.gz")

    reconstructed = []
    for seed in benchmark["frozen_accession_seed"]:
        accession = seed["accession"]
        study = read_gzip_json(
            source_dir / f"{accession}_study.json.gz"
        )
        raw_metadata = read_gzip_yaml(
            source_dir / f"{accession}_raw_meta.yaml.gz"
        )
        metadata = read_gzip_yaml(
            source_dir / f"{accession}_harmonised_meta.yaml.gz"
        )
        sample = one_sample(metadata)
        categories = sample.get("sample_ancestry_category") or []
        cohorts = study.get("cohort") or []
        root_links = independent_links(
            source_dir / f"{accession}_root_index.html.gz"
        )
        harmonised_links = independent_links(
            source_dir / f"{accession}_harmonised_index.html.gz"
        )
        disease_trait = str(study.get("disease_trait") or "")
        interaction = (
            study.get("gxe") is True
            or study.get("gxg") is True
            or bool(
                re.search(
                    r"\binteraction\b|\s[x×]\s", disease_trait, re.I
                )
            )
        )
        reconstructed.append(
            {
                "accession": accession,
                "role": seed["intended_role"],
                "cohort": cohorts[0] if len(cohorts) == 1 else None,
                "ancestry_category": (
                    categories[0] if len(categories) == 1 else None
                ),
                "sample_size": sample.get("sample_size"),
                "snp_count": study.get("snp_count"),
                "response_label": independent_response_label(
                    raw_metadata, metadata
                ),
                "publication": str(study.get("pubmed_id")),
                "metadata_ready": all(
                    [
                        accession in query_by_id,
                        study.get("full_summary_stats_available") is True,
                        int(study.get("snp_count") or 0) >= 1_000_000,
                        not interaction,
                        len(cohorts) == 1,
                        len(categories) == 1,
                        metadata.get("is_harmonised") is True,
                        metadata.get("is_sorted") is True,
                        metadata.get("genome_assembly") == "GRCh38",
                        metadata.get("file_type") == "GWAS-SSF v1.0",
                        sample.get("case_control_study") is False,
                        bool(study.get("terms_of_license")),
                        benchmark["trait"]["ontology_id"]
                        in (metadata.get("ontology_mapping") or []),
                        any(
                            link.endswith("-meta.yaml")
                            for link in root_links
                        ),
                        any(
                            link.endswith(".h.tsv.gz")
                            for link in harmonised_links
                        ),
                        bool(
                            re.fullmatch(
                                r"[0-9a-f]{32}",
                                str(
                                    metadata.get(
                                        "data_file_md5sum", ""
                                    )
                                ),
                            )
                        ),
                        int(
                            headers[accession]["raw"].get(
                                "content_length"
                            )
                            or 0
                        )
                        > 0,
                        int(
                            headers[accession]["harmonised"].get(
                                "content_length"
                            )
                            or 0
                        )
                        > 0,
                    ]
                ),
            }
        )

    recorded = [
        {
            "accession": row["accession"],
            "role": row["intended_role"],
            "cohort": row["cohort"],
            "ancestry_category": row["ancestry_category"],
            "sample_size": row["sample_size"],
            "snp_count": row["snp_count"],
            "response_label": row["response_label"],
            "publication": row["pubmed_id"],
            "metadata_ready": row["passes_accession_manifest"],
        }
        for row in result["roster"]
    ]
    full_count = sum(
        bool(row.get("full_summary_stats_available")) for row in query_rows
    )
    total_sample = sum(
        int(row["sample_size"] or 0) for row in reconstructed
    )
    ancestry = sorted(
        {str(row["ancestry_category"]) for row in reconstructed}
    )
    cohorts = sorted({str(row["cohort"]) for row in reconstructed})
    publications = sorted(
        {str(row["publication"]) for row in reconstructed}
    )
    current_hashes = source_hashes(source_dir)
    checks = [
        check(
            "scope_only_p052",
            benchmark["scope"]["included_catalog_problem_ids"] == [52],
            "Only catalog problem #052 is included.",
        ),
        check(
            "complete_query_replayed",
            len(query_rows) == int(query["page"]["totalElements"])
            == result["catalog_query"]["reported_total"],
            f"{len(query_rows)} rows.",
        ),
        check(
            "full_summary_count_replayed",
            full_count
            == result["catalog_query"][
                "full_summary_statistics_available"
            ],
            f"{full_count} rows.",
        ),
        check(
            "frozen_ids_exact",
            [row["accession"] for row in reconstructed] == frozen_ids,
            ", ".join(frozen_ids),
        ),
        check(
            "independent_roster_exact",
            reconstructed == recorded,
            f"{len(reconstructed)} rows.",
        ),
        check(
            "accession_metadata_ready",
            all(row["metadata_ready"] for row in reconstructed),
            f"{sum(row['metadata_ready'] for row in reconstructed)}/3 pass.",
        ),
        check(
            "three_cohorts_and_ancestries",
            len(cohorts) == len(ancestry) == 3,
            f"cohorts={cohorts}; ancestry={ancestry}",
        ),
        check(
            "sample_total_replayed",
            total_sample
            == result["roster_summary"][
                "total_discovery_sample_size"
            ],
            str(total_sample),
        ),
        check(
            "publication_grouping_replayed",
            publications == ["41861830", "41896352"]
            and result["roster_summary"]["same_publication_pair"]
            == ["GCST90727382", "GCST90728584"],
            ", ".join(publications),
        ),
        check(
            "all_holdout_fields_absent",
            not any(
                value[
                    "available_for_participant_level_external_evaluation"
                ]
                for value in result[
                    "required_holdout_field_matrix"
                ].values()
            ),
            "0 participant-level fields marked available.",
        ),
        check(
            "blocked_without_execution",
            result["decision"]
            == "blocked_no_individual_level_external_holdout"
            and result["summary"]["candidate_model_executed"] is False
            and result["summary"][
                "polygenic_score_denominator_executed"
            ]
            is False,
            result["decision"],
        ),
        check(
            "retained_source_hashes_exact",
            current_hashes == result["source"]["retained_files"],
            f"{len(current_hashes)} files.",
        ),
    ]
    if not all(item["passed"] for item in checks):
        failed = [item["name"] for item in checks if not item["passed"]]
        raise RuntimeError(f"independent audit failed: {failed}")
    return {
        "schema_version": "p052_height_accession_manifest_audit_v1",
        "status": "pass",
        "decision_replayed": result["decision"],
        "reconstructed_roster": reconstructed,
        "reconstructed_query": {
            "study_count": len(query_rows),
            "full_summary_statistics_count": full_count,
        },
        "reconstructed_sample_total": total_sample,
        "checks": checks,
        "summary": {
            "check_count": len(checks),
            "passed_checks": sum(item["passed"] for item in checks),
            "failed_checks": sum(not item["passed"] for item in checks),
            "maximum_numeric_difference": 0,
        },
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "result": str(result_path.relative_to(ROOT)),
            "result_sha256": sha256_path(result_path),
            "tool": "tools/p052_height_accession_audit.py",
            "python": platform.python_version(),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--check-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit = build_audit(args.benchmark.resolve(), args.result.resolve())
    payload = pretty_json(audit)
    if args.check_only:
        if payload != args.audit.read_text(encoding="utf-8"):
            raise SystemExit("check-only mismatch: rebuilt audit differs")
        print(
            pretty_json(
                {
                    "status": "pass",
                    "audit_sha256": sha256_path(args.audit),
                }
            ),
            end="",
        )
        return
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(payload, encoding="utf-8")
    print(
        pretty_json(
            {
                "status": "pass",
                "checks": audit["summary"]["check_count"],
                "audit": str(args.audit),
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
