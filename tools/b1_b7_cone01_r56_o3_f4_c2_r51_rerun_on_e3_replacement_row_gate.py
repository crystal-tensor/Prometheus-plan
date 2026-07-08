#!/usr/bin/env python3
"""T-B1-004ff/T-B7-014o: R56 reruns R51 on the R55 E1/E2/E3 row."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r56_o3_f4_c2_r51_rerun_on_e3_replacement_row_gate_v0"
STATUS = "cone01_r56_o3_f4_c2_r51_rerun_accepts_e3_row_zero_c2_credit"
MODEL_STATUS = "o3_f4_c2_c01_r51_preflight_passed_r47_not_rerun"
VERSION = "0.1"
TARGET_ID = "T-B1-004ff/T-B7-014o"
UPSTREAM_TARGET_ID = "T-B1-004fe/T-B7-014n"
SELECTED_CHALLENGE_ID = "O3-F4-C01"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def req(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def boolean_aware_empty_keys(row: dict[str, Any], production_keys: list[str], boolean_keys: set[str]) -> list[str]:
    keys = []
    for key in production_keys:
        if key not in row:
            keys.append(key)
            continue
        value = row.get(key)
        if key in boolean_keys:
            if not isinstance(value, bool):
                keys.append(key)
            continue
        if value in (None, ""):
            keys.append(key)
    return keys


def verify_row(row: dict[str, Any], spec: dict[str, Any], root: Path) -> dict[str, Any]:
    file_hash_pairs = [tuple(pair) for pair in spec["file_hash_pairs"]]
    boolean_keys = set(spec["boolean_production_keys"])
    missing_keys = [key for key in spec["required_keys"] if key not in row]
    empty_production_keys = boolean_aware_empty_keys(
        row,
        list(spec["production_required_keys"]),
        boolean_keys,
    )
    malformed_sha_fields = [
        hash_key
        for _, hash_key in file_hash_pairs
        if hash_key in row and row.get(hash_key) is not None and not is_sha256(row.get(hash_key))
    ]
    file_results = []
    for path_key, hash_key in file_hash_pairs:
        path_value = row.get(path_key)
        expected_hash = row.get(hash_key)
        path = root / path_value if isinstance(path_value, str) else None
        exists = bool(path and path.exists() and path.is_file())
        actual_hash = file_hash(path) if exists else None
        file_results.append(
            {
                "path_key": path_key,
                "hash_key": hash_key,
                "path": path_value,
                "expected_hash": expected_hash,
                "exists": exists,
                "actual_hash": actual_hash,
                "hash_matches": exists and actual_hash == expected_hash,
            }
        )
    file_hash_failures = [
        item["path_key"]
        for item in file_results
        if not item["exists"] or not item["hash_matches"]
    ]
    flag_failures = [
        key
        for key, expected in spec["required_boolean_state"].items()
        if row.get(key) is not expected
    ]
    schema_passed = row.get("same_unitary_witness_schema") == spec["required_schema"]
    boundary_tokens_present = all(
        token in str(row.get("claim_boundary", "")) for token in spec["required_claim_boundary_tokens"]
    )
    accepted = (
        not missing_keys
        and not empty_production_keys
        and not malformed_sha_fields
        and not file_hash_failures
        and not flag_failures
        and schema_passed
        and boundary_tokens_present
    )
    return {
        "accepted": accepted,
        "missing_key_count": len(missing_keys),
        "empty_production_key_count": len(empty_production_keys),
        "malformed_sha_field_count": len(malformed_sha_fields),
        "file_hash_failure_count": len(file_hash_failures),
        "flag_failure_count": len(flag_failures),
        "schema_passed": schema_passed,
        "boundary_tokens_present": boundary_tokens_present,
        "missing_keys": missing_keys,
        "empty_production_keys": empty_production_keys,
        "malformed_sha_fields": malformed_sha_fields,
        "file_hash_failures": file_hash_failures,
        "flag_failures": flag_failures,
        "file_results": file_results,
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    r55 = load_json(args.r55_result)
    r51 = load_json(args.r51_result)
    spec = load_json(args.r51_verifier)
    row = load_json(args.e3_row_input)

    row_file_sha256 = file_hash(args.e3_row_input)
    spec_file_sha256 = file_hash(args.r51_verifier)
    actual_eval = verify_row(row, spec, args.root)
    evaluation = {
        "evaluation_id": "B1-B7-cone01-O3-F4-C2-C01-R56-r51-rerun-on-e3-row",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "challenge_id": SELECTED_CHALLENGE_ID,
        "source_r55_result": str(args.r55_result),
        "source_r55_e3_replacement_row_hash": r55["summary"]["e3_replacement_row_hash"],
        "e3_row_input": str(args.e3_row_input),
        "e3_row_file_sha256": row_file_sha256,
        "e3_row_hash": row["presubmission_row_hash"],
        "r51_verifier": str(args.r51_verifier),
        "r51_verifier_hash": spec["verifier_hash"],
        "r51_verifier_file_sha256": spec_file_sha256,
        "actual_row_verification": actual_eval,
        "r51_preflight_accepted": actual_eval["accepted"],
        "r51_preflight_accepted_row_count": 1 if actual_eval["accepted"] else 0,
        "r47_rerun_performed": False,
        "accepted_source_backed_row_count": 0,
        "c2_accepted": False,
        "o3_closed": False,
        "reroute_allowed": False,
        "b7_credit_delta": 0,
        "b7_space_time_volume_credit": 0,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "claim_boundary": (
            "R51 preflight rerun only; no C2; O3 remains open; no reroute; "
            "no B7 credit; no STV credit; no resource saving; R47 has not been rerun."
        ),
    }
    evaluation["evaluation_hash"] = stable_hash(evaluation)
    write_json(args.evaluation_output, evaluation)
    evaluation_file_sha256 = file_hash(args.evaluation_output)

    row_bound_to_r55 = (
        row["presubmission_row_hash"] == r55["summary"]["e3_replacement_row_hash"]
        and row_file_sha256 == file_hash(args.e3_row_input)
    )
    verifier_matches_r51 = (
        spec["verifier_hash"] == r51["summary"]["boolean_aware_verifier_hash"]
        and spec_file_sha256 == r51["summary"]["boolean_aware_verifier_file_sha256"]
    )
    no_structural_failures = (
        actual_eval["missing_key_count"] == 0
        and actual_eval["empty_production_key_count"] == 0
        and actual_eval["malformed_sha_field_count"] == 0
        and actual_eval["file_hash_failure_count"] == 0
    )
    semantic_flags_pass = (
        actual_eval["flag_failure_count"] == 0
        and row.get("source_backed_replay") is True
        and row.get("same_unitary_certificate") is True
        and row.get("smoke_only_not_c2_acceptance") is False
    )
    zero_credit_ok = (
        evaluation["accepted_source_backed_row_count"] == 0
        and evaluation["c2_accepted"] is False
        and evaluation["o3_closed"] is False
        and evaluation["reroute_allowed"] is False
        and evaluation["b7_credit_delta"] == 0
        and evaluation["b7_space_time_volume_credit"] == 0
        and evaluation["resource_saving_claimed"] is False
        and evaluation["b7_ledger_improvement_claimed"] is False
        and "no C2" in evaluation["claim_boundary"]
    )
    requirements = [
        req(
            "S1",
            "R55 is the upstream E1/E2/E3 evidence packet and left R51/R47 open",
            r55["summary"].get("requirements_passed") == 8
            and r55["summary"].get("evidence_slots_satisfied") == 3
            and r55["summary"].get("r51_rerun_performed") is False
            and r55["summary"].get("r47_rerun_performed") is False,
            {
                "r55_requirements_passed": r55["summary"].get("requirements_passed"),
                "r55_evidence_slots_satisfied": r55["summary"].get("evidence_slots_satisfied"),
                "r55_r51_rerun_performed": r55["summary"].get("r51_rerun_performed"),
                "r55_r47_rerun_performed": r55["summary"].get("r47_rerun_performed"),
            },
        ),
        req(
            "S2",
            "R56 reruns the exact R51 boolean-aware verifier",
            verifier_matches_r51,
            {
                "r51_source_hash": r51["summary"].get("boolean_aware_verifier_hash"),
                "r56_verifier_hash": spec["verifier_hash"],
                "r51_verifier_file_sha256": r51["summary"].get("boolean_aware_verifier_file_sha256"),
                "r56_verifier_file_sha256": spec_file_sha256,
            },
        ),
        req(
            "S3",
            "R56 binds the submitted row to the R55 E3 replacement row",
            row_bound_to_r55,
            {
                "r55_e3_replacement_row_hash": r55["summary"]["e3_replacement_row_hash"],
                "r56_e3_row_hash": row["presubmission_row_hash"],
                "r56_e3_row_file_sha256": row_file_sha256,
            },
        ),
        req(
            "S4",
            "R56 has no required-key, production-key, sha-shape, or file-hash failures",
            no_structural_failures,
            {
                "missing_key_count": actual_eval["missing_key_count"],
                "empty_production_key_count": actual_eval["empty_production_key_count"],
                "malformed_sha_field_count": actual_eval["malformed_sha_field_count"],
                "file_hash_failure_count": actual_eval["file_hash_failure_count"],
            },
        ),
        req(
            "S5",
            "R56 passes all R51 semantic flags, schema, and zero-credit boundary checks",
            semantic_flags_pass
            and actual_eval["schema_passed"] is True
            and actual_eval["boundary_tokens_present"] is True,
            {
                "flag_failure_count": actual_eval["flag_failure_count"],
                "flag_failures": actual_eval["flag_failures"],
                "schema_passed": actual_eval["schema_passed"],
                "boundary_tokens_present": actual_eval["boundary_tokens_present"],
                "source_backed_replay": row.get("source_backed_replay"),
                "same_unitary_certificate": row.get("same_unitary_certificate"),
                "smoke_only_not_c2_acceptance": row.get("smoke_only_not_c2_acceptance"),
            },
        ),
        req(
            "S6",
            "R56 accepts one row at R51 preflight only",
            actual_eval["accepted"] is True
            and evaluation["r51_preflight_accepted_row_count"] == 1
            and evaluation["r47_rerun_performed"] is False,
            {
                "r51_preflight_accepted": actual_eval["accepted"],
                "r51_preflight_accepted_row_count": evaluation["r51_preflight_accepted_row_count"],
                "r47_rerun_performed": evaluation["r47_rerun_performed"],
            },
        ),
        req(
            "S7",
            "R56 preserves zero C2/O3/reroute/B7/STV/resource credit",
            zero_credit_ok,
            {
                "accepted_source_backed_row_count": evaluation["accepted_source_backed_row_count"],
                "c2_accepted": evaluation["c2_accepted"],
                "o3_closed": evaluation["o3_closed"],
                "reroute_allowed": evaluation["reroute_allowed"],
                "b7_credit_delta": evaluation["b7_credit_delta"],
                "b7_space_time_volume_credit": evaluation["b7_space_time_volume_credit"],
            },
        ),
        req(
            "S8",
            "R56 leaves R47 exact-one-row acceptance as the next gate",
            evaluation["r47_rerun_performed"] is False
            and evaluation["r51_preflight_accepted"] is True
            and evaluation["accepted_source_backed_row_count"] == 0,
            {
                "next_gate": "rerun_R47_and_accept_exactly_one_row",
                "r51_preflight_accepted": evaluation["r51_preflight_accepted"],
                "accepted_source_backed_row_count": evaluation["accepted_source_backed_row_count"],
            },
        ),
    ]
    failed = [item["requirement_id"] for item in requirements if not item["passed"]]
    summary = {
        "source_r55_e3_signature_hash": r55["summary"]["e3_signature_hash"],
        "source_r55_e3_replacement_row_hash": r55["summary"]["e3_replacement_row_hash"],
        "selected_challenge_id": SELECTED_CHALLENGE_ID,
        "r51_verifier_hash": spec["verifier_hash"],
        "r51_verifier_file_sha256": spec_file_sha256,
        "r56_evaluation_hash": evaluation["evaluation_hash"],
        "r56_evaluation_file_sha256": evaluation_file_sha256,
        "r56_e3_row_hash": row["presubmission_row_hash"],
        "r56_e3_row_file_sha256": row_file_sha256,
        "missing_key_count": actual_eval["missing_key_count"],
        "empty_production_key_count": actual_eval["empty_production_key_count"],
        "malformed_sha_field_count": actual_eval["malformed_sha_field_count"],
        "file_hash_failure_count": actual_eval["file_hash_failure_count"],
        "flag_failure_count": actual_eval["flag_failure_count"],
        "schema_passed": actual_eval["schema_passed"],
        "boundary_tokens_present": actual_eval["boundary_tokens_present"],
        "source_backed_replay": row.get("source_backed_replay"),
        "same_unitary_certificate": row.get("same_unitary_certificate"),
        "smoke_only_not_c2_acceptance": row.get("smoke_only_not_c2_acceptance"),
        "r51_rerun_performed": True,
        "r51_preflight_accepted": actual_eval["accepted"],
        "r51_preflight_accepted_row_count": evaluation["r51_preflight_accepted_row_count"],
        "r47_rerun_performed": False,
        "accepted_source_backed_row_count": 0,
        "c2_strict_replay_rows_accepted": False,
        "o3_closed": False,
        "reroute_allowed": False,
        "b7_credit_delta": 0,
        "b7_space_time_volume_credit": 0,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "remaining_open_obligations": ["rerun_R47_and_accept_exactly_one_row"],
        "remaining_open_obligation_count": 1,
        "requirement_count": len(requirements),
        "requirements_passed": len(requirements) - len(failed),
        "requirements_failed": len(failed),
        "failed_requirement_ids": failed,
        "validation_error_count": len(failed),
    }
    return {
        "title": "B1/B7 Cone01 R56 O3-F4 C2 R51 Rerun on E3 Replacement Row Gate",
        "version": VERSION,
        "last_updated": "2026-07-08",
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "r51_rerun_packet": {
            "source_r55_result": str(args.r55_result),
            "source_r51_result": str(args.r51_result),
            "r51_verifier": str(args.r51_verifier),
            "e3_row_input": str(args.e3_row_input),
            "evaluation_output": str(args.evaluation_output),
            "evaluation": evaluation,
        },
        "requirements": requirements,
        "summary": summary,
        "claim_boundary": {
            "what_is_supported": (
                "R56 reruns the exact R51 boolean-aware preflight verifier on the R55 "
                "E1/E2/E3 replacement row and accepts exactly one row at the R51 preflight layer."
            ),
            "what_is_not_supported": (
                "R56 does not rerun R47, does not accept a source-backed row at the discriminator, "
                "does not close C2 or O3, and does not grant reroute, B7, STV, resource, or ledger credit."
            ),
            "next_gate": "Rerun R47 and require exactly one source-backed row to pass.",
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": failed,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    s = payload["summary"]
    lines = [
        "# B1/B7 Cone01 R56 O3-F4 C2 R51 Rerun on E3 Replacement Row Gate",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Upstream target: `{payload['upstream_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Selected challenge: `{s['selected_challenge_id']}`",
        f"- R51 verifier hash: `{s['r51_verifier_hash']}`",
        f"- R56 evaluation hash: `{s['r56_evaluation_hash']}`",
        f"- R56 E3 row hash: `{s['r56_e3_row_hash']}`",
        "",
        "## Result",
        "",
        (
            f"R56 passes {s['requirements_passed']}/{s['requirement_count']} "
            "requirements by rerunning R51 on the R55 E1/E2/E3 row. One row passes "
            "R51 preflight, but R47 and C2 acceptance remain open."
        ),
        "",
        "## R51 Rerun Evidence",
        "",
        f"- Missing keys: `{s['missing_key_count']}`",
        f"- Empty production keys: `{s['empty_production_key_count']}`",
        f"- Malformed sha fields: `{s['malformed_sha_field_count']}`",
        f"- File-hash failures: `{s['file_hash_failure_count']}`",
        f"- Flag failures: `{s['flag_failure_count']}`",
        f"- Schema passed: `{s['schema_passed']}`",
        f"- Boundary tokens present: `{s['boundary_tokens_present']}`",
        f"- R51 preflight accepted: `{s['r51_preflight_accepted']}`",
        f"- R51 preflight accepted row count: `{s['r51_preflight_accepted_row_count']}`",
        f"- Accepted source-backed rows after R47: `{s['accepted_source_backed_row_count']}`",
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
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--r55-result", type=Path, default=Path("results/B1_B7_cone01_R55_o3_f4_c2_e3_verifier_signature_artifact_gate_v0.json"))
    parser.add_argument("--r51-result", type=Path, default=Path("results/B1_B7_cone01_R51_o3_f4_c2_boolean_aware_preflight_gate_v0.json"))
    parser.add_argument("--r51-verifier", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_backed_rows/O3-F4-C01.boolean_aware_preflight.verifier.json"))
    parser.add_argument("--e3-row-input", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_backed_rows/O3-F4-C01.e3_replacement_presubmission.json"))
    parser.add_argument("--evaluation-output", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_backed_rows/O3-F4-C01.r56_r51_rerun_evaluation.json"))
    parser.add_argument("--json-output", type=Path, default=Path("results/B1_B7_cone01_R56_o3_f4_c2_r51_rerun_on_e3_replacement_row_gate_v0.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("research/B1_B7_cone01_R56_o3_f4_c2_r51_rerun_on_e3_replacement_row_gate.md"))
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = build_payload(args)
    write_json(args.json_output, payload)
    write_markdown(args.markdown_output, payload)
    if args.pretty:
        s = payload["summary"]
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "selected_challenge_id": s["selected_challenge_id"],
                    "requirements_passed": s["requirements_passed"],
                    "requirements_failed": s["requirements_failed"],
                    "r51_rerun_performed": s["r51_rerun_performed"],
                    "r51_preflight_accepted": s["r51_preflight_accepted"],
                    "r51_preflight_accepted_row_count": s["r51_preflight_accepted_row_count"],
                    "r47_rerun_performed": s["r47_rerun_performed"],
                    "accepted_source_backed_row_count": s["accepted_source_backed_row_count"],
                    "file_hash_failure_count": s["file_hash_failure_count"],
                    "flag_failure_count": s["flag_failure_count"],
                    "r56_evaluation_hash": s["r56_evaluation_hash"],
                    "r56_e3_row_hash": s["r56_e3_row_hash"],
                    "json_output": str(args.json_output),
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
