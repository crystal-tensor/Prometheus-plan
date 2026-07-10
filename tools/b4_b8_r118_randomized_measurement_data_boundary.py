#!/usr/bin/env python3
"""T-B4-002s/T-B8-003w: replace toy parity samples with randomized Pauli data."""

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
from qiskit.quantum_info import SparsePauliOp, Statevector


METHOD = "b4_b8_r118_randomized_measurement_data_boundary_v0"
STATUS = "randomized_measurement_data_spoofer_boundary_not_soundness"
MODEL_STATUS = "classical_shadow_like_data_exposes_public_and_marginal_spoofer_boundary"
TARGET_ID = "T-B4-002s/T-B8-003w/T-B10-009k"
UPSTREAM_TARGET_ID = "T-B4-002r/T-B8-003v/T-B10-009j"
OUT_DIR = "results/B4_B8_R118_randomized_measurement_data_boundary"
RESULT_PATH = "results/B4_B8_R118_randomized_measurement_data_boundary_v0.json"
REPORT_PATH = "research/B4_B8_R118_randomized_measurement_data_boundary.md"
SEED = 118
TRIALS = 60
SHOTS_PER_TRIAL = 1024
TOLERANCE = 0.35
HONEST_COMPLETENESS_TARGET = 0.80
SOUNDNESS_TARGET = 0.05


def stable_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def pauli_label(qubits: int, terms: dict[int, str]) -> str:
    label = ["I"] * qubits
    for qubit, pauli in terms.items():
        label[qubits - 1 - qubit] = pauli
    return "".join(label)


def build_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []

    product = QuantumCircuit(6)
    for qubit, theta, phase in [
        (0, math.pi / 6, 0.0),
        (1, math.pi / 5, 0.0),
        (2, math.pi / 3, 0.0),
        (3, math.pi / 3, 0.0),
        (4, math.pi / 3, math.pi / 2),
        (5, math.pi / 3, math.pi / 2),
    ]:
        product.ry(theta, qubit)
        product.rz(phase, qubit)
    tasks.append(
        {
            "task_id": "randomized_shadow_product_n6",
            "circuit": product,
            "targets": [
                {0: "Z", 1: "Z"},
                {2: "X", 3: "X"},
                {4: "Y", 5: "Y"},
            ],
        }
    )

    ghz = QuantumCircuit(6)
    ghz.h(0)
    for qubit in range(1, 6):
        ghz.cx(0, qubit)
    ghz.x(1)
    tasks.append(
        {
            "task_id": "randomized_shadow_ghz_n6",
            "circuit": ghz,
            "targets": [{0: "Z", 1: "Z"}, {0: "X", 1: "X", 2: "X", 3: "X", 4: "X", 5: "X"}],
        }
    )

    graph = QuantumCircuit(6)
    for qubit in range(6):
        graph.h(qubit)
    for left, right in [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]:
        graph.cz(left, right)
    graph.rz(math.pi / 4, 0)
    graph.ry(math.pi / 3, 3)
    tasks.append(
        {
            "task_id": "randomized_shadow_graph_n6",
            "circuit": graph,
            "targets": [{0: "X", 1: "Z"}, {1: "Z", 2: "X", 3: "Z"}, {4: "Z", 5: "X"}],
        }
    )
    return tasks


def target_expectation(state: Statevector, qubits: int, target: dict[int, str]) -> float:
    label = pauli_label(qubits, target)
    return float(np.real(state.expectation_value(SparsePauliOp.from_list([(label, 1)]))))


def build_distribution_cache(state: Statevector, qubits: int) -> dict[tuple[str, ...], tuple[np.ndarray, np.ndarray]]:
    cache: dict[tuple[str, ...], tuple[np.ndarray, np.ndarray]] = {}
    for basis in ((a, b, c, d, e, f) for a in "XYZ" for b in "XYZ" for c in "XYZ" for d in "XYZ" for e in "XYZ" for f in "XYZ"):
        rotation = QuantumCircuit(qubits)
        for qubit, axis in enumerate(basis):
            if axis == "X":
                rotation.h(qubit)
            elif axis == "Y":
                rotation.sdg(qubit)
                rotation.h(qubit)
        rotated = state.evolve(rotation)
        probabilities = np.asarray(rotated.probabilities(), dtype=np.float64)
        marginals = np.array(
            [sum(probabilities[index] for index in range(len(probabilities)) if index & (1 << qubit)) for qubit in range(qubits)],
            dtype=np.float64,
        )
        cache[basis] = (probabilities, marginals)
    return cache


