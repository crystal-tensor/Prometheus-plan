#!/usr/bin/env python3
"""Independently reconstruct and audit the B9 R198 result.

The rational-frame path uses sparse symplectic Pauli bit pairs. The
continuous path independently rebuilds the exact polynomial Pauli matrix and
its maximal-minor certificate. No R193-R198 construction module is imported.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import subprocess
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any, Iterable

import sympy as sp


METHOD = "b9_r198_independent_symplectic_polynomial_audit_v1"
VERSION = "1.0"
LAST_UPDATED = "2026-07-30"
AUDIT_PRIME = 1_000_037
MAIN_PRIMES = (1_000_003, 1_000_033)
BASIS_PRIME = MAIN_PRIMES[0]
ALL_PRIMES = (*MAIN_PRIMES, AUDIT_PRIME)
INITIAL_ANCHORS = (0, 1, 2, 4)
MAX_ADAPTIVE_ROUNDS = 12
GRID_BOUND = 7

CONTRACT_PATH = Path(
    "benchmarks/B9_R198_continuous_frame_contract_v0.json"
)
RESULT_PATH = Path("results/B9_R198_continuous_frame_stress_v1.json")
AUDIT_PATH = Path("results/B9_R198_independent_audit_v1.json")
EXPECTED_CONTRACT_SHA256 = (
    "c1b68368dbf9ad577f84838b5a3dd77387c63b78f9f7a7c7e6fa334803f9d03c"
)

T = sp.Symbol("t", real=True)
D = 1 + T * T
POLY_ZERO_ZZ = sp.Poly(0, T, domain=sp.ZZ)
POLY_ZERO_QQ = sp.Poly(0, T, domain=sp.QQ)

I, X, Y, Z = 0, 1, 2, 3
Axis = dict[int, Fraction]
PolyAxis = dict[int, sp.Expr]
PauliKey = tuple[int, int]
Operator = dict[PauliKey, int]
PolyOperator = dict[PauliKey, sp.Poly]

# The exponent denotes i**exponent.
LOCAL_PRODUCT: dict[tuple[int, int], tuple[int, int]] = {
    (I, I): (0, I),
    (I, X): (0, X),
    (I, Y): (0, Y),
    (I, Z): (0, Z),
    (X, I): (0, X),
    (Y, I): (0, Y),
    (Z, I): (0, Z),
    (X, X): (0, I),
    (Y, Y): (0, I),
    (Z, Z): (0, I),
    (X, Y): (1, Z),
    (Y, X): (3, Z),
    (Y, Z): (1, X),
    (Z, Y): (3, X),
    (Z, X): (1, Y),
    (X, Z): (3, Y),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hash(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def fraction_text(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def lcm(values: Iterable[int]) -> int:
    result = 1
    for value in values:
        result = math.lcm(result, value)
    return result


def local_code(key: PauliKey, site: int) -> int:
    x_bit = (key[0] >> site) & 1
    z_bit = (key[1] >> site) & 1
    if x_bit and z_bit:
        return Y
    if x_bit:
        return X
    if z_bit:
        return Z
    return I


def code_key(code: int, site: int) -> PauliKey:
    if code == X:
        return (1 << site, 0)
    if code == Y:
        return (1 << site, 1 << site)
    if code == Z:
        return (0, 1 << site)
    return (0, 0)


def key_word(key: PauliKey, n: int) -> str:
    chars = "IXYZ"
    return "".join(chars[local_code(key, site)] for site in range(n))


def primitive(
    value: dict[PauliKey, Fraction] | dict[PauliKey, int],
    n: int,
) -> Operator:
    fractions = {
        key: Fraction(coefficient)
        for key, coefficient in value.items()
        if coefficient
    }
    if not fractions:
        return {}
    denominator = lcm(
        coefficient.denominator for coefficient in fractions.values()
    )
    integers = {
        key: int(coefficient * denominator)
        for key, coefficient in fractions.items()
    }
    divisor = 0
    for coefficient in integers.values():
        divisor = math.gcd(divisor, abs(coefficient))
    integers = {
        key: coefficient // divisor
        for key, coefficient in integers.items()
        if coefficient
    }
    first = min(integers, key=lambda key: key_word(key, n))
    if integers[first] < 0:
        integers = {
            key: -coefficient for key, coefficient in integers.items()
        }
    return dict(
        sorted(integers.items(), key=lambda item: key_word(item[0], n))
    )


def expand_axes(
    n: int,
    site_axes: dict[int, Axis],
    scale: int = 1,
) -> Operator:
    partial: dict[PauliKey, Fraction] = {
        (0, 0): Fraction(scale)
    }
    for site in sorted(site_axes):
        updated: dict[PauliKey, Fraction] = {}
        for key, coefficient in partial.items():
            for code, local_coefficient in site_axes[site].items():
                local_key = code_key(code, site)
                output = (
                    key[0] | local_key[0],
                    key[1] | local_key[1],
                )
                updated[output] = (
                    updated.get(output, Fraction(0))
                    + coefficient * local_coefficient
                )
        partial = updated
    return primitive(partial, n)


def hamiltonian(n: int, coupling: Fraction) -> Operator:
    terms: dict[PauliKey, Fraction] = {}
    for site in range(n):
        x_key = code_key(X, site)
        z_key = code_key(Z, site)
        terms[x_key] = terms.get(x_key, Fraction(0)) - 1
        terms[z_key] = terms.get(z_key, Fraction(0)) + Fraction(3, 4)
    for site in range(n - 1):
        zz_key = (0, (1 << site) | (1 << (site + 1)))
        terms[zz_key] = terms.get(zz_key, Fraction(0)) + coupling
    return primitive(terms, n)


def anticommutes(left: PauliKey, right: PauliKey) -> bool:
    parity = (
        (left[0] & right[1]).bit_count()
        + (left[1] & right[0]).bit_count()
    )
    return parity % 2 == 1


def multiply(
    left: PauliKey,
    right: PauliKey,
    n: int,
) -> tuple[int, PauliKey]:
    exponent = 0
    output_x = 0
    output_z = 0
    for site in range(n):
        local_exponent, output_code = LOCAL_PRODUCT[
            (local_code(left, site), local_code(right, site))
        ]
        exponent = (exponent + local_exponent) % 4
        local_key = code_key(output_code, site)
        output_x |= local_key[0]
        output_z |= local_key[1]
    return exponent, (output_x, output_z)


def commutator(
    h_value: Operator,
    candidate: Operator,
    n: int,
) -> Operator:
    output: dict[PauliKey, Fraction] = {}
    for h_key, h_coefficient in h_value.items():
        for candidate_key, candidate_coefficient in candidate.items():
            if not anticommutes(h_key, candidate_key):
                continue
            exponent, output_key = multiply(h_key, candidate_key, n)
            if exponent == 1:
                sign = 1
            elif exponent == 3:
                sign = -1
            else:
                raise AssertionError("invalid anticommuting phase")
            output[output_key] = (
                output.get(output_key, Fraction(0))
                + h_coefficient * candidate_coefficient * sign
            )
    return primitive(output, n)


def frame(c_value: Fraction, s_value: Fraction) -> dict[str, Axis]:
    return {
        "P": {X: c_value, Z: s_value},
        "Q": {X: s_value, Z: -c_value},
        "R": {Y: Fraction(1)},
    }


def gamma(
    n: int,
    axes: dict[str, Axis],
    site: int,
    endpoint: str,
) -> Operator:
    site_axes = {index: axes["P"] for index in range(site)}
    site_axes[site] = axes[endpoint]
    return expand_axes(n, site_axes)


def bilinear(
    n: int,
    axes: dict[str, Axis],
    left_site: int,
    left_endpoint: str,
    right_site: int,
    right_endpoint: str,
) -> Operator:
    if left_site == right_site:
        return expand_axes(n, {left_site: axes["P"]}, scale=-1)
    site_axes: dict[int, Axis] = {}
    sign = 1
    if left_endpoint == "Q":
        site_axes[left_site] = axes["R"]
    else:
        site_axes[left_site] = axes["Q"]
        sign = -1
    for site in range(left_site + 1, right_site):
        site_axes[site] = axes["P"]
    site_axes[right_site] = axes[right_endpoint]
    return expand_axes(n, site_axes, scale=sign)


@cache
def rational_pool(
    n: int,
    c_value: Fraction,
    s_value: Fraction,
) -> tuple[tuple[str, Operator], ...]:
    axes = frame(c_value, s_value)
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
                gamma(n, axes, site, endpoint),
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
                    bilinear(
                        n,
                        axes,
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
            expand_axes(
                n, {site: axes["P"] for site in range(n)}
            ),
        )
    )
    return tuple(entries)


def sparse_rank(
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


def operator_rank(
    operators: list[Operator],
    n: int,
    prime: int,
) -> int:
    words = sorted(
        {
            key_word(key, n)
            for operator in operators
            for key in operator
        }
    )
    index = {word: row for row, word in enumerate(words)}
    columns = [
        {
            index[key_word(key, n)]: coefficient
            for key, coefficient in operator.items()
        }
        for operator in operators
    ]
    return sparse_rank(columns, prime)


def in_span(
    operator: Operator,
    basis: list[Operator],
    n: int,
) -> bool:
    return operator_rank(basis + [operator], n, BASIS_PRIME) == len(
        basis
    )


def rational_catalog() -> list[dict[str, str]]:
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


def rational_rebuild(
    n: int,
    coupling: Fraction,
    frame_entry: dict[str, str],
    primes: tuple[int, ...] = ALL_PRIMES,
) -> dict[str, Any]:
    c_value = Fraction(frame_entry["c"])
    s_value = Fraction(frame_entry["s"])
    entries = list(rational_pool(n, c_value, s_value))
    labels = [label for label, _ in entries]
    operators = [operator for _, operator in entries]
    h_value = hamiltonian(n, coupling)
    raw_columns = [
        commutator(h_value, operator, n) for operator in operators
    ]
    output_words = sorted(
        {
            key_word(key, n)
            for column in raw_columns
            for key in column
        }
    )
    output_index = {
        word: index for index, word in enumerate(output_words)
    }
    columns = [
        {
            output_index[key_word(key, n)]: coefficient
            for key, coefficient in column.items()
        }
        for column in raw_columns
    ]
    operator_ranks = {
        str(prime): operator_rank(operators, n, prime)
        for prime in primes
    }
    ranks = {
        str(prime): sparse_rank(columns, prime) for prime in primes
    }
    operator_payload = {
        "labels": labels,
        "operators": [
            sorted(
                (
                    key_word(key, n),
                    coefficient,
                )
                for key, coefficient in operator.items()
            )
            for operator in operators
        ],
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
    column_count = len(columns)
    rebuilt: dict[str, Any] = {
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
        "modular_ranks": ranks,
        "modular_nullities": {
            str(prime): column_count - ranks[str(prime)]
            for prime in primes
        },
    }
    if coupling == 0 and c_value == Fraction(-4, 5) and s_value == Fraction(3, 5):
        tilted = {X: Fraction(-4, 5), Z: Fraction(3, 5)}
        witnesses = [
            expand_axes(n, {site: tilted}) for site in range(n)
        ]
        rebuilt["onsite_tilted_charge_witness_count"] = len(witnesses)
        rebuilt["onsite_tilted_charge_commutes_count"] = sum(
            not commutator(h_value, witness, n)
            for witness in witnesses
        )
        rebuilt["onsite_tilted_charge_in_span_count"] = sum(
            in_span(witness, operators, n) for witness in witnesses
        )
        rebuilt["onsite_tilted_charge_witnesses_checked"] = bool(
            rebuilt["onsite_tilted_charge_commutes_count"] == n
            and rebuilt["onsite_tilted_charge_in_span_count"] == n
        )
    return rebuilt


def poly_axes() -> dict[str, PolyAxis]:
    return {
        "P": {X: 1 - T * T, Z: 2 * T},
        "Q": {X: 2 * T, Z: T * T - 1},
        "R": {Y: D},
    }


def expand_poly_axes(
    n: int,
    site_axes: dict[int, PolyAxis],
    scale: int = 1,
) -> PolyOperator:
    partial: dict[PauliKey, sp.Expr] = {(0, 0): sp.Integer(scale)}
    for site in sorted(site_axes):
        updated: dict[PauliKey, sp.Expr] = {}
        for key, coefficient in partial.items():
            for code, local_coefficient in site_axes[site].items():
                local_key = code_key(code, site)
                output = (
                    key[0] | local_key[0],
                    key[1] | local_key[1],
                )
                updated[output] = sp.expand(
                    updated.get(output, 0)
                    + coefficient * local_coefficient
                )
        partial = updated
    return {
        key: sp.Poly(coefficient, T, domain=sp.ZZ)
        for key, coefficient in partial.items()
        if coefficient != 0
    }


@cache
def poly_pool(n: int) -> tuple[tuple[str, PolyOperator], ...]:
    axes = poly_axes()
    gamma_labels = [
        (site, endpoint)
        for site in range(n)
        for endpoint in ("Q", "R")
    ]
    entries: list[tuple[str, PolyOperator]] = []
    for site, endpoint in gamma_labels:
        site_axes = {
            index: axes["P"] for index in range(site)
        }
        site_axes[site] = axes[endpoint]
        entries.append(
            (
                f"gamma:{site}:{endpoint}",
                expand_poly_axes(n, site_axes),
            )
        )
    for left_index, (left_site, left_endpoint) in enumerate(gamma_labels):
        for right_site, right_endpoint in gamma_labels[left_index + 1 :]:
            if left_site == right_site:
                operator = expand_poly_axes(
                    n, {left_site: axes["P"]}, scale=-1
                )
            else:
                site_axes: dict[int, PolyAxis] = {}
                sign = 1
                if left_endpoint == "Q":
                    site_axes[left_site] = axes["R"]
                else:
                    site_axes[left_site] = axes["Q"]
                    sign = -1
                for site in range(left_site + 1, right_site):
                    site_axes[site] = axes["P"]
                site_axes[right_site] = axes[right_endpoint]
                operator = expand_poly_axes(
                    n, site_axes, scale=sign
                )
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
            expand_poly_axes(
                n, {site: axes["P"] for site in range(n)}
            ),
        )
    )
    return tuple(entries)


def commutator_poly(
    h_value: Operator,
    candidate: PolyOperator,
    n: int,
) -> PolyOperator:
    output: dict[PauliKey, sp.Poly] = {}
    for h_key, h_coefficient in h_value.items():
        for candidate_key, candidate_coefficient in candidate.items():
            if not anticommutes(h_key, candidate_key):
                continue
            exponent, output_key = multiply(h_key, candidate_key, n)
            if exponent == 1:
                sign = 1
            elif exponent == 3:
                sign = -1
            else:
                raise AssertionError("invalid polynomial commutator phase")
            output[output_key] = (
                output.get(output_key, POLY_ZERO_ZZ)
                + candidate_coefficient * (h_coefficient * sign)
            )
    return {
        key: sp.Poly(coefficient, T, domain=sp.ZZ)
        for key, coefficient in output.items()
        if not coefficient.is_zero
    }


def normalized_primitive(poly: sp.Poly) -> tuple[int, sp.Poly]:
    poly = sp.Poly(poly, T, domain=sp.ZZ)
    content, primitive_poly = sp.polys.polytools.primitive(poly)
    primitive_poly = sp.Poly(primitive_poly, T, domain=sp.ZZ)
    if primitive_poly.LC() < 0:
        primitive_poly = -primitive_poly
        content = -content
    return int(content), primitive_poly


def poly_coefficients(poly: sp.Poly) -> list[str]:
    return [str(int(coefficient)) for coefficient in poly.all_coeffs()]


def symbolic_matrix(
    n: int,
    coupling: Fraction,
) -> tuple[list[str], list[PolyOperator], list[str], str]:
    entries = list(poly_pool(n))
    labels = [label for label, _ in entries]
    h_value = hamiltonian(n, coupling)
    columns = [
        commutator_poly(h_value, operator, n)
        for _, operator in entries
    ]
    output_words = sorted(
        {
            key_word(key, n)
            for column in columns
            for key in column
        }
    )
    triples = [
        (
            key_word(key, n),
            column_index,
            poly_coefficients(coefficient),
        )
        for column_index, column in enumerate(columns)
        for key, coefficient in sorted(
            column.items(), key=lambda item: key_word(item[0], n)
        )
    ]
    matrix_hash = canonical_hash(
        {
            "labels": labels,
            "output_words": output_words,
            "triples": triples,
        }
    )
    return labels, columns, output_words, matrix_hash


def poly_at_word(
    column: PolyOperator,
    word: str,
    n: int,
    domain: str = "ZZ",
) -> sp.Poly:
    for key, coefficient in column.items():
        if key_word(key, n) == word:
            return coefficient
    return POLY_ZERO_ZZ if domain == "ZZ" else POLY_ZERO_QQ


def rows_at_anchor(
    columns: list[PolyOperator],
    output_words: list[str],
    n: int,
    anchor: int,
    prime: int,
) -> list[str]:
    pivots: dict[int, dict[int, int]] = {}
    selected: list[str] = []
    for word in output_words:
        vector = {
            column_index: int(
                poly_at_word(
                    columns[column_index], word, n
                ).eval(anchor)
            )
            % prime
            for column_index in range(len(columns))
        }
        vector = {
            index: coefficient
            for index, coefficient in vector.items()
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


def rows_over_factor(
    columns: list[PolyOperator],
    output_words: list[str],
    n: int,
    factor: sp.Poly,
) -> list[str]:
    factor = sp.Poly(factor, T, domain=sp.QQ)
    pivots: dict[int, dict[int, sp.Poly]] = {}
    selected: list[str] = []
    for word in output_words:
        vector = {
            column_index: field_reduce(
                poly_at_word(
                    columns[column_index], word, n, domain="QQ"
                ),
                factor,
            )
            for column_index in range(len(columns))
        }
        vector = {
            index: coefficient
            for index, coefficient in vector.items()
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
            multiplier = vector[pivot]
            for index, coefficient in pivots[pivot].items():
                updated = field_reduce(
                    vector.get(index, POLY_ZERO_QQ)
                    - field_multiply(
                        multiplier, coefficient, factor
                    ),
                    factor,
                )
                if updated.is_zero:
                    vector.pop(index, None)
                else:
                    vector[index] = updated
        if len(selected) == len(columns):
            break
    return selected


def determinant(
    columns: list[PolyOperator],
    row_words: list[str],
    n: int,
    source: dict[str, Any],
) -> tuple[dict[str, Any], sp.Poly]:
    matrix = sp.Matrix(
        [
            [
                poly_at_word(columns[column_index], word, n).as_expr()
                for column_index in range(len(columns))
            ]
            for word in row_words
        ]
    )
    raw = sp.Poly(matrix.det(method="domain-ge"), T, domain=sp.ZZ)
    content, primitive_poly = normalized_primitive(raw)
    coefficients = poly_coefficients(primitive_poly)
    record = {
        "source": source,
        "row_count": len(row_words),
        "row_words_sha256": canonical_hash(row_words),
        "degree": primitive_poly.degree(),
        "term_count": len(primitive_poly.terms()),
        "content_abs_bit_length": abs(content).bit_length(),
        "primitive_max_coefficient_bit_length": max(
            abs(int(coefficient)).bit_length()
            for coefficient in primitive_poly.all_coeffs()
        ),
        "primitive_determinant_sha256": canonical_hash(
            {
                "row_words": row_words,
                "primitive_coefficients": coefficients,
            }
        ),
    }
    return record, primitive_poly


def factor_records(poly: sp.Poly) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for factor, exponent in sp.factor_list(poly)[1]:
        _, primitive_poly = normalized_primitive(
            sp.Poly(factor, T, domain=sp.ZZ)
        )
        coefficients = poly_coefficients(primitive_poly)
        records.append(
            {
                "degree": primitive_poly.degree(),
                "exponent": int(exponent),
                "coefficients": coefficients,
                "factor_sha256": canonical_hash(coefficients),
                "real_root_count": int(
                    sp.polys.polytools.count_roots(
                        sp.Poly(
                            primitive_poly, T, domain=sp.QQ
                        ),
                        -sp.oo,
                        sp.oo,
                    )
                ),
            }
        )
    return records


def continuous_rebuild(
    n: int,
    coupling: Fraction,
) -> dict[str, Any]:
    labels, columns, output_words, matrix_hash = symbolic_matrix(
        n, coupling
    )
    determinant_records: list[dict[str, Any]] = []
    determinant_polys: list[sp.Poly] = []
    for anchor in INITIAL_ANCHORS:
        row_words = rows_at_anchor(
            columns, output_words, n, anchor, BASIS_PRIME
        )
        record, determinant_poly = determinant(
            columns,
            row_words,
            n,
            {
                "type": "integer_anchor",
                "anchor": anchor,
                "selection_prime": BASIS_PRIME,
            },
        )
        determinant_records.append(record)
        determinant_polys.append(determinant_poly)

    unresolved: list[dict[str, Any]] = []
    adaptive_round = 0
    while determinant_polys and adaptive_round < MAX_ADAPTIVE_ROUNDS:
        gcd_poly = determinant_polys[0]
        for determinant_poly in determinant_polys[1:]:
            gcd_poly = sp.gcd(gcd_poly, determinant_poly)
        _, gcd_poly = normalized_primitive(gcd_poly)
        real_factors = [
            item
            for item in factor_records(gcd_poly)
            if item["real_root_count"] > 0
        ]
        if not real_factors:
            break
        factor_record = real_factors[0]
        factor = sp.Poly(
            [int(value) for value in factor_record["coefficients"]],
            T,
            domain=sp.QQ,
        )
        row_words = rows_over_factor(
            columns, output_words, n, factor
        )
        if len(row_words) != len(columns):
            unresolved.append(
                {
                    **factor_record,
                    "quotient_field_rank": len(row_words),
                    "candidate_column_count": len(columns),
                }
            )
            break
        record, determinant_poly = determinant(
            columns,
            row_words,
            n,
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
        determinant_polys.append(determinant_poly)
        adaptive_round += 1

    gcd_poly = determinant_polys[0]
    for determinant_poly in determinant_polys[1:]:
        gcd_poly = sp.gcd(gcd_poly, determinant_poly)
    _, gcd_poly = normalized_primitive(gcd_poly)
    square_free = sp.Poly(
        sp.sqf_part(gcd_poly), T, domain=sp.QQ
    )
    finite_roots = int(
        sp.polys.polytools.count_roots(
            square_free, -sp.oo, sp.oo
        )
    )
    infinity = rational_rebuild(
        n,
        coupling,
        {"frame_id": "projective_infinity", "c": "-1", "s": "0"},
    )

    sampled_ranks: dict[str, int] = {}
    for anchor in (0, 1, 2, 3, 5, 7, 11):
        evaluated_columns: list[dict[int, int]] = []
        word_index = {
            word: index for index, word in enumerate(output_words)
        }
        for column in columns:
            evaluated_columns.append(
                {
                    word_index[key_word(key, n)]: int(
                        coefficient.eval(anchor)
                    )
                    for key, coefficient in column.items()
                    if int(coefficient.eval(anchor))
                }
            )
        sampled_ranks[str(anchor)] = sparse_rank(
            evaluated_columns, AUDIT_PRIME
        )

    return {
        "coupling": fraction_text(coupling),
        "n": n,
        "candidate_column_count": len(columns),
        "candidate_labels_sha256": canonical_hash(labels),
        "output_basis_size": len(output_words),
        "polynomial_commutator_nonzero_count": sum(
            len(column) for column in columns
        ),
        "polynomial_commutator_matrix_sha256": matrix_hash,
        "determinant_count": len(determinant_records),
        "determinants": determinant_records,
        "adaptive_round_count": adaptive_round,
        "unresolved_factors": unresolved,
        "final_primitive_gcd_degree": gcd_poly.degree(),
        "final_primitive_gcd_sha256": canonical_hash(
            poly_coefficients(gcd_poly)
        ),
        "final_factorization": factor_records(gcd_poly),
        "square_free_gcd_degree": square_free.degree(),
        "finite_real_common_root_count": finite_roots,
        "projective_infinity": infinity,
        "third_prime_sampled_ranks": sampled_ranks,
    }


def verify_freeze(
    root: Path,
    source: dict[str, Any],
) -> dict[str, Any]:
    commit = source["public_freeze"]["preregistration_commit"]
    ancestor = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=root,
            check=False,
        ).returncode
        == 0
    )
    frozen = subprocess.run(
        ["git", "show", f"{commit}:{CONTRACT_PATH}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    frozen_hash = sha256_bytes(frozen)
    working_hash = sha256_file(root / CONTRACT_PATH)
    return {
        "preregistration_commit": commit,
        "is_ancestor": ancestor,
        "contract_sha256_at_commit": frozen_hash,
        "working_contract_sha256": working_hash,
        "expected_contract_sha256": EXPECTED_CONTRACT_SHA256,
        "verified": bool(
            ancestor
            and frozen_hash == EXPECTED_CONTRACT_SHA256
            and working_hash == EXPECTED_CONTRACT_SHA256
        ),
    }


def forbidden_imports() -> dict[str, Any]:
    tree = ast.parse(Path(__file__).read_text())
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    forbidden = [
        name
        for name in imported
        if any(
            token in name
            for token in (
                "b9_r193",
                "b9_r194",
                "b9_r195",
                "b9_r196",
                "b9_r197",
                "b9_r198_continuous_frame_stress",
            )
        )
    ]
    return {
        "imported_modules": sorted(imported),
        "forbidden_imports": forbidden,
        "checked": not forbidden,
    }


def compare_rational(
    source: dict[str, Any],
    rebuilt: dict[str, Any],
    row_id: str,
) -> list[str]:
    errors: list[str] = []
    exact_fields = (
        "frame_id",
        "c",
        "s",
        "coupling",
        "n",
        "candidate_column_count",
        "operator_basis_pauli_nonzero_count",
        "operator_basis_sha256",
        "output_basis_size",
        "commutator_nonzero_count",
        "commutator_matrix_sha256",
    )
    for field in exact_fields:
        if source.get(field) != rebuilt.get(field):
            errors.append(f"{row_id}: {field} mismatch")
    for prime in MAIN_PRIMES:
        key = str(prime)
        if source["operator_basis_modular_ranks"].get(key) != rebuilt[
            "operator_basis_modular_ranks"
        ].get(key):
            errors.append(f"{row_id}: operator rank {prime} mismatch")
        if source["modular_ranks"].get(key) != rebuilt[
            "modular_ranks"
        ].get(key):
            errors.append(f"{row_id}: commutator rank {prime} mismatch")
    column_count = rebuilt["candidate_column_count"]
    if rebuilt["operator_basis_modular_ranks"][str(AUDIT_PRIME)] != column_count:
        errors.append(f"{row_id}: third-prime operator rank deficient")
    if source["coupling"] != "0" and rebuilt["modular_ranks"][
        str(AUDIT_PRIME)
    ] != column_count:
        errors.append(f"{row_id}: third-prime commutator rank deficient")
    return errors


def compare_continuous(
    source: dict[str, Any],
    rebuilt: dict[str, Any],
) -> list[str]:
    row_id = f"continuous J={source['coupling']},n={source['n']}"
    errors: list[str] = []
    exact_fields = (
        "coupling",
        "n",
        "candidate_column_count",
        "candidate_labels_sha256",
        "output_basis_size",
        "polynomial_commutator_nonzero_count",
        "polynomial_commutator_matrix_sha256",
        "determinant_count",
        "adaptive_round_count",
        "unresolved_factors",
        "final_primitive_gcd_degree",
        "final_primitive_gcd_sha256",
        "final_factorization",
        "square_free_gcd_degree",
        "finite_real_common_root_count",
    )
    for field in exact_fields:
        if source.get(field) != rebuilt.get(field):
            errors.append(f"{row_id}: {field} mismatch")
    if len(source["determinants"]) != len(rebuilt["determinants"]):
        errors.append(f"{row_id}: determinant record count mismatch")
    else:
        determinant_fields = (
            "source",
            "row_count",
            "row_words_sha256",
            "degree",
            "term_count",
            "content_abs_bit_length",
            "primitive_max_coefficient_bit_length",
            "primitive_determinant_sha256",
        )
        for index, (source_item, rebuilt_item) in enumerate(
            zip(source["determinants"], rebuilt["determinants"])
        ):
            for field in determinant_fields:
                if source_item.get(field) != rebuilt_item.get(field):
                    errors.append(
                        f"{row_id}: determinant {index} {field} mismatch"
                    )
    errors.extend(
        compare_rational(
            source["projective_infinity"],
            rebuilt["projective_infinity"],
            f"{row_id}: infinity",
        )
    )
    column_count = rebuilt["candidate_column_count"]
    if any(
        rank != column_count
        for rank in rebuilt["third_prime_sampled_ranks"].values()
    ):
        errors.append(f"{row_id}: sampled third-prime rank deficient")
    return errors


def build_audit(root: Path) -> dict[str, Any]:
    source = json.loads((root / RESULT_PATH).read_text())
    contract = json.loads((root / CONTRACT_PATH).read_text())
    freeze = verify_freeze(root, source)
    imports = forbidden_imports()
    errors: list[str] = []

    catalog = rational_catalog()
    if len(catalog) != 72:
        errors.append("independent catalog count mismatch")
    if canonical_hash(catalog) != contract["rational_frame_pressure"][
        "catalog_sha256"
    ]:
        errors.append("independent catalog hash mismatch")
    if catalog != source["rational_frame_catalog"]:
        errors.append("independent catalog content mismatch")

    continuous_rows: list[dict[str, Any]] = []
    for source_row in source["continuous_rows"]:
        rebuilt = continuous_rebuild(
            int(source_row["n"]),
            Fraction(source_row["coupling"]),
        )
        continuous_rows.append(rebuilt)
        errors.extend(compare_continuous(source_row, rebuilt))

    rational_rows: list[dict[str, Any]] = []
    for source_row in source["rational_grid_rows"]:
        rebuilt = rational_rebuild(
            int(source_row["n"]),
            Fraction(source_row["coupling"]),
            {
                "frame_id": source_row["frame_id"],
                "c": source_row["c"],
                "s": source_row["s"],
            },
        )
        row_id = (
            f"grid J={source_row['coupling']},n={source_row['n']},"
            f"frame={source_row['frame_id']}"
        )
        errors.extend(compare_rational(source_row, rebuilt, row_id))
        rational_rows.append(
            {
                "coupling": rebuilt["coupling"],
                "n": rebuilt["n"],
                "frame_id": rebuilt["frame_id"],
                "candidate_column_count": rebuilt[
                    "candidate_column_count"
                ],
                "operator_basis_sha256": rebuilt[
                    "operator_basis_sha256"
                ],
                "commutator_matrix_sha256": rebuilt[
                    "commutator_matrix_sha256"
                ],
                "third_prime_operator_rank": rebuilt[
                    "operator_basis_modular_ranks"
                ][str(AUDIT_PRIME)],
                "third_prime_commutator_rank": rebuilt[
                    "modular_ranks"
                ][str(AUDIT_PRIME)],
            }
        )

    control_source = source["positive_control"]
    control = rational_rebuild(
        int(control_source["n"]),
        Fraction(control_source["coupling"]),
        {
            "frame_id": control_source["frame_id"],
            "c": control_source["c"],
            "s": control_source["s"],
        },
    )
    errors.extend(
        compare_rational(control_source, control, "positive control")
    )
    for field in (
        "onsite_tilted_charge_witness_count",
        "onsite_tilted_charge_commutes_count",
        "onsite_tilted_charge_in_span_count",
        "onsite_tilted_charge_witnesses_checked",
    ):
        if control_source.get(field) != control.get(field):
            errors.append(f"positive control: {field} mismatch")
    source_control_nullity = next(
        iter(control_source["modular_nullities"].values())
    )
    audit_control_nullity = (
        control["candidate_column_count"]
        - control["modular_ranks"][str(AUDIT_PRIME)]
    )
    if source_control_nullity != audit_control_nullity:
        errors.append("positive control third-prime nullity mismatch")

    if not freeze["verified"]:
        errors.append("public freeze verification failed")
    if not imports["checked"]:
        errors.append("forbidden construction module import detected")
    if source["status"] != "checked_continuous_xz_frame_boundary":
        errors.append("source result is not an accepted scoped boundary")
    if not all(item["passed"] for item in source["requirements"]):
        errors.append("source acceptance requirements are incomplete")
    if source["claims"]["scientific_promotion_accepted"] is not False:
        errors.append("scientific promotion must remain false")
    if source["claims"]["new_credit_delta"] != 0:
        errors.append("new credit delta must remain zero")
    if any(source["claims"].get(claim) for claim in contract[
        "claim_boundary"
    ]["forbidden"]):
        errors.append("at least one forbidden broad claim is true")

    continuous_compact = [
        {
            "coupling": row["coupling"],
            "n": row["n"],
            "candidate_column_count": row["candidate_column_count"],
            "polynomial_commutator_matrix_sha256": row[
                "polynomial_commutator_matrix_sha256"
            ],
            "determinant_count": row["determinant_count"],
            "final_primitive_gcd_sha256": row[
                "final_primitive_gcd_sha256"
            ],
            "finite_real_common_root_count": row[
                "finite_real_common_root_count"
            ],
            "third_prime_sampled_ranks": row[
                "third_prime_sampled_ranks"
            ],
            "projective_infinity_third_prime_rank": row[
                "projective_infinity"
            ]["modular_ranks"][str(AUDIT_PRIME)],
        }
        for row in continuous_rows
    ]
    core = {
        "source_result": {
            "path": str(RESULT_PATH),
            "sha256": sha256_file(root / RESULT_PATH),
            "payload_sha256": source["payload_sha256"],
        },
        "public_freeze": freeze,
        "forbidden_import_audit": imports,
        "audit_prime": AUDIT_PRIME,
        "catalog_count": len(catalog),
        "catalog_sha256": canonical_hash(catalog),
        "continuous_rebuilds": continuous_compact,
        "rational_grid_rebuilds": rational_rows,
        "positive_control": {
            "third_prime_nullity": audit_control_nullity,
            "commuting_witness_count": control[
                "onsite_tilted_charge_commutes_count"
            ],
            "in_span_witness_count": control[
                "onsite_tilted_charge_in_span_count"
            ],
        },
        "errors": errors,
    }
    return {
        "experiment_id": "B9-R198-independent-audit",
        "method": METHOD,
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "status": "pass" if not errors else "fail",
        "audit_prime": AUDIT_PRIME,
        "continuous_row_count": len(continuous_rows),
        "continuous_exact_match_count": (
            len(continuous_rows) if not any(
                error.startswith("continuous") for error in errors
            ) else None
        ),
        "rational_grid_row_count": len(rational_rows),
        "third_prime_full_rank_grid_count": sum(
            row["third_prime_commutator_rank"]
            == row["candidate_column_count"]
            for row in rational_rows
        ),
        "positive_control_third_prime_nullity": audit_control_nullity,
        "evidence_integrity_complete": not errors,
        "error_count": len(errors),
        "errors": errors,
        "source_result": core["source_result"],
        "public_freeze": freeze,
        "forbidden_import_audit": imports,
        "catalog_count": len(catalog),
        "catalog_sha256": canonical_hash(catalog),
        "continuous_rebuilds": continuous_compact,
        "rational_grid_rebuilds": rational_rows,
        "positive_control": core["positive_control"],
        "payload_sha256": canonical_hash(core),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    audit = build_audit(root)
    output_path = args.json_output or root / AUDIT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            audit,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "status": audit["status"],
                "continuous_exact_match_count": audit[
                    "continuous_exact_match_count"
                ],
                "third_prime_full_rank_grid_count": audit[
                    "third_prime_full_rank_grid_count"
                ],
                "rational_grid_row_count": audit[
                    "rational_grid_row_count"
                ],
                "positive_control_third_prime_nullity": audit[
                    "positive_control_third_prime_nullity"
                ],
                "error_count": audit["error_count"],
                "payload_sha256": audit["payload_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if audit["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
