#!/usr/bin/env python3
"""Verify a constructive local-dressing factorization for w8_21.

The factorization converts the controlled-unitary invariant closure into an
exact two-CNOT normal form.  It is useful because it separates the five
continuous source parameters into three target-local layers.  The parameter
count is intentionally audited: this normal form is a constructive identity,
not a resource reduction claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


METHOD = "b7_w8_21_constructive_dressing_v0"
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
    "results/B7_w8_21_controlled_invariant_closure_v0.json",
]
RESULT_PATH = "results/B7_w8_21_constructive_dressing_v0.json"
REPORT_PATH = "research/B7_w8_21_constructive_dressing.md"

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


def source_unitary(params: dict[str, float]) -> np.ndarray:
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


def source_blocks(params: dict[str, float]) -> tuple[np.ndarray, np.ndarray]:
    a, b, c, d, e = (params[name] for name in PARAMETER_NAMES)
    p = rz(math.pi)
    u0 = ry(e) @ rz(d) @ p @ ry(c) @ rz(b) @ rz(a)
    u1 = ry(e) @ rz(d) @ X @ p @ ry(c) @ rz(b) @ X @ rz(a)
    return u0, u1


def relative_block(params: dict[str, float]) -> np.ndarray:
    a, b, c = params["a"], params["b"], params["c"]
    return np.array(
        [
            [-np.exp(1j * b) * math.cos(c), -np.exp(1j * a) * math.sin(c)],
            [np.exp(-1j * a) * math.sin(c), -np.exp(-1j * b) * math.cos(c)],
        ],
        dtype=complex,
    )


def euler_dressing(params: dict[str, float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return A, B, C with A B C=I and A X B X C=W."""

    a, b, c = params["a"], params["b"], params["c"]
    alpha = -a - b - math.pi
    beta = 2.0 * c
    gamma = a - b - math.pi
    A = rz(alpha) @ ry(beta / 2.0)
    B = ry(-beta / 2.0) @ rz(-(alpha + gamma) / 2.0)
    C = rz((gamma - alpha) / 2.0)
    return A, B, C


