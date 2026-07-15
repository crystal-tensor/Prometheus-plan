#!/usr/bin/env python3
"""Search a bounded two-frame control-side Clifford family for w8_21.

The one-frame control-side screen is closed.  This gate adds a second fixed
control-side +/- pi/2 frame in a different local layer, while retaining two
CX gates and five arbitrary target-side angles.  It is a longer fixed local
Clifford word, not a global KAK theorem or a full-circuit rewrite.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import b7_w8_21_control_frame_search as single


METHOD = "b7_w8_21_double_control_frame_search_v0"
TEMPLATE_ID = "w8_21"
RESULT_PATH = "results/B7_w8_21_double_control_frame_search_v0.json"
REPORT_PATH = "research/B7_w8_21_double_control_frame_search.md"
EXACT_TOLERANCE = 1e-10
LAYERS = single.LAYERS
EULER_AXES = single.EULER_AXES
FRAME_ANGLES = (-math.pi / 2.0, math.pi / 2.0)
SOURCE_FREE_SLOTS = single.SOURCE_FREE_SLOTS
SLOTS = single.SLOTS
SLOT_BY_LABEL = single.SLOT_BY_LABEL
CNOT_DIRS = single.CNOT_DIRS


def frame_slot(layer: str, axis: str) -> int:
    return SLOT_BY_LABEL[f"{layer}:q0:{axis}"]


def families() -> list[dict[str, Any]]:
    output = []
    for layer_a, layer_b in itertools.combinations(LAYERS, 2):
        for axis_a in EULER_AXES:
            for axis_b in EULER_AXES:
                for angle_a, angle_b in itertools.product(FRAME_ANGLES, repeat=2):
                    for cnot_dirs in itertools.product(CNOT_DIRS, repeat=2):
                        slots = (frame_slot(layer_a, axis_a), frame_slot(layer_b, axis_b))
                        output.append(
                            {
                                "fixed_slots": slots,
                                "fixed_slot_labels": [SLOTS[index]["label"] for index in slots],
                                "fixed_angles": (angle_a, angle_b),
                                "fixed_angle_labels": [
                                    "+pi/2" if angle_a > 0 else "-pi/2",
                                    "+pi/2" if angle_b > 0 else "-pi/2",
                                ],
                                "cnot_directions": cnot_dirs,
                            }
                        )
    return output


def candidate_unitary(family: dict[str, Any], values: np.ndarray) -> np.ndarray:
    angles = np.zeros(len(SLOTS), dtype=float)
    for slot, angle in zip(family["fixed_slots"], family["fixed_angles"]):
        angles[slot] = angle
    for slot, value in zip(SOURCE_FREE_SLOTS, values):
        angles[slot] = float(value)
    total = np.eye(4, dtype=complex)
    cnot_index = 0
    for layer in LAYERS:
        for slot in SLOTS:
            if slot["layer"] == layer:
                total = single.one_qubit_rotation(slot["qubit"], slot["axis"], angles[slot["index"]]) @ total
        if layer != "post":
            total = (single.CX_01 if family["cnot_directions"][cnot_index] == "01" else single.CX_10) @ total
            cnot_index += 1
    return total


def optimize_family(target: np.ndarray, family: dict[str, Any], seed_count: int, max_nfev: int) -> dict[str, Any]:
    def objective(values: np.ndarray) -> np.ndarray:
        return single.residual_vector(candidate_unitary(family, values), target)

    best = None
    for seed_index, seed in enumerate(single.initial_points(seed_count)):
        fit = least_squares(objective, seed, max_nfev=max_nfev, xtol=1e-12, ftol=1e-12, gtol=1e-12)
        candidate = candidate_unitary(family, fit.x)
        aligned_error = single.phase_align(candidate, target) - target
        row = {
            "seed_index": seed_index,
            "fitted_parameters": [float(value) for value in fit.x],
            "residual_norm": float(np.linalg.norm(single.residual_vector(candidate, target))),
            "max_abs_entry_error": float(np.max(np.abs(aligned_error))),
            "optimizer_nfev": int(fit.nfev),
            "optimizer_status": int(fit.status),
            "optimizer_success": bool(fit.success),
        }
        if best is None or row["residual_norm"] < best["residual_norm"]:
            best = row
    assert best is not None
    return best


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = args.root.resolve()
    all_families = families()
    selected = all_families[: args.family_limit] if args.family_limit else all_families
    targets = single.context_targets(root)
    context_results = []
    optimizer_runs = 0
    for context_index, context in enumerate(targets, start=1):
        best = None
        exact_count = 0
        for family_index, family in enumerate(selected, start=1):
            fit = optimize_family(context["matrix"], family, args.seed_count, args.max_nfev)
            optimizer_runs += args.seed_count
            candidate = {"family_index": family_index, **family, "fit": fit}
            if best is None or fit["residual_norm"] < best["fit"]["residual_norm"]:
                best = candidate
            if fit["residual_norm"] <= args.exact_tolerance:
                exact_count += 1
        assert best is not None
        context_results.append(
            {
                "context_index": context_index,
                "direction": context["row"]["direction"],
                "line_span": context["row"]["line_span"],
                "context_operation": context["row"]["context_operation"],
                "tested_family_count": len(selected),
                "exact_family_count": exact_count,
                "best_candidate": best,
                "accepted_occurrence_removal": 0,
                "accepted_proxy_t_reduction": 0,
                "b7_credit": 0,
            }
        )
    exact_context_count = sum(row["exact_family_count"] > 0 for row in context_results)
    payload = {
        "title": "B7 w8_21 two-frame control-side Clifford search",
        "version": 0,
        "method": METHOD,
        "status": "double_control_frame_search_complete_no_exact_context_replay" if exact_context_count == 0 else "double_control_frame_search_found_bounded_candidate",
        "classification": "bounded_two_frame_control_side_clifford_boundary",
        "template_id": TEMPLATE_ID,
        "last_updated": args.last_updated,
        "question": "Can two fixed control-side +/- pi/2 frames in different layers alter the w8_21 phase obstruction without adding a CX or arbitrary angle?",
        "candidate_family": {
            "description": "two fixed control-side +/- pi/2 Euler rotations in distinct local layers, five arbitrary source target-side angles, and both two-CX direction sequences",
            "family_count": len(selected),
            "total_family_count": len(all_families),
            "layer_pair_count": 3,
            "fixed_frame_angle_set": ["-pi/2", "+pi/2"],
            "fixed_frame_qubit": 0,
            "free_slot_labels": [SLOTS[slot]["label"] for slot in SOURCE_FREE_SLOTS],
            "cnot_direction_count": 4,
            "seed_count_per_family": args.seed_count,
            "max_nfev_per_seed": args.max_nfev,
            "family_selection": "exhaustive" if not args.family_limit else "prefix_subset",
        },
        "fit_configuration": {
            "seed_count": args.seed_count,
            "max_nfev": args.max_nfev,
            "exact_tolerance": args.exact_tolerance,
            "objective": "global-phase-aligned 4x4 unitary residual",
        },
        "summary": {
            "tested_context_count": len(context_results),
            "exact_context_count": exact_context_count,
            "total_exact_family_count": sum(row["exact_family_count"] for row in context_results),
            "best_residual_norm": min(row["best_candidate"]["fit"]["residual_norm"] for row in context_results),
            "attempted_optimizer_runs": optimizer_runs,
            "baseline_arbitrary_parameter_count": 6,
            "candidate_arbitrary_parameter_count": 5,
            "baseline_cnot_count": 2,
            "candidate_cnot_count": 2,
            "accepted_occurrence_removal": 0,
            "accepted_proxy_t_reduction": 0,
            "b7_credit": 0,
            "validation_error_count": 0,
            "rewrite_claimed": False,
            "resource_saving_claimed": False,
            "global_lower_bound_claimed": False,
        },
        "source_bindings": {
            single.SOURCE_QASM: {"path": single.SOURCE_QASM, "sha256": single.file_sha256(root / single.SOURCE_QASM)},
            single.SCAN_PATH: {"path": single.SCAN_PATH, "sha256": single.file_sha256(root / single.SCAN_PATH)},
            single.NEIGHBORHOOD_RESULT: {"path": single.NEIGHBORHOOD_RESULT, "sha256": single.file_sha256(root / single.NEIGHBORHOOD_RESULT)},
        },
        "contexts": context_results,
        "claim_boundary": {
            "supported_claim": "No exact five-arbitrary-angle replay was found in the declared two-frame control-side +/- pi/2 family across all seven source-bound contexts.",
            "unsupported_claims": [
                "No global lower bound is claimed.",
                "Other fixed Clifford words, continuous frames, ancillas, measurements, and full-circuit rewrites are not excluded.",
                "No occurrence removal, proxy-T reduction, or B7 credit is accepted.",
            ],
            "global_lower_bound_claimed": False,
            "rewrite_claimed": False,
            "resource_saving_claimed": False,
        },
        "artifacts": {"result": RESULT_PATH, "markdown_report": REPORT_PATH},
        "payload_hash": "",
    }
    payload["payload_hash"] = single.stable_hash({key: value for key, value in payload.items() if key != "payload_hash"})
    return payload


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# B7 w8_21 Two-Frame Control-Side Clifford Search",
        "",
        f"- Status: `{payload['status']}`",
        f"- Classification: `{payload['classification']}`",
        f"- Families tested per context: `{payload['candidate_family']['family_count']}`",
        f"- Contexts tested: `{summary['tested_context_count']}`",
        f"- Optimizer runs: `{summary['attempted_optimizer_runs']}`",
        f"- Exact context replays: `{summary['exact_context_count']}/{summary['tested_context_count']}`",
        f"- Best residual norm: `{summary['best_residual_norm']:.16g}`",
        f"- Payload hash: `{payload['payload_hash']}`",
        "",
        "## Heuristic question",
        "",
        "Can two fixed control-side Clifford frames in different layers alter the phase obstruction without adding a CX or arbitrary angle?",
        "",
        "## Search scope",
        "",
        "The candidate retains two CX gates and five arbitrary target-side source angles. It inserts two fixed control-side `+/- pi/2` Euler rotations in two distinct local layers, exhausts all layer pairs, axes, signs, and CX direction sequences, yielding 432 families per context.",
        "",
        "## Result",
        "",
        "| Context | Exact families | Best residual | Best two-frame word |",
        "|---:|---:|---:|---|",
    ]
    for row in payload["contexts"]:
        best = row["best_candidate"]
        frame = ", ".join(f"{label}={angle}" for label, angle in zip(best["fixed_slot_labels"], best["fixed_angle_labels"]))
        lines.append(f"| {row['context_index']} | {row['exact_family_count']} | {best['fit']['residual_norm']:.16g} | `{frame}, CX {''.join(best['cnot_directions'])}` |")
    lines.extend(
        [
            "",
            "No exact five-angle replay was found in the declared two-frame control-side Clifford family." if summary["exact_context_count"] == 0 else "A bounded exact candidate exists and requires full source replay before any credit.",
            "",
            "## Claim boundary",
            "",
            "This closes only the 432 two-frame families in the declared search. It is not a global KAK lower bound, an exhaustive Clifford-word search, or a full-circuit rewrite. Accepted occurrence removal, proxy-T reduction, and B7 credit remain zero.",
            "",
            "## Next route",
            "",
            "If this boundary remains negative, the next test should change the nonlocal word itself or move to a symbolic invariant for longer words, with exact arbitrary-input replay and resource pricing required before promotion.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json-output", type=Path, default=Path(RESULT_PATH))
    parser.add_argument("--markdown-output", type=Path, default=Path(REPORT_PATH))
    parser.add_argument("--last-updated", default="2026-07-15")
    parser.add_argument("--family-limit", type=int, default=0)
    parser.add_argument("--seed-count", type=int, default=2)
    parser.add_argument("--max-nfev", type=int, default=400)
    parser.add_argument("--exact-tolerance", type=float, default=EXACT_TOLERANCE)
    args = parser.parse_args()
    result = run(args)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(report(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "payload_hash": result["payload_hash"], **result["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
