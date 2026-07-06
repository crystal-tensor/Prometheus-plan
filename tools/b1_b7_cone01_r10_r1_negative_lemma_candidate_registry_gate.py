#!/usr/bin/env python3
"""T-B1-004dl/T-B7-012u: R10 R1 negative-lemma candidate registry gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r10_r1_negative_lemma_candidate_registry_gate_v0"
STATUS = "cone01_r10_negative_lemma_candidate_registry_ready_no_checked_lemma"
MODEL_STATUS = "r1_line1381_negative_lemma_candidates_registered_but_unchecked"
VERSION = "0.1"
TARGET_ID = "T-B1-004dl/T-B7-012u"
REGISTRY_ID = "B1-B7-cone01-R10-R1-negative-lemma-candidate-registry"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def requirement(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def candidate(
    candidate_id: str,
    title: str,
    pressure_family: str,
    covered_domain: str,
    source_hashes: dict[str, str | None],
    falsification_tests: list[str],
    acceptance_conditions: list[str],
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "title": title,
        "pressure_family": pressure_family,
        "covered_domain": covered_domain,
        "source_hashes": source_hashes,
        "falsification_tests": falsification_tests,
        "acceptance_conditions": acceptance_conditions,
        "non_claims": [
            "not_a_checked_negative_lemma",
            "not_an_impossibility_theorem",
            "not_a_resource_saving",
            "not_a_b7_credit",
            "not_a_reroute_authorization",
        ],
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    r8 = load_json(args.r8_preflight)
    r9 = load_json(args.r9_pressure)
    r8s = r8["summary"]
    r9s = r9["summary"]

    source_hashes = {
        "r8_preflight": file_hash(args.r8_preflight),
        "r9_pressure": file_hash(args.r9_pressure),
        "r9_markdown": file_hash(args.r9_markdown),
    }

    candidates = [
        candidate(
            "NL-C01",
            "Route-contract rejection lemma candidate",
            "contract_preflight",
            (
                "The current R1 contract routes A and B under the R7 submission contract and "
                "R8 preflight predicates."
            ),
            {
                "r8_preflight": source_hashes["r8_preflight"],
                "r7_contract_hash": r8s.get("r7_contract_hash"),
                "r8_preflight_hash": r8s.get("preflight_hash"),
            },
            [
                "Submit a target R1 artifact that passes Route A.",
                "Submit a target R1 artifact that passes Route B.",
                "Show an R8 predicate mismatch against the R7 contract.",
            ],
            [
                "Bind the R7 contract hash and R8 preflight hash.",
                "List each failed Route A/B predicate and prove the predicate cannot be cleared inside the covered domain.",
                "State explicitly that the lemma is conditional on the current R7/R8 contract language.",
            ],
        ),
        candidate(
            "NL-C02",
            "Leave-out parameter elimination lemma candidate",
            "parameter_removal",
            (
                "All nonempty leave-out subsets of the five current line1381 off-grid parameters "
                "covered by R9 leave-out pressure."
            ),
            {
                "r9_pressure": source_hashes["r9_pressure"],
                "r9_pressure_hash": r9s.get("pressure_hash"),
            },
            [
                "Find any leave-out subset with exact pass.",
                "Show a missing nonempty subset among the 31 leave-out rows.",
                "Show a tolerance or grid mismatch that invalidates a recorded exact failure.",
            ],
            [
                "Bind all 31 leave-out rows.",
                "Bind the five-parameter off-grid domain.",
                "Prove exact-pass count remains zero under the declared tolerance and grid.",
            ],
        ),
        candidate(
            "NL-C03",
            "Bounded context absorption lemma candidate",
            "context_absorption",
            (
                "Signed-grid context absorption attempts for widths 1 through 5 over the current "
                "line1381 parameter domain."
            ),
            {
                "r9_pressure": source_hashes["r9_pressure"],
                "r9_pressure_hash": r9s.get("pressure_hash"),
            },
            [
                "Produce one exact absorption at width <= 5.",
                "Expose an untested signed-combination family inside the stated width bound.",
                "Lower the best context-grid error to zero under the same arithmetic model.",
            ],
            [
                "Bind context widths [1, 2, 3, 4, 5].",
                "Bind 173,761,280 width-5 virtual tests.",
                "Prove total exact absorption count remains zero inside the covered arithmetic model.",
            ],
        ),
        candidate(
            "NL-C04",
            "Commutation-corridor replay lemma candidate",
            "commutation_corridor",
            "Best-context replay candidates under the current commutation-corridor references.",
            {
                "r9_pressure": source_hashes["r9_pressure"],
                "r9_pressure_hash": r9s.get("pressure_hash"),
            },
            [
                "Produce one candidate accepted by all corridor references.",
                "Show a blocked corridor reference is unsound or outside the covered domain.",
                "Replay a candidate that preserves the required references with nonzero accepted count.",
            ],
            [
                "Bind the commutation-corridor source row.",
                "Bind accepted replay candidate count 0.",
                "State the exact corridor reference family under coverage.",
            ],
        ),
        candidate(
            "NL-C05",
            "Physical Route-B deficit lemma candidate",
            "physical_pricing",
            "Current physical-pricing ledger used by R8/R9 for Route B.",
            {
                "r9_pressure": source_hashes["r9_pressure"],
                "r9_pressure_hash": r9s.get("pressure_hash"),
            },
            [
                "Reduce physical cost-minus-credit to <= 0 under the same ledger.",
                "Show the selected CNOT credit or placeholder proxy-T pressure is priced incorrectly.",
                "Submit a same-ledger artifact that clears Route B.",
            ],
            [
                "Bind physical cost-minus-credit 365.",
                "Bind Route B failure under the same pricing ledger.",
                "State that the lemma is ledger-conditional and does not rule out new physical evidence.",
            ],
        ),
    ]

    pr_packets = [
        {
            "packet_id": "R10-PR01",
            "title": "Formalize the covered R1 domain",
            "owner_hint": "Theory Agent",
            "required_output": "machine-readable domain manifest plus human-readable scope note",
        },
        {
            "packet_id": "R10-PR02",
            "title": "Independently replay the R9 source hashes",
            "owner_hint": "Audit Agent",
            "required_output": "replay transcript binding R8/R9 hashes and source paths",
        },
        {
            "packet_id": "R10-PR03",
            "title": "Write a proof skeleton for one candidate",
            "owner_hint": "Formal Methods Agent",
            "required_output": "checked or checkable proof skeleton with open obligations",
        },
        {
            "packet_id": "R10-PR04",
            "title": "Attack the candidates with a route-clearing artifact",
            "owner_hint": "Compiler Agent",
            "required_output": "R1 artifact attempting to clear Route A or Route B",
        },
        {
            "packet_id": "R10-PR05",
            "title": "Build the negative-lemma acceptance packet",
            "owner_hint": "Maintainer Agent",
            "required_output": "acceptance packet separating candidate, checked lemma, and reroute decision",
        },
    ]

    registry = {
        "registry_id": REGISTRY_ID,
        "source_target_id": TARGET_ID,
        "source_r8_preflight": str(args.r8_preflight),
        "source_r9_pressure": str(args.r9_pressure),
        "source_hashes": source_hashes,
        "r8_preflight_hash": r8s.get("preflight_hash"),
        "r9_pressure_hash": r9s.get("pressure_hash"),
        "r9_status": r9.get("status"),
        "r9_reroute_allowed": r9s.get("reroute_allowed"),
        "candidate_negative_lemmas": candidates,
        "external_pr_packets": pr_packets,
        "decision": {
            "checked_negative_lemma_present": False,
            "reroute_allowed": False,
            "r5_reroute_authorized": False,
            "why": (
                "R10 makes the negative-lemma work concrete and falsifiable, but a candidate "
                "registry is still not a checked lemma."
            ),
        },
    }
    registry["registry_hash"] = stable_hash(registry)

    falsification_test_count = sum(len(row["falsification_tests"]) for row in candidates)
    acceptance_condition_count = sum(len(row["acceptance_conditions"]) for row in candidates)
    source_hash_count = sum(1 for value in source_hashes.values() if value)

    requirements = [
        requirement(
            "C1",
            "R9 pressure is validation-clean and still blocks reroute",
            r9.get("method") == "b1_b7_cone01_r9_r1_reroute_pressure_gate_v0"
            and r9s.get("requirements_failed") == 0
            and r9s.get("validation_error_count") == 0
            and r9s.get("reroute_allowed") is False,
            {
                "r9_method": r9.get("method"),
                "r9_requirements_failed": r9s.get("requirements_failed"),
                "r9_validation_error_count": r9s.get("validation_error_count"),
                "r9_reroute_allowed": r9s.get("reroute_allowed"),
            },
        ),
        requirement(
            "C2",
            "Registry contains five candidate negative lemmas",
            len(candidates) == 5,
            {"candidate_count": len(candidates)},
        ),
        requirement(
            "C3",
            "Candidates cover contract, parameter, context, commutation, and physical pressure families",
            {row["pressure_family"] for row in candidates}
            == {
                "contract_preflight",
                "parameter_removal",
                "context_absorption",
                "commutation_corridor",
                "physical_pricing",
            },
            {"pressure_families": sorted({row["pressure_family"] for row in candidates})},
        ),
        requirement(
            "C4",
            "Every candidate is falsifiable",
            all(row["falsification_tests"] for row in candidates) and falsification_test_count >= 15,
            {"falsification_test_count": falsification_test_count},
        ),
        requirement(
            "C5",
            "Every candidate has acceptance conditions",
            all(row["acceptance_conditions"] for row in candidates)
            and acceptance_condition_count >= 15,
            {"acceptance_condition_count": acceptance_condition_count},
        ),
        requirement(
            "C6",
            "Registry binds R8, R9, and R9 report source hashes",
            source_hash_count == 3
            and bool(r8s.get("preflight_hash"))
            and bool(r9s.get("pressure_hash")),
            {"source_hash_count": source_hash_count, "source_hashes": source_hashes},
        ),
        requirement(
            "C7",
            "External PR packets separate theory, audit, compiler, formal, and maintainer work",
            len(pr_packets) == 5
            and {row["owner_hint"] for row in pr_packets}
            == {
                "Theory Agent",
                "Audit Agent",
                "Formal Methods Agent",
                "Compiler Agent",
                "Maintainer Agent",
            },
            {"pr_packet_count": len(pr_packets)},
        ),
        requirement(
            "C8",
            "Registry explicitly refuses to upgrade candidates into checked lemmas",
            registry["decision"]["checked_negative_lemma_present"] is False
            and registry["decision"]["reroute_allowed"] is False,
            registry["decision"],
        ),
        requirement(
            "C9",
            "Registry preserves zero resource and B7 credit claims",
            True,
            {
                "accepted_route_count": 0,
                "accepted_occurrence_removal": 0,
                "accepted_proxy_t_reduction": 0,
                "b7_credit_delta": 0,
                "b7_space_time_volume_credit": 0,
                "resource_saving_claimed": False,
                "b7_ledger_improvement_claimed": False,
            },
        ),
        requirement(
            "C10",
            "Next gate is a checked lemma or an R1 Route A/B clearing artifact",
            True,
            {
                "next_gate": (
                    "Submit a checked negative lemma for one or more R10 candidates, or falsify "
                    "the registry by submitting an R1 artifact that clears R8 Route A or Route B."
                )
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids:
        validation_errors.append(f"unexpected R10 registry failures: {failed_ids}")

    summary = {
        "registry_id": REGISTRY_ID,
        "registry_hash": registry["registry_hash"],
        "r8_preflight_hash": r8s.get("preflight_hash"),
        "r9_pressure_hash": r9s.get("pressure_hash"),
        "lemma_candidate_count": len(candidates),
        "falsification_test_count": falsification_test_count,
        "acceptance_condition_count": acceptance_condition_count,
        "external_pr_packet_count": len(pr_packets),
        "checked_negative_lemma_present": False,
        "reroute_allowed": False,
        "r5_reroute_authorized": False,
        "accepted_route_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "b7_credit_delta": 0,
        "b7_space_time_volume_credit": 0,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "requirement_count": len(requirements),
        "requirements_passed": passed,
        "requirements_failed": len(requirements) - passed,
        "failed_requirement_ids": failed_ids,
        "validation_error_count": len(validation_errors),
    }

    return {
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "source_target_id": TARGET_ID,
        "title": "B1/B7 Cone01 R10 R1 Negative-Lemma Candidate Registry Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "summary": summary,
        "negative_lemma_candidate_registry": registry,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "R10 turns R9 reroute pressure into five falsifiable negative-lemma candidates and "
                "five external PR packets."
            ),
            "what_is_not_supported": (
                "No candidate is a checked negative lemma. No R5 reroute, R1 solution, occurrence "
                "removal, proxy-T reduction, B7 credit, resource saving, or impossibility theorem is "
                "supported."
            ),
            "next_gate": (
                "Submit a checked negative lemma artifact for at least one candidate, or falsify the "
                "registry by clearing R8 Route A or Route B."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    registry = payload["negative_lemma_candidate_registry"]
    lines = [
        f"# {payload['title']}",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Registry: `{s['registry_id']}`",
        f"- Registry hash: `{s['registry_hash']}`",
        f"- R9 pressure hash: `{s['r9_pressure_hash']}`",
        "",
        "## Result",
        "",
        (
            f"The R10 registry gate passes {s['requirements_passed']}/{s['requirement_count']} "
            "requirements. It converts R9 pressure into falsifiable negative-lemma candidates, but "
            "does not claim that any candidate has been checked."
        ),
        "",
        "## Candidate Negative Lemmas",
        "",
    ]
    for row in registry["candidate_negative_lemmas"]:
        lines.extend(
            [
                f"### {row['candidate_id']} - {row['title']}",
                "",
                f"- Pressure family: `{row['pressure_family']}`",
                f"- Covered domain: {row['covered_domain']}",
                f"- Falsification tests: `{len(row['falsification_tests'])}`",
                f"- Acceptance conditions: `{len(row['acceptance_conditions'])}`",
                "",
            ]
        )
    lines.extend(
        [
            "## External PR Packets",
            "",
        ]
    )
    for row in registry["external_pr_packets"]:
        lines.append(
            f"- `{row['packet_id']}` {row['title']} ({row['owner_hint']}): {row['required_output']}"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Checked negative lemma present: `{s['checked_negative_lemma_present']}`",
            f"- Reroute allowed: `{s['reroute_allowed']}`",
            f"- R5 reroute authorized: `{s['r5_reroute_authorized']}`",
            "",
            "## Requirement Results",
            "",
        ]
    )
    for row in payload["requirements"]:
        marker = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- `{row['requirement_id']}` {marker}: {row['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            "",
            "This registry gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a checked impossibility theorem, an R5 reroute, or a solved B1/B7 problem.",
            "",
            "## Validation",
            "",
            f"- validation_error_count: `{s['validation_error_count']}`",
        ]
    )
    for error in payload["validation_errors"]:
        lines.append(f"- {error}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--r8-preflight",
        type=Path,
        default=Path("results/B1_B7_cone01_R8_r1_contract_preflight_gate_v0.json"),
    )
    parser.add_argument(
        "--r9-pressure",
        type=Path,
        default=Path("results/B1_B7_cone01_R9_r1_reroute_pressure_gate_v0.json"),
    )
    parser.add_argument(
        "--r9-markdown",
        type=Path,
        default=Path("research/B1_B7_cone01_R9_r1_reroute_pressure_gate.md"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_R10_r1_negative_lemma_candidate_registry_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_R10_r1_negative_lemma_candidate_registry_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-06")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "registry_hash": payload["summary"]["registry_hash"],
                "lemma_candidate_count": payload["summary"]["lemma_candidate_count"],
                "falsification_test_count": payload["summary"]["falsification_test_count"],
                "external_pr_packet_count": payload["summary"]["external_pr_packet_count"],
                "reroute_allowed": payload["summary"]["reroute_allowed"],
                "requirements_passed": payload["summary"]["requirements_passed"],
                "requirements_failed": payload["summary"]["requirements_failed"],
                "validation_error_count": payload["summary"]["validation_error_count"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if payload["validation_errors"]:
        raise SystemExit("B1/B7 R10 negative-lemma registry gate validation failed")


if __name__ == "__main__":
    main()
