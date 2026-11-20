#!/usr/bin/env python3
"""Execute the post-freeze strict correlated-decoder distance-6 QEC run."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import scipy
from scipy.stats import beta
import stim


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_correlated_strict_acceptance_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_correlated_strict_acceptance_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_correlated_strict_acceptance_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_d6_correlated_strict_acceptance_discussion_v1.md"
DELTA = 2.0 ** -128


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


def clopper_pearson_upper(failures: int, shots: int) -> float:
    if failures >= shots:
        return 1.0
    return float(beta.isf(DELTA, failures + 1, shots - failures))


def wilson_upper(failures: int, shots: int) -> float:
    z = 1.959963984540054
    p = failures / shots
    denominator = 1 + z * z / shots
    center = (p + z * z / (2 * shots)) / denominator
    radius = z * math.sqrt((p * (1 - p) + z * z / (4 * shots)) / shots) / denominator
    return min(1.0, center + radius)


def build_circuit(basis: str, execution: dict[str, Any]) -> stim.Circuit:
    noise = execution["noise_parameters"]
    return stim.Circuit.generated(
        f"surface_code:rotated_memory_{basis}",
        distance=execution["distance"],
        rounds=execution["rounds"],
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
            raise ValueError("invalid QUBIT_COORDS instruction")
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
            output.append(item.name, [remap_target(target, mapping) for target in item.targets_copy()], item.gate_args_copy())
    return output


def coordinate_canonical(circuit: stim.Circuit) -> stim.Circuit:
    active = active_ids(circuit)
    coords = coordinates(circuit)
    if any(qubit not in coords for qubit in active):
        raise ValueError("every active qubit requires coordinates")
    if len({coords[qubit] for qubit in active}) != len(active):
        raise ValueError("coordinates must be unique")
    mapping = {old: new for new, old in enumerate(sorted(active, key=lambda qubit: coords[qubit]))}
    return remap_circuit(circuit, mapping)


def challenge_seed(salt: str, canonical_circuit_bytes: bytes) -> tuple[int, str]:
    digest = hashlib.sha256(salt.encode() + b"\x00" + canonical_circuit_bytes).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1), digest.hex()


def run_basis(basis: str, execution: dict[str, Any]) -> dict[str, Any]:
    circuit = build_circuit(basis, execution)
    canonical_circuit = coordinate_canonical(circuit)
    canonical_bytes = str(canonical_circuit).encode()
    seed, challenge_hash = challenge_seed(execution["challenge_salt"], canonical_bytes)
    started = time.perf_counter()
    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(
        dem,
        enable_correlations=True,
    )
    sampler = circuit.compile_detector_sampler(seed=seed)
    build_seconds = time.perf_counter() - started
    shots = execution["shots_per_basis"]
    chunk_size = execution["shot_chunk_size"]
    total_failures = 0
    sample_seconds = 0.0
    decode_seconds = 0.0
    trace_hasher = hashlib.sha256()
    failure_hasher = hashlib.sha256()
    chunks: list[dict[str, Any]] = []
    for chunk_index, offset in enumerate(range(0, shots, chunk_size)):
        chunk_shots = min(chunk_size, shots - offset)
        tick = time.perf_counter()
        detectors, observables = sampler.sample(
            chunk_shots,
            separate_observables=True,
            bit_packed=True,
        )
        sample_seconds += time.perf_counter() - tick
        tick = time.perf_counter()
        predictions = matching.decode_batch(
            detectors,
            bit_packed_shots=True,
            bit_packed_predictions=True,
            enable_correlations=True,
        )
        decode_seconds += time.perf_counter() - tick
        if predictions.shape != observables.shape:
            raise ValueError("prediction and observable shapes differ")
        failures = np.any(np.bitwise_xor(predictions, observables) != 0, axis=1).astype(np.uint8)
        total_failures += int(np.count_nonzero(failures))
        header = {
            "basis": basis,
            "chunk_index": chunk_index,
            "shot_offset": offset,
            "shots": chunk_shots,
            "detector_shape": list(detectors.shape),
            "observable_shape": list(observables.shape),
            "prediction_shape": list(predictions.shape),
        }
        payload = (
            compact(header)
            + b"\x00"
            + detectors.tobytes(order="C")
            + observables.tobytes(order="C")
            + predictions.tobytes(order="C")
        )
        trace_hasher.update(payload)
        failure_hasher.update(compact({"shot_offset": offset, "shots": chunk_shots}))
        failure_hasher.update(b"\x00")
        failure_hasher.update(failures.tobytes(order="C"))
        chunks.append({**header, "sha256": digest_bytes(payload)})

    strict_upper = clopper_pearson_upper(total_failures, shots)
    target = execution["target_total_logical_failure"]
    active = active_ids(circuit)
    return {
        "memory_basis": basis,
        "distance": execution["distance"],
        "rounds": execution["rounds"],
        "physical_error": execution["physical_error"],
        "shots": shots,
        "seed": seed,
        "challenge_hash_sha256": challenge_hash,
        "index_span_qubits": circuit.num_qubits,
        "active_operational_qubits": len(active),
        "active_ids_sha256": digest_bytes(compact(active)),
        "cost_active_qubit_rounds": len(active) * execution["rounds"],
        "detectors": circuit.num_detectors,
        "observables": circuit.num_observables,
        "matching_nodes": matching.num_nodes,
        "matching_edges": matching.num_edges,
        "correlations_enabled_at_construction": True,
        "correlations_enabled_at_decode": True,
        "raw_circuit_sha256": digest_bytes(str(circuit).encode()),
        "coordinate_canonical_circuit_sha256": digest_bytes(canonical_bytes),
        "detector_error_model_sha256": digest_bytes(str(dem).encode()),
        "logical_failures": total_failures,
        "logical_error_rate": total_failures / shots,
        "wilson_95_upper": wilson_upper(total_failures, shots),
        "clopper_pearson_upper_delta_2m128": strict_upper,
        "target_total_logical_failure": target,
        "strict_verification_pass": strict_upper <= target,
        "sample_prediction_trace_sha256": trace_hasher.hexdigest(),
        "failure_vector_sha256": failure_hasher.hexdigest(),
        "chunk_digests": chunks,
        "timing": {
            "build_seconds": build_seconds,
            "sample_seconds": sample_seconds,
            "decode_seconds": decode_seconds,
            "total_seconds": build_seconds + sample_seconds + decode_seconds,
            "decode_seconds_per_shot": decode_seconds / shots,
            "decoded_memory_rounds_per_second": shots * execution["rounds"] / decode_seconds,
        },
    }


def without_timing(value: Any) -> Any:
    copied = copy.deepcopy(value)
    if isinstance(copied, dict):
        copied.pop("timing", None)
        for key in list(copied):
            copied[key] = without_timing(copied[key])
    elif isinstance(copied, list):
        copied = [without_timing(item) for item in copied]
    return copied


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

    freeze_binding = protocol["frozen_inputs"]["correlated_decoder_freeze_result"]
    freeze_result = read(ROOT / freeze_binding["path"])
    if freeze_result["decision"] != freeze_binding["required_decision"]:
        raise ValueError("correlated-decoder freeze decision mismatch")
    if freeze_result["summary"]["stochastic_shots_before_freeze"] != 0:
        raise ValueError("candidate freeze was not pre-outcome")
    execution = protocol["execution"]
    if execution["candidate_id"] != freeze_result["candidate"]["candidate_id"]:
        raise ValueError("candidate id changed after freeze")
    rows = [run_basis(basis, execution) for basis in execution["memory_bases"]]
    freeze_rows = {row["memory_basis"]: row for row in freeze_result["candidate_rows"]}
    independent_binding = protocol["frozen_inputs"]["independent_decoder_result"]
    independent_result = read(ROOT / independent_binding["path"])
    if independent_result["decision"] != independent_binding["required_decision"]:
        raise ValueError("independent-decoder baseline decision mismatch")
    independent_rows = {
        row["memory_basis"]: row for row in independent_result["candidate_rows"]
    }
    same_host_toolchain = (
        independent_result["execution_environment"]["python"] == platform.python_version()
        and independent_result["execution_environment"]["stim"] == stim.__version__
        and independent_result["execution_environment"]["pymatching"] == pymatching.__version__
        and independent_result["execution_environment"]["numpy"] == np.__version__
        and independent_result["execution_environment"]["scipy"] == scipy.__version__
        and independent_result["execution_environment"]["system"] == platform.system()
        and independent_result["execution_environment"]["machine"] == platform.machine()
    )
    for row in rows:
        baseline = independent_rows[row["memory_basis"]]
        baseline_seconds = baseline["timing"]["decode_seconds"]
        row["timing"]["independent_decode_seconds"] = baseline_seconds
        row["timing"]["independent_decode_seconds_per_shot"] = baseline["timing"][
            "decode_seconds_per_shot"
        ]
        row["timing"]["correlated_to_independent_decode_ratio"] = (
            row["timing"]["decode_seconds"] / baseline_seconds
        )
        row["timing"]["same_host_toolchain_match"] = same_host_toolchain
    score_contract = protocol["score_contract"]
    basis_improvement = {
        row["memory_basis"]: score_contract["reference_cost_per_basis"] / row["cost_active_qubit_rounds"]
        for row in rows
    }
    both_strict = all(row["strict_verification_pass"] for row in rows)
    conditional_score = math.sqrt(math.prod(basis_improvement.values()))
    accepted_score = conditional_score if both_strict else score_contract["invalid_candidate_score"]
    physical_memory_gate_passed = (
        both_strict
        and accepted_score >= score_contract["acceptance_threshold"]
        and all(value >= 1 for value in basis_improvement.values())
    )
    decision = (
        "d6_correlated_decoder_strict_xz_pass_physical_memory_gate_b2_p023_b7_credit_closed"
        if physical_memory_gate_passed
        else "d6_correlated_decoder_rejected_by_strict_xz_gate_score_zero_b2_p023_b7_credit_closed"
    )
    result: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_correlated_strict_acceptance_result_v1",
        "as_of_date": protocol["as_of_date"],
        "question": protocol["question"],
        "scope": protocol["scope"],
        "public_freeze": protocol["public_freeze"],
        "protocol_binding": {"path": str(protocol_path.relative_to(ROOT)), "sha256": digest_path(protocol_path)},
        "frozen_inputs_current": current_bindings,
        "frozen_inputs_at_commit": {"commit": freeze_commit, "bindings": commit_bindings},
        "generator": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": digest_path(Path(__file__).resolve())},
        "execution_environment": {
            "python": platform.python_version(),
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "execution": execution,
        "kaggle_inspired_verification_contract": protocol[
            "kaggle_inspired_verification_contract"
        ],
        "timing_contract": protocol["timing_contract"],
        "candidate_rows": rows,
        "score": {
            "reference_cost_per_basis": score_contract["reference_cost_per_basis"],
            "candidate_cost_by_basis": {row["memory_basis"]: row["cost_active_qubit_rounds"] for row in rows},
            "basis_improvement": basis_improvement,
            "conditional_composite_score": conditional_score,
            "accepted_composite_score": accepted_score,
            "acceptance_threshold": score_contract["acceptance_threshold"],
            "both_bases_strict_pass": both_strict,
            "physical_memory_gate_passed": physical_memory_gate_passed,
            "candidate_accepted": physical_memory_gate_passed,
        },
        "readiness": {
            "candidate_publicly_frozen_before_execution": True,
            "candidate_correctness_tested": True,
            "candidate_accepted_under_strict_memory_contract": physical_memory_gate_passed,
            "b2_physical_memory_candidate_gate_passed": physical_memory_gate_passed,
            "b2_candidate_improvement_verified": False,
            "full_b2_credit": False,
            "p023_scalable_memory_verified": False,
            "million_round_direct_evidence": False,
            "drift_correlation_stress_passed": False,
            "declared_decoder_deadline_passed": False,
            "b7_resource_credit": 0,
        },
        "downstream_gates": protocol["downstream_gates"],
        "claim_boundary": {
            **protocol["claim_boundary"],
            "physical_memory_candidate_claimed": physical_memory_gate_passed,
            "b2_improvement_claimed": False,
            "p023_scalable_memory_claimed": False,
            "b7_resource_credit_claimed": False,
        },
        "decision": decision,
        "next_gate": (
            "Price decoder latency, test model mismatch and correlated-noise stress, declare a decoder deadline, and obtain direct million-round X/Z evidence before full B2, #023, or B7 credit."
            if physical_memory_gate_passed
            else "Reject this correlated-decoder route under the frozen contract; preserve the zero score and preregister a genuinely different <=77-active-qubit code or schedule before sampling."
        ),
    }

    checks: list[dict[str, Any]] = []
    checks.append(check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23] and protocol["scope"]["included_tracks"] == ["B2", "B7"], "Exact scope."))
    checks.append(check("public_freeze", protocol["public_freeze"]["commit"] == freeze_commit and protocol["public_freeze"]["candidate_frozen_before_salt"], freeze_commit))
    checks.append(check("discussion", protocol["public_freeze"]["discussion_number"] == 325, protocol["public_freeze"]["discussion_url"]))
    checks.append(check("frozen_current", len(current_bindings) == 5, "Five frozen inputs match."))
    checks.append(check("frozen_commit", all(binding["matches"] for binding in commit_bindings.values()), freeze_commit))
    checks.append(check("freeze_decision", freeze_result["decision"] == freeze_binding["required_decision"], freeze_result["decision"]))
    checks.append(check("freeze_pre_outcome", freeze_result["summary"]["stochastic_shots_before_freeze"] == 0 and not freeze_result["summary"]["candidate_correctness_tested"], "Zero pre-freeze shots."))
    checks.append(check("toolchain", execution["toolchain"] == {"python": platform.python_version(), "stim": stim.__version__, "pymatching": pymatching.__version__, "numpy": np.__version__, "scipy": scipy.__version__}, str(execution["toolchain"])))
    checks.append(check("basis_set", [row["memory_basis"] for row in rows] == ["x", "z"], "X and Z executed."))
    checks.append(check("same_candidate", all(row["raw_circuit_sha256"] == freeze_rows[row["memory_basis"]]["raw_circuit_sha256"] for row in rows), "Raw candidate circuits match freeze."))
    checks.append(check("same_canonical_candidate", all(row["coordinate_canonical_circuit_sha256"] == freeze_rows[row["memory_basis"]]["coordinate_canonical_circuit_sha256"] for row in rows), "Canonical circuits match freeze."))
    checks.append(check("same_dem", all(row["detector_error_model_sha256"] == freeze_rows[row["memory_basis"]]["detector_error_model_sha256"] for row in rows), "DEMs match freeze."))
    checks.append(check("same_matching_graph", all(row["matching_nodes"] == freeze_rows[row["memory_basis"]]["matching_nodes"] and row["matching_edges"] == freeze_rows[row["memory_basis"]]["matching_edges"] for row in rows), "Correlation-aware matching graphs match freeze."))
    checks.append(check("correlations_enabled", all(row["correlations_enabled_at_construction"] and row["correlations_enabled_at_decode"] and freeze_rows[row["memory_basis"]]["correlations_enabled_at_construction"] and freeze_rows[row["memory_basis"]]["correlations_required_at_decode"] for row in rows), "Two-pass correlations enabled at construction and decoding."))
    checks.append(check("active_qubits", all(row["active_operational_qubits"] == 71 and row["index_span_qubits"] == 89 for row in rows), "71 active qubits in an 89-slot span."))
    checks.append(check("direct_exposure", all(row["rounds"] == 1000 and row["shots"] == 102400 for row in rows), "102,400 direct 1,000-round shots per basis."))
    checks.append(check("seed_derivation", all(row["seed"] == challenge_seed(execution["challenge_salt"], str(coordinate_canonical(build_circuit(row["memory_basis"], execution))).encode())[0] for row in rows), "Seeds reproduce from canonical circuits."))
    checks.append(check("seed_separation", len({row["seed"] for row in rows}) == 2, "X/Z challenge seeds differ."))
    checks.append(check("chunk_coverage", all(len(row["chunk_digests"]) == 400 and sum(chunk["shots"] for chunk in row["chunk_digests"]) == row["shots"] for row in rows), "400 complete chunks per basis."))
    checks.append(check("chunk_shapes", all(all(chunk["detector_shape"][0] == chunk["shots"] and chunk["observable_shape"][0] == chunk["shots"] and chunk["prediction_shape"][0] == chunk["shots"] for chunk in row["chunk_digests"]) for row in rows), "All chunk leading dimensions match shots."))
    checks.append(check("failure_arithmetic", all(abs(row["logical_error_rate"] - row["logical_failures"] / row["shots"]) < 1e-18 for row in rows), "Failure rates reproduce."))
    checks.append(check("strict_bounds", all(0 <= row["clopper_pearson_upper_delta_2m128"] <= 1 for row in rows), str({row["memory_basis"]: row["clopper_pearson_upper_delta_2m128"] for row in rows})))
    checks.append(check("strict_flags", all(row["strict_verification_pass"] == (row["clopper_pearson_upper_delta_2m128"] <= row["target_total_logical_failure"]) for row in rows), "Strict flags reproduce."))
    checks.append(check("cost", all(row["cost_active_qubit_rounds"] == 71000 for row in rows), "71,000 active-qubit-rounds per basis."))
    checks.append(check("basis_improvement", all(abs(value - 97 / 71) < 1e-15 for value in basis_improvement.values()), str(basis_improvement)))
    checks.append(check("score", accepted_score == (conditional_score if both_strict else 0) and physical_memory_gate_passed == (both_strict and conditional_score >= 1.25), str(result["score"])))
    checks.append(check("timing_baseline", same_host_toolchain and all(row["timing"]["correlated_to_independent_decode_ratio"] > 0 for row in rows), "Same host/toolchain; positive diagnostic ratios recorded outside the scientific run identity."))
    checks.append(check("decision", decision == ("d6_correlated_decoder_strict_xz_pass_physical_memory_gate_b2_p023_b7_credit_closed" if physical_memory_gate_passed else "d6_correlated_decoder_rejected_by_strict_xz_gate_score_zero_b2_p023_b7_credit_closed"), decision))
    checks.append(check("downstream", not result["readiness"]["b2_candidate_improvement_verified"] and not result["readiness"]["p023_scalable_memory_verified"] and result["readiness"]["b7_resource_credit"] == 0, "Full B2, #023, and B7 remain closed."))
    checks.append(check("claim_boundary", not result["claim_boundary"]["b2_improvement_claimed"] and not result["claim_boundary"]["p023_scalable_memory_claimed"] and not result["claim_boundary"]["b7_resource_credit_claimed"] and not result["claim_boundary"]["hardware_result_claimed"], "No full B2, downstream, or hardware overclaim."))
    result["formal_checks"] = checks
    result["summary"] = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "total_shots": sum(row["shots"] for row in rows),
        "total_logical_failures": sum(row["logical_failures"] for row in rows),
        "both_bases_strict_pass": both_strict,
        "conditional_score": conditional_score,
        "accepted_score": accepted_score,
        "physical_memory_gate_passed": physical_memory_gate_passed,
        "candidate_accepted": physical_memory_gate_passed,
        "b2_candidate_improvement_verified": False,
        "p023_scalable_memory_verified": False,
        "b7_resource_credit": 0,
    }
    result["run_id"] = digest_bytes(compact(without_timing({key: value for key, value in result.items() if key != "run_id"})))
    if result["summary"]["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"formal checks failed: {failed}")
    return result


def build_report(result: dict[str, Any]) -> str:
    rows = result["candidate_rows"]
    score = result["score"]
    verdict = "PHYSICAL-MEMORY GATE PASSED" if score["physical_memory_gate_passed"] else "REJECTED"
    return "\n".join(
        [
            "# B2/B7/#023 Distance-6 Correlated-Decoder Strict Acceptance v1",
            "",
            f"As of {result['as_of_date']}. Scope is exactly #021/B7, #022/B2, and #023.",
            "",
            "## Heuristic question",
            "",
            "Can two-pass correlation-aware matching make the unchanged 71-active-qubit candidate keep both X and Z below the strict 1% logical-failure ceiling for 1,000 rounds?",
            "",
            f"## Verdict: {verdict}",
            "",
            "| basis | seed | failures/shots | observed pL | strict CP upper | target | strict pass | cost |",
            "|---|---:|---:|---:|---:|---:|---|---:|",
            *[
                f"| {row['memory_basis'].upper()} | {row['seed']} | {row['logical_failures']}/{row['shots']} | {row['logical_error_rate']:.8f} | {row['clopper_pearson_upper_delta_2m128']:.8f} | {row['target_total_logical_failure']:.2f} | {row['strict_verification_pass']} | {row['cost_active_qubit_rounds']:,} |"
                for row in rows
            ],
            "",
            f"Both bases strict-pass: **{score['both_bases_strict_pass']}**. Conditional resource score: **{score['conditional_composite_score']:.9f}**. Accepted physical-memory score: **{score['accepted_composite_score']:.9f}**. Physical-memory gate passed: **{score['physical_memory_gate_passed']}**.",
            "",
            "## Freeze integrity",
            "",
            f"The candidate was publicly frozen at commit `{result['public_freeze']['commit']}` and Discussion #{result['public_freeze']['discussion_number']} before the salt was revealed. Raw circuits, coordinate-canonical circuits, DEMs, 71-qubit cost, noise model, decoder, horizon, and thresholds all match the no-outcome packet.",
            "",
            "## Claim boundary",
            "",
            ("This passes only the physical-memory candidate gate. Full B2 remains closed pending decoder-latency pricing, model-mismatch robustness, and implementation constraints; it also does not establish scalable #023 memory, a hardware result, or B7 credit." if score["physical_memory_gate_passed"] else "The correlated-decoder candidate fails the frozen acceptance contract and earns score zero. It does not establish B2 improvement, scalable #023 memory, a hardware result, or B7 credit."),
            "",
            f"Formal checks: **{result['summary']['checks_passed']}/{result['summary']['checks_total']}**. Run ID: `{result['run_id']}`.",
            "",
            "## Next gate",
            "",
            result["next_gate"],
            "",
        ]
    )


def build_discussion(result: dict[str, Any]) -> str:
    rows = {row["memory_basis"]: row for row in result["candidate_rows"]}
    accepted = result["score"]["physical_memory_gate_passed"]
    lead = "The 71-qubit correlated-decoder candidate survived both strict basis gates." if accepted else "The 71-qubit correlated-decoder candidate did not survive the frozen strict basis gate."
    return "\n".join(
        [
            "Can a smarter decoder buy 26 qubits—and who should pay for its latency?",
            "",
            lead,
            "",
            f"After public preregistration in Discussion #325, we revealed the freeze-bound salt and ran 102,400 fresh shots per basis at 1,000 rounds. X recorded {rows['x']['logical_failures']}/{rows['x']['shots']} failures with strict upper {rows['x']['clopper_pearson_upper_delta_2m128']:.6f}; Z recorded {rows['z']['logical_failures']}/{rows['z']['shots']} with strict upper {rows['z']['clopper_pearson_upper_delta_2m128']:.6f}.",
            "",
            f"The resource ratio is 97/71 = {result['score']['conditional_composite_score']:.4f}×. Following a Kaggle-style correctness veto, the accepted physical-memory score is **{result['score']['accepted_composite_score']:.4f}** and the physical-memory gate is **{accepted}**.",
            "",
            "Questions for critique:",
            "",
            "- Is the 1% total-memory failure target meaningful enough for algorithmic workloads?",
            "- Should decoder wall time be multiplied into the cost, constrained by a hard deadline, or reported as a separate Pareto axis?",
            "- Is exploiting decomposed Y-error correlation a fair algorithmic gain when the circuit and physical noise are unchanged?",
            "- Which mismatch, leakage, burst-noise, and decoder-deadline stress should precede any full B2 or #023 claim?",
            "- If this route failed, what genuinely different ≤77-qubit route should be frozen next; if it passed, what is the strongest falsifier?",
            "",
            f"Current boundary: physical-memory gate={result['readiness']['b2_physical_memory_candidate_gate_passed']}; full B2=false; #023 scalable memory=false; B7 resource credit=0.",
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
