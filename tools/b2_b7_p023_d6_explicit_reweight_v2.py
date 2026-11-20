#!/usr/bin/env python3
"""Explicit fixed-point two-pass decoder bridge for B2/B7/#023.

This module deliberately does not use PyMatching's hidden probability-to-rule
derivation or wide non-integral rescaling for the candidate.  It exports the
correlation rewrite table from the DEM and quantizes both base and implied
weights.  A pinned pybind-only audit adapter injects these integers into the
unchanged two-pass MWPM engine; an adapter-free fallback materializes an
independent second graph.  Every candidate weight is chosen by this module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import scipy
import stim

import b2_b7_p023_d6_correlated_strict_acceptance as strict_base
import b2_b7_p023_d6_fault_vector as fault_base
import b2_b7_p023_d6_decoder_latency_matrix as latency_base
import b2_b7_p023_d6_microblossom_admission as admission_base
import b2_b7_p023_d6_online_window as online_base


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_admission_v1.json"
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_explicit_reweight_v2.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_explicit_reweight_v2.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_explicit_reweight_v2.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_d6_explicit_reweight_discussion_v2.md"


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


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


def cpp_round_nonnegative(value: float) -> int:
    """Match C++ std::round for finite non-negative inputs."""
    if not math.isfinite(value) or value < 0:
        raise ValueError("expected a finite non-negative value")
    return math.floor(value + 0.5)


def bernoulli_xor(left: float, right: float) -> float:
    return left * (1 - right) + right * (1 - left)


def weight_from_probability(probability: float) -> float:
    if not 0 < probability <= 0.5:
        raise ValueError("correlated probability must lie in (0, 0.5]")
    return math.log((1 - probability) / probability)


def even_weight(weight: float, half_weight_scale: int) -> tuple[int, int]:
    """Return the integer half-weight and Micro Blossom's even edge weight."""
    half = cpp_round_nonnegative(weight * half_weight_scale)
    return half, 2 * half


@dataclass(frozen=True)
class EdgeImage:
    node1: int
    node2: int | None
    fault_ids: frozenset[int]
    source_weight: float
    half_weight: int
    even_weight: int

    @property
    def key(self) -> tuple[int, int]:
        return fault_base.edge_key(self.node1, self.node2)


@dataclass
class ExplicitWindow:
    reference: pymatching.Matching
    base_candidate: pymatching.Matching
    explicit_candidate: pymatching.Matching | None
    detector_outputs: np.ndarray
    observable_outputs: np.ndarray
    edges: tuple[EdgeImage, ...]
    base_half_weights: dict[tuple[int, int], int]
    rules: dict[tuple[int, int], tuple[tuple[tuple[int, int], int], ...]]
    graph_image_sha256: str
    rule_image_sha256: str
    cache: dict[tuple[tuple[int, int, int], ...], pymatching.Matching] = field(
        default_factory=dict
    )


def joint_probabilities(
    model: stim.DetectorErrorModel,
) -> dict[tuple[int, int], dict[tuple[int, int], float]]:
    result: dict[tuple[int, int], dict[tuple[int, int], float]] = defaultdict(
        lambda: defaultdict(float)
    )
    for instruction in model:
        if instruction.type != "error":
            continue
        probability = float(instruction.args_copy()[0])
        if probability == 0:
            continue
        if probability > 0.5:
            raise ValueError("probability above 0.5 is unsupported")
        components = admission_base.split_component_keys(instruction)
        for first_index, first in enumerate(components):
            for second in components[first_index + 1 :]:
                result[first][second] = bernoulli_xor(
                    result[first][second], probability
                )
                result[second][first] = bernoulli_xor(
                    result[second][first], probability
                )
        for component in components:
            result[component][component] = bernoulli_xor(
                result[component][component], probability
            )
    return {source: dict(row) for source, row in result.items()}


def correlation_rules(
    model: stim.DetectorErrorModel,
    half_weight_scale: int,
    base_half_weights: dict[tuple[int, int], int],
) -> tuple[
    dict[tuple[int, int], tuple[tuple[tuple[int, int], int], ...]],
    dict[str, Any],
]:
    joint = joint_probabilities(model)
    rules: dict[tuple[int, int], tuple[tuple[tuple[int, int], int], ...]] = {}
    all_half_weights: list[int] = []
    all_even_weights: list[int] = []
    active_rules = 0
    for source in sorted(joint):
        if source not in base_half_weights:
            raise ValueError(f"causal edge absent from base graph: {source}")
        marginal = joint[source].get(source, 0.0)
        if marginal == 0:
            continue
        row: list[tuple[tuple[int, int], int]] = []
        for target, joint_probability in sorted(joint[source].items()):
            if target == source:
                continue
            if target not in base_half_weights:
                raise ValueError(f"rewrite target absent from base graph: {target}")
            implied_probability = min(0.5, joint_probability / marginal)
            half, even = even_weight(
                weight_from_probability(implied_probability), half_weight_scale
            )
            row.append((target, half))
            all_half_weights.append(half)
            all_even_weights.append(even)
            active_rules += int(half < base_half_weights[target])
        if row:
            rules[source] = tuple(row)
    manifest = [
        [list(source), [[list(target), half] for target, half in row]]
        for source, row in sorted(rules.items())
    ]
    stats = {
        "causal_edges": len(rules),
        "directed_rules": len(all_half_weights),
        "active_lowering_rules": active_rules,
        "implied_half_weight_min": min(all_half_weights),
        "implied_half_weight_max": max(all_half_weights),
        "implied_even_weight_min": min(all_even_weights),
        "implied_even_weight_max": max(all_even_weights),
        "implied_even_weight_unique": len(set(all_even_weights)),
        "zero_even_weight_rules": sum(weight == 0 for weight in all_even_weights),
        "rule_image_sha256": sha_bytes(compact(manifest)),
    }
    return rules, stats


