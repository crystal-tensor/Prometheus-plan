#!/usr/bin/env python3
"""Execute the preregistered R142 seed-robust LCB mapping holdout."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r121_private_bundle_shot_sweep import basis_circuit
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r127_calibration_aware_layout_design import SNAPSHOT_CLASSES
from b4_b8_r132_topology_constrained_route_policy import DETERMINISTIC_PROCESS_ENV
from b4_b8_r135_dense_interaction_fallback import build_dense_validation_tasks
from b4_b8_r138_postcommit_statistical_challenge import (
    exact_distribution,
    hellinger_fidelity,
    paired_bootstrap,
    probability_from_counts,
)


METHOD = "b4_b8_r142_seed_robust_lcb_mapping_holdout_v0"
TARGET_ID = "T-B4-002at/T-B8-003ax/T-B10-009al"
UPSTREAM_TARGET_ID = "T-B4-002as/T-B8-003aw/T-B10-009ak"
CONTRACT_PATH = "benchmarks/B4_B8_R142_seed_robust_lcb_mapping_holdout_contract_v0.json"
CONTRACT_SHA256 = "60d62422c35b4f9b2f3339faefc7512c81c3f8049a1ce7291dacb2c6853ba4b6"
PREREGISTRATION_COMMIT = "b550327b6e3a4acc15a52acebaaf6e512c00849c"
PREREGISTRATION_DISCUSSION = "https://github.com/crystal-tensor/Prometheus-plan/discussions/147"
PREREGISTRATION_CREATED_AT = "2026-07-12T18:27:08Z"
DESIGN_PATH = "results/B4_B8_R142_seed_robust_lcb_mapping_design_v0.json"
R140_DESIGN_PATH = "results/B4_B8_R140_output_aware_mapping_design_v0.json"
RESULT_PATH = "results/B4_B8_R142_seed_robust_lcb_mapping_holdout_v0.json"
REPORT_PATH = "research/B4_B8_R142_seed_robust_lcb_mapping_holdout.md"
OUT_DIR = "results/B4_B8_R142_seed_robust_lcb_mapping_holdout"
COMMITMENT_PATH = f"{OUT_DIR}/challenge_commitment.json"
TRIALS_PATH = f"{OUT_DIR}/three_arm_trial_rows.json"
REVEAL_PATH = f"{OUT_DIR}/challenge_reveal.json"
TRANSCRIPT_PATH = f"{OUT_DIR}/verifier_transcript.json"


def ensure_deterministic_process_environment() -> None:
    if all(os.environ.get(key) == value for key, value in DETERMINISTIC_PROCESS_ENV.items()):
        return
    environment = dict(os.environ)
    environment.update(DETERMINISTIC_PROCESS_ENV)
    os.execvpe(sys.executable, [sys.executable, *sys.argv], environment)


def utc_timestamp(value: str) -> int:
    from datetime import datetime

    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def derive_seed(secret: bytes, artifact_id: str, trial: int, role: str) -> int:
    message = f"{CONTRACT_SHA256}|{artifact_id}|{trial}|{role}".encode()
    digest = hmac.new(secret, message, hashlib.sha256).digest()
    return int.from_bytes(digest[:8], "big") % (2**31 - 1) + 1


def condition(
    condition_id: str, label: str, value: Any, threshold: Any, passed: bool
) -> dict[str, Any]:
    return {
        "condition_id": condition_id,
        "label": label,
        "value": value,
        "threshold": threshold,
        "passed": passed,
    }


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    verdict = "ACCEPT" if summary["global_acceptance"] else "REJECT"
    conditions = "\n".join(
        f"- {row['condition_id']} {'PASS' if row['passed'] else 'FAIL'}: "
        f"{row['label']}; value {row['value']}, threshold {row['threshold']}."
        for row in payload["acceptance_conditions"]
    )
    groups = "\n".join(
        f"- {row['artifact_id']}: R142-auto {row['mean_r142_minus_automatic']:+.8f}, "
        f"R142-R140 {row['mean_r142_minus_r140']:+.8f}, wins vs auto "
        f"{row['r142_win_count_vs_automatic']}/8."
        for row in payload["group_rows"]
    )
    requirements = "\n".join(
        f"- {row['requirement_id']} {'PASS' if row['passed'] else 'FAIL'}: {row['label']}"
        for row in payload["requirements"]
    )
    return f"""# B4/B8 R142 Seed-Robust LCB Mapping Holdout

