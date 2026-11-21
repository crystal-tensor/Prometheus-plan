#!/usr/bin/env python3
"""Build the Z Rust-primal/phase-aware-DistributedDual integration input."""

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

PLAN = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
FAULT_TRACE = ROOT / "benchmarks/B2_B7_P023_d6_z_phase_fault_output_trace_v1.json"
PHASE_TRACE = ROOT / "results/B2_B7_P023_d6_microblossom_phase_batch_trace_v1.json"
STEADY_TRACE = ROOT / "results/B2_B7_P023_d6_microblossom_batch_trace_v1.json"
OUTPUT = ROOT / "benchmarks/B2_B7_P023_d6_z_phase_primal_dual_input_v1.json"
MICRO_BLOSSOM_WEIGHT_SCALE = 2


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def balanced_tree(leaves: int) -> dict[str, list[dict[str, int]]]:
    nodes: list[dict[str, int]] = [{} for _ in range(leaves)]
    frontier = list(range(leaves))
    while len(frontier) > 1:
        following: list[int] = []
        index = 0
        while index < len(frontier):
            if index + 1 == len(frontier):
                following.append(frontier[index])
                index += 1
            else:
                left, right = frontier[index : index + 2]
                parent = len(nodes)
                nodes.append({"l": left, "r": right})
                nodes[left]["p"] = parent
                nodes[right]["p"] = parent
                following.append(parent)
                index += 2
        frontier = following
    return {"nodes": nodes}


def graph_json(
    positions: list[dict[str, float]],
    vertex_num: int,
    weighted_edges: list[dict[str, int]],
    virtual_vertices: list[int],
    vertex_max_growth: list[int],
) -> dict[str, Any]:
    return {
        "positions": positions,
        "vertex_num": vertex_num,
        "weighted_edges": weighted_edges,
        "virtual_vertices": virtual_vertices,
        "vertex_binary_tree": balanced_tree(vertex_num),
        "edge_binary_tree": balanced_tree(len(weighted_edges)),
        "vertex_edge_binary_tree": balanced_tree(vertex_num + len(weighted_edges)),
        "vertex_max_growth": vertex_max_growth,
        "offloading": [],
        "layer_fusion": None,
        "parity_reporters": None,
    }


def representative_sources() -> dict[tuple[int, int], dict[str, Any]]:
    result: dict[tuple[int, int], dict[str, Any]] = {}
    phase_z = next(row for row in read(PHASE_TRACE)["basis_rows"] if row["basis"] == "z")
    steady_z = next(row for row in read(STEADY_TRACE)["basis_rows"] if row["basis"] == "z")
    for phase_row in phase_z["phases"]:
        for record in phase_row["representative_batches"].values():
            result[(record["shot"], record["window"])] = record
    for record in steady_z["representative_batches"].values():
        result[(record["shot"], record["window"])] = record
    return result


def bits_hex(bits: np.ndarray) -> str:
    value = sum(int(bit) << index for index, bit in enumerate(bits.tolist()))
    return format(value, "x")


