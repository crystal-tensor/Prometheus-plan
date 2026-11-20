#!/usr/bin/env python3
"""Preregistered online-window QEC decoder benchmark for #021/#022/#023.

The benchmark implements sequential overlapping recovery.  A fixed 3d window
detects errors, the oldest d syndrome layers are committed, and correction
endpoints outside the commit region are propagated into later windows.  The
timed path includes bit packing, a local Unix socket transport, decoding, and a
feedback acknowledgement.  It is a host-local software proxy, never a hardware
deadline result.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import platform
import socket
import statistics
import struct
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pymatching
import scipy
import stim

import b2_b7_p023_d6_correlated_strict_acceptance as strict_base
import b2_b7_p023_d6_decoder_latency_matrix as latency_base


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_online_window_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_online_window_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_online_window_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_d6_online_window_discussion_v1.md"

INPUT_HEADER = struct.Struct("!4sBBHII")
FEEDBACK_PACKET = struct.Struct("!4sBBHIB")
INPUT_MAGIC = b"QEC1"
FEEDBACK_MAGIC = b"ACK1"
PREBUFFER_WINDOW = 0xFFFF


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


def xor_sorted(values: Iterable[int]) -> tuple[int, ...]:
    parity: set[int] = set()
    for value in values:
        if value in parity:
            parity.remove(value)
        else:
            parity.add(value)
    return tuple(sorted(parity))


@dataclass(frozen=True)
class Component:
    group_id: int
    detectors: tuple[int, ...]
    observables: tuple[int, ...]


@dataclass(frozen=True)
class ErrorGroup:
    probability: float
    component_ids: tuple[int, ...]


@dataclass
class ParsedModel:
    num_detectors: int
    num_observables: int
    groups: list[ErrorGroup]
    components: list[Component]
    components_by_detector: list[list[int]]


@dataclass
class Window:
    index: int
    start_time: int
    end_time: int
    detection_detectors: np.ndarray
    commit_detectors: np.ndarray
    arrival_detectors: np.ndarray
    commit_layers: int
    commit_component_ids: frozenset[int]
    local_fault_to_component: tuple[int, ...]
    matching: pymatching.Matching


@dataclass
class CompiledWindows:
    model: ParsedModel
    windows: list[Window]
    prebuffer_detectors: np.ndarray
    detector_times: np.ndarray
    structural: dict[str, Any]


def parse_model(dem: stim.DetectorErrorModel) -> ParsedModel:
    """Parse a flattened Stim DEM without discarding decomposition correlations."""
    flattened = dem.flattened()
    groups: list[ErrorGroup] = []
    components: list[Component] = []
    by_detector: list[list[int]] = [[] for _ in range(flattened.num_detectors)]
    for instruction in flattened:
        if instruction.type != "error":
            continue
        probability = float(instruction.args_copy()[0])
        target_groups: list[list[stim.DemTarget]] = [[]]
        for target in instruction.targets_copy():
            if target.is_separator():
                target_groups.append([])
            else:
                target_groups[-1].append(target)
        group_id = len(groups)
        component_ids: list[int] = []
        for target_group in target_groups:
            detector_ids = xor_sorted(
                target.val for target in target_group if target.is_relative_detector_id()
            )
            observable_ids = xor_sorted(
                target.val for target in target_group if target.is_logical_observable_id()
            )
            if len(detector_ids) > 2:
                raise ValueError(
                    f"non-graphlike suggested component with {len(detector_ids)} detectors"
                )
            component_id = len(components)
            components.append(Component(group_id, detector_ids, observable_ids))
            component_ids.append(component_id)
            for detector in detector_ids:
                by_detector[detector].append(component_id)
        groups.append(ErrorGroup(probability, tuple(component_ids)))
    return ParsedModel(
        num_detectors=flattened.num_detectors,
        num_observables=flattened.num_observables,
        groups=groups,
        components=components,
        components_by_detector=by_detector,
    )


def union_components(model: ParsedModel, detectors: Iterable[int]) -> set[int]:
    result: set[int] = set()
    for detector in detectors:
        result.update(model.components_by_detector[int(detector)])
    return result


def detector_time_array(
    num_detectors: int,
    coordinates: dict[int, list[float]],
    coordinate_index: int,
) -> np.ndarray:
    times = np.empty(num_detectors, dtype=np.int64)
    for detector in range(num_detectors):
        coords = coordinates.get(detector)
        if coords is None or len(coords) <= coordinate_index:
            raise ValueError(f"detector {detector} lacks time coordinate {coordinate_index}")
        value = coords[coordinate_index]
        if int(value) != value:
            raise ValueError(f"detector {detector} has non-integral time coordinate {value}")
        times[detector] = int(value)
    if np.any(times[1:] < times[:-1]):
        raise ValueError("detector time coordinate is not monotone")
    return times


def window_ranges(
    times: np.ndarray,
    window_size: int,
    stride: int,
) -> list[tuple[int, int, int]]:
    """Return (start, end-exclusive, commit-end-exclusive) time ranges."""
    start = int(times.min())
    end = int(times.max()) + 1
    ranges: list[tuple[int, int, int]] = []
    max_last = window_size + stride - 1
    while start < end - max_last:
        ranges.append((start, start + window_size, start + stride))
        start += stride
    ranges.append((start, end, end))
    return ranges


def build_window_dem(
    model: ParsedModel,
    detection_detectors: np.ndarray,
    detection_components: set[int],
    commit_components: set[int],
) -> tuple[stim.DetectorErrorModel, tuple[int, ...]]:
    local_of_global = {
        int(detector): local for local, detector in enumerate(detection_detectors.tolist())
    }
    commit_order = tuple(sorted(commit_components))
    fault_of_component = {component: fault for fault, component in enumerate(commit_order)}
    by_group: dict[int, list[int]] = defaultdict(list)
    for component in sorted(detection_components):
        by_group[model.components[component].group_id].append(component)

    window_dem = stim.DetectorErrorModel()
    for local in range(len(detection_detectors)):
        window_dem.append(
            "detector",
            [],
            [stim.DemTarget.relative_detector_id(local)],
        )
    for group_id in sorted(by_group):
        targets: list[stim.DemTarget] = []
        emitted = 0
        for component_id in by_group[group_id]:
            component = model.components[component_id]
            local_detectors = [
                local_of_global[detector]
                for detector in component.detectors
                if detector in local_of_global
            ]
            if not local_detectors:
                continue
            if emitted:
                targets.append(stim.DemTarget.separator())
            targets.extend(
                stim.DemTarget.relative_detector_id(detector) for detector in local_detectors
            )
            if component_id in fault_of_component:
                targets.append(
                    stim.DemTarget.logical_observable_id(fault_of_component[component_id])
                )
            emitted += 1
        if emitted:
            window_dem.append("error", model.groups[group_id].probability, targets)
    return window_dem, commit_order


def compile_windows(
    dem: stim.DetectorErrorModel,
    coordinates: dict[int, list[float]],
    window_size: int,
    stride: int,
    coordinate_index: int,
) -> CompiledWindows:
    model = parse_model(dem)
    times = detector_time_array(model.num_detectors, coordinates, coordinate_index)
    ranges = window_ranges(times, window_size, stride)
    addressed = np.zeros(len(model.components), dtype=bool)
    windows: list[Window] = []
    available: set[int] = set()

    first_start, _first_end, _first_commit_end = ranges[0]
    prebuffer_end = first_start + window_size - stride
    prebuffer = np.flatnonzero((times >= first_start) & (times < prebuffer_end)).astype(np.int64)
    available.update(prebuffer.tolist())

    max_nodes = 0
    max_edges = 0
    max_fault_ids = 0
    max_components = 0
    component_assignments = 0
    for index, (start, end, commit_end) in enumerate(ranges):
        detection_detectors = np.flatnonzero((times >= start) & (times < end)).astype(np.int64)
        commit_detectors = np.flatnonzero(
            (times >= start) & (times < commit_end)
        ).astype(np.int64)
        arrival = np.asarray(
            [detector for detector in detection_detectors.tolist() if detector not in available],
            dtype=np.int64,
        )
        available.update(arrival.tolist())
        detection_components = {
            component
            for component in union_components(model, detection_detectors)
            if not addressed[component]
        }
        commit_components = {
            component
            for component in union_components(model, commit_detectors)
            if not addressed[component]
        }
        if not commit_components.issubset(detection_components):
            raise ValueError(f"window {index} commit components escape detection region")
        window_dem, fault_map = build_window_dem(
            model,
            detection_detectors,
            detection_components,
            commit_components,
        )
        matching = pymatching.Matching.from_detector_error_model(
            window_dem,
            enable_correlations=True,
        )
        commit_layers = commit_end - start
        windows.append(
            Window(
                index=index,
                start_time=start,
                end_time=end,
                detection_detectors=detection_detectors,
                commit_detectors=commit_detectors,
                arrival_detectors=arrival,
                commit_layers=commit_layers,
                commit_component_ids=frozenset(commit_components),
                local_fault_to_component=fault_map,
                matching=matching,
            )
        )
        addressed[list(commit_components)] = True
        component_assignments += len(commit_components)
        max_nodes = max(max_nodes, matching.num_nodes)
        max_edges = max(max_edges, matching.num_edges)
        max_fault_ids = max(max_fault_ids, matching.num_fault_ids)
        max_components = max(max_components, len(detection_components))

    triggered_components = np.asarray(
        [bool(component.detectors) for component in model.components], dtype=bool
    )
    unaddressed = int(np.count_nonzero(triggered_components & ~addressed))
    if unaddressed:
        raise ValueError(f"{unaddressed} detector-triggering components were not committed")
    if len(available) != model.num_detectors:
        raise ValueError("stream arrival plan does not cover every detector")

    structural = {
        "num_error_groups": len(model.groups),
        "num_components": len(model.components),
        "num_detector_triggering_components": int(np.count_nonzero(triggered_components)),
        "num_undetectable_components": int(np.count_nonzero(~triggered_components)),
        "num_windows": len(windows),
        "component_commit_assignments": component_assignments,
        "prebuffer_detectors": len(prebuffer),
        "max_window_nodes": max_nodes,
        "max_window_edges": max_edges,
        "max_window_fault_ids": max_fault_ids,
        "max_window_components": max_components,
        "first_window": {
            "start": windows[0].start_time,
            "end": windows[0].end_time,
            "commit_layers": windows[0].commit_layers,
        },
        "last_window": {
            "start": windows[-1].start_time,
            "end": windows[-1].end_time,
            "commit_layers": windows[-1].commit_layers,
        },
    }
    return CompiledWindows(model, windows, prebuffer, times, structural)


def recv_exact(sock: socket.socket, size: int) -> bytes:
    output = bytearray()
    while len(output) < size:
        part = sock.recv(size - len(output))
        if not part:
            raise ConnectionError("socket closed before packet completed")
        output.extend(part)
    return bytes(output)


def transport_input(
    sender: socket.socket,
    receiver: socket.socket,
    basis_code: int,
    decoder_code: int,
    window_index: int,
    shot_index: int,
    detector_values: np.ndarray,
) -> np.ndarray:
    values = np.asarray(detector_values, dtype=np.uint8)
    packed = np.packbits(values, bitorder="little").tobytes()
    header = INPUT_HEADER.pack(
        INPUT_MAGIC,
        basis_code,
        decoder_code,
        window_index,
        shot_index,
        len(values),
    )
    sender.sendall(header + packed)
    received_header = recv_exact(receiver, INPUT_HEADER.size)
    magic, got_basis, got_decoder, got_window, got_shot, bit_count = INPUT_HEADER.unpack(
        received_header
    )
    if (magic, got_basis, got_decoder, got_window, got_shot) != (
        INPUT_MAGIC,
        basis_code,
        decoder_code,
        window_index,
        shot_index,
    ):
        raise ValueError("input transport header mismatch")
    received_payload = recv_exact(receiver, math.ceil(bit_count / 8))
    return np.unpackbits(
        np.frombuffer(received_payload, dtype=np.uint8),
        count=bit_count,
        bitorder="little",
    ).astype(np.uint8, copy=False)


def transport_feedback(
    sender: socket.socket,
    receiver: socket.socket,
    basis_code: int,
    decoder_code: int,
    window_index: int,
    shot_index: int,
    frame_bit: int,
) -> None:
    packet = FEEDBACK_PACKET.pack(
        FEEDBACK_MAGIC,
        basis_code,
        decoder_code,
        window_index,
        shot_index,
        frame_bit,
    )
    sender.sendall(packet)
    received = recv_exact(receiver, FEEDBACK_PACKET.size)
    values = FEEDBACK_PACKET.unpack(received)
    if values != (
        FEEDBACK_MAGIC,
        basis_code,
        decoder_code,
        window_index,
        shot_index,
        frame_bit,
    ):
        raise ValueError("feedback transport mismatch")


def edge_fault_ids(matching: pymatching.Matching, u: int, v: int) -> set[int]:
    data = (
        matching.get_boundary_edge_data(u)
        if v == -1
        else matching.get_edge_data(u, v)
    )
    return set(data.get("fault_ids", set()))


def decode_stream(
    compiled: CompiledWindows,
    raw_syndrome: np.ndarray,
    *,
    enable_correlations: bool,
    basis_code: int,
    decoder_code: int,
    shot_index: int,
    record_timing: bool,
) -> tuple[np.ndarray, dict[str, Any]]:
    model = compiled.model
    raw_syndrome = np.asarray(raw_syndrome, dtype=np.uint8)
    if raw_syndrome.shape != (model.num_detectors,):
        raise ValueError("raw syndrome shape mismatch")
    received = np.zeros(model.num_detectors, dtype=np.uint8)
    correction = np.zeros(model.num_detectors, dtype=np.uint8)
    frame = np.zeros(model.num_observables, dtype=np.uint8)
    total_ns: list[int] = []
    decode_ns: list[int] = []
    input_ns: list[int] = []
    feedback_ns: list[int] = []
    selected_components_total = 0
    commit_residual_failures = 0

    qpu_sock, decoder_sock = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        prebuffer_values = raw_syndrome[compiled.prebuffer_detectors]
        delivered = transport_input(
            qpu_sock,
            decoder_sock,
            basis_code,
            decoder_code,
            PREBUFFER_WINDOW,
            shot_index,
            prebuffer_values,
        )
        received[compiled.prebuffer_detectors] = delivered

        for window in compiled.windows:
            start_total = time.perf_counter_ns()
            arrival_values = raw_syndrome[window.arrival_detectors]
            delivered = transport_input(
                qpu_sock,
                decoder_sock,
                basis_code,
                decoder_code,
                window.index,
                shot_index,
                arrival_values,
            )
            received[window.arrival_detectors] = delivered
            after_input = time.perf_counter_ns()

            syndrome = np.bitwise_xor(
                received[window.detection_detectors],
                correction[window.detection_detectors],
            )
            selected_edges = window.matching.decode_to_edges_array(
                syndrome,
                enable_correlations=enable_correlations,
            )
            selected_components: set[int] = set()
            for u, v in selected_edges.tolist():
                for local_fault in edge_fault_ids(window.matching, int(u), int(v)):
                    component_id = window.local_fault_to_component[local_fault]
                    if component_id not in window.commit_component_ids:
                        raise ValueError("matching emitted a non-commit fault label")
                    if component_id in selected_components:
                        selected_components.remove(component_id)
                    else:
                        selected_components.add(component_id)
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
            after_decode = time.perf_counter_ns()

            transport_feedback(
                decoder_sock,
                qpu_sock,
                basis_code,
                decoder_code,
                window.index,
                shot_index,
                int(frame[0]) if len(frame) else 0,
            )
            end_total = time.perf_counter_ns()
            if record_timing:
                total_ns.append(end_total - start_total)
                input_ns.append(after_input - start_total)
                decode_ns.append(after_decode - after_input)
                feedback_ns.append(end_total - after_decode)
    finally:
        qpu_sock.close()
        decoder_sock.close()

    if not np.array_equal(received, raw_syndrome):
        raise ValueError("stream transport did not reproduce the raw syndrome")
    residual = np.bitwise_xor(received, correction)
    diagnostics = {
        "residual_weight": int(np.count_nonzero(residual)),
        "commit_residual_failures": commit_residual_failures,
        "selected_components": selected_components_total,
        "raw_total_ns": total_ns,
        "raw_input_ns": input_ns,
        "raw_decode_ns": decode_ns,
        "raw_feedback_ns": feedback_ns,
    }
    return frame, diagnostics


def nearest_rank(values: list[float] | list[int], probability: float) -> float:
    if not values:
        raise ValueError("cannot summarize an empty timing vector")
    ordered = sorted(values)
    index = max(0, math.ceil(probability * len(ordered)) - 1)
    return float(ordered[index])


def encode_u64(values: list[int]) -> tuple[str, str]:
    raw = np.asarray(values, dtype="<u8").tobytes(order="C")
    return base64.b64encode(raw).decode("ascii"), sha_bytes(raw)


def timing_summary(
    totals: list[int],
    phases: dict[str, list[int]],
    commit_layers: list[int],
    shots: int,
    threshold_us_per_round: float,
) -> dict[str, Any]:
    expected = shots * len(commit_layers)
    if len(totals) != expected:
        raise ValueError(f"timing count {len(totals)} != {expected}")
    repeated_layers = commit_layers * shots
    per_round_us = [
        total / layers / 1000.0 for total, layers in zip(totals, repeated_layers, strict=True)
    ]
    deadlines_ns = [layers * threshold_us_per_round * 1000.0 for layers in repeated_layers]
    misses = sum(total > deadline for total, deadline in zip(totals, deadlines_ns, strict=True))
    encoded, raw_sha = encode_u64(totals)
    summary: dict[str, Any] = {
        "timed_shots": shots,
        "windows_per_shot": len(commit_layers),
        "timing_observations": len(totals),
        "quantile_method": "nearest_rank_ceil_qn",
        "p50_microseconds_per_committed_layer": nearest_rank(per_round_us, 0.50),
        "p95_microseconds_per_committed_layer": nearest_rank(per_round_us, 0.95),
        "p99_microseconds_per_committed_layer": nearest_rank(per_round_us, 0.99),
        "p999_microseconds_per_committed_layer": nearest_rank(per_round_us, 0.999),
        "max_microseconds_per_committed_layer": max(per_round_us),
        "deadline_misses": misses,
        "deadline_miss_fraction": misses / len(totals),
        "raw_total_nanoseconds_encoding": "base64_little_endian_uint64",
        "raw_total_nanoseconds_b64": encoded,
        "raw_total_nanoseconds_sha256": raw_sha,
    }
    phase_summary: dict[str, Any] = {}
    for phase, values in phases.items():
        if len(values) != expected:
            raise ValueError(f"{phase} timing count mismatch")
        phase_summary[phase] = {
            "median_nanoseconds": statistics.median(values),
            "p99_nanoseconds": nearest_rank(values, 0.99),
            "max_nanoseconds": max(values),
            "sum_nanoseconds": sum(values),
            "sha256_little_endian_uint64": sha_bytes(
                np.asarray(values, dtype="<u8").tobytes(order="C")
            ),
        }
    summary["phase_summary"] = phase_summary
    return summary


def preflight(protocol: dict[str, Any]) -> dict[str, Any]:
    strict_result = read(ROOT / protocol["frozen_inputs"]["strict_result"]["path"])
    execution = strict_result["execution"]
    contract = protocol["window_contract"]
    rows: list[dict[str, Any]] = []
    for basis in execution["memory_bases"]:
        circuit = strict_base.build_circuit(basis, execution)
        dem = circuit.detector_error_model(decompose_errors=True)
        compiled = compile_windows(
            dem,
            circuit.get_detector_coordinates(),
            contract["window_size_layers"],
            contract["stride_layers"],
            contract["time_coordinate_index"],
        )
        zero = np.zeros(circuit.num_detectors, dtype=np.uint8)
        zero_frames: dict[str, list[int]] = {}
        for decoder_code, (name, correlations) in enumerate(
            [("independent_mwpm", False), ("two_pass_correlated_matching", True)]
        ):
            frame, diagnostics = decode_stream(
                compiled,
                zero,
                enable_correlations=correlations,
                basis_code=0 if basis == "x" else 1,
                decoder_code=decoder_code,
                shot_index=0,
                record_timing=False,
            )
            if diagnostics["residual_weight"] or diagnostics["commit_residual_failures"]:
                raise ValueError(f"all-zero preflight failed for {basis}/{name}")
            zero_frames[name] = frame.tolist()
        rows.append(
            {
                "basis": basis,
                "detectors": circuit.num_detectors,
                "observables": circuit.num_observables,
                "structural": compiled.structural,
                "all_zero_frames": zero_frames,
                "stochastic_samples_observed": 0,
            }
        )
    return {
        "schema_version": "b2_b7_p023_d6_online_window_preflight_v1",
        "scope": protocol["scope"],
        "window_contract": contract,
        "rows": rows,
        "stochastic_samples_observed": 0,
        "online_prediction_outcomes_observed": False,
    }


def run_arm(
    compiled: CompiledWindows,
    syndromes: np.ndarray,
    observables_packed: np.ndarray,
    full_predictions_packed: np.ndarray,
    *,
    basis: str,
    decoder_name: str,
    enable_correlations: bool,
    timed_shots: int,
    threshold_us_per_round: float,
    maximum_deadline_miss_fraction: float,
) -> dict[str, Any]:
    basis_code = 0 if basis == "x" else 1
    decoder_code = 1 if enable_correlations else 0
    if timed_shots > len(syndromes):
        raise ValueError("timed shot count exceeds corpus")

    # One outcome-bearing warmup is permitted only after the public freeze.
    decode_stream(
        compiled,
        syndromes[0],
        enable_correlations=enable_correlations,
        basis_code=basis_code,
        decoder_code=decoder_code,
        shot_index=0,
        record_timing=False,
    )

    predictions = np.zeros((len(syndromes), compiled.model.num_observables), dtype=np.uint8)
    totals: list[int] = []
    phase_values = {"input_transport": [], "decoder_and_commit": [], "feedback": []}
    residual_shots = 0
    commit_failure_shots = 0
    selected_components = 0
    for shot_index, syndrome in enumerate(syndromes):
        record = shot_index < timed_shots
        frame, diagnostics = decode_stream(
            compiled,
            syndrome,
            enable_correlations=enable_correlations,
            basis_code=basis_code,
            decoder_code=decoder_code,
            shot_index=shot_index,
            record_timing=record,
        )
        predictions[shot_index] = frame
        residual_shots += diagnostics["residual_weight"] != 0
        commit_failure_shots += diagnostics["commit_residual_failures"] != 0
        selected_components += diagnostics["selected_components"]
        if record:
            totals.extend(diagnostics["raw_total_ns"])
            phase_values["input_transport"].extend(diagnostics["raw_input_ns"])
            phase_values["decoder_and_commit"].extend(diagnostics["raw_decode_ns"])
            phase_values["feedback"].extend(diagnostics["raw_feedback_ns"])

    prediction_packed = np.packbits(predictions, axis=1, bitorder="little")
    full_unpacked = np.unpackbits(
        full_predictions_packed,
        axis=1,
        count=compiled.model.num_observables,
        bitorder="little",
    )
    exact_rows = np.all(predictions == full_unpacked, axis=1)
    failures = int(
        np.count_nonzero(
            np.any(np.bitwise_xor(prediction_packed, observables_packed) != 0, axis=1)
        )
    )
    timing = timing_summary(
        totals,
        phase_values,
        [window.commit_layers for window in compiled.windows],
        timed_shots,
        threshold_us_per_round,
    )
    exact = int(np.count_nonzero(exact_rows)) == len(syndromes)
    residual_zero = residual_shots == 0 and commit_failure_shots == 0
    tail_pass = (
        timing["p99_microseconds_per_committed_layer"] <= threshold_us_per_round
        and timing["deadline_miss_fraction"]
        <= maximum_deadline_miss_fraction
    )
    return {
        "basis": basis,
        "decoder": decoder_name,
        "enable_correlations": enable_correlations,
        "shots": len(syndromes),
        "warmup_shots": 1,
        "prediction_sha256": sha_bytes(prediction_packed.tobytes(order="C")),
        "full_block_prediction_sha256": sha_bytes(
            full_predictions_packed.tobytes(order="C")
        ),
        "prediction_rows_equal_full_block": int(np.count_nonzero(exact_rows)),
        "prediction_exact_match": exact,
        "online_prefix_failures": failures,
        "residual_nonzero_shots": residual_shots,
        "commit_residual_failure_shots": commit_failure_shots,
        "residual_zero": residual_zero,
        "selected_components_total": selected_components,
        "timing": timing,
        "tail_proxy_pass": tail_pass,
        "online_semantics_and_tail_pass": exact and residual_zero and tail_pass,
    }

def build_result(
    protocol: dict[str, Any],
    protocol_path: Path,
    public_freeze_commit: str,
    discussion_number: int,
) -> dict[str, Any]:
    if protocol["scope"]["included_catalog_problem_ids"] != [21, 22, 23]:
        raise ValueError("scope mismatch")
    if discussion_number <= 0:
        raise ValueError("a positive public discussion number is required")
    artifact_commit = protocol["frozen_inputs"]["artifact_commit"]
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", artifact_commit, public_freeze_commit],
        cwd=ROOT,
        check=True,
    )

    current_bindings: dict[str, Any] = {}
    commit_bindings: dict[str, Any] = {}
    for name, binding in protocol["frozen_inputs"].items():
        if name == "artifact_commit":
            continue
        path = ROOT / binding["path"]
        current_sha = sha_path(path)
        commit_sha = sha_bytes(git_blob(artifact_commit, binding["path"]))
        if current_sha != binding["sha256"] or commit_sha != binding["sha256"]:
            raise ValueError(f"frozen input mismatch: {name}")
        current_bindings[name] = {"path": binding["path"], "sha256": current_sha}
        commit_bindings[name] = {
            "path": binding["path"],
            "sha256": commit_sha,
            "matches": True,
        }

    runner_path = str(Path(__file__).resolve().relative_to(ROOT))
    protocol_rel = str(protocol_path.resolve().relative_to(ROOT))
    freeze_protocol_sha = sha_bytes(git_blob(public_freeze_commit, protocol_rel))
    freeze_runner_sha = sha_bytes(git_blob(public_freeze_commit, runner_path))
    if freeze_protocol_sha != sha_path(protocol_path):
        raise ValueError("protocol differs from public freeze")
    if freeze_runner_sha != sha_path(Path(__file__).resolve()):
        raise ValueError("runner differs from public freeze")

    strict_result = read(ROOT / protocol["frozen_inputs"]["strict_result"]["path"])
    latency_result = read(ROOT / protocol["frozen_inputs"]["latency_result"]["path"])
    if strict_result["decision"] != protocol["frozen_inputs"]["strict_result"][
        "required_decision"
    ]:
        raise ValueError("strict source decision mismatch")
    if latency_result["decision"] != protocol["frozen_inputs"]["latency_result"][
        "required_decision"
    ]:
        raise ValueError("latency source decision mismatch")
    execution = strict_result["execution"]
    strict_rows = {row["memory_basis"]: row for row in strict_result["candidate_rows"]}
    latency_corpora = {row["basis"]: row for row in latency_result["corpora"]}
    contract = protocol["window_contract"]
    corpus_contract = protocol["corpus_contract"]
    threshold = protocol["online_software_proxy"]["threshold_microseconds_per_round"]
    arms: list[dict[str, Any]] = []
    structural_rows: list[dict[str, Any]] = []
    corpus_rows: list[dict[str, Any]] = []

    for basis in execution["memory_bases"]:
        circuit = strict_base.build_circuit(basis, execution)
        dem = circuit.detector_error_model(decompose_errors=True)
        corpus, detectors_packed, observables_packed, independent, correlated = (
            latency_base.build_corpus(
                basis,
                execution,
                strict_rows[basis],
                corpus_contract,
            )
        )
        if corpus["corpus_sha256"] != latency_corpora[basis]["corpus_sha256"]:
            raise ValueError("latency corpus hash mismatch")
        syndromes = np.unpackbits(
            detectors_packed,
            axis=1,
            count=circuit.num_detectors,
            bitorder="little",
        ).astype(np.uint8, copy=False)
        compiled = compile_windows(
            dem,
            circuit.get_detector_coordinates(),
            contract["window_size_layers"],
            contract["stride_layers"],
            contract["time_coordinate_index"],
        )
        structural_rows.append({"basis": basis, **compiled.structural})
        corpus_rows.append(corpus)
        full_predictions = {
            "independent_mwpm": latency_base.decode_corpus(
                independent, detectors_packed, 256, False
            ),
            "two_pass_correlated_matching": latency_base.decode_corpus(
                correlated, detectors_packed, 256, True
            ),
        }
        for decoder_name, enable_correlations in [
            ("independent_mwpm", False),
            ("two_pass_correlated_matching", True),
        ]:
            arms.append(
                run_arm(
                    compiled,
                    syndromes,
                    observables_packed,
                    full_predictions[decoder_name],
                    basis=basis,
                    decoder_name=decoder_name,
                    enable_correlations=enable_correlations,
                    timed_shots=protocol["timing_contract"]["timed_shots_per_basis_decoder"],
                    threshold_us_per_round=threshold,
                    maximum_deadline_miss_fraction=protocol["online_software_proxy"][
                        "maximum_deadline_miss_fraction"
                    ],
                )
            )

    primary = [row for row in arms if row["decoder"] == "two_pass_correlated_matching"]
    online_proxy_pass = all(row["online_semantics_and_tail_pass"] for row in primary)
    decision = (
        "d6_correlated_online_window_host_proxy_pass_hardware_deadline_b2_p023_b7_open"
        if online_proxy_pass
        else "d6_correlated_online_window_host_proxy_fail_hardware_deadline_b2_p023_b7_open"
    )
    result: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_online_window_result_v1",
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
        "frozen_inputs_current": current_bindings,
        "frozen_inputs_at_commit": {"commit": artifact_commit, "bindings": commit_bindings},
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
        "corpus_contract": corpus_contract,
        "window_contract": contract,
        "transport_contract": protocol["transport_contract"],
        "timing_contract": protocol["timing_contract"],
        "online_software_proxy": protocol["online_software_proxy"],
        "external_basis": protocol["external_basis"],
        "corpora": corpus_rows,
        "structural_rows": structural_rows,
        "arms": arms,
        "verdict": {
            "online_correlated_host_proxy_pass": online_proxy_pass,
            "physical_memory_gate_passed": True,
            "hardware_decoder_deadline_passed": False,
            "full_b2_credit_ready": False,
            "p023_scalable_memory_ready": False,
            "b7_resource_credit": 0,
        },
        "hard_boundaries": protocol["hard_boundaries"],
        "decision": decision,
        "next_gate": (
            "If the online host proxy fails, localize semantic versus tail failure before changing"
            " one frozen axis. If it passes, move to a real asynchronous device/control path and"
            " model-mismatch stress; hardware, full B2, #023, and B7 remain open either way."
        ),
    }
    checks: list[dict[str, Any]] = []
    checks.append(check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact QEC scope."))
    checks.append(check("public_freeze", freeze_protocol_sha == sha_path(protocol_path) and freeze_runner_sha == sha_path(Path(__file__).resolve()), public_freeze_commit))
    checks.append(check("discussion", discussion_number > 0, result["public_freeze"]["discussion_url"]))
    checks.append(check("frozen_inputs", len(current_bindings) == 8 and all(item["matches"] for item in commit_bindings.values()), artifact_commit))
    checks.append(check("strict_source", strict_result["summary"]["physical_memory_gate_passed"] and strict_result["summary"]["checks_failed"] == 0, strict_result["decision"]))
    checks.append(check("latency_source", latency_result["verdict"]["software_batch1_backlog_proxy_pass"] and latency_result["verdict"]["hardware_decoder_deadline_passed"] is False, latency_result["decision"]))
    checks.append(check("corpora", len(corpus_rows) == 2 and all(row["shots"] == corpus_contract["shots_per_basis"] for row in corpus_rows), "Two frozen corpora."))
    checks.append(check("windows", len(structural_rows) == 2 and all(row["num_windows"] > 1 and row["max_window_nodes"] < 1000 for row in structural_rows), "O(d) temporal windows."))
    checks.append(check("arms", len(arms) == 4, "2 bases x 2 decoders."))
    checks.append(check("timing_counts", all(row["timing"]["timing_observations"] == row["timing"]["timed_shots"] * row["timing"]["windows_per_shot"] for row in arms), "Complete raw timing vectors."))
    checks.append(check("raw_timing_hashes", all(len(row["timing"]["raw_total_nanoseconds_sha256"]) == 64 for row in arms), "Raw timing vectors bound."))
    checks.append(check("residuals_reported", all("residual_zero" in row for row in arms), "Residual invariants reported."))
    checks.append(check("hardware_boundary", result["verdict"]["hardware_decoder_deadline_passed"] is False and result["verdict"]["full_b2_credit_ready"] is False and result["verdict"]["p023_scalable_memory_ready"] is False and result["verdict"]["b7_resource_credit"] == 0, "No hardware or downstream credit."))
    result["checks"] = checks
    result["summary"] = {
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "online_correlated_host_proxy_pass": online_proxy_pass,
        "hardware_decoder_deadline_passed": False,
        "full_b2_credit_ready": False,
        "p023_scalable_memory_ready": False,
        "b7_resource_credit": 0,
    }
    if result["summary"]["checks_failed"]:
        raise ValueError("formal result checks failed")
    evidence_view = {
        "public_freeze": result["public_freeze"],
        "structural_rows": structural_rows,
        "arms": [
            {
                key: value
                for key, value in row.items()
                if key != "timing"
            }
            | {
                "timing": {
                    key: value
                    for key, value in row["timing"].items()
                    if key != "raw_total_nanoseconds_b64"
                }
            }
            for row in arms
        ],
        "verdict": result["verdict"],
        "decision": decision,
    }
    result["evidence_id"] = sha_bytes(compact(evidence_view))
    return result


def report_text(result: dict[str, Any]) -> str:
    rows = []
    for arm in result["arms"]:
        timing = arm["timing"]
        rows.append(
            "| {basis} | {decoder} | {equal}/{shots} | {failures} | {p50:.3f} | {p99:.3f} | {miss:.2%} | {passed} |".format(
                basis=arm["basis"].upper(),
                decoder=arm["decoder"],
                equal=arm["prediction_rows_equal_full_block"],
                shots=arm["shots"],
                failures=arm["online_prefix_failures"],
                p50=timing["p50_microseconds_per_committed_layer"],
                p99=timing["p99_microseconds_per_committed_layer"],
                miss=timing["deadline_miss_fraction"],
                passed=arm["online_semantics_and_tail_pass"],
            )
        )
    return f"""# B2/B7/#023 Distance-6 Online Window Decoder v1

