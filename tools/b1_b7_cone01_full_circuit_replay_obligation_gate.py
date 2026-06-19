#!/usr/bin/env python3
"""Full-circuit replay obligation gate for B1/B7 cone_01 packets.

T-B1-004am/ar make the current boundary sharper: all three reduced-CNOT
packets have bounded exact repairs, but the project still lacks the evidence
that would turn those local packet repairs into accepted full-circuit replay
certificates and B7 ledger savings.

This gate records the missing obligations explicitly. It is a negative
acceptance gate, not a rewrite.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from b1_b7_cone01_carrier_absorption_inventory_gate import (
    PROXY_T_PER_OCCURRENCE,
    REQUIRED_OCCURRENCE_REMOVALS,
    display_path,
    load_json,
    write_json,
    write_text,
)


ROOT = Path(__file__).resolve().parents[1]
REPAIRED_PACKET_PATH = ROOT / "results" / "B1_B7_cone01_repaired_packet_resource_boundary_gate_v0.json"
LINE1381_EXACT_PATH = ROOT / "results" / "B1_B7_cone01_line1381_exact_decomposition_pressure_gate_v0.json"
LINE1381_CONTEXT_PATH = ROOT / "results" / "B1_B7_cone01_line1381_context_absorption_gate_v0.json"
LINE1381_MULTI_CONTEXT_PATH = ROOT / "results" / "B1_B7_cone01_line1381_multi_rotation_context_gate_v0.json"
LINE1381_FOUR_CONTEXT_PATH = ROOT / "results" / "B1_B7_cone01_line1381_four_rotation_context_gate_v0.json"
LINE1381_CORRIDOR_PATH = ROOT / "results" / "B1_B7_cone01_line1381_commutation_corridor_gate_v0.json"
JSON_OUT = ROOT / "results" / "B1_B7_cone01_full_circuit_replay_obligation_gate_v0.json"
MD_OUT = ROOT / "research" / "B1_B7_cone01_full_circuit_replay_obligation_gate.md"

METHOD = "b1_b7_cone01_full_circuit_replay_obligation_gate_v0"
STATUS = "cone01_full_circuit_replay_obligations_not_satisfied"
MODEL_STATUS = "bounded_packet_repairs_do_not_yet_form_full_circuit_replay_certificates"


def line1381_pressure() -> dict[str, Any]:
    exact = load_json(LINE1381_EXACT_PATH)["summary"]
    context = load_json(LINE1381_CONTEXT_PATH)["summary"]
    multi = load_json(LINE1381_MULTI_CONTEXT_PATH)["summary"]
    four = load_json(LINE1381_FOUR_CONTEXT_PATH)["summary"]
    corridor = load_json(LINE1381_CORRIDOR_PATH)["summary"]
    return {
        "simple_exact_decomposition_accept_count": exact[
            "accepted_exact_decomposition_parameter_count"
        ],
        "single_step_context_absorption_accept_count": context[
            "accepted_context_absorption_certificate_count"
        ],
        "multi_rotation_context_absorption_accept_count": multi[
            "accepted_multi_rotation_context_absorption_count"
        ],
        "four_rotation_context_absorption_accept_count": four[
            "accepted_four_rotation_context_absorption_count"
        ],
        "commutation_corridor_candidate_accept_count": corridor[
            "accepted_commutation_corridor_replay_candidate_count"
        ],
        "best_context_candidate_count": corridor["best_context_candidate_count"],
        "context_reference_count": corridor["context_reference_count"],
        "clear_external_standalone_z_reference_count": corridor[
            "clear_external_standalone_z_reference_count"
        ],
    }


def obligation_rows() -> list[dict[str, Any]]:
    repaired = load_json(REPAIRED_PACKET_PATH)
    line1381 = line1381_pressure()
    rows: list[dict[str, Any]] = []
    for row in repaired["repaired_packet_resource_boundary_rows"]:
        line = int(row["candidate_line_number"])
        resource_clean = int(row["repaired_off_pi_over_four_parameter_count"]) == int(
            row["source_off_pi_over_four_parameter_count"]
        )
        symbolic_exactness = False
        full_circuit_replay_event = False
        replacement_patch = False
        occurrence_class_lift = False
        b7_ledger_acceptance = False
        line1381_context_or_pricing = True
        line1381_context_summary: dict[str, Any] | None = None
        if line == 1381:
            line1381_context_or_pricing = (
                line1381["simple_exact_decomposition_accept_count"] > 0
                or line1381["single_step_context_absorption_accept_count"] > 0
                or line1381["multi_rotation_context_absorption_accept_count"] > 0
                or line1381["four_rotation_context_absorption_accept_count"] > 0
                or line1381["commutation_corridor_candidate_accept_count"] > 0
            )
            line1381_context_summary = line1381

        obligations = {
            "bounded_packet_exact_repair_available": bool(row["bounded_packet_exact_repair"]),
            "resource_clean_or_priced": resource_clean,
            "symbolic_exactness_certificate_available": symbolic_exactness,
            "full_circuit_replay_event_available": full_circuit_replay_event,
            "replacement_qasm_patch_available": replacement_patch,
            "occurrence_class_lift_available": occurrence_class_lift,
            "line1381_context_or_pricing_available": line1381_context_or_pricing,
            "b7_ledger_acceptance_available": b7_ledger_acceptance,
        }
        blocking = [name for name, passed in obligations.items() if not passed]
        rows.append(
            {
                "candidate_line_number": line,
                "repair_gate_id": row["repair_gate_id"],
                "source_cnot_count": row["source_cnot_count"],
                "replacement_cnot_count": row["replacement_cnot_count"],
                "candidate_cnot_reduction": row["candidate_cnot_reduction"],
                "bounded_packet_exact_repair": row["bounded_packet_exact_repair"],
                "exact_repair_free_parameter_count": row[
                    "exact_repair_free_parameter_count"
                ],
                "repaired_off_pi_over_four_parameter_count": row[
                    "repaired_off_pi_over_four_parameter_count"
                ],
                "repaired_incremental_proxy_t_pressure": row[
                    "repaired_incremental_proxy_t_pressure"
                ],
                "obligations": obligations,
                "blocking_obligation_count": len(blocking),
                "blocking_obligations": blocking,
                "line1381_context_pressure_summary": line1381_context_summary,
                "accepted_full_circuit_replay_certificate": False,
                "accepted_occurrence_removal": 0,
                "accepted_proxy_t_reduction": 0,
            }
        )
    return rows


def build_payload() -> dict[str, Any]:
    repaired = load_json(REPAIRED_PACKET_PATH)
    rows = obligation_rows()
    accepted_removed = sum(row["accepted_occurrence_removal"] for row in rows)
    summary = {
        "source_repaired_packet_method": repaired.get("method"),
        "packet_count": len(rows),
        "bounded_packet_exact_repair_count": sum(
            1 for row in rows if row["bounded_packet_exact_repair"]
        ),
        "resource_clean_or_priced_packet_count": sum(
            1 for row in rows if row["obligations"]["resource_clean_or_priced"]
        ),
        "packets_with_remaining_unpriced_off_grid_count": sum(
            1 for row in rows if not row["obligations"]["resource_clean_or_priced"]
        ),
        "symbolic_exactness_certificate_count": sum(
            1
            for row in rows
            if row["obligations"]["symbolic_exactness_certificate_available"]
        ),
        "full_circuit_replay_event_count": sum(
            1 for row in rows if row["obligations"]["full_circuit_replay_event_available"]
        ),
        "replacement_qasm_patch_count": sum(
            1 for row in rows if row["obligations"]["replacement_qasm_patch_available"]
        ),
        "occurrence_class_lift_count": sum(
            1 for row in rows if row["obligations"]["occurrence_class_lift_available"]
        ),
        "b7_ledger_acceptance_count": sum(
            1 for row in rows if row["obligations"]["b7_ledger_acceptance_available"]
        ),
        "line1381_context_or_pricing_accept_count": sum(
            1
            for row in rows
            if row["candidate_line_number"] == 1381
            and row["obligations"]["line1381_context_or_pricing_available"]
        ),
        "total_blocking_obligation_count": sum(row["blocking_obligation_count"] for row in rows),
        "max_blocking_obligation_count": max(row["blocking_obligation_count"] for row in rows),
        "candidate_cnot_reduction_if_all_packets_accepted": sum(
            row["candidate_cnot_reduction"] for row in rows
        ),
        "accepted_full_circuit_replay_certificate_count": sum(
            1 for row in rows if row["accepted_full_circuit_replay_certificate"]
        ),
        "accepted_occurrence_removal": accepted_removed,
        "accepted_proxy_t_reduction": sum(row["accepted_proxy_t_reduction"] for row in rows),
        "missing_occurrences_after_gate": max(0, REQUIRED_OCCURRENCE_REMOVALS - accepted_removed),
        "missing_proxy_t_after_gate": max(
            0,
            (REQUIRED_OCCURRENCE_REMOVALS - accepted_removed) * PROXY_T_PER_OCCURRENCE,
        ),
        "bounded_packet_repair_claimed_as_full_circuit_rewrite": False,
        "symbolic_exact_decomposition_claimed": False,
        "full_circuit_rewrite_claimed": False,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
    }
    payload = {
        "benchmark_id": "B1",
        "linked_b7_problem_id": 21,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "workload": repaired.get("workload", "qasmbench_medium_exact/gcm_h6.qasm"),
        "source_repaired_packet_resource_boundary_result": display_path(REPAIRED_PACKET_PATH),
        "source_line1381_exact_decomposition_result": display_path(LINE1381_EXACT_PATH),
        "source_line1381_context_absorption_result": display_path(LINE1381_CONTEXT_PATH),
        "source_line1381_multi_rotation_context_result": display_path(
            LINE1381_MULTI_CONTEXT_PATH
        ),
        "source_line1381_four_rotation_context_result": display_path(
            LINE1381_FOUR_CONTEXT_PATH
        ),
        "source_line1381_commutation_corridor_result": display_path(LINE1381_CORRIDOR_PATH),
        "summary": summary,
        "full_circuit_replay_obligation_rows": rows,
        "claim_boundary": {
            "supported_claim": (
                "The current cone_01 packet route has bounded exact repairs but has not "
                "satisfied the symbolic/full-circuit replay obligations required for B7 "
                "ledger acceptance."
            ),
            "unsupported_claims": [
                "No full-circuit replay certificate is accepted.",
                "No source-to-replacement QASM patch is accepted.",
                "No occurrence class has been lifted to the 30-occurrence B7 target.",
                "No B7 occurrence or proxy-T reduction is accepted.",
            ],
            "bounded_packet_repair_claimed_as_full_circuit_rewrite": False,
            "symbolic_exact_decomposition_claimed": False,
            "full_circuit_rewrite_claimed": False,
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
    }
    payload["summary"]["validation_error_count"] = len(validate_payload(payload))
    return payload


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = payload.get("summary", {})
    rows = payload.get("full_circuit_replay_obligation_rows", [])
    if payload.get("method") != METHOD:
        errors.append("method_mismatch")
    if payload.get("status") != STATUS:
        errors.append("status_mismatch")
    expected = {
        "packet_count": 3,
        "bounded_packet_exact_repair_count": 3,
        "resource_clean_or_priced_packet_count": 2,
        "packets_with_remaining_unpriced_off_grid_count": 1,
        "symbolic_exactness_certificate_count": 0,
        "full_circuit_replay_event_count": 0,
        "replacement_qasm_patch_count": 0,
        "occurrence_class_lift_count": 0,
        "b7_ledger_acceptance_count": 0,
        "line1381_context_or_pricing_accept_count": 0,
        "candidate_cnot_reduction_if_all_packets_accepted": 9,
        "accepted_full_circuit_replay_certificate_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": 30,
        "missing_proxy_t_after_gate": 600,
    }
    for field, value in expected.items():
        if summary.get(field) != value:
            errors.append(f"{field}_expected_{value}_got_{summary.get(field)}")
    if [row.get("candidate_line_number") for row in rows] != [1378, 268, 1381]:
        errors.append("candidate_lines_must_be_[1378,268,1381]")
    for row in rows:
        line = row.get("candidate_line_number")
        if row.get("bounded_packet_exact_repair") is not True:
            errors.append(f"line_{line}_must_preserve_bounded_packet_repair")
        if row.get("accepted_full_circuit_replay_certificate") is not False:
            errors.append(f"line_{line}_must_not_accept_full_circuit_replay")
        if row.get("accepted_occurrence_removal") != 0:
            errors.append(f"line_{line}_accepted_occurrence_must_be_zero")
        obligations = row.get("obligations", {})
        for field in [
            "symbolic_exactness_certificate_available",
            "full_circuit_replay_event_available",
            "replacement_qasm_patch_available",
            "occurrence_class_lift_available",
            "b7_ledger_acceptance_available",
        ]:
            if obligations.get(field) is not False:
                errors.append(f"line_{line}_{field}_must_be_false")
        if line == 1381:
            if obligations.get("resource_clean_or_priced") is not False:
                errors.append("line_1381_resource_clean_or_priced_must_be_false")
            if obligations.get("line1381_context_or_pricing_available") is not False:
                errors.append("line_1381_context_or_pricing_must_be_false")
            pressure = row.get("line1381_context_pressure_summary") or {}
            if pressure.get("commutation_corridor_candidate_accept_count") != 0:
                errors.append("line_1381_corridor_accept_count_must_be_zero")
        else:
            if obligations.get("resource_clean_or_priced") is not True:
                errors.append(f"line_{line}_resource_clean_or_priced_must_be_true")
            if obligations.get("line1381_context_or_pricing_available") is not True:
                errors.append(f"line_{line}_line1381_context_flag_must_be_true")
    for field in [
        "bounded_packet_repair_claimed_as_full_circuit_rewrite",
        "symbolic_exact_decomposition_claimed",
        "full_circuit_rewrite_claimed",
        "resource_saving_claimed",
        "b7_ledger_improvement_claimed",
    ]:
        if summary.get(field) is not False or payload.get("claim_boundary", {}).get(field) is not False:
            errors.append(f"{field}_must_remain_false")
    return errors


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = payload["full_circuit_replay_obligation_rows"]
    lines = [
        "# B1/B7 cone_01 Full-Circuit Replay Obligation Gate",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Packet count / bounded exact repairs: `{summary['packet_count']}` / `{summary['bounded_packet_exact_repair_count']}`",
        f"- Resource-clean packets / unpriced off-grid packets: `{summary['resource_clean_or_priced_packet_count']}` / `{summary['packets_with_remaining_unpriced_off_grid_count']}`",
        f"- Symbolic exactness / full-circuit replay events / QASM patches: `{summary['symbolic_exactness_certificate_count']}` / `{summary['full_circuit_replay_event_count']}` / `{summary['replacement_qasm_patch_count']}`",
        f"- Occurrence lift / B7 ledger acceptance: `{summary['occurrence_class_lift_count']}` / `{summary['b7_ledger_acceptance_count']}`",
        f"- Candidate CNOT reduction if accepted: `{summary['candidate_cnot_reduction_if_all_packets_accepted']}`",
        f"- Accepted replay / occurrence / proxy-T reduction: `{summary['accepted_full_circuit_replay_certificate_count']}` / `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        f"- Validation errors: `{summary['validation_error_count']}`",
        "",
        "## Packet Obligations",
        "",
        "| Line | Repair gate | CNOT delta | Off-grid params | Blocking obligations | Accepted replay |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['candidate_line_number']} | {row['repair_gate_id']} | "
            f"{row['candidate_cnot_reduction']} | "
            f"{row['repaired_off_pi_over_four_parameter_count']} | "
            f"{row['blocking_obligation_count']} | "
            f"{row['accepted_full_circuit_replay_certificate']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"]["supported_claim"],
            "",
            "Unsupported claims:",
            "",
        ]
    )
    for claim in payload["claim_boundary"]["unsupported_claims"]:
        lines.append(f"- {claim}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "The repaired packets are stronger than the raw reduced-CNOT candidates, "
                "but they remain bounded-packet evidence only. Lines 1378 and 268 still "
                "need symbolic exactness, a replay event, a replacement QASM patch, and "
                "an occurrence-class lift. Line 1381 carries those obligations plus an "
                "unpriced five-parameter off-grid resource burden already rejected by "
                "simple exact decomposition, bounded context absorption, four-rotation "
                "context search, and cheap commutation-corridor movement."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=JSON_OUT)
    parser.add_argument("--markdown-output", type=Path, default=MD_OUT)
    args = parser.parse_args()
    payload = build_payload()
    write_json(args.json_output, payload, True)
    write_text(args.markdown_output, render_markdown(payload))
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