def constructive_layers(params: dict[str, float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Simplified target-local layers after absorbing A into the source U0."""

    a, b, c, d, e = (params[name] for name in PARAMETER_NAMES)
    left = ry(e) @ rz(d)
    middle = ry(-c) @ rz(b + math.pi)
    right = rz(a)
    return left, middle, right


def constructive_unitary(params: dict[str, float]) -> np.ndarray:
    left, middle, right = constructive_layers(params)
    return np.kron(I2, left) @ CX @ np.kron(I2, middle) @ CX @ np.kron(I2, right)


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
    source = source_unitary(params)
    u0, u1 = source_blocks(params)
    W = u0.conj().T @ u1
    A, B, C = euler_dressing(params)
    left, middle, right = constructive_layers(params)
    controlled_reconstruction = np.block(
        [[np.eye(2, dtype=complex), np.zeros((2, 2), dtype=complex)],
         [np.zeros((2, 2), dtype=complex), W]]
    )
    return {
        "source_unitary_residual": float(np.linalg.norm(source.conj().T @ source - np.eye(4))),
        "source_block_unitarity_residual": float(
            max(
                np.linalg.norm(u0.conj().T @ u0 - I2),
                np.linalg.norm(u1.conj().T @ u1 - I2),
            )
        ),
        "relative_closed_form_residual": float(np.linalg.norm(W - relative_block(params))),
        "euler_abc_identity_residual": float(np.linalg.norm(A @ B @ C - I2)),
        "euler_controlled_relative_residual": float(np.linalg.norm(A @ X @ B @ X @ C - W)),
        "controlled_block_reconstruction_residual": float(
            np.linalg.norm(
                np.block([[u0, np.zeros((2, 2), dtype=complex)],
                          [np.zeros((2, 2), dtype=complex), u0 @ W]])
                - np.block([[u0, np.zeros((2, 2), dtype=complex)],
                            [np.zeros((2, 2), dtype=complex), u1]])
            )
        ),
        "constructive_unitary_residual": float(np.linalg.norm(constructive_unitary(params) - source)),
        "left_layer_unitarity_residual": float(np.linalg.norm(left.conj().T @ left - I2)),
        "middle_layer_unitarity_residual": float(np.linalg.norm(middle.conj().T @ middle - I2)),
        "right_layer_unitarity_residual": float(np.linalg.norm(right.conj().T @ right - I2)),
        "controlled_reconstruction_unitarity_residual": float(
            np.linalg.norm(controlled_reconstruction.conj().T @ controlled_reconstruction - np.eye(4))
        ),
    }


def build(root: Path) -> dict[str, Any]:
    source_bindings = {
        path: {"path": path, "sha256": file_sha256(root / path)}
        for path in SOURCE_BINDING_PATHS
    }
    source = evaluate_sample(BASE_PARAMS)
    family_rows = [evaluate_sample(params) for params in sample_parameters()]
    residual_keys = [
        "source_unitary_residual",
        "source_block_unitarity_residual",
        "relative_closed_form_residual",
        "euler_abc_identity_residual",
        "euler_controlled_relative_residual",
        "controlled_block_reconstruction_residual",
        "constructive_unitary_residual",
        "left_layer_unitarity_residual",
        "middle_layer_unitarity_residual",
        "right_layer_unitarity_residual",
        "controlled_reconstruction_unitarity_residual",
    ]
    max_residuals = {key: max(row[key] for row in family_rows) for key in residual_keys}
    conditions = [
        ("A1", source["source_unitary_residual"] < 1e-12),
        ("A2", source["source_block_unitarity_residual"] < 1e-12),
        ("A3", source["relative_closed_form_residual"] < 1e-12),
        ("A4", source["euler_abc_identity_residual"] < 1e-12),
        ("A5", source["euler_controlled_relative_residual"] < 1e-12),
        ("A6", source["controlled_block_reconstruction_residual"] < 1e-12),
        ("A7", source["constructive_unitary_residual"] < 1e-12),
        ("A8", len(family_rows) == 65),
        ("A9", max_residuals["constructive_unitary_residual"] < 1e-11),
        ("A10", max_residuals["euler_controlled_relative_residual"] < 1e-11),
    ]
    result: dict[str, Any] = {
        "title": "B7 w8_21 constructive local dressing",
        "version": 0,
        "method": METHOD,
        "status": "constructive_dressing_complete_no_resource_reduction_claim",
        "classification": "exact_two_cnot_local_dressing_normal_form",
        "template_id": "w8_21",
        "source_parameters": BASE_PARAMS,
        "source_bindings": source_bindings,
        "derived_factorization": {
            "source_form": "U = (I tensor U0) controlled(W)",
            "relative_block_euler": "W = Rz(alpha) Ry(2c) Rz(gamma), alpha=-a-b-pi, gamma=a-b-pi",
            "controlled_u_identity": "controlled(W) = (I tensor A) CX (I tensor B) CX (I tensor C)",
            "euler_layers": {
                "A": "Rz(-a-b-pi) Ry(c)",
                "B": "Ry(-c) Rz(b+pi)",
                "C": "Rz(a)",
            },
            "absorbed_normal_form": "U = (I tensor Ry(e) Rz(d)) CX (I tensor Ry(-c) Rz(b+pi)) CX (I tensor Rz(a))",
            "cnot_count": 2,
            "arbitrary_parameter_count": 5,
            "fixed_pi_rotation_count": 1,
        },
        "source_evidence": source,
        "family_validation": {"sample_count": len(family_rows), "max_residuals": max_residuals},
        "acceptance_conditions": [
            {"condition_id": condition_id, "passed": bool(passed)}
            for condition_id, passed in conditions
        ],
        "requirements_passed": sum(bool(passed) for _, passed in conditions),
        "requirements_failed": sum(not bool(passed) for _, passed in conditions),
        "resource_accounting": {
            "baseline_cnot_count": 2,
            "normal_form_cnot_count": 2,
            "baseline_arbitrary_parameter_count": 5,
            "normal_form_arbitrary_parameter_count": 5,
            "accepted_occurrence_removal": 0,
            "accepted_proxy_t_reduction": 0,
            "b7_credit": 0,
        },
        "claim_boundary": {
            "what_is_supported": "an exact constructive two-CNOT local-dressing normal form for the fixed w8_21 role skeleton, with a deterministic 65-point replay validation",
            "what_is_not_supported": "fewer CNOTs, fewer arbitrary rotations, an occurrence-removing rewrite, a global lower bound, exclusion of all other Clifford scaffolds, proxy-T reduction, B7 credit, or a solved B1/B7 frontier",
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
    family = result["family_validation"]
    return "\n".join(
        [
            "# B7 w8_21 Constructive Local Dressing",
            "",
            f"- Status: `{result['status']}`",
            f"- Classification: `{result['classification']}`",
            f"- Requirements: `{result['requirements_passed']}/{result['requirements_passed'] + result['requirements_failed']}`",
            f"- Payload hash: `{result['payload_hash']}`",
            "",
            "## Heuristic question",
            "",
            "Can an exact controlled-unitary dressing expose a rotation-free interface around the repeated w8_21 block, or does exact synthesis preserve all five continuous degrees of freedom?",
            "",
            "## Constructive factorization",
            "",
            "The relative block has the Euler form `W = Rz(alpha) Ry(2c) Rz(gamma)` with `alpha=-a-b-pi` and `gamma=a-b-pi`. The standard controlled-unitary identity gives `controlled(W) = (I tensor A) CX (I tensor B) CX (I tensor C)` with `A=Rz(-a-b-pi) Ry(c)`, `B=Ry(-c) Rz(b+pi)`, and `C=Rz(a)`.",
            "",
            "After absorbing A into the source control-zero branch, the exact normal form is",
            "",
            "`U = (I tensor Ry(e) Rz(d)) CX (I tensor Ry(-c) Rz(b+pi)) CX (I tensor Rz(a))`.",
            "",
            f"At the source point the constructive unitary residual is `{source['constructive_unitary_residual']:.3e}` and the controlled-relative residual is `{source['euler_controlled_relative_residual']:.3e}`. A deterministic family replay covers `{family['sample_count']}` points; the maximum constructive-unitary residual is `{family['max_residuals']['constructive_unitary_residual']:.3e}`.",
            "",
            "## Resource boundary",
            "",
            "The normal form keeps two CNOTs and five arbitrary parameters. It is therefore a constructive synthesis identity and a better scaffold for future local-dressing search, not a resource reduction. No occurrence, proxy-T, B7, lower-bound, or solved-frontier credit is assigned.",
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
        raise ValueError("constructive dressing packet already exists; refusing to overwrite")
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
                "constructive_residual": result["source_evidence"]["constructive_unitary_residual"],
                "payload_hash": result["payload_hash"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
