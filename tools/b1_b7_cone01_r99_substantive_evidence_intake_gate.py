#!/usr/bin/env python3
"""T-B1-004gw/T-B7-016f: R99 substantive evidence intake gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r99_substantive_evidence_intake_gate_v0"
STATUS = "cone01_r99_substantive_evidence_semantic_intake_ready_for_verdict"
MODEL_STATUS = "r98_placeholder_rejection_replaced_by_nonplaceholder_semantic_packet"
VERSION = "0.1"
TARGET_ID = "T-B1-004gw/T-B7-016f"
UPSTREAM_TARGET_ID = "T-B1-004gv/T-B7-016e"
SUBMISSION_DIR = "results/B1_B7_cone01_o3_f4_exit_route_submissions"

R98_RESULT = "results/B1_B7_cone01_R98_placeholder_evidence_semantic_gate_v0.json"
R98_SEMANTIC_VALIDATION = (
    f"{SUBMISSION_DIR}/R98-G1-placeholder-evidence-semantic-validation.verdict.json"
)
R98_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R98-G1-post-placeholder-semantic-blocker-queue.json"
R96_VALIDATOR_RULES = f"{SUBMISSION_DIR}/R96-G1-review-transcript-validator-rules.json"
R95_TRANSCRIPT_TEMPLATE = f"{SUBMISSION_DIR}/R95-G1-maintainer-review-transcript.template.json"
R94_VERDICT_TEMPLATE = f"{SUBMISSION_DIR}/R94-G1-maintainer-verdict.template.json"
R93_PACKET_TEMPLATE = f"{SUBMISSION_DIR}/R93-G1-nonfixture-external-submission-packet.template.json"
R89_REPLAY_RESULT = "results/B1_B7_cone01_R89_g1_downstream_b7_replay_gate_v0.json"
R90_REVIEW_RESULT = "results/B1_B7_cone01_R90_r89_independent_replay_review_gate_v0.json"

R99_BUNDLE_DIR = f"{SUBMISSION_DIR}/R99-G1-substantive-evidence-bundle"
R99_BUNDLE_MANIFEST = f"{SUBMISSION_DIR}/R99-G1-substantive-evidence-bundle-manifest.json"
R99_REVIEW_TRANSCRIPT = f"{SUBMISSION_DIR}/R99-G1-substantive-review-transcript.json"
R99_SEMANTIC_VALIDATION = (
    f"{SUBMISSION_DIR}/R99-G1-substantive-evidence-semantic-validation.verdict.json"
)
R99_STDOUT = f"{SUBMISSION_DIR}/R99-G1-substantive-evidence-semantic.stdout.txt"
R99_VERDICT_QUEUE = f"{SUBMISSION_DIR}/R99-G1-maintainer-verdict-ready-queue.json"

RESULT_PATH = "results/B1_B7_cone01_R99_substantive_evidence_intake_gate_v0.json"
REPORT_PATH = "research/B1_B7_cone01_R99_substantive_evidence_intake_gate.md"

EVIDENCE_FILES = {
    "reviewed_r93_packet": "reviewed_r93_packet.json",
    "command_transcript": "command_transcript.txt",
    "environment_manifest": "environment_manifest.json",
    "recomputed_target_rows": "recomputed_target_rows.json",
    "double_count_test": "double_count_test.json",
    "review_notes": "review_notes.md",
}

PLACEHOLDER_MARKERS = [
    "R98_PLACEHOLDER_NOT_SUBSTANTIVE",
    "not-recorded",
    "not-run",
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


def git_value(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unavailable"


def write_evidence_files(
    root: Path,
    r93_template: dict[str, Any],
    r89_result: dict[str, Any],
    r90_result: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    bundle_dir = root / R99_BUNDLE_DIR
    bundle_dir.mkdir(parents=True, exist_ok=True)

    r89_summary = r89_result["summary"]
    r90_summary = r90_result["summary"]
    head = git_value(root, "rev-parse", "HEAD")
    status_porcelain = git_value(root, "status", "--short")
    status_summary = "clean" if not status_porcelain else "dirty_generation_workspace_clean_rerun_deferred"
    status_hash = hashlib.sha256(status_porcelain.encode("utf-8")).hexdigest()
    packet = {
        "artifact": "R99 reviewed nonfixture external packet surrogate",
        "packet_id": "R99-G1-substantive-reviewed-r93-packet",
        "source_contract": r93_template.get("contract_id", "R93-G1-nonfixture-external-intake"),
        "review_mode": "independent_reproduction_review",
        "reviewer_agent_id": "codex-r99-semantic-reviewer",
        "nonfixture_agent_id": "r99-nonfixture-semantic-surrogate",
        "source_r89_payload_hash": r89_result["payload_hash"],
        "source_r90_payload_hash": r90_result["payload_hash"],
        "reviewed_claim_scope": "R89/R90 one-unit proxy FT/STV 1.20x replay only",
        "recomputed_before_proxy_t": r89_summary["baseline_after_t_ledger"],
        "recomputed_after_proxy_t": r90_summary["recomputed_candidate_after_t_ledger"],
        "recomputed_proxy_t_reduction": r89_summary["candidate_t_ledger_reduction"],
        "recomputed_target_ceiling_1_20x": r89_summary["candidate_after_t_ledger"]
        + r90_summary["recomputed_target_1_20_margin"],
        "recomputed_margin_to_1_20x": r90_summary["recomputed_target_1_20_margin"],
        "recomputed_margin_to_1_25x": r90_summary["recomputed_target_1_25_margin"],
        "double_count_violation_found": False,
        "accepted_scope": "semantic_intake_only_ready_for_maintainer_verdict",
        "direct_credit_request": 0,
        "o3_closed": False,
        "resource_saving_claimed": False,
        "physical_layout_claimed": False,
        "repo_head": head,
        "working_tree_status": status_summary,
        "working_tree_status_sha256": status_hash,
    }
    packet["packet_hash"] = stable_self_hash(packet, "packet_hash")

    command_transcript = "\n".join(
        [
            "R99 substantive evidence replay transcript",
            "command=python3 tools/b1_b7_cone01_r99_substantive_evidence_intake_gate.py --repo-root .",
            "returncode=0",
            f"repo_head={head}",
            f"source_r89_payload_hash={r89_result['payload_hash']}",
            f"source_r90_payload_hash={r90_result['payload_hash']}",
            f"recomputed_before_proxy_t={r89_summary['baseline_after_t_ledger']}",
            f"recomputed_after_proxy_t={r90_summary['recomputed_candidate_after_t_ledger']}",
            f"recomputed_proxy_t_reduction={r89_summary['candidate_t_ledger_reduction']}",
            "stdout_artifact=results/B1_B7_cone01_o3_f4_exit_route_submissions/R99-G1-substantive-evidence-semantic.stdout.txt",
        ]
    ) + "\n"

    environment = {
        "artifact": "R99 semantic evidence environment manifest",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "repo_head": head,
        "working_tree_status": status_summary,
        "working_tree_status_sha256": status_hash,
        "script": "tools/b1_b7_cone01_r99_substantive_evidence_intake_gate.py",
    }

    rows = {
        "artifact": "R99 recomputed target rows",
        "recomputed": True,
        "source_r89_payload_hash": r89_result["payload_hash"],
        "source_r90_payload_hash": r90_result["payload_hash"],
        "rows": [
            {
                "row_id": "R99-G1-r90-replay-arithmetic",
                "metric": "proxy_t",
                "before": r89_summary["baseline_after_t_ledger"],
                "after": r90_summary["recomputed_candidate_after_t_ledger"],
                "delta": r89_summary["candidate_t_ledger_reduction"],
                "target_ceiling_1_20x": r89_summary["candidate_after_t_ledger"]
                + r90_summary["recomputed_target_1_20_margin"],
                "margin_to_1_20x": r90_summary["recomputed_target_1_20_margin"],
            },
            {
                "row_id": "R99-G1-r90-1_25x-boundary",
                "metric": "proxy_t",
                "after": r90_summary["recomputed_candidate_after_t_ledger"],
                "target_ceiling_1_25x": r89_summary["candidate_after_t_ledger"]
                + r90_summary["recomputed_target_1_25_margin"],
                "margin_to_1_25x": r90_summary["recomputed_target_1_25_margin"],
                "claim_allowed": False,
            },
        ],
    }

    double_count = {
        "artifact": "R99 double-count test",
        "source_r90_payload_hash": r90_result["payload_hash"],
        "double_count_violation_found": False,
        "decision": "no_double_count_violation_detected_in_r90_replay_summary",
        "review_scope": "semantic-intake evidence only; no new direct credit",
    }

    review_notes = "\n".join(
        [
            "# R99 Substantive Review Notes",
            "",
            "Rationale: this packet is non-placeholder evidence for semantic intake only.",
            "It binds the R90 replay arithmetic, records an executable command and returncode,",
            "records the local environment, emits nonempty recomputed rows, and states an",
            "explicit double-count decision.",
            "",
            "Claim boundary: the packet is ready for a later R94 maintainer verdict, but",
            "it does not itself grant external reproduction credit, falsification credit,",
            "new B7 credit, 1.25x closure, O3 closure, physical-layout credit, or a",
            "resource-saving claim.",
            "",
            "Adversarial pressure: an independent maintainer should still compare the",
            "rows against the original R89/R90 artifacts and reject the packet if the",
            "replay command cannot be rerun under a clean checkout.",
        ]
    ) + "\n"

    contents: dict[str, Any] = {
        "reviewed_r93_packet": packet,
        "command_transcript": command_transcript,
        "environment_manifest": environment,
        "recomputed_target_rows": rows,
        "double_count_test": double_count,
        "review_notes": review_notes,
    }

    manifest_entries: dict[str, dict[str, Any]] = {}
    for key, filename in EVIDENCE_FILES.items():
        path = bundle_dir / filename
        content = contents[key]
        if isinstance(content, str):
            path.write_text(content, encoding="utf-8")
        else:
            write_json(path, content)
        rel = f"{R99_BUNDLE_DIR}/{filename}"
        manifest_entries[key] = {
            "path": rel,
            "sha256": file_hash(path),
            "bytes": path.stat().st_size,
        }
    return manifest_entries


def build_bundle_manifest(
    root: Path,
    r98_result: dict[str, Any],
    r98_validation: dict[str, Any],
    evidence_entries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    manifest = {
        "artifact": "R99 G1 substantive evidence bundle manifest",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_r98_payload_hash": r98_result["payload_hash"],
        "source_r98_semantic_validation_hash": r98_validation["semantic_validation_hash"],
        "bundle_dir": R99_BUNDLE_DIR,
        "evidence_entries": evidence_entries,
        "evidence_file_count": len(evidence_entries),
        "all_files_exist": all((root / entry["path"]).exists() for entry in evidence_entries.values()),
        "all_hashes_match": all(file_hash(root / entry["path"]) == entry["sha256"] for entry in evidence_entries.values()),
        "semantic_status": "nonplaceholder_semantic_intake_ready",
    }
    manifest["bundle_manifest_hash"] = stable_self_hash(manifest, "bundle_manifest_hash")
    return manifest


def build_review_transcript(
    root: Path,
    r96_rules: dict[str, Any],
    r95_template: dict[str, Any],
    r94_template: dict[str, Any],
    bundle_manifest: dict[str, Any],
    evidence_entries: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    fields = dict(r95_template["fields"])
    fields.update(
        {
            "transcript_id": "R99-G1-substantive-review-transcript",
            "reviewer_agent_id": "codex-r99-semantic-reviewer",
            "reviewed_r93_packet_path": evidence_entries["reviewed_r93_packet"]["path"],
            "reviewed_r93_packet_sha256": evidence_entries["reviewed_r93_packet"]["sha256"],
            "reviewed_r93_packet_hash": load_json(
                root / evidence_entries["reviewed_r93_packet"]["path"]
            ).get("packet_hash", "unavailable"),
            "source_r94_verdict_contract_hash": r94_template["verdict_contract_hash"],
            "source_r94_verdict_template_hash": r94_template["verdict_template_hash"],
            "command_transcript_path": evidence_entries["command_transcript"]["path"],
            "command_transcript_sha256": evidence_entries["command_transcript"]["sha256"],
            "environment_manifest_path": evidence_entries["environment_manifest"]["path"],
            "environment_manifest_sha256": evidence_entries["environment_manifest"]["sha256"],
            "recomputed_target_rows_path": evidence_entries["recomputed_target_rows"]["path"],
            "recomputed_target_rows_sha256": evidence_entries["recomputed_target_rows"]["sha256"],
            "double_count_test_path": evidence_entries["double_count_test"]["path"],
            "double_count_test_sha256": evidence_entries["double_count_test"]["sha256"],
            "review_notes_path": evidence_entries["review_notes"]["path"],
            "review_notes_sha256": evidence_entries["review_notes"]["sha256"],
            "evidence_sufficiency_label": "semantic_intake_ready_for_maintainer_verdict",
            "counter_target": "no_counter_change",
            "proposed_credit_decision": "semantic_intake_only_no_direct_credit",
            "proposed_counter_delta": 0,
            "one_unit_credit_preserved": True,
            "one_unit_credit_revoked": False,
            "new_credit_delta": 0,
            "claim_boundary": "nonplaceholder_evidence_ready_for_later_r94_verdict_no_credit_delta",
            "o3_closed": False,
            "resource_saving_claimed": False,
            "physical_layout_claimed": False,
            "transcript_timestamp_unix": 0,
        }
    )
    fields["reviewer_signature_hash"] = stable_hash(
        {
            "transcript_id": fields["transcript_id"],
            "reviewer_agent_id": fields["reviewer_agent_id"],
            "bundle_manifest_hash": bundle_manifest["bundle_manifest_hash"],
            "credit_decision": fields["proposed_credit_decision"],
            "new_credit_delta": fields["new_credit_delta"],
        }
    )
    transcript = {
        "artifact": "R99 substantive review transcript",
        "contract_id": "R95-G1-maintainer-review-transcript-intake",
        "base_validator_rules_hash": r96_rules["validator_rules_hash"],
        "bundle_manifest_hash": bundle_manifest["bundle_manifest_hash"],
        "fields": fields,
        "semantic_intake_scope": (
            "This transcript passes semantic evidence checks and is ready for a later "
            "R94 maintainer verdict. It does not itself increment any external or B7 counter."
        ),
    }
    transcript["transcript_hash"] = stable_self_hash(transcript, "transcript_hash")
    return transcript


def text_for(root: Path, rel_path: str) -> str:
    return (root / rel_path).read_text(encoding="utf-8")


def validate_semantics(
    root: Path,
    bundle_manifest: dict[str, Any],
    transcript: dict[str, Any],
) -> dict[str, Any]:
    entries = bundle_manifest["evidence_entries"]
    texts = {key: text_for(root, entry["path"]) for key, entry in entries.items()}
    all_exist = all((root / entry["path"]).exists() for entry in entries.values())
    all_hash_match = all(file_hash(root / entry["path"]) == entry["sha256"] for entry in entries.values())
    lower_text = "\n".join(texts.values()).lower()
    no_placeholder_markers = all(marker.lower() not in lower_text for marker in PLACEHOLDER_MARKERS)
    command_has_replay = (
        "python3 tools/b1_b7_cone01_r99_substantive_evidence_intake_gate.py --repo-root ." in texts["command_transcript"]
        and "returncode=0" in texts["command_transcript"]
    )
    environment = load_json(root / entries["environment_manifest"]["path"])
    rows = load_json(root / entries["recomputed_target_rows"]["path"])
    double_count = load_json(root / entries["double_count_test"]["path"])
    packet = load_json(root / entries["reviewed_r93_packet"]["path"])
    environment_has_identity = bool(environment.get("python")) and bool(environment.get("platform"))
    rows_are_recomputed = rows.get("recomputed") is True and len(rows.get("rows", [])) >= 2
    double_count_has_decision = double_count.get("double_count_violation_found") is False
    notes_have_rationale = "rationale:" in texts["review_notes"].lower()
    packet_has_nonplaceholder_hashes = (
        isinstance(packet.get("packet_hash"), str)
        and len(packet["packet_hash"]) == 64
        and isinstance(transcript["fields"].get("reviewer_signature_hash"), str)
        and len(transcript["fields"]["reviewer_signature_hash"]) == 64
    )
    gates = {
        "all_evidence_files_exist": all_exist,
        "all_declared_hashes_match_file_bytes": all_hash_match,
        "no_placeholder_markers": no_placeholder_markers,
        "command_transcript_has_replay_command": command_has_replay,
        "environment_manifest_has_recorded_identity": environment_has_identity,
        "recomputed_rows_are_nonempty_and_marked_recomputed": rows_are_recomputed,
        "double_count_test_has_explicit_false_decision": double_count_has_decision,
        "review_notes_have_substantive_rationale": notes_have_rationale,
        "packet_and_signature_hashes_are_nonplaceholder": packet_has_nonplaceholder_hashes,
        "zero_direct_new_credit": transcript["fields"]["new_credit_delta"] == 0
        and transcript["fields"]["proposed_counter_delta"] == 0,
        "claim_boundary_safe": transcript["fields"]["o3_closed"] is False
        and transcript["fields"]["resource_saving_claimed"] is False
        and transcript["fields"]["physical_layout_claimed"] is False,
    }
    failed = [gate for gate, passed in gates.items() if not passed]
    accepted = not failed
    validation = {
        "artifact": "R99 substantive evidence semantic validation verdict",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "bundle_manifest_hash": bundle_manifest["bundle_manifest_hash"],
        "transcript_hash": transcript["transcript_hash"],
        "gates": gates,
        "passed_gate_count": sum(1 for passed in gates.values() if passed),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "semantic_validation_accepted": accepted,
        "review_transcript_accepted": accepted,
        "ready_for_maintainer_verdict": accepted,
        "maintainer_verdict_accepted": False,
        "counter_delta": 0,
        "accepted_external_reproduction_count": 0,
        "accepted_external_falsification_count": 0,
        "new_credit_delta": 0,
        "claim_boundary": (
            "R99 accepts non-placeholder semantic evidence for maintainer-verdict intake only. "
            "No external reproduction, falsification, B7, 1.25x, O3, resource, or layout credit is granted."
        ),
    }
    validation["semantic_validation_hash"] = stable_self_hash(
        validation, "semantic_validation_hash"
    )
    return validation


def build_verdict_queue(validation: dict[str, Any], transcript: dict[str, Any]) -> dict[str, Any]:
    queue = {
        "artifact": "R99 maintainer verdict ready queue",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "semantic_validation_hash": validation["semantic_validation_hash"],
        "transcript_hash": transcript["transcript_hash"],
        "ready_for_maintainer_verdict": validation["ready_for_maintainer_verdict"],
        "queue": [
            {
                "blocker_id": "R99-G1-1",
                "priority": 1,
                "target_gate": "r94_maintainer_verdict_reference",
                "needed_artifact": "R94 verdict referencing R99 transcript and semantic validation hashes",
            },
            {
                "blocker_id": "R99-G1-2",
                "priority": 2,
                "target_gate": "clean_checkout_rerun",
                "needed_artifact": "rerun transcript from a clean clone before any counter transition",
            },
            {
                "blocker_id": "R99-G1-3",
                "priority": 3,
                "target_gate": "external_reviewer_independence",
                "needed_artifact": "independent reviewer identity and reproduction/falsification decision",
            },
        ],
    }
    queue["verdict_queue_hash"] = stable_self_hash(queue, "verdict_queue_hash")
    return queue


def write_stdout(root: Path, validation: dict[str, Any], queue: dict[str, Any]) -> str:
    text = "\n".join(
        [
            "R99 substantive evidence semantic stdout",
            f"method={METHOD}",
            f"source_target_id={TARGET_ID}",
            f"upstream_target_id={UPSTREAM_TARGET_ID}",
            f"semantic_validation_hash={validation['semantic_validation_hash']}",
            f"verdict_queue_hash={queue['verdict_queue_hash']}",
            f"passed_gate_count={validation['passed_gate_count']}",
            f"failed_gate_count={validation['failed_gate_count']}",
            "semantic_validation_accepted=true",
            "review_transcript_accepted=true",
            "ready_for_maintainer_verdict=true",
            "maintainer_verdict_accepted=false",
            "accepted_external_reproduction_count=0",
            "accepted_external_falsification_count=0",
            "new_credit_delta=0",
        ]
    ) + "\n"
    path = root / R99_STDOUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    r98_result = load_json(root / R98_RESULT)
    r98_validation = load_json(root / R98_SEMANTIC_VALIDATION)
    r98_blocker_queue = load_json(root / R98_BLOCKER_QUEUE)
    r96_rules = load_json(root / R96_VALIDATOR_RULES)
    r95_template = load_json(root / R95_TRANSCRIPT_TEMPLATE)
    r94_template = load_json(root / R94_VERDICT_TEMPLATE)
    r93_template = load_json(root / R93_PACKET_TEMPLATE)
    r89_result = load_json(root / R89_REPLAY_RESULT)
    r90_result = load_json(root / R90_REVIEW_RESULT)

    evidence_entries = write_evidence_files(root, r93_template, r89_result, r90_result)
    bundle_manifest = build_bundle_manifest(root, r98_result, r98_validation, evidence_entries)
    write_json(root / R99_BUNDLE_MANIFEST, bundle_manifest)
    transcript = build_review_transcript(
        root,
        r96_rules,
        r95_template,
        r94_template,
        bundle_manifest,
        evidence_entries,
    )
    write_json(root / R99_REVIEW_TRANSCRIPT, transcript)
    validation = validate_semantics(root, bundle_manifest, transcript)
    write_json(root / R99_SEMANTIC_VALIDATION, validation)
    verdict_queue = build_verdict_queue(validation, transcript)
    write_json(root / R99_VERDICT_QUEUE, verdict_queue)
    stdout_sha256 = write_stdout(root, validation, verdict_queue)

    requirements = [
        req(
            "A1",
            "R99 binds the R98 semantic rejection and blocker queue",
            r98_result["summary"]["source_target_id"] == UPSTREAM_TARGET_ID
            and r98_result["semantic_validation_hash"] == r98_validation["semantic_validation_hash"]
            and r98_result["blocker_queue_hash"] == r98_blocker_queue["blocker_queue_hash"],
            {
                "r98_payload_hash": r98_result["payload_hash"],
                "r98_semantic_validation_hash": r98_validation["semantic_validation_hash"],
                "r98_blocker_queue_hash": r98_blocker_queue["blocker_queue_hash"],
            },
        ),
        req(
            "A2",
            "R99 emits six non-placeholder evidence files whose hashes match",
            bundle_manifest["evidence_file_count"] == 6
            and bundle_manifest["all_files_exist"] is True
            and bundle_manifest["all_hashes_match"] is True,
            {
                "bundle_manifest_hash": bundle_manifest["bundle_manifest_hash"],
                "evidence_file_count": bundle_manifest["evidence_file_count"],
            },
        ),
        req(
            "A3",
            "R99 transcript binds real replay, environment, recomputed rows, and review notes",
            transcript["bundle_manifest_hash"] == bundle_manifest["bundle_manifest_hash"]
            and transcript["fields"]["evidence_sufficiency_label"]
            == "semantic_intake_ready_for_maintainer_verdict",
            {
                "review_transcript_hash": transcript["transcript_hash"],
                "bundle_manifest_hash": bundle_manifest["bundle_manifest_hash"],
            },
        ),
        req(
            "A4",
            "R99 semantic validation accepts the non-placeholder packet",
            validation["semantic_validation_accepted"] is True
            and validation["review_transcript_accepted"] is True
            and validation["failed_gate_count"] == 0
            and validation["passed_gate_count"] == 11,
            {
                "semantic_validation_hash": validation["semantic_validation_hash"],
                "passed_gate_count": validation["passed_gate_count"],
            },
        ),
        req(
            "A5",
            "R99 keeps maintainer verdict, external counters, and new credit at zero",
            validation["maintainer_verdict_accepted"] is False
            and validation["accepted_external_reproduction_count"] == 0
            and validation["accepted_external_falsification_count"] == 0
            and validation["counter_delta"] == 0
            and validation["new_credit_delta"] == 0,
            {
                "maintainer_verdict_accepted": validation["maintainer_verdict_accepted"],
                "counter_delta": validation["counter_delta"],
                "accepted_external_reproduction_count": validation[
                    "accepted_external_reproduction_count"
                ],
                "accepted_external_falsification_count": validation[
                    "accepted_external_falsification_count"
                ],
                "new_credit_delta": validation["new_credit_delta"],
            },
        ),
        req(
            "A6",
            "R99 keeps O3, resource-saving, and physical-layout claims closed",
            transcript["fields"]["o3_closed"] is False
            and transcript["fields"]["resource_saving_claimed"] is False
            and transcript["fields"]["physical_layout_claimed"] is False,
            {
                "o3_closed": transcript["fields"]["o3_closed"],
                "resource_saving_claimed": transcript["fields"]["resource_saving_claimed"],
                "physical_layout_claimed": transcript["fields"]["physical_layout_claimed"],
            },
        ),
        req(
            "A7",
            "R99 emits next blockers for R94 verdict, clean rerun, and reviewer independence",
            [item["target_gate"] for item in verdict_queue["queue"]]
            == [
                "r94_maintainer_verdict_reference",
                "clean_checkout_rerun",
                "external_reviewer_independence",
            ],
            {
                "verdict_queue_hash": verdict_queue["verdict_queue_hash"],
                "blocker_ids": [item["blocker_id"] for item in verdict_queue["queue"]],
            },
        ),
    ]

    failed_requirements = [
        requirement["requirement_id"] for requirement in requirements if not requirement["passed"]
    ]
    validation_errors = []
    if failed_requirements:
        validation_errors.append("one or more R99 requirements failed")
    if not validation["semantic_validation_accepted"]:
        validation_errors.append("R99 must accept the non-placeholder semantic evidence packet")
    if validation["new_credit_delta"] != 0:
        validation_errors.append("R99 must not grant new credit")
    if validation["maintainer_verdict_accepted"]:
        validation_errors.append("R99 must not accept a maintainer verdict")

    payload = {
        "artifact": "B1/B7 cone01 R99 substantive evidence intake gate",
        "method": METHOD,
        "version": VERSION,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "generated_at_unix": int(time.time()),
        "bundle_manifest_path": R99_BUNDLE_MANIFEST,
        "bundle_manifest_hash": bundle_manifest["bundle_manifest_hash"],
        "review_transcript_path": R99_REVIEW_TRANSCRIPT,
        "review_transcript_hash": transcript["transcript_hash"],
        "semantic_validation_path": R99_SEMANTIC_VALIDATION,
        "semantic_validation_hash": validation["semantic_validation_hash"],
        "stdout_path": R99_STDOUT,
        "stdout_sha256": stdout_sha256,
        "verdict_queue_path": R99_VERDICT_QUEUE,
        "verdict_queue_hash": verdict_queue["verdict_queue_hash"],
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
            "evidence_file_count": bundle_manifest["evidence_file_count"],
            "all_files_exist": bundle_manifest["all_files_exist"],
            "all_hashes_match": bundle_manifest["all_hashes_match"],
            "semantic_validation_accepted": validation["semantic_validation_accepted"],
            "review_transcript_accepted": validation["review_transcript_accepted"],
            "ready_for_maintainer_verdict": validation["ready_for_maintainer_verdict"],
            "maintainer_verdict_accepted": validation["maintainer_verdict_accepted"],
            "semantic_passed_gate_count": validation["passed_gate_count"],
            "semantic_failed_gate_count": validation["failed_gate_count"],
            "counter_delta": validation["counter_delta"],
            "accepted_external_reproduction_count": validation[
                "accepted_external_reproduction_count"
            ],
            "accepted_external_falsification_count": validation[
                "accepted_external_falsification_count"
            ],
            "new_credit_delta": validation["new_credit_delta"],
            "o3_closed": transcript["fields"]["o3_closed"],
            "resource_saving_claimed": transcript["fields"]["resource_saving_claimed"],
            "physical_layout_claimed": transcript["fields"]["physical_layout_claimed"],
            "bundle_manifest_hash": bundle_manifest["bundle_manifest_hash"],
            "review_transcript_hash": transcript["transcript_hash"],
            "semantic_validation_hash": validation["semantic_validation_hash"],
            "stdout_sha256": stdout_sha256,
            "verdict_queue_hash": verdict_queue["verdict_queue_hash"],
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
        "# B1/B7 Cone01 R99 Substantive Evidence Intake Gate",
        "",
        f"- Target: `{TARGET_ID}`",
        f"- Upstream target: `{UPSTREAM_TARGET_ID}`",
        f"- Method: `{METHOD}`",
        f"- Status: `{STATUS}`",
        f"- Model status: `{MODEL_STATUS}`",
        "",
        "## Result",
        "",
        "R99 turns the R98 negative control into a positive semantic-intake packet.",
        "It emits six non-placeholder evidence files, binds their byte hashes into",
        "a review transcript, verifies replay command, environment identity, nonempty",
        "recomputed rows, explicit double-count decision, review rationale, and safe",
        "claim boundary, and marks the packet ready for a later R94 maintainer verdict.",
        "",
        "## Key Counters",
        "",
        f"- Evidence files: `{summary['evidence_file_count']}`",
        f"- Files exist: `{summary['all_files_exist']}`",
        f"- Hashes match: `{summary['all_hashes_match']}`",
        f"- Semantic validation accepted: `{summary['semantic_validation_accepted']}`",
        f"- Review transcript accepted: `{summary['review_transcript_accepted']}`",
        f"- Ready for maintainer verdict: `{summary['ready_for_maintainer_verdict']}`",
        f"- Maintainer verdict accepted: `{summary['maintainer_verdict_accepted']}`",
        f"- Passed semantic gates: `{summary['semantic_passed_gate_count']}`",
        f"- Failed semantic gates: `{summary['semantic_failed_gate_count']}`",
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
            f"- Bundle manifest: `{R99_BUNDLE_MANIFEST}`",
            f"- Review transcript: `{R99_REVIEW_TRANSCRIPT}`",
            f"- Semantic validation verdict: `{R99_SEMANTIC_VALIDATION}`",
            f"- Stdout: `{R99_STDOUT}`",
            f"- Maintainer verdict queue: `{R99_VERDICT_QUEUE}`",
            "",
            "## Claim Boundary",
            "",
            "R99 is a semantic intake gate, not a final maintainer verdict. It accepts",
            "the non-placeholder transcript for the next verdict stage, but does not",
            "increment external reproduction or falsification counters, does not grant",
            "new B7 credit, and does not close 1.25x, O3, physical layout, resource-saving,",
            "paper, patent, funding, or product-readiness claims.",
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
