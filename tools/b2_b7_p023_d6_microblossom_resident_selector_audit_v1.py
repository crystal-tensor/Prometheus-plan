#!/usr/bin/env python3
"""Independently audit the d=6 resident-rule selector RTL evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_resident_selector_rtl_v1.json"
ROW = re.compile(
    r"RESIDENT_SELECTOR_BATCH_PASS name=(x|z)/(maximum|p50|p99|zero) "
    r"selectors=(\d+) updates=(\d+) checked_edges=(\d+) "
    r"axi_write_span_slow_cycles=(\d+)"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def require(condition: bool, label: str, checks: list[dict[str, Any]]) -> None:
    checks.append({"label": label, "pass": bool(condition)})
    if not condition:
        raise AssertionError(label)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    args = parser.parse_args()
    result = json.loads(args.result.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    without_id = dict(result)
    evidence_id = without_id.pop("evidence_id")
    require(
        evidence_id == hashlib.sha256(compact(without_id)).hexdigest(),
        "canonical evidence id",
        checks,
    )
    require(result["scope"] == ["021/B7", "022/B2", "023"], "strict scope", checks)

    source = result["source"]
    for key in (
        "batch_trace",
        "architecture_routes",
        "x_steady_image",
        "z_steady_image",
        "simulation_transcript",
        "simulation_harness",
    ):
        path = ROOT / source[key]
        require(path.is_file(), f"{key}: exists", checks)
        require(sha(path) == source[f"{key}_sha256"], f"{key}: hash", checks)

    implementation = result["implementation"]
    for key in ("prerequisite_dynamic_weight_patch", "resident_selector_patch"):
        path = ROOT / implementation[key]
        require(path.is_file(), f"{key}: exists", checks)
        require(sha(path) == implementation[f"{key}_sha256"], f"{key}: hash", checks)
    require(
        implementation["prerequisite_dynamic_weight_patch_sha256"]
        == "990beb9fc86329960a6eef88b9f88b601f5807f0e2ae2abd71acc0d3671e27d5",
        "published dynamic patch unchanged",
        checks,
    )

    selector_patch = (ROOT / implementation["resident_selector_patch"]).read_text(encoding="utf-8")
    harness = (ROOT / source["simulation_harness"]).read_text(encoding="utf-8")
    for needle in (
        "residentWeightRules",
        "weightUpdateIsRuleSelector",
        "SizeMapping(base = 16 KiB, size = 4 KiB)",
        "residentSelectorReplacement < fetchState.weight",
        "stateWriteRuleSelector",
    ):
        require(needle in selector_patch, f"selector patch semantic: {needle}", checks)
    require("driver.write_64(0x4000" in harness, "harness uses selector AXI window", checks)
    require(
        "math.min(reconstructed(targetEdgeIndex), replacementWeight)" in harness,
        "harness independently reconstructs min semantics",
        checks,
    )

    x_image = json.loads((ROOT / source["x_steady_image"]).read_text(encoding="utf-8"))
    z_image = json.loads((ROOT / source["z_steady_image"]).read_text(encoding="utf-8"))
    require(
        x_image["weighted_edges"] == z_image["weighted_edges"],
        "X/Z steady graph equality",
        checks,
    )

    def rules(image: dict[str, Any]) -> tuple[dict[int, list[tuple[int, int]]], int, int]:
        table: dict[int, list[tuple[int, int]]] = {}
        total = 0
        active = 0
        all_even = True
        all_exact = True
        for source_row in image["qec_image_metadata"]["correlation_rules"]:
            source_index = int(source_row["source_edge_index"])
            for target in source_row["targets"]:
                total += 1
                even = int(target["replacement_even_weight"])
                half = int(target["replacement_half_weight"])
                hardware = int(target["replacement_hardware_weight"])
                all_even = all_even and even % 2 == 0
                all_exact = all_exact and even // 2 == half == hardware
                if target["lowers_base"]:
                    active += 1
                    table.setdefault(source_index, []).append(
                        (int(target["target_edge_index"]), hardware)
                    )
        require(all_even, "all rule weights are even before normalization", checks)
        require(all_exact, "all rule weights normalize exactly", checks)
        return table, total, active

    x_rules, x_total, x_active = rules(x_image)
    z_rules, z_total, z_active = rules(z_image)
    require(x_rules == z_rules, "X/Z resident rules equal", checks)
    require((x_total, x_active) == (15610, 15606), "X rule counts", checks)
    require((z_total, z_active) == (15610, 15606), "Z rule counts", checks)
    require(
        implementation["active_steady_rules"] == x_active
        and implementation["directed_steady_rules_including_nonlowering"] == x_total,
        "result rule counts",
        checks,
    )

    transcript = (ROOT / source["simulation_transcript"]).read_text(encoding="utf-8")
    observed = {
        (basis, boundary): {
            "selectors": int(selectors),
            "updates": int(updates),
            "checked_edges": int(edges),
            "cycles": int(cycles),
        }
        for basis, boundary, selectors, updates, edges, cycles in ROW.findall(transcript)
    }
    require(len(observed) == 8, "eight unique transcript rows", checks)
    require("mismatches=0" in transcript and "simulation=PASS" in transcript,
            "transcript pass boundary", checks)

    trace = json.loads((ROOT / source["batch_trace"]).read_text(encoding="utf-8"))
    require(trace["evidence_id"] == source["batch_trace_evidence_id"],
            "trace evidence binding", checks)
    routes = json.loads((ROOT / source["architecture_routes"]).read_text(encoding="utf-8"))
    require(routes["evidence_id"] == source["architecture_routes_evidence_id"],
            "route evidence binding", checks)
    trace_rows = {row["basis"]: row for row in trace["basis_rows"]}
    route_rows = {row["basis"]: row for row in routes["basis_rows"]}
    for basis in ("x", "z"):
        selector_route = next(
            route for route in route_rows[basis]["routes"]
            if route["route"] == "resident_rule_causal_selector"
        )
        require(
            int(trace_rows[basis]["selected_edges"]["p99"]) == 13
            and selector_route["p99_commands"] == 13
            and selector_route["p99_slow_cycles"] == 26,
            f"{basis}: route projection bound to accepted trace",
            checks,
        )
    result_rows = {
        (row["basis"], row["boundary"]): row
        for row in result["representative_rtl_replay"]["rows"]
    }
    require(len(result_rows) == 8, "eight unique result rows", checks)
    base = [int(edge["w"]) for edge in x_image["weighted_edges"]]
    for basis in ("x", "z"):
        for boundary in ("zero", "p50", "p99", "maximum"):
            representative = trace_rows[basis]["representative_batches"][boundary]
            selected = [int(value) for value in representative["selected_edge_indices"]]
            expected = {int(edge): int(weight) for edge, weight in representative["updates"]}
            reconstructed = list(base)
            for source_index in selected:
                for target_index, replacement in x_rules.get(source_index, []):
                    reconstructed[target_index] = min(reconstructed[target_index], replacement)
            reconstructed_updates = {
                index: weight
                for index, weight in enumerate(reconstructed)
                if weight != base[index]
            }
            require(
                reconstructed_updates == expected,
                f"{basis}/{boundary}: independent rule reconstruction",
                checks,
            )
            measured = observed[(basis, boundary)]
            row = result_rows[(basis, boundary)]
            require(measured["selectors"] == len(selected) == row["selected_source_edges"],
                    f"{basis}/{boundary}: selector count", checks)
            require(measured["updates"] == len(expected) == row["expected_weight_updates"],
                    f"{basis}/{boundary}: update count", checks)
            require(measured["checked_edges"] == len(base) == row["checked_edges"],
                    f"{basis}/{boundary}: edge coverage", checks)
            require(measured["cycles"] == 2 * len(selected)
                    == row["axi_write_span_slow_cycles"],
                    f"{basis}/{boundary}: cycle span", checks)
            require(row["pass"] is True, f"{basis}/{boundary}: pass flag", checks)

    replay = result["representative_rtl_replay"]
    require(
        replay["batches_run"] == replay["batches_passed"] == 8
        and replay["batches_failed"] == 0,
        "all replay batches pass",
        checks,
    )
    require(
        replay["full_edge_state_checks"]
        == replay["full_edge_state_checks_passed"]
        == 8 * len(base)
        and replay["mismatches"] == 0,
        "full edge-state replay coverage",
        checks,
    )

    reduction = result["transport_reduction"]
    require(reduction["measured_slow_cycles_per_selector_command"] == 2,
            "two-cycle selector contract", checks)
    x_p99 = result_rows[("x", "p99")]["axi_write_span_slow_cycles"]
    z_p99 = result_rows[("z", "p99")]["axi_write_span_slow_cycles"]
    require(x_p99 == 22 and z_p99 == 24, "representative p99 spans", checks)
    require(
        math.isclose(reduction["x_representative_p99"]["reduction_factor"], 204 / 22)
        and math.isclose(reduction["z_representative_p99"]["reduction_factor"], 206 / 24),
        "representative reduction arithmetic",
        checks,
    )
    projection = reduction["accepted_distribution_projection"]
    require(
        projection["x_p99_selected_sources"] == 13
        and projection["z_p99_selected_sources"] == 13
        and projection["x_p99_update_only_slow_cycles"] == 26
        and projection["z_p99_update_only_slow_cycles"] == 26,
        "accepted-distribution projection",
        checks,
    )
    require(
        projection["classification"] == "projected_from_full_accepted_trace_not_full_rtl_replay",
        "projection boundary",
        checks,
    )

    generation = result["rtl_generation"]
    require(
        generation["elaboration_pass"]
        and generation["verilog_generation_pass"]
        and generation["iverilog_compile_pass"],
        "RTL generation and compile pass",
        checks,
    )
    acceptance = result["acceptance"]
    require(
        acceptance["correctness_veto_for_eight_steady_representatives"] is True,
        "representative correctness credit",
        checks,
    )
    require(
        acceptance["all_accepted_window_batches_replayed_in_rtl"] is False
        and acceptance["opening_closing_selector_replay"] is False
        and acceptance["rtl_corrections_compared"] is False,
        "functional scope boundary",
        checks,
    )
    require(
        acceptance["fpga_fmax_measured"] is False
        and acceptance["lut_bram_measured"] is False
        and acceptance["full_update_plus_decode_p99_cycles_measured"] is False
        and acceptance["p99_le_1us"] is False
        and acceptance["miss_rate_le_1pct"] is False,
        "timing and resource boundary",
        checks,
    )
    require(
        acceptance["full_b2"] is False
        and acceptance["scalable_p023"] is False
        and acceptance["b7_resource_credit"] == 0,
        "downstream credit closed",
        checks,
    )

    print(json.dumps({
        "classification": "resident_selector_rtl_evidence_audit_pass",
        "checks_passed": sum(row["pass"] for row in checks),
        "checks_total": len(checks),
        "checks": checks,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

