#!/usr/bin/env python3
"""Audit closed-loop X shots 25-63 and the cumulative 64-shot prefix."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "benchmarks/B2_B7_P023_d6_x_closed_loop_shard_0025_0063_v1.json"
RAW = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0025_0063_verilator_v1.json"
CAPTURE = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0025_0063_verilator_capture_v1.json"
LOG = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0025_0063_verilator_capture_v1.log"
PRIOR = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0009_0024_evidence_v1.json"
OPEN_LOOP = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0009_0135_verilator_v1.json"
OPEN_LOOP_EVIDENCE = ROOT / "results/B2_B7_P023_d6_x_lookahead_divergence_evidence_v1.json"
PATCH = ROOT / "tools/microblossom/d6_x_phase_primal_dual_closed_loop_v9.patch"
SELECTOR = ROOT / "tools/b2_b7_p023_d6_x_selector_server_v1.py"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0025_0063_evidence_v1.json"

NEW_SHOTS = list(range(25, 64))
CUMULATIVE_SHOTS = list(range(64))
EXPECTED_INITIATORS = [
    {"shot": 29, "window": 143},
    {"shot": 36, "window": 127},
    {"shot": 38, "window": 145},
    {"shot": 54, "window": 154},
    {"shot": 58, "window": 120},
    {"shot": 60, "window": 15},
]
EXPECTED_RESPONSES = [
    {"shot": row["shot"], "window": row["window"] + 1}
    for row in EXPECTED_INITIATORS
]


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
    open_loop_evidence = read(OPEN_LOOP_EVIDENCE)
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool) -> None:
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    pilot_shots = [row["shot"] for row in pilot["shots"]]
    prior_shots = prior["frozen_denominator"]["accepted_shot_indices"]
    check("pilot binds exact shot range twenty-five through sixty-three", pilot_shots == NEW_SHOTS)
    check("pilot has complete windows", len(pilot["windows"]) == 164)
    check("prior evidence accepted contiguous zero through twenty-four", prior_shots == list(range(25)))
    check("new and prior shot sets are disjoint", not (set(pilot_shots) & set(prior_shots)))
    check("cumulative shot set is contiguous zero through sixty-three", sorted(pilot_shots + prior_shots) == CUMULATIVE_SHOTS)

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
    check("complete thirty-nine-shot cardinality", summary["shots"] == 39 and summary["cases"] == 6396)
    check("all closed-loop syndromes valid", summary["all_syndromes_valid"] is True)
    check("all committed residuals clear", summary["commit_residual_failures"] == 0)
    check("all final residuals clear", summary["final_residual_failures"] == 0)
    check("all final logical frames match", summary["final_frame_failures"] == 0)
    check("closed-loop semantic gate accepted", summary["accepted_closed_loop_gate"] is True)
    check("occupancy audit complete", raw["occupancy_audit"] == {
        "checks": 64465,
        "expected_checks": 64465,
        "all_clear": True,
    })
    check("all case rows individually pass", all(
        row["syndrome_valid"] and row["commit_residual_clear"]
        for row in raw["cases"]
    ))

    initiators = sorted(
        {
            (row["shot"], row["window"])
            for row in open_loop_evidence["diagnosis"]["delta_rows"]
            if row["shot"] in NEW_SHOTS
        }
    )
    check("open-loop evidence identifies exact six initiators", [
        {"shot": shot, "window": window} for shot, window in initiators
    ] == EXPECTED_INITIATORS)

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
    check("closed-loop divergences occur only in six response windows", divergent == EXPECTED_RESPONSES)

    rows_by_key = {(row["shot"], row["window"]): row for row in raw["cases"]}
    check("all six response windows clear commit residuals", all(
        rows_by_key[(row["shot"], row["window"])]["commit_residual_clear"]
        for row in EXPECTED_RESPONSES
    ))
    check("all six trajectories reconverge by following window", all(
        all(
            rows_by_key[(row["shot"], row["window"] + 1)][field]
            == open_by_key[(row["shot"], row["window"] + 1)][field]
            for field in replay_fields
        )
        for row in EXPECTED_RESPONSES
    ))
    check("raw rows cover each new shot exactly once per window", all(
        sum(row["shot"] == shot for row in raw["cases"]) == 164
        for shot in NEW_SHOTS
    ))

    evidence: dict[str, Any] = {
        "schema": "b2_b7_p023_d6_x_closed_loop_shard_0025_0063_evidence_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "closed_loop_x_prefix_64_with_six_feedback_sensitive_shots_pass",
        "checks": checks,
        "new_closed_loop_result": {
            "shots": NEW_SHOTS,
            "cases": 6396,
            "syndrome_valid_cases": 6396,
            "occupancy_checks_clear": 64465,
            "commit_residual_failures": 0,
            "final_residual_failures": 0,
            "final_frame_failures": 0,
            "maximum_iterations": summary["max_iterations"],
            "total_iterations": summary["total_iterations"],
            "feedback_sensitive_initiators": EXPECTED_INITIATORS,
            "closed_loop_response_windows": EXPECTED_RESPONSES,
            "all_response_commit_residuals_clear": True,
            "all_trajectories_reconverge_by_following_window": True,
            "elapsed_seconds": capture["elapsed_seconds"],
        },
        "cumulative_feedback_sensitive_shots": [15, 29, 36, 38, 54, 58, 60],
        "frozen_denominator": {
            "basis": "x",
            "shots": 1024,
            "cases": 167936,
            "accepted_distinct_shots": 64,
            "accepted_cases": 10496,
            "accepted_shot_indices": CUMULATIVE_SHOTS,
            "remaining_shots": 960,
            "remaining_cases": 157440,
            "fraction_tested": 64 / 1024,
        },
        "acceptance": {
            "new_closed_loop_shard": True,
            "cumulative_x_prefix_zero_through_sixty_three": True,
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
            "Continue the frozen X corpus from shot 64 through the same closed-loop route, "
            "including the remaining known open-loop mismatch initiators."
        ),
        "sources": {
            str(path.relative_to(ROOT)): sha_path(path)
            for path in (
                PILOT, RAW, CAPTURE, LOG, PRIOR, OPEN_LOOP, OPEN_LOOP_EVIDENCE, PATCH, SELECTOR
            )
        },
    }
    evidence["evidence_id"] = hashlib.sha256(compact(evidence)).hexdigest()
    OUTPUT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT.relative_to(ROOT)),
        "evidence_id": evidence["evidence_id"],
        "checks": len(checks),
        "accepted_distinct_x_shots": 64,
        "accepted_x_cases": 10496,
        "feedback_sensitive_shots": evidence["cumulative_feedback_sensitive_shots"],
    }, indent=2))


if __name__ == "__main__":
    main()
