#!/usr/bin/env python3
"""Four-parameter repair-pressure gate for the unresolved B1/B7 cone_01 packet.

T-B1-004aj left one reduced-CNOT packet unresolved: source line 1381. This gate
keeps the same pi/4-snapped two-CNOT local-U3 scaffold and exhaustively frees
exactly four local-U3 parameters for that packet only.

This is a pressure test, not a resource claim. A lower residual is evidence
about the scaffold geometry; it is not a symbolic exact decomposition, not a
full-circuit rewrite, and not a B7 ledger saving.
"""

from __future__ import annotations

import argparse
import itertools
import json
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
    first_cnot_orientation,
    residual_norm,
    scaffold_unitary,
    target_matrix,
)
from b1_b7_cone01_sparse_local_u3_repair_gate import optimize_free_indices


ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_PACKET_PATH = ROOT / "results" / "B1_B7_cone01_semantic_replay_packet_gate_v0.json"
SYNTHESIS_PATH = ROOT / "results" / "B1_B7_cone01_packet_synthesis_search_gate_v0.json"
THREE_PARAMETER_PATH = ROOT / "results" / "B1_B7_cone01_three_parameter_local_u3_repair_gate_v0.json"
JSON_OUT = ROOT / "results" / "B1_B7_cone01_four_parameter_line1381_repair_pressure_gate_v0.json"
MD_OUT = ROOT / "research" / "B1_B7_cone01_four_parameter_line1381_repair_pressure_gate.md"

METHOD = "b1_b7_cone01_four_parameter_line1381_repair_pressure_gate_v0"
STATUS = "cone01_four_parameter_line1381_pressure_no_exact_repair"
MODEL_STATUS = "line1381_four_parameter_pressure_improves_residual_but_remains_unrepaired"
TARGET_LINE = 1381
FREE_PARAMETER_COUNT = 4
DEFAULT_MAX_NFEV = 700


def analyze_line1381(max_nfev: int) -> dict[str, Any]:
    semantic = load_json(SEMANTIC_PACKET_PATH)
    synthesis = load_json(SYNTHESIS_PATH)
    three_parameter = load_json(THREE_PARAMETER_PATH)
    packet_by_line = {
        int(packet["candidate_line_number"]): packet
        for packet in semantic.get("semantic_replay_packets", [])
    }
    synthesis_by_line = {
        int(row["candidate_line_number"]): row
        for row in synthesis.get("packet_synthesis_rows", [])
    }
    three_by_line = {
        int(row["candidate_line_number"]): row
        for row in three_parameter.get("three_parameter_local_u3_repair_rows", [])
    }

    packet = packet_by_line[TARGET_LINE]
    synthesis_row = synthesis_by_line[TARGET_LINE]
    three_row = three_by_line[TARGET_LINE]
    exact = best_exact_scaffold(synthesis_row)
    if exact is None:
        raise ValueError(f"missing exact scaffold for line {TARGET_LINE}")

    original_parameters = np.array([float(value) for value in exact["best"]["wrapped_parameters"]])
    snapped_parameters = np.array(
        [wrap_angle(snap_to_pi_over_four(value)) for value in original_parameters],
        dtype=float,
    )
    matrix = target_matrix(packet)
    control, target_qubit = first_cnot_orientation(packet)
    cnot_count = int(exact["cnot_count"])
    snapped_residual = residual_norm(
        scaffold_unitary(snapped_parameters, cnot_count, control, target_qubit),
        matrix,
    )

    rows: list[dict[str, Any]] = []
    for free_indices in itertools.combinations(range(len(snapped_parameters)), FREE_PARAMETER_COUNT):
        rows.append(
            optimize_free_indices(
                snapped_parameters,
                original_parameters,
                tuple(free_indices),
                matrix,
                cnot_count,
                control,
                target_qubit,
                max_nfev,
            )
        )

    best = min(rows, key=lambda row: row["residual_norm"])
    exact_rows = [row for row in rows if row["exact_pass"]]
    best_exact = min(exact_rows, key=lambda row: row["residual_norm"], default=None)
    best_three_residual = float(three_row["best_three_parameter_residual_norm"])
    return {
        "pattern_id": packet["pattern_id"],
        "candidate_line_number": TARGET_LINE,
        "window_start_line": int(packet["window_start_line"]),
        "window_end_line": int(packet["window_end_line"]),
        "support_qubits": packet["support_qubits"],
        "source_cnot_count": int(packet["cx_count"]),
        "replacement_cnot_count": cnot_count,
        "candidate_cnot_reduction": int(packet["cx_count"]) - cnot_count,
        "replacement_parameter_count": len(original_parameters),
        "replacement_off_pi_over_four_parameter_count": int(
            parameter_stats([float(value) for value in original_parameters])[
                "off_pi_over_four_parameter_count"
            ]
        ),
        "source_best_three_parameter_residual_norm": best_three_residual,
        "snapped_residual_norm": snapped_residual,
        "four_parameter_candidate_count": len(rows),
        "four_parameter_exact_pass": best_exact is not None,
        "best_four_parameter_residual_norm": best["residual_norm"],
        "best_four_parameter_free_indices": best["free_indices"],
        "best_four_parameter_free_values": best["free_parameter_values"],
        "best_four_parameter_off_pi_over_four_parameter_count": int(
            best["repaired_parameter_stats"]["off_pi_over_four_parameter_count"]
        ),
        "four_parameter_residual_improvement_over_three_parameter": (
            best_three_residual - float(best["residual_norm"])
        ),
        "exact_four_parameter_residual_norm": float(best_exact["residual_norm"])
        if best_exact
        else None,
        "exact_four_parameter_free_indices": best_exact["free_indices"] if best_exact else None,
        "exact_four_parameter_free_values": best_exact["free_parameter_values"]
        if best_exact
        else None,
        "accepted_four_parameter_repair_as_full_circuit_rewrite": False,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
    }


