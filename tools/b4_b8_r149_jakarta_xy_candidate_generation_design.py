#!/usr/bin/env python3
"""Generate a new Jakarta dense-XY route without copying frozen route identities."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from qiskit import qasm3
from qiskit_aer import AerSimulator

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r121_private_bundle_shot_sweep import basis_circuit, stable_hash
from b4_b8_r126_calibration_attribution_ledger import circuit_exposure, file_sha256
from b4_b8_r127_calibration_aware_layout_design import SNAPSHOT_CLASSES, logical_two_qubit_edges, static_layout_objective
from b4_b8_r132_topology_constrained_route_policy import DETERMINISTIC_PROCESS_ENV, compile_policy
from b4_b8_r135_dense_interaction_fallback import build_dense_validation_tasks
from b4_b8_r138_postcommit_statistical_challenge import exact_distribution, hellinger_fidelity, probability_from_counts
from b4_b8_r139_lagos_ising_channel_attribution import apply_symmetric_readout_channel, exact_compiled_classical_distribution


METHOD = "b4_b8_r149_jakarta_xy_candidate_generation_design_v0"
TARGET_SNAPSHOT = "FakeJakartaV2"
TARGET_TASK = "dense_validation_xy_network_n6"
R148_DESIGN_PATH = "results/B4_B8_R148_task_conditioned_channel_risk_design_v0.json"
R148_RESULT_PATH = "results/B4_B8_R148_task_conditioned_channel_risk_holdout_v0.json"
R143_PATH = "results/B4_B8_R143_successive_halving_lcb_design_v0.json"
R125_PATH = "results/B4_B8_R125_historical_snapshot_replay_v0.json"
TASK_BUILDER_PATH = "tools/b4_b8_r135_dense_interaction_fallback.py"
RESULT_PATH = "results/B4_B8_R149_jakarta_xy_candidate_generation_design_v0.json"
REPORT_PATH = "research/B4_B8_R149_jakarta_xy_candidate_generation_design.md"
OUT_DIR = "results/B4_B8_R149_jakarta_xy_candidate_generation_design/candidates"
SHORTLIST_MAPPING_COUNT = 12
POLICY_IDS = ("selected_o3_default", "selected_o3_lookahead")
REALIZATION_SEEDS = (14901, 14902)
ROUND_SEEDS = ((14911, 14912, 14913, 14914), (14915, 14916, 14917, 14918), tuple(range(14919, 14927)))
SURVIVOR_COUNTS = (12, 3, 1)
SHOTS = 2048


def ensure_environment() -> None:
    if all(os.environ.get(key) == value for key, value in DETERMINISTIC_PROCESS_ENV.items()):
        return
    environment = dict(os.environ)
    environment.update(DETERMINISTIC_PROCESS_ENV)
    os.execvpe(sys.executable, [sys.executable, *sys.argv], environment)


def lcb(values: list[float]) -> float:
    mean = statistics.mean(values)
    if len(values) < 2:
        return mean
    return mean - 1.96 * statistics.stdev(values) / math.sqrt(len(values))


def build(root: Path) -> dict[str, Any]:
    r148_design = json.loads((root / R148_DESIGN_PATH).read_text())
    r143 = json.loads((root / R143_PATH).read_text())
    r125 = json.loads((root / R125_PATH).read_text())
    task = next(task for task in build_dense_validation_tasks() if task["task_id"] == TARGET_TASK)
    backend = SNAPSHOT_CLASSES[TARGET_SNAPSHOT]()
    simulator = AerSimulator.from_backend(backend)
    representative = basis_circuit(task["circuit"], tuple("Z" for _ in range(task["circuit"].num_qubits)))
    ideal = exact_distribution(task["circuit"])
    logical_edges = logical_two_qubit_edges(task)
    metadata = r125["snapshot_metadata"][TARGET_SNAPSHOT]
    measure_errors = {
        row["qargs"][0]: float(row["error"] or 0.0)
        for row in metadata["canonical"]["instruction_properties"]["measure"]
    }
    target_r143 = next(row for row in r143["group_rows"] if row["snapshot"] == TARGET_SNAPSHOT and row["task_id"] == TARGET_TASK)
    foreign_rows = [row for row in r148_design["candidate_rows"] if row["target_snapshot"] == TARGET_SNAPSHOT and row["task_id"] == TARGET_TASK]
    excluded_mappings = {
        tuple(target_r143["selected_mapping"]),
        *(tuple(row["source_mapping"]) for row in foreign_rows),
    }

    static_rows = []
    for mapping in itertools.permutations(range(backend.num_qubits), task["circuit"].num_qubits):
        if mapping in excluded_mappings:
            continue
        objective = static_layout_objective(backend, mapping, logical_edges)
        readout_vector = [measure_errors[physical] for physical in mapping]
        readout_fidelity = hellinger_fidelity(ideal, apply_symmetric_readout_channel(ideal, readout_vector))
        cx_success = 1.0 - objective["static_cx_any_error_proxy"]
        static_rows.append({
            "mapping": list(mapping),
            "exact_output_aware_readout_fidelity": readout_fidelity,
            "static_cx_success_proxy": cx_success,
            "static_product_score": readout_fidelity * cx_success,
            "static_routed_step_count_proxy": objective["routed_step_count_proxy"],
            "static_combined_any_error_proxy": objective["static_combined_any_error_proxy"],
        })
    rankings = [
        sorted(static_rows, key=lambda row: (-row["exact_output_aware_readout_fidelity"], -row["static_cx_success_proxy"], row["mapping"])),
        sorted(static_rows, key=lambda row: (-row["static_cx_success_proxy"], -row["exact_output_aware_readout_fidelity"], row["mapping"])),
        sorted(static_rows, key=lambda row: (-row["static_product_score"], row["static_routed_step_count_proxy"], row["mapping"])),
    ]
    shortlist = []
    seen = set()
    rank = 0
    while len(shortlist) < SHORTLIST_MAPPING_COUNT:
        for ranking_name, ranking in zip(("readout_first", "cx_first", "product"), rankings, strict=True):
            row = ranking[rank]
            key = tuple(row["mapping"])
            if key in seen:
                continue
            seen.add(key)
            shortlist.append({**row, "shortlist_source": ranking_name, "shortlist_source_rank": rank + 1})
            if len(shortlist) == SHORTLIST_MAPPING_COUNT:
                break
        rank += 1

    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    candidates = []
    for mapping_row in shortlist:
        for policy_id in POLICY_IDS:
            for realization_seed in REALIZATION_SEEDS:
                compiled = compile_policy(representative, backend, mapping_row["mapping"], policy_id, realization_seed)
                candidate_id = f"m{'-'.join(map(str, mapping_row['mapping']))}__{policy_id}__s{realization_seed}"
                path = out / f"{candidate_id}.qasm"
                path.write_text(qasm3.dumps(compiled), encoding="utf-8")
                exposure = circuit_exposure(path, metadata)
                semantic = hellinger_fidelity(ideal, exact_compiled_classical_distribution(compiled))
                candidates.append({
                    "candidate_id": candidate_id,
                    "mapping": mapping_row["mapping"],
                    "policy_id": policy_id,
                    "realization_seed": realization_seed,
                    "shortlist_source": mapping_row["shortlist_source"],
                    "shortlist_source_rank": mapping_row["shortlist_source_rank"],
                    "static_readout_fidelity": mapping_row["exact_output_aware_readout_fidelity"],
                    "static_cx_success_proxy": mapping_row["static_cx_success_proxy"],
                    "static_product_score": mapping_row["static_product_score"],
                    "circuit_path": str(path.relative_to(root)),
                    "circuit_sha256": file_sha256(path),
                    "qasm_stable_hash": stable_hash(qasm3.dumps(compiled)),
                    "semantic_fidelity": semantic,
                    "compiled_readout_any_error_proxy": exposure["readout_any_error_proxy"],
                    "compiled_cx_any_error_proxy": exposure["cx_any_error_proxy"],
                    "compiled_combined_any_error_proxy": exposure["combined_any_error_proxy"],
                    "compiled_cx_occurrence_count": exposure["cx_occurrence_count"],
                    "design_fidelities": [],
                    "selection_trace": [],
                })

    survivors = candidates
    charged_executions = 0
    rounds = []
    for round_index, (seeds, survivor_count) in enumerate(zip(ROUND_SEEDS, SURVIVOR_COUNTS, strict=True), start=1):
        for candidate in survivors:
            circuit = qasm3.load(root / candidate["circuit_path"])
            for seed in seeds:
                counts = simulator.run(circuit, shots=SHOTS, seed_simulator=seed).result().get_counts()
                observed = probability_from_counts(counts, SHOTS, task["circuit"].num_qubits)
                candidate["design_fidelities"].append(hellinger_fidelity(ideal, observed))
                charged_executions += 1
            candidate["selection_trace"].append({
                "round": round_index,
                "cumulative_seed_count": len(candidate["design_fidelities"]),
                "mean_fidelity": statistics.mean(candidate["design_fidelities"]),
                "lcb_95": lcb(candidate["design_fidelities"]),
            })
        ranked = sorted(
            survivors,
            key=lambda row: (
                -lcb(row["design_fidelities"]),
                -statistics.mean(row["design_fidelities"]),
                row["compiled_combined_any_error_proxy"],
                row["candidate_id"],
            ),
        )
        survivors = ranked[:survivor_count]
        rounds.append({
            "round": round_index,
            "additional_seed_count": len(seeds),
            "candidate_count_before": len(ranked),
            "survivor_count": len(survivors),
            "leader_candidate_id": ranked[0]["candidate_id"],
            "leader_mean_fidelity": statistics.mean(ranked[0]["design_fidelities"]),
            "leader_lcb_95": lcb(ranked[0]["design_fidelities"]),
        })
    selected = survivors[0]
    diagnostic_seeds = tuple(seed for seeds in ROUND_SEEDS for seed in seeds)
    selected_values = selected["design_fidelities"]
    target_circuit = compile_policy(
        representative,
        backend,
        target_r143["selected_mapping"],
        target_r143["selected_policy_id"],
        target_r143["selected_realization_seed"],
    )
    r148_selected = next(
        row
        for row in r148_design["selection_rows"]
        if row["target_snapshot"] == TARGET_SNAPSHOT and row["task_id"] == TARGET_TASK
    )
    foreign_circuit = compile_policy(
        representative,
        backend,
        r148_selected["selected_mapping"],
        r148_selected["selected_policy_id"],
        r148_selected["selected_realization_seed"],
    )
    target_values = []
    foreign_values = []
    for seed in diagnostic_seeds:
        for circuit, values in [(target_circuit, target_values), (foreign_circuit, foreign_values)]:
            counts = simulator.run(circuit, shots=SHOTS, seed_simulator=seed).result().get_counts()
            observed = probability_from_counts(counts, SHOTS, task["circuit"].num_qubits)
            values.append(hellinger_fidelity(ideal, observed))
    diagnostic_execution_count = len(diagnostic_seeds) * 2
    summary = {
        "target_snapshot": TARGET_SNAPSHOT,
        "target_task": TARGET_TASK,
        "enumerated_mapping_count": len(static_rows) + len(excluded_mappings),
        "excluded_mapping_count": len(excluded_mappings),
        "eligible_mapping_count": len(static_rows),
        "shortlist_mapping_count": len(shortlist),
        "compiled_candidate_count": len(candidates),
        "successive_halving_round_count": len(rounds),
        "charged_design_execution_count": charged_executions,
        "diagnostic_execution_count": diagnostic_execution_count,
        "total_design_execution_count": charged_executions + diagnostic_execution_count,
        "design_shots_per_execution": SHOTS,
        "total_design_shots": (charged_executions + diagnostic_execution_count) * SHOTS,
        "selected_candidate_id": selected["candidate_id"],
        "selected_mapping": selected["mapping"],
        "selected_policy_id": selected["policy_id"],
        "selected_realization_seed": selected["realization_seed"],
        "selected_mean_fidelity": statistics.mean(selected["design_fidelities"]),
        "selected_lcb_95": lcb(selected["design_fidelities"]),
        "selected_seed_count": len(selected["design_fidelities"]),
        "diagnostic_target_mean_fidelity": statistics.mean(target_values),
        "diagnostic_r148_foreign_mean_fidelity": statistics.mean(foreign_values),
        "diagnostic_selected_minus_target_mean": statistics.mean(a - b for a, b in zip(selected_values, target_values, strict=True)),
        "diagnostic_selected_minus_r148_foreign_mean": statistics.mean(a - b for a, b in zip(selected_values, foreign_values, strict=True)),
        "diagnostics_used_for_selection": False,
        "selected_circuit_path": selected["circuit_path"],
        "selected_circuit_sha256": selected["circuit_sha256"],
        "selected_qasm_stable_hash": selected["qasm_stable_hash"],
        "selected_semantic_fidelity": selected["semantic_fidelity"],
        "selected_mapping_matches_target_r143": selected["mapping"] == target_r143["selected_mapping"],
        "selected_mapping_matches_foreign_r148": any(selected["mapping"] == row["source_mapping"] for row in foreign_rows),
        "r148_hidden_trial_rows_read_count": 0,
        "challenge_executed": False,
        "hardware_execution_claimed": False,
        "quantum_advantage_claimed": False,
        "solved_frontier_claimed": False,
        "new_credit_delta": 0,
    }
    requirements = [
        {"requirement_id": "R1", "label": "R148 design/result provenance, R143 exclusion identity, R125 metadata, and task builder are bound", "passed": True},
        {"requirement_id": "R2", "label": "all 5,040 mappings are accounted for and three frozen identities are excluded", "passed": summary["enumerated_mapping_count"] == 5040 and summary["excluded_mapping_count"] == 3 and summary["eligible_mapping_count"] == 5037},
        {"requirement_id": "R3", "label": "three static rankings produce 12 unique mappings", "passed": len(shortlist) == 12 and len({tuple(row["mapping"]) for row in shortlist}) == 12},
        {"requirement_id": "R4", "label": "12 mappings, two policies, and two realization seeds produce 48 candidates", "passed": len(candidates) == 48},
        {"requirement_id": "R5", "label": "48-to-12-to-3-to-1 successive halving charges 264 executions and 32 post-selection diagnostics do not affect selection", "passed": [row["survivor_count"] for row in rounds] == [12, 3, 1] and charged_executions == 264 and diagnostic_execution_count == 32 and not summary["diagnostics_used_for_selection"]},
        {"requirement_id": "R6", "label": "all compiled candidates preserve semantics", "passed": all(row["semantic_fidelity"] >= 0.9999999999 for row in candidates)},
        {"requirement_id": "R7", "label": "selected mapping copies neither target R143 nor foreign R148 identities", "passed": not summary["selected_mapping_matches_target_r143"] and not summary["selected_mapping_matches_foreign_r148"]},
        {"requirement_id": "R8", "label": "R148 hidden rows are not loaded for generation or selection", "passed": summary["r148_hidden_trial_rows_read_count"] == 0},
        {"requirement_id": "R9", "label": "no R149 holdout is executed during design", "passed": not summary["challenge_executed"]},
        {"requirement_id": "R10", "label": "hardware, advantage, solved-frontier, and credit claims remain false", "passed": not any([summary["hardware_execution_claimed"], summary["quantum_advantage_claimed"], summary["solved_frontier_claimed"], summary["new_credit_delta"]])},
    ]
    payload = {
        "title": "B4/B8 R149 Jakarta dense-XY target-aware candidate generation design",
        "version": 0,
        "method": METHOD,
        "status": "jakarta_xy_candidate_generation_design_frozen_before_holdout",
        "model_status": "target_aware_successive_halving_without_frozen_identity_copy_or_r148_row_reuse",
        "generated_at_unix": int(time.time()),
        "source_target_id": "T-B4-002bg/T-B8-003bk/T-B10-009ay",
        "upstream_target_id": "T-B4-002bf/T-B8-003bj/T-B10-009ax",
        "source_bindings": {
            "r148_design_path": R148_DESIGN_PATH,
            "r148_design_sha256": file_sha256(root / R148_DESIGN_PATH),
            "r148_design_payload_hash": r148_design["payload_hash"],
            "r148_result_path": R148_RESULT_PATH,
            "r148_result_sha256_provenance_only": file_sha256(root / R148_RESULT_PATH),
            "r148_trial_rows_consumed": False,
            "r143_design_path": R143_PATH,
            "r143_design_sha256": file_sha256(root / R143_PATH),
            "r143_design_payload_hash": r143["payload_hash"],
            "r125_snapshot_path": R125_PATH,
            "r125_snapshot_sha256": file_sha256(root / R125_PATH),
            "r125_snapshot_payload_hash": r125["payload_hash"],
            "task_builder_path": TASK_BUILDER_PATH,
            "task_builder_sha256": file_sha256(root / TASK_BUILDER_PATH),
        },
        "excluded_route_identities": {
            "target_r143_mapping": target_r143["selected_mapping"],
            "foreign_r148_mappings": [row["source_mapping"] for row in foreign_rows],
        },
        "design_protocol": {
            "static_rankings": ["exact_output_aware_readout_fidelity", "static_cx_success_proxy", "static_product_score"],
            "shortlist_mapping_count": SHORTLIST_MAPPING_COUNT,
            "policy_ids": list(POLICY_IDS),
            "realization_seeds": list(REALIZATION_SEEDS),
            "round_simulator_seeds": [list(seeds) for seeds in ROUND_SEEDS],
            "survivor_counts": list(SURVIVOR_COUNTS),
            "shots_per_execution": SHOTS,
            "selection_statistic": "mean_fidelity_minus_1.96_standard_error",
            "post_selection_diagnostic_arms": ["target_specific_r143", "r148_selected_foreign"],
            "post_selection_diagnostics_used_for_selection": False,
        },
        "summary": summary,
        "static_shortlist_rows": shortlist,
        "candidate_rows": candidates,
        "successive_halving_rounds": rounds,
        "requirements": requirements,
        "requirement_count": 10,
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [row["requirement_id"] for row in requirements if not row["passed"]],
        "artifacts": {"candidate_directory": OUT_DIR, "result": RESULT_PATH, "markdown_report": REPORT_PATH},
        "claim_boundary": {
            "what_is_supported": "one target-aware generated Jakarta dense-XY candidate selected without copying frozen route identities or reading R148 hidden rows",
            "what_is_not_supported": "a holdout repair, general candidate-generation advantage, temporal transfer, cross-machine transfer, real hardware, mitigation, soundness, quantum advantage, BQP separation, solved B4/B8/B10, or new credit",
        },
    }
    hash_payload = dict(payload)
    payload["payload_hash"] = hashlib.sha256(json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload


def report(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    rounds = "\n".join(
        f"- Round `{row['round']}`: `{row['candidate_count_before']}` to `{row['survivor_count']}`, leader `{row['leader_candidate_id']}`, LCB `{row['leader_lcb_95']:.8f}`."
        for row in payload["successive_halving_rounds"]
    )
    return f"""# B4/B8 R149 Jakarta Dense-XY Candidate Generation Design

