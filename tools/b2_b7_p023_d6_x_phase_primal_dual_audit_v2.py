#!/usr/bin/env python3
"""Independently audit the deferred-selector X primal/real-RTL evidence."""

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
RESULT = ROOT / "results/B2_B7_P023_d6_x_phase_primal_dual_evidence_v2.json"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_phase_primal_dual_audit_v2.json"


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


def main() -> None:
    source = read(INPUT)
    raw = read(RAW)
    comb = read(COMB)
    capture = read(CAPTURE)
    result = read(RESULT)
    checks: list[dict[str, Any]] = []

    def check(label: str, condition: bool) -> None:
        checks.append({"label": label, "pass": bool(condition)})

    check("input evidence id", source["evidence_id"] == canonical_id(source))
    check("fixed input id", source["evidence_id"] == "486c68356642f6ed62dc163d4bcad5f7e0cd40d3ff9bfb5c66600d47d2b3e121")
    check("weight scale two", source["micro_blossom_weight_scale"] == 2)
    for bank in source["phase_banks"]:
        name = bank["name"]
        check(f"{name}: even edge base weights", all(weight % 2 == 0 for weight in bank["edge_base_weights"]))
        check(
            f"{name}: even resident replacements",
            all(weight % 2 == 0 for rule in bank["resident_weight_rules"] for _, weight in rule["rules"]),
        )
        check(f"{name}: even vertex growth", all(weight % 2 == 0 for weight in bank["vertex_max_growth"]))
    for phase in source["phase_graphs"]:
        check(
            f"{phase['name']}: even local graph weights",
            all(edge["w"] % 2 == 0 for edge in phase["graph"]["weighted_edges"]),
        )

    check("result evidence id", result["evidence_id"] == canonical_id(result))
    check("strict scope", result["scope"] == ["021/B7", "022/B2", "023"])
    for key, entry in result["source"].items():
        if not isinstance(entry, dict) or "path" not in entry:
            continue
        path = ROOT / entry["path"]
        check(f"{key}: exists", path.is_file())
        check(f"{key}: hash", path.is_file() and entry["sha256"] == sha256(path))

    check("capture exit zero", capture["exit_code"] == 0)
    check("capture accepted", capture["accepted_representative_x_rtl_gate"] is True)
    check("capture forbidden empty", capture["forbidden_hits"] == [])
    check("capture unexpected warnings empty", capture["unexpected_warning_lines"] == [])
    check("capture two classified warnings", len(capture["known_warning_lines"]) == 2)
    check("capture input hash", capture["input_sha256"] == sha256(INPUT))
    check("capture output hash", capture["output_sha256"] == sha256(RAW))
    patch_path = ROOT / result["source"]["source_patch"]["path"]
    log_path = ROOT / result["source"]["capture_log"]["path"]
    check("capture patch hash", capture["source_patch_sha256"] == sha256(patch_path))
    check("capture log hash", capture["log_sha256"] == sha256(log_path))
    check("pinned archive hash", capture["source_archive_sha256"] == "284f3e52ab0a3de038821d7b9063ea978c16ec0f8b3a35204f8d862f6595659b")

    patch = patch_path.read_text(encoding="utf-8")
    for marker in (
        "fn after_defects_loaded(&mut self)",
        "queue_rule_selector",
        "queue_edge_weight",
        "simMakePublicOccupancyAudit",
        "cannot add defect node $node to occupied vertex",
        "occupancy_audit_read",
        "after_all_defects_before_first_obstacle",
    ):
        check(f"patch marker: {marker}", marker in patch)

    expected = source["cases"]
    observed = raw["cases"]
    comb_rows = comb["cases"]
    check("raw schema", raw["schema"] == "d6_x_phase_primal_dual_deferred_selector_rtl_v2")
    check("selector commit order", raw["selector_commit_order"] == "after_all_defects_before_first_obstacle")
    check("twelve expected cases", len(expected) == 12)
    check("twelve RTL cases", len(observed) == 12)
    check("twelve comb cases", len(comb_rows) == 12)
    total_defects = sum(len(row["defect_vertices"]) for row in expected)
    occupancy = raw["occupancy_audit"]
    check("occupancy all clear", occupancy["all_clear"] is True)
    check("occupancy expected count", occupancy["expected_checks"] == total_defects == 177)
    check("occupancy observed count", occupancy["checks"] == total_defects)

    phase_graphs = {row["name"]: row for row in source["phase_graphs"]}
    phase_banks = {row["name"]: row for row in source["phase_banks"]}
    for want, got, control in zip(expected, observed, comb_rows, strict=True):
        label = f"{want['phase']}/{want['boundary']}"
        identity = (want["phase"], want["boundary"], want["shot"], want["window"])
        check(f"{label}: RTL identity", (got["phase"], got["boundary"], got["shot"], got["window"]) == identity)
        check(f"{label}: comb identity", (control["phase"], control["boundary"], control["shot"], control["window"]) == identity)
        check(f"{label}: defect count", got["defects"] == len(want["defect_vertices"]))
        check(f"{label}: selector count", got["selectors"] == len(want["selector_edges"]))
        local_count = len(phase_graphs[want["phase"]]["graph"]["weighted_edges"])
        active = {edge for edge, enabled in enumerate(phase_banks[want["phase"]]["edge_active"]) if enabled}
        check(f"{label}: local edge range", all(0 <= edge < local_count for edge in got["actual_subgraph_local_edges"]))
        check(f"{label}: active superset edges", all(edge in active for edge in got["actual_subgraph_superset_edges"]))
        check(f"{label}: exact reference list", sorted(got["actual_subgraph_superset_edges"]) == sorted(want["expected_reference_subgraph_superset_edges"]))
        check(f"{label}: exact flag", got["exact_reference_subgraph_edges"] is True)
        check(f"{label}: syndrome valid", got["syndrome_valid"] is True)
        check(f"{label}: correction value", int(got["correction_hex"], 16) == int(want["expected_correction_hex"], 16))
        check(f"{label}: correction flag", got["correction_equal"] is True)
        check(f"{label}: RTL watchdog bound", 0 <= got["iterations"] <= 21)
        check(f"{label}: comb syndrome", control["syndrome_valid"] is True)
        check(f"{label}: comb correction", control["correction_equal"] is True)
        check(f"{label}: comb watchdog bound", 0 <= control["iterations"] <= 21)

    summary = raw["summary"]
    check("RTL summary cases", summary["cases"] == 12)
    check("RTL summary syndromes", summary["all_syndromes_valid"] is True)
    check("RTL summary corrections", summary["all_corrections_equal"] is True)
    check("RTL summary exact subgraphs", summary["exact_reference_subgraphs"] == 12)
    check("comb summary cases", comb["summary"]["cases"] == 12)
    check("comb summary syndromes", comb["summary"]["all_syndromes_valid"] is True)
    check("comb summary corrections", comb["summary"]["all_corrections_equal"] is True)
    check("comb max iterations", comb["summary"]["max_iterations"] == 21)

    acceptance = result["acceptance"]
    for key in (
        "same_image_x_phase_bank_switching",
        "real_distributed_dual_edge_vertex_path",
        "rust_primal_real_distributed_dual_joint_run",
        "defects_loaded_before_zero_weight_selector_commit",
        "representative_x_occupancy_gate",
        "representative_x_complete_subgraphs_exact",
        "representative_x_complete_corrections_equal",
        "representative_x_end_to_end_correctness_gate",
    ):
        check(f"open representative gate: {key}", acceptance[key] is True)
    for key in (
        "all_accepted_x_corpus_end_to_end",
        "z_basis_phase_bank_switching",
        "axi_phase_control_path",
        "fpga_fmax_measured",
        "lut_bram_measured",
        "p99_le_1us",
        "miss_rate_le_1pct",
        "full_b2",
        "scalable_p023",
    ):
        check(f"closed broader gate: {key}", acceptance[key] is False)
    check("zero B7 credit", acceptance["b7_resource_credit"] == 0)

    passed = sum(row["pass"] for row in checks)
    payload = {
        "schema": "b2_b7_p023_d6_x_phase_primal_dual_audit_v2",
        "classification": "x_representative_deferred_selector_real_rtl_audit_pass" if passed == len(checks) else "audit_failure",
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: payload[key] for key in ("classification", "checks_passed", "checks_total")}, indent=2, sort_keys=True))
    if passed != len(checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
