#!/usr/bin/env python3
"""Sparse local-U3 repair gate for B1/B7 cone_01 reduced-CNOT packets.

T-B1-004ah showed that snapping every reduced-CNOT local-U3 parameter to the
pi/4 grid breaks all three packet replays. This gate tests the next-cheapest
repair: keep the pi/4 snapped scaffold, but free one or two local-U3 parameters
and optimize only those sparse continuous degrees of freedom.

Finding a sparse packet repair is still not a full-circuit rewrite, not a
symbolic exact decomposition, and not a B7 ledger saving. It is only a bounded
packet-level repair candidate when the exact residual gate passes.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import least_squares

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
    residual_norm,
    residual_vector,
    scaffold_unitary,
    target_matrix,
)


ROOT = Path(__file__).resolve().parents[1]
SEMANTIC_PACKET_PATH = ROOT / "results" / "B1_B7_cone01_semantic_replay_packet_gate_v0.json"
SYNTHESIS_PATH = ROOT / "results" / "B1_B7_cone01_packet_synthesis_search_gate_v0.json"
EXACTIFICATION_PATH = ROOT / "results" / "B1_B7_cone01_local_u3_exactification_gate_v0.json"
JSON_OUT = ROOT / "results" / "B1_B7_cone01_sparse_local_u3_repair_gate_v0.json"
MD_OUT = ROOT / "research" / "B1_B7_cone01_sparse_local_u3_repair_gate.md"

METHOD = "b1_b7_cone01_sparse_local_u3_repair_gate_v0"
STATUS = "cone01_sparse_local_u3_repair_partial_not_ledger_accepted"
MODEL_STATUS = "one_packet_sparse_u3_repair_found_two_packets_remain_unrepaired"
MAX_FREE_PARAMETER_COUNT = 2
DEFAULT_MAX_NFEV = 900


def candidate_seeds(base_values: np.ndarray, original_values: np.ndarray) -> list[np.ndarray]:
    seeds = [
        np.array(base_values, dtype=float),
        np.array(original_values, dtype=float),
        np.zeros(len(base_values), dtype=float),
    ]
    if len(base_values) == 1:
        for value in [math.pi / 4, -math.pi / 4, math.pi / 2, -math.pi / 2]:
            seeds.append(np.array([value], dtype=float))
    return seeds


def optimize_free_indices(
    base_parameters: np.ndarray,
    original_parameters: np.ndarray,
    free_indices: tuple[int, ...],
    target: np.ndarray,
    cnot_count: int,
    control: int,
    target_qubit: int,
    max_nfev: int,
) -> dict[str, Any]:
    index_array = np.array(free_indices, dtype=int)
    base_free = base_parameters[index_array]
    original_free = original_parameters[index_array]

    def objective(values: np.ndarray) -> np.ndarray:
        trial = base_parameters.copy()
        trial[index_array] = values
        return residual_vector(scaffold_unitary(trial, cnot_count, control, target_qubit), target)

    best: dict[str, Any] | None = None
    for seed in candidate_seeds(base_free, original_free):
        result = least_squares(
            objective,
            seed,
            method="trf",
            max_nfev=max_nfev,
            ftol=1e-12,
            xtol=1e-12,
            gtol=1e-12,
        )
        residual = float(np.linalg.norm(result.fun))
        if best is None or residual < best["residual_norm"]:
            repaired_parameters = base_parameters.copy()
            repaired_parameters[index_array] = result.x
            best = {
                "free_indices": list(free_indices),
                "free_parameter_count": len(free_indices),
                "residual_norm": residual,
                "optimizer_success": bool(result.success),
                "optimizer_nfev": int(result.nfev),
                "free_parameter_values": [float(wrap_angle(value)) for value in result.x],
                "repaired_parameter_stats": parameter_stats(
                    [float(wrap_angle(value)) for value in repaired_parameters]
                ),
                "exact_pass": residual <= EXACT_TOLERANCE,
            }
    assert best is not None
    return best


def sparse_search(
    base_parameters: np.ndarray,
    original_parameters: np.ndarray,
    target: np.ndarray,
    cnot_count: int,
    control: int,
    target_qubit: int,
    max_nfev: int,
) -> dict[str, Any]:
    by_free_count: dict[int, list[dict[str, Any]]] = {}
    for free_count in range(1, MAX_FREE_PARAMETER_COUNT + 1):
        rows = [
            optimize_free_indices(
                base_parameters,
                original_parameters,
                tuple(indices),
                target,
                cnot_count,
                control,
                target_qubit,
                max_nfev,
            )
            for indices in itertools.combinations(range(len(base_parameters)), free_count)
        ]
        by_free_count[free_count] = rows

    best_by_free_count = {
        str(free_count): min(rows, key=lambda row: row["residual_norm"])
        for free_count, rows in by_free_count.items()
    }
    exact_repairs = [
        row
        for rows in by_free_count.values()
        for row in rows
        if row["exact_pass"]
    ]
    best_exact = min(
        exact_repairs,
        key=lambda row: (row["free_parameter_count"], row["residual_norm"]),
        default=None,
    )
    return {
        "searched_candidate_count": sum(len(rows) for rows in by_free_count.values()),
        "best_by_free_parameter_count": best_by_free_count,
        "best_exact_sparse_repair": best_exact,
        "sparse_repair_exact_pass": best_exact is not None,
    }


def analyze_packet(packet: dict[str, Any], synthesis_row: dict[str, Any]) -> dict[str, Any]:
    exact = best_exact_scaffold(synthesis_row)
    if exact is None:
        raise ValueError(f"missing exact scaffold for line {packet['candidate_line_number']}")

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
    search = sparse_search(
        snapped_parameters,
        original_parameters,
        matrix,
        cnot_count,
        control,
        target_qubit,
        DEFAULT_MAX_NFEV,
    )
    best_exact = search["best_exact_sparse_repair"]
    exact_free_count = int(best_exact["free_parameter_count"]) if best_exact else None
    exact_off_grid = (
        int(best_exact["repaired_parameter_stats"]["off_pi_over_four_parameter_count"])
        if best_exact
        else None
    )
    return {
        "pattern_id": packet["pattern_id"],
        "candidate_line_number": int(packet["candidate_line_number"]),
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
        "snapped_residual_norm": snapped_residual,
        "searched_sparse_repair_candidate_count": search["searched_candidate_count"],
        "best_one_parameter_residual_norm": search["best_by_free_parameter_count"]["1"][
            "residual_norm"
        ],
        "best_two_parameter_residual_norm": search["best_by_free_parameter_count"]["2"][
            "residual_norm"
        ],
        "best_one_parameter_free_indices": search["best_by_free_parameter_count"]["1"][
            "free_indices"
        ],
        "best_two_parameter_free_indices": search["best_by_free_parameter_count"]["2"][
            "free_indices"
        ],
        "sparse_repair_exact_pass": search["sparse_repair_exact_pass"],
        "minimum_exact_free_parameter_count": exact_free_count,
        "exact_repair_residual_norm": float(best_exact["residual_norm"]) if best_exact else None,
        "exact_repair_off_pi_over_four_parameter_count": exact_off_grid,
        "accepted_sparse_repair_as_full_circuit_rewrite": False,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
    }


def build_payload() -> dict[str, Any]:
    semantic = load_json(SEMANTIC_PACKET_PATH)
    synthesis = load_json(SYNTHESIS_PATH)
    exactification = load_json(EXACTIFICATION_PATH)
    synthesis_by_line = {
        int(row["candidate_line_number"]): row
        for row in synthesis.get("packet_synthesis_rows", [])
    }
    rows = [
        analyze_packet(packet, synthesis_by_line[int(packet["candidate_line_number"])])
        for packet in semantic.get("semantic_replay_packets", [])
    ]
    exact_rows = [row for row in rows if row["sparse_repair_exact_pass"]]
    unresolved_rows = [row for row in rows if not row["sparse_repair_exact_pass"]]
    accepted_removed = sum(row["accepted_occurrence_removal"] for row in rows)
    summary = {
        "source_semantic_method": semantic.get("method"),
        "source_synthesis_method": synthesis.get("method"),
        "source_exactification_method": exactification.get("method"),
        "packet_count": len(rows),
        "max_free_parameter_count": MAX_FREE_PARAMETER_COUNT,
        "sparse_repair_candidate_count": sum(
            row["searched_sparse_repair_candidate_count"] for row in rows
        ),
        "one_parameter_repair_exact_pass_count": sum(
            1
            for row in rows
            if row["sparse_repair_exact_pass"] and row["minimum_exact_free_parameter_count"] == 1
        ),
        "two_or_fewer_parameter_repair_exact_pass_count": len(exact_rows),
        "sparse_repair_unresolved_packet_count": len(unresolved_rows),
        "candidate_cnot_reduction_if_all_packets_accepted": sum(
            row["candidate_cnot_reduction"] for row in rows
        ),
        "partial_candidate_cnot_reduction_if_accepted": sum(
            row["candidate_cnot_reduction"] for row in exact_rows
        ),
        "replacement_off_pi_over_four_parameter_count": sum(
            row["replacement_off_pi_over_four_parameter_count"] for row in rows
        ),
        "sparse_exact_repair_off_pi_over_four_parameter_count": sum(
            row["exact_repair_off_pi_over_four_parameter_count"] or 0 for row in exact_rows
        ),
        "sparse_exact_repair_free_parameter_count_total": sum(
            row["minimum_exact_free_parameter_count"] or 0 for row in exact_rows
        ),
        "unrepaired_replacement_off_pi_over_four_parameter_count": sum(
            row["replacement_off_pi_over_four_parameter_count"] for row in unresolved_rows
        ),
        "accepted_sparse_repair_as_full_circuit_rewrite_count": 0,
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
        "workload": semantic.get("workload", "qasmbench_medium_exact/gcm_h6.qasm"),
        "source_semantic_packet_result": display_path(SEMANTIC_PACKET_PATH),
        "source_packet_synthesis_result": display_path(SYNTHESIS_PATH),
        "source_local_u3_exactification_result": display_path(EXACTIFICATION_PATH),
        "summary": summary,
        "sparse_local_u3_repair_rows": rows,
        "claim_boundary": {
            "supported_claim": (
                "A sparse one-parameter local-U3 repair restores bounded replay for one of "
                "three reduced-CNOT packet candidates by changing one snapped grid choice; the "
                "other two packets remain unrepaired even with two free local-U3 parameters."
            ),
            "unsupported_claims": [
                "The partial packet repair is not accepted as a full-circuit rewrite.",
                "No symbolic exact decomposition or absorption certificate is emitted.",
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
    rows = payload.get("sparse_local_u3_repair_rows", [])
    if payload.get("method") != METHOD:
        errors.append("method_mismatch")
    if payload.get("status") != STATUS:
        errors.append("status_mismatch")
    if len(rows) != 3:
        errors.append("row_count_must_be_3")
    expected = {
        "packet_count": 3,
        "max_free_parameter_count": 2,
        "sparse_repair_candidate_count": 420,
        "one_parameter_repair_exact_pass_count": 1,
        "two_or_fewer_parameter_repair_exact_pass_count": 1,
        "sparse_repair_unresolved_packet_count": 2,
        "candidate_cnot_reduction_if_all_packets_accepted": 9,
        "partial_candidate_cnot_reduction_if_accepted": 3,
        "replacement_off_pi_over_four_parameter_count": 40,
        "sparse_exact_repair_off_pi_over_four_parameter_count": 0,
        "sparse_exact_repair_free_parameter_count_total": 1,
        "unrepaired_replacement_off_pi_over_four_parameter_count": 30,
        "accepted_sparse_repair_as_full_circuit_rewrite_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": 30,
        "missing_proxy_t_after_gate": 600,
    }
    for field, expected_value in expected.items():
        if summary.get(field) != expected_value:
            errors.append(f"{field}_expected_{expected_value}_got_{summary.get(field)}")
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
    exact_rows = [row for row in rows if row.get("sparse_repair_exact_pass")]
    if [row.get("candidate_line_number") for row in exact_rows] != [1378]:
        errors.append("only_line_1378_should_have_sparse_exact_repair")
    for row in rows:
        if row.get("accepted_sparse_repair_as_full_circuit_rewrite") is not False:
            errors.append(f"{row.get('candidate_line_number')}_must_not_accept_rewrite")
        if row.get("accepted_occurrence_removal") != 0:
            errors.append(f"{row.get('candidate_line_number')}_accepted_occurrence_must_be_zero")
    return errors


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone_01 Sparse Local-U3 Repair Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This artifact consumes T-B1-004ah and tests whether direct pi/4 snapping can be repaired by freeing only one or two local-U3 parameters.",
        "",
        "## Summary",
        "",
        f"- Packets checked: `{summary['packet_count']}`",
        f"- Sparse repair candidates searched: `{summary['sparse_repair_candidate_count']}`",
        f"- One-parameter exact repairs: `{summary['one_parameter_repair_exact_pass_count']}`",
        f"- Two-or-fewer-parameter exact repairs: `{summary['two_or_fewer_parameter_repair_exact_pass_count']}`",
        f"- Unresolved packets after sparse search: `{summary['sparse_repair_unresolved_packet_count']}`",
        f"- Partial CNOT reduction if accepted: `{summary['partial_candidate_cnot_reduction_if_accepted']}`",
        f"- Sparse exact repair off-grid parameters: `{summary['sparse_exact_repair_off_pi_over_four_parameter_count']}`",
        f"- Sparse exact repair free-parameter decisions: `{summary['sparse_exact_repair_free_parameter_count_total']}`",
        f"- Unrepaired replacement off-grid parameters: `{summary['unrepaired_replacement_off_pi_over_four_parameter_count']}`",
        f"- Accepted occurrence/proxy-T reduction: `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        f"- Validation errors: `{summary['validation_error_count']}`",
        "",
        "## Packet Rows",
        "",
        "| Candidate line | Replacement CX | Best 1-param residual | Best 2-param residual | Sparse exact pass | Min exact free params | Accepted rewrite |",
        "|---:|---:|---:|---:|---|---:|---|",
    ]
    for row in payload["sparse_local_u3_repair_rows"]:
        exact_free = row["minimum_exact_free_parameter_count"]
        lines.append(
            f"| {row['candidate_line_number']} | {row['replacement_cnot_count']} | "
            f"{row['best_one_parameter_residual_norm']:.6e} | "
            f"{row['best_two_parameter_residual_norm']:.6e} | "
            f"{row['sparse_repair_exact_pass']} | "
            f"{exact_free if exact_free is not None else 'None'} | "
            f"{row['accepted_sparse_repair_as_full_circuit_rewrite']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "Line 1378 has a bounded packet-level sparse repair after changing one snapped local-U3 grid choice, but the route is still incomplete: the other two packets remain unrepaired even with two free parameters, no symbolic exact decomposition is emitted, no full-circuit rewrite is replayed, and no B7 occurrence/proxy-T saving is accepted.",
            "",
            "## Next Required Gate",
            "",
            "The next route must either broaden the repair dimension/scaffold for the two unresolved packets, convert the line-1378 sparse repair into a symbolic replayable full-circuit certificate, or abandon this reduced-CNOT scaffold for a different occurrence-removing route.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, default=JSON_OUT)
    parser.add_argument("--markdown-output", type=Path, default=MD_OUT)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_payload()
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
