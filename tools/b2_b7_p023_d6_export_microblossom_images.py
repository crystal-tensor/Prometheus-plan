#!/usr/bin/env python3
"""Export the six frozen d6 graph/rule pairs as loadable Micro Blossom JSON.

This is a zero-sample transform of the accepted explicit-reweight v2 protocol.
It does not observe a new stochastic shot and does not claim RTL equivalence.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import b2_b7_p023_d6_explicit_reweight_v2 as reweight  # noqa: E402


DEFAULT_OUTPUT_DIR = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_images_v1"
DEFAULT_MANIFEST = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_images_v1.json"
PINNED_MICRO_BLOSSOM_COMMIT = "a3530d9e58ff790dafc93d56c9a2769ceac84731"


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


def balanced_tree(leaves: int) -> dict[str, Any]:
    if leaves <= 0:
        raise ValueError("binary tree needs at least one leaf")
    nodes: list[dict[str, int | None]] = [
        {"p": None, "l": None, "r": None} for _ in range(leaves)
    ]
    active = list(range(leaves))
    while len(active) > 1:
        nxt: list[int] = []
        for offset in range(0, len(active), 2):
            if offset + 1 == len(active):
                nxt.append(active[offset])
                continue
            left, right = active[offset : offset + 2]
            parent = len(nodes)
            nodes.append({"p": None, "l": left, "r": right})
            nodes[left]["p"] = parent
            nodes[right]["p"] = parent
            nxt.append(parent)
        active = nxt
    if nodes[active[0]]["p"] is not None:
        raise ValueError("tree root unexpectedly has a parent")
    return {"nodes": nodes}


def nearest_virtual_distances(
    vertex_num: int,
    weighted_edges: list[dict[str, int]],
    virtual_vertices: list[int],
) -> list[int]:
    adjacency: list[list[tuple[int, int]]] = [[] for _ in range(vertex_num)]
    for edge in weighted_edges:
        left, right, weight = edge["l"], edge["r"], edge["w"]
        adjacency[left].append((right, weight))
        adjacency[right].append((left, weight))
    infinity = 1 << 62
    distances = [infinity] * vertex_num
    queue: list[tuple[int, int]] = []
    for vertex in virtual_vertices:
        distances[vertex] = 0
        heapq.heappush(queue, (0, vertex))
    while queue:
        distance, vertex = heapq.heappop(queue)
        if distance != distances[vertex]:
            continue
        for neighbor, weight in adjacency[vertex]:
            candidate = distance + weight
            if candidate < distances[neighbor]:
                distances[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    if any(value == infinity for value in distances):
        raise ValueError("exported graph has a component disconnected from every boundary")
    return distances


def grid_positions(vertex_num: int) -> list[dict[str, float]]:
    """Deterministic simulation layout; not placement/timing evidence."""
    width = max(1, math.ceil(math.sqrt(vertex_num)))
    return [
        {"i": float(index % width), "j": float(index // width), "t": 0.0}
        for index in range(vertex_num)
    ]


def phase_rows(windows: list[reweight.ExplicitWindow]) -> list[tuple[str, list[int], reweight.ExplicitWindow]]:
    pairs = [(window.graph_image_sha256, window.rule_image_sha256) for window in windows]
    counts = Counter(pairs)
    if len(counts) != 3 or counts[pairs[0]] != 1 or counts[pairs[-1]] != 1:
        raise ValueError(f"unexpected image pairing: {counts}")
    steady_pair, steady_count = counts.most_common(1)[0]
    if steady_count != len(windows) - 2 or any(pair != steady_pair for pair in pairs[1:-1]):
        raise ValueError("the frozen opening/steady/closing sequence changed")
    result = []
    for phase, pair in (("opening", pairs[0]), ("steady", steady_pair), ("closing", pairs[-1])):
        indices = [index for index, value in enumerate(pairs) if value == pair]
        result.append((phase, indices, windows[indices[0]]))
    return result


def export_image(
    basis: str,
    phase: str,
    window_indices: list[int],
    window: reweight.ExplicitWindow,
    half_weight_scale: int,
) -> dict[str, Any]:
    detector_vertices = 1 + max(
        vertex
        for edge in window.edges
        for vertex in (edge.node1, edge.node2)
        if vertex is not None
    )
    boundary_edges = [edge for edge in window.edges if edge.node2 is None]
    virtual_vertices = list(
        range(detector_vertices, detector_vertices + len(boundary_edges))
    )
    boundary_vertex_by_key = {
        edge.key: virtual for edge, virtual in zip(boundary_edges, virtual_vertices, strict=True)
    }
    edge_index_by_key = {edge.key: index for index, edge in enumerate(window.edges)}
    if len(edge_index_by_key) != len(window.edges):
        raise ValueError("duplicate edge key")
    weighted_edges: list[dict[str, int]] = []
    edge_metadata: list[dict[str, Any]] = []
    for edge_index, edge in enumerate(window.edges):
        right = edge.node2 if edge.node2 is not None else boundary_vertex_by_key[edge.key]
        # PyMatching's accepted representation doubles the integral half
        # weights.  Every base and replacement is therefore exactly even.
        # Store the common-factor-normalized integer here: dividing every
        # weight by two preserves all path orderings and ties, while keeping
        # the bus-wide maximum growth below its fixed 16-bit limit.
        weighted_edges.append({"l": edge.node1, "r": right, "w": edge.half_weight})
        edge_metadata.append(
            {
                "edge_index": edge_index,
                "key": list(edge.key),
                "fault_ids": sorted(edge.fault_ids),
                "base_half_weight": edge.half_weight,
                "base_even_weight": edge.even_weight,
                "boundary": edge.node2 is None,
            }
        )
    rules: list[dict[str, Any]] = []
    active_rules = 0
    for source, row in sorted(window.rules.items()):
        targets = []
        for target, half_weight in row:
            base = window.base_half_weights[target]
            active = half_weight < base
            active_rules += int(active)
            targets.append(
                {
                    "target_edge_index": edge_index_by_key[target],
                    "replacement_half_weight": half_weight,
                    "replacement_even_weight": 2 * half_weight,
                    "replacement_hardware_weight": half_weight,
                    "lowers_base": active,
                }
            )
        rules.append(
            {
                "source_edge_index": edge_index_by_key[source],
                "targets": targets,
            }
        )
    vertex_num = detector_vertices + len(virtual_vertices)
    vertex_max_growth = nearest_virtual_distances(
        vertex_num, weighted_edges, virtual_vertices
    )
    metadata = {
        "schema": "b2_b7_p023_d6_microblossom_image_v1",
        "scope": ["021/B7", "022/B2", "023"],
        "basis": basis,
        "phase": phase,
        "window_indices": window_indices,
        "window_multiplicity": len(window_indices),
        "source_graph_image_sha256": window.graph_image_sha256,
        "source_rule_image_sha256": window.rule_image_sha256,
        "half_weight_scale": half_weight_scale,
        "accepted_even_weight_scale": 2 * half_weight_scale,
        "hardware_weight_scale": half_weight_scale,
        "hardware_weight_normalization_divisor_from_accepted_even": 2,
        "micro_blossom_commit": PINNED_MICRO_BLOSSOM_COMMIT,
        "edge_index_bits_required": max(1, (len(window.edges) - 1).bit_length()),
        "stored_weight_bits_required": max(edge.half_weight for edge in window.edges).bit_length(),
        "detector_vertices": detector_vertices,
        "virtual_vertices": len(virtual_vertices),
        "edges": len(window.edges),
        "causal_edges": len(window.rules),
        "directed_rules": sum(len(row) for row in window.rules.values()),
        "active_lowering_rules": active_rules,
        "placement_positions_authoritative": False,
        "fault_ids_and_weights_by_edge": edge_metadata,
        "correlation_rules": rules,
    }
    graph = {
        "positions": grid_positions(vertex_num),
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
        "qec_image_metadata": metadata,
    }
    metadata["image_payload_sha256"] = sha_bytes(compact(graph))
    return graph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    protocol = reweight.read(reweight.DEFAULT_PROTOCOL)
    accepted = reweight.read(reweight.DEFAULT_RESULT)
    if accepted["classification"] != "sixteen_bit_explicit_reweight_semantic_pass_hardware_write_path_absent":
        raise ValueError("accepted v2 classification changed")
    scale = int(protocol["candidate_contract"]["half_weight_scale"])
    args.output_dir.mkdir(parents=True, exist_ok=True)
    image_rows: list[dict[str, Any]] = []
    for basis in protocol["fresh_holdout_contract"]["memory_bases"]:
        _, _, windows, structural = reweight.compile_basis(basis, scale)
        if structural["unique_graph_images"] != 3 or structural["unique_rule_images"] != 3:
            raise ValueError("frozen image cardinality changed")
        for phase, indices, window in phase_rows(windows):
            image = export_image(basis, phase, indices, window, scale)
            path = args.output_dir / f"{basis}_{phase}.json"
            # Keep the directly loadable images compact; the six pretty-printed
            # rule tables would otherwise add tens of megabytes without adding evidence.
            path.write_bytes(compact(image) + b"\n")
            meta = image["qec_image_metadata"]
            image_rows.append(
                {
                    "basis": basis,
                    "phase": phase,
                    "path": str(path.resolve().relative_to(ROOT)),
                    "file_sha256": sha_path(path),
                    "image_payload_sha256": meta["image_payload_sha256"],
                    "source_graph_image_sha256": meta["source_graph_image_sha256"],
                    "source_rule_image_sha256": meta["source_rule_image_sha256"],
                    "window_indices": indices,
                    "vertex_num": image["vertex_num"],
                    "edges": len(image["weighted_edges"]),
                    "virtual_vertices": len(image["virtual_vertices"]),
                    "directed_rules": meta["directed_rules"],
                    "active_lowering_rules": meta["active_lowering_rules"],
                    "maximum_hardware_weight": max(edge["w"] for edge in image["weighted_edges"]),
                    "maximum_accepted_even_weight": max(
                        edge["base_even_weight"]
                        for edge in meta["fault_ids_and_weights_by_edge"]
                    ),
                    "maximum_vertex_growth": max(image["vertex_max_growth"]),
                }
            )
    manifest = {
        "schema": "b2_b7_p023_d6_microblossom_images_manifest_v1",
        "scope": ["021/B7", "022/B2", "023"],
        "source_protocol": str(reweight.DEFAULT_PROTOCOL.relative_to(ROOT)),
        "source_protocol_sha256": reweight.sha_path(reweight.DEFAULT_PROTOCOL),
        "source_result": str(reweight.DEFAULT_RESULT.relative_to(ROOT)),
        "source_result_sha256": reweight.sha_path(reweight.DEFAULT_RESULT),
        "micro_blossom_commit": PINNED_MICRO_BLOSSOM_COMMIT,
        "fresh_stochastic_samples_observed": 0,
        "images": image_rows,
        "image_count": len(image_rows),
        "all_images_directly_loadable_single_graph_json": True,
        "placement_positions_authoritative": False,
        "rtl_replay_completed": False,
        "timing_credit": False,
    }
    manifest["evidence_id"] = sha_bytes(compact(manifest))
    args.manifest.write_text(canonical(manifest), encoding="utf-8")
    print(canonical(manifest), end="")


if __name__ == "__main__":
    main()
