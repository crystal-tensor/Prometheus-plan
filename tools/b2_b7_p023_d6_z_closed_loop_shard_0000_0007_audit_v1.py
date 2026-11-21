#!/usr/bin/env python3
"""Audit the first bounded closed-loop Z RTL shard."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "benchmarks/B2_B7_P023_d6_z_closed_loop_shard_0000_0007_v1.json"
BASE_INPUT = ROOT / "benchmarks/B2_B7_P023_d6_z_phase_primal_dual_input_v1.json"
RAW = ROOT / "results/B2_B7_P023_d6_z_closed_loop_shard_0000_0007_verilator_v1.json"
CAPTURE = ROOT / "results/B2_B7_P023_d6_z_closed_loop_shard_0000_0007_verilator_capture_v1.json"
LOG = ROOT / "results/B2_B7_P023_d6_z_closed_loop_shard_0000_0007_verilator_v1.log"
ACCEPTED = ROOT / "results/B2_B7_P023_d6_explicit_reweight_v2.json"
PATCH = ROOT / "tools/microblossom/d6_z_phase_primal_dual_closed_loop_v1.patch"
SELECTOR = ROOT / "tools/b2_b7_p023_d6_z_selector_server_v1.py"
OUTPUT = ROOT / "results/B2_B7_P023_d6_z_closed_loop_shard_0000_0007_evidence_v1.json"

SHOTS = list(range(8))
WINDOWS_PER_SHOT = 164
CASES = len(SHOTS) * WINDOWS_PER_SHOT
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
    accepted = read(ACCEPTED)
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool) -> None:
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    pilot_shots = [row["shot"] for row in pilot["shots"]]
    check("pilot binds exact Z shot prefix zero through seven", pilot_shots == SHOTS)
    check("pilot declares Z basis", pilot["basis"] == "z")
    check("pilot has complete windows", len(pilot["windows"]) == WINDOWS_PER_SHOT)
    accepted_z = next(row for row in accepted["corpora"] if row["basis"] == "z")
    check("accepted Z corpus hash bound", pilot["accepted_corpus_sha256"] == accepted_z["corpus_sha256"])
    check("base input evidence bound", raw["base_input_evidence_id"] == base_input["evidence_id"])
    check("pilot evidence bound", raw["pilot_evidence_id"] == pilot["evidence_id"])
    check("runtime corpus hash bound", raw["accepted_corpus_sha256"] == pilot["accepted_corpus_sha256"])

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
    check("complete eight-shot cardinality", summary["shots"] == len(SHOTS) and summary["cases"] == CASES)
    check("all closed-loop syndromes valid", summary["all_syndromes_valid"] is True)
    check("all committed residuals clear", summary["commit_residual_failures"] == 0)
    check("all final residuals clear", summary["final_residual_failures"] == 0)
    check("all final logical frames match", summary["final_frame_failures"] == 0)
    check("closed-loop semantic gate accepted", summary["accepted_closed_loop_gate"] is True)
    check("occupancy audit complete", raw["occupancy_audit"] == {
        "checks": 13498,
        "expected_checks": 13498,
        "all_clear": True,
    })
    check("all case rows individually pass", all(
        row["syndrome_valid"] and row["commit_residual_clear"]
        for row in raw["cases"]
    ))
    check("raw rows cover every shot and window exactly once", {
        (row["shot"], row["window"]) for row in raw["cases"]
    } == {(shot, window) for shot in SHOTS for window in range(WINDOWS_PER_SHOT)})

    evidence: dict[str, Any] = {
        "schema": "b2_b7_p023_d6_z_closed_loop_shard_0000_0007_evidence_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "first_bounded_closed_loop_z_rtl_shard_pass",
        "checks": checks,
        "closed_loop_result": {
            "shots": SHOTS,
            "cases": CASES,
            "syndrome_valid_cases": CASES,
            "occupancy_checks_clear": 13498,
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
            "accepted_distinct_shots": len(SHOTS),
            "accepted_cases": CASES,
            "accepted_shot_indices": SHOTS,
            "remaining_shots": FROZEN_SHOTS - len(SHOTS),
            "remaining_cases": FROZEN_CASES - CASES,
            "fraction_tested": len(SHOTS) / FROZEN_SHOTS,
        },
        "acceptance": {
            "first_bounded_z_closed_loop_shard": True,
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
        "excluded_from_acceptance_design": {
            "qubits": 120,
            "circuit_depth": 7000,
            "reason": "capacity exploration only; not part of this QEC evidence gate",
        },
        "next_gate": (
            "Continue the frozen Z corpus from shot 8 through the same closed-loop route; "
            "do not infer full Z, FPGA behavior, or hardware latency from this bounded shard."
        ),
        "sources": {
            str(path.relative_to(ROOT)): sha_path(path)
            for path in (PILOT, BASE_INPUT, RAW, CAPTURE, LOG, ACCEPTED, PATCH, SELECTOR)
        },
    }
    evidence["evidence_id"] = hashlib.sha256(compact(evidence)).hexdigest()
    OUTPUT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT.relative_to(ROOT)),
        "evidence_id": evidence["evidence_id"],
        "checks": len(checks),
        "accepted_distinct_z_shots": len(SHOTS),
        "accepted_z_cases": CASES,
    }, indent=2))


if __name__ == "__main__":
    main()