def extract_edges(
    matching: pymatching.Matching, half_weight_scale: int
) -> tuple[tuple[EdgeImage, ...], dict[str, Any]]:
    edges: list[EdgeImage] = []
    for node1, node2, data in matching.edges():
        source_weight = float(data["weight"])
        if source_weight < 0:
            raise ValueError("negative edge weight is outside this candidate")
        half, even = even_weight(source_weight, half_weight_scale)
        edges.append(
            EdgeImage(
                node1=int(node1),
                node2=None if node2 is None else int(node2),
                fault_ids=frozenset(int(value) for value in data["fault_ids"]),
                source_weight=source_weight,
                half_weight=half,
                even_weight=even,
            )
        )
    edges.sort(key=lambda edge: edge.key)
    if len({edge.key for edge in edges}) != len(edges):
        raise ValueError("parallel edge survived PyMatching graph construction")
    manifest = [
        [
            list(edge.key),
            sorted(edge.fault_ids),
            edge.half_weight,
            edge.even_weight,
        ]
        for edge in edges
    ]
    even_weights = [edge.even_weight for edge in edges]
    stats = {
        "edges": len(edges),
        "base_half_weight_min": min(edge.half_weight for edge in edges),
        "base_half_weight_max": max(edge.half_weight for edge in edges),
        "base_even_weight_min": min(even_weights),
        "base_even_weight_max": max(even_weights),
        "base_even_weight_unique": len(set(even_weights)),
        "base_even_weights_all_even": all(weight % 2 == 0 for weight in even_weights),
        "base_even_weight_bits": max(even_weights).bit_length(),
        "graph_image_sha256": sha_bytes(compact(manifest)),
    }
    return tuple(edges), stats


def build_integer_matching(
    edges: tuple[EdgeImage, ...],
    replacements: dict[tuple[int, int], int] | None = None,
) -> pymatching.Matching:
    replacements = replacements or {}
    matching = pymatching.Matching()
    for edge in edges:
        half_weight = replacements.get(edge.key, edge.half_weight)
        kwargs = {
            "fault_ids": set(edge.fault_ids),
            "weight": float(half_weight),
        }
        if edge.node2 is None:
            matching.add_boundary_edge(edge.node1, **kwargs)
        else:
            matching.add_edge(edge.node1, edge.node2, **kwargs)
    return matching


def build_correlated_integer_matching(
    edges: tuple[EdgeImage, ...],
    rules: dict[tuple[int, int], tuple[tuple[tuple[int, int], int], ...]],
) -> pymatching.Matching | None:
    """Use the pinned audit adapter when its two explicit-rule methods exist."""
    matching = pymatching.Matching()
    graph = matching._matching_graph
    if not (
        hasattr(graph, "add_edge_with_implied_weights")
        and hasattr(graph, "add_boundary_edge_with_implied_weights")
    ):
        return None
    for edge in edges:
        implied = [
            (target[0], target[1], float(half_weight))
            for target, half_weight in rules.get(edge.key, ())
        ]
        if edge.node2 is None:
            graph.add_boundary_edge_with_implied_weights(
                edge.node1,
                set(edge.fault_ids),
                float(edge.half_weight),
                implied,
            )
        else:
            graph.add_edge_with_implied_weights(
                edge.node1,
                edge.node2,
                set(edge.fault_ids),
                float(edge.half_weight),
                implied,
            )
    return matching


