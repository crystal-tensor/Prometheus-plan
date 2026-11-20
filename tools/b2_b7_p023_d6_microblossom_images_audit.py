#!/usr/bin/env python3
"""Independently audit the six frozen d6 Micro Blossom graph images.

The auditor deliberately does not import the exporter.  It validates the
serialized evidence and recomputes graph invariants from the JSON payloads.
It observes no stochastic samples and gives no RTL or timing credit.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import heapq
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_images_v1.json"
EXPECTED_SOURCE_HASHES = {
    ("x", "opening"): (
        "6ed6a88d8c6da4f7bf4ad3e0c14d824cad034dac2bbf74f82f8f0750d60ac9ae",
        "079a4a0ab906ebd88c8899bae09747de8449a06fe1a36017bfbab92fadb52cbb",
    ),
    ("x", "steady"): (
        "575d34ea8c4d69e497b585a886e69e9464ccc70dca6d984fd115b663d10cac20",
        "52c9f1b1636c6290536ca911679abbbbbef57b1e848c8df37c9956ef5ceb2375",
    ),
    ("x", "closing"): (
        "f5c750c5df5f49ad30d3ad956c9381596018895ae3fe02b2c66ab3007d08c150",
        "a440e26e866e23751f07d3c86313958acc26e176038decad37b40cea8a2adde0",
    ),
    ("z", "opening"): (
        "1e14346c208d36af1709334ae1ff567e1edfe2758435ae658b33f4a5fb02ecc0",
        "1156c15a1181208774ad9892b7a421dbf5385702a27f982c2e159ff53e46c37f",
    ),
    ("z", "steady"): (
        "d4762a9915ba8b64991d18b5b06841bc79d69992b79d9c9acde1caf033b7812c",
        "52c9f1b1636c6290536ca911679abbbbbef57b1e848c8df37c9956ef5ceb2375",
    ),
    ("z", "closing"): (
        "f3430153c7dedcd83328f4560a05ac3b48eca795b3816532bc25341614e4080e",
        "bc4506b8af20d30304190cbc0bb43c072aaa4f99f5d7062936cdaf0eb4a53d86",
    ),
}
EXPECTED_INDICES = {
    "opening": [0],
    "steady": list(range(1, 163)),
    "closing": [163],
}
REQUIRED_GRAPH_FIELDS = {
    "positions",
    "vertex_num",
    "weighted_edges",
    "virtual_vertices",
    "vertex_binary_tree",
    "edge_binary_tree",
    "vertex_edge_binary_tree",
    "vertex_max_growth",
    "offloading",
    "layer_fusion",
    "parity_reporters",
    "qec_image_metadata",
}


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def audit_tree(tree: Any, leaves: int, label: str) -> None:
    require(isinstance(tree, dict) and set(tree) == {"nodes"}, f"{label}: shape")
    nodes = tree["nodes"]
    require(leaves > 0 and len(nodes) == 2 * leaves - 1, f"{label}: node count")
    roots: list[int] = []
    for index, node in enumerate(nodes):
        require(set(node) == {"l", "p", "r"}, f"{label}: node {index} fields")
        parent, left, right = node["p"], node["l"], node["r"]
        if index < leaves:
            require(left is None and right is None, f"{label}: leaf {index} has children")
        else:
            require(
                isinstance(left, int) and isinstance(right, int),
                f"{label}: internal {index} lacks children",
            )
            require(0 <= left < index and 0 <= right < index and left != right,
                    f"{label}: internal {index} child indices")
            require(nodes[left]["p"] == index and nodes[right]["p"] == index,
                    f"{label}: child parent mismatch at {index}")
        if parent is None:
            roots.append(index)
        else:
            require(isinstance(parent, int) and index < parent < len(nodes),
                    f"{label}: parent index at {index}")
    require(len(roots) == 1, f"{label}: expected one root")
    seen: set[int] = set()
    stack = [roots[0]]
    while stack:
        index = stack.pop()
        require(index not in seen, f"{label}: cycle/shared child at {index}")
        seen.add(index)
        node = nodes[index]
        if node["l"] is not None:
            stack.extend((node["l"], node["r"]))
    require(len(seen) == len(nodes), f"{label}: unreachable nodes")
    require(set(range(leaves)).issubset(seen), f"{label}: unreachable leaves")


def nearest_virtual_distances(
    vertex_num: int, edges: list[dict[str, int]], virtuals: list[int]
) -> list[int]:
    adjacency: list[list[tuple[int, int]]] = [[] for _ in range(vertex_num)]
    for edge in edges:
        adjacency[edge["l"]].append((edge["r"], edge["w"]))
        adjacency[edge["r"]].append((edge["l"], edge["w"]))
    infinity = 1 << 62
    distances = [infinity] * vertex_num
    queue: list[tuple[int, int]] = []
    for vertex in virtuals:
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
    require(all(value != infinity for value in distances), "component lacks virtual boundary")
    return distances


def audit_image(path: Path, row: dict[str, Any]) -> dict[str, Any]:
    require(path.is_file(), f"missing image: {path}")
    require(sha_path(path) == row["file_sha256"], f"{path.name}: file hash")
    image = json.loads(path.read_text(encoding="utf-8"))
    require(set(image) == REQUIRED_GRAPH_FIELDS, f"{path.name}: graph fields")
    metadata = image["qec_image_metadata"]
    basis, phase = metadata["basis"], metadata["phase"]
    require((basis, phase) in EXPECTED_SOURCE_HASHES, f"{path.name}: basis/phase")
    require(path.name == f"{basis}_{phase}.json", f"{path.name}: filename")
    require(row["basis"] == basis and row["phase"] == phase, f"{path.name}: manifest key")
    require(metadata["window_indices"] == EXPECTED_INDICES[phase], f"{path.name}: indices")
    require(metadata["window_multiplicity"] == len(EXPECTED_INDICES[phase]),
            f"{path.name}: multiplicity")
    require(row["window_indices"] == EXPECTED_INDICES[phase], f"{path.name}: row indices")
    source_graph, source_rules = EXPECTED_SOURCE_HASHES[(basis, phase)]
    require(metadata["source_graph_image_sha256"] == source_graph,
            f"{path.name}: source graph hash")
    require(metadata["source_rule_image_sha256"] == source_rules,
            f"{path.name}: source rule hash")
    require(row["source_graph_image_sha256"] == source_graph,
            f"{path.name}: manifest source graph hash")
    require(row["source_rule_image_sha256"] == source_rules,
            f"{path.name}: manifest source rule hash")
    require(metadata["hardware_weight_normalization_divisor_from_accepted_even"] == 2,
            f"{path.name}: normalization divisor")
    require(metadata["accepted_even_weight_scale"] == 2 * metadata["hardware_weight_scale"],
            f"{path.name}: normalized scale")

    payload = copy.deepcopy(image)
    embedded_payload_hash = payload["qec_image_metadata"].pop("image_payload_sha256")
    require(sha_bytes(compact(payload)) == embedded_payload_hash,
            f"{path.name}: payload hash")
    require(row["image_payload_sha256"] == embedded_payload_hash,
            f"{path.name}: manifest payload hash")

    vertex_num = image["vertex_num"]
    edges = image["weighted_edges"]
    virtuals = image["virtual_vertices"]
    require(isinstance(vertex_num, int) and vertex_num > 0, f"{path.name}: vertex_num")
    require(len(image["positions"]) == vertex_num, f"{path.name}: positions")
    require(len(image["vertex_max_growth"]) == vertex_num, f"{path.name}: growth length")
    require(len(edges) > 0 and len(edges) < (1 << 15), f"{path.name}: edge index width")
    require(len(set(virtuals)) == len(virtuals), f"{path.name}: duplicate virtual")
    require(all(isinstance(v, int) and 0 <= v < vertex_num for v in virtuals),
            f"{path.name}: virtual range")
    virtual_set = set(virtuals)
    for edge_index, edge in enumerate(edges):
        require(set(edge) == {"l", "r", "w"}, f"{path.name}: edge {edge_index} fields")
        require(0 <= edge["l"] < vertex_num and 0 <= edge["r"] < vertex_num,
                f"{path.name}: edge {edge_index} endpoint")
        require(isinstance(edge["w"], int) and 0 < edge["w"] <= 65535,
                f"{path.name}: edge {edge_index} weight")

    edge_metadata = metadata["fault_ids_and_weights_by_edge"]
    require(len(edge_metadata) == len(edges), f"{path.name}: edge metadata length")
    boundary_virtuals: list[int] = []
    base_half_weights: list[int] = []
    for edge_index, (edge, edge_meta) in enumerate(zip(edges, edge_metadata, strict=True)):
        require(edge_meta["edge_index"] == edge_index, f"{path.name}: edge metadata index")
        require(edge_meta["base_half_weight"] == edge["w"], f"{path.name}: hardware weight")
        require(edge_meta["base_even_weight"] == 2 * edge_meta["base_half_weight"],
                f"{path.name}: half/even weight")
        require(edge_meta["fault_ids"] == sorted(set(edge_meta["fault_ids"])),
                f"{path.name}: fault ids")
        endpoints = {edge["l"], edge["r"]}
        boundary_endpoints = endpoints & virtual_set
        require(bool(boundary_endpoints) == edge_meta["boundary"],
                f"{path.name}: boundary flag at edge {edge_index}")
        require(len(boundary_endpoints) <= 1, f"{path.name}: virtual-to-virtual edge")
        if boundary_endpoints:
            boundary_virtuals.extend(boundary_endpoints)
        base_half_weights.append(edge_meta["base_half_weight"])
    require(sorted(boundary_virtuals) == sorted(virtuals),
            f"{path.name}: boundary vertices not one-to-one")

    rules = metadata["correlation_rules"]
    require(len(rules) == metadata["causal_edges"], f"{path.name}: causal count")
    seen_sources: set[int] = set()
    directed = active = 0
    for rule in rules:
        source = rule["source_edge_index"]
        require(isinstance(source, int) and 0 <= source < len(edges), f"{path.name}: source index")
        require(source not in seen_sources, f"{path.name}: duplicate source")
        seen_sources.add(source)
        for target in rule["targets"]:
            target_index = target["target_edge_index"]
            half = target["replacement_half_weight"]
            even = target["replacement_even_weight"]
            require(isinstance(target_index, int) and 0 <= target_index < len(edges),
                    f"{path.name}: target index")
            # Correlated p_implied may be exactly 0.5, whose log-odds and
            # quantized replacement weight are both zero.  The accepted v2
            # evidence explicitly records implied_even_weight_min == 0.
            require(isinstance(half, int) and half >= 0 and even == 2 * half and even <= 65535,
                    f"{path.name}: replacement weight")
            require(target["replacement_hardware_weight"] == half,
                    f"{path.name}: replacement hardware weight")
            lowers = half < base_half_weights[target_index]
            require(target["lowers_base"] is lowers, f"{path.name}: lowers_base")
            directed += 1
            active += int(lowers)
    require(directed == metadata["directed_rules"] == row["directed_rules"],
            f"{path.name}: directed count")
    require(active == metadata["active_lowering_rules"] == row["active_lowering_rules"],
            f"{path.name}: active count")

    audit_tree(image["vertex_binary_tree"], vertex_num, f"{path.name}: vertex tree")
    audit_tree(image["edge_binary_tree"], len(edges), f"{path.name}: edge tree")
    audit_tree(image["vertex_edge_binary_tree"], vertex_num + len(edges),
               f"{path.name}: combined tree")
    recomputed_growth = nearest_virtual_distances(vertex_num, edges, virtuals)
    require(recomputed_growth == image["vertex_max_growth"], f"{path.name}: growth distances")
    require(max(recomputed_growth) <= 65535, f"{path.name}: 16-bit maximum growth")

    require(row["vertex_num"] == vertex_num, f"{path.name}: manifest vertices")
    require(row["edges"] == len(edges), f"{path.name}: manifest edges")
    require(row["virtual_vertices"] == len(virtuals), f"{path.name}: manifest virtuals")
    require(row["maximum_hardware_weight"] == max(edge["w"] for edge in edges),
            f"{path.name}: manifest max hardware weight")
    require(row["maximum_accepted_even_weight"] ==
            max(edge["base_even_weight"] for edge in edge_metadata),
            f"{path.name}: manifest max accepted weight")
    require(row["maximum_vertex_growth"] == max(recomputed_growth),
            f"{path.name}: manifest max growth")
    require(metadata["placement_positions_authoritative"] is False,
            f"{path.name}: placement claim")
    return {
        "basis": basis,
        "phase": phase,
        "vertices": vertex_num,
        "edges": len(edges),
        "directed_rules": directed,
        "active_lowering_rules": active,
        "maximum_hardware_weight": max(edge["w"] for edge in edges),
        "maximum_accepted_even_weight": max(
            edge["base_even_weight"] for edge in edge_metadata
        ),
        "maximum_vertex_growth": max(recomputed_growth),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    evidence_copy = copy.deepcopy(manifest)
    evidence_id = evidence_copy.pop("evidence_id")
    require(sha_bytes(compact(evidence_copy)) == evidence_id, "manifest evidence_id")
    require(manifest["schema"] == "b2_b7_p023_d6_microblossom_images_manifest_v1",
            "manifest schema")
    require(manifest["scope"] == ["021/B7", "022/B2", "023"], "scope")
    require(manifest["fresh_stochastic_samples_observed"] == 0, "fresh samples claim")
    require(manifest["rtl_replay_completed"] is False, "RTL claim")
    require(manifest["timing_credit"] is False, "timing claim")
    require(manifest["placement_positions_authoritative"] is False, "placement claim")
    require(manifest["image_count"] == 6 == len(manifest["images"]), "image count")
    source_protocol = ROOT / manifest["source_protocol"]
    source_result = ROOT / manifest["source_result"]
    require(sha_path(source_protocol) == manifest["source_protocol_sha256"], "protocol hash")
    require(sha_path(source_result) == manifest["source_result_sha256"], "result hash")

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in manifest["images"]:
        key = (row["basis"], row["phase"])
        require(key not in seen, f"duplicate manifest image: {key}")
        seen.add(key)
        rows.append(audit_image(ROOT / row["path"], row))
    require(seen == set(EXPECTED_SOURCE_HASHES), "six basis/phase images")
    print(json.dumps({
        "classification": "six_d6_microblossom_images_independently_audited",
        "evidence_id": evidence_id,
        "fresh_stochastic_samples_observed": 0,
        "rtl_replay_completed": False,
        "timing_credit": False,
        "images": rows,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
