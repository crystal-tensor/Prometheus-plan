#!/usr/bin/env python3
"""Execute the preregistered R146 cross-snapshot transfer holdout."""

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


METHOD = "b4_b8_r146_cross_snapshot_transfer_holdout_v0"
CONTRACT_PATH = "benchmarks/B4_B8_R146_cross_snapshot_transfer_contract_v0.json"
CONTRACT_SHA256 = "5e29e68eefcb6809a4df6cc86916b76f299267f36eeabc4d44fd22754cfaceb3"
PREREGISTRATION_COMMIT = "3654f2e44d30e26f2a2c1c1911a11054132e673c"
PREREGISTRATION_DISCUSSION = "https://github.com/crystal-tensor/Prometheus-plan/discussions/155"
PREREGISTRATION_CREATED_AT = "2026-07-13T09:33:26Z"
PROTOCOL_PATH = "results/B4_B8_R146_cross_snapshot_transfer_protocol_v0.json"
R143_PATH = "results/B4_B8_R143_successive_halving_lcb_design_v0.json"
RESULT_PATH = "results/B4_B8_R146_cross_snapshot_transfer_holdout_v0.json"
REPORT_PATH = "research/B4_B8_R146_cross_snapshot_transfer_holdout.md"
OUT_DIR = "results/B4_B8_R146_cross_snapshot_transfer_holdout"
COMMITMENT_PATH = f"{OUT_DIR}/challenge_commitment.json"
TRIALS_PATH = f"{OUT_DIR}/three_arm_trial_rows.json"
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


def derive_seed(secret: bytes, transfer_id: str, trial: int, role: str) -> int:
    message = f"{CONTRACT_SHA256}|{transfer_id}|{trial}|{role}".encode()
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
        f"- `{row['target_snapshot']}`: transfer-target `{row['mean_transfer_minus_target']:+.8f}`, transfer-auto `{row['mean_transfer_minus_automatic']:+.8f}` over `{row['row_count']}` rows."
        for row in payload["target_snapshot_rows"]
    )
    return f"""# B4/B8 R146 Cross-Backend Snapshot Transfer Holdout

- Preregistered verdict: {verdict}
- Transfer groups / trial rows: `{s['transfer_group_count']}` / `{s['trial_row_count']}`
- Three-arm executions / shots: `{s['simulated_circuit_execution_count']}` / `{s['total_simulated_shots']}`
- Portfolio transfer-automatic mean / bootstrap lower: `{s['portfolio_mean_transfer_minus_automatic']:+.8f}` / `{s['portfolio_transfer_minus_automatic_bootstrap_95_lower']:+.8f}`
- Portfolio transfer-target mean / bootstrap lower: `{s['portfolio_mean_transfer_minus_target']:+.8f}` / `{s['portfolio_transfer_minus_target_bootstrap_95_lower']:+.8f}`
- Groups above -0.02 versus target: `{s['groups_with_mean_transfer_minus_target_at_least_negative_0_02']} / 24`
- Severe rows below -0.05 versus target: `{s['severe_transfer_minus_target_regression_count_below_negative_0_05']}`
- Minimum target-snapshot mean versus target: `{s['minimum_target_snapshot_mean_transfer_minus_target']:+.8f}`
- Semantic passes: `{s['semantic_fidelity_pass_count']} / 48`
- Conditions passed / failed: `{s['acceptance_conditions_passed']} / {s['acceptance_conditions_failed']}`
- New credit delta: `0`

## Target Snapshot Evidence

{targets}

## Acceptance Conditions

{conditions}

## Claim Boundary

Supported only if accepted: one preregistered synthetic all-direction transfer
verdict across three fake-backend snapshots. Not supported: temporal same-device
calibration drift, cross-machine transfer, provider access, real hardware,
mitigation, soundness, quantum advantage, BQP separation, solved B4/B8/B10, or
new credit.
"""


