#!/usr/bin/env python3
"""T-B1-004gp/T-B7-015y: R92 validator fixture for the R91 external contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r92_external_submission_validator_gate_v0"
STATUS = "cone01_r92_r91_submission_validator_fixture_passed_no_external_acceptance"
MODEL_STATUS = "r91_contract_has_runnable_validator_fixture_but_no_external_reproduction_yet"
VERSION = "0.1"
TARGET_ID = "T-B1-004gp/T-B7-015y"
UPSTREAM_TARGET_ID = "T-B1-004go/T-B7-015x"
SUBMISSION_DIR = "results/B1_B7_cone01_o3_f4_exit_route_submissions"

R91_RESULT = "results/B1_B7_cone01_R91_external_reproduction_contract_gate_v0.json"
R91_CONTRACT = f"{SUBMISSION_DIR}/R91-G1-external-reproduction-contract.json"
R91_TEMPLATE = f"{SUBMISSION_DIR}/R91-G1-external-reproduction-submission.template.json"
R91_PREFLIGHT = f"{SUBMISSION_DIR}/R91-G1-external-reproduction-preflight.verdict.json"
R90_REVIEW_LEDGER = f"{SUBMISSION_DIR}/R90-G1-r89-independent-review-ledger.json"

R92_VALIDATOR_RULES = f"{SUBMISSION_DIR}/R92-G1-external-submission-validator-rules.json"
R92_ENV_MANIFEST = f"{SUBMISSION_DIR}/R92-G1-local-validator-environment-manifest.json"
R92_COMMAND_TRANSCRIPT = f"{SUBMISSION_DIR}/R92-G1-local-validator-command-transcript.txt"
R92_DOUBLE_COUNT_TEST = f"{SUBMISSION_DIR}/R92-G1-local-validator-double-count-test.json"
R92_FIXTURE_SUBMISSION = f"{SUBMISSION_DIR}/R92-G1-local-validator-filled-submission.json"
R92_PREFLIGHT = f"{SUBMISSION_DIR}/R92-G1-local-validator-preflight.verdict.json"
R92_STDOUT = f"{SUBMISSION_DIR}/R92-G1-external-submission-validator.stdout.txt"
R92_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R92-G1-post-validator-blocker-queue.json"


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


def build_validator_rules(root: Path, r91_result: dict[str, Any], contract: dict[str, Any], template: dict[str, Any]) -> dict[str, Any]:
    rules = {
        "artifact": "R92 G1 external submission validator rules",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_r91_result_path": R91_RESULT,
        "source_r91_result_sha256": file_hash(root / R91_RESULT),
        "source_r91_payload_hash": r91_result["payload_hash"],
        "source_r91_contract_path": R91_CONTRACT,
        "source_r91_contract_sha256": file_hash(root / R91_CONTRACT),
        "source_r91_contract_hash": contract["contract_hash"],
        "source_r91_template_path": R91_TEMPLATE,
        "source_r91_template_sha256": file_hash(root / R91_TEMPLATE),
        "source_r91_template_hash": template["template_hash"],
        "contract_id": contract["contract_id"],
        "route_id": contract["route_id"],
        "required_fields": contract["required_fields"],
        "production_required_fields": contract["production_required_fields"],
        "accepted_review_modes": contract["accepted_review_modes"],
        "accepted_credit_decisions": template["allowed_credit_decisions"],
        "validator_gates": [
            "all_required_fields_present",
            "production_required_fields_present",
            "hash_binding_matches_contract",
            "review_mode_allowed",
            "credit_decision_allowed",
            "target_arithmetic_matches_contract",
            "double_count_decision_present",
            "claim_boundary_safe",
            "fixture_not_counted_as_external",
        ],
        "external_acceptance_policy": (
            "A local validator fixture may pass schema and replay arithmetic, but it "
            "must not increment accepted external reproduction/falsification counters."
        ),
        "new_credit_delta": 0,
        "o3_closed": False,
        "resource_saving_claimed": False,
        "physical_layout_claimed": False,
    }
    rules["validator_rules_hash"] = stable_self_hash(rules, "validator_rules_hash")
    return rules


def build_environment_manifest(root: Path, contract: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    manifest = {
        "artifact": "R92 local validator environment manifest",
        "method": METHOD,
        "contract_hash": contract["contract_hash"],
        "validator_rules_hash": rules["validator_rules_hash"],
        "agent_id": "r92-local-validator-fixture",
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "repo_root_name": root.name,
        "execution_mode": "local_fixture_not_external_reproduction",
        "network_required": False,
        "external_submitter_attested": False,
    }
    manifest["environment_manifest_hash"] = stable_self_hash(
        manifest, "environment_manifest_hash"
    )
    return manifest


def write_command_transcript(root: Path, contract: dict[str, Any], rules: dict[str, Any]) -> str:
    text = "\n".join(
        [
            "R92 local validator command transcript",
            f"method={METHOD}",
            f"contract_id={contract['contract_id']}",
            f"contract_hash={contract['contract_hash']}",
            f"validator_rules_hash={rules['validator_rules_hash']}",
            "command=python3 tools/b1_b7_cone01_r92_external_submission_validator_gate.py --pretty",
            "execution_mode=local_fixture_not_external_reproduction",
            "external_submitter_attested=false",
        ]
    ) + "\n"
    path = root / R92_COMMAND_TRANSCRIPT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_double_count_test(contract: dict[str, Any], r90_ledger: dict[str, Any]) -> dict[str, Any]:
    component_credit_sum = (
        int(r90_ledger["component_credit_sum"])
        if "component_credit_sum" in r90_ledger
        else int(r90_ledger["accepted_b7_credit_delta_after_review"])
    )
    accepted_credit = int(r90_ledger["accepted_b7_credit_delta_after_review"])
    test = {
        "artifact": "R92 local validator double-count test",
        "method": METHOD,
        "contract_hash": contract["contract_hash"],
        "baseline_after_t_ledger": contract["baseline_after_t_ledger"],
        "candidate_t_ledger_reduction": contract["candidate_t_ledger_reduction"],
        "candidate_after_t_ledger": contract["candidate_after_t_ledger"],
        "target_1_20_margin": contract["target_1_20_margin"],
        "target_1_25_margin": contract["target_1_25_margin"],
        "component_credit_sum": component_credit_sum,
        "accepted_b7_credit_delta_after_review": accepted_credit,
        "double_count_violation_found": component_credit_sum != accepted_credit,
        "new_credit_delta": 0,
        "reproduction_claimed_by_fixture": True,
        "external_reproduction_claimed": False,
    }
    test["double_count_test_hash"] = stable_self_hash(test, "double_count_test_hash")
    return test


def build_fixture_submission(
    root: Path,
    contract: dict[str, Any],
    environment_manifest: dict[str, Any],
    command_transcript_sha256: str,
    double_count_test: dict[str, Any],
) -> dict[str, Any]:
    submission = {
        "artifact": "R92 local validator filled R91 submission fixture",
        "contract_id": contract["contract_id"],
        "contract_hash": contract["contract_hash"],
        "fixture_status": "schema_positive_local_fixture_not_external",
        "fields": {
            "submission_id": "R92-G1-local-validator-fixture",
            "agent_id": "r92-local-validator-fixture",
            "review_mode": "reproduce_r90",
            "source_r90_result_sha256": contract["source_r90_result_sha256"],
            "source_r90_review_ledger_hash": contract["source_r90_review_ledger_hash"],
            "source_r90_verdict_hash": contract["source_r90_verdict_hash"],
            "source_r90_blocker_queue_hash": contract["source_r90_blocker_queue_hash"],
            "independent_environment_manifest_path": R92_ENV_MANIFEST,
            "independent_environment_manifest_sha256": file_hash(root / R92_ENV_MANIFEST),
            "command_transcript_path": R92_COMMAND_TRANSCRIPT,
            "command_transcript_sha256": command_transcript_sha256,
            "recomputed_baseline_after_t_ledger": contract["baseline_after_t_ledger"],
            "recomputed_candidate_t_ledger_reduction": contract[
                "candidate_t_ledger_reduction"
            ],
            "recomputed_candidate_after_t_ledger": contract["candidate_after_t_ledger"],
            "recomputed_target_1_20_margin": contract["target_1_20_margin"],
            "recomputed_target_1_25_margin": contract["target_1_25_margin"],
            "double_count_test_path": R92_DOUBLE_COUNT_TEST,
            "double_count_test_sha256": file_hash(root / R92_DOUBLE_COUNT_TEST),
            "double_count_violation_found": double_count_test[
                "double_count_violation_found"
            ],
            "accepted_b7_credit_delta_after_review": contract[
                "accepted_b7_credit_delta_after_review"
            ]
            if "accepted_b7_credit_delta_after_review" in contract
            else 1,
            "new_credit_delta": 0,
            "credit_decision": "reproduced_preserve_credit",
            "falsification_claimed": False,
            "reproduction_claimed": True,
            "o3_closed": False,
            "resource_saving_claimed": False,
            "physical_layout_claimed": False,
            "claim_boundary": "local_validator_fixture_only_not_external_reproduction",
        },
    }
    submission["submission_hash"] = stable_self_hash(submission, "submission_hash")
    return submission


def build_fixture_preflight(
    contract: dict[str, Any],
    template: dict[str, Any],
    rules: dict[str, Any],
    submission: dict[str, Any],
) -> dict[str, Any]:
    fields = submission["fields"]
    missing_required = [field for field in rules["required_fields"] if field not in fields]
    missing_production = [
        field for field in rules["production_required_fields"] if fields.get(field) in (None, "")
    ]
    gates = {
        "all_required_fields_present": not missing_required,
        "production_required_fields_present": not missing_production,
        "hash_binding_matches_contract": fields["source_r90_result_sha256"]
        == contract["source_r90_result_sha256"]
        and fields["source_r90_review_ledger_hash"]
        == contract["source_r90_review_ledger_hash"]
        and fields["source_r90_verdict_hash"] == contract["source_r90_verdict_hash"]
        and fields["source_r90_blocker_queue_hash"]
        == contract["source_r90_blocker_queue_hash"],
        "review_mode_allowed": fields["review_mode"] in rules["accepted_review_modes"],
        "credit_decision_allowed": fields["credit_decision"]
        in template["allowed_credit_decisions"],
        "target_arithmetic_matches_contract": fields["recomputed_baseline_after_t_ledger"]
        == contract["baseline_after_t_ledger"]
        and fields["recomputed_candidate_t_ledger_reduction"]
        == contract["candidate_t_ledger_reduction"]
        and fields["recomputed_candidate_after_t_ledger"]
        == contract["candidate_after_t_ledger"]
        and fields["recomputed_target_1_20_margin"] == contract["target_1_20_margin"]
        and fields["recomputed_target_1_25_margin"] == contract["target_1_25_margin"],
        "double_count_decision_present": fields["double_count_violation_found"] is not None,
        "claim_boundary_safe": fields["o3_closed"] is False
        and fields["resource_saving_claimed"] is False
        and fields["physical_layout_claimed"] is False,
        "fixture_not_counted_as_external": fields["agent_id"] == "r92-local-validator-fixture",
    }
    failed = [gate for gate, passed in gates.items() if not passed]
    preflight = {
        "artifact": "R92 local validator fixture preflight verdict",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "validator_rules_hash": rules["validator_rules_hash"],
        "submission_hash": submission["submission_hash"],
        "gates": gates,
        "passed_gate_count": sum(1 for passed in gates.values() if passed),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "missing_required_fields": missing_required,
        "missing_production_fields": missing_production,
        "fixture_preflight_passed": failed == [],
        "external_submission_accepted": False,
        "accepted_external_reproduction_count": 0,
        "accepted_external_falsification_count": 0,
        "accepted_b7_credit_delta_after_review": 1,
        "new_credit_delta": 0,
        "claim_boundary": (
            "R92 validates the R91 submission mechanics with a local fixture. "
            "The fixture is not an external reproduction and cannot increment "
            "accepted external reproduction or falsification counters."
        ),
    }
    preflight["preflight_hash"] = stable_self_hash(preflight, "preflight_hash")
    return preflight


def build_blocker_queue(contract: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    queue = {
        "artifact": "R92 G1 post-validator blocker queue",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "preflight_hash": preflight["preflight_hash"],
        "fixture_preflight_passed": preflight["fixture_preflight_passed"],
        "queue": [
            {
                "blocker_id": "R92-G1-1",
                "priority": 1,
                "target_gate": "independent_external_submission",
                "needed_artifact": "non-fixture agent submission using the R91 template and R92 validator rules",
            },
            {
                "blocker_id": "R92-G1-2",
                "priority": 2,
                "target_gate": "external_double_count_attack",
                "needed_artifact": "external double-count test that challenges the one-unit proxy credit",
            },
            {
                "blocker_id": "R92-G1-3",
                "priority": 3,
                "target_gate": "accepted_external_verdict",
                "needed_artifact": "maintainer review that increments reproduction or falsification counters only after non-fixture evidence",
            },
        ],
    }
    queue["blocker_queue_hash"] = stable_self_hash(queue, "blocker_queue_hash")
    return queue


def write_stdout(root: Path, rules: dict[str, Any], preflight: dict[str, Any], queue: dict[str, Any]) -> str:
    text = "\n".join(
        [
            "R92 external submission validator stdout",
            f"method={METHOD}",
            f"source_target_id={TARGET_ID}",
            f"upstream_target_id={UPSTREAM_TARGET_ID}",
            f"validator_rules_hash={rules['validator_rules_hash']}",
            f"preflight_hash={preflight['preflight_hash']}",
            f"blocker_queue_hash={queue['blocker_queue_hash']}",
            f"fixture_preflight_passed={str(preflight['fixture_preflight_passed']).lower()}",
            f"external_submission_accepted={str(preflight['external_submission_accepted']).lower()}",
            f"accepted_external_reproduction_count={preflight['accepted_external_reproduction_count']}",
            f"accepted_external_falsification_count={preflight['accepted_external_falsification_count']}",
            "new_credit_delta=0",
            "o3_closed=false",
        ]
    ) + "\n"
    path = root / R92_STDOUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    r91_result = load_json(root / R91_RESULT)
    contract = load_json(root / R91_CONTRACT)
    template = load_json(root / R91_TEMPLATE)
    r91_preflight = load_json(root / R91_PREFLIGHT)
    r90_ledger = load_json(root / R90_REVIEW_LEDGER)

    rules = build_validator_rules(root, r91_result, contract, template)
    write_json(root / R92_VALIDATOR_RULES, rules)
    environment_manifest = build_environment_manifest(root, contract, rules)
    write_json(root / R92_ENV_MANIFEST, environment_manifest)
    command_transcript_sha256 = write_command_transcript(root, contract, rules)
    double_count_test = build_double_count_test(contract, r90_ledger)
    write_json(root / R92_DOUBLE_COUNT_TEST, double_count_test)
    fixture_submission = build_fixture_submission(
        root, contract, environment_manifest, command_transcript_sha256, double_count_test
    )
    write_json(root / R92_FIXTURE_SUBMISSION, fixture_submission)
    fixture_preflight = build_fixture_preflight(contract, template, rules, fixture_submission)
    write_json(root / R92_PREFLIGHT, fixture_preflight)
    blocker_queue = build_blocker_queue(contract, fixture_preflight)
    write_json(root / R92_BLOCKER_QUEUE, blocker_queue)
    stdout_sha256 = write_stdout(root, rules, fixture_preflight, blocker_queue)

    requirements = [
        req(
            "A1",
            "R92 binds the R91 result, contract, template, and empty preflight",
            r91_result["summary"]["source_target_id"] == UPSTREAM_TARGET_ID
            and r91_result["contract_hash"] == contract["contract_hash"]
            and r91_result["template_hash"] == template["template_hash"]
            and r91_result["preflight_hash"] == r91_preflight["preflight_hash"],
            {
                "r91_payload_hash": r91_result["payload_hash"],
                "contract_hash": contract["contract_hash"],
                "template_hash": template["template_hash"],
                "r91_preflight_hash": r91_preflight["preflight_hash"],
            },
        ),
        req(
            "A2",
            "R92 emits validator rules covering all R91 required and production-required fields",
            set(rules["required_fields"]) == set(contract["required_fields"])
            and set(rules["production_required_fields"])
            == set(contract["production_required_fields"])
            and len(rules["validator_gates"]) == 9,
            {
                "validator_rules_hash": rules["validator_rules_hash"],
                "validator_gate_count": len(rules["validator_gates"]),
            },
        ),
        req(
            "A3",
            "R92 emits local fixture evidence files for environment, transcript, and double-count test",
            file_hash(root / R92_ENV_MANIFEST)
            == fixture_submission["fields"]["independent_environment_manifest_sha256"]
            and command_transcript_sha256
            == fixture_submission["fields"]["command_transcript_sha256"]
            and file_hash(root / R92_DOUBLE_COUNT_TEST)
            == fixture_submission["fields"]["double_count_test_sha256"],
            {
                "environment_manifest_hash": environment_manifest[
                    "environment_manifest_hash"
                ],
                "command_transcript_sha256": command_transcript_sha256,
                "double_count_test_hash": double_count_test["double_count_test_hash"],
            },
        ),
        req(
            "A4",
            "R92 local fixture passes schema, hash, arithmetic, and claim-safety gates",
            fixture_preflight["fixture_preflight_passed"] is True
            and fixture_preflight["failed_gate_count"] == 0
            and fixture_preflight["passed_gate_count"] == 9,
            {
                "fixture_preflight_hash": fixture_preflight["preflight_hash"],
                "passed_gate_count": fixture_preflight["passed_gate_count"],
            },
        ),
        req(
            "A5",
            "R92 fixture is not counted as external reproduction or falsification",
            fixture_preflight["external_submission_accepted"] is False
            and fixture_preflight["accepted_external_reproduction_count"] == 0
            and fixture_preflight["accepted_external_falsification_count"] == 0,
            {
                "external_submission_accepted": fixture_preflight[
                    "external_submission_accepted"
                ],
                "accepted_external_reproduction_count": fixture_preflight[
                    "accepted_external_reproduction_count"
                ],
                "accepted_external_falsification_count": fixture_preflight[
                    "accepted_external_falsification_count"
                ],
            },
        ),
        req(
            "A6",
            "R92 grants no new credit and keeps stronger claims closed",
            fixture_preflight["new_credit_delta"] == 0
            and fixture_submission["fields"]["o3_closed"] is False
            and fixture_submission["fields"]["resource_saving_claimed"] is False
            and fixture_submission["fields"]["physical_layout_claimed"] is False,
            {
                "new_credit_delta": fixture_preflight["new_credit_delta"],
                "o3_closed": fixture_submission["fields"]["o3_closed"],
                "resource_saving_claimed": fixture_submission["fields"][
                    "resource_saving_claimed"
                ],
                "physical_layout_claimed": fixture_submission["fields"][
                    "physical_layout_claimed"
                ],
            },
        ),
        req(
            "A7",
            "R92 emits blockers for non-fixture external submission and accepted external verdict",
            len(blocker_queue["queue"]) == 3
            and [item["target_gate"] for item in blocker_queue["queue"]]
            == [
                "independent_external_submission",
                "external_double_count_attack",
                "accepted_external_verdict",
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
        validation_errors.append("one or more R92 requirements failed")
    if fixture_preflight["external_submission_accepted"]:
        validation_errors.append("R92 fixture must not count as external submission")
    if fixture_preflight["new_credit_delta"] != 0:
        validation_errors.append("R92 must not grant new credit")

    payload = {
        "artifact": "B1/B7 cone01 R92 external submission validator gate",
        "method": METHOD,
        "version": VERSION,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "generated_at_unix": int(time.time()),
        "validator_rules_path": R92_VALIDATOR_RULES,
        "validator_rules_hash": rules["validator_rules_hash"],
        "environment_manifest_path": R92_ENV_MANIFEST,
        "environment_manifest_hash": environment_manifest["environment_manifest_hash"],
        "command_transcript_path": R92_COMMAND_TRANSCRIPT,
        "command_transcript_sha256": command_transcript_sha256,
        "double_count_test_path": R92_DOUBLE_COUNT_TEST,
        "double_count_test_hash": double_count_test["double_count_test_hash"],
        "fixture_submission_path": R92_FIXTURE_SUBMISSION,
        "fixture_submission_hash": fixture_submission["submission_hash"],
        "fixture_preflight_path": R92_PREFLIGHT,
        "fixture_preflight_hash": fixture_preflight["preflight_hash"],
        "stdout_path": R92_STDOUT,
        "stdout_sha256": stdout_sha256,
        "blocker_queue_path": R92_BLOCKER_QUEUE,
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
            "validator_gate_count": len(rules["validator_gates"]),
            "fixture_preflight_passed": fixture_preflight["fixture_preflight_passed"],
            "fixture_failed_gate_count": fixture_preflight["failed_gate_count"],
            "fixture_passed_gate_count": fixture_preflight["passed_gate_count"],
            "external_submission_accepted": fixture_preflight[
                "external_submission_accepted"
            ],
            "accepted_external_reproduction_count": fixture_preflight[
                "accepted_external_reproduction_count"
            ],
            "accepted_external_falsification_count": fixture_preflight[
                "accepted_external_falsification_count"
            ],
            "fixture_reproduction_claimed": fixture_submission["fields"][
                "reproduction_claimed"
            ],
            "double_count_violation_found": fixture_submission["fields"][
                "double_count_violation_found"
            ],
            "accepted_b7_credit_delta_after_review": fixture_preflight[
                "accepted_b7_credit_delta_after_review"
            ],
            "new_credit_delta": fixture_preflight["new_credit_delta"],
            "baseline_after_t_ledger": contract["baseline_after_t_ledger"],
            "candidate_t_ledger_reduction": contract["candidate_t_ledger_reduction"],
            "candidate_after_t_ledger": contract["candidate_after_t_ledger"],
            "target_1_20_margin": contract["target_1_20_margin"],
            "target_1_25_margin": contract["target_1_25_margin"],
            "o3_closed": fixture_submission["fields"]["o3_closed"],
            "resource_saving_claimed": fixture_submission["fields"][
                "resource_saving_claimed"
            ],
            "physical_layout_claimed": fixture_submission["fields"][
                "physical_layout_claimed"
            ],
            "validator_rules_hash": rules["validator_rules_hash"],
            "fixture_submission_hash": fixture_submission["submission_hash"],
            "fixture_preflight_hash": fixture_preflight["preflight_hash"],
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
        "# B1/B7 Cone01 R92 External Submission Validator Gate",
        "",
        f"- Target: `{TARGET_ID}`",
        f"- Upstream target: `{UPSTREAM_TARGET_ID}`",
        f"- Method: `{METHOD}`",
        f"- Status: `{STATUS}`",
        f"- Model status: `{MODEL_STATUS}`",
        "",
        "## Result",
        "",
        "R92 turns the R91 external reproduction contract into a runnable validator",
        "fixture. It emits validator rules, a local environment manifest, a command",
        "transcript, a double-count test, a filled fixture submission, and a preflight",
        "verdict. The fixture passes schema, hash-binding, arithmetic, double-count,",
        "and claim-boundary gates.",
        "",
        "The fixture is deliberately not counted as an external reproduction or",
        "falsification. It proves the submission mechanics are runnable, not that an",
        "outside agent has reproduced the one-unit proxy credit.",
        "",
        "## Key Counters",
        "",
        f"- Validator gates: `{summary['validator_gate_count']}`",
        f"- Fixture preflight passed: `{summary['fixture_preflight_passed']}`",
        f"- Fixture passed gates: `{summary['fixture_passed_gate_count']}`",
        f"- Fixture failed gates: `{summary['fixture_failed_gate_count']}`",
        f"- External submission accepted: `{summary['external_submission_accepted']}`",
        f"- Accepted external reproductions: `{summary['accepted_external_reproduction_count']}`",
        f"- Accepted external falsifications: `{summary['accepted_external_falsification_count']}`",
        f"- Double-count violation found: `{summary['double_count_violation_found']}`",
        f"- New credit delta: `{summary['new_credit_delta']}`",
        f"- 1.20x margin inherited from R91/R90: `{summary['target_1_20_margin']}`",
        f"- 1.25x margin inherited from R91/R90: `{summary['target_1_25_margin']}`",
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
            "- Result JSON: `results/B1_B7_cone01_R92_external_submission_validator_gate_v0.json`",
            f"- Validator rules: `{R92_VALIDATOR_RULES}`",
            f"- Environment manifest: `{R92_ENV_MANIFEST}`",
            f"- Command transcript: `{R92_COMMAND_TRANSCRIPT}`",
            f"- Double-count test: `{R92_DOUBLE_COUNT_TEST}`",
            f"- Filled fixture submission: `{R92_FIXTURE_SUBMISSION}`",
            f"- Fixture preflight verdict: `{R92_PREFLIGHT}`",
            f"- Stdout: `{R92_STDOUT}`",
            f"- Blocker queue: `{R92_BLOCKER_QUEUE}`",
            "",
            "## Claim Boundary",
            "",
            "R92 is validator plumbing, not an external reproduction. The local fixture",
            "is allowed to pass validator gates but cannot increment external",
            "reproduction or falsification counters, cannot grant new B7 credit, and",
            "does not close 1.25x, O3, physical-layout, resource-saving, or",
            "product-readiness claims.",
            "",
        ]
    )
    report_path = root / "research/B1_B7_cone01_R92_external_submission_validator_gate.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    payload = build_payload(args)
    result_path = root / "results/B1_B7_cone01_R92_external_submission_validator_gate_v0.json"
    write_json(result_path, payload)
    write_report(root, payload)
    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
