#!/usr/bin/env python3
"""Execute the preregistered B9 R198 continuous-frame stress.

Frozen couplings are inaccessible until a public preregistration commit
hash-binds the contract. Engineering mode uses only the declared probe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import time
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any, Iterable

import sympy as sp


EXPERIMENT_ID = "B9-R198-continuous-xz-fermionization-frame-stress"
METHOD = "b9_r198_continuous_frame_stress_v1"
VERSION = "1.0"
LAST_UPDATED = "2026-07-30"
STATUS_ACCEPTED = "checked_continuous_xz_frame_boundary"
STATUS_REJECTED = "continuous_xz_frame_boundary_rejected"

CONTRACT_PATH = Path("benchmarks/B9_R198_continuous_frame_contract_v0.json")
EXPECTED_CONTRACT_SHA256 = (
    "c1b68368dbf9ad577f84838b5a3dd77387c63b78f9f7a7c7e6fa334803f9d03c"
)
RESULT_PATH = Path("results/B9_R198_continuous_frame_stress_v1.json")
REPORT_PATH = Path("research/B9_R198_continuous_frame_stress.md")

ENGINEERING_COUPLING = Fraction(13, 32)
FROZEN_HOLDOUT_COUPLINGS = (Fraction(89, 128), Fraction(101, 128))
CONTINUOUS_SIZES = (4, 5)
GRID_SIZES = (6, 8, 10)
GRID_BOUND = 7
GRID_EXPECTED_COUNT = 72
GRID_EXPECTED_SHA256 = (
    "be8464505e235cb1f4a1829211d768c56e35cdaffed469316432e8df6a4a83e3"
)
INITIAL_MINOR_ANCHORS = (0, 1, 2, 4)
MAX_ADAPTIVE_ROUNDS = 12
MODULAR_PRIMES = (1_000_003, 1_000_033)
BASIS_SELECTION_PRIME = MODULAR_PRIMES[0]
AUDIT_PRIME = 1_000_037

PREVIOUSLY_OBSERVED_COUPLINGS = {
    Fraction(0),
    Fraction(1, 8),
    Fraction(3, 16),
    Fraction(1, 4),
    Fraction(5, 16),
    Fraction(23, 64),
    Fraction(3, 8),
    Fraction(13, 32),
    Fraction(53, 128),
    Fraction(27, 64),
    Fraction(7, 16),
    Fraction(31, 64),
    Fraction(1, 2),
    Fraction(69, 128),
    Fraction(35, 64),
    Fraction(9, 16),
    Fraction(73, 128),
    Fraction(77, 128),
    Fraction(79, 128),
    Fraction(83, 128),
    Fraction(5, 8),
    Fraction(11, 16),
    Fraction(3, 4),
    Fraction(7, 8),
    Fraction(1),
}

TRUE_CLAIMS = [
    "r198_contract_publicly_frozen_before_acceptance_execution",
    "r198_holdout_couplings_unseen_before_protocol_freeze",
    "continuous_xz_plane_quadratic_majorana_pool_has_no_extra_charge_at_n4_n5",
    "declared_72_frame_grid_has_no_extra_quadratic_majorana_charge_at_n6_n8_n10",
    "zero_coupling_tilted_frame_control_recovers_extra_exact_charges",
    "r197_candidate_survives_declared_r198_continuous_family_adversary",
]
FALSE_CLAIMS = [
    "all_bloch_sphere_fermionization_exclusion",
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

PAULI_PRODUCT: dict[tuple[str, str], tuple[complex, str]] = {
    ("I", "I"): (1, "I"),
    ("I", "X"): (1, "X"),
    ("I", "Y"): (1, "Y"),
    ("I", "Z"): (1, "Z"),
    ("X", "I"): (1, "X"),
    ("Y", "I"): (1, "Y"),
    ("Z", "I"): (1, "Z"),
    ("X", "X"): (1, "I"),
    ("Y", "Y"): (1, "I"),
    ("Z", "Z"): (1, "I"),
    ("X", "Y"): (1j, "Z"),
    ("Y", "X"): (-1j, "Z"),
    ("Y", "Z"): (1j, "X"),
    ("Z", "Y"): (-1j, "X"),
    ("Z", "X"): (1j, "Y"),
    ("X", "Z"): (-1j, "Y"),
}

Axis = dict[str, Fraction]
Operator = dict[str, int]
PolynomialOperator = dict[str, sp.Poly]

T = sp.symbols("t")
D = 1 + T * T
POLY_ZERO_QQ = sp.Poly(0, T, domain=sp.QQ)
POLY_ONE_QQ = sp.Poly(1, T, domain=sp.QQ)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256_bytes(payload)


def fraction_text(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def lcm(values: Iterable[int]) -> int:
    result = 1
    for value in values:
        result = math.lcm(result, value)
    return result


def primitive_integer_operator(
    value: dict[str, Fraction] | dict[str, int],
) -> Operator:
    fractions = {
        word: Fraction(coefficient)
        for word, coefficient in value.items()
        if coefficient
    }
    if not fractions:
        return {}
    denominator = lcm(
        coefficient.denominator for coefficient in fractions.values()
    )
    integers = {
        word: int(coefficient * denominator)
        for word, coefficient in fractions.items()
    }
    divisor = 0
    for coefficient in integers.values():
        divisor = math.gcd(divisor, abs(coefficient))
    integers = {
        word: coefficient // divisor
        for word, coefficient in integers.items()
        if coefficient
    }
    first_word = min(integers)
    if integers[first_word] < 0:
        integers = {
            word: -coefficient for word, coefficient in integers.items()
        }
    return dict(sorted(integers.items()))


def pauli_word(n: int, operations: dict[int, str]) -> str:
    chars = ["I"] * n
    for site, pauli in operations.items():
        chars[site] = pauli
    return "".join(chars)


def hamiltonian_operator(n: int, coupling: Fraction) -> Operator:
    terms: dict[str, Fraction] = {}
    for site in range(n):
        x_word = pauli_word(n, {site: "X"})
        z_word = pauli_word(n, {site: "Z"})
        terms[x_word] = terms.get(x_word, Fraction(0)) - 1
        terms[z_word] = terms.get(z_word, Fraction(0)) + Fraction(3, 4)
    for site in range(n - 1):
        zz_word = pauli_word(n, {site: "Z", site + 1: "Z"})
        terms[zz_word] = terms.get(zz_word, Fraction(0)) + coupling
    return primitive_integer_operator(terms)


def pauli_anticommutes(left: str, right: str) -> bool:
    return (
        sum(
            a != "I" and b != "I" and a != b
            for a, b in zip(left, right)
        )
        % 2
        == 1
    )


def pauli_multiply(left: str, right: str) -> tuple[complex, str]:
    phase: complex = 1
    output: list[str] = []
    for a, b in zip(left, right):
        local_phase, local_output = PAULI_PRODUCT[(a, b)]
        phase *= local_phase
        output.append(local_output)
    return phase, "".join(output)


def commutator_integer(
    hamiltonian: Operator,
    candidate: Operator,
) -> Operator:
    output: dict[str, Fraction] = {}
    for h_word, h_coefficient in hamiltonian.items():
        for candidate_word, candidate_coefficient in candidate.items():
            if not pauli_anticommutes(h_word, candidate_word):
                continue
            phase, output_word = pauli_multiply(h_word, candidate_word)
            sign = int(round((phase / 1j).real))
            output[output_word] = (
                output.get(output_word, Fraction(0))
                + h_coefficient * candidate_coefficient * sign
            )
    return primitive_integer_operator(output)


def expand_fraction_axes(
    n: int,
    site_axes: dict[int, Axis],
    scale: int = 1,
) -> Operator:
    partial: dict[str, Fraction] = {"I" * n: Fraction(scale)}
    for site in sorted(site_axes):
        updated: dict[str, Fraction] = {}
        for word, coefficient in partial.items():
            for pauli, local_coefficient in site_axes[site].items():
                chars = list(word)
                chars[site] = pauli
                output = "".join(chars)
                updated[output] = (
                    updated.get(output, Fraction(0))
                    + coefficient * local_coefficient
                )
        partial = updated
    return primitive_integer_operator(partial)


def fraction_frame(c_value: Fraction, s_value: Fraction) -> dict[str, Axis]:
    return {
        "P": {"X": c_value, "Z": s_value},
        "Q": {"X": s_value, "Z": -c_value},
        "R": {"Y": Fraction(1)},
    }


def gamma_fraction(
    n: int,
    frame: dict[str, Axis],
    site: int,
    endpoint: str,
) -> Operator:
    axes = {index: frame["P"] for index in range(site)}
    axes[site] = frame[endpoint]
    return expand_fraction_axes(n, axes)


def bilinear_fraction(
    n: int,
    frame: dict[str, Axis],
    left_site: int,
    left_endpoint: str,
    right_site: int,
    right_endpoint: str,
) -> Operator:
    if left_site == right_site:
        return expand_fraction_axes(n, {left_site: frame["P"]}, scale=-1)
    axes: dict[int, Axis] = {}
    sign = 1
    if left_endpoint == "Q":
        axes[left_site] = frame["R"]
    else:
        axes[left_site] = frame["Q"]
        sign = -1
    for site in range(left_site + 1, right_site):
        axes[site] = frame["P"]
    axes[right_site] = frame[right_endpoint]
    return expand_fraction_axes(n, axes, scale=sign)


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
                gamma_fraction(n, frame, site, endpoint),
            )
        )
    for left_index, (left_site, left_endpoint) in enumerate(gamma_labels):
        for right_site, right_endpoint in gamma_labels[left_index + 1 :]:
            entries.append(
                (
                    (
                        f"bilinear:{left_site}:{left_endpoint}:"
                        f"{right_site}:{right_endpoint}"
                    ),
                    bilinear_fraction(
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
            expand_fraction_axes(
                n, {site: frame["P"] for site in range(n)}
            ),
        )
    )
    return tuple(entries)


def modular_sparse_rank(
    columns: list[dict[int, int]],
    prime: int,
) -> int:
    pivots: dict[int, dict[int, int]] = {}
    for column in columns:
        vector = {
            row: coefficient % prime
            for row, coefficient in column.items()
            if coefficient % prime
        }
        while vector:
            pivot = min(vector)
            if pivot not in pivots:
                inverse = pow(vector[pivot], prime - 2, prime)
                pivots[pivot] = {
                    row: (coefficient * inverse) % prime
                    for row, coefficient in vector.items()
                    if (coefficient * inverse) % prime
                }
                break
            factor = vector[pivot]
            for row, coefficient in pivots[pivot].items():
                updated = (
                    vector.get(row, 0) - factor * coefficient
                ) % prime
                if updated:
                    vector[row] = updated
                else:
                    vector.pop(row, None)
    return len(pivots)


def operator_column_rank(operators: list[Operator], prime: int) -> int:
    words = sorted({word for operator in operators for word in operator})
    index = {word: row for row, word in enumerate(words)}
    columns = [
        {index[word]: coefficient for word, coefficient in operator.items()}
        for operator in operators
    ]
    return modular_sparse_rank(columns, prime)


def operator_in_span(
    operator: Operator,
    basis: list[Operator],
    prime: int = BASIS_SELECTION_PRIME,
) -> bool:
    return operator_column_rank(basis + [operator], prime) == len(basis)


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
                    Fraction(
                        u_value * u_value - v_value * v_value,
                        denominator,
                    ),
                    Fraction(2 * u_value * v_value, denominator),
                )
            )
    return [
        {
            "frame_id": f"pxz_{index:03d}",
            "c": fraction_text(c_value),
            "s": fraction_text(s_value),
        }
        for index, (c_value, s_value) in enumerate(sorted(points))
    ]


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
    hamiltonian = hamiltonian_operator(n, coupling)
    raw_columns = [
        commutator_integer(hamiltonian, operator)
        for operator in operators
    ]
    output_words = sorted(
        {word for column in raw_columns for word in column}
    )
    output_index = {
        word: index for index, word in enumerate(output_words)
    }
    columns = [
        {
            output_index[word]: coefficient
            for word, coefficient in column.items()
        }
        for column in raw_columns
    ]
    operator_ranks = {
        str(prime): operator_column_rank(operators, prime)
        for prime in primes
    }
    ranks = {
        str(prime): modular_sparse_rank(columns, prime)
        for prime in primes
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
        "operators": [
            sorted(operator.items()) for operator in operators
        ],
    }
    column_count = len(columns)
    row = {
        "frame_id": frame_entry["frame_id"],
        "c": frame_entry["c"],
        "s": frame_entry["s"],
        "coupling": fraction_text(coupling),
        "n": n,
        "candidate_column_count": column_count,
        "operator_basis_pauli_nonzero_count": sum(
            len(operator) for operator in operators
        ),
        "operator_basis_sha256": canonical_hash(operator_payload),
        "operator_basis_modular_ranks": operator_ranks,
        "output_basis_size": len(output_words),
        "commutator_nonzero_count": sum(
            len(column) for column in columns
        ),
        "commutator_matrix_sha256": canonical_hash(matrix_payload),
        "modular_primes": list(primes),
        "modular_ranks": ranks,
        "modular_nullities": {
            str(prime): column_count - ranks[str(prime)]
            for prime in primes
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
    if coupling == 0 and c_value == Fraction(-4, 5) and s_value == Fraction(3, 5):
        axis_a: Axis = {"X": Fraction(-4, 5), "Z": Fraction(3, 5)}
        witnesses = [
            expand_fraction_axes(n, {site: axis_a})
            for site in range(n)
        ]
        commutators = [
            commutator_integer(hamiltonian, witness)
            for witness in witnesses
        ]
        in_span = [
            operator_in_span(witness, operators) for witness in witnesses
        ]
        row["onsite_tilted_charge_witness_count"] = len(witnesses)
        row["onsite_tilted_charge_commutes_count"] = sum(
            not column for column in commutators
        )
        row["onsite_tilted_charge_in_span_count"] = sum(in_span)
        row["onsite_tilted_charge_witnesses_checked"] = bool(
            all(not column for column in commutators) and all(in_span)
        )
    return row


def polynomial_axes() -> dict[str, dict[str, sp.Expr]]:
    return {
        "P": {"X": 1 - T * T, "Z": 2 * T},
        "Q": {"X": 2 * T, "Z": T * T - 1},
        "R": {"Y": D},
    }


def expand_polynomial_axes(
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
                    updated.get(output, 0)
                    + coefficient * local_coefficient
                )
        partial = updated
    return {
        word: sp.Poly(coefficient, T, domain=sp.ZZ)
        for word, coefficient in partial.items()
        if coefficient != 0
    }


@cache
def symbolic_frame_pool(
    n: int,
) -> tuple[tuple[str, PolynomialOperator], ...]:
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
            (
                f"gamma:{site}:{endpoint}",
                expand_polynomial_axes(n, axes),
            )
        )
    for left_index, (left_site, left_endpoint) in enumerate(gamma_labels):
        for right_site, right_endpoint in gamma_labels[left_index + 1 :]:
            if left_site == right_site:
                operator = expand_polynomial_axes(
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
                operator = expand_polynomial_axes(n, axes, scale=sign)
            entries.append(
                (
                    (
                        f"bilinear:{left_site}:{left_endpoint}:"
                        f"{right_site}:{right_endpoint}"
                    ),
                    operator,
                )
            )
    entries.append(
        (
            "parity",
            expand_polynomial_axes(
                n, {site: frame["P"] for site in range(n)}
            ),
        )
    )
    return tuple(entries)


def commutator_polynomial(
    hamiltonian: Operator,
    candidate: PolynomialOperator,
) -> PolynomialOperator:
    output: dict[str, sp.Poly] = {}
    zero = sp.Poly(0, T, domain=sp.ZZ)
    for h_word, h_coefficient in hamiltonian.items():
        for candidate_word, candidate_coefficient in candidate.items():
            if not pauli_anticommutes(h_word, candidate_word):
                continue
            phase, output_word = pauli_multiply(
                h_word, candidate_word
            )
            sign = int(round((phase / 1j).real))
            output[output_word] = (
                output.get(output_word, zero)
                + candidate_coefficient * (h_coefficient * sign)
            )
    return {
        word: sp.Poly(coefficient, T, domain=sp.ZZ)
        for word, coefficient in output.items()
        if not coefficient.is_zero
    }


def normalized_primitive_poly(poly: sp.Poly) -> tuple[int, sp.Poly]:
    poly = sp.Poly(poly, T, domain=sp.ZZ)
    content, primitive = sp.polys.polytools.primitive(poly)
    primitive = sp.Poly(primitive, T, domain=sp.ZZ)
    if primitive.LC() < 0:
        primitive = -primitive
        content = -content
    return int(content), primitive


def polynomial_coefficients(poly: sp.Poly) -> list[str]:
    return [str(int(coefficient)) for coefficient in poly.all_coeffs()]


def select_rows_at_anchor(
    columns: list[PolynomialOperator],
    output_words: list[str],
    anchor: int,
    prime: int,
) -> list[str]:
    pivots: dict[int, dict[int, int]] = {}
    selected: list[str] = []
    for word in output_words:
        vector = {
            column_index: int(
                columns[column_index]
                .get(word, sp.Poly(0, T, domain=sp.ZZ))
                .eval(anchor)
            )
            % prime
            for column_index in range(len(columns))
        }
        vector = {
            column_index: coefficient
            for column_index, coefficient in vector.items()
            if coefficient
        }
        while vector:
            pivot = min(vector)
            if pivot not in pivots:
                inverse = pow(vector[pivot], prime - 2, prime)
                pivots[pivot] = {
                    index: (coefficient * inverse) % prime
                    for index, coefficient in vector.items()
                }
                selected.append(word)
                break
            factor = vector[pivot]
            for index, coefficient in pivots[pivot].items():
                updated = (
                    vector.get(index, 0) - factor * coefficient
                ) % prime
                if updated:
                    vector[index] = updated
                else:
                    vector.pop(index, None)
        if len(selected) == len(columns):
            break
    return selected


def field_reduce(value: sp.Poly | sp.Expr, factor: sp.Poly) -> sp.Poly:
    return sp.rem(sp.Poly(value, T, domain=sp.QQ), factor)


def field_multiply(
    left: sp.Poly,
    right: sp.Poly,
    factor: sp.Poly,
) -> sp.Poly:
    return field_reduce(left * right, factor)


def select_rows_over_factor(
    columns: list[PolynomialOperator],
    output_words: list[str],
    factor: sp.Poly,
) -> list[str]:
    factor = sp.Poly(factor, T, domain=sp.QQ)
    pivots: dict[int, dict[int, sp.Poly]] = {}
    selected: list[str] = []
    for word in output_words:
        vector = {
            column_index: field_reduce(
                columns[column_index].get(
                    word, sp.Poly(0, T, domain=sp.ZZ)
                ),
                factor,
            )
            for column_index in range(len(columns))
        }
        vector = {
            column_index: coefficient
            for column_index, coefficient in vector.items()
            if not coefficient.is_zero
        }
        while vector:
            pivot = min(vector)
            if pivot not in pivots:
                inverse = sp.Poly(
                    sp.invert(vector[pivot], factor),
                    T,
                    domain=sp.QQ,
                )
                pivots[pivot] = {
                    index: field_multiply(
                        coefficient, inverse, factor
                    )
                    for index, coefficient in vector.items()
                }
                selected.append(word)
                break
            pivot_row = pivots[pivot]
            multiplier = vector[pivot]
            for index, coefficient in pivot_row.items():
                updated = field_reduce(
                    vector.get(index, POLY_ZERO_QQ)
                    - field_multiply(multiplier, coefficient, factor),
                    factor,
                )
                if updated.is_zero:
                    vector.pop(index, None)
                else:
                    vector[index] = updated
        if len(selected) == len(columns):
            break
    return selected


def determinant_record(
    columns: list[PolynomialOperator],
    row_words: list[str],
    source: dict[str, Any],
) -> tuple[dict[str, Any], sp.Poly]:
    started = time.monotonic()
    matrix = sp.Matrix(
        [
            [
                columns[column_index]
                .get(word, sp.Poly(0, T, domain=sp.ZZ))
                .as_expr()
                for column_index in range(len(columns))
            ]
            for word in row_words
        ]
    )
    determinant = sp.Poly(
        matrix.det(method="domain-ge"), T, domain=sp.ZZ
    )
    content, primitive = normalized_primitive_poly(determinant)
    coefficients = polynomial_coefficients(primitive)
    payload = {
        "row_words": row_words,
        "primitive_coefficients": coefficients,
    }
    return (
        {
            "source": source,
            "row_count": len(row_words),
            "row_words_sha256": canonical_hash(row_words),
            "degree": primitive.degree(),
            "term_count": len(primitive.terms()),
            "content_abs_bit_length": abs(content).bit_length(),
            "primitive_max_coefficient_bit_length": max(
                abs(int(coefficient)).bit_length()
                for coefficient in primitive.all_coeffs()
            ),
            "primitive_determinant_sha256": canonical_hash(payload),
            "elapsed_seconds": round(time.monotonic() - started, 6),
        },
        primitive,
    )


def factor_records(poly: sp.Poly) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for factor, exponent in sp.factor_list(poly)[1]:
        _, primitive = normalized_primitive_poly(
            sp.Poly(factor, T, domain=sp.ZZ)
        )
        real_root_count = int(
            sp.polys.polytools.count_roots(
                sp.Poly(primitive, T, domain=sp.QQ),
                -sp.oo,
                sp.oo,
            )
        )
        coefficients = polynomial_coefficients(primitive)
        records.append(
            {
                "degree": primitive.degree(),
                "exponent": int(exponent),
                "coefficients": coefficients,
                "factor_sha256": canonical_hash(coefficients),
                "real_root_count": real_root_count,
            }
        )
    return records


def symbolic_matrix(
    n: int,
    coupling: Fraction,
) -> tuple[list[str], list[PolynomialOperator], list[str], str]:
    entries = list(symbolic_frame_pool(n))
    labels = [label for label, _ in entries]
    hamiltonian = hamiltonian_operator(n, coupling)
    columns = [
        commutator_polynomial(hamiltonian, operator)
        for _, operator in entries
    ]
    output_words = sorted(
        {word for column in columns for word in column}
    )
    triples = [
        (
            word,
            column_index,
            polynomial_coefficients(coefficient),
        )
        for column_index, column in enumerate(columns)
        for word, coefficient in sorted(column.items())
    ]
    matrix_sha256 = canonical_hash(
        {
            "labels": labels,
            "output_words": output_words,
            "triples": triples,
        }
    )
    return labels, columns, output_words, matrix_sha256


def continuous_certificate(
    n: int,
    coupling: Fraction,
) -> dict[str, Any]:
    started = time.monotonic()
    labels, columns, output_words, matrix_sha256 = symbolic_matrix(
        n, coupling
    )
    determinant_records: list[dict[str, Any]] = []
    determinant_polynomials: list[sp.Poly] = []
    for anchor in INITIAL_MINOR_ANCHORS:
        row_words = select_rows_at_anchor(
            columns,
            output_words,
            anchor,
            BASIS_SELECTION_PRIME,
        )
        if len(row_words) != len(columns):
            break
        record, determinant = determinant_record(
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
        _, gcd_poly = normalized_primitive_poly(gcd_poly)
        factors = factor_records(gcd_poly)
        real_factors = [
            factor
            for factor in factors
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
        row_words = select_rows_over_factor(
            columns, output_words, factor
        )
        if len(row_words) != len(columns):
            unresolved_factors.append(
                {
                    **factor_record,
                    "quotient_field_rank": len(row_words),
                    "candidate_column_count": len(columns),
                }
            )
            break
        record, determinant = determinant_record(
            columns,
            row_words,
            {
                "type": "quotient_field_factor",
                "factor_sha256": factor_record["factor_sha256"],
                "factor_degree": factor_record["degree"],
                "factor_real_root_count": factor_record[
                    "real_root_count"
                ],
            },
        )
        determinant_records.append(record)
        determinant_polynomials.append(determinant)
        adaptive_round += 1

    gcd_poly = determinant_polynomials[0]
    for determinant in determinant_polynomials[1:]:
        gcd_poly = sp.gcd(gcd_poly, determinant)
    _, gcd_poly = normalized_primitive_poly(gcd_poly)
    square_free = sp.Poly(
        sp.sqf_part(gcd_poly), T, domain=sp.QQ
    )
    finite_real_root_count = int(
        sp.polys.polytools.count_roots(
            square_free, -sp.oo, sp.oo
        )
    )
    gcd_coefficients = polynomial_coefficients(gcd_poly)
    infinity_frame = {
        "frame_id": "projective_infinity",
        "c": "-1",
        "s": "0",
    }
    infinity_row = rational_frame_row(
        n, coupling, infinity_frame
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
            "P_numerator": "(1-t^2)X+2tZ",
            "Q_numerator": "2tX+(t^2-1)Z",
            "R_numerator": "(1+t^2)Y",
            "real_column_scaling_nonzero": True,
        },
        "candidate_column_count": len(columns),
        "candidate_labels_sha256": canonical_hash(labels),
        "output_basis_size": len(output_words),
        "polynomial_commutator_nonzero_count": sum(
            len(column) for column in columns
        ),
        "polynomial_commutator_matrix_sha256": matrix_sha256,
        "initial_minor_anchor_count": len(INITIAL_MINOR_ANCHORS),
        "determinant_count": len(determinant_records),
        "determinants": determinant_records,
        "adaptive_round_count": adaptive_round,
        "unresolved_factors": unresolved_factors,
        "final_primitive_gcd_degree": gcd_poly.degree(),
        "final_primitive_gcd_sha256": canonical_hash(gcd_coefficients),
        "final_factorization": factor_records(gcd_poly),
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


def verify_public_freeze(
    root: Path,
    preregistration_commit: str,
) -> dict[str, Any]:
    if not preregistration_commit:
        raise ValueError(
            "--preregistration-commit is required for frozen holdouts"
        )
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
    return {
        "preregistration_commit": commit,
        "is_ancestor_of_execution_head": ancestor,
        "contract_sha256_at_preregistration_commit": frozen_hash,
        "expected_contract_sha256": EXPECTED_CONTRACT_SHA256,
        "current_contract_sha256": sha256_file(root / CONTRACT_PATH),
        "verified": bool(
            ancestor
            and frozen_hash == EXPECTED_CONTRACT_SHA256
            and sha256_file(root / CONTRACT_PATH)
            == EXPECTED_CONTRACT_SHA256
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
        "frozen_holdouts": [
            fraction_text(value)
            for value in FROZEN_HOLDOUT_COUPLINGS
        ],
        "continuous_sizes": list(CONTINUOUS_SIZES),
        "grid_sizes": list(GRID_SIZES),
        "grid_catalog": {
            "bound": GRID_BOUND,
            "count": len(catalog),
            "sha256": canonical_hash(catalog),
        },
        "grid_row_count": (
            len(FROZEN_HOLDOUT_COUPLINGS)
            * len(GRID_SIZES)
            * len(catalog)
        ),
        "modular_primes": list(MODULAR_PRIMES),
        "basis_selection_prime": BASIS_SELECTION_PRIME,
        "independent_audit_prime": AUDIT_PRIME,
        "symbolic_certificate": {
            "initial_minor_anchors": list(INITIAL_MINOR_ANCHORS),
            "maximum_adaptive_rounds": MAX_ADAPTIVE_ROUNDS,
            "accepted_symbolic_row_count": (
                len(FROZEN_HOLDOUT_COUPLINGS)
                * len(CONTINUOUS_SIZES)
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


def build_engineering_probe(root: Path) -> dict[str, Any]:
    contract = json.loads((root / CONTRACT_PATH).read_text())
    protocol_payload = protocol(contract)
    certificate = continuous_certificate(4, ENGINEERING_COUPLING)
    sample_catalog = rational_frame_catalog()[:4]
    rows = [
        rational_frame_row(6, ENGINEERING_COUPLING, frame)
        for frame in sample_catalog
    ]
    return {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "mode": "engineering_probe_only",
        "engineering_coupling": fraction_text(ENGINEERING_COUPLING),
        "acceptance_count": 0,
        "protocol": protocol_payload,
        "continuous_probe": certificate,
        "grid_probe_rows": rows,
        "frozen_holdouts_executed": False,
    }


def build_result(
    root: Path,
    preregistration_commit: str,
) -> dict[str, Any]:
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
    control_frame = {
        "frame_id": "positive_control_t3",
        "c": "-4/5",
        "s": "3/5",
    }
    positive_control = rational_frame_row(
        6, Fraction(0), control_frame
    )
    catalog_hash = canonical_hash(catalog)
    continuous_pass_count = sum(row["checked"] for row in continuous_rows)
    grid_pass_count = sum(row["checked"] for row in grid_rows)

    requirements = [
        requirement(
            "P1",
            "Public preregistration commit is an ancestor and hash-binds the contract",
            freeze["verified"],
            freeze,
        ),
        requirement(
            "P2",
            "Frozen holdouts are disjoint from all previous coupling grids",
            set(FROZEN_HOLDOUT_COUPLINGS).isdisjoint(
                PREVIOUSLY_OBSERVED_COUPLINGS
            ),
            {
                "holdouts": [
                    fraction_text(value)
                    for value in FROZEN_HOLDOUT_COUPLINGS
                ],
                "previous_count": len(PREVIOUSLY_OBSERVED_COUPLINGS),
            },
        ),
        requirement(
            "P3",
            "Engineering probe contributes zero frozen decisions",
            True,
            {
                "engineering_coupling": fraction_text(
                    ENGINEERING_COUPLING
                ),
                "acceptance_count": 0,
            },
        ),
        requirement(
            "P4",
            "The frozen exact rational frame catalog has 72 rows and the declared digest",
            len(catalog) == GRID_EXPECTED_COUNT
            and catalog_hash == GRID_EXPECTED_SHA256,
            {
                "count": len(catalog),
                "sha256": catalog_hash,
                "expected_sha256": GRID_EXPECTED_SHA256,
            },
        ),
        requirement(
            "P5",
            "All four continuous symbolic rows execute",
            len(continuous_rows) == 4,
            {"actual": len(continuous_rows), "expected": 4},
        ),
        requirement(
            "P6",
            "Every continuous n=4,5 row has no finite real common minor root",
            all(
                row["finite_real_common_root_count"] == 0
                and row[
                    "finite_real_frames_full_column_rank_certified"
                ]
                for row in continuous_rows
            ),
            {"passed": continuous_pass_count, "total": len(continuous_rows)},
        ),
        requirement(
            "P7",
            "Every projective infinity endpoint has full rank",
            all(
                row["projective_infinity"][
                    "commutator_full_column_rank"
                ]
                for row in continuous_rows
            ),
            {"row_count": len(continuous_rows)},
        ),
        requirement(
            "P8",
            "All 432 frozen rational-frame rows execute",
            len(grid_rows) == 432,
            {"actual": len(grid_rows), "expected": 432},
        ),
        requirement(
            "P9",
            "Every rational-frame operator pool and commutator matrix has full column rank",
            all(row["checked"] for row in grid_rows),
            {"passed": grid_pass_count, "total": len(grid_rows)},
        ),
        requirement(
            "P10",
            "The solvable tilted-frame control recovers extra exact charges",
            bool(
                positive_control["checked"]
                and positive_control[
                    "onsite_tilted_charge_witnesses_checked"
                ]
                and positive_control[
                    "onsite_tilted_charge_commutes_count"
                ]
                == 6
                and positive_control[
                    "onsite_tilted_charge_in_span_count"
                ]
                == 6
            ),
            {
                "nullities": positive_control["modular_nullities"],
                "commuting_witnesses": positive_control.get(
                    "onsite_tilted_charge_commutes_count", 0
                ),
                "in_span_witnesses": positive_control.get(
                    "onsite_tilted_charge_in_span_count", 0
                ),
            },
        ),
        requirement(
            "P11",
            "Every forbidden broad claim remains false",
            True,
            {
                "false_claim_count": len(FALSE_CLAIMS),
                "scientific_promotion_accepted": False,
                "new_credit_delta": 0,
            },
        ),
        requirement(
            "P12",
            "All declared R198 acceptance gates pass",
            bool(
                continuous_pass_count == 4
                and grid_pass_count == 432
                and positive_control["checked"]
            ),
            {
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
            "continuous_determinant_count": sum(
                row["determinant_count"] for row in continuous_rows
            ),
            "continuous_finite_real_common_root_count": sum(
                row["finite_real_common_root_count"]
                for row in continuous_rows
            ),
            "rational_frame_count": len(catalog),
            "rational_grid_row_count": len(grid_rows),
            "rational_grid_pass_count": grid_pass_count,
            "largest_candidate_column_count": max(
                row["candidate_column_count"] for row in grid_rows
            ),
            "largest_commutator_nonzero_count": max(
                row["commutator_nonzero_count"] for row in grid_rows
            ),
            "positive_control_nullities": positive_control[
                "modular_nullities"
            ],
            "requirement_pass_count": sum(
                item["passed"] for item in requirements
            ),
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
        "# B9 R198 Continuous XZ-Frame Stress",
        "",
        f"- Status: `{result['status']}`",
        f"- Protocol hash: `{result['protocol_hash']}`",
        f"- Payload hash: `{result['payload_sha256']}`",
        (
            "- Public preregistration commit: "
            f"`{result['public_freeze']['preregistration_commit']}`"
        ),
        (
            "- Continuous symbolic rows: "
            f"`{summary['continuous_pass_count']}/"
            f"{summary['continuous_row_count']}`"
        ),
        (
            "- Exact maximal-minor determinants: "
            f"`{summary['continuous_determinant_count']}`"
        ),
        (
            "- Finite real common roots after adaptive factor pressure: "
            f"`{summary['continuous_finite_real_common_root_count']}`"
        ),
        (
            "- Rational-frame rows: "
            f"`{summary['rational_grid_pass_count']}/"
            f"{summary['rational_grid_row_count']}`"
        ),
        (
            "- Largest candidate pool / commutator nonzeros: "
            f"`{summary['largest_candidate_column_count']}` / "
            f"`{summary['largest_commutator_nonzero_count']}`"
        ),
        (
            "- Requirements: "
            f"`{summary['requirement_pass_count']}/"
            f"{summary['requirement_count']}`"
        ),
        "- Scientific promotion: `false`",
        "- New credit delta: `0`",
        "",
        "## Research Question",
        "",
        (
            "Can a continuously rotated XZ-plane Jordan-Wigner parity "
            "frame reveal an extra exact quadratic-Majorana conserved "
            "operator missed by the five R197 frames?"
        ),
        "",
        "## Method",
        "",
        (
            "For `n=4,5`, every scaled commutator entry is an exact "
            "integer polynomial in the Pythagorean parameter `t`. "
            "Initial maximal minors are selected at frozen anchors "
            "`0,1,2,4`. Any real-root factor shared by those minors is "
            "attacked by a new row basis selected over the exact quotient "
            "field. Zero real roots in the final common divisor, plus a "
            "full-rank projective-infinity endpoint, certifies the whole "
            "declared real projective line."
        ),
        "",
        (
            "For `n=6,8,10`, the protocol separately checks 72 exact "
            "Pythagorean frames at both holdout couplings under two "
            "prime fields."
        ),
        "",
        "## Continuous Rows",
        "",
        "| J | n | columns | determinants | final gcd degree | real roots | infinity full rank |",
        "|---:|---:|---:|---:|---:|---:|:---:|",
    ]
    for row in result["continuous_rows"]:
        lines.append(
            f"| {row['coupling']} | {row['n']} | "
            f"{row['candidate_column_count']} | "
            f"{row['determinant_count']} | "
            f"{row['final_primitive_gcd_degree']} | "
            f"{row['finite_real_common_root_count']} | "
            f"{str(row['projective_infinity']['commutator_full_column_rank']).lower()} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            (
                "R198 closes only the declared XZ-plane continuous "
                "quadratic-Majorana-plus-parity family at `n=4,5` and "
                "the frozen 72-frame grid at `n=6,8,10`. It does not "
                "exclude general Bloch-sphere frames, nonlinear frame "
                "mixtures, cubic or quartic Majorana charges, nonlocal "
                "dualities, interacting integrability, larger-size "
                "drift, nonintegrability, quantum chaos, spectral "
                "hardness, Quantum PCP, NLTS, BQP separation, hardware "
                "relevance, or a solved frontier."
            ),
            "",
            "## Next Gate",
            "",
            (
                "Run an independent symplectic-bit and polynomial "
                "reconstruction under a third prime. Then attack a "
                "second Bloch-sphere chart, quartic Majorana charges, "
                "or one explicit nonlocal duality."
            ),
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
    if args.engineering_probe:
        result = build_engineering_probe(root)
    else:
        result = build_result(root, args.preregistration_commit)
    output_path = (
        args.output
        if args.output.is_absolute()
        else root / args.output
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            result,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
        + "\n"
    )
    if args.execute_frozen_holdouts:
        report_path = (
            args.report
            if args.report.is_absolute()
            else root / args.report
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_report(result))
    print(
        json.dumps(
            {
                "mode": (
                    "engineering"
                    if args.engineering_probe
                    else "frozen"
                ),
                "status": result.get("status", "engineering_probe"),
                "output": str(output_path),
                "payload_sha256": result.get("payload_sha256"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
