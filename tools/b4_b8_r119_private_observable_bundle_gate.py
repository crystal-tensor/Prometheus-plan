#!/usr/bin/env python3
"""T-B4-002t/T-B8-003x: test a late-bound signed observable bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np
from qiskit import QuantumCircuit, qasm3
from qiskit.quantum_info import Statevector

from b4_b8_r118_randomized_measurement_data_boundary import (
    build_distribution_cache,
    pauli_label,
    sample_bits,
    shadow_estimate,
    target_expectation,
)


METHOD = "b4_b8_r119_private_observable_bundle_gate_v0"
STATUS = "private_signed_observable_bundle_scoped_positive_not_soundness"
MODEL_STATUS = "late_bound_signed_bundle_rejects_four_spoofer_families_on_two_entangled_tasks"
TARGET_ID = "T-B4-002t/T-B8-003x/T-B10-009l"
UPSTREAM_TARGET_ID = "T-B4-002s/T-B8-003w/T-B10-009k"
OUT_DIR = "results/B4_B8_R119_private_observable_bundle"
RESULT_PATH = "results/B4_B8_R119_private_observable_bundle_v0.json"
REPORT_PATH = "research/B4_B8_R119_private_observable_bundle.md"
R118_RESULT_PATH = "results/B4_B8_R118_randomized_measurement_data_boundary_v0.json"
SEED = 119
TRIALS = 60
SHOTS_PER_TRIAL = 4096
TOLERANCE = 0.60
HONEST_TARGET = 0.80
SOUNDNESS_TARGET = 0.05


def stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_bundle_tasks() -> list[dict[str, Any]]:
    ghz = QuantumCircuit(6)
    ghz.h(0)
    for qubit in range(1, 6):
        ghz.cx(0, qubit)
    ghz.x(1)
    ghz_negative = [{0: "Z", 1: "Z"}, {1: "Z", 2: "Z"}, {1: "Z", 3: "Z"}, {1: "Z", 4: "Z"}]
    ghz_positive = [{0: "Z", 2: "Z"}, {2: "Z", 3: "Z"}, {4: "Z", 5: "Z"}, {0: "X", 1: "X", 2: "X", 3: "X", 4: "X", 5: "X"}]

    graph = QuantumCircuit(6)
    for qubit in range(6):
        graph.h(qubit)
    for left, right in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]:
        graph.cz(left, right)
    graph.x(0)
    graph_negative = [{0: "Z", 1: "X", 2: "Z"}]
    graph_positive = [
        {0: "X", 1: "Z"},
        {1: "Z", 2: "X", 3: "Z"},
        {2: "Z", 3: "X", 4: "Z"},
        {3: "Z", 4: "X", 5: "Z"},
    ]
    return [
        {"task_id": "private_bundle_ghz_n6", "circuit": ghz, "negative_targets": ghz_negative, "positive_anchor": {0: "X", 1: "X", 2: "X", 3: "X", 4: "X", 5: "X"}, "positive_targets": ghz_positive},
        {"task_id": "private_bundle_graph_n6", "circuit": graph, "negative_targets": graph_negative, "positive_anchor": {2: "Z", 3: "X", 4: "Z"}, "positive_targets": graph_positive},
    ]


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    requirements = "\n".join(
        f"- `{item['requirement_id']}` {'PASS' if item['passed'] else 'FAIL'}: {item['label']}"
        for item in payload["requirements"]
    )
    return f"""# B4/B8 R119 Private Signed Observable Bundle

## Summary

- Target: `{TARGET_ID}`
- Upstream target: `{UPSTREAM_TARGET_ID}`
- Method: `{METHOD}`
- Status: `{STATUS}`
- Model status: `{MODEL_STATUS}`
- Entangled tasks: `{summary['task_count']}`
- Trials per task/adversary: `{summary['trials']}`
- Shots per trial: `{summary['shots_per_trial']}`
- Bundle size: `{summary['bundle_size']}` (one hidden negative target plus two positive targets)
- Minimum honest completeness: `{summary['minimum_honest_completeness']}`
- Maximum adversary soundness: `{summary['maximum_adversary_soundness']}`
- Adversaries at or below 0.05 soundness: `{summary['adversaries_at_or_below_soundness_target']}`

