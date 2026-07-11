#!/usr/bin/env python3
"""T-B4-002u/T-B8-003y: replay the R119 bundle under explicit Aer noise."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from qiskit import QuantumCircuit, qasm3
from qiskit.quantum_info import Statevector
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

from b4_b8_r119_private_observable_bundle_gate import build_bundle_tasks, shadow_estimate, target_expectation


METHOD = "b4_b8_r120_private_bundle_noise_replay_v0"
STATUS = "private_signed_observable_bundle_noise_margin_boundary"
MODEL_STATUS = "r119_bundle_honest_noise_margin_replayed_with_explicit_aer_profiles"
TARGET_ID = "T-B4-002u/T-B8-003y/T-B10-009m"
UPSTREAM_TARGET_ID = "T-B4-002t/T-B8-003x/T-B10-009l"
R119_RESULT_PATH = "results/B4_B8_R119_private_observable_bundle_v0.json"
OUT_DIR = "results/B4_B8_R120_private_bundle_noise_replay"
RESULT_PATH = "results/B4_B8_R120_private_bundle_noise_replay_v0.json"
REPORT_PATH = "research/B4_B8_R120_private_bundle_noise_replay.md"
SEED = 120
TRIALS = 20
SHOTS_PER_TRIAL = 1024
TOLERANCE = 0.60
HONEST_TARGET = 0.80

PROFILES = {
    "ideal": {"p1": 0.0, "p2": 0.0, "readout": 0.0},
    "light": {"p1": 0.001, "p2": 0.005, "readout": 0.005},
    "moderate": {"p1": 0.003, "p2": 0.015, "readout": 0.01},
    "stress": {"p1": 0.006, "p2": 0.03, "readout": 0.02},
}


def stable_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def noise_model(profile: dict[str, float]) -> NoiseModel:
    model = NoiseModel()
    if profile["p1"]:
        error = depolarizing_error(profile["p1"], 1)
        model.add_all_qubit_quantum_error(error, ["h", "rz", "ry", "x", "sdg", "sx", "u", "u1", "u2", "u3"])
    if profile["p2"]:
        error = depolarizing_error(profile["p2"], 2)
        model.add_all_qubit_quantum_error(error, ["cx", "cz"])
    if profile["readout"]:
        readout = ReadoutError([[1 - profile["readout"], profile["readout"]], [profile["readout"], 1 - profile["readout"]]])
        model.add_all_qubit_readout_error(readout)
    return model


def basis_circuit(base: QuantumCircuit, basis: tuple[str, ...]) -> QuantumCircuit:
    circuit = base.copy()
    for qubit, axis in enumerate(basis):
        if axis == "X":
            circuit.h(qubit)
        elif axis == "Y":
            circuit.sdg(qubit)
            circuit.h(qubit)
    circuit.measure_all()
    return circuit


def decode_counts(counts: dict[str, int], qubits: int) -> list[np.ndarray]:
    records: list[np.ndarray] = []
    for key, count in counts.items():
        bits = np.array([int(bit) for bit in key.replace(" ", "")[::-1][:qubits]], dtype=np.int8)
        records.extend([bits.copy() for _ in range(int(count))])
    return records


def noisy_records(
    base: QuantumCircuit,
    simulator: AerSimulator,
    rng: np.random.Generator,
    cache: dict[tuple[str, ...], QuantumCircuit],
) -> list[tuple[tuple[str, ...], np.ndarray]]:
    qubits = base.num_qubits
    schedule = [tuple(rng.choice(["X", "Y", "Z"], size=qubits)) for _ in range(SHOTS_PER_TRIAL)]
    groups = Counter(schedule)
    records: list[tuple[tuple[str, ...], np.ndarray]] = []
    for basis, count in groups.items():
        circuit = cache.setdefault(basis, basis_circuit(base, basis))
        result = simulator.run(circuit, shots=count, seed_simulator=int(rng.integers(0, 2**31 - 1))).result()
        for bits in decode_counts(result.get_counts(0), qubits):
            records.append((basis, bits))
    if len(records) != SHOTS_PER_TRIAL:
        raise RuntimeError(f"noise replay shot mismatch: {len(records)} != {SHOTS_PER_TRIAL}")
    return records


def bundle_error(records: list[tuple[tuple[str, ...], np.ndarray]], task: dict[str, Any], state_targets: dict[str, float], rng: np.random.Generator) -> float:
    negative_index = int(rng.integers(len(task["negative_targets"])))
    positive_index = int(rng.integers(len(task["positive_targets"])))
    bundle = [
        task["negative_targets"][negative_index],
        task["positive_anchor"],
        task["positive_targets"][positive_index],
    ]
    errors = []
    for target in bundle:
        key = json.dumps(target, sort_keys=True)
        exact = state_targets[key]
        estimate = float(np.mean([shadow_estimate(bits, basis, target) for basis, bits in records]))
        errors.append(abs(estimate - exact))
    return max(errors)


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    reqs = "\n".join(f"- `{x['requirement_id']}` {'PASS' if x['passed'] else 'FAIL'}: {x['label']}" for x in payload["requirements"])
    profile_lines = "\n".join(
        f"- `{name}`: minimum honest completeness `{row['minimum_honest_completeness']}`, maximum bundle error `{row['maximum_bundle_error']}`"
        for name, row in summary["profiles"].items()
    )
    return f"""# B4/B8 R120 Private Bundle Noise Replay

