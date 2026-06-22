#!/usr/bin/env python3
"""Bounded replacement patch gate for B1/B7 cone_01 packets.

T-B1-004as showed that the repaired reduced-CNOT packets still lack concrete
replacement QASM patches and full-circuit replay events. This gate emits
bounded OpenQASM 3 patch snippets for the three exact repaired packets, then
checks whether those snippets are already composable as a full-circuit patch
set.

The answer is still no: snippets exist for all three bounded packets, but two
source windows overlap, so the snippets are not accepted as independent
full-circuit replacements or B7 ledger savings.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from b1_b7_cone01_carrier_absorption_inventory_gate import (
    PROXY_T_PER_OCCURRENCE,
    REQUIRED_OCCURRENCE_REMOVALS,
    display_path,
    load_json,
    write_json,
    write_text,
)
from b1_b7_cone01_local_u3_exactification_gate import (
    best_exact_scaffold,
    parameter_stats,
    snap_to_pi_over_four,
    wrap_angle,
)
from b1_b7_cone01_packet_synthesis_search_gate import (
    EXACT_TOLERANCE,
    first_cnot_orientation,
    phase_align,
    scaffold_unitary,
    target_matrix,
)
from b1_b7_cone01_sparse_local_u3_repair_gate import optimize_free_indices


ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_PACKET_PATH = ROOT / "results" / "B1_B7_cone01_semantic_replay_packet_gate_v0.json"
SYNTHESIS_PATH = ROOT / "results" / "B1_B7_cone01_packet_synthesis_search_gate_v0.json"
SPARSE_REPAIR_PATH = ROOT / "results" / "B1_B7_cone01_sparse_local_u3_repair_gate_v0.json"
THREE_PARAMETER_PATH = ROOT / "results" / "B1_B7_cone01_three_parameter_local_u3_repair_gate_v0.json"
FIVE_PARAMETER_PATH = ROOT / "results" / "B1_B7_cone01_five_parameter_line1381_exact_repair_gate_v0.json"
OBLIGATION_PATH = ROOT / "results" / "B1_B7_cone01_full_circuit_replay_obligation_gate_v0.json"
JSON_OUT = ROOT / "results" / "B1_B7_cone01_bounded_replacement_patch_gate_v0.json"
MD_OUT = ROOT / "research" / "B1_B7_cone01_bounded_replacement_patch_gate.md"

METHOD = "b1_b7_cone01_bounded_replacement_patch_gate_v0"
STATUS = "cone01_bounded_replacement_patches_not_composable_full_circuit"
MODEL_STATUS = "bounded_qasm3_patches_exist_but_overlapping_windows_block_full_circuit_patch"


def format_angle(value: float) -> str:
    value = float(wrap_angle(value))
    if abs(value) < 5e-15:
        value = 0.0
    return f"{value:.16g}"


def qasm3_for_parameters(
    support_qubits: list[int],
    cnot_count: int,
    local_control: int,
    local_target: int,
    parameters: list[float],
) -> list[str]:
    lines: list[str] = ["// OPENQASM 3 bounded replacement snippet"]
    control_qubit = support_qubits[local_control]
    target_qubit = support_qubits[local_target]
    offset = 0
    for layer_index in range(cnot_count + 1):
        left = parameters[offset : offset + 3]
        right = parameters[offset + 3 : offset + 6]
        lines.append(
            f"U({format_angle(left[0])}, {format_angle(left[1])}, {format_angle(left[2])}) q[{support_qubits[0]}];"
        )
        lines.append(
            f"U({format_angle(right[0])}, {format_angle(right[1])}, {format_angle(right[2])}) q[{support_qubits[1]}];"
        )
        offset += 6
        if layer_index < cnot_count:
            lines.append(f"cx q[{control_qubit}], q[{target_qubit}];")
    return lines


def replacement_parameters(
    packet: dict[str, Any],
    synthesis_row: dict[str, Any],
    sparse_rows: dict[int, dict[str, Any]],
    three_rows: dict[int, dict[str, Any]],
    five_rows: dict[int, dict[str, Any]],
) -> tuple[str, int, list[float], list[int]]:
    exact = best_exact_scaffold(synthesis_row)
    if exact is None:
        raise ValueError(f"missing exact reduced scaffold for line {packet['candidate_line_number']}")
    original = np.array([float(value) for value in exact["best"]["wrapped_parameters"]])
    repaired = np.array([wrap_angle(snap_to_pi_over_four(value)) for value in original], dtype=float)
    line = int(packet["candidate_line_number"])
    if line == 1378:
        sparse_row = sparse_rows[line]
        free_indices = tuple(int(index) for index in sparse_row["best_one_parameter_free_indices"])
        matrix = target_matrix(packet)
        control, target_qubit = first_cnot_orientation(packet)
        repair = optimize_free_indices(
            repaired,
            original,
            free_indices,
            matrix,
            int(exact["cnot_count"]),
            control,
            target_qubit,
            900,
        )
        free_values = repair["free_parameter_values"]
        repair_gate = "T-B1-004ai"
    elif line == 268:
        three_row = three_rows[line]
        free_indices = tuple(int(index) for index in three_row["exact_three_parameter_free_indices"])
        free_values = three_row["exact_three_parameter_free_values"]
        repair_gate = "T-B1-004aj"
    elif line == 1381:
        five_row = five_rows[line]
        free_indices = tuple(int(index) for index in five_row["first_exact_five_parameter_free_indices"])
        free_values = five_row["first_exact_five_parameter_free_values"]
        repair_gate = "T-B1-004al"
    else:
        raise ValueError(f"unexpected packet line {line}")
    for index, value in zip(free_indices, free_values, strict=True):
        repaired[index] = float(value)
    return repair_gate, int(exact["cnot_count"]), [float(wrap_angle(v)) for v in repaired], list(free_indices)


def row_residual(packet: dict[str, Any], cnot_count: int, parameters: list[float]) -> tuple[float, float]:
    matrix = target_matrix(packet)
    control, target_qubit = first_cnot_orientation(packet)
    candidate = scaffold_unitary(np.array(parameters, dtype=float), cnot_count, control, target_qubit)
    aligned = phase_align(candidate, matrix)
    diff = aligned - matrix
    return float(np.linalg.norm(np.concatenate([diff.real.ravel(), diff.imag.ravel()]))), float(
        np.max(np.abs(diff))
    )


def build_rows() -> list[dict[str, Any]]:
    semantic = load_json(SEMANTIC_PACKET_PATH)
    synthesis = load_json(SYNTHESIS_PATH)
    sparse = load_json(SPARSE_REPAIR_PATH)
    three = load_json(THREE_PARAMETER_PATH)
    five = load_json(FIVE_PARAMETER_PATH)
    synthesis_rows = {
        int(row["candidate_line_number"]): row for row in synthesis["packet_synthesis_rows"]
    }
    sparse_rows = {
        int(row["candidate_line_number"]): row for row in sparse["sparse_local_u3_repair_rows"]
    }
    three_rows = {
        int(row["candidate_line_number"]): row
        for row in three["three_parameter_local_u3_repair_rows"]
    }
    five_rows = {
        int(row["candidate_line_number"]): row
        for row in five["five_parameter_line1381_exact_repair_rows"]
    }
    rows: list[dict[str, Any]] = []
    for packet in semantic["semantic_replay_packets"]:
        line = int(packet["candidate_line_number"])
        synthesis_row = synthesis_rows[line]
        repair_gate, cnot_count, parameters, free_indices = replacement_parameters(
            packet,
            synthesis_row,
            sparse_rows,
            three_rows,
            five_rows,
        )
        residual, max_error = row_residual(packet, cnot_count, parameters)
        support_qubits = [int(qubit) for qubit in packet["support_qubits"]]
        control, target_qubit = first_cnot_orientation(packet)
        qasm_lines = qasm3_for_parameters(
            support_qubits,
            cnot_count,
            control,
            target_qubit,
            parameters,
        )
        stats = parameter_stats(parameters)
        rows.append(
            {
                "candidate_line_number": line,
                "repair_gate_id": repair_gate,
                "window_start_line": int(packet["window_start_line"]),
                "window_end_line": int(packet["window_end_line"]),
                "support_qubits": support_qubits,
                "source_cnot_count": int(packet["cx_count"]),
                "replacement_cnot_count": cnot_count,
                "candidate_cnot_reduction": int(packet["cx_count"]) - cnot_count,
                "free_parameter_indices": free_indices,
                "replacement_parameter_count": len(parameters),
                "replacement_off_pi_over_four_parameter_count": int(
                    stats["off_pi_over_four_parameter_count"]
                ),
                "bounded_patch_residual_norm": residual,
                "bounded_patch_max_abs_entry_error": max_error,
                "bounded_patch_exact_pass": residual <= EXACT_TOLERANCE,
                "qasm3_patch_line_count": len(qasm_lines),
                "qasm3_patch_snippet": qasm_lines,
                "bounded_replacement_qasm3_patch_available": True,
                "accepted_full_circuit_replay_certificate": False,
                "accepted_full_circuit_qasm_patch": False,
                "accepted_occurrence_removal": 0,
                "accepted_proxy_t_reduction": 0,
            }
        )
    return rows


def overlapping_pairs(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs: list[dict[str, Any]] = []
    for index, left in enumerate(rows):
        for right in rows[index + 1 :]:
            start = max(int(left["window_start_line"]), int(right["window_start_line"]))
            end = min(int(left["window_end_line"]), int(right["window_end_line"]))
            if start <= end:
                pairs.append(
                    {
                        "left_candidate_line_number": left["candidate_line_number"],
                        "right_candidate_line_number": right["candidate_line_number"],
                        "overlap_start_line": start,
                        "overlap_end_line": end,
                        "overlap_line_count": end - start + 1,
                    }
                )
    return pairs


def build_payload() -> dict[str, Any]:
    obligation = load_json(OBLIGATION_PATH)
    rows = build_rows()
    pairs = overlapping_pairs(rows)
    accepted_removed = sum(row["accepted_occurrence_removal"] for row in rows)
    summary = {
        "source_obligation_method": obligation.get("method"),
        "packet_count": len(rows),
        "bounded_replacement_qasm3_patch_count": sum(
            1 for row in rows if row["bounded_replacement_qasm3_patch_available"]
        ),
        "bounded_patch_exact_pass_count": sum(1 for row in rows if row["bounded_patch_exact_pass"]),
        "max_bounded_patch_residual_norm": max(row["bounded_patch_residual_norm"] for row in rows),
        "max_bounded_patch_entry_error": max(row["bounded_patch_max_abs_entry_error"] for row in rows),
        "total_qasm3_patch_line_count": sum(row["qasm3_patch_line_count"] for row in rows),
        "candidate_cnot_reduction_if_all_patches_accepted": sum(
            row["candidate_cnot_reduction"] for row in rows
        ),
        "replacement_off_pi_over_four_parameter_count": sum(
            row["replacement_off_pi_over_four_parameter_count"] for row in rows
        ),
        "overlapping_patch_window_pair_count": len(pairs),
        "overlapping_patch_window_pairs": pairs,
        "composable_full_circuit_patch_set_available": len(pairs) == 0,
        "accepted_full_circuit_qasm_patch_count": sum(
            1 for row in rows if row["accepted_full_circuit_qasm_patch"]
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
        "bounded_replacement_patch_claimed_as_full_circuit_patch": False,
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
        "workload": obligation.get("workload", "qasmbench_medium_exact/gcm_h6.qasm"),
        "source_full_circuit_replay_obligation_result": display_path(OBLIGATION_PATH),
        "source_semantic_packet_result": display_path(SEMANTIC_PACKET_PATH),
        "source_packet_synthesis_result": display_path(SYNTHESIS_PATH),
        "source_sparse_repair_result": display_path(SPARSE_REPAIR_PATH),
        "source_three_parameter_repair_result": display_path(THREE_PARAMETER_PATH),
        "source_five_parameter_repair_result": display_path(FIVE_PARAMETER_PATH),
        "summary": summary,
        "bounded_replacement_patch_rows": rows,
        "claim_boundary": {
            "supported_claim": (
                "OpenQASM 3 bounded replacement snippets now exist for all three exact "
                "repaired reduced-CNOT packets."
            ),
            "unsupported_claims": [
                "The snippets are not accepted as a composable full-circuit patch set.",
                "The snippets are not accepted full-circuit replay certificates.",
                "The overlapping line-1378 and line-1381 source windows must be resolved before B7 ledger credit.",
                "No occurrence or proxy-T reduction is accepted.",
            ],
            "bounded_replacement_patch_claimed_as_full_circuit_patch": False,
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
    rows = payload.get("bounded_replacement_patch_rows", [])
    if payload.get("method") != METHOD:
        errors.append("method_mismatch")
    if payload.get("status") != STATUS:
        errors.append("status_mismatch")
    expected = {
        "packet_count": 3,
        "bounded_replacement_qasm3_patch_count": 3,
        "bounded_patch_exact_pass_count": 3,
        "candidate_cnot_reduction_if_all_patches_accepted": 9,
        "replacement_off_pi_over_four_parameter_count": 5,
        "overlapping_patch_window_pair_count": 1,
        "composable_full_circuit_patch_set_available": False,
        "accepted_full_circuit_qasm_patch_count": 0,
        "accepted_full_circuit_replay_certificate_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": 30,
        "missing_proxy_t_after_gate": 600,
    }
    for field, value in expected.items():
        if summary.get(field) != value:
            errors.append(f"{field}_expected_{value}_got_{summary.get(field)}")
    if summary.get("max_bounded_patch_residual_norm", 1.0) > EXACT_TOLERANCE:
        errors.append("bounded_patch_residual_exceeds_tolerance")
    if [row.get("candidate_line_number") for row in rows] != [1378, 1381, 268]:
        errors.append("candidate_lines_must_be_[1378,1381,268]")
    for row in rows:
        if row.get("bounded_replacement_qasm3_patch_available") is not True:
            errors.append(f"line_{row.get('candidate_line_number')}_missing_bounded_patch")
        if row.get("bounded_patch_exact_pass") is not True:
            errors.append(f"line_{row.get('candidate_line_number')}_bounded_patch_must_pass")
        if row.get("accepted_full_circuit_qasm_patch") is not False:
            errors.append(f"line_{row.get('candidate_line_number')}_full_circuit_patch_must_be_false")
        if row.get("accepted_occurrence_removal") != 0:
            errors.append(f"line_{row.get('candidate_line_number')}_accepted_occurrence_must_be_zero")
        snippet = row.get("qasm3_patch_snippet", [])
        if not snippet or "OPENQASM 3" not in snippet[0]:
            errors.append(f"line_{row.get('candidate_line_number')}_snippet_must_be_openqasm3")
    pair = (summary.get("overlapping_patch_window_pairs") or [{}])[0]
    if pair.get("left_candidate_line_number") != 1378 or pair.get("right_candidate_line_number") != 1381:
        errors.append("overlap_pair_must_be_1378_1381")
    for field in [
        "bounded_replacement_patch_claimed_as_full_circuit_patch",
        "full_circuit_rewrite_claimed",
        "resource_saving_claimed",
        "b7_ledger_improvement_claimed",
    ]:
        if summary.get(field) is not False or payload.get("claim_boundary", {}).get(field) is not False:
            errors.append(f"{field}_must_remain_false")
    return errors


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = payload["bounded_replacement_patch_rows"]
    lines = [
        "# B1/B7 cone_01 Bounded Replacement Patch Gate",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Bounded OpenQASM 3 patch snippets: `{summary['bounded_replacement_qasm3_patch_count']}` / `{summary['packet_count']}`",
        f"- Bounded exact-pass snippets: `{summary['bounded_patch_exact_pass_count']}`",
        f"- Max bounded residual / entry error: `{summary['max_bounded_patch_residual_norm']:.6e}` / `{summary['max_bounded_patch_entry_error']:.6e}`",
        f"- Candidate CNOT reduction if accepted: `{summary['candidate_cnot_reduction_if_all_patches_accepted']}`",
        f"- Remaining replacement off-grid parameters: `{summary['replacement_off_pi_over_four_parameter_count']}`",
        f"- Overlapping source-window pairs: `{summary['overlapping_patch_window_pair_count']}`",
        f"- Composable full-circuit patch set available: `{summary['composable_full_circuit_patch_set_available']}`",
        f"- Accepted full-circuit patch / replay / occurrence / proxy-T reduction: `{summary['accepted_full_circuit_qasm_patch_count']}` / `{summary['accepted_full_circuit_replay_certificate_count']}` / `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        f"- Validation errors: `{summary['validation_error_count']}`",
        "",
        "## Patch Rows",
        "",
        "| Line | Window | Support | CNOT delta | QASM3 lines | Off-grid params | Accepted full-circuit patch |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['candidate_line_number']} | {row['window_start_line']}-{row['window_end_line']} | "
            f"{row['support_qubits']} | {row['candidate_cnot_reduction']} | "
            f"{row['qasm3_patch_line_count']} | {row['replacement_off_pi_over_four_parameter_count']} | "
            f"{row['accepted_full_circuit_qasm_patch']} |"
        )
    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"]["supported_claim"], "", "Unsupported claims:", ""])
    for claim in payload["claim_boundary"]["unsupported_claims"]:
        lines.append(f"- {claim}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "This gate converts the prior replay obligation into concrete bounded patch "
                "snippets, which is real forward motion. It also exposes why B7 still cannot "
                "count a saving: line 1378 and line 1381 patches overlap on source lines "
                "1369-1377, so independent local snippets are not yet a composable "
                "full-circuit replacement. The next gate must merge or resynthesize the "
                "overlapping patch region and then replay it against the source circuit."
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
