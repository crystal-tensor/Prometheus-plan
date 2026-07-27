#!/usr/bin/env python3
"""Check the B9 all-n open-chain structural certificate without spectral overclaim."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "B9-R188-open-chain-all-n-structural-certificate"
METHOD = "b9_r188_open_chain_all_n_structural_certificate_v1"
STATUS = (
    "checked_all_n_structural_hamiltonian_support_certificate_complete_"
    "operator_spectral_bridge_open"
)
VERSION = "1.0"
EXPECTED_PROFILES = {
    4: [2, 3, 3, 2],
    5: [2, 3, 3, 3, 2],
    6: [2, 3, 3, 3, 3, 2],
}
REQUIRED_DEFINITIONS = [
    "openChainZSites",
    "openChainTerm",
    "openChainSupport",
    "OpenChainHamiltonian",
    "openChainHamiltonian",
    "openChainSupportCardProfile",
    "reweightOpenChainTerm",
    "reweightedOpenChainHamiltonian",
    "openChainBeforeSummary",
    "openChainAfterSummary",
]
REQUIRED_THEOREMS = [
    "open_chain_term_count",
    "open_chain_support_subset_range",
    "open_chain_support_card_le_three",
    "open_chain_left_boundary_support",
    "open_chain_interior_support",
    "open_chain_right_boundary_support",
    "open_chain_interior_one_attains_three",
    "open_chain_support_card_profile_length",
    "reweight_open_chain_term_support",
    "open_chain_reweight_preserves_every_support",
    "open_chain_summaries_are_uniformly_scaled",
    "open_chain_summaries_preserve_locality",
    "open_chain_uniform_reweight_instantiates_r187",
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


def parse_profiles(output: str) -> dict[int, list[int]]:
    profiles: dict[int, list[int]] = {}
    pattern = re.compile(
        r"^R188_PROFILE n=(\d+) support_cards=\[([0-9,\s]*)\]$",
        re.MULTILINE,
    )
    for match in pattern.finditer(output):
        n = int(match.group(1))
        cards = [
            int(value.strip())
            for value in match.group(2).split(",")
            if value.strip()
        ]
        profiles[n] = cards
    return profiles


def profile_invariants(profiles: dict[int, list[int]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for n in sorted(EXPECTED_PROFILES):
        cards = profiles.get(n, [])
        row = {
            "n": n,
            "support_cards": cards,
            "term_count": len(cards),
            "boundary_cards": [cards[0], cards[-1]] if len(cards) >= 2 else [],
            "interior_cards": cards[1:-1] if len(cards) >= 2 else [],
            "max_locality": max(cards, default=0),
        }
        row["checked"] = (
            cards == EXPECTED_PROFILES[n]
            and row["term_count"] == n
            and row["boundary_cards"] == [2, 2]
            and all(card == 3 for card in row["interior_cards"])
            and row["max_locality"] == 3
        )
        rows.append(row)
    return {
        "rows": rows,
        "all_rows_checked": all(row["checked"] for row in rows),
    }


def build_payload(args: argparse.Namespace) -> tuple[dict[str, Any], str]:
    repo_root = args.repo_root.resolve()
    module_path = (repo_root / args.lean_module).resolve()
    r187_module_path = (repo_root / args.r187_module).resolve()
    toolchain_path = repo_root / "lean-toolchain"
    lakefile_path = repo_root / "lakefile.lean"
    manifest_path = repo_root / "lake-manifest.json"
    source = module_path.read_text(encoding="utf-8")

    protocol = {
        "experiment_id": EXPERIMENT_ID,
        "track": ["B9", "B10"],
        "target": (
            "Construct the open-boundary cluster-stabilizer term family for every n, "
            "prove all-n support and locality facts, preserve support under 27/20 "
            "reweighting, and instantiate R187 while leaving operator spectra open."
        ),
        "source_module": args.lean_module,
        "r187_source_module": args.r187_module,
        "domain": "integer n >= 4 for exact maximum locality and R187 instantiation",
        "pinned_toolchain": "leanprover/lean4:v4.12.0",
        "generated_profile_ns": sorted(EXPECTED_PROFILES),
        "expected_profiles": EXPECTED_PROFILES,
        "required_definitions": REQUIRED_DEFINITIONS,
        "required_theorems": REQUIRED_THEOREMS,
        "forbidden_source_tokens": ["sorry", "axiom"],
        "acceptance": {
            "lean_version_returncode": 0,
            "lake_version_returncode": 0,
            "module_check_returncode": 0,
            "module_check_warning_count": 0,
            "generated_profile_count": 3,
            "requirement_pass_count": 12,
        },
        "claim_boundary": {
            "formal_all_n_structural_hamiltonian_specification": True,
            "all_n_support_and_locality_theorems": True,
            "r187_instantiated_with_structural_locality": True,
            "finite_rows_generated_by_lean": True,
            "operator_matrix_semantics_formalized": False,
            "spectral_gap_derived_from_operator": False,
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
    profiles = parse_profiles(probes[2]["stdout"])
    profile_checks = profile_invariants(profiles)

    structure_names = re.findall(r"(?m)^structure\s+([A-Za-z0-9_']+)", source)
    definition_names = re.findall(
        r"(?m)^(?:noncomputable\s+)?def\s+([A-Za-z0-9_'.]+)", source
    )
    theorem_names = re.findall(
        r"(?m)^(?:@\[[^\n]+\]\s+)?theorem\s+([A-Za-z0-9_']+)",
        source,
    )
    forbidden_hits = {
        token: len(re.findall(rf"\b{re.escape(token)}\b", source))
        for token in protocol["forbidden_source_tokens"]
    }
    formal_object_fields = all(
        pattern in source
        for pattern in [
            "structure OpenChainTerm",
            "center : Nat",
            "zSites : Finset Nat",
            "coefficient : Real",
            "Fin n → OpenChainTerm",
        ]
    )
    all_n_signatures = all(
        pattern in source
        for pattern in [
            "open_chain_support_subset_range",
            "open_chain_support_card_le_three",
            "open_chain_interior_one_attains_three",
            "(hN : 4 ≤ n)",
            "open_chain_uniform_reweight_instantiates_r187",
        ]
    )
    support_reweight_bound = all(
        pattern in source
        for pattern in [
            "coefficient := B9.UniformScaleFactor * term.coefficient",
            "reweight_open_chain_term_support",
            "open_chain_reweight_preserves_every_support",
        ]
    )
    r187_bridge_bound = all(
        pattern in source
        for pattern in [
            "import B9.ClusterStabilizer.WidthLocality",
            "B9.uniform_reweight_derived_rejection",
            "open_chain_summaries_are_uniformly_scaled",
            "open_chain_summaries_preserve_locality",
        ]
    )

    broad_claims_false = all(
        value is False
        for key, value in protocol["claim_boundary"].items()
        if key
        not in {
            "formal_all_n_structural_hamiltonian_specification",
            "all_n_support_and_locality_theorems",
            "r187_instantiated_with_structural_locality",
            "finite_rows_generated_by_lean",
            "new_credit_delta",
        }
    )
    requirements = [
        requirement(
            "R1",
            "Protocol is content-addressed and broad frontier claims remain false",
            len(protocol_hash) == 64
            and broad_claims_false
            and protocol["claim_boundary"]["new_credit_delta"] == 0,
            {"protocol_hash": protocol_hash, "claim_boundary": protocol["claim_boundary"]},
        ),
        requirement(
            "R2",
            "Pinned Lean toolchain, Lake project, manifest, and R187 source exist",
            toolchain_path.exists()
            and toolchain_path.read_text(encoding="utf-8").strip()
            == "leanprover/lean4:v4.12.0"
            and lakefile_path.exists()
            and manifest_path.exists()
            and r187_module_path.exists(),
            {
                "lean_toolchain_sha256": sha256_file(toolchain_path),
                "lakefile_sha256": sha256_file(lakefile_path),
                "lake_manifest_sha256": sha256_file(manifest_path),
                "r187_module_sha256": sha256_file(r187_module_path),
            },
        ),
        requirement(
            "R3",
            "The new Lean source contains no sorry or axiom escape hatch",
            forbidden_hits["sorry"] == 0 and forbidden_hits["axiom"] == 0,
            {"forbidden_hits": forbidden_hits},
        ),
        requirement(
            "R4",
            "The formal term object records center X, neighboring Z support, and coefficient",
            "OpenChainTerm" in structure_names and formal_object_fields,
            {
                "structure_names": structure_names,
                "formal_object_fields_found": formal_object_fields,
            },
        ),
        requirement(
            "R5",
            "All declared construction definitions are present",
            all(name in definition_names for name in REQUIRED_DEFINITIONS),
            {
                "required_definitions": REQUIRED_DEFINITIONS,
                "definition_names": definition_names,
            },
        ),
        requirement(
            "R6",
            "All declared structural and bridge theorems are present",
            all(name in theorem_names for name in REQUIRED_THEOREMS),
            {
                "required_theorems": REQUIRED_THEOREMS,
                "theorem_names": theorem_names,
            },
        ),
        requirement(
            "R7",
            "All-n support, locality upper bound, and attained-locality signatures are explicit",
            all_n_signatures,
            {"all_n_signatures_found": all_n_signatures},
        ),
        requirement(
            "R8",
            "The 27/20 reweighting changes coefficients while preserving every support",
            support_reweight_bound,
            {"support_reweight_binding_found": support_reweight_bound},
        ),
        requirement(
            "R9",
            "The structural family explicitly instantiates the checked R187 theorem",
            r187_bridge_bound,
            {"r187_bridge_binding_found": r187_bridge_bound},
        ),
        requirement(
            "R10",
            "Lean, Lake, and the all-n module all return zero with no warnings",
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
        requirement(
            "R11",
            "Lean emits exactly the frozen n=4,5,6 support-card profiles",
            profiles == EXPECTED_PROFILES,
            {"profiles": profiles, "expected_profiles": EXPECTED_PROFILES},
        ),
        requirement(
            "R12",
            "Generated rows have n terms, boundary locality 2, interior locality 3, and maximum 3",
            profile_checks["all_rows_checked"],
            profile_checks,
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
        "status": STATUS if not failed_ids else "all_n_structural_certificate_rejected",
        "last_updated": "2026-07-27",
        "protocol": protocol,
        "protocol_hash": protocol_hash,
        "source": {
            "lean_module": args.lean_module,
            "lean_module_sha256": sha256_file(module_path),
            "r187_module": args.r187_module,
            "r187_module_sha256": sha256_file(r187_module_path),
            "lean_toolchain_sha256": sha256_file(toolchain_path),
            "lakefile_sha256": sha256_file(lakefile_path),
            "lake_manifest_sha256": sha256_file(manifest_path),
            "structure_names": structure_names,
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
        "generated_profiles": {
            str(n): cards for n, cards in sorted(profiles.items())
        },
        "profile_checks": profile_checks,
        "requirements": requirements,
        "summary": {
            "requirement_count": len(requirements),
            "requirements_passed": passed,
            "requirements_failed": len(requirements) - passed,
            "failed_requirement_ids": failed_ids,
            "formal_all_n_structural_hamiltonian_specification": not failed_ids,
            "all_n_support_and_locality_theorems": not failed_ids,
            "r187_instantiated_with_structural_locality": not failed_ids,
            "finite_rows_generated_by_lean": not failed_ids,
            "operator_matrix_semantics_formalized": False,
            "spectral_gap_derived_from_operator": False,
            "quantum_pcp_theorem": False,
            "nlts_theorem": False,
            "global_gap_amplification_impossibility": False,
            "bqp_separation": False,
            "new_credit_delta": 0,
        },
        "claim_boundary": {
            "supported": [
                "Lean defines one open-chain term for each Fin n center.",
                "Lean proves every support index is in range and every support has cardinality at most three.",
                "For n >= 4, Lean proves an interior term attains locality three.",
                "Lean proves 27/20 coefficient reweighting preserves every term support.",
                "The formal object emits the frozen n=4,5,6 support-card rows.",
                "The structural locality facts instantiate the checked R187 rejection.",
            ],
            "not_supported": [
                "Pauli operators are not yet interpreted as matrices on a Hilbert space.",
                "The spectral gap and width are not yet derived from the formal Hamiltonian operator.",
                "No Quantum PCP, NLTS, global no-go, BQP separation, solved-frontier, or new-credit claim is supported.",
            ],
        },
    }
    payload["payload_sha256"] = canonical_hash(payload)
    return payload, transcript


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = payload["profile_checks"]["rows"]
    row_lines = "\n".join(
        f"| {row['n']} | {row['term_count']} | `{row['support_cards']}` | "
        f"{row['max_locality']} | {row['checked']} |"
        for row in rows
    )
    return f"""# B9 R188 All-n Open-Chain Structural Certificate

