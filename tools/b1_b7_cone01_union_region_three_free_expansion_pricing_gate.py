#!/usr/bin/env python3
"""Targeted three-free expansion pricing gate for B1/B7 cone_01 union candidates.

T-B1-004bo closed the exhaustive two-free-parameter pricing rung for the four
exact 2-CNOT union-region candidates. This gate does not claim an exhaustive
three-free lower bound. Instead, it takes each sequence's best failed two-free
pair, frees one additional local-U3 parameter, and tests whether that targeted
64-trial expansion recovers exact replay at a 60-proxy-T pricing rung.
"""

from __future__ import annotations

import argparse
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
from b1_b7_cone01_local_u3_exactification_gate import wrap_angle
from b1_b7_cone01_packet_synthesis_search_gate import (
    EXACT_TOLERANCE,
    parameter_stats,
    residual_norm,
    residual_vector,
    target_matrix,
)
from b1_b7_cone01_union_region_one_free_parameter_pricing_gate import (
    GRID_SNAP_PATH,
    ORIENTATION_CENSUS_PATH,
    SEMANTIC_PACKET_PATH,
    TARGET_LINE,
    line_packet,
    snapped_parameters,
)
from b1_b7_cone01_union_region_two_cnot_orientation_census_gate import (
    mixed_scaffold_unitary,
)


ROOT = Path(__file__).resolve().parents[1]
TWO_FREE_PATH = (
    ROOT / "results" / "B1_B7_cone01_union_region_two_free_parameter_pricing_gate_v0.json"
)
JSON_OUT = (
    ROOT
    / "results"
    / "B1_B7_cone01_union_region_three_free_expansion_pricing_gate_v0.json"
)
MD_OUT = (
    ROOT / "research" / "B1_B7_cone01_union_region_three_free_expansion_pricing_gate.md"
)

METHOD = "b1_b7_cone01_union_region_three_free_expansion_pricing_gate_v0"
STATUS_REJECTED = "cone01_union_region_targeted_three_free_expansion_rejected"
STATUS_CANDIDATE = (
    "cone01_union_region_targeted_three_free_candidate_needs_full_circuit_replay"
)
MODEL_REJECTED = "best_two_free_pair_plus_one_parameter_expansion_does_not_recover_exactness"
MODEL_CANDIDATE = "best_two_free_pair_plus_one_parameter_expansion_has_exact_local_replay_only"
DEFAULT_MAX_NFEV = 900


def sequence_best_pairs(two_free_payload: dict[str, Any]) -> dict[str, list[int]]:
    pairs: dict[str, list[int]] = {}
    for row in two_free_payload.get("union_region_two_free_sequence_rows", []):
        pairs[str(row["sequence_id"])] = [int(v) for v in row["best_two_free_parameter_pair"]]
    return pairs


def previous_two_free_values(
    two_free_payload: dict[str, Any],
    sequence_id: str,
    pair: list[int],
) -> list[float] | None:
    target_pair = list(pair)
    best_match: dict[str, Any] | None = None
    for row in two_free_payload.get("union_region_two_free_trial_rows", []):
        if row.get("sequence_id") != sequence_id:
            continue
        if [int(v) for v in row.get("free_parameter_pair", [])] != target_pair:
            continue
        if best_match is None or row["residual_norm"] < best_match["residual_norm"]:
            best_match = row
    if best_match is None:
        return None
    return [float(v) for v in best_match["free_parameter_values"]]


def three_free_seeds(
    base: np.ndarray,
    original: np.ndarray,
    triple: tuple[int, int, int],
    prior_pair_values: list[float] | None,
) -> list[np.ndarray]:
    i, j, k = triple
    seeds = [
        np.array([base[i], base[j], base[k]], dtype=float),
        np.array([original[i], original[j], original[k]], dtype=float),
        np.array([base[i], base[j], original[k]], dtype=float),
        np.array([original[i], original[j], base[k]], dtype=float),
        np.array([0.0, 0.0, 0.0], dtype=float),
        np.array([math.pi / 4, -math.pi / 4, 0.0], dtype=float),
        np.array([-math.pi / 4, math.pi / 4, 0.0], dtype=float),
    ]
    if prior_pair_values is not None:
        seeds.extend(
            [
                np.array([prior_pair_values[0], prior_pair_values[1], base[k]], dtype=float),
                np.array(
                    [prior_pair_values[0], prior_pair_values[1], original[k]],
                    dtype=float,
                ),
            ]
        )
    return seeds


