#!/usr/bin/env python3
"""Build a frozen raw-detector pilot for closed-loop Z RTL execution."""

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


PLAN = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
OUTPUT = ROOT / "benchmarks/B2_B7_P023_d6_z_closed_loop_pilot_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bits_hex(bits: np.ndarray) -> str:
    value = sum(int(bit) << index for index, bit in enumerate(bits.tolist()))
    return format(value, "x")


def phase_for(window: int) -> tuple[str, int]:
    if window == 0:
        return "opening", 0
    if window == 163:
        return "closing", 2
    return "steady", 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shots", type=int, nargs="+", default=[0, 15])
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if len(set(args.shots)) != len(args.shots):
        raise ValueError("shot indices must be unique")

    source = read(accepted.DEFAULT_RESULT)
    scale = int(source["candidate_contract"]["half_weight_scale"])
    corpus = next(row for row in source["corpora"] if row["basis"] == "z")
    circuit, compiled, windows, structural = accepted.compile_basis("z", scale)
    if any(shot < 0 or shot >= int(corpus["shots"]) for shot in args.shots):
        raise ValueError("pilot shot outside frozen corpus")
    sampler = circuit.compile_detector_sampler(seed=int(corpus["seed"]))
    detectors_packed, observables_packed = sampler.sample(
        int(corpus["shots"]), separate_observables=True, bit_packed=True
    )
    header = {
        "basis": "z",
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
        raise ValueError("accepted Z corpus hash changed")
    raw_syndromes = np.unpackbits(
        detectors_packed,
        axis=1,
        count=circuit.num_detectors,
        bitorder="little",
    ).astype(np.uint8, copy=False)

    plan = read(PLAN)
    z_plan = next(row for row in plan["basis_plans"] if row["basis"] == "z")
    phase_rows = {row["phase"]: row for row in z_plan["phases"]}
    phases = []
    for phase, phase_index in (("opening", 0), ("steady", 1), ("closing", 2)):
        row = phase_rows[phase]
        phases.append({
            "name": phase,
            "phase_index": phase_index,
            "local_to_superset_vertex": row["local_to_superset_vertex"],
            "fault_id_count": row["fault_id_count"],
        })

    window_rows = []
    for window_index, (baseline, window) in enumerate(
        zip(compiled.windows, windows, strict=True)
    ):
        phase, phase_index = phase_for(window_index)
        if len(baseline.detection_detectors) > len(
            phase_rows[phase]["local_to_superset_vertex"]
        ):
            raise ValueError("syndrome-to-vertex map is too short")
        window_rows.append({
            "window": window_index,
            "phase": phase,
            "phase_index": phase_index,
            "arrival_detectors": list(map(int, baseline.arrival_detectors)),
            "detection_detectors": list(map(int, baseline.detection_detectors)),
            "commit_detectors": list(map(int, baseline.commit_detectors)),
            "detector_outputs": list(map(int, window.detector_outputs)),
            "observable_outputs": list(map(int, window.observable_outputs)),
        })

    shot_rows = []
    for shot in args.shots:
        raw = raw_syndromes[shot]
        received = np.zeros(compiled.model.num_detectors, dtype=np.uint8)
        correction = np.zeros(compiled.model.num_detectors, dtype=np.uint8)
        frame = np.zeros(compiled.model.num_observables, dtype=np.uint8)
        received[compiled.prebuffer_detectors] = raw[compiled.prebuffer_detectors]
        for baseline, window in zip(compiled.windows, windows, strict=True):
            received[baseline.arrival_detectors] = raw[baseline.arrival_detectors]
            syndrome = np.bitwise_xor(
                received[baseline.detection_detectors],
                correction[baseline.detection_detectors],
            )
            prediction, _ = accepted.explicit_decode(window, syndrome)
            detector_count = len(window.detector_outputs)
            correction[window.detector_outputs] ^= prediction[:detector_count]
            frame[window.observable_outputs] ^= prediction[detector_count:]
            if np.any(np.bitwise_xor(
                received[baseline.commit_detectors],
                correction[baseline.commit_detectors],
            )):
                raise ValueError(f"shot {shot}: reference commit residual")
        if np.any(np.bitwise_xor(received, correction)):
            raise ValueError(f"shot {shot}: reference final residual")
        shot_rows.append({
            "shot": shot,
            "raw_detector_hex": bits_hex(raw),
            "expected_final_frame_hex": bits_hex(frame),
        })

    payload: dict[str, Any] = {
        "schema": "b2_b7_p023_d6_z_closed_loop_pilot_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "basis": "z",
        "accepted_corpus_sha256": corpus_sha,
        "structural_graph_sequence_sha256": structural["graph_sequence_sha256"],
        "structural_rule_sequence_sha256": structural["rule_sequence_sha256"],
        "detector_count": compiled.model.num_detectors,
        "observable_count": compiled.model.num_observables,
        "prebuffer_detectors": list(map(int, compiled.prebuffer_detectors)),
        "phases": phases,
        "windows": window_rows,
        "shots": shot_rows,
        "source": {
            "accepted_result": str(accepted.DEFAULT_RESULT.relative_to(ROOT)),
            "accepted_result_sha256": sha_path(accepted.DEFAULT_RESULT),
            "superset_plan": str(PLAN.relative_to(ROOT)),
            "superset_plan_sha256": sha_path(PLAN),
        },
    }
    payload["evidence_id"] = sha_bytes(compact(payload))
    args.output.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    print(json.dumps({
        "output": str(args.output),
        "evidence_id": payload["evidence_id"],
        "shots": args.shots,
        "windows": len(window_rows),
        "detector_count": payload["detector_count"],
    }, indent=2))


if __name__ == "__main__":
    main()
