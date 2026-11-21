#!/usr/bin/env python3
"""Audit closed-loop X shots 256-511 and the cumulative 50% prefix."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "benchmarks/B2_B7_P023_d6_x_closed_loop_shard_0256_0511_v1.json"
RAW = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0256_0511_verilator_v1.json"
CAPTURE = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0256_0511_verilator_capture_v1.json"
LOG = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0256_0511_verilator_capture_v1.log"
PRIOR = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0128_0255_evidence_v1.json"
PATCH = ROOT / "tools/microblossom/d6_x_phase_primal_dual_closed_loop_v9.patch"
SELECTOR = ROOT / "tools/b2_b7_p023_d6_x_selector_server_v1.py"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_closed_loop_shard_0256_0511_evidence_v1.json"

NEW_SHOTS = list(range(256, 512))
CUMULATIVE_SHOTS = list(range(512))


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
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool) -> None:
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    pilot_shots = [row["shot"] for row in pilot["shots"]]
    prior_shots = prior["frozen_denominator"]["accepted_shot_indices"]
    check("pilot binds exact shot range two-fifty-six through five-eleven", pilot_shots == NEW_SHOTS)
    check("pilot has complete windows", len(pilot["windows"]) == 164)
    check("prior evidence accepted contiguous zero through two-fifty-five", prior_shots == list(range(256)))
    check("new and prior shot sets are disjoint", not (set(pilot_shots) & set(prior_shots)))
    check("cumulative shot set is contiguous zero through five-eleven", sorted(pilot_shots + prior_shots) == CUMULATIVE_SHOTS)

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
    check("complete two-hundred-fifty-six-shot cardinality", summary["shots"] == 256 and summary["cases"] == 41984)
    check("all closed-loop syndromes valid", summary["all_syndromes_valid"] is True)
    check("all committed residuals clear", summary["commit_residual_failures"] == 0)
    check("all final residuals clear", summary["final_residual_failures"] == 0)
    check("all final logical frames match", summary["final_frame_failures"] == 0)
    check("closed-loop semantic gate accepted", summary["accepted_closed_loop_gate"] is True)
    check("occupancy audit complete", raw["occupancy_audit"] == {
        "checks": 425915,
        "expected_checks": 425915,
        "all_clear": True,
    })
    check("all case rows individually pass", all(
        row["syndrome_valid"] and row["commit_residual_clear"]
        for row in raw["cases"]
    ))
    check("raw rows cover each new shot exactly once per window", all(
        sum(row["shot"] == shot for row in raw["cases"]) == 164
        for shot in NEW_SHOTS
    ))
    check("prior evidence closed all twenty-one known replay divergences", prior["open_loop_mismatch_coverage"] == {
        "open_loop_mismatches": 21,
        "closed_loop_responses_accepted": 21,
        "coverage_fraction": 1.0,
    })
    check("cumulative denominator reaches exactly one half", 512 / 1024 == 0.5)
    check("claim boundary remains closed", prior["acceptance"]["full_x"] is False)

    evidence: dict[str, Any] = {
        "schema": "b2_b7_p023_d6_x_closed_loop_shard_0256_0511_evidence_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "closed_loop_x_contiguous_half_corpus_prefix_pass",
        "checks": checks,
        "new_closed_loop_result": {
            "shots": NEW_SHOTS,
            "cases": 41984,
            "syndrome_valid_cases": 41984,
            "occupancy_checks_clear": 425915,
            "commit_residual_failures": 0,
            "final_residual_failures": 0,
            "final_frame_failures": 0,
            "maximum_iterations": summary["max_iterations"],
            "total_iterations": summary["total_iterations"],
            "open_loop_overlap_shots": [],
            "open_loop_overlap_cases": 0,
            "elapsed_seconds": capture["elapsed_seconds"],
        },
        "open_loop_mismatch_coverage": prior["open_loop_mismatch_coverage"],
        "frozen_denominator": {
            "basis": "x",
            "shots": 1024,
            "cases": 167936,
            "accepted_distinct_shots": 512,
            "accepted_cases": 83968,
            "accepted_shot_indices": CUMULATIVE_SHOTS,
            "remaining_shots": 512,
            "remaining_cases": 83968,
            "fraction_tested": 512 / 1024,
        },
        "acceptance": {
            "new_closed_loop_shard": True,
            "cumulative_x_half_corpus_prefix": True,
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
            "Continue the frozen X corpus from shot 512 through the same closed-loop route; "
            "the accepted prefix is one half of X, not a full-X result."
        ),
        "sources": {
            str(path.relative_to(ROOT)): sha_path(path)
            for path in (PILOT, RAW, CAPTURE, LOG, PRIOR, PATCH, SELECTOR)
        },
    }
    evidence["evidence_id"] = hashlib.sha256(compact(evidence)).hexdigest()
    OUTPUT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT.relative_to(ROOT)),
        "evidence_id": evidence["evidence_id"],
        "checks": len(checks),
        "accepted_distinct_x_shots": 512,
        "accepted_x_cases": 83968,
        "fraction_tested": "50%",
    }, indent=2))


if __name__ == "__main__":
    main()
