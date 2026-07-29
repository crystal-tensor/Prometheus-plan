#!/usr/bin/env python3
"""Build and independently check the B9 R191 noncommuting-control certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np


EXPERIMENT_ID = "B9-R191-noncommuting-integrable-negative-control"
METHOD = "b9_r191_noncommuting_integrable_negative_control_v1"
STATUS = "checked_noncommuting_integrable_negative_control"
VERSION = "1.0"
FIELD = Fraction(3, 4)
SCALE = Fraction(5, 4)
CHECKED_SIZES = (4, 5, 6, 7)
REQUIRED_DEFINITIONS = [
    "pythagoreanFieldStrength",
    "pythagoreanSpectralScale",
    "tiltedLocalOperator",
    "tiltedGroundVector",
    "tiltedExcitedVector",
    "tiltedLocalEigenvalue",
    "tiltedLocalBasisMatrix",
    "zFieldOperator",
    "tiltedProductOperator",
    "integrableClusterControlOperator",
    "pythagoreanControlSummary",
]
REQUIRED_THEOREMS = [
    "tiltedLocalOperator_isHermitian",
    "tilted_ground_eigenpair",
    "tilted_excited_eigenpair",
    "tiltedLocalBasis_diagonalizes",
    "tiltedLocalOperator_spectrum",
    "pauliX_does_not_commute_with_tiltedLocalOperator",
    "tiltedLocalOperator_not_scalar_pauliX",
    "pythagorean_field_support_card",
    "pythagorean_field_support_subset_range",
    "zFieldOperator_isHermitian",
    "tiltedProductOperator_isHermitian",
    "pythagoreanControlSummary_normalized",
    "pythagorean_noncommuting_control_boundary",
]
TRUE_CLAIMS = [
    "exact_local_eigenpairs_formalized",
    "exact_local_spectrum_formalized",
    "local_noncommutation_formalized",
    "not_scalar_x_formalized",
    "finite_product_spectrum_replayed",
    "cluster_conjugation_replayed",
    "noncommuting_integrable_negative_control",
]
FALSE_CLAIMS = [
    "overlapping_noncommuting_spectrum_formalized",
    "spectral_hardness_theorem",
    "quantum_hardware_execution",
    "quantum_pcp_theorem",
    "nlts_theorem",
    "global_gap_amplification_impossibility",
    "bqp_separation",
    "solved_frontier",
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


def zero_matrix(dimension: int) -> list[list[Fraction]]:
    return [
        [Fraction(0, 1) for _ in range(dimension)]
        for _ in range(dimension)
    ]


def add_matrices(
    left: list[list[Fraction]],
    right: list[list[Fraction]],
) -> list[list[Fraction]]:
    return [
        [left[row][column] + right[row][column] for column in range(len(left))]
        for row in range(len(left))
    ]


def build_x_site_matrix(n: int, site: int) -> list[list[Fraction]]:
    dimension = 1 << n
    matrix = zero_matrix(dimension)
    for state in range(dimension):
        matrix[state ^ (1 << site)][state] = Fraction(-1, 1)
    return matrix


def build_z_site_matrix(n: int, site: int) -> list[list[Fraction]]:
    dimension = 1 << n
    matrix = zero_matrix(dimension)
    for state in range(dimension):
        sign = -1 if (state >> site) & 1 else 1
        matrix[state][state] = FIELD * sign
    return matrix


def build_x_chain_matrix(n: int) -> list[list[Fraction]]:
    matrix = zero_matrix(1 << n)
    for site in range(n):
        matrix = add_matrices(matrix, build_x_site_matrix(n, site))
    return matrix


def build_z_field_matrix(n: int) -> list[list[Fraction]]:
    matrix = zero_matrix(1 << n)
    for site in range(n):
        matrix = add_matrices(matrix, build_z_site_matrix(n, site))
    return matrix


def build_site_block_matrix(n: int, site: int) -> list[list[Fraction]]:
    return add_matrices(
        build_x_site_matrix(n, site),
        build_z_site_matrix(n, site),
    )


def cluster_phase(state: int, n: int) -> int:
    parity = sum(
        ((state >> q) & 1) * ((state >> (q + 1)) & 1)
        for q in range(max(0, n - 1))
    )
    return -1 if parity % 2 else 1


def build_cluster_matrix(n: int) -> list[list[Fraction]]:
    dimension = 1 << n
    matrix = zero_matrix(dimension)
    for state in range(dimension):
        for center in range(n):
            neighbor_phase = 1
            if center > 0 and ((state >> (center - 1)) & 1):
                neighbor_phase *= -1
            if center + 1 < n and ((state >> (center + 1)) & 1):
                neighbor_phase *= -1
            matrix[state ^ (1 << center)][state] -= neighbor_phase
    return matrix


def phase_conjugate(
    matrix: list[list[Fraction]],
    n: int,
) -> list[list[Fraction]]:
    phases = [cluster_phase(state, n) for state in range(1 << n)]
    return [
        [
            Fraction(phases[row] * phases[column], 1) * matrix[row][column]
            for column in range(1 << n)
        ]
        for row in range(1 << n)
    ]


def fraction_matvec(
    matrix: list[list[Fraction]],
    vector: list[Fraction],
) -> list[Fraction]:
    return [
        sum(
            (matrix[row][column] * vector[column] for column in range(len(vector))),
            Fraction(0, 1),
        )
        for row in range(len(vector))
    ]


def local_exact_checks() -> dict[str, Any]:
    local = [
        [FIELD, Fraction(-1, 1)],
        [Fraction(-1, 1), -FIELD],
    ]
    x = [
        [Fraction(0, 1), Fraction(1, 1)],
        [Fraction(1, 1), Fraction(0, 1)],
    ]
    ground = [Fraction(1, 1), Fraction(2, 1)]
    excited = [Fraction(2, 1), Fraction(-1, 1)]
    ground_image = fraction_matvec(local, ground)
    excited_image = fraction_matvec(local, excited)
    ground_expected = [-SCALE * value for value in ground]
    excited_expected = [SCALE * value for value in excited]
    commutator = [
        [
            sum((x[row][k] * local[k][column] for k in range(2)), Fraction())
            - sum((local[row][k] * x[k][column] for k in range(2)), Fraction())
            for column in range(2)
        ]
        for row in range(2)
    ]
    return {
        "local_matrix": [[str(value) for value in row] for row in local],
        "ground_vector": [str(value) for value in ground],
        "excited_vector": [str(value) for value in excited],
        "ground_eigenvalue": str(-SCALE),
        "excited_eigenvalue": str(SCALE),
        "ground_eigenpair_exact": ground_image == ground_expected,
        "excited_eigenpair_exact": excited_image == excited_expected,
        "basis_determinant": str(local[0][0] * local[1][1] - local[0][1] * local[1][0]),
        "commutator": [[str(value) for value in row] for row in commutator],
        "commutator_nonzero_exact": any(value != 0 for row in commutator for value in row),
        "not_scalar_x_exact": local[0][0] != 0 and local[1][1] != 0,
    }


def independent_row(n: int) -> dict[str, Any]:
    dimension = 1 << n
    x_chain = build_x_chain_matrix(n)
    z_field = build_z_field_matrix(n)
    product = add_matrices(x_chain, z_field)
    cluster_control = phase_conjugate(product, n)
    expected_cluster_control = add_matrices(build_cluster_matrix(n), z_field)
    dense_x = np.asarray(x_chain, dtype=np.float64)
    dense_z = np.asarray(z_field, dtype=np.float64)
    dense_product = np.asarray(product, dtype=np.float64)
    eigenvalues = np.linalg.eigvalsh(dense_product)
    expected = sorted(
        SCALE * (2 * label.bit_count() - n)
        for label in range(dimension)
    )
    expected_float = np.asarray([float(value) for value in expected])
    spectrum_error = float(np.max(np.abs(eigenvalues - expected_float)))
    observed_counter = Counter(round(float(value), 10) for value in eigenvalues)
    expected_counter = Counter(round(float(value), 10) for value in expected)
    binomial_counter = {
        round(float(SCALE * (2 * weight - n)), 10): math.comb(n, weight)
        for weight in range(n + 1)
    }
    site_blocks = [
        np.asarray(build_site_block_matrix(n, site), dtype=np.float64)
        for site in range(n)
    ]
    max_site_block_commutator = max(
        (
            float(np.max(np.abs(left @ right - right @ left)))
            for index, left in enumerate(site_blocks)
            for right in site_blocks[index + 1 :]
        ),
        default=0.0,
    )
    pieces_commutator = dense_x @ dense_z - dense_z @ dense_x
    pieces_commutator_max = float(np.max(np.abs(pieces_commutator)))
    ground = expected[0]
    distinct = sorted(set(expected))
    first_excited = distinct[1]
    top = expected[-1]
    gap = first_excited - ground
    width = top - ground
    row = {
        "n": n,
        "dimension": dimension,
        "ordered_spectrum_max_abs_error": spectrum_error,
        "ordered_spectrum_multiplicity_match": observed_counter == expected_counter,
        "binomial_multiplicity_match": expected_counter == binomial_counter,
        "ground_energy": str(ground),
        "first_excited_energy": str(first_excited),
        "top_energy": str(top),
        "gap": str(gap),
        "width": str(width),
        "normalized_gap": f"1/{n}",
        "x_z_piece_commutator_max_abs": pieces_commutator_max,
        "x_z_pieces_noncommuting": pieces_commutator_max > 0.0,
        "site_block_commutator_max_abs": max_site_block_commutator,
        "site_blocks_pairwise_commuting": max_site_block_commutator == 0.0,
        "not_uniform_x_scaling": product
        != [
            [SCALE * value for value in row_values]
            for row_values in x_chain
        ],
        "exact_cluster_phase_conjugation": cluster_control == expected_cluster_control,
    }
    row["checked"] = (
        row["ordered_spectrum_max_abs_error"] <= 1e-12
        and row["ordered_spectrum_multiplicity_match"]
        and row["binomial_multiplicity_match"]
        and gap == Fraction(5, 2)
        and width == Fraction(5 * n, 2)
        and gap / width == Fraction(1, n)
        and row["x_z_pieces_noncommuting"]
        and row["site_blocks_pairwise_commuting"]
        and row["not_uniform_x_scaling"]
        and row["exact_cluster_phase_conjugation"]
    )
    return row


def build_payload(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    repo_root = args.repo_root.resolve()
    module_path = (repo_root / args.lean_module).resolve()
    spectrum_path = (repo_root / args.spectrum_module).resolve()
    toolchain_path = repo_root / "lean-toolchain"
    lakefile_path = repo_root / "lakefile.lean"
    manifest_path = repo_root / "lake-manifest.json"
    source = module_path.read_text(encoding="utf-8")
    claim_boundary = {
        **{field: True for field in TRUE_CLAIMS},
        **{field: False for field in FALSE_CLAIMS},
        "new_credit_delta": 0,
    }
    protocol = {
        "experiment_id": EXPERIMENT_ID,
        "track": ["B9", "B10"],
        "target": (
            "Construct an exact local block -X+(3/4)Z that does not commute "
            "with X and is not a scalar X rescaling, then test whether its "
            "site-factorized chain remains exactly integrable after cluster-phase "
            "conjugation."
        ),
        "source_module": args.lean_module,
        "spectrum_module": args.spectrum_module,
        "pinned_toolchain": "leanprover/lean4:v4.12.0",
        "independent_oracle": (
            "Python Fraction bit-action matrices plus NumPy Hermitian eigenspectra"
        ),
        "checked_sizes": list(CHECKED_SIZES),
        "field_strength": "3/4",
        "local_spectral_scale": "5/4",
        "required_definitions": REQUIRED_DEFINITIONS,
        "required_theorems": REQUIRED_THEOREMS,
        "forbidden_source_tokens": ["sorry", "axiom"],
        "acceptance": {
            "lean_version_returncode": 0,
            "lake_version_returncode": 0,
            "module_check_returncode": 0,
            "module_check_warning_count": 0,
            "independent_row_count": len(CHECKED_SIZES),
            "requirement_pass_count": 12,
        },
        "claim_boundary": claim_boundary,
    }
    protocol_hash = canonical_hash(protocol)
    lean = resolve_executable("lean")
    lake = resolve_executable("lake")
    probes = [
        run_command(
            [lean, "--version"],
            ["lean", "--version"],
            repo_root,
            args.timeout_seconds,
        ),
        run_command(
            [lake, "--version"],
            ["lake", "--version"],
            repo_root,
            args.timeout_seconds,
        ),
        run_command(
            [lake, "env", "lean", args.lean_module],
            ["lake", "env", "lean", args.lean_module],
            repo_root,
            args.timeout_seconds,
        ),
    ]
    transcript = render_transcript(probes)
    warning_count = (
        probes[2]["stdout"] + probes[2]["stderr"]
    ).lower().count("warning:")
    local_checks = local_exact_checks()
    rows = [independent_row(n) for n in CHECKED_SIZES]
    definition_names = re.findall(
        r"(?m)^(?:noncomputable\s+)?def\s+([A-Za-z0-9_'.]+)",
        source,
    )
    theorem_names = re.findall(
        r"(?m)^(?:@\[[^\n]+\]\s+)?theorem\s+([A-Za-z0-9_']+)",
        source,
    )
    forbidden_hits = {
        token: len(re.findall(rf"\b{re.escape(token)}\b", source))
        for token in protocol["forbidden_source_tokens"]
    }
    all_rows_checked = (
        len(rows) == len(CHECKED_SIZES)
        and all(row["checked"] for row in rows)
    )
    requirements = [
        requirement(
            "R1",
            "Protocol is content-addressed and broad frontier claims remain false",
            len(protocol_hash) == 64
            and all(claim_boundary[field] is False for field in FALSE_CLAIMS)
            and claim_boundary["new_credit_delta"] == 0,
            {"protocol_hash": protocol_hash, "claim_boundary": claim_boundary},
        ),
        requirement(
            "R2",
            "Pinned Lean project and both formal source layers exist",
            toolchain_path.exists()
            and toolchain_path.read_text(encoding="utf-8").strip()
            == "leanprover/lean4:v4.12.0"
            and lakefile_path.exists()
            and manifest_path.exists()
            and spectrum_path.exists(),
            {
                "lean_toolchain_sha256": sha256_file(toolchain_path),
                "lakefile_sha256": sha256_file(lakefile_path),
                "lake_manifest_sha256": sha256_file(manifest_path),
                "spectrum_module_sha256": sha256_file(spectrum_path),
            },
        ),
        requirement(
            "R3",
            "The control source contains no sorry or axiom escape hatch",
            forbidden_hits["sorry"] == 0 and forbidden_hits["axiom"] == 0,
            {"forbidden_hits": forbidden_hits},
        ),
        requirement(
            "R4",
            "All declared control definitions exist",
            all(name in definition_names for name in REQUIRED_DEFINITIONS),
            {
                "required_definitions": REQUIRED_DEFINITIONS,
                "definition_names": definition_names,
            },
        ),
        requirement(
            "R5",
            "All declared exact control theorems exist",
            all(name in theorem_names for name in REQUIRED_THEOREMS),
            {
                "required_theorems": REQUIRED_THEOREMS,
                "theorem_names": theorem_names,
            },
        ),
        requirement(
            "R6",
            "Local eigenpairs and noncommutation replay exactly over rationals",
            local_checks["ground_eigenpair_exact"]
            and local_checks["excited_eigenpair_exact"]
            and local_checks["commutator_nonzero_exact"],
            local_checks,
        ),
        requirement(
            "R7",
            "The local control is not a scalar multiple of Pauli X",
            local_checks["not_scalar_x_exact"],
            local_checks,
        ),
        requirement(
            "R8",
            "Finite product spectra and binomial multiplicities match",
            all(
                row["ordered_spectrum_max_abs_error"] <= 1e-12
                and row["ordered_spectrum_multiplicity_match"]
                and row["binomial_multiplicity_match"]
                for row in rows
            ),
            {"rows": rows, "eigenvalue_tolerance": 1e-12},
        ),
        requirement(
            "R9",
            "Raw gap, width, and normalized ratio match 5/2, 5n/2, and 1/n",
            all_rows_checked,
            {"rows": rows},
        ),
        requirement(
            "R10",
            "X and Z pieces do not commute while grouped site blocks do",
            all(
                row["x_z_pieces_noncommuting"]
                and row["site_blocks_pairwise_commuting"]
                for row in rows
            ),
            {"rows": rows},
        ),
        requirement(
            "R11",
            "Exact cluster-phase conjugation preserves the Z field and transfers X",
            all(row["exact_cluster_phase_conjugation"] for row in rows),
            {"rows": rows},
        ),
        requirement(
            "R12",
            "Lean, Lake, and NoncommutingControl return zero with no warnings",
            all(
                probe["returncode"] == 0 and not probe["timed_out"]
                for probe in probes
            )
            and "Lean (version 4.12.0" in probes[0]["stdout"]
            and "Lake version" in probes[1]["stdout"]
            and warning_count == 0,
            {
                "returncodes": [probe["returncode"] for probe in probes],
                "timed_out": [probe["timed_out"] for probe in probes],
                "warning_count": warning_count,
            },
        ),
    ]
    passed = sum(row["passed"] for row in requirements)
    failed_ids = [
        row["requirement_id"] for row in requirements if not row["passed"]
    ]
    transcript_hash = sha256_bytes(transcript.encode("utf-8"))
    payload = {
        "version": VERSION,
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "status": STATUS if not failed_ids else "noncommuting_control_rejected",
        "last_updated": "2026-07-29",
        "protocol": protocol,
        "protocol_hash": protocol_hash,
        "source": {
            "lean_module": args.lean_module,
            "lean_module_sha256": sha256_file(module_path),
            "spectrum_module": args.spectrum_module,
            "spectrum_module_sha256": sha256_file(spectrum_path),
            "lean_toolchain_sha256": sha256_file(toolchain_path),
            "lakefile_sha256": sha256_file(lakefile_path),
            "lake_manifest_sha256": sha256_file(manifest_path),
            "definition_names": definition_names,
            "theorem_names": theorem_names,
            "forbidden_hits": forbidden_hits,
        },
        "execution": {
            "probes": probes,
            "transcript_path": str(args.transcript),
            "transcript_sha256": transcript_hash,
            "module_warning_count": warning_count,
        },
        "local_exact_checks": local_checks,
        "independent_spectrum_rows": rows,
        "requirements": requirements,
        "summary": {
            "requirement_count": len(requirements),
            "requirements_passed": passed,
            "requirements_failed": len(requirements) - passed,
            "failed_requirement_ids": failed_ids,
            **{field: not failed_ids for field in TRUE_CLAIMS},
            **{field: False for field in FALSE_CLAIMS},
            "new_credit_delta": 0,
        },
        "claim_boundary": {
            "supported": [
                "Lean checks the exact local eigenpairs, local spectrum, Hermiticity, noncommutation with X, and non-scalar-X boundary.",
                "Independent n=4,5,6,7 product spectra match (5/4)(2k-n) with binomial multiplicities.",
                "The raw gap is 5/2, width is 5n/2, and normalized gap remains 1/n.",
                "The X and Z pieces do not commute, but regrouping by disjoint sites exposes pairwise-commuting local blocks.",
                "Exact cluster-phase conjugation produces the cluster-stabilizer Hamiltonian plus the same longitudinal Z field.",
            ],
            "not_supported": [
                "The all-n product spectrum is independently replayed at finite sizes but is not yet formalized as a Lean tensor-product theorem.",
                "This is a negative control showing that noncommutation alone does not imply hardness; overlapping noncommuting terms remain untested.",
                "No spectral-hardness theorem, hardware execution, Quantum PCP theorem, NLTS theorem, BQP separation, solved frontier, or new credit is supported.",
            ],
        },
    }
    payload["payload_sha256"] = canonical_hash(payload)
    return payload, transcript


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = "\n".join(
        "| {n} | {dimension} | {gap} | {width} | {normalized} | "
        "{spectrum_error:.3e} | {commuting} | {checked} |".format(
            n=row["n"],
            dimension=row["dimension"],
            gap=row["gap"],
            width=row["width"],
            normalized=row["normalized_gap"],
            spectrum_error=row["ordered_spectrum_max_abs_error"],
            commuting=row["site_blocks_pairwise_commuting"],
            checked=row["checked"],
        )
        for row in payload["independent_spectrum_rows"]
    )
    supported = "\n".join(
        f"- {item}" for item in payload["claim_boundary"]["supported"]
    )
    not_supported = "\n".join(
        f"- {item}" for item in payload["claim_boundary"]["not_supported"]
    )
    return f"""# B9 R191 Noncommuting Integrable Negative Control

