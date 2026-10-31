#!/usr/bin/env python3
"""Independently audit the first R209 CRT shard and matrix point replays."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import sympy as sp
from sympy.ntheory.modular import crt

import b9_r201_independent_audit as source


VERSION = "0.1.0"
METHOD = "b9_r209_independent_matrix_and_sympy_CRT_audit_v1"
BOUND_PATH = Path("results/B9_R209_determinant_coefficient_bound_v0.json")
REPLAY_PATH = Path("results/B9_R209_crt_shard_replay_v0.json")
MINOR_INDICES = (4, 5, 6)
DEGREE = 184


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def homogeneous_lattice(degree: int) -> list[tuple[int, int, int]]:
    return [
        (a_degree, b_degree, degree - a_degree - b_degree)
        for a_degree in range(degree, -1, -1)
        for b_degree in range(degree - a_degree, -1, -1)
    ]


def payload_to_sparse(
    terms: list[list[Any]], prime: int
) -> dict[tuple[int, int, int], int]:
    result = {}
    for monomial_raw, coefficient_raw in terms:
        monomial = tuple(int(value) for value in monomial_raw)
        coefficient = int(coefficient_raw) % prime
        if monomial in result or sum(monomial) not in (96, 184) or coefficient == 0:
            raise ValueError("invalid R209 sparse payload")
        result[monomial] = coefficient
    return result


def sparse_evaluate(
    polynomial: dict[tuple[int, int, int], int],
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


def determinant_mod_prime(matrix: list[list[int]], prime: int) -> int:
    work = [[value % prime for value in row] for row in matrix]
    dimension = len(work)
    determinant = 1
    for column in range(dimension):
        pivot_row = next(
            (row for row in range(column, dimension) if work[row][column]),
            None,
        )
        if pivot_row is None:
            return 0
        if pivot_row != column:
            work[column], work[pivot_row] = work[pivot_row], work[column]
            determinant = -determinant
        pivot = work[column][column] % prime
        determinant = determinant * pivot % prime
        pivot_inverse = pow(pivot, -1, prime)
        for row in range(column + 1, dimension):
            factor = work[row][column] * pivot_inverse % prime
            if factor == 0:
                continue
            for next_column in range(column, dimension):
                work[row][next_column] = (
                    work[row][next_column]
                    - factor * work[column][next_column]
                ) % prime
    return determinant % prime


def matrix_at_point(
    columns: list[dict[str, sp.Poly]],
    row_words: list[str],
    point: tuple[int, int, int],
    prime: int,
) -> list[list[int]]:
    substitutions = dict(zip(source.VARS, point))
    matrix = []
    for word in row_words:
        row = []
        for column in columns:
            polynomial = column.get(word)
            row.append(
                0
                if polynomial is None
                else int(polynomial.as_expr().subs(substitutions)) % prime
            )
        matrix.append(row)
    return matrix


def analyze(root: Path) -> dict[str, Any]:
    bound_path = root / BOUND_PATH
    replay_path = root / REPLAY_PATH
    bound = json.loads(bound_path.read_text())
    replay = json.loads(replay_path.read_text())
    if (
        bound.get("checked") is not True
        or replay.get("checked") is not True
        or replay.get("method") != "b9_r209_incremental_three_minor_CRT_replay_v1"
        or replay.get("partial_CRT_residues_are_unique_integer_coefficients")
        is not False
    ):
        raise ValueError("R209 bound or partial replay is not accepted")

    labels, columns, output_words, matrix_hash = source.symbolic_matrix(4, sp.Rational(13, 32))
    bound_rows = {row["minor_index"]: row for row in bound["rows"]}
    replay_rows = {row["minor_index"]: row for row in replay["minor_rows"]}
    artifact_rows = replay["artifact_rows"]
    artifact_paths = {
        (row["minor_index"], row["prime"]): Path(row["path"])
        for row in artifact_rows
    }
    primes = replay["all_CRT_primes"]
    new_primes = replay["completed_planned_primes"]
    if len(new_primes) != 1:
        raise ValueError("independent R209 audit currently requires one new shard")
    new_prime = new_primes[0]

    matrix_rows = []
    sparse_by_minor: dict[int, dict[int, dict[tuple[int, int, int], int]]] = {
        index: {} for index in MINOR_INDICES
    }
    for minor_index in MINOR_INDICES:
        for prime in primes:
            artifact_path = root / artifact_paths[(minor_index, prime)]
            artifact = json.loads(artifact_path.read_text())
            sparse_by_minor[minor_index][prime] = payload_to_sparse(
                artifact["determinant_canonical_terms"], prime
            )
        artifact_path = root / artifact_paths[(minor_index, new_prime)]
        artifact = json.loads(artifact_path.read_text())
        row_words = artifact["row_words"]
        if (
            canonical_hash(row_words) != artifact["row_words_sha256"]
            or artifact["row_words_sha256"]
            != bound_rows[minor_index]["row_words_sha256"]
            or artifact["matrix_sha256"] != matrix_hash
            or artifact["candidate_labels_sha256"] != canonical_hash(labels)
            or not set(row_words).issubset(output_words)
        ):
            raise ValueError("independent R209 matrix binding failed")
        determinant_sparse = sparse_by_minor[minor_index][new_prime]
        quotient_sparse = payload_to_sparse(
            artifact["quotient_canonical_terms"], new_prime
        )
        for point_row in artifact["point_replays"]:
            point = tuple(int(value) for value in point_row["projective_point"])
            direct_modular = determinant_mod_prime(
                matrix_at_point(columns, row_words, point, new_prime),
                new_prime,
            )
            determinant_value = sparse_evaluate(
                determinant_sparse, point, new_prime
            )
            quotient_value = sparse_evaluate(quotient_sparse, point, new_prime)
            d_value = sum(value * value for value in point) % new_prime
            matrix_rows.append(
                {
                    "minor_index": minor_index,
                    "prime": new_prime,
                    "projective_point": list(point),
                    "independent_modular_elimination_determinant": direct_modular,
                    "stored_polynomial_determinant": determinant_value,
                    "stored_quotient_value": quotient_value,
                    "matrix_polynomial_match": direct_modular == determinant_value,
                    "D44_recomposition_match": determinant_value
                    == quotient_value * pow(d_value, 44, new_prime) % new_prime,
                }
            )

    lattice = homogeneous_lattice(DEGREE)
    modulus = math.prod(primes)
    crt_rows = []
    total_roundtrips = 0
    for minor_index in MINOR_INDICES:
        symmetric_payload = []
        maximum_abs = 0
        roundtrips = 0
        for monomial in lattice:
            residues = [
                sparse_by_minor[minor_index][prime].get(monomial, 0)
                for prime in primes
            ]
            value_raw, modulus_raw = crt(primes, residues, check=True)
            value = int(value_raw)
            observed_modulus = int(modulus_raw)
            if observed_modulus != modulus:
                raise RuntimeError("independent R209 CRT modulus mismatch")
            if value > modulus // 2:
                value -= modulus
            for residue, prime in zip(residues, primes):
                if value % prime != residue:
                    raise RuntimeError("independent R209 CRT roundtrip mismatch")
                roundtrips += 1
            if value:
                symmetric_payload.append([list(monomial), str(value)])
                maximum_abs = max(maximum_abs, abs(value))
        replay_row = replay_rows[minor_index]
        row = {
            "minor_index": minor_index,
            "independent_nonzero_symmetric_residue_count": len(symmetric_payload),
            "independent_maximum_absolute_symmetric_residue": str(maximum_abs),
            "independent_symmetric_payload_sha256": canonical_hash(symmetric_payload),
            "independent_roundtrip_check_count": roundtrips,
            "count_match": len(symmetric_payload)
            == replay_row["partial_CRT_nonzero_symmetric_residue_count"],
            "maximum_match": str(maximum_abs)
            == replay_row["partial_CRT_maximum_absolute_symmetric_residue"],
            "payload_hash_match": canonical_hash(symmetric_payload)
            == replay_row["partial_CRT_symmetric_payload_sha256"],
            "roundtrip_count_match": roundtrips
            == replay_row["partial_CRT_roundtrip_check_count"],
        }
        crt_rows.append(row)
        total_roundtrips += roundtrips

    checked = bool(
        len(matrix_rows) == 12
        and all(row["matrix_polynomial_match"] for row in matrix_rows)
        and all(row["D44_recomposition_match"] for row in matrix_rows)
        and len(crt_rows) == 3
        and all(row["count_match"] for row in crt_rows)
        and all(row["maximum_match"] for row in crt_rows)
        and all(row["payload_hash_match"] for row in crt_rows)
        and all(row["roundtrip_count_match"] for row in crt_rows)
        and modulus == int(replay["partial_CRT_modulus"])
        and modulus.bit_length() == replay["partial_CRT_modulus_bit_length"]
    )
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R209_independent_first_shard_audit_only",
        "coupling": "13/32",
        "n": 4,
        "sympy_version": sp.__version__,
        "independent_matrix_algorithm": "custom modular Gaussian elimination",
        "independent_CRT_algorithm": "sympy.ntheory.modular.crt",
        "bound_result_sha256": sha256_file(bound_path),
        "replay_result_sha256": sha256_file(replay_path),
        "new_prime": new_prime,
        "all_CRT_primes": primes,
        "partial_CRT_modulus": str(modulus),
        "partial_CRT_modulus_bit_length": modulus.bit_length(),
        "matrix_rows": matrix_rows,
        "matrix_replay_count": len(matrix_rows),
        "matrix_replay_match_count": sum(
            row["matrix_polynomial_match"] for row in matrix_rows
        ),
        "D44_recomposition_match_count": sum(
            row["D44_recomposition_match"] for row in matrix_rows
        ),
        "crt_rows": crt_rows,
        "total_independent_CRT_roundtrip_check_count": total_roundtrips,
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
                "matrix_replays": result["matrix_replay_count"],
                "matrix_matches": result["matrix_replay_match_count"],
                "D44_matches": result["D44_recomposition_match_count"],
                "CRT_roundtrips": result[
                    "total_independent_CRT_roundtrip_check_count"
                ],
                "new_credit_delta": result["new_credit_delta"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