def optimize_three_parameters(
    base: np.ndarray,
    original: np.ndarray,
    triple: tuple[int, int, int],
    prior_pair_values: list[float] | None,
    sequence: list[tuple[int, int]],
    target: np.ndarray,
    max_nfev: int,
) -> dict[str, Any]:
    i, j, k = triple

    def objective(values: np.ndarray) -> np.ndarray:
        trial = base.copy()
        trial[i] = values[0]
        trial[j] = values[1]
        trial[k] = values[2]
        return residual_vector(mixed_scaffold_unitary(trial, sequence), target)

    best: dict[str, Any] | None = None
    for seed_index, seed in enumerate(three_free_seeds(base, original, triple, prior_pair_values)):
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
            repaired = base.copy()
            repaired[i] = result.x[0]
            repaired[j] = result.x[1]
            repaired[k] = result.x[2]
            wrapped = [float(wrap_angle(value)) for value in repaired]
            best = {
                "free_parameter_triple": [i, j, k],
                "free_parameter_values": [
                    float(wrap_angle(result.x[0])),
                    float(wrap_angle(result.x[1])),
                    float(wrap_angle(result.x[2])),
                ],
                "source_parameter_values": [
                    float(original[i]),
                    float(original[j]),
                    float(original[k]),
                ],
                "grid_parameter_values": [float(base[i]), float(base[j]), float(base[k])],
                "residual_norm": residual,
                "residual_ratio_to_exact_tolerance": residual / EXACT_TOLERANCE,
                "exact_pass": residual <= EXACT_TOLERANCE,
                "optimizer_success": bool(result.success),
                "optimizer_nfev": int(result.nfev),
                "best_seed_index": seed_index,
                "repaired_parameter_stats": parameter_stats(wrapped),
            }
    assert best is not None
    return best


