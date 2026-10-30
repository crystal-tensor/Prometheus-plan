#!/usr/bin/env python3
"""Seal an audit-owned dense Kronecker reconstruction before R201 results."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import sys
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any

import sympy as sp


VERSION = "0.3.0"
METHOD = "b9_r201_dense_kronecker_presource_design_seal_v3"
CONTRACT_PATH = Path("benchmarks/B9_R201_projective_patch_contract_v0.json")
DEFAULT_OUTPUT = Path("results/B9_R201_audit_owned_presource_manifest_v1.json")
ENGINEERING_COUPLING = Fraction(13, 32)
AUDIT_ENGINEERING_ANCHORS = ((1, -1, 1), (2, 1, 1), (-1, 2, 1), (1, 2, 3))
BASIS_PRIME = 1_000_003
CONTROL_PRIMES = (1_000_037, 1_000_081)
CONTROL_POINT = (-1, 0, 2)
A, B, C = sp.symbols("a b c", real=True)
VARS = (A, B, C)
D = A * A + B * B + C * C

I2 = sp.eye(2)
X2 = sp.Matrix([[0, 1], [1, 0]])
Y2 = sp.Matrix([[0, -sp.I], [sp.I, 0]])
Z2 = sp.diag(1, -1)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def ast_source_result_guard(path: Path) -> dict[str, Any]:
    tree = ast.parse(path.read_text())
    forbidden_names = {"SOURCE_PATH", "SOURCE_FIELDS_CONSUMED_FOR_REBUILD"}
    forbidden_modules = {
        "b9_r201_projective_patch_certificate",
        "b9_r201_independent_audit",
    }
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in forbidden_names:
            violations.append(f"name:{node.id}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in forbidden_modules:
                    violations.append(f"import:{alias.name}")
        elif isinstance(node, ast.ImportFrom) and (node.module or "") in forbidden_modules:
            violations.append(f"from:{node.module}")
    return {"violations": sorted(set(violations)), "checked": not violations}


def kron_all(local: list[sp.Matrix]) -> sp.Matrix:
    output = sp.Matrix([[1]])
    for matrix in local:
        output = sp.kronecker_product(output, matrix)
    return output


@cache
def local_operator(n: int, site: int, axis: str) -> sp.Matrix:
    matrix = {"I": I2, "X": X2, "Y": Y2, "Z": Z2}[axis]
    return kron_all([matrix if index == site else I2 for index in range(n)])


def primitive_hamiltonian(n: int, coupling: Fraction) -> sp.Matrix:
    coefficients = [Fraction(-1), Fraction(3, 4), coupling]
    scale = math.lcm(*(value.denominator for value in coefficients))
    integers = [int(value * scale) for value in coefficients]
    divisor = math.gcd(*[abs(value) for value in integers])
    x_coefficient, z_coefficient, zz_coefficient = [
        value // divisor for value in integers
    ]
    output = sp.zeros(2**n)
    for site in range(n):
        output += x_coefficient * local_operator(n, site, "X")
        output += z_coefficient * local_operator(n, site, "Z")
    for site in range(n - 1):
        output += zz_coefficient * (
            local_operator(n, site, "Z") * local_operator(n, site + 1, "Z")
        )
    return output


def frame_matrices() -> dict[str, sp.Matrix]:
    return {
        "P": 2 * A * C * X2 + 2 * B * C * Y2 + (C * C - A * A - B * B) * Z2,
        "Q": (C * C - A * A + B * B) * X2 - 2 * A * B * Y2 - 2 * A * C * Z2,
        "R": -2 * A * B * X2 + (C * C + A * A - B * B) * Y2 - 2 * B * C * Z2,
    }


def frame_identity_checks() -> dict[str, Any]:
    frame = frame_matrices()
    d_value = A * A + B * B + C * C
    checks = {
        "P2": frame["P"] * frame["P"] - d_value**2 * I2,
        "Q2": frame["Q"] * frame["Q"] - d_value**2 * I2,
        "R2": frame["R"] * frame["R"] - d_value**2 * I2,
        "PQ_anticommutator": frame["P"] * frame["Q"] + frame["Q"] * frame["P"],
        "QR_anticommutator": frame["Q"] * frame["R"] + frame["R"] * frame["Q"],
        "RP_anticommutator": frame["R"] * frame["P"] + frame["P"] * frame["R"],
        "QR_orientation": frame["Q"] * frame["R"] - sp.I * d_value * frame["P"],
    }
    passed = {
        label: all(sp.expand(value) == 0 for value in matrix)
        for label, matrix in checks.items()
    }
    return {
        "identity_count": len(passed),
        "identity_pass_count": sum(passed.values()),
        "checks": passed,
        "checked": all(passed.values()),
    }


def gamma_matrix(n: int, site: int, endpoint: str, frame: dict[str, sp.Matrix]) -> sp.Matrix:
    local = []
    for index in range(n):
        if index < site:
            local.append(frame["P"])
        elif index == site:
            local.append(frame[endpoint])
        else:
            local.append(I2)
    return kron_all(local)


def candidate_matrices_from_frame(
    n: int, frame: dict[str, sp.Matrix]
) -> list[tuple[str, sp.Matrix]]:
    gamma_specs = [(site, endpoint) for site in range(n) for endpoint in ("Q", "R")]
    gammas = {
        spec: gamma_matrix(n, spec[0], spec[1], frame) for spec in gamma_specs
    }
    output = [
        (f"gamma:{site}:{endpoint}", gammas[(site, endpoint)])
        for site, endpoint in gamma_specs
    ]
    for left_index, left in enumerate(gamma_specs):
        for right in gamma_specs[left_index + 1 :]:
            output.append(
                (
                    f"bilinear:{left[0]}:{left[1]}:{right[0]}:{right[1]}",
                    sp.expand(sp.I * gammas[left] * gammas[right]),
                )
            )
    output.append(("parity", kron_all([frame["P"] for _ in range(n)])))
    return output


def candidate_matrices(n: int) -> list[tuple[str, sp.Matrix]]:
    return candidate_matrices_from_frame(n, frame_matrices())


def encode_poly(expression: sp.Expr) -> list[list[Any]]:
    poly = sp.Poly(sp.expand(expression), *VARS, domain=sp.QQ)
    return [
        [
            list(monomial),
            [str(sp.Rational(coefficient).p), str(sp.Rational(coefficient).q)],
        ]
        for monomial, coefficient in poly.terms()
    ]


def encode_complex_poly(expression: sp.Expr) -> dict[str, list[list[Any]]]:
    real, imaginary = sp.expand_complex(expression).as_real_imag()
    return {"real": encode_poly(real), "imaginary": encode_poly(imaginary)}


def evaluate_payload(
    payload: list[list[Any]], point: tuple[int, int, int], prime: int
) -> int:
    total = 0
    for exponents, coefficient in payload:
        numerator, denominator = (int(value) for value in coefficient)
        value = numerator * pow(denominator % prime, prime - 2, prime)
        for coordinate, exponent in zip(point, exponents):
            value = value * pow(coordinate % prime, int(exponent), prime) % prime
        total = (total + value) % prime
    return total


def modular_rank(matrix: list[list[int]], prime: int) -> int:
    rows = [list(value % prime for value in row) for row in matrix]
    rank = 0
    for column in range(len(rows[0]) if rows else 0):
        pivot = next(
            (index for index in range(rank, len(rows)) if rows[index][column]),
            None,
        )
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        inverse = pow(rows[rank][column], prime - 2, prime)
        rows[rank] = [value * inverse % prime for value in rows[rank]]
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
    matrix: list[list[int]], row_labels: list[str], prime: int
) -> list[str]:
    basis: dict[int, list[int]] = {}
    selected: list[str] = []
    for label, source_row in zip(row_labels, matrix):
        row = [value % prime for value in source_row]
        for pivot in sorted(basis):
            if row[pivot]:
                factor = row[pivot]
                row = [
                    (left - factor * right) % prime
                    for left, right in zip(row, basis[pivot])
                ]
        pivot = next((index for index, value in enumerate(row) if value), None)
        if pivot is None:
            continue
        inverse = pow(row[pivot], prime - 2, prime)
        row = [value * inverse % prime for value in row]
        basis[pivot] = row
        selected.append(label)
    return selected


def is_exactly_hermitian(matrix: sp.Matrix) -> bool:
    difference = matrix - matrix.conjugate().T
    return all(sp.expand_complex(value) == 0 for value in difference)


def hermitian_coordinates(matrix: sp.Matrix) -> list[tuple[str, sp.Expr]]:
    if not is_exactly_hermitian(matrix):
        raise ValueError("Hermitian coordinate projection received a non-Hermitian matrix")
    coordinates: list[tuple[str, sp.Expr]] = []
    for row in range(matrix.rows):
        coordinates.append((f"diag:{row}", sp.re(sp.expand_complex(matrix[row, row]))))
    for row in range(matrix.rows):
        for column in range(row + 1, matrix.cols):
            value = sp.expand_complex(matrix[row, column])
            coordinates.append((f"upper_re:{row}:{column}", sp.re(value)))
            coordinates.append((f"upper_im:{row}:{column}", sp.im(value)))
    return [(label, sp.expand(value)) for label, value in coordinates]


def dense_matrix_commitment(n: int, coupling: Fraction) -> dict[str, Any]:
    hamiltonian = primitive_hamiltonian(n, coupling)
    candidates = candidate_matrices(n)
    all_candidates_hermitian = all(
        is_exactly_hermitian(candidate) for _, candidate in candidates
    )
    if not all_candidates_hermitian:
        raise RuntimeError("engineering candidate family is not Hermitian")
    labels = [label for label, _ in candidates]
    columns = []
    row_labels: list[str] | None = None
    for _, candidate in candidates:
        commutator = sp.expand(-sp.I * (hamiltonian * candidate - candidate * hamiltonian))
        coordinates = hermitian_coordinates(commutator)
        labels_for_column = [label for label, _ in coordinates]
        if row_labels is None:
            row_labels = labels_for_column
        elif row_labels != labels_for_column:
            raise RuntimeError("dense coordinate order drift")
        columns.append([encode_poly(value) for _, value in coordinates])
    if row_labels is None:
        raise RuntimeError("empty dense candidate family")
    triples = [
        [row_labels[row], column, payload]
        for column, values in enumerate(columns)
        for row, payload in enumerate(values)
        if payload
    ]
    anchor_ranks = []
    selected_row_hashes: set[str] = set()
    for anchor in AUDIT_ENGINEERING_ANCHORS:
        matrix = [
            [
                evaluate_payload(columns[column][row], anchor, BASIS_PRIME)
                for column in range(len(columns))
            ]
            for row in range(len(row_labels))
        ]
        rank = modular_rank(matrix, BASIS_PRIME)
        row_order = sorted(
            range(len(row_labels)),
            key=lambda index: canonical_hash(
                {"anchor": list(anchor), "coordinate": row_labels[index]}
            ),
        )
        ordered_matrix = [matrix[index] for index in row_order]
        ordered_labels = [row_labels[index] for index in row_order]
        selected_rows = select_independent_rows(
            ordered_matrix, ordered_labels, BASIS_PRIME
        )
        selected_rows_sha256 = canonical_hash(selected_rows)
        selected_row_hashes.add(selected_rows_sha256)
        anchor_ranks.append(
            {
                "anchor": list(anchor),
                "prime": BASIS_PRIME,
                "rank": rank,
                "full_column_rank": rank == len(columns),
                "row_order_method": "sha256_anchor_and_coordinate_label",
                "selected_coordinate_rows": selected_rows,
                "selected_coordinate_rows_sha256": selected_rows_sha256,
            }
        )
    return {
        "coupling": fraction_text(coupling),
        "n": n,
        "representation": "dense_2x2_kronecker_to_hermitian_upper_coordinates",
        "dense_operator_dimension": 2**n,
        "coordinate_row_count": len(row_labels),
        "candidate_column_count": len(columns),
        "candidate_labels": labels,
        "candidate_labels_sha256": canonical_hash(labels),
        "nonzero_polynomial_entry_count": len(triples),
        "coefficient_tensor_sha256": canonical_hash(triples),
        "direct_gamma_product_construction": True,
        "all_candidates_hermitian": all_candidates_hermitian,
        "all_commutators_hermitian": True,
        "coordinate_row_labels_sha256": canonical_hash(row_labels),
        "audit_engineering_anchor_ranks": anchor_ranks,
        "audit_selected_minor_count": len(selected_row_hashes),
        "audit_selected_minor_rows_frozen": bool(
            len(selected_row_hashes) == len(AUDIT_ENGINEERING_ANCHORS)
            and all(len(record["selected_coordinate_rows"]) == len(columns) for record in anchor_ranks)
        ),
        "all_audit_engineering_anchors_full_column_rank": all(
            record["full_column_rank"] for record in anchor_ranks
        ),
        "column_scaling_semantics": "bilinears are constructed directly as i*gamma_p*gamma_q",
    }


def numeric_frame(point: tuple[int, int, int]) -> tuple[dict[str, sp.Matrix], int]:
    substitutions = dict(zip(VARS, point))
    frame = {
        label: matrix.applyfunc(lambda value: sp.expand(value.subs(substitutions)))
        for label, matrix in frame_matrices().items()
    }
    d_value = sum(coordinate * coordinate for coordinate in point)
    return frame, d_value


def numeric_coordinates(matrix: sp.Matrix) -> list[int]:
    values = hermitian_coordinates(matrix)
    output: list[int] = []
    for _, value in values:
        resolved = sp.expand(value)
        if resolved.is_Integer is not True:
            raise RuntimeError(f"positive-control coordinate is not integral: {resolved}")
        output.append(int(resolved))
    return output


def matrix_from_columns(columns: list[list[int]]) -> list[list[int]]:
    if not columns:
        return []
    return [
        [columns[column][row] for column in range(len(columns))]
        for row in range(len(columns[0]))
    ]


def dense_positive_control() -> dict[str, Any]:
    n = 6
    frame, d_value = numeric_frame(CONTROL_POINT)
    candidates = candidate_matrices_from_frame(n, frame)
    labels = [label for label, _ in candidates]
    label_to_index = {label: index for index, label in enumerate(labels)}
    hamiltonian = primitive_hamiltonian(n, Fraction(0))
    all_candidates_hermitian = all(
        is_exactly_hermitian(matrix) for _, matrix in candidates
    )
    if not all_candidates_hermitian:
        raise RuntimeError("positive-control candidate family is not Hermitian")
    operator_columns = [numeric_coordinates(matrix) for _, matrix in candidates]
    commutator_matrices = [
        sp.expand(-sp.I * (hamiltonian * matrix - matrix * hamiltonian))
        for _, matrix in candidates
    ]
    all_commutators_hermitian = all(
        is_exactly_hermitian(matrix) for matrix in commutator_matrices
    )
    if not all_commutators_hermitian:
        raise RuntimeError("positive-control commutator family is not Hermitian")
    commutator_columns = [numeric_coordinates(matrix) for matrix in commutator_matrices]
    operator_matrix = matrix_from_columns(operator_columns)
    commutator_matrix = matrix_from_columns(commutator_columns)
    exact_kernel_rows: list[dict[str, Any]] = []
    kernel_vectors: list[list[int]] = []

    def add_kernel(label: str, coefficients: dict[str, int]) -> None:
        vector = [0] * len(candidates)
        for candidate_label, coefficient in coefficients.items():
            vector[label_to_index[candidate_label]] = coefficient
        residual = [
            sum(vector[column] * commutator_columns[column][row] for column in range(len(candidates)))
            for row in range(len(commutator_columns[0]))
        ]
        kernel_vectors.append(vector)
        exact_kernel_rows.append(
            {
                "label": label,
                "coefficients": coefficients,
                "residual_nonzero_count": sum(value != 0 for value in residual),
                "checked": not any(residual),
            }
        )

    for site in range(n):
        add_kernel(
            f"onsite_P:{site}",
            {f"bilinear:{site}:Q:{site}:R": 1},
        )
    for left in range(n):
        for right in range(left + 1, n):
            add_kernel(
                f"pair_dot:{left}:{right}",
                {
                    f"bilinear:{left}:Q:{right}:Q": 1,
                    f"bilinear:{left}:R:{right}:R": 1,
                },
            )
            add_kernel(
                f"pair_cross:{left}:{right}",
                {
                    f"bilinear:{left}:Q:{right}:R": 1,
                    f"bilinear:{left}:R:{right}:Q": -1,
                },
            )
    add_kernel("parity", {"parity": 1})

    kernel_coefficient_rank = int(sp.Matrix(kernel_vectors).rank())
    kernel_residual_nonzero_count = sum(
        row["residual_nonzero_count"] for row in exact_kernel_rows
    )

    witness_rows = []
    for site in range(n):
        witness = kron_all(
            [frame["P"] if index == site else I2 for index in range(n)]
        )
        witness_column = numeric_coordinates(witness)
        commutator_zero = hamiltonian * witness - witness * hamiltonian == sp.zeros(2**n)
        bilinear_label = f"bilinear:{site}:Q:{site}:R"
        bilinear = candidates[label_to_index[bilinear_label]][1]
        exact_scale = -(d_value ** (2 * site + 1))
        exact_bilinear_relation = bilinear == exact_scale * witness
        witness_rows.append(
            {
                "site": site,
                "bilinear_label": bilinear_label,
                "exact_bilinear_scale": exact_scale,
                "commutator_zero": commutator_zero,
                "exact_bilinear_relation": exact_bilinear_relation,
                "checked": commutator_zero and exact_bilinear_relation,
            }
        )
    operator_ranks = {
        str(prime): modular_rank(operator_matrix, prime) for prime in CONTROL_PRIMES
    }
    commutator_ranks = {
        str(prime): modular_rank(commutator_matrix, prime) for prime in CONTROL_PRIMES
    }
    nullities = {
        str(prime): len(candidates) - commutator_ranks[str(prime)]
        for prime in CONTROL_PRIMES
    }
    commutator_rank_lower_bound = min(commutator_ranks.values())
    commutator_rank_upper_bound = len(candidates) - kernel_coefficient_rank
    checked = bool(
        len(candidates) == 79
        and all(rank == 79 for rank in operator_ranks.values())
        and all(rank == 42 for rank in commutator_ranks.values())
        and all(nullity == 37 for nullity in nullities.values())
        and len(exact_kernel_rows) == 37
        and kernel_coefficient_rank == 37
        and kernel_residual_nonzero_count == 0
        and commutator_rank_lower_bound == 42
        and commutator_rank_upper_bound == 42
        and all(row["checked"] for row in witness_rows)
    )
    return {
        "n": n,
        "coupling": "0",
        "homogeneous_point": list(CONTROL_POINT),
        "D": d_value,
        "representation": "dense_2x2_kronecker_to_hermitian_upper_coordinates",
        "candidate_column_count": len(candidates),
        "candidate_counts": {"gamma": 12, "bilinear": 66, "parity": 1, "total": 79},
        "candidate_labels_sha256": canonical_hash(labels),
        "coordinate_row_count": len(operator_matrix),
        "audit_primes": list(CONTROL_PRIMES),
        "operator_ranks": operator_ranks,
        "commutator_ranks": commutator_ranks,
        "nullities": nullities,
        "operator_rank_exact": 79,
        "commutator_rank_lower_bound": commutator_rank_lower_bound,
        "commutator_rank_upper_bound": commutator_rank_upper_bound,
        "commutator_rank_exact": 42,
        "nullity_exact": 37,
        "exact_kernel_vector_count": len(exact_kernel_rows),
        "exact_kernel_coefficient_rank": kernel_coefficient_rank,
        "exact_kernel_residual_nonzero_count": kernel_residual_nonzero_count,
        "exact_kernel_vectors": exact_kernel_rows,
        "exact_kernel_coefficient_sha256": canonical_hash(kernel_vectors),
        "direct_gamma_product_construction": True,
        "source_modules_imported": [],
        "all_candidates_hermitian": all_candidates_hermitian,
        "all_commutators_hermitian": all_commutators_hermitian,
        "onsite_P_witness_count": len(witness_rows),
        "onsite_P_witnesses": witness_rows,
        "operator_coordinate_tensor_sha256": canonical_hash(operator_columns),
        "commutator_coordinate_tensor_sha256": canonical_hash(commutator_columns),
        "checked": checked,
    }


def mutation_checks(reference: dict[str, Any]) -> dict[str, Any]:
    frame = frame_matrices()
    baseline = encode_complex_poly(gamma_matrix(1, 0, "Q", frame)[0, 1])
    mutated_frames = {
        "flip_Q_y_sign": {**frame, "Q": frame["Q"] + 4 * A * B * Y2},
        "swap_Q_R": {**frame, "Q": frame["R"], "R": frame["Q"]},
    }
    records = []
    for label, altered in mutated_frames.items():
        payload = encode_complex_poly(gamma_matrix(1, 0, "Q", altered)[0, 1])
        records.append(
            {
                "label": label,
                "mutated_local_sha256": canonical_hash(payload),
                "baseline_local_sha256": canonical_hash(baseline),
                "rejected": payload != baseline,
            }
        )
    records.append(
        {
            "label": "coefficient_tensor_hash",
            "altered_hash": "0" * 64,
            "reference_hash": reference["coefficient_tensor_sha256"],
            "rejected": reference["coefficient_tensor_sha256"] != "0" * 64,
        }
    )
    return {
        "case_count": len(records),
        "rejected_count": sum(record["rejected"] for record in records),
        "records": records,
        "checked": all(record["rejected"] for record in records),
    }


def build_manifest(root: Path) -> dict[str, Any]:
    contract_path = root / CONTRACT_PATH
    contract = json.loads(contract_path.read_text())
    guard = ast_source_result_guard(Path(__file__).resolve())
    engineering = dense_matrix_commitment(4, ENGINEERING_COUPLING)
    positive_control = dense_positive_control()
    mutations = mutation_checks(engineering)
    frozen_schedule = [
        {"n": n, "coupling": value, "conditional": n == 5}
        for n in (4, 5)
        for value in contract["frozen_holdouts"]["couplings"]
    ]
    payload = {
        "experiment_id": contract["experiment_id"],
        "method": METHOD,
        "version": VERSION,
        "status": "audit_owned_presource_minor_and_control_seal_complete",
        "contract_sha256": sha256_file(contract_path),
        "manifest_tool_sha256": sha256_file(Path(__file__).resolve()),
        "input_authority": "contract_and_audit_design_only",
        "source_result_path_read": False,
        "source_result_fields_consumed_for_reconstruction": [],
        "source_result_guard": guard,
        "frame_identity_checks": frame_identity_checks(),
        "engineering_dense_commitment": engineering,
        "dense_positive_control": positive_control,
        "mutation_checks": mutations,
        "frozen_execution_schedule": frozen_schedule,
        "frozen_holdout_matrix_construction_executed": False,
        "frozen_holdout_row_selection_executed": False,
        "frozen_holdout_minor_computation_executed": False,
        "frozen_holdout_solver_executed": False,
        "frozen_holdout_scientific_decision_executed": False,
        "remaining_readiness_requirements": [
            "run the pre-source holdout reconstruction in an isolated filesystem without the main result path",
            "bind the emitted ideal certificate generators to independently reconstructed dense minors",
        ],
        "readiness_blocker_closed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    payload["checked"] = bool(
        guard["checked"]
        and payload["frame_identity_checks"]["checked"]
        and mutations["checked"]
        and engineering["coordinate_row_count"] == 256
        and engineering["candidate_column_count"] == 37
        and engineering["all_audit_engineering_anchors_full_column_rank"]
        and engineering["audit_selected_minor_count"] == 4
        and engineering["audit_selected_minor_rows_frozen"]
        and positive_control["checked"]
        and not payload["frozen_holdout_scientific_decision_executed"]
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
    result = build_manifest(root)
    output = args.output if args.output.is_absolute() else root / args.output
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "dense_shape": [
                    result["engineering_dense_commitment"]["coordinate_row_count"],
                    result["engineering_dense_commitment"]["candidate_column_count"],
                ],
                "source_result_fields_consumed_for_reconstruction": result[
                    "source_result_fields_consumed_for_reconstruction"
                ],
                "audit_selected_minor_count": result["engineering_dense_commitment"][
                    "audit_selected_minor_count"
                ],
                "positive_control_checked": result["dense_positive_control"]["checked"],
                "readiness_blocker_closed": result["readiness_blocker_closed"],
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
