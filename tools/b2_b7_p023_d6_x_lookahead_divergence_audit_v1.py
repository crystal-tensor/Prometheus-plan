#!/usr/bin/env python3
"""Audit the first long-X replay falsifier without relaxing the frozen gate."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import b2_b7_p023_d6_explicit_reweight_v2 as accepted  # noqa: E402


SHARD = ROOT / "benchmarks/B2_B7_P023_d6_x_full_corpus_shard_0009_0135_v1.json"
RAW = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0009_0135_verilator_v1.json"
CAPTURE = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0009_0135_verilator_capture_v1.json"
LOG = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0009_0135_verilator_capture_v1.log"
PATCH = ROOT / "tools/microblossom/d6_x_phase_primal_dual_full_corpus_shard_v8.patch"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_lookahead_divergence_evidence_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    shard = read(SHARD)
    raw = read(RAW)
    capture = read(CAPTURE)
    source_result = read(accepted.DEFAULT_RESULT)
    scale = int(source_result["candidate_contract"]["half_weight_scale"])
    _, compiled, windows, _ = accepted.compile_basis("x", scale)

    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool) -> None:
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    check("frozen shot interval", shard["shot_start"] == 9 and shard["shot_end"] == 136)
    check("case cardinality", len(shard["cases"]) == 127 * 164 == len(raw["cases"]))
    check("capture rejected replay gate", capture["accepted_x_shard_real_rtl_gate"] is False)
    check("process rejected exact-correction mismatch", capture["exit_code"] == 101)
    check("all syndrome checks passed", raw["summary"]["all_syndromes_valid"] is True)
    check("exact correction gate failed", raw["summary"]["all_corrections_equal"] is False)
    check("occupancy checks complete", raw["occupancy_audit"] == {
        "checks": 210748,
        "expected_checks": 210748,
        "all_clear": True,
    })
    check("simulator pinned", capture["simulator_version"] == "Verilator 5.040 2025-08-30 rev v5.040")
    check("patch bound", capture["source_patch_sha256"] == sha_path(PATCH))
    check("raw output bound", capture["output_sha256"] == sha_path(RAW))
    check("log bound", capture["log_sha256"] == sha_path(LOG))

    commit_map: dict[int, list[int]] = {}
    arrival_map: dict[int, list[int]] = {}
    detection_map: dict[int, list[int]] = {}
    for window_index, baseline in enumerate(compiled.windows):
        for detector in map(int, baseline.commit_detectors):
            commit_map.setdefault(detector, []).append(window_index)
        for detector in map(int, baseline.arrival_detectors):
            arrival_map.setdefault(detector, []).append(window_index)
        for detector in map(int, baseline.detection_detectors):
            detection_map.setdefault(detector, []).append(window_index)

    mismatches: list[dict[str, Any]] = []
    delta_rows: list[dict[str, Any]] = []
    for expected, actual in zip(shard["cases"], raw["cases"], strict=True):
        if actual["correction_equal"]:
            continue
        assert expected["shot"] == actual["shot"]
        assert expected["window"] == actual["window"]
        expected_value = int(expected["expected_correction_hex"], 16)
        actual_value = int(actual["correction_hex"], 16)
        delta = expected_value ^ actual_value
        phase_window = windows[actual["window"]]
        delta_bits = [
            bit for bit in range(expected["fault_id_count"]) if (delta >> bit) & 1
        ]
        observable_start = len(phase_window.detector_outputs)
        mismatch = {
            "shot": actual["shot"],
            "window": actual["window"],
            "phase": actual["phase"],
            "delta_bits": delta_bits,
            "delta_bit_count": len(delta_bits),
            "observable_delta_bits": [bit for bit in delta_bits if bit >= observable_start],
            "syndrome_valid": actual["syndrome_valid"],
        }
        mismatches.append(mismatch)
        for bit in delta_bits:
            if bit >= observable_start:
                delta_rows.append({**mismatch, "bit": bit, "kind": "observable"})
                continue
            global_detector = int(phase_window.detector_outputs[bit])
            delta_rows.append({
                "shot": actual["shot"],
                "window": actual["window"],
                "bit": bit,
                "kind": "detector",
                "global_detector": global_detector,
                "arrival_windows": arrival_map.get(global_detector, []),
                "detection_windows": detection_map.get(global_detector, []),
                "commit_windows": commit_map.get(global_detector, []),
            })

    check("mismatch count reproduced", len(mismatches) == 21)
    check("all mismatches remain syndrome-valid", all(row["syndrome_valid"] for row in mismatches))
    check("observable frame unchanged", all(not row["observable_delta_bits"] for row in mismatches))
    check("all deltas are detector corrections", all(row["kind"] == "detector" for row in delta_rows))
    check("all divergent detectors commit next window", all(
        row["commit_windows"] == [row["window"] + 1] for row in delta_rows
    ))
    check("all divergent detectors were prior arrivals", all(
        row["arrival_windows"] == [row["window"] - 1] for row in delta_rows
    ))
    check("all divergent detectors span three-window detection", all(
        row["detection_windows"] == [row["window"] - 1, row["window"], row["window"] + 1]
        for row in delta_rows
    ))

    evidence: dict[str, Any] = {
        "schema": "b2_b7_p023_d6_x_lookahead_divergence_evidence_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "classification": "x_open_loop_replay_gate_falsified_by_next_window_correction_divergence",
        "checks": checks,
        "trial": {
            "shot_start": 9,
            "shot_end": 136,
            "shots": 127,
            "cases": 20828,
            "syndrome_valid_cases": 20828,
            "occupancy_checks_clear": 210748,
            "exact_correction_mismatches": len(mismatches),
            "mismatch_rate": len(mismatches) / len(raw["cases"]),
            "unique_divergent_detectors": len({row["global_detector"] for row in delta_rows}),
            "observable_frame_mismatches": 0,
        },
        "diagnosis": {
            "mismatches": mismatches,
            "delta_rows": delta_rows,
            "finding": (
                "Every correction delta is a detector carried by the three-window overlap and "
                "committed in the immediately following window. A frozen open-loop defect replay "
                "therefore cannot establish sequential correctness after the first delta."
            ),
        },
        "acceptance": {
            "trial_accepted_as_full_x_progress": False,
            "previous_nine_shot_evidence_revoked": False,
            "accepted_frozen_x_shots": 9,
            "accepted_frozen_x_cases": 1476,
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
            "Build a closed-loop RTL harness that applies each actual correction to the persistent "
            "detector state before deriving the next window syndrome and selector set."
        ),
        "sources": {
            str(path.relative_to(ROOT)): sha_path(path)
            for path in (SHARD, RAW, CAPTURE, LOG, PATCH)
        },
    }
    evidence["evidence_id"] = hashlib.sha256(compact(evidence)).hexdigest()
    OUTPUT.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(OUTPUT.relative_to(ROOT)),
        "evidence_id": evidence["evidence_id"],
        "checks": len(checks),
        "mismatches": len(mismatches),
        "unique_divergent_detectors": evidence["trial"]["unique_divergent_detectors"],
    }, indent=2))


if __name__ == "__main__":
    main()
