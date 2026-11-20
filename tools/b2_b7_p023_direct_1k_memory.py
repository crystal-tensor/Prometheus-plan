#!/usr/bin/env python3
"""Run the frozen #021/B7, #022/B2, #023 direct 1,000-round memory packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import stim


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/B2_B7_P023_direct_1k_memory_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_direct_1k_memory_v1.json"
DEFAULT_MANIFEST = ROOT / "results/B2_B7_P023_direct_1k_memory_manifest_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_direct_1k_memory_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_direct_1k_memory_discussion_v1.md"
Z95 = 1.959963984540054


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def wilson_interval(failures: int, shots: int, z: float = Z95) -> tuple[float, float]:
    if shots <= 0:
        raise ValueError("shots must be positive")
    phat = failures / shots
    denom = 1.0 + z * z / shots
    center = (phat + z * z / (2.0 * shots)) / denom
    half = z * math.sqrt((phat * (1.0 - phat) + z * z / (4.0 * shots)) / shots) / denom
    return max(0.0, center - half), min(1.0, center + half)


def item(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def resolve_bound_input(binding: dict[str, Any]) -> Path:
    path = ROOT / binding["path"]
    actual = sha256_path(path)
    if actual != binding["sha256"]:
        raise ValueError(f"input hash mismatch for {binding['path']}: {actual}")
    return path


def validate_protocol(protocol: dict[str, Any], benchmark_path: Path) -> dict[str, Any]:
    if protocol["scope"]["included_catalog_problem_ids"] != [21, 22, 23]:
        raise ValueError("protocol scope must be exactly #021, #022, #023")
    if protocol["scope"]["included_tracks"] != ["B2", "B7"]:
        raise ValueError("protocol tracks must be exactly B2 and B7")
    bound = {}
    for name, binding in protocol["inputs"].items():
        path = resolve_bound_input(binding)
        value = read_json(path)
        if "required_status" in binding and value.get("status") != binding["required_status"]:
            raise ValueError(f"status mismatch for {name}")
        if "required_decision" in binding and value.get("decision") != binding["required_decision"]:
            raise ValueError(f"decision mismatch for {name}")
        bound[name] = {
            "path": binding["path"],
            "sha256": binding["sha256"],
        }
    versions = {
        "python": platform.python_version(),
        "stim": stim.__version__,
        "pymatching": pymatching.__version__,
        "numpy": np.__version__,
    }
    for name, required in protocol["toolchain_contract"].items():
        if name in versions and versions[name] != required:
            raise ValueError(f"tool version mismatch for {name}: {versions[name]} != {required}")
    return {
        "benchmark_path": str(benchmark_path.relative_to(ROOT)),
        "benchmark_sha256": sha256_path(benchmark_path),
        "bound_inputs": bound,
        "versions": versions,
    }


def build_circuit(config: dict[str, Any], experiment: dict[str, Any]) -> stim.Circuit:
    basis = config["memory_basis"]
    task = f"surface_code:rotated_memory_{basis}"
    noise = experiment["noise_parameters"]
    return stim.Circuit.generated(
        task,
        distance=config["distance"],
        rounds=experiment["rounds"],
        after_clifford_depolarization=noise["after_clifford_depolarization"],
        before_round_data_depolarization=noise["before_round_data_depolarization"],
        before_measure_flip_probability=noise["before_measure_flip_probability"],
        after_reset_flip_probability=noise["after_reset_flip_probability"],
    )


def run_configuration(config: dict[str, Any], experiment: dict[str, Any]) -> dict[str, Any]:
    shots = experiment["shots_per_configuration"]
    chunk_size = experiment["shot_chunk_size"]
    started_build = time.perf_counter()
    circuit = build_circuit(config, experiment)
    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(dem)
    sampler = circuit.compile_detector_sampler(seed=config["seed"])
    build_seconds = time.perf_counter() - started_build

    trace_hasher = hashlib.sha256()
    failure_hasher = hashlib.sha256()
    chunk_digests = []
    logical_failures = 0
    sample_seconds = 0.0
    decode_seconds = 0.0
    shot_offset = 0
    chunk_index = 0
    while shot_offset < shots:
        chunk_shots = min(chunk_size, shots - shot_offset)
        started_sample = time.perf_counter()
        detectors, observables = sampler.sample(
            chunk_shots,
            separate_observables=True,
            bit_packed=True,
        )
        sample_seconds += time.perf_counter() - started_sample
        started_decode = time.perf_counter()
        predictions = matching.decode_batch(
            detectors,
            bit_packed_shots=True,
            bit_packed_predictions=True,
        )
        decode_seconds += time.perf_counter() - started_decode
        if predictions.shape != observables.shape:
            raise ValueError(
                f"prediction/observable shape mismatch: {predictions.shape} != {observables.shape}"
            )
        failures = np.any(np.bitwise_xor(predictions, observables) != 0, axis=1).astype(np.uint8)
        logical_failures += int(np.count_nonzero(failures))
        header = {
            "chunk_index": chunk_index,
            "configuration_id": config["configuration_id"],
            "detector_shape": list(detectors.shape),
            "observable_shape": list(observables.shape),
            "prediction_shape": list(predictions.shape),
            "shot_offset": shot_offset,
            "shots": chunk_shots,
        }
        chunk_payload = (
            compact(header)
            + b"\x00"
            + detectors.tobytes(order="C")
            + observables.tobytes(order="C")
            + predictions.tobytes(order="C")
        )
        digest = sha256_bytes(chunk_payload)
        chunk_digests.append({**header, "sha256": digest})
        trace_hasher.update(chunk_payload)
        failure_hasher.update(compact({"shot_offset": shot_offset, "shots": chunk_shots}))
        failure_hasher.update(b"\x00")
        failure_hasher.update(failures.tobytes(order="C"))
        shot_offset += chunk_shots
        chunk_index += 1

    low, high = wilson_interval(logical_failures, shots)
    targets = [
        {
            "target_total_logical_failure": target,
            "wilson_upper_pass": high <= target,
        }
        for target in experiment["total_logical_failure_targets"]
    ]
    total_seconds = build_seconds + sample_seconds + decode_seconds
    return {
        **config,
        "stim_task": f"surface_code:rotated_memory_{config['memory_basis']}",
        "code_family": "rotated_surface_code_memory",
        "decoder": "pymatching_mwpm_from_decomposed_stim_dem",
        "rounds": experiment["rounds"],
        "shots": shots,
        "shot_chunk_size": chunk_size,
        "physical_error": experiment["physical_error"],
        "physical_qubits_in_stim_circuit": circuit.num_qubits,
        "detectors": circuit.num_detectors,
        "observables": circuit.num_observables,
        "dem_terms": len(str(dem).splitlines()),
        "matching_nodes": matching.num_nodes,
        "matching_edges": matching.num_edges,
        "logical_failures": logical_failures,
        "logical_error_rate": logical_failures / shots,
        "wilson_95_low": low,
        "wilson_95_high": high,
        "target_evaluations": targets,
        "direct_1k_evidence": True,
        "circuit_sha256": sha256_bytes(str(circuit).encode()),
        "detector_error_model_sha256": sha256_bytes(str(dem).encode()),
        "sample_prediction_trace_sha256": trace_hasher.hexdigest(),
        "failure_vector_sha256": failure_hasher.hexdigest(),
        "chunk_digests": chunk_digests,
        "timing": {
            "build_seconds": build_seconds,
            "sample_seconds": sample_seconds,
            "decode_seconds": decode_seconds,
            "total_seconds": total_seconds,
            "decode_seconds_per_shot": decode_seconds / shots,
            "sample_decode_seconds_per_shot": (sample_seconds + decode_seconds) / shots,
            "decoded_memory_rounds_per_second": shots * experiment["rounds"] / decode_seconds,
        },
    }


def paired_gates(rows: list[dict[str, Any]], experiment: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for distance in experiment["distances"]:
        selected = [row for row in rows if row["distance"] == distance]
        by_basis = {row["memory_basis"]: row for row in selected}
        for target in experiment["total_logical_failure_targets"]:
            basis_pass = {
                basis: next(
                    value["wilson_upper_pass"]
                    for value in by_basis[basis]["target_evaluations"]
                    if value["target_total_logical_failure"] == target
                )
                for basis in ["x", "z"]
            }
            output.append(
                {
                    "distance": distance,
                    "rounds": experiment["rounds"],
                    "shots_per_basis": experiment["shots_per_configuration"],
                    "physical_error": experiment["physical_error"],
                    "target_total_logical_failure": target,
                    "x_wilson_95_high": by_basis["x"]["wilson_95_high"],
                    "z_wilson_95_high": by_basis["z"]["wilson_95_high"],
                    "basis_pass": basis_pass,
                    "both_bases_direct_pass": all(basis_pass.values()),
                }
            )
    return output


def build_checks(
    protocol: dict[str, Any],
    binding: dict[str, Any],
    rows: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    experiment = protocol["experiment_contract"]
    expected_configs = experiment["configurations"]
    actual_keys = [
        (row["configuration_id"], row["memory_basis"], row["distance"], row["seed"])
        for row in rows
    ]
    expected_keys = [
        (row["configuration_id"], row["memory_basis"], row["distance"], row["seed"])
        for row in expected_configs
    ]
    expected_chunks = math.ceil(experiment["shots_per_configuration"] / experiment["shot_chunk_size"])
    recomputed_wilson = [wilson_interval(row["logical_failures"], row["shots"]) for row in rows]
    checks = [
        item("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact catalog scope."),
        item("tracks", protocol["scope"]["included_tracks"] == ["B2", "B7"], "Exact track scope."),
        item("input_hashes", len(binding["bound_inputs"]) == 3, "Three upstream inputs are hash-bound."),
        item("tool_versions", binding["versions"] == {k: protocol["toolchain_contract"][k] for k in ["python", "stim", "pymatching", "numpy"]}, str(binding["versions"])),
        item("configuration_matrix", actual_keys == expected_keys, f"Configurations: {len(rows)}."),
        item("basis_distance_axes", {row["memory_basis"] for row in rows} == {"x", "z"} and {row["distance"] for row in rows} == {3, 5, 7}, "X/Z at distances 3/5/7."),
        item("direct_rounds", all(row["rounds"] == 1000 and row["direct_1k_evidence"] for row in rows), "Every row directly executes 1,000 rounds."),
        item("shot_resolution", all(row["shots"] == 3838 for row in rows), "Every row uses the frozen 3,838-shot resolution."),
        item("physical_error", all(row["physical_error"] == 0.001 for row in rows), "All operation-class noise parameters are 0.001."),
        item("chunk_coverage", all(len(row["chunk_digests"]) == expected_chunks and sum(chunk["shots"] for chunk in row["chunk_digests"]) == row["shots"] for row in rows), f"{expected_chunks} ordered chunks per row."),
        item("chunk_offsets", all([chunk["shot_offset"] for chunk in row["chunk_digests"]] == list(range(0, row["shots"], row["shot_chunk_size"])) for row in rows), "Chunk offsets are contiguous."),
        item("hash_shapes", all(all(len(row[name]) == 64 for name in ["circuit_sha256", "detector_error_model_sha256", "sample_prediction_trace_sha256", "failure_vector_sha256"]) for row in rows), "All primary bindings are SHA-256 shaped."),
        item("chunk_hash_shapes", all(all(len(chunk["sha256"]) == 64 for chunk in row["chunk_digests"]) for row in rows), "Every chunk has a SHA-256 digest."),
        item("circuit_dimensions", all(row["physical_qubits_in_stim_circuit"] > 0 and row["detectors"] > 0 and row["observables"] == 1 for row in rows), "Every circuit has qubits, detectors, and one logical observable."),
        item("failure_arithmetic", all(row["logical_error_rate"] == row["logical_failures"] / row["shots"] for row in rows), "Failure rates reproduce."),
        item("wilson_recomputed", all(math.isclose(row["wilson_95_low"], bounds[0], rel_tol=0, abs_tol=1e-15) and math.isclose(row["wilson_95_high"], bounds[1], rel_tol=0, abs_tol=1e-15) for row, bounds in zip(rows, recomputed_wilson)), "All Wilson intervals reproduce."),
        item("target_evaluations", all(all(target["wilson_upper_pass"] == (row["wilson_95_high"] <= target["target_total_logical_failure"]) for target in row["target_evaluations"]) for row in rows), "Target pass flags reproduce."),
        item("paired_gate_count", len(pairs) == 6, "Three distances by two targets."),
        item("paired_basis_presence", all(set(row["basis_pass"]) == {"x", "z"} for row in pairs), "Both bases are present in every gate."),
        item("paired_gate_arithmetic", all(row["both_bases_direct_pass"] == all(row["basis_pass"].values()) for row in pairs), "Paired pass flags reproduce."),
        item("timing_recorded", all(all(row["timing"][key] > 0 for key in ["build_seconds", "sample_seconds", "decode_seconds", "total_seconds", "decoded_memory_rounds_per_second"]) for row in rows), "Positive local timing measurements are recorded."),
        item("no_projection", all(row["direct_1k_evidence"] for row in rows), "No projection row is used."),
        item("claim_boundary", not any(protocol["claim_boundary"][key] for key in protocol["claim_boundary"] if key != "simulator_experiment"), "All promotion claims remain false."),
        item("b7_credit_zero", protocol["acceptance_gate"]["b7_resource_credit"] == 0 and not protocol["acceptance_gate"]["b7_memory_credit_ready"], "B7 credit remains zero."),
    ]
    return checks


def build_result(protocol: dict[str, Any], benchmark_path: Path) -> dict[str, Any]:
    binding = validate_protocol(protocol, benchmark_path)
    experiment = protocol["experiment_contract"]
    rows = [run_configuration(config, experiment) for config in experiment["configurations"]]
    pairs = paired_gates(rows, experiment)
    staging_passes = [
        row for row in pairs
        if row["target_total_logical_failure"] == 0.01 and row["both_bases_direct_pass"]
    ]
    checks = build_checks(protocol, binding, rows, pairs)
    trace_identity = [
        {
            "configuration_id": row["configuration_id"],
            "circuit_sha256": row["circuit_sha256"],
            "detector_error_model_sha256": row["detector_error_model_sha256"],
            "sample_prediction_trace_sha256": row["sample_prediction_trace_sha256"],
            "failure_vector_sha256": row["failure_vector_sha256"],
        }
        for row in rows
    ]
    run_id = sha256_bytes(
        compact(
            {
                "benchmark_sha256": binding["benchmark_sha256"],
                "environment": {
                    "machine": platform.machine(),
                    "system": platform.system(),
                    "versions": binding["versions"],
                },
                "traces": trace_identity,
            }
        )
    )
    failed = [check for check in checks if not check["passed"]]
    if failed:
        raise RuntimeError(f"formal checks failed: {[check['name'] for check in failed]}")
    staging = bool(staging_passes)
    decision = (
        "direct_1000_round_staging_gate_passed_p023_scalable_b2_b7_credit_closed"
        if staging
        else "direct_1000_round_staging_gate_failed_p023_scalable_b2_b7_credit_closed"
    )
    return {
        "schema_version": "b2_b7_p023_direct_1k_memory_result_v1",
        "as_of_date": protocol["as_of_date"],
        "status": "direct_1000_round_simulator_memory_packet",
        "decision": decision,
        "scope": protocol["scope"],
        "question": protocol["question"],
        "protocol_binding": binding,
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_path(Path(__file__).resolve()),
        },
        "execution_environment": {
            "python": binding["versions"]["python"],
            "stim": binding["versions"]["stim"],
            "pymatching": binding["versions"]["pymatching"],
            "numpy": binding["versions"]["numpy"],
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "experiment_contract": experiment,
        "run_id": run_id,
        "configurations": rows,
        "paired_basis_gates": pairs,
        "readiness": {
            "direct_1k_staging_pass": staging,
            "direct_1k_passing_distances_at_1pct": [row["distance"] for row in staging_passes],
            "p023_scalable_memory_ready": False,
            "million_round_direct_evidence": False,
            "drift_correlation_stress_passed": False,
            "b2_low_overhead_credit_ready": False,
            "b7_memory_credit_ready": False,
            "b7_resource_credit": 0,
        },
        "trace_binding": protocol["trace_binding"],
        "formal_checks": checks,
        "summary": {
            "configuration_count": len(rows),
            "total_shots": sum(row["shots"] for row in rows),
            "total_executed_memory_rounds": sum(row["shots"] * row["rounds"] for row in rows),
            "total_physical_qubit_rounds": sum(row["shots"] * row["rounds"] * row["physical_qubits_in_stim_circuit"] for row in rows),
            "logical_failures": sum(row["logical_failures"] for row in rows),
            "paired_1pct_pass_count": len(staging_passes),
            "paired_0p1pct_pass_count": sum(row["both_bases_direct_pass"] for row in pairs if row["target_total_logical_failure"] == 0.001),
            "checks_passed": sum(check["passed"] for check in checks),
            "checks_total": len(checks),
            "checks_failed": len(failed),
        },
        "claim_boundary": protocol["claim_boundary"],
        "next_gate": "Run a source-bound million-round X/Z pilot only for the strongest 1,000-round distance, add declared drift/correlation stress, and keep B2/B7 credit closed until the same-condition candidate and calibrated-evidence gates pass.",
    }


def render_manifest(result: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for row in result["configurations"]:
        rows.append(
            {
                key: row[key]
                for key in [
                    "configuration_id", "memory_basis", "distance", "rounds", "shots", "seed",
                    "physical_error", "physical_qubits_in_stim_circuit", "detectors", "observables",
                    "logical_failures", "logical_error_rate", "wilson_95_low", "wilson_95_high",
                    "circuit_sha256", "detector_error_model_sha256",
                    "sample_prediction_trace_sha256", "failure_vector_sha256", "timing",
                ]
            }
        )
    return {
        "schema_version": "b2_b7_p023_direct_1k_memory_manifest_v1",
        "as_of_date": result["as_of_date"],
        "status": result["status"],
        "decision": result["decision"],
        "scope": result["scope"],
        "run_id": result["run_id"],
        "protocol_binding": result["protocol_binding"],
        "generator": result["generator"],
        "execution_environment": result["execution_environment"],
        "configurations": rows,
        "paired_basis_gates": result["paired_basis_gates"],
        "readiness": result["readiness"],
        "summary": result["summary"],
        "claim_boundary": result["claim_boundary"],
    }


def render_report(result: dict[str, Any]) -> str:
    s = result["summary"]
    readiness = result["readiness"]
    lines = [
        "# B2/B7/#023 Direct 1,000-Round Logical-Memory Packet v1",
        "",
        f"Last updated: {result['as_of_date']}",
        "",
        f"Status: **{result['decision']}**",
        "",
        "## Can direct observation replace the seven-round projection?",
        "",
        f"Yes, at the 1,000-round staging horizon only. This packet executes `{s['configuration_count']}` frozen Stim/PyMatching configurations across X/Z memory and distances 3/5/7, with 3,838 shots per row. It records `{s['total_shots']:,}` shots, `{s['total_executed_memory_rounds']:,}` shot-rounds, and `{s['total_physical_qubit_rounds']:,}` physical-qubit-rounds.",
        "",
        f"At the 1% total logical-failure target, `{s['paired_1pct_pass_count']}` distance(s) pass both X and Z by directly observed Wilson upper bounds: `{readiness['direct_1k_passing_distances_at_1pct']}`. At the stricter 0.1% target, `{s['paired_0p1pct_pass_count']}` distance(s) pass both bases.",
        "",
        "## Direct results",
        "",
        "| basis | d | rounds | shots | failures | logical pL | Wilson 95% upper | decode μs/shot | trace hash |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in result["configurations"]:
        lines.append(
            f"| {row['memory_basis']} | {row['distance']} | {row['rounds']} | {row['shots']} | "
            f"{row['logical_failures']} | {row['logical_error_rate']:.6g} | {row['wilson_95_high']:.6g} | "
            f"{1e6 * row['timing']['decode_seconds_per_shot']:.3f} | `{row['sample_prediction_trace_sha256'][:16]}…` |"
        )
    lines.extend([
        "",
        "## Paired-basis gates",
        "",
        "| d | target | X upper | Z upper | X pass | Z pass | paired direct pass |",
        "|---:|---:|---:|---:|---|---|---|",
    ])
    for row in result["paired_basis_gates"]:
        lines.append(
            f"| {row['distance']} | {row['target_total_logical_failure']:.4g} | "
            f"{row['x_wilson_95_high']:.6g} | {row['z_wilson_95_high']:.6g} | "
            f"{row['basis_pass']['x']} | {row['basis_pass']['z']} | {row['both_bases_direct_pass']} |"
        )
    lines.extend([
        "",
        "## Source and replay binding",
        "",
        f"- Run ID: `{result['run_id']}`",
        f"- Protocol SHA-256: `{result['protocol_binding']['benchmark_sha256']}`",
        f"- Generator SHA-256: `{result['generator']['sha256']}`",
        f"- Toolchain: Python {result['execution_environment']['python']}; Stim {result['execution_environment']['stim']}; PyMatching {result['execution_environment']['pymatching']}; NumPy {result['execution_environment']['numpy']}; {result['execution_environment']['system']} {result['execution_environment']['machine']}.",
        "- Each row binds canonical circuit text, decomposed detector error model, all ordered bit-packed detector/observable/prediction chunks, and the per-shot failure vector.",
        "- Raw detector traces are not published in this packet. The hashes support exact same-environment rerun comparison but are not a substitute for a public hardware trace dataset.",
        "",
        "## What changed—and what did not",
        "",
        "The previous seven-round ceiling is removed for the 1,000-round simulator staging gate. This is direct simulator observation, not a stationary projection. It does **not** activate scalable #023 memory: direct one-million-round X/Z evidence and declared drift/correlation stress remain absent. No same-condition candidate-code overhead win is tested, and the calibrated B7 dependency gate remains closed. Therefore B2 low-overhead credit remains false and B7 memory-derived resource credit remains exactly zero.",
        "",
        "## Claim boundary",
        "",
        "No new-code, threshold, scalable-memory, million-round, hardware, production-decoder, drift-robustness, B2 low-overhead improvement, B7 resource-credit, or quantum-advantage claim is made.",
        "",
        "## Next falsifier",
        "",
        result["next_gate"],
        "",
        f"Formal checks: `{s['checks_passed']}/{s['checks_total']}`.",
        "",
    ])
    return "\n".join(lines)


def render_discussion(result: dict[str, Any]) -> str:
    s = result["summary"]
    passing = result["readiness"]["direct_1k_passing_distances_at_1pct"]
    return f"""If 1,000 rounds pass in a simulator, what—exactly—has been learned about scalable quantum memory?

