#!/usr/bin/env python3
"""Check the B9 nonzero-scale certificate without promoting it to Quantum PCP."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "B9-R187-nonzero-scale-derived-certificate"
METHOD = "b9_r187_nonzero_scale_derived_certificate_v1"
STATUS = "checked_derived_algebraic_certificate_complete_all_n_hamiltonian_open"
VERSION = "1.0"
REQUIRED_THEOREMS = [
    "uniform_scale_factor_nonzero",
    "uniform_scale_factor_gt_one",
    "uniform_scale_preserves_computed_normalized_gap",
    "uniform_scale_raw_gap_amplifies_from_positive_gap",
    "uniform_scale_preserves_spectral_width_ratio",
    "uniform_reweight_derived_rejection",
]
REQUIRED_DEFINITIONS = [
    "UniformScaleFactor",
    "IsUniformlyScaled",
    "ComputedNormalizedGap",
    "ComputedNormalizedGapInvariant",
    "SpectralWidthPreserved",
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
    resolved = shutil.which(name)
    if resolved is None:
        return name
    return resolved


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


def build_payload(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    repo_root = args.repo_root.resolve()
    module_path = (repo_root / args.lean_module).resolve()
    toolchain_path = (repo_root / "lean-toolchain").resolve()
    lakefile_path = (repo_root / "lakefile.lean").resolve()
    manifest_path = (repo_root / "lake-manifest.json").resolve()
    source = module_path.read_text(encoding="utf-8")

    protocol = {
        "experiment_id": EXPERIMENT_ID,
        "track": ["B9", "B10"],
        "target": (
            "Replace conclusion-shaped ratio assumptions with checked derivations from "
            "nonzero uniform scaling and positive source gap."
        ),
        "source_module": args.lean_module,
        "pinned_toolchain": "leanprover/lean4:v4.12.0",
        "required_theorems": REQUIRED_THEOREMS,
        "required_definitions": REQUIRED_DEFINITIONS,
        "forbidden_source_tokens": ["hRatio", "sorry", "axiom"],
        "acceptance": {
            "lean_version_returncode": 0,
            "lake_version_returncode": 0,
            "module_check_returncode": 0,
            "module_check_warning_count": 0,
            "requirement_pass_count": 10,
        },
        "claim_boundary": {
            "restricted_checked_algebraic_theorem": True,
            "formal_all_n_hamiltonian_theorem": False,
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

    theorem_names = re.findall(r"(?m)^theorem\s+([A-Za-z0-9_']+)", source)
    definition_names = re.findall(
        r"(?m)^(?:noncomputable\s+)?def\s+([A-Za-z0-9_']+)", source
    )
    forbidden_hits = {
        token: len(re.findall(rf"\b{re.escape(token)}\b", source))
        for token in protocol["forbidden_source_tokens"]
    }
    compile_output = probes[2]["stdout"] + probes[2]["stderr"]
    warning_count = compile_output.lower().count("warning:")
    derived_signature_pattern = re.compile(
        r"theorem\s+uniform_reweight_derived_rejection"
        r"[\s\S]*?\(hScale\s*:\s*IsUniformlyScaled"
        r"[\s\S]*?\(hLocality\s*:\s*ClusterStabilizer\.LocalityPreserved"
        r"[\s\S]*?\(hPositiveGap\s*:\s*0\s*<\s*before\.gap\)"
        r"[\s\S]*?:=",
        re.MULTILINE,
    )

    requirements = [
        requirement(
            "R1",
            "Protocol is content-addressed and keeps all broad frontier claims false",
            len(protocol_hash) == 64
            and all(
                value is False
                for key, value in protocol["claim_boundary"].items()
                if key
                not in {
                    "restricted_checked_algebraic_theorem",
                    "new_credit_delta",
                }
            )
            and protocol["claim_boundary"]["new_credit_delta"] == 0,
            {"protocol_hash": protocol_hash, "claim_boundary": protocol["claim_boundary"]},
        ),
        requirement(
            "R2",
            "Pinned Lean toolchain, Lake project, and manifest are present",
            toolchain_path.exists()
            and toolchain_path.read_text(encoding="utf-8").strip()
            == "leanprover/lean4:v4.12.0"
            and lakefile_path.exists()
            and manifest_path.exists(),
            {
                "lean_toolchain_sha256": sha256_file(toolchain_path),
                "lakefile_sha256": sha256_file(lakefile_path),
                "lake_manifest_sha256": sha256_file(manifest_path),
            },
        ),
        requirement(
            "R3",
            "The Lean source contains no sorry or axiom escape hatch",
            forbidden_hits["sorry"] == 0 and forbidden_hits["axiom"] == 0,
            {"forbidden_hits": forbidden_hits},
        ),
        requirement(
            "R4",
            "The conclusion-shaped hRatio assumption is absent",
            forbidden_hits["hRatio"] == 0,
            {"hRatio_hits": forbidden_hits["hRatio"]},
        ),
        requirement(
            "R5",
            "All declared definitions are present",
            all(name in definition_names for name in REQUIRED_DEFINITIONS),
            {
                "required_definitions": REQUIRED_DEFINITIONS,
                "definition_names": definition_names,
            },
        ),
        requirement(
            "R6",
            "All declared derived theorems are present",
            all(name in theorem_names for name in REQUIRED_THEOREMS),
            {
                "required_theorems": REQUIRED_THEOREMS,
                "theorem_names": theorem_names,
            },
        ),
        requirement(
            "R7",
            "The final rejection theorem exposes scale, locality, and positive-gap inputs",
            derived_signature_pattern.search(source) is not None,
            {
                "derived_signature_found": derived_signature_pattern.search(source)
                is not None
            },
        ),
        requirement(
            "R8",
            "Pinned Lean 4.12.0 reports successfully",
            probes[0]["returncode"] == 0
            and not probes[0]["timed_out"]
            and "Lean (version 4.12.0" in probes[0]["stdout"],
            {
                "returncode": probes[0]["returncode"],
                "stdout": probes[0]["stdout"].strip(),
            },
        ),
        requirement(
            "R9",
            "Lake reports successfully",
            probes[1]["returncode"] == 0
            and not probes[1]["timed_out"]
            and "Lake version" in probes[1]["stdout"],
            {
                "returncode": probes[1]["returncode"],
                "stdout": probes[1]["stdout"].strip(),
            },
        ),
        requirement(
            "R10",
            "The source module checks with zero warnings",
            probes[2]["returncode"] == 0
            and not probes[2]["timed_out"]
            and warning_count == 0,
            {
                "returncode": probes[2]["returncode"],
                "warning_count": warning_count,
                "stdout": probes[2]["stdout"],
                "stderr": probes[2]["stderr"],
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
        "status": STATUS if not failed_ids else "derived_certificate_rejected",
        "last_updated": "2026-07-27",
        "protocol": protocol,
        "protocol_hash": protocol_hash,
        "source": {
            "lean_module": args.lean_module,
            "lean_module_sha256": sha256_file(module_path),
            "lean_toolchain_sha256": sha256_file(toolchain_path),
            "lakefile_sha256": sha256_file(lakefile_path),
            "lake_manifest_sha256": sha256_file(manifest_path),
            "theorem_count": len(theorem_names),
            "definition_count": len(definition_names),
            "theorem_names": theorem_names,
            "definition_names": definition_names,
            "forbidden_hits": forbidden_hits,
        },
        "execution": {
            "probes": probes,
            "transcript_path": str(args.transcript),
            "transcript_sha256": transcript_hash,
            "module_warning_count": warning_count,
        },
        "requirements": requirements,
        "summary": {
            "requirement_count": len(requirements),
            "requirements_passed": passed,
            "requirements_failed": len(requirements) - passed,
            "failed_requirement_ids": failed_ids,
            "hRatio_assumption_removed": forbidden_hits["hRatio"] == 0,
            "restricted_checked_algebraic_theorem": not failed_ids,
            "formal_all_n_hamiltonian_theorem": False,
            "quantum_pcp_theorem": False,
            "nlts_theorem": False,
            "global_gap_amplification_impossibility": False,
            "bqp_separation": False,
            "new_credit_delta": 0,
        },
        "claim_boundary": {
            "supported": [
                "Lean derives normalized-gap invariance from nonzero uniform scaling.",
                "Lean derives spectral-width-ratio invariance from the same nonzero scale.",
                "Lean derives raw-gap amplification from scale > 1 and a positive source gap.",
                "The restricted algebraic rejection theorem is proof-assistant checked.",
            ],
            "not_supported": [
                "The open-boundary cluster-stabilizer Hamiltonian is not yet constructed for all n in Lean.",
                "The finite JSON rows are not yet generated from the formal construction.",
                "No Quantum PCP, NLTS, global no-go, BQP separation, or solved-frontier claim is supported.",
            ],
        },
    }
    payload["payload_sha256"] = canonical_hash(payload)
    return payload, transcript


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    return f"""# B9 R187 Nonzero-Scale Derived Certificate

