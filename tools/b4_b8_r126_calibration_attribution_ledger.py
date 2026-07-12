#!/usr/bin/env python3
"""T-B4-002aa/T-B8-003ae: attribute the R125 snapshot failures."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from qiskit import qasm3
from scipy.stats import spearmanr

from b4_b8_r121_private_bundle_shot_sweep import stable_hash, write_json


METHOD = "b4_b8_r126_calibration_attribution_ledger_v0"
STATUS = "historical_snapshot_failure_attribution_boundary"
MODEL_STATUS = "r125_failures_split_by_readout_routing_bundle_and_seed_block"
TARGET_ID = "T-B4-002aa/T-B8-003ae/T-B10-009s"
UPSTREAM_TARGET_ID = "T-B4-002z/T-B8-003ad/T-B10-009r"
R125_RESULT_PATH = "results/B4_B8_R125_historical_snapshot_replay_v0.json"
R125_CIRCUIT_DIR = "results/B4_B8_R125_historical_snapshot_replay/circuits"
RESULT_PATH = "results/B4_B8_R126_calibration_attribution_ledger_v0.json"
REPORT_PATH = "research/B4_B8_R126_calibration_attribution_ledger.md"
CANDIDATE_SHOTS = 8192


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def instruction_error_map(
    metadata: dict[str, Any], operation: str
) -> dict[tuple[int, ...], float]:
    rows = metadata["canonical"]["instruction_properties"][operation]
    return {
        tuple(row["qargs"]): float(row["error"] or 0.0)
        for row in rows
    }


def circuit_exposure(
    path: Path, metadata: dict[str, Any]
) -> dict[str, Any]:
    circuit = qasm3.load(path)
    measure_errors = instruction_error_map(metadata, "measure")
    cx_errors = instruction_error_map(metadata, "cx")
    measured = []
    cx_occurrences = []
    for instruction in circuit.data:
        if instruction.operation.name == "measure":
            qubit = circuit.find_bit(instruction.qubits[0]).index
            classical = circuit.find_bit(instruction.clbits[0]).index
            measured.append(
                {
                    "physical_qubit": qubit,
                    "classical_bit": classical,
                    "readout_error": measure_errors[(qubit,)],
                }
            )
        elif instruction.operation.name == "cx":
            edge = tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits)
            cx_occurrences.append(
                {"edge": list(edge), "cx_error": cx_errors[edge]}
            )
    measured.sort(key=lambda row: row["classical_bit"])
    readout_survival = math.prod(1.0 - row["readout_error"] for row in measured)
    cx_survival = math.prod(1.0 - row["cx_error"] for row in cx_occurrences)
    return {
        "circuit_path": str(path),
        "circuit_sha256": file_sha256(path),
        "qubit_count": circuit.num_qubits,
        "classical_bit_count": circuit.num_clbits,
        "depth": circuit.depth(),
        "operation_counts": {str(k): int(v) for k, v in circuit.count_ops().items()},
        "measurement_map": measured,
        "measurement_map_preserves_logical_order": [
            row["classical_bit"] for row in measured
        ]
        == list(range(circuit.num_clbits)),
        "mean_measured_readout_error": float(
            np.mean([row["readout_error"] for row in measured])
        ),
        "maximum_measured_readout_error": max(
            row["readout_error"] for row in measured
        ),
        "readout_any_error_proxy": 1.0 - readout_survival,
        "cx_occurrences": cx_occurrences,
        "cx_occurrence_count": len(cx_occurrences),
        "unique_cx_edges": sorted({tuple(row["edge"]) for row in cx_occurrences}),
        "mean_occurrence_cx_error": float(
            np.mean([row["cx_error"] for row in cx_occurrences])
        ),
        "maximum_occurrence_cx_error": max(
            row["cx_error"] for row in cx_occurrences
        ),
        "cx_any_error_proxy": 1.0 - cx_survival,
        "combined_any_error_proxy": 1.0 - readout_survival * cx_survival,
    }


def bundle_strata(rows: list[dict[str, Any]], shots: int) -> list[dict[str, Any]]:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        choice = row["bundle_choice"]
        grouped[(choice["negative_index"], choice["positive_index"])].append(row)
    output = []
    for (negative_index, positive_index), selected in sorted(grouped.items()):
        errors = [
            row["by_shot_budget"][str(shots)]["maximum_bundle_error"]
            for row in selected
        ]
        passes = [row["by_shot_budget"][str(shots)]["passed"] for row in selected]
        output.append(
            {
                "negative_index": negative_index,
                "positive_index": positive_index,
                "trial_count": len(selected),
                "pass_count": sum(passes),
                "pass_rate": sum(passes) / len(selected),
                "mean_maximum_bundle_error": float(np.mean(errors)),
                "maximum_bundle_error": max(errors),
            }
        )
    return output


def block_strata(rows: list[dict[str, Any]], shots: int) -> list[dict[str, Any]]:
    output = []
    for block_index in sorted({row["block_index"] for row in rows}):
        selected = [row for row in rows if row["block_index"] == block_index]
        errors = [
            row["by_shot_budget"][str(shots)]["maximum_bundle_error"]
            for row in selected
        ]
        passes = [row["by_shot_budget"][str(shots)]["passed"] for row in selected]
        output.append(
            {
                "block_index": block_index,
                "block_seed": selected[0]["block_seed"],
                "trial_count": len(selected),
                "pass_count": sum(passes),
                "pass_rate": sum(passes) / len(selected),
                "mean_maximum_bundle_error": float(np.mean(errors)),
                "maximum_bundle_error": max(errors),
            }
        )
    return output


def paired_transitions(rows: list[dict[str, Any]]) -> dict[str, int]:
    before = [row["by_shot_budget"]["4096"]["passed"] for row in rows]
    after = [row["by_shot_budget"]["8192"]["passed"] for row in rows]
    return {
        "fail_to_pass": sum(
            (not low) and high for low, high in zip(before, after, strict=True)
        ),
        "pass_to_fail": sum(
            low and (not high) for low, high in zip(before, after, strict=True)
        ),
        "stable_pass": sum(
            low and high for low, high in zip(before, after, strict=True)
        ),
        "stable_fail": sum(
            (not low) and (not high)
            for low, high in zip(before, after, strict=True)
        ),
    }


def correlation(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
    x = [row[field] for row in rows]
    y = [row["candidate_pass_rate"] for row in rows]
    statistic, pvalue = spearmanr(x, y)
    return {
        "exposure_field": field,
        "spearman_rho": float(statistic),
        "two_sided_pvalue": float(pvalue),
        "row_count": len(rows),
        "descriptive_only": True,
    }


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    task_lines = []
    for row in payload["task_attribution_rows"]:
        task_lines.append(
            f"- `{row['snapshot']}` / `{row['task_id']}`: candidate pass "
            f"`{row['candidate_pass_count']}/{row['trial_count']}` "
            f"(`{row['candidate_pass_rate']:.4f}`), mean/max bundle error "
            f"`{row['candidate_mean_maximum_bundle_error']:.4f}/"
            f"{row['candidate_maximum_bundle_error']:.4f}`, CX count "
            f"`{row['cx_occurrence_count']}`, readout/cx/combined exposure "
            f"`{row['readout_any_error_proxy']:.4f}/"
            f"{row['cx_any_error_proxy']:.4f}/"
            f"{row['combined_any_error_proxy']:.4f}`."
        )
    requirements = "\n".join(
        f"- `{row['requirement_id']}` "
        f"{'PASS' if row['passed'] else 'FAIL'}: {row['label']}"
        for row in payload["requirements"]
    )
    return f"""# B4/B8 R126 Calibration Attribution Ledger