def main() -> None:
    plan = read(PLAN)
    fault_trace = read(FAULT_TRACE)
    z_plan = next(row for row in plan["basis_plans"] if row["basis"] == "z")
    phase_rows = {row["phase"]: row for row in z_plan["phases"]}
    phase_names = ("opening", "steady", "closing")
    edge_num = len(z_plan["superset_edges"])
    vertex_num = len(z_plan["superset_vertices"])

    positions = []
    for index, key in enumerate(z_plan["superset_vertices"]):
        numeric = [float(value) for value in key[1:]]
        positions.append(
            {
                "i": numeric[0] if len(numeric) > 0 else float(index),
                "j": numeric[1] if len(numeric) > 1 else 0.0,
                "t": numeric[2] if len(numeric) > 2 else 0.0,
            }
        )

    phase_banks = []
    phase_graphs = []
    for phase in phase_names:
        row = phase_rows[phase]
        local_to_edge = row["local_to_superset_edge"]
        local_to_vertex = row["local_to_superset_vertex"]
        edge_active = [False] * edge_num
        base_weights = [0] * edge_num
        edge_fault_ids: list[list[int]] = [[] for _ in range(edge_num)]
        for superset, weight, fault_ids in zip(
            local_to_edge,
            row["base_weights_local_edge_order"],
            row["fault_ids_local_edge_order"],
            strict=True,
        ):
            edge_active[superset] = True
            base_weights[superset] = weight * MICRO_BLOSSOM_WEIGHT_SCALE
            edge_fault_ids[superset] = fault_ids
        vertex_active = [False] * vertex_num
        vertex_growth = [0] * vertex_num
        for superset, growth in zip(
            local_to_vertex, row["vertex_max_growth_local_order"], strict=True
        ):
            vertex_active[superset] = True
            vertex_growth[superset] = growth * MICRO_BLOSSOM_WEIGHT_SCALE
        image = read(ROOT / row["source_image"])
        virtual_vertices = [local_to_vertex[index] for index in image["virtual_vertices"]]
        virtual_set = set(virtual_vertices)
        vertex_virtual = [index in virtual_set for index in range(vertex_num)]
        by_target: dict[int, list[list[int]]] = {}
        for rule in row["active_resident_rules"]:
            by_target.setdefault(rule["target_edge"], []).append(
                [
                    rule["source_edge"],
                    rule["replacement_weight"] * MICRO_BLOSSOM_WEIGHT_SCALE,
                ]
            )
        phase_banks.append(
            {
                "name": phase,
                "edge_active": edge_active,
                "edge_base_weights": base_weights,
                "resident_weight_rules": [
                    {"target": target, "rules": sorted(rules)}
                    for target, rules in sorted(by_target.items())
                ],
                "edge_fault_ids": edge_fault_ids,
                "fault_id_count": row["fault_id_count"],
                "vertex_active": vertex_active,
                "vertex_virtual": vertex_virtual,
                "vertex_max_growth": vertex_growth,
            }
        )
        local_edges = []
        for local_index, superset in enumerate(local_to_edge):
            edge = z_plan["superset_edges"][superset]
            local_edges.append(
                {
                    "l": edge["left_vertex"],
                    "r": edge["right_vertex"],
                    "w": row["base_weights_local_edge_order"][local_index]
                    * MICRO_BLOSSOM_WEIGHT_SCALE,
                }
            )
        phase_graphs.append(
            {
                "name": phase,
                "graph": graph_json(
                    positions,
                    vertex_num,
                    local_edges,
                    virtual_vertices,
                    vertex_growth,
                ),
                "local_to_superset_edge": local_to_edge,
            }
        )

    superset_weighted_edges = []
    for edge_index, edge in enumerate(z_plan["superset_edges"]):
        available = [
            phase_banks[index]["edge_base_weights"][edge_index]
            for index in range(len(phase_names))
            if phase_banks[index]["edge_base_weights"][edge_index] > 0
        ]
        if not available:
            raise ValueError(f"superset edge {edge_index} has no weight")
        superset_weighted_edges.append(
            {"l": edge["left_vertex"], "r": edge["right_vertex"], "w": available[0]}
        )
    superset_virtual = sorted(
        {
            index
            for bank in phase_banks
            for index, virtual in enumerate(bank["vertex_virtual"])
            if virtual
        }
    )
    superset_growth = [
        max(bank["vertex_max_growth"][index] for bank in phase_banks)
        for index in range(vertex_num)
    ]
    superset_graph = graph_json(
        positions,
        vertex_num,
        superset_weighted_edges,
        superset_virtual,
        superset_growth,
    )

    source = read(accepted.DEFAULT_RESULT)
    scale = int(source["candidate_contract"]["half_weight_scale"])
    corpus = next(row for row in source["corpora"] if row["basis"] == "z")
    circuit, compiled, windows, _ = accepted.compile_basis("z", scale)
    sampler = circuit.compile_detector_sampler(seed=int(corpus["seed"]))
    detectors_packed, _ = sampler.sample(
        int(corpus["shots"]), separate_observables=True, bit_packed=True
    )
    raw_syndromes = np.unpackbits(
        detectors_packed,
        axis=1,
        count=circuit.num_detectors,
        bitorder="little",
    ).astype(np.uint8, copy=False)
    target_rows = {
        (row["shot"], row["window"]): row
        for row in fault_trace["representative_corrections"]
    }
    source_records = representative_sources()
    cases = []
    for shot in sorted({shot for shot, _ in target_rows}):
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
            if key in target_rows:
                target = target_rows[key]
                phase = target["phase"]
                phase_index = phase_names.index(phase)
                row = phase_rows[phase]
                source_record = source_records[key]
                if prior.digest_bits(syndrome) != target["syndrome_sha256"]:
                    raise ValueError("target syndrome changed")
                if prior.digest_bits(prediction) != target["correction_sha256"]:
                    raise ValueError("target correction changed")
                defect_local = np.flatnonzero(syndrome).tolist()
                defect_superset = [
                    row["local_to_superset_vertex"][index] for index in defect_local
                ]
                selector_superset = [
                    row["local_to_superset_edge"][index]
                    for index in source_record["selected_edge_indices"]
                ]
                cases.append(
                    {
                        "phase": phase,
                        "phase_index": phase_index,
                        "boundary": target["boundary"],
                        "shot": shot,
                        "window": window_index,
                        "defect_vertices": defect_superset,
                        "selector_edges": selector_superset,
                        "expected_reference_subgraph_local_edges": target[
                            "selected_local_edges"
                        ],
                        "expected_reference_subgraph_superset_edges": target[
                            "selected_superset_edges"
                        ],
                        "expected_correction_hex": bits_hex(prediction),
                        "expected_correction_sha256": target["correction_sha256"],
                        "fault_id_count": target["fault_id_count"],
                    }
                )
            detector_count = len(window.detector_outputs)
            correction[window.detector_outputs] ^= prediction[:detector_count]
    cases.sort(
        key=lambda row: (
            phase_names.index(row["phase"]),
            ("zero", "p50", "p99", "maximum").index(row["boundary"]),
        )
    )
    if len(cases) != 12:
        raise ValueError("expected twelve integration cases")

    payload = {
        "schema": "b2_b7_p023_d6_z_phase_primal_dual_input_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "basis": "z",
        "micro_blossom_weight_scale": MICRO_BLOSSOM_WEIGHT_SCALE,
        "source": {
            "superset_plan": str(PLAN.relative_to(ROOT)),
            "superset_plan_sha256": sha_path(PLAN),
            "fault_output_trace": str(FAULT_TRACE.relative_to(ROOT)),
            "fault_output_trace_sha256": sha_path(FAULT_TRACE),
            "phase_trace": str(PHASE_TRACE.relative_to(ROOT)),
            "phase_trace_sha256": sha_path(PHASE_TRACE),
            "steady_trace": str(STEADY_TRACE.relative_to(ROOT)),
            "steady_trace_sha256": sha_path(STEADY_TRACE),
        },
        "graph": superset_graph,
        "phase_banks": phase_banks,
        "phase_graphs": phase_graphs,
        "cases": cases,
    }
    payload["evidence_id"] = sha_bytes(compact(payload))
    OUTPUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "bytes": OUTPUT.stat().st_size,
                "evidence_id": payload["evidence_id"],
                "cases": len(cases),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
