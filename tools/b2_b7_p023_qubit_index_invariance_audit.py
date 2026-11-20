#!/usr/bin/env python3
"""Independent audit of the #021/B7, #022/B2, #023 qubit-index metric correction."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import stim


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_qubit_index_invariance_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_qubit_index_invariance_v1.json"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_qubit_index_invariance_audit_v1.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def verdict(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def circuit_for(basis: str, experiment: dict[str, Any]) -> stim.Circuit:
    noise = experiment["noise_parameters"]
    return stim.Circuit.generated(
        "surface_code:rotated_memory_" + basis,
        distance=experiment["distance"],
        rounds=experiment["rounds"],
        after_clifford_depolarization=noise["after_clifford_depolarization"],
        before_round_data_depolarization=noise["before_round_data_depolarization"],
        before_measure_flip_probability=noise["before_measure_flip_probability"],
        after_reset_flip_probability=noise["after_reset_flip_probability"],
    )


def target_qubit(target: stim.GateTarget) -> int | None:
    predicates = (
        target.is_qubit_target,
        target.is_inverted_result_target,
        target.is_x_target,
        target.is_y_target,
        target.is_z_target,
    )
    return target.value if any(predicates) else None


def independent_active_ids(circuit: stim.Circuit) -> list[int]:
    # Flatten repeats here, unlike the producer's recursive traversal.
    values: set[int] = set()
    for operation in circuit.flattened():
        if operation.name == "QUBIT_COORDS":
            continue
        for target in operation.targets_copy():
            value = target_qubit(target)
            if value is not None:
                values.add(value)
    return sorted(values)


def translated_target(target: stim.GateTarget, table: dict[int, int]) -> int | stim.GateTarget:
    if target.is_x_target:
        return stim.target_x(table[target.value])
    if target.is_y_target:
        return stim.target_y(table[target.value])
    if target.is_z_target:
        return stim.target_z(table[target.value])
    if target.is_inverted_result_target:
        return stim.target_inv(table[target.value])
    if target.is_qubit_target:
        return table[target.value]
    return target


def independently_compact(circuit: stim.Circuit) -> stim.Circuit:
    table = {old: new for new, old in enumerate(independent_active_ids(circuit))}

    def translate(block: stim.Circuit) -> stim.Circuit:
        output = stim.Circuit()
        for operation in block:
            if isinstance(operation, stim.CircuitRepeatBlock):
                output.append(stim.CircuitRepeatBlock(operation.repeat_count, translate(operation.body_copy())))
            else:
                output.append(
                    operation.name,
                    [translated_target(target, table) for target in operation.targets_copy()],
                    operation.gate_args_copy(),
                )
        return output

    return translate(circuit)


def independent_coordinates(circuit: stim.Circuit) -> dict[int, tuple[float, ...]]:
    coordinates: dict[int, tuple[float, ...]] = {}
    for operation in circuit.flattened():
        if operation.name != "QUBIT_COORDS":
            continue
        targets = [target.value for target in operation.targets_copy() if target.is_qubit_target]
        if len(targets) != 1:
            raise ValueError("invalid QUBIT_COORDS binding")
        coordinates[targets[0]] = tuple(operation.gate_args_copy())
    return coordinates


def independent_coordinate_canonical(circuit: stim.Circuit) -> stim.Circuit:
    active = independent_active_ids(circuit)
    coordinates = independent_coordinates(circuit)
    if any(qubit not in coordinates for qubit in active):
        raise ValueError("missing coordinate binding")
    if len({coordinates[qubit] for qubit in active}) != len(active):
        raise ValueError("duplicate coordinate binding")
    table = {old: new for new, old in enumerate(sorted(active, key=lambda qubit: coordinates[qubit]))}

    def translate(block: stim.Circuit) -> stim.Circuit:
        output = stim.Circuit()
        for operation in block:
            if isinstance(operation, stim.CircuitRepeatBlock):
                output.append(stim.CircuitRepeatBlock(operation.repeat_count, translate(operation.body_copy())))
            else:
                output.append(
                    operation.name,
                    [translated_target(target, table) for target in operation.targets_copy()],
                    operation.gate_args_copy(),
                )
        return output

    return translate(circuit)


def replay_hashes(circuit: stim.Circuit, shots: int, seed: int) -> dict[str, Any]:
    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(dem)
    detectors, observables = circuit.compile_detector_sampler(seed=seed).sample(
        shots,
        separate_observables=True,
        bit_packed=True,
    )
    predictions = matching.decode_batch(
        detectors,
        bit_packed_shots=True,
        bit_packed_predictions=True,
    )
    failures = np.any(np.bitwise_xor(predictions, observables) != 0, axis=1).astype(np.uint8)
    header = {
        "detector_shape": list(detectors.shape),
        "observable_shape": list(observables.shape),
        "prediction_shape": list(predictions.shape),
        "shots": shots,
    }
    trace = (
        stable_bytes(header)
        + b"\x00"
        + detectors.tobytes(order="C")
        + observables.tobytes(order="C")
        + predictions.tobytes(order="C")
    )
    return {
        **header,
        "logical_failures": int(np.count_nonzero(failures)),
        "detectors_sha256": sha(detectors.tobytes(order="C")),
        "observables_sha256": sha(observables.tobytes(order="C")),
        "predictions_sha256": sha(predictions.tobytes(order="C")),
        "failure_vector_sha256": sha(failures.tobytes(order="C")),
        "trace_sha256": sha(trace),
    }


def challenge(salt: str, payload: bytes) -> tuple[int, str]:
    digest = hashlib.sha256(salt.encode() + b"\x00" + payload).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1), digest.hex()


def audit(protocol_path: Path, result_path: Path) -> dict[str, Any]:
    protocol = load(protocol_path)
    result = load(result_path)
    checks: list[dict[str, Any]] = []
    checks.append(verdict("schema", result["schema_version"] == "b2_b7_p023_qubit_index_invariance_result_v1", result["schema_version"]))
    checks.append(verdict("scope", result["scope"]["included_catalog_problem_ids"] == [21, 22, 23] and result["scope"]["included_tracks"] == ["B2", "B7"], "Exact scope."))
    checks.append(verdict("protocol_hash", result["protocol_binding"]["sha256"] == file_sha(protocol_path), file_sha(protocol_path)))
    checks.append(verdict("generator_hash", result["generator"]["sha256"] == file_sha(ROOT / result["generator"]["path"]), result["generator"]["sha256"]))
    current_bindings = all(file_sha(ROOT / binding["path"]) == binding["sha256"] for key, binding in protocol["frozen_inputs"].items() if key != "artifact_freeze_commit")
    checks.append(verdict("frozen_inputs", current_bindings, "All frozen input hashes match."))
    strict = load(ROOT / protocol["frozen_inputs"]["strict_result"]["path"])
    checks.append(verdict("strict_decision", strict["decision"] == protocol["frozen_inputs"]["strict_result"]["required_decision"], strict["decision"]))
    checks.append(verdict("strict_gate", strict["reference_gate"]["both_bases_strict_pass"], "Strict X/Z correctness remains verified."))
    experiment = strict["strict_reference_experiment"]
    rows = {row["memory_basis"]: row for row in result["basis_rows"]}
    strict_rows = {row["memory_basis"]: row for row in strict["strict_reference_rows"]}
    audit_contract = protocol["adversarial_audit"]
    salt = protocol["challenge_binding_v2"]["audit_salt"]
    independently_recomputed: list[dict[str, Any]] = []
    for basis in ("x", "z"):
        original = circuit_for(basis, experiment)
        compacted = independently_compact(original)
        active = independent_active_ids(original)
        compact_active = independent_active_ids(compacted)
        raw = str(original).encode()
        compact_raw = str(compacted).encode()
        canonical_original = str(independent_coordinate_canonical(original)).encode()
        canonical_compacted = str(independent_coordinate_canonical(compacted)).encode()
        dem_original = str(original.detector_error_model(decompose_errors=True)).encode()
        dem_compacted = str(compacted.detector_error_model(decompose_errors=True)).encode()
        replay_original = replay_hashes(original, audit_contract["audit_shots_per_basis"], audit_contract["audit_seed"])
        replay_compacted = replay_hashes(compacted, audit_contract["audit_shots_per_basis"], audit_contract["audit_seed"])
        raw_seed_original, raw_hash_original = challenge(salt, raw)
        raw_seed_compacted, raw_hash_compacted = challenge(salt, compact_raw)
        canonical_seed_original, canonical_hash_original = challenge(salt, canonical_original)
        canonical_seed_compacted, canonical_hash_compacted = challenge(salt, canonical_compacted)
        independently_recomputed.append(
            {
                "memory_basis": basis,
                "index_span_qubits": original.num_qubits,
                "active_operational_qubits": len(active),
                "unused_index_slots": original.num_qubits - len(active),
                "compacted_index_span_qubits": compacted.num_qubits,
                "compacted_active_operational_qubits": len(compact_active),
                "raw_circuit_sha256": sha(raw),
                "compacted_raw_circuit_sha256": sha(compact_raw),
                "canonical_circuit_sha256": sha(canonical_original),
                "canonical_equal": canonical_original == canonical_compacted,
                "dem_sha256": sha(dem_original),
                "dem_equal": dem_original == dem_compacted,
                "replay_original": replay_original,
                "replay_compacted": replay_compacted,
                "raw_seed_original": raw_seed_original,
                "raw_seed_compacted": raw_seed_compacted,
                "raw_challenge_original": raw_hash_original,
                "raw_challenge_compacted": raw_hash_compacted,
                "canonical_seed_original": canonical_seed_original,
                "canonical_seed_compacted": canonical_seed_compacted,
                "canonical_challenge_original": canonical_hash_original,
                "canonical_challenge_compacted": canonical_hash_compacted,
                "corrected_cost": len(active) * experiment["rounds"],
            }
        )

        recorded = rows[basis]
        strict_row = strict_rows[basis]
        checks.append(verdict(f"{basis}_strict_raw_binding", sha(raw) == strict_row["circuit_sha256"] == recorded["raw_circuit_sha256"]["original"], sha(raw)))
        checks.append(verdict(f"{basis}_active_count", len(active) == 97 == recorded["original_active_operational_qubits"], str(len(active))))
        checks.append(verdict(f"{basis}_holes", original.num_qubits - len(active) == 21 == recorded["original_unused_index_slots"], str(original.num_qubits - len(active))))
        checks.append(verdict(f"{basis}_compact_count", compacted.num_qubits == len(compact_active) == 97, str(compacted.num_qubits)))
        coordinate_binding = recorded["coordinate_canonicalization"]["all_active_qubits_bound"] and recorded["coordinate_canonicalization"]["unique_active_coordinates"]
        checks.append(verdict(f"{basis}_canonical", coordinate_binding and canonical_original == canonical_compacted and sha(canonical_original) == recorded["canonical_circuit_sha256"]["original"], sha(canonical_original)))
        checks.append(verdict(f"{basis}_dem", dem_original == dem_compacted and sha(dem_original) == recorded["detector_error_model_sha256"]["original"], sha(dem_original)))
        replay_fields = ["detectors_sha256", "observables_sha256", "predictions_sha256", "failure_vector_sha256", "trace_sha256"]
        replay_exact = all(replay_original[field] == replay_compacted[field] == recorded["fixed_seed_semantic_replay"]["original"][field] for field in replay_fields)
        checks.append(verdict(f"{basis}_semantic_replay", replay_exact, f"{audit_contract['audit_shots_per_basis']} shots."))
        checks.append(verdict(f"{basis}_challenge_binding", raw_seed_original != raw_seed_compacted and canonical_seed_original == canonical_seed_compacted == recorded["challenge_binding_audit"]["canonical_original_seed"], str(canonical_seed_original)))
        checks.append(verdict(f"{basis}_cost", len(active) * experiment["rounds"] == 97000 == recorded["cost_regrade"]["corrected_active_qubit_cost"], "97,000 active-qubit-rounds."))

    naive = math.sqrt(math.prod(row["cost_regrade"]["index_only_naive_improvement"] for row in rows.values()))
    invariant = math.sqrt(math.prod(row["cost_regrade"]["index_invariant_improvement"] for row in rows.values()))
    checks.append(verdict("naive_score", abs(naive - 118 / 97) < 1e-15 and naive == result["adversarial_relabel_candidate"]["naive_label_sensitive_composite_score"], str(naive)))
    checks.append(verdict("invariant_score", invariant == 1.0 == result["adversarial_relabel_candidate"]["index_invariant_composite_score"], str(invariant)))
    checks.append(verdict("pair_cost", result["reference_regrade"]["corrected_pair_cost"] == 194000, "194,000."))
    checks.append(verdict("candidate_threshold", result["reference_regrade"]["symmetric_candidate_max_active_qubits_at_1000_rounds"] == 77, "At most 77 active qubits."))
    recomputed_run_id = sha(stable_bytes({key: value for key, value in result.items() if key != "run_id"}))
    checks.append(verdict("run_id", result["run_id"] == recomputed_run_id, recomputed_run_id))
    checks.append(verdict("producer_checks", result["summary"]["checks_failed"] == 0 and result["summary"]["checks_passed"] == result["summary"]["checks_total"], f"{result['summary']['checks_passed']}/{result['summary']['checks_total']}"))
    checks.append(verdict("readiness", not result["readiness"]["b2_candidate_improvement_verified"] and not result["readiness"]["p023_scalable_memory_verified"] and result["readiness"]["b7_resource_credit"] == 0, "B2/#023/B7 remain closed."))
    checks.append(verdict("decision", result["decision"] == "qubit_index_loophole_closed_reference_regraded_to_97_active_qubits_b2_p023_b7_credit_closed", result["decision"]))
    summary = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "basis_count": len(independently_recomputed),
    }
    output = {
        "schema_version": "b2_b7_p023_qubit_index_invariance_independent_audit_v1",
        "as_of_date": protocol["as_of_date"],
        "source_result": {"path": str(result_path.relative_to(ROOT)), "sha256": file_sha(result_path)},
        "auditor": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": file_sha(Path(__file__).resolve())},
        "environment": {
            "python": platform.python_version(),
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
        },
        "independently_recomputed": independently_recomputed,
        "checks": checks,
        "summary": summary,
    }
    if summary["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"independent audit failed: {failed}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = audit(args.protocol, args.result)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
