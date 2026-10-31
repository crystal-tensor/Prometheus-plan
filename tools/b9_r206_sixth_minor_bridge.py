#!/usr/bin/env python3
"""Lift the R205 Pauli rank witness into the sixth full projective minor."""

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
import b9_r202_modular_ideal_preflight as r202


METHOD = "b9_r206_r205_selected_rows_sixth_minor_bridge_v1"
VERSION = "0.1.0"
R205_PATH = Path("results/B9_R205_sextic_full_matrix_rank_v0.json")
R204_PREFLIGHT_PATH = Path("results/B9_R204_expanded_ideal_preflight_v0.json")
R201_PATH = Path("results/B9_R201_integer_reconstruction_v0.json")
R204_PATHS = {
    1_000_003: Path("results/B9_R204_added_minor_mod1000003_v0.json"),
    536_870_723: Path("results/B9_R204_added_minor_mod536870723_v0.json"),
}
SOURCE_REPRESENTATION = "independent_sparse_Pauli_word_matrix"
NEW_MINOR_INDEX = 5
ENGINEERING_COUPLING = Fraction(13, 32)
T = sp.symbols("t")
SEXTIC = sp.Poly(
    768 * T**6
    - 256 * T**5
    - 7227 * T**4
    + 5120 * T**3
    + 7227 * T**2
    - 256 * T
    - 768,
    T,
    domain=sp.ZZ,
)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_hash_valid(result: dict[str, Any]) -> bool:
    payload = dict(result)
    expected = payload.pop("payload_sha256", None)
    return expected is not None and canonical_hash(payload) == expected


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


def slice_polynomial_from_terms(
    terms: list[list[Any]], prime: int
) -> sp.Poly:
    expression = sp.Integer(0)
    for monomial, coefficient in terms:
        a_degree, b_degree, _ = monomial
        if b_degree == 0:
            expression += (int(coefficient) % prime) * T**a_degree
    return sp.Poly(expression, T, modulus=prime)