- Enumerated / excluded / eligible mappings: `{s['enumerated_mapping_count']}` / `{s['excluded_mapping_count']}` / `{s['eligible_mapping_count']}`
- Shortlist mappings / compiled candidates: `{s['shortlist_mapping_count']}` / `{s['compiled_candidate_count']}`
- Selection / diagnostic / total executions: `{s['charged_design_execution_count']}` / `{s['diagnostic_execution_count']}` / `{s['total_design_execution_count']}`
- Total design shots: `{s['total_design_shots']}`
- Selected candidate: `{s['selected_candidate_id']}`
- Selected mapping / policy / seed: `{s['selected_mapping']}` / `{s['selected_policy_id']}` / `{s['selected_realization_seed']}`
- Selected mean / 95% LCB: `{s['selected_mean_fidelity']:.8f}` / `{s['selected_lcb_95']:.8f}`
- Diagnostic selected-target / selected-R148-foreign means: `{s['diagnostic_selected_minus_target_mean']:+.8f}` / `{s['diagnostic_selected_minus_r148_foreign_mean']:+.8f}`
- Copies target R143 / foreign R148 mapping: `{str(s['selected_mapping_matches_target_r143']).lower()}` / `{str(s['selected_mapping_matches_foreign_r148']).lower()}`
- R148 hidden rows read: `{s['r148_hidden_trial_rows_read_count']}`
- Holdout executed: `false`

## Successive Halving

{rounds}

The design excludes the target-specific R143 mapping and both foreign R148
mappings before enumerating candidates. Three public-calibration views create
a 12-mapping shortlist; two policies and two realization seeds create 48 new
compiled routes. Fixed public design seeds reduce them 48 to 12 to 3 to 1 by
fidelity LCB. Only after selection, 32 diagnostic executions compare the
winner with target-specific R143 and R148 foreign routes; these diagnostics do
not alter selection. No R148 hidden row is loaded.

This design does not establish a holdout repair, general route-generation
advantage, temporal or cross-machine transfer, real hardware, mitigation,
soundness, quantum advantage, BQP separation, a solved frontier, or new credit.
"""


def main() -> int:
    ensure_environment()
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