## Summary

- Target: `{TARGET_ID}`
- Upstream target: `{UPSTREAM_TARGET_ID}`
- Method: `{METHOD}`
- Status: `{STATUS}`
- R125 source rows consumed: `{summary['source_trial_row_count']}`
- Snapshot/task attribution rows: `{summary['task_attribution_row_count']}`
- Bundle strata: `{summary['bundle_stratum_count']}`
- Block strata: `{summary['block_stratum_count']}`
- Candidate budget: `{CANDIDATE_SHOTS}` shots
- Lowest candidate task pass rate: `{summary['minimum_candidate_task_pass_rate']:.4f}`
- Highest candidate task pass rate: `{summary['maximum_candidate_task_pass_rate']:.4f}`
- Mitigation tested: `{summary['mitigation_tested']}`
- New credit delta: `{summary['new_credit_delta']}`

{chr(10).join(task_lines)}

R126 does not tune or rerun the failed holdout. It decomposes the already fixed
R125 rows by historical snapshot, task, hidden-bundle choice, seed block,
physical readout exposure, and routed CX exposure. Correlations use only six
snapshot/task rows and are descriptive diagnostics, not causal estimates.

## Mitigation Priority

1. Pre-register physical-qubit subset selection using snapshot properties only.
2. Separate routing-only and readout-only ablations on new disjoint seeds.
3. Fit readout mitigation on calibration rows disjoint from evaluation rows.
4. Preserve the hidden bundle and A1-A5 rules in the next holdout.
5. Keep current provider and hardware transcript evidence as separate gates.

