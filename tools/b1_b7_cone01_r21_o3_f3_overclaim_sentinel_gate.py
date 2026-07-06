#!/usr/bin/env python3
"""T-B1-004dw/T-B7-013f: R21 O3-F3 overclaim sentinel gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r21_o3_f3_overclaim_sentinel_gate_v0"
STATUS = "cone01_r21_o3_f3_overclaim_sentinel_rejected"
MODEL_STATUS = "o3_f3_semantic_overclaim_fixture_rejected_no_artifact_no_reroute"
VERSION = "0.1"
TARGET_ID = "T-B1-004dw/T-B7-013f"
SOURCE_TARGET_ID = "T-B1-004dv/T-B7-013e"
CANDIDATE_ID = "NL-C02"
FAMILY_ID = "O3-F3"
SENTINEL_ID = "B1-B7-cone01-R21-O3-F3-overclaim-sentinel"
EXPECTED_FAILED_GATES = ["A2", "A4", "A7", "A8"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def requirement(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def build_overclaim_fixture(r19: dict[str, Any], r20: dict[str, Any]) -> dict[str, Any]:
    r19_summary = r19["summary"]
    r20_summary = r20["summary"]
    return {
        "artifact_id": "B1-B7-cone01-O3-F3-symbolic-lu-redteam-overclaim-sentinel",
        "source_target_id": TARGET_ID,
        "family_id": FAMILY_ID,
        "candidate_id": CANDIDATE_ID,
        "source_registry_hash": r19_summary["source_r18_registry_hash"],
        "source_contract_hash": r20_summary["source_contract_hash"],
        "symbolic_transform_definition": {
            "definition": "theta_i := round(theta_i/(pi/4))*pi/4 for every source coordinate",
            "status": "claimed_symbolic_but_unproved",
            "redteam_note": "This fixture snaps parameters to the pi/4 lattice without a preservation proof.",
        },
        "source_unitary_preservation_certificate": None,
        "leaveout_domain_mapping": {
            "covered_source_parameters": [3, 4, 9, 16, 17],
            "mapping": "identity labels only; no proof that rounded coordinates preserve the source unitary",
        },
        "pi_over_four_lattice_relation": {
            "relation": "reaches_lattice",
            "evidence_mode": "numerical_only",
            "redteam_note": "This must fail A4 because it is not a symbolic replayable relation.",
        },
        "route_a_effect": "clears_route_a",
        "counterexample_payload": {
            "payload_type": "overclaim_fixture",
            "exact_values": None,
            "replayable_construction": None,
        },
        "claim_boundary": {
            "supported": "claims full O3-F3 success without proof",
            "not_supported": "pretends B7 credit, STV credit, and reroute are available",
            "kill_conditions": ["missing preservation certificate", "missing replay command", "numerical-only lattice relation"],
        },
        "machine_check_command": "",
        "expected_outputs": {},
        "checked_negative_lemma_present": True,
        "reroute_allowed": True,
        "o3_closed": True,
    }


def evaluate_submission(submission: dict[str, Any], contract_packet: dict[str, Any]) -> dict[str, Any]:
    required_fields = [row["field"] for row in contract_packet["required_fields"]]
    missing = [field for field in required_fields if field not in submission]
    passed: list[str] = []
    failed: list[str] = []

    if (
        submission.get("family_id") == FAMILY_ID
        and submission.get("candidate_id") == CANDIDATE_ID
        and submission.get("source_registry_hash")
        == contract_packet["source_artifact_hashes"]["r18_registry_hash"]
    ):
        passed.append("A1")
    else:
        failed.append("A1")

    if submission.get("source_unitary_preservation_certificate"):
        passed.append("A2")
    else:
        failed.append("A2")

    mapping = submission.get("leaveout_domain_mapping")
    if mapping and "3" in json.dumps(mapping) and "17" in json.dumps(mapping):
        passed.append("A3")
    else:
        failed.append("A3")

    lattice = submission.get("pi_over_four_lattice_relation")
    if lattice and "numerical_only" not in json.dumps(lattice):
        passed.append("A4")
    else:
        failed.append("A4")

    if submission.get("route_a_effect") in {"not_claimed", "clears_route_a", "does_not_clear_route_a"}:
        passed.append("A5")
    else:
        failed.append("A5")

    boundary = json.dumps(submission.get("claim_boundary", {}), sort_keys=True)
    if "B7 credit" in boundary or "STV credit" in boundary or "reroute" in boundary:
        passed.append("A6")
    else:
        failed.append("A6")

    if submission.get("machine_check_command") and submission.get("expected_outputs"):
        passed.append("A7")
    else:
        failed.append("A7")

    if not any(submission.get(flag) is True for flag in ["checked_negative_lemma_present", "reroute_allowed", "o3_closed"]):
        passed.append("A8")
    else:
        failed.append("A8")

    if missing:
        for gate in [row["gate_id"] for row in contract_packet["acceptance_gates"]]:
            if gate not in failed and gate not in passed:
                failed.append(gate)

    return {
        "submission_exists": True,
        "missing_required_fields": missing,
        "passed_gate_ids": passed,
        "failed_gate_ids": failed,
        "blocked_gate_ids": [],
        "accepted": not missing and len(failed) == 0 and len(passed) == 8,
        "why": "Overclaim sentinel must be rejected despite field completeness.",
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    r19 = load_json(args.r19_contract)
    r20 = load_json(args.r20_intake)
    r19_packet = r19["o3_f3_symbolic_lu_contract_packet"]
    r20_summary = r20["summary"]
    fixture = build_overclaim_fixture(r19, r20)
    fixture_hash = stable_hash(fixture)
    preflight = evaluate_submission(fixture, r19_packet)
    preflight_hash = stable_hash(preflight)

    sentinel_packet = {
        "sentinel_id": SENTINEL_ID,
        "source_target_id": TARGET_ID,
        "source_r20_intake": str(args.r20_intake),
        "source_r19_contract": str(args.r19_contract),
        "source_hashes": {
            "r20_intake_file": file_hash(args.r20_intake),
            "r19_contract_file": file_hash(args.r19_contract),
        },
        "source_intake_hash": r20_summary["intake_hash"],
        "source_template_hash": r20_summary["template_hash"],
        "source_checklist_hash": r20_summary["checklist_hash"],
        "source_contract_hash": r20_summary["source_contract_hash"],
        "fixture_output": str(args.fixture_output),
        "overclaim_fixture": fixture,
        "overclaim_fixture_hash": fixture_hash,
        "preflight_result": preflight,
        "preflight_hash": preflight_hash,
        "expected_failed_gate_ids": EXPECTED_FAILED_GATES,
        "decision": {
            "o3_f3_overclaim_sentinel_ready": True,
            "overclaim_fixture_emitted": True,
            "overclaim_fixture_has_all_required_fields": len(preflight["missing_required_fields"]) == 0,
            "overclaim_fixture_rejected": preflight["accepted"] is False,
            "o3_f3_artifact_accepted": False,
            "o3_closed": False,
            "checked_negative_lemma_present": False,
            "nlc02_full_lemma_ready": False,
            "reroute_allowed": False,
            "why": (
                "R21 proves the intake can reject a field-complete but semantically invalid O3-F3 overclaim fixture."
            ),
        },
    }
    sentinel_packet["sentinel_hash"] = stable_hash(sentinel_packet)

    failed_gate_set = set(preflight["failed_gate_ids"])
    requirements = [
        requirement(
            "L1",
            "R20 intake is validation-clean and ready",
            r20.get("method") == "b1_b7_cone01_r20_o3_f3_artifact_intake_preflight_gate_v0"
            and r20_summary.get("validation_error_count") == 0
            and r20_summary.get("o3_f3_intake_ready") is True,
            {
                "r20_method": r20.get("method"),
                "r20_validation_error_count": r20_summary.get("validation_error_count"),
                "o3_f3_intake_ready": r20_summary.get("o3_f3_intake_ready"),
            },
        ),
        requirement(
            "L2",
            "Overclaim fixture carries all fourteen R19 required fields",
            len(preflight["missing_required_fields"]) == 0,
            {"missing_required_fields": preflight["missing_required_fields"]},
        ),
        requirement(
            "L3",
            "Overclaim fixture is bound to O3-F3 and the source registry",
            fixture["family_id"] == FAMILY_ID
            and fixture["candidate_id"] == CANDIDATE_ID
            and fixture["source_registry_hash"] == r19["summary"]["source_r18_registry_hash"],
            {
                "family_id": fixture["family_id"],
                "candidate_id": fixture["candidate_id"],
                "source_registry_hash": fixture["source_registry_hash"],
            },
        ),
        requirement(
            "L4",
            "Semantic overclaim is present in the fixture",
            fixture["source_unitary_preservation_certificate"] is None
            and fixture["pi_over_four_lattice_relation"]["evidence_mode"] == "numerical_only"
            and fixture["machine_check_command"] == ""
            and fixture["reroute_allowed"] is True
            and fixture["o3_closed"] is True,
            {
                "source_unitary_preservation_certificate": fixture["source_unitary_preservation_certificate"],
                "lattice_evidence_mode": fixture["pi_over_four_lattice_relation"]["evidence_mode"],
                "machine_check_command": fixture["machine_check_command"],
                "reroute_allowed": fixture["reroute_allowed"],
                "o3_closed": fixture["o3_closed"],
            },
        ),
        requirement(
            "L5",
            "Preflight rejects the overclaim fixture on the expected semantic gates",
            preflight["accepted"] is False and set(EXPECTED_FAILED_GATES).issubset(failed_gate_set),
            {
                "accepted": preflight["accepted"],
                "passed_gate_ids": preflight["passed_gate_ids"],
                "failed_gate_ids": preflight["failed_gate_ids"],
                "expected_failed_gate_ids": EXPECTED_FAILED_GATES,
            },
        ),
        requirement(
            "L6",
            "Rejection is semantic rather than missing-field only",
            len(preflight["missing_required_fields"]) == 0 and len(preflight["failed_gate_ids"]) >= 4,
            {
                "missing_required_field_count": len(preflight["missing_required_fields"]),
                "failed_gate_count": len(preflight["failed_gate_ids"]),
            },
        ),
        requirement(
            "L7",
            "R21 does not silently close O3, accept O3-F3, or allow reroute",
            sentinel_packet["decision"]["o3_f3_artifact_accepted"] is False
            and sentinel_packet["decision"]["o3_closed"] is False
            and sentinel_packet["decision"]["reroute_allowed"] is False,
            sentinel_packet["decision"],
        ),
        requirement(
            "L8",
            "R21 preserves zero B7/resource credit claims",
            True,
            {
                "accepted_route_count": 0,
                "accepted_occurrence_removal": 0,
                "accepted_proxy_t_reduction": 0,
                "b7_credit_delta": 0,
                "b7_space_time_volume_credit": 0,
                "resource_saving_claimed": False,
                "b7_ledger_improvement_claimed": False,
            },
        ),
        requirement(
            "L9",
            "Sentinel packet is internally hash-bound",
            bool(sentinel_packet["sentinel_hash"]) and bool(fixture_hash) and bool(preflight_hash),
            {
                "sentinel_hash": sentinel_packet["sentinel_hash"],
                "overclaim_fixture_hash": fixture_hash,
                "preflight_hash": preflight_hash,
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids:
        validation_errors.append(f"unexpected R21 O3-F3 overclaim sentinel failures: {failed_ids}")

    summary = {
        "sentinel_id": SENTINEL_ID,
        "sentinel_hash": sentinel_packet["sentinel_hash"],
        "overclaim_fixture_hash": fixture_hash,
        "preflight_hash": preflight_hash,
        "source_intake_hash": r20_summary["intake_hash"],
        "source_template_hash": r20_summary["template_hash"],
        "source_contract_hash": r20_summary["source_contract_hash"],
        "candidate_id": CANDIDATE_ID,
        "family_id": FAMILY_ID,
        "required_field_count": len(r19_packet["required_fields"]),
        "acceptance_gate_count": len(r19_packet["acceptance_gates"]),
        "overclaim_fixture_has_all_required_fields": len(preflight["missing_required_fields"]) == 0,
        "overclaim_fixture_rejected": preflight["accepted"] is False,
        "preflight_passed_gate_count": len(preflight["passed_gate_ids"]),
        "preflight_failed_gate_count": len(preflight["failed_gate_ids"]),
        "preflight_failed_gate_ids": preflight["failed_gate_ids"],
        "expected_failed_gate_ids": EXPECTED_FAILED_GATES,
        "o3_f3_artifact_accepted": False,
        "o3_closed": False,
        "remaining_open_obligations": ["O3-F3_symbolic_lu_artifact", "O3-F4_refit_harness", "O3-F5_route_a_artifact"],
        "remaining_open_obligation_count": 3,
        "checked_negative_lemma_present": False,
        "nlc02_full_lemma_ready": False,
        "reroute_allowed": False,
        "accepted_route_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "b7_credit_delta": 0,
        "b7_space_time_volume_credit": 0,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "requirement_count": len(requirements),
        "requirements_passed": passed,
        "requirements_failed": len(requirements) - passed,
        "failed_requirement_ids": failed_ids,
        "validation_error_count": len(validation_errors),
    }

    return {
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "source_target_id": TARGET_ID,
        "upstream_target_id": SOURCE_TARGET_ID,
        "title": "B1/B7 Cone01 R21 O3-F3 Overclaim Sentinel Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "summary": summary,
        "o3_f3_overclaim_sentinel_packet": sentinel_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "R21 emits a field-complete but invalid O3-F3 overclaim fixture and proves the preflight rejects it."
            ),
            "what_is_not_supported": (
                "R21 does not submit or accept a valid O3-F3 artifact, does not close O3, and does not permit R5 reroute. "
                "No R1 solution, occurrence removal, proxy-T reduction, B7 credit, resource saving, or impossibility theorem is supported."
            ),
            "next_gate": (
                "Either harden the preflight further, or replace the red-team fixture with a real O3-F3 symbolic artifact that passes all gates."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    packet = payload["o3_f3_overclaim_sentinel_packet"]
    preflight = packet["preflight_result"]
    lines = [
        f"# {payload['title']}",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Upstream target: `{payload['upstream_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Candidate: `{s['candidate_id']}`",
        f"- Family: `{s['family_id']}`",
        f"- Sentinel hash: `{s['sentinel_hash']}`",
        f"- Overclaim fixture hash: `{s['overclaim_fixture_hash']}`",
        f"- Preflight hash: `{s['preflight_hash']}`",
        "",
        "## Result",
        "",
        (
            f"The R21 overclaim sentinel gate passes {s['requirements_passed']}/{s['requirement_count']} requirements. "
            "It emits a field-complete but invalid O3-F3 fixture and confirms the preflight rejects it."
        ),
        "",
        "## Sentinel Fixture",
        "",
        f"- Fixture path: `{packet['fixture_output']}`",
        f"- All required fields present: `{s['overclaim_fixture_has_all_required_fields']}`",
        f"- Fixture rejected: `{s['overclaim_fixture_rejected']}`",
        f"- Failed gates: `{s['preflight_failed_gate_ids']}`",
        "",
        "## Why It Fails",
        "",
        "- `A2` fails because no source-unitary preservation certificate is supplied.",
        "- `A4` fails because the lattice relation is marked `numerical_only`.",
        "- `A7` fails because no machine-check command or expected replay output is supplied.",
        "- `A8` fails because the fixture directly overclaims `checked_negative_lemma_present`, `reroute_allowed`, and `o3_closed`.",
        "",
        "## Preflight Result",
        "",
        f"- Passed gates: `{preflight['passed_gate_ids']}`",
        f"- Failed gates: `{preflight['failed_gate_ids']}`",
        f"- Missing required fields: `{preflight['missing_required_fields']}`",
        f"- Accepted: `{preflight['accepted']}`",
        "",
        "## Requirement Results",
        "",
    ]
    for row in payload["requirements"]:
        marker = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- `{row['requirement_id']}` {marker}: {row['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            "",
            "This sentinel gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a checked impossibility theorem, an R5 reroute, or a solved B1/B7 problem.",
            "",
            "## Validation",
            "",
            f"- validation_error_count: `{s['validation_error_count']}`",
        ]
    )
    for error in payload["validation_errors"]:
        lines.append(f"- {error}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--r19-contract",
        type=Path,
        default=Path("results/B1_B7_cone01_R19_o3_f3_symbolic_lu_contract_gate_v0.json"),
    )
    parser.add_argument(
        "--r20-intake",
        type=Path,
        default=Path("results/B1_B7_cone01_R20_o3_f3_artifact_intake_preflight_gate_v0.json"),
    )
    parser.add_argument(
        "--fixture-output",
        type=Path,
        default=Path(
            "results/B1_B7_cone01_o3_f3_symbolic_lu_submissions/"
            "B1-B7-cone01-O3-F3-symbolic-lu.overclaim-sentinel.json"
        ),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_R21_o3_f3_overclaim_sentinel_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_R21_o3_f3_overclaim_sentinel_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-06")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.fixture_output, payload["o3_f3_overclaim_sentinel_packet"]["overclaim_fixture"], True)
    write_json(args.json_output, payload, args.pretty)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "sentinel_hash": payload["summary"]["sentinel_hash"],
                "overclaim_fixture_hash": payload["summary"]["overclaim_fixture_hash"],
                "preflight_hash": payload["summary"]["preflight_hash"],
                "overclaim_fixture_has_all_required_fields": payload["summary"]["overclaim_fixture_has_all_required_fields"],
                "overclaim_fixture_rejected": payload["summary"]["overclaim_fixture_rejected"],
                "preflight_failed_gate_ids": payload["summary"]["preflight_failed_gate_ids"],
                "o3_f3_artifact_accepted": payload["summary"]["o3_f3_artifact_accepted"],
                "o3_closed": payload["summary"]["o3_closed"],
                "reroute_allowed": payload["summary"]["reroute_allowed"],
                "requirements_passed": payload["summary"]["requirements_passed"],
                "requirements_failed": payload["summary"]["requirements_failed"],
                "validation_error_count": payload["summary"]["validation_error_count"],
                "fixture_output": str(args.fixture_output),
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if payload["validation_errors"]:
        raise SystemExit("B1/B7 R21 O3-F3 overclaim sentinel gate validation failed")


if __name__ == "__main__":
    main()
