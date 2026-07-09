#!/usr/bin/env python3
"""T-B1-004hf/T-B7-016o: R108 material evidence preflight verifier gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r108_material_evidence_preflight_verifier_gate_v0"
STATUS = "cone01_r108_near_pass_material_packet_rejected_local_synthetic"
MODEL_STATUS = "r107_contract_has_hardened_preflight_verifier_and_near_pass_negative_control"
VERSION = "0.1"
TARGET_ID = "T-B1-004hf/T-B7-016o"
UPSTREAM_TARGET_ID = "T-B1-004he/T-B7-016n"
SUBMISSION_DIR = "results/B1_B7_cone01_o3_f4_exit_route_submissions"
R108_DIR = f"{SUBMISSION_DIR}/R108-G1-material-evidence-preflight-verifier"
R108_PACKET_DIR = f"{R108_DIR}/near-pass-local-synthetic-packet"

R107_RESULT = "results/B1_B7_cone01_R107_material_evidence_packet_contract_gate_v0.json"
R107_CONTRACT = (
    f"{SUBMISSION_DIR}/R107-G1-external-material-evidence-packet-contract/"
    "external-material-evidence-packet-contract.json"
)
R107_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R107-G1-post-material-evidence-contract-blocker-queue.json"

R108_RULES = f"{R108_DIR}/material-evidence-preflight-verifier-rules.json"
R108_PACKET = f"{R108_PACKET_DIR}/near-pass-local-synthetic-material-evidence-packet.json"
R108_VERDICT = f"{R108_PACKET_DIR}/near-pass-local-synthetic-preflight.verdict.json"
R108_MANIFEST = f"{R108_PACKET_DIR}/near-pass-local-synthetic-evidence-manifest.json"
R108_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R108-G1-post-preflight-verifier-blocker-queue.json"
R108_STDOUT = f"{SUBMISSION_DIR}/R108-G1-material-evidence-preflight-verifier.stdout.txt"

RESULT_PATH = "results/B1_B7_cone01_R108_material_evidence_preflight_verifier_gate_v0.json"
REPORT_PATH = "research/B1_B7_cone01_R108_material_evidence_preflight_verifier_gate.md"

SUPPORT_FILES = {
    "reviewer_key_registry_path": f"{R108_PACKET_DIR}/reviewer-key-registry.json",
    "reviewer_identity_verification_path": f"{R108_PACKET_DIR}/reviewer-identity-verification.txt",
    "signed_payload_path": f"{R108_PACKET_DIR}/signed-payload.json",
    "detached_signature_path": f"{R108_PACKET_DIR}/detached-signature.asc",
    "signature_verification_transcript_path": f"{R108_PACKET_DIR}/signature-verification-transcript.txt",
    "third_party_ci_log_path": f"{R108_PACKET_DIR}/third-party-ci-log.txt",
    "remote_artifact_fetch_transcript_path": f"{R108_PACKET_DIR}/remote-artifact-fetch-transcript.txt",
    "fetched_artifact_manifest_path": f"{R108_PACKET_DIR}/fetched-artifact-manifest.json",
    "environment_manifest_path": f"{R108_PACKET_DIR}/environment-manifest.json",
    "reviewer_contact_verification_path": f"{R108_PACKET_DIR}/reviewer-contact-verification.txt",
}

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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def req(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def build_rules(root: Path, contract: dict[str, Any], r107_result: dict[str, Any]) -> dict[str, Any]:
    acceptance_gates = list(contract["acceptance_gates"]) + [
        "local_synthetic_marker_absent",
        "single_counter_request_only",
    ]
    rules = {
        "artifact": "R108 hardened material evidence preflight verifier rules",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_r107_result": R107_RESULT,
        "source_r107_contract": R107_CONTRACT,
        "source_r107_blocker_queue": R107_BLOCKER_QUEUE,
        "r107_contract_hash": contract["contract_hash"],
        "r107_payload_hash": r107_result["payload_hash"],
        "required_fields": contract["required_fields"],
        "required_hash_bindings": HASH_FIELDS,
        "accepted_counter_transition_modes": contract["accepted_counter_transition_modes"],
        "acceptance_gates": acceptance_gates,
        "synthetic_markers": [
            "r108-local-synthetic",
            "local-synthetic",
            "synthetic-negative-control",
            "not-a-public-third-party-run",
        ],
        "claim_boundary": (
            "R108 is a reusable preflight verifier. A packet passing this verifier "
            "only becomes eligible for a separate single-counter audit."
        ),
    }
    rules["verifier_rules_hash"] = stable_self_hash(rules, "verifier_rules_hash")
    write_json(root / R108_RULES, rules)
    return rules


def materialize_support_files(root: Path, contract: dict[str, Any]) -> dict[str, str]:
    payloads = {
        "reviewer_key_registry_path": {
            "artifact": "R108 reviewer key registry fixture",
            "marker": "r108-local-synthetic",
            "reviewer_id": "r108-near-pass-reviewer",
            "public_key_fingerprint": "SHA256:0123456789abcdef0123456789abcdef",
        },
        "reviewer_identity_verification_path": (
            "reviewer=r108-near-pass-reviewer\n"
            "verification_status=local-synthetic-fixture\n"
            "marker=r108-local-synthetic\n"
        ),
        "signed_payload_path": {
            "artifact": "R108 signed payload fixture",
            "marker": "r108-local-synthetic",
            "contract_hash": contract["contract_hash"],
            "requested_counter_transition": "external_reproduction_counter_increment",
        },
        "detached_signature_path": (
            "-----BEGIN SIGNATURE-----\n"
            "r108-local-synthetic-signature\n"
            "-----END SIGNATURE-----\n"
        ),
        "signature_verification_transcript_path": (
            "tool=minisign-compatible-fixture\n"
            "signature_valid=true\n"
            "marker=r108-local-synthetic\n"
        ),
        "third_party_ci_log_path": (
            "provider=github_actions\n"
            "run_url=https://github.com/crystal-tensor/Prometheus-plan/actions/runs/1080000001\n"
            "result=pass\n"
            "marker=not-a-public-third-party-run\n"
        ),
        "remote_artifact_fetch_transcript_path": (
            "fetched_from=https://github.com/crystal-tensor/Prometheus-plan\n"
            "artifact=R107-G1-external-material-evidence-packet-contract\n"
            "returncode=0\n"
            "marker=r108-local-synthetic\n"
        ),
        "fetched_artifact_manifest_path": {
            "artifact": "R108 fetched artifact manifest fixture",
            "marker": "r108-local-synthetic",
            "source": "https://github.com/crystal-tensor/Prometheus-plan",
        },
        "environment_manifest_path": {
            "artifact": "R108 environment manifest fixture",
            "runner_kind": "local-synthetic",
            "marker": "r108-local-synthetic",
            "python": "3.12",
        },
        "reviewer_contact_verification_path": (
            "reviewer_contact=https://github.com/r108-near-pass-reviewer\n"
            "verification_status=local-synthetic-fixture\n"
            "marker=r108-local-synthetic\n"
        ),
    }
    hashes: dict[str, str] = {}
    for field, rel_path in SUPPORT_FILES.items():
        value = payloads[field]
        path = root / rel_path
        if isinstance(value, dict):
            write_json(path, value)
        else:
            write_text(path, value)
        hashes[HASH_FIELDS[field]] = file_hash(path)
    return hashes


def build_near_pass_packet(root: Path, contract: dict[str, Any], hashes: dict[str, str]) -> dict[str, Any]:
    fields = {field: "" for field in contract["required_fields"]}
    for path_field, rel_path in SUPPORT_FILES.items():
        fields[path_field] = rel_path
        fields[HASH_FIELDS[path_field]] = hashes[HASH_FIELDS[path_field]]
    fields.update(
        {
            "reviewer_id": "r108-near-pass-reviewer",
            "reviewer_public_contact_or_handle": "https://github.com/r108-near-pass-reviewer",
            "reviewer_key_fingerprint": "SHA256:0123456789abcdef0123456789abcdef",
            "third_party_ci_run_url": "https://github.com/crystal-tensor/Prometheus-plan/actions/runs/1080000001",
            "third_party_ci_provider": "github_actions_fixture",
            "third_party_ci_commit_sha": "4e932ece2bd6d83c05195c01f4c387bd4555f54d",
            "r106_materiality_audit_hash": contract["source_r106_materiality_audit_hash"],
            "requested_counter_transition": "external_reproduction_counter_increment",
            "double_count_prevention_statement": "single counter request only; no prior accepted external packet",
            "claim_boundary": (
                "R108 local-synthetic near-pass negative control. This packet has "
                "complete fields and matching hashes but is not public third-party evidence."
            ),
        }
    )
    packet = {
        "artifact": "R108 near-pass local-synthetic material evidence packet",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "fields": fields,
        "negative_control_reason": (
            "All contract fields are filled, but the material evidence is explicitly "
            "local-synthetic and must not move an external counter."
        ),
    }
    packet["near_pass_packet_hash"] = stable_self_hash(packet, "near_pass_packet_hash")
    write_json(root / R108_PACKET, packet)
    return packet


def path_hash_matches(root: Path, fields: dict[str, Any], path_field: str) -> bool:
    rel_path = fields.get(path_field)
    hash_field = HASH_FIELDS[path_field]
    expected = fields.get(hash_field)
    if not rel_path or not expected:
        return False
    path = root / rel_path
    return path.is_file() and file_hash(path) == expected


def read_text(root: Path, rel_path: str) -> str:
    path = root / rel_path
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def validate_packet(root: Path, packet: dict[str, Any], contract: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    fields = packet["fields"]
    signature_text = read_text(root, fields.get("signature_verification_transcript_path", ""))
    fetch_text = read_text(root, fields.get("remote_artifact_fetch_transcript_path", ""))
    evidence_text = json.dumps(packet, sort_keys=True)
    for path_field in HASH_FIELDS:
        evidence_text += "\n" + read_text(root, fields.get(path_field, ""))
    gates = {
        "contract_hash_matches": packet.get("contract_hash") == contract["contract_hash"],
        "required_fields_present": all(field in fields for field in contract["required_fields"]),
        "required_fields_nonempty": all(fields.get(field) not in (None, "") for field in contract["required_fields"]),
        "reviewer_key_registry_file_hash_matches": path_hash_matches(root, fields, "reviewer_key_registry_path"),
        "reviewer_key_fingerprint_format": bool(
            re.fullmatch(r"(SHA256:)?[A-Fa-f0-9:]{32,95}", str(fields.get("reviewer_key_fingerprint", "")))
        ),
        "reviewer_identity_verification_file_hash_matches": path_hash_matches(root, fields, "reviewer_identity_verification_path"),
        "signed_payload_file_hash_matches": path_hash_matches(root, fields, "signed_payload_path"),
        "detached_signature_file_hash_matches": path_hash_matches(root, fields, "detached_signature_path"),
        "signature_verification_transcript_file_hash_matches": path_hash_matches(root, fields, "signature_verification_transcript_path"),
        "signature_verification_transcript_says_valid": "signature_valid=true" in signature_text,
        "third_party_ci_run_url_public_https": str(fields.get("third_party_ci_run_url", "")).startswith("https://")
        and "/actions/runs/" in str(fields.get("third_party_ci_run_url", "")),
        "third_party_ci_commit_sha_format": bool(
            re.fullmatch(r"[0-9a-f]{40}", str(fields.get("third_party_ci_commit_sha", "")))
        ),
        "third_party_ci_log_file_hash_matches": path_hash_matches(root, fields, "third_party_ci_log_path"),
        "remote_artifact_fetch_transcript_file_hash_matches": path_hash_matches(
            root, fields, "remote_artifact_fetch_transcript_path"
        ),
        "remote_artifact_fetch_transcript_says_fetched_from_github": "fetched_from=https://github.com/" in fetch_text,
        "fetched_artifact_manifest_file_hash_matches": path_hash_matches(root, fields, "fetched_artifact_manifest_path"),
        "environment_manifest_file_hash_matches": path_hash_matches(root, fields, "environment_manifest_path"),
        "reviewer_contact_verification_file_hash_matches": path_hash_matches(root, fields, "reviewer_contact_verification_path"),
        "r106_materiality_audit_hash_matches": fields.get("r106_materiality_audit_hash")
        == contract["source_r106_materiality_audit_hash"],
        "counter_transition_mode_allowed": fields.get("requested_counter_transition")
        in rules["accepted_counter_transition_modes"],
        "claim_boundary_present": fields.get("claim_boundary") not in (None, ""),
        "not_self_attestation_only": "self_declared" not in evidence_text and "self-declared" not in evidence_text,
        "local_synthetic_marker_absent": not any(marker in evidence_text for marker in rules["synthetic_markers"]),
        "single_counter_request_only": fields.get("requested_counter_transition")
        in {"external_reproduction_counter_increment", "external_falsification_counter_increment"},
    }
    gates["material_evidence_packet_accepted"] = all(gates.values())
    failed = [gate for gate, passed in gates.items() if not passed]
    verdict = {
        "artifact": "R108 near-pass local-synthetic material evidence preflight verdict",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "verifier_rules_hash": rules["verifier_rules_hash"],
        "near_pass_packet_hash": packet["near_pass_packet_hash"],
        "gates": gates,
        "passed_gate_count": sum(1 for passed in gates.values() if passed),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "material_evidence_packet_accepted": gates["material_evidence_packet_accepted"],
        "claim_boundary": (
            "Near-pass rejection is expected: local-synthetic material cannot move "
            "an external counter."
        ),
    }
    verdict["preflight_verdict_hash"] = stable_self_hash(verdict, "preflight_verdict_hash")
    write_json(root / R108_VERDICT, verdict)
    return verdict


def build_manifest(root: Path, packet: dict[str, Any], verdict: dict[str, Any]) -> dict[str, Any]:
    manifest = {
        "artifact": "R108 near-pass local-synthetic evidence manifest",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "near_pass_packet_hash": packet["near_pass_packet_hash"],
        "preflight_verdict_hash": verdict["preflight_verdict_hash"],
        "support_files": {
            field: {
                "path": rel_path,
                "sha256": file_hash(root / rel_path),
            }
            for field, rel_path in SUPPORT_FILES.items()
        },
    }
    manifest["manifest_hash"] = stable_self_hash(manifest, "manifest_hash")
    write_json(root / R108_MANIFEST, manifest)
    return manifest


def build_blocker_queue(root: Path, rules: dict[str, Any], verdict: dict[str, Any]) -> dict[str, Any]:
    queue = {
        "artifact": "R108 post-preflight-verifier blocker queue",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "verifier_rules_hash": rules["verifier_rules_hash"],
        "near_pass_preflight_verdict_hash": verdict["preflight_verdict_hash"],
        "counter_transition_accepted": False,
        "counter_delta": 0,
        "accepted_external_reproduction_count": 0,
        "accepted_external_falsification_count": 0,
        "new_credit_delta": 0,
        "blockers": [
            {
                "blocker_id": "R108-G1-1",
                "label": "Replace local-synthetic support files with public third-party artifacts.",
            },
            {
                "blocker_id": "R108-G1-2",
                "label": "Provide a public CI run whose log is externally dereferenceable.",
            },
            {
                "blocker_id": "R108-G1-3",
                "label": "Provide a reviewer key and contact trail without synthetic markers.",
            },
            {
                "blocker_id": "R108-G1-4",
                "label": "Rerun R108 verifier and then run a separate single-counter audit.",
            },
        ],
    }
    queue["blocker_queue_hash"] = stable_self_hash(queue, "blocker_queue_hash")
    write_json(root / R108_BLOCKER_QUEUE, queue)
    return queue


def build_report(result: dict[str, Any]) -> str:
    s = result["summary"]
    lines = [
        "# B1/B7 Cone01 R108 Material Evidence Preflight Verifier Gate",
        "",
        f"- Target: `{TARGET_ID}`",
        f"- Upstream target: `{UPSTREAM_TARGET_ID}`",
        f"- Method: `{METHOD}`",
        f"- Status: `{STATUS}`",
        f"- Model status: `{MODEL_STATUS}`",
        "",
        "## Result",
        "",
        "R108 turns the R107 material evidence packet contract into a reusable",
        "hardened preflight verifier. It materializes a field-complete near-pass",
        "packet with matching hashes, signature-valid transcript text, CI log, and",
        "fetch transcript, then rejects it because the evidence is explicitly local",
        "synthetic rather than public third-party material.",
        "",
        "## Key Counters",
        "",
        f"- Verifier gate count: `{s['verifier_gate_count']}`",
        f"- Evidence file count: `{s['evidence_file_count']}`",
        f"- Near-pass packet accepted: `{s['near_pass_packet_accepted']}`",
        f"- Near-pass gates passed / failed: `{s['near_pass_passed_gate_count']}` / `{s['near_pass_failed_gate_count']}`",
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
            f"- Verifier rules: `{R108_RULES}`",
            f"- Near-pass packet: `{R108_PACKET}`",
            f"- Near-pass preflight verdict: `{R108_VERDICT}`",
            f"- Evidence manifest: `{R108_MANIFEST}`",
            f"- Blocker queue: `{R108_BLOCKER_QUEUE}`",
            "",
            "## Claim Boundary",
            "",
            "R108 is a verifier-hardening and negative-control gate. It does not",
            "accept an external reproduction, does not move any counter, and does",
            "not grant B7/O3/resource/layout credit.",
            "",
        ]
    )
    return "\n".join(lines)


def run(root: Path) -> dict[str, Any]:
    r107_result = load_json(root / R107_RESULT)
    contract = load_json(root / R107_CONTRACT)
    rules = build_rules(root, contract, r107_result)
    hashes = materialize_support_files(root, contract)
    packet = build_near_pass_packet(root, contract, hashes)
    verdict = validate_packet(root, packet, contract, rules)
    manifest = build_manifest(root, packet, verdict)
    blocker_queue = build_blocker_queue(root, rules, verdict)

    requirements = [
        req(
            "A1",
            "R108 binds the R107 result, contract, and blocker queue",
            rules["r107_contract_hash"] == contract["contract_hash"]
            and rules["r107_payload_hash"] == r107_result["payload_hash"],
            {
                "r107_contract_hash": rules["r107_contract_hash"],
                "r107_payload_hash": rules["r107_payload_hash"],
            },
        ),
        req(
            "A2",
            "R108 emits hardened verifier rules with synthetic-marker rejection",
            "local_synthetic_marker_absent" in rules["acceptance_gates"]
            and len(rules["acceptance_gates"]) == 24,
            {
                "verifier_rules_hash": rules["verifier_rules_hash"],
                "verifier_gate_count": len(rules["acceptance_gates"]),
            },
        ),
        req(
            "A3",
            "R108 materializes a field-complete near-pass evidence packet",
            len(manifest["support_files"]) == 10 and all(packet["fields"].get(field) for field in contract["required_fields"]),
            {
                "near_pass_packet_hash": packet["near_pass_packet_hash"],
                "evidence_file_count": len(manifest["support_files"]),
                "manifest_hash": manifest["manifest_hash"],
            },
        ),
        req(
            "A4",
            "R108 rejects the near-pass packet only after high-surface completion",
            verdict["material_evidence_packet_accepted"] is False
            and verdict["passed_gate_count"] >= 22
            and "local_synthetic_marker_absent" in verdict["failed_gates"],
            {
                "near_pass_passed_gate_count": verdict["passed_gate_count"],
                "near_pass_failed_gate_count": verdict["failed_gate_count"],
                "failed_gates": verdict["failed_gates"],
                "preflight_verdict_hash": verdict["preflight_verdict_hash"],
            },
        ),
        req(
            "A5",
            "R108 keeps counters and new credit at zero",
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
            "R108 emits blockers for replacing synthetic evidence and rerunning a single-counter audit",
            len(blocker_queue["blockers"]) == 4,
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
        "verifier_gate_count": len(rules["acceptance_gates"]),
        "evidence_file_count": len(manifest["support_files"]),
        "near_pass_packet_accepted": verdict["material_evidence_packet_accepted"],
        "near_pass_passed_gate_count": verdict["passed_gate_count"],
        "near_pass_failed_gate_count": verdict["failed_gate_count"],
        "near_pass_failed_gates": verdict["failed_gates"],
        "counter_transition_accepted": blocker_queue["counter_transition_accepted"],
        "counter_delta": blocker_queue["counter_delta"],
        "accepted_external_reproduction_count": blocker_queue["accepted_external_reproduction_count"],
        "accepted_external_falsification_count": blocker_queue["accepted_external_falsification_count"],
        "new_credit_delta": blocker_queue["new_credit_delta"],
        "verifier_rules_hash": rules["verifier_rules_hash"],
        "near_pass_packet_hash": packet["near_pass_packet_hash"],
        "preflight_verdict_hash": verdict["preflight_verdict_hash"],
        "manifest_hash": manifest["manifest_hash"],
        "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
        "requirements_passed": sum(1 for requirement in requirements if requirement["passed"]),
        "requirements_failed": len(failed_requirement_ids),
        "failed_requirement_ids": failed_requirement_ids,
        "validation_error_count": len(validation_errors),
    }
    payload = {
        "artifact": "B1/B7 cone01 R108 material evidence preflight verifier gate",
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
        "verifier_rules_path": R108_RULES,
        "near_pass_packet_path": R108_PACKET,
        "near_pass_preflight_verdict_path": R108_VERDICT,
        "evidence_manifest_path": R108_MANIFEST,
        "blocker_queue_path": R108_BLOCKER_QUEUE,
        "stdout_path": R108_STDOUT,
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
        "near_pass_packet_accepted": verdict["material_evidence_packet_accepted"],
        "near_pass_passed_gate_count": verdict["passed_gate_count"],
        "near_pass_failed_gate_count": verdict["failed_gate_count"],
        "counter_delta": blocker_queue["counter_delta"],
        "new_credit_delta": blocker_queue["new_credit_delta"],
        "payload_hash": payload["payload_hash"],
    }
    stdout_path = root / R108_STDOUT
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
    payload = run(Path(args.repo_root).resolve())
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
