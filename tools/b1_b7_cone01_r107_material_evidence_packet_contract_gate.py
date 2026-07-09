#!/usr/bin/env python3
"""T-B1-004he/T-B7-016n: R107 material evidence packet contract gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r107_material_evidence_packet_contract_gate_v0"
STATUS = "cone01_r107_material_evidence_packet_contract_ready_no_external_counter"
MODEL_STATUS = "r106_materiality_blockers_converted_to_fillable_external_evidence_packet"
VERSION = "0.1"
TARGET_ID = "T-B1-004he/T-B7-016n"
UPSTREAM_TARGET_ID = "T-B1-004hd/T-B7-016m"
SUBMISSION_DIR = "results/B1_B7_cone01_o3_f4_exit_route_submissions"
R107_DIR = f"{SUBMISSION_DIR}/R107-G1-external-material-evidence-packet-contract"

R106_RESULT = "results/B1_B7_cone01_R106_remote_origin_materiality_gate_v0.json"
R106_MATERIALITY_AUDIT = (
    f"{SUBMISSION_DIR}/R106-G1-remote-looking-origin-spoof/"
    "remote-origin-materiality-audit.verdict.json"
)
R106_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R106-G1-post-remote-origin-materiality-blocker-queue.json"
R106_REMOTE_LOOKING_PACKET = (
    f"{SUBMISSION_DIR}/R106-G1-remote-looking-origin-spoof/remote-looking-origin-packet.json"
)

R107_CONTRACT = f"{R107_DIR}/external-material-evidence-packet-contract.json"
R107_TEMPLATE = f"{R107_DIR}/external-material-evidence-packet.template.json"
R107_SELF_DECLARED_PACKET = f"{R107_DIR}/self-declared-materiality-negative-control.json"
R107_EMPTY_PREFLIGHT = f"{R107_DIR}/empty-template-preflight.verdict.json"
R107_SELF_DECLARED_PREFLIGHT = f"{R107_DIR}/self-declared-packet-preflight.verdict.json"
R107_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R107-G1-post-material-evidence-contract-blocker-queue.json"
R107_STDOUT = f"{SUBMISSION_DIR}/R107-G1-material-evidence-contract.stdout.txt"

RESULT_PATH = "results/B1_B7_cone01_R107_material_evidence_packet_contract_gate_v0.json"
REPORT_PATH = "research/B1_B7_cone01_R107_material_evidence_packet_contract_gate.md"


REQUIRED_FIELDS = [
    "reviewer_id",
    "reviewer_public_contact_or_handle",
    "reviewer_key_registry_path",
    "reviewer_key_registry_sha256",
    "reviewer_key_fingerprint",
    "reviewer_identity_verification_path",
    "reviewer_identity_verification_sha256",
    "signed_payload_path",
    "signed_payload_sha256",
    "detached_signature_path",
    "detached_signature_sha256",
    "signature_verification_transcript_path",
    "signature_verification_transcript_sha256",
    "third_party_ci_run_url",
    "third_party_ci_provider",
    "third_party_ci_commit_sha",
    "third_party_ci_log_path",
    "third_party_ci_log_sha256",
    "remote_artifact_fetch_transcript_path",
    "remote_artifact_fetch_transcript_sha256",
    "fetched_artifact_manifest_path",
    "fetched_artifact_manifest_sha256",
    "environment_manifest_path",
    "environment_manifest_sha256",
    "reviewer_contact_verification_path",
    "reviewer_contact_verification_sha256",
    "r106_materiality_audit_hash",
    "requested_counter_transition",
    "double_count_prevention_statement",
    "claim_boundary",
]

ACCEPTANCE_GATES = [
    "contract_hash_matches",
    "required_fields_present",
    "required_fields_nonempty",
    "reviewer_key_registry_file_hash_matches",
    "reviewer_key_fingerprint_format",
    "reviewer_identity_verification_file_hash_matches",
    "signed_payload_file_hash_matches",
    "detached_signature_file_hash_matches",
    "signature_verification_transcript_file_hash_matches",
    "signature_verification_transcript_says_valid",
    "third_party_ci_run_url_public_https",
    "third_party_ci_commit_sha_format",
    "third_party_ci_log_file_hash_matches",
    "remote_artifact_fetch_transcript_file_hash_matches",
    "remote_artifact_fetch_transcript_says_fetched_from_github",
    "fetched_artifact_manifest_file_hash_matches",
    "environment_manifest_file_hash_matches",
    "reviewer_contact_verification_file_hash_matches",
    "r106_materiality_audit_hash_matches",
    "counter_transition_mode_allowed",
    "claim_boundary_present",
    "not_self_attestation_only",
]

HASH_FIELDS = {
    "reviewer_key_registry_path": "reviewer_key_registry_sha256",
    "reviewer_identity_verification_path": "reviewer_identity_verification_sha256",
    "signed_payload_path": "signed_payload_sha256",
    "detached_signature_path": "detached_signature_sha256",
    "signature_verification_transcript_path": "signature_verification_transcript_sha256",
    "third_party_ci_log_path": "third_party_ci_log_sha256",
    "remote_artifact_fetch_transcript_path": "remote_artifact_fetch_transcript_sha256",
    "fetched_artifact_manifest_path": "fetched_artifact_manifest_sha256",
    "environment_manifest_path": "environment_manifest_sha256",
    "reviewer_contact_verification_path": "reviewer_contact_verification_sha256",
}

ACCEPTED_COUNTER_TRANSITIONS = [
    "external_reproduction_counter_increment",
    "external_falsification_counter_increment",
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


def build_contract(root: Path, r106_result: dict[str, Any]) -> dict[str, Any]:
    materiality_hash = r106_result["summary"]["materiality_audit_hash"]
    blocker_hash = r106_result["summary"]["blocker_queue_hash"]
    contract = {
        "artifact": "R107 external material evidence packet contract",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_r106_result": R106_RESULT,
        "source_r106_materiality_audit": R106_MATERIALITY_AUDIT,
        "source_r106_blocker_queue": R106_BLOCKER_QUEUE,
        "source_r106_materiality_audit_hash": materiality_hash,
        "source_r106_blocker_queue_hash": blocker_hash,
        "required_fields": REQUIRED_FIELDS,
        "required_hash_bindings": HASH_FIELDS,
        "acceptance_gates": ACCEPTANCE_GATES,
        "accepted_counter_transition_modes": ACCEPTED_COUNTER_TRANSITIONS,
        "forbidden_claims_without_separate_counter_audit": [
            "B7 resource savings",
            "O3 closure",
            "physical-layout relevance",
            "1.25x target satisfaction",
            "general external reproduction count movement",
        ],
        "claim_boundary": (
            "R107 defines the material evidence packet required after R106. "
            "It does not accept an external counter by itself."
        ),
    }
    contract["contract_hash"] = stable_self_hash(contract, "contract_hash")
    write_json(root / R107_CONTRACT, contract)
    return contract


def build_template(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    fields = {field: "" for field in REQUIRED_FIELDS}
    fields["r106_materiality_audit_hash"] = contract["source_r106_materiality_audit_hash"]
    fields["requested_counter_transition"] = ""
    fields["claim_boundary"] = (
        "Fill with the exact claim boundary. This packet may only request one "
        "external reproduction or falsification counter transition."
    )
    template = {
        "artifact": "R107 external material evidence packet template",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "fields": fields,
        "template_status": "fillable_not_accepted",
    }
    template["template_hash"] = stable_self_hash(template, "template_hash")
    write_json(root / R107_TEMPLATE, template)
    return template


def build_self_declared_packet(root: Path, contract: dict[str, Any], r106_packet: dict[str, Any]) -> dict[str, Any]:
    fields = {field: "" for field in REQUIRED_FIELDS}
    fields.update(
        {
            "reviewer_id": "self-declared-r107-reviewer",
            "reviewer_public_contact_or_handle": "https://github.com/claimed-r106-reviewer",
            "reviewer_key_registry_path": R106_REMOTE_LOOKING_PACKET,
            "reviewer_key_registry_sha256": file_hash(root / R106_REMOTE_LOOKING_PACKET),
            "reviewer_key_fingerprint": "self-declared-no-public-key",
            "reviewer_identity_verification_path": R106_REMOTE_LOOKING_PACKET,
            "reviewer_identity_verification_sha256": file_hash(root / R106_REMOTE_LOOKING_PACKET),
            "signed_payload_path": R106_REMOTE_LOOKING_PACKET,
            "signed_payload_sha256": file_hash(root / R106_REMOTE_LOOKING_PACKET),
            "detached_signature_path": R106_REMOTE_LOOKING_PACKET,
            "detached_signature_sha256": file_hash(root / R106_REMOTE_LOOKING_PACKET),
            "signature_verification_transcript_path": R106_REMOTE_LOOKING_PACKET,
            "signature_verification_transcript_sha256": file_hash(root / R106_REMOTE_LOOKING_PACKET),
            "third_party_ci_run_url": "https://github.com/crystal-tensor/Prometheus-plan/actions/runs/self-declared-r107",
            "third_party_ci_provider": "self_declared_github_actions",
            "third_party_ci_commit_sha": r106_packet["fields"]["repository_source_commit_sha"],
            "third_party_ci_log_path": R106_REMOTE_LOOKING_PACKET,
            "third_party_ci_log_sha256": file_hash(root / R106_REMOTE_LOOKING_PACKET),
            "remote_artifact_fetch_transcript_path": R106_REMOTE_LOOKING_PACKET,
            "remote_artifact_fetch_transcript_sha256": file_hash(root / R106_REMOTE_LOOKING_PACKET),
            "fetched_artifact_manifest_path": R106_REMOTE_LOOKING_PACKET,
            "fetched_artifact_manifest_sha256": file_hash(root / R106_REMOTE_LOOKING_PACKET),
            "environment_manifest_path": R106_REMOTE_LOOKING_PACKET,
            "environment_manifest_sha256": file_hash(root / R106_REMOTE_LOOKING_PACKET),
            "reviewer_contact_verification_path": R106_REMOTE_LOOKING_PACKET,
            "reviewer_contact_verification_sha256": file_hash(root / R106_REMOTE_LOOKING_PACKET),
            "r106_materiality_audit_hash": contract["source_r106_materiality_audit_hash"],
            "requested_counter_transition": "external_reproduction_counter_increment",
            "double_count_prevention_statement": "self-declared-no-duplicate",
            "claim_boundary": "self-declared packet reused from R106 negative control",
        }
    )
    packet = {
        "artifact": "R107 self-declared materiality negative control",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "fields": fields,
        "negative_control_reason": (
            "This packet reuses the R106 remote-looking packet for every material "
            "artifact slot. It should fail the material evidence preflight."
        ),
    }
    packet["self_declared_packet_hash"] = stable_self_hash(packet, "self_declared_packet_hash")
    write_json(root / R107_SELF_DECLARED_PACKET, packet)
    return packet


def hash_matches(root: Path, fields: dict[str, Any], path_field: str) -> bool:
    path_value = fields.get(path_field)
    hash_field = HASH_FIELDS[path_field]
    expected_hash = fields.get(hash_field)
    if not path_value or not expected_hash:
        return False
    path = root / path_value
    return path.is_file() and expected_hash == file_hash(path)


def read_text_if_exists(root: Path, path_value: str) -> str:
    path = root / path_value
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def validate_packet(root: Path, packet: dict[str, Any], contract: dict[str, Any], label: str) -> dict[str, Any]:
    fields = packet.get("fields", {})
    signature_text = read_text_if_exists(root, fields.get("signature_verification_transcript_path", ""))
    fetch_text = read_text_if_exists(root, fields.get("remote_artifact_fetch_transcript_path", ""))
    self_attestation_markers = ["self-declared", "self_declared", "negative control", "remote-looking"]
    serialized_fields = json.dumps(fields, sort_keys=True)
    gates = {
        "contract_hash_matches": packet.get("contract_hash") == contract["contract_hash"],
        "required_fields_present": all(field in fields for field in contract["required_fields"]),
        "required_fields_nonempty": all(fields.get(field) not in (None, "") for field in contract["required_fields"]),
        "reviewer_key_registry_file_hash_matches": hash_matches(root, fields, "reviewer_key_registry_path"),
        "reviewer_key_fingerprint_format": bool(
            re.fullmatch(r"(SHA256:)?[A-Fa-f0-9:]{32,95}", str(fields.get("reviewer_key_fingerprint", "")))
        ),
        "reviewer_identity_verification_file_hash_matches": hash_matches(root, fields, "reviewer_identity_verification_path"),
        "signed_payload_file_hash_matches": hash_matches(root, fields, "signed_payload_path"),
        "detached_signature_file_hash_matches": hash_matches(root, fields, "detached_signature_path"),
        "signature_verification_transcript_file_hash_matches": hash_matches(root, fields, "signature_verification_transcript_path"),
        "signature_verification_transcript_says_valid": "signature_valid=true" in signature_text,
        "third_party_ci_run_url_public_https": str(fields.get("third_party_ci_run_url", "")).startswith("https://")
        and "/actions/runs/" in str(fields.get("third_party_ci_run_url", "")),
        "third_party_ci_commit_sha_format": bool(
            re.fullmatch(r"[0-9a-f]{40}", str(fields.get("third_party_ci_commit_sha", "")))
        ),
        "third_party_ci_log_file_hash_matches": hash_matches(root, fields, "third_party_ci_log_path"),
        "remote_artifact_fetch_transcript_file_hash_matches": hash_matches(
            root, fields, "remote_artifact_fetch_transcript_path"
        ),
        "remote_artifact_fetch_transcript_says_fetched_from_github": "fetched_from=https://github.com/" in fetch_text,
        "fetched_artifact_manifest_file_hash_matches": hash_matches(root, fields, "fetched_artifact_manifest_path"),
        "environment_manifest_file_hash_matches": hash_matches(root, fields, "environment_manifest_path"),
        "reviewer_contact_verification_file_hash_matches": hash_matches(root, fields, "reviewer_contact_verification_path"),
        "r106_materiality_audit_hash_matches": fields.get("r106_materiality_audit_hash")
        == contract["source_r106_materiality_audit_hash"],
        "counter_transition_mode_allowed": fields.get("requested_counter_transition")
        in contract["accepted_counter_transition_modes"],
        "claim_boundary_present": fields.get("claim_boundary") not in (None, ""),
        "not_self_attestation_only": not any(marker in serialized_fields for marker in self_attestation_markers),
    }
    gates["material_evidence_packet_accepted"] = all(gates.values())
    failed = [gate for gate, passed in gates.items() if not passed]
    verdict = {
        "artifact": f"R107 material evidence preflight verdict: {label}",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "packet_label": label,
        "gates": gates,
        "passed_gate_count": sum(1 for passed in gates.values() if passed),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "material_evidence_packet_accepted": gates["material_evidence_packet_accepted"],
        "claim_boundary": (
            "Preflight acceptance would only make the packet eligible for a separate "
            "single-counter audit. R107 itself moves no counters."
        ),
    }
    verdict["preflight_hash"] = stable_self_hash(verdict, "preflight_hash")
    return verdict


def build_blocker_queue(
    root: Path,
    contract: dict[str, Any],
    empty_preflight: dict[str, Any],
    self_preflight: dict[str, Any],
) -> dict[str, Any]:
    blockers = [
        {
            "blocker_id": "R107-G1-1",
            "label": "Submit a public reviewer-key registry artifact and fingerprint.",
            "required_artifacts": ["reviewer_key_registry_path", "reviewer_key_fingerprint"],
        },
        {
            "blocker_id": "R107-G1-2",
            "label": "Submit detached signature plus verification transcript with signature_valid=true.",
            "required_artifacts": [
                "signed_payload_path",
                "detached_signature_path",
                "signature_verification_transcript_path",
            ],
        },
        {
            "blocker_id": "R107-G1-3",
            "label": "Submit public third-party CI run and log artifact bound to a 40-char commit.",
            "required_artifacts": ["third_party_ci_run_url", "third_party_ci_commit_sha", "third_party_ci_log_path"],
        },
        {
            "blocker_id": "R107-G1-4",
            "label": "Submit remote artifact-fetch transcript and fetched artifact manifest.",
            "required_artifacts": ["remote_artifact_fetch_transcript_path", "fetched_artifact_manifest_path"],
        },
        {
            "blocker_id": "R107-G1-5",
            "label": "Submit reviewer contact verification and only then run a separate single-counter audit.",
            "required_artifacts": ["reviewer_contact_verification_path"],
        },
    ]
    queue = {
        "artifact": "R107 post-material-evidence-contract blocker queue",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "empty_template_preflight_hash": empty_preflight["preflight_hash"],
        "self_declared_preflight_hash": self_preflight["preflight_hash"],
        "counter_transition_accepted": False,
        "counter_delta": 0,
        "accepted_external_reproduction_count": 0,
        "accepted_external_falsification_count": 0,
        "new_credit_delta": 0,
        "blockers": blockers,
    }
    queue["blocker_queue_hash"] = stable_self_hash(queue, "blocker_queue_hash")
    write_json(root / R107_BLOCKER_QUEUE, queue)
    return queue


def build_report(result: dict[str, Any]) -> str:
    s = result["summary"]
    lines = [
        "# B1/B7 Cone01 R107 Material Evidence Packet Contract Gate",
        "",
        f"- Target: `{TARGET_ID}`",
        f"- Upstream target: `{UPSTREAM_TARGET_ID}`",
        f"- Method: `{METHOD}`",
        f"- Status: `{STATUS}`",
        f"- Model status: `{MODEL_STATUS}`",
        "",
        "## Result",
        "",
        "R107 converts the R106 materiality blockers into a fillable external",
        "material evidence packet contract. It rejects both the empty template and",
        "a self-declared packet that reuses the R106 negative-control artifact.",
        "",
        "## Key Counters",
        "",
        f"- Contract required fields: `{s['contract_required_field_count']}`",
        f"- Acceptance gates: `{s['acceptance_gate_count']}`",
        f"- Empty template accepted: `{s['empty_template_accepted']}`",
        f"- Empty template gates passed / failed: `{s['empty_template_passed_gate_count']}` / `{s['empty_template_failed_gate_count']}`",
        f"- Self-declared packet accepted: `{s['self_declared_packet_accepted']}`",
        f"- Self-declared packet gates passed / failed: `{s['self_declared_passed_gate_count']}` / `{s['self_declared_failed_gate_count']}`",
        f"- Counter transition accepted: `{s['counter_transition_accepted']}`",
        f"- Counter delta: `{s['counter_delta']}`",
        f"- Accepted external reproductions: `{s['accepted_external_reproduction_count']}`",
        f"- Accepted external falsifications: `{s['accepted_external_falsification_count']}`",
        f"- New credit delta: `{s['new_credit_delta']}`",
        "",
        "## Requirements",
        "",
    ]
    for requirement in result["requirements"]:
        mark = "PASS" if requirement["passed"] else "FAIL"
        lines.append(f"- `{requirement['requirement_id']}` {mark}: {requirement['label']}")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Result JSON: `{RESULT_PATH}`",
            f"- Contract: `{R107_CONTRACT}`",
            f"- Template: `{R107_TEMPLATE}`",
            f"- Empty-template preflight: `{R107_EMPTY_PREFLIGHT}`",
            f"- Self-declared negative control: `{R107_SELF_DECLARED_PACKET}`",
            f"- Self-declared preflight: `{R107_SELF_DECLARED_PREFLIGHT}`",
            f"- Blocker queue: `{R107_BLOCKER_QUEUE}`",
            "",
            "## Claim Boundary",
            "",
            "R107 is a contract and preflight gate. It does not accept an external",
            "reproduction, does not move any counter, and does not grant new B7/O3/",
            "resource/layout credit. A future packet must pass this contract before a",
            "separate single-counter audit can be run.",
            "",
        ]
    )
    return "\n".join(lines)


def run(root: Path) -> dict[str, Any]:
    r106_result = load_json(root / R106_RESULT)
    r106_packet = load_json(root / R106_REMOTE_LOOKING_PACKET)
    contract = build_contract(root, r106_result)
    template = build_template(root, contract)
    self_packet = build_self_declared_packet(root, contract, r106_packet)
    empty_preflight = validate_packet(root, template, contract, "empty-template")
    self_preflight = validate_packet(root, self_packet, contract, "self-declared-r106-reuse")
    write_json(root / R107_EMPTY_PREFLIGHT, empty_preflight)
    write_json(root / R107_SELF_DECLARED_PREFLIGHT, self_preflight)
    blocker_queue = build_blocker_queue(root, contract, empty_preflight, self_preflight)

    requirements = [
        req(
            "A1",
            "R107 binds R106 materiality audit and blocker queue",
            contract["source_r106_materiality_audit_hash"] == r106_result["summary"]["materiality_audit_hash"]
            and contract["source_r106_blocker_queue_hash"] == r106_result["summary"]["blocker_queue_hash"],
            {
                "r106_materiality_audit_hash": contract["source_r106_materiality_audit_hash"],
                "r106_blocker_queue_hash": contract["source_r106_blocker_queue_hash"],
            },
        ),
        req(
            "A2",
            "R107 emits a fillable material evidence packet contract and template",
            len(contract["required_fields"]) == 30 and len(contract["acceptance_gates"]) == 22,
            {
                "contract_hash": contract["contract_hash"],
                "template_hash": template["template_hash"],
                "required_field_count": len(contract["required_fields"]),
                "acceptance_gate_count": len(contract["acceptance_gates"]),
            },
        ),
        req(
            "A3",
            "R107 rejects the empty template before any counter audit",
            empty_preflight["material_evidence_packet_accepted"] is False
            and empty_preflight["failed_gate_count"] >= 18,
            {
                "empty_template_preflight_hash": empty_preflight["preflight_hash"],
                "empty_template_failed_gate_count": empty_preflight["failed_gate_count"],
            },
        ),
        req(
            "A4",
            "R107 rejects self-declared reuse of the R106 negative-control packet",
            self_preflight["material_evidence_packet_accepted"] is False
            and "not_self_attestation_only" in self_preflight["failed_gates"],
            {
                "self_declared_preflight_hash": self_preflight["preflight_hash"],
                "self_declared_failed_gates": self_preflight["failed_gates"],
            },
        ),
        req(
            "A5",
            "R107 keeps counters and new credit at zero",
            blocker_queue["counter_delta"] == 0
            and blocker_queue["accepted_external_reproduction_count"] == 0
            and blocker_queue["accepted_external_falsification_count"] == 0
            and blocker_queue["new_credit_delta"] == 0,
            {
                "counter_delta": blocker_queue["counter_delta"],
                "accepted_external_reproduction_count": blocker_queue["accepted_external_reproduction_count"],
                "accepted_external_falsification_count": blocker_queue["accepted_external_falsification_count"],
                "new_credit_delta": blocker_queue["new_credit_delta"],
            },
        ),
        req(
            "A6",
            "R107 emits blockers for key registry, signature, CI, fetch transcript, and contact verification",
            len(blocker_queue["blockers"]) == 5,
            {
                "blocker_ids": [blocker["blocker_id"] for blocker in blocker_queue["blockers"]],
                "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
            },
        ),
    ]
    failed_requirement_ids = [
        requirement["requirement_id"] for requirement in requirements if not requirement["passed"]
    ]
    validation_errors: list[str] = []
    if failed_requirement_ids:
        validation_errors.append(f"failed_requirements={failed_requirement_ids}")

    summary = {
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_required_field_count": len(contract["required_fields"]),
        "acceptance_gate_count": len(contract["acceptance_gates"]),
        "empty_template_accepted": empty_preflight["material_evidence_packet_accepted"],
        "empty_template_passed_gate_count": empty_preflight["passed_gate_count"],
        "empty_template_failed_gate_count": empty_preflight["failed_gate_count"],
        "self_declared_packet_accepted": self_preflight["material_evidence_packet_accepted"],
        "self_declared_passed_gate_count": self_preflight["passed_gate_count"],
        "self_declared_failed_gate_count": self_preflight["failed_gate_count"],
        "counter_transition_accepted": blocker_queue["counter_transition_accepted"],
        "counter_delta": blocker_queue["counter_delta"],
        "accepted_external_reproduction_count": blocker_queue["accepted_external_reproduction_count"],
        "accepted_external_falsification_count": blocker_queue["accepted_external_falsification_count"],
        "new_credit_delta": blocker_queue["new_credit_delta"],
        "contract_hash": contract["contract_hash"],
        "template_hash": template["template_hash"],
        "empty_template_preflight_hash": empty_preflight["preflight_hash"],
        "self_declared_packet_hash": self_packet["self_declared_packet_hash"],
        "self_declared_preflight_hash": self_preflight["preflight_hash"],
        "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
        "requirements_passed": sum(1 for requirement in requirements if requirement["passed"]),
        "requirements_failed": len(failed_requirement_ids),
        "failed_requirement_ids": failed_requirement_ids,
        "validation_error_count": len(validation_errors),
    }
    payload = {
        "artifact": "B1/B7 cone01 R107 material evidence packet contract gate",
        "version": VERSION,
        "generated_at_unix": int(time.time()),
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "requirement_count": len(requirements),
        "requirements_passed": summary["requirements_passed"],
        "requirements_failed": summary["requirements_failed"],
        "requirements": requirements,
        "validation_error_count": len(validation_errors),
        "validation_errors": validation_errors,
        "contract_path": R107_CONTRACT,
        "template_path": R107_TEMPLATE,
        "empty_template_preflight_path": R107_EMPTY_PREFLIGHT,
        "self_declared_packet_path": R107_SELF_DECLARED_PACKET,
        "self_declared_preflight_path": R107_SELF_DECLARED_PREFLIGHT,
        "blocker_queue_path": R107_BLOCKER_QUEUE,
        "stdout_path": R107_STDOUT,
        "summary": summary,
    }
    payload["payload_hash"] = stable_self_hash(payload, "payload_hash")
    payload["summary"]["payload_hash"] = payload["payload_hash"]
    write_json(root / RESULT_PATH, payload)
    report_path = root / REPORT_PATH
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(payload), encoding="utf-8")
    stdout = {
        "artifact": payload["artifact"],
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "requirements_passed": payload["requirements_passed"],
        "requirements_failed": payload["requirements_failed"],
        "contract_hash": contract["contract_hash"],
        "empty_template_accepted": empty_preflight["material_evidence_packet_accepted"],
        "self_declared_packet_accepted": self_preflight["material_evidence_packet_accepted"],
        "counter_delta": blocker_queue["counter_delta"],
        "new_credit_delta": blocker_queue["new_credit_delta"],
        "payload_hash": payload["payload_hash"],
    }
    stdout_path = root / R107_STDOUT
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(json.dumps(stdout, sort_keys=True) + "\n", encoding="utf-8")
    payload["stdout_sha256"] = file_hash(stdout_path)
    payload["summary"]["stdout_sha256"] = payload["stdout_sha256"]
    write_json(root / RESULT_PATH, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    payload = run(root)
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
