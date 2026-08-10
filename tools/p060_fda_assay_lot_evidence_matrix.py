#!/usr/bin/env python3
"""Capture and audit the public FDA guidance matrix for catalog problem #060."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P060_fda_assay_lot_evidence_matrix_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P060_fda_assay_lot_source_v1"
DEFAULT_RESULT = ROOT / "results/P060_fda_assay_lot_evidence_matrix_v1.json"
DEFAULT_REPORT = ROOT / "research/P060_fda_assay_lot_evidence_matrix_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/P060_fda_assay_lot_discussion_v1.md"
CAPTURE_MANIFEST = "capture_manifest.json"
USER_AGENT = "Codex-P060-FDA-public-guidance-audit/1.0"


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


def fetch_bytes(url: str, attempts: int = 5, timeout: int = 180) -> tuple[bytes, str]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT, "Accept": "text/plain,*/*;q=0.8"},
                timeout=timeout,
                allow_redirects=True,
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


def normalize_text(payload: bytes) -> bytes:
    text = payload.decode("utf-8-sig", errors="strict")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    return (text.rstrip("\n") + "\n").encode("utf-8")


def write_gzip(path: Path, payload: bytes) -> None:
    path.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))


def read_gzip(path: Path) -> bytes:
    return gzip.decompress(path.read_bytes())


def capture_sources(
    benchmark_path: Path, benchmark: dict[str, Any], source_dir: Path
) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for name, spec in benchmark["sources"].items():
        raw, final_url = fetch_bytes(spec["transport_url"])
        normalized = normalize_text(raw)
        path = source_dir / f"{name}.txt.gz"
        write_gzip(path, normalized)
        entries.append(
            {
                "name": name,
                "kind": spec["kind"],
                "official_url": spec["official_url"],
                "transport_url": spec["transport_url"],
                "final_transport_url": final_url,
                "path": str(path.relative_to(ROOT)),
                "relay_raw_bytes": len(raw),
                "relay_raw_sha256": sha256_bytes(raw),
                "normalized_bytes": len(normalized),
                "normalized_sha256": sha256_bytes(normalized),
                "gzip_bytes": path.stat().st_size,
                "gzip_sha256": sha256_path(path),
            }
        )
    manifest = {
        "schema_version": "p060_fda_guidance_text_capture_manifest_v1",
        "as_of_date": benchmark["as_of_date"],
        "benchmark": str(benchmark_path.relative_to(ROOT)),
        "benchmark_sha256": sha256_path(benchmark_path),
        "transport_boundary": (
            "Official FDA origins were retrieved through the r.jina.ai text relay because "
            "the shell transport was redirected to FDA abuse detection. These are normalized "
            "text snapshots, not raw FDA PDF-byte claims; official origin markers and relay "
            "hashes are retained."
        ),
        "normalization": "UTF-8 text, normalized line endings/trailing spaces, deterministic gzip mtime=0.",
        "sources": entries,
    }
    (source_dir / CAPTURE_MANIFEST).write_text(pretty_json(manifest), encoding="utf-8")


def load_sources(
    benchmark: dict[str, Any], source_dir: Path
) -> tuple[dict[str, str], dict[str, Any]]:
    capture = read_json(source_dir / CAPTURE_MANIFEST)
    sources = {
        name: read_gzip(source_dir / f"{name}.txt.gz").decode(
            "utf-8", errors="replace"
        )
        for name in benchmark["sources"]
    }
    return sources, capture


def source_inventory_valid(
    benchmark: dict[str, Any], source_dir: Path, capture: dict[str, Any]
) -> tuple[bool, list[dict[str, Any]]]:
    by_name = {entry["name"]: entry for entry in capture["sources"]}
    valid = len(by_name) == len(benchmark["sources"])
    rows: list[dict[str, Any]] = []
    for name, spec in benchmark["sources"].items():
        path = source_dir / f"{name}.txt.gz"
        entry = by_name.get(name, {})
        gzip_hash = sha256_path(path) if path.exists() else None
        normalized_hash = sha256_bytes(read_gzip(path)) if path.exists() else None
        relay_hash = entry.get("relay_raw_sha256", "")
        text = read_gzip(path).decode("utf-8", errors="replace") if path.exists() else ""
        origin_http = spec["official_url"].replace("https://", "http://", 1)
        origin_marker = (
            f"URL Source: {origin_http}" in text
            or f"URL Source: {spec['official_url']}" in text
        )
        row_valid = (
            entry.get("kind") == spec["kind"]
            and entry.get("official_url") == spec["official_url"]
            and entry.get("transport_url") == spec["transport_url"]
            and entry.get("path") == str(path.relative_to(ROOT))
            and entry.get("gzip_sha256") == gzip_hash
            and entry.get("normalized_sha256") == normalized_hash
            and bool(re.fullmatch(r"[0-9a-f]{64}", relay_hash))
            and text.startswith("Title:")
            and origin_marker
        )
        valid = valid and row_valid
        rows.append(
            {
                "name": name,
                "official_url": spec["official_url"],
                "relay_raw_sha256": relay_hash,
                "normalized_sha256": normalized_hash,
                "gzip_sha256": gzip_hash,
                "official_origin_marker": origin_marker,
                "valid": row_valid,
            }
        )
    return valid, rows


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def build_result(
    benchmark_path: Path, benchmark: dict[str, Any], source_dir: Path
) -> dict[str, Any]:
    sources, capture = load_sources(benchmark, source_dir)
    source_valid, source_rows = source_inventory_valid(benchmark, source_dir, capture)
    final_page = sources["final_2024_page"]
    final_pdf = sources["final_2024_pdf_text"]
    ngs_page = sources["ngs_2026_page"]
    ngs_pdf = sources["ngs_2026_pdf_text"]
    prior_page = sources["prior_2026_page"]
    prior_pdf = sources["prior_2026_pdf_text"]
    index = sources["guidance_index"]
    matrix = benchmark["evidence_matrix"]
    guidance_ids = {row["id"] for row in benchmark["guidance_status_contract"]}
    guidance_coverage = Counter(
        guidance for row in matrix for guidance in row["guidance"]
    )
    control_coverage = Counter(
        control for row in matrix for control in row["controls"]
    )
    threshold_states = Counter(row["threshold_state"] for row in matrix)
    decision = benchmark["readiness_decision"]

    observed = {
        "guidance_status": {
            "G01": {
                "issue_date": "2024-01",
                "status": "final",
                "docket": "FDA-2021-D-0398",
            },
            "G02": {
                "issue_date": "2026-04",
                "status": "draft_not_for_implementation",
                "docket": "FDA-2026-D-1255",
            },
            "G03": {
                "issue_date": "2026-06",
                "status": "draft_not_for_implementation",
                "docket": "FDA-2026-D-1257",
            },
        },
        "matrix": {
            "rows": len(matrix),
            "ids": [row["id"] for row in matrix],
            "domains": [row["domain"] for row in matrix],
            "guidance_coverage": dict(sorted(guidance_coverage.items())),
            "control_coverage": dict(sorted(control_coverage.items())),
            "unique_threshold_states": len(threshold_states),
        },
        "protocol": {
            "arms": len(benchmark["control_and_split_contract"]["arms"]),
            "independent_manufacturing_lots": benchmark["control_and_split_contract"]["independent_manufacturing_lots"],
            "blinded_assay_laboratories": benchmark["control_and_split_contract"]["blinded_assay_laboratories"],
            "operational_details_disclosed": benchmark["frozen_product_class"]["disclosed_operational_details"],
        },
        "execution": {
            "product_specific_assays_frozen": False,
            "numeric_thresholds_frozen": False,
            "manufacturing_lot_data_available": False,
            "blinded_lab_confirmation_available": False,
            "wet_lab_experiment_executed": False,
        },
    }

    checks = [
        check(
            "schema_and_scope",
            benchmark["scope"]["included_catalog_problem_ids"] == [60]
            and benchmark["scope"]["excluded_catalog_problem_ids"]
            == [49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59],
            "Packet is restricted to catalog problem #060.",
        ),
        check(
            "benchmark_hash",
            capture["benchmark_sha256"] == sha256_path(benchmark_path),
            sha256_path(benchmark_path),
        ),
        check(
            "source_inventory",
            source_valid,
            f"{sum(row['valid'] for row in source_rows)}/{len(source_rows)} official-origin relay snapshots hash-verified.",
        ),
        check(
            "guidance_index",
            contains_all(
                index,
                [
                    "Human Gene Therapy Products Incorporating Human Genome Editing",
                    "1/2024",
                    "Safety Assessment of Genome Editing",
                    "4/2026",
                    "Leveraging Prior Knowledge",
                    "6/2026",
                ],
            ),
            "All three core documents and issue months recovered from the FDA index.",
        ),
        check(
            "final_status",
            contains_all(
                final_page,
                [
                    "Guidance for Industry January 2024",
                    "Final",
                    "FDA-2021-D-0398",
                ],
            ),
            "G01 status/date/docket recovered.",
        ),
        check(
            "ngs_draft_status",
            contains_all(
                ngs_page,
                [
                    "April 2026",
                    "Draft",
                    "Not for implementation",
                    "FDA-2026-D-1255",
                ],
            ),
            "G02 draft boundary recovered.",
        ),
        check(
            "prior_draft_status",
            contains_all(
                prior_page,
                [
                    "June 2026",
                    "Draft",
                    "Not for implementation",
                    "FDA-2026-D-1257",
                ],
            ),
            "G03 draft boundary recovered.",
        ),
        check(
            "final_scope",
            contains_all(
                final_pdf,
                [
                    "human somatic cells",
                    "product design",
                    "product manufacturing and testing",
                    "nonclinical safety assessment",
                    "clinical trial design",
                ],
            ),
            "Somatic-cell and development-lifecycle scope recovered.",
        ),
        check(
            "final_release_testing",
            contains_all(
                final_pdf,
                [
                    "Release testing of ex vivo-modified human GE DPs",
                    "on-target editing efficiency",
                    "off-target editing frequency",
                    "intrachromosomal and interchromosomal rearrangements",
                    "residual GE components",
                    "Acceptance criteria or limits should be provided and justified",
                ],
            ),
            "Ex vivo release-testing obligations recovered.",
        ),
        check(
            "final_potency",
            contains_all(
                final_pdf,
                [
                    "potency assays",
                    "intended downstream biological modification",
                    "corrected cellular function",
                    "stability studies",
                ],
            ),
            "Genetic edit plus downstream functional potency recovered.",
        ),
        check(
            "final_off_target_methods",
            contains_all(
                final_pdf,
                [
                    "Multiple methods",
                    "in silico, biochemical, cellular-based assays",
                    "genome-wide analysis",
                    "multiple donors",
                    "adequate sensitivity to detect low frequency events",
                ],
            ),
            "Multi-method nomination and sensitive donor-level verification recovered.",
        ),
        check(
            "final_genomic_integrity",
            contains_all(
                final_pdf,
                [
                    "Assessment of genomic integrity",
                    "chromosomal abnormalities",
                    "insertions or deletions",
                    "clonal expansion",
                    "unregulated proliferation",
                ],
            ),
            "Chromosomal and clonal-risk evidence recovered.",
        ),
        check(
            "final_biological_guardrails",
            contains_all(
                final_pdf,
                [
                    "viability and function of the edited cells",
                    "Assessment of immunogenicity",
                ],
            ),
            "Viability/function and immunogenicity guardrails recovered.",
        ),
        check(
            "final_long_term_followup",
            contains_all(
                final_pdf,
                [
                    "conduct LTFU for up to 15 years",
                    "plan be provided for follow-up, including funding",
                ],
            ),
            "Up-to-15-year and continuity-plan recommendation recovered.",
        ),
        check(
            "ngs_purpose",
            contains_all(
                ngs_pdf,
                [
                    "Draft Guidance for Industry",
                    "off-target editing",
                    "loss of genome integrity",
                    "nonclinical studies",
                    "original IND application",
                ],
            ),
            "G02 nonclinical NGS purpose recovered.",
        ),
        check(
            "ngs_read_strategy",
            contains_all(
                ngs_pdf,
                [
                    "short stretch of DNA",
                    "≤50-bp",
                    "long-read sequencing",
                    "large insertions or large deletions",
                    "adequate amount of the input material",
                    "adequacy and the sensitivity of sequencing depth",
                ],
            ),
            "Short/long-read and sensitivity justification recovered.",
        ),
        check(
            "ngs_metadata",
            contains_all(
                ngs_pdf,
                [
                    "cell type",
                    "amount of nucleic acid material extracted",
                    "library preparation",
                    "command line interface",
                    "Reference sequence(s) and database(s)",
                    "sequencing quality acceptance criteria",
                    "sequencing depth acceptance criteria",
                    "alignment metric acceptance",
                    "criteria",
                    "CSV",
                ],
            ),
            "Reproducible NGS metadata and tabular-output obligations recovered.",
        ),
        check(
            "ngs_sample_replicates",
            contains_all(
                ngs_pdf,
                [
                    "multiple biological replicates",
                    "identical to the cell type being edited",
                    "on-target editing rates that are comparable",
                ],
            ),
            "Biological-replicate and product-relevant sample requirements recovered.",
        ),
        check(
            "ngs_nomination_confirmation",
            contains_all(
                ngs_pdf,
                [
                    "off-target edit site nomination",
                    "Confirmatory testing methods",
                    "while performing confirmatory testing at all the",
                    "nominated off-target edit sites is recommended",
                    "stringent filtering criteria",
                    "should be avoided",
                ],
            ),
            "Nomination/confirmation separation and anti-filtering boundary recovered.",
        ),
        check(
            "ngs_confirmation_sensitivity",
            contains_all(
                ngs_pdf,
                [
                    "predetermined sequencing depth",
                    "quality that enables evaluation",
                    "low frequency editing events",
                    "unedited control and edited sample pairs",
                ],
            ),
            "Predetermined sensitivity and paired-control confirmation recovered.",
        ),
        check(
            "ngs_human_variation",
            contains_all(
                ngs_pdf,
                [
                    "human genetic variation databases",
                    "healthy and/or patient populations",
                    "Population stratification",
                    "allele frequency",
                    "specific genetic ancestry",
                ],
            ),
            "Human-variation and ancestry-aware nomination recovered.",
        ),
        check(
            "ngs_translocation",
            contains_all(
                ngs_pdf,
                [
                    "chromosomal translocation",
                    "on-target and off-target edit sites",
                    "sensitive and quantitative NGS-based assessment",
                ],
            ),
            "On-target/off-target translocation assessment recovered.",
        ),
        check(
            "ngs_reporting",
            contains_all(
                ngs_pdf,
                [
                    "read counts and/or editing frequencies",
                    "Genomic coordinate information",
                    "intergenic, exonic, or intronic",
                    "summary",
                    "risk assessment performed using prior knowledge",
                ],
            ),
            "Annotated site-level reporting recovered.",
        ),
        check(
            "prior_definitions",
            contains_all(
                prior_pdf,
                [
                    "Public knowledge",
                    "generally accepted scientific knowledge",
                    "Platform knowledge",
                    "similar products and processes",
                    "Prior knowledge",
                ],
            ),
            "Public/platform/prior knowledge definitions recovered.",
        ),
        check(
            "prior_applicability",
            contains_all(
                prior_pdf,
                [
                    "justification for the applicability",
                    "sufficiently granular",
                    "Justify that the referenced data are applicable",
                    "Supply bridging or confirmatory data as appropriate",
                ],
            ),
            "Applicability, granularity, and bridging boundary recovered.",
        ),
        check(
            "prior_lot_release",
            contains_all(
                prior_pdf,
                [
                    "support",
                    "a lot release specification",
                    "similarity(s) of the GE",
                    "component or product structure",
                    "suitable",
                    "acceptance criteria for those quality attributes",
                    "identity and potency",
                    "product specific",
                ],
            ),
            "Lot reuse and product-specific identity/potency boundary recovered.",
        ),
        check(
            "prior_stability",
            contains_all(
                prior_pdf,
                [
                    "real time stability data",
                    "primary product lots",
                    "not intended to",
                    "replace long-term, real-time product stability data",
                ],
            ),
            "Platform knowledge cannot replace primary-lot long-term stability.",
        ),
        check(
            "prior_comparability",
            contains_all(
                prior_pdf,
                [
                    "impact of product differences on a comparability",
                    "determination should be assessed for each relevant quality",
                    "product-specific",
                    "basis for products",
                ],
            ),
            "Comparability remains quality-attribute and product specific.",
        ),
        check(
            "prior_bioinformatics",
            contains_all(
                prior_pdf,
                [
                    "Off-target analysis and genomic integrity assessment of all GE products",
                    "essential for assessing drug product safety",
                    "study design(s)",
                    "methods, analysis tools, and sequencing technologies",
                    "may be more broadly",
                    "appropriate across multiple types of GE products",
                    "product-specific due to the sequence-specific nature of genome editing",
                ],
            ),
            "Methods may transfer; product safety results do not transfer automatically.",
        ),
        check(
            "matrix_shape",
            len(matrix) == 15
            and [row["id"] for row in matrix]
            == [f"E{index:02d}" for index in range(1, 16)]
            and all(set(row["guidance"]).issubset(guidance_ids) for row in matrix),
            "15 ordered evidence rows with valid guidance anchors.",
        ),
        check(
            "matrix_required_domains",
            set(observed["matrix"]["domains"])
            == {
                "product and component identity",
                "manufacturing lot release",
                "functional potency",
                "on-target intended and unintended outcomes",
                "off-target nomination",
                "off-target confirmation",
                "human genetic variation",
                "chromosomal integrity",
                "residual editor and persistence",
                "viability and cell function",
                "immunogenicity",
                "oncogenicity and clonal behavior",
                "stability",
                "scale change and comparability",
                "long-term follow-up trigger",
            },
            "All required identity, activity, safety, lot, scale, and follow-up domains present.",
        ),
        check(
            "control_arms",
            benchmark["control_and_split_contract"]["arms"]
            == [
                "unedited cells",
                "mock delivery",
                "current standard editor and delivery system",
                "P060-EXV-DSB-01 candidate",
            ],
            "Four frozen arms recovered.",
        ),
        check(
            "lot_and_lab_split",
            observed["protocol"]["independent_manufacturing_lots"] == 3
            and observed["protocol"]["blinded_assay_laboratories"] == 2
            and "internal preregistered engineering floor"
            in benchmark["control_and_split_contract"]["lot_count_boundary"]
            and "internal confirmation floor"
            in benchmark["control_and_split_contract"]["lab_count_boundary"],
            "Three-lot/two-lab internal floors and non-FDA boundary frozen.",
        ),
        check(
            "matched_sensitivity",
            contains_all(
                benchmark["control_and_split_contract"]["matched_assessment"],
                [
                    "assay versions",
                    "input amounts",
                    "sequencing depth/quality criteria",
                    "bioinformatics versions",
                ],
            ),
            "Matched-sensitivity denominator frozen.",
        ),
        check(
            "no_operational_editing_details",
            benchmark["frozen_product_class"]["disclosed_operational_details"] is False
            and len(benchmark["frozen_product_class"]["explicitly_withheld"]) == 8,
            "No sequence, editor, target, dose, recipe, condition, or procedure disclosed.",
        ),
        check(
            "no_universal_fda_threshold",
            benchmark["acceptance_and_falsification"]["universal_fda_numeric_threshold_claimed"]
            is False
            and "before arm labels or outcome data are opened"
            in benchmark["acceptance_and_falsification"]["threshold_freeze_rule"],
            "Product/assay thresholds remain to be frozen prospectively.",
        ),
        check(
            "fail_closed_aggregation",
            "one failed required evidence row"
            in benchmark["control_and_split_contract"]["failure_aggregation"]
            and "all 15 evidence rows pass"
            in benchmark["acceptance_and_falsification"]["required_pass"],
            "No safety-row or lot failure may be averaged away.",
        ),
        check(
            "execution_boundary",
            all(
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
            "No assay outcome, lot, wet-lab execution, safety, scale, or compliance claim.",
        ),
        check(
            "decision",
            decision["ready_label"]
            == "fda_guidance_evidence_matrix_ready_protocol_activation_blocked_by_product_specific_assays_thresholds_lot_data_and_blinded_lab_execution",
            decision["ready_label"],
        ),
    ]
    passed = sum(item["passed"] for item in checks)
    return {
        "schema_version": "p060_fda_assay_lot_evidence_matrix_result_v1",
        "as_of_date": benchmark["as_of_date"],
        "scope": benchmark["scope"],
        "question": benchmark["question"],
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "capture_manifest": str((source_dir / CAPTURE_MANIFEST).relative_to(ROOT)),
            "capture_manifest_sha256": sha256_path(source_dir / CAPTURE_MANIFEST),
            "transport_boundary": capture["transport_boundary"],
            "snapshots": source_rows,
        },
        "observed": observed,
        "guidance_status_contract": benchmark["guidance_status_contract"],
        "frozen_product_class": benchmark["frozen_product_class"],
        "control_and_split_contract": benchmark["control_and_split_contract"],
        "evidence_matrix": matrix,
        "ngs_and_reporting_contract": benchmark["ngs_and_reporting_contract"],
        "prior_knowledge_boundary": benchmark["prior_knowledge_boundary"],
        "acceptance_and_falsification": benchmark["acceptance_and_falsification"],
        "readiness_decision": decision,
        "interpretation_boundaries": benchmark["interpretation_boundaries"],
        "formal_checks": {
            "passed": passed,
            "total": len(checks),
            "all_passed": passed == len(checks),
            "checks": checks,
        },
    }


def report_table(matrix: list[dict[str, Any]]) -> str:
    guidance_names = {"G01": "2024 final", "G02": "2026 NGS draft", "G03": "2026 prior-knowledge draft"}
    rows = ["| ID | Evidence domain | FDA anchor | What must be frozen before results |", "|---|---|---|---|"]
    for item in matrix:
        anchors = ", ".join(guidance_names[key] for key in item["guidance"])
        rows.append(
            f"| `{item['id']}` | {item['domain']} | {anchors} | `{item['threshold_state']}` |"
        )
    return "\n".join(rows)


def write_report(result: dict[str, Any], path: Path) -> None:
    checks = result["formal_checks"]
    matrix = result["evidence_matrix"]
    decision = result["readiness_decision"]["ready_label"]
    text = f"""# P060 FDA assay-and-lot evidence matrix v1

