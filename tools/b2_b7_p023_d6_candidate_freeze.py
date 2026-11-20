#!/usr/bin/env python3
"""Freeze the distance-6 QEC candidate before any stochastic acceptance run."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import stim


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_candidate_freeze_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_candidate_freeze_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_candidate_freeze_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_d6_candidate_freeze_discussion_v1.md"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_path(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def build_circuit(basis: str, candidate: dict[str, Any]) -> stim.Circuit:
    noise = candidate["noise_parameters"]
    return stim.Circuit.generated(
        f"surface_code:rotated_memory_{basis}",
        distance=candidate["distance"],
        rounds=candidate["rounds"],
        after_clifford_depolarization=noise["after_clifford_depolarization"],
        before_round_data_depolarization=noise["before_round_data_depolarization"],
        before_measure_flip_probability=noise["before_measure_flip_probability"],
        after_reset_flip_probability=noise["after_reset_flip_probability"],
    )


def qubit_value(target: stim.GateTarget) -> int | None:
    if (
        target.is_qubit_target
        or target.is_inverted_result_target
        or target.is_x_target
        or target.is_y_target
        or target.is_z_target
    ):
        return target.value
    return None


def active_ids(circuit: stim.Circuit) -> list[int]:
    values: set[int] = set()

    def visit(block: stim.Circuit) -> None:
        for item in block:
            if isinstance(item, stim.CircuitRepeatBlock):
                visit(item.body_copy())
                continue
            if item.name == "QUBIT_COORDS":
                continue
            for target in item.targets_copy():
                value = qubit_value(target)
                if value is not None:
                    values.add(value)

    visit(circuit)
    return sorted(values)


def coordinates(circuit: stim.Circuit) -> dict[int, tuple[float, ...]]:
    values: dict[int, tuple[float, ...]] = {}
    for item in circuit:
        if isinstance(item, stim.CircuitRepeatBlock) or item.name != "QUBIT_COORDS":
            continue
        targets = [target.value for target in item.targets_copy() if target.is_qubit_target]
        if len(targets) != 1:
            raise ValueError("QUBIT_COORDS must bind exactly one qubit")
        values[targets[0]] = tuple(item.gate_args_copy())
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


def remap_circuit(circuit: stim.Circuit, mapping: dict[int, int]) -> stim.Circuit:
    output = stim.Circuit()
    for item in circuit:
        if isinstance(item, stim.CircuitRepeatBlock):
            output.append(stim.CircuitRepeatBlock(item.repeat_count, remap_circuit(item.body_copy(), mapping)))
        else:
            output.append(
                item.name,
                [remap_target(target, mapping) for target in item.targets_copy()],
                item.gate_args_copy(),
            )
    return output


def coordinate_canonical(circuit: stim.Circuit) -> tuple[stim.Circuit, dict[int, int]]:
    active = active_ids(circuit)
    coords = coordinates(circuit)
    if any(qubit not in coords for qubit in active):
        raise ValueError("every active qubit needs coordinates")
    active_coords = [coords[qubit] for qubit in active]
    if len(set(active_coords)) != len(active_coords):
        raise ValueError("active coordinates must be unique")
    ordered = sorted(active, key=lambda qubit: coords[qubit])
    mapping = {old: new for new, old in enumerate(ordered)}
    return remap_circuit(circuit, mapping), mapping


def build_result(protocol: dict[str, Any], protocol_path: Path) -> dict[str, Any]:
    if protocol["scope"]["included_catalog_problem_ids"] != [21, 22, 23]:
        raise ValueError("scope mismatch")
    freeze_commit = protocol["frozen_inputs"]["artifact_freeze_commit"]
    current_bindings: dict[str, Any] = {}
    commit_bindings: dict[str, Any] = {}
    for name, binding in protocol["frozen_inputs"].items():
        if name == "artifact_freeze_commit":
            continue
        path = ROOT / binding["path"]
        current_sha = digest_path(path)
        if current_sha != binding["sha256"]:
            raise ValueError(f"current frozen input mismatch: {name}")
        commit_bytes = subprocess.check_output(["git", "show", f"{freeze_commit}:{binding['path']}"], cwd=ROOT)
        commit_sha = digest_bytes(commit_bytes)
        if commit_sha != binding["sha256"]:
            raise ValueError(f"commit frozen input mismatch: {name}")
        current_bindings[name] = {"path": binding["path"], "sha256": current_sha}
        commit_bindings[name] = {"path": binding["path"], "sha256": commit_sha, "matches": True}

    metric_result = read(ROOT / protocol["frozen_inputs"]["index_invariance_result"]["path"])
    strict_result = read(ROOT / protocol["frozen_inputs"]["strict_reference_result"]["path"])
    if metric_result["decision"] != protocol["frozen_inputs"]["index_invariance_result"]["required_decision"]:
        raise ValueError("metric decision mismatch")
    if strict_result["decision"] != protocol["frozen_inputs"]["strict_reference_result"]["required_decision"]:
        raise ValueError("strict reference decision mismatch")

    candidate = protocol["candidate"]
    rows: list[dict[str, Any]] = []
    for basis in candidate["memory_bases"]:
        circuit = build_circuit(basis, candidate)
        canonical_circuit, mapping = coordinate_canonical(circuit)
        dem = circuit.detector_error_model(decompose_errors=True)
        matching = pymatching.Matching.from_detector_error_model(dem)
        active = active_ids(circuit)
        coords = coordinates(circuit)
        rows.append(
            {
                "memory_basis": basis,
                "distance": candidate["distance"],
                "rounds": candidate["rounds"],
                "physical_error": candidate["physical_error"],
                "index_span_qubits": circuit.num_qubits,
                "active_operational_qubits": len(active),
                "unused_index_slots": circuit.num_qubits - len(active),
                "active_ids_sha256": digest_bytes(compact(active)),
                "coordinate_count": len(coords),
                "unique_coordinate_count": len(set(coords.values())),
                "coordinate_mapping_sha256": digest_bytes(compact(mapping)),
                "raw_circuit_sha256": digest_bytes(str(circuit).encode()),
                "coordinate_canonical_circuit_sha256": digest_bytes(str(canonical_circuit).encode()),
                "detector_error_model_sha256": digest_bytes(str(dem).encode()),
                "detectors": circuit.num_detectors,
                "observables": circuit.num_observables,
                "matching_nodes": matching.num_nodes,
                "matching_edges": matching.num_edges,
                "cost_active_qubit_rounds": len(active) * candidate["rounds"],
                "conditional_basis_improvement": metric_result["reference_regrade"]["corrected_active_qubit_cost_by_basis"][basis] / (len(active) * candidate["rounds"]),
                "stochastic_shots": 0,
                "logical_failures_observed": None,
                "acceptance_seed": None,
                "strict_verification_pass": None,
            }
        )

    conditional_score = math.sqrt(math.prod(row["conditional_basis_improvement"] for row in rows))
    result: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_candidate_freeze_result_v1",
        "as_of_date": protocol["as_of_date"],
        "question": protocol["question"],
        "scope": protocol["scope"],
        "protocol_binding": {"path": str(protocol_path.relative_to(ROOT)), "sha256": digest_path(protocol_path)},
        "frozen_inputs_current": current_bindings,
        "frozen_inputs_at_commit": {"commit": freeze_commit, "bindings": commit_bindings},
        "generator": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest_path(Path(__file__).resolve())},
        "execution_environment": {
            "python": platform.python_version(),
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "selection_rule": candidate["selection_rule"],
        "candidate": candidate,
        "candidate_rows": rows,
        "conditional_resource_score": {
            "reference_cost_per_basis": 97000,
            "candidate_cost_per_basis": 71000,
            "basis_improvement": {row["memory_basis"]: row["conditional_basis_improvement"] for row in rows},
            "composite_score_if_both_bases_verify": conditional_score,
            "acceptance_threshold": 1.25,
            "resource_threshold_cleared_conditionally": conditional_score >= 1.25,
            "correctness_gate_pending": True,
            "accepted_score_before_correctness": 0,
        },
        "post_freeze_acceptance_contract": protocol["post_freeze_acceptance_contract"],
        "pre_outcome_integrity": protocol["pre_outcome_integrity"],
        "readiness": {
            "candidate_structure_frozen": True,
            "candidate_public_freeze_commit_pending": True,
            "acceptance_salt_revealed": False,
            "candidate_correctness_tested": False,
            "candidate_accepted": False,
            "b2_candidate_improvement_verified": False,
            "p023_scalable_memory_verified": False,
            "b7_resource_credit": 0,
        },
        "claim_boundary": protocol["claim_boundary"],
        "decision": "distance6_candidate_structurally_frozen_before_salt_no_outcome_b2_p023_b7_credit_closed",
        "next_gate": "Commit and publish this exact packet, bind the resulting commit into a new acceptance salt, then execute 102,400 strict shots per basis without changing the candidate or thresholds.",
    }

    checks: list[dict[str, Any]] = []
    checks.append(check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23] and protocol["scope"]["included_tracks"] == ["B2", "B7"], "Exact scope."))
    checks.append(check("frozen_current", len(current_bindings) == 4, "Four frozen inputs match."))
    checks.append(check("frozen_commit", all(binding["matches"] for binding in commit_bindings.values()), freeze_commit))
    checks.append(check("metric_decision", metric_result["decision"] == protocol["frozen_inputs"]["index_invariance_result"]["required_decision"], metric_result["decision"]))
    checks.append(check("strict_reference", strict_result["reference_gate"]["both_bases_strict_pass"], "Strict d7 reference passed both bases."))
    checks.append(check("candidate_bases", [row["memory_basis"] for row in rows] == ["x", "z"], "X and Z are frozen."))
    checks.append(check("candidate_distance", all(row["distance"] == 6 for row in rows), "Distance 6."))
    checks.append(check("candidate_horizon", all(row["rounds"] == 1000 for row in rows), "Exactly 1,000 rounds."))
    checks.append(check("active_qubits", all(row["active_operational_qubits"] == 71 for row in rows), "71 active operational qubits per basis."))
    checks.append(check("index_span_diagnostic", all(row["index_span_qubits"] == 89 and row["unused_index_slots"] == 18 for row in rows), "89-slot span with 18 holes."))
    checks.append(check("coordinate_binding", all(row["coordinate_count"] == row["unique_coordinate_count"] == row["active_operational_qubits"] for row in rows), "All active qubits have unique coordinates."))
    checks.append(check("candidate_cost", all(row["cost_active_qubit_rounds"] == 71000 for row in rows), "71,000 active-qubit-rounds per basis."))
    checks.append(check("conditional_score", abs(conditional_score - 97 / 71) < 1e-15 and conditional_score >= 1.25, str(conditional_score)))
    checks.append(check("no_shots", all(row["stochastic_shots"] == 0 for row in rows) and protocol["pre_outcome_integrity"]["candidate_stochastic_shots_before_freeze"] == 0, "No stochastic candidate shots."))
    checks.append(check("no_outcome", all(row["logical_failures_observed"] is None and row["strict_verification_pass"] is None for row in rows), "No candidate outcome observed."))
    checks.append(check("no_seed", all(row["acceptance_seed"] is None for row in rows) and not protocol["post_freeze_acceptance_contract"]["seed_present_in_freeze_packet"], "No acceptance seed."))
    checks.append(check("no_salt", not protocol["post_freeze_acceptance_contract"]["salt_present_in_freeze_packet"], "No acceptance salt."))
    checks.append(check("zero_pre_correctness_score", result["conditional_resource_score"]["accepted_score_before_correctness"] == 0, "Score remains zero before correctness."))
    checks.append(check("candidate_unaccepted", not result["readiness"]["candidate_accepted"] and not result["readiness"]["b2_candidate_improvement_verified"], "Candidate remains unaccepted."))
    checks.append(check("downstream_closed", not result["readiness"]["p023_scalable_memory_verified"] and result["readiness"]["b7_resource_credit"] == 0, "#023 and B7 remain closed."))
    checks.append(check("claim_boundary", not any(protocol["claim_boundary"].values()), "No positive claim before execution."))
    result["formal_checks"] = checks
    result["summary"] = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "candidate_active_qubits": 71,
        "candidate_cost_per_basis": 71000,
        "conditional_score": conditional_score,
        "stochastic_shots_before_freeze": 0,
        "candidate_correctness_tested": False,
        "candidate_accepted": False,
    }
    result["run_id"] = digest_bytes(compact({key: value for key, value in result.items() if key != "run_id"}))
    if result["summary"]["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"freeze checks failed: {failed}")
    return result


def build_report(result: dict[str, Any]) -> str:
    x, z = result["candidate_rows"]
    score = result["conditional_resource_score"]
    return "\n".join(
        [
            "# B2/B7/#023 Distance-6 Candidate Freeze v1",
            "",
            f"As of {result['as_of_date']}. Scope is exactly #021/B7, #022/B2, and #023.",
            "",
            "## Heuristic question",
            "",
            "Can 26 fewer active qubits preserve the strict 1,000-round X/Z reliability of the verified distance-7 reference? This packet freezes that question before looking at one candidate sample.",
            "",
            "## Candidate selected without outcome data",
            "",
            "The nearest lower-distance member of the same Stim rotated-surface-code family is distance 6. It uses 71 active operational qubits versus the corrected reference's 97, at the same 1,000 rounds, physical error 0.001, circuit-level noise model, and PyMatching MWPM decoder.",
            "",
            "| basis | distance | index span | active qubits | detectors | cost | raw circuit hash | canonical hash |",
            "|---|---:|---:|---:|---:|---:|---|---|",
            f"| X | 6 | {x['index_span_qubits']} | {x['active_operational_qubits']} | {x['detectors']} | {x['cost_active_qubit_rounds']:,} | `{x['raw_circuit_sha256'][:16]}…` | `{x['coordinate_canonical_circuit_sha256'][:16]}…` |",
            f"| Z | 6 | {z['index_span_qubits']} | {z['active_operational_qubits']} | {z['detectors']} | {z['cost_active_qubit_rounds']:,} | `{z['raw_circuit_sha256'][:16]}…` | `{z['coordinate_canonical_circuit_sha256'][:16]}…` |",
            "",
            f"If—and only if—both bases pass the frozen correctness gate, the resource score is `97/71 = {score['composite_score_if_both_bases_verify']:.9f}`, above the 1.25 threshold. Before correctness, the accepted score is 0.",
            "",
            "## What is deliberately absent",
            "",
            "- candidate stochastic shots: 0",
            "- observed candidate logical failures: none",
            "- acceptance salt: absent",
            "- acceptance seeds: absent",
            "- candidate pass/fail decision: absent",
            "",
            "The packet permits only deterministic circuit construction, coordinate-canonical hashing, DEM construction, and matching-graph dimension inspection before the public freeze.",
            "",
            "## Post-freeze gate",
            "",
            "After this exact packet is committed and published, bind that commit into the acceptance salt and run 102,400 shots per basis. Both one-sided Clopper–Pearson upper bounds at confidence `1-2^-128` must be at most 1%; otherwise the candidate score is 0.",
            "",
            "## Claim boundary",
            "",
            "This is a preregistered candidate, not an accepted code, B2 improvement, scalable #023 memory, threshold result, hardware result, or B7 credit.",
            "",
            f"Formal checks: **{result['summary']['checks_passed']}/{result['summary']['checks_total']}**. Run ID: `{result['run_id']}`.",
            "",
        ]
    )


def build_discussion(result: dict[str, Any]) -> str:
    score = result["conditional_resource_score"]["composite_score_if_both_bases_verify"]
    return "\n".join(
        [
            "Can a 71-qubit memory keep the reliability of a 97-qubit reference?",
            "",
            "For #021/B7 · #022/B2 · #023, we have frozen the first candidate under the corrected verifier—before observing any candidate failures.",
            "",
            "The candidate is the distance-6 member of the same rotated-surface-code family: 71 active qubits, 1,000 rounds, physical error 0.001, identical circuit-level noise channels, and the same PyMatching MWPM decoder. The verified distance-7 reference uses 97 active qubits.",
            "",
            f"If both X and Z pass the strict correctness gate, its conditional resource score is **97/71 = {score:.4f}×**, above the frozen 1.25 threshold. If either basis fails, its accepted score is zero.",
            "",
            "At publication time this packet contains:",
            "",
            "- 0 stochastic candidate shots",
            "- no logical-failure observation",
            "- no acceptance salt or seed",
            "- no candidate pass/fail claim",
            "",
            "Questions before execution:",
            "",
            "- Is even distance 6 a scientifically fair same-family candidate, or should the benchmark restrict to odd distances?",
            "- Does holding the decoder family fixed isolate overhead cleanly enough?",
            "- Should a candidate need 1.25× geometric improvement, or a larger margin for model risk?",
            "- What failure result would most strongly falsify the belief that distance 6 is near the strict 1% boundary?",
            "",
            "Next: bind the public freeze commit into a newly revealed salt and run exactly 102,400 X plus 102,400 Z shots without changing any threshold.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_result(read(args.protocol), args.protocol)
    args.output.write_text(canonical(result), encoding="utf-8")
    args.report.write_text(build_report(result), encoding="utf-8")
    args.discussion.write_text(build_discussion(result), encoding="utf-8")
    print(canonical(result["summary"]).strip())


if __name__ == "__main__":
    main()
