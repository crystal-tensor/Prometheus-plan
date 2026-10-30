#!/usr/bin/env python3
"""Independently replay and factor the eight public R201 modular minors."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import sympy as sp

import b9_r201_projective_patch_certificate as r201
import b9_r201_singular_minor_bridge as bridge


VERSION = "0.1.0"
METHOD = "b9_r201_project_owned_modular_minor_structure_v1"
PRIMES = (1_000_003, 536_870_723)
MINOR_INDICES = range(4)
REPLAY_POINTS = (
    (1, 0, 1),
    (1, 1, 1),
    (2, -1, 1),
    (-1, 2, 3),
    (3, 1, -2),
)
FACTOR_BEGIN = "R201_FACTOR_BEGIN"
FACTOR_END = "R201_FACTOR_END"


SparsePolynomial = dict[tuple[int, int, int], int]


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_to_sparse(payload: list[list[Any]], prime: int) -> SparsePolynomial:
    polynomial = {
        tuple(int(exponent) for exponent in monomial): int(coefficient) % prime
        for monomial, coefficient in payload
    }
    return {
        monomial: coefficient
        for monomial, coefficient in polynomial.items()
        if coefficient
    }


def sparse_to_payload(polynomial: SparsePolynomial, prime: int) -> list[list[Any]]:
    return [
        [list(monomial), str(coefficient % prime)]
        for monomial, coefficient in sorted(polynomial.items(), reverse=True)
        if coefficient % prime
    ]


def normalize_sparse(polynomial: SparsePolynomial, prime: int) -> SparsePolynomial:
    polynomial = {
        monomial: coefficient % prime
        for monomial, coefficient in polynomial.items()
        if coefficient % prime
    }
    if not polynomial:
        return {}
    leading = max(polynomial)
    inverse = pow(polynomial[leading], -1, prime)
    return {
        monomial: coefficient * inverse % prime
        for monomial, coefficient in polynomial.items()
    }


def sparse_multiply(
    left: SparsePolynomial, right: SparsePolynomial, prime: int
) -> SparsePolynomial:
    product: SparsePolynomial = {}
    for left_monomial, left_coefficient in left.items():
        for right_monomial, right_coefficient in right.items():
            monomial = tuple(
                left_monomial[index] + right_monomial[index] for index in range(3)
            )
            product[monomial] = (
                product.get(monomial, 0)
                + left_coefficient * right_coefficient
            ) % prime
    return {
        monomial: coefficient
        for monomial, coefficient in product.items()
        if coefficient
    }


def sparse_power(
    polynomial: SparsePolynomial, exponent: int, prime: int
) -> SparsePolynomial:
    result: SparsePolynomial = {(0, 0, 0): 1}
    base = polynomial
    while exponent:
        if exponent & 1:
            result = sparse_multiply(result, base, prime)
        exponent >>= 1
        if exponent:
            base = sparse_multiply(base, base, prime)
    return result


def evaluate_sparse(
    polynomial: SparsePolynomial, point: tuple[int, int, int], prime: int
) -> int:
    a, b, c = (value % prime for value in point)
    return sum(
        coefficient
        * pow(a, monomial[0], prime)
        * pow(b, monomial[1], prime)
        * pow(c, monomial[2], prime)
        for monomial, coefficient in polynomial.items()
    ) % prime


def evaluate_expression(
    expression: sp.Expr, point: tuple[int, int, int], prime: int
) -> int:
    value = sp.cancel(expression.subs(dict(zip(r201.VARS, point))))
    numerator, denominator = sp.fraction(value)
    numerator_integer = int(numerator)
    denominator_integer = int(denominator)
    return (
        numerator_integer
        % prime
        * pow(denominator_integer % prime, -1, prime)
        % prime
    )


def determinant_mod(matrix: list[list[int]], prime: int) -> int:
    work = [[value % prime for value in row] for row in matrix]
    determinant = 1
    for column in range(len(work)):
        pivot = next(
            (row for row in range(column, len(work)) if work[row][column]),
            None,
        )
        if pivot is None:
            return 0
        if pivot != column:
            work[column], work[pivot] = work[pivot], work[column]
            determinant = -determinant
        pivot_value = work[column][column]
        determinant = determinant * pivot_value % prime
        inverse = pow(pivot_value, -1, prime)
        for row in range(column + 1, len(work)):
            if not work[row][column]:
                continue
            multiplier = work[row][column] * inverse % prime
            for inner_column in range(column + 1, len(work)):
                work[row][inner_column] = (
                    work[row][inner_column]
                    - multiplier * work[column][inner_column]
                ) % prime
    return determinant % prime


def singular_polynomial(polynomial: SparsePolynomial, prime: int) -> str:
    terms = []
    for monomial, coefficient in sorted(polynomial.items(), reverse=True):
        coefficient %= prime
        pieces = [str(coefficient)]
        for variable, exponent in zip(("a", "b", "c"), monomial):
            if exponent:
                pieces.append(variable if exponent == 1 else f"{variable}{exponent}")
        terms.append("*".join(pieces))
    return "+".join(terms) or "0"


def parse_factor_output(stdout: str, prime: int) -> list[dict[str, Any]]:
    factors = []
    pattern = re.compile(
        rf"{FACTOR_BEGIN}\s+(\d+)\s+(\d+)\s+(.*?)\s+{FACTOR_END}",
        re.DOTALL,
    )
    for match in pattern.finditer(stdout):
        index = int(match.group(1))
        multiplicity = int(match.group(2))
        polynomial = bridge.parse_polynomial(
            f"{bridge.BEGIN_MARKER}\n{match.group(3)}\n{bridge.END_MARKER}",
            prime,
        )
        sparse = normalize_sparse(
            payload_to_sparse(bridge.polynomial_payload(polynomial, prime), prime),
            prime,
        )
        payload = sparse_to_payload(sparse, prime)
        factors.append(
            {
                "index": index,
                "multiplicity": multiplicity,
                "degree": polynomial.total_degree(),
                "term_count": len(sparse),
                "normalized_terms": payload,
                "normalized_terms_sha256": canonical_hash(payload),
            }
        )
    if not factors:
        raise RuntimeError("Singular emitted no parseable nonconstant factors")
    return factors


def factor_with_singular(
    polynomial: SparsePolynomial, prime: int
) -> tuple[list[dict[str, Any]], str]:
    singular = shutil.which("Singular")
    if singular is None:
        raise RuntimeError("Singular executable not found")
    script = "\n".join(
        [
            f"ring r={prime},(a,b,c),dp;",
            f"poly f={singular_polynomial(polynomial, prime)};",
            "list L=factorize(f,2);",
            "int i;",
            "for (i=1;i<=size(L[1]);i++) {",
            f'  print("{FACTOR_BEGIN}");',
            "  print(i);",
            "  print(L[2][i]);",
            "  print(string(L[1][i]));",
            f'  print("{FACTOR_END}");',
            "}",
            "quit;",
        ]
    ) + "\n"
    completed = subprocess.run(
        [singular, "-q"],
        input=script,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=1800,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Singular factorization failed with {completed.returncode}: "
            f"{completed.stderr[-4000:]}"
        )
    return parse_factor_output(completed.stdout, prime), hashlib.sha256(script.encode()).hexdigest()


def validate_factorization(
    polynomial: SparsePolynomial, factors: list[dict[str, Any]], prime: int
) -> bool:
    reconstructed: SparsePolynomial = {(0, 0, 0): 1}
    for factor in factors:
        sparse = payload_to_sparse(factor["normalized_terms"], prime)
        reconstructed = sparse_multiply(
            reconstructed,
            sparse_power(sparse, factor["multiplicity"], prime),
            prime,
        )
    return normalize_sparse(reconstructed, prime) == normalize_sparse(polynomial, prime)


def replay_artifact(
    path: Path,
    matrix_entries: list[sp.Expr],
    record: dict[str, Any],
    expected_bridge_hash: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    artifact = json.loads(path.read_text())
    prime = artifact["characteristic"]
    polynomial = payload_to_sparse(artifact["canonical_terms"], prime)
    validation_errors = []
    expectations = {
        "method": bridge.METHOD,
        "version": bridge.VERSION,
        "mode": "public_engineering_coupling_only",
        "coupling": "13/32",
        "n": 4,
        "dimension": 37,
        "minor_index": artifact["minor_index"],
        "row_words_sha256": record["row_words_sha256"],
        "matrix_sha256": record["matrix_sha256"],
        "candidate_labels_sha256": record["candidate_labels_sha256"],
        "bridge_tool_sha256": expected_bridge_hash,
        "total_degree": 184,
        "term_count": len(polynomial),
        "canonical_terms_sha256": canonical_hash(artifact["canonical_terms"]),
        "frozen_holdouts_executed": False,
        "integer_engineering_certificate_verified": False,
        "modular_bridge_validation_only": True,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    for field, expected in expectations.items():
        if artifact.get(field) != expected:
            validation_errors.append(field)
    if artifact.get("characteristic") not in PRIMES or artifact.get("checked") is not True:
        validation_errors.append("characteristic_or_checked")

    dimension = record["dimension"]
    point_replays = []
    for point in REPLAY_POINTS:
        evaluated = [
            evaluate_expression(expression, point, prime) for expression in matrix_entries
        ]
        matrix = [
            evaluated[offset : offset + dimension]
            for offset in range(0, len(evaluated), dimension)
        ]
        polynomial_value = evaluate_sparse(polynomial, point, prime)
        matrix_value = determinant_mod(matrix, prime)
        point_replays.append(
            {
                "point": list(point),
                "D_mod_prime": sum(value * value for value in point) % prime,
                "polynomial_value": polynomial_value,
                "matrix_determinant": matrix_value,
                "match": polynomial_value == matrix_value,
            }
        )

    factors, factor_input_hash = factor_with_singular(polynomial, prime)
    factorization_replayed = validate_factorization(polynomial, factors, prime)
    D_hash = canonical_hash(
        sparse_to_payload({(2, 0, 0): 1, (0, 2, 0): 1, (0, 0, 2): 1}, prime)
    )
    D_multiplicity = sum(
        factor["multiplicity"]
        for factor in factors
        if factor["normalized_terms_sha256"] == D_hash
    )
    D_removed: SparsePolynomial = {(0, 0, 0): 1}
    for factor in factors:
        if factor["normalized_terms_sha256"] == D_hash:
            continue
        sparse = payload_to_sparse(factor["normalized_terms"], prime)
        D_removed = sparse_multiply(
            D_removed,
            sparse_power(sparse, factor["multiplicity"], prime),
            prime,
        )
    summary = {
        "path": str(Path(*path.parts[-2:])),
        "artifact_sha256": sha256_file(path),
        "prime": prime,
        "minor_index": artifact["minor_index"],
        "row_words_sha256": artifact["row_words_sha256"],
        "total_degree": artifact["total_degree"],
        "term_count": artifact["term_count"],
        "canonical_terms_sha256": artifact["canonical_terms_sha256"],
        "artifact_binding_errors": validation_errors,
        "point_replays": point_replays,
        "point_replay_match_count": sum(row["match"] for row in point_replays),
        "nonzero_point_count": sum(
            row["matrix_determinant"] != 0 for row in point_replays
        ),
        "singular_factor_input_sha256": factor_input_hash,
        "factorization_replayed": factorization_replayed,
        "D_multiplicity": D_multiplicity,
        "D_removed_degree": max(sum(monomial) for monomial in D_removed),
        "D_removed_term_count": len(D_removed),
        "factor_degree_multiplicity": sorted(
            [[factor["degree"], factor["multiplicity"]] for factor in factors]
        ),
        "factor_count": len(factors),
        "factor_records": [
            {
                key: factor[key]
                for key in (
                    "degree",
                    "multiplicity",
                    "term_count",
                    "normalized_terms_sha256",
                )
            }
            for factor in factors
        ],
    }
    return summary, factors


def cross_prime_support_check(root: Path, minor_index: int) -> bool:
    supports = []
    for prime in PRIMES:
        path = (
            root
            / "results"
            / f"B9_R201_singular_minor{minor_index}_mod{prime}_v0.json"
        )
        artifact = json.loads(path.read_text())
        supports.append(
            [tuple(row[0]) for row in artifact["canonical_terms"]]
        )
    return supports[0] == supports[1]


def build_result(root: Path) -> dict[str, Any]:
    matrices, records = bridge.engineering_row_sets()
    if len(matrices) != 4 or len(records) != 4:
        raise RuntimeError("expected exactly four frozen R201 engineering minors")
    bridge_hash = sha256_file(root / "tools" / "b9_r201_singular_minor_bridge.py")
    rows = []
    factor_maps: dict[int, list[dict[str, int]]] = {}
    for prime in PRIMES:
        factor_sets: list[dict[str, int]] = []
        factor_lookup: dict[str, dict[str, Any]] = {}
        for minor_index in MINOR_INDICES:
            path = (
                root
                / "results"
                / f"B9_R201_singular_minor{minor_index}_mod{prime}_v0.json"
            )
            row, factors = replay_artifact(
                path, matrices[minor_index], records[minor_index], bridge_hash
            )
            rows.append(row)
            factor_sets.append(
                {
                    factor["normalized_terms_sha256"]: factor["multiplicity"]
                    for factor in factors
                }
            )
            factor_lookup.update(
                {
                    factor["normalized_terms_sha256"]: factor
                    for factor in factors
                }
            )
        common_hashes = set(factor_sets[0])
        for factor_set in factor_sets[1:]:
            common_hashes &= set(factor_set)
        common = [
            {
                "normalized_terms_sha256": factor_hash,
                "multiplicity": min(
                    factor_set[factor_hash] for factor_set in factor_sets
                ),
            }
            for factor_hash in sorted(common_hashes)
        ]
        for item in common:
            factor = factor_lookup[item["normalized_terms_sha256"]]
            item["degree"] = factor["degree"]
            item["term_count"] = factor["term_count"]
        factor_maps[prime] = common

    support_checks = {
        str(minor_index): cross_prime_support_check(root, minor_index)
        for minor_index in MINOR_INDICES
    }
    all_replays_match = all(
        row["point_replay_match_count"] == len(REPLAY_POINTS) for row in rows
    )
    all_factorizations_replay = all(row["factorization_replayed"] for row in rows)
    all_bindings_clean = all(not row["artifact_binding_errors"] for row in rows)
    all_have_nonzero_point = all(row["nonzero_point_count"] > 0 for row in rows)
    prime_patterns_match = all(
        next(
            row
            for row in rows
            if row["prime"] == PRIMES[0] and row["minor_index"] == index
        )["factor_degree_multiplicity"]
        == next(
            row
            for row in rows
            if row["prime"] == PRIMES[1] and row["minor_index"] == index
        )["factor_degree_multiplicity"]
        for index in MINOR_INDICES
    )
    checked = (
        all_replays_match
        and all_factorizations_replay
        and all_bindings_clean
        and all_have_nonzero_point
        and all(support_checks.values())
    )
    return {
        "method": METHOD,
        "version": VERSION,
        "date": "2026-10-31",
        "scope": "public_engineering_modular_minor_structure_only",
        "primes": list(PRIMES),
        "safe_prime": 536_870_723,
        "safe_prime_half": 268_435_361,
        "minor_count": 4,
        "artifact_count": len(rows),
        "artifact_bundle_sha256": canonical_hash(
            [
                {
                    "path": row["path"],
                    "artifact_sha256": row["artifact_sha256"],
                }
                for row in rows
            ]
        ),
        "replay_points": [list(point) for point in REPLAY_POINTS],
        "rows": rows,
        "cross_prime_monomial_support_match": support_checks,
        "cross_prime_factor_degree_multiplicity_match": prime_patterns_match,
        "common_factors_by_prime": {str(prime): factor_maps[prime] for prime in PRIMES},
        "common_gcd_degree_by_prime": {
            str(prime): sum(
                factor["degree"] * factor["multiplicity"]
                for factor in factor_maps[prime]
            )
            for prime in PRIMES
        },
        "all_artifact_bindings_clean": all_bindings_clean,
        "all_point_replays_match": all_replays_match,
        "all_factorizations_replay": all_factorizations_replay,
        "all_minors_have_nonzero_public_replay_point": all_have_nonzero_point,
        "bounded_CRT_integer_reconstruction_complete": False,
        "integer_coefficient_bound_proved": False,
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
    result = build_result(root)
    output = args.output if args.output.is_absolute() else root / args.output
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "artifact_count": result["artifact_count"],
                "all_point_replays_match": result["all_point_replays_match"],
                "all_factorizations_replay": result["all_factorizations_replay"],
                "cross_prime_factor_degree_multiplicity_match": result[
                    "cross_prime_factor_degree_multiplicity_match"
                ],
                "checked": result["checked"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
