#!/usr/bin/env python3
"""Bind complete X representative correction subgraphs to the phase superset.

This reopens the frozen accepted corpus.  For each opening/steady/closing
zero/p50/p99/maximum representative, it reproduces every preceding online
window, obtains the final second-pass matching subgraph, and proves that XORing
the selected edges' fault IDs equals the public correction vector bit-for-bit.
The resulting trace is an input to RTL replay, not evidence that RTL chose the
subgraph itself.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import b2_b7_p023_d6_explicit_reweight_v2 as accepted  # noqa: E402
import b2_b7_p023_d6_microblossom_batch_trace_v1 as prior  # noqa: E402

PHASE_TRACE = ROOT / "results/B2_B7_P023_d6_microblossom_phase_batch_trace_v1.json"
STEADY_TRACE = ROOT / "results/B2_B7_P023_d6_microblossom_batch_trace_v1.json"
SUPERSET_PLAN = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
OUTPUT = ROOT / "benchmarks/B2_B7_P023_d6_x_phase_fault_output_trace_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def second_pass_matching(
    window: accepted.ExplicitWindow, syndrome: np.ndarray
):
    selected = accepted.selected_edge_keys(window.base_candidate, syndrome)
    replacements: dict[tuple[int, int], int] = {}
    for source in selected:
        for target, half_weight in window.rules.get(source, ()):
            replacements[target] = min(
                replacements.get(target, window.base_half_weights[target]),
                half_weight,
            )
    if not replacements:
        return window.base_candidate
    return accepted.build_integer_matching(window.edges, replacements)


def representative_targets() -> dict[tuple[int, int], tuple[str, str, dict[str, Any]]]:
    phase_x = next(row for row in read(PHASE_TRACE)["basis_rows"] if row["basis"] == "x")
    steady_x = next(row for row in read(STEADY_TRACE)["basis_rows"] if row["basis"] == "x")
    targets: dict[tuple[int, int], tuple[str, str, dict[str, Any]]] = {}
    for phase_row in phase_x["phases"]:
        for boundary, record in phase_row["representative_batches"].items():
            targets[(record["shot"], record["window"])] = (
                phase_row["phase"], boundary, record
            )
    for boundary, record in steady_x["representative_batches"].items():
        targets[(record["shot"], record["window"])] = ("steady", boundary, record)
    if len(targets) != 12:
        raise ValueError("expected twelve representative targets")
    return targets


def main() -> None:
    source = read(accepted.DEFAULT_RESULT)
    scale = int(source["candidate_contract"]["half_weight_scale"])
    corpus = next(row for row in source["corpora"] if row["basis"] == "x")
    plan = read(SUPERSET_PLAN)
    x_plan = next(row for row in plan["basis_plans"] if row["basis"] == "x")
    phase_plan = {row["phase"]: row for row in x_plan["phases"]}
    targets = representative_targets()

    circuit, compiled, windows, _ = accepted.compile_basis("x", scale)
    sampler = circuit.compile_detector_sampler(seed=int(corpus["seed"]))
    detectors_packed, observables_packed = sampler.sample(
        int(corpus["shots"]), separate_observables=True, bit_packed=True
    )
    header = {
        "basis": "x",
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
        raise ValueError("accepted X corpus hash changed")
    raw_syndromes = np.unpackbits(
        detectors_packed,
        axis=1,
        count=circuit.num_detectors,
        bitorder="little",
    ).astype(np.uint8, copy=False)

    rows: list[dict[str, Any]] = []
    target_shots = sorted({shot for shot, _ in targets})
    for shot in target_shots:
        raw = raw_syndromes[shot]
        received = np.zeros(compiled.model.num_detectors, dtype=np.uint8)
        correction = np.zeros(compiled.model.num_detectors, dtype=np.uint8)
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
            key = (shot, window_index)
            if key in targets:
                phase, boundary, source_record = targets[key]
                if prior.digest_bits(syndrome) != source_record["syndrome_sha256"]:
                    raise ValueError(f"{phase}/{boundary}: syndrome digest changed")
                if prior.digest_bits(prediction) != source_record["prediction_sha256"]:
                    raise ValueError(f"{phase}/{boundary}: prediction digest changed")
                matching = second_pass_matching(window, syndrome)
                selected_array = matching.decode_to_edges_array(
                    syndrome, enable_correlations=False
                )
                index_by_key = {edge.key: index for index, edge in enumerate(window.edges)}
                edge_by_key = {edge.key: edge for edge in window.edges}
                selected_local: list[int] = []
                reconstructed = np.zeros(matching.num_fault_ids, dtype=np.uint8)
                for node1, node2 in selected_array:
                    edge_key = (
                        (int(node1), -1)
                        if int(node2) == -1
                        else tuple(sorted((int(node1), int(node2))))
                    )
                    selected_local.append(index_by_key[edge_key])
                    for fault_id in edge_by_key[edge_key].fault_ids:
                        reconstructed[fault_id] ^= 1
                selected_local.sort()
                if len(selected_local) != len(set(selected_local)):
                    raise ValueError(f"{phase}/{boundary}: duplicate selected edge")
                if not np.array_equal(reconstructed, prediction):
                    raise ValueError(f"{phase}/{boundary}: fault XOR differs from correction")
                phase_row = phase_plan[phase]
                if len(prediction) != phase_row["fault_id_count"]:
                    raise ValueError(f"{phase}/{boundary}: fault-vector width changed")
                selected_superset = [
                    phase_row["local_to_superset_edge"][index]
                    for index in selected_local
                ]
                rows.append(
                    {
                        "phase": phase,
                        "boundary": boundary,
                        "shot": shot,
                        "window": window_index,
                        "syndrome_sha256": source_record["syndrome_sha256"],
                        "correction_sha256": source_record["prediction_sha256"],
                        "fault_id_count": len(prediction),
                        "nonzero_fault_ids": np.flatnonzero(prediction).tolist(),
                        "selected_local_edges": selected_local,
                        "selected_superset_edges": selected_superset,
                    }
                )
            detector_count = len(window.detector_outputs)
            correction[window.detector_outputs] ^= prediction[:detector_count]

    rows.sort(key=lambda row: (("opening", "steady", "closing").index(row["phase"]), ("zero", "p50", "p99", "maximum").index(row["boundary"])))
    if len(rows) != 12:
        raise ValueError("not all representative corrections were reconstructed")
    payload = {
        "schema": "b2_b7_p023_d6_x_phase_fault_output_trace_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "basis": "x",
        "classification": "complete_reference_subgraph_fault_xor_trace_for_rtl_input",
        "source": {
            "accepted_result": str(accepted.DEFAULT_RESULT.relative_to(ROOT)),
            "accepted_result_sha256": sha_path(accepted.DEFAULT_RESULT),
            "phase_trace": str(PHASE_TRACE.relative_to(ROOT)),
            "phase_trace_sha256": sha_path(PHASE_TRACE),
            "steady_trace": str(STEADY_TRACE.relative_to(ROOT)),
            "steady_trace_sha256": sha_path(STEADY_TRACE),
            "superset_plan": str(SUPERSET_PLAN.relative_to(ROOT)),
            "superset_plan_sha256": sha_path(SUPERSET_PLAN),
            "accepted_corpus_sha256": corpus_sha,
        },
        "representative_corrections": rows,
        "checks": {
            "representatives": len(rows),
            "complete_second_pass_subgraphs_extracted": True,
            "selected_edge_fault_xor_equals_public_correction": True,
            "mapped_to_superset_edges": True,
            "rtl_executed": False,
            "distributed_dual_selected_subgraph": False,
        },
    }
    payload["evidence_id"] = sha_bytes(compact(payload))
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
