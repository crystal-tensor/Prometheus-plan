#!/usr/bin/env python3
"""Replay R209 determinant shards and audit the incremental CRT state."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


VERSION = "0.1.0"
METHOD = "b9_r209_incremental_three_minor_CRT_replay_v1"
BOUND_PATH = Path("results/B9_R209_determinant_coefficient_bound_v0.json")
BASE_PRIMES = (1_000_003, 536_870_723)
DEGREE = 184
MINOR_INDICES = (4, 5, 6)
BASE_ARTIFACTS = {
    4: {
        1_000_003: Path("results/B9_R204_added_minor_mod1000003_v0.json"),
        536_870_723: Path("results/B9_R204_added_minor_mod536870723_v0.json"),
    },
    5: {
        1_000_003: Path("results/B9_R206_sixth_minor_mod1000003_v0.json"),
        536_870_723: Path("results/B9_R206_sixth_minor_mod536870723_v0.json"),
    },
    6: {
        1_000_003: Path("results/B9_R208_seventh_minor_mod1000003_v0.json"),
        536_870_723: Path("results/B9_R208_seventh_minor_mod536870723_v0.json"),
    },
}
BASE_METHODS = {
    4: "b9_r204_independent_added_minor_bridge_v1",
    5: "b9_r206_r205_selected_rows_sixth_minor_bridge_v1",
    6: "b9_r208_r207_cross_branch_seventh_minor_bridge_v1",
}


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


def terms_to_sparse(
    terms: list[list[Any]], prime: int
) -> dict[tuple[int, int, int], int]:
    sparse: dict[tuple[int, int, int], int] = {}
    for monomial_raw, coefficient_raw in terms:
        monomial = tuple(int(value) for value in monomial_raw)
        coefficient = int(coefficient_raw) % prime
        if (
            len(monomial) != 3
            or sum(monomial) != DEGREE
            or monomial in sparse
            or coefficient == 0
        ):
            raise ValueError("invalid R209 determinant term payload")
        sparse[monomial] = coefficient
    return sparse


def combine_crt(residues: list[int], primes: list[int]) -> tuple[int, int]:
    value = 0
    modulus = 1
    for residue, prime in zip(residues, primes):
        step = ((residue - value) % prime) * pow(modulus, -1, prime) % prime
        value += modulus * step
        modulus *= prime
    if value > modulus // 2:
        value -= modulus
    return value, modulus


def discover_new_artifacts(root: Path) -> dict[int, dict[int, Path]]:
    artifacts = {minor_index: {} for minor_index in MINOR_INDICES}
    pattern = re.compile(r"B9_R209_minor([456])_mod([0-9]+)_v0\.json$")
    for path in sorted((root / "results").glob("B9_R209_minor*_mod*_v0.json")):
        match = pattern.fullmatch(path.name)
        if match is None:
            continue
        minor_index = int(match.group(1))
        prime = int(match.group(2))
        if prime in artifacts[minor_index]:
            raise ValueError("duplicate R209 modular artifact")
        artifacts[minor_index][prime] = path.relative_to(root)
    return artifacts


def validate_artifact(
    artifact: dict[str, Any],
    minor_index: int,
    prime: int,
    expected_row: dict[str, Any],
    is_new: bool,
) -> None:
    observed_index = artifact.get("minor_index", artifact.get("new_minor_index"))
    expected_method = (
        "b9_r209_planned_modular_minor_shard_v1"
        if is_new
        else BASE_METHODS[minor_index]
    )
    exact_division = artifact.get(
        "exact_D44_division_verified_mod_prime",
        artifact.get("exact_D44_division_verified"),
    )
    if (
        artifact.get("checked") is not True
        or artifact.get("method") != expected_method
        or artifact.get("characteristic") != prime
        or observed_index != minor_index
        or artifact.get("row_words_sha256")
        != expected_row["row_words_sha256"]
        or artifact.get("matrix_sha256")
        != expected_row["source_matrix_sha256"]
        or artifact.get("candidate_labels_sha256")
        != expected_row["candidate_labels_sha256"]
        or artifact.get("dimension") != 37
        or artifact.get("determinant_total_degree") != DEGREE
        or artifact.get("D_exponent") != 44
        or exact_division is not True
        or artifact.get("quotient_total_degree") != 96
        or artifact.get("frozen_holdouts_executed") is not False
        or artifact.get("scientific_promotion_accepted") is not False
        or artifact.get("new_credit_delta") != 0
    ):
        raise ValueError(
            f"R209 artifact contract failed for minor {minor_index}, prime {prime}"
        )
    if is_new and (
        artifact.get("all_direct_integer_point_replays_match") is not True
        or artifact.get("all_D44_point_recompositions_match") is not True
        or artifact.get("bounded_CRT_integer_reconstruction_complete") is not False
        or artifact.get("characteristic_zero_D44_divisibility_verified") is not False
        or artifact.get("QQ_Nullstellensatz_certificate_verified") is not False
    ):
        raise ValueError("R209 new shard overstates or fails its replay boundary")


def analyze(root: Path) -> dict[str, Any]:
    bound_path = root / BOUND_PATH
    bound = json.loads(bound_path.read_text())
    if (
        bound.get("checked") is not True
        or bound.get("method")
        != "b9_r209_three_minor_unconditional_coefficient_bound_v1"
    ):
        raise ValueError("R209 coefficient-bound result is not accepted")
    bound_rows = {row["minor_index"]: row for row in bound["rows"]}
    if set(bound_rows) != set(MINOR_INDICES):
        raise ValueError("R209 coefficient-bound rows are incomplete")

    new_artifacts = discover_new_artifacts(root)
    complete_new_primes = sorted(
        set.intersection(
            *(set(new_artifacts[index]) for index in MINOR_INDICES)
        ),
        reverse=True,
    )
    if any(set(new_artifacts[index]) != set(complete_new_primes) for index in MINOR_INDICES):
        raise ValueError("R209 has an incomplete three-minor prime shard")
    planned = bound["prime_plan"]["planned_additional_primes"]
    if complete_new_primes != planned[: len(complete_new_primes)]:
        raise ValueError("R209 new-prime artifacts are not the planned prefix")
    primes = list(BASE_PRIMES) + complete_new_primes
    modulus = math.prod(primes)
    lattice = homogeneous_lattice(DEGREE)
    lattice_hash = canonical_hash([list(monomial) for monomial in lattice])

    artifact_rows = []
    sparse_by_minor: dict[int, dict[int, dict[tuple[int, int, int], int]]] = {
        index: {} for index in MINOR_INDICES
    }
    for minor_index in MINOR_INDICES:
        paths = dict(BASE_ARTIFACTS[minor_index])
        paths.update(new_artifacts[minor_index])
        for prime in primes:
            relative_path = paths[prime]
            path = root / relative_path
            artifact = json.loads(path.read_text())
            validate_artifact(
                artifact,
                minor_index,
                prime,
                bound_rows[minor_index],
                prime not in BASE_PRIMES,
            )
            sparse = terms_to_sparse(
                artifact["determinant_canonical_terms"], prime
            )
            if canonical_hash(artifact["determinant_canonical_terms"]) != artifact[
                "determinant_canonical_terms_sha256"
            ]:
                raise ValueError("R209 determinant term hash mismatch")
            sparse_by_minor[minor_index][prime] = sparse
            artifact_rows.append(
                {
                    "minor_index": minor_index,
                    "prime": prime,
                    "path": str(relative_path),
                    "file_sha256": sha256_file(path),
                    "payload_sha256": artifact["payload_sha256"],
                    "determinant_canonical_terms_sha256": artifact[
                        "determinant_canonical_terms_sha256"
                    ],
                    "determinant_support_sha256": canonical_hash(
                        [list(monomial) for monomial in sorted(sparse, reverse=True)]
                    ),
                    "determinant_term_count": len(sparse),
                    "quotient_canonical_terms_sha256": artifact[
                        "quotient_canonical_terms_sha256"
                    ],
                    "quotient_term_count": artifact["quotient_term_count"],
                    "checked": True,
                }
            )

    minor_rows = []
    total_roundtrips = 0
    for minor_index in MINOR_INDICES:
        symmetric_payload = []
        roundtrip_count = 0
        maximum_abs = 0
        for monomial in lattice:
            residues = [
                sparse_by_minor[minor_index][prime].get(monomial, 0)
                for prime in primes
            ]
            coefficient, coefficient_modulus = combine_crt(residues, primes)
            if coefficient_modulus != modulus:
                raise RuntimeError("R209 CRT modulus drift")
            for residue, prime in zip(residues, primes):
                if coefficient % prime != residue:
                    raise RuntimeError("R209 CRT roundtrip failed")
                roundtrip_count += 1
            if coefficient:
                symmetric_payload.append([list(monomial), str(coefficient)])
                maximum_abs = max(maximum_abs, abs(coefficient))

        support_hashes = {
            canonical_hash(
                [
                    list(monomial)
                    for monomial in sorted(
                        sparse_by_minor[minor_index][prime], reverse=True
                    )
                ]
            )
            for prime in primes
        }
        selected_bound = int(
            bound_rows[minor_index]["selected_unconditional_coefficient_bound"][
                "value"
            ]
        )
        uniqueness = modulus > 2 * selected_bound
        minor_rows.append(
            {
                "minor_index": minor_index,
                "row_words_sha256": bound_rows[minor_index][
                    "row_words_sha256"
                ],
                "homogeneous_monomial_lattice_size": len(lattice),
                "homogeneous_monomial_lattice_sha256": lattice_hash,
                "cross_prime_support_hash_count": len(support_hashes),
                "cross_prime_support_identical": len(support_hashes) == 1,
                "cross_prime_support_sha256": next(iter(support_hashes))
                if len(support_hashes) == 1
                else None,
                "partial_CRT_nonzero_symmetric_residue_count": len(
                    symmetric_payload
                ),
                "partial_CRT_maximum_absolute_symmetric_residue": str(maximum_abs),
                "partial_CRT_symmetric_payload_sha256": canonical_hash(
                    symmetric_payload
                ),
                "partial_CRT_roundtrip_check_count": roundtrip_count,
                "partial_CRT_roundtrip_expected_count": len(lattice) * len(primes),
                "partial_CRT_roundtrip_complete": roundtrip_count
                == len(lattice) * len(primes),
                "selected_unconditional_coefficient_bound": bound_rows[
                    minor_index
                ]["selected_unconditional_coefficient_bound"],
                "partial_CRT_modulus_exceeds_twice_selected_bound": uniqueness,
            }
        )
        total_roundtrips += roundtrip_count

    expected_artifact_count = len(MINOR_INDICES) * len(primes)
    uniqueness_available = all(
        row["partial_CRT_modulus_exceeds_twice_selected_bound"]
        for row in minor_rows
    )
    checked = bool(
        len(artifact_rows) == expected_artifact_count
        and all(row["checked"] for row in artifact_rows)
        and all(row["cross_prime_support_identical"] for row in minor_rows)
        and all(row["partial_CRT_roundtrip_complete"] for row in minor_rows)
        and not uniqueness_available
        and len(complete_new_primes) < len(planned)
    )
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R209_incremental_modular_CRT_execution_only",
        "coupling": "13/32",
        "n": 4,
        "minor_indices": list(MINOR_INDICES),
        "bound_result_sha256": sha256_file(bound_path),
        "bound_stable_payload_sha256": bound["stable_payload_sha256"],
        "base_primes": list(BASE_PRIMES),
        "completed_planned_primes": complete_new_primes,
        "all_CRT_primes": primes,
        "completed_planned_prime_count": len(complete_new_primes),
        "planned_additional_prime_count": len(planned),
        "remaining_planned_primes": planned[len(complete_new_primes) :],
        "remaining_planned_prime_count": len(planned) - len(complete_new_primes),
        "completed_new_minor_artifact_count": len(complete_new_primes)
        * len(MINOR_INDICES),
        "planned_new_minor_artifact_count": len(planned) * len(MINOR_INDICES),
        "remaining_new_minor_artifact_count": (
            len(planned) - len(complete_new_primes)
        )
        * len(MINOR_INDICES),
        "artifact_rows": artifact_rows,
        "artifact_bundle_sha256": canonical_hash(artifact_rows),
        "minor_rows": minor_rows,
        "partial_CRT_modulus": str(modulus),
        "partial_CRT_modulus_bit_length": modulus.bit_length(),
        "maximum_twice_bound_bit_length": max(
            row["twice_selected_bound_bit_length"] for row in bound["rows"]
        ),
        "all_partial_CRT_roundtrips_complete": all(
            row["partial_CRT_roundtrip_complete"] for row in minor_rows
        ),
        "total_partial_CRT_roundtrip_check_count": total_roundtrips,
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
                "completed_planned_primes": result["completed_planned_prime_count"],
                "completed_new_minor_artifacts": result[
                    "completed_new_minor_artifact_count"
                ],
                "partial_CRT_modulus_bits": result[
                    "partial_CRT_modulus_bit_length"
                ],
                "maximum_twice_bound_bits": result[
                    "maximum_twice_bound_bit_length"
                ],
                "roundtrip_checks": result[
                    "total_partial_CRT_roundtrip_check_count"
                ],
                "uniqueness_available": result[
                    "partial_CRT_residues_are_unique_integer_coefficients"
                ],
                "remaining_new_minor_artifacts": result[
                    "remaining_new_minor_artifact_count"
                ],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
