#!/usr/bin/env python3
"""Independently replay R205 selected minors with SymPy polynomial arithmetic."""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

import sympy as sp


METHOD = "b9_r205_sympy_polynomial_remainder_independent_audit_v1"
VERSION = "0.1.0"
ENGINEERING_COUPLING = Fraction(13, 32)
SOURCE_RESULT = Path("results/B9_R205_sextic_full_matrix_rank_v0.json")
DENSE_TOOL_PATH = Path("tools/b9_r201_presource_manifest.py")
SOURCE_TOOL_PATH = Path("tools/b9_r201_independent_audit.py")
T = sp.symbols("t")
SEXTIC_EXPRESSION = (
    768 * T**6
    - 256 * T**5
    - 7227 * T**4
    + 5120 * T**3
    + 7227 * T**2
    - 256 * T
    - 768
)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def specialize(expression: sp.Expr, variables: tuple[sp.Symbol, ...]) -> sp.Expr:
    return sp.expand(
        expression.subs(
            {variables[0]: T, variables[1]: sp.Integer(0), variables[2]: sp.Integer(1)}
        )
    )


def source_square(
    source: Any, selected_rows: list[str]
) -> tuple[list[list[sp.Expr]], list[str], str]:
    labels, columns, output_words, source_hash = source.symbolic_matrix(
        4, ENGINEERING_COUPLING
    )
    if not set(selected_rows).issubset(output_words):
        raise ValueError("R205 source selected rows are not in the rebuilt matrix")
    zero = source.sp.Poly(0, *source.VARS, domain=source.sp.ZZ)
    square = [
        [
            specialize(column.get(word, zero).as_expr(), source.VARS)
            for column in columns
        ]
        for word in selected_rows
    ]
    return square, labels, source_hash


def dense_square(
    dense: Any, selected_rows: list[str]
) -> tuple[list[list[sp.Expr]], list[str], str]:
    hamiltonian = dense.primitive_hamiltonian(4, ENGINEERING_COUPLING)
    candidates = dense.candidate_matrices(4)
    labels = [label for label, _ in candidates]
    columns = []
    all_rows: list[str] | None = None
    full_triples = []
    for column_index, (_, candidate) in enumerate(candidates):
        commutator = dense.sp.expand(
            -dense.sp.I * (hamiltonian * candidate - candidate * hamiltonian)
        )
        coordinates = dense.hermitian_coordinates(commutator)
        current_rows = [label for label, _ in coordinates]
        if all_rows is None:
            all_rows = current_rows
        elif all_rows != current_rows:
            raise RuntimeError("dense coordinate order drift")
        expression_map = {label: value for label, value in coordinates}
        if not set(selected_rows).issubset(expression_map):
            raise ValueError("R205 dense selected rows are not in rebuilt coordinates")
        columns.append(
            [specialize(expression_map[row], dense.VARS) for row in selected_rows]
        )
        for label, value in coordinates:
            payload = dense.encode_poly(value)
            if payload and any(
                int(numerator) != 0 for _, (numerator, _) in payload
            ):
                full_triples.append([label, column_index, payload])
    square = [
        [columns[column][row] for column in range(len(columns))]
        for row in range(len(selected_rows))
    ]
    return square, labels, canonical_hash(full_triples)


def determinant_residue(square: list[list[sp.Expr]], prime: int) -> list[int]:
    modulus = sp.Poly(SEXTIC_EXPRESSION, T, modulus=prime)
    if modulus.is_irreducible is not True:
        raise ValueError(f"sextic is not irreducible modulo {prime}")
    rows = [
        [sp.Poly(value, T, modulus=prime).rem(modulus) for value in row]
        for row in square
    ]
    zero = sp.Poly(0, T, modulus=prime)
    determinant = sp.Poly(1, T, modulus=prime)
    for column in range(len(rows)):
        pivot = next(
            (
                index
                for index in range(column, len(rows))
                if rows[index][column] != zero
            ),
            None,
        )
        if pivot is None:
            return [0] * 6
        if pivot != column:
            rows[column], rows[pivot] = rows[pivot], rows[column]
            determinant = -determinant
        pivot_value = rows[column][column]
        determinant = (determinant * pivot_value).rem(modulus)
        inverse = sp.invert(pivot_value, modulus)
        rows[column] = [(value * inverse).rem(modulus) for value in rows[column]]
        for index in range(column + 1, len(rows)):
            factor = rows[index][column]
            if factor == zero:
                continue
            rows[index] = [
                (left - factor * right).rem(modulus)
                for left, right in zip(rows[index], rows[column])
            ]
    determinant = determinant.rem(modulus)
    return [int(determinant.nth(degree)) % prime for degree in range(6)]


