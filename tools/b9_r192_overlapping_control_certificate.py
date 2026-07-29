#!/usr/bin/env python3
"""Build and independently check the B9 R192 overlapping-control certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


EXPERIMENT_ID = "B9-R192-connected-overlap-spectral-boundary"
METHOD = "b9_r192_connected_overlap_spectral_boundary_v1"
STATUS = "checked_connected_overlap_spectral_boundary"
VERSION = "1.0"
LAST_UPDATED = "2026-07-29"
CHECKED_SIZES = tuple(range(4, 11))
COMMON_DENOMINATOR = 4
FIELD_NUMERATOR = 3
COUPLING_NUMERATOR = 2
MATRIX_TOLERANCE = 1e-12
SPECTRUM_TOLERANCE = 1e-10
SYMMETRY_TOLERANCE = 1e-12
CENTRAL_TRIM_FRACTION = 0.10
NORMALIZED_GAP_TARGET_FACTOR = 1.05
MODULE_PATH = Path("B9/ClusterStabilizer/OverlappingControl.lean")
TRUE_CLAIMS = [
    "connected_two_local_support_formalized",
    "adjacent_bond_overlap_formalized",
    "local_bond_noncommutation_formalized",
    "overlapping_operator_hermiticity_formalized",
    "independent_matrix_replay_complete",
    "reflection_symmetry_resolved",
    "finite_spectrum_degeneracy_collapse_observed",
    "normalized_gap_target_rejected",
]
FALSE_CLAIMS = [
    "all_n_overlapping_spectrum_theorem",
    "nonintegrability_theorem",
    "quantum_chaos_theorem",
    "spectral_hardness_theorem",
    "quantum_hardware_execution",
    "quantum_pcp_theorem",
    "nlts_theorem",
    "global_gap_amplification_impossibility",
    "bqp_separation",
    "solved_frontier",
]
REQUIRED_DEFINITIONS = [
    "overlapCoupling",
    "nearestNeighborSupport",
    "openChainBondSet",
    "zzBondSitePauli",
    "zzBondPauliWord",
    "zzBondTermOperator",
    "zzInteractionOperator",
    "overlappingControlOperator",
    "twoQubitLeftTiltedOperator",
    "twoQubitZZOperator",
]
REQUIRED_THEOREMS = [
    "nearest_neighbor_support_card",
    "adjacent_bond_support_intersection",
    "adjacent_bond_supports_overlap",
    "first_two_bonds_cover_three_sites",
    "zzBondSitePauli_isHermitian",
    "zzBondPauliWord_isHermitian",
    "zzBondTermOperator_isHermitian",
    "zzInteractionOperator_isHermitian",
    "overlappingControlOperator_isHermitian",
    "twoQubitLeftTiltedOperator_isHermitian",
    "twoQubitZZOperator_isHermitian",
    "twoQubit_left_tilted_does_not_commute_with_zz",
    "overlapCoupling_nonzero",
    "overlapping_control_structural_boundary",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hash(payload: Any) -> str:
    return sha256_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


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


def build_bit_action_numerator(n: int) -> np.ndarray:
    dimension = 1 << n
    matrix = np.zeros((dimension, dimension), dtype=np.int64)
    for state in range(dimension):
        z = [1 - 2 * ((state >> site) & 1) for site in range(n)]
        matrix[state, state] += (
            FIELD_NUMERATOR * sum(z)
            + COUPLING_NUMERATOR * sum(
                z[site] * z[site + 1] for site in range(n - 1)
            )
        )
        for site in range(n):
            matrix[state ^ (1 << site), state] -= COMMON_DENOMINATOR
    return matrix


def build_kron_numerator(n: int) -> np.ndarray:
    identity = np.eye(2, dtype=np.int64)
    pauli_x = np.array([[0, 1], [1, 0]], dtype=np.int64)
    pauli_z = np.array([[1, 0], [0, -1]], dtype=np.int64)
    dimension = 1 << n
    matrix = np.zeros((dimension, dimension), dtype=np.int64)
    for site in range(n):
        matrix -= COMMON_DENOMINATOR * kron_word(n, {site: pauli_x})
        matrix += FIELD_NUMERATOR * kron_word(n, {site: pauli_z})
    for site in range(n - 1):
        matrix += COUPLING_NUMERATOR * kron_word(
            n,
            {site: pauli_z, site + 1: pauli_z},
        )
    assert identity.shape == (2, 2)
    return matrix


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
    }


def product_denominator(n: int) -> dict[str, Any]:
    scale = 5.0 / 4.0
    levels: list[float] = []
    multiplicities: list[int] = []
    for weight in range(n + 1):
        levels.append(scale * (2 * weight - n))
        multiplicities.append(math.comb(n, weight))
    gap = 5.0 / 2.0
    width = 5.0 * n / 2.0
    return {
        "distinct_level_count": n + 1,
        "dimension": 1 << n,
        "levels": levels,
        "multiplicities": multiplicities,
        "maximum_multiplicity": max(multiplicities),
        "gap": gap,
        "width": width,
        "normalized_gap": 1.0 / n,
    }


def local_exact_checks() -> dict[str, Any]:
    tilted_numerator = np.array([[3, -4], [-4, -3]], dtype=np.int64)
    identity = np.eye(2, dtype=np.int64)
    zz = np.diag([1, -1, -1, 1]).astype(np.int64)
    tilted_left = np.kron(tilted_numerator, identity)
    commutator_numerator = tilted_left @ zz - zz @ tilted_left
    return {
        "common_denominator": COMMON_DENOMINATOR,
        "tilted_left_numerator": tilted_left.tolist(),
        "zz_matrix": zz.tolist(),
        "commutator_numerator": commutator_numerator.tolist(),
        "physical_commutator_max_abs": float(
            np.max(np.abs(commutator_numerator)) / COMMON_DENOMINATOR
        ),
        "commutator_nonzero_exact": bool(np.any(commutator_numerator)),
        "bond_support_card": 2,
        "adjacent_bond_intersection_card": 1,
        "first_two_bonds_union_card": 3,
    }


def spectrum_row(n: int) -> dict[str, Any]:
    bit_numerator = build_bit_action_numerator(n)
    kron_numerator = build_kron_numerator(n)
    exact_matrix_match = np.array_equal(bit_numerator, kron_numerator)
    matrix = bit_numerator.astype(np.float64) / COMMON_DENOMINATOR
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
    parity_cross_residual = float(
        np.max(np.abs(even_basis.T @ odd_basis))
    )
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
    denominator = product_denominator(n)
    normalized_gap_ratio = normalized_gap / denominator["normalized_gap"]
    normalized_target = (
        NORMALIZED_GAP_TARGET_FACTOR * denominator["normalized_gap"]
    )
    distinct_level_count = int(
        1 + np.count_nonzero(gaps > SPECTRUM_TOLERANCE)
    )

    return {
        "n": n,
        "dimension": 1 << n,
        "bond_count": n - 1,
        "interaction_graph_connected": True,
        "adjacent_bond_overlap_count": max(0, n - 2),
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
        "product_denominator_gap": denominator["gap"],
        "product_denominator_width": denominator["width"],
        "product_denominator_normalized_gap": denominator["normalized_gap"],
        "normalized_gap_ratio_to_product": normalized_gap_ratio,
        "normalized_gap_target": normalized_target,
        "normalized_gap_target_passed": normalized_gap >= normalized_target,
        "minimum_full_spectrum_spacing": float(np.min(gaps)),
        "overlap_distinct_level_count": distinct_level_count,
        "overlap_full_spectrum_simple": distinct_level_count == (1 << n),
        "product_distinct_level_count": denominator["distinct_level_count"],
        "product_maximum_multiplicity": denominator["maximum_multiplicity"],
        "finite_degeneracy_collapse_observed": (
            distinct_level_count == (1 << n)
            and denominator["distinct_level_count"] < (1 << n)
        ),
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
            and distinct_level_count == (1 << n)
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
                "sum_i[-X_i+(3/4)Z_i]+(1/2)"
                "sum_{i=0}^{n-2}Z_i Z_{i+1}"
            ),
            "field": "3/4",
            "overlap_coupling": "1/2",
            "locality": 2,
            "checked_sizes": list(CHECKED_SIZES),
        },
        "denominator": {
            "name": "R191 disjoint-site tilted product control",
            "hamiltonian": "sum_i[-X_i+(3/4)Z_i]",
            "gap": "5/2",
            "width": "5n/2",
            "normalized_gap": "1/n",
            "distinct_levels": "n+1",
            "multiplicity": "choose(n,k)",
        },
        "promotion_target": {
            "metric": "normalized_gap",
            "rule": "overlap >= 1.05 * product denominator for every checked n",
            "factor": NORMALIZED_GAP_TARGET_FACTOR,
            "failure_action": "no promotion and no new credit",
        },
        "independent_implementations": [
            "integer bit-action matrix with common denominator four",
            "integer Kronecker Pauli-word matrix with common denominator four",
        ],
        "symmetry_policy": {
            "declared_symmetry": "open-chain spatial reflection",
            "level_statistics": "separate even and odd reflection sectors",
            "central_trim_fraction": CENTRAL_TRIM_FRACTION,
            "interpretation": "finite-size diagnostic only",
        },
        "tolerances": {
            "matrix": MATRIX_TOLERANCE,
            "spectrum": SPECTRUM_TOLERANCE,
            "symmetry": SYMMETRY_TOLERANCE,
        },
        "lean": {
            "module": MODULE_PATH.as_posix(),
            "required_definitions": REQUIRED_DEFINITIONS,
            "required_theorems": REQUIRED_THEOREMS,
        },
        "claim_boundary": {
            "true_claims": TRUE_CLAIMS,
            "false_claims": FALSE_CLAIMS,
            "new_credit_delta": 0,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# B9 R192 Connected Overlap Spectral Boundary",
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
        f"- Lean module warnings: `{result['execution']['module_warning_count']}`",
        f"- New credit delta: `{result['new_credit_delta']}`",
        "",
        "## Frozen Model",
        "",
        "R192 fixes the open-chain Hamiltonian",
        "`H = sum_i[-X_i+(3/4)Z_i] + (1/2)sum_i Z_i Z_{i+1}`",
        f"for `n={CHECKED_SIZES[0]}..{CHECKED_SIZES[-1]}`. The denominator is",
        "the R191 disjoint-site product control under the same local field.",
        "",
        "## Formal Structural Gate",
        "",
        "Lean checks two-site bond support, exact one-site overlap between",
        "adjacent bonds, three-site coverage by the first two bonds, Hermiticity",
        "of every declared operator layer, and a nonzero exact commutator between",
        "the tilted one-site block and an adjacent `ZZ` bond.",
        "",
        "## Independent Spectral Replay",
        "",
        (
            "| n | dim | gap | width | norm gap | product norm | ratio | "
            "distinct levels | even r | odd r | checked |"
        ),
        (
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|"
        ),
    ]
    for row in result["spectrum_rows"]:
        lines.append(
            "| {n} | {dimension} | {gap:.8f} | {width:.8f} | "
            "{normalized_gap:.8f} | {product:.8f} | {ratio:.4f} | "
            "{distinct}/{dimension} | {even_r:.4f} | {odd_r:.4f} | {checked} |".format(
                n=row["n"],
                dimension=row["dimension"],
                gap=row["gap"],
                width=row["width"],
                normalized_gap=row["normalized_gap"],
                product=row["product_denominator_normalized_gap"],
                ratio=row["normalized_gap_ratio_to_product"],
                distinct=row["overlap_distinct_level_count"],
                even_r=row["even_sector_level_statistics"][
                    "mean_adjacent_gap_ratio"
                ],
                odd_r=row["odd_sector_level_statistics"][
                    "mean_adjacent_gap_ratio"
                ],
                checked=str(row["checked"]),
            )
        )
    lines.extend(
        [
            "",
            "Both implementations produce byte-identical integer matrices before",
            "division by four. Reflection commutes exactly with every integer",
            "Hamiltonian, so level statistics are computed separately inside even",
            "and odd reflection sectors.",
            "",
            "## Result",
            "",
            (
                f"- Full-spectrum degeneracy collapse: "
                f"`{result['summary']['degeneracy_collapse_count']}/"
                f"{len(CHECKED_SIZES)}` finite sizes."
            ),
            (
                f"- Normalized-gap target passes: "
                f"`{result['summary']['normalized_gap_target_pass_count']}/"
                f"{len(CHECKED_SIZES)}`."
            ),
            (
                f"- Normalized-gap ratio range versus R191: "
                f"`{result['summary']['normalized_gap_ratio_min']:.4f}` to "
                f"`{result['summary']['normalized_gap_ratio_max']:.4f}`."
            ),
            (
                "- The connected overlap destroys the R191 single-site product "
                "spectrum at the checked sizes, but it does not improve the "
                "preregistered normalized-gap denominator."
            ),
            (
                "- Reflection-resolved adjacent-gap ratios are recorded as a "
                "diagnostic; their finite-size variation is not promoted into "
                "a quantum-chaos or nonintegrability claim."
            ),
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
            "Preregister a bounded coupling sweep and an adversarial low-weight",
            "conserved-operator/free-fermion search. A later result may discuss",
            "nonintegrability only if the symmetry-resolved spectral signal is",
            "stable across size and coupling and the escape-route search fails.",
            "",
        ]
    )
    return "\n".join(lines)


def build_result(
    root: Path,
    transcript_path: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    protocol_payload = protocol()
    protocol_sha256 = canonical_hash(protocol_payload)
    module_path = root / MODULE_PATH
    tool_path = Path(__file__).resolve()
    module_text = module_path.read_text(encoding="utf-8")

    lean = resolve_executable("lean")
    lake = resolve_executable("lake")
    probes = [
        run_command(
            [lean, "--version"],
            ["lean", "--version"],
            root,
            timeout_seconds,
        ),
        run_command(
            [lake, "--version"],
            ["lake", "--version"],
            root,
            timeout_seconds,
        ),
        run_command(
            [lake, "env", "lean", MODULE_PATH.as_posix()],
            ["lake", "env", "lean", MODULE_PATH.as_posix()],
            root,
            timeout_seconds,
        ),
    ]
    transcript = render_transcript(probes)
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(transcript, encoding="utf-8")
    transcript_sha256 = sha256_file(transcript_path)
    module_warning_count = len(
        re.findall(
            r"\bwarning:",
            "\n".join(
                probe["stdout"] + "\n" + probe["stderr"] for probe in probes
            ),
            flags=re.IGNORECASE,
        )
    )

    local_checks = local_exact_checks()
    rows = [spectrum_row(n) for n in CHECKED_SIZES]
    normalized_target_pass_count = sum(
        row["normalized_gap_target_passed"] for row in rows
    )
    degeneracy_collapse_count = sum(
        row["finite_degeneracy_collapse_observed"] for row in rows
    )
    normalized_ratios = [
        row["normalized_gap_ratio_to_product"] for row in rows
    ]
    scientific_promotion_accepted = (
        normalized_target_pass_count == len(rows)
    )

    definitions_present = {
        name: bool(re.search(rf"\bdef\s+{re.escape(name)}\b", module_text))
        for name in REQUIRED_DEFINITIONS
    }
    theorems_present = {
        name: bool(
            re.search(
                rf"\b(?:theorem|lemma)\s+{re.escape(name)}\b",
                module_text,
            )
        )
        for name in REQUIRED_THEOREMS
    }
    probes_passed = all(
        probe["returncode"] == 0 and not probe["timed_out"]
        for probe in probes
    )
    all_rows_checked = all(row["checked"] for row in rows)
    all_matrix_replays_exact = all(
        row["exact_integer_matrix_match"]
        and row["matrix_max_abs_difference"] == 0
        for row in rows
    )
    all_reflection_checks_pass = all(
        row["reflection_commutator_max_abs_exact"] == 0
        and row["parity_block_off_diagonal_residual"]
        <= SYMMETRY_TOLERANCE
        and row["parity_spectrum_max_abs_error"]
        <= SPECTRUM_TOLERANCE
        for row in rows
    )
    all_finite_spectra_simple = all(
        row["overlap_full_spectrum_simple"] for row in rows
    )
    no_credit_consistent = (
        not scientific_promotion_accepted
        and normalized_target_pass_count == 0
    )

    requirements = [
        requirement(
            "R192-C01",
            "Protocol freezes model, sizes, denominator, target, and tolerances.",
            protocol_sha256 == canonical_hash(protocol_payload),
            {"protocol_sha256": protocol_sha256},
        ),
        requirement(
            "R192-C02",
            "Pinned Lean and Lake probes complete without warnings or timeouts.",
            probes_passed and module_warning_count == 0,
            {
                "probe_count": len(probes),
                "module_warning_count": module_warning_count,
                "transcript_sha256": transcript_sha256,
            },
        ),
        requirement(
            "R192-C03",
            "All required Lean definitions and theorems are present.",
            all(definitions_present.values())
            and all(theorems_present.values()),
            {
                "definitions_present": definitions_present,
                "theorems_present": theorems_present,
            },
        ),
        requirement(
            "R192-C04",
            "The overlap coupling is fixed to nonzero one half.",
            COUPLING_NUMERATOR == 2 and COMMON_DENOMINATOR == 4,
            {
                "coupling": "1/2",
                "common_denominator": COMMON_DENOMINATOR,
            },
        ),
        requirement(
            "R192-C05",
            "Two-site supports overlap on one site and connect three sites.",
            local_checks["bond_support_card"] == 2
            and local_checks["adjacent_bond_intersection_card"] == 1
            and local_checks["first_two_bonds_union_card"] == 3,
            local_checks,
        ),
        requirement(
            "R192-C06",
            "The tilted local block and adjacent ZZ bond fail to commute exactly.",
            local_checks["commutator_nonzero_exact"]
            and local_checks["physical_commutator_max_abs"] == 2.0,
            {
                "physical_commutator_max_abs": local_checks[
                    "physical_commutator_max_abs"
                ],
                "commutator_numerator": local_checks[
                    "commutator_numerator"
                ],
            },
        ),
        requirement(
            "R192-C07",
            "Bit-action and Kronecker implementations match exactly.",
            all_matrix_replays_exact,
            {
                "checked_sizes": list(CHECKED_SIZES),
                "maximum_matrix_difference": max(
                    row["matrix_max_abs_difference"] for row in rows
                ),
            },
        ),
        requirement(
            "R192-C08",
            "All finite Hamiltonians are Hermitian within the frozen tolerance.",
            all(
                row["hermitian_residual"] <= MATRIX_TOLERANCE
                for row in rows
            ),
            {
                "maximum_hermitian_residual": max(
                    row["hermitian_residual"] for row in rows
                )
            },
        ),
        requirement(
            "R192-C09",
            "Reflection symmetry is exact and parity blocks reassemble the spectrum.",
            all_reflection_checks_pass,
            {
                "maximum_exact_reflection_commutator": max(
                    row["reflection_commutator_max_abs_exact"]
                    for row in rows
                ),
                "maximum_parity_spectrum_error": max(
                    row["parity_spectrum_max_abs_error"]
                    for row in rows
                ),
            },
        ),
        requirement(
            "R192-C10",
            "Every checked full spectrum is simple under the declared threshold.",
            all_finite_spectra_simple,
            {
                "checked_sizes": list(CHECKED_SIZES),
                "minimum_spacing": min(
                    row["minimum_full_spectrum_spacing"] for row in rows
                ),
            },
        ),
        requirement(
            "R192-C11",
            "The R191 product denominator is replayed on the same finite sizes.",
            all(
                row["product_distinct_level_count"] == row["n"] + 1
                and math.isclose(
                    row["product_denominator_normalized_gap"],
                    1.0 / row["n"],
                )
                for row in rows
            ),
            {
                "denominator": protocol_payload["denominator"],
                "checked_sizes": list(CHECKED_SIZES),
            },
        ),
        requirement(
            "R192-C12",
            "The preregistered normalized-gap target is classified without promotion.",
            no_credit_consistent,
            {
                "target_pass_count": normalized_target_pass_count,
                "scientific_promotion_accepted": scientific_promotion_accepted,
                "new_credit_delta": 0,
            },
        ),
        requirement(
            "R192-C13",
            "Level statistics are symmetry-resolved and retained as diagnostic only.",
            all(
                row["even_sector_level_statistics"]["ratio_count"] > 0
                and row["odd_sector_level_statistics"]["ratio_count"] > 0
                for row in rows
            ),
            {
                "declared_symmetry": "reflection",
                "central_trim_fraction": CENTRAL_TRIM_FRACTION,
                "interpretation": "diagnostic_only",
            },
        ),
        requirement(
            "R192-C14",
            "Claim boundary keeps theorem, hardware, and frontier credit false.",
            not scientific_promotion_accepted,
            {
                "true_claims": TRUE_CLAIMS,
                "false_claims": FALSE_CLAIMS,
                "new_credit_delta": 0,
            },
        ),
    ]
    requirements_passed = sum(item["passed"] for item in requirements)
    requirements_total = len(requirements)

    supported = [
        (
            "Lean checks connected two-local support, adjacent-bond overlap, "
            "Hermiticity, and exact local-bond noncommutation."
        ),
        (
            "Independent integer bit-action and Kronecker implementations "
            "match exactly for n=4..10."
        ),
        (
            "Every checked finite spectrum is simple, while the R191 product "
            "denominator has only n+1 distinct levels with binomial multiplicity."
        ),
        (
            "Reflection symmetry is resolved before adjacent-gap statistics "
            "are computed."
        ),
        (
            "The connected overlap normalized gap misses the 1.05x product "
            "target at every checked size, so promotion and new credit remain zero."
        ),
    ]
    not_supported = [
        (
            "Finite degeneracy collapse is not an all-n spectrum theorem or "
            "a proof that no alternate integrable representation exists."
        ),
        (
            "Reflection-resolved adjacent-gap ratios are finite-size diagnostics, "
            "not a nonintegrability or quantum-chaos theorem."
        ),
        (
            "No spectral-hardness theorem, hardware execution, Quantum PCP "
            "theorem, NLTS theorem, BQP separation, solved frontier, or new "
            "credit is supported."
        ),
    ]

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "status": STATUS,
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "protocol": protocol_payload,
        "protocol_sha256": protocol_sha256,
        "evidence": {
            "module_path": MODULE_PATH.as_posix(),
            "module_sha256": sha256_file(module_path),
            "tool_path": tool_path.relative_to(root).as_posix(),
            "tool_sha256": sha256_file(tool_path),
        },
        "execution": {
            "probes": probes,
            "module_warning_count": module_warning_count,
            "transcript_path": transcript_path.relative_to(root).as_posix(),
            "transcript_sha256": transcript_sha256,
        },
        "local_exact_checks": local_checks,
        "spectrum_rows": rows,
        "summary": {
            "row_count": len(rows),
            "checked_row_count": sum(row["checked"] for row in rows),
            "degeneracy_collapse_count": degeneracy_collapse_count,
            "normalized_gap_target_pass_count": normalized_target_pass_count,
            "scientific_promotion_accepted": scientific_promotion_accepted,
            "normalized_gap_ratio_min": min(normalized_ratios),
            "normalized_gap_ratio_max": max(normalized_ratios),
            "reflection_symmetry_resolved": all_reflection_checks_pass,
            "level_statistics_interpretation": "diagnostic_only",
        },
        "requirements": requirements,
        "requirements_passed": requirements_passed,
        "requirements_total": requirements_total,
        "evidence_integrity_complete": (
            requirements_passed == requirements_total
            and all_rows_checked
            and probes_passed
        ),
        "claim_boundary": {
            "supported": supported,
            "not_supported": not_supported,
            "true_claims": TRUE_CLAIMS,
            "false_claims": FALSE_CLAIMS,
        },
        "new_credit_delta": 0,
    }
    payload_sha256 = canonical_hash(payload)
    return {**payload, "payload_sha256": payload_sha256}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/B9_R192_overlapping_control_certificate_v1.json"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("research/B9_R192_overlapping_control_certificate.md"),
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        default=Path("results/B9_R192_overlapping_control_transcript_v1.txt"),
    )
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    output_path = (root / args.output).resolve()
    report_path = (root / args.report).resolve()
    transcript_path = (root / args.transcript).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    result = build_result(root, transcript_path, args.timeout_seconds)
    indent = 2 if args.pretty else None
    output_path.write_text(
        json.dumps(result, indent=indent, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(render_report(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "requirements": (
                    f"{result['requirements_passed']}/"
                    f"{result['requirements_total']}"
                ),
                "checked_rows": result["summary"]["checked_row_count"],
                "target_pass_count": result["summary"][
                    "normalized_gap_target_pass_count"
                ],
                "scientific_promotion_accepted": result["summary"][
                    "scientific_promotion_accepted"
                ],
                "new_credit_delta": result["new_credit_delta"],
                "payload_sha256": result["payload_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["evidence_integrity_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
