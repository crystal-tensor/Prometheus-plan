#!/usr/bin/env python3
"""Preregistered sparse/preindexed kernel test for the d=6 online decoder."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import scipy
import stim

import b2_b7_p023_d6_correlated_strict_acceptance as strict_base
import b2_b7_p023_d6_decoder_latency_matrix as latency_base
import b2_b7_p023_d6_latency_attribution as attribution_base
import b2_b7_p023_d6_online_window as online_base


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_sparse_kernel_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_sparse_kernel_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_sparse_kernel_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_d6_sparse_kernel_discussion_v1.md"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def edge_key(u: int, v: int | None) -> tuple[int, int]:
    if v is None or int(v) == -1:
        return int(u), -1
    a, b = int(u), int(v)
    return (a, b) if a <= b else (b, a)


@dataclass(frozen=True)
class EdgeIndex:
    component_by_edge: dict[tuple[int, int], int | None]
    edge_count: int
    zero_fault_edges: int
    one_fault_edges: int
    maximum_fault_ids_per_edge: int


def build_edge_indexes(
    compiled: online_base.CompiledWindows,
) -> tuple[list[EdgeIndex], dict[str, int]]:
    indexes: list[EdgeIndex] = []
    totals = {
        "edge_count": 0,
        "zero_fault_edges": 0,
        "one_fault_edges": 0,
        "maximum_fault_ids_per_edge": 0,
    }
    for window in compiled.windows:
        mapping: dict[tuple[int, int], int | None] = {}
        zero = 0
        one = 0
        maximum = 0
        for u, v, data in window.matching.edges():
            key = edge_key(u, v)
            if key in mapping:
                raise ValueError("normalized matching edge is not unique")
            faults = set(data.get("fault_ids", set()))
            maximum = max(maximum, len(faults))
            if len(faults) > 1:
                raise ValueError("preindex contract requires at most one fault ID per edge")
            if faults:
                local_fault = next(iter(faults))
                if local_fault >= len(window.local_fault_to_component):
                    raise ValueError("edge fault ID escapes local component map")
                mapping[key] = window.local_fault_to_component[local_fault]
                one += 1
            else:
                mapping[key] = None
                zero += 1
        indexes.append(EdgeIndex(mapping, len(mapping), zero, one, maximum))
        totals["edge_count"] += len(mapping)
        totals["zero_fault_edges"] += zero
        totals["one_fault_edges"] += one
        totals["maximum_fault_ids_per_edge"] = max(
            totals["maximum_fault_ids_per_edge"], maximum
        )
    return indexes, totals


def decode_sparse_candidate(
    compiled: online_base.CompiledWindows,
    indexes: list[EdgeIndex],
    raw_syndrome: np.ndarray,
    *,
    record_timing: bool,
) -> tuple[np.ndarray, dict[str, Any]]:
    if pymatching.__version__ != "2.4.0":
        raise ValueError("sparse candidate is version-locked to PyMatching 2.4.0")
    model = compiled.model
    raw_syndrome = np.asarray(raw_syndrome, dtype=np.uint8)
    if raw_syndrome.shape != (model.num_detectors,):
        raise ValueError("raw syndrome shape mismatch")
    if len(indexes) != len(compiled.windows):
        raise ValueError("edge index/window count mismatch")
    received = np.zeros(model.num_detectors, dtype=np.uint8)
    correction = np.zeros(model.num_detectors, dtype=np.uint8)
    frame = np.zeros(model.num_observables, dtype=np.uint8)
    received[compiled.prebuffer_detectors] = raw_syndrome[compiled.prebuffer_detectors]
    phases: dict[str, list[int]] = {
        "arrival_delivery": [],
        "syndrome_materialization": [],
        "detection_event_extraction": [],
        "cpp_correlated_matching": [],
        "preindexed_edge_mapping": [],
        "commit_propagation_and_residual": [],
        "direct_feedback_read": [],
    }
    totals: list[int] = []
    selected_components_total = 0
    commit_residual_failures = 0
    feedback_checksum = 0

    for window, index in zip(compiled.windows, indexes, strict=True):
        t0 = time.perf_counter_ns()
        received[window.arrival_detectors] = raw_syndrome[window.arrival_detectors]
        t1 = time.perf_counter_ns()
        syndrome = np.bitwise_xor(
            received[window.detection_detectors],
            correction[window.detection_detectors],
        )
        t2 = time.perf_counter_ns()
        detection_events = np.flatnonzero(syndrome)
        t3 = time.perf_counter_ns()
        native_graph = getattr(window.matching, "_matching_graph")
        selected_edges = native_graph.decode_to_edges_array(
            detection_events,
            enable_correlations=True,
        )
        t4 = time.perf_counter_ns()
        selected_components: set[int] = set()
        for u, v in selected_edges.tolist():
            key = edge_key(int(u), int(v))
            if key not in index.component_by_edge:
                raise ValueError("decoded edge is absent from preindex")
            component_id = index.component_by_edge[key]
            if component_id is not None:
                selected_components.symmetric_difference_update({component_id})
        t5 = time.perf_counter_ns()
        for component_id in selected_components:
            component = model.components[component_id]
            for detector in component.detectors:
                correction[detector] ^= 1
            for observable in component.observables:
                frame[observable] ^= 1
        selected_components_total += len(selected_components)
        commit_residual = np.bitwise_xor(
            received[window.commit_detectors],
            correction[window.commit_detectors],
        )
        if np.any(commit_residual):
            commit_residual_failures += 1
        t6 = time.perf_counter_ns()
        feedback_checksum ^= int(frame[0]) if len(frame) else 0
        t7 = time.perf_counter_ns()
        if record_timing:
            totals.append(t7 - t0)
            phases["arrival_delivery"].append(t1 - t0)
            phases["syndrome_materialization"].append(t2 - t1)
            phases["detection_event_extraction"].append(t3 - t2)
            phases["cpp_correlated_matching"].append(t4 - t3)
            phases["preindexed_edge_mapping"].append(t5 - t4)
            phases["commit_propagation_and_residual"].append(t6 - t5)
            phases["direct_feedback_read"].append(t7 - t6)

    residual = np.bitwise_xor(received, correction)
    additive = all(
        total == sum(phases[name][position] for name in phases)
        for position, total in enumerate(totals)
    )
    return frame, {
        "residual_weight": int(np.count_nonzero(residual)),
        "commit_residual_failures": commit_residual_failures,
        "selected_components": selected_components_total,
        "feedback_checksum": feedback_checksum,
        "raw_total_ns": totals,
        "raw_phases_ns": phases,
        "phase_additivity": additive,
    }


def preflight(protocol: dict[str, Any]) -> dict[str, Any]:
    attribution_protocol = read(
        ROOT / protocol["frozen_inputs"]["attribution_protocol"]["path"]
    )
    online_protocol = read(
        ROOT / attribution_protocol["frozen_inputs"]["online_protocol"]["path"]
    )
    strict_result = read(
        ROOT / online_protocol["frozen_inputs"]["strict_result"]["path"]
    )
    execution = strict_result["execution"]
    contract = online_protocol["window_contract"]
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
        indexes, index_totals = build_edge_indexes(compiled)
        zero = np.zeros(circuit.num_detectors, dtype=np.uint8)
        baseline_frame, baseline = attribution_base.decode_direct(
            compiled, zero, record_timing=False
        )
        candidate_frame, candidate = decode_sparse_candidate(
            compiled, indexes, zero, record_timing=False
        )
        if (
            not np.array_equal(baseline_frame, candidate_frame)
            or baseline["residual_weight"]
            or baseline["commit_residual_failures"]
            or candidate["residual_weight"]
            or candidate["commit_residual_failures"]
        ):
            raise ValueError(f"all-zero sparse-kernel preflight failed for {basis}")
        rows.append(
            {
                "basis": basis,
                "detectors": circuit.num_detectors,
                "windows": len(compiled.windows),
                "baseline_frame": baseline_frame.tolist(),
                "candidate_frame": candidate_frame.tolist(),
                "index_totals": index_totals,
                "structural": compiled.structural,
                "stochastic_samples_observed": 0,
                "nonzero_candidate_predictions_observed": 0,
                "candidate_timing_observations": 0,
            }
        )
    return {
        "schema_version": "b2_b7_p023_d6_sparse_kernel_preflight_v1",
        "scope": protocol["scope"],
        "pymatching_version": pymatching.__version__,
        "rows": rows,
        "stochastic_samples_observed": 0,
        "nonzero_candidate_predictions_observed": 0,
        "candidate_timing_observations": 0,
    }


def run_basis(
    basis: str,
    compiled: online_base.CompiledWindows,
    indexes: list[EdgeIndex],
    index_totals: dict[str, int],
    syndromes: np.ndarray,
    full_predictions_packed: np.ndarray,
    timed_shots: int,
    threshold_us_per_layer: float,
    maximum_miss_fraction: float,
) -> dict[str, Any]:
    full_predictions = np.unpackbits(
        full_predictions_packed,
        axis=1,
        count=compiled.model.num_observables,
        bitorder="little",
    )
    candidate_predictions = np.zeros_like(full_predictions)
    baseline_predictions = np.zeros(
        (timed_shots, full_predictions.shape[1]), dtype=np.uint8
    )
    candidate_totals: list[int] = []
    candidate_phases = {
        name: []
        for name in [
            "arrival_delivery",
            "syndrome_materialization",
            "detection_event_extraction",
            "cpp_correlated_matching",
            "preindexed_edge_mapping",
            "commit_propagation_and_residual",
            "direct_feedback_read",
        ]
    }
    baseline_totals: list[int] = []
    candidate_residual_shots = 0
    candidate_commit_failure_shots = 0
    baseline_residual_shots = 0
    baseline_commit_failure_shots = 0
    candidate_selected_components = 0
    baseline_selected_components = 0

    attribution_base.decode_direct(compiled, syndromes[0], record_timing=False)
    decode_sparse_candidate(compiled, indexes, syndromes[0], record_timing=False)
    for shot_index, syndrome in enumerate(syndromes):
        record = shot_index < timed_shots
        order = (
            ("baseline", "candidate")
            if shot_index % 2 == 0
            else ("candidate", "baseline")
        )
        if not record:
            order = ("candidate",)
        for mode in order:
            if mode == "candidate":
                frame, diagnostics = decode_sparse_candidate(
                    compiled, indexes, syndrome, record_timing=record
                )
                candidate_predictions[shot_index] = frame
                candidate_residual_shots += diagnostics["residual_weight"] != 0
                candidate_commit_failure_shots += (
                    diagnostics["commit_residual_failures"] != 0
                )
                candidate_selected_components += diagnostics["selected_components"]
                if record:
                    if not diagnostics["phase_additivity"]:
                        raise ValueError("candidate phase additivity failed")
                    candidate_totals.extend(diagnostics["raw_total_ns"])
                    for name in candidate_phases:
                        candidate_phases[name].extend(
                            diagnostics["raw_phases_ns"][name]
                        )
            else:
                frame, diagnostics = attribution_base.decode_direct(
                    compiled, syndrome, record_timing=True
                )
                baseline_predictions[shot_index] = frame
                baseline_residual_shots += diagnostics["residual_weight"] != 0
                baseline_commit_failure_shots += (
                    diagnostics["commit_residual_failures"] != 0
                )
                baseline_selected_components += diagnostics["selected_components"]
                baseline_totals.extend(diagnostics["raw_total_ns"])

    commit_layers = [window.commit_layers for window in compiled.windows]
    baseline_summary = attribution_base.vector_summary(
        baseline_totals, commit_layers, timed_shots, threshold_us_per_layer
    )
    candidate_summary = attribution_base.vector_summary(
        candidate_totals, commit_layers, timed_shots, threshold_us_per_layer
    )
    phase_summaries = {
        name: attribution_base.vector_summary(
            values, commit_layers, timed_shots, threshold_us_per_layer
        )
        for name, values in candidate_phases.items()
    }
    candidate_exact = int(
        np.count_nonzero(np.all(candidate_predictions == full_predictions, axis=1))
    )
    baseline_exact = int(
        np.count_nonzero(
            np.all(baseline_predictions == full_predictions[:timed_shots], axis=1)
        )
    )
    cross_path_exact = int(
        np.count_nonzero(
            np.all(
                candidate_predictions[:timed_shots] == baseline_predictions,
                axis=1,
            )
        )
    )
    semantic_pass = bool(
        candidate_exact == len(syndromes)
        and baseline_exact == timed_shots
        and cross_path_exact == timed_shots
        and candidate_residual_shots == 0
        and candidate_commit_failure_shots == 0
        and baseline_residual_shots == 0
        and baseline_commit_failure_shots == 0
    )
    cpp_pass = attribution_base.stage_pass(
        phase_summaries["cpp_correlated_matching"],
        threshold_us_per_layer,
        maximum_miss_fraction,
    )
    mapping_pass = attribution_base.stage_pass(
        phase_summaries["preindexed_edge_mapping"],
        threshold_us_per_layer,
        maximum_miss_fraction,
    )
    candidate_pass = attribution_base.stage_pass(
        candidate_summary,
        threshold_us_per_layer,
        maximum_miss_fraction,
    )
    return {
        "basis": basis,
        "decoder": "two_pass_correlated_matching",
        "shots": len(syndromes),
        "timed_shots": timed_shots,
        "windows_per_shot": len(compiled.windows),
        "index_totals": index_totals,
        "full_block_prediction_sha256": sha_bytes(
            full_predictions_packed.tobytes(order="C")
        ),
        "candidate_prediction_sha256": sha_bytes(
            np.packbits(candidate_predictions, axis=1, bitorder="little").tobytes(
                order="C"
            )
        ),
        "baseline_timed_prediction_sha256": sha_bytes(
            np.packbits(baseline_predictions, axis=1, bitorder="little").tobytes(
                order="C"
            )
        ),
        "candidate_prediction_rows_equal_full_block": candidate_exact,
        "baseline_prediction_rows_equal_full_block": baseline_exact,
        "timed_cross_path_prediction_rows_equal": cross_path_exact,
        "candidate_residual_nonzero_shots": candidate_residual_shots,
        "candidate_commit_residual_failure_shots": candidate_commit_failure_shots,
        "baseline_residual_nonzero_shots": baseline_residual_shots,
        "baseline_commit_residual_failure_shots": baseline_commit_failure_shots,
        "candidate_selected_components_total": candidate_selected_components,
        "baseline_timed_selected_components_total": baseline_selected_components,
        "semantic_veto_pass": semantic_pass,
        "candidate_phase_additivity": True,
        "timing": {
            "baseline_direct_end_to_end": baseline_summary,
            "candidate_direct_end_to_end": candidate_summary,
            "candidate_phases": phase_summaries,
        },
        "stage_pass": {
            "cpp_correlated_matching": cpp_pass,
            "preindexed_edge_mapping": mapping_pass,
            "candidate_direct_end_to_end": candidate_pass,
        },
        "baseline_to_candidate_p99_speedup": (
            baseline_summary["p99_microseconds_per_committed_layer"]
            / candidate_summary["p99_microseconds_per_committed_layer"]
            if semantic_pass
            else None
        ),
    }


def render_report(result: dict[str, Any]) -> str:
    rows = {row["basis"]: row for row in result["basis_rows"]}
    score = result["reference_relative_score"][
        "geometric_mean_baseline_to_candidate_p99_speedup"
    ]
    score_text = f"`{score:.6f}`" if score is not None else "withheld by the semantic veto"
    lines = [
        "# B2/B7/#023 Distance-6 Sparse Kernel v1",
        "",
        f"As of {result['as_of_date']}. Scope is exactly #021/B7, #022/B2, and #023.",
        "",
        "## Heuristic question",
        "",
        "If the decoder already lives in C++, is Python asking it the wrong question?",
        "",
        f"Public freeze: `{result['public_freeze']['commit']}` and Discussion #{result['public_freeze']['discussion_number']}.",
        "",
        "| basis | C++ matching p99 us/layer | preindexed mapping p99 | candidate total p99 | baseline total p99 | candidate semantic rows |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for basis in ["x", "z"]:
        row = rows[basis]
        phases = row["timing"]["candidate_phases"]
        lines.append(
            f"| {basis.upper()} | {phases['cpp_correlated_matching']['p99_microseconds_per_committed_layer']:.6f} | "
            f"{phases['preindexed_edge_mapping']['p99_microseconds_per_committed_layer']:.6f} | "
            f"{row['timing']['candidate_direct_end_to_end']['p99_microseconds_per_committed_layer']:.6f} | "
            f"{row['timing']['baseline_direct_end_to_end']['p99_microseconds_per_committed_layer']:.6f} | "
            f"{row['candidate_prediction_rows_equal_full_block']}/1024 |"
        )
    lines.extend(
        [
            "",
            f"Classification: **{result['classification']}**.",
            "",
            "## Verification before speed",
            "",
            f"The semantic veto is `{result['verdict']['semantic_veto_pass']}`. The X/Z baseline-to-candidate p99 geometric mean is {score_text}; it cannot waive the absolute tail gate.",
            "",
            "## Boundary",
            "",
            "The candidate uses a version-locked private PyMatching C++ entry point. It is diagnostic only. Hardware deadline, full B2, scalable #023 memory, and B7 credit remain false.",
            "",
            f"Formal checks: **{result['summary']['checks_passed']}/{len(result['checks'])}**. Evidence ID: `{result['evidence_id']}`.",
            "",
            "## Next gate",
            "",
            result["next_gate"],
            "",
        ]
    )
    return "\n".join(lines)


def render_discussion(result: dict[str, Any]) -> str:
    rows = {row["basis"]: row for row in result["basis_rows"]}
    x = rows["x"]
    z = rows["z"]
    score = result["reference_relative_score"][
        "geometric_mean_baseline_to_candidate_p99_speedup"
    ]
    score_text = f"`{score:.6f}×`" if score is not None else "withheld"
    return "\n".join(
        [
            "Did a sparse C++ call remove the decoder's missing microsecond?",
            "",
            "The preregistered candidate keeps the correlated graph and every correction decision fixed, but bypasses dense wrapper conversion and replaces repeated edge-data queries with a complete preindex.",
            "",
            f"X C++/mapping/candidate-total/baseline-total p99 is `{x['timing']['candidate_phases']['cpp_correlated_matching']['p99_microseconds_per_committed_layer']:.6f}` / `{x['timing']['candidate_phases']['preindexed_edge_mapping']['p99_microseconds_per_committed_layer']:.6f}` / `{x['timing']['candidate_direct_end_to_end']['p99_microseconds_per_committed_layer']:.6f}` / `{x['timing']['baseline_direct_end_to_end']['p99_microseconds_per_committed_layer']:.6f}` microseconds per committed layer. Z is `{z['timing']['candidate_phases']['cpp_correlated_matching']['p99_microseconds_per_committed_layer']:.6f}` / `{z['timing']['candidate_phases']['preindexed_edge_mapping']['p99_microseconds_per_committed_layer']:.6f}` / `{z['timing']['candidate_direct_end_to_end']['p99_microseconds_per_committed_layer']:.6f}` / `{z['timing']['baseline_direct_end_to_end']['p99_microseconds_per_committed_layer']:.6f}`.",
            "",
            f"The frozen classifier returns **{result['classification']}**. The semantic veto is `{result['verdict']['semantic_veto_pass']}`, so the reference-relative p99 geometric mean is {score_text}; the one-microsecond line remains absolute.",
            "",
            "Questions for critique:",
            "",
            "- Does the result justify a maintained native decoder interface, or a different decoding architecture?",
            "- Which independent implementation should reproduce the sparse-event kernel first?",
            "- Can parallelism reduce tail latency without batching away single-stream causality?",
            "- Where should a private-API diagnostic stop influencing system-level resource claims?",
            "",
            "Hardware deadline, full B2, scalable #023 memory, and B7 credit remain false.",
            "",
        ]
    )


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
    if pymatching.__version__ != protocol["candidate_contract"][
        "required_pymatching_version"
    ]:
        raise ValueError("PyMatching version does not match the frozen private API")
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
    runner_path = str(Path(__file__).resolve().relative_to(ROOT))
    protocol_rel = str(protocol_path.resolve().relative_to(ROOT))
    freeze_protocol_sha = sha_bytes(git_blob(public_freeze_commit, protocol_rel))
    freeze_runner_sha = sha_bytes(git_blob(public_freeze_commit, runner_path))
    if freeze_protocol_sha != sha_path(protocol_path):
        raise ValueError("protocol differs from public freeze")
    if freeze_runner_sha != sha_path(Path(__file__).resolve()):
        raise ValueError("runner differs from public freeze")

    attribution_protocol = read(
        ROOT / protocol["frozen_inputs"]["attribution_protocol"]["path"]
    )
    attribution_result = read(
        ROOT / protocol["frozen_inputs"]["attribution_result"]["path"]
    )
    if attribution_result["classification"] != protocol["frozen_inputs"][
        "attribution_result"
    ]["required_classification"]:
        raise ValueError("attribution source classification mismatch")
    online_protocol = read(
        ROOT / attribution_protocol["frozen_inputs"]["online_protocol"]["path"]
    )
    strict_result = read(
        ROOT / online_protocol["frozen_inputs"]["strict_result"]["path"]
    )
    latency_result = read(
        ROOT / online_protocol["frozen_inputs"]["latency_result"]["path"]
    )
    execution = strict_result["execution"]
    strict_rows = {row["memory_basis"]: row for row in strict_result["candidate_rows"]}
    latency_corpora = {row["basis"]: row for row in latency_result["corpora"]}
    window_contract = online_protocol["window_contract"]
    timed_shots = protocol["corpus_contract"]["timed_shots_per_basis_and_path"]
    threshold = protocol["timing_contract"][
        "threshold_microseconds_per_committed_layer"
    ]
    maximum_miss = protocol["timing_contract"]["maximum_deadline_miss_fraction"]
    basis_rows: list[dict[str, Any]] = []
    corpora: list[dict[str, Any]] = []
    structures: list[dict[str, Any]] = []
    for basis in execution["memory_bases"]:
        circuit = strict_base.build_circuit(basis, execution)
        corpus, detectors_packed, _observables, _independent, correlated = (
            latency_base.build_corpus(
                basis,
                execution,
                strict_rows[basis],
                online_protocol["corpus_contract"],
            )
        )
        if corpus["corpus_sha256"] != latency_corpora[basis]["corpus_sha256"]:
            raise ValueError("corpus hash mismatch")
        syndromes = np.unpackbits(
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
        indexes, index_totals = build_edge_indexes(compiled)
        full_predictions = latency_base.decode_corpus(
            correlated, detectors_packed, 256, True
        )
        basis_rows.append(
            run_basis(
                basis,
                compiled,
                indexes,
                index_totals,
                syndromes,
                full_predictions,
                timed_shots,
                threshold,
                maximum_miss,
            )
        )
        corpora.append(corpus)
        structures.append(
            {"basis": basis, **compiled.structural, "index_totals": index_totals}
        )

    semantic_pass = all(row["semantic_veto_pass"] for row in basis_rows)
    cpp_pass = all(
        row["stage_pass"]["cpp_correlated_matching"] for row in basis_rows
    )
    mapping_pass = all(
        row["stage_pass"]["preindexed_edge_mapping"] for row in basis_rows
    )
    candidate_pass = all(
        row["stage_pass"]["candidate_direct_end_to_end"] for row in basis_rows
    )
    if not semantic_pass:
        classification = "semantic_regression"
    elif not cpp_pass:
        classification = "cpp_correlated_matching_tail_bottleneck"
    elif not mapping_pass:
        classification = "preindexed_edge_mapping_tail_bottleneck"
    elif not candidate_pass:
        classification = "candidate_direct_tail_bottleneck"
    else:
        classification = "candidate_host_proxy_pass"
    speedups = [row["baseline_to_candidate_p99_speedup"] for row in basis_rows]
    geometric_speedup = math.sqrt(speedups[0] * speedups[1]) if semantic_pass else None
    next_gates = {
        "semantic_regression": "Stop timing work and repair the sparse/preindexed semantic mismatch under the frozen corpus.",
        "cpp_correlated_matching_tail_bottleneck": "Move beyond wrapper tuning: preregister a maintained native or alternate decoder kernel with identical window semantics.",
        "preindexed_edge_mapping_tail_bottleneck": "Fuse edge extraction and component mapping in a maintained native interface while retaining raw tail evidence.",
        "candidate_direct_tail_bottleneck": "Optimize the next measured direct-path phase without changing matching decisions or the deadline.",
        "candidate_host_proxy_pass": "Replace the private diagnostic with a supported native implementation, then test an asynchronous device/control path.",
    }
    result: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_sparse_kernel_result_v1",
        "as_of_date": protocol["as_of_date"],
        "question": protocol["question"],
        "scope": protocol["scope"],
        "public_freeze": {
            "commit": public_freeze_commit,
            "discussion_number": discussion_number,
            "discussion_url": (
                "https://github.com/crystal-tensor/Prometheus-plan/discussions/"
                f"{discussion_number}"
            ),
            "protocol_sha256": freeze_protocol_sha,
            "runner_sha256": freeze_runner_sha,
        },
        "protocol_binding": {"path": protocol_rel, "sha256": sha_path(protocol_path)},
        "generator": {"path": runner_path, "sha256": sha_path(Path(__file__).resolve())},
        "frozen_inputs": {"artifact_commit": artifact_commit, "bindings": bindings},
        "execution_environment": {
            "python": platform.python_version(),
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "known_before_preregistration": protocol["known_before_preregistration"],
        "candidate_contract": protocol["candidate_contract"],
        "corpus_contract": protocol["corpus_contract"],
        "timing_contract": protocol["timing_contract"],
        "classification_rule": protocol["classification_rule"],
        "kaggle_inspired_evaluation": protocol["kaggle_inspired_evaluation"],
        "hard_boundaries": protocol["hard_boundaries"],
        "corpora": corpora,
        "structures": structures,
        "basis_rows": basis_rows,
        "classification": classification,
        "reference_relative_score": {
            "x_baseline_to_candidate_p99_speedup": speedups[0] if semantic_pass else None,
            "z_baseline_to_candidate_p99_speedup": speedups[1] if semantic_pass else None,
            "geometric_mean_baseline_to_candidate_p99_speedup": geometric_speedup,
            "absolute_deadline_waived": False,
        },
        "verdict": {
            "semantic_veto_pass": semantic_pass,
            "cpp_correlated_matching_tail_pass": cpp_pass,
            "preindexed_edge_mapping_tail_pass": mapping_pass,
            "candidate_direct_tail_pass": candidate_pass,
            "hardware_decoder_deadline_passed": False,
            "full_b2_credit_ready": False,
            "p023_scalable_memory_ready": False,
            "b7_resource_credit": 0,
        },
        "next_gate": next_gates[classification],
    }
    checks = [
        check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact QEC scope."),
        check("public_freeze", freeze_protocol_sha == sha_path(protocol_path) and freeze_runner_sha == sha_path(Path(__file__).resolve()), public_freeze_commit),
        check("frozen_inputs", len(bindings) == 5 and all(row["matches_artifact_commit"] for row in bindings.values()), artifact_commit),
        check("source_classification", attribution_result["classification"] == "matching_kernel_tail_bottleneck", attribution_result["classification"]),
        check("pymatching_version", pymatching.__version__ == "2.4.0", pymatching.__version__),
        check("corpora", len(corpora) == 2 and all(row["shots"] == 1024 for row in corpora), "Two frozen 1,024-shot corpora."),
        check("structure", len(structures) == 2 and all(row["num_windows"] == 164 and row["index_totals"]["maximum_fault_ids_per_edge"] <= 1 for row in structures), "164 windows and complete zero/one-fault preindexes."),
        check("semantic_adjudication", (semantic_pass and classification != "semantic_regression") or ((not semantic_pass) and classification == "semantic_regression"), f"semantic_veto_pass={semantic_pass}; classification={classification}"),
        check("timing_counts", all(row["timing"]["baseline_direct_end_to_end"]["observations"] == timed_shots * 164 and row["timing"]["candidate_direct_end_to_end"]["observations"] == timed_shots * 164 for row in basis_rows), "Complete interleaved timing vectors."),
        check("phase_additivity", all(row["candidate_phase_additivity"] for row in basis_rows), "Every candidate phase sum equals total."),
        check("raw_vectors", all(len(row["timing"]["candidate_direct_end_to_end"]["raw_nanoseconds_sha256"]) == 64 and len(row["timing"]["baseline_direct_end_to_end"]["raw_nanoseconds_sha256"]) == 64 for row in basis_rows), "Raw timing vectors bound."),
        check("classification", classification in protocol["classification_rule"]["order"], classification),
        check("score_guard", (geometric_speedup is not None) == semantic_pass and result["reference_relative_score"]["absolute_deadline_waived"] is False, "Score follows semantic veto and cannot waive deadline."),
        check("hard_boundaries", result["verdict"]["hardware_decoder_deadline_passed"] is False and result["verdict"]["full_b2_credit_ready"] is False and result["verdict"]["p023_scalable_memory_ready"] is False and result["verdict"]["b7_resource_credit"] == 0, "No downstream credit."),
    ]
    result["checks"] = checks
    result["summary"] = {
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "classification": classification,
        "semantic_veto_pass": semantic_pass,
        "cpp_correlated_matching_tail_pass": cpp_pass,
        "preindexed_edge_mapping_tail_pass": mapping_pass,
        "candidate_direct_tail_pass": candidate_pass,
        "hardware_decoder_deadline_passed": False,
        "full_b2_credit_ready": False,
        "p023_scalable_memory_ready": False,
        "b7_resource_credit": 0,
    }
    if result["summary"]["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"formal checks failed: {failed}")
    result["evidence_id"] = sha_bytes(
        compact(
            {
                "public_freeze": result["public_freeze"],
                "classification": classification,
                "reference_relative_score": result["reference_relative_score"],
                "verdict": result["verdict"],
                "timing_hashes": [
                    {
                        "basis": row["basis"],
                        "baseline": row["timing"]["baseline_direct_end_to_end"]["raw_nanoseconds_sha256"],
                        "candidate": row["timing"]["candidate_direct_end_to_end"]["raw_nanoseconds_sha256"],
                        "cpp": row["timing"]["candidate_phases"]["cpp_correlated_matching"]["raw_nanoseconds_sha256"],
                        "mapping": row["timing"]["candidate_phases"]["preindexed_edge_mapping"]["raw_nanoseconds_sha256"],
                    }
                    for row in basis_rows
                ],
            }
        )
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument("--public-freeze-commit")
    parser.add_argument("--discussion-number", type=int)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    protocol = read(args.protocol)
    if args.preflight_only:
        print(canonical(preflight(protocol)), end="")
        return
    if not args.public_freeze_commit or not args.discussion_number:
        raise ValueError("public freeze commit and discussion number are required")
    result = build_result(
        protocol,
        args.protocol,
        args.public_freeze_commit,
        args.discussion_number,
    )
    args.result.write_text(canonical(result), encoding="utf-8")
    args.report.write_text(render_report(result), encoding="utf-8")
    args.discussion.write_text(render_discussion(result), encoding="utf-8")
    print(canonical(result["summary"]), end="")


if __name__ == "__main__":
    main()
