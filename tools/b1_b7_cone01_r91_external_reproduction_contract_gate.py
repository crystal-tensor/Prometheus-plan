#!/usr/bin/env python3
"""T-B1-004go/T-B7-015x: R91 external reproduction contract for R89/R90."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r91_external_reproduction_contract_gate_v0"
STATUS = "cone01_r91_external_reproduction_contract_open_no_submission_yet"
MODEL_STATUS = "r90_review_exported_as_external_reproduction_contract_no_new_credit"
VERSION = "0.1"
TARGET_ID = "T-B1-004go/T-B7-015x"
UPSTREAM_TARGET_ID = "T-B1-004gn/T-B7-015w"
SUBMISSION_DIR = "results/B1_B7_cone01_o3_f4_exit_route_submissions"

R90_RESULT = "results/B1_B7_cone01_R90_r89_independent_replay_review_gate_v0.json"
R90_REVIEW_LEDGER = f"{SUBMISSION_DIR}/R90-G1-r89-independent-review-ledger.json"
R90_VERDICT = f"{SUBMISSION_DIR}/R90-G1-r89-double-count-kill-test.verdict.json"
R90_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R90-G1-post-review-blocker-queue.json"

R91_CONTRACT = f"{SUBMISSION_DIR}/R91-G1-external-reproduction-contract.json"
R91_TEMPLATE = f"{SUBMISSION_DIR}/R91-G1-external-reproduction-submission.template.json"
R91_EMPTY_SUBMISSION = f"{SUBMISSION_DIR}/R91-G1-external-reproduction-empty-submission.json"
R91_PREFLIGHT = f"{SUBMISSION_DIR}/R91-G1-external-reproduction-preflight.verdict.json"
R91_STDOUT = f"{SUBMISSION_DIR}/R91-G1-external-reproduction-contract.stdout.txt"
R91_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R91-G1-external-reproduction-blocker-queue.json"


REQUIRED_FIELDS = [
    "submission_id",
    "agent_id",
    "review_mode",
    "source_r90_result_sha256",
    "source_r90_review_ledger_hash",
    "source_r90_verdict_hash",
    "source_r90_blocker_queue_hash",
    "independent_environment_manifest_path",
    "independent_environment_manifest_sha256",
    "command_transcript_path",
    "command_transcript_sha256",
    "recomputed_baseline_after_t_ledger",
    "recomputed_candidate_t_ledger_reduction",
    "recomputed_candidate_after_t_ledger",
    "recomputed_target_1_20_margin",
    "recomputed_target_1_25_margin",
    "double_count_test_path",
    "double_count_test_sha256",
    "double_count_violation_found",
    "accepted_b7_credit_delta_after_review",
    "new_credit_delta",
    "credit_decision",
    "falsification_claimed",
    "reproduction_claimed",
    "o3_closed",
    "resource_saving_claimed",
    "physical_layout_claimed",
    "claim_boundary",
]

PRODUCTION_REQUIRED_FIELDS = [
    "independent_environment_manifest_path",
    "independent_environment_manifest_sha256",
    "command_transcript_path",
    "command_transcript_sha256",
    "recomputed_baseline_after_t_ledger",
    "recomputed_candidate_t_ledger_reduction",
    "recomputed_candidate_after_t_ledger",
    "recomputed_target_1_20_margin",
    "recomputed_target_1_25_margin",
    "double_count_test_path",
    "double_count_test_sha256",
    "double_count_violation_found",
    "credit_decision",
    "claim_boundary",
]


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


def build_contract(root: Path, r90_result: dict[str, Any], r90_ledger: dict[str, Any], r90_verdict: dict[str, Any], r90_blocker_queue: dict[str, Any]) -> dict[str, Any]:
    summary = r90_result["summary"]
    contract = {
        "artifact": "R91 G1 external reproduction contract",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_r90_result_path": R90_RESULT,
        "source_r90_result_sha256": file_hash(root / R90_RESULT),
        "source_r90_payload_hash": r90_result["payload_hash"],
        "source_r90_review_ledger_path": R90_REVIEW_LEDGER,
        "source_r90_review_ledger_sha256": file_hash(root / R90_REVIEW_LEDGER),
        "source_r90_review_ledger_hash": r90_ledger["review_ledger_hash"],
        "source_r90_verdict_path": R90_VERDICT,
        "source_r90_verdict_sha256": file_hash(root / R90_VERDICT),
        "source_r90_verdict_hash": r90_verdict["verdict_hash"],
        "source_r90_blocker_queue_path": R90_BLOCKER_QUEUE,
        "source_r90_blocker_queue_sha256": file_hash(root / R90_BLOCKER_QUEUE),
        "source_r90_blocker_queue_hash": r90_blocker_queue["blocker_queue_hash"],
        "route_id": summary["route_id"],
        "contract_id": "R91-G1-external-reproduction-contract",
        "purpose": "accept independent reproduction or falsification of the R89/R90 one-unit proxy credit",
        "required_fields": REQUIRED_FIELDS,
        "required_field_count": len(REQUIRED_FIELDS),
        "production_required_fields": PRODUCTION_REQUIRED_FIELDS,
        "production_required_field_count": len(PRODUCTION_REQUIRED_FIELDS),
        "accepted_review_modes": [
            "reproduce_r90",
            "falsify_double_count",
            "falsify_arithmetic",
            "extend_to_1_25",
            "physical_layout_reprice",
        ],
        "acceptance_rules": {
            "hash_bound_to_r90": True,
            "must_include_command_transcript": True,
            "must_recompute_target_rows": True,
            "must_report_double_count_decision": True,
            "must_keep_claim_boundary_explicit": True,
            "positive_reproduction_allowed": True,
            "falsification_allowed": True,
            "new_credit_requires_new_artifacts": True,
            "o3_claim_forbidden_without_physical_layout": True,
        },
        "frozen_r90_values": {
            "recomputed_baseline_after_t_ledger": r90_ledger[
                "recomputed_baseline_after_t_ledger"
            ],
            "candidate_after_t_ledger": summary["recomputed_candidate_after_t_ledger"],
            "target_1_20_margin": summary["recomputed_target_1_20_margin"],
            "target_1_25_margin": summary["recomputed_target_1_25_margin"],
            "accepted_b7_credit_delta_after_review": summary[
                "accepted_b7_credit_delta_after_review"
            ],
            "new_credit_delta": summary["new_credit_delta"],
        },
        "baseline_after_t_ledger": r90_ledger["recomputed_baseline_after_t_ledger"],
        "candidate_t_ledger_reduction": r90_ledger[
            "recomputed_candidate_t_ledger_reduction"
        ],
        "candidate_after_t_ledger": r90_ledger["recomputed_candidate_after_t_ledger"],
        "target_1_20_margin": r90_ledger["recomputed_target_1_20_margin"],
        "target_1_25_margin": r90_ledger["recomputed_target_1_25_margin"],
        "external_submission_accepted": False,
        "accepted_external_reproduction_count": 0,
        "accepted_external_falsification_count": 0,
        "new_credit_delta": 0,
        "o3_closed": False,
        "resource_saving_claimed": False,
        "physical_layout_claimed": False,
        "claim_boundary": (
            "R91 exports R90 as an external reproduction/falsification contract. "
            "It accepts no external submission yet, grants no new credit, and "
            "does not close 1.25x, O3, physical-layout, or resource-saving claims."
        ),
    }
    contract["contract_hash"] = stable_self_hash(contract, "contract_hash")
    return contract


def build_template(contract: dict[str, Any]) -> dict[str, Any]:
    template = {
        "artifact": "R91 G1 external reproduction submission template",
        "contract_id": contract["contract_id"],
        "contract_hash": contract["contract_hash"],
        "fields": {field: None for field in REQUIRED_FIELDS},
        "allowed_credit_decisions": [
            "reproduced_preserve_credit",
            "falsified_revoke_credit",
            "insufficient_evidence",
            "new_credit_candidate_pending_review",
        ],
        "claim_boundary_options": [
            "external_reproduction_only",
            "external_falsification_only",
            "external_new_credit_candidate_not_accepted",
            "physical_layout_candidate_not_o3_closure",
        ],
    }
    template["template_hash"] = stable_self_hash(template, "template_hash")
    return template


def build_empty_submission(contract: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    submission = {
        "artifact": "R91 current empty external reproduction submission",
        "contract_id": contract["contract_id"],
        "contract_hash": contract["contract_hash"],
        "template_hash": template["template_hash"],
        "fields": {
            "submission_id": "R91-G1-empty",
            "agent_id": "none",
            "review_mode": "none",
            "source_r90_result_sha256": contract["source_r90_result_sha256"],
            "source_r90_review_ledger_hash": contract["source_r90_review_ledger_hash"],
            "source_r90_verdict_hash": contract["source_r90_verdict_hash"],
            "source_r90_blocker_queue_hash": contract["source_r90_blocker_queue_hash"],
            "independent_environment_manifest_path": None,
            "independent_environment_manifest_sha256": None,
            "command_transcript_path": None,
            "command_transcript_sha256": None,
            "recomputed_baseline_after_t_ledger": None,
            "recomputed_candidate_t_ledger_reduction": None,
            "recomputed_candidate_after_t_ledger": None,
            "recomputed_target_1_20_margin": None,
            "recomputed_target_1_25_margin": None,
            "double_count_test_path": None,
            "double_count_test_sha256": None,
            "double_count_violation_found": None,
            "accepted_b7_credit_delta_after_review": None,
            "new_credit_delta": 0,
            "credit_decision": "insufficient_evidence",
            "falsification_claimed": False,
            "reproduction_claimed": False,
            "o3_closed": False,
            "resource_saving_claimed": False,
            "physical_layout_claimed": False,
            "claim_boundary": "empty_submission_no_external_evidence",
        },
    }
    submission["submission_hash"] = stable_self_hash(submission, "submission_hash")
    return submission


def build_preflight(contract: dict[str, Any], submission: dict[str, Any]) -> dict[str, Any]:
    fields = submission["fields"]
    missing_required = [field for field in REQUIRED_FIELDS if field not in fields]
    missing_production = [
        field for field in PRODUCTION_REQUIRED_FIELDS if fields.get(field) in (None, "")
    ]
    gates = {
        "all_required_fields_present": not missing_required,
        "production_evidence_present": not missing_production,
        "external_environment_present": bool(fields.get("independent_environment_manifest_path"))
        and bool(fields.get("independent_environment_manifest_sha256")),
        "command_transcript_present": bool(fields.get("command_transcript_path"))
        and bool(fields.get("command_transcript_sha256")),
        "target_arithmetic_recomputed": isinstance(
            fields.get("recomputed_candidate_after_t_ledger"), int
        )
        and isinstance(fields.get("recomputed_target_1_20_margin"), int)
        and isinstance(fields.get("recomputed_target_1_25_margin"), int),
        "double_count_decision_present": fields.get("double_count_violation_found")
        is not None,
        "claim_boundary_safe": fields.get("o3_closed") is False
        and fields.get("resource_saving_claimed") is False
        and fields.get("physical_layout_claimed") is False,
        "external_submission_accepted": False,
    }
    failed = [gate for gate, passed in gates.items() if not passed]
    preflight = {
        "artifact": "R91 G1 external reproduction preflight verdict",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "submission_hash": submission["submission_hash"],
        "gates": gates,
        "passed_gate_count": sum(1 for passed in gates.values() if passed),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "missing_required_fields": missing_required,
        "missing_production_fields": missing_production,
        "accepted": False,
        "accepted_external_reproduction_count": 0,
        "accepted_external_falsification_count": 0,
        "accepted_b7_credit_delta_after_review": 1,
        "new_credit_delta": 0,
        "claim_boundary": contract["claim_boundary"],
    }
    preflight["preflight_hash"] = stable_self_hash(preflight, "preflight_hash")
    return preflight


def build_blocker_queue(contract: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    queue = {
        "artifact": "R91 G1 external reproduction blocker queue",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "preflight_hash": preflight["preflight_hash"],
        "queue": [
            {
                "blocker_id": "R91-G1-1",
                "priority": 1,
                "target_gate": "external_reproduction_submission",
                "needed_artifact": "hash-bound third-party submission using the R91 template",
                "missing_fields": preflight["missing_production_fields"],
            },
            {
                "blocker_id": "R91-G1-2",
                "priority": 2,
                "target_gate": "double_count_attack",
                "needed_artifact": "independent double-count test that either preserves or revokes the R89/R90 credit",
            },
            {
                "blocker_id": "R91-G1-3",
                "priority": 3,
                "target_gate": "one_point_two_five_or_layout",
                "needed_artifact": "new accepted reduction or physical-layout reprice before stronger B7 claims",
            },
        ],
    }
    queue["blocker_queue_hash"] = stable_self_hash(queue, "blocker_queue_hash")
    return queue


def write_stdout(root: Path, contract: dict[str, Any], preflight: dict[str, Any], queue: dict[str, Any]) -> str:
    text = "\n".join(
        [
            "R91 external reproduction contract stdout",
            f"method={METHOD}",
            f"source_target_id={TARGET_ID}",
            f"upstream_target_id={UPSTREAM_TARGET_ID}",
            f"contract_hash={contract['contract_hash']}",
            f"preflight_hash={preflight['preflight_hash']}",
            f"blocker_queue_hash={queue['blocker_queue_hash']}",
            f"required_field_count={contract['required_field_count']}",
            f"production_required_field_count={contract['production_required_field_count']}",
            f"failed_gate_count={preflight['failed_gate_count']}",
            "external_submission_accepted=false",
            "new_credit_delta=0",
            "o3_closed=false",
        ]
    ) + "\n"
    path = root / R91_STDOUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    r90_result = load_json(root / R90_RESULT)
    r90_ledger = load_json(root / R90_REVIEW_LEDGER)
    r90_verdict = load_json(root / R90_VERDICT)
    r90_blocker_queue = load_json(root / R90_BLOCKER_QUEUE)

    contract = build_contract(root, r90_result, r90_ledger, r90_verdict, r90_blocker_queue)
    write_json(root / R91_CONTRACT, contract)
    template = build_template(contract)
    write_json(root / R91_TEMPLATE, template)
    empty_submission = build_empty_submission(contract, template)
    write_json(root / R91_EMPTY_SUBMISSION, empty_submission)
    preflight = build_preflight(contract, empty_submission)
    write_json(root / R91_PREFLIGHT, preflight)
    blocker_queue = build_blocker_queue(contract, preflight)
    write_json(root / R91_BLOCKER_QUEUE, blocker_queue)
    stdout_sha256 = write_stdout(root, contract, preflight, blocker_queue)

    requirements = [
        req(
            "A1",
            "R91 binds the R90 result, review ledger, verdict, and blocker queue",
            r90_result["summary"]["source_target_id"] == UPSTREAM_TARGET_ID
            and r90_result["review_ledger_hash"] == r90_ledger["review_ledger_hash"]
            and r90_result["verdict_hash"] == r90_verdict["verdict_hash"],
            {
                "r90_payload_hash": r90_result["payload_hash"],
                "r90_review_ledger_hash": r90_ledger["review_ledger_hash"],
                "r90_verdict_hash": r90_verdict["verdict_hash"],
            },
        ),
        req(
            "A2",
            "R91 emits an external reproduction contract with required schema",
            contract["required_field_count"] == len(REQUIRED_FIELDS)
            and contract["production_required_field_count"] == len(PRODUCTION_REQUIRED_FIELDS)
            and len(contract["accepted_review_modes"]) == 5,
            {
                "contract_hash": contract["contract_hash"],
                "required_field_count": contract["required_field_count"],
                "production_required_field_count": contract[
                    "production_required_field_count"
                ],
            },
        ),
        req(
            "A3",
            "R91 emits a fillable external submission template",
            template["contract_hash"] == contract["contract_hash"]
            and set(template["fields"]) == set(REQUIRED_FIELDS),
            {
                "template_hash": template["template_hash"],
                "template_field_count": len(template["fields"]),
            },
        ),
        req(
            "A4",
            "R91 rejects the current empty submission before external evidence exists",
            preflight["accepted"] is False
            and preflight["failed_gate_count"] == 6
            and preflight["accepted_external_reproduction_count"] == 0
            and preflight["accepted_external_falsification_count"] == 0,
            {
                "preflight_hash": preflight["preflight_hash"],
                "failed_gates": preflight["failed_gates"],
                "missing_production_field_count": len(preflight["missing_production_fields"]),
            },
        ),
        req(
            "A5",
            "R91 grants no new credit and keeps stronger claims closed",
            contract["new_credit_delta"] == 0
            and contract["o3_closed"] is False
            and contract["resource_saving_claimed"] is False
            and contract["physical_layout_claimed"] is False,
            {
                "new_credit_delta": contract["new_credit_delta"],
                "o3_closed": contract["o3_closed"],
                "resource_saving_claimed": contract["resource_saving_claimed"],
                "physical_layout_claimed": contract["physical_layout_claimed"],
            },
        ),
        req(
            "A6",
            "R91 emits blockers for external submission, double-count attack, and stronger B7 evidence",
            len(blocker_queue["queue"]) == 3
            and [item["target_gate"] for item in blocker_queue["queue"]]
            == [
                "external_reproduction_submission",
                "double_count_attack",
                "one_point_two_five_or_layout",
            ],
            {
                "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
                "blocker_ids": [item["blocker_id"] for item in blocker_queue["queue"]],
            },
        ),
    ]

    failed_requirements = [
        requirement["requirement_id"] for requirement in requirements if not requirement["passed"]
    ]
    validation_errors = []
    if failed_requirements:
        validation_errors.append("one or more R91 requirements failed")
    if contract["external_submission_accepted"]:
        validation_errors.append("R91 must not accept an external submission yet")
    if contract["new_credit_delta"] != 0:
        validation_errors.append("R91 must not grant new credit")

    payload = {
        "artifact": "B1/B7 cone01 R91 external reproduction contract gate",
        "method": METHOD,
        "version": VERSION,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "generated_at_unix": int(time.time()),
        "contract_path": R91_CONTRACT,
        "contract_hash": contract["contract_hash"],
        "template_path": R91_TEMPLATE,
        "template_hash": template["template_hash"],
        "empty_submission_path": R91_EMPTY_SUBMISSION,
        "empty_submission_hash": empty_submission["submission_hash"],
        "preflight_path": R91_PREFLIGHT,
        "preflight_hash": preflight["preflight_hash"],
        "stdout_path": R91_STDOUT,
        "stdout_sha256": stdout_sha256,
        "blocker_queue_path": R91_BLOCKER_QUEUE,
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
            "route_id": contract["route_id"],
            "contract_id": contract["contract_id"],
            "required_field_count": contract["required_field_count"],
            "production_required_field_count": contract[
                "production_required_field_count"
            ],
            "accepted_review_mode_count": len(contract["accepted_review_modes"]),
            "template_emitted": True,
            "external_submission_accepted": contract["external_submission_accepted"],
            "accepted_external_reproduction_count": contract[
                "accepted_external_reproduction_count"
            ],
            "accepted_external_falsification_count": contract[
                "accepted_external_falsification_count"
            ],
            "preflight_accepted": preflight["accepted"],
            "preflight_failed_gate_count": preflight["failed_gate_count"],
            "missing_production_field_count": len(preflight["missing_production_fields"]),
            "accepted_b7_credit_delta_after_review": preflight[
                "accepted_b7_credit_delta_after_review"
            ],
            "new_credit_delta": contract["new_credit_delta"],
            "baseline_after_t_ledger": contract["baseline_after_t_ledger"],
            "candidate_t_ledger_reduction": contract["candidate_t_ledger_reduction"],
            "candidate_after_t_ledger": contract["candidate_after_t_ledger"],
            "target_1_20_margin": contract["target_1_20_margin"],
            "target_1_25_margin": contract["target_1_25_margin"],
            "o3_closed": contract["o3_closed"],
            "resource_saving_claimed": contract["resource_saving_claimed"],
            "physical_layout_claimed": contract["physical_layout_claimed"],
            "contract_hash": contract["contract_hash"],
            "template_hash": template["template_hash"],
            "empty_submission_hash": empty_submission["submission_hash"],
            "preflight_hash": preflight["preflight_hash"],
            "stdout_sha256": stdout_sha256,
            "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
            "payload_hash": None,
            "requirements_passed": sum(1 for requirement in requirements if requirement["passed"]),
            "requirements_failed": len(failed_requirements),
            "failed_requirement_ids": failed_requirements,
            "validation_error_count": len(validation_errors),
        },
    }
    payload["payload_hash"] = stable_self_hash(payload, "payload_hash")
    payload["summary"]["payload_hash"] = payload["payload_hash"]
    return payload


def write_report(root: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone01 R91 External Reproduction Contract Gate",
        "",
        f"- Target: `{TARGET_ID}`",
        f"- Upstream target: `{UPSTREAM_TARGET_ID}`",
        f"- Method: `{METHOD}`",
        f"- Status: `{STATUS}`",
        f"- Model status: `{MODEL_STATUS}`",
        "",
        "## Result",
        "",
        "R91 exports the R89/R90 one-unit proxy credit into a fillable external",
        "reproduction or falsification contract. It defines the required fields for",
        "a third-party submission, emits a template, and rejects the current empty",
        "submission until independent environment, command transcript, target-row",
        "recomputation, and double-count evidence are supplied.",
        "",
        "No external reproduction is accepted yet. No falsification is accepted yet.",
        "No new credit is granted. The R89/R90 one-unit proxy credit remains the only",
        "counted B7 credit and remains bounded to `1.20x` proxy FT/STV scope.",
        "",
        "## Key Counters",
        "",
        f"- Required fields: `{summary['required_field_count']}`",
        f"- Production-required fields: `{summary['production_required_field_count']}`",
        f"- Accepted review modes: `{summary['accepted_review_mode_count']}`",
        f"- External submission accepted: `{summary['external_submission_accepted']}`",
        f"- Preflight failed gates: `{summary['preflight_failed_gate_count']}`",
        f"- Missing production fields: `{summary['missing_production_field_count']}`",
        f"- Accepted external reproductions: `{summary['accepted_external_reproduction_count']}`",
        f"- Accepted external falsifications: `{summary['accepted_external_falsification_count']}`",
        f"- New credit delta: `{summary['new_credit_delta']}`",
        f"- 1.20x margin inherited from R90: `{summary['target_1_20_margin']}`",
        f"- 1.25x margin inherited from R90: `{summary['target_1_25_margin']}`",
        "",
        "## Requirements",
        "",
    ]
    for requirement in payload["requirements"]:
        status = "PASS" if requirement["passed"] else "FAIL"
        lines.append(f"- `{requirement['requirement_id']}` {status}: {requirement['label']}")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            "- Result JSON: `results/B1_B7_cone01_R91_external_reproduction_contract_gate_v0.json`",
            f"- Contract: `{R91_CONTRACT}`",
            f"- Template: `{R91_TEMPLATE}`",
            f"- Empty submission: `{R91_EMPTY_SUBMISSION}`",
            f"- Preflight verdict: `{R91_PREFLIGHT}`",
            f"- Stdout: `{R91_STDOUT}`",
            f"- Blocker queue: `{R91_BLOCKER_QUEUE}`",
            "",
            "## Claim Boundary",
            "",
            "R91 is a collaboration contract, not a new technical credit. It accepts",
            "no external submission yet, grants no new B7 credit, does not close the",
            "1.25x gap, and does not close O3, physical-layout, resource-saving, or",
            "product-readiness claims.",
            "",
        ]
    )
    report_path = root / "research/B1_B7_cone01_R91_external_reproduction_contract_gate.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    payload = build_payload(args)
    result_path = root / "results/B1_B7_cone01_R91_external_reproduction_contract_gate_v0.json"
    write_json(result_path, payload)
    write_report(root, payload)
    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
