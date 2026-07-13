#!/usr/bin/env python3
"""Execute the preregistered R149 Jakarta dense-XY candidate-generation holdout."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r121_private_bundle_shot_sweep import basis_circuit, stable_hash
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r127_calibration_aware_layout_design import SNAPSHOT_CLASSES
from b4_b8_r132_topology_constrained_route_policy import DETERMINISTIC_PROCESS_ENV, compile_policy
from b4_b8_r135_dense_interaction_fallback import build_dense_validation_tasks
from b4_b8_r138_postcommit_statistical_challenge import exact_distribution, hellinger_fidelity, paired_bootstrap, probability_from_counts
from b4_b8_r139_lagos_ising_channel_attribution import exact_compiled_classical_distribution


METHOD = "b4_b8_r149_jakarta_xy_candidate_generation_holdout_v0"
CONTRACT_PATH = "benchmarks/B4_B8_R149_jakarta_xy_candidate_generation_contract_v0.json"
CONTRACT_SHA256 = "4efbda7920ec5b7cc9486145076f4550d109f6db32c730904e9fc406c4a80552"
PREREGISTRATION_COMMIT = "5791504f0223cb98b9cbc9aa2277470558fbe1aa"
PREREGISTRATION_DISCUSSION = "https://github.com/crystal-tensor/Prometheus-plan/discussions/161"
PREREGISTRATION_CREATED_AT = "2026-07-13T10:25:26Z"
PROTOCOL_PATH = "results/B4_B8_R149_jakarta_xy_candidate_generation_protocol_v0.json"
DESIGN_PATH = "results/B4_B8_R149_jakarta_xy_candidate_generation_design_v0.json"
R148_DESIGN_PATH = "results/B4_B8_R148_task_conditioned_channel_risk_design_v0.json"
R143_PATH = "results/B4_B8_R143_successive_halving_lcb_design_v0.json"
RESULT_PATH = "results/B4_B8_R149_jakarta_xy_candidate_generation_holdout_v0.json"
REPORT_PATH = "research/B4_B8_R149_jakarta_xy_candidate_generation_holdout.md"
OUT_DIR = "results/B4_B8_R149_jakarta_xy_candidate_generation_holdout"
COMMITMENT_PATH = f"{OUT_DIR}/challenge_commitment.json"
TRIALS_PATH = f"{OUT_DIR}/portfolio_trial_rows.json"
REVEAL_PATH = f"{OUT_DIR}/challenge_reveal.json"
TRANSCRIPT_PATH = f"{OUT_DIR}/verifier_transcript.json"


def ensure_environment() -> None:
    if all(os.environ.get(key) == value for key, value in DETERMINISTIC_PROCESS_ENV.items()):
        return
    environment = dict(os.environ)
    environment.update(DETERMINISTIC_PROCESS_ENV)
    os.execvpe(sys.executable, [sys.executable, *sys.argv], environment)


def utc_timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def derive_seed(secret: bytes, group_id: str, trial: int, role: str) -> int:
    message = f"{CONTRACT_SHA256}|{group_id}|{trial}|{role}".encode()
    digest = hmac.new(secret, message, hashlib.sha256).digest()
    return int.from_bytes(digest[:8], "big") % (2**31 - 1) + 1


def condition(condition_id: str, label: str, value: Any, threshold: Any, passed: bool) -> dict[str, Any]:
    return {"condition_id": condition_id, "label": label, "value": value, "threshold": threshold, "passed": passed}


def report(payload: dict) -> str:
    s = payload["summary"]
    verdict = "ACCEPT" if s["global_acceptance"] else "REJECT"
    conditions = "\n".join(
        f"- {row['condition_id']} {'PASS' if row['passed'] else 'FAIL'}: {row['label']}; value {row['value']}, threshold {row['threshold']}."
        for row in payload["acceptance_conditions"]
    )
    targets = "\n".join(
        f"- `{row['target_snapshot']}`: repaired-target `{row['mean_repaired_minus_target']:+.8f}`, repaired-auto `{row['mean_repaired_minus_automatic']:+.8f}` over `{row['row_count']}` rows."
        for row in payload["target_snapshot_rows"]
    )
    replacements = "\n".join(
        f"- `{row['portfolio_group_id']}`: repaired-target mean `{row['mean_repaired_minus_target']:+.8f}`, minimum `{row['minimum_repaired_minus_target']:+.8f}`, severe rows `{row['severe_regression_count']}`."
        for row in payload["replacement_group_rows"]
    )
    return f"""# B4/B8 R149 Jakarta Dense-XY Candidate-Generation Holdout

