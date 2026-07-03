#!/usr/bin/env python3
"""T-B1-004df/T-B7-012o: R4 B7 ledger replay blocked gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r4_b7_ledger_replay_blocked_gate_v0"
STATUS = "cone01_r4_b7_ledger_replay_blocked_until_exit_route_acceptance"
MODEL_STATUS = "r4_refreshed_b7_ledger_replay_must_wait_for_r1_r2_or_r3_acceptance"
VERSION = "0.1"
R4_PACKET_ID = "B1-B7-cone01-R4-refreshed-B7-ledger-replay"

EXPECTED_METHODS = {
    "triage": "b1_b7_cone01_post_boundary_submission_triage_v0",
    "boundary": "b7_b1_cone01_resource_escape_boundary_v0",
    "r1": "b1_b7_cone01_r1_line1381_resolution_packet_gate_v0",
    "r2": "b1_b7_cone01_r2_line1378_overlap_recovery_packet_gate_v0",
    "r3": "b1_b7_cone01_r3_occurrence_certificate_batch_gate_v0",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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


def exit_route_summary(label: str, payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload["summary"]
    return {
        "route": label,
        "method": payload.get("method"),
        "requirements_passed": summary.get("requirements_passed"),
        "requirements_failed": summary.get("requirements_failed"),
        "failed_requirement_ids": summary.get("failed_requirement_ids"),
        "accepted_exit_route_count": summary.get("accepted_exit_route_count"),
        "accepted_occurrence_removal": summary.get("accepted_occurrence_removal"),
        "accepted_proxy_t_reduction": summary.get("accepted_proxy_t_reduction"),
        "b7_credit_delta": summary.get("b7_credit_delta"),
        "b7_space_time_volume_credit": summary.get("b7_space_time_volume_credit"),
        "submitted_artifact_exists": (
            summary.get("submitted_r1_artifact_exists")
            if label == "R1"
            else summary.get("submitted_r2_artifact_exists")
            if label == "R2"
            else summary.get("submitted_r3_artifact_exists")
        ),
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    triage = load_json(args.post_boundary_triage)
    boundary = load_json(args.b7_resource_boundary)
    r1 = load_json(args.r1_gate)
    r2 = load_json(args.r2_gate)
    r3 = load_json(args.r3_gate)

    triage_summary = triage["summary"]
    boundary_summary = boundary["summary"]
    route_rows = [
        exit_route_summary("R1", r1),
        exit_route_summary("R2", r2),
        exit_route_summary("R3", r3),
    ]
    route_table_hash = stable_hash(route_rows)

    accepted_exit_route_count = sum(row.get("accepted_exit_route_count", 0) for row in route_rows)
    accepted_occurrence_removal = sum(row.get("accepted_occurrence_removal", 0) for row in route_rows)
    accepted_proxy_t_reduction = sum(row.get("accepted_proxy_t_reduction", 0) for row in route_rows)
    b7_credit_delta = sum(row.get("b7_credit_delta", 0) for row in route_rows)
    submitted_route_count = sum(1 for row in route_rows if row.get("submitted_artifact_exists") is True)

    blocked_reasons = [
        "R1 line-1381 resolution artifact is not submitted or accepted",
        "R2 line-1378 overlap-recovery artifact is not submitted or accepted",
        "R3 thirty-certificate occurrence-removal batch is not submitted or accepted",
        "accepted_exit_route_count is 0",
        "accepted_occurrence_removal is 0",
        "accepted_proxy_t_reduction is 0",
        "B7 zero-credit boundary still forbids resource, FT-ledger, occurrence, proxy-T, and STV credit",
    ]
    r4_block_packet = {
        "packet_id": R4_PACKET_ID,
        "work_packet_id": "R4",
        "source_post_boundary_triage": str(args.post_boundary_triage),
        "source_b7_resource_boundary": str(args.b7_resource_boundary),
        "source_r1_gate": str(args.r1_gate),
        "source_r2_gate": str(args.r2_gate),
        "source_r3_gate": str(args.r3_gate),
        "triage_hash": triage_summary.get("triage_hash"),
        "boundary_hash": boundary_summary.get("boundary_hash"),
        "route_table_hash": route_table_hash,
        "route_rows": route_rows,
        "blocked_reasons": blocked_reasons,
        "unblock_only_if": [
            "at least one of R1, R2, or R3 has a source-backed accepted exit route",
            "accepted_exit_route_count is greater than 0",
            "resource_delta_ledger and no-double-counting ledger are accepted by the resource-escape packet",
            "B7 refreshed ledger replay explicitly replays accepted occurrence/proxy-T deltas",
        ],
    }
    r4_block_packet["packet_hash"] = stable_hash(r4_block_packet)

    requirements = [
        requirement(
            "B1",
            "Post-boundary triage keeps R4 blocked",
            triage.get("method") == EXPECTED_METHODS["triage"]
            and "R4" in triage_summary.get("blocked_packet_ids", [])
            and triage_summary.get("accepted_exit_route_count") == 0,
            {
                "method": triage.get("method"),
                "blocked_packet_ids": triage_summary.get("blocked_packet_ids"),
                "accepted_exit_route_count": triage_summary.get("accepted_exit_route_count"),
            },
        ),
        requirement(
            "B2",
            "B7 zero-credit boundary still denies all credit classes",
            boundary.get("method") == EXPECTED_METHODS["boundary"]
            and boundary_summary.get("requirements_passed") == 7
            and boundary_summary.get("b7_resource_credit_allowed") is False
            and boundary_summary.get("b7_ft_ledger_credit_allowed") is False
            and boundary_summary.get("b7_space_time_volume_credit") == 0,
            {
                "method": boundary.get("method"),
                "boundary_hash": boundary_summary.get("boundary_hash"),
                "b7_resource_credit_allowed": boundary_summary.get("b7_resource_credit_allowed"),
                "b7_ft_ledger_credit_allowed": boundary_summary.get("b7_ft_ledger_credit_allowed"),
                "b7_space_time_volume_credit": boundary_summary.get("b7_space_time_volume_credit"),
            },
        ),
        requirement(
            "B3",
            "R1 remains unaccepted with zero credit",
            r1.get("method") == EXPECTED_METHODS["r1"]
            and r1["summary"].get("submitted_r1_artifact_exists") is False
            and r1["summary"].get("accepted_exit_route_count") == 0
            and r1["summary"].get("b7_credit_delta") == 0,
            route_rows[0],
        ),
        requirement(
            "B4",
            "R2 remains unaccepted with zero credit",
            r2.get("method") == EXPECTED_METHODS["r2"]
            and r2["summary"].get("submitted_r2_artifact_exists") is False
            and r2["summary"].get("accepted_exit_route_count") == 0
            and r2["summary"].get("b7_credit_delta") == 0,
            route_rows[1],
        ),
        requirement(
            "B5",
            "R3 remains unaccepted with zero credit",
            r3.get("method") == EXPECTED_METHODS["r3"]
            and r3["summary"].get("submitted_r3_artifact_exists") is False
            and r3["summary"].get("accepted_exit_route_count") == 0
            and r3["summary"].get("b7_credit_delta") == 0,
            route_rows[2],
        ),
        requirement(
            "B6",
            "No accepted occurrence or proxy-T delta exists for B7 replay",
            accepted_exit_route_count == 0
            and accepted_occurrence_removal == 0
            and accepted_proxy_t_reduction == 0
            and b7_credit_delta == 0,
            {
                "accepted_exit_route_count": accepted_exit_route_count,
                "accepted_occurrence_removal": accepted_occurrence_removal,
                "accepted_proxy_t_reduction": accepted_proxy_t_reduction,
                "b7_credit_delta": b7_credit_delta,
            },
        ),
        requirement(
            "B7",
            "R4 block packet is source-bound to the three route gates",
            len(route_rows) == 3
            and route_table_hash == r4_block_packet["route_table_hash"]
            and bool(r4_block_packet["packet_hash"]),
            {
                "route_table_hash": route_table_hash,
                "r4_block_packet_hash": r4_block_packet["packet_hash"],
                "route_count": len(route_rows),
            },
        ),
        requirement(
            "B8",
            "Forbidden resource claims remain false",
            boundary_summary.get("resource_saving_claimed") is False
            and boundary_summary.get("b7_ledger_improvement_claimed") is False
            and boundary_summary.get("b7_space_time_volume_credit") == 0,
            {
                "resource_saving_claimed": boundary_summary.get("resource_saving_claimed"),
                "b7_ledger_improvement_claimed": boundary_summary.get(
                    "b7_ledger_improvement_claimed"
                ),
                "b7_space_time_volume_credit": boundary_summary.get("b7_space_time_volume_credit"),
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids:
        validation_errors.append(f"unexpected R4 block gate failures: {failed_ids}")

    summary = {
        "r4_packet_id": R4_PACKET_ID,
        "r4_block_packet_hash": r4_block_packet["packet_hash"],
        "route_table_hash": route_table_hash,
        "triage_hash": triage_summary.get("triage_hash"),
        "boundary_hash": boundary_summary.get("boundary_hash"),
        "requirement_count": len(requirements),
        "requirements_passed": passed,
        "requirements_failed": len(requirements) - passed,
        "failed_requirement_ids": failed_ids,
        "blocked_packet_ids": triage_summary.get("blocked_packet_ids"),
        "submitted_route_count": submitted_route_count,
        "accepted_exit_route_count": accepted_exit_route_count,
        "accepted_occurrence_removal": accepted_occurrence_removal,
        "accepted_proxy_t_reduction": accepted_proxy_t_reduction,
        "b7_credit_delta": b7_credit_delta,
        "b7_space_time_volume_credit": 0,
        "r4_replay_allowed": False,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "validation_error_count": len(validation_errors),
    }

    return {
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "source_target_id": "T-B1-004df/T-B7-012o",
        "title": "B1/B7 Cone01 R4 B7 Ledger Replay Blocked Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_post_boundary_triage": str(args.post_boundary_triage),
        "source_b7_resource_boundary": str(args.b7_resource_boundary),
        "source_r1_gate": str(args.r1_gate),
        "source_r2_gate": str(args.r2_gate),
        "source_r3_gate": str(args.r3_gate),
        "summary": summary,
        "r4_b7_ledger_replay_block_packet": r4_block_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "R4 refreshed B7 ledger replay is explicitly blocked until at least one of R1/R2/R3 "
                "has an accepted source-backed exit route."
            ),
            "what_is_not_supported": (
                "No refreshed B7 ledger replay, resource credit, FT ledger credit, occurrence removal, "
                "proxy-T reduction, or STV credit is supported."
            ),
            "next_gate": (
                "Accept one of R1, R2, or R3, then submit R4 with refreshed B7 ledger replay, "
                "resource delta replay, no-double-counting ledger, and claim boundary."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "r4_replay_allowed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    block = payload["r4_b7_ledger_replay_block_packet"]
    lines = [
        f"# {payload['title']}",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- R4 packet: `{s['r4_packet_id']}`",
        f"- R4 block hash: `{s['r4_block_packet_hash']}`",
        f"- Route table hash: `{s['route_table_hash']}`",
        "",
        "## Result",
        "",
        (
            f"The R4 B7 ledger replay block gate passes {s['requirements_passed']}/"
            f"{s['requirement_count']} requirements. R4 stays blocked because R1/R2/R3 have "
            f"`{s['accepted_exit_route_count']}` accepted exit routes and `{s['submitted_route_count']}` "
            "submitted route artifacts."
        ),
        "",
        "## Block Reasons",
        "",
    ]
    for reason in block["blocked_reasons"]:
        lines.append(f"- {reason}")
    lines.extend(["", "## Route Rows", ""])
    for row in block["route_rows"]:
        lines.append(
            f"- `{row['route']}` method `{row['method']}`: submitted `{row['submitted_artifact_exists']}`, "
            f"accepted exits `{row['accepted_exit_route_count']}`, occurrence removal "
            f"`{row['accepted_occurrence_removal']}`, proxy-T `{row['accepted_proxy_t_reduction']}`"
        )
    lines.extend(["", "## Requirement Results", ""])
    for row in payload["requirements"]:
        marker = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- `{row['requirement_id']}` {marker}: {row['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            "",
            "This blocked gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, or a solved B1/B7 problem.",
            "",
            "## Validation",
            "",
            f"- validation_error_count: `{s['validation_error_count']}`",
        ]
    )
    for error in payload["validation_errors"]:
        lines.append(f"- {error}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--post-boundary-triage",
        type=Path,
        default=Path("results/B1_B7_cone01_post_boundary_submission_triage_v0.json"),
    )
    parser.add_argument(
        "--b7-resource-boundary",
        type=Path,
        default=Path("results/B7_B1_cone01_resource_escape_boundary_v0.json"),
    )
    parser.add_argument(
        "--r1-gate",
        type=Path,
        default=Path("results/B1_B7_cone01_R1_line1381_resolution_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--r2-gate",
        type=Path,
        default=Path("results/B1_B7_cone01_R2_line1378_overlap_recovery_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--r3-gate",
        type=Path,
        default=Path("results/B1_B7_cone01_R3_occurrence_certificate_batch_gate_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_R4_b7_ledger_replay_blocked_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_R4_b7_ledger_replay_blocked_gate.md"),
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
                "r4_block_packet_hash": payload["summary"]["r4_block_packet_hash"],
                "requirements_passed": payload["summary"]["requirements_passed"],
                "requirements_failed": payload["summary"]["requirements_failed"],
                "accepted_exit_route_count": payload["summary"]["accepted_exit_route_count"],
                "r4_replay_allowed": payload["summary"]["r4_replay_allowed"],
                "validation_error_count": payload["summary"]["validation_error_count"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if payload["validation_errors"]:
        raise SystemExit("B1/B7 R4 B7 ledger replay blocked gate validation failed")


if __name__ == "__main__":
    main()
