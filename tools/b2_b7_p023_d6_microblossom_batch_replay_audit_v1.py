#!/usr/bin/env python3
"""Audit representative RTL replay evidence and serial-cycle accounting."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_batch_replay_v1.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, label: str, checks: list[dict[str, Any]]) -> None:
    checks.append({"label": label, "pass": bool(condition)})
    if not condition:
        raise AssertionError(label)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    args = parser.parse_args()
    result = json.loads(args.result.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []
    require(result["scope"] == ["021/B7", "022/B2", "023"], "strict scope", checks)
    source = result["source"]
    trace_path = ROOT / source["accepted_batch_trace"]
    harness_path = ROOT / source["simulation_harness"]
    transcript_path = ROOT / source["simulation_transcript"]
    require(sha(trace_path) == source["accepted_batch_trace_sha256"], "trace hash", checks)
    require(sha(harness_path) == source["simulation_harness_sha256"], "harness hash", checks)
    require(sha(transcript_path) == source["simulation_transcript_sha256"], "transcript hash", checks)
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    require(trace["evidence_id"] == source["accepted_batch_trace_evidence_id"],
            "trace evidence id", checks)
    trace_rows = {row["basis"]: row for row in trace["basis_rows"]}
    bound = result["accepted_batch_trace"]
    for basis in ("x", "z"):
        row = trace_rows[basis]
        require(bound[f"{basis}_window_batches"] == row["window_batches"],
                f"{basis}: window batches", checks)
        require(bound[f"{basis}_unique_update_batches"] == row["unique_update_batches"],
                f"{basis}: unique batches", checks)
        require(bound[f"{basis}_total_update_writes"] == row["total_update_writes"],
                f"{basis}: total writes", checks)
        require(bound[f"{basis}_update_edges_p99"] == int(row["hardware_update_edges"]["p99"]),
                f"{basis}: p99", checks)
        require(bound[f"{basis}_update_edges_maximum"] == int(row["hardware_update_edges"]["maximum"]),
                f"{basis}: maximum", checks)
    replay = result["representative_rtl_replay"]
    require(replay["batches_run"] == replay["batches_passed"] == 8 and
            replay["batches_failed"] == 0, "eight representative passes", checks)
    require(replay["full_edge_state_checks"] ==
            replay["full_edge_state_checks_passed"] == 8 * replay["graph_edges"],
            "full edge-state coverage", checks)
    rows = {(row["basis"], row["boundary"]): row for row in replay["rows"]}
    require(len(rows) == 8 and all(row["pass"] for row in rows.values()),
            "unique passing replay rows", checks)
    for basis in ("x", "z"):
        examples = trace_rows[basis]["representative_batches"]
        for boundary in ("zero", "p50", "p99", "maximum"):
            row = rows[(basis, boundary)]
            expected_updates = len(examples[boundary]["updates"])
            require(row["updates"] == expected_updates,
                    f"{basis}/{boundary}: trace update count", checks)
            require(row["axi_write_span_slow_cycles"] == 2 * expected_updates,
                    f"{basis}/{boundary}: two cycles per update", checks)
    pressure = result["serial_update_pressure"]
    require(pressure["x_p99_update_only_cycles"] == rows[("x", "p99")]["axi_write_span_slow_cycles"],
            "X p99 cycle binding", checks)
    require(pressure["z_p99_update_only_cycles"] == rows[("z", "p99")]["axi_write_span_slow_cycles"],
            "Z p99 cycle binding", checks)
    require(pressure["x_p99_minimum_slow_clock_mhz_for_one_microsecond"] ==
            pressure["x_p99_update_only_cycles"], "X clock arithmetic", checks)
    require(pressure["z_p99_minimum_slow_clock_mhz_for_one_microsecond"] ==
            pressure["z_p99_update_only_cycles"], "Z clock arithmetic", checks)
    require(pressure["reset_decode_and_output_cycles_included"] is False and
            pressure["fpga_fmax_measured"] is False and
            pressure["one_microsecond_deadline_credit"] is False,
            "timing boundary", checks)
    acceptance = result["acceptance"]
    require(acceptance["representative_steady_edge_state_rtl_replay"] is True,
            "representative credit", checks)
    require(acceptance["all_accepted_window_batches_replayed_in_rtl"] is False and
            acceptance["rtl_corrections_compared"] is False,
            "full replay boundary", checks)
    require(acceptance["p99_le_1us"] is False and
            acceptance["miss_rate_le_1pct"] is False,
            "deadline boundary", checks)
    require(acceptance["full_b2"] is False and
            acceptance["scalable_p023"] is False and
            acceptance["b7_resource_credit"] == 0,
            "downstream credit closed", checks)
    transcript = transcript_path.read_text(encoding="utf-8")
    for row in replay["rows"]:
        needle = (
            f"REPRESENTATIVE_BATCH_PASS name={row['basis']}/{row['boundary']} "
            f"updates={row['updates']} checked_edges={replay['graph_edges']} "
            f"axi_write_span_slow_cycles={row['axi_write_span_slow_cycles']}"
        )
        require(needle in transcript, f"transcript row {row['basis']}/{row['boundary']}", checks)
    print(json.dumps({
        "classification": "representative_batch_rtl_replay_audit_pass",
        "checks_passed": sum(row["pass"] for row in checks),
        "checks_total": len(checks),
        "checks": checks,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
