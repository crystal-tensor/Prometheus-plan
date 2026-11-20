#!/usr/bin/env python3
"""Build a topology-safe opening/steady/closing superset mapping plan.

The plan is a zero-sample transform of the six frozen Micro Blossom images.
It does not claim that the current RTL implements phase masks or switching.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import b2_b7_p023_d6_explicit_reweight_v2 as reweight  # noqa: E402


MANIFEST = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_images_v1.json"
DEFAULT_PLAN = (
    ROOT / "benchmarks/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
)
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
PHASES = ("opening", "steady", "closing")


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def scalar(value: float) -> int | float:
    return int(value) if int(value) == value else float(value)


def detector_key(
    coordinates: dict[int, list[float]],
    global_detector: int,
    start_time: int,
    time_coordinate_index: int,
) -> tuple[Any, ...]:
    values = list(coordinates[global_detector])
    values[time_coordinate_index] -= start_time
    return ("detector", *(scalar(value) for value in values))


def boundary_key(detector: tuple[Any, ...]) -> tuple[Any, ...]:
    return ("boundary", *detector[1:])


def edge_key(
    left: tuple[Any, ...], right: tuple[Any, ...], boundary: bool
) -> tuple[Any, ...]:
    if boundary:
        return ("boundary_edge", *left[1:])
    ordered = sorted((left, right))
    return ("edge", ordered[0], ordered[1])


def json_key(value: tuple[Any, ...]) -> Any:
    return [json_key(item) if isinstance(item, tuple) else item for item in value]


def phase_index(phase: str, count: int) -> int:
    return {"opening": 0, "steady": 1, "closing": count - 1}[phase]


def active_rules(image: dict[str, Any]) -> list[dict[str, int]]:
    result = []
    for source in image["qec_image_metadata"]["correlation_rules"]:
        for target in source["targets"]:
            if target["lowers_base"]:
                result.append(
                    {
                        "source_local_edge": int(source["source_edge_index"]),
                        "target_local_edge": int(target["target_edge_index"]),
                        "replacement_weight": int(
                            target["replacement_hardware_weight"]
                        ),
                    }
                )
    return result


def distribution(values: list[int]) -> dict[str, int | float]:
    ordered = sorted(values)
    if not ordered:
        return {"count": 0, "minimum": 0, "maximum": 0, "mean": 0.0}
    return {
        "count": len(ordered),
        "minimum": ordered[0],
        "maximum": ordered[-1],
        "mean": sum(ordered) / len(ordered),
    }


def pairwise_rows(phase_sets: dict[str, set[int]]) -> list[dict[str, Any]]:
    result = []
    for left_index, left in enumerate(PHASES):
        for right in PHASES[left_index + 1 :]:
            intersection = phase_sets[left] & phase_sets[right]
            union = phase_sets[left] | phase_sets[right]
            result.append(
                {
                    "left": left,
                    "right": right,
                    "left_count": len(phase_sets[left]),
                    "right_count": len(phase_sets[right]),
                    "intersection": len(intersection),
                    "union": len(union),
                    "jaccard": len(intersection) / len(union),
                }
            )
    return result


def build_basis(
    basis: str,
    rows: dict[tuple[str, str], dict[str, Any]],
    half_weight_scale: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    circuit, compiled, windows, structural = reweight.compile_basis(
        basis, half_weight_scale
    )
    coordinates = circuit.get_detector_coordinates()
    source_protocol = reweight.admission_base.read(
        reweight.admission_base.DEFAULT_PROTOCOL
    )
    fault_protocol = reweight.admission_base.read(
        ROOT / source_protocol["frozen_inputs"]["fault_vector_protocol"]["path"]
    )
    online_protocol, _ = reweight.fault_base.load_upstream(fault_protocol)
    time_coordinate_index = int(
        online_protocol["window_contract"]["time_coordinate_index"]
    )
    vertex_keys: set[tuple[Any, ...]] = set()
    edge_keys: set[tuple[Any, ...]] = set()
    raw_phases: dict[str, dict[str, Any]] = {}
    for phase in PHASES:
        window_index = phase_index(phase, len(compiled.windows))
        baseline = compiled.windows[window_index]
        image_path = ROOT / rows[(basis, phase)]["path"]
        image = read(image_path)
        meta = image["qec_image_metadata"]
        detector_vertices = int(meta["detector_vertices"])
        if detector_vertices != len(baseline.detection_detectors):
            raise ValueError(
                f"{basis}/{phase}: detector mapping size {detector_vertices} != "
                f"{len(baseline.detection_detectors)}"
            )
        local_vertices: list[tuple[Any, ...]] = []
        for global_detector in baseline.detection_detectors.tolist():
            local_vertices.append(
                detector_key(
                    coordinates,
                    int(global_detector),
                    int(baseline.start_time),
                    time_coordinate_index,
                )
            )
        if len(set(local_vertices)) != len(local_vertices):
            raise ValueError(f"{basis}/{phase}: normalized detector coordinate collision")
        for edge in image["weighted_edges"]:
            left = int(edge["l"])
            right = int(edge["r"])
            if left >= detector_vertices:
                raise ValueError(f"{basis}/{phase}: left endpoint is virtual")
            if right >= detector_vertices:
                local_vertices.append(boundary_key(local_vertices[left]))
        if len(local_vertices) != int(image["vertex_num"]):
            raise ValueError(f"{basis}/{phase}: virtual vertex reconstruction mismatch")
        if len(set(local_vertices)) != len(local_vertices):
            raise ValueError(f"{basis}/{phase}: canonical vertex collision")
        local_edges: list[tuple[Any, ...]] = []
        for edge in image["weighted_edges"]:
            left_index = int(edge["l"])
            right_index = int(edge["r"])
            is_boundary = right_index >= detector_vertices
            local_edges.append(
                edge_key(
                    local_vertices[left_index],
                    local_vertices[right_index],
                    is_boundary,
                )
            )
        if len(set(local_edges)) != len(local_edges):
            raise ValueError(f"{basis}/{phase}: canonical edge collision")
        vertex_keys.update(local_vertices)
        edge_keys.update(local_edges)
        raw_phases[phase] = {
            "image": image,
            "image_path": image_path,
            "baseline": baseline,
            "local_vertices": local_vertices,
            "local_edges": local_edges,
            "active_rules": active_rules(image),
            "window": windows[window_index],
        }

    ordered_vertices = sorted(vertex_keys)
    ordered_edges = sorted(edge_keys)
    vertex_index = {value: index for index, value in enumerate(ordered_vertices)}
    edge_index = {value: index for index, value in enumerate(ordered_edges)}
    plan_phases = []
    phase_vertex_sets: dict[str, set[int]] = {}
    phase_edge_sets: dict[str, set[int]] = {}
    weight_by_phase_edge: dict[int, dict[str, int]] = {}
    replacement_by_pair: dict[tuple[int, int], dict[str, set[int]]] = {}
    for phase in PHASES:
        raw = raw_phases[phase]
        image = raw["image"]
        local_to_vertex = [vertex_index[value] for value in raw["local_vertices"]]
        local_to_edge = [edge_index[value] for value in raw["local_edges"]]
        active_vertex_indices = sorted(set(local_to_vertex))
        active_edge_indices = sorted(set(local_to_edge))
        if len(active_vertex_indices) != len(local_to_vertex):
            raise ValueError(f"{basis}/{phase}: non-injective vertex map")
        if len(active_edge_indices) != len(local_to_edge):
            raise ValueError(f"{basis}/{phase}: non-injective edge map")
        translated_rules = []
        for rule in raw["active_rules"]:
            source = local_to_edge[rule["source_local_edge"]]
            target = local_to_edge[rule["target_local_edge"]]
            replacement = rule["replacement_weight"]
            if source not in active_edge_indices or target not in active_edge_indices:
                raise ValueError(f"{basis}/{phase}: rule escapes phase edge mask")
            translated_rules.append(
                {
                    "source_edge": source,
                    "target_edge": target,
                    "replacement_weight": replacement,
                }
            )
            replacement_by_pair.setdefault((source, target), {}).setdefault(
                phase, set()
            ).add(replacement)
        for local, superset in enumerate(local_to_edge):
            weight_by_phase_edge.setdefault(superset, {})[phase] = int(
                image["weighted_edges"][local]["w"]
            )
        meta = image["qec_image_metadata"]
        fault_map = [
            row["fault_ids"] for row in meta["fault_ids_and_weights_by_edge"]
        ]
        plan_phases.append(
            {
                "phase": phase,
                "window_indices": meta["window_indices"],
                "source_image": str(raw["image_path"].relative_to(ROOT)),
                "source_image_sha256": sha_path(raw["image_path"]),
                "local_to_superset_vertex": local_to_vertex,
                "local_to_superset_edge": local_to_edge,
                "active_vertex_indices": active_vertex_indices,
                "active_edge_indices": active_edge_indices,
                "base_weights_local_edge_order": [
                    int(edge["w"]) for edge in image["weighted_edges"]
                ],
                "vertex_max_growth_local_order": [
                    int(value) for value in image["vertex_max_growth"]
                ],
                "active_resident_rules": translated_rules,
                "fault_ids_local_edge_order": fault_map,
                "fault_id_count": int(raw["window"].base_candidate.num_fault_ids),
                "commit_component_count": len(raw["baseline"].commit_component_ids),
                "detector_vertices": int(meta["detector_vertices"]),
                "virtual_vertices": int(meta["virtual_vertices"]),
                "edges": int(meta["edges"]),
            }
        )
        phase_vertex_sets[phase] = set(active_vertex_indices)
        phase_edge_sets[phase] = set(active_edge_indices)

    shared_weight_conflicts = [
        {
            "superset_edge": edge,
            "phase_weights": values,
        }
        for edge, values in sorted(weight_by_phase_edge.items())
        if len(values) > 1 and len(set(values.values())) > 1
    ]
    shared_rule_replacement_conflicts = []
    for (source, target), by_phase in sorted(replacement_by_pair.items()):
        values = {value for replacements in by_phase.values() for value in replacements}
        if len(by_phase) > 1 and len(values) > 1:
            shared_rule_replacement_conflicts.append(
                {
                    "source_edge": source,
                    "target_edge": target,
                    "phase_replacements": {
                        phase: sorted(replacements)
                        for phase, replacements in sorted(by_phase.items())
                    },
                }
            )

    plan = {
        "basis": basis,
        "superset_vertices": [json_key(value) for value in ordered_vertices],
        "superset_edges": [
            {
                "key": json_key(value),
                "left_vertex": vertex_index[
                    ("detector", *value[1:]) if value[0] == "boundary_edge" else value[1]
                ],
                "right_vertex": vertex_index[
                    ("boundary", *value[1:]) if value[0] == "boundary_edge" else value[2]
                ],
                "boundary": value[0] == "boundary_edge",
            }
            for value in ordered_edges
        ],
        "phases": plan_phases,
    }
    phase_vertex_counts = [len(values) for values in phase_vertex_sets.values()]
    phase_edge_counts = [len(values) for values in phase_edge_sets.values()]
    phase_rule_counts = [
        len(row["active_resident_rules"]) for row in plan_phases
    ]
    summary = {
        "basis": basis,
        "frozen_windows": len(windows),
        "unique_graph_images": structural["unique_graph_images"],
        "superset": {
            "vertices": len(ordered_vertices),
            "edges": len(ordered_edges),
            "phase_control_bits": 2,
            "three_phase_vertex_mask_bits": 3 * len(ordered_vertices),
            "three_phase_edge_mask_bits": 3 * len(ordered_edges),
            "vertices_vs_largest_phase_ratio": len(ordered_vertices)
            / max(phase_vertex_counts),
            "edges_vs_largest_phase_ratio": len(ordered_edges) / max(phase_edge_counts),
            "edges_vs_three_images_ratio": len(ordered_edges) / sum(phase_edge_counts),
        },
        "phase_rows": [
            {
                "phase": row["phase"],
                "vertices": len(row["active_vertex_indices"]),
                "detector_vertices": row["detector_vertices"],
                "virtual_vertices": row["virtual_vertices"],
                "edges": row["edges"],
                "active_rules": len(row["active_resident_rules"]),
                "fault_id_count": row["fault_id_count"],
                "baseline_commit_component_candidates": row[
                    "commit_component_count"
                ],
            }
            for row in plan_phases
        ],
        "vertex_overlap": pairwise_rows(phase_vertex_sets),
        "edge_overlap": pairwise_rows(phase_edge_sets),
        "shared_edges_with_phase_dependent_base_weight": len(
            shared_weight_conflicts
        ),
        "shared_rule_pairs_with_phase_dependent_replacement": len(
            shared_rule_replacement_conflicts
        ),
        "phase_active_rule_count": distribution(phase_rule_counts),
        "translated_rule_targets_all_active": True,
        "canonical_maps_injective": True,
        "shared_weight_conflict_digest": sha_bytes(compact(shared_weight_conflicts)),
        "shared_rule_conflict_digest": sha_bytes(
            compact(shared_rule_replacement_conflicts)
        ),
    }
    return plan, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    args = parser.parse_args()
    manifest = read(MANIFEST)
    rows = {
        (row["basis"], row["phase"]): row for row in manifest["images"]
    }
    if set(rows) != {(basis, phase) for basis in ("x", "z") for phase in PHASES}:
        raise ValueError("six frozen X/Z phase images are required")
    protocol = read(reweight.DEFAULT_PROTOCOL)
    half_weight_scale = int(protocol["candidate_contract"]["half_weight_scale"])
    basis_plans = []
    basis_summaries = []
    for basis in ("x", "z"):
        plan, summary = build_basis(basis, rows, half_weight_scale)
        basis_plans.append(plan)
        basis_summaries.append(summary)
    plan = {
        "schema": "b2_b7_p023_d6_microblossom_phase_superset_plan_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "canonical_phase_superset_mapping_plan_not_rtl",
        "source_manifest": str(MANIFEST.relative_to(ROOT)),
        "source_manifest_sha256": sha_path(MANIFEST),
        "fresh_stochastic_samples_observed": 0,
        "basis_plans": basis_plans,
    }
    plan["evidence_id"] = sha_bytes(compact(plan))
    args.plan.write_bytes(compact(plan) + b"\n")
    result = {
        "schema": "b2_b7_p023_d6_microblossom_phase_superset_result_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "phase_superset_mapping_feasible_phase_banked_state_required_no_rtl_credit",
        "source": {
            "plan": str(args.plan.relative_to(ROOT)),
            "plan_sha256": sha_path(args.plan),
            "plan_evidence_id": plan["evidence_id"],
            "image_manifest": str(MANIFEST.relative_to(ROOT)),
            "image_manifest_sha256": sha_path(MANIFEST),
        },
        "basis_rows": basis_summaries,
        "selected_route": {
            "name": "masked_superset_with_phase_banked_semantics",
            "why_not_mask_only": [
                "shared canonical edges can carry phase-dependent base weights",
                "shared source/target rule pairs can carry phase-dependent replacements",
                "fault/output maps and commit-component counts are phase-specific",
                "vertex_max_growth and tree participation must be phase-isolated",
            ],
            "required_invariants": [
                "the active masked subgraph is isomorphic to the frozen phase image",
                "inactive vertices and edges cannot grow, become tight, conflict, or report parity",
                "selectors are accepted only for active sources and can update only active targets",
                "phase-specific base weights, resident rules, growth bounds, and fault maps are selected atomically",
                "a phase change is legal only at a quiescent reset boundary with all transient state cleared",
                "complete correction and observable output equals the independent frozen phase image",
            ],
        },
        "acceptance": {
            "canonical_superset_mapping_constructed": True,
            "phase_maps_injective": True,
            "rule_targets_stay_inside_phase_masks": True,
            "masked_superset_rtl_implemented": False,
            "runtime_phase_switching_implemented": False,
            "complete_corrections_compared": False,
            "fpga_fmax_measured": False,
            "lut_bram_measured": False,
            "p99_le_1us": False,
            "miss_rate_le_1pct": False,
            "full_b2": False,
            "scalable_p023": False,
            "b7_resource_credit": 0,
        },
        "next_gate": "Implement one-basis masked-superset RTL with atomic phase-bank selection and reset-bound switching, then replay opening-to-steady-to-closing transitions against the three independent frozen images.",
    }
    result["evidence_id"] = sha_bytes(compact(result))
    args.result.write_text(canonical(result), encoding="utf-8")
    print(canonical(result), end="")


if __name__ == "__main__":
    main()
