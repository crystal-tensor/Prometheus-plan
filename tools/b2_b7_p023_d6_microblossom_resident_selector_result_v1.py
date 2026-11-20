#!/usr/bin/env python3
"""Build evidence for the d=6 resident-rule selector RTL replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "results/B2_B7_P023_d6_microblossom_batch_trace_v1.json"
ROUTES = ROOT / "results/B2_B7_P023_d6_microblossom_architecture_routes_v1.json"
X_IMAGE = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_images_v1/x_steady.json"
Z_IMAGE = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_images_v1/z_steady.json"
DYNAMIC_PATCH = ROOT / "tools/patches/micro_blossom_a3530d9_dynamic_weight_sideband.patch"
SELECTOR_PATCH = ROOT / "tools/patches/micro_blossom_a3530d9_resident_rule_selector_on_dynamic_patch.patch"
HARNESS = ROOT / "tools/microblossom/D6ResidentRuleSelectorReplay.scala"
TRANSCRIPT = ROOT / "results/B2_B7_P023_d6_microblossom_resident_selector_sim_v1.log"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_microblossom_resident_selector_rtl_v1.json"

ROW = re.compile(
    r"RESIDENT_SELECTOR_BATCH_PASS name=(x|z)/(maximum|p50|p99|zero) "
    r"selectors=(\d+) updates=(\d+) checked_edges=(\d+) "
    r"axi_write_span_slow_cycles=(\d+)"
)


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def active_rules(image: dict[str, Any]) -> tuple[dict[int, list[tuple[int, int]]], int, int]:
    by_source: dict[int, list[tuple[int, int]]] = {}
    total = 0
    active = 0
    for source_row in image["qec_image_metadata"]["correlation_rules"]:
        source = int(source_row["source_edge_index"])
        for target in source_row["targets"]:
            total += 1
            if target["lowers_base"]:
                active += 1
                even = int(target["replacement_even_weight"])
                half = int(target["replacement_half_weight"])
                hardware = int(target["replacement_hardware_weight"])
                if even % 2 or even // 2 != half or half != hardware:
                    raise ValueError("non-exact hardware weight normalization")
                by_source.setdefault(source, []).append(
                    (int(target["target_edge_index"]), hardware)
                )
    return by_source, total, active


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    trace = read(TRACE)
    routes = read(ROUTES)
    x_image = read(X_IMAGE)
    z_image = read(Z_IMAGE)
    x_rules, x_directed, x_active = active_rules(x_image)
    z_rules, z_directed, z_active = active_rules(z_image)
    if x_rules != z_rules:
        raise ValueError("X/Z steady resident rules differ")
    if (x_directed, x_active) != (15610, 15606):
        raise ValueError("unexpected steady rule counts")
    if (z_directed, z_active) != (15610, 15606):
        raise ValueError("unexpected Z steady rule counts")

    transcript = TRANSCRIPT.read_text(encoding="utf-8")
    observed: dict[tuple[str, str], dict[str, int]] = {}
    for match in ROW.finditer(transcript):
        basis, boundary, selectors, updates, edges, cycles = match.groups()
        key = (basis, boundary)
        if key in observed:
            raise ValueError(f"duplicate transcript row {key}")
        observed[key] = {
            "selectors": int(selectors),
            "updates": int(updates),
            "checked_edges": int(edges),
            "axi_write_span_slow_cycles": int(cycles),
        }
    if len(observed) != 8:
        raise ValueError(f"expected eight transcript rows, got {len(observed)}")

    base_weights = [int(edge["w"]) for edge in x_image["weighted_edges"]]
    if x_image["weighted_edges"] != z_image["weighted_edges"]:
        raise ValueError("X/Z steady graph edges differ")
    trace_rows = {row["basis"]: row for row in trace["basis_rows"]}
    replay_rows: list[dict[str, Any]] = []
    for basis in ("x", "z"):
        for boundary in ("zero", "p50", "p99", "maximum"):
            representative = trace_rows[basis]["representative_batches"][boundary]
            selected = [int(value) for value in representative["selected_edge_indices"]]
            expected_updates = {
                int(edge): int(weight) for edge, weight in representative["updates"]
            }
            reconstructed = list(base_weights)
            for source in selected:
                for target, replacement in x_rules.get(source, []):
                    reconstructed[target] = min(reconstructed[target], replacement)
            reconstructed_updates = {
                edge: weight
                for edge, weight in enumerate(reconstructed)
                if weight != base_weights[edge]
            }
            if reconstructed_updates != expected_updates:
                raise ValueError(f"{basis}/{boundary} software reconstruction mismatch")
            measured = observed[(basis, boundary)]
            if measured["selectors"] != len(selected):
                raise ValueError(f"{basis}/{boundary} selector count mismatch")
            if measured["updates"] != len(expected_updates):
                raise ValueError(f"{basis}/{boundary} update count mismatch")
            if measured["checked_edges"] != len(base_weights):
                raise ValueError(f"{basis}/{boundary} graph edge count mismatch")
            if measured["axi_write_span_slow_cycles"] != 2 * len(selected):
                raise ValueError(f"{basis}/{boundary} cycle span mismatch")
            replay_rows.append({
                "basis": basis,
                "boundary": boundary,
                "selected_source_edges": len(selected),
                "expected_weight_updates": len(expected_updates),
                "checked_edges": measured["checked_edges"],
                "axi_write_span_slow_cycles": measured["axi_write_span_slow_cycles"],
                "pass": True,
            })

    route_rows = {
        row["basis"]: next(
            route for route in row["routes"]
            if route["route"] == "resident_rule_causal_selector"
        )
        for row in routes["basis_rows"]
    }
    baseline_p99 = {"x": 204, "z": 206}
    representative_p99 = {
        row["basis"]: row for row in replay_rows if row["boundary"] == "p99"
    }
    result: dict[str, Any] = {
        "schema": "b2_b7_p023_d6_microblossom_resident_selector_rtl_v1",
        "date": "2026-11-21",
        "classification": "steady_representative_resident_selector_rtl_replay_pass_no_timing_or_resource_credit",
        "scope": ["021/B7", "022/B2", "023"],
        "source": {
            "batch_trace": str(TRACE.relative_to(ROOT)),
            "batch_trace_sha256": sha(TRACE),
            "batch_trace_evidence_id": trace["evidence_id"],
            "architecture_routes": str(ROUTES.relative_to(ROOT)),
            "architecture_routes_sha256": sha(ROUTES),
            "architecture_routes_evidence_id": routes["evidence_id"],
            "x_steady_image": str(X_IMAGE.relative_to(ROOT)),
            "x_steady_image_sha256": sha(X_IMAGE),
            "z_steady_image": str(Z_IMAGE.relative_to(ROOT)),
            "z_steady_image_sha256": sha(Z_IMAGE),
            "simulation_transcript": str(TRANSCRIPT.relative_to(ROOT)),
            "simulation_transcript_sha256": sha(TRANSCRIPT),
            "simulation_harness": str(HARNESS.relative_to(ROOT)),
            "simulation_harness_sha256": sha(HARNESS),
        },
        "implementation": {
            "micro_blossom_commit": "a3530d9e58ff790dafc93d56c9a2769ceac84731",
            "prerequisite_dynamic_weight_patch": str(DYNAMIC_PATCH.relative_to(ROOT)),
            "prerequisite_dynamic_weight_patch_sha256": sha(DYNAMIC_PATCH),
            "resident_selector_patch": str(SELECTOR_PATCH.relative_to(ROOT)),
            "resident_selector_patch_sha256": sha(SELECTOR_PATCH),
            "axi_selector_window": "0x4000-0x4fff",
            "selector_payload": "source edge index [14:0], context id [47:32] on 64-bit AXI",
            "exact_edge_semantics": "on reset restore base; on each selected source, every matching target stores min(current, resident replacement)",
            "active_steady_rules": x_active,
            "directed_steady_rules_including_nonlowering": x_directed,
            "graph_edges": len(base_weights),
            "x_z_steady_rule_tables_equal": True,
        },
        "rtl_generation": {
            "spinalhdl_version": "1.9.3",
            "iverilog_version": "13.0",
            "java": "Homebrew OpenJDK 17.0.21.0.3",
            "elaboration_pass": True,
            "verilog_generation_pass": True,
            "iverilog_compile_pass": True,
            "pruned_signals": 1322474,
            "generated_verilog_bytes": 412800759,
            "generated_verilog_sha256": "e6b27894217a8e671e1d5f122e6f208fea118a6a4fb0738b9b3ed3a32fe0e961",
            "generated_vvp_bytes": 496850097,
            "generated_vvp_sha256": "4cf7c6dfc1d3bf902a325221cb6c6309f864f49e069a9d7baeec5488de0b6aaa",
            "generated_artifacts_committed": False,
        },
        "representative_rtl_replay": {
            "batches_run": 8,
            "batches_passed": 8,
            "batches_failed": 0,
            "graph_edges": len(base_weights),
            "full_edge_state_checks": len(base_weights) * 8,
            "full_edge_state_checks_passed": len(base_weights) * 8,
            "mismatches": 0,
            "rows": replay_rows,
        },
        "transport_reduction": {
            "measured_slow_cycles_per_selector_command": 2,
            "x_representative_p99": {
                "serial_weight_cycles": baseline_p99["x"],
                "resident_selector_cycles": representative_p99["x"]["axi_write_span_slow_cycles"],
                "reduction_factor": baseline_p99["x"] / representative_p99["x"]["axi_write_span_slow_cycles"],
            },
            "z_representative_p99": {
                "serial_weight_cycles": baseline_p99["z"],
                "resident_selector_cycles": representative_p99["z"]["axi_write_span_slow_cycles"],
                "reduction_factor": baseline_p99["z"] / representative_p99["z"]["axi_write_span_slow_cycles"],
            },
            "accepted_distribution_projection": {
                "x_p99_selected_sources": route_rows["x"]["p99_commands"],
                "x_p99_update_only_slow_cycles": route_rows["x"]["p99_slow_cycles"],
                "z_p99_selected_sources": route_rows["z"]["p99_commands"],
                "z_p99_update_only_slow_cycles": route_rows["z"]["p99_slow_cycles"],
                "classification": "projected_from_full_accepted_trace_not_full_rtl_replay",
            },
        },
        "acceptance": {
            "correctness_veto_for_eight_steady_representatives": True,
            "all_accepted_window_batches_replayed_in_rtl": False,
            "opening_closing_selector_replay": False,
            "rtl_corrections_compared": False,
            "fpga_fmax_measured": False,
            "lut_bram_measured": False,
            "full_update_plus_decode_p99_cycles_measured": False,
            "p99_le_1us": False,
            "miss_rate_le_1pct": False,
            "full_b2": False,
            "scalable_p023": False,
            "b7_resource_credit": 0,
        },
        "next_gate": "Synthesize the resident selector for FPGA Fmax/LUT/BRAM, add opening/closing image switching, and compare full RTL corrections before any B2, scalable-023, B7 resource, or one-microsecond claim.",
    }
    result["evidence_id"] = hashlib.sha256(compact(result)).hexdigest()
    args.output.write_text(canonical(result), encoding="utf-8")
    print(canonical(result), end="")


if __name__ == "__main__":
    main()

