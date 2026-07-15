#!/usr/bin/env python3
"""Search a bounded control-side Clifford-frame family for w8_21 contexts.

The discrete relative-block branches are closed, so this gate tests a new
continuous escape route: retain two CX gates and five arbitrary target-side
angles, but insert one fixed control-side +/- pi/2 frame at every layer/axis
choice and scan both CX orientations.  This is deliberately different from
the prior target-slot relocation search.

The output is a bounded numerical boundary, not a global KAK theorem or a
full-circuit resource certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import b7_w8_21_neighborhood_transfer as neighborhood


METHOD = "b7_w8_21_control_frame_search_v0"
TEMPLATE_ID = "w8_21"
SOURCE_QASM = neighborhood.SOURCE_QASM
SCAN_PATH = neighborhood.SCAN_PATH
NEIGHBORHOOD_RESULT = "results/B7_w8_21_neighborhood_transfer_v0.json"
RESULT_PATH = "results/B7_w8_21_control_frame_search_v0.json"
REPORT_PATH = "research/B7_w8_21_control_frame_search.md"
EXACT_TOLERANCE = 1e-10
BASE_PARAMS = neighborhood.BASE_PARAMS
LAYERS = ("pre", "mid", "post")
EULER_AXES = ("rz0", "ry", "rz1")
CNOT_DIRS = ("01", "10")
FRAME_ANGLES = (-math.pi / 2.0, math.pi / 2.0)

I2 = np.eye(2, dtype=complex)
P0 = np.array([[1, 0], [0, 0]], dtype=complex)
P1 = np.array([[0, 0], [0, 1]], dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
CX_01 = np.kron(P0, I2) + np.kron(P1, X)
CX_10 = np.kron(I2, P0) + np.kron(X, P1)


def stable_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rz(theta: float) -> np.ndarray:
    return np.array(
        [[np.exp(-0.5j * theta), 0.0], [0.0, np.exp(0.5j * theta)]],
        dtype=complex,
    )


def ry(theta: float) -> np.ndarray:
    c = math.cos(theta / 2.0)
    s = math.sin(theta / 2.0)
    return np.array([[c, -s], [s, c]], dtype=complex)


def one_qubit_rotation(qubit: int, axis: str, theta: float) -> np.ndarray:
    single = rz(theta) if axis.startswith("rz") else ry(theta)
    return np.kron(single, I2) if qubit == 0 else np.kron(I2, single)


def euler_slots() -> list[dict[str, Any]]:
    slots = []
    for layer in LAYERS:
        for qubit in (0, 1):
            for axis in EULER_AXES:
                slots.append(
                    {
                        "index": len(slots),
                        "layer": layer,
                        "qubit": qubit,
                        "axis": axis,
                        "label": f"{layer}:q{qubit}:{axis}",
                    }
                )
    return slots


SLOTS = euler_slots()
SLOT_BY_LABEL = {slot["label"]: slot["index"] for slot in SLOTS}
SOURCE_FREE_SLOTS = (
    SLOT_BY_LABEL["pre:q1:rz0"],
    SLOT_BY_LABEL["mid:q1:rz0"],
    SLOT_BY_LABEL["mid:q1:ry"],
    SLOT_BY_LABEL["post:q1:rz0"],
    SLOT_BY_LABEL["post:q1:ry"],
)
SOURCE_VALUES = dict(zip(SOURCE_FREE_SLOTS, BASE_PARAMS))


def candidate_unitary(
    cnot_dirs: tuple[str, str], fixed_slot: int, fixed_angle: float, values: np.ndarray
) -> np.ndarray:
    angles = np.zeros(len(SLOTS), dtype=float)
    angles[fixed_slot] = fixed_angle
    for slot, value in zip(SOURCE_FREE_SLOTS, values):
        angles[slot] = float(value)
    total = np.eye(4, dtype=complex)
    cnot_index = 0
    for layer in LAYERS:
        for slot in SLOTS:
            if slot["layer"] == layer:
                total = one_qubit_rotation(slot["qubit"], slot["axis"], angles[slot["index"]]) @ total
        if layer != "post":
            total = (CX_01 if cnot_dirs[cnot_index] == "01" else CX_10) @ total
            cnot_index += 1
    return total


def phase_align(candidate: np.ndarray, target: np.ndarray) -> np.ndarray:
    overlap = np.trace(np.conjugate(target.T) @ candidate)
    return candidate * np.exp(-1j * np.angle(overlap)) if abs(overlap) > 1e-15 else candidate


def residual_vector(candidate: np.ndarray, target: np.ndarray) -> np.ndarray:
    diff = phase_align(candidate, target) - target
    return np.concatenate([diff.real.ravel(), diff.imag.ravel()])


def families() -> list[dict[str, Any]]:
    families = []
    for layer in LAYERS:
        for axis in EULER_AXES:
            fixed_slot = SLOT_BY_LABEL[f"{layer}:q0:{axis}"]
            for fixed_angle in FRAME_ANGLES:
                for cnot_dirs in itertools.product(CNOT_DIRS, repeat=2):
                    families.append(
                        {
                            "fixed_slot": fixed_slot,
                            "fixed_slot_label": SLOTS[fixed_slot]["label"],
                            "fixed_angle": fixed_angle,
                            "fixed_angle_label": "+pi/2" if fixed_angle > 0 else "-pi/2",
                            "cnot_directions": cnot_dirs,
                        }
                    )
    return families


def initial_points(seed_count: int) -> list[np.ndarray]:
    source = np.array(BASE_PARAMS, dtype=float)
    points = [source, np.zeros(5, dtype=float)]
    for index in range(2, seed_count):
        offsets = np.array([((17 * index + 11 * slot) % 31 - 15) * math.pi / 31.0 for slot in SOURCE_FREE_SLOTS])
        points.append(source + offsets)
    return points[:seed_count]


def context_targets(root: Path) -> list[dict[str, Any]]:
    rows = neighborhood.context_rows(root)
    source = neighborhood.source_unitary(BASE_PARAMS)
    targets = []
    for row in rows:
        local = neighborhood.target_local_matrix(row["context_operation"], row["target"])
        if local is None:
            raise ValueError(f"unsupported context operation: {row['context_operation']}")
        matrix = local @ source if row["direction"] == "after" else source @ local
        targets.append({"row": row, "matrix": matrix})
    return targets


def optimize_family(
    target: np.ndarray, family: dict[str, Any], seed_count: int, max_nfev: int
) -> dict[str, Any]:
    def objective(values: np.ndarray) -> np.ndarray:
        candidate = candidate_unitary(
            family["cnot_directions"], family["fixed_slot"], family["fixed_angle"], values
        )
        return residual_vector(candidate, target)

    best = None
    for seed_index, seed in enumerate(initial_points(seed_count)):
        fit = least_squares(objective, seed, max_nfev=max_nfev, xtol=1e-12, ftol=1e-12, gtol=1e-12)
        candidate = candidate_unitary(
            family["cnot_directions"], family["fixed_slot"], family["fixed_angle"], fit.x
        )
        residual = float(np.linalg.norm(residual_vector(candidate, target)))
        row = {
            "seed_index": seed_index,
            "fitted_parameters": [float(value) for value in fit.x],
            "residual_norm": residual,
            "max_abs_entry_error": float(np.max(np.abs(phase_align(candidate, target) - target))),
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
    targets = context_targets(root)
    context_results = []
    optimizer_runs = 0
    for context_index, context in enumerate(targets, start=1):
        best = None
        exact_count = 0
        best_family = None
        for family_index, family in enumerate(selected, start=1):
            fit = optimize_family(context["matrix"], family, args.seed_count, args.max_nfev)
            optimizer_runs += args.seed_count
            candidate = {
                "family_index": family_index,
                **family,
                "fit": fit,
            }
            if best is None or fit["residual_norm"] < best["fit"]["residual_norm"]:
                best = candidate
                best_family = candidate
            if fit["residual_norm"] <= args.exact_tolerance:
                exact_count += 1
        assert best is not None and best_family is not None
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
    best_residual = min(row["best_candidate"]["fit"]["residual_norm"] for row in context_results)
    payload = {
        "title": "B7 w8_21 control-side Clifford-frame search",
        "version": 0,
        "method": METHOD,
        "status": "control_frame_search_complete_no_exact_context_replay" if exact_context_count == 0 else "control_frame_search_found_bounded_candidate",
        "classification": "bounded_control_side_fixed_clifford_frame_boundary",
        "template_id": TEMPLATE_ID,
        "last_updated": args.last_updated,
        "question": "Can a single fixed control-side +/- pi/2 Clifford frame preserve two CX gates and five arbitrary target angles while absorbing the external target-local Rz?",
        "candidate_family": {
            "description": "one fixed control-side +/- pi/2 Euler rotation at any layer/axis, five arbitrary source target-side angles, and both two-CX direction sequences",
            "family_count": len(selected),
            "total_family_count": len(all_families),
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
            "best_residual_norm": best_residual,
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
            SOURCE_QASM: {"path": SOURCE_QASM, "sha256": file_sha256(root / SOURCE_QASM)},
            SCAN_PATH: {"path": SCAN_PATH, "sha256": file_sha256(root / SCAN_PATH)},
            NEIGHBORHOOD_RESULT: {"path": NEIGHBORHOOD_RESULT, "sha256": file_sha256(root / NEIGHBORHOOD_RESULT)},
        },
        "contexts": context_results,
        "claim_boundary": {
            "supported_claim": "No exact five-arbitrary-angle replay was found in the declared 72-family control-side +/- pi/2 Clifford-frame search across all seven source-bound contexts.",
            "unsupported_claims": [
                "No global lower bound is claimed.",
                "Other fixed Clifford words, continuous control-side frames, ancillas, measurements, and full-circuit rewrites are not excluded.",
                "No occurrence removal, proxy-T reduction, or B7 credit is accepted.",
            ],
            "global_lower_bound_claimed": False,
            "rewrite_claimed": False,
            "resource_saving_claimed": False,
        },
        "artifacts": {"result": RESULT_PATH, "markdown_report": REPORT_PATH},
        "payload_hash": "",
    }
    payload["payload_hash"] = stable_hash({key: value for key, value in payload.items() if key != "payload_hash"})
    return payload


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# B7 w8_21 Control-Side Clifford-Frame Search",
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
        "Can one fixed control-side Clifford frame change the continuous escape route without adding a CNOT or a sixth arbitrary angle?",
        "",
        "## Search scope",
        "",
        "The candidate keeps two CX gates and the five arbitrary target-side source angles. It adds exactly one fixed control-side `+/- pi/2` Euler rotation, exhausts all three local layers, all three Euler axes, both signs, and all four CX direction sequences. This yields 72 families per context and is distinct from the earlier target-slot relocation search.",
        "",
        "## Result",
        "",
        "| Context | Exact families | Best residual | Best frame |",
        "|---:|---:|---:|---|",
    ]
    for row in payload["contexts"]:
        best = row["best_candidate"]
        frame = f"{best['fixed_slot_label']}={best['fixed_angle_label']}, CX {''.join(best['cnot_directions'])}"
        lines.append(f"| {row['context_index']} | {row['exact_family_count']} | {best['fit']['residual_norm']:.16g} | `{frame}` |")
    lines.extend(
        [
            "",
            "No exact five-angle replay was found in the declared control-side Clifford-frame family." if summary["exact_context_count"] == 0 else "A bounded exact candidate exists and requires full source replay before any credit.",
            "",
            "## Claim boundary",
            "",
            "This closes only the 72 fixed-frame families in the declared search. It is not a global KAK lower bound, not an exhaustive Clifford-word search, and not a full-circuit rewrite. Accepted occurrence removal, proxy-T reduction, and B7 credit remain zero.",
            "",
            "## Next route",
            "",
            "The remaining continuous route is a longer fixed Clifford word or a genuinely different nonlocal skeleton, with exact arbitrary-input replay and resource pricing required before promotion.",
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
