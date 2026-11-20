#!/usr/bin/env python3
"""Build the bounded result for the full X phase-superset DistributedDual replay."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
PLAN_RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
PATCH = ROOT / "tools/microblossom/d6_x_phase_superset_distributed_dual_v1.patch"
HARNESS = ROOT / "tools/microblossom/D6XPhaseSupersetDistributedDualReplay.scala"
TRANSCRIPT = ROOT / "results/B2_B7_P023_d6_x_phase_superset_distributed_dual_sim_v1.log"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_phase_superset_distributed_dual_rtl_v1.json"

BATCH_RE = re.compile(
    r"^PHASE_DISTRIBUTED_DUAL_BATCH_PASS phase=(\w+) boundary=(\w+) "
    r"selectors=(\d+) updates=(\d+) checked_edges=(\d+) checked_vertices=(\d+)$"
)
TRANSITION_RE = re.compile(
    r"^PHASE_DISTRIBUTED_DUAL_TRANSITION_PASS phase_selections=(\d+) "
    r"selector_commands=(\d+) checked_edges=(\d+) checked_vertices=(\d+)$"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_id(payload: dict) -> str:
    body = dict(payload)
    body.pop("evidence_id", None)
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    plan = json.loads(PLAN.read_text())
    plan_result = json.loads(PLAN_RESULT.read_text())
    x_plan = next(row for row in plan["basis_plans"] if row["basis"] == "x")
    phase_by_name = {row["phase"]: row for row in x_plan["phases"]}

    batches = []
    transition = None
    generated = {}
    for line in TRANSCRIPT.read_text().splitlines():
        match = BATCH_RE.match(line)
        if match:
            phase, boundary, selectors, updates, edges, vertices = match.groups()
            batches.append(
                {
                    "phase": phase,
                    "boundary": boundary,
                    "selectors": int(selectors),
                    "updates": int(updates),
                    "checked_edges": int(edges),
                    "checked_vertices": int(vertices),
                }
            )
        match = TRANSITION_RE.match(line)
        if match:
            selections, commands, edges, vertices = map(int, match.groups())
            transition = {
                "phase_selections": selections,
                "selector_commands": commands,
                "checked_edges": edges,
                "checked_vertices": vertices,
            }
        if line.startswith("VERILOG_GENERATION PASS "):
            parts = dict(item.split("=", 1) for item in line.split()[2:])
            generated["verilog_bytes"] = int(parts["bytes"])
            generated["verilog_sha256"] = parts["sha256"]
        if line.startswith("IVERILOG_COMPILE PASS "):
            parts = dict(item.split("=", 1) for item in line.split()[2:])
            generated["vvp_bytes"] = int(parts["vvp_bytes"])
            generated["vvp_sha256"] = parts["vvp_sha256"]

    assert transition is not None
    assert len(batches) == 12
    assert set((row["phase"], row["boundary"]) for row in batches) == {
        (phase, boundary)
        for phase in ("opening", "steady", "closing")
        for boundary in ("zero", "p50", "p99", "maximum")
    }

    inactive_edge_checks = sum(
        len(x_plan["superset_edges"]) - len(phase_by_name[name]["active_edge_indices"])
        for name in ("opening", "steady", "closing")
    ) * 8
    inactive_vertex_checks = sum(
        len(x_plan["superset_vertices"]) - len(phase_by_name[name]["active_vertex_indices"])
        for name in ("opening", "steady", "closing")
    ) * 8

    payload = {
        "schema": "b2_b7_p023_d6_x_phase_superset_distributed_dual_rtl_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "x_phase_superset_real_distributed_dual_edge_vertex_convergecast_pass_not_complete_correction",
        "source": {
            "micro_blossom_commit": "a3530d9e58ff790dafc93d56c9a2769ceac84731",
            "superset_plan": str(PLAN.relative_to(ROOT)),
            "superset_plan_sha256": sha256(PLAN),
            "superset_plan_evidence_id": plan["evidence_id"],
            "superset_result": str(PLAN_RESULT.relative_to(ROOT)),
            "superset_result_sha256": sha256(PLAN_RESULT),
            "superset_result_evidence_id": plan_result["evidence_id"],
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
            "real_paths_exercised": [
                "DistributedDual phase register and broadcast",
                "Edge phase-active and base-weight registers",
                "Edge resident-rule selection",
                "Edge offload and execute tightness gates",
                "Edge max-growable and conflict gates",
                "Vertex phase-active and virtual reset state",
                "Vertex command gate and max-growable gate",
                "DistributedDual max-growable and conflict convergecast trees",
            ],
            "phase_select_contract": "quiescent Reset plus phase select restores active masks, weights, rules, and vertex reset state",
        },
        "representative_replay": {
            "batches": batches,
            **transition,
            "post_select_and_post_batch_edge_register_comparisons": 12 * 2 * len(x_plan["superset_edges"]),
            "post_select_and_post_batch_vertex_active_comparisons": 12 * 2 * len(x_plan["superset_vertices"]),
            "inactive_edge_output_gate_checks": inactive_edge_checks,
            "inactive_vertex_output_gate_checks": inactive_vertex_checks,
            "convergecast_no_obstacle_checks": 12,
        },
        "generated_rtl": {
            **generated,
            "spinalhdl_version": "1.9.3",
            "iverilog_version": "13.0",
            "artifacts_committed": False,
        },
        "acceptance": {
            "same_image_x_phase_bank_switching": True,
            "real_distributed_dual_edge_vertex_path": True,
            "inactive_edge_tightness_conflict_exclusion": True,
            "inactive_vertex_command_growable_exclusion": True,
            "representative_phase_batch_replay": True,
            "phase_banked_fault_output_map": False,
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
            "implemented": "real X DistributedDual Edge/Vertex/tightness/max-growable/conflict/convergecast phase slice",
            "not_implemented": [
                "phase-banked fault/output map",
                "complete correction or observable comparison",
                "Z-basis phase banks",
                "AXI phase-control path and race proof",
                "FPGA synthesis, Fmax, LUT/BRAM, or routing closure",
                "end-to-end update-plus-decode latency",
            ],
        },
        "next_gate": "Bank the X fault/output map, drive complete accepted syndromes through the phase-aware DistributedDual, and compare complete corrections before extending the same path to Z and AXI.",
    }
    payload["evidence_id"] = evidence_id(payload)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