Last updated: 2026-07-27

Status: **{payload['status']}**

## Question

Can the B9 uniform-reweight rejection survive after removing the
conclusion-shaped `hRatio` assumption?

## Result

- Requirements: `{summary['requirements_passed']}/{summary['requirement_count']}`
- `hRatio` assumption removed: `{summary['hRatio_assumption_removed']}`
- Restricted checked algebraic theorem: `{summary['restricted_checked_algebraic_theorem']}`
- Module warnings: `{payload['execution']['module_warning_count']}`
- Protocol hash: `{payload['protocol_hash']}`
- Module hash: `{payload['source']['lean_module_sha256']}`
- Transcript hash: `{payload['execution']['transcript_sha256']}`
- Payload hash: `{payload['payload_sha256']}`

Lean now derives normalized-gap invariance and spectral-width-ratio invariance
from the nonzero `27/20` scale. It separately derives raw-gap amplification from
`27/20 > 1` and a positive source gap. The final checked theorem combines these
facts with locality preservation and rejects improvement of the computed
normalized gap.

## Claim Boundary

This closes one algebraic hypothesis-injection gap. It does not formalize the
open-boundary cluster-stabilizer Hamiltonian for every `n >= 4`, connect the
finite JSON rows to a generated formal object, prove Quantum PCP or NLTS,
establish a global gap-amplification no-go theorem, separate BQP, or solve B9.
`new_credit_delta` remains `0`.

## Next Gate

Define the open-boundary Hamiltonian family and support sets in Lean, prove the
all-`n` locality and uniform-reweight identities, and instantiate this checked
algebraic certificate from that construction rather than from abstract
`SpectralSummary` inputs.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--lean-module",
        default="B9/ClusterStabilizer/WidthLocality.lean",
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        default=Path("results/B9_R187_nonzero_scale_transcript_v1.txt"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B9_R187_nonzero_scale_certificate_v1.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B9_R187_nonzero_scale_certificate.md"),
    )
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload, transcript = build_payload(args)
    repo_root = args.repo_root.resolve()
    transcript_path = (repo_root / args.transcript).resolve()
    json_path = (repo_root / args.json_output).resolve()
    markdown_path = (repo_root / args.markdown_output).resolve()
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(transcript, encoding="utf-8")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "requirements": (
                    f"{payload['summary']['requirements_passed']}/"
                    f"{payload['summary']['requirement_count']}"
                ),
                "protocol_hash": payload["protocol_hash"],
                "payload_sha256": payload["payload_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0 if not payload["summary"]["failed_requirement_ids"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
