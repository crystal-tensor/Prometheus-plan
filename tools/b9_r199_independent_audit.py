#!/usr/bin/env python3
"""Independent, bounded sidecar audit for the B9 R199 result.

This file reconstructs the A-Y meridian candidate family from sparse
symplectic Pauli keys.  It deliberately does not import or dynamically load
any R193-R199 implementation module.  The main result is treated only as an
artifact to compare after the independent catalog, grid keys, operators,
commutators, determinants, and root certificates have been defined.
"""

from __future__ import annotations

import argparse
import ast
import gc
import hashlib
import json
import math
import subprocess
from collections import Counter
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any, Iterable, TypeVar

import sympy as sp


EXPERIMENT_ID = "B9-R199-independent-audit"
METHOD = "b9_r199_independent_symplectic_sturm_audit_v1"
VERSION = "1.0"
LAST_UPDATED = "2026-10-30"
STATUS_ACCEPTED = "checked_continuous_ay_meridian_boundary"
AUDIT_PRIME = 1_000_037
SOURCE_PRIMES = (1_000_003, 1_000_033)
BASIS_PRIME = SOURCE_PRIMES[0]
SOURCE_ANCHORS = (0, 1, 2, 4)
AUDIT_ANCHORS = (-3, -1, 3, 5)
MAX_ADAPTIVE_ROUNDS = 12
GRID_BOUND = 7
FROZEN_COUPLINGS = (Fraction(97, 128), Fraction(107, 128))
CONTINUOUS_SIZES = (4, 5)
GRID_SIZES = (6, 8, 10)

CONTRACT_PATH = Path("benchmarks/B9_R199_ay_meridian_contract_v0.json")
RESULT_PATH = Path("results/B9_R199_ay_meridian_stress_v1.json")
AUDIT_PATH = Path("results/B9_R199_independent_audit_v1.json")
EXPECTED_CONTRACT_SHA256 = (
    "a9679357747deb983de1285946ac97c1679c018b383a8e5e0d9c2c9cc6bcb1cb"
)
EXPECTED_CATALOG_SHA256 = (
    "d39600595c4b54b622e6a76acdf4e0838322901d13aa3b72bda8a67599547842"
)

T = sp.Symbol("t", real=True)
D = 1 + T * T
I, X, Y, Z = 0, 1, 2, 3
PauliKey = tuple[int, int]
Operator = dict[PauliKey, int]
RationalAxis = dict[int, Fraction]
PolynomialAxis = dict[int, sp.Expr]
PolynomialOperator = dict[PauliKey, sp.Poly]
GaussianQ = tuple[Fraction, Fraction]
GaussianP = tuple[sp.Expr, sp.Expr]
PolyQ = list[Fraction]
Coefficient = TypeVar("Coefficient", Fraction, sp.Expr)

AXIS_A: RationalAxis = {X: Fraction(-4, 5), Z: Fraction(3, 5)}
AXIS_B: RationalAxis = {X: Fraction(-3, 5), Z: Fraction(-4, 5)}
AXIS_Y: RationalAxis = {Y: Fraction(1)}

FORBIDDEN_CLAIM_KEYS = (
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
)
SOURCE_FIELDS_CONSUMED_FOR_REBUILD: tuple[str, ...] = ()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hash(value: Any) -> str:
    return sha256_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
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
        return 1 << site, 0
    if code == Y:
        return 1 << site, 1 << site
    if code == Z:
        return 0, 1 << site
    return 0, 0


def key_word(key: PauliKey, n: int) -> str:
    chars = "IXYZ"
    return "".join(chars[local_code(key, site)] for site in range(n))


def pauli_product(left: PauliKey, right: PauliKey) -> tuple[int, PauliKey]:
    """Return exponent e and key K for P(left)P(right)=i**e P(K).

    The canonical Hermitian convention is
    P(x,z)=i**popcount(x&z) X**x Z**z.  This phase rule is independent of
    the table-driven implementation used by the source experiment.
    """

    output = left[0] ^ right[0], left[1] ^ right[1]
    exponent = (
        (left[0] & left[1]).bit_count()
        + (right[0] & right[1]).bit_count()
        + 2 * (left[1] & right[0]).bit_count()
        - (output[0] & output[1]).bit_count()
    ) % 4
    return exponent, output


def one_qubit_phase_oracle() -> dict[str, Any]:
    matrices = {
        I: ((1 + 0j, 0j), (0j, 1 + 0j)),
        X: ((0j, 1 + 0j), (1 + 0j, 0j)),
        Y: ((0j, -1j), (1j, 0j)),
        Z: ((1 + 0j, 0j), (0j, -1 + 0j)),
    }

    def multiply_matrix(
        left: tuple[tuple[complex, complex], tuple[complex, complex]],
        right: tuple[tuple[complex, complex], tuple[complex, complex]],
    ) -> tuple[tuple[complex, complex], tuple[complex, complex]]:
        return tuple(
            tuple(sum(left[row][k] * right[k][column] for k in range(2)) for column in range(2))
            for row in range(2)
        )  # type: ignore[return-value]

    rows: list[dict[str, Any]] = []
    for left_code in (I, X, Y, Z):
        for right_code in (I, X, Y, Z):
            exponent, output = pauli_product(
                code_key(left_code, 0), code_key(right_code, 0)
            )
            output_code = local_code(output, 0)
            predicted = tuple(
                tuple((1j**exponent) * value for value in row)
                for row in matrices[output_code]
            )
            observed = multiply_matrix(matrices[left_code], matrices[right_code])
            rows.append(
                {
                    "left": "IXYZ"[left_code],
                    "right": "IXYZ"[right_code],
                    "phase_exponent": exponent,
                    "output": "IXYZ"[output_code],
                    "passed": predicted == observed,
                }
            )
    return {
        "case_count": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "checked": all(row["passed"] for row in rows),
        "cases": rows,
    }


