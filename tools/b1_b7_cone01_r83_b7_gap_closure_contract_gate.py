#!/usr/bin/env python3
"""T-B1-004gg/T-B7-015p: R83 B7 591-gap closure contract gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r83_b7_gap_closure_contract_gate_v0"
STATUS = "cone01_r83_b7_gap_closure_contract_ready_no_credit"
MODEL_STATUS = "r82_591_t_ledger_gap_converted_to_fillable_b7_closure_contract"
VERSION = "0.1"
TARGET_ID = "T-B1-004gg/T-B7-015p"
UPSTREAM_TARGET_ID = "T-B1-004gf/T-B7-015o"
SUBMISSION_DIR = "results/B1_B7_cone01_o3_f4_exit_route_submissions"

R82_RESULT = "results/B1_B7_cone01_R82_b7_downstream_retest_gate_v0.json"
R82_LEDGER = f"{SUBMISSION_DIR}/R82-b7-downstream-retest-ledger.json"
R82_VERDICT = f"{SUBMISSION_DIR}/R82-b7-downstream-retest.verdict.json"
R82_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R82-b7-next-blocker-queue.json"
B7_GCM_BOUNDARY = "results/B7_gcm_h6_ft_boundary_v0.json"
B7_FT_LEDGER = "results/B7_ft_synthesis_ledger_v0.json"

R83_CONTRACT = f"{SUBMISSION_DIR}/R83-b7-gap-closure.contract.json"
R83_TEMPLATE = f"{SUBMISSION_DIR}/R83-b7-gap-closure.template.json"
R83_PREFLIGHT = f"{SUBMISSION_DIR}/R83-b7-gap-closure-template.verdict.json"
R83_WORK_PACKETS = f"{SUBMISSION_DIR}/R83-b7-gap-closure-work-packets.json"
R83_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R83-b7-gap-closure-blocker-queue.json"
R83_STDOUT = f"{SUBMISSION_DIR}/R83-b7-gap-closure-contract.stdout.txt"


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


def build_contract(
    root: Path,
    r82_result: dict[str, Any],
    r82_ledger: dict[str, Any],
    r82_verdict: dict[str, Any],
    r82_blocker_queue: dict[str, Any],
    b7_boundary: dict[str, Any],
) -> dict[str, Any]:
    min_gap = int(r82_result["summary"]["min_t_ledger_gap_after_r81"])
    target_120 = next(
        row
        for row in r82_result["summary"]["target_gap_rows"]
        if float(row["target_stv_reduction"]) == 1.2
    )
    target_125 = next(
        row
        for row in r82_result["summary"]["target_gap_rows"]
        if float(row["target_stv_reduction"]) == 1.25
    )
    required_fields = [
        "submission_id",
        "route_id",
        "source_target_id",
        "upstream_target_id",
        "source_r82_result_path",
        "source_r82_result_sha256",
        "source_r82_ledger_path",
        "source_r82_ledger_sha256",
        "source_r82_verdict_path",
        "source_r82_verdict_sha256",
        "source_b7_boundary_path",
        "source_b7_boundary_sha256",
        "claimed_target_stv_reduction",
        "claimed_t_ledger_reduction",
        "candidate_after_t_ledger",
        "evidence_bundle_path",
        "evidence_bundle_sha256",
        "replay_command",
        "replay_stdout_path",
        "replay_stdout_sha256",
        "t_ledger_reduction_rows_path",
        "t_ledger_reduction_rows_sha256",
        "no_double_counting_ledger_path",
        "no_double_counting_ledger_sha256",
        "logical_t_mapping_ledger_path",
        "logical_t_mapping_ledger_sha256",
        "stv_reprice_ledger_path",
        "stv_reprice_ledger_sha256",
        "claim_boundary",
        "o3_closed",
        "reroute_allowed",
        "resource_saving_claimed",
        "b7_credit_requested",
    ]
    contract = {
        "artifact": "R83 B7 gap-closure submission contract",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_id": "B1-B7-cone01-R83-B7-591-gap-closure-contract",
        "source_r82_result_path": R82_RESULT,
        "source_r82_result_sha256": file_hash(root / R82_RESULT),
        "source_r82_payload_hash": r82_result["payload_hash"],
        "source_r82_ledger_path": R82_LEDGER,
        "source_r82_ledger_sha256": file_hash(root / R82_LEDGER),
        "source_r82_ledger_hash": r82_ledger["ledger_hash"],
        "source_r82_verdict_path": R82_VERDICT,
        "source_r82_verdict_sha256": file_hash(root / R82_VERDICT),
        "source_r82_verdict_hash": r82_verdict["verdict_hash"],
        "source_r82_blocker_queue_path": R82_BLOCKER_QUEUE,
        "source_r82_blocker_queue_sha256": file_hash(root / R82_BLOCKER_QUEUE),
        "source_r82_blocker_queue_hash": r82_blocker_queue["blocker_queue_hash"],
        "source_b7_boundary_path": B7_GCM_BOUNDARY,
        "source_b7_boundary_sha256": file_hash(root / B7_GCM_BOUNDARY),
        "source_b7_boundary_status": b7_boundary["status"],
        "target_1_20_t_ledger_gap_after_r81": min_gap,
        "target_1_20_max_after_t_ledger": int(
            b7_boundary["target_requirements_for_current_min"][0]["max_after_t_ledger"]
        ),
        "target_1_25_t_ledger_gap_after_r81": int(
            target_125["additional_t_ledger_to_remove_after_r81"]
        ),
        "current_after_t_ledger": int(b7_boundary["gcm_h6_after_total_t_ledger"]),
        "minimum_accepted_t_ledger_reduction": min_gap,
        "minimum_equivalent_arbitrary_rotation_removal_at_cost_20": int(
            target_120["equivalent_arbitrary_rotations_remaining_at_cost_20"]
        ),
        "required_submission_fields": required_fields,
        "production_required_fields": required_fields,
        "acceptance_gates": [
            "all_required_fields_complete",
            "all_hash_bound_artifacts_match",
            "source_r82_boundary_hashes_match",
            "claimed_t_ledger_reduction_at_least_591",
            "candidate_after_t_ledger_at_or_below_5632",
            "stv_reprice_ledger_present",
            "logical_t_mapping_ledger_present",
            "no_double_counting_ledger_present",
            "replay_stdout_hash_matches",
            "claim_boundary_blocks_o3_reroute_until_audit",
        ],
        "forbidden_shortcuts": [
            "metadata_only_t_ledger_reduction",
            "counting_R81_one_unit_delta_as_B7_credit",
            "claiming_resource_saving_without_full_B7_reprice",
            "claiming_O3_closure_or_reroute_permission_inside_this_contract",
        ],
        "claim_boundary": (
            "R83 is a fillable contract for closing the R82 591 T-ledger gap. "
            "It grants no B7 credit until a future submission supplies hash-bound "
            "replay, logical-T mapping, STV reprice, and no-double-counting evidence."
        ),
    }
    contract["contract_hash"] = stable_self_hash(contract, "contract_hash")
    return contract


def build_template(contract: dict[str, Any]) -> dict[str, Any]:
    template = {
        field: "" for field in contract["production_required_fields"]
    }
    template.update(
        {
            "submission_id": "B1-B7-cone01-R83-fill-me",
            "route_id": "",
            "source_target_id": TARGET_ID,
            "upstream_target_id": UPSTREAM_TARGET_ID,
            "source_r82_result_path": R82_RESULT,
            "source_r82_result_sha256": contract["source_r82_result_sha256"],
            "source_r82_ledger_path": R82_LEDGER,
            "source_r82_ledger_sha256": contract["source_r82_ledger_sha256"],
            "source_r82_verdict_path": R82_VERDICT,
            "source_r82_verdict_sha256": contract["source_r82_verdict_sha256"],
            "source_b7_boundary_path": B7_GCM_BOUNDARY,
            "source_b7_boundary_sha256": contract["source_b7_boundary_sha256"],
            "claimed_target_stv_reduction": 1.2,
            "claimed_t_ledger_reduction": 0,
            "candidate_after_t_ledger": contract["current_after_t_ledger"],
            "o3_closed": False,
            "reroute_allowed": False,
            "resource_saving_claimed": False,
            "b7_credit_requested": False,
            "claim_boundary": (
                "Template only. No B7 credit, O3 closure, reroute permission, or "
                "resource saving may be claimed before all R83 gates pass."
            ),
        }
    )
    template["template_hash"] = stable_self_hash(template, "template_hash")
    return template


def preflight_template(root: Path, contract: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    missing = [
        field for field in contract["production_required_fields"] if template.get(field) in ("", None)
    ]
    hash_failures = []
    hash_fields_seen = 0
    for field in contract["production_required_fields"]:
        if not field.endswith("_sha256"):
            continue
        path_field = field[: -len("_sha256")] + "_path"
        if template.get(field) in ("", None) or template.get(path_field) in ("", None):
            continue
        hash_fields_seen += 1
        if not path_hash_matches(root, template.get(path_field), template.get(field)):
            hash_failures.append(field)
    gates = {
        "all_required_fields_complete": missing == [],
        "all_hash_bound_artifacts_match": hash_failures == [] and missing == [],
        "source_r82_boundary_hashes_match": template["source_r82_result_sha256"]
        == contract["source_r82_result_sha256"]
        and template["source_r82_ledger_sha256"] == contract["source_r82_ledger_sha256"]
        and template["source_r82_verdict_sha256"] == contract["source_r82_verdict_sha256"],
        "claimed_t_ledger_reduction_at_least_591": int(
            template["claimed_t_ledger_reduction"]
        )
        >= contract["minimum_accepted_t_ledger_reduction"],
        "candidate_after_t_ledger_at_or_below_5632": int(template["candidate_after_t_ledger"])
        <= contract["target_1_20_max_after_t_ledger"],
        "stv_reprice_ledger_present": template.get("stv_reprice_ledger_path") not in ("", None),
        "logical_t_mapping_ledger_present": template.get("logical_t_mapping_ledger_path")
        not in ("", None),
        "no_double_counting_ledger_present": template.get("no_double_counting_ledger_path")
        not in ("", None),
        "replay_stdout_hash_matches": template.get("replay_stdout_path") not in ("", None)
        and template.get("replay_stdout_sha256") not in ("", None)
        and "replay_stdout_sha256" not in hash_failures,
        "claim_boundary_blocks_o3_reroute_until_audit": all(
            token in template["claim_boundary"].lower()
            for token in ["no b7 credit", "o3 closure", "reroute"]
        ),
    }
    failed = [gate for gate, passed in gates.items() if not passed]
    verdict = {
        "artifact": "R83 B7 gap-closure template preflight verdict",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_id": contract["contract_id"],
        "contract_hash": contract["contract_hash"],
        "template_hash": template["template_hash"],
        "gates": gates,
        "passed_gate_count": sum(1 for passed in gates.values() if passed),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "missing_required_fields": missing,
        "missing_required_field_count": len(missing),
        "hash_fields_seen": hash_fields_seen,
        "hash_failures": hash_failures,
        "accepted": failed == [],
        "accepted_b7_credit_delta": 0,
        "accepted_b7_space_time_volume_credit": 0,
        "claim_boundary": "The R83 template is a rejected placeholder and grants no B7 credit.",
    }
    verdict["verdict_hash"] = stable_self_hash(verdict, "verdict_hash")
    return verdict


def build_work_packets(contract: dict[str, Any]) -> dict[str, Any]:
    packets = {
        "artifact": "R83 B7 gap-closure work packets",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "minimum_accepted_t_ledger_reduction": contract["minimum_accepted_t_ledger_reduction"],
        "packets": [
            {
                "packet_id": "R83-G1-30-arbitrary-rotation-batch",
                "priority": 1,
                "target": "remove or reprice 30 arbitrary numeric rotations at cost 20 each",
                "candidate_t_ledger_reduction": 600,
                "can_close_1_20_gap_if_accepted": True,
                "required_evidence": [
                    "source-backed rotation rows",
                    "replay stdout",
                    "logical-T mapping ledger",
                    "STV reprice ledger",
                    "no-double-counting ledger",
                ],
            },
            {
                "packet_id": "R83-G2-591-proxy-t-row-batch",
                "priority": 2,
                "target": "submit at least 591 source-backed proxy-T units of reduction",
                "candidate_t_ledger_reduction": 591,
                "can_close_1_20_gap_if_accepted": True,
                "required_evidence": [
                    "row-level source/candidate artifacts",
                    "machine-check replay transcripts",
                    "logical-T mapping ledger",
                    "STV reprice ledger",
                    "claim-boundary audit",
                ],
            },
            {
                "packet_id": "R83-G3-full-b7-reprice",
                "priority": 3,
                "target": "provide an equivalent full B7 resource reprice that reaches 1.20x STV",
                "candidate_t_ledger_reduction": None,
                "can_close_1_20_gap_if_accepted": True,
                "required_evidence": [
                    "complete B7 reprice ledger",
                    "same-access assumptions",
                    "factory/path bottleneck audit",
                    "independent reproduction command",
                    "negative-overclaim checklist",
                ],
            },
        ],
        "claim_boundary": "Work packets are invitations for future PRs, not accepted B7 credit.",
    }
    packets["work_packet_hash"] = stable_self_hash(packets, "work_packet_hash")
    return packets


def build_blocker_queue(contract: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    queue = {
        "artifact": "R83 B7 gap-closure blocker queue",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "template_preflight_hash": preflight["verdict_hash"],
        "accepted_b7_credit_delta": 0,
        "queue": [
            {
                "blocker_id": "R83-B7-1",
                "priority": 1,
                "target_gate": "submitted_gap_closure_evidence",
                "needed_artifact": "fill all R83 production fields with source-backed replay evidence",
            },
            {
                "blocker_id": "R83-B7-2",
                "priority": 2,
                "target_gate": "logical_t_and_stv_reprice",
                "needed_artifact": "prove claimed T-ledger reduction maps into logical-T and STV accounting",
            },
            {
                "blocker_id": "R83-B7-3",
                "priority": 3,
                "target_gate": "independent_claim_boundary_audit",
                "needed_artifact": "audit that no O3, reroute, or B7 credit is claimed before R83 acceptance",
            },
        ],
    }
    queue["blocker_queue_hash"] = stable_self_hash(queue, "blocker_queue_hash")
    return queue


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    r82_result = load_json(root / R82_RESULT)
    r82_ledger = load_json(root / R82_LEDGER)
    r82_verdict = load_json(root / R82_VERDICT)
    r82_blocker_queue = load_json(root / R82_BLOCKER_QUEUE)
    b7_boundary = load_json(root / B7_GCM_BOUNDARY)
    b7_ft_ledger = load_json(root / B7_FT_LEDGER)

    contract = build_contract(root, r82_result, r82_ledger, r82_verdict, r82_blocker_queue, b7_boundary)
    write_json(root / R83_CONTRACT, contract)
    template = build_template(contract)
    write_json(root / R83_TEMPLATE, template)
    preflight = preflight_template(root, contract, template)
    write_json(root / R83_PREFLIGHT, preflight)
    work_packets = build_work_packets(contract)
    write_json(root / R83_WORK_PACKETS, work_packets)
    blocker_queue = build_blocker_queue(contract, preflight)
    write_json(root / R83_BLOCKER_QUEUE, blocker_queue)
    stdout = {
        "artifact": "R83 B7 gap-closure contract stdout",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "template_preflight_accepted": preflight["accepted"],
        "minimum_accepted_t_ledger_reduction": contract["minimum_accepted_t_ledger_reduction"],
        "work_packet_count": len(work_packets["packets"]),
        "accepted_b7_credit_delta": 0,
    }
    write_json(root / R83_STDOUT, stdout)

    requirements = [
        req(
            "A1",
            "R82 downstream B7 retest is complete and zero-credit",
            r82_result["summary"]["b7_downstream_retest_completed"] is True
            and r82_result["summary"]["accepted_b7_credit_delta"] == 0
            and r82_result["summary"]["min_t_ledger_gap_after_r81"] == 591,
            {
                "r82_result": R82_RESULT,
                "r82_payload_hash": r82_result["payload_hash"],
                "min_t_ledger_gap_after_r81": r82_result["summary"]["min_t_ledger_gap_after_r81"],
            },
        ),
        req(
            "A2",
            "R83 contract encodes the 591-unit 1.20x gap and 823-unit 1.25x gap",
            contract["minimum_accepted_t_ledger_reduction"] == 591
            and contract["target_1_25_t_ledger_gap_after_r81"] == 823,
            {
                "minimum_accepted_t_ledger_reduction": contract[
                    "minimum_accepted_t_ledger_reduction"
                ],
                "target_1_25_t_ledger_gap_after_r81": contract[
                    "target_1_25_t_ledger_gap_after_r81"
                ],
            },
        ),
        req(
            "A3",
            "R83 production contract has concrete required fields and gates",
            len(contract["production_required_fields"]) >= 30
            and len(contract["acceptance_gates"]) >= 10,
            {
                "production_required_field_count": len(contract["production_required_fields"]),
                "acceptance_gate_count": len(contract["acceptance_gates"]),
                "contract_hash": contract["contract_hash"],
            },
        ),
        req(
            "A4",
            "R83 placeholder template is rejected without granting credit",
            preflight["accepted"] is False
            and preflight["failed_gate_count"] >= 1
            and preflight["accepted_b7_credit_delta"] == 0,
            {
                "template_hash": template["template_hash"],
                "preflight_hash": preflight["verdict_hash"],
                "failed_gates": preflight["failed_gates"],
            },
        ),
        req(
            "A5",
            "R83 emits three PR-sized work packets",
            len(work_packets["packets"]) == 3
            and work_packets["packets"][0]["candidate_t_ledger_reduction"] == 600
            and work_packets["packets"][1]["candidate_t_ledger_reduction"] == 591,
            {
                "work_packet_hash": work_packets["work_packet_hash"],
                "packet_ids": [packet["packet_id"] for packet in work_packets["packets"]],
            },
        ),
        req(
            "A6",
            "R83 source artifacts are hash-bound",
            contract["source_r82_result_sha256"] == file_hash(root / R82_RESULT)
            and contract["source_r82_ledger_sha256"] == file_hash(root / R82_LEDGER)
            and contract["source_b7_boundary_sha256"] == file_hash(root / B7_GCM_BOUNDARY),
            {
                "source_r82_result_sha256": contract["source_r82_result_sha256"],
                "source_b7_boundary_sha256": contract["source_b7_boundary_sha256"],
            },
        ),
        req(
            "A7",
            "R83 preserves zero B7 credit and no O3/reroute/resource claim",
            template["o3_closed"] is False
            and template["reroute_allowed"] is False
            and template["resource_saving_claimed"] is False
            and template["b7_credit_requested"] is False
            and preflight["accepted_b7_credit_delta"] == 0,
            {
                "accepted_b7_credit_delta": preflight["accepted_b7_credit_delta"],
                "template_flags": {
                    "o3_closed": template["o3_closed"],
                    "reroute_allowed": template["reroute_allowed"],
                    "resource_saving_claimed": template["resource_saving_claimed"],
                    "b7_credit_requested": template["b7_credit_requested"],
                },
            },
        ),
        req(
            "A8",
            "R83 emits next blockers for submitted evidence, reprice, and audit",
            len(blocker_queue["queue"]) == 3,
            {
                "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
                "blocker_ids": [item["blocker_id"] for item in blocker_queue["queue"]],
            },
        ),
    ]
    failed_requirements = [
        requirement["requirement_id"]
        for requirement in requirements
        if not requirement["passed"]
    ]
    validation_errors = []
    if failed_requirements:
        validation_errors.append("one or more R83 requirements failed")
    if preflight["accepted_b7_credit_delta"] != 0:
        validation_errors.append("R83 must not grant B7 credit")

    payload = {
        "artifact": "B1/B7 cone01 R83 B7 gap-closure contract gate",
        "method": METHOD,
        "version": VERSION,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "generated_at_unix": int(time.time()),
        "contract_path": R83_CONTRACT,
        "contract_hash": contract["contract_hash"],
        "template_path": R83_TEMPLATE,
        "template_hash": template["template_hash"],
        "template_preflight_path": R83_PREFLIGHT,
        "template_preflight_hash": preflight["verdict_hash"],
        "work_packets_path": R83_WORK_PACKETS,
        "work_packet_hash": work_packets["work_packet_hash"],
        "blocker_queue_path": R83_BLOCKER_QUEUE,
        "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
        "stdout_path": R83_STDOUT,
        "stdout_sha256": file_hash(root / R83_STDOUT),
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
            "source_r82_payload_hash": r82_result["payload_hash"],
            "minimum_accepted_t_ledger_reduction": contract[
                "minimum_accepted_t_ledger_reduction"
            ],
            "target_1_20_t_ledger_gap_after_r81": 591,
            "target_1_25_t_ledger_gap_after_r81": 823,
            "target_1_20_max_after_t_ledger": contract["target_1_20_max_after_t_ledger"],
            "current_after_t_ledger": contract["current_after_t_ledger"],
            "production_required_field_count": len(contract["production_required_fields"]),
            "acceptance_gate_count": len(contract["acceptance_gates"]),
            "template_preflight_accepted": preflight["accepted"],
            "template_failed_gate_count": preflight["failed_gate_count"],
            "work_packet_count": len(work_packets["packets"]),
            "accepted_b7_credit_delta": 0,
            "accepted_b7_space_time_volume_credit": 0,
            "o3_closed": False,
            "reroute_allowed": False,
            "resource_saving_claimed": False,
            "contract_hash": contract["contract_hash"],
            "template_preflight_hash": preflight["verdict_hash"],
            "work_packet_hash": work_packets["work_packet_hash"],
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
    report_path = root / "research/B1_B7_cone01_R83_b7_gap_closure_contract_gate.md"
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone01 R83 B7 Gap-Closure Contract Gate",
        "",
        f"- Target: `{TARGET_ID}`",
        f"- Upstream target: `{UPSTREAM_TARGET_ID}`",
        f"- Method: `{METHOD}`",
        f"- Status: `{STATUS}`",
        f"- Model status: `{MODEL_STATUS}`",
        "",
        "## Result",
        "",
        "R83 converts the R82 zero-credit B7 retest into a fillable 591-unit",
        "gap-closure contract. The contract gives future PRs a precise acceptance",
        "surface: either remove at least 591 T-ledger units, or submit an equivalent",
        "full B7 reprice that reaches the current 1.20x STV boundary.",
        "",
        "## Key Counters",
        "",
        f"- Minimum accepted T-ledger reduction: `{summary['minimum_accepted_t_ledger_reduction']}`",
        f"- 1.20x STV gap after R81/R82: `{summary['target_1_20_t_ledger_gap_after_r81']}`",
        f"- 1.25x STV gap after R81/R82: `{summary['target_1_25_t_ledger_gap_after_r81']}`",
        f"- Production required fields: `{summary['production_required_field_count']}`",
        f"- Acceptance gates: `{summary['acceptance_gate_count']}`",
        f"- Work packets: `{summary['work_packet_count']}`",
        f"- Template accepted: `{summary['template_preflight_accepted']}`",
        f"- Accepted B7 credit delta: `{summary['accepted_b7_credit_delta']}`",
        "",
        "## Work Packets",
        "",
        "- `R83-G1-30-arbitrary-rotation-batch`: remove or reprice 30 arbitrary numeric rotations at cost 20 each.",
        "- `R83-G2-591-proxy-t-row-batch`: submit at least 591 source-backed proxy-T units of reduction.",
        "- `R83-G3-full-b7-reprice`: provide an equivalent full B7 resource reprice that reaches 1.20x STV.",
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
            "- Result JSON: `results/B1_B7_cone01_R83_b7_gap_closure_contract_gate_v0.json`",
            f"- Contract: `{R83_CONTRACT}`",
            f"- Template: `{R83_TEMPLATE}`",
            f"- Template preflight: `{R83_PREFLIGHT}`",
            f"- Work packets: `{R83_WORK_PACKETS}`",
            f"- Blocker queue: `{R83_BLOCKER_QUEUE}`",
            f"- Stdout: `{R83_STDOUT}`",
            "",
            "## Claim Boundary",
            "",
            "R83 is a contract gate, not a resource win. It does not close O3, does",
            "not allow reroute, does not claim resource saving, and does not grant B7",
            "dependency, resource, FT-ledger, STV, or credit. A future filled",
            "submission must pass the R83 gates and then a full downstream B7 replay.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--output",
        default="results/B1_B7_cone01_R83_b7_gap_closure_contract_gate_v0.json",
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
        raise SystemExit("B1/B7 R83 B7 gap-closure contract validation failed")


if __name__ == "__main__":
    main()
