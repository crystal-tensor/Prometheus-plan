#!/usr/bin/env python3
"""Prove coefficient bounds and a CRT budget for the R204/R206/R208 minors."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

import sympy as sp

import b9_r201_independent_audit as source
import b9_r204_expanded_minor_bridge as r204
import b9_r206_sixth_minor_bridge as r206
import b9_r208_seventh_minor_bridge as r208


VERSION = "0.1.0"
METHOD = "b9_r209_three_minor_unconditional_coefficient_bound_v1"
EXISTING_PRIMES = (1_000_003, 536_870_723)
SINGULAR_PRIME_LIMIT = 1 << 29
EXPECTED_DIMENSION = 37
EXPECTED_DETERMINANT_DEGREE = 184
MINOR_BUILDERS: tuple[tuple[int, str, Callable], ...] = (
    (4, "R204", r204.matrix_and_record),
    (5, "R206", r206.matrix_and_record),
    (6, "R208", r208.matrix_and_record),
)


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
        polynomial = sp.Poly(sp.expand(expression), *source.VARS, domain=sp.ZZ)
        if polynomial.domain != sp.ZZ:
            raise RuntimeError("R209 matrix entry is not an integer polynomial")
        polynomials.append(polynomial)
    return polynomials


def l1_norm(polynomial: sp.Poly) -> int:
    return sum(abs(int(coefficient)) for coefficient in polynomial.coeffs())


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
                    f"R209 matrix entry ({row}, {column}) is not homogeneous"
                )
            observed.update(entry_degrees)
        if len(observed) != 1:
            raise RuntimeError(
                f"R209 matrix column {column} has inconsistent degrees"
            )
        degrees.append(observed.pop())
    return degrees


def common_column_d_exponent(
    polynomials: list[sp.Poly], dimension: int, column: int, d_poly: sp.Poly
) -> int:
    exponents = []
    for row in range(dimension):
        polynomial = polynomials[row * dimension + column]
        if polynomial.is_zero:
            continue
        exponent = 0
        quotient = polynomial
        while True:
            next_quotient, remainder = sp.div(quotient, d_poly, domain=sp.ZZ)
            if not remainder.is_zero:
                break
            quotient = next_quotient
            exponent += 1
        exponents.append(exponent)
    if not exponents:
        raise RuntimeError(f"R209 matrix column {column} is identically zero")
    return min(exponents)


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
        "planned_minor_artifact_count": len(planned) * len(MINOR_BUILDERS),
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
    d_poly = sp.Poly(
        sum(variable**2 for variable in source.VARS),
        *source.VARS,
        domain=sp.ZZ,
    )
    rows = []
    selected_bounds = []
    for minor_index, source_round, builder in MINOR_BUILDERS:
        entries, record = builder(root)
        dimension = record["dimension"]
        if dimension != EXPECTED_DIMENSION or len(entries) != dimension**2:
            raise RuntimeError(f"{source_round} does not define a frozen 37x37 minor")
        polynomials = entry_polynomials(entries)
        norm_matrix = [
            [
                l1_norm(polynomials[row * dimension + column])
                for column in range(dimension)
            ]
            for row in range(dimension)
        ]
        bounds = candidate_bounds(norm_matrix)
        selected_method, selected_bound = min(bounds.items(), key=lambda item: item[1])
        selected_bounds.append(selected_bound)
        column_degrees = column_homogeneous_degrees(polynomials, dimension)
        column_d_exponents = [
            common_column_d_exponent(polynomials, dimension, column, d_poly)
            for column in range(dimension)
        ]
        determinant_degree = sum(column_degrees)
        rows.append(
            {
                "minor_index": minor_index,
                "source_round": source_round,
                "dimension": dimension,
                "row_words_sha256": record["row_words_sha256"],
                "source_matrix_sha256": record["matrix_sha256"],
                "candidate_labels_sha256": record["candidate_labels_sha256"],
                "entry_polynomial_payload_sha256": canonical_hash(
                    [polynomial_payload(polynomial) for polynomial in polynomials]
                ),
                "entry_l1_norm_matrix_sha256": canonical_hash(norm_matrix),
                "integer_polynomial_entry_count": len(polynomials),
                "all_entries_are_integer_polynomials": True,
                "all_nonzero_entries_are_column_homogeneous": True,
                "column_homogeneous_degrees": column_degrees,
                "determinant_homogeneous_degree": determinant_degree,
                "homogeneous_monomial_lattice_size": math.comb(
                    EXPECTED_DETERMINANT_DEGREE + 2, 2
                ),
                "column_common_D_exponents": column_d_exponents,
                "column_common_D_exponent_sum": sum(column_d_exponents),
                "D_is_not_a_trivial_column_product_factor": (
                    sum(column_d_exponents) == 0
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
    checked = bool(
        len(rows) == 3
        and all(row["determinant_homogeneous_degree"] == 184 for row in rows)
        and all(row["column_common_D_exponent_sum"] == 0 for row in rows)
        and len({row["row_words_sha256"] for row in rows}) == 3
        and prime_plan["all_planned_values_are_distinct_primes_below_limit"]
        and prime_plan["modulus_before_final_prime_is_insufficient"]
        and prime_plan["final_modulus_exceeds_twice_maximum_bound"]
    )
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R209_three_minor_integer_bound_and_CRT_budget_only",
        "coupling": "13/32",
        "n": 4,
        "variables": [str(variable) for variable in source.VARS],
        "minor_count": len(rows),
        "dimension": EXPECTED_DIMENSION,
        "entry_count": len(rows) * EXPECTED_DIMENSION**2,
        "determinant_degree": EXPECTED_DETERMINANT_DEGREE,
        "coefficient_bound_argument": (
            "Polynomial L1 norm is submultiplicative. The Leibniz determinant "
            "expansion is bounded by the permanent of the entry-L1 matrix, "
            "which is bounded by each recorded row/column sum product and "
            "factorial row/column maximum product. Every determinant "
            "coefficient is at most the selected bound."
        ),
        "source_tools": {
            "R204": sha256_file(root / "tools/b9_r204_expanded_minor_bridge.py"),
            "R206": sha256_file(root / "tools/b9_r206_sixth_minor_bridge.py"),
            "R208": sha256_file(root / "tools/b9_r208_seventh_minor_bridge.py"),
        },
        "rows": rows,
        "maximum_unconditional_coefficient_bound": integer_summary(maximum_bound),
        "maximum_bound_minor_index": rows[selected_bounds.index(maximum_bound)][
            "minor_index"
        ],
        "prime_plan": prime_plan,
        "direct_degree_96_residual_CRT_accepted": False,
        "required_reconstruction_order": [
            "compute all three degree-184 determinants at every planned prime",
            "reconstruct every degree-184 integer coefficient by symmetric CRT",
            "replay each determinant against direct integer matrix evaluations",
            "verify exact divisibility by D^44 in ZZ[a,b,c]",
            "only then use the three degree-96 integer quotients",
        ],
        "bounded_CRT_integer_reconstruction_complete": False,
        "characteristic_zero_D44_divisibility_verified": False,
        "QQ_Nullstellensatz_certificate_verified": False,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "checked": checked,
    }
    stable_payload = dict(result)
    result["stable_payload_sha256"] = canonical_hash(stable_payload)
    payload_without_hash = dict(result)
    result["payload_sha256"] = canonical_hash(payload_without_hash)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    result = analyze(root)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
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
