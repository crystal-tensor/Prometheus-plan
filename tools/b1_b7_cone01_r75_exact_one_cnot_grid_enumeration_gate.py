#!/usr/bin/env python3
"""T-B1-004fy/T-B7-015h: exact one-CNOT pi/4-grid enumeration.

R74 used seeded optimization over the discrete grid.  R75 makes the one-CNOT
case auditable: every pi/4-grid local pair class is enumerated as the right
layer, and the left layer is derived algebraically and checked against the
same complete pair-class table.  Global phase classes are safe to quotient
because the local factors can absorb the phase.

This is a complete result for the declared one-CNOT, pi/4-grid scaffold.  It
is not a full-circuit rewrite and does not claim that the B1/B7 problem is
solved until the candidate survives source-aligned replay and FT accounting.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np

from b1_b7_cone01_packet_synthesis_search_gate import (
    EXACT_TOLERANCE,
    cx_on,
    phase_align,
    target_matrix,
    u3,
)
from b7_ft_synthesis_ledger import rotation_cost


METHOD = "b1_b7_cone01_r75_exact_one_cnot_grid_enumeration_gate_v0"
STATUS = "cone01_r75_line1378_exact_one_cnot_grid_candidate_boundary"
MODEL_STATUS = "one_cnot_pi_over_four_grid_candidate_found_for_line1378_only"
VERSION = "0.1"
TARGET_ID = "T-B1-004fy/T-B7-015h"
UPSTREAM_TARGET_ID = "T-B1-004fx/T-B7-015g"
SEMANTIC_PACKET = "results/B1_B7_cone01_semantic_replay_packet_gate_v0.json"
R74_RESULT = "results/B1_B7_cone01_R74_grid_scaffold_pressure_gate_v0.json"
GRID_DENOMINATOR = 4
GRID_POINTS = tuple(range(8))
ONE_CNOT_ORIENTATIONS = ((0, 1), (1, 0))


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def req(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def cost_args() -> SimpleNamespace:
    return SimpleNamespace(
        pi_over_4_t_cost=1,
        pi_over_8_t_cost=4,
        arbitrary_rotation_t_cost=20,
        unknown_rotation_t_cost=20,
    )


def canonical_key(matrix: np.ndarray, digits: int = 9) -> tuple[tuple[float, float], ...]:
    flat = matrix.ravel()
    anchor = next((value for value in flat if abs(value) > 1e-10), 1.0 + 0.0j)
    normalized = matrix * np.exp(-1j * np.angle(anchor))
    return tuple(
        (round(float(value.real), digits), round(float(value.imag), digits))
        for value in normalized.ravel()
    )


def source_rotation_cost(packet: dict[str, Any], args: SimpleNamespace) -> dict[str, Any]:
    total = 0
    families: dict[str, int] = {}
    for operation in packet["normalized_ops"]:
        if operation["gate"] == "cx":
            continue
        cost, family = rotation_cost(operation["raw_args"][0], args)
        total += cost
        families[family] = families.get(family, 0) + 1
    return {"rotation_cost": total, "rotation_family_counts": dict(sorted(families.items()))}


def grid_rotation_cost(values: list[int], args: SimpleNamespace) -> dict[str, Any]:
    total = 0
    families: dict[str, int] = {}
    for value in values:
        cost, family = rotation_cost(f"{int(value)}/{GRID_DENOMINATOR}*pi", args)
        total += cost
        families[family] = families.get(family, 0) + 1
    return {
        "rotation_cost": total,
        "rotation_family_counts": dict(sorted(families.items())),
        "parameter_count": len(values),
        "arbitrary_parameter_count": 0,
    }


def build_pair_classes() -> dict[str, Any]:
    single_rows = []
    for values in itertools.product(GRID_POINTS, repeat=3):
        single_rows.append(
            {
                "values": list(values),
                "matrix": u3(*(value * math.pi / GRID_DENOMINATOR for value in values)),
            }
        )
    single_keys = {canonical_key(row["matrix"]) for row in single_rows}
    pair_rows_by_key: dict[tuple[tuple[float, float], ...], dict[str, Any]] = {}
    for left in single_rows:
        for right in single_rows:
            matrix = np.kron(left["matrix"], right["matrix"])
            key = canonical_key(matrix)
            pair_rows_by_key.setdefault(
                key,
                {
                    "left_values": left["values"],
                    "right_values": right["values"],
                    "matrix": matrix,
                },
            )
    return {
        "single_parameterization_count": len(single_rows),
        "single_global_phase_class_count": len(single_keys),
        "pair_parameterization_count": len(single_rows) * len(single_rows),
        "pair_global_phase_class_count": len(pair_rows_by_key),
        "pair_rows_by_key": pair_rows_by_key,
    }


def match_orientation(
    packet: dict[str, Any],
    target: np.ndarray,
    orientation: tuple[int, int],
    pair_rows_by_key: dict[tuple[tuple[float, float], ...], dict[str, Any]],
    args: SimpleNamespace,
) -> dict[str, Any]:
    cnot = cx_on(*orientation)
    exact_matches: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    for right_key, right in pair_rows_by_key.items():
        del right_key
        left_candidate = target @ (cnot @ right["matrix"]).conj().T
        left_key = canonical_key(left_candidate)
        left = pair_rows_by_key.get(left_key)
        if left is None:
            continue
        candidate = left["matrix"] @ cnot @ right["matrix"]
        residual = float(np.linalg.norm(phase_align(candidate, target) - target))
        if residual > EXACT_TOLERANCE:
            continue
        values = left["left_values"] + left["right_values"] + right["left_values"] + right["right_values"]
        row = {
            "cnot_count": 1,
            "cnot_sequence": [[orientation[0], orientation[1]]],
            "sequence_id": f"{orientation[0]}{orientation[1]}",
            "residual_norm": residual,
            "max_abs_entry_error": float(np.max(np.abs(phase_align(candidate, target) - target))),
            "left_pair_values": left["left_values"] + left["right_values"],
            "right_pair_values": right["left_values"] + right["right_values"],
            "all_grid_values": values,
            "candidate_rotation_cost": grid_rotation_cost(values, args),
        }
        exact_matches.append(row)
        if best is None or (
            row["candidate_rotation_cost"]["rotation_cost"],
            row["residual_norm"],
            row["sequence_id"],
            row["all_grid_values"],
        ) < (
            best["candidate_rotation_cost"]["rotation_cost"],
            best["residual_norm"],
            best["sequence_id"],
            best["all_grid_values"],
        ):
            best = row
    exact_matches.sort(
        key=lambda row: (
            row["candidate_rotation_cost"]["rotation_cost"],
            row["residual_norm"],
            row["sequence_id"],
            row["all_grid_values"],
        )
    )
    return {
        "orientation": list(orientation),
        "sequence_id": f"{orientation[0]}{orientation[1]}",
        "raw_right_parameterization_count": 512 * 512,
        "right_global_phase_class_count": len(pair_rows_by_key),
        "class_enumeration_complete": True,
        "exact_match_count": len(exact_matches),
        "best_exact_by_cost": best,
        "exact_matches": exact_matches,
    }


def analyze_packet(
    packet: dict[str, Any],
    pair_data: dict[str, Any],
    args: SimpleNamespace,
) -> dict[str, Any]:
    target = target_matrix(packet)
    orientation_rows = [
        match_orientation(packet, target, orientation, pair_data["pair_rows_by_key"], args)
        for orientation in ONE_CNOT_ORIENTATIONS
    ]
    exact_rows = [
        row["best_exact_by_cost"]
        for row in orientation_rows
        if row["best_exact_by_cost"] is not None
    ]
    best_exact = min(
        exact_rows,
        key=lambda row: (
            row["candidate_rotation_cost"]["rotation_cost"],
            row["residual_norm"],
            row["sequence_id"],
        ),
    ) if exact_rows else None
    source_cost = source_rotation_cost(packet, args)
    return {
        "candidate_line_number": int(packet["candidate_line_number"]),
        "pattern_id": packet["pattern_id"],
        "source_cnot_count": int(packet["cx_count"]),
        "source_rotation_cost": source_cost,
        "orientation_count": len(orientation_rows),
        "raw_right_parameterization_count_per_orientation": 512 * 512,
        "global_phase_class_count_per_orientation": pair_data["pair_global_phase_class_count"],
        "total_raw_right_parameterization_count": 2 * 512 * 512,
        "total_class_evaluation_count": 2 * pair_data["pair_global_phase_class_count"],
        "exact_match_count": sum(row["exact_match_count"] for row in orientation_rows),
        "best_exact_by_cost": best_exact,
        "best_exact_rotation_cost": (
            best_exact["candidate_rotation_cost"]["rotation_cost"] if best_exact else None
        ),
        "source_minus_best_exact_rotation_cost": (
            source_cost["rotation_cost"] - best_exact["candidate_rotation_cost"]["rotation_cost"]
            if best_exact
            else None
        ),
        "cnot_reduction": (
            int(packet["cx_count"]) - best_exact["cnot_count"] if best_exact else 0
        ),
        "orientation_rows": orientation_rows,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "accepted_full_circuit_replay_certificate_count": 0,
    }


def build_payload(root: Path) -> dict[str, Any]:
    started = time.time()
    semantic_path = root / SEMANTIC_PACKET
    r74_path = root / R74_RESULT
    semantic = load_json(semantic_path)
    r74 = load_json(r74_path)
    args = cost_args()
    pair_data = build_pair_classes()
    rows = [
        analyze_packet(packet, pair_data, args)
        for packet in semantic["semantic_replay_packets"]
    ]
    exact_packet_count = sum(1 for row in rows if row["best_exact_by_cost"] is not None)
    cost_improving_packet_count = sum(
        1
        for row in rows
        if row["source_minus_best_exact_rotation_cost"] is not None
        and row["source_minus_best_exact_rotation_cost"] > 0
    )
    requirements = [
        req(
            "R1",
            "Three source semantic replay packets are available",
            len(rows) == 3,
            {"packet_count": len(rows), "source_method": semantic["method"]},
        ),
        req(
            "R2",
            "R74 upstream remains a verified grid pressure boundary",
            r74["summary"]["requirements_failed"] == 0
            and r74["summary"]["exact_solution_count"] == 0,
            {
                "r74_requirements_failed": r74["summary"]["requirements_failed"],
                "r74_exact_solution_count": r74["summary"]["exact_solution_count"],
            },
        ),
        req(
            "R3",
            "The pi/4 grid model is pinned",
            GRID_DENOMINATOR == 4 and GRID_POINTS == tuple(range(8)),
            {"grid_denominator": GRID_DENOMINATOR, "grid_point_count": len(GRID_POINTS)},
        ),
        req(
            "R4",
            "The one-CNOT pair-class enumeration is complete",
            pair_data["single_parameterization_count"] == 512
            and pair_data["pair_parameterization_count"] == 262144
            and pair_data["pair_global_phase_class_count"] == 43264
            and all(row["orientation_count"] == 2 for row in rows)
            and all(
                all(orientation["class_enumeration_complete"] for orientation in row["orientation_rows"])
                for row in rows
            ),
            {
                "single_parameterization_count": pair_data["single_parameterization_count"],
                "single_global_phase_class_count": pair_data["single_global_phase_class_count"],
                "pair_parameterization_count": pair_data["pair_parameterization_count"],
                "pair_global_phase_class_count": pair_data["pair_global_phase_class_count"],
                "orientations_per_packet": [row["orientation_count"] for row in rows],
            },
        ),
        req(
            "R5",
            "The complete one-CNOT enumeration finds an exact grid candidate for line 1378",
            rows[0]["exact_match_count"] > 0
            and rows[0]["best_exact_by_cost"] is not None
            and rows[0]["best_exact_by_cost"]["candidate_rotation_cost"]["rotation_cost"] == 3
            and rows[0]["best_exact_by_cost"]["residual_norm"] <= EXACT_TOLERANCE,
            {
                "line1378_exact_match_count": rows[0]["exact_match_count"],
                "line1378_best_exact_rotation_cost": rows[0]["best_exact_rotation_cost"],
                "line1378_best_exact_residual": (
                    rows[0]["best_exact_by_cost"]["residual_norm"]
                    if rows[0]["best_exact_by_cost"]
                    else None
                ),
            },
        ),
        req(
            "R6",
            "The other two semantic packets remain one-CNOT grid-negative",
            rows[1]["exact_match_count"] == 0 and rows[2]["exact_match_count"] == 0,
            {
                "line1381_exact_match_count": rows[1]["exact_match_count"],
                "line268_exact_match_count": rows[2]["exact_match_count"],
            },
        ),
        req(
            "R7",
            "The local candidate is not promoted to B7 credit",
            all(row["accepted_occurrence_removal"] == 0 for row in rows)
            and all(row["accepted_proxy_t_reduction"] == 0 for row in rows)
            and all(row["accepted_full_circuit_replay_certificate_count"] == 0 for row in rows),
            {
                "accepted_occurrence_removal": 0,
                "accepted_proxy_t_reduction": 0,
                "accepted_full_circuit_replay_certificate_count": 0,
            },
        ),
        req(
            "R8",
            "The exact candidate and source-cost comparison are serialized",
            exact_packet_count == 1
            and cost_improving_packet_count == 1
            and rows[0]["cnot_reduction"] == 3,
            {
                "exact_packet_count": exact_packet_count,
                "cost_improving_packet_count": cost_improving_packet_count,
                "line1378_cnot_reduction": rows[0]["cnot_reduction"],
            },
        ),
    ]
    summary = {
        "packet_count": len(rows),
        "grid_denominator": GRID_DENOMINATOR,
        "grid_point_count_per_parameter": len(GRID_POINTS),
        "single_parameterization_count": pair_data["single_parameterization_count"],
        "single_global_phase_class_count": pair_data["single_global_phase_class_count"],
        "pair_parameterization_count": pair_data["pair_parameterization_count"],
        "pair_global_phase_class_count": pair_data["pair_global_phase_class_count"],
        "orientations_per_packet": len(ONE_CNOT_ORIENTATIONS),
        "total_raw_right_parameterization_count_per_packet": 2 * 512 * 512,
        "total_class_evaluation_count_per_packet": 2 * pair_data["pair_global_phase_class_count"],
        "exact_match_count_by_packet": [row["exact_match_count"] for row in rows],
        "exact_packet_count": exact_packet_count,
        "cost_improving_packet_count": cost_improving_packet_count,
        "source_minus_best_exact_rotation_cost": [
            row["source_minus_best_exact_rotation_cost"] for row in rows
        ],
        "cnot_reduction_by_packet": [row["cnot_reduction"] for row in rows],
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "accepted_full_circuit_replay_certificate_count": 0,
        "accepted_exit_route_count": 0,
        "b7_credit_delta": 0,
        "requirements_passed": sum(1 for item in requirements if item["passed"]),
        "requirements_failed": sum(1 for item in requirements if not item["passed"]),
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "full_circuit_replay_claimed": False,
        "runtime_seconds": round(time.time() - started, 6),
    }
    payload: dict[str, Any] = {
        "benchmark_id": "B1",
        "linked_b7_problem_id": 21,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "version": VERSION,
        "target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_semantic_packet": rel(root, semantic_path),
        "source_semantic_packet_sha256": file_hash(semantic_path),
        "source_r74_result": rel(root, r74_path),
        "source_r74_result_sha256": file_hash(r74_path),
        "grid_model": {
            "angle_expression": "k*pi/4",
            "k_values": list(GRID_POINTS),
            "one_cnot_orientations": [[control, target] for control, target in ONE_CNOT_ORIENTATIONS],
            "global_phase_quotient": True,
            "enumeration_mode": "derive_left_local_factor_from_each_right_pair_class",
        },
        "requirements": requirements,
        "summary": summary,
        "packet_rows": rows,
        "claim_boundary": {
            "supported_claim": (
                "A complete one-CNOT enumeration of the declared pi/4-grid local pair classes "
                "finds exact candidates for line 1378, including a best local rotation cost of "
                "3 versus source cost 5, while lines 1381 and 268 have no exact one-CNOT grid match."
            ),
            "unsupported_claims": [
                "This is not a full-circuit rewrite or source-aligned replay certificate.",
                "This does not establish a global Clifford+T lower bound or solve B1/B7.",
                "This does not accept occurrence removal, proxy-T reduction, reroute, or B7 credit.",
            ],
            "full_circuit_replay_claimed": False,
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
    }
    payload["payload_hash"] = stable_hash(payload)
    return payload


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    best = payload["packet_rows"][0]["best_exact_by_cost"]
    lines = [
        "# B1/B7 Cone01 R75 Exact One-CNOT Grid Enumeration Gate",
        "",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Requirements: `{summary['requirements_passed']}/{len(payload['requirements'])}`",
        f"- Raw right-layer parameterizations per orientation: `{summary['pair_parameterization_count']}`",
        f"- Unique right-layer global-phase classes: `{summary['pair_global_phase_class_count']}`",
        f"- Exact matches by packet: `{summary['exact_match_count_by_packet']}`",
        f"- Source minus best exact rotation cost: `{summary['source_minus_best_exact_rotation_cost']}`",
        f"- CNOT reduction by packet: `{summary['cnot_reduction_by_packet']}`",
        f"- Accepted occurrence removal / proxy-T reduction: `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        f"- B7 credit: `{summary['b7_credit_delta']}`",
        "",
        "## Interpretation",
        "",
        "The complete one-CNOT pi/4-grid enumeration finds a local exact candidate for line 1378. Its best local grid cost is 3 against source cost 5, with a three-CNOT local reduction. Lines 1381 and 268 have no exact one-CNOT grid match in the same declared class. The line-1378 result is now a concrete candidate for source-aligned full-circuit replay, not yet an accepted B7 saving.",
        "",
        "## Claim Boundary",
        "",
        "- Complete only for the declared one-CNOT pi/4-grid pair-class scaffold.",
        "- No full-circuit rewrite, semantic replay certificate, occurrence removal, proxy-T reduction, reroute, or B7 credit is accepted.",
        "",
        "## Best Line-1378 Candidate",
        "",
        f"- CNOT sequence: `{best['sequence_id']}`",
        f"- Left pair values: `{best['left_pair_values']}`",
        f"- Right pair values: `{best['right_pair_values']}`",
        f"- Residual norm: `{best['residual_norm']}`",
        f"- Grid rotation cost: `{best['candidate_rotation_cost']['rotation_cost']}`",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_R75_exact_one_cnot_grid_enumeration_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_R75_exact_one_cnot_grid_enumeration_gate.md"),
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    payload = build_payload(root)
    json_output = args.json_output if args.json_output.is_absolute() else root / args.json_output
    markdown_output = args.markdown_output if args.markdown_output.is_absolute() else root / args.markdown_output
    write_json(json_output, payload)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(report(payload), encoding="utf-8")
    if args.pretty:
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "requirements_passed": payload["summary"]["requirements_passed"],
                    "requirements_failed": payload["summary"]["requirements_failed"],
                    "pair_global_phase_class_count": payload["summary"]["pair_global_phase_class_count"],
                    "exact_match_count_by_packet": payload["summary"]["exact_match_count_by_packet"],
                    "source_minus_best_exact_rotation_cost": payload["summary"][
                        "source_minus_best_exact_rotation_cost"
                    ],
                    "cnot_reduction_by_packet": payload["summary"]["cnot_reduction_by_packet"],
                    "payload_hash": payload["payload_hash"],
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
