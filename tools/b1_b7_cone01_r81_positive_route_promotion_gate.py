#!/usr/bin/env python3
"""T-B1-004ge/T-B7-015n: R81 positive-route promotion gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r81_positive_route_promotion_gate_v0"
STATUS = "cone01_r81_positive_route_accepted_b7_retest_still_blocked"
MODEL_STATUS = "positive_occurrence_proxy_t_and_exit_route_pass_b7_credit_still_zero"
VERSION = "0.1"
TARGET_ID = "T-B1-004ge/T-B7-015n"
UPSTREAM_TARGET_ID = "T-B1-004gd/T-B7-015m"
SUBMISSION_DIR = "results/B1_B7_cone01_o3_f4_exit_route_submissions"

R78_CONTRACT = f"{SUBMISSION_DIR}/R78-positive-route-packet.contract.json"
R80_PACKET = f"{SUBMISSION_DIR}/R80-acceptance-ledger-bound-zero.packet.json"
R80_PREFLIGHT = f"{SUBMISSION_DIR}/R80-acceptance-ledger-bound-zero.verdict.json"
R74_ARTIFACT = f"{SUBMISSION_DIR}/R74-r1-line1381-occurrence-replay-artifact.json"
R74_VERDICT = f"{SUBMISSION_DIR}/R74-r1-line1381-occurrence-replay.verdict.json"
R75_DERIVATION = f"{SUBMISSION_DIR}/R75-proxy-t-pricing-derivation-artifact.json"
R75_VERDICT = f"{SUBMISSION_DIR}/R75-proxy-t-pricing-replay.verdict.json"
R76_LEDGER = f"{SUBMISSION_DIR}/R76-line1378-no-double-counting-ledger.json"
R76_INTAKE_VERDICT = f"{SUBMISSION_DIR}/R76-r1-d1-d2-d3-source-closure-intake.verdict.json"
R81_OCCURRENCE_LEDGER = f"{SUBMISSION_DIR}/R81-occurrence-acceptance-positive-ledger.json"
R81_PROXY_T_LEDGER = f"{SUBMISSION_DIR}/R81-proxy-t-acceptance-positive-ledger.json"
R81_PACKET = f"{SUBMISSION_DIR}/R81-positive-route-accepted.packet.json"
R81_PREFLIGHT = f"{SUBMISSION_DIR}/R81-positive-route-accepted.verdict.json"
R81_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R81-b7-retest-blocker-queue.json"
R81_STDOUT = f"{SUBMISSION_DIR}/R81-positive-route-promotion.stdout.txt"


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def stable_self_hash(payload: dict[str, Any], hash_key: str) -> str:
    copy = dict(payload)
    copy.pop(hash_key, None)
    return stable_hash(copy)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def req(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def path_hash_matches(root: Path, path_value: Any, hash_value: Any) -> bool:
    if not isinstance(path_value, str) or not isinstance(hash_value, str):
        return False
    path = root / path_value
    return path.exists() and file_hash(path) == hash_value


def preflight_packet(root: Path, contract: dict[str, Any], packet: dict[str, Any]) -> dict[str, Any]:
    missing = [
        field for field in contract["production_required_fields"] if packet.get(field) in (None, "")
    ]
    hash_failures = []
    hash_fields_seen = 0
    for field in contract["production_required_fields"]:
        if not field.endswith("_sha256"):
            continue
        path_field = field[: -len("_sha256")] + "_path"
        value = packet.get(field)
        path_value = packet.get(path_field)
        if value in (None, "") or path_value in (None, ""):
            continue
        hash_fields_seen += 1
        if not path_hash_matches(root, path_value, value):
            hash_failures.append(field)

    gates = {
        "all_required_fields_complete": missing == [],
        "all_hash_bound_artifacts_match": missing == [] and hash_failures == [],
        "source_r77_payload_hash_matches": packet.get("source_r77_payload_hash")
        == contract["source_r77_payload_hash"],
        "r76_no_double_counting_preserved": packet.get(
            "source_r76_no_double_counting_ledger_sha256"
        )
        == contract["r76_no_double_counting_ledger_sha256"],
        "accepted_exit_route_positive": packet.get("accepted_exit_route_count", 0) >= 1,
        "accepted_occurrence_positive": packet.get("accepted_occurrence_removal", 0) >= 1,
        "accepted_proxy_t_positive": packet.get("accepted_proxy_t_reduction", 0) >= 1,
        "b7_not_requested_inside_packet": packet.get("b7_nonzero_retest_requested") is False,
        "claim_boundary_blocks_b7": "b7 credit" in str(packet.get("claim_boundary", "")).lower()
        and "cannot" in str(packet.get("claim_boundary", "")).lower(),
    }
    failed = [gate for gate, passed in gates.items() if not passed]
    verdict = {
        "artifact": "R81 positive-route packet preflight verdict",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_id": contract["contract_id"],
        "contract_hash": contract["contract_hash"],
        "packet_id": packet["packet_id"],
        "packet_hash": packet["packet_hash"],
        "gates": gates,
        "passed_gate_count": sum(1 for passed in gates.values() if passed),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "missing_required_fields": missing,
        "missing_required_field_count": len(missing),
        "hash_fields_seen": hash_fields_seen,
        "hash_failures": hash_failures,
        "accepted": failed == [],
        "accepted_exit_route_count": packet.get("accepted_exit_route_count", 0),
        "accepted_occurrence_removal": packet.get("accepted_occurrence_removal", 0),
        "accepted_proxy_t_reduction": packet.get("accepted_proxy_t_reduction", 0),
        "b7_credit_delta": 0,
        "b7_nonzero_retest_allowed": False,
        "claim_boundary": "R81 accepts the B1 exit-route packet only; B7 credit requires a separate downstream retest.",
    }
    verdict["verdict_hash"] = stable_self_hash(verdict, "verdict_hash")
    return verdict


def build_occurrence_ledger(
    root: Path,
    r74_artifact: dict[str, Any],
    r74_verdict: dict[str, Any],
    r76_ledger: dict[str, Any],
    r76_intake: dict[str, Any],
) -> dict[str, Any]:
    ledger = {
        "artifact": "R81 occurrence acceptance positive ledger",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "ledger_id": "B1-B7-cone01-R81-occurrence-acceptance-positive-ledger",
        "route_id": "R1-line1381-resolution",
        "source_r74_artifact_path": R74_ARTIFACT,
        "source_r74_artifact_sha256": file_hash(root / R74_ARTIFACT),
        "source_r74_artifact_hash": r74_artifact["artifact_hash"],
        "source_r74_verdict_path": R74_VERDICT,
        "source_r74_verdict_sha256": file_hash(root / R74_VERDICT),
        "source_r74_verdict_hash": r74_verdict["verdict_hash"],
        "source_r76_no_double_counting_ledger_path": R76_LEDGER,
        "source_r76_no_double_counting_ledger_sha256": file_hash(root / R76_LEDGER),
        "source_r76_no_double_counting_ledger_hash": r76_ledger["ledger_hash"],
        "source_r76_intake_verdict_path": R76_INTAKE_VERDICT,
        "source_r76_intake_verdict_sha256": file_hash(root / R76_INTAKE_VERDICT),
        "source_r76_intake_verdict_hash": r76_intake["verdict_hash"],
        "source_line1381": r74_artifact["line1381_source_instruction"],
        "candidate_line1381": r74_artifact["line1381_candidate_instruction_at_same_line"],
        "occurrence_removed_lines": r74_artifact["occurrence_removed_lines"],
        "accepted_occurrence_removal": 1,
        "acceptance_checks": {
            "r74_prefill_verdict_passed": r74_verdict["accepted_for_r73_d1_prefill"] is True
            and r74_verdict["failed_checks"] == [],
            "source_line1381_is_cx": r74_artifact["line1381_source_is_cx"] is True,
            "candidate_same_line_not_cx": r74_artifact[
                "line1381_candidate_same_line_is_not_cx"
            ]
            is True,
            "r76_intake_accepted": r76_intake["accepted"] is True,
            "line1378_not_double_counted": r76_ledger["double_counting_prevented"] is True
            and r76_ledger["counted_positive_line_windows"] == [1381],
        },
        "claim_boundary": (
            "This ledger accepts exactly one occurrence removal for the B1 R78 "
            "packet. It cannot close O3, permit reroute, claim B7 credit, or count "
            "line1378 as a second positive occurrence."
        ),
    }
    ledger["accepted"] = all(ledger["acceptance_checks"].values())
    ledger["ledger_hash"] = stable_self_hash(ledger, "ledger_hash")
    return ledger


def build_proxy_t_ledger(
    root: Path,
    r75_derivation: dict[str, Any],
    r75_verdict: dict[str, Any],
    r76_ledger: dict[str, Any],
    r76_intake: dict[str, Any],
) -> dict[str, Any]:
    ledger = {
        "artifact": "R81 proxy-T acceptance positive ledger",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "ledger_id": "B1-B7-cone01-R81-proxy-t-acceptance-positive-ledger",
        "route_id": "R1-line1381-resolution",
        "source_r75_derivation_path": R75_DERIVATION,
        "source_r75_derivation_sha256": file_hash(root / R75_DERIVATION),
        "source_r75_derivation_hash": r75_derivation["derivation_hash"],
        "source_r75_verdict_path": R75_VERDICT,
        "source_r75_verdict_sha256": file_hash(root / R75_VERDICT),
        "source_r75_verdict_hash": r75_verdict["verdict_hash"],
        "source_r76_no_double_counting_ledger_path": R76_LEDGER,
        "source_r76_no_double_counting_ledger_sha256": file_hash(root / R76_LEDGER),
        "source_r76_no_double_counting_ledger_hash": r76_ledger["ledger_hash"],
        "source_r76_intake_verdict_path": R76_INTAKE_VERDICT,
        "source_r76_intake_verdict_sha256": file_hash(root / R76_INTAKE_VERDICT),
        "source_r76_intake_verdict_hash": r76_intake["verdict_hash"],
        "proxy_t_before": r75_derivation["proxy_t_before"],
        "proxy_t_after": r75_derivation["proxy_t_after"],
        "accepted_proxy_t_reduction": r75_derivation["proxy_t_delta"],
        "acceptance_checks": {
            "r75_prefill_verdict_passed": r75_verdict["accepted_for_r73_d2_prefill"] is True
            and r75_verdict["failed_checks"] == [],
            "proxy_t_arithmetic_positive": r75_derivation["proxy_t_before"]
            - r75_derivation["proxy_t_after"]
            == r75_derivation["proxy_t_delta"]
            and r75_derivation["proxy_t_delta"] >= 1,
            "r76_intake_accepted": r76_intake["accepted"] is True,
            "line1378_not_double_counted": r76_ledger["double_counting_prevented"] is True
            and r76_ledger["counted_positive_line_windows"] == [1381],
        },
        "claim_boundary": (
            "This ledger accepts the R75 one-unit proxy-T reduction for the B1 R78 "
            "packet after R76 source closure. It cannot close O3, permit reroute, "
            "claim resource saving at the B7 ledger, or grant B7 credit."
        ),
    }
    ledger["accepted"] = all(ledger["acceptance_checks"].values())
    ledger["ledger_hash"] = stable_self_hash(ledger, "ledger_hash")
    return ledger


def build_packet(
    root: Path,
    r80_packet: dict[str, Any],
    occurrence_ledger: dict[str, Any],
    proxy_t_ledger: dict[str, Any],
) -> dict[str, Any]:
    packet = dict(r80_packet)
    packet.update(
        {
            "packet_id": "B1-B7-cone01-R81-positive-route-accepted-packet",
            "route_class": "positive_route_accepted_b1_only_b7_retest_required",
            "source_r80_packet_path": R80_PACKET,
            "source_r80_packet_sha256": file_hash(root / R80_PACKET),
            "source_r80_packet_hash": r80_packet["packet_hash"],
            "occurrence_acceptance_ledger_path": R81_OCCURRENCE_LEDGER,
            "occurrence_acceptance_ledger_sha256": file_hash(root / R81_OCCURRENCE_LEDGER),
            "proxy_t_acceptance_ledger_path": R81_PROXY_T_LEDGER,
            "proxy_t_acceptance_ledger_sha256": file_hash(root / R81_PROXY_T_LEDGER),
            "accepted_exit_route_count": 1,
            "accepted_occurrence_removal": occurrence_ledger["accepted_occurrence_removal"],
            "accepted_proxy_t_reduction": proxy_t_ledger["accepted_proxy_t_reduction"],
            "b7_nonzero_retest_requested": False,
            "claim_boundary": (
                "R81 accepts exactly one B1 positive-route packet after R74 "
                "occurrence evidence, R75 proxy-T evidence, and R76 no-double-counting "
                "all pass. It cannot close O3, permit reroute, claim resource saving, "
                "or grant B7 credit; downstream B7 retest remains required."
            ),
        }
    )
    packet["packet_hash"] = stable_self_hash(packet, "packet_hash")
    return packet


def build_blocker_queue(preflight: dict[str, Any]) -> dict[str, Any]:
    queue = {
        "artifact": "R81 downstream B7 retest blocker queue",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "positive_route_preflight_accepted": preflight["accepted"],
        "accepted_exit_route_count": preflight["accepted_exit_route_count"],
        "accepted_occurrence_removal": preflight["accepted_occurrence_removal"],
        "accepted_proxy_t_reduction": preflight["accepted_proxy_t_reduction"],
        "b7_credit_delta": 0,
        "queue": [
            {
                "blocker_id": "R81-B7-1",
                "priority": 1,
                "target_gate": "downstream_b7_nonzero_retest",
                "needed_artifact": "rerun B7 resource/FT ledger using the R81 accepted B1 route packet",
            },
            {
                "blocker_id": "R81-B7-2",
                "priority": 2,
                "target_gate": "claim_boundary_audit",
                "needed_artifact": "prove any B7/STV credit is derived only from the downstream retest, not from R81 packet acceptance alone",
            },
        ],
    }
    queue["blocker_queue_hash"] = stable_self_hash(queue, "blocker_queue_hash")
    return queue


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    contract = load_json(root / R78_CONTRACT)
    r80_packet = load_json(root / R80_PACKET)
    r80_preflight = load_json(root / R80_PREFLIGHT)
    r74_artifact = load_json(root / R74_ARTIFACT)
    r74_verdict = load_json(root / R74_VERDICT)
    r75_derivation = load_json(root / R75_DERIVATION)
    r75_verdict = load_json(root / R75_VERDICT)
    r76_ledger = load_json(root / R76_LEDGER)
    r76_intake = load_json(root / R76_INTAKE_VERDICT)

    occurrence_ledger = build_occurrence_ledger(
        root, r74_artifact, r74_verdict, r76_ledger, r76_intake
    )
    write_json(root / R81_OCCURRENCE_LEDGER, occurrence_ledger)
    proxy_t_ledger = build_proxy_t_ledger(
        root, r75_derivation, r75_verdict, r76_ledger, r76_intake
    )
    write_json(root / R81_PROXY_T_LEDGER, proxy_t_ledger)
    packet = build_packet(root, r80_packet, occurrence_ledger, proxy_t_ledger)
    write_json(root / R81_PACKET, packet)
    preflight = preflight_packet(root, contract, packet)
    write_json(root / R81_PREFLIGHT, preflight)
    blocker_queue = build_blocker_queue(preflight)
    write_json(root / R81_BLOCKER_QUEUE, blocker_queue)
    stdout = {
        "artifact": "R81 positive-route promotion stdout",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "packet_hash": packet["packet_hash"],
        "preflight_accepted": preflight["accepted"],
        "r80_failed_gate_count_before": r80_preflight["failed_gate_count"],
        "r81_failed_gate_count_after": preflight["failed_gate_count"],
        "accepted_exit_route_count": preflight["accepted_exit_route_count"],
        "accepted_occurrence_removal": preflight["accepted_occurrence_removal"],
        "accepted_proxy_t_reduction": preflight["accepted_proxy_t_reduction"],
        "b7_credit_delta": 0,
    }
    write_json(root / R81_STDOUT, stdout)

    requirements = [
        req(
            "A1",
            "R80 upstream packet is field-complete but positive-gate blocked",
            r80_preflight["missing_required_field_count"] == 0
            and r80_preflight["failed_gates"]
            == [
                "accepted_exit_route_positive",
                "accepted_occurrence_positive",
                "accepted_proxy_t_positive",
            ],
            {
                "r80_packet_path": R80_PACKET,
                "r80_packet_sha256": file_hash(root / R80_PACKET),
                "r80_failed_gates": r80_preflight["failed_gates"],
            },
        ),
        req(
            "A2",
            "R74 supplies accepted line1381 occurrence evidence",
            occurrence_ledger["accepted"] is True
            and occurrence_ledger["accepted_occurrence_removal"] == 1,
            {
                "occurrence_ledger_path": R81_OCCURRENCE_LEDGER,
                "occurrence_ledger_hash": occurrence_ledger["ledger_hash"],
                "source_line1381": occurrence_ledger["source_line1381"],
                "candidate_line1381": occurrence_ledger["candidate_line1381"],
            },
        ),
        req(
            "A3",
            "R75 supplies accepted proxy-T positive evidence",
            proxy_t_ledger["accepted"] is True
            and proxy_t_ledger["accepted_proxy_t_reduction"] == 1,
            {
                "proxy_t_ledger_path": R81_PROXY_T_LEDGER,
                "proxy_t_ledger_hash": proxy_t_ledger["ledger_hash"],
                "proxy_t_before": proxy_t_ledger["proxy_t_before"],
                "proxy_t_after": proxy_t_ledger["proxy_t_after"],
            },
        ),
        req(
            "A4",
            "R76 no-double-counting closure is preserved",
            r76_intake["accepted"] is True
            and r76_ledger["double_counting_prevented"] is True
            and r76_ledger["counted_positive_line_windows"] == [1381],
            {
                "r76_ledger_path": R76_LEDGER,
                "r76_ledger_hash": r76_ledger["ledger_hash"],
                "r76_intake_verdict_hash": r76_intake["verdict_hash"],
            },
        ),
        req(
            "A5",
            "R81 positive-route packet passes all R78 preflight gates",
            preflight["accepted"] is True
            and preflight["failed_gates"] == []
            and preflight["missing_required_field_count"] == 0
            and preflight["hash_failures"] == [],
            {
                "preflight_path": R81_PREFLIGHT,
                "preflight_hash": preflight["verdict_hash"],
                "passed_gate_count": preflight["passed_gate_count"],
            },
        ),
        req(
            "A6",
            "R81 accepts one B1 route while preserving zero B7 credit",
            preflight["accepted_exit_route_count"] == 1
            and preflight["accepted_occurrence_removal"] == 1
            and preflight["accepted_proxy_t_reduction"] == 1
            and preflight["b7_credit_delta"] == 0
            and preflight["b7_nonzero_retest_allowed"] is False,
            {
                "accepted_exit_route_count": preflight["accepted_exit_route_count"],
                "accepted_occurrence_removal": preflight["accepted_occurrence_removal"],
                "accepted_proxy_t_reduction": preflight["accepted_proxy_t_reduction"],
                "b7_credit_delta": preflight["b7_credit_delta"],
            },
        ),
        req(
            "A7",
            "R81 emits downstream B7 retest blockers",
            len(blocker_queue["queue"]) == 2,
            {
                "blocker_queue_path": R81_BLOCKER_QUEUE,
                "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
            },
        ),
        req(
            "A8",
            "R81 claim boundary blocks O3/reroute/resource/B7 overclaim",
            all(
                token in packet["claim_boundary"].lower()
                for token in ["cannot", "reroute", "resource saving", "b7 credit"]
            ),
            {"claim_boundary": packet["claim_boundary"]},
        ),
    ]
    failed_requirements = [
        requirement["requirement_id"]
        for requirement in requirements
        if not requirement["passed"]
    ]
    validation_errors = []
    if not preflight["accepted"]:
        validation_errors.append("R81 positive-route packet should pass R78 preflight")
    if preflight["b7_credit_delta"] != 0:
        validation_errors.append("R81 must preserve zero B7 credit")
    if preflight["b7_nonzero_retest_allowed"] is not False:
        validation_errors.append("R81 must leave B7 nonzero retest to a downstream gate")

    payload = {
        "artifact": "B1/B7 cone01 R81 positive-route promotion gate",
        "method": METHOD,
        "version": VERSION,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "generated_at_unix": int(time.time()),
        "occurrence_ledger_path": R81_OCCURRENCE_LEDGER,
        "occurrence_ledger_hash": occurrence_ledger["ledger_hash"],
        "proxy_t_ledger_path": R81_PROXY_T_LEDGER,
        "proxy_t_ledger_hash": proxy_t_ledger["ledger_hash"],
        "packet_path": R81_PACKET,
        "packet_hash": packet["packet_hash"],
        "preflight_path": R81_PREFLIGHT,
        "preflight_hash": preflight["verdict_hash"],
        "stdout_path": R81_STDOUT,
        "stdout_sha256": file_hash(root / R81_STDOUT),
        "blocker_queue_path": R81_BLOCKER_QUEUE,
        "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
        "requirement_count": len(requirements),
        "requirements_passed": sum(1 for requirement in requirements if requirement["passed"]),
        "requirements_failed": len(failed_requirements),
        "failed_requirement_ids": failed_requirements,
        "requirements": requirements,
        "validation_error_count": len(validation_errors),
        "validation_errors": validation_errors,
        "summary": {
            "method": METHOD,
            "status": STATUS,
            "model_status": MODEL_STATUS,
            "source_target_id": TARGET_ID,
            "upstream_target_id": UPSTREAM_TARGET_ID,
            "r80_failed_gate_count_before": r80_preflight["failed_gate_count"],
            "r81_failed_gate_count_after": preflight["failed_gate_count"],
            "r81_preflight_accepted": preflight["accepted"],
            "r81_failed_gates": preflight["failed_gates"],
            "accepted_exit_route_count": preflight["accepted_exit_route_count"],
            "accepted_occurrence_removal": preflight["accepted_occurrence_removal"],
            "accepted_proxy_t_reduction": preflight["accepted_proxy_t_reduction"],
            "b7_credit_delta": 0,
            "b7_nonzero_retest_allowed": False,
            "o3_closed": False,
            "reroute_allowed": False,
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "occurrence_ledger_hash": occurrence_ledger["ledger_hash"],
            "proxy_t_ledger_hash": proxy_t_ledger["ledger_hash"],
            "packet_hash": packet["packet_hash"],
            "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
            "payload_hash": None,
            "requirements_passed": sum(
                1 for requirement in requirements if requirement["passed"]
            ),
            "requirements_failed": len(failed_requirements),
            "failed_requirement_ids": failed_requirements,
            "validation_error_count": len(validation_errors),
        },
    }
    payload["payload_hash"] = stable_self_hash(payload, "payload_hash")
    payload["summary"]["payload_hash"] = payload["payload_hash"]
    return payload


def write_report(root: Path, payload: dict[str, Any]) -> None:
    report_path = root / "research/B1_B7_cone01_R81_positive_route_promotion_gate.md"
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone01 R81 Positive-Route Promotion Gate",
        "",
        f"- Target: `{TARGET_ID}`",
        f"- Upstream target: `{UPSTREAM_TARGET_ID}`",
        f"- Method: `{METHOD}`",
        f"- Status: `{STATUS}`",
        f"- Model status: `{MODEL_STATUS}`",
        "",
        "## Result",
        "",
        "R81 replaces the R80 zero ledgers with source-backed positive occurrence",
        "and proxy-T ledgers, then reruns the R78 positive-route packet preflight.",
        "The B1 route packet passes all R78 gates with one accepted exit route, one",
        "accepted occurrence removal, and one accepted proxy-T reduction. B7 credit",
        "remains zero because no downstream B7 retest has been run.",
        "",
        "## Key Counters",
        "",
        f"- R80 failed gates before: `{summary['r80_failed_gate_count_before']}`",
        f"- R81 failed gates after: `{summary['r81_failed_gate_count_after']}`",
        f"- R81 preflight accepted: `{summary['r81_preflight_accepted']}`",
        f"- Accepted exit routes: `{summary['accepted_exit_route_count']}`",
        f"- Accepted occurrence removal: `{summary['accepted_occurrence_removal']}`",
        f"- Accepted proxy-T reduction: `{summary['accepted_proxy_t_reduction']}`",
        f"- B7 credit delta: `{summary['b7_credit_delta']}`",
        "",
        "## Requirements",
        "",
    ]
    for requirement in payload["requirements"]:
        status = "PASS" if requirement["passed"] else "FAIL"
        lines.append(
            f"- `{requirement['requirement_id']}` {status}: {requirement['label']}"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- Result JSON: `results/B1_B7_cone01_R81_positive_route_promotion_gate_v0.json`",
            f"- Occurrence ledger: `{R81_OCCURRENCE_LEDGER}`",
            f"- Proxy-T ledger: `{R81_PROXY_T_LEDGER}`",
            f"- Accepted packet: `{R81_PACKET}`",
            f"- Preflight verdict: `{R81_PREFLIGHT}`",
            f"- Downstream blocker queue: `{R81_BLOCKER_QUEUE}`",
            f"- Stdout: `{R81_STDOUT}`",
            "",
            "## Claim Boundary",
            "",
            "R81 accepts one B1 exit-route packet under the R78 preflight. It is not",
            "O3 closure, not reroute permission, not a B7 resource/FT ledger replay,",
            "and not B7 credit. The next gate is a downstream B7 retest using the R81",
            "accepted packet as input.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--output",
        default="results/B1_B7_cone01_R81_positive_route_promotion_gate_v0.json",
    )
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.repo_root).resolve()
    payload = build_payload(args)
    write_json(root / args.output, payload)
    write_report(root, payload)
    print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
    if payload["validation_error_count"] or payload["requirements_failed"]:
        raise SystemExit("B1/B7 R81 positive-route promotion validation failed")


if __name__ == "__main__":
    main()
