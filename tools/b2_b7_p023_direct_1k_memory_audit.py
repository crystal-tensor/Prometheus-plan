#!/usr/bin/env python3
"""Independently audit the B2/B7/#023 direct 1,000-round memory packet."""

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
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_direct_1k_memory_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_direct_1k_memory_v1.json"
DEFAULT_MANIFEST = ROOT / "results/B2_B7_P023_direct_1k_memory_manifest_v1.json"
DEFAULT_AUDIT = ROOT / "results/B2_B7_P023_direct_1k_memory_audit_v1.json"
Z95 = 1.959963984540054


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def packed(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def wilson(failures: int, shots: int) -> tuple[float, float]:
    observed = failures / shots
    adjustment = Z95 * Z95 / shots
    midpoint = (observed + adjustment / 2.0) / (1.0 + adjustment)
    radius = Z95 / (1.0 + adjustment) * math.sqrt(
        observed * (1.0 - observed) / shots + Z95 * Z95 / (4.0 * shots * shots)
    )
    return max(0.0, midpoint - radius), min(1.0, midpoint + radius)


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def generated_circuit(protocol: dict[str, Any], config: dict[str, Any]) -> stim.Circuit:
    experiment = protocol["experiment_contract"]
    noise = experiment["noise_parameters"]
    return stim.Circuit.generated(
        f"surface_code:rotated_memory_{config['memory_basis']}",
        distance=config["distance"],
        rounds=experiment["rounds"],
        after_clifford_depolarization=noise["after_clifford_depolarization"],
        before_round_data_depolarization=noise["before_round_data_depolarization"],
        before_measure_flip_probability=noise["before_measure_flip_probability"],
        after_reset_flip_probability=noise["after_reset_flip_probability"],
    )


def expected_pairs(result: dict[str, Any], protocol: dict[str, Any]) -> list[dict[str, Any]]:
    rows = result["configurations"]
    experiment = protocol["experiment_contract"]
    output = []
    for distance in experiment["distances"]:
        by_basis = {
            row["memory_basis"]: row
            for row in rows
            if row["distance"] == distance
        }
        for target in experiment["total_logical_failure_targets"]:
            basis_pass = {
                basis: by_basis[basis]["wilson_95_high"] <= target
                for basis in ["x", "z"]
            }
            output.append(
                {
                    "basis_pass": basis_pass,
                    "both_bases_direct_pass": basis_pass["x"] and basis_pass["z"],
                    "distance": distance,
                    "physical_error": experiment["physical_error"],
                    "rounds": experiment["rounds"],
                    "shots_per_basis": experiment["shots_per_configuration"],
                    "target_total_logical_failure": target,
                    "x_wilson_95_high": by_basis["x"]["wilson_95_high"],
                    "z_wilson_95_high": by_basis["z"]["wilson_95_high"],
                }
            )
    return output


def manifest_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    keys = [
        "configuration_id", "memory_basis", "distance", "rounds", "shots", "seed",
        "physical_error", "physical_qubits_in_stim_circuit", "detectors", "observables",
        "logical_failures", "logical_error_rate", "wilson_95_low", "wilson_95_high",
        "circuit_sha256", "detector_error_model_sha256",
        "sample_prediction_trace_sha256", "failure_vector_sha256", "timing",
    ]
    return [{key: row[key] for key in keys} for row in result["configurations"]]


def audit(protocol: dict[str, Any], result: dict[str, Any], manifest: dict[str, Any], protocol_path: Path) -> dict[str, Any]:
    experiment = protocol["experiment_contract"]
    rows = result["configurations"]
    configured = experiment["configurations"]
    versions = {
        "python": platform.python_version(),
        "stim": stim.__version__,
        "pymatching": pymatching.__version__,
        "numpy": np.__version__,
    }
    regenerated = []
    for config, row in zip(configured, rows):
        circuit = generated_circuit(protocol, config)
        dem = circuit.detector_error_model(decompose_errors=True)
        matching = pymatching.Matching.from_detector_error_model(dem)
        regenerated.append(
            {
                "configuration_id": config["configuration_id"],
                "circuit_sha256": hashlib.sha256(str(circuit).encode()).hexdigest(),
                "detector_error_model_sha256": hashlib.sha256(str(dem).encode()).hexdigest(),
                "physical_qubits": circuit.num_qubits,
                "detectors": circuit.num_detectors,
                "observables": circuit.num_observables,
                "dem_terms": len(str(dem).splitlines()),
                "matching_nodes": matching.num_nodes,
                "matching_edges": matching.num_edges,
                "row": row,
            }
        )
    pair_rows = expected_pairs(result, protocol)
    passing_1pct = [
        row["distance"] for row in pair_rows
        if row["target_total_logical_failure"] == 0.01 and row["both_bases_direct_pass"]
    ]
    passing_0p1pct = [
        row["distance"] for row in pair_rows
        if row["target_total_logical_failure"] == 0.001 and row["both_bases_direct_pass"]
    ]
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
    run_id = hashlib.sha256(
        packed(
            {
                "benchmark_sha256": digest(protocol_path),
                "environment": {
                    "machine": result["execution_environment"]["machine"],
                    "system": result["execution_environment"]["system"],
                    "versions": result["protocol_binding"]["versions"],
                },
                "traces": trace_identity,
            }
        )
    ).hexdigest()
    expected_config_keys = [
        (row["configuration_id"], row["memory_basis"], row["distance"], row["seed"])
        for row in configured
    ]
    actual_config_keys = [
        (row["configuration_id"], row["memory_basis"], row["distance"], row["seed"])
        for row in rows
    ]
    hex64 = lambda value: len(value) == 64 and all(char in "0123456789abcdef" for char in value)
    checks = [
        check("scope", result["scope"] == protocol["scope"] and result["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact scope reproduced."),
        check("protocol_hash", result["protocol_binding"]["benchmark_sha256"] == digest(protocol_path), digest(protocol_path)),
        check("input_hashes", all(digest(ROOT / binding["path"]) == binding["sha256"] for binding in protocol["inputs"].values()), "All three inputs reproduce their frozen SHA-256."),
        check("bound_input_projection", result["protocol_binding"]["bound_inputs"] == {name: {"path": value["path"], "sha256": value["sha256"]} for name, value in protocol["inputs"].items()}, "Result binds the exact input set."),
        check("tool_versions", versions == {name: protocol["toolchain_contract"][name] for name in versions}, str(versions)),
        check("result_environment_versions", result["protocol_binding"]["versions"] == versions, "Recorded versions match the audit environment."),
        check("generator_hash", digest(ROOT / result["generator"]["path"]) == result["generator"]["sha256"], result["generator"]["sha256"]),
        check("configuration_order", actual_config_keys == expected_config_keys, f"Rows: {len(rows)}."),
        check("direct_contract", all(row["rounds"] == 1000 and row["shots"] == 3838 and row["physical_error"] == 0.001 and row["direct_1k_evidence"] for row in rows), "All rows are direct frozen 1,000-round experiments."),
        check("regenerated_circuit_hashes", all(value["circuit_sha256"] == value["row"]["circuit_sha256"] for value in regenerated), "All canonical Stim circuits reproduce."),
        check("regenerated_dem_hashes", all(value["detector_error_model_sha256"] == value["row"]["detector_error_model_sha256"] for value in regenerated), "All decomposed DEMs reproduce."),
        check("regenerated_dimensions", all(all(value[key] == value["row"][row_key] for key, row_key in [("physical_qubits", "physical_qubits_in_stim_circuit"), ("detectors", "detectors"), ("observables", "observables"), ("dem_terms", "dem_terms"), ("matching_nodes", "matching_nodes"), ("matching_edges", "matching_edges")]) for value in regenerated), "Circuit and matching dimensions reproduce."),
        check("trace_hash_shapes", all(all(hex64(row[key]) for key in ["sample_prediction_trace_sha256", "failure_vector_sha256"]) for row in rows), "All trace bindings are valid SHA-256."),
        check("trace_hash_distinct", len({row["sample_prediction_trace_sha256"] for row in rows}) == len(rows), "Every configuration has a distinct trace digest."),
        check("chunk_count", all(len(row["chunk_digests"]) == math.ceil(row["shots"] / row["shot_chunk_size"]) for row in rows), "Frozen chunk counts reproduce."),
        check("chunk_sequence", all([chunk["chunk_index"] for chunk in row["chunk_digests"]] == list(range(len(row["chunk_digests"]))) and [chunk["shot_offset"] for chunk in row["chunk_digests"]] == list(range(0, row["shots"], row["shot_chunk_size"])) for row in rows), "Chunk indices and offsets are contiguous."),
        check("chunk_shapes", all(all(chunk["detector_shape"] == [chunk["shots"], math.ceil(row["detectors"] / 8)] and chunk["observable_shape"] == [chunk["shots"], math.ceil(row["observables"] / 8)] and chunk["prediction_shape"] == chunk["observable_shape"] for chunk in row["chunk_digests"]) for row in rows), "Bit-packed detector/observable/prediction shapes reproduce."),
        check("chunk_hash_shapes", all(all(hex64(chunk["sha256"]) for chunk in row["chunk_digests"]) for row in rows), "Every chunk carries a valid SHA-256."),
        check("failure_rates", all(row["logical_error_rate"] == row["logical_failures"] / row["shots"] for row in rows), "All logical rates reproduce."),
        check("wilson_intervals", all(math.isclose(row["wilson_95_low"], wilson(row["logical_failures"], row["shots"])[0], abs_tol=1e-15, rel_tol=0) and math.isclose(row["wilson_95_high"], wilson(row["logical_failures"], row["shots"])[1], abs_tol=1e-15, rel_tol=0) for row in rows), "All Wilson intervals independently reproduce."),
        check("target_flags", all(all(value["wilson_upper_pass"] == (row["wilson_95_high"] <= value["target_total_logical_failure"]) for value in row["target_evaluations"]) for row in rows), "Every per-row target flag reproduces."),
        check("paired_gates", result["paired_basis_gates"] == pair_rows, "All six paired-basis gates independently reproduce."),
        check("one_percent_outcome", result["readiness"]["direct_1k_passing_distances_at_1pct"] == passing_1pct and result["readiness"]["direct_1k_staging_pass"] == bool(passing_1pct), f"Passing distances: {passing_1pct}."),
        check("strict_outcome", result["summary"]["paired_0p1pct_pass_count"] == len(passing_0p1pct), f"Passing distances: {passing_0p1pct}."),
        check("decision", result["decision"] == ("direct_1000_round_staging_gate_passed_p023_scalable_b2_b7_credit_closed" if passing_1pct else "direct_1000_round_staging_gate_failed_p023_scalable_b2_b7_credit_closed"), result["decision"]),
        check("run_id", result["run_id"] == run_id, run_id),
        check("summary_counts", result["summary"]["configuration_count"] == len(rows) and result["summary"]["total_shots"] == sum(row["shots"] for row in rows) and result["summary"]["total_executed_memory_rounds"] == sum(row["shots"] * row["rounds"] for row in rows) and result["summary"]["total_physical_qubit_rounds"] == sum(row["shots"] * row["rounds"] * row["physical_qubits_in_stim_circuit"] for row in rows) and result["summary"]["logical_failures"] == sum(row["logical_failures"] for row in rows), "All summary totals reproduce."),
        check("timing_fields", all(all(row["timing"][key] > 0 for key in ["build_seconds", "sample_seconds", "decode_seconds", "total_seconds", "decode_seconds_per_shot", "sample_decode_seconds_per_shot", "decoded_memory_rounds_per_second"]) for row in rows), "All local timing fields are positive."),
        check("manifest_rows", manifest["configurations"] == manifest_rows(result), "Manifest row projection exactly matches the full result."),
        check("manifest_gates", manifest["paired_basis_gates"] == pair_rows and manifest["readiness"] == result["readiness"] and manifest["summary"] == result["summary"], "Manifest gates and totals exactly match."),
        check("claim_boundary", result["claim_boundary"] == protocol["claim_boundary"] and result["claim_boundary"]["simulator_experiment"] and not any(value for key, value in result["claim_boundary"].items() if key != "simulator_experiment"), "Only the simulator-experiment classification is true."),
        check("readiness_boundary", not result["readiness"]["p023_scalable_memory_ready"] and not result["readiness"]["million_round_direct_evidence"] and not result["readiness"]["drift_correlation_stress_passed"] and not result["readiness"]["b2_low_overhead_credit_ready"] and not result["readiness"]["b7_memory_credit_ready"] and result["readiness"]["b7_resource_credit"] == 0, "All downstream credit gates remain closed."),
        check("raw_trace_boundary", protocol["trace_binding"]["raw_trace_published"] is False, "No public raw-trace claim is made."),
        check("producer_formal_checks", result["summary"]["checks_failed"] == 0 and all(value["passed"] for value in result["formal_checks"]), f"Producer checks: {result['summary']['checks_passed']}/{result['summary']['checks_total']}.")
    ]
    failed = [value for value in checks if not value["passed"]]
    return {
        "schema_version": "b2_b7_p023_direct_1k_memory_audit_v1",
        "as_of_date": protocol["as_of_date"],
        "scope": protocol["scope"],
        "status": "independent_direct_1k_memory_audit_passed" if not failed else "independent_direct_1k_memory_audit_failed",
        "audited_run_id": result["run_id"],
        "checks": checks,
        "summary": {
            "checks_passed": sum(value["passed"] for value in checks),
            "checks_total": len(checks),
            "checks_failed": len(failed),
        },
        "failure_names": [value["name"] for value in failed],
        "independence_boundary": "The audit independently rebuilds circuits, DEMs, matching dimensions, statistics, paired gates, summaries, manifest projections, and run identity. Exact sampled-trace bytes are verified separately by a second frozen execution because raw detector streams are not stored.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()
    output = audit(read(args.protocol), read(args.result), read(args.manifest), args.protocol)
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], sort_keys=True))
    if output["summary"]["checks_failed"]:
        raise SystemExit(f"audit failed: {output['failure_names']}")


if __name__ == "__main__":
    main()
