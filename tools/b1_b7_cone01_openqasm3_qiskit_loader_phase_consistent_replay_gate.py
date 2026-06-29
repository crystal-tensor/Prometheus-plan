#!/usr/bin/env python3
"""Qiskit-loader phase-consistent replay gate for B1/B7 cone_01 OpenQASM 3."""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
from typing import Any

import numpy as np
from qiskit import QuantumCircuit, qasm3
from qiskit.quantum_info import Statevector, state_fidelity


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RESEARCH = ROOT / "research"

METHOD = "b1_b7_cone01_openqasm3_qiskit_loader_phase_consistent_replay_gate_v0"
STATUS = "cone01_openqasm3_qiskit_loader_phase_consistent_replay_passed"
MODEL_STATUS = "qiskit_loader_openqasm3_has_phase_consistent_sampled_replay_without_b7_credit"

SOURCE_QASM_PATH = RESULTS / "b1_native_t_resource_optimizer" / "qasmbench_medium_exact" / "gcm_h6.qasm"
QISKIT_LOADER_MULTI_INPUT_PATH = (
    RESULTS / "B1_B7_cone01_openqasm3_qiskit_loader_multi_input_replay_gate_v0.json"
)
PROJECT_LOCAL_PHASE_PATH = RESULTS / "B1_B7_cone01_openqasm3_phase_consistent_replay_gate_v0.json"
QASM3_PATH = (
    RESULTS
    / "B1_B7_cone01_openqasm3_candidate_export_gate"
    / "gcm_h6_line268_line1381_candidate_openqasm3.qasm"
)
OUT_JSON = RESULTS / "B1_B7_cone01_openqasm3_qiskit_loader_phase_consistent_replay_gate_v0.json"
OUT_MD = RESEARCH / "B1_B7_cone01_openqasm3_qiskit_loader_phase_consistent_replay_gate.md"

PHASE_TOLERANCE = 1e-10
FIDELITY_TOLERANCE = 1e-10
AMPLITUDE_TOLERANCE = 1e-10
PROBABILITY_TOLERANCE = 1e-10
PRODUCT_STATE_SEEDS = [17, 29]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def without_final_measurements(circuit: QuantumCircuit) -> QuantumCircuit:
    return circuit.remove_final_measurements(inplace=False)


def basis_state(num_qubits: int, active_qubits: list[int]) -> Statevector:
    prep = QuantumCircuit(num_qubits)
    for qubit in active_qubits:
        prep.x(qubit)
    return Statevector.from_instruction(prep)


def product_state(num_qubits: int, seed: int) -> Statevector:
    rng = np.random.default_rng(seed)
    prep = QuantumCircuit(num_qubits)
    for qubit in range(num_qubits):
        prep.ry(float(rng.uniform(-np.pi, np.pi)), qubit)
        prep.rz(float(rng.uniform(-np.pi, np.pi)), qubit)
    return Statevector.from_instruction(prep)


def normalized_superposition(left: Statevector, right: Statevector, phase: complex = 1.0) -> Statevector:
    vector = np.asarray(left.data) + phase * np.asarray(right.data)
    return Statevector(vector / np.linalg.norm(vector))


def input_suite(num_qubits: int) -> list[tuple[str, str, Statevector]]:
    zero = basis_state(num_qubits, [])
    x_q0 = basis_state(num_qubits, [0])
    x_q4 = basis_state(num_qubits, [4])
    x_q14 = basis_state(num_qubits, [14])
    product_17 = product_state(num_qubits, 17)
    product_29 = product_state(num_qubits, 29)
    return [
        ("zero", "basis_phase_anchor", zero),
        ("x_q0", "basis_phase_anchor", x_q0),
        ("x_q4", "basis_phase_anchor", x_q4),
        ("x_q14", "basis_phase_anchor", x_q14),
        ("sup_zero_xq4", "basis_superposition", normalized_superposition(zero, x_q4)),
        ("sup_xq0_xq14", "basis_superposition", normalized_superposition(x_q0, x_q14)),
        ("sup_zero_product17", "basis_product_superposition", normalized_superposition(zero, product_17)),
        (
            "sup_product17_i_product29",
            "product_superposition",
            normalized_superposition(product_17, product_29, 1j),
        ),
    ]


