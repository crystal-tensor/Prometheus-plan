#!/usr/bin/env python3
"""Independently audit the completed prefix of R209 CRT prime shards."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import sympy as sp
from sympy.ntheory.modular import crt

import b9_r201_independent_audit as source
import b9_r209_independent_crt_audit as prior


VERSION = "0.1.0"
METHOD = "b9_r210_independent_prefix_matrix_and_sympy_CRT_audit_v1"
BOUND_PATH = Path("results/B9_R209_determinant_coefficient_bound_v0.json")
REPLAY_PATH = Path("results/B9_R210_crt_shard2_replay_v0.json")
BASE_PRIMES = (1_000_003, 536_870_723)
MINOR_INDICES = (4, 5, 6)
DEGREE = 184
REPLAY_POINTS = ((2, 0, 1), (1, 0, -2), (1, 2, 3), (3, -1, 2))


def validate_sparse_payload(terms: list[list[object]], degree: int, prime: int) -> None:
    seen: set[tuple[int, int, int]] = set()
    for monomial_raw, coefficient_raw in terms:
        monomial = tuple(int(value) for value in monomial_raw)
        coefficient = int(coefficient_raw) % prime
        if (
            len(monomial) != 3
            or any(value < 0 for value in monomial)
            or sum(monomial) != degree
            or monomial in seen
            or coefficient == 0
        ):
            raise ValueError("R210 sparse payload shape failed")
        seen.add(monomial)


def analyze(root: Path) -> dict:
    bound_path = root / BOUND_PATH
    replay_path = root / REPLAY_PATH
    bound = json.loads(bound_path.read_text())
    replay = json.loads(replay_path.read_text())
    replay_payload = dict(replay)
    observed_replay_payload_hash = replay_payload.pop("payload_sha256", None)
    replay_stable = dict(replay_payload)
    observed_replay_stable_hash = replay_stable.pop(
        "stable_payload_sha256", None
    )
    new_primes = replay.get("completed_planned_primes", [])
    primes = replay.get("all_CRT_primes", [])
    planned_primes = bound.get("prime_plan", {}).get(
        "planned_additional_primes", []
    )
    pairwise_coprime = all(
        math.gcd(left, right) == 1
        for index, left in enumerate(primes)
        for right in primes[index + 1 :]
    )
    if (
        bound.get("checked") is not True
        or replay.get("checked") is not True
        or replay.get("method")
        != "b9_r209_incremental_three_minor_CRT_replay_v1"
        or replay.get("partial_CRT_residues_are_unique_integer_coefficients")
        is not False
        or replay.get("bounded_CRT_integer_reconstruction_complete") is not False
        or replay.get("characteristic_zero_D44_divisibility_verified") is not False
        or replay.get("QQ_Nullstellensatz_certificate_verified") is not False
        or prior.canonical_hash(replay_stable) != observed_replay_stable_hash
        or prior.canonical_hash(replay_payload) != observed_replay_payload_hash
        or not new_primes
        or new_primes != planned_primes[: len(new_primes)]
        or len(primes) != len(set(primes))
        or not pairwise_coprime
        or primes != list(BASE_PRIMES) + new_primes
    ):
        raise ValueError("R210 bound, replay, or non-uniqueness contract failed")

    labels, columns, output_words, matrix_hash = source.symbolic_matrix(
        4, sp.Rational(13, 32)
    )
    bound_rows = {row["minor_index"]: row for row in bound["rows"]}
    replay_rows = {row["minor_index"]: row for row in replay["minor_rows"]}
    artifact_rows = replay["artifact_rows"]
    artifact_paths = {
        (row["minor_index"], row["prime"]): Path(row["path"])
        for row in artifact_rows
    }
    artifact_row_by_key = {
        (row["minor_index"], row["prime"]): row for row in artifact_rows
    }
    expected_artifact_keys = {
        (minor_index, prime)
        for minor_index in MINOR_INDICES
        for prime in primes
    }
    if (
        len(artifact_rows) != len(expected_artifact_keys)
        or len(artifact_paths) != len(expected_artifact_keys)
        or set(artifact_paths) != expected_artifact_keys
    ):
        raise ValueError("R210 replay artifact grid is incomplete")

    matrix_rows = []
    sparse_by_minor = {index: {} for index in MINOR_INDICES}
    for minor_index in MINOR_INDICES:
        for prime in primes:
            artifact_path = root / artifact_paths[(minor_index, prime)]
            artifact = json.loads(artifact_path.read_text())
            replay_artifact_row = artifact_row_by_key[(minor_index, prime)]
            if prior.sha256_file(artifact_path) != replay_artifact_row["file_sha256"]:
                raise ValueError("R210 replay artifact file hash mismatch")
            validate_sparse_payload(
                artifact["determinant_canonical_terms"], DEGREE, prime
            )
            if (
                prior.canonical_hash(artifact["determinant_canonical_terms"])
                != artifact["determinant_canonical_terms_sha256"]
                or len(artifact["determinant_canonical_terms"])
                != artifact["determinant_term_count"]
            ):
                raise ValueError("R210 determinant payload hash or count failed")
            sparse_by_minor[minor_index][prime] = prior.payload_to_sparse(
                artifact["determinant_canonical_terms"], prime
            )

        for prime in new_primes:
            artifact_path = root / artifact_paths[(minor_index, prime)]
            artifact = json.loads(artifact_path.read_text())
            row_words = artifact["row_words"]
            validate_sparse_payload(
                artifact["quotient_canonical_terms"], 96, prime
            )
            payload = dict(artifact)
            observed_payload_hash = payload.pop("payload_sha256", None)
            stable = dict(payload)
            observed_stable_hash = stable.pop("stable_payload_sha256", None)
            stable.pop("elapsed_seconds", None)
            stable.pop("singular_path", None)
            point_rows = artifact.get("point_replays", [])
            point_map = {
                tuple(int(value) for value in row["projective_point"]): row
                for row in point_rows
            }
            if (
                prior.canonical_hash(row_words) != artifact["row_words_sha256"]
                or artifact["row_words_sha256"]
                != bound_rows[minor_index]["row_words_sha256"]
                or artifact["matrix_sha256"] != matrix_hash
                or artifact["candidate_labels_sha256"]
                != prior.canonical_hash(labels)
                or not set(row_words).issubset(output_words)
                or artifact.get("checked") is not True
                or artifact.get("exact_D44_division_verified_mod_prime") is not True
                or prior.canonical_hash(artifact["quotient_canonical_terms"])
                != artifact["quotient_canonical_terms_sha256"]
                or len(artifact["quotient_canonical_terms"])
                != artifact["quotient_term_count"]
                or prior.canonical_hash(payload) != observed_payload_hash
                or prior.canonical_hash(stable) != observed_stable_hash
                or len(point_rows) != len(REPLAY_POINTS)
                or len(point_map) != len(REPLAY_POINTS)
                or set(point_map) != set(REPLAY_POINTS)
            ):
                raise ValueError("R210 matrix or source binding failed")
            determinant_sparse = sparse_by_minor[minor_index][prime]
            quotient_sparse = prior.payload_to_sparse(
                artifact["quotient_canonical_terms"], prime
            )
            for point in REPLAY_POINTS:
                point_row = point_map[point]
                direct_modular = prior.determinant_mod_prime(
                    prior.matrix_at_point(columns, row_words, point, prime), prime
                )
                determinant_value = prior.sparse_evaluate(
                    determinant_sparse, point, prime
                )
                quotient_value = prior.sparse_evaluate(
                    quotient_sparse, point, prime
                )
                d_value = sum(value * value for value in point) % prime
                stored_values_match = bool(
                    point_row.get("direct_integer_determinant_mod_prime")
                    == direct_modular
                    and point_row.get("polynomial_determinant_mod_prime")
                    == determinant_value
                    and point_row.get("quotient_mod_prime") == quotient_value
                    and point_row.get("D_mod_prime") == d_value
                    and point_row.get("determinant_replay_match") is True
                    and point_row.get("D_power_recomposition_match") is True
                )
                matrix_rows.append(
                    {
                        "minor_index": minor_index,
                        "prime": prime,
                        "projective_point": list(point),
                        "artifact_sha256": prior.sha256_file(artifact_path),
                        "independent_modular_elimination_determinant": direct_modular,
                        "stored_polynomial_determinant": determinant_value,
                        "stored_quotient_value": quotient_value,
                        "matrix_polynomial_match": direct_modular
                        == determinant_value,
                        "D44_recomposition_match": determinant_value
                        == quotient_value * pow(d_value, 44, prime) % prime,
                        "stored_point_values_match": stored_values_match,
                    }
                )

    lattice = prior.homogeneous_lattice(DEGREE)
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
                raise RuntimeError("R210 independent CRT modulus mismatch")
            if value > modulus // 2:
                value -= modulus
            for residue, prime in zip(residues, primes):
                if value % prime != residue:
                    raise RuntimeError("R210 independent CRT roundtrip mismatch")
                roundtrips += 1
            if value:
                symmetric_payload.append([list(monomial), str(value)])
                maximum_abs = max(maximum_abs, abs(value))
        replay_row = replay_rows[minor_index]
        crt_rows.append(
            {
                "minor_index": minor_index,
                "independent_nonzero_symmetric_residue_count": len(
                    symmetric_payload
                ),
                "independent_maximum_absolute_symmetric_residue": str(maximum_abs),
                "independent_symmetric_payload_sha256": prior.canonical_hash(
                    symmetric_payload
                ),
                "independent_roundtrip_check_count": roundtrips,
                "count_match": len(symmetric_payload)
                == replay_row["partial_CRT_nonzero_symmetric_residue_count"],
                "maximum_match": str(maximum_abs)
                == replay_row["partial_CRT_maximum_absolute_symmetric_residue"],
                "payload_hash_match": prior.canonical_hash(symmetric_payload)
                == replay_row["partial_CRT_symmetric_payload_sha256"],
                "roundtrip_count_match": roundtrips
                == replay_row["partial_CRT_roundtrip_check_count"],
            }
        )
        total_roundtrips += roundtrips

    expected_matrix_rows = len(MINOR_INDICES) * len(new_primes) * 4
    selected_bounds = {
        row["minor_index"]: int(
            row["selected_unconditional_coefficient_bound"]["value"]
        )
        for row in bound["rows"]
    }
    uniqueness_by_minor = {
        minor_index: modulus > 2 * selected_bounds[minor_index]
        for minor_index in MINOR_INDICES
    }
    uniqueness_available = all(uniqueness_by_minor.values())
    checked = bool(
        len(matrix_rows) == expected_matrix_rows
        and all(row["matrix_polynomial_match"] for row in matrix_rows)
        and all(row["D44_recomposition_match"] for row in matrix_rows)
        and all(row["stored_point_values_match"] for row in matrix_rows)
        and len(crt_rows) == len(MINOR_INDICES)
        and all(row["count_match"] for row in crt_rows)
        and all(row["maximum_match"] for row in crt_rows)
        and all(row["payload_hash_match"] for row in crt_rows)
        and all(row["roundtrip_count_match"] for row in crt_rows)
        and modulus == int(replay["partial_CRT_modulus"])
        and modulus.bit_length() == replay["partial_CRT_modulus_bit_length"]
        and total_roundtrips
        == replay["total_partial_CRT_roundtrip_check_count"]
        and uniqueness_available
        == replay["partial_CRT_residues_are_unique_integer_coefficients"]
        and uniqueness_available
        == replay["bounded_CRT_integer_reconstruction_complete"]
    )
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R210_independent_completed_prefix_audit_only",
        "coupling": "13/32",
        "n": 4,
        "sympy_version": sp.__version__,
        "independent_matrix_algorithm": "custom modular Gaussian elimination",
        "independent_CRT_algorithm": "sympy.ntheory.modular.crt",
        "bound_result_sha256": prior.sha256_file(bound_path),
        "replay_result_sha256": prior.sha256_file(replay_path),
        "new_primes": new_primes,
        "all_CRT_primes": primes,
        "partial_CRT_modulus": str(modulus),
        "partial_CRT_modulus_bit_length": modulus.bit_length(),
        "uniqueness_by_minor": uniqueness_by_minor,
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
        "partial_CRT_residues_are_unique_integer_coefficients": uniqueness_available,
        "bounded_CRT_integer_reconstruction_complete": uniqueness_available,
        "characteristic_zero_D44_divisibility_verified": False,
        "QQ_Nullstellensatz_certificate_verified": False,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "checked": checked,
    }
    stable_payload = dict(result)
    result["stable_payload_sha256"] = prior.canonical_hash(stable_payload)
    payload_without_hash = dict(result)
    result["payload_sha256"] = prior.canonical_hash(payload_without_hash)
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
                "completed_new_primes": len(result["new_primes"]),
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