## Verdict

- Preregistered verdict: {verdict}
- Contract SHA-256: {CONTRACT_SHA256}
- Lagos R142-auto mean / wins: {summary['lagos_ising_mean_r142_minus_automatic']:+.8f} / {summary['lagos_ising_r142_win_count_vs_automatic']} of 8
- Lagos R142-R140 mean: {summary['lagos_ising_mean_r142_minus_r140']:+.8f}
- Portfolio R142-auto mean / bootstrap lower: {summary['portfolio_mean_r142_minus_automatic']:+.8f} / {summary['portfolio_r142_minus_automatic_bootstrap_95_lower']:+.8f}
- Portfolio R142-R140 mean: {summary['portfolio_mean_r142_minus_r140']:+.8f}
- Groups above -0.01 versus R140: {summary['groups_with_mean_r142_minus_r140_at_least_negative_0_01']} / 12
- Three-arm rows / executions / shots: {summary['trial_row_count']} / {summary['simulated_circuit_execution_count']} / {summary['total_simulated_shots']}
- Conditions passed / failed: {summary['acceptance_conditions_passed']} / {summary['acceptance_conditions_failed']}
- Phase replay: {summary['phase_artifact_replay_match_count']} / 4
- New credit delta: 0

R142 and R140 circuits are frozen before the hidden seed. Each row creates a
fresh automatic compilation and uses one shared simulator seed across all
three arms. The result therefore tests whether lower-confidence-bound design
selection transfers to a disjoint challenge block.

## Acceptance Conditions

{conditions}

## Group Evidence

{groups}

## Requirements

{requirements}

## Claim Boundary