def ast_independence(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text())
    forbidden = {"b9_r205_sextic_full_matrix_rank"}
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            violations.extend(
                f"import:{alias.name}"
                for alias in node.names
                if alias.name in forbidden
            )
        elif isinstance(node, ast.ImportFrom) and (node.module or "") in forbidden:
            violations.append(f"from:{node.module}")
    return {"violations": violations, "checked": not violations}


def build_result(root: Path) -> dict[str, Any]:
    result_path = root / SOURCE_RESULT
    source_result = json.loads(result_path.read_text())
    if source_result.get("checked") is not True:
        raise ValueError("R205 source result is not checked")
    certificate_by_name = {
        row["representation"]: row
        for row in source_result.get("representation_certificates", [])
    }
    dense = load_module(root / DENSE_TOOL_PATH, "b9_r205_audit_dense_dependency")
    source = load_module(root / SOURCE_TOOL_PATH, "b9_r205_audit_source_dependency")
    route_specs = [
        (
            "independent_sparse_Pauli_word_matrix",
            source_square,
            source,
        ),
        (
            "dense_Kronecker_Hermitian_coordinate_matrix",
            dense_square,
            dense,
        ),
    ]
    rows = []
    candidate_hashes = []
    for name, builder, dependency in route_specs:
        certificate = certificate_by_name.get(name)
        if not certificate:
            raise ValueError(f"R205 certificate missing: {name}")
        selected_rows = certificate["selected_rows"]
        square, labels, parent_hash = builder(dependency, selected_rows)
        candidate_hash = canonical_hash(labels)
        candidate_hashes.append(candidate_hash)
        replays = []
        for expected in certificate["prime_replays"]:
            prime = int(expected["prime"])
            observed = determinant_residue(square, prime)
            replays.append(
                {
                    "prime": prime,
                    "observed_coefficients_low_to_high": observed,
                    "observed_sha256": canonical_hash(observed),
                    "expected_coefficients_low_to_high": expected[
                        "determinant_residue_coefficients_low_to_high"
                    ],
                    "expected_sha256": expected["determinant_residue_sha256"],
                    "coefficient_match": observed
                    == expected["determinant_residue_coefficients_low_to_high"],
                    "hash_match": canonical_hash(observed)
                    == expected["determinant_residue_sha256"],
                    "nonzero": any(observed),
                }
            )
        rows.append(
            {
                "representation": name,
                "shape": certificate["shape"],
                "candidate_labels_sha256": candidate_hash,
                "parent_symbolic_matrix_sha256": parent_hash,
                "selected_rows_sha256": canonical_hash(selected_rows),
                "selected_row_count": len(selected_rows),
                "prime_replays": replays,
                "all_replays_match": all(
                    replay["coefficient_match"]
                    and replay["hash_match"]
                    and replay["nonzero"]
                    for replay in replays
                ),
            }
        )
    independence = ast_independence(Path(__file__).resolve())
    checked = bool(
        len(rows) == 2
        and len(set(candidate_hashes)) == 1
        and all(row["selected_row_count"] == 37 for row in rows)
        and all(row["all_replays_match"] for row in rows)
        and independence["checked"]
    )
    stable = {
        "source_result_sha256": sha256_file(result_path),
        "source_dependency_sha256": sha256_file(root / SOURCE_TOOL_PATH),
        "dense_dependency_sha256": sha256_file(root / DENSE_TOOL_PATH),
        "representation_rows": rows,
        "implementation_independence": independence,
    }
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "independent_R205_selected_minor_replay_only",
        "source_result_sha256": stable["source_result_sha256"],
        "source_dependency_sha256": stable["source_dependency_sha256"],
        "dense_dependency_sha256": stable["dense_dependency_sha256"],
        "arithmetic_path": "SymPy_Poly_rem_invert_and_Gaussian_elimination",
        "imports_R205_field_implementation": False,
        "implementation_independence": independence,
        "representation_rows": rows,
        "matched_representation_count": sum(
            row["all_replays_match"] for row in rows
        ),
        "matched_determinant_replay_count": sum(
            replay["coefficient_match"] and replay["hash_match"]
            for row in rows
            for replay in row["prime_replays"]
        ),
        "all_four_determinant_residues_independently_reproduced": all(
            row["all_replays_match"] for row in rows
        ),
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "stable_audit_payload": stable,
        "stable_audit_sha256": canonical_hash(stable),
        "checked": checked,
    }
    payload = dict(result)
    result["payload_sha256"] = canonical_hash(payload)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = build_result(root)
    output = args.output if args.output.is_absolute() else root / args.output
    output.write_text(
        json.dumps(result, indent=2 if args.pretty else None, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "checked": result["checked"],
                "matched_representation_count": result[
                    "matched_representation_count"
                ],
                "matched_determinant_replay_count": result[
                    "matched_determinant_replay_count"
                ],
                "new_credit_delta": result["new_credit_delta"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
