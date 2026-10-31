#!/usr/bin/env python3
"""Replay completed R201 modular determinant shards and hash partial CRT state."""

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
METHOD = "b9_r201_incremental_modular_CRT_shard_replay_v1"
EXISTING_PRIMES = (1_000_003, 536_870_723)
REPLAY_POINTS = (
    (1, 0, 1),
    (1, 1, 1),
    (2, -1, 1),
    (-1, 2, 3),
    (3, 1, -2),
)
DEGREE = 184
DIMENSION = 37


SparsePolynomial = dict[tuple[int, int, int], int]


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_to_sparse(payload: list[list[Any]], prime: int) -> SparsePolynomial:
    return {
        tuple(int(exponent) for exponent in monomial): int(coefficient) % prime
        for monomial, coefficient in payload
        if int(coefficient) % prime
    }


def evaluate_sparse(
    polynomial: SparsePolynomial, point: tuple[int, int, int], prime: int
) -> int:
    coordinates = tuple(value % prime for value in point)
    return sum(
        coefficient
        * math.prod(
            pow(coordinates[index], monomial[index], prime) for index in range(3)
        )
        for monomial, coefficient in polynomial.items()
    ) % prime


def evaluate_expression(
    expression: sp.Expr, point: tuple[int, int, int], prime: int
) -> int:
    value = sp.cancel(expression.subs(dict(zip(r201.VARS, point))))
    numerator, denominator = sp.fraction(value)
    return (
        int(numerator) % prime * pow(int(denominator) % prime, -1, prime) % prime
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
            if work[row][column] == 0:
                continue
            multiplier = work[row][column] * inverse % prime
            for inner_column in range(column + 1, len(work)):
                work[row][inner_column] = (
                    work[row][inner_column]
                    - multiplier * work[column][inner_column]
                ) % prime
    return determinant % prime


def homogeneous_lattice(degree: int) -> list[tuple[int, int, int]]:
    return sorted(
        (
            (a_exponent, b_exponent, degree - a_exponent - b_exponent)
            for a_exponent in range(degree + 1)
            for b_exponent in range(degree - a_exponent + 1)
        ),
        reverse=True,
    )


def symmetric_crt(residues: list[int], primes: list[int]) -> int:
    value = 0
    modulus = 1
    for residue, prime in zip(residues, primes):
        step = (residue - value) % prime
        step = step * pow(modulus, -1, prime) % prime
        value += modulus * step
        modulus *= prime
    if value > modulus // 2:
        value -= modulus
    return value


def artifact_path(root: Path, minor_index: int, prime: int) -> Path:
    return root / f"results/B9_R201_singular_minor{minor_index}_mod{prime}_v0.json"


def discover_completed_primes(
    root: Path, planned_primes: list[int]
) -> tuple[list[int], list[int]]:
    completed = []
    partial = []
    for prime in planned_primes:
        count = sum(artifact_path(root, index, prime).exists() for index in range(4))
        if count == 4:
            completed.append(prime)
        elif count:
            partial.append(prime)
    return completed, partial


def replay_artifact(
    root: Path,
    path: Path,
    expected_prime: int,
    expected_index: int,
    matrix_entries: list[sp.Expr],
    matrix_record: dict[str, Any],
    bridge_hash: str,
    reference_artifact: dict[str, Any],
) -> tuple[dict[str, Any], SparsePolynomial]:
    artifact = json.loads(path.read_text())
    polynomial = payload_to_sparse(artifact.get("canonical_terms", []), expected_prime)
    support = sorted(polynomial, reverse=True)
    point_rows = []
    for point in REPLAY_POINTS:
        matrix = [
            [
                evaluate_expression(
                    matrix_entries[row * DIMENSION + column], point, expected_prime
                )
                for column in range(DIMENSION)
            ]
            for row in range(DIMENSION)
        ]
        matrix_value = determinant_mod(matrix, expected_prime)
        polynomial_value = evaluate_sparse(polynomial, point, expected_prime)
        point_rows.append(
            {
                "point": list(point),
                "matrix_determinant": matrix_value,
                "polynomial_value": polynomial_value,
                "match": matrix_value == polynomial_value,
            }
        )
    binding_errors = []
    expected_fields = {
        "method": bridge.METHOD,
        "version": bridge.VERSION,
        "coupling": "13/32",
        "characteristic": expected_prime,
        "n": 4,
        "minor_index": expected_index,
        "dimension": DIMENSION,
        "row_words_sha256": matrix_record["row_words_sha256"],
        "matrix_sha256": matrix_record["matrix_sha256"],
        "candidate_labels_sha256": reference_artifact["candidate_labels_sha256"],
        "bridge_tool_sha256": bridge_hash,
        "total_degree": DEGREE,
        "checked": True,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    for field, expected in expected_fields.items():
        if artifact.get(field) != expected:
            binding_errors.append(
                {"field": field, "expected": expected, "observed": artifact.get(field)}
            )
    if artifact.get("term_count") != len(polynomial):
        binding_errors.append(
            {
                "field": "term_count",
                "expected": len(polynomial),
                "observed": artifact.get("term_count"),
            }
        )
    if artifact.get("canonical_terms_sha256") != canonical_hash(
        artifact.get("canonical_terms", [])
    ):
        binding_errors.append({"field": "canonical_terms_sha256"})
    return (
        {
            "path": str(path.relative_to(root)),
            "artifact_sha256": sha256_file(path),
            "prime": expected_prime,
            "minor_index": expected_index,
            "row_words_sha256": artifact.get("row_words_sha256"),
            "total_degree": artifact.get("total_degree"),
            "term_count": artifact.get("term_count"),
            "monomial_support_sha256": canonical_hash([list(item) for item in support]),
            "point_replay_count": len(point_rows),
            "point_replay_match_count": sum(row["match"] for row in point_rows),
            "point_rows": point_rows,
            "binding_errors": binding_errors,
        },
        polynomial,
    )


def analyze(root: Path) -> dict[str, Any]:
    bound_path = root / "results/B9_R201_determinant_coefficient_bound_v0.json"
    bound = json.loads(bound_path.read_text())
    planned = bound["prime_plan"]["planned_additional_primes"]
    completed, partial = discover_completed_primes(root, planned)
    if partial:
        raise RuntimeError(f"incomplete R201 prime shards exist: {partial}")
    if not completed:
        raise RuntimeError("no completed R201 planned prime shard found")
    if completed != planned[: len(completed)]:
        raise RuntimeError("completed R201 prime shards are not a plan prefix")

    primes = [*EXISTING_PRIMES, *completed]
    if len(set(primes)) != len(primes) or not all(sp.isprime(prime) for prime in primes):
        raise RuntimeError("R201 CRT shard primes must be distinct primes")
    matrices, records = bridge.engineering_row_sets()
    bridge_hash = sha256_file(root / "tools/b9_r201_singular_minor_bridge.py")
    lattice = homogeneous_lattice(DEGREE)
    modulus = math.prod(primes)
    artifact_rows = []
    polynomials_by_minor: dict[int, list[SparsePolynomial]] = {
        index: [] for index in range(4)
    }
    for prime in primes:
        for minor_index in range(4):
            path = artifact_path(root, minor_index, prime)
            reference = json.loads(
                artifact_path(root, minor_index, EXISTING_PRIMES[0]).read_text()
            )
            row, polynomial = replay_artifact(
                root,
                path,
                prime,
                minor_index,
                matrices[minor_index],
                records[minor_index],
                bridge_hash,
                reference,
            )
            artifact_rows.append(row)
            polynomials_by_minor[minor_index].append(polynomial)

    minor_rows = []
    for minor_index in range(4):
        polynomials = polynomials_by_minor[minor_index]
        supports = [set(polynomial) for polynomial in polynomials]
        support_match = all(support == supports[0] for support in supports[1:])
        symmetric_payload = []
        roundtrip_count = 0
        nonzero_count = 0
        maximum_abs = 0
        for monomial in lattice:
            residues = [polynomial.get(monomial, 0) for polynomial in polynomials]
            symmetric = symmetric_crt(residues, primes)
            if symmetric:
                nonzero_count += 1
            maximum_abs = max(maximum_abs, abs(symmetric))
            symmetric_payload.append([list(monomial), str(symmetric)])
            roundtrip_count += sum(
                symmetric % prime == residue
                for prime, residue in zip(primes, residues)
            )
        minor_rows.append(
            {
                "minor_index": minor_index,
                "row_words_sha256": records[minor_index]["row_words_sha256"],
                "cross_prime_monomial_support_match": support_match,
                "modular_support_term_count": len(supports[0]),
                "homogeneous_lattice_size": len(lattice),
                "partial_CRT_nonzero_symmetric_residue_count": nonzero_count,
                "partial_CRT_maximum_absolute_symmetric_residue": str(maximum_abs),
                "partial_CRT_symmetric_payload_sha256": canonical_hash(
                    symmetric_payload
                ),
                "partial_CRT_roundtrip_check_count": roundtrip_count,
                "partial_CRT_roundtrip_expected_count": len(lattice) * len(primes),
                "partial_CRT_roundtrip_complete": (
                    roundtrip_count == len(lattice) * len(primes)
                ),
            }
        )

    all_bindings_clean = all(not row["binding_errors"] for row in artifact_rows)
    all_point_replays_match = all(
        row["point_replay_match_count"] == row["point_replay_count"]
        for row in artifact_rows
    )
    all_supports_match = all(
        row["cross_prime_monomial_support_match"] for row in minor_rows
    )
    all_CRT_roundtrips_complete = all(
        row["partial_CRT_roundtrip_complete"] for row in minor_rows
    )
    planned_count = len(planned)
    completed_count = len(completed)
    twice_bound = 2 * int(bound["maximum_unconditional_coefficient_bound"]["value"])
    plan_complete = completed_count == planned_count
    uniqueness_available = plan_complete and modulus > twice_bound
    phase_boundary_valid = (
        (plan_complete and modulus > twice_bound)
        or (not plan_complete and modulus <= twice_bound)
    )
    checked = (
        all_bindings_clean
        and all_point_replays_match
        and all_supports_match
        and all_CRT_roundtrips_complete
        and phase_boundary_valid
    )
    return {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R201_incremental_modular_CRT_execution_only",
        "coupling": "13/32",
        "n": 4,
        "determinant_degree": DEGREE,
        "dimension": DIMENSION,
        "bound_result_sha256": sha256_file(bound_path),
        "bridge_tool_sha256": bridge_hash,
        "planned_additional_primes": planned,
        "completed_additional_primes": completed,
        "all_CRT_primes": primes,
        "completed_additional_prime_count": completed_count,
        "remaining_additional_prime_count": planned_count - completed_count,
        "completed_additional_minor_artifact_count": completed_count * 4,
        "planned_additional_minor_artifact_count": planned_count * 4,
        "remaining_additional_minor_artifact_count": (planned_count - completed_count)
        * 4,
        "artifact_progress": f"{completed_count * 4}/{planned_count * 4}",
        "partial_CRT_modulus": str(modulus),
        "partial_CRT_modulus_bit_length": modulus.bit_length(),
        "required_twice_bound_bit_length": bound["prime_plan"][
            "target_twice_maximum_bound"
        ]["bit_length"],
        "partial_CRT_modulus_exceeds_twice_maximum_bound": modulus
        > twice_bound,
        "planned_prime_execution_complete": plan_complete,
        "artifact_rows": artifact_rows,
        "minor_rows": minor_rows,
        "all_artifact_bindings_clean": all_bindings_clean,
        "all_point_replays_match": all_point_replays_match,
        "all_cross_prime_monomial_supports_match": all_supports_match,
        "all_partial_CRT_roundtrips_complete": all_CRT_roundtrips_complete,
        "partial_CRT_residues_are_unique_integer_coefficients": uniqueness_available,
        "bounded_CRT_integer_reconstruction_complete": uniqueness_available,
        "characteristic_zero_D44_divisibility_verified": False,
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
                "artifact_progress": result["artifact_progress"],
                "point_replay_match_count": sum(
                    row["point_replay_match_count"]
                    for row in result["artifact_rows"]
                ),
                "point_replay_count": sum(
                    row["point_replay_count"] for row in result["artifact_rows"]
                ),
                "partial_CRT_modulus_bit_length": result[
                    "partial_CRT_modulus_bit_length"
                ],
                "remaining_additional_prime_count": result[
                    "remaining_additional_prime_count"
                ],
                "new_credit_delta": result["new_credit_delta"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