def compile_window(
    model: stim.DetectorErrorModel,
    detector_outputs: np.ndarray,
    observable_outputs: np.ndarray,
    half_weight_scale: int,
) -> tuple[ExplicitWindow, dict[str, Any]]:
    reference = pymatching.Matching.from_detector_error_model(
        model, enable_correlations=True
    )
    edges, edge_stats = extract_edges(reference, half_weight_scale)
    base_half_weights = {edge.key: edge.half_weight for edge in edges}
    rules, rule_stats = correlation_rules(
        model, half_weight_scale, base_half_weights
    )
    base_candidate = build_integer_matching(edges)
    explicit_candidate = build_correlated_integer_matching(edges, rules)
    if base_candidate.num_edges != reference.num_edges:
        raise ValueError("integer graph edge count changed")
    if base_candidate.num_fault_ids != reference.num_fault_ids:
        raise ValueError("integer graph fault-vector width changed")
    if explicit_candidate is not None and (
        explicit_candidate.num_edges != reference.num_edges
        or explicit_candidate.num_fault_ids != reference.num_fault_ids
    ):
        raise ValueError("explicit correlated graph shape changed")
    window = ExplicitWindow(
        reference=reference,
        base_candidate=base_candidate,
        explicit_candidate=explicit_candidate,
        detector_outputs=detector_outputs,
        observable_outputs=observable_outputs,
        edges=edges,
        base_half_weights=base_half_weights,
        rules=rules,
        graph_image_sha256=edge_stats["graph_image_sha256"],
        rule_image_sha256=rule_stats["rule_image_sha256"],
    )
    return window, {**edge_stats, **rule_stats}


def selected_edge_keys(
    matching: pymatching.Matching, syndrome: np.ndarray
) -> tuple[tuple[int, int], ...]:
    edge_array = matching.decode_to_edges_array(
        syndrome, enable_correlations=False
    )
    return tuple(
        sorted(
            {
                fault_base.edge_key(
                    int(node1), None if int(node2) == -1 else int(node2)
                )
                for node1, node2 in edge_array
            }
        )
    )


def explicit_decode(
    window: ExplicitWindow, syndrome: np.ndarray
) -> tuple[np.ndarray, dict[str, int]]:
    selected = selected_edge_keys(window.base_candidate, syndrome)
    replacements: dict[tuple[int, int], int] = {}
    for source in selected:
        for target, half_weight in window.rules.get(source, ()):
            current = replacements.get(target, window.base_half_weights[target])
            if half_weight < current:
                replacements[target] = half_weight
    cache_key = tuple(
        (target[0], target[1], half_weight)
        for target, half_weight in sorted(replacements.items())
    )
    if window.explicit_candidate is not None:
        prediction = window.explicit_candidate.decode(
            syndrome, enable_correlations=True
        )
    elif not cache_key:
        second_pass = window.base_candidate
        prediction = second_pass.decode(syndrome, enable_correlations=False)
    else:
        second_pass = window.cache.get(cache_key)
        if second_pass is None:
            second_pass = build_integer_matching(window.edges, replacements)
            window.cache[cache_key] = second_pass
        prediction = second_pass.decode(syndrome, enable_correlations=False)
    return prediction, {
        "selected_edges": len(selected),
        "replacement_edges": len(replacements),
        "replacement_payload_bits": len(replacements) * 28,
    }


def compile_basis(
    basis: str, half_weight_scale: int
) -> tuple[stim.Circuit, online_base.CompiledWindows, list[ExplicitWindow], dict[str, Any]]:
    source_protocol = admission_base.read(admission_base.DEFAULT_PROTOCOL)
    fault_protocol = admission_base.read(
        ROOT / source_protocol["frozen_inputs"]["fault_vector_protocol"]["path"]
    )
    online_protocol, strict_result = fault_base.load_upstream(fault_protocol)
    execution = strict_result["execution"]
    contract = online_protocol["window_contract"]
    circuit = strict_base.build_circuit(basis, execution)
    compiled = online_base.compile_windows(
        circuit.detector_error_model(decompose_errors=True),
        circuit.get_detector_coordinates(),
        contract["window_size_layers"],
        contract["stride_layers"],
        contract["time_coordinate_index"],
    )
    addressed: set[int] = set()
    windows: list[ExplicitWindow] = []
    rows: list[dict[str, Any]] = []
    for baseline in compiled.windows:
        detection_components = (
            online_base.union_components(
                compiled.model, baseline.detection_detectors
            )
            - addressed
        )
        commit_components = set(baseline.commit_component_ids)
        model, detector_outputs, observable_outputs = fault_base.build_fault_vector_dem(
            compiled.model,
            baseline.detection_detectors,
            detection_components,
            commit_components,
        )
        window, stats = compile_window(
            model, detector_outputs, observable_outputs, half_weight_scale
        )
        windows.append(window)
        rows.append(stats)
        addressed.update(commit_components)
    graph_counts = Counter(window.graph_image_sha256 for window in windows)
    rule_counts = Counter(window.rule_image_sha256 for window in windows)
    structural = {
        "basis": basis,
        "windows": len(windows),
        "half_weight_scale": half_weight_scale,
        "stored_even_weight_scale": 2 * half_weight_scale,
        "explicit_rule_adapter_active": all(
            window.explicit_candidate is not None for window in windows
        ),
        "unique_graph_images": len(graph_counts),
        "graph_image_multiplicities": sorted(graph_counts.values(), reverse=True),
        "unique_rule_images": len(rule_counts),
        "rule_image_multiplicities": sorted(rule_counts.values(), reverse=True),
        "base_even_weight_min": min(row["base_even_weight_min"] for row in rows),
        "base_even_weight_max": max(row["base_even_weight_max"] for row in rows),
        "base_even_weight_bits": max(row["base_even_weight_bits"] for row in rows),
        "base_even_weights_all_even": all(
            row["base_even_weights_all_even"] for row in rows
        ),
        "implied_even_weight_min": min(
            row["implied_even_weight_min"] for row in rows
        ),
        "implied_even_weight_max": max(
            row["implied_even_weight_max"] for row in rows
        ),
        "maximum_directed_rules": max(row["directed_rules"] for row in rows),
        "maximum_active_lowering_rules": max(
            row["active_lowering_rules"] for row in rows
        ),
        "graph_sequence_sha256": sha_bytes(
            compact([window.graph_image_sha256 for window in windows])
        ),
        "rule_sequence_sha256": sha_bytes(
            compact([window.rule_image_sha256 for window in windows])
        ),
    }
    return circuit, compiled, windows, structural