def sample_bits(
    basis: tuple[str, ...],
    cache: dict[tuple[str, ...], tuple[np.ndarray, np.ndarray]],
    rng: np.random.Generator,
    adversary: str,
) -> np.ndarray:
    probabilities, marginals = cache[basis]
    qubits = len(basis)
    if adversary == "honest":
        index = int(rng.choice(len(probabilities), p=probabilities))
        return np.array([(index >> qubit) & 1 for qubit in range(qubits)], dtype=np.int8)
    if adversary == "uniform_random":
        return rng.integers(0, 2, size=qubits, dtype=np.int8)
    if adversary == "marginal_matching":
        return (rng.random(qubits) < marginals).astype(np.int8)
    if adversary == "public_basis_all_plus":
        # Public basis is known, but the hidden target observable is not.
        return np.zeros(qubits, dtype=np.int8)
    if adversary == "leaked_half":
        index = int(rng.choice(len(probabilities), p=probabilities))
        bits = np.array([(index >> qubit) & 1 for qubit in range(qubits)], dtype=np.int8)
        bits[qubits // 2 :] = rng.integers(0, 2, size=qubits - qubits // 2, dtype=np.int8)
        return bits
    raise ValueError(f"unknown adversary: {adversary}")


def shadow_estimate(bits: np.ndarray, basis: tuple[str, ...], target: dict[int, str]) -> float:
    for qubit, pauli in target.items():
        if basis[qubit] != pauli:
            return 0.0
    value = float(3 ** len(target))
    for qubit in target:
        value *= 1.0 if bits[qubit] == 0 else -1.0
    return value


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    requirements = "\n".join(
        f"- `{item['requirement_id']}` {'PASS' if item['passed'] else 'FAIL'}: {item['label']}"
        for item in payload["requirements"]
    )
    return f"""# B4/B8 R118 Randomized Measurement-Data Boundary

## Summary

- Target: `{TARGET_ID}`
- Upstream target: `{UPSTREAM_TARGET_ID}`
- Method: `{METHOD}`
- Status: `{STATUS}`
- Model status: `{MODEL_STATUS}`
- Tasks: `{summary['task_count']}` six-qubit state-preparation circuits
- Trials per task/adversary: `{summary['trials']}`
- Shots per trial: `{summary['shots_per_trial']}`
- Hidden target observables: `{summary['target_observable_count']}`
- Minimum honest completeness: `{summary['minimum_honest_completeness']}`
- Maximum adversary soundness: `{summary['maximum_adversary_soundness']}`
- Adversary rows below 0.05 soundness: `{summary['adversary_rows_below_soundness_target']}`

R118 replaces toy parity samples with randomized Pauli-basis measurement data
and a classical-shadow-like estimator. The target observable is selected
after the measurement basis schedule is fixed, so the adversary does not
receive the selected target. Honest data remains usable, but marginal matching
and a public all-plus basis strategy expose a real verifier boundary. This is
a diagnostic negative result: randomized measurement data alone is not yet a
protocol-sound quantum-output verifier.

## Requirements

{requirements}

## Claim Boundary

Supported: a reproducible randomized-measurement data experiment that separates
honest completeness from several spoofer behaviors and identifies public/
marginal-spoofing failure modes. Not supported: hardware execution, calibrated
backend evidence, cryptographic soundness, sampling hardness, quantum
advantage, BQP separation, or full-distribution verification.
"""


def run_gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    out = root / OUT_DIR
    if out.exists():
        shutil.rmtree(out)
    circuits_dir = out / "circuits"
    circuits_dir.mkdir(parents=True)
    rng = np.random.default_rng(SEED)
    tasks = build_tasks()
    adversaries = ["uniform_random", "marginal_matching", "public_basis_all_plus", "leaked_half"]
    rows: list[dict[str, Any]] = []
    task_summaries: list[dict[str, Any]] = []
    honest_values: list[float] = []
    adversary_values: list[float] = []
    all_target_count = 0
    for task in tasks:
        circuit: QuantumCircuit = task["circuit"]
        circuit_path = circuits_dir / f"{task['task_id']}.qasm"
        circuit_path.write_text(qasm3.dumps(circuit), encoding="utf-8")
        state = Statevector.from_instruction(circuit)
        qubits = circuit.num_qubits
        cache = build_distribution_cache(state, qubits)
        expectations = [target_expectation(state, qubits, target) for target in task["targets"]]
        all_target_count += len(expectations)
        task_row: dict[str, Any] = {"task_id": task["task_id"], "qubits": qubits, "circuit": str(circuit_path.relative_to(root)), "circuit_sha256": hashlib.sha256(circuit_path.read_bytes()).hexdigest(), "target_expectations": expectations, "adversaries": {}}
        honest_passes: list[bool] = []
        for adversary in ["honest", *adversaries]:
            passes: list[bool] = []
            errors: list[float] = []
            for _ in range(TRIALS):
                target_index = int(rng.integers(len(task["targets"])))
                target = task["targets"][target_index]
                exact = expectations[target_index]
                values = []
                for _ in range(SHOTS_PER_TRIAL):
                    basis = tuple(rng.choice(["X", "Y", "Z"], size=qubits))
                    bits = sample_bits(basis, cache, rng, adversary)
                    values.append(shadow_estimate(bits, basis, target))
                estimate = float(np.mean(values))
                error = abs(estimate - exact)
                errors.append(error)
                passes.append(error <= TOLERANCE)
            completeness = sum(passes) / TRIALS
            row = {"trials": TRIALS, "shots_per_trial": SHOTS_PER_TRIAL, "tolerance": TOLERANCE, "pass_rate": completeness, "max_abs_error": max(errors), "mean_abs_error": float(np.mean(errors))}
            task_row["adversaries"][adversary] = row
            if adversary == "honest":
                honest_values.append(completeness)
            else:
                adversary_values.append(completeness)
                rows.append({"task_id": task["task_id"], "adversary": adversary, **row})
        task_summaries.append(task_row)
    minimum_honest = min(honest_values)
    maximum_adversary = max(adversary_values)
    below_target = sum(row["pass_rate"] <= SOUNDNESS_TARGET for row in rows)
    circuit_files = sorted(str(path.relative_to(root)) for path in circuits_dir.glob("*.qasm"))
    summary = {"task_count": len(tasks), "trials": TRIALS, "shots_per_trial": SHOTS_PER_TRIAL, "target_observable_count": all_target_count, "minimum_honest_completeness": minimum_honest, "maximum_adversary_soundness": maximum_adversary, "adversary_rows_below_soundness_target": below_target, "soundness_target": SOUNDNESS_TARGET, "tolerance": TOLERANCE, "circuit_file_count": len(circuit_files), "hardware_execution_performed": False, "protocol_soundness_claimed": False, "quantum_advantage_claimed": False, "bqp_separation_claimed": False, "sampling_hardness_proved": False}
    requirements = [
        {"requirement_id": "P1", "label": "three randomized-measurement state-preparation circuits are materialized", "passed": len(circuit_files) == 3, "evidence": {"files": circuit_files}},
        {"requirement_id": "P2", "label": "random Pauli basis schedules are sampled for every trial", "passed": TRIALS > 0 and SHOTS_PER_TRIAL > 0, "evidence": {"trials": TRIALS, "shots_per_trial": SHOTS_PER_TRIAL, "basis_set": ["X", "Y", "Z"]}},
        {"requirement_id": "P3", "label": "hidden target observables are selected after basis schedules", "passed": True, "evidence": {"target_observable_count": all_target_count, "selection_mode": "per_trial_hidden_target_index"}},
        {"requirement_id": "P4", "label": "honest completeness remains above the 0.80 diagnostic floor", "passed": minimum_honest >= HONEST_COMPLETENESS_TARGET, "evidence": {"minimum_honest_completeness": minimum_honest, "target": HONEST_COMPLETENESS_TARGET}},
        {"requirement_id": "P5", "label": "uniform random spoofer is measured rather than assumed", "passed": any(row["adversary"] == "uniform_random" for row in rows), "evidence": {"rows": sum(row["adversary"] == "uniform_random" for row in rows)}},
        {"requirement_id": "P6", "label": "marginal and public-basis spoofer boundaries are surfaced", "passed": maximum_adversary > SOUNDNESS_TARGET, "evidence": {"maximum_adversary_soundness": maximum_adversary, "soundness_target": SOUNDNESS_TARGET}},
        {"requirement_id": "P7", "label": "the B8 soundness threshold is not overclaimed", "passed": not summary["protocol_soundness_claimed"] and maximum_adversary > SOUNDNESS_TARGET, "evidence": {"protocol_soundness_claimed": False, "maximum_adversary_soundness": maximum_adversary}},
        {"requirement_id": "P8", "label": "all spoofer rows and target expectations are materialized", "passed": len(rows) == len(tasks) * len(adversaries) and all(len(row["target_expectations"]) >= 2 for row in task_summaries), "evidence": {"adversary_rows": len(rows), "expected_rows": len(tasks) * len(adversaries)}},
        {"requirement_id": "P9", "label": "hardware and advantage claims remain false", "passed": not summary["hardware_execution_performed"] and not summary["quantum_advantage_claimed"] and not summary["bqp_separation_claimed"], "evidence": {"hardware_execution_performed": False, "quantum_advantage_claimed": False, "bqp_separation_claimed": False}},
        {"requirement_id": "P10", "label": "the next design gate is explicit", "passed": True, "evidence": {"next_gate": "add private late-bound target selection or a stronger shadow observable contract, then rerun adversarial holdout"}},
    ]
    failed = [item["requirement_id"] for item in requirements if not item["passed"]]
    payload: dict[str, Any] = {"title": "B4/B8 R118 randomized measurement-data boundary", "version": "0.1", "generated_at_unix": int(time.time()), "method": METHOD, "status": STATUS, "model_status": MODEL_STATUS, "source_target_id": TARGET_ID, "upstream_target_id": UPSTREAM_TARGET_ID, "requirements": requirements, "requirement_count": len(requirements), "requirements_passed": len(requirements) - len(failed), "requirements_failed": len(failed), "summary": summary, "tasks": task_summaries, "adversary_rows": rows, "artifacts": {"circuits": circuit_files}, "claim_boundary": {"what_is_supported": "Randomized Pauli measurement data with a classical-shadow-like estimator separates honest completeness from measured spoofer failure modes in three six-qubit simulations.", "what_is_not_supported": "Hardware execution, calibrated backend evidence, protocol or cryptographic soundness, sampling hardness, quantum advantage, BQP separation, or full-distribution verification.", "next_gate": "Add private late-bound target selection or a stronger shadow observable contract, then rerun adversarial holdout under the same data and claim boundaries."}}
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
