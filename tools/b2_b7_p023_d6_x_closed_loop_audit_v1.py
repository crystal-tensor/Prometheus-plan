#!/usr/bin/env python3
"""Audit the closed-loop calibration shot and first replay counterexample."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "benchmarks/B2_B7_P023_d6_x_closed_loop_pilot_v1.json"
RAW = ROOT / "results/B2_B7_P023_d6_x_closed_loop_pilot_verilator_v1.json"
CAPTURE = ROOT / "results/B2_B7_P023_d6_x_closed_loop_pilot_verilator_capture_v1.json"
LOG = ROOT / "results/B2_B7_P023_d6_x_closed_loop_pilot_verilator_capture_v1.log"
SHOT0 = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_verilator_v1.json"
OPEN_LOOP = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0009_0135_verilator_v1.json"
OPEN_LOOP_EVIDENCE = ROOT / "results/B2_B7_P023_d6_x_lookahead_divergence_evidence_v1.json"
PATCH = ROOT / "tools/microblossom/d6_x_phase_primal_dual_closed_loop_v9.patch"
SELECTOR = ROOT / "tools/b2_b7_p023_d6_x_selector_server_v1.py"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_closed_loop_evidence_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    pilot = read(PILOT)
    raw = read(RAW)
    capture = read(CAPTURE)
    shot0 = read(SHOT0)
    open_loop = read(OPEN_LOOP)
    open_loop_evidence = read(OPEN_LOOP_EVIDENCE)
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool) -> None:
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    check("pilot binds frozen shots 0 and 15", [row["shot"] for row in pilot["shots"]] == [0, 15])
    check("pilot has complete windows", len(pilot["windows"]) == 164)
    check("formal capture accepted", capture["accepted_x_closed_loop_real_rtl_gate"] is True)
    check("formal process exited cleanly", capture["exit_code"] == 0)
    check("Verilator version pinned", capture["simulator_version"] == "Verilator 5.040 2025-08-30 rev v5.040")
    check("v9 patch bound", capture["source_patch_sha256"] == sha_path(PATCH))
    check("pilot bound", capture["pilot_sha256"] == sha_path(PILOT))
    check("selector server bound", capture["selector_server_sha256"] == sha_path(SELECTOR))
    check("output bound", capture["output_sha256"] == sha_path(RAW))
    check("log bound", capture["log_sha256"] == sha_path(LOG))
    check("no forbidden runtime hits", not capture["forbidden_hits"])
    check("no unexpected warnings", not capture["unexpected_warning_lines"])

    summary = raw["summary"]
    check("complete two-shot cardinality", summary["shots"] == 2 and summary["cases"] == 328)
    check("all closed-loop syndromes valid", summary["all_syndromes_valid"] is True)
    check("all committed residuals clear", summary["commit_residual_failures"] == 0)
    check("all final residuals clear", summary["final_residual_failures"] == 0)
    check("all final logical frames match", summary["final_frame_failures"] == 0)
    check("occupancy audit complete", raw["occupancy_audit"] == {
        "checks": 3254,
        "expected_checks": 3254,
        "all_clear": True,
    })

    closed_0 = [row for row in raw["cases"] if row["shot"] == 0]
    closed_15 = [row for row in raw["cases"] if row["shot"] == 15]
    open_15 = [row for row in open_loop["cases"] if row["shot"] == 15]
    calibration_fields = (
        "actual_subgraph_local_edges",
        "actual_subgraph_superset_edges",
        "correction_hex",
        "iterations",
    )
    check("shot 0 replay-equivalent calibration", all(
        all(left[field] == right[field] for field in calibration_fields)
        for left, right in zip(closed_0, shot0["cases"], strict=True)
    ))
    differing_windows = [
        closed["window"]
        for closed, opened in zip(closed_15, open_15, strict=True)
        if any(closed[field] != opened[field] for field in ("defects", "selectors", "correction_hex", "iterations"))
    ]
    check("closed-loop response diverges only at next window", differing_windows == [60])
    check("first counterexample changes next syndrome", (
        open_15[60]["defects"], closed_15[60]["defects"]
    ) == (14, 12))
    check("first counterexample changes next selector set size", (
        open_15[60]["selectors"], closed_15[60]["selectors"]
    ) == (7, 6))
    check("counterexample shot remains fully committed", all(
        row["syndrome_valid"] and row["commit_residual_clear"] for row in closed_15
    ))
    check("prior open-loop block remains rejected", open_loop_evidence["acceptance"]["trial_accepted_as_full_x_progress"] is False)

    evidence: dict[str, Any] = {
        "schema": "b2_b7_p023_d6_x_closed_loop_evidence_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "x_closed_loop_calibration_and_first_degenerate_correction_shot_pass",
        "checks": checks,
        "closed_loop_result": {
            "shots": [0, 15],
            "cases": 328,
            "syndrome_valid_cases": 328,
            "occupancy_checks_clear": 3254,
            "commit_residual_failures": 0,
            "final_residual_failures": 0,
            "final_frame_failures": 0,
            "maximum_iterations": 18,
            "total_iterations": 1906,
        },
        "trajectory_falsifier": {
            "shot": 15,
            "first_noncanonical_correction_window": 59,
            "feedback_response_window": 60,
            "open_loop_window_60_defects": 14,
            "closed_loop_window_60_defects": 12,
            "open_loop_window_60_selectors": 7,
            "closed_loop_window_60_selectors": 6,
            "later_differing_windows": [],
            "final_residual_clear": True,
            "final_frame_hex": "1",
        },
        "frozen_denominator": {
            "basis": "x",
            "shots": 1024,
            "cases": 167936,
            "accepted_distinct_shots": 10,
            "accepted_cases": 1640,
            "accepted_shot_indices": list(range(9)) + [15],
            "remaining_shots": 1014,
            "remaining_cases": 166296,
            "fraction_tested": 10 / 1024,
        },
        "acceptance": {
            "closed_loop_semantic_gate": True,
            "open_loop_127_shot_block_accepted": False,
            "full_x": False,
            "z_basis": False,
            "axi": False,
            "fpga": False,
            "p99_le_1us": False,
            "miss_rate_le_1pct": False,
            "full_b2": False,
            "scalable_p023": False,
            "b7_resource_credit": 0,
        },
        "next_gate": (
            "Run the remaining frozen X shots through the closed-loop state-feedback route; "
            "do not count the rejected 127-shot open-loop block."
        ),
        "sources": {
            str(path.relative_to(ROOT)): sha_path(path)
            for path in (PILOT, RAW, CAPTURE, LOG, SHOT0, OPEN_LOOP, OPEN_LOOP_EVIDENCE, PATCH, SELECTOR)
        },
    }
    evidence["evidence_id"] = hashlib.sha256(compact(evidence)).hexdigest()
    OUTPUT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT.relative_to(ROOT)),
        "evidence_id": evidence["evidence_id"],
        "checks": len(checks),
        "accepted_distinct_x_shots": 10,
        "accepted_x_cases": 1640,
    }, indent=2))


if __name__ == "__main__":
    main()