def align_global_phase(reference: np.ndarray, candidate: np.ndarray, overlap: complex) -> np.ndarray:
    if abs(overlap) == 0:
        return candidate
    return candidate * np.conj(overlap / abs(overlap))


def replay_case(
    label: str,
    input_kind: str,
    initial_state: Statevector,
    source_circuit: QuantumCircuit,
    qiskit_loader_circuit: QuantumCircuit,
) -> dict[str, Any]:
    source_state = initial_state.evolve(source_circuit)
    qiskit_state = initial_state.evolve(qiskit_loader_circuit)
    source_data = np.asarray(source_state.data)
    qiskit_data = np.asarray(qiskit_state.data)
    overlap = complex(np.vdot(source_data, qiskit_data))
    aligned_qiskit = align_global_phase(source_data, qiskit_data, overlap)
    amplitude_delta = np.abs(source_data - aligned_qiskit)
    probability_delta = np.abs(np.abs(source_data) ** 2 - np.abs(qiskit_data) ** 2)
    fidelity = float(state_fidelity(source_state, qiskit_state))
    infidelity = float(max(0.0, 1.0 - fidelity))
    max_amplitude_delta = float(np.max(amplitude_delta))
    max_probability_delta = float(np.max(probability_delta))
    return {
        "label": label,
        "input_kind": input_kind,
        "overlap_magnitude": float(abs(overlap)),
        "overlap_phase_radians": float(np.angle(overlap)),
        "state_fidelity": fidelity,
        "infidelity": infidelity,
        "max_global_phase_aligned_amplitude_delta": max_amplitude_delta,
        "l2_global_phase_aligned_amplitude_delta": float(
            np.linalg.norm(source_data - aligned_qiskit)
        ),
        "max_probability_delta": max_probability_delta,
        "passed": bool(
            infidelity <= FIDELITY_TOLERANCE
            and max_amplitude_delta <= AMPLITUDE_TOLERANCE
            and max_probability_delta <= PROBABILITY_TOLERANCE
        ),
    }


def phase_spread(phases: list[float]) -> float:
    unwrapped = np.unwrap(np.asarray(phases, dtype=float))
    return float(np.max(unwrapped) - np.min(unwrapped))


