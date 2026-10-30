#!/usr/bin/env python3
"""Preregister and execute the B9 R201 continuous projective-patch test.

The scientific object is an exact homogeneous polynomial commutator matrix.
Each candidate column is denominator-cleared independently by a power of
D=a^2+b^2+c^2, which is nonzero on the declared real projective domain.
Frozen couplings cannot execute until a public commit hash-binds this file,
the contract, and the independent auditor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import subprocess
import sys
import time
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any

import sympy as sp

import b9_r198_continuous_frame_stress as base


EXPERIMENT_ID = "B9-R201-continuous-projective-bloch-patch-certificate"
METHOD = "b9_r201_homogeneous_projective_patch_certificate_v1"
VERSION = "0.1.0"
LAST_UPDATED = "2026-10-31"
CONTRACT_PATH = Path("benchmarks/B9_R201_projective_patch_contract_v0.json")
EXPECTED_CONTRACT_SHA256 = "b3c960f5081a776ccd7165c0146c39e81bf6170820ac593c0f37c8b928b6cb99"
ENGINEERING_PATH = Path("results/B9_R201_engineering_probe_v0.json")
RESULT_PATH = Path("results/B9_R201_projective_patch_certificate_v1.json")
REPORT_PATH = Path("research/B9_R201_projective_patch_certificate.md")

ENGINEERING_COUPLING = Fraction(13, 32)
FROZEN_HOLDOUT_COUPLINGS = (Fraction(127, 128), Fraction(131, 128))
ENGINEERING_ANCHORS = (
    (0, 0, 1),
    (1, 0, 1),
    (0, 1, 1),
    (1, 1, 1),
    (-1, 1, 2),
    (2, -1, 1),
    (1, 0, 0),
    (0, 1, 0),
)
MAIN_MINOR_ANCHORS = ENGINEERING_ANCHORS + (
    (-2, 1, 3),
    (1, -2, 3),
    (2, 2, 1),
    (-1, -2, 2),
    (3, -1, 2),
    (1, 3, 2),
)
BASIS_SELECTION_PRIME = 1_000_003
MAX_SELECTED_MINORS = 12
A, B, C, U = sp.symbols("a b c u")
D = A * A + B * B + C * C
VARS = (A, B, C)

Operator = base.Operator
PolynomialOperator = dict[str, sp.Poly]

PREVIOUSLY_OBSERVED_COUPLINGS = (
    set(base.PREVIOUSLY_OBSERVED_COUPLINGS)
    | set(base.FROZEN_HOLDOUT_COUPLINGS)
)

FALSE_CLAIMS = [
    "global_continuous_tangent_frame_theorem",
    "all_bloch_sphere_fermionization_exclusion",
    "all_irrational_frame_exclusion_outside_declared_patch",
    "higher_order_majorana_charge_exclusion",
    "nonlocal_duality_exclusion",
    "interacting_integrability_exclusion",
    "complete_integrability_exclusion",
    "nonintegrability_theorem",
    "quantum_chaos_theorem",
    "spectral_hardness_theorem",
    "quantum_pcp_theorem",
    "nlts_theorem",
    "bqp_separation",
    "hardware_relevance",
    "solved_frontier",
]


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def polynomial_axes() -> dict[str, dict[str, sp.Expr]]:
    return {
        "P": {"X": 2 * A * C, "Y": 2 * B * C, "Z": C * C - A * A - B * B},
        "Q": {"X": C * C - A * A + B * B, "Y": -2 * A * B, "Z": -2 * A * C},
        "R": {"X": -2 * A * B, "Y": C * C + A * A - B * B, "Z": -2 * B * C},
    }


def frame_identity_checks() -> dict[str, Any]:
    frame = polynomial_axes()
    vectors = {
        label: sp.Matrix([frame[label].get(pauli, 0) for pauli in "XYZ"])
        for label in ("P", "Q", "R")
    }
    p, q, r = (vectors[label] for label in ("P", "Q", "R"))
    expressions: dict[str, sp.Expr | list[sp.Expr]] = {
        "p_norm": sp.expand(p.dot(p) - D**2),
        "q_norm": sp.expand(q.dot(q) - D**2),
        "r_norm": sp.expand(r.dot(r) - D**2),
        "p_dot_q": sp.expand(p.dot(q)),
        "q_dot_r": sp.expand(q.dot(r)),
        "r_dot_p": sp.expand(r.dot(p)),
        "p_cross_q": [sp.expand(value) for value in p.cross(q) - D * r],
        "q_cross_r": [sp.expand(value) for value in q.cross(r) - D * p],
        "r_cross_p": [sp.expand(value) for value in r.cross(p) - D * q],
        "orientation": sp.expand(sp.det(sp.Matrix.hstack(p, q, r)) - D**3),
    }
    checks = {
        label: (
            all(value == 0 for value in expression)
            if isinstance(expression, list)
            else expression == 0
        )
        for label, expression in expressions.items()
    }
    return {
        "identity_count": len(checks),
        "identity_pass_count": sum(checks.values()),
        "checks": checks,
        "checked": all(checks.values()),
    }


def expand_axes(
    n: int,
    site_axes: dict[int, dict[str, sp.Expr]],
    scale: int = 1,
) -> PolynomialOperator:
    partial: dict[str, sp.Expr] = {"I" * n: sp.Integer(scale)}
    for site in sorted(site_axes):
        updated: dict[str, sp.Expr] = {}
        for word, coefficient in partial.items():
            for pauli, local_coefficient in site_axes[site].items():
                chars = list(word)
                chars[site] = pauli
                output = "".join(chars)
                updated[output] = sp.expand(
                    updated.get(output, 0) + coefficient * local_coefficient
                )
        partial = updated
    return {
        word: sp.Poly(coefficient, *VARS, domain=sp.ZZ)
        for word, coefficient in partial.items()
        if coefficient != 0
    }


@cache
def candidate_pool(n: int) -> tuple[tuple[str, PolynomialOperator], ...]:
    frame = polynomial_axes()
    gamma_labels = [(site, endpoint) for site in range(n) for endpoint in ("Q", "R")]
    entries: list[tuple[str, PolynomialOperator]] = []
    for site, endpoint in gamma_labels:
        axes = {index: frame["P"] for index in range(site)}
        axes[site] = frame[endpoint]
        entries.append((f"gamma:{site}:{endpoint}", expand_axes(n, axes)))
    for left_index, (left_site, left_endpoint) in enumerate(gamma_labels):
        for right_site, right_endpoint in gamma_labels[left_index + 1 :]:
            if left_site == right_site:
                operator = expand_axes(n, {left_site: frame["P"]}, scale=-1)
            else:
                axes: dict[int, dict[str, sp.Expr]] = {}
                sign = 1
                if left_endpoint == "Q":
                    axes[left_site] = frame["R"]
                else:
                    axes[left_site] = frame["Q"]
                    sign = -1
                for site in range(left_site + 1, right_site):
                    axes[site] = frame["P"]
                axes[right_site] = frame[right_endpoint]
                operator = expand_axes(n, axes, scale=sign)
            entries.append(
                (
                    f"bilinear:{left_site}:{left_endpoint}:{right_site}:{right_endpoint}",
                    operator,
                )
            )
    entries.append(("parity", expand_axes(n, {site: frame["P"] for site in range(n)})))
    return tuple(entries)


def commutator(hamiltonian: Operator, candidate: PolynomialOperator) -> PolynomialOperator:
    output: dict[str, sp.Poly] = {}
    zero = sp.Poly(0, *VARS, domain=sp.ZZ)
    for h_word, h_coefficient in hamiltonian.items():
        for candidate_word, candidate_coefficient in candidate.items():
            if not base.pauli_anticommutes(h_word, candidate_word):
                continue
            phase, output_word = base.pauli_multiply(h_word, candidate_word)
            sign = int(round((phase / 1j).real))
            output[output_word] = output.get(output_word, zero) + candidate_coefficient * int(h_coefficient) * sign
    return {
        word: sp.Poly(coefficient, *VARS, domain=sp.ZZ)
        for word, coefficient in output.items()
        if not coefficient.is_zero
    }


def poly_payload(poly: sp.Poly) -> list[list[Any]]:
    return [[list(monomial), str(int(coefficient))] for monomial, coefficient in poly.terms()]


def symbolic_matrix(
    n: int, coupling: Fraction
) -> tuple[list[str], list[PolynomialOperator], list[str], str]:
    entries = list(candidate_pool(n))
    labels = [label for label, _ in entries]
    hamiltonian = base.hamiltonian_operator(n, coupling)
    columns = [commutator(hamiltonian, operator) for _, operator in entries]
    output_words = sorted({word for column in columns for word in column})
    triples = [
        [word, column_index, poly_payload(coefficient)]
        for column_index, column in enumerate(columns)
        for word, coefficient in sorted(column.items())
    ]
    return labels, columns, output_words, canonical_hash(
        {"labels": labels, "output_words": output_words, "triples": triples}
    )


def select_rows_at_anchor(
    columns: list[PolynomialOperator],
    output_words: list[str],
    anchor: tuple[int, int, int],
    prime: int,
) -> list[str]:
    pivots: dict[int, dict[int, int]] = {}
    selected: list[str] = []
    substitutions = dict(zip(VARS, anchor))
    for word in output_words:
        vector = {
            column_index: int(
                columns[column_index]
                .get(word, sp.Poly(0, *VARS, domain=sp.ZZ))
                .as_expr()
                .subs(substitutions)
            )
            % prime
            for column_index in range(len(columns))
        }
        vector = {index: value for index, value in vector.items() if value}
        while vector:
            pivot = min(vector)
            if pivot not in pivots:
                inverse = pow(vector[pivot], prime - 2, prime)
                pivots[pivot] = {
                    index: (value * inverse) % prime for index, value in vector.items()
                }
                selected.append(word)
                break
            factor = vector[pivot]
            for index, value in pivots[pivot].items():
                updated = (vector.get(index, 0) - factor * value) % prime
                if updated:
                    vector[index] = updated
                else:
                    vector.pop(index, None)
        if len(selected) == len(columns):
            break
    return selected


def matrix_probe(n: int, coupling: Fraction, anchors: tuple[tuple[int, int, int], ...]) -> dict[str, Any]:
    labels, columns, output_words, matrix_hash = symbolic_matrix(n, coupling)
    selections = []
    for anchor in anchors:
        rows = select_rows_at_anchor(columns, output_words, anchor, BASIS_SELECTION_PRIME)
        selections.append(
            {
                "anchor": list(anchor),
                "D": sum(value * value for value in anchor),
                "rank": len(rows),
                "full_column_rank": len(rows) == len(columns),
                "row_words": rows,
                "row_words_sha256": canonical_hash(rows),
            }
        )
    column_degrees = [
        max((coefficient.total_degree() for coefficient in column.values()), default=0)
        for column in columns
    ]
    return {
        "coupling": fraction_text(coupling),
        "n": n,
        "candidate_column_count": len(columns),
        "candidate_labels_sha256": canonical_hash(labels),
        "output_basis_size": len(output_words),
        "polynomial_commutator_nonzero_count": sum(len(column) for column in columns),
        "polynomial_commutator_matrix_sha256": matrix_hash,
        "column_total_degrees": column_degrees,
        "maximum_column_total_degree": max(column_degrees),
        "maximal_minor_total_degree_bound": sum(column_degrees),
        "anchor_selections": selections,
        "full_rank_anchor_count": sum(item["full_column_rank"] for item in selections),
        "checked": all(item["full_column_rank"] for item in selections),
    }


def primitive_polynomial(poly: sp.Poly) -> sp.Poly:
    _, primitive = sp.polys.polytools.primitive(sp.Poly(poly, *VARS, domain=sp.ZZ))
    primitive = sp.Poly(primitive, *VARS, domain=sp.ZZ)
    if primitive.LC() < 0:
        primitive = -primitive
    return primitive


def determinant_for_rows(columns: list[PolynomialOperator], row_words: list[str]) -> sp.Poly:
    matrix = sp.Matrix(
        [
            [
                columns[column_index]
                .get(word, sp.Poly(0, *VARS, domain=sp.ZZ))
                .as_expr()
                for column_index in range(len(columns))
            ]
            for word in row_words
        ]
    )
    return primitive_polynomial(sp.Poly(matrix.det(method="domain-ge"), *VARS, domain=sp.ZZ))


def solve_exact_patch(n: int, coupling: Fraction, cpu_hour_cap: int) -> dict[str, Any]:
    started = time.monotonic()
    labels, columns, output_words, matrix_hash = symbolic_matrix(n, coupling)
    selections: list[dict[str, Any]] = []
    unique_row_hashes: set[str] = set()
    row_sets: list[list[str]] = []
    for anchor in MAIN_MINOR_ANCHORS:
        rows = select_rows_at_anchor(columns, output_words, anchor, BASIS_SELECTION_PRIME)
        row_hash = canonical_hash(rows)
        selections.append({"anchor": list(anchor), "rank": len(rows), "row_words_sha256": row_hash})
        if len(rows) == len(columns) and row_hash not in unique_row_hashes:
            unique_row_hashes.add(row_hash)
            row_sets.append(rows)
        if len(row_sets) == MAX_SELECTED_MINORS:
            break
    if not row_sets:
        return {
            "coupling": fraction_text(coupling),
            "n": n,
            "status": "inconclusive_resource_cap",
            "reason": "no full-column-rank engineering anchor",
            "matrix_sha256": matrix_hash,
            "selections": selections,
            "checked": False,
        }
    determinants: list[sp.Poly] = []
    determinant_records = []
    for rows in row_sets:
        if time.monotonic() - started > cpu_hour_cap * 3600:
            break
        determinant = determinant_for_rows(columns, rows)
        determinants.append(determinant)
        determinant_records.append(
            {
                "row_words_sha256": canonical_hash(rows),
                "total_degree": determinant.total_degree(),
                "term_count": len(determinant.terms()),
                "primitive_terms": poly_payload(determinant),
                "primitive_terms_sha256": canonical_hash(poly_payload(determinant)),
            }
        )
    if not determinants or len(determinants) < len(row_sets):
        return {
            "coupling": fraction_text(coupling),
            "n": n,
            "status": "inconclusive_resource_cap",
            "reason": "minor computation did not finish under the frozen cap",
            "matrix_sha256": matrix_hash,
            "minor_records": determinant_records,
            "checked": False,
        }
    groebner_started = time.monotonic()
    saturated_generators = [poly.as_expr() for poly in determinants] + [1 - U * D]
    basis = sp.groebner(saturated_generators, U, A, B, C, order="grevlex", domain=sp.QQ)
    unit_ideal = len(basis.polys) == 1 and basis.polys[0].as_expr() == 1
    elapsed = time.monotonic() - started
    certificate_verified = False
    status = "inconclusive_resource_cap"
    return {
        "coupling": fraction_text(coupling),
        "n": n,
        "status": status,
        "candidate_column_count": len(columns),
        "candidate_labels_sha256": canonical_hash(labels),
        "matrix_sha256": matrix_hash,
        "minor_count": len(determinants),
        "minor_records": determinant_records,
        "saturation_equation": "1-u*(a^2+b^2+c^2)",
        "groebner_order": "grevlex(u,a,b,c)",
        "groebner_basis_size": len(basis.polys),
        "groebner_basis_expressions": [str(poly.as_expr()) for poly in basis.polys],
        "groebner_basis_sha256": canonical_hash(
            [str(poly.as_expr()) for poly in basis.polys]
        ),
        "unit_ideal": unit_ideal,
        "candidate_unit_ideal_detected": unit_ideal,
        "nullstellensatz_certificate_verified": certificate_verified,
        "acceptance_blocker": (
            "exact Nullstellensatz or independently replayable ideal-membership trace is not yet emitted"
            if unit_ideal
            else "the selected-minor saturated ideal is not certified empty"
        ),
        "complex_solver_elapsed_seconds": round(time.monotonic() - groebner_started, 6),
        "elapsed_seconds": round(elapsed, 6),
        "full_matrix_root_recheck_required": not unit_ideal,
        "checked": certificate_verified,
    }


def run_solver_isolated(
    root: Path,
    n: int,
    coupling: Fraction,
    cpu_hour_cap: int,
    memory_gib: int,
) -> dict[str, Any]:
    output = root / "results" / f".B9_R201_worker_n{n}_{coupling.numerator}_{coupling.denominator}.json"
    output.unlink(missing_ok=True)

    def limits() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_hour_cap * 3600, cpu_hour_cap * 3600 + 30))
        memory_bytes = memory_gib * 1024**3
        resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))

    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--worker",
        "--worker-n",
        str(n),
        "--worker-coupling",
        fraction_text(coupling),
        "--worker-cpu-hours",
        str(cpu_hour_cap),
        "--output",
        str(output.relative_to(root)),
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=cpu_hour_cap * 3600 + 90,
            preexec_fn=limits,
            check=False,
        )
    except subprocess.TimeoutExpired:
        completed = None
    if completed and completed.returncode == 0 and output.exists():
        result = json.loads(output.read_text())
        output.unlink(missing_ok=True)
        return result
    stderr = "" if completed is None else completed.stderr[-4000:]
    output.unlink(missing_ok=True)
    return {
        "coupling": fraction_text(coupling),
        "n": n,
        "status": "inconclusive_resource_cap",
        "reason": "isolated exact solver exceeded the frozen CPU, wall-clock, or memory cap",
        "worker_stderr_tail": stderr,
        "checked": False,
    }


def git_bytes(root: Path, commit: str, relative_path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{relative_path}"], cwd=root)


def verify_public_freeze(root: Path, preregistration_commit: str) -> dict[str, Any]:
    if not preregistration_commit:
        raise ValueError("--preregistration-commit is required for frozen holdouts")
    contract = json.loads((root / CONTRACT_PATH).read_text())
    remote_main = subprocess.check_output(
        ["git", "ls-remote", "origin", "refs/heads/main"], cwd=root, text=True
    ).split()[0]
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", preregistration_commit, remote_main],
        cwd=root,
        check=False,
    ).returncode == 0
    files = []
    for relative_path in [str(CONTRACT_PATH), *contract["code_freeze"]["paths"]]:
        current = (root / relative_path).read_bytes()
        frozen = git_bytes(root, preregistration_commit, relative_path)
        files.append(
            {
                "path": relative_path,
                "current_sha256": hashlib.sha256(current).hexdigest(),
                "frozen_sha256": hashlib.sha256(frozen).hexdigest(),
                "matches": current == frozen,
            }
        )
    return {
        "preregistration_commit": preregistration_commit,
        "remote_main": remote_main,
        "ancestor_of_remote_main": ancestor,
        "files": files,
        "verified": bool(ancestor and all(item["matches"] for item in files)),
    }


def protocol(root: Path) -> dict[str, Any]:
    contract = json.loads((root / CONTRACT_PATH).read_text())
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "contract_sha256": sha256_file(root / CONTRACT_PATH),
        "frame_identities": frame_identity_checks(),
        "engineering_anchors": [list(anchor) for anchor in ENGINEERING_ANCHORS],
        "main_minor_anchors": [list(anchor) for anchor in MAIN_MINOR_ANCHORS],
        "basis_selection_prime": BASIS_SELECTION_PRIME,
        "maximum_selected_minors": MAX_SELECTED_MINORS,
        "frozen_holdouts": [fraction_text(value) for value in FROZEN_HOLDOUT_COUPLINGS],
        "resource_caps": contract["resource_caps"],
        "false_claims": FALSE_CLAIMS,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    return {**payload, "protocol_sha256": canonical_hash(payload)}


def build_engineering_probe(root: Path) -> dict[str, Any]:
    probe = matrix_probe(4, ENGINEERING_COUPLING, ENGINEERING_ANCHORS)
    positive_control = base.rational_frame_row(
        6,
        Fraction(0),
        {"frame_id": "positive_control_A", "c": "-4/5", "s": "3/5"},
        base.MODULAR_PRIMES,
    )
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "mode": "engineering_probe_only",
        "status": "public_preregistration_execution_pending",
        "protocol": protocol(root),
        "matrix_probe": probe,
        "positive_control": positive_control,
        "frozen_holdouts_executed": False,
        "acceptance_count": 0,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    payload["payload_sha256"] = canonical_hash(payload)
    return payload


def build_result(root: Path, preregistration_commit: str) -> dict[str, Any]:
    freeze = verify_public_freeze(root, preregistration_commit)
    if not freeze["verified"]:
        raise RuntimeError("public preregistration freeze verification failed")
    contract = json.loads((root / CONTRACT_PATH).read_text())
    if not contract["execution_readiness"]["frozen_holdouts_may_execute"]:
        raise RuntimeError(
            "R201 frozen holdouts remain sealed until the declared certificate and independent-rebuild blockers close"
        )
    n4_rows = [
        run_solver_isolated(
            root,
            4,
            coupling,
            contract["resource_caps"]["n4_complex_solver_cpu_hours"],
            contract["resource_caps"]["n4_memory_gib"],
        )
        for coupling in FROZEN_HOLDOUT_COUPLINGS
    ]
    n4_resolved = all(
        row["status"]
        in {"checked_complex_projective_full_rank", "checked_real_projective_full_rank_only"}
        for row in n4_rows
    )
    n5_rows = (
        [
            run_solver_isolated(
                root,
                5,
                coupling,
                contract["resource_caps"]["n5_cpu_hours"],
                contract["resource_caps"]["n5_memory_gib"],
            )
            for coupling in FROZEN_HOLDOUT_COUPLINGS
        ]
        if n4_resolved
        else []
    )
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "status": (
            "checked_continuous_projective_patch_boundary"
            if n4_resolved and all(row["checked"] for row in n5_rows)
            else "continuous_projective_patch_unresolved"
        ),
        "public_freeze": freeze,
        "protocol": protocol(root),
        "n4_rows": n4_rows,
        "n5_rows": n5_rows,
        "n5_execution_condition_satisfied": n4_resolved,
        "frozen_holdouts_executed": True,
        "false_claims": {claim: False for claim in FALSE_CLAIMS},
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    payload["payload_sha256"] = canonical_hash(payload)
    return payload


def render_report(result: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# B9 R201 Continuous Projective Bloch-Patch Certificate",
            "",
            f"- Status: `{result['status']}`",
            f"- Public preregistration commit: `{result['public_freeze']['preregistration_commit']}`",
            f"- N4 rows: `{len(result['n4_rows'])}`",
            f"- N5 rows: `{len(result['n5_rows'])}`",
            "- Scientific promotion: `false`",
            "- New credit: `0`",
            "",
            "R201 tests exact full-column rank on one declared continuous homogeneous projective patch. It does not prove a global tangent-frame theorem, exclude higher-order or nonlocal charges, establish interacting nonintegrability, or support Quantum PCP, NLTS, BQP, hardware, solved-frontier, or new-credit claims.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--protocol", action="store_true")
    modes.add_argument("--engineering-probe", action="store_true")
    modes.add_argument("--execute-frozen-holdouts", action="store_true")
    modes.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--preregistration-commit", default="")
    parser.add_argument("--worker-n", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--worker-coupling", default="", help=argparse.SUPPRESS)
    parser.add_argument("--worker-cpu-hours", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    if sha256_file(root / CONTRACT_PATH) != EXPECTED_CONTRACT_SHA256:
        raise RuntimeError("R201 contract hash mismatch")
    if args.protocol:
        result: dict[str, Any] = protocol(root)
    elif args.engineering_probe:
        result = build_engineering_probe(root)
    elif args.worker:
        result = solve_exact_patch(
            args.worker_n,
            Fraction(args.worker_coupling),
            args.worker_cpu_hours,
        )
    else:
        result = build_result(root, args.preregistration_commit)
    output = args.output or (RESULT_PATH if args.execute_frozen_holdouts else ENGINEERING_PATH)
    (root / output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if args.execute_frozen_holdouts:
        (root / args.report).write_text(render_report(result))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
