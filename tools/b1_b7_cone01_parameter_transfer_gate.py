#!/usr/bin/env python3
"""Parameter-transfer obligation gate for B1/B7 cone_01.

The previous cone_01 gates closed narrow same-envelope deletion/reabsorption
routes.  This gate asks a prerequisite question for any broader scaffold:
does the target RY(theta) carry nonzero continuous unitary sensitivity, and
are enough theta values already exact/Clifford-like to delete them without a
new parameter carrier?

The output is a guardrail, not a rewrite certificate.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from b1_b7_cone01_phase_removal_gate import (
    angle_from_params,
    phase_align,
    residual_norm,
    target_rows,
    unitary_for_ops,
)


METHOD = "b1_b7_cone01_parameter_transfer_gate_v0"
STATUS = "cone01_parameter_transfer_obligation_gate"
MODEL_STATUS = "parameter_sensitivity_guardrail_not_rewrite_certificate"
VERSION = "0.1"
EXACT_TOLERANCE = 1e-8
SENSITIVITY_THRESHOLD = 1e-6
ANGLE_GROUP_TOLERANCE_DECIMALS = 12
PROXY_T_COST_PER_ARBITRARY_ROTATION = 20


def display_path(path: Path) -> str:
    root = Path(__file__).resolve().parents[1]
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(root))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: dict, pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def canonical_angle(theta: float) -> float:
    value = (theta + math.pi) % (2.0 * math.pi) - math.pi
    return round(value, ANGLE_GROUP_TOLERANCE_DECIMALS)


def distance_to_pi_over_four_grid(theta: float) -> tuple[float, str, float]:
    candidates = []
    for k in range(-8, 9):
        grid_angle = k * math.pi / 4.0
        diff = (theta - grid_angle + math.pi) % (2.0 * math.pi) - math.pi
        candidates.append((abs(diff), f"{k}*pi/4", grid_angle))
    return min(candidates, key=lambda item: item[0])


def clone_window_with_theta(window: list[dict], ry_op_index: int, theta: float) -> list[dict]:
    output = []
    for op in window:
        clone = dict(op)
        if op["op_index"] == ry_op_index:
            clone["params"] = f"{theta:.17g}"
            clone["text"] = f"ry({theta:.17g}) q[{op['qubits'][0]}];"
        output.append(clone)
    return output


def projective_sensitivity(window: list[dict], row: dict, local_qubits: list[int], theta: float) -> dict:
    target = unitary_for_ops(window, local_qubits)
    eps = 1e-6
    plus = unitary_for_ops(clone_window_with_theta(window, row["op_index"], theta + eps), local_qubits)
    minus = unitary_for_ops(clone_window_with_theta(window, row["op_index"], theta - eps), local_qubits)
    aligned_plus = phase_align(plus, target)
    aligned_minus = phase_align(minus, target)
    derivative = (aligned_plus - aligned_minus) / (2.0 * eps)
    return {
        "finite_difference_eps": eps,
        "projective_derivative_norm": float(np.linalg.norm(derivative)),
        "plus_residual_per_eps": residual_norm(plus, target) / eps,
        "minus_residual_per_eps": residual_norm(minus, target) / eps,
    }


def analyze_window(ops: list[dict], row: dict) -> dict:
    local_qubits = [row["previous_cx_partner"], row["qubit"]]
    window = ops[row["previous_cx_index"] : row["next_cx_index"] + 1]
    theta = angle_from_params(row["params"])
    grid_distance, grid_label, grid_angle = distance_to_pi_over_four_grid(theta)
    sensitivity = projective_sensitivity(window, row, local_qubits, theta)
    nonzero = sensitivity["projective_derivative_norm"] > SENSITIVITY_THRESHOLD
    return {
        "line_number": row["line_number"],
        "op_index": row["op_index"],
        "qubit": row["qubit"],
        "partner": row["previous_cx_partner"],
        "original_ry_params": row["params"],
        "theta": theta,
        "canonical_theta": canonical_angle(theta),
        "nearest_pi_over_four_label": grid_label,
        "nearest_pi_over_four_angle": grid_angle,
        "distance_to_pi_over_four_grid": grid_distance,
        "near_pi_over_four_grid": grid_distance <= EXACT_TOLERANCE,
        "window_operation_count": len(window),
        "previous_cx_line": row["previous_cx_line"],
        "next_cx_line": row["next_cx_line"],
        "window_text": [op["text"] for op in window],
        "parameter_sensitivity": sensitivity,
        "nonzero_parameter_sensitivity": nonzero,
        "deletion_without_parameter_carrier_admissible": False,
    }


def angle_groups(rows: list[dict]) -> list[dict]:
    grouped: dict[float, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["canonical_theta"]].append(row)
    output = []
    for theta, members in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        output.append(
            {
                "canonical_theta": theta,
                "occurrence_count": len(members),
                "line_numbers": [row["line_number"] for row in members],
                "nearest_pi_over_four_label": members[0]["nearest_pi_over_four_label"],
                "min_distance_to_pi_over_four_grid": min(row["distance_to_pi_over_four_grid"] for row in members),
            }
        )
    return output


def build_payload(args: argparse.Namespace) -> dict:
    ops, rows = target_rows(args)
    analyses = [analyze_window(ops, row) for row in rows]
    groups = angle_groups(analyses)
    nonzero_count = sum(1 for row in analyses if row["nonzero_parameter_sensitivity"])
    near_grid_count = sum(1 for row in analyses if row["near_pi_over_four_grid"])
    deletion_without_carrier_clears_target = (
        nonzero_count < args.required_windows or near_grid_count >= args.required_windows
    )
    largest_repeated_group = max((group["occurrence_count"] for group in groups), default=0)
    repeated_occurrences = sum(group["occurrence_count"] for group in groups if group["occurrence_count"] > 1)
    summary = {
        "target_cone_id": args.cone_id,
        "candidate_window_count": len(analyses),
        "required_exact_windows_for_b7_target": args.required_windows,
        "target_proxy_t_ledger_reduction_for_gcm_h6_1_20": args.required_windows
        * PROXY_T_COST_PER_ARBITRARY_ROTATION,
        "nonzero_parameter_sensitivity_count": nonzero_count,
        "parameter_sensitivity_zero_count": len(analyses) - nonzero_count,
        "near_pi_over_four_grid_count": near_grid_count,
        "distinct_canonical_theta_count": len(groups),
        "largest_repeated_theta_group": largest_repeated_group,
        "repeated_theta_occurrence_count": repeated_occurrences,
        "minimum_parameter_carrier_obligation_for_b7_target": args.required_windows,
        "deletion_without_parameter_carrier_clears_b7_target": deletion_without_carrier_clears_target,
        "rewrite_claimed": False,
        "resource_saving_claimed": False,
        "semantic_certificate_claimed": False,
        "obstruction_theorem_claimed": False,
        "validation_error_count": None,
    }
    payload = {
        "benchmark_id": "B1",
        "problem_id": 25,
        "linked_b7_problem_id": 21,
        "title": "B1/B7 cone_01 parameter-transfer obligation gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "method": METHOD,
        "source_qasm": display_path(args.qasm),
        "source_selector": display_path(args.selector),
        "source_feasibility_gate": display_path(args.feasibility),
        "source_phase_removal_gate": display_path(args.phase_removal),
        "source_euler_reabsorption_gate": display_path(args.euler_reabsorption),
        "workload": "qasmbench_medium_exact/gcm_h6.qasm",
        "summary": summary,
        "angle_groups": groups,
        "top_windows_by_parameter_sensitivity": sorted(
            analyses,
            key=lambda item: item["parameter_sensitivity"]["projective_derivative_norm"],
            reverse=True,
        )[: args.report_limit],
        "top_angle_groups": groups[: args.report_limit],
        "claim_boundary": {
            "rewrite_claimed": False,
            "resource_saving_claimed": False,
            "semantic_certificate_claimed": False,
            "obstruction_theorem_claimed": False,
            "physical_layout_claimed": False,
            "supported_claim": (
                "The cone_01 RY(theta) occurrences carry nonzero local unitary sensitivity, "
                "so a deletion route must either carry theta elsewhere, prove exact special-angle "
                "identities, or show certified cross-window parameter sharing before B7 can count savings."
            ),
            "unsupported_claims": [
                "No local rewrite certificate is produced.",
                "No KAK lower bound or global obstruction theorem is proved.",
                "No B7 FT ledger improvement is counted.",
                "Repeated theta groups are not counted as physical resource savings without certificates.",
            ],
            "next_gate": (
                "Run a broader two-qubit synthesis/KAK scaffold only on routes that explicitly account "
                "for the theta carrier and preserve or reduce the arbitrary-rotation ledger."
            ),
        },
    }
    errors = validate(payload)
    payload["summary"]["validation_error_count"] = len(errors)
    payload["validation_errors"] = errors
    return payload


def validate(payload: dict) -> list[str]:
    errors = []
    summary = payload["summary"]
    if payload.get("method") != METHOD:
        errors.append("method mismatch")
    if payload.get("status") != STATUS:
        errors.append("status mismatch")
    if summary["candidate_window_count"] < summary["required_exact_windows_for_b7_target"]:
        errors.append("candidate window count should cover the B7 target")
    if summary["nonzero_parameter_sensitivity_count"] != summary["candidate_window_count"]:
        errors.append("all cone_01 candidate windows should carry nonzero parameter sensitivity")
    if summary["near_pi_over_four_grid_count"] >= summary["required_exact_windows_for_b7_target"]:
        errors.append("too many cone_01 windows appear exact-grid removable; review route")
    if summary["deletion_without_parameter_carrier_clears_b7_target"]:
        errors.append("deletion without a parameter carrier should not clear the B7 target")
    for field in [
        "rewrite_claimed",
        "resource_saving_claimed",
        "semantic_certificate_claimed",
        "obstruction_theorem_claimed",
    ]:
        if summary[field] is not False:
            errors.append(f"{field} must remain false")
    boundary = payload.get("claim_boundary", {})
    for field in [
        "rewrite_claimed",
        "resource_saving_claimed",
        "semantic_certificate_claimed",
        "obstruction_theorem_claimed",
        "physical_layout_claimed",
    ]:
        if boundary.get(field) is not False:
            errors.append(f"claim boundary {field} must remain false")
    return errors


def markdown(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone_01 Parameter-Transfer Obligation Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This artifact checks a prerequisite for any broader cone_01 rewrite. "
        "The previous gates showed that direct deletion, phase replacement, and "
        "same-envelope Euler reabsorption do not produce exact windows. This gate "
        "asks whether the original `RY(theta)` occurrences carry nonzero continuous "
        "unitary sensitivity and whether enough angles are already exact-grid angles.",
        "",
        "It is a guardrail only. It is not a rewrite certificate, not a KAK lower "
        "bound, not a B7 resource saving, and not a physical-layout claim.",
        "",
        "## Summary",
        "",
        f"- Candidate windows: `{summary['candidate_window_count']}`",
        f"- Required exact windows for the B7 target: `{summary['required_exact_windows_for_b7_target']}`",
        f"- Nonzero parameter-sensitivity windows: `{summary['nonzero_parameter_sensitivity_count']}`",
        f"- Near pi/4-grid windows: `{summary['near_pi_over_four_grid_count']}`",
        f"- Distinct canonical theta values: `{summary['distinct_canonical_theta_count']}`",
        f"- Largest repeated theta group: `{summary['largest_repeated_theta_group']}`",
        f"- Repeated theta occurrences: `{summary['repeated_theta_occurrence_count']}`",
        f"- Deletion without a parameter carrier clears B7 target: `{summary['deletion_without_parameter_carrier_clears_b7_target']}`",
        f"- Validation errors: `{summary['validation_error_count']}`",
        "",
        "## Top Theta Groups",
        "",
        "| canonical theta | occurrences | nearest pi/4 grid | min distance |",
        "|---:|---:|---|---:|",
    ]
    for group in payload["top_angle_groups"]:
        lines.append(
            "| {canonical_theta} | {occurrence_count} | {nearest_pi_over_four_label} | "
            "{min_distance_to_pi_over_four_grid:.6g} |".format(**group)
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Every checked cone_01 candidate window has nonzero projective sensitivity "
            "to its `RY(theta)` parameter. Therefore a future occurrence-removing "
            "rewrite cannot simply delete theta from the local model. It must either "
            "move theta into another counted parameter, prove enough exact special-angle "
            "identities, or provide certified parameter sharing that actually reduces "
            "the arbitrary-rotation ledger.",
            "",
            "The current evidence does not support any B7 ledger change.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--qasm",
        type=Path,
        default=root / "results" / "b1_u3_phase_factored_optimizer" / "qasmbench_medium_exact" / "gcm_h6.qasm",
    )
    parser.add_argument("--selector", type=Path, default=root / "results" / "B1_B7_gcm_h6_target_selector_v0.json")
    parser.add_argument(
        "--feasibility",
        type=Path,
        default=root / "results" / "B1_B7_gcm_h6_cone_feasibility_gate_v0.json",
    )
    parser.add_argument(
        "--phase-removal",
        type=Path,
        default=root / "results" / "B1_B7_cone01_phase_removal_gate_v0.json",
    )
    parser.add_argument(
        "--euler-reabsorption",
        type=Path,
        default=root / "results" / "B1_B7_cone01_euler_reabsorption_gate_v0.json",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=root / "results" / "B1_B7_cone01_parameter_transfer_gate_v0.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=root / "research" / "B1_B7_cone01_parameter_transfer_gate.md",
    )
    parser.add_argument("--cone-id", default="cone_01")
    parser.add_argument("--required-windows", type=int, default=30)
    parser.add_argument("--report-limit", type=int, default=10)
    parser.add_argument("--last-updated", default="2026-06-18")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    write_text(args.markdown_output, markdown(payload))
    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Wrote {args.json_output}")
        print(f"Wrote {args.markdown_output}")


if __name__ == "__main__":
    main()
