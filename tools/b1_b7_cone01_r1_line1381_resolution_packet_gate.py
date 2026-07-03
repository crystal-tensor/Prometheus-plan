#!/usr/bin/env python3
"""T-B1-004dc/T-B7-012l: R1 line-1381 resolution packet gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r1_line1381_resolution_packet_gate_v0"
STATUS = "cone01_r1_line1381_resolution_packet_open_missing_artifact"
MODEL_STATUS = "line1381_resolution_packet_required_before_resource_escape_acceptance"
VERSION = "0.1"
EXPECTED_R1_PACKET_ID = "B1-B7-cone01-R1-line1381-resolution"
EXPECTED_ACCEPTANCE_PACKET_ID = "B1-B7-cone01-resource-escape-acceptance-packet"
EXPECTED_TRIAGE_METHOD = "b1_b7_cone01_post_boundary_submission_triage_v0"
EXPECTED_ACCEPTANCE_METHOD = "b1_b7_cone01_resource_escape_acceptance_packet_gate_v0"
EXPECTED_SEEDED_BOUNDARY_METHOD = "b1_b7_cone01_openqasm3_qiskit_loader_seeded_resource_boundary_gate_v0"
EXPECTED_SOURCE_FAILED_IDS = ["P6", "P7", "P8"]
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
    triage = load_json(args.post_boundary_triage)
    acceptance = load_json(args.acceptance_packet_gate)
    seeded_boundary = load_json(args.seeded_resource_boundary)
    triage_summary = triage["summary"]
    acceptance_summary = acceptance["summary"]
    seeded_summary = seeded_boundary["summary"]

    submission_path = args.submission_dir / f"{EXPECTED_R1_PACKET_ID}.json"
    submitted_exists = submission_path.exists()
    submitted = load_json(submission_path) if submitted_exists else None

    required_keys = [
        "packet_id",
        "source_triage_id",
        "source_acceptance_packet_id",
        "triage_hash",
        "acceptance_packet_hash",
        "seeded_resource_boundary_hash",
        "selected_line_numbers",
        "line1381_resolution_route",
        "line1381_off_grid_parameter_count_before",
        "line1381_off_grid_parameter_count_after",
        "line1381_resolution_artifact_hash",
        "full_replay_or_symbolic_equivalence_hash",
        "physical_pricing_replay_hash",
        "resource_delta_ledger_hash",
        "no_double_counting_ledger_hash",
        "claim_boundary",
        "source_evidence_files_present",
    ]
    production_required_keys = [
        "line1381_resolution_route",
        "line1381_off_grid_parameter_count_after",
        "line1381_resolution_artifact_hash",
        "full_replay_or_symbolic_equivalence_hash",
        "physical_pricing_replay_hash",
        "resource_delta_ledger_hash",
        "no_double_counting_ledger_hash",
        "claim_boundary",
        "source_evidence_files_present",
    ]
    required_evidence_files = [
        "line1381_resolution_manifest",
        "line1381_rewritten_patch_or_parameter_elimination_artifact",
        "full_replay_or_symbolic_equivalence_certificate",
        "physical_pricing_replay",
        "resource_delta_ledger",
        "no_double_counting_ledger",
        "qiskit_loader_seeded_replay_reference",
        "claim_boundary_note",
    ]

    missing_keys = [key for key in required_keys if submitted is None or key not in submitted]
    production_present = [
        key for key in production_required_keys if submitted is not None and submitted.get(key) is not None
    ]

    source_backed = submitted is not None and submitted.get("source_evidence_files_present") is True
    source_bound = (
        submitted is not None
        and submitted.get("packet_id") == EXPECTED_R1_PACKET_ID
        and submitted.get("source_triage_id") == triage_summary.get("triage_id")
        and submitted.get("source_acceptance_packet_id") == EXPECTED_ACCEPTANCE_PACKET_ID
        and submitted.get("triage_hash") == triage_summary.get("triage_hash")
        and submitted.get("acceptance_packet_hash") == acceptance_summary.get("acceptance_packet_hash")
    )
    selected_lines_bound = submitted is not None and submitted.get("selected_line_numbers") == [268, 1381]
    line1381_eliminated = (
        submitted is not None
        and submitted.get("line1381_off_grid_parameter_count_before") == 5
        and submitted.get("line1381_off_grid_parameter_count_after") == 0
        and bool(submitted.get("line1381_resolution_artifact_hash"))
        and bool(submitted.get("full_replay_or_symbolic_equivalence_hash"))
    )
    pricing_beats_boundary = (
        submitted is not None
        and isinstance(submitted.get("physical_pricing_replay"), dict)
        and submitted["physical_pricing_replay"].get("cost_minus_credit", 1) <= 0
        and bool(submitted.get("physical_pricing_replay_hash"))
        and bool(submitted.get("resource_delta_ledger_hash"))
    )
    claim_boundary_bound = (
        submitted is not None
        and isinstance(submitted.get("claim_boundary"), dict)
        and submitted["claim_boundary"].get("resource_saving_claimed") is False
        and submitted["claim_boundary"].get("b7_ledger_improvement_claimed") is False
        and submitted["claim_boundary"].get("accepted_before_resource_escape_packet") is False
    )

    r1_packet = {
        "packet_id": EXPECTED_R1_PACKET_ID,
        "work_packet_id": "R1",
        "source_post_boundary_triage": str(args.post_boundary_triage),
        "source_acceptance_packet_gate": str(args.acceptance_packet_gate),
        "source_seeded_resource_boundary": str(args.seeded_resource_boundary),
        "triage_hash": triage_summary.get("triage_hash"),
        "acceptance_packet_hash": acceptance_summary.get("acceptance_packet_hash"),
        "seeded_resource_boundary_status": seeded_boundary.get("status"),
        "submission_artifact_path": str(submission_path),
        "selected_line_numbers": triage_summary.get("selected_line_numbers"),
        "dropped_overlap_candidate_line_numbers": triage_summary.get(
            "dropped_overlap_candidate_line_numbers"
        ),
        "line1381_off_grid_parameter_count_before": triage_summary.get(
            "line1381_off_grid_parameter_count"
        ),
        "line1381_unpriced_proxy_t_pressure_before": triage_summary.get(
            "line1381_unpriced_proxy_t_pressure"
        ),
        "required_keys": required_keys,
        "production_required_keys": production_required_keys,
        "required_evidence_files": required_evidence_files,
        "accepted_only_if": [
            "packet_id equals B1-B7-cone01-R1-line1381-resolution",
            "triage_hash and acceptance_packet_hash match the locked source gates",
            "selected_line_numbers remain [268, 1381] and line1378 remains handled by a no-double-counting ledger",
            "line1381_off_grid_parameter_count_after is 0 with full replay or symbolic equivalence, or physical pricing replay beats the current cost-minus-credit boundary",
            "resource_delta_ledger_hash and no_double_counting_ledger_hash are present",
            "claim_boundary forbids resource-saving and B7-credit claims before the resource-escape acceptance packet accepts the route",
        ],
    }
    r1_packet["packet_hash"] = stable_hash(r1_packet)

    requirements = [
        requirement(
            "P1",
            "Post-boundary triage is current and exposes R1 as ready",
            triage.get("method") == EXPECTED_TRIAGE_METHOD
            and triage_summary.get("validation_error_count") == 0
            and "R1" in triage_summary.get("ready_packet_ids", []),
            {
                "source_method": triage.get("method"),
                "ready_packet_ids": triage_summary.get("ready_packet_ids"),
                "validation_error_count": triage_summary.get("validation_error_count"),
            },
        ),
        requirement(
            "P2",
            "Resource-escape acceptance packet remains open on missing submitted evidence only",
            acceptance.get("method") == EXPECTED_ACCEPTANCE_METHOD
            and acceptance_summary.get("submitted_acceptance_packet_exists") is False
            and acceptance_summary.get("failed_acceptance_requirement_ids") == EXPECTED_SOURCE_FAILED_IDS,
            {
                "source_method": acceptance.get("method"),
                "submitted_acceptance_packet_exists": acceptance_summary.get(
                    "submitted_acceptance_packet_exists"
                ),
                "failed_acceptance_requirement_ids": acceptance_summary.get(
                    "failed_acceptance_requirement_ids"
                ),
            },
        ),
        requirement(
            "P3",
            "Seeded replay evidence is accepted but resource blockers remain failed",
            seeded_boundary.get("method") == EXPECTED_SEEDED_BOUNDARY_METHOD
            and seeded_summary.get("qiskit_loader_seeded_product_replay_passed") is True
            and seeded_summary.get("resource_boundary_failed_blocker_count") == 5
            and seeded_summary.get("accepted_occurrence_removal") == 0,
            {
                "source_method": seeded_boundary.get("method"),
                "qiskit_loader_seeded_product_replay_passed": seeded_summary.get(
                    "qiskit_loader_seeded_product_replay_passed"
                ),
                "resource_boundary_failed_blocker_count": seeded_summary.get(
                    "resource_boundary_failed_blocker_count"
                ),
                "accepted_occurrence_removal": seeded_summary.get("accepted_occurrence_removal"),
            },
        ),
        requirement(
            "P4",
            "Line-1381 blocker is still the five-parameter 100-proxy-T boundary",
            triage_summary.get("line1381_off_grid_parameter_count") == 5
            and triage_summary.get("line1381_unpriced_proxy_t_pressure") == 100,
            {
                "line1381_off_grid_parameter_count": triage_summary.get(
                    "line1381_off_grid_parameter_count"
                ),
                "line1381_unpriced_proxy_t_pressure": triage_summary.get(
                    "line1381_unpriced_proxy_t_pressure"
                ),
            },
        ),
        requirement(
            "P5",
            "R1 packet schema and evidence classes are locked",
            len(required_keys) == 17
            and len(production_required_keys) == 9
            and len(required_evidence_files) == 8,
            {
                "required_key_count": len(required_keys),
                "production_required_key_count": len(production_required_keys),
                "required_evidence_file_count": len(required_evidence_files),
            },
        ),
        requirement(
            "P6",
            "R1 line-1381 resolution artifact has been submitted",
            submitted_exists,
            {"submission_artifact_path": str(submission_path), "exists": submitted_exists},
        ),
        requirement(
            "P7",
            "Submitted R1 artifact satisfies the locked schema",
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
            "Submitted R1 artifact is source-backed, source-bound, line-bound, route-valid, and claim-boundary-bound",
            source_backed
            and source_bound
            and selected_lines_bound
            and (line1381_eliminated or pricing_beats_boundary)
            and claim_boundary_bound,
            {
                "source_backed": source_backed,
                "source_bound": source_bound,
                "selected_lines_bound": selected_lines_bound,
                "line1381_eliminated": line1381_eliminated,
                "pricing_beats_boundary": pricing_beats_boundary,
                "claim_boundary_bound": claim_boundary_bound,
            },
        ),
        requirement(
            "P9",
            "Forbidden B1/B7 resource and ledger claims remain false",
            triage_summary.get("b1_resource_saving_claimed") is False
            and triage_summary.get("b7_ledger_improvement_claimed") is False
            and triage_summary.get("b7_space_time_volume_credit") == 0,
            {
                "b1_resource_saving_claimed": triage_summary.get("b1_resource_saving_claimed"),
                "b7_ledger_improvement_claimed": triage_summary.get(
                    "b7_ledger_improvement_claimed"
                ),
                "b7_space_time_volume_credit": triage_summary.get("b7_space_time_volume_credit"),
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids != EXPECTED_FAILED_IDS:
        validation_errors.append(f"unexpected R1 line1381 packet failures: {failed_ids}")
    if submitted_exists:
        validation_errors.append("gate expected no submitted R1 artifact until a compiler PR supplies one")

    summary = {
        "r1_packet_id": EXPECTED_R1_PACKET_ID,
        "r1_packet_hash": r1_packet["packet_hash"],
        "triage_hash": triage_summary.get("triage_hash"),
        "acceptance_packet_hash": acceptance_summary.get("acceptance_packet_hash"),
        "source_acceptance_packet_id": EXPECTED_ACCEPTANCE_PACKET_ID,
        "requirement_count": len(requirements),
        "requirements_passed": passed,
        "requirements_failed": len(requirements) - passed,
        "failed_requirement_ids": failed_ids,
        "required_key_count": len(required_keys),
        "production_required_key_count": len(production_required_keys),
        "required_evidence_file_count": len(required_evidence_files),
        "selected_line_numbers": triage_summary.get("selected_line_numbers"),
        "dropped_overlap_candidate_line_numbers": triage_summary.get(
            "dropped_overlap_candidate_line_numbers"
        ),
        "line1381_off_grid_parameter_count_before": triage_summary.get(
            "line1381_off_grid_parameter_count"
        ),
        "line1381_unpriced_proxy_t_pressure_before": triage_summary.get(
            "line1381_unpriced_proxy_t_pressure"
        ),
        "submitted_r1_artifact_exists": submitted_exists,
        "missing_key_count": len(missing_keys),
        "production_keys_present_count": len(production_present),
        "accepted_exit_route_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "b7_credit_delta": 0,
        "b1_resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "b7_space_time_volume_credit": 0,
        "validation_error_count": len(validation_errors),
    }

    return {
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "source_target_id": "T-B1-004dc/T-B7-012l",
        "title": "B1/B7 Cone01 R1 Line-1381 Resolution Packet Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_post_boundary_triage": str(args.post_boundary_triage),
        "source_acceptance_packet_gate": str(args.acceptance_packet_gate),
        "source_seeded_resource_boundary": str(args.seeded_resource_boundary),
        "summary": summary,
        "r1_line1381_resolution_packet": r1_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "R1 now has a source-bound packet schema for resolving the line-1381 "
                "off-grid local-U3 blocker before any resource-escape acceptance can count."
            ),
            "what_is_not_supported": (
                "No R1 artifact, line-1381 resolution, accepted exit route, occurrence "
                "removal, proxy-T reduction, B7 ledger credit, or resource saving is supported."
            ),
            "next_gate": (
                "Submit B1-B7-cone01-R1-line1381-resolution with a source-backed "
                "line1381 resolution artifact, full replay or symbolic equivalence, physical "
                "pricing replay, resource-delta ledger, no-double-counting ledger, and claim boundary."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "occurrence_removal_claimed": False,
            "proxy_t_reduction_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    packet = payload["r1_line1381_resolution_packet"]
    lines = [
        f"# {payload['title']}",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- R1 packet: `{s['r1_packet_id']}`",
        f"- R1 packet hash: `{s['r1_packet_hash']}`",
        f"- Triage hash: `{s['triage_hash']}`",
        f"- Acceptance packet hash: `{s['acceptance_packet_hash']}`",
        "",
        "## Result",
        "",
        (
            f"The R1 line-1381 gate passes {s['requirements_passed']}/{s['requirement_count']} "
            f"requirements and intentionally fails {s['failed_requirement_ids']} because no "
            "source-backed R1 resolution artifact has been submitted."
        ),
        "",
        "## Locked R1 Packet",
        "",
        f"- Submission path: `{packet['submission_artifact_path']}`",
        f"- Required keys: `{s['required_key_count']}`",
        f"- Production required keys: `{s['production_required_key_count']}`",
        f"- Evidence file classes: `{s['required_evidence_file_count']}`",
        "",
        "Required evidence files:",
        "",
    ]
    for item in packet["required_evidence_files"]:
        lines.append(f"- {item}")
    lines.extend(["", "Acceptance predicates:", ""])
    for item in packet["accepted_only_if"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            f"- Selected lines: `{s['selected_line_numbers']}`",
            f"- Dropped overlap line: `{s['dropped_overlap_candidate_line_numbers']}`",
            f"- line1381 off-grid parameters before: `{s['line1381_off_grid_parameter_count_before']}`",
            f"- line1381 unpriced proxy-T pressure before: `{s['line1381_unpriced_proxy_t_pressure_before']}`",
            f"- Submitted R1 artifact exists: `{s['submitted_r1_artifact_exists']}`",
            f"- Accepted exit routes / occurrence removal / proxy-T reduction: `{s['accepted_exit_route_count']}` / `{s['accepted_occurrence_removal']}` / `{s['accepted_proxy_t_reduction']}`",
            f"- B7 credit delta / STV credit: `{s['b7_credit_delta']}` / `{s['b7_space_time_volume_credit']}`",
            "",
            "## Requirement Results",
            "",
        ]
    )
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
            "This packet gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, or a solved B1/B7 problem.",
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
        "--post-boundary-triage",
        type=Path,
        default=Path("results/B1_B7_cone01_post_boundary_submission_triage_v0.json"),
    )
    parser.add_argument(
        "--acceptance-packet-gate",
        type=Path,
        default=Path("results/B1_B7_cone01_resource_escape_acceptance_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--seeded-resource-boundary",
        type=Path,
        default=Path("results/B1_B7_cone01_openqasm3_qiskit_loader_seeded_resource_boundary_gate_v0.json"),
    )
    parser.add_argument(
        "--submission-dir",
        type=Path,
        default=Path("results/B1_B7_cone01_r1_line1381_resolution_submissions"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_R1_line1381_resolution_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_R1_line1381_resolution_packet_gate.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-03")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "r1_packet_hash": payload["summary"]["r1_packet_hash"],
                "requirements_passed": payload["summary"]["requirements_passed"],
                "requirements_failed": payload["summary"]["requirements_failed"],
                "failed_requirement_ids": payload["summary"]["failed_requirement_ids"],
                "validation_error_count": payload["summary"]["validation_error_count"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if payload["validation_errors"]:
        raise SystemExit("B1/B7 R1 line1381 resolution packet gate validation failed")


if __name__ == "__main__":
    main()
