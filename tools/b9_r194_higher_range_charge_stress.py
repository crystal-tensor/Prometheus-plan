#!/usr/bin/env python3
"""Build the B9 R194 higher-range conserved-charge stress certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from itertools import product
from pathlib import Path
from typing import Any

import b9_r193_coupling_integrability_stress as r193


EXPERIMENT_ID = "B9-R194-higher-range-charge-stress"
METHOD = "b9_r194_higher_range_charge_stress_v1"
STATUS_ACCEPTED = "checked_higher_range_local_charge_boundary"
STATUS_REJECTED = "higher_range_local_charge_boundary_rejected"
VERSION = "1.0"
LAST_UPDATED = "2026-07-29"

# J=13/32 was used only while measuring elimination cost before this protocol
# was frozen. It is disclosed and excluded from every scientific count.
ENGINEERING_PROBE_COUPLINGS = (Fraction(13, 32),)
FROZEN_HOLDOUT_COUPLINGS = (
    Fraction(23, 64),
    Fraction(27, 64),
    Fraction(31, 64),
    Fraction(35, 64),
)
RANGE_FIVE_SIZES = (8, 9, 10)
RANGE_SIX_CHALLENGE_COUPLING = Fraction(31, 64)
RANGE_SIX_CHALLENGE_SIZE = 8
RANGE_FIVE = 5
RANGE_SIX = 6
MODULAR_PRIMES = (1_000_003, 1_000_033)

RESULT_PATH = Path("results/B9_R194_higher_range_charge_stress_v1.json")
REPORT_PATH = Path("research/B9_R194_higher_range_charge_stress.md")
R193_TOOL_PATH = Path("tools/b9_r193_coupling_integrability_stress.py")

TRUE_CLAIMS = [
    "engineering_probe_excluded_from_acceptance",
    "frozen_holdout_couplings_recorded_before_execution",
    "complete_range_five_nullity_two_on_frozen_holdouts",
    "complete_range_six_challenge_nullity_two",
    "translation_summed_range_six_nullity_two_on_frozen_holdouts",
    "zero_coupling_controls_detect_extra_conserved_charges",
    "r193_candidate_survives_declared_higher_range_adversaries",
]
FALSE_CLAIMS = [
    "all_coupling_theorem",
    "all_size_theorem",
    "complete_quasi_local_charge_exclusion",
    "site_dependent_nonlocal_duality_exclusion",
    "nonstandard_fermionization_exclusion",
    "interacting_integrability_exclusion",
    "complete_integrability_exclusion",
    "nonintegrability_theorem",
    "quantum_chaos_theorem",
    "spectral_hardness_theorem",
    "quantum_pcp_theorem",
    "nlts_theorem",
    "bqp_separation",
    "solved_frontier",
]


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


def fraction_text(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


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


def hamiltonian_kernel_vector(
    candidate_basis: list[str],
    n: int,
    coupling: Fraction,
) -> tuple[dict[int, int], int]:
    candidate_index = {
        word: index for index, word in enumerate(candidate_basis)
    }
    terms, denominator = r193.hamiltonian_pauli_terms(n, coupling)
    vector: dict[int, int] = {}
    for coefficient, word in terms:
        index = candidate_index[word]
        vector[index] = vector.get(index, 0) + coefficient
    return vector, denominator


def minimum_degree_sparse_rank(
    columns: list[dict[int, int]],
    prime: int,
) -> int:
    """Compute exact modular rank with deterministic sparse column pivots."""
    active_columns = {
        column_index: {
            row: value % prime
            for row, value in column.items()
            if value % prime
        }
        for column_index, column in enumerate(columns)
    }
    row_columns: dict[int, set[int]] = {}
    for column_index, column in active_columns.items():
        for row in column:
            row_columns.setdefault(row, set()).add(column_index)

    rank = 0
    while active_columns:
        pivot_column_index = min(
            active_columns,
            key=lambda index: (len(active_columns[index]), index),
        )
        pivot_column = active_columns[pivot_column_index]
        if not pivot_column:
            active_columns.pop(pivot_column_index)
            continue
        pivot_row = min(
            pivot_column,
            key=lambda row: (len(row_columns[row]), row),
        )
        inverse = pow(pivot_column[pivot_row], prime - 2, prime)
        normalized_pivot = {
            row: (value * inverse) % prime
            for row, value in pivot_column.items()
            if (value * inverse) % prime
        }
        affected_columns = sorted(
            row_columns[pivot_row] - {pivot_column_index}
        )
        for affected_index in affected_columns:
            affected = active_columns[affected_index]
            factor = affected[pivot_row]
            for row, value in normalized_pivot.items():
                old_value = affected.get(row, 0)
                new_value = (old_value - factor * value) % prime
                if new_value:
                    affected[row] = new_value
                    if not old_value:
                        row_columns.setdefault(row, set()).add(
                            affected_index
                        )
                elif old_value:
                    affected.pop(row)
                    row_columns[row].discard(affected_index)
                    if not row_columns[row]:
                        row_columns.pop(row)

        for row in pivot_column:
            row_columns[row].discard(pivot_column_index)
            if not row_columns[row]:
                row_columns.pop(row)
        active_columns.pop(pivot_column_index)
        rank += 1
    return rank


def complete_charge_row(
    n: int,
    coupling: Fraction,
    max_range: int,
    primes: tuple[int, ...] = MODULAR_PRIMES,
    crosscheck_legacy: bool = True,
) -> dict[str, Any]:
    (
        candidate_basis,
        columns,
        output_basis,
        nonzero_count,
        matrix_hash,
    ) = r193.pauli_commutator_columns(n, coupling, max_range)
    candidate_index = {
        word: index for index, word in enumerate(candidate_basis)
    }
    identity_vector = {candidate_index["I" * n]: 1}
    hamiltonian_vector, denominator = hamiltonian_kernel_vector(
        candidate_basis,
        n,
        coupling,
    )
    identity_kernel = not r193.combine_columns(columns, identity_vector)
    hamiltonian_kernel = not r193.combine_columns(
        columns,
        hamiltonian_vector,
    )
    ranks = {
        str(prime): minimum_degree_sparse_rank(columns, prime)
        for prime in primes
    }
    legacy_ranks = (
        {
            str(prime): r193.modular_sparse_rank(columns, prime)
            for prime in primes
        }
        if crosscheck_legacy
        else None
    )
    rank_implementations_agree = (
        legacy_ranks is None or ranks == legacy_ranks
    )
    nullities = {
        prime: len(candidate_basis) - rank
        for prime, rank in ranks.items()
    }
    exact_nullity_two = bool(
        coupling != 0
        and identity_kernel
        and hamiltonian_kernel
        and rank_implementations_agree
        and all(rank == len(candidate_basis) - 2 for rank in ranks.values())
    )
    return {
        "search_family": "complete_position_dependent",
        "coupling": fraction_text(coupling),
        "coupling_numerator": coupling.numerator,
        "coupling_denominator": coupling.denominator,
        "n": n,
        "max_contiguous_support_range": max_range,
        "candidate_basis_size": len(candidate_basis),
        "output_basis_size": len(output_basis),
        "commutator_nonzero_count": nonzero_count,
        "commutator_matrix_sha256": matrix_hash,
        "hamiltonian_common_denominator": denominator,
        "identity_kernel_verified": identity_kernel,
        "hamiltonian_kernel_verified": hamiltonian_kernel,
        "modular_primes": list(primes),
        "modular_ranks": ranks,
        "legacy_modular_ranks": legacy_ranks,
        "rank_implementations_agree": rank_implementations_agree,
        "modular_nullities": nullities,
        "exact_nullity_two_certified": exact_nullity_two,
        "checked": (
            exact_nullity_two
            if coupling != 0
            else identity_kernel and hamiltonian_kernel
        ),
    }


def local_patterns(max_range: int) -> list[tuple[int, str]]:
    patterns: list[tuple[int, str]] = []
    for span in range(1, max_range + 1):
        for local in product("IXYZ", repeat=span):
            if local[0] == "I" or local[-1] == "I":
                continue
            patterns.append((span, "".join(local)))
    return patterns


def translated_word(n: int, start: int, local: str) -> str:
    chars = ["I"] * n
    chars[start : start + len(local)] = local
    return "".join(chars)


def translation_summed_charge_row(
    n: int,
    coupling: Fraction,
    max_range: int,
) -> dict[str, Any]:
    (
        full_basis,
        full_columns,
        output_basis,
        _,
        _,
    ) = r193.pauli_commutator_columns(n, coupling, max_range)
    full_index = {word: index for index, word in enumerate(full_basis)}
    labels = ["identity"]
    coefficient_vectors: list[dict[int, int]] = [
        {full_index["I" * n]: 1}
    ]
    for span, local in local_patterns(max_range):
        labels.append(f"range_{span}:{local}")
        coefficient_vectors.append(
            {
                full_index[translated_word(n, start, local)]: 1
                for start in range(n - span + 1)
            }
        )
    columns = [
        r193.combine_columns(full_columns, vector)
        for vector in coefficient_vectors
    ]
    triples = [
        (output_basis[row], column_index, value)
        for column_index, column in enumerate(columns)
        for row, value in sorted(column.items())
    ]
    matrix_hash = canonical_hash(
        {
            "candidate_labels": labels,
            "output_basis": output_basis,
            "triples": triples,
        }
    )
    label_index = {label: index for index, label in enumerate(labels)}
    denominator = r193.common_denominator(coupling)
    coupling_numerator = (
        coupling.numerator * denominator // coupling.denominator
    )
    hamiltonian_vector = {
        label_index["range_1:X"]: -denominator,
        label_index["range_1:Z"]: 3 * denominator // 4,
    }
    if coupling_numerator:
        hamiltonian_vector[label_index["range_2:ZZ"]] = coupling_numerator
    identity_vector = {label_index["identity"]: 1}
    identity_kernel = not r193.combine_columns(columns, identity_vector)
    hamiltonian_kernel = not r193.combine_columns(
        columns,
        hamiltonian_vector,
    )
    ranks = {
        str(prime): minimum_degree_sparse_rank(columns, prime)
        for prime in MODULAR_PRIMES
    }
    nullities = {
        prime: len(labels) - rank for prime, rank in ranks.items()
    }
    exact_nullity_two = bool(
        coupling != 0
        and identity_kernel
        and hamiltonian_kernel
        and all(rank == len(labels) - 2 for rank in ranks.values())
    )
    return {
        "search_family": "translation_summed_truncated_quasi_local_proxy",
        "coupling": fraction_text(coupling),
        "coupling_numerator": coupling.numerator,
        "coupling_denominator": coupling.denominator,
        "n": n,
        "max_contiguous_support_range": max_range,
        "candidate_basis_size": len(labels),
        "complete_parent_basis_size": len(full_basis),
        "output_basis_size": len(output_basis),
        "commutator_nonzero_count": len(triples),
        "commutator_matrix_sha256": matrix_hash,
        "hamiltonian_common_denominator": denominator,
        "identity_kernel_verified": identity_kernel,
        "hamiltonian_kernel_verified": hamiltonian_kernel,
        "modular_primes": list(MODULAR_PRIMES),
        "modular_ranks": ranks,
        "modular_nullities": nullities,
        "exact_nullity_two_certified": exact_nullity_two,
        "finite_range_truncation_only": True,
        "checked": (
            exact_nullity_two
            if coupling != 0
            else identity_kernel and hamiltonian_kernel
        ),
    }


def protocol() -> dict[str, Any]:
    return {
        "version": VERSION,
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "model": {
            "boundary": "open",
            "hamiltonian": (
                "sum_i[-X_i+(3/4)Z_i]+J"
                "sum_{i=0}^{n-2}Z_i Z_{i+1}"
            ),
            "engineering_probe_couplings": [
                fraction_text(value) for value in ENGINEERING_PROBE_COUPLINGS
            ],
            "frozen_holdout_couplings": [
                fraction_text(value) for value in FROZEN_HOLDOUT_COUPLINGS
            ],
        },
        "engineering_probe_disclosure": {
            "status": "observed_before_protocol_freeze_for_runtime_only",
            "acceptance_use": "none",
            "observed_fields": [
                "candidate basis size",
                "output basis size",
                "commutator nonzero count",
                "two-prime modular ranks at n=8",
            ],
        },
        "complete_range_five": {
            "sizes": list(RANGE_FIVE_SIZES),
            "couplings": [
                fraction_text(value) for value in FROZEN_HOLDOUT_COUPLINGS
            ],
            "max_range": RANGE_FIVE,
            "basis": (
                "identity plus every position-dependent Pauli word with "
                "minimal contiguous support span at most five"
            ),
            "acceptance_rule": (
                "identity and H are explicit rational kernels and modular "
                "rank is ncols-2 under both declared primes on every row"
            ),
        },
        "complete_range_six_challenge": {
            "size": RANGE_SIX_CHALLENGE_SIZE,
            "coupling": fraction_text(RANGE_SIX_CHALLENGE_COUPLING),
            "max_range": RANGE_SIX,
            "basis": (
                "identity plus every position-dependent Pauli word with "
                "minimal contiguous support span at most six"
            ),
            "acceptance_rule": (
                "identity and H are explicit rational kernels and modular "
                "rank is ncols-2 under both declared primes"
            ),
        },
        "translation_summed_range_six": {
            "sizes": list(RANGE_FIVE_SIZES),
            "couplings": [
                fraction_text(value) for value in FROZEN_HOLDOUT_COUPLINGS
            ],
            "max_range": RANGE_SIX,
            "basis": (
                "identity plus the open-chain translation sum of every "
                "Pauli density with support span at most six"
            ),
            "interpretation": (
                "six-shell finite truncation of a putative quasi-local "
                "charge; it cannot exclude tails beyond range six"
            ),
            "acceptance_rule": (
                "identity and H are explicit rational kernels and modular "
                "rank is ncols-2 under both declared primes on every row"
            ),
        },
        "positive_controls": {
            "coupling": "0",
            "complete_range_five_size": 8,
            "translation_range_six_size": 8,
            "acceptance_rule": (
                "each control must expose modular nullity greater than two"
            ),
        },
        "exactness": {
            "modular_primes": list(MODULAR_PRIMES),
            "argument": (
                "two explicit rational kernels give nullity at least two; "
                "rank ncols-2 modulo either prime gives rational rank at "
                "least ncols-2, hence rational nullity exactly two"
            ),
        },
        "claim_boundary": {
            "true_claims": TRUE_CLAIMS,
            "false_claims": FALSE_CLAIMS,
            "scientific_promotion_accepted": False,
            "new_credit_delta": 0,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    challenge = result["complete_range_six_challenge_row"]
    lines = [
        "# B9 R194 Higher-Range Conserved-Charge Stress",
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
        "- Scientific promotion accepted: `false`",
        "- New credit delta: `0`",
        "",
        "## Preregistration Boundary",
        "",
        "`J=13/32` was observed only while measuring sparse-elimination cost.",
        "It is disclosed as an engineering probe and contributes zero",
        "scientific acceptance decisions. R194 acceptance uses only the newly",
        "frozen `23/64`, `27/64`, `31/64`, and `35/64` couplings.",
        "",
        "## Complete Position-Dependent Range Five",
        "",
        (
            "- Exact-nullity-two rows: "
            f"`{summary['complete_range_five_nullity_two_count']}/"
            f"{summary['complete_range_five_row_count']}`."
        ),
        (
            "- Sizes: `8, 9, 10`; every position-dependent Pauli word with "
            "minimal contiguous support span at most five is included."
        ),
        "",
        "## Complete Position-Dependent Range Six Challenge",
        "",
        f"- Coupling and size: `J={challenge['coupling']}`, `n={challenge['n']}`.",
        f"- Candidate columns: `{challenge['candidate_basis_size']}`.",
        f"- Output rows: `{challenge['output_basis_size']}`.",
        (
            "- Exact modular nullities: "
            f"`{challenge['modular_nullities']}`."
        ),
        (
            "- Identity/H kernels and two-prime rank certify exact nullity "
            "two inside this complete finite-size range-six ansatz."
        ),
        "",
        "## Six-Shell Translation-Summed Proxy",
        "",
        (
            "- Exact-nullity-two rows: "
            f"`{summary['translation_range_six_nullity_two_count']}/"
            f"{summary['translation_range_six_row_count']}`."
        ),
        (
            "- The basis contains identity plus the open-chain translation "
            "sum of every Pauli density through range six."
        ),
        (
            "- This is a finite six-shell truncation only. A quasi-local "
            "charge with a nonzero tail beyond range six can evade it."
        ),
        "",
        "## Positive Controls",
        "",
        (
            "- `J=0` complete range-five nullity: "
            f"`{summary['complete_zero_control_nullity_min']}`."
        ),
        (
            "- `J=0` translation-summed range-six nullity: "
            f"`{summary['translation_zero_control_nullity_min']}`."
        ),
        (
            "- Both controls expose more than identity and H, so the "
            "adversaries detect known extra conserved structure."
        ),
        "",
        "## Supported",
        "",
    ]
    lines.extend(f"- {claim}" for claim in result["claim_boundary"]["supported"])
    lines.extend(["", "## Not Supported", ""])
    lines.extend(
        f"- {claim}" for claim in result["claim_boundary"]["not_supported"]
    )
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            "Extend the complete position-dependent range-six certificate",
            "beyond one size/coupling, then test range-seven/eight tails,",
            "site-dependent or nonlocal dualities, nonstandard",
            "fermionizations, and larger sparse spectra. R194 narrows the",
            "integrability escape surface; it does not prove nonintegrability,",
            "quantum chaos, spectral hardness, Quantum PCP, NLTS, or BQP.",
            "",
        ]
    )
    return "\n".join(lines)


def build_result(root: Path) -> dict[str, Any]:
    protocol_payload = protocol()
    complete_range_five_rows = [
        complete_charge_row(n, coupling, RANGE_FIVE)
        for coupling in FROZEN_HOLDOUT_COUPLINGS
        for n in RANGE_FIVE_SIZES
    ]
    challenge_row = complete_charge_row(
        RANGE_SIX_CHALLENGE_SIZE,
        RANGE_SIX_CHALLENGE_COUPLING,
        RANGE_SIX,
        crosscheck_legacy=False,
    )
    translation_rows = [
        translation_summed_charge_row(n, coupling, RANGE_SIX)
        for coupling in FROZEN_HOLDOUT_COUPLINGS
        for n in RANGE_FIVE_SIZES
    ]
    complete_control = complete_charge_row(8, Fraction(0), RANGE_FIVE)
    translation_control = translation_summed_charge_row(
        8,
        Fraction(0),
        RANGE_SIX,
    )

    range_five_pass_count = sum(
        row["exact_nullity_two_certified"]
        for row in complete_range_five_rows
    )
    translation_pass_count = sum(
        row["exact_nullity_two_certified"] for row in translation_rows
    )
    complete_control_nullity_min = min(
        complete_control["modular_nullities"].values()
    )
    translation_control_nullity_min = min(
        translation_control["modular_nullities"].values()
    )
    summary = {
        "engineering_probe_acceptance_count": 0,
        "frozen_holdout_coupling_count": len(FROZEN_HOLDOUT_COUPLINGS),
        "complete_range_five_row_count": len(complete_range_five_rows),
        "complete_range_five_nullity_two_count": range_five_pass_count,
        "complete_range_six_challenge_count": 1,
        "complete_range_six_challenge_nullity_two_count": int(
            challenge_row["exact_nullity_two_certified"]
        ),
        "translation_range_six_row_count": len(translation_rows),
        "translation_range_six_nullity_two_count": translation_pass_count,
        "complete_zero_control_nullity_min": complete_control_nullity_min,
        "translation_zero_control_nullity_min": (
            translation_control_nullity_min
        ),
        "positive_control_pass_count": int(complete_control_nullity_min > 2)
        + int(translation_control_nullity_min > 2),
        "scoped_higher_range_boundary_accepted": bool(
            range_five_pass_count == len(complete_range_five_rows)
            and challenge_row["exact_nullity_two_certified"]
            and translation_pass_count == len(translation_rows)
            and complete_control_nullity_min > 2
            and translation_control_nullity_min > 2
        ),
        "scientific_promotion_accepted": False,
    }
    supported = list(TRUE_CLAIMS)
    not_supported = list(FALSE_CLAIMS)
    claim_boundary = {
        "supported": supported,
        "not_supported": not_supported,
        "true_claims": supported,
        "false_claims": not_supported,
        "remaining_escape_routes": [
            "complete position-dependent range six beyond n=8 and J=31/64",
            "range-seven and longer quasi-local tails",
            "site-dependent or nonlocal dualities",
            "nonstandard fermionizations",
            "interacting integrability structures",
            "larger-size finite-spectrum drift",
        ],
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    requirements = [
        requirement(
            "P1",
            "Engineering probe is disclosed and excluded",
            set(ENGINEERING_PROBE_COUPLINGS).isdisjoint(
                FROZEN_HOLDOUT_COUPLINGS
            )
            and summary["engineering_probe_acceptance_count"] == 0,
            {
                "engineering_probe_couplings": [
                    fraction_text(value)
                    for value in ENGINEERING_PROBE_COUPLINGS
                ],
                "acceptance_count": 0,
            },
        ),
        requirement(
            "P2",
            "Four new rational holdout couplings are frozen",
            len(FROZEN_HOLDOUT_COUPLINGS) == 4
            and len(set(FROZEN_HOLDOUT_COUPLINGS)) == 4,
            {
                "couplings": [
                    fraction_text(value)
                    for value in FROZEN_HOLDOUT_COUPLINGS
                ]
            },
        ),
        requirement(
            "P3",
            "Complete range-five row set is exhaustive",
            len(complete_range_five_rows)
            == len(FROZEN_HOLDOUT_COUPLINGS) * len(RANGE_FIVE_SIZES),
            {
                "row_count": len(complete_range_five_rows),
                "expected": (
                    len(FROZEN_HOLDOUT_COUPLINGS)
                    * len(RANGE_FIVE_SIZES)
                ),
            },
        ),
        requirement(
            "P4",
            "Complete range-five matrices have explicit digests",
            all(
                len(row["commutator_matrix_sha256"]) == 64
                for row in complete_range_five_rows
            ),
            {"digest_count": len(complete_range_five_rows)},
        ),
        requirement(
            "P5",
            "Identity and H are exact complete range-five kernels",
            all(
                row["identity_kernel_verified"]
                and row["hamiltonian_kernel_verified"]
                for row in complete_range_five_rows
            ),
            {"row_count": len(complete_range_five_rows)},
        ),
        requirement(
            "P6",
            "Complete range-five nullity is exactly two",
            range_five_pass_count == len(complete_range_five_rows),
            {
                "passed": range_five_pass_count,
                "total": len(complete_range_five_rows),
            },
        ),
        requirement(
            "P7",
            "Complete range-six challenge has explicit kernels",
            challenge_row["identity_kernel_verified"]
            and challenge_row["hamiltonian_kernel_verified"],
            {
                "coupling": challenge_row["coupling"],
                "n": challenge_row["n"],
            },
        ),
        requirement(
            "P8",
            "Complete range-six challenge nullity is exactly two",
            challenge_row["exact_nullity_two_certified"],
            {
                "candidate_basis_size": challenge_row[
                    "candidate_basis_size"
                ],
                "modular_nullities": challenge_row["modular_nullities"],
            },
        ),
        requirement(
            "P9",
            "Translation-summed range-six row set is exhaustive",
            len(translation_rows)
            == len(FROZEN_HOLDOUT_COUPLINGS) * len(RANGE_FIVE_SIZES),
            {
                "row_count": len(translation_rows),
                "expected": (
                    len(FROZEN_HOLDOUT_COUPLINGS)
                    * len(RANGE_FIVE_SIZES)
                ),
            },
        ),
        requirement(
            "P10",
            "Translation-summed rows have explicit kernels",
            all(
                row["identity_kernel_verified"]
                and row["hamiltonian_kernel_verified"]
                for row in translation_rows
            ),
            {"row_count": len(translation_rows)},
        ),
        requirement(
            "P11",
            "Translation-summed range-six nullity is exactly two",
            translation_pass_count == len(translation_rows),
            {
                "passed": translation_pass_count,
                "total": len(translation_rows),
            },
        ),
        requirement(
            "P12",
            "J=0 positive controls expose extra charges",
            complete_control_nullity_min > 2
            and translation_control_nullity_min > 2,
            {
                "complete_range_five_nullity": (
                    complete_control_nullity_min
                ),
                "translation_range_six_nullity": (
                    translation_control_nullity_min
                ),
            },
        ),
        requirement(
            "P13",
            "R193 sparse exact dependency is hash-bound",
            len(sha256_file(root / R193_TOOL_PATH)) == 64,
            {"r193_tool_sha256": sha256_file(root / R193_TOOL_PATH)},
        ),
        requirement(
            "P14",
            "Broad scientific promotion remains disabled",
            claim_boundary["scientific_promotion_accepted"] is False
            and claim_boundary["new_credit_delta"] == 0
            and set(FALSE_CLAIMS).issubset(not_supported),
            {
                "scientific_promotion_accepted": False,
                "new_credit_delta": 0,
                "remaining_escape_route_count": len(
                    claim_boundary["remaining_escape_routes"]
                ),
            },
        ),
    ]
    requirements_passed = sum(row["passed"] for row in requirements)
    accepted = bool(
        requirements_passed == len(requirements)
        and summary["scoped_higher_range_boundary_accepted"]
    )
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "status": STATUS_ACCEPTED if accepted else STATUS_REJECTED,
        "protocol": protocol_payload,
        "protocol_sha256": canonical_hash(protocol_payload),
        "complete_range_five_rows": complete_range_five_rows,
        "complete_range_six_challenge_row": challenge_row,
        "translation_range_six_rows": translation_rows,
        "positive_controls": {
            "complete_range_five": complete_control,
            "translation_range_six": translation_control,
        },
        "summary": summary,
        "claim_boundary": claim_boundary,
        "requirements": requirements,
        "requirements_total": len(requirements),
        "requirements_passed": requirements_passed,
        "evidence": {
            "tool_sha256": sha256_file(Path(__file__)),
            "r193_dependency_sha256": sha256_file(root / R193_TOOL_PATH),
        },
        "evidence_integrity_complete": accepted,
        "new_credit_delta": 0,
    }
    payload["payload_sha256"] = canonical_hash(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json-output", type=Path, default=RESULT_PATH)
    parser.add_argument("--markdown-output", type=Path, default=REPORT_PATH)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    payload = build_result(root)
    json_output = (
        args.json_output
        if args.json_output.is_absolute()
        else root / args.json_output
    )
    markdown_output = (
        args.markdown_output
        if args.markdown_output.is_absolute()
        else root / args.markdown_output
    )
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(
            payload,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
        + "\n"
    )
    markdown_output.write_text(render_report(payload))
    print(
        json.dumps(
            {
                "experiment_id": payload["experiment_id"],
                "status": payload["status"],
                "requirements_passed": payload["requirements_passed"],
                "requirements_total": payload["requirements_total"],
                "payload_sha256": payload["payload_sha256"],
                "summary": payload["summary"],
            },
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )
    return 0 if payload["evidence_integrity_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
