#!/usr/bin/env python3
"""Reconstruct accepted X/Z per-window dynamic-weight batches for RTL replay.

This reopens only the already accepted public corpus from its frozen seeds.  It
does not draw a new holdout and does not execute or time RTL.  The full trace is
bound by a streaming digest; representative count-boundary batches are kept in
the compact result for the next simulation gate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import b2_b7_p023_d6_explicit_reweight_v2 as accepted  # noqa: E402


DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_microblossom_batch_trace_v1.json"
IMAGE_MANIFEST = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_images_v1.json"


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def phase_for(window_index: int) -> str:
    if window_index == 0:
        return "opening"
    if window_index == 163:
        return "closing"
    if 1 <= window_index <= 162:
        return "steady"
    raise ValueError(f"unexpected window index {window_index}")


def replacement_batch(
    window: accepted.ExplicitWindow, syndrome: np.ndarray
) -> tuple[list[int], list[list[int]]]:
    index_by_key = {edge.key: index for index, edge in enumerate(window.edges)}
    selected_keys = accepted.selected_edge_keys(window.base_candidate, syndrome)
    replacements: dict[tuple[int, int], int] = {}
    for source in selected_keys:
        for target, half_weight in window.rules.get(source, ()):
            current = replacements.get(target, window.base_half_weights[target])
            if half_weight < current:
                replacements[target] = half_weight
    selected = sorted(index_by_key[key] for key in selected_keys)
    updates = [
        [index_by_key[target], half_weight]
        for target, half_weight in sorted(replacements.items())
    ]
    if len({edge_index for edge_index, _ in updates}) != len(updates):
        raise ValueError("duplicate target edge in replacement batch")
    return selected, updates


def digest_bits(bits: np.ndarray) -> str:
    packed = np.packbits(np.asarray(bits, dtype=np.uint8), bitorder="little")
    return sha_bytes(packed.tobytes())


def reconstruct_basis(
    basis: str,
    corpus: dict[str, Any],
    accepted_row: dict[str, Any],
    manifest_rows: dict[tuple[str, str], dict[str, Any]],
    scale: int,
) -> dict[str, Any]:
    circuit, compiled, windows, structural = accepted.compile_basis(basis, scale)
    if len(windows) != 164:
        raise ValueError("window cardinality changed")
    sampler = circuit.compile_detector_sampler(seed=int(corpus["seed"]))
    detectors_packed, observables_packed = sampler.sample(
        int(corpus["shots"]), separate_observables=True, bit_packed=True
    )
    header = {
        "basis": basis,
        "shots": int(corpus["shots"]),
        "seed": int(corpus["seed"]),
        "seed_digest_sha256": corpus["seed_digest_sha256"],
        "detector_shape": list(detectors_packed.shape),
        "observable_shape": list(observables_packed.shape),
    }
    corpus_sha = sha_bytes(
        compact(header)
        + b"\x00"
        + detectors_packed.tobytes(order="C")
        + observables_packed.tobytes(order="C")
    )
    if corpus_sha != corpus["corpus_sha256"]:
        raise ValueError(f"{basis}: accepted corpus hash changed")
    raw_syndromes = np.unpackbits(
        detectors_packed,
        axis=1,
        count=circuit.num_detectors,
        bitorder="little",
    ).astype(np.uint8, copy=False)
    final_predictions = np.zeros((len(raw_syndromes), circuit.num_observables), dtype=np.uint8)
    trace_digest = hashlib.sha256()
    batch_hash_counts: Counter[str] = Counter()
    update_counts: list[int] = []
    selected_counts: list[int] = []
    phase_update_counts: dict[str, list[int]] = defaultdict(list)
    first_batch_by_count: dict[int, dict[str, Any]] = {}
    total_update_writes = 0
    commit_failures = 0
    final_residual_failures = 0
    for shot_index, raw in enumerate(raw_syndromes):
        received = np.zeros(compiled.model.num_detectors, dtype=np.uint8)
        correction = np.zeros(compiled.model.num_detectors, dtype=np.uint8)
        frame = np.zeros(compiled.model.num_observables, dtype=np.uint8)
        received[compiled.prebuffer_detectors] = raw[compiled.prebuffer_detectors]
        for window_index, (baseline, window) in enumerate(
            zip(compiled.windows, windows, strict=True)
        ):
            received[baseline.arrival_detectors] = raw[baseline.arrival_detectors]
            syndrome = np.bitwise_xor(
                received[baseline.detection_detectors],
                correction[baseline.detection_detectors],
            )
            prediction, _ = accepted.explicit_decode(window, syndrome)
            selected, updates = replacement_batch(window, syndrome)
            phase = phase_for(window_index)
            manifest_row = manifest_rows[(basis, phase)]
            if (
                manifest_row["source_graph_image_sha256"] != window.graph_image_sha256
                or manifest_row["source_rule_image_sha256"] != window.rule_image_sha256
            ):
                raise ValueError(f"{basis}/{window_index}: image binding changed")
            if any(
                edge_index < 0
                or edge_index >= int(manifest_row["edges"])
                or weight < 0
                or weight > int(manifest_row["maximum_hardware_weight"])
                for edge_index, weight in updates
            ):
                raise ValueError(f"{basis}/{window_index}: hardware update out of range")
            batch_hash = sha_bytes(compact(updates))
            record = {
                "shot": shot_index,
                "window": window_index,
                "phase": phase,
                "syndrome_sha256": digest_bits(syndrome),
                "selected_edge_indices": selected,
                "updates": updates,
                "prediction_sha256": digest_bits(prediction),
                "reset_before_batch": True,
            }
            trace_digest.update(compact(record) + b"\n")
            batch_hash_counts[batch_hash] += 1
            count = len(updates)
            update_counts.append(count)
            selected_counts.append(len(selected))
            phase_update_counts[phase].append(count)
            total_update_writes += count
            first_batch_by_count.setdefault(count, record)
            detector_count = len(window.detector_outputs)
            correction[window.detector_outputs] ^= prediction[:detector_count]
            frame[window.observable_outputs] ^= prediction[detector_count:]
            residual = np.bitwise_xor(
                received[baseline.commit_detectors],
                correction[baseline.commit_detectors],
            )
            commit_failures += int(np.any(residual))
        final_predictions[shot_index] = frame
        final_residual_failures += int(np.any(np.bitwise_xor(received, correction)))
        if (shot_index + 1) % 128 == 0:
            print(f"{basis}: batch trace {shot_index + 1}/{len(raw_syndromes)}", flush=True)
    prediction_sha = sha_bytes(
        np.packbits(final_predictions, axis=1, bitorder="little").tobytes()
    )
    if prediction_sha != accepted_row["candidate_prediction_sha256"]:
        raise ValueError(f"{basis}: accepted candidate prediction hash changed")
    if commit_failures or final_residual_failures:
        raise ValueError(f"{basis}: reconstructed residual gate failed")
    distribution = accepted.distribution(update_counts)
    selected_distribution = accepted.distribution(selected_counts)
    expected_distribution = accepted_row["controller_payload"][
        "actually_lowered_replacement_edges"
    ]
    if distribution != expected_distribution:
        raise ValueError(f"{basis}: replacement distribution changed")
    wanted_counts = {
        "zero": 0,
        "p50": int(distribution["p50"]),
        "p99": int(distribution["p99"]),
        "maximum": int(distribution["maximum"]),
    }
    examples = {
        label: first_batch_by_count[count]
        for label, count in wanted_counts.items()
        if count in first_batch_by_count
    }
    return {
        "basis": basis,
        "shots": len(raw_syndromes),
        "windows_per_shot": len(windows),
        "window_batches": len(update_counts),
        "corpus_sha256": corpus_sha,
        "candidate_prediction_sha256": prediction_sha,
        "trace_sha256": trace_digest.hexdigest(),
        "unique_update_batches": len(batch_hash_counts),
        "update_batch_occurrence_sha256": sha_bytes(
            compact(sorted(batch_hash_counts.items()))
        ),
        "total_update_writes": total_update_writes,
        "reset_commands": len(update_counts),
        "selected_edges": selected_distribution,
        "hardware_update_edges": distribution,
        "hardware_update_bus_words_32bit": distribution,
        "hardware_update_bus_bits": {
            key: (value * 32 if isinstance(value, (int, float)) and key not in {"observations", "zero_fraction"} else value)
            for key, value in distribution.items()
            if key != "raw_uint32_sha256"
        },
        "phase_hardware_update_edges": {
            phase: accepted.distribution(values)
            for phase, values in sorted(phase_update_counts.items())
        },
        "representative_batches": examples,
        "commit_residual_failures": commit_failures,
        "final_residual_failure_shots": final_residual_failures,
        "structural_graph_sequence_sha256": structural["graph_sequence_sha256"],
        "structural_rule_sequence_sha256": structural["rule_sequence_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source_result = read(accepted.DEFAULT_RESULT)
    if source_result["classification"] != "sixteen_bit_explicit_reweight_semantic_pass_hardware_write_path_absent":
        raise ValueError("accepted v2 result changed")
    image_manifest = read(IMAGE_MANIFEST)
    manifest_rows = {
        (row["basis"], row["phase"]): row for row in image_manifest["images"]
    }
    corpora = {row["basis"]: row for row in source_result["corpora"]}
    accepted_rows = {row["basis"]: row for row in source_result["basis_rows"]}
    scale = int(source_result["candidate_contract"]["half_weight_scale"])
    rows = [
        reconstruct_basis(
            basis, corpora[basis], accepted_rows[basis], manifest_rows, scale
        )
        for basis in ("x", "z")
    ]
    result = {
        "schema": "b2_b7_p023_d6_microblossom_batch_trace_v1",
        "date": "2026-11-20",
        "classification": "accepted_corpus_hardware_batch_trace_reconstructed_rtl_replay_open",
        "scope": ["021/B7", "022/B2", "023"],
        "source_result": str(accepted.DEFAULT_RESULT.relative_to(ROOT)),
        "source_result_sha256": accepted.sha_path(accepted.DEFAULT_RESULT),
        "image_manifest": str(IMAGE_MANIFEST.relative_to(ROOT)),
        "image_manifest_sha256": accepted.sha_path(IMAGE_MANIFEST),
        "image_evidence_id": image_manifest["evidence_id"],
        "accepted_corpus_reopened": True,
        "fresh_stochastic_samples_observed": 0,
        "hardware_weight_normalization_divisor": 2,
        "hardware_update_encoding": "one 32-bit AXI word per edge: edge[14:0], reserved[15], normalized weight[31:16]",
        "basis_rows": rows,
        "acceptance": {
            "accepted_corpus_hashes_reproduced": True,
            "accepted_candidate_prediction_hashes_reproduced": True,
            "per_window_update_batches_bound": True,
            "rtl_batch_replay_completed": False,
            "rtl_corrections_compared": False,
            "batch_p99_cycles_measured": False,
            "p99_le_1us": False,
            "miss_rate_le_1pct": False,
            "full_b2": False,
            "scalable_p023": False,
            "b7_resource_credit": 0,
        },
        "next_gate": "Replay representative boundary batches first, then all accepted per-window batches, against the generated RTL and compare edge state plus correction output before timing credit.",
    }
    result["evidence_id"] = sha_bytes(compact(result))
    args.output.write_text(canonical(result), encoding="utf-8")
    print(canonical(result), end="")


if __name__ == "__main__":
    main()