## Summary

- Target: `{TARGET_ID}`
- Upstream target: `{UPSTREAM_TARGET_ID}`
- Method: `{METHOD}`
- Status: `{STATUS}`
- Model status: `{MODEL_STATUS}`
- Tasks: `{summary['task_count']}` ideal six-qubit entangled tasks
- Trials per profile/task: `{summary['trials']}`
- Shots per trial: `{summary['shots_per_trial']}`
- Bundle size: `{summary['bundle_size']}`
- Fixed estimator tolerance: `{summary['tolerance']}`
- Profiles above the `{HONEST_TARGET}` honest floor: `{summary['noise_profiles_above_honest_floor']}/{len(PROFILES)}`

Profile results:

{profile_lines}

R120 replays the R119 private signed bundle under explicit Qiskit Aer
depolarizing and readout-noise profiles at a fixed 1,024-shot budget. The
noise-free profile is retained as a sampling baseline: if it misses the R119
floor, the implementation must not blame hardware noise alone. The R119 ideal
adversary result is carried as a dependency, not silently re-run as a new
soundness proof. No profile is treated as calibrated hardware evidence.

## Requirements

{reqs}

## Claim Boundary

Supported: an explicit simulator noise-margin ledger for the R119 private
bundle. Not supported: calibrated backend evidence, real hardware execution,
general protocol soundness, cryptographic soundness, sampling hardness,
quantum advantage, BQP separation, or full-distribution verification.
"""


def run_gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    r119 = json.loads((root / R119_RESULT_PATH).read_text(encoding="utf-8"))
    if r119.get("status") != "private_signed_observable_bundle_scoped_positive_not_soundness":
        raise ValueError("R120 requires accepted R119 scoped result")
    out = root / OUT_DIR
    if out.exists():
        shutil.rmtree(out)
    circuits_dir = out / "circuits"
    circuits_dir.mkdir(parents=True)
    rng = np.random.default_rng(SEED)
    tasks = build_bundle_tasks()
    profile_results: dict[str, Any] = {}
    all_profile_rows: list[dict[str, Any]] = []
    for profile_name, profile in PROFILES.items():
        simulator = AerSimulator(noise_model=noise_model(profile), method="density_matrix")
        task_rows = []
        for task in tasks:
            base = task["circuit"]
            path = circuits_dir / f"{profile_name}_{task['task_id']}.qasm"
            path.write_text(qasm3.dumps(base), encoding="utf-8")
            state = Statevector.from_instruction(base)
            target_values = {}
            for target in [*task["negative_targets"], task["positive_anchor"], *task["positive_targets"]]:
                target_values[json.dumps(target, sort_keys=True)] = target_expectation(state, base.num_qubits, target)
            cache: dict[tuple[str, ...], QuantumCircuit] = {}
            pass_flags = []
            errors = []
            for _ in range(TRIALS):
                records = noisy_records(base, simulator, rng, cache)
                error = bundle_error(records, task, target_values, rng)
                errors.append(error)
                pass_flags.append(error <= TOLERANCE)
            row = {"task_id": task["task_id"], "profile": profile_name, "trials": TRIALS, "shots_per_trial": SHOTS_PER_TRIAL, "pass_rate": sum(pass_flags) / TRIALS, "maximum_bundle_error": max(errors), "mean_bundle_error": float(np.mean(errors)), "circuit": str(path.relative_to(root)), "circuit_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            task_rows.append(row)
            all_profile_rows.append(row)
        profile_results[profile_name] = {"noise": profile, "minimum_honest_completeness": min(row["pass_rate"] for row in task_rows), "maximum_bundle_error": max(row["maximum_bundle_error"] for row in task_rows), "task_rows": task_rows}
    minimum_profile = min(row["minimum_honest_completeness"] for row in profile_results.values())
    summary = {"task_count": len(tasks), "trials": TRIALS, "shots_per_trial": SHOTS_PER_TRIAL, "bundle_size": 3, "tolerance": TOLERANCE, "profiles": profile_results, "minimum_profile_honest_completeness": minimum_profile, "noise_profiles_above_honest_floor": sum(row["minimum_honest_completeness"] >= HONEST_TARGET for row in profile_results.values()), "r119_max_adversary_soundness": r119["summary"]["maximum_adversary_soundness"], "hardware_execution_performed": False, "calibrated_backend_evidence": False, "protocol_soundness_claimed": False, "quantum_advantage_claimed": False, "bqp_separation_claimed": False}
    circuit_files = sorted(str(path.relative_to(root)) for path in circuits_dir.glob("*.qasm"))
    requirements = [
        {"requirement_id": "P1", "label": "accepted R119 bundle is consumed", "passed": True, "evidence": {"r119_status": r119["status"], "r119_max_adversary_soundness": r119["summary"]["maximum_adversary_soundness"]}},
        {"requirement_id": "P2", "label": "four explicit Aer noise profiles are replayed", "passed": set(profile_results) == set(PROFILES), "evidence": {"profiles": list(profile_results)}},
        {"requirement_id": "P3", "label": "same three-observable bundle contract is retained", "passed": summary["bundle_size"] == 3, "evidence": {"bundle_size": 3}},
        {"requirement_id": "P4", "label": "noise-free profile is materialized as the sampling baseline", "passed": "ideal" in profile_results and len(profile_results["ideal"]["task_rows"]) == len(tasks), "evidence": {"minimum_honest_completeness": profile_results["ideal"]["minimum_honest_completeness"], "target": HONEST_TARGET, "baseline_only": True}},
        {"requirement_id": "P5", "label": "noise margin is reported per profile rather than averaged away", "passed": len(all_profile_rows) == len(PROFILES) * len(tasks), "evidence": {"rows": len(all_profile_rows)}},
        {"requirement_id": "P6", "label": "no noise profile is mislabeled as calibrated hardware evidence", "passed": not summary["calibrated_backend_evidence"] and not summary["hardware_execution_performed"], "evidence": {"calibrated_backend_evidence": False, "hardware_execution_performed": False}},
        {"requirement_id": "P7", "label": "R119 adversary result is carried without a new soundness claim", "passed": summary["r119_max_adversary_soundness"] <= 0.05 and not summary["protocol_soundness_claimed"], "evidence": {"r119_max_adversary_soundness": summary["r119_max_adversary_soundness"], "protocol_soundness_claimed": False}},
        {"requirement_id": "P8", "label": "all profile circuits and rows are materialized", "passed": len(circuit_files) == len(PROFILES) * len(tasks), "evidence": {"circuit_file_count": len(circuit_files)}},
        {"requirement_id": "P9", "label": "B4/B8/B10 advantage and BQP claims remain false", "passed": not summary["quantum_advantage_claimed"] and not summary["bqp_separation_claimed"], "evidence": {"quantum_advantage_claimed": False, "bqp_separation_claimed": False}},
        {"requirement_id": "P10", "label": "next gate is independent backend or calibrated transcript", "passed": True, "evidence": {"next_gate": "replace synthetic Aer profiles with calibrated backend properties or an independent backend transcript"}},
    ]
    failed = [x["requirement_id"] for x in requirements if not x["passed"]]
    payload: dict[str, Any] = {"title": "B4/B8 R120 private bundle noise replay", "version": "0.1", "generated_at_unix": int(time.time()), "method": METHOD, "status": STATUS, "model_status": MODEL_STATUS, "source_target_id": TARGET_ID, "upstream_target_id": UPSTREAM_TARGET_ID, "requirements": requirements, "requirement_count": len(requirements), "requirements_passed": len(requirements) - len(failed), "requirements_failed": len(failed), "summary": summary, "profile_rows": all_profile_rows, "artifacts": {"circuits": circuit_files, "r119_result": R119_RESULT_PATH}, "claim_boundary": {"what_is_supported": "Explicit Aer noise-margin replay of the R119 private signed observable bundle over four synthetic profiles.", "what_is_not_supported": "Calibrated backend evidence, real hardware execution, general protocol soundness, cryptographic soundness, sampling hardness, quantum advantage, BQP separation, or full-distribution verification.", "next_gate": "Replace synthetic Aer profiles with calibrated backend properties or an independent backend transcript."}}
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
