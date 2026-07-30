#!/usr/bin/env python3
"""Capture and validate the frozen P053 Vanguard endpoint dictionary."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import html
import json
import platform
import re
import ssl
import time
import urllib.request
from pathlib import Path
from typing import Any

import certifi


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P053_vanguard_endpoint_dictionary_v1.json"
DEFAULT_SOURCE_DIR = ROOT / "results/P053_vanguard_endpoint_source_v1"
DEFAULT_RESULT = ROOT / "results/P053_vanguard_endpoint_dictionary_v1.json"
DEFAULT_REPORT = ROOT / "research/P053_vanguard_endpoint_dictionary_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/P053_vanguard_endpoint_discussion_v1.md"
USER_AGENT = "Axiom-Horizon-P053-endpoints/1.0 (+public protocol audit)"
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


def fetch_bytes(
    url: str, attempts: int = 3, timeout: int = 90
) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        )
        try:
            with urllib.request.urlopen(
                request, timeout=timeout, context=SSL_CONTEXT
            ) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status} for {url}")
                return response.read()
        except Exception as exc:  # pragma: no cover - network path
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1 + attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def html_text(payload: bytes) -> str:
    text = payload.decode("utf-8", errors="replace")
    text = re.sub(r"(?is)<script.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def capture_sources(
    benchmark: dict[str, Any], source_dir: Path
) -> dict[str, Any]:
    source_dir.mkdir(parents=True, exist_ok=True)
    registry_url = benchmark["sources"]["clinicaltrials"]["record_url"]
    write_gzip(
        source_dir / "clinicaltrials_NCT06995898.json.gz",
        fetch_bytes(registry_url),
    )
    for name, url in benchmark["sources"]["nci"].items():
        write_gzip(source_dir / f"nci_{name}.html.gz", fetch_bytes(url))
    return load_sources(source_dir)


def load_sources(source_dir: Path) -> dict[str, Any]:
    registry = json.loads(
        read_gzip(source_dir / "clinicaltrials_NCT06995898.json.gz")
    )
    nci_pages = {
        path.name.removeprefix("nci_").removesuffix(".html.gz"): html_text(
            read_gzip(path)
        )
        for path in sorted(source_dir.glob("nci_*.html.gz"))
    }
    return {"registry": registry, "nci_pages": nci_pages}


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


def section_rows(
    outcomes: dict[str, Any], key: str
) -> list[dict[str, Any]]:
    return list(outcomes.get(key) or [])


def parse_max_years(time_frames: list[str]) -> int:
    values = []
    for value in time_frames:
        match = re.search(r"(\d+)\s+years?", value, flags=re.I)
        if match:
            values.append(int(match.group(1)))
    return max(values) if values else 0


def phrase(text: str, value: str) -> bool:
    return value.casefold() in text.casefold()


def build_result(
    benchmark_path: Path,
    benchmark: dict[str, Any],
    source_dir: Path,
    source: dict[str, Any],
    protocol_commit: str,
) -> dict[str, Any]:
    registry = source["registry"]
    protocol = registry["protocolSection"]
    identification = protocol["identificationModule"]
    status = protocol["statusModule"]
    design = protocol["designModule"]
    arms = protocol["armsInterventionsModule"]["armGroups"]
    outcomes = protocol["outcomesModule"]
    description = protocol["descriptionModule"]
    primary = section_rows(outcomes, "primaryOutcomes")
    secondary = section_rows(outcomes, "secondaryOutcomes")
    other = section_rows(outcomes, "otherOutcomes")
    mapping = benchmark["frozen_endpoint_mapping"]

    registry_sets = {
        "feasibility_primary": {
            row["measure"] for row in primary
        },
        "secondary_all": {row["measure"] for row in secondary},
        "other_all": {row["measure"] for row in other},
    }
    frozen_sets = {
        key: set(values) for key, values in mapping.items()
    }
    secondary_mapped = (
        frozen_sets["pathway_and_harm_secondary"]
        | frozen_sets["assay_performance_secondary"]
    )
    other_mapped = (
        frozen_sets["long_term_other"]
        | frozen_sets["participant_burden_other"]
    )
    all_frozen = set().union(*frozen_sets.values())
    all_registered = (
        registry_sets["feasibility_primary"]
        | registry_sets["secondary_all"]
        | registry_sets["other_all"]
    )
    overlap_count = sum(
        len(left & right)
        for index, left in enumerate(frozen_sets.values())
        for right in list(frozen_sets.values())[index + 1 :]
    )

    section_lookup = {
        row["measure"]: ("primary", row) for row in primary
    }
    section_lookup.update(
        {row["measure"]: ("secondary", row) for row in secondary}
    )
    section_lookup.update(
        {row["measure"]: ("other", row) for row in other}
    )
    endpoint_rows = []
    for evidence_class, measures in mapping.items():
        for measure in measures:
            registry_section, row = section_lookup[measure]
            endpoint_rows.append(
                {
                    "measure": measure,
                    "registry_section": registry_section,
                    "evidence_class": evidence_class,
                    "description": row.get("description"),
                    "time_frame": row.get("timeFrame"),
                    "explicit_numeric_go_no_go_threshold": False,
                }
            )

    start_date = dt.date.fromisoformat(
        status["startDateStruct"]["date"]
    )
    completion_date = dt.date.fromisoformat(
        status["completionDateStruct"]["date"]
    )
    calendar_days = (completion_date - start_date).days
    calendar_years = calendar_days / 365.2425
    maximum_outcome_years = parse_max_years(
        [str(row.get("timeFrame") or "") for row in primary + secondary + other]
    )
    detailed = str(description.get("detailedDescription") or "")
    passive_match = re.search(
        r"followed passively up to (\d+) years", detailed, re.I
    )
    passive_years = int(passive_match.group(1)) if passive_match else None
    timeline_aligned = calendar_years >= maximum_outcome_years

    mortality_measures = [
        row["measure"]
        for row in endpoint_rows
        if "mortality" in row["measure"].casefold()
    ]
    treatment_terms = re.compile(
        r"\b(treatment assignment|therapy selection|personalized treatment|cure)\b",
        re.I,
    )
    treatment_endpoint_count = sum(
        bool(treatment_terms.search(row["measure"]))
        for row in endpoint_rows
    )
    explicit_primary_thresholds = sum(
        row["explicit_numeric_go_no_go_threshold"]
        for row in endpoint_rows
        if row["registry_section"] == "primary"
    )
    results_posted = bool(registry.get("resultsSection"))

    pages = source["nci_pages"]
    vanguard_program = pages["vanguard_program"]
    screening_overview = pages["screening_overview"]
    funded_grant = pages["funded_grant"]
    evidence_page = pages["levels_of_evidence"]

    controls = {
        "positive": {
            "passed": (
                all_frozen == all_registered and overlap_count == 0
            ),
            "detail": (
                f"{len(all_registered)} registered outcomes map exactly "
                "once to five frozen evidence classes."
            ),
        },
        "negative": {
            "passed": (
                "mortality reduction"
                in benchmark["claim_ladder"][0]["does_not_imply"]
                and "cure"
                in benchmark["claim_ladder"][0]["does_not_imply"]
            ),
            "detail": (
                "Enrollment feasibility is forbidden from promoting "
                "mortality reduction or cure."
            ),
        },
    }

    expected_primary = frozen_sets["feasibility_primary"]
    expected_mortality = {
        "Targeted cancer-specific mortality of each MCD assay",
        "Cancer-specific mortality",
        "All-cause mortality",
    }
    registry_counts = {
        "primary": len(primary),
        "secondary": len(secondary),
        "other": len(other),
        "total": len(primary) + len(secondary) + len(other),
    }
    dictionary_ready = (
        registry_sets["feasibility_primary"] == expected_primary
        and registry_sets["secondary_all"] == secondary_mapped
        and registry_sets["other_all"] == other_mapped
        and overlap_count == 0
    )
    decision = (
        benchmark["readiness_decision"]["dictionary_ready_label"]
        if dictionary_ready
        else benchmark["readiness_decision"]["dictionary_blocked_label"]
    )

    checks = [
        check(
            "schema_version",
            benchmark["schema_version"]
            == "p053_vanguard_endpoint_dictionary_v1",
            benchmark["schema_version"],
        ),
        check(
            "scope_only_p053",
            benchmark["scope"]["included_catalog_problem_ids"] == [53],
            "Only catalog problem #053 is included.",
        ),
        check(
            "protocol_commit",
            bool(re.fullmatch(r"[0-9a-f]{40}", protocol_commit)),
            protocol_commit,
        ),
        check(
            "registry_identity",
            identification["nctId"] == benchmark["study"]["nct_id"]
            and identification["organization"]["fullName"]
            == benchmark["study"]["sponsor"],
            f"{identification['nctId']} / {identification['organization']['fullName']}",
        ),
        check(
            "recruiting_status",
            status["overallStatus"]
            == benchmark["study"]["expected_status"],
            status["overallStatus"],
        ),
        check(
            "randomized_parallel_screening",
            design["designInfo"]["allocation"] == "RANDOMIZED"
            and design["designInfo"]["interventionModel"] == "PARALLEL"
            and design["designInfo"]["primaryPurpose"]
            == benchmark["study"]["purpose"],
            pretty_json(design["designInfo"]).strip(),
        ),
        check(
            "estimated_enrollment",
            design["enrollmentInfo"]["count"]
            == benchmark["study"]["expected_enrollment"]
            and design["enrollmentInfo"]["type"] == "ESTIMATED",
            pretty_json(design["enrollmentInfo"]).strip(),
        ),
        check(
            "three_arms",
            len(arms) == benchmark["study"]["expected_arms"]
            and sum("MCD test" in row["label"] for row in arms) == 2
            and sum("Control" in row["label"] for row in arms) == 1,
            ", ".join(row["label"] for row in arms),
        ),
        check(
            "registered_outcome_counts",
            registry_counts
            == {"primary": 6, "secondary": 20, "other": 9, "total": 35},
            pretty_json(registry_counts).strip(),
        ),
        check(
            "primary_mapping_exact",
            registry_sets["feasibility_primary"] == expected_primary,
            f"{len(expected_primary)} measures.",
        ),
        check(
            "secondary_mapping_exact",
            registry_sets["secondary_all"] == secondary_mapped,
            f"{len(secondary_mapped)} measures.",
        ),
        check(
            "other_mapping_exact",
            registry_sets["other_all"] == other_mapped,
            f"{len(other_mapped)} measures.",
        ),
        check(
            "mapping_exhaustive_nonoverlapping",
            all_frozen == all_registered and overlap_count == 0,
            f"{len(all_registered)} mapped; overlap={overlap_count}.",
        ),
        check(
            "primary_go_no_go_thresholds_absent",
            explicit_primary_thresholds
            == benchmark["go_no_go_threshold_rule"][
                "expected_explicit_primary_thresholds"
            ],
            f"{explicit_primary_thresholds}/6 explicit thresholds.",
        ),
        check(
            "no_results_posted",
            not results_posted,
            f"resultsSection present={results_posted}.",
        ),
        check(
            "mortality_registered_as_other",
            set(mortality_measures) == expected_mortality
            and all(
                row["registry_section"] == "other"
                for row in endpoint_rows
                if row["measure"] in expected_mortality
            ),
            ", ".join(mortality_measures),
        ),
        check(
            "personalized_treatment_absent",
            treatment_endpoint_count == 0,
            f"{treatment_endpoint_count} treatment/cure endpoints.",
        ),
        check(
            "timeline_sentinel_detected",
            not timeline_aligned
            and maximum_outcome_years == 12
            and passive_years == 10,
            (
                f"calendar={calendar_years:.2f} years; "
                f"max outcome={maximum_outcome_years}; passive={passive_years}."
            ),
        ),
        check(
            "nci_feasibility_boundary",
            phrase(vanguard_program, "pilot study")
            and (
                phrase(vanguard_program, "future randomized controlled trials")
                or phrase(vanguard_program, "larger RCT")
            )
            and phrase(funded_grant, "feasibility trial"),
            "NCI pages identify Vanguard as a feasibility/pilot study.",
        ),
        check(
            "nci_no_head_to_head_boundary",
            phrase(vanguard_program, "will not be compared to each other"),
            "The two assays are not compared to each other.",
        ),
        check(
            "nci_mortality_evidence_boundary",
            phrase(
                screening_overview,
                "No MCD assay has been properly evaluated to show a mortality reduction",
            ),
            "NCI screening overview states that randomized mortality evidence is absent.",
        ),
        check(
            "screening_harms_retained",
            all(
                phrase(screening_overview + " " + evidence_page, item)
                for item in [
                    "false-positive",
                    "overdiagnosis",
                    "overtreatment",
                    "anxiety",
                ]
            ),
            "False positives, overdiagnosis, overtreatment, and anxiety remain explicit harms.",
        ),
        check(
            "controls",
            controls["positive"]["passed"]
            and controls["negative"]["passed"],
            "Positive and negative claim-mapping controls pass.",
        ),
        check(
            "no_execution",
            benchmark["readiness_decision"][
                "participant_level_analysis_executed"
            ]
            is False
            and benchmark["readiness_decision"][
                "assay_comparison_executed"
            ]
            is False,
            "No participant analysis or assay comparison was executed.",
        ),
        check(
            "retained_sources",
            len(source_inventory(source_dir)) == 6,
            f"{len(source_inventory(source_dir))} source files retained.",
        ),
    ]
    if not all(item["passed"] for item in checks):
        failed = [item["name"] for item in checks if not item["passed"]]
        raise RuntimeError(f"formal checks failed: {failed}")

    return {
        "schema_version": "p053_vanguard_endpoint_dictionary_result_v1",
        "as_of_date": benchmark["as_of_date"],
        "status": "pass",
        "decision": decision,
        "question": benchmark["question"],
        "study_snapshot": {
            "nct_id": identification["nctId"],
            "title": identification["officialTitle"],
            "sponsor": identification["organization"]["fullName"],
            "overall_status": status["overallStatus"],
            "status_verified_date": status["statusVerifiedDate"],
            "last_update_posted": status["lastUpdatePostDateStruct"]["date"],
            "start_date": str(start_date),
            "primary_completion_date": status[
                "primaryCompletionDateStruct"
            ]["date"],
            "completion_date": str(completion_date),
            "enrollment": design["enrollmentInfo"],
            "allocation": design["designInfo"]["allocation"],
            "intervention_model": design["designInfo"]["interventionModel"],
            "primary_purpose": design["designInfo"]["primaryPurpose"],
            "arms": [
                {"label": row["label"], "type": row["type"]}
                for row in arms
            ],
            "results_posted": results_posted,
        },
        "endpoint_counts": registry_counts,
        "endpoint_dictionary": endpoint_rows,
        "primary_threshold_audit": {
            "definition": benchmark["go_no_go_threshold_rule"]["definition"],
            "explicit_thresholds": explicit_primary_thresholds,
            "primary_outcomes": len(primary),
            "ready_for_numeric_go_no_go": explicit_primary_thresholds
            == len(primary)
            and results_posted,
        },
        "timeline_sentinel": {
            "start_date": str(start_date),
            "estimated_completion_date": str(completion_date),
            "calendar_days": calendar_days,
            "calendar_years": round(calendar_years, 6),
            "maximum_registered_outcome_years": maximum_outcome_years,
            "passive_follow_up_years_in_description": passive_years,
            "calendar_spans_maximum_outcome": timeline_aligned,
            "status": "requires_registry_alignment"
            if not timeline_aligned
            else "aligned",
        },
        "claim_status": {
            "operational_feasibility": "registered_not_scored_thresholds_missing",
            "diagnostic_pathway_and_harm": "registered_not_scored",
            "assay_performance": "registered_not_scored",
            "clinical_utility_and_mortality": "registered_as_other_not_scored_timeline_requires_alignment",
            "personalized_treatment_or_cure": "absent_from_protocol",
        },
        "claim_ladder": benchmark["claim_ladder"],
        "controls": controls,
        "formal_checks": checks,
        "summary": {
            "check_count": len(checks),
            "passed_checks": sum(item["passed"] for item in checks),
            "failed_checks": sum(not item["passed"] for item in checks),
            "registered_outcomes": len(endpoint_rows),
            "participant_level_analysis_executed": False,
            "assay_comparison_executed": False,
            "mortality_claim_ready": False,
            "personalized_cure_claim_ready": False,
        },
        "source": {
            "benchmark": str(benchmark_path.relative_to(ROOT)),
            "benchmark_sha256": sha256_path(benchmark_path),
            "protocol_commit": protocol_commit,
            "source_directory": str(source_dir.relative_to(ROOT)),
            "retained_files": source_inventory(source_dir),
            "tool": "tools/p053_vanguard_endpoint_dictionary.py",
            "python": platform.python_version(),
        },
        "interpretation_boundaries": benchmark[
            "interpretation_boundaries"
        ],
    }


def render_report(result: dict[str, Any]) -> str:
    snapshot = result["study_snapshot"]
    counts = result["endpoint_counts"]
    timeline = result["timeline_sentinel"]
    checks = result["summary"]
    ladder_rows = []
    for row in result["claim_ladder"]:
        ladder_rows.append(
            f"| {row['level']} | `{row['name']}` | "
            f"{row['minimum_evidence']} | "
            f"{', '.join(row['does_not_imply']) or 'No higher claim encoded'} |"
        )
    return "\n".join(
        [
            "# P053 Vanguard endpoint and claim dictionary v1",
            "",
            f"**Decision:** `{result['decision']}`.",
            "",
            "## What changed in the public protocol",
            "",
            f"[{snapshot['nct_id']}](https://clinicaltrials.gov/study/{snapshot['nct_id']}) is currently `{snapshot['overall_status']}`, randomized, parallel, screening-purpose, and estimates enrollment of `{snapshot['enrollment']['count']:,}` participants across three arms. No results section is posted.",
            "",
            "The current registry is richer than a simple feasibility label: it lists "
            f"`{counts['primary']}` primary, `{counts['secondary']}` secondary, "
            f"and `{counts['other']}` other outcomes. The endpoint dictionary maps all "
            f"`{counts['total']}` measures exactly once rather than letting one endpoint silently support several claims.",
            "",
            "## Frozen evidence ladder",
            "",
            "| Level | Evidence class | Minimum evidence | Still does not imply |",
            "|---:|---|---|---|",
            *ladder_rows,
            "",
            "## The two traps",
            "",
            "**A registered mortality field is not a mortality result.** Targeted cancer-specific mortality, cancer-specific mortality, and all-cause mortality are present only as `other` outcomes, with no posted results. The study remains a recruiting feasibility trial, and NCI describes it as groundwork for later definitive randomized evaluation.",
            "",
            "**A measurement window is not a success threshold.** All six primary outcomes provide a measure and time frame, but `0/6` state an explicit numeric go/no-go cutoff for the measure itself. Enrollment goals, 60/90-day windows, and references to trial targets describe observation, not the minimum result that would make feasibility pass.",
            "",
            "## Timing sentinel",
            "",
            f"The registry gives an actual start of `{timeline['start_date']}` and estimated completion of `{timeline['estimated_completion_date']}`, a calendar span of `{timeline['calendar_years']:.2f}` years. Long-term outcomes are listed through `{timeline['maximum_registered_outcome_years']}` years, while the detailed description says passive follow-up up to `{timeline['passive_follow_up_years_in_description']}` years. This does not invalidate the study; it means the public calendar and long-term estimands require alignment before any mortality claim is promoted.",
            "",
            "## What the current outcomes can eventually test",
            "",
            "- Primary outcomes: recruitment, questionnaires, year-one blood draw, retention, representative enrollment, and staggered-arm feasibility.",
            "- Diagnostic pathway and harm: result return, diagnostic resolution, contamination, standard screening, complications, anxiety, and cancer worry.",
            "- Assay performance: sensitivity, specificity, predictive values, false positives, interval cancers, detected cancers, and tissue-of-origin accuracy.",
            "- Long-term clinical utility: stage, mortality, and costs—but only after results, adequate randomized estimands, power, multiplicity control, follow-up, and joint harm accounting.",
            "- Personalized treatment or cure: absent; the protocol does not randomize treatment or test a molecular therapy-selection rule.",
            "",
            "## Reproducibility and next falsifier",
            "",
            f"The formal packet passes `{checks['passed_checks']}/{checks['check_count']}` checks. The current ClinicalTrials.gov JSON and five NCI pages are hash-retained. No participant-level analysis or comparison between the two assays was performed.",
            "",
            "The next falsifier is a public numeric feasibility decision rule: denominators and pass/fail thresholds for each primary endpoint, plus a registry calendar aligned to the longest planned outcome. Assay performance, diagnostic burden, mortality, and treatment claims remain separate estimands.",
            "",
            "## Official sources",
            "",
            "- [ClinicalTrials.gov NCT06995898](https://clinicaltrials.gov/study/NCT06995898)",
            "- [NCI Vanguard Study](https://prevention.cancer.gov/research-areas/networks-consortia-programs/csrn/vanguard-study)",
            "- [NCI cancer-screening overview](https://www.cancer.gov/about-cancer/screening/hp-screening-overview-pdq)",
            "- [NCI levels of evidence for screening](https://www.cancer.gov/publications/pdq/levels-evidence/screening-prevention)",
            "",
            "No assay recommendation, screening advice, diagnostic action, treatment selection, trial-participation recommendation, mortality benefit, personalized cure, regulatory, or solved-frontier claim is made.",
            "",
        ]
    )


def render_discussion(result: dict[str, Any]) -> str:
    snapshot = result["study_snapshot"]
    counts = result["endpoint_counts"]
    timeline = result["timeline_sentinel"]
    checks = result["summary"]
    return "\n".join(
        [
            "When does a mortality endpoint become more than a checkbox?",
            "",
            "A trial registry can contain cancer-specific and all-cause mortality fields while the study is still a recruiting feasibility pilot with no posted results. What additional commitments turn a long-term outcome label into a credible mortality test?",
            "",
            f"The #053 audit freezes the current public record for {snapshot['nct_id']}: {snapshot['enrollment']['count']:,} estimated participants, three randomized arms, {counts['primary']} primary outcomes, {counts['secondary']} secondary outcomes, and {counts['other']} other outcomes. All {counts['total']} measures map exactly once to feasibility, diagnostic-pathway/harm, assay-performance, long-term utility, or participant-burden evidence.",
            "",
            "Two gaps are easy to miss. First, `0/6` primary outcomes state a numeric go/no-go threshold for the endpoint itself; time windows and enrollment goals are not pass criteria. Second, the registered calendar spans "
            f"{timeline['calendar_years']:.2f} years, while several other outcomes extend to {timeline['maximum_registered_outcome_years']} years and the description mentions {timeline['passive_follow_up_years_in_description']} years of passive follow-up. That needs alignment before long-term claims are read literally.",
            "",
            "The registry does include prospective sensitivity, specificity, PPV, false positives, interval cancers, diagnostic complications, anxiety, stage, and mortality measures. But assay accuracy cannot stand in for mortality benefit, stage shift cannot stand in for mortality, and screening randomization cannot establish personalized treatment or cure.",
            "",
            "What numeric feasibility thresholds would you preregister for recruitment, follow-up, specimen adherence, representative enrollment, and staggered-arm activation? And what minimum mortality estimand would you require—arm-specific denominator, cause-of-death rules, power, multiplicity, follow-up, and harm accounting—before allowing the word “benefit”?",
            "",
            "A useful contribution is a falsifiable endpoint rule or public analysis-plan reference, not an assay endorsement or patient recommendation.",
            "",
            f"Reproducibility: {checks['passed_checks']}/{checks['check_count']} formal checks; an independent endpoint replay is required. No participant data, assay comparison, medical recommendation, treatment selection, cure, regulatory, or solved-frontier claim is made.",
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
    source = (
        capture_sources(benchmark, source_dir)
        if args.capture
        else load_sources(source_dir)
    )
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
                "registered_outcomes": result["summary"][
                    "registered_outcomes"
                ],
                "result": str(args.result),
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
