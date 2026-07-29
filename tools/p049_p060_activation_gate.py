#!/usr/bin/env python3
"""Validate and render the catalog #049-#060 activation-gate packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


EXPECTED_IDS = list(range(49, 61))
ALLOWED_READINESS = {
    "ready_for_public_replay",
    "ready_after_access",
    "protocol_only_high_stakes",
}
REQUIRED_SOURCE_FIELDS = {
    "publisher",
    "title",
    "url",
    "latest_update",
    "access",
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def catalog_titles(path: Path) -> dict[int, str]:
    payload = read_json(path)
    records = payload.get("problems") or payload.get("records") or payload.get("items")
    if not isinstance(records, list):
        raise ValueError("catalog must contain a problems, records, or items array")
    return {
        int(problem["id"]): str(problem["title"])
        for problem in records
        if int(problem["id"]) in EXPECTED_IDS
    }


def validate(packet: dict[str, Any], titles: dict[int, str]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    scope = packet.get("scope", {})
    problems = packet.get("problems", [])
    ids = [problem.get("id") for problem in problems]
    check("exact_scope_ids", ids == EXPECTED_IDS, f"observed={ids}")
    check(
        "declared_scope_ids",
        scope.get("problem_ids") == EXPECTED_IDS,
        f"declared={scope.get('problem_ids')}",
    )
    check(
        "activation_claim_only",
        scope.get("claim_level") == "activation_gate_only",
        f"claim_level={scope.get('claim_level')}",
    )
    check(
        "catalog_not_mutated",
        scope.get("catalog_mutation") is False,
        f"catalog_mutation={scope.get('catalog_mutation')}",
    )
    check(
        "no_intervention_executed",
        scope.get("human_or_animal_intervention") is False,
        f"human_or_animal_intervention={scope.get('human_or_animal_intervention')}",
    )

    required = set(packet.get("required_fields", []))
    missing_fields = {
        str(problem.get("id")): sorted(required - set(problem))
        for problem in problems
        if required - set(problem)
    }
    check("required_fields_complete", not missing_fields, str(missing_fields or "complete"))

    title_mismatches = {
        problem["id"]: {
            "catalog": titles.get(problem["id"]),
            "packet": problem.get("title"),
        }
        for problem in problems
        if titles.get(problem["id"]) != problem.get("title")
    }
    check("catalog_titles_match", not title_mismatches, str(title_mismatches or "match"))

    non_questions = [
        problem["id"]
        for problem in problems
        if not str(problem.get("heuristic_question", "")).endswith("?")
    ]
    check("heuristic_questions", not non_questions, f"non_questions={non_questions}")

    invalid_readiness = {
        problem["id"]: problem.get("execution_readiness")
        for problem in problems
        if problem.get("execution_readiness") not in ALLOWED_READINESS
    }
    check("readiness_enum", not invalid_readiness, str(invalid_readiness or "valid"))

    incomplete_sources: dict[int, list[str]] = {}
    invalid_urls: dict[int, str] = {}
    for problem in problems:
        source = problem.get("source", {})
        missing = sorted(REQUIRED_SOURCE_FIELDS - set(source))
        if missing:
            incomplete_sources[problem["id"]] = missing
        url = str(source.get("url", ""))
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            invalid_urls[problem["id"]] = url
    check(
        "source_fields_complete",
        not incomplete_sources,
        str(incomplete_sources or "complete"),
    )
    check("source_urls_https", not invalid_urls, str(invalid_urls or "valid"))

    empty_gate_fields: dict[int, list[str]] = {}
    gate_fields = {
        "first_gate",
        "denominator",
        "primary_metric",
        "acceptance_rule",
        "falsifier",
        "data_split",
        "safety_boundary",
        "next_artifact",
    }
    for problem in problems:
        empty = sorted(field for field in gate_fields if not str(problem.get(field, "")).strip())
        if empty:
            empty_gate_fields[problem["id"]] = empty
    check("gate_fields_nonempty", not empty_gate_fields, str(empty_gate_fields or "complete"))

    check(
        "unique_ids",
        len(ids) == len(set(ids)) == len(EXPECTED_IDS),
        f"count={len(ids)} unique={len(set(ids))}",
    )
    return checks


def render_report(packet: dict[str, Any], result: dict[str, Any]) -> str:
    problems = packet["problems"]
    readiness = Counter(problem["execution_readiness"] for problem in problems)
    lines = [
        "# Problems #049–#060 Activation Gate v1",
        "",
        "Date: 2026-07-29",
        "",
        "Status: **activation packet validated; no frontier problem is claimed solved.**",
        "",
        "This packet reopens only catalog problems **#049 through #060**. It does not revise the frozen",
        "100-problem catalog, execute a human/animal intervention, or touch any other research lane.",
        "Its contribution is narrower and auditable: each problem now has one heuristic question, one",
        "first falsifiable gate, an explicit denominator, a holdout rule, and a safety boundary.",
        "",
        "## Machine-check summary",
        "",
        f"- Scope: `{result['summary']['problem_count']}/12` exact catalog IDs.",
        f"- Contract checks: `{result['summary']['passed_checks']}/{result['summary']['check_count']}` passed.",
        f"- Ready for public replay: `{readiness['ready_for_public_replay']}`.",
        f"- Ready after data/access work: `{readiness['ready_after_access']}`.",
        f"- Protocol-only high-stakes lanes: `{readiness['protocol_only_high_stakes']}`.",
        f"- Packet SHA-256: `{result['source']['packet_sha256']}`.",
        "",
        "## Activation matrix",
        "",
        "| ID | Heuristic question | First denominator | Acceptance boundary | Readiness |",
        "|---:|---|---|---|---|",
    ]
    for problem in problems:
        lines.append(
            "| #{id:03d} | {question} | {denominator} | {acceptance} | `{readiness}` |".format(
                id=problem["id"],
                question=problem["heuristic_question"].replace("|", "\\|"),
                denominator=problem["denominator"].replace("|", "\\|"),
                acceptance=problem["acceptance_rule"].replace("|", "\\|"),
                readiness=problem["execution_readiness"],
            )
        )

    lines.extend(["", "## Problem-by-problem research entry points", ""])
    for problem in problems:
        source = problem["source"]
        lines.extend(
            [
                f"### #{problem['id']:03d} — {problem['title']}",
                "",
                f"**Question.** {problem['heuristic_question']}",
                "",
                f"**Current evidence boundary.** {problem['current_evidence_boundary']}",
                "",
                f"**First gate.** {problem['first_gate']}",
                "",
                f"**Denominator.** {problem['denominator']}",
                "",
                f"**Primary metric.** {problem['primary_metric']}",
                "",
                f"**Acceptance rule.** {problem['acceptance_rule']}",
                "",
                f"**Falsifier.** {problem['falsifier']}",
                "",
                f"**Split.** {problem['data_split']}",
                "",
                f"**Safety boundary.** {problem['safety_boundary']}",
                "",
                f"**Next artifact.** {problem['next_artifact']}",
                "",
                f"**Source.** [{source['publisher']} — {source['title']}]({source['url']}). "
                f"{source['latest_update']} Access: {source['access']}.",
                "",
            ]
        )

    lines.extend(
        [
            "## Claim boundary",
            "",
            "Passing this packet means only that all twelve projects have an auditable first research gate.",
            "It does **not** mean the gates have been executed, that any result generalizes, or that any of",
            "the twelve frontier problems has been solved. Retrospective prediction does not establish",
            "causality; protocol design does not establish clinical benefit; and a safety checklist does",
            "not establish safety.",
            "",
        ]
    )
    return "\n".join(lines)


def render_discussion(packet: dict[str, Any], result: dict[str, Any]) -> str:
    rows = []
    for problem in packet["problems"]:
        rows.append(
            f"- **#{problem['id']:03d} {problem['title']}** — {problem['heuristic_question']}"
        )
    return "\n".join(
        [
            "# Which of twelve frontier problems can be falsified before it can be solved?",
            "",
            "Problems #049–#060 span reaction dynamics, self-assembly, protein ensembles,",
            "genotype-to-phenotype maps, cancer screening, aging, neurodegeneration, immune",
            "control, antimicrobial resistance, pandemic warning, connectomics, and gene editing.",
            "That breadth creates a dangerous temptation: count datasets, model parameters, or papers",
            "as progress. This update takes the opposite test—what is the first result that could",
            "honestly fail?",
            "",
            f"The new activation packet passes `{result['summary']['passed_checks']}/"
            f"{result['summary']['check_count']}` machine checks and gives every problem an explicit",
            "denominator, unopened-data rule, falsifier, and safety boundary:",
            "",
            *rows,
            "",
            "Three questions for collaborators:",
            "",
            "1. Which denominator above is still too weak to make a positive result interesting?",
            "2. Which acceptance threshold would you tighten before any data are opened?",
            "3. Which public dataset or independent replay team could attack one gate without expanding",
            "   beyond #049–#060?",
            "",
            "The boundary matters: this is an activation packet, not twelve claimed solutions. High-risk",
            "medical and biological lanes remain protocol-only; no intervention is executed.",
            "",
            "Research packet: `research/P049_P060_activation_gate_v1.md`",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--packet",
        type=Path,
        default=Path("benchmarks/P049_P060_activation_gate_v1.json"),
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("research/problem_catalog_100.json"),
    )
    parser.add_argument(
        "--result",
        type=Path,
        default=Path("results/P049_P060_activation_gate_v1.json"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("research/P049_P060_activation_gate_v1.md"),
    )
    parser.add_argument(
        "--discussion",
        type=Path,
        default=Path("research/P049_P060_discussion_prompt_v1.md"),
    )
    args = parser.parse_args()

    packet = read_json(args.packet)
    titles = catalog_titles(args.catalog)
    checks = validate(packet, titles)
    passed = sum(check["passed"] for check in checks)
    result = {
        "schema_version": "p049_p060_activation_gate_result_v1",
        "status": "pass" if passed == len(checks) else "fail",
        "source": {
            "packet": str(args.packet),
            "packet_sha256": sha256_bytes(args.packet.read_bytes()),
            "canonical_packet_sha256": sha256_bytes(canonical_json(packet)),
            "catalog": str(args.catalog),
            "catalog_sha256": sha256_bytes(args.catalog.read_bytes()),
        },
        "scope": packet["scope"],
        "summary": {
            "problem_count": len(packet["problems"]),
            "problem_ids": [problem["id"] for problem in packet["problems"]],
            "check_count": len(checks),
            "passed_checks": passed,
            "failed_checks": len(checks) - passed,
            "readiness_counts": dict(
                sorted(
                    Counter(
                        problem["execution_readiness"] for problem in packet["problems"]
                    ).items()
                )
            ),
        },
        "checks": checks,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.discussion.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    args.report.write_text(render_report(packet, result), encoding="utf-8")
    args.discussion.write_text(render_discussion(packet, result), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": result["status"],
                "problem_count": result["summary"]["problem_count"],
                "checks": f"{passed}/{len(checks)}",
                "result": str(args.result),
                "report": str(args.report),
                "discussion": str(args.discussion),
            },
            indent=2,
        )
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
