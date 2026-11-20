#!/usr/bin/env python3
"""Run the publicly preregistered distance-6 decoder latency matrix."""

from __future__ import annotations

import argparse
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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_decoder_latency_matrix_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_decoder_latency_matrix_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_decoder_latency_matrix_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_d6_decoder_latency_matrix_discussion_v1.md"


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


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def decode_corpus(
    matching: pymatching.Matching,
    detectors: np.ndarray,
    batch_size: int,
    enable_correlations: bool,
) -> np.ndarray:
    pieces: list[np.ndarray] = []
    for offset in range(0, len(detectors), batch_size):
        pieces.append(
            matching.decode_batch(
                detectors[offset : offset + batch_size],
                bit_packed_shots=True,
                bit_packed_predictions=True,
                enable_correlations=enable_correlations,
            )
        )
    return np.concatenate(pieces, axis=0)


def build_corpus(
    basis: str,
    execution: dict[str, Any],
    strict_row: dict[str, Any],
    corpus_contract: dict[str, Any],
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, pymatching.Matching, pymatching.Matching]:
    circuit = strict_base.build_circuit(basis, execution)
    dem = circuit.detector_error_model(decompose_errors=True)
    independent = pymatching.Matching.from_detector_error_model(dem)
    correlated = pymatching.Matching.from_detector_error_model(
        dem,
        enable_correlations=True,
    )
    sampler = circuit.compile_detector_sampler(seed=strict_row["seed"])
    detector_parts: list[np.ndarray] = []
    observable_parts: list[np.ndarray] = []
    replayed_chunks: list[dict[str, Any]] = []
    chunk_size = corpus_contract["source_chunk_size"]
    source_chunks = strict_row["chunk_digests"][: corpus_contract["source_chunks_per_basis"]]
    for chunk_index, source in enumerate(source_chunks):
        detectors, observables = sampler.sample(
            chunk_size,
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
        replayed = sha_bytes(payload)
        if replayed != source["sha256"]:
            raise ValueError(f"source chunk replay mismatch for {basis} chunk {chunk_index}")
        detector_parts.append(detectors)
        observable_parts.append(observables)
        replayed_chunks.append(
            {
                "chunk_index": chunk_index,
                "source_sha256": source["sha256"],
                "replayed_sha256": replayed,
                "matches": True,
            }
        )
    detectors = np.concatenate(detector_parts, axis=0)
    observables = np.concatenate(observable_parts, axis=0)
    if len(detectors) != corpus_contract["shots_per_basis"]:
        raise ValueError("corpus shot count mismatch")
    correlated_predictions = decode_corpus(correlated, detectors, 256, True)
    independent_predictions = decode_corpus(independent, detectors, 256, False)
    corpus_header = {
        "basis": basis,
        "shots": len(detectors),
        "detector_shape": list(detectors.shape),
        "observable_shape": list(observables.shape),
        "seed": strict_row["seed"],
    }
    corpus_hash = sha_bytes(
        compact(corpus_header)
        + b"\x00"
        + detectors.tobytes(order="C")
        + observables.tobytes(order="C")
    )
    correlated_failures = int(
        np.count_nonzero(
            np.any(np.bitwise_xor(correlated_predictions, observables) != 0, axis=1)
        )
    )
    independent_failures = int(
        np.count_nonzero(
            np.any(np.bitwise_xor(independent_predictions, observables) != 0, axis=1)
        )
    )
    row = {
        **corpus_header,
        "corpus_sha256": corpus_hash,
        "raw_circuit_sha256": sha_bytes(str(circuit).encode()),
        "detector_error_model_sha256": sha_bytes(str(dem).encode()),
        "source_chunk_replay": replayed_chunks,
        "independent_prediction_sha256": sha_bytes(independent_predictions.tobytes(order="C")),
        "correlated_prediction_sha256": sha_bytes(correlated_predictions.tobytes(order="C")),
        "independent_prefix_failures": independent_failures,
        "correlated_prefix_failures": correlated_failures,
        "matching_dimensions": {
            "independent_nodes": independent.num_nodes,
            "independent_edges": independent.num_edges,
            "correlated_nodes": correlated.num_nodes,
            "correlated_edges": correlated.num_edges,
        },
    }
    return row, detectors, observables, independent, correlated


def metric_row(
    basis: str,
    decoder: str,
    batch_size: int,
    raw_ns: list[int],
    shots: int,
    rounds: int,
    prediction_sha256: str,
) -> dict[str, Any]:
    median_ns = float(statistics.median(raw_ns))
    median_seconds = median_ns * 1e-9
    return {
        "memory_basis": basis,
        "decoder": decoder,
        "batch_size": batch_size,
        "timed_repetitions": len(raw_ns),
        "raw_total_decode_nanoseconds": raw_ns,
        "min_total_decode_seconds": min(raw_ns) * 1e-9,
        "median_total_decode_seconds": median_seconds,
        "max_total_decode_seconds": max(raw_ns) * 1e-9,
        "median_seconds_per_shot": median_seconds / shots,
        "median_microseconds_per_round": median_seconds * 1e6 / (shots * rounds),
        "median_memory_rounds_per_second": shots * rounds / median_seconds,
        "prediction_sha256": prediction_sha256,
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
        commit_bindings[name] = {"path": binding["path"], "sha256": commit_sha, "matches": True}

    runner_path = str(Path(__file__).resolve().relative_to(ROOT))
    protocol_rel = str(protocol_path.resolve().relative_to(ROOT))
    freeze_protocol_sha = sha_bytes(git_blob(public_freeze_commit, protocol_rel))
    freeze_runner_sha = sha_bytes(git_blob(public_freeze_commit, runner_path))
    if freeze_protocol_sha != sha_path(protocol_path):
        raise ValueError("protocol differs from public freeze")
    if freeze_runner_sha != sha_path(Path(__file__).resolve()):
        raise ValueError("runner differs from public freeze")

    strict_result = read(ROOT / protocol["frozen_inputs"]["strict_result"]["path"])
    if strict_result["decision"] != protocol["frozen_inputs"]["strict_result"]["required_decision"]:
        raise ValueError("strict source decision mismatch")
    strict_rows = {row["memory_basis"]: row for row in strict_result["candidate_rows"]}
    execution = strict_result["execution"]
    corpus_contract = protocol["corpus_contract"]
    corpora: list[dict[str, Any]] = []
    runtime: dict[str, tuple[np.ndarray, pymatching.Matching, pymatching.Matching]] = {}
    for basis in execution["memory_bases"]:
        corpus, detectors, _observables, independent, correlated = build_corpus(
            basis,
            execution,
            strict_rows[basis],
            corpus_contract,
        )
        corpora.append(corpus)
        runtime[basis] = (detectors, independent, correlated)

    matrix = protocol["matrix_contract"]
    configs = [
        (basis, decoder, batch_size)
        for basis in execution["memory_bases"]
        for decoder in matrix["decoders"]
        for batch_size in matrix["batch_sizes"]
    ]
    canonical_hashes: dict[tuple[str, str], str] = {}
    corpus_by_basis = {row["basis"]: row for row in corpora}
    for basis in execution["memory_bases"]:
        canonical_hashes[(basis, "independent_mwpm")] = corpus_by_basis[basis][
            "independent_prediction_sha256"
        ]
        canonical_hashes[(basis, "two_pass_correlated_matching")] = corpus_by_basis[basis][
            "correlated_prediction_sha256"
        ]

    for basis, decoder, batch_size in configs:
        detectors, independent, correlated = runtime[basis]
        matching = correlated if decoder == "two_pass_correlated_matching" else independent
        prediction = decode_corpus(
            matching,
            detectors,
            batch_size,
            decoder == "two_pass_correlated_matching",
        )
        if sha_bytes(prediction.tobytes(order="C")) != canonical_hashes[(basis, decoder)]:
            raise ValueError("warmup prediction mismatch")

    raw_times: dict[tuple[str, str, int], list[int]] = {config: [] for config in configs}
    for repetition in range(matrix["timed_repetitions"]):
        shift = repetition % len(configs)
        order = configs[shift:] + configs[:shift]
        if repetition % 2:
            order = list(reversed(order))
        for basis, decoder, batch_size in order:
            detectors, independent, correlated = runtime[basis]
            matching = correlated if decoder == "two_pass_correlated_matching" else independent
            tick = time.perf_counter_ns()
            prediction = decode_corpus(
                matching,
                detectors,
                batch_size,
                decoder == "two_pass_correlated_matching",
            )
            elapsed = time.perf_counter_ns() - tick
            if sha_bytes(prediction.tobytes(order="C")) != canonical_hashes[(basis, decoder)]:
                raise ValueError("timed prediction mismatch")
            raw_times[(basis, decoder, batch_size)].append(elapsed)

    measurements = [
        metric_row(
            basis,
            decoder,
            batch_size,
            raw_times[(basis, decoder, batch_size)],
            corpus_contract["shots_per_basis"],
            corpus_contract["rounds_per_shot"],
            canonical_hashes[(basis, decoder)],
        )
        for basis, decoder, batch_size in configs
    ]
    indexed = {
        (row["memory_basis"], row["decoder"], row["batch_size"]): row
        for row in measurements
    }
    for basis in execution["memory_bases"]:
        for batch_size in matrix["batch_sizes"]:
            independent = indexed[(basis, "independent_mwpm", batch_size)]
            correlated = indexed[(basis, "two_pass_correlated_matching", batch_size)]
            correlated["correlated_to_independent_median_ratio"] = (
                correlated["median_total_decode_seconds"]
                / independent["median_total_decode_seconds"]
            )
    threshold = protocol["software_backlog_proxy"]["threshold_microseconds_per_round"]
    primary_rows = [
        indexed[(basis, "two_pass_correlated_matching", 1)]
        for basis in execution["memory_bases"]
    ]
    batch256_rows = [
        indexed[(basis, "two_pass_correlated_matching", 256)]
        for basis in execution["memory_bases"]
    ]
    software_proxy_pass = all(
        row["median_microseconds_per_round"] <= threshold for row in primary_rows
    )
    batch256_proxy_pass = all(
        row["median_microseconds_per_round"] <= threshold for row in batch256_rows
    )
    decision = (
        "d6_correlated_decoder_batch1_software_backlog_proxy_pass_hardware_deadline_b2_p023_b7_open"
        if software_proxy_pass
        else "d6_correlated_decoder_batch1_software_backlog_proxy_fail_hardware_deadline_b2_p023_b7_open"
    )
    result: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_decoder_latency_matrix_result_v1",
        "as_of_date": protocol["as_of_date"],
        "question": protocol["question"],
        "scope": protocol["scope"],
        "public_freeze": {
            "commit": public_freeze_commit,
            "discussion_number": discussion_number,
            "discussion_url": f"https://github.com/crystal-tensor/Prometheus-plan/discussions/{discussion_number}",
            "protocol_sha256": freeze_protocol_sha,
            "runner_sha256": freeze_runner_sha,
        },
        "protocol_binding": {"path": protocol_rel, "sha256": sha_path(protocol_path)},
        "frozen_inputs_current": current_bindings,
        "frozen_inputs_at_commit": {"commit": artifact_commit, "bindings": commit_bindings},
        "generator": {"path": runner_path, "sha256": sha_path(Path(__file__).resolve())},
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
        "matrix_contract": matrix,
        "software_backlog_proxy": protocol["software_backlog_proxy"],
        "external_basis": protocol["external_basis"],
        "corpora": corpora,
        "measurements": measurements,
        "verdict": {
            "software_batch1_backlog_proxy_pass": software_proxy_pass,
            "software_batch256_throughput_proxy_pass": batch256_proxy_pass,
            "threshold_microseconds_per_round": threshold,
            "physical_memory_gate_passed": True,
            "hardware_decoder_deadline_passed": False,
            "full_b2_credit_ready": False,
            "p023_scalable_memory_ready": False,
            "b7_resource_credit": 0,
        },
        "hard_boundaries": protocol["hard_boundaries"],
        "decision": decision,
        "next_gate": "Implement and time an online O(d) sliding-window decoder with communication, control, feedback, and tail latency before any hardware deadline, full B2, #023, or B7 claim.",
    }
    checks: list[dict[str, Any]] = []
    checks.append(check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact QEC scope."))
    checks.append(check("public_freeze", freeze_protocol_sha == sha_path(protocol_path) and freeze_runner_sha == sha_path(Path(__file__).resolve()), public_freeze_commit))
    checks.append(check("discussion", discussion_number > 0, result["public_freeze"]["discussion_url"]))
    checks.append(check("frozen_inputs", len(current_bindings) == 5 and all(item["matches"] for item in commit_bindings.values()), artifact_commit))
    checks.append(check("strict_source", strict_result["summary"]["physical_memory_gate_passed"] and strict_result["summary"]["checks_failed"] == 0, strict_result["decision"]))
    checks.append(check("corpus_count", len(corpora) == 2 and all(row["shots"] == 1024 for row in corpora), "Two 1,024-shot corpora."))
    checks.append(check("source_chunks", all(len(row["source_chunk_replay"]) == 4 and all(chunk["matches"] for chunk in row["source_chunk_replay"]) for row in corpora), "Eight source chunks replay."))
    checks.append(check("matrix_rows", len(measurements) == 20, "2 bases x 2 decoders x 5 batch sizes."))
    checks.append(check("repetitions", all(row["timed_repetitions"] == 9 and len(row["raw_total_decode_nanoseconds"]) == 9 for row in measurements), "Nine timings per row."))
    checks.append(check("positive_timing", all(row["min_total_decode_seconds"] > 0 and row["min_total_decode_seconds"] <= row["median_total_decode_seconds"] <= row["max_total_decode_seconds"] for row in measurements), "Positive ordered timing statistics."))
    checks.append(check("prediction_hashes", all(len(row["prediction_sha256"]) == 64 for row in measurements), "All prediction hashes present."))
    checks.append(check("proxy_rule", software_proxy_pass == all(row["median_microseconds_per_round"] <= threshold for row in primary_rows), str({row["memory_basis"]: row["median_microseconds_per_round"] for row in primary_rows})))
    checks.append(check("hardware_boundary", not result["verdict"]["hardware_decoder_deadline_passed"] and not result["verdict"]["full_b2_credit_ready"] and not result["verdict"]["p023_scalable_memory_ready"] and result["verdict"]["b7_resource_credit"] == 0, "Hardware/full-credit gates remain closed."))
    result["formal_checks"] = checks
    result["summary"] = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "corpus_shots_total": sum(row["shots"] for row in corpora),
        "matrix_rows": len(measurements),
        "timed_repetitions_total": sum(row["timed_repetitions"] for row in measurements),
        "software_batch1_backlog_proxy_pass": software_proxy_pass,
        "software_batch256_throughput_proxy_pass": batch256_proxy_pass,
        "hardware_decoder_deadline_passed": False,
        "full_b2_credit_ready": False,
        "p023_scalable_memory_ready": False,
        "b7_resource_credit": 0,
    }
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
    result["deterministic_id"] = sha_bytes(compact(deterministic_payload))
    result["timing_evidence_id"] = sha_bytes(
        compact({key: value for key, value in result.items() if key != "timing_evidence_id"})
    )
    if result["summary"]["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"formal checks failed: {failed}")
    return result


def build_report(result: dict[str, Any]) -> str:
    verdict = result["verdict"]
    rows = sorted(
        result["measurements"],
        key=lambda row: (row["memory_basis"], row["decoder"], row["batch_size"]),
    )
    return "\n".join(
        [
            "# B2/B7/#023 Distance-6 Decoder Latency Matrix v1",
            "",
            f"As of {result['as_of_date']}. Scope is exactly #021/B7, #022/B2, and #023.",
            "",
            "## Heuristic question",
            "",
            "Does a correlation-aware decoder still keep pace when the 256-shot batch advantage is removed?",
            "",
            f"Public freeze: `{result['public_freeze']['commit']}` and Discussion #{result['public_freeze']['discussion_number']}.",
            "",
            "| basis | decoder | batch | median s | median us/round | memory-rounds/s | correlated / independent |",
            "|---|---|---:|---:|---:|---:|---:|",
            *[
                f"| {row['memory_basis'].upper()} | {row['decoder']} | {row['batch_size']} | {row['median_total_decode_seconds']:.6f} | {row['median_microseconds_per_round']:.6f} | {row['median_memory_rounds_per_second']:.0f} | {row.get('correlated_to_independent_median_ratio', 1.0):.3f}x |"
                for row in rows
            ],
            "",
            f"Batch-1 software backlog proxy pass: **{verdict['software_batch1_backlog_proxy_pass']}**. Batch-256 throughput proxy pass: **{verdict['software_batch256_throughput_proxy_pass']}**. The declared line is 1 microsecond per syndrome round.",
            "",
            "## Boundary",
            "",
            "This is an offline host-local block-decoding proxy. It excludes communication, control, feedback, online O(d) windowing, and tail response time. Hardware decoder deadline passed remains **False**; full B2, #023, and B7 remain closed.",
            "",
            f"Formal checks: **{result['summary']['checks_passed']}/{result['summary']['checks_total']}**. Deterministic ID: `{result['deterministic_id']}`. Timing evidence ID: `{result['timing_evidence_id']}`.",
            "",
            "## Next gate",
            "",
            result["next_gate"],
            "",
        ]
    )


def build_discussion(result: dict[str, Any]) -> str:
    rows = {
        (row["memory_basis"], row["decoder"], row["batch_size"]): row
        for row in result["measurements"]
    }
    passed = result["verdict"]["software_batch1_backlog_proxy_pass"]
    return "\n".join(
        [
            "Does 4x slower still count as real time when the machine gives you 1 microsecond per round?",
            "",
            f"The preregistered batch-size matrix is complete. The correlation-aware distance-6 decoder's batch-1 software backlog proxy is **{passed}** under the declared 1 microsecond/round line.",
            "",
            f"At batch 1, X uses {rows[('x', 'two_pass_correlated_matching', 1)]['median_microseconds_per_round']:.6f} us/round and Z uses {rows[('z', 'two_pass_correlated_matching', 1)]['median_microseconds_per_round']:.6f} us/round. At batch 256, they use {rows[('x', 'two_pass_correlated_matching', 256)]['median_microseconds_per_round']:.6f} and {rows[('z', 'two_pass_correlated_matching', 256)]['median_microseconds_per_round']:.6f} us/round.",
            "",
            "The physical result is unchanged: 71 active qubits passed both strict correctness gates for a 1.3662x physical-memory score. But this matrix is still offline and excludes the communication/control path, so hardware deadline, full B2, #023, and B7 remain open.",
            "",
            "Questions for critique:",
            "",
            "- Is 1 microsecond per round the right platform-neutral backlog line, or should each hardware family declare its own cycle budget?",
            "- Should the physical-qubit saving and classical decoder cost remain a Pareto pair instead of being collapsed into one arbitrary scalar?",
            "- Is batch-1 full-block decoding informative enough, or must only online O(d) sliding-window latency count?",
            "- What tail-latency percentile and communication/control budget should be mandatory before calling a decoder real time?",
            "",
            "Current boundary: software proxy only; hardware deadline=false; full B2=false; #023=false; B7 credit=0.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--public-freeze-commit", required=True)
    parser.add_argument("--discussion-number", type=int, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_result(
        read(args.protocol),
        args.protocol,
        args.public_freeze_commit,
        args.discussion_number,
    )
    args.output.write_text(canonical(result), encoding="utf-8")
    args.report.write_text(build_report(result), encoding="utf-8")
    args.discussion.write_text(build_discussion(result), encoding="utf-8")
    print(canonical(result["summary"]).strip())


if __name__ == "__main__":
    main()
