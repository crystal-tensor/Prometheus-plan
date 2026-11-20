#!/usr/bin/env python3
"""Preregistered fine-grained latency attribution for the d=6 online decoder."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import platform
import statistics
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import scipy
import stim

import b2_b7_p023_d6_correlated_strict_acceptance as strict_base
import b2_b7_p023_d6_decoder_latency_matrix as latency_base
import b2_b7_p023_d6_online_window as online_base


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_latency_attribution_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_latency_attribution_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_latency_attribution_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_d6_latency_attribution_discussion_v1.md"


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


def nearest_rank(values: list[float] | list[int], probability: float) -> float:
    if not values:
        raise ValueError("cannot summarize an empty vector")
    ordered = sorted(values)
    return float(ordered[max(0, math.ceil(probability * len(ordered)) - 1)])


def encode_u64(values: list[int]) -> tuple[str, str]:
    raw = np.asarray(values, dtype="<u8").tobytes(order="C")
    return base64.b64encode(raw).decode("ascii"), sha_bytes(raw)


def vector_summary(
    values: list[int],
    commit_layers: list[int],
    shots: int,
    threshold_us_per_layer: float,
) -> dict[str, Any]:
    expected = shots * len(commit_layers)
    if len(values) != expected:
        raise ValueError(f"timing count {len(values)} != {expected}")
    layers = commit_layers * shots
    per_layer = [
        value / layer_count / 1000.0
        for value, layer_count in zip(values, layers, strict=True)
    ]
    deadlines = [layer_count * threshold_us_per_layer * 1000.0 for layer_count in layers]
    misses = sum(
        value > deadline for value, deadline in zip(values, deadlines, strict=True)
    )
    encoded, raw_sha = encode_u64(values)
    return {
        "observations": len(values),
        "sum_nanoseconds": sum(values),
        "mean_nanoseconds": statistics.fmean(values),
        "p50_microseconds_per_committed_layer": nearest_rank(per_layer, 0.50),
        "p95_microseconds_per_committed_layer": nearest_rank(per_layer, 0.95),
        "p99_microseconds_per_committed_layer": nearest_rank(per_layer, 0.99),
        "p999_microseconds_per_committed_layer": nearest_rank(per_layer, 0.999),
        "max_microseconds_per_committed_layer": max(per_layer),
        "deadline_misses": misses,
        "deadline_miss_fraction": misses / len(values),
        "raw_nanoseconds_encoding": "base64_little_endian_uint64",
        "raw_nanoseconds_b64": encoded,
        "raw_nanoseconds_sha256": raw_sha,
    }


def stage_pass(
    summary: dict[str, Any],
    threshold_us_per_layer: float,
    maximum_miss_fraction: float,
) -> bool:
    return bool(
        summary["p99_microseconds_per_committed_layer"] <= threshold_us_per_layer
        and summary["deadline_miss_fraction"] <= maximum_miss_fraction
    )


def decode_direct(
    compiled: online_base.CompiledWindows,
    raw_syndrome: np.ndarray,
    *,
    record_timing: bool,
) -> tuple[np.ndarray, dict[str, Any]]:
    model = compiled.model
    raw_syndrome = np.asarray(raw_syndrome, dtype=np.uint8)
    if raw_syndrome.shape != (model.num_detectors,):
        raise ValueError("raw syndrome shape mismatch")
    received = np.zeros(model.num_detectors, dtype=np.uint8)
    correction = np.zeros(model.num_detectors, dtype=np.uint8)
    frame = np.zeros(model.num_observables, dtype=np.uint8)
    received[compiled.prebuffer_detectors] = raw_syndrome[compiled.prebuffer_detectors]
    phases: dict[str, list[int]] = {
        "arrival_delivery": [],
        "syndrome_materialization": [],
        "matching_kernel": [],
        "edge_to_component_mapping": [],
        "commit_propagation_and_residual": [],
        "direct_feedback_read": [],
    }
    totals: list[int] = []
    selected_components_total = 0
    commit_residual_failures = 0
    feedback_checksum = 0

    for window in compiled.windows:
        t0 = time.perf_counter_ns()
        received[window.arrival_detectors] = raw_syndrome[window.arrival_detectors]
        t1 = time.perf_counter_ns()
        syndrome = np.bitwise_xor(
            received[window.detection_detectors],
            correction[window.detection_detectors],
        )
        t2 = time.perf_counter_ns()
        selected_edges = window.matching.decode_to_edges_array(
            syndrome,
            enable_correlations=True,
        )
        t3 = time.perf_counter_ns()
        selected_components: set[int] = set()
        for u, v in selected_edges.tolist():
            for local_fault in online_base.edge_fault_ids(
                window.matching, int(u), int(v)
            ):
                component_id = window.local_fault_to_component[local_fault]
                if component_id not in window.commit_component_ids:
                    raise ValueError("matching emitted a non-commit fault label")
                if component_id in selected_components:
                    selected_components.remove(component_id)
                else:
                    selected_components.add(component_id)
        t4 = time.perf_counter_ns()
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
        t5 = time.perf_counter_ns()
        feedback_checksum ^= int(frame[0]) if len(frame) else 0
        t6 = time.perf_counter_ns()
        if record_timing:
            totals.append(t6 - t0)
            phases["arrival_delivery"].append(t1 - t0)
            phases["syndrome_materialization"].append(t2 - t1)
            phases["matching_kernel"].append(t3 - t2)
            phases["edge_to_component_mapping"].append(t4 - t3)
            phases["commit_propagation_and_residual"].append(t5 - t4)
            phases["direct_feedback_read"].append(t6 - t5)

    residual = np.bitwise_xor(received, correction)
    phase_additivity = all(
        total == sum(phases[name][index] for name in phases)
        for index, total in enumerate(totals)
    )
    return frame, {
        "residual_weight": int(np.count_nonzero(residual)),
        "commit_residual_failures": commit_residual_failures,
        "selected_components": selected_components_total,
        "feedback_checksum": feedback_checksum,
        "raw_total_ns": totals,
        "raw_phases_ns": phases,
        "phase_additivity": phase_additivity,
    }


def preflight(protocol: dict[str, Any]) -> dict[str, Any]:
    online_protocol = read(ROOT / protocol["frozen_inputs"]["online_protocol"]["path"])
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
        zero = np.zeros(circuit.num_detectors, dtype=np.uint8)
        direct_frame, direct = decode_direct(compiled, zero, record_timing=False)
        sync_frame, sync = online_base.decode_stream(
            compiled,
            zero,
            enable_correlations=True,
            basis_code=0 if basis == "x" else 1,
            decoder_code=1,
            shot_index=0,
            record_timing=False,
        )
        if (
            not np.array_equal(direct_frame, sync_frame)
            or direct["residual_weight"]
            or direct["commit_residual_failures"]
            or sync["residual_weight"]
            or sync["commit_residual_failures"]
        ):
            raise ValueError(f"all-zero attribution preflight failed for {basis}")
        rows.append(
            {
                "basis": basis,
                "detectors": circuit.num_detectors,
                "windows": len(compiled.windows),
                "direct_frame": direct_frame.tolist(),
                "sync_frame": sync_frame.tolist(),
                "structural": compiled.structural,
                "stochastic_samples_observed": 0,
                "timing_observations": 0,
            }
        )
    return {
        "schema_version": "b2_b7_p023_d6_latency_attribution_preflight_v1",
        "scope": protocol["scope"],
        "rows": rows,
        "stochastic_samples_observed": 0,
        "direct_path_timing_observations": 0,
        "fine_phase_timing_observations": 0,
    }


def run_basis(
    basis: str,
    compiled: online_base.CompiledWindows,
    syndromes: np.ndarray,
    full_predictions_packed: np.ndarray,
    timed_shots: int,
    threshold_us_per_layer: float,
    maximum_miss_fraction: float,
) -> dict[str, Any]:
    if timed_shots > len(syndromes):
        raise ValueError("timed shots exceed corpus")
    full_predictions = np.unpackbits(
        full_predictions_packed,
        axis=1,
        count=compiled.model.num_observables,
        bitorder="little",
    )
    direct_predictions = np.zeros_like(full_predictions)
    sync_predictions = np.zeros((timed_shots, full_predictions.shape[1]), dtype=np.uint8)
    direct_totals: list[int] = []
    direct_phases = {
        name: []
        for name in [
            "arrival_delivery",
            "syndrome_materialization",
            "matching_kernel",
            "edge_to_component_mapping",
            "commit_propagation_and_residual",
            "direct_feedback_read",
        ]
    }
    sync_totals: list[int] = []
    sync_phases = {
        "input_transport": [],
        "decoder_and_commit": [],
        "feedback": [],
    }
    direct_residual_shots = 0
    direct_commit_failure_shots = 0
    sync_residual_shots = 0
    sync_commit_failure_shots = 0
    direct_selected_components = 0
    sync_selected_components = 0

    decode_direct(compiled, syndromes[0], record_timing=False)
    online_base.decode_stream(
        compiled,
        syndromes[0],
        enable_correlations=True,
        basis_code=0 if basis == "x" else 1,
        decoder_code=1,
        shot_index=0,
        record_timing=False,
    )

    for shot_index, syndrome in enumerate(syndromes):
        record = shot_index < timed_shots
        order = (
            ("sync", "direct")
            if shot_index % 2 == 0
            else ("direct", "sync")
        )
        if not record:
            order = ("direct",)
        for mode in order:
            if mode == "direct":
                frame, diagnostics = decode_direct(
                    compiled,
                    syndrome,
                    record_timing=record,
                )
                direct_predictions[shot_index] = frame
                direct_residual_shots += diagnostics["residual_weight"] != 0
                direct_commit_failure_shots += (
                    diagnostics["commit_residual_failures"] != 0
                )
                direct_selected_components += diagnostics["selected_components"]
                if record:
                    if not diagnostics["phase_additivity"]:
                        raise ValueError("direct phase additivity failed")
                    direct_totals.extend(diagnostics["raw_total_ns"])
                    for name in direct_phases:
                        direct_phases[name].extend(
                            diagnostics["raw_phases_ns"][name]
                        )
            else:
                frame, diagnostics = online_base.decode_stream(
                    compiled,
                    syndrome,
                    enable_correlations=True,
                    basis_code=0 if basis == "x" else 1,
                    decoder_code=1,
                    shot_index=shot_index,
                    record_timing=True,
                )
                sync_predictions[shot_index] = frame
                sync_residual_shots += diagnostics["residual_weight"] != 0
                sync_commit_failure_shots += (
                    diagnostics["commit_residual_failures"] != 0
                )
                sync_selected_components += diagnostics["selected_components"]
                sync_totals.extend(diagnostics["raw_total_ns"])
                sync_phases["input_transport"].extend(diagnostics["raw_input_ns"])
                sync_phases["decoder_and_commit"].extend(
                    diagnostics["raw_decode_ns"]
                )
                sync_phases["feedback"].extend(diagnostics["raw_feedback_ns"])

    commit_layers = [window.commit_layers for window in compiled.windows]
    direct_summary = vector_summary(
        direct_totals, commit_layers, timed_shots, threshold_us_per_layer
    )
    direct_phase_summaries = {
        name: vector_summary(
            values, commit_layers, timed_shots, threshold_us_per_layer
        )
        for name, values in direct_phases.items()
    }
    sync_summary = vector_summary(
        sync_totals, commit_layers, timed_shots, threshold_us_per_layer
    )
    sync_phase_summaries = {
        name: vector_summary(
            values, commit_layers, timed_shots, threshold_us_per_layer
        )
        for name, values in sync_phases.items()
    }
    sync_additivity = all(
        total == sum(sync_phases[name][index] for name in sync_phases)
        for index, total in enumerate(sync_totals)
    )
    direct_exact_rows = int(
        np.count_nonzero(np.all(direct_predictions == full_predictions, axis=1))
    )
    sync_exact_rows = int(
        np.count_nonzero(
            np.all(sync_predictions == full_predictions[:timed_shots], axis=1)
        )
    )
    timed_cross_path_rows = int(
        np.count_nonzero(
            np.all(
                direct_predictions[:timed_shots] == sync_predictions,
                axis=1,
            )
        )
    )
    semantic_pass = bool(
        direct_exact_rows == len(syndromes)
        and sync_exact_rows == timed_shots
        and timed_cross_path_rows == timed_shots
        and direct_residual_shots == 0
        and direct_commit_failure_shots == 0
        and sync_residual_shots == 0
        and sync_commit_failure_shots == 0
    )
    matching_pass = stage_pass(
        direct_phase_summaries["matching_kernel"],
        threshold_us_per_layer,
        maximum_miss_fraction,
    )
    direct_pass = stage_pass(
        direct_summary, threshold_us_per_layer, maximum_miss_fraction
    )
    sync_pass = stage_pass(
        sync_summary, threshold_us_per_layer, maximum_miss_fraction
    )
    return {
        "basis": basis,
        "decoder": "two_pass_correlated_matching",
        "shots": len(syndromes),
        "timed_shots": timed_shots,
        "windows_per_shot": len(compiled.windows),
        "timed_mode_order": "sync_then_direct_even_direct_then_sync_odd",
        "full_block_prediction_sha256": sha_bytes(
            full_predictions_packed.tobytes(order="C")
        ),
        "direct_prediction_sha256": sha_bytes(
            np.packbits(direct_predictions, axis=1, bitorder="little").tobytes(
                order="C"
            )
        ),
        "sync_timed_prediction_sha256": sha_bytes(
            np.packbits(sync_predictions, axis=1, bitorder="little").tobytes(
                order="C"
            )
        ),
        "direct_prediction_rows_equal_full_block": direct_exact_rows,
        "sync_prediction_rows_equal_full_block": sync_exact_rows,
        "timed_cross_path_prediction_rows_equal": timed_cross_path_rows,
        "direct_residual_nonzero_shots": direct_residual_shots,
        "direct_commit_residual_failure_shots": direct_commit_failure_shots,
        "sync_residual_nonzero_shots": sync_residual_shots,
        "sync_commit_residual_failure_shots": sync_commit_failure_shots,
        "direct_selected_components_total": direct_selected_components,
        "sync_timed_selected_components_total": sync_selected_components,
        "semantic_veto_pass": semantic_pass,
        "phase_additivity": {
            "direct": True,
            "sync": sync_additivity,
        },
        "timing": {
            "sync_end_to_end": sync_summary,
            "sync_phases": sync_phase_summaries,
            "direct_end_to_end": direct_summary,
            "direct_phases": direct_phase_summaries,
        },
        "stage_pass": {
            "matching_kernel": matching_pass,
            "direct_end_to_end": direct_pass,
            "sync_end_to_end": sync_pass,
        },
        "sync_to_direct_p99_speedup": (
            sync_summary["p99_microseconds_per_committed_layer"]
            / direct_summary["p99_microseconds_per_committed_layer"]
            if semantic_pass
            else None
        ),
        "matching_share_of_direct_total_by_sum": (
            direct_phase_summaries["matching_kernel"]["sum_nanoseconds"]
            / direct_summary["sum_nanoseconds"]
        ),
    }


def render_report(result: dict[str, Any]) -> str:
    rows = {row["basis"]: row for row in result["basis_rows"]}
    geometric_speedup = result["reference_relative_score"][
        "geometric_mean_sync_to_direct_p99_speedup"
    ]
    speedup_text = (
        f"`{geometric_speedup:.6f}`"
        if geometric_speedup is not None
        else "not reported because the semantic veto failed"
    )
    lines = [
        "# B2/B7/#023 Distance-6 Latency Attribution v1",
        "",
        f"As of {result['as_of_date']}. Scope is exactly #021/B7, #022/B2, and #023.",
        "",
        "## Heuristic question",
        "",
        "If transport vanished, would the decoder finally catch the clock?",
        "",
        f"Public freeze: `{result['public_freeze']['commit']}` and Discussion #{result['public_freeze']['discussion_number']}.",
        "",
        "| basis | matching p99 us/layer | direct p99 | sync p99 | direct semantic rows | first-stage passes (match/direct/sync) |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for basis in ["x", "z"]:
        row = rows[basis]
        phases = row["timing"]["direct_phases"]
        stages = row["stage_pass"]
        lines.append(
            f"| {basis.upper()} | {phases['matching_kernel']['p99_microseconds_per_committed_layer']:.6f} | "
            f"{row['timing']['direct_end_to_end']['p99_microseconds_per_committed_layer']:.6f} | "
            f"{row['timing']['sync_end_to_end']['p99_microseconds_per_committed_layer']:.6f} | "
            f"{row['direct_prediction_rows_equal_full_block']}/1024 | "
            f"{stages['matching_kernel']}/{stages['direct_end_to_end']}/{stages['sync_end_to_end']} |"
        )
    lines.extend(
        [
            "",
            f"Classification: **{result['classification']}**.",
            "",
            "## Kaggle-inspired score boundary",
            "",
            f"The semantic veto is `{result['verdict']['semantic_veto_pass']}`. Only after that pass is the X/Z sync-to-direct p99 geometric mean reported: {speedup_text}. The relative number cannot override the absolute one-microsecond p99 and one-percent miss gates.",
            "",
            "## Boundary",
            "",
            "Both paths remain same-host Python measurements. Hardware deadline, full B2, scalable #023 memory, and B7 resource credit remain false.",
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
    geometric_speedup = result["reference_relative_score"][
        "geometric_mean_sync_to_direct_p99_speedup"
    ]
    speedup_text = (
        f"`{geometric_speedup:.6f}×`"
        if geometric_speedup is not None
        else "withheld because the semantic veto failed"
    )
    return "\n".join(
        [
            "Where did the missing microsecond actually go?",
            "",
            "The preregistered distance-6 attribution run keeps the same corpus, windows, correlated matching objects, correction propagation, and absolute deadline, then compares the synchronous packed socket path with a direct no-pack/no-socket path.",
            "",
            f"X matching/direct/sync p99 is `{x['timing']['direct_phases']['matching_kernel']['p99_microseconds_per_committed_layer']:.6f}` / `{x['timing']['direct_end_to_end']['p99_microseconds_per_committed_layer']:.6f}` / `{x['timing']['sync_end_to_end']['p99_microseconds_per_committed_layer']:.6f}` microseconds per committed layer. Z is `{z['timing']['direct_phases']['matching_kernel']['p99_microseconds_per_committed_layer']:.6f}` / `{z['timing']['direct_end_to_end']['p99_microseconds_per_committed_layer']:.6f}` / `{z['timing']['sync_end_to_end']['p99_microseconds_per_committed_layer']:.6f}`.",
            "",
            f"The frozen classifier returns **{result['classification']}**. The semantic veto is `{result['verdict']['semantic_veto_pass']}`, so the sync-to-direct p99 geometric-mean speedup is {speedup_text}; any relative gain does not waive the one-microsecond absolute line.",
            "",
            "Questions for critique:",
            "",
            "- Is the first failing stage the right place to invest, or should optimization follow total time share instead?",
            "- Would native batching or parallel windows preserve the online deadline semantics, or merely recreate an offline throughput proxy?",
            "- Which independent hardware/controller trace would make this attribution actionable?",
            "- Should matching, bookkeeping, and transport remain a Pareto vector rather than one combined latency score?",
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
    artifact_commit = protocol["frozen_inputs"]["artifact_commit"]
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", artifact_commit, public_freeze_commit],
        cwd=ROOT,
        check=True,
    )
    frozen_bindings: dict[str, Any] = {}
    for name, binding in protocol["frozen_inputs"].items():
        if name == "artifact_commit":
            continue
        path = ROOT / binding["path"]
        current_sha = sha_path(path)
        committed_sha = sha_bytes(git_blob(artifact_commit, binding["path"]))
        if current_sha != binding["sha256"] or committed_sha != binding["sha256"]:
            raise ValueError(f"frozen input mismatch: {name}")
        frozen_bindings[name] = {
            "path": binding["path"],
            "sha256": current_sha,
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

    online_protocol = read(ROOT / protocol["frozen_inputs"]["online_protocol"]["path"])
    online_result = read(ROOT / protocol["frozen_inputs"]["online_result"]["path"])
    if online_result["decision"] != protocol["frozen_inputs"]["online_result"][
        "required_decision"
    ]:
        raise ValueError("online source decision mismatch")
    strict_result = read(
        ROOT / online_protocol["frozen_inputs"]["strict_result"]["path"]
    )
    latency_result = read(
        ROOT / online_protocol["frozen_inputs"]["latency_result"]["path"]
    )
    execution = strict_result["execution"]
    strict_rows = {row["memory_basis"]: row for row in strict_result["candidate_rows"]}
    latency_corpora = {row["basis"]: row for row in latency_result["corpora"]}
    contract = online_protocol["window_contract"]
    timed_shots = protocol["corpus_contract"]["timed_shots_per_basis"]
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
            contract["window_size_layers"],
            contract["stride_layers"],
            contract["time_coordinate_index"],
        )
        full_predictions = latency_base.decode_corpus(
            correlated,
            detectors_packed,
            256,
            True,
        )
        basis_rows.append(
            run_basis(
                basis,
                compiled,
                syndromes,
                full_predictions,
                timed_shots,
                threshold,
                maximum_miss,
            )
        )
        corpora.append(corpus)
        structures.append({"basis": basis, **compiled.structural})

    semantic_pass = all(row["semantic_veto_pass"] for row in basis_rows)
    matching_pass = all(row["stage_pass"]["matching_kernel"] for row in basis_rows)
    direct_pass = all(row["stage_pass"]["direct_end_to_end"] for row in basis_rows)
    sync_pass = all(row["stage_pass"]["sync_end_to_end"] for row in basis_rows)
    if not semantic_pass:
        classification = "semantic_regression"
    elif not matching_pass:
        classification = "matching_kernel_tail_bottleneck"
    elif not direct_pass:
        classification = "python_window_bookkeeping_tail_bottleneck"
    elif not sync_pass:
        classification = "synchronous_transport_feedback_tail_bottleneck"
    else:
        classification = "sync_host_proxy_pass"
    speedups = [row["sync_to_direct_p99_speedup"] for row in basis_rows]
    geometric_speedup = math.sqrt(speedups[0] * speedups[1]) if semantic_pass else None
    next_gate_by_classification = {
        "semantic_regression": "Stop latency optimization and repair the direct/sync semantic mismatch under the same frozen corpus.",
        "matching_kernel_tail_bottleneck": "Preregister a native or parallel matching-kernel candidate while retaining exact window semantics and the absolute tail gate.",
        "python_window_bookkeeping_tail_bottleneck": "Preregister preallocated native edge mapping and correction propagation without changing the matching decisions.",
        "synchronous_transport_feedback_tail_bottleneck": "Preregister an asynchronous or controller-like transport path with the same decoder and response contract.",
        "sync_host_proxy_pass": "Move to a real asynchronous device/control path and model-mismatch stress; do not promote the host result to hardware credit.",
    }
    result: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_latency_attribution_result_v1",
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
        "frozen_inputs": {
            "artifact_commit": artifact_commit,
            "bindings": frozen_bindings,
        },
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
        "corpus_contract": protocol["corpus_contract"],
        "attribution_contract": protocol["attribution_contract"],
        "timing_contract": protocol["timing_contract"],
        "classification_rule": protocol["classification_rule"],
        "kaggle_inspired_evaluation": protocol["kaggle_inspired_evaluation"],
        "hard_boundaries": protocol["hard_boundaries"],
        "corpora": corpora,
        "structures": structures,
        "basis_rows": basis_rows,
        "classification": classification,
        "reference_relative_score": {
            "x_sync_to_direct_p99_speedup": speedups[0] if semantic_pass else None,
            "z_sync_to_direct_p99_speedup": speedups[1] if semantic_pass else None,
            "geometric_mean_sync_to_direct_p99_speedup": geometric_speedup,
            "absolute_deadline_waived": False,
        },
        "verdict": {
            "semantic_veto_pass": semantic_pass,
            "matching_kernel_tail_pass": matching_pass,
            "direct_path_tail_pass": direct_pass,
            "sync_path_tail_pass": sync_pass,
            "hardware_decoder_deadline_passed": False,
            "full_b2_credit_ready": False,
            "p023_scalable_memory_ready": False,
            "b7_resource_credit": 0,
        },
        "next_gate": next_gate_by_classification[classification],
    }
    checks = [
        check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact QEC scope."),
        check("public_freeze", freeze_protocol_sha == sha_path(protocol_path) and freeze_runner_sha == sha_path(Path(__file__).resolve()), public_freeze_commit),
        check("frozen_inputs", len(frozen_bindings) == 4 and all(row["matches_artifact_commit"] for row in frozen_bindings.values()), artifact_commit),
        check("source_negative", online_result["verdict"]["online_correlated_host_proxy_pass"] is False, online_result["decision"]),
        check("corpora", len(corpora) == 2 and all(row["shots"] == 1024 for row in corpora), "Two frozen 1,024-shot corpora."),
        check("structure", len(structures) == 2 and all(row["num_windows"] == 164 for row in structures), "164 windows per basis."),
        check("semantic_adjudication", (semantic_pass and classification != "semantic_regression") or ((not semantic_pass) and classification == "semantic_regression"), f"semantic_veto_pass={semantic_pass}; classification={classification}"),
        check("timing_counts", all(row["timing"]["sync_end_to_end"]["observations"] == timed_shots * 164 and row["timing"]["direct_end_to_end"]["observations"] == timed_shots * 164 for row in basis_rows), "Complete paired timing vectors."),
        check("phase_additivity", all(row["phase_additivity"]["direct"] and row["phase_additivity"]["sync"] for row in basis_rows), "Every phase sum equals its total."),
        check("raw_vectors", all(len(row["timing"]["direct_end_to_end"]["raw_nanoseconds_sha256"]) == 64 and len(row["timing"]["sync_end_to_end"]["raw_nanoseconds_sha256"]) == 64 for row in basis_rows), "Raw uint64 timing vectors bound."),
        check("classification", classification in protocol["classification_rule"]["order"], classification),
        check("relative_score_guard", (geometric_speedup is not None) == semantic_pass and result["reference_relative_score"]["absolute_deadline_waived"] is False, "Score follows semantic veto and cannot waive deadline."),
        check("hard_boundaries", result["verdict"]["hardware_decoder_deadline_passed"] is False and result["verdict"]["full_b2_credit_ready"] is False and result["verdict"]["p023_scalable_memory_ready"] is False and result["verdict"]["b7_resource_credit"] == 0, "No downstream credit."),
    ]
    result["checks"] = checks
    result["summary"] = {
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "classification": classification,
        "semantic_veto_pass": semantic_pass,
        "matching_kernel_tail_pass": matching_pass,
        "direct_path_tail_pass": direct_pass,
        "sync_path_tail_pass": sync_pass,
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
                        "sync": row["timing"]["sync_end_to_end"]["raw_nanoseconds_sha256"],
                        "direct": row["timing"]["direct_end_to_end"]["raw_nanoseconds_sha256"],
                        "matching": row["timing"]["direct_phases"]["matching_kernel"]["raw_nanoseconds_sha256"],
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
