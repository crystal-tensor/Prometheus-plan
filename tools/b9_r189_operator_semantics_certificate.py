#!/usr/bin/env python3
"""Check the B9 matrix-operator semantics and spectrum-scaling certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np


EXPERIMENT_ID = "B9-R189-open-chain-operator-semantics-certificate"
METHOD = "b9_r189_open_chain_operator_semantics_certificate_v1"
STATUS = (
    "checked_all_n_matrix_operator_and_spectrum_set_scaling_complete_"
    "all_n_ordered_spectrum_formula_open"
)
VERSION = "1.0"
SCALE = Fraction(27, 20)
CHECKED_SIZES = (4, 5, 6)
REQUIRED_DEFINITIONS = [
    "pauliI",
    "pauliX",
    "pauliZ",
    "pauliWordMatrix",
    "openChainSitePauli",
    "openChainPauliWord",
    "openChainTermOperator",
    "reweightedOpenChainTermOperator",
    "openChainOperator",
    "reweightedOpenChainOperator",
    "uniformScaleComplex",
]
REQUIRED_THEOREMS = [
    "qubitBasis_card",
    "pauliI_isHermitian",
    "pauliX_isHermitian",
    "pauliZ_isHermitian",
    "pauliWordMatrix_isHermitian",
    "openChainSitePauli_at_center",
    "openChainSitePauli_at_zSite",
    "openChainSitePauli_away_from_term",
    "openChainSitePauli_isHermitian",
    "openChainPauliWord_isHermitian",
    "real_coefficient_smul_isHermitian",
    "openChainTermOperator_isHermitian",
    "reweightedOpenChainTermOperator_isHermitian",
    "openChainOperator_isHermitian",
    "reweightedOpenChainOperator_isHermitian",
    "uniformScaleComplex_nonzero",
    "reweighted_term_operator_eq_smul",
    "reweighted_operator_eq_smul",
    "reweighted_operator_spectrum_eq_smul",
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


def build_open_chain_matrix(n: int, scale: Fraction) -> list[list[Fraction]]:
    dimension = 1 << n
    matrix = [
        [Fraction(0, 1) for _ in range(dimension)]
        for _ in range(dimension)
    ]
    for basis_state in range(dimension):
        for center in range(n):
            phase = 1
            if center > 0 and ((basis_state >> (center - 1)) & 1):
                phase *= -1
            if center + 1 < n and ((basis_state >> (center + 1)) & 1):
                phase *= -1
            output_state = basis_state ^ (1 << center)
            matrix[output_state][basis_state] += -scale * phase
    return matrix


def matrix_is_hermitian(matrix: list[list[Fraction]]) -> bool:
    dimension = len(matrix)
    return all(
        matrix[row][column] == matrix[column][row]
        for row in range(dimension)
        for column in range(dimension)
    )


def matrix_scale_exact(
    before: list[list[Fraction]],
    after: list[list[Fraction]],
) -> bool:
    return all(
        after[row][column] == SCALE * before[row][column]
        for row in range(len(before))
        for column in range(len(before))
    )


def expected_spectrum(n: int, scale: Fraction) -> list[Fraction]:
    values: list[Fraction] = []
    for excitations in range(n + 1):
        eigenvalue = scale * Fraction(-n + 2 * excitations, 1)
        values.extend([eigenvalue] * math.comb(n, excitations))
    return sorted(values)


def unique_gap(values: list[Fraction]) -> Fraction:
    unique_values = sorted(set(values))
    return min(
        upper - lower
        for lower, upper in zip(unique_values, unique_values[1:])
    )


def fraction_text(value: Fraction) -> str:
    return (
        str(value.numerator)
        if value.denominator == 1
        else f"{value.numerator}/{value.denominator}"
    )


def independent_operator_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for n in CHECKED_SIZES:
        before = build_open_chain_matrix(n, Fraction(1, 1))
        after = build_open_chain_matrix(n, SCALE)
        before_expected = expected_spectrum(n, Fraction(1, 1))
        after_expected = expected_spectrum(n, SCALE)
        before_dense = np.asarray(before, dtype=np.float64)
        after_dense = np.asarray(after, dtype=np.float64)
        before_eigenvalues = np.linalg.eigvalsh(before_dense)
        after_eigenvalues = np.linalg.eigvalsh(after_dense)
        before_expected_float = np.asarray(
            [float(value) for value in before_expected],
            dtype=np.float64,
        )
        after_expected_float = np.asarray(
            [float(value) for value in after_expected],
            dtype=np.float64,
        )
        before_gap = unique_gap(before_expected)
        after_gap = unique_gap(after_expected)
        before_width = before_expected[-1] - before_expected[0]
        after_width = after_expected[-1] - after_expected[0]
        nonzero_entries_before = sum(
            value != 0 for row in before for value in row
        )
        nonzero_entries_after = sum(
            value != 0 for row in after for value in row
        )
        row = {
            "n": n,
            "dimension": len(before),
            "expected_dimension": 2**n,
            "term_count": n,
            "nonzero_entries_before": nonzero_entries_before,
            "nonzero_entries_after": nonzero_entries_after,
            "before_hermitian_exact": matrix_is_hermitian(before),
            "after_hermitian_exact": matrix_is_hermitian(after),
            "operator_scaling_exact": matrix_scale_exact(before, after),
            "before_spectrum_formula": [
                fraction_text(value) for value in sorted(set(before_expected))
            ],
            "after_spectrum_formula": [
                fraction_text(value) for value in sorted(set(after_expected))
            ],
            "before_eigenvalue_max_abs_error": float(
                np.max(np.abs(before_eigenvalues - before_expected_float))
            ),
            "after_eigenvalue_max_abs_error": float(
                np.max(np.abs(after_eigenvalues - after_expected_float))
            ),
            "before_gap": fraction_text(before_gap),
            "after_gap": fraction_text(after_gap),
            "gap_scale_ratio": fraction_text(after_gap / before_gap),
            "before_width": fraction_text(before_width),
            "after_width": fraction_text(after_width),
            "width_scale_ratio": fraction_text(after_width / before_width),
            "before_normalized_gap": fraction_text(before_gap / before_width),
            "after_normalized_gap": fraction_text(after_gap / after_width),
        }
        row["checked"] = (
            row["dimension"] == row["expected_dimension"]
            and nonzero_entries_before > 0
            and nonzero_entries_after == nonzero_entries_before
            and row["before_hermitian_exact"]
            and row["after_hermitian_exact"]
            and row["operator_scaling_exact"]
            and row["before_eigenvalue_max_abs_error"] <= 1e-12
            and row["after_eigenvalue_max_abs_error"] <= 1e-12
            and after_gap == SCALE * before_gap
            and after_width == SCALE * before_width
            and after_gap / after_width == before_gap / before_width
        )
        rows.append(row)
    return rows


def build_payload(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    repo_root = args.repo_root.resolve()
    module_path = (repo_root / args.lean_module).resolve()
    structure_path = (repo_root / args.structure_module).resolve()
    r187_path = (repo_root / args.r187_module).resolve()
    toolchain_path = repo_root / "lean-toolchain"
    lakefile_path = repo_root / "lakefile.lean"
    manifest_path = repo_root / "lake-manifest.json"
    source = module_path.read_text(encoding="utf-8")

    protocol = {
        "experiment_id": EXPERIMENT_ID,
        "track": ["B9", "B10"],
        "target": (
            "Interpret the R188 all-n open-chain terms as explicit 2^n by 2^n "
            "complex Pauli-word matrices; prove term and Hamiltonian Hermiticity, "
            "prove exact 27/20 operator scaling, and derive exact spectrum-set "
            "scaling without assuming an ordered spectral-gap formula."
        ),
        "source_module": args.lean_module,
        "structure_module": args.structure_module,
        "r187_source_module": args.r187_module,
        "pinned_toolchain": "leanprover/lean4:v4.12.0",
        "independent_oracle": (
            "Python Fraction bit-action reconstruction plus NumPy eigvalsh"
        ),
        "checked_sizes": list(CHECKED_SIZES),
        "uniform_scale": fraction_text(SCALE),
        "required_definitions": REQUIRED_DEFINITIONS,
        "required_theorems": REQUIRED_THEOREMS,
        "forbidden_source_tokens": ["sorry", "axiom"],
        "acceptance": {
            "lean_version_returncode": 0,
            "lake_version_returncode": 0,
            "module_check_returncode": 0,
            "module_check_warning_count": 0,
            "independent_row_count": len(CHECKED_SIZES),
            "requirement_pass_count": 13,
        },
        "claim_boundary": {
            "all_n_matrix_operator_semantics": True,
            "all_n_hermitian_proof": True,
            "all_n_operator_scaling_identity": True,
            "all_n_spectrum_set_scaling": True,
            "finite_ordered_spectra_independently_computed": True,
            "all_n_ordered_spectrum_formula_formalized": False,
            "all_n_spectral_gap_formula_formalized": False,
            "quantum_hardware_execution": False,
            "quantum_pcp_theorem": False,
            "nlts_theorem": False,
            "global_gap_amplification_impossibility": False,
            "bqp_separation": False,
            "new_credit_delta": 0,
        },
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
    compile_output = probes[2]["stdout"] + probes[2]["stderr"]
    warning_count = compile_output.lower().count("warning:")
    rows = independent_operator_rows()

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
    hermitian_binding = all(
        token in source
        for token in [
            "Matrix.IsHermitian.ext",
            "pauliWordMatrix_isHermitian",
            "openChainOperator_isHermitian",
            "reweightedOpenChainOperator_isHermitian",
        ]
    )
    operator_binding = all(
        token in source
        for token in [
            "openChainHamiltonian n i",
            "reweightedOpenChainHamiltonian n i",
            "openChainPauliWord n i",
            "reweighted_operator_eq_smul",
        ]
    )
    spectrum_binding = all(
        token in source
        for token in [
            "spectrum Complex (reweightedOpenChainOperator n)",
            "spectrum Complex (openChainOperator n)",
            "spectrum.unit_smul_eq_smul",
            "Units.mk0 uniformScaleComplex uniformScaleComplex_nonzero",
        ]
    )
    all_rows_checked = len(rows) == len(CHECKED_SIZES) and all(
        row["checked"] for row in rows
    )
    dimensions_checked = all(
        row["dimension"] == 2 ** row["n"] for row in rows
    )
    hermitian_checked = all(
        row["before_hermitian_exact"] and row["after_hermitian_exact"]
        for row in rows
    )
    operator_scaling_checked = all(
        row["operator_scaling_exact"] for row in rows
    )
    spectrum_checked = all(
        row["before_eigenvalue_max_abs_error"] <= 1e-12
        and row["after_eigenvalue_max_abs_error"] <= 1e-12
        for row in rows
    )
    gap_width_checked = all(
        row["gap_scale_ratio"] == fraction_text(SCALE)
        and row["width_scale_ratio"] == fraction_text(SCALE)
        and row["before_normalized_gap"] == row["after_normalized_gap"]
        for row in rows
    )
    broad_claims_false = all(
        protocol["claim_boundary"][key] is False
        for key in [
            "all_n_ordered_spectrum_formula_formalized",
            "all_n_spectral_gap_formula_formalized",
            "quantum_hardware_execution",
            "quantum_pcp_theorem",
            "nlts_theorem",
            "global_gap_amplification_impossibility",
            "bqp_separation",
        ]
    )
    requirements = [
        requirement(
            "R1",
            "Protocol is content-addressed and broad frontier claims remain false",
            len(protocol_hash) == 64
            and broad_claims_false
            and protocol["claim_boundary"]["new_credit_delta"] == 0,
            {
                "protocol_hash": protocol_hash,
                "claim_boundary": protocol["claim_boundary"],
            },
        ),
        requirement(
            "R2",
            "Pinned Lean project and all three formal source layers exist",
            toolchain_path.exists()
            and toolchain_path.read_text(encoding="utf-8").strip()
            == "leanprover/lean4:v4.12.0"
            and lakefile_path.exists()
            and manifest_path.exists()
            and structure_path.exists()
            and r187_path.exists(),
            {
                "lean_toolchain_sha256": sha256_file(toolchain_path),
                "lakefile_sha256": sha256_file(lakefile_path),
                "lake_manifest_sha256": sha256_file(manifest_path),
                "structure_module_sha256": sha256_file(structure_path),
                "r187_module_sha256": sha256_file(r187_path),
            },
        ),
        requirement(
            "R3",
            "The operator-semantics source contains no sorry or axiom escape hatch",
            forbidden_hits["sorry"] == 0 and forbidden_hits["axiom"] == 0,
            {"forbidden_hits": forbidden_hits},
        ),
        requirement(
            "R4",
            "All declared Pauli, word, term, and Hamiltonian definitions are present",
            all(name in definition_names for name in REQUIRED_DEFINITIONS),
            {
                "required_definitions": REQUIRED_DEFINITIONS,
                "definition_names": definition_names,
            },
        ),
        requirement(
            "R5",
            "All declared dimension, semantic, Hermitian, scaling, and spectrum theorems are present",
            all(name in theorem_names for name in REQUIRED_THEOREMS),
            {
                "required_theorems": REQUIRED_THEOREMS,
                "theorem_names": theorem_names,
            },
        ),
        requirement(
            "R6",
            "The formal source binds R188 terms to explicit Pauli-word matrix operators",
            operator_binding,
            {"operator_binding_found": operator_binding},
        ),
        requirement(
            "R7",
            "The formal source proves local words and both Hamiltonians Hermitian",
            hermitian_binding,
            {"hermitian_binding_found": hermitian_binding},
        ),
        requirement(
            "R8",
            "The formal source derives spectrum-set scaling from exact operator scaling",
            spectrum_binding,
            {"spectrum_binding_found": spectrum_binding},
        ),
        requirement(
            "R9",
            "Independent matrices have exactly 2^n dimensions and nonzero content",
            dimensions_checked
            and all(row["nonzero_entries_before"] > 0 for row in rows),
            {"rows": rows},
        ),
        requirement(
            "R10",
            "Independent Fraction matrices are exactly Hermitian before and after reweighting",
            hermitian_checked,
            {"rows": rows},
        ),
        requirement(
            "R11",
            "Independent Fraction matrices satisfy the exact 27/20 operator identity",
            operator_scaling_checked,
            {"rows": rows},
        ),
        requirement(
            "R12",
            "Independent eigenspectra match the open-chain formula and preserve normalized gap",
            spectrum_checked and gap_width_checked and all_rows_checked,
            {"rows": rows, "eigenvalue_tolerance": 1e-12},
        ),
        requirement(
            "R13",
            "Lean, Lake, and the operator module return zero with no module warnings",
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
        "status": STATUS if not failed_ids else "operator_semantics_certificate_rejected",
        "last_updated": "2026-07-29",
        "protocol": protocol,
        "protocol_hash": protocol_hash,
        "source": {
            "lean_module": args.lean_module,
            "lean_module_sha256": sha256_file(module_path),
            "structure_module": args.structure_module,
            "structure_module_sha256": sha256_file(structure_path),
            "r187_module": args.r187_module,
            "r187_module_sha256": sha256_file(r187_path),
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
        "independent_operator_rows": rows,
        "requirements": requirements,
        "summary": {
            "requirement_count": len(requirements),
            "requirements_passed": passed,
            "requirements_failed": len(requirements) - passed,
            "failed_requirement_ids": failed_ids,
            "all_n_matrix_operator_semantics": not failed_ids,
            "all_n_hermitian_proof": not failed_ids,
            "all_n_operator_scaling_identity": not failed_ids,
            "all_n_spectrum_set_scaling": not failed_ids,
            "finite_ordered_spectra_independently_computed": not failed_ids,
            "all_n_ordered_spectrum_formula_formalized": False,
            "all_n_spectral_gap_formula_formalized": False,
            "quantum_hardware_execution": False,
            "quantum_pcp_theorem": False,
            "nlts_theorem": False,
            "global_gap_amplification_impossibility": False,
            "bqp_separation": False,
            "new_credit_delta": 0,
        },
        "claim_boundary": {
            "supported": [
                "Lean interprets every R188 open-chain term as a 2^n-dimensional complex Pauli-word matrix.",
                "Lean proves every local Pauli word, term operator, and summed Hamiltonian Hermitian.",
                "Lean proves the independently defined reweighted Hamiltonian equals (27/20) times the original operator.",
                "Lean derives exact complex spectrum-set scaling from the operator identity and a nonzero unit.",
                "An independent Fraction bit-action oracle exactly reproduces Hermiticity and operator scaling for n=4,5,6.",
                "Independent NumPy eigenspectra match the finite open-chain formula and show unchanged normalized gap for n=4,5,6.",
            ],
            "not_supported": [
                "The ordered all-n spectrum formula and all-n spectral-gap formula are not yet formalized in Lean.",
                "Finite NumPy rows are cross-checks, not a replacement for the remaining all-n ordered-spectrum proof.",
                "No quantum hardware execution, Quantum PCP theorem, NLTS theorem, global no-go theorem, BQP separation, solved frontier, or new credit is supported.",
            ],
        },
    }
    payload["payload_sha256"] = canonical_hash(payload)
    return payload, transcript


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    row_lines = "\n".join(
        "| {n} | {dimension} | {entries} | {gap_before} -> {gap_after} | "
        "{width_before} -> {width_after} | {normalized} | {checked} |".format(
            n=row["n"],
            dimension=row["dimension"],
            entries=row["nonzero_entries_before"],
            gap_before=row["before_gap"],
            gap_after=row["after_gap"],
            width_before=row["before_width"],
            width_after=row["after_width"],
            normalized=row["before_normalized_gap"],
            checked=row["checked"],
        )
        for row in payload["independent_operator_rows"]
    )
    supported = "\n".join(
        f"- {item}" for item in payload["claim_boundary"]["supported"]
    )
    not_supported = "\n".join(
        f"- {item}" for item in payload["claim_boundary"]["not_supported"]
    )
    return f"""# B9 R189 Operator-Semantics Certificate

