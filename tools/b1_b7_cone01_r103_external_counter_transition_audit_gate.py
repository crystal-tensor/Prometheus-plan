#!/usr/bin/env python3
"""T-B1-004ha/T-B7-016j: R103 external counter transition audit gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r103_external_counter_transition_audit_gate_v0"
STATUS = "cone01_r103_filled_external_counter_packet_rejected_no_external_origin"
MODEL_STATUS = "r102_contract_ready_but_filled_counter_packet_reuses_local_r101_artifacts"
VERSION = "0.1"
TARGET_ID = "T-B1-004ha/T-B7-016j"
UPSTREAM_TARGET_ID = "T-B1-004gz/T-B7-016i"
SUBMISSION_DIR = "results/B1_B7_cone01_o3_f4_exit_route_submissions"

R102_RESULT = "results/B1_B7_cone01_R102_external_reviewer_identity_contract_gate_v0.json"
R102_CONTRACT = f"{SUBMISSION_DIR}/R102-G1-external-reviewer-identity-contract.json"
R102_TEMPLATE = f"{SUBMISSION_DIR}/R102-G1-external-counter-decision.template.json"
R102_PREFLIGHT = f"{SUBMISSION_DIR}/R102-G1-external-counter-decision-preflight.verdict.json"
R102_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R102-G1-post-external-identity-blocker-queue.json"
R101_MANIFEST = f"{SUBMISSION_DIR}/R101-G1-clean-clone-rerun-manifest.json"
R101_TRANSCRIPT = f"{SUBMISSION_DIR}/R101-G1-clean-clone-rerun-transcript.txt"
R101_COMPARISON = f"{SUBMISSION_DIR}/R101-G1-clean-clone-rerun-comparison.verdict.json"

R103_CLAIMED_DECISION = f"{SUBMISSION_DIR}/R103-G1-claimed-external-counter-decision.json"
R103_AUDIT = f"{SUBMISSION_DIR}/R103-G1-external-counter-transition-audit.verdict.json"
R103_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R103-G1-post-counter-transition-audit-blocker-queue.json"
R103_STDOUT = f"{SUBMISSION_DIR}/R103-G1-external-counter-transition-audit.stdout.txt"

RESULT_PATH = "results/B1_B7_cone01_R103_external_counter_transition_audit_gate_v0.json"
REPORT_PATH = "research/B1_B7_cone01_R103_external_counter_transition_audit_gate.md"


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


def build_claimed_decision(
    contract: dict[str, Any],
    template: dict[str, Any],
    r101_manifest: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    fields = dict(template["fields"])
    fields.update(
        {
            "reviewer_id": "claimed-external-reviewer-r103",
            "reviewer_affiliation_or_agent_context": "unverified_external_claim_reuses_repo_local_artifacts",
            "independence_statement": "claims_independent_but_no_external_origin_attestation",
            "independent_environment_manifest_path": R101_MANIFEST,
            "independent_environment_manifest_sha256": file_hash(root / R101_MANIFEST),
            "clean_checkout_transcript_path": R101_TRANSCRIPT,
            "clean_checkout_transcript_sha256": file_hash(root / R101_TRANSCRIPT),
            "source_r101_comparison_hash": contract["source_r101_comparison_hash"],
            "decision_mode": "external_reproduction_counter_increment",
            "counter_target": "accepted_external_reproduction_count",
            "counter_delta": 1,
            "double_count_decision": "claims_no_duplicate_but_external_origin_unverified",
            "claim_boundary": (
                "This is a filled-looking counter packet that requests one external "
                "reproduction counter increment. It must be rejected unless external "
                "origin and reviewer independence are verified."
            ),
        }
    )
    fields["signature_hash"] = stable_hash(
        {
            "reviewer_id": fields["reviewer_id"],
            "source_r101_comparison_hash": fields["source_r101_comparison_hash"],
            "counter_target": fields["counter_target"],
            "counter_delta": fields["counter_delta"],
            "transcript_sha256": fields["clean_checkout_transcript_sha256"],
        }
    )
    decision = {
        "artifact": "R103 filled-looking claimed external counter decision",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "identity_contract_hash": contract["identity_contract_hash"],
        "decision_template_hash": template["decision_template_hash"],
        "source_r101_manifest_hash": r101_manifest["manifest_hash"],
        "fields": fields,
        "negative_control_reason": (
            "The packet is structurally filled and requests a counter increment, but "
            "it reuses repo-local R101 artifacts and lacks external origin attestation."
        ),
    }
    decision["claimed_decision_hash"] = stable_self_hash(decision, "claimed_decision_hash")
    return decision


def audit_claimed_decision(
    root: Path,
    contract: dict[str, Any],
    template: dict[str, Any],
    decision: dict[str, Any],
    r101_manifest: dict[str, Any],
    r101_comparison: dict[str, Any],
) -> dict[str, Any]:
    fields = decision["fields"]
    missing = [field for field in contract["required_fields"] if fields.get(field) in (None, "")]
    env_path = root / fields["independent_environment_manifest_path"]
    transcript_path = root / fields["clean_checkout_transcript_path"]
    env_hash_ok = env_path.exists() and file_hash(env_path) == fields["independent_environment_manifest_sha256"]
    transcript_hash_ok = (
        transcript_path.exists()
        and file_hash(transcript_path) == fields["clean_checkout_transcript_sha256"]
    )
    env_manifest = load_json(env_path) if env_path.exists() else {}
    transcript_text = transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
    source_hash_ok = fields["source_r101_comparison_hash"] == r101_comparison["comparison_hash"]
    decision_mode_allowed = fields["decision_mode"] in contract["allowed_decision_modes"]
    counter_shape_ok = (
        fields["counter_target"] == "accepted_external_reproduction_count"
        and fields["counter_delta"] == 1
        and fields["decision_mode"] == "external_reproduction_counter_increment"
    )
    local_artifact_reuse_detected = (
        env_manifest.get("clone_was_local") is True
        or "R101 clean-clone rerun transcript" in transcript_text
        or "git clone --local" in transcript_text
    )
    external_origin_attested = (
        "external_origin_attested" in fields["independence_statement"]
        and "unverified" not in fields["reviewer_affiliation_or_agent_context"]
        and not local_artifact_reuse_detected
    )
    gates = {
        "r102_contract_and_template_bound": template["identity_contract_hash"]
        == contract["identity_contract_hash"],
        "all_required_fields_present": not missing,
        "decision_mode_allowed": decision_mode_allowed,
        "source_r101_comparison_hash_matches": source_hash_ok,
        "environment_manifest_file_hash_matches": env_hash_ok,
        "clean_checkout_transcript_file_hash_matches": transcript_hash_ok,
        "counter_increment_shape_is_valid": counter_shape_ok,
        "local_artifact_reuse_detected": local_artifact_reuse_detected,
        "external_origin_attested": external_origin_attested,
        "counter_transition_accepted": False,
    }
    failed = [
        gate
        for gate, passed in gates.items()
        if (gate != "local_artifact_reuse_detected" and not passed)
        or (gate == "local_artifact_reuse_detected" and passed)
    ]
    audit = {
        "artifact": "R103 external counter transition audit verdict",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "identity_contract_hash": contract["identity_contract_hash"],
        "decision_template_hash": template["decision_template_hash"],
        "claimed_decision_hash": decision["claimed_decision_hash"],
        "source_r101_manifest_hash": r101_manifest["manifest_hash"],
        "source_r101_comparison_hash": r101_comparison["comparison_hash"],
        "gates": gates,
        "passed_gate_count": sum(
            1
            for gate, passed in gates.items()
            if (gate != "local_artifact_reuse_detected" and passed)
            or (gate == "local_artifact_reuse_detected" and not passed)
        ),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "claimed_counter_delta": fields["counter_delta"],
        "counter_transition_accepted": False,
        "accepted_external_reproduction_count": 0,
        "accepted_external_falsification_count": 0,
        "counter_delta": 0,
        "new_credit_delta": 0,
        "claimed_external_packet_rejected": True,
        "rejection_reason": "filled_packet_reuses_local_r101_artifacts_without_external_origin_attestation",
        "claim_boundary": (
            "R103 rejects a structurally filled counter-increment packet because it "
            "reuses repo-local R101 artifacts and lacks verified external origin."
        ),
    }
    audit["audit_hash"] = stable_self_hash(audit, "audit_hash")
    return audit


def build_blocker_queue(audit: dict[str, Any]) -> dict[str, Any]:
    queue = {
        "artifact": "R103 post counter transition audit blocker queue",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "audit_hash": audit["audit_hash"],
        "queue": [
            {
                "blocker_id": "R103-G1-1",
                "priority": 1,
                "target_gate": "external_origin_attestation",
                "needed_artifact": "attestation that reviewer, environment, and checkout were produced outside maintainer context",
            },
            {
                "blocker_id": "R103-G1-2",
                "priority": 2,
                "target_gate": "nonlocal_replay_artifacts",
                "needed_artifact": "environment and transcript files not copied from repo-local R101 artifacts",
            },
            {
                "blocker_id": "R103-G1-3",
                "priority": 3,
                "target_gate": "accepted_single_counter_transition",
                "needed_artifact": "audit accepting exactly one reproduction or falsification counter transition",
            },
        ],
    }
    queue["blocker_queue_hash"] = stable_self_hash(queue, "blocker_queue_hash")
    return queue


def write_stdout(root: Path, audit: dict[str, Any], queue: dict[str, Any]) -> str:
    text = "\n".join(
        [
            "R103 external counter transition audit stdout",
            f"method={METHOD}",
            f"source_target_id={TARGET_ID}",
            f"upstream_target_id={UPSTREAM_TARGET_ID}",
            f"audit_hash={audit['audit_hash']}",
            f"blocker_queue_hash={queue['blocker_queue_hash']}",
            f"passed_gate_count={audit['passed_gate_count']}",
            f"failed_gate_count={audit['failed_gate_count']}",
            "claimed_external_packet_rejected=true",
            "counter_transition_accepted=false",
            "accepted_external_reproduction_count=0",
            "accepted_external_falsification_count=0",
            "new_credit_delta=0",
        ]
    ) + "\n"
    path = root / R103_STDOUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    r102_result = load_json(root / R102_RESULT)
    contract = load_json(root / R102_CONTRACT)
    template = load_json(root / R102_TEMPLATE)
    preflight = load_json(root / R102_PREFLIGHT)
    r102_queue = load_json(root / R102_BLOCKER_QUEUE)
    r101_manifest = load_json(root / R101_MANIFEST)
    r101_comparison = load_json(root / R101_COMPARISON)

    decision = build_claimed_decision(contract, template, r101_manifest, root)
    write_json(root / R103_CLAIMED_DECISION, decision)
    audit = audit_claimed_decision(
        root,
        contract,
        template,
        decision,
        r101_manifest,
        r101_comparison,
    )
    write_json(root / R103_AUDIT, audit)
    blocker_queue = build_blocker_queue(audit)
    write_json(root / R103_BLOCKER_QUEUE, blocker_queue)
    stdout_sha256 = write_stdout(root, audit, blocker_queue)

    requirements = [
        req(
            "A1",
            "R103 binds the R102 identity contract, preflight, and blocker queue",
            r102_result["summary"]["source_target_id"] == UPSTREAM_TARGET_ID
            and r102_result["identity_contract_hash"] == contract["identity_contract_hash"]
            and r102_result["preflight_hash"] == preflight["preflight_hash"]
            and r102_result["blocker_queue_hash"] == r102_queue["blocker_queue_hash"],
            {
                "r102_payload_hash": r102_result["payload_hash"],
                "identity_contract_hash": contract["identity_contract_hash"],
                "preflight_hash": preflight["preflight_hash"],
            },
        ),
        req(
            "A2",
            "R103 emits a filled-looking counter-increment packet",
            decision["fields"]["counter_delta"] == 1
            and decision["fields"]["counter_target"] == "accepted_external_reproduction_count"
            and decision["fields"]["decision_mode"] == "external_reproduction_counter_increment",
            {
                "claimed_decision_hash": decision["claimed_decision_hash"],
                "requested_counter_delta": decision["fields"]["counter_delta"],
            },
        ),
        req(
            "A3",
            "R103 detects repo-local R101 artifact reuse and rejects the packet",
            audit["claimed_external_packet_rejected"] is True
            and audit["counter_transition_accepted"] is False
            and "local_artifact_reuse_detected" in audit["failed_gates"]
            and "external_origin_attested" in audit["failed_gates"],
            {"audit_hash": audit["audit_hash"], "failed_gates": audit["failed_gates"]},
        ),
        req(
            "A4",
            "R103 keeps external counters and new credit at zero",
            audit["counter_delta"] == 0
            and audit["accepted_external_reproduction_count"] == 0
            and audit["accepted_external_falsification_count"] == 0
            and audit["new_credit_delta"] == 0,
            {
                "counter_delta": audit["counter_delta"],
                "accepted_external_reproduction_count": audit[
                    "accepted_external_reproduction_count"
                ],
                "accepted_external_falsification_count": audit[
                    "accepted_external_falsification_count"
                ],
                "new_credit_delta": audit["new_credit_delta"],
            },
        ),
        req(
            "A5",
            "R103 emits blockers for external origin, nonlocal replay artifacts, and accepted counter transition",
            [item["target_gate"] for item in blocker_queue["queue"]]
            == [
                "external_origin_attestation",
                "nonlocal_replay_artifacts",
                "accepted_single_counter_transition",
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
        validation_errors.append("one or more R103 requirements failed")
    if audit["counter_transition_accepted"]:
        validation_errors.append("R103 must reject repo-local artifact reuse")

    payload = {
        "artifact": "B1/B7 cone01 R103 external counter transition audit gate",
        "method": METHOD,
        "version": VERSION,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "generated_at_unix": int(time.time()),
        "claimed_decision_path": R103_CLAIMED_DECISION,
        "claimed_decision_hash": decision["claimed_decision_hash"],
        "audit_path": R103_AUDIT,
        "audit_hash": audit["audit_hash"],
        "stdout_path": R103_STDOUT,
        "stdout_sha256": stdout_sha256,
        "blocker_queue_path": R103_BLOCKER_QUEUE,
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
            "claimed_counter_delta": audit["claimed_counter_delta"],
            "claimed_external_packet_rejected": audit["claimed_external_packet_rejected"],
            "counter_transition_accepted": audit["counter_transition_accepted"],
            "passed_gate_count": audit["passed_gate_count"],
            "failed_gate_count": audit["failed_gate_count"],
            "counter_delta": audit["counter_delta"],
            "accepted_external_reproduction_count": audit[
                "accepted_external_reproduction_count"
            ],
            "accepted_external_falsification_count": audit[
                "accepted_external_falsification_count"
            ],
            "new_credit_delta": audit["new_credit_delta"],
            "claimed_decision_hash": decision["claimed_decision_hash"],
            "audit_hash": audit["audit_hash"],
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
        "# B1/B7 Cone01 R103 External Counter Transition Audit Gate",
        "",
        f"- Target: `{TARGET_ID}`",
        f"- Upstream target: `{UPSTREAM_TARGET_ID}`",
        f"- Method: `{METHOD}`",
        f"- Status: `{STATUS}`",
        f"- Model status: `{MODEL_STATUS}`",
        "",
        "## Result",
        "",
        "R103 fills the R102 counter-decision shape with a packet that requests one",
        "external reproduction counter increment, then rejects it because the packet",
        "reuses repo-local R101 artifacts and lacks external-origin attestation.",
        "",
        "## Key Counters",
        "",
        f"- Claimed counter delta: `{summary['claimed_counter_delta']}`",
        f"- Claimed external packet rejected: `{summary['claimed_external_packet_rejected']}`",
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
            f"- Claimed decision: `{R103_CLAIMED_DECISION}`",
            f"- Audit verdict: `{R103_AUDIT}`",
            f"- Blocker queue: `{R103_BLOCKER_QUEUE}`",
            "",
            "## Claim Boundary",
            "",
            "R103 is a negative-control counter-transition audit. It does not move",
            "external reproduction or falsification counters, does not grant new credit,",
            "and does not close B7/O3/resource/layout claims.",
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
