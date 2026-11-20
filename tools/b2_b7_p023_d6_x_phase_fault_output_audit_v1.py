#!/usr/bin/env python3
"""Audit the bounded X phase-banked RTL fault-output evidence."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results/B2_B7_P023_d6_x_phase_fault_output_rtl_v1.json"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_phase_fault_output_audit_v1.json"

BATCH_RE = re.compile(
    r"^PHASE_FAULT_OUTPUT_BATCH_PASS phase=(\w+) boundary=(\w+) "
    r"selected_edges=(\d+) correction_bits=(\d+) nonzero_bits=(\d+)$"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_id(payload: dict) -> str:
    body = dict(payload)
    body.pop("evidence_id", None)
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> None:
    result = json.loads(RESULT.read_text())
    checks: list[dict] = []

    def check(label: str, condition: bool) -> None:
        checks.append({"label": label, "pass": bool(condition)})

    check("canonical evidence id", result["evidence_id"] == canonical_id(result))
    check("strict scope", result["scope"] == ["021/B7", "022/B2", "023"])
    check(
        "bounded classification",
        result["classification"].endswith("not_distributed_dual_subgraph_selection"),
    )

    source = result["source"]
    for key in (
        "superset_plan",
        "correction_trace",
        "previous_distributed_dual_result",
        "source_patch",
        "replay_harness",
        "simulation_transcript",
    ):
        path = ROOT / source[key]
        check(f"{key}: exists", path.is_file())
        check(f"{key}: hash", sha256(path) == source[f"{key}_sha256"])

    plan = json.loads((ROOT / source["superset_plan"]).read_text())
    trace = json.loads((ROOT / source["correction_trace"]).read_text())
    previous = json.loads((ROOT / source["previous_distributed_dual_result"]).read_text())
    x_plan = next(row for row in plan["basis_plans"] if row["basis"] == "x")
    phase_plan = {row["phase"]: row for row in x_plan["phases"]}
    check("plan evidence", plan["evidence_id"] == source["superset_plan_evidence_id"])
    check("trace evidence", trace["evidence_id"] == source["correction_trace_evidence_id"])
    check(
        "previous dual evidence",
        previous["evidence_id"] == source["previous_distributed_dual_evidence_id"],
    )
    check("previous real dual path", previous["acceptance"]["real_distributed_dual_edge_vertex_path"] is True)
    check("X superset edges", len(x_plan["superset_edges"]) == result["implementation"]["superset_edges"] == 3762)
    check("X superset vertices", len(x_plan["superset_vertices"]) == result["implementation"]["superset_vertices"] == 1147)
    check("phase widths", result["implementation"]["phase_fault_vector_bits"] == {"opening": 229, "steady": 246, "closing": 789})

    trace_rows = trace["representative_corrections"]
    check("twelve correction traces", len(trace_rows) == 12)
    check(
        "all phase-boundary trace keys",
        {(row["phase"], row["boundary"]) for row in trace_rows}
        == {
            (phase, boundary)
            for phase in ("opening", "steady", "closing")
            for boundary in ("zero", "p50", "p99", "maximum")
        },
    )
    for row in trace_rows:
        phase = phase_plan[row["phase"]]
        active = set(phase["active_edge_indices"])
        check(
            f"{row['phase']}/{row['boundary']}: width",
            row["fault_id_count"] == phase["fault_id_count"],
        )
        check(
            f"{row['phase']}/{row['boundary']}: selected active",
            all(edge in active for edge in row["selected_superset_edges"]),
        )
        check(
            f"{row['phase']}/{row['boundary']}: unique selected",
            len(row["selected_superset_edges"])
            == len(set(row["selected_superset_edges"])),
        )
        check(
            f"{row['phase']}/{row['boundary']}: fault range",
            all(0 <= value < row["fault_id_count"] for value in row["nonzero_fault_ids"]),
        )

    transcript = (ROOT / source["simulation_transcript"]).read_text()
    observed = []
    for line in transcript.splitlines():
        match = BATCH_RE.match(line)
        if match:
            phase, boundary, selected, width, nonzero = match.groups()
            observed.append(
                {
                    "phase": phase,
                    "boundary": boundary,
                    "selected_edges": int(selected),
                    "correction_bits": int(width),
                    "nonzero_bits": int(nonzero),
                }
            )
    check("twelve transcript batches", len(observed) == 12)
    check("transcript binds result batches", observed == result["rtl_replay"]["batches"])
    expected_map_checks = 3 * len(x_plan["superset_edges"])
    expected_inactive = sum(
        len(x_plan["superset_edges"]) - len(row["active_edge_indices"])
        for row in x_plan["phases"]
    )
    check("exhaustive edge map accounting", result["rtl_replay"]["edge_map_checks"] == expected_map_checks == 11286)
    check("inactive empty map accounting", result["rtl_replay"]["inactive_edge_empty_map_checks"] == expected_inactive == 1682)
    check("complete correction accounting", result["rtl_replay"]["complete_reference_corrections"] == 12)
    check("selected subgraph accounting", result["rtl_replay"]["selected_subgraph_edges"] == sum(len(row["selected_superset_edges"]) for row in trace_rows) == 104)

    for marker in (
        "FULL_SOURCE_COMPILE PASS",
        "REPLAY_HARNESS_COMPILE PASS",
        "PATCH_REPLAY PASS",
        "SPINAL_ELABORATION PASS",
        "VERILOG_GENERATION PASS",
        "IVERILOG_COMPILE PASS",
        "PHASE_FAULT_OUTPUT_REPLAY_PASS",
        "SIMULATION PASS",
    ):
        check(marker, marker in transcript)

    generated = result["generated_rtl"]
    check("Verilog bytes", generated["verilog_bytes"] == 573238230)
    check("VVP bytes", generated["vvp_bytes"] == 701116898)
    check("Verilog hash", generated["verilog_sha256"] == "0ce72d50ae3232edaccfb5caa337be6dc0b49cd3caf746b1817c377e074909d6")
    check("VVP hash", generated["vvp_sha256"] == "83895af47f47a35239fd8215047c8e7486837f89dbf5f602c03ef61eb35c9171")
    check("generated artifacts uncommitted", generated["artifacts_committed"] is False)

    patch = (ROOT / source["source_patch"]).read_text()
    for marker in (
        "edgeFaultIds: Seq[Seq[Int]]",
        "faultIdCount: Int",
        "val correctionAccumulator",
        "io.correctionEdgeValid",
        "correctionAccumulator(selectedFaultId0)",
        "def simAccumulateCorrectionEdge",
    ):
        check(f"patch marker: {marker}", marker in patch)
    harness = (ROOT / source["replay_harness"]).read_text()
    for marker in (
        "DistributedDual(config, ioConfig)",
        "dut.simAccumulateCorrectionEdge",
        "for (edgeIndex <- 0 until edgeNum)",
        "PHASE_FAULT_OUTPUT_BATCH_PASS",
        "PHASE_FAULT_OUTPUT_REPLAY_PASS",
    ):
        check(f"harness marker: {marker}", marker in harness)

    acceptance = result["acceptance"]
    for key in (
        "same_image_x_phase_bank_switching",
        "real_distributed_dual_edge_vertex_path",
        "phase_banked_fault_output_map",
        "all_phase_edge_maps_compared",
        "inactive_edge_maps_empty",
        "complete_reference_corrections_compared",
    ):
        check(f"positive credit: {key}", acceptance[key] is True)
    for key in (
        "distributed_dual_selected_complete_subgraphs",
        "complete_corrections_compared",
        "z_basis_phase_bank_switching",
        "axi_phase_control_path",
        "fpga_fmax_measured",
        "lut_bram_measured",
        "p99_le_1us",
        "miss_rate_le_1pct",
        "full_b2",
        "scalable_p023",
    ):
        check(f"closed gate: {key}", acceptance[key] is False)
    check("zero B7 credit", acceptance["b7_resource_credit"] == 0)

    payload = {
        "classification": "x_phase_fault_output_evidence_audit_pass",
        "checks_passed": sum(row["pass"] for row in checks),
        "checks_total": len(checks),
        "checks": checks,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload["checks_passed"] != payload["checks_total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