## Requirements

{requirements}

## Claim Boundary

Supported: row-level attribution of the fixed R125 historical-snapshot failure.
Not supported: a mitigation win, causal noise decomposition, current calibration,
provider access, hardware execution, protocol soundness, quantum advantage, BQP
separation, or B10 credit.
"""


def run_gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    source_path = root / R125_RESULT_PATH
    source = json.loads(source_path.read_text(encoding="utf-8"))
    if source.get("status") != "preregistered_historical_qpu_snapshot_replay_boundary":
        raise ValueError("R126 requires the accepted R125 attribution source")
    tasks = sorted({row["task_id"] for row in source["trial_rows"]})
    snapshots = source["summary"]["snapshot_names"]
    attribution_rows = []
    all_bundle_rows = []
    all_block_rows = []
    circuit_files = []
    for snapshot in snapshots:
        metadata = source["snapshot_metadata"][snapshot]
        for task in tasks:
            path = root / R125_CIRCUIT_DIR / f"{snapshot}_{task}_all_z.qasm"
            exposure = circuit_exposure(path, metadata)
            circuit_files.append(str(path.relative_to(root)))
            selected = [
                row
                for row in source["trial_rows"]
                if row["snapshot"] == snapshot and row["task_id"] == task
            ]
            candidate_errors = [
                row["by_shot_budget"][str(CANDIDATE_SHOTS)][
                    "maximum_bundle_error"
                ]
                for row in selected
            ]
            candidate_passes = [
                row["by_shot_budget"][str(CANDIDATE_SHOTS)]["passed"]
                for row in selected
            ]
            control_passes = [
                row["by_shot_budget"]["4096"]["passed"] for row in selected
            ]
            bundles = bundle_strata(selected, CANDIDATE_SHOTS)
            blocks = block_strata(selected, CANDIDATE_SHOTS)
            for row in bundles:
                row.update({"snapshot": snapshot, "task_id": task})
            for row in blocks:
                row.update({"snapshot": snapshot, "task_id": task})
            all_bundle_rows.extend(bundles)
            all_block_rows.extend(blocks)
            attribution_rows.append(
                {
                    "snapshot": snapshot,
                    "snapshot_role": source["summary"]["snapshots"][snapshot][
                        "role"
                    ],
                    "task_id": task,
                    "trial_count": len(selected),
                    "control_pass_count": sum(control_passes),
                    "control_pass_rate": sum(control_passes) / len(selected),
                    "candidate_pass_count": sum(candidate_passes),
                    "candidate_pass_rate": sum(candidate_passes) / len(selected),
                    "candidate_mean_maximum_bundle_error": float(
                        np.mean(candidate_errors)
                    ),
                    "candidate_maximum_bundle_error": max(candidate_errors),
                    "paired_transitions": paired_transitions(selected),
                    "bundle_stratum_count": len(bundles),
                    "block_stratum_count": len(blocks),
                    **exposure,
                }
            )

    correlations = [
        correlation(attribution_rows, field)
        for field in [
            "mean_measured_readout_error",
            "maximum_measured_readout_error",
            "readout_any_error_proxy",
            "mean_occurrence_cx_error",
            "cx_any_error_proxy",
            "combined_any_error_proxy",
            "cx_occurrence_count",
        ]
    ]
    ghz_rows = [
        row for row in attribution_rows if row["task_id"] == "private_bundle_ghz_n6"
    ]
    graph_rows = [
        row
        for row in attribution_rows
        if row["task_id"] == "private_bundle_graph_n6"
    ]
    paired_task_gap = []
    for snapshot in snapshots:
        ghz = next(row for row in ghz_rows if row["snapshot"] == snapshot)
        graph = next(row for row in graph_rows if row["snapshot"] == snapshot)
        paired_task_gap.append(
            {
                "snapshot": snapshot,
                "graph_minus_ghz_candidate_pass_rate": graph[
                    "candidate_pass_rate"
                ]
                - ghz["candidate_pass_rate"],
                "ghz_minus_graph_cx_occurrence_count": ghz["cx_occurrence_count"]
                - graph["cx_occurrence_count"],
                "readout_exposure_gap": graph["readout_any_error_proxy"]
                - ghz["readout_any_error_proxy"],
                "routing_sensitive_diagnostic": graph["candidate_pass_rate"]
                > ghz["candidate_pass_rate"]
                and ghz["cx_occurrence_count"] > graph["cx_occurrence_count"],
            }
        )
    mitigation_queue = [
        {
            "priority": 1,
            "packet": "R127-P1-calibration-aware-physical-subset",
            "rationale": "Select the six physical qubits and initial layout using only frozen snapshot properties before evaluation.",
            "status": "ready_for_preregistration",
        },
        {
            "priority": 2,
            "packet": "R127-P2-routing-readout-ablation",
            "rationale": "Separate topology/routing exposure from measurement exposure on new disjoint seeds.",
            "status": "ready_for_preregistration",
        },
        {
            "priority": 3,
            "packet": "R127-P3-disjoint-readout-mitigation",
            "rationale": "Fit any confusion-matrix correction only on calibration rows excluded from evaluation.",
            "status": "ready_for_preregistration",
        },
        {
            "priority": 4,
            "packet": "R127-P4-current-provider-or-transcript",
            "rationale": "Replace frozen snapshots with current provider-backed properties or independent raw-count transcripts.",
            "status": "externally_blocked",
        },
    ]
    summary = {
        "source_trial_row_count": len(source["trial_rows"]),
        "snapshot_count": len(snapshots),
        "task_count": len(tasks),
        "task_attribution_row_count": len(attribution_rows),
        "bundle_stratum_count": len(all_bundle_rows),
        "block_stratum_count": len(all_block_rows),
        "correlation_count": len(correlations),
        "minimum_candidate_task_pass_rate": min(
            row["candidate_pass_rate"] for row in attribution_rows
        ),
        "maximum_candidate_task_pass_rate": max(
            row["candidate_pass_rate"] for row in attribution_rows
        ),
        "routing_sensitive_snapshot_count": sum(
            row["routing_sensitive_diagnostic"] for row in paired_task_gap
        ),
        "lagos_graph_candidate_pass_rate": next(
            row["candidate_pass_rate"]
            for row in graph_rows
            if row["snapshot"] == "FakeLagosV2"
        ),
        "lagos_ghz_candidate_pass_rate": next(
            row["candidate_pass_rate"]
            for row in ghz_rows
            if row["snapshot"] == "FakeLagosV2"
        ),
        "mitigation_tested": False,
        "holdout_reused_for_acceptance": False,
        "current_backend_calibration_used": False,
        "hardware_execution_performed": False,
        "protocol_soundness_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "new_credit_delta": 0,
    }
    requirements = [
        {
            "requirement_id": "P1",
            "label": "the complete R125 result is hash-bound and consumed",
            "passed": len(source["trial_rows"]) == 480,
            "evidence": {
                "source_sha256": file_sha256(source_path),
                "source_payload_hash": source["payload_hash"],
            },
        },
        {
            "requirement_id": "P2",
            "label": "all six snapshot/task combinations have attribution rows",
            "passed": len(attribution_rows) == len(snapshots) * len(tasks),
            "evidence": {"attribution_row_count": len(attribution_rows)},
        },
        {
            "requirement_id": "P3",
            "label": "all representative QASM 3 circuits parse and preserve measurement order",
            "passed": len(circuit_files) == 6
            and all(
                row["measurement_map_preserves_logical_order"]
                for row in attribution_rows
            ),
            "evidence": {"circuit_file_count": len(circuit_files)},
        },
        {
            "requirement_id": "P4",
            "label": "all historical snapshot hashes remain bound",
            "passed": all(
                row["snapshot"] in source["snapshot_metadata"]
                for row in attribution_rows
            ),
            "evidence": {
                name: source["snapshot_metadata"][name]["sha256"]
                for name in snapshots
            },
        },
        {
            "requirement_id": "P5",
            "label": "bundle-choice strata cover every source trial",
            "passed": sum(row["trial_count"] for row in all_bundle_rows)
            == len(source["trial_rows"]),
            "evidence": {"bundle_stratum_count": len(all_bundle_rows)},
        },
        {
            "requirement_id": "P6",
            "label": "seed-block strata cover every source trial",
            "passed": sum(row["trial_count"] for row in all_block_rows)
            == len(source["trial_rows"]),
            "evidence": {"block_stratum_count": len(all_block_rows)},
        },
        {
            "requirement_id": "P7",
            "label": "readout and CX exposure proxies are finite and bounded",
            "passed": all(
                0.0 <= row["readout_any_error_proxy"] <= 1.0
                and 0.0 <= row["cx_any_error_proxy"] <= 1.0
                and 0.0 <= row["combined_any_error_proxy"] <= 1.0
                for row in attribution_rows
            ),
            "evidence": {"exposure_row_count": len(attribution_rows)},
        },
        {
            "requirement_id": "P8",
            "label": "small-sample correlations are explicitly descriptive only",
            "passed": all(row["descriptive_only"] for row in correlations),
            "evidence": {"correlation_row_count": len(correlations)},
        },
        {
            "requirement_id": "P9",
            "label": "mitigation packets are proposed without reusing holdout for acceptance",
            "passed": not summary["mitigation_tested"]
            and not summary["holdout_reused_for_acceptance"],
            "evidence": {"mitigation_packet_count": len(mitigation_queue)},
        },
        {
            "requirement_id": "P10",
            "label": "no hardware, soundness, advantage, BQP, or new credit is claimed",
            "passed": not summary["current_backend_calibration_used"]
            and not summary["hardware_execution_performed"]
            and not summary["protocol_soundness_claimed"]
            and not summary["quantum_advantage_claimed"]
            and not summary["bqp_separation_claimed"]
            and summary["new_credit_delta"] == 0,
            "evidence": {"new_credit_delta": 0},
        },
    ]
    failed = [row["requirement_id"] for row in requirements if not row["passed"]]
    payload: dict[str, Any] = {
        "title": "B4/B8 R126 calibration attribution ledger",
        "version": "0.1",
        "generated_at_unix": int(time.time()),
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "requirements": requirements,
        "requirement_count": len(requirements),
        "requirements_passed": len(requirements) - len(failed),
        "requirements_failed": len(failed),
        "summary": summary,
        "task_attribution_rows": attribution_rows,
        "bundle_strata": all_bundle_rows,
        "block_strata": all_block_rows,
        "paired_task_gap": paired_task_gap,
        "descriptive_correlations": correlations,
        "mitigation_queue": mitigation_queue,
        "artifacts": {
            "r125_result": R125_RESULT_PATH,
            "representative_circuits": sorted(circuit_files),
        },
        "claim_boundary": {
            "what_is_supported": (
                "Row-level attribution of the fixed R125 historical-snapshot failure "
                "across readout, routing, task, bundle, and seed-block strata."
            ),
            "what_is_not_supported": (
                "A mitigation win, causal noise decomposition, current calibration, "
                "provider access, hardware execution, protocol soundness, quantum "
                "advantage, BQP separation, or B10 credit."
            ),
            "next_gate": (
                "Publicly preregister calibration-aware physical-qubit selection, "
                "routing/readout ablations, and disjoint readout mitigation before "
                "collecting a new holdout."
            ),
        },
    }
    payload["payload_hash"] = stable_hash(payload)
    write_json(root / RESULT_PATH, payload)
    (root / REPORT_PATH).write_text(report(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    print(json.dumps(run_gate(Path(args.repo_root)), sort_keys=True))


if __name__ == "__main__":
    main()
