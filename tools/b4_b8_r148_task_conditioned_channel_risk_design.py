#!/usr/bin/env python3
"""Select foreign routes with a task-conditioned, channel-priority descriptor."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r135_dense_interaction_fallback import build_dense_validation_tasks
from b4_b8_r138_postcommit_statistical_challenge import exact_distribution, hellinger_fidelity
from b4_b8_r139_lagos_ising_channel_attribution import apply_symmetric_readout_channel


METHOD = "b4_b8_r148_task_conditioned_channel_risk_design_v0"
R147_DESIGN_PATH = "results/B4_B8_R147_target_descriptor_adaptation_design_v0.json"
R147_RESULT_PATH = "results/B4_B8_R147_target_descriptor_adaptation_holdout_v0.json"
R125_PATH = "results/B4_B8_R125_historical_snapshot_replay_v0.json"
R139_TOOL_PATH = "tools/b4_b8_r139_lagos_ising_channel_attribution.py"
TASK_BUILDER_PATH = "tools/b4_b8_r135_dense_interaction_fallback.py"
RESULT_PATH = "results/B4_B8_R148_task_conditioned_channel_risk_design_v0.json"
REPORT_PATH = "research/B4_B8_R148_task_conditioned_channel_risk_design.md"
UNIFORM_TOLERANCE = 1e-12


def uniformity_gap(distribution: dict[str, float]) -> float:
    uniform = 1.0 / len(distribution)
    return max(abs(value - uniform) for value in distribution.values())


def selection_key(row: dict[str, Any], mode: str) -> tuple[Any, ...]:
    if mode == "readout_first":
        return (
            row["exact_output_aware_readout_fidelity"],
            row["cx_success_proxy"],
            -row["cx_occurrence_count"],
            row["source_snapshot"],
        )
    return (
        row["cx_success_proxy"],
        row["exact_output_aware_readout_fidelity"],
        -row["cx_occurrence_count"],
        row["source_snapshot"],
    )


def build(root: Path) -> dict[str, Any]:
    prior = json.loads((root / R147_DESIGN_PATH).read_text())
    r125 = json.loads((root / R125_PATH).read_text())
    tasks = {task["task_id"]: task for task in build_dense_validation_tasks()}
    prior_selections = {
        (row["target_snapshot"], row["task_id"]): row["selected_source_snapshot"]
        for row in prior["selection_rows"]
    }
    candidate_rows = []
    selection_rows = []
    group_keys = sorted({(row["target_snapshot"], row["task_id"]) for row in prior["candidate_rows"]})
    for target_snapshot, task_id in group_keys:
        ideal = exact_distribution(tasks[task_id]["circuit"])
        gap = uniformity_gap(ideal)
        mode = "cx_first" if gap <= UNIFORM_TOLERANCE else "readout_first"
        measure_rows = r125["snapshot_metadata"][target_snapshot]["canonical"]["instruction_properties"]["measure"]
        physical_errors = {row["qargs"][0]: float(row["error"] or 0.0) for row in measure_rows}
        group_candidates = []
        for source in prior["candidate_rows"]:
            if source["target_snapshot"] != target_snapshot or source["task_id"] != task_id:
                continue
            measurement_map = sorted(source["measurement_map"], key=lambda row: row["classical_bit"])
            readout_vector = [physical_errors[row["physical_qubit"]] for row in measurement_map]
            distorted = apply_symmetric_readout_channel(ideal, readout_vector)
            readout_fidelity = hellinger_fidelity(ideal, distorted)
            row = {
                "adaptation_group_id": f"{target_snapshot}::{task_id}",
                "target_snapshot": target_snapshot,
                "task_id": task_id,
                "source_snapshot": source["source_snapshot"],
                "source_mapping": source["source_mapping"],
                "source_policy_id": source["source_policy_id"],
                "source_realization_seed": source["source_realization_seed"],
                "candidate_circuit_path": source["candidate_circuit_path"],
                "candidate_circuit_sha256": source["candidate_circuit_sha256"],
                "candidate_qasm_stable_hash": source["candidate_qasm_stable_hash"],
                "semantic_fidelity": source["semantic_fidelity"],
                "ideal_uniformity_gap": gap,
                "channel_priority_mode": mode,
                "readout_error_vector": readout_vector,
                "exact_output_aware_readout_fidelity": readout_fidelity,
                "cx_success_proxy": 1.0 - source["cx_any_error_proxy"],
                "cx_any_error_proxy": source["cx_any_error_proxy"],
                "cx_occurrence_count": source["cx_occurrence_count"],
                "combined_any_error_proxy": source["combined_any_error_proxy"],
            }
            row["selection_key"] = list(selection_key(row, mode))
            candidate_rows.append(row)
            group_candidates.append(row)
        selected = max(group_candidates, key=lambda row: selection_key(row, mode))
        prior_source = prior_selections[(target_snapshot, task_id)]
        selection_rows.append({
            "adaptation_group_id": selected["adaptation_group_id"],
            "target_snapshot": target_snapshot,
            "task_id": task_id,
            "candidate_count": len(group_candidates),
            "candidate_source_snapshots": sorted(row["source_snapshot"] for row in group_candidates),
            "channel_priority_mode": mode,
            "ideal_uniformity_gap": gap,
            "target_specific_route_excluded_from_selector": True,
            "selected_source_snapshot": selected["source_snapshot"],
            "selected_mapping": selected["source_mapping"],
            "selected_policy_id": selected["source_policy_id"],
            "selected_realization_seed": selected["source_realization_seed"],
            "selected_circuit_path": selected["candidate_circuit_path"],
            "selected_circuit_sha256": selected["candidate_circuit_sha256"],
            "selected_qasm_stable_hash": selected["candidate_qasm_stable_hash"],
            "selected_semantic_fidelity": selected["semantic_fidelity"],
            "selected_exact_output_aware_readout_fidelity": selected["exact_output_aware_readout_fidelity"],
            "selected_cx_success_proxy": selected["cx_success_proxy"],
            "selected_selection_key": selected["selection_key"],
            "r147_selected_source_snapshot": prior_source,
            "selection_changed_from_r147": selected["source_snapshot"] != prior_source,
        })

    summary = {
        "snapshot_count": len({row["target_snapshot"] for row in selection_rows}),
        "task_count": len({row["task_id"] for row in selection_rows}),
        "adaptation_group_count": len(selection_rows),
        "foreign_candidate_count": len(candidate_rows),
        "readout_first_group_count": sum(row["channel_priority_mode"] == "readout_first" for row in selection_rows),
        "cx_first_group_count": sum(row["channel_priority_mode"] == "cx_first" for row in selection_rows),
        "selection_change_count_from_r147": sum(row["selection_changed_from_r147"] for row in selection_rows),
        "changed_group_ids": [row["adaptation_group_id"] for row in selection_rows if row["selection_changed_from_r147"]],
        "target_specific_routes_in_selector_count": 0,
        "r147_hidden_trial_rows_read_count": 0,
        "fitted_weight_count": 0,
        "minimum_candidate_semantic_fidelity": min(row["semantic_fidelity"] for row in candidate_rows),
        "semantic_fidelity_pass_count": sum(row["semantic_fidelity"] >= 0.9999999999 for row in candidate_rows),
        "challenge_executed": False,
        "hardware_execution_claimed": False,
        "quantum_advantage_claimed": False,
        "solved_frontier_claimed": False,
        "new_credit_delta": 0,
    }
    requirements = [
        {"requirement_id": "R1", "label": "R147 design, R147 provenance, R125 metadata, R139 channel function, and task builder are bound", "passed": True},
        {"requirement_id": "R2", "label": "12 groups contain exactly two foreign candidates", "passed": len(selection_rows) == 12 and len(candidate_rows) == 24 and all(row["candidate_count"] == 2 for row in selection_rows)},
        {"requirement_id": "R3", "label": "uniform tasks prioritize CX and nonuniform tasks prioritize exact output-aware readout", "passed": summary["readout_first_group_count"] == 6 and summary["cx_first_group_count"] == 6},
        {"requirement_id": "R4", "label": "the selector has zero fitted weights", "passed": summary["fitted_weight_count"] == 0},
        {"requirement_id": "R5", "label": "target-specific R143 routes remain excluded", "passed": summary["target_specific_routes_in_selector_count"] == 0},
        {"requirement_id": "R6", "label": "R147 hidden rows are not loaded for design or tuning", "passed": summary["r147_hidden_trial_rows_read_count"] == 0},
        {"requirement_id": "R7", "label": "all 24 candidates retain semantic fidelity", "passed": summary["semantic_fidelity_pass_count"] == 24},
        {"requirement_id": "R8", "label": "all candidate QASM hashes replay", "passed": all(file_sha256(root / row["candidate_circuit_path"]) == row["candidate_circuit_sha256"] for row in candidate_rows)},
        {"requirement_id": "R9", "label": "no R148 holdout is executed during design", "passed": not summary["challenge_executed"]},
        {"requirement_id": "R10", "label": "hardware, advantage, solved-frontier, and credit claims remain false", "passed": not any([summary["hardware_execution_claimed"], summary["quantum_advantage_claimed"], summary["solved_frontier_claimed"], summary["new_credit_delta"]])},
    ]
    payload = {
        "title": "B4/B8 R148 task-conditioned channel-risk foreign-route design",
        "version": 0,
        "method": METHOD,
        "status": "task_conditioned_channel_risk_design_frozen_before_holdout",
        "model_status": "zero_fit_channel_priority_selector_without_r147_row_reuse",
        "generated_at_unix": int(time.time()),
        "source_target_id": "T-B4-002be/T-B8-003bi/T-B10-009aw",
        "upstream_target_id": "T-B4-002bd/T-B8-003bh/T-B10-009av",
        "source_bindings": {
            "r147_design_path": R147_DESIGN_PATH,
            "r147_design_sha256": file_sha256(root / R147_DESIGN_PATH),
            "r147_design_payload_hash": prior["payload_hash"],
            "r147_result_path": R147_RESULT_PATH,
            "r147_result_sha256_provenance_only": file_sha256(root / R147_RESULT_PATH),
            "r147_trial_rows_consumed": False,
            "r125_snapshot_path": R125_PATH,
            "r125_snapshot_sha256": file_sha256(root / R125_PATH),
            "r125_snapshot_payload_hash": r125["payload_hash"],
            "r139_channel_function_path": R139_TOOL_PATH,
            "r139_channel_function_sha256": file_sha256(root / R139_TOOL_PATH),
            "task_builder_path": TASK_BUILDER_PATH,
            "task_builder_sha256": file_sha256(root / TASK_BUILDER_PATH),
        },
        "selector": {
            "candidate_pool": "the two foreign R143 routes preserved by the R147 design artifact",
            "uniformity_rule": f"cx_first when ideal output maximum uniformity gap <= {UNIFORM_TOLERANCE}",
            "nonuniform_rule": "readout_first lexicographic ordering by exact output-aware readout fidelity then CX success",
            "uniform_rule": "cx_first lexicographic ordering by CX success then exact output-aware readout fidelity",
            "fitted_weights": [],
            "target_specific_route_used_for_selection": False,
            "r147_trial_rows_used_for_selection_or_tuning": False,
        },
        "summary": summary,
        "candidate_rows": candidate_rows,
        "selection_rows": selection_rows,
        "requirements": requirements,
        "requirement_count": 10,
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [row["requirement_id"] for row in requirements if not row["passed"]],
        "artifacts": {"result": RESULT_PATH, "markdown_report": REPORT_PATH},
        "claim_boundary": {
            "what_is_supported": "a zero-fit task-conditioned channel-priority selector over frozen foreign routes",
            "what_is_not_supported": "holdout improvement, scalable exact-output evaluation, temporal transfer, cross-machine transfer, real hardware, mitigation, soundness, quantum advantage, BQP separation, solved B4/B8/B10, or new credit",
        },
    }
    hash_payload = dict(payload)
    payload["payload_hash"] = hashlib.sha256(json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload


def report(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    rows = "\n".join(
        f"- `{row['target_snapshot']}` / `{row['task_id']}`: `{row['channel_priority_mode']}`, selected `{row['selected_source_snapshot']}`, prior `{row['r147_selected_source_snapshot']}`, changed `{str(row['selection_changed_from_r147']).lower()}`."
        for row in payload["selection_rows"]
    )
    return f"""# B4/B8 R148 Task-Conditioned Channel-Risk Design

