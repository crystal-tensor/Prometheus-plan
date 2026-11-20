#!/usr/bin/env python3
"""Build bounded evidence for the X phase-banked RTL fault-output slice."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
TRACE = ROOT / "benchmarks/B2_B7_P023_d6_x_phase_fault_output_trace_v1.json"
PREVIOUS = ROOT / "results/B2_B7_P023_d6_x_phase_superset_distributed_dual_rtl_v1.json"
PATCH = ROOT / "tools/microblossom/d6_x_phase_superset_fault_output_v2.patch"
HARNESS = ROOT / "tools/microblossom/D6XPhaseSupersetFaultOutputReplay.scala"
TRANSCRIPT = ROOT / "results/B2_B7_P023_d6_x_phase_fault_output_sim_v1.log"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_phase_fault_output_rtl_v1.json"

BATCH_RE = re.compile(
    r"^PHASE_FAULT_OUTPUT_BATCH_PASS phase=(\w+) boundary=(\w+) "
    r"selected_edges=(\d+) correction_bits=(\d+) nonzero_bits=(\d+)$"
)
SUMMARY_RE = re.compile(
    r"^PHASE_FAULT_OUTPUT_REPLAY_PASS phase_selections=(\d+) map_checks=(\d+) "
    r"inactive_empty_checks=(\d+) complete_corrections=(\d+) selected_edges=(\d+)$"
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_id(payload: dict) -> str:
    body = dict(payload)
    body.pop("evidence_id", None)
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> None:
    plan = read(PLAN)
    trace = read(TRACE)
    previous = read(PREVIOUS)
    x_plan = next(row for row in plan["basis_plans"] if row["basis"] == "x")
    transcript = TRANSCRIPT.read_text(encoding="utf-8")
    batches = []
    summary = None
    generated = {}
    for line in transcript.splitlines():
        match = BATCH_RE.match(line)
        if match:
            phase, boundary, selected, width, nonzero = match.groups()
            batches.append(
                {
                    "phase": phase,
                    "boundary": boundary,
                    "selected_edges": int(selected),
                    "correction_bits": int(width),
                    "nonzero_bits": int(nonzero),
                }
            )
        match = SUMMARY_RE.match(line)
        if match:
            selections, map_checks, inactive, corrections, selected = map(
                int, match.groups()
            )
            summary = {
                "phase_selections": selections,
                "edge_map_checks": map_checks,
                "inactive_edge_empty_map_checks": inactive,
                "complete_reference_corrections": corrections,
                "selected_subgraph_edges": selected,
            }
        if line.startswith("VERILOG_GENERATION PASS "):
            fields = dict(item.split("=", 1) for item in line.split()[2:])
            generated["verilog_bytes"] = int(fields["bytes"])
            generated["verilog_sha256"] = fields["sha256"]
        if line.startswith("IVERILOG_COMPILE PASS "):
            fields = dict(item.split("=", 1) for item in line.split()[2:])
            generated["vvp_bytes"] = int(fields["vvp_bytes"])
            generated["vvp_sha256"] = fields["vvp_sha256"]
    if summary is None or len(batches) != 12:
        raise ValueError("simulation transcript is incomplete")

    payload = {
        "schema": "b2_b7_p023_d6_x_phase_fault_output_rtl_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "x_phase_banked_fault_output_and_complete_reference_subgraph_readout_pass_not_distributed_dual_subgraph_selection",
        "source": {
            "micro_blossom_commit": "a3530d9e58ff790dafc93d56c9a2769ceac84731",
            "superset_plan": str(PLAN.relative_to(ROOT)),
            "superset_plan_sha256": sha256(PLAN),
            "superset_plan_evidence_id": plan["evidence_id"],
            "correction_trace": str(TRACE.relative_to(ROOT)),
            "correction_trace_sha256": sha256(TRACE),
            "correction_trace_evidence_id": trace["evidence_id"],
            "previous_distributed_dual_result": str(PREVIOUS.relative_to(ROOT)),
            "previous_distributed_dual_result_sha256": sha256(PREVIOUS),
            "previous_distributed_dual_evidence_id": previous["evidence_id"],
            "source_patch": str(PATCH.relative_to(ROOT)),
            "source_patch_sha256": sha256(PATCH),
            "replay_harness": str(HARNESS.relative_to(ROOT)),
            "replay_harness_sha256": sha256(HARNESS),
            "simulation_transcript": str(TRANSCRIPT.relative_to(ROOT)),
            "simulation_transcript_sha256": sha256(TRANSCRIPT),
        },
        "implementation": {
            "basis": "x",
            "phase_banks": ["opening", "steady", "closing"],
            "superset_edges": len(x_plan["superset_edges"]),
            "superset_vertices": len(x_plan["superset_vertices"]),
            "maximum_fault_ids_per_edge": 2,
            "phase_fault_vector_bits": {
                row["phase"]: row["fault_id_count"] for row in x_plan["phases"]
            },
            "readout_contract": "the primal host submits each selected subgraph edge exactly once; phase-local zero/one/two fault IDs are XORed into a reset-bound correction accumulator",
            "phase_select_clears_correction_accumulator": True,
        },
        "rtl_replay": {"batches": batches, **summary},
        "generated_rtl": {
            **generated,
            "spinalhdl_version": "1.9.3",
            "iverilog_version": "13.0",
            "artifacts_committed": False,
        },
        "acceptance": {
            "same_image_x_phase_bank_switching": True,
            "real_distributed_dual_edge_vertex_path": True,
            "phase_banked_fault_output_map": True,
            "all_phase_edge_maps_compared": True,
            "inactive_edge_maps_empty": True,
            "complete_reference_corrections_compared": True,
            "distributed_dual_selected_complete_subgraphs": False,
            "complete_corrections_compared": False,
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
            "implemented": "X opening/steady/closing phase-banked sparse fault map and RTL correction accumulator, exhaustively checked per edge and on twelve complete reference subgraphs",
            "not_implemented": [
                "Rust primal host plus phase-aware DistributedDual generation of the compared subgraphs",
                "Z-basis phase banks and fault-output map",
                "AXI phase-control and correction-readout path with race proof",
                "FPGA synthesis, Fmax, LUT/BRAM, or routing closure",
                "end-to-end update-plus-decode latency",
            ],
        },
        "next_gate": "Integrate the Rust primal host with phase selection and resident selectors so the compared subgraph is produced by the real phase-aware DistributedDual, then feed that subgraph through this verified fault-output accumulator.",
    }
    payload["evidence_id"] = evidence_id(payload)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