As of {result['as_of_date']}. Scope is exactly #021/B7, #022/B2, and #023.

## Heuristic question

Can a decoder still be called real time when its median keeps pace but its tail misses the next syndrome?

Public freeze: `{result['public_freeze']['commit']}` and Discussion #{result['public_freeze']['discussion_number']}.

| basis | decoder | prediction rows equal full block | prefix failures | p50 us/layer | p99 us/layer | deadline misses | online semantics + tail |
|---|---|---:|---:|---:|---:|---:|---|
{chr(10).join(rows)}

The primary correlated online host proxy is **{result['verdict']['online_correlated_host_proxy_pass']}**. The frozen line is 1 microsecond per committed syndrome layer at nearest-rank p99, at most 1% deadline misses, exact equality to the already frozen full-block predictions, and zero committed/final residual syndrome.

## What was actually timed

Each sequential overlapping-recovery window spans `3d=18` syndrome layers and commits the oldest `d=6`. The timed response starts before bit packing, crosses an in-process Unix socket, performs the window decode and correction propagation, sends the logical-frame feedback through the reverse socket, and ends after acknowledgement. Sampling and graph construction are excluded.

## Boundary

This is a host-local synchronous socket emulator, not a QPU/controller integration. Hardware decoder deadline passed remains **False**; full B2, scalable #023 memory, and B7 resource credit remain closed.

