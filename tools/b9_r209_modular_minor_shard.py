#!/usr/bin/env python3
"""Compute one planned R209 determinant shard over a fresh finite field."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import sympy as sp

import b9_r201_independent_audit as source
import b9_r201_modular_minor_structure as modular
import b9_r201_singular_minor_bridge as singular_bridge
import b9_r204_expanded_minor_bridge as r204
import b9_r206_sixth_minor_bridge as r206
import b9_r208_seventh_minor_bridge as r208


VERSION = "0.1.0"
METHOD = "b9_r209_planned_modular_minor_shard_v1"
BOUND_PATH = Path("results/B9_R209_determinant_coefficient_bound_v0.json")
EXPECTED_DIMENSION = 37
EXPECTED_DETERMINANT_DEGREE = 184
D_EXPONENT = 44
MINOR_BUILDERS: dict[int, tuple[str, Callable]] = {
    4: ("R204", r204.matrix_and_record),
    5: ("R206", r206.matrix_and_record),
    6: ("R208", r208.matrix_and_record),
}
REPLAY_POINTS = ((2, 0, 1), (1, 0, -2), (1, 2, 3), (3, -1, 2))


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def polynomial_payload(polynomial: sp.Poly, prime: int) -> list[list[Any]]:
    return [
        [list(monomial), str(int(coefficient) % prime)]
        for monomial, coefficient in polynomial.terms()
        if int(coefficient) % prime
    ]


def sparse_evaluate(
    polynomial: modular.SparsePolynomial,
    point: tuple[int, int, int],
    prime: int,
) -> int:
    return sum(
        coefficient
        * pow(point[0], monomial[0], prime)
        * pow(point[1], monomial[1], prime)
        * pow(point[2], monomial[2], prime)
        for monomial, coefficient in polynomial.items()
    ) % prime


def direct_matrix_determinant(
    entries: list[sp.Expr], dimension: int, point: tuple[int, int, int]
) -> int:
    substitutions = dict(zip(source.VARS, point))
    matrix = sp.Matrix(
        dimension,
        dimension,
        [int(expression.subs(substitutions)) for expression in entries],
    )
    return int(matrix.det(method="domain-ge"))


def validate_bound(
    root: Path, prime: int, minor_index: int, record: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    bound_path = root / BOUND_PATH
    bound = json.loads(bound_path.read_text())
    rows = [
        row for row in bound.get("rows", []) if row.get("minor_index") == minor_index
    ]
    if (
        bound.get("checked") is not True
        or bound.get("method")
        != "b9_r209_three_minor_unconditional_coefficient_bound_v1"
        or prime
        not in bound.get("prime_plan", {}).get("planned_additional_primes", [])
        or len(rows) != 1
    ):
        raise ValueError("R209 bound or planned-prime contract is not accepted")
    row = rows[0]
    if (
        row.get("row_words_sha256") != record["row_words_sha256"]
        or row.get("source_matrix_sha256") != record["matrix_sha256"]
        or row.get("candidate_labels_sha256") != record["candidate_labels_sha256"]
        or row.get("determinant_homogeneous_degree") != 184
        or row.get("column_common_D_exponent_sum") != 0
    ):
        raise ValueError("R209 bound row does not bind the requested minor")
    return bound, {
        "bound_result_sha256": sha256_file(bound_path),
        "bound_stable_payload_sha256": bound["stable_payload_sha256"],
        "selected_bound_method": row["selected_bound_method"],
        "selected_unconditional_coefficient_bound": row[
            "selected_unconditional_coefficient_bound"
        ],
    }


def compute(
    root: Path, prime: int, minor_index: int, timeout_seconds: int
) -> dict[str, Any]:
    if prime < 2 or not sp.isprime(prime):
        raise ValueError("--prime must be prime")
    if minor_index not in MINOR_BUILDERS:
        raise ValueError("--minor-index must be one of 4, 5, or 6")
    source_round, builder = MINOR_BUILDERS[minor_index]
    entries, record = builder(root)
    dimension = record["dimension"]
    if dimension != EXPECTED_DIMENSION or len(entries) != dimension**2:
        raise ValueError("R209 source does not define a frozen 37x37 minor")
    _, bound_record = validate_bound(root, prime, minor_index, record)

    singular = shutil.which("Singular")
    if singular is None:
        raise RuntimeError("Singular executable not found")
    script = singular_bridge.singular_script(entries, dimension, prime)
    started = time.monotonic()
    completed = subprocess.run(
        [singular, "-q"],
        input=script,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
    )
    elapsed = time.monotonic() - started
    if completed.returncode != 0:
        raise RuntimeError(
            f"Singular failed with {completed.returncode}: {completed.stderr[-4000:]}"
        )

    determinant = singular_bridge.parse_polynomial(completed.stdout, prime)
    determinant_terms = polynomial_payload(determinant, prime)
    determinant_sparse = modular.payload_to_sparse(determinant_terms, prime)
    factors, factorization_input_sha256 = modular.factor_with_singular(
        determinant_sparse, prime
    )
    factorization_validated = modular.validate_factorization(
        determinant_sparse, factors, prime
    )
    d_sparse: modular.SparsePolynomial = {
        (2, 0, 0): 1,
        (0, 2, 0): 1,
        (0, 0, 2): 1,
    }
    d_hash = canonical_hash(modular.sparse_to_payload(d_sparse, prime))
    d_factor_rows = [
        factor
        for factor in factors
        if factor["normalized_terms_sha256"] == d_hash
    ]
    exact_d44_factor = bool(
        len(d_factor_rows) == 1
        and d_factor_rows[0]["multiplicity"] >= D_EXPONENT
    )
    quotient_sparse: modular.SparsePolynomial = {(0, 0, 0): 1}
    factor_summary = []
    for factor in factors:
        multiplicity = factor["multiplicity"]
        if factor["normalized_terms_sha256"] == d_hash:
            multiplicity -= D_EXPONENT
        factor_sparse = modular.payload_to_sparse(
            factor["normalized_terms"], prime
        )
        if multiplicity:
            quotient_sparse = modular.sparse_multiply(
                quotient_sparse,
                modular.sparse_power(factor_sparse, multiplicity, prime),
                prime,
            )
        factor_summary.append(
            {
                "multiplicity": factor["multiplicity"],
                "degree": factor["degree"],
                "term_count": factor["term_count"],
                "normalized_terms_sha256": factor[
                    "normalized_terms_sha256"
                ],
                "is_D_factor": factor["normalized_terms_sha256"] == d_hash,
            }
        )
    recomposed_monic = modular.sparse_multiply(
        quotient_sparse,
        modular.sparse_power(d_sparse, D_EXPONENT, prime),
        prime,
    )
    leading_monomial = max(determinant_sparse)
    factorization_scalar = (
        determinant_sparse[leading_monomial]
        * pow(recomposed_monic[leading_monomial], -1, prime)
        % prime
    )
    quotient_sparse = {
        monomial: coefficient * factorization_scalar % prime
        for monomial, coefficient in quotient_sparse.items()
        if coefficient * factorization_scalar % prime
    }
    quotient_terms = modular.sparse_to_payload(quotient_sparse, prime)
    quotient_total_degree = max(sum(monomial) for monomial in quotient_sparse)
    recomposed_sparse = modular.sparse_multiply(
        quotient_sparse,
        modular.sparse_power(d_sparse, D_EXPONENT, prime),
        prime,
    )
    exact_d44_division = bool(
        exact_d44_factor
        and factorization_validated
        and recomposed_sparse == determinant_sparse
    )

    point_rows = []
    for point in REPLAY_POINTS:
        direct_integer = direct_matrix_determinant(entries, dimension, point)
        polynomial_value = sparse_evaluate(determinant_sparse, point, prime)
        quotient_value = sparse_evaluate(quotient_sparse, point, prime)
        d_value = sum(value * value for value in point) % prime
        point_rows.append(
            {
                "projective_point": list(point),
                "D_mod_prime": d_value,
                "direct_integer_determinant_sha256": hashlib.sha256(
                    str(direct_integer).encode()
                ).hexdigest(),
                "direct_integer_determinant_mod_prime": direct_integer % prime,
                "polynomial_determinant_mod_prime": polynomial_value,
                "quotient_mod_prime": quotient_value,
                "determinant_replay_match": direct_integer % prime
                == polynomial_value,
                "D_power_recomposition_match": polynomial_value
                == quotient_value * pow(d_value, D_EXPONENT, prime) % prime,
            }
        )

    checked = bool(
        determinant.total_degree() == EXPECTED_DETERMINANT_DEGREE
        and quotient_total_degree == EXPECTED_DETERMINANT_DEGREE - 2 * D_EXPONENT
        and exact_d44_division
        and all(row["determinant_replay_match"] for row in point_rows)
        and all(row["D_power_recomposition_match"] for row in point_rows)
    )
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R209_planned_modular_determinant_shard_only",
        "coupling": "13/32",
        "coefficient_domain": f"GF({prime})",
        "characteristic": prime,
        "n": 4,
        "minor_index": minor_index,
        "source_round": source_round,
        **record,
        **bound_record,
        "singular_path": singular,
        "singular_version": subprocess.check_output(
            [singular, "--version"], text=True
        ).splitlines()[0],
        "tool_sha256": sha256_file(Path(__file__).resolve()),
        "singular_input_sha256": hashlib.sha256(script.encode()).hexdigest(),
        "determinant_total_degree": determinant.total_degree(),
        "determinant_term_count": len(determinant_terms),
        "determinant_canonical_terms": determinant_terms,
        "determinant_canonical_terms_sha256": canonical_hash(determinant_terms),
        "factorization_input_sha256": factorization_input_sha256,
        "factorization_rows": factor_summary,
        "factorization_validated": factorization_validated,
        "factorization_nonzero_scalar": factorization_scalar,
        "D_factor_normalized_terms_sha256": d_hash,
        "D_exponent": D_EXPONENT,
        "exact_D44_division_verified_mod_prime": exact_d44_division,
        "quotient_total_degree": quotient_total_degree,
        "quotient_term_count": len(quotient_terms),
        "quotient_canonical_terms": quotient_terms,
        "quotient_canonical_terms_sha256": canonical_hash(quotient_terms),
        "remainder_term_count": 0 if exact_d44_division else None,
        "remainder_is_zero": exact_d44_division,
        "point_replays": point_rows,
        "all_direct_integer_point_replays_match": all(
            row["determinant_replay_match"] for row in point_rows
        ),
        "all_D44_point_recompositions_match": all(
            row["D_power_recomposition_match"] for row in point_rows
        ),
        "elapsed_seconds": round(elapsed, 6),
        "bounded_CRT_integer_reconstruction_complete": False,
        "characteristic_zero_D44_divisibility_verified": False,
        "QQ_Nullstellensatz_certificate_verified": False,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "checked": checked,
    }
    stable_payload = dict(result)
    stable_payload.pop("elapsed_seconds", None)
    stable_payload.pop("singular_path", None)
    result["stable_payload_sha256"] = canonical_hash(stable_payload)
    payload_without_hash = dict(result)
    result["payload_sha256"] = canonical_hash(payload_without_hash)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--prime", type=int, required=True)
    parser.add_argument("--minor-index", type=int, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    result = compute(root, args.prime, args.minor_index, args.timeout_seconds)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "prime": result["characteristic"],
                "minor_index": result["minor_index"],
                "determinant_term_count": result["determinant_term_count"],
                "quotient_term_count": result["quotient_term_count"],
                "elapsed_seconds": result["elapsed_seconds"],
                "checked": result["checked"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
