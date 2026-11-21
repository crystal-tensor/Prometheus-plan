#!/usr/bin/env python3
"""Bind the deferred-selector X primal/real-RTL run into scoped evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "benchmarks/B2_B7_P023_d6_x_phase_primal_dual_input_v1.json"
RAW = ROOT / "results/B2_B7_P023_d6_x_phase_primal_dual_rtl_v2.json"
COMB = ROOT / "results/B2_B7_P023_d6_x_phase_primal_dual_comb_deferred_selector_v2.json"
CAPTURE = ROOT / "results/B2_B7_P023_d6_x_phase_primal_dual_capture_v1.json"
LOG = ROOT / "results/B2_B7_P023_d6_x_phase_primal_dual_capture_v1.log"
PATCH = ROOT / "tools/microblossom/d6_x_phase_primal_dual_deferred_selector_occupancy_v6.patch"
BUILDER = ROOT / "tools/b2_b7_p023_d6_x_phase_primal_dual_input_v1.py"
CAPTURE_TOOL = ROOT / "tools/b2_b7_p023_d6_x_phase_primal_dual_capture_v1.py"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_phase_primal_dual_evidence_v2.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_id(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("evidence_id", None)
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def source_entry(path: Path) -> dict[str, str]:
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}


def main() -> None:
    input_payload = read(INPUT)
    raw = read(RAW)
    comb = read(COMB)
    capture = read(CAPTURE)
    rows = raw["cases"]
    all_syndromes = len(rows) == 12 and all(row["syndrome_valid"] for row in rows)
    all_corrections = len(rows) == 12 and all(row["correction_equal"] for row in rows)
    exact_subgraphs = sum(row["exact_reference_subgraph_edges"] for row in rows)
    occupancy = raw["occupancy_audit"]
    gate = all(
        (
            all_syndromes,
            all_corrections,
            exact_subgraphs == 12,
            occupancy["all_clear"],
            occupancy["checks"] == occupancy["expected_checks"] == 177,
            capture["accepted_representative_x_rtl_gate"],
            capture["exit_code"] == 0,
            not capture["forbidden_hits"],
            not capture["unexpected_warning_lines"],
        )
    )
    phase_iterations = {
        phase: {
            row["boundary"]: row["iterations"]
            for row in rows
            if row["phase"] == phase
        }
        for phase in ("opening", "steady", "closing")
    }
    payload = {
        "schema": "b2_b7_p023_d6_x_phase_primal_dual_evidence_v2",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": (
            "x_representative_deferred_selector_real_rtl_gate_pass"
            if gate
            else "x_representative_real_rtl_correctness_falsifier"
        ),
        "source": {
            "micro_blossom_commit": "a3530d9e58ff790dafc93d56c9a2769ceac84731",
            "micro_blossom_source_archive_sha256": capture["source_archive_sha256"],
            "input": source_entry(INPUT),
            "input_builder": source_entry(BUILDER),
            "source_patch": source_entry(PATCH),
            "capture_tool": source_entry(CAPTURE_TOOL),
            "comb_control": source_entry(COMB),
            "raw_rtl_run": source_entry(RAW),
            "capture_log": source_entry(LOG),
            "capture_metadata": source_entry(CAPTURE),
        },
        "implementation": {
            "basis": "x",
            "phase_banks": ["opening", "steady", "closing"],
            "superset_vertices": input_payload["graph"]["vertex_num"],
            "superset_edges": len(input_payload["graph"]["weighted_edges"]),
            "micro_blossom_weight_scale": input_payload["micro_blossom_weight_scale"],
            "selector_commit_order": raw["selector_commit_order"],
            "software_primal": "fusion_blossom Rust primal",
            "hardware_dual": "phase-aware SpinalHDL DistributedDual executed by Icarus",
            "correction_readout": "phase-banked RTL XOR accumulator over selected superset edges",
        },
        "diagnostic_and_fix": {
            "discarded_pre_fix_falsifier": (
                "An odd edge weight (phase-local 1401 / superset 1901, weight 12037) "
                "caused maxGrowth rounding and invalidated the long pre-fix run."
            ),
            "weight_domain_fix": (
                "Scale edge, resident-rule, and vertex-growth weights by two so the "
                "Micro Blossom integer-growth domain is even."
            ),
            "occupancy_falsifier": (
                "Applying a selector before the complete syndrome made a zero-weight "
                "edge propagate node 4 from vertex 587 into future defect vertex 474."
            ),
            "ordering_fix": (
                "Load all defects first, then commit queued resident selectors before "
                "the first obstacle search."
            ),
        },
        "representative_x_run": {
            "cases": len(rows),
            "defects_checked_before_add": occupancy["checks"],
            "occupancy_checks_all_clear": occupancy["all_clear"],
            "all_syndromes_valid": all_syndromes,
            "all_corrections_equal": all_corrections,
            "exact_reference_subgraphs": exact_subgraphs,
            "iterations": phase_iterations,
            "max_iterations": max(row["iterations"] for row in rows),
            "rows": rows,
        },
        "independent_comb_control": comb["summary"],
        "capture_gate": {
            "exit_code": capture["exit_code"],
            "forbidden_hits": capture["forbidden_hits"],
            "known_warning_lines": capture["known_warning_lines"],
            "unexpected_warning_lines": capture["unexpected_warning_lines"],
            "accepted": capture["accepted_representative_x_rtl_gate"],
        },
        "acceptance": {
            "same_image_x_phase_bank_switching": True,
            "real_distributed_dual_edge_vertex_path": True,
            "rust_primal_real_distributed_dual_joint_run": True,
            "defects_loaded_before_zero_weight_selector_commit": True,
            "representative_x_occupancy_gate": occupancy["all_clear"],
            "representative_x_complete_subgraphs_exact": exact_subgraphs == 12,
            "representative_x_complete_corrections_equal": all_corrections,
            "representative_x_end_to_end_correctness_gate": gate,
            "all_accepted_x_corpus_end_to_end": False,
            "z_basis_phase_bank_switching": False,
            "axi_phase_control_path": False,
            "fpga_fmax_measured": False,
            "lut_bram_measured": False,
            "p99_le_1us": False,
            "miss_rate_le_1pct": False,
            "full_b2": False,
            "scalable_p023": False,
            "b7_resource_credit": 0,
        },
        "claim_boundary": {
            "implemented": (
                "Twelve frozen X representatives spanning opening, steady, closing and "
                "zero/p50/p99/maximum were jointly solved by the Rust primal and real "
                "phase-aware DistributedDual; every subgraph, syndrome and correction matched."
            ),
            "not_implemented": [
                "the full accepted X corpus",
                "Z-basis phase banks and end-to-end correction",
                "AXI phase control and correction readout",
                "FPGA synthesis, Fmax, LUT/BRAM, routing, or measured hardware latency",
                "p99 at or below one microsecond and miss rate at or below one percent",
            ],
        },
        "next_gate": (
            "Run the complete accepted X corpus through the same defect-first selector-commit "
            "path, then build and test the independent Z phase banks before AXI/FPGA timing."
        ),
    }
    payload["evidence_id"] = canonical_id(payload)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "output": str(OUTPUT),
        "classification": payload["classification"],
        "evidence_id": payload["evidence_id"],
        "gate": gate,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