def primitive(value: dict[PauliKey, Fraction], n: int) -> Operator:
    clean = {key: Fraction(coefficient) for key, coefficient in value.items() if coefficient}
    if not clean:
        return {}
    denominator = lcm(coefficient.denominator for coefficient in clean.values())
    integers = {key: int(coefficient * denominator) for key, coefficient in clean.items()}
    divisor = 0
    for coefficient in integers.values():
        divisor = math.gcd(divisor, abs(coefficient))
    integers = {key: coefficient // divisor for key, coefficient in integers.items() if coefficient}
    first = min(integers, key=lambda key: key_word(key, n))
    if integers[first] < 0:
        integers = {key: -coefficient for key, coefficient in integers.items()}
    return dict(sorted(integers.items(), key=lambda item: key_word(item[0], n)))


def add_axes(*axes: RationalAxis) -> RationalAxis:
    output: RationalAxis = {}
    for axis in axes:
        for code, coefficient in axis.items():
            output[code] = output.get(code, Fraction(0)) + coefficient
    return {code: coefficient for code, coefficient in output.items() if coefficient}


def scale_axis(axis: RationalAxis, scale: Fraction) -> RationalAxis:
    return {code: coefficient * scale for code, coefficient in axis.items() if coefficient * scale}


def rational_frame(c_value: Fraction, s_value: Fraction) -> dict[str, RationalAxis]:
    return {
        "P": add_axes(scale_axis(AXIS_A, c_value), scale_axis(AXIS_Y, s_value)),
        "Q": add_axes(scale_axis(AXIS_A, -s_value), scale_axis(AXIS_Y, c_value)),
        "R": dict(AXIS_B),
    }


def gamma_factors(
    n: int,
    frame: dict[str, dict[int, Coefficient]],
    site: int,
    endpoint: str,
    one: Coefficient,
) -> list[dict[int, Coefficient]]:
    factors: list[dict[int, Coefficient]] = [{I: one} for _ in range(n)]
    for index in range(site):
        factors[index] = frame["P"]
    factors[site] = frame[endpoint]
    return factors


def gq_add(left: GaussianQ, right: GaussianQ) -> GaussianQ:
    return left[0] + right[0], left[1] + right[1]


def gq_multiply(left: GaussianQ, right: GaussianQ) -> GaussianQ:
    return left[0] * right[0] - left[1] * right[1], left[0] * right[1] + left[1] * right[0]


def gq_phase(value: Fraction, exponent: int) -> GaussianQ:
    return (
        (value, Fraction(0)),
        (Fraction(0), value),
        (-value, Fraction(0)),
        (Fraction(0), -value),
    )[exponent % 4]


def multiply_local_rational(left: RationalAxis, right: RationalAxis) -> dict[int, GaussianQ]:
    output: dict[int, GaussianQ] = {}
    for left_code, left_coefficient in left.items():
        for right_code, right_coefficient in right.items():
            exponent, key = pauli_product(code_key(left_code, 0), code_key(right_code, 0))
            code = local_code(key, 0)
            term = gq_phase(left_coefficient * right_coefficient, exponent)
            output[code] = gq_add(output.get(code, (Fraction(0), Fraction(0))), term)
    return {code: value for code, value in output.items() if value != (0, 0)}


def expand_rational_factors(factors: list[RationalAxis], n: int) -> Operator:
    partial: dict[PauliKey, Fraction] = {(0, 0): Fraction(1)}
    for site, axis in enumerate(factors):
        updated: dict[PauliKey, Fraction] = {}
        for key, coefficient in partial.items():
            for code, local_coefficient in axis.items():
                local = code_key(code, site)
                output = key[0] | local[0], key[1] | local[1]
                updated[output] = updated.get(output, Fraction(0)) + coefficient * local_coefficient
        partial = updated
    return primitive(partial, n)


def bilinear_from_majoranas_rational(
    left: list[RationalAxis], right: list[RationalAxis], n: int
) -> Operator:
    local_products = [multiply_local_rational(a, b) for a, b in zip(left, right)]
    partial: dict[PauliKey, GaussianQ] = {(0, 0): (Fraction(1), Fraction(0))}
    for site, local_product in enumerate(local_products):
        updated: dict[PauliKey, GaussianQ] = {}
        for key, coefficient in partial.items():
            for code, local_coefficient in local_product.items():
                local = code_key(code, site)
                output = key[0] | local[0], key[1] | local[1]
                term = gq_multiply(coefficient, local_coefficient)
                updated[output] = gq_add(updated.get(output, (Fraction(0), Fraction(0))), term)
        partial = updated
    real: dict[PauliKey, Fraction] = {}
    for key, coefficient in partial.items():
        multiplied_by_i = (-coefficient[1], coefficient[0])
        if multiplied_by_i[1] != 0:
            raise AssertionError("i*gamma_a*gamma_b was not Hermitian-real")
        if multiplied_by_i[0]:
            real[key] = multiplied_by_i[0]
    return primitive(real, n)


@cache
def rational_pool(
    n: int, c_value: Fraction, s_value: Fraction
) -> tuple[tuple[str, Operator], ...]:
    frame = rational_frame(c_value, s_value)
    labels = [(site, endpoint) for site in range(n) for endpoint in ("Q", "R")]
    factors = {
        label: gamma_factors(n, frame, label[0], label[1], Fraction(1))
        for label in labels
    }
    entries = [
        (f"gamma:{site}:{endpoint}", expand_rational_factors(factors[(site, endpoint)], n))
        for site, endpoint in labels
    ]
    for left_index, (left_site, left_endpoint) in enumerate(labels):
        for right_site, right_endpoint in labels[left_index + 1 :]:
            entries.append(
                (
                    f"bilinear:{left_site}:{left_endpoint}:{right_site}:{right_endpoint}",
                    bilinear_from_majoranas_rational(
                        factors[(left_site, left_endpoint)],
                        factors[(right_site, right_endpoint)],
                        n,
                    ),
                )
            )
    parity_factors = [frame["P"] for _ in range(n)]
    entries.append(("parity", expand_rational_factors(parity_factors, n)))
    return tuple(entries)


def hamiltonian(n: int, coupling: Fraction) -> Operator:
    terms: dict[PauliKey, Fraction] = {}
    for site in range(n):
        terms[code_key(X, site)] = Fraction(-1)
        terms[code_key(Z, site)] = Fraction(3, 4)
    for site in range(n - 1):
        key = (0, (1 << site) | (1 << (site + 1)))
        terms[key] = terms.get(key, Fraction(0)) + coupling
    return primitive(terms, n)


def anticommutes(left: PauliKey, right: PauliKey) -> bool:
    return (
        ((left[0] & right[1]).bit_count() + (left[1] & right[0]).bit_count()) % 2
        == 1
    )


def commutator(h_value: Operator, candidate: Operator, n: int) -> Operator:
    output: dict[PauliKey, Fraction] = {}
    for h_key, h_coefficient in h_value.items():
        for candidate_key, candidate_coefficient in candidate.items():
            if not anticommutes(h_key, candidate_key):
                continue
            exponent, output_key = pauli_product(h_key, candidate_key)
            if exponent not in (1, 3):
                raise AssertionError("anticommuting product has non-imaginary phase")
            sign = 1 if exponent == 1 else -1
            output[output_key] = output.get(output_key, Fraction(0)) + h_coefficient * candidate_coefficient * sign
    return primitive(output, n)


def sparse_rank(columns: list[dict[int, int]], prime: int) -> int:
    pivots: dict[int, dict[int, int]] = {}
    for column in columns:
        vector = {row: coefficient % prime for row, coefficient in column.items() if coefficient % prime}
        while vector:
            pivot = min(vector)
            if pivot not in pivots:
                inverse = pow(vector[pivot], prime - 2, prime)
                pivots[pivot] = {
                    row: coefficient * inverse % prime
                    for row, coefficient in vector.items()
                    if coefficient * inverse % prime
                }
                break
            factor = vector[pivot]
            for row, coefficient in pivots[pivot].items():
                updated = (vector.get(row, 0) - factor * coefficient) % prime
                if updated:
                    vector[row] = updated
                else:
                    vector.pop(row, None)
    return len(pivots)


def operator_rank(operators: list[Operator], n: int, prime: int) -> int:
    words = sorted({key_word(key, n) for operator in operators for key in operator})
    index = {word: row for row, word in enumerate(words)}
    columns = [
        {index[key_word(key, n)]: coefficient for key, coefficient in operator.items()}
        for operator in operators
    ]
    return sparse_rank(columns, prime)


def operator_in_span(operator: Operator, basis: list[Operator], n: int) -> bool:
    return operator_rank(basis + [operator], n, AUDIT_PRIME) == len(basis)


def rational_catalog() -> list[dict[str, str]]:
    points: set[tuple[Fraction, Fraction]] = set()
    for u_value in range(-GRID_BOUND, GRID_BOUND + 1):
        for v_value in range(-GRID_BOUND, GRID_BOUND + 1):
            if (u_value, v_value) == (0, 0):
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
        {"frame_id": f"pay_{index:03d}", "c": fraction_text(c), "s": fraction_text(s)}
        for index, (c, s) in enumerate(sorted(points))
    ]


def projective_catalog_count(catalog: list[dict[str, str]]) -> int:
    representatives: set[tuple[Fraction, Fraction]] = set()
    for entry in catalog:
        point = Fraction(entry["c"]), Fraction(entry["s"])
        representatives.add(min(point, (-point[0], -point[1])))
    return len(representatives)


def grid_key(coupling: Fraction, n: int, frame: dict[str, str]) -> tuple[str, int, str, str, str]:
    return fraction_text(coupling), n, frame["frame_id"], frame["c"], frame["s"]


