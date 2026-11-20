#!/usr/bin/env python3
"""Audit the X phase-superset edge/growth-bank RTL replay result."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results/B2_B7_P023_d6_x_phase_superset_edge_bank_rtl_v1.json"


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


def canonical_id(value: dict[str, Any]) -> str:
    payload = dict(value)
    payload.pop("evidence_id")
    return sha_bytes(compact(payload))


def require(checks: list[dict[str, Any]], label: str, condition: bool) -> None:
    checks.append({"label": label, "pass": bool(condition)})
    if not condition:
        raise AssertionError(label)


def basis_row(value: dict[str, Any], basis: str) -> dict[str, Any]:
    return next(row for row in value["basis_rows"] if row["basis"] == basis)


def main() -> None:
    checks: list[dict[str, Any]] = []
    result = read(RESULT)
    require(checks, "canonical evidence id", result["evidence_id"] == canonical_id(result))
    require(checks, "strict scope", result["scope"] == ["021/B7", "022/B2", "023"])
    require(
        checks,
        "classification boundary",
        result["classification"]
        == "x_phase_superset_edge_growth_bank_rtl_transition_pass_not_distributed_dual",
    )
    sources: dict[str, dict[str, Any]] = {}
    for name in (
        "superset_plan",
        "superset_result",
        "phase_trace",
        "steady_trace",
        "rtl_harness",
        "simulation_transcript",
    ):
        path = ROOT / result["source"][name]
        require(checks, f"{name}: exists", path.is_file())
        require(
            checks,
            f"{name}: hash",
            result["source"][f"{name}_sha256"] == sha_path(path),
        )
        if path.suffix == ".json":
            sources[name] = read(path)
    plan = sources["superset_plan"]
    plan_result = sources["superset_result"]
    require(
        checks,
        "superset plan id",
        result["source"]["superset_plan_evidence_id"] == plan["evidence_id"],
    )
    require(
        checks,
        "superset result id",
        result["source"]["superset_result_evidence_id"]
        == plan_result["evidence_id"],
    )
    x_plan = next(row for row in plan["basis_plans"] if row["basis"] == "x")
    edge_count = len(x_plan["superset_edges"])
    vertex_count = len(x_plan["superset_vertices"])
    require(checks, "X superset edge count", edge_count == 3762)
    require(checks, "X superset vertex count", vertex_count == 1147)
    implementation = result["implementation"]
    require(checks, "result edge count", implementation["superset_edges"] == edge_count)
    require(checks, "result vertex count", implementation["superset_vertices"] == vertex_count)
    phase_plans = {row["phase"]: row for row in x_plan["phases"]}
    require(checks, "three phase plans", set(phase_plans) == {"opening", "steady", "closing"})
    for phase, row in phase_plans.items():
        require(
            checks,
            f"{phase}: injective edge map",
            len(set(row["local_to_superset_edge"])) == len(row["local_to_superset_edge"]),
        )
        require(
            checks,
            f"{phase}: injective vertex map",
            len(set(row["local_to_superset_vertex"]))
            == len(row["local_to_superset_vertex"]),
        )
        active_edges = set(row["active_edge_indices"])
        require(
            checks,
            f"{phase}: rule sources and targets active",
            all(
                rule["source_edge"] in active_edges
                and rule["target_edge"] in active_edges
                for rule in row["active_resident_rules"]
            ),
        )
    phase_trace = sources["phase_trace"]
    steady_trace = sources["steady_trace"]
    phase_trace_x = basis_row(phase_trace, "x")
    steady_trace_x = basis_row(steady_trace, "x")
    expected: dict[tuple[str, str], tuple[int, int]] = {}
    for phase in ("opening", "closing"):
        phase_row = next(row for row in phase_trace_x["phases"] if row["phase"] == phase)
        for boundary, batch in phase_row["representative_batches"].items():
            expected[(phase, boundary)] = (
                len(batch["selected_edge_indices"]),
                len(batch["updates"]),
            )
    for boundary, batch in steady_trace_x["representative_batches"].items():
        expected[("steady", boundary)] = (
            len(batch["selected_edge_indices"]),
            len(batch["updates"]),
        )
    result_rows = {
        (row["phase"], row["boundary"]): row
        for row in result["representative_replay"]["phase_boundary_batches"]
    }
    require(checks, "twelve result batches", set(result_rows) == set(expected))
    transcript_path = ROOT / result["source"]["simulation_transcript"]
    transcript = transcript_path.read_text(encoding="utf-8")
    transcript_pattern = re.compile(
        r"^PHASE_SUPERSET_BATCH_PASS phase=(opening|steady|closing) "
        r"boundary=(zero|p50|p99|maximum) selectors=(\d+) updates=(\d+) "
        r"checked_edges=(\d+) checked_vertices=(\d+)$",
        re.MULTILINE,
    )
    transcript_rows = {
        (match.group(1), match.group(2)): {
            "selectors": int(match.group(3)),
            "updates": int(match.group(4)),
            "checked_edges": int(match.group(5)),
            "checked_vertices": int(match.group(6)),
        }
        for match in transcript_pattern.finditer(transcript)
    }
    require(checks, "twelve transcript batches", set(transcript_rows) == set(expected))
    for key, counts in expected.items():
        row = result_rows[key]
        transcript_row = transcript_rows[key]
        require(
            checks,
            f"{key[0]}/{key[1]}: trace counts",
            (row["selectors"], row["updates"]) == counts,
        )
        require(
            checks,
            f"{key[0]}/{key[1]}: transcript binding",
            transcript_row
            == {
                "selectors": row["selectors"],
                "updates": row["updates"],
                "checked_edges": edge_count,
                "checked_vertices": vertex_count,
            },
        )
    transition = re.search(
        r"^PHASE_SUPERSET_TRANSITION_PASS phase_selections=(\d+) "
        r"selector_commands=(\d+) rejected_inactive_selectors=(\d+) "
        r"checked_edges=(\d+) checked_vertices=(\d+)$",
        transcript,
        re.MULTILINE,
    )
    require(checks, "transition row exists", transition is not None)
    assert transition is not None
    replay = result["representative_replay"]
    require(checks, "twelve phase selections", int(transition.group(1)) == replay["phase_selections"] == 12)
    require(
        checks,
        "accepted selector total",
        int(transition.group(2))
        == replay["selector_commands_accepted"]
        == sum(value[0] for value in expected.values())
        == 103,
    )
    require(
        checks,
        "inactive selector rejection total",
        int(transition.group(3)) == replay["inactive_selectors_rejected"] == 12,
    )
    require(checks, "transition edge count", int(transition.group(4)) == edge_count)
    require(checks, "transition vertex count", int(transition.group(5)) == vertex_count)
    require(
        checks,
        "edge comparison accounting",
        replay["post_select_and_post_batch_edge_state_comparisons"]
        == 2 * 12 * edge_count,
    )
    require(
        checks,
        "vertex comparison accounting",
        replay["post_select_and_post_batch_vertex_growth_comparisons"]
        == 2 * 12 * vertex_count,
    )
    require(
        checks,
        "inactive no-change accounting",
        replay["inactive_selector_no_change_edge_comparisons"] == 12 * edge_count,
    )
    for marker in (
        "SCALA_COMPILE PASS",
        "SPINAL_ELABORATION PASS",
        "VERILOG_GENERATION PASS",
        "IVERILOG_COMPILE PASS",
    ):
        require(checks, marker, marker in transcript)
    harness = (ROOT / result["source"]["rtl_harness"]).read_text(encoding="utf-8")
    for label, marker in (
        ("atomic phase select priority", "when(validPhaseSelect)"),
        ("phase register update", "phaseRegister := io.phaseId"),
        ("inactive selector rejection", "rejectedCountRegister := rejectedCountRegister + 1"),
        ("edge full-state loop", "for (edgeIndex <- 0 until edgeNum)"),
        ("vertex full-state loop", "for (vertexIndex <- 0 until vertexNum)"),
        ("inactive state equality", "dut.edges.map(_.weight.toInt) == before"),
    ):
        require(checks, label, marker in harness)
    generated = result["generated_rtl"]
    require(checks, "Verilog byte count", generated["verilog_bytes"] == 31684681)
    require(checks, "VVP byte count", generated["vvp_bytes"] == 53786527)
    require(checks, "Verilog hash shape", re.fullmatch(r"[0-9a-f]{64}", generated["verilog_sha256"]) is not None)
    require(checks, "VVP hash shape", re.fullmatch(r"[0-9a-f]{64}", generated["vvp_sha256"]) is not None)
    acceptance = result["acceptance"]
    for label in (
        "same_image_x_phase_bank_switching",
        "edge_mask_weight_rule_banks_replayed",
        "vertex_mask_growth_banks_replayed",
        "inactive_selector_rejection_replayed",
    ):
        require(checks, f"positive credit: {label}", acceptance[label] is True)
    for label in (
        "full_distributed_dual_integration",
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
        require(checks, f"closed gate: {label}", acceptance[label] is False)
    require(checks, "zero B7 credit", acceptance["b7_resource_credit"] == 0)
    output = {
        "classification": "x_phase_superset_edge_bank_rtl_evidence_audit_pass",
        "checks_total": len(checks),
        "checks_passed": sum(item["pass"] for item in checks),
        "checks": checks,
    }
    print(json.dumps(output, indent=2, sort_keys=True) + "\n", end="")


if __name__ == "__main__":
    main()
