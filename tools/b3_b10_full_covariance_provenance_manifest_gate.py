#!/usr/bin/env python3
"""T-B3-016/T-B10-015c: full-covariance provenance manifest gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b3_b10_full_covariance_provenance_manifest_gate_v0"
STATUS = "b3_b10_full_covariance_provenance_manifest_open_missing_artifact"
MODEL_STATUS = "full_covariance_provenance_manifest_required_before_reopen_rows"
VERSION = "0.1"
EXPECTED_MANIFEST_ID = "B3-R1-full-covariance-provenance-manifest"
EXPECTED_DOWNSTREAM_PACKET_ID = "B3-R1-full-compiled-covariance"
EXPECTED_FAILED_IDS = ["P6", "P7", "P8"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2 if pretty else None, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def requirement(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    priority = load_json(args.priority_packet_gate)
    summary = priority["summary"]
    submission_path = args.submission_dir / f"{EXPECTED_MANIFEST_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None
    required_keys = [
        "manifest_id",
        "downstream_packet_id",
        "row_aligned_instance_count",
        "state_preparation_family",
        "state_preparation_provenance_hashes",
        "compiled_covariance_protocol_hash",
        "grouped_observable_ledger_hash",
        "derivative_shot_floor_protocol_hash",
        "reference_validation_protocol_hash",
        "b10_access_contract_bridge_hash",
        "claim_boundary",
    ]
    production_required_keys = [
        "row_aligned_instance_count",
        "state_preparation_family",
        "state_preparation_provenance_hashes",
        "compiled_covariance_protocol_hash",
        "grouped_observable_ledger_hash",
        "derivative_shot_floor_protocol_hash",
        "reference_validation_protocol_hash",
        "b10_access_contract_bridge_hash",
    ]
    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    production_present = [
        key for key in production_required_keys if submitted is not None and submitted.get(key) is not None
    ]
    source_backed = submitted is not None and submitted.get("source_evidence_files_present") is True
    downstream_bound = (
        submitted is not None
        and submitted.get("downstream_packet_id") == EXPECTED_DOWNSTREAM_PACKET_ID
    )
    row_scope_bound = (
        submitted is not None
        and submitted.get("row_aligned_instance_count") == summary.get("row_aligned_instance_count")
    )

    manifest_packet = {
        "manifest_id": EXPECTED_MANIFEST_ID,
        "downstream_packet_id": EXPECTED_DOWNSTREAM_PACKET_ID,
        "submission_artifact_path": str(submission_path),
        "source_priority_packet_gate": str(args.priority_packet_gate),
        "required_keys": required_keys,
        "production_required_keys": production_required_keys,
        "required_evidence_files": [
            "state_preparation_family_manifest",
            "state_preparation_circuit_hash_manifest",
            "compiled_covariance_protocol_note",
            "grouped_observable_ledger_protocol",
            "derivative_shot_floor_protocol",
            "reference_validation_protocol",
            "b10_access_contract_bridge_note",
            "source_rescue_gate_manifest",
            "source_negative_boundary_manifest",
            "claim_boundary_note",
        ],
        "accepted_only_if": [
            "manifest_id equals B3-R1-full-covariance-provenance-manifest",
            "downstream_packet_id equals B3-R1-full-compiled-covariance",
            "row_aligned_instance_count equals the locked four-row B3 scope",
            "state-preparation, covariance, observable-ledger, derivative-shot-floor, validation, and B10 access-contract protocol hashes are present",
            "source evidence files are present and hash-bound",
            "claim_boundary forbids B3 reopen, positive same-access route, reaction-dynamics solution, quantum advantage, and BQP separation claims",
        ],
    }
    manifest_packet["manifest_hash"] = stable_hash(manifest_packet)

    forbidden_claims = [
        "b3_reopen_ready",
        "positive_same_access_route_available",
        "reaction_dynamics_solution_claimed",
        "quantum_advantage_claimed",
        "bqp_separation_claimed",
    ]
    requirements = [
        requirement(
            "P1",
            "Priority reopen packet remains valid and blocked only on P6/P7/P8",
            priority.get("method") == "b3_b10_reopen_priority_packet_gate_v0"
            and summary.get("validation_error_count") == 0
            and summary.get("failed_priority_requirement_ids") == ["P6", "P7", "P8"],
            {
                "source_status": priority.get("status"),
                "failed_priority_requirement_ids": summary.get("failed_priority_requirement_ids"),
                "validation_error_count": summary.get("validation_error_count"),
            },
        ),
        requirement(
            "P2",
            "Provenance manifest is bound to the full compiled-covariance reopen packet",
            summary.get("priority_packet_id") == EXPECTED_DOWNSTREAM_PACKET_ID
            and summary.get("accepted_priority_reopen_rows") == 0,
            {
                "downstream_packet_id": summary.get("priority_packet_id"),
                "accepted_priority_reopen_rows": summary.get("accepted_priority_reopen_rows"),
            },
        ),
        requirement(
            "P3",
            "Manifest packet carries locked schema and evidence file classes",
            len(required_keys) == 11
            and len(production_required_keys) == 8
            and len(manifest_packet["required_evidence_files"]) == 10,
            {
                "required_key_count": len(required_keys),
                "production_required_key_count": len(production_required_keys),
                "required_evidence_file_count": len(manifest_packet["required_evidence_files"]),
            },
        ),
        requirement(
            "P4",
            "Four-row B3 reaction-coordinate scope remains preserved",
            summary.get("row_aligned_instance_count") == 4
            and summary.get("compiled_pilot_instance_count") == 1
            and summary.get("full_compiled_state_covariance_computed") is False,
            {
                "row_aligned_instance_count": summary.get("row_aligned_instance_count"),
                "compiled_pilot_instance_count": summary.get("compiled_pilot_instance_count"),
                "full_compiled_state_covariance_computed": summary.get("full_compiled_state_covariance_computed"),
            },
        ),
        requirement(
            "P5",
            "Current B3/B10 route remains demoted before provenance evidence",
            summary.get("b3_reopen_ready") is False
            and summary.get("positive_same_access_route_available") is False
            and summary.get("reaction_dynamics_solution_claimed") is False
            and summary.get("quantum_advantage_claimed") is False
            and summary.get("bqp_separation_claimed") is False,
            {key: summary.get(key) for key in forbidden_claims},
        ),
        requirement(
            "P6",
            "Full-covariance provenance manifest artifact has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted manifest satisfies the locked provenance schema",
            submitted_exists and not missing_keys and len(production_present) == len(production_required_keys),
            {
                "missing_keys": missing_keys,
                "production_keys_present": production_present,
                "production_required_keys": production_required_keys,
                "submitted_key_count": len(submitted) if submitted else 0,
            },
        ),
        requirement(
            "P8",
            "Submitted manifest is source-backed, downstream-bound, and four-row-bound",
            source_backed and downstream_bound and row_scope_bound,
            {
                "source_evidence_files_present": source_backed,
                "downstream_bound": downstream_bound,
                "row_scope_bound": row_scope_bound,
            },
        ),
        requirement(
            "P9",
            "Forbidden reopen, solution, advantage, and BQP claims remain false",
            all(summary.get(key) is False for key in forbidden_claims),
            {key: summary.get(key) for key in forbidden_claims},
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected full-covariance provenance manifest failures: {failed_ids}")
    if submitted_exists:
        validation_errors.append("gate expected no submitted manifest until a chemistry PR supplies one")

    payload_summary = {
        "manifest_id": EXPECTED_MANIFEST_ID,
        "downstream_packet_id": EXPECTED_DOWNSTREAM_PACKET_ID,
        "manifest_hash": manifest_packet["manifest_hash"],
        "manifest_requirement_count": len(requirements),
        "manifest_requirements_passed": passed,
        "manifest_requirements_failed": len(requirements) - passed,
        "failed_manifest_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "production_required_key_count": len(production_required_keys),
        "required_evidence_file_count": len(manifest_packet["required_evidence_files"]),
        "row_aligned_instance_count": summary.get("row_aligned_instance_count"),
        "compiled_pilot_instance_count": summary.get("compiled_pilot_instance_count"),
        "full_compiled_state_covariance_computed": summary.get("full_compiled_state_covariance_computed"),
        "submitted_manifest_exists": submitted_exists,
        "missing_key_count": len(missing_keys),
        "production_keys_present_count": len(production_present),
        "accepted_priority_reopen_rows": summary.get("accepted_priority_reopen_rows"),
        "b3_reopen_ready": False,
        "positive_same_access_route_available": False,
        "reaction_dynamics_solution_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "validation_error_count": len(validation_errors),
    }
    return {
        "benchmark_id": "B3_B10",
        "problem_ids": [49, 11],
        "title": "B3/B10 Full-Covariance Provenance Manifest Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_priority_packet_gate": str(args.priority_packet_gate),
        "source_target_id": "B10-T1",
        "dependency_benchmarks": ["B3", "B10"],
        "summary": payload_summary,
        "full_covariance_provenance_manifest_packet": manifest_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "The B3/B10 full-covariance reopen route now has a concrete provenance manifest "
                "packet that must be accepted before full compiled-state covariance rows can count."
            ),
            "what_is_not_supported": (
                "No provenance manifest or full-covariance row has been submitted or accepted; B3 "
                "remains demoted and no reaction-dynamics solution, positive same-access route, "
                "quantum advantage, or BQP separation is supported."
            ),
            "next_gate": (
                "Submit B3-R1-full-covariance-provenance-manifest with four-row state-prep "
                "provenance, compiled covariance protocol, grouped observable ledger, derivative "
                "shot-floor protocol, validation protocol, B10 access-contract bridge hash, and "
                "claim boundary."
            ),
            "b3_reopen_ready": False,
            "positive_same_access_route_claimed": False,
            "reaction_dynamics_solution_claimed": False,
            "quantum_advantage_claimed": False,
            "bqp_separation_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    packet = payload["full_covariance_provenance_manifest_packet"]
    lines = [
        "# B3/B10 Full-Covariance Provenance Manifest Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Manifest: `{summary['manifest_id']}`",
        f"- Downstream packet: `{summary['downstream_packet_id']}`",
        f"- Manifest hash: `{summary['manifest_hash']}`",
        f"- Requirements passed/failed: `{summary['manifest_requirements_passed']}` / `{summary['manifest_requirements_failed']}`",
        f"- Failed requirement IDs: `{summary['failed_manifest_requirement_ids']}`",
        f"- Required key / production key / evidence file count: `{summary['required_key_count']}` / `{summary['production_required_key_count']}` / `{summary['required_evidence_file_count']}`",
        f"- Row-aligned / compiled-pilot instances: `{summary['row_aligned_instance_count']}` / `{summary['compiled_pilot_instance_count']}`",
        f"- Full compiled-state covariance computed: `{summary['full_compiled_state_covariance_computed']}`",
        f"- Submitted manifest exists: `{summary['submitted_manifest_exists']}`",
        f"- Accepted priority reopen rows: `{summary['accepted_priority_reopen_rows']}`",
        f"- validation_error_count: `{summary['validation_error_count']}`",
        "",
        "## Manifest Packet",
        "",
        f"- Submission path: `{packet['submission_artifact_path']}`",
        "",
        "Required evidence files:",
        "",
    ]
    for item in packet["required_evidence_files"]:
        lines.append(f"- {item}")
    lines.extend(["", "Acceptance predicates:", ""])
    for item in packet["accepted_only_if"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Requirement Results", ""])
    for row in payload["requirements"]:
        state = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- {row['requirement_id']} [{state}]: {row['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            f"- b3_reopen_ready: {payload['claim_boundary']['b3_reopen_ready']}",
            f"- positive_same_access_route_claimed: {payload['claim_boundary']['positive_same_access_route_claimed']}",
            f"- reaction_dynamics_solution_claimed: {payload['claim_boundary']['reaction_dynamics_solution_claimed']}",
            f"- quantum_advantage_claimed: {payload['claim_boundary']['quantum_advantage_claimed']}",
            f"- bqp_separation_claimed: {payload['claim_boundary']['bqp_separation_claimed']}",
            "",
            "## Validation",
            "",
            f"- validation_error_count: {summary['validation_error_count']}",
        ]
    )
    if payload["validation_errors"]:
        for error in payload["validation_errors"]:
            lines.append(f"- {error}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--priority-packet-gate",
        type=Path,
        default=Path("results/B3_B10_reopen_priority_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--submission-dir",
        type=Path,
        default=Path("results/B3_B10_full_covariance_provenance_manifest_submissions"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B3_B10_full_covariance_provenance_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B3_B10_full_covariance_provenance_manifest_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-02")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, pretty=args.pretty)
    write_markdown(payload, args.markdown_output)
    print(json.dumps(payload["summary"], indent=2 if args.pretty else None, sort_keys=True))
    if payload["validation_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
