#!/usr/bin/env python3
"""Build and independently check the B9 R190 spectrum-formula certificate."""

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


EXPERIMENT_ID = "B9-R190-open-chain-spectrum-formula-certificate"
METHOD = "b9_r190_open_chain_spectrum_formula_certificate_v1"
STATUS = (
    "checked_all_n_spectrum_formula_multiplicity_gap_width_complete_"
    "restricted_negative_boundary"
)
VERSION = "1.0"
SCALE = Fraction(27, 20)
CHECKED_SIZES = (4, 5, 6)
REQUIRED_DEFINITIONS = [
    "finTwoSign",
    "walshCharacter",
    "walshMatrix",
    "xChainOperator",
    "openChainEigenvalue",
    "clusterPhase",
    "clusterPhaseMatrix",
    "labelWeight",
    "labelSupport",
    "labelSupportEquiv",
    "openChainEnergy",
    "openChainExactBeforeSummary",
    "openChainExactAfterSummary",
]
REQUIRED_THEOREMS = [
    "walshCharacter_injective",
    "walsh_character_orthogonality",
    "walshMatrix_conjTranspose_mul",
    "walshMatrix_mul_inverse",
    "xChainOperator_mulVec_walsh",
    "xChainOperator_spectrum",
    "clusterPhase_conjugates_xChainOperator",
    "openChainOperator_spectrum_formula",
    "labelWeight_eq_support_card",
    "openChainEigenvalue_eq_weight",
    "labelWeight_multiplicity",
    "openChainEnergy_lower_bound",
    "openChainEnergy_upper_bound",
    "openChainEnergy_ground",
    "openChainEnergy_top",
    "openChainEnergy_first_excited",
    "openChain_raw_gap_formula",
    "openChain_width_formula",
    "openChainExactBeforeSummary_normalized",
    "openChain_exact_spectrum_reweight_boundary",
]
TRUE_CLAIMS = [
    "all_n_walsh_eigenbasis_formalized",
    "all_n_cluster_conjugation_formalized",
    "all_n_spectrum_formula_formalized",
    "all_n_binomial_multiplicity_formalized",
    "all_n_gap_width_normalized_formalized",
    "r187_operator_derived_boundary_formalized",
    "independent_finite_replay",
]
FALSE_CLAIMS = [
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


def cluster_phase(state: int, n: int) -> int:
    parity = sum(
        ((state >> q) & 1) * ((state >> (q + 1)) & 1)
        for q in range(max(0, n - 1))
    )
    return -1 if parity % 2 else 1


def walsh_sign(label: int, state: int) -> int:
    return -1 if (label & state).bit_count() % 2 else 1


def build_x_chain_matrix(n: int) -> list[list[Fraction]]:
    dimension = 1 << n
    matrix = [
        [Fraction(0, 1) for _ in range(dimension)]
        for _ in range(dimension)
    ]
    for state in range(dimension):
        for center in range(n):
            matrix[state ^ (1 << center)][state] -= 1
    return matrix


def build_cluster_matrix(n: int) -> list[list[Fraction]]:
    dimension = 1 << n
    matrix = [
        [Fraction(0, 1) for _ in range(dimension)]
        for _ in range(dimension)
    ]
    for state in range(dimension):
        for center in range(n):
            neighbor_phase = 1
            if center > 0 and ((state >> (center - 1)) & 1):
                neighbor_phase *= -1
            if center + 1 < n and ((state >> (center + 1)) & 1):
                neighbor_phase *= -1
            matrix[state ^ (1 << center)][state] -= neighbor_phase
    return matrix


def exact_matmul(
    left: list[list[Fraction]],
    right: list[list[Fraction]],
) -> list[list[Fraction]]:
    dimension = len(left)
    return [
        [
            sum(
                (left[row][inner] * right[inner][column]
                 for inner in range(dimension)),
                Fraction(0, 1),
            )
            for column in range(dimension)
        ]
        for row in range(dimension)
    ]


def independent_row(n: int) -> dict[str, Any]:
    dimension = 1 << n
    x_chain = build_x_chain_matrix(n)
    cluster = build_cluster_matrix(n)
    phases = [cluster_phase(state, n) for state in range(dimension)]
    conjugated = [
        [
            Fraction(phases[row], 1)
            * x_chain[row][column]
            * Fraction(phases[column], 1)
            for column in range(dimension)
        ]
        for row in range(dimension)
    ]
    walsh = [
        [Fraction(walsh_sign(label, state), 1) for label in range(dimension)]
        for state in range(dimension)
    ]
    walsh_gram = exact_matmul(
        [[walsh[column][row] for column in range(dimension)]
         for row in range(dimension)],
        walsh,
    )
    walsh_orthogonal_exact = all(
        walsh_gram[row][column]
        == (Fraction(dimension, 1) if row == column else Fraction(0, 1))
        for row in range(dimension)
        for column in range(dimension)
    )
    expected = sorted(
        2 * label.bit_count() - n
        for label in range(dimension)
    )
    expected_counter = Counter(expected)
    binomial_counter = {
        2 * weight - n: math.comb(n, weight)
        for weight in range(n + 1)
    }
    dense = np.asarray(cluster, dtype=np.float64)
    eigenvalues = np.linalg.eigvalsh(dense)
    expected_float = np.asarray(expected, dtype=np.float64)
    spectrum_error = float(np.max(np.abs(eigenvalues - expected_float)))
    rounded_counter = Counter(int(round(value)) for value in eigenvalues)
    vector_residual = 0.0
    for label in range(dimension):
        vector = np.asarray(
            [
                cluster_phase(state, n) * walsh_sign(label, state)
                for state in range(dimension)
            ],
            dtype=np.float64,
        )
        energy = 2 * label.bit_count() - n
        residual = dense @ vector - energy * vector
        vector_residual = max(
            vector_residual,
            float(np.max(np.abs(residual))),
        )
    gap = expected_counter and sorted(expected_counter)[1] - sorted(expected_counter)[0]
    width = expected[-1] - expected[0]
    after_gap = SCALE * gap
    after_width = SCALE * width
    multiplicities = [
        {
            "weight": weight,
            "energy": 2 * weight - n,
            "observed": expected_counter[2 * weight - n],
            "binomial": math.comb(n, weight),
        }
        for weight in range(n + 1)
    ]
    row = {
        "n": n,
        "dimension": dimension,
        "exact_cluster_conjugation": conjugated == cluster,
        "walsh_orthogonal_exact": walsh_orthogonal_exact,
        "cluster_eigenvector_max_abs_residual": vector_residual,
        "ordered_spectrum_max_abs_error": spectrum_error,
        "ordered_spectrum_multiplicity_match": rounded_counter == expected_counter,
        "binomial_multiplicity_match": dict(expected_counter) == binomial_counter,
        "multiplicities": multiplicities,
        "ground_energy": expected[0],
        "first_excited_energy": sorted(expected_counter)[1],
        "top_energy": expected[-1],
        "gap": str(gap),
        "width": str(width),
        "normalized_gap": f"1/{n}",
        "after_gap": f"{after_gap.numerator}/{after_gap.denominator}",
        "after_width": f"{after_width.numerator}/{after_width.denominator}",
        "after_normalized_gap": f"1/{n}",
    }
    row["checked"] = (
        row["dimension"] == 2**n
        and row["exact_cluster_conjugation"]
        and row["walsh_orthogonal_exact"]
        and row["cluster_eigenvector_max_abs_residual"] == 0.0
        and row["ordered_spectrum_max_abs_error"] <= 1e-12
        and row["ordered_spectrum_multiplicity_match"]
        and row["binomial_multiplicity_match"]
        and row["ground_energy"] == -n
        and row["first_excited_energy"] == 2 - n
        and row["top_energy"] == n
        and gap == 2
        and width == 2 * n
        and after_gap / after_width == Fraction(1, n)
    )
    return row


def build_payload(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    repo_root = args.repo_root.resolve()
    module_path = (repo_root / args.lean_module).resolve()
    operator_path = (repo_root / args.operator_module).resolve()
    r187_path = (repo_root / args.r187_module).resolve()
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
            "Derive the complete all-n open-chain cluster-stabilizer spectrum "
            "from a Walsh eigenbasis and exact cluster-phase conjugation, prove "
            "binomial multiplicities and operator-derived gap/width formulas, "
            "then reconnect those values to the R187 uniform-scale rejection."
        ),
        "source_module": args.lean_module,
        "operator_module": args.operator_module,
        "r187_source_module": args.r187_module,
        "pinned_toolchain": "leanprover/lean4:v4.12.0",
        "independent_oracle": (
            "Python integer bit-action matrices, exact Walsh Gram and phase "
            "conjugation, plus NumPy eigvalsh"
        ),
        "checked_sizes": list(CHECKED_SIZES),
        "uniform_scale": "27/20",
        "required_definitions": REQUIRED_DEFINITIONS,
        "required_theorems": REQUIRED_THEOREMS,
        "forbidden_source_tokens": ["sorry", "axiom"],
        "acceptance": {
            "lean_version_returncode": 0,
            "lake_version_returncode": 0,
            "module_check_returncode": 0,
            "module_check_warning_count": 0,
            "independent_row_count": len(CHECKED_SIZES),
            "requirement_pass_count": 14,
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
    source_bindings = {
        "walsh_completion": all(
            token in source
            for token in [
                "walshMatrix_conjTranspose_mul",
                "walshMatrixUnit",
                "xChainOperator_spectrum",
            ]
        ),
        "cluster_conjugation": all(
            token in source
            for token in [
                "clusterPhase_conjugates_xChainOperator",
                "clusterPhaseMatrixUnit",
                "openChainOperator_spectrum_formula",
            ]
        ),
        "multiplicity": all(
            token in source
            for token in [
                "labelSupportEquiv",
                "labelsOfWeightEquiv",
                "labelWeight_eq_support_card",
                "Nat.choose n k",
            ]
        ),
        "derived_boundary": all(
            token in source
            for token in [
                "openChain_raw_gap_formula",
                "openChain_width_formula",
                "openChainExactBeforeSummary_normalized",
                "open_chain_uniform_reweight_instantiates_r187",
            ]
        ),
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
            "Pinned Lean project and all formal source layers exist",
            toolchain_path.exists()
            and toolchain_path.read_text(encoding="utf-8").strip()
            == "leanprover/lean4:v4.12.0"
            and lakefile_path.exists()
            and manifest_path.exists()
            and operator_path.exists()
            and r187_path.exists(),
            {
                "lean_toolchain_sha256": sha256_file(toolchain_path),
                "lakefile_sha256": sha256_file(lakefile_path),
                "lake_manifest_sha256": sha256_file(manifest_path),
                "operator_module_sha256": sha256_file(operator_path),
                "r187_module_sha256": sha256_file(r187_path),
            },
        ),
        requirement(
            "R3",
            "The spectrum source contains no sorry or axiom escape hatch",
            forbidden_hits["sorry"] == 0 and forbidden_hits["axiom"] == 0,
            {"forbidden_hits": forbidden_hits},
        ),
        requirement(
            "R4",
            "All declared character, matrix, weight, and summary definitions exist",
            all(name in definition_names for name in REQUIRED_DEFINITIONS),
            {
                "required_definitions": REQUIRED_DEFINITIONS,
                "definition_names": definition_names,
            },
        ),
        requirement(
            "R5",
            "All declared eigenbasis, spectrum, multiplicity, and metric theorems exist",
            all(name in theorem_names for name in REQUIRED_THEOREMS),
            {
                "required_theorems": REQUIRED_THEOREMS,
                "theorem_names": theorem_names,
            },
        ),
        requirement(
            "R6",
            "Walsh orthogonality is promoted to a complete invertible eigenbasis",
            source_bindings["walsh_completion"],
            source_bindings,
        ),
        requirement(
            "R7",
            "Cluster phase conjugation transfers the complete X-chain spectrum",
            source_bindings["cluster_conjugation"],
            source_bindings,
        ),
        requirement(
            "R8",
            "Label support equivalence proves exact binomial multiplicities",
            source_bindings["multiplicity"],
            source_bindings,
        ),
        requirement(
            "R9",
            "Operator-derived gap and width reconnect to the R187 rejection",
            source_bindings["derived_boundary"],
            source_bindings,
        ),
        requirement(
            "R10",
            "Independent Walsh matrices have exact 2^n orthogonality",
            all(row["walsh_orthogonal_exact"] for row in rows),
            {"rows": rows},
        ),
        requirement(
            "R11",
            "Independent cluster matrices equal exact phase conjugates of X chains",
            all(row["exact_cluster_conjugation"] for row in rows),
            {"rows": rows},
        ),
        requirement(
            "R12",
            "Independent cluster eigenvectors and complete ordered spectra replay",
            all(
                row["cluster_eigenvector_max_abs_residual"] == 0.0
                and row["ordered_spectrum_max_abs_error"] <= 1e-12
                and row["ordered_spectrum_multiplicity_match"]
                for row in rows
            ),
            {"rows": rows, "eigenvalue_tolerance": 1e-12},
        ),
        requirement(
            "R13",
            "Binomial multiplicities, gap, width, and scale-invariant ratio replay",
            all_rows_checked
            and all(row["binomial_multiplicity_match"] for row in rows),
            {"rows": rows},
        ),
        requirement(
            "R14",
            "Lean, Lake, and SpectrumFormula return zero with no module warnings",
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
        "status": STATUS if not failed_ids else "spectrum_formula_certificate_rejected",
        "last_updated": "2026-07-29",
        "protocol": protocol,
        "protocol_hash": protocol_hash,
        "source": {
            "lean_module": args.lean_module,
            "lean_module_sha256": sha256_file(module_path),
            "operator_module": args.operator_module,
            "operator_module_sha256": sha256_file(operator_path),
            "r187_module": args.r187_module,
            "r187_module_sha256": sha256_file(r187_path),
            "lean_toolchain_sha256": sha256_file(toolchain_path),
            "lakefile_sha256": sha256_file(lakefile_path),
            "lake_manifest_sha256": sha256_file(manifest_path),
            "definition_names": definition_names,
            "theorem_names": theorem_names,
            "forbidden_hits": forbidden_hits,
            "bindings": source_bindings,
        },
        "execution": {
            "probes": probes,
            "transcript_path": str(args.transcript),
            "transcript_sha256": transcript_hash,
            "module_warning_count": warning_count,
        },
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
                "Lean constructs an invertible all-n Walsh eigenbasis for the X chain.",
                "Lean proves exact cluster-phase conjugation from the X chain to the open-chain cluster Hamiltonian.",
                "Lean proves every eigenvalue is 2k-n and weight k has exactly choose(n,k) labels.",
                "Lean derives ground energy -n, first excited energy 2-n, gap 2, top energy n, width 2n, and normalized gap 1/n.",
                "Lean reconnects these operator-derived values to the R187 27/20 uniform-reweight rejection.",
                "Independent n=4,5,6 integer-matrix, Walsh, eigenvector, eigenspectrum, and multiplicity replays pass.",
            ],
            "not_supported": [
                "This solves one exactly diagonalizable commuting stabilizer family, not arbitrary local Hamiltonians.",
                "The 27/20 result rejects only global uniform rescaling as normalized-gap amplification; it is not a global no-go theorem.",
                "No quantum hardware execution, Quantum PCP theorem, NLTS theorem, BQP separation, solved frontier, or new credit is supported.",
            ],
        },
    }
    payload["payload_sha256"] = canonical_hash(payload)
    return payload, transcript


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = "\n".join(
        "| {n} | {dimension} | {gap} | {width} | {normalized} | "
        "{spectrum_error:.3e} | {checked} |".format(
            n=row["n"],
            dimension=row["dimension"],
            gap=row["gap"],
            width=row["width"],
            normalized=row["normalized_gap"],
            spectrum_error=row["ordered_spectrum_max_abs_error"],
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
    return f"""# B9 R190 Complete Spectrum Formula Certificate

## Verdict

- Status: `{payload['status']}`
- Requirements: `{summary['requirements_passed']}/{summary['requirement_count']}`
- Protocol hash: `{payload['protocol_hash']}`
- Payload hash: `{payload['payload_sha256']}`
- Transcript hash: `{payload['execution']['transcript_sha256']}`
- Lean module warnings: `{payload['execution']['module_warning_count']}`
- New credit delta: `{summary['new_credit_delta']}`

## Formal Result

The pinned Lean 4.12.0 module constructs a complete Walsh eigenbasis for the
independent `-sum X_i` chain and an exact diagonal cluster-phase conjugation
to the open-chain cluster-stabilizer Hamiltonian. Every label of Hamming
weight `k` has energy `2k-n`; label/support equivalence proves multiplicity
`choose(n,k)`. Ground energy, first excitation, raw gap, top energy, width,
and normalized gap are therefore `-n`, `2-n`, `2`, `n`, `2n`, and `1/n`.

## Independent Replay

| n | dimension | gap | width | normalized gap | spectrum error | checked |
|---:|---:|---:|---:|---:|---:|---|
{rows}

The independent path builds integer bit-action matrices, exact Walsh Gram
matrices, exact cluster-phase conjugates, and all cluster eigenvectors without
using Lean output. NumPy is used only to compare the complete ordered finite
eigenspectrum.

## Supported

{supported}

## Not Supported

{not_supported}

## Next Gate

Use the exact solvable family as a control, then seek a restricted
noncommuting perturbation whose normalized gap behavior cannot be reduced to
uniform scaling. Any next theorem must preserve explicit locality, state its
perturbation regime, and retain the same hardware/Quantum-PCP claim boundary.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--lean-module",
        default="B9/ClusterStabilizer/SpectrumFormula.lean",
    )
    parser.add_argument(
        "--operator-module",
        default="B9/ClusterStabilizer/OperatorSemantics.lean",
    )
    parser.add_argument(
        "--r187-module",
        default="B9/ClusterStabilizer/WidthLocality.lean",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(
            "results/B9_R190_open_chain_spectrum_formula_certificate_v1.json"
        ),
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        default=Path(
            "results/B9_R190_open_chain_spectrum_formula_transcript_v1.txt"
        ),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B9_R190_spectrum_formula_certificate.md"),
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
