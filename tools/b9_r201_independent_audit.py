#!/usr/bin/env python3
"""Independent exact-algebra auditor for B9 R201.

This file owns its Pauli arithmetic, homogeneous frame, candidate generator,
row selection, determinant reconstruction, and Groebner replay. It does not
import any R193-R201 project module.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import subprocess
import sys
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any, Iterable

import sympy as sp


EXPERIMENT_ID = "B9-R201-independent-projective-patch-audit"
METHOD = "b9_r201_independent_exact_projective_patch_audit_v1"
VERSION = "0.1.0"
CONTRACT_PATH = Path("benchmarks/B9_R201_projective_patch_contract_v0.json")
SOURCE_PATH = Path("results/B9_R201_projective_patch_certificate_v1.json")
AUDIT_PATH = Path("results/B9_R201_independent_audit_v1.json")
SEAL_PATH = Path("results/B9_R201_independent_audit_seal_v0.json")
EXPECTED_CONTRACT_SHA256 = "b3c960f5081a776ccd7165c0146c39e81bf6170820ac593c0f37c8b928b6cb99"
FROZEN_COUPLINGS = (Fraction(127, 128), Fraction(131, 128))
AUDIT_ANCHORS = ((1, -1, 1), (2, 1, 1), (-1, 2, 1), (1, 2, 3))
MAIN_ANCHORS = (
    (0, 0, 1),
    (1, 0, 1),
    (0, 1, 1),
    (1, 1, 1),
    (-1, 1, 2),
    (2, -1, 1),
    (1, 0, 0),
    (0, 1, 0),
    (-2, 1, 3),
    (1, -2, 3),
    (2, 2, 1),
    (-1, -2, 2),
    (3, -1, 2),
    (1, 3, 2),
)
BASIS_SELECTION_PRIME = 1_000_003
MAX_SELECTED_MINORS = 12
FORBIDDEN_IMPORT_PREFIXES = tuple(f"b9_r{index}" for index in range(193, 202))
FORBIDDEN_IMPORT_MODULES = {"importlib", "runpy", "pickle", "marshal", "socket"}
FORBIDDEN_CALLS = {"exec", "eval", "compile", "__import__"}
SOURCE_FIELDS_CONSUMED_FOR_REBUILD: tuple[str, ...] = (
    "coupling",
    "n",
    "minor_records",
    "matrix_sha256",
    "candidate_labels_sha256",
    "unit_ideal",
    "groebner_basis_sha256",
    "groebner_basis_expressions",
)

A, B, C, U = sp.symbols("a b c u")
D = A * A + B * B + C * C
VARS = (A, B, C)
PolynomialOperator = dict[str, sp.Poly]
Operator = dict[str, int]

PAULI_PRODUCT = {
    ("I", "I"): (1, "I"),
    ("I", "X"): (1, "X"),
    ("I", "Y"): (1, "Y"),
    ("I", "Z"): (1, "Z"),
    ("X", "I"): (1, "X"),
    ("Y", "I"): (1, "Y"),
    ("Z", "I"): (1, "Z"),
    ("X", "X"): (1, "I"),
    ("Y", "Y"): (1, "I"),
    ("Z", "Z"): (1, "I"),
    ("X", "Y"): (1j, "Z"),
    ("Y", "X"): (-1j, "Z"),
    ("Y", "Z"): (1j, "X"),
    ("Z", "Y"): (-1j, "X"),
    ("Z", "X"): (1j, "Y"),
    ("X", "Z"): (-1j, "Y"),
}


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def lcm(values: Iterable[int]) -> int:
    result = 1
    for value in values:
        result = math.lcm(result, value)
    return result


def primitive(terms: dict[str, Fraction]) -> Operator:
    clean = {word: Fraction(value) for word, value in terms.items() if value}
    denominator = lcm(value.denominator for value in clean.values())
    integers = {word: int(value * denominator) for word, value in clean.items()}
    divisor = 0
    for value in integers.values():
        divisor = math.gcd(divisor, abs(value))
    integers = {word: value // divisor for word, value in integers.items() if value}
    first = min(integers)
    if integers[first] < 0:
        integers = {word: -value for word, value in integers.items()}
    return dict(sorted(integers.items()))


def pauli_word(n: int, operations: dict[int, str]) -> str:
    chars = ["I"] * n
    for site, pauli in operations.items():
        chars[site] = pauli
    return "".join(chars)


def hamiltonian(n: int, coupling: Fraction) -> Operator:
    terms: dict[str, Fraction] = {}
    for site in range(n):
        terms[pauli_word(n, {site: "X"})] = Fraction(-1)
        terms[pauli_word(n, {site: "Z"})] = Fraction(3, 4)
    for site in range(n - 1):
        terms[pauli_word(n, {site: "Z", site + 1: "Z"})] = coupling
    return primitive(terms)


def anticommutes(left: str, right: str) -> bool:
    return sum(a != "I" and b != "I" and a != b for a, b in zip(left, right)) % 2 == 1


def multiply(left: str, right: str) -> tuple[complex, str]:
    phase: complex = 1
    output = []
    for a, b in zip(left, right):
        local_phase, local_output = PAULI_PRODUCT[(a, b)]
        phase *= local_phase
        output.append(local_output)
    return phase, "".join(output)


def axes() -> dict[str, dict[str, sp.Expr]]:
    return {
        "P": {"X": 2 * A * C, "Y": 2 * B * C, "Z": C * C - A * A - B * B},
        "Q": {"X": C * C - A * A + B * B, "Y": -2 * A * B, "Z": -2 * A * C},
        "R": {"X": -2 * A * B, "Y": C * C + A * A - B * B, "Z": -2 * B * C},
    }


def frame_checks() -> dict[str, Any]:
    frame = axes()
    p, q, r = (
        sp.Matrix([frame[label].get(pauli, 0) for pauli in "XYZ"])
        for label in ("P", "Q", "R")
    )
    values = [
        p.dot(p) - D**2,
        q.dot(q) - D**2,
        r.dot(r) - D**2,
        p.dot(q),
        q.dot(r),
        r.dot(p),
        *list(p.cross(q) - D * r),
        *list(q.cross(r) - D * p),
        *list(r.cross(p) - D * q),
        sp.det(sp.Matrix.hstack(p, q, r)) - D**3,
    ]
    expanded = [sp.expand(value) for value in values]
    return {
        "scalar_identity_count": len(expanded),
        "scalar_identity_pass_count": sum(value == 0 for value in expanded),
        "checked": all(value == 0 for value in expanded),
    }


def expand_axes(n: int, site_axes: dict[int, dict[str, sp.Expr]], scale: int = 1) -> PolynomialOperator:
    partial: dict[str, sp.Expr] = {"I" * n: sp.Integer(scale)}
    for site in sorted(site_axes):
        updated: dict[str, sp.Expr] = {}
        for word, coefficient in partial.items():
            for pauli, local in site_axes[site].items():
                chars = list(word)
                chars[site] = pauli
                output = "".join(chars)
                updated[output] = sp.expand(updated.get(output, 0) + coefficient * local)
        partial = updated
    return {
        word: sp.Poly(value, *VARS, domain=sp.ZZ)
        for word, value in partial.items()
        if value != 0
    }


@cache
def candidate_pool(n: int) -> tuple[tuple[str, PolynomialOperator], ...]:
    frame = axes()
    gamma_labels = [(site, endpoint) for site in range(n) for endpoint in ("Q", "R")]
    entries: list[tuple[str, PolynomialOperator]] = []
    for site, endpoint in gamma_labels:
        local = {index: frame["P"] for index in range(site)}
        local[site] = frame[endpoint]
        entries.append((f"gamma:{site}:{endpoint}", expand_axes(n, local)))
    for left_index, (left_site, left_endpoint) in enumerate(gamma_labels):
        for right_site, right_endpoint in gamma_labels[left_index + 1 :]:
            if left_site == right_site:
                operator = expand_axes(n, {left_site: frame["P"]}, scale=-1)
            else:
                local: dict[int, dict[str, sp.Expr]] = {}
                sign = 1
                if left_endpoint == "Q":
                    local[left_site] = frame["R"]
                else:
                    local[left_site] = frame["Q"]
                    sign = -1
                for site in range(left_site + 1, right_site):
                    local[site] = frame["P"]
                local[right_site] = frame[right_endpoint]
                operator = expand_axes(n, local, scale=sign)
            entries.append((f"bilinear:{left_site}:{left_endpoint}:{right_site}:{right_endpoint}", operator))
    entries.append(("parity", expand_axes(n, {site: frame["P"] for site in range(n)})))
    return tuple(entries)


def commutator(h_value: Operator, candidate: PolynomialOperator) -> PolynomialOperator:
    output: dict[str, sp.Poly] = {}
    zero = sp.Poly(0, *VARS, domain=sp.ZZ)
    for h_word, h_coefficient in h_value.items():
        for candidate_word, candidate_coefficient in candidate.items():
            if not anticommutes(h_word, candidate_word):
                continue
            phase, output_word = multiply(h_word, candidate_word)
            sign = int(round((phase / 1j).real))
            output[output_word] = output.get(output_word, zero) + candidate_coefficient * h_coefficient * sign
    return {
        word: sp.Poly(value, *VARS, domain=sp.ZZ)
        for word, value in output.items()
        if not value.is_zero
    }


def poly_payload(poly: sp.Poly) -> list[list[Any]]:
    return [[list(monomial), str(int(coefficient))] for monomial, coefficient in poly.terms()]


def symbolic_matrix(n: int, coupling: Fraction) -> tuple[list[str], list[PolynomialOperator], list[str], str]:
    entries = list(candidate_pool(n))
    labels = [label for label, _ in entries]
    columns = [commutator(hamiltonian(n, coupling), operator) for _, operator in entries]
    output_words = sorted({word for column in columns for word in column})
    triples = [
        [word, column_index, poly_payload(value)]
        for column_index, column in enumerate(columns)
        for word, value in sorted(column.items())
    ]
    return labels, columns, output_words, canonical_hash(
        {"labels": labels, "output_words": output_words, "triples": triples}
    )


def select_rows(columns: list[PolynomialOperator], output_words: list[str], anchor: tuple[int, int, int]) -> list[str]:
    substitutions = dict(zip(VARS, anchor))
    pivots: dict[int, dict[int, int]] = {}
    selected = []
    for word in output_words:
        vector = {
            index: int(column.get(word, sp.Poly(0, *VARS, domain=sp.ZZ)).as_expr().subs(substitutions))
            % BASIS_SELECTION_PRIME
            for index, column in enumerate(columns)
        }
        vector = {index: value for index, value in vector.items() if value}
        while vector:
            pivot = min(vector)
            if pivot not in pivots:
                inverse = pow(vector[pivot], BASIS_SELECTION_PRIME - 2, BASIS_SELECTION_PRIME)
                pivots[pivot] = {
                    index: value * inverse % BASIS_SELECTION_PRIME for index, value in vector.items()
                }
                selected.append(word)
                break
            factor = vector[pivot]
            for index, value in pivots[pivot].items():
                updated = (vector.get(index, 0) - factor * value) % BASIS_SELECTION_PRIME
                if updated:
                    vector[index] = updated
                else:
                    vector.pop(index, None)
        if len(selected) == len(columns):
            break
    return selected


def primitive_poly(poly: sp.Poly) -> sp.Poly:
    _, value = sp.polys.polytools.primitive(sp.Poly(poly, *VARS, domain=sp.ZZ))
    value = sp.Poly(value, *VARS, domain=sp.ZZ)
    return -value if value.LC() < 0 else value


def determinant(columns: list[PolynomialOperator], rows: list[str]) -> sp.Poly:
    matrix = sp.Matrix(
        [
            [column.get(word, sp.Poly(0, *VARS, domain=sp.ZZ)).as_expr() for column in columns]
            for word in rows
        ]
    )
    return primitive_poly(sp.Poly(matrix.det(method="domain-ge"), *VARS, domain=sp.ZZ))


def ast_anti_circularity(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text())
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root.startswith(FORBIDDEN_IMPORT_PREFIXES) or root in FORBIDDEN_IMPORT_MODULES:
                    violations.append(f"import:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            root = module.split(".")[0]
            if root.startswith(FORBIDDEN_IMPORT_PREFIXES) or root in FORBIDDEN_IMPORT_MODULES:
                violations.append(f"from:{module}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            violations.append(f"call:{node.func.id}")
    return {"violations": sorted(set(violations)), "checked": not violations}


def build_seal(root: Path) -> dict[str, Any]:
    contract = json.loads((root / CONTRACT_PATH).read_text())
    main_anchors = {tuple(values) for values in contract["engineering_probe"]["anchor_points"]}
    audit_anchors = {tuple(values) for values in contract["independent_audit"]["audit_owned_anchor_points"]}
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "status": "independent_pre_source_seal_complete",
        "contract_sha256": sha256_file(root / CONTRACT_PATH),
        "expected_contract_sha256": EXPECTED_CONTRACT_SHA256,
        "frozen_couplings": [fraction_text(value) for value in FROZEN_COUPLINGS],
        "audit_owned_anchor_points": [list(value) for value in AUDIT_ANCHORS],
        "main_and_audit_anchor_sets_disjoint": main_anchors.isdisjoint(audit_anchors),
        "frame_checks": frame_checks(),
        "candidate_column_counts": {str(n): len(candidate_pool(n)) for n in (4, 5, 6)},
        "anti_circularity": ast_anti_circularity(Path(__file__).resolve()),
        "source_fields_consumed_for_rebuild": list(SOURCE_FIELDS_CONSUMED_FOR_REBUILD),
        "source_result_read": False,
        "checked": bool(
            sha256_file(root / CONTRACT_PATH) == EXPECTED_CONTRACT_SHA256
            and main_anchors.isdisjoint(audit_anchors)
            and frame_checks()["checked"]
            and ast_anti_circularity(Path(__file__).resolve())["checked"]
        ),
    }
    payload["payload_sha256"] = canonical_hash(payload)
    return payload


def rebuild_row(source_row: dict[str, Any]) -> dict[str, Any]:
    coupling = Fraction(source_row["coupling"])
    n = int(source_row["n"])
    labels, columns, output_words, matrix_hash = symbolic_matrix(n, coupling)
    row_sets = []
    seen = set()
    for anchor in MAIN_ANCHORS:
        rows = select_rows(columns, output_words, anchor)
        digest = canonical_hash(rows)
        if len(rows) == len(columns) and digest not in seen:
            seen.add(digest)
            row_sets.append(rows)
        if len(row_sets) == MAX_SELECTED_MINORS:
            break
    source_records = source_row.get("minor_records", [])
    rebuilt_records = []
    determinants = []
    for rows in row_sets[: len(source_records)]:
        value = determinant(columns, rows)
        determinants.append(value)
        rebuilt_records.append(
            {
                "row_words_sha256": canonical_hash(rows),
                "total_degree": value.total_degree(),
                "term_count": len(value.terms()),
                "primitive_terms": poly_payload(value),
                "primitive_terms_sha256": canonical_hash(poly_payload(value)),
            }
        )
    basis = (
        sp.groebner(
            [value.as_expr() for value in determinants] + [1 - U * D],
            U,
            A,
            B,
            C,
            order="grevlex",
            domain=sp.QQ,
        )
        if determinants
        else None
    )
    unit_ideal = bool(basis and len(basis.polys) == 1 and basis.polys[0].as_expr() == 1)
    errors = []
    if matrix_hash != source_row.get("matrix_sha256"):
        errors.append("matrix_sha256")
    if canonical_hash(labels) != source_row.get("candidate_labels_sha256"):
        errors.append("candidate_labels_sha256")
    if rebuilt_records != source_records:
        errors.append("minor_records")
    if unit_ideal != source_row.get("unit_ideal"):
        errors.append("unit_ideal")
    if basis and canonical_hash([str(poly.as_expr()) for poly in basis.polys]) != source_row.get("groebner_basis_sha256"):
        errors.append("groebner_basis_sha256")
    if basis and [str(poly.as_expr()) for poly in basis.polys] != source_row.get("groebner_basis_expressions"):
        errors.append("groebner_basis_expressions")
    return {
        "coupling": fraction_text(coupling),
        "n": n,
        "candidate_column_count": len(columns),
        "matrix_sha256": matrix_hash,
        "minor_count": len(determinants),
        "unit_ideal": unit_ideal,
        "errors": errors,
        "checked": not errors,
    }


def build_audit(root: Path) -> dict[str, Any]:
    source = json.loads((root / SOURCE_PATH).read_text())
    seal = build_seal(root)
    source_rows = [*source.get("n4_rows", []), *source.get("n5_rows", [])]
    rebuilt = [rebuild_row(row) for row in source_rows]
    errors = []
    if not seal["checked"]:
        errors.append("pre_source_seal")
    if source.get("public_freeze", {}).get("verified") is not True:
        errors.append("public_freeze")
    expected_keys = {
        (fraction_text(coupling), n)
        for coupling in FROZEN_COUPLINGS
        for n in ((4, 5) if source.get("n5_execution_condition_satisfied") else (4,))
    }
    actual_keys = {(row["coupling"], row["n"]) for row in rebuilt}
    if actual_keys != expected_keys:
        errors.append("row_keys")
    if not all(row["checked"] for row in rebuilt):
        errors.append("independent_rebuild")
    if source.get("scientific_promotion_accepted") is not False or source.get("new_credit_delta") != 0:
        errors.append("claim_boundary")
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "status": "pass" if not errors else "fail",
        "pre_source_seal": seal,
        "source_result_read": True,
        "source_fields_consumed_for_rebuild": list(SOURCE_FIELDS_CONSUMED_FOR_REBUILD),
        "rebuilt_rows": rebuilt,
        "errors": errors,
        "checked": not errors,
    }
    payload["payload_sha256"] = canonical_hash(payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--seal", action="store_true")
    modes.add_argument("--audit", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    result = build_seal(root) if args.seal else build_audit(root)
    output = args.output or (SEAL_PATH if args.seal else AUDIT_PATH)
    (root / output).write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
