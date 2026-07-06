#!/usr/bin/env python3
"""T-B1-004dj/T-B7-012s: R8 R1 contract preflight gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r8_r1_contract_preflight_gate_v0"
STATUS = "cone01_r8_r1_contract_preflight_rejects_existing_evidence"
MODEL_STATUS = "existing_line1381_evidence_fails_both_r7_acceptance_routes"
VERSION = "0.1"
TARGET_ID = "T-B1-004dj/T-B7-012s"
PREFLIGHT_ID = "B1-B7-cone01-R8-R1-contract-preflight"
EXPECTED_R7_METHOD = "b1_b7_cone01_r7_r1_submission_contract_gate_v0"
EXPECTED_R1_PACKET_ID = "B1-B7-cone01-R1-line1381-resolution"


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


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    r7 = load_json(args.r7_contract_gate)
    contract = load_json(args.r7_contract_artifact)
    five = load_json(args.five_parameter_repair)
    local = load_json(args.local_u3_pricing)
    physical = load_json(args.physical_pricing)
    r7_summary = r7["summary"]
    five_summary = five["summary"]
    local_summary = local["summary"]
    physical_summary = physical["summary"]

    source_hashes = {
        "r7_contract_gate_sha256": file_hash(args.r7_contract_gate),
        "r7_contract_artifact_sha256": file_hash(args.r7_contract_artifact),
        "five_parameter_repair_sha256": file_hash(args.five_parameter_repair),
        "local_u3_pricing_sha256": file_hash(args.local_u3_pricing),
        "physical_pricing_sha256": file_hash(args.physical_pricing),
    }

    route_a_checks = [
        {
            "predicate": "source_r6_inventory_hash matches contract",
            "passed": contract.get("source_r6_inventory_hash") == r7_summary.get("r6_inventory_hash"),
            "observed": contract.get("source_r6_inventory_hash"),
            "required": r7_summary.get("r6_inventory_hash"),
        },
        {
            "predicate": "line1381_off_grid_parameter_count_before == 5",
            "passed": r7_summary.get("line1381_off_grid_parameter_count") == 5,
            "observed": r7_summary.get("line1381_off_grid_parameter_count"),
            "required": 5,
        },
        {
            "predicate": "line1381_off_grid_parameter_count_after == 0",
            "passed": local_summary.get("line1381_replacement_off_pi_over_four_parameter_count") == 0,
            "observed": local_summary.get("line1381_replacement_off_pi_over_four_parameter_count"),
            "required": 0,
        },
        {
            "predicate": "five-parameter repair is packet-exact",
            "passed": five_summary.get("five_parameter_exact_packet_count") == 1,
            "observed": five_summary.get("five_parameter_exact_packet_count"),
            "required": 1,
        },
        {
            "predicate": "full replay or symbolic equivalence for the submitted R1 artifact is present",
            "passed": False,
            "observed": "no submitted R1 artifact replay/symbolic-equivalence hash",
            "required": "full_replay_or_symbolic_equivalence_hash",
        },
        {
            "predicate": "resource and no-double-counting ledgers for the submitted R1 artifact are present",
            "passed": False,
            "observed": "no submitted R1 resource_delta_ledger_hash/no_double_counting_ledger_hash",
            "required": "both ledger hashes",
        },
    ]
    route_b_checks = [
        {
            "predicate": "source_r6_inventory_hash matches contract",
            "passed": contract.get("source_r6_inventory_hash") == r7_summary.get("r6_inventory_hash"),
            "observed": contract.get("source_r6_inventory_hash"),
            "required": r7_summary.get("r6_inventory_hash"),
        },
        {
            "predicate": "physical_pricing_replay.cost_minus_credit <= 0",
            "passed": physical_summary.get("physical_synthesis_cost_minus_selected_cnot_credit", 1) <= 0,
            "observed": physical_summary.get("physical_synthesis_cost_minus_selected_cnot_credit"),
            "required": "<= 0",
        },
        {
            "predicate": "physical pricing replay is accepted",
            "passed": physical_summary.get("physical_synthesis_pricing_accepted") is True,
            "observed": physical_summary.get("physical_synthesis_pricing_accepted"),
            "required": True,
        },
        {
            "predicate": "submitted R1 pricing and ledger hashes are present",
            "passed": False,
            "observed": "no submitted R1 physical_pricing_replay_hash/resource_delta_ledger_hash/no_double_counting_ledger_hash",
            "required": "pricing and ledger hashes",
        },
        {
            "predicate": "claim boundary forbids B7 credit before resource-escape acceptance",
            "passed": contract["forbidden_claims_before_acceptance"].get("b7_space_time_volume_credit") == 0,
            "observed": contract["forbidden_claims_before_acceptance"],
            "required": "zero credit until accepted",
        },
    ]

    route_a_passed = all(row["passed"] for row in route_a_checks)
    route_b_passed = all(row["passed"] for row in route_b_checks)
    cost_minus_credit = physical_summary.get("physical_synthesis_cost_minus_selected_cnot_credit")
    proxy_pressure = local_summary.get("line1381_unpriced_proxy_t_pressure")
    preflight_packet = {
        "preflight_id": PREFLIGHT_ID,
        "source_target_id": TARGET_ID,
        "r7_contract_hash": r7_summary.get("contract_hash"),
        "r7_contract_artifact_hash": contract.get("contract_hash"),
        "target_packet_id": EXPECTED_R1_PACKET_ID,
        "candidate_package": "existing_r6_evidence_without_submitted_r1_artifact",
        "source_hashes": source_hashes,
        "route_a": {
            "route_id": "A",
            "name": "parameter_elimination_with_replay_or_symbolic_equivalence",
            "passed": route_a_passed,
            "checks": route_a_checks,
            "blocking_reason": (
                "Existing evidence has a packet-exact five-parameter repair, but the accepted route "
                "requires line1381_off_grid_parameter_count_after == 0 and a submitted artifact "
                "with replay/symbolic-equivalence plus ledgers."
            ),
        },
        "route_b": {
            "route_id": "B",
            "name": "physical_pricing_replay_beats_boundary",
            "passed": route_b_passed,
            "checks": route_b_checks,
            "blocking_reason": (
                f"Existing physical pricing has cost-minus-credit {cost_minus_credit}, "
                "so it does not beat the <= 0 boundary."
            ),
        },
        "quantified_gap_to_acceptance": {
            "route_a_remaining_off_grid_parameters_to_eliminate": local_summary.get(
                "line1381_replacement_off_pi_over_four_parameter_count"
            ),
            "route_a_required_full_replay_or_symbolic_hash_count": 1,
            "route_a_required_ledger_hash_count": 2,
            "route_b_cost_minus_credit_deficit_to_zero": max(0, cost_minus_credit or 0),
            "route_b_current_unpriced_proxy_t_pressure": proxy_pressure,
            "accepted_occurrence_removal": 0,
            "accepted_proxy_t_reduction": 0,
            "b7_credit_delta": 0,
        },
        "next_atomic_work_order": [
            "Produce a submitted R1 artifact that reduces line1381 off-grid parameter count from 5 to 0, then attach full replay or symbolic equivalence and ledgers.",
            "Or produce a physical-pricing replay that improves cost-minus-credit by at least 365 while preserving no-double-counting and zero-credit claim boundaries before acceptance.",
            "Or submit a checked negative lemma proving R1 should be abandoned and R5 rerun against R2/R3/R4.",
        ],
    }
    preflight_packet["preflight_hash"] = stable_hash(preflight_packet)

    requirements = [
        requirement(
            "P1",
            "R7 contract gate is current and passed",
            r7.get("method") == EXPECTED_R7_METHOD
            and r7_summary.get("requirements_failed") == 0
            and r7_summary.get("contract_hash") == contract.get("contract_hash"),
            {
                "r7_method": r7.get("method"),
                "r7_requirements_failed": r7_summary.get("requirements_failed"),
                "r7_contract_hash": r7_summary.get("contract_hash"),
                "contract_artifact_hash": contract.get("contract_hash"),
            },
        ),
        requirement(
            "P2",
            "Existing evidence source files are hash-readable",
            all(source_hashes.values()),
            source_hashes,
        ),
        requirement(
            "P3",
            "Route A preflight is evaluated against the five-parameter exact repair evidence",
            five.get("method") == "b1_b7_cone01_five_parameter_line1381_exact_repair_gate_v0"
            and five_summary.get("five_parameter_exact_packet_count") == 1,
            {
                "method": five.get("method"),
                "five_parameter_exact_packet_count": five_summary.get(
                    "five_parameter_exact_packet_count"
                ),
                "five_parameter_exact_repair_off_pi_over_four_parameter_count": five_summary.get(
                    "five_parameter_exact_repair_off_pi_over_four_parameter_count"
                ),
            },
        ),
        requirement(
            "P4",
            "Route A remains rejected because five off-grid line1381 parameters remain",
            route_a_passed is False
            and local_summary.get("line1381_replacement_off_pi_over_four_parameter_count") == 5,
            {
                "route_a_passed": route_a_passed,
                "line1381_replacement_off_pi_over_four_parameter_count": local_summary.get(
                    "line1381_replacement_off_pi_over_four_parameter_count"
                ),
            },
        ),
        requirement(
            "P5",
            "Route B preflight is evaluated against honest physical-pricing evidence",
            physical.get("method") == "b1_b7_cone01_physical_synthesis_pricing_gate_v0"
            and physical_summary.get("physical_synthesis_cost_minus_selected_cnot_credit") == 365,
            {
                "method": physical.get("method"),
                "physical_synthesis_cost_minus_selected_cnot_credit": cost_minus_credit,
                "physical_synthesis_pricing_accepted": physical_summary.get(
                    "physical_synthesis_pricing_accepted"
                ),
            },
        ),
        requirement(
            "P6",
            "Route B remains rejected because cost-minus-credit is positive",
            route_b_passed is False and (cost_minus_credit or 0) > 0,
            {"route_b_passed": route_b_passed, "cost_minus_credit": cost_minus_credit},
        ),
        requirement(
            "P7",
            "No R1 accepted-route, resource, or B7 credit is created by preflight",
            route_a_passed is False
            and route_b_passed is False
            and local_summary.get("accepted_occurrence_removal") == 0
            and physical_summary.get("accepted_proxy_t_reduction") == 0,
            {
                "route_a_passed": route_a_passed,
                "route_b_passed": route_b_passed,
                "accepted_occurrence_removal": local_summary.get("accepted_occurrence_removal"),
                "accepted_proxy_t_reduction": physical_summary.get("accepted_proxy_t_reduction"),
            },
        ),
        requirement(
            "P8",
            "Preflight quantifies the next technical gap",
            preflight_packet["quantified_gap_to_acceptance"][
                "route_a_remaining_off_grid_parameters_to_eliminate"
            ]
            == 5
            and preflight_packet["quantified_gap_to_acceptance"][
                "route_b_cost_minus_credit_deficit_to_zero"
            ]
            == 365,
            preflight_packet["quantified_gap_to_acceptance"],
        ),
        requirement(
            "P9",
            "Preflight remains a rejection, not a negative impossibility lemma",
            preflight_packet["route_a"]["passed"] is False
            and preflight_packet["route_b"]["passed"] is False,
            {
                "negative_lemma_claimed": False,
                "route_a_passed": preflight_packet["route_a"]["passed"],
                "route_b_passed": preflight_packet["route_b"]["passed"],
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids:
        validation_errors.append(f"unexpected R8 preflight failures: {failed_ids}")

    summary = {
        "preflight_id": PREFLIGHT_ID,
        "preflight_hash": preflight_packet["preflight_hash"],
        "r7_contract_hash": r7_summary.get("contract_hash"),
        "r7_contract_artifact_hash": contract.get("contract_hash"),
        "route_a_passed": route_a_passed,
        "route_b_passed": route_b_passed,
        "accepted_route_count": int(route_a_passed) + int(route_b_passed),
        "route_a_failed_predicate_count": sum(1 for row in route_a_checks if not row["passed"]),
        "route_b_failed_predicate_count": sum(1 for row in route_b_checks if not row["passed"]),
        "line1381_packet_exact_repair_exists": five_summary.get(
            "five_parameter_exact_packet_count"
        )
        == 1,
        "line1381_remaining_off_grid_parameter_count": local_summary.get(
            "line1381_replacement_off_pi_over_four_parameter_count"
        ),
        "line1381_unpriced_proxy_t_pressure": proxy_pressure,
        "physical_cost_minus_credit": cost_minus_credit,
        "cost_minus_credit_deficit_to_zero": max(0, cost_minus_credit or 0),
        "target_submission_exists": r7_summary.get("target_submission_exists"),
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "b7_credit_delta": 0,
        "b7_space_time_volume_credit": 0,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "negative_lemma_claimed": False,
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
        "title": "B1/B7 Cone01 R8 R1 Contract Preflight Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_r7_contract_gate": str(args.r7_contract_gate),
        "source_r7_contract_artifact": str(args.r7_contract_artifact),
        "source_five_parameter_repair": str(args.five_parameter_repair),
        "source_local_u3_pricing": str(args.local_u3_pricing),
        "source_physical_pricing": str(args.physical_pricing),
        "summary": summary,
        "r1_contract_preflight_packet": preflight_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "R8 preflights existing line1381 evidence against the R7 contract and rejects both "
                "acceptance routes with quantified blockers."
            ),
            "what_is_not_supported": (
                "No submitted R1 artifact, accepted R1 route, line1381 parameter elimination, "
                "physical-pricing win, occurrence removal, proxy-T reduction, B7 credit, resource saving, "
                "or negative impossibility lemma is supported."
            ),
            "next_gate": (
                "Either eliminate the remaining five line1381 off-grid parameters with submitted replay/"
                "symbolic-equivalence and ledgers, improve physical cost-minus-credit by at least 365, "
                "or submit a checked negative lemma to reroute R5."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    packet = payload["r1_contract_preflight_packet"]
    lines = [
        f"# {payload['title']}",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Preflight: `{s['preflight_id']}`",
        f"- Preflight hash: `{s['preflight_hash']}`",
        f"- R7 contract hash: `{s['r7_contract_hash']}`",
        "",
        "## Result",
        "",
        (
            f"The R8 preflight gate passes {s['requirements_passed']}/{s['requirement_count']} "
            "requirements by rejecting the existing evidence package against both R7 acceptance routes. "
            "This is useful negative pressure, not a solution claim."
        ),
        "",
        "## Route A Preflight",
        "",
        f"- Passed: `{s['route_a_passed']}`",
        f"- Failed predicates: `{s['route_a_failed_predicate_count']}`",
    ]
    for row in packet["route_a"]["checks"]:
        marker = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- `{marker}` {row['predicate']} (observed `{row['observed']}`, required `{row['required']}`)")
    lines.extend(
        [
            "",
            "## Route B Preflight",
            "",
            f"- Passed: `{s['route_b_passed']}`",
            f"- Failed predicates: `{s['route_b_failed_predicate_count']}`",
        ]
    )
    for row in packet["route_b"]["checks"]:
        marker = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- `{marker}` {row['predicate']} (observed `{row['observed']}`, required `{row['required']}`)")
    lines.extend(
        [
            "",
            "## Quantified Gap",
            "",
            f"- Remaining line1381 off-grid parameters to eliminate: `{s['line1381_remaining_off_grid_parameter_count']}`",
            f"- Current line1381 unpriced proxy-T pressure: `{s['line1381_unpriced_proxy_t_pressure']}`",
            f"- Physical cost-minus-credit: `{s['physical_cost_minus_credit']}`",
            f"- Improvement needed to reach cost-minus-credit <= 0: `{s['cost_minus_credit_deficit_to_zero']}`",
            f"- Accepted route count / occurrence removal / proxy-T reduction / B7 credit: `{s['accepted_route_count']}` / `{s['accepted_occurrence_removal']}` / `{s['accepted_proxy_t_reduction']}` / `{s['b7_credit_delta']}`",
            "",
            "## Next Atomic Work Order",
            "",
        ]
    )
    for item in packet["next_atomic_work_order"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Requirement Results", ""])
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
            "This preflight gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a negative impossibility theorem, or a solved B1/B7 problem.",
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
        "--r7-contract-gate",
        type=Path,
        default=Path("results/B1_B7_cone01_R7_r1_submission_contract_gate_v0.json"),
    )
    parser.add_argument(
        "--r7-contract-artifact",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_r1_line1381_resolution_submissions/"
            "B1-B7-cone01-R1-line1381-resolution.contract.json"
        ),
    )
    parser.add_argument(
        "--five-parameter-repair",
        type=Path,
        default=Path("results/B1_B7_cone01_five_parameter_line1381_exact_repair_gate_v0.json"),
    )
    parser.add_argument(
        "--local-u3-pricing",
        type=Path,
        default=Path("results/B1_B7_cone01_line1381_local_u3_pricing_gate_v0.json"),
    )
    parser.add_argument(
        "--physical-pricing",
        type=Path,
        default=Path("results/B1_B7_cone01_physical_synthesis_pricing_gate_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_R8_r1_contract_preflight_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_R8_r1_contract_preflight_gate.md"),
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
                "preflight_hash": payload["summary"]["preflight_hash"],
                "route_a_passed": payload["summary"]["route_a_passed"],
                "route_b_passed": payload["summary"]["route_b_passed"],
                "line1381_remaining_off_grid_parameter_count": payload["summary"][
                    "line1381_remaining_off_grid_parameter_count"
                ],
                "physical_cost_minus_credit": payload["summary"]["physical_cost_minus_credit"],
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
        raise SystemExit("B1/B7 R8 R1 contract preflight gate validation failed")


if __name__ == "__main__":
    main()
