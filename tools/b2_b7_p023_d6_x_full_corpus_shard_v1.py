#!/usr/bin/env python3
"""Reopen a deterministic X-corpus shot range as an RTL primal/dual shard."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import b2_b7_p023_d6_explicit_reweight_v2 as accepted  # noqa: E402
import b2_b7_p023_d6_microblossom_batch_trace_v1 as trace  # noqa: E402


BASE_INPUT = ROOT / "benchmarks/B2_B7_P023_d6_x_phase_primal_dual_input_v1.json"
PLAN = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
ACCEPTED_TRACE = ROOT / "results/B2_B7_P023_d6_microblossom_batch_trace_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def bits_hex(bits: np.ndarray) -> str:
    value = sum(int(bit) << index for index, bit in enumerate(bits.tolist()))
    return format(value, "x")


def phase_for(window: int) -> tuple[str, int]:
    if window == 0:
        return "opening", 0
    if 1 <= window <= 162:
        return "steady", 1
    if window == 163:
        return "closing", 2
    raise ValueError(f"unexpected window {window}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shot-start", type=int, required=True)
    parser.add_argument("--shot-end", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source_result = read(accepted.DEFAULT_RESULT)
    corpus = next(row for row in source_result["corpora"] if row["basis"] == "x")
    accepted_trace = next(row for row in read(ACCEPTED_TRACE)["basis_rows"] if row["basis"] == "x")
    shots = int(corpus["shots"])
    if not 0 <= args.shot_start < args.shot_end <= shots:
        raise ValueError("shot range must be a non-empty subset of the frozen X corpus")
    scale = int(source_result["candidate_contract"]["half_weight_scale"])
    circuit, compiled, windows, structural = accepted.compile_basis("x", scale)
    if len(windows) != 164:
        raise ValueError("window cardinality changed")
    sampler = circuit.compile_detector_sampler(seed=int(corpus["seed"]))
    detectors_packed, observables_packed = sampler.sample(
        shots, separate_observables=True, bit_packed=True
    )
    header = {
        "basis": "x",
        "shots": shots,
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
    if corpus_sha != corpus["corpus_sha256"] or corpus_sha != accepted_trace["corpus_sha256"]:
        raise ValueError("accepted X corpus hash changed")
    if structural["graph_sequence_sha256"] != accepted_trace["structural_graph_sequence_sha256"]:
        raise ValueError("X graph sequence changed")
    if structural["rule_sequence_sha256"] != accepted_trace["structural_rule_sequence_sha256"]:
        raise ValueError("X rule sequence changed")

    raw_syndromes = np.unpackbits(
        detectors_packed,
        axis=1,
        count=circuit.num_detectors,
        bitorder="little",
    ).astype(np.uint8, copy=False)
    plan = read(PLAN)
    x_plan = next(row for row in plan["basis_plans"] if row["basis"] == "x")
    phase_rows = {row["phase"]: row for row in x_plan["phases"]}
    phase_metadata: dict[str, dict[str, Any]] = {}
    for phase, row in phase_rows.items():
        image = read(ROOT / row["source_image"])
        phase_metadata[phase] = image["qec_image_metadata"]

    cases: list[dict[str, Any]] = []
    final_frames: list[np.ndarray] = []
    commit_failures = 0
    final_residual_failures = 0
    for shot in range(args.shot_start, args.shot_end):
        raw = raw_syndromes[shot]
        received = np.zeros(compiled.model.num_detectors, dtype=np.uint8)
        correction = np.zeros(compiled.model.num_detectors, dtype=np.uint8)
        frame = np.zeros(compiled.model.num_observables, dtype=np.uint8)
        received[compiled.prebuffer_detectors] = raw[compiled.prebuffer_detectors]
        for window_index, (baseline, window) in enumerate(
            zip(compiled.windows, windows, strict=True)
        ):
            phase, phase_index = phase_for(window_index)
            row = phase_rows[phase]
            metadata = phase_metadata[phase]
            if window.graph_image_sha256 != metadata["source_graph_image_sha256"]:
                raise ValueError(f"{phase}: graph image changed")
            if window.rule_image_sha256 != metadata["source_rule_image_sha256"]:
                raise ValueError(f"{phase}: rule image changed")
            received[baseline.arrival_detectors] = raw[baseline.arrival_detectors]
            syndrome = np.bitwise_xor(
                received[baseline.detection_detectors],
                correction[baseline.detection_detectors],
            )
            prediction, _ = accepted.explicit_decode(window, syndrome)
            selected_local, _ = trace.replacement_batch(window, syndrome)
            defect_local = np.flatnonzero(syndrome).tolist()
            defect_superset = [row["local_to_superset_vertex"][index] for index in defect_local]
            selector_superset = [row["local_to_superset_edge"][index] for index in selected_local]
            cases.append(
                {
                    "phase": phase,
                    "phase_index": phase_index,
                    "shot": shot,
                    "window": window_index,
                    "defect_vertices": defect_superset,
                    "selector_edges": selector_superset,
                    "syndrome_sha256": trace.digest_bits(syndrome),
                    "expected_correction_hex": bits_hex(prediction),
                    "expected_correction_sha256": trace.digest_bits(prediction),
                    "fault_id_count": row["fault_id_count"],
                }
            )
            detector_count = len(window.detector_outputs)
            correction[window.detector_outputs] ^= prediction[:detector_count]
            frame[window.observable_outputs] ^= prediction[detector_count:]
            residual = np.bitwise_xor(
                received[baseline.commit_detectors],
                correction[baseline.commit_detectors],
            )
            commit_failures += int(np.any(residual))
        final_frames.append(frame)
        final_residual_failures += int(np.any(np.bitwise_xor(received, correction)))
        print(f"x shard: generated shot {shot}", flush=True)

    if commit_failures or final_residual_failures:
        raise ValueError("accepted X residual gate changed")
    final_packed = np.packbits(np.asarray(final_frames), axis=1, bitorder="little")
    payload = {
        "schema": "b2_b7_p023_d6_x_full_corpus_shard_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "basis": "x",
        "base_input": str(BASE_INPUT.relative_to(ROOT)),
        "base_input_sha256": sha_path(BASE_INPUT),
        "base_input_evidence_id": read(BASE_INPUT)["evidence_id"],
        "accepted_corpus_sha256": corpus_sha,
        "accepted_candidate_prediction_sha256": accepted_trace["candidate_prediction_sha256"],
        "shot_start": args.shot_start,
        "shot_end": args.shot_end,
        "shots": args.shot_end - args.shot_start,
        "windows_per_shot": len(windows),
        "cases": cases,
        "case_sequence_sha256": sha_bytes(b"".join(compact(case) + b"\n" for case in cases)),
        "shard_final_prediction_sha256": sha_bytes(final_packed.tobytes()),
        "commit_residual_failures": commit_failures,
        "final_residual_failures": final_residual_failures,
    }
    payload["evidence_id"] = sha_bytes(compact(payload))
    args.output.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "evidence_id": payload["evidence_id"],
        "shots": payload["shots"],
        "cases": len(cases),
        "defects": sum(len(case["defect_vertices"]) for case in cases),
        "selectors": sum(len(case["selector_edges"]) for case in cases),
    }, indent=2))


if __name__ == "__main__":
    main()
