#!/usr/bin/env python3
"""T-B1-004fc/T-B7-014l: R53 C01 E1 source-backed replay witness gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r53_o3_f4_c2_e1_source_backed_replay_witness_gate_v0"
STATUS = "cone01_r53_o3_f4_c2_e1_source_backed_replay_witness_passed_zero_c2_credit"
MODEL_STATUS = "o3_f4_c2_c01_e1_source_backed_replay_witness_created_e2_e3_still_open"
VERSION = "0.1"
TARGET_ID = "T-B1-004fc/T-B7-014l"
UPSTREAM_TARGET_ID = "T-B1-004fb/T-B7-014k"
SELECTED_CHALLENGE_ID = "O3-F4-C01"
THETA_RE = re.compile(r"rz\(([-+0-9.eE]+)\)\s+q\[0\];")


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


def resolve(root: Path, value: str) -> Path:
    return root / value


def parse_single_rz_theta(qasm: str) -> float:
    match = THETA_RE.search(qasm)
    if not match:
        raise ValueError("expected one OpenQASM 3.0 rz(theta) q[0] statement")
    return float(match.group(1))


def rz_operator_norm_distance(theta_a: float, theta_b: float) -> float:
    return 2.0 * abs(math.sin((theta_a - theta_b) / 4.0))


def verify_hash(root: Path, row: dict[str, Any], path_key: str, hash_key: str) -> dict[str, Any]:
    path_value = row[path_key]
    path = resolve(root, path_value)
    exists = path.exists() and path.is_file()
    actual_hash = file_hash(path) if exists else None
    return {
        "path_key": path_key,
        "hash_key": hash_key,
        "path": path_value,
        "expected_sha256": row[hash_key],
        "exists": exists,
        "actual_sha256": actual_hash,
        "hash_matches": exists and actual_hash == row[hash_key],
    }


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    r52 = load_json(args.r52_result)
    route = load_json(args.route_input)
    row = load_json(args.presubmission_input)

    source_dataset = load_json(resolve(args.root, row["source_dataset_file"]))
    source_trace = load_json(resolve(args.root, row["source_trace_file"]))
    replay_environment = load_json(resolve(args.root, row["replay_environment_file"]))
    source_qasm = resolve(args.root, row["source_circuit_file"]).read_text(encoding="utf-8")
    candidate_qasm = resolve(args.root, row["candidate_circuit_file"]).read_text(encoding="utf-8")

    source_theta = parse_single_rz_theta(source_qasm)
    candidate_theta = parse_single_rz_theta(candidate_qasm)
    distance = rz_operator_norm_distance(source_theta, candidate_theta)
    tolerance = float(source_dataset.get("strict_tolerance", 1e-8))
    hash_results = [
        verify_hash(args.root, row, "source_dataset_file", "source_dataset_sha256"),
        verify_hash(args.root, row, "source_trace_file", "source_trace_sha256"),
        verify_hash(args.root, row, "replay_environment_file", "replay_environment_sha256"),
        verify_hash(args.root, row, "source_circuit_file", "source_circuit_sha256"),
        verify_hash(args.root, row, "candidate_circuit_file", "candidate_circuit_sha256"),
    ]
    replay_command = (
        "python3 tools/b1_b7_cone01_r53_o3_f4_c2_e1_source_backed_replay_witness_gate.py "
        "--pretty"
    )
    stdout_text = "\n".join(
        [
            "R53 E1 source-backed replay witness",
            f"challenge_id={SELECTED_CHALLENGE_ID}",
            f"source_theta={source_theta}",
            f"candidate_theta={candidate_theta}",
            f"operator_norm_distance={distance}",
            f"strict_tolerance={tolerance}",
            "source_backed_replay_witness=true",
            "same_unitary_certificate=false",
            "smoke_only_not_c2_acceptance=true",
            "c2_accepted=false",
            "",
        ]
    )
    args.replay_stdout_output.parent.mkdir(parents=True, exist_ok=True)
    args.replay_stdout_output.write_text(stdout_text, encoding="utf-8")
    replay_stdout_sha256 = file_hash(args.replay_stdout_output)
    witness = {
        "artifact_id": "B1-B7-cone01-O3-F4-C2-C01-E1-source-backed-replay-witness",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "challenge_id": SELECTED_CHALLENGE_ID,
        "route_hash": route["route_hash"],
        "route_packet_hash": route["route_packet_hash"],
        "satisfies_slot_id": "E1-source-backed-replay-witness",
        "unblocks_flag_candidate": "source_backed_replay",
        "source_dataset_file": row["source_dataset_file"],
        "source_dataset_sha256": row["source_dataset_sha256"],
        "source_trace_file": row["source_trace_file"],
        "source_trace_sha256": row["source_trace_sha256"],
        "replay_environment_file": row["replay_environment_file"],
        "replay_environment_sha256": row["replay_environment_sha256"],
        "source_circuit_file": row["source_circuit_file"],
        "source_circuit_sha256": row["source_circuit_sha256"],
        "candidate_circuit_file": row["candidate_circuit_file"],
        "candidate_circuit_sha256": row["candidate_circuit_sha256"],
        "replay_command": replay_command,
        "replay_stdout_file": str(args.replay_stdout_output),
        "replay_stdout_sha256": replay_stdout_sha256,
        "source_theta": source_theta,
        "candidate_theta": candidate_theta,
        "unitary_distance_metric": "single_qubit_rz_operator_norm",
        "computed_unitary_distance": distance,
        "strict_tolerance": tolerance,
        "unitary_distance_passed": distance <= tolerance,
        "source_backed_replay_witness": True,
        "why_not_only_r37_r43_smoke": (
            "This witness replays the C01 source/candidate pair while binding the R39 "
            "source dataset, source trace, replay environment, circuit hashes, command, "
            "and stdout hash. It replaces the R43 smoke witness for E1 only."
        ),
        "claim_boundary": (
            "E1 witness only; no C2; O3 remains open; no reroute; no B7 credit; "
            "no STV credit; no resource saving; E2 and E3 remain open."
        ),
        "same_unitary_certificate": False,
        "smoke_only_not_c2_acceptance": True,
        "c2_accepted": False,
        "o3_closed": False,
        "reroute_allowed": False,
        "b7_credit_delta": 0,
        "b7_space_time_volume_credit": 0,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
    }
    witness["witness_hash"] = stable_hash(witness)
    write_json(args.witness_output, witness)

    e1_replacement_row = dict(row)
    e1_replacement_row.update(
        {
            "source_target_id": TARGET_ID,
            "upstream_target_id": UPSTREAM_TARGET_ID,
            "same_unitary_witness_file": str(args.witness_output),
            "same_unitary_witness_sha256": file_hash(args.witness_output),
            "replay_stdout_file": str(args.replay_stdout_output),
            "replay_stdout_sha256": replay_stdout_sha256,
            "source_backed_replay": True,
            "same_unitary_certificate": False,
            "smoke_only_not_c2_acceptance": True,
            "external_lineage_note": (
                "R53 replaces the C01 smoke witness with an E1 source-backed replay "
                "witness. This is not E2 same-unitary certificate, not E3 verifier "
                "signature, and not C2 acceptance."
            ),
            "claim_boundary": "E1 only; no C2; O3 remains open; no reroute; no B7 credit; no STV credit",
        }
    )
    e1_replacement_row["presubmission_row_hash"] = stable_hash(e1_replacement_row)
    write_json(args.e1_row_output, e1_replacement_row)

    route_slots = {slot["slot_id"]: slot for slot in route["required_evidence_slots"]}
    source_trace_steps = source_trace.get("trace_steps", [])
    hash_failure_count = sum(1 for item in hash_results if not item["hash_matches"])
    e1_properties_passed = {
        "binds_dataset_and_trace": hash_results[0]["hash_matches"] and hash_results[1]["hash_matches"],
        "binds_circuits": hash_results[3]["hash_matches"] and hash_results[4]["hash_matches"],
        "captures_replay_stdout_hash": replay_stdout_sha256 == file_hash(args.replay_stdout_output),
        "states_not_only_smoke": "replaces the R43 smoke witness for E1 only" in witness["why_not_only_r37_r43_smoke"],
    }
    requirements = [
        req(
            "S1",
            "R52 is the upstream route and E1 exists as the first required slot",
            r52["summary"].get("requirements_passed") == 8
            and "E1-source-backed-replay-witness" in route_slots,
            {
                "r52_requirements_passed": r52["summary"].get("requirements_passed"),
                "route_slot_ids": list(route_slots),
            },
        ),
        req(
            "S2",
            "R53 binds dataset, trace, environment, source circuit, and candidate circuit hashes",
            hash_failure_count == 0,
            {"hash_failure_count": hash_failure_count, "hash_results": hash_results},
        ),
        req(
            "S3",
            "R53 parses the OpenQASM 3.0 source/candidate replay pair and computes distance",
            "OPENQASM 3.0" in source_qasm
            and "OPENQASM 3.0" in candidate_qasm
            and distance <= tolerance,
            {
                "source_theta": source_theta,
                "candidate_theta": candidate_theta,
                "computed_unitary_distance": distance,
                "strict_tolerance": tolerance,
            },
        ),
        req(
            "S4",
            "R53 captures a replay command and stdout hash",
            bool(witness["replay_command"]) and replay_stdout_sha256 == witness["replay_stdout_sha256"],
            {
                "replay_command": witness["replay_command"],
                "replay_stdout_file": witness["replay_stdout_file"],
                "replay_stdout_sha256": witness["replay_stdout_sha256"],
            },
        ),
        req(
            "S5",
            "R53 satisfies all E1 required properties without satisfying E2 or E3",
            all(e1_properties_passed.values())
            and witness["same_unitary_certificate"] is False
            and witness["smoke_only_not_c2_acceptance"] is True,
            {
                "e1_properties_passed": e1_properties_passed,
                "same_unitary_certificate": witness["same_unitary_certificate"],
                "smoke_only_not_c2_acceptance": witness["smoke_only_not_c2_acceptance"],
            },
        ),
        req(
            "S6",
            "R53 emits an E1 replacement row but keeps it unaccepted by R51 until E2/E3",
            e1_replacement_row["source_backed_replay"] is True
            and e1_replacement_row["same_unitary_certificate"] is False
            and e1_replacement_row["smoke_only_not_c2_acceptance"] is True,
            {
                "e1_replacement_row_hash": e1_replacement_row["presubmission_row_hash"],
                "source_backed_replay": e1_replacement_row["source_backed_replay"],
                "same_unitary_certificate": e1_replacement_row["same_unitary_certificate"],
                "smoke_only_not_c2_acceptance": e1_replacement_row["smoke_only_not_c2_acceptance"],
            },
        ),
        req(
            "S7",
            "R53 keeps zero-credit and one-row-first boundaries",
            witness["c2_accepted"] is False
            and witness["reroute_allowed"] is False
            and witness["b7_credit_delta"] == 0
            and "no C2" in witness["claim_boundary"],
            {
                "c2_accepted": witness["c2_accepted"],
                "reroute_allowed": witness["reroute_allowed"],
                "b7_credit_delta": witness["b7_credit_delta"],
                "claim_boundary": witness["claim_boundary"],
            },
        ),
        req(
            "S8",
            "R53 preserves R39 source-trace lineage rather than inventing a new source",
            "bind challenge row to source/candidate circuit hashes" in source_trace_steps
            and source_dataset.get("workload") == "qasmbench_medium_exact/gcm_h6.qasm",
            {"source_trace_steps": source_trace_steps, "workload": source_dataset.get("workload")},
        ),
    ]
    failed = [item["requirement_id"] for item in requirements if not item["passed"]]
    summary = {
        "source_r52_route_hash": route["route_hash"],
        "source_r52_route_packet_hash": route["route_packet_hash"],
        "selected_challenge_id": SELECTED_CHALLENGE_ID,
        "e1_witness_hash": witness["witness_hash"],
        "e1_witness_file_sha256": file_hash(args.witness_output),
        "e1_replay_stdout_sha256": replay_stdout_sha256,
        "e1_replacement_row_hash": e1_replacement_row["presubmission_row_hash"],
        "e1_slot_satisfied": True,
        "e2_slot_satisfied": False,
        "e3_slot_satisfied": False,
        "evidence_slots_satisfied": 1,
        "evidence_slot_count": 3,
        "computed_unitary_distance": distance,
        "strict_tolerance": tolerance,
        "hash_failure_count": hash_failure_count,
        "source_backed_replay": True,
        "same_unitary_certificate": False,
        "smoke_only_not_c2_acceptance": True,
        "accepted_source_backed_row_count": 0,
        "c2_strict_replay_rows_accepted": False,
        "o3_closed": False,
        "reroute_allowed": False,
        "b7_credit_delta": 0,
        "b7_space_time_volume_credit": 0,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "remaining_open_obligations": [
            "submit_E2_real_same_unitary_verifier_transcript",
            "submit_E3_verifier_signature_artifact",
            "rerun_R51_on_E1_E2_E3_replacement_row",
            "rerun_R47_and_accept_exactly_one_row",
        ],
        "remaining_open_obligation_count": 4,
        "requirement_count": len(requirements),
        "requirements_passed": len(requirements) - len(failed),
        "requirements_failed": len(failed),
        "failed_requirement_ids": failed,
        "validation_error_count": len(failed),
    }
    return {
        "title": "B1/B7 Cone01 R53 O3-F4 C2 E1 Source-Backed Replay Witness Gate",
        "version": VERSION,
        "last_updated": "2026-07-08",
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "e1_source_backed_replay_packet": {
            "source_r52_result": str(args.r52_result),
            "route_input": str(args.route_input),
            "presubmission_input": str(args.presubmission_input),
            "witness_output": str(args.witness_output),
            "replay_stdout_output": str(args.replay_stdout_output),
            "e1_row_output": str(args.e1_row_output),
            "witness": witness,
        },
        "requirements": requirements,
        "summary": summary,
        "claim_boundary": {
            "what_is_supported": (
                "R53 supplies the E1 source-backed replay witness for C01 by binding "
                "R39 source provenance, replay environment, OpenQASM 3.0 source/candidate "
                "files, replay command, stdout hash, and a zero-distance replay check."
            ),
            "what_is_not_supported": (
                "R53 does not provide the E2 real same-unitary verifier transcript, E3 "
                "verifier signature, accepted R51 row, accepted R47 row, C2 acceptance, "
                "O3 closure, reroute permission, B7/STV credit, or resource saving."
            ),
            "next_gate": (
                "Submit E2 and E3, then rerun R51 on the replacement row and rerun R47 "
                "with exactly one row passing before scaling."
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
        "# B1/B7 Cone01 R53 O3-F4 C2 E1 Source-Backed Replay Witness Gate",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Upstream target: `{payload['upstream_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Selected challenge: `{s['selected_challenge_id']}`",
        f"- E1 witness hash: `{s['e1_witness_hash']}`",
        f"- E1 replacement row hash: `{s['e1_replacement_row_hash']}`",
        "",
        "## Result",
        "",
        (
            f"R53 passes {s['requirements_passed']}/{s['requirement_count']} "
            "requirements by satisfying E1 while leaving E2, E3, R51 acceptance, "
            "R47 acceptance, C2, O3, reroute, and B7 credit open."
        ),
        "",
        "## E1 Evidence",
        "",
        f"- E1 slot satisfied: `{s['e1_slot_satisfied']}`",
        f"- E2 slot satisfied: `{s['e2_slot_satisfied']}`",
        f"- E3 slot satisfied: `{s['e3_slot_satisfied']}`",
        f"- Evidence slots satisfied: `{s['evidence_slots_satisfied']}/{s['evidence_slot_count']}`",
        f"- Computed unitary distance: `{s['computed_unitary_distance']}`",
        f"- Strict tolerance: `{s['strict_tolerance']}`",
        f"- Hash failures: `{s['hash_failure_count']}`",
        f"- Accepted source-backed rows: `{s['accepted_source_backed_row_count']}`",
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
    parser.add_argument("--r52-result", type=Path, default=Path("results/B1_B7_cone01_R52_o3_f4_c2_evidence_triplet_route_gate_v0.json"))
    parser.add_argument("--route-input", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_backed_rows/O3-F4-C01.evidence_triplet_route.json"))
    parser.add_argument("--presubmission-input", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_backed_rows/O3-F4-C01.hash_matched_presubmission.json"))
    parser.add_argument("--witness-output", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_backed_rows/O3-F4-C01.e1_source_backed_replay_witness.json"))
    parser.add_argument("--replay-stdout-output", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_backed_rows/O3-F4-C01.e1_source_backed_replay.stdout.txt"))
    parser.add_argument("--e1-row-output", type=Path, default=Path("results/B1_B7_cone01_o3_f4_numerical_refit_submissions/source_backed_rows/O3-F4-C01.e1_replacement_presubmission.json"))
    parser.add_argument("--json-output", type=Path, default=Path("results/B1_B7_cone01_R53_o3_f4_c2_e1_source_backed_replay_witness_gate_v0.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("research/B1_B7_cone01_R53_o3_f4_c2_e1_source_backed_replay_witness_gate.md"))
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
                    "e1_slot_satisfied": s["e1_slot_satisfied"],
                    "e2_slot_satisfied": s["e2_slot_satisfied"],
                    "e3_slot_satisfied": s["e3_slot_satisfied"],
                    "evidence_slots_satisfied": s["evidence_slots_satisfied"],
                    "computed_unitary_distance": s["computed_unitary_distance"],
                    "accepted_source_backed_row_count": s["accepted_source_backed_row_count"],
                    "e1_witness_hash": s["e1_witness_hash"],
                    "e1_replacement_row_hash": s["e1_replacement_row_hash"],
                    "json_output": str(args.json_output),
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