def run_probe(max_nfev: int) -> dict[str, Any]:
    semantic = load_json(SEMANTIC_PACKET_PATH)
    census = load_json(ORIENTATION_CENSUS_PATH)
    grid_snap = load_json(GRID_SNAP_PATH)
    two_free = load_json(TWO_FREE_PATH)
    packet = line_packet(semantic, TARGET_LINE)
    target = target_matrix(packet)
    best_pairs = sequence_best_pairs(two_free)

    trial_rows: list[dict[str, Any]] = []
    sequence_rows: list[dict[str, Any]] = []
    for row in census["union_region_two_cnot_orientation_rows"]:
        sequence_id = str(row["sequence_id"])
        sequence = [(int(control), int(target_qubit)) for control, target_qubit in row["cnot_sequence"]]
        original = np.array([float(value) for value in row["best"]["wrapped_parameters"]], dtype=float)
        snapped = snapped_parameters(original.tolist())
        best_pair = best_pairs[sequence_id]
        prior_pair_values = previous_two_free_values(two_free, sequence_id, best_pair)
        sequence_trials = []
        for third_index in range(len(original)):
            if third_index in best_pair:
                continue
            triple = (best_pair[0], best_pair[1], third_index)
            trial = optimize_three_parameters(
                snapped,
                original,
                triple,
                prior_pair_values,
                sequence,
                target,
                max_nfev,
            )
            trial.update(
                {
                    "sequence_id": sequence_id,
                    "cnot_sequence": row["cnot_sequence"],
                    "base_two_free_parameter_pair": best_pair,
                    "added_parameter_index": third_index,
                }
            )
            sequence_trials.append(trial)
            trial_rows.append(trial)
        best_trial = min(sequence_trials, key=lambda trial: trial["residual_norm"])
        sequence_rows.append(
            {
                "sequence_id": sequence_id,
                "cnot_sequence": row["cnot_sequence"],
                "source_residual_norm": row["best"]["residual_norm"],
                "source_off_pi_over_four_parameter_count": row["best"]["parameter_stats"][
                    "off_pi_over_four_grid_parameter_count"
                ],
                "grid_snap_residual_norm": residual_norm(
                    mixed_scaffold_unitary(snapped, sequence), target
                ),
                "base_two_free_parameter_pair": best_pair,
                "targeted_three_free_trial_count": len(sequence_trials),
                "targeted_three_free_exact_pass_count": sum(
                    1 for trial in sequence_trials if trial["exact_pass"]
                ),
                "best_targeted_three_free_parameter_triple": best_trial[
                    "free_parameter_triple"
                ],
                "best_targeted_three_free_residual_norm": best_trial["residual_norm"],
                "best_targeted_three_free_residual_ratio_to_exact_tolerance": best_trial[
                    "residual_ratio_to_exact_tolerance"
                ],
                "best_targeted_three_free_off_pi_over_four_parameter_count": best_trial[
                    "repaired_parameter_stats"
                ]["off_pi_over_four_grid_parameter_count"],
                "best_targeted_three_free_nonzero_parameter_count": best_trial[
                    "repaired_parameter_stats"
                ]["nonzero_parameter_count"],
            }
        )

    exact_pass_count = sum(1 for trial in trial_rows if trial["exact_pass"])
    best_trial = min(trial_rows, key=lambda trial: trial["residual_norm"])
    best_sequence = min(
        sequence_rows, key=lambda row: row["best_targeted_three_free_residual_norm"]
    )
    worst_sequence = max(
        sequence_rows, key=lambda row: row["best_targeted_three_free_residual_norm"]
    )
    accepted_removed = 0
    targeted_proxy_t_pressure = 60
    candidate_found = exact_pass_count > 0
    summary = {
        "source_semantic_packet_method": semantic.get("method"),
        "source_orientation_census_method": census.get("method"),
        "source_grid_snap_pricing_method": grid_snap.get("method"),
        "source_two_free_pricing_method": two_free.get("method"),
        "target_line_number": TARGET_LINE,
        "union_window": [
            int(packet["window_start_line"]),
            int(packet["window_end_line"]),
        ],
        "support_qubits": packet["support_qubits"],
        "source_cnot_count": int(packet["cx_count"]),
        "searched_cnot_count": 2,
        "orientation_sequence_count": len(sequence_rows),
        "orientation_sequence_ids": [row["sequence_id"] for row in sequence_rows],
        "targeted_three_free_trial_count": len(trial_rows),
        "targeted_three_free_exact_pass_count": exact_pass_count,
        "targeted_three_free_exact_fail_count": len(trial_rows) - exact_pass_count,
        "all_targeted_three_free_trials_fail": exact_pass_count == 0,
        "best_targeted_three_free_sequence_id": best_sequence["sequence_id"],
        "best_targeted_three_free_parameter_triple": best_trial["free_parameter_triple"],
        "best_targeted_three_free_residual_norm": best_trial["residual_norm"],
        "best_targeted_three_free_residual_ratio_to_exact_tolerance": best_trial[
            "residual_ratio_to_exact_tolerance"
        ],
        "worst_best_sequence_id": worst_sequence["sequence_id"],
        "worst_best_sequence_residual_norm": worst_sequence[
            "best_targeted_three_free_residual_norm"
        ],
        "targeted_three_free_proxy_t_pressure_if_accepted": targeted_proxy_t_pressure,
        "two_free_proxy_t_pressure_if_accepted": two_free["summary"][
            "two_free_proxy_t_pressure_if_accepted"
        ],
        "current_line1381_proxy_t_pressure": grid_snap["summary"][
            "current_line1381_proxy_t_pressure"
        ],
        "best_source_proxy_t_pressure": grid_snap["summary"]["best_source_proxy_t_pressure"],
        "targeted_three_free_pricing_candidate_found": candidate_found,
        "targeted_three_free_pricing_accepted": False,
        "local_u3_pricing_completed": False,
        "accepted_full_circuit_replay_certificate_count": 0,
        "accepted_full_circuit_qasm_patch_count": 0,
        "accepted_occurrence_removal": accepted_removed,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": max(0, REQUIRED_OCCURRENCE_REMOVALS - accepted_removed),
        "missing_proxy_t_after_gate": max(
            0,
            (REQUIRED_OCCURRENCE_REMOVALS - accepted_removed) * PROXY_T_PER_OCCURRENCE,
        ),
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "probe_scope": "best_two_free_pair_plus_one_parameter_per_sequence",
        "probe_exhaustive_for_three_free": False,
    }
    payload = {
        "benchmark_id": "B1",
        "linked_b7_problem_id": 21,
        "method": METHOD,
        "status": STATUS_CANDIDATE if candidate_found else STATUS_REJECTED,
        "model_status": MODEL_CANDIDATE if candidate_found else MODEL_REJECTED,
        "workload": "qasmbench_medium_exact/gcm_h6.qasm",
        "source_semantic_packet_result": display_path(SEMANTIC_PACKET_PATH),
        "source_orientation_census_result": display_path(ORIENTATION_CENSUS_PATH),
        "source_grid_snap_pricing_result": display_path(GRID_SNAP_PATH),
        "source_two_free_pricing_result": display_path(TWO_FREE_PATH),
        "summary": summary,
        "union_region_targeted_three_free_sequence_rows": sequence_rows,
        "union_region_targeted_three_free_trial_rows": trial_rows,
        "claim_boundary": {
            "supported_claim": (
                "Within the T-B1-004bf union-region two-CNOT census candidates, "
                "this targeted probe expands each sequence's best failed two-free "
                "pair by one additional free local-U3 parameter."
            ),
            "unsupported_claims": [
                "This is not an exhaustive three-free-parameter lower bound.",
                "A local exact targeted-three-free candidate, if present, is not a full-circuit replay certificate.",
                "This does not accept occurrence removal, proxy-T reduction, or a B7 ledger improvement.",
            ],
            "targeted_three_free_pricing_accepted": False,
            "local_u3_pricing_completed": False,
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
    }
    payload["summary"]["validation_error_count"] = len(validate_payload(payload))
    return payload


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = payload.get("summary", {})
    sequence_rows = payload.get("union_region_targeted_three_free_sequence_rows", [])
    trial_rows = payload.get("union_region_targeted_three_free_trial_rows", [])
    expected = {
        "target_line_number": 1381,
        "union_window": [1369, 1379],
        "support_qubits": [4, 8],
        "source_cnot_count": 5,
        "searched_cnot_count": 2,
        "orientation_sequence_count": 4,
        "orientation_sequence_ids": ["01-01", "01-10", "10-01", "10-10"],
        "targeted_three_free_trial_count": 64,
        "targeted_three_free_pricing_accepted": False,
        "local_u3_pricing_completed": False,
        "accepted_full_circuit_replay_certificate_count": 0,
        "accepted_full_circuit_qasm_patch_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": 30,
        "missing_proxy_t_after_gate": 600,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "probe_scope": "best_two_free_pair_plus_one_parameter_per_sequence",
        "probe_exhaustive_for_three_free": False,
    }
    if payload.get("benchmark_id") != "B1":
        errors.append("benchmark_id_mismatch")
    if payload.get("method") != METHOD:
        errors.append("method_mismatch")
    if payload.get("status") not in {STATUS_REJECTED, STATUS_CANDIDATE}:
        errors.append("status_mismatch")
    if payload.get("model_status") not in {MODEL_REJECTED, MODEL_CANDIDATE}:
        errors.append("model_status_mismatch")
    for key, value in expected.items():
        if summary.get(key) != value:
            errors.append(f"summary_{key}_expected_{value!r}_got_{summary.get(key)!r}")
    if len(sequence_rows) != 4:
        errors.append(f"sequence_row_count_expected_4_got_{len(sequence_rows)}")
    if len(trial_rows) != 64:
        errors.append(f"trial_row_count_expected_64_got_{len(trial_rows)}")
    exact_count = sum(1 for trial in trial_rows if trial.get("exact_pass"))
    if summary.get("targeted_three_free_exact_pass_count") != exact_count:
        errors.append("exact_pass_count_mismatch")
    if summary.get("targeted_three_free_exact_fail_count") != len(trial_rows) - exact_count:
        errors.append("exact_fail_count_mismatch")
    if summary.get("all_targeted_three_free_trials_fail") != (exact_count == 0):
        errors.append("all_targeted_three_free_trials_fail_mismatch")
    if summary.get("targeted_three_free_pricing_candidate_found") != (exact_count > 0):
        errors.append("candidate_found_mismatch")
    claims = payload.get("claim_boundary", {})
    for field in [
        "targeted_three_free_pricing_accepted",
        "local_u3_pricing_completed",
        "resource_saving_claimed",
        "b7_ledger_improvement_claimed",
    ]:
        if claims.get(field) is not False:
            errors.append(f"claim_boundary_{field}_not_false")
    return errors


def markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# B1/B7 cone_01 Union-Region Targeted Three-Free Expansion Pricing Gate",
        "",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Model status: `{payload['model_status']}`",
        f"- Workload: `{payload['workload']}`",
        f"- Union window: `{summary['union_window']}`",
        f"- Support qubits: `{summary['support_qubits']}`",
        f"- Probe scope: `{summary['probe_scope']}`",
        f"- Exhaustive for three-free search: `{summary['probe_exhaustive_for_three_free']}`",
        f"- Orientation sequences: `{summary['orientation_sequence_ids']}`",
        f"- Targeted three-free trials: `{summary['targeted_three_free_trial_count']}`",
        f"- Exact pass / fail: `{summary['targeted_three_free_exact_pass_count']}` / `{summary['targeted_three_free_exact_fail_count']}`",
        f"- Best targeted three-free residual: `{summary['best_targeted_three_free_residual_norm']}`",
        f"- Best sequence / parameter triple: `{summary['best_targeted_three_free_sequence_id']}` / `{summary['best_targeted_three_free_parameter_triple']}`",
        f"- Worst best-sequence residual: `{summary['worst_best_sequence_residual_norm']}`",
        f"- Targeted three-free proxy-T pressure if accepted: `{summary['targeted_three_free_proxy_t_pressure_if_accepted']}`",
        f"- Current line-1381 proxy-T pressure: `{summary['current_line1381_proxy_t_pressure']}`",
        f"- Targeted candidate found: `{summary['targeted_three_free_pricing_candidate_found']}`",
        f"- B7 ledger improvement claimed: `{summary['b7_ledger_improvement_claimed']}`",
        "",
        "## Claim Boundary",
        "",
        payload["claim_boundary"]["supported_claim"],
        "",
        "Unsupported claims:",
    ]
    for claim in payload["claim_boundary"]["unsupported_claims"]:
        lines.append(f"- {claim}")
    lines.extend(["", "## Sequence Best Rows", ""])
    for row in payload["union_region_targeted_three_free_sequence_rows"]:
        lines.append(
            "- "
            f"`{row['sequence_id']}`: base pair `{row['base_two_free_parameter_pair']}`, "
            f"best triple `{row['best_targeted_three_free_parameter_triple']}`, "
            f"residual `{row['best_targeted_three_free_residual_norm']}`, "
            f"exact passes `{row['targeted_three_free_exact_pass_count']}` / `{row['targeted_three_free_trial_count']}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, default=JSON_OUT)
    parser.add_argument("--markdown-output", type=Path, default=MD_OUT)
    parser.add_argument("--max-nfev", type=int, default=DEFAULT_MAX_NFEV)
    args = parser.parse_args()

    payload = run_probe(args.max_nfev)
    errors = validate_payload(payload)
    if errors:
        raise SystemExit("validation failed: " + "; ".join(errors))
    write_json(args.json_output, payload, True)
    write_text(args.markdown_output, markdown_report(payload))
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
