#!/usr/bin/env python3
"""T-B3-041/T-B10-015ab: P8 pressure gate for the submitted B3/B10 F1 packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b3_b10_f1_p8_acceptance_pressure_gate_v0"
STATUS = "b3_b10_f1_p8_pressure_ready_zero_credit"
MODEL_STATUS = "submitted_f1_acceptance_packet_p8_blocker_decomposed_before_credit"
VERSION = "0.1"
EXPECTED_ACCEPTANCE_PACKET_ID = "B3-R1-full-covariance-row-acceptance-packet"
EXPECTED_ACCEPTANCE_GATE_METHOD = "b3_b10_full_covariance_row_acceptance_packet_gate_v0"
EXPECTED_ACCEPTANCE_SUBMISSION_HASH = "40a5a0903de970b798f94d371c4d3cd6ccbdab9e514044ba760e05ac5db756cc"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2 if pretty else None, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def condition(condition_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "condition_id": condition_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def work_packet(
    packet_id: str,
    title: str,
    owner_role: str,
    status: str,
    blocker: str,
    required_evidence: list[str],
    acceptance_predicate: str,
) -> dict[str, Any]:
    return {
        "packet_id": packet_id,
        "title": title,
        "owner_role": owner_role,
        "status": status,
        "blocker": blocker,
        "required_evidence": required_evidence,
        "acceptance_predicate": acceptance_predicate,
    }


def get_requirement(payload: dict[str, Any], requirement_id: str) -> dict[str, Any]:
    for row in payload.get("requirements", []):
        if row.get("requirement_id") == requirement_id:
            return row
    return {}


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    acceptance_gate = load_json(args.acceptance_packet_gate)
    submission = load_json(args.acceptance_packet_submission)
    gate_summary = acceptance_gate["summary"]
    p8 = get_requirement(acceptance_gate, "P8")
    p8_evidence = p8.get("evidence", {})

    row_acceptance_subchecks = {
        "accepted_full_covariance_row_count_positive": submission.get("accepted_full_covariance_row_count", 0)
        > 0,
        "denominator_win_count_positive": submission.get("denominator_win_count", 0) > 0,
        "optimizer_loop_total_shots_lower_bound_locked": submission.get(
            "optimizer_loop_total_shots_lower_bound"
        )
        == gate_summary.get("max_optimizer_loop_total_shots_lower_bound"),
        "row_scope_hash_present": bool(submission.get("row_scope_hash")),
        "full_covariance_row_table_hash_present": bool(submission.get("full_covariance_row_table_hash")),
        "compiled_state_replay_hash_present": bool(submission.get("compiled_state_replay_hash")),
        "pauli_grouping_covariance_replay_hash_present": bool(
            submission.get("pauli_grouping_covariance_replay_hash")
        ),
        "derivative_estimator_replay_hash_present": bool(
            submission.get("derivative_estimator_replay_hash")
        ),
        "same_access_decision_hash_present": bool(submission.get("same_access_decision_hash")),
    }
    row_acceptance_blockers = [
        key for key, value in row_acceptance_subchecks.items() if value is False
    ]

    pressure_packets = [
        work_packet(
            "P8-A",
            "Accepted-row validity replay",
            "chemistry-measurement-agent",
            "ready_for_external_pr_not_credit",
            "accepted_full_covariance_row_count is still 0",
            [
                "row-level observable table for H2/H2O/N2/LiH",
                "compiled-state replay command transcript",
                "row acceptance ledger with at least one accepted row",
                "hash-bound replay bundle matching the submitted F1 packet",
            ],
            "accepted_full_covariance_row_count > 0 with replayable row evidence",
        ),
        work_packet(
            "P8-B",
            "Same-access denominator win replay",
            "baseline-adversary",
            "ready_for_external_pr_not_credit",
            "denominator_win_count is still 0",
            [
                "same-access denominator comparison table",
                "selected-CI/FCI replay transcript or stronger denominator replay",
                "access-model note proving no hidden data-loading advantage",
                "decision hash replacing the current negative same-access decision",
            ],
            "denominator_win_count > 0 under the locked same-access model",
        ),
        work_packet(
            "P8-C",
            "Derivative and optimizer-loop replay pressure",
            "measurement-optimization-agent",
            "ready_for_external_pr_not_credit",
            "derivative and optimizer-loop evidence is hash-present but not yet acceptance-positive",
            [
                "derivative estimator replay transcript",
                "optimizer-loop cost ledger with state-prep and measurement charging",
                "shot, circuit, and observable-count delta report",
                "nonpromotion note if no cost collapse is achieved",
            ],
            "derivative replay and optimizer ledger support the same accepted row and denominator comparison",
        ),
        work_packet(
            "P8-D",
            "B10 access-boundary replay",
            "bqp-boundary-agent",
            "blocked_until_P8_A_B_C_pass",
            "B10-T1 credit is explicitly false until accepted rows and denominator wins exist",
            [
                "B10 access-boundary note",
                "positive same-access route claim boundary",
                "BQP/advantage nonclaim ledger",
                "dependency trace from accepted B3 rows to B10-T1 boundary",
            ],
            "B10-T1 remains zero-credit until P8-A/P8-B/P8-C evidence is accepted",
        ),
        work_packet(
            "P8-E",
            "Claim-boundary audit",
            "audit-agent",
            "ready_for_external_pr_not_credit",
            "the submitted packet must stay zero-credit while P8 is attacked",
            [
                "claim-boundary diff",
                "forbidden-claim scan",
                "benchmark YAML and landing-page status update",
                "portfolio audit transcript",
            ],
            "no B3 reopen, reaction-dynamics solution, advantage, or BQP claim before P8 passes",
        ),
    ]
    ready_packets = [
        packet["packet_id"] for packet in pressure_packets if packet["status"] == "ready_for_external_pr_not_credit"
    ]
    blocked_packets = [
        packet["packet_id"] for packet in pressure_packets if packet["status"].startswith("blocked_")
    ]

    p8_pressure_packet = {
        "pressure_packet_id": "B3B10-F1-P8-acceptance-pressure",
        "acceptance_packet_id": EXPECTED_ACCEPTANCE_PACKET_ID,
        "source_acceptance_packet_gate": str(args.acceptance_packet_gate),
        "source_acceptance_packet_submission": str(args.acceptance_packet_submission),
        "acceptance_submission_hash": submission.get("acceptance_submission_hash"),
        "row_bundle_hash": submission.get("row_scope", {}).get("row_bundle_hash"),
        "p8_evidence": p8_evidence,
        "row_acceptance_subchecks": row_acceptance_subchecks,
        "row_acceptance_blockers": row_acceptance_blockers,
        "pressure_packet_ids": [packet["packet_id"] for packet in pressure_packets],
    }
    p8_pressure_packet["pressure_packet_hash"] = stable_hash(p8_pressure_packet)

    conditions = [
        condition(
            "C1",
            "Source acceptance gate is the submitted zero-credit F1 gate",
            acceptance_gate.get("method") == EXPECTED_ACCEPTANCE_GATE_METHOD
            and gate_summary.get("submitted_acceptance_packet_exists") is True
            and gate_summary.get("acceptance_submission_hash") == EXPECTED_ACCEPTANCE_SUBMISSION_HASH
            and gate_summary.get("validation_error_count") == 0,
            {
                "method": acceptance_gate.get("method"),
                "submitted_acceptance_packet_exists": gate_summary.get(
                    "submitted_acceptance_packet_exists"
                ),
                "acceptance_submission_hash": gate_summary.get("acceptance_submission_hash"),
                "validation_error_count": gate_summary.get("validation_error_count"),
            },
        ),
        condition(
            "C2",
            "P8 is isolated as the only failed acceptance requirement",
            gate_summary.get("failed_acceptance_requirement_ids") == ["P8"]
            and gate_summary.get("acceptance_requirements_passed") == 8
            and gate_summary.get("acceptance_requirements_failed") == 1,
            {
                "failed_acceptance_requirement_ids": gate_summary.get(
                    "failed_acceptance_requirement_ids"
                ),
                "acceptance_requirements_passed": gate_summary.get("acceptance_requirements_passed"),
                "acceptance_requirements_failed": gate_summary.get("acceptance_requirements_failed"),
            },
        ),
        condition(
            "C3",
            "Source and manifest binding subconditions already pass",
            p8_evidence.get("source_backed") is True and p8_evidence.get("manifest_bound") is True,
            {
                "source_backed": p8_evidence.get("source_backed"),
                "manifest_bound": p8_evidence.get("manifest_bound"),
            },
        ),
        condition(
            "C4",
            "Row-acceptance validity remains the live blocker",
            p8_evidence.get("row_acceptance_valid") is False
            and row_acceptance_blockers
            == ["accepted_full_covariance_row_count_positive", "denominator_win_count_positive"],
            {
                "row_acceptance_valid": p8_evidence.get("row_acceptance_valid"),
                "row_acceptance_blockers": row_acceptance_blockers,
                "row_acceptance_subchecks": row_acceptance_subchecks,
            },
        ),
        condition(
            "C5",
            "B3, B10, and claim-boundary bindings still pass",
            p8_evidence.get("b3_boundary_bound") is True
            and p8_evidence.get("b10_boundary_bound") is True
            and p8_evidence.get("claim_boundary_bound") is True,
            {
                "b3_boundary_bound": p8_evidence.get("b3_boundary_bound"),
                "b10_boundary_bound": p8_evidence.get("b10_boundary_bound"),
                "claim_boundary_bound": p8_evidence.get("claim_boundary_bound"),
            },
        ),
        condition(
            "C6",
            "Zero-credit boundary remains locked while P8 is attacked",
            submission.get("accepted_full_covariance_row_count") == 0
            and submission.get("denominator_win_count") == 0
            and submission.get("b3_reopen_boundary", {}).get("b3_reopen_ready") is False
            and submission.get("b10_access_boundary", {}).get("b10_t1_credit_allowed") is False
            and submission.get("claim_boundary", {}).get("quantum_advantage_claimed") is False
            and submission.get("claim_boundary", {}).get("bqp_separation_claimed") is False,
            {
                "accepted_full_covariance_row_count": submission.get(
                    "accepted_full_covariance_row_count"
                ),
                "denominator_win_count": submission.get("denominator_win_count"),
                "b3_reopen_ready": submission.get("b3_reopen_boundary", {}).get("b3_reopen_ready"),
                "b10_t1_credit_allowed": submission.get("b10_access_boundary", {}).get(
                    "b10_t1_credit_allowed"
                ),
                "quantum_advantage_claimed": submission.get("claim_boundary", {}).get(
                    "quantum_advantage_claimed"
                ),
                "bqp_separation_claimed": submission.get("claim_boundary", {}).get(
                    "bqp_separation_claimed"
                ),
            },
        ),
        condition(
            "C7",
            "P8 pressure is split into PR-sized packets",
            ready_packets == ["P8-A", "P8-B", "P8-C", "P8-E"] and blocked_packets == ["P8-D"],
            {"ready_packet_ids": ready_packets, "blocked_packet_ids": blocked_packets},
        ),
    ]

    passed = sum(row["passed"] for row in conditions)
    failed_ids = [row["condition_id"] for row in conditions if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids:
        validation_errors.append(f"unexpected P8 pressure condition failures: {failed_ids}")

    summary = {
        "pressure_packet_id": p8_pressure_packet["pressure_packet_id"],
        "pressure_packet_hash": p8_pressure_packet["pressure_packet_hash"],
        "acceptance_packet_id": EXPECTED_ACCEPTANCE_PACKET_ID,
        "acceptance_submission_hash": submission.get("acceptance_submission_hash"),
        "row_bundle_hash": submission.get("row_scope", {}).get("row_bundle_hash"),
        "source_failed_acceptance_requirement_ids": gate_summary.get(
            "failed_acceptance_requirement_ids"
        ),
        "p8_source_backed": p8_evidence.get("source_backed"),
        "p8_manifest_bound": p8_evidence.get("manifest_bound"),
        "p8_row_acceptance_valid": p8_evidence.get("row_acceptance_valid"),
        "p8_b3_boundary_bound": p8_evidence.get("b3_boundary_bound"),
        "p8_b10_boundary_bound": p8_evidence.get("b10_boundary_bound"),
        "p8_claim_boundary_bound": p8_evidence.get("claim_boundary_bound"),
        "row_acceptance_blocker_count": len(row_acceptance_blockers),
        "row_acceptance_blockers": row_acceptance_blockers,
        "ready_pressure_packet_count": len(ready_packets),
        "blocked_pressure_packet_count": len(blocked_packets),
        "ready_pressure_packet_ids": ready_packets,
        "blocked_pressure_packet_ids": blocked_packets,
        "accepted_full_covariance_row_count": submission.get("accepted_full_covariance_row_count"),
        "denominator_win_count": submission.get("denominator_win_count"),
        "b3_reopen_ready": False,
        "b10_t1_credit_allowed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "conditions_passed": passed,
        "conditions_failed": len(conditions) - passed,
        "failed_condition_ids": failed_ids,
        "validation_error_count": len(validation_errors),
    }

    return {
        "benchmark_id": "B3_B10",
        "problem_ids": [49, 11],
        "title": "B3/B10 F1 P8 Acceptance Pressure Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_acceptance_packet_gate": str(args.acceptance_packet_gate),
        "source_acceptance_packet_submission": str(args.acceptance_packet_submission),
        "source_target_id": "B10-T1",
        "dependency_benchmarks": ["B3", "B10"],
        "summary": summary,
        "p8_pressure_packet": p8_pressure_packet,
        "pressure_packets": pressure_packets,
        "conditions": conditions,
        "claim_boundary": {
            "what_is_supported": (
                "The submitted B3/B10 F1 acceptance packet now has a machine-readable P8 "
                "pressure decomposition. Source and manifest binding pass; row acceptance is "
                "blocked only by accepted-row and denominator-win positivity."
            ),
            "what_is_not_supported": (
                "P8 is not solved. The gate records zero accepted full-covariance rows, zero "
                "denominator wins, no B3 reopen, no B10-T1 credit, no quantum advantage, and no "
                "BQP separation."
            ),
            "next_gate": (
                "Submit evidence for P8-A and P8-B first: at least one replayable accepted row "
                "and at least one same-access denominator win, then bind derivative/optimizer "
                "replay before any B10 access-boundary promotion."
            ),
            "accepted_full_covariance_row_count": submission.get("accepted_full_covariance_row_count"),
            "denominator_win_count": submission.get("denominator_win_count"),
            "b3_reopen_ready": False,
            "b10_t1_credit_allowed": False,
            "quantum_advantage_claimed": False,
            "bqp_separation_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# B3/B10 F1 P8 Acceptance Pressure Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Pressure packet: `{summary['pressure_packet_id']}`",
        f"- Pressure packet hash: `{summary['pressure_packet_hash']}`",
        f"- Acceptance packet: `{summary['acceptance_packet_id']}`",
        f"- Acceptance submission hash: `{summary['acceptance_submission_hash']}`",
        f"- Row bundle hash: `{summary['row_bundle_hash']}`",
        f"- Source failed acceptance IDs: `{summary['source_failed_acceptance_requirement_ids']}`",
        f"- P8 source/manifest/row-valid: `{summary['p8_source_backed']}` / `{summary['p8_manifest_bound']}` / `{summary['p8_row_acceptance_valid']}`",
        f"- P8 B3/B10/claim boundaries: `{summary['p8_b3_boundary_bound']}` / `{summary['p8_b10_boundary_bound']}` / `{summary['p8_claim_boundary_bound']}`",
        f"- Row-acceptance blockers: `{summary['row_acceptance_blockers']}`",
        f"- Ready / blocked pressure packets: `{summary['ready_pressure_packet_count']}` / `{summary['blocked_pressure_packet_count']}`",
        f"- Accepted rows / denominator wins: `{summary['accepted_full_covariance_row_count']}` / `{summary['denominator_win_count']}`",
        f"- validation_error_count: `{summary['validation_error_count']}`",
        "",
        "## Pressure Packets",
        "",
    ]
    for packet in payload["pressure_packets"]:
        lines.extend(
            [
                f"### {packet['packet_id']}: {packet['title']}",
                "",
                f"- Owner role: `{packet['owner_role']}`",
                f"- Status: `{packet['status']}`",
                f"- Blocker: {packet['blocker']}",
                f"- Acceptance predicate: {packet['acceptance_predicate']}",
                "- Required evidence:",
            ]
        )
        lines.extend(f"  - {item}" for item in packet["required_evidence"])
        lines.append("")
    lines.extend(["## Condition Results", ""])
    for row in payload["conditions"]:
        state = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- {row['condition_id']} [{state}]: {row['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            f"- accepted_full_covariance_row_count: {payload['claim_boundary']['accepted_full_covariance_row_count']}",
            f"- denominator_win_count: {payload['claim_boundary']['denominator_win_count']}",
            f"- b3_reopen_ready: {payload['claim_boundary']['b3_reopen_ready']}",
            f"- b10_t1_credit_allowed: {payload['claim_boundary']['b10_t1_credit_allowed']}",
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
        "--acceptance-packet-gate",
        type=Path,
        default=Path("results/B3_B10_full_covariance_row_acceptance_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--acceptance-packet-submission",
        type=Path,
        default=Path(
            "results/B3_B10_full_covariance_row_acceptance_packet_submissions/"
            "B3-R1-full-covariance-row-acceptance-packet.json"
        ),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B3_B10_F1_P8_acceptance_pressure_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B3_B10_F1_P8_acceptance_pressure_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-03")
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
