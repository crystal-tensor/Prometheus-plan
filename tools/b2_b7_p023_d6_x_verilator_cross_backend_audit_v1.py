#!/usr/bin/env python3
"""Audit replay equivalence and measured X-corpus Verilator throughput."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SHARD_0 = ROOT / "benchmarks/B2_B7_P023_d6_x_full_corpus_shard_0000_v1.json"
SHARD_1_8 = ROOT / "benchmarks/B2_B7_P023_d6_x_full_corpus_shard_0001_0008_v1.json"
ICARUS_RAW = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_rtl_v1.json"
ICARUS_CAPTURE = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_capture_v1.json"
VERILATOR_0_RAW = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_verilator_v1.json"
VERILATOR_0_CAPTURE = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_verilator_capture_v1.json"
VERILATOR_0_LOG = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_verilator_capture_v1.log"
VERILATOR_1_8_RAW = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0001_0008_verilator_v1.json"
VERILATOR_1_8_CAPTURE = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0001_0008_verilator_capture_v1.json"
VERILATOR_1_8_LOG = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0001_0008_verilator_capture_v1.log"
PATCH = ROOT / "tools/microblossom/d6_x_phase_primal_dual_full_corpus_shard_v8.patch"
TOOLCHAIN = ROOT / "results/B2_B7_P023_verilator_5_040_toolchain_v1.json"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_verilator_cross_backend_evidence_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def simulation_seconds(path: Path) -> float:
    match = re.search(r"Simulation done in ([0-9.]+) ms", path.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError(f"missing simulation duration in {path}")
    return float(match.group(1)) / 1000.0


def main() -> None:
    shard_0 = read(SHARD_0)
    shard_1_8 = read(SHARD_1_8)
    icarus_raw = read(ICARUS_RAW)
    icarus_capture = read(ICARUS_CAPTURE)
    verilator_0_raw = read(VERILATOR_0_RAW)
    verilator_0_capture = read(VERILATOR_0_CAPTURE)
    verilator_1_8_raw = read(VERILATOR_1_8_RAW)
    verilator_1_8_capture = read(VERILATOR_1_8_CAPTURE)
    toolchain = read(TOOLCHAIN)

    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool) -> None:
        checks.append({"name": name, "passed": bool(passed)})
        if not passed:
            raise ValueError(f"audit failed: {name}")

    check("single-shot Icarus capture accepted", icarus_capture["accepted_x_shard_real_rtl_gate"])
    check("single-shot Verilator capture accepted", verilator_0_capture["accepted_x_shard_real_rtl_gate"])
    check("eight-shot Verilator capture accepted", verilator_1_8_capture["accepted_x_shard_real_rtl_gate"])
    check("Verilator version pinned", verilator_0_capture["simulator_version"] == "Verilator 5.040 2025-08-30 rev v5.040")
    check("toolchain manifest binds Verilator version", toolchain["verilator"]["reported_version"] == verilator_0_capture["simulator_version"])
    check("Verilator captures have no unexpected warnings", not verilator_0_capture["unexpected_warning_lines"] and not verilator_1_8_capture["unexpected_warning_lines"])
    check("single-shot outputs are byte-identical", sha256(ICARUS_RAW) == sha256(VERILATOR_0_RAW))
    check("single-shot output metadata binds exact files", icarus_capture["output_sha256"] == sha256(ICARUS_RAW) == verilator_0_capture["output_sha256"] == sha256(VERILATOR_0_RAW))
    check("eight-shot output metadata binds exact file", verilator_1_8_capture["output_sha256"] == sha256(VERILATOR_1_8_RAW))
    check("single-shot shard binding", icarus_raw["shard_evidence_id"] == verilator_0_raw["shard_evidence_id"] == shard_0["evidence_id"])
    check("eight-shot shard binding", verilator_1_8_raw["shard_evidence_id"] == shard_1_8["evidence_id"])
    check("disjoint contiguous shot intervals", shard_0["shot_start"] == 0 and shard_0["shot_end"] == shard_1_8["shot_start"] == 1 and shard_1_8["shot_end"] == 9)
    check("frozen corpus binding", shard_0["accepted_corpus_sha256"] == shard_1_8["accepted_corpus_sha256"] == "86185652355a9197eabc0503945820837dbf497ff822812f37f47a0e26836e89")
    check("frozen prediction binding", shard_0["accepted_candidate_prediction_sha256"] == shard_1_8["accepted_candidate_prediction_sha256"] == "3c9e23b747a0527ad15a042954a1cf7a6c1be31501450c7c3e0b1366360e1331")
    check("eight-shot case cardinality", len(shard_1_8["cases"]) == 8 * 164 and verilator_1_8_raw["summary"]["cases"] == 8 * 164)
    check("eight-shot syndrome gate", verilator_1_8_raw["summary"]["all_syndromes_valid"] is True)
    check("eight-shot correction gate", verilator_1_8_raw["summary"]["all_corrections_equal"] is True)
    check("eight-shot occupancy gate", verilator_1_8_raw["occupancy_audit"] == {"checks": 12990, "expected_checks": 12990, "all_clear": True})
    check("v8 patch binding", verilator_0_capture["source_patch_sha256"] == verilator_1_8_capture["source_patch_sha256"] == sha256(PATCH))

    icarus_body = 439.699413
    verilator_0_body = simulation_seconds(VERILATOR_0_LOG)
    verilator_1_8_body = simulation_seconds(VERILATOR_1_8_LOG)
    cases_tested = 9 * 164
    denominator_cases = 1024 * 164
    payload: dict[str, Any] = {
        "schema": "b2_b7_p023_d6_x_verilator_cross_backend_evidence_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "x_cross_backend_replay_equivalent_nine_shots_pass",
        "checks": checks,
        "cross_backend_equivalence": {
            "icarus_output_sha256": sha256(ICARUS_RAW),
            "verilator_output_sha256": sha256(VERILATOR_0_RAW),
            "byte_identical": True,
            "cases": 164,
        },
        "frozen_denominator": {
            "basis": "x",
            "shots": 1024,
            "windows_per_shot": 164,
            "cases": denominator_cases,
            "tested_shots": 9,
            "tested_cases": cases_tested,
            "fraction_tested": cases_tested / denominator_cases,
            "remaining_shots": 1015,
            "remaining_cases": denominator_cases - cases_tested,
        },
        "verilator_result": {
            "simulator": verilator_0_capture["simulator_version"],
            "single_shot_cases": 164,
            "eight_shot_cases": 1312,
            "all_syndromes_valid": True,
            "all_corrections_equal": True,
            "all_occupancy_checks_clear": True,
            "occupancy_checks": 1648 + 12990,
            "maximum_iterations": max(icarus_raw["summary"]["max_iterations"], verilator_1_8_raw["summary"]["max_iterations"]),
        },
        "software_simulation_cost": {
            "icarus_single_shot_body_seconds": icarus_body,
            "verilator_single_shot_body_seconds": verilator_0_body,
            "single_shot_body_speedup": icarus_body / verilator_0_body,
            "verilator_eight_shot_body_seconds": verilator_1_8_body,
            "verilator_eight_shot_body_seconds_per_case": verilator_1_8_body / 1312,
            "verilator_eight_shot_body_seconds_per_shot": verilator_1_8_body / 8,
            "persistent_1024_shot_body_projection_hours": (verilator_1_8_body / 8) * 1024 / 3600,
            "warning": "Software-host simulation cost only; it is not FPGA or decoder hardware latency.",
        },
        "acceptance": {
            "cross_backend_replay_equivalent": True,
            "nine_frozen_x_shots_real_rtl": True,
            "all_accepted_x_corpus_end_to_end": False,
            "z_basis_phase_bank_switching": False,
            "axi_phase_control_path": False,
            "fpga_fmax_measured": False,
            "p99_le_1us": False,
            "miss_rate_le_1pct": False,
            "full_b2": False,
            "scalable_p023": False,
            "b7_resource_credit": 0,
        },
        "next_gate": "Run the remaining 1015 frozen X shots through the replay-equivalent Verilator path without changing corpus or acceptance rules.",
        "sources": {
            path.relative_to(ROOT).as_posix(): sha256(path)
            for path in (
                SHARD_0,
                SHARD_1_8,
                ICARUS_RAW,
                ICARUS_CAPTURE,
                VERILATOR_0_RAW,
                VERILATOR_0_CAPTURE,
                VERILATOR_0_LOG,
                VERILATOR_1_8_RAW,
                VERILATOR_1_8_CAPTURE,
                VERILATOR_1_8_LOG,
                PATCH,
                TOOLCHAIN,
            )
        },
    }
    payload["evidence_id"] = hashlib.sha256(compact(payload)).hexdigest()
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT.relative_to(ROOT)),
        "evidence_id": payload["evidence_id"],
        "checks": len(checks),
        "single_shot_body_speedup": payload["software_simulation_cost"]["single_shot_body_speedup"],
        "tested_cases": cases_tested,
    }, indent=2))


if __name__ == "__main__":
    main()
