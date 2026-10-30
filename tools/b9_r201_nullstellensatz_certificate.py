#!/usr/bin/env python3
"""Emit replayable sparse ideal-membership certificates for R201."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

import sympy as sp
from sympy.polys.distributedmodules import (
    sdm_from_vector,
    sdm_groebner,
    sdm_nf_buchberger,
    sdm_to_vector,
)
from sympy.polys.domains import QQ
from sympy.polys.orderings import grevlex

import b9_r201_projective_patch_certificate as r201
from b9_r201_certificate_replay import canonical_hash, replay


VERSION = "0.1.0"
SCHEMA = "sparse-nullstellensatz-v1"
EXPECTED_SYMPY_VERSION = "1.14.0"
ENGINEERING_COUPLING = Fraction(13, 32)
U, A, B, C = sp.symbols("u a b c")
VARIABLES = (U, A, B, C)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encode_poly(expression: sp.Expr) -> list[list[Any]]:
    poly = sp.Poly(expression, *VARIABLES, domain=sp.QQ)
    return [
        [
            list(monomial),
            [str(sp.Rational(coefficient).p), str(sp.Rational(coefficient).q)],
        ]
        for monomial, coefficient in poly.terms()
    ]


def polynomial_record(label: str, expression: sp.Expr) -> dict[str, Any]:
    terms = encode_poly(expression)
    return {
        "label": label,
        "total_degree": sp.Poly(expression, *VARIABLES, domain=sp.QQ).total_degree(),
        "term_count": len(terms),
        "terms": terms,
        "terms_sha256": canonical_hash(terms),
    }


def emit_certificate(
    generators: list[tuple[str, sp.Expr]],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    if sp.__version__ != EXPECTED_SYMPY_VERSION:
        raise RuntimeError(
            f"extended Groebner transition tracking requires SymPy {EXPECTED_SYMPY_VERSION}, "
            f"observed {sp.__version__}"
        )
    started = time.monotonic()
    module_generators = [
        sdm_from_vector([expression], grevlex, QQ, gens=list(VARIABLES))
        for _, expression in generators
    ]
    basis, transitions = sdm_groebner(
        module_generators,
        sdm_nf_buchberger,
        grevlex,
        QQ,
        extended=True,
    )
    constant_index = None
    constant_value = None
    for index, value in enumerate(basis):
        vector = sdm_to_vector(value, list(VARIABLES), QQ)
        poly = sp.Poly(vector[0], *VARIABLES, domain=sp.QQ)
        if poly.total_degree() == 0 and not poly.is_zero:
            constant_index = index
            constant_value = sp.Rational(poly.LC())
            break
    if constant_index is None or constant_value is None:
        raise RuntimeError("the exact generator ideal did not produce a nonzero constant")

    coefficients = sdm_to_vector(
        transitions[constant_index],
        list(VARIABLES),
        QQ,
        n=len(generators),
    )
    multipliers = [sp.expand(expression / constant_value) for expression in coefficients]
    generator_records = [
        polynomial_record(label, expression) for label, expression in generators
    ]
    multiplier_records = [
        polynomial_record(f"multiplier:{label}", expression)
        for (label, _), expression in zip(generators, multipliers)
    ]
    target = polynomial_record("target:one", sp.Integer(1))
    bundle = {
        "variables": [str(value) for value in VARIABLES],
        "generators": generator_records,
        "target": target,
    }
    payload = {
        "schema": SCHEMA,
        "version": VERSION,
        "sympy_version": sp.__version__,
        "variables": bundle["variables"],
        "monomial_order_used_for_discovery": "grevlex(u,a,b,c)",
        "provenance": provenance,
        "generators": generator_records,
        "multipliers": multiplier_records,
        "target": target,
        "generator_bundle_sha256": canonical_hash(bundle),
        "discovery_basis_size": len(basis),
        "discovery_elapsed_seconds": round(time.monotonic() - started, 6),
    }
    check = replay(payload)
    if not check["checked"]:
        raise RuntimeError(f"emitted certificate failed stdlib replay: {check['errors']}")
    payload["stdlib_replay"] = check
    payload["payload_sha256"] = canonical_hash(payload)
    return payload


def toy_certificate(root: Path) -> dict[str, Any]:
    generators = [
        ("toy:a", A),
        ("toy:1+a+b", 1 + A + B),
        ("toy:5-7b", 5 - 7 * B),
    ]
    return emit_certificate(
        generators,
        {
            "mode": "toy_engine_test",
            "purpose": "validate transition tracking and stdlib replay before engineering minors",
            "source_tool_sha256": sha256_file(Path(__file__).resolve()),
        },
    )


def engineering_generators() -> tuple[list[tuple[str, sp.Expr]], dict[str, Any]]:
    labels, columns, output_words, matrix_hash = r201.symbolic_matrix(
        4, ENGINEERING_COUPLING
    )
    seen: set[str] = set()
    generators: list[tuple[str, sp.Expr]] = []
    row_records = []
    for anchor in r201.MAIN_MINOR_ANCHORS:
        rows = r201.select_rows_at_anchor(
            columns, output_words, anchor, r201.BASIS_SELECTION_PRIME
        )
        row_hash = canonical_hash(rows)
        if len(rows) != len(columns) or row_hash in seen:
            continue
        seen.add(row_hash)
        determinant = r201.determinant_for_rows(columns, rows)
        expression = determinant.as_expr().subs(
            {r201.A: A, r201.B: B, r201.C: C}
        )
        generators.append((f"minor:{len(generators)}", expression))
        row_records.append(
            {
                "anchor": list(anchor),
                "row_words_sha256": row_hash,
                "row_words": rows,
                "determinant_total_degree": determinant.total_degree(),
                "determinant_term_count": len(determinant.terms()),
                "determinant_terms_sha256": canonical_hash(r201.poly_payload(determinant)),
            }
        )
        if len(generators) == r201.MAX_SELECTED_MINORS:
            break
    generators.append(("saturation:1-uD", 1 - U * (A * A + B * B + C * C)))
    provenance = {
        "mode": "public_engineering_coupling_only",
        "coupling": "13/32",
        "n": 4,
        "candidate_column_count": len(columns),
        "candidate_labels_sha256": canonical_hash(labels),
        "matrix_sha256": matrix_hash,
        "row_records": row_records,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    return generators, provenance


def mutation_checks(certificate: dict[str, Any]) -> dict[str, Any]:
    cases = []

    changed_multiplier = copy.deepcopy(certificate)
    changed_multiplier["multipliers"][0]["terms"][0][1][0] = str(
        int(changed_multiplier["multipliers"][0]["terms"][0][1][0]) + 1
    )
    cases.append(("multiplier_coefficient", changed_multiplier))

    changed_generator = copy.deepcopy(certificate)
    changed_generator["generators"][0]["terms"][0][0][0] += 1
    cases.append(("generator_exponent", changed_generator))

    changed_hash = copy.deepcopy(certificate)
    changed_hash["generator_bundle_sha256"] = "0" * 64
    cases.append(("bundle_hash", changed_hash))

    records = []
    for label, candidate in cases:
        result = replay(candidate)
        records.append(
            {"label": label, "rejected": not result["checked"], "errors": result["errors"]}
        )
    return {
        "case_count": len(records),
        "rejected_count": sum(record["rejected"] for record in records),
        "records": records,
        "checked": all(record["rejected"] for record in records),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--toy", action="store_true")
    modes.add_argument("--engineering", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mutation-output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.toy:
        certificate = toy_certificate(root)
    else:
        generators, provenance = engineering_generators()
        certificate = emit_certificate(generators, provenance)
    output = args.output if args.output.is_absolute() else root / args.output
    output.write_text(json.dumps(certificate, indent=2, sort_keys=True) + "\n")
    mutations = mutation_checks(certificate)
    if args.mutation_output:
        mutation_output = (
            args.mutation_output
            if args.mutation_output.is_absolute()
            else root / args.mutation_output
        )
        mutation_output.write_text(json.dumps(mutations, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "generator_count": len(certificate["generators"]),
                "multiplier_term_count": certificate["stdlib_replay"]["multiplier_term_count"],
                "replay_checked": certificate["stdlib_replay"]["checked"],
                "mutation_checks": mutations,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if certificate["stdlib_replay"]["checked"] and mutations["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
