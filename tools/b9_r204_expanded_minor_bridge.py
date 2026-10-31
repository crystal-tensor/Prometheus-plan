#!/usr/bin/env python3
"""Compute the first R204 independent maximal minor over a finite field."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

import sympy as sp

import b9_r201_independent_audit as source
import b9_r201_modular_minor_structure as modular
import b9_r201_singular_minor_bridge as singular_bridge


METHOD = "b9_r204_independent_added_minor_bridge_v1"
VERSION = "0.1.0"
ENGINEERING_COUPLING = Fraction(13, 32)
R203_PATH = Path("results/B9_R203_rational_common_zero_rank_replay_v0.json")
ROW_SOURCE_INDEX = 0
NEW_MINOR_INDEX = 4


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


def matrix_and_record(root: Path) -> tuple[list[sp.Expr], dict[str, Any]]:
    r203_path = root / R203_PATH
    r203 = json.loads(r203_path.read_text())
    witness = r203["witness_rows"][ROW_SOURCE_INDEX]
    row_words = witness["source_full_matrix"]["selected_rows"]
    expected_row_hash = witness["source_full_matrix"]["selected_rows_sha256"]
    if canonical_hash(row_words) != expected_row_hash:
        raise ValueError("R203 source row hash mismatch")
    labels, columns, output_words, matrix_hash = source.symbolic_matrix(
        4, ENGINEERING_COUPLING
    )
    if witness["source_symbolic_matrix_sha256"] != matrix_hash:
        raise ValueError("R203 source symbolic matrix hash mismatch")
    if witness["candidate_labels_sha256"] != canonical_hash(labels):
        raise ValueError("R203 candidate-label hash mismatch")
    if len(row_words) != len(columns) or not set(row_words).issubset(output_words):
        raise ValueError("R203 selected rows do not define a maximal source minor")
    zero = sp.Poly(0, *source.VARS, domain=sp.ZZ)
    entries = [
        columns[column].get(word, zero).as_expr()
        for word in row_words
        for column in range(len(columns))
    ]
    return entries, {
        "source_r203_sha256": sha256_file(r203_path),
        "source_witness_index": ROW_SOURCE_INDEX,
        "source_witness_point": witness["projective_point"],
        "row_words": row_words,
        "row_words_sha256": expected_row_hash,
        "matrix_sha256": matrix_hash,
        "candidate_labels_sha256": canonical_hash(labels),
        "dimension": len(columns),
    }


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


def compute(root: Path, prime: int, timeout_seconds: int) -> dict[str, Any]:
    if prime < 2 or not sp.isprime(prime):
        raise ValueError("--prime must be prime")
    singular = shutil.which("Singular")
    if singular is None:
        raise RuntimeError("Singular executable not found")
    entries, record = matrix_and_record(root)
    script = singular_bridge.singular_script(entries, record["dimension"], prime)
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
    d_terms = modular.sparse_to_payload(d_sparse, prime)
    d_hash = canonical_hash(d_terms)
    d_factor_rows = [
        factor
        for factor in factors
        if factor["normalized_terms_sha256"] == d_hash
    ]
    exact_d44_factor = bool(
        len(d_factor_rows) == 1 and d_factor_rows[0]["multiplicity"] >= 44
    )
    quotient_sparse: modular.SparsePolynomial = {(0, 0, 0): 1}
    factor_summary = []
    for factor in factors:
        multiplicity = factor["multiplicity"]
        if factor["normalized_terms_sha256"] == d_hash:
            multiplicity -= 44
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
        modular.sparse_power(d_sparse, 44, prime),
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
    recomposed = modular.sparse_multiply(
        quotient_sparse,
        modular.sparse_power(d_sparse, 44, prime),
        prime,
    )
    scaled_recomposition_validated = bool(
        recomposed == determinant_sparse
    )
    exact_d44_division_verified = bool(
        exact_d44_factor
        and factorization_validated
        and scaled_recomposition_validated
    )
    quotient_terms = modular.sparse_to_payload(quotient_sparse, prime)
    quotient_total_degree = max(
        sum(monomial) for monomial in quotient_sparse
    )
    replay_points = [(2, 0, 1), (1, 0, -2)]
    point_rows = []
    for point in replay_points:
        substitutions = dict(zip(source.VARS, point))
        direct_integer = direct_matrix_determinant(
            entries, record["dimension"], point
        )
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
                "quotient_nonzero": quotient_value != 0,
                "D_power_recomposition_match": polynomial_value
                == quotient_value * pow(d_value, 44, prime) % prime,
            }
        )
    checked = bool(
        determinant.total_degree() == 184
        and quotient_total_degree == 96
        and exact_d44_division_verified
        and all(row["determinant_replay_match"] for row in point_rows)
        and all(row["quotient_nonzero"] for row in point_rows)
        and all(row["D_power_recomposition_match"] for row in point_rows)
    )
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_engineering_added_minor_only",
        "coupling": "13/32",
        "coefficient_domain": f"GF({prime})",
        "characteristic": prime,
        "n": 4,
        "new_minor_index": NEW_MINOR_INDEX,
        **record,
        "singular_path": singular,
        "singular_version": subprocess.check_output(
            [singular, "--version"], text=True
        ).splitlines()[0],
        "bridge_tool_sha256": sha256_file(Path(__file__).resolve()),
        "source_independent_audit_tool_sha256": sha256_file(
            root / "tools/b9_r201_independent_audit.py"
        ),
        "singular_input_sha256": hashlib.sha256(script.encode()).hexdigest(),
        "determinant_total_degree": determinant.total_degree(),
        "determinant_term_count": len(determinant_terms),
        "determinant_canonical_terms": determinant_terms,
        "determinant_canonical_terms_sha256": canonical_hash(determinant_terms),
        "factorization_input_sha256": factorization_input_sha256,
        "factorization_rows": factor_summary,
        "factorization_validated": factorization_validated,
        "factorization_nonzero_scalar": factorization_scalar,
        "scaled_recomposition_validated": scaled_recomposition_validated,
        "D_factor_normalized_terms_sha256": d_hash,
        "D_exponent": 44,
        "exact_D44_division_verified": exact_d44_division_verified,
        "quotient_total_degree": quotient_total_degree,
        "quotient_term_count": len(quotient_terms),
        "quotient_canonical_terms": quotient_terms,
        "quotient_canonical_terms_sha256": canonical_hash(quotient_terms),
        "remainder_term_count": 0 if exact_d44_division_verified else None,
        "remainder_canonical_terms_sha256": canonical_hash([])
        if exact_d44_division_verified
        else None,
        "point_replays": point_rows,
        "both_R203_rational_artifacts_excluded": all(
            row["quotient_nonzero"] for row in point_rows
        ),
        "elapsed_seconds": round(elapsed, 6),
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
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    result = compute(root, args.prime, args.timeout_seconds)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "prime": result["characteristic"],
                "determinant_term_count": result["determinant_term_count"],
                "quotient_term_count": result["quotient_term_count"],
                "both_R203_rational_artifacts_excluded": result[
                    "both_R203_rational_artifacts_excluded"
                ],
                "elapsed_seconds": result["elapsed_seconds"],
                "checked": result["checked"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
