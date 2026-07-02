#!/usr/bin/env python3
"""T-B3-044/T-B10-015ae: P8-C derivative/optimizer promotion readiness gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b3_b10_p8c_derivative_optimizer_promotion_readiness_gate_v0"
STATUS = "b3_b10_p8c_derivative_optimizer_promotion_blocked_missing_p8a_p8b_evidence"
MODEL_STATUS = "p8c_promotion_blocked_until_row_and_denominator_replay_positive"
VERSION = "0.1"
EXPECTED_FAILED_IDS = ["C6", "C7", "C8"]
EXPECTED_PRESSURE_PACKET_HASH = "55384c1a143b50d9b334193c3e55151f33bc9511b90dd19a21f22198bf9fe0b0"
EXPECTED_P8A_TEMPLATE_TABLE_HASH = "a82007811e0448e2436857aaf22ca5fcf30060a1d032370f8f8e8252848584a2"
EXPECTED_P8B_TEMPLATE_TABLE_HASH = "95ea8fecbfb592aae2491ec95d4dc6b19d0b12e98b4dfdbee0087499cfe523ba"


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
    p8_pressure = load_json(args.p8_pressure_gate)
    p8a = load_json(args.p8a_intake_gate)
    p8b = load_json(args.p8b_intake_gate)
    pressure_summary = p8_pressure["summary"]
    p8a_summary = p8a["summary"]
    p8b_summary = p8b["summary"]

    p8c_dependencies = [
        {
            "dependency_id": "P8-source-pressure",
            "artifact": str(args.p8_pressure_gate),
            "hash": pressure_summary.get("pressure_packet_hash"),
            "required_state": "P8-C appears in ready_pressure_packet_ids",
            "current_state": "P8-C listed but still downstream of row and denominator positivity",
            "satisfied": "P8-C" in pressure_summary.get("ready_pressure_packet_ids", []),
        },
        {
            "dependency_id": "P8-A-accepted-row-replay",
            "artifact": str(args.p8a_intake_gate),
            "hash": p8a_summary.get("template_table_hash"),
            "required_state": "accepted_full_covariance_row_count > 0",
            "current_state": f"accepted_full_covariance_row_count={p8a_summary.get('accepted_full_covariance_row_count')}",
            "satisfied": p8a_summary.get("accepted_full_covariance_row_count", 0) > 0,
        },
        {
            "dependency_id": "P8-B-same-access-denominator-replay",
            "artifact": str(args.p8b_intake_gate),
            "hash": p8b_summary.get("template_table_hash"),
            "required_state": "accepted_denominator_win_row_count > 0",
            "current_state": (
                "accepted_denominator_win_row_count="
                f"{p8b_summary.get('accepted_denominator_win_row_count')}"
            ),
            "satisfied": p8b_summary.get("accepted_denominator_win_row_count", 0) > 0,
        },
    ]
    dependency_table_hash = stable_hash(p8c_dependencies)
    accepted_row_count = int(p8a_summary.get("accepted_full_covariance_row_count", 0))
    accepted_denominator_win_count = int(p8b_summary.get("accepted_denominator_win_row_count", 0))
    denominator_win_count = int(p8b_summary.get("denominator_win_count", 0))
    p8c_ready = accepted_row_count > 0 and accepted_denominator_win_count > 0

    requirements = [
        requirement(
            "C1",
            "P8 pressure gate is current and lists P8-C as a decomposed pressure packet",
            p8_pressure.get("method") == "b3_b10_f1_p8_acceptance_pressure_gate_v0"
            and pressure_summary.get("pressure_packet_hash") == EXPECTED_PRESSURE_PACKET_HASH
            and "P8-C" in pressure_summary.get("ready_pressure_packet_ids", [])
            and pressure_summary.get("validation_error_count") == 0,
            {
                "method": p8_pressure.get("method"),
                "pressure_packet_hash": pressure_summary.get("pressure_packet_hash"),
                "ready_pressure_packet_ids": pressure_summary.get("ready_pressure_packet_ids"),
                "validation_error_count": pressure_summary.get("validation_error_count"),
            },
        ),
        requirement(
            "C2",
            "P8-A intake artifact is current",
            p8a.get("method") == "b3_b10_p8a_accepted_row_replay_intake_template_gate_v0"
            and p8a_summary.get("template_table_hash") == EXPECTED_P8A_TEMPLATE_TABLE_HASH
            and p8a_summary.get("validation_error_count") == 0,
            {
                "method": p8a.get("method"),
                "template_table_hash": p8a_summary.get("template_table_hash"),
                "validation_error_count": p8a_summary.get("validation_error_count"),
            },
        ),
        requirement(
            "C3",
            "P8-B intake artifact is current",
            p8b.get("method") == "b3_b10_p8b_same_access_denominator_replay_intake_template_gate_v0"
            and p8b_summary.get("template_table_hash") == EXPECTED_P8B_TEMPLATE_TABLE_HASH
            and p8b_summary.get("validation_error_count") == 0,
            {
                "method": p8b.get("method"),
                "template_table_hash": p8b_summary.get("template_table_hash"),
                "validation_error_count": p8b_summary.get("validation_error_count"),
            },
        ),
        requirement(
            "C4",
            "P8-A and P8-B cover the same four F1 candidate rows",
            p8a_summary.get("row_template_count") == 4
            and p8b_summary.get("row_template_count") == 4
            and p8a_summary.get("row_bundle_hash") == p8b_summary.get("row_bundle_hash"),
            {
                "p8a_row_template_count": p8a_summary.get("row_template_count"),
                "p8b_row_template_count": p8b_summary.get("row_template_count"),
                "p8a_row_bundle_hash": p8a_summary.get("row_bundle_hash"),
                "p8b_row_bundle_hash": p8b_summary.get("row_bundle_hash"),
            },
        ),
        requirement(
            "C5",
            "Both prerequisite intake gates preserve zero-credit claim boundaries",
            p8a_summary.get("b3_reopen_ready") is False
            and p8a_summary.get("b10_t1_credit_allowed") is False
            and p8b_summary.get("b3_reopen_ready") is False
            and p8b_summary.get("b10_t1_credit_allowed") is False
            and p8b_summary.get("quantum_advantage_claimed") is False
            and p8b_summary.get("bqp_separation_claimed") is False,
            {
                "p8a_b3_reopen_ready": p8a_summary.get("b3_reopen_ready"),
                "p8a_b10_t1_credit_allowed": p8a_summary.get("b10_t1_credit_allowed"),
                "p8b_b3_reopen_ready": p8b_summary.get("b3_reopen_ready"),
                "p8b_b10_t1_credit_allowed": p8b_summary.get("b10_t1_credit_allowed"),
                "p8b_quantum_advantage_claimed": p8b_summary.get("quantum_advantage_claimed"),
                "p8b_bqp_separation_claimed": p8b_summary.get("bqp_separation_claimed"),
            },
        ),
        requirement(
            "C6",
            "At least one P8-A row replay artifact is accepted before P8-C promotion",
            accepted_row_count > 0,
            {"accepted_full_covariance_row_count": accepted_row_count},
        ),
        requirement(
            "C7",
            "At least one P8-B same-access denominator replay artifact is accepted before P8-C promotion",
            accepted_denominator_win_count > 0,
            {"accepted_denominator_win_row_count": accepted_denominator_win_count},
        ),
        requirement(
            "C8",
            "P8-C derivative/optimizer replay is allowed only after P8-A and P8-B positivity",
            p8c_ready,
            {
                "accepted_full_covariance_row_count": accepted_row_count,
                "accepted_denominator_win_row_count": accepted_denominator_win_count,
                "p8c_ready": p8c_ready,
            },
        ),
        requirement(
            "C9",
            "P8-C gate does not fabricate B3 reopen, B10-T1 credit, quantum advantage, or BQP separation",
            not p8c_ready
            and pressure_summary.get("b3_reopen_ready") is False
            and pressure_summary.get("b10_t1_credit_allowed") is False
            and pressure_summary.get("quantum_advantage_claimed") is False
            and pressure_summary.get("bqp_separation_claimed") is False,
            {
                "p8c_ready": p8c_ready,
                "b3_reopen_ready": pressure_summary.get("b3_reopen_ready"),
                "b10_t1_credit_allowed": pressure_summary.get("b10_t1_credit_allowed"),
                "quantum_advantage_claimed": pressure_summary.get("quantum_advantage_claimed"),
                "bqp_separation_claimed": pressure_summary.get("bqp_separation_claimed"),
            },
        ),
        requirement(
            "C10",
            "P8-C dependency table is deterministic and source-bound",
            dependency_table_hash == stable_hash(p8c_dependencies)
            and len(p8c_dependencies) == 3,
            {
                "dependency_table_hash": dependency_table_hash,
                "dependency_count": len(p8c_dependencies),
            },
        ),
    ]
    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected P8-C readiness failures: {failed_ids}")
    if p8c_ready:
        validation_errors.append("P8-C readiness gate must not become ready without external replay artifacts")
    if denominator_win_count != 0:
        validation_errors.append("P8-C readiness gate must not fabricate denominator wins")

    blocker_table = [
        {
            "blocker_id": "P8C-BLOCKER-ROW-REPLAY",
            "source_requirement_id": "C6",
            "required_artifact": "results/B3_B10_P8A_accepted_row_replay_submissions/<row_id>.json",
            "required_positive_condition": "accepted_full_covariance_row_count > 0",
            "current_value": accepted_row_count,
        },
        {
            "blocker_id": "P8C-BLOCKER-DENOMINATOR-REPLAY",
            "source_requirement_id": "C7",
            "required_artifact": (
                "results/B3_B10_P8B_same_access_denominator_replay_submissions/<row_id>.json"
            ),
            "required_positive_condition": "accepted_denominator_win_row_count > 0",
            "current_value": accepted_denominator_win_count,
        },
        {
            "blocker_id": "P8C-BLOCKER-PROMOTION",
            "source_requirement_id": "C8",
            "required_artifact": "paired P8-A accepted row and P8-B same-access denominator win",
            "required_positive_condition": "ready_for_derivative_optimizer_promotion is true",
            "current_value": p8c_ready,
        },
    ]
    blocker_table_hash = stable_hash(blocker_table)

    summary = {
        "readiness_gate_id": "B3B10-P8C-derivative-optimizer-promotion-readiness",
        "source_pressure_packet_hash": pressure_summary.get("pressure_packet_hash"),
        "source_p8a_template_table_hash": p8a_summary.get("template_table_hash"),
        "source_p8b_template_table_hash": p8b_summary.get("template_table_hash"),
        "acceptance_submission_hash": p8a_summary.get("acceptance_submission_hash"),
        "row_bundle_hash": p8a_summary.get("row_bundle_hash"),
        "dependency_table_hash": dependency_table_hash,
        "blocker_table_hash": blocker_table_hash,
        "dependency_count": len(p8c_dependencies),
        "blocker_count": len(blocker_table),
        "accepted_full_covariance_row_count": accepted_row_count,
        "accepted_denominator_win_row_count": accepted_denominator_win_count,
        "denominator_win_count": denominator_win_count,
        "ready_for_derivative_optimizer_promotion": p8c_ready,
        "ready_for_p8c_derivative_optimizer_replay": p8c_ready,
        "requirements_passed": passed,
        "requirements_failed": len(requirements) - passed,
        "failed_requirement_ids": failed_ids,
        "b3_reopen_ready": False,
        "b10_t1_credit_allowed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "validation_error_count": len(validation_errors),
    }
    return {
        "benchmark_id": "B3_B10",
        "problem_ids": [49, 11],
        "title": "B3/B10 P8-C Derivative Optimizer Promotion Readiness Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_p8_pressure_gate": str(args.p8_pressure_gate),
        "source_p8a_intake_gate": str(args.p8a_intake_gate),
        "source_p8b_intake_gate": str(args.p8b_intake_gate),
        "source_target_id": "B10-T1",
        "dependency_benchmarks": ["B3", "B10"],
        "summary": summary,
        "p8c_dependencies": p8c_dependencies,
        "p8c_blockers": blocker_table,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "P8-C derivative/optimizer promotion now has a source-bound readiness gate "
                "that consumes P8 pressure, P8-A row replay intake, and P8-B same-access "
                "denominator replay intake artifacts."
            ),
            "what_is_not_supported": (
                "P8-C is not ready. No accepted P8-A row, no accepted P8-B denominator win, "
                "no B3 reopen, no B10-T1 credit, no quantum advantage, and no BQP separation "
                "are supported."
            ),
            "next_gate": (
                "Submit at least one accepted P8-A row replay artifact and one linked P8-B "
                "same-access denominator-win artifact, then rerun this P8-C readiness gate."
            ),
            "accepted_full_covariance_row_count": accepted_row_count,
            "accepted_denominator_win_row_count": accepted_denominator_win_count,
            "denominator_win_count": denominator_win_count,
            "b3_reopen_ready": False,
            "b10_t1_credit_allowed": False,
            "quantum_advantage_claimed": False,
            "bqp_separation_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    s = payload["summary"]
    lines = [
        "# B3/B10 P8-C Derivative Optimizer Promotion Readiness Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Readiness gate: `{s['readiness_gate_id']}`",
        f"- Source pressure packet hash: `{s['source_pressure_packet_hash']}`",
        f"- Source P8-A template table hash: `{s['source_p8a_template_table_hash']}`",
        f"- Source P8-B template table hash: `{s['source_p8b_template_table_hash']}`",
        f"- Acceptance submission hash: `{s['acceptance_submission_hash']}`",
        f"- Row bundle hash: `{s['row_bundle_hash']}`",
        f"- Dependency table hash: `{s['dependency_table_hash']}`",
        f"- Blocker table hash: `{s['blocker_table_hash']}`",
        f"- Accepted rows / denominator wins: `{s['accepted_full_covariance_row_count']}` / `{s['denominator_win_count']}`",
        f"- Ready for derivative/optimizer promotion: `{s['ready_for_derivative_optimizer_promotion']}`",
        f"- Requirements passed/failed: `{s['requirements_passed']}` / `{s['requirements_failed']}`",
        f"- Failed requirement IDs: `{s['failed_requirement_ids']}`",
        f"- validation_error_count: `{s['validation_error_count']}`",
        "",
        "## Dependencies",
        "",
    ]
    for row in payload["p8c_dependencies"]:
        lines.extend(
            [
                f"### {row['dependency_id']}",
                "",
                f"- Artifact: `{row['artifact']}`",
                f"- Hash: `{row['hash']}`",
                f"- Required state: {row['required_state']}",
                f"- Current state: {row['current_state']}",
                f"- Satisfied: `{row['satisfied']}`",
                "",
            ]
        )
    lines.extend(["## Blockers", ""])
    for row in payload["p8c_blockers"]:
        lines.append(
            f"- {row['blocker_id']} ({row['source_requirement_id']}): "
            f"{row['required_positive_condition']} currently `{row['current_value']}`; "
            f"required artifact `{row['required_artifact']}`."
        )
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
            f"- accepted_full_covariance_row_count: {payload['claim_boundary']['accepted_full_covariance_row_count']}",
            f"- accepted_denominator_win_row_count: {payload['claim_boundary']['accepted_denominator_win_row_count']}",
            f"- denominator_win_count: {payload['claim_boundary']['denominator_win_count']}",
            f"- b3_reopen_ready: {payload['claim_boundary']['b3_reopen_ready']}",
            f"- b10_t1_credit_allowed: {payload['claim_boundary']['b10_t1_credit_allowed']}",
            f"- quantum_advantage_claimed: {payload['claim_boundary']['quantum_advantage_claimed']}",
            f"- bqp_separation_claimed: {payload['claim_boundary']['bqp_separation_claimed']}",
            "",
            "## Validation",
            "",
            f"- validation_error_count: {s['validation_error_count']}",
        ]
    )
    if payload["validation_errors"]:
        lines.extend(f"- {error}" for error in payload["validation_errors"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--p8-pressure-gate",
        type=Path,
        default=Path("results/B3_B10_F1_P8_acceptance_pressure_gate_v0.json"),
    )
    parser.add_argument(
        "--p8a-intake-gate",
        type=Path,
        default=Path("results/B3_B10_P8A_accepted_row_replay_intake_template_gate_v0.json"),
    )
    parser.add_argument(
        "--p8b-intake-gate",
        type=Path,
        default=Path("results/B3_B10_P8B_same_access_denominator_replay_intake_template_gate_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B3_B10_P8C_derivative_optimizer_promotion_readiness_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B3_B10_P8C_derivative_optimizer_promotion_readiness_gate.md"),
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
