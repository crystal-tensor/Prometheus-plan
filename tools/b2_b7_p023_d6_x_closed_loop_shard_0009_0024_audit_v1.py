#!/usr/bin/env python3
"""Audit the first multi-shot closed-loop X RTL shard and cumulative denominator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "benchmarks/B2_B7_P023_d6_x_closed_loop_shard_0009_0024_v1.json"
RAW = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0009_0024_verilator_v1.json"
CAPTURE = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0009_0024_verilator_capture_v1.json"
LOG = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0009_0024_verilator_capture_v1.log"
PRIOR = ROOT / "results/B2_B7_P023_d6_x_closed_loop_evidence_v1.json"
OPEN_LOOP = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0009_0135_verilator_v1.json"
PATCH = ROOT / "tools/microblossom/d6_x_phase_primal_dual_closed_loop_v9.patch"
SELECTOR = ROOT / "tools/b2_b7_p023_d6_x_selector_server_v1.py"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0009_0024_evidence_v1.json"

NEW_SHOTS = list(range(9, 15)) + list(range(16, 25))
CUMULATIVE_SHOTS = list(range(25))


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
    prior = read(PRIOR)
    open_loop = read(OPEN_LOOP)
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool) -> None:
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    pilot_shots = [row["shot"] for row in pilot["shots"]]
    prior_shots = prior["frozen_denominator"]["accepted_shot_indices"]
    check("pilot binds exact new shot set", pilot_shots == NEW_SHOTS)
    check("pilot has complete windows", len(pilot["windows"]) == 164)
    check("prior evidence accepted ten distinct shots", prior_shots == list(range(9)) + [15])
    check("new and prior shot sets are disjoint", not (set(pilot_shots) & set(prior_shots)))
    check("cumulative shot set is contiguous zero through twenty-four", sorted(pilot_shots + prior_shots) == CUMULATIVE_SHOTS)

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
    check("complete fifteen-shot cardinality", summary["shots"] == 15 and summary["cases"] == 2460)
    check("all closed-loop syndromes valid", summary["all_syndromes_valid"] is True)
    check("all committed residuals clear", summary["commit_residual_failures"] == 0)
    check("all final residuals clear", summary["final_residual_failures"] == 0)
    check("all final logical frames match", summary["final_frame_failures"] == 0)
    check("closed-loop semantic gate accepted", summary["accepted_closed_loop_gate"] is True)
    check("occupancy audit complete", raw["occupancy_audit"] == {
        "checks": 25756,
        "expected_checks": 25756,
        "all_clear": True,
    })
    check("all case rows individually pass", all(
        row["syndrome_valid"] and row["commit_residual_clear"]
        for row in raw["cases"]
    ))

    open_by_key = {
        (row["shot"], row["window"]): row
        for row in open_loop["cases"]
        if row["shot"] in NEW_SHOTS
    }
    replay_fields = ("defects", "selectors", "correction_hex", "iterations")
    divergent = [
        {"shot": row["shot"], "window": row["window"]}
        for row in raw["cases"]
        if any(
            row[field] != open_by_key[(row["shot"], row["window"])][field]
            for field in replay_fields
        )
    ]
    check("new shard is replay-equivalent under closed-loop feedback", not divergent)
    check("raw rows cover each new shot exactly once per window", all(
        sum(row["shot"] == shot for row in raw["cases"]) == 164
        for shot in NEW_SHOTS
    ))

    evidence: dict[str, Any] = {
        "schema": "b2_b7_p023_d6_x_closed_loop_shard_0009_0024_evidence_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "first_multi_shot_closed_loop_x_rtl_shard_pass",
        "checks": checks,
        "new_closed_loop_result": {
            "shots": NEW_SHOTS,
            "cases": 2460,
            "syndrome_valid_cases": 2460,
            "occupancy_checks_clear": 25756,
            "commit_residual_failures": 0,
            "final_residual_failures": 0,
            "final_frame_failures": 0,
            "maximum_iterations": summary["max_iterations"],
            "total_iterations": summary["total_iterations"],
            "open_loop_trajectory_divergences": divergent,
            "elapsed_seconds": capture["elapsed_seconds"],
        },
        "frozen_denominator": {
            "basis": "x",
            "shots": 1024,
            "cases": 167936,
            "accepted_distinct_shots": 25,
            "accepted_cases": 4100,
            "accepted_shot_indices": CUMULATIVE_SHOTS,
            "remaining_shots": 999,
            "remaining_cases": 163836,
            "fraction_tested": 25 / 1024,
        },
        "acceptance": {
            "new_closed_loop_shard": True,
            "cumulative_x_prefix_zero_through_twenty_four": True,
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
            "Continue the frozen X corpus from shot 25 through the same closed-loop "
            "state-feedback route; do not infer hardware latency from host elapsed time."
        ),
        "sources": {
            str(path.relative_to(ROOT)): sha_path(path)
            for path in (PILOT, RAW, CAPTURE, LOG, PRIOR, OPEN_LOOP, PATCH, SELECTOR)
        },
    }
    evidence["evidence_id"] = hashlib.sha256(compact(evidence)).hexdigest()
    OUTPUT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT.relative_to(ROOT)),
        "evidence_id": evidence["evidence_id"],
        "checks": len(checks),
        "accepted_distinct_x_shots": 25,
        "accepted_x_cases": 4100,
    }, indent=2))


if __name__ == "__main__":
    main()