## Verdict

- Status: `{payload['status']}`
- Requirements: `{summary['requirements_passed']}/{summary['requirement_count']}`
- Protocol hash: `{payload['protocol_hash']}`
- Payload hash: `{payload['payload_sha256']}`
- Transcript hash: `{payload['execution']['transcript_sha256']}`
- Lean module warnings: `{payload['execution']['module_warning_count']}`
- New credit delta: `{summary['new_credit_delta']}`

## Exact Local Control

The local block is `A = -X + (3/4)Z`. Lean and an independent rational
calculation agree that `[1,2]` and `[2,-1]` are exact eigenvectors with
eigenvalues `-5/4` and `+5/4`. The commutator `[X,A]` is nonzero, and the
nonzero diagonal entries prove that `A` is not any scalar multiple of `X`.

## Independent Product Replay

| n | dimension | gap | width | normalized gap | spectrum error | site blocks commute | checked |
|---:|---:|---:|---:|---:|---:|:---:|:---:|
{rows}

The finite oracle builds exact rational bit-action matrices. NumPy is used
only to compare the complete ordered Hermitian eigenspectrum. Although the
global `X` and `Z` sums do not commute, regrouping them as one tilted block
per site exposes a pairwise-commuting tensor-product structure.

## Supported

{supported}

