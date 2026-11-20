#!/usr/bin/env python3
"""Independent audit of the d=6 latency-attribution result.

This auditor never imports the attribution producer.  It uses the previously
independent DEM/window implementation, reconstructs the frozen corpora and
predictions, and recomputes every raw timing statistic and classification.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import platform
import statistics
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import scipy
import stim

import b2_b7_p023_d6_correlated_strict_acceptance as strict_base
import b2_b7_p023_d6_online_window_audit as online_audit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_latency_attribution_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_latency_attribution_v1.json"
DEFAULT_AUDIT = ROOT / "results/B2_B7_P023_d6_latency_attribution_audit_v1.json"


def read(path: Path) -> dict[str, Any]:
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
            derived["deadline_miss_fraction"] == summary["deadline_miss_fraction"],
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
    online_protocol = read(ROOT / protocol["frozen_inputs"]["online_protocol"]["path"])
    strict_result = read(
        ROOT / online_protocol["frozen_inputs"]["strict_result"]["path"]
    )
    execution = strict_result["execution"]
    strict_rows = {row["memory_basis"]: row for row in strict_result["candidate_rows"]}
    source_rows = {row["basis"]: row for row in result["basis_rows"]}
    source_corpora = {row["basis"]: row for row in result["corpora"]}
    source_structures = {row["basis"]: row for row in result["structures"]}
    contract = online_protocol["window_contract"]
    corpus_contract = online_protocol["corpus_contract"]
    timed_shots = protocol["corpus_contract"]["timed_shots_per_basis"]
    threshold = protocol["timing_contract"][
        "threshold_microseconds_per_committed_layer"
    ]
    maximum_miss = protocol["timing_contract"]["maximum_deadline_miss_fraction"]
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
        model, windows, structure = online_audit.compile_audit_windows(
            dem,
            circuit.get_detector_coordinates(),
            contract["window_size_layers"],
            contract["stride_layers"],
            contract["time_coordinate_index"],
        )
        predictions, diagnostics = online_audit.decode_audit_corpus(
            model,
            windows,
            syndromes,
            True,
        )
        timed_predictions, timed_diagnostics = online_audit.decode_audit_corpus(
            model,
            windows,
            syndromes[:timed_shots],
            True,
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
        full_predictions = np.unpackbits(
            full_packed,
            axis=1,
            count=model.observable_count,
            bitorder="little",
        )
        direct_packed = np.packbits(predictions, axis=1, bitorder="little")
        timed_packed = np.packbits(timed_predictions, axis=1, bitorder="little")
        direct_exact = int(
            np.count_nonzero(np.all(predictions == full_predictions, axis=1))
        )
        sync_exact = int(
            np.count_nonzero(
                np.all(timed_predictions == full_predictions[:timed_shots], axis=1)
            )
        )
        reconstruction_rows.append(
            {
                "basis": basis,
                "source_chunks_replayed": corpus["chunk_matches"],
                "corpus_sha256": corpus["corpus_sha256"],
                "corpus_matches": corpus["corpus_sha256"]
                == source_corpora[basis]["corpus_sha256"],
                "structure_matches": structure
                == {
                    key: value
                    for key, value in source_structures[basis].items()
                    if key != "basis"
                },
                "direct_prediction_sha256": digest(
                    direct_packed.tobytes(order="C")
                ),
                "sync_timed_prediction_sha256": digest(
                    timed_packed.tobytes(order="C")
                ),
                "full_prediction_sha256": digest(full_packed.tobytes(order="C")),
                "direct_prediction_rows_equal_full_block": direct_exact,
                "sync_prediction_rows_equal_full_block": sync_exact,
                "timed_cross_path_prediction_rows_equal": int(
                    np.count_nonzero(
                        np.all(predictions[:timed_shots] == timed_predictions, axis=1)
                    )
                ),
                "direct_diagnostics": diagnostics,
                "sync_timed_diagnostics": timed_diagnostics,
                "matches_result": all(
                    [
                        digest(direct_packed.tobytes(order="C"))
                        == source["direct_prediction_sha256"],
                        digest(timed_packed.tobytes(order="C"))
                        == source["sync_timed_prediction_sha256"],
                        digest(full_packed.tobytes(order="C"))
                        == source["full_block_prediction_sha256"],
                        direct_exact
                        == source["direct_prediction_rows_equal_full_block"],
                        sync_exact
                        == source["sync_prediction_rows_equal_full_block"],
                        diagnostics["residual_nonzero_shots"]
                        == source["direct_residual_nonzero_shots"],
                        diagnostics["commit_residual_failure_shots"]
                        == source["direct_commit_residual_failure_shots"],
                        diagnostics["selected_components_total"]
                        == source["direct_selected_components_total"],
                        timed_diagnostics["residual_nonzero_shots"]
                        == source["sync_residual_nonzero_shots"],
                        timed_diagnostics["commit_residual_failure_shots"]
                        == source["sync_commit_residual_failure_shots"],
                        timed_diagnostics["selected_components_total"]
                        == source["sync_timed_selected_components_total"],
                    ]
                ),
            }
        )

        commit_layers = [window.commit_layers for window in windows]
        vectors: dict[str, list[int]] = {}
        derived: dict[str, Any] = {}
        for name, summary in [
            ("sync_end_to_end", source["timing"]["sync_end_to_end"]),
            ("direct_end_to_end", source["timing"]["direct_end_to_end"]),
        ]:
            vectors[name], derived[name] = decode_vector(
                summary, commit_layers, timed_shots, threshold
            )
        for phase, summary in source["timing"]["sync_phases"].items():
            name = f"sync::{phase}"
            vectors[name], derived[name] = decode_vector(
                summary, commit_layers, timed_shots, threshold
            )
        for phase, summary in source["timing"]["direct_phases"].items():
            name = f"direct::{phase}"
            vectors[name], derived[name] = decode_vector(
                summary, commit_layers, timed_shots, threshold
            )
        sync_additive = all(
            vectors["sync_end_to_end"][index]
            == sum(
                vectors[f"sync::{phase}"][index]
                for phase in source["timing"]["sync_phases"]
            )
            for index in range(len(vectors["sync_end_to_end"]))
        )
        direct_additive = all(
            vectors["direct_end_to_end"][index]
            == sum(
                vectors[f"direct::{phase}"][index]
                for phase in source["timing"]["direct_phases"]
            )
            for index in range(len(vectors["direct_end_to_end"]))
        )
        stage_passes = {
            "matching_kernel": passes(
                derived["direct::matching_kernel"], threshold, maximum_miss
            ),
            "direct_end_to_end": passes(
                derived["direct_end_to_end"], threshold, maximum_miss
            ),
            "sync_end_to_end": passes(
                derived["sync_end_to_end"], threshold, maximum_miss
            ),
        }
        timing_rows.append(
            {
                "basis": basis,
                "derived": derived,
                "all_vectors_match_result": all(
                    row["matches_result"] for row in derived.values()
                ),
                "phase_additivity": {
                    "sync": sync_additive,
                    "direct": direct_additive,
                },
                "stage_pass": stage_passes,
                "stage_pass_matches_result": stage_passes == source["stage_pass"],
            }
        )

    semantic_pass = all(
        row["matches_result"]
        and row["direct_prediction_rows_equal_full_block"] == 1024
        and row["sync_prediction_rows_equal_full_block"] == timed_shots
        and row["direct_diagnostics"]["residual_nonzero_shots"] == 0
        and row["direct_diagnostics"]["commit_residual_failure_shots"] == 0
        and row["sync_timed_diagnostics"]["residual_nonzero_shots"] == 0
        and row["sync_timed_diagnostics"]["commit_residual_failure_shots"] == 0
        for row in reconstruction_rows
    )
    matching_pass = all(row["stage_pass"]["matching_kernel"] for row in timing_rows)
    direct_pass = all(row["stage_pass"]["direct_end_to_end"] for row in timing_rows)
    sync_pass = all(row["stage_pass"]["sync_end_to_end"] for row in timing_rows)
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
    speedups = [
        row["derived"]["sync_end_to_end"][
            "p99_microseconds_per_committed_layer"
        ]
        / row["derived"]["direct_end_to_end"][
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
    evidence_view = {
        "public_freeze": result["public_freeze"],
        "classification": result["classification"],
        "reference_relative_score": result["reference_relative_score"],
        "verdict": result["verdict"],
        "timing_hashes": [
            {
                "basis": row["basis"],
                "sync": source_rows[row["basis"]]["timing"]["sync_end_to_end"][
                    "raw_nanoseconds_sha256"
                ],
                "direct": source_rows[row["basis"]]["timing"][
                    "direct_end_to_end"
                ]["raw_nanoseconds_sha256"],
                "matching": source_rows[row["basis"]]["timing"]["direct_phases"][
                    "matching_kernel"
                ]["raw_nanoseconds_sha256"],
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
    add("source_negative", read(ROOT / protocol["frozen_inputs"]["online_result"]["path"])["decision"] == protocol["frozen_inputs"]["online_result"]["required_decision"], "Online source decision matches.")
    add("source_chunks", sum(row["source_chunks_replayed"] for row in reconstruction_rows) == 8, "8/8 source chunks.")
    add("corpora", all(row["corpus_matches"] for row in reconstruction_rows), "Both corpus hashes match.")
    add("structures", all(row["structure_matches"] for row in reconstruction_rows), "Both window structures match.")
    add("predictions", all(row["matches_result"] for row in reconstruction_rows), "Direct and timed sync prediction hashes reproduce.")
    add("semantic_veto", semantic_pass == result["verdict"]["semantic_veto_pass"], f"semantic_veto_pass={semantic_pass}")
    add("raw_vectors", all(row["all_vectors_match_result"] for row in timing_rows), "All 22 timing vectors reproduce counts, hashes, sums, quantiles, and misses.")
    add("phase_additivity", all(row["phase_additivity"]["sync"] and row["phase_additivity"]["direct"] for row in timing_rows), "Every per-event phase sum equals its total.")
    add("stage_passes", all(row["stage_pass_matches_result"] for row in timing_rows), "All stage verdicts reproduce.")
    add("classification", classification == result["classification"], classification)
    add("relative_score", result["reference_relative_score"]["x_sync_to_direct_p99_speedup"] == speedups[0] and result["reference_relative_score"]["z_sync_to_direct_p99_speedup"] == speedups[1] and result["reference_relative_score"]["geometric_mean_sync_to_direct_p99_speedup"] == geometric_speedup and result["reference_relative_score"]["absolute_deadline_waived"] is False, f"geometric_speedup={geometric_speedup}")
    add("formal_checks", result["summary"]["checks_passed"] == 13 and result["summary"]["checks_failed"] == 0, "13/13 producer checks.")
    add("hard_boundaries", result["verdict"]["hardware_decoder_deadline_passed"] is False and result["verdict"]["full_b2_credit_ready"] is False and result["verdict"]["p023_scalable_memory_ready"] is False and result["verdict"]["b7_resource_credit"] == 0, "No downstream credit.")
    add("evidence_id", digest(compact(evidence_view)) == result["evidence_id"], result["evidence_id"])

    output: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_latency_attribution_audit_v1",
        "as_of_date": protocol["as_of_date"],
        "scope": protocol["scope"],
        "source_result": {
            "path": str(result_path.resolve().relative_to(ROOT)),
            "sha256": file_digest(result_path),
        },
        "auditor": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": file_digest(Path(__file__).resolve()),
            "imports_attribution_producer": False,
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
            "matching_kernel_tail_pass": matching_pass,
            "direct_path_tail_pass": direct_pass,
            "sync_path_tail_pass": sync_pass,
            "classification": classification,
            "x_sync_to_direct_p99_speedup": speedups[0] if semantic_pass else None,
            "z_sync_to_direct_p99_speedup": speedups[1] if semantic_pass else None,
            "geometric_mean_sync_to_direct_p99_speedup": geometric_speedup,
        },
        "checks": checks,
        "summary": {
            "checks_passed": sum(item["passed"] for item in checks),
            "checks_failed": sum(not item["passed"] for item in checks),
            "source_chunks_replayed": 8,
            "direct_prediction_rows_replayed": 2048,
            "sync_timed_prediction_rows_replayed": 256,
            "raw_timing_vectors_replayed": 22,
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
