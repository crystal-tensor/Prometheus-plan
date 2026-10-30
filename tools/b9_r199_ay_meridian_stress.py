#!/usr/bin/env python3
"""Preregister and execute the B9 R199 out-of-XZ meridian stress.

The acceptance couplings remain inaccessible until a public commit hash-binds
the contract.  Engineering mode uses only a previously observed coupling.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any

import sympy as sp

import b9_r198_continuous_frame_stress as base


EXPERIMENT_ID = "B9-R199-continuous-ay-meridian-frame-stress"
METHOD = "b9_r199_ay_meridian_stress_v1"
VERSION = "1.0"
LAST_UPDATED = "2026-10-30"
STATUS_ACCEPTED = "checked_continuous_ay_meridian_boundary"
STATUS_REJECTED = "continuous_ay_meridian_boundary_rejected"

CONTRACT_PATH = Path("benchmarks/B9_R199_ay_meridian_contract_v0.json")
EXPECTED_CONTRACT_SHA256 = (
    "a9679357747deb983de1285946ac97c1679c018b383a8e5e0d9c2c9cc6bcb1cb"
)
RESULT_PATH = Path("results/B9_R199_ay_meridian_stress_v1.json")
REPORT_PATH = Path("research/B9_R199_ay_meridian_stress.md")

ENGINEERING_COUPLING = Fraction(13, 32)
FROZEN_HOLDOUT_COUPLINGS = (Fraction(97, 128), Fraction(107, 128))
CONTINUOUS_SIZES = (4, 5)
GRID_SIZES = (6, 8, 10)
GRID_BOUND = 7
GRID_EXPECTED_COUNT = 72
GRID_EXPECTED_SHA256 = (
    "d39600595c4b54b622e6a76acdf4e0838322901d13aa3b72bda8a67599547842"
)
INITIAL_MINOR_ANCHORS = (0, 1, 2, 4)
MAX_ADAPTIVE_ROUNDS = 12
MODULAR_PRIMES = (1_000_003, 1_000_033)
BASIS_SELECTION_PRIME = MODULAR_PRIMES[0]
AUDIT_PRIME = 1_000_037

T = base.T
D = base.D
Axis = base.Axis
Operator = base.Operator
PolynomialOperator = base.PolynomialOperator

AXIS_A: Axis = {"X": Fraction(-4, 5), "Z": Fraction(3, 5)}
AXIS_B: Axis = {"X": Fraction(-3, 5), "Z": Fraction(-4, 5)}
AXIS_Y: Axis = {"Y": Fraction(1)}

PREVIOUSLY_OBSERVED_COUPLINGS = set(base.PREVIOUSLY_OBSERVED_COUPLINGS) | {
    Fraction(89, 128),
    Fraction(101, 128),
}

TRUE_CLAIMS = [
    "r199_contract_publicly_frozen_before_acceptance_execution",
    "r199_holdout_couplings_unseen_before_protocol_freeze",
    "continuous_ay_meridian_quadratic_majorana_pool_has_no_extra_charge_at_n4_n5",
    "declared_72_frame_grid_has_no_extra_quadratic_majorana_charge_at_n6_n8_n10",
    "zero_coupling_ay_origin_control_recovers_extra_exact_charges",
    "r198_candidate_survives_declared_r199_out_of_xz_adversary",
]

FALSE_CLAIMS = [
    "all_bloch_sphere_fermionization_exclusion",
    "full_two_dimensional_bloch_sphere_exclusion",
    "nonlinear_frame_mixture_exclusion",
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


def fraction_text(value: Fraction) -> str:
    return base.fraction_text(value)


def canonical_hash(value: Any) -> str:
    return base.canonical_hash(value)


def vector(axis: Axis) -> tuple[Fraction, Fraction, Fraction]:
    return tuple(axis.get(pauli, Fraction(0)) for pauli in "XYZ")  # type: ignore[return-value]


def dot(
    left: tuple[Fraction, Fraction, Fraction],
    right: tuple[Fraction, Fraction, Fraction],
) -> Fraction:
    return sum((a * b for a, b in zip(left, right)), Fraction(0))


def cross(
    left: tuple[Fraction, Fraction, Fraction],
    right: tuple[Fraction, Fraction, Fraction],
) -> tuple[Fraction, Fraction, Fraction]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def scaled_axis(axis: Axis, scale: Fraction) -> Axis:
    return {
        pauli: coefficient * scale
        for pauli, coefficient in axis.items()
        if coefficient * scale
    }


def add_axes(*axes: Axis) -> Axis:
    result: Axis = {}
    for axis in axes:
        for pauli, coefficient in axis.items():
            result[pauli] = result.get(pauli, Fraction(0)) + coefficient
    return {pauli: coefficient for pauli, coefficient in result.items() if coefficient}


def fraction_frame(c_value: Fraction, s_value: Fraction) -> dict[str, Axis]:
    return {
        "P": add_axes(scaled_axis(AXIS_A, c_value), scaled_axis(AXIS_Y, s_value)),
        "Q": add_axes(scaled_axis(AXIS_A, -s_value), scaled_axis(AXIS_Y, c_value)),
        "R": dict(AXIS_B),
    }


def frame_algebra_checks() -> dict[str, Any]:
    probes = [
        (Fraction(1), Fraction(0)),
        (Fraction(0), Fraction(1)),
        (Fraction(3, 5), Fraction(4, 5)),
        (Fraction(-5, 13), Fraction(12, 13)),
    ]
    rows: list[dict[str, Any]] = []
    for c_value, s_value in probes:
        frame = fraction_frame(c_value, s_value)
        p, q, r = (vector(frame[label]) for label in ("P", "Q", "R"))
        checks = {
            "p_norm_one": dot(p, p) == 1,
            "q_norm_one": dot(q, q) == 1,
            "r_norm_one": dot(r, r) == 1,
            "p_dot_q_zero": dot(p, q) == 0,
            "q_dot_r_zero": dot(q, r) == 0,
            "r_dot_p_zero": dot(r, p) == 0,
            "q_cross_r_equals_p": cross(q, r) == p,
            "r_cross_p_equals_q": cross(r, p) == q,
            "p_cross_q_equals_r": cross(p, q) == r,
        }
        rows.append(
            {
                "c": fraction_text(c_value),
                "s": fraction_text(s_value),
                "checks": checks,
                "checked": all(checks.values()),
            }
        )
    return {
        "rows": rows,
        "checked_row_count": sum(row["checked"] for row in rows),
        "row_count": len(rows),
        "checked": all(row["checked"] for row in rows),
    }


@cache
def rational_frame_pool(
    n: int,
    c_value: Fraction,
    s_value: Fraction,
) -> tuple[tuple[str, Operator], ...]:
    frame = fraction_frame(c_value, s_value)
    gamma_labels = [
        (site, endpoint)
        for site in range(n)
        for endpoint in ("Q", "R")
    ]
    entries: list[tuple[str, Operator]] = []
    for site, endpoint in gamma_labels:
        entries.append(
            (
                f"gamma:{site}:{endpoint}",
                base.gamma_fraction(n, frame, site, endpoint),
            )
        )
    for left_index, (left_site, left_endpoint) in enumerate(gamma_labels):
        for right_site, right_endpoint in gamma_labels[left_index + 1 :]:
            entries.append(
                (
                    f"bilinear:{left_site}:{left_endpoint}:{right_site}:{right_endpoint}",
                    base.bilinear_fraction(
                        n,
                        frame,
                        left_site,
                        left_endpoint,
                        right_site,
                        right_endpoint,
                    ),
                )
            )
    entries.append(
        (
            "parity",
            base.expand_fraction_axes(
                n, {site: frame["P"] for site in range(n)}
            ),
        )
    )
    return tuple(entries)


def rational_frame_catalog() -> list[dict[str, str]]:
    points: set[tuple[Fraction, Fraction]] = set()
    for u_value in range(-GRID_BOUND, GRID_BOUND + 1):
        for v_value in range(-GRID_BOUND, GRID_BOUND + 1):
            if u_value == 0 and v_value == 0:
                continue
            if math.gcd(abs(u_value), abs(v_value)) != 1:
                continue
            denominator = u_value * u_value + v_value * v_value
            points.add(
                (
                    Fraction(u_value * u_value - v_value * v_value, denominator),
                    Fraction(2 * u_value * v_value, denominator),
                )
            )
    return [
        {
            "frame_id": f"pay_{index:03d}",
            "c": fraction_text(c_value),
            "s": fraction_text(s_value),
        }
        for index, (c_value, s_value) in enumerate(sorted(points))
    ]


def projective_frame_count(catalog: list[dict[str, str]]) -> int:
    representatives: set[tuple[Fraction, Fraction]] = set()
    for entry in catalog:
        point = (Fraction(entry["c"]), Fraction(entry["s"]))
        opposite = (-point[0], -point[1])
        representatives.add(min(point, opposite))
    return len(representatives)


def candidate_subspace_sentinels(n: int = 4) -> dict[str, Any]:
    frames = {
        "t0": (Fraction(1), Fraction(0)),
        "infinity": (Fraction(-1), Fraction(0)),
        "t1": (Fraction(0), Fraction(1)),
        "t_minus_1": (Fraction(0), Fraction(-1)),
    }
    operators = {
        label: [operator for _, operator in rational_frame_pool(n, *point)]
        for label, point in frames.items()
    }
    rows = []
    for left, right, expected_axis in (
        ("t0", "infinity", "tilted_A"),
        ("t1", "t_minus_1", "pauli_Y"),
    ):
        left_rank = base.operator_column_rank(operators[left], BASIS_SELECTION_PRIME)
        right_rank = base.operator_column_rank(operators[right], BASIS_SELECTION_PRIME)
        union_rank = base.operator_column_rank(
            operators[left] + operators[right], BASIS_SELECTION_PRIME
        )
        column_count = len(operators[left])
        rows.append(
            {
                "left": left,
                "right": right,
                "expected_axis": expected_axis,
                "column_count": column_count,
                "left_rank": left_rank,
                "right_rank": right_rank,
                "union_rank": union_rank,
                "checked": (
                    left_rank == column_count
                    and right_rank == column_count
                    and union_rank == column_count
                ),
            }
        )
    return {
        "n": n,
        "rows": rows,
        "checked_row_count": sum(row["checked"] for row in rows),
        "row_count": len(rows),
        "checked": all(row["checked"] for row in rows),
    }


def rational_frame_row(
    n: int,
    coupling: Fraction,
    frame_entry: dict[str, str],
    primes: tuple[int, ...] = MODULAR_PRIMES,
) -> dict[str, Any]:
    c_value = Fraction(frame_entry["c"])
    s_value = Fraction(frame_entry["s"])
    entries = list(rational_frame_pool(n, c_value, s_value))
    labels = [label for label, _ in entries]
    operators = [operator for _, operator in entries]
    hamiltonian = base.hamiltonian_operator(n, coupling)
    raw_columns = [base.commutator_integer(hamiltonian, operator) for operator in operators]
    output_words = sorted({word for column in raw_columns for word in column})
    output_index = {word: index for index, word in enumerate(output_words)}
    columns = [
        {output_index[word]: coefficient for word, coefficient in column.items()}
        for column in raw_columns
    ]
    operator_ranks = {
        str(prime): base.operator_column_rank(operators, prime) for prime in primes
    }
    ranks = {
        str(prime): base.modular_sparse_rank(columns, prime) for prime in primes
    }
    matrix_payload = {
        "labels": labels,
        "output_basis": output_words,
        "triples": [
            (output_words[row], column_index, coefficient)
            for column_index, column in enumerate(columns)
            for row, coefficient in sorted(column.items())
        ],
    }
    operator_payload = {
        "labels": labels,
        "operators": [sorted(operator.items()) for operator in operators],
    }
    column_count = len(columns)
    row: dict[str, Any] = {
        "frame_id": frame_entry["frame_id"],
        "c": frame_entry["c"],
        "s": frame_entry["s"],
        "coupling": fraction_text(coupling),
        "n": n,
        "candidate_column_count": column_count,
        "operator_basis_pauli_nonzero_count": sum(len(operator) for operator in operators),
        "operator_basis_sha256": canonical_hash(operator_payload),
        "operator_basis_modular_ranks": operator_ranks,
        "output_basis_size": len(output_words),
        "commutator_nonzero_count": sum(len(column) for column in columns),
        "commutator_matrix_sha256": canonical_hash(matrix_payload),
        "modular_primes": list(primes),
        "modular_ranks": ranks,
        "modular_nullities": {
            str(prime): column_count - ranks[str(prime)] for prime in primes
        },
        "operator_basis_independent": all(
            rank == column_count for rank in operator_ranks.values()
        ),
        "commutator_full_column_rank": all(
            rank == column_count for rank in ranks.values()
        ),
    }
    row["checked"] = bool(
        row["operator_basis_independent"]
        and (
            row["commutator_full_column_rank"]
            if coupling != 0
            else all(rank < column_count for rank in ranks.values())
        )
    )
    if coupling == 0 and c_value == 1 and s_value == 0:
        witnesses = [
            base.expand_fraction_axes(n, {site: AXIS_A}) for site in range(n)
        ]
        commutators = [
            base.commutator_integer(hamiltonian, witness) for witness in witnesses
        ]
        in_span = [base.operator_in_span(witness, operators) for witness in witnesses]
        row["onsite_axis_a_witness_count"] = len(witnesses)
        row["onsite_axis_a_commutes_count"] = sum(not item for item in commutators)
        row["onsite_axis_a_in_span_count"] = sum(in_span)
        row["onsite_axis_a_witnesses_checked"] = bool(
            all(not item for item in commutators) and all(in_span)
        )
    return row


def polynomial_axes() -> dict[str, dict[str, sp.Expr]]:
    c_numerator = 1 - T * T
    s_numerator = 2 * T
    return {
        "P": {
            "X": -4 * c_numerator,
            "Y": 5 * s_numerator,
            "Z": 3 * c_numerator,
        },
        "Q": {
            "X": 4 * s_numerator,
            "Y": 5 * c_numerator,
            "Z": -3 * s_numerator,
        },
        "R": {"X": -3 * D, "Z": -4 * D},
    }


def symbolic_frame_identity_checks() -> dict[str, Any]:
    axes = polynomial_axes()
    vectors = {
        label: sp.Matrix([axis.get(pauli, 0) for pauli in "XYZ"])
        for label, axis in axes.items()
    }
    p, q, r = (vectors[label] for label in ("P", "Q", "R"))
    target_norm = 25 * D**2
    identities = {
        "p_norm": sp.expand(p.dot(p) - target_norm),
        "q_norm": sp.expand(q.dot(q) - target_norm),
        "r_norm": sp.expand(r.dot(r) - target_norm),
        "p_dot_q": sp.expand(p.dot(q)),
        "q_dot_r": sp.expand(q.dot(r)),
        "r_dot_p": sp.expand(r.dot(p)),
        "p_cross_q": [sp.expand(value) for value in p.cross(q) - 5 * D * r],
        "q_cross_r": [sp.expand(value) for value in q.cross(r) - 5 * D * p],
        "r_cross_p": [sp.expand(value) for value in r.cross(p) - 5 * D * q],
        "orientation_determinant": sp.expand(sp.det(sp.Matrix.hstack(p, q, r)) - 125 * D**3),
    }
    checks = {
        label: (
            all(value == 0 for value in expression)
            if isinstance(expression, list)
            else expression == 0
        )
        for label, expression in identities.items()
    }
    return {
        "identity_count": len(checks),
        "identity_pass_count": sum(checks.values()),
        "checks": checks,
        "orientation_determinant": "125*(1+t^2)^3",
        "checked": all(checks.values()),
    }


@cache
def symbolic_frame_pool(n: int) -> tuple[tuple[str, PolynomialOperator], ...]:
    frame = polynomial_axes()
    gamma_labels = [
        (site, endpoint)
        for site in range(n)
        for endpoint in ("Q", "R")
    ]
    entries: list[tuple[str, PolynomialOperator]] = []
    for site, endpoint in gamma_labels:
        axes = {index: frame["P"] for index in range(site)}
        axes[site] = frame[endpoint]
        entries.append(
            (f"gamma:{site}:{endpoint}", base.expand_polynomial_axes(n, axes))
        )
    for left_index, (left_site, left_endpoint) in enumerate(gamma_labels):
        for right_site, right_endpoint in gamma_labels[left_index + 1 :]:
            if left_site == right_site:
                operator = base.expand_polynomial_axes(
                    n, {left_site: frame["P"]}, scale=-1
                )
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
                operator = base.expand_polynomial_axes(n, axes, scale=sign)
            entries.append(
                (
                    f"bilinear:{left_site}:{left_endpoint}:{right_site}:{right_endpoint}",
                    operator,
                )
            )
    entries.append(
        (
            "parity",
            base.expand_polynomial_axes(
                n, {site: frame["P"] for site in range(n)}
            ),
        )
    )
    return tuple(entries)


def symbolic_matrix(
    n: int, coupling: Fraction
) -> tuple[list[str], list[PolynomialOperator], list[str], str]:
    entries = list(symbolic_frame_pool(n))
    labels = [label for label, _ in entries]
    hamiltonian = base.hamiltonian_operator(n, coupling)
    columns = [
        base.commutator_polynomial(hamiltonian, operator)
        for _, operator in entries
    ]
    output_words = sorted({word for column in columns for word in column})
    triples = [
        (word, column_index, base.polynomial_coefficients(coefficient))
        for column_index, column in enumerate(columns)
        for word, coefficient in sorted(column.items())
    ]
    matrix_sha256 = canonical_hash(
        {"labels": labels, "output_words": output_words, "triples": triples}
    )
    return labels, columns, output_words, matrix_sha256


def continuous_certificate(n: int, coupling: Fraction) -> dict[str, Any]:
    started = time.monotonic()
    labels, columns, output_words, matrix_sha256 = symbolic_matrix(n, coupling)
    determinant_records: list[dict[str, Any]] = []
    determinant_polynomials: list[sp.Poly] = []
    for anchor in INITIAL_MINOR_ANCHORS:
        row_words = base.select_rows_at_anchor(
            columns, output_words, anchor, BASIS_SELECTION_PRIME
        )
        if len(row_words) != len(columns):
            break
        record, determinant = base.determinant_record(
            columns,
            row_words,
            {
                "type": "integer_anchor",
                "anchor": anchor,
                "selection_prime": BASIS_SELECTION_PRIME,
            },
        )
        determinant_records.append(record)
        determinant_polynomials.append(determinant)

    unresolved_factors: list[dict[str, Any]] = []
    adaptive_round = 0
    while determinant_polynomials and adaptive_round < MAX_ADAPTIVE_ROUNDS:
        gcd_poly = determinant_polynomials[0]
        for determinant in determinant_polynomials[1:]:
            gcd_poly = sp.gcd(gcd_poly, determinant)
        _, gcd_poly = base.normalized_primitive_poly(gcd_poly)
        real_factors = [
            factor
            for factor in base.factor_records(gcd_poly)
            if factor["real_root_count"] > 0
        ]
        if not real_factors:
            break
        factor_record = real_factors[0]
        factor = sp.Poly(
            [int(value) for value in factor_record["coefficients"]],
            T,
            domain=sp.QQ,
        )
        row_words = base.select_rows_over_factor(columns, output_words, factor)
        if len(row_words) != len(columns):
            unresolved_factors.append(
                {
                    **factor_record,
                    "quotient_field_rank": len(row_words),
                    "candidate_column_count": len(columns),
                }
            )
            break
        record, determinant = base.determinant_record(
            columns,
            row_words,
            {
                "type": "quotient_field_factor",
                "factor_sha256": factor_record["factor_sha256"],
                "factor_degree": factor_record["degree"],
                "factor_real_root_count": factor_record["real_root_count"],
            },
        )
        determinant_records.append(record)
        determinant_polynomials.append(determinant)
        adaptive_round += 1

    if not determinant_polynomials:
        raise RuntimeError("no full-rank anchor minor was found")
    gcd_poly = determinant_polynomials[0]
    for determinant in determinant_polynomials[1:]:
        gcd_poly = sp.gcd(gcd_poly, determinant)
    _, gcd_poly = base.normalized_primitive_poly(gcd_poly)
    square_free = sp.Poly(sp.sqf_part(gcd_poly), T, domain=sp.QQ)
    finite_real_root_count = int(
        sp.polys.polytools.count_roots(square_free, -sp.oo, sp.oo)
    )
    gcd_coefficients = base.polynomial_coefficients(gcd_poly)
    infinity_row = rational_frame_row(
        n,
        coupling,
        {"frame_id": "projective_infinity", "c": "-1", "s": "0"},
    )
    passed = bool(
        len(determinant_records) >= len(INITIAL_MINOR_ANCHORS)
        and not unresolved_factors
        and finite_real_root_count == 0
        and infinity_row["commutator_full_column_rank"]
        and infinity_row["operator_basis_independent"]
    )
    return {
        "coupling": fraction_text(coupling),
        "n": n,
        "parameterization": {
            "D": "1+t^2",
            "A": "(-4X+3Z)/5",
            "B": "(-3X-4Z)/5",
            "P_numerator": "(1-t^2)(-4X+3Z)+10tY",
            "Q_numerator": "8tX+5(1-t^2)Y-6tZ",
            "R_numerator": "(1+t^2)(-3X-4Z)",
            "common_axis_scale": "5(1+t^2)",
            "real_column_scaling_nonzero": True,
        },
        "candidate_column_count": len(columns),
        "candidate_labels_sha256": canonical_hash(labels),
        "output_basis_size": len(output_words),
        "polynomial_commutator_nonzero_count": sum(len(column) for column in columns),
        "polynomial_commutator_matrix_sha256": matrix_sha256,
        "initial_minor_anchor_count": len(INITIAL_MINOR_ANCHORS),
        "determinant_count": len(determinant_records),
        "determinants": determinant_records,
        "adaptive_round_count": adaptive_round,
        "unresolved_factors": unresolved_factors,
        "final_primitive_gcd_degree": gcd_poly.degree(),
        "final_primitive_gcd_sha256": canonical_hash(gcd_coefficients),
        "final_factorization": base.factor_records(gcd_poly),
        "square_free_gcd_degree": square_free.degree(),
        "finite_real_common_root_count": finite_real_root_count,
        "finite_real_frames_full_column_rank_certified": (
            finite_real_root_count == 0 and not unresolved_factors
        ),
        "projective_infinity": infinity_row,
        "continuous_projective_line_full_column_rank_certified": passed,
        "elapsed_seconds": round(time.monotonic() - started, 6),
        "checked": passed,
    }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def verify_public_freeze(root: Path, preregistration_commit: str) -> dict[str, Any]:
    if not preregistration_commit:
        raise ValueError("--preregistration-commit is required for frozen holdouts")
    commit = subprocess.run(
        ["git", "rev-parse", f"{preregistration_commit}^{{commit}}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    ancestor = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=root,
            check=False,
        ).returncode
        == 0
    )
    frozen_bytes = subprocess.run(
        ["git", "show", f"{commit}:{CONTRACT_PATH}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    frozen_hash = sha256_bytes(frozen_bytes)
    current_hash = sha256_file(root / CONTRACT_PATH)
    contract = json.loads((root / CONTRACT_PATH).read_text())
    code_files: list[dict[str, Any]] = []
    for relative_path in contract["code_freeze"]["paths"]:
        frozen_file = subprocess.run(
            ["git", "show", f"{commit}:{relative_path}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        current_file = (root / relative_path).read_bytes()
        code_files.append(
            {
                "path": relative_path,
                "preregistration_sha256": sha256_bytes(frozen_file),
                "current_sha256": sha256_bytes(current_file),
                "matches": frozen_file == current_file,
            }
        )
    code_freeze_verified = all(item["matches"] for item in code_files)
    return {
        "preregistration_commit": commit,
        "is_ancestor_of_execution_head": ancestor,
        "contract_sha256_at_preregistration_commit": frozen_hash,
        "expected_contract_sha256": EXPECTED_CONTRACT_SHA256,
        "current_contract_sha256": current_hash,
        "code_files": code_files,
        "code_freeze_verified": code_freeze_verified,
        "runtime_versions": {
            "python": sys.version.split()[0],
            "sympy": sp.__version__,
        },
        "verified": bool(
            ancestor
            and frozen_hash == EXPECTED_CONTRACT_SHA256
            and current_hash == EXPECTED_CONTRACT_SHA256
            and code_freeze_verified
        ),
    }


def requirement(
    requirement_id: str,
    label: str,
    passed: bool,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def protocol(contract: dict[str, Any]) -> dict[str, Any]:
    catalog = rational_frame_catalog()
    return {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "contract": {
            "path": str(CONTRACT_PATH),
            "sha256": EXPECTED_CONTRACT_SHA256,
            "version": contract["version"],
            "status": contract["status"],
        },
        "chart": contract["chart"],
        "frame_algebra": frame_algebra_checks(),
        "symbolic_frame_algebra": symbolic_frame_identity_checks(),
        "candidate_subspace_sentinels": candidate_subspace_sentinels(),
        "frozen_holdouts": [fraction_text(value) for value in FROZEN_HOLDOUT_COUPLINGS],
        "continuous_sizes": list(CONTINUOUS_SIZES),
        "grid_sizes": list(GRID_SIZES),
        "grid_catalog": {
            "bound": GRID_BOUND,
            "count": len(catalog),
            "projective_count": projective_frame_count(catalog),
            "sha256": canonical_hash(catalog),
        },
        "grid_row_count": (
            len(FROZEN_HOLDOUT_COUPLINGS) * len(GRID_SIZES) * len(catalog)
        ),
        "modular_primes": list(MODULAR_PRIMES),
        "basis_selection_prime": BASIS_SELECTION_PRIME,
        "independent_audit_prime": AUDIT_PRIME,
        "symbolic_certificate": {
            "initial_minor_anchors": list(INITIAL_MINOR_ANCHORS),
            "maximum_adaptive_rounds": MAX_ADAPTIVE_ROUNDS,
            "accepted_symbolic_row_count": (
                len(FROZEN_HOLDOUT_COUPLINGS) * len(CONTINUOUS_SIZES)
            ),
        },
        "positive_control": contract["positive_control"],
        "claim_boundary": {
            "true_claims": TRUE_CLAIMS,
            "false_claims": FALSE_CLAIMS,
            "scientific_promotion_accepted": False,
            "new_credit_delta": 0,
        },
    }


def strip_runtime_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: strip_runtime_fields(item)
            for key, item in value.items()
            if key != "elapsed_seconds"
        }
    if isinstance(value, list):
        return [strip_runtime_fields(item) for item in value]
    return value


def build_engineering_probe(root: Path) -> dict[str, Any]:
    contract = json.loads((root / CONTRACT_PATH).read_text())
    catalog = rational_frame_catalog()
    return strip_runtime_fields({
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "mode": "engineering_probe_only",
        "engineering_coupling": fraction_text(ENGINEERING_COUPLING),
        "acceptance_count": 0,
        "protocol": protocol(contract),
        "continuous_probe": continuous_certificate(4, ENGINEERING_COUPLING),
        "grid_probe_rows": [
            rational_frame_row(6, ENGINEERING_COUPLING, frame)
            for frame in catalog[:4]
        ],
        "frozen_holdouts_executed": False,
    })


def build_result(root: Path, preregistration_commit: str) -> dict[str, Any]:
    contract = json.loads((root / CONTRACT_PATH).read_text())
    freeze = verify_public_freeze(root, preregistration_commit)
    if not freeze["verified"]:
        raise RuntimeError("public preregistration freeze verification failed")
    protocol_payload = protocol(contract)
    catalog = rational_frame_catalog()
    continuous_rows = [
        continuous_certificate(n, coupling)
        for coupling in FROZEN_HOLDOUT_COUPLINGS
        for n in CONTINUOUS_SIZES
    ]
    grid_rows = [
        rational_frame_row(n, coupling, frame)
        for coupling in FROZEN_HOLDOUT_COUPLINGS
        for n in GRID_SIZES
        for frame in catalog
    ]
    positive_control = rational_frame_row(
        6,
        Fraction(0),
        {"frame_id": "positive_control_t0", "c": "1", "s": "0"},
    )
    continuous_pass_count = sum(row["checked"] for row in continuous_rows)
    grid_pass_count = sum(row["checked"] for row in grid_rows)
    catalog_hash = canonical_hash(catalog)
    frame_checks = protocol_payload["frame_algebra"]
    symbolic_frame_checks = protocol_payload["symbolic_frame_algebra"]
    subspace_sentinels = protocol_payload["candidate_subspace_sentinels"]
    expected_column_counts = {4: 37, 5: 56, 6: 79, 8: 137, 10: 211}
    observed_column_counts: dict[int, set[int]] = {}
    for row in continuous_rows + grid_rows:
        observed_column_counts.setdefault(row["n"], set()).add(
            row["candidate_column_count"]
        )
    candidate_counts_checked = all(
        observed_column_counts.get(n) == {expected}
        for n, expected in expected_column_counts.items()
    )
    requirements = [
        requirement(
            "P1",
            "Public preregistration commit is an ancestor and hash-binds the contract",
            freeze["verified"],
            freeze,
        ),
        requirement(
            "P2",
            "Frozen holdouts are disjoint from every earlier coupling grid",
            set(FROZEN_HOLDOUT_COUPLINGS).isdisjoint(PREVIOUSLY_OBSERVED_COUPLINGS),
            {
                "holdouts": [fraction_text(value) for value in FROZEN_HOLDOUT_COUPLINGS],
                "previous_count": len(PREVIOUSLY_OBSERVED_COUPLINGS),
            },
        ),
        requirement(
            "P3",
            "Engineering probe contributes zero frozen decisions",
            True,
            {"engineering_coupling": fraction_text(ENGINEERING_COUPLING), "acceptance_count": 0},
        ),
        requirement(
            "P4",
            "The A-Y meridian frames satisfy all sampled and symbolic right-handed orthonormal identities",
            bool(
                frame_checks["checked"]
                and symbolic_frame_checks["checked"]
                and symbolic_frame_checks["identity_pass_count"] == 10
            ),
            {
                "sampled": frame_checks,
                "symbolic": symbolic_frame_checks,
            },
        ),
        requirement(
            "P5",
            "The catalog has 72 directed frames, 36 projective subspaces, and the declared digest",
            bool(
                len(catalog) == GRID_EXPECTED_COUNT
                and projective_frame_count(catalog) == 36
                and catalog_hash == GRID_EXPECTED_SHA256
            ),
            {
                "directed_count": len(catalog),
                "projective_count": projective_frame_count(catalog),
                "sha256": catalog_hash,
                "expected_sha256": GRID_EXPECTED_SHA256,
            },
        ),
        requirement(
            "P6",
            "The complete candidate family has the frozen column counts and projective overlap sentinels",
            bool(candidate_counts_checked and subspace_sentinels["checked"]),
            {
                "expected_column_counts": expected_column_counts,
                "observed_column_counts": {
                    str(n): sorted(values)
                    for n, values in observed_column_counts.items()
                },
                "subspace_sentinels": subspace_sentinels,
            },
        ),
        requirement(
            "P7",
            "All four continuous symbolic rows execute",
            len(continuous_rows) == 4,
            {"actual": len(continuous_rows), "expected": 4},
        ),
        requirement(
            "P8",
            "Every continuous row has no finite real common minor root",
            all(
                row["finite_real_common_root_count"] == 0
                and row["finite_real_frames_full_column_rank_certified"]
                for row in continuous_rows
            ),
            {"passed": continuous_pass_count, "total": len(continuous_rows)},
        ),
        requirement(
            "P9",
            "Every projective infinity endpoint has full rank",
            all(
                row["projective_infinity"]["commutator_full_column_rank"]
                for row in continuous_rows
            ),
            {"row_count": len(continuous_rows)},
        ),
        requirement(
            "P10",
            "All 432 frozen rational-frame rows execute",
            len(grid_rows) == 432,
            {"actual": len(grid_rows), "expected": 432},
        ),
        requirement(
            "P11",
            "Every rational-frame operator pool and commutator matrix has full column rank",
            all(row["checked"] for row in grid_rows),
            {"passed": grid_pass_count, "total": len(grid_rows)},
        ),
        requirement(
            "P12",
            "The t=0 A-axis control has the exact frozen ranks and all six onsite charges",
            bool(
                positive_control["checked"]
                and positive_control["candidate_column_count"] == 79
                and all(
                    rank == 79
                    for rank in positive_control["operator_basis_modular_ranks"].values()
                )
                and all(
                    rank == 42
                    for rank in positive_control["modular_ranks"].values()
                )
                and all(
                    nullity == 37
                    for nullity in positive_control["modular_nullities"].values()
                )
                and positive_control.get("onsite_axis_a_witnesses_checked")
                and positive_control.get("onsite_axis_a_commutes_count") == 6
                and positive_control.get("onsite_axis_a_in_span_count") == 6
            ),
            {
                "candidate_column_count": positive_control["candidate_column_count"],
                "operator_ranks": positive_control["operator_basis_modular_ranks"],
                "commutator_ranks": positive_control["modular_ranks"],
                "nullities": positive_control["modular_nullities"],
                "commuting_witnesses": positive_control.get("onsite_axis_a_commutes_count", 0),
                "in_span_witnesses": positive_control.get("onsite_axis_a_in_span_count", 0),
            },
        ),
        requirement(
            "P13",
            "Every forbidden broad claim remains false",
            True,
            {
                "false_claim_count": len(FALSE_CLAIMS),
                "scientific_promotion_accepted": False,
                "new_credit_delta": 0,
            },
        ),
        requirement(
            "P14",
            "All declared R199 acceptance gates pass",
            bool(
                frame_checks["checked"]
                and symbolic_frame_checks["checked"]
                and subspace_sentinels["checked"]
                and candidate_counts_checked
                and continuous_pass_count == 4
                and grid_pass_count == 432
                and positive_control["checked"]
                and all(
                    nullity == 37
                    for nullity in positive_control["modular_nullities"].values()
                )
            ),
            {
                "frame_algebra_passed": frame_checks["checked"],
                "symbolic_frame_algebra_passed": symbolic_frame_checks["checked"],
                "subspace_sentinels_passed": subspace_sentinels["checked"],
                "candidate_counts_checked": candidate_counts_checked,
                "continuous_pass_count": continuous_pass_count,
                "grid_pass_count": grid_pass_count,
                "positive_control_passed": positive_control["checked"],
            },
        ),
    ]
    all_passed = all(item["passed"] for item in requirements)
    result: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "status": STATUS_ACCEPTED if all_passed else STATUS_REJECTED,
        "public_freeze": freeze,
        "protocol": protocol_payload,
        "continuous_rows": continuous_rows,
        "rational_frame_catalog": catalog,
        "rational_grid_rows": grid_rows,
        "positive_control": positive_control,
        "summary": {
            "continuous_row_count": len(continuous_rows),
            "continuous_pass_count": continuous_pass_count,
            "continuous_determinant_count": sum(row["determinant_count"] for row in continuous_rows),
            "continuous_finite_real_common_root_count": sum(
                row["finite_real_common_root_count"] for row in continuous_rows
            ),
            "rational_frame_count": len(catalog),
            "projective_frame_count": projective_frame_count(catalog),
            "rational_grid_row_count": len(grid_rows),
            "rational_grid_pass_count": grid_pass_count,
            "largest_candidate_column_count": max(row["candidate_column_count"] for row in grid_rows),
            "largest_commutator_nonzero_count": max(row["commutator_nonzero_count"] for row in grid_rows),
            "positive_control_nullities": positive_control["modular_nullities"],
            "requirement_pass_count": sum(item["passed"] for item in requirements),
            "requirement_count": len(requirements),
        },
        "requirements": requirements,
        "claims": {
            **{claim: all_passed for claim in TRUE_CLAIMS},
            **{claim: False for claim in FALSE_CLAIMS},
            "scientific_promotion_accepted": False,
            "new_credit_delta": 0,
        },
    }
    result["protocol_hash"] = canonical_hash(protocol_payload)
    result["payload_sha256"] = canonical_hash(result)
    return result


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    lines = [
        "# B9 R199 Continuous A-Y Meridian Stress",
        "",
        f"- Status: `{result['status']}`",
        f"- Protocol hash: `{result['protocol_hash']}`",
        f"- Payload hash: `{result['payload_sha256']}`",
        f"- Public preregistration commit: `{result['public_freeze']['preregistration_commit']}`",
        f"- Continuous symbolic rows: `{summary['continuous_pass_count']}/{summary['continuous_row_count']}`",
        f"- Exact maximal-minor determinants: `{summary['continuous_determinant_count']}`",
        f"- Finite real common roots: `{summary['continuous_finite_real_common_root_count']}`",
        f"- Rational-frame rows: `{summary['rational_grid_pass_count']}/{summary['rational_grid_row_count']}`",
        f"- Requirements: `{summary['requirement_pass_count']}/{summary['requirement_count']}`",
        "- Scientific promotion: `false`",
        "- New credit delta: `0`",
        "",
        "## Research Question",
        "",
        "Can a Jordan-Wigner parity axis that leaves the XZ plane reveal an exact quadratic-Majorana charge missed by R198?",
        "",
        "## Method",
        "",
        "R199 rotates the solvable local-field axis `A=(-4X+3Z)/5` toward `Y` while fixing `B=(-3X-4Z)/5`. Except at isolated endpoints, the parity axis contains a nonzero Y component and therefore lies outside the R198 XZ chart. Exact polynomial maximal minors certify the complete real projective line at `n=4,5`; 72 exact rational frames pressure `n=6,8,10` under two primes.",
        "",
        "## Continuous Rows",
        "",
        "| J | n | columns | determinants | final gcd degree | real roots | infinity full rank |",
        "|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for row in result["continuous_rows"]:
        lines.append(
            f"| {row['coupling']} | {row['n']} | {row['candidate_column_count']} | "
            f"{row['determinant_count']} | {row['final_primitive_gcd_degree']} | "
            f"{row['finite_real_common_root_count']} | "
            f"{str(row['projective_infinity']['commutator_full_column_rank']).lower()} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "R199 closes only one declared out-of-XZ A-Y meridian of quadratic-Majorana-plus-parity charges at `n=4,5` and its frozen 72-frame grid at `n=6,8,10`. It does not cover the full two-dimensional Bloch sphere, nonlinear frame mixtures, higher-order Majorana charges, nonlocal dualities, interacting integrability, larger-size drift, nonintegrability, chaos, hardness, Quantum PCP, NLTS, BQP, hardware, or a solved frontier.",
            "",
            "## Next Gate",
            "",
            "Run the non-importing symplectic-bit and polynomial reconstruction under a third prime. Then attack a second independent meridian, quartic Majorana charges, or an explicit nonlocal duality.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--engineering-probe", action="store_true")
    modes.add_argument("--execute-frozen-holdouts", action="store_true")
    parser.add_argument("--preregistration-commit", default="")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    result = (
        build_engineering_probe(root)
        if args.engineering_probe
        else build_result(root, args.preregistration_commit)
    )
    output_path = args.output if args.output.is_absolute() else root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2 if args.pretty else None, sort_keys=True) + "\n"
    )
    if args.execute_frozen_holdouts:
        report_path = args.report if args.report.is_absolute() else root / args.report
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_report(result))
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if all(item["passed"] for item in result.get("requirements", [])) else 1


if __name__ == "__main__":
    raise SystemExit(main())
