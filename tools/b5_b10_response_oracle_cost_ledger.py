#!/usr/bin/env python3
"""T-B5-006f/T-B10-014d: W3 same-access response-oracle cost ledger."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b5_b10_response_oracle_cost_ledger_v0"
STATUS = "same_access_response_oracle_cost_ledger_failed_no_oracle"
MODEL_STATUS = "w3_response_oracle_ledger_executed_oracle_not_constructed"
VERSION = "0.1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        text = json.dumps(payload, indent=2, sort_keys=True)
    else:
        text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def requirement(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def row_key(row: dict[str, Any]) -> str:
    return f"{int(row['sites'])}|{float(row['u_over_t']):.6g}"


def build_rows(sampler: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in sampler["rows"]:
        seeded_target = row["targets"]["match_exact_state_seeded_mps_pressure"]
        als_target = row["targets"]["match_one_site_variational_mps_als"]
        non_oracle_target = row["targets"]["match_non_oracle_embedding"]
        rows.append(
            {
                "row_id": row_key(row),
                "sites": int(row["sites"]),
                "u_over_t": float(row["u_over_t"]),
                "eta": float(row["eta"]),
                "exact_response": float(row["exact_response"]),
                "exact_d5_matvec_equivalent_ops": int(row["exact_d5_matvec_equivalent_ops"]),
                "shots_to_match_non_oracle_embedding": int(non_oracle_target["total_measurement_shots"]),
                "shots_to_match_variational_mps_als": int(als_target["total_measurement_shots"]),
                "shots_to_match_seeded_mps_pressure": int(seeded_target["total_measurement_shots"]),
                "seeded_target_prep_2q_floor": int(
                    seeded_target["optimistic_state_preparation_two_qubit_gate_floor"]
                ),
                "sampler_beats_seeded_mps_pressure_by_shots": bool(
                    row["sampler_beats_seeded_mps_pressure_by_shots"]
                ),
                "same_access_positive_route_ready": bool(row["same_access_positive_route_ready"]),
            }
        )
    return rows


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    row_contract = load_json(args.row_contract)
    sampler = load_json(args.sampler_stress)
    bridge = load_json(args.same_access_bridge)
    production_contract = load_json(args.production_contract)
    seeded_replacement = load_json(args.seeded_replacement)

    row_contract_summary = row_contract["summary"]
    sampler_summary = sampler["summary"]
    bridge_summary = bridge["summary"]
    production_summary = production_contract["summary"]
    seeded_replacement_summary = seeded_replacement["summary"]
    sampling_model = sampler.get("sampling_model", {})
    rows = build_rows(sampler)

    requirements = [
        requirement(
            "O1",
            "W4 row contract is preserved before any oracle comparison",
            row_contract_summary.get("row_contract_count") == 9
            and row_contract_summary.get("source_checks_failed") == 0,
            {
                "row_contract_hash": row_contract_summary.get("row_contract_hash"),
                "row_contract_count": row_contract_summary.get("row_contract_count"),
                "source_checks_failed": row_contract_summary.get("source_checks_failed"),
            },
        ),
        requirement(
            "O2",
            "Optimistic measurement-confidence ledger exists on all nine rows",
            sampler_summary.get("instance_count") == 9
            and sampler_summary.get("confidence_z") is not None
            and sampler_summary.get("density_variance_upper_bound") is not None,
            {
                "instance_count": sampler_summary.get("instance_count"),
                "confidence_z": sampler_summary.get("confidence_z"),
                "density_variance_upper_bound": sampler_summary.get(
                    "density_variance_upper_bound"
                ),
            },
        ),
        requirement(
            "O3",
            "State-preparation algorithm and cost ledger are instantiated",
            False,
            {
                "state_preparation_floor_present": bool(
                    sampling_model.get("state_preparation_floor_per_circuit_2q_gates")
                ),
                "state_preparation_algorithm_instantiated": False,
                "reason": "sampler stress contains only an optimistic per-circuit floor",
            },
        ),
        requirement(
            "O4",
            "Mixing or response-query cost is included",
            sampling_model.get("mixing_cost_included") is True,
            {
                "mixing_cost_included": sampling_model.get("mixing_cost_included"),
                "response_estimator": sampling_model.get("response_estimator"),
            },
        ),
        requirement(
            "O5",
            "Readout, noise, or backend calibration costs are included",
            sampling_model.get("readout_error_included") is True,
            {
                "readout_error_included": sampling_model.get("readout_error_included"),
                "real_backend_or_hardware_rows": 0,
            },
        ),
        requirement(
            "O6",
            "Optimizer-loop or adaptive-query amplification cost is bounded",
            False,
            {
                "optimizer_loop_cost_included": False,
                "reason": "sampler stress prices fixed finite differences, not an optimizer loop",
            },
        ),
        requirement(
            "O7",
            "Oracle beats explicit D5 and seeded-pressure denominator ladder",
            sampler_summary.get("rows_where_sampler_shots_beat_explicit_d5_matvec_ops_for_seeded_target")
            == 9
            and seeded_replacement_summary.get("seeded_pressure_replaced") is True,
            {
                "rows_beating_explicit_d5_matvec_for_seeded_target": sampler_summary.get(
                    "rows_where_sampler_shots_beat_explicit_d5_matvec_ops_for_seeded_target"
                ),
                "seeded_pressure_replaced": seeded_replacement_summary.get(
                    "seeded_pressure_replaced"
                ),
                "max_shots_to_match_seeded_pressure": sampler_summary.get(
                    "max_total_shots_to_match_seeded_mps_pressure"
                ),
                "max_exact_d5_matvec_equivalent_ops": sampler_summary.get(
                    "max_exact_d5_matvec_equivalent_ops"
                ),
            },
        ),
        requirement(
            "O8",
            "Forbidden claims remain false",
            bridge_summary.get("same_access_positive_route_ready") is False
            and production_summary.get("quantum_response_win_claimed") is False
            and sampler_summary.get("quantum_advantage_claimed") is False
            and sampler_summary.get("bqp_separation_claimed") is False,
            {
                "bridge_same_access_positive_route_ready": bridge_summary.get(
                    "same_access_positive_route_ready"
                ),
                "production_quantum_response_win_claimed": production_summary.get(
                    "quantum_response_win_claimed"
                ),
                "sampler_quantum_advantage_claimed": sampler_summary.get(
                    "quantum_advantage_claimed"
                ),
                "sampler_bqp_separation_claimed": sampler_summary.get("bqp_separation_claimed"),
            },
        ),
    ]

    passed = sum(1 for item in requirements if item["passed"])
    failed = len(requirements) - passed
    failed_ids = [item["requirement_id"] for item in requirements if not item["passed"]]

    validation_errors: list[str] = []
    if row_contract_summary.get("row_contract_count") != 9:
        validation_errors.append("row contract must contain nine B5/B10 response rows")
    if sampler_summary.get("instance_count") != 9:
        validation_errors.append("sampler stress must contain nine rows")
    if failed_ids != ["O3", "O4", "O5", "O6", "O7"]:
        validation_errors.append(f"unexpected failed oracle requirements: {failed_ids}")
    if sampler_summary.get("sampling_oracle_constructed") is not False:
        validation_errors.append("source sampler must not claim a constructed oracle")
    if bridge_summary.get("same_access_positive_route_ready") is not False:
        validation_errors.append("same-access bridge must remain negative")

    summary = {
        "row_contract_hash": row_contract_summary.get("row_contract_hash"),
        "row_contract_count": row_contract_summary.get("row_contract_count"),
        "sampler_instance_count": sampler_summary.get("instance_count"),
        "oracle_requirement_count": len(requirements),
        "oracle_requirements_passed": passed,
        "oracle_requirements_failed": failed,
        "failed_oracle_requirement_ids": failed_ids,
        "measurement_confidence_ledger_present": requirements[1]["passed"],
        "state_preparation_algorithm_instantiated": False,
        "mixing_cost_included": sampling_model.get("mixing_cost_included") is True,
        "readout_error_included": sampling_model.get("readout_error_included") is True,
        "optimizer_loop_cost_included": False,
        "rows_beating_explicit_d5_matvec_for_seeded_target": sampler_summary.get(
            "rows_where_sampler_shots_beat_explicit_d5_matvec_ops_for_seeded_target"
        ),
        "max_total_shots_to_match_seeded_mps_pressure": sampler_summary.get(
            "max_total_shots_to_match_seeded_mps_pressure"
        ),
        "median_total_shots_to_match_seeded_mps_pressure": sampler_summary.get(
            "median_total_shots_to_match_seeded_mps_pressure"
        ),
        "min_total_shots_to_match_seeded_mps_pressure": sampler_summary.get(
            "min_total_shots_to_match_seeded_mps_pressure"
        ),
        "max_optimistic_seeded_target_prep_2q_gate_floor": sampler_summary.get(
            "max_optimistic_seeded_target_prep_2q_gate_floor"
        ),
        "seeded_pressure_replaced": seeded_replacement_summary.get("seeded_pressure_replaced"),
        "w3_same_access_response_oracle_ledger_executed": True,
        "w3_response_oracle_constructed": False,
        "w3_remains_blocked_on_oracle": True,
        "remaining_positive_route_packets": ["W1"],
        "production_dmrg_available": False,
        "sampling_oracle_constructed": False,
        "same_access_response_oracle_constructed": False,
        "same_access_positive_route_ready": False,
        "b10_t1_positive_route_ready": False,
        "catalog_change_required": False,
        "production_dmrg_claimed": False,
        "quantum_response_win_claimed": False,
        "accuracy_per_resource_win_claimed": False,
        "same_access_positive_route_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "dequantization_theorem_claimed": False,
        "sampling_access_theorem_claimed": False,
        "condition_count": len(requirements),
        "conditions_satisfied": passed,
        "conditions_failed": failed,
        "validation_error_count": len(validation_errors),
    }

    payload = {
        "benchmark_id": "B5",
        "linked_benchmark_id": "B10",
        "problem_id": 38,
        "linked_problem_id": 11,
        "source_target_id": "B10-T1",
        "title": "B5/B10 same-access response-oracle cost ledger",
        "version": VERSION,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "method": METHOD,
        "created_unix": int(started),
        "source_row_contract_result": str(args.row_contract),
        "source_sampler_stress_result": str(args.sampler_stress),
        "source_same_access_bridge_result": str(args.same_access_bridge),
        "source_production_contract_result": str(args.production_contract),
        "source_seeded_replacement_result": str(args.seeded_replacement),
        "requirements": requirements,
        "rows": rows,
        "summary": summary,
        "claim_boundary": {
            "what_is_supported": (
                "W3 is executed as a same-access response-oracle cost ledger over the locked "
                "nine B5/B10 rows. The measurement-confidence floor is present, but the full "
                "oracle is not constructed."
            ),
            "what_is_not_supported": (
                "This is not a state-preparation algorithm, not a mixing/query oracle, not a "
                "hardware/noise-calibrated response oracle, not production DMRG, not a positive "
                "same-access route, not quantum advantage, and not BQP separation."
            ),
            "kill_condition": (
                "Any future W3 retry must preserve the row-contract hash, instantiate state "
                "preparation, include mixing/query and readout/noise costs, bound optimizer-loop "
                "amplification, and beat the seeded-pressure denominator ladder without hidden "
                "access advantages."
            ),
            "next_gate": "Run W1 production DMRG/MPS; W3 is closed unless a real same-access response oracle is instantiated.",
            "production_dmrg_claimed": False,
            "sampling_oracle_constructed": False,
            "same_access_response_oracle_constructed": False,
            "same_access_positive_route_claimed": False,
            "quantum_response_win_claimed": False,
            "accuracy_per_resource_win_claimed": False,
            "quantum_advantage_claimed": False,
            "bqp_separation_claimed": False,
            "dequantization_theorem_claimed": False,
            "sampling_access_theorem_claimed": False,
        },
        "validation_errors": validation_errors,
    }
    return payload


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# B5/B10 Same-Access Response-Oracle Cost Ledger v0.1",
        "",
        f"Status: **{payload['status']}**",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Row contract hash: `{summary['row_contract_hash']}`",
        f"- Row contract count: {summary['row_contract_count']}",
        f"- Oracle requirements passed/failed: {summary['oracle_requirements_passed']} / {summary['oracle_requirements_failed']}",
        f"- Failed oracle requirement IDs: {summary['failed_oracle_requirement_ids']}",
        f"- Measurement confidence ledger present: {summary['measurement_confidence_ledger_present']}",
        f"- State-preparation algorithm instantiated: {summary['state_preparation_algorithm_instantiated']}",
        f"- Mixing cost included: {summary['mixing_cost_included']}",
        f"- Readout error included: {summary['readout_error_included']}",
        f"- Optimizer-loop cost included: {summary['optimizer_loop_cost_included']}",
        f"- Rows beating explicit D5 matvec for seeded target: {summary['rows_beating_explicit_d5_matvec_for_seeded_target']}",
        f"- Min/median/max shots to match seeded MPS pressure: {summary['min_total_shots_to_match_seeded_mps_pressure']} / {summary['median_total_shots_to_match_seeded_mps_pressure']} / {summary['max_total_shots_to_match_seeded_mps_pressure']}",
        f"- Max optimistic seeded-target prep 2Q floor: {summary['max_optimistic_seeded_target_prep_2q_gate_floor']}",
        f"- W3 response oracle constructed: {summary['w3_response_oracle_constructed']}",
        f"- Remaining positive-route packets: {summary['remaining_positive_route_packets']}",
        f"- Validation errors: {payload['validation_errors']}",
        "",
        "## Oracle Requirements",
        "",
        "| ID | Requirement | Passed | Key evidence |",
        "|---|---|---:|---|",
    ]
    for item in payload["requirements"]:
        evidence = ", ".join(f"{key}={value}" for key, value in item["evidence"].items())
        lines.append(f"| {item['requirement_id']} | {item['label']} | {item['passed']} | {evidence} |")
    lines.extend(
        [
            "",
            "## Row Cost Pressure",
            "",
            "| row | D5 ops | shots to seeded pressure | seeded prep 2Q floor | beats D5 by shots |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in payload["rows"]:
        lines.append(
            f"| {row['row_id']} | {row['exact_d5_matvec_equivalent_ops']} | "
            f"{row['shots_to_match_seeded_mps_pressure']} | {row['seeded_target_prep_2q_floor']} | "
            f"{row['sampler_beats_seeded_mps_pressure_by_shots']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
        ]
    )
    for key, value in payload["claim_boundary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "W3 is now an executed negative ledger, not an unexamined opportunity. The",
            "existing sampler stress supplies a measurement-confidence floor, but the",
            "project still lacks instantiated state preparation, mixing/query costs,",
            "readout/noise costs, optimizer-loop amplification, and a denominator win.",
            "The remaining positive B5/B10 route is W1 production DMRG/MPS unless a",
            "future W3 submission supplies a real same-access response oracle.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--row-contract", type=Path, default=Path("results/B5_B10_row_contract_harness_v0.json"))
    parser.add_argument("--sampler-stress", type=Path, default=Path("results/B10_t1_b5_response_sampler_cost_stress_v0.json"))
    parser.add_argument("--same-access-bridge", type=Path, default=Path("results/B10_t1_b5_same_access_sampling_or_dmrg_bridge_v0.json"))
    parser.add_argument("--production-contract", type=Path, default=Path("results/B5_B10_same_access_production_contract_gate_v0.json"))
    parser.add_argument("--seeded-replacement", type=Path, default=Path("results/B5_seeded_pressure_replacement_audit_v0.json"))
    parser.add_argument("--json-output", type=Path, default=Path("results/B5_B10_response_oracle_cost_ledger_v0.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("research/B5_B10_response_oracle_cost_ledger.md"))
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    write_markdown(payload, args.markdown_output)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "method": payload["method"],
                "oracle_requirements_passed": payload["summary"]["oracle_requirements_passed"],
                "oracle_requirements_failed": payload["summary"]["oracle_requirements_failed"],
                "remaining_positive_route_packets": payload["summary"]["remaining_positive_route_packets"],
                "validation_errors": payload["validation_errors"],
            },
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )
    return 1 if payload["validation_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