def decode_online_pair(
    compiled: online_base.CompiledWindows,
    windows: list[ExplicitWindow],
    raw_syndrome: np.ndarray,
) -> dict[str, Any]:
    raw_syndrome = np.asarray(raw_syndrome, dtype=np.uint8)
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
    output_equal = 0
    syndrome_equal = 0
    selected_edges: list[int] = []
    replacement_edges: list[int] = []
    replacement_payload_bits: list[int] = []
    commit_failures = {"reference": 0, "candidate": 0}
    for baseline, window in zip(compiled.windows, windows, strict=True):
        for state in states.values():
            state["received"][baseline.arrival_detectors] = raw_syndrome[
                baseline.arrival_detectors
            ]
        syndromes = {
            name: np.bitwise_xor(
                state["received"][baseline.detection_detectors],
                state["correction"][baseline.detection_detectors],
            )
            for name, state in states.items()
        }
        syndrome_equal += int(
            np.array_equal(syndromes["reference"], syndromes["candidate"])
        )
        predictions = {
            "reference": window.reference.decode(
                syndromes["reference"], enable_correlations=True
            )
        }
        predictions["candidate"], diagnostics = explicit_decode(
            window, syndromes["candidate"]
        )
        selected_edges.append(diagnostics["selected_edges"])
        replacement_edges.append(diagnostics["replacement_edges"])
        replacement_payload_bits.append(diagnostics["replacement_payload_bits"])
        output_equal += int(
            np.array_equal(predictions["reference"], predictions["candidate"])
        )
        detector_count = len(window.detector_outputs)
        for name, prediction in predictions.items():
            states[name]["correction"][window.detector_outputs] ^= prediction[
                :detector_count
            ]
            states[name]["frame"][window.observable_outputs] ^= prediction[
                detector_count:
            ]
            commit = np.bitwise_xor(
                states[name]["received"][baseline.commit_detectors],
                states[name]["correction"][baseline.commit_detectors],
            )
            commit_failures[name] += int(np.any(commit))
    residuals = {
        name: int(
            np.count_nonzero(
                np.bitwise_xor(state["received"], state["correction"])
            )
        )
        for name, state in states.items()
    }
    return {
        "reference_frame": states["reference"]["frame"],
        "candidate_frame": states["candidate"]["frame"],
        "window_syndromes_equal": syndrome_equal,
        "window_outputs_equal": output_equal,
        "reference_commit_failures": commit_failures["reference"],
        "candidate_commit_failures": commit_failures["candidate"],
        "reference_final_residual_weight": residuals["reference"],
        "candidate_final_residual_weight": residuals["candidate"],
        "selected_edge_counts": selected_edges,
        "replacement_edge_counts": replacement_edges,
        "replacement_payload_bits": replacement_payload_bits,
    }


def all_zero_preflight(
    compiled: online_base.CompiledWindows,
    windows: list[ExplicitWindow],
) -> dict[str, Any]:
    diagnostics = decode_online_pair(
        compiled,
        windows,
        np.zeros(compiled.model.num_detectors, dtype=np.uint8),
    )
    if (
        np.any(diagnostics["reference_frame"])
        or np.any(diagnostics["candidate_frame"])
        or diagnostics["reference_commit_failures"]
        or diagnostics["candidate_commit_failures"]
        or diagnostics["reference_final_residual_weight"]
        or diagnostics["candidate_final_residual_weight"]
    ):
        raise ValueError("all-zero explicit-reweight preflight failed")
    return {
        "reference_frame": diagnostics["reference_frame"].tolist(),
        "candidate_frame": diagnostics["candidate_frame"].tolist(),
        "window_outputs_equal": diagnostics["window_outputs_equal"],
        "window_syndromes_equal": diagnostics["window_syndromes_equal"],
        "reference_commit_failures": 0,
        "candidate_commit_failures": 0,
        "reference_final_residual_weight": 0,
        "candidate_final_residual_weight": 0,
        "selected_edge_distribution": distribution(
            diagnostics["selected_edge_counts"]
        ),
        "replacement_edge_distribution": distribution(
            diagnostics["replacement_edge_counts"]
        ),
    }


