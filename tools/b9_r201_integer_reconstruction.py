#!/usr/bin/env python3
"""Reconstruct the four frozen R201 determinants over ZZ and divide by D^44."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import sympy as sp

import b9_r201_crt_shard_replay as shard
import b9_r201_projective_patch_certificate as r201


VERSION = "0.2.0"
METHOD = "b9_r201_bounded_integer_reconstruction_and_D44_division_v2"
D_EXPONENT = 44


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
        if coefficient
    ]


def reconstruct(root: Path) -> dict[str, Any]:
    bound_path = root / "results/B9_R201_determinant_coefficient_bound_v0.json"
    replay_path = root / "results/B9_R201_crt_shard_replay_v0.json"
    bound = json.loads(bound_path.read_text())
    replay = json.loads(replay_path.read_text())

    planned = bound["prime_plan"]["planned_additional_primes"]
    primes = [*shard.EXISTING_PRIMES, *planned]
    modulus = 1
    for prime in primes:
        modulus *= prime
    twice_maximum_bound = 2 * int(
        bound["maximum_unconditional_coefficient_bound"]["value"]
    )
    if modulus <= twice_maximum_bound:
        raise RuntimeError("R201 CRT modulus does not exceed twice the proved bound")
    if (
        replay.get("checked") is not True
        or replay.get("planned_prime_execution_complete") is not True
        or replay.get("all_CRT_primes") != primes
        or replay.get("partial_CRT_modulus") != str(modulus)
        or replay.get("partial_CRT_residues_are_unique_integer_coefficients")
        is not True
        or replay.get("bounded_CRT_integer_reconstruction_complete") is not True
    ):
        raise RuntimeError("R201 final CRT replay is not ready for integer reconstruction")

    lattice = shard.homogeneous_lattice(shard.DEGREE)
    D = sp.Poly(sum(variable**2 for variable in r201.VARS), *r201.VARS, domain=sp.ZZ)
    D_power = D**D_EXPONENT
    rows = []
    quotient_polynomials = []
    for minor_index in range(4):
        polynomials = []
        source_artifacts = []
        for prime in primes:
            path = shard.artifact_path(root, minor_index, prime)
            artifact = json.loads(path.read_text())
            polynomial = shard.payload_to_sparse(
                artifact.get("canonical_terms", []), prime
            )
            polynomials.append(polynomial)
            source_artifacts.append(
                {
                    "prime": prime,
                    "path": str(path.relative_to(root)),
                    "sha256": sha256_file(path),
                    "canonical_terms_sha256": artifact.get(
                        "canonical_terms_sha256"
                    ),
                }
            )

        bound_row = bound["rows"][minor_index]
        selected_bound = int(
            bound_row["selected_unconditional_coefficient_bound"]["value"]
        )
        full_lattice_payload = []
        coefficients: dict[tuple[int, int, int], int] = {}
        roundtrip_count = 0
        maximum_absolute_coefficient = 0
        for monomial in lattice:
            residues = [polynomial.get(monomial, 0) for polynomial in polynomials]
            coefficient = shard.symmetric_crt(residues, primes)
            full_lattice_payload.append([list(monomial), str(coefficient)])
            maximum_absolute_coefficient = max(
                maximum_absolute_coefficient, abs(coefficient)
            )
            if coefficient:
                coefficients[monomial] = coefficient
            roundtrip_count += sum(
                coefficient % prime == residue
                for prime, residue in zip(primes, residues)
            )

        determinant = sp.Poly.from_dict(coefficients, r201.VARS, domain=sp.ZZ)
        quotient, remainder = sp.div(determinant, D_power, domain=sp.ZZ)
        quotient_polynomials.append(quotient)
        quotient_content, primitive_quotient = quotient.primitive()
        if primitive_quotient.LC() < 0:
            quotient_content = -quotient_content
            primitive_quotient = -primitive_quotient
        determinant_payload = polynomial_payload(determinant)
        quotient_payload = polynomial_payload(quotient)
        primitive_quotient_payload = polynomial_payload(primitive_quotient)
        remainder_payload = polynomial_payload(remainder)
        replay_row = replay["minor_rows"][minor_index]
        expected_roundtrips = len(lattice) * len(primes)
        rows.append(
            {
                "minor_index": minor_index,
                "row_words_sha256": bound_row["row_words_sha256"],
                "source_artifacts": source_artifacts,
                "source_artifact_count": len(source_artifacts),
                "selected_bound_method": bound_row["selected_bound_method"],
                "selected_unconditional_coefficient_bound": str(selected_bound),
                "selected_unconditional_coefficient_bound_bit_length": selected_bound.bit_length(),
                "maximum_absolute_reconstructed_coefficient": str(
                    maximum_absolute_coefficient
                ),
                "maximum_absolute_reconstructed_coefficient_bit_length": maximum_absolute_coefficient.bit_length(),
                "all_reconstructed_coefficients_within_selected_bound": (
                    maximum_absolute_coefficient <= selected_bound
                ),
                "homogeneous_lattice_size": len(lattice),
                "coefficient_slot_prime_roundtrip_count": roundtrip_count,
                "coefficient_slot_prime_roundtrip_expected_count": expected_roundtrips,
                "coefficient_slot_prime_roundtrip_complete": (
                    roundtrip_count == expected_roundtrips
                ),
                "full_lattice_integer_payload_sha256": canonical_hash(
                    full_lattice_payload
                ),
                "full_lattice_payload_matches_final_replay": canonical_hash(
                    full_lattice_payload
                )
                == replay_row["partial_CRT_symmetric_payload_sha256"],
                "determinant_total_degree": determinant.total_degree(),
                "determinant_term_count": len(determinant_payload),
                "determinant_canonical_terms_sha256": canonical_hash(
                    determinant_payload
                ),
                "determinant_canonical_terms": determinant_payload,
                "D_polynomial": "a^2+b^2+c^2",
                "D_exponent": D_EXPONENT,
                "D_power_total_degree": D_power.total_degree(),
                "quotient_total_degree": quotient.total_degree(),
                "quotient_term_count": len(quotient_payload),
                "quotient_canonical_terms_sha256": canonical_hash(quotient_payload),
                "quotient_canonical_terms": quotient_payload,
                "quotient_integer_content": str(int(quotient_content)),
                "quotient_integer_content_absolute": str(abs(int(quotient_content))),
                "primitive_quotient_total_degree": primitive_quotient.total_degree(),
                "primitive_quotient_term_count": len(primitive_quotient_payload),
                "primitive_quotient_canonical_terms_sha256": canonical_hash(
                    primitive_quotient_payload
                ),
                "remainder_term_count": len(remainder_payload),
                "remainder_canonical_terms_sha256": canonical_hash(
                    remainder_payload
                ),
                "exact_D44_division_verified": remainder.is_zero,
            }
        )

    all_bounds_pass = all(
        row["all_reconstructed_coefficients_within_selected_bound"] for row in rows
    )
    all_roundtrips_pass = all(
        row["coefficient_slot_prime_roundtrip_complete"] for row in rows
    )
    all_replay_hashes_match = all(
        row["full_lattice_payload_matches_final_replay"] for row in rows
    )
    all_D44_divisions_pass = all(row["exact_D44_division_verified"] for row in rows)
    quotient_gcd_over_ZZ = quotient_polynomials[0]
    for quotient in quotient_polynomials[1:]:
        quotient_gcd_over_ZZ = sp.gcd(quotient_gcd_over_ZZ, quotient)
    if quotient_gcd_over_ZZ.LC() < 0:
        quotient_gcd_over_ZZ = -quotient_gcd_over_ZZ
    quotient_gcd_over_ZZ_payload = polynomial_payload(quotient_gcd_over_ZZ)
    quotient_contents = [
        abs(int(row["quotient_integer_content"])) for row in rows
    ]
    common_integer_content = math.gcd(*quotient_contents)
    primitive_quotients = [quotient.primitive()[1] for quotient in quotient_polynomials]
    primitive_quotient_gcd = primitive_quotients[0]
    for primitive_quotient in primitive_quotients[1:]:
        primitive_quotient_gcd = sp.gcd(
            primitive_quotient_gcd, primitive_quotient
        )
    primitive_quotient_gcd = primitive_quotient_gcd.primitive()[1]
    if primitive_quotient_gcd.LC() < 0:
        primitive_quotient_gcd = -primitive_quotient_gcd
    primitive_quotient_gcd_payload = polynomial_payload(primitive_quotient_gcd)
    primitive_quotient_gcd_is_unit = (
        primitive_quotient_gcd.total_degree() == 0
        and len(primitive_quotient_gcd_payload) == 1
        and abs(int(primitive_quotient_gcd_payload[0][1])) == 1
    )
    quotient_gcd_over_ZZ_matches_common_content = (
        quotient_gcd_over_ZZ.total_degree() == 0
        and quotient_gcd_over_ZZ_payload
        == [[[0, 0, 0], str(common_integer_content)]]
    )
    checked = (
        all_bounds_pass
        and all_roundtrips_pass
        and all_replay_hashes_match
        and all_D44_divisions_pass
        and primitive_quotient_gcd_is_unit
        and quotient_gcd_over_ZZ_matches_common_content
        and [row["determinant_term_count"] for row in rows]
        == [8649, 4468, 4770, 2760]
        and [row["quotient_term_count"] for row in rows]
        == [2401, 464, 590, 450]
    )
    return {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R201_bounded_integer_reconstruction_and_exact_D44_division_only",
        "coupling": "13/32",
        "n": 4,
        "dimension": shard.DIMENSION,
        "determinant_degree": shard.DEGREE,
        "source_bound_result_sha256": sha256_file(bound_path),
        "source_final_replay_sha256": sha256_file(replay_path),
        "all_CRT_primes": primes,
        "CRT_prime_count": len(primes),
        "CRT_modulus": str(modulus),
        "CRT_modulus_bit_length": modulus.bit_length(),
        "twice_maximum_bound": str(twice_maximum_bound),
        "twice_maximum_bound_bit_length": twice_maximum_bound.bit_length(),
        "CRT_modulus_exceeds_twice_maximum_bound": modulus
        > twice_maximum_bound,
        "integer_reconstruction_uniqueness_proved": True,
        "rows": rows,
        "all_reconstructed_coefficients_within_selected_bounds": all_bounds_pass,
        "all_coefficient_slot_prime_roundtrips_complete": all_roundtrips_pass,
        "all_integer_payload_hashes_match_final_replay": all_replay_hashes_match,
        "quotient_common_integer_content": str(common_integer_content),
        "quotient_common_integer_content_factorization": {
            str(prime): exponent
            for prime, exponent in sorted(sp.factorint(common_integer_content).items())
        },
        "quotient_gcd_over_ZZ_total_degree": quotient_gcd_over_ZZ.total_degree(),
        "quotient_gcd_over_ZZ_term_count": len(quotient_gcd_over_ZZ_payload),
        "quotient_gcd_over_ZZ_canonical_terms_sha256": canonical_hash(
            quotient_gcd_over_ZZ_payload
        ),
        "quotient_gcd_over_ZZ_canonical_terms": quotient_gcd_over_ZZ_payload,
        "quotient_gcd_over_ZZ_matches_common_integer_content": (
            quotient_gcd_over_ZZ_matches_common_content
        ),
        "primitive_quotient_gcd_total_degree": primitive_quotient_gcd.total_degree(),
        "primitive_quotient_gcd_term_count": len(primitive_quotient_gcd_payload),
        "primitive_quotient_gcd_canonical_terms_sha256": canonical_hash(
            primitive_quotient_gcd_payload
        ),
        "primitive_quotient_gcd_canonical_terms": primitive_quotient_gcd_payload,
        "primitive_quotient_gcd_is_unit": primitive_quotient_gcd_is_unit,
        "characteristic_zero_engineering_determinants_verified": checked,
        "characteristic_zero_D44_divisibility_verified": all_D44_divisions_pass,
        "characteristic_zero_gcd_over_QQ_exactly_D44_up_to_nonzero_rational_scalar": (
            all_D44_divisions_pass and primitive_quotient_gcd_is_unit
        ),
        "characteristic_zero_gcd_over_ZZ_exactly_common_content_times_D44_up_to_sign": (
            all_D44_divisions_pass and quotient_gcd_over_ZZ_matches_common_content
        ),
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
    result = reconstruct(root)
    output = args.output if args.output.is_absolute() else root / args.output
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "checked": result["checked"],
                "CRT_modulus_bit_length": result["CRT_modulus_bit_length"],
                "determinant_term_counts": [
                    row["determinant_term_count"] for row in result["rows"]
                ],
                "quotient_term_counts": [
                    row["quotient_term_count"] for row in result["rows"]
                ],
                "characteristic_zero_D44_divisibility_verified": result[
                    "characteristic_zero_D44_divisibility_verified"
                ],
                "quotient_common_integer_content": result[
                    "quotient_common_integer_content"
                ],
                "characteristic_zero_gcd_over_QQ_exactly_D44_up_to_nonzero_rational_scalar": result[
                    "characteristic_zero_gcd_over_QQ_exactly_D44_up_to_nonzero_rational_scalar"
                ],
                "characteristic_zero_gcd_over_ZZ_exactly_common_content_times_D44_up_to_sign": result[
                    "characteristic_zero_gcd_over_ZZ_exactly_common_content_times_D44_up_to_sign"
                ],
                "new_credit_delta": result["new_credit_delta"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
