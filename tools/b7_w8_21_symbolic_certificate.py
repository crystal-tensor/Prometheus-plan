#!/usr/bin/env python3
"""Build a machine-checkable symbolic certificate for the fixed w8_21 skeleton.

This artifact proves a scoped identity for the role-normalized two-CNOT family:
the control/target block form, the closed relative block W, its half-trace
invariant, and the quadratic relation for W.  It deliberately does not turn
that identity into a compression theorem or a global KAK lower bound.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import sympy as sp


METHOD = "b7_w8_21_symbolic_certificate_v0"
TEMPLATE_ID = "w8_21"
RESULT_PATH = "results/B7_w8_21_symbolic_certificate_v0.json"
REPORT_PATH = "research/B7_w8_21_symbolic_certificate.md"
CERTIFICATE_PATH = "results/B7_w8_21_symbolic_certificate_candidate_v0.json"
SOURCE_RESULT_PATHS = [
    "results/B7_w8_21_kak_invariant_packet_v0.json",
    "results/B7_w8_21_controlled_invariant_closure_v0.json",
    "results/B7_w8_21_constructive_dressing_v0.json",
    "results/B7_w8_21_small_block_synthesis_v0.json",
    "results/B7_w8_21_broad_skeleton_search_v0.json",
    "results/B7_w8_21_euler_local_search_v0.json",
    "results/B7_w8_21_three_cnot_search_v0.json",
]
SOURCE_QASM = "results/b1_u3_phase_factored_optimizer/qasmbench_medium_exact/gcm_h6.qasm"

I = sp.I
a, b, c, d, e = sp.symbols("a b c d e", real=True)
I2 = sp.eye(2)
P0 = sp.diag(1, 0)
P1 = sp.diag(0, 1)
X = sp.Matrix([[0, 1], [1, 0]])
CX = sp.kronecker_product(P0, I2) + sp.kronecker_product(P1, X)


def stable_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rz(theta: sp.Expr) -> sp.Matrix:
    return sp.diag(sp.exp(-I * theta / 2), sp.exp(I * theta / 2))


def ry(theta: sp.Expr) -> sp.Matrix:
    return sp.Matrix(
        [[sp.cos(theta / 2), -sp.sin(theta / 2)], [sp.sin(theta / 2), sp.cos(theta / 2)]]
    )


def one_qubit(matrix: sp.Matrix) -> sp.Matrix:
    return sp.kronecker_product(I2, matrix)


def compose(gates: list[sp.Matrix]) -> sp.Matrix:
    result = sp.eye(4)
    for gate in gates:
        result = gate * result
    return result


def symbolic_source_unitary() -> sp.Matrix:
    return compose(
        [
            one_qubit(rz(a)),
            CX,
            one_qubit(rz(b)),
            one_qubit(ry(c)),
            one_qubit(rz(sp.pi)),
            CX,
            one_qubit(rz(d)),
            one_qubit(ry(e)),
        ]
    )


def symbolic_relative_block() -> sp.Matrix:
    unitary = symbolic_source_unitary()
    u0 = unitary[:2, :2]
    u1 = unitary[2:4, 2:4]
    return (sp.conjugate(u0).T * u1).applyfunc(sp.simplify)


def exact_certificate() -> dict[str, Any]:
    unitary = symbolic_source_unitary()
    u0 = unitary[:2, :2]
    u1 = unitary[2:4, 2:4]
    relative = symbolic_relative_block()
    expected_relative = sp.Matrix(
        [
            [-sp.exp(I * b) * sp.cos(c), -sp.exp(I * a) * sp.sin(c)],
            [sp.exp(-I * a) * sp.sin(c), -sp.exp(-I * b) * sp.cos(c)],
        ]
    )
    tau = sp.simplify(sp.trace(relative) / 2)
    quadratic = (relative * relative - 2 * tau * relative + I2).applyfunc(
        lambda value: sp.simplify(sp.expand_complex(value))
    )
    off_block = [sp.simplify(unitary[i, j]) for i in range(4) for j in range(4) if (i < 2) != (j < 2)]
    expected_rows = {
        "control_target_block_form": all(value == 0 for value in off_block),
        "relative_block_closed_form": all(
            sp.simplify(relative[i, j] - expected_relative[i, j]) == 0
            for i in range(2)
            for j in range(2)
        ),
        "relative_half_trace": sp.simplify(tau + sp.cos(b) * sp.cos(c)) == 0,
        "relative_unitarity": all(
            sp.simplify((sp.conjugate(relative).T * relative - I2)[i, j]) == 0
            for i in range(2)
            for j in range(2)
        ),
        "quadratic_identity": all(value == 0 for value in quadratic),
        "relative_invariant_independent_of_d_e": not (relative.has(d) or relative.has(e)),
    }
    return {
        "symbol_names": ["a", "b", "c", "d", "e"],
        "unitary_block_form": "U = |0><0| tensor U0 + |1><1| tensor U1",
        "relative_block_expression": [[str(relative[i, j]) for j in range(2)] for i in range(2)],
        "relative_block_expected_expression": [[str(expected_relative[i, j]) for j in range(2)] for i in range(2)],
        "relative_half_trace_expression": str(tau),
        "relative_quadratic_expression": "W**2 - 2*tau*W + I2",
        "magic_characteristic_polynomial_candidate": "(lambda**2 - 2*tau*lambda + 1)**2",
        "exact_checks": [{"check_id": key, "passed": bool(value)} for key, value in expected_rows.items()],
        "exact_checks_passed": sum(bool(value) for value in expected_rows.values()),
        "exact_checks_failed": sum(not bool(value) for value in expected_rows.values()),
    }


def numeric_source_matrix() -> list[list[dict[str, float]]]:
    values = {
        a: 1.4922506383856682,
        b: 2.1870074319274799,
        c: 0.52538524712872736,
        d: 2.538142068316358,
        e: 1.1254377896453873,
    }
    matrix = np.array(symbolic_source_unitary().subs(values).evalf(), dtype=complex)
    return [[{"real": float(value.real), "imag": float(value.imag)} for value in row] for row in matrix]


def build(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    theorem = exact_certificate()
    source_bindings = {
        path: {"path": path, "sha256": file_sha256(root / path)}
        for path in SOURCE_RESULT_PATHS + [SOURCE_QASM]
    }
    source_results = {path: json.loads((root / path).read_text(encoding="utf-8")) for path in SOURCE_RESULT_PATHS}
    scaffold_exclusions = [
        {
            "artifact": path,
            "status": source_results[path].get("status"),
            "requirements_passed": source_results[path].get("requirements_passed"),
            "claim_boundary": "numeric or bounded scaffold exclusion only; not a global theorem",
        }
        for path in SOURCE_RESULT_PATHS[3:]
    ]
    numeric_search_digest = {
        "prior_optimizer_runs": 43480,
        "three_cnot_attempted_optimizer_runs": 8880,
        "three_cnot_passing_candidate_count": 0,
        "tested_scaffold_artifacts": scaffold_exclusions,
    }
    certificate = {
        "title": "B7 w8_21 scoped symbolic invariant certificate",
        "version": 0,
        "method": METHOD,
        "template_id": TEMPLATE_ID,
        "certificate_class": "scoped_exact_symbolic_relative_block_certificate",
        "theorem": theorem,
        "source_bindings": source_bindings,
        "numeric_search_digest": numeric_search_digest,
        "target_matrix": {
            "representation": "normalized source role block in control-target basis",
            "matrix": numeric_source_matrix(),
            "source_qasm": SOURCE_QASM,
        },
        "uncovered_routes": [
            "This certificate does not exclude other two-CNOT local scaffolds.",
            "This certificate does not exclude three-CNOT or broader circuit identities.",
            "This certificate does not prove that five arbitrary parameters are resource-minimal.",
            "This certificate does not prove occurrence removal or a full-circuit rewrite.",
        ],
        "claim_boundary": {
            "what_is_supported": "exact symbolic control-block, relative-block, half-trace, and quadratic identities for the fixed w8_21 role skeleton, plus machine-checked source-point binding",
            "what_is_not_supported": "a global KAK theorem, CNOT lower bound, arbitrary-rotation lower bound, occurrence-removing rewrite, proxy-T reduction, B7 credit, or solved B1/B7 frontier",
            "new_rewrite_claimed": False,
            "global_lower_bound_claimed": False,
            "physical_resource_reduction_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
    }
    certificate["payload_hash"] = stable_hash(certificate)
    result = {
        "title": "B7 w8_21 machine-checked symbolic certificate",
        "version": 0,
        "method": METHOD,
        "status": "symbolic_certificate_complete_scoped_no_resource_claim",
        "classification": "exact_fixed_skeleton_symbolic_invariant_certificate",
        "template_id": TEMPLATE_ID,
        "theorem": theorem,
        "source_bindings": source_bindings,
        "numeric_search_digest": numeric_search_digest,
        "certificate_candidate": CERTIFICATE_PATH,
        "certificate_candidate_hash": certificate["payload_hash"],
        "machine_checked": theorem["exact_checks_failed"] == 0,
        "claim_boundary": certificate["claim_boundary"],
        "artifacts": {"result": RESULT_PATH, "markdown_report": REPORT_PATH, "candidate": CERTIFICATE_PATH},
    }
    result["payload_hash"] = stable_hash(result)
    return result, certificate


def report(result: dict[str, Any]) -> str:
    theorem = result["theorem"]
    digest = result["numeric_search_digest"]
    lines = [
        "# B7 w8_21 Machine-Checked Symbolic Certificate",
        "",
        f"- Status: `{result['status']}`",
        f"- Classification: `{result['classification']}`",
        f"- Exact checks: `{theorem['exact_checks_passed']}/{theorem['exact_checks_passed'] + theorem['exact_checks_failed']}`",
        f"- Machine checked: `{result['machine_checked']}`",
        f"- Payload hash: `{result['payload_hash']}`",
        f"- Candidate hash: `{result['certificate_candidate_hash']}`",
        "",
        "## Heuristic question",
        "",
        "Can a fixed two-CNOT circuit family carry a compact exact invariant certificate without that certificate being mistaken for a compression theorem?",
        "",
        "## Exact symbolic result",
        "",
        "SymPy constructs the source-order role block with symbolic parameters `a,b,c,d,e`. It proves the control-target block form, the closed relative block",
        "",
        "`W = [[-exp(i*b)*cos(c), -exp(i*a)*sin(c)], [exp(-i*a)*sin(c), -exp(-i*b)*cos(c)]]`,",
        "",
        "the half-trace `tau = -cos(b)*cos(c)`, unitarity, independence from `d,e`, and the exact Cayley-Hamilton relation `W^2 - 2*tau*W + I = 0`.",
        "",
        f"All `{theorem['exact_checks_passed']}` exact checks pass. The certificate is bound to the source QASM and to the existing fixed-family numerical closure; the prior search digest retains `{digest['prior_optimizer_runs']}` optimizer runs and `{digest['three_cnot_attempted_optimizer_runs']}` three-CNOT attempts with `{digest['three_cnot_passing_candidate_count']}` passing candidates.",
        "",
        "## Boundary",
        "",
        "This is a scoped exact identity for one fixed role skeleton. It does not prove a global KAK obstruction, minimality, a shorter rewrite, resource reduction, or B7 credit. The next technical question is whether this invariant can be connected to a source-level occurrence-removing certificate without introducing equally expensive local parameters.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    result_path = root / RESULT_PATH
    report_path = root / REPORT_PATH
    candidate_path = root / CERTIFICATE_PATH
    if result_path.exists() or report_path.exists() or candidate_path.exists():
        raise ValueError("symbolic certificate artifacts already exist; refusing to overwrite")
    result, certificate = build(root)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(report(result), encoding="utf-8")
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(json.dumps(certificate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "machine_checked": result["machine_checked"],
        "exact_checks_passed": result["theorem"]["exact_checks_passed"],
        "exact_checks_failed": result["theorem"]["exact_checks_failed"],
        "candidate_hash": result["certificate_candidate_hash"],
        "payload_hash": result["payload_hash"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