- Preregistered verdict: {verdict}
- Groups / trial rows: `{s['portfolio_group_count']}` / `{s['trial_row_count']}`
- Three-arm executions / shots: `{s['simulated_circuit_execution_count']}` / `{s['total_simulated_shots']}`
- Portfolio repaired-automatic mean / bootstrap lower: `{s['portfolio_mean_repaired_minus_automatic']:+.8f}` / `{s['portfolio_repaired_minus_automatic_bootstrap_95_lower']:+.8f}`
- Portfolio repaired-target mean / bootstrap lower: `{s['portfolio_mean_repaired_minus_target']:+.8f}` / `{s['portfolio_repaired_minus_target_bootstrap_95_lower']:+.8f}`
- Groups above -0.02 versus target: `{s['groups_with_mean_repaired_minus_target_at_least_negative_0_02']} / 12`
- Severe rows below -0.05 versus target: `{s['severe_repaired_minus_target_regression_count_below_negative_0_05']}`
- Minimum target-snapshot mean: `{s['minimum_target_snapshot_mean_repaired_minus_target']:+.8f}`
- Replacement repaired-target / repaired-R148 means: `{s['replacement_group_mean_repaired_minus_target']:+.8f}` / `{s['replacement_group_mean_repaired_minus_r148_foreign']:+.8f}`
- Replacement minimum / severe rows: `{s['replacement_group_minimum_repaired_minus_target']:+.8f}` / `{s['replacement_group_severe_regression_count']}`
- Semantic passes: `{s['semantic_fidelity_pass_count']} / 24`
- Conditions passed / failed: `{s['acceptance_conditions_passed']}` / `{s['acceptance_conditions_failed']}`
- New credit delta: `0`

## Target Snapshot Evidence

{targets}

## Jakarta Dense-XY Replacement

{replacements}

## Acceptance Conditions

{conditions}

## Claim Boundary