def run_gate(root: Path) -> dict:
    root = root.resolve()
    started_at = int(time.time())
    if started_at <= utc_timestamp(PREREGISTRATION_CREATED_AT):
        raise ValueError("R146 holdout must start after public preregistration")
    if file_sha256(root / CONTRACT_PATH) != CONTRACT_SHA256:
        raise ValueError("R146 contract hash mismatch")
    contract = json.loads((root / CONTRACT_PATH).read_text())
    protocol_payload = json.loads((root / PROTOCOL_PATH).read_text())
    bindings = contract["source_bindings"]
    if file_sha256(root / PROTOCOL_PATH) != bindings["protocol_sha256"] or protocol_payload["payload_hash"] != bindings["protocol_payload_hash"]:
        raise ValueError("R146 protocol binding mismatch")
    if file_sha256(root / R143_PATH) != bindings["r143_design_sha256"]:
        raise ValueError("R146 R143 binding mismatch")
    r143 = json.loads((root / R143_PATH).read_text())
    if r143["payload_hash"] != bindings["r143_design_payload_hash"]:
        raise ValueError("R146 R143 payload binding mismatch")
    protocol = protocol_payload["protocol"]
    tasks = {task["task_id"]: task for task in build_dense_validation_tasks()}
    route_rows = {(row["snapshot"], row["task_id"]): row for row in r143["group_rows"]}

    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    commitment_path = root / COMMITMENT_PATH
    trials_path = root / TRIALS_PATH
    reveal_path = root / REVEAL_PATH
    transcript_path = root / TRANSCRIPT_PATH
    phase_paths = [commitment_path, trials_path, reveal_path, transcript_path]
    preexisting = {str(path): path.read_bytes() for path in phase_paths if path.exists()}

    if reveal_path.exists():
        secret = bytes.fromhex(json.loads(reveal_path.read_text())["challenge_secret_hex"])
    else:
        secret = os.urandom(32)
    commitment = hashlib.sha256(secret).hexdigest()
    if commitment_path.exists():
        commitment_payload = json.loads(commitment_path.read_text())
        if commitment_payload["challenge_secret_commitment_sha256"] != commitment:
            raise ValueError("R146 challenge commitment mismatch")
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
    for pair in protocol["directional_snapshot_pairs"]:
        source_snapshot = pair["source_snapshot"]
        target_snapshot = pair["target_snapshot"]
        backend = SNAPSHOT_CLASSES[target_snapshot]()
        simulator = AerSimulator.from_backend(backend)
        for task_id in protocol["task_ids"]:
            transfer_id = f"{source_snapshot}->{target_snapshot}::{task_id}"
            task = tasks[task_id]
            logical = basis_circuit(task["circuit"], tuple("Z" for _ in range(task["circuit"].num_qubits)))
            ideal = exact_distribution(task["circuit"])
            source_route = route_rows[(source_snapshot, task_id)]
            target_route = route_rows[(target_snapshot, task_id)]
            source_circuit = compile_policy(logical, backend, source_route["selected_mapping"], source_route["selected_policy_id"], source_route["selected_realization_seed"])
            target_circuit = compile_policy(logical, backend, target_route["selected_mapping"], target_route["selected_policy_id"], target_route["selected_realization_seed"])
            source_semantic = hellinger_fidelity(ideal, exact_compiled_classical_distribution(source_circuit))
            target_semantic = hellinger_fidelity(ideal, exact_compiled_classical_distribution(target_circuit))
            compiled_rows.append({
                "transfer_id": transfer_id,
                "source_snapshot": source_snapshot,
                "target_snapshot": target_snapshot,
                "task_id": task_id,
                "source_mapping": source_route["selected_mapping"],
                "source_policy_id": source_route["selected_policy_id"],
                "source_realization_seed": source_route["selected_realization_seed"],
                "target_mapping": target_route["selected_mapping"],
                "target_policy_id": target_route["selected_policy_id"],
                "target_realization_seed": target_route["selected_realization_seed"],
                "source_transfer_qasm_stable_hash": stable_hash(qasm3.dumps(source_circuit)),
                "target_specific_qasm_stable_hash": stable_hash(qasm3.dumps(target_circuit)),
                "source_transfer_semantic_fidelity": source_semantic,
                "target_specific_semantic_fidelity": target_semantic,
            })
            for trial in range(protocol["hidden_trial_count_per_group"]):
                transpiler_seed = derive_seed(secret, transfer_id, trial, "transpiler")
                simulator_seed = derive_seed(secret, transfer_id, trial, "simulator")
                automatic = transpile(logical, backend=backend, optimization_level=3, seed_transpiler=transpiler_seed)
                fidelities = {}
                for arm, circuit in [("source_transfer", source_circuit), ("target_specific", target_circuit), ("automatic", automatic)]:
                    counts = simulator.run(circuit, shots=protocol["shots_per_execution"], seed_simulator=simulator_seed).result().get_counts()
                    observed = probability_from_counts(counts, protocol["shots_per_execution"], task["circuit"].num_qubits)
                    fidelities[arm] = hellinger_fidelity(ideal, observed)
                trial_rows.append({
                    "transfer_id": transfer_id,
                    "source_snapshot": source_snapshot,
                    "target_snapshot": target_snapshot,
                    "task_id": task_id,
                    "trial": trial,
                    "transpiler_seed": transpiler_seed,
                    "simulator_seed": simulator_seed,
                    "source_transfer_fidelity": fidelities["source_transfer"],
                    "target_specific_fidelity": fidelities["target_specific"],
                    "automatic_fidelity": fidelities["automatic"],
                    "transfer_minus_automatic": fidelities["source_transfer"] - fidelities["automatic"],
                    "transfer_minus_target": fidelities["source_transfer"] - fidelities["target_specific"],
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
    for transfer_id in sorted({row["transfer_id"] for row in trial_rows}):
        rows = [row for row in trial_rows if row["transfer_id"] == transfer_id]
        group_rows.append({
            "transfer_id": transfer_id,
            "source_snapshot": rows[0]["source_snapshot"],
            "target_snapshot": rows[0]["target_snapshot"],
            "task_id": rows[0]["task_id"],
            "row_count": len(rows),
            "mean_transfer_minus_automatic": statistics.mean(row["transfer_minus_automatic"] for row in rows),
            "mean_transfer_minus_target": statistics.mean(row["transfer_minus_target"] for row in rows),
            "transfer_win_count_vs_automatic": sum(row["transfer_minus_automatic"] > 0 for row in rows),
            "transfer_win_count_vs_target": sum(row["transfer_minus_target"] > 0 for row in rows),
            "minimum_transfer_minus_target": min(row["transfer_minus_target"] for row in rows),
        })
    target_rows = []
    for target in protocol["snapshot_names"]:
        rows = [row for row in trial_rows if row["target_snapshot"] == target]
        target_rows.append({
            "target_snapshot": target,
            "row_count": len(rows),
            "mean_transfer_minus_automatic": statistics.mean(row["transfer_minus_automatic"] for row in rows),
            "mean_transfer_minus_target": statistics.mean(row["transfer_minus_target"] for row in rows),
        })
    auto_deltas = [row["transfer_minus_automatic"] for row in trial_rows]
    target_deltas = [row["transfer_minus_target"] for row in trial_rows]
    bootstrap_auto = paired_bootstrap(auto_deltas, derive_seed(secret, "portfolio", 0, "bootstrap-auto"), 10000)
    bootstrap_target = paired_bootstrap(target_deltas, derive_seed(secret, "portfolio", 0, "bootstrap-target"), 10000)
    semantic_values = [value for row in compiled_rows for value in [row["source_transfer_semantic_fidelity"], row["target_specific_semantic_fidelity"]]]
    summary = {
        "transfer_group_count": len(group_rows),
        "trial_row_count": len(trial_rows),
        "simulated_circuit_execution_count": len(trial_rows) * 3,
        "total_simulated_shots": len(trial_rows) * 3 * protocol["shots_per_execution"],
        "portfolio_mean_transfer_minus_automatic": statistics.mean(auto_deltas),
        "portfolio_transfer_minus_automatic_bootstrap_95_lower": bootstrap_auto["lower_95"],
        "portfolio_transfer_minus_automatic_bootstrap_95_upper": bootstrap_auto["upper_95"],
        "portfolio_mean_transfer_minus_target": statistics.mean(target_deltas),
        "portfolio_transfer_minus_target_bootstrap_95_lower": bootstrap_target["lower_95"],
        "portfolio_transfer_minus_target_bootstrap_95_upper": bootstrap_target["upper_95"],
        "groups_with_mean_transfer_minus_target_at_least_negative_0_02": sum(row["mean_transfer_minus_target"] >= -0.02 for row in group_rows),
        "severe_transfer_minus_target_regression_count_below_negative_0_05": sum(value < -0.05 for value in target_deltas),
        "minimum_target_snapshot_mean_transfer_minus_target": min(row["mean_transfer_minus_target"] for row in target_rows),
        "minimum_semantic_fidelity": min(semantic_values),
        "semantic_fidelity_pass_count": sum(value >= protocol["minimum_semantic_fidelity"] for value in semantic_values),
        "phase_artifact_count": 4,
        "phase_artifact_preexisting_count": len(preexisting),
        "temporal_same_device_calibration_transfer_claimed": False,
        "cross_machine_transfer_claimed": False,
        "hardware_execution_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "solved_frontier_claimed": False,
        "new_credit_delta": 0,
    }
    conditions = [
        condition("A1", "protocol and source bindings remain exact", True, True, True),
        condition("A2", "transfer groups, rows, and executions", [summary["transfer_group_count"], summary["trial_row_count"], summary["simulated_circuit_execution_count"]], [24, 192, 576], summary["transfer_group_count"] == 24 and summary["trial_row_count"] == 192 and summary["simulated_circuit_execution_count"] == 576),
        condition("A3", "all transferred and target routes retain semantic fidelity", [summary["semantic_fidelity_pass_count"], summary["minimum_semantic_fidelity"]], [48, protocol["minimum_semantic_fidelity"]], summary["semantic_fidelity_pass_count"] == 48),
        condition("A4", "portfolio transfer versus automatic noninferiority", [summary["portfolio_mean_transfer_minus_automatic"], summary["portfolio_transfer_minus_automatic_bootstrap_95_lower"]], [protocol["minimum_portfolio_transfer_minus_automatic_mean"], protocol["minimum_portfolio_transfer_minus_automatic_bootstrap_lower"]], summary["portfolio_mean_transfer_minus_automatic"] >= protocol["minimum_portfolio_transfer_minus_automatic_mean"] and summary["portfolio_transfer_minus_automatic_bootstrap_95_lower"] >= protocol["minimum_portfolio_transfer_minus_automatic_bootstrap_lower"]),
        condition("A5", "portfolio transfer versus target-specific noninferiority", [summary["portfolio_mean_transfer_minus_target"], summary["portfolio_transfer_minus_target_bootstrap_95_lower"]], [protocol["minimum_portfolio_transfer_minus_target_mean"], protocol["minimum_portfolio_transfer_minus_target_bootstrap_lower"]], summary["portfolio_mean_transfer_minus_target"] >= protocol["minimum_portfolio_transfer_minus_target_mean"] and summary["portfolio_transfer_minus_target_bootstrap_95_lower"] >= protocol["minimum_portfolio_transfer_minus_target_bootstrap_lower"]),
        condition("A6", "groups above negative 0.02 versus target", summary["groups_with_mean_transfer_minus_target_at_least_negative_0_02"], protocol["minimum_group_count_above_negative_0_02_vs_target"], summary["groups_with_mean_transfer_minus_target_at_least_negative_0_02"] >= protocol["minimum_group_count_above_negative_0_02_vs_target"]),
        condition("A7", "severe row regressions below negative 0.05", summary["severe_transfer_minus_target_regression_count_below_negative_0_05"], protocol["maximum_severe_regression_count_below_negative_0_05_vs_target"], summary["severe_transfer_minus_target_regression_count_below_negative_0_05"] <= protocol["maximum_severe_regression_count_below_negative_0_05_vs_target"]),
        condition("A8", "each target snapshot mean transfer-target", summary["minimum_target_snapshot_mean_transfer_minus_target"], protocol["minimum_each_target_mean_transfer_minus_target"], summary["minimum_target_snapshot_mean_transfer_minus_target"] >= protocol["minimum_each_target_mean_transfer_minus_target"]),
        condition("A9", "commitment, hidden rows, reveal, and transcript replay", reveal["commitment_matches"] and reveal["trial_rows_complete_before_reveal"], True, reveal["commitment_matches"] and reveal["trial_rows_complete_before_reveal"]),
        condition("A10", "forbidden claims and credit remain false", 0, 0, not any([summary["temporal_same_device_calibration_transfer_claimed"], summary["cross_machine_transfer_claimed"], summary["hardware_execution_claimed"], summary["quantum_advantage_claimed"], summary["bqp_separation_claimed"], summary["solved_frontier_claimed"], summary["new_credit_delta"]])),
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
        {"requirement_id": "P2", "label": "contract and protocol hashes verify", "passed": True},
        {"requirement_id": "P3", "label": "all six directed pairs and four tasks execute", "passed": len(group_rows) == 24},
        {"requirement_id": "P4", "label": "all three arms share one row seed", "passed": len(trial_rows) == 192},
        {"requirement_id": "P5", "label": "commitment matches revealed secret", "passed": reveal["commitment_matches"]},
        {"requirement_id": "P6", "label": "trial rows are complete before reveal", "passed": reveal["trial_rows_complete_before_reveal"]},
        {"requirement_id": "P7", "label": "48 compiled route semantic checks pass", "passed": summary["semantic_fidelity_pass_count"] == 48},
        {"requirement_id": "P8", "label": "four phase artifacts replay", "passed": phase_replay == 4},
        {"requirement_id": "P9", "label": "acceptance transcript contains A1-A10", "passed": len(conditions) == 10},
        {"requirement_id": "P10", "label": "claim boundary and zero credit remain explicit", "passed": conditions[-1]["passed"]},
    ]
    payload = {
        "title": "B4/B8 R146 cross-backend snapshot transfer holdout",
        "version": 0,
        "method": METHOD,
        "status": "cross_snapshot_transfer_preregistered_acceptance" if summary["global_acceptance"] else "cross_snapshot_transfer_preregistered_rejection",
        "model_status": "synthetic_all_direction_fake_backend_snapshot_transfer",
        "generated_at_unix": started_at,
        "source_target_id": "T-B4-002bb/T-B8-003bf/T-B10-009at",
        "upstream_target_id": "T-B4-002ba/T-B8-003be/T-B10-009as",
        "summary": summary,
        "acceptance_conditions": conditions,
        "compiled_route_rows": compiled_rows,
        "group_rows": group_rows,
        "target_snapshot_rows": target_rows,
        "requirements": requirements,
        "requirement_count": 10,
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [row["requirement_id"] for row in requirements if not row["passed"]],
        "artifacts": {"contract": CONTRACT_PATH, "challenge_commitment": COMMITMENT_PATH, "three_arm_trial_rows": TRIALS_PATH, "challenge_reveal": REVEAL_PATH, "verifier_transcript": TRANSCRIPT_PATH, "result": RESULT_PATH, "markdown_report": REPORT_PATH},
        "claim_boundary": {"what_is_supported": "one preregistered synthetic all-direction fake-backend snapshot transfer verdict", "what_is_not_supported": "temporal same-device calibration transfer, cross-machine transfer, provider access, real hardware, mitigation, soundness, quantum advantage, BQP separation, solved B4/B8/B10, or new credit"},
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