def validate_sources(
    root: Path, prime: int
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    paths = {
        "r201": root / R201_PATH,
        "r204_preflight": root / R204_PREFLIGHT_PATH,
        "r204_fifth": root / R204_PATHS[prime],
        "r205": root / R205_PATH,
    }
    results = {label: json.loads(path.read_text()) for label, path in paths.items()}
    if not all(
        payload_hash_valid(results[label])
        for label in ("r204_preflight", "r204_fifth", "r205")
    ):
        raise ValueError("R204/R205 source payload hash mismatch")

    r201 = results["r201"]
    r204_preflight = results["r204_preflight"]
    r204_fifth = results["r204_fifth"]
    r205 = results["r205"]
    expected_sextic_terms = [
        [[6], "768"],
        [[5], "-256"],
        [[4], "-7227"],
        [[3], "5120"],
        [[2], "7227"],
        [[1], "-256"],
        [[0], "-768"],
    ]
    if (
        r201.get("method")
        != "b9_r201_bounded_integer_reconstruction_and_D44_division_v2"
        or r201.get("checked") is not True
        or len(r201.get("rows", [])) != 4
        or r201.get("characteristic_zero_D44_divisibility_verified") is not True
        or r201.get("primitive_quotient_gcd_is_unit") is not True
        or r204_preflight.get("checked") is not True
        or r204_preflight.get("primes") != [1_000_003, 536_870_723]
        or r204_preflight.get("expanded_slice_gcd_total_degree") != 6
        or r204_preflight.get("expanded_slice_matches_R203_residual_degree_six")
        is not True
        or r204_preflight.get("added_minor_result_sha256", {}).get(str(prime))
        != sha256_file(paths["r204_fifth"])
        or r204_fifth.get("checked") is not True
        or r204_fifth.get("characteristic") != prime
        or r204_fifth.get("new_minor_index") != 4
        or r204_fifth.get("both_R203_rational_artifacts_excluded") is not True
        or r205.get("checked") is not True
        or r205.get("sextic_canonical_terms") != expected_sextic_terms
        or r205.get("source_sha256", {}).get("r204")
        != sha256_file(paths["r204_preflight"])
    ):
        raise ValueError("R201/R204/R205 source semantics mismatch")
    return r201, r204_preflight, r204_fifth, r205


def five_minor_slice_replay(
    r201: dict[str, Any], r204_fifth: dict[str, Any], prime: int
) -> dict[str, Any]:
    quotient_sets = [
        r202.primitive_quotient_terms(row) for row in r201["rows"]
    ]
    quotient_sets.append(r204_fifth["quotient_canonical_terms"])
    slice_polynomials = [
        slice_polynomial_from_terms(terms, prime) for terms in quotient_sets
    ]
    gcd = slice_polynomials[0]
    for polynomial in slice_polynomials[1:]:
        gcd = sp.gcd(gcd, polynomial)
    gcd = gcd.monic()
    sextic = sp.Poly(SEXTIC.as_expr(), T, modulus=prime).monic()
    coefficients = [int(gcd.nth(index)) % prime for index in range(7)]
    return {
        "five_minor_slice_gcd_degree": gcd.degree(),
        "five_minor_slice_gcd_coefficients_low_to_high": coefficients,
        "five_minor_slice_gcd_sha256": canonical_hash(coefficients),
        "five_minor_slice_gcd_matches_R204_sextic": gcd == sextic,
    }


def matrix_and_record(root: Path) -> tuple[list[sp.Expr], dict[str, Any]]:
    r205_path = root / R205_PATH
    r205 = json.loads(r205_path.read_text())
    certificates = [
        row
        for row in r205.get("representation_certificates", [])
        if row.get("representation") == SOURCE_REPRESENTATION
    ]
    if (
        r205.get("checked") is not True
        or r205.get(
            "all_six_real_sextic_points_full_rank_in_both_representations"
        )
        is not True
        or len(certificates) != 1
    ):
        raise ValueError("R205 Pauli rank certificate is not accepted")
    certificate = certificates[0]
    row_words = certificate["selected_rows"]
    expected_row_hash = certificate["selected_rows_sha256"]
    if canonical_hash(row_words) != expected_row_hash:
        raise ValueError("R205 selected-row hash mismatch")

    labels, columns, output_words, matrix_hash = source.symbolic_matrix(
        4, ENGINEERING_COUPLING
    )
    if certificate["parent_symbolic_matrix_sha256"] != matrix_hash:
        raise ValueError("R205 source symbolic matrix hash mismatch")
    if certificate["candidate_labels_sha256"] != canonical_hash(labels):
        raise ValueError("R205 candidate-label hash mismatch")
    if len(row_words) != len(columns) or not set(row_words).issubset(output_words):
        raise ValueError("R205 selected rows do not define a maximal source minor")

    zero = sp.Poly(0, *source.VARS, domain=sp.ZZ)
    entries = [
        columns[column].get(word, zero).as_expr()
        for word in row_words
        for column in range(len(columns))
    ]
    return entries, {
        "source_r205_sha256": sha256_file(r205_path),
        "source_representation": SOURCE_REPRESENTATION,
        "row_words": row_words,
        "row_words_sha256": expected_row_hash,
        "matrix_sha256": matrix_hash,
        "candidate_labels_sha256": canonical_hash(labels),
        "dimension": len(columns),
    }


def slice_sextic_replay(result: dict[str, Any], prime: int) -> dict[str, Any]:
    slice_polynomial = slice_polynomial_from_terms(
        result["quotient_canonical_terms"], prime
    )
    sextic = sp.Poly(SEXTIC.as_expr(), T, modulus=prime)
    gcd = sp.gcd(slice_polynomial, sextic).monic()
    remainder = slice_polynomial.rem(sextic)
    coefficients = [int(remainder.nth(index)) % prime for index in range(6)]
    gcd_terms = [
        [[int(monomial[0])], str(int(coefficient) % prime)]
        for monomial, coefficient in gcd.terms()
        if int(coefficient) % prime
    ]
    return {
        "slice_quotient_total_degree": slice_polynomial.degree(),
        "sympy_version": sp.__version__,
        "slice_quotient_gcd_with_R204_sextic_degree": gcd.degree(),
        "slice_quotient_gcd_with_R204_sextic_terms": gcd_terms,
        "slice_quotient_gcd_with_R204_sextic_sha256": canonical_hash(gcd_terms),
        "slice_quotient_remainder_mod_sextic_coefficients_low_to_high": coefficients,
        "slice_quotient_remainder_mod_sextic_sha256": canonical_hash(coefficients),
        "R204_sextic_excluded_mod_prime": gcd.degree() == 0,
    }


def compute(root: Path, prime: int, timeout_seconds: int) -> dict[str, Any]:
    if prime not in R204_PATHS:
        raise ValueError("R206 requires one of the two R204 classification primes")
    if not sp.isprime(prime):
        raise ValueError("--prime must be prime")
    r201, r204_preflight, r204_fifth, _ = validate_sources(root, prime)
    five_minor_slice = five_minor_slice_replay(r201, r204_fifth, prime)
    if five_minor_slice["five_minor_slice_gcd_matches_R204_sextic"] is not True:
        raise ValueError("direct five-minor slice replay does not recover the sextic")

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
    scaled_recomposition_validated = recomposed == determinant_sparse
    exact_d44_division_verified = bool(
        exact_d44_factor
        and factorization_validated
        and scaled_recomposition_validated
    )
    quotient_terms = modular.sparse_to_payload(quotient_sparse, prime)
    quotient_total_degree = max(sum(monomial) for monomial in quotient_sparse)

    replay_specs = [
        ((2, 0, 1), False, "R203_rational_artifact_A"),
        ((1, 0, -2), False, "R203_rational_artifact_B"),
        ((1, 1, 1), True, "positive_control_A"),
        ((3, 2, 1), True, "positive_control_B"),
    ]
    point_rows = []
    for point, require_nonzero, label in replay_specs:
        direct_integer = direct_matrix_determinant(
            entries, record["dimension"], point
        )
        polynomial_value = sparse_evaluate(determinant_sparse, point, prime)
        quotient_value = sparse_evaluate(quotient_sparse, point, prime)
        d_value = sum(value * value for value in point) % prime
        point_rows.append(
            {
                "label": label,
                "projective_point": list(point),
                "require_nonzero": require_nonzero,
                "D_mod_prime": d_value,
                "direct_integer_determinant_sha256": hashlib.sha256(
                    str(direct_integer).encode()
                ).hexdigest(),
                "direct_integer_determinant_nonzero": direct_integer != 0,
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

    result: dict[str, Any] = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R205_selected_rows_sixth_projective_minor_only",
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
        "r204_bridge_algorithm_lineage_sha256": sha256_file(
            root / "tools/b9_r204_expanded_minor_bridge.py"
        ),
        "modular_polynomial_dependency_sha256": sha256_file(
            root / "tools/b9_r201_modular_minor_structure.py"
        ),
        "singular_bridge_dependency_sha256": sha256_file(
            root / "tools/b9_r201_singular_minor_bridge.py"
        ),
        "source_r205_tool_sha256": sha256_file(
            root / "tools/b9_r205_sextic_full_matrix_rank.py"
        ),
        "source_r201_result_sha256": sha256_file(root / R201_PATH),
        "source_r204_preflight_result_sha256": sha256_file(
            root / R204_PREFLIGHT_PATH
        ),
        "source_r204_fifth_minor_result_sha256": sha256_file(
            root / R204_PATHS[prime]
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
        "sixth_minor_alone_excludes_R203_rational_artifacts": all(
            row["quotient_nonzero"] for row in point_rows[:2]
        ),
        "positive_nonzero_replay_count": sum(
            row["quotient_nonzero"] for row in point_rows if row["require_nonzero"]
        ),
        **five_minor_slice,
        "elapsed_seconds": round(elapsed, 6),
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    result.update(slice_sextic_replay(result, prime))
    result["bridge_structural_checks_passed"] = bool(
        result["determinant_total_degree"] == 184
        and result["quotient_total_degree"] == 96
        and result["exact_D44_division_verified"]
        and result["factorization_validated"]
        and result["scaled_recomposition_validated"]
        and all(
            row["determinant_replay_match"]
            and row["D_power_recomposition_match"]
            and (not row["require_nonzero"] or row["quotient_nonzero"])
            for row in point_rows
        )
    )
    result[
        "combined_R204_fifth_plus_R206_sixth_excludes_known_b_zero_components"
    ] = bool(
        r204_preflight["expanded_slice_matches_R203_residual_degree_six"]
        and result["five_minor_slice_gcd_matches_R204_sextic"]
        and result["R204_sextic_excluded_mod_prime"]
    )
    result["checked"] = bool(
        result["bridge_structural_checks_passed"]
        and result[
            "combined_R204_fifth_plus_R206_sixth_excludes_known_b_zero_components"
        ]
    )
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
                "sextic_gcd_degree": result[
                    "slice_quotient_gcd_with_R204_sextic_degree"
                ],
                "combined_known_b_zero_components_excluded": result[
                    "combined_R204_fifth_plus_R206_sixth_excludes_known_b_zero_components"
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
