#!/usr/bin/env python3
"""Audit closed-loop X shots 64-127 and all 21 known open-loop divergences."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "benchmarks/B2_B7_P023_d6_x_closed_loop_shard_0064_0127_v1.json"
RAW = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0064_0127_verilator_v1.json"
CAPTURE = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0064_0127_verilator_capture_v1.json"
LOG = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0064_0127_verilator_capture_v1.log"
PRIOR = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0025_0063_evidence_v1.json"
OPEN_LOOP = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0009_0135_verilator_v1.json"
OPEN_LOOP_EVIDENCE = ROOT / "results/B2_B7_P023_d6_x_lookahead_divergence_evidence_v1.json"
PATCH = ROOT / "tools/microblossom/d6_x_phase_primal_dual_closed_loop_v9.patch"
SELECTOR = ROOT / "tools/b2_b7_p023_d6_x_selector_server_v1.py"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0064_0127_evidence_v1.json"

NEW_SHOTS = list(range(64, 128))
CUMULATIVE_SHOTS = list(range(128))
EXPECTED_INITIATORS = [
    {"shot": 73, "window": 13},
    {"shot": 74, "window": 129},
    {"shot": 75, "window": 148},
    {"shot": 99, "window": 32},
    {"shot": 102, "window": 26},
    {"shot": 106, "window": 20},
    {"shot": 108, "window": 6},
    {"shot": 111, "window": 139},
    {"shot": 115, "window": 66},
    {"shot": 116, "window": 62},
    {"shot": 118, "window": 8},
    {"shot": 119, "window": 30},
    {"shot": 121, "window": 48},
    {"shot": 127, "window": 141},
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
    check("pilot binds exact shot range sixty-four through one-twenty-seven", pilot_shots == NEW_SHOTS)
    check("pilot has complete windows", len(pilot["windows"]) == 164)
    check("prior evidence accepted contiguous zero through sixty-three", prior_shots == list(range(64)))
    check("new and prior shot sets are disjoint", not (set(pilot_shots) & set(prior_shots)))
    check("cumulative shot set is contiguous zero through one-twenty-seven", sorted(pilot_shots + prior_shots) == CUMULATIVE_SHOTS)

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
    check("complete sixty-four-shot cardinality", summary["shots"] == 64 and summary["cases"] == 10496)
    check("all closed-loop syndromes valid", summary["all_syndromes_valid"] is True)
    check("all committed residuals clear", summary["commit_residual_failures"] == 0)
    check("all final residuals clear", summary["final_residual_failures"] == 0)
    check("all final logical frames match", summary["final_frame_failures"] == 0)
    check("closed-loop semantic gate accepted", summary["accepted_closed_loop_gate"] is True)
    check("occupancy audit complete", raw["occupancy_audit"] == {
        "checks": 105733,
        "expected_checks": 105733,
        "all_clear": True,
    })
    check("all case rows individually pass", all(
        row["syndrome_valid"] and row["commit_residual_clear"]
        for row in raw["cases"]
    ))

    initiators = [
        {"shot": row["shot"], "window": row["window"]}
        for row in open_loop_evidence["diagnosis"]["mismatches"]
        if row["shot"] in NEW_SHOTS
    ]
    check("open-loop evidence identifies exact fourteen initiators", initiators == EXPECTED_INITIATORS)
    check("open-loop trial contains twenty-one total correction mismatches", open_loop_evidence["trial"]["exact_correction_mismatches"] == 21)

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
    check("closed-loop divergences occur only in fourteen response windows", divergent == EXPECTED_RESPONSES)

    rows_by_key = {(row["shot"], row["window"]): row for row in raw["cases"]}
    check("all fourteen response windows clear commit residuals", all(
        rows_by_key[(row["shot"], row["window"])]["commit_residual_clear"]
        for row in EXPECTED_RESPONSES
    ))
    check("all fourteen trajectories reconverge by following window", all(
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

    prior_sensitive = prior["cumulative_feedback_sensitive_shots"]
    cumulative_sensitive = prior_sensitive + [row["shot"] for row in EXPECTED_INITIATORS]
    all_open_loop_sensitive = [
        row["shot"] for row in open_loop_evidence["diagnosis"]["mismatches"]
    ]
    check("prior evidence binds first seven feedback-sensitive shots", prior_sensitive == [15, 29, 36, 38, 54, 58, 60])
    check("cumulative prefix covers all twenty-one open-loop mismatches", cumulative_sensitive == all_open_loop_sensitive)
    check("all open-loop mismatch shots are within accepted prefix", all(shot < 128 for shot in all_open_loop_sensitive))

    evidence: dict[str, Any] = {
        "schema": "b2_b7_p023_d6_x_closed_loop_shard_0064_0127_evidence_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "closed_loop_x_prefix_128_covers_all_21_open_loop_divergences",
        "checks": checks,
        "new_closed_loop_result": {
            "shots": NEW_SHOTS,
            "cases": 10496,
            "syndrome_valid_cases": 10496,
            "occupancy_checks_clear": 105733,
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
        "cumulative_feedback_sensitive_shots": cumulative_sensitive,
        "open_loop_mismatch_coverage": {
            "open_loop_mismatches": 21,
            "closed_loop_responses_accepted": 21,
            "coverage_fraction": 1.0,
        },
        "frozen_denominator": {
            "basis": "x",
            "shots": 1024,
            "cases": 167936,
            "accepted_distinct_shots": 128,
            "accepted_cases": 20992,
            "accepted_shot_indices": CUMULATIVE_SHOTS,
            "remaining_shots": 896,
            "remaining_cases": 146944,
            "fraction_tested": 128 / 1024,
        },
        "acceptance": {
            "new_closed_loop_shard": True,
            "all_known_open_loop_divergences_closed_loop_accepted": True,
            "cumulative_x_prefix_zero_through_one_twenty_seven": True,
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
            "Continue the frozen X corpus from shot 128 through the same closed-loop route; "
            "the 21 known open-loop divergences no longer block this route, but full X remains unproven."
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
        "accepted_distinct_x_shots": 128,
        "accepted_x_cases": 20992,
        "closed_loop_responses_over_known_open_loop_mismatches": "21/21",
    }, indent=2))


if __name__ == "__main__":
    main()
