#!/usr/bin/env python3
"""Independent no-outcome audit of the frozen distance-6 QEC candidate."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import pymatching
import stim


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_candidate_freeze_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_candidate_freeze_v1.json"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_candidate_freeze_audit_v1.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def circuit_for(basis: str, spec: dict[str, Any]) -> stim.Circuit:
    noise = spec["noise_parameters"]
    return stim.Circuit.generated(
        "surface_code:rotated_memory_" + basis,
        distance=spec["distance"],
        rounds=spec["rounds"],
        after_clifford_depolarization=noise["after_clifford_depolarization"],
        before_round_data_depolarization=noise["before_round_data_depolarization"],
        before_measure_flip_probability=noise["before_measure_flip_probability"],
        after_reset_flip_probability=noise["after_reset_flip_probability"],
    )


def target_value(target: stim.GateTarget) -> int | None:
    return target.value if any((target.is_qubit_target, target.is_inverted_result_target, target.is_x_target, target.is_y_target, target.is_z_target)) else None


def independent_active(circuit: stim.Circuit) -> list[int]:
    values: set[int] = set()
    for operation in circuit.flattened():
        if operation.name == "QUBIT_COORDS":
            continue
        for target in operation.targets_copy():
            value = target_value(target)
            if value is not None:
                values.add(value)
    return sorted(values)


def independent_coordinates(circuit: stim.Circuit) -> dict[int, tuple[float, ...]]:
    values: dict[int, tuple[float, ...]] = {}
    for operation in circuit.flattened():
        if operation.name != "QUBIT_COORDS":
            continue
        targets = [target.value for target in operation.targets_copy() if target.is_qubit_target]
        if len(targets) != 1:
            raise ValueError("invalid coordinate binding")
        values[targets[0]] = tuple(operation.gate_args_copy())
    return values


def remap_target(target: stim.GateTarget, mapping: dict[int, int]) -> int | stim.GateTarget:
    if target.is_x_target:
        return stim.target_x(mapping[target.value])
    if target.is_y_target:
        return stim.target_y(mapping[target.value])
    if target.is_z_target:
        return stim.target_z(mapping[target.value])
    if target.is_inverted_result_target:
        return stim.target_inv(mapping[target.value])
    if target.is_qubit_target:
        return mapping[target.value]
    return target


def canonical_by_coordinates(circuit: stim.Circuit) -> stim.Circuit:
    active = independent_active(circuit)
    coords = independent_coordinates(circuit)
    if any(qubit not in coords for qubit in active):
        raise ValueError("missing coordinate")
    if len({coords[qubit] for qubit in active}) != len(active):
        raise ValueError("duplicate coordinate")
    mapping = {old: new for new, old in enumerate(sorted(active, key=lambda qubit: coords[qubit]))}

    def translate(block: stim.Circuit) -> stim.Circuit:
        output = stim.Circuit()
        for operation in block:
            if isinstance(operation, stim.CircuitRepeatBlock):
                output.append(stim.CircuitRepeatBlock(operation.repeat_count, translate(operation.body_copy())))
            else:
                output.append(operation.name, [remap_target(target, mapping) for target in operation.targets_copy()], operation.gate_args_copy())
        return output

    return translate(circuit)


def stochastic_calls(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    forbidden = {"sample", "compile_detector_sampler", "compile_sampler", "sample_write"}
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in forbidden:
            found.append(node.func.attr)
    return sorted(found)


def audit(protocol_path: Path, result_path: Path) -> dict[str, Any]:
    protocol = load(protocol_path)
    result = load(result_path)
    checks: list[dict[str, Any]] = []
    checks.append(check("schema", result["schema_version"] == "b2_b7_p023_d6_candidate_freeze_result_v1", result["schema_version"]))
    checks.append(check("scope", result["scope"]["included_catalog_problem_ids"] == [21, 22, 23] and result["scope"]["included_tracks"] == ["B2", "B7"], "Exact scope."))
    checks.append(check("protocol_hash", result["protocol_binding"]["sha256"] == file_sha(protocol_path), file_sha(protocol_path)))
    generator_path = ROOT / result["generator"]["path"]
    checks.append(check("generator_hash", result["generator"]["sha256"] == file_sha(generator_path), file_sha(generator_path)))
    calls = stochastic_calls(generator_path)
    checks.append(check("no_stochastic_generator_calls", calls == [], str(calls)))
    bindings_ok = all(file_sha(ROOT / binding["path"]) == binding["sha256"] for name, binding in protocol["frozen_inputs"].items() if name != "artifact_freeze_commit")
    checks.append(check("frozen_inputs", bindings_ok, "All four frozen hashes match."))
    metric = load(ROOT / protocol["frozen_inputs"]["index_invariance_result"]["path"])
    strict = load(ROOT / protocol["frozen_inputs"]["strict_reference_result"]["path"])
    checks.append(check("metric_decision", metric["decision"] == protocol["frozen_inputs"]["index_invariance_result"]["required_decision"], metric["decision"]))
    checks.append(check("strict_reference", strict["reference_gate"]["both_bases_strict_pass"], "Reference passes X/Z."))
    rows = {row["memory_basis"]: row for row in result["candidate_rows"]}
    independently_recomputed: list[dict[str, Any]] = []
    for basis in ("x", "z"):
        circuit = circuit_for(basis, protocol["candidate"])
        active = independent_active(circuit)
        coords = independent_coordinates(circuit)
        canonical = canonical_by_coordinates(circuit)
        dem = circuit.detector_error_model(decompose_errors=True)
        matching = pymatching.Matching.from_detector_error_model(dem)
        record = {
            "memory_basis": basis,
            "raw_circuit_sha256": sha(str(circuit).encode()),
            "canonical_circuit_sha256": sha(str(canonical).encode()),
            "detector_error_model_sha256": sha(str(dem).encode()),
            "index_span_qubits": circuit.num_qubits,
            "active_operational_qubits": len(active),
            "coordinate_count": len(coords),
            "detectors": circuit.num_detectors,
            "matching_nodes": matching.num_nodes,
            "matching_edges": matching.num_edges,
            "cost": len(active) * protocol["candidate"]["rounds"],
        }
        independently_recomputed.append(record)
        expected = rows[basis]
        checks.append(check(f"{basis}_circuit", record["raw_circuit_sha256"] == expected["raw_circuit_sha256"], record["raw_circuit_sha256"]))
        checks.append(check(f"{basis}_canonical", record["canonical_circuit_sha256"] == expected["coordinate_canonical_circuit_sha256"], record["canonical_circuit_sha256"]))
        checks.append(check(f"{basis}_dem", record["detector_error_model_sha256"] == expected["detector_error_model_sha256"], record["detector_error_model_sha256"]))
        checks.append(check(f"{basis}_qubits", record["index_span_qubits"] == 89 and record["active_operational_qubits"] == 71 and record["coordinate_count"] == 71, str(record["active_operational_qubits"])))
        checks.append(check(f"{basis}_dimensions", record["detectors"] == expected["detectors"] and record["matching_nodes"] == expected["matching_nodes"] and record["matching_edges"] == expected["matching_edges"], f"{record['detectors']} detectors."))
        checks.append(check(f"{basis}_cost", record["cost"] == expected["cost_active_qubit_rounds"] == 71000, "71,000."))
        checks.append(check(f"{basis}_no_outcome", expected["stochastic_shots"] == 0 and expected["logical_failures_observed"] is None and expected["acceptance_seed"] is None and expected["strict_verification_pass"] is None, "No stochastic outcome fields."))

    conditional_score = math.sqrt(math.prod(rows[basis]["conditional_basis_improvement"] for basis in ("x", "z")))
    checks.append(check("conditional_score", abs(conditional_score - 97 / 71) < 1e-15 and conditional_score == result["conditional_resource_score"]["composite_score_if_both_bases_verify"], str(conditional_score)))
    checks.append(check("score_zero_before_correctness", result["conditional_resource_score"]["accepted_score_before_correctness"] == 0 and result["conditional_resource_score"]["correctness_gate_pending"], "Correctness is pending."))
    checks.append(check("salt_absent", not protocol["post_freeze_acceptance_contract"]["salt_present_in_freeze_packet"] and not result["readiness"]["acceptance_salt_revealed"], "Salt absent."))
    checks.append(check("claim_boundary", not any(protocol["claim_boundary"].values()), "All positive claims false."))
    checks.append(check("downstream_closed", not result["readiness"]["candidate_accepted"] and not result["readiness"]["b2_candidate_improvement_verified"] and not result["readiness"]["p023_scalable_memory_verified"] and result["readiness"]["b7_resource_credit"] == 0, "Candidate/B2/#023/B7 remain closed."))
    recomputed_run_id = sha(stable({key: value for key, value in result.items() if key != "run_id"}))
    checks.append(check("run_id", result["run_id"] == recomputed_run_id, recomputed_run_id))
    checks.append(check("producer_checks", result["summary"]["checks_failed"] == 0 and result["summary"]["checks_passed"] == result["summary"]["checks_total"], f"{result['summary']['checks_passed']}/{result['summary']['checks_total']}"))
    summary = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "basis_count": 2,
        "stochastic_generator_calls": len(calls),
    }
    output = {
        "schema_version": "b2_b7_p023_d6_candidate_freeze_independent_audit_v1",
        "source_result": {"path": str(result_path.relative_to(ROOT)), "sha256": file_sha(result_path)},
        "auditor": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": file_sha(Path(__file__).resolve())},
        "independently_recomputed": independently_recomputed,
        "checks": checks,
        "summary": summary,
    }
    if summary["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"freeze audit failed: {failed}")
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
