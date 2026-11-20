#!/usr/bin/env python3
"""Audit the d6 phase-superset mapping plan against all six source images."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
MANIFEST = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_images_v1.json"
PHASES = ("opening", "steady", "closing")


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def evidence_id(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("evidence_id")
    return sha_bytes(compact(payload))


def require(checks: list[dict[str, Any]], label: str, condition: bool) -> None:
    checks.append({"label": label, "pass": bool(condition)})
    if not condition:
        raise AssertionError(label)


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


def main() -> None:
    checks: list[dict[str, Any]] = []
    plan = read(PLAN)
    result = read(RESULT)
    manifest = read(MANIFEST)
    require(checks, "plan canonical evidence id", plan["evidence_id"] == evidence_id(plan))
    require(
        checks, "result canonical evidence id", result["evidence_id"] == evidence_id(result)
    )
    require(checks, "strict plan scope", plan["scope"] == ["021/B7", "022/B2", "023"])
    require(
        checks, "strict result scope", result["scope"] == ["021/B7", "022/B2", "023"]
    )
    require(checks, "manifest hash", result["source"]["image_manifest_sha256"] == sha_path(MANIFEST))
    require(checks, "plan hash", result["source"]["plan_sha256"] == sha_path(PLAN))
    require(checks, "plan id binding", result["source"]["plan_evidence_id"] == plan["evidence_id"])
    require(checks, "zero fresh samples", plan["fresh_stochastic_samples_observed"] == 0)
    manifest_rows = {
        (row["basis"], row["phase"]): row for row in manifest["images"]
    }
    plan_rows = {row["basis"]: row for row in plan["basis_plans"]}
    result_rows = {row["basis"]: row for row in result["basis_rows"]}
    require(checks, "two basis plans", set(plan_rows) == {"x", "z"})
    require(checks, "two basis summaries", set(result_rows) == {"x", "z"})
    for basis in ("x", "z"):
        basis_plan = plan_rows[basis]
        summary = result_rows[basis]
        vertices = basis_plan["superset_vertices"]
        edges = basis_plan["superset_edges"]
        require(checks, f"{basis}: unique superset vertices", len({compact(v) for v in vertices}) == len(vertices))
        require(checks, f"{basis}: unique superset edges", len({compact(v["key"]) for v in edges}) == len(edges))
        require(
            checks,
            f"{basis}: superset endpoints in range",
            all(
                0 <= edge["left_vertex"] < len(vertices)
                and 0 <= edge["right_vertex"] < len(vertices)
                for edge in edges
            ),
        )
        phases = {row["phase"]: row for row in basis_plan["phases"]}
        require(checks, f"{basis}: three phase plans", set(phases) == set(PHASES))
        vertex_sets: dict[str, set[int]] = {}
        edge_sets: dict[str, set[int]] = {}
        weights_by_edge: dict[int, dict[str, int]] = {}
        replacements_by_pair: dict[tuple[int, int], dict[str, set[int]]] = {}
        for phase in PHASES:
            row = phases[phase]
            source_path = ROOT / row["source_image"]
            source = read(source_path)
            meta = source["qec_image_metadata"]
            vertex_map = row["local_to_superset_vertex"]
            edge_map = row["local_to_superset_edge"]
            require(checks, f"{basis}/{phase}: source hash", row["source_image_sha256"] == sha_path(source_path))
            require(checks, f"{basis}/{phase}: manifest path", manifest_rows[(basis, phase)]["path"] == row["source_image"])
            require(checks, f"{basis}/{phase}: vertex map length", len(vertex_map) == source["vertex_num"])
            require(checks, f"{basis}/{phase}: edge map length", len(edge_map) == len(source["weighted_edges"]))
            require(checks, f"{basis}/{phase}: injective vertex map", len(set(vertex_map)) == len(vertex_map))
            require(checks, f"{basis}/{phase}: injective edge map", len(set(edge_map)) == len(edge_map))
            require(checks, f"{basis}/{phase}: vertex mask exact", row["active_vertex_indices"] == sorted(vertex_map))
            require(checks, f"{basis}/{phase}: edge mask exact", row["active_edge_indices"] == sorted(edge_map))
            require(
                checks,
                f"{basis}/{phase}: base weight bank exact",
                row["base_weights_local_edge_order"]
                == [edge["w"] for edge in source["weighted_edges"]],
            )
            require(
                checks,
                f"{basis}/{phase}: growth bank exact",
                row["vertex_max_growth_local_order"] == source["vertex_max_growth"],
            )
            require(
                checks,
                f"{basis}/{phase}: fault map exact",
                row["fault_ids_local_edge_order"]
                == [item["fault_ids"] for item in meta["fault_ids_and_weights_by_edge"]],
            )
            require(
                checks,
                f"{basis}/{phase}: fault dimension exact",
                row["fault_id_count"]
                == 1
                + max(
                    fault
                    for item in row["fault_ids_local_edge_order"]
                    for fault in item
                ),
            )
            endpoint_pass = True
            for local, source_edge in enumerate(source["weighted_edges"]):
                superset_edge = edges[edge_map[local]]
                mapped = {
                    vertex_map[source_edge["l"]],
                    vertex_map[source_edge["r"]],
                }
                expected = {
                    superset_edge["left_vertex"],
                    superset_edge["right_vertex"],
                }
                endpoint_pass &= mapped == expected
                endpoint_pass &= superset_edge["boundary"] == (
                    source_edge["r"] >= meta["detector_vertices"]
                )
                weights_by_edge.setdefault(edge_map[local], {})[phase] = int(
                    source_edge["w"]
                )
            require(checks, f"{basis}/{phase}: endpoint isomorphism", endpoint_pass)
            translated_rules = []
            for source_rule in meta["correlation_rules"]:
                for target in source_rule["targets"]:
                    if not target["lowers_base"]:
                        continue
                    translated = {
                        "source_edge": edge_map[source_rule["source_edge_index"]],
                        "target_edge": edge_map[target["target_edge_index"]],
                        "replacement_weight": target[
                            "replacement_hardware_weight"
                        ],
                    }
                    translated_rules.append(translated)
                    pair = (translated["source_edge"], translated["target_edge"])
                    replacements_by_pair.setdefault(pair, {}).setdefault(
                        phase, set()
                    ).add(translated["replacement_weight"])
            require(
                checks,
                f"{basis}/{phase}: translated rules exact",
                row["active_resident_rules"] == translated_rules,
            )
            active_edges = set(row["active_edge_indices"])
            require(
                checks,
                f"{basis}/{phase}: rules stay in mask",
                all(
                    rule["source_edge"] in active_edges
                    and rule["target_edge"] in active_edges
                    for rule in row["active_resident_rules"]
                ),
            )
            vertex_sets[phase] = set(row["active_vertex_indices"])
            edge_sets[phase] = active_edges
        require(checks, f"{basis}: vertex overlap exact", summary["vertex_overlap"] == pairwise_rows(vertex_sets))
        require(checks, f"{basis}: edge overlap exact", summary["edge_overlap"] == pairwise_rows(edge_sets))
        require(checks, f"{basis}: superset vertex count", summary["superset"]["vertices"] == len(vertices))
        require(checks, f"{basis}: superset edge count", summary["superset"]["edges"] == len(edges))
        weight_conflicts = [
            {"superset_edge": edge, "phase_weights": values}
            for edge, values in sorted(weights_by_edge.items())
            if len(values) > 1 and len(set(values.values())) > 1
        ]
        rule_conflicts = []
        for (source, target), by_phase in sorted(replacements_by_pair.items()):
            values = {value for phase_values in by_phase.values() for value in phase_values}
            if len(by_phase) > 1 and len(values) > 1:
                rule_conflicts.append(
                    {
                        "source_edge": source,
                        "target_edge": target,
                        "phase_replacements": {
                            phase: sorted(phase_values)
                            for phase, phase_values in sorted(by_phase.items())
                        },
                    }
                )
        require(
            checks,
            f"{basis}: weight conflict count",
            summary["shared_edges_with_phase_dependent_base_weight"]
            == len(weight_conflicts),
        )
        require(
            checks,
            f"{basis}: weight conflict digest",
            summary["shared_weight_conflict_digest"]
            == sha_bytes(compact(weight_conflicts)),
        )
        require(
            checks,
            f"{basis}: rule conflict count",
            summary["shared_rule_pairs_with_phase_dependent_replacement"]
            == len(rule_conflicts),
        )
        require(
            checks,
            f"{basis}: rule conflict digest",
            summary["shared_rule_conflict_digest"]
            == sha_bytes(compact(rule_conflicts)),
        )
    acceptance = result["acceptance"]
    require(checks, "superset mapping credit", acceptance["canonical_superset_mapping_constructed"] is True)
    require(checks, "injective mapping credit", acceptance["phase_maps_injective"] is True)
    require(checks, "rule mask credit", acceptance["rule_targets_stay_inside_phase_masks"] is True)
    for label in (
        "masked_superset_rtl_implemented",
        "runtime_phase_switching_implemented",
        "complete_corrections_compared",
        "fpga_fmax_measured",
        "lut_bram_measured",
        "p99_le_1us",
        "miss_rate_le_1pct",
        "full_b2",
        "scalable_p023",
    ):
        require(checks, f"closed gate: {label}", acceptance[label] is False)
    require(checks, "zero B7 credit", acceptance["b7_resource_credit"] == 0)
    output = {
        "classification": "phase_superset_plan_audit_pass",
        "checks_total": len(checks),
        "checks_passed": sum(item["pass"] for item in checks),
        "checks": checks,
    }
    print(json.dumps(output, indent=2, sort_keys=True) + "\n", end="")


if __name__ == "__main__":
    main()
