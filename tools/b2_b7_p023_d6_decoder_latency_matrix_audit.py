#!/usr/bin/env python3
"""Independent audit for the distance-6 decoder latency matrix."""

from __future__ import annotations

import argparse
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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_decoder_latency_matrix_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_decoder_latency_matrix_v1.json"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_decoder_latency_matrix_audit_v1.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def decode(
    matching: pymatching.Matching,
    detectors: np.ndarray,
    batch_size: int,
    correlated: bool,
) -> np.ndarray:
    values: list[np.ndarray] = []
    for offset in range(0, len(detectors), batch_size):
        values.append(
            matching.decode_batch(
                detectors[offset : offset + batch_size],
                bit_packed_shots=True,
                bit_packed_predictions=True,
                enable_correlations=correlated,
            )
        )
    return np.concatenate(values, axis=0)


def reconstruct(
    protocol: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    strict_result = load(ROOT / protocol["frozen_inputs"]["strict_result"]["path"])
    strict_rows = {row["memory_basis"]: row for row in strict_result["candidate_rows"]}
    result_corpora = {row["basis"]: row for row in result["corpora"]}
    execution = strict_result["execution"]
    contract = protocol["corpus_contract"]
    reconstructed_corpora: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    for basis in execution["memory_bases"]:
        source = strict_rows[basis]
        circuit = strict_base.build_circuit(basis, execution)
        dem = circuit.detector_error_model(decompose_errors=True)
        independent = pymatching.Matching.from_detector_error_model(dem)
        correlated = pymatching.Matching.from_detector_error_model(
            dem,
            enable_correlations=True,
        )
        sampler = circuit.compile_detector_sampler(seed=source["seed"])
        detector_parts: list[np.ndarray] = []
        observable_parts: list[np.ndarray] = []
        chunk_hashes: list[str] = []
        for chunk_index in range(contract["source_chunks_per_basis"]):
            detectors, observables = sampler.sample(
                contract["source_chunk_size"],
                separate_observables=True,
                bit_packed=True,
            )
            predictions = correlated.decode_batch(
                detectors,
                bit_packed_shots=True,
                bit_packed_predictions=True,
                enable_correlations=True,
            )
            header = {
                "basis": basis,
                "chunk_index": chunk_index,
                "shot_offset": chunk_index * contract["source_chunk_size"],
                "shots": contract["source_chunk_size"],
                "detector_shape": list(detectors.shape),
                "observable_shape": list(observables.shape),
                "prediction_shape": list(predictions.shape),
            }
            payload = (
                stable(header)
                + b"\x00"
                + detectors.tobytes(order="C")
                + observables.tobytes(order="C")
                + predictions.tobytes(order="C")
            )
            chunk_hashes.append(sha(payload))
            detector_parts.append(detectors)
            observable_parts.append(observables)
        detectors = np.concatenate(detector_parts, axis=0)
        observables = np.concatenate(observable_parts, axis=0)
        corpus_header = {
            "basis": basis,
            "shots": len(detectors),
            "detector_shape": list(detectors.shape),
            "observable_shape": list(observables.shape),
            "seed": source["seed"],
        }
        corpus_hash = sha(
            stable(corpus_header)
            + b"\x00"
            + detectors.tobytes(order="C")
            + observables.tobytes(order="C")
        )
        canonical: dict[str, np.ndarray] = {
            "independent_mwpm": decode(independent, detectors, 256, False),
            "two_pass_correlated_matching": decode(correlated, detectors, 256, True),
        }
        failures = {
            name: int(
                np.count_nonzero(
                    np.any(np.bitwise_xor(prediction, observables) != 0, axis=1)
                )
            )
            for name, prediction in canonical.items()
        }
        for decoder_name in protocol["matrix_contract"]["decoders"]:
            matching = correlated if decoder_name == "two_pass_correlated_matching" else independent
            correlation_flag = decoder_name == "two_pass_correlated_matching"
            expected_hash = sha(canonical[decoder_name].tobytes(order="C"))
            for batch_size in protocol["matrix_contract"]["batch_sizes"]:
                prediction = decode(
                    matching,
                    detectors,
                    batch_size,
                    correlation_flag,
                )
                prediction_rows.append(
                    {
                        "memory_basis": basis,
                        "decoder": decoder_name,
                        "batch_size": batch_size,
                        "prediction_sha256": sha(prediction.tobytes(order="C")),
                        "matches_canonical": sha(prediction.tobytes(order="C")) == expected_hash,
                    }
                )
        reconstructed_corpora.append(
            {
                "basis": basis,
                "corpus_sha256": corpus_hash,
                "source_chunk_sha256": chunk_hashes,
                "independent_prediction_sha256": sha(canonical["independent_mwpm"].tobytes(order="C")),
                "correlated_prediction_sha256": sha(canonical["two_pass_correlated_matching"].tobytes(order="C")),
                "independent_prefix_failures": failures["independent_mwpm"],
                "correlated_prefix_failures": failures["two_pass_correlated_matching"],
                "matches_result": (
                    corpus_hash == result_corpora[basis]["corpus_sha256"]
                    and chunk_hashes
                    == [row["replayed_sha256"] for row in result_corpora[basis]["source_chunk_replay"]]
                    and failures["independent_mwpm"] == result_corpora[basis]["independent_prefix_failures"]
                    and failures["two_pass_correlated_matching"] == result_corpora[basis]["correlated_prefix_failures"]
                ),
            }
        )
    return {"corpora": reconstructed_corpora, "prediction_rows": prediction_rows}


def audit(protocol_path: Path, result_path: Path) -> dict[str, Any]:
    protocol = load(protocol_path)
    result = load(result_path)
    freeze = result["public_freeze"]
    reconstructed = reconstruct(protocol, result)
    measurements = result["measurements"]
    indexed_predictions = {
        (row["memory_basis"], row["decoder"], row["batch_size"]): row
        for row in reconstructed["prediction_rows"]
    }
    metric_checks: list[bool] = []
    for row in measurements:
        raw = row["raw_total_decode_nanoseconds"]
        median_ns = float(statistics.median(raw))
        median_seconds = median_ns * 1e-9
        shots = protocol["corpus_contract"]["shots_per_basis"]
        rounds = protocol["corpus_contract"]["rounds_per_shot"]
        metric_checks.append(
            len(raw) == protocol["matrix_contract"]["timed_repetitions"]
            and math.isclose(row["min_total_decode_seconds"], min(raw) * 1e-9, rel_tol=0, abs_tol=1e-15)
            and math.isclose(row["median_total_decode_seconds"], median_seconds, rel_tol=0, abs_tol=1e-15)
            and math.isclose(row["max_total_decode_seconds"], max(raw) * 1e-9, rel_tol=0, abs_tol=1e-15)
            and math.isclose(row["median_seconds_per_shot"], median_seconds / shots, rel_tol=0, abs_tol=1e-18)
            and math.isclose(row["median_microseconds_per_round"], median_seconds * 1e6 / (shots * rounds), rel_tol=0, abs_tol=1e-15)
            and row["prediction_sha256"]
            == indexed_predictions[(row["memory_basis"], row["decoder"], row["batch_size"])]["prediction_sha256"]
        )

    measurement_index = {
        (row["memory_basis"], row["decoder"], row["batch_size"]): row
        for row in measurements
    }
    threshold = protocol["software_backlog_proxy"]["threshold_microseconds_per_round"]
    expected_proxy = all(
        measurement_index[(basis, "two_pass_correlated_matching", 1)]["median_microseconds_per_round"] <= threshold
        for basis in ["x", "z"]
    )
    expected_batch256 = all(
        measurement_index[(basis, "two_pass_correlated_matching", 256)]["median_microseconds_per_round"] <= threshold
        for basis in ["x", "z"]
    )
    expected_decision = (
        "d6_correlated_decoder_batch1_software_backlog_proxy_pass_hardware_deadline_b2_p023_b7_open"
        if expected_proxy
        else "d6_correlated_decoder_batch1_software_backlog_proxy_fail_hardware_deadline_b2_p023_b7_open"
    )
    input_hashes: dict[str, dict[str, str]] = {}
    artifact_commit = protocol["frozen_inputs"]["artifact_commit"]
    for name, binding in protocol["frozen_inputs"].items():
        if name == "artifact_commit":
            continue
        input_hashes[name] = {
            "current": file_sha(ROOT / binding["path"]),
            "commit": sha(git_blob(artifact_commit, binding["path"])),
            "expected": binding["sha256"],
        }
    runner_at_freeze = sha(git_blob(freeze["commit"], result["generator"]["path"]))
    protocol_at_freeze = sha(git_blob(freeze["commit"], result["protocol_binding"]["path"]))
    deterministic_payload = {
        "public_freeze": result["public_freeze"],
        "protocol_binding": result["protocol_binding"],
        "frozen_inputs_current": result["frozen_inputs_current"],
        "corpora": result["corpora"],
        "prediction_hashes": [
            {
                "basis": row["memory_basis"],
                "decoder": row["decoder"],
                "batch_size": row["batch_size"],
                "prediction_sha256": row["prediction_sha256"],
            }
            for row in measurements
        ],
    }
    expected_deterministic_id = sha(stable(deterministic_payload))
    expected_timing_id = sha(
        stable({key: value for key, value in result.items() if key != "timing_evidence_id"})
    )
    versions = {
        "python": platform.python_version(),
        "stim": stim.__version__,
        "pymatching": pymatching.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "system": platform.system(),
        "machine": platform.machine(),
    }
    checks: list[dict[str, Any]] = []
    checks.append(check("schema", result["schema_version"] == "b2_b7_p023_d6_decoder_latency_matrix_result_v1", result["schema_version"]))
    checks.append(check("scope", result["scope"] == protocol["scope"] and result["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact scope."))
    checks.append(check("protocol_hash", result["protocol_binding"]["sha256"] == file_sha(protocol_path) == protocol_at_freeze, protocol_at_freeze))
    checks.append(check("runner_hash", result["generator"]["sha256"] == file_sha(ROOT / result["generator"]["path"]) == runner_at_freeze, runner_at_freeze))
    checks.append(check("input_hashes", all(item["current"] == item["commit"] == item["expected"] for item in input_hashes.values()), artifact_commit))
    checks.append(check("environment", result["execution_environment"] == versions, str(versions)))
    checks.append(check("corpora", len(reconstructed["corpora"]) == 2 and all(row["matches_result"] for row in reconstructed["corpora"]), "Both corpora and eight chunks reproduce."))
    checks.append(check("prediction_matrix", len(reconstructed["prediction_rows"]) == 20 and all(row["matches_canonical"] for row in reconstructed["prediction_rows"]), "All 20 prediction rows reproduce."))
    checks.append(check("metric_arithmetic", len(metric_checks) == 20 and all(metric_checks), "All timing summaries recompute from raw nanoseconds."))
    checks.append(check("proxy", result["verdict"]["software_batch1_backlog_proxy_pass"] == expected_proxy and result["verdict"]["software_batch256_throughput_proxy_pass"] == expected_batch256, str({"batch1": expected_proxy, "batch256": expected_batch256})))
    checks.append(check("decision", result["decision"] == expected_decision, expected_decision))
    checks.append(check("hard_boundary", not result["verdict"]["hardware_decoder_deadline_passed"] and not result["verdict"]["full_b2_credit_ready"] and not result["verdict"]["p023_scalable_memory_ready"] and result["verdict"]["b7_resource_credit"] == 0, "Hardware/full-credit gates remain closed."))
    checks.append(check("deterministic_id", result["deterministic_id"] == expected_deterministic_id, expected_deterministic_id))
    checks.append(check("timing_evidence_id", result["timing_evidence_id"] == expected_timing_id, expected_timing_id))
    checks.append(check("producer_checks", result["summary"]["checks_failed"] == 0 and all(item["passed"] for item in result["formal_checks"]), f"{result['summary']['checks_passed']}/{result['summary']['checks_total']}"))
    summary = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "exact_source_chunks": 8 if all(row["matches_result"] for row in reconstructed["corpora"]) else 0,
        "exact_prediction_rows": sum(row["matches_canonical"] for row in reconstructed["prediction_rows"]),
        "software_batch1_backlog_proxy_pass": expected_proxy,
        "hardware_decoder_deadline_passed": False,
    }
    output = {
        "schema_version": "b2_b7_p023_d6_decoder_latency_matrix_independent_audit_v1",
        "source_result": {"path": str(result_path.relative_to(ROOT)), "sha256": file_sha(result_path)},
        "auditor": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": file_sha(Path(__file__).resolve())},
        "input_hashes": input_hashes,
        "reconstructed": reconstructed,
        "checks": checks,
        "summary": summary,
    }
    if summary["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"latency audit failed: {failed}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = audit(args.protocol, args.result)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