Last updated: 2026-07-27

Status: **{payload['status']}**

## Question

Can the R187 algebraic rejection be attached to an actual all-`n` formal
Hamiltonian structure instead of an abstract locality number?

## Result

- Requirements: `{summary['requirements_passed']}/{summary['requirement_count']}`
- Formal all-`n` structural Hamiltonian specification: `{summary['formal_all_n_structural_hamiltonian_specification']}`
- All-`n` support and locality theorems: `{summary['all_n_support_and_locality_theorems']}`
- R187 instantiated with structural locality: `{summary['r187_instantiated_with_structural_locality']}`
- Finite rows generated by Lean: `{summary['finite_rows_generated_by_lean']}`
- Module warnings: `{payload['execution']['module_warning_count']}`
- Protocol hash: `{payload['protocol_hash']}`
- Module hash: `{payload['source']['lean_module_sha256']}`
- Transcript hash: `{payload['execution']['transcript_sha256']}`
- Payload hash: `{payload['payload_sha256']}`

The new Lean module encodes each open-chain term with one center `X` site,
neighboring `Z` sites, and a real coefficient. It proves term count `n`, support
indices inside `0..n-1`, support cardinality at most `3`, exact two-site boundary
supports, exact three-site interior supports, and support preservation under
uniform coefficient reweighting by `27/20`.

