#!/usr/bin/env python3
"""Prove unconditional coefficient bounds for the four R201 determinants."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import sympy as sp

import b9_r201_projective_patch_certificate as r201
import b9_r201_singular_minor_bridge as bridge


VERSION = "0.1.0"
METHOD = "b9_r201_unconditional_integer_determinant_bound_v1"
EXISTING_PRIMES = (1_000_003, 536_870_723)
SINGULAR_PRIME_LIMIT = 1 << 29
EXPECTED_DIMENSION = 37
EXPECTED_DETERMINANT_DEGREE = 184


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def polynomial_payload(polynomial: sp.Poly) -> list[list[Any]]:
    return [
        [list(monomial), str(int(coefficient))]
        for monomial, coefficient in polynomial.terms()
    ]


def entry_polynomials(entries: list[sp.Expr]) -> list[sp.Poly]:
    polynomials = []
    for expression in entries:
        polynomial = sp.Poly(sp.expand(expression), *r201.VARS, domain=sp.ZZ)
        if polynomial.domain != sp.ZZ:
            raise RuntimeError("R201 matrix entry is not an integer polynomial")
        polynomials.append(polynomial)
    return polynomials


def l1_norm(polynomial: sp.Poly) -> int:
    return sum(abs(int(coefficient)) for coefficient in polynomial.coeffs())


def common_column_D_exponent(
    polynomials: list[sp.Poly], dimension: int, column: int, D: sp.Poly
) -> int:
    exponents = []
    for row in range(dimension):
        polynomial = polynomials[row * dimension + column]
        if polynomial.is_zero:
            continue
        exponent = 0
        quotient = polynomial
        while True:
            next_quotient, remainder = sp.div(quotient, D)
            if not remainder.is_zero:
                break
            quotient = next_quotient
            exponent += 1
        exponents.append(exponent)
    if not exponents:
        raise RuntimeError(f"R201 matrix column {column} is identically zero")
    return min(exponents)


def column_homogeneous_degrees(
    polynomials: list[sp.Poly], dimension: int
) -> list[int]:
    degrees = []
    for column in range(dimension):
        observed = set()
        for row in range(dimension):
            polynomial = polynomials[row * dimension + column]
            if polynomial.is_zero:
                continue
            entry_degrees = {sum(monomial) for monomial, _ in polynomial.terms()}
            if len(entry_degrees) != 1:
                raise RuntimeError(
                    f"R201 matrix entry ({row}, {column}) is not homogeneous"
                )
            observed.update(entry_degrees)
        if len(observed) != 1:
            raise RuntimeError(
                f"R201 matrix column {column} has inconsistent homogeneous degrees"
            )
        degrees.append(observed.pop())
    return degrees


def candidate_bounds(norm_matrix: list[list[int]]) -> dict[str, int]:
    dimension = len(norm_matrix)
    row_sums = [sum(row) for row in norm_matrix]
    column_sums = [
        sum(norm_matrix[row][column] for row in range(dimension))
        for column in range(dimension)
    ]
    row_maxima = [max(row) for row in norm_matrix]
    column_maxima = [
        max(norm_matrix[row][column] for row in range(dimension))
        for column in range(dimension)
    ]
    return {
        "row_sum_product": math.prod(row_sums),
        "column_sum_product": math.prod(column_sums),
        "factorial_row_max_product": math.factorial(dimension)
        * math.prod(row_maxima),
        "factorial_column_max_product": math.factorial(dimension)
        * math.prod(column_maxima),
    }


def integer_summary(value: int) -> dict[str, Any]:
    return {
        "value": str(value),
        "bit_length": value.bit_length(),
        "decimal_digits": len(str(value)),
    }


def deterministic_prime_plan(maximum_bound: int) -> dict[str, Any]:
    target = 2 * maximum_bound
    modulus = math.prod(EXISTING_PRIMES)
    planned = []
    cursor = SINGULAR_PRIME_LIMIT
    while modulus <= target:
        cursor = int(sp.prevprime(cursor))
        if cursor in EXISTING_PRIMES:
            continue
        planned.append(cursor)
        modulus *= cursor
    previous_modulus = modulus // planned[-1] if planned else modulus
    return {
        "selection_rule": "descending distinct primes below 2^29",
        "prime_limit_exclusive": SINGULAR_PRIME_LIMIT,
        "existing_primes": list(EXISTING_PRIMES),
        "existing_modulus": integer_summary(math.prod(EXISTING_PRIMES)),
        "planned_additional_primes": planned,
        "planned_prime_count": len(planned),
        "planned_minor_artifact_count": len(planned) * 4,
        "all_planned_values_are_distinct_primes_below_limit": (
            len(set(planned)) == len(planned)
            and all(sp.isprime(prime) for prime in planned)
            and all(0 < prime < SINGULAR_PRIME_LIMIT for prime in planned)
        ),
        "target_twice_maximum_bound": integer_summary(target),
        "modulus_before_final_prime": integer_summary(previous_modulus),
        "final_modulus": integer_summary(modulus),
        "modulus_before_final_prime_is_insufficient": previous_modulus <= target,
        "final_modulus_exceeds_twice_maximum_bound": modulus > target,
        "uniqueness_rule": (
            "For every integer coefficient c with |c| <= B, residues modulo "
            "M determine the unique symmetric representative once M > 2B."
        ),
    }


def analyze(root: Path) -> dict[str, Any]:
    matrices, records = bridge.engineering_row_sets()
    if len(matrices) != 4 or any(
        record["dimension"] != EXPECTED_DIMENSION for record in records
    ):
        raise RuntimeError("expected four frozen 37x37 R201 engineering minors")

    D = sp.Poly(sum(variable**2 for variable in r201.VARS), *r201.VARS, domain=sp.ZZ)
    rows = []
    selected_bounds = []
    for minor_index, (entries, record) in enumerate(zip(matrices, records)):
        dimension = record["dimension"]
        polynomials = entry_polynomials(entries)
        norm_matrix = [
            [l1_norm(polynomials[row * dimension + column]) for column in range(dimension)]
            for row in range(dimension)
        ]
        bounds = candidate_bounds(norm_matrix)
        selected_method, selected_bound = min(bounds.items(), key=lambda item: item[1])
        selected_bounds.append(selected_bound)

        column_degrees = column_homogeneous_degrees(polynomials, dimension)
        column_D_exponents = [
            common_column_D_exponent(polynomials, dimension, column, D)
            for column in range(dimension)
        ]
        if sum(column_degrees) != EXPECTED_DETERMINANT_DEGREE:
            raise RuntimeError("R201 determinant degree does not match frozen degree 184")

        entry_payload_hash = canonical_hash(
            [polynomial_payload(polynomial) for polynomial in polynomials]
        )
        rows.append(
            {
                "minor_index": minor_index,
                "dimension": dimension,
                "row_words_sha256": record["row_words_sha256"],
                "source_matrix_sha256": record["matrix_sha256"],
                "entry_polynomial_payload_sha256": entry_payload_hash,
                "entry_l1_norm_matrix_sha256": canonical_hash(norm_matrix),
                "integer_polynomial_entry_count": len(polynomials),
                "all_entries_are_integer_polynomials": True,
                "all_nonzero_entries_are_column_homogeneous": True,
                "column_homogeneous_degrees": column_degrees,
                "determinant_homogeneous_degree": sum(column_degrees),
                "homogeneous_monomial_lattice_size": math.comb(
                    EXPECTED_DETERMINANT_DEGREE + 2, 2
                ),
                "column_common_D_exponents": column_D_exponents,
                "column_common_D_exponent_sum": sum(column_D_exponents),
                "D_is_not_a_trivial_column_product_factor": (
                    sum(column_D_exponents) == 0
                ),
                "candidate_bounds": {
                    name: integer_summary(value) for name, value in bounds.items()
                },
                "selected_bound_method": selected_method,
                "selected_unconditional_coefficient_bound": integer_summary(
                    selected_bound
                ),
                "twice_selected_bound_bit_length": (2 * selected_bound).bit_length(),
            }
        )

    maximum_bound = max(selected_bounds)
    prime_plan = deterministic_prime_plan(maximum_bound)
    source_structure = root / "results/B9_R201_modular_minor_structure_v0.json"
    source_structure_payload = json.loads(source_structure.read_text())
    checked = (
        all(row["all_entries_are_integer_polynomials"] for row in rows)
        and all(row["all_nonzero_entries_are_column_homogeneous"] for row in rows)
        and all(row["determinant_homogeneous_degree"] == 184 for row in rows)
        and all(row["column_common_D_exponent_sum"] == 0 for row in rows)
        and prime_plan["all_planned_values_are_distinct_primes_below_limit"]
        and prime_plan["modulus_before_final_prime_is_insufficient"]
        and prime_plan["final_modulus_exceeds_twice_maximum_bound"]
    )
    return {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R201_integer_determinant_bound_and_CRT_budget_only",
        "coupling": "13/32",
        "n": 4,
        "variables": [str(variable) for variable in r201.VARS],
        "minor_count": len(rows),
        "dimension": EXPECTED_DIMENSION,
        "entry_count": len(rows) * EXPECTED_DIMENSION**2,
        "determinant_degree": EXPECTED_DETERMINANT_DEGREE,
        "coefficient_bound_argument": (
            "Polynomial L1 norm is submultiplicative. The Leibniz determinant "
            "expansion is bounded by the permanent of the entry-L1 matrix, "
            "which is bounded independently by each recorded row/column sum "
            "product and factorial row/column maximum product. Every individual "
            "integer determinant coefficient is at most the selected L1 bound."
        ),
        "bridge_tool_sha256": sha256_file(root / "tools/b9_r201_singular_minor_bridge.py"),
        "source_tool_sha256": sha256_file(
            root / "tools/b9_r201_projective_patch_certificate.py"
        ),
        "source_modular_structure_sha256": sha256_file(source_structure),
        "source_modular_artifact_bundle_sha256": source_structure_payload[
            "artifact_bundle_sha256"
        ],
        "rows": rows,
        "maximum_unconditional_coefficient_bound": integer_summary(maximum_bound),
        "maximum_bound_minor_index": selected_bounds.index(maximum_bound),
        "prime_plan": prime_plan,
        "direct_degree_96_residual_CRT_accepted": False,
        "required_reconstruction_order": [
            "compute every frozen degree-184 determinant at all planned primes",
            "reconstruct every degree-184 integer coefficient by symmetric CRT",
            "replay each reconstructed determinant against public matrix points",
            "verify exact divisibility by D^44 in ZZ[a,b,c]",
            "only then factor or use the degree-96 integer quotient",
        ],
        "characteristic_zero_D44_divisibility_verified": False,
        "bounded_CRT_integer_reconstruction_complete": False,
        "characteristic_zero_engineering_certificate_verified": False,
        "ideal_membership_certificate_verified": False,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "checked": checked,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    result = analyze(root)
    output = args.output if args.output.is_absolute() else root / args.output
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "checked": result["checked"],
                "maximum_bound_bits": result[
                    "maximum_unconditional_coefficient_bound"
                ]["bit_length"],
                "additional_prime_count": result["prime_plan"][
                    "planned_prime_count"
                ],
                "additional_minor_artifact_count": result["prime_plan"][
                    "planned_minor_artifact_count"
                ],
                "final_modulus_bits": result["prime_plan"]["final_modulus"][
                    "bit_length"
                ],
                "new_credit_delta": result["new_credit_delta"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
