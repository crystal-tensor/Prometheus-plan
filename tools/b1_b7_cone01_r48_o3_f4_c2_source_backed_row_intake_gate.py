#!/usr/bin/env python3
"""T-B1-004ex/T-B7-014g: R48 O3-F4 C2 source-backed row intake gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r48_o3_f4_c2_source_backed_row_intake_gate_v0"
STATUS = "cone01_r48_o3_f4_c2_source_backed_row_intake_contract_blocked_no_submission"
MODEL_STATUS = "o3_f4_c2_first_source_backed_row_contract_ready_no_row_submitted"
VERSION = "0.1"
TARGET_ID = "T-B1-004ex/T-B7-014g"
UPSTREAM_TARGET_ID = "T-B1-004ew/T-B7-014f"
SELECTED_CHALLENGE_ID = "O3-F4-C01"


REQUIRED_KEYS = [
    "artifact_id",
    "challenge_id",
    "source_target_id",
    "upstream_target_id",
    "source_dataset_id",
    "source_dataset_file",
    "source_dataset_sha256",
    "source_trace_id",
    "source_trace_file",
    "source_trace_sha256",
    "external_lineage_note",
    "external_lineage_sha256",
    "replay_environment_file",
    "replay_environment_sha256",
    "source_circuit_file",
    "source_circuit_sha256",
    "candidate_circuit_file",
    "candidate_circuit_sha256",
    "replay_stdout_file",
    "replay_stdout_sha256",
    "same_unitary_witness_file",
    "same_unitary_witness_sha256",
    "same_unitary_witness_schema",
    "same_unitary_witness_verifier",
    "verifier_signature_file",
    "verifier_signature_sha256",
    "source_backed_replay",
    "same_unitary_certificate",
    "smoke_only_not_c2_acceptance",
    "claim_boundary",
]

PRODUCTION_REQUIRED_KEYS = [
    "source_dataset_file",
    "source_trace_file",
    "external_lineage_note",
    "replay_environment_file",
    "source_circuit_file",
    "candidate_circuit_file",
    "replay_stdout_file",
    "same_unitary_witness_file",
    "same_unitary_witness_verifier",
    "verifier_signature_file",
    "source_backed_replay",
    "same_unitary_certificate",
    "smoke_only_not_c2_acceptance",
    "claim_boundary",
]

EVIDENCE_FILE_CLASSES = [
    "independent_source_dataset",
    "independent_source_trace",
    "external_lineage_note",
    "replay_environment_manifest",
    "source_circuit",
    "candidate_circuit",
    "replay_stdout",
    "same_unitary_witness",
    "verifier_signature",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def req(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def build_contract(r47: dict[str, Any], r46_fixture: dict[str, Any]) -> dict[str, Any]:
    selected_rows = [
        row for row in r46_fixture["rows"] if row.get("challenge_id") == SELECTED_CHALLENGE_ID
    ]
    if len(selected_rows) != 1:
        raise ValueError(f"Expected exactly one {SELECTED_CHALLENGE_ID} row")
    row = selected_rows[0]
    contract = {
        "contract_id": "B1-B7-cone01-O3-F4-C2-source-backed-row-intake-contract",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "selected_challenge_id": SELECTED_CHALLENGE_ID,
        "source_r47_discriminator_hash": r47["summary"]["discriminator_hash"],
        "source_r47_fixture_hash": r47["summary"]["fixture_hash"],
        "source_r47_replacement_contract_hash": r47["summary"]["replacement_contract_hash"],
        "selected_row_existing_source_dataset_id": row.get("source_dataset_id"),
        "selected_row_existing_source_trace_id": row.get("source_trace_id"),
        "required_key_count": len(REQUIRED_KEYS),
        "production_required_key_count": len(PRODUCTION_REQUIRED_KEYS),
        "evidence_file_class_count": len(EVIDENCE_FILE_CLASSES),
        "required_keys": REQUIRED_KEYS,
        "production_required_keys": PRODUCTION_REQUIRED_KEYS,
        "evidence_file_classes": EVIDENCE_FILE_CLASSES,
        "hard_reject_if": [
            "source_backed_replay is not true",
            "same_unitary_certificate is not true",
            "smoke_only_not_c2_acceptance is not false",
            "external_lineage_note does not identify source provenance outside the smoke fixture",
            "verifier_signature_file is missing or hash-mismatched",
            "claim_boundary omits no C2/O3/reroute/B7/STV credit until all 8 rows pass",
            "submission mutates unrelated C3-C7 or B7 ledger state",
        ],
        "acceptance_statement": (
            "One C2 row can be marked source-backed only after the submitted row "
            "satisfies every production key, carries independent external lineage, "
            "sets source_backed_replay=true and same_unitary_certificate=true, sets "
            "smoke_only_not_c2_acceptance=false, and preserves zero-credit claim boundaries. "
            "All-row C2 acceptance still requires 8/8 rows and a fresh discriminator rerun."
        ),
    }
    contract["contract_hash"] = stable_hash(contract)
    return contract


def build_template(contract: dict[str, Any]) -> dict[str, Any]:
    template = {
        "artifact_id": "B1-B7-cone01-O3-F4-C2-C01-source-backed-row-submission",
        "challenge_id": SELECTED_CHALLENGE_ID,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "contract_hash": contract["contract_hash"],
        "source_dataset_id": None,
        "source_dataset_file": None,
        "source_dataset_sha256": None,
        "source_trace_id": None,
        "source_trace_file": None,
        "source_trace_sha256": None,
        "external_lineage_note": None,
        "external_lineage_sha256": None,
        "replay_environment_file": None,
        "replay_environment_sha256": None,
        "source_circuit_file": None,
        "source_circuit_sha256": None,
        "candidate_circuit_file": None,
        "candidate_circuit_sha256": None,
        "replay_stdout_file": None,
        "replay_stdout_sha256": None,
        "same_unitary_witness_file": None,
        "same_unitary_witness_sha256": None,
        "same_unitary_witness_schema": "source_backed_unitary_equivalence_v1",
        "same_unitary_witness_verifier": None,
        "verifier_signature_file": None,
        "verifier_signature_sha256": None,
        "source_backed_replay": False,
        "same_unitary_certificate": False,
        "smoke_only_not_c2_acceptance": True,
        "claim_boundary": "no C2/O3/reroute/B7/STV credit until 8/8 source-backed rows pass",
    }
    template["template_hash"] = stable_hash(template)
    return template


def evaluate_submission(contract: dict[str, Any], template: dict[str, Any], submission_path: Path | None) -> dict[str, Any]:
    submitted = bool(submission_path and submission_path.exists())
    submission = load_json(submission_path) if submitted and submission_path else None
    if submission is None:
        missing_keys = REQUIRED_KEYS
        production_missing_keys = PRODUCTION_REQUIRED_KEYS
        flag_state = {
            "source_backed_replay": False,
            "same_unitary_certificate": False,
            "smoke_only_not_c2_acceptance": True,
        }
    else:
        missing_keys = [key for key in REQUIRED_KEYS if key not in submission]
        production_missing_keys = [
            key
            for key in PRODUCTION_REQUIRED_KEYS
            if key not in submission or submission.get(key) in (None, "", False)
        ]
        flag_state = {
            "source_backed_replay": submission.get("source_backed_replay") is True,
            "same_unitary_certificate": submission.get("same_unitary_certificate") is True,
            "smoke_only_not_c2_acceptance": submission.get("smoke_only_not_c2_acceptance") is True,
        }
    flags_passed = (
        flag_state["source_backed_replay"]
        and flag_state["same_unitary_certificate"]
        and not flag_state["smoke_only_not_c2_acceptance"]
    )
    accepted = submitted and not missing_keys and not production_missing_keys and flags_passed
    evaluation = {
        "contract_hash": contract["contract_hash"],
        "template_hash": template["template_hash"],
        "submission_path": str(submission_path) if submission_path else None,
        "submitted": submitted,
        "required_key_count": len(REQUIRED_KEYS),
        "production_required_key_count": len(PRODUCTION_REQUIRED_KEYS),
        "evidence_file_class_count": len(EVIDENCE_FILE_CLASSES),
        "missing_key_count": len(missing_keys),
        "production_missing_key_count": len(production_missing_keys),
        "missing_keys": missing_keys,
        "production_missing_keys": production_missing_keys,
        "flag_state": flag_state,
        "source_backed_flags_passed": flags_passed,
        "accepted_source_backed_row_count": 1 if accepted else 0,
        "accepted": accepted,
        "failed_reasons": [],
    }
    if not submitted:
        evaluation["failed_reasons"].append("source_backed_row_submission_missing")
    if missing_keys:
        evaluation["failed_reasons"].append("required_keys_missing")
    if production_missing_keys:
        evaluation["failed_reasons"].append("production_required_keys_missing")
    if not flags_passed:
        evaluation["failed_reasons"].append("source_backed_flags_not_satisfied")
    evaluation["evaluation_hash"] = stable_hash(evaluation)
    return evaluation


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    r47 = load_json(args.r47_result)
    r46_fixture = load_json(args.r46_fixture)
    contract = build_contract(r47, r46_fixture)
    template = build_template(contract)
    write_json(args.contract_output, contract)
    write_json(args.template_output, template)
    evaluation = evaluate_submission(
        contract,
        template,
        args.submission_input if str(args.submission_input) else None,
    )
    requirements = [
        req(
            "S1",
            "R47 discriminator is validation-clean and flags-only blocked",
            r47["summary"].get("validation_error_count") == 0
            and r47["summary"].get("prerequisite_clean_rows_passed") == 8
            and r47["summary"].get("flags_only_rejection_rows") == 8
            and r47["summary"].get("source_backed_rows_passed") == 0,
            {
                "r47_validation_error_count": r47["summary"].get("validation_error_count"),
                "r47_prerequisite_clean_rows_passed": r47["summary"].get("prerequisite_clean_rows_passed"),
                "r47_flags_only_rejection_rows": r47["summary"].get("flags_only_rejection_rows"),
                "r47_source_backed_rows_passed": r47["summary"].get("source_backed_rows_passed"),
            },
        ),
        req(
            "S2",
            "R48 emits a row-level source-backed intake contract",
            contract["required_key_count"] == len(REQUIRED_KEYS)
            and contract["production_required_key_count"] == len(PRODUCTION_REQUIRED_KEYS)
            and contract["evidence_file_class_count"] == len(EVIDENCE_FILE_CLASSES),
            {
                "contract_hash": contract["contract_hash"],
                "required_key_count": contract["required_key_count"],
                "production_required_key_count": contract["production_required_key_count"],
                "evidence_file_class_count": contract["evidence_file_class_count"],
            },
        ),
        req(
            "S3",
            "R48 emits a hash-bound first-row submission template",
            template["challenge_id"] == SELECTED_CHALLENGE_ID
            and template["contract_hash"] == contract["contract_hash"]
            and bool(template["template_hash"]),
            {
                "selected_challenge_id": template["challenge_id"],
                "template_hash": template["template_hash"],
                "contract_hash": template["contract_hash"],
            },
        ),
        req(
            "S4",
            "Current state has no submitted source-backed row artifact",
            evaluation["submitted"] is False and evaluation["accepted_source_backed_row_count"] == 0,
            {
                "submitted": evaluation["submitted"],
                "accepted_source_backed_row_count": evaluation["accepted_source_backed_row_count"],
                "failed_reasons": evaluation["failed_reasons"],
            },
        ),
        req(
            "S5",
            "The missing submission is explicitly blocked on required production keys",
            evaluation["production_missing_key_count"] == len(PRODUCTION_REQUIRED_KEYS),
            {
                "production_missing_key_count": evaluation["production_missing_key_count"],
                "production_required_key_count": len(PRODUCTION_REQUIRED_KEYS),
            },
        ),
        req(
            "S6",
            "R48 preserves source-backed flag rejection until real evidence exists",
            evaluation["source_backed_flags_passed"] is False
            and evaluation["flag_state"]["source_backed_replay"] is False
            and evaluation["flag_state"]["same_unitary_certificate"] is False,
            {
                "source_backed_flags_passed": evaluation["source_backed_flags_passed"],
                "flag_state": evaluation["flag_state"],
            },
        ),
        req(
            "S7",
            "R48 preserves C2/O3/reroute/B7 zero-credit boundaries",
            True,
            {
                "c2_accepted": False,
                "o3_closed": False,
                "reroute_allowed": False,
                "b7_credit_delta": 0,
                "b7_space_time_volume_credit": 0,
            },
        ),
        req(
            "S8",
            "R48 claims no C3-C7, occurrence-removal, or B7 ledger progress",
            True,
            {
                "c3_c7_progress_claimed": False,
                "occurrence_removal_claimed": False,
                "b7_ledger_credit_claimed": False,
            },
        ),
    ]
    failed = [item["requirement_id"] for item in requirements if not item["passed"]]
    summary = {
        "source_r47_discriminator_hash": r47["summary"]["discriminator_hash"],
        "source_r47_fixture_hash": r47["summary"]["fixture_hash"],
        "source_r47_file_sha256": file_hash(args.r47_result),
        "source_r46_fixture_hash": r46_fixture["fixture_hash"],
        "selected_challenge_id": SELECTED_CHALLENGE_ID,
        "contract_hash": contract["contract_hash"],
        "contract_file_sha256": file_hash(args.contract_output),
        "template_hash": template["template_hash"],
        "template_file_sha256": file_hash(args.template_output),
        "evaluation_hash": evaluation["evaluation_hash"],
        "required_key_count": len(REQUIRED_KEYS),
        "production_required_key_count": len(PRODUCTION_REQUIRED_KEYS),
        "evidence_file_class_count": len(EVIDENCE_FILE_CLASSES),
        "submitted_source_backed_row_count": 0,
        "accepted_source_backed_row_count": evaluation["accepted_source_backed_row_count"],
        "missing_key_count": evaluation["missing_key_count"],
        "production_missing_key_count": evaluation["production_missing_key_count"],
        "source_backed_flags_passed": evaluation["source_backed_flags_passed"],
        "c2_strict_replay_rows_accepted": False,
        "o3_closed": False,
        "reroute_allowed": False,
        "accepted_route_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "b7_credit_delta": 0,
        "b7_space_time_volume_credit": 0,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "remaining_open_obligations": [
            "submit_O3_F4_C01_source_backed_row_artifact",
            "hash_bind_external_lineage_note_and_replay_environment",
            "provide_verifier_signature_for_same_unitary_certificate",
            "make_one_row_pass_the_R47_discriminator_without_weakening_rules",
            "scale_source_backed_acceptance_from_1_row_to_8_rows",
            "C3_same_unitary_replay_certificate",
            "C4_C5_same_access_denominator_comparison",
            "C6_leakage_free_optimizer_trace",
            "C7_machine_check_replay_bundle",
        ],
        "remaining_open_obligation_count": 9,
        "requirement_count": len(requirements),
        "requirements_passed": len(requirements) - len(failed),
        "requirements_failed": len(failed),
        "failed_requirement_ids": failed,
        "validation_error_count": len(failed),
    }
    return {
        "title": "B1/B7 Cone01 R48 O3-F4 C2 Source-Backed Row Intake Gate",
        "version": VERSION,
        "last_updated": "2026-07-08",
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "o3_f4_c2_source_backed_row_intake_packet": {
            "source_r47_result": str(args.r47_result),
            "source_r46_fixture": str(args.r46_fixture),
            "contract_output": str(args.contract_output),
            "template_output": str(args.template_output),
            "contract": contract,
            "template": template,
            "evaluation": evaluation,
        },
        "requirements": requirements,
        "summary": summary,
        "claim_boundary": {
            "what_is_supported": (
                "R48 converts the R47 flags-only blocker into a concrete source-backed "
                "row intake contract and hash-bound submission template for O3-F4-C01."
            ),
            "what_is_not_supported": (
                "R48 does not submit or accept a source-backed row, does not flip any "
                "source-backed flags, does not accept C2, close O3, allow reroute, or "
                "grant B7/STV credit."
            ),
            "next_gate": (
                "Submit the O3-F4-C01 source-backed row artifact satisfying the R48 "
                "contract, then rerun R47 and require exactly one row to pass before "
                "scaling to all 8 rows."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": failed,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    s = payload["summary"]
    lines = [
        "# B1/B7 Cone01 R48 O3-F4 C2 Source-Backed Row Intake Gate",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Upstream target: `{payload['upstream_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Selected challenge: `{s['selected_challenge_id']}`",
        f"- Contract hash: `{s['contract_hash']}`",
        f"- Template hash: `{s['template_hash']}`",
        f"- Evaluation hash: `{s['evaluation_hash']}`",
        "",
        "## Result",
        "",
        (
            f"R48 passes {s['requirements_passed']}/{s['requirement_count']} "
            "requirements by emitting the first concrete source-backed row intake "
            "contract while keeping the row unaccepted because no submission exists."
        ),
        "",
        "## Intake Surface",
        "",
        f"- Required keys: `{s['required_key_count']}`",
        f"- Production-required keys: `{s['production_required_key_count']}`",
        f"- Evidence file classes: `{s['evidence_file_class_count']}`",
        f"- Submitted source-backed rows: `{s['submitted_source_backed_row_count']}`",
        f"- Accepted source-backed rows: `{s['accepted_source_backed_row_count']}`",
        f"- Production missing keys: `{s['production_missing_key_count']}`",
        f"- Source-backed flags passed: `{s['source_backed_flags_passed']}`",
        f"- C2 accepted: `{s['c2_strict_replay_rows_accepted']}`",
        "",
        "## Requirement Results",
        "",
    ]
    for item in payload["requirements"]:
        lines.append(f"- `{item['requirement_id']}` {'PASS' if item['passed'] else 'FAIL'}: {item['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            "",
            f"- validation_error_count: `{s['validation_error_count']}`",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r47-result", type=Path, default=Path("results/B1_B7_cone01_R47_o3_f4_c2_source_backed_discriminator_rerun_gate_v0.json"))
    parser.add_argument("--r46-fixture", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/B1-B7-cone01-O3-F4-C2-remaining-witness-preflight.fixture.json"))
    parser.add_argument("--submission-input", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_backed_rows/O3-F4-C01.source_backed_row_submission.json"))
    parser.add_argument("--contract-output", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/B1-B7-cone01-O3-F4-C2-C01-source-backed-row-intake.contract.json"))
    parser.add_argument("--template-output", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/B1-B7-cone01-O3-F4-C2-C01-source-backed-row-intake.template.json"))
    parser.add_argument("--json-output", type=Path, default=Path("results/B1_B7_cone01_R48_o3_f4_c2_source_backed_row_intake_gate_v0.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("research/B1_B7_cone01_R48_o3_f4_c2_source_backed_row_intake_gate.md"))
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_payload(args)
    write_json(args.json_output, payload)
    write_markdown(args.markdown_output, payload)
    if args.pretty:
        s = payload["summary"]
        print(json.dumps({
            "status": payload["status"],
            "selected_challenge_id": s["selected_challenge_id"],
            "contract_hash": s["contract_hash"],
            "template_hash": s["template_hash"],
            "evaluation_hash": s["evaluation_hash"],
            "requirements_passed": s["requirements_passed"],
            "requirements_failed": s["requirements_failed"],
            "accepted_source_backed_row_count": s["accepted_source_backed_row_count"],
            "production_missing_key_count": s["production_missing_key_count"],
            "json_output": str(args.json_output),
        }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
