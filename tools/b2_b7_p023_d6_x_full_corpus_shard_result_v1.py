#!/usr/bin/env python3
"""Bind the first complete-shot X real-RTL calibration into scoped evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks/B2_B7_P023_d6_x_phase_primal_dual_input_v1.json"
SHARD = ROOT / "benchmarks/B2_B7_P023_d6_x_full_corpus_shard_0000_v1.json"
RAW = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_rtl_v1.json"
CAPTURE = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_capture_v1.json"
LOG = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_capture_v1.log"
PATCH = ROOT / "tools/microblossom/d6_x_phase_primal_dual_full_corpus_shard_v7.patch"
GENERATOR = ROOT / "tools/b2_b7_p023_d6_x_full_corpus_shard_v1.py"
CAPTURE_TOOL = ROOT / "tools/b2_b7_p023_d6_x_full_corpus_shard_capture_v1.py"
PATCH_TOOL = ROOT / "tools/microblossom/make_exact_source_patch_v1.py"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_evidence_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_entry(path: Path) -> dict[str, str]:
    return {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}


def canonical_id(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("evidence_id", None)
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> None:
    base = read(BASE)
    shard = read(SHARD)
    raw = read(RAW)
    capture = read(CAPTURE)
    rows = raw["cases"]
    log_text = LOG.read_text(encoding="utf-8")
    simulation_match = re.search(r"Simulation done in ([0-9.]+) ms", log_text)
    if simulation_match is None:
        raise ValueError("simulation duration missing from capture log")
    simulation_seconds = float(simulation_match.group(1)) / 1000
    phase_counts = {
        phase: sum(row["phase"] == phase for row in rows)
        for phase in ("opening", "steady", "closing")
    }
    gate = all(
        (
            shard["shots"] == 1,
            shard["windows_per_shot"] == 164,
            shard["commit_residual_failures"] == 0,
            shard["final_residual_failures"] == 0,
            len(rows) == 164,
            raw["summary"]["all_syndromes_valid"],
            raw["summary"]["all_corrections_equal"],
            raw["occupancy_audit"]["all_clear"],
            raw["occupancy_audit"]["checks"]
            == raw["occupancy_audit"]["expected_checks"]
            == 1648,
            capture["accepted_x_shard_real_rtl_gate"],
            capture["exit_code"] == 0,
            not capture["forbidden_hits"],
            not capture["unexpected_warning_lines"],
        )
    )
    payload = {
        "schema": "b2_b7_p023_d6_x_full_corpus_shard_0000_evidence_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": (
            "x_complete_shot_0000_real_rtl_calibration_pass"
            if gate
            else "x_complete_shot_0000_real_rtl_falsifier"
        ),
        "source": {
            "micro_blossom_commit": "a3530d9e58ff790dafc93d56c9a2769ceac84731",
            "micro_blossom_source_archive_sha256": capture["source_archive_sha256"],
            "base_input": source_entry(BASE),
            "shard": source_entry(SHARD),
            "shard_generator": source_entry(GENERATOR),
            "source_patch": source_entry(PATCH),
            "source_patch_generator": source_entry(PATCH_TOOL),
            "capture_tool": source_entry(CAPTURE_TOOL),
            "raw_rtl_run": source_entry(RAW),
            "capture_log": source_entry(LOG),
            "capture_metadata": source_entry(CAPTURE),
        },
        "frozen_denominator": {
            "accepted_x_corpus_sha256": shard["accepted_corpus_sha256"],
            "accepted_candidate_prediction_sha256": shard[
                "accepted_candidate_prediction_sha256"
            ],
            "shots": 1024,
            "windows_per_shot": 164,
            "cases": 167936,
            "tested_shots": 1,
            "tested_cases": len(rows),
            "fraction_tested": len(rows) / 167936,
        },
        "shard_identity": {
            "base_input_evidence_id": base["evidence_id"],
            "shard_evidence_id": shard["evidence_id"],
            "case_sequence_sha256": shard["case_sequence_sha256"],
            "shot_start": shard["shot_start"],
            "shot_end": shard["shot_end"],
            "phase_counts": phase_counts,
        },
        "real_rtl_result": {
            "cases": len(rows),
            "defects": raw["summary"]["total_defects"],
            "selectors": raw["summary"]["total_selectors"],
            "occupancy_checks": raw["occupancy_audit"]["checks"],
            "all_occupancy_checks_clear": raw["occupancy_audit"]["all_clear"],
            "all_syndromes_valid": raw["summary"]["all_syndromes_valid"],
            "all_corrections_equal": raw["summary"]["all_corrections_equal"],
            "maximum_iterations": raw["summary"]["max_iterations"],
            "total_iterations": raw["summary"]["total_iterations"],
            "capture_exit_code": capture["exit_code"],
            "forbidden_hits": capture["forbidden_hits"],
            "unexpected_warning_lines": capture["unexpected_warning_lines"],
            "accepted": gate,
        },
        "simulation_calibration": {
            "simulator": "Icarus Verilog 13.0 hosted by SpinalHDL 1.9.3",
            "captured_end_to_end_seconds": capture["elapsed_seconds"],
            "captured_end_to_end_seconds_per_case": capture[
                "elapsed_seconds_per_case"
            ],
            "reported_simulation_body_seconds": simulation_seconds,
            "reported_simulation_body_seconds_per_case": simulation_seconds / len(rows),
            "naive_1024_shard_end_to_end_hours": capture["elapsed_seconds"]
            * 1024
            / 3600,
            "single_persistent_body_projection_hours": simulation_seconds
            * 1024
            / 3600,
            "projection_warning": (
                "One-shot software-simulator calibration only; workload complexity varies, "
                "parallel contention is unmeasured, and none of these durations is hardware latency."
            ),
        },
        "acceptance": {
            "complete_shot_0000_real_rtl": gate,
            "all_accepted_x_corpus_end_to_end": False,
            "z_basis_phase_bank_switching": False,
            "axi_phase_control_path": False,
            "fpga_fmax_measured": False,
            "lut_bram_measured": False,
            "p99_le_1us": False,
            "miss_rate_le_1pct": False,
            "full_b2": False,
            "scalable_p023": False,
            "b7_resource_credit": 0,
        },
        "claim_boundary": {
            "implemented": (
                "The first frozen X shot's complete 164-window opening/steady/closing "
                "sequence passed the real Rust-primal plus phase-aware DistributedDual path."
            ),
            "not_implemented": [
                "the remaining 1023 accepted X shots",
                "Z-basis phase banks and end-to-end correction",
                "AXI phase control and correction readout",
                "FPGA synthesis, Fmax, LUT/BRAM, routing, or measured hardware latency",
                "p99 at or below one microsecond and miss rate at or below one percent",
            ],
        },
        "next_gate": (
            "Reduce real-RTL corpus cost with a replay-equivalent faster simulator and/or "
            "audited shards, then execute all remaining X shots without changing the frozen corpus."
        ),
    }
    payload["evidence_id"] = canonical_id(payload)
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "classification": payload["classification"],
                "evidence_id": payload["evidence_id"],
                "gate": gate,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
