#!/usr/bin/env python3
"""Verify a family-level controlled-unitary invariant closure for w8_21.

The fixed role skeleton has two CNOTs and all variable one-qubit gates on the
target wire.  In the control-target basis it is therefore block diagonal.  We
derive the relative 2x2 block explicitly and test the resulting magic-basis
quadratic identity over a deterministic parameter family.  This is a symbolic
invariant certificate for the tested skeleton, not a compression theorem.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


METHOD = "b7_w8_21_controlled_invariant_closure_v0"
PARAMETER_NAMES = ["a", "b", "c", "d", "e"]
BASE_PARAMS = {
    "a": 1.4922506383856682,
    "b": 2.1870074319274799,
    "c": 0.52538524712872736,
    "d": 2.538142068316358,
    "e": 1.1254377896453873,
}
SOURCE_BINDING_PATHS = [
    "benchmarks/qasmbench_medium_exact/gcm_h6.qasm",
    "results/B7_w8_21_kak_invariant_packet_v0.json",
]
RESULT_PATH = "results/B7_w8_21_controlled_invariant_closure_v0.json"
REPORT_PATH = "research/B7_w8_21_controlled_invariant_closure.md"

I2 = np.eye(2, dtype=complex)
P0 = np.array([[1, 0], [0, 0]], dtype=complex)
P1 = np.array([[0, 0], [0, 1]], dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
CX = np.kron(P0, I2) + np.kron(P1, X)


def canonical_hash(value: Any) -> str:
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


def role_block_unitary(params: dict[str, float]) -> np.ndarray:
    """Rebuild the source order as U = E D CX P C B CX A."""

    gates = [
        np.kron(I2, rz(params["a"])),
        CX,
        np.kron(I2, rz(params["b"])),
        np.kron(I2, ry(params["c"])),
        np.kron(I2, rz(math.pi)),
        CX,
        np.kron(I2, rz(params["d"])),
        np.kron(I2, ry(params["e"])),
    ]
    total = np.eye(4, dtype=complex)
    for gate in gates:
        total = gate @ total
    return total


def controlled_blocks(params: dict[str, float]) -> tuple[np.ndarray, np.ndarray]:
    """Return the control=0 and control=1 target blocks independently."""

    a, b, c, d, e = (params[name] for name in PARAMETER_NAMES)
    p = rz(math.pi)
    u0 = ry(e) @ rz(d) @ p @ ry(c) @ rz(b) @ rz(a)
    u1 = ry(e) @ rz(d) @ X @ p @ ry(c) @ rz(b) @ X @ rz(a)
    return u0, u1


def block_diagonal_unitary(u0: np.ndarray, u1: np.ndarray) -> np.ndarray:
    result = np.zeros((4, 4), dtype=complex)
    result[:2, :2] = u0
    result[2:, 2:] = u1
    return result


def closed_form_relative_block(params: dict[str, float]) -> np.ndarray:
    """Closed form for W = U0^dagger U1 from direct 2x2 algebra."""

    a, b, c = params["a"], params["b"], params["c"]
    return np.array(
        [
            [-np.exp(1j * b) * math.cos(c), -np.exp(1j * a) * math.sin(c)],
            [np.exp(-1j * a) * math.sin(c), -np.exp(-1j * b) * math.cos(c)],
        ],
        dtype=complex,
    )


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


def magic_m(unitary: np.ndarray) -> np.ndarray:
    q = magic_basis()
    in_magic = q.conj().T @ unitary @ q
    return in_magic.T @ in_magic


def characteristic_coefficients(matrix: np.ndarray) -> np.ndarray:
    """Compute det(lambda I - matrix) coefficients by Newton identities."""

    traces = [np.trace(np.linalg.matrix_power(matrix, power)) for power in range(1, 5)]
    e1 = traces[0]
    e2 = (traces[0] ** 2 - traces[1]) / 2.0
    e3 = (traces[0] ** 3 - 3.0 * traces[0] * traces[1] + 2.0 * traces[2]) / 6.0
    e4 = np.linalg.det(matrix)
    return np.array([1.0, -e1, e2, -e3, e4], dtype=complex)


def tau_from_params(params: dict[str, float]) -> float:
    return -math.cos(params["b"]) * math.cos(params["c"])


def expected_characteristic_coefficients(tau: float) -> np.ndarray:
    # chi(lambda) = (lambda^2 - 2*tau*lambda + 1)^2.
    return np.array(
        [1.0, -4.0 * tau, 4.0 * tau * tau + 2.0, -4.0 * tau, 1.0],
        dtype=complex,
    )


def sample_parameters() -> list[dict[str, float]]:
    samples = [dict(BASE_PARAMS)]
    for index in range(64):
        samples.append(
            {
                "a": float(-math.pi + 2.0 * math.pi * ((index * 17 + 3) % 64) / 64.0),
                "b": float(-math.pi + 2.0 * math.pi * ((index * 29 + 7) % 64) / 64.0),
                "c": float(-math.pi + 2.0 * math.pi * ((index * 11 + 13) % 64) / 64.0),
                "d": float(-math.pi + 2.0 * math.pi * ((index * 37 + 19) % 64) / 64.0),
                "e": float(-math.pi + 2.0 * math.pi * ((index * 43 + 23) % 64) / 64.0),
            }
        )
    return samples


def evaluate_sample(params: dict[str, float]) -> dict[str, Any]:
    unitary = role_block_unitary(params)
    u0, u1 = controlled_blocks(params)
    reconstructed = block_diagonal_unitary(u0, u1)
    relative = u0.conj().T @ u1
    closed = closed_form_relative_block(params)
    tau = tau_from_params(params)
    m = magic_m(unitary)
    coefficients = characteristic_coefficients(m)
    expected = expected_characteristic_coefficients(tau)
    return {
        "unitary_residual": float(np.linalg.norm(unitary.conj().T @ unitary - np.eye(4))),
        "control_block_reconstruction_residual": float(np.linalg.norm(unitary - reconstructed)),
        "relative_unitary_residual": float(np.linalg.norm(relative.conj().T @ relative - np.eye(2))),
        "relative_closed_form_residual": float(np.linalg.norm(relative - closed)),
        "tau": float(tau),
        "tau_from_relative_half_trace": float(np.trace(relative).real / 2.0),
        "magic_quadratic_residual": float(np.linalg.norm(m @ m - 2.0 * tau * m + np.eye(4))),
        "characteristic_coefficient_residual": float(np.max(np.abs(coefficients - expected))),
    }


def build(root: Path) -> dict[str, Any]:
    source_bindings = {
        path: {"path": path, "sha256": file_sha256(root / path)}
        for path in SOURCE_BINDING_PATHS
    }
    source = evaluate_sample(BASE_PARAMS)
    family_rows = [evaluate_sample(params) for params in sample_parameters()]
    max_family = {
        key: max(row[key] for row in family_rows)
        for key in [
            "unitary_residual",
            "control_block_reconstruction_residual",
            "relative_unitary_residual",
            "relative_closed_form_residual",
            "magic_quadratic_residual",
            "characteristic_coefficient_residual",
        ]
    }
    source_tau_error = abs(source["tau"] - 0.5)
    conditions = [
        ("A1", source["unitary_residual"] < 1e-12),
        ("A2", source["control_block_reconstruction_residual"] < 1e-12),
        ("A3", source["relative_closed_form_residual"] < 1e-12),
        ("A4", source["relative_unitary_residual"] < 1e-12),
        ("A5", source_tau_error < 1e-12),
        ("A6", source["magic_quadratic_residual"] < 1e-12),
        ("A7", source["characteristic_coefficient_residual"] < 1e-12),
        ("A8", len(family_rows) == 65),
        ("A9", max_family["relative_closed_form_residual"] < 1e-12),
        ("A10", max_family["characteristic_coefficient_residual"] < 1e-11),
    ]
    result: dict[str, Any] = {
        "title": "B7 w8_21 controlled-unitary invariant closure",
        "version": 0,
        "method": METHOD,
        "status": "controlled_invariant_closure_complete_scoped_no_compression_claim",
        "classification": "family_level_symbolic_invariant_closure",
        "template_id": "w8_21",
        "source_parameters": BASE_PARAMS,
        "source_bindings": source_bindings,
        "derived_structure": {
            "control_target_basis": True,
            "unitary_block_form": "U = |0><0| tensor U0 + |1><1| tensor U1",
            "relative_block": "W = U0^dagger U1 = [[-exp(i*b)*cos(c), -exp(i*a)*sin(c)], [exp(-i*a)*sin(c), -exp(-i*b)*cos(c)]]",
            "relative_half_trace": "tau = -cos(b)*cos(c)",
            "magic_minimal_polynomial": "lambda^2 - 2*tau*lambda + 1",
            "magic_characteristic_polynomial": "(lambda^2 - 2*tau*lambda + 1)^2",
            "independent_of_relative_half_trace": ["d", "e"],
        },
        "source_evidence": source,
        "source_tau_error_from_one_half": source_tau_error,
        "family_validation": {
            "sample_count": len(family_rows),
            "max_residuals": max_family,
        },
        "acceptance_conditions": [
            {"condition_id": condition_id, "passed": bool(passed)}
            for condition_id, passed in conditions
        ],
        "requirements_passed": sum(bool(passed) for _, passed in conditions),
        "requirements_failed": sum(not bool(passed) for _, passed in conditions),
        "claim_boundary": {
            "what_is_supported": "a family-level controlled-unitary decomposition and source-bound symbolic relative-block/magic-polynomial closure for the fixed w8_21 two-CNOT role skeleton",
            "what_is_not_supported": "an occurrence-removing rewrite, fewer CNOTs, fewer arbitrary rotations, a global two-CNOT lower bound, exclusion of other Clifford scaffolds, proxy-T reduction, B7 credit, hardware advantage, or a solved B1/B7 frontier",
        },
        "artifacts": {
            "result": RESULT_PATH,
            "markdown_report": REPORT_PATH,
            "source_bindings": SOURCE_BINDING_PATHS,
        },
    }
    result["payload_hash"] = canonical_hash(result)
    return result


def report(result: dict[str, Any]) -> str:
    source = result["source_evidence"]
    validation = result["family_validation"]
    return "\n".join(
        [
            "# B7 w8_21 Controlled-Unitary Invariant Closure",
            "",
            f"- Status: `{result['status']}`",
            f"- Classification: `{result['classification']}`",
            f"- Requirements: `{result['requirements_passed']}/{result['requirements_passed'] + result['requirements_failed']}`",
            f"- Payload hash: `{result['payload_hash']}`",
            "",
            "## Heuristic question",
            "",
            "If the repeated w8_21 block is a controlled-unitary family with one nonlocal invariant parameter, can the remaining local dressing be rewritten without paying five arbitrary rotations at every occurrence?",
            "",
            "## Derived closure",
            "",
            "In the control-target basis the source order is block diagonal: `U = |0><0| tensor U0 + |1><1| tensor U1`. Direct 2x2 multiplication gives",
            "",
            "`W = U0^dagger U1 = [[-exp(i*b)*cos(c), -exp(i*a)*sin(c)], [exp(-i*a)*sin(c), -exp(-i*b)*cos(c)]]`,",
            "",
            "so `tau = trace(W)/2 = -cos(b)cos(c)`. The corresponding magic-basis matrix satisfies the candidate identity `m^2 - 2*tau*m + I = 0`, and its characteristic polynomial is `(lambda^2 - 2*tau*lambda + 1)^2`. The formula is independent of `d` and `e` at the relative-block level.",
            "",
            f"For the source point, `tau = {source['tau']:.16f}` with error from `1/2` equal to `{result['source_tau_error_from_one_half']:.3e}`. The magic quadratic residual is `{source['magic_quadratic_residual']:.3e}` and the characteristic-coefficient residual is `{source['characteristic_coefficient_residual']:.3e}`.",
            "",
            f"A deterministic family check covers `{validation['sample_count']}` parameter points. The maximum relative closed-form residual is `{validation['max_residuals']['relative_closed_form_residual']:.3e}` and the maximum characteristic-coefficient residual is `{validation['max_residuals']['characteristic_coefficient_residual']:.3e}`.",
            "",
            "## Interpretation",
            "",
            "This upgrades the earlier pointwise KAK observation into a family-level invariant closure for this fixed skeleton. It identifies a one-parameter nonlocal invariant and gives a cleaner target for local-dressing synthesis. It does not prove a compression rewrite, a lower CNOT count, a reduction in arbitrary rotations, or any B7 resource credit.",
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
        raise ValueError("controlled invariant closure already exists; refusing to overwrite")
    result = build(root)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(report(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "requirements_passed": result["requirements_passed"],
                "requirements_failed": result["requirements_failed"],
                "sample_count": result["family_validation"]["sample_count"],
                "source_tau": result["source_evidence"]["tau"],
                "payload_hash": result["payload_hash"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