Formal checks: **{result['summary']['checks_passed']}/{len(result['checks'])}**. Evidence ID: `{result['evidence_id']}`.

## Next gate

{result['next_gate']}
"""


def discussion_text(result: dict[str, Any]) -> str:
    correlated = {
        row["basis"]: row
        for row in result["arms"]
        if row["decoder"] == "two_pass_correlated_matching"
    }
    x = correlated["x"]
    z = correlated["z"]
    return f"""Can a decoder be real time if one percent of its windows miss the clock?

The preregistered distance-6 overlapping-window experiment is complete. Each window spans 18 syndrome layers, commits 6, propagates correction endpoints forward, and times bit packing, Unix-socket transport, correlated matching, and feedback acknowledgement.

For correlated matching, X has p99 `{x['timing']['p99_microseconds_per_committed_layer']:.6f}` microseconds per committed layer with `{x['timing']['deadline_miss_fraction']:.2%}` deadline misses; Z has p99 `{z['timing']['p99_microseconds_per_committed_layer']:.6f}` with `{z['timing']['deadline_miss_fraction']:.2%}` misses.

X matches `{x['prediction_rows_equal_full_block']}/{x['shots']}` frozen full-block predictions and Z matches `{z['prediction_rows_equal_full_block']}/{z['shots']}`. The combined online host proxy is **{result['verdict']['online_correlated_host_proxy_pass']}**.

Questions for critique:

- Should a real-time decoder be judged by p99, worst case, or a declared logical-clock stall budget?
- Is exact agreement with a full-block decoder too strict, or the right first guard against window-boundary regressions?
- Does a Unix-socket path reveal enough about communication overhead to guide the next prototype, or should only a real QPU/controller link count?
- If latency and physical-qubit savings disagree, should they remain a Pareto pair rather than one scalar score?

Hardware deadline, full B2, scalable #023 memory, and B7 credit remain open regardless of this host result.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument("--public-freeze-commit")
    parser.add_argument("--discussion-number", type=int)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    protocol = read(args.protocol)
    if args.preflight:
        print(canonical(preflight(protocol)), end="")
        return
    if not args.public_freeze_commit or not args.discussion_number:
        parser.error("full execution requires --public-freeze-commit and --discussion-number")
    result = build_result(
        protocol,
        args.protocol,
        args.public_freeze_commit,
        args.discussion_number,
    )
    args.result.write_text(canonical(result), encoding="utf-8")
    args.report.write_text(report_text(result), encoding="utf-8")
    args.discussion.write_text(discussion_text(result), encoding="utf-8")
    print(canonical(result["summary"]), end="")


if __name__ == "__main__":
    main()
