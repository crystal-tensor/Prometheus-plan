#!/usr/bin/env python3
"""Export B4/B8 randomized hidden-projection verifier circuits as OpenQASM 3."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import numpy as np
from qiskit import QuantumCircuit, qasm3
from qiskit_aer import AerSimulator

from b4_b8_circuit_refresh_task import build_tasks, gf2_inverse, parse_int_list, parse_str_list
from b10_t2_transcript_leakage_simulator import honest_samples, refreshed_masks, target_vector


METHOD = "b4_b8_openqasm3_randomized_measurement_packet_v0"
STATUS = "openqasm3_randomized_measurement_packet_not_hardware_execution_or_advantage_claim"
MODEL_STATUS = "hardware_executable_circuit_packet_not_hardware_run"
VERSION = "0.1"
QASM_VERSION = "OPENQASM 3.0"


def output_to_input_bits(output_bits: np.ndarray, inverse_matrix: np.ndarray) -> np.ndarray:
    return (output_bits.astype(np.uint8) @ inverse_matrix.T) % 2


def slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_verifier_circuit(
    task: dict[str, Any],
    input_bits: np.ndarray,
    masks: list[list[int]],
    challenge_flips: np.ndarray,
) -> QuantumCircuit:
    data_qubits = int(task["qubits"])
    predicate_count = len(masks)
    circuit = QuantumCircuit(data_qubits + predicate_count, predicate_count)
    for qubit, bit in enumerate(input_bits.tolist()):
        if int(bit):
            circuit.x(qubit)
    for control, target in task["gates"]:
        circuit.cx(int(control), int(target))
    for predicate_idx, mask in enumerate(masks):
        ancilla = data_qubits + predicate_idx
        for qubit in mask:
            circuit.cx(int(qubit), ancilla)
        if int(challenge_flips[predicate_idx]):
            circuit.x(ancilla)
        circuit.measure(ancilla, predicate_idx)
    return circuit


def decode_memory(memory: str, predicate_count: int, challenge_flips: np.ndarray) -> np.ndarray:
    bits = np.array([int(bit) for bit in memory[::-1][:predicate_count]], dtype=np.int8)
    return bits ^ challenge_flips.astype(np.int8)


def run_aer_batch(
    circuits: list[QuantumCircuit],
    predicate_count: int,
    challenge_flips: list[np.ndarray],
    seed: int,
) -> np.ndarray:
    simulator = AerSimulator(method="stabilizer", seed_simulator=seed)
    result = simulator.run(circuits, shots=1, memory=True).result()
    measured = []
    for idx in range(len(circuits)):
        memory = result.get_memory(idx)[0]
        measured.append(decode_memory(memory, predicate_count, challenge_flips[idx]))
    return np.array(measured, dtype=np.int8)


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("status") != STATUS:
        errors.append("status must identify the packet as not hardware execution or advantage")
    if report.get("method") != METHOD:
        errors.append("method mismatch")
    if report.get("qasm_version") != QASM_VERSION:
        errors.append("OpenQASM 3 version marker mismatch")
    if report.get("hardware_executable_randomized_measurement_circuits_instantiated") is not True:
        errors.append("hardware-executable randomized measurement circuits should be instantiated")
    if report.get("openqasm3_files_exported") is not True:
        errors.append("OpenQASM 3 files should be exported")
    if report.get("all_qasm3_headers_valid") is not True:
        errors.append("all exported QASM files must start with OPENQASM 3.0")
    if report.get("hardware_execution_performed") is not False:
        errors.append("packet must not claim hardware execution")
    for field in [
        "quantum_advantage_claimed",
        "bqp_separation_claimed",
        "sampling_hardness_proved",
        "cryptographic_soundness_proved",
        "full_distribution_verification_claimed",
    ]:
        if report.get(field) is not False:
            errors.append(f"packet must keep {field}=False")
    if report.get("aer_semantic_mismatch_count") != 0:
        errors.append("Aer semantic mismatch count should be zero")
    if float(report.get("minimum_aer_honest_completeness", 0.0)) < 1.0:
        errors.append("ideal Aer honest completeness should be 1.0 for the exported packet")
    if report.get("circuit_file_count") != len(report.get("circuits", [])):
        errors.append("circuit_file_count must equal circuit metadata rows")
    if report.get("circuit_file_count") != (
        int(report.get("task_count", 0))
        * int(report.get("refresh_mode_count", 0))
        * int(report.get("packet_circuits_per_task_mode", 0))
    ):
        errors.append("circuit_file_count does not match task x mode x packet count")
    if not report.get("circuits"):
        errors.append("packet must contain circuit metadata")
    for row in report.get("circuits", []):
        if not row.get("qasm3_header_valid"):
            errors.append(f"invalid OpenQASM 3 header for {row.get('path')}")
        if row.get("semantic_mismatch_count") != 0:
            errors.append(f"semantic mismatch in {row.get('path')}")
    return errors


def build_packet(
    qubits: list[int],
    invariant_count: int,
    circuit_depth_factor: int,
    refresh_modes: list[str],
    packet_circuits_per_task_mode: int,
    seed: int,
    qasm_dir: Path,
) -> dict[str, Any]:
    started = time.time()
    rng = np.random.default_rng(seed)
    tasks = build_tasks(qubits, invariant_count, circuit_depth_factor, seed + 23000)
    qasm_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    all_circuits: list[QuantumCircuit] = []
    all_expected: list[np.ndarray] = []
    all_flips: list[np.ndarray] = []
    all_row_indices: list[int] = []
    max_total_qubits = 0

    for task in tasks:
        inverse_matrix = gf2_inverse(task["matrix"])
        for refresh_mode in refresh_modes:
            masks = refreshed_masks(task, refresh_mode, invariant_count, rng)
            targets = target_vector(len(masks), int(task["qubits"]))
            desired_outputs = honest_samples(
                int(task["qubits"]),
                packet_circuits_per_task_mode,
                masks,
                targets,
                honest_bias=1.0,
                rng=rng,
            )
            for packet_idx, output_bits in enumerate(desired_outputs):
                input_bits = output_to_input_bits(output_bits, inverse_matrix)
                challenge_flips = rng.integers(0, 2, size=len(masks), dtype=np.int8)
                circuit = build_verifier_circuit(task, input_bits, masks, challenge_flips)
                circuit.name = f"{slug(task['task_id'])}_{slug(refresh_mode)}_{packet_idx:02d}"
                qasm_text = qasm3.dumps(circuit)
                qasm_path = qasm_dir / f"{circuit.name}.qasm"
                qasm_path.write_text(qasm_text, encoding="utf-8")
                ops = {key: int(value) for key, value in circuit.count_ops().items()}
                row = {
                    "task_id": task["task_id"],
                    "refresh_mode": refresh_mode,
                    "packet_index": packet_idx,
                    "path": str(qasm_path),
                    "sha256": sha256_text(qasm_text),
                    "qasm_version": QASM_VERSION,
                    "qasm3_header_valid": qasm_text.startswith(f"{QASM_VERSION};"),
                    "data_qubits": int(task["qubits"]),
                    "ancilla_qubits": len(masks),
                    "total_qubits": int(task["qubits"]) + len(masks),
                    "classical_bits": len(masks),
                    "cnot_count": ops.get("cx", 0),
                    "x_count": ops.get("x", 0),
                    "measure_count": ops.get("measure", 0),
                    "line_count": len(qasm_text.splitlines()),
                    "byte_count": len(qasm_text.encode("utf-8")),
                    "semantic_mismatch_count": None,
                    "predicate_bit_error_rate": None,
                }
                max_total_qubits = max(max_total_qubits, row["total_qubits"])
                rows.append(row)
                all_row_indices.append(len(rows) - 1)
                all_circuits.append(circuit)
                all_flips.append(challenge_flips)
                all_expected.append(((1 - targets) // 2).astype(np.int8))

    measured = run_aer_batch(
        all_circuits,
        predicate_count=invariant_count,
        challenge_flips=all_flips,
        seed=seed + 40000,
    )
    expected = np.array(all_expected, dtype=np.int8)
    mismatches_by_circuit = np.sum(measured != expected, axis=1)
    for idx, row_idx in enumerate(all_row_indices):
        rows[row_idx]["semantic_mismatch_count"] = int(mismatches_by_circuit[idx])
        rows[row_idx]["predicate_bit_error_rate"] = float(np.mean(measured[idx] != expected[idx]))

    total_mismatches = int(np.sum(mismatches_by_circuit))
    report = {
        "benchmark_id": "B4_B8",
        "problem_ids": [16, 30],
        "title": "B4/B8 OpenQASM 3 randomized-measurement circuit packet",
        "version": VERSION,
        "last_updated": time.strftime("%Y-%m-%d"),
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "method": METHOD,
        "source_method": "b4_b8_circuit_hidden_projection_refresh_v0",
        "task_family": "random_cnot_hidden_projection_sampling",
        "qasm_version": QASM_VERSION,
        "qasm_directory": str(qasm_dir),
        "task_count": len(tasks),
        "qubits": qubits,
        "refresh_modes": refresh_modes,
        "refresh_mode_count": len(refresh_modes),
        "invariant_count": invariant_count,
        "circuit_depth_factor": circuit_depth_factor,
        "packet_circuits_per_task_mode": packet_circuits_per_task_mode,
        "circuit_file_count": len(rows),
        "max_total_qubits": max_total_qubits,
        "openqasm3_files_exported": True,
        "all_qasm3_headers_valid": all(row["qasm3_header_valid"] for row in rows),
        "hardware_executable_randomized_measurement_circuits_instantiated": True,
        "qiskit_aer_semantic_check_performed": True,
        "aer_semantic_mismatch_count": total_mismatches,
        "maximum_predicate_bit_error_rate": max(float(row["predicate_bit_error_rate"]) for row in rows),
        "minimum_aer_honest_completeness": 1.0 if total_mismatches == 0 else 0.0,
        "hardware_execution_performed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "sampling_hardness_proved": False,
        "cryptographic_soundness_proved": False,
        "full_distribution_verification_claimed": False,
        "circuits": rows,
        "claim_boundary": {
            "what_is_supported": (
                "A deterministic OpenQASM 3 packet of hidden-projection verifier circuits with randomized "
                "measurement challenge flips and ideal Qiskit/Aer semantic checks."
            ),
            "what_is_not_supported": (
                "This is not hardware execution, not calibrated backend evidence, not sampling hardness, "
                "not cryptographic soundness, not quantum advantage, and not BQP separation."
            ),
            "hardware_execution_performed": False,
            "quantum_advantage_claimed": False,
            "bqp_separation_claimed": False,
            "sampling_hardness_proved": False,
            "cryptographic_soundness_proved": False,
            "full_distribution_verification_claimed": False,
        },
        "runtime_seconds": round(time.time() - started, 6),
    }
    report["validation_errors"] = validate_report({**report, "validation_errors": []})
    return report


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        text = json.dumps(payload, indent=2, sort_keys=True)
    else:
        text = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# B4/B8 OpenQASM 3 Randomized-Measurement Packet v0.1",
        "",
        f"Last updated: {report['last_updated']}",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Summary",
        "",
        f"- Method: `{report['method']}`",
        f"- Model status: `{report['model_status']}`",
        f"- QASM version: {report['qasm_version']}",
        f"- QASM directory: `{report['qasm_directory']}`",
        f"- Tasks / refresh modes / circuits per task-mode: {report['task_count']} / {report['refresh_mode_count']} / {report['packet_circuits_per_task_mode']}",
        f"- Circuit files: {report['circuit_file_count']}",
        f"- Max total qubits including verifier ancillas: {report['max_total_qubits']}",
        f"- All OpenQASM 3 headers valid: {report['all_qasm3_headers_valid']}",
        f"- Aer semantic mismatch count: {report['aer_semantic_mismatch_count']}",
        f"- Minimum Aer honest completeness: {report['minimum_aer_honest_completeness']:.3f}",
        f"- Hardware execution performed: {report['hardware_execution_performed']}",
        f"- Quantum advantage claimed: {report['quantum_advantage_claimed']}",
        f"- Validation errors: {len(report['validation_errors'])}",
        "",
        "## Packet Rows",
        "",
        "| task | mode | idx | qubits | cx | x | measure | qasm | sha256 |",
        "|---|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in report["circuits"]:
        lines.append(
            f"| {row['task_id']} | {row['refresh_mode']} | {row['packet_index']} | "
            f"{row['total_qubits']} | {row['cnot_count']} | {row['x_count']} | "
            f"{row['measure_count']} | `{row['path']}` | `{row['sha256'][:12]}` |"
        )
    lines.extend(["", "## Claim Boundary", ""])
    for key, value in report["claim_boundary"].items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qubits", default="12,16,20")
    parser.add_argument("--invariant-count", type=int, default=10)
    parser.add_argument("--circuit-depth-factor", type=int, default=4)
    parser.add_argument("--refresh-modes", default="projection_rotation,challenge_refresh,refresh_plus_rotation")
    parser.add_argument("--packet-circuits-per-task-mode", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260618)
    parser.add_argument(
        "--qasm-dir",
        type=Path,
        default=Path("results/B4_B8_openqasm3_randomized_measurement_packet/circuits"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B4_B8_openqasm3_randomized_measurement_packet_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B4_B8_openqasm3_randomized_measurement_packet.md"),
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    report = build_packet(
        qubits=parse_int_list(args.qubits),
        invariant_count=args.invariant_count,
        circuit_depth_factor=args.circuit_depth_factor,
        refresh_modes=parse_str_list(args.refresh_modes),
        packet_circuits_per_task_mode=args.packet_circuits_per_task_mode,
        seed=args.seed,
        qasm_dir=args.qasm_dir,
    )
    write_json(args.json_output, report, pretty=args.pretty)
    write_markdown(args.markdown_output, report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "qasm_version": report["qasm_version"],
                "circuit_file_count": report["circuit_file_count"],
                "aer_semantic_mismatch_count": report["aer_semantic_mismatch_count"],
                "validation_error_count": len(report["validation_errors"]),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 1 if report["validation_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