def preflight(protocol: dict[str, Any]) -> dict[str, Any]:
    scale = int(protocol["candidate_contract"]["half_weight_scale"])
    rows: list[dict[str, Any]] = []
    for basis in protocol["fresh_holdout_contract"]["memory_bases"]:
        _, compiled, windows, structural = compile_basis(basis, scale)
        if not structural["explicit_rule_adapter_active"]:
            raise ValueError("pinned explicit-rule adapter is not active")
        rows.append(
            {
                "basis": basis,
                "structural": structural,
                "all_zero": all_zero_preflight(compiled, windows),
                "fresh_stochastic_samples_observed": 0,
                "fresh_nonzero_predictions_observed": 0,
            }
        )
    return {
        "schema_version": "b2_b7_p023_d6_explicit_reweight_preflight_v2",
        "scope": protocol["scope"],
        "half_weight_scale": scale,
        "stored_even_weight_scale": 2 * scale,
        "rows": rows,
        "fresh_stochastic_samples_observed": 0,
        "fresh_nonzero_predictions_observed": 0,
        "hardware_execution_observed": False,
    }


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
        path = ROOT / binding["path"]
        current = sha_path(path)
        committed = sha_bytes(git_blob(artifact_commit, binding["path"]))
        if current != binding["sha256"] or committed != binding["sha256"]:
            raise ValueError(f"frozen input mismatch: {name}")
        bindings[name] = {
            "path": binding["path"],
            "sha256": current,
            "matches_artifact_commit": True,
        }
    return bindings


