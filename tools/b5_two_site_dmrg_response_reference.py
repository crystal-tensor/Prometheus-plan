#!/usr/bin/env python3
"""Build a two-site finite-DMRG-style B5 response pressure reference."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from scipy import linalg
from scipy import sparse

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from b10_t1_d5_observable_denominator_table import (  # noqa: E402
    ETA,
    basis_states,
    hubbard_hamiltonian,
    local_density_diagonal,
)
from b5_mps_truncation_response_reference import (  # noqa: E402
    full_tensor_to_fixed_vector,
    local_state,
    lowest_eigenpair,
    relative_error,
    solve_response_from_state,
)
from b5_variational_mps_als_response_reference import (  # noqa: E402
    energy_of_mps,
    fixed_state_from_mps,
    random_mps,
)


METHOD = "b5_two_site_finite_dmrg_response_reference_v0"
STATUS = "two_site_finite_dmrg_pressure_reference_not_production_dmrg_or_advantage_claim"
MODEL_STATUS = "two_site_finite_dmrg_style_pressure_reference"
DEFAULT_BOND_DIMS = (4,)
DEFAULT_SWEEPS = 4
DEFAULT_RESTARTS = 2
RNG_SEED = 20260619


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def left_environment(mps: list[np.ndarray], site: int) -> np.ndarray:
    if site == 0:
        return np.ones((1,), dtype=np.float64)
    env = mps[0][0, :, :]
    for tensor in mps[1:site]:
        env = np.tensordot(env, tensor, axes=([-1], [0]))
    return env


def right_environment(mps: list[np.ndarray], site_after_pair: int) -> np.ndarray:
    if site_after_pair >= len(mps):
        return np.ones((1,), dtype=np.float64)
    env = mps[-1][:, :, 0]
    for tensor in reversed(mps[site_after_pair:-1]):
        env = np.tensordot(tensor, env, axes=([2], [0]))
    return env


def two_site_theta(mps: list[np.ndarray], site: int) -> np.ndarray:
    return np.tensordot(mps[site], mps[site + 1], axes=([2], [0]))


def theta_to_fixed_vector(
    left_env: np.ndarray,
    theta: np.ndarray,
    right_env: np.ndarray,
    sites: int,
    n_up: int,
    n_down: int,
) -> np.ndarray:
    tensor = np.tensordot(left_env, theta, axes=([-1], [0]))
    tensor = np.tensordot(tensor, right_env, axes=([-1], [0]))
    return full_tensor_to_fixed_vector(tensor, sites, n_up, n_down)


def two_site_basis_matrix(
    mps: list[np.ndarray],
    site: int,
    sites: int,
    n_up: int,
    n_down: int,
) -> np.ndarray:
    original = two_site_theta(mps, site)
    left_env = left_environment(mps, site)
    right_env = right_environment(mps, site + 2)
    basis = np.zeros((len(basis_states(sites, n_up, n_down)), original.size), dtype=np.float64)
    for row_index, (up_bits, down_bits) in enumerate(basis_states(sites, n_up, n_down)):
        physical = [local_state(up_bits, down_bits, physical_site) for physical_site in range(sites)]
        if site == 0:
            left_vector = np.ones((original.shape[0],), dtype=np.float64)
        else:
            left_vector = np.asarray(left_env[tuple(physical[:site])], dtype=np.float64)
        if site + 2 >= sites:
            right_vector = np.ones((original.shape[3],), dtype=np.float64)
        else:
            right_vector = np.asarray(
                right_env[(slice(None), *tuple(physical[site + 2 :]))],
                dtype=np.float64,
            )
        row_tensor = basis[row_index].reshape(original.shape)
        row_tensor[:, physical[site], physical[site + 1], :] = np.outer(left_vector, right_vector)
    return basis


def split_theta_into_mps_pair(theta: np.ndarray, bond_dimension: int) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    left_dim, physical_left, physical_right, right_dim = theta.shape
    matrix = theta.reshape(left_dim * physical_left, physical_right * right_dim)
    u_matrix, singular_values, vh_matrix = np.linalg.svd(matrix, full_matrices=False)
    keep = min(bond_dimension, len(singular_values))
    kept = singular_values[:keep]
    discarded = singular_values[keep:]
    total_weight = float(np.sum(singular_values**2))
    discarded_weight = float(np.sum(discarded**2))
    left_tensor = u_matrix[:, :keep].reshape(left_dim, physical_left, keep)
    right_tensor = (kept[:, None] * vh_matrix[:keep, :]).reshape(keep, physical_right, right_dim)
    return left_tensor, right_tensor, {
        "kept_rank": int(keep),
        "full_rank": int(len(singular_values)),
        "discarded_weight": discarded_weight,
        "relative_discarded_weight": discarded_weight / total_weight if total_weight else 0.0,
        "largest_discarded_singular_value": float(discarded[0]) if len(discarded) else 0.0,
        "kept_singular_values": [float(value) for value in kept[: min(8, len(kept))]],
    }


def optimize_two_site(
    mps: list[np.ndarray],
    site: int,
    matrix: sparse.csr_matrix,
    sites: int,
    n_up: int,
    n_down: int,
    bond_dimension: int,
) -> dict[str, Any]:
    basis = two_site_basis_matrix(mps, site, sites, n_up, n_down)
    norm_matrix = basis.T @ basis
    h_matrix = basis.T @ (matrix @ basis)
    reg = 1e-10 * max(1.0, float(np.trace(norm_matrix)) / max(1, norm_matrix.shape[0]))
    norm_matrix = norm_matrix + reg * np.eye(norm_matrix.shape[0])
    values, vectors = linalg.eigh(h_matrix, norm_matrix, check_finite=False)
    best = np.asarray(vectors[:, int(np.argmin(values))], dtype=np.float64)
    theta = best.reshape(two_site_theta(mps, site).shape)
    scale = float(np.linalg.norm(theta.ravel()))
    if scale > 0.0:
        theta = theta / scale
    left_tensor, right_tensor, truncation = split_theta_into_mps_pair(theta, bond_dimension)
    mps[site] = left_tensor
    mps[site + 1] = right_tensor
    return {
        "site_pair": [site, site + 1],
        "local_parameter_count": int(basis.shape[1]),
        "local_rank": int(np.linalg.matrix_rank(norm_matrix, tol=1e-9)),
        "local_lowest_energy": float(np.min(values)),
        "regularization": reg,
        **truncation,
    }


def run_two_site_dmrg(
    matrix: sparse.csr_matrix,
    sites: int,
    n_up: int,
    n_down: int,
    bond_dimension: int,
    restarts: int,
    sweeps: int,
    seed: int,
) -> dict[str, Any]:
    best_payload: dict[str, Any] | None = None
    restart_summaries = []
    for restart in range(restarts):
        rng = np.random.default_rng(seed + 1009 * restart + 131 * bond_dimension + 17 * sites)
        mps = random_mps(sites, bond_dimension, rng, noise_scale=0.04)
        initial = energy_of_mps(mps, matrix, sites, n_up, n_down)
        sweep_history = []
        for sweep in range(sweeps):
            local_updates = []
            direction = range(sites - 1) if sweep % 2 == 0 else range(sites - 2, -1, -1)
            for site in direction:
                local_updates.append(optimize_two_site(mps, site, matrix, sites, n_up, n_down, bond_dimension))
            energy_payload = energy_of_mps(mps, matrix, sites, n_up, n_down)
            sweep_history.append(
                {
                    "sweep": sweep + 1,
                    "direction": "left_to_right" if sweep % 2 == 0 else "right_to_left",
                    "energy": float(energy_payload["energy"]),
                    "energy_variance": float(energy_payload["energy_variance"]),
                    "fixed_sector_norm_before_normalization": float(
                        energy_payload["fixed_sector_norm_before_normalization"]
                    ),
                    "max_local_parameter_count": max(update["local_parameter_count"] for update in local_updates),
                    "min_local_rank": min(update["local_rank"] for update in local_updates),
                    "max_relative_discarded_weight": max(
                        update["relative_discarded_weight"] for update in local_updates
                    ),
                }
            )
        final_payload = energy_of_mps(mps, matrix, sites, n_up, n_down)
        restart_summaries.append(
            {
                "restart": restart,
                "initial_energy": float(initial["energy"]),
                "final_energy": float(final_payload["energy"]),
                "final_energy_variance": float(final_payload["energy_variance"]),
                "final_fixed_sector_norm_before_normalization": float(
                    final_payload["fixed_sector_norm_before_normalization"]
                ),
                "sweep_history": sweep_history,
            }
        )
        candidate = {
            "mps": mps,
            "state": final_payload["state"],
            "full_norm": final_payload["full_norm"],
            "fixed_sector_norm_before_normalization": final_payload["fixed_sector_norm_before_normalization"],
            "fixed_sector_leakage": final_payload["fixed_sector_leakage"],
            "energy": final_payload["energy"],
            "energy_variance": final_payload["energy_variance"],
            "restart": restart,
        }
        if best_payload is None or float(candidate["energy"]) < float(best_payload["energy"]):
            best_payload = candidate
    if best_payload is None or best_payload.get("state") is None:
        raise RuntimeError("two-site finite DMRG did not produce a nonzero fixed-sector state")
    return {
        "state": best_payload["state"],
        "energy": float(best_payload["energy"]),
        "energy_variance": float(best_payload["energy_variance"]),
        "full_norm": float(best_payload["full_norm"]),
        "fixed_sector_norm_before_normalization": float(
            best_payload["fixed_sector_norm_before_normalization"]
        ),
        "fixed_sector_leakage": float(best_payload["fixed_sector_leakage"]),
        "selected_restart": int(best_payload["restart"]),
        "restart_summaries": restart_summaries,
    }


def build_rows(
    d5_source: dict[str, Any],
    seeded_mps_source: dict[str, Any],
    variational_mps_source: dict[str, Any],
    bond_dimensions: tuple[int, ...],
    restarts: int,
    sweeps: int,
    seed: int,
) -> list[dict[str, Any]]:
    seeded_rows = {
        (int(row["sites"]), float(row["u_over_t"])): row
        for row in seeded_mps_source.get("rows", [])
    }
    als_rows = {
        (int(row["sites"]), float(row["u_over_t"])): row
        for row in variational_mps_source.get("rows", [])
    }
    rows: list[dict[str, Any]] = []
    for d5_row in d5_source.get("rows", []):
        sites = int(d5_row["sites"])
        u_over_t = float(d5_row["u_over_t"])
        t_value = float(d5_row.get("t", 1.0))
        n_up = sites // 2
        n_down = sites // 2
        matrix = hubbard_hamiltonian(sites, n_up, n_down, u_over_t * t_value, t_value)
        ground_energy, exact_psi = lowest_eigenpair(matrix)
        density = local_density_diagonal(sites, n_up, n_down, sites // 2)
        exact_susceptibility = float(d5_row["susceptibility_proxy"])
        bond_rows = []
        for bond_dimension in bond_dimensions:
            dmrg = run_two_site_dmrg(
                matrix,
                sites,
                n_up,
                n_down,
                bond_dimension=bond_dimension,
                restarts=restarts,
                sweeps=sweeps,
                seed=seed,
            )
            psi_dmrg = dmrg["state"]
            response = solve_response_from_state(matrix, psi_dmrg, ground_energy, density)
            susceptibility = float(response["susceptibility_proxy"])
            overlap = abs(float(np.dot(exact_psi, psi_dmrg)))
            bond_rows.append(
                {
                    "bond_dimension": int(bond_dimension),
                    "energy": float(dmrg["energy"]),
                    "energy_error_per_site": abs(float(dmrg["energy"]) - ground_energy) / sites,
                    "energy_variance": float(dmrg["energy_variance"]),
                    "susceptibility_proxy": susceptibility,
                    "absolute_response_error": abs(susceptibility - exact_susceptibility),
                    "relative_response_error": relative_error(susceptibility, exact_susceptibility),
                    "response_relative_residual": float(response["relative_residual"]),
                    "response_iterations": int(response["iterations"]),
                    "response_solver_info": int(response["solver_info"]),
                    "overlap_with_exact_ground_state": overlap,
                    "full_norm": float(dmrg["full_norm"]),
                    "fixed_sector_norm_before_normalization": float(
                        dmrg["fixed_sector_norm_before_normalization"]
                    ),
                    "fixed_sector_leakage": float(dmrg["fixed_sector_leakage"]),
                    "selected_restart": int(dmrg["selected_restart"]),
                    "restart_summaries": dmrg["restart_summaries"],
                }
            )
        selected = min(bond_rows, key=lambda row: float(row["energy"]))
        seeded_row = seeded_rows.get((sites, u_over_t), {})
        als_row = als_rows.get((sites, u_over_t), {})
        seeded_error = seeded_row.get("selected_relative_response_error")
        als_error = als_row.get("selected_relative_response_error")
        rows.append(
            {
                "model": "one_dimensional_fermi_hubbard_half_filled_density_response",
                "sites": sites,
                "u_over_t": u_over_t,
                "t": t_value,
                "eta": float(d5_row.get("eta", ETA)),
                "exact_d5_susceptibility_proxy": exact_susceptibility,
                "exact_d5_hilbert_dimension": int(d5_row["hilbert_dimension"]),
                "exact_ground_energy": ground_energy,
                "bond_dimensions_tested": list(bond_dimensions),
                "selected_bond_dimension": int(selected["bond_dimension"]),
                "selected_susceptibility_proxy": float(selected["susceptibility_proxy"]),
                "selected_relative_response_error": float(selected["relative_response_error"]),
                "selected_energy_error_per_site": float(selected["energy_error_per_site"]),
                "selected_energy_variance": float(selected["energy_variance"]),
                "selected_overlap_with_exact_ground_state": float(selected["overlap_with_exact_ground_state"]),
                "selected_fixed_sector_norm_before_normalization": float(
                    selected["fixed_sector_norm_before_normalization"]
                ),
                "selected_response_relative_residual": float(selected["response_relative_residual"]),
                "seeded_mps_pressure_relative_response_error": seeded_error,
                "variational_mps_als_relative_response_error": als_error,
                "two_site_dmrg_beats_seeded_mps_pressure_reference": (
                    bool(seeded_error is not None and float(selected["relative_response_error"]) < float(seeded_error))
                ),
                "two_site_dmrg_beats_variational_mps_als_reference": (
                    bool(als_error is not None and float(selected["relative_response_error"]) < float(als_error))
                ),
                "two_site_finite_dmrg_style": True,
                "canonical_environment_production_dmrg": False,
                "production_dmrg": False,
                "exact_state_seeded": False,
                "quantum_response_win_claimed": False,
                "accuracy_per_resource_win_claimed": False,
                "bond_dimension_rows": bond_rows,
            }
        )
    return rows


def summarize(rows: list[dict[str, Any]], bond_dimensions: tuple[int, ...], restarts: int, sweeps: int) -> dict[str, Any]:
    selected_errors = [float(row["selected_relative_response_error"]) for row in rows]
    energy_errors = [float(row["selected_energy_error_per_site"]) for row in rows]
    return {
        "instance_count": len(rows),
        "site_values": sorted({int(row["sites"]) for row in rows}),
        "u_over_t_values": sorted({float(row["u_over_t"]) for row in rows}),
        "bond_dimensions_tested": list(bond_dimensions),
        "selected_bond_dimensions": sorted({int(row["selected_bond_dimension"]) for row in rows}),
        "restarts_per_instance_bond_dimension": restarts,
        "sweeps_per_restart": sweeps,
        "two_site_finite_dmrg_style": True,
        "canonical_environment_production_dmrg": False,
        "production_dmrg": False,
        "exact_state_seeded": False,
        "selected_mean_relative_response_error": float(np.mean(selected_errors)),
        "selected_median_relative_response_error": float(np.median(selected_errors)),
        "selected_max_relative_response_error": float(np.max(selected_errors)),
        "selected_mean_energy_error_per_site": float(np.mean(energy_errors)),
        "selected_max_energy_error_per_site": float(np.max(energy_errors)),
        "selected_min_overlap_with_exact_ground_state": float(
            np.min([float(row["selected_overlap_with_exact_ground_state"]) for row in rows])
        ),
        "selected_min_fixed_sector_norm_before_normalization": float(
            np.min([float(row["selected_fixed_sector_norm_before_normalization"]) for row in rows])
        ),
        "two_site_dmrg_rows_beating_seeded_mps_pressure_reference": int(
            sum(1 for row in rows if row["two_site_dmrg_beats_seeded_mps_pressure_reference"])
        ),
        "two_site_dmrg_rows_beating_variational_mps_als_reference": int(
            sum(1 for row in rows if row["two_site_dmrg_beats_variational_mps_als_reference"])
        ),
        "quantum_response_win_claimed": False,
        "accuracy_per_resource_win_claimed": False,
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# B5 Two-Site Finite-DMRG Response Reference v0.1",
        "",
        f"- Status: {report['status']}",
        f"- Method: {report['method']}",
        f"- Instances: {summary['instance_count']}",
        f"- Bond dimensions tested: {summary['bond_dimensions_tested']}",
        f"- Restarts x sweeps: {summary['restarts_per_instance_bond_dimension']} x {summary['sweeps_per_restart']}",
        f"- Mean/max relative response error: {summary['selected_mean_relative_response_error']} / {summary['selected_max_relative_response_error']}",
        f"- Rows beating one-site MPS/ALS: {summary['two_site_dmrg_rows_beating_variational_mps_als_reference']}",
        f"- Rows beating exact-state-seeded MPS pressure: {summary['two_site_dmrg_rows_beating_seeded_mps_pressure_reference']}",
        f"- Production DMRG: {summary['production_dmrg']}",
        f"- Validation errors: {report['validation_errors']}",
        "",
        "## Row Summary",
        "",
        "| sites | U/t | selected bond | rel response error | energy error/site | overlap | beats ALS | beats seeded pressure |",
        "|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in report["rows"]:
        lines.append(
            f"| {row['sites']} | {row['u_over_t']} | {row['selected_bond_dimension']} | "
            f"{row['selected_relative_response_error']:.6g} | {row['selected_energy_error_per_site']:.6g} | "
            f"{row['selected_overlap_with_exact_ground_state']:.6g} | "
            f"{row['two_site_dmrg_beats_variational_mps_als_reference']} | "
            f"{row['two_site_dmrg_beats_seeded_mps_pressure_reference']} |"
        )
    lines.extend(["", "## Claim Boundary", ""])
    for key, value in report["claim_boundary"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)


def build_report(
    d5_source: dict[str, Any],
    seeded_mps_source: dict[str, Any],
    variational_mps_source: dict[str, Any],
    bond_dimensions: tuple[int, ...],
    restarts: int,
    sweeps: int,
    seed: int,
) -> dict[str, Any]:
    started = time.time()
    rows = build_rows(d5_source, seeded_mps_source, variational_mps_source, bond_dimensions, restarts, sweeps, seed)
    summary = summarize(rows, bond_dimensions, restarts, sweeps)
    validation_errors = []
    if summary["instance_count"] != 9:
        validation_errors.append("expected 9 B5/B10 D5 response rows")
    if summary["production_dmrg"] is not False:
        validation_errors.append("two-site prototype must not claim production DMRG")
    if summary["two_site_dmrg_rows_beating_seeded_mps_pressure_reference"] != 0:
        validation_errors.append("two-site prototype should not beat exact-state-seeded pressure in v0")
    if any(row["quantum_response_win_claimed"] for row in rows):
        validation_errors.append("row claims quantum response win")
    return {
        "benchmark_id": "B5",
        "problem_id": 38,
        "title": "B5 Two-Site Finite-DMRG Response Reference",
        "version": "0.1",
        "last_updated": "2026-06-18",
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "method": METHOD,
        "dependency_b10_table": "b10_t1_d5_observable_denominator_table_v0",
        "dependency_seeded_mps_pressure_result": "../results/B5_mps_truncation_response_reference_v0.json",
        "dependency_variational_mps_als_result": "../results/B5_variational_mps_als_response_reference_v0.json",
        "runtime_seconds": time.time() - started,
        "summary": {**summary, "validation_error_count": len(validation_errors)},
        "rows": rows,
        "claim_boundary": {
            "two_site_finite_dmrg_style": True,
            "canonical_environment_production_dmrg": False,
            "production_dmrg": False,
            "exact_state_seeded": False,
            "quantum_response_win_claimed": False,
            "accuracy_per_resource_win_claimed": False,
            "what_is_supported": (
                "A two-site finite-DMRG-style block update has been tested on the same 9 B5/B10 D5 response rows, "
                "with the same response observable and denominator comparisons."
            ),
            "what_is_not_supported": (
                "This is not a production DMRG implementation, not a canonical-environment proof, not a 2D correlated-matter solver, "
                "not a quantum response kernel, and not an accuracy-per-resource win."
            ),
        },
        "validation_errors": validation_errors,
    }


def parse_int_tuple(value: str) -> tuple[int, ...]:
    return tuple(int(item.strip()) for item in value.split(",") if item.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--d5-source", type=Path, default=Path("results/B10_t1_d5_observable_denominator_table_v0.json"))
    parser.add_argument("--seeded-mps-source", type=Path, default=Path("results/B5_mps_truncation_response_reference_v0.json"))
    parser.add_argument("--variational-mps-source", type=Path, default=Path("results/B5_variational_mps_als_response_reference_v0.json"))
    parser.add_argument("--bond-dimensions", default=",".join(str(value) for value in DEFAULT_BOND_DIMS))
    parser.add_argument("--restarts", type=int, default=DEFAULT_RESTARTS)
    parser.add_argument("--sweeps", type=int, default=DEFAULT_SWEEPS)
    parser.add_argument("--seed", type=int, default=RNG_SEED)
    parser.add_argument("--json-output", type=Path, default=Path("results/B5_two_site_dmrg_response_reference_v0.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("research/B5_two_site_dmrg_response_reference.md"))
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    report = build_report(
        load_json(args.d5_source),
        load_json(args.seeded_mps_source),
        load_json(args.variational_mps_source),
        parse_int_tuple(args.bond_dimensions),
        args.restarts,
        args.sweeps,
        args.seed,
    )
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(report, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"status": report["status"], "method": report["method"], **report["summary"], "validation_errors": report["validation_errors"]}, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if not report["validation_errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
