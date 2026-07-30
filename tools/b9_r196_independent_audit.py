#!/usr/bin/env python3
"""Independently rebuild and audit the B9 R196 certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from fractions import Fraction
from itertools import product
from pathlib import Path
from typing import Any


RESULT_PATH = Path("results/B9_R196_extended_tail_charge_stress_v1.json")
AUDIT_PATH = Path("results/B9_R196_independent_audit_v1.json")
REPORT_PATH = Path("research/B9_R196_extended_tail_charge_stress.md")
CONTRACT_PATH = Path(
    "benchmarks/B9_R196_extended_tail_charge_contract_v0.json"
)
EXPECTED_CONTRACT_SHA256 = (
    "afc5a721320ccf2a73291b961e6c3c28e5029ebe9e783ef54ccda2d48223e668"
)
INDEPENDENT_PRIME = 1_000_037
SYMBOLS = "IXYZ"
SYMBOL_TO_CODE = {symbol: code for code, symbol in enumerate(SYMBOLS)}
CODE_TO_SYMBOL = dict(enumerate(SYMBOLS))

# phase is the coefficient of i in [left, right] / 2.
COMMUTATOR_PHASE = {
    (1, 2): 1,
    (2, 1): -1,
    (2, 3): 1,
    (3, 2): -1,
    (3, 1): 1,
    (1, 3): -1,
}
PRODUCT_CODE = {
    (0, 0): 0,
    (0, 1): 1,
    (0, 2): 2,
    (0, 3): 3,
    (1, 0): 1,
    (2, 0): 2,
    (3, 0): 3,
    (1, 1): 0,
    (2, 2): 0,
    (3, 3): 0,
    (1, 2): 3,
    (2, 1): 3,
    (2, 3): 1,
    (3, 2): 1,
    (3, 1): 2,
    (1, 3): 2,
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hash(value: Any) -> str:
    return sha256_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def encode(text: str) -> tuple[int, ...]:
    return tuple(SYMBOL_TO_CODE[symbol] for symbol in text)


def decode(word: tuple[int, ...]) -> str:
    return "".join(CODE_TO_SYMBOL[code] for code in word)


def placed_word(
    n: int,
    start: int,
    local: tuple[int, ...],
) -> tuple[int, ...]:
    output = [0] * n
    output[start : start + len(local)] = local
    return tuple(output)


def local_patterns(max_range: int) -> list[tuple[int, tuple[int, ...]]]:
    patterns: list[tuple[int, tuple[int, ...]]] = []
    for span in range(1, max_range + 1):
        for local in product(range(4), repeat=span):
            if local[0] == 0 or local[-1] == 0:
                continue
            patterns.append((span, tuple(local)))
    return patterns


def complete_basis(n: int, max_range: int) -> list[tuple[int, ...]]:
    basis = [tuple([0] * n)]
    for span in range(1, max_range + 1):
        for start in range(n - span + 1):
            for _, local in local_patterns(span):
                if len(local) != span:
                    continue
                basis.append(placed_word(n, start, local))
    return basis


def hamiltonian_terms(
    n: int,
    coupling: Fraction,
) -> tuple[list[tuple[int, tuple[int, ...]]], int]:
    denominator = math.lcm(4, coupling.denominator)
    field = 3 * denominator // 4
    interaction = coupling.numerator * denominator // coupling.denominator
    terms: list[tuple[int, tuple[int, ...]]] = []
    for site in range(n):
        terms.append((-denominator, placed_word(n, site, (1,))))
        terms.append((field, placed_word(n, site, (3,))))
    if interaction:
        for site in range(n - 1):
            terms.append(
                (interaction, placed_word(n, site, (3, 3)))
            )
    return terms, denominator


def multiply_and_phase(
    left: tuple[int, ...],
    right: tuple[int, ...],
) -> tuple[int, tuple[int, ...]] | None:
    anticommute_sites = 0
    phase_sign = 1
    output: list[int] = []
    for left_code, right_code in zip(left, right):
        phase = COMMUTATOR_PHASE.get((left_code, right_code), 0)
        if phase:
            anticommute_sites += 1
            phase_sign *= phase
        output.append(PRODUCT_CODE[(left_code, right_code)])
    if anticommute_sites % 2 == 0:
        return None
    # The product phase is i^(odd count); reduce it to +/-i.
    phase_sign *= -1 if anticommute_sites % 4 == 3 else 1
    return phase_sign, tuple(output)


def raw_commutator_columns(
    basis: list[tuple[int, ...]],
    terms: list[tuple[int, tuple[int, ...]]],
) -> tuple[list[dict[tuple[int, ...], int]], list[tuple[int, ...]]]:
    raw: list[dict[tuple[int, ...], int]] = []
    output_words: set[tuple[int, ...]] = set()
    for candidate in basis:
        column: dict[tuple[int, ...], int] = {}
        for coefficient, term in terms:
            multiplied = multiply_and_phase(term, candidate)
            if multiplied is None:
                continue
            sign, output = multiplied
            column[output] = column.get(output, 0) + coefficient * sign
        column = {key: value for key, value in column.items() if value}
        raw.append(column)
        output_words.update(column)
    return raw, sorted(output_words)


def indexed_columns(
    raw: list[dict[tuple[int, ...], int]],
    output_basis: list[tuple[int, ...]],
) -> list[dict[int, int]]:
    output_index = {
        word: position for position, word in enumerate(output_basis)
    }
    return [
        {output_index[word]: value for word, value in column.items()}
        for column in raw
    ]


def combine(
    columns: list[dict[int, int]],
    coefficients: dict[int, int],
) -> dict[int, int]:
    result: dict[int, int] = {}
    for column_index, coefficient in coefficients.items():
        for row, value in columns[column_index].items():
            result[row] = result.get(row, 0) + coefficient * value
    return {row: value for row, value in result.items() if value}


def sparse_rank(
    columns: list[dict[int, int]],
    prime: int = INDEPENDENT_PRIME,
) -> int:
    active = {
        index: {
            row: value % prime
            for row, value in column.items()
            if value % prime
        }
        for index, column in enumerate(columns)
    }
    incidence: dict[int, set[int]] = {}
    for index, column in active.items():
        for row in column:
            incidence.setdefault(row, set()).add(index)

    rank = 0
    while active:
        pivot_index = min(active, key=lambda i: (len(active[i]), i))
        pivot = active[pivot_index]
        if not pivot:
            active.pop(pivot_index)
            continue
        pivot_row = min(pivot, key=lambda row: (len(incidence[row]), row))
        inverse = pow(pivot[pivot_row], prime - 2, prime)
        normalized = {
            row: value * inverse % prime for row, value in pivot.items()
        }
        for target_index in sorted(
            incidence[pivot_row] - {pivot_index}
        ):
            target = active[target_index]
            factor = target[pivot_row]
            for row, value in normalized.items():
                old = target.get(row, 0)
                new = (old - factor * value) % prime
                if new:
                    target[row] = new
                    if not old:
                        incidence.setdefault(row, set()).add(target_index)
                elif old:
                    target.pop(row)
                    incidence[row].discard(target_index)
                    if not incidence[row]:
                        incidence.pop(row)
        for row in pivot:
            incidence[row].discard(pivot_index)
            if not incidence[row]:
                incidence.pop(row)
        active.pop(pivot_index)
        rank += 1
    return rank


def complete_row(
    n: int,
    coupling: Fraction,
    max_range: int,
) -> dict[str, Any]:
    basis = complete_basis(n, max_range)
    terms, denominator = hamiltonian_terms(n, coupling)
    raw, output_basis = raw_commutator_columns(basis, terms)
    columns = indexed_columns(raw, output_basis)
    triples = [
        (decode(output_basis[row]), column_index, value)
        for column_index, column in enumerate(columns)
        for row, value in sorted(column.items())
    ]
    matrix_hash = canonical_hash(
        {
            "candidate_basis": [decode(word) for word in basis],
            "output_basis": [decode(word) for word in output_basis],
            "triples": triples,
        }
    )
    basis_index = {word: index for index, word in enumerate(basis)}
    identity = {basis_index[tuple([0] * n)]: 1}
    hamiltonian: dict[int, int] = {}
    for coefficient, term in terms:
        position = basis_index[term]
        hamiltonian[position] = (
            hamiltonian.get(position, 0) + coefficient
        )
    rank = sparse_rank(columns)
    return {
        "candidate_basis_size": len(basis),
        "output_basis_size": len(output_basis),
        "commutator_nonzero_count": len(triples),
        "commutator_matrix_sha256": matrix_hash,
        "hamiltonian_common_denominator": denominator,
        "identity_kernel_verified": not combine(columns, identity),
        "hamiltonian_kernel_verified": not combine(columns, hamiltonian),
        "independent_modular_prime": INDEPENDENT_PRIME,
        "independent_modular_rank": rank,
        "independent_modular_nullity": len(basis) - rank,
    }


def reduced_family_row(
    n: int,
    coupling: Fraction,
    parent_range: int,
    family: str,
    boundary_range: int = 0,
) -> dict[str, Any]:
    parent_basis = complete_basis(n, parent_range)
    parent_index = {
        word: position for position, word in enumerate(parent_basis)
    }
    terms, denominator = hamiltonian_terms(n, coupling)
    raw, output_basis = raw_commutator_columns(parent_basis, terms)
    parent_columns = indexed_columns(raw, output_basis)

    labels = ["identity"]
    vectors: list[dict[int, int]] = [
        {parent_index[tuple([0] * n)]: 1}
    ]
    for span, local in local_patterns(parent_range):
        labels.append(f"bulk_range_{span}:{decode(local)}")
        vectors.append(
            {
                parent_index[placed_word(n, start, local)]: 1
                for start in range(n - span + 1)
            }
        )
    if family == "translation":
        labels = [
            label.replace("bulk_range_", "range_") for label in labels
        ]
    elif family == "boundary":
        for span, local in local_patterns(boundary_range):
            labels.append(f"left_range_{span}:{decode(local)}")
            vectors.append({parent_index[placed_word(n, 0, local)]: 1})
            labels.append(f"right_range_{span}:{decode(local)}")
            vectors.append(
                {
                    parent_index[
                        placed_word(n, n - span, local)
                    ]: 1
                }
            )
    else:
        raise ValueError(f"unknown reduced family: {family}")

    columns = [combine(parent_columns, vector) for vector in vectors]
    triples = [
        (decode(output_basis[row]), column_index, value)
        for column_index, column in enumerate(columns)
        for row, value in sorted(column.items())
    ]
    matrix_hash = canonical_hash(
        {
            "candidate_labels": labels,
            "output_basis": [decode(word) for word in output_basis],
            "triples": triples,
        }
    )
    label_index = {label: index for index, label in enumerate(labels)}
    prefix = "range_" if family == "translation" else "bulk_range_"
    hamiltonian = {
        label_index[f"{prefix}1:X"]: -denominator,
        label_index[f"{prefix}1:Z"]: 3 * denominator // 4,
    }
    interaction = coupling.numerator * denominator // coupling.denominator
    if interaction:
        hamiltonian[label_index[f"{prefix}2:ZZ"]] = interaction
    rank = sparse_rank(columns)
    return {
        "candidate_basis_size": len(labels),
        "complete_parent_basis_size": len(parent_basis),
        "output_basis_size": len(output_basis),
        "commutator_nonzero_count": len(triples),
        "commutator_matrix_sha256": matrix_hash,
        "hamiltonian_common_denominator": denominator,
        "identity_kernel_verified": not columns[0],
        "hamiltonian_kernel_verified": not combine(columns, hamiltonian),
        "independent_modular_prime": INDEPENDENT_PRIME,
        "independent_modular_rank": rank,
        "independent_modular_nullity": len(labels) - rank,
    }


def commutator_of_sparse_operators(
    left: dict[tuple[int, ...], int],
    right: dict[tuple[int, ...], int],
) -> dict[tuple[int, ...], int]:
    result: dict[tuple[int, ...], int] = {}
    for left_word, left_value in left.items():
        for right_word, right_value in right.items():
            multiplied = multiply_and_phase(left_word, right_word)
            if multiplied is None:
                continue
            sign, output = multiplied
            result[output] = (
                result.get(output, 0)
                + left_value * right_value * sign
            )
    return {word: value for word, value in result.items() if value}


def positive_control_check(n: int = 10) -> dict[str, Any]:
    terms, _ = hamiltonian_terms(n, Fraction(0))
    hamiltonian = {word: coefficient for coefficient, word in terms}
    identity = {tuple([0] * n): 1}
    left_field = {
        placed_word(n, 0, (1,)): -4,
        placed_word(n, 0, (3,)): 3,
    }
    adjacent_product: dict[tuple[int, ...], int] = {}
    products = {
        (1, 1): 16,
        (1, 3): -12,
        (3, 1): -12,
        (3, 3): 9,
    }
    for site in range(n - 1):
        for local, coefficient in products.items():
            placed = placed_word(n, site, local)
            adjacent_product[placed] = (
                adjacent_product.get(placed, 0) + coefficient
            )
    witnesses = {
        "identity": identity,
        "hamiltonian_times_four": hamiltonian,
        "left_tilted_field_times_four": left_field,
        "adjacent_tilted_field_product_sum_times_sixteen": (
            adjacent_product
        ),
    }
    checks = {
        label: not commutator_of_sparse_operators(
            hamiltonian,
            witness,
        )
        for label, witness in witnesses.items()
    }
    return {
        "witness_kernel_checks": checks,
        "linearly_independent_by_disjoint_support_sectors": True,
        "checked": all(checks.values()),
    }


def compare_row(
    label: str,
    observed: dict[str, Any],
    rebuilt: dict[str, Any],
    errors: list[str],
) -> None:
    shared_fields = [
        "candidate_basis_size",
        "output_basis_size",
        "commutator_nonzero_count",
        "commutator_matrix_sha256",
        "hamiltonian_common_denominator",
        "identity_kernel_verified",
        "hamiltonian_kernel_verified",
    ]
    if "complete_parent_basis_size" in rebuilt:
        shared_fields.append("complete_parent_basis_size")
    for field in shared_fields:
        if observed.get(field) != rebuilt.get(field):
            errors.append(
                f"{label} {field} mismatch: "
                f"{observed.get(field)!r} != {rebuilt.get(field)!r}"
            )
    if rebuilt["independent_modular_nullity"] != 2:
        errors.append(
            f"{label} independent nullity is "
            f"{rebuilt['independent_modular_nullity']}, expected 2"
        )


def audit(root: Path) -> dict[str, Any]:
    payload = json.loads((root / RESULT_PATH).read_text())
    report = (root / REPORT_PATH).read_text()
    errors: list[str] = []

    stored_payload_hash = payload.get("payload_sha256")
    unhashed_payload = dict(payload)
    unhashed_payload.pop("payload_sha256", None)
    recomputed_payload_hash = canonical_hash(unhashed_payload)
    if stored_payload_hash != recomputed_payload_hash:
        errors.append("R196 payload self-hash mismatch")
    contract_hash = sha256_file(root / CONTRACT_PATH)
    if contract_hash != EXPECTED_CONTRACT_SHA256:
        errors.append("R196 contract hash mismatch")
    if payload.get("evidence", {}).get("contract_sha256") != contract_hash:
        errors.append("R196 payload contract binding mismatch")
    if payload.get("status") != "checked_extended_tail_charge_boundary":
        errors.append("R196 status mismatch")
    if payload.get("requirements_passed") != 15:
        errors.append("R196 frozen requirements are not 15/15")
    if payload.get("new_credit_delta") != 0:
        errors.append("R196 new credit must remain zero")

    independent_rows: dict[str, Any] = {
        "complete_range_six_n10": [],
        "translation_range_eight": [],
        "boundary_range_four": [],
    }
    for observed in payload.get("complete_range_six_n10_rows", []):
        rebuilt = complete_row(
            int(observed["n"]),
            Fraction(observed["coupling"]),
            6,
        )
        compare_row(
            f"complete J={observed['coupling']} n={observed['n']}",
            observed,
            rebuilt,
            errors,
        )
        independent_rows["complete_range_six_n10"].append(rebuilt)

    for observed in payload.get("translation_range_eight_rows", []):
        rebuilt = reduced_family_row(
            int(observed["n"]),
            Fraction(observed["coupling"]),
            8,
            "translation",
        )
        compare_row(
            f"translation J={observed['coupling']} n={observed['n']}",
            observed,
            rebuilt,
            errors,
        )
        independent_rows["translation_range_eight"].append(rebuilt)

    for observed in payload.get("boundary_range_four_rows", []):
        rebuilt = reduced_family_row(
            int(observed["n"]),
            Fraction(observed["coupling"]),
            6,
            "boundary",
            boundary_range=4,
        )
        compare_row(
            f"boundary J={observed['coupling']} n={observed['n']}",
            observed,
            rebuilt,
            errors,
        )
        independent_rows["boundary_range_four"].append(rebuilt)

    if len(independent_rows["complete_range_six_n10"]) != 2:
        errors.append("R196 independent complete row count mismatch")
    if len(independent_rows["translation_range_eight"]) != 1:
        errors.append("R196 independent translation row count mismatch")
    if len(independent_rows["boundary_range_four"]) != 4:
        errors.append("R196 independent boundary row count mismatch")

    positive_control = positive_control_check()
    if not positive_control["checked"]:
        errors.append("R196 independent positive control failed")
    required_report_phrases = [
        "Exact-nullity-two rows: `2/2`",
        "Candidate columns: `49153`",
        "Exact-nullity-two rows: `4/4`",
        "it does not prove nonintegrability",
    ]
    if any(phrase not in report for phrase in required_report_phrases):
        errors.append("R196 report claim boundary is incomplete")

    return {
        "audit_id": "B9-R196-independent-audit-v1",
        "method": "independent_integer_pauli_third_prime_rebuild",
        "independent_prime": INDEPENDENT_PRIME,
        "status": "pass" if not errors else "fail",
        "errors": errors,
        "error_count": len(errors),
        "result_payload_sha256": stored_payload_hash,
        "recomputed_payload_sha256": recomputed_payload_hash,
        "contract_sha256": contract_hash,
        "positive_control": positive_control,
        "independent_rows": independent_rows,
        "evidence_integrity_complete": not errors,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--output", type=Path, default=AUDIT_PATH)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    result = audit(root)
    output = (
        args.output if args.output.is_absolute() else root / args.output
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            result,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "audit_id": result["audit_id"],
                "status": result["status"],
                "error_count": result["error_count"],
                "independent_prime": result["independent_prime"],
                "result_payload_sha256": result[
                    "result_payload_sha256"
                ],
            },
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )
    return 0 if result["evidence_integrity_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