def expected_grid_keys(catalog: list[dict[str, str]]) -> list[tuple[str, int, str, str, str]]:
    return [
        grid_key(coupling, n, frame)
        for coupling in FROZEN_COUPLINGS
        for n in GRID_SIZES
        for frame in catalog
    ]


def rational_row(n: int, coupling: Fraction, frame_entry: dict[str, str]) -> dict[str, Any]:
    entries = rational_pool(n, Fraction(frame_entry["c"]), Fraction(frame_entry["s"]))
    labels = [label for label, _ in entries]
    operators = [operator for _, operator in entries]
    h_value = hamiltonian(n, coupling)
    raw_columns = [commutator(h_value, operator, n) for operator in operators]
    output_words = sorted({key_word(key, n) for column in raw_columns for key in column})
    output_index = {word: row for row, word in enumerate(output_words)}
    columns = [
        {output_index[key_word(key, n)]: coefficient for key, coefficient in column.items()}
        for column in raw_columns
    ]
    operator_payload = {
        "labels": labels,
        "operators": [
            sorted((key_word(key, n), coefficient) for key, coefficient in operator.items())
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
    operator_rank_value = operator_rank(operators, n, AUDIT_PRIME)
    commutator_rank_value = sparse_rank(columns, AUDIT_PRIME)
    column_count = len(columns)
    rebuilt: dict[str, Any] = {
        "frame_id": frame_entry["frame_id"],
        "c": frame_entry["c"],
        "s": frame_entry["s"],
        "coupling": fraction_text(coupling),
        "n": n,
        "candidate_column_count": column_count,
        "operator_basis_pauli_nonzero_count": sum(len(operator) for operator in operators),
        "operator_basis_sha256": canonical_hash(operator_payload),
        "output_basis_size": len(output_words),
        "commutator_nonzero_count": sum(len(column) for column in columns),
        "commutator_matrix_sha256": canonical_hash(matrix_payload),
        "third_prime_operator_rank": operator_rank_value,
        "third_prime_commutator_rank": commutator_rank_value,
        "third_prime_nullity": column_count - commutator_rank_value,
    }
    if coupling == 0 and Fraction(frame_entry["c"]) == 1 and Fraction(frame_entry["s"]) == 0:
        witnesses = [
            expand_rational_factors(
                [{I: Fraction(1)} if index != site else AXIS_A for index in range(n)], n
            )
            for site in range(n)
        ]
        rebuilt.update(
            {
                "onsite_axis_a_witness_count": len(witnesses),
                "onsite_axis_a_commutes_count": sum(not commutator(h_value, witness, n) for witness in witnesses),
                "onsite_axis_a_in_span_count": sum(operator_in_span(witness, operators, n) for witness in witnesses),
            }
        )
    return rebuilt


def gp_add(left: GaussianP, right: GaussianP) -> GaussianP:
    return sp.expand(left[0] + right[0]), sp.expand(left[1] + right[1])


def gp_multiply(left: GaussianP, right: GaussianP) -> GaussianP:
    return (
        sp.expand(left[0] * right[0] - left[1] * right[1]),
        sp.expand(left[0] * right[1] + left[1] * right[0]),
    )


def gp_phase(value: sp.Expr, exponent: int) -> GaussianP:
    return (
        (value, sp.Integer(0)),
        (sp.Integer(0), value),
        (-value, sp.Integer(0)),
        (sp.Integer(0), -value),
    )[exponent % 4]


def polynomial_frame() -> dict[str, PolynomialAxis]:
    c_numerator = 1 - T * T
    s_numerator = 2 * T
    return {
        "P": {X: -4 * c_numerator, Y: 5 * s_numerator, Z: 3 * c_numerator},
        "Q": {X: 4 * s_numerator, Y: 5 * c_numerator, Z: -3 * s_numerator},
        "R": {X: -3 * D, Z: -4 * D},
    }


def multiply_local_polynomial(left: PolynomialAxis, right: PolynomialAxis) -> dict[int, GaussianP]:
    output: dict[int, GaussianP] = {}
    for left_code, left_coefficient in left.items():
        for right_code, right_coefficient in right.items():
            exponent, key = pauli_product(code_key(left_code, 0), code_key(right_code, 0))
            code = local_code(key, 0)
            term = gp_phase(sp.expand(left_coefficient * right_coefficient), exponent)
            output[code] = gp_add(output.get(code, (sp.Integer(0), sp.Integer(0))), term)
    return {
        code: value
        for code, value in output.items()
        if sp.expand(value[0]) != 0 or sp.expand(value[1]) != 0
    }


def expand_polynomial_factors(factors: list[PolynomialAxis], n: int) -> PolynomialOperator:
    partial: dict[PauliKey, sp.Expr] = {(0, 0): sp.Integer(1)}
    for site, axis in enumerate(factors):
        updated: dict[PauliKey, sp.Expr] = {}
        for key, coefficient in partial.items():
            for code, local_coefficient in axis.items():
                local = code_key(code, site)
                output = key[0] | local[0], key[1] | local[1]
                updated[output] = sp.expand(updated.get(output, 0) + coefficient * local_coefficient)
        partial = updated
    return {
        key: sp.Poly(coefficient, T, domain=sp.ZZ)
        for key, coefficient in partial.items()
        if coefficient != 0
    }


def bilinear_from_majoranas_polynomial(
    left: list[PolynomialAxis],
    right: list[PolynomialAxis],
    left_site: int,
    n: int,
) -> PolynomialOperator:
    local_products = [multiply_local_polynomial(a, b) for a, b in zip(left, right)]
    partial: dict[PauliKey, GaussianP] = {(0, 0): (sp.Integer(1), sp.Integer(0))}
    for site, local_product in enumerate(local_products):
        updated: dict[PauliKey, GaussianP] = {}
        for key, coefficient in partial.items():
            for code, local_coefficient in local_product.items():
                local = code_key(code, site)
                output = key[0] | local[0], key[1] | local[1]
                term = gp_multiply(coefficient, local_coefficient)
                updated[output] = gp_add(updated.get(output, (sp.Integer(0), sp.Integer(0))), term)
        partial = updated
    normalization = sp.Poly((5 * D) ** (2 * left_site + 1), T, domain=sp.ZZ)
    output: PolynomialOperator = {}
    for key, coefficient in partial.items():
        real_after_i = sp.expand(-coefficient[1])
        imaginary_after_i = sp.expand(coefficient[0])
        if imaginary_after_i != 0:
            raise AssertionError("symbolic i*gamma_a*gamma_b was not Hermitian-real")
        quotient, remainder = sp.div(sp.Poly(real_after_i, T, domain=sp.ZZ), normalization)
        if not remainder.is_zero:
            raise AssertionError("Majorana normalization did not divide exactly")
        if not quotient.is_zero:
            output[key] = sp.Poly(quotient, T, domain=sp.ZZ)
    return output


def polynomial_pool(n: int) -> list[tuple[str, PolynomialOperator]]:
    frame = polynomial_frame()
    labels = [(site, endpoint) for site in range(n) for endpoint in ("Q", "R")]
    factors = {
        label: gamma_factors(n, frame, label[0], label[1], sp.Integer(1))
        for label in labels
    }
    entries = [
        (f"gamma:{site}:{endpoint}", expand_polynomial_factors(factors[(site, endpoint)], n))
        for site, endpoint in labels
    ]
    for left_index, (left_site, left_endpoint) in enumerate(labels):
        for right_site, right_endpoint in labels[left_index + 1 :]:
            entries.append(
                (
                    f"bilinear:{left_site}:{left_endpoint}:{right_site}:{right_endpoint}",
                    bilinear_from_majoranas_polynomial(
                        factors[(left_site, left_endpoint)],
                        factors[(right_site, right_endpoint)],
                        left_site,
                        n,
                    ),
                )
            )
    entries.append(("parity", expand_polynomial_factors([frame["P"] for _ in range(n)], n)))
    return entries


def commutator_polynomial(
    h_value: Operator, candidate: PolynomialOperator
) -> PolynomialOperator:
    output: dict[PauliKey, sp.Poly] = {}
    zero = sp.Poly(0, T, domain=sp.ZZ)
    for h_key, h_coefficient in h_value.items():
        for candidate_key, candidate_coefficient in candidate.items():
            if not anticommutes(h_key, candidate_key):
                continue
            exponent, output_key = pauli_product(h_key, candidate_key)
            if exponent not in (1, 3):
                raise AssertionError("invalid polynomial commutator phase")
            sign = 1 if exponent == 1 else -1
            output[output_key] = output.get(output_key, zero) + candidate_coefficient * (h_coefficient * sign)
    return {
        key: sp.Poly(coefficient, T, domain=sp.ZZ)
        for key, coefficient in output.items()
        if not coefficient.is_zero
    }


def polynomial_coefficients(poly: sp.Poly) -> list[str]:
    return [str(int(coefficient)) for coefficient in poly.all_coeffs()]


def symbolic_matrix(
    n: int, coupling: Fraction
) -> tuple[list[str], list[PolynomialOperator], list[str], str]:
    entries = polynomial_pool(n)
    labels = [label for label, _ in entries]
    columns = [commutator_polynomial(hamiltonian(n, coupling), operator) for _, operator in entries]
    output_words = sorted({key_word(key, n) for column in columns for key in column})
    triples = [
        (key_word(key, n), column_index, polynomial_coefficients(coefficient))
        for column_index, column in enumerate(columns)
        for key, coefficient in sorted(column.items(), key=lambda item: key_word(item[0], n))
    ]
    matrix_hash = canonical_hash({"labels": labels, "output_words": output_words, "triples": triples})
    return labels, columns, output_words, matrix_hash


def polynomial_at_word(column: PolynomialOperator, word: str, n: int) -> sp.Poly:
    for key, coefficient in column.items():
        if key_word(key, n) == word:
            return coefficient
    return sp.Poly(0, T, domain=sp.ZZ)


def select_rows_at_anchor(
    columns: list[PolynomialOperator],
    output_words: list[str],
    n: int,
    anchor: int,
    selection_prime: int,
) -> list[str]:
    pivots: dict[int, dict[int, int]] = {}
    selected: list[str] = []
    for word in output_words:
        vector = {
            column_index: int(polynomial_at_word(column, word, n).eval(anchor))
            % selection_prime
            for column_index, column in enumerate(columns)
        }
        vector = {index: value for index, value in vector.items() if value}
        while vector:
            pivot = min(vector)
            if pivot not in pivots:
                inverse = pow(vector[pivot], selection_prime - 2, selection_prime)
                pivots[pivot] = {
                    index: value * inverse % selection_prime
                    for index, value in vector.items()
                    if value * inverse % selection_prime
                }
                selected.append(word)
                break
            factor = vector[pivot]
            for index, value in pivots[pivot].items():
                updated = (
                    vector.get(index, 0) - factor * value
                ) % selection_prime
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
    left: sp.Poly, right: sp.Poly, factor: sp.Poly
) -> sp.Poly:
    return field_reduce(left * right, factor)


def select_rows_over_factor(
    columns: list[PolynomialOperator],
    output_words: list[str],
    n: int,
    factor: sp.Poly,
) -> list[str]:
    factor = sp.Poly(factor, T, domain=sp.QQ)
    zero = sp.Poly(0, T, domain=sp.QQ)
    pivots: dict[int, dict[int, sp.Poly]] = {}
    selected: list[str] = []
    for word in output_words:
        vector = {
            column_index: field_reduce(
                polynomial_at_word(column, word, n), factor
            )
            for column_index, column in enumerate(columns)
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
                    vector.get(index, zero)
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


def normalized_primitive(poly: sp.Poly) -> tuple[int, sp.Poly]:
    content, primitive_poly = sp.polys.polytools.primitive(sp.Poly(poly, T, domain=sp.ZZ))
    primitive_poly = sp.Poly(primitive_poly, T, domain=sp.ZZ)
    if primitive_poly.LC() < 0:
        primitive_poly = -primitive_poly
        content = -content
    return int(content), primitive_poly


def determinant_record(
    columns: list[PolynomialOperator], row_words: list[str], n: int, source: dict[str, Any]
) -> tuple[dict[str, Any], sp.Poly]:
    matrix = sp.Matrix(
        [
            [polynomial_at_word(column, word, n).as_expr() for column in columns]
            for word in row_words
        ]
    )
    raw = sp.Poly(matrix.det(method="domain-ge"), T, domain=sp.ZZ)
    content, primitive_poly = normalized_primitive(raw)
    coefficients = polynomial_coefficients(primitive_poly)
    return (
        {
            "source": source,
            "row_count": len(row_words),
            "row_words_sha256": canonical_hash(row_words),
            "degree": primitive_poly.degree(),
            "term_count": len(primitive_poly.terms()),
            "content_abs_bit_length": abs(content).bit_length(),
            "primitive_max_coefficient_bit_length": max(
                abs(int(coefficient)).bit_length() for coefficient in primitive_poly.all_coeffs()
            ),
            "primitive_determinant_sha256": canonical_hash(
                {"row_words": row_words, "primitive_coefficients": coefficients}
            ),
        },
        primitive_poly,
    )


def pq_trim(poly: PolyQ) -> PolyQ:
    output = list(poly)
    while output and output[-1] == 0:
        output.pop()
    return output


def pq_derivative(poly: PolyQ) -> PolyQ:
    return pq_trim([Fraction(index) * coefficient for index, coefficient in enumerate(poly[1:], 1)])


def pq_divmod(numerator: PolyQ, denominator: PolyQ) -> tuple[PolyQ, PolyQ]:
    numerator = pq_trim(numerator)
    denominator = pq_trim(denominator)
    if not denominator:
        raise ZeroDivisionError("polynomial division by zero")
    quotient = [Fraction(0)] * max(1, len(numerator) - len(denominator) + 1)
    remainder = list(numerator)
    while remainder and len(remainder) >= len(denominator):
        shift = len(remainder) - len(denominator)
        factor = remainder[-1] / denominator[-1]
        quotient[shift] += factor
        for index, coefficient in enumerate(denominator):
            remainder[index + shift] -= factor * coefficient
        remainder = pq_trim(remainder)
    return pq_trim(quotient), remainder


def pq_monic(poly: PolyQ) -> PolyQ:
    poly = pq_trim(poly)
    if not poly:
        return []
    lead = poly[-1]
    return [coefficient / lead for coefficient in poly]


def pq_positive_normalize(poly: PolyQ) -> PolyQ:
    """Normalize without changing a Sturm polynomial's sign."""

    poly = pq_trim(poly)
    if not poly:
        return []
    scale = abs(poly[-1])
    return [coefficient / scale for coefficient in poly]


def pq_gcd(left: PolyQ, right: PolyQ) -> PolyQ:
    left, right = pq_trim(left), pq_trim(right)
    while right:
        _, remainder = pq_divmod(left, right)
        left, right = right, remainder
    return pq_monic(left)


def sp_to_pq(poly: sp.Poly) -> PolyQ:
    degree = poly.degree()
    if degree < 0:
        return []
    return [Fraction(poly.nth(index)) for index in range(degree + 1)]


def sign_at_infinity(poly: PolyQ, positive: bool) -> int:
    poly = pq_trim(poly)
    if not poly:
        return 0
    sign = 1 if poly[-1] > 0 else -1
    if not positive and (len(poly) - 1) % 2:
        sign = -sign
    return sign


def sign_variations(signs: list[int]) -> int:
    nonzero = [sign for sign in signs if sign]
    return sum(left != right for left, right in zip(nonzero, nonzero[1:]))


def sturm_real_root_count(poly: sp.Poly) -> dict[str, Any]:
    rational = sp_to_pq(sp.Poly(poly, T, domain=sp.QQ))
    derivative = pq_derivative(rational)
    common = pq_gcd(rational, derivative)
    square_free, remainder = pq_divmod(rational, common)
    if remainder:
        raise AssertionError("square-free division left a remainder")
    sequence = [
        pq_positive_normalize(square_free),
        pq_positive_normalize(pq_derivative(square_free)),
    ]
    if not sequence[1]:
        count = 0
    else:
        while sequence[-1]:
            _, next_remainder = pq_divmod(sequence[-2], sequence[-1])
            if not next_remainder:
                break
            sequence.append(
                pq_positive_normalize(
                    [-coefficient for coefficient in next_remainder]
                )
            )
        negative = sign_variations([sign_at_infinity(item, False) for item in sequence])
        positive = sign_variations([sign_at_infinity(item, True) for item in sequence])
        count = negative - positive
    sympy_count = int(
        sp.polys.polytools.count_roots(
            sp.Poly(poly, T, domain=sp.QQ), -sp.oo, sp.oo
        )
    )
    return {
        "primary_method": "in_file_fraction_sturm_sequence",
        "real_root_count": count,
        "sequence_length": len(sequence),
        "sympy_secondary_count": sympy_count,
        "secondary_agrees": count == sympy_count,
    }


def sturm_regression_oracle() -> dict[str, Any]:
    cases = (
        ("t^2+1", T**2 + 1, 0),
        ("t^3+t+1", T**3 + T + 1, 1),
        ("t^4+t+1", T**4 + T + 1, 0),
        ("(t-1)^2", (T - 1) ** 2, 1),
        ("t^3-t", T**3 - T, 3),
    )
    rows: list[dict[str, Any]] = []
    for label, expression, expected in cases:
        result = sturm_real_root_count(
            sp.Poly(expression, T, domain=sp.QQ)
        )
        rows.append(
            {
                "polynomial": label,
                "expected_real_root_count": expected,
                "observed_real_root_count": result["real_root_count"],
                "secondary_agrees": result["secondary_agrees"],
                "passed": bool(
                    result["real_root_count"] == expected
                    and result["secondary_agrees"]
                ),
            }
        )
    return {
        "case_count": len(rows),
        "pass_count": sum(row["passed"] for row in rows),
        "cases": rows,
        "checked": all(row["passed"] for row in rows),
    }


def factor_records(poly: sp.Poly) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for factor, exponent in sp.factor_list(poly)[1]:
        _, primitive_factor = normalized_primitive(sp.Poly(factor, T, domain=sp.ZZ))
        coefficients = polynomial_coefficients(primitive_factor)
        sturm = sturm_real_root_count(primitive_factor)
        records.append(
            {
                "degree": primitive_factor.degree(),
                "exponent": int(exponent),
                "coefficients": coefficients,
                "factor_sha256": canonical_hash(coefficients),
                "real_root_count": sturm["real_root_count"],
            }
        )
    return records


def prescribed_column_degree(label: str, n: int) -> int:
    if label == "parity":
        return 2 * n
    parts = label.split(":")
    if parts[0] == "gamma":
        return 2 * (int(parts[1]) + 1)
    if parts[0] == "bilinear":
        return 2 * (int(parts[3]) - int(parts[1]) + 1)
    raise ValueError(f"unknown candidate label: {label}")


def leading_coefficient_infinity_rank(
    columns: list[PolynomialOperator],
    labels: list[str],
    output_words: list[str],
    n: int,
    coupling: Fraction,
) -> dict[str, Any]:
    word_index = {word: index for index, word in enumerate(output_words)}
    leading_columns: list[dict[int, int]] = []
    prescribed_degrees: list[int] = []
    actual_degrees: list[int] = []
    triples: list[tuple[str, int, int]] = []
    leading_word_columns: list[dict[str, int]] = []
    for column_index, (label, column) in enumerate(zip(labels, columns)):
        prescribed_degree = prescribed_column_degree(label, n)
        actual_degree = max(
            (coefficient.degree() for coefficient in column.values()),
            default=-1,
        )
        prescribed_degrees.append(prescribed_degree)
        actual_degrees.append(actual_degree)
        leading: dict[int, int] = {}
        leading_words: dict[str, int] = {}
        for key, coefficient in column.items():
            value = int(coefficient.nth(prescribed_degree))
            if value:
                word = key_word(key, n)
                leading[word_index[word]] = value
                leading_words[word] = value
                triples.append((word, column_index, value))
        leading_columns.append(leading)
        leading_word_columns.append(leading_words)

    explicit_entries = rational_pool(n, Fraction(-1), Fraction(0))
    explicit_labels = [label for label, _ in explicit_entries]
    explicit_hamiltonian = hamiltonian(n, coupling)
    explicit_columns = [
        {
            key_word(key, n): coefficient
            for key, coefficient in commutator(
                explicit_hamiltonian, operator, n
            ).items()
        }
        for _, operator in explicit_entries
    ]
    proportional_rows: list[dict[str, Any]] = []
    for label, leading, explicit in zip(
        labels, leading_word_columns, explicit_columns
    ):
        words = sorted(set(leading) | set(explicit))
        pivot = next(
            (
                word
                for word in words
                if explicit.get(word, 0) % AUDIT_PRIME
            ),
            None,
        )
        if pivot is None:
            scale = 0
            proportional = False
        else:
            scale = (
                leading.get(pivot, 0)
                * pow(
                    explicit[pivot] % AUDIT_PRIME,
                    AUDIT_PRIME - 2,
                    AUDIT_PRIME,
                )
            ) % AUDIT_PRIME
            proportional = bool(
                scale
                and all(
                    (
                        leading.get(word, 0)
                        - scale * explicit.get(word, 0)
                    )
                    % AUDIT_PRIME
                    == 0
                    for word in words
                )
            )
        proportional_rows.append(
            {
                "label": label,
                "scale_mod_prime": scale,
                "passed": proportional,
            }
        )

    rank = sparse_rank(leading_columns, AUDIT_PRIME)
    return {
        "route": "prescribed_degree_homogenized_leading_coefficients",
        "prescribed_column_degrees": prescribed_degrees,
        "actual_column_degrees": actual_degrees,
        "prescribed_degree_match_count": sum(
            actual == prescribed
            for actual, prescribed in zip(
                actual_degrees, prescribed_degrees
            )
        ),
        "explicit_labels_match": explicit_labels == labels,
        "explicit_proportional_column_count": sum(
            row["passed"] for row in proportional_rows
        ),
        "explicit_proportional_columns": proportional_rows,
        "leading_matrix_sha256": canonical_hash(triples),
        "third_prime_rank": rank,
        "column_count": len(columns),
        "full_column_rank": bool(
            rank == len(columns)
            and explicit_labels == labels
            and all(
                actual == prescribed
                for actual, prescribed in zip(
                    actual_degrees, prescribed_degrees
                )
            )
            and all(row["passed"] for row in proportional_rows)
        ),
    }


def continuous_rebuild(n: int, coupling: Fraction) -> dict[str, Any]:
    labels, columns, output_words, matrix_hash = symbolic_matrix(n, coupling)
    determinant_cache: dict[
        tuple[str, ...], tuple[dict[str, Any], sp.Poly]
    ] = {}

    def cached_determinant(
        row_words: list[str], source: dict[str, Any]
    ) -> tuple[dict[str, Any], sp.Poly]:
        key = tuple(row_words)
        if key not in determinant_cache:
            record, determinant = determinant_record(
                columns, row_words, n, source
            )
            determinant_cache[key] = (
                {
                    field: value
                    for field, value in record.items()
                    if field != "source"
                },
                determinant,
            )
        cached_record, determinant = determinant_cache[key]
        return {"source": source, **cached_record}, determinant

    source_records: list[dict[str, Any]] = []
    source_polys: list[sp.Poly] = []
    for anchor in SOURCE_ANCHORS:
        rows = select_rows_at_anchor(
            columns, output_words, n, anchor, BASIS_PRIME
        )
        record, determinant = cached_determinant(
            rows,
            {"type": "integer_anchor", "anchor": anchor, "selection_prime": BASIS_PRIME},
        )
        source_records.append(record)
        source_polys.append(determinant)
    audit_records: list[dict[str, Any]] = []
    audit_adaptive_records: list[dict[str, Any]] = []
    audit_polys: list[sp.Poly] = []
    for anchor in AUDIT_ANCHORS:
        rows = select_rows_at_anchor(
            columns, output_words, n, anchor, AUDIT_PRIME
        )
        record, determinant = cached_determinant(
            rows,
            {
                "type": "audit_owned_integer_anchor",
                "anchor": anchor,
                "selection_prime": AUDIT_PRIME,
            },
        )
        audit_records.append(record)
        audit_polys.append(determinant)

    audit_unresolved_factors: list[dict[str, Any]] = []
    audit_adaptive_round_count = 0
    while audit_adaptive_round_count < MAX_ADAPTIVE_ROUNDS:
        audit_gcd = audit_polys[0]
        for determinant in audit_polys[1:]:
            audit_gcd = sp.gcd(audit_gcd, determinant)
        _, audit_gcd = normalized_primitive(audit_gcd)
        real_factors = [
            item
            for item in factor_records(audit_gcd)
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
        rows = select_rows_over_factor(
            columns, output_words, n, factor
        )
        if len(rows) != len(columns):
            audit_unresolved_factors.append(
                {
                    **factor_record,
                    "quotient_field_rank": len(rows),
                    "candidate_column_count": len(columns),
                }
            )
            break
        record, determinant = cached_determinant(
            rows,
            {
                "type": "audit_owned_quotient_field_factor",
                "factor_sha256": factor_record["factor_sha256"],
                "factor_degree": factor_record["degree"],
                "factor_real_root_count": factor_record[
                    "real_root_count"
                ],
            },
        )
        audit_adaptive_records.append(record)
        audit_polys.append(determinant)
        audit_adaptive_round_count += 1

    source_gcd = source_polys[0]
    for determinant in source_polys[1:]:
        source_gcd = sp.gcd(source_gcd, determinant)
    _, source_gcd = normalized_primitive(source_gcd)
    audit_gcd = audit_polys[0]
    for determinant in audit_polys[1:]:
        audit_gcd = sp.gcd(audit_gcd, determinant)
    _, audit_gcd = normalized_primitive(audit_gcd)
    source_sturm = sturm_real_root_count(source_gcd)
    audit_sturm = sturm_real_root_count(audit_gcd)
    explicit_infinity = rational_row(
        n, coupling, {"frame_id": "projective_infinity", "c": "-1", "s": "0"}
    )
    homogenized_infinity = leading_coefficient_infinity_rank(
        columns, labels, output_words, n, coupling
    )
    result = {
        "coupling": fraction_text(coupling),
        "n": n,
        "candidate_column_count": len(columns),
        "candidate_labels_sha256": canonical_hash(labels),
        "output_basis_size": len(output_words),
        "polynomial_commutator_nonzero_count": sum(len(column) for column in columns),
        "polynomial_commutator_matrix_sha256": matrix_hash,
        "source_anchor_determinants": source_records,
        "audit_owned_anchor_determinants": audit_records,
        "audit_owned_adaptive_determinants": audit_adaptive_records,
        "audit_owned_adaptive_round_count": audit_adaptive_round_count,
        "audit_owned_unresolved_factors": audit_unresolved_factors,
        "unique_exact_determinant_count": len(determinant_cache),
        "source_anchor_gcd_degree": source_gcd.degree(),
        "source_anchor_gcd_sha256": canonical_hash(polynomial_coefficients(source_gcd)),
        "source_anchor_factorization": factor_records(source_gcd),
        "source_anchor_sturm": source_sturm,
        "audit_anchor_gcd_degree": audit_gcd.degree(),
        "audit_anchor_gcd_sha256": canonical_hash(polynomial_coefficients(audit_gcd)),
        "audit_anchor_sturm": audit_sturm,
        "explicit_projective_infinity": explicit_infinity,
        "homogenized_projective_infinity": homogenized_infinity,
    }
    del columns
    gc.collect()
    return result


def compare_rational(source: dict[str, Any], rebuilt: dict[str, Any], row_id: str) -> list[str]:
    errors: list[str] = []
    for field in (
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
    ):
        if source.get(field) != rebuilt.get(field):
            errors.append(f"{row_id}: {field} mismatch")
    if rebuilt["third_prime_operator_rank"] != rebuilt["candidate_column_count"]:
        errors.append(f"{row_id}: third-prime operator rank deficient")
    expected_commutator_rank = 42 if rebuilt["coupling"] == "0" else rebuilt["candidate_column_count"]
    if rebuilt["third_prime_commutator_rank"] != expected_commutator_rank:
        errors.append(f"{row_id}: third-prime commutator rank mismatch")
    return errors


def compare_continuous(source: dict[str, Any], rebuilt: dict[str, Any]) -> list[str]:
    row_id = f"continuous J={rebuilt['coupling']},n={rebuilt['n']}"
    errors: list[str] = []
    field_map = {
        "coupling": "coupling",
        "n": "n",
        "candidate_column_count": "candidate_column_count",
        "candidate_labels_sha256": "candidate_labels_sha256",
        "output_basis_size": "output_basis_size",
        "polynomial_commutator_nonzero_count": "polynomial_commutator_nonzero_count",
        "polynomial_commutator_matrix_sha256": "polynomial_commutator_matrix_sha256",
        "final_primitive_gcd_degree": "source_anchor_gcd_degree",
        "final_primitive_gcd_sha256": "source_anchor_gcd_sha256",
        "final_factorization": "source_anchor_factorization",
        "finite_real_common_root_count": None,
    }
    for source_field, rebuilt_field in field_map.items():
        rebuilt_value = (
            rebuilt["source_anchor_sturm"]["real_root_count"]
            if rebuilt_field is None
            else rebuilt[rebuilt_field]
        )
        if source.get(source_field) != rebuilt_value:
            errors.append(f"{row_id}: {source_field} mismatch")
    normalized_source_determinants = [
        {
            key: value
            for key, value in record.items()
            if key != "elapsed_seconds"
        }
        for record in source.get("determinants", [])
    ]
    if normalized_source_determinants != rebuilt[
        "source_anchor_determinants"
    ]:
        errors.append(f"{row_id}: source-anchor determinant records mismatch")
    errors.extend(
        compare_rational(
            source["projective_infinity"],
            rebuilt["explicit_projective_infinity"],
            f"{row_id}: explicit infinity",
        )
    )
    if not rebuilt["source_anchor_sturm"]["secondary_agrees"]:
        errors.append(f"{row_id}: source-anchor Sturm/SymPy disagreement")
    if rebuilt["audit_anchor_sturm"]["real_root_count"] != 0:
        errors.append(f"{row_id}: audit-owned anchors retain a finite real common root")
    if rebuilt["audit_owned_unresolved_factors"]:
        errors.append(f"{row_id}: audit-owned quotient-field factor remains unresolved")
    if not rebuilt["audit_anchor_sturm"]["secondary_agrees"]:
        errors.append(f"{row_id}: audit-anchor Sturm/SymPy disagreement")
    if not rebuilt["homogenized_projective_infinity"]["full_column_rank"]:
        errors.append(f"{row_id}: homogenized infinity rank deficient")
    if rebuilt["homogenized_projective_infinity"]["third_prime_rank"] != rebuilt[
        "explicit_projective_infinity"
    ]["third_prime_commutator_rank"]:
        errors.append(f"{row_id}: explicit and homogenized infinity ranks disagree")
    return errors


def ast_anti_circularity() -> dict[str, Any]:
    tree = ast.parse(Path(__file__).read_text())
    imports: list[str] = []
    forbidden_imports: list[str] = []
    forbidden_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)
            imports.extend(
                f"{module}.{alias.name}" if module else alias.name
                for alias in node.names
            )
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {
                "exec",
                "eval",
                "__import__",
                "compile",
            }:
                forbidden_calls.append(node.func.id)
            if isinstance(node.func, ast.Attribute) and node.func.attr in {
                "SourceFileLoader",
                "import_module",
                "exec_module",
                "run_module",
                "run_path",
            }:
                forbidden_calls.append(node.func.attr)
            if (
                isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
            ):
                command = node.args[0] if node.args else None
                allowed_git_call = bool(
                    node.func.attr == "run"
                    and isinstance(command, (ast.List, ast.Tuple))
                    and len(command.elts) >= 2
                    and isinstance(command.elts[0], ast.Constant)
                    and command.elts[0].value == "git"
                    and isinstance(command.elts[1], ast.Constant)
                    and command.elts[1].value in {"merge-base", "show"}
                )
                if not allowed_git_call:
                    forbidden_calls.append(
                        f"subprocess.{node.func.attr}"
                    )
    for name in imports:
        if (
            name == "runpy"
            or name.startswith("runpy.")
            or name == "importlib"
            or name.startswith("importlib.")
            or any(
                f"b9_r{number}" in name for number in range(193, 200)
            )
        ):
            forbidden_imports.append(name)
    return {
        "imported_modules": sorted(imports),
        "forbidden_imports": sorted(forbidden_imports),
        "forbidden_dynamic_calls": sorted(forbidden_calls),
        "source_fields_consumed_for_rebuild": list(
            SOURCE_FIELDS_CONSUMED_FOR_REBUILD
        ),
        "rebuild_functions_accept_source_artifacts": False,
        "checked": not forbidden_imports and not forbidden_calls,
    }


def verify_freeze(
    root: Path, source: dict[str, Any], contract: dict[str, Any]
) -> dict[str, Any]:
    commit = source["public_freeze"]["preregistration_commit"]
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=root, check=False
    ).returncode == 0
    frozen = subprocess.run(
        ["git", "show", f"{commit}:{CONTRACT_PATH}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    frozen_hash = sha256_bytes(frozen)
    working_hash = sha256_file(root / CONTRACT_PATH)
    source_code_files = {
        item["path"]: item
        for item in source["public_freeze"].get("code_files", [])
    }
    code_files: list[dict[str, Any]] = []
    for relative_path in contract["code_freeze"]["paths"]:
        frozen_file = subprocess.run(
            ["git", "show", f"{commit}:{relative_path}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        current_file = (root / relative_path).read_bytes()
        preregistration_sha256 = sha256_bytes(frozen_file)
        current_sha256 = sha256_bytes(current_file)
        source_record = source_code_files.get(relative_path, {})
        source_record_matches = bool(
            source_record.get("preregistration_sha256")
            == preregistration_sha256
            and source_record.get("current_sha256") == current_sha256
            and source_record.get("matches") is True
        )
        code_files.append(
            {
                "path": relative_path,
                "preregistration_sha256": preregistration_sha256,
                "current_sha256": current_sha256,
                "commit_bytes_match_worktree": frozen_file == current_file,
                "source_record_matches": source_record_matches,
                "verified": bool(
                    frozen_file == current_file and source_record_matches
                ),
            }
        )
    code_freeze_verified = bool(
        len(code_files) == len(contract["code_freeze"]["paths"])
        and all(item["verified"] for item in code_files)
    )
    return {
        "preregistration_commit": commit,
        "is_ancestor": ancestor,
        "contract_sha256_at_commit": frozen_hash,
        "working_contract_sha256": working_hash,
        "expected_contract_sha256": EXPECTED_CONTRACT_SHA256,
        "code_files": code_files,
        "code_freeze_verified": code_freeze_verified,
        "verified": bool(
            ancestor
            and frozen_hash == EXPECTED_CONTRACT_SHA256
            and working_hash == EXPECTED_CONTRACT_SHA256
            and code_freeze_verified
        ),
    }


def build_audit(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    phase_oracle = one_qubit_phase_oracle()
    sturm_oracle = sturm_regression_oracle()
    anti_circularity = ast_anti_circularity()

    # These objects are intentionally complete before the source result is read.
    catalog = rational_catalog()
    expected_keys = expected_grid_keys(catalog)
    expected_counter = Counter(expected_keys)
    pre_source_generation = {
        "catalog_generated_before_source_read": True,
        "expected_grid_generated_before_source_read": True,
        "catalog_count": len(catalog),
        "projective_catalog_count": projective_catalog_count(catalog),
        "catalog_sha256": canonical_hash(catalog),
        "expected_grid_key_count": len(expected_keys),
        "expected_unique_grid_key_count": len(expected_counter),
    }

    source = json.loads((root / RESULT_PATH).read_text())
    contract = json.loads((root / CONTRACT_PATH).read_text())
    freeze = verify_freeze(root, source, contract)

    source_payload = dict(source)
    recorded_payload_hash = source_payload.pop("payload_sha256")
    payload_for_replay = json.loads(json.dumps(source_payload))
    payload_normalizations: list[str] = []
    for item in payload_for_replay.get("requirements", []):
        if item.get("requirement_id") == "P6":
            expected_counts = item["evidence"].get(
                "expected_column_counts", {}
            )
            item["evidence"]["expected_column_counts"] = {
                int(key): value
                for key, value in expected_counts.items()
            }
            payload_normalizations.append(
                "P6.expected_column_counts:string_keys_to_int_keys"
            )
    recomputed_payload_hash = canonical_hash(payload_for_replay)
    if recomputed_payload_hash != recorded_payload_hash:
        errors.append("source payload hash mismatch")
    if canonical_hash(source.get("protocol")) != source.get("protocol_hash"):
        errors.append("source protocol hash mismatch")
    if len(catalog) != 72 or projective_catalog_count(catalog) != 36:
        errors.append("independent catalog count mismatch")
    if canonical_hash(catalog) != EXPECTED_CATALOG_SHA256:
        errors.append("independent catalog hash mismatch")
    if catalog != source.get("rational_frame_catalog"):
        errors.append("independent catalog content mismatch")
    if contract["acceptance"]["frozen_grid"]["catalog_sha256"] != canonical_hash(catalog):
        errors.append("contract catalog hash mismatch")

    source_keys = [
        (
            row["coupling"],
            int(row["n"]),
            row["frame_id"],
            row["c"],
            row["s"],
        )
        for row in source.get("rational_grid_rows", [])
    ]
    source_counter = Counter(source_keys)
    missing_count = sum((expected_counter - source_counter).values())
    extra_count = sum((source_counter - expected_counter).values())
    duplicate_count = sum(count - 1 for count in source_counter.values() if count > 1)
    if (missing_count, extra_count, duplicate_count) != (0, 0, 0):
        errors.append("source grid has missing, extra, or duplicate rows")
    source_rows = {key: row for key, row in zip(source_keys, source.get("rational_grid_rows", []))}

    continuous_rebuilds: list[dict[str, Any]] = []
    source_continuous = {
        (row["coupling"], int(row["n"])): row for row in source.get("continuous_rows", [])
    }
    for coupling in FROZEN_COUPLINGS:
        for n in CONTINUOUS_SIZES:
            rebuilt = continuous_rebuild(n, coupling)
            continuous_rebuilds.append(rebuilt)
            source_row = source_continuous.get((fraction_text(coupling), n))
            if source_row is None:
                errors.append(f"continuous J={fraction_text(coupling)},n={n}: missing source row")
            else:
                errors.extend(compare_continuous(source_row, rebuilt))

    grid_compact: list[dict[str, Any]] = []
    for coupling in FROZEN_COUPLINGS:
        for n in GRID_SIZES:
            for frame in catalog:
                key = grid_key(coupling, n, frame)
                rebuilt = rational_row(n, coupling, frame)
                source_row = source_rows.get(key)
                if source_row is None:
                    errors.append(f"grid {key}: missing source row")
                else:
                    errors.extend(compare_rational(source_row, rebuilt, f"grid {key}"))
                grid_compact.append(
                    {
                        "coupling": rebuilt["coupling"],
                        "n": n,
                        "frame_id": rebuilt["frame_id"],
                        "operator_basis_sha256": rebuilt["operator_basis_sha256"],
                        "commutator_matrix_sha256": rebuilt["commutator_matrix_sha256"],
                        "candidate_column_count": rebuilt["candidate_column_count"],
                        "third_prime_operator_rank": rebuilt["third_prime_operator_rank"],
                        "third_prime_commutator_rank": rebuilt["third_prime_commutator_rank"],
                    }
                )
                del rebuilt
                gc.collect()

    control = rational_row(
        6, Fraction(0), {"frame_id": "positive_control_t0", "c": "1", "s": "0"}
    )
    source_control = source.get("positive_control", {})
    errors.extend(compare_rational(source_control, control, "positive control"))
    for field in (
        "onsite_axis_a_witness_count",
        "onsite_axis_a_commutes_count",
        "onsite_axis_a_in_span_count",
    ):
        if source_control.get(field) != control.get(field):
            errors.append(f"positive control: {field} mismatch")
    if not (
        control["candidate_column_count"] == 79
        and control["third_prime_operator_rank"] == 79
        and control["third_prime_commutator_rank"] == 42
        and control["third_prime_nullity"] == 37
        and control.get("onsite_axis_a_commutes_count") == 6
        and control.get("onsite_axis_a_in_span_count") == 6
    ):
        errors.append("positive control exact rank/witness contract failed")

    if not phase_oracle["checked"]:
        errors.append("one-qubit matrix phase oracle failed")
    if not sturm_oracle["checked"]:
        errors.append("Fraction Sturm regression oracle failed")
    if not anti_circularity["checked"]:
        errors.append("AST anti-circularity failed")
    if not freeze["verified"]:
        errors.append("public freeze verification failed")
    if source.get("status") != STATUS_ACCEPTED:
        errors.append("source result is not the accepted narrow R199 boundary")
    if not all(item.get("passed") for item in source.get("requirements", [])):
        errors.append("source acceptance requirements are incomplete")
    if source.get("claims", {}).get("scientific_promotion_accepted") is not False:
        errors.append("scientific promotion must remain false")
    if source.get("claims", {}).get("new_credit_delta") != 0:
        errors.append("new credit delta must remain zero")
    if any(source.get("claims", {}).get(key) for key in FORBIDDEN_CLAIM_KEYS):
        errors.append("a forbidden broad claim is true")

    continuous_compact = [
        {
            "coupling": row["coupling"],
            "n": row["n"],
            "candidate_column_count": row["candidate_column_count"],
            "polynomial_commutator_matrix_sha256": row["polynomial_commutator_matrix_sha256"],
            "source_anchor_determinants": row["source_anchor_determinants"],
            "audit_owned_anchor_determinants": row["audit_owned_anchor_determinants"],
            "audit_owned_adaptive_determinants": row[
                "audit_owned_adaptive_determinants"
            ],
            "audit_owned_adaptive_round_count": row[
                "audit_owned_adaptive_round_count"
            ],
            "audit_owned_unresolved_factors": row[
                "audit_owned_unresolved_factors"
            ],
            "unique_exact_determinant_count": row[
                "unique_exact_determinant_count"
            ],
            "source_anchor_sturm": row["source_anchor_sturm"],
            "audit_anchor_sturm": row["audit_anchor_sturm"],
            "explicit_projective_infinity_third_prime_rank": row[
                "explicit_projective_infinity"
            ]["third_prime_commutator_rank"],
            "homogenized_projective_infinity": row["homogenized_projective_infinity"],
        }
        for row in continuous_rebuilds
    ]
    core = {
        "source_result": {
            "path": str(RESULT_PATH),
            "sha256": sha256_file(root / RESULT_PATH),
            "payload_sha256": recorded_payload_hash,
            "recomputed_payload_sha256": recomputed_payload_hash,
            "payload_roundtrip_normalizations": payload_normalizations,
            "protocol_hash": source.get("protocol_hash"),
        },
        "public_freeze": freeze,
        "anti_circularity": anti_circularity,
        "one_qubit_phase_oracle": phase_oracle,
        "sturm_regression_oracle": sturm_oracle,
        "pre_source_generation": pre_source_generation,
        "grid_shape_audit": {
            "missing_count": missing_count,
            "extra_count": extra_count,
            "duplicate_count": duplicate_count,
        },
        "continuous_rebuilds": continuous_compact,
        "rational_grid_rebuilds": grid_compact,
        "positive_control": control,
        "claim_boundary": {
            "scientific_promotion_accepted": False,
            "new_credit_delta": 0,
            "narrow_only": True,
        },
        "errors": errors,
    }
    return {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "status": "pass" if not errors else "fail",
        "audit_prime": AUDIT_PRIME,
        "source_anchor_set": list(SOURCE_ANCHORS),
        "audit_owned_anchor_set": list(AUDIT_ANCHORS),
        "anchor_sets_disjoint": set(SOURCE_ANCHORS).isdisjoint(AUDIT_ANCHORS),
        "source_fields_consumed_for_rebuild": list(
            SOURCE_FIELDS_CONSUMED_FOR_REBUILD
        ),
        "continuous_exact_match_count": sum(
            not any(error.startswith(f"continuous J={row['coupling']},n={row['n']}") for error in errors)
            for row in continuous_rebuilds
        ),
        "rational_grid_row_count": len(grid_compact),
        "third_prime_full_rank_grid_count": sum(
            row["third_prime_operator_rank"] == row["candidate_column_count"]
            and row["third_prime_commutator_rank"] == row["candidate_column_count"]
            for row in grid_compact
        ),
        "grid_shape_audit": core["grid_shape_audit"],
        "positive_control": {
            "candidate_column_count": control["candidate_column_count"],
            "operator_rank": control["third_prime_operator_rank"],
            "commutator_rank": control["third_prime_commutator_rank"],
            "nullity": control["third_prime_nullity"],
            "commuting_onsite_witness_count": control.get("onsite_axis_a_commutes_count", 0),
            "in_span_onsite_witness_count": control.get("onsite_axis_a_in_span_count", 0),
        },
        "evidence_integrity_complete": not errors,
        "error_count": len(errors),
        "errors": errors,
        "source_result": core["source_result"],
        "public_freeze": freeze,
        "anti_circularity": anti_circularity,
        "one_qubit_phase_oracle": phase_oracle,
        "sturm_regression_oracle": sturm_oracle,
        "pre_source_generation": pre_source_generation,
        "continuous_rebuilds": continuous_compact,
        "rational_grid_rebuilds": grid_compact,
        "claim_boundary": core["claim_boundary"],
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
    if not output_path.is_absolute():
        output_path = root / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(audit, indent=2 if args.pretty else None, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "status": audit["status"],
                "continuous_exact_match_count": audit["continuous_exact_match_count"],
                "third_prime_full_rank_grid_count": audit["third_prime_full_rank_grid_count"],
                "rational_grid_row_count": audit["rational_grid_row_count"],
                "positive_control": audit["positive_control"],
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
