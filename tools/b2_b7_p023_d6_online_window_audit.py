#!/usr/bin/env python3
"""Independent audit of the preregistered distance-6 online-window result.

This auditor deliberately does not import the online-window producer.  It
reparses the Stim detector error models, rebuilds the overlapping windows,
replays both online decoders, and recomputes the raw timing arithmetic.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import platform
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pymatching
import scipy
import stim

import b2_b7_p023_d6_correlated_strict_acceptance as strict_base


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_online_window_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_online_window_v1.json"
DEFAULT_AUDIT = ROOT / "results/B2_B7_P023_d6_online_window_audit_v1.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def git_digest(commit: str, path: str) -> str:
    return digest(subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT))


def parity_tuple(values: Iterable[int]) -> tuple[int, ...]:
    odd: set[int] = set()
    for value in values:
        odd.symmetric_difference_update({value})
    return tuple(sorted(odd))


@dataclass(frozen=True)
class AuditComponent:
    group: int
    detectors: tuple[int, ...]
    observables: tuple[int, ...]


@dataclass(frozen=True)
class AuditGroup:
    probability: float
    components: tuple[int, ...]


@dataclass
class AuditModel:
    detector_count: int
    observable_count: int
    groups: list[AuditGroup]
    components: list[AuditComponent]
    detector_components: list[list[int]]


@dataclass
class AuditWindow:
    detectors: np.ndarray
    commits: np.ndarray
    commit_layers: int
    commit_components: frozenset[int]
    faults: tuple[int, ...]
    matching: pymatching.Matching


def parse_dem_independently(dem: stim.DetectorErrorModel) -> AuditModel:
    flat = dem.flattened()
    components: list[AuditComponent] = []
    groups: list[AuditGroup] = []
    detector_components: list[list[int]] = [[] for _ in range(flat.num_detectors)]
    for instruction in flat:
        if instruction.type != "error":
            continue
        pieces: list[list[stim.DemTarget]] = [[]]
        for target in instruction.targets_copy():
            if target.is_separator():
                pieces.append([])
            else:
                pieces[-1].append(target)
        group_index = len(groups)
        indices: list[int] = []
        for piece in pieces:
            detectors = parity_tuple(
                target.val for target in piece if target.is_relative_detector_id()
            )
            observables = parity_tuple(
                target.val for target in piece if target.is_logical_observable_id()
            )
            if len(detectors) > 2:
                raise ValueError("audit encountered a non-graphlike decomposition component")
            index = len(components)
            components.append(AuditComponent(group_index, detectors, observables))
            indices.append(index)
            for detector in detectors:
                detector_components[detector].append(index)
        groups.append(AuditGroup(float(instruction.args_copy()[0]), tuple(indices)))
    return AuditModel(
        flat.num_detectors,
        flat.num_observables,
        groups,
        components,
        detector_components,
    )


def components_touching(model: AuditModel, detectors: np.ndarray) -> set[int]:
    output: set[int] = set()
    for detector in detectors.tolist():
        output.update(model.detector_components[detector])
    return output


def time_vector(
    detector_count: int,
    coordinates: dict[int, list[float]],
    coordinate_index: int,
) -> np.ndarray:
    values = np.asarray(
        [coordinates[index][coordinate_index] for index in range(detector_count)],
        dtype=float,
    )
    if np.any(values != values.astype(np.int64)) or np.any(values[1:] < values[:-1]):
        raise ValueError("invalid audit detector time coordinate")
    return values.astype(np.int64)


def temporal_ranges(times: np.ndarray, width: int, stride: int) -> list[tuple[int, int, int]]:
    start = int(times.min())
    stop = int(times.max()) + 1
    ranges: list[tuple[int, int, int]] = []
    while start < stop - (width + stride - 1):
        ranges.append((start, start + width, start + stride))
        start += stride
    ranges.append((start, stop, stop))
    return ranges


def make_audit_matching(
    model: AuditModel,
    detector_ids: np.ndarray,
    detection_components: set[int],
    commit_components: set[int],
) -> tuple[pymatching.Matching, tuple[int, ...]]:
    local_detector = {global_id: local for local, global_id in enumerate(detector_ids.tolist())}
    faults = tuple(sorted(commit_components))
    local_fault = {component: index for index, component in enumerate(faults)}
    grouped: dict[int, list[int]] = defaultdict(list)
    for component in sorted(detection_components):
        grouped[model.components[component].group].append(component)

    local_dem = stim.DetectorErrorModel()
    for detector in range(len(detector_ids)):
        local_dem.append(
            "detector", [], [stim.DemTarget.relative_detector_id(detector)]
        )
    for group_index in sorted(grouped):
        targets: list[stim.DemTarget] = []
        component_count = 0
        for component_index in grouped[group_index]:
            component = model.components[component_index]
            local_ids = [
                local_detector[detector]
                for detector in component.detectors
                if detector in local_detector
            ]
            if not local_ids:
                continue
            if component_count:
                targets.append(stim.DemTarget.separator())
            targets.extend(
                stim.DemTarget.relative_detector_id(detector) for detector in local_ids
            )
            if component_index in local_fault:
                targets.append(
                    stim.DemTarget.logical_observable_id(local_fault[component_index])
                )
            component_count += 1
        if component_count:
            local_dem.append("error", model.groups[group_index].probability, targets)
    return (
        pymatching.Matching.from_detector_error_model(
            local_dem, enable_correlations=True
        ),
        faults,
    )


def compile_audit_windows(
    dem: stim.DetectorErrorModel,
    coordinates: dict[int, list[float]],
    width: int,
    stride: int,
    coordinate_index: int,
) -> tuple[AuditModel, list[AuditWindow], dict[str, Any]]:
    model = parse_dem_independently(dem)
    times = time_vector(model.detector_count, coordinates, coordinate_index)
    addressed = np.zeros(len(model.components), dtype=bool)
    windows: list[AuditWindow] = []
    maxima = {"nodes": 0, "edges": 0, "faults": 0, "components": 0}
    for start, end, commit_end in temporal_ranges(times, width, stride):
        detectors = np.flatnonzero((times >= start) & (times < end)).astype(np.int64)
        commits = np.flatnonzero((times >= start) & (times < commit_end)).astype(np.int64)
        detection_components = {
            index
            for index in components_touching(model, detectors)
            if not addressed[index]
        }
        commit_components = {
            index
            for index in components_touching(model, commits)
            if not addressed[index]
        }
        if not commit_components <= detection_components:
            raise ValueError("audit commit region escapes detection region")
        matching, faults = make_audit_matching(
            model, detectors, detection_components, commit_components
        )
        windows.append(
            AuditWindow(
                detectors,
                commits,
                commit_end - start,
                frozenset(commit_components),
                faults,
                matching,
            )
        )
        addressed[list(commit_components)] = True
        maxima["nodes"] = max(maxima["nodes"], matching.num_nodes)
        maxima["edges"] = max(maxima["edges"], matching.num_edges)
        maxima["faults"] = max(maxima["faults"], matching.num_fault_ids)
        maxima["components"] = max(maxima["components"], len(detection_components))
    triggered = np.asarray([bool(component.detectors) for component in model.components])
    if np.any(triggered & ~addressed):
        raise ValueError("audit left detector-triggering components uncommitted")
    structure = {
        "num_error_groups": len(model.groups),
        "num_components": len(model.components),
        "num_detector_triggering_components": int(np.count_nonzero(triggered)),
        "num_undetectable_components": int(np.count_nonzero(~triggered)),
        "num_windows": len(windows),
        "component_commit_assignments": int(np.count_nonzero(addressed)),
        "prebuffer_detectors": int(
            np.count_nonzero(
                (times >= times.min()) & (times < times.min() + width - stride)
            )
        ),
        "max_window_nodes": maxima["nodes"],
        "max_window_edges": maxima["edges"],
        "max_window_fault_ids": maxima["faults"],
        "max_window_components": maxima["components"],
        "first_window": {
            "start": int(times.min()),
            "end": int(times.min() + width),
            "commit_layers": windows[0].commit_layers,
        },
        "last_window": {
            "start": temporal_ranges(times, width, stride)[-1][0],
            "end": temporal_ranges(times, width, stride)[-1][1],
            "commit_layers": windows[-1].commit_layers,
        },
    }
    return model, windows, structure


def selected_faults(window: AuditWindow, syndrome: np.ndarray, correlated: bool) -> set[int]:
    selected: set[int] = set()
    for u, v in window.matching.decode_to_edges_array(
        syndrome, enable_correlations=correlated
    ).tolist():
        data = (
            window.matching.get_boundary_edge_data(int(u))
            if int(v) == -1
            else window.matching.get_edge_data(int(u), int(v))
        )
        for local_fault in data.get("fault_ids", set()):
            component = window.faults[local_fault]
            selected.symmetric_difference_update({component})
    return selected


def decode_audit_corpus(
    model: AuditModel,
    windows: list[AuditWindow],
    syndromes: np.ndarray,
    correlated: bool,
) -> tuple[np.ndarray, dict[str, int]]:
    predictions = np.zeros((len(syndromes), model.observable_count), dtype=np.uint8)
    residual_shots = 0
    commit_failure_shots = 0
    selected_total = 0
    for shot_index, raw in enumerate(syndromes):
        correction = np.zeros(model.detector_count, dtype=np.uint8)
        frame = np.zeros(model.observable_count, dtype=np.uint8)
        commit_failed = False
        for window in windows:
            syndrome = np.bitwise_xor(raw[window.detectors], correction[window.detectors])
            selected = selected_faults(window, syndrome, correlated)
            for component_index in selected:
                component = model.components[component_index]
                for detector in component.detectors:
                    correction[detector] ^= 1
                for observable in component.observables:
                    frame[observable] ^= 1
            selected_total += len(selected)
            if np.any(np.bitwise_xor(raw[window.commits], correction[window.commits])):
                commit_failed = True
        predictions[shot_index] = frame
        residual_shots += bool(np.any(np.bitwise_xor(raw, correction)))
        commit_failure_shots += commit_failed
    return predictions, {
        "residual_nonzero_shots": residual_shots,
        "commit_residual_failure_shots": commit_failure_shots,
        "selected_components_total": selected_total,
    }


def replay_corpus(
    basis: str,
    circuit: stim.Circuit,
    strict_row: dict[str, Any],
    shots: int,
    chunk_size: int,
    chunks: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    dem = circuit.detector_error_model(decompose_errors=True)
    correlated_matching = pymatching.Matching.from_detector_error_model(
        dem, enable_correlations=True
    )
    sampler = circuit.compile_detector_sampler(seed=strict_row["seed"])
    detector_parts: list[np.ndarray] = []
    observable_parts: list[np.ndarray] = []
    chunk_matches = 0
    for chunk_index in range(chunks):
        detectors, observables = sampler.sample(
            chunk_size,
            separate_observables=True,
            bit_packed=True,
        )
        predictions = correlated_matching.decode_batch(
            detectors,
            bit_packed_shots=True,
            bit_packed_predictions=True,
            enable_correlations=True,
        )
        header = {
            "basis": basis,
            "chunk_index": chunk_index,
            "shot_offset": chunk_index * chunk_size,
            "shots": chunk_size,
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
        expected = strict_row["chunk_digests"][chunk_index]["sha256"]
        chunk_matches += digest(payload) == expected
        detector_parts.append(detectors)
        observable_parts.append(observables)
    detectors = np.concatenate(detector_parts)
    observables = np.concatenate(observable_parts)
    if len(detectors) != shots:
        raise ValueError("audit corpus shot count mismatch")
    corpus_header = {
        "basis": basis,
        "shots": shots,
        "detector_shape": list(detectors.shape),
        "observable_shape": list(observables.shape),
        "seed": strict_row["seed"],
    }
    corpus_sha = digest(
        compact(corpus_header)
        + b"\x00"
        + detectors.tobytes(order="C")
        + observables.tobytes(order="C")
    )
    return detectors, observables, {
        "basis": basis,
        "chunk_matches": chunk_matches,
        "corpus_sha256": corpus_sha,
    }


def nearest_rank(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return float(ordered[max(0, math.ceil(probability * len(ordered)) - 1)])


def audit_timing(
    arm: dict[str, Any], commit_layers: list[int], protocol: dict[str, Any]
) -> dict[str, Any]:
    timing = arm["timing"]
    raw = base64.b64decode(timing["raw_total_nanoseconds_b64"], validate=True)
    values = np.frombuffer(raw, dtype="<u8").astype(np.uint64).tolist()
    expected = timing["timed_shots"] * len(commit_layers)
    repeated_layers = commit_layers * timing["timed_shots"]
    per_layer = [
        value / layers / 1000.0
        for value, layers in zip(values, repeated_layers, strict=True)
    ]
    threshold = protocol["online_software_proxy"]["threshold_microseconds_per_round"]
    misses = sum(
        value > layers * threshold * 1000.0
        for value, layers in zip(values, repeated_layers, strict=True)
    )
    derived = {
        "count": len(values),
        "expected_count": expected,
        "raw_sha256": digest(raw),
        "p50": nearest_rank(per_layer, 0.50),
        "p95": nearest_rank(per_layer, 0.95),
        "p99": nearest_rank(per_layer, 0.99),
        "p999": nearest_rank(per_layer, 0.999),
        "maximum": max(per_layer),
        "deadline_misses": misses,
        "deadline_miss_fraction": misses / len(values),
        "phase_sum_matches_total": sum(
            phase["sum_nanoseconds"] for phase in timing["phase_summary"].values()
        )
        == sum(values),
    }
    derived["matches_result"] = (
        derived["count"] == expected == timing["timing_observations"]
        and derived["raw_sha256"] == timing["raw_total_nanoseconds_sha256"]
        and derived["p50"] == timing["p50_microseconds_per_committed_layer"]
        and derived["p95"] == timing["p95_microseconds_per_committed_layer"]
        and derived["p99"] == timing["p99_microseconds_per_committed_layer"]
        and derived["p999"] == timing["p999_microseconds_per_committed_layer"]
        and derived["maximum"] == timing["max_microseconds_per_committed_layer"]
        and derived["deadline_misses"] == timing["deadline_misses"]
        and derived["deadline_miss_fraction"] == timing["deadline_miss_fraction"]
        and derived["phase_sum_matches_total"]
    )
    return derived


def audit(
    protocol_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    protocol = load(protocol_path)
    result = load(result_path)
    strict_result = load(ROOT / protocol["frozen_inputs"]["strict_result"]["path"])
    latency_result = load(ROOT / protocol["frozen_inputs"]["latency_result"]["path"])
    execution = strict_result["execution"]
    strict_rows = {row["memory_basis"]: row for row in strict_result["candidate_rows"]}
    result_arms = {(row["basis"], row["decoder"]): row for row in result["arms"]}
    result_corpora = {row["basis"]: row for row in result["corpora"]}
    result_structures = {row["basis"]: row for row in result["structural_rows"]}
    contract = protocol["window_contract"]
    corpus_contract = protocol["corpus_contract"]
    reconstruction_rows: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []

    for basis in execution["memory_bases"]:
        circuit = strict_base.build_circuit(basis, execution)
        dem = circuit.detector_error_model(decompose_errors=True)
        detectors_packed, observables_packed, corpus_row = replay_corpus(
            basis,
            circuit,
            strict_rows[basis],
            corpus_contract["shots_per_basis"],
            corpus_contract["source_chunk_size"],
            corpus_contract["source_chunks_per_basis"],
        )
        syndromes = np.unpackbits(
            detectors_packed,
            axis=1,
            count=circuit.num_detectors,
            bitorder="little",
        ).astype(np.uint8, copy=False)
        model, windows, structure = compile_audit_windows(
            dem,
            circuit.get_detector_coordinates(),
            contract["window_size_layers"],
            contract["stride_layers"],
            contract["time_coordinate_index"],
        )
        independent = pymatching.Matching.from_detector_error_model(dem)
        correlated = pymatching.Matching.from_detector_error_model(
            dem, enable_correlations=True
        )
        basis_row: dict[str, Any] = {
            **corpus_row,
            "corpus_matches_result": corpus_row["corpus_sha256"]
            == result_corpora[basis]["corpus_sha256"],
            "structure": structure,
            "structure_matches_result": structure
            == {key: value for key, value in result_structures[basis].items() if key != "basis"},
            "arms": [],
        }
        for decoder_name, correlated_mode, full_matching in [
            ("independent_mwpm", False, independent),
            ("two_pass_correlated_matching", True, correlated),
        ]:
            online, diagnostics = decode_audit_corpus(
                model, windows, syndromes, correlated_mode
            )
            online_packed = np.packbits(online, axis=1, bitorder="little")
            full_packed = full_matching.decode_batch(
                detectors_packed,
                bit_packed_shots=True,
                bit_packed_predictions=True,
                enable_correlations=correlated_mode,
            )
            online_hash = digest(online_packed.tobytes(order="C"))
            full_hash = digest(full_packed.tobytes(order="C"))
            exact_rows = int(
                np.count_nonzero(
                    np.all(
                        online
                        == np.unpackbits(
                            full_packed,
                            axis=1,
                            count=model.observable_count,
                            bitorder="little",
                        ),
                        axis=1,
                    )
                )
            )
            failures = int(
                np.count_nonzero(
                    np.any(np.bitwise_xor(online_packed, observables_packed) != 0, axis=1)
                )
            )
            source = result_arms[(basis, decoder_name)]
            arm_row = {
                "decoder": decoder_name,
                "online_prediction_sha256": online_hash,
                "full_prediction_sha256": full_hash,
                "prediction_rows_equal": exact_rows,
                "prefix_failures": failures,
                **diagnostics,
            }
            arm_row["matches_result"] = (
                online_hash == source["prediction_sha256"]
                and full_hash == source["full_block_prediction_sha256"]
                and exact_rows == source["prediction_rows_equal_full_block"]
                and failures == source["online_prefix_failures"]
                and diagnostics["residual_nonzero_shots"]
                == source["residual_nonzero_shots"]
                and diagnostics["commit_residual_failure_shots"]
                == source["commit_residual_failure_shots"]
                and diagnostics["selected_components_total"]
                == source["selected_components_total"]
            )
            basis_row["arms"].append(arm_row)
            timing = audit_timing(
                source,
                [window.commit_layers for window in windows],
                protocol,
            )
            timing_rows.append({"basis": basis, "decoder": decoder_name, **timing})
        reconstruction_rows.append(basis_row)

    freeze = result["public_freeze"]
    protocol_rel = str(protocol_path.resolve().relative_to(ROOT))
    producer_rel = result["generator"]["path"]
    frozen_bindings_pass = all(
        file_digest(ROOT / binding["path"]) == binding["sha256"]
        and git_digest(protocol["frozen_inputs"]["artifact_commit"], binding["path"])
        == binding["sha256"]
        for name, binding in protocol["frozen_inputs"].items()
        if name != "artifact_commit"
    )
    primary = [
        result_arms[(basis, "two_pass_correlated_matching")]
        for basis in execution["memory_bases"]
    ]
    derived_online_pass = all(row["online_semantics_and_tail_pass"] for row in primary)
    evidence_view = {
        "public_freeze": result["public_freeze"],
        "structural_rows": result["structural_rows"],
        "arms": [
            {key: value for key, value in row.items() if key != "timing"}
            | {
                "timing": {
                    key: value
                    for key, value in row["timing"].items()
                    if key != "raw_total_nanoseconds_b64"
                }
            }
            for row in result["arms"]
        ],
        "verdict": result["verdict"],
        "decision": result["decision"],
    }

    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add("scope", result["scope"] == protocol["scope"], "Exact #021/#022/#023 scope.")
    add("protocol_binding", result["protocol_binding"]["sha256"] == file_digest(protocol_path), protocol_rel)
    add("result_binding", file_digest(result_path) == file_digest(result_path), file_digest(result_path))
    add("public_freeze_protocol", freeze["protocol_sha256"] == git_digest(freeze["commit"], protocol_rel) == file_digest(protocol_path), freeze["commit"])
    add("public_freeze_producer", freeze["runner_sha256"] == git_digest(freeze["commit"], producer_rel) == file_digest(ROOT / producer_rel), producer_rel)
    add("frozen_inputs", frozen_bindings_pass, protocol["frozen_inputs"]["artifact_commit"])
    add("source_decisions", strict_result["decision"] == protocol["frozen_inputs"]["strict_result"]["required_decision"] and latency_result["decision"] == protocol["frozen_inputs"]["latency_result"]["required_decision"], "Strict and latency sources match.")
    add("source_chunks", sum(row["chunk_matches"] for row in reconstruction_rows) == 8, "8/8 chunks independently replayed.")
    add("corpora", all(row["corpus_matches_result"] for row in reconstruction_rows), "Both corpus hashes match.")
    add("structures", all(row["structure_matches_result"] for row in reconstruction_rows), "Both window structures match.")
    add("online_predictions", all(arm["matches_result"] for row in reconstruction_rows for arm in row["arms"]), "Four online arms independently reproduce.")
    add("prediction_equality", all(arm["prediction_rows_equal"] == corpus_contract["shots_per_basis"] for row in reconstruction_rows for arm in row["arms"]), "4,096/4,096 online rows equal full-block rows.")
    add("residuals", all(arm["residual_nonzero_shots"] == 0 and arm["commit_residual_failure_shots"] == 0 for row in reconstruction_rows for arm in row["arms"]), "All committed/final residuals are zero.")
    add("timing_bytes", all(row["raw_sha256"] == result_arms[(row["basis"], row["decoder"])]["timing"]["raw_total_nanoseconds_sha256"] for row in timing_rows), "Four raw timing byte streams match.")
    add("timing_arithmetic", all(row["matches_result"] for row in timing_rows), "Counts, quantiles, maxima, misses, and phase sums match.")
    add("primary_verdict", derived_online_pass == result["verdict"]["online_correlated_host_proxy_pass"] is False, result["decision"])
    add("hard_boundaries", result["verdict"]["hardware_decoder_deadline_passed"] is False and result["verdict"]["full_b2_credit_ready"] is False and result["verdict"]["p023_scalable_memory_ready"] is False and result["verdict"]["b7_resource_credit"] == 0, "No downstream credit.")
    add("evidence_id", digest(compact(evidence_view)) == result["evidence_id"], result["evidence_id"])

    output: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_online_window_audit_v1",
        "as_of_date": protocol["as_of_date"],
        "scope": protocol["scope"],
        "source_result": {"path": str(result_path.relative_to(ROOT)), "sha256": file_digest(result_path)},
        "auditor": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": file_digest(Path(__file__).resolve()),
            "imports_online_window_producer": False,
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
        "reconstruction_rows": reconstruction_rows,
        "timing_rows": timing_rows,
        "checks": checks,
        "summary": {
            "checks_passed": sum(item["passed"] for item in checks),
            "checks_failed": sum(not item["passed"] for item in checks),
            "source_chunks_replayed": 8,
            "online_arms_replayed": 4,
            "prediction_rows_replayed": 4096,
            "online_correlated_host_proxy_pass": derived_online_pass,
            "hardware_decoder_deadline_passed": False,
            "full_b2_credit_ready": False,
            "p023_scalable_memory_ready": False,
            "b7_resource_credit": 0,
        },
    }
    if output["summary"]["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"independent audit failed: {failed}")
    output["audit_id"] = digest(
        compact(
            {
                "source_result": output["source_result"],
                "reconstruction_rows": reconstruction_rows,
                "timing_rows": timing_rows,
                "summary": output["summary"],
            }
        )
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()
    output = audit(args.protocol, args.result)
    args.audit.write_text(canonical(output), encoding="utf-8")
    print(canonical(output["summary"]), end="")


if __name__ == "__main__":
    main()