## Not Supported

{not_supported}

## Next Gate

Formalize the all-`n` tensor-product spectrum in Lean, then introduce the
smallest overlapping noncommuting term that destroys the disjoint-site block
decomposition. Any next claim must retain explicit locality, spectrum,
denominator, and no-credit boundaries.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--lean-module",
        default="B9/ClusterStabilizer/NoncommutingControl.lean",
    )
    parser.add_argument(
        "--spectrum-module",
        default="B9/ClusterStabilizer/SpectrumFormula.lean",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B9_R191_noncommuting_control_certificate_v1.json"),
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        default=Path("results/B9_R191_noncommuting_control_transcript_v1.txt"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B9_R191_noncommuting_control_certificate.md"),
    )
    parser.add_argument("--timeout-seconds", type=int, default=120)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    args.json_output = (repo_root / args.json_output).resolve()
    args.transcript = (repo_root / args.transcript).resolve()
    args.markdown_output = (repo_root / args.markdown_output).resolve()
    payload, transcript = build_payload(args)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.transcript.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.transcript.write_text(transcript, encoding="utf-8")
    args.json_output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "requirements": (
                    f"{payload['summary']['requirements_passed']}/"
                    f"{payload['summary']['requirement_count']}"
                ),
                "payload_sha256": payload["payload_sha256"],
                "transcript_sha256": payload["execution"]["transcript_sha256"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            sort_keys=True,
        )
    )
    return 0 if payload["summary"]["requirements_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
