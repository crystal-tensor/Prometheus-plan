#!/usr/bin/env python3
"""T-B3-017/T-B10-015d: full-covariance denominator replay manifest gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b3_b10_full_covariance_denominator_replay_manifest_gate_v0"
STATUS = "b3_b10_full_covariance_denominator_replay_manifest_open_missing_artifact"
MODEL_STATUS = "denominator_replay_manifest_required_before_full_covariance_rows"
VERSION = "0.1"
EXPECTED_PROVENANCE_MANIFEST_ID = "B3-R1-full-covariance-provenance-manifest"
EXPECTED_REPLAY_MANIFEST_ID = "B3-R1-full-covariance-denominator-replay-manifest"
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
    provenance = load_json(args.provenance_manifest_gate)
    queue = load_json(args.reopen_queue_gate)
    negative = load_json(args.same_access_negative_boundary)
    provenance_summary = provenance["summary"]
    queue_summary = queue["summary"]
    negative_claim_boundary = negative["claim_boundary"]
    negative_metrics = negative["metrics"]
    demotion_decision = negative["demotion_decision"]
    submission_path = args.submission_dir / f"{EXPECTED_REPLAY_MANIFEST_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None

    required_keys = [
        "manifest_id",
        "provenance_manifest_id",
        "downstream_packet_id",
        "provenance_manifest_hash",
        "row_scope_hash",
        "selected_ci_fci_reference_table_hash",
        "compiled_covariance_replay_command_hash",
        "grouped_observable_covariance_ledger_hash",
        "derivative_shot_floor_replay_hash",
        "optimizer_loop_cost_ledger_hash",
        "same_access_denominator_decision_hash",
        "b10_access_contract_boundary_hash",
        "reference_validation_protocol_hash",
        "negative_boundary_hash",
        "claim_boundary",
    ]
    production_required_keys = [
        "provenance_manifest_hash",
        "row_scope_hash",
        "selected_ci_fci_reference_table_hash",
        "compiled_covariance_replay_command_hash",
        "grouped_observable_covariance_ledger_hash",
        "derivative_shot_floor_replay_hash",
        "optimizer_loop_cost_ledger_hash",
        "same_access_denominator_decision_hash",
        "b10_access_contract_boundary_hash",
        "reference_validation_protocol_hash",
        "negative_boundary_hash",
    ]
    evidence_files = [
        "accepted_full_covariance_provenance_manifest",
        "four_row_scope_manifest",
        "selected_ci_or_fci_reference_table",
        "compiled_covariance_replay_command",
        "grouped_observable_covariance_ledger",
        "derivative_shot_floor_replay_table",
        "optimizer_loop_cost_ledger",
        "same_access_denominator_decision_table",
        "b10_access_contract_boundary_note",
        "reference_validation_protocol",
        "negative_boundary_manifest",
        "claim_boundary_note",
    ]

    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    production_present = [
        key for key in production_required_keys if submitted is not None and submitted.get(key) is not None
    ]
    replay_hashes = submitted.get("replay_hashes") if submitted else None
    replay_bound = (
        isinstance(replay_hashes, dict)
        and replay_hashes.get("provenance_manifest_hash") == provenance_summary.get("manifest_hash")
        and replay_hashes.get("downstream_packet_id") == EXPECTED_DOWNSTREAM_PACKET_ID
        and replay_hashes.get("row_aligned_instance_count") == provenance_summary.get("row_aligned_instance_count")
    )
    source_backed = submitted is not None and submitted.get("source_evidence_files_present") is True
    manifest_bound = (
        submitted is not None
        and submitted.get("manifest_id") == EXPECTED_REPLAY_MANIFEST_ID
        and submitted.get("provenance_manifest_id") == EXPECTED_PROVENANCE_MANIFEST_ID
        and submitted.get("downstream_packet_id") == EXPECTED_DOWNSTREAM_PACKET_ID
        and submitted.get("provenance_manifest_hash") == provenance_summary.get("manifest_hash")
    )
    claim_boundary_bound = (
        submitted is not None
        and isinstance(submitted.get("claim_boundary"), dict)
        and submitted["claim_boundary"].get("b3_reopen_ready") is False
        and submitted["claim_boundary"].get("quantum_advantage_claimed") is False
        and submitted["claim_boundary"].get("bqp_separation_claimed") is False
    )

    manifest_packet = {
        "manifest_id": EXPECTED_REPLAY_MANIFEST_ID,
        "provenance_manifest_id": EXPECTED_PROVENANCE_MANIFEST_ID,
        "downstream_packet_id": EXPECTED_DOWNSTREAM_PACKET_ID,
        "source_provenance_manifest_gate": str(args.provenance_manifest_gate),
        "source_reopen_queue_gate": str(args.reopen_queue_gate),
        "source_same_access_negative_boundary": str(args.same_access_negative_boundary),
        "submission_artifact_path": str(submission_path),
        "provenance_manifest_hash": provenance_summary.get("manifest_hash"),
        "row_aligned_instance_count": provenance_summary.get("row_aligned_instance_count"),
        "compiled_pilot_instance_count": provenance_summary.get("compiled_pilot_instance_count"),
        "selected_ci_larger_basis_denominator_beaten_count": queue_summary.get(
            "selected_ci_larger_basis_denominator_beaten_count"
        ),
        "max_optimizer_loop_total_shots_lower_bound": queue_summary.get(
            "max_optimizer_loop_total_shots_lower_bound"
        ),
        "required_keys": required_keys,
        "production_required_keys": production_required_keys,
        "required_evidence_files": evidence_files,
        "accepted_only_if": [
            "manifest_id equals B3-R1-full-covariance-denominator-replay-manifest",
            "provenance_manifest_id equals B3-R1-full-covariance-provenance-manifest",
            "downstream_packet_id equals B3-R1-full-compiled-covariance",
            "provenance_manifest_hash matches the source full-covariance provenance manifest hash",
            "four-row scope, selected-CI/FCI reference table, compiled-covariance replay command, grouped-observable ledger, derivative shot-floor replay, optimizer-loop ledger, same-access decision, B10 access boundary, and validation protocol are hash-bound",
            "replay_hashes bind provenance_manifest_hash, downstream_packet_id, and row_aligned_instance_count",
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
            "Full-covariance provenance manifest gate remains valid and blocked only on P6/P7/P8",
            provenance.get("method") == "b3_b10_full_covariance_provenance_manifest_gate_v0"
            and provenance_summary.get("validation_error_count") == 0
            and provenance_summary.get("failed_manifest_requirement_ids") == ["P6", "P7", "P8"],
            {
                "source_status": provenance.get("status"),
                "failed_manifest_requirement_ids": provenance_summary.get("failed_manifest_requirement_ids"),
                "validation_error_count": provenance_summary.get("validation_error_count"),
            },
        ),
        requirement(
            "P2",
            "Denominator replay manifest is bound to the full compiled-covariance packet",
            provenance_summary.get("manifest_id") == EXPECTED_PROVENANCE_MANIFEST_ID
            and provenance_summary.get("downstream_packet_id") == EXPECTED_DOWNSTREAM_PACKET_ID
            and provenance_summary.get("accepted_priority_reopen_rows") == 0,
            {
                "provenance_manifest_id": provenance_summary.get("manifest_id"),
                "downstream_packet_id": provenance_summary.get("downstream_packet_id"),
                "accepted_priority_reopen_rows": provenance_summary.get("accepted_priority_reopen_rows"),
            },
        ),
        requirement(
            "P3",
            "Manifest packet carries locked denominator replay schema and evidence classes",
            len(required_keys) == 15
            and len(production_required_keys) == 11
            and len(evidence_files) == 12,
            {
                "required_key_count": len(required_keys),
                "production_required_key_count": len(production_required_keys),
                "required_evidence_file_count": len(evidence_files),
            },
        ),
        requirement(
            "P4",
            "Four-row scope and negative denominator pressure remain preserved",
            provenance_summary.get("row_aligned_instance_count") == 4
            and provenance_summary.get("compiled_pilot_instance_count") == 1
            and queue_summary.get("selected_ci_larger_basis_denominator_beaten_count") == 0
            and queue_summary.get("max_optimizer_loop_total_shots_lower_bound") == 475043013690000,
            {
                "row_aligned_instance_count": provenance_summary.get("row_aligned_instance_count"),
                "compiled_pilot_instance_count": provenance_summary.get("compiled_pilot_instance_count"),
                "selected_ci_larger_basis_denominator_beaten_count": queue_summary.get(
                    "selected_ci_larger_basis_denominator_beaten_count"
                ),
                "max_optimizer_loop_total_shots_lower_bound": queue_summary.get(
                    "max_optimizer_loop_total_shots_lower_bound"
                ),
            },
        ),
        requirement(
            "P5",
            "Same-access and B10 boundary remain negative before replay evidence",
            demotion_decision.get("b3_current_route_demoted") is True
            and demotion_decision.get("b10_t1_same_access_positive_route_available") is False
            and negative_claim_boundary.get("quantum_advantage_claimed") is False
            and negative_claim_boundary.get("bqp_separation_claimed") is False,
            {
                "b3_current_route_demoted": demotion_decision.get("b3_current_route_demoted"),
                "b10_t1_same_access_positive_route_available": demotion_decision.get(
                    "b10_t1_same_access_positive_route_available"
                ),
                "negative_boundary_failed_source_gate_ids": negative_metrics.get("failed_source_gate_ids"),
                "quantum_advantage_claimed": negative_claim_boundary.get("quantum_advantage_claimed"),
                "bqp_separation_claimed": negative_claim_boundary.get("bqp_separation_claimed"),
            },
        ),
        requirement(
            "P6",
            "Denominator replay manifest artifact has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted manifest satisfies the locked denominator replay schema",
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
            "Submitted manifest is source-backed, provenance-bound, replay-bound, and claim-boundary-bound",
            source_backed and manifest_bound and replay_bound and claim_boundary_bound,
            {
                "source_evidence_files_present": source_backed,
                "manifest_bound": manifest_bound,
                "replay_bound": replay_bound,
                "claim_boundary_bound": claim_boundary_bound,
            },
        ),
        requirement(
            "P9",
            "Forbidden reopen, solution, advantage, and BQP claims remain false",
            all(provenance_summary.get(key) is False for key in forbidden_claims),
            {key: provenance_summary.get(key) for key in forbidden_claims},
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected denominator replay manifest failures: {failed_ids}")
    if submitted_exists:
        validation_errors.append("gate expected no submitted denominator replay manifest until a chemistry PR supplies one")

    summary = {
        "manifest_id": EXPECTED_REPLAY_MANIFEST_ID,
        "provenance_manifest_id": EXPECTED_PROVENANCE_MANIFEST_ID,
        "downstream_packet_id": EXPECTED_DOWNSTREAM_PACKET_ID,
        "provenance_manifest_hash": provenance_summary.get("manifest_hash"),
        "manifest_hash": manifest_packet["manifest_hash"],
        "manifest_requirement_count": len(requirements),
        "manifest_requirements_passed": passed,
        "manifest_requirements_failed": len(requirements) - passed,
        "failed_manifest_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "production_required_key_count": len(production_required_keys),
        "required_evidence_file_count": len(evidence_files),
        "row_aligned_instance_count": provenance_summary.get("row_aligned_instance_count"),
        "compiled_pilot_instance_count": provenance_summary.get("compiled_pilot_instance_count"),
        "selected_ci_larger_basis_denominator_beaten_count": queue_summary.get(
            "selected_ci_larger_basis_denominator_beaten_count"
        ),
        "max_optimizer_loop_total_shots_lower_bound": queue_summary.get(
            "max_optimizer_loop_total_shots_lower_bound"
        ),
        "submitted_manifest_exists": submitted_exists,
        "submitted_key_count": len(submitted) if submitted else 0,
        "missing_key_count": len(missing_keys),
        "production_keys_present_count": len(production_present),
        "accepted_priority_reopen_rows": provenance_summary.get("accepted_priority_reopen_rows"),
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
        "title": "B3/B10 Full-Covariance Denominator Replay Manifest Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_provenance_manifest_gate": str(args.provenance_manifest_gate),
        "source_reopen_queue_gate": str(args.reopen_queue_gate),
        "source_same_access_negative_boundary": str(args.same_access_negative_boundary),
        "source_target_id": "B10-T1",
        "dependency_benchmarks": ["B3", "B10"],
        "summary": summary,
        "denominator_replay_manifest_packet": manifest_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "The B3/B10 full-covariance route now has a denominator-replay manifest packet "
                "that must bind the provenance manifest, four-row denominator references, replay "
                "commands, optimizer-loop cost ledger, B10 access boundary, and negative claim boundary."
            ),
            "what_is_not_supported": (
                "No denominator replay manifest or full-covariance row has been submitted or accepted; "
                "B3 remains demoted and no reaction-dynamics solution, positive same-access route, "
                "quantum advantage, or BQP separation is supported."
            ),
            "next_gate": (
                "Submit B3-R1-full-covariance-denominator-replay-manifest with the accepted provenance "
                "manifest hash, four-row denominator reference table, compiled covariance replay command, "
                "optimizer-loop cost ledger, same-access decision hash, B10 access boundary hash, and "
                "explicit claim boundary."
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
    packet = payload["denominator_replay_manifest_packet"]
    lines = [
        "# B3/B10 Full-Covariance Denominator Replay Manifest Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Manifest: `{summary['manifest_id']}`",
        f"- Provenance manifest: `{summary['provenance_manifest_id']}`",
        f"- Downstream packet: `{summary['downstream_packet_id']}`",
        f"- Provenance manifest hash: `{summary['provenance_manifest_hash']}`",
        f"- Manifest hash: `{summary['manifest_hash']}`",
        f"- Requirements passed/failed: `{summary['manifest_requirements_passed']}` / `{summary['manifest_requirements_failed']}`",
        f"- Failed requirement IDs: `{summary['failed_manifest_requirement_ids']}`",
        f"- Required key / production key / evidence file count: `{summary['required_key_count']}` / `{summary['production_required_key_count']}` / `{summary['required_evidence_file_count']}`",
        f"- Row-aligned / compiled-pilot instances: `{summary['row_aligned_instance_count']}` / `{summary['compiled_pilot_instance_count']}`",
        f"- Selected-CI larger-basis denominator wins: `{summary['selected_ci_larger_basis_denominator_beaten_count']}`",
        f"- Max optimizer-loop lower-bound shots: `{summary['max_optimizer_loop_total_shots_lower_bound']}`",
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
        "--provenance-manifest-gate",
        type=Path,
        default=Path("results/B3_B10_full_covariance_provenance_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--reopen-queue-gate",
        type=Path,
        default=Path("results/B3_B10_reopen_blocker_queue_gate_v0.json"),
    )
    parser.add_argument(
        "--same-access-negative-boundary",
        type=Path,
        default=Path("results/B3_B10_same_access_negative_boundary_note_v0.json"),
    )
    parser.add_argument(
        "--submission-dir",
        type=Path,
        default=Path("results/B3_B10_full_covariance_denominator_replay_manifest_submissions"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B3_B10_full_covariance_denominator_replay_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B3_B10_full_covariance_denominator_replay_manifest_gate.md"),
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