def run_basis(
    basis: str,
    circuit: stim.Circuit,
    compiled: online_base.CompiledWindows,
    windows: list[ExplicitWindow],
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
    replacement_edges: list[int] = []
    payload_bits: list[int] = []
    for shot_index, raw in enumerate(raw_syndromes):
        diagnostics = decode_online_pair(compiled, windows, raw)
        reference_predictions[shot_index] = diagnostics["reference_frame"]
        candidate_predictions[shot_index] = diagnostics["candidate_frame"]
        reference_commit_failures += diagnostics["reference_commit_failures"]
        candidate_commit_failures += diagnostics["candidate_commit_failures"]
        reference_final_failures += int(
            diagnostics["reference_final_residual_weight"] > 0
        )
        candidate_final_failures += int(
            diagnostics["candidate_final_residual_weight"] > 0
        )
        window_output_equal += diagnostics["window_outputs_equal"]
        window_syndrome_equal += diagnostics["window_syndromes_equal"]
        selected_edges.extend(diagnostics["selected_edge_counts"])
        replacement_edges.extend(diagnostics["replacement_edge_counts"])
        payload_bits.extend(diagnostics["replacement_payload_bits"])
        if (shot_index + 1) % 128 == 0:
            print(f"{basis}: explicit decoded {shot_index + 1}/{shots}", flush=True)
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
    window_observations = shots * len(windows)
    semantic_pass = bool(
        candidate_equal_reference == shots
        and reference_equal_full == shots
        and candidate_equal_full == shots
        and window_output_equal == window_observations
        and window_syndrome_equal == window_observations
        and reference_commit_failures == 0
        and candidate_commit_failures == 0
        and reference_final_failures == 0
        and candidate_final_failures == 0
    )
    row = {
        "basis": basis,
        "shots": shots,
        "windows_per_shot": len(windows),
        "window_observations": window_observations,
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
            "actually_lowered_replacement_edges": distribution(replacement_edges),
            "dynamic_update_payload_bits": distribution(payload_bits),
            "encoding": "12-bit edge index plus 16-bit even replacement weight",
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
    graph = pymatching.Matching()._matching_graph
    adapter_active = bool(
        hasattr(graph, "add_edge_with_implied_weights")
        and hasattr(graph, "add_boundary_edge_with_implied_weights")
    )
    if not adapter_active:
        raise ValueError("pinned explicit-rule adapter is not active")
    bindings = load_and_verify_inputs(protocol, public_freeze_commit)
    runner_path = str(Path(__file__).resolve().relative_to(ROOT))
    protocol_rel = str(protocol_path.resolve().relative_to(ROOT))
    patch_path = protocol["adapter_contract"]["patch"]["path"]
    if sha_bytes(git_blob(public_freeze_commit, protocol_rel)) != sha_path(
        protocol_path
    ):
        raise ValueError("protocol differs from public freeze")
    if sha_bytes(git_blob(public_freeze_commit, runner_path)) != sha_path(
        Path(__file__).resolve()
    ):
        raise ValueError("runner differs from public freeze")
    if (
        sha_path(ROOT / patch_path)
        != protocol["adapter_contract"]["patch"]["sha256"]
        or sha_bytes(git_blob(public_freeze_commit, patch_path))
        != protocol["adapter_contract"]["patch"]["sha256"]
    ):
        raise ValueError("adapter patch binding mismatch")
    scale = int(protocol["candidate_contract"]["half_weight_scale"])
    shots = int(protocol["fresh_holdout_contract"]["shots_per_basis"])
    namespace = protocol["fresh_holdout_contract"]["seed_namespace"]
    basis_rows: list[dict[str, Any]] = []
    corpora: list[dict[str, Any]] = []
    for basis in protocol["fresh_holdout_contract"]["memory_bases"]:
        seed, seed_digest = seed_for(
            public_freeze_commit, discussion_number, namespace, basis
        )
        circuit, compiled, windows, structural = compile_basis(basis, scale)
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
    representation_pass = all(
        row["structural"]["explicit_rule_adapter_active"]
        and row["structural"]["base_even_weights_all_even"]
        and row["structural"]["base_even_weight_bits"] <= 16
        and row["structural"]["implied_even_weight_max"] <= 65535
        and row["structural"]["unique_graph_images"] == 3
        and row["structural"]["unique_rule_images"] == 3
        for row in basis_rows
    )
    if not semantic_pass:
        classification = "fresh_holdout_explicit_reweight_semantic_regression"
    elif not representation_pass:
        classification = "sixteen_bit_even_representation_failure"
    else:
        classification = (
            "sixteen_bit_explicit_reweight_semantic_pass_hardware_write_path_absent"
        )
    result: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_explicit_reweight_result_v2",
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
            "adapter_patch_path": patch_path,
            "adapter_patch_sha256": sha_path(ROOT / patch_path),
        },
        "frozen_inputs": bindings,
        "external_source_profile": protocol["external_source_profile"],
        "adapter_contract": protocol["adapter_contract"],
        "known_before_preregistration": protocol["known_before_preregistration"],
        "candidate_contract": protocol["candidate_contract"],
        "fresh_holdout_contract": protocol["fresh_holdout_contract"],
        "corpora": corpora,
        "basis_rows": basis_rows,
        "classification_rule": protocol["classification_rule"],
        "classification": classification,
        "kaggle_inspired_evaluation": protocol["kaggle_inspired_evaluation"],
        "prior_result_correction": protocol["prior_result_correction"],
        "verdict": {
            "semantic_veto_pass": semantic_pass,
            "sixteen_bit_even_representation_pass": representation_pass,
            "explicit_dynamic_reweight_software_bridge_pass": semantic_pass
            and representation_pass,
            "micro_blossom_dynamic_weight_write_path_implemented": False,
            "micro_blossom_rtl_generated_for_candidate": False,
            "cycle_accurate_candidate_executed": False,
            "fpga_candidate_executed": False,
            "hardware_decoder_deadline_passed": False,
            "full_b2_credit_ready": False,
            "p023_scalable_memory_ready": False,
            "b7_resource_credit": 0,
        },
        "next_gate": (
            "Stop the fixed-point route and repair or reject the explicit representation."
            if not (semantic_pass and representation_pass)
            else "Implement the missing Micro Blossom dynamic-weight register/write path, generate the six bound graph/rule images, and measure exact correction equality plus p99 cycles before hardware credit."
        ),
        "execution_environment": {
            "python": platform.python_version(),
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "pymatching_module": str(Path(pymatching.__file__).resolve()),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "explicit_rule_adapter_active": adapter_active,
        },
    }
    checks = [
        check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact catalog scope."),
        check("freeze_binding", len(public_freeze_commit) == 40 and discussion_number > 0, "Public commit and Discussion bind the seeds."),
        check("frozen_inputs", len(bindings) == 4, "Four predecessor artifacts match their public commit."),
        check("adapter_patch", adapter_active and len(sha_path(ROOT / patch_path)) == 64, "Pinned adapter exposes only explicit rule insertion."),
        check("basis_set", [row["basis"] for row in basis_rows] == ["x", "z"], "Both memory bases executed."),
        check("seed_separation", len({row["seed"] for row in corpora}) == 2, "X/Z seeds are distinct."),
        check("fresh_shots", all(row["shots"] == shots for row in basis_rows), f"{shots} fresh shots per basis."),
        check("corpus_hashes", all(len(row["corpus_sha256"]) == 64 for row in corpora), "Detector and observable bytes are bound."),
        check("static_images", all(row["structural"]["unique_graph_images"] == 3 and row["structural"]["unique_rule_images"] == 3 for row in basis_rows), "Three graph and rule images per basis."),
        check("even_sixteen_bit", all(row["structural"]["base_even_weights_all_even"] and row["structural"]["base_even_weight_bits"] <= 16 and row["structural"]["implied_even_weight_max"] <= 65535 for row in basis_rows), "All base and implied weights fit unsigned sixteen-bit even storage."),
        check(
            "semantic_veto_adjudicated",
            (
                semantic_pass
                and classification
                != "fresh_holdout_explicit_reweight_semantic_regression"
            )
            or (
                not semantic_pass
                and classification
                == "fresh_holdout_explicit_reweight_semantic_regression"
            ),
            "The classification records the exact per-window semantic veto without preventing a negative result artifact.",
        ),
        check("residuals", all(row["reference_commit_residual_failures"] == 0 and row["candidate_commit_residual_failures"] == 0 and row["reference_final_residual_failure_shots"] == 0 and row["candidate_final_residual_failure_shots"] == 0 for row in basis_rows), "Every commit and final residual is zero."),
        check("payload_vectors", all(row["controller_payload"]["dynamic_update_payload_bits"]["observations"] == shots * 164 for row in basis_rows), "Complete per-window payload vectors are hashed."),
        check("classification", classification in protocol["classification_rule"]["order"], classification),
        check("source_gap", not result["verdict"]["micro_blossom_dynamic_weight_write_path_implemented"], "Pinned RTL keeps the dynamic write path TODO/commented."),
        check("hard_boundaries", not result["verdict"]["hardware_decoder_deadline_passed"] and not result["verdict"]["full_b2_credit_ready"] and not result["verdict"]["p023_scalable_memory_ready"] and result["verdict"]["b7_resource_credit"] == 0, "No hardware or downstream credit."),
    ]
    result["checks"] = checks
    result["summary"] = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "fresh_shots_total": sum(row["shots"] for row in basis_rows),
        "semantic_veto_pass": semantic_pass,
        "sixteen_bit_even_representation_pass": representation_pass,
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
        "# B2/B7/#023 explicit 16-bit correlation reweight v2",
        "",
        "## Question",
        "",
        result["question"],
        "",
        "## Fresh semantic veto",
        "",
        "| basis | candidate = online reference | online reference = full block | window outputs equal | base even range | implied even range | replacements p99 | payload p99 (bits) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in result["basis_rows"]:
        structural = row["structural"]
        payload = row["controller_payload"]
        lines.append(
            f"| {row['basis'].upper()} | {row['candidate_prediction_rows_equal_reference_online']}/{row['shots']} | "
            f"{row['reference_online_prediction_rows_equal_full_block']}/{row['shots']} | "
            f"{row['window_outputs_equal']}/{row['window_observations']} | "
            f"{structural['base_even_weight_min']}-{structural['base_even_weight_max']} | "
            f"{structural['implied_even_weight_min']}-{structural['implied_even_weight_max']} | "
            f"{payload['actually_lowered_replacement_edges']['p99']:.0f} | "
            f"{payload['dynamic_update_payload_bits']['p99']:.0f} |"
        )
    lines.extend(
        [
            "",
            "## Correction to the prior admission result",
            "",
            result["prior_result_correction"]["summary"],
            "",
            "## Decision",
            "",
            f"Classification: `{result['classification']}`.",
            "",
            (
                "The semantic veto admits an explicit integer software graph plus rewrite table. "
                if result["verdict"]["semantic_veto_pass"]
                else "The semantic veto rejects this explicit integer software graph plus rewrite table. "
            )
            + "The pinned Micro Blossom source still reserves an opcode while leaving the dynamic edge-weight write path unimplemented; no generated RTL, cycle, FPGA, timing, LUT/BRAM, full B2, #023, or B7 credit follows.",
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
            "# When exact streaming equivalence costs seven more bits, is that a decoder fix or a hardware warning?",
            "",
            "The public 9-bit experiment ended with identical final X/Z frames but 58 transient output disagreements, so the strict streaming veto failed. Post-outcome route selection then found a principled power-of-two scale whose already-public corpus has zero syndrome and output disagreements; this fresh holdout asks whether that observation generalizes.",
            "",
            f"This fresh test removes that ambiguity. Every base edge and every correlation-conditioned replacement is injected explicitly on one even-integer grid. X/Z candidate frames agree with the high-precision online reference on `{x['candidate_prediction_rows_equal_reference_online']}/{x['shots']}` and `{z['candidate_prediction_rows_equal_reference_online']}/{z['shots']}` fresh shots; online reference equals full block on `{x['reference_online_prediction_rows_equal_full_block']}/{x['shots']}` and `{z['reference_online_prediction_rows_equal_full_block']}/{z['shots']}`.",
            "",
            f"The strict streaming comparison is X `{x['window_observations'] - x['window_syndromes_equal']}` syndrome and `{x['window_observations'] - x['window_outputs_equal']}` output mismatches, and Z `{z['window_observations'] - z['window_syndromes_equal']}` syndrome and `{z['window_observations'] - z['window_outputs_equal']}` output mismatches. Semantic veto: `{'pass' if result['verdict']['semantic_veto_pass'] else 'fail'}`.",
            "",
            f"The actual stored range is X `{x['structural']['base_even_weight_min']}..{x['structural']['base_even_weight_max']}` and Z `{z['structural']['base_even_weight_min']}..{z['structural']['base_even_weight_max']}` for base edges, with implied weights ending at `{max(x['structural']['implied_even_weight_max'], z['structural']['implied_even_weight_max'])}`. The p99 number of actually lowered X/Z edges is `{x['controller_payload']['actually_lowered_replacement_edges']['p99']:.0f}/{z['controller_payload']['actually_lowered_replacement_edges']['p99']:.0f}`, or `{x['controller_payload']['dynamic_update_payload_bits']['p99']:.0f}/{z['controller_payload']['dynamic_update_payload_bits']['p99']:.0f}` raw bits at 12-bit index + 16-bit weight.",
            "",
            "Heuristic question: if exact transient equivalence needs 16-bit weights while 9-bit weights recover the same final logical frame, should hardware pay the wider bandwidth, or should the interface expose a weaker—but explicitly justified—contract? What experiment would distinguish harmless resynchronization from a future feedback failure?",
            "",
            "The boundary matters: this is a pinned software semantic bridge, not Micro Blossom RTL execution. Until the missing write path exists and p99 cycles are measured, the one-microsecond deadline, full B2, scalable #023 memory, and B7 resource credit remain closed.",
            "",
            f"Evidence ID: `{result['evidence_id']}`.",
            "",
        ]
    )