The new #021/B7 · #022/B2 · #023 packet removes one ambiguity from our earlier result: this time the X and Z memories are **directly executed for 1,000 rounds**. There is no seven-round extrapolation hiding inside the claim.

The frozen run uses Stim 1.16.0 and PyMatching 2.4.0 at circuit-level physical error 0.001, distances 3/5/7, and 3,838 shots per basis-distance row. Across {s['total_shots']:,} shots and {s['total_physical_qubit_rounds']:,} physical-qubit-rounds, {s['paired_1pct_pass_count']} distance(s) clear a 1% total-failure Wilson gate in both X and Z: **{passing}**. The stricter 0.1% paired gate is passed by {s['paired_0p1pct_pass_count']} distance(s).

Every row is bound to its exact circuit, detector error model, bit-packed detector/observable/prediction chunks, failure vector, seed, toolchain, and local decoder timing. But the raw traces are not published, the noise is not calibrated hardware noise, and a million-round experiment has not been run.

So where should the scientific boundary sit?

- Is 1,000 directly observed rounds a meaningful staging milestone, or still too short to earn any memory-language at all?
- Should a million-round simulator run be attempted next, or should correlated-noise and drift stress come first?
- Are hash-bound traces enough for reproducibility, or must the full detector stream be public before the result is useful?
- What same-condition qLDPC or alternative-code denominator would prevent a surface-code baseline from grading itself?
- Which decoder-throughput measurement belongs in a resource ledger: local batch throughput, worst-case latency, or a hardware-timed deadline miss rate?

Useful contributions are falsifiable: propose a drift/correlation model, a public trace format, a paired-basis confidence rule, or a code-family comparison that keeps the identical noise, decoder, horizon, and confidence budget.

Current boundary: **the direct 1,000-round staging gate is evaluated; #023 scalable-memory readiness remains false; B2 low-overhead credit remains false; B7 memory-derived resource credit remains zero.** Formal checks: {s['checks_passed']}/{s['checks_total']}.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    args = parser.parse_args()
    protocol = read_json(args.benchmark)
    result = build_result(protocol, args.benchmark)
    manifest = render_manifest(result)
    for path in [args.result, args.manifest, args.report, args.discussion]:
        path.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(canonical(result), encoding="utf-8")
    args.manifest.write_text(canonical(manifest), encoding="utf-8")
    args.report.write_text(render_report(result), encoding="utf-8")
    args.discussion.write_text(render_discussion(result), encoding="utf-8")
    print(canonical({"decision": result["decision"], "run_id": result["run_id"], **result["summary"]}), end="")


if __name__ == "__main__":
    main()
