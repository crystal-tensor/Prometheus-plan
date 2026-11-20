#!/usr/bin/env python3
"""Independent audit of the frozen distance-6 strict QEC result."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import scipy
from scipy.optimize import brentq
from scipy.stats import binom
import stim


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_strict_acceptance_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_strict_acceptance_v1.json"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_strict_acceptance_audit_v1.json"
DELTA = 2.0 ** -128


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


def independent_cp_upper(failures: int, shots: int) -> float:
    if failures >= shots:
        return 1.0
    return float(
        brentq(
            lambda probability: binom.logcdf(failures, shots, probability) - math.log(DELTA),
            failures / shots,
            1.0 - 1e-15,
            xtol=1e-14,
            rtol=1e-14,
        )
    )


def circuit_for(basis: str, execution: dict[str, Any]) -> stim.Circuit:
    noise = execution["noise_parameters"]
    return stim.Circuit.generated(
        "surface_code:rotated_memory_" + basis,
        distance=execution["distance"],
        rounds=execution["rounds"],
        after_clifford_depolarization=noise["after_clifford_depolarization"],
        before_round_data_depolarization=noise["before_round_data_depolarization"],
        before_measure_flip_probability=noise["before_measure_flip_probability"],
        after_reset_flip_probability=noise["after_reset_flip_probability"],
    )


def target_value(target: stim.GateTarget) -> int | None:
    return target.value if any((target.is_qubit_target, target.is_inverted_result_target, target.is_x_target, target.is_y_target, target.is_z_target)) else None


def active(circuit: stim.Circuit) -> list[int]:
    values: set[int] = set()
    for operation in circuit.flattened():
        if operation.name == "QUBIT_COORDS":
            continue
        for target in operation.targets_copy():
            value = target_value(target)
            if value is not None:
                values.add(value)
    return sorted(values)


def coords(circuit: stim.Circuit) -> dict[int, tuple[float, ...]]:
    values: dict[int, tuple[float, ...]] = {}
    for operation in circuit.flattened():
        if operation.name != "QUBIT_COORDS":
            continue
        targets = [target.value for target in operation.targets_copy() if target.is_qubit_target]
        if len(targets) != 1:
            raise ValueError("invalid coordinate instruction")
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


def canonical_circuit(circuit: stim.Circuit) -> stim.Circuit:
    identifiers = active(circuit)
    coordinates = coords(circuit)
    if any(identifier not in coordinates for identifier in identifiers):
        raise ValueError("missing coordinate")
    if len({coordinates[identifier] for identifier in identifiers}) != len(identifiers):
        raise ValueError("duplicate coordinate")
    mapping = {old: new for new, old in enumerate(sorted(identifiers, key=lambda identifier: coordinates[identifier]))}

    def translate(block: stim.Circuit) -> stim.Circuit:
        output = stim.Circuit()
        for operation in block:
            if isinstance(operation, stim.CircuitRepeatBlock):
                output.append(stim.CircuitRepeatBlock(operation.repeat_count, translate(operation.body_copy())))
            else:
                output.append(operation.name, [remap_target(target, mapping) for target in operation.targets_copy()], operation.gate_args_copy())
        return output

    return translate(circuit)


def seed_for(salt: str, circuit: stim.Circuit) -> tuple[int, str]:
    digest = hashlib.sha256(salt.encode() + b"\x00" + str(canonical_circuit(circuit)).encode()).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1), digest.hex()


def strip_timing(value: Any) -> Any:
    copied = copy.deepcopy(value)
    if isinstance(copied, dict):
        copied.pop("timing", None)
        for key in list(copied):
            copied[key] = strip_timing(copied[key])
    elif isinstance(copied, list):
        copied = [strip_timing(item) for item in copied]
    return copied


def audit(protocol_path: Path, result_path: Path) -> dict[str, Any]:
    protocol = load(protocol_path)
    result = load(result_path)
    execution = protocol["execution"]
    rows = result["candidate_rows"]
    freeze_commit = protocol["frozen_inputs"]["artifact_freeze_commit"]
    freeze_result = load(ROOT / protocol["frozen_inputs"]["candidate_freeze_result"]["path"])
    freeze_rows = {row["memory_basis"]: row for row in freeze_result["candidate_rows"]}
    regenerated: list[dict[str, Any]] = []
    for row in rows:
        circuit = circuit_for(row["memory_basis"], execution)
        dem = circuit.detector_error_model(decompose_errors=True)
        matching = pymatching.Matching.from_detector_error_model(dem)
        seed, challenge_hash = seed_for(execution["challenge_salt"], circuit)
        regenerated.append(
            {
                "memory_basis": row["memory_basis"],
                "raw_circuit_sha256": sha(str(circuit).encode()),
                "canonical_circuit_sha256": sha(str(canonical_circuit(circuit)).encode()),
                "dem_sha256": sha(str(dem).encode()),
                "seed": seed,
                "challenge_hash": challenge_hash,
                "index_span": circuit.num_qubits,
                "active_qubits": len(active(circuit)),
                "detectors": circuit.num_detectors,
                "observables": circuit.num_observables,
                "matching_nodes": matching.num_nodes,
                "matching_edges": matching.num_edges,
            }
        )
    independent_bounds = {row["memory_basis"]: independent_cp_upper(row["logical_failures"], row["shots"]) for row in rows}
    target = execution["target_total_logical_failure"]
    strict_flags = {basis: value <= target for basis, value in independent_bounds.items()}
    both_strict = all(strict_flags.values())
    basis_improvement = {row["memory_basis"]: 97000 / row["cost_active_qubit_rounds"] for row in rows}
    conditional_score = math.sqrt(math.prod(basis_improvement.values()))
    accepted_score = conditional_score if both_strict else 0
    candidate_accepted = both_strict and conditional_score >= 1.25 and all(value >= 1 for value in basis_improvement.values())
    expected_decision = "d6_candidate_strictly_accepted_b2_improvement_verified_p023_b7_credit_closed" if candidate_accepted else "d6_candidate_rejected_by_strict_xz_gate_score_zero_p023_b2_b7_credit_closed"
    frozen_commit_hashes: dict[str, str] = {}
    for name, binding in protocol["frozen_inputs"].items():
        if name == "artifact_freeze_commit":
            continue
        frozen_commit_hashes[name] = sha(subprocess.check_output(["git", "show", f"{freeze_commit}:{binding['path']}"], cwd=ROOT))
    versions = {
        "python": platform.python_version(),
        "stim": stim.__version__,
        "pymatching": pymatching.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    checks: list[dict[str, Any]] = []
    checks.append(check("schema", result["schema_version"] == "b2_b7_p023_d6_strict_acceptance_result_v1", result["schema_version"]))
    checks.append(check("scope", result["scope"] == protocol["scope"] and result["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact scope."))
    checks.append(check("protocol_hash", result["protocol_binding"]["sha256"] == file_sha(protocol_path), file_sha(protocol_path)))
    checks.append(check("generator_hash", result["generator"]["sha256"] == file_sha(ROOT / result["generator"]["path"]), result["generator"]["sha256"]))
    checks.append(check("current_inputs", all(file_sha(ROOT / binding["path"]) == binding["sha256"] for name, binding in protocol["frozen_inputs"].items() if name != "artifact_freeze_commit"), "All current frozen inputs match."))
    checks.append(check("commit_inputs", all(frozen_commit_hashes[name] == protocol["frozen_inputs"][name]["sha256"] for name in frozen_commit_hashes), freeze_commit))
    checks.append(check("public_freeze", result["public_freeze"] == protocol["public_freeze"] and result["public_freeze"]["discussion_number"] == 323, result["public_freeze"]["commit"]))
    checks.append(check("freeze_pre_outcome", freeze_result["summary"]["stochastic_shots_before_freeze"] == 0 and not freeze_result["summary"]["candidate_correctness_tested"], "Candidate was frozen before outcomes."))
    checks.append(check("toolchain", versions == execution["toolchain"], str(versions)))
    checks.append(check("basis_set", [row["memory_basis"] for row in rows] == ["x", "z"], "X and Z rows."))
    checks.append(check("circuits", all(item["raw_circuit_sha256"] == rows[index]["raw_circuit_sha256"] == freeze_rows[item["memory_basis"]]["raw_circuit_sha256"] for index, item in enumerate(regenerated)), "Raw circuits reproduce and match freeze."))
    checks.append(check("canonical_circuits", all(item["canonical_circuit_sha256"] == rows[index]["coordinate_canonical_circuit_sha256"] == freeze_rows[item["memory_basis"]]["coordinate_canonical_circuit_sha256"] for index, item in enumerate(regenerated)), "Coordinate-canonical circuits reproduce."))
    checks.append(check("dem", all(item["dem_sha256"] == rows[index]["detector_error_model_sha256"] == freeze_rows[item["memory_basis"]]["detector_error_model_sha256"] for index, item in enumerate(regenerated)), "DEMs reproduce and match freeze."))
    checks.append(check("seeds", all(item["seed"] == rows[index]["seed"] and item["challenge_hash"] == rows[index]["challenge_hash_sha256"] for index, item in enumerate(regenerated)), "Canonical salt-derived seeds reproduce."))
    checks.append(check("dimensions", all(item["index_span"] == rows[index]["index_span_qubits"] == 89 and item["active_qubits"] == rows[index]["active_operational_qubits"] == 71 and item["detectors"] == rows[index]["detectors"] and item["observables"] == rows[index]["observables"] and item["matching_nodes"] == rows[index]["matching_nodes"] and item["matching_edges"] == rows[index]["matching_edges"] for index, item in enumerate(regenerated)), "Circuit and matching dimensions reproduce."))
    checks.append(check("direct_exposure", all(row["rounds"] == 1000 and row["shots"] == 102400 for row in rows), "102,400 direct 1,000-round shots per basis."))
    checks.append(check("failure_arithmetic", all(row["logical_error_rate"] == row["logical_failures"] / row["shots"] for row in rows), "Observed rates reproduce."))
    checks.append(check("independent_cp", all(math.isclose(row["clopper_pearson_upper_delta_2m128"], independent_bounds[row["memory_basis"]], abs_tol=2e-13, rel_tol=0) for row in rows), str(independent_bounds)))
    checks.append(check("strict_flags", all(row["strict_verification_pass"] == strict_flags[row["memory_basis"]] for row in rows), str(strict_flags)))
    checks.append(check("pair_gate", result["score"]["both_bases_strict_pass"] == both_strict, str(both_strict)))
    checks.append(check("chunk_coverage", all(len(row["chunk_digests"]) == 400 and sum(chunk["shots"] for chunk in row["chunk_digests"]) == row["shots"] for row in rows), "400 chunks per basis."))
    checks.append(check("chunk_shapes", all(all(chunk["detector_shape"] == [chunk["shots"], math.ceil(row["detectors"] / 8)] and chunk["observable_shape"] == [chunk["shots"], 1] and chunk["prediction_shape"] == [chunk["shots"], 1] for chunk in row["chunk_digests"]) for row in rows), "Packed shapes reproduce."))
    checks.append(check("hash_shapes", all(all(len(row[key]) == 64 for key in ["challenge_hash_sha256", "raw_circuit_sha256", "coordinate_canonical_circuit_sha256", "detector_error_model_sha256", "sample_prediction_trace_sha256", "failure_vector_sha256"]) for row in rows), "All primary hashes are SHA-256 shaped."))
    checks.append(check("costs", all(row["cost_active_qubit_rounds"] == 71000 for row in rows), "71,000 active-qubit-rounds."))
    checks.append(check("basis_improvement", result["score"]["basis_improvement"] == basis_improvement, str(basis_improvement)))
    checks.append(check("score", result["score"]["conditional_composite_score"] == conditional_score and result["score"]["accepted_composite_score"] == accepted_score and result["score"]["candidate_accepted"] == candidate_accepted, str({"conditional": conditional_score, "accepted": accepted_score})))
    checks.append(check("decision", result["decision"] == expected_decision, expected_decision))
    checks.append(check("summary", result["summary"]["total_shots"] == sum(row["shots"] for row in rows) and result["summary"]["total_logical_failures"] == sum(row["logical_failures"] for row in rows) and result["summary"]["candidate_accepted"] == candidate_accepted, "Summary reproduces."))
    checks.append(check("readiness", result["readiness"]["b2_candidate_improvement_verified"] == candidate_accepted and not result["readiness"]["p023_scalable_memory_verified"] and result["readiness"]["b7_resource_credit"] == 0, "B2 follows verdict; #023/B7 remain closed."))
    checks.append(check("claim_boundary", not result["claim_boundary"]["p023_scalable_memory_claimed"] and not result["claim_boundary"]["b7_resource_credit_claimed"] and not result["claim_boundary"]["hardware_result_claimed"], "No downstream overclaim."))
    recomputed_run_id = sha(stable(strip_timing({key: value for key, value in result.items() if key != "run_id"})))
    checks.append(check("run_id", result["run_id"] == recomputed_run_id, recomputed_run_id))
    checks.append(check("producer_checks", result["summary"]["checks_failed"] == 0 and all(item["passed"] for item in result["formal_checks"]), f"{result['summary']['checks_passed']}/{result['summary']['checks_total']}"))
    summary = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "both_bases_strict_pass": both_strict,
        "candidate_accepted": candidate_accepted,
    }
    output = {
        "schema_version": "b2_b7_p023_d6_strict_acceptance_independent_audit_v1",
        "source_result": {"path": str(result_path.relative_to(ROOT)), "sha256": file_sha(result_path)},
        "auditor": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": file_sha(Path(__file__).resolve())},
        "independent_cp_method": "solve log BinomialCDF(k;n,p)=log(2^-128) with Brent root finding, independent of producer beta inverse-survival",
        "independent_cp_upper_by_basis": independent_bounds,
        "regenerated": regenerated,
        "checks": checks,
        "summary": summary,
    }
    if summary["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"strict audit failed: {failed}")
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
