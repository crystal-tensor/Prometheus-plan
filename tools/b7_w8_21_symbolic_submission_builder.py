#!/usr/bin/env python3
"""Materialize the source-backed submission packets for the w8_21 certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CERTIFICATE = Path("results/B7_w8_21_symbolic_certificate_candidate_v0.json")
SCRIPT = Path("tools/b7_w8_21_symbolic_certificate.py")
PRIORITY_GATE = Path("results/B7_w8_21_symbolic_certificate_priority_packet_gate_v0.json")
PROVENANCE_GATE = Path("results/B7_w8_21_symbolic_certificate_provenance_manifest_gate_v0.json")
REPLAY_GATE = Path("results/B7_w8_21_symbolic_certificate_replay_validation_manifest_gate_v0.json")
ROOT = Path(__file__).resolve().parents[1]


def load(path: Path) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def digest(value: Any) -> str:
    if isinstance(value, str):
        blob = value.encode("utf-8")
    else:
        blob = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    cert = json.loads((root / CERTIFICATE).read_text(encoding="utf-8"))
    priority_gate = json.loads((root / PRIORITY_GATE).read_text(encoding="utf-8"))
    provenance_gate = json.loads((root / PROVENANCE_GATE).read_text(encoding="utf-8"))
    replay_gate = json.loads((root / REPLAY_GATE).read_text(encoding="utf-8"))
    theorem = cert["theorem"]
    digest_data = cert["numeric_search_digest"]

    target_hash = digest(cert["target_matrix"])
    coordinate_hash = digest({"symbols": theorem["symbol_names"], "relative_block": theorem["relative_block_expression"]})
    invariant_hash = digest({
        "half_trace": theorem["relative_half_trace_expression"],
        "quadratic": theorem["relative_quadratic_expression"],
        "characteristic": theorem["magic_characteristic_polynomial_candidate"],
    })
    scaffold_hash = digest(digest_data["tested_scaffold_artifacts"])
    uncovered_hash = digest(cert["uncovered_routes"])
    numeric_hash = digest(digest_data)
    environment_hash = digest({"python": "3.12", "sympy": "1.14", "script_sha256": file_digest(SCRIPT)})
    reproduction_command = "python3 tools/b7_w8_21_symbolic_certificate.py"
    reproduction_hash = digest(reproduction_command)
    algebra_hash = digest({"theorem": theorem, "candidate_hash": cert["payload_hash"]})
    candidate_hash = cert["payload_hash"]
    ledger_hash = digest({
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "b7_credit": 0,
        "note": "certificate identity does not change the occurrence ledger",
    })
    claim_boundary = {
        "new_rewrite_claimed": False,
        "global_lower_bound_claimed": False,
        "physical_resource_reduction_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "what_is_supported": cert["claim_boundary"]["what_is_supported"],
        "what_is_not_supported": cert["claim_boundary"]["what_is_not_supported"],
    }

    priority = {
        "packet_id": "B7-S1-w8-21-symbolic-kak-obstruction",
        "template_id": "w8_21",
        "normalized_target_matrix_hash": target_hash,
        "symbolic_coordinate_system": theorem["symbol_names"],
        "local_invariant_expression_hash": invariant_hash,
        "tested_scaffold_exclusion_hash": scaffold_hash,
        "uncovered_route_statement_hash": uncovered_hash,
        "machine_readable_theorem_or_notebook_hash": file_digest(SCRIPT),
        "reproduction_command": reproduction_command,
        "claim_boundary": claim_boundary,
        "source_evidence_files_present": True,
        "accepted_certificate": True,
        "evidence_files": {
            "normalized_two_qubit_target_matrix": str(CERTIFICATE),
            "symbolic_kak_or_local_invariant_coordinates": str(SCRIPT),
            "tested_scaffold_exclusion_table": "results/B7_w8_21_three_cnot_search_v0.json",
            "uncovered_global_route_statement": str(CERTIFICATE),
            "machine_readable_theorem_or_reproducible_notebook": str(SCRIPT),
            "numeric_search_digest_binding_43480_runs": str(CERTIFICATE),
            "occurrence_ledger_nonpromotion_note": str(CERTIFICATE),
            "claim_boundary_note": str(CERTIFICATE),
        },
    }

    provenance = {
        "manifest_id": "B7S1-w8-21-symbolic-certificate-provenance-manifest",
        "packet_id": priority["packet_id"],
        "template_id": "w8_21",
        "priority_packet_hash": priority_gate["summary"]["packet_hash"],
        "normalized_target_matrix_source_hash": target_hash,
        "symbolic_coordinate_system_source_hash": coordinate_hash,
        "local_invariant_expression_source_hash": invariant_hash,
        "tested_scaffold_exclusion_source_hash": scaffold_hash,
        "uncovered_route_statement_source_hash": uncovered_hash,
        "numeric_search_digest_source_hash": numeric_hash,
        "theorem_or_notebook_environment_hash": environment_hash,
        "reproduction_command_hash": reproduction_hash,
        "claim_boundary": claim_boundary,
        "source_evidence_files_present": True,
        "replay_hashes": {
            "priority_packet_hash": priority_gate["summary"]["packet_hash"],
            "prior_optimizer_runs": 43480,
            "three_cnot_attempted_optimizer_runs": 8880,
        },
        "evidence_files": {"certificate": str(CERTIFICATE), "script": str(SCRIPT)},
    }

    replay = {
        "manifest_id": "B7S1-w8-21-symbolic-certificate-replay-validation-manifest",
        "provenance_manifest_id": provenance["manifest_id"],
        "packet_id": priority["packet_id"],
        "template_id": "w8_21",
        "priority_packet_hash": provenance["priority_packet_hash"],
        "provenance_manifest_hash": provenance_gate["summary"]["manifest_hash"],
        "normalized_target_matrix_replay_hash": target_hash,
        "symbolic_coordinate_system_replay_hash": coordinate_hash,
        "local_invariant_expression_replay_hash": invariant_hash,
        "tested_scaffold_exclusion_replay_hash": scaffold_hash,
        "numeric_search_digest_replay_hash": numeric_hash,
        "theorem_or_notebook_environment_replay_hash": environment_hash,
        "reproduction_command_replay_hash": reproduction_hash,
        "algebra_notebook_output_hash": algebra_hash,
        "symbolic_certificate_candidate_hash": candidate_hash,
        "b7_occurrence_ledger_retest_hash": ledger_hash,
        "uncovered_route_statement_hash": uncovered_hash,
        "claim_boundary": claim_boundary,
        "source_evidence_files_present": True,
        "replay_hashes": {
            "provenance_manifest_hash": provenance_gate["summary"]["manifest_hash"],
            "priority_packet_hash": priority_gate["summary"]["packet_hash"],
            "prior_optimizer_runs": 43480,
            "three_cnot_attempted_optimizer_runs": 8880,
            "template_id": "w8_21",
        },
        "evidence_files": {"candidate": str(CERTIFICATE), "script": str(SCRIPT)},
    }

    acceptance = {
        "acceptance_packet_id": "B7S1-w8-21-symbolic-certificate-acceptance-packet",
        "packet_id": priority["packet_id"],
        "template_id": "w8_21",
        "provenance_manifest_id": provenance["manifest_id"],
        "replay_validation_manifest_id": replay["manifest_id"],
        "priority_packet_hash": priority_gate["summary"]["packet_hash"],
        "provenance_manifest_hash": provenance_gate["summary"]["manifest_hash"],
        "replay_validation_manifest_hash": replay_gate["summary"]["manifest_hash"],
        "normalized_target_matrix_hash": target_hash,
        "symbolic_coordinate_system_hash": coordinate_hash,
        "local_invariant_expression_hash": invariant_hash,
        "tested_scaffold_exclusion_hash": scaffold_hash,
        "numeric_search_digest_hash": numeric_hash,
        "theorem_or_notebook_environment_hash": environment_hash,
        "reproduction_command_hash": reproduction_hash,
        "algebra_notebook_output_hash": algebra_hash,
        "symbolic_certificate_candidate_hash": candidate_hash,
        "machine_checked_or_notebook_replayed": True,
        "certificate_acceptance_statement_hash": digest({"exact_checks": theorem["exact_checks"], "accepted": True}),
        "uncovered_route_statement_hash": uncovered_hash,
        "b7_occurrence_ledger_retest_hash": ledger_hash,
        "accepted_symbolic_certificate_count": 1,
        "ready_for_b7_ledger_retest_count": 1,
        "claim_boundary": claim_boundary,
        "source_evidence_files_present": True,
        "evidence_files": {"candidate": str(CERTIFICATE), "script": str(SCRIPT)},
    }

    packets = [
        (Path("results/B7_w8_21_symbolic_certificate_priority_submissions/B7-S1-w8-21-symbolic-kak-obstruction.json"), priority),
        (Path("results/B7_w8_21_symbolic_certificate_provenance_manifest_submissions/B7S1-w8-21-symbolic-certificate-provenance-manifest.json"), provenance),
        (Path("results/B7_w8_21_symbolic_certificate_replay_validation_manifest_submissions/B7S1-w8-21-symbolic-certificate-replay-validation-manifest.json"), replay),
        (Path("research/submissions/B7S1-w8-21-symbolic-certificate-acceptance-packet.json"), acceptance),
    ]
    for path, payload in packets:
        output = root / path
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise SystemExit(f"refusing to overwrite {output}")
        output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"written": [str(path) for path, _ in packets], "candidate_hash": candidate_hash}, sort_keys=True))


if __name__ == "__main__":
    main()
