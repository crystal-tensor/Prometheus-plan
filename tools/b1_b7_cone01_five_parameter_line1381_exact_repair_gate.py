#!/usr/bin/env python3
"""Five-parameter exact-repair gate for the B1/B7 cone_01 line-1381 packet.

T-B1-004ak improved line 1381 under four freed local-U3 parameters but did not
exactify it. This gate keeps the same pi/4-snapped two-CNOT scaffold and
deterministically searches exactly five freed local-U3 parameters until it finds
the first exact packet repair.

This closes the bounded packet-level repair set at 3/3 packets. It is still not
a symbolic full-circuit replay certificate, not an accepted local-U3 resource
decomposition, and not a B7 ledger saving.
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
FOUR_PARAMETER_PATH = ROOT / "results" / "B1_B7_cone01_four_parameter_line1381_repair_pressure_gate_v0.json"
JSON_OUT = ROOT / "results" / "B1_B7_cone01_five_parameter_line1381_exact_repair_gate_v0.json"
MD_OUT = ROOT / "research" / "B1_B7_cone01_five_parameter_line1381_exact_repair_gate.md"

METHOD = "b1_b7_cone01_five_parameter_line1381_exact_repair_gate_v0"
STATUS = "cone01_five_parameter_line1381_exact_packet_repair_not_ledger_accepted"
MODEL_STATUS = "line1381_five_parameter_exact_packet_repair_found"
TARGET_LINE = 1381
FREE_PARAMETER_COUNT = 5
DEFAULT_MAX_NFEV = 700
TOTAL_FIVE_PARAMETER_COMBINATIONS = 8568


def analyze_line1381(max_nfev: int) -> dict[str, Any]:
    semantic = load_json(SEMANTIC_PACKET_PATH)
    synthesis = load_json(SYNTHESIS_PATH)
    four_parameter = load_json(FOUR_PARAMETER_PATH)
    packet_by_line = {
        int(packet["candidate_line_number"]): packet
        for packet in semantic.get("semantic_replay_packets", [])
    }
    synthesis_by_line = {
        int(row["candidate_line_number"]): row
        for row in synthesis.get("packet_synthesis_rows", [])
    }

    packet = packet_by_line[TARGET_LINE]
    synthesis_row = synthesis_by_line[TARGET_LINE]
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

    searched_rows: list[dict[str, Any]] = []
    first_exact: dict[str, Any] | None = None
    for free_indices in itertools.combinations(range(len(snapped_parameters)), FREE_PARAMETER_COUNT):
        row = optimize_free_indices(
            snapped_parameters,
            original_parameters,
            tuple(free_indices),
            matrix,
            cnot_count,
            control,
            target_qubit,
            max_nfev,
        )
        searched_rows.append(row)
        if row["exact_pass"]:
            first_exact = row
            break

    best = min(searched_rows, key=lambda row: row["residual_norm"])
    best_four_residual = float(four_parameter["summary"]["best_four_parameter_residual_norm"])
    exact_stats = first_exact["repaired_parameter_stats"] if first_exact else None
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
        "source_best_four_parameter_residual_norm": best_four_residual,
        "snapped_residual_norm": snapped_residual,
        "five_parameter_total_combination_count": TOTAL_FIVE_PARAMETER_COMBINATIONS,
        "five_parameter_candidate_count_until_first_exact": len(searched_rows),
        "five_parameter_exact_pass": first_exact is not None,
        "best_five_parameter_residual_norm": best["residual_norm"],
        "best_five_parameter_free_indices": best["free_indices"],
        "first_exact_five_parameter_residual_norm": float(first_exact["residual_norm"])
        if first_exact
        else None,
        "first_exact_five_parameter_free_indices": first_exact["free_indices"]
        if first_exact
        else None,
        "first_exact_five_parameter_free_values": first_exact["free_parameter_values"]
        if first_exact
        else None,
        "first_exact_five_parameter_off_pi_over_four_parameter_count": int(
            exact_stats["off_pi_over_four_parameter_count"]
        )
        if exact_stats
        else None,
        "five_parameter_residual_improvement_over_four_parameter": (
            best_four_residual - float(best["residual_norm"])
        ),
        "accepted_five_parameter_repair_as_full_circuit_rewrite": False,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
    }


def build_payload(max_nfev: int) -> dict[str, Any]:
    four_parameter = load_json(FOUR_PARAMETER_PATH)
    row = analyze_line1381(max_nfev)
    exact_before = int(four_parameter["summary"]["total_packet_exact_after_four_parameter_gate"])
    unresolved_before = int(
        four_parameter["summary"]["total_packet_unresolved_after_four_parameter_gate"]
    )
    new_exact = 1 if row["five_parameter_exact_pass"] else 0
    accepted_removed = int(row["accepted_occurrence_removal"])
    summary = {
        "source_four_parameter_method": four_parameter.get("method"),
        "target_candidate_line_number": TARGET_LINE,
        "source_total_packet_exact_before_five_parameter_gate": exact_before,
        "source_total_packet_unresolved_before_five_parameter_gate": unresolved_before,
        "five_parameter_free_count": FREE_PARAMETER_COUNT,
        "five_parameter_packet_count": 1,
        "five_parameter_total_combination_count": row["five_parameter_total_combination_count"],
        "five_parameter_candidate_count_until_first_exact": row[
            "five_parameter_candidate_count_until_first_exact"
        ],
        "five_parameter_exact_packet_count": new_exact,
        "five_parameter_unresolved_packet_count": 0 if new_exact else 1,
        "total_packet_exact_after_five_parameter_gate": exact_before + new_exact,
        "total_packet_unresolved_after_five_parameter_gate": 0
        if new_exact
        else unresolved_before,
        "best_four_parameter_residual_norm": row["source_best_four_parameter_residual_norm"],
        "best_five_parameter_residual_norm": row["best_five_parameter_residual_norm"],
        "five_parameter_residual_improvement_over_four_parameter": row[
            "five_parameter_residual_improvement_over_four_parameter"
        ],
        "candidate_cnot_reduction_if_all_packets_accepted": int(
            four_parameter["summary"]["candidate_cnot_reduction_if_all_packets_accepted"]
        ),
        "partial_candidate_cnot_reduction_if_accepted": int(
            four_parameter["summary"]["candidate_cnot_reduction_if_all_packets_accepted"]
        ),
        "remaining_unrepaired_replacement_off_pi_over_four_parameter_count": 0
        if new_exact
        else int(row["replacement_off_pi_over_four_parameter_count"]),
        "five_parameter_exact_repair_off_pi_over_four_parameter_count": (
            row["first_exact_five_parameter_off_pi_over_four_parameter_count"] or 0
        ),
        "accepted_five_parameter_repair_as_full_circuit_rewrite_count": 0,
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
        "source_four_parameter_line1381_repair_pressure_result": display_path(FOUR_PARAMETER_PATH),
        "summary": summary,
        "five_parameter_line1381_exact_repair_rows": [row],
        "claim_boundary": {
            "supported_claim": (
                "A deterministic exactly-five-parameter search finds a bounded packet-level "
                "exact repair for line 1381, closing the cone_01 reduced-CNOT packet set at 3/3."
            ),
            "unsupported_claims": [
                "The packet repair is not accepted as a full-circuit rewrite.",
                "No symbolic exact decomposition or absorption certificate is emitted.",
                "The five off-grid local-U3 degrees of freedom are not accepted as a B7 saving.",
                "No B7 occurrence or proxy-T ledger reduction is accepted.",
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
    rows = payload.get("five_parameter_line1381_exact_repair_rows", [])
    if payload.get("method") != METHOD:
        errors.append("method_mismatch")
    if payload.get("status") != STATUS:
        errors.append("status_mismatch")
    expected = {
        "target_candidate_line_number": TARGET_LINE,
        "source_total_packet_exact_before_five_parameter_gate": 2,
        "source_total_packet_unresolved_before_five_parameter_gate": 1,
        "five_parameter_free_count": 5,
        "five_parameter_packet_count": 1,
        "five_parameter_total_combination_count": 8568,
        "five_parameter_candidate_count_until_first_exact": 5795,
        "five_parameter_exact_packet_count": 1,
        "five_parameter_unresolved_packet_count": 0,
        "total_packet_exact_after_five_parameter_gate": 3,
        "total_packet_unresolved_after_five_parameter_gate": 0,
        "candidate_cnot_reduction_if_all_packets_accepted": 9,
        "partial_candidate_cnot_reduction_if_accepted": 9,
        "remaining_unrepaired_replacement_off_pi_over_four_parameter_count": 0,
        "five_parameter_exact_repair_off_pi_over_four_parameter_count": 5,
        "accepted_five_parameter_repair_as_full_circuit_rewrite_count": 0,
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
        if row.get("five_parameter_exact_pass") is not True:
            errors.append("line1381_five_parameter_exact_pass_must_be_true")
        if row.get("first_exact_five_parameter_residual_norm", 1.0) > 1e-9:
            errors.append("line1381_five_parameter_residual_too_large")
        if row.get("first_exact_five_parameter_free_indices") != [3, 4, 9, 16, 17]:
            errors.append("line1381_five_parameter_indices_mismatch")
        if row.get("accepted_five_parameter_repair_as_full_circuit_rewrite") is not False:
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
    row = payload["five_parameter_line1381_exact_repair_rows"][0]
    lines = [
        "# B1/B7 Cone_01 Five-Parameter Line-1381 Exact Repair Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This artifact consumes T-B1-004ak and searches exactly five freed local-U3 parameters for the one remaining unresolved reduced-CNOT packet, line 1381, stopping at the first exact repair.",
        "",
        "## Summary",
        "",
        f"- Target candidate line: `{summary['target_candidate_line_number']}`",
        f"- Total five-parameter combinations: `{summary['five_parameter_total_combination_count']}`",
        f"- Candidates searched until first exact: `{summary['five_parameter_candidate_count_until_first_exact']}`",
        f"- Five-parameter exact packets: `{summary['five_parameter_exact_packet_count']}`",
        f"- Total exact packets after this gate: `{summary['total_packet_exact_after_five_parameter_gate']}` / `3`",
        f"- Remaining unresolved packets: `{summary['total_packet_unresolved_after_five_parameter_gate']}`",
        f"- Best 4-param residual: `{summary['best_four_parameter_residual_norm']:.12e}`",
        f"- Best 5-param residual: `{summary['best_five_parameter_residual_norm']:.12e}`",
        f"- Five-parameter exact repair off-grid parameters: `{summary['five_parameter_exact_repair_off_pi_over_four_parameter_count']}`",
        f"- Partial CNOT reduction if accepted: `{summary['partial_candidate_cnot_reduction_if_accepted']}`",
        f"- Accepted occurrence/proxy-T reduction: `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        f"- Validation errors: `{summary['validation_error_count']}`",
        "",
        "## Packet Row",
        "",
        "| Candidate line | Replacement CX | 4-param residual | First exact 5-param residual | Exact 5-param pass | Exact indices | Accepted rewrite |",
        "|---:|---:|---:|---:|---|---|---|",
        f"| {row['candidate_line_number']} | {row['replacement_cnot_count']} | "
        f"{row['source_best_four_parameter_residual_norm']:.6e} | "
        f"{row['first_exact_five_parameter_residual_norm']:.6e} | "
        f"{row['five_parameter_exact_pass']} | "
        f"{row['first_exact_five_parameter_free_indices']} | "
        f"{row['accepted_five_parameter_repair_as_full_circuit_rewrite']} |",
        "",
        "## Claim Boundary",
        "",
        "Line 1381 now has a bounded packet-level exact repair after freeing five local-U3 parameters. Together with the earlier line-1378 and line-268 repairs, the reduced-CNOT packet set is 3/3 repaired at packet level. This still is not a symbolic exact decomposition, not a full-circuit replay certificate, and not a B7 occurrence/proxy-T saving because the local-U3 resource burden is not accepted.",
        "",
        "## Next Required Gate",
        "",
        "The next route must convert the three packet repairs into symbolic full-circuit replay certificates, price or eliminate the off-grid local-U3 parameters, and propagate only accepted occurrence removals into the B7 ledger.",
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
