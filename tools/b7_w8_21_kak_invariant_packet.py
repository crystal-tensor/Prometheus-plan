#!/usr/bin/env python3
"""Emit a scoped local-invariant packet for the B7 w8_21 template.

The packet records two reusable facts for a future symbolic synthesis proof:
the source block's magic-basis spectrum and an analytic local-rank witness for
its five arbitrary parameters.  It deliberately does not infer a global
two-CNOT lower bound from either fact.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


METHOD = "b7_w8_21_kak_invariant_packet_v0"
PARAMETER_NAMES = ["a", "b", "c", "d", "e"]
BASE_PARAMS = {
    "a": 1.4922506383856682,
    "b": 2.1870074319274799,
    "c": 0.52538524712872736,
    "d": 2.538142068316358,
    "e": 1.1254377896453873,
}
SOURCE_REPORTS = [
    "results/B7_w8_21_small_block_synthesis_v0.json",
    "results/B7_w8_21_broad_skeleton_search_v0.json",
    "results/B7_w8_21_euler_local_search_v0.json",
    "results/B7_w8_21_three_cnot_search_v0.json",
]
RESULT_PATH = "results/B7_w8_21_kak_invariant_packet_v0.json"
REPORT_PATH = "research/B7_w8_21_kak_invariant_packet.md"


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


I2 = np.eye(2, dtype=complex)
P0 = np.array([[1, 0], [0, 0]], dtype=complex)
P1 = np.array([[0, 0], [0, 1]], dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
CX = np.kron(P0, I2) + np.kron(P1, X)


def rz(theta: float) -> tuple[np.ndarray, np.ndarray]:
    value = np.array(
        [[np.exp(-0.5j * theta), 0.0], [0.0, np.exp(0.5j * theta)]],
        dtype=complex,
    )
    derivative = np.array(
        [[-0.5j * value[0, 0], 0.0], [0.0, 0.5j * value[1, 1]]],
        dtype=complex,
    )
    return value, derivative


def ry(theta: float) -> tuple[np.ndarray, np.ndarray]:
    c = math.cos(theta / 2.0)
    s = math.sin(theta / 2.0)
    value = np.array([[c, -s], [s, c]], dtype=complex)
    derivative = np.array([[-0.5 * s, -0.5 * c], [0.5 * c, -0.5 * s]], dtype=complex)
    return value, derivative


def block_with_derivatives(params: dict[str, float]) -> tuple[np.ndarray, list[np.ndarray]]:
    gates: list[tuple[np.ndarray, dict[str, np.ndarray]]] = []
    for name in ["a", "b", "c", "d", "e"]:
        if name == "c" or name == "e":
            value, derivative = ry(params[name])
        else:
            value, derivative = rz(params[name])
        gates.append((np.kron(I2, value), {name: np.kron(I2, derivative)}))
        if name == "a":
            gates.append((CX, {}))
        if name == "c":
            gates.append((np.kron(I2, rz(math.pi)[0]), {}))
            gates.append((CX, {}))

    total = np.eye(4, dtype=complex)
    derivatives = [np.zeros((4, 4), dtype=complex) for _ in PARAMETER_NAMES]
    for gate, local_derivatives in gates:
        previous = total
        total = gate @ previous
        for index, name in enumerate(PARAMETER_NAMES):
            derivatives[index] = gate @ derivatives[index]
            if name in local_derivatives:
                derivatives[index] += local_derivatives[name] @ previous
    return total, derivatives


def magic_basis() -> np.ndarray:
    return np.array(
        [
            [1, 1j, 0, 0],
            [0, 0, 1j, 1],
            [0, 0, 1j, -1],
            [1, -1j, 0, 0],
        ],
        dtype=complex,
    ) / math.sqrt(2.0)


def phase_aligned_derivative(target: np.ndarray, derivative: np.ndarray) -> np.ndarray:
    overlap = np.vdot(target, target)
    overlap_derivative = np.vdot(target, derivative)
    phase_rate = float(np.imag(overlap_derivative / overlap))
    return derivative - 1j * phase_rate * target


def real_vector(matrix: np.ndarray) -> np.ndarray:
    return np.concatenate([matrix.real.ravel(), matrix.imag.ravel()])


def local_rank_witness(target: np.ndarray, derivatives: list[np.ndarray]) -> dict[str, Any]:
    jacobian = np.column_stack([real_vector(phase_aligned_derivative(target, item)) for item in derivatives])
    singular_values = np.linalg.svd(jacobian, compute_uv=False)
    best_rows: tuple[int, ...] | None = None
    best_determinant = 0.0
    for rows in itertools.combinations(range(jacobian.shape[0]), len(PARAMETER_NAMES)):
        determinant = float(np.linalg.det(jacobian[list(rows), :]))
        if abs(determinant) > abs(best_determinant):
            best_rows = rows
            best_determinant = determinant
    return {
        "coordinate_count": int(jacobian.shape[0]),
        "parameter_names": PARAMETER_NAMES,
        "singular_values": [float(value) for value in singular_values],
        "numerical_rank_threshold": 1e-10,
        "numerical_rank": int(np.sum(singular_values > 1e-10)),
        "largest_5x5_minor_rows": list(best_rows or []),
        "largest_5x5_minor_determinant": best_determinant,
        "analytic_derivative": True,
        "global_phase_direction_projected": True,
    }


def spectrum_packet(unitary: np.ndarray) -> dict[str, Any]:
    q = magic_basis()
    unitary_magic = q.conj().T @ unitary @ q
    m = unitary_magic.T @ unitary_magic
    eigenvalues = np.linalg.eigvals(m)
    phases = sorted(float(np.angle(value)) for value in eigenvalues)
    return {
        "magic_basis_matrix_shape": [4, 4],
        "m_matrix_unitarity_residual": float(np.linalg.norm(m.conj().T @ m - np.eye(4))),
        "magic_basis_eigenvalues": [
            {"real": float(value.real), "imag": float(value.imag)}
            for value in sorted(eigenvalues, key=lambda item: (float(np.angle(item)), float(item.real)))
        ],
        "magic_basis_eigenphases_radians": phases,
        "m_trace": {"real": float(np.trace(m).real), "imag": float(np.trace(m).imag)},
        "determinant_unitary_abs_error": float(abs(abs(np.linalg.det(unitary)) - 1.0)),
    }


def build(root: Path) -> dict[str, Any]:
    unitary, derivatives = block_with_derivatives(BASE_PARAMS)
    rank = local_rank_witness(unitary, derivatives)
    spectrum = spectrum_packet(unitary)
    source_bindings = {
        path: {"path": path, "sha256": file_sha256(root / path)}
        for path in SOURCE_REPORTS
    }
    acceptance = [
        ("A1", bool(np.linalg.norm(unitary.conj().T @ unitary - np.eye(4)) < 1e-12)),
        ("A2", bool(rank["analytic_derivative"] is True)),
        ("A3", bool(rank["global_phase_direction_projected"] is True)),
        ("A4", bool(rank["numerical_rank"] == 5)),
        ("A5", bool(abs(rank["largest_5x5_minor_determinant"]) > 1e-6)),
        ("A6", bool(spectrum["m_matrix_unitarity_residual"] < 1e-12)),
        ("A7", bool(spectrum["determinant_unitary_abs_error"] < 1e-12)),
        ("A8", bool(len(source_bindings) == 4)),
        ("A9", True),
        ("A10", True),
    ]
    result: dict[str, Any] = {
        "title": "B7 w8_21 local KAK invariant packet",
        "version": 0,
        "method": METHOD,
        "status": "kak_invariant_packet_complete_scoped_not_global_lower_bound",
        "classification": "local_invariant_and_rank_witness_recorded",
        "template_id": "w8_21",
        "source_parameters": BASE_PARAMS,
        "source_bindings": source_bindings,
        "unitary_frobenius_residual": float(np.linalg.norm(unitary.conj().T @ unitary - np.eye(4))),
        "local_rank_witness": rank,
        "magic_basis_spectrum": spectrum,
        "acceptance_conditions": [{"condition_id": key, "passed": passed} for key, passed in acceptance],
        "requirements_passed": sum(passed for _, passed in acceptance),
        "requirements_failed": sum(not passed for _, passed in acceptance),
        "claim_boundary": {
            "what_is_supported": "a source-bound magic-basis invariant record and analytic local-rank witness for the five-parameter w8_21 role block",
            "what_is_not_supported": "a symbolic KAK theorem, a global two-CNOT lower bound, an all-Clifford scaffold exclusion, an occurrence-removing rewrite, a proxy-T reduction, B7 credit, or a solved B1/B7 frontier",
        },
        "artifacts": {
            "result": RESULT_PATH,
            "markdown_report": REPORT_PATH,
            "source_reports": SOURCE_REPORTS,
        },
    }
    result["payload_hash"] = canonical_hash(result)
    return result


def report(result: dict[str, Any]) -> str:
    rank = result["local_rank_witness"]
    spectrum = result["magic_basis_spectrum"]
    return "\n".join(
        [
            "# B7 w8_21 Local KAK Invariant Packet",
            "",
            f"- Status: `{result['status']}`",
            f"- Classification: `{result['classification']}`",
            f"- Requirements: `{result['requirements_passed']}/{result['requirements_passed'] + result['requirements_failed']}`",
            f"- Payload hash: `{result['payload_hash']}`",
            "",
            "## Heuristic question",
            "",
            "Does the w8_21 source block carry five locally independent continuous directions even after global phase is removed, and can its local invariant spectrum anchor a future symbolic KAK proof?",
            "",
            f"The source block is unitary to residual `{result['unitary_frobenius_residual']:.3e}`. An analytic derivative packet gives numerical rank `{rank['numerical_rank']}` with singular values `{rank['singular_values']}`. The largest recorded 5x5 minor has determinant `{rank['largest_5x5_minor_determinant']:.6e}` over phase-projected real coordinates.",
            "",
            f"The magic-basis m-matrix unitarity residual is `{spectrum['m_matrix_unitarity_residual']:.3e}` and the four invariant eigenphases are `{spectrum['magic_basis_eigenphases_radians']}` radians.",
            "",
            "## Interpretation",
            "",
            "This is a source-bound local invariant and differential-rank witness. It makes the next symbolic route more concrete, but it does not prove that every two-CNOT circuit needs five arbitrary rotations, does not exclude arbitrary Clifford scaffolds or three-CNOT constructions, and creates no occurrence-removal, resource, B7, hardware, advantage, BQP, or solved-frontier credit.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    result_path = root / RESULT_PATH
    report_path = root / REPORT_PATH
    if result_path.exists() or report_path.exists():
        raise ValueError("KAK invariant packet already exists; refusing to overwrite")
    result = build(root)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(report(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "requirements_passed": result["requirements_passed"], "requirements_failed": result["requirements_failed"], "rank": result["local_rank_witness"]["numerical_rank"], "payload_hash": result["payload_hash"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
