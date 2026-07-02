#!/usr/bin/env python3
"""T-B1-004db/T-B7-012j: post-boundary submission triage for cone_01."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_post_boundary_submission_triage_v0"
STATUS = "cone01_post_boundary_submission_triage_ready_no_credit"
MODEL_STATUS = "b7_zero_credit_boundary_split_into_pr_sized_exit_routes"
VERSION = "0.1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2 if pretty else None, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def packet(
    packet_id: str,
    title: str,
    owner_role: str,
    status: str,
    blocker: str,
    expected_artifacts: list[str],
    acceptance_evidence: list[str],
) -> dict[str, Any]:
    return {
        "packet_id": packet_id,
        "title": title,
        "owner_role": owner_role,
        "status": status,
        "blocker": blocker,
        "expected_artifacts": expected_artifacts,
        "acceptance_evidence": acceptance_evidence,
    }


def condition(condition_id: str, label: str, satisfied: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "condition_id": condition_id,
        "label": label,
        "satisfied": bool(satisfied),
        "evidence": evidence,
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    boundary = load_json(args.boundary)
    acceptance = load_json(args.acceptance_packet_gate)
    priority = load_json(args.priority_packet_gate)
    boundary_summary = boundary["summary"]
    acceptance_summary = acceptance["summary"]
    priority_summary = priority["summary"]

    work_packets = [
        packet(
            "R1",
            "Line-1381 off-grid local-U3 resolution route",
            "compiler-agent",
            "ready_for_external_pr_not_credit",
            "line 1381 still has 5 off-grid parameters and 100 unpriced proxy-T pressure",
            [
                "submissions/B1-B7-cone01-resource-escape/line1381_resolution_manifest.json",
                "submissions/B1-B7-cone01-resource-escape/full_replay_or_symbolic_equivalence.json",
                "submissions/B1-B7-cone01-resource-escape/line1381_claim_boundary.md",
            ],
            [
                "line1381_off_grid_parameter_count_after == 0, or honest physical pricing beats the current boundary",
                "full replay or symbolic equivalence is hash-bound",
                "resource delta ledger excludes line-1378 double counting",
            ],
        ),
        packet(
            "R2",
            "Line-1378 recovery without overlap double counting",
            "audit-agent",
            "ready_for_external_pr_not_credit",
            "line 1378 is a dropped overlap candidate and cannot be counted additively",
            [
                "submissions/B1-B7-cone01-resource-escape/line1378_recovery_manifest.json",
                "submissions/B1-B7-cone01-resource-escape/no_double_counting_ledger.json",
                "submissions/B1-B7-cone01-resource-escape/selected_line_window_manifest.json",
            ],
            [
                "line-1378 recovery is source-backed",
                "selected lines [268, 1381] and dropped overlap line [1378] are reconciled",
                "the refreshed ledger accepts a non-overlap delta",
            ],
        ),
        packet(
            "R3",
            "Thirty occurrence-removing certificates",
            "synthesis-agent",
            "ready_for_external_pr_not_credit",
            "no batch of 30 accepted occurrence-removing certificates exists",
            [
                "submissions/B1-B7-cone01-resource-escape/occurrence_certificate_batch.json",
                "submissions/B1-B7-cone01-resource-escape/certificate_replay_bundle/",
                "submissions/B1-B7-cone01-resource-escape/resource_delta_ledger.json",
            ],
            [
                "accepted_occurrence_removal >= 30",
                "accepted_proxy_t_reduction >= 600",
                "each certificate has replay or symbolic-equivalence evidence",
            ],
        ),
        packet(
            "R4",
            "B7 refreshed ledger replay after an accepted exit route",
            "fault-tolerance-agent",
            "blocked_until_R1_or_R2_or_R3_accepts",
            "B7 ledger replay cannot count credit before an exit route is accepted",
            [
                "submissions/B1-B7-cone01-resource-escape/b7_refreshed_ledger_replay.json",
                "submissions/B1-B7-cone01-resource-escape/b7_credit_boundary.json",
            ],
            [
                "one of R1/R2/R3 is accepted by the resource-escape acceptance packet",
                "b7_credit_delta is computed with no double counting",
                "B7 resource/FT ledger/STV credit remains false until the ledger accepts the route",
            ],
        ),
    ]
    ready_packets = [p for p in work_packets if p["status"] == "ready_for_external_pr_not_credit"]
    blocked_packets = [p for p in work_packets if p["status"].startswith("blocked_")]
    triage_packet = {
        "triage_id": "B1-B7-cone01-post-boundary-submission-triage",
        "source_boundary": str(args.boundary),
        "source_acceptance_packet_gate": str(args.acceptance_packet_gate),
        "source_priority_packet_gate": str(args.priority_packet_gate),
        "boundary_hash": boundary_summary.get("boundary_hash"),
        "acceptance_packet_hash": boundary_summary.get("source_acceptance_packet_hash"),
        "priority_packet_hash": acceptance_summary.get("priority_packet_hash"),
        "selected_line_numbers": boundary_summary.get("selected_line_numbers"),
        "dropped_overlap_candidate_line_numbers": boundary_summary.get(
            "dropped_overlap_candidate_line_numbers"
        ),
        "line1381_off_grid_parameter_count": boundary_summary.get(
            "line1381_off_grid_parameter_count"
        ),
        "line1381_unpriced_proxy_t_pressure": boundary_summary.get(
            "line1381_unpriced_proxy_t_pressure"
        ),
        "accepted_exit_route_count": boundary_summary.get("accepted_exit_route_count"),
        "accepted_occurrence_removal": boundary_summary.get("accepted_occurrence_removal"),
        "accepted_proxy_t_reduction": boundary_summary.get("accepted_proxy_t_reduction"),
        "b7_resource_credit_allowed": False,
        "b7_ft_ledger_credit_allowed": False,
        "b7_space_time_volume_credit": 0,
        "work_packet_ids": [p["packet_id"] for p in work_packets],
    }
    triage_packet["triage_hash"] = stable_hash(triage_packet)

    conditions = [
        condition(
            "C1",
            "Source B7/B1 zero-credit boundary is current and valid",
            boundary.get("method") == "b7_b1_cone01_resource_escape_boundary_v0"
            and boundary_summary.get("requirements_failed") == 0
            and boundary_summary.get("validation_error_count") == 0,
            {
                "source_method": boundary.get("method"),
                "requirements_failed": boundary_summary.get("requirements_failed"),
                "validation_error_count": boundary_summary.get("validation_error_count"),
            },
        ),
        condition(
            "C2",
            "The source acceptance packet remains blocked on missing submitted evidence",
            acceptance.get("method") == "b1_b7_cone01_resource_escape_acceptance_packet_gate_v0"
            and acceptance_summary.get("failed_acceptance_requirement_ids") == ["P6", "P7", "P8"]
            and acceptance_summary.get("submitted_acceptance_packet_exists") is False,
            {
                "failed_acceptance_requirement_ids": acceptance_summary.get(
                    "failed_acceptance_requirement_ids"
                ),
                "submitted_acceptance_packet_exists": acceptance_summary.get(
                    "submitted_acceptance_packet_exists"
                ),
            },
        ),
        condition(
            "C3",
            "The active cone_01 resource blockers are preserved",
            boundary_summary.get("selected_line_numbers") == [268, 1381]
            and boundary_summary.get("dropped_overlap_candidate_line_numbers") == [1378]
            and boundary_summary.get("line1381_off_grid_parameter_count") == 5
            and boundary_summary.get("line1381_unpriced_proxy_t_pressure") == 100,
            {
                "selected_line_numbers": boundary_summary.get("selected_line_numbers"),
                "dropped_overlap_candidate_line_numbers": boundary_summary.get(
                    "dropped_overlap_candidate_line_numbers"
                ),
                "line1381_off_grid_parameter_count": boundary_summary.get(
                    "line1381_off_grid_parameter_count"
                ),
                "line1381_unpriced_proxy_t_pressure": boundary_summary.get(
                    "line1381_unpriced_proxy_t_pressure"
                ),
            },
        ),
        condition(
            "C4",
            "Three independent exit-route PR packets are ready for external agents",
            [p["packet_id"] for p in ready_packets] == ["R1", "R2", "R3"],
            {"ready_packet_ids": [p["packet_id"] for p in ready_packets]},
        ),
        condition(
            "C5",
            "B7 ledger replay is correctly blocked until an exit route is accepted",
            [p["packet_id"] for p in blocked_packets] == ["R4"]
            and boundary_summary.get("accepted_exit_route_count") == 0,
            {
                "blocked_packet_ids": [p["packet_id"] for p in blocked_packets],
                "accepted_exit_route_count": boundary_summary.get("accepted_exit_route_count"),
            },
        ),
        condition(
            "C6",
            "Forbidden B1/B7 credit and resource claims remain false",
            boundary_summary.get("b7_resource_credit_allowed") is False
            and boundary_summary.get("b7_ft_ledger_credit_allowed") is False
            and boundary_summary.get("b7_space_time_volume_credit") == 0
            and priority_summary.get("resource_saving_claimed") is False
            and priority_summary.get("b7_ledger_improvement_claimed") is False,
            {
                "b7_resource_credit_allowed": boundary_summary.get("b7_resource_credit_allowed"),
                "b7_ft_ledger_credit_allowed": boundary_summary.get("b7_ft_ledger_credit_allowed"),
                "b7_space_time_volume_credit": boundary_summary.get("b7_space_time_volume_credit"),
                "resource_saving_claimed": priority_summary.get("resource_saving_claimed"),
                "b7_ledger_improvement_claimed": priority_summary.get(
                    "b7_ledger_improvement_claimed"
                ),
            },
        ),
    ]
    satisfied = sum(row["satisfied"] for row in conditions)
    failed_ids = [row["condition_id"] for row in conditions if not row["satisfied"]]
    validation_errors = []
    if failed_ids:
        validation_errors.append(f"post-boundary submission triage failed: {failed_ids}")
    if len(work_packets) != 4 or len(ready_packets) != 3 or len(blocked_packets) != 1:
        validation_errors.append("unexpected work-packet shape")

    summary = {
        "triage_id": triage_packet["triage_id"],
        "triage_hash": triage_packet["triage_hash"],
        "source_boundary_hash": boundary_summary.get("boundary_hash"),
        "source_acceptance_packet_hash": boundary_summary.get("source_acceptance_packet_hash"),
        "priority_packet_hash": acceptance_summary.get("priority_packet_hash"),
        "work_packet_count": len(work_packets),
        "ready_external_pr_packet_count": len(ready_packets),
        "blocked_packet_count": len(blocked_packets),
        "ready_packet_ids": [p["packet_id"] for p in ready_packets],
        "blocked_packet_ids": [p["packet_id"] for p in blocked_packets],
        "condition_count": len(conditions),
        "conditions_satisfied": satisfied,
        "conditions_failed": len(conditions) - satisfied,
        "failed_condition_ids": failed_ids,
        "selected_line_numbers": boundary_summary.get("selected_line_numbers"),
        "dropped_overlap_candidate_line_numbers": boundary_summary.get(
            "dropped_overlap_candidate_line_numbers"
        ),
        "line1381_off_grid_parameter_count": boundary_summary.get(
            "line1381_off_grid_parameter_count"
        ),
        "line1381_unpriced_proxy_t_pressure": boundary_summary.get(
            "line1381_unpriced_proxy_t_pressure"
        ),
        "accepted_exit_route_count": boundary_summary.get("accepted_exit_route_count"),
        "accepted_occurrence_removal": boundary_summary.get("accepted_occurrence_removal"),
        "accepted_proxy_t_reduction": boundary_summary.get("accepted_proxy_t_reduction"),
        "b7_resource_credit_allowed": False,
        "b7_ft_ledger_credit_allowed": False,
        "b7_space_time_volume_credit": 0,
        "b1_resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "validation_error_count": len(validation_errors),
    }
    return {
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "source_target_id": "T-B1-004db/T-B7-012j",
        "title": "B1/B7 Cone01 Post-Boundary Submission Triage",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_boundary": str(args.boundary),
        "source_acceptance_packet_gate": str(args.acceptance_packet_gate),
        "source_priority_packet_gate": str(args.priority_packet_gate),
        "summary": summary,
        "triage_packet": triage_packet,
        "work_packets": work_packets,
        "conditions": conditions,
        "claim_boundary": {
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "b7_resource_credit_allowed": False,
            "b7_ft_ledger_credit_allowed": False,
            "b7_space_time_volume_credit": 0,
            "quantum_advantage_claimed": False,
            "problem_solved_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": time.time() - started,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    lines = [
        f"# {payload['title']}",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Triage hash: `{s['triage_hash']}`",
        f"- Source boundary hash: `{s['source_boundary_hash']}`",
        f"- Source acceptance packet hash: `{s['source_acceptance_packet_hash']}`",
        "",
        "## Result",
        "",
        (
            f"The post-boundary triage satisfies {s['conditions_satisfied']}/"
            f"{s['condition_count']} conditions and emits {s['work_packet_count']} PR-sized work packets."
        ),
        (
            f"Ready external PR packets: {', '.join(s['ready_packet_ids'])}. "
            f"Blocked packet: {', '.join(s['blocked_packet_ids'])}."
        ),
        "",
        "## Work Packets",
        "",
        "| Packet | Status | Blocker |",
        "| --- | --- | --- |",
    ]
    for packet_row in payload["work_packets"]:
        lines.append(
            f"| {packet_row['packet_id']} | {packet_row['status']} | {packet_row['blocker']} |"
        )
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            f"- Selected lines: `{s['selected_line_numbers']}`",
            f"- Dropped overlap line: `{s['dropped_overlap_candidate_line_numbers']}`",
            f"- Line 1381 off-grid parameters: `{s['line1381_off_grid_parameter_count']}`",
            f"- Line 1381 unpriced proxy-T pressure: `{s['line1381_unpriced_proxy_t_pressure']}`",
            f"- Accepted exit routes: `{s['accepted_exit_route_count']}`",
            f"- Accepted occurrence removal: `{s['accepted_occurrence_removal']}`",
            f"- Accepted proxy-T reduction: `{s['accepted_proxy_t_reduction']}`",
            f"- B7 resource credit allowed: `{s['b7_resource_credit_allowed']}`",
            f"- B7 FT ledger credit allowed: `{s['b7_ft_ledger_credit_allowed']}`",
            "",
            "## Claim Boundary",
            "",
            "This is a triage result, not a resource-saving result. It does not claim B1 compression credit, B7 resource credit, FT ledger credit, quantum advantage, or a solved problem.",
            "",
            "## Validation",
            "",
            f"- Validation errors: `{s['validation_error_count']}`",
        ]
    )
    for row in payload["conditions"]:
        marker = "PASS" if row["satisfied"] else "FAIL"
        lines.append(f"- `{row['condition_id']}` {marker}: {row['label']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--boundary",
        type=Path,
        default=Path("results/B7_B1_cone01_resource_escape_boundary_v0.json"),
    )
    parser.add_argument(
        "--acceptance-packet-gate",
        type=Path,
        default=Path("results/B1_B7_cone01_resource_escape_acceptance_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--priority-packet-gate",
        type=Path,
        default=Path("results/B1_B7_cone01_resource_escape_priority_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_post_boundary_submission_triage_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_post_boundary_submission_triage.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-03")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_markdown(payload), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": payload["status"],
                "triage_hash": payload["summary"]["triage_hash"],
                "conditions_satisfied": payload["summary"]["conditions_satisfied"],
                "conditions_failed": payload["summary"]["conditions_failed"],
                "ready_packet_ids": payload["summary"]["ready_packet_ids"],
                "blocked_packet_ids": payload["summary"]["blocked_packet_ids"],
                "validation_error_count": payload["summary"]["validation_error_count"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if payload["validation_errors"]:
        raise SystemExit("B1/B7 cone01 post-boundary submission triage validation failed")


if __name__ == "__main__":
    main()
