#!/usr/bin/env python3
"""Reconstruct opening/closing resident-selector batches from the accepted corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import b2_b7_p023_d6_explicit_reweight_v2 as accepted  # noqa: E402
import b2_b7_p023_d6_microblossom_batch_trace_v1 as prior  # noqa: E402


DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_microblossom_phase_batch_trace_v1.json"
IMAGE_MANIFEST = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_images_v1.json"
SOURCE_TRACE = ROOT / "results/B2_B7_P023_d6_microblossom_batch_trace_v1.json"


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    final_predictions = np.zeros(
        (len(raw_syndromes), circuit.num_observables), dtype=np.uint8
    )
    phase_update_counts: dict[str, list[int]] = defaultdict(list)
    phase_selected_counts: dict[str, list[int]] = defaultdict(list)
    phase_first_by_update_count: dict[str, dict[int, dict[str, Any]]] = {
        "opening": {},
        "closing": {},
    }
    phase_trace_digest = hashlib.sha256()
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
            phase = prior.phase_for(window_index)
            if phase in {"opening", "closing"}:
                selected, updates = prior.replacement_batch(window, syndrome)
                manifest_row = manifest_rows[(basis, phase)]
                if (
                    manifest_row["source_graph_image_sha256"]
                    != window.graph_image_sha256
                    or manifest_row["source_rule_image_sha256"]
                    != window.rule_image_sha256
                ):
                    raise ValueError(f"{basis}/{window_index}: image binding changed")
                record = {
                    "shot": shot_index,
                    "window": window_index,
                    "phase": phase,
                    "syndrome_sha256": prior.digest_bits(syndrome),
                    "selected_edge_indices": selected,
                    "updates": updates,
                    "prediction_sha256": prior.digest_bits(prediction),
                    "reset_before_batch": True,
                }
                phase_trace_digest.update(compact(record) + b"\n")
                count = len(updates)
                phase_update_counts[phase].append(count)
                phase_selected_counts[phase].append(len(selected))
                phase_first_by_update_count[phase].setdefault(count, record)
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
            print(
                f"{basis}: phase trace {shot_index + 1}/{len(raw_syndromes)}",
                flush=True,
            )
    prediction_sha = sha_bytes(
        np.packbits(final_predictions, axis=1, bitorder="little").tobytes()
    )
    if prediction_sha != accepted_row["candidate_prediction_sha256"]:
        raise ValueError(f"{basis}: accepted candidate prediction hash changed")
    if commit_failures or final_residual_failures:
        raise ValueError(f"{basis}: reconstructed residual gate failed")

    phases = []
    for phase in ("opening", "closing"):
        updates = accepted.distribution(phase_update_counts[phase])
        selected = accepted.distribution(phase_selected_counts[phase])
        wanted = {
            "zero": 0,
            "p50": int(updates["p50"]),
            "p99": int(updates["p99"]),
            "maximum": int(updates["maximum"]),
        }
        representatives = {
            boundary: phase_first_by_update_count[phase][count]
            for boundary, count in wanted.items()
        }
        phases.append({
            "phase": phase,
            "window_index": 0 if phase == "opening" else 163,
            "batches": len(phase_update_counts[phase]),
            "hardware_update_edges": updates,
            "selected_source_edges": selected,
            "representative_batches": representatives,
        })
    return {
        "basis": basis,
        "shots": len(raw_syndromes),
        "corpus_sha256": corpus_sha,
        "candidate_prediction_sha256": prediction_sha,
        "opening_closing_trace_sha256": phase_trace_digest.hexdigest(),
        "phases": phases,
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
    if (
        source_result["classification"]
        != "sixteen_bit_explicit_reweight_semantic_pass_hardware_write_path_absent"
    ):
        raise ValueError("accepted v2 result changed")
    source_trace = read(SOURCE_TRACE)
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
        "schema": "b2_b7_p023_d6_microblossom_phase_batch_trace_v1",
        "date": "2026-11-21",
        "classification": "accepted_opening_closing_selector_trace_reconstructed_rtl_replay_open",
        "scope": ["021/B7", "022/B2", "023"],
        "source_result": str(accepted.DEFAULT_RESULT.relative_to(ROOT)),
        "source_result_sha256": sha_path(accepted.DEFAULT_RESULT),
        "source_batch_trace": str(SOURCE_TRACE.relative_to(ROOT)),
        "source_batch_trace_sha256": sha_path(SOURCE_TRACE),
        "source_batch_trace_evidence_id": source_trace["evidence_id"],
        "image_manifest": str(IMAGE_MANIFEST.relative_to(ROOT)),
        "image_manifest_sha256": sha_path(IMAGE_MANIFEST),
        "image_evidence_id": image_manifest["evidence_id"],
        "accepted_corpus_reopened": True,
        "fresh_stochastic_samples_observed": 0,
        "basis_rows": rows,
        "acceptance": {
            "accepted_corpus_hashes_reproduced": True,
            "accepted_candidate_prediction_hashes_reproduced": True,
            "opening_closing_batches_bound": True,
            "opening_closing_rtl_replay_completed": False,
            "rtl_corrections_compared": False,
            "fpga_fmax_measured": False,
            "p99_le_1us": False,
            "miss_rate_le_1pct": False,
            "full_b2": False,
            "scalable_p023": False,
            "b7_resource_credit": 0,
        },
        "next_gate": "Generate resident-selector RTL for X/Z opening and closing images, replay all sixteen phase boundary batches, and compare every edge state before phase-switch or timing credit.",
    }
    result["evidence_id"] = sha_bytes(compact(result))
    args.output.write_text(canonical(result), encoding="utf-8")
    print(canonical(result), end="")


if __name__ == "__main__":
    main()