def development_check(
    basis: str, shots: int, half_weight_scale: int
) -> dict[str, Any]:
    source = admission_base.read(DEFAULT_SOURCE_RESULT)
    corpus = next(row for row in source["corpora"] if row["basis"] == basis)
    circuit, compiled, windows, structural = compile_basis(
        basis, half_weight_scale
    )
    sampler = circuit.compile_detector_sampler(seed=int(corpus["seed"]))
    detector_packed, _ = sampler.sample(
        shots, separate_observables=True, bit_packed=True
    )
    raw = np.unpackbits(
        detector_packed,
        axis=1,
        count=circuit.num_detectors,
        bitorder="little",
    ).astype(np.uint8, copy=False)
    equal_frames = 0
    window_outputs_equal = 0
    window_syndromes_equal = 0
    reference_commit_failures = 0
    candidate_commit_failures = 0
    reference_final_failures = 0
    candidate_final_failures = 0
    selected_edges = 0
    replacement_edges = 0
    payload_bits = 0
    for shot_index, syndrome in enumerate(raw):
        row = decode_online_pair(compiled, windows, syndrome)
        equal_frames += int(
            np.array_equal(row["reference_frame"], row["candidate_frame"])
        )
        window_outputs_equal += row["window_outputs_equal"]
        window_syndromes_equal += row["window_syndromes_equal"]
        reference_commit_failures += row["reference_commit_failures"]
        candidate_commit_failures += row["candidate_commit_failures"]
        reference_final_failures += int(row["reference_final_residual_weight"] > 0)
        candidate_final_failures += int(row["candidate_final_residual_weight"] > 0)
        selected_edges += sum(row["selected_edge_counts"])
        replacement_edges += sum(row["replacement_edge_counts"])
        payload_bits += sum(row["replacement_payload_bits"])
        print(f"{basis}: explicit {shot_index + 1}/{shots}", flush=True)
    return {
        "schema_version": "b2_b7_p023_d6_explicit_reweight_development_v2",
        "basis": basis,
        "shots": shots,
        "source_public_corpus_seed": int(corpus["seed"]),
        "source_public_corpus_sha256": corpus["corpus_sha256"],
        "half_weight_scale": half_weight_scale,
        "stored_even_weight_scale": 2 * half_weight_scale,
        "structural": structural,
        "candidate_frames_equal_hidden_reference": equal_frames,
        "window_outputs_equal": window_outputs_equal,
        "window_observations": shots * len(windows),
        "window_syndromes_equal": window_syndromes_equal,
        "reference_commit_failures": reference_commit_failures,
        "candidate_commit_failures": candidate_commit_failures,
        "reference_final_failure_shots": reference_final_failures,
        "candidate_final_failure_shots": candidate_final_failures,
        "selected_edges_total": selected_edges,
        "replacement_edges_total": replacement_edges,
        "replacement_payload_bits_total": payload_bits,
        "matching_cache_entries": sum(len(window.cache) for window in windows),
        "semantic_pass": bool(
            equal_frames == shots
            and window_outputs_equal == shots * len(windows)
            and window_syndromes_equal == shots * len(windows)
            and reference_commit_failures == 0
            and candidate_commit_failures == 0
            and reference_final_failures == 0
            and candidate_final_failures == 0
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion-output", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument("--public-freeze-commit")
    parser.add_argument("--discussion-number", type=int)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--development-check", action="store_true")
    parser.add_argument("--basis", choices=("x", "z"))
    parser.add_argument("--shots", type=int, default=16)
    parser.add_argument("--half-weight-scale", type=int, default=16)
    args = parser.parse_args()
    if args.development_check:
        if args.basis is None:
            raise SystemExit("--basis is required with --development-check")
        result = development_check(args.basis, args.shots, args.half_weight_scale)
        print(canonical(result), end="")
        return
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