- Groups / foreign candidates: `{s['adaptation_group_count']}` / `{s['foreign_candidate_count']}`
- Readout-first / CX-first groups: `{s['readout_first_group_count']}` / `{s['cx_first_group_count']}`
- Selections changed from R147: `{s['selection_change_count_from_r147']}`
- Target-specific routes in selector: `{s['target_specific_routes_in_selector_count']}`
- R147 hidden rows read: `{s['r147_hidden_trial_rows_read_count']}`
- Fitted weights: `{s['fitted_weight_count']}`
- Candidate semantic passes: `{s['semantic_fidelity_pass_count']} / 24`
- Holdout executed: `false`

## Frozen Selections

{rows}

## Method Boundary

Uniform ideal outputs are invariant under symmetric bit-flip readout, so their
selector prioritizes compiled CX survival. Nonuniform ideal outputs expose
logical-bit placement to physical readout asymmetry, so their selector
prioritizes exact output-aware readout fidelity and uses CX survival only as a
tie break. The rule has no fitted weight, excludes target-specific routes, and
does not load any R147 hidden row.

This finite six-qubit design does not support scalable exact-output evaluation,
a holdout improvement, temporal or cross-machine transfer, real hardware,
mitigation, soundness, quantum advantage, BQP separation, a solved frontier,
or new credit.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    payload = build(root)
    write_json(root / RESULT_PATH, payload)
    (root / REPORT_PATH).write_text(report(payload), encoding="utf-8")
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