## Verdict

- Status: `{payload['status']}`
- Requirements: `{summary['requirements_passed']}/{summary['requirement_count']}`
- Protocol hash: `{payload['protocol_hash']}`
- Payload hash: `{payload['payload_sha256']}`
- Transcript hash: `{payload['execution']['transcript_sha256']}`
- Lean module warnings: `{payload['execution']['module_warning_count']}`
- New credit delta: `{summary['new_credit_delta']}`

## Formal Result

Lean now interprets the R188 open-chain support object as an explicit complex
matrix on the `2^n` computational basis. It proves all local words, term
operators, and summed Hamiltonians Hermitian. The independently defined
reweighted Hamiltonian is exactly `(27/20) • H`, and its full complex spectrum
set is exactly `(27/20) • spectrum(H)`.

## Independent Finite Oracle

| n | dimension | nonzero entries | gap | width | normalized gap | checked |
|---:|---:|---:|---:|---:|---:|---|
{row_lines}

The independent path rebuilds each matrix from bit flips and neighboring
`Z` phases with Python `Fraction`; NumPy is used only for the eigenspectrum
cross-check.

## Supported

{supported}

## Not Supported

{not_supported}

## Next Gate

Formalize the ordered all-n eigenvalue multiset, including binomial
multiplicities, from the commuting independent stabilizer generators. Then
derive the all-n raw gap, width, and normalized gap from that ordered spectrum
inside Lean rather than from finite NumPy rows.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--lean-module",
        default="B9/ClusterStabilizer/OperatorSemantics.lean",
    )
    parser.add_argument(
        "--structure-module",
        default="B9/ClusterStabilizer/OpenChainHamiltonian.lean",
    )
    parser.add_argument(
        "--r187-module",
        default="B9/ClusterStabilizer/WidthLocality.lean",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "results/B9_R189_open_chain_operator_semantics_certificate_v1.json"
        ),
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        default=Path(
            "results/B9_R189_open_chain_operator_semantics_transcript_v1.txt"
        ),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B9_R189_operator_semantics_certificate.md"),
    )
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload, transcript = build_payload(args)
    markdown = render_markdown(payload)
    for path in [args.output, args.transcript, args.markdown_output]:
        path.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            payload,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    args.transcript.write_text(transcript, encoding="utf-8")
    args.markdown_output.write_text(markdown, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "requirements_passed": payload["summary"]["requirements_passed"],
                "requirement_count": payload["summary"]["requirement_count"],
                "protocol_hash": payload["protocol_hash"],
                "payload_hash": payload["payload_sha256"],
                "transcript_hash": payload["execution"]["transcript_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0 if payload["summary"]["requirements_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
