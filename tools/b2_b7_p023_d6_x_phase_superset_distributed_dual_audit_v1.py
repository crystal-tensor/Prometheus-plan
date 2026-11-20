#!/usr/bin/env python3
"""Audit the bounded X phase-superset DistributedDual RTL result."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results/B2_B7_P023_d6_x_phase_superset_distributed_dual_rtl_v1.json"
BATCH_RE = re.compile(
    r"^PHASE_DISTRIBUTED_DUAL_BATCH_PASS phase=(\w+) boundary=(\w+) "
    r"selectors=(\d+) updates=(\d+) checked_edges=(\d+) checked_vertices=(\d+)$"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_id(payload: dict) -> str:
    body = dict(payload)
    body.pop("evidence_id", None)
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> None:
    result = json.loads(RESULT.read_text())
    checks = []

    def check(label: str, condition: bool) -> None:
        checks.append({"label": label, "pass": bool(condition)})

    check("canonical evidence id", result["evidence_id"] == canonical_id(result))
    check("strict scope", result["scope"] == ["021/B7", "022/B2", "023"])
    check("bounded classification", result["classification"].endswith("not_complete_correction"))

    source = result["source"]
    for key in ("superset_plan", "superset_result", "source_patch", "replay_harness", "simulation_transcript"):
        path = ROOT / source[key]
        check(f"{key}: exists", path.is_file())
        check(f"{key}: hash", sha256(path) == source[f"{key}_sha256"])

    plan = json.loads((ROOT / source["superset_plan"]).read_text())
    plan_result = json.loads((ROOT / source["superset_result"]).read_text())
    x_plan = next(row for row in plan["basis_plans"] if row["basis"] == "x")
    check("plan evidence id", plan["evidence_id"] == source["superset_plan_evidence_id"])
    check("plan result evidence id", plan_result["evidence_id"] == source["superset_result_evidence_id"])
    check("X superset edges", len(x_plan["superset_edges"]) == result["implementation"]["superset_edges"] == 3762)
    check("X superset vertices", len(x_plan["superset_vertices"]) == result["implementation"]["superset_vertices"] == 1147)
    check("three ordered banks", result["implementation"]["phase_banks"] == ["opening", "steady", "closing"])

    transcript = (ROOT / source["simulation_transcript"]).read_text()
    observed = []
    for line in transcript.splitlines():
        match = BATCH_RE.match(line)
        if match:
            phase, boundary, selectors, updates, edges, vertices = match.groups()
            observed.append(
                {
                    "phase": phase,
                    "boundary": boundary,
                    "selectors": int(selectors),
                    "updates": int(updates),
                    "checked_edges": int(edges),
                    "checked_vertices": int(vertices),
                }
            )
    expected = result["representative_replay"]["batches"]
    check("twelve result batches", len(expected) == 12)
    check("twelve transcript batches", len(observed) == 12)
    check("transcript rows bind result", observed == expected)
    check("all phase-boundary keys", len({(row["phase"], row["boundary"]) for row in observed}) == 12)
    check("selector total", sum(row["selectors"] for row in observed) == result["representative_replay"]["selector_commands"] == 103)
    check("phase selections", result["representative_replay"]["phase_selections"] == 12)
    check("edge register accounting", result["representative_replay"]["post_select_and_post_batch_edge_register_comparisons"] == 90288)
    check("vertex active accounting", result["representative_replay"]["post_select_and_post_batch_vertex_active_comparisons"] == 27528)
    check("inactive edge gate accounting", result["representative_replay"]["inactive_edge_output_gate_checks"] == 13456)
    check("inactive vertex gate accounting", result["representative_replay"]["inactive_vertex_output_gate_checks"] == 4256)
    check("convergecast accounting", result["representative_replay"]["convergecast_no_obstacle_checks"] == 12)

    for marker in (
        "FULL_SOURCE_COMPILE PASS",
        "REPLAY_HARNESS_COMPILE PASS",
        "PATCH_REPLAY PASS",
        "SPINAL_ELABORATION PASS",
        "VERILOG_GENERATION PASS",
        "IVERILOG_COMPILE PASS",
        "PHASE_DISTRIBUTED_DUAL_TRANSITION_PASS",
        "SIMULATION PASS",
    ):
        check(marker, marker in transcript)

    generated = result["generated_rtl"]
    check("Verilog bytes", generated["verilog_bytes"] == 571867041)
    check("VVP bytes", generated["vvp_bytes"] == 697900922)
    check("Verilog hash shape", bool(re.fullmatch(r"[0-9a-f]{64}", generated["verilog_sha256"])))
    check("VVP hash shape", bool(re.fullmatch(r"[0-9a-f]{64}", generated["vvp_sha256"])))
    check("generated artifacts uncommitted", generated["artifacts_committed"] is False)

    patch = (ROOT / source["source_patch"]).read_text()
    for marker in (
        "case class DualPhaseBank",
        "phaseSelectValid",
        "activeRegister",
        "stages.offloadSet2.isTight := activeRegister",
        "io.conflict.valid := False",
        "stages.offloadSet.message.valid := False",
        "def simSelectPhase",
    ):
        check(f"patch marker: {marker}", marker in patch)

    harness = (ROOT / source["replay_harness"]).read_text()
    for marker in (
        "DistributedDual(config, ioConfig)",
        "dut.simSelectPhase(phaseIndex)",
        "dut.simApplyResidentRuleSelector",
        "generateFindObstacle",
        "PHASE_DISTRIBUTED_DUAL_BATCH_PASS",
        "PHASE_DISTRIBUTED_DUAL_TRANSITION_PASS",
    ):
        check(f"harness marker: {marker}", marker in harness)

    acceptance = result["acceptance"]
    for key in (
        "same_image_x_phase_bank_switching",
        "real_distributed_dual_edge_vertex_path",
        "inactive_edge_tightness_conflict_exclusion",
        "inactive_vertex_command_growable_exclusion",
        "representative_phase_batch_replay",
    ):
        check(f"positive credit: {key}", acceptance[key] is True)
    for key in (
        "phase_banked_fault_output_map",
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
        "classification": "x_phase_superset_distributed_dual_evidence_audit_pass",
        "checks_passed": sum(row["pass"] for row in checks),
        "checks_total": len(checks),
        "checks": checks,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if payload["checks_passed"] != payload["checks_total"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
