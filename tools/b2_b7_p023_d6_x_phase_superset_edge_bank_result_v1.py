#!/usr/bin/env python3
"""Bind the X phase-superset edge/growth bank RTL replay evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
PLAN_RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"
PHASE_TRACE = ROOT / "results/B2_B7_P023_d6_microblossom_phase_batch_trace_v1.json"
STEADY_TRACE = ROOT / "results/B2_B7_P023_d6_microblossom_batch_trace_v1.json"
HARNESS = ROOT / "tools/microblossom/D6XPhaseSupersetEdgeBankReplay.scala"
TRANSCRIPT = ROOT / "results/B2_B7_P023_d6_x_phase_superset_edge_bank_sim_v1.log"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_phase_superset_edge_bank_rtl_v1.json"


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


def find_basis(value: dict[str, Any], basis: str) -> dict[str, Any]:
    return next(row for row in value["basis_rows"] if row["basis"] == basis)


def representative_counts() -> dict[tuple[str, str], tuple[int, int]]:
    phase_row = find_basis(read(PHASE_TRACE), "x")
    steady_row = find_basis(read(STEADY_TRACE), "x")
    result: dict[tuple[str, str], tuple[int, int]] = {}
    for phase in ("opening", "closing"):
        row = next(item for item in phase_row["phases"] if item["phase"] == phase)
        for boundary, batch in row["representative_batches"].items():
            result[(phase, boundary)] = (
                len(batch["selected_edge_indices"]),
                len(batch["updates"]),
            )
    for boundary, batch in steady_row["representative_batches"].items():
        result[("steady", boundary)] = (
            len(batch["selected_edge_indices"]),
            len(batch["updates"]),
        )
    return result


def main() -> None:
    plan = read(PLAN)
    plan_result = read(PLAN_RESULT)
    x_plan = next(row for row in plan["basis_plans"] if row["basis"] == "x")
    x_summary = next(row for row in plan_result["basis_rows"] if row["basis"] == "x")
    edge_count = len(x_plan["superset_edges"])
    vertex_count = len(x_plan["superset_vertices"])
    transcript = TRANSCRIPT.read_text(encoding="utf-8")
    row_pattern = re.compile(
        r"^PHASE_SUPERSET_BATCH_PASS phase=(opening|steady|closing) "
        r"boundary=(zero|p50|p99|maximum) selectors=(\d+) updates=(\d+) "
        r"checked_edges=(\d+) checked_vertices=(\d+)$",
        re.MULTILINE,
    )
    rows = []
    for match in row_pattern.finditer(transcript):
        rows.append(
            {
                "phase": match.group(1),
                "boundary": match.group(2),
                "selectors": int(match.group(3)),
                "updates": int(match.group(4)),
                "checked_edges": int(match.group(5)),
                "checked_vertices": int(match.group(6)),
            }
        )
    transition_match = re.search(
        r"^PHASE_SUPERSET_TRANSITION_PASS phase_selections=(\d+) "
        r"selector_commands=(\d+) rejected_inactive_selectors=(\d+) "
        r"checked_edges=(\d+) checked_vertices=(\d+)$",
        transcript,
        re.MULTILINE,
    )
    if transition_match is None:
        raise ValueError("transition result missing")
    expected_counts = representative_counts()
    if len(rows) != 12 or len({(row["phase"], row["boundary"]) for row in rows}) != 12:
        raise ValueError("twelve unique phase/boundary rows required")
    for row in rows:
        expected = expected_counts[(row["phase"], row["boundary"])]
        if (row["selectors"], row["updates"]) != expected:
            raise ValueError(f"trace count mismatch: {row}")
        if row["checked_edges"] != edge_count or row["checked_vertices"] != vertex_count:
            raise ValueError(f"superset size mismatch: {row}")
    transition = {
        "phase_selections": int(transition_match.group(1)),
        "selector_commands": int(transition_match.group(2)),
        "rejected_inactive_selectors": int(transition_match.group(3)),
        "checked_edges": int(transition_match.group(4)),
        "checked_vertices": int(transition_match.group(5)),
    }
    if transition != {
        "phase_selections": 12,
        "selector_commands": sum(row["selectors"] for row in rows),
        "rejected_inactive_selectors": 12,
        "checked_edges": edge_count,
        "checked_vertices": vertex_count,
    }:
        raise ValueError("transition totals mismatch")
    artifact_match = re.search(
        r"^GENERATED_VERILOG bytes=(\d+) sha256=([0-9a-f]{64})$.*"
        r"^GENERATED_VVP bytes=(\d+) sha256=([0-9a-f]{64})$",
        transcript,
        re.MULTILINE | re.DOTALL,
    )
    if artifact_match is None:
        raise ValueError("generated artifact binding missing")
    result = {
        "schema": "b2_b7_p023_d6_x_phase_superset_edge_bank_rtl_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "x_phase_superset_edge_growth_bank_rtl_transition_pass_not_distributed_dual",
        "source": {
            "superset_plan": str(PLAN.relative_to(ROOT)),
            "superset_plan_sha256": sha_path(PLAN),
            "superset_plan_evidence_id": plan["evidence_id"],
            "superset_result": str(PLAN_RESULT.relative_to(ROOT)),
            "superset_result_sha256": sha_path(PLAN_RESULT),
            "superset_result_evidence_id": plan_result["evidence_id"],
            "phase_trace": str(PHASE_TRACE.relative_to(ROOT)),
            "phase_trace_sha256": sha_path(PHASE_TRACE),
            "steady_trace": str(STEADY_TRACE.relative_to(ROOT)),
            "steady_trace_sha256": sha_path(STEADY_TRACE),
            "rtl_harness": str(HARNESS.relative_to(ROOT)),
            "rtl_harness_sha256": sha_path(HARNESS),
            "simulation_transcript": str(TRANSCRIPT.relative_to(ROOT)),
            "simulation_transcript_sha256": sha_path(TRANSCRIPT),
        },
        "implementation": {
            "basis": "x",
            "superset_edges": edge_count,
            "superset_vertices": vertex_count,
            "edge_overhead_vs_largest_phase_ratio": x_summary["superset"][
                "edges_vs_largest_phase_ratio"
            ],
            "phase_banks": [
                "edge active mask",
                "edge base weight",
                "edge resident rules",
                "vertex active mask",
                "vertex maximum growth",
            ],
            "atomic_event": "phaseSelectValid selects opening/steady/closing and restores every banked register in one simulated clock edge",
            "inactive_selector_contract": "an inactive or out-of-range selector increments the rejection counter and cannot update any edge weight",
            "micro_blossom_commit": "a3530d9e58ff790dafc93d56c9a2769ceac84731",
        },
        "generated_rtl": {
            "spinalhdl_version": "1.9.3",
            "iverilog_version": "13.0",
            "verilog_bytes": int(artifact_match.group(1)),
            "verilog_sha256": artifact_match.group(2),
            "vvp_bytes": int(artifact_match.group(3)),
            "vvp_sha256": artifact_match.group(4),
            "artifacts_committed": False,
        },
        "representative_replay": {
            "phase_boundary_batches": rows,
            "batches_passed": 12,
            "phase_selections": transition["phase_selections"],
            "selector_commands_accepted": transition["selector_commands"],
            "inactive_selectors_rejected": transition[
                "rejected_inactive_selectors"
            ],
            "post_select_and_post_batch_edge_state_comparisons": 2
            * 12
            * edge_count,
            "post_select_and_post_batch_vertex_growth_comparisons": 2
            * 12
            * vertex_count,
            "inactive_selector_no_change_edge_comparisons": 12 * edge_count,
        },
        "claim_boundary": {
            "implemented": "same-image X edge-mask/base-weight/rule bank and vertex-mask/growth bank switching",
            "not_implemented": [
                "integration into Micro Blossom DistributedDual vertices, edges, convergecast, and conflict logic",
                "phase-banked fault/output map in RTL",
                "complete correction or observable comparison",
                "Z-basis banked RTL",
                "AXI phase-control path",
                "FPGA synthesis, Fmax, LUT/BRAM, or routing closure",
                "end-to-end update-plus-decode latency",
            ],
        },
        "acceptance": {
            "same_image_x_phase_bank_switching": True,
            "edge_mask_weight_rule_banks_replayed": True,
            "vertex_mask_growth_banks_replayed": True,
            "inactive_selector_rejection_replayed": True,
            "full_distributed_dual_integration": False,
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
        "next_gate": "Integrate the X phase banks and active masks into the real DistributedDual edge/vertex/convergecast paths, add a reset-bound AXI phase command, and compare complete corrections before extending the same mechanism to Z.",
    }
    result["evidence_id"] = sha_bytes(compact(result))
    OUTPUT.write_text(canonical(result), encoding="utf-8")
    print(canonical(result), end="")


if __name__ == "__main__":
    main()
