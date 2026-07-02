#!/usr/bin/env python3
"""T-B7-010f/T-B1-004cz: acceptance packet gate for w8_21 symbolic certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b7_w8_21_symbolic_certificate_acceptance_packet_gate_v0"
STATUS = "w8_21_symbolic_certificate_acceptance_packet_open_missing_artifact"
MODEL_STATUS = "symbolic_certificate_acceptance_packet_required_before_rewrite_or_b7_credit"
VERSION = "0.1"
EXPECTED_PACKET_ID = "B7-S1-w8-21-symbolic-kak-obstruction"
EXPECTED_PROVENANCE_MANIFEST_ID = "B7S1-w8-21-symbolic-certificate-provenance-manifest"
EXPECTED_REPLAY_MANIFEST_ID = "B7S1-w8-21-symbolic-certificate-replay-validation-manifest"
EXPECTED_ACCEPTANCE_PACKET_ID = "B7S1-w8-21-symbolic-certificate-acceptance-packet"
EXPECTED_TEMPLATE_ID = "w8_21"
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
    replay = load_json(args.replay_validation_manifest_gate)
    priority = load_json(args.priority_packet_gate)
    replay_summary = replay["summary"]
    priority_summary = priority["summary"]
    submission_path = args.submission_dir / f"{EXPECTED_ACCEPTANCE_PACKET_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None

    required_keys = [
        "acceptance_packet_id",
        "packet_id",
        "template_id",
        "provenance_manifest_id",
        "replay_validation_manifest_id",
        "priority_packet_hash",
        "provenance_manifest_hash",
        "replay_validation_manifest_hash",
        "normalized_target_matrix_hash",
        "symbolic_coordinate_system_hash",
        "local_invariant_expression_hash",
        "tested_scaffold_exclusion_hash",
        "numeric_search_digest_hash",
        "theorem_or_notebook_environment_hash",
        "reproduction_command_hash",
        "algebra_notebook_output_hash",
        "symbolic_certificate_candidate_hash",
        "machine_checked_or_notebook_replayed",
        "certificate_acceptance_statement_hash",
        "uncovered_route_statement_hash",
        "b7_occurrence_ledger_retest_hash",
        "accepted_symbolic_certificate_count",
        "ready_for_b7_ledger_retest_count",
        "claim_boundary",
        "source_evidence_files_present",
    ]
    production_required_keys = [
        "replay_validation_manifest_hash",
        "normalized_target_matrix_hash",
        "symbolic_coordinate_system_hash",
        "local_invariant_expression_hash",
        "tested_scaffold_exclusion_hash",
        "numeric_search_digest_hash",
        "theorem_or_notebook_environment_hash",
        "reproduction_command_hash",
        "algebra_notebook_output_hash",
        "symbolic_certificate_candidate_hash",
        "machine_checked_or_notebook_replayed",
        "certificate_acceptance_statement_hash",
        "uncovered_route_statement_hash",
        "b7_occurrence_ledger_retest_hash",
        "accepted_symbolic_certificate_count",
        "ready_for_b7_ledger_retest_count",
        "claim_boundary",
    ]
    required_evidence_files = [
        "accepted_replay_validation_manifest",
        "priority_symbolic_certificate_packet",
        "provenance_manifest",
        "normalized_target_matrix_replay",
        "symbolic_coordinate_system_replay",
        "local_invariant_expression_replay",
        "tested_scaffold_exclusion_replay",
        "numeric_search_digest_replay_binding_43480_runs",
        "theorem_or_notebook_environment_replay",
        "reproduction_command_replay",
        "algebra_notebook_output",
        "symbolic_certificate_candidate",
        "certificate_acceptance_statement",
        "b7_occurrence_ledger_retest",
        "uncovered_route_statement",
        "claim_boundary_note",
    ]

    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    production_present = [
        key for key in production_required_keys if submitted is not None and submitted.get(key) is not None
    ]
    manifest_bound = (
        submitted is not None
        and submitted.get("acceptance_packet_id") == EXPECTED_ACCEPTANCE_PACKET_ID
        and submitted.get("packet_id") == EXPECTED_PACKET_ID
        and submitted.get("template_id") == EXPECTED_TEMPLATE_ID
        and submitted.get("provenance_manifest_id") == EXPECTED_PROVENANCE_MANIFEST_ID
        and submitted.get("replay_validation_manifest_id") == EXPECTED_REPLAY_MANIFEST_ID
        and submitted.get("priority_packet_hash") == replay_summary.get("priority_packet_hash")
        and submitted.get("provenance_manifest_hash") == replay_summary.get("provenance_manifest_hash")
        and submitted.get("replay_validation_manifest_hash") == replay_summary.get("manifest_hash")
    )
    certificate_valid = (
        submitted is not None
        and submitted.get("machine_checked_or_notebook_replayed") is True
        and bool(submitted.get("symbolic_certificate_candidate_hash"))
        and bool(submitted.get("certificate_acceptance_statement_hash"))
        and submitted.get("accepted_symbolic_certificate_count", 0) > 0
        and submitted.get("ready_for_b7_ledger_retest_count", 0) > 0
    )
    b7_retest_bound = submitted is not None and bool(submitted.get("b7_occurrence_ledger_retest_hash"))
    claim_boundary_bound = (
        submitted is not None
        and isinstance(submitted.get("claim_boundary"), dict)
        and submitted["claim_boundary"].get("new_rewrite_claimed") is False
        and submitted["claim_boundary"].get("global_lower_bound_claimed") is False
        and submitted["claim_boundary"].get("physical_resource_reduction_claimed") is False
        and submitted["claim_boundary"].get("b7_ledger_improvement_claimed") is False
    )
    source_backed = submitted is not None and submitted.get("source_evidence_files_present") is True

    acceptance_packet = {
        "acceptance_packet_id": EXPECTED_ACCEPTANCE_PACKET_ID,
        "packet_id": EXPECTED_PACKET_ID,
        "template_id": EXPECTED_TEMPLATE_ID,
        "provenance_manifest_id": EXPECTED_PROVENANCE_MANIFEST_ID,
        "replay_validation_manifest_id": EXPECTED_REPLAY_MANIFEST_ID,
        "source_replay_validation_manifest_gate": str(args.replay_validation_manifest_gate),
        "source_priority_packet_gate": str(args.priority_packet_gate),
        "submission_artifact_path": str(submission_path),
        "priority_packet_hash": replay_summary.get("priority_packet_hash"),
        "provenance_manifest_hash": replay_summary.get("provenance_manifest_hash"),
        "replay_validation_manifest_hash": replay_summary.get("manifest_hash"),
        "prior_optimizer_runs": replay_summary.get("prior_optimizer_runs"),
        "three_cnot_attempted_optimizer_runs": replay_summary.get(
            "three_cnot_attempted_optimizer_runs"
        ),
        "three_cnot_passing_candidate_count": replay_summary.get(
            "three_cnot_passing_candidate_count"
        ),
        "target_removed_arbitrary_occurrences": replay_summary.get(
            "target_removed_arbitrary_occurrences"
        ),
        "target_removed_t_ledger": replay_summary.get("target_removed_t_ledger"),
        "required_keys": required_keys,
        "production_required_keys": production_required_keys,
        "required_evidence_files": required_evidence_files,
        "accepted_only_if": [
            "acceptance_packet_id equals B7S1-w8-21-symbolic-certificate-acceptance-packet",
            "packet, template, provenance, replay-validation, and priority hashes match source gates",
            "normalized target matrix, symbolic coordinates, local invariant expression, scaffold exclusion, and numeric-search digest are hash-bound",
            "theorem/notebook environment, reproduction command, algebra output, and certificate candidate are replay-bound",
            "machine_checked_or_notebook_replayed is true before the certificate can count",
            "accepted_symbolic_certificate_count and ready_for_b7_ledger_retest_count are positive before B7 retest can start",
            "B7 occurrence ledger retest is hash-bound and no B7 ledger credit is claimed by the acceptance packet itself",
            "claim_boundary forbids rewrite, global-lower-bound, resource-reduction, and B7-ledger-credit claims until a later ledger PR accepts them",
        ],
    }
    acceptance_packet["packet_hash"] = stable_hash(acceptance_packet)

    requirements = [
        requirement(
            "P1",
            "Replay-validation manifest gate remains valid and blocked only on P6/P7/P8",
            replay.get("method") == "b7_w8_21_symbolic_certificate_replay_validation_manifest_gate_v0"
            and replay_summary.get("validation_error_count") == 0
            and replay_summary.get("failed_manifest_requirement_ids") == EXPECTED_FAILED_IDS,
            {
                "source_status": replay.get("status"),
                "failed_manifest_requirement_ids": replay_summary.get("failed_manifest_requirement_ids"),
                "validation_error_count": replay_summary.get("validation_error_count"),
            },
        ),
        requirement(
            "P2",
            "Priority symbolic certificate packet remains fixed and source-shaped",
            priority.get("method") == "b7_w8_21_symbolic_certificate_priority_packet_gate_v0"
            and priority_summary.get("priority_packet_id") == EXPECTED_PACKET_ID
            and priority_summary.get("template_id") == EXPECTED_TEMPLATE_ID
            and priority_summary.get("validation_error_count") == 0
            and priority_summary.get("failed_priority_requirement_ids") == EXPECTED_FAILED_IDS,
            {
                "priority_packet_id": priority_summary.get("priority_packet_id"),
                "template_id": priority_summary.get("template_id"),
                "packet_hash": priority_summary.get("packet_hash"),
                "failed_priority_requirement_ids": priority_summary.get(
                    "failed_priority_requirement_ids"
                ),
            },
        ),
        requirement(
            "P3",
            "Acceptance packet carries locked symbolic certificate schema and evidence classes",
            len(required_keys) == 25
            and len(production_required_keys) == 17
            and len(required_evidence_files) == 16,
            {
                "required_key_count": len(required_keys),
                "production_required_key_count": len(production_required_keys),
                "required_evidence_file_count": len(required_evidence_files),
            },
        ),
        requirement(
            "P4",
            "Prior negative-search boundary and target ledger pressure remain preserved",
            replay_summary.get("prior_optimizer_runs") == 43480
            and replay_summary.get("three_cnot_attempted_optimizer_runs") == 8880
            and replay_summary.get("three_cnot_passing_candidate_count") == 0
            and replay_summary.get("target_removed_arbitrary_occurrences") == 30
            and replay_summary.get("target_removed_t_ledger") == 600,
            {
                "prior_optimizer_runs": replay_summary.get("prior_optimizer_runs"),
                "three_cnot_attempted_optimizer_runs": replay_summary.get(
                    "three_cnot_attempted_optimizer_runs"
                ),
                "three_cnot_passing_candidate_count": replay_summary.get(
                    "three_cnot_passing_candidate_count"
                ),
                "target_removed_arbitrary_occurrences": replay_summary.get(
                    "target_removed_arbitrary_occurrences"
                ),
                "target_removed_t_ledger": replay_summary.get("target_removed_t_ledger"),
            },
        ),
        requirement(
            "P5",
            "Current state has no accepted certificate, rewrite, resource reduction, or B7 credit",
            replay_summary.get("accepted_symbolic_certificate_count") == 0
            and replay_summary.get("ready_for_b7_ledger_retest_count") == 0
            and replay_summary.get("new_rewrite_claimed") is False
            and replay_summary.get("global_lower_bound_claimed") is False
            and replay_summary.get("physical_resource_reduction_claimed") is False
            and replay_summary.get("b7_ledger_improvement_claimed") is False,
            {
                "accepted_symbolic_certificate_count": replay_summary.get(
                    "accepted_symbolic_certificate_count"
                ),
                "ready_for_b7_ledger_retest_count": replay_summary.get(
                    "ready_for_b7_ledger_retest_count"
                ),
                "new_rewrite_claimed": replay_summary.get("new_rewrite_claimed"),
                "global_lower_bound_claimed": replay_summary.get("global_lower_bound_claimed"),
                "physical_resource_reduction_claimed": replay_summary.get(
                    "physical_resource_reduction_claimed"
                ),
                "b7_ledger_improvement_claimed": replay_summary.get("b7_ledger_improvement_claimed"),
            },
        ),
        requirement(
            "P6",
            "Symbolic certificate acceptance packet has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted acceptance packet satisfies the locked symbolic certificate schema",
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
            "Submitted acceptance packet is source-backed, manifest-bound, certificate-valid, B7-retest-bound, and claim-boundary-safe",
            source_backed
            and manifest_bound
            and certificate_valid
            and b7_retest_bound
            and claim_boundary_bound,
            {
                "source_backed": source_backed,
                "manifest_bound": manifest_bound,
                "certificate_valid": certificate_valid,
                "b7_retest_bound": b7_retest_bound,
                "claim_boundary_bound": claim_boundary_bound,
            },
        ),
        requirement(
            "P9",
            "Forbidden rewrite, lower-bound, resource, and B7-ledger claims remain false",
            replay_summary.get("new_rewrite_claimed") is False
            and replay_summary.get("global_lower_bound_claimed") is False
            and replay_summary.get("physical_resource_reduction_claimed") is False
            and replay_summary.get("b7_ledger_improvement_claimed") is False,
            {
                "new_rewrite_claimed": replay_summary.get("new_rewrite_claimed"),
                "global_lower_bound_claimed": replay_summary.get("global_lower_bound_claimed"),
                "physical_resource_reduction_claimed": replay_summary.get(
                    "physical_resource_reduction_claimed"
                ),
                "b7_ledger_improvement_claimed": replay_summary.get("b7_ledger_improvement_claimed"),
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected symbolic certificate acceptance failures: {failed_ids}")
    if submitted_exists:
        validation_errors.append("gate expected no submitted acceptance packet until a theory PR supplies one")

    summary = {
        "acceptance_packet_id": EXPECTED_ACCEPTANCE_PACKET_ID,
        "priority_packet_id": EXPECTED_PACKET_ID,
        "template_id": EXPECTED_TEMPLATE_ID,
        "provenance_manifest_id": EXPECTED_PROVENANCE_MANIFEST_ID,
        "replay_validation_manifest_id": EXPECTED_REPLAY_MANIFEST_ID,
        "priority_packet_hash": replay_summary.get("priority_packet_hash"),
        "provenance_manifest_hash": replay_summary.get("provenance_manifest_hash"),
        "replay_validation_manifest_hash": replay_summary.get("manifest_hash"),
        "acceptance_packet_hash": acceptance_packet["packet_hash"],
        "acceptance_requirement_count": len(requirements),
        "acceptance_requirements_passed": passed,
        "acceptance_requirements_failed": len(requirements) - passed,
        "failed_acceptance_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "production_required_key_count": len(production_required_keys),
        "required_evidence_file_count": len(required_evidence_files),
        "prior_optimizer_runs": replay_summary.get("prior_optimizer_runs"),
        "three_cnot_attempted_optimizer_runs": replay_summary.get(
            "three_cnot_attempted_optimizer_runs"
        ),
        "three_cnot_passing_candidate_count": replay_summary.get(
            "three_cnot_passing_candidate_count"
        ),
        "target_removed_arbitrary_occurrences": replay_summary.get(
            "target_removed_arbitrary_occurrences"
        ),
        "target_removed_t_ledger": replay_summary.get("target_removed_t_ledger"),
        "submitted_acceptance_packet_exists": submitted_exists,
        "submitted_key_count": len(submitted) if submitted else 0,
        "missing_key_count": len(missing_keys),
        "production_keys_present_count": len(production_present),
        "accepted_symbolic_certificate_count": 0,
        "ready_for_b7_ledger_retest_count": 0,
        "new_rewrite_claimed": False,
        "global_lower_bound_claimed": False,
        "physical_resource_reduction_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "validation_error_count": len(validation_errors),
    }
    return {
        "benchmark_id": "B7",
        "linked_benchmark_id": "B1",
        "problem_id": 21,
        "title": "B7 w8_21 Symbolic Certificate Acceptance Packet Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_replay_validation_manifest_gate": str(args.replay_validation_manifest_gate),
        "source_priority_packet_gate": str(args.priority_packet_gate),
        "summary": summary,
        "symbolic_certificate_acceptance_packet": acceptance_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "The B7 w8_21 route now has an acceptance packet defining what a source-backed "
                "symbolic KAK/local-invariant certificate must contain before it can count."
            ),
            "what_is_not_supported": (
                "No symbolic certificate acceptance packet or symbolic certificate has been "
                "submitted or accepted; no rewrite, global lower bound, physical resource "
                "reduction, or B7 ledger improvement is supported."
            ),
            "next_gate": (
                "Submit B7S1-w8-21-symbolic-certificate-acceptance-packet with replay manifest "
                "hash, normalized target matrix, symbolic coordinates/local invariants, tested "
                "scaffold exclusions, reproducible theorem or notebook output, certificate candidate, "
                "B7 occurrence-ledger retest, uncovered-route statement, and claim boundary."
            ),
            "new_rewrite_claimed": False,
            "global_lower_bound_claimed": False,
            "physical_resource_reduction_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    packet = payload["symbolic_certificate_acceptance_packet"]
    lines = [
        "# B7 w8_21 Symbolic Certificate Acceptance Packet Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Acceptance packet: `{summary['acceptance_packet_id']}`",
        f"- Priority packet: `{summary['priority_packet_id']}`",
        f"- Template: `{summary['template_id']}`",
        f"- Replay-validation manifest: `{summary['replay_validation_manifest_id']}`",
        f"- Replay-validation manifest hash: `{summary['replay_validation_manifest_hash']}`",
        f"- Priority packet hash: `{summary['priority_packet_hash']}`",
        f"- Acceptance packet hash: `{summary['acceptance_packet_hash']}`",
        f"- Requirements passed/failed: `{summary['acceptance_requirements_passed']}` / `{summary['acceptance_requirements_failed']}`",
        f"- Failed requirement IDs: `{summary['failed_acceptance_requirement_ids']}`",
        f"- Required key / production key / evidence file count: `{summary['required_key_count']}` / `{summary['production_required_key_count']}` / `{summary['required_evidence_file_count']}`",
        f"- Prior optimizer runs / three-CNOT attempted / passing: `{summary['prior_optimizer_runs']}` / `{summary['three_cnot_attempted_optimizer_runs']}` / `{summary['three_cnot_passing_candidate_count']}`",
        f"- Target removed arbitrary occurrences / proxy-T ledger: `{summary['target_removed_arbitrary_occurrences']}` / `{summary['target_removed_t_ledger']}`",
        f"- Submitted acceptance packet exists: `{summary['submitted_acceptance_packet_exists']}`",
        f"- Accepted symbolic certificates / ready B7 retests: `{summary['accepted_symbolic_certificate_count']}` / `{summary['ready_for_b7_ledger_retest_count']}`",
        f"- validation_error_count: `{summary['validation_error_count']}`",
        "",
        "## Acceptance Packet",
        "",
        f"- Submission path: `{packet['submission_artifact_path']}`",
        f"- Packet hash: `{packet['packet_hash']}`",
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
            f"- new_rewrite_claimed: {payload['claim_boundary']['new_rewrite_claimed']}",
            f"- global_lower_bound_claimed: {payload['claim_boundary']['global_lower_bound_claimed']}",
            f"- physical_resource_reduction_claimed: {payload['claim_boundary']['physical_resource_reduction_claimed']}",
            f"- b7_ledger_improvement_claimed: {payload['claim_boundary']['b7_ledger_improvement_claimed']}",
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
        "--replay-validation-manifest-gate",
        type=Path,
        default=Path("results/B7_w8_21_symbolic_certificate_replay_validation_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--priority-packet-gate",
        type=Path,
        default=Path("results/B7_w8_21_symbolic_certificate_priority_packet_gate_v0.json"),
    )
    parser.add_argument("--submission-dir", type=Path, default=Path("research/submissions"))
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B7_w8_21_symbolic_certificate_acceptance_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B7_w8_21_symbolic_certificate_acceptance_packet_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-03")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    write_markdown(payload, args.markdown_output)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    if payload["validation_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
