#!/usr/bin/env python3
"""Independent source replay for the P053 Vanguard endpoint dictionary."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import html
import json
import platform
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/P053_vanguard_endpoint_dictionary_v1.json"
DEFAULT_RESULT = ROOT / "results/P053_vanguard_endpoint_dictionary_v1.json"
DEFAULT_AUDIT = ROOT / "results/P053_vanguard_endpoint_dictionary_audit_v1.json"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pretty_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def read_gzip_json(path: Path) -> dict[str, Any]:
    return json.loads(gzip.decompress(path.read_bytes()))


def independent_html_text(path: Path) -> str:
    text = gzip.decompress(path.read_bytes()).decode(
        "utf-8", errors="replace"
    )
    text = re.sub(r"(?is)<script.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


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


def max_years(values: list[str]) -> int:
    years = []
    for value in values:
        match = re.search(r"(\d+)\s+years?", value, flags=re.I)
        if match:
            years.append(int(match.group(1)))
    return max(years) if years else 0


def build_audit(
    benchmark_path: Path, result_path: Path
) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    result = read_json(result_path)
    source_dir = ROOT / result["source"]["source_directory"]
    registry = read_gzip_json(
        source_dir / "clinicaltrials_NCT06995898.json.gz"
    )
    protocol = registry["protocolSection"]
    outcomes = protocol["outcomesModule"]
    primary = list(outcomes.get("primaryOutcomes") or [])
    secondary = list(outcomes.get("secondaryOutcomes") or [])
    other = list(outcomes.get("otherOutcomes") or [])
    mapping = benchmark["frozen_endpoint_mapping"]
    frozen_classes = {
        name: set(values) for name, values in mapping.items()
    }
    registered = {
        "feasibility_primary": {row["measure"] for row in primary},
        "secondary_all": {row["measure"] for row in secondary},
        "other_all": {row["measure"] for row in other},
    }
    secondary_mapped = (
        frozen_classes["pathway_and_harm_secondary"]
        | frozen_classes["assay_performance_secondary"]
    )
    other_mapped = (
        frozen_classes["long_term_other"]
        | frozen_classes["participant_burden_other"]
    )
    all_frozen = set().union(*frozen_classes.values())
    all_registered = (
        registered["feasibility_primary"]
        | registered["secondary_all"]
        | registered["other_all"]
    )
    memberships: dict[str, int] = {}
    for values in frozen_classes.values():
        for value in values:
            memberships[value] = memberships.get(value, 0) + 1

    result_rows = {
        row["measure"]: {
            "registry_section": row["registry_section"],
            "evidence_class": row["evidence_class"],
            "time_frame": row["time_frame"],
            "threshold": row[
                "explicit_numeric_go_no_go_threshold"
            ],
        }
        for row in result["endpoint_dictionary"]
    }
    reconstructed_rows: dict[str, Any] = {}
    section_rows = [
        ("primary", primary),
        ("secondary", secondary),
        ("other", other),
    ]
    class_by_measure = {
        value: name
        for name, values in frozen_classes.items()
        for value in values
    }
    for section, rows in section_rows:
        for row in rows:
            reconstructed_rows[row["measure"]] = {
                "registry_section": section,
                "evidence_class": class_by_measure[row["measure"]],
                "time_frame": row.get("timeFrame"),
                "threshold": False,
            }

    status = protocol["statusModule"]
    start = dt.date.fromisoformat(status["startDateStruct"]["date"])
    completion = dt.date.fromisoformat(
        status["completionDateStruct"]["date"]
    )
    calendar_days = (completion - start).days
    all_time_frames = [
        str(row.get("timeFrame") or "")
        for row in primary + secondary + other
    ]
    outcome_years = max_years(all_time_frames)
    detailed = protocol["descriptionModule"]["detailedDescription"]
    passive = re.search(
        r"followed passively up to (\d+) years", detailed, re.I
    )
    passive_years = int(passive.group(1)) if passive else None

    program_text = independent_html_text(
        source_dir / "nci_vanguard_program.html.gz"
    )
    screening_text = independent_html_text(
        source_dir / "nci_screening_overview.html.gz"
    )
    current_sources = source_inventory(source_dir)
    checks = [
        check(
            "scope_only_p053",
            benchmark["scope"]["included_catalog_problem_ids"] == [53],
            "Only catalog problem #053 is included.",
        ),
        check(
            "registry_identity_replayed",
            protocol["identificationModule"]["nctId"] == "NCT06995898"
            and protocol["identificationModule"]["organization"][
                "fullName"
            ]
            == "National Cancer Institute (NCI)",
            protocol["identificationModule"]["nctId"],
        ),
        check(
            "study_design_replayed",
            protocol["statusModule"]["overallStatus"] == "RECRUITING"
            and protocol["designModule"]["designInfo"]["allocation"]
            == "RANDOMIZED"
            and protocol["designModule"]["enrollmentInfo"]["count"]
            == 24000
            and len(
                protocol["armsInterventionsModule"]["armGroups"]
            )
            == 3,
            "Recruiting / randomized / 24,000 / 3 arms.",
        ),
        check(
            "outcome_counts_replayed",
            [len(primary), len(secondary), len(other)]
            == [
                result["endpoint_counts"]["primary"],
                result["endpoint_counts"]["secondary"],
                result["endpoint_counts"]["other"],
            ]
            == [6, 20, 9],
            f"{len(primary)}/{len(secondary)}/{len(other)}.",
        ),
        check(
            "frozen_mapping_exact",
            registered["feasibility_primary"]
            == frozen_classes["feasibility_primary"]
            and registered["secondary_all"] == secondary_mapped
            and registered["other_all"] == other_mapped,
            f"{len(all_registered)} measures.",
        ),
        check(
            "mapping_once_only",
            all_frozen == all_registered
            and all(value == 1 for value in memberships.values()),
            f"{len(memberships)} unique memberships.",
        ),
        check(
            "endpoint_rows_replayed",
            reconstructed_rows == result_rows,
            f"{len(reconstructed_rows)} exact rows.",
        ),
        check(
            "threshold_absence_replayed",
            not any(
                row["threshold"]
                for row in reconstructed_rows.values()
                if row["registry_section"] == "primary"
            )
            and result["primary_threshold_audit"][
                "explicit_thresholds"
            ]
            == 0,
            "0/6 explicit numeric go/no-go thresholds.",
        ),
        check(
            "no_results_and_no_cure_replayed",
            not registry.get("resultsSection")
            and result["claim_status"][
                "personalized_treatment_or_cure"
            ]
            == "absent_from_protocol",
            "No resultsSection; no treatment/cure endpoint.",
        ),
        check(
            "timeline_replayed",
            calendar_days == result["timeline_sentinel"]["calendar_days"]
            and outcome_years
            == result["timeline_sentinel"][
                "maximum_registered_outcome_years"
            ]
            == 12
            and passive_years
            == result["timeline_sentinel"][
                "passive_follow_up_years_in_description"
            ]
            == 10,
            f"{calendar_days} days / {outcome_years} years / passive {passive_years}.",
        ),
        check(
            "nci_boundaries_replayed",
            "pilot study" in program_text.casefold()
            and "will not be compared to each other"
            in program_text.casefold()
            and "no mcd assay has been properly evaluated to show a mortality reduction"
            in screening_text.casefold(),
            "Feasibility, no head-to-head comparison, and mortality boundary found.",
        ),
        check(
            "source_hashes_exact",
            current_sources == result["source"]["retained_files"],
            f"{len(current_sources)} source files.",
        ),
    ]
    if not all(item["passed"] for item in checks):
        failed = [item["name"] for item in checks if not item["passed"]]
        raise RuntimeError(f"independent audit failed: {failed}")
    return {
        "schema_version": "p053_vanguard_endpoint_dictionary_audit_v1",
        "status": "pass",
        "decision_replayed": result["decision"],
        "reconstructed_outcome_counts": {
            "primary": len(primary),
            "secondary": len(secondary),
            "other": len(other),
            "total": len(all_registered),
        },
        "reconstructed_timeline": {
            "calendar_days": calendar_days,
            "maximum_outcome_years": outcome_years,
            "passive_follow_up_years": passive_years,
        },
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
            "tool": "tools/p053_vanguard_endpoint_audit.py",
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
