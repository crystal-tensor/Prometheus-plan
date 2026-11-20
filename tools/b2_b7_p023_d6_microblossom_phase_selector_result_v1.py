#!/usr/bin/env python3
"""Build evidence for opening/closing resident-selector RTL replay."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "results/B2_B7_P023_d6_microblossom_phase_batch_trace_v1.json"
TRANSCRIPT = ROOT / "results/B2_B7_P023_d6_microblossom_phase_selector_sim_v1.log"
HARNESS = ROOT / "tools/microblossom/D6PhaseResidentRuleSelectorReplay.scala"
DYNAMIC_PATCH = ROOT / "tools/patches/micro_blossom_a3530d9_dynamic_weight_sideband.patch"
SELECTOR_PATCH = ROOT / "tools/patches/micro_blossom_a3530d9_resident_rule_selector_on_dynamic_patch.patch"
IMAGE_DIR = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_images_v1"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_microblossom_phase_selector_rtl_v1.json"

BATCH = re.compile(
    r"PHASE_SELECTOR_BATCH_PASS basis=(x|z) phase=(opening|closing) "
    r"boundary=(maximum|p50|p99|zero) selectors=(\d+) updates=(\d+) "
    r"checked_edges=(\d+) axi_write_span_slow_cycles=(\d+)"
)
ARTIFACT = re.compile(
    r"PHASE_RTL_ARTIFACT basis=(x|z) phase=(opening|closing) "
    r"verilog_bytes=(\d+) verilog_sha256=([0-9a-f]{64}) "
    r"vvp_bytes=(\d+) vvp_sha256=([0-9a-f]{64})"
)


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    trace = read(TRACE)
    transcript = TRANSCRIPT.read_text(encoding="utf-8")
    observed = {
        (basis, phase, boundary): {
            "selected_source_edges": int(selectors),
            "expected_weight_updates": int(updates),
            "checked_edges": int(edges),
            "axi_write_span_slow_cycles": int(cycles),
        }
        for basis, phase, boundary, selectors, updates, edges, cycles
        in BATCH.findall(transcript)
    }
    artifacts = {
        (basis, phase): {
            "generated_verilog_bytes": int(verilog_bytes),
            "generated_verilog_sha256": verilog_sha,
            "generated_vvp_bytes": int(vvp_bytes),
            "generated_vvp_sha256": vvp_sha,
        }
        for basis, phase, verilog_bytes, verilog_sha, vvp_bytes, vvp_sha
        in ARTIFACT.findall(transcript)
    }
    if len(observed) != 16 or len(artifacts) != 4:
        raise ValueError("incomplete phase RTL transcript")

    trace_rows = {row["basis"]: row for row in trace["basis_rows"]}
    phase_rows: list[dict[str, Any]] = []
    total_checks = 0
    for basis in ("x", "z"):
        trace_phases = {
            row["phase"]: row for row in trace_rows[basis]["phases"]
        }
        for phase in ("opening", "closing"):
            image_path = IMAGE_DIR / f"{basis}_{phase}.json"
            image = read(image_path)
            metadata = image["qec_image_metadata"]
            trace_phase = trace_phases[phase]
            reps = []
            for boundary in ("zero", "p50", "p99", "maximum"):
                record = trace_phase["representative_batches"][boundary]
                measured = observed[(basis, phase, boundary)]
                if measured["selected_source_edges"] != len(record["selected_edge_indices"]):
                    raise ValueError(f"{basis}/{phase}/{boundary}: selector mismatch")
                if measured["expected_weight_updates"] != len(record["updates"]):
                    raise ValueError(f"{basis}/{phase}/{boundary}: update mismatch")
                if measured["checked_edges"] != len(image["weighted_edges"]):
                    raise ValueError(f"{basis}/{phase}/{boundary}: edge mismatch")
                if measured["axi_write_span_slow_cycles"] != 2 * len(record["selected_edge_indices"]):
                    raise ValueError(f"{basis}/{phase}/{boundary}: cycle mismatch")
                reps.append({
                    "boundary": boundary,
                    **measured,
                    "pass": True,
                })
                total_checks += measured["checked_edges"]
            phase_rows.append({
                "basis": basis,
                "phase": phase,
                "image": str(image_path.relative_to(ROOT)),
                "image_sha256": sha(image_path),
                "graph_edges": len(image["weighted_edges"]),
                "directed_rules": int(metadata["directed_rules"]),
                "active_resident_rules": int(metadata["active_lowering_rules"]),
                "accepted_phase_batches": int(trace_phase["batches"]),
                "accepted_update_distribution": trace_phase["hardware_update_edges"],
                "accepted_selector_distribution": trace_phase["selected_source_edges"],
                "representative_replay": reps,
                **artifacts[(basis, phase)],
            })

    result: dict[str, Any] = {
        "schema": "b2_b7_p023_d6_microblossom_phase_selector_rtl_v1",
        "date": "2026-11-21",
        "classification": "opening_closing_representative_resident_selector_rtl_replay_pass_no_runtime_switch_timing_or_resource_credit",
        "scope": ["021/B7", "022/B2", "023"],
        "source": {
            "phase_batch_trace": str(TRACE.relative_to(ROOT)),
            "phase_batch_trace_sha256": sha(TRACE),
            "phase_batch_trace_evidence_id": trace["evidence_id"],
            "simulation_transcript": str(TRANSCRIPT.relative_to(ROOT)),
            "simulation_transcript_sha256": sha(TRANSCRIPT),
            "simulation_harness": str(HARNESS.relative_to(ROOT)),
            "simulation_harness_sha256": sha(HARNESS),
        },
        "implementation": {
            "micro_blossom_commit": "a3530d9e58ff790dafc93d56c9a2769ceac84731",
            "prerequisite_dynamic_weight_patch": str(DYNAMIC_PATCH.relative_to(ROOT)),
            "prerequisite_dynamic_weight_patch_sha256": sha(DYNAMIC_PATCH),
            "resident_selector_patch": str(SELECTOR_PATCH.relative_to(ROOT)),
            "resident_selector_patch_sha256": sha(SELECTOR_PATCH),
            "axi_selector_window": "0x4000-0x4fff",
            "exact_edge_semantics": "on reset restore base; on each selected source, every matching target stores min(current, resident replacement)",
        },
        "rtl_generation": {
            "spinalhdl_version": "1.9.3",
            "iverilog_version": "13.0",
            "java": "Homebrew OpenJDK 17.0.21.0.3",
            "phase_images_generated": 4,
            "phase_images_compiled": 4,
            "generated_artifacts_committed": False,
            "phase_rows": phase_rows,
        },
        "representative_rtl_replay": {
            "phase_images": 4,
            "batches_run": 16,
            "batches_passed": 16,
            "batches_failed": 0,
            "full_edge_state_checks": total_checks,
            "full_edge_state_checks_passed": total_checks,
            "mismatches": 0,
        },
        "transport": {
            "measured_slow_cycles_per_selector_command": 2,
            "representative_p99_slow_cycles": {
                f"{row['basis']}_{row['phase']}": next(
                    rep["axi_write_span_slow_cycles"]
                    for rep in row["representative_replay"]
                    if rep["boundary"] == "p99"
                )
                for row in phase_rows
            },
            "accepted_distribution_p99_update_only_slow_cycles": {
                f"{row['basis']}_{row['phase']}":
                    int(row["accepted_selector_distribution"]["p99"]) * 2
                for row in phase_rows
            },
            "distribution_cycle_classification": "projected_from_all_4096_accepted_phase_batches_not_full_rtl_replay",
        },
        "acceptance": {
            "opening_closing_representative_edge_state_rtl_replay": True,
            "runtime_phase_switching_implemented": False,
            "all_accepted_phase_batches_replayed_in_rtl": False,
            "rtl_corrections_compared": False,
            "fpga_fmax_measured": False,
            "lut_bram_measured": False,
            "full_update_plus_decode_p99_cycles_measured": False,
            "p99_le_1us": False,
            "miss_rate_le_1pct": False,
            "full_b2": False,
            "scalable_p023": False,
            "b7_resource_credit": 0,
        },
        "next_gate": "Choose and implement an honest opening/steady/closing integration route, then replay complete corrections; separate per-phase RTL images do not establish runtime switching, FPGA timing, or resources.",
    }
    result["evidence_id"] = hashlib.sha256(compact(result)).hexdigest()
    args.output.write_text(canonical(result), encoding="utf-8")
    print(canonical(result), end="")


if __name__ == "__main__":
    main()
