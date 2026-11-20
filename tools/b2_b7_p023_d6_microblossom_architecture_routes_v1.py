#!/usr/bin/env python3
"""Compare exact dynamic-weight transport routes for the accepted d6 trace."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "results/B2_B7_P023_d6_microblossom_batch_trace_v1.json"
REPLAY = ROOT / "results/B2_B7_P023_d6_microblossom_batch_replay_v1.json"
MANIFEST = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_images_v1.json"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_microblossom_architecture_routes_v1.json"


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


def commands(value: float, lanes: int) -> int:
    return math.ceil(int(value) / lanes)


def image_resource_row(row: dict[str, Any]) -> dict[str, Any]:
    image = read(ROOT / row["path"])
    meta = image["qec_image_metadata"]
    edge_bits = max(1, (len(image["weighted_edges"]) - 1).bit_length())
    weight_bits = int(meta["stored_weight_bits_required"])
    directed = int(meta["directed_rules"])
    source_fanout = [len(rule["targets"]) for rule in meta["correlation_rules"]]
    target_indegree = [0] * len(image["weighted_edges"])
    for rule in meta["correlation_rules"]:
        for target in rule["targets"]:
            target_indegree[target["target_edge_index"]] += 1
    active_indegree = sorted(value for value in target_indegree if value)
    raw_rule_bits = directed * (edge_bits + weight_bits)
    offset_bits = (directed + 1).bit_length()
    csr_offset_bits = (len(meta["correlation_rules"]) + 1) * offset_bits
    return {
        "basis": row["basis"],
        "phase": row["phase"],
        "rule_image_sha256": row["source_rule_image_sha256"],
        "edges": len(image["weighted_edges"]),
        "source_edges_with_rules": len(meta["correlation_rules"]),
        "directed_rules": directed,
        "edge_index_bits": edge_bits,
        "weight_bits": weight_bits,
        "edge_local_raw_rule_bits": raw_rule_bits,
        "edge_local_raw_rule_kib": raw_rule_bits / 8 / 1024,
        "source_csr_raw_bits_with_offsets": raw_rule_bits + csr_offset_bits,
        "source_csr_raw_kib_with_offsets": (raw_rule_bits + csr_offset_bits) / 8 / 1024,
        "source_fanout_maximum": max(source_fanout),
        "source_fanout_p99": source_fanout[max(0, math.ceil(0.99 * len(source_fanout)) - 1)]
        if source_fanout == sorted(source_fanout)
        else sorted(source_fanout)[max(0, math.ceil(0.99 * len(source_fanout)) - 1)],
        "target_rule_indegree_maximum": max(active_indegree),
        "target_rule_indegree_p99": active_indegree[
            max(0, math.ceil(0.99 * len(active_indegree)) - 1)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    trace = read(TRACE)
    replay = read(REPLAY)
    manifest = read(MANIFEST)
    cycles_per_command = int(
        replay["serial_update_pressure"]["observed_slow_cycles_per_update"]
    )
    if cycles_per_command != 2:
        raise ValueError("measured command-cycle contract changed")
    basis_rows = []
    for row in trace["basis_rows"]:
        basis = row["basis"]
        updates = row["hardware_update_edges"]
        selected = row["selected_edges"]
        route_rows = []
        for route, lanes, word_bits, evidence in (
            ("serial_weight_words", 1, 32, "measured"),
            ("dual_weight_words", 2, 64, "modeled_requires_new_packing"),
            ("quad_weight_words", 4, 128, "modeled_requires_new_stream"),
        ):
            p99_commands = commands(updates["p99"], lanes)
            maximum_commands = commands(updates["maximum"], lanes)
            route_rows.append(
                {
                    "route": route,
                    "updates_per_command": lanes,
                    "command_word_bits": word_bits,
                    "evidence": evidence,
                    "p99_commands": p99_commands,
                    "maximum_commands": maximum_commands,
                    "p99_slow_cycles": p99_commands * cycles_per_command,
                    "maximum_slow_cycles": maximum_commands * cycles_per_command,
                    "p99_bus_bits": p99_commands * word_bits,
                    "minimum_slow_clock_mhz_for_p99_update_only_under_1us":
                        p99_commands * cycles_per_command,
                }
            )
        selector_p99 = int(selected["p99"])
        selector_maximum = int(selected["maximum"])
        route_rows.append(
            {
                "route": "resident_rule_causal_selector",
                "updates_per_command": "parallel_fanout_from_one_selected_source",
                "command_word_bits": 32,
                "useful_selector_bits": 15,
                "evidence": "modeled_from_accepted_selected-edge_trace_hardware_not_yet_implemented",
                "p99_commands": selector_p99,
                "maximum_commands": selector_maximum,
                "p99_slow_cycles": selector_p99 * cycles_per_command,
                "maximum_slow_cycles": selector_maximum * cycles_per_command,
                "p99_bus_bits": selector_p99 * 32,
                "minimum_slow_clock_mhz_for_p99_update_only_under_1us":
                    selector_p99 * cycles_per_command,
            }
        )
        basis_rows.append(
            {
                "basis": basis,
                "accepted_update_edges": updates,
                "accepted_selected_source_edges": selected,
                "routes": route_rows,
                "selector_vs_serial_p99_command_reduction":
                    int(updates["p99"]) / selector_p99,
            }
        )
    image_resources = [image_resource_row(row) for row in manifest["images"]]
    unique_rule_rows: dict[str, dict[str, Any]] = {}
    for row in image_resources:
        unique_rule_rows.setdefault(row["rule_image_sha256"], row)
    all_raw_bits = sum(row["edge_local_raw_rule_bits"] for row in image_resources)
    unique_raw_bits = sum(row["edge_local_raw_rule_bits"] for row in unique_rule_rows.values())
    result = {
        "schema": "b2_b7_p023_d6_microblossom_architecture_routes_v1",
        "date": "2026-11-20",
        "classification": "resident_rule_causal_selector_selected_for_rtl_prototype_no_timing_or_resource_credit",
        "scope": ["021/B7", "022/B2", "023"],
        "source": {
            "batch_trace": str(TRACE.relative_to(ROOT)),
            "batch_trace_sha256": sha_path(TRACE),
            "batch_trace_evidence_id": trace["evidence_id"],
            "representative_replay": str(REPLAY.relative_to(ROOT)),
            "representative_replay_sha256": sha_path(REPLAY),
            "image_manifest": str(MANIFEST.relative_to(ROOT)),
            "image_manifest_sha256": sha_path(MANIFEST),
        },
        "measured_transport_contract": {
            "serial_axi_slow_cycles_per_command": cycles_per_command,
            "measurement_scope": "representative steady edge-state replay",
            "decode_cycles_included": False,
            "fpga_frequency_measured": False,
        },
        "basis_rows": basis_rows,
        "resident_rule_resource_lower_bound": {
            "images": image_resources,
            "six_image_directed_rules": sum(row["directed_rules"] for row in image_resources),
            "six_image_edge_local_raw_rule_bits": all_raw_bits,
            "six_image_edge_local_raw_rule_kib": all_raw_bits / 8 / 1024,
            "unique_rule_tables": len(unique_rule_rows),
            "unique_rule_table_hashes": sorted(unique_rule_rows),
            "unique_rule_edge_local_raw_bits": unique_raw_bits,
            "unique_rule_edge_local_raw_kib": unique_raw_bits / 8 / 1024,
            "encoding_lower_bound": "per directed rule: edge/source index bits plus 15-bit normalized weight; excludes mux/comparator/routing/BRAM granularity",
        },
        "selected_route": {
            "name": "resident_rule_causal_selector",
            "exact_semantics": "Reset to base, then apply selected source-edge selectors sequentially; each target edge takes min(current, resident replacement), making selector order irrelevant and reproducing strict-lowering aggregation.",
            "why": [
                "accepted X/Z p99 selected-source count is 13 versus 102/103 replacement writes",
                "under the measured two-cycle command path, modeled p99 update span falls from 204/206 to 26/26 slow cycles",
                "one source fans out to at most 24 target edges in the six frozen images",
                "one target compares at most 24 resident source rules, with p99 indegree 19",
            ],
            "unproven_costs": [
                "selector decode fanout and comparator timing",
                "routing congestion and synthesis mapping of roughly 278 KiB unique raw rule data",
                "integration with first-pass selected-edge production",
                "opening/closing switching, full correction equivalence, FPGA Fmax, LUT/BRAM, and one-microsecond deadline",
            ],
        },
        "acceptance": {
            "architecture_route_selected": True,
            "resident_selector_rtl_implemented": False,
            "resident_selector_representative_replay": False,
            "resource_synthesis_measured": False,
            "full_update_plus_decode_p99_cycles_measured": False,
            "p99_le_1us": False,
            "miss_rate_le_1pct": False,
            "full_b2": False,
            "scalable_p023": False,
            "b7_resource_credit": 0,
        },
        "next_gate": "Implement the steady resident-rule selector in the pinned RTL, replay all eight boundary batches by sending selected source edges rather than weights, and compare all 2,973 edge states before any timing or resource claim.",
    }
    result["evidence_id"] = sha_bytes(compact(result))
    args.output.write_text(canonical(result), encoding="utf-8")
    print(canonical(result), end="")


if __name__ == "__main__":
    main()