**Decision:** `{decision}`.

## Can a high on-target number still be a failed editing result?

Yes. The #060 gate now treats on-target correction as one row in a 15-row evidence matrix, not as a safety verdict. The matrix maps the January 2024 FDA final genome-editing guidance, the April 2026 NGS safety draft, and the June 2026 prior-knowledge draft into a protocol-only failure system.

The two 2026 documents are explicitly **draft, not for implementation**, and contain non-binding recommendations. This packet therefore does not convert draft wording into law, approval criteria, or a claim of FDA compliance.

## One abstract product class, no executable edit

The frozen label `P060-EXV-DSB-01` means only a conceptual ex vivo autologous human somatic-cell product using a single-locus nuclease-dependent double-strand-break editor with transient non-integrating delivery. The target, sequence, guide, editor identity, disease, dose, culture conditions, delivery recipe, and wet-lab procedure are intentionally withheld.

That abstract class is enough to trigger long-read assessment of larger unintended on-target changes, multi-method off-target nomination, independent confirmation, human-variation analysis, and chromosomal-translocation testing without publishing an operational editing protocol.

## Fifteen rows that cannot be averaged away

{report_table(matrix)}

Every row must have its assay, input, sensitivity, quality/depth criteria, analysis parameters, categorical or numeric threshold, non-inferiority margin, timepoint, and failure rule frozen before arm labels or outcomes are opened. FDA does not provide one universal number that proves a genome-editing product safe or scalable.

