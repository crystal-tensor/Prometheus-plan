#!/usr/bin/env python3
"""Independent audit for the 8-bit Micro Blossom admission result.

This auditor intentionally does not import the producer module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import stim

import b2_b7_p023_d6_correlated_strict_acceptance as strict_base
import b2_b7_p023_d6_decoder_latency_matrix as latency_base
import b2_b7_p023_d6_fault_vector as fault_base
import b2_b7_p023_d6_online_window as online_base


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_admission_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_admission_v1.json"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_microblossom_admission_audit_v1.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def git_digest(commit: str, path: str) -> str:
    return digest(
        subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
    )


def audit_check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def derive_seed(commit: str, discussion: int, namespace: str, basis: str) -> tuple[int, str]:
    raw = hashlib.sha256(
        f"{commit}:{discussion}:{namespace}:{basis}".encode()
    ).digest()
    return int.from_bytes(raw[:8], "little"), raw.hex()


def q_dem(
    source: stim.DetectorErrorModel, bits: int, scale: int
) -> tuple[stim.DetectorErrorModel, list[int]]:
    target = stim.DetectorErrorModel()
    integers: list[int] = []
    for instruction in source:
        args = instruction.args_copy()
        if instruction.type == "error":
            p = float(args[0])
            if not 0 < p < 0.5:
                raise ValueError("probability outside correlation contract")
            q = max(1, round(scale * math.log((1 - p) / p)))
            if q >= 1 << bits:
                raise ValueError("integer weight overflow")
            args = [1 / (1 + math.exp(q / scale))]
            integers.append(q)
        target.append(instruction.type, args, instruction.targets_copy())
    return target, integers


def edge_key(u: int, v: int | None) -> tuple[int, int]:
    if v is None or v == -1:
        return int(u), -1
    return (int(u), int(v)) if u <= v else (int(v), int(u))


def topology(matching: pymatching.Matching) -> list[list[int]]:
    return sorted([list(edge_key(int(u), None if v is None else int(v))) for u, v, _ in matching.edges()])


def component_edges(instruction: Any) -> list[tuple[int, int]]:
    groups: list[list[int]] = []
    current: list[int] = []
    for target in instruction.targets_copy():
        if target.is_separator():
            if current:
                groups.append(current)
                current = []
        elif target.is_relative_detector_id():
            current.append(int(target.val))
    if current:
        groups.append(current)
    answer: list[tuple[int, int]] = []
    for group in groups:
        if len(group) == 1:
            answer.append(edge_key(group[0], None))
        elif len(group) == 2:
            answer.append(edge_key(group[0], group[1]))
        elif group:
            raise ValueError("non-graphlike decomposed mechanism")
    return answer


def relation_table(
    model: stim.DetectorErrorModel,
) -> dict[tuple[int, int], set[tuple[int, int]]]:
    answer: dict[tuple[int, int], set[tuple[int, int]]] = defaultdict(set)
    for instruction in model:
        if instruction.type != "error":
            continue
        keys = component_edges(instruction)
        for source in keys:
            targets = {target for target in keys if target != source}
            if targets:
                answer[source].update(targets)
    return dict(answer)


def relation_digest(table: dict[tuple[int, int], set[tuple[int, int]]]) -> str:
    value = [
        [list(source), [list(target) for target in sorted(targets)]]
        for source, targets in sorted(table.items())
    ]
    return digest(compact(value))


def rank(values: list[int], p: float) -> float:
    ordered = sorted(values)
    return float(ordered[max(0, math.ceil(p * len(ordered)) - 1)])


def summarize(values: list[int]) -> dict[str, Any]:
    return {
        "observations": len(values),
        "mean": sum(values) / len(values),
        "p50": rank(values, 0.50),
        "p95": rank(values, 0.95),
        "p99": rank(values, 0.99),
        "p999": rank(values, 0.999),
        "maximum": max(values),
        "zero_fraction": sum(value == 0 for value in values) / len(values),
        "raw_uint32_sha256": digest(np.asarray(values, dtype="<u4").tobytes()),
    }


def compile_windows(
    compiled: online_base.CompiledWindows, bits: int, scale: int
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    addressed: set[int] = set()
    windows: list[dict[str, Any]] = []
    q_values: list[int] = []
    reference_topology_hashes: list[str] = []
    candidate_graph_hashes: list[str] = []
    relation_hashes: list[str] = []
    geometries: list[tuple[int, int, int, int]] = []
    relation_shapes: list[tuple[int, int, int]] = []
    total_edges = 0
    for baseline in compiled.windows:
        components = (
            online_base.union_components(compiled.model, baseline.detection_detectors)
            - addressed
        )
        commit = set(baseline.commit_component_ids)
        reference_dem, detector_outputs, observable_outputs = fault_base.build_fault_vector_dem(
            compiled.model,
            baseline.detection_detectors,
            components,
            commit,
        )
        candidate_dem, q = q_dem(reference_dem, bits, scale)
        reference = pymatching.Matching.from_detector_error_model(
            reference_dem, enable_correlations=True
        )
        candidate = pymatching.Matching.from_detector_error_model(
            candidate_dem, enable_correlations=True
        )
        reference_topology = topology(reference)
        candidate_topology = topology(candidate)
        if reference_topology != topology(baseline.matching) or candidate_topology != reference_topology:
            raise ValueError("topology mismatch")
        relations = relation_table(reference_dem)
        unique_pairs = {
            tuple(sorted((source, target)))
            for source, targets in relations.items()
            for target in targets
        }
        relation_shapes.append(
            (len(relations), sum(map(len, relations.values())), len(unique_pairs))
        )
        signature = sorted(
            [
                [
                    list(edge_key(int(u), None if v is None else int(v))),
                    float(data["weight"]),
                    float(data["error_probability"]),
                ]
                for u, v, data in candidate.edges()
            ]
        )
        reference_topology_hashes.append(digest(compact(reference_topology)))
        candidate_graph_hashes.append(digest(compact(signature)))
        relation_hashes.append(relation_digest(relations))
        geometry = (
            candidate.num_nodes,
            candidate.num_edges,
            candidate.num_detectors,
            candidate.num_fault_ids,
        )
        geometries.append(geometry)
        q_values.extend(q)
        total_edges += candidate.num_edges
        windows.append(
            {
                "reference": reference,
                "candidate": candidate,
                "detector_outputs": detector_outputs,
                "observable_outputs": observable_outputs,
                "relations": relations,
            }
        )
        addressed.update(commit)
    geometry_counts = Counter(geometries)
    graph_counts = Counter(candidate_graph_hashes)
    steady_geometry, steady_windows = geometry_counts.most_common(1)[0]
    steady_relation = Counter(relation_shapes).most_common(1)[0][0]
    structure = {
        "windows": len(windows),
        "topology_equal_windows": len(windows),
        "output_map_equal_windows": len(windows),
        "unique_reference_topologies": len(set(reference_topology_hashes)),
        "unique_quantized_graphs": len(graph_counts),
        "quantized_graph_multiplicities": sorted(graph_counts.values(), reverse=True),
        "steady_windows": steady_windows,
        "steady_geometry": {
            "nodes": steady_geometry[0],
            "edges": steady_geometry[1],
            "detectors": steady_geometry[2],
            "fault_vector_bits": steady_geometry[3],
        },
        "total_edges_across_windows": total_edges,
        "edge_index_bits": math.ceil(math.log2(max(g[1] for g in geometries))),
        "quantized_group_weight_min": min(q_values),
        "quantized_group_weight_max": max(q_values),
        "quantized_group_weight_unique": len(set(q_values)),
        "quantized_weights_fit_unsigned_width": max(q_values) < (1 << bits),
        "relation_manifest_sha256": digest(compact(relation_hashes)),
        "steady_correlation_table": {
            "causal_keys": steady_relation[0],
            "directed_relations": steady_relation[1],
            "undirected_pairs": steady_relation[2],
        },
        "maximum_correlation_table": {
            "causal_keys": max(row[0] for row in relation_shapes),
            "directed_relations": max(row[1] for row in relation_shapes),
            "undirected_pairs": max(row[2] for row in relation_shapes),
        },
    }
    return windows, structure


def decode_shot(
    compiled: online_base.CompiledWindows,
    windows: list[dict[str, Any]],
    raw: np.ndarray,
) -> dict[str, Any]:
    states: dict[str, dict[str, np.ndarray]] = {}
    for name in ("reference", "candidate"):
        states[name] = {
            "received": np.zeros(compiled.model.num_detectors, dtype=np.uint8),
            "correction": np.zeros(compiled.model.num_detectors, dtype=np.uint8),
            "frame": np.zeros(compiled.model.num_observables, dtype=np.uint8),
        }
        states[name]["received"][compiled.prebuffer_detectors] = raw[
            compiled.prebuffer_detectors
        ]
    commit_failures = {"reference": 0, "candidate": 0}
    same_syndrome = 0
    same_output = 0
    selected_counts: list[int] = []
    affected_counts: list[int] = []
    for baseline, window in zip(compiled.windows, windows, strict=True):
        for state in states.values():
            state["received"][baseline.arrival_detectors] = raw[
                baseline.arrival_detectors
            ]
        syndromes: dict[str, np.ndarray] = {}
        for name, state in states.items():
            syndromes[name] = np.bitwise_xor(
                state["received"][baseline.detection_detectors],
                state["correction"][baseline.detection_detectors],
            )
        same_syndrome += int(np.array_equal(syndromes["reference"], syndromes["candidate"]))
        reference_vector = window["reference"].decode(
            syndromes["reference"], enable_correlations=True
        )
        candidate_vector = window["candidate"].decode(
            syndromes["candidate"], enable_correlations=True
        )
        same_output += int(np.array_equal(reference_vector, candidate_vector))
        detector_count = len(window["detector_outputs"])
        for name, vector in (("reference", reference_vector), ("candidate", candidate_vector)):
            states[name]["correction"][window["detector_outputs"]] ^= vector[:detector_count]
            states[name]["frame"][window["observable_outputs"]] ^= vector[detector_count:]
            residual = np.bitwise_xor(
                states[name]["received"][baseline.commit_detectors],
                states[name]["correction"][baseline.commit_detectors],
            )
            commit_failures[name] += int(np.any(residual))
        first_edges = window["candidate"].decode_to_edges_array(
            syndromes["candidate"], enable_correlations=False
        )
        selected = {
            edge_key(int(u), None if int(v) == -1 else int(v))
            for u, v in first_edges
        }
        affected: set[tuple[int, int]] = set()
        for selected_edge in selected:
            affected.update(window["relations"].get(selected_edge, set()))
        selected_counts.append(len(selected))
        affected_counts.append(len(affected))
    final_weights = {
        name: int(np.count_nonzero(np.bitwise_xor(state["received"], state["correction"])))
        for name, state in states.items()
    }
    return {
        "reference_frame": states["reference"]["frame"],
        "candidate_frame": states["candidate"]["frame"],
        "same_syndrome": same_syndrome,
        "same_output": same_output,
        "commit_failures": commit_failures,
        "final_weights": final_weights,
        "selected": selected_counts,
        "affected": affected_counts,
    }


def audit_basis(
    basis: str,
    execution: dict[str, Any],
    window_contract: dict[str, Any],
    protocol: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    freeze = result["public_freeze"]
    seed, seed_hash = derive_seed(
        freeze["commit"],
        freeze["discussion_number"],
        protocol["fresh_holdout_contract"]["seed_namespace"],
        basis,
    )
    shots = protocol["fresh_holdout_contract"]["shots_per_basis"]
    circuit = strict_base.build_circuit(basis, execution)
    sampler = circuit.compile_detector_sampler(seed=seed)
    detectors_packed, observables_packed = sampler.sample(
        shots, separate_observables=True, bit_packed=True
    )
    corpus_header = {
        "basis": basis,
        "shots": shots,
        "seed": seed,
        "seed_digest_sha256": seed_hash,
        "detector_shape": list(detectors_packed.shape),
        "observable_shape": list(observables_packed.shape),
    }
    corpus_hash = digest(
        compact(corpus_header)
        + b"\x00"
        + detectors_packed.tobytes(order="C")
        + observables_packed.tobytes(order="C")
    )
    full_matcher = pymatching.Matching.from_detector_error_model(
        circuit.detector_error_model(decompose_errors=True),
        enable_correlations=True,
    )
    full_packed = latency_base.decode_corpus(full_matcher, detectors_packed, 256, True)
    full = np.unpackbits(
        full_packed,
        axis=1,
        count=circuit.num_observables,
        bitorder="little",
    )
    actual = np.unpackbits(
        observables_packed,
        axis=1,
        count=circuit.num_observables,
        bitorder="little",
    )
    raw = np.unpackbits(
        detectors_packed,
        axis=1,
        count=circuit.num_detectors,
        bitorder="little",
    ).astype(np.uint8, copy=False)
    compiled = online_base.compile_windows(
        circuit.detector_error_model(decompose_errors=True),
        circuit.get_detector_coordinates(),
        window_contract["window_size_layers"],
        window_contract["stride_layers"],
        window_contract["time_coordinate_index"],
    )
    windows, structure = compile_windows(
        compiled,
        protocol["candidate_contract"]["weight_bits"],
        protocol["candidate_contract"]["fixed_point_scale"],
    )
    reference = np.zeros_like(full)
    candidate = np.zeros_like(full)
    same_syndrome = 0
    same_output = 0
    commit_reference = 0
    commit_candidate = 0
    final_reference = 0
    final_candidate = 0
    selected: list[int] = []
    affected: list[int] = []
    for shot_index, row in enumerate(raw):
        decoded = decode_shot(compiled, windows, row)
        reference[shot_index] = decoded["reference_frame"]
        candidate[shot_index] = decoded["candidate_frame"]
        same_syndrome += decoded["same_syndrome"]
        same_output += decoded["same_output"]
        commit_reference += decoded["commit_failures"]["reference"]
        commit_candidate += decoded["commit_failures"]["candidate"]
        final_reference += decoded["final_weights"]["reference"] > 0
        final_candidate += decoded["final_weights"]["candidate"] > 0
        selected.extend(decoded["selected"])
        affected.extend(decoded["affected"])
    payload = [value * 20 for value in affected]
    pack_hash = lambda array: digest(
        np.packbits(array, axis=1, bitorder="little").tobytes()
    )
    return {
        "basis": basis,
        "seed": seed,
        "seed_digest_sha256": seed_hash,
        "corpus_sha256": corpus_hash,
        "structural": structure,
        "candidate_prediction_rows_equal_reference_online": int(
            np.count_nonzero(np.all(candidate == reference, axis=1))
        ),
        "reference_online_prediction_rows_equal_full_block": int(
            np.count_nonzero(np.all(reference == full, axis=1))
        ),
        "candidate_prediction_rows_equal_full_block": int(
            np.count_nonzero(np.all(candidate == full, axis=1))
        ),
        "window_syndromes_equal": same_syndrome,
        "window_outputs_equal": same_output,
        "reference_commit_residual_failures": commit_reference,
        "candidate_commit_residual_failures": commit_candidate,
        "reference_final_residual_failure_shots": final_reference,
        "candidate_final_residual_failure_shots": final_candidate,
        "full_block_logical_failures": int(np.count_nonzero(np.any(full != actual, axis=1))),
        "reference_online_logical_failures": int(np.count_nonzero(np.any(reference != actual, axis=1))),
        "candidate_logical_failures": int(np.count_nonzero(np.any(candidate != actual, axis=1))),
        "full_block_prediction_sha256": pack_hash(full),
        "reference_online_prediction_sha256": pack_hash(reference),
        "candidate_prediction_sha256": pack_hash(candidate),
        "controller_payload": {
            "first_pass_selected_edges": summarize(selected),
            "unique_affected_edges_upper_bound": summarize(affected),
            "dynamic_update_payload_bits_upper_bound": summarize(payload),
            "encoding": "12-bit edge index plus 8-bit replacement weight",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    protocol = load(args.protocol)
    result = load(args.result)
    source_protocol = load(
        ROOT / protocol["frozen_inputs"]["fault_vector_protocol"]["path"]
    )
    online_protocol, strict_result = fault_base.load_upstream(source_protocol)
    execution = strict_result["execution"]
    rows = {
        basis: audit_basis(
            basis,
            execution,
            online_protocol["window_contract"],
            protocol,
            result,
        )
        for basis in execution["memory_bases"]
    }
    expected_rows = {row["basis"]: row for row in result["basis_rows"]}
    expected_corpora = {row["basis"]: row for row in result["corpora"]}
    row_fields = [
        "candidate_prediction_rows_equal_reference_online",
        "reference_online_prediction_rows_equal_full_block",
        "candidate_prediction_rows_equal_full_block",
        "window_syndromes_equal",
        "window_outputs_equal",
        "reference_commit_residual_failures",
        "candidate_commit_residual_failures",
        "reference_final_residual_failure_shots",
        "candidate_final_residual_failure_shots",
        "full_block_logical_failures",
        "reference_online_logical_failures",
        "candidate_logical_failures",
        "full_block_prediction_sha256",
        "reference_online_prediction_sha256",
        "candidate_prediction_sha256",
    ]
    freeze_commit = result["public_freeze"]["commit"]
    protocol_rel = str(args.protocol.resolve().relative_to(ROOT))
    runner_rel = result["protocol_binding"]["runner_path"]
    checks: list[dict[str, Any]] = []
    checks.append(audit_check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact scope."))
    checks.append(audit_check("protocol_freeze", git_digest(freeze_commit, protocol_rel) == file_digest(args.protocol), freeze_commit))
    checks.append(audit_check("runner_freeze", git_digest(freeze_commit, runner_rel) == result["protocol_binding"]["runner_sha256"], runner_rel))
    checks.append(audit_check("result_digest", file_digest(args.result) == "d063538cb4cdd4ee23b1aee80b9d54760510a522c7c7927100f69ca6d8ddbbd5", file_digest(args.result)))
    evidence_source = {key: value for key, value in result.items() if key != "evidence_id"}
    checks.append(audit_check("evidence_id", digest(compact(evidence_source)) == result["evidence_id"], result["evidence_id"]))
    checks.append(audit_check("basis_set", sorted(rows) == ["x", "z"], str(sorted(rows))))
    checks.append(audit_check("seeds", all(rows[b]["seed"] == expected_corpora[b]["seed"] and rows[b]["seed_digest_sha256"] == expected_corpora[b]["seed_digest_sha256"] for b in rows), "Seeds independently derived."))
    checks.append(audit_check("corpora", all(rows[b]["corpus_sha256"] == expected_corpora[b]["corpus_sha256"] for b in rows), "Detector/observable bytes reproduce."))
    checks.append(audit_check("x_structure", rows["x"]["structural"] == expected_rows["x"]["structural"], "X graph manifest exact."))
    checks.append(audit_check("z_structure", rows["z"]["structural"] == expected_rows["z"]["structural"], "Z graph manifest exact."))
    checks.append(audit_check("x_semantics", all(rows["x"][field] == expected_rows["x"][field] for field in row_fields), "X predictions, residuals, and failures exact."))
    checks.append(audit_check("z_semantics", all(rows["z"][field] == expected_rows["z"][field] for field in row_fields), "Z predictions, residuals, and failures exact."))
    checks.append(audit_check("x_payload", rows["x"]["controller_payload"] == expected_rows["x"]["controller_payload"], "X payload vectors exact."))
    checks.append(audit_check("z_payload", rows["z"]["controller_payload"] == expected_rows["z"]["controller_payload"], "Z payload vectors exact."))
    checks.append(audit_check("semantic_pass", all(expected_rows[b]["semantic_veto_pass"] for b in expected_rows), "Both basis vetoes pass."))
    checks.append(audit_check("classification", result["classification"] == "eight_bit_semantic_admission_pass_hardware_execution_unmeasured", result["classification"]))
    checks.append(audit_check("formal_checks", result["summary"]["checks_passed"] == result["summary"]["checks_total"] == 17, str(result["summary"])))
    checks.append(audit_check("no_hardware_claim", not result["verdict"]["micro_blossom_rtl_generated_for_candidate"] and not result["verdict"]["cycle_accurate_candidate_executed"] and not result["verdict"]["fpga_candidate_executed"] and not result["verdict"]["hardware_decoder_deadline_passed"], "Hardware remains unmeasured."))
    checks.append(audit_check("no_downstream_credit", not result["verdict"]["full_b2_credit_ready"] and not result["verdict"]["p023_scalable_memory_ready"] and result["verdict"]["b7_resource_credit"] == 0, "B2/#023/B7 remain closed."))
    checks.append(audit_check("external_pin", protocol["external_source_profile"]["micro_blossom_commit"] == "a3530d9e58ff790dafc93d56c9a2769ceac84731" and protocol["external_source_profile"]["pymatching_tag_commit"] == "6f63b2b9474ba0fa7e511fe52bffdce858a06984", "External source commits pinned."))
    audit: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_microblossom_admission_audit_v1",
        "producer_imported": False,
        "source_result_path": str(args.result.resolve().relative_to(ROOT)),
        "source_result_sha256": file_digest(args.result),
        "recomputed": rows,
        "checks": checks,
        "summary": {
            "checks_total": len(checks),
            "checks_passed": sum(row["passed"] for row in checks),
            "checks_failed": sum(not row["passed"] for row in checks),
        },
    }
    audit["audit_id"] = digest(compact(audit))
    if audit["summary"]["checks_failed"]:
        failed = [row["name"] for row in checks if not row["passed"]]
        raise ValueError(f"audit failed: {failed}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical(audit), encoding="utf-8")
    print(canonical({"audit_id": audit["audit_id"], "summary": audit["summary"]}), end="")


if __name__ == "__main__":
    main()
