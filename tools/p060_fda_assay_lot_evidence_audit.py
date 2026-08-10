#!/usr/bin/env python3
"""Independently audit the P060 FDA assay-and-lot evidence packet."""

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
DEFAULT_BENCHMARK = ROOT / "benchmarks/P060_fda_assay_lot_evidence_matrix_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P060_fda_assay_lot_source_v1"
DEFAULT_RESULT = ROOT / "results/P060_fda_assay_lot_evidence_matrix_v1.json"
DEFAULT_AUDIT = ROOT / "results/P060_fda_assay_lot_evidence_audit_v1.json"
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


def load_text(source_dir: Path, name: str) -> str:
    return gzip.decompress((source_dir / f"{name}.txt.gz").read_bytes()).decode(
        "utf-8", errors="replace"
    )


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def build_audit(
    benchmark_path: Path, source_dir: Path, result_path: Path
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    capture = read_json(source_dir / CAPTURE_MANIFEST)
    result = read_json(result_path)
    sources = {name: load_text(source_dir, name) for name in benchmark["sources"]}
    by_name = {entry["name"]: entry for entry in capture["sources"]}
    source_rows: list[dict[str, Any]] = []
    source_valid = len(by_name) == len(benchmark["sources"]) == 9
    for name, spec in benchmark["sources"].items():
        path = source_dir / f"{name}.txt.gz"
        payload = gzip.decompress(path.read_bytes())
        text = payload.decode("utf-8", errors="replace")
        entry = by_name.get(name, {})
        origin_http = spec["official_url"].replace("https://", "http://", 1)
        origin_marker = (
            f"URL Source: {origin_http}" in text
            or f"URL Source: {spec['official_url']}" in text
        )
        valid = (
            entry.get("official_url") == spec["official_url"]
            and entry.get("transport_url") == spec["transport_url"]
            and entry.get("kind") == spec["kind"]
            and entry.get("gzip_sha256") == sha256_path(path)
            and entry.get("normalized_sha256") == sha256_bytes(payload)
            and bool(
                re.fullmatch(r"[0-9a-f]{64}", entry.get("relay_raw_sha256", ""))
            )
            and text.startswith("Title:")
            and origin_marker
        )
        source_valid = source_valid and valid
        source_rows.append(
            {
                "name": name,
                "relay_raw_sha256": entry.get("relay_raw_sha256"),
                "normalized_sha256": sha256_bytes(payload),
                "gzip_sha256": sha256_path(path),
                "official_origin_marker": origin_marker,
                "valid": valid,
            }
        )

    final_page = sources["final_2024_page"]
    final_pdf = sources["final_2024_pdf_text"]
    ngs_page = sources["ngs_2026_page"]
    ngs_pdf = sources["ngs_2026_pdf_text"]
    prior_page = sources["prior_2026_page"]
    prior_pdf = sources["prior_2026_pdf_text"]
    matrix = benchmark["evidence_matrix"]
    decision = benchmark["readiness_decision"]
    guide_counts = Counter(key for row in matrix for key in row["guidance"])
    control_counts = Counter(value for row in matrix for value in row["controls"])
    independent = {
        "source_snapshots": len(sources),
        "guidance_statuses": {
            "G01": "final",
            "G02": "draft_not_for_implementation",
            "G03": "draft_not_for_implementation",
        },
        "evidence_rows": len(matrix),
        "evidence_ids": [row["id"] for row in matrix],
        "guidance_coverage": dict(sorted(guide_counts.items())),
        "control_coverage": dict(sorted(control_counts.items())),
        "arms": len(benchmark["control_and_split_contract"]["arms"]),
        "lots": benchmark["control_and_split_contract"]["independent_manufacturing_lots"],
        "labs": benchmark["control_and_split_contract"]["blinded_assay_laboratories"],
        "withheld_operational_details": len(
            benchmark["frozen_product_class"]["explicitly_withheld"]
        ),
        "wet_lab_executed": False,
    }

    checks = [
        check(
            "audit_scope",
            benchmark["scope"]["included_catalog_problem_ids"] == [60]
            and result["scope"]["included_catalog_problem_ids"] == [60],
            "Independent audit is restricted to catalog problem #060.",
        ),
        check(
            "benchmark_hash",
            sha256_path(benchmark_path)
            == capture["benchmark_sha256"]
            == result["source"]["benchmark_sha256"],
            sha256_path(benchmark_path),
        ),
        check(
            "source_hashes_and_origins",
            source_valid,
            f"{sum(row['valid'] for row in source_rows)}/9 sources independently verified.",
        ),
        check(
            "document_statuses",
            contains(final_page, "January 2024", "Final", "FDA-2021-D-0398")
            and contains(
                ngs_page,
                "April 2026",
                "Draft",
                "Not for implementation",
                "FDA-2026-D-1255",
            )
            and contains(
                prior_page,
                "June 2026",
                "Draft",
                "Not for implementation",
                "FDA-2026-D-1257",
            ),
            "One final and two draft documents independently classified.",
        ),
        check(
            "final_lifecycle_scope",
            contains(
                final_pdf,
                "human somatic cells",
                "product design",
                "product manufacturing and testing",
                "nonclinical safety assessment",
                "clinical trial design",
            ),
            "G01 lifecycle scope independently recovered.",
        ),
        check(
            "final_release_potency",
            contains(
                final_pdf,
                "Release testing of ex vivo-modified human GE DPs",
                "on-target editing efficiency",
                "off-target editing frequency",
                "residual GE components",
                "potency assays",
                "corrected cellular function",
            ),
            "Release and downstream potency anchors independently recovered.",
        ),
        check(
            "final_safety_guardrails",
            contains(
                final_pdf,
                "Multiple methods",
                "genome-wide analysis",
                "multiple donors",
                "chromosomal abnormalities",
                "clonal expansion",
                "viability and function",
                "immunogenicity",
            ),
            "Off-target, chromosomal, cellular, and immune guardrails recovered.",
        ),
        check(
            "final_followup",
            contains(final_pdf, "conduct LTFU for up to 15 years", "including funding"),
            "Long-term follow-up boundary independently recovered.",
        ),
        check(
            "ngs_reproducibility_fields",
            contains(
                ngs_pdf,
                "amount of nucleic acid material extracted",
                "library preparation",
                "command line interface",
                "Reference sequence(s) and database(s)",
                "sequencing depth acceptance criteria",
                "alignment metric acceptance criteria",
                "CSV",
            ),
            "NGS input, pipeline, criterion, and output fields recovered.",
        ),
        check(
            "ngs_reads_and_samples",
            contains(
                ngs_pdf,
                "≤50-bp",
                "long-read sequencing",
                "multiple biological replicates",
                "identical to the cell type being edited",
                "on-target editing rates that are comparable",
            ),
            "Read-strategy and biological-sample rules recovered.",
        ),
        check(
            "ngs_nomination_confirmation",
            contains(
                ngs_pdf,
                "off-target edit site nomination",
                "Confirmatory testing methods",
                "stringent filtering criteria should be avoided",
                "predetermined sequencing depth and quality",
                "unedited control and edited sample pairs",
            ),
            "Nomination/confirmation split independently recovered.",
        ),
        check(
            "ngs_variation_and_integrity",
            contains(
                ngs_pdf,
                "human genetic variation databases",
                "Population stratification",
                "specific genetic ancestry",
                "chromosomal translocation",
                "on-target and off-target edit sites",
            ),
            "Variation and translocation obligations recovered.",
        ),
        check(
            "ngs_reporting",
            contains(
                ngs_pdf,
                "read counts and/or editing frequencies",
                "Genomic coordinate information",
                "intergenic, exonic, or intronic",
                "summary of the risk assessment",
            ),
            "Site-level report schema independently recovered.",
        ),
        check(
            "prior_knowledge_definitions",
            contains(
                prior_pdf,
                "Public knowledge",
                "Platform knowledge",
                "similar products and processes",
                "Prior knowledge",
            ),
            "Public/platform knowledge definitions recovered.",
        ),
        check(
            "prior_knowledge_applicability",
            contains(
                prior_pdf,
                "justification for the applicability",
                "sufficiently granular",
                "Supply bridging or confirmatory data as appropriate",
            ),
            "Applicability and bridging boundary independently recovered.",
        ),
        check(
            "prior_product_specificity",
            contains(
                prior_pdf,
                "identity and potency",
                "product specific",
                "not intended to replace long-term, real-time product stability data",
                "each relevant quality attribute",
                "product-specific basis",
                "sequence-specific nature of genome editing",
            ),
            "Product-specific result/stability/comparability boundary recovered.",
        ),
        check(
            "matrix_shape_and_coverage",
            len(matrix) == 15
            and independent["evidence_ids"]
            == [f"E{index:02d}" for index in range(1, 16)]
            and set(guide_counts) == {"G01", "G02", "G03"}
            and all(row["threshold_state"].endswith("before_results") or row["id"] in {"E06", "E15"} for row in matrix),
            f"{len(matrix)} ordered evidence rows independently reconstructed.",
        ),
        check(
            "arms_lots_labs",
            independent["arms"] == 4
            and independent["lots"] == 3
            and independent["labs"] == 2
            and "not an FDA universal minimum"
            in benchmark["control_and_split_contract"]["lot_count_boundary"]
            and "not an FDA universal minimum"
            in benchmark["control_and_split_contract"]["lab_count_boundary"],
            "Four arms, three lots, two labs, and internal-floor boundary recovered.",
        ),
        check(
            "fail_closed_and_nonoperational",
            independent["withheld_operational_details"] == 8
            and benchmark["frozen_product_class"]["disclosed_operational_details"] is False
            and benchmark["acceptance_and_falsification"]["universal_fda_numeric_threshold_claimed"] is False
            and "one failed required evidence row"
            in benchmark["control_and_split_contract"]["failure_aggregation"],
            "No operational edit or universal FDA threshold; one-row failure rejects.",
        ),
        check(
            "result_agreement",
            result["formal_checks"]["all_passed"] is True
            and result["observed"]["matrix"]["rows"] == independent["evidence_rows"]
            and result["observed"]["matrix"]["guidance_coverage"]
            == independent["guidance_coverage"]
            and result["observed"]["protocol"]["arms"] == independent["arms"]
            and result["observed"]["protocol"]["independent_manufacturing_lots"]
            == independent["lots"]
            and result["observed"]["protocol"]["blinded_assay_laboratories"]
            == independent["labs"],
            "Independent matrix and protocol counts agree with primary result.",
        ),
        check(
            "execution_and_decision",
            result["readiness_decision"]["ready_label"] == decision["ready_label"]
            and all(
                decision[key] is False
                for key in [
                    "product_specific_assays_frozen",
                    "numeric_thresholds_frozen",
                    "manufacturing_lot_data_available",
                    "blinded_lab_confirmation_available",
                    "wet_lab_experiment_executed",
                    "safety_claim_ready",
                    "scalability_claim_ready",
                    "fda_compliance_claim_ready",
                ]
            ),
            decision["ready_label"],
        ),
    ]
    passed = sum(item["passed"] for item in checks)
    return {
        "schema_version": "p060_fda_assay_lot_evidence_independent_audit_v1",
        "as_of_date": benchmark["as_of_date"],
        "scope": {"included_catalog_problem_ids": [60]},
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
        f"P060 independent audit: {audit['audit_checks']['passed']}/{audit['audit_checks']['total']} "
        f"decision={audit['decision']}"
    )
    return 0 if audit["audit_checks"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
