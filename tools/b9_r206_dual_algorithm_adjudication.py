#!/usr/bin/env python3
"""Adjudicate the R206 six-minor classification across two Singular algorithms."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


METHOD = "b9_r206_dual_singular_algorithm_adjudication_v1"
VERSION = "0.1.0"
EXPECTED_PRIMES = [1_000_003, 536_870_723]
EXPECTED_CONCLUSION = "two_prime_nonunit_outside_b_zero_after_sixth_minor"


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_verified(path: Path) -> dict[str, Any]:
    result = json.loads(path.read_text())
    payload = dict(result)
    expected = payload.pop("payload_sha256", None)
    if expected is None or canonical_hash(payload) != expected:
        raise ValueError(f"payload hash mismatch: {path}")
    return result


def invariant_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in result.get("prime_rows", []):
        basis = row.get("expanded_engineering", {})
        rows.append(
            {
                "prime": row.get("prime"),
                "basis_size": basis.get("basis_size"),
                "unit_membership_remainder": basis.get(
                    "unit_membership_remainder"
                ),
                "unit_ideal_detected": basis.get("unit_ideal_detected"),
                "slice": row.get("slice"),
                "checked": row.get("checked"),
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--slimgb-result",
        type=Path,
        default=Path("results/B9_R206_six_minor_ideal_preflight_v0.json"),
    )
    parser.add_argument(
        "--std-result",
        type=Path,
        default=Path("results/B9_R206_six_minor_ideal_std_audit_v0.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/B9_R206_dual_algorithm_adjudication_v0.json"),
    )
    args = parser.parse_args()

    slimgb = load_verified(args.slimgb_result)
    std = load_verified(args.std_result)
    slimgb_rows = invariant_rows(slimgb)
    std_rows = invariant_rows(std)
    expected_rows = [
        {
            "prime": prime,
            "basis_size": 7,
            "unit_membership_remainder": "1",
            "unit_ideal_detected": False,
            "slice": {
                "gcd_total_degree": 0,
                "gcd_term_count": 1,
                "normalized_gcd_is_one": True,
            },
            "checked": True,
        }
        for prime in EXPECTED_PRIMES
    ]

    source_bindings_match = all(
        slimgb.get(field) == std.get(field)
        for field in (
            "source_sha256",
            "fifth_minor_result_sha256",
            "sixth_minor_result_sha256",
            "sixth_minor_support_sha256",
            "old_minor_count",
            "expanded_minor_count",
            "saturation_equation",
            "monomial_order",
        )
    )
    algorithm_independent_classification_match = (
        slimgb.get("standard_basis_algorithm") == "slimgb"
        and std.get("standard_basis_algorithm") == "std"
        and slimgb.get("primes") == EXPECTED_PRIMES
        and std.get("primes") == EXPECTED_PRIMES
        and slimgb.get("preflight_conclusion") == EXPECTED_CONCLUSION
        and std.get("preflight_conclusion") == EXPECTED_CONCLUSION
        and slimgb.get("expanded_slice_gcd_total_degree") == 0
        and std.get("expanded_slice_gcd_total_degree") == 0
        and slimgb.get("expanded_slice_gcd_term_count") == 1
        and std.get("expanded_slice_gcd_term_count") == 1
        and slimgb.get("unit_ideal_prime_count") == 0
        and std.get("unit_ideal_prime_count") == 0
        and slimgb.get("nonunit_ideal_prime_count") == 2
        and std.get("nonunit_ideal_prime_count") == 2
        and slimgb_rows == expected_rows
        and std_rows == expected_rows
        and slimgb.get("checked") is True
        and std.get("checked") is True
    )

    stable_payload = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R206_dual_algorithm_classification_only",
        "algorithms": ["slimgb", "std"],
        "primes": EXPECTED_PRIMES,
        "source_bindings_match": source_bindings_match,
        "algorithm_independent_classification_match": (
            algorithm_independent_classification_match
        ),
        "slice_gcd_total_degree": 0,
        "slice_gcd_term_count": 1,
        "standard_basis_sizes": [7, 7],
        "unit_membership_remainders": ["1", "1"],
        "unit_ideal_prime_count": 0,
        "nonunit_ideal_prime_count": 2,
        "preflight_conclusion": EXPECTED_CONCLUSION,
        "six_minor_unit_certificate_route_supported": False,
        "rational_nullstellensatz_certificate_verified": False,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    result = {
        **stable_payload,
        "adjudication_tool_sha256": sha256_file(Path(__file__)),
        "slimgb_result_sha256": sha256_file(args.slimgb_result),
        "std_result_sha256": sha256_file(args.std_result),
        "slimgb_stable_classification_sha256": slimgb.get(
            "stable_classification_sha256"
        ),
        "std_stable_classification_sha256": std.get(
            "stable_classification_sha256"
        ),
        "slimgb_basis_summary_sha256": [
            row["expanded_engineering"]["basis_summary_sha256"]
            for row in slimgb["prime_rows"]
        ],
        "std_basis_summary_sha256": [
            row["expanded_engineering"]["basis_summary_sha256"]
            for row in std["prime_rows"]
        ],
        "basis_representation_identical": False,
        "basis_representation_note": (
            "slimgb and std emit different noncanonical standard-basis "
            "summaries; the classification invariants agree at both primes"
        ),
        "stable_adjudication_payload": stable_payload,
        "stable_adjudication_sha256": canonical_hash(stable_payload),
        "claim_boundary": (
            "This is a two-prime, two-algorithm modular preflight. It excludes "
            "the known b=0 components but does not prove a rational "
            "Nullstellensatz certificate, global full rank, Quantum PCP, NLTS, "
            "or any frozen-holdout result."
        ),
        "checked": source_bindings_match
        and algorithm_independent_classification_match,
    }
    payload = dict(result)
    result["payload_sha256"] = canonical_hash(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