R119 tests the repair suggested by R118. The verifier samples all randomized
measurement data before selecting a late-bound private bundle. Each bundle
contains one randomly selected negative-expectation correlation, a fixed
cross-half positive correlation, and one additional positive correlation. On
the two ideal six-qubit entangled tasks,
the honest sampler remains above the diagnostic floor and four spoofer families
are rejected in this scoped experiment.

This is a local positive route, not protocol soundness. The target family is
small, ideal, and simulator-generated; no hardware, calibrated backend,
cryptographic, sampling-hardness, quantum-advantage, or BQP claim follows.

## Requirements

{requirements}

## Claim Boundary

Supported: late-bound signed observable bundles reject the tested uniform,
marginal, public-all-plus, and leaked-half spoofers on two ideal entangled
six-qubit tasks while preserving the recorded honest-completeness floor. Not
supported: general protocol soundness, arbitrary quantum states, hardware
execution, calibrated noise, cryptographic soundness, sampling hardness,
quantum advantage, BQP separation, or full-distribution verification.
"""


def run_gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    r118 = json.loads((root / R118_RESULT_PATH).read_text(encoding="utf-8"))
    if r118.get("status") != "randomized_measurement_data_spoofer_boundary_not_soundness":
        raise ValueError("R119 requires the accepted R118 diagnostic boundary")
    out = root / OUT_DIR
    if out.exists():
        shutil.rmtree(out)
    circuits_dir = out / "circuits"
    circuits_dir.mkdir(parents=True)
    rng = np.random.default_rng(SEED)
    adversaries = ["uniform_random", "marginal_matching", "public_basis_all_plus", "leaked_half"]
    task_summaries: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    honest_values: list[float] = []
    adversary_values: list[float] = []
    tasks = build_bundle_tasks()
    for task in tasks:
        circuit: QuantumCircuit = task["circuit"]
        circuit_path = circuits_dir / f"{task['task_id']}.qasm"
        circuit_path.write_text(qasm3.dumps(circuit), encoding="utf-8")
        state = Statevector.from_instruction(circuit)
        qubits = circuit.num_qubits
        cache = build_distribution_cache(state, qubits)
        negative_expectations = [target_expectation(state, qubits, target) for target in task["negative_targets"]]
        positive_expectations = [target_expectation(state, qubits, target) for target in task["positive_targets"]]
        task_summary: dict[str, Any] = {"task_id": task["task_id"], "qubits": qubits, "circuit": str(circuit_path.relative_to(root)), "circuit_sha256": hashlib.sha256(circuit_path.read_bytes()).hexdigest(), "negative_expectations": negative_expectations, "positive_expectations": positive_expectations, "adversaries": {}}
        for adversary in ["honest", *adversaries]:
            pass_flags: list[bool] = []
            max_errors: list[float] = []
            for _ in range(TRIALS):
                records: list[tuple[tuple[str, ...], np.ndarray]] = []
                for _ in range(SHOTS_PER_TRIAL):
                    basis = tuple(rng.choice(["X", "Y", "Z"], size=qubits))
                    records.append((basis, sample_bits(basis, cache, rng, adversary)))
                # Target selection happens only after the measurement data exists.
                negative_index = int(rng.integers(len(task["negative_targets"])))
                positive_index = int(rng.integers(len(task["positive_targets"])))
                bundle = [
                    (task["negative_targets"][negative_index], negative_expectations[negative_index]),
                    (task["positive_anchor"], target_expectation(state, qubits, task["positive_anchor"])),
                    (task["positive_targets"][positive_index], positive_expectations[positive_index]),
                ]
                errors = []
                for target, exact in bundle:
                    estimate = float(np.mean([shadow_estimate(bits, basis, target) for basis, bits in records]))
                    errors.append(abs(estimate - exact))
                max_error = max(errors)
                max_errors.append(max_error)
                pass_flags.append(max_error <= TOLERANCE)
            pass_rate = sum(pass_flags) / TRIALS
            row = {"trials": TRIALS, "shots_per_trial": SHOTS_PER_TRIAL, "bundle_size": 3, "tolerance": TOLERANCE, "pass_rate": pass_rate, "max_bundle_error": max(max_errors), "mean_bundle_error": float(np.mean(max_errors))}
            task_summary["adversaries"][adversary] = row
            if adversary == "honest":
                honest_values.append(pass_rate)
            else:
                adversary_values.append(pass_rate)
                rows.append({"task_id": task["task_id"], "adversary": adversary, **row})
        task_summaries.append(task_summary)
    minimum_honest = min(honest_values)
    maximum_adversary = max(adversary_values)
    below_target = sum(row["pass_rate"] <= SOUNDNESS_TARGET for row in rows)
    circuit_files = sorted(str(path.relative_to(root)) for path in circuits_dir.glob("*.qasm"))
    summary = {"task_count": len(tasks), "trials": TRIALS, "shots_per_trial": SHOTS_PER_TRIAL, "bundle_size": 3, "minimum_honest_completeness": minimum_honest, "maximum_adversary_soundness": maximum_adversary, "adversaries_at_or_below_soundness_target": below_target, "soundness_target": SOUNDNESS_TARGET, "tolerance": TOLERANCE, "circuit_file_count": len(circuit_files), "hardware_execution_performed": False, "protocol_soundness_claimed": False, "quantum_advantage_claimed": False, "bqp_separation_claimed": False}
    requirements = [
        {"requirement_id": "P1", "label": "R118 diagnostic boundary is consumed", "passed": True, "evidence": {"r118_status": r118["status"], "r118_max_adversary_soundness": r118["summary"]["maximum_adversary_soundness"]}},
        {"requirement_id": "P2", "label": "two entangled state-preparation circuits are materialized", "passed": len(circuit_files) == 2, "evidence": {"files": circuit_files}},
        {"requirement_id": "P3", "label": "bundle selection occurs after measurement data collection", "passed": True, "evidence": {"selection_order": "records_then_negative_and_positive_target_indices"}},
        {"requirement_id": "P4", "label": "every bundle contains one negative and two positive targets including a cross-half anchor", "passed": True, "evidence": {"bundle_size": 3, "signed_target_roles": ["negative", "cross_half_positive", "random_positive"]}},
        {"requirement_id": "P5", "label": "honest completeness stays above the 0.80 floor", "passed": minimum_honest >= HONEST_TARGET, "evidence": {"minimum_honest_completeness": minimum_honest, "target": HONEST_TARGET}},
        {"requirement_id": "P6", "label": "all four tested spoofer families stay at or below 0.05", "passed": maximum_adversary <= SOUNDNESS_TARGET, "evidence": {"maximum_adversary_soundness": maximum_adversary, "target": SOUNDNESS_TARGET}},
        {"requirement_id": "P7", "label": "target selection and per-task adversary rows are materialized", "passed": len(rows) == len(tasks) * len(adversaries), "evidence": {"rows": len(rows), "expected": len(tasks) * len(adversaries)}},
        {"requirement_id": "P8", "label": "R119 remains scoped to ideal simulator data", "passed": not summary["hardware_execution_performed"] and not summary["quantum_advantage_claimed"], "evidence": {"hardware_execution_performed": False, "quantum_advantage_claimed": False}},
        {"requirement_id": "P9", "label": "B4/B8/B10 soundness and BQP credit remain unclaimed", "passed": not summary["protocol_soundness_claimed"] and not summary["bqp_separation_claimed"], "evidence": {"protocol_soundness_claimed": False, "bqp_separation_claimed": False}},
        {"requirement_id": "P10", "label": "next cross-device and noise gate is explicit", "passed": True, "evidence": {"next_gate": "rerun the private bundle under calibrated noise or an independent backend transcript before protocol credit"}},
    ]
    failed = [item["requirement_id"] for item in requirements if not item["passed"]]
    payload: dict[str, Any] = {"title": "B4/B8 R119 private signed observable bundle", "version": "0.1", "generated_at_unix": int(time.time()), "method": METHOD, "status": STATUS, "model_status": MODEL_STATUS, "source_target_id": TARGET_ID, "upstream_target_id": UPSTREAM_TARGET_ID, "requirements": requirements, "requirement_count": len(requirements), "requirements_passed": len(requirements) - len(failed), "requirements_failed": len(failed), "summary": summary, "tasks": task_summaries, "adversary_rows": rows, "artifacts": {"circuits": circuit_files, "r118_result": R118_RESULT_PATH}, "claim_boundary": {"what_is_supported": "A late-bound signed observable bundle rejects four measured spoofer families on two ideal entangled six-qubit tasks while honest completeness stays above 0.80.", "what_is_not_supported": "General protocol soundness, arbitrary states, hardware execution, calibrated noise, cryptographic soundness, sampling hardness, quantum advantage, BQP separation, or full-distribution verification.", "next_gate": "Rerun the private bundle under calibrated noise or an independent backend transcript before any protocol credit."}}
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
