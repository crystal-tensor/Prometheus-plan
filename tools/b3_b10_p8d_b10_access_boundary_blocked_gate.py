#!/usr/bin/env python3
"""T-B3-046/T-B10-015ag: P8-D B10 access-boundary blocked gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b3_b10_p8d_b10_access_boundary_blocked_gate_v0"
STATUS = "b3_b10_p8d_b10_access_boundary_blocked_until_p8abc_positive"
MODEL_STATUS = "p8d_b10_t1_access_boundary_correctly_blocked_zero_credit"
VERSION = "0.1"
EXPECTED_PRESSURE_PACKET_HASH = "55384c1a143b50d9b334193c3e55151f33bc9511b90dd19a21f22198bf9fe0b0"
EXPECTED_P8A_TEMPLATE_TABLE_HASH = "a82007811e0448e2436857aaf22ca5fcf30060a1d032370f8f8e8252848584a2"
EXPECTED_P8B_TEMPLATE_TABLE_HASH = "95ea8fecbfb592aae2491ec95d4dc6b19d0b12e98b4dfdbee0087499cfe523ba"
EXPECTED_P8C_BLOCKER_TABLE_HASH = "290440c963db1924d8fefefaa3435e95830e171e4cd2ca29962a60f2992cb009"
EXPECTED_P8E_BOUNDARY_TABLE_HASH = "5cb6bb002a4f67e28f28dcd943ff40dbe682a166bba7c7fa14c70a28c408e769"


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


def p8d_packet(pressure: dict[str, Any]) -> dict[str, Any]:
    for packet in pressure.get("pressure_packets", []):
        if packet.get("packet_id") == "P8-D":
            return packet
    return {}


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    pressure = load_json(args.p8_pressure_gate)
    p8a = load_json(args.p8a_intake_gate)
    p8b = load_json(args.p8b_intake_gate)
    p8c = load_json(args.p8c_readiness_gate)
    p8e = load_json(args.p8e_claim_audit_gate)
    pressure_summary = pressure["summary"]
    p8a_summary = p8a["summary"]
    p8b_summary = p8b["summary"]
    p8c_summary = p8c["summary"]
    p8e_summary = p8e["summary"]
    packet = p8d_packet(pressure)

    access_dependencies = [
        {
            "dependency_id": "P8-A-accepted-row",
            "artifact": str(args.p8a_intake_gate),
            "hash": p8a_summary.get("template_table_hash"),
            "required_positive_condition": "accepted_full_covariance_row_count > 0",
            "current_value": p8a_summary.get("accepted_full_covariance_row_count"),
            "satisfied": p8a_summary.get("accepted_full_covariance_row_count", 0) > 0,
        },
        {
            "dependency_id": "P8-B-same-access-denominator-win",
            "artifact": str(args.p8b_intake_gate),
            "hash": p8b_summary.get("template_table_hash"),
            "required_positive_condition": "accepted_denominator_win_row_count > 0",
            "current_value": p8b_summary.get("accepted_denominator_win_row_count"),
            "satisfied": p8b_summary.get("accepted_denominator_win_row_count", 0) > 0,
        },
        {
            "dependency_id": "P8-C-derivative-optimizer-readiness",
            "artifact": str(args.p8c_readiness_gate),
            "hash": p8c_summary.get("blocker_table_hash"),
            "required_positive_condition": "ready_for_derivative_optimizer_promotion is true",
            "current_value": p8c_summary.get("ready_for_derivative_optimizer_promotion"),
            "satisfied": p8c_summary.get("ready_for_derivative_optimizer_promotion") is True,
        },
        {
            "dependency_id": "P8-E-claim-boundary-audit",
            "artifact": str(args.p8e_claim_audit_gate),
            "hash": p8e_summary.get("boundary_table_hash"),
            "required_positive_condition": "claim-boundary audit passes with no forbidden hits",
            "current_value": {
                "requirements_failed": p8e_summary.get("requirements_failed"),
                "forbidden_result_hit_count": p8e_summary.get("forbidden_result_hit_count"),
                "forbidden_landing_hit_count": p8e_summary.get("forbidden_landing_hit_count"),
            },
            "satisfied": (
                p8e_summary.get("requirements_failed") == 0
                and p8e_summary.get("forbidden_result_hit_count") == 0
                and p8e_summary.get("forbidden_landing_hit_count") == 0
            ),
        },
    ]
    unsatisfied_dependencies = [
        row["dependency_id"] for row in access_dependencies if row["satisfied"] is False
    ]
    access_boundary_table_hash = stable_hash(access_dependencies)
    p8abc_positive = (
        p8a_summary.get("accepted_full_covariance_row_count", 0) > 0
        and p8b_summary.get("accepted_denominator_win_row_count", 0) > 0
        and p8c_summary.get("ready_for_derivative_optimizer_promotion") is True
    )
    b10_access_boundary_blocked = not p8abc_positive

    requirements = [
        requirement(
            "D1",
            "P8 pressure gate exposes P8-D as the B10 access-boundary replay packet",
            pressure.get("method") == "b3_b10_f1_p8_acceptance_pressure_gate_v0"
            and pressure_summary.get("pressure_packet_hash") == EXPECTED_PRESSURE_PACKET_HASH
            and pressure_summary.get("blocked_pressure_packet_ids") == ["P8-D"]
            and packet.get("status") == "blocked_until_P8_A_B_C_pass",
            {
                "method": pressure.get("method"),
                "pressure_packet_hash": pressure_summary.get("pressure_packet_hash"),
                "blocked_pressure_packet_ids": pressure_summary.get("blocked_pressure_packet_ids"),
                "p8d_packet": packet,
            },
        ),
        requirement(
            "D2",
            "P8-A accepted-row prerequisite is still absent",
            p8a.get("method") == "b3_b10_p8a_accepted_row_replay_intake_template_gate_v0"
            and p8a_summary.get("template_table_hash") == EXPECTED_P8A_TEMPLATE_TABLE_HASH
            and p8a_summary.get("accepted_full_covariance_row_count") == 0,
            {
                "method": p8a.get("method"),
                "template_table_hash": p8a_summary.get("template_table_hash"),
                "accepted_full_covariance_row_count": p8a_summary.get(
                    "accepted_full_covariance_row_count"
                ),
            },
        ),
        requirement(
            "D3",
            "P8-B same-access denominator prerequisite is still absent",
            p8b.get("method") == "b3_b10_p8b_same_access_denominator_replay_intake_template_gate_v0"
            and p8b_summary.get("template_table_hash") == EXPECTED_P8B_TEMPLATE_TABLE_HASH
            and p8b_summary.get("accepted_denominator_win_row_count") == 0
            and p8b_summary.get("denominator_win_count") == 0,
            {
                "method": p8b.get("method"),
                "template_table_hash": p8b_summary.get("template_table_hash"),
                "accepted_denominator_win_row_count": p8b_summary.get(
                    "accepted_denominator_win_row_count"
                ),
                "denominator_win_count": p8b_summary.get("denominator_win_count"),
            },
        ),
        requirement(
            "D4",
            "P8-C derivative/optimizer promotion remains blocked",
            p8c.get("method") == "b3_b10_p8c_derivative_optimizer_promotion_readiness_gate_v0"
            and p8c_summary.get("blocker_table_hash") == EXPECTED_P8C_BLOCKER_TABLE_HASH
            and p8c_summary.get("ready_for_derivative_optimizer_promotion") is False,
            {
                "method": p8c.get("method"),
                "blocker_table_hash": p8c_summary.get("blocker_table_hash"),
                "ready_for_derivative_optimizer_promotion": p8c_summary.get(
                    "ready_for_derivative_optimizer_promotion"
                ),
            },
        ),
        requirement(
            "D5",
            "P8-E claim-boundary audit has passed with no forbidden positive claims",
            p8e.get("method") == "b3_b10_p8e_claim_boundary_audit_gate_v0"
            and p8e_summary.get("boundary_table_hash") == EXPECTED_P8E_BOUNDARY_TABLE_HASH
            and p8e_summary.get("requirements_failed") == 0
            and p8e_summary.get("forbidden_result_hit_count") == 0
            and p8e_summary.get("forbidden_landing_hit_count") == 0,
            {
                "method": p8e.get("method"),
                "boundary_table_hash": p8e_summary.get("boundary_table_hash"),
                "requirements_failed": p8e_summary.get("requirements_failed"),
                "forbidden_result_hit_count": p8e_summary.get("forbidden_result_hit_count"),
                "forbidden_landing_hit_count": p8e_summary.get("forbidden_landing_hit_count"),
            },
        ),
        requirement(
            "D6",
            "B10-T1 access boundary is correctly blocked until P8-A/P8-B/P8-C are positive",
            b10_access_boundary_blocked
            and unsatisfied_dependencies
            == [
                "P8-A-accepted-row",
                "P8-B-same-access-denominator-win",
                "P8-C-derivative-optimizer-readiness",
            ],
            {
                "b10_access_boundary_blocked": b10_access_boundary_blocked,
                "unsatisfied_dependencies": unsatisfied_dependencies,
            },
        ),
        requirement(
            "D7",
            "No B10, BQP, advantage, or B3 credit is allowed by this gate",
            pressure_summary.get("b10_t1_credit_allowed") is False
            and pressure_summary.get("b3_reopen_ready") is False
            and pressure_summary.get("quantum_advantage_claimed") is False
            and pressure_summary.get("bqp_separation_claimed") is False
            and p8e_summary.get("b10_t1_credit_allowed") is False
            and p8e_summary.get("b3_reopen_ready") is False,
            {
                "pressure_b10_t1_credit_allowed": pressure_summary.get("b10_t1_credit_allowed"),
                "pressure_b3_reopen_ready": pressure_summary.get("b3_reopen_ready"),
                "pressure_quantum_advantage_claimed": pressure_summary.get(
                    "quantum_advantage_claimed"
                ),
                "pressure_bqp_separation_claimed": pressure_summary.get("bqp_separation_claimed"),
                "p8e_b10_t1_credit_allowed": p8e_summary.get("b10_t1_credit_allowed"),
                "p8e_b3_reopen_ready": p8e_summary.get("b3_reopen_ready"),
            },
        ),
        requirement(
            "D8",
            "P8-D dependency table is deterministic and source-bound",
            access_boundary_table_hash == stable_hash(access_dependencies)
            and len(access_dependencies) == 4,
            {
                "access_boundary_table_hash": access_boundary_table_hash,
                "dependency_count": len(access_dependencies),
            },
        ),
    ]
    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids:
        validation_errors.append(f"unexpected P8-D access-boundary failures: {failed_ids}")
    if not b10_access_boundary_blocked:
        validation_errors.append("P8-D gate must remain blocked until P8-A/P8-B/P8-C are positive")

    summary = {
        "access_boundary_gate_id": "B3B10-P8D-b10-access-boundary-blocked",
        "source_pressure_packet_hash": pressure_summary.get("pressure_packet_hash"),
        "source_p8a_template_table_hash": p8a_summary.get("template_table_hash"),
        "source_p8b_template_table_hash": p8b_summary.get("template_table_hash"),
        "source_p8c_blocker_table_hash": p8c_summary.get("blocker_table_hash"),
        "source_p8e_boundary_table_hash": p8e_summary.get("boundary_table_hash"),
        "access_boundary_table_hash": access_boundary_table_hash,
        "dependency_count": len(access_dependencies),
        "unsatisfied_dependency_count": len(unsatisfied_dependencies),
        "unsatisfied_dependency_ids": unsatisfied_dependencies,
        "accepted_full_covariance_row_count": p8a_summary.get("accepted_full_covariance_row_count"),
        "accepted_denominator_win_row_count": p8b_summary.get("accepted_denominator_win_row_count"),
        "denominator_win_count": p8b_summary.get("denominator_win_count"),
        "ready_for_derivative_optimizer_promotion": p8c_summary.get(
            "ready_for_derivative_optimizer_promotion"
        ),
        "b10_access_boundary_blocked": b10_access_boundary_blocked,
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
        "title": "B3/B10 P8-D B10 Access-Boundary Blocked Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_p8_pressure_gate": str(args.p8_pressure_gate),
        "source_p8a_intake_gate": str(args.p8a_intake_gate),
        "source_p8b_intake_gate": str(args.p8b_intake_gate),
        "source_p8c_readiness_gate": str(args.p8c_readiness_gate),
        "source_p8e_claim_audit_gate": str(args.p8e_claim_audit_gate),
        "source_target_id": "B10-T1",
        "dependency_benchmarks": ["B3", "B10"],
        "summary": summary,
        "access_dependencies": access_dependencies,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "P8-D now has a source-bound B10 access-boundary blocked gate proving B10-T1 "
                "must remain zero-credit until P8-A, P8-B, and P8-C become positive."
            ),
            "what_is_not_supported": (
                "This does not accept a B3 row, establish a denominator win, allow P8-C "
                "promotion, grant B10-T1 credit, claim quantum advantage, or claim BQP separation."
            ),
            "next_gate": (
                "Submit positive P8-A/P8-B artifacts, rerun P8-C, rerun P8-E, then rerun P8-D "
                "before any B10-T1 access-boundary credit is considered."
            ),
            "accepted_full_covariance_row_count": summary["accepted_full_covariance_row_count"],
            "accepted_denominator_win_row_count": summary["accepted_denominator_win_row_count"],
            "denominator_win_count": summary["denominator_win_count"],
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
        "# B3/B10 P8-D B10 Access-Boundary Blocked Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Access-boundary gate: `{s['access_boundary_gate_id']}`",
        f"- Access-boundary table hash: `{s['access_boundary_table_hash']}`",
        f"- Source P8-E boundary table hash: `{s['source_p8e_boundary_table_hash']}`",
        f"- Unsatisfied dependencies: `{s['unsatisfied_dependency_ids']}`",
        f"- Accepted rows / denominator wins: `{s['accepted_full_covariance_row_count']}` / `{s['denominator_win_count']}`",
        f"- Ready for derivative/optimizer promotion: `{s['ready_for_derivative_optimizer_promotion']}`",
        f"- B10 access boundary blocked: `{s['b10_access_boundary_blocked']}`",
        f"- Requirements passed/failed: `{s['requirements_passed']}` / `{s['requirements_failed']}`",
        f"- Failed requirement IDs: `{s['failed_requirement_ids']}`",
        f"- validation_error_count: `{s['validation_error_count']}`",
        "",
        "## Access Dependencies",
        "",
    ]
    for row in payload["access_dependencies"]:
        lines.extend(
            [
                f"### {row['dependency_id']}",
                "",
                f"- Artifact: `{row['artifact']}`",
                f"- Hash: `{row['hash']}`",
                f"- Required positive condition: {row['required_positive_condition']}",
                f"- Current value: `{row['current_value']}`",
                f"- Satisfied: `{row['satisfied']}`",
                "",
            ]
        )
    lines.extend(["## Requirement Results", ""])
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
        "--p8c-readiness-gate",
        type=Path,
        default=Path("results/B3_B10_P8C_derivative_optimizer_promotion_readiness_gate_v0.json"),
    )
    parser.add_argument(
        "--p8e-claim-audit-gate",
        type=Path,
        default=Path("results/B3_B10_P8E_claim_boundary_audit_gate_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B3_B10_P8D_b10_access_boundary_blocked_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B3_B10_P8D_b10_access_boundary_blocked_gate.md"),
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
