#!/usr/bin/env python3
"""Classify the R206 off-slice component and test it on complete matrices."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from typing import Any

import sympy as sp

import b9_r202_modular_ideal_preflight as r202
import b9_r206_six_minor_ideal_preflight as r206


METHOD = "b9_r207_off_slice_component_full_rank_classification_v1"
VERSION = "0.1.0"
ENGINEERING_COUPLING = Fraction(13, 32)
CLASSIFICATION_PRIMES = (1_000_003, 536_870_723)
RANK_PRIMES = (1_000_117, 1_000_039)
R206_PATH = Path("results/B9_R206_six_minor_ideal_preflight_v0.json")
R201_PATH = Path("results/B9_R201_integer_reconstruction_v0.json")
R204_RESULTS = r206.R204_RESULTS
R206_RESULTS = r206.R206_RESULTS
DENSE_TOOL_PATH = Path("tools/b9_r201_presource_manifest.py")
SOURCE_TOOL_PATH = Path("tools/b9_r201_independent_audit.py")
S = sp.symbols("s")
QUADRATIC = sp.Poly(S**2 + 407, S, domain=sp.ZZ)
BEGIN = "__R207_BEGIN__"
END = "__R207_END__"


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_hash_valid(result: dict[str, Any]) -> bool:
    payload = dict(result)
    expected = payload.pop("payload_sha256", None)
    return expected is not None and canonical_hash(payload) == expected


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def singular_polynomials(root: Path, prime: int) -> list[list[list[Any]]]:
    r201 = json.loads((root / R201_PATH).read_text())
    old = [r202.primitive_quotient_terms(row) for row in r201["rows"]]
    fifth = json.loads((root / R204_RESULTS[prime]).read_text())
    sixth = json.loads((root / R206_RESULTS[prime]).read_text())
    return [
        *old,
        fifth["quotient_canonical_terms"],
        sixth["quotient_canonical_terms"],
    ]


def singular_script(quotients: list[list[list[Any]]], prime: int) -> str:
    lines = [f"ring r={prime},(u,a,b,c),dp;"]
    for index, terms in enumerate(quotients):
        lines.append(f"poly q{index}={r202.polynomial_text(terms, prime)};")
    lines.extend(
        [
            "poly sat=1-u*(a2+b2+c2);",
            "poly A=169a2+407c2;",
            "poly B=169b2-576c2;",
            "poly U=2uc2-1;",
            "ideal I=q0,q1,q2,q3,q4,q5,sat;",
            "ideal J=A,B,U;",
            "ideal GI=slimgb(I);",
            "ideal GJ=slimgb(J);",
            f'print("{BEGIN}basis_I");',
            "print(size(GI));",
            "int i; for(i=1;i<=size(GI);i++){print(string(GI[i]));}",
            f'print("{END}basis_I");',
            "kill i;",
            f'print("{BEGIN}basis_J");',
            "print(size(GJ));",
            "int i; for(i=1;i<=size(GJ);i++){print(string(GJ[i]));}",
            f'print("{END}basis_J");',
            "kill i;",
            f'print("{BEGIN}I_in_J");',
            "print(string(reduce(q0,GJ)));",
            "print(string(reduce(q1,GJ)));",
            "print(string(reduce(q2,GJ)));",
            "print(string(reduce(q3,GJ)));",
            "print(string(reduce(q4,GJ)));",
            "print(string(reduce(q5,GJ)));",
            "print(string(reduce(sat,GJ)));",
            f'print("{END}I_in_J");',
            f'print("{BEGIN}radical_powers");',
            "print(string(reduce(A*A,GI)));",
            "print(string(reduce(B*B,GI)));",
            "print(string(reduce(U*U,GI)));",
            f'print("{END}radical_powers");',
            "ideal Ic=I,c-1; ideal Jc=J,c-1;",
            "ideal GIc=slimgb(Ic); ideal GJc=slimgb(Jc);",
            f'print("{BEGIN}chart");',
            "print(dim(GI)); print(dim(GJ));",
            "print(dim(GIc)); print(vdim(GIc));",
            "print(dim(GJc)); print(vdim(GJc));",
            f'print("{END}chart");',
            "ideal Ic0=I,c; ideal GIc0=slimgb(Ic0);",
            f'print("{BEGIN}c_zero");',
            "print(string(reduce(1,GIc0)));",
            f'print("{END}c_zero");',
            "quit;",
            "",
        ]
    )
    return "\n".join(lines)


def marked_rows(stdout: str, label: str) -> list[str]:
    begin = f"{BEGIN}{label}"
    end = f"{END}{label}"
    if begin not in stdout or end not in stdout:
        raise ValueError(f"missing Singular block {label}")
    return [
        row.strip()
        for row in stdout.split(begin, 1)[1].split(end, 1)[0].splitlines()
        if row.strip()
    ]


def run_singular(root: Path, singular: str, prime: int) -> dict[str, Any]:
    script = singular_script(singular_polynomials(root, prime), prime)
    completed = subprocess.run(
        [singular, "-q"],
        input=script,
        text=True,
        capture_output=True,
        check=False,
        timeout=600,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr[-4000:])
    basis_i_rows = marked_rows(completed.stdout, "basis_I")
    basis_j_rows = marked_rows(completed.stdout, "basis_J")
    basis_i_size = int(basis_i_rows.pop(0))
    basis_j_size = int(basis_j_rows.pop(0))
    if len(basis_i_rows) != basis_i_size or len(basis_j_rows) != basis_j_size:
        raise ValueError("Singular basis length mismatch")
    inclusion = marked_rows(completed.stdout, "I_in_J")
    powers = marked_rows(completed.stdout, "radical_powers")
    chart = [int(value) for value in marked_rows(completed.stdout, "chart")]
    c_zero = marked_rows(completed.stdout, "c_zero")
    checked = bool(
        basis_i_size == 7
        and len(inclusion) == 7
        and all(value == "0" for value in inclusion)
        and powers == ["0", "0", "0"]
        and chart == [1, 1, 0, 8, 0, 4]
        and c_zero == ["0"]
    )
    return {
        "prime": prime,
        "standard_basis_algorithm": "slimgb",
        "original_basis_size": basis_i_size,
        "original_basis": basis_i_rows,
        "original_basis_sha256": canonical_hash(basis_i_rows),
        "candidate_radical_basis_size": basis_j_size,
        "candidate_radical_basis": basis_j_rows,
        "candidate_radical_basis_sha256": canonical_hash(basis_j_rows),
        "original_generators_reduce_to_zero_mod_candidate_radical": all(
            value == "0" for value in inclusion
        ),
        "original_generator_remainders": inclusion,
        "candidate_generator_squares_reduce_to_zero_mod_original": powers
        == ["0", "0", "0"],
        "candidate_generator_square_remainders": powers,
        "original_dimension": chart[0],
        "candidate_radical_dimension": chart[1],
        "c_one_original_dimension": chart[2],
        "c_one_original_vector_space_dimension": chart[3],
        "c_one_candidate_radical_dimension": chart[4],
        "c_one_candidate_radical_vector_space_dimension": chart[5],
        "c_zero_original_is_unit_ideal": c_zero == ["0"],
        "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
        "returncode": completed.returncode,
        "checked": checked,
    }


def pair_payload(expression: sp.Expr) -> list[str]:
    reduced = sp.rem(
        sp.Poly(sp.together(sp.expand(expression)), S, domain=sp.QQ),
        sp.Poly(S**2 + 407, S, domain=sp.QQ),
    )
    x = sp.Rational(reduced.nth(0))
    y = sp.Rational(reduced.nth(1))
    return [str(x), str(y)]


def specialized_source(
    source: Any, b_sign: int, symbolic_data: tuple[Any, Any, Any, Any]
) -> dict[str, Any]:
    labels, columns, row_labels, parent_hash = symbolic_data
    substitutions = {
        source.VARS[0]: S / 13,
        source.VARS[1]: sp.Rational(b_sign * 24, 13),
        source.VARS[2]: 1,
    }
    zero = source.sp.Poly(0, *source.VARS, domain=source.sp.ZZ)
    matrix = []
    triples = []
    for row_label in row_labels:
        row = []
        for column_index, column in enumerate(columns):
            payload = pair_payload(
                column.get(row_label, zero).as_expr().subs(substitutions)
            )
            row.append(payload)
            if payload != ["0", "0"]:
                triples.append([row_label, column_index, payload])
        matrix.append(row)
    return {
        "representation": "independent_sparse_Pauli_word_matrix",
        "b_sign": b_sign,
        "candidate_labels": labels,
        "row_labels": row_labels,
        "matrix": matrix,
        "parent_symbolic_matrix_sha256": parent_hash,
        "specialized_matrix_sha256": canonical_hash(
            {"candidate_labels": labels, "row_labels": row_labels, "triples": triples}
        ),
        "nonzero_entry_count": len(triples),
    }


def dense_symbolic_data(dense: Any) -> tuple[list[str], list[str], list, str]:
    hamiltonian = dense.primitive_hamiltonian(4, ENGINEERING_COUPLING)
    candidates = dense.candidate_matrices(4)
    labels = [label for label, _ in candidates]
    columns = []
    row_labels: list[str] | None = None
    for _, candidate in candidates:
        commutator = dense.sp.expand(
            -dense.sp.I * (hamiltonian * candidate - candidate * hamiltonian)
        )
        coordinates = dense.hermitian_coordinates(commutator)
        current = [label for label, _ in coordinates]
        if row_labels is None:
            row_labels = current
        elif row_labels != current:
            raise RuntimeError("dense coordinate order drift")
        columns.append([value for _, value in coordinates])
    if row_labels is None:
        raise RuntimeError("dense matrix is empty")
    parent_payload = [
        [row_labels[row_index], column_index, str(columns[column_index][row_index])]
        for row_index in range(len(row_labels))
        for column_index in range(len(columns))
        if columns[column_index][row_index] != 0
    ]
    return labels, row_labels, columns, canonical_hash(parent_payload)


def specialized_dense(
    dense: Any,
    b_sign: int,
    symbolic_data: tuple[list[str], list[str], list, str],
) -> dict[str, Any]:
    labels, row_labels, columns, parent_hash = symbolic_data
    substitutions = {
        dense.VARS[0]: S / 13,
        dense.VARS[1]: sp.Rational(b_sign * 24, 13),
        dense.VARS[2]: 1,
    }
    matrix = []
    triples = []
    for row_index, row_label in enumerate(row_labels):
        row = []
        for column_index in range(len(columns)):
            payload = pair_payload(columns[column_index][row_index].subs(substitutions))
            row.append(payload)
            if payload != ["0", "0"]:
                triples.append([row_label, column_index, payload])
        matrix.append(row)
    return {
        "representation": "dense_Kronecker_Hermitian_coordinate_matrix",
        "b_sign": b_sign,
        "candidate_labels": labels,
        "row_labels": row_labels,
        "matrix": matrix,
        "parent_symbolic_matrix_sha256": parent_hash,
        "specialized_matrix_sha256": canonical_hash(
            {"candidate_labels": labels, "row_labels": row_labels, "triples": triples}
        ),
        "nonzero_entry_count": len(triples),
    }


class QuadraticField:
    """GF(p)[s]/(s^2+407), represented as x+y*s."""

    zero = (0, 0)
    one = (1, 0)

    def __init__(self, prime: int) -> None:
        self.prime = prime

    def add(self, left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
        return ((left[0] + right[0]) % self.prime, (left[1] + right[1]) % self.prime)

    def sub(self, left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
        return ((left[0] - right[0]) % self.prime, (left[1] - right[1]) % self.prime)

    def neg(self, value: tuple[int, int]) -> tuple[int, int]:
        return (-value[0] % self.prime, -value[1] % self.prime)

    def mul(self, left: tuple[int, int], right: tuple[int, int]) -> tuple[int, int]:
        return (
            (left[0] * right[0] - 407 * left[1] * right[1]) % self.prime,
            (left[0] * right[1] + left[1] * right[0]) % self.prime,
        )

    def inverse(self, value: tuple[int, int]) -> tuple[int, int]:
        norm = (value[0] * value[0] + 407 * value[1] * value[1]) % self.prime
        if norm == 0:
            raise ZeroDivisionError("zero quadratic-field norm")
        inverse_norm = pow(norm, self.prime - 2, self.prime)
        return (value[0] * inverse_norm % self.prime, -value[1] * inverse_norm % self.prime)

    def from_payload(self, payload: list[str]) -> tuple[int, int]:
        output = []
        for raw in payload:
            value = Fraction(raw)
            output.append(
                value.numerator
                * pow(value.denominator % self.prime, self.prime - 2, self.prime)
                % self.prime
            )
        return output[0], output[1]


def finite_matrix(payload_matrix: list, field: QuadraticField) -> list:
    return [[field.from_payload(value) for value in row] for row in payload_matrix]


def select_rows(matrix: list, labels: list[str], field: QuadraticField, purpose: str) -> list[str]:
    order = sorted(
        range(len(labels)),
        key=lambda index: canonical_hash(
            {"purpose": purpose, "coordinate": labels[index], "prime": field.prime}
        ),
    )
    basis: dict[int, list[tuple[int, int]]] = {}
    selected = []
    for row_index in order:
        row = list(matrix[row_index])
        for pivot in sorted(basis):
            if row[pivot] == field.zero:
                continue
            factor = row[pivot]
            row = [
                field.sub(left, field.mul(factor, right))
                for left, right in zip(row, basis[pivot])
            ]
        pivot = next((i for i, value in enumerate(row) if value != field.zero), None)
        if pivot is None:
            continue
        inverse = field.inverse(row[pivot])
        basis[pivot] = [field.mul(value, inverse) for value in row]
        selected.append(labels[row_index])
        if len(selected) == len(row):
            break
    return selected


def determinant(matrix: list, field: QuadraticField) -> tuple[int, int]:
    rows = [list(row) for row in matrix]
    value = field.one
    for column in range(len(rows)):
        pivot = next(
            (row for row in range(column, len(rows)) if rows[row][column] != field.zero),
            None,
        )
        if pivot is None:
            return field.zero
        if pivot != column:
            rows[column], rows[pivot] = rows[pivot], rows[column]
            value = field.neg(value)
        pivot_value = rows[column][column]
        value = field.mul(value, pivot_value)
        inverse = field.inverse(pivot_value)
        rows[column] = [field.mul(entry, inverse) for entry in rows[column]]
        for row_index in range(column + 1, len(rows)):
            factor = rows[row_index][column]
            if factor == field.zero:
                continue
            rows[row_index] = [
                field.sub(left, field.mul(factor, right))
                for left, right in zip(rows[row_index], rows[column])
            ]
    return value


def irreducible_mod_prime(prime: int) -> bool:
    factors = sp.factor_list(QUADRATIC.as_expr(), modulus=prime)[1]
    return bool(
        len(factors) == 1
        and factors[0][1] == 1
        and sp.Poly(factors[0][0], S, modulus=prime).degree() == 2
    )


def certificate(payload: dict[str, Any]) -> dict[str, Any]:
    selection_field = QuadraticField(RANK_PRIMES[0])
    matrix = finite_matrix(payload["matrix"], selection_field)
    purpose = f"R207:{payload['representation']}:b_sign={payload['b_sign']}"
    selected = select_rows(matrix, payload["row_labels"], selection_field, purpose)
    if len(selected) != len(payload["candidate_labels"]):
        raise RuntimeError(f"{purpose} did not reach full rank")
    row_index = {label: index for index, label in enumerate(payload["row_labels"])}
    exact_square = [payload["matrix"][row_index[label]] for label in selected]
    prime_rows = []
    for prime in RANK_PRIMES:
        field = QuadraticField(prime)
        square = finite_matrix(exact_square, field)
        value = determinant(square, field)
        prime_rows.append(
            {
                "prime": prime,
                "quadratic_irreducible_mod_prime": irreducible_mod_prime(prime),
                "determinant_residue_x_y": list(value),
                "determinant_residue_sha256": canonical_hash(list(value)),
                "determinant_nonzero": value != field.zero,
                "replayed_rank": len(selected) if value != field.zero else None,
            }
        )
    checked = bool(
        all(row["quadratic_irreducible_mod_prime"] for row in prime_rows)
        and all(row["determinant_nonzero"] for row in prime_rows)
    )
    return {
        "representation": payload["representation"],
        "b_sign": payload["b_sign"],
        "algebraic_points_covered": [
            f"a=+sqrt(-407)/13,b={payload['b_sign'] * 24}/13,c=1",
            f"a=-sqrt(-407)/13,b={payload['b_sign'] * 24}/13,c=1",
        ],
        "shape": [len(payload["row_labels"]), len(payload["candidate_labels"])],
        "candidate_labels_sha256": canonical_hash(payload["candidate_labels"]),
        "row_labels_sha256": canonical_hash(payload["row_labels"]),
        "parent_symbolic_matrix_sha256": payload["parent_symbolic_matrix_sha256"],
        "specialized_matrix_sha256": payload["specialized_matrix_sha256"],
        "nonzero_entry_count": payload["nonzero_entry_count"],
        "selected_rows": selected,
        "selected_rows_sha256": canonical_hash(selected),
        "selected_row_count": len(selected),
        "exact_selected_submatrix": exact_square,
        "exact_selected_submatrix_sha256": canonical_hash(exact_square),
        "prime_replays": prime_rows,
        "rank_over_QQ_s_mod_quadratic": len(selected) if checked else None,
        "both_quadratic_conjugates_full_rank": checked,
        "checked": checked,
    }


def cross_branch_replay(
    certificate_row: dict[str, Any], target_payload: dict[str, Any]
) -> dict[str, Any]:
    row_index = {label: index for index, label in enumerate(target_payload["row_labels"])}
    square_payload = [
        target_payload["matrix"][row_index[label]]
        for label in certificate_row["selected_rows"]
    ]
    rows = []
    for prime in RANK_PRIMES:
        field = QuadraticField(prime)
        value = determinant(finite_matrix(square_payload, field), field)
        rows.append(
            {
                "prime": prime,
                "determinant_residue_x_y": list(value),
                "determinant_nonzero": value != field.zero,
            }
        )
    return {
        "source_b_sign": certificate_row["b_sign"],
        "target_b_sign": target_payload["b_sign"],
        "representation": certificate_row["representation"],
        "selected_rows_sha256": certificate_row["selected_rows_sha256"],
        "target_square_sha256": canonical_hash(square_payload),
        "exact_target_submatrix": square_payload,
        "prime_replays": rows,
        "same_minor_nonzero_on_target_branch": all(
            row["determinant_nonzero"] for row in rows
        ),
    }


def build_result(root: Path) -> dict[str, Any]:
    paths = {
        "r206": root / R206_PATH,
        "r201": root / R201_PATH,
        "dense_tool": root / DENSE_TOOL_PATH,
        "source_tool": root / SOURCE_TOOL_PATH,
        "r207_tool": Path(__file__).resolve(),
    }
    r206_result = json.loads(paths["r206"].read_text())
    if (
        not payload_hash_valid(r206_result)
        or r206_result.get("checked") is not True
        or r206_result.get("preflight_conclusion")
        != "two_prime_nonunit_outside_b_zero_after_sixth_minor"
        or r206_result.get("expanded_minor_count") != 6
    ):
        raise ValueError("R206 source result is not accepted")
    singular = shutil.which("Singular")
    if singular is None:
        raise RuntimeError("Singular executable not found")
    radical_rows = [run_singular(root, singular, prime) for prime in CLASSIFICATION_PRIMES]
    if not all(row["checked"] for row in radical_rows):
        print(json.dumps(radical_rows, indent=2, sort_keys=True), file=sys.stderr)
        raise RuntimeError("two-prime radical classification failed")

    source = load_module(paths["source_tool"], "b9_r207_source_dependency")
    dense = load_module(paths["dense_tool"], "b9_r207_dense_dependency")
    source_symbolic = source.symbolic_matrix(4, ENGINEERING_COUPLING)
    dense_symbolic = dense_symbolic_data(dense)
    payloads = []
    for b_sign in (1, -1):
        payloads.append(specialized_source(source, b_sign, source_symbolic))
        payloads.append(specialized_dense(dense, b_sign, dense_symbolic))
    certificates = [certificate(payload) for payload in payloads]
    by_key = {
        (payload["representation"], payload["b_sign"]): payload
        for payload in payloads
    }
    cross_rows = [
        cross_branch_replay(
            row,
            by_key[(row["representation"], -row["b_sign"])],
        )
        for row in certificates
    ]
    all_full_rank = all(row["checked"] for row in certificates)
    common_minor_exists = any(
        row["same_minor_nonzero_on_target_branch"] for row in cross_rows
    )
    stable = {
        "source_sha256": {label: sha256_file(path) for label, path in paths.items()},
        "candidate_radical_generators": [
            "169*a^2+407*c^2",
            "169*b^2-576*c^2",
            "2*u*c^2-1",
        ],
        "classification_primes": list(CLASSIFICATION_PRIMES),
        "rank_primes": list(RANK_PRIMES),
        "radical_rows": radical_rows,
        "representation_rows": [
            {
                "representation": row["representation"],
                "b_sign": row["b_sign"],
                "shape": row["shape"],
                "specialized_matrix_sha256": row["specialized_matrix_sha256"],
                "selected_rows_sha256": row["selected_rows_sha256"],
                "exact_selected_submatrix_sha256": row[
                    "exact_selected_submatrix_sha256"
                ],
                "prime_replays": row["prime_replays"],
            }
            for row in certificates
        ],
        "cross_branch_rows": cross_rows,
    }
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R206_off_slice_component_classification_only",
        "coupling": "13/32",
        "n": 4,
        "source_sha256": stable["source_sha256"],
        "singular_path": singular,
        "singular_version": subprocess.check_output(
            [singular, "--version"], text=True
        ).splitlines()[0],
        "classification_primes": list(CLASSIFICATION_PRIMES),
        "candidate_radical_generators": stable["candidate_radical_generators"],
        "candidate_radical_generator_sha256": canonical_hash(
            stable["candidate_radical_generators"]
        ),
        "radical_classification_rows": radical_rows,
        "two_prime_radical_equality_supported": all(
            row["original_generators_reduce_to_zero_mod_candidate_radical"]
            and row["candidate_generator_squares_reduce_to_zero_mod_original"]
            and row["c_one_original_vector_space_dimension"] == 8
            and row["c_one_candidate_radical_vector_space_dimension"] == 4
            and row["c_zero_original_is_unit_ideal"]
            for row in radical_rows
        ),
        "projective_chart": "c=1; c=0 is excluded by the saturated six-minor ideal",
        "candidate_point_count_over_algebraic_closure": 4,
        "candidate_point_multiplicity_in_original_chart": 2,
        "candidate_points": [
            "a=+sqrt(-407)/13,b=+24/13,c=1,u=1/2",
            "a=-sqrt(-407)/13,b=+24/13,c=1,u=1/2",
            "a=+sqrt(-407)/13,b=-24/13,c=1,u=1/2",
            "a=-sqrt(-407)/13,b=-24/13,c=1,u=1/2",
        ],
        "candidate_norm_a2_b2_c2": "2",
        "quadratic_polynomial": "s^2+407",
        "quadratic_irreducible_over_QQ": sp.Poly(S**2 + 407, S).is_irreducible,
        "rank_primes": list(RANK_PRIMES),
        "rank_prime_quadratic_irreducibility": {
            str(prime): irreducible_mod_prime(prime) for prime in RANK_PRIMES
        },
        "representation_certificates": certificates,
        "cross_branch_minor_replays": cross_rows,
        "all_four_candidate_points_full_rank_in_both_representations": all_full_rank,
        "off_slice_component_is_full_rank_selected_minor_artifact": all_full_rank,
        "one_existing_selected_minor_excludes_both_b_sign_branches": common_minor_exists,
        "next_gate": (
            "promote_one_cross_branch_nonzero_selected_minor_and_rerun_the_saturated_ideal"
            if common_minor_exists
            else "find_one_or_two_minors_covering_both_b_sign_branches_and_rerun_the_saturated_ideal"
        ),
        "rational_nullstellensatz_certificate_verified": False,
        "global_full_rank_theorem_verified": False,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "claim_boundary": (
            "R207 classifies only the off-slice component left by the R206 six-minor "
            "modular ideals. Two good-characteristic radical replays and complete-matrix "
            "rank certificates show that its four algebraic points are selected-minor "
            "artifacts; they do not prove the characteristic-zero saturated ideal is the "
            "unit ideal, global full rank, Quantum PCP, NLTS, or a BQP separation."
        ),
        "python_version": platform.python_version(),
        "sympy_version": sp.__version__,
        "stable_classification_payload": stable,
        "stable_classification_sha256": canonical_hash(stable),
        "checked": bool(
            all(row["checked"] for row in radical_rows)
            and all_full_rank
            and sp.Poly(S**2 + 407, S).is_irreducible
        ),
    }
    result["payload_sha256"] = canonical_hash(result)
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
                "candidate_point_count": result[
                    "candidate_point_count_over_algebraic_closure"
                ],
                "all_four_points_full_rank": result[
                    "all_four_candidate_points_full_rank_in_both_representations"
                ],
                "one_minor_crosses_both_branches": result[
                    "one_existing_selected_minor_excludes_both_b_sign_branches"
                ],
                "new_credit_delta": result["new_credit_delta"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
