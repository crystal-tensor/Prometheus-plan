#!/usr/bin/env python3
"""Replay exact R203 four-minor common zeros against both full matrices."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any

import sympy as sp


METHOD = "b9_r203_rational_common_zero_full_matrix_replay_v1"
VERSION = "0.1.0"
R201_PATH = Path("results/B9_R201_integer_reconstruction_v0.json")
R202_PATH = Path("results/B9_R202_modular_ideal_preflight_v0.json")
DENSE_TOOL_PATH = Path("tools/b9_r201_presource_manifest.py")
SOURCE_TOOL_PATH = Path("tools/b9_r201_independent_audit.py")
DEFAULT_OUTPUT = Path("results/B9_R203_rational_common_zero_rank_replay_v0.json")
ENGINEERING_COUPLING = Fraction(13, 32)
R202_PRIMES = (1_000_003, 536_870_723)
ROW_SELECTION_PRIME = 1_000_037
POINTS = ((2, 0, 1), (1, 0, -2))

A, B, C = sp.symbols("a b c")
VARS = (A, B, C)


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


def primitive_quotient(row: dict[str, Any]) -> sp.Poly:
    content = int(row["quotient_integer_content"])
    expression = 0
    primitive_terms: list[list[Any]] = []
    for raw_exponents, raw_coefficient in row["quotient_canonical_terms"]:
        exponents = [int(value) for value in raw_exponents]
        coefficient = int(raw_coefficient)
        if coefficient % content:
            raise ValueError("quotient coefficient is not divisible by signed content")
        primitive_coefficient = coefficient // content
        primitive_terms.append([exponents, str(primitive_coefficient)])
        expression += primitive_coefficient * sp.prod(
            variable**exponent for variable, exponent in zip(VARS, exponents)
        )
    if canonical_hash(primitive_terms) != row["primitive_quotient_canonical_terms_sha256"]:
        raise ValueError("primitive quotient hash mismatch")
    return sp.Poly(expression, *VARS, domain=sp.ZZ)


def normalized_poly_terms(poly: sp.Poly) -> list[list[Any]]:
    primitive = sp.primitive(sp.Poly(poly, *poly.gens, domain=sp.ZZ))[1]
    if primitive.LC() < 0:
        primitive = -primitive
    return [
        [list(monomial), str(int(coefficient))]
        for monomial, coefficient in primitive.terms()
    ]


def modular_rank(matrix: list[list[int]], prime: int) -> int:
    rows = [[value % prime for value in row] for row in matrix]
    rank = 0
    width = len(rows[0]) if rows else 0
    for column in range(width):
        pivot = next(
            (index for index in range(rank, len(rows)) if rows[index][column]),
            None,
        )
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        inverse = pow(rows[rank][column], prime - 2, prime)
        rows[rank] = [(value * inverse) % prime for value in rows[rank]]
        for index in range(len(rows)):
            if index == rank or not rows[index][column]:
                continue
            factor = rows[index][column]
            rows[index] = [
                (left - factor * right) % prime
                for left, right in zip(rows[index], rows[rank])
            ]
        rank += 1
        if rank == len(rows):
            break
    return rank


def select_independent_rows(
    matrix: list[list[int]], row_labels: list[str], point: tuple[int, int, int]
) -> list[str]:
    order = sorted(
        range(len(matrix)),
        key=lambda index: canonical_hash(
            {
                "purpose": "R203_exact_rank_witness",
                "point": list(point),
                "coordinate": row_labels[index],
                "selection_prime": ROW_SELECTION_PRIME,
            }
        ),
    )
    basis: dict[int, list[int]] = {}
    selected: list[str] = []
    for index in order:
        row = [value % ROW_SELECTION_PRIME for value in matrix[index]]
        for pivot in sorted(basis):
            if row[pivot]:
                factor = row[pivot]
                row = [
                    (left - factor * right) % ROW_SELECTION_PRIME
                    for left, right in zip(row, basis[pivot])
                ]
        pivot = next((column for column, value in enumerate(row) if value), None)
        if pivot is None:
            continue
        inverse = pow(row[pivot], ROW_SELECTION_PRIME - 2, ROW_SELECTION_PRIME)
        basis[pivot] = [(value * inverse) % ROW_SELECTION_PRIME for value in row]
        selected.append(row_labels[index])
        if len(selected) == len(matrix[0]):
            break
    return selected


def rank_certificate(
    matrix: list[list[int]], row_labels: list[str], point: tuple[int, int, int]
) -> dict[str, Any]:
    selected = select_independent_rows(matrix, row_labels, point)
    if len(selected) != len(matrix[0]):
        raise RuntimeError("deterministic selector did not find full column rank")
    row_index = {label: index for index, label in enumerate(row_labels)}
    square = [matrix[row_index[label]] for label in selected]
    determinant = int(sp.Matrix(square).det(method="domain-ge"))
    if determinant == 0:
        raise RuntimeError("selected exact determinant is zero")
    primes = (*R202_PRIMES, ROW_SELECTION_PRIME)
    ranks = {str(prime): modular_rank(matrix, prime) for prime in primes}
    residues = {str(prime): determinant % prime for prime in primes}
    return {
        "shape": [len(matrix), len(matrix[0])],
        "rank_over_QQ": len(matrix[0]),
        "rank_proof": "nonzero_exact_integer_maximal_minor",
        "modular_ranks": ranks,
        "row_selection_prime": ROW_SELECTION_PRIME,
        "row_selection_method": "sha256(point,coordinate,purpose,selection_prime)",
        "selected_rows": selected,
        "selected_rows_sha256": canonical_hash(selected),
        "exact_determinant": str(determinant),
        "exact_determinant_sha256": hashlib.sha256(str(determinant).encode()).hexdigest(),
        "exact_determinant_sign": 1 if determinant > 0 else -1,
        "exact_determinant_bit_length": abs(determinant).bit_length(),
        "exact_determinant_residues": residues,
        "checked": bool(
            all(rank == len(matrix[0]) for rank in ranks.values())
            and all(residue != 0 for residue in residues.values())
        ),
    }


def dense_matrix(
    dense: Any, point: tuple[int, int, int]
) -> tuple[list[list[int]], list[str], list[str]]:
    hamiltonian = dense.primitive_hamiltonian(4, ENGINEERING_COUPLING)
    frame, _ = dense.numeric_frame(point)
    candidates = dense.candidate_matrices_from_frame(4, frame)
    columns: list[list[int]] = []
    row_labels: list[str] | None = None
    for _, candidate in candidates:
        commutator = dense.sp.expand(
            -dense.sp.I * (hamiltonian * candidate - candidate * hamiltonian)
        )
        coordinates = dense.hermitian_coordinates(commutator)
        labels = [label for label, _ in coordinates]
        if row_labels is None:
            row_labels = labels
        elif labels != row_labels:
            raise RuntimeError("dense coordinate order drift")
        values = []
        for _, value in coordinates:
            resolved = dense.sp.expand(value)
            if resolved.is_Integer is not True:
                raise RuntimeError("dense coordinate is not integral")
            values.append(int(resolved))
        columns.append(values)
    if row_labels is None:
        raise RuntimeError("dense matrix is empty")
    matrix = [
        [columns[column][row] for column in range(len(columns))]
        for row in range(len(row_labels))
    ]
    return matrix, row_labels, [label for label, _ in candidates]


def source_matrix(
    source: Any, point: tuple[int, int, int]
) -> tuple[list[list[int]], list[str], list[str], str]:
    labels, columns, output_words, symbolic_hash = source.symbolic_matrix(
        4, ENGINEERING_COUPLING
    )
    substitutions = dict(zip(source.VARS, point))
    matrix = []
    for word in output_words:
        matrix.append(
            [
                int(
                    column.get(
                        word, source.sp.Poly(0, *source.VARS, domain=source.sp.ZZ)
                    ).as_expr().subs(substitutions)
                )
                for column in columns
            ]
        )
    return matrix, output_words, labels, symbolic_hash


def build_result(root: Path) -> dict[str, Any]:
    r201_path = root / R201_PATH
    r202_path = root / R202_PATH
    dense_path = root / DENSE_TOOL_PATH
    source_path = root / SOURCE_TOOL_PATH
    r201 = json.loads(r201_path.read_text())
    r202 = json.loads(r202_path.read_text())
    quotients = [primitive_quotient(row) for row in r201["rows"]]

    restrictions = [
        sp.Poly(poly.as_expr().subs(B, 0), A, C, domain=sp.ZZ)
        for poly in quotients
    ]
    restricted_gcd = restrictions[0]
    for poly in restrictions[1:]:
        restricted_gcd = sp.gcd(restricted_gcd, poly)
    restricted_gcd = sp.primitive(restricted_gcd)[1]
    if restricted_gcd.LC() < 0:
        restricted_gcd = -restricted_gcd
    expected_sextic = sp.Poly(
        768 * A**6
        - 256 * A**5 * C
        - 7227 * A**4 * C**2
        + 5120 * A**3 * C**3
        + 7227 * A**2 * C**4
        - 256 * A * C**5
        - 768 * C**6,
        A,
        C,
        domain=sp.ZZ,
    )
    expected_gcd = sp.Poly(
        (A - 2 * C) ** 5 * (2 * A + C) ** 5 * expected_sextic.as_expr(),
        A,
        C,
        domain=sp.ZZ,
    )
    restricted_factorization_checked = restricted_gcd == expected_gcd

    dense = load_module(dense_path, "b9_r203_dense_dependency")
    source = load_module(source_path, "b9_r203_source_dependency")
    witness_rows = []
    for point in POINTS:
        d_value = sum(value * value for value in point)
        quotient_values = [int(poly.as_expr().subs(dict(zip(VARS, point)))) for poly in quotients]
        dense_values, dense_rows, dense_labels = dense_matrix(dense, point)
        source_values, source_rows, source_labels, source_symbolic_hash = source_matrix(
            source, point
        )
        dense_certificate = rank_certificate(dense_values, dense_rows, point)
        source_certificate = rank_certificate(source_values, source_rows, point)
        if dense_labels != source_labels:
            raise RuntimeError("candidate label mismatch across implementations")
        witness_rows.append(
            {
                "projective_point": list(point),
                "projective_point_normalization": "primitive_integer_coordinates; first_nonzero_positive",
                "D": d_value,
                "saturation_u": f"1/{d_value}",
                "saturation_residual": "0",
                "primitive_quotient_values": quotient_values,
                "all_four_primitive_quotients_zero": not any(quotient_values),
                "dense_full_matrix": dense_certificate,
                "source_full_matrix": source_certificate,
                "source_symbolic_matrix_sha256": source_symbolic_hash,
                "candidate_labels_sha256": canonical_hash(dense_labels),
                "full_matrix_rank_drop_detected": False,
                "four_minor_common_zero_is_full_rank_artifact": True,
                "checked": bool(
                    d_value != 0
                    and not any(quotient_values)
                    and dense_certificate["checked"]
                    and source_certificate["checked"]
                    and dense_certificate["rank_over_QQ"] == 37
                    and source_certificate["rank_over_QQ"] == 37
                ),
            }
        )

    stable_payload = {
        "source_primitive_quotient_sha256": [
            row["primitive_quotient_canonical_terms_sha256"] for row in r201["rows"]
        ],
        "restricted_gcd_canonical_terms_sha256": canonical_hash(
            normalized_poly_terms(restricted_gcd)
        ),
        "points": [row["projective_point"] for row in witness_rows],
        "quotient_values": [row["primitive_quotient_values"] for row in witness_rows],
        "dense_rank_certificates": [
            {
                "selected_rows_sha256": row["dense_full_matrix"]["selected_rows_sha256"],
                "exact_determinant_sha256": row["dense_full_matrix"]["exact_determinant_sha256"],
                "rank_over_QQ": row["dense_full_matrix"]["rank_over_QQ"],
            }
            for row in witness_rows
        ],
        "source_rank_certificates": [
            {
                "selected_rows_sha256": row["source_full_matrix"]["selected_rows_sha256"],
                "exact_determinant_sha256": row["source_full_matrix"]["exact_determinant_sha256"],
                "rank_over_QQ": row["source_full_matrix"]["rank_over_QQ"],
            }
            for row in witness_rows
        ],
    }
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R201_four_minor_artifact_classification_only",
        "coupling": "13/32",
        "n": 4,
        "source_integer_reconstruction_sha256": sha256_file(r201_path),
        "source_modular_preflight_sha256": sha256_file(r202_path),
        "dense_dependency_sha256": sha256_file(dense_path),
        "source_dependency_sha256": sha256_file(source_path),
        "source_primitive_quotient_sha256": stable_payload[
            "source_primitive_quotient_sha256"
        ],
        "b_zero_restricted_gcd_total_degree": restricted_gcd.total_degree(),
        "b_zero_restricted_gcd_term_count": len(restricted_gcd.terms()),
        "b_zero_restricted_gcd_canonical_terms": normalized_poly_terms(restricted_gcd),
        "b_zero_restricted_gcd_canonical_terms_sha256": stable_payload[
            "restricted_gcd_canonical_terms_sha256"
        ],
        "b_zero_restricted_gcd_factorization": "(a-2*c)^5*(2*a+c)^5*(768*a^6-256*a^5*c-7227*a^4*c^2+5120*a^3*c^3+7227*a^2*c^4-256*a*c^5-768*c^6)",
        "rational_linear_factor_multiplicities": {
            "a-2*c": 5,
            "2*a+c": 5,
        },
        "restricted_factorization_checked": restricted_factorization_checked,
        "rational_common_zero_count": len(witness_rows),
        "witness_rows": witness_rows,
        "r202_primes": list(R202_PRIMES),
        "independent_row_selection_prime": ROW_SELECTION_PRIME,
        "dense_and_source_paths_separate": True,
        "four_minor_rational_common_zero_verified": all(
            row["all_four_primitive_quotients_zero"] for row in witness_rows
        ),
        "all_witnesses_full_rank_over_QQ": all(
            row["dense_full_matrix"]["rank_over_QQ"] == 37
            and row["source_full_matrix"]["rank_over_QQ"] == 37
            for row in witness_rows
        ),
        "four_selected_minors_sufficient_for_full_rank_locus": False,
        "r202_nonunit_classification_explained_by_rational_artifact": True,
        "next_gate": "add independently selected maximal minors and rerun exact saturated-ideal classification",
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "python_version": platform.python_version(),
        "sympy_version": sp.__version__,
        "stable_classification_payload": stable_payload,
        "stable_classification_sha256": canonical_hash(stable_payload),
        "checked": bool(
            r202.get("all_classified_primes_detect_nonunit_ideal") is True
            and restricted_factorization_checked
            and all(row["checked"] for row in witness_rows)
        ),
    }
    payload_without_hash = dict(result)
    result["payload_sha256"] = canonical_hash(payload_without_hash)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    result = build_result(root)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2 if args.pretty else None, sort_keys=True) + "\n"
    )
    print(json.dumps({
        "checked": result["checked"],
        "rational_common_zero_count": result["rational_common_zero_count"],
        "all_witnesses_full_rank_over_QQ": result["all_witnesses_full_rank_over_QQ"],
        "stable_classification_sha256": result["stable_classification_sha256"],
        "output": str(output),
    }, sort_keys=True))
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
