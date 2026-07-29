#!/usr/bin/env python3
"""Build the B9 R193 coupling-sweep and integrability-stress certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from fractions import Fraction
from itertools import product
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np


EXPERIMENT_ID = "B9-R193-coupling-integrability-stress"
METHOD = "b9_r193_coupling_integrability_stress_v1"
STATUS_ACCEPTED = "checked_holdout_spectral_crossover_candidate"
STATUS_REJECTED = "holdout_spectral_crossover_candidate_rejected"
VERSION = "1.0"
LAST_UPDATED = "2026-07-29"
CHECKED_SIZES = tuple(range(6, 11))
TAIL_SIZES = (8, 9, 10)
PILOT_COUPLINGS = (
    Fraction(0),
    Fraction(1, 8),
    Fraction(1, 4),
    Fraction(3, 8),
    Fraction(1, 2),
    Fraction(5, 8),
    Fraction(3, 4),
    Fraction(1),
)
HOLDOUT_COUPLINGS = (
    Fraction(3, 16),
    Fraction(5, 16),
    Fraction(7, 16),
    Fraction(9, 16),
    Fraction(11, 16),
    Fraction(7, 8),
)
WEAK_HOLDOUT_COUPLINGS = (Fraction(3, 16),)
TRANSITION_HOLDOUT_COUPLINGS = (Fraction(5, 16),)
STRONG_HOLDOUT_COUPLINGS = (
    Fraction(7, 16),
    Fraction(9, 16),
    Fraction(11, 16),
    Fraction(7, 8),
)
FIELD = Fraction(3, 4)
MATRIX_TOLERANCE = 1e-12
SPECTRUM_TOLERANCE = 1e-10
SYMMETRY_TOLERANCE = 1e-12
CENTRAL_TRIM_FRACTION = 0.10
LOCAL_CHARGE_MAX_RANGE = 4
MODULAR_PRIMES = (1_000_003, 1_000_033)
POISSON_REFERENCE = 2.0 * math.log(2.0) - 1.0
GOE_REFERENCE = 0.5307
MODULE_PATH = Path("B9/ClusterStabilizer/FreeFermionObstruction.lean")
RESULT_PATH = Path("results/B9_R193_coupling_integrability_stress_v1.json")
REPORT_PATH = Path("research/B9_R193_coupling_integrability_stress.md")
TRANSCRIPT_PATH = Path(
    "results/B9_R193_free_fermion_obstruction_transcript_v1.txt"
)
TRUE_CLAIMS = [
    "pilot_holdout_split_recorded",
    "independent_exact_matrix_replay_complete",
    "reflection_symmetry_resolved",
    "nonzero_holdout_spectra_simple",
    "range_four_local_charge_kernel_reduced_to_identity_and_hamiltonian",
    "zero_coupling_control_has_extensive_local_charges",
    "standard_jw_axis_obstruction_formalized",
    "weak_to_strong_level_statistic_crossover_candidate",
    "normalized_gap_not_improved_on_holdout",
]
FALSE_CLAIMS = [
    "all_n_spectrum_theorem",
    "complete_integrability_exclusion",
    "site_dependent_nonlocal_duality_exclusion",
    "nonintegrability_theorem",
    "quantum_chaos_theorem",
    "spectral_hardness_theorem",
    "quantum_hardware_execution",
    "quantum_pcp_theorem",
    "nlts_theorem",
    "bqp_separation",
    "solved_frontier",
]
REQUIRED_DEFINITIONS = [
    "SpinVector",
    "spinDot",
    "tiltedFieldVector",
    "isingCouplingAxis",
    "standardJWQuadraticAxisCondition",
    "fieldCouplingSquaredAlignment",
]
REQUIRED_THEOREMS = [
    "tilted_field_dot_ising_axis",
    "tilted_field_norm_squared",
    "ising_axis_norm_squared",
    "field_coupling_squared_alignment",
    "dot_preserving_map_keeps_field_coupling_overlap",
    "no_dot_preserving_rotation_satisfies_standard_jw_condition",
    "standard_jw_rotation_obstruction_boundary",
]

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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hash(payload: Any) -> str:
    return sha256_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def fraction_text(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def coupling_id(value: Fraction) -> str:
    return f"j_{value.numerator}_{value.denominator}"


def scrub_home(value: str) -> str:
    return value.replace(str(Path.home()), "~")


def resolve_executable(name: str) -> str:
    elan_candidate = Path.home() / ".elan" / "bin" / name
    if elan_candidate.exists():
        return str(elan_candidate)
    return shutil.which(name) or name


def run_command(
    command: list[str],
    display_command: list[str],
    cwd: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return {
            "command": display_command,
            "returncode": completed.returncode,
            "timed_out": False,
            "stdout": scrub_home(completed.stdout),
            "stderr": scrub_home(completed.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return {
            "command": display_command,
            "returncode": None,
            "timed_out": True,
            "stdout": scrub_home(stdout),
            "stderr": scrub_home(stderr),
        }


def render_transcript(probes: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for probe in probes:
        blocks.extend(
            [
                f"COMMAND: {' '.join(probe['command'])}",
                f"RETURNCODE: {probe['returncode']}",
                f"TIMED_OUT: {str(probe['timed_out']).lower()}",
                "STDOUT:",
                probe["stdout"].rstrip(),
                "STDERR:",
                probe["stderr"].rstrip(),
                "END_COMMAND",
                "",
            ]
        )
    return "\n".join(blocks)


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


def kron_word(n: int, operators: dict[int, np.ndarray]) -> np.ndarray:
    identity = np.eye(2, dtype=np.int64)
    result = np.array([[1]], dtype=np.int64)
    for site in reversed(range(n)):
        result = np.kron(result, operators.get(site, identity))
    return result


def common_denominator(coupling: Fraction) -> int:
    return math.lcm(4, coupling.denominator)


def build_bit_action_numerator(
    n: int,
    coupling: Fraction,
) -> tuple[np.ndarray, int]:
    denominator = common_denominator(coupling)
    field_numerator = FIELD.numerator * denominator // FIELD.denominator
    coupling_numerator = (
        coupling.numerator * denominator // coupling.denominator
    )
    dimension = 1 << n
    matrix = np.zeros((dimension, dimension), dtype=np.int64)
    for state in range(dimension):
        z = [1 - 2 * ((state >> site) & 1) for site in range(n)]
        matrix[state, state] += (
            field_numerator * sum(z)
            + coupling_numerator
            * sum(z[site] * z[site + 1] for site in range(n - 1))
        )
        for site in range(n):
            matrix[state ^ (1 << site), state] -= denominator
    return matrix, denominator


def build_kron_numerator(
    n: int,
    coupling: Fraction,
) -> tuple[np.ndarray, int]:
    denominator = common_denominator(coupling)
    field_numerator = FIELD.numerator * denominator // FIELD.denominator
    coupling_numerator = (
        coupling.numerator * denominator // coupling.denominator
    )
    pauli_x = np.array([[0, 1], [1, 0]], dtype=np.int64)
    pauli_z = np.array([[1, 0], [0, -1]], dtype=np.int64)
    dimension = 1 << n
    matrix = np.zeros((dimension, dimension), dtype=np.int64)
    for site in range(n):
        matrix -= denominator * kron_word(n, {site: pauli_x})
        matrix += field_numerator * kron_word(n, {site: pauli_z})
    for site in range(n - 1):
        matrix += coupling_numerator * kron_word(
            n,
            {site: pauli_z, site + 1: pauli_z},
        )
    return matrix, denominator


def matrix_digest(matrix: np.ndarray, denominator: int) -> str:
    return sha256_bytes(
        denominator.to_bytes(8, byteorder="little", signed=False)
        + matrix.astype("<i8", copy=False).tobytes()
    )


def reflected_state(state: int, n: int) -> int:
    reflected = 0
    for site in range(n):
        reflected |= ((state >> site) & 1) << (n - 1 - site)
    return reflected


def reflection_permutation(n: int) -> np.ndarray:
    dimension = 1 << n
    matrix = np.zeros((dimension, dimension), dtype=np.int64)
    for state in range(dimension):
        matrix[reflected_state(state, n), state] = 1
    return matrix


def reflection_parity_basis(n: int, parity: int) -> np.ndarray:
    dimension = 1 << n
    seen: set[int] = set()
    columns: list[np.ndarray] = []
    for state in range(dimension):
        if state in seen:
            continue
        reflected = reflected_state(state, n)
        seen.add(state)
        seen.add(reflected)
        if state == reflected:
            if parity == 1:
                vector = np.zeros(dimension)
                vector[state] = 1.0
                columns.append(vector)
            continue
        low, high = sorted((state, reflected))
        vector = np.zeros(dimension)
        vector[low] = 1.0 / math.sqrt(2.0)
        vector[high] = parity / math.sqrt(2.0)
        columns.append(vector)
    return np.stack(columns, axis=1)


def central_gap_ratio(eigenvalues: np.ndarray) -> dict[str, Any]:
    ordered = np.sort(eigenvalues)
    trim = int(len(ordered) * CENTRAL_TRIM_FRACTION)
    central = ordered[trim : len(ordered) - trim]
    gaps = np.diff(central)
    if np.any(gaps <= SPECTRUM_TOLERANCE):
        return {
            "trim_fraction": CENTRAL_TRIM_FRACTION,
            "retained_eigenvalue_count": int(len(central)),
            "ratio_count": 0,
            "mean_adjacent_gap_ratio": None,
            "minimum_central_spacing": float(np.min(gaps)),
            "contains_degeneracy": True,
        }
    ratios = np.minimum(gaps[:-1], gaps[1:]) / np.maximum(
        gaps[:-1],
        gaps[1:],
    )
    return {
        "trim_fraction": CENTRAL_TRIM_FRACTION,
        "retained_eigenvalue_count": int(len(central)),
        "ratio_count": int(len(ratios)),
        "mean_adjacent_gap_ratio": float(np.mean(ratios)),
        "minimum_central_spacing": float(np.min(gaps)),
        "contains_degeneracy": False,
    }


def spectrum_row(
    n: int,
    coupling: Fraction,
    phase: str,
) -> dict[str, Any]:
    bit_numerator, denominator = build_bit_action_numerator(n, coupling)
    kron_numerator, kron_denominator = build_kron_numerator(n, coupling)
    exact_matrix_match = (
        denominator == kron_denominator
        and np.array_equal(bit_numerator, kron_numerator)
    )
    matrix = bit_numerator.astype(np.float64) / denominator
    hermitian_residual = float(np.max(np.abs(matrix - matrix.T)))

    reflection = reflection_permutation(n)
    reflection_commutator = bit_numerator @ reflection - reflection @ bit_numerator
    reflection_commutator_max_abs = int(np.max(np.abs(reflection_commutator)))

    even_basis = reflection_parity_basis(n, 1)
    odd_basis = reflection_parity_basis(n, -1)
    parity_orthogonality_residual = max(
        float(
            np.max(
                np.abs(
                    even_basis.T @ even_basis
                    - np.eye(even_basis.shape[1])
                )
            )
        ),
        float(
            np.max(
                np.abs(
                    odd_basis.T @ odd_basis
                    - np.eye(odd_basis.shape[1])
                )
            )
        ),
    )
    parity_cross_residual = float(np.max(np.abs(even_basis.T @ odd_basis)))
    parity_block_off_diagonal_residual = float(
        np.max(np.abs(even_basis.T @ matrix @ odd_basis))
    )

    eigenvalues = np.linalg.eigvalsh(matrix)
    even_eigenvalues = np.linalg.eigvalsh(even_basis.T @ matrix @ even_basis)
    odd_eigenvalues = np.linalg.eigvalsh(odd_basis.T @ matrix @ odd_basis)
    parity_reassembled = np.sort(
        np.concatenate((even_eigenvalues, odd_eigenvalues))
    )
    parity_spectrum_max_abs_error = float(
        np.max(np.abs(eigenvalues - parity_reassembled))
    )

    gaps = np.diff(eigenvalues)
    ground_energy = float(eigenvalues[0])
    first_excited_energy = float(eigenvalues[1])
    top_energy = float(eigenvalues[-1])
    gap = first_excited_energy - ground_energy
    width = top_energy - ground_energy
    normalized_gap = gap / width
    normalized_gap_ratio = normalized_gap / (1.0 / n)
    distinct_level_count = int(
        1 + np.count_nonzero(gaps > SPECTRUM_TOLERANCE)
    )

    return {
        "phase": phase,
        "coupling": fraction_text(coupling),
        "coupling_numerator": coupling.numerator,
        "coupling_denominator": coupling.denominator,
        "n": n,
        "dimension": 1 << n,
        "matrix_common_denominator": denominator,
        "matrix_sha256": matrix_digest(bit_numerator, denominator),
        "independent_matrix_sha256": matrix_digest(
            kron_numerator,
            kron_denominator,
        ),
        "exact_integer_matrix_match": exact_matrix_match,
        "matrix_max_abs_difference": int(
            np.max(np.abs(bit_numerator - kron_numerator))
        ),
        "hermitian_residual": hermitian_residual,
        "reflection_commutator_max_abs_exact": reflection_commutator_max_abs,
        "even_sector_dimension": int(even_basis.shape[1]),
        "odd_sector_dimension": int(odd_basis.shape[1]),
        "parity_orthogonality_residual": parity_orthogonality_residual,
        "parity_cross_residual": parity_cross_residual,
        "parity_block_off_diagonal_residual": parity_block_off_diagonal_residual,
        "parity_spectrum_max_abs_error": parity_spectrum_max_abs_error,
        "ground_energy": ground_energy,
        "first_excited_energy": first_excited_energy,
        "top_energy": top_energy,
        "gap": gap,
        "width": width,
        "normalized_gap": normalized_gap,
        "product_denominator_normalized_gap": 1.0 / n,
        "normalized_gap_ratio_to_product": normalized_gap_ratio,
        "minimum_full_spectrum_spacing": float(np.min(gaps)),
        "distinct_level_count": distinct_level_count,
        "full_spectrum_simple": distinct_level_count == (1 << n),
        "even_sector_level_statistics": central_gap_ratio(even_eigenvalues),
        "odd_sector_level_statistics": central_gap_ratio(odd_eigenvalues),
        "checked": bool(
            exact_matrix_match
            and hermitian_residual <= MATRIX_TOLERANCE
            and reflection_commutator_max_abs == 0
            and parity_orthogonality_residual <= SYMMETRY_TOLERANCE
            and parity_cross_residual <= SYMMETRY_TOLERANCE
            and parity_block_off_diagonal_residual <= SYMMETRY_TOLERANCE
            and parity_spectrum_max_abs_error <= SPECTRUM_TOLERANCE
        ),
    }


def pauli_word(n: int, entries: dict[int, str]) -> str:
    chars = ["I"] * n
    for site, value in entries.items():
        chars[site] = value
    return "".join(chars)


def bounded_range_pauli_basis(n: int, max_range: int) -> list[str]:
    basis = ["I" * n]
    for span in range(1, max_range + 1):
        for start in range(n - span + 1):
            for local in product("IXYZ", repeat=span):
                if local[0] == "I" or local[-1] == "I":
                    continue
                chars = ["I"] * n
                chars[start : start + span] = local
                basis.append("".join(chars))
    return basis


def hamiltonian_pauli_terms(
    n: int,
    coupling: Fraction,
) -> tuple[list[tuple[int, str]], int]:
    denominator = common_denominator(coupling)
    field_numerator = FIELD.numerator * denominator // FIELD.denominator
    coupling_numerator = (
        coupling.numerator * denominator // coupling.denominator
    )
    terms: list[tuple[int, str]] = []
    for site in range(n):
        terms.append((-denominator, pauli_word(n, {site: "X"})))
        terms.append((field_numerator, pauli_word(n, {site: "Z"})))
    if coupling_numerator:
        for site in range(n - 1):
            terms.append(
                (
                    coupling_numerator,
                    pauli_word(n, {site: "Z", site + 1: "Z"}),
                )
            )
    return terms, denominator


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


def pauli_commutator_columns(
    n: int,
    coupling: Fraction,
    max_range: int,
) -> tuple[list[str], list[dict[int, int]], list[str], int, str]:
    candidate_basis = bounded_range_pauli_basis(n, max_range)
    hamiltonian_terms, _ = hamiltonian_pauli_terms(n, coupling)
    raw_columns: list[dict[str, int]] = []
    output_words: set[str] = set()
    for candidate in candidate_basis:
        column: dict[str, int] = {}
        for coefficient, term in hamiltonian_terms:
            if not pauli_anticommutes(term, candidate):
                continue
            phase, output = pauli_multiply(term, candidate)
            sign = int(round((phase / 1j).real))
            column[output] = column.get(output, 0) + coefficient * sign
        column = {key: value for key, value in column.items() if value}
        raw_columns.append(column)
        output_words.update(column)
    output_basis = sorted(output_words)
    output_index = {word: index for index, word in enumerate(output_basis)}
    columns = [
        {output_index[word]: value for word, value in column.items()}
        for column in raw_columns
    ]
    triples = [
        (output_basis[row], column_index, value)
        for column_index, column in enumerate(columns)
        for row, value in sorted(column.items())
    ]
    nonzero_count = len(triples)
    matrix_hash = canonical_hash(
        {
            "candidate_basis": candidate_basis,
            "output_basis": output_basis,
            "triples": triples,
        }
    )
    return (
        candidate_basis,
        columns,
        output_basis,
        nonzero_count,
        matrix_hash,
    )


def modular_sparse_rank(
    columns: list[dict[int, int]],
    prime: int,
) -> int:
    pivot_basis: dict[int, dict[int, int]] = {}
    for column in columns:
        vector = {
            row: value % prime
            for row, value in column.items()
            if value % prime
        }
        while vector:
            pivot = min(vector)
            if pivot not in pivot_basis:
                inverse = pow(vector[pivot], prime - 2, prime)
                pivot_basis[pivot] = {
                    row: (value * inverse) % prime
                    for row, value in vector.items()
                    if (value * inverse) % prime
                }
                break
            factor = vector[pivot]
            for row, value in pivot_basis[pivot].items():
                updated = (vector.get(row, 0) - factor * value) % prime
                if updated:
                    vector[row] = updated
                else:
                    vector.pop(row, None)
    return len(pivot_basis)


def combine_columns(
    columns: list[dict[int, int]],
    coefficients: dict[int, int],
) -> dict[int, int]:
    output: dict[int, int] = {}
    for column_index, coefficient in coefficients.items():
        for row, value in columns[column_index].items():
            output[row] = output.get(row, 0) + coefficient * value
    return {row: value for row, value in output.items() if value}


def local_charge_row(
    n: int,
    coupling: Fraction,
) -> dict[str, Any]:
    (
        candidate_basis,
        columns,
        output_basis,
        nonzero_count,
        matrix_hash,
    ) = pauli_commutator_columns(
        n,
        coupling,
        LOCAL_CHARGE_MAX_RANGE,
    )
    candidate_index = {
        word: index for index, word in enumerate(candidate_basis)
    }
    hamiltonian_terms, denominator = hamiltonian_pauli_terms(n, coupling)
    hamiltonian_vector: dict[int, int] = {}
    for coefficient, word in hamiltonian_terms:
        index = candidate_index[word]
        hamiltonian_vector[index] = (
            hamiltonian_vector.get(index, 0) + coefficient
        )
    identity_vector = {candidate_index["I" * n]: 1}
    identity_kernel_verified = not combine_columns(columns, identity_vector)
    hamiltonian_kernel_verified = not combine_columns(
        columns,
        hamiltonian_vector,
    )
    modular_ranks = {
        str(prime): modular_sparse_rank(columns, prime)
        for prime in MODULAR_PRIMES
    }
    modular_nullities = {
        prime: len(candidate_basis) - rank
        for prime, rank in modular_ranks.items()
    }

    site_block_kernel_count = 0
    if coupling == 0:
        for site in range(n):
            vector = {
                candidate_index[pauli_word(n, {site: "X"})]: -4,
                candidate_index[pauli_word(n, {site: "Z"})]: 3,
            }
            if not combine_columns(columns, vector):
                site_block_kernel_count += 1

    exact_nullity_two = bool(
        coupling != 0
        and identity_kernel_verified
        and hamiltonian_kernel_verified
        and all(
            rank == len(candidate_basis) - 2
            for rank in modular_ranks.values()
        )
    )
    zero_control_extensive_kernel = bool(
        coupling == 0
        and identity_kernel_verified
        and site_block_kernel_count == n
    )
    return {
        "coupling": fraction_text(coupling),
        "coupling_numerator": coupling.numerator,
        "coupling_denominator": coupling.denominator,
        "n": n,
        "max_contiguous_support_range": LOCAL_CHARGE_MAX_RANGE,
        "candidate_basis_size": len(candidate_basis),
        "output_basis_size": len(output_basis),
        "commutator_nonzero_count": nonzero_count,
        "commutator_matrix_sha256": matrix_hash,
        "hamiltonian_common_denominator": denominator,
        "identity_kernel_verified": identity_kernel_verified,
        "hamiltonian_kernel_verified": hamiltonian_kernel_verified,
        "modular_primes": list(MODULAR_PRIMES),
        "modular_ranks": modular_ranks,
        "modular_nullities": modular_nullities,
        "exact_nullity_two_certified": exact_nullity_two,
        "site_block_kernel_count": site_block_kernel_count,
        "known_rational_kernel_dimension_lower_bound": (
            n + 1 if coupling == 0 else 2
        ),
        "zero_control_extensive_kernel_verified": zero_control_extensive_kernel,
        "checked": (
            exact_nullity_two
            if coupling != 0
            else zero_control_extensive_kernel
        ),
    }


def free_fermion_geometry() -> dict[str, Any]:
    field = (Fraction(-1), Fraction(0), Fraction(3, 4))
    coupling_axis = (Fraction(0), Fraction(0), Fraction(1))
    dot = sum(a * b for a, b in zip(field, coupling_axis))
    field_norm_squared = sum(value * value for value in field)
    coupling_norm_squared = sum(value * value for value in coupling_axis)
    squared_alignment = (
        dot * dot / (field_norm_squared * coupling_norm_squared)
    )
    return {
        "tilted_field": [fraction_text(value) for value in field],
        "ising_coupling_axis": [
            fraction_text(value) for value in coupling_axis
        ],
        "dot_product": fraction_text(dot),
        "field_norm_squared": fraction_text(field_norm_squared),
        "coupling_axis_norm_squared": fraction_text(coupling_norm_squared),
        "squared_alignment": fraction_text(squared_alignment),
        "standard_jw_orthogonality_condition_satisfied": dot == 0,
        "scoped_obstruction": (
            "No dot-product-preserving on-site rotation can make the tilted "
            "field axis orthogonal to the Ising coupling axis, a necessary "
            "condition for the declared standard parity-preserving quadratic "
            "Jordan-Wigner alignment."
        ),
        "not_excluded": [
            "site-dependent nonlocal dualities",
            "interacting Bethe-ansatz integrability",
            "quasi-local conserved charges above range four",
            "auxiliary-mode or nonstandard fermionizations",
        ],
    }


def coupling_summary(
    rows: list[dict[str, Any]],
    phase: str,
    coupling: Fraction,
) -> dict[str, Any]:
    selected = [
        row
        for row in rows
        if row["phase"] == phase
        and row["coupling_numerator"] == coupling.numerator
        and row["coupling_denominator"] == coupling.denominator
    ]
    tail = [row for row in selected if row["n"] in TAIL_SIZES]
    tail_ratios = [
        value
        for row in tail
        for value in (
            row["even_sector_level_statistics"]["mean_adjacent_gap_ratio"],
            row["odd_sector_level_statistics"]["mean_adjacent_gap_ratio"],
        )
        if value is not None
    ]
    tail_median = float(median(tail_ratios)) if tail_ratios else None
    if tail_median is None:
        classification = "degenerate_control"
        poisson_distance = None
        goe_distance = None
    else:
        poisson_distance = abs(tail_median - POISSON_REFERENCE)
        goe_distance = abs(tail_median - GOE_REFERENCE)
        classification = (
            "goe_like_reference_closer"
            if goe_distance < poisson_distance
            else "poisson_like_reference_closer"
        )
    return {
        "phase": phase,
        "coupling": fraction_text(coupling),
        "coupling_numerator": coupling.numerator,
        "coupling_denominator": coupling.denominator,
        "row_count": len(selected),
        "checked_row_count": sum(row["checked"] for row in selected),
        "simple_spectrum_row_count": sum(
            row["full_spectrum_simple"] for row in selected
        ),
        "tail_sizes": list(TAIL_SIZES),
        "tail_sector_ratio_count": len(tail_ratios),
        "tail_sector_mean_gap_ratios": tail_ratios,
        "tail_median_gap_ratio": tail_median,
        "poisson_reference": POISSON_REFERENCE,
        "goe_reference": GOE_REFERENCE,
        "distance_to_poisson_reference": poisson_distance,
        "distance_to_goe_reference": goe_distance,
        "reference_classification": classification,
        "normalized_gap_ratio_min": min(
            row["normalized_gap_ratio_to_product"] for row in selected
        ),
        "normalized_gap_ratio_max": max(
            row["normalized_gap_ratio_to_product"] for row in selected
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
            "checked_sizes": list(CHECKED_SIZES),
            "tail_sizes": list(TAIL_SIZES),
            "pilot_couplings": [
                fraction_text(value) for value in PILOT_COUPLINGS
            ],
            "holdout_couplings": [
                fraction_text(value) for value in HOLDOUT_COUPLINGS
            ],
        },
        "pilot_disclosure": {
            "status": "exploratory_pilot_observed_before_protocol_freeze",
            "acceptance_use": "none",
            "purpose": (
                "Choose an honest weak/transition/strong holdout partition "
                "without treating the pilot as confirmatory evidence."
            ),
        },
        "holdout_acceptance": {
            "weak_couplings": [
                fraction_text(value) for value in WEAK_HOLDOUT_COUPLINGS
            ],
            "transition_couplings": [
                fraction_text(value)
                for value in TRANSITION_HOLDOUT_COUPLINGS
            ],
            "strong_couplings": [
                fraction_text(value) for value in STRONG_HOLDOUT_COUPLINGS
            ],
            "weak_rule": (
                "tail median reflection-sector adjacent-gap ratio is closer "
                "to the Poisson reference than the GOE reference"
            ),
            "strong_rule": (
                "each tail median reflection-sector adjacent-gap ratio is "
                "closer to the GOE reference than the Poisson reference"
            ),
            "transition_rule": "record only; never use for acceptance",
            "simple_spectrum_rule": (
                "every nonzero holdout size has a simple full spectrum"
            ),
            "local_charge_rule": (
                "for every nonzero holdout and n=6..10, the complete "
                "contiguous-range<=4 Pauli ansatz has exact nullity two, "
                "certified by identity/H kernels and rank ncols-2 modulo "
                "two declared primes"
            ),
        },
        "reference_values": {
            "poisson_mean_adjacent_gap_ratio": POISSON_REFERENCE,
            "goe_mean_adjacent_gap_ratio": GOE_REFERENCE,
            "interpretation": (
                "finite-size symmetry-resolved reference comparison only"
            ),
        },
        "local_charge_search": {
            "basis": (
                "identity plus every Pauli word with minimal contiguous "
                "support span at most four"
            ),
            "max_range": LOCAL_CHARGE_MAX_RANGE,
            "modular_primes": list(MODULAR_PRIMES),
            "exactness_argument": (
                "two explicit rational kernel vectors give nullity>=2; "
                "rank ncols-2 modulo a prime gives rational rank>=ncols-2, "
                "hence rational nullity=2"
            ),
            "zero_control": (
                "J=0 must retain identity plus n independent tilted-site "
                "blocks as exact rational conserved operators"
            ),
        },
        "independent_implementations": [
            "integer computational-basis bit action",
            "integer Kronecker Pauli-word construction",
            "two-prime sparse modular commutator rank",
        ],
        "symmetry_policy": {
            "declared_symmetry": "open-chain spatial reflection",
            "level_statistics": "separate even and odd reflection sectors",
            "central_trim_fraction": CENTRAL_TRIM_FRACTION,
        },
        "lean": {
            "module": MODULE_PATH.as_posix(),
            "required_definitions": REQUIRED_DEFINITIONS,
            "required_theorems": REQUIRED_THEOREMS,
            "scope": (
                "standard parity-preserving quadratic Jordan-Wigner axis "
                "alignment under dot-product-preserving on-site rotations"
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
    lines = [
        "# B9 R193 Coupling and Integrability Stress",
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
        f"- Transcript hash: `{result['execution']['transcript_sha256']}`",
        (
            "- Scoped holdout crossover candidate accepted: "
            f"`{str(summary['scoped_candidate_accepted']).lower()}`"
        ),
        "- Scientific promotion accepted: `false`",
        "- New credit delta: `0`",
        "",
        "## Honest Pilot/Holdout Boundary",
        "",
        "The pilot grid was observed before this protocol was frozen. It is",
        "therefore reported as exploratory evidence only and contributes",
        "`zero` acceptance decisions. The confirmatory decision uses only the",
        "six previously unopened rational holdout couplings.",
        "",
        "## Holdout Coupling Summary",
        "",
        (
            "| J | rows | simple | tail median r | reference closer | "
            "norm-gap ratio range |"
        ),
        "|---:|---:|---:|---:|---|---:|",
    ]
    holdout_summaries = [
        row for row in result["coupling_summaries"] if row["phase"] == "holdout"
    ]
    for row in holdout_summaries:
        lines.append(
            "| {coupling} | {rows} | {simple} | {median:.6f} | "
            "{classification} | {low:.4f}..{high:.4f} |".format(
                coupling=row["coupling"],
                rows=row["row_count"],
                simple=row["simple_spectrum_row_count"],
                median=row["tail_median_gap_ratio"],
                classification=row["reference_classification"],
                low=row["normalized_gap_ratio_min"],
                high=row["normalized_gap_ratio_max"],
            )
        )
    lines.extend(
        [
            "",
            (
                f"- Nonzero holdout simple-spectrum rows: "
                f"`{summary['holdout_simple_spectrum_row_count']}/"
                f"{summary['holdout_row_count']}`."
            ),
            (
                f"- Weak holdout Poisson-like classifications: "
                f"`{summary['weak_holdout_pass_count']}/"
                f"{len(WEAK_HOLDOUT_COUPLINGS)}`."
            ),
            (
                f"- Strong holdout GOE-like classifications: "
                f"`{summary['strong_holdout_pass_count']}/"
                f"{len(STRONG_HOLDOUT_COUPLINGS)}`."
            ),
            (
                f"- Holdout normalized-gap improvements over R191: "
                f"`{summary['holdout_normalized_gap_gain_count']}/"
                f"{summary['holdout_row_count']}`."
            ),
            "",
            "The transition coupling is displayed but excluded from every",
            "acceptance count. The GOE/Poisson labels are finite-size reference",
            "comparisons, not a quantum-chaos theorem.",
            "",
            "## Exact Local-Charge Adversary",
            "",
            (
                "For each declared row, the search spans identity plus every "
                "Pauli word whose minimal contiguous support interval has "
                "length at most four. The commutator matrix is integer-valued."
            ),
            "",
            (
                f"- Nonzero holdout exact-nullity-two rows: "
                f"`{summary['holdout_local_charge_nullity_two_count']}/"
                f"{summary['holdout_local_charge_row_count']}`."
            ),
            (
                f"- Zero-coupling extensive-control rows: "
                f"`{summary['zero_control_extensive_kernel_count']}/"
                f"{len(CHECKED_SIZES)}`."
            ),
            (
                "- Every nonzero holdout row contains the explicit identity and "
                "Hamiltonian kernels. Rank `ncols-2` modulo both declared "
                "primes certifies that no third rational conserved operator "
                "exists inside the complete range-four ansatz."
            ),
            (
                "- At `J=0`, identity plus `n` independent tilted-site blocks "
                "are verified exact rational kernels, so the adversary detects "
                "the known integrable control."
            ),
            "",
            "## Standard Jordan-Wigner Axis Obstruction",
            "",
            "- Tilted field vector: `(-1, 0, 3/4)`.",
            "- Ising coupling axis: `(0, 0, 1)`.",
            "- Exact dot product: `3/4`.",
            "- Exact squared alignment: `9/25`.",
            (
                "- Lean proves that every dot-product-preserving on-site "
                "rotation preserves this nonzero overlap. It therefore cannot "
                "make the field axis orthogonal to the coupling axis, the "
                "declared necessary condition for a standard "
                "parity-preserving quadratic Jordan-Wigner alignment."
            ),
            "",
            "This does not exclude nonlocal dualities, higher-range quasi-local",
            "charges, interacting Bethe-ansatz structure, auxiliary-mode",
            "fermionizations, or any other integrability mechanism outside the",
            "declared route.",
            "",
            "## Supported",
            "",
        ]
    )
    for claim in result["claim_boundary"]["supported"]:
        lines.append(f"- {claim}")
    lines.extend(["", "## Not Supported", ""])
    for claim in result["claim_boundary"]["not_supported"]:
        lines.append(f"- {claim}")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            "Attack the holdout crossover with range-five/six and quasi-local",
            "charge searches, site-dependent/nonlocal duality candidates, and",
            "larger-size sparse shift-invert spectra. A nonintegrability or",
            "quantum-chaos claim remains forbidden unless those independent",
            "escape routes and finite-size drift are closed.",
            "",
        ]
    )
    return "\n".join(lines)


def build_result(root: Path) -> tuple[dict[str, Any], str, str]:
    lean = resolve_executable("lean")
    lake = resolve_executable("lake")
    probes = [
        run_command(
            [lean, "--version"],
            ["lean", "--version"],
            root,
            120,
        ),
        run_command(
            [lake, "--version"],
            ["lake", "--version"],
            root,
            120,
        ),
        run_command(
            [
                lake,
                "env",
                "lean",
                MODULE_PATH.as_posix(),
            ],
            [
                "lake",
                "env",
                "lean",
                MODULE_PATH.as_posix(),
            ],
            root,
            300,
        ),
    ]
    transcript = render_transcript(probes)
    transcript_hash = sha256_bytes(transcript.encode("utf-8"))
    module_text = (root / MODULE_PATH).read_text()
    definition_names = set(
        re.findall(
            r"(?m)^(?:noncomputable\s+)?(?:abbrev|def)\s+([A-Za-z0-9_']+)",
            module_text,
        )
    )
    theorem_names = set(
        re.findall(
            r"(?m)^theorem\s+([A-Za-z0-9_']+)",
            module_text,
        )
    )
    forbidden_tokens = re.findall(
        r"\b(?:sorry|axiom)\b",
        module_text,
    )

    spectrum_rows = [
        spectrum_row(n, coupling, phase)
        for phase, couplings in (
            ("pilot", PILOT_COUPLINGS),
            ("holdout", HOLDOUT_COUPLINGS),
        )
        for coupling in couplings
        for n in CHECKED_SIZES
    ]
    coupling_summaries = [
        coupling_summary(spectrum_rows, phase, coupling)
        for phase, couplings in (
            ("pilot", PILOT_COUPLINGS),
            ("holdout", HOLDOUT_COUPLINGS),
        )
        for coupling in couplings
    ]
    local_charge_rows = [
        local_charge_row(n, coupling)
        for coupling in (Fraction(0), *HOLDOUT_COUPLINGS)
        for n in CHECKED_SIZES
    ]
    geometry = free_fermion_geometry()

    holdout_rows = [
        row for row in spectrum_rows if row["phase"] == "holdout"
    ]
    weak_summaries = [
        row
        for row in coupling_summaries
        if row["phase"] == "holdout"
        and Fraction(
            row["coupling_numerator"],
            row["coupling_denominator"],
        )
        in WEAK_HOLDOUT_COUPLINGS
    ]
    strong_summaries = [
        row
        for row in coupling_summaries
        if row["phase"] == "holdout"
        and Fraction(
            row["coupling_numerator"],
            row["coupling_denominator"],
        )
        in STRONG_HOLDOUT_COUPLINGS
    ]
    weak_pass_count = sum(
        row["reference_classification"]
        == "poisson_like_reference_closer"
        for row in weak_summaries
    )
    strong_pass_count = sum(
        row["reference_classification"]
        == "goe_like_reference_closer"
        for row in strong_summaries
    )
    holdout_local_rows = [
        row for row in local_charge_rows if row["coupling"] != "0"
    ]
    zero_control_rows = [
        row for row in local_charge_rows if row["coupling"] == "0"
    ]
    holdout_simple_count = sum(
        row["full_spectrum_simple"] for row in holdout_rows
    )
    holdout_nullity_two_count = sum(
        row["exact_nullity_two_certified"] for row in holdout_local_rows
    )
    zero_extensive_count = sum(
        row["zero_control_extensive_kernel_verified"]
        for row in zero_control_rows
    )
    normalized_gap_gain_count = sum(
        row["normalized_gap_ratio_to_product"] > 1.0 + SPECTRUM_TOLERANCE
        for row in holdout_rows
    )
    all_spectrum_rows_checked = all(row["checked"] for row in spectrum_rows)
    scoped_candidate_accepted = bool(
        all_spectrum_rows_checked
        and holdout_simple_count == len(holdout_rows)
        and holdout_nullity_two_count == len(holdout_local_rows)
        and zero_extensive_count == len(zero_control_rows)
        and weak_pass_count == len(WEAK_HOLDOUT_COUPLINGS)
        and strong_pass_count == len(STRONG_HOLDOUT_COUPLINGS)
        and geometry["standard_jw_orthogonality_condition_satisfied"] is False
    )
    status = STATUS_ACCEPTED if scoped_candidate_accepted else STATUS_REJECTED

    protocol_payload = protocol()
    protocol_hash = canonical_hash(protocol_payload)
    module_hash = sha256_file(root / MODULE_PATH)
    tool_hash = sha256_file(Path(__file__).resolve())
    execution_ok = bool(
        all(
            probe["returncode"] == 0 and not probe["timed_out"]
            for probe in probes
        )
        and all(
            not probe["stderr"].strip()
            or "warning:" not in probe["stderr"].lower()
            for probe in probes
        )
    )
    source_complete = bool(
        set(REQUIRED_DEFINITIONS).issubset(definition_names)
        and set(REQUIRED_THEOREMS).issubset(theorem_names)
        and not forbidden_tokens
    )

    summary = {
        "spectrum_row_count": len(spectrum_rows),
        "pilot_row_count": sum(
            row["phase"] == "pilot" for row in spectrum_rows
        ),
        "holdout_row_count": len(holdout_rows),
        "holdout_simple_spectrum_row_count": holdout_simple_count,
        "weak_holdout_pass_count": weak_pass_count,
        "strong_holdout_pass_count": strong_pass_count,
        "transition_holdout_acceptance_count": 0,
        "holdout_local_charge_row_count": len(holdout_local_rows),
        "holdout_local_charge_nullity_two_count": holdout_nullity_two_count,
        "zero_control_extensive_kernel_count": zero_extensive_count,
        "holdout_normalized_gap_gain_count": normalized_gap_gain_count,
        "scoped_candidate_accepted": scoped_candidate_accepted,
        "scientific_promotion_accepted": False,
    }

    requirements = [
        requirement(
            "R1",
            "Pilot and holdout coupling sets are disjoint and frozen",
            not set(PILOT_COUPLINGS).intersection(HOLDOUT_COUPLINGS),
            {
                "pilot": [
                    fraction_text(value) for value in PILOT_COUPLINGS
                ],
                "holdout": [
                    fraction_text(value) for value in HOLDOUT_COUPLINGS
                ],
            },
        ),
        requirement(
            "R2",
            "Lean source contains every required definition and theorem",
            source_complete,
            {
                "required_definition_count": len(REQUIRED_DEFINITIONS),
                "required_theorem_count": len(REQUIRED_THEOREMS),
                "forbidden_token_count": len(forbidden_tokens),
            },
        ),
        requirement(
            "R3",
            "Pinned Lean and Lake probes complete without warnings",
            execution_ok,
            {
                "returncodes": [probe["returncode"] for probe in probes],
                "timed_out": [probe["timed_out"] for probe in probes],
            },
        ),
        requirement(
            "R4",
            "Exact field-coupling geometry matches the Lean obstruction",
            geometry["dot_product"] == "3/4"
            and geometry["field_norm_squared"] == "25/16"
            and geometry["coupling_axis_norm_squared"] == "1"
            and geometry["squared_alignment"] == "9/25"
            and geometry["standard_jw_orthogonality_condition_satisfied"]
            is False,
            geometry,
        ),
        requirement(
            "R5",
            "Independent exact integer matrices agree on every row",
            all(
                row["exact_integer_matrix_match"]
                and row["matrix_sha256"]
                == row["independent_matrix_sha256"]
                for row in spectrum_rows
            ),
            {"row_count": len(spectrum_rows)},
        ),
        requirement(
            "R6",
            "Reflection symmetry and parity reconstruction pass every row",
            all(
                row["reflection_commutator_max_abs_exact"] == 0
                and row["parity_block_off_diagonal_residual"]
                <= SYMMETRY_TOLERANCE
                and row["parity_spectrum_max_abs_error"]
                <= SPECTRUM_TOLERANCE
                for row in spectrum_rows
            ),
            {"row_count": len(spectrum_rows)},
        ),
        requirement(
            "R7",
            "Every nonzero holdout spectrum is simple",
            holdout_simple_count == len(holdout_rows),
            {
                "simple_count": holdout_simple_count,
                "row_count": len(holdout_rows),
            },
        ),
        requirement(
            "R8",
            "The zero-coupling pilot retains degeneracy at every size",
            all(
                not row["full_spectrum_simple"]
                for row in spectrum_rows
                if row["phase"] == "pilot" and row["coupling"] == "0"
            ),
            {"checked_sizes": list(CHECKED_SIZES)},
        ),
        requirement(
            "R9",
            "Every local-charge row uses the complete range-four basis",
            all(
                row["max_contiguous_support_range"]
                == LOCAL_CHARGE_MAX_RANGE
                and row["candidate_basis_size"] > 0
                and row["commutator_nonzero_count"] > 0
                for row in local_charge_rows
            ),
            {"row_count": len(local_charge_rows)},
        ),
        requirement(
            "R10",
            "Every nonzero holdout local-charge kernel has exact nullity two",
            holdout_nullity_two_count == len(holdout_local_rows),
            {
                "passed": holdout_nullity_two_count,
                "total": len(holdout_local_rows),
                "modular_primes": list(MODULAR_PRIMES),
            },
        ),
        requirement(
            "R11",
            "The zero-coupling control exposes identity plus n site charges",
            zero_extensive_count == len(zero_control_rows),
            {
                "passed": zero_extensive_count,
                "total": len(zero_control_rows),
            },
        ),
        requirement(
            "R12",
            "The weak holdout is closer to the Poisson reference",
            weak_pass_count == len(WEAK_HOLDOUT_COUPLINGS),
            {
                "passed": weak_pass_count,
                "total": len(WEAK_HOLDOUT_COUPLINGS),
            },
        ),
        requirement(
            "R13",
            "Every strong holdout is closer to the GOE reference",
            strong_pass_count == len(STRONG_HOLDOUT_COUPLINGS),
            {
                "passed": strong_pass_count,
                "total": len(STRONG_HOLDOUT_COUPLINGS),
            },
        ),
        requirement(
            "R14",
            "The transition coupling contributes no acceptance decision",
            summary["transition_holdout_acceptance_count"] == 0,
            {
                "transition_couplings": [
                    fraction_text(value)
                    for value in TRANSITION_HOLDOUT_COUPLINGS
                ]
            },
        ),
        requirement(
            "R15",
            "No holdout row improves the R191 normalized-gap denominator",
            normalized_gap_gain_count == 0,
            {
                "gain_count": normalized_gap_gain_count,
                "row_count": len(holdout_rows),
            },
        ),
        requirement(
            "R16",
            "The scoped holdout crossover candidate passes every frozen gate",
            scoped_candidate_accepted,
            summary,
        ),
        requirement(
            "R17",
            "Broad theorem and hardware claims remain explicitly false",
            bool(FALSE_CLAIMS)
            and protocol_payload["claim_boundary"][
                "scientific_promotion_accepted"
            ]
            is False
            and protocol_payload["claim_boundary"]["new_credit_delta"] == 0,
            {
                "false_claim_count": len(FALSE_CLAIMS),
                "new_credit_delta": 0,
            },
        ),
    ]

    result: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "status": status,
        "last_updated": LAST_UPDATED,
        "protocol": protocol_payload,
        "protocol_sha256": protocol_hash,
        "free_fermion_geometry": geometry,
        "spectrum_rows": spectrum_rows,
        "coupling_summaries": coupling_summaries,
        "local_charge_rows": local_charge_rows,
        "summary": summary,
        "requirements": requirements,
        "requirements_total": len(requirements),
        "requirements_passed": sum(row["passed"] for row in requirements),
        "evidence_integrity_complete": all(
            row["passed"] for row in requirements
        ),
        "claim_boundary": {
            "true_claims": TRUE_CLAIMS,
            "false_claims": FALSE_CLAIMS,
            "supported": [
                "A pilot/holdout split with acceptance based only on unopened holdout couplings",
                "Exact independent matrix agreement and reflection-sector reconstruction",
                "Simple full spectra on every nonzero holdout size",
                "Exact range-four local-charge nullity two on every nonzero holdout row",
                "An extensive exact local-charge family at the J=0 control",
                "A Lean-checked standard Jordan-Wigner axis-alignment obstruction",
                "A finite-size weak-to-strong symmetry-resolved crossover candidate",
                "Zero normalized-gap improvements over the R191 denominator",
            ],
            "not_supported": [
                "This is not an all-n spectrum theorem.",
                "This does not exclude every integrability mechanism.",
                "This is not a nonintegrability or quantum-chaos theorem.",
                "This is not a spectral-hardness theorem.",
                "This is not quantum-hardware evidence.",
                "This is not a Quantum PCP or NLTS theorem.",
                "This is not a BQP separation or solved frontier.",
            ],
            "scientific_promotion_accepted": False,
            "new_credit_delta": 0,
        },
        "execution": {
            "probes": probes,
            "transcript_sha256": transcript_hash,
            "module_warning_count": sum(
                probe["stderr"].lower().count("warning:")
                + probe["stdout"].lower().count("warning:")
                for probe in probes
            ),
        },
        "evidence": {
            "module": MODULE_PATH.as_posix(),
            "module_sha256": module_hash,
            "tool": Path(__file__).resolve().relative_to(root).as_posix(),
            "tool_sha256": tool_hash,
            "result": RESULT_PATH.as_posix(),
            "report": REPORT_PATH.as_posix(),
            "transcript": TRANSCRIPT_PATH.as_posix(),
        },
        "new_credit_delta": 0,
    }
    payload_without_hash = dict(result)
    result["payload_sha256"] = canonical_hash(payload_without_hash)
    report = render_report(result)
    return result, report, transcript


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    result, report, transcript = build_result(root)
    result_path = root / RESULT_PATH
    report_path = root / REPORT_PATH
    transcript_path = root / TRANSCRIPT_PATH
    result_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    report_path.write_text(report)
    transcript_path.write_text(transcript)
    summary = {
        "status": result["status"],
        "requirements": (
            f"{result['requirements_passed']}/{result['requirements_total']}"
        ),
        "spectrum_rows": result["summary"]["spectrum_row_count"],
        "holdout_rows": result["summary"]["holdout_row_count"],
        "holdout_simple_rows": result["summary"][
            "holdout_simple_spectrum_row_count"
        ],
        "local_nullity_two_rows": result["summary"][
            "holdout_local_charge_nullity_two_count"
        ],
        "scoped_candidate_accepted": result["summary"][
            "scoped_candidate_accepted"
        ],
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "payload_sha256": result["payload_sha256"],
    }
    print(
        json.dumps(
            summary,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )
    return 0 if result["evidence_integrity_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
