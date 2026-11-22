#!/usr/bin/env python3
"""Audit Z shots 256-511 and the cumulative contiguous closed-loop prefix."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "benchmarks/B2_B7_P023_d6_z_closed_loop_shard_0256_0511_v1.json"
BASE_INPUT = ROOT / "benchmarks/B2_B7_P023_d6_z_phase_primal_dual_input_v1.json"
RAW = ROOT / "results/B2_B7_P023_d6_z_closed_loop_shard_0256_0511_verilator_v1.json"
CAPTURE = ROOT / "results/B2_B7_P023_d6_z_closed_loop_shard_0256_0511_verilator_capture_v1.json"
LOG = ROOT / "results/B2_B7_P023_d6_z_closed_loop_shard_0256_0511_verilator_v1.log"
PRIOR = ROOT / "results/B2_B7_P023_d6_z_closed_loop_shard_0128_0255_evidence_v1.json"
PRIOR_RAW = ROOT / "results/B2_B7_P023_d6_z_closed_loop_shard_0128_0255_verilator_v1.json"
PATCH = ROOT / "tools/microblossom/d6_z_phase_primal_dual_closed_loop_v1.patch"
SELECTOR = ROOT / "tools/b2_b7_p023_d6_z_selector_server_v1.py"
OUTPUT = ROOT / "results/B2_B7_P023_d6_z_closed_loop_shard_0256_0511_evidence_v1.json"

NEW_SHOTS = list(range(256, 512))
CUMULATIVE_SHOTS = list(range(512))
WINDOWS_PER_SHOT = 164
NEW_CASES = len(NEW_SHOTS) * WINDOWS_PER_SHOT
FROZEN_SHOTS = 1024
FROZEN_CASES = FROZEN_SHOTS * WINDOWS_PER_SHOT


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    pilot = read(PILOT)
    base_input = read(BASE_INPUT)
    raw = read(RAW)
    capture = read(CAPTURE)
    prior = read(PRIOR)
    prior_raw = read(PRIOR_RAW)
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool) -> None:
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    pilot_shots = [row["shot"] for row in pilot["shots"]]
    prior_shots = prior["frozen_denominator"]["accepted_shot_indices"]
    check("pilot binds exact Z shots two hundred fifty-six through five hundred eleven", pilot_shots == NEW_SHOTS)
    check("pilot declares Z basis", pilot["basis"] == "z")
    check("pilot has complete windows", len(pilot["windows"]) == WINDOWS_PER_SHOT)
    check("prior evidence accepts exact shots zero through two hundred fifty-five", prior_shots == list(range(256)))
    check("new and prior shot sets are disjoint", not (set(pilot_shots) & set(prior_shots)))
    check("cumulative Z prefix is contiguous zero through five hundred eleven", sorted(pilot_shots + prior_shots) == CUMULATIVE_SHOTS)
    check("pilot and prior bind the same accepted corpus", pilot["accepted_corpus_sha256"] == prior_raw["accepted_corpus_sha256"])
    check("runtime corpus hash bound", raw["accepted_corpus_sha256"] == pilot["accepted_corpus_sha256"])
    check("base input evidence bound", raw["base_input_evidence_id"] == base_input["evidence_id"])
    check("pilot evidence bound", raw["pilot_evidence_id"] == pilot["evidence_id"])

    check("formal capture accepted", capture["accepted_z_closed_loop_real_rtl_gate"] is True)
    check("formal process exited cleanly", capture["exit_code"] == 0)
    check("Verilator 5.040 pinned", capture["simulator_version"].startswith("Verilator 5.040 2025-08-30"))
    check("pinned source archive bound", capture["source_archive_sha256"] == "284f3e52ab0a3de038821d7b9063ea978c16ec0f8b3a35204f8d862f6595659b")
    check("self-contained Z patch bound", capture["source_patch_sha256"] == sha_path(PATCH))
    check("pilot file bound", capture["pilot_sha256"] == sha_path(PILOT))
    check("base input file bound", capture["base_input_sha256"] == sha_path(BASE_INPUT))
    check("selector server bound", capture["selector_server_sha256"] == sha_path(SELECTOR))
    check("output bound", capture["output_sha256"] == sha_path(RAW))
    check("log bound", capture["log_sha256"] == sha_path(LOG))
    check("no forbidden runtime hits", not capture["forbidden_hits"])
    check("no unexpected warnings", not capture["unexpected_warning_lines"])

    summary = raw["summary"]
    check("complete two-hundred-fifty-six-shot cardinality", summary["shots"] == len(NEW_SHOTS) and summary["cases"] == NEW_CASES)
    check("all closed-loop syndromes valid", summary["all_syndromes_valid"] is True)
    check("all committed residuals clear", summary["commit_residual_failures"] == 0)
    check("all final residuals clear", summary["final_residual_failures"] == 0)
    check("all final logical frames match", summary["final_frame_failures"] == 0)
    check("closed-loop semantic gate accepted", summary["accepted_closed_loop_gate"] is True)
    check("occupancy audit complete", raw["occupancy_audit"] == {
        "checks": 425215,
        "expected_checks": 425215,
        "all_clear": True,
    })
    check("all case rows individually pass", all(
        row["syndrome_valid"] and row["commit_residual_clear"]
        for row in raw["cases"]
    ))
    check("raw rows cover every new shot and window exactly once", {
        (row["shot"], row["window"]) for row in raw["cases"]
    } == {(shot, window) for shot in NEW_SHOTS for window in range(WINDOWS_PER_SHOT)})

    evidence: dict[str, Any] = {
        "schema": "b2_b7_p023_d6_z_closed_loop_shard_0256_0511_evidence_v1",
        "date": "2026-11-22",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "closed_loop_z_rtl_contiguous_prefix_zero_through_five_hundred_eleven_pass",
        "checks": checks,
        "new_closed_loop_result": {
            "shots": NEW_SHOTS,
            "cases": NEW_CASES,
            "syndrome_valid_cases": NEW_CASES,
            "occupancy_checks_clear": 425215,
            "commit_residual_failures": 0,
            "final_residual_failures": 0,
            "final_frame_failures": 0,
            "maximum_iterations": summary["max_iterations"],
            "total_iterations": summary["total_iterations"],
            "elapsed_seconds": capture["elapsed_seconds"],
        },
        "frozen_denominator": {
            "basis": "z",
            "shots": FROZEN_SHOTS,
            "cases": FROZEN_CASES,
            "accepted_distinct_shots": len(CUMULATIVE_SHOTS),
            "accepted_cases": len(CUMULATIVE_SHOTS) * WINDOWS_PER_SHOT,
            "accepted_shot_indices": CUMULATIVE_SHOTS,
            "remaining_shots": FROZEN_SHOTS - len(CUMULATIVE_SHOTS),
            "remaining_cases": FROZEN_CASES - len(CUMULATIVE_SHOTS) * WINDOWS_PER_SHOT,
            "fraction_tested": len(CUMULATIVE_SHOTS) / FROZEN_SHOTS,
        },
        "acceptance": {
            "new_z_closed_loop_shard": True,
            "cumulative_z_prefix_zero_through_five_hundred_eleven": True,
            "full_x": True,
            "full_z": False,
            "axi": False,
            "fpga": False,
            "p99_le_1us": False,
            "miss_rate_le_1pct": False,
            "full_b2": False,
            "scalable_p023": False,
            "b7_resource_credit": 0,
        },
        "next_gate": (
            "Continue the frozen Z corpus from shot 512 under the unchanged closed-loop gate; "
            "host elapsed time is not hardware latency."
        ),
        "sources": {
            str(path.relative_to(ROOT)): sha_path(path)
            for path in (PILOT, BASE_INPUT, RAW, CAPTURE, LOG, PRIOR, PRIOR_RAW, PATCH, SELECTOR)
        },
    }
    evidence["evidence_id"] = hashlib.sha256(compact(evidence)).hexdigest()
    OUTPUT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT.relative_to(ROOT)),
        "evidence_id": evidence["evidence_id"],
        "checks": len(checks),
        "accepted_distinct_z_shots": len(CUMULATIVE_SHOTS),
        "accepted_z_cases": len(CUMULATIVE_SHOTS) * WINDOWS_PER_SHOT,
    }, indent=2))


if __name__ == "__main__":
    main()