def build_payload(max_nfev: int) -> dict[str, Any]:
    three_parameter = load_json(THREE_PARAMETER_PATH)
    row = analyze_line1381(max_nfev)
    exact_packet_count = int(
        three_parameter["summary"]["total_packet_exact_after_three_parameter_gate"]
    )
    unresolved_packet_count = int(
        three_parameter["summary"]["total_packet_unresolved_after_three_parameter_gate"]
    )
    accepted_removed = int(row["accepted_occurrence_removal"])
    summary = {
        "source_three_parameter_method": three_parameter.get("method"),
        "target_candidate_line_number": TARGET_LINE,
        "source_total_packet_exact_before_four_parameter_gate": exact_packet_count,
        "source_total_packet_unresolved_before_four_parameter_gate": unresolved_packet_count,
        "four_parameter_free_count": FREE_PARAMETER_COUNT,
        "four_parameter_packet_count": 1,
        "four_parameter_candidate_count": row["four_parameter_candidate_count"],
        "four_parameter_exact_packet_count": 1 if row["four_parameter_exact_pass"] else 0,
        "four_parameter_unresolved_packet_count": 0 if row["four_parameter_exact_pass"] else 1,
        "total_packet_exact_after_four_parameter_gate": exact_packet_count
        + (1 if row["four_parameter_exact_pass"] else 0),
        "total_packet_unresolved_after_four_parameter_gate": 0
        if row["four_parameter_exact_pass"]
        else unresolved_packet_count,
        "best_three_parameter_residual_norm": row["source_best_three_parameter_residual_norm"],
        "best_four_parameter_residual_norm": row["best_four_parameter_residual_norm"],
        "four_parameter_residual_improvement_over_three_parameter": row[
            "four_parameter_residual_improvement_over_three_parameter"
        ],
        "candidate_cnot_reduction_if_all_packets_accepted": int(
            three_parameter["summary"]["candidate_cnot_reduction_if_all_packets_accepted"]
        ),
        "partial_candidate_cnot_reduction_if_accepted": int(
            three_parameter["summary"]["partial_candidate_cnot_reduction_if_accepted"]
        ),
        "remaining_unrepaired_replacement_off_pi_over_four_parameter_count": int(
            row["replacement_off_pi_over_four_parameter_count"]
        ),
        "accepted_four_parameter_repair_as_full_circuit_rewrite_count": 0,
        "accepted_occurrence_removal": accepted_removed,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": max(0, REQUIRED_OCCURRENCE_REMOVALS - accepted_removed),
        "missing_proxy_t_after_gate": max(
            0,
            (REQUIRED_OCCURRENCE_REMOVALS - accepted_removed) * PROXY_T_PER_OCCURRENCE,
        ),
        "partial_packet_repair_claimed_as_b7_saving": False,
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
        "workload": "qasmbench_medium_exact/gcm_h6.qasm",
        "source_semantic_packet_result": display_path(SEMANTIC_PACKET_PATH),
        "source_packet_synthesis_result": display_path(SYNTHESIS_PATH),
        "source_three_parameter_local_u3_repair_result": display_path(THREE_PARAMETER_PATH),
        "summary": summary,
        "four_parameter_line1381_repair_pressure_rows": [row],
        "claim_boundary": {
            "supported_claim": (
                "Exhaustive exactly-four-parameter pressure on line 1381 improves the best "
                "packet residual but does not exactify the reduced-CNOT scaffold."
            ),
            "unsupported_claims": [
                "Line 1381 is not repaired by this gate.",
                "The repaired two-packet subset is not accepted as a full-circuit rewrite.",
                "No symbolic exact decomposition or B7 occurrence/proxy-T saving is emitted.",
            ],
            "partial_packet_repair_claimed_as_b7_saving": False,
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
    rows = payload.get("four_parameter_line1381_repair_pressure_rows", [])
    if payload.get("method") != METHOD:
        errors.append("method_mismatch")
    if payload.get("status") != STATUS:
        errors.append("status_mismatch")
    expected = {
        "target_candidate_line_number": TARGET_LINE,
        "source_total_packet_exact_before_four_parameter_gate": 2,
        "source_total_packet_unresolved_before_four_parameter_gate": 1,
        "four_parameter_free_count": 4,
        "four_parameter_packet_count": 1,
        "four_parameter_candidate_count": 3060,
        "four_parameter_exact_packet_count": 0,
        "four_parameter_unresolved_packet_count": 1,
        "total_packet_exact_after_four_parameter_gate": 2,
        "total_packet_unresolved_after_four_parameter_gate": 1,
        "candidate_cnot_reduction_if_all_packets_accepted": 9,
        "partial_candidate_cnot_reduction_if_accepted": 6,
        "remaining_unrepaired_replacement_off_pi_over_four_parameter_count": 15,
        "accepted_four_parameter_repair_as_full_circuit_rewrite_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": 30,
        "missing_proxy_t_after_gate": 600,
    }
    for field, expected_value in expected.items():
        if summary.get(field) != expected_value:
            errors.append(f"{field}_expected_{expected_value}_got_{summary.get(field)}")
    if not rows:
        errors.append("missing_line1381_row")
    else:
        row = rows[0]
        if row.get("candidate_line_number") != TARGET_LINE:
            errors.append(f"line_expected_{TARGET_LINE}_got_{row.get('candidate_line_number')}")
        if row.get("four_parameter_exact_pass") is not False:
            errors.append("line1381_four_parameter_exact_pass_must_be_false")
        if row.get("best_four_parameter_residual_norm", 1.0) >= row.get(
            "source_best_three_parameter_residual_norm", 0.0
        ):
            errors.append("four_parameter_residual_must_improve_over_three_parameter")
        if row.get("accepted_four_parameter_repair_as_full_circuit_rewrite") is not False:
            errors.append("line1381_must_not_accept_rewrite")
        if row.get("accepted_occurrence_removal") != 0:
            errors.append("line1381_accepted_occurrence_must_be_zero")
    for field in [
        "partial_packet_repair_claimed_as_b7_saving",
        "symbolic_exact_decomposition_claimed",
        "full_circuit_rewrite_claimed",
        "resource_saving_claimed",
        "b7_ledger_improvement_claimed",
    ]:
        if summary.get(field) is not False:
            errors.append(f"{field}_must_be_false")
        if payload.get("claim_boundary", {}).get(field) is not False:
            errors.append(f"claim_boundary_{field}_must_be_false")
    return errors


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    row = payload["four_parameter_line1381_repair_pressure_rows"][0]
    lines = [
        "# B1/B7 Cone_01 Four-Parameter Line-1381 Repair Pressure Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This artifact consumes T-B1-004aj and exhaustively frees exactly four local-U3 parameters for the one remaining unresolved reduced-CNOT packet, line 1381.",
        "",
        "## Summary",
        "",
        f"- Target candidate line: `{summary['target_candidate_line_number']}`",
        f"- Four-parameter candidates searched: `{summary['four_parameter_candidate_count']}`",
        f"- Four-parameter exact packets: `{summary['four_parameter_exact_packet_count']}`",
        f"- Total exact packets after this gate: `{summary['total_packet_exact_after_four_parameter_gate']}` / `3`",
        f"- Remaining unresolved packets: `{summary['total_packet_unresolved_after_four_parameter_gate']}`",
        f"- Best 3-param residual: `{summary['best_three_parameter_residual_norm']:.12e}`",
        f"- Best 4-param residual: `{summary['best_four_parameter_residual_norm']:.12e}`",
        f"- Residual improvement: `{summary['four_parameter_residual_improvement_over_three_parameter']:.12e}`",
        f"- Partial CNOT reduction if accepted: `{summary['partial_candidate_cnot_reduction_if_accepted']}`",
        f"- Accepted occurrence/proxy-T reduction: `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        f"- Validation errors: `{summary['validation_error_count']}`",
        "",
        "## Packet Row",
        "",
        "| Candidate line | Replacement CX | 3-param residual | Best 4-param residual | Exact 4-param pass | Best indices | Accepted rewrite |",
        "|---:|---:|---:|---:|---|---|---|",
        f"| {row['candidate_line_number']} | {row['replacement_cnot_count']} | "
        f"{row['source_best_three_parameter_residual_norm']:.6e} | "
        f"{row['best_four_parameter_residual_norm']:.6e} | "
        f"{row['four_parameter_exact_pass']} | "
        f"{row['best_four_parameter_free_indices']} | "
        f"{row['accepted_four_parameter_repair_as_full_circuit_rewrite']} |",
        "",
        "## Claim Boundary",
        "",
        "Line 1381 improves under exactly-four-parameter pressure but still does not pass the exact residual gate. The project remains at 2/3 bounded packet repairs, with no symbolic exact decomposition, no full-circuit replay certificate, and no B7 occurrence/proxy-T saving.",
        "",
        "## Next Required Gate",
        "",
        "The next route must either broaden beyond four freed local-U3 parameters, change the two-CNOT scaffold, prove a scoped obstruction for this scaffold family, or abandon this reduced-CNOT route for a ledger-reducing construction.",
        "",
    ]
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, default=JSON_OUT)
    parser.add_argument("--markdown-output", type=Path, default=MD_OUT)
    parser.add_argument("--max-nfev", type=int, default=DEFAULT_MAX_NFEV)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_payload(args.max_nfev)
    errors = validate_payload(payload)
    payload["summary"]["validation_error_count"] = len(errors)
    if errors:
        payload["validation_errors"] = errors
    write_json(args.json_output, payload, pretty=args.pretty)
    write_text(args.markdown_output, render_markdown(payload))
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
