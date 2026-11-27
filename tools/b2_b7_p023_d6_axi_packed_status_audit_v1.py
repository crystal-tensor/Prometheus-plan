#!/usr/bin/env python3
"""Check that a packed obstacle read replaces exactly its two split reads."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import b2_b7_p023_d6_axi_cycle_audit_v1 as cycle
import b2_b7_p023_d6_axi_lite_replay_v1 as pilot
import b2_b7_p023_d6_axi_packed_status_record_v1 as record

require = pilot.require
SMOKE = re.compile(r"^AXI_STATUS_SMOKE_RESULT status=(split|packed) result=(.+)$", re.M)
PROBE = re.compile(r"AXI_PACKED_STATUS_PROBE_PASS old=0x([0-9a-f]{8}) new=0x([0-9a-f]{8}) held_across_find_obstacle=1")
EXTENSION = ("status", "queries", "packed_reads")
CONFLICT_FLAG = 1 << 31


def read_lines(path: Path) -> tuple[str, list[str]]:
    log = path.read_text(encoding="utf-8")
    return log, [line.removeprefix("[info] ") for line in log.splitlines()]


def audit_smoke(folder: Path) -> dict:
    paths = record.smoke_paths(folder)
    receipt = pilot.read(paths["capture"])
    require(receipt["schema"] == "b2_b7_p023_d6_axi_packed_status_smoke_capture_v1" and
            receipt["scope"] == pilot.SCOPE and receipt["source_commit"] == pilot.SOURCE_COMMIT and
            receipt["source_archive_sha256"] == pilot.ARCHIVE_SHA and
            receipt["sources_sha256"] == record.sources(None), "smoke source not bound")
    require(receipt["simulator_seed"] == record.SEED and receipt["simulator_version"].startswith("Icarus Verilog") and
            receipt["positive_exit_code"] == 0 and receipt["negative_exit_code"] != 0 and
            receipt["started_utc"] < receipt["finished_utc"], "unexpected smoke simulator/outcome")
    for key in ("positive", "negative"):
        require(pilot.file_sha(paths[key]) == receipt[f"{key}_log_sha256"], f"unbound {key} smoke log")
    pos, lines = read_lines(paths["positive"])
    neg, neg_lines = read_lines(paths["negative"])
    results = SMOKE.findall("\n".join(lines))
    negative_results = SMOKE.findall("\n".join(neg_lines))
    require(len(results) == 2 and [mode for mode, _ in results] == ["split", "packed"] and
            results[0][1] == results[1][1] and negative_results == [results[1]] and
            lines.count(pilot.PROBE_LINE) == 2, "fixtures disagree or never reached the fault")
    probe = [match.groups() for line in lines if (match := PROBE.fullmatch(line))]
    require(len(probe) == 1 and not pilot.BAD_RUNTIME.search(pos), "positive probe did not pass")
    before, after = (int(word, 16) for word in probe[0])
    require(before & CONFLICT_FLAG != 0 and after == (1 << 26) - 1 and before != after,
            "probe did not exercise a distinct conflict and length sentinel")
    require(record.BAD_R in neg and "AXI_PACKED_STATUS_PROBE_PASS" not in neg,
            "negative control did not fail the held-R invariant")
    return {"capture_sha256": pilot.file_sha(paths["capture"]), "matching_smoke_result": results[0][1],
            "held_conflict_word": f"0x{before:08x}", "next_query_word": f"0x{after:08x}",
            "unlatched_mutation_rejected": True}


def audit_basis(folder: Path, basis: str) -> dict:
    reference = record.cycle.prior_basis(basis)
    archived = record.ROOT / "results"
    expected_evidence = next(row for row in pilot.read(record.BASELINE_EVIDENCE)["basis_rows"] if row["basis"] == basis)
    require(cycle.compare_basis(archived, basis) == expected_evidence, "previous paired evidence no longer verifies")
    incl = pilot.inputs(basis)
    direct = pilot.read(incl["direct_raw"])
    frozen = pilot.read(incl["pilot"])
    baseline = cycle.read_run(archived, basis, record.POLICY, reference, direct)
    paths = record.paths(folder, basis, "packed")
    capture = pilot.read(paths["capture"])
    log, lines = read_lines(paths["run"])
    require(capture["schema"] == "b2_b7_p023_d6_axi_packed_status_capture_v1" and
            capture["scope"] == pilot.SCOPE and capture["basis"] == basis and
            capture["obstacle_status"] == "packed" and capture["timing_policy"] == record.POLICY and
            capture["source_commit"] == pilot.SOURCE_COMMIT and capture["source_archive_sha256"] == pilot.ARCHIVE_SHA and
            capture["sources_sha256"] == record.sources(basis), "candidate manifest not bound")
    require(capture["started_utc"] < capture["finished_utc"] and capture["exit_code"] == 0 and
            not pilot.BAD_RUNTIME.search(log), "candidate replay did not pass")
    require(capture["raw_sha256"] == pilot.file_sha(paths["raw"]) == reference["direct_raw_sha256"] and
            pilot.read(paths["raw"]) == direct and capture["log_sha256"] == pilot.file_sha(paths["run"]),
            "raw output drift or unbound candidate log")
    for name in ("simulator_version", "simulator_binary_sha256", "simulator_seed"):
        require(capture[name] == baseline["capture"][name], f"candidate changed the simulator: {name}")
    for name in ("generated_endpoint_rtl_sha256", "compiled_model_archive_sha256"):
        require(cycle.digest(capture[name]) and capture[name] != baseline["capture"][name],
                f"not a separately compiled candidate: {name}")

    cases = direct["cases"]
    require(pilot.START_LINE.findall(log) == [
        (str(case["shot"]), str(case["window"]), case["phase"], str(case["defects"]), str(case["selectors"]))
        for case in cases
    ] and pilot.SOLVED_LINE.findall(log) == [
        (str(case["shot"]), str(case["window"]), str(case["iterations"]), "true") for case in cases
    ], "runtime keys or solve outcomes changed")
    require(pilot.SHOT_LINE.findall(log) == [
        (str(shot["shot"]), "true", shot["expected_final_frame_hex"], shot["expected_final_frame_hex"])
        for shot in frozen["shots"]
    ], "runtime ending frames changed")

    seed_idx, _ = cycle.unique_mark(lines, f"[Progress] Start D6PhaseAxiEndpoint hosted simulation with seed {record.SEED}")
    probe_idx, probe = cycle.unique_mark(lines, "AXI_PHASE_PROBES_PASS ")
    profile_idx, summary = cycle.unique_mark(lines, cycle.PROFILE)
    report_idx, transport = cycle.unique_mark(lines, pilot.REPORT)
    marks = [(idx, line) for idx, line in enumerate(lines) if line.startswith(cycle.WINDOW)]
    require(len(marks) == len(cases) and probe == pilot.PROBE_LINE and
            seed_idx < probe_idx < marks[0][0] <= marks[-1][0] < profile_idx < report_idx,
            "candidate windows missing or incorrectly bounded by probe and report")
    count = cycle.uint
    measure = cycle.tally
    saved = 0
    candidate_rows = []
    traffic = hashlib.sha256()
    for base, (_, line) in zip(baseline["rows"], marks, strict=True):
        raw = cycle.entries(line, cycle.WINDOW, (*cycle.WINDOW_FIELDS, *EXTENSION, "split_tx_sha256"))
        key = tuple(count(raw[name]) for name in ("shot", "window", "phase"))
        require(key == base["key"] and raw["status"] == "packed" and raw["mode"] == record.POLICY,
                f"candidate window key or mode drift: {basis}/{key}")
        writes_before, reads_before = base["offsets"]
        require((count(raw["b_start"]), count(raw["r_start"])) == (writes_before, reads_before - saved),
                f"only removed reads may shift later offsets: {basis}/{key}")
        require(raw["split_tx_sha256"] == base["tx_sha256"] and cycle.digest(raw["tx_sha256"]),
                f"expanded ordered transaction sequence changed: {basis}/{key}")
        queries = count(raw["queries"])
        require(count(raw["packed_reads"]) == queries and (raw["tx_sha256"] != base["tx_sha256"]) == bool(queries),
                f"expected exactly one physical packed read per query: {basis}/{key}")
        counts = {group: measure(raw[group]) for group in cycle.GROUPS}
        extra_reads = counts["obstacle_read"][2] - queries
        require(0 <= extra_reads <= 3 * queries and extra_reads % 3 == 0,
                f"expected three extra register reads per signalled conflict: {basis}/{key}")
        for group in cycle.GROUPS:
            budget = queries if group in ("total", "obstacle_read") else 0
            clk, wr, rd, bhold, rhold, skew = base["counts"][group]
            require((clk - 2 * budget, wr, rd - budget, bhold, rhold, skew) == counts[group],
                    f"cycles or traffic changed outside removed reads: {basis}/{key}/{group}")
        traffic.update(f"{','.join(map(str, key))} {raw['tx_sha256']} {raw['split_tx_sha256']}\n".encode("ascii"))
        candidate_rows.append(counts)
        saved += queries

    totals = {group: cycle.summed([row[group] for row in candidate_rows]) for group in cycle.GROUPS}
    run = cycle.entries(summary, cycle.PROFILE, ("mode", "read_latency", "windows", "total", *EXTENSION))
    require(run["mode"] == record.POLICY and run["status"] == "packed" and count(run["read_latency"]) == 1 and
            count(run["windows"]) == len(cases) and measure(run["total"]) == totals["total"] and
            count(run["queries"]) == count(run["packed_reads"]) == saved and saved > 0,
            "candidate profile does not reconcile to measured windows")
    bus = {field: count(value) for field, value in cycle.entries(transport, pilot.REPORT, pilot.FIELDS).items()}
    expected_bus = baseline["bus"].copy()
    expected_bus["r"] -= saved
    expected_bus["ar"] -= saved
    expected_bus["simulated_bus_cycles"] -= 2 * saved
    require(bus == expected_bus and bus["obstacle_reads"] == saved,
            "candidate summary changed something beyond one fewer read per FindObstacle")
    old = [row["counts"]["total"][0] for row in baseline["rows"]]
    new = [row["total"][0] for row in candidate_rows]
    return {
        "basis": basis, "shots": reference["shots"], "paired_windows": len(cases),
        "obstacle_queries": saved, "reads_removed": saved, "cycles_removed": 2 * saved,
        "split_window_cycles": cycle.quantiles(old), "packed_window_cycles": cycle.quantiles(new),
        "paired_delta_cycles": cycle.quantiles([a - b for a, b in zip(old, new, strict=True)]),
        "split_stages": {group: dict(zip(cycle.FIELDS, v, strict=True)) for group, v in baseline["totals"].items()},
        "packed_stages": {group: dict(zip(cycle.FIELDS, v, strict=True)) for group, v in totals.items()},
        "ordered_physical_and_expanded_sha256": traffic.hexdigest(),
        "generated_endpoint_rtl_sha256": capture["generated_endpoint_rtl_sha256"],
        "compiled_model_archive_sha256": capture["compiled_model_archive_sha256"],
        "raw_output_sha256": capture["raw_sha256"], "capture_sha256": pilot.file_sha(paths["capture"]),
        "baseline_ready_log_sha256": baseline["capture"]["log_sha256"],
        "packed_log_sha256": capture["log_sha256"], "occupancy_checks": reference["occupancy_checks"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=record.ROOT / "results")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    smoke = audit_smoke(args.artifact_dir)
    rows = [audit_basis(args.artifact_dir, basis) for basis in pilot.FROZEN]
    payload = {
        "schema": "b2_b7_p023_d6_axi_packed_status_evidence_v1", "scope": pilot.SCOPE,
        "classification": "bounded_serialized_axi_lite32_packed_obstacle_status",
        "paired_windows": sum(row["paired_windows"] for row in rows),
        "read_transactions_removed": sum(row["reads_removed"] for row in rows),
        "simulated_bus_cycles_removed": sum(row["cycles_removed"] for row in rows),
        "baseline_evidence_sha256": pilot.file_sha(record.BASELINE_EVIDENCE),
        "audit_tool_sha256": pilot.file_sha(Path(__file__)),
        "quantile_method": "nearest rank within basis (ceil(n * percentile / 100))",
        "basis_rows": rows, "smoke": smoke,
        "acceptance": {
            "paired_packed_status_rtl_simulation": True, "held_packed_r_beat_small_graph": True,
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
    print(f"{payload['evidence_id']} windows={payload['paired_windows']} "
          f"reads_removed={payload['read_transactions_removed']} "
          f"cycles_removed={payload['simulated_bus_cycles_removed']}")


if __name__ == "__main__":
    main()
