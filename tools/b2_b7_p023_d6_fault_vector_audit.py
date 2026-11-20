#!/usr/bin/env python3
"""Independent audit of the d=6 public correction-bit fault-vector result."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import platform
import statistics
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import scipy
import stim

import b2_b7_p023_d6_correlated_strict_acceptance as strict_base
import b2_b7_p023_d6_online_window_audit as online_audit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_fault_vector_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_fault_vector_v1.json"
DEFAULT_AUDIT = ROOT / "results/B2_B7_P023_d6_fault_vector_audit_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def git_digest(commit: str, path: str) -> str:
    return digest(
        subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)
    )


def edge_key(u: int, v: int | None) -> tuple[int, int]:
    if v is None or int(v) == -1:
        return int(u), -1
    a, b = int(u), int(v)
    return (a, b) if a <= b else (b, a)


def graph_signature(matching: pymatching.Matching) -> list[list[Any]]:
    return sorted(
        [
            [
                list(edge_key(u, v)),
                float(data["weight"]),
                float(data["error_probability"]),
            ]
            for u, v, data in matching.edges()
        ]
    )


@dataclass(frozen=True)
class AuditFaultWindow:
    matching: pymatching.Matching
    detector_outputs: np.ndarray
    observable_outputs: np.ndarray
    fault_vector_bits: int


def build_fault_window(
    model: online_audit.AuditModel,
    window: online_audit.AuditWindow,
    detection_components: set[int],
) -> tuple[AuditFaultWindow, dict[str, int], str]:
    commit_components = set(window.commit_components)
    local_of_global = {
        int(detector): local
        for local, detector in enumerate(window.detectors.tolist())
    }
    detector_outputs = np.asarray(
        sorted(
            {
                detector
                for component_id in commit_components
                for detector in model.components[component_id].detectors
            }
        ),
        dtype=np.int64,
    )
    observable_outputs = np.asarray(
        sorted(
            {
                observable
                for component_id in commit_components
                for observable in model.components[component_id].observables
            }
        ),
        dtype=np.int64,
    )
    output_keys = tuple(("d", int(value)) for value in detector_outputs) + tuple(
        ("o", int(value)) for value in observable_outputs
    )
    fault_of_output = {item: index for index, item in enumerate(output_keys)}
    by_group: dict[int, list[int]] = defaultdict(list)
    for component_id in sorted(detection_components):
        by_group[model.components[component_id].group].append(component_id)
    window_dem = stim.DetectorErrorModel()
    for local in range(len(window.detectors)):
        window_dem.append(
            "detector", [], [stim.DemTarget.relative_detector_id(local)]
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
                stim.DemTarget.relative_detector_id(detector)
                for detector in local_detectors
            )
            if component_id in commit_components:
                targets.extend(
                    stim.DemTarget.logical_observable_id(
                        fault_of_output[("d", detector)]
                    )
                    for detector in component.detectors
                )
                targets.extend(
                    stim.DemTarget.logical_observable_id(
                        fault_of_output[("o", observable)]
                    )
                    for observable in component.observables
                )
            emitted += 1
        if emitted:
            window_dem.append("error", model.groups[group_id].probability, targets)
    matching = pymatching.Matching.from_detector_error_model(
        window_dem, enable_correlations=True
    )
    baseline_signature = graph_signature(window.matching)
    candidate_signature = graph_signature(matching)
    if baseline_signature != candidate_signature:
        raise ValueError("audit candidate graph differs from baseline")
    bits = len(detector_outputs) + len(observable_outputs)
    if matching.num_fault_ids != bits:
        raise ValueError("audit output IDs are not complete and contiguous")
    maximum_faults = 0
    multiple_fault_edges = 0
    for _u, _v, data in matching.edges():
        count = len(set(data.get("fault_ids", set())))
        maximum_faults = max(maximum_faults, count)
        multiple_fault_edges += count > 1
    return (
        AuditFaultWindow(
            matching=matching,
            detector_outputs=detector_outputs,
            observable_outputs=observable_outputs,
            fault_vector_bits=bits,
        ),
        {
            "detector_output_bits": len(detector_outputs),
            "observable_output_bits": len(observable_outputs),
            "fault_vector_bits": bits,
            "maximum_fault_ids_per_edge": maximum_faults,
            "edges_with_multiple_fault_ids": multiple_fault_edges,
        },
        digest(compact(candidate_signature)),
    )


def compile_fault_windows(
    model: online_audit.AuditModel,
    windows: list[online_audit.AuditWindow],
) -> tuple[list[AuditFaultWindow], dict[str, Any]]:
    addressed: set[int] = set()
    candidate_windows: list[AuditFaultWindow] = []
    signature_hashes: list[str] = []
    totals = {
        "windows": len(windows),
        "graph_signatures_equal": 0,
        "total_fault_vector_bits_across_windows": 0,
        "max_fault_vector_bits_per_window": 0,
        "max_detector_output_bits_per_window": 0,
        "max_observable_output_bits_per_window": 0,
        "maximum_fault_ids_per_merged_edge": 0,
        "merged_edges_with_multiple_output_fault_ids": 0,
        "correlation_groups_preserved_by_construction": True,
    }
    for window in windows:
        detection_components = (
            online_audit.components_touching(model, window.detectors) - addressed
        )
        candidate, row, signature_hash = build_fault_window(
            model, window, detection_components
        )
        candidate_windows.append(candidate)
        signature_hashes.append(signature_hash)
        totals["graph_signatures_equal"] += 1
        totals["total_fault_vector_bits_across_windows"] += row["fault_vector_bits"]
        totals["max_fault_vector_bits_per_window"] = max(
            totals["max_fault_vector_bits_per_window"], row["fault_vector_bits"]
        )
        totals["max_detector_output_bits_per_window"] = max(
            totals["max_detector_output_bits_per_window"],
            row["detector_output_bits"],
        )
        totals["max_observable_output_bits_per_window"] = max(
            totals["max_observable_output_bits_per_window"],
            row["observable_output_bits"],
        )
        totals["maximum_fault_ids_per_merged_edge"] = max(
            totals["maximum_fault_ids_per_merged_edge"],
            row["maximum_fault_ids_per_edge"],
        )
        totals["merged_edges_with_multiple_output_fault_ids"] += row[
            "edges_with_multiple_fault_ids"
        ]
        addressed.update(window.commit_components)
    totals["graph_signature_manifest_sha256"] = digest(compact(signature_hashes))
    return candidate_windows, totals


def decode_fault_corpus(
    model: online_audit.AuditModel,
    windows: list[online_audit.AuditWindow],
    candidate_windows: list[AuditFaultWindow],
    syndromes: np.ndarray,
) -> tuple[np.ndarray, dict[str, int]]:
    predictions = np.zeros((len(syndromes), model.observable_count), dtype=np.uint8)
    residual_shots = 0
    commit_failure_shots = 0
    output_nonzero_bits = 0
    for shot_index, raw in enumerate(syndromes):
        correction = np.zeros(model.detector_count, dtype=np.uint8)
        frame = np.zeros(model.observable_count, dtype=np.uint8)
        commit_failed = False
        for window, candidate in zip(windows, candidate_windows, strict=True):
            syndrome = np.bitwise_xor(
                raw[window.detectors], correction[window.detectors]
            )
            fault_vector = candidate.matching.decode(
                syndrome, enable_correlations=True
            )
            if len(fault_vector) != candidate.fault_vector_bits:
                raise ValueError("audit public decode returned a wrong-length vector")
            detector_count = len(candidate.detector_outputs)
            if detector_count:
                correction[candidate.detector_outputs] ^= fault_vector[:detector_count]
            if len(candidate.observable_outputs):
                frame[candidate.observable_outputs] ^= fault_vector[detector_count:]
            output_nonzero_bits += int(np.count_nonzero(fault_vector))
            if np.any(np.bitwise_xor(raw[window.commits], correction[window.commits])):
                commit_failed = True
        predictions[shot_index] = frame
        residual_shots += bool(np.any(np.bitwise_xor(raw, correction)))
        commit_failure_shots += commit_failed
    return predictions, {
        "residual_nonzero_shots": residual_shots,
        "commit_residual_failure_shots": commit_failure_shots,
        "output_nonzero_bits_total": output_nonzero_bits,
    }


def nearest_rank(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return float(ordered[max(0, math.ceil(probability * len(ordered)) - 1)])


def decode_vector(
    summary: dict[str, Any],
    commit_layers: list[int],
    shots: int,
    threshold_us_per_layer: float,
) -> tuple[list[int], dict[str, Any]]:
    raw = base64.b64decode(summary["raw_nanoseconds_b64"], validate=True)
    values = np.frombuffer(raw, dtype="<u8").astype(np.uint64).tolist()
    expected = shots * len(commit_layers)
    layers = commit_layers * shots
    per_layer = [
        value / layer_count / 1000.0
        for value, layer_count in zip(values, layers, strict=True)
    ]
    misses = sum(
        value > layer_count * threshold_us_per_layer * 1000.0
        for value, layer_count in zip(values, layers, strict=True)
    )
    derived = {
        "observations": len(values),
        "expected_observations": expected,
        "sum_nanoseconds": sum(values),
        "mean_nanoseconds": statistics.fmean(values),
        "p50_microseconds_per_committed_layer": nearest_rank(per_layer, 0.50),
        "p95_microseconds_per_committed_layer": nearest_rank(per_layer, 0.95),
        "p99_microseconds_per_committed_layer": nearest_rank(per_layer, 0.99),
        "p999_microseconds_per_committed_layer": nearest_rank(per_layer, 0.999),
        "max_microseconds_per_committed_layer": max(per_layer),
        "deadline_misses": misses,
        "deadline_miss_fraction": misses / len(values),
        "raw_nanoseconds_sha256": digest(raw),
    }
    derived["matches_result"] = all(
        [
            derived["observations"] == expected == summary["observations"],
            derived["sum_nanoseconds"] == summary["sum_nanoseconds"],
            derived["mean_nanoseconds"] == summary["mean_nanoseconds"],
            derived["p50_microseconds_per_committed_layer"]
            == summary["p50_microseconds_per_committed_layer"],
            derived["p95_microseconds_per_committed_layer"]
            == summary["p95_microseconds_per_committed_layer"],
            derived["p99_microseconds_per_committed_layer"]
            == summary["p99_microseconds_per_committed_layer"],
            derived["p999_microseconds_per_committed_layer"]
            == summary["p999_microseconds_per_committed_layer"],
            derived["max_microseconds_per_committed_layer"]
            == summary["max_microseconds_per_committed_layer"],
            derived["deadline_misses"] == summary["deadline_misses"],
            derived["deadline_miss_fraction"]
            == summary["deadline_miss_fraction"],
            derived["raw_nanoseconds_sha256"]
            == summary["raw_nanoseconds_sha256"],
        ]
    )
    return values, derived


def passes(
    summary: dict[str, Any],
    threshold_us_per_layer: float,
    maximum_miss_fraction: float,
) -> bool:
    return bool(
        summary["p99_microseconds_per_committed_layer"] <= threshold_us_per_layer
        and summary["deadline_miss_fraction"] <= maximum_miss_fraction
    )


def audit(protocol_path: Path, result_path: Path) -> dict[str, Any]:
    protocol = read(protocol_path)
    result = read(result_path)
    sparse_protocol = read(
        ROOT / protocol["frozen_inputs"]["sparse_protocol"]["path"]
    )
    attribution_protocol = read(
        ROOT / sparse_protocol["frozen_inputs"]["attribution_protocol"]["path"]
    )
    online_protocol = read(
        ROOT / attribution_protocol["frozen_inputs"]["online_protocol"]["path"]
    )
    strict_result = read(
        ROOT / online_protocol["frozen_inputs"]["strict_result"]["path"]
    )
    execution = strict_result["execution"]
    strict_rows = {
        row["memory_basis"]: row for row in strict_result["candidate_rows"]
    }
    source_rows = {row["basis"]: row for row in result["basis_rows"]}
    source_corpora = {row["basis"]: row for row in result["corpora"]}
    source_structures = {row["basis"]: row for row in result["structures"]}
    window_contract = online_protocol["window_contract"]
    corpus_contract = online_protocol["corpus_contract"]
    timed_shots = protocol["corpus_contract"][
        "timed_shots_per_basis_and_path"
    ]
    threshold = protocol["timing_contract"][
        "threshold_microseconds_per_committed_layer"
    ]
    maximum_miss = protocol["timing_contract"][
        "maximum_deadline_miss_fraction"
    ]
    reconstruction_rows: list[dict[str, Any]] = []
    timing_rows: list[dict[str, Any]] = []
    for basis in execution["memory_bases"]:
        source = source_rows[basis]
        circuit = strict_base.build_circuit(basis, execution)
        dem = circuit.detector_error_model(decompose_errors=True)
        detectors_packed, _observables_packed, corpus = online_audit.replay_corpus(
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
        model, windows, _window_structure = online_audit.compile_audit_windows(
            dem,
            circuit.get_detector_coordinates(),
            window_contract["window_size_layers"],
            window_contract["stride_layers"],
            window_contract["time_coordinate_index"],
        )
        candidate_windows, structural = compile_fault_windows(model, windows)
        candidate, candidate_diagnostics = decode_fault_corpus(
            model, windows, candidate_windows, syndromes
        )
        baseline, baseline_diagnostics = online_audit.decode_audit_corpus(
            model, windows, syndromes[:timed_shots], True
        )
        full_matching = pymatching.Matching.from_detector_error_model(
            dem, enable_correlations=True
        )
        full_packed = full_matching.decode_batch(
            detectors_packed,
            bit_packed_shots=True,
            bit_packed_predictions=True,
            enable_correlations=True,
        )
        full = np.unpackbits(
            full_packed,
            axis=1,
            count=model.observable_count,
            bitorder="little",
        )
        candidate_packed = np.packbits(candidate, axis=1, bitorder="little")
        baseline_packed = np.packbits(baseline, axis=1, bitorder="little")
        candidate_exact = int(np.count_nonzero(np.all(candidate == full, axis=1)))
        baseline_exact = int(
            np.count_nonzero(np.all(baseline == full[:timed_shots], axis=1))
        )
        cross_exact = int(
            np.count_nonzero(
                np.all(candidate[:timed_shots] == baseline, axis=1)
            )
        )
        candidate_hash = digest(candidate_packed.tobytes(order="C"))
        baseline_hash = digest(baseline_packed.tobytes(order="C"))
        full_hash = digest(full_packed.tobytes(order="C"))
        structural_matches = structural == {
            key: value
            for key, value in source_structures[basis].items()
            if key != "basis"
        }
        reconstruction = {
            "basis": basis,
            "source_chunks_replayed": corpus["chunk_matches"],
            "corpus_sha256": corpus["corpus_sha256"],
            "corpus_matches": corpus["corpus_sha256"]
            == source_corpora[basis]["corpus_sha256"],
            "structural": structural,
            "structural_matches": structural_matches,
            "candidate_prediction_sha256": candidate_hash,
            "baseline_timed_prediction_sha256": baseline_hash,
            "full_block_prediction_sha256": full_hash,
            "candidate_prediction_rows_equal_full_block": candidate_exact,
            "baseline_prediction_rows_equal_full_block": baseline_exact,
            "timed_cross_path_prediction_rows_equal": cross_exact,
            "candidate_diagnostics": candidate_diagnostics,
            "baseline_diagnostics": baseline_diagnostics,
        }
        reconstruction["matches_result"] = all(
            [
                candidate_hash == source["candidate_prediction_sha256"],
                baseline_hash == source["baseline_timed_prediction_sha256"],
                full_hash == source["full_block_prediction_sha256"],
                candidate_exact
                == source["candidate_prediction_rows_equal_full_block"],
                baseline_exact
                == source["baseline_prediction_rows_equal_full_block"],
                cross_exact == source["timed_cross_path_prediction_rows_equal"],
                candidate_diagnostics["residual_nonzero_shots"]
                == source["candidate_residual_nonzero_shots"],
                candidate_diagnostics["commit_residual_failure_shots"]
                == source["candidate_commit_residual_failure_shots"],
                candidate_diagnostics["output_nonzero_bits_total"]
                == source["candidate_output_nonzero_bits_total"],
                baseline_diagnostics["residual_nonzero_shots"]
                == source["baseline_residual_nonzero_shots"],
                baseline_diagnostics["commit_residual_failure_shots"]
                == source["baseline_commit_residual_failure_shots"],
                baseline_diagnostics["selected_components_total"]
                == source["baseline_timed_selected_components_total"],
                structural_matches,
            ]
        )
        reconstruction_rows.append(reconstruction)
        commit_layers = [window.commit_layers for window in windows]
        vectors: dict[str, list[int]] = {}
        derived: dict[str, Any] = {}
        for name, summary in [
            ("sparse_baseline_end_to_end", source["timing"]["sparse_baseline_end_to_end"]),
            ("public_candidate_end_to_end", source["timing"]["public_candidate_end_to_end"]),
        ]:
            vectors[name], derived[name] = decode_vector(
                summary, commit_layers, timed_shots, threshold
            )
        for phase, summary in source["timing"]["candidate_phases"].items():
            name = f"candidate::{phase}"
            vectors[name], derived[name] = decode_vector(
                summary, commit_layers, timed_shots, threshold
            )
        phase_additivity = all(
            vectors["public_candidate_end_to_end"][position]
            == sum(
                vectors[f"candidate::{phase}"][position]
                for phase in source["timing"]["candidate_phases"]
            )
            for position in range(len(vectors["public_candidate_end_to_end"]))
        )
        stage_pass = {
            name: passes(
                derived[f"candidate::{name}"], threshold, maximum_miss
            )
            for name in [
                "public_fault_vector_decode",
                "vectorized_correction_apply",
                "commit_residual_check",
            ]
        }
        stage_pass["candidate_direct_end_to_end"] = passes(
            derived["public_candidate_end_to_end"], threshold, maximum_miss
        )
        timing_rows.append(
            {
                "basis": basis,
                "derived": derived,
                "all_vectors_match_result": all(
                    row["matches_result"] for row in derived.values()
                ),
                "phase_additivity": phase_additivity,
                "stage_pass": stage_pass,
                "stage_pass_matches_result": stage_pass == source["stage_pass"],
            }
        )
    semantic_pass = all(
        row["matches_result"]
        and row["candidate_prediction_rows_equal_full_block"] == 1024
        and row["baseline_prediction_rows_equal_full_block"] == timed_shots
        and row["timed_cross_path_prediction_rows_equal"] == timed_shots
        and row["candidate_diagnostics"]["residual_nonzero_shots"] == 0
        and row["candidate_diagnostics"]["commit_residual_failure_shots"] == 0
        and row["baseline_diagnostics"]["residual_nonzero_shots"] == 0
        and row["baseline_diagnostics"]["commit_residual_failure_shots"] == 0
        for row in reconstruction_rows
    )
    public_decode_pass = all(
        row["stage_pass"]["public_fault_vector_decode"] for row in timing_rows
    )
    vector_apply_pass = all(
        row["stage_pass"]["vectorized_correction_apply"] for row in timing_rows
    )
    residual_check_pass = all(
        row["stage_pass"]["commit_residual_check"] for row in timing_rows
    )
    candidate_pass = all(
        row["stage_pass"]["candidate_direct_end_to_end"] for row in timing_rows
    )
    if not semantic_pass:
        classification = "semantic_regression"
    elif not public_decode_pass:
        classification = "public_fault_vector_decode_tail_bottleneck"
    elif not vector_apply_pass:
        classification = "vectorized_correction_apply_tail_bottleneck"
    elif not residual_check_pass:
        classification = "commit_residual_check_tail_bottleneck"
    elif not candidate_pass:
        classification = "public_candidate_direct_tail_bottleneck"
    else:
        classification = "public_candidate_host_proxy_pass"
    speedups = [
        row["derived"]["sparse_baseline_end_to_end"][
            "p99_microseconds_per_committed_layer"
        ]
        / row["derived"]["public_candidate_end_to_end"][
            "p99_microseconds_per_committed_layer"
        ]
        for row in timing_rows
    ]
    geometric_speedup = math.sqrt(speedups[0] * speedups[1]) if semantic_pass else None
    freeze = result["public_freeze"]
    protocol_rel = str(protocol_path.resolve().relative_to(ROOT))
    producer_rel = result["generator"]["path"]
    artifact_commit = protocol["frozen_inputs"]["artifact_commit"]
    frozen_inputs_pass = all(
        file_digest(ROOT / binding["path"]) == binding["sha256"]
        and git_digest(artifact_commit, binding["path"]) == binding["sha256"]
        for name, binding in protocol["frozen_inputs"].items()
        if name != "artifact_commit"
    )
    source_sparse = read(ROOT / protocol["frozen_inputs"]["sparse_result"]["path"])
    evidence_view = {
        "public_freeze": result["public_freeze"],
        "classification": result["classification"],
        "reference_relative_score": result["reference_relative_score"],
        "verdict": result["verdict"],
        "timing_hashes": [
            {
                "basis": row["basis"],
                "baseline": source_rows[row["basis"]]["timing"][
                    "sparse_baseline_end_to_end"
                ]["raw_nanoseconds_sha256"],
                "candidate": source_rows[row["basis"]]["timing"][
                    "public_candidate_end_to_end"
                ]["raw_nanoseconds_sha256"],
                "public_decode": source_rows[row["basis"]]["timing"][
                    "candidate_phases"
                ]["public_fault_vector_decode"]["raw_nanoseconds_sha256"],
                "vector_apply": source_rows[row["basis"]]["timing"][
                    "candidate_phases"
                ]["vectorized_correction_apply"]["raw_nanoseconds_sha256"],
            }
            for row in timing_rows
        ],
    }
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add("scope", result["scope"] == protocol["scope"], "Exact #021/#022/#023 scope.")
    add("protocol_binding", result["protocol_binding"]["sha256"] == file_digest(protocol_path), protocol_rel)
    add("public_freeze_protocol", freeze["protocol_sha256"] == git_digest(freeze["commit"], protocol_rel) == file_digest(protocol_path), freeze["commit"])
    add("public_freeze_producer", freeze["runner_sha256"] == git_digest(freeze["commit"], producer_rel) == file_digest(ROOT / producer_rel), producer_rel)
    add("frozen_inputs", frozen_inputs_pass, artifact_commit)
    add("source_classification", source_sparse["classification"] == protocol["frozen_inputs"]["sparse_result"]["required_classification"], source_sparse["classification"])
    add("pymatching_version", pymatching.__version__ == "2.4.0", pymatching.__version__)
    add("source_chunks", sum(row["source_chunks_replayed"] for row in reconstruction_rows) == 8, "8/8 frozen source chunks.")
    add("corpora", all(row["corpus_matches"] for row in reconstruction_rows), "Both corpus hashes reproduce.")
    add("graphs_and_output_maps", all(row["structural_matches"] for row in reconstruction_rows), "328 graph signatures and all output maps reproduce.")
    add("predictions", all(row["matches_result"] for row in reconstruction_rows), "Candidate and timed baseline predictions reproduce.")
    add("semantic_veto", semantic_pass == result["verdict"]["semantic_veto_pass"], f"semantic_veto_pass={semantic_pass}")
    add("raw_vectors", all(row["all_vectors_match_result"] for row in timing_rows), "All 16 raw timing vectors reproduce their statistics.")
    add("phase_additivity", all(row["phase_additivity"] for row in timing_rows), "Every candidate event total equals its six phases.")
    add("stage_passes", all(row["stage_pass_matches_result"] for row in timing_rows), "All absolute stage verdicts reproduce.")
    add("classification", classification == result["classification"], classification)
    add("relative_score", result["reference_relative_score"]["x_baseline_to_candidate_p99_speedup"] == speedups[0] and result["reference_relative_score"]["z_baseline_to_candidate_p99_speedup"] == speedups[1] and result["reference_relative_score"]["geometric_mean_baseline_to_candidate_p99_speedup"] == geometric_speedup and result["reference_relative_score"]["absolute_deadline_waived"] is False, f"geometric_speedup={geometric_speedup}")
    add("formal_checks", result["summary"]["checks_passed"] == 15 and result["summary"]["checks_failed"] == 0, "15/15 producer checks.")
    add("hard_boundaries", result["verdict"]["hardware_decoder_deadline_passed"] is False and result["verdict"]["full_b2_credit_ready"] is False and result["verdict"]["p023_scalable_memory_ready"] is False and result["verdict"]["b7_resource_credit"] == 0, "No downstream credit.")
    add("evidence_id", digest(compact(evidence_view)) == result["evidence_id"], result["evidence_id"])
    output: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_fault_vector_audit_v1",
        "as_of_date": protocol["as_of_date"],
        "scope": protocol["scope"],
        "source_result": {
            "path": str(result_path.resolve().relative_to(ROOT)),
            "sha256": file_digest(result_path),
        },
        "auditor": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": file_digest(Path(__file__).resolve()),
            "imports_fault_vector_producer": False,
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
        "derived": {
            "semantic_veto_pass": semantic_pass,
            "public_fault_vector_decode_tail_pass": public_decode_pass,
            "vectorized_correction_apply_tail_pass": vector_apply_pass,
            "commit_residual_check_tail_pass": residual_check_pass,
            "public_candidate_direct_tail_pass": candidate_pass,
            "classification": classification,
            "x_baseline_to_candidate_p99_speedup": speedups[0]
            if semantic_pass
            else None,
            "z_baseline_to_candidate_p99_speedup": speedups[1]
            if semantic_pass
            else None,
            "geometric_mean_baseline_to_candidate_p99_speedup": geometric_speedup,
        },
        "checks": checks,
        "summary": {
            "checks_passed": sum(item["passed"] for item in checks),
            "checks_failed": sum(not item["passed"] for item in checks),
            "source_chunks_replayed": 8,
            "candidate_prediction_rows_replayed": 2048,
            "baseline_timed_prediction_rows_replayed": 256,
            "raw_timing_vectors_replayed": 16,
            "classification": classification,
            "semantic_veto_pass": semantic_pass,
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
                "derived": output["derived"],
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
