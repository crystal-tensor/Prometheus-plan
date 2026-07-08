#!/usr/bin/env python3
"""T-B1-004gz/T-B7-016i: R102 external reviewer identity contract gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r102_external_reviewer_identity_contract_gate_v0"
STATUS = "cone01_r102_external_reviewer_identity_contract_ready_no_counter_move"
MODEL_STATUS = "r101_clean_rerun_ready_but_independent_external_identity_missing"
VERSION = "0.1"
TARGET_ID = "T-B1-004gz/T-B7-016i"
UPSTREAM_TARGET_ID = "T-B1-004gy/T-B7-016h"
SUBMISSION_DIR = "results/B1_B7_cone01_o3_f4_exit_route_submissions"

R101_RESULT = "results/B1_B7_cone01_R101_clean_clone_rerun_gate_v0.json"
R101_MANIFEST = f"{SUBMISSION_DIR}/R101-G1-clean-clone-rerun-manifest.json"
R101_COMPARISON = f"{SUBMISSION_DIR}/R101-G1-clean-clone-rerun-comparison.verdict.json"
R101_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R101-G1-post-clean-rerun-blocker-queue.json"

R102_IDENTITY_CONTRACT = f"{SUBMISSION_DIR}/R102-G1-external-reviewer-identity-contract.json"
R102_DECISION_TEMPLATE = f"{SUBMISSION_DIR}/R102-G1-external-counter-decision.template.json"
R102_SURROGATE_DECISION = f"{SUBMISSION_DIR}/R102-G1-local-surrogate-counter-decision.json"
R102_PREFLIGHT = f"{SUBMISSION_DIR}/R102-G1-external-counter-decision-preflight.verdict.json"
R102_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R102-G1-post-external-identity-blocker-queue.json"
R102_STDOUT = f"{SUBMISSION_DIR}/R102-G1-external-reviewer-identity.stdout.txt"

RESULT_PATH = "results/B1_B7_cone01_R102_external_reviewer_identity_contract_gate_v0.json"
REPORT_PATH = "research/B1_B7_cone01_R102_external_reviewer_identity_contract_gate.md"

IDENTITY_REQUIRED_FIELDS = [
    "reviewer_id",
    "reviewer_affiliation_or_agent_context",
    "independence_statement",
    "independent_environment_manifest_path",
    "independent_environment_manifest_sha256",
    "clean_checkout_transcript_path",
    "clean_checkout_transcript_sha256",
    "source_r101_comparison_hash",
    "decision_mode",
    "counter_target",
    "counter_delta",
    "double_count_decision",
    "claim_boundary",
    "signature_hash",
]

ALLOWED_DECISION_MODES = [
    "external_reproduction_counter_increment",
    "external_falsification_counter_increment",
    "insufficient_independence_no_counter",
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


def build_identity_contract(r101_result: dict[str, Any], r101_comparison: dict[str, Any]) -> dict[str, Any]:
    contract = {
        "artifact": "R102 external reviewer identity and counter-decision contract",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_r101_payload_hash": r101_result["payload_hash"],
        "source_r101_comparison_hash": r101_comparison["comparison_hash"],
        "required_fields": IDENTITY_REQUIRED_FIELDS,
        "required_field_count": len(IDENTITY_REQUIRED_FIELDS),
        "allowed_decision_modes": ALLOWED_DECISION_MODES,
        "allowed_counter_targets": [
            "accepted_external_reproduction_count",
            "accepted_external_falsification_count",
            "no_counter_change",
        ],
        "counter_transition_rules": {
            "accepted_external_reproduction_count": {
                "allowed_delta": [1],
                "requires": [
                    "independent_reviewer_identity",
                    "independent_clean_checkout_transcript",
                    "same_stable_hashes_reproduced",
                    "double_count_decision_no_duplicate",
                    "claim_boundary_safe",
                ],
            },
            "accepted_external_falsification_count": {
                "allowed_delta": [1],
                "requires": [
                    "independent_reviewer_identity",
                    "independent_clean_checkout_transcript",
                    "explicit_falsification_reason",
                    "double_count_decision_no_duplicate",
                    "claim_boundary_safe",
                ],
            },
            "no_counter_change": {
                "allowed_delta": [0],
                "requires": ["explicit_no_counter_reason"],
            },
        },
        "forbidden_direct_claims": [
            "new_b7_credit",
            "1_25x_closure",
            "o3_closure",
            "physical_layout_claim",
            "resource_saving_claim",
        ],
        "pre_r102_external_reproduction_count": 0,
        "pre_r102_external_falsification_count": 0,
        "pre_r102_new_credit_delta": 0,
    }
    contract["identity_contract_hash"] = stable_self_hash(contract, "identity_contract_hash")
    return contract


def build_decision_template(contract: dict[str, Any]) -> dict[str, Any]:
    template = {
        "artifact": "R102 external counter-decision template",
        "identity_contract_hash": contract["identity_contract_hash"],
        "fields": {field: None for field in contract["required_fields"]},
        "allowed_decision_modes": contract["allowed_decision_modes"],
        "allowed_counter_targets": contract["allowed_counter_targets"],
        "instructions": [
            "Use an environment and checkout transcript produced outside the maintainer agent.",
            "Bind the R101 comparison hash before any counter transition.",
            "Move exactly one external counter only when independence and replay evidence are both present.",
            "Do not use this gate for new B7 credit, 1.25x closure, O3 closure, layout, or resource-saving claims.",
        ],
    }
    template["decision_template_hash"] = stable_self_hash(template, "decision_template_hash")
    return template


def build_surrogate_decision(contract: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "reviewer_id": "codex-r102-local-surrogate-reviewer",
        "reviewer_affiliation_or_agent_context": "same-maintainer-agent-local-context",
        "independence_statement": "not_independent_same_agent_negative_control",
        "independent_environment_manifest_path": None,
        "independent_environment_manifest_sha256": None,
        "clean_checkout_transcript_path": None,
        "clean_checkout_transcript_sha256": None,
        "source_r101_comparison_hash": contract["source_r101_comparison_hash"],
        "decision_mode": "insufficient_independence_no_counter",
        "counter_target": "no_counter_change",
        "counter_delta": 0,
        "double_count_decision": "no_external_counter_to_double_count",
        "claim_boundary": (
            "Local surrogate reviewer is intentionally not independent. This decision "
            "tests the contract and must not move external counters or strong claims."
        ),
        "signature_hash": stable_hash(
            {
                "reviewer_id": "codex-r102-local-surrogate-reviewer",
                "source_r101_comparison_hash": contract["source_r101_comparison_hash"],
                "counter_delta": 0,
            }
        ),
    }
    decision = {
        "artifact": "R102 local surrogate external counter decision negative control",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "identity_contract_hash": contract["identity_contract_hash"],
        "fields": fields,
    }
    decision["surrogate_decision_hash"] = stable_self_hash(
        decision, "surrogate_decision_hash"
    )
    return decision


def validate_surrogate_decision(
    contract: dict[str, Any],
    decision: dict[str, Any],
    r101_result: dict[str, Any],
    r101_comparison: dict[str, Any],
) -> dict[str, Any]:
    fields = decision["fields"]
    missing = [field for field in contract["required_fields"] if fields.get(field) in (None, "")]
    independence_ok = (
        fields["reviewer_id"] != "codex-r102-local-surrogate-reviewer"
        and "not_independent" not in fields["independence_statement"]
    )
    replay_artifacts_present = (
        fields.get("independent_environment_manifest_path") is not None
        and fields.get("clean_checkout_transcript_path") is not None
    )
    decision_mode_allowed = fields["decision_mode"] in contract["allowed_decision_modes"]
    safe_counter = fields["counter_target"] == "no_counter_change" and fields["counter_delta"] == 0
    source_hash_ok = (
        fields["source_r101_comparison_hash"] == r101_comparison["comparison_hash"]
        == r101_result["comparison_hash"]
    )
    gates = {
        "r101_clean_clone_rerun_reproduced": r101_result["summary"][
            "clean_clone_rerun_reproduced"
        ]
        is True,
        "source_r101_comparison_hash_matches": source_hash_ok,
        "decision_mode_allowed": decision_mode_allowed,
        "required_independence_fields_complete": not missing,
        "reviewer_identity_independent": independence_ok,
        "independent_replay_artifacts_present": replay_artifacts_present,
        "safe_no_counter_decision": safe_counter,
        "claim_boundary_safe": "strong claims" in fields["claim_boundary"]
        and fields["counter_delta"] == 0,
    }
    failed = [gate for gate, passed in gates.items() if not passed]
    preflight = {
        "artifact": "R102 external counter-decision preflight verdict",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "identity_contract_hash": contract["identity_contract_hash"],
        "surrogate_decision_hash": decision["surrogate_decision_hash"],
        "gates": gates,
        "passed_gate_count": sum(1 for passed in gates.values() if passed),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "missing_required_fields": missing,
        "surrogate_decision_rejected": True,
        "external_reviewer_identity_accepted": False,
        "counter_transition_accepted": False,
        "accepted_external_reproduction_count": 0,
        "accepted_external_falsification_count": 0,
        "counter_delta": 0,
        "new_credit_delta": 0,
        "claim_boundary": (
            "R102 defines the external reviewer identity contract and rejects the local "
            "surrogate negative control. It does not move external counters."
        ),
    }
    preflight["preflight_hash"] = stable_self_hash(preflight, "preflight_hash")
    return preflight


def build_blocker_queue(preflight: dict[str, Any]) -> dict[str, Any]:
    queue = {
        "artifact": "R102 post external identity blocker queue",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "preflight_hash": preflight["preflight_hash"],
        "queue": [
            {
                "blocker_id": "R102-G1-1",
                "priority": 1,
                "target_gate": "real_independent_reviewer_identity",
                "needed_artifact": "reviewer identity and independence statement outside maintainer context",
            },
            {
                "blocker_id": "R102-G1-2",
                "priority": 2,
                "target_gate": "independent_environment_and_checkout_transcript",
                "needed_artifact": "environment manifest and clean checkout rerun transcript with hashes",
            },
            {
                "blocker_id": "R102-G1-3",
                "priority": 3,
                "target_gate": "single_counter_transition_audit",
                "needed_artifact": "audit that moves exactly one external counter and no strong claim",
            },
        ],
    }
    queue["blocker_queue_hash"] = stable_self_hash(queue, "blocker_queue_hash")
    return queue


def write_stdout(root: Path, preflight: dict[str, Any], queue: dict[str, Any]) -> str:
    text = "\n".join(
        [
            "R102 external reviewer identity contract stdout",
            f"method={METHOD}",
            f"source_target_id={TARGET_ID}",
            f"upstream_target_id={UPSTREAM_TARGET_ID}",
            f"preflight_hash={preflight['preflight_hash']}",
            f"blocker_queue_hash={queue['blocker_queue_hash']}",
            f"passed_gate_count={preflight['passed_gate_count']}",
            f"failed_gate_count={preflight['failed_gate_count']}",
            "surrogate_decision_rejected=true",
            "external_reviewer_identity_accepted=false",
            "counter_transition_accepted=false",
            "accepted_external_reproduction_count=0",
            "accepted_external_falsification_count=0",
            "new_credit_delta=0",
        ]
    ) + "\n"
    path = root / R102_STDOUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    r101_result = load_json(root / R101_RESULT)
    r101_manifest = load_json(root / R101_MANIFEST)
    r101_comparison = load_json(root / R101_COMPARISON)
    r101_queue = load_json(root / R101_BLOCKER_QUEUE)

    contract = build_identity_contract(r101_result, r101_comparison)
    write_json(root / R102_IDENTITY_CONTRACT, contract)
    template = build_decision_template(contract)
    write_json(root / R102_DECISION_TEMPLATE, template)
    surrogate = build_surrogate_decision(contract)
    write_json(root / R102_SURROGATE_DECISION, surrogate)
    preflight = validate_surrogate_decision(contract, surrogate, r101_result, r101_comparison)
    write_json(root / R102_PREFLIGHT, preflight)
    blocker_queue = build_blocker_queue(preflight)
    write_json(root / R102_BLOCKER_QUEUE, blocker_queue)
    stdout_sha256 = write_stdout(root, preflight, blocker_queue)

    requirements = [
        req(
            "A1",
            "R102 binds the accepted R101 clean-clone rerun and blocker queue",
            r101_result["summary"]["source_target_id"] == UPSTREAM_TARGET_ID
            and r101_result["manifest_hash"] == r101_manifest["manifest_hash"]
            and r101_result["comparison_hash"] == r101_comparison["comparison_hash"]
            and r101_result["blocker_queue_hash"] == r101_queue["blocker_queue_hash"],
            {
                "r101_payload_hash": r101_result["payload_hash"],
                "r101_comparison_hash": r101_comparison["comparison_hash"],
            },
        ),
        req(
            "A2",
            "R102 emits an external reviewer identity contract and decision template",
            contract["required_field_count"] == len(IDENTITY_REQUIRED_FIELDS)
            and template["identity_contract_hash"] == contract["identity_contract_hash"],
            {
                "identity_contract_hash": contract["identity_contract_hash"],
                "decision_template_hash": template["decision_template_hash"],
            },
        ),
        req(
            "A3",
            "R102 rejects the local surrogate reviewer as not independent",
            preflight["surrogate_decision_rejected"] is True
            and preflight["external_reviewer_identity_accepted"] is False
            and "reviewer_identity_independent" in preflight["failed_gates"],
            {
                "preflight_hash": preflight["preflight_hash"],
                "failed_gates": preflight["failed_gates"],
            },
        ),
        req(
            "A4",
            "R102 keeps external counters and new credit at zero",
            preflight["counter_delta"] == 0
            and preflight["accepted_external_reproduction_count"] == 0
            and preflight["accepted_external_falsification_count"] == 0
            and preflight["new_credit_delta"] == 0,
            {
                "counter_delta": preflight["counter_delta"],
                "accepted_external_reproduction_count": preflight[
                    "accepted_external_reproduction_count"
                ],
                "accepted_external_falsification_count": preflight[
                    "accepted_external_falsification_count"
                ],
                "new_credit_delta": preflight["new_credit_delta"],
            },
        ),
        req(
            "A5",
            "R102 emits blockers for real identity, independent transcript, and single-counter audit",
            [item["target_gate"] for item in blocker_queue["queue"]]
            == [
                "real_independent_reviewer_identity",
                "independent_environment_and_checkout_transcript",
                "single_counter_transition_audit",
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
        validation_errors.append("one or more R102 requirements failed")
    if preflight["counter_transition_accepted"]:
        validation_errors.append("R102 must not accept the local surrogate counter transition")

    payload = {
        "artifact": "B1/B7 cone01 R102 external reviewer identity contract gate",
        "method": METHOD,
        "version": VERSION,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "generated_at_unix": int(time.time()),
        "identity_contract_path": R102_IDENTITY_CONTRACT,
        "identity_contract_hash": contract["identity_contract_hash"],
        "decision_template_path": R102_DECISION_TEMPLATE,
        "decision_template_hash": template["decision_template_hash"],
        "surrogate_decision_path": R102_SURROGATE_DECISION,
        "surrogate_decision_hash": surrogate["surrogate_decision_hash"],
        "preflight_path": R102_PREFLIGHT,
        "preflight_hash": preflight["preflight_hash"],
        "stdout_path": R102_STDOUT,
        "stdout_sha256": stdout_sha256,
        "blocker_queue_path": R102_BLOCKER_QUEUE,
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
            "identity_contract_hash": contract["identity_contract_hash"],
            "decision_template_hash": template["decision_template_hash"],
            "surrogate_decision_rejected": preflight["surrogate_decision_rejected"],
            "external_reviewer_identity_accepted": preflight[
                "external_reviewer_identity_accepted"
            ],
            "counter_transition_accepted": preflight["counter_transition_accepted"],
            "passed_gate_count": preflight["passed_gate_count"],
            "failed_gate_count": preflight["failed_gate_count"],
            "counter_delta": preflight["counter_delta"],
            "accepted_external_reproduction_count": preflight[
                "accepted_external_reproduction_count"
            ],
            "accepted_external_falsification_count": preflight[
                "accepted_external_falsification_count"
            ],
            "new_credit_delta": preflight["new_credit_delta"],
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
        "# B1/B7 Cone01 R102 External Reviewer Identity Contract Gate",
        "",
        f"- Target: `{TARGET_ID}`",
        f"- Upstream target: `{UPSTREAM_TARGET_ID}`",
        f"- Method: `{METHOD}`",
        f"- Status: `{STATUS}`",
        f"- Model status: `{MODEL_STATUS}`",
        "",
        "## Result",
        "",
        "R102 turns the R101 clean-clone rerun blocker into a concrete external",
        "reviewer identity and counter-decision contract. It also emits a local",
        "surrogate decision as a negative control and rejects it because the reviewer",
        "is not independent and no independent replay artifacts are attached.",
        "",
        "## Key Counters",
        "",
        f"- Surrogate decision rejected: `{summary['surrogate_decision_rejected']}`",
        f"- External reviewer identity accepted: `{summary['external_reviewer_identity_accepted']}`",
        f"- Counter transition accepted: `{summary['counter_transition_accepted']}`",
        f"- Gates passed / failed: `{summary['passed_gate_count']}` / `{summary['failed_gate_count']}`",
        f"- Counter delta: `{summary['counter_delta']}`",
        f"- Accepted external reproductions: `{summary['accepted_external_reproduction_count']}`",
        f"- Accepted external falsifications: `{summary['accepted_external_falsification_count']}`",
        f"- New credit delta: `{summary['new_credit_delta']}`",
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
            f"- Result JSON: `{RESULT_PATH}`",
            f"- Identity contract: `{R102_IDENTITY_CONTRACT}`",
            f"- Decision template: `{R102_DECISION_TEMPLATE}`",
            f"- Surrogate decision: `{R102_SURROGATE_DECISION}`",
            f"- Preflight: `{R102_PREFLIGHT}`",
            f"- Blocker queue: `{R102_BLOCKER_QUEUE}`",
            "",
            "## Claim Boundary",
            "",
            "R102 is a contract and negative-control gate. It does not accept an external",
            "reviewer identity yet, does not move reproduction or falsification counters,",
            "does not grant new credit, and does not close B7/O3/resource/layout claims.",
            "",
        ]
    )
    (root / REPORT_PATH).write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    payload = build_payload(args)
    write_json(root / RESULT_PATH, payload)
    write_report(root, payload)
    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
