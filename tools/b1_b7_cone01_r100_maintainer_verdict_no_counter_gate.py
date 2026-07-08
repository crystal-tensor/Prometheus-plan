#!/usr/bin/env python3
"""T-B1-004gx/T-B7-016g: R100 maintainer verdict no-counter gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r100_maintainer_verdict_no_counter_gate_v0"
STATUS = "cone01_r100_maintainer_verdict_accepted_no_counter_change"
MODEL_STATUS = "r99_semantic_intake_promoted_to_no_counter_maintainer_verdict"
VERSION = "0.1"
TARGET_ID = "T-B1-004gx/T-B7-016g"
UPSTREAM_TARGET_ID = "T-B1-004gw/T-B7-016f"
SUBMISSION_DIR = "results/B1_B7_cone01_o3_f4_exit_route_submissions"

R99_RESULT = "results/B1_B7_cone01_R99_substantive_evidence_intake_gate_v0.json"
R99_REVIEW_TRANSCRIPT = f"{SUBMISSION_DIR}/R99-G1-substantive-review-transcript.json"
R99_SEMANTIC_VALIDATION = (
    f"{SUBMISSION_DIR}/R99-G1-substantive-evidence-semantic-validation.verdict.json"
)
R99_VERDICT_QUEUE = f"{SUBMISSION_DIR}/R99-G1-maintainer-verdict-ready-queue.json"
R94_VERDICT_CONTRACT = f"{SUBMISSION_DIR}/R94-G1-maintainer-verdict-contract.json"
R94_VERDICT_TEMPLATE = f"{SUBMISSION_DIR}/R94-G1-maintainer-verdict.template.json"

R100_VERDICT = f"{SUBMISSION_DIR}/R100-G1-maintainer-no-counter-verdict.json"
R100_VERDICT_VALIDATION = (
    f"{SUBMISSION_DIR}/R100-G1-maintainer-no-counter-verdict-validation.verdict.json"
)
R100_STDOUT = f"{SUBMISSION_DIR}/R100-G1-maintainer-no-counter-verdict.stdout.txt"
R100_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R100-G1-post-verdict-blocker-queue.json"

RESULT_PATH = "results/B1_B7_cone01_R100_maintainer_verdict_no_counter_gate_v0.json"
REPORT_PATH = "research/B1_B7_cone01_R100_maintainer_verdict_no_counter_gate.md"


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


def build_verdict(
    root: Path,
    r99_result: dict[str, Any],
    r99_transcript: dict[str, Any],
    r99_validation: dict[str, Any],
    r94_contract: dict[str, Any],
    r94_template: dict[str, Any],
) -> dict[str, Any]:
    fields = dict(r94_template["fields"])
    transcript_fields = r99_transcript["fields"]
    fields.update(
        {
            "verdict_id": "R100-G1-maintainer-no-counter-verdict",
            "maintainer_id": "codex-r100-maintainer",
            "source_r93_packet_hash": transcript_fields["reviewed_r93_packet_hash"],
            "source_r93_preflight_hash": r99_validation["semantic_validation_hash"],
            "reviewed_packet_path": transcript_fields["reviewed_r93_packet_path"],
            "reviewed_packet_sha256": transcript_fields["reviewed_r93_packet_sha256"],
            "review_transcript_path": R99_REVIEW_TRANSCRIPT,
            "review_transcript_sha256": file_hash(root / R99_REVIEW_TRANSCRIPT),
            "review_mode": "insufficient_evidence_review",
            "evidence_sufficiency": "insufficient_evidence_no_counter",
            "counter_target": "no_counter_change",
            "counter_delta": 0,
            "credit_decision": "preserve_one_unit_proxy_credit",
            "double_count_decision": "no_duplicate_no_new_credit",
            "one_unit_credit_preserved": True,
            "one_unit_credit_revoked": False,
            "new_credit_delta": 0,
            "accepted_external_reproduction_count_after": 0,
            "accepted_external_falsification_count_after": 0,
            "claim_boundary": (
                "R100 accepts R99 as substantive maintainer-verdict evidence for "
                "a no-counter decision only. It preserves the already reviewed "
                "one-unit proxy FT/STV credit, but does not increment external "
                "reproduction/falsification counters or close B7/O3/resource/layout claims."
            ),
            "o3_closed": False,
            "resource_saving_claimed": False,
            "physical_layout_claimed": False,
            "review_timestamp_unix": 0,
        }
    )
    verdict = {
        "artifact": "R100 G1 maintainer no-counter verdict",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_r99_payload_hash": r99_result["payload_hash"],
        "source_r99_review_transcript_hash": r99_transcript["transcript_hash"],
        "source_r99_semantic_validation_hash": r99_validation["semantic_validation_hash"],
        "source_r94_verdict_contract_hash": r94_contract["verdict_contract_hash"],
        "source_r94_verdict_template_hash": r94_template["verdict_template_hash"],
        "fields": fields,
        "verdict_scope": (
            "No-counter maintainer verdict: accept R99 as substantive evidence for "
            "preserving prior internal proxy credit, while keeping external counters and "
            "all strong solution claims closed."
        ),
    }
    verdict["verdict_hash"] = stable_self_hash(verdict, "verdict_hash")
    return verdict


def validate_verdict(
    root: Path,
    r99_result: dict[str, Any],
    r99_transcript: dict[str, Any],
    r99_validation: dict[str, Any],
    r99_queue: dict[str, Any],
    r94_contract: dict[str, Any],
    verdict: dict[str, Any],
) -> dict[str, Any]:
    fields = verdict["fields"]
    required_fields = r94_contract["required_fields"]
    missing = [field for field in required_fields if fields.get(field) in (None, "")]
    transcript_fields = r99_transcript["fields"]
    reviewed_packet_hash_ok = (
        file_hash(root / transcript_fields["reviewed_r93_packet_path"])
        == transcript_fields["reviewed_r93_packet_sha256"]
    )
    transcript_hash_ok = r99_transcript["transcript_hash"] == r99_result["review_transcript_hash"]
    semantic_hash_ok = (
        r99_validation["semantic_validation_hash"] == r99_result["semantic_validation_hash"]
        and r99_validation["transcript_hash"] == r99_transcript["transcript_hash"]
    )
    queue_hash_ok = r99_queue["verdict_queue_hash"] == r99_result["verdict_queue_hash"]
    gates = {
        "r99_ready_for_maintainer_verdict": r99_result["summary"]["ready_for_maintainer_verdict"]
        is True,
        "r99_semantic_validation_accepted": r99_validation["semantic_validation_accepted"]
        is True,
        "r99_review_transcript_accepted": r99_validation["review_transcript_accepted"] is True,
        "r99_transcript_hash_matches_result": transcript_hash_ok,
        "r99_semantic_hash_matches_result": semantic_hash_ok,
        "r99_verdict_queue_hash_matches_result": queue_hash_ok,
        "reviewed_packet_file_hash_matches_transcript": reviewed_packet_hash_ok,
        "all_r94_required_fields_filled": not missing,
        "verdict_references_r99_transcript_and_semantic_hashes": (
            verdict["source_r99_review_transcript_hash"] == r99_transcript["transcript_hash"]
            and verdict["source_r99_semantic_validation_hash"]
            == r99_validation["semantic_validation_hash"]
        ),
        "no_counter_change": fields["counter_target"] == "no_counter_change"
        and fields["counter_delta"] == 0,
        "external_counters_stay_zero": fields["accepted_external_reproduction_count_after"] == 0
        and fields["accepted_external_falsification_count_after"] == 0,
        "one_unit_proxy_credit_preserved_without_new_credit": fields[
            "one_unit_credit_preserved"
        ]
        is True
        and fields["one_unit_credit_revoked"] is False
        and fields["new_credit_delta"] == 0,
        "claim_boundary_safe": fields["o3_closed"] is False
        and fields["resource_saving_claimed"] is False
        and fields["physical_layout_claimed"] is False,
    }
    failed = [gate for gate, passed in gates.items() if not passed]
    accepted = not failed
    validation = {
        "artifact": "R100 maintainer no-counter verdict validation",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "verdict_hash": verdict["verdict_hash"],
        "r99_payload_hash": r99_result["payload_hash"],
        "r99_review_transcript_hash": r99_transcript["transcript_hash"],
        "r99_semantic_validation_hash": r99_validation["semantic_validation_hash"],
        "gates": gates,
        "passed_gate_count": sum(1 for passed in gates.values() if passed),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "missing_required_fields": missing,
        "maintainer_verdict_accepted": accepted,
        "counter_delta": 0,
        "accepted_external_reproduction_count": 0,
        "accepted_external_falsification_count": 0,
        "new_credit_delta": 0,
        "one_unit_proxy_credit_preserved": accepted,
        "o3_closed": False,
        "resource_saving_claimed": False,
        "physical_layout_claimed": False,
        "claim_boundary": (
            "R100 accepts a no-counter maintainer verdict over R99. This is not an "
            "external reproduction, not a new-credit increment, not a 1.25x close, "
            "and not an O3/resource/layout claim."
        ),
    }
    validation["verdict_validation_hash"] = stable_self_hash(
        validation, "verdict_validation_hash"
    )
    return validation


def build_blocker_queue(validation: dict[str, Any]) -> dict[str, Any]:
    queue = {
        "artifact": "R100 post no-counter verdict blocker queue",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "verdict_validation_hash": validation["verdict_validation_hash"],
        "queue": [
            {
                "blocker_id": "R100-G1-1",
                "priority": 1,
                "target_gate": "clean_clone_independent_rerun",
                "needed_artifact": "independent clean-checkout rerun transcript and environment manifest",
            },
            {
                "blocker_id": "R100-G1-2",
                "priority": 2,
                "target_gate": "external_reproduction_or_falsification_decision",
                "needed_artifact": "third-party decision that can move exactly one external counter",
            },
            {
                "blocker_id": "R100-G1-3",
                "priority": 3,
                "target_gate": "strong_claim_separation",
                "needed_artifact": "separate gate for 1.25x, O3, physical layout, and resource-saving claims",
            },
        ],
    }
    queue["blocker_queue_hash"] = stable_self_hash(queue, "blocker_queue_hash")
    return queue


def write_stdout(root: Path, validation: dict[str, Any], queue: dict[str, Any]) -> str:
    text = "\n".join(
        [
            "R100 maintainer no-counter verdict stdout",
            f"method={METHOD}",
            f"source_target_id={TARGET_ID}",
            f"upstream_target_id={UPSTREAM_TARGET_ID}",
            f"verdict_validation_hash={validation['verdict_validation_hash']}",
            f"blocker_queue_hash={queue['blocker_queue_hash']}",
            f"passed_gate_count={validation['passed_gate_count']}",
            f"failed_gate_count={validation['failed_gate_count']}",
            "maintainer_verdict_accepted=true",
            "counter_delta=0",
            "accepted_external_reproduction_count=0",
            "accepted_external_falsification_count=0",
            "new_credit_delta=0",
            "one_unit_proxy_credit_preserved=true",
            "o3_closed=false",
            "resource_saving_claimed=false",
            "physical_layout_claimed=false",
        ]
    ) + "\n"
    path = root / R100_STDOUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    r99_result = load_json(root / R99_RESULT)
    r99_transcript = load_json(root / R99_REVIEW_TRANSCRIPT)
    r99_validation = load_json(root / R99_SEMANTIC_VALIDATION)
    r99_queue = load_json(root / R99_VERDICT_QUEUE)
    r94_contract = load_json(root / R94_VERDICT_CONTRACT)
    r94_template = load_json(root / R94_VERDICT_TEMPLATE)

    verdict = build_verdict(
        root,
        r99_result,
        r99_transcript,
        r99_validation,
        r94_contract,
        r94_template,
    )
    write_json(root / R100_VERDICT, verdict)
    validation = validate_verdict(
        root,
        r99_result,
        r99_transcript,
        r99_validation,
        r99_queue,
        r94_contract,
        verdict,
    )
    write_json(root / R100_VERDICT_VALIDATION, validation)
    blocker_queue = build_blocker_queue(validation)
    write_json(root / R100_BLOCKER_QUEUE, blocker_queue)
    stdout_sha256 = write_stdout(root, validation, blocker_queue)

    requirements = [
        req(
            "A1",
            "R100 binds accepted R99 semantic intake and verdict queue",
            r99_result["summary"]["source_target_id"] == UPSTREAM_TARGET_ID
            and r99_result["semantic_validation_hash"]
            == r99_validation["semantic_validation_hash"]
            and r99_result["review_transcript_hash"] == r99_transcript["transcript_hash"]
            and r99_result["verdict_queue_hash"] == r99_queue["verdict_queue_hash"],
            {
                "r99_payload_hash": r99_result["payload_hash"],
                "r99_review_transcript_hash": r99_transcript["transcript_hash"],
                "r99_semantic_validation_hash": r99_validation["semantic_validation_hash"],
            },
        ),
        req(
            "A2",
            "R100 emits a complete R94-shaped maintainer verdict",
            validation["gates"]["all_r94_required_fields_filled"]
            and verdict["source_r94_verdict_contract_hash"]
            == r94_contract["verdict_contract_hash"],
            {
                "verdict_hash": verdict["verdict_hash"],
                "missing_required_fields": validation["missing_required_fields"],
            },
        ),
        req(
            "A3",
            "R100 accepts the no-counter maintainer verdict",
            validation["maintainer_verdict_accepted"] is True
            and validation["failed_gate_count"] == 0,
            {
                "verdict_validation_hash": validation["verdict_validation_hash"],
                "passed_gate_count": validation["passed_gate_count"],
            },
        ),
        req(
            "A4",
            "R100 preserves the existing one-unit proxy credit without granting new credit",
            validation["one_unit_proxy_credit_preserved"] is True
            and validation["new_credit_delta"] == 0
            and validation["counter_delta"] == 0,
            {
                "one_unit_proxy_credit_preserved": validation[
                    "one_unit_proxy_credit_preserved"
                ],
                "counter_delta": validation["counter_delta"],
                "new_credit_delta": validation["new_credit_delta"],
            },
        ),
        req(
            "A5",
            "R100 keeps external reproduction and falsification counters at zero",
            validation["accepted_external_reproduction_count"] == 0
            and validation["accepted_external_falsification_count"] == 0,
            {
                "accepted_external_reproduction_count": validation[
                    "accepted_external_reproduction_count"
                ],
                "accepted_external_falsification_count": validation[
                    "accepted_external_falsification_count"
                ],
            },
        ),
        req(
            "A6",
            "R100 keeps O3, resource-saving, and physical-layout claims closed",
            validation["o3_closed"] is False
            and validation["resource_saving_claimed"] is False
            and validation["physical_layout_claimed"] is False,
            {
                "o3_closed": validation["o3_closed"],
                "resource_saving_claimed": validation["resource_saving_claimed"],
                "physical_layout_claimed": validation["physical_layout_claimed"],
            },
        ),
        req(
            "A7",
            "R100 emits blockers for clean rerun, external decision, and strong-claim separation",
            [item["target_gate"] for item in blocker_queue["queue"]]
            == [
                "clean_clone_independent_rerun",
                "external_reproduction_or_falsification_decision",
                "strong_claim_separation",
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
        validation_errors.append("one or more R100 requirements failed")
    if validation["counter_delta"] != 0 or validation["new_credit_delta"] != 0:
        validation_errors.append("R100 must not move counters or new credit")
    if validation["accepted_external_reproduction_count"] != 0:
        validation_errors.append("R100 must not claim external reproduction")
    if validation["accepted_external_falsification_count"] != 0:
        validation_errors.append("R100 must not claim external falsification")

    payload = {
        "artifact": "B1/B7 cone01 R100 maintainer verdict no-counter gate",
        "method": METHOD,
        "version": VERSION,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "generated_at_unix": int(time.time()),
        "verdict_path": R100_VERDICT,
        "verdict_hash": verdict["verdict_hash"],
        "verdict_validation_path": R100_VERDICT_VALIDATION,
        "verdict_validation_hash": validation["verdict_validation_hash"],
        "stdout_path": R100_STDOUT,
        "stdout_sha256": stdout_sha256,
        "blocker_queue_path": R100_BLOCKER_QUEUE,
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
            "maintainer_verdict_accepted": validation["maintainer_verdict_accepted"],
            "passed_gate_count": validation["passed_gate_count"],
            "failed_gate_count": validation["failed_gate_count"],
            "counter_delta": validation["counter_delta"],
            "accepted_external_reproduction_count": validation[
                "accepted_external_reproduction_count"
            ],
            "accepted_external_falsification_count": validation[
                "accepted_external_falsification_count"
            ],
            "new_credit_delta": validation["new_credit_delta"],
            "one_unit_proxy_credit_preserved": validation[
                "one_unit_proxy_credit_preserved"
            ],
            "o3_closed": validation["o3_closed"],
            "resource_saving_claimed": validation["resource_saving_claimed"],
            "physical_layout_claimed": validation["physical_layout_claimed"],
            "verdict_hash": verdict["verdict_hash"],
            "verdict_validation_hash": validation["verdict_validation_hash"],
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
        "# B1/B7 Cone01 R100 Maintainer Verdict No-Counter Gate",
        "",
        f"- Target: `{TARGET_ID}`",
        f"- Upstream target: `{UPSTREAM_TARGET_ID}`",
        f"- Method: `{METHOD}`",
        f"- Status: `{STATUS}`",
        f"- Model status: `{MODEL_STATUS}`",
        "",
        "## Result",
        "",
        "R100 consumes the accepted R99 semantic-intake packet and emits an",
        "R94-shaped maintainer verdict. The verdict is accepted only as a",
        "no-counter decision: it preserves the already reviewed one-unit proxy FT/STV",
        "credit, but does not increment external reproduction or falsification",
        "counters and does not grant new B7 credit.",
        "",
        "## Key Counters",
        "",
        f"- Maintainer verdict accepted: `{summary['maintainer_verdict_accepted']}`",
        f"- Verdict gates passed / failed: `{summary['passed_gate_count']}` / `{summary['failed_gate_count']}`",
        f"- Counter delta: `{summary['counter_delta']}`",
        f"- Accepted external reproductions: `{summary['accepted_external_reproduction_count']}`",
        f"- Accepted external falsifications: `{summary['accepted_external_falsification_count']}`",
        f"- New credit delta: `{summary['new_credit_delta']}`",
        f"- One-unit proxy credit preserved: `{summary['one_unit_proxy_credit_preserved']}`",
        f"- O3/resource/layout claims: `{summary['o3_closed']}` / `{summary['resource_saving_claimed']}` / `{summary['physical_layout_claimed']}`",
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
            f"- Maintainer verdict: `{R100_VERDICT}`",
            f"- Verdict validation: `{R100_VERDICT_VALIDATION}`",
            f"- Stdout: `{R100_STDOUT}`",
            f"- Blocker queue: `{R100_BLOCKER_QUEUE}`",
            "",
            "## Claim Boundary",
            "",
            "R100 is not an external reproduction, not an external falsification, not a",
            "new-credit gate, not a 1.25x closure, and not an O3/resource/layout claim.",
            "It only accepts a no-counter maintainer verdict over R99 and keeps the next",
            "work focused on clean-clone independent rerun and explicit external decision.",
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
