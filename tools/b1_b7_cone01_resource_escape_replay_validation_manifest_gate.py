#!/usr/bin/env python3
"""T-B1-004cw/T-B7-012e: cone_01 resource-escape replay-validation manifest gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_resource_escape_replay_validation_manifest_gate_v0"
STATUS = "cone01_resource_escape_replay_validation_manifest_open_missing_artifact"
MODEL_STATUS = "resource_escape_replay_manifest_required_before_b7_credit"
VERSION = "0.1"
EXPECTED_PACKET_ID = "B1-B7-cone01-resource-escape"
EXPECTED_PROVENANCE_MANIFEST_ID = "B1-B7-cone01-resource-escape-provenance-manifest"
EXPECTED_REPLAY_MANIFEST_ID = "B1-B7-cone01-resource-escape-replay-validation-manifest"
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
    claim_seal = load_json(args.claim_boundary_seal)
    physical = load_json(args.physical_pricing_gate)
    provenance_summary = provenance["summary"]
    provenance_packet = provenance["resource_escape_provenance_manifest_packet"]
    claim_summary = claim_seal["summary"]
    physical_summary = physical["summary"]
    submission_path = args.submission_dir / f"{EXPECTED_REPLAY_MANIFEST_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None

    required_keys = [
        "manifest_id",
        "provenance_manifest_id",
        "priority_packet_id",
        "priority_packet_hash",
        "provenance_manifest_hash",
        "qiskit_loader_claim_boundary_seal_replay_hash",
        "physical_synthesis_pricing_replay_hash",
        "openqasm3_source_map_replay_hash",
        "selected_line_window_replay_hash",
        "line1381_resolution_replay_hash",
        "line1378_recovery_replay_hash",
        "occurrence_certificate_batch_replay_hash",
        "b7_refreshed_ledger_replay_hash",
        "full_replay_or_symbolic_equivalence_hash",
        "no_double_counting_ledger_replay_hash",
        "accepted_exit_route_manifest_hash",
        "resource_delta_ledger_hash",
        "claim_boundary",
    ]
    production_required_keys = [
        "provenance_manifest_hash",
        "qiskit_loader_claim_boundary_seal_replay_hash",
        "physical_synthesis_pricing_replay_hash",
        "openqasm3_source_map_replay_hash",
        "selected_line_window_replay_hash",
        "b7_refreshed_ledger_replay_hash",
        "full_replay_or_symbolic_equivalence_hash",
        "no_double_counting_ledger_replay_hash",
        "accepted_exit_route_manifest_hash",
        "resource_delta_ledger_hash",
        "claim_boundary",
    ]
    evidence_files = [
        "accepted_resource_escape_provenance_manifest",
        "qiskit_loader_claim_boundary_seal_replay",
        "physical_synthesis_pricing_replay",
        "openqasm3_source_map_replay",
        "selected_line_window_replay",
        "line1381_resolution_replay",
        "line1378_recovery_replay",
        "occurrence_certificate_batch_replay",
        "b7_refreshed_ledger_replay",
        "full_replay_or_symbolic_equivalence_certificate",
        "no_double_counting_ledger_replay",
        "accepted_exit_route_manifest",
        "resource_delta_ledger",
        "claim_boundary_note",
    ]

    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    production_present = [
        key for key in production_required_keys if submitted is not None and submitted.get(key) is not None
    ]
    replay_hashes = submitted.get("replay_hashes") if submitted else None
    replay_bound = (
        isinstance(replay_hashes, dict)
        and replay_hashes.get("provenance_manifest_hash") == provenance_summary.get("manifest_hash")
        and replay_hashes.get("priority_packet_hash") == provenance_summary.get("priority_packet_hash")
        and replay_hashes.get("priority_packet_id") == EXPECTED_PACKET_ID
    )
    source_backed = submitted is not None and submitted.get("source_evidence_files_present") is True
    manifest_bound = (
        submitted is not None
        and submitted.get("manifest_id") == EXPECTED_REPLAY_MANIFEST_ID
        and submitted.get("provenance_manifest_id") == EXPECTED_PROVENANCE_MANIFEST_ID
        and submitted.get("priority_packet_id") == EXPECTED_PACKET_ID
        and submitted.get("priority_packet_hash") == provenance_summary.get("priority_packet_hash")
        and submitted.get("provenance_manifest_hash") == provenance_summary.get("manifest_hash")
    )
    claim_boundary_bound = (
        submitted is not None
        and isinstance(submitted.get("claim_boundary"), dict)
        and submitted["claim_boundary"].get("resource_saving_claimed") is False
        and submitted["claim_boundary"].get("b7_ledger_improvement_claimed") is False
        and submitted["claim_boundary"].get("occurrence_removal_claimed") is False
        and submitted["claim_boundary"].get("proxy_t_reduction_claimed") is False
    )

    replay_packet = {
        "manifest_id": EXPECTED_REPLAY_MANIFEST_ID,
        "provenance_manifest_id": EXPECTED_PROVENANCE_MANIFEST_ID,
        "priority_packet_id": EXPECTED_PACKET_ID,
        "submission_artifact_path": str(submission_path),
        "source_provenance_manifest_gate": str(args.provenance_manifest_gate),
        "source_claim_boundary_seal": str(args.claim_boundary_seal),
        "source_physical_pricing_gate": str(args.physical_pricing_gate),
        "priority_packet_hash": provenance_summary.get("priority_packet_hash"),
        "provenance_manifest_hash": provenance_summary.get("manifest_hash"),
        "selected_line_numbers": provenance_summary.get("selected_line_numbers"),
        "dropped_overlap_candidate_line_numbers": provenance_summary.get(
            "dropped_overlap_candidate_line_numbers"
        ),
        "line1381_off_grid_parameter_count": provenance_summary.get(
            "line1381_off_grid_parameter_count"
        ),
        "line1381_unpriced_proxy_t_pressure": provenance_summary.get(
            "line1381_unpriced_proxy_t_pressure"
        ),
        "required_keys": required_keys,
        "production_required_keys": production_required_keys,
        "required_evidence_files": evidence_files,
        "accepted_only_if": [
            "manifest_id equals B1-B7-cone01-resource-escape-replay-validation-manifest",
            "provenance_manifest_id equals B1-B7-cone01-resource-escape-provenance-manifest",
            "priority_packet_id equals B1-B7-cone01-resource-escape",
            "priority_packet_hash and provenance_manifest_hash match the source gates",
            "Qiskit-loader seal, physical pricing, OpenQASM 3 source map, selected-line window, B7 ledger replay, equivalence proof, and no-double-counting ledger are replay-bound",
            "at least one exit route replay is supplied for line1381 resolution, line1378 recovery, or occurrence certificate batch",
            "accepted_exit_route_manifest and resource_delta_ledger are hash-bound before any B7 credit",
            "source evidence files are present and replay_hashes bind provenance, priority packet, and packet id",
            "claim_boundary forbids resource-saving, B7-ledger improvement, occurrence-removal, and proxy-T reduction claims until accepted",
        ],
    }
    replay_packet["manifest_hash"] = stable_hash(replay_packet)

    requirements = [
        requirement(
            "P1",
            "Resource-escape provenance manifest remains valid and blocked only on P6/P7/P8",
            provenance.get("method") == "b1_b7_cone01_resource_escape_provenance_manifest_gate_v0"
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
            "Replay manifest is bound to provenance and priority resource-escape packet",
            provenance_summary.get("manifest_id") == EXPECTED_PROVENANCE_MANIFEST_ID
            and provenance_summary.get("priority_packet_id") == EXPECTED_PACKET_ID
            and provenance_packet.get("manifest_hash") == provenance_summary.get("manifest_hash"),
            {
                "provenance_manifest_id": provenance_summary.get("manifest_id"),
                "priority_packet_id": provenance_summary.get("priority_packet_id"),
                "priority_packet_hash": provenance_summary.get("priority_packet_hash"),
                "provenance_manifest_hash": provenance_summary.get("manifest_hash"),
            },
        ),
        requirement(
            "P3",
            "Replay manifest packet carries locked replay schema and evidence file classes",
            len(required_keys) == 18 and len(production_required_keys) == 11 and len(evidence_files) == 14,
            {
                "required_key_count": len(required_keys),
                "production_required_key_count": len(production_required_keys),
                "required_evidence_file_count": len(evidence_files),
            },
        ),
        requirement(
            "P4",
            "Current line-1381, line-1378, and occurrence blockers remain preserved",
            claim_summary.get("line1381_replacement_off_pi_over_four_parameter_count") == 5
            and claim_summary.get("line1378_delta_recovered") is False
            and claim_summary.get("accepted_occurrence_removal") == 0
            and physical_summary.get("physical_synthesis_pricing_accepted") is False,
            {
                "line1381_replacement_off_pi_over_four_parameter_count": claim_summary.get(
                    "line1381_replacement_off_pi_over_four_parameter_count"
                ),
                "line1378_delta_recovered": claim_summary.get("line1378_delta_recovered"),
                "accepted_occurrence_removal": claim_summary.get("accepted_occurrence_removal"),
                "physical_synthesis_pricing_accepted": physical_summary.get(
                    "physical_synthesis_pricing_accepted"
                ),
            },
        ),
        requirement(
            "P5",
            "B7 ledger credit remains zero before source-backed replay validation",
            provenance_summary.get("accepted_occurrence_removal") == 0
            and provenance_summary.get("accepted_proxy_t_reduction") == 0
            and provenance_summary.get("resource_saving_claimed") is False
            and provenance_summary.get("b7_ledger_improvement_claimed") is False,
            {
                "accepted_occurrence_removal": provenance_summary.get("accepted_occurrence_removal"),
                "accepted_proxy_t_reduction": provenance_summary.get("accepted_proxy_t_reduction"),
                "resource_saving_claimed": provenance_summary.get("resource_saving_claimed"),
                "b7_ledger_improvement_claimed": provenance_summary.get(
                    "b7_ledger_improvement_claimed"
                ),
            },
        ),
        requirement(
            "P6",
            "Resource-escape replay-validation manifest artifact has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted replay manifest satisfies the locked replay schema",
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
            "Submitted replay manifest is source-backed, manifest-bound, replay-bound, and claim-boundary-bound",
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
            "Forbidden resource-saving and B7-ledger claims remain false",
            provenance["claim_boundary"].get("resource_saving_claimed") is False
            and provenance["claim_boundary"].get("b7_ledger_improvement_claimed") is False
            and provenance["claim_boundary"].get("occurrence_removal_claimed") is False
            and provenance["claim_boundary"].get("proxy_t_reduction_claimed") is False,
            {
                "resource_saving_claimed": provenance["claim_boundary"].get("resource_saving_claimed"),
                "b7_ledger_improvement_claimed": provenance["claim_boundary"].get(
                    "b7_ledger_improvement_claimed"
                ),
                "occurrence_removal_claimed": provenance["claim_boundary"].get(
                    "occurrence_removal_claimed"
                ),
                "proxy_t_reduction_claimed": provenance["claim_boundary"].get(
                    "proxy_t_reduction_claimed"
                ),
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected resource-escape replay manifest failures: {failed_ids}")
    if submitted_exists:
        validation_errors.append("gate expected no submitted replay manifest until a compiler PR supplies one")

    summary = {
        "manifest_id": EXPECTED_REPLAY_MANIFEST_ID,
        "provenance_manifest_id": EXPECTED_PROVENANCE_MANIFEST_ID,
        "priority_packet_id": EXPECTED_PACKET_ID,
        "priority_packet_hash": provenance_summary.get("priority_packet_hash"),
        "provenance_manifest_hash": provenance_summary.get("manifest_hash"),
        "manifest_hash": replay_packet["manifest_hash"],
        "manifest_requirement_count": len(requirements),
        "manifest_requirements_passed": passed,
        "manifest_requirements_failed": len(requirements) - passed,
        "failed_manifest_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "production_required_key_count": len(production_required_keys),
        "required_evidence_file_count": len(evidence_files),
        "selected_line_numbers": provenance_summary.get("selected_line_numbers"),
        "dropped_overlap_candidate_line_numbers": provenance_summary.get(
            "dropped_overlap_candidate_line_numbers"
        ),
        "line1381_off_grid_parameter_count": provenance_summary.get(
            "line1381_off_grid_parameter_count"
        ),
        "line1381_unpriced_proxy_t_pressure": provenance_summary.get(
            "line1381_unpriced_proxy_t_pressure"
        ),
        "line1378_delta_recovered": provenance_summary.get("line1378_delta_recovered"),
        "accepted_occurrence_removal": provenance_summary.get("accepted_occurrence_removal"),
        "accepted_proxy_t_reduction": provenance_summary.get("accepted_proxy_t_reduction"),
        "accepted_exit_route_count": provenance_summary.get("accepted_exit_route_count"),
        "submitted_manifest_exists": submitted_exists,
        "submitted_key_count": len(submitted) if submitted else 0,
        "missing_key_count": len(missing_keys),
        "production_keys_present_count": len(production_present),
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "validation_error_count": len(validation_errors),
    }
    return {
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "problem_ids": [25, 21],
        "title": "B1/B7 Cone_01 Resource-Escape Replay-Validation Manifest Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_provenance_manifest_gate": str(args.provenance_manifest_gate),
        "source_claim_boundary_seal": str(args.claim_boundary_seal),
        "source_physical_pricing_gate": str(args.physical_pricing_gate),
        "workload": provenance.get("workload", "qasmbench_medium_exact/gcm_h6.qasm"),
        "summary": summary,
        "resource_escape_replay_validation_manifest_packet": replay_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "The B1/B7 cone_01 resource-escape route now has a replay-validation manifest "
                "packet that must bind the accepted provenance manifest, Qiskit-loader seal, "
                "physical pricing, source map, line windows, B7 ledger replay, equivalence evidence, "
                "no-double-counting, exit route, and resource delta before B7 credit can count."
            ),
            "what_is_not_supported": (
                "No replay-validation manifest or escape artifact has been submitted or accepted; "
                "line 1381 remains unpriced, line 1378 remains unrecovered, occurrence certificates "
                "remain 0, and no B7 resource saving is supported."
            ),
            "next_gate": (
                "Submit B1-B7-cone01-resource-escape-replay-validation-manifest with the accepted "
                "provenance manifest hash, Qiskit-loader/physical-pricing/source-map replays, "
                "B7 ledger replay, one source-backed exit route, no-double-counting ledger, and claim boundary."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "occurrence_removal_claimed": False,
            "proxy_t_reduction_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    packet = payload["resource_escape_replay_validation_manifest_packet"]
    lines = [
        "# B1/B7 Cone_01 Resource-Escape Replay-Validation Manifest Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Manifest: `{summary['manifest_id']}`",
        f"- Provenance manifest: `{summary['provenance_manifest_id']}`",
        f"- Priority packet: `{summary['priority_packet_id']}`",
        f"- Priority packet hash: `{summary['priority_packet_hash']}`",
        f"- Provenance manifest hash: `{summary['provenance_manifest_hash']}`",
        f"- Manifest hash: `{summary['manifest_hash']}`",
        f"- Requirements passed/failed: `{summary['manifest_requirements_passed']}` / `{summary['manifest_requirements_failed']}`",
        f"- Failed requirement IDs: `{summary['failed_manifest_requirement_ids']}`",
        f"- Required key / production key / evidence file count: `{summary['required_key_count']}` / `{summary['production_required_key_count']}` / `{summary['required_evidence_file_count']}`",
        f"- Selected lines: `{summary['selected_line_numbers']}`",
        f"- Dropped overlap line(s): `{summary['dropped_overlap_candidate_line_numbers']}`",
        f"- line1381 off-grid parameters / unpriced proxy-T pressure: `{summary['line1381_off_grid_parameter_count']}` / `{summary['line1381_unpriced_proxy_t_pressure']}`",
        f"- line1378 delta recovered: `{summary['line1378_delta_recovered']}`",
        f"- accepted occurrence removal / proxy-T reduction: `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        f"- Submitted manifest exists: `{summary['submitted_manifest_exists']}`",
        f"- validation_error_count: `{summary['validation_error_count']}`",
        "",
        "## Replay-Validation Manifest Packet",
        "",
        f"- Submission path: `{packet['submission_artifact_path']}`",
        f"- Provenance manifest hash: `{packet['provenance_manifest_hash']}`",
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
            f"- resource_saving_claimed: {payload['claim_boundary']['resource_saving_claimed']}",
            f"- b7_ledger_improvement_claimed: {payload['claim_boundary']['b7_ledger_improvement_claimed']}",
            f"- occurrence_removal_claimed: {payload['claim_boundary']['occurrence_removal_claimed']}",
            f"- proxy_t_reduction_claimed: {payload['claim_boundary']['proxy_t_reduction_claimed']}",
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
        default=Path("results/B1_B7_cone01_resource_escape_provenance_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--claim-boundary-seal",
        type=Path,
        default=Path("results/B1_B7_cone01_openqasm3_claim_boundary_seal_gate_v0.json"),
    )
    parser.add_argument(
        "--physical-pricing-gate",
        type=Path,
        default=Path("results/B1_B7_cone01_physical_synthesis_pricing_gate_v0.json"),
    )
    parser.add_argument(
        "--submission-dir",
        type=Path,
        default=Path("results/B1_B7_cone01_resource_escape_replay_validation_manifest_submissions"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_resource_escape_replay_validation_manifest_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_resource_escape_replay_validation_manifest_gate.md"),
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
