#!/usr/bin/env python3
"""Preregistered 8-bit Micro Blossom architecture-admission experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import scipy
import stim

import b2_b7_p023_d6_correlated_strict_acceptance as strict_base
import b2_b7_p023_d6_decoder_latency_matrix as latency_base
import b2_b7_p023_d6_fault_vector as fault_base
import b2_b7_p023_d6_online_window as online_base


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_admission_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_admission_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_microblossom_admission_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_d6_microblossom_admission_discussion_v1.md"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def nearest_rank(values: list[int] | list[float], probability: float) -> float:
    if not values:
        raise ValueError("cannot summarize an empty vector")
    ordered = sorted(values)
    return float(ordered[max(0, math.ceil(probability * len(ordered)) - 1)])


def distribution(values: list[int]) -> dict[str, Any]:
    if not values:
        raise ValueError("cannot summarize an empty vector")
    return {
        "observations": len(values),
        "mean": sum(values) / len(values),
        "p50": nearest_rank(values, 0.50),
        "p95": nearest_rank(values, 0.95),
        "p99": nearest_rank(values, 0.99),
        "p999": nearest_rank(values, 0.999),
        "maximum": max(values),
        "zero_fraction": sum(value == 0 for value in values) / len(values),
        "raw_uint32_sha256": sha_bytes(np.asarray(values, dtype="<u4").tobytes()),
    }


def seed_for(
    public_freeze_commit: str,
    discussion_number: int,
    namespace: str,
    basis: str,
) -> tuple[int, str]:
    material = (
        f"{public_freeze_commit}:{discussion_number}:{namespace}:{basis}".encode()
    )
    digest = hashlib.sha256(material).digest()
    return int.from_bytes(digest[:8], "little"), digest.hex()


def quantize_probability(
    probability: float, weight_bits: int, scale: int
) -> tuple[float, int]:
    if not 0 < probability < 0.5:
        raise ValueError("correlated error probability must be in (0, 0.5)")
    weight = math.log((1 - probability) / probability)
    quantized = max(1, round(scale * weight))
    if quantized >= 1 << weight_bits:
        raise ValueError("quantized weight does not fit the frozen unsigned width")
    restored_probability = 1 / (1 + math.exp(quantized / scale))
    return restored_probability, quantized


def quantize_dem(
    model: stim.DetectorErrorModel, weight_bits: int, scale: int
) -> tuple[stim.DetectorErrorModel, list[int]]:
    result = stim.DetectorErrorModel()
    weights: list[int] = []
    for instruction in model:
        args = instruction.args_copy()
        if instruction.type == "error":
            probability, quantized = quantize_probability(
                float(args[0]), weight_bits, scale
            )
            args = [probability]
            weights.append(quantized)
        result.append(instruction.type, args, instruction.targets_copy())
    if not weights:
        raise ValueError("window has no error mechanisms")
    return result, weights


def split_component_keys(instruction: Any) -> list[tuple[int, int]]:
    components: list[list[int]] = []
    current: list[int] = []
    for target in instruction.targets_copy():
        if target.is_separator():
            if current:
                components.append(current)
                current = []
        elif target.is_relative_detector_id():
            current.append(int(target.val))
    if current:
        components.append(current)
    keys: list[tuple[int, int]] = []
    for component in components:
        if len(component) == 1:
            keys.append(fault_base.edge_key(component[0], None))
        elif len(component) == 2:
            keys.append(fault_base.edge_key(component[0], component[1]))
        elif component:
            raise ValueError("non-graphlike component in frozen decomposed DEM")
    return keys


def correlation_map(
    model: stim.DetectorErrorModel,
) -> dict[tuple[int, int], set[tuple[int, int]]]:
    result: dict[tuple[int, int], set[tuple[int, int]]] = defaultdict(set)
    for instruction in model:
        if instruction.type != "error":
            continue
        keys = split_component_keys(instruction)
        for source in keys:
            for target in keys:
                if source != target:
                    result[source].add(target)
    return dict(result)


def relation_signature(
    relations: dict[tuple[int, int], set[tuple[int, int]]],
) -> str:
    manifest = [
        [list(source), [list(target) for target in sorted(targets)]]
        for source, targets in sorted(relations.items())
    ]
    return sha_bytes(compact(manifest))


@dataclass(frozen=True)
class AdmissionWindow:
    reference: pymatching.Matching
    candidate: pymatching.Matching
    detector_outputs: np.ndarray
    observable_outputs: np.ndarray
    fault_vector_bits: int
    relations: dict[tuple[int, int], set[tuple[int, int]]]


def compile_admission_windows(
    compiled: online_base.CompiledWindows, weight_bits: int, scale: int
) -> tuple[list[AdmissionWindow], dict[str, Any]]:
    addressed: set[int] = set()
    windows: list[AdmissionWindow] = []
    all_quantized_weights: list[int] = []
    reference_topologies: list[str] = []
    candidate_graphs: list[str] = []
    relation_hashes: list[str] = []
    geometries: list[tuple[int, int, int, int]] = []
    table_rows: list[tuple[int, int, int]] = []
    topology_equal_windows = 0
    output_map_equal_windows = 0
    total_edges = 0

    for baseline in compiled.windows:
        detection_components = (
            online_base.union_components(
                compiled.model, baseline.detection_detectors
            )
            - addressed
        )
        commit_components = set(baseline.commit_component_ids)
        reference_dem, detector_outputs, observable_outputs = (
            fault_base.build_fault_vector_dem(
                compiled.model,
                baseline.detection_detectors,
                detection_components,
                commit_components,
            )
        )
        candidate_dem, quantized_weights = quantize_dem(
            reference_dem, weight_bits, scale
        )
        reference = pymatching.Matching.from_detector_error_model(
            reference_dem, enable_correlations=True
        )
        candidate = pymatching.Matching.from_detector_error_model(
            candidate_dem, enable_correlations=True
        )
        reference_signature = fault_base.graph_signature(reference)
        candidate_signature = fault_base.graph_signature(candidate)
        baseline_signature = fault_base.graph_signature(baseline.matching)
        reference_topology = [row[0] for row in reference_signature]
        candidate_topology = [row[0] for row in candidate_signature]
        baseline_topology = [row[0] for row in baseline_signature]
        if reference_topology != baseline_topology:
            raise ValueError("reference correction-bit topology changed")
        if candidate_topology != reference_topology:
            raise ValueError("quantization changed graph topology")
        topology_equal_windows += 1
        fault_vector_bits = len(detector_outputs) + len(observable_outputs)
        if (
            reference.num_fault_ids != fault_vector_bits
            or candidate.num_fault_ids != fault_vector_bits
        ):
            raise ValueError("fault-vector output maps changed")
        output_map_equal_windows += 1
        relations = correlation_map(reference_dem)
        undirected_pairs = {
            tuple(sorted((source, target)))
            for source, targets in relations.items()
            for target in targets
        }
        table_rows.append(
            (
                len(relations),
                sum(len(targets) for targets in relations.values()),
                len(undirected_pairs),
            )
        )
        reference_topologies.append(sha_bytes(compact(reference_topology)))
        candidate_graphs.append(sha_bytes(compact(candidate_signature)))
        relation_hashes.append(relation_signature(relations))
        geometries.append(
            (
                candidate.num_nodes,
                candidate.num_edges,
                candidate.num_detectors,
                candidate.num_fault_ids,
            )
        )
        total_edges += candidate.num_edges
        all_quantized_weights.extend(quantized_weights)
        windows.append(
            AdmissionWindow(
                reference=reference,
                candidate=candidate,
                detector_outputs=detector_outputs,
                observable_outputs=observable_outputs,
                fault_vector_bits=fault_vector_bits,
                relations=relations,
            )
        )
        addressed.update(commit_components)

    geometry_counts = Counter(geometries)
    graph_counts = Counter(candidate_graphs)
    steady_geometry, steady_windows = geometry_counts.most_common(1)[0]
    steady_table = Counter(table_rows).most_common(1)[0][0]
    structural = {
        "windows": len(windows),
        "topology_equal_windows": topology_equal_windows,
        "output_map_equal_windows": output_map_equal_windows,
        "unique_reference_topologies": len(set(reference_topologies)),
        "unique_quantized_graphs": len(graph_counts),
        "quantized_graph_multiplicities": sorted(
            graph_counts.values(), reverse=True
        ),
        "steady_windows": steady_windows,
        "steady_geometry": {
            "nodes": steady_geometry[0],
            "edges": steady_geometry[1],
            "detectors": steady_geometry[2],
            "fault_vector_bits": steady_geometry[3],
        },
        "total_edges_across_windows": total_edges,
        "edge_index_bits": math.ceil(
            math.log2(max(window.candidate.num_edges for window in windows))
        ),
        "quantized_group_weight_min": min(all_quantized_weights),
        "quantized_group_weight_max": max(all_quantized_weights),
        "quantized_group_weight_unique": len(set(all_quantized_weights)),
        "quantized_weights_fit_unsigned_width": max(all_quantized_weights)
        < (1 << weight_bits),
        "relation_manifest_sha256": sha_bytes(compact(relation_hashes)),
        "steady_correlation_table": {
            "causal_keys": steady_table[0],
            "directed_relations": steady_table[1],
            "undirected_pairs": steady_table[2],
        },
        "maximum_correlation_table": {
            "causal_keys": max(row[0] for row in table_rows),
            "directed_relations": max(row[1] for row in table_rows),
            "undirected_pairs": max(row[2] for row in table_rows),
        },
    }
    return windows, structural


def all_zero_preflight(
    compiled: online_base.CompiledWindows,
    windows: list[AdmissionWindow],
) -> dict[str, Any]:
    raw = np.zeros(compiled.model.num_detectors, dtype=np.uint8)
    diagnostics = decode_pair(compiled, windows, raw, collect_payload=False)
    if (
        np.any(diagnostics["reference_frame"])
        or np.any(diagnostics["candidate_frame"])
        or diagnostics["reference_commit_residual_failures"]
        or diagnostics["candidate_commit_residual_failures"]
        or diagnostics["reference_final_residual_weight"]
        or diagnostics["candidate_final_residual_weight"]
    ):
        raise ValueError("all-zero admission preflight failed")
    return {
        "reference_frame": diagnostics["reference_frame"].tolist(),
        "candidate_frame": diagnostics["candidate_frame"].tolist(),
        "reference_commit_residual_failures": 0,
        "candidate_commit_residual_failures": 0,
        "reference_final_residual_weight": 0,
        "candidate_final_residual_weight": 0,
    }


def preflight(protocol: dict[str, Any]) -> dict[str, Any]:
    source_protocol = read(
        ROOT / protocol["frozen_inputs"]["fault_vector_protocol"]["path"]
    )
    online_protocol, strict_result = fault_base.load_upstream(source_protocol)
    execution = strict_result["execution"]
    contract = online_protocol["window_contract"]
    weight_bits = protocol["candidate_contract"]["weight_bits"]
    scale = protocol["candidate_contract"]["fixed_point_scale"]
    rows: list[dict[str, Any]] = []
    for basis in execution["memory_bases"]:
        circuit = strict_base.build_circuit(basis, execution)
        compiled = online_base.compile_windows(
            circuit.detector_error_model(decompose_errors=True),
            circuit.get_detector_coordinates(),
            contract["window_size_layers"],
            contract["stride_layers"],
            contract["time_coordinate_index"],
        )
        windows, structural = compile_admission_windows(
            compiled, weight_bits, scale
        )
        rows.append(
            {
                "basis": basis,
                "detectors": circuit.num_detectors,
                "structural": structural,
                "all_zero": all_zero_preflight(compiled, windows),
                "fresh_stochastic_samples_observed": 0,
                "fresh_nonzero_predictions_observed": 0,
            }
        )
    return {
        "schema_version": "b2_b7_p023_d6_microblossom_admission_preflight_v1",
        "scope": protocol["scope"],
        "candidate_weight_bits": weight_bits,
        "fixed_point_scale": scale,
        "rows": rows,
        "fresh_stochastic_samples_observed": 0,
        "fresh_nonzero_predictions_observed": 0,
        "hardware_execution_observed": False,
    }


def decode_pair(
    compiled: online_base.CompiledWindows,
    windows: list[AdmissionWindow],
    raw_syndrome: np.ndarray,
    *,
    collect_payload: bool,
) -> dict[str, Any]:
    raw_syndrome = np.asarray(raw_syndrome, dtype=np.uint8)
    if raw_syndrome.shape != (compiled.model.num_detectors,):
        raise ValueError("raw syndrome shape mismatch")
    states: dict[str, dict[str, np.ndarray]] = {}
    for name in ("reference", "candidate"):
        states[name] = {
            "received": np.zeros(compiled.model.num_detectors, dtype=np.uint8),
            "correction": np.zeros(compiled.model.num_detectors, dtype=np.uint8),
            "frame": np.zeros(compiled.model.num_observables, dtype=np.uint8),
        }
        states[name]["received"][compiled.prebuffer_detectors] = raw_syndrome[
            compiled.prebuffer_detectors
        ]
    selected_edges: list[int] = []
    affected_edges: list[int] = []
    payload_bits: list[int] = []
    output_equal = 0
    syndrome_equal = 0
    reference_commit_failures = 0
    candidate_commit_failures = 0
    for baseline, window in zip(compiled.windows, windows, strict=True):
        for state in states.values():
            state["received"][baseline.arrival_detectors] = raw_syndrome[
                baseline.arrival_detectors
            ]
        reference_syndrome = np.bitwise_xor(
            states["reference"]["received"][baseline.detection_detectors],
            states["reference"]["correction"][baseline.detection_detectors],
        )
        candidate_syndrome = np.bitwise_xor(
            states["candidate"]["received"][baseline.detection_detectors],
            states["candidate"]["correction"][baseline.detection_detectors],
        )
        syndrome_equal += int(
            np.array_equal(reference_syndrome, candidate_syndrome)
        )
        reference_vector = window.reference.decode(
            reference_syndrome, enable_correlations=True
        )
        candidate_vector = window.candidate.decode(
            candidate_syndrome, enable_correlations=True
        )
        output_equal += int(np.array_equal(reference_vector, candidate_vector))
        detector_count = len(window.detector_outputs)
        states["reference"]["correction"][window.detector_outputs] ^= (
            reference_vector[:detector_count]
        )
        states["candidate"]["correction"][window.detector_outputs] ^= (
            candidate_vector[:detector_count]
        )
        states["reference"]["frame"][window.observable_outputs] ^= (
            reference_vector[detector_count:]
        )
        states["candidate"]["frame"][window.observable_outputs] ^= (
            candidate_vector[detector_count:]
        )
        reference_commit = np.bitwise_xor(
            states["reference"]["received"][baseline.commit_detectors],
            states["reference"]["correction"][baseline.commit_detectors],
        )
        candidate_commit = np.bitwise_xor(
            states["candidate"]["received"][baseline.commit_detectors],
            states["candidate"]["correction"][baseline.commit_detectors],
        )
        reference_commit_failures += int(np.any(reference_commit))
        candidate_commit_failures += int(np.any(candidate_commit))
        if collect_payload:
            edge_array = window.candidate.decode_to_edges_array(
                candidate_syndrome, enable_correlations=False
            )
            selected = {
                fault_base.edge_key(
                    int(u), None if int(v) == -1 else int(v)
                )
                for u, v in edge_array
            }
            affected: set[tuple[int, int]] = set()
            for edge in selected:
                affected.update(window.relations.get(edge, set()))
            selected_edges.append(len(selected))
            affected_edges.append(len(affected))
            payload_bits.append(len(affected) * 20)
    reference_residual = np.bitwise_xor(
        states["reference"]["received"], states["reference"]["correction"]
    )
    candidate_residual = np.bitwise_xor(
        states["candidate"]["received"], states["candidate"]["correction"]
    )
    return {
        "reference_frame": states["reference"]["frame"],
        "candidate_frame": states["candidate"]["frame"],
        "reference_commit_residual_failures": reference_commit_failures,
        "candidate_commit_residual_failures": candidate_commit_failures,
        "reference_final_residual_weight": int(
            np.count_nonzero(reference_residual)
        ),
        "candidate_final_residual_weight": int(
            np.count_nonzero(candidate_residual)
        ),
        "window_output_equal": output_equal,
        "window_syndrome_equal": syndrome_equal,
        "selected_edges": selected_edges,
        "affected_edges": affected_edges,
        "payload_bits": payload_bits,
    }


def run_basis(
    basis: str,
    circuit: stim.Circuit,
    compiled: online_base.CompiledWindows,
    windows: list[AdmissionWindow],
    structural: dict[str, Any],
    shots: int,
    seed: int,
    seed_digest: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    sampler = circuit.compile_detector_sampler(seed=seed)
    detectors_packed, observables_packed = sampler.sample(
        shots, separate_observables=True, bit_packed=True
    )
    corpus_header = {
        "basis": basis,
        "shots": shots,
        "seed": seed,
        "seed_digest_sha256": seed_digest,
        "detector_shape": list(detectors_packed.shape),
        "observable_shape": list(observables_packed.shape),
    }
    corpus_sha = sha_bytes(
        compact(corpus_header)
        + b"\x00"
        + detectors_packed.tobytes(order="C")
        + observables_packed.tobytes(order="C")
    )
    full_matching = pymatching.Matching.from_detector_error_model(
        circuit.detector_error_model(decompose_errors=True),
        enable_correlations=True,
    )
    full_packed = latency_base.decode_corpus(
        full_matching, detectors_packed, 256, True
    )
    raw_syndromes = np.unpackbits(
        detectors_packed,
        axis=1,
        count=circuit.num_detectors,
        bitorder="little",
    ).astype(np.uint8, copy=False)
    actual = np.unpackbits(
        observables_packed,
        axis=1,
        count=circuit.num_observables,
        bitorder="little",
    )
    full_predictions = np.unpackbits(
        full_packed,
        axis=1,
        count=circuit.num_observables,
        bitorder="little",
    )
    reference_predictions = np.zeros_like(full_predictions)
    candidate_predictions = np.zeros_like(full_predictions)
    reference_commit_failures = 0
    candidate_commit_failures = 0
    reference_final_failures = 0
    candidate_final_failures = 0
    window_output_equal = 0
    window_syndrome_equal = 0
    selected_edges: list[int] = []
    affected_edges: list[int] = []
    payload_bits: list[int] = []
    for shot_index, raw in enumerate(raw_syndromes):
        diagnostics = decode_pair(compiled, windows, raw, collect_payload=True)
        reference_predictions[shot_index] = diagnostics["reference_frame"]
        candidate_predictions[shot_index] = diagnostics["candidate_frame"]
        reference_commit_failures += diagnostics[
            "reference_commit_residual_failures"
        ]
        candidate_commit_failures += diagnostics[
            "candidate_commit_residual_failures"
        ]
        reference_final_failures += diagnostics["reference_final_residual_weight"] > 0
        candidate_final_failures += diagnostics["candidate_final_residual_weight"] > 0
        window_output_equal += diagnostics["window_output_equal"]
        window_syndrome_equal += diagnostics["window_syndrome_equal"]
        selected_edges.extend(diagnostics["selected_edges"])
        affected_edges.extend(diagnostics["affected_edges"])
        payload_bits.extend(diagnostics["payload_bits"])
        if (shot_index + 1) % 128 == 0:
            print(f"{basis}: decoded {shot_index + 1}/{shots}", flush=True)
    candidate_equal_reference = int(
        np.count_nonzero(
            np.all(candidate_predictions == reference_predictions, axis=1)
        )
    )
    reference_equal_full = int(
        np.count_nonzero(np.all(reference_predictions == full_predictions, axis=1))
    )
    candidate_equal_full = int(
        np.count_nonzero(np.all(candidate_predictions == full_predictions, axis=1))
    )
    full_failures = int(
        np.count_nonzero(np.any(full_predictions != actual, axis=1))
    )
    reference_failures = int(
        np.count_nonzero(np.any(reference_predictions != actual, axis=1))
    )
    candidate_failures = int(
        np.count_nonzero(np.any(candidate_predictions != actual, axis=1))
    )
    semantic_pass = bool(
        candidate_equal_reference == shots
        and reference_equal_full == shots
        and candidate_equal_full == shots
        and reference_commit_failures == 0
        and candidate_commit_failures == 0
        and reference_final_failures == 0
        and candidate_final_failures == 0
    )
    row = {
        "basis": basis,
        "shots": shots,
        "windows_per_shot": len(windows),
        "window_observations": shots * len(windows),
        "semantic_veto_pass": semantic_pass,
        "candidate_prediction_rows_equal_reference_online": candidate_equal_reference,
        "reference_online_prediction_rows_equal_full_block": reference_equal_full,
        "candidate_prediction_rows_equal_full_block": candidate_equal_full,
        "window_syndromes_equal": window_syndrome_equal,
        "window_outputs_equal": window_output_equal,
        "reference_commit_residual_failures": reference_commit_failures,
        "candidate_commit_residual_failures": candidate_commit_failures,
        "reference_final_residual_failure_shots": reference_final_failures,
        "candidate_final_residual_failure_shots": candidate_final_failures,
        "full_block_logical_failures": full_failures,
        "reference_online_logical_failures": reference_failures,
        "candidate_logical_failures": candidate_failures,
        "full_block_prediction_sha256": sha_bytes(
            np.packbits(full_predictions, axis=1, bitorder="little").tobytes()
        ),
        "reference_online_prediction_sha256": sha_bytes(
            np.packbits(reference_predictions, axis=1, bitorder="little").tobytes()
        ),
        "candidate_prediction_sha256": sha_bytes(
            np.packbits(candidate_predictions, axis=1, bitorder="little").tobytes()
        ),
        "structural": structural,
        "controller_payload": {
            "first_pass_selected_edges": distribution(selected_edges),
            "unique_affected_edges_upper_bound": distribution(affected_edges),
            "dynamic_update_payload_bits_upper_bound": distribution(payload_bits),
            "encoding": "12-bit edge index plus 8-bit replacement weight",
        },
    }
    corpus = {
        **corpus_header,
        "corpus_sha256": corpus_sha,
        "raw_circuit_sha256": sha_bytes(str(circuit).encode()),
        "detector_error_model_sha256": sha_bytes(
            str(circuit.detector_error_model(decompose_errors=True)).encode()
        ),
    }
    return row, corpus


def load_and_verify_inputs(
    protocol: dict[str, Any], public_freeze_commit: str
) -> dict[str, Any]:
    artifact_commit = protocol["frozen_inputs"]["artifact_commit"]
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", artifact_commit, public_freeze_commit],
        cwd=ROOT,
        check=True,
    )
    bindings: dict[str, Any] = {}
    for name, binding in protocol["frozen_inputs"].items():
        if name == "artifact_commit":
            continue
        current = sha_path(ROOT / binding["path"])
        committed = sha_bytes(git_blob(artifact_commit, binding["path"]))
        if current != binding["sha256"] or committed != binding["sha256"]:
            raise ValueError(f"frozen input mismatch: {name}")
        bindings[name] = {
            "path": binding["path"],
            "sha256": current,
            "matches_artifact_commit": True,
        }
    return bindings


def build_result(
    protocol: dict[str, Any],
    protocol_path: Path,
    public_freeze_commit: str,
    discussion_number: int,
) -> dict[str, Any]:
    if protocol["scope"]["included_catalog_problem_ids"] != [21, 22, 23]:
        raise ValueError("scope mismatch")
    if discussion_number <= 0:
        raise ValueError("positive discussion number required")
    if pymatching.__version__ != protocol["external_source_profile"][
        "pymatching_version"
    ]:
        raise ValueError("PyMatching version mismatch")
    bindings = load_and_verify_inputs(protocol, public_freeze_commit)
    runner_path = str(Path(__file__).resolve().relative_to(ROOT))
    protocol_rel = str(protocol_path.resolve().relative_to(ROOT))
    if sha_bytes(git_blob(public_freeze_commit, protocol_rel)) != sha_path(
        protocol_path
    ):
        raise ValueError("protocol differs from public freeze")
    if sha_bytes(git_blob(public_freeze_commit, runner_path)) != sha_path(
        Path(__file__).resolve()
    ):
        raise ValueError("runner differs from public freeze")
    source_result = read(
        ROOT / protocol["frozen_inputs"]["fault_vector_result"]["path"]
    )
    if source_result["classification"] != protocol["frozen_inputs"][
        "fault_vector_result"
    ]["required_classification"]:
        raise ValueError("source classification mismatch")
    source_protocol = read(
        ROOT / protocol["frozen_inputs"]["fault_vector_protocol"]["path"]
    )
    online_protocol, strict_result = fault_base.load_upstream(source_protocol)
    execution = strict_result["execution"]
    contract = online_protocol["window_contract"]
    weight_bits = protocol["candidate_contract"]["weight_bits"]
    scale = protocol["candidate_contract"]["fixed_point_scale"]
    shots = protocol["fresh_holdout_contract"]["shots_per_basis"]
    namespace = protocol["fresh_holdout_contract"]["seed_namespace"]
    basis_rows: list[dict[str, Any]] = []
    corpora: list[dict[str, Any]] = []
    for basis in execution["memory_bases"]:
        seed, seed_digest = seed_for(
            public_freeze_commit, discussion_number, namespace, basis
        )
        circuit = strict_base.build_circuit(basis, execution)
        compiled = online_base.compile_windows(
            circuit.detector_error_model(decompose_errors=True),
            circuit.get_detector_coordinates(),
            contract["window_size_layers"],
            contract["stride_layers"],
            contract["time_coordinate_index"],
        )
        windows, structural = compile_admission_windows(
            compiled, weight_bits, scale
        )
        row, corpus = run_basis(
            basis,
            circuit,
            compiled,
            windows,
            structural,
            shots,
            seed,
            seed_digest,
        )
        basis_rows.append(row)
        corpora.append(corpus)
    semantic_pass = all(row["semantic_veto_pass"] for row in basis_rows)
    graph_pass = all(
        row["structural"]["topology_equal_windows"] == 164
        and row["structural"]["output_map_equal_windows"] == 164
        and row["structural"]["quantized_weights_fit_unsigned_width"]
        and row["structural"]["unique_quantized_graphs"] == 3
        for row in basis_rows
    )
    if not semantic_pass:
        classification = "fresh_holdout_semantic_regression"
    elif not graph_pass:
        classification = "eight_bit_graph_admission_failure"
    else:
        classification = (
            "eight_bit_semantic_admission_pass_hardware_execution_unmeasured"
        )
    result: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_microblossom_admission_result_v1",
        "as_of_date": protocol["as_of_date"],
        "question": protocol["question"],
        "scope": protocol["scope"],
        "public_freeze": {
            "commit": public_freeze_commit,
            "discussion_number": discussion_number,
            "discussion_url": f"https://github.com/crystal-tensor/Prometheus-plan/discussions/{discussion_number}",
        },
        "protocol_binding": {
            "path": protocol_rel,
            "sha256": sha_path(protocol_path),
            "runner_path": runner_path,
            "runner_sha256": sha_path(Path(__file__).resolve()),
        },
        "frozen_inputs": bindings,
        "external_source_profile": protocol["external_source_profile"],
        "known_before_preregistration": protocol["known_before_preregistration"],
        "candidate_contract": protocol["candidate_contract"],
        "fresh_holdout_contract": protocol["fresh_holdout_contract"],
        "corpora": corpora,
        "basis_rows": basis_rows,
        "classification_rule": protocol["classification_rule"],
        "classification": classification,
        "kaggle_inspired_evaluation": protocol["kaggle_inspired_evaluation"],
        "verdict": {
            "semantic_veto_pass": semantic_pass,
            "eight_bit_graph_admission_pass": graph_pass,
            "architecture_admission_pass": semantic_pass and graph_pass,
            "micro_blossom_rtl_generated_for_candidate": False,
            "cycle_accurate_candidate_executed": False,
            "fpga_candidate_executed": False,
            "hardware_decoder_deadline_passed": False,
            "full_b2_credit_ready": False,
            "p023_scalable_memory_ready": False,
            "b7_resource_credit": 0,
        },
        "next_gate": (
            "Stop hardware work and repair or reject the 8-bit semantic representation."
            if not (semantic_pass and graph_pass)
            else "Generate the six admitted static graph images, implement on-chip parallel correlation reweighting, and measure exact correction equality plus p99 cycles before any hardware or downstream credit."
        ),
        "execution_environment": {
            "python": platform.python_version(),
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
    }
    checks = [
        check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact catalog scope."),
        check("freeze_binding", len(public_freeze_commit) == 40 and discussion_number > 0, "Public commit and Discussion bind the seeds."),
        check("frozen_inputs", len(bindings) == 5, "Five source artifacts match the predecessor commit."),
        check("source_classification", source_result["classification"] == "public_fault_vector_decode_tail_bottleneck", source_result["classification"]),
        check("basis_set", [row["basis"] for row in basis_rows] == ["x", "z"], "Both memory bases executed."),
        check("seed_separation", len({row["seed"] for row in corpora}) == 2, "X/Z seeds are distinct."),
        check("fresh_shots", all(row["shots"] == shots for row in basis_rows), f"{shots} fresh shots per basis."),
        check("corpus_hashes", all(len(row["corpus_sha256"]) == 64 for row in corpora), "Detector and observable bytes are bound."),
        check("topology", all(row["structural"]["topology_equal_windows"] == 164 for row in basis_rows), "All 328 window topologies match."),
        check("output_maps", all(row["structural"]["output_map_equal_windows"] == 164 for row in basis_rows), "All correction output maps match."),
        check("static_graph_classes", all(row["structural"]["unique_quantized_graphs"] == 3 and row["structural"]["steady_windows"] == 162 for row in basis_rows), "Three graphs per basis; 162 steady windows."),
        check("unsigned_eight_bit", all(row["structural"]["quantized_weights_fit_unsigned_width"] and row["structural"]["quantized_group_weight_max"] <= 255 for row in basis_rows), "Every group weight fits uint8."),
        check("semantic_veto", semantic_pass, "Fresh candidate, online reference, and full-block frames agree."),
        check("residuals", all(row["reference_commit_residual_failures"] == 0 and row["candidate_commit_residual_failures"] == 0 and row["reference_final_residual_failure_shots"] == 0 and row["candidate_final_residual_failure_shots"] == 0 for row in basis_rows), "Every commit and final residual is zero."),
        check("payload_vectors", all(row["controller_payload"]["dynamic_update_payload_bits_upper_bound"]["observations"] == shots * 164 for row in basis_rows), "Complete per-window payload vectors are hashed."),
        check("classification", classification in protocol["classification_rule"]["order"], classification),
        check("hard_boundaries", not result["verdict"]["hardware_decoder_deadline_passed"] and not result["verdict"]["full_b2_credit_ready"] and not result["verdict"]["p023_scalable_memory_ready"] and result["verdict"]["b7_resource_credit"] == 0, "No hardware or downstream credit."),
    ]
    result["checks"] = checks
    result["summary"] = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "fresh_shots_total": sum(row["shots"] for row in basis_rows),
        "semantic_veto_pass": semantic_pass,
        "eight_bit_graph_admission_pass": graph_pass,
        "architecture_admission_pass": semantic_pass and graph_pass,
        "hardware_decoder_deadline_passed": False,
        "full_b2_credit_ready": False,
        "p023_scalable_memory_ready": False,
        "b7_resource_credit": 0,
    }
    result["evidence_id"] = sha_bytes(compact(result))
    if result["summary"]["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"formal checks failed: {failed}")
    return result


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# B2/B7/#023 8-bit Micro Blossom admission v1",
        "",
        "## Question",
        "",
        result["question"],
        "",
        "## Fresh semantic veto",
        "",
        "| basis | candidate = online reference | online reference = full block | window corrections equal | q range | affected edges p99 | update payload p99 (bits) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["basis_rows"]:
        structural = row["structural"]
        payload = row["controller_payload"]
        lines.append(
            f"| {row['basis'].upper()} | {row['candidate_prediction_rows_equal_reference_online']}/{row['shots']} | "
            f"{row['reference_online_prediction_rows_equal_full_block']}/{row['shots']} | "
            f"{row['window_outputs_equal']}/{row['window_observations']} | "
            f"{structural['quantized_group_weight_min']}-{structural['quantized_group_weight_max']} | "
            f"{payload['unique_affected_edges_upper_bound']['p99']:.0f} | "
            f"{payload['dynamic_update_payload_bits_upper_bound']['p99']:.0f} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"Classification: `{result['classification']}`.",
            "",
            f"Semantic veto: `{result['verdict']['semantic_veto_pass']}`. Eight-bit graph admission: `{result['verdict']['eight_bit_graph_admission_pass']}`. Hardware deadline: `false`.",
            "",
            "The admitted object is an integer graph and control-payload contract, not generated RTL, cycle-accurate execution, FPGA timing, LUT/BRAM evidence, or a hardware decoder. Full B2, scalable #023, and B7 credit remain closed.",
            "",
            "## Verification",
            "",
            f"Formal checks: `{result['summary']['checks_passed']}/{result['summary']['checks_total']}`. Evidence ID: `{result['evidence_id']}`.",
            "",
            "## Next gate",
            "",
            result["next_gate"],
            "",
        ]
    )
    return "\n".join(lines)


def render_discussion(result: dict[str, Any]) -> str:
    x, z = result["basis_rows"]
    return "\n".join(
        [
            "# If 8-bit weights preserve every logical answer, what still prevents a sub-microsecond decoder?",
            "",
            "This fresh holdout asks a deliberately narrower question than ‘does Micro Blossom solve our decoder?’ It tests whether the current correlated window semantics can first cross the integer-graph admission boundary without borrowing unmeasured hardware claims.",
            "",
            f"X/Z candidate frames agree with the unquantized online reference on `{x['candidate_prediction_rows_equal_reference_online']}/{x['shots']}` and `{z['candidate_prediction_rows_equal_reference_online']}/{z['shots']}` fresh shots. The online reference also agrees with the full-block correlated reference on `{x['reference_online_prediction_rows_equal_full_block']}/{x['shots']}` and `{z['reference_online_prediction_rows_equal_full_block']}/{z['shots']}`; every commit and final residual is zero.",
            "",
            f"The steady graph is 630 vertices and 2,973 edges and repeats 162/164 windows per basis. Yet a first pass touches only p99 13 selected edges while correlation can expose p99 `{x['controller_payload']['unique_affected_edges_upper_bound']['p99']:.0f}/{z['controller_payload']['unique_affected_edges_upper_bound']['p99']:.0f}` affected X/Z edges—an upper-bound payload of `{x['controller_payload']['dynamic_update_payload_bits_upper_bound']['p99']:.0f}/{z['controller_payload']['dynamic_update_payload_bits_upper_bound']['p99']:.0f}` bits before the second match.",
            "",
            "Heuristic question: should a controller broadcast a compact list of causal first-pass edges into a resident on-chip correlation table, instead of streaming every replacement weight over a bus? What architecture would prove that the broadcast, reweight, second exact match, and correction readout all fit the same p99 clock?",
            "",
            "The boundary is intentional: no candidate RTL was generated or run, and no cycle, FPGA, p99, LUT, BRAM, full B2, #023, or B7 claim is awarded. The next falsifier is a cycle-accurate implementation of the six admitted static graphs with exact correction replay.",
            "",
            f"Evidence ID: `{result['evidence_id']}`.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion-output", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument("--public-freeze-commit")
    parser.add_argument("--discussion-number", type=int)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    protocol = read(args.protocol)
    if args.preflight:
        print(canonical(preflight(protocol)), end="")
        return
    if not args.public_freeze_commit or not args.discussion_number:
        raise SystemExit(
            "--public-freeze-commit and --discussion-number are required after publication"
        )
    result = build_result(
        protocol,
        args.protocol,
        args.public_freeze_commit,
        args.discussion_number,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.discussion_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical(result), encoding="utf-8")
    args.report.write_text(render_report(result), encoding="utf-8")
    args.discussion_output.write_text(render_discussion(result), encoding="utf-8")
    print(
        canonical(
            {
                "classification": result["classification"],
                "evidence_id": result["evidence_id"],
                "summary": result["summary"],
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
