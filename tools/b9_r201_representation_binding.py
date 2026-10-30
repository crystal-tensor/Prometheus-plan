#!/usr/bin/env python3
"""Build an exact binding between the two public R201 matrix representations."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any

import sympy as sp

import b9_r201_projective_patch_certificate as source
import b9_r201_presource_manifest as dense


VERSION = "0.1.0"
METHOD = "b9_r201_exact_source_dense_representation_binding_v1"
DEFAULT_OUTPUT = Path("results/B9_R201_source_dense_representation_binding_v0.json")
PRESOURCE_PATH = Path("results/B9_R201_audit_owned_presource_manifest_v1.json")
ENGINEERING_PROBE_PATH = Path("results/B9_R201_engineering_probe_v0.json")
ENGINEERING_COUPLING = Fraction(13, 32)
N = 4
DIMENSION = 2**N
FULL_COORDINATE_COUNT = DIMENSION**2
COMMUTATOR_CONSTANT = -2
PAULI = {"I": dense.I2, "X": dense.X2, "Y": dense.Y2, "Z": dense.Z2}
SOURCE_TO_DENSE_SYMBOLS = {
    source.A: dense.A,
    source.B: dense.B,
    source.C: dense.C,
}


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@cache
def pauli_word_matrix(word: str) -> sp.Matrix:
    return dense.kron_all([PAULI[letter] for letter in word])


def all_pauli_words() -> list[str]:
    return ["".join(letters) for letters in itertools.product("IXYZ", repeat=N)]


def exact_zero_matrix(matrix: sp.Matrix) -> bool:
    return all(sp.expand(value) == 0 for value in matrix)


def independent_hermitian_coordinates(
    matrix: sp.Matrix,
) -> list[tuple[str, sp.Expr]]:
    if not dense.is_exactly_hermitian(matrix):
        raise ValueError("coordinate projection requires an exact Hermitian matrix")
    coordinates: list[tuple[str, sp.Expr]] = []
    for row in range(matrix.rows):
        coordinates.append((f"diag:{row}", sp.re(sp.expand_complex(matrix[row, row]))))
    for row in range(matrix.rows):
        for column in range(row + 1, matrix.cols):
            value = sp.expand_complex(matrix[row, column])
            coordinates.append((f"upper_re:{row}:{column}", sp.re(value)))
            coordinates.append((f"upper_im:{row}:{column}", sp.im(value)))
    return [(label, sp.expand(value)) for label, value in coordinates]


def reconstruct_hermitian(
    coordinates: list[tuple[str, sp.Expr]], *, flip_upper_im: bool = False
) -> sp.Matrix:
    values = dict(coordinates)
    matrix = sp.zeros(DIMENSION)
    for row in range(DIMENSION):
        matrix[row, row] = values[f"diag:{row}"]
    for row in range(DIMENSION):
        for column in range(row + 1, DIMENSION):
            real = values[f"upper_re:{row}:{column}"]
            imaginary = values[f"upper_im:{row}:{column}"]
            if flip_upper_im:
                imaginary = -imaginary
            matrix[row, column] = real + sp.I * imaginary
            matrix[column, row] = real - sp.I * imaginary
    return matrix


def sparse_product(
    left: dict[tuple[int, int], int], right: dict[tuple[int, int], int]
) -> dict[tuple[int, int], int]:
    right_by_row: dict[int, list[tuple[int, int]]] = {}
    for (row, column), value in right.items():
        right_by_row.setdefault(row, []).append((column, value))
    output: dict[tuple[int, int], int] = {}
    for (row, inner), left_value in left.items():
        for column, right_value in right_by_row.get(inner, []):
            key = (row, column)
            output[key] = output.get(key, 0) + left_value * right_value
    return {key: value for key, value in output.items() if value}


def scaled_identity(size: int, scale: int) -> dict[tuple[int, int], int]:
    return {(index, index): scale for index in range(size)}


def coordinate_transform_certificate() -> dict[str, Any]:
    words = all_pauli_words()
    coordinate_labels: list[str] | None = None
    transform: dict[tuple[int, int], int] = {}
    inverse_numerator: dict[tuple[int, int], int] = {}
    roundtrip_count = 0
    signatures = []
    for word_index, word in enumerate(words):
        matrix = pauli_word_matrix(word)
        coordinates = independent_hermitian_coordinates(matrix)
        labels = [label for label, _ in coordinates]
        if coordinate_labels is None:
            coordinate_labels = labels
        elif labels != coordinate_labels:
            raise RuntimeError("Hermitian coordinate order drift")
        if reconstruct_hermitian(coordinates) != matrix:
            raise RuntimeError(f"coordinate roundtrip failed for {word}")
        roundtrip_count += 1
        nonzero_signature = []
        for coordinate_index, (label, value) in enumerate(coordinates):
            integer = int(value)
            if integer:
                transform[(coordinate_index, word_index)] = integer
                nonzero_signature.append([label, integer])
        signatures.append([word, nonzero_signature])

    if coordinate_labels is None:
        raise RuntimeError("empty Pauli coordinate transform")
    for word_index, word in enumerate(words):
        matrix = pauli_word_matrix(word)
        for coordinate_index, label in enumerate(coordinate_labels):
            parts = label.split(":")
            if parts[0] == "diag":
                value = sp.re(matrix[int(parts[1]), int(parts[1])])
            else:
                row, column = int(parts[1]), int(parts[2])
                entry = matrix[row, column]
                component = sp.re(entry) if parts[0] == "upper_re" else sp.im(entry)
                value = 2 * component
            integer = int(value)
            if integer:
                inverse_numerator[(word_index, coordinate_index)] = integer

    transform_inverse = sparse_product(transform, inverse_numerator)
    inverse_transform = sparse_product(inverse_numerator, transform)
    expected = scaled_identity(FULL_COORDINATE_COUNT, DIMENSION)
    transform_triples = [
        [row, column, value]
        for (row, column), value in sorted(transform.items())
    ]
    inverse_triples = [
        [row, column, value]
        for (row, column), value in sorted(inverse_numerator.items())
    ]
    return {
        "shape": [FULL_COORDINATE_COUNT, FULL_COORDINATE_COUNT],
        "pauli_word_order_sha256": canonical_hash(words),
        "hermitian_coordinate_order_sha256": canonical_hash(coordinate_labels),
        "coordinate_roundtrip_count": roundtrip_count,
        "transform_nonzero_count": len(transform_triples),
        "transform_sparse_sha256": canonical_hash(transform_triples),
        "inverse_numerator_nonzero_count": len(inverse_triples),
        "inverse_numerator_sparse_sha256": canonical_hash(inverse_triples),
        "inverse_denominator": DIMENSION,
        "transform_times_inverse_equals_16I": transform_inverse == expected,
        "inverse_times_transform_equals_16I": inverse_transform == expected,
        "pauli_coordinate_signatures_sha256": canonical_hash(signatures),
        "invertible_domains": ["QQ", "RR", "GF(p) for odd prime p"],
        "excluded_characteristic": 2,
        "checked": bool(
            roundtrip_count == FULL_COORDINATE_COUNT
            and len(transform_triples) == 2176
            and len(inverse_triples) == 2176
            and transform_inverse == expected
            and inverse_transform == expected
        ),
    }


def source_operator_matrix(operator: dict[str, Any]) -> sp.Matrix:
    output = sp.zeros(DIMENSION)
    for word, coefficient in operator.items():
        if isinstance(coefficient, sp.Poly):
            expression = coefficient.as_expr()
        elif isinstance(coefficient, Fraction):
            expression = sp.Rational(coefficient.numerator, coefficient.denominator)
        else:
            expression = sp.sympify(coefficient)
        output += expression.subs(SOURCE_TO_DENSE_SYMBOLS) * pauli_word_matrix(word)
    return output


def relative_d_exponent(label: str) -> int:
    if not label.startswith("bilinear:"):
        return 0
    return 2 * int(label.split(":")[1]) + 1


def polynomial_matrix_hash(matrix: sp.Matrix) -> str:
    triples = []
    for row in range(matrix.rows):
        for column in range(matrix.cols):
            expression = sp.expand_complex(matrix[row, column])
            real = sp.expand(sp.re(expression))
            imaginary = sp.expand(sp.im(expression))
            if real != 0 or imaginary != 0:
                triples.append(
                    [
                        row,
                        column,
                        {
                            "real": dense.encode_poly(real),
                            "imaginary": dense.encode_poly(imaginary),
                        },
                    ]
                )
    return canonical_hash(triples)


def build_binding(root: Path) -> dict[str, Any]:
    presource_path = root / PRESOURCE_PATH
    engineering_probe_path = root / ENGINEERING_PROBE_PATH
    presource = json.loads(presource_path.read_text())
    engineering_probe = json.loads(engineering_probe_path.read_text())
    coordinate_transform = coordinate_transform_certificate()

    source_candidates = list(source.candidate_pool(N))
    dense_candidates = dense.candidate_matrices(N)
    source_labels, source_columns, source_output_words, source_matrix_hash = (
        source.symbolic_matrix(N, ENGINEERING_COUPLING)
    )
    dense_labels = [label for label, _ in dense_candidates]
    if source_labels != dense_labels or [label for label, _ in source_candidates] != dense_labels:
        raise RuntimeError("candidate label order mismatch")

    source_hamiltonian = source_operator_matrix(
        source.base.hamiltonian_operator(N, ENGINEERING_COUPLING)
    )
    dense_hamiltonian = dense.primitive_hamiltonian(N, ENGINEERING_COUPLING)
    hamiltonian_binding_checked = exact_zero_matrix(
        dense_hamiltonian + source_hamiltonian
    )

    column_records = []
    dense_commutator_columns: list[list[list[Any]]] = []
    coordinate_labels: list[str] | None = None
    candidate_relations_passed = 0
    commutator_relations_passed = 0
    total_d_exponent = 0
    source_candidate_matrices: dict[str, sp.Matrix] = {}
    dense_candidate_matrices: dict[str, sp.Matrix] = {}
    source_commutator_matrices: dict[str, sp.Matrix] = {}
    dense_commutator_matrices: dict[str, sp.Matrix] = {}

    for (label, source_candidate), (_, dense_candidate), source_column in zip(
        source_candidates, dense_candidates, source_columns
    ):
        exponent = relative_d_exponent(label)
        scale = dense.D**exponent
        source_candidate_matrix = source_operator_matrix(source_candidate)
        source_commutator_matrix = source_operator_matrix(source_column)
        dense_commutator_matrix = sp.expand(
            -sp.I
            * (
                dense_hamiltonian * dense_candidate
                - dense_candidate * dense_hamiltonian
            )
        )
        candidate_checked = exact_zero_matrix(
            dense_candidate - scale * source_candidate_matrix
        )
        commutator_checked = exact_zero_matrix(
            dense_commutator_matrix
            - COMMUTATOR_CONSTANT * scale * source_commutator_matrix
        )
        candidate_relations_passed += int(candidate_checked)
        commutator_relations_passed += int(commutator_checked)
        total_d_exponent += exponent
        source_candidate_matrices[label] = source_candidate_matrix
        dense_candidate_matrices[label] = dense_candidate
        source_commutator_matrices[label] = source_commutator_matrix
        dense_commutator_matrices[label] = dense_commutator_matrix
        coordinates = independent_hermitian_coordinates(dense_commutator_matrix)
        labels = [coordinate_label for coordinate_label, _ in coordinates]
        if coordinate_labels is None:
            coordinate_labels = labels
        elif labels != coordinate_labels:
            raise RuntimeError("dense commutator coordinate order drift")
        dense_commutator_columns.append(
            [dense.encode_poly(value) for _, value in coordinates]
        )
        column_records.append(
            {
                "label": label,
                "relative_D_exponent": exponent,
                "candidate_factor": f"D^{exponent}",
                "commutator_factor": f"-2*D^{exponent}",
                "source_candidate_matrix_sha256": polynomial_matrix_hash(
                    source_candidate_matrix
                ),
                "dense_candidate_matrix_sha256": polynomial_matrix_hash(
                    dense_candidate
                ),
                "source_commutator_matrix_sha256": polynomial_matrix_hash(
                    source_commutator_matrix
                ),
                "dense_commutator_matrix_sha256": polynomial_matrix_hash(
                    dense_commutator_matrix
                ),
                "candidate_relation_checked": candidate_checked,
                "commutator_relation_checked": commutator_checked,
            }
        )

    if coordinate_labels is None:
        raise RuntimeError("empty dense commutator family")
    dense_triples = [
        [coordinate_labels[row], column, payload]
        for column, values in enumerate(dense_commutator_columns)
        for row, payload in enumerate(values)
        if payload
    ]
    full_words = all_pauli_words()
    source_zero_rows = sorted(set(full_words) - set(source_output_words))
    column_exponent_histogram = {
        str(exponent): sum(
            record["relative_D_exponent"] == exponent for record in column_records
        )
        for exponent in sorted({record["relative_D_exponent"] for record in column_records})
    }

    mutation_checks = []
    first_label = dense_labels[0]
    first_scale = dense.D ** relative_d_exponent(first_label)
    mutation_checks.append(
        {
            "mutation": "drop_commutator_minus_sign",
            "rejected": not exact_zero_matrix(
                dense_commutator_matrices[first_label]
                - 2 * first_scale * source_commutator_matrices[first_label]
            ),
        }
    )
    mutation_checks.append(
        {
            "mutation": "drop_commutator_factor_two",
            "rejected": not exact_zero_matrix(
                dense_commutator_matrices[first_label]
                + first_scale * source_commutator_matrices[first_label]
            ),
        }
    )
    bilinear_label = next(
        label for label in dense_labels if label.startswith("bilinear:1:")
    )
    wrong_scale = dense.D ** (relative_d_exponent(bilinear_label) + 1)
    mutation_checks.append(
        {
            "mutation": "increment_bilinear_D_exponent",
            "rejected": not exact_zero_matrix(
                dense_candidate_matrices[bilinear_label]
                - wrong_scale * source_candidate_matrices[bilinear_label]
            ),
        }
    )
    y_word = "Y" + "I" * (N - 1)
    y_coordinates = independent_hermitian_coordinates(pauli_word_matrix(y_word))
    mutation_checks.append(
        {
            "mutation": "flip_upper_im_sign",
            "rejected": reconstruct_hermitian(
                y_coordinates, flip_upper_im=True
            )
            != pauli_word_matrix(y_word),
        }
    )
    gamma_label = "gamma:0:Q"
    reversed_source = sp.zeros(DIMENSION)
    for word, coefficient in source_candidates[0][1].items():
        reversed_source += coefficient.as_expr().subs(
            SOURCE_TO_DENSE_SYMBOLS
        ) * dense.kron_all([PAULI[letter] for letter in reversed(word)])
    mutation_checks.append(
        {
            "mutation": "reverse_kronecker_site_order",
            "rejected": not exact_zero_matrix(
                dense_candidate_matrices[gamma_label] - reversed_source
            ),
        }
    )

    audit_primes = sorted(
        {
            dense.BASIS_PRIME,
            *dense.CONTROL_PRIMES,
        }
    )
    anchor_domain_checks = []
    for anchor in dense.AUDIT_ENGINEERING_ANCHORS:
        d_value = sum(value * value for value in anchor)
        anchor_domain_checks.append(
            {
                "anchor": list(anchor),
                "D": d_value,
                "nonzero_mod_all_audit_primes": all(
                    d_value % prime != 0 for prime in audit_primes
                ),
            }
        )

    selected_minor_rows = presource["engineering_dense_commitment"][
        "audit_engineering_anchor_ranks"
    ]
    selected_minor_hashes = [
        row["selected_coordinate_rows_sha256"] for row in selected_minor_rows
    ]
    mutation_rejected_count = sum(row["rejected"] for row in mutation_checks)
    payload = {
        "method": METHOD,
        "version": VERSION,
        "status": "exact_source_dense_representation_binding_verified",
        "n": N,
        "coupling": "13/32",
        "D": "a^2+b^2+c^2",
        "source_representation_shape": [len(source_output_words), len(source_columns)],
        "source_representation_full_shape_after_zero_row_extension": [
            FULL_COORDINATE_COUNT,
            len(source_columns),
        ],
        "dense_representation_shape": [
            len(coordinate_labels),
            len(dense_commutator_columns),
        ],
        "source_zero_row_count": len(source_zero_rows),
        "source_zero_rows": source_zero_rows,
        "source_zero_rows_sha256": canonical_hash(source_zero_rows),
        "candidate_labels_sha256": canonical_hash(dense_labels),
        "source_matrix_sha256": source_matrix_hash,
        "engineering_probe_source_matrix_sha256": engineering_probe[
            "matrix_probe"
        ]["polynomial_commutator_matrix_sha256"],
        "dense_coefficient_tensor_sha256": canonical_hash(dense_triples),
        "presource_dense_coefficient_tensor_sha256": presource[
            "engineering_dense_commitment"
        ]["coefficient_tensor_sha256"],
        "presource_manifest_sha256": sha256_file(presource_path),
        "binding_tool_sha256": sha256_file(Path(__file__).resolve()),
        "hamiltonian_binding": {
            "dense_equals_source_times": -1,
            "checked": hamiltonian_binding_checked,
        },
        "coordinate_transform": coordinate_transform,
        "column_binding": {
            "candidate_equation": "C_dense = T*C_source*Lambda",
            "commutator_equation": "M_dense = -2*T*M_source*Lambda",
            "Lambda_diagonal": "D^relative_D_exponent",
            "candidate_relation_pass_count": candidate_relations_passed,
            "commutator_relation_pass_count": commutator_relations_passed,
            "column_count": len(column_records),
            "relative_D_exponent_histogram": column_exponent_histogram,
            "relative_D_exponent_sum": total_d_exponent,
            "columns": column_records,
        },
        "minor_binding": {
            "dense_minor_constant_factor": str(COMMUTATOR_CONSTANT**len(column_records)),
            "dense_minor_D_exponent": total_d_exponent,
            "equation": "det(E*M_dense)=(-2)^37*D^72*det(E*T*M_source_full)",
            "selected_dense_minor_count": len(selected_minor_hashes),
            "selected_dense_minor_row_hashes": selected_minor_hashes,
            "derived_from_exact_column_binding": True,
        },
        "domain_boundary": {
            "D_nonzero_required": True,
            "characteristic_two_excluded": True,
            "audit_primes": audit_primes,
            "anchor_checks": anchor_domain_checks,
            "all_anchor_D_values_nonzero_mod_audit_primes": all(
                row["nonzero_mod_all_audit_primes"] for row in anchor_domain_checks
            ),
        },
        "mutation_checks": mutation_checks,
        "mutation_rejected_count": mutation_rejected_count,
        "frozen_holdout_matrix_construction_executed": False,
        "frozen_holdout_solver_executed": False,
        "frozen_holdout_scientific_decision_executed": False,
        "engineering_characteristic_zero_minors_verified": False,
        "ideal_membership_certificate_verified": False,
        "readiness_blocker_closed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    payload["checked"] = bool(
        payload["source_representation_shape"] == [238, 37]
        and payload["source_representation_full_shape_after_zero_row_extension"]
        == [256, 37]
        and payload["dense_representation_shape"] == [256, 37]
        and payload["source_zero_row_count"] == 18
        and payload["candidate_labels_sha256"]
        == presource["engineering_dense_commitment"]["candidate_labels_sha256"]
        and payload["source_matrix_sha256"]
        == payload["engineering_probe_source_matrix_sha256"]
        and payload["dense_coefficient_tensor_sha256"]
        == payload["presource_dense_coefficient_tensor_sha256"]
        and hamiltonian_binding_checked
        and coordinate_transform["checked"]
        and candidate_relations_passed == 37
        and commutator_relations_passed == 37
        and column_exponent_histogram == {"0": 9, "1": 13, "3": 9, "5": 5, "7": 1}
        and total_d_exponent == 72
        and len(selected_minor_hashes) == 4
        and len(set(selected_minor_hashes)) == 4
        and payload["domain_boundary"][
            "all_anchor_D_values_nonzero_mod_audit_primes"
        ]
        and mutation_rejected_count == len(mutation_checks) == 5
        and not payload["frozen_holdout_scientific_decision_executed"]
        and not payload["engineering_characteristic_zero_minors_verified"]
        and not payload["ideal_membership_certificate_verified"]
        and not payload["readiness_blocker_closed"]
    )
    payload["payload_sha256"] = canonical_hash(payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    result = build_binding(root)
    output = args.output if args.output.is_absolute() else root / args.output
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "candidate_relations": result["column_binding"][
                    "candidate_relation_pass_count"
                ],
                "commutator_relations": result["column_binding"][
                    "commutator_relation_pass_count"
                ],
                "coordinate_roundtrips": result["coordinate_transform"][
                    "coordinate_roundtrip_count"
                ],
                "relative_D_exponent_sum": result["column_binding"][
                    "relative_D_exponent_sum"
                ],
                "mutations_rejected": result["mutation_rejected_count"],
                "checked": result["checked"],
                "payload_sha256": result["payload_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
