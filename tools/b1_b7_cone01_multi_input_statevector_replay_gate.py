#!/usr/bin/env python3
"""Multi-input statevector replay pressure for the B1/B7 cone_01 QASM2 candidate.

T-B1-004aw showed that the T-B1-004av QASM2 candidate matches the source
`gcm_h6` circuit on the benchmark default input. This gate adds sampled input
pressure: several computational-basis preparations and deterministic product
states are evolved through both circuits after final measurements are removed.

This is stronger than a default-input replay probe, but it is still not a
symbolic arbitrary-input unitary-equivalence proof and still cannot move the B7
resource ledger.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, state_fidelity

from b1_b7_cone01_carrier_absorption_inventory_gate import (
    PROXY_T_PER_OCCURRENCE,
    REQUIRED_OCCURRENCE_REMOVALS,
    display_path,
    load_json,
    write_json,
    write_text,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_QASM_PATH = (
    ROOT / "results" / "b1_native_t_resource_optimizer" / "qasmbench_medium_exact" / "gcm_h6.qasm"
)
CANDIDATE_REWRITE_PATH = ROOT / "results" / "B1_B7_cone01_qasm2_candidate_rewrite_gate_v0.json"
JSON_OUT = ROOT / "results" / "B1_B7_cone01_multi_input_statevector_replay_gate_v0.json"
MD_OUT = ROOT / "research" / "B1_B7_cone01_multi_input_statevector_replay_gate.md"

METHOD = "b1_b7_cone01_multi_input_statevector_replay_gate_v0"
STATUS = "cone01_multi_input_statevector_replay_pressure_passed_not_symbolic_certificate"
MODEL_STATUS = "qasm2_candidate_matches_sampled_input_statevectors_without_b7_credit"
FIDELITY_TOLERANCE = 1e-10
AMPLITUDE_TOLERANCE = 1e-10
PROBABILITY_TOLERANCE = 1e-10
PRODUCT_STATE_SEEDS = [17, 29]
BASIS_INPUTS = [
    ("zero", []),
    ("x_q0", [0]),
    ("x_q4", [4]),
    ("x_q14", [14]),
    ("x_q4_q14", [4, 14]),
    ("x_q0_q4_q14", [0, 4, 14]),
]


def load_circuit(path: Path) -> QuantumCircuit:
    return QuantumCircuit.from_qasm_file(str(path))


def without_final_measurements(circuit: QuantumCircuit) -> QuantumCircuit:
    return circuit.remove_final_measurements(inplace=False)


def align_global_phase(reference: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    inner = np.vdot(reference, candidate)
    if abs(inner) == 0:
        return candidate
    return candidate * np.conj(inner / abs(inner))


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


def replay_case(
    label: str,
    input_kind: str,
    initial_state: Statevector,
    source_circuit: QuantumCircuit,
    candidate_circuit: QuantumCircuit,
) -> dict[str, Any]:
    source_state = initial_state.evolve(source_circuit)
    candidate_state = initial_state.evolve(candidate_circuit)
    source_data = np.asarray(source_state.data)
    candidate_data = np.asarray(candidate_state.data)
    aligned_candidate = align_global_phase(source_data, candidate_data)
    amplitude_delta = np.abs(source_data - aligned_candidate)
    probability_delta = np.abs(np.abs(source_data) ** 2 - np.abs(candidate_data) ** 2)
    fidelity = float(state_fidelity(source_state, candidate_state))
    return {
        "label": label,
        "input_kind": input_kind,
        "state_fidelity": fidelity,
        "infidelity": float(max(0.0, 1.0 - fidelity)),
        "max_global_phase_aligned_amplitude_delta": float(np.max(amplitude_delta)),
        "l2_global_phase_aligned_amplitude_delta": float(np.linalg.norm(source_data - aligned_candidate)),
        "max_probability_delta": float(np.max(probability_delta)),
        "passed": bool(
            1.0 - fidelity <= FIDELITY_TOLERANCE
            and float(np.max(amplitude_delta)) <= AMPLITUDE_TOLERANCE
            and float(np.max(probability_delta)) <= PROBABILITY_TOLERANCE
        ),
    }


def run_probe() -> dict[str, Any]:
    candidate_payload = load_json(CANDIDATE_REWRITE_PATH)
    candidate_qasm = ROOT / candidate_payload["summary"]["qasm2_candidate_path"]
    source_circuit = load_circuit(SOURCE_QASM_PATH)
    candidate_circuit = load_circuit(candidate_qasm)
    source_unitary_part = without_final_measurements(source_circuit)
    candidate_unitary_part = without_final_measurements(candidate_circuit)
    num_qubits = source_circuit.num_qubits

    cases: list[dict[str, Any]] = []
    for label, active_qubits in BASIS_INPUTS:
        cases.append(
            replay_case(
                label,
                "computational_basis",
                basis_state(num_qubits, active_qubits),
                source_unitary_part,
                candidate_unitary_part,
            )
        )
    for seed in PRODUCT_STATE_SEEDS:
        cases.append(
            replay_case(
                f"product_seed_{seed}",
                "deterministic_product_state",
                product_state(num_qubits, seed),
                source_unitary_part,
                candidate_unitary_part,
            )
        )

    accepted_removed = 0
    failed_cases = [case["label"] for case in cases if not case["passed"]]
    summary = {
        "source_qasm": display_path(SOURCE_QASM_PATH),
        "candidate_qasm": display_path(candidate_qasm),
        "source_method": candidate_payload.get("method"),
        "source_default_input_replay_method": "b1_b7_cone01_full_statevector_replay_probe_gate_v0",
        "qubit_count": num_qubits,
        "statevector_dimension": 2**num_qubits,
        "source_operation_count_without_measurements": int(source_unitary_part.size()),
        "candidate_operation_count_without_measurements": int(candidate_unitary_part.size()),
        "source_cnot_count": int(source_unitary_part.count_ops().get("cx", 0)),
        "candidate_cnot_count": int(candidate_unitary_part.count_ops().get("cx", 0)),
        "candidate_cnot_delta": int(source_unitary_part.count_ops().get("cx", 0))
        - int(candidate_unitary_part.count_ops().get("cx", 0)),
        "final_measurement_removed_for_statevector": True,
        "input_case_count": len(cases),
        "computational_basis_input_count": len(BASIS_INPUTS),
        "deterministic_product_state_input_count": len(PRODUCT_STATE_SEEDS),
        "product_state_seeds": PRODUCT_STATE_SEEDS,
        "input_cases": cases,
        "multi_input_statevector_replay_passed": len(failed_cases) == 0,
        "failed_input_case_count": len(failed_cases),
        "failed_input_cases": failed_cases,
        "min_state_fidelity": min(case["state_fidelity"] for case in cases),
        "max_infidelity": max(case["infidelity"] for case in cases),
        "max_global_phase_aligned_amplitude_delta": max(
            case["max_global_phase_aligned_amplitude_delta"] for case in cases
        ),
        "max_probability_delta": max(case["max_probability_delta"] for case in cases),
        "symbolic_unitary_equivalence_claimed": False,
        "arbitrary_input_equivalence_claimed": False,
        "accepted_full_circuit_replay_certificate_count": 0,
        "accepted_full_circuit_qasm_patch_count": 0,
        "accepted_occurrence_removal": accepted_removed,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": max(0, REQUIRED_OCCURRENCE_REMOVALS - accepted_removed),
        "missing_proxy_t_after_gate": max(
            0,
            (REQUIRED_OCCURRENCE_REMOVALS - accepted_removed) * PROXY_T_PER_OCCURRENCE,
        ),
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
    }
    payload = {
        "benchmark_id": "B1",
        "linked_b7_problem_id": 21,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "workload": "qasmbench_medium_exact/gcm_h6.qasm",
        "source_candidate_rewrite_result": display_path(CANDIDATE_REWRITE_PATH),
        "summary": summary,
        "claim_boundary": {
            "supported_claim": (
                "The T-B1-004av QASM2 candidate matches the source circuit across "
                "a deterministic sampled-input statevector replay pressure suite."
            ),
            "unsupported_claims": [
                "This is not a symbolic unitary-equivalence proof for arbitrary input states.",
                "This is not an exhaustive input-space replay certificate.",
                "This is not an accepted B7 occurrence-removing certificate.",
                "This does not recover the dropped line-1378 overlap delta.",
                "This does not price or eliminate the remaining line-1381 off-grid local-U3 parameters.",
            ],
            "symbolic_unitary_equivalence_claimed": False,
            "arbitrary_input_equivalence_claimed": False,
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
    }
    payload["summary"]["validation_error_count"] = len(validate_payload(payload))
    return payload


def close(left: float, right: float, tolerance: float) -> bool:
    return math.isclose(float(left), float(right), rel_tol=0.0, abs_tol=tolerance)


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = payload.get("summary", {})
    if payload.get("method") != METHOD:
        errors.append("method_mismatch")
    if payload.get("status") != STATUS:
        errors.append("status_mismatch")
    expected = {
        "qubit_count": 19,
        "statevector_dimension": 524288,
        "source_cnot_count": 795,
        "candidate_cnot_count": 789,
        "candidate_cnot_delta": 6,
        "final_measurement_removed_for_statevector": True,
        "input_case_count": 8,
        "computational_basis_input_count": 6,
        "deterministic_product_state_input_count": 2,
        "multi_input_statevector_replay_passed": True,
        "failed_input_case_count": 0,
        "symbolic_unitary_equivalence_claimed": False,
        "arbitrary_input_equivalence_claimed": False,
        "accepted_full_circuit_replay_certificate_count": 0,
        "accepted_full_circuit_qasm_patch_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": 30,
        "missing_proxy_t_after_gate": 600,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
    }
    for field, value in expected.items():
        if summary.get(field) != value:
            errors.append(f"{field}_expected_{value}_got_{summary.get(field)}")
    if 1.0 - float(summary.get("min_state_fidelity", 0.0)) > FIDELITY_TOLERANCE:
        errors.append("min_state_fidelity_below_tolerance")
    if float(summary.get("max_global_phase_aligned_amplitude_delta", 1.0)) > AMPLITUDE_TOLERANCE:
        errors.append("max_amplitude_delta_above_tolerance")
    if float(summary.get("max_probability_delta", 1.0)) > PROBABILITY_TOLERANCE:
        errors.append("max_probability_delta_above_tolerance")
    if summary.get("failed_input_cases") != []:
        errors.append("failed_input_cases_not_empty")
    if summary.get("product_state_seeds") != PRODUCT_STATE_SEEDS:
        errors.append("product_state_seeds_mismatch")
    for case in summary.get("input_cases", []):
        if case.get("passed") is not True:
            errors.append(f"case_{case.get('label')}_failed")
        if 1.0 - float(case.get("state_fidelity", 0.0)) > FIDELITY_TOLERANCE:
            errors.append(f"case_{case.get('label')}_fidelity_below_tolerance")
        if float(case.get("max_probability_delta", 1.0)) > PROBABILITY_TOLERANCE:
            errors.append(f"case_{case.get('label')}_probability_delta_above_tolerance")
    if not close(summary.get("min_state_fidelity", 0.0), 0.9999999999999547, 1e-15):
        errors.append("min_state_fidelity_regression")
    if float(summary.get("max_probability_delta", 1.0)) > 2e-15:
        errors.append("max_probability_delta_regression")
    for field in [
        "symbolic_unitary_equivalence_claimed",
        "arbitrary_input_equivalence_claimed",
        "resource_saving_claimed",
        "b7_ledger_improvement_claimed",
    ]:
        if summary.get(field) is not False or payload.get("claim_boundary", {}).get(field) is not False:
            errors.append(f"{field}_must_remain_false")
    return errors


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# B1/B7 cone_01 Multi-Input Statevector Replay Gate",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Source QASM: `{summary['source_qasm']}`",
        f"- Candidate QASM: `{summary['candidate_qasm']}`",
        f"- Qubits / statevector dimension: `{summary['qubit_count']}` / `{summary['statevector_dimension']}`",
        f"- Input cases: `{summary['input_case_count']}` total; `{summary['computational_basis_input_count']}` computational-basis and `{summary['deterministic_product_state_input_count']}` deterministic product-state inputs",
        f"- Source / candidate CNOT count / delta: `{summary['source_cnot_count']}` / `{summary['candidate_cnot_count']}` / `{summary['candidate_cnot_delta']}`",
        f"- Multi-input replay passed: `{summary['multi_input_statevector_replay_passed']}`",
        f"- Failed input cases: `{summary['failed_input_case_count']}`",
        f"- Min state fidelity / max infidelity: `{summary['min_state_fidelity']}` / `{summary['max_infidelity']}`",
        f"- Max global-phase-aligned amplitude delta: `{summary['max_global_phase_aligned_amplitude_delta']}`",
        f"- Max probability delta: `{summary['max_probability_delta']}`",
        f"- Accepted full-circuit patch / replay / occurrence / proxy-T reduction: `{summary['accepted_full_circuit_qasm_patch_count']}` / `{summary['accepted_full_circuit_replay_certificate_count']}` / `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        f"- Validation errors: `{summary['validation_error_count']}`",
        "",
        "## Input Cases",
        "",
        "| Case | Kind | Fidelity | Max probability delta | Passed |",
        "|---|---|---:|---:|---|",
    ]
    for case in summary["input_cases"]:
        lines.append(
            f"| `{case['label']}` | `{case['input_kind']}` | `{case['state_fidelity']}` | `{case['max_probability_delta']}` | `{case['passed']}` |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"]["supported_claim"],
            "",
            "Unsupported claims:",
            "",
        ]
    )
    for claim in payload["claim_boundary"]["unsupported_claims"]:
        lines.append(f"- {claim}")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "This is a stronger pressure gate than the default-input replay probe: "
                "the candidate matches the source across a small deterministic input "
                "suite. It is still sampled evidence, not a symbolic arbitrary-input "
                "proof, and it still cannot enter the B7 resource ledger until "
                "occurrence, local-U3 pricing, and full certificate obligations are satisfied."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-output", type=Path, default=JSON_OUT)
    parser.add_argument("--markdown-output", type=Path, default=MD_OUT)
    args = parser.parse_args()
    payload = run_probe()
    write_json(args.json_output, payload, True)
    write_text(args.markdown_output, render_markdown(payload))
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
