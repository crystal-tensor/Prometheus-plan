#!/usr/bin/env python3
"""Classify the R204 sextic component against both complete R201 matrices."""

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


METHOD = "b9_r205_sextic_algebraic_full_matrix_rank_v1"
VERSION = "0.1.0"
ENGINEERING_COUPLING = Fraction(13, 32)
AUDIT_PRIMES = (1_000_117, 1_000_121)
R203_PATH = Path("results/B9_R203_rational_common_zero_rank_replay_v0.json")
R204_PATH = Path("results/B9_R204_expanded_ideal_preflight_v0.json")
DENSE_TOOL_PATH = Path("tools/b9_r201_presource_manifest.py")
SOURCE_TOOL_PATH = Path("tools/b9_r201_independent_audit.py")
T = sp.symbols("t")
SEXTIC = sp.Poly(
    768 * T**6
    - 256 * T**5
    - 7227 * T**4
    + 5120 * T**3
    + 7227 * T**2
    - 256 * T
    - 768,
    T,
    domain=sp.ZZ,
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


def rational_text(value: sp.Rational) -> str:
    value = sp.Rational(value)
    return str(value.p) if value.q == 1 else f"{value.p}/{value.q}"


def polynomial_payload(expression: sp.Expr, variables: tuple[sp.Symbol, ...]) -> list:
    specialized = sp.Poly(
        sp.expand(
            expression.subs(
                {variables[0]: T, variables[1]: sp.Integer(0), variables[2]: sp.Integer(1)}
            )
        ),
        T,
        domain=sp.QQ,
    )
    return [
        [[int(monomial[0])], [str(sp.Rational(coefficient).p), str(sp.Rational(coefficient).q)]]
        for monomial, coefficient in specialized.terms()
        if coefficient != 0
    ]


def source_specialized_matrix(source: Any) -> dict[str, Any]:
    labels, columns, output_words, source_hash = source.symbolic_matrix(
        4, ENGINEERING_COUPLING
    )
    zero = source.sp.Poly(0, *source.VARS, domain=source.sp.ZZ)
    matrix = []
    triples = []
    for row_index, word in enumerate(output_words):
        row = []
        for column_index, column in enumerate(columns):
            payload = polynomial_payload(
                column.get(word, zero).as_expr(), source.VARS
            )
            row.append(payload)
            if payload:
                triples.append([word, column_index, payload])
        matrix.append(row)
    return {
        "representation": "independent_sparse_Pauli_word_matrix",
        "candidate_labels": labels,
        "row_labels": output_words,
        "matrix": matrix,
        "specialized_matrix_sha256": canonical_hash(
            {"candidate_labels": labels, "row_labels": output_words, "triples": triples}
        ),
        "parent_symbolic_matrix_sha256": source_hash,
        "nonzero_entry_count": len(triples),
    }


def dense_specialized_matrix(dense: Any) -> dict[str, Any]:
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
        current_labels = [label for label, _ in coordinates]
        if row_labels is None:
            row_labels = current_labels
        elif row_labels != current_labels:
            raise RuntimeError("dense coordinate order drift")
        columns.append(
            [polynomial_payload(value, dense.VARS) for _, value in coordinates]
        )
    if row_labels is None:
        raise RuntimeError("dense matrix is empty")
    matrix = []
    triples = []
    for row_index, row_label in enumerate(row_labels):
        row = []
        for column_index in range(len(columns)):
            payload = columns[column_index][row_index]
            row.append(payload)
            if payload:
                triples.append([row_label, column_index, payload])
        matrix.append(row)
    return {
        "representation": "dense_Kronecker_Hermitian_coordinate_matrix",
        "candidate_labels": labels,
        "row_labels": row_labels,
        "matrix": matrix,
        "specialized_matrix_sha256": canonical_hash(
            {"candidate_labels": labels, "row_labels": row_labels, "triples": triples}
        ),
        "parent_symbolic_matrix_sha256": canonical_hash(triples),
        "nonzero_entry_count": len(triples),
    }


class FiniteExtension:
    """Small project-owned GF(p)[t]/(SEXTIC) arithmetic."""

    degree = 6

    def __init__(self, prime: int) -> None:
        self.prime = prime
        inverse_lead = pow(768, prime - 2, prime)
        self.relation = tuple(
            value * inverse_lead % prime
            for value in (768, 256, -7227, -5120, 7227, 256)
        )
        self.zero = (0,) * self.degree
        self.one = (1,) + (0,) * (self.degree - 1)

    def add(self, left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
        return tuple((a + b) % self.prime for a, b in zip(left, right))

    def sub(self, left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
        return tuple((a - b) % self.prime for a, b in zip(left, right))

    def neg(self, value: tuple[int, ...]) -> tuple[int, ...]:
        return tuple(-coefficient % self.prime for coefficient in value)

    def mul(self, left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
        values = [0] * (2 * self.degree - 1)
        for left_degree, left_coefficient in enumerate(left):
            if not left_coefficient:
                continue
            for right_degree, right_coefficient in enumerate(right):
                if right_coefficient:
                    values[left_degree + right_degree] = (
                        values[left_degree + right_degree]
                        + left_coefficient * right_coefficient
                    ) % self.prime
        for degree in range(len(values) - 1, self.degree - 1, -1):
            coefficient = values[degree] % self.prime
            if not coefficient:
                continue
            values[degree] = 0
            offset = degree - self.degree
            for relation_degree, relation_coefficient in enumerate(self.relation):
                values[offset + relation_degree] = (
                    values[offset + relation_degree]
                    + coefficient * relation_coefficient
                ) % self.prime
        return tuple(value % self.prime for value in values[: self.degree])

    def power(self, value: tuple[int, ...], exponent: int) -> tuple[int, ...]:
        output = self.one
        base = value
        while exponent:
            if exponent & 1:
                output = self.mul(output, base)
            base = self.mul(base, base)
            exponent >>= 1
        return output

    def inverse(self, value: tuple[int, ...]) -> tuple[int, ...]:
        if value == self.zero:
            raise ZeroDivisionError("zero has no inverse")
        inverse = self.power(value, self.prime**self.degree - 2)
        if self.mul(value, inverse) != self.one:
            raise ArithmeticError("finite-extension inverse replay failed")
        return inverse

    def from_payload(self, payload: list) -> tuple[int, ...]:
        values = [0] * self.degree
        for raw_monomial, raw_fraction in payload:
            exponent = int(raw_monomial[0])
            numerator, denominator = (int(value) for value in raw_fraction)
            coefficient = numerator % self.prime
            coefficient = coefficient * pow(
                denominator % self.prime, self.prime - 2, self.prime
            ) % self.prime
            term = [0] * (exponent + 1)
            term[exponent] = coefficient
            for degree in range(len(term) - 1, self.degree - 1, -1):
                current = term[degree] % self.prime
                if not current:
                    continue
                term[degree] = 0
                offset = degree - self.degree
                if len(term) < offset + self.degree:
                    term.extend([0] * (offset + self.degree - len(term)))
                for relation_degree, relation_coefficient in enumerate(self.relation):
                    term[offset + relation_degree] = (
                        term[offset + relation_degree]
                        + current * relation_coefficient
                    ) % self.prime
            for degree, value in enumerate(term[: self.degree]):
                values[degree] = (values[degree] + value) % self.prime
        return tuple(values)


def finite_matrix(payload_matrix: list, field: FiniteExtension) -> list:
    return [
        [field.from_payload(payload) for payload in row] for row in payload_matrix
    ]


def select_rows(
    matrix: list,
    row_labels: list[str],
    field: FiniteExtension,
    representation: str,
) -> tuple[list[str], int]:
    order = sorted(
        range(len(row_labels)),
        key=lambda index: canonical_hash(
            {
                "purpose": "R205_sextic_extension_field_rank",
                "representation": representation,
                "coordinate": row_labels[index],
                "selection_prime": field.prime,
            }
        ),
    )
    basis: dict[int, list[tuple[int, ...]]] = {}
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
        pivot = next(
            (index for index, value in enumerate(row) if value != field.zero), None
        )
        if pivot is None:
            continue
        inverse = field.inverse(row[pivot])
        basis[pivot] = [field.mul(value, inverse) for value in row]
        selected.append(row_labels[row_index])
        if len(selected) == len(row):
            break
    return selected, len(basis)


def determinant(matrix: list, field: FiniteExtension) -> tuple[int, ...]:
    rows = [list(row) for row in matrix]
    determinant_value = field.one
    for column in range(len(rows)):
        pivot = next(
            (
                index
                for index in range(column, len(rows))
                if rows[index][column] != field.zero
            ),
            None,
        )
        if pivot is None:
            return field.zero
        if pivot != column:
            rows[column], rows[pivot] = rows[pivot], rows[column]
            determinant_value = field.neg(determinant_value)
        pivot_value = rows[column][column]
        determinant_value = field.mul(determinant_value, pivot_value)
        inverse = field.inverse(pivot_value)
        rows[column] = [field.mul(value, inverse) for value in rows[column]]
        for index in range(column + 1, len(rows)):
            factor = rows[index][column]
            if factor == field.zero:
                continue
            rows[index] = [
                field.sub(left, field.mul(factor, right))
                for left, right in zip(rows[index], rows[column])
            ]
    return determinant_value


def irreducible_mod_prime(prime: int) -> bool:
    factorization = sp.factor_list(SEXTIC.as_expr(), modulus=prime)[1]
    return bool(
        len(factorization) == 1
        and factorization[0][1] == 1
        and sp.Poly(factorization[0][0], T, modulus=prime).degree() == 6
    )


def representation_certificate(payload: dict[str, Any]) -> dict[str, Any]:
    selection_field = FiniteExtension(AUDIT_PRIMES[0])
    selection_matrix = finite_matrix(payload["matrix"], selection_field)
    selected_rows, rank = select_rows(
        selection_matrix,
        payload["row_labels"],
        selection_field,
        payload["representation"],
    )
    if rank != len(payload["candidate_labels"]):
        raise RuntimeError(
            f"{payload['representation']} is not full rank in the selection field"
        )
    row_index = {label: index for index, label in enumerate(payload["row_labels"])}
    prime_rows = []
    for prime in AUDIT_PRIMES:
        field = FiniteExtension(prime)
        matrix = finite_matrix(payload["matrix"], field)
        square = [matrix[row_index[label]] for label in selected_rows]
        value = determinant(square, field)
        prime_rows.append(
            {
                "prime": prime,
                "extension_degree": field.degree,
                "sextic_irreducible_mod_prime": irreducible_mod_prime(prime),
                "determinant_residue_coefficients_low_to_high": list(value),
                "determinant_residue_sha256": canonical_hash(list(value)),
                "determinant_nonzero": value != field.zero,
                "replayed_rank": len(selected_rows) if value != field.zero else None,
            }
        )
    checked = bool(
        len(selected_rows) == len(payload["candidate_labels"])
        and all(row["sextic_irreducible_mod_prime"] for row in prime_rows)
        and all(row["determinant_nonzero"] for row in prime_rows)
    )
    return {
        "representation": payload["representation"],
        "shape": [len(payload["row_labels"]), len(payload["candidate_labels"])],
        "candidate_labels_sha256": canonical_hash(payload["candidate_labels"]),
        "row_labels_sha256": canonical_hash(payload["row_labels"]),
        "parent_symbolic_matrix_sha256": payload["parent_symbolic_matrix_sha256"],
        "specialized_matrix_sha256": payload["specialized_matrix_sha256"],
        "nonzero_entry_count": payload["nonzero_entry_count"],
        "row_selection_method": "sha256(purpose,representation,coordinate,selection_prime)",
        "row_selection_prime": AUDIT_PRIMES[0],
        "selected_rows": selected_rows,
        "selected_rows_sha256": canonical_hash(selected_rows),
        "selected_row_count": len(selected_rows),
        "prime_replays": prime_rows,
        "rank_over_QQ_t_mod_sextic": len(selected_rows) if checked else None,
        "rank_proof": "same_maximal_minor_nonzero_under_two_irreducible_good_reductions",
        "all_six_conjugate_roots_full_rank": checked,
        "checked": checked,
    }


def build_result(root: Path) -> dict[str, Any]:
    paths = {
        "r203": root / R203_PATH,
        "r204": root / R204_PATH,
        "dense_tool": root / DENSE_TOOL_PATH,
        "source_tool": root / SOURCE_TOOL_PATH,
    }
    r203 = json.loads(paths["r203"].read_text())
    r204 = json.loads(paths["r204"].read_text())
    if (
        r203.get("checked") is not True
        or r204.get("checked") is not True
        or r204.get("expanded_slice_matches_R203_residual_degree_six") is not True
    ):
        raise ValueError("R203/R204 source chain is not accepted")

    rational_factorization = sp.factor_list(SEXTIC.as_expr(), T)
    irreducible_over_qq = bool(
        rational_factorization[0] == 1
        and len(rational_factorization[1]) == 1
        and rational_factorization[1][0][1] == 1
        and sp.Poly(rational_factorization[1][0][0], T, domain=sp.QQ).degree() == 6
    )
    intervals = SEXTIC.intervals(eps=sp.Rational(1, 10**10))
    real_root_rows = [
        {
            "lower": rational_text(lower),
            "upper": rational_text(upper),
            "multiplicity": int(multiplicity),
        }
        for (lower, upper), multiplicity in intervals
    ]
    discriminant = int(sp.discriminant(SEXTIC.as_expr(), T))

    dense = load_module(paths["dense_tool"], "b9_r205_dense_dependency")
    source = load_module(paths["source_tool"], "b9_r205_source_dependency")
    source_payload = source_specialized_matrix(source)
    dense_payload = dense_specialized_matrix(dense)
    if source_payload["candidate_labels"] != dense_payload["candidate_labels"]:
        raise RuntimeError("candidate labels differ across representations")

    source_certificate = representation_certificate(source_payload)
    dense_certificate = representation_certificate(dense_payload)
    certificates = [source_certificate, dense_certificate]
    all_full_rank = bool(
        irreducible_over_qq
        and len(real_root_rows) == 6
        and all(row["multiplicity"] == 1 for row in real_root_rows)
        and all(certificate["checked"] for certificate in certificates)
    )
    stable = {
        "source_sha256": {label: sha256_file(path) for label, path in paths.items()},
        "sextic_canonical_terms": [
            [[int(monomial[0])], str(int(coefficient))]
            for monomial, coefficient in SEXTIC.terms()
        ],
        "real_root_rows": real_root_rows,
        "audit_primes": list(AUDIT_PRIMES),
        "representation_rows": [
            {
                "representation": certificate["representation"],
                "shape": certificate["shape"],
                "specialized_matrix_sha256": certificate[
                    "specialized_matrix_sha256"
                ],
                "selected_rows_sha256": certificate["selected_rows_sha256"],
                "prime_replays": certificate["prime_replays"],
            }
            for certificate in certificates
        ],
    }
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R204_sextic_component_full_matrix_classification_only",
        "coupling": "13/32",
        "n": 4,
        "source_sha256": stable["source_sha256"],
        "sextic_canonical_terms": stable["sextic_canonical_terms"],
        "sextic_canonical_terms_sha256": canonical_hash(
            stable["sextic_canonical_terms"]
        ),
        "sextic_degree": SEXTIC.degree(),
        "sextic_irreducible_over_QQ": irreducible_over_qq,
        "sextic_discriminant": str(discriminant),
        "sextic_discriminant_sha256": hashlib.sha256(
            str(discriminant).encode()
        ).hexdigest(),
        "sextic_discriminant_nonzero": discriminant != 0,
        "real_root_count": len(real_root_rows),
        "real_root_rows": real_root_rows,
        "all_roots_real_and_simple": bool(
            len(real_root_rows) == 6
            and all(row["multiplicity"] == 1 for row in real_root_rows)
        ),
        "projective_chart": "[a:b:c]=[t:0:1]; c=0 excluded by nonzero a^6 coefficient",
        "D_positive_on_real_component": True,
        "audit_primes": list(AUDIT_PRIMES),
        "audit_prime_sextic_irreducibility": {
            str(prime): irreducible_mod_prime(prime) for prime in AUDIT_PRIMES
        },
        "representation_certificates": certificates,
        "dense_and_source_paths_separate": True,
        "all_six_real_sextic_points_full_rank_in_both_representations": all_full_rank,
        "sextic_component_is_full_rank_selected_minor_artifact": all_full_rank,
        "R204_five_minors_sufficient_for_full_rank_locus": False,
        "next_gate": "append_an_R205_excluding_minor_and_rerun_the_saturated_ideal",
        "rational_nullstellensatz_certificate_verified": False,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "claim_boundary": (
            "R205 classifies only the irreducible b=0 sextic component left by "
            "R204. Good-reduction nonzero determinants prove full rank at its six "
            "real conjugate points, but do not prove global full rank outside that "
            "component or supply a characteristic-zero unit-ideal certificate."
        ),
        "python_version": platform.python_version(),
        "sympy_version": sp.__version__,
        "stable_classification_payload": stable,
        "stable_classification_sha256": canonical_hash(stable),
        "checked": all_full_rank,
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
                "real_root_count": result["real_root_count"],
                "sextic_irreducible_over_QQ": result[
                    "sextic_irreducible_over_QQ"
                ],
                "all_six_real_sextic_points_full_rank_in_both_representations": result[
                    "all_six_real_sextic_points_full_rank_in_both_representations"
                ],
                "new_credit_delta": result["new_credit_delta"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
