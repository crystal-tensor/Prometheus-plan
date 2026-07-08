#!/usr/bin/env python3
"""T-B1-004fw/T-B7-015f: R73 R1/R2 source-closure intake gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r73_r1_r2_source_closure_intake_gate_v0"
STATUS = "cone01_r73_r1_r2_source_closure_intake_ready_zero_credit"
MODEL_STATUS = "r72_blockers_are_converted_into_source_backed_intake_contract"
VERSION = "0.1"
TARGET_ID = "T-B1-004fw/T-B7-015f"
UPSTREAM_TARGET_ID = "T-B1-004fv/T-B7-015e"
SUBMISSION_DIR = "results/B1_B7_cone01_o3_f4_exit_route_submissions"
R72_RESULT = "results/B1_B7_cone01_R72_source_backed_delta_preflight_gate_v0.json"
R72_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R72-source-backed-delta-blocker-queue.json"
R72_CANDIDATE = f"{SUBMISSION_DIR}/R72-R1-source-backed-positive-delta-candidate.json"
R73_CONTRACT = f"{SUBMISSION_DIR}/R73-r1-r2-source-closure-intake.contract.json"
R73_TEMPLATE = f"{SUBMISSION_DIR}/R73-r1-r2-source-closure-intake.template.json"
R73_FIXTURE = f"{SUBMISSION_DIR}/R73-metadata-only-source-closure.fixture.json"
R73_VERDICT = f"{SUBMISSION_DIR}/R73-metadata-only-source-closure.verdict.json"
R73_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R73-source-closure-blocker-queue.json"


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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


def build_contract(root: Path, r72: dict[str, Any], blocker_queue: dict[str, Any]) -> dict[str, Any]:
    closure_packets = [
        {
            "packet_id": "R73-D1-line1381-source-backed-occurrence",
            "source_blocker_id": "R72-D1",
            "target_failed_gates": [
                "r1_packet_requirements_all_pass",
                "r1_submitted_source_backed_artifact_exists",
                "r1_accepted_occurrence_positive",
            ],
            "required_fields": [
                "r1_source_artifact_path",
                "r1_source_artifact_sha256",
                "r1_replay_command",
                "r1_replay_stdout_path",
                "r1_replay_stdout_sha256",
                "r1_selected_lines",
                "r1_occurrence_removed_lines",
                "r1_occurrence_delta_derivation",
                "r1_replay_verdict_path",
                "r1_replay_verdict_sha256",
                "r1_claim_boundary",
            ],
            "acceptance_rule": (
                "The R1 artifact must replay from source/candidate circuits, remove at least one "
                "accepted occurrence, and close R1 P6/P7/P8 without claiming B7 credit."
            ),
        },
        {
            "packet_id": "R73-D2-line1381-source-backed-proxy-t",
            "source_blocker_id": "R72-D2",
            "target_failed_gates": [
                "r1_accepted_proxy_t_positive",
                "ledger_positive_values_not_metadata_only",
            ],
            "required_fields": [
                "proxy_t_derivation_artifact_path",
                "proxy_t_derivation_artifact_sha256",
                "proxy_t_before",
                "proxy_t_after",
                "proxy_t_delta",
                "proxy_t_pricing_model_path",
                "proxy_t_pricing_model_sha256",
                "proxy_t_replay_command",
                "proxy_t_replay_stdout_path",
                "proxy_t_replay_stdout_sha256",
                "proxy_t_claim_boundary",
            ],
            "acceptance_rule": (
                "The proxy-T delta must be derived from a source-backed pricing model and replay, "
                "not from a metadata-only positive integer."
            ),
        },
        {
            "packet_id": "R73-D3-line1378-source-backed-no-double-counting",
            "source_blocker_id": "R72-D3",
            "target_failed_gates": [
                "r2_packet_requirements_all_pass",
                "r2_submitted_source_backed_artifact_exists",
                "r2_no_double_counting_recovery_valid",
            ],
            "required_fields": [
                "r2_source_artifact_path",
                "r2_source_artifact_sha256",
                "r2_replay_command",
                "r2_replay_stdout_path",
                "r2_replay_stdout_sha256",
                "line1378_recovery_or_exclusion_decision",
                "line1378_overlap_window",
                "line1381_window",
                "no_double_counting_ledger_path",
                "no_double_counting_ledger_sha256",
                "r2_claim_boundary",
            ],
            "acceptance_rule": (
                "The R2 artifact must either recover line1378 or prove it is excluded from the "
                "line1381 count, with a hash-bound no-double-counting ledger."
            ),
        },
    ]
    contract = {
        "contract_id": "B1-B7-cone01-R73-r1-r2-source-closure-intake",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_r72_result": R72_RESULT,
        "source_r72_result_sha256": file_hash(root / R72_RESULT),
        "source_r72_payload_hash": r72["summary"]["payload_hash"],
        "source_r72_blocker_queue": R72_BLOCKER_QUEUE,
        "source_r72_blocker_queue_sha256": file_hash(root / R72_BLOCKER_QUEUE),
        "source_r72_blocker_queue_hash": blocker_queue["blocker_queue_hash"],
        "closure_packets": closure_packets,
        "required_packet_count": len(closure_packets),
        "required_field_count": sum(len(packet["required_fields"]) for packet in closure_packets),
        "forbidden_shortcuts": [
            "using R72 metadata-positive values as source-backed closure evidence",
            "using structural CNOT delta alone as occurrence or proxy-T evidence",
            "counting line1378 and line1381 overlap twice",
            "requesting B7 nonzero credit before R1/R2 closure and R72 hardened preflight pass",
            "claiming O3 closure or reroute permission from an intake packet",
        ],
    }
    contract["contract_hash"] = stable_hash(contract)
    return contract


def build_template(contract: dict[str, Any]) -> dict[str, Any]:
    template = {
        "submission_id": "B1-B7-cone01-R73-r1-r2-source-closure-submission",
        "source_contract_hash": contract["contract_hash"],
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "accepted_exit_route_count": None,
        "occurrence_removal_delta": None,
        "proxy_t_reduction_delta": None,
        "b7_nonzero_retest_requested": False,
        "packets": {},
        "claim_boundary": (
            "Template only. Fill all R73 D1-D3 source-backed packets, rerun this intake, "
            "then rerun R72 hardened preflight. Do not claim B7 credit here."
        ),
    }
    for packet in contract["closure_packets"]:
        template["packets"][packet["packet_id"]] = {
            field: None for field in packet["required_fields"]
        }
    template["template_hash"] = stable_hash(template)
    return template


def build_metadata_only_fixture(
    template: dict[str, Any], r72_candidate: dict[str, Any]
) -> dict[str, Any]:
    fixture = json.loads(json.dumps(template))
    fixture.update(
        {
            "submission_id": "B1-B7-cone01-R73-metadata-only-source-closure-fixture",
            "accepted_exit_route_count": 1,
            "occurrence_removal_delta": 1,
            "proxy_t_reduction_delta": 1,
            "claim_boundary": (
                "Rejected fixture. It copies R72 positive metadata but does not provide "
                "source-backed R1/R2 closure artifacts and must not be used for B7 credit."
            ),
        }
    )
    fixture["packets"]["R73-D1-line1381-source-backed-occurrence"].update(
        {
            "r1_selected_lines": r72_candidate["selected_lines"],
            "r1_occurrence_removed_lines": [1381],
            "r1_occurrence_delta_derivation": r72_candidate["occurrence_delta_derivation"],
            "r1_claim_boundary": fixture["claim_boundary"],
        }
    )
    fixture["packets"]["R73-D2-line1381-source-backed-proxy-t"].update(
        {
            "proxy_t_before": 1,
            "proxy_t_after": 0,
            "proxy_t_delta": 1,
            "proxy_t_claim_boundary": fixture["claim_boundary"],
        }
    )
    fixture["packets"]["R73-D3-line1378-source-backed-no-double-counting"].update(
        {
            "line1378_recovery_or_exclusion_decision": "metadata_only_not_source_backed",
            "line1378_overlap_window": [1369, 1377],
            "line1381_window": [1369, 1379],
            "r2_claim_boundary": fixture["claim_boundary"],
        }
    )
    fixture["fixture_hash"] = stable_hash(fixture)
    return fixture


def verify_submission(root: Path, submission: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    missing_by_packet: dict[str, list[str]] = {}
    hash_failures: list[str] = []
    for packet in contract["closure_packets"]:
        packet_id = packet["packet_id"]
        row = submission.get("packets", {}).get(packet_id, {})
        missing = [
            field for field in packet["required_fields"] if row.get(field) in (None, "")
        ]
        missing_by_packet[packet_id] = missing
        for field in packet["required_fields"]:
            if not field.endswith("_sha256"):
                continue
            path_field = field[:-7] + "path"
            if path_field in row and row.get(path_field) not in (None, ""):
                if not path_hash_matches(root, row.get(path_field), row.get(field)):
                    hash_failures.append(field)

    d1 = submission.get("packets", {}).get("R73-D1-line1381-source-backed-occurrence", {})
    d2 = submission.get("packets", {}).get("R73-D2-line1381-source-backed-proxy-t", {})
    d3 = submission.get("packets", {}).get("R73-D3-line1378-source-backed-no-double-counting", {})
    occurrence_derivation = str(d1.get("r1_occurrence_delta_derivation", ""))
    proxy_t_delta = d2.get("proxy_t_delta")
    proxy_t_before = d2.get("proxy_t_before")
    proxy_t_after = d2.get("proxy_t_after")
    gates = {
        "source_contract_hash_matches": submission.get("source_contract_hash")
        == contract["contract_hash"],
        "all_required_fields_complete": all(not missing for missing in missing_by_packet.values()),
        "all_hash_bound_artifacts_exist": hash_failures == []
        and all(
            path_hash_matches(
                root,
                submission.get("packets", {}).get(packet["packet_id"], {}).get(field[:-7] + "path"),
                submission.get("packets", {}).get(packet["packet_id"], {}).get(field),
            )
            for packet in contract["closure_packets"]
            for field in packet["required_fields"]
            if field.endswith("_sha256")
        ),
        "r1_occurrence_delta_source_backed": (
            isinstance(d1.get("r1_occurrence_removed_lines"), list)
            and len(d1.get("r1_occurrence_removed_lines", [])) >= 1
            and "Preflight candidate only" not in occurrence_derivation
            and d1.get("r1_source_artifact_path") not in (None, "")
        ),
        "proxy_t_delta_source_backed": (
            isinstance(proxy_t_before, int)
            and isinstance(proxy_t_after, int)
            and isinstance(proxy_t_delta, int)
            and proxy_t_before - proxy_t_after == proxy_t_delta
            and proxy_t_delta >= 1
            and d2.get("proxy_t_derivation_artifact_path") not in (None, "")
        ),
        "r2_no_double_counting_source_backed": (
            d3.get("line1378_recovery_or_exclusion_decision")
            in {"recovered", "excluded_from_line1381_count"}
            and d3.get("no_double_counting_ledger_path") not in (None, "")
        ),
        "b7_not_requested_before_closure": submission.get("b7_nonzero_retest_requested") is False,
        "claim_boundary_blocks_b7": "b7 credit" in str(submission.get("claim_boundary", "")).lower()
        and "not" in str(submission.get("claim_boundary", "")).lower(),
    }
    failed = [gate for gate, passed in gates.items() if not passed]
    verdict = {
        "artifact": "R73 R1/R2 source-closure intake verdict",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "submission_id": submission.get("submission_id"),
        "gates": gates,
        "passed_gate_count": sum(1 for passed in gates.values() if passed),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "missing_by_packet": missing_by_packet,
        "hash_failures": hash_failures,
        "accepted": failed == [],
        "accepted_exit_route_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "b7_credit_delta": 0,
    }
    verdict["verdict_hash"] = stable_hash(verdict)
    return verdict


def build_blocker_queue(verdict: dict[str, Any]) -> dict[str, Any]:
    queue = {
        "artifact": "R73 source-closure blocker queue",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "failed_gates": verdict["failed_gates"],
        "queue": [
            {
                "blocker_id": "R73-C1",
                "priority": 1,
                "needed_artifact": "source-backed R1 occurrence artifact with replay stdout and verdict hash",
            },
            {
                "blocker_id": "R73-C2",
                "priority": 2,
                "needed_artifact": "source-backed proxy-T pricing derivation and replay transcript",
            },
            {
                "blocker_id": "R73-C3",
                "priority": 3,
                "needed_artifact": "source-backed line1378 recovery or exclusion ledger",
            },
        ],
    }
    queue["blocker_queue_hash"] = stable_hash(queue)
    return queue


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    r72 = load_json(root / R72_RESULT)
    r72_queue = load_json(root / R72_BLOCKER_QUEUE)
    r72_candidate = load_json(root / R72_CANDIDATE)

    contract = build_contract(root, r72, r72_queue)
    write_json(root / R73_CONTRACT, contract)
    template = build_template(contract)
    write_json(root / R73_TEMPLATE, template)
    fixture = build_metadata_only_fixture(template, r72_candidate)
    write_json(root / R73_FIXTURE, fixture)
    verdict = verify_submission(root, fixture, contract)
    write_json(root / R73_VERDICT, verdict)
    blocker_queue = build_blocker_queue(verdict)
    write_json(root / R73_BLOCKER_QUEUE, blocker_queue)

    requirements = [
        req(
            "I1",
            "R73 consumes the R72 source-backed blocker queue",
            contract["source_r72_blocker_queue_hash"] == r72_queue["blocker_queue_hash"],
            {"r72_blocker_queue_hash": r72_queue["blocker_queue_hash"]},
        ),
        req(
            "I2",
            "intake contract maps all three R72 blockers to closure packets",
            contract["required_packet_count"] == 3
            and {p["source_blocker_id"] for p in contract["closure_packets"]}
            == {"R72-D1", "R72-D2", "R72-D3"},
            {"required_packet_count": contract["required_packet_count"]},
        ),
        req(
            "I3",
            "template exposes every required source-backed field",
            contract["required_field_count"] == 33
            and all(
                field in template["packets"][packet["packet_id"]]
                for packet in contract["closure_packets"]
                for field in packet["required_fields"]
            ),
            {"required_field_count": contract["required_field_count"]},
        ),
        req(
            "I4",
            "metadata-only fixture is rejected",
            verdict["accepted"] is False and verdict["failed_gate_count"] >= 5,
            {"failed_gates": verdict["failed_gates"]},
        ),
        req(
            "I5",
            "fixture rejection names missing source-backed artifacts",
            "all_required_fields_complete" in verdict["failed_gates"]
            and "all_hash_bound_artifacts_exist" in verdict["failed_gates"],
            {"missing_by_packet": verdict["missing_by_packet"]},
        ),
        req(
            "I6",
            "R73 keeps all accepted deltas and B7 credit at zero",
            verdict["accepted_exit_route_count"] == 0
            and verdict["accepted_occurrence_removal"] == 0
            and verdict["accepted_proxy_t_reduction"] == 0
            and verdict["b7_credit_delta"] == 0,
            {
                "accepted_exit_route_count": verdict["accepted_exit_route_count"],
                "accepted_occurrence_removal": verdict["accepted_occurrence_removal"],
                "accepted_proxy_t_reduction": verdict["accepted_proxy_t_reduction"],
                "b7_credit_delta": verdict["b7_credit_delta"],
            },
        ),
        req(
            "I7",
            "R73 emits a source-closure blocker queue",
            len(blocker_queue["queue"]) == 3,
            {"blocker_queue_hash": blocker_queue["blocker_queue_hash"]},
        ),
        req(
            "I8",
            "R73 does not claim O3 closure, reroute, or resource savings",
            True,
            {"o3_closed": False, "reroute_allowed": False, "resource_saving_claimed": False},
        ),
    ]
    summary = {
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "template_hash": template["template_hash"],
        "metadata_only_fixture_hash": fixture["fixture_hash"],
        "metadata_only_verdict_hash": verdict["verdict_hash"],
        "required_packet_count": contract["required_packet_count"],
        "required_field_count": contract["required_field_count"],
        "metadata_only_fixture_accepted": verdict["accepted"],
        "metadata_only_failed_gate_count": verdict["failed_gate_count"],
        "metadata_only_failed_gates": verdict["failed_gates"],
        "accepted_exit_route_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "b7_nonzero_retest_allowed": False,
        "b7_credit_delta": 0,
        "o3_closed": False,
        "reroute_allowed": False,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
        "requirement_count": len(requirements),
        "requirements_passed": sum(1 for item in requirements if item["passed"]),
        "requirements_failed": sum(1 for item in requirements if not item["passed"]),
        "failed_requirement_ids": [
            item["requirement_id"] for item in requirements if not item["passed"]
        ],
        "validation_error_count": sum(1 for item in requirements if not item["passed"]),
    }
    payload = {
        "title": "B1/B7 Cone01 R73 R1/R2 Source-Closure Intake Gate",
        "version": VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "summary": summary,
        "requirements": requirements,
        "contract": contract,
        "metadata_only_verdict": verdict,
        "claim_boundary": {
            "what_is_supported": (
                "R73 converts the R72 D1-D3 blockers into source-backed intake "
                "requirements and proves metadata-only closure is rejected."
            ),
            "what_is_not_supported": (
                "R73 does not close R1 or R2, does not accept the positive-delta row, "
                "and does not grant B7 credit."
            ),
            "next_gate": (
                "Submit source-backed R1 occurrence, R1 proxy-T, and R2 no-double-counting "
                "artifacts against the R73 template, then rerun R73 and R72."
            ),
        },
        "artifacts": {
            "contract": R73_CONTRACT,
            "template": R73_TEMPLATE,
            "metadata_only_fixture": R73_FIXTURE,
            "metadata_only_verdict": R73_VERDICT,
            "blocker_queue": R73_BLOCKER_QUEUE,
        },
    }
    payload["summary"]["payload_hash"] = stable_hash(payload)
    return payload


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    s = payload["summary"]
    lines = [
        "# B1/B7 Cone01 R73 R1/R2 Source-Closure Intake Gate",
        "",
        "## Summary",
        "",
        f"- Status: `{s['status']}`",
        f"- Required closure packets: `{s['required_packet_count']}`",
        f"- Required source-backed fields: `{s['required_field_count']}`",
        f"- Metadata-only fixture accepted: `{s['metadata_only_fixture_accepted']}`",
        f"- Metadata-only failed gates: `{s['metadata_only_failed_gate_count']}`",
        f"- Accepted exit routes: `{s['accepted_exit_route_count']}`",
        f"- Accepted occurrence removal: `{s['accepted_occurrence_removal']}`",
        f"- Accepted proxy-T reduction: `{s['accepted_proxy_t_reduction']}`",
        f"- B7 credit delta: `{s['b7_credit_delta']}`",
        f"- Contract hash: `{s['contract_hash']}`",
        f"- Blocker queue hash: `{s['blocker_queue_hash']}`",
        "",
        "R73 turns the R72 D1-D3 blockers into an intake contract. It does not solve R1 or R2; it defines the exact source-backed evidence shape required before R72 can be rerun honestly.",
        "",
        "## Failed Gates For Metadata-Only Fixture",
        "",
    ]
    for gate in s["metadata_only_failed_gates"]:
        lines.append(f"- `{gate}`")
    lines.extend(["", "## Requirements", ""])
    for item in payload["requirements"]:
        status = "PASS" if item["passed"] else "FAIL"
        lines.append(f"- `{item['requirement_id']}` {status}: {item['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            "",
            "## Artifacts",
            "",
        ]
    )
    for label, artifact_path in payload["artifacts"].items():
        lines.append(f"- `{label}`: `{artifact_path}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--json-output",
        default="results/B1_B7_cone01_R73_r1_r2_source_closure_intake_gate_v0.json",
    )
    parser.add_argument(
        "--markdown-output",
        default="research/B1_B7_cone01_R73_r1_r2_source_closure_intake_gate.md",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    root = Path(args.repo_root).resolve()
    write_json(root / args.json_output, payload)
    write_markdown(root / args.markdown_output, payload)
    if args.pretty:
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
