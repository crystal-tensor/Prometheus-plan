#!/usr/bin/env python3
"""T-B7-010c/T-B1-004cv: priority symbolic certificate packet gate for w8_21."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b7_w8_21_symbolic_certificate_priority_packet_gate_v0"
STATUS = "w8_21_symbolic_certificate_priority_packet_open_missing_artifact"
MODEL_STATUS = "w8_21_symbolic_kak_packet_ready_no_artifact_submitted"
VERSION = "0.1"
EXPECTED_PACKET_ID = "B7-S1-w8-21-symbolic-kak-obstruction"
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
    intake = load_json(args.intake_gate)
    summary = intake["summary"]
    packet = next(
        (
            row
            for row in intake["obligation_packets"]
            if row["packet_id"] == EXPECTED_PACKET_ID
        ),
        None,
    )
    submission_path = args.submission_dir / f"{EXPECTED_PACKET_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None
    required_keys = [
        "packet_id",
        "template_id",
        "normalized_target_matrix_hash",
        "symbolic_coordinate_system",
        "local_invariant_expression_hash",
        "tested_scaffold_exclusion_hash",
        "uncovered_route_statement_hash",
        "machine_readable_theorem_or_notebook_hash",
        "reproduction_command",
        "claim_boundary",
    ]
    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    source_backed = (
        submitted is not None
        and submitted.get("source_evidence_files_present") is True
        and not missing_keys
        and submitted.get("template_id") == "w8_21"
        and submitted.get("accepted_certificate") is True
    )

    priority_packet = {
        "packet_id": EXPECTED_PACKET_ID,
        "submission_artifact_path": str(submission_path),
        "source_intake_gate": str(args.intake_gate),
        "owner_role": packet.get("owner_role") if packet else None,
        "acceptance_rule": packet.get("acceptance_rule") if packet else None,
        "required_keys": required_keys,
        "required_evidence_files": [
            "normalized_two_qubit_target_matrix",
            "symbolic_kak_or_local_invariant_coordinates",
            "tested_scaffold_exclusion_table",
            "uncovered_global_route_statement",
            "machine_readable_theorem_or_reproducible_notebook",
            "numeric_search_digest_binding_43480_runs",
            "occurrence_ledger_nonpromotion_note",
            "claim_boundary_note",
        ],
        "accepted_only_if": [
            "packet_id equals B7-S1-w8-21-symbolic-kak-obstruction",
            "template_id equals w8_21",
            "normalized target matrix hash is supplied and source-bound",
            "symbolic coordinates or local invariants are reproducible",
            "tested numerical scaffold exclusions are separated from untested global routes",
            "machine-readable theorem or notebook reproduces the certificate",
            "claim_boundary forbids rewrite, resource reduction, global lower bound, and B7 ledger credit claims",
        ],
    }
    priority_packet["packet_hash"] = stable_hash(priority_packet)

    requirements = [
        requirement(
            "P1",
            "Symbolic obligation intake gate remains valid and blocked only on S5/S6/S7",
            intake.get("method") == "b7_w8_21_symbolic_obligation_intake_gate_v0"
            and summary.get("validation_error_count") == 0
            and summary.get("failed_intake_requirement_ids") == ["S5", "S6", "S7"],
            {
                "source_status": intake.get("status"),
                "failed_intake_requirement_ids": summary.get("failed_intake_requirement_ids"),
                "validation_error_count": summary.get("validation_error_count"),
            },
        ),
        requirement(
            "P2",
            "Priority packet is fixed to the symbolic KAK/local-invariant route",
            packet is not None
            and packet.get("packet_id") == EXPECTED_PACKET_ID
            and packet.get("owner_role") == "theory_agent",
            {
                "expected_packet_id": EXPECTED_PACKET_ID,
                "actual_packet_id": packet.get("packet_id") if packet else None,
                "owner_role": packet.get("owner_role") if packet else None,
            },
        ),
        requirement(
            "P3",
            "Current evidence preserves the 43,480-run negative numerical boundary",
            summary.get("prior_optimizer_runs") == 43480
            and summary.get("three_cnot_attempted_optimizer_runs") == 8880
            and summary.get("three_cnot_passing_candidate_count") == 0,
            {
                "prior_optimizer_runs": summary.get("prior_optimizer_runs"),
                "three_cnot_attempted_optimizer_runs": summary.get(
                    "three_cnot_attempted_optimizer_runs"
                ),
                "three_cnot_passing_candidate_count": summary.get(
                    "three_cnot_passing_candidate_count"
                ),
            },
        ),
        requirement(
            "P4",
            "Packet carries locked schema and evidence file classes",
            len(required_keys) == 10 and len(priority_packet["required_evidence_files"]) == 8,
            {
                "required_key_count": len(required_keys),
                "required_evidence_file_count": len(priority_packet["required_evidence_files"]),
            },
        ),
        requirement(
            "P5",
            "Current B7 state has no accepted symbolic certificate or ledger credit",
            summary.get("submitted_artifact_count") == 0
            and summary.get("accepted_certificate_count") == 0
            and summary.get("ready_for_b7_ledger_retest_count") == 0
            and summary.get("physical_resource_reduction_claimed") is False,
            {
                "submitted_artifact_count": summary.get("submitted_artifact_count"),
                "accepted_certificate_count": summary.get("accepted_certificate_count"),
                "ready_for_b7_ledger_retest_count": summary.get(
                    "ready_for_b7_ledger_retest_count"
                ),
                "physical_resource_reduction_claimed": summary.get(
                    "physical_resource_reduction_claimed"
                ),
            },
        ),
        requirement(
            "P6",
            "Priority symbolic certificate artifact has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted artifact satisfies the locked symbolic certificate schema",
            submitted_exists and not missing_keys,
            {"missing_keys": missing_keys, "submitted_key_count": len(submitted) if submitted else 0},
        ),
        requirement(
            "P8",
            "Submitted artifact is source-backed and accepted as a symbolic certificate",
            source_backed,
            {
                "source_evidence_files_present": submitted.get("source_evidence_files_present")
                if submitted
                else False,
                "accepted_certificate": submitted.get("accepted_certificate") if submitted else False,
                "template_id": submitted.get("template_id") if submitted else None,
            },
        ),
        requirement(
            "P9",
            "Forbidden rewrite, lower-bound, and resource claims remain false",
            intake["claim_boundary"].get("new_rewrite_claimed") is False
            and intake["claim_boundary"].get("global_lower_bound_claimed") is False
            and intake["claim_boundary"].get("physical_resource_reduction_claimed") is False,
            {
                "new_rewrite_claimed": intake["claim_boundary"].get("new_rewrite_claimed"),
                "global_lower_bound_claimed": intake["claim_boundary"].get(
                    "global_lower_bound_claimed"
                ),
                "physical_resource_reduction_claimed": intake["claim_boundary"].get(
                    "physical_resource_reduction_claimed"
                ),
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids not in (EXPECTED_FAILED_IDS, []):
        validation_errors.append(f"unexpected symbolic certificate packet failures: {failed_ids}")

    payload_summary = {
        "priority_packet_id": EXPECTED_PACKET_ID,
        "packet_hash": priority_packet["packet_hash"],
        "priority_requirement_count": len(requirements),
        "priority_requirements_passed": passed,
        "priority_requirements_failed": len(requirements) - passed,
        "failed_priority_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "required_evidence_file_count": len(priority_packet["required_evidence_files"]),
        "template_id": "w8_21",
        "prior_optimizer_runs": summary.get("prior_optimizer_runs"),
        "three_cnot_attempted_optimizer_runs": summary.get(
            "three_cnot_attempted_optimizer_runs"
        ),
        "three_cnot_passing_candidate_count": summary.get("three_cnot_passing_candidate_count"),
        "target_removed_arbitrary_occurrences": summary.get(
            "target_removed_arbitrary_occurrences"
        ),
        "target_removed_t_ledger": summary.get("target_removed_t_ledger"),
        "submitted_artifact_exists": submitted_exists,
        "missing_key_count": len(missing_keys),
        "accepted_symbolic_certificate_count": 0,
        "ready_for_b7_ledger_retest_count": summary.get("ready_for_b7_ledger_retest_count"),
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
        "title": "B7 w8_21 Symbolic Certificate Priority Packet Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS if failed_ids else "w8_21_symbolic_certificate_priority_packet_source_backed",
        "model_status": MODEL_STATUS,
        "source_intake_gate": str(args.intake_gate),
        "summary": payload_summary,
        "priority_symbolic_certificate_packet": priority_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "The first B7 w8_21 theory obligation now has a concrete source-backed "
                "submission packet for symbolic KAK/local-invariant evidence."
            ),
            "what_is_not_supported": (
                "No symbolic obstruction, constructive certificate, occurrence-removing "
                "rewrite, global lower bound, resource reduction, or B7 ledger improvement "
                "is established."
            ),
            "next_gate": (
                "Submit B7-S1-w8-21-symbolic-kak-obstruction with target matrix, "
                "symbolic coordinates/invariants, tested-scaffold exclusions, and "
                "a reproducible theorem or notebook."
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
    packet = payload["priority_symbolic_certificate_packet"]
    lines = [
        "# B7 w8_21 Symbolic Certificate Priority Packet Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Priority packet: `{summary['priority_packet_id']}`",
        f"- Packet hash: `{summary['packet_hash']}`",
        f"- Requirements passed/failed: `{summary['priority_requirements_passed']}` / `{summary['priority_requirements_failed']}`",
        f"- Failed requirement IDs: `{summary['failed_priority_requirement_ids']}`",
        f"- Prior optimizer runs: `{summary['prior_optimizer_runs']}`",
        f"- Three-CNOT attempted runs / passing candidates: `{summary['three_cnot_attempted_optimizer_runs']}` / `{summary['three_cnot_passing_candidate_count']}`",
        f"- Target arbitrary removals / proxy-T ledger: `{summary['target_removed_arbitrary_occurrences']}` / `{summary['target_removed_t_ledger']}`",
        f"- Submitted artifact exists: `{summary['submitted_artifact_exists']}`",
        f"- Accepted symbolic certificates: `{summary['accepted_symbolic_certificate_count']}`",
        f"- B7 ledger improvement claimed: `{summary['b7_ledger_improvement_claimed']}`",
        f"- validation_error_count: `{summary['validation_error_count']}`",
        "",
        "## Submission Packet",
        "",
        f"- Submission path: `{packet['submission_artifact_path']}`",
        f"- Required key count: `{summary['required_key_count']}`",
        f"- Required evidence file count: `{summary['required_evidence_file_count']}`",
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
        status = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- {row['requirement_id']} [{status}]: {row['label']}")
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
        "--intake-gate",
        type=Path,
        default=Path("results/B7_w8_21_symbolic_obligation_intake_gate_v0.json"),
    )
    parser.add_argument(
        "--submission-dir",
        type=Path,
        default=Path("results/B7_w8_21_symbolic_certificate_priority_submissions"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B7_w8_21_symbolic_certificate_priority_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B7_w8_21_symbolic_certificate_priority_packet_gate.md"),
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