## Four arms, three lots, two blinded laboratories

The four arms are unedited cells, mock delivery, the current standard editor/delivery system, and the candidate. All are assessed at matched assay versions, inputs, sequencing sensitivity, bioinformatics versions, timepoints, and reporting rules.

The internal gate requires three independent manufacturing lots and two blinded confirmation laboratories. These are preregistered engineering floors, **not FDA universal minima**. A single failed safety row in any lot rejects promotion; a mean cannot hide the failure. Off-target nomination is locked before confirmation samples and labels are opened.

## Discovery is not confirmation

The 2024 final guidance recommends multiple off-target methods, including in-silico, biochemical, cellular, and genome-wide analysis, using relevant human cells and multiple donors where possible. The 2026 NGS draft separates nomination from confirmation, recommends multiple biological replicates, warns against stringent filtering, and calls for predetermined sequencing depth and quality capable of evaluating low-frequency events.

The frozen matrix retains the union of nominated sites. Every site must be confirmed, or a subset rule must be scientifically justified and frozen before nomination results. Edited/unedited pairs, read counts, edit frequencies, coordinates, functional context, reference databases, quality/depth/alignment criteria, tools, versions, and command-line records all remain part of the evidence.

## Prior knowledge can transfer a method, not a safety conclusion

The June 2026 draft distinguishes public knowledge from platform knowledge and allows scientifically justified reuse of methods, manufacturing experience, sequencing technology, pipeline structure, and some quality metrics. It also requires applicability justification, sufficiently granular sources, and bridging or confirmatory data as appropriate.

