#!/usr/bin/env python3
"""Execute the preregistered B9 R197 fermionization-frame stress.

The frozen holdouts are inaccessible unless the caller supplies the public
preregistration commit. Engineering mode is restricted to the declared probe.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any, Iterable


EXPERIMENT_ID = "B9-R197-nonstandard-fermionization-stress"
METHOD = "b9_r197_nonstandard_fermionization_stress_v1"
VERSION = "1.0"
LAST_UPDATED = "2026-07-30"
STATUS_ACCEPTED = "checked_nonstandard_fermionization_boundary"
STATUS_REJECTED = "nonstandard_fermionization_boundary_rejected"

CONTRACT_PATH = Path(
    "benchmarks/B9_R197_nonstandard_fermionization_contract_v0.json"
)
EXPECTED_CONTRACT_SHA256 = (
    "6ab7640f7d2ab686f81c2da7519260c5950120352dc14e7f6e4b700829b6b39e"
)
RESULT_PATH = Path(
    "results/B9_R197_nonstandard_fermionization_stress_v1.json"
)
REPORT_PATH = Path(
    "research/B9_R197_nonstandard_fermionization_stress.md"
)

ENGINEERING_COUPLING = Fraction(13, 32)
FROZEN_HOLDOUT_COUPLINGS = (Fraction(79, 128), Fraction(83, 128))
FROZEN_SIZES = (8, 9, 10)
MODULAR_PRIMES = (1_000_003, 1_000_033)
BASIS_SELECTION_PRIME = MODULAR_PRIMES[0]

PREVIOUSLY_OBSERVED_COUPLINGS = {
    Fraction(0),
    Fraction(1, 8),
    Fraction(3, 16),
    Fraction(1, 4),
    Fraction(5, 16),
    Fraction(23, 64),
    Fraction(3, 8),
    Fraction(13, 32),
    Fraction(53, 128),
    Fraction(27, 64),
    Fraction(7, 16),
    Fraction(31, 64),
    Fraction(1, 2),
    Fraction(69, 128),
    Fraction(35, 64),
    Fraction(9, 16),
    Fraction(73, 128),
    Fraction(77, 128),
    Fraction(5, 8),
    Fraction(11, 16),
    Fraction(3, 4),
    Fraction(7, 8),
    Fraction(1),
}

PAULI_PRODUCT: dict[tuple[str, str], tuple[complex, str]] = {
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

Axis = dict[str, Fraction]
Operator = dict[str, int]

AXIS_X: Axis = {"X": Fraction(1)}
AXIS_Y: Axis = {"Y": Fraction(1)}
AXIS_Z: Axis = {"Z": Fraction(1)}
AXIS_A: Axis = {"X": Fraction(-4, 5), "Z": Fraction(3, 5)}
AXIS_B: Axis = {"X": Fraction(3, 5), "Z": Fraction(4, 5)}

FRAMES: dict[str, dict[str, Axis]] = {
    "pauli_x": {"P": AXIS_X, "Q": AXIS_Y, "R": AXIS_Z},
    "pauli_y": {"P": AXIS_Y, "Q": AXIS_Z, "R": AXIS_X},
    "pauli_z": {"P": AXIS_Z, "Q": AXIS_X, "R": AXIS_Y},
    "tilted_a": {"P": AXIS_A, "Q": AXIS_B, "R": AXIS_Y},
    "tilted_b": {"P": AXIS_B, "Q": AXIS_Y, "R": AXIS_A},
}
FRAME_ORDER = tuple(FRAMES)

TRUE_CLAIMS = [
    "r197_contract_publicly_frozen_before_acceptance_execution",
    "r197_holdout_couplings_unseen_before_protocol_freeze",
    "declared_single_frame_quadratic_majorana_plus_h_families_have_nullity_two",
    "declared_five_frame_union_plus_h_family_has_nullity_two",
    "zero_coupling_tilted_frame_controls_recover_extra_exact_charges",
    "r196_candidate_survives_declared_r197_finite_fermionization_adversary",
]
FALSE_CLAIMS = [
    "all_frame_fermionization_exclusion",
    "nonlocal_duality_exclusion",
    "nonstandard_fermionization_exclusion",
    "interacting_integrability_exclusion",
    "complete_integrability_exclusion",
    "nonintegrability_theorem",
    "quantum_chaos_theorem",
    "spectral_hardness_theorem",
    "quantum_pcp_theorem",
    "nlts_theorem",
    "bqp_separation",
    "hardware_relevance",
    "solved_frontier",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hash(value: Any) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256_bytes(payload)


def fraction_text(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def lcm(values: Iterable[int]) -> int:
    result = 1
    for value in values:
        result = math.lcm(result, value)
    return result


def primitive_integer_operator(
    value: dict[str, Fraction] | dict[str, int],
) -> Operator:
    fractions = {
        word: Fraction(coefficient)
        for word, coefficient in value.items()
        if coefficient
    }
    if not fractions:
        return {}
    denominator = lcm(
        coefficient.denominator for coefficient in fractions.values()
    )
    integers = {
        word: int(coefficient * denominator)
        for word, coefficient in fractions.items()
    }
    divisor = 0
    for coefficient in integers.values():
        divisor = math.gcd(divisor, abs(coefficient))
    integers = {
        word: coefficient // divisor
        for word, coefficient in integers.items()
        if coefficient
    }
    first_word = min(integers)
    if integers[first_word] < 0:
        integers = {
            word: -coefficient for word, coefficient in integers.items()
        }
    return dict(sorted(integers.items()))


def operator_key(value: Operator) -> tuple[tuple[str, int], ...]:
    return tuple(sorted(value.items()))


def scaled_axis(axis: Axis, scale: int) -> Axis:
    return {pauli: coefficient * scale for pauli, coefficient in axis.items()}


def axis_vector(axis: Axis) -> tuple[Fraction, Fraction, Fraction]:
    return tuple(axis.get(pauli, Fraction(0)) for pauli in "XYZ")  # type: ignore[return-value]


def vector_dot(
    left: tuple[Fraction, Fraction, Fraction],
    right: tuple[Fraction, Fraction, Fraction],
) -> Fraction:
    return sum(
        (a * b for a, b in zip(left, right)),
        start=Fraction(0),
    )


def vector_cross(
    left: tuple[Fraction, Fraction, Fraction],
    right: tuple[Fraction, Fraction, Fraction],
) -> tuple[Fraction, Fraction, Fraction]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def frame_algebra_checks() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for frame_id, frame in FRAMES.items():
        p = axis_vector(frame["P"])
        q = axis_vector(frame["Q"])
        r = axis_vector(frame["R"])
        checks = {
            "p_norm_one": vector_dot(p, p) == 1,
            "q_norm_one": vector_dot(q, q) == 1,
            "r_norm_one": vector_dot(r, r) == 1,
            "p_dot_q_zero": vector_dot(p, q) == 0,
            "q_dot_r_zero": vector_dot(q, r) == 0,
            "r_dot_p_zero": vector_dot(r, p) == 0,
            "q_cross_r_equals_p": vector_cross(q, r) == p,
            "r_cross_p_equals_q": vector_cross(r, p) == q,
            "p_cross_q_equals_r": vector_cross(p, q) == r,
        }
        rows.append(
            {
                "frame_id": frame_id,
                "checks": checks,
                "checked": all(checks.values()),
            }
        )
    return {
        "rows": rows,
        "checked_frame_count": sum(row["checked"] for row in rows),
        "frame_count": len(rows),
        "checked": all(row["checked"] for row in rows),
    }


def expand_local_axes(
    n: int,
    site_axes: dict[int, Axis],
    scale: int = 1,
) -> Operator:
    partial: dict[str, Fraction] = {"I" * n: Fraction(scale)}
    for site in sorted(site_axes):
        axis = site_axes[site]
        updated: dict[str, Fraction] = {}
        for word, coefficient in partial.items():
            for pauli, local_coefficient in axis.items():
                chars = list(word)
                chars[site] = pauli
                output = "".join(chars)
                updated[output] = (
                    updated.get(output, Fraction(0))
                    + coefficient * local_coefficient
                )
        partial = updated
    return primitive_integer_operator(partial)


def gamma_operator(
    n: int,
    frame: dict[str, Axis],
    site: int,
    endpoint: str,
) -> Operator:
    axes = {index: frame["P"] for index in range(site)}
    axes[site] = frame[endpoint]
    return expand_local_axes(n, axes)


def bilinear_operator(
    n: int,
    frame: dict[str, Axis],
    left_site: int,
    left_endpoint: str,
    right_site: int,
    right_endpoint: str,
) -> Operator:
    if left_site == right_site:
        if (left_endpoint, right_endpoint) != ("Q", "R"):
            raise ValueError("same-site bilinear must be ordered Q,R")
        return expand_local_axes(
            n, {left_site: frame["P"]}, scale=-1
        )
    if left_site > right_site:
        raise ValueError("bilinear sites must be ordered")
    axes: dict[int, Axis] = {}
    if left_endpoint == "Q":
        axes[left_site] = frame["R"]
        sign = 1
    else:
        axes[left_site] = frame["Q"]
        sign = -1
    for site in range(left_site + 1, right_site):
        axes[site] = frame["P"]
    axes[right_site] = frame[right_endpoint]
    return expand_local_axes(n, axes, scale=sign)


def parity_operator(n: int, frame: dict[str, Axis]) -> Operator:
    return expand_local_axes(
        n, {site: frame["P"] for site in range(n)}
    )


@cache
def frame_operator_pool(
    n: int,
    frame_id: str,
) -> tuple[tuple[str, Operator], ...]:
    frame = FRAMES[frame_id]
    entries: list[tuple[str, Operator]] = []
    gamma_labels = [
        (site, endpoint)
        for site in range(n)
        for endpoint in ("Q", "R")
    ]
    for site, endpoint in gamma_labels:
        entries.append(
            (
                f"{frame_id}:gamma:{site}:{endpoint}",
                gamma_operator(n, frame, site, endpoint),
            )
        )
    for left_index, (left_site, left_endpoint) in enumerate(gamma_labels):
        for right_site, right_endpoint in gamma_labels[left_index + 1 :]:
            entries.append(
                (
                    (
                        f"{frame_id}:bilinear:{left_site}:{left_endpoint}:"
                        f"{right_site}:{right_endpoint}"
                    ),
                    bilinear_operator(
                        n,
                        frame,
                        left_site,
                        left_endpoint,
                        right_site,
                        right_endpoint,
                    ),
                )
            )
    entries.append(
        (f"{frame_id}:parity", parity_operator(n, frame))
    )
    return tuple(entries)


def pauli_word(n: int, operations: dict[int, str]) -> str:
    chars = ["I"] * n
    for site, pauli in operations.items():
        chars[site] = pauli
    return "".join(chars)


def hamiltonian_operator(n: int, coupling: Fraction) -> Operator:
    terms: dict[str, Fraction] = {}
    for site in range(n):
        x_word = pauli_word(n, {site: "X"})
        z_word = pauli_word(n, {site: "Z"})
        terms[x_word] = terms.get(x_word, Fraction(0)) - 1
        terms[z_word] = terms.get(z_word, Fraction(0)) + Fraction(3, 4)
    for site in range(n - 1):
        zz_word = pauli_word(n, {site: "Z", site + 1: "Z"})
        terms[zz_word] = terms.get(zz_word, Fraction(0)) + coupling
    return primitive_integer_operator(terms)


def modular_independent_basis(
    entries: list[tuple[str, Operator]],
    prime: int = BASIS_SELECTION_PRIME,
) -> list[tuple[str, Operator]]:
    pivots: dict[str, dict[str, int]] = {}
    selected: list[tuple[str, Operator]] = []
    for label, operator in entries:
        vector = {
            word: coefficient % prime
            for word, coefficient in operator.items()
            if coefficient % prime
        }
        while vector:
            pivot = min(vector)
            if pivot not in pivots:
                inverse = pow(vector[pivot], prime - 2, prime)
                pivots[pivot] = {
                    word: (coefficient * inverse) % prime
                    for word, coefficient in vector.items()
                    if (coefficient * inverse) % prime
                }
                selected.append((label, operator))
                break
            factor = vector[pivot]
            for word, coefficient in pivots[pivot].items():
                updated = (
                    vector.get(word, 0) - factor * coefficient
                ) % prime
                if updated:
                    vector[word] = updated
                else:
                    vector.pop(word, None)
    return selected


def operator_in_span(
    operator: Operator,
    basis: list[tuple[str, Operator]],
    prime: int = BASIS_SELECTION_PRIME,
) -> bool:
    augmented = list(basis) + [("__witness__", operator)]
    return len(modular_independent_basis(augmented, prime)) == len(basis)


def candidate_basis(
    n: int,
    coupling: Fraction,
    frame_ids: tuple[str, ...],
) -> list[tuple[str, Operator]]:
    identity = {"I" * n: 1}
    hamiltonian = hamiltonian_operator(n, coupling)
    entries: list[tuple[str, Operator]] = [
        ("identity", identity),
        ("hamiltonian", hamiltonian),
    ]
    seen = {operator_key(identity), operator_key(hamiltonian)}
    for frame_id in frame_ids:
        for label, operator in frame_operator_pool(n, frame_id):
            key = operator_key(operator)
            if key in seen:
                continue
            seen.add(key)
            entries.append((label, operator))
    selected = modular_independent_basis(entries)
    if [label for label, _ in selected[:2]] != [
        "identity",
        "hamiltonian",
    ]:
        raise AssertionError("identity and Hamiltonian must lead basis")
    return selected


def pauli_anticommutes(left: str, right: str) -> bool:
    return (
        sum(
            a != "I" and b != "I" and a != b
            for a, b in zip(left, right)
        )
        % 2
        == 1
    )


def pauli_multiply(left: str, right: str) -> tuple[complex, str]:
    phase: complex = 1
    output: list[str] = []
    for a, b in zip(left, right):
        local_phase, local_output = PAULI_PRODUCT[(a, b)]
        phase *= local_phase
        output.append(local_output)
    return phase, "".join(output)


def commutator_column(
    hamiltonian: Operator,
    candidate: Operator,
) -> Operator:
    output: dict[str, Fraction] = {}
    for h_word, h_coefficient in hamiltonian.items():
        for candidate_word, candidate_coefficient in candidate.items():
            if not pauli_anticommutes(h_word, candidate_word):
                continue
            phase, output_word = pauli_multiply(
                h_word, candidate_word
            )
            sign = int(round((phase / 1j).real))
            output[output_word] = (
                output.get(output_word, Fraction(0))
                + h_coefficient * candidate_coefficient * sign
            )
    return primitive_integer_operator(output)


def modular_sparse_rank(
    columns: list[dict[int, int]],
    prime: int,
) -> int:
    pivots: dict[int, dict[int, int]] = {}
    for column in columns:
        vector = {
            row: coefficient % prime
            for row, coefficient in column.items()
            if coefficient % prime
        }
        while vector:
            pivot = min(vector)
            if pivot not in pivots:
                inverse = pow(vector[pivot], prime - 2, prime)
                pivots[pivot] = {
                    row: (coefficient * inverse) % prime
                    for row, coefficient in vector.items()
                    if (coefficient * inverse) % prime
                }
                break
            factor = vector[pivot]
            for row, coefficient in pivots[pivot].items():
                updated = (
                    vector.get(row, 0) - factor * coefficient
                ) % prime
                if updated:
                    vector[row] = updated
                else:
                    vector.pop(row, None)
    return len(pivots)


def charge_row(
    n: int,
    coupling: Fraction,
    frame_ids: tuple[str, ...],
) -> dict[str, Any]:
    basis = candidate_basis(n, coupling, frame_ids)
    labels = [label for label, _ in basis]
    operators = [operator for _, operator in basis]
    hamiltonian = operators[1]
    raw_columns = [
        commutator_column(hamiltonian, operator)
        for operator in operators
    ]
    output_words = sorted(
        {
            word
            for column in raw_columns
            for word in column
        }
    )
    output_index = {
        word: index for index, word in enumerate(output_words)
    }
    columns = [
        {
            output_index[word]: coefficient
            for word, coefficient in column.items()
        }
        for column in raw_columns
    ]
    operator_basis_hash = canonical_hash(
        {
            "labels": labels,
            "operators": [
                sorted(operator.items()) for operator in operators
            ],
        }
    )
    triples = [
        (output_words[row], column_index, coefficient)
        for column_index, column in enumerate(columns)
        for row, coefficient in sorted(column.items())
    ]
    matrix_hash = canonical_hash(
        {
            "labels": labels,
            "output_basis": output_words,
            "triples": triples,
        }
    )
    ranks = {
        str(prime): modular_sparse_rank(columns, prime)
        for prime in MODULAR_PRIMES
    }
    nullities = {
        prime: len(columns) - rank for prime, rank in ranks.items()
    }
    exact_nullity_two = bool(
        coupling != 0
        and not columns[0]
        and not columns[1]
        and all(
            rank == len(columns) - 2 for rank in ranks.values()
        )
    )
    row = {
        "search_family": (
            "single_fermionization_frame_plus_h"
            if len(frame_ids) == 1
            else "five_frame_operator_union_plus_h"
        ),
        "frame_ids": list(frame_ids),
        "coupling": fraction_text(coupling),
        "n": n,
        "raw_candidate_count": (
            2
            + sum(
                len(frame_operator_pool(n, frame_id))
                for frame_id in frame_ids
            )
        ),
        "independent_operator_basis_size": len(columns),
        "operator_basis_pauli_nonzero_count": sum(
            len(operator) for operator in operators
        ),
        "operator_basis_sha256": operator_basis_hash,
        "output_basis_size": len(output_words),
        "commutator_nonzero_count": len(triples),
        "commutator_matrix_sha256": matrix_hash,
        "basis_selection_prime": BASIS_SELECTION_PRIME,
        "identity_kernel_verified": not columns[0],
        "hamiltonian_kernel_verified": not columns[1],
        "modular_primes": list(MODULAR_PRIMES),
        "modular_ranks": ranks,
        "modular_nullities": nullities,
        "exact_nullity_two_certified": exact_nullity_two,
        "checked": (
            exact_nullity_two
            if coupling != 0
            else all(nullity > 2 for nullity in nullities.values())
        ),
    }
    if coupling == 0 and "tilted_a" in frame_ids:
        witnesses = [
            expand_local_axes(n, {site: AXIS_A})
            for site in range(n)
        ]
        witness_commutators = [
            commutator_column(hamiltonian, witness)
            for witness in witnesses
        ]
        witness_in_span = [
            operator_in_span(witness, basis) for witness in witnesses
        ]
        row["onsite_tilted_charge_witness_count"] = len(witnesses)
        row["onsite_tilted_charge_commutes_count"] = sum(
            not column for column in witness_commutators
        )
        row["onsite_tilted_charge_in_span_count"] = sum(witness_in_span)
        row["onsite_tilted_charge_witnesses_checked"] = bool(
            all(not column for column in witness_commutators)
            and all(witness_in_span)
        )
    return row


def verify_public_freeze(
    root: Path,
    preregistration_commit: str,
) -> dict[str, Any]:
    if not preregistration_commit:
        raise ValueError(
            "--preregistration-commit is required for frozen holdouts"
        )
    commit = subprocess.run(
        ["git", "rev-parse", f"{preregistration_commit}^{{commit}}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    ancestor = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=root,
            check=False,
        ).returncode
        == 0
    )
    frozen_bytes = subprocess.run(
        ["git", "show", f"{commit}:{CONTRACT_PATH}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    frozen_hash = sha256_bytes(frozen_bytes)
    return {
        "preregistration_commit": commit,
        "is_ancestor_of_execution_head": ancestor,
        "contract_sha256_at_preregistration_commit": frozen_hash,
        "expected_contract_sha256": EXPECTED_CONTRACT_SHA256,
        "verified": bool(
            ancestor
            and frozen_hash == EXPECTED_CONTRACT_SHA256
            and sha256_file(root / CONTRACT_PATH)
            == EXPECTED_CONTRACT_SHA256
        ),
    }


def requirement(
    requirement_id: str,
    label: str,
    passed: bool,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def protocol(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "contract": {
            "path": str(CONTRACT_PATH),
            "sha256": EXPECTED_CONTRACT_SHA256,
            "version": contract["version"],
            "status": contract["status"],
        },
        "frozen_holdouts": [
            fraction_text(value)
            for value in FROZEN_HOLDOUT_COUPLINGS
        ],
        "frozen_sizes": list(FROZEN_SIZES),
        "frame_order": list(FRAME_ORDER),
        "single_frame_row_count": (
            len(FROZEN_HOLDOUT_COUPLINGS)
            * len(FROZEN_SIZES)
            * len(FRAME_ORDER)
        ),
        "union_row_count": (
            len(FROZEN_HOLDOUT_COUPLINGS) * len(FROZEN_SIZES)
        ),
        "modular_primes": list(MODULAR_PRIMES),
        "basis_selection_prime": BASIS_SELECTION_PRIME,
        "positive_control": contract["acceptance_rows"][
            "positive_control"
        ],
        "frame_algebra": frame_algebra_checks(),
        "claim_boundary": {
            "true_claims": TRUE_CLAIMS,
            "false_claims": FALSE_CLAIMS,
            "scientific_promotion_accepted": False,
            "new_credit_delta": 0,
        },
    }


def build_result(
    root: Path,
    preregistration_commit: str,
) -> dict[str, Any]:
    contract = json.loads((root / CONTRACT_PATH).read_text())
    freeze = verify_public_freeze(root, preregistration_commit)
    if not freeze["verified"]:
        raise RuntimeError("public preregistration freeze verification failed")
    protocol_payload = protocol(contract)
    algebra = protocol_payload["frame_algebra"]

    rows: list[dict[str, Any]] = []
    for coupling in FROZEN_HOLDOUT_COUPLINGS:
        for n in FROZEN_SIZES:
            for frame_id in FRAME_ORDER:
                rows.append(charge_row(n, coupling, (frame_id,)))
            rows.append(charge_row(n, coupling, FRAME_ORDER))

    controls = [
        charge_row(8, Fraction(0), ("tilted_a",)),
        charge_row(8, Fraction(0), FRAME_ORDER),
    ]
    single_rows = [
        row for row in rows if len(row["frame_ids"]) == 1
    ]
    union_rows = [
        row for row in rows if len(row["frame_ids"]) == len(FRAME_ORDER)
    ]
    passed_rows = sum(
        row["exact_nullity_two_certified"] for row in rows
    )
    controls_passed = sum(row["checked"] for row in controls)

    requirements = [
        requirement(
            "P1",
            "Public preregistration commit is an ancestor and hash-binds the contract",
            freeze["verified"],
            freeze,
        ),
        requirement(
            "P2",
            "Frozen holdouts are disjoint from all previous coupling grids",
            set(FROZEN_HOLDOUT_COUPLINGS).isdisjoint(
                PREVIOUSLY_OBSERVED_COUPLINGS
            ),
            {
                "holdouts": [
                    fraction_text(value)
                    for value in FROZEN_HOLDOUT_COUPLINGS
                ],
                "previous_count": len(PREVIOUSLY_OBSERVED_COUPLINGS),
            },
        ),
        requirement(
            "P3",
            "Engineering probe contributes zero frozen decisions",
            True,
            {
                "engineering_coupling": fraction_text(
                    ENGINEERING_COUPLING
                ),
                "acceptance_count": 0,
            },
        ),
        requirement(
            "P4",
            "All five rational frames satisfy the exact Pauli-axis algebra",
            algebra["checked"],
            {
                "checked": algebra["checked_frame_count"],
                "total": algebra["frame_count"],
            },
        ),
        requirement(
            "P5",
            "All 30 frozen single-frame rows execute",
            len(single_rows) == 30,
            {"actual": len(single_rows), "expected": 30},
        ),
        requirement(
            "P6",
            "All six frozen five-frame union rows execute",
            len(union_rows) == 6,
            {"actual": len(union_rows), "expected": 6},
        ),
        requirement(
            "P7",
            "Every frozen row uses an independent operator basis led by identity and H",
            all(
                row["identity_kernel_verified"]
                and row["hamiltonian_kernel_verified"]
                for row in rows
            ),
            {"row_count": len(rows)},
        ),
        requirement(
            "P8",
            "Every frozen row has exact nullity two under both declared primes",
            passed_rows == len(rows),
            {"passed": passed_rows, "total": len(rows)},
        ),
        requirement(
            "P9",
            "Tilted-frame and union J=0 controls recover extra exact charges",
            controls_passed == len(controls)
            and all(
                all(
                    nullity > 2
                    for nullity in row["modular_nullities"].values()
                )
                for row in controls
            )
            and all(
                row.get("onsite_tilted_charge_witnesses_checked") is True
                and row.get("onsite_tilted_charge_witness_count") == 8
                and row.get("onsite_tilted_charge_commutes_count") == 8
                and row.get("onsite_tilted_charge_in_span_count") == 8
                for row in controls
            ),
            {
                "passed": controls_passed,
                "total": len(controls),
                "nullities": [
                    row["modular_nullities"] for row in controls
                ],
                "onsite_witness_counts": [
                    {
                        "total": row.get(
                            "onsite_tilted_charge_witness_count"
                        ),
                        "commutes": row.get(
                            "onsite_tilted_charge_commutes_count"
                        ),
                        "in_span": row.get(
                            "onsite_tilted_charge_in_span_count"
                        ),
                    }
                    for row in controls
                ],
            },
        ),
        requirement(
            "P10",
            "Every frozen row carries operator and commutator digests",
            all(
                len(row["operator_basis_sha256"]) == 64
                and len(row["commutator_matrix_sha256"]) == 64
                for row in rows
            ),
            {"row_count": len(rows)},
        ),
        requirement(
            "P11",
            "Scientific promotion and new credit remain disabled",
            True,
            {
                "scientific_promotion_accepted": False,
                "new_credit_delta": 0,
            },
        ),
    ]
    requirements_passed = sum(item["passed"] for item in requirements)
    summary = {
        "frozen_row_count": len(rows),
        "single_frame_row_count": len(single_rows),
        "union_row_count": len(union_rows),
        "exact_nullity_two_row_count": passed_rows,
        "positive_control_row_count": len(controls),
        "positive_control_pass_count": controls_passed,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    payload_core = {
        "protocol_sha256": canonical_hash(protocol_payload),
        "public_freeze": freeze,
        "summary": summary,
        "rows": rows,
        "positive_control_rows": controls,
        "claim_boundary": {
            "supported": list(TRUE_CLAIMS),
            "not_supported": list(FALSE_CLAIMS),
            "remaining_escape_routes": [
                "arbitrary continuously rotated Jordan-Wigner frames",
                "nonlinear combinations of distinct fermionization frames",
                "interacting higher-than-quadratic Majorana charges",
                "Kramers-Wannier and other nonlocal dualities outside the declared frames",
                "size-dependent or adaptive nonlocal strings",
                "range-nine and longer quasi-local tails",
                "larger-size sparse-spectrum drift",
            ],
            "scientific_promotion_accepted": False,
            "new_credit_delta": 0,
        },
        "requirements": requirements,
    }
    payload_sha256 = canonical_hash(payload_core)
    accepted = bool(
        requirements_passed == len(requirements)
        and passed_rows == len(rows)
        and controls_passed == len(controls)
    )
    return {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "status": STATUS_ACCEPTED if accepted else STATUS_REJECTED,
        "requirements_passed": requirements_passed,
        "requirements_total": len(requirements),
        "protocol": protocol_payload,
        "protocol_sha256": payload_core["protocol_sha256"],
        "public_freeze": freeze,
        "summary": summary,
        "rows": rows,
        "positive_control_rows": controls,
        "claim_boundary": payload_core["claim_boundary"],
        "requirements": requirements,
        "payload_sha256": payload_sha256,
        "evidence": {
            "contract_path": str(CONTRACT_PATH),
            "contract_sha256": sha256_file(root / CONTRACT_PATH),
            "tool_path": "tools/b9_r197_nonstandard_fermionization_stress.py",
        },
    }


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    single_rows = [
        row for row in result["rows"] if len(row["frame_ids"]) == 1
    ]
    union_rows = [
        row
        for row in result["rows"]
        if len(row["frame_ids"]) == len(FRAME_ORDER)
    ]
    lines = [
        "# B9 R197 Nonstandard Fermionization Stress",
        "",
        "## Verdict",
        "",
        f"- Status: `{result['status']}`",
        (
            f"- Requirements: `{result['requirements_passed']}/"
            f"{result['requirements_total']}`"
        ),
        f"- Protocol hash: `{result['protocol_sha256']}`",
        f"- Payload hash: `{result['payload_sha256']}`",
        (
            "- Public preregistration commit: "
            f"`{result['public_freeze']['preregistration_commit']}`"
        ),
        "- Scientific promotion accepted: `false`",
        "- New credit delta: `0`",
        "",
        "## Heuristic Question",
        "",
        (
            "Can the apparent R196 nonintegrable candidate become a free "
            "fermion after changing the Jordan-Wigner parity axis?"
        ),
        "",
        "## Frozen Frame Sweep",
        "",
        (
            f"- Single-frame exact-nullity-two rows: "
            f"`{sum(row['exact_nullity_two_certified'] for row in single_rows)}/"
            f"{len(single_rows)}`."
        ),
        (
            f"- Five-frame union exact-nullity-two rows: "
            f"`{sum(row['exact_nullity_two_certified'] for row in union_rows)}/"
            f"{len(union_rows)}`."
        ),
        (
            "- Frames: standard `X`, `Y`, `Z`; tilted field-aligned "
            "`A=(-4X+3Z)/5`; and orthogonal tilted `B=(3X+4Z)/5`."
        ),
        (
            "- Each family contains all Majorana-linear operators, all "
            "quadratic Hermitian bilinears, full parity, identity, and H."
        ),
        "",
        "## Positive Control",
        "",
        (
            "- At `J=0,n=8`, tilted-A and all-frame union nullities are "
            f"`{[row['modular_nullities'] for row in result['positive_control_rows']]}`."
        ),
        "",
        "## Supported",
        "",
    ]
    lines.extend(
        f"- {claim}" for claim in result["claim_boundary"]["supported"]
    )
    lines.extend(["", "## Not Supported", ""])
    lines.extend(
        f"- {claim}"
        for claim in result["claim_boundary"]["not_supported"]
    )
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            (
                "Audit every row with an independent symplectic-bit "
                "implementation and a third prime. Then attack continuous "
                "frames, higher-than-quadratic Majorana charges, explicit "
                "Kramers-Wannier dualities, or range-nine adaptive tails."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def engineering_probe() -> dict[str, Any]:
    rows = [
        charge_row(6, ENGINEERING_COUPLING, (frame_id,))
        for frame_id in FRAME_ORDER
    ]
    rows.append(charge_row(6, ENGINEERING_COUPLING, FRAME_ORDER))
    controls = [
        charge_row(6, Fraction(0), ("tilted_a",)),
        charge_row(6, Fraction(0), FRAME_ORDER),
    ]
    return {
        "mode": "engineering_only",
        "coupling": fraction_text(ENGINEERING_COUPLING),
        "n": 6,
        "acceptance_count": 0,
        "frame_algebra": frame_algebra_checks(),
        "rows": rows,
        "positive_controls": controls,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--engineering-only", action="store_true")
    modes.add_argument("--execute-frozen-holdouts", action="store_true")
    parser.add_argument("--preregistration-commit", default="")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    if args.engineering_only:
        result = engineering_probe()
        output = json.dumps(
            result,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
        if args.json_output:
            args.json_output.write_text(output + "\n")
        else:
            print(output)
        return 0

    result = build_result(root, args.preregistration_commit)
    json_path = args.json_output or root / RESULT_PATH
    markdown_path = args.markdown_output or root / REPORT_PATH
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(
            result,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
        + "\n"
    )
    markdown_path.write_text(render_report(result))
    print(
        json.dumps(
            {
                "status": result["status"],
                "requirements": (
                    f"{result['requirements_passed']}/"
                    f"{result['requirements_total']}"
                ),
                "frozen_rows": result["summary"]["frozen_row_count"],
                "exact_nullity_two_rows": result["summary"][
                    "exact_nullity_two_row_count"
                ],
                "payload_sha256": result["payload_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["status"] == STATUS_ACCEPTED else 1


if __name__ == "__main__":
    raise SystemExit(main())