Supported only if accepted: one preregistered finite six-qubit synthetic
generated-route portfolio verdict. Not supported: general route-generation
advantage, temporal same-device transfer, cross-machine transfer, provider
access, real hardware, mitigation, soundness, quantum advantage, BQP
separation, solved B4/B8/B10, or new credit.
"""


def run_gate(root: Path) -> dict:
    root = root.resolve()
    started_at = int(time.time())
    if started_at <= utc_timestamp(PREREGISTRATION_CREATED_AT):
        raise ValueError("R149 holdout must start after public preregistration")
    if file_sha256(root / CONTRACT_PATH) != CONTRACT_SHA256:
        raise ValueError("R149 contract hash mismatch")
    contract = json.loads((root / CONTRACT_PATH).read_text())
    protocol_payload = json.loads((root / PROTOCOL_PATH).read_text())
    design = json.loads((root / DESIGN_PATH).read_text())
    r148_design = json.loads((root / R148_DESIGN_PATH).read_text())
    r143 = json.loads((root / R143_PATH).read_text())
    bindings = contract["source_bindings"]
    if file_sha256(root / PROTOCOL_PATH) != bindings["protocol_sha256"] or protocol_payload["payload_hash"] != bindings["protocol_payload_hash"]:
        raise ValueError("R149 protocol binding mismatch")
    if file_sha256(root / DESIGN_PATH) != bindings["r149_design_sha256"] or design["payload_hash"] != bindings["r149_design_payload_hash"]:
        raise ValueError("R149 design binding mismatch")
    if file_sha256(root / R148_DESIGN_PATH) != bindings["r148_design_sha256"] or r148_design["payload_hash"] != bindings["r148_design_payload_hash"]:
        raise ValueError("R149 frozen R148 design binding mismatch")
    if file_sha256(root / R143_PATH) != bindings["r143_design_sha256"] or r143["payload_hash"] != bindings["r143_design_payload_hash"]:
        raise ValueError("R149 R143 binding mismatch")
    if bindings.get("r148_trial_rows_consumed") is not False or design["summary"]["r148_hidden_trial_rows_read_count"] != 0:
        raise ValueError("R149 forbidden R148 row consumption boundary mismatch")
    protocol = protocol_payload["protocol"]
    tasks = {task["task_id"]: task for task in build_dense_validation_tasks()}
    r148_selections = {(row["target_snapshot"], row["task_id"]): row for row in r148_design["selection_rows"]}
    replacement_group_id = protocol["replacement_group_id"]
    selected_generated = design["summary"]
    target_routes = {(row["snapshot"], row["task_id"]): row for row in r143["group_rows"]}

    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    commitment_path = root / COMMITMENT_PATH
    trials_path = root / TRIALS_PATH
    reveal_path = root / REVEAL_PATH
    transcript_path = root / TRANSCRIPT_PATH
    phase_paths = [commitment_path, trials_path, reveal_path, transcript_path]
    preexisting = {str(path): path.read_bytes() for path in phase_paths if path.exists()}
    secret = bytes.fromhex(json.loads(reveal_path.read_text())["challenge_secret_hex"]) if reveal_path.exists() else os.urandom(32)
    commitment = hashlib.sha256(secret).hexdigest()
    if commitment_path.exists():
        commitment_payload = json.loads(commitment_path.read_text())
        if commitment_payload["challenge_secret_commitment_sha256"] != commitment:
            raise ValueError("R149 challenge commitment mismatch")
    else:
        commitment_payload = {
            "contract_sha256": CONTRACT_SHA256,
            "preregistration_commit": PREREGISTRATION_COMMIT,
            "preregistration_discussion": PREREGISTRATION_DISCUSSION,
            "preregistration_created_at": PREREGISTRATION_CREATED_AT,
            "challenge_generated_at_unix": started_at,
            "challenge_secret_commitment_sha256": commitment,
            "secret_revealed": False,
        }
    write_json(commitment_path, commitment_payload)

    trial_rows = []
    compiled_rows = []
    for target_snapshot in protocol["snapshot_names"]:
        backend = SNAPSHOT_CLASSES[target_snapshot]()
        simulator = AerSimulator.from_backend(backend)
        for task_id in protocol["task_ids"]:
            group_id = f"{target_snapshot}::{task_id}"
            task = tasks[task_id]
            logical = basis_circuit(task["circuit"], tuple("Z" for _ in range(task["circuit"].num_qubits)))
            ideal = exact_distribution(task["circuit"])
            frozen = r148_selections[(target_snapshot, task_id)]
            is_replacement = group_id == replacement_group_id
            if is_replacement:
                route_mapping = selected_generated["selected_mapping"]
                route_policy = selected_generated["selected_policy_id"]
                route_seed = selected_generated["selected_realization_seed"]
                route_source = "r149_generated"
            else:
                route_mapping = frozen["selected_mapping"]
                route_policy = frozen["selected_policy_id"]
                route_seed = frozen["selected_realization_seed"]
                route_source = frozen["selected_source_snapshot"]
            target_route = target_routes[(target_snapshot, task_id)]
            repaired = compile_policy(logical, backend, route_mapping, route_policy, route_seed)
            target = compile_policy(logical, backend, target_route["selected_mapping"], target_route["selected_policy_id"], target_route["selected_realization_seed"])
            old_r148 = compile_policy(logical, backend, frozen["selected_mapping"], frozen["selected_policy_id"], frozen["selected_realization_seed"]) if is_replacement else None
            repaired_semantic = hellinger_fidelity(ideal, exact_compiled_classical_distribution(repaired))
            target_semantic = hellinger_fidelity(ideal, exact_compiled_classical_distribution(target))
            compiled_rows.append({
                "portfolio_group_id": group_id,
                "target_snapshot": target_snapshot,
                "task_id": task_id,
                "route_source": route_source,
                "is_r149_replacement": is_replacement,
                "repaired_mapping": route_mapping,
                "repaired_policy_id": route_policy,
                "repaired_realization_seed": route_seed,
                "repaired_qasm_stable_hash": stable_hash(qasm3.dumps(repaired)),
                "target_specific_qasm_stable_hash": stable_hash(qasm3.dumps(target)),
                "repaired_semantic_fidelity": repaired_semantic,
                "target_specific_semantic_fidelity": target_semantic,
            })
            for trial in range(protocol["hidden_trial_count_per_group"]):
                transpiler_seed = derive_seed(secret, group_id, trial, "transpiler")
                simulator_seed = derive_seed(secret, group_id, trial, "simulator")
                automatic = transpile(logical, backend=backend, optimization_level=3, seed_transpiler=transpiler_seed)
                fidelities = {}
                arms = [("repaired_portfolio", repaired), ("target_specific", target), ("automatic", automatic)]
                if is_replacement:
                    arms.append(("r148_foreign", old_r148))
                for arm, circuit in arms:
                    counts = simulator.run(circuit, shots=protocol["shots_per_execution"], seed_simulator=simulator_seed).result().get_counts()
                    observed = probability_from_counts(counts, protocol["shots_per_execution"], task["circuit"].num_qubits)
                    fidelities[arm] = hellinger_fidelity(ideal, observed)
                trial_rows.append({
                    "portfolio_group_id": group_id,
                    "target_snapshot": target_snapshot,
                    "task_id": task_id,
                    "trial": trial,
                    "transpiler_seed": transpiler_seed,
                    "simulator_seed": simulator_seed,
                    "repaired_fidelity": fidelities["repaired_portfolio"],
                    "target_specific_fidelity": fidelities["target_specific"],
                    "automatic_fidelity": fidelities["automatic"],
                    "r148_foreign_fidelity": fidelities.get("r148_foreign"),
                    "repaired_minus_automatic": fidelities["repaired_portfolio"] - fidelities["automatic"],
                    "repaired_minus_target": fidelities["repaired_portfolio"] - fidelities["target_specific"],
                    "repaired_minus_r148_foreign": fidelities["repaired_portfolio"] - fidelities["r148_foreign"] if is_replacement else None,
                })
    write_json(trials_path, trial_rows)
    reveal = {
        "contract_sha256": CONTRACT_SHA256,
        "challenge_secret_hex": secret.hex(),
        "challenge_secret_commitment_sha256": commitment,
        "commitment_matches": hashlib.sha256(secret).hexdigest() == commitment,
        "trial_rows_complete_before_reveal": len(trial_rows) == protocol["trial_row_count"],
    }
    write_json(reveal_path, reveal)

    group_rows = []
    for group_id in sorted({row["portfolio_group_id"] for row in trial_rows}):
        rows = [row for row in trial_rows if row["portfolio_group_id"] == group_id]
        group_rows.append({
            "portfolio_group_id": group_id,
            "target_snapshot": rows[0]["target_snapshot"],
            "task_id": rows[0]["task_id"],
            "row_count": len(rows),
            "mean_repaired_minus_automatic": statistics.mean(row["repaired_minus_automatic"] for row in rows),
            "mean_repaired_minus_target": statistics.mean(row["repaired_minus_target"] for row in rows),
            "repaired_win_count_vs_automatic": sum(row["repaired_minus_automatic"] > 0 for row in rows),
            "repaired_win_count_vs_target": sum(row["repaired_minus_target"] > 0 for row in rows),
            "minimum_repaired_minus_target": min(row["repaired_minus_target"] for row in rows),
            "severe_regression_count": sum(row["repaired_minus_target"] < -0.05 for row in rows),
        })
    target_rows = []
    for target_snapshot in protocol["snapshot_names"]:
        rows = [row for row in trial_rows if row["target_snapshot"] == target_snapshot]
        target_rows.append({
            "target_snapshot": target_snapshot,
            "row_count": len(rows),
            "mean_repaired_minus_automatic": statistics.mean(row["repaired_minus_automatic"] for row in rows),
            "mean_repaired_minus_target": statistics.mean(row["repaired_minus_target"] for row in rows),
        })
    replacement_group_rows = [row for row in group_rows if row["portfolio_group_id"] == replacement_group_id]
    replacement_trial_rows = [row for row in trial_rows if row["portfolio_group_id"] == replacement_group_id]
    auto_deltas = [row["repaired_minus_automatic"] for row in trial_rows]
    target_deltas = [row["repaired_minus_target"] for row in trial_rows]
    bootstrap_auto = paired_bootstrap(auto_deltas, derive_seed(secret, "portfolio", 0, "bootstrap-auto"), 10000)
    bootstrap_target = paired_bootstrap(target_deltas, derive_seed(secret, "portfolio", 0, "bootstrap-target"), 10000)
    semantic_values = [value for row in compiled_rows for value in [row["repaired_semantic_fidelity"], row["target_specific_semantic_fidelity"]]]
    summary = {
        "portfolio_group_count": len(group_rows),
        "trial_row_count": len(trial_rows),
        "simulated_circuit_execution_count": len(trial_rows) * 3 + len(replacement_trial_rows),
        "total_simulated_shots": (len(trial_rows) * 3 + len(replacement_trial_rows)) * protocol["shots_per_execution"],
        "portfolio_mean_repaired_minus_automatic": statistics.mean(auto_deltas),
        "portfolio_repaired_minus_automatic_bootstrap_95_lower": bootstrap_auto["lower_95"],
        "portfolio_repaired_minus_automatic_bootstrap_95_upper": bootstrap_auto["upper_95"],
        "portfolio_mean_repaired_minus_target": statistics.mean(target_deltas),
        "portfolio_repaired_minus_target_bootstrap_95_lower": bootstrap_target["lower_95"],
        "portfolio_repaired_minus_target_bootstrap_95_upper": bootstrap_target["upper_95"],
        "groups_with_mean_repaired_minus_target_at_least_negative_0_02": sum(row["mean_repaired_minus_target"] >= -0.02 for row in group_rows),
        "severe_repaired_minus_target_regression_count_below_negative_0_05": sum(value < -0.05 for value in target_deltas),
        "minimum_target_snapshot_mean_repaired_minus_target": min(row["mean_repaired_minus_target"] for row in target_rows),
        "replacement_group_count": len(replacement_group_rows),
        "replacement_group_mean_repaired_minus_target": replacement_group_rows[0]["mean_repaired_minus_target"],
        "replacement_group_mean_repaired_minus_r148_foreign": statistics.mean(row["repaired_minus_r148_foreign"] for row in replacement_trial_rows),
        "replacement_group_minimum_repaired_minus_target": replacement_group_rows[0]["minimum_repaired_minus_target"],
        "replacement_group_severe_regression_count": replacement_group_rows[0]["severe_regression_count"],
        "minimum_semantic_fidelity": min(semantic_values),
        "semantic_fidelity_pass_count": sum(value >= protocol["minimum_semantic_fidelity"] for value in semantic_values),
        "generated_mapping_matches_target_r143": selected_generated["selected_mapping_matches_target_r143"],
        "generated_mapping_matches_foreign_r148": selected_generated["selected_mapping_matches_foreign_r148"],
        "phase_artifact_count": 4,
        "phase_artifact_preexisting_count": len(preexisting),
        "r148_hidden_trial_rows_read_count": 0,
        "target_specific_routes_in_selector_count": 0,
        "scalable_exact_output_method_claimed": False,
        "temporal_same_device_transfer_claimed": False,
        "cross_machine_transfer_claimed": False,
        "hardware_execution_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "solved_frontier_claimed": False,
        "new_credit_delta": 0,
    }
    a8_pass = summary["minimum_target_snapshot_mean_repaired_minus_target"] >= protocol["minimum_each_target_mean_repaired_minus_target"] and summary["replacement_group_mean_repaired_minus_target"] >= protocol["minimum_replacement_group_mean_repaired_minus_target"] and summary["replacement_group_mean_repaired_minus_r148_foreign"] >= protocol["minimum_replacement_group_mean_repaired_minus_r148_foreign"] and summary["replacement_group_severe_regression_count"] <= protocol["maximum_replacement_group_severe_regression_count"]
    conditions = [
        condition("A1", "protocol, selector, route identities, and source bindings remain exact", True, True, True),
        condition("A2", "groups, rows, executions, and replacement-only diagnostic arm", [summary["portfolio_group_count"], summary["trial_row_count"], summary["simulated_circuit_execution_count"], len(replacement_trial_rows)], [12, 96, 296, 8], summary["portfolio_group_count"] == 12 and summary["trial_row_count"] == 96 and summary["simulated_circuit_execution_count"] == 296 and len(replacement_trial_rows) == 8),
        condition("A3", "all repaired and target routes retain semantic fidelity", [summary["semantic_fidelity_pass_count"], summary["minimum_semantic_fidelity"]], [24, protocol["minimum_semantic_fidelity"]], summary["semantic_fidelity_pass_count"] == 24),
        condition("A4", "portfolio repaired versus automatic noninferiority", [summary["portfolio_mean_repaired_minus_automatic"], summary["portfolio_repaired_minus_automatic_bootstrap_95_lower"]], [protocol["minimum_portfolio_repaired_minus_automatic_mean"], protocol["minimum_portfolio_repaired_minus_automatic_bootstrap_lower"]], summary["portfolio_mean_repaired_minus_automatic"] >= protocol["minimum_portfolio_repaired_minus_automatic_mean"] and summary["portfolio_repaired_minus_automatic_bootstrap_95_lower"] >= protocol["minimum_portfolio_repaired_minus_automatic_bootstrap_lower"]),
        condition("A5", "portfolio repaired versus target-specific noninferiority", [summary["portfolio_mean_repaired_minus_target"], summary["portfolio_repaired_minus_target_bootstrap_95_lower"]], [protocol["minimum_portfolio_repaired_minus_target_mean"], protocol["minimum_portfolio_repaired_minus_target_bootstrap_lower"]], summary["portfolio_mean_repaired_minus_target"] >= protocol["minimum_portfolio_repaired_minus_target_mean"] and summary["portfolio_repaired_minus_target_bootstrap_95_lower"] >= protocol["minimum_portfolio_repaired_minus_target_bootstrap_lower"]),
        condition("A6", "groups above negative 0.02 versus target", summary["groups_with_mean_repaired_minus_target_at_least_negative_0_02"], protocol["minimum_group_count_above_negative_0_02_vs_target"], summary["groups_with_mean_repaired_minus_target_at_least_negative_0_02"] >= protocol["minimum_group_count_above_negative_0_02_vs_target"]),
        condition("A7", "severe row regressions below negative 0.05", summary["severe_repaired_minus_target_regression_count_below_negative_0_05"], protocol["maximum_severe_regression_count_below_negative_0_05_vs_target"], summary["severe_repaired_minus_target_regression_count_below_negative_0_05"] <= protocol["maximum_severe_regression_count_below_negative_0_05_vs_target"]),
        condition("A8", "each-target and Jakarta dense-XY replacement guards", [summary["minimum_target_snapshot_mean_repaired_minus_target"], summary["replacement_group_mean_repaired_minus_target"], summary["replacement_group_mean_repaired_minus_r148_foreign"], summary["replacement_group_severe_regression_count"]], [protocol["minimum_each_target_mean_repaired_minus_target"], protocol["minimum_replacement_group_mean_repaired_minus_target"], protocol["minimum_replacement_group_mean_repaired_minus_r148_foreign"], protocol["maximum_replacement_group_severe_regression_count"]], a8_pass),
        condition("A9", "commitment, hidden rows, reveal, and transcript", reveal["commitment_matches"] and reveal["trial_rows_complete_before_reveal"], True, reveal["commitment_matches"] and reveal["trial_rows_complete_before_reveal"]),
        condition("A10", "forbidden claims and credit remain false", 0, 0, not any([summary["scalable_exact_output_method_claimed"], summary["temporal_same_device_transfer_claimed"], summary["cross_machine_transfer_claimed"], summary["hardware_execution_claimed"], summary["quantum_advantage_claimed"], summary["bqp_separation_claimed"], summary["solved_frontier_claimed"], summary["new_credit_delta"]])),
    ]
    summary.update({
        "acceptance_conditions_passed": sum(row["passed"] for row in conditions),
        "acceptance_conditions_failed": sum(not row["passed"] for row in conditions),
        "failed_acceptance_condition_ids": [row["condition_id"] for row in conditions if not row["passed"]],
        "global_acceptance": all(row["passed"] for row in conditions),
    })
    transcript = {"contract_sha256": CONTRACT_SHA256, "trial_rows_sha256": file_sha256(trials_path), "challenge_secret_commitment_sha256": commitment, "acceptance_conditions": conditions, "global_acceptance": summary["global_acceptance"]}
    write_json(transcript_path, transcript)
    phase_replay = sum(path.exists() and (str(path) not in preexisting or path.read_bytes() == preexisting[str(path)]) for path in phase_paths)
    summary["phase_artifact_replay_match_count"] = phase_replay
    requirements = [
        {"requirement_id": "P1", "label": "public preregistration precedes challenge", "passed": started_at >= utc_timestamp(PREREGISTRATION_CREATED_AT)},
        {"requirement_id": "P2", "label": "contract, protocol, design, and R143 hashes verify", "passed": True},
        {"requirement_id": "P3", "label": "12 frozen groups execute", "passed": len(group_rows) == 12},
        {"requirement_id": "P4", "label": "three portfolio arms and the replacement-only diagnostic share each row seed", "passed": len(trial_rows) == 96 and len(replacement_trial_rows) == 8},
        {"requirement_id": "P5", "label": "commitment matches revealed secret", "passed": reveal["commitment_matches"]},
        {"requirement_id": "P6", "label": "trial rows are complete before reveal", "passed": reveal["trial_rows_complete_before_reveal"]},
        {"requirement_id": "P7", "label": "24 compiled route semantic checks pass", "passed": summary["semantic_fidelity_pass_count"] == 24},
        {"requirement_id": "P8", "label": "four phase artifacts replay", "passed": phase_replay == 4},
        {"requirement_id": "P9", "label": "acceptance transcript contains A1-A10", "passed": len(conditions) == 10},
        {"requirement_id": "P10", "label": "R148 rows stay unused and claim boundary remains explicit", "passed": summary["r148_hidden_trial_rows_read_count"] == 0 and conditions[-1]["passed"]},
    ]
    payload = {
        "title": "B4/B8 R149 Jakarta dense-XY candidate-generation holdout",
        "version": 0,
        "method": METHOD,
        "status": "jakarta_xy_candidate_generation_preregistered_acceptance" if summary["global_acceptance"] else "jakarta_xy_candidate_generation_preregistered_rejection",
        "model_status": "one_generated_replacement_plus_eleven_frozen_r148_routes",
        "generated_at_unix": started_at,
        "source_target_id": "T-B4-002bh/T-B8-003bl/T-B10-009az",
        "upstream_target_id": "T-B4-002bg/T-B8-003bk/T-B10-009ay",
        "summary": summary,
        "acceptance_conditions": conditions,
        "compiled_route_rows": compiled_rows,
        "group_rows": group_rows,
        "target_snapshot_rows": target_rows,
        "replacement_group_rows": replacement_group_rows,
        "requirements": requirements,
        "requirement_count": 10,
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [row["requirement_id"] for row in requirements if not row["passed"]],
        "artifacts": {"contract": CONTRACT_PATH, "challenge_commitment": COMMITMENT_PATH, "portfolio_trial_rows": TRIALS_PATH, "challenge_reveal": REVEAL_PATH, "verifier_transcript": TRANSCRIPT_PATH, "result": RESULT_PATH, "markdown_report": REPORT_PATH},
        "claim_boundary": {"what_is_supported": "one preregistered finite six-qubit synthetic generated-route portfolio verdict", "what_is_not_supported": "general route-generation advantage, temporal same-device transfer, cross-machine transfer, provider access, real hardware, mitigation, soundness, quantum advantage, BQP separation, solved B4/B8/B10, or new credit"},
    }
    hash_payload = dict(payload)
    payload["payload_hash"] = hashlib.sha256(json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    write_json(root / RESULT_PATH, payload)
    (root / REPORT_PATH).write_text(report(payload), encoding="utf-8")
    return payload


def main() -> int:
    ensure_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    payload = run_gate(args.root)
    print(json.dumps({"status": payload["status"], "summary": payload["summary"], "requirements_passed": payload["requirements_passed"], "requirements_failed": payload["requirements_failed"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
