#!/usr/bin/env python3
"""T-B3-018/T-B10-015e: full-covariance row replay-validation manifest gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b3_b10_full_covariance_row_replay_validation_manifest_gate_v0"
STATUS = "b3_b10_full_covariance_row_replay_validation_manifest_open_missing_artifact"
MODEL_STATUS = "row_replay_validation_manifest_required_before_full_covariance_rows"
VERSION = "0.1"
EXPECTED_DENOMINATOR_MANIFEST_ID = "B3-R1-full-covariance-denominator-replay-manifest"
EXPECTED_ROW_REPLAY_MANIFEST_ID = "B3-R1-full-covariance-row-replay-validation-manifest"
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
    denominator = load_json(args.denominator_replay_manifest_gate)
    denominator_summary = denominator["summary"]
    denominator_packet = denominator["denominator_replay_manifest_packet"]
    submission_path = args.submission_dir / f"{EXPECTED_ROW_REPLAY_MANIFEST_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None

    required_keys = [
        "manifest_id",
        "denominator_replay_manifest_id",
        "downstream_packet_id",
        "denominator_manifest_hash",
        "provenance_manifest_hash",
        "row_scope_hash",
        "full_covariance_row_table_hash",
        "compiled_state_amplitude_or_sampler_replay_hash",
        "pauli_grouping_covariance_replay_hash",
        "derivative_estimator_replay_hash",
        "selected_ci_fci_denominator_replay_hash",
        "optimizer_loop_cost_replay_hash",
        "same_access_decision_replay_hash",
        "b10_access_boundary_replay_hash",
        "row_acceptance_ledger_hash",
        "negative_boundary_nonpromotion_hash",
        "reproduction_command_hash",
        "claim_boundary",
    ]
    production_required_keys = [
        "denominator_manifest_hash",
        "provenance_manifest_hash",
        "row_scope_hash",
        "full_covariance_row_table_hash",
        "compiled_state_amplitude_or_sampler_replay_hash",
        "pauli_grouping_covariance_replay_hash",
        "derivative_estimator_replay_hash",
        "selected_ci_fci_denominator_replay_hash",
        "optimizer_loop_cost_replay_hash",
        "same_access_decision_replay_hash",
        "b10_access_boundary_replay_hash",
        "row_acceptance_ledger_hash",
        "negative_boundary_nonpromotion_hash",
        "reproduction_command_hash",
        "claim_boundary",
    ]
    evidence_files = [
        "accepted_denominator_replay_manifest",
        "full_covariance_row_scope_manifest",
        "full_covariance_row_table",
        "compiled_state_replay_or_sampler_trace",
        "pauli_grouping_covariance_replay",
        "derivative_estimator_replay",
        "selected_ci_fci_denominator_replay",
        "optimizer_loop_cost_replay",
        "same_access_decision_replay",
        "b10_access_boundary_replay",
        "row_acceptance_ledger",
        "negative_boundary_nonpromotion_note",
        "reproduction_command_manifest",
        "claim_boundary_note",
    ]

    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    production_present = [
        key for key in production_required_keys if submitted is not None and submitted.get(key) is not None
    ]
    replay_hashes = submitted.get("replay_hashes") if submitted else None
    replay_bound = (
        isinstance(replay_hashes, dict)
        and replay_hashes.get("denominator_manifest_hash") == denominator_summary.get("manifest_hash")
        and replay_hashes.get("provenance_manifest_hash")
        == denominator_summary.get("provenance_manifest_hash")
        and replay_hashes.get("downstream_packet_id") == EXPECTED_DOWNSTREAM_PACKET_ID
        and replay_hashes.get("row_aligned_instance_count")
        == denominator_summary.get("row_aligned_instance_count")
        and replay_hashes.get("selected_ci_larger_basis_denominator_beaten_count") == 0
    )
    source_backed = submitted is not None and submitted.get("source_evidence_files_present") is True
    manifest_bound = (
        submitted is not None
        and submitted.get("manifest_id") == EXPECTED_ROW_REPLAY_MANIFEST_ID
        and submitted.get("denominator_replay_manifest_id") == EXPECTED_DENOMINATOR_MANIFEST_ID
        and submitted.get("downstream_packet_id") == EXPECTED_DOWNSTREAM_PACKET_ID
        and submitted.get("denominator_manifest_hash") == denominator_summary.get("manifest_hash")
        and submitted.get("provenance_manifest_hash") == denominator_summary.get("provenance_manifest_hash")
    )
    claim_boundary_bound = (
        submitted is not None
        and isinstance(submitted.get("claim_boundary"), dict)
        and submitted["claim_boundary"].get("accepted_full_covariance_rows") == 0
        and submitted["claim_boundary"].get("b3_reopen_ready") is False
        and submitted["claim_boundary"].get("positive_same_access_route_claimed") is False
        and submitted["claim_boundary"].get("reaction_dynamics_solution_claimed") is False
        and submitted["claim_boundary"].get("quantum_advantage_claimed") is False
        and submitted["claim_boundary"].get("bqp_separation_claimed") is False
    )

    row_replay_packet = {
        "manifest_id": EXPECTED_ROW_REPLAY_MANIFEST_ID,
        "denominator_replay_manifest_id": EXPECTED_DENOMINATOR_MANIFEST_ID,
        "downstream_packet_id": EXPECTED_DOWNSTREAM_PACKET_ID,
        "source_denominator_replay_manifest_gate": str(args.denominator_replay_manifest_gate),
        "submission_artifact_path": str(submission_path),
        "denominator_manifest_hash": denominator_summary.get("manifest_hash"),
        "provenance_manifest_hash": denominator_summary.get("provenance_manifest_hash"),
        "row_aligned_instance_count": denominator_summary.get("row_aligned_instance_count"),
        "compiled_pilot_instance_count": denominator_summary.get("compiled_pilot_instance_count"),
        "selected_ci_larger_basis_denominator_beaten_count": denominator_summary.get(
            "selected_ci_larger_basis_denominator_beaten_count"
        ),
        "max_optimizer_loop_total_shots_lower_bound": denominator_summary.get(
            "max_optimizer_loop_total_shots_lower_bound"
        ),
        "required_keys": required_keys,
        "production_required_keys": production_required_keys,
        "required_evidence_files": evidence_files,
        "accepted_only_if": [
            "manifest_id equals B3-R1-full-covariance-row-replay-validation-manifest",
            "denominator_replay_manifest_id equals B3-R1-full-covariance-denominator-replay-manifest",
            "downstream_packet_id equals B3-R1-full-compiled-covariance",
            "denominator_manifest_hash and provenance_manifest_hash match the source gates",
            "full covariance row table, compiled-state replay, Pauli grouping covariance replay, derivative estimator replay, denominator replay, optimizer-loop cost replay, same-access decision replay, and B10 access boundary replay are hash-bound",
            "row_acceptance_ledger and negative_boundary_nonpromotion_hash keep accepted rows at 0 until full evidence exists",
            "source evidence files are present and replay_hashes bind denominator manifest, provenance manifest, downstream packet, row count, and denominator-win count",
            "claim_boundary forbids B3 reopen, positive same-access route, reaction-dynamics solution, quantum advantage, and BQP separation claims until accepted",
        ],
    }
    row_replay_packet["manifest_hash"] = stable_hash(row_replay_packet)

    requirements = [
        requirement(
            "P1",
            "Denominator replay manifest gate remains valid and blocked only on P6/P7/P8",
            denominator.get("method") == "b3_b10_full_covariance_denominator_replay_manifest_gate_v0"
            and denominator_summary.get("validation_error_count") == 0
            and denominator_summary.get("failed_manifest_requirement_ids") == ["P6", "P7", "P8"],
            {
                "source_status": denominator.get("status"),
                "failed_manifest_requirement_ids": denominator_summary.get("failed_manifest_requirement_ids"),
                "validation_error_count": denominator_summary.get("validation_error_count"),
            },
        ),
        requirement(
            "P2",
            "Row replay manifest is bound to denominator replay and full compiled-covariance packet",
            denominator_summary.get("manifest_id") == EXPECTED_DENOMINATOR_MANIFEST_ID
            and denominator_summary.get("downstream_packet_id") == EXPECTED_DOWNSTREAM_PACKET_ID
            and denominator_packet.get("manifest_hash") == denominator_summary.get("manifest_hash"),
            {
                "denominator_replay_manifest_id": denominator_summary.get("manifest_id"),
                "downstream_packet_id": denominator_summary.get("downstream_packet_id"),
                "denominator_manifest_hash": denominator_summary.get("manifest_hash"),
            },
        ),
        requirement(
            "P3",
            "Row replay packet carries locked replay schema and evidence classes",
            len(required_keys) == 18 and len(production_required_keys) == 15 and len(evidence_files) == 14,
            {
                "required_key_count": len(required_keys),
                "production_required_key_count": len(production_required_keys),
                "required_evidence_file_count": len(evidence_files),
            },
        ),
        requirement(
            "P4",
            "Four-row scope and denominator negative boundary remain preserved",
            denominator_summary.get("row_aligned_instance_count") == 4
            and denominator_summary.get("compiled_pilot_instance_count") == 1
            and denominator_summary.get("selected_ci_larger_basis_denominator_beaten_count") == 0
            and denominator_summary.get("max_optimizer_loop_total_shots_lower_bound") == 475043013690000,
            {
                "row_aligned_instance_count": denominator_summary.get("row_aligned_instance_count"),
                "compiled_pilot_instance_count": denominator_summary.get("compiled_pilot_instance_count"),
                "selected_ci_larger_basis_denominator_beaten_count": denominator_summary.get(
                    "selected_ci_larger_basis_denominator_beaten_count"
                ),
                "max_optimizer_loop_total_shots_lower_bound": denominator_summary.get(
                    "max_optimizer_loop_total_shots_lower_bound"
                ),
            },
        ),
        requirement(
            "P5",
            "B3/B10 route remains non-promoted before accepted rows",
            denominator_summary.get("accepted_priority_reopen_rows") == 0
            and denominator_summary.get("b3_reopen_ready") is False
            and denominator_summary.get("positive_same_access_route_available") is False
            and denominator_summary.get("reaction_dynamics_solution_claimed") is False
            and denominator_summary.get("quantum_advantage_claimed") is False
            and denominator_summary.get("bqp_separation_claimed") is False,
            {
                "accepted_priority_reopen_rows": denominator_summary.get("accepted_priority_reopen_rows"),
                "b3_reopen_ready": denominator_summary.get("b3_reopen_ready"),
                "positive_same_access_route_available": denominator_summary.get(
                    "positive_same_access_route_available"
                ),
                "reaction_dynamics_solution_claimed": denominator_summary.get(
                    "reaction_dynamics_solution_claimed"
                ),
                "quantum_advantage_claimed": denominator_summary.get("quantum_advantage_claimed"),
                "bqp_separation_claimed": denominator_summary.get("bqp_separation_claimed"),
            },
        ),
        requirement(
            "P6",
            "Full-covariance row replay-validation manifest artifact has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted row replay manifest satisfies the locked replay schema",
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
            "Submitted row replay manifest is source-backed, gate-bound, replay-bound, and claim-boundary-safe",
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
            "Forbidden row acceptance, solution, advantage, and BQP claims remain false",
            denominator_summary.get("accepted_priority_reopen_rows") == 0
            and denominator_summary.get("b3_reopen_ready") is False
            and denominator_summary.get("positive_same_access_route_available") is False
            and denominator_summary.get("reaction_dynamics_solution_claimed") is False
            and denominator_summary.get("quantum_advantage_claimed") is False
            and denominator_summary.get("bqp_separation_claimed") is False,
            {
                "accepted_priority_reopen_rows": denominator_summary.get("accepted_priority_reopen_rows"),
                "b3_reopen_ready": denominator_summary.get("b3_reopen_ready"),
                "positive_same_access_route_available": denominator_summary.get(
                    "positive_same_access_route_available"
                ),
                "reaction_dynamics_solution_claimed": denominator_summary.get(
                    "reaction_dynamics_solution_claimed"
                ),
                "quantum_advantage_claimed": denominator_summary.get("quantum_advantage_claimed"),
                "bqp_separation_claimed": denominator_summary.get("bqp_separation_claimed"),
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected full-covariance row replay manifest failures: {failed_ids}")
    if submitted_exists:
        validation_errors.append("gate expected no submitted row replay-validation manifest until a chemistry PR supplies one")

    summary = {
        "manifest_id": EXPECTED_ROW_REPLAY_MANIFEST_ID,
        "denominator_replay_manifest_id": EXPECTED_DENOMINATOR_MANIFEST_ID,
        "downstream_packet_id": EXPECTED_DOWNSTREAM_PACKET_ID,
        "denominator_manifest_hash": denominator_summary.get("manifest_hash"),
        "provenance_manifest_hash": denominator_summary.get("provenance_manifest_hash"),
        "manifest_hash": row_replay_packet["manifest_hash"],
        "manifest_requirement_count": len(requirements),
        "manifest_requirements_passed": passed,
        "manifest_requirements_failed": len(requirements) - passed,
        "failed_manifest_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "production_required_key_count": len(production_required_keys),
        "required_evidence_file_count": len(evidence_files),
        "row_aligned_instance_count": denominator_summary.get("row_aligned_instance_count"),
        "compiled_pilot_instance_count": denominator_summary.get("compiled_pilot_instance_count"),
        "selected_ci_larger_basis_denominator_beaten_count": denominator_summary.get(
            "selected_ci_larger_basis_denominator_beaten_count"
        ),
        "max_optimizer_loop_total_shots_lower_bound": denominator_summary.get(
            "max_optimizer_loop_total_shots_lower_bound"
        ),
        "submitted_manifest_exists": submitted_exists,
        "submitted_key_count": len(submitted) if submitted else 0,
        "missing_key_count": len(missing_keys),
        "production_keys_present_count": len(production_present),
        "accepted_priority_reopen_rows": 0,
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
        "title": "B3/B10 Full-Covariance Row Replay-Validation Manifest Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_denominator_replay_manifest_gate": str(args.denominator_replay_manifest_gate),
        "source_target_id": "B10-T1",
        "dependency_benchmarks": ["B3", "B10"],
        "summary": summary,
        "row_replay_validation_manifest_packet": row_replay_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "The B3/B10 full-covariance reopen route now has a row replay-validation "
                "manifest packet after the denominator replay manifest and before any full "
                "compiled-state covariance rows can count."
            ),
            "what_is_not_supported": (
                "No row replay-validation manifest or full-covariance row has been submitted "
                "or accepted; B3 remains demoted and no reaction-dynamics solution, positive "
                "same-access route, quantum advantage, or BQP separation is supported."
            ),
            "next_gate": (
                "Submit B3-R1-full-covariance-row-replay-validation-manifest with denominator "
                "manifest hash, row table replay, compiled-state replay, covariance replay, "
                "derivative estimator replay, denominator replay, optimizer-loop cost replay, "
                "same-access decision replay, B10 access-boundary replay, row acceptance ledger, "
                "and claim boundary before B3-R1-full-compiled-covariance rows can count."
            ),
            "accepted_full_covariance_rows": 0,
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
    packet = payload["row_replay_validation_manifest_packet"]
    lines = [
        "# B3/B10 Full-Covariance Row Replay-Validation Manifest Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Manifest: `{summary['manifest_id']}`",
        f"- Denominator replay manifest: `{summary['denominator_replay_manifest_id']}`",
        f"- Downstream packet: `{summary['downstream_packet_id']}`",
        f"- Denominator manifest hash: `{summary['denominator_manifest_hash']}`",
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
        "## Row Replay-Validation Manifest Packet",
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
            f"- accepted_full_covariance_rows: {payload['claim_boundary']['accepted_full_covariance_rows']}",
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
        lines.extend(f"- {error}" for error in payload["validation_errors"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--denominator-replay-manifest-gate",
        type=Path,
        default=Path("results/B3_B10_full_covariance_denominator_replay_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--submission-dir",
        type=Path,
        default=Path("results/B3_B10_full_covariance_row_replay_validation_manifest_submissions"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B3_B10_full_covariance_row_replay_validation_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B3_B10_full_covariance_row_replay_validation_manifest_gate.md"),
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