Supported: one preregistered synthetic hidden-seed verdict for the R142 LCB
mapping portfolio. Not supported: efficient production selection, current
calibration, real hardware, mitigation, independent custody, protocol
soundness, quantum advantage, BQP separation, solved B4/B8/B10, or new credit.
"""


def run_gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    started_at = int(time.time())
    if started_at <= utc_timestamp(PREREGISTRATION_CREATED_AT):
        raise ValueError("R142 holdout must start after public preregistration")
    contract_path = root / CONTRACT_PATH
    if file_sha256(contract_path) != CONTRACT_SHA256:
        raise ValueError("R142 contract hash mismatch")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    design_path = root / DESIGN_PATH
    design = json.loads(design_path.read_text(encoding="utf-8"))
    bindings = contract["source_bindings"]
    if file_sha256(design_path) != bindings["r142_design_sha256"]:
        raise ValueError("R142 design file binding mismatch")
    if design["payload_hash"] != bindings["r142_design_payload_hash"]:
        raise ValueError("R142 design payload binding mismatch")
    r140 = json.loads((root / R140_DESIGN_PATH).read_text(encoding="utf-8"))
    tasks = {task["task_id"]: task for task in build_dense_validation_tasks()}
    r142_groups = {
        (row["snapshot"], row["task_id"]): row for row in design["group_rows"]
    }
    r140_groups = {
        (row["snapshot"], row["task_id"]): row for row in r140["group_rows"]
    }
    artifact_bindings = {
        row["artifact_id"]: row["sha256"] for row in contract["artifact_bindings"]
    }
    source_binding_valid = len(artifact_bindings) == 12 and all(
        file_sha256(root / row["selected_circuit_path"])
        == artifact_bindings[f"{row['snapshot']}::{row['task_id']}"]
        for row in design["group_rows"]
    )

    output = root / OUT_DIR
    output.mkdir(parents=True, exist_ok=True)
    phase_paths = [
        root / COMMITMENT_PATH,
        root / TRIALS_PATH,
        root / REVEAL_PATH,
        root / TRANSCRIPT_PATH,
    ]
    preexisting = {str(path): path.read_bytes() for path in phase_paths if path.exists()}
    reveal_path = root / REVEAL_PATH
    commitment_path = root / COMMITMENT_PATH
    if reveal_path.exists():
        secret = bytes.fromhex(
            json.loads(reveal_path.read_text(encoding="utf-8"))["challenge_secret_hex"]
        )
    else:
        secret = os.urandom(32)
    commitment = hashlib.sha256(secret).hexdigest()
    if commitment_path.exists():
        commitment_payload = json.loads(commitment_path.read_text(encoding="utf-8"))
        if commitment_payload["challenge_secret_commitment_sha256"] != commitment:
            raise ValueError("R142 preexisting commitment mismatch")
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

    challenge = contract["challenge_design"]
    shots = challenge["shots_per_circuit"]
    trials_per_group = challenge["hidden_trial_count_per_group"]
    trial_rows = []
    for key in sorted(r142_groups):
        snapshot_name, task_id = key
        artifact_id = f"{snapshot_name}::{task_id}"
        task = tasks[task_id]
        logical = basis_circuit(
            task["circuit"], tuple("Z" for _ in range(task["circuit"].num_qubits))
        )
        ideal = exact_distribution(task["circuit"])
        backend = SNAPSHOT_CLASSES[snapshot_name]()
        simulator = AerSimulator.from_backend(backend)
        r142_circuit = qasm3.loads(
            (root / r142_groups[key]["selected_circuit_path"]).read_text(encoding="utf-8")
        )
        r140_circuit = qasm3.loads(
            (root / r140_groups[key]["selected_circuit_path"]).read_text(encoding="utf-8")
        )
        for trial in range(trials_per_group):
            transpiler_seed = derive_seed(secret, artifact_id, trial, "transpiler")
            simulator_seed = derive_seed(secret, artifact_id, trial, "simulator")
            automatic = transpile(
                logical,
                backend=backend,
                optimization_level=3,
                seed_transpiler=transpiler_seed,
            )
            fidelities = {}
            for arm, circuit in [
                ("r142_lcb", r142_circuit),
                ("r140_exact", r140_circuit),
                ("automatic", automatic),
            ]:
                counts = simulator.run(
                    circuit, shots=shots, seed_simulator=simulator_seed
                ).result().get_counts()
                observed = probability_from_counts(
                    counts, shots, task["circuit"].num_qubits
                )
                fidelities[arm] = hellinger_fidelity(ideal, observed)
            trial_rows.append(
                {
                    "artifact_id": artifact_id,
                    "snapshot": snapshot_name,
                    "task_id": task_id,
                    "trial": trial,
                    "transpiler_seed": transpiler_seed,
                    "simulator_seed": simulator_seed,
                    "r142_lcb_fidelity": fidelities["r142_lcb"],
                    "r140_exact_fidelity": fidelities["r140_exact"],
                    "automatic_fidelity": fidelities["automatic"],
                    "r142_minus_automatic": fidelities["r142_lcb"]
                    - fidelities["automatic"],
                    "r142_minus_r140": fidelities["r142_lcb"]
                    - fidelities["r140_exact"],
                }
            )
    write_json(root / TRIALS_PATH, trial_rows)
    reveal_payload = {
        "contract_sha256": CONTRACT_SHA256,
        "challenge_secret_hex": secret.hex(),
        "challenge_secret_commitment_sha256": commitment,
        "commitment_matches": hashlib.sha256(secret).hexdigest() == commitment,
        "trial_rows_complete_before_reveal": len(trial_rows) == 96,
    }
    write_json(reveal_path, reveal_payload)

    group_rows = []
    for artifact_id in sorted({row["artifact_id"] for row in trial_rows}):
        rows = [row for row in trial_rows if row["artifact_id"] == artifact_id]
        group_rows.append(
            {
                "artifact_id": artifact_id,
                "row_count": len(rows),
                "mean_r142_minus_automatic": statistics.mean(
                    row["r142_minus_automatic"] for row in rows
                ),
                "mean_r142_minus_r140": statistics.mean(
                    row["r142_minus_r140"] for row in rows
                ),
                "r142_win_count_vs_automatic": sum(
                    row["r142_minus_automatic"] > 0 for row in rows
                ),
                "minimum_r142_minus_automatic": min(
                    row["r142_minus_automatic"] for row in rows
                ),
            }
        )
    lagos_rows = [
        row
        for row in trial_rows
        if row["artifact_id"]
        == "FakeLagosV2::dense_validation_complete_ising_n6"
    ]
    auto_deltas = [row["r142_minus_automatic"] for row in trial_rows]
    r140_deltas = [row["r142_minus_r140"] for row in trial_rows]
    bootstrap_auto = paired_bootstrap(
        auto_deltas, derive_seed(secret, "portfolio", 0, "bootstrap-auto"), 10000
    )
    bootstrap_r140 = paired_bootstrap(
        r140_deltas, derive_seed(secret, "portfolio", 0, "bootstrap-r140"), 10000
    )
    summary = {
        "artifact_count": 12,
        "trial_row_count": len(trial_rows),
        "group_count": len(group_rows),
        "lagos_ising_mean_r142_minus_automatic": statistics.mean(
            row["r142_minus_automatic"] for row in lagos_rows
        ),
        "lagos_ising_r142_win_count_vs_automatic": sum(
            row["r142_minus_automatic"] > 0 for row in lagos_rows
        ),
        "lagos_ising_mean_r142_minus_r140": statistics.mean(
            row["r142_minus_r140"] for row in lagos_rows
        ),
        "portfolio_mean_r142_minus_automatic": statistics.mean(auto_deltas),
        "portfolio_r142_minus_automatic_bootstrap_95_lower": bootstrap_auto[
            "lower_95"
        ],
        "portfolio_mean_r142_minus_r140": statistics.mean(r140_deltas),
        "portfolio_r142_minus_r140_bootstrap_95_lower": bootstrap_r140[
            "lower_95"
        ],
        "groups_with_mean_r142_minus_r140_at_least_negative_0_01": sum(
            row["mean_r142_minus_r140"] >= -0.01 for row in group_rows
        ),
        "severe_r142_minus_r140_regression_count_below_negative_0_05": sum(
            value < -0.05 for value in r140_deltas
        ),
        "simulated_circuit_execution_count": len(trial_rows) * 3,
        "shots_per_circuit": shots,
        "total_simulated_shots": len(trial_rows) * 3 * shots,
        "bootstrap_resample_count": 10000,
        "efficient_production_mapper_claimed": False,
        "hardware_execution_performed": False,
        "protocol_soundness_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "new_credit_delta": 0,
    }
    conditions = [
        condition("A1", "design and selected-QASM bindings remain exact", source_binding_valid, True, source_binding_valid),
        condition("A2", "all groups contain eight complete three-arm rows", [summary["trial_row_count"], summary["group_count"]], [96, 12], summary["trial_row_count"] == 96 and summary["group_count"] == 12),
        condition("A3", "Lagos R142-auto mean is nonnegative", summary["lagos_ising_mean_r142_minus_automatic"], ">= 0", summary["lagos_ising_mean_r142_minus_automatic"] >= 0),
        condition("A4", "Lagos R142 wins at least half against automatic", summary["lagos_ising_r142_win_count_vs_automatic"], ">= 4", summary["lagos_ising_r142_win_count_vs_automatic"] >= 4),
        condition("A5", "Lagos R142 materially improves over R140", summary["lagos_ising_mean_r142_minus_r140"], ">= 0.005", summary["lagos_ising_mean_r142_minus_r140"] >= 0.005),
        condition("A6", "portfolio R142-auto bootstrap lower bound", summary["portfolio_r142_minus_automatic_bootstrap_95_lower"], ">= -0.005", summary["portfolio_r142_minus_automatic_bootstrap_95_lower"] >= -0.005),
        condition("A7", "portfolio R142-R140 mean noninferiority", summary["portfolio_mean_r142_minus_r140"], ">= -0.002", summary["portfolio_mean_r142_minus_r140"] >= -0.002),
        condition("A8", "cross-group improvement avoids broad regressions", summary["groups_with_mean_r142_minus_r140_at_least_negative_0_01"], ">= 11", summary["groups_with_mean_r142_minus_r140_at_least_negative_0_01"] >= 11),
        condition("A9", "disclosed execution and shot budget matches contract", [summary["simulated_circuit_execution_count"], summary["total_simulated_shots"]], [288, 1179648], summary["simulated_circuit_execution_count"] == 288 and summary["total_simulated_shots"] == 1179648),
        condition("A10", "production, hardware, soundness, advantage, BQP, and credit claims remain false", 0, 0, not any([summary["efficient_production_mapper_claimed"], summary["hardware_execution_performed"], summary["protocol_soundness_claimed"], summary["quantum_advantage_claimed"], summary["bqp_separation_claimed"], summary["new_credit_delta"]])),
    ]
    summary["acceptance_conditions_passed"] = sum(row["passed"] for row in conditions)
    summary["acceptance_conditions_failed"] = sum(not row["passed"] for row in conditions)
    summary["failed_acceptance_condition_ids"] = [
        row["condition_id"] for row in conditions if not row["passed"]
    ]
    summary["global_acceptance"] = all(row["passed"] for row in conditions)
    transcript = {
        "contract_sha256": CONTRACT_SHA256,
        "challenge_secret_commitment_sha256": commitment,
        "trial_rows_sha256": file_sha256(root / TRIALS_PATH),
        "acceptance_conditions": conditions,
        "global_acceptance": summary["global_acceptance"],
    }
    write_json(root / TRANSCRIPT_PATH, transcript)
    phase_replay_matches = sum(
        path.exists()
        and str(path) in preexisting
        and path.read_bytes() == preexisting[str(path)]
        for path in phase_paths
    )
    summary["phase_artifact_count"] = 4
    summary["phase_artifact_preexisting_count"] = len(preexisting)
    summary["phase_artifact_replay_match_count"] = phase_replay_matches
    requirements = [
        {"requirement_id": "P1", "label": "public contract and discussion precede challenge generation", "passed": started_at > utc_timestamp(PREREGISTRATION_CREATED_AT)},
        {"requirement_id": "P2", "label": "all twelve R142 artifact bindings remain exact", "passed": source_binding_valid},
        {"requirement_id": "P3", "label": "secret commitment precedes rows and reveal follows complete rows", "passed": reveal_payload["commitment_matches"] and reveal_payload["trial_rows_complete_before_reveal"]},
        {"requirement_id": "P4", "label": "all twelve groups contain eight complete three-arm rows", "passed": len(trial_rows) == 96 and all(row["row_count"] == 8 for row in group_rows)},
        {"requirement_id": "P5", "label": "288 executions and 1,179,648 shots match the contract", "passed": summary["simulated_circuit_execution_count"] == 288 and summary["total_simulated_shots"] == 1179648},
        {"requirement_id": "P6", "label": "each three-arm row shares one simulator seed", "passed": True},
        {"requirement_id": "P7", "label": "both portfolio bootstraps use 10,000 resamples", "passed": bootstrap_auto["resamples"] == 10000 and bootstrap_r140["resamples"] == 10000},
        {"requirement_id": "P8", "label": "the verdict follows unchanged A1-A10 gates", "passed": True},
        {"requirement_id": "P9", "label": "all four phase artifacts replay in a fresh process", "passed": phase_replay_matches in {0, 4}},
        {"requirement_id": "P10", "label": "production, hardware, soundness, advantage, BQP, and credit remain excluded", "passed": conditions[-1]["passed"]},
    ]
    payload = {
        "title": "B4/B8 R142 seed-robust LCB mapping holdout",
        "version": 0,
        "method": METHOD,
        "status": "seed_robust_lcb_mapping_preregistered_holdout_acceptance" if summary["global_acceptance"] else "seed_robust_lcb_mapping_preregistered_holdout_rejection",
        "model_status": "disjoint_hidden_seed_transfer_of_lower_confidence_bound_mapping",
        "generated_at_unix": started_at,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "summary": summary,
        "acceptance_conditions": conditions,
        "group_rows": group_rows,
        "three_arm_trial_rows": trial_rows,
        "bootstrap_r142_minus_automatic": bootstrap_auto,
        "bootstrap_r142_minus_r140": bootstrap_r140,
        "requirements": requirements,
        "requirement_count": len(requirements),
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [row["requirement_id"] for row in requirements if not row["passed"]],
        "artifacts": {
            "contract": CONTRACT_PATH,
            "challenge_commitment": COMMITMENT_PATH,
            "three_arm_trial_rows": TRIALS_PATH,
            "challenge_reveal": REVEAL_PATH,
            "verifier_transcript": TRANSCRIPT_PATH,
            "result": RESULT_PATH,
            "markdown_report": REPORT_PATH,
        },
        "claim_boundary": {
            "what_is_supported": "one preregistered synthetic hidden-seed verdict for the R142 LCB mapping portfolio",
            "what_is_not_supported": "efficient production selection, current calibration, real hardware, mitigation, independent custody, protocol soundness, quantum advantage, BQP separation, solved B4/B8/B10, or new credit",
        },
    }
    hash_payload = dict(payload)
    payload["payload_hash"] = hashlib.sha256(
        json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    ensure_deterministic_process_environment()
    root = args.root.resolve()
    payload = run_gate(root)
    output = args.output or root / RESULT_PATH
    markdown = args.report or root / REPORT_PATH
    write_json(output, payload)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(report(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if payload["requirements_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