def main() -> None:
    loader_multi_payload = load_json(QISKIT_LOADER_MULTI_INPUT_PATH)
    local_phase_payload = load_json(PROJECT_LOCAL_PHASE_PATH)
    source_circuit = QuantumCircuit.from_qasm_file(str(SOURCE_QASM_PATH))
    qiskit_circuit = qasm3.loads(QASM3_PATH.read_text(encoding="utf-8"))

    errors: list[str] = []
    if (
        loader_multi_payload.get("status")
        != "cone01_openqasm3_qiskit_loader_multi_input_replay_passed_sampled_inputs"
    ):
        errors.append("source Qiskit-loader multi-input gate status changed")
    if (
        local_phase_payload.get("status")
        != "cone01_openqasm3_phase_consistent_replay_passed_not_symbolic_certificate"
    ):
        errors.append("source project-local phase-consistent gate status changed")

    qiskit_counts = {key: int(value) for key, value in qiskit_circuit.count_ops().items()}
    expected_counts = {"cx": 789, "rz": 601, "u": 487, "measure": 1}
    if qiskit_counts != expected_counts:
        errors.append("Qiskit-loader operation counts changed")
    if qiskit_circuit.num_qubits != 19:
        errors.append("Qiskit-loader qubit count changed")
    if qiskit_circuit.num_clbits != 1:
        errors.append("Qiskit-loader clbit count changed")
    if qiskit_circuit.depth() != 1483:
        errors.append("Qiskit-loader depth changed")

    source_unitary = without_final_measurements(source_circuit)
    qiskit_unitary = without_final_measurements(qiskit_circuit)
    num_qubits = source_circuit.num_qubits
    cases = [
        replay_case(label, kind, state, source_unitary, qiskit_unitary)
        for label, kind, state in input_suite(num_qubits)
    ]
    failed_cases = [case["label"] for case in cases if not case["passed"]]
    spread = phase_spread([case["overlap_phase_radians"] for case in cases])
    replay_passed = not failed_cases and spread <= PHASE_TOLERANCE
    if failed_cases:
        errors.append("Qiskit-loader phase replay failed cases: " + ", ".join(failed_cases))
    if spread > PHASE_TOLERANCE:
        errors.append(f"Qiskit-loader phase spread exceeds tolerance: {spread}")

    summary = {
        "source_qiskit_loader_multi_input_gate": rel(QISKIT_LOADER_MULTI_INPUT_PATH),
        "source_project_local_phase_consistent_gate": rel(PROJECT_LOCAL_PHASE_PATH),
        "source_qasm_path": rel(SOURCE_QASM_PATH),
        "openqasm3_candidate_path": rel(QASM3_PATH),
        "qiskit_version": package_version("qiskit"),
        "qiskit_qasm3_import_version": package_version("qiskit-qasm3-import"),
        "openqasm3_package_version": package_version("openqasm3"),
        "qiskit_loader_passed": True,
        "qiskit_num_qubits": int(qiskit_circuit.num_qubits),
        "qiskit_num_clbits": int(qiskit_circuit.num_clbits),
        "qiskit_depth": int(qiskit_circuit.depth()),
        "qiskit_count_ops": qiskit_counts,
        "expected_qiskit_count_ops": expected_counts,
        "statevector_dimension": 2**num_qubits,
        "final_measurement_removed_for_statevector": True,
        "input_case_count": len(cases),
        "phase_anchor_input_count": 4,
        "superposition_input_count": 4,
        "product_state_seeds": PRODUCT_STATE_SEEDS,
        "input_cases": cases,
        "qiskit_loader_phase_consistent_replay_passed": replay_passed,
        "failed_input_case_count": len(failed_cases),
        "failed_input_cases": failed_cases,
        "overlap_phase_spread_radians": spread,
        "min_overlap_magnitude": min(case["overlap_magnitude"] for case in cases),
        "min_state_fidelity": min(case["state_fidelity"] for case in cases),
        "max_infidelity": max(case["infidelity"] for case in cases),
        "max_global_phase_aligned_amplitude_delta": max(
            case["max_global_phase_aligned_amplitude_delta"] for case in cases
        ),
        "max_probability_delta": max(case["max_probability_delta"] for case in cases),
        "accepted_qiskit_loader_parse_artifact_count": 1,
        "accepted_qiskit_loader_replay_artifact_count": 1 if replay_passed else 0,
        "accepted_qiskit_loader_phase_consistent_replay_artifact_count": (
            1 if replay_passed else 0
        ),
        "accepted_full_circuit_replay_certificate_count": 0,
        "accepted_symbolic_unitary_equivalence_count": 0,
        "accepted_local_u3_pricing_certificate_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": 30,
        "missing_proxy_t_after_gate": 600,
        "qiskit_loader_parse_claimed": True,
        "qiskit_loader_replay_claimed": replay_passed,
        "qiskit_loader_phase_consistent_replay_claimed": replay_passed,
        "symbolic_unitary_equivalence_claimed": False,
        "arbitrary_input_equivalence_claimed": False,
        "full_hilbert_space_certificate_claimed": False,
        "local_u3_pricing_accepted": False,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "validation_error_count": len(errors),
    }
    payload = {
        "benchmark_id": "B1",
        "linked_b7_problem_id": 21,
        "method": METHOD,
        "status": STATUS if not errors else "cone01_openqasm3_qiskit_loader_phase_consistent_replay_failed",
        "model_status": MODEL_STATUS if not errors else "qiskit_loader_openqasm3_phase_replay_rejected",
        "workload": "qasmbench_medium_exact/gcm_h6.qasm",
        "claim_boundary": {
            "supported_claim": (
                "The Qiskit-loaded OpenQASM 3 candidate matches the optimized source "
                "on phase-anchor and superposition replay cases while maintaining "
                "tiny overlap-phase spread after final measurements are removed."
            ),
            "qiskit_loader_parse_claimed": True,
            "qiskit_loader_replay_claimed": replay_passed,
            "qiskit_loader_phase_consistent_replay_claimed": replay_passed,
            "symbolic_unitary_equivalence_claimed": False,
            "arbitrary_input_equivalence_claimed": False,
            "full_hilbert_space_certificate_claimed": False,
            "local_u3_pricing_accepted": False,
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "unsupported_claims": [
                "This is sampled phase-consistent statevector evidence, not arbitrary-input equivalence.",
                "This is not a symbolic exact full-circuit unitary proof.",
                "This does not price or eliminate the remaining line-1381 off-grid local-U3 parameters.",
                "This does not recover the dropped line-1378 overlap delta.",
                "This does not improve the B7 resource ledger.",
            ],
        },
        "summary": summary,
        "validation_errors": errors,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    if errors:
        raise SystemExit("OpenQASM3 Qiskit-loader phase-consistent replay failed: " + "; ".join(errors))


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    claims = payload["claim_boundary"]
    return "\n".join(
        [
            "# B1/B7 cone_01 OpenQASM 3 Qiskit-Loader Phase-Consistent Replay Gate",
            "",
            f"- Method: `{payload['method']}`",
            f"- Status: `{payload['status']}`",
            f"- Model status: `{payload['model_status']}`",
            f"- Workload: `{payload['workload']}`",
            f"- Supported claim: {claims['supported_claim']}",
            "",
            "## Inputs",
            "",
            f"- Qiskit-loader multi-input gate: `{summary['source_qiskit_loader_multi_input_gate']}`",
            f"- Project-local phase-consistent gate: `{summary['source_project_local_phase_consistent_gate']}`",
            f"- OpenQASM 3 candidate: `{summary['openqasm3_candidate_path']}`",
            "",
            "## Loader Evidence",
            "",
            f"- Qiskit / qiskit-qasm3-import / openqasm3 versions: {summary['qiskit_version']} / {summary['qiskit_qasm3_import_version']} / {summary['openqasm3_package_version']}",
            f"- Qubits / clbits / depth: {summary['qiskit_num_qubits']} / {summary['qiskit_num_clbits']} / {summary['qiskit_depth']}",
            f"- Operation counts: {summary['qiskit_count_ops']}",
            "",
            "## Phase-Consistent Replay Evidence",
            "",
            f"- Input cases: {summary['input_case_count']} ({summary['phase_anchor_input_count']} phase anchors, {summary['superposition_input_count']} superpositions)",
            f"- Product-state seeds: {summary['product_state_seeds']}",
            f"- Overlap phase spread: {summary['overlap_phase_spread_radians']}",
            f"- Min overlap magnitude: {summary['min_overlap_magnitude']}",
            f"- Min fidelity / max infidelity: {summary['min_state_fidelity']} / {summary['max_infidelity']}",
            f"- Max amplitude / probability delta: {summary['max_global_phase_aligned_amplitude_delta']} / {summary['max_probability_delta']}",
            f"- Failed cases: {summary['failed_input_cases']}",
            f"- Accepted Qiskit-loader parse / replay / phase artifacts: {summary['accepted_qiskit_loader_parse_artifact_count']} / {summary['accepted_qiskit_loader_replay_artifact_count']} / {summary['accepted_qiskit_loader_phase_consistent_replay_artifact_count']}",
            f"- Accepted occurrence / proxy-T reduction / B7 claim: {summary['accepted_occurrence_removal']} / {summary['accepted_proxy_t_reduction']} / {summary['b7_ledger_improvement_claimed']}",
            "",
            "## Claim Boundary",
            "",
            *[f"- {claim}" for claim in claims["unsupported_claims"]],
            "",
            "## Validation",
            "",
            f"- Qiskit-loader phase-consistent replay passed: {summary['qiskit_loader_phase_consistent_replay_passed']}",
            f"- Validation errors: {summary['validation_error_count']}",
            "",
        ]
    )


if __name__ == "__main__":
    main()
