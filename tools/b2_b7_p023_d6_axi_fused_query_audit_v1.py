#!/usr/bin/env python3
"""Audit a fused query against packed-status RTL with the same logical write schedule."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import b2_b7_p023_d6_axi_cycle_audit_v1 as cycle
import b2_b7_p023_d6_axi_fused_query_record_v1 as record
import b2_b7_p023_d6_axi_lite_replay_v1 as pilot
import b2_b7_p023_d6_axi_packed_status_audit_v1 as packed

require = pilot.require
EXT = (*packed.EXTENSION, "split_tx_sha256")
EXEC = "AXI_FUSED_EXEC_PASS "
EXEC_FIELDS = ("accepted", "executed", "returned", "min_capture_gap")
SKEW = (0, 2, 3)
ORDER = ("simultaneous", "aw_first", "w_first")


def audit_smoke(folder: Path) -> dict:
    paths = record.smoke_paths(folder)
    receipt = pilot.read(paths["capture"])
    require(receipt["schema"] == "b2_b7_p023_d6_axi_fused_query_smoke_capture_v1" and
            receipt["scope"] == pilot.SCOPE and receipt["seed"] == record.SEED and
            receipt["source_commit"] == pilot.SOURCE_COMMIT and
            receipt["source_archive_sha256"] == pilot.ARCHIVE_SHA and
            receipt["sources_sha256"] == record.sources(None), "smoke receipt not bound")
    require(receipt["simulator"].startswith("Icarus Verilog") and
            receipt["started_utc"] < receipt["finished_utc"], "unexpected smoke environment")
    for name in ("positive", *record.CONTROLS):
        require(pilot.file_sha(paths[name]) == receipt["log_sha256"][name], f"unbound {name} smoke log")
    log, lines = packed.read_lines(paths["positive"])
    results = re.findall(r"^AXI_STATUS_SMOKE_RESULT status=(split|packed|fused) result=(.+)$", "\n".join(lines), re.M)
    require(receipt["exit_codes"]["positive"] == 0 and not pilot.BAD_RUNTIME.search(log) and
            [mode for mode, _ in results] == ["split", "packed", "fused"] and
            len({result for _, result in results}) == 1 and lines.count(pilot.PROBE_LINE) == 3,
            "smoke managers did not produce the same result")
    for order in ("aw_first", "w_first"):
        require(lines.count(f"AXI_FUSED_HALF_WRITE_PASS order={order} both_responses_held=1") == 1,
                f"missing {order} partial-write stress")
    require(lines.count("AXI_FUSED_HELD_PASS old=0x80000000 new=0x03ffffff") == 1,
            "missing held-result and new-result pair")
    _, marker = cycle.unique_mark(lines, EXEC)
    accepted, executed, returned, gap = map(cycle.uint, cycle.entries(marker, EXEC, EXEC_FIELDS).values())
    require(accepted == executed == returned and accepted > 0 and gap == 2, "wrong positive sequence count")
    for name, expected_error in record.CONTROLS.items():
        bad, _ = packed.read_lines(paths[name])
        require(receipt["exit_codes"][name] != 0 and expected_error in bad and EXEC not in bad and
                pilot.PROBE_LINE in bad, f"{name} mutation did not reach the intended invariant")
    return {
        "capture_sha256": pilot.file_sha(paths["capture"]), "identical_smoke_result": results[0][1],
        "accepted": accepted, "executed": executed, "returned": returned,
        "aw_first_and_w_first_fenced": True, "held_r_snapshot_stable": True,
        "duplicate_and_early_mutations_rejected": True,
    }


def measure_window(before: dict[str, cycle.Tally], after: dict[str, cycle.Tally],
                   removed: tuple[int, ...], key: tuple[int, ...]) -> None:
    q = len(removed)
    skew = sum(SKEW[n % 3] for n in removed)
    for group in cycle.GROUPS:
        cycles, writes, reads, bhold, rhold, aw_skew = before[group]
        if group == "solve_cmd":
            expected = (cycles - 4 * q - skew, writes - q, reads, bhold, rhold, aw_skew - skew)
        elif group == "obstacle_read":
            expected = (cycles + 2 * q, writes, reads, bhold, rhold, aw_skew)
        elif group == "total":
            expected = (cycles - 2 * q - skew, writes - q, reads, bhold, rhold, aw_skew - skew)
        else:
            expected = before[group]
        require(after[group] == expected, f"unexpected cycle or transaction delta: {key}/{group}")


def audit_basis(folder: Path, basis: str) -> dict:
    arch = record.ROOT / "results"
    baseline = next(r for r in pilot.read(record.BASELINE)["basis_rows"] if r["basis"] == basis)
    require(packed.audit_basis(arch, basis) == baseline, "archived packed comparison no longer verifies")
    paths = record.paths(folder, basis)
    log, lines = packed.read_lines(paths["run"])
    capture = pilot.read(paths["capture"])
    require(capture["schema"] == "b2_b7_p023_d6_axi_fused_query_capture_v1" and
            capture["scope"] == pilot.SCOPE and capture["basis"] == basis and capture["mode"] == "fused" and
            capture["timing_policy"] == record.POLICY and capture["source_commit"] == pilot.SOURCE_COMMIT and
            capture["source_archive_sha256"] == pilot.ARCHIVE_SHA and capture["sources_sha256"] == record.sources(basis),
            "candidate source or scope not bound")
    require(capture["started_utc"] < capture["finished_utc"] and capture["exit_code"] == 0 and
            not pilot.BAD_RUNTIME.search(log), "candidate replay did not pass")
    old_paths = record.packed.paths(arch, basis, "packed")
    old_capture = pilot.read(old_paths["capture"])
    for field in ("simulator_version", "simulator_binary_sha256", "simulator_seed"):
        require(capture[field] == old_capture[field], f"simulator drift: {field}")
    for field in ("generated_endpoint_rtl_sha256", "compiled_model_archive_sha256"):
        require(cycle.digest(capture[field]) and capture[field] != old_capture[field],
                f"candidate was not independently compiled: {field}")
    incl = pilot.inputs(basis)
    direct = pilot.read(incl["direct_raw"])
    frozen = pilot.read(incl["pilot"])
    cases = direct["cases"]
    require(capture["raw_sha256"] == pilot.file_sha(paths["raw"]) == pilot.file_sha(incl["direct_raw"]) ==
            baseline["raw_output_sha256"] and pilot.read(paths["raw"]) == direct and
            capture["log_sha256"] == pilot.file_sha(paths["run"]), "raw output or log drift")
    require(pilot.START_LINE.findall(log) == [
        (str(c["shot"]), str(c["window"]), c["phase"], str(c["defects"]), str(c["selectors"])) for c in cases
    ] and pilot.SOLVED_LINE.findall(log) == [
        (str(c["shot"]), str(c["window"]), str(c["iterations"]), "true") for c in cases
    ] and pilot.SHOT_LINE.findall(log) == [
        (str(shot["shot"]), "true", shot["expected_final_frame_hex"], shot["expected_final_frame_hex"])
        for shot in frozen["shots"]
    ], "runtime row or closing frame drift")
    _, old_lines = packed.read_lines(old_paths["run"])
    old_marks = [line for line in old_lines if line.startswith(cycle.WINDOW)]
    marks = [(i, line) for i, line in enumerate(lines) if line.startswith(cycle.WINDOW)]
    seed_idx, _ = cycle.unique_mark(lines, f"[Progress] Start D6PhaseAxiEndpoint hosted simulation with seed {record.SEED}")
    probe_idx, probe = cycle.unique_mark(lines, "AXI_PHASE_PROBES_PASS ")
    profile_idx, profile = cycle.unique_mark(lines, cycle.PROFILE)
    exec_idx, executed = cycle.unique_mark(lines, EXEC)
    bus_idx, transport = cycle.unique_mark(lines, pilot.REPORT)
    require(len(marks) == len(old_marks) == len(cases) == baseline["paired_windows"] and probe == pilot.PROBE_LINE and
            seed_idx < probe_idx < marks[0][0] <= marks[-1][0] < profile_idx < exec_idx < bus_idx,
            "candidate windows not correctly enclosed by probes and reports")

    removed = 0
    removed_order = Counter()
    candidates = []
    previous = []
    packed_no_skew = []
    logical_pairs = hashlib.sha256()
    for old, (_, new) in zip(old_marks, marks, strict=True):
        a = cycle.entries(old, cycle.WINDOW, (*cycle.WINDOW_FIELDS, *EXT))
        b = cycle.entries(new, cycle.WINDOW, (*cycle.WINDOW_FIELDS, *EXT, "packed_tx_sha256", "fused_ordinals"))
        key = tuple(cycle.uint(a[k]) for k in ("shot", "window", "phase"))
        require(all(a[k] == b[k] for k in ("shot", "window", "phase", "mode", "queries", "packed_reads",
                                          "split_tx_sha256")) and
                a["mode"] == record.POLICY and a["status"] == "packed" and b["status"] == "fused" and
                a["tx_sha256"] == b["packed_tx_sha256"] and cycle.digest(b["tx_sha256"]),
                f"expanded transaction or window drift: {key}")
        require(cycle.uint(b["b_start"]) == cycle.uint(a["b_start"]) - removed and a["r_start"] == b["r_start"],
                f"unexpected write/read offsets before window: {key}")
        q = cycle.uint(b["queries"])
        ordinals = () if b["fused_ordinals"] == "-" else tuple(map(cycle.uint, b["fused_ordinals"].split(",")))
        before = {group: cycle.tally(a[group]) for group in cycle.GROUPS}
        after = {group: cycle.tally(b[group]) for group in cycle.GROUPS}
        start = cycle.uint(a["b_start"])
        require(q == len(ordinals) == cycle.uint(b["packed_reads"]) and
                tuple(sorted(set(ordinals))) == ordinals and
                all(start <= i < start + before["total"][1] for i in ordinals) and
                (a["tx_sha256"] != b["tx_sha256"]) == bool(q), f"not exactly one removed write per query: {key}")
        measure_window(before, after, ordinals, key)
        removed += q
        removed_order.update(ORDER[n % 3] for n in ordinals)
        logical_pairs.update(f"{key} {b['tx_sha256']} {b['packed_tx_sha256']} {b['fused_ordinals']}\n".encode("ascii"))
        previous.append(before["total"][0])
        packed_no_skew.append(before["total"][0] - before["total"][5])
        candidates.append(after)

    totals = {group: cycle.summed([row[group] for row in candidates]) for group in cycle.GROUPS}
    run = cycle.entries(profile, cycle.PROFILE, ("mode", "read_latency", "windows", "total",
                                               *packed.EXTENSION, "fused_queries"))
    require(run["mode"] == record.POLICY and run["status"] == "fused" and
            cycle.uint(run["read_latency"]) == 1 and cycle.uint(run["windows"]) == len(cases) and
            cycle.tally(run["total"]) == totals["total"] and
            all(cycle.uint(run[name]) == removed for name in ("queries", "packed_reads", "fused_queries")),
            "fused summary did not reconcile to the measured windows")
    accepted, issued, returned, capture_gap = map(cycle.uint, cycle.entries(executed, EXEC, EXEC_FIELDS).values())
    require(accepted == issued == returned == removed == baseline["obstacle_queries"] and capture_gap == 2,
            "RTL edge monitor did not witness one issue and return per accepted query")

    _, old_transport = cycle.unique_mark(old_lines, pilot.REPORT)
    old_bus = {k: cycle.uint(v) for k, v in cycle.entries(old_transport, pilot.REPORT, pilot.FIELDS).items()}
    bus = {k: cycle.uint(v) for k, v in cycle.entries(transport, pilot.REPORT, pilot.FIELDS).items()}
    deselected_skew = removed_order["aw_first"] * 2 + removed_order["w_first"] * 3
    expected_bus = old_bus.copy()
    for name in ("aw", "w", "b"):
        expected_bus[name] -= removed
    for name in ORDER:
        expected_bus[name] -= removed_order[name]
    expected_bus["simulated_bus_cycles"] -= 2 * removed + deselected_skew
    require(bus == expected_bus and bus["obstacle_reads"] == removed, "all-traffic counts differ beyond fused writes")
    candidate = [r["total"][0] for r in candidates]
    fused_no_skew = [r["total"][0] - r["total"][5] for r in candidates]
    require(sum(packed_no_skew) - sum(fused_no_skew) == 2 * removed, "counterfactual must remove only fixed cost")
    return {
        "basis": basis, "shots": baseline["shots"], "paired_windows": len(cases), "queries": removed,
        "observed_execution": {"accepted": accepted, "executed": issued, "returned": returned,
                               "enforced_minimum_capture_gap_cycles": capture_gap},
        "removed_writes_by_order": dict(removed_order), "fixed_cycles_removed": removed * 2,
        "write_skew_cycles_removed": deselected_skew, "cycles_removed": sum(previous) - sum(candidate),
        "packed_window_cycles": cycle.quantiles(previous), "fused_window_cycles": cycle.quantiles(candidate),
        "paired_delta_cycles": cycle.quantiles([a - b for a, b in zip(previous, candidate, strict=True)]),
        "packed_total_cycles": sum(previous), "fused_total_cycles": sum(candidate),
        "no_skew_accounting_not_a_replay": {
            "packed_total": sum(packed_no_skew), "fused_total": sum(fused_no_skew),
            "packed_window_cycles": cycle.quantiles(packed_no_skew),
            "fused_window_cycles": cycle.quantiles(fused_no_skew),
        },
        "fused_stage_totals": {group: dict(zip(cycle.FIELDS, v, strict=True)) for group, v in totals.items()},
        "occupancy_checks": baseline["occupancy_checks"], "raw_sha256": capture["raw_sha256"],
        "candidate_rtl_sha256": capture["generated_endpoint_rtl_sha256"],
        "compiled_model_archive_sha256": capture["compiled_model_archive_sha256"],
        "paired_physical_logical_sha256": logical_pairs.hexdigest(), "capture_sha256": pilot.file_sha(paths["capture"]),
        "packed_log_sha256": old_capture["log_sha256"], "fused_log_sha256": capture["log_sha256"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=record.ROOT / "results")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    smoke = audit_smoke(args.artifact_dir)
    rows = [audit_basis(args.artifact_dir, basis) for basis in pilot.FROZEN]
    payload = {
        "schema": "b2_b7_p023_d6_axi_fused_query_evidence_v1", "scope": pilot.SCOPE,
        "classification": "bounded_opt_in_axi_lite32_fused_obstacle_command_and_status",
        "baseline_evidence_sha256": pilot.file_sha(record.BASELINE),
        "audit_tool_sha256": pilot.file_sha(Path(__file__)), "smoke": smoke,
        "paired_windows": sum(row["paired_windows"] for row in rows),
        "fused_queries": sum(row["queries"] for row in rows),
        "fixed_cycles_removed": sum(row["fixed_cycles_removed"] for row in rows),
        "write_skew_cycles_removed": sum(row["write_skew_cycles_removed"] for row in rows),
        "total_simulated_cycles_removed": sum(row["cycles_removed"] for row in rows),
        "basis_rows": rows, "quantile_method": "nearest rank within basis (ceil(n * percentile / 100))",
        "acceptance": {
            "paired_fused_query_rtl_simulation": True, "held_response_and_partial_write_small_graph": True,
            "exact_once_per_accepted_ar_in_tested_runs": True, "production_software_mmio_integration": False,
            "overlapping_multi_register_result_protocol": False, "full_axi_denominator": False,
            "multi_context_or_cdc": False, "fpga": False, "p99_le_1us": False, "miss_rate_le_1pct": False,
            "full_b2": False, "scalable_p023": False, "b7_resource_credit": 0,
        },
    }
    payload["evidence_id"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    path = args.artifact_dir / f"{record.PREFIX}_evidence_v1.json"
    if args.write:
        pilot.dump_new(path, payload)
    else:
        require(pilot.read(path) == payload, "saved evidence does not replay")
    print(f"{payload['evidence_id']} windows={payload['paired_windows']} queries={payload['fused_queries']} "
          f"cycles_removed={payload['total_simulated_cycles_removed']}")


if __name__ == "__main__":
    main()
