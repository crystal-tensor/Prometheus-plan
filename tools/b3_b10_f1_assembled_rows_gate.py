#!/usr/bin/env python3
"""T-B3-039/T-B10-015z: assemble B3/B10 F1 covariance rows from completed shards."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


METHOD = "b3_b10_f1_assembled_rows_gate_v0"
STATUS = "f1_three_remaining_rows_assembled_zero_credit"
MODEL_STATUS = "h2_candidate_plus_h2o_n2_lih_rows_assembled_no_acceptance_credit"
SOURCE_TARGET_ID = "T-B3-039/T-B10-015z"
EXPECTED_WORKER_METHOD = "b3_b10_f1_full_covariance_row_worker_v0"
EXPECTED_ROW_PACKET_METHOD = "b3_b10_f1_full_covariance_row_packet_gate_v0"
EXPECTED_H2_CANDIDATE_METHOD = "b3_b10_f1_pilot_row_candidate_gate_v0"
EXPECTED_TOTAL_SHARDS = 65
EXPECTED_F1_ROW_COUNT = 4

MOLECULES = [
    {
        "row_id": "B3B10-F1-row-h2o-symmetric-oh-stretch-full-covariance-v0",
        "molecule": "h2o_symmetric_oh_stretch",
        "shard_dir": "h2o_symmetric_oh_stretch",
        "expected_shards": 7,
        "batch_gate": "results/B3_B10_F1_h2o_shard_batch_gate_v0.json",
        "batch_method": "b3_b10_f1_h2o_shard_batch_gate_v0",
        "batch_hash_field": "h2o_shard_batch_hash",
        "expected_group_count": 3130,
    },
    {
        "row_id": "B3B10-F1-row-n2-bond-stretch-full-covariance-v0",
        "molecule": "n2_bond_stretch",
        "shard_dir": "n2_bond_stretch",
        "expected_shards": 19,
        "batch_gate": "results/B3_B10_F1_n2_shard_batch_gate_v0.json",
        "batch_method": "b3_b10_f1_n2_shard_batch_gate_v0",
        "batch_hash_field": "n2_shard_batch_hash",
        "expected_group_count": 9476,
    },
    {
        "row_id": "B3B10-F1-row-lih-bond-stretch-full-covariance-v0",
        "molecule": "lih_bond_stretch",
        "shard_dir": "lih_bond_stretch",
        "expected_shards": 39,
        "batch_gate": "results/B3_B10_F1_lih_shard_batch_gate_v0.json",
        "batch_method": "b3_b10_f1_lih_shard_batch_gate_v0",
        "batch_hash_field": "lih_prefix_shard_batch_hash",
        "expected_group_count": 19645,
    },
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2 if pretty else None, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def requirement(req_id: str, passed: bool, description: str, evidence: Any) -> dict[str, Any]:
    return {
        "id": req_id,
        "passed": bool(passed),
        "description": description,
        "evidence": evidence,
    }


def summarize_shard(path: Path) -> dict[str, Any]:
    shard = load_json(path)
    summary = shard.get("full_covariance_matrix_shard", {}).get("summary", {})
    manifest = shard.get("qwc_group_manifest", {})
    return {
        "path": str(path),
        "file_hash": file_hash(path),
        "shard_id": shard.get("shard_id"),
        "method": shard.get("method"),
        "status": shard.get("status"),
        "molecule": shard.get("molecule"),
        "group_start_inclusive": shard.get("group_start_inclusive"),
        "group_end_exclusive": shard.get("group_end_exclusive"),
        "compiled_qwc_group_count": manifest.get("compiled_qwc_group_count"),
        "group_count": summary.get("group_count"),
        "nonzero_covariance_pair_count": summary.get("nonzero_covariance_pair_count"),
        "variance_sum": summary.get("variance_sum"),
        "sqrt_variance_sum": summary.get("sqrt_variance_sum"),
        "full_covariance_matrix_shard_hash": shard.get("full_covariance_matrix_shard_hash"),
        "compiled_state_replay_hash": shard.get("compiled_state_replay_hash"),
        "qwc_group_manifest_hash": shard.get("qwc_group_manifest_hash"),
        "measurement_basis_manifest_hash": shard.get("measurement_basis_manifest_hash"),
        "stdout_stderr_returncode_hash": shard.get("stdout_stderr_returncode_hash"),
        "wall_time_memory_ledger_hash": shard.get("wall_time_memory_ledger_hash"),
        "claim_boundary_hash": shard.get("claim_boundary_hash"),
        "validation_error_count": len(shard.get("validation_errors", [])),
    }


def shard_paths(root: Path, config: dict[str, Any]) -> list[Path]:
    shard_dir = root / str(config["shard_dir"])
    return [shard_dir / f"shard_{index:03d}.json" for index in range(1, int(config["expected_shards"]) + 1)]


def assemble_row(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    paths = shard_paths(root, config)
    shards = [summarize_shard(path) for path in paths if path.exists()]
    starts = [item["group_start_inclusive"] for item in shards]
    ends = [item["group_end_exclusive"] for item in shards]
    contiguous = bool(shards) and starts[0] == 0 and all(
        previous["group_end_exclusive"] == current["group_start_inclusive"]
        for previous, current in zip(shards, shards[1:])
    )
    row = {
        "row_id": config["row_id"],
        "molecule": config["molecule"],
        "source_shard_dir": str(root / str(config["shard_dir"])),
        "source_batch_gate": config["batch_gate"],
        "expected_shard_count": config["expected_shards"],
        "produced_shard_count": len(shards),
        "expected_group_count": config["expected_group_count"],
        "assembled_group_count": sum(int(item["group_count"]) for item in shards),
        "nonzero_covariance_pair_count": sum(int(item["nonzero_covariance_pair_count"]) for item in shards),
        "variance_sum": sum(float(item["variance_sum"]) for item in shards),
        "sqrt_variance_sum": sum(float(item["sqrt_variance_sum"]) for item in shards),
        "first_group_start": starts[0] if starts else None,
        "last_group_end": ends[-1] if ends else None,
        "contiguous": contiguous,
        "shard_hashes": [item["full_covariance_matrix_shard_hash"] for item in shards],
        "compiled_state_replay_hashes": [item["compiled_state_replay_hash"] for item in shards],
        "qwc_group_manifest_hashes": [item["qwc_group_manifest_hash"] for item in shards],
        "measurement_basis_manifest_hashes": [item["measurement_basis_manifest_hash"] for item in shards],
        "stdout_stderr_returncode_hashes": [item["stdout_stderr_returncode_hash"] for item in shards],
        "wall_time_memory_ledger_hashes": [item["wall_time_memory_ledger_hash"] for item in shards],
        "claim_boundary_hashes": [item["claim_boundary_hash"] for item in shards],
        "source_shards": shards,
        "validation_errors": [],
        "claim_boundary": {
            "what_is_supported": "A row-level covariance summary was assembled from all available shard summaries for this molecule.",
            "what_is_not_supported": "This is not a four-row F1 acceptance packet, not a denominator win, not B3/B10 credit, and not quantum advantage.",
        },
    }
    row["row_replay_hash"] = canonical_hash(
        {
            "row_id": row["row_id"],
            "molecule": row["molecule"],
            "shard_hashes": row["shard_hashes"],
            "assembled_group_count": row["assembled_group_count"],
            "nonzero_covariance_pair_count": row["nonzero_covariance_pair_count"],
            "variance_sum": row["variance_sum"],
        }
    )
    row["row_hash"] = canonical_hash(row)
    return row


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    row_packet = load_json(args.row_packet_gate)
    h2_candidate_gate = load_json(args.h2_candidate_gate)
    row_packet_summary = row_packet.get("summary", {})
    h2_summary = h2_candidate_gate.get("summary", {})
    h2_candidate = h2_candidate_gate.get("candidate_row", {})
    rows = [assemble_row(args.shard_root, config) for config in MOLECULES]
    batch_gates = []
    for config in MOLECULES:
        path = Path(str(config["batch_gate"]))
        batch = load_json(path)
        summary = batch.get("summary", {})
        batch_gates.append(
            {
                "path": str(path),
                "file_hash": file_hash(path),
                "method": batch.get("method"),
                "status": batch.get("status"),
                "source_target_id": batch.get("source_target_id"),
                "validation_error_count": summary.get("validation_error_count"),
                "failed_requirement_ids": summary.get("failed_requirement_ids"),
                "batch_hash": summary.get(str(config["batch_hash_field"])),
            }
        )

    assembled_row_count = sum(
        1
        for row in rows
        if row["produced_shard_count"] == row["expected_shard_count"]
        and row["assembled_group_count"] == row["expected_group_count"]
        and row["contiguous"]
    )
    source_shard_count = sum(row["produced_shard_count"] for row in rows)
    candidate_row_ids = [h2_summary.get("candidate_row_id")] + [row["row_id"] for row in rows]
    candidate_row_hashes = [h2_summary.get("candidate_row_hash")] + [row["row_hash"] for row in rows]
    row_bundle = {
        "bundle_id": "B3B10-F1-h2-plus-h2o-n2-lih-row-candidate-bundle-v0",
        "source_row_packet_gate": str(args.row_packet_gate),
        "source_h2_candidate_gate": str(args.h2_candidate_gate),
        "assembled_row_ids": [row["row_id"] for row in rows],
        "assembled_row_hashes": [row["row_hash"] for row in rows],
        "h2_candidate_row_id": h2_summary.get("candidate_row_id"),
        "h2_candidate_row_hash": h2_summary.get("candidate_row_hash"),
        "candidate_row_ids": candidate_row_ids,
        "candidate_row_hashes": candidate_row_hashes,
        "source_batch_gates": batch_gates,
        "rows": rows,
        "claim_boundary": {
            "what_is_supported": "The H2 pilot candidate and the assembled H2O/N2/LiH row summaries now form a four-row F1 candidate bundle.",
            "what_is_not_supported": "This is not an accepted F1 artifact, not a same-access denominator win, not B3/B10 credit, and not quantum advantage.",
        },
    }
    row_bundle["row_bundle_hash"] = canonical_hash(row_bundle)

    requirements = [
        requirement(
            "P1",
            row_packet.get("method") == EXPECTED_ROW_PACKET_METHOD
            and row_packet_summary.get("validation_error_count") == 0,
            "F1 row packet gate is current",
            {
                "method": row_packet.get("method"),
                "validation_error_count": row_packet_summary.get("validation_error_count"),
                "source_f1_packet_hash": row_packet_summary.get("f1_packet_hash"),
            },
        ),
        requirement(
            "P2",
            h2_candidate_gate.get("method") == EXPECTED_H2_CANDIDATE_METHOD
            and h2_summary.get("candidate_row_count") == 1
            and h2_summary.get("validation_error_count") == 0,
            "H2 pilot candidate row remains available",
            {
                "method": h2_candidate_gate.get("method"),
                "candidate_row_id": h2_summary.get("candidate_row_id"),
                "candidate_row_hash": h2_summary.get("candidate_row_hash"),
            },
        ),
        requirement(
            "P3",
            all(item["validation_error_count"] == 0 for item in batch_gates),
            "H2O/N2/LiH shard batch gates validate",
            batch_gates,
        ),
        requirement(
            "P4",
            source_shard_count == EXPECTED_TOTAL_SHARDS,
            "All 65 source shards are present in the assembled row bundle",
            {"source_shard_count": source_shard_count, "required_source_shard_count": EXPECTED_TOTAL_SHARDS},
        ),
        requirement(
            "P5",
            assembled_row_count == 3,
            "H2O/N2/LiH rows are assembled from all completed shard batches",
            {
                "assembled_row_count": assembled_row_count,
                "assembled_row_ids": row_bundle["assembled_row_ids"],
            },
        ),
        requirement(
            "P6",
            len([row_id for row_id in candidate_row_ids if row_id]) == EXPECTED_F1_ROW_COUNT,
            "Four F1 candidate rows are now present before acceptance",
            {
                "candidate_row_ids": candidate_row_ids,
                "candidate_row_hashes": candidate_row_hashes,
                "required_f1_row_count": EXPECTED_F1_ROW_COUNT,
            },
        ),
        requirement(
            "P7",
            all(row.get("row_hash") and row.get("row_replay_hash") for row in rows)
            and row_bundle.get("row_bundle_hash") is not None,
            "Row and bundle hashes are replay-bound",
            {
                "row_hashes": [row["row_hash"] for row in rows],
                "row_replay_hashes": [row["row_replay_hash"] for row in rows],
                "row_bundle_hash": row_bundle["row_bundle_hash"],
            },
        ),
        requirement(
            "P8",
            all(
                row["compiled_state_replay_hashes"]
                and row["qwc_group_manifest_hashes"]
                and row["measurement_basis_manifest_hashes"]
                and row["claim_boundary_hashes"]
                for row in rows
            ),
            "Assembled rows retain source replay and claim-boundary hashes",
            {"row_ids": [row["row_id"] for row in rows]},
        ),
        requirement(
            "P9",
            False,
            "Four-row F1 artifact has been submitted and accepted",
            {"accepted_f1_artifact": False, "accepted_full_covariance_row_count": 0},
        ),
        requirement(
            "P10",
            False,
            "Same-access denominator win or B3/B10 credit is allowed",
            {"denominator_win_count": 0, "b3_full_covariance_credit_allowed": False, "b10_t1_credit_allowed": False},
        ),
    ]
    failed = [item["id"] for item in requirements if not item["passed"]]
    validation_errors: list[str] = []
    if failed != ["P9", "P10"]:
        validation_errors.append(f"unexpected_failed_requirement_ids:{failed}")

    summary = {
        "source_shard_count": source_shard_count,
        "required_source_shard_count": EXPECTED_TOTAL_SHARDS,
        "assembled_row_count": assembled_row_count,
        "required_remaining_row_count": 3,
        "h2_candidate_row_count": 1,
        "f1_candidate_row_count": len([row_id for row_id in candidate_row_ids if row_id]),
        "required_f1_row_count": EXPECTED_F1_ROW_COUNT,
        "row_bundle_hash": row_bundle["row_bundle_hash"],
        "assembled_row_hashes": row_bundle["assembled_row_hashes"],
        "h2_candidate_row_hash": h2_summary.get("candidate_row_hash"),
        "total_assembled_group_count": sum(row["assembled_group_count"] for row in rows),
        "total_nonzero_covariance_pair_count": sum(row["nonzero_covariance_pair_count"] for row in rows),
        "total_variance_sum": sum(row["variance_sum"] for row in rows),
        "requirements_passed": len(requirements) - len(failed),
        "requirements_failed": len(failed),
        "failed_requirement_ids": failed,
        "accepted_f1_artifact": False,
        "accepted_full_covariance_row_count": 0,
        "denominator_win_count": 0,
        "b3_reopen_ready": False,
        "b3_full_covariance_credit_allowed": False,
        "b10_t1_credit_allowed": False,
        "quantum_advantage_claimed": False,
        "reaction_dynamics_solution_claimed": False,
        "bqp_separation_claimed": False,
        "validation_error_count": len(validation_errors),
    }

    return {
        "benchmark_id": "B3_B10",
        "problem_ids": ["B3", "B10"],
        "source_target_id": args.source_target_id,
        "title": "B3/B10 F1 Assembled Rows Gate",
        "version": "0.1",
        "last_updated": args.last_updated,
        "status": STATUS,
        "method": args.method,
        "model_status": args.model_status,
        "row_bundle": row_bundle,
        "h2_candidate_row": h2_candidate,
        "requirements": requirements,
        "summary": summary,
        "validation_errors": validation_errors,
        "claim_boundary": {
            "what_is_supported": "Three remaining F1 full-covariance rows were assembled from the completed H2O/N2/LiH shard batches and paired with the existing H2 pilot candidate as a four-row candidate bundle.",
            "what_is_not_supported": "This is not an accepted F1 artifact, not a same-access denominator win, not B3/B10 credit, and not quantum advantage.",
        },
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# B3/B10 F1 Assembled Rows Gate",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Row bundle hash: `{summary['row_bundle_hash']}`",
        f"- Source shards: {summary['source_shard_count']}/{summary['required_source_shard_count']}",
        f"- Assembled rows: {summary['assembled_row_count']}/{summary['required_remaining_row_count']}",
        f"- F1 candidate rows: {summary['f1_candidate_row_count']}/{summary['required_f1_row_count']}",
        "",
        "## Result",
        "",
        (
            "The gate assembles the H2O, N2, and LiH row-level covariance summaries from the "
            "completed shard batches and pairs them with the existing H2 pilot candidate. It "
            f"passes {summary['requirements_passed']}/10 requirements and intentionally fails "
            f"{summary['failed_requirement_ids']} because no four-row F1 artifact has been accepted "
            "and no same-access denominator win or B3/B10 credit is allowed."
        ),
        "",
        "## Row Metrics",
        "",
        f"- Total assembled groups: {summary['total_assembled_group_count']}",
        f"- Total nonzero covariance pairs: {summary['total_nonzero_covariance_pair_count']}",
        f"- Total variance sum: {summary['total_variance_sum']}",
        f"- Accepted full-covariance rows: {summary['accepted_full_covariance_row_count']}",
        f"- Denominator wins: {summary['denominator_win_count']}",
        "",
        "## Requirements",
        "",
    ]
    for item in payload["requirements"]:
        marker = "PASS" if item["passed"] else "FAIL"
        lines.append(f"- `{item['id']}` {marker}: {item['description']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shard-root", type=Path, default=Path("results/B3_B10_F1_full_covariance_shards"))
    parser.add_argument(
        "--row-packet-gate",
        type=Path,
        default=Path("results/B3_B10_F1_full_covariance_row_packet_gate_v0.json"),
    )
    parser.add_argument(
        "--h2-candidate-gate",
        type=Path,
        default=Path("results/B3_B10_F1_pilot_row_candidate_gate_v0.json"),
    )
    parser.add_argument("--json-output", type=Path, default=Path("results/B3_B10_F1_assembled_rows_gate_v0.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("research/B3_B10_F1_assembled_rows_gate.md"))
    parser.add_argument("--method", default=METHOD)
    parser.add_argument("--model-status", default=MODEL_STATUS)
    parser.add_argument("--source-target-id", default=SOURCE_TARGET_ID)
    parser.add_argument("--last-updated", default="2026-07-03")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    write_markdown(args.markdown_output, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "summary": payload["summary"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