## Lean-Generated Rows

| n | terms | support cards | max locality | checked |
|---:|---:|---|---:|---|
{row_lines}

These rows come from evaluating `openChainSupportCardProfile` inside the checked
Lean module. They are not separately handwritten JSON fixtures.

## Claim Boundary

This is a checked all-`n` structural Hamiltonian and locality certificate. The
Pauli terms are not yet interpreted as matrices on a Hilbert space, and the
spectral gap and width are not yet derived from that operator. It does not prove
Quantum PCP or NLTS, establish a global gap-amplification no-go theorem, separate
BQP, solve B9, or add research credit. `new_credit_delta` remains `0`.

## Next Gate

Define the Pauli-word matrix semantics and the finite-dimensional Hamiltonian
operator, prove that uniform coefficient scaling gives `H'_n = (27/20) H_n`,
then connect the operator spectrum to the abstract gap and width consumed by
R187. The finite generated rows must remain a consequence of the same formal
object.
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
        default="B9/ClusterStabilizer/OpenChainHamiltonian.lean",
    )
    parser.add_argument(
        "--r187-module",
        default="B9/ClusterStabilizer/WidthLocality.lean",
    )
    parser.add_argument(
        "--transcript",
        type=Path,
        default=Path("results/B9_R188_open_chain_formal_transcript_v1.txt"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B9_R188_open_chain_formal_certificate_v1.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B9_R188_open_chain_formal_certificate.md"),
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
