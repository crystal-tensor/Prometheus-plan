#!/usr/bin/env python3
"""T-B5-006q/T-B10-014n: W1 replay-validation manifest gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b5_b10_w1_replay_validation_manifest_gate_v0"
STATUS = "w1_replay_validation_manifest_open_missing_artifact"
MODEL_STATUS = "w1_replay_validation_manifest_required_before_priority_row_acceptance"
VERSION = "0.1"
EXPECTED_ROW_CONTRACT_HASH = "7ee407e20f51bd0c003d885c8d43282359f84bea9729f0da203b9b2c2970a9fc"
EXPECTED_PRIORITY_ROW_ID = "D5H_s8_u2_eta0.25_n4x4_obs_density_site_4"
EXPECTED_PROVENANCE_MANIFEST_ID = "B5B10-W1-priority-row-provenance-manifest"
EXPECTED_REPLAY_MANIFEST_ID = "B5B10-W1-priority-row-replay-validation-manifest"
EXPECTED_FAILED_IDS = ["P6", "P7", "P8"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2 if pretty else None, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def requirement(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    provenance = load_json(args.provenance_manifest_gate)
    prototype = load_json(args.prototype_environment_scout)
    blocker = load_json(args.blocker_queue_gate)
    provenance_summary = provenance["summary"]
    prototype_summary = prototype["summary"]
    blocker_summary = blocker["summary"]
    submission_path = args.submission_dir / f"{EXPECTED_REPLAY_MANIFEST_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None

    required_keys = [
        "manifest_id",
        "provenance_manifest_id",
        "row_id",
        "row_contract_hash",
        "provenance_manifest_hash",
        "canonical_state_replay_hash",
        "left_environment_replay_hash",
        "right_environment_replay_hash",
        "orthonormal_residual_replay_hash",
        "discarded_weight_replay_hash",
        "convergence_replay_hash",
        "same_access_cost_ledger_hash",
        "wall_clock_memory_ledger_hash",
        "sweep_matvec_count_ledger_hash",
        "seeded_pressure_comparison_hash",
        "b10_access_boundary_hash",
        "claim_boundary",
    ]
    production_required_keys = [
        "provenance_manifest_hash",
        "canonical_state_replay_hash",
        "left_environment_replay_hash",
        "right_environment_replay_hash",
        "orthonormal_residual_replay_hash",
        "discarded_weight_replay_hash",
        "convergence_replay_hash",
        "same_access_cost_ledger_hash",
        "wall_clock_memory_ledger_hash",
        "sweep_matvec_count_ledger_hash",
        "seeded_pressure_comparison_hash",
        "b10_access_boundary_hash",
        "claim_boundary",
    ]
    evidence_files = [
        "accepted_priority_row_provenance_manifest",
        "canonical_state_replay_manifest",
        "left_environment_replay_manifest",
        "right_environment_replay_manifest",
        "orthonormal_residual_replay_table",
        "discarded_weight_replay_table",
        "convergence_replay_table",
        "same_access_cost_ledger",
        "wall_clock_memory_ledger",
        "sweep_matvec_count_ledger",
        "seeded_pressure_comparison_manifest",
        "b10_access_boundary_note",
        "claim_boundary_note",
    ]

    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    production_present = [
        key for key in production_required_keys if submitted is not None and submitted.get(key) is not None
    ]
    replay_hashes = submitted.get("replay_hashes") if submitted else None
    replay_bound = (
        isinstance(replay_hashes, dict)
        and replay_hashes.get("row_contract_hash") == EXPECTED_ROW_CONTRACT_HASH
        and replay_hashes.get("provenance_manifest_hash") == provenance_summary.get("manifest_hash")
        and replay_hashes.get("row_id") == EXPECTED_PRIORITY_ROW_ID
    )
    source_backed = submitted is not None and submitted.get("source_evidence_files_present") is True
    manifest_bound = (
        submitted is not None
        and submitted.get("manifest_id") == EXPECTED_REPLAY_MANIFEST_ID
        and submitted.get("provenance_manifest_id") == EXPECTED_PROVENANCE_MANIFEST_ID
        and submitted.get("row_id") == EXPECTED_PRIORITY_ROW_ID
        and submitted.get("row_contract_hash") == EXPECTED_ROW_CONTRACT_HASH
        and submitted.get("provenance_manifest_hash") == provenance_summary.get("manifest_hash")
    )
    claim_boundary_bound = (
        submitted is not None
        and isinstance(submitted.get("claim_boundary"), dict)
        and submitted["claim_boundary"].get("production_dmrg_claimed") is False
        and submitted["claim_boundary"].get("same_access_positive_route_claimed") is False
        and submitted["claim_boundary"].get("quantum_advantage_claimed") is False
        and submitted["claim_boundary"].get("bqp_separation_claimed") is False
    )

    manifest_packet = {
        "manifest_id": EXPECTED_REPLAY_MANIFEST_ID,
        "provenance_manifest_id": EXPECTED_PROVENANCE_MANIFEST_ID,
        "row_id": EXPECTED_PRIORITY_ROW_ID,
        "row_contract_hash": EXPECTED_ROW_CONTRACT_HASH,
        "submission_artifact_path": str(submission_path),
        "source_provenance_manifest_gate": str(args.provenance_manifest_gate),
        "source_prototype_environment_scout": str(args.prototype_environment_scout),
        "source_blocker_queue_gate": str(args.blocker_queue_gate),
        "provenance_manifest_hash": provenance_summary.get("manifest_hash"),
        "row_contract_count": prototype_summary.get("row_contract_count"),
        "prototype_trace_hash_rows": prototype_summary.get("prototype_trace_hash_rows"),
        "prototype_discarded_weight_metric_rows": prototype_summary.get(
            "prototype_discarded_weight_metric_rows"
        ),
        "production_contract_rows_accepted": prototype_summary.get("production_contract_rows_accepted"),
        "required_keys": required_keys,
        "production_required_keys": production_required_keys,
        "required_evidence_files": evidence_files,
        "accepted_only_if": [
            "manifest_id equals B5B10-W1-priority-row-replay-validation-manifest",
            "provenance_manifest_id equals B5B10-W1-priority-row-provenance-manifest",
            "row_id equals D5H_s8_u2_eta0.25_n4x4_obs_density_site_4",
            "row_contract_hash and provenance_manifest_hash match the source gates",
            "canonical state, left/right environments, residuals, discarded weights, convergence, same-access cost, wall-clock/memory, sweep/matvec counts, seeded-pressure comparison, and B10 access boundary are hash-bound",
            "replay_hashes bind row_contract_hash, provenance_manifest_hash, and row_id",
            "source evidence files are present and hash-bound",
            "claim_boundary forbids production DMRG, same-access positive route, quantum advantage, and BQP separation claims until accepted rows exist",
        ],
    }
    manifest_packet["manifest_hash"] = stable_hash(manifest_packet)

    forbidden_claims = [
        "production_dmrg_claimed",
        "same_access_positive_route_claimed",
        "quantum_advantage_claimed",
        "bqp_separation_claimed",
    ]
    requirements = [
        requirement(
            "P1",
            "Priority-row provenance manifest gate remains valid and blocked only on P6/P7/P8",
            provenance.get("method") == "b5_b10_w1_priority_row_provenance_manifest_gate_v0"
            and provenance_summary.get("validation_error_count") == 0
            and provenance_summary.get("failed_manifest_requirement_ids") == ["P6", "P7", "P8"],
            {
                "source_status": provenance.get("status"),
                "failed_manifest_requirement_ids": provenance_summary.get("failed_manifest_requirement_ids"),
                "validation_error_count": provenance_summary.get("validation_error_count"),
            },
        ),
        requirement(
            "P2",
            "Replay-validation manifest is bound to the priority W1 row contract",
            provenance_summary.get("manifest_id") == EXPECTED_PROVENANCE_MANIFEST_ID
            and provenance_summary.get("priority_row_id") == EXPECTED_PRIORITY_ROW_ID
            and provenance_summary.get("row_contract_hash") == EXPECTED_ROW_CONTRACT_HASH,
            {
                "provenance_manifest_id": provenance_summary.get("manifest_id"),
                "priority_row_id": provenance_summary.get("priority_row_id"),
                "row_contract_hash": provenance_summary.get("row_contract_hash"),
            },
        ),
        requirement(
            "P3",
            "Manifest packet carries locked replay-validation schema and evidence classes",
            len(required_keys) == 17
            and len(production_required_keys) == 13
            and len(evidence_files) == 13,
            {
                "required_key_count": len(required_keys),
                "production_required_key_count": len(production_required_keys),
                "required_evidence_file_count": len(evidence_files),
            },
        ),
        requirement(
            "P4",
            "Prototype scope and production blockers remain preserved",
            prototype_summary.get("row_contract_count") == 9
            and prototype_summary.get("prototype_trace_hash_rows") == 9
            and prototype_summary.get("prototype_discarded_weight_metric_rows") == 9
            and prototype_summary.get("production_contract_rows_accepted") == 0
            and prototype_summary.get("production_dmrg_available") is False,
            {
                "row_contract_count": prototype_summary.get("row_contract_count"),
                "prototype_trace_hash_rows": prototype_summary.get("prototype_trace_hash_rows"),
                "prototype_discarded_weight_metric_rows": prototype_summary.get(
                    "prototype_discarded_weight_metric_rows"
                ),
                "production_contract_rows_accepted": prototype_summary.get(
                    "production_contract_rows_accepted"
                ),
                "production_dmrg_available": prototype_summary.get("production_dmrg_available"),
            },
        ),
        requirement(
            "P5",
            "Blocker queue still has no submitted or accepted production rows",
            blocker_summary.get("submitted_production_row_count") == 0
            and blocker_summary.get("accepted_production_row_count") == 0
            and provenance_summary.get("accepted_priority_row_count") == 0
            and all(provenance_summary.get(key) is False for key in forbidden_claims),
            {
                "submitted_production_row_count": blocker_summary.get("submitted_production_row_count"),
                "accepted_production_row_count": blocker_summary.get("accepted_production_row_count"),
                "accepted_priority_row_count": provenance_summary.get("accepted_priority_row_count"),
                **{key: provenance_summary.get(key) for key in forbidden_claims},
            },
        ),
        requirement(
            "P6",
            "Replay-validation manifest artifact has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted manifest satisfies the locked replay-validation schema",
            submitted_exists and not missing_keys and len(production_present) == len(production_required_keys),
            {
                "missing_keys": missing_keys,
                "production_keys_present": production_present,
                "production_required_keys": production_required_keys,
                "submitted_key_count": len(submitted) if submitted else 0,
            },
        ),
        requirement(
            "P8",
            "Submitted manifest is source-backed, row-bound, replay-bound, and claim-boundary-bound",
            source_backed and manifest_bound and replay_bound and claim_boundary_bound,
            {
                "source_evidence_files_present": source_backed,
                "manifest_bound": manifest_bound,
                "replay_bound": replay_bound,
                "claim_boundary_bound": claim_boundary_bound,
            },
        ),
        requirement(
            "P9",
            "Forbidden production, positive-route, advantage, and BQP claims remain false",
            all(provenance_summary.get(key) is False for key in forbidden_claims),
            {key: provenance_summary.get(key) for key in forbidden_claims},
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected replay-validation manifest failures: {failed_ids}")
    if submitted_exists:
        validation_errors.append("gate expected no submitted replay-validation manifest until a solver PR supplies one")

    summary = {
        "manifest_id": EXPECTED_REPLAY_MANIFEST_ID,
        "provenance_manifest_id": EXPECTED_PROVENANCE_MANIFEST_ID,
        "priority_row_id": EXPECTED_PRIORITY_ROW_ID,
        "row_contract_hash": EXPECTED_ROW_CONTRACT_HASH,
        "provenance_manifest_hash": provenance_summary.get("manifest_hash"),
        "manifest_hash": manifest_packet["manifest_hash"],
        "manifest_requirement_count": len(requirements),
        "manifest_requirements_passed": passed,
        "manifest_requirements_failed": len(requirements) - passed,
        "failed_manifest_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "production_required_key_count": len(production_required_keys),
        "required_evidence_file_count": len(evidence_files),
        "row_contract_count": prototype_summary.get("row_contract_count"),
        "prototype_trace_hash_rows": prototype_summary.get("prototype_trace_hash_rows"),
        "prototype_discarded_weight_metric_rows": prototype_summary.get(
            "prototype_discarded_weight_metric_rows"
        ),
        "production_contract_rows_accepted": prototype_summary.get("production_contract_rows_accepted"),
        "submitted_manifest_exists": submitted_exists,
        "submitted_key_count": len(submitted) if submitted else 0,
        "missing_key_count": len(missing_keys),
        "production_keys_present_count": len(production_present),
        "accepted_priority_row_count": provenance_summary.get("accepted_priority_row_count"),
        "b10_t1_positive_route_ready": False,
        "production_dmrg_claimed": False,
        "same_access_positive_route_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "validation_error_count": len(validation_errors),
    }
    return {
        "benchmark_id": "B5",
        "linked_benchmark_id": "B10",
        "source_target_id": "B10-T1",
        "dependency_benchmarks": ["B5", "B10"],
        "title": "B5/B10 W1 Replay-Validation Manifest Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_provenance_manifest_gate": str(args.provenance_manifest_gate),
        "source_prototype_environment_scout": str(args.prototype_environment_scout),
        "source_blocker_queue_gate": str(args.blocker_queue_gate),
        "summary": summary,
        "replay_validation_manifest_packet": manifest_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "The B5/B10 W1 priority-row route now has a replay-validation manifest packet "
                "that must bind canonical states, environments, residuals, discarded weights, "
                "convergence, same-access cost, resource ledgers, seeded-pressure comparison, and "
                "B10 boundary evidence before the priority row can count."
            ),
            "what_is_not_supported": (
                "No replay-validation manifest or priority production row has been submitted or accepted; "
                "no production DMRG denominator, same-access positive route, quantum advantage, or BQP "
                "separation is supported."
            ),
            "next_gate": (
                "Submit B5B10-W1-priority-row-replay-validation-manifest with the accepted provenance "
                "manifest hash, row replay hashes, cost ledgers, seeded-pressure comparison, B10 access "
                "boundary, and claim boundary before the priority production-row artifact can count."
            ),
            "production_dmrg_claimed": False,
            "same_access_positive_route_claimed": False,
            "quantum_advantage_claimed": False,
            "bqp_separation_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    packet = payload["replay_validation_manifest_packet"]
    lines = [
        "# B5/B10 W1 Replay-Validation Manifest Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Manifest: `{summary['manifest_id']}`",
        f"- Provenance manifest: `{summary['provenance_manifest_id']}`",
        f"- Priority row: `{summary['priority_row_id']}`",
        f"- Provenance manifest hash: `{summary['provenance_manifest_hash']}`",
        f"- Manifest hash: `{summary['manifest_hash']}`",
        f"- Requirements passed/failed: `{summary['manifest_requirements_passed']}` / `{summary['manifest_requirements_failed']}`",
        f"- Failed requirement IDs: `{summary['failed_manifest_requirement_ids']}`",
        f"- Required key / production key / evidence file count: `{summary['required_key_count']}` / `{summary['production_required_key_count']}` / `{summary['required_evidence_file_count']}`",
        f"- Row contracts / prototype trace hashes / discarded-weight metric rows: `{summary['row_contract_count']}` / `{summary['prototype_trace_hash_rows']}` / `{summary['prototype_discarded_weight_metric_rows']}`",
        f"- Production contract rows accepted: `{summary['production_contract_rows_accepted']}`",
        f"- Submitted manifest exists: `{summary['submitted_manifest_exists']}`",
        f"- Accepted priority rows: `{summary['accepted_priority_row_count']}`",
        f"- validation_error_count: `{summary['validation_error_count']}`",
        "",
        "## Manifest Packet",
        "",
        f"- Submission path: `{packet['submission_artifact_path']}`",
        "",
        "Required evidence files:",
        "",
    ]
    for item in packet["required_evidence_files"]:
        lines.append(f"- {item}")
    lines.extend(["", "Acceptance predicates:", ""])
    for item in packet["accepted_only_if"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Requirement Results", ""])
    for row in payload["requirements"]:
        state = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- {row['requirement_id']} [{state}]: {row['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            f"- production_dmrg_claimed: {payload['claim_boundary']['production_dmrg_claimed']}",
            f"- same_access_positive_route_claimed: {payload['claim_boundary']['same_access_positive_route_claimed']}",
            f"- quantum_advantage_claimed: {payload['claim_boundary']['quantum_advantage_claimed']}",
            f"- bqp_separation_claimed: {payload['claim_boundary']['bqp_separation_claimed']}",
            "",
            "## Validation",
            "",
            f"- validation_error_count: {summary['validation_error_count']}",
        ]
    )
    if payload["validation_errors"]:
        for error in payload["validation_errors"]:
            lines.append(f"- {error}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provenance-manifest-gate",
        type=Path,
        default=Path("results/B5_B10_w1_priority_row_provenance_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--prototype-environment-scout",
        type=Path,
        default=Path("results/B5_B10_w1_prototype_environment_scout_v0.json"),
    )
    parser.add_argument(
        "--blocker-queue-gate",
        type=Path,
        default=Path("results/B5_B10_w1_production_row_blocker_queue_gate_v0.json"),
    )
    parser.add_argument(
        "--submission-dir",
        type=Path,
        default=Path("results/B5_B10_w1_replay_validation_manifest_submissions"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B5_B10_w1_replay_validation_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B5_B10_w1_replay_validation_manifest_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-02")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, pretty=args.pretty)
    write_markdown(payload, args.markdown_output)
    print(json.dumps(payload["summary"], indent=2 if args.pretty else None, sort_keys=True))
    if payload["validation_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