Identity and potency testing remain product-specific. Primary-product long-term real-time stability cannot be replaced by prior knowledge. Comparability must assess each relevant quality attribute, and sequence-specific off-target/genomic-integrity results cannot be borrowed merely because two products look related.

## What is ready—and what is not

The formal parser passes **{checks['passed']}/{checks['total']}** checks over **{len(result['source']['snapshots'])}** hash-bound official-origin text snapshots. The 15-row evidence vocabulary, four arms, lot/lab split, matched-sensitivity rule, prior-knowledge boundary, and fail-closed aggregation are ready.

Product-specific assays, numeric thresholds, lot data, and blinded laboratory confirmation do not exist in this packet. No wet-lab edit, sequence, cell result, product, patient, animal, safety, efficacy, scalability, regulatory, approval, or solved-frontier claim is made.

## Official sources

- [FDA 2024 final guidance page](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/human-gene-therapy-products-incorporating-human-genome-editing)
- [FDA 2024 final guidance PDF](https://www.fda.gov/media/156894/download)
- [FDA 2026 NGS draft page](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/safety-assessment-genome-editing-human-gene-therapy-products-using-next-generation-sequencing)
- [FDA 2026 NGS draft PDF](https://www.fda.gov/media/191966/download)
- [FDA 2026 prior-knowledge draft page](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/leveraging-prior-knowledge-development-human-gene-therapy-products-incorporating-genome-editing)
- [FDA 2026 prior-knowledge draft PDF](https://www.fda.gov/media/192810/download)

Snapshot boundary: the shell transport was redirected to FDA abuse detection, so normalized official-origin text was captured through a relay with explicit origin markers and hashes. No raw-FDA-PDF-byte identity is claimed.
"""
    path.write_text(text, encoding="utf-8")


def write_discussion(result: dict[str, Any], path: Path) -> None:
    checks = result["formal_checks"]
    text = f"""If a genome editor corrects 95% of its target—but one manufacturing lot shows a chromosomal signal—did the editor succeed?

The #060 FDA-guidance audit starts from an uncomfortable answer: **the on-target number is only one cell in the safety table**.

The new protocol maps the 2024 FDA final genome-editing guidance and two 2026 drafts into 15 evidence rows: identity, lot release, functional potency, intended and unintended on-target outcomes, off-target nomination, off-target confirmation, human genetic variation, chromosomal integrity, residual editor, viability/function, immunogenicity, clonal behavior, stability, scale comparability, and long-term follow-up.

Four arms must face identical assays and sequencing sensitivity: unedited cells, mock delivery, the current standard editor/delivery system, and the candidate. The internal gate uses three independent lots and two blinded confirmation laboratories. One failed safety row in one lot rejects promotion; the average cannot rescue it.

The 2026 NGS draft sharpens the most tempting loophole. Nomination and confirmation are different jobs. The union of in-silico, biochemical, cell-based, and genome-wide nominated sites must be frozen before confirmation. Stringent filters cannot be invented after the sites become inconvenient. Human genetic variation and on-target/off-target translocations remain inside the matrix.

The June 2026 prior-knowledge draft creates a second trap: methods and platform experience may sometimes transfer, but that does not mean a safety conclusion transfers. Applicability, source granularity, and bridging still have to be justified; identity, potency, primary-lot stability, and relevant product-specific safety evidence cannot simply be inherited.

Which result should veto the phrase “safe and scalable” even if on-target correction is spectacular?

1. one low-frequency off-target signal that appears in only one assay;
2. one lot whose chromosomal-integrity result crosses its frozen margin;
3. a scale-up lot whose potency passes but viability variability grows;
4. a human-variation analysis that misses the intended population; or
5. a platform-knowledge claim with no product-specific bridging file?

And what would you freeze before seeing the data: every nominated site, the sensitivity floor, the non-inferiority margin, the lot-variability rule, or all of them?

Useful contributions are falsifiable: a missing evidence row, a correction to the FDA mapping, a better blinded-lot failure rule, a defendable matched-sensitivity definition, or a reason a method can—or cannot—be reused across products.

Reproducibility: **{checks['passed']}/{checks['total']}** formal checks over **{len(result['source']['snapshots'])}** hash-bound official-origin text snapshots; an independent parser is run separately. The 2026 documents are drafts, not for implementation. No sequence, editor identity, wet-lab instruction, product result, safety, efficacy, scalability, regulatory, or approval claim is made.
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    benchmark = read_json(args.benchmark)
    if args.capture:
        capture_sources(args.benchmark, benchmark, args.source_dir)
    result = build_result(args.benchmark, benchmark, args.source_dir)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(pretty_json(result), encoding="utf-8")
    write_report(result, args.report)
    write_discussion(result, args.discussion)
    print(
        f"P060 formal checks: {result['formal_checks']['passed']}/{result['formal_checks']['total']} "
        f"decision={result['readiness_decision']['ready_label']}"
    )
    return 0 if result["formal_checks"]["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
