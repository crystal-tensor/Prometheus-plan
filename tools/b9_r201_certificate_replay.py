#!/usr/bin/env python3
"""Replay a sparse polynomial ideal-membership certificate with stdlib only."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any


Monomial = tuple[int, ...]
Polynomial = dict[Monomial, Fraction]


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def decode_polynomial(payload: list[list[Any]], variable_count: int) -> Polynomial:
    output: Polynomial = {}
    previous: Monomial | None = None
    for raw_exponents, raw_coefficient in payload:
        exponents = tuple(int(value) for value in raw_exponents)
        if len(exponents) != variable_count or any(value < 0 for value in exponents):
            raise ValueError("invalid monomial exponent vector")
        if not isinstance(raw_coefficient, list) or len(raw_coefficient) != 2:
            raise ValueError("coefficient must be [numerator, denominator]")
        coefficient = Fraction(int(raw_coefficient[0]), int(raw_coefficient[1]))
        if coefficient == 0 or exponents in output:
            raise ValueError("zero or duplicate sparse term")
        if previous is not None and exponents >= previous:
            raise ValueError("sparse terms must be strictly descending")
        output[exponents] = coefficient
        previous = exponents
    return output


def add(left: Polynomial, right: Polynomial) -> Polynomial:
    output = dict(left)
    for monomial, coefficient in right.items():
        value = output.get(monomial, Fraction(0)) + coefficient
        if value:
            output[monomial] = value
        else:
            output.pop(monomial, None)
    return output


def multiply(left: Polynomial, right: Polynomial) -> Polynomial:
    output: Polynomial = {}
    for left_monomial, left_coefficient in left.items():
        for right_monomial, right_coefficient in right.items():
            monomial = tuple(
                left_value + right_value
                for left_value, right_value in zip(left_monomial, right_monomial)
            )
            output[monomial] = (
                output.get(monomial, Fraction(0))
                + left_coefficient * right_coefficient
            )
    return {monomial: value for monomial, value in output.items() if value}


def replay(certificate: dict[str, Any]) -> dict[str, Any]:
    variables = certificate.get("variables", [])
    generators = certificate.get("generators", [])
    multipliers = certificate.get("multipliers", [])
    errors: list[str] = []
    if certificate.get("schema") != "sparse-nullstellensatz-v1":
        errors.append("schema")
    if not variables or len(set(variables)) != len(variables):
        errors.append("variables")
    if len(generators) != len(multipliers) or not generators:
        errors.append("generator_multiplier_count")
    if errors:
        return {"checked": False, "errors": errors}

    variable_count = len(variables)
    decoded_generators = []
    decoded_multipliers = []
    for index, record in enumerate(generators):
        if canonical_hash(record["terms"]) != record.get("terms_sha256"):
            errors.append(f"generator_{index}_hash")
        decoded_generators.append(decode_polynomial(record["terms"], variable_count))
    for index, record in enumerate(multipliers):
        if canonical_hash(record["terms"]) != record.get("terms_sha256"):
            errors.append(f"multiplier_{index}_hash")
        decoded_multipliers.append(decode_polynomial(record["terms"], variable_count))

    target_record = certificate.get("target", {})
    if canonical_hash(target_record.get("terms", [])) != target_record.get("terms_sha256"):
        errors.append("target_hash")
    target = decode_polynomial(target_record.get("terms", []), variable_count)
    total: Polynomial = {}
    for generator, multiplier in zip(decoded_generators, decoded_multipliers):
        total = add(total, multiply(generator, multiplier))
    if total != target:
        errors.append("identity")

    bundle = {
        "variables": variables,
        "generators": generators,
        "target": target_record,
    }
    expected_bundle_hash = certificate.get("generator_bundle_sha256")
    if canonical_hash(bundle) != expected_bundle_hash:
        errors.append("generator_bundle_hash")
    return {
        "schema": certificate.get("schema"),
        "variable_count": variable_count,
        "generator_count": len(generators),
        "generator_term_count": sum(len(record["terms"]) for record in generators),
        "multiplier_term_count": sum(len(record["terms"]) for record in multipliers),
        "generator_bundle_sha256": canonical_hash(bundle),
        "identity_sha256": canonical_hash(
            sorted(
                [list(monomial), [str(value.numerator), str(value.denominator)]]
                for monomial, value in total.items()
            )
        ),
        "errors": errors,
        "checked": not errors,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("certificate", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    certificate = json.loads(
        args.certificate.read_text(), object_pairs_hook=strict_object
    )
    result = replay(certificate)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
