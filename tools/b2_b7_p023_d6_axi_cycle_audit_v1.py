#!/usr/bin/env python3
"""Reconcile the measured AXI cycles with a paired control and the accepted RTL pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import b2_b7_p023_d6_axi_cycle_record_v1 as record
import b2_b7_p023_d6_axi_lite_replay_v1 as pilot

FIELDS = ("cycles", "writes", "reads", "b_stalls", "r_stalls", "aw_w_skew")
STAGES = ("ingress", "solve_cmd", "obstacle_read", "correction_write", "correction_read")
PHASES = ("opening", "steady", "closing")
GROUPS = ("total", *STAGES)
WINDOW = "AXI_CYCLE_WINDOW "
PROFILE = "AXI_CYCLE_PROFILE "
WINDOW_FIELDS = ("mode", "shot", "window", "phase", "b_start", "r_start", "tx_sha256", *GROUPS)
Tally = tuple[int, int, int, int, int, int]
require = pilot.require


def entries(line: str, prefix: str, keys: tuple[str, ...] | list[str]) -> dict[str, str]:
    values = tuple(token.partition("=") for token in line.removeprefix(prefix).split())
    require(tuple(name for name, _, _ in values) == tuple(keys) and
            all(eq and val for _, eq, val in values), f"unexpected fields in {prefix}")
    return {name: val for name, _, val in values}


def uint(value: str) -> int:
    require(bool(re.fullmatch(r"0|[1-9][0-9]*", value)), f"invalid unsigned count {value!r}")
    return int(value)


def digest(value: str | None) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", value or ""))


def tally(value: str) -> Tally:
    cycles, writes, reads, b_stalls, r_stalls, skew = map(uint, value.split(","))
    return (cycles, writes, reads, b_stalls, r_stalls, skew)


def summed(tallies: list[Tally]) -> Tally:
    return tuple(sum(axis) for axis in zip(*tallies, strict=True)) if tallies else (0,) * len(FIELDS)


def unique_mark(lines: list[str], prefix: str) -> tuple[int, str]:
    hits = [(i, line) for i, line in enumerate(lines) if line.startswith(prefix)]
    require(len(hits) == 1, f"missing or duplicate {prefix}")
    return hits[0]


def read_run(folder: Path, basis: str, policy: str, prior: dict, direct: dict) -> dict:
    paths = record.paths(folder, basis, policy)
    captured = pilot.read(paths["capture"])
    log = paths["run"].read_text(encoding="utf-8")
    cases = direct["cases"]
    frozen = pilot.read(pilot.inputs(basis)["pilot"])
    count = len(cases)
    require(captured["schema"] == "b2_b7_p023_d6_axi_cycle_profile_capture_v1" and
            captured["scope"] == pilot.SCOPE and captured["basis"] == basis and captured["policy"] == policy,
            "capture is out of scope or not the named policy")
    require(captured["source_commit"] == pilot.SOURCE_COMMIT and
            captured["source_archive_sha256"] == pilot.ARCHIVE_SHA and
            captured["sources_sha256"] == record.sources(basis), "source manifest changed")
    require(captured["started_utc"] < captured["finished_utc"] and captured["exit_code"] == 0 and
            not pilot.BAD_RUNTIME.search(log), "runtime did not pass")
    require(captured["simulator_seed"] == record.SEED and
            captured["simulator_version"].startswith("Verilator 5.040 2025-08-30") and
            digest(captured["simulator_binary_sha256"]) and digest(captured["compiled_model_archive_sha256"]),
            "missing execution environment binding")
    require(captured["generated_endpoint_rtl_sha256"] == prior["generated_endpoint_rtl_sha256"],
            "changed RTL relative to accepted endpoint")
    require(captured["log_sha256"] == pilot.file_sha(paths["run"]) and
            captured["raw_sha256"] == pilot.file_sha(paths["raw"]) == prior["direct_raw_sha256"] and
            pilot.read(paths["raw"]) == direct, "unbound log or changed direct RTL output")

    starts = list(pilot.START_LINE.finditer(log))
    solves = list(pilot.SOLVED_LINE.finditer(log))
    closes = list(pilot.SHOT_LINE.finditer(log))
    require([m.groups() for m in starts] == [
        tuple(str(row[key]) for key in ("shot", "window", "phase", "defects", "selectors")) for row in cases
    ] and [m.groups() for m in solves] == [
        (str(row["shot"]), str(row["window"]), str(row["iterations"]), "true") for row in cases
    ], "runtime starts/solves do not match accepted rows")
    require([m.groups() for m in closes] == [
        (str(shot["shot"]), "true", shot["expected_final_frame_hex"], shot["expected_final_frame_hex"])
        for shot in frozen["shots"]
    ], "runtime closing states do not match frozen frames")

    lines = [line.removeprefix("[info] ") for line in log.splitlines()]
    seed_pos, _ = unique_mark(lines, f"[Progress] Start D6PhaseAxiEndpoint hosted simulation with seed {record.SEED}")
    probe_pos, probe = unique_mark(lines, "AXI_PHASE_PROBES_PASS ")
    profile_pos, profile_line = unique_mark(lines, PROFILE)
    report_pos, report_line = unique_mark(lines, pilot.REPORT)
    profile = entries(profile_line, PROFILE, ("mode", "read_latency", "windows", "total"))
    latency = uint(profile["read_latency"])
    require(profile["mode"] == policy and latency == 1 and uint(profile["windows"]) == count,
            "wrong timing profile, read latency or window count")
    marks = [(i, line) for i, line in enumerate(lines) if line.startswith(WINDOW)]
    require(len(marks) == count and probe == pilot.PROBE_LINE and
            seed_pos < probe_pos < marks[0][0] <= marks[-1][0] < profile_pos < report_pos,
            "missing/duplicate measurements, or probe and profile out of order")
    # Scala logging is relayed asynchronously; it can arrive after Rust's
    # solved line. Bind the two ordered streams by exact keys, not adjacency.
    require(all(starts[i].start() < solves[i].start() <
                (starts[i + 1].start() if i + 1 < count else closes[-1].start())
                for i in range(count)), "Rust solve intervals are out of order")
    words = {phase["name"]: (phase["fault_id_count"] + 31) // 32 for phase in frozen["phases"]}
    rows = []
    offsets = None
    warmup = None
    for case, (_, line) in zip(cases, marks, strict=True):
        raw = entries(line, WINDOW, WINDOW_FIELDS)
        key = tuple(uint(raw[k]) for k in ("shot", "window", "phase"))
        require(raw["mode"] == policy and key == (case["shot"], case["window"], PHASES.index(case["phase"])) and
                digest(raw["tx_sha256"]), f"wrong window key, mode or transaction digest: {key}")
        bw, ar = (uint(raw[k]) for k in ("b_start", "r_start"))
        if offsets is None:
            warmup = (bw, ar)
        else:
            require((bw, ar) == offsets, f"gap in accepted transaction offsets: {key}")
        counts = {group: tally(raw[group]) for group in GROUPS}
        require(summed([counts[stage] for stage in STAGES]) == counts["total"], f"unattributed tally: {key}")
        for group, (cycles, writes, reads, bs, rs, skew) in counts.items():
            require(cycles == (3 + latency) * writes + 2 * reads + bs + rs + skew,
                    f"unexpected cycle accounting: {key}/{group}")
            if group != "total":
                require((writes == bs == skew == 0) if group.endswith("read") else (reads == rs == 0),
                        f"mixed read/write stage: {key}/{group}")
        _, writes, reads, bs, rs, skew = counts["total"]
        offsets = (bw + writes, ar + reads)
        expected_skew = sum((0, 2, 3)[n % 3] for n in range(bw, bw + writes))
        expected_stalls = (sum(1 + n % 4 for n in range(bw, bw + writes)),
                           sum(1 + (n + 1) % 5 for n in range(ar, ar + reads)))
        require(skew == expected_skew and (bs, rs) == (expected_stalls if policy == "legacy_hold" else (0, 0)),
                f"response-stall or AW/W skew mismatch: {key}")
        require(counts["ingress"][1] == 2 + case["defects"] + case["selectors"],
                f"reset/phase/defect/selector command count mismatch: {key}")
        require(counts["correction_write"][1] == 2 + len(case["actual_subgraph_superset_edges"]) and
                counts["correction_read"][2] == 3 + words[case["phase"]],
                f"correction clear/edge/latch or generation/meta/word count mismatch: {key}")
        rows.append({"key": key, "offsets": (bw, ar), "tx_sha256": raw["tx_sha256"], "counts": counts})

    bus = {field: uint(value) for field, value in entries(report_line, pilot.REPORT, pilot.FIELDS).items()}
    totals = {group: summed([row["counts"][group] for row in rows]) for group in GROUPS}
    require(tally(profile["total"]) == totals["total"] and offsets == (bus["b"], bus["r"]) and
            bus["aw"] == bus["w"] == bus["b"] and bus["ar"] == bus["r"],
            "window sums do not reconcile to the overall timing profile and completed transactions")
    # Each FindObstacle reads two status registers and three more on a conflict.
    query_calls = bus["obstacle_reads"]
    extra_register_reads = totals["obstacle_read"][2] - 2 * query_calls
    require(0 <= extra_register_reads <= 3 * query_calls and extra_register_reads % 3 == 0,
            "obstacle register coverage does not reconcile")
    return {"rows": rows, "totals": totals, "warmup_transactions": warmup, "bus": bus,
            "capture_sha256": pilot.file_sha(paths["capture"]), "capture": captured}


def quantiles(values: list[int]) -> dict[str, int]:
    ordered = sorted(values)
    return {"n": len(values), "min": ordered[0], "max": ordered[-1], **{
        f"p{pct}": ordered[(pct * len(values) + 99) // 100 - 1] for pct in (50, 95, 99)
    }}


def compare_basis(folder: Path, basis: str) -> dict:
    prior = record.prior_basis(basis)
    require(pilot.audit_basis(pilot.ROOT / "results", basis) == prior, "accepted pilot no longer verifies")
    direct = pilot.read(pilot.inputs(basis)["direct_raw"])
    legacy, ready = (read_run(folder, basis, policy, prior, direct) for policy in record.POLICIES)
    for attr in ("source_commit", "simulator_version", "simulator_binary_sha256", "simulator_seed",
                 "generated_endpoint_rtl_sha256", "compiled_model_archive_sha256", "raw_sha256"):
        require(legacy["capture"][attr] == ready["capture"][attr], f"pair drifted: {basis}/{attr}")
    require(legacy["bus"] == prior["bus"], "legacy timing run did not reproduce the prior pilot totals")
    stalled = legacy["totals"]["total"]
    control_bus = legacy["bus"].copy()
    control_bus["b_stalls"] -= stalled[3]
    control_bus["r_stalls"] -= stalled[4]
    control_bus["simulated_bus_cycles"] -= stalled[3] + stalled[4]
    require(legacy["warmup_transactions"] == ready["warmup_transactions"] and ready["bus"] == control_bus,
            "control changed something other than measured READY holds")
    delta = []
    tx_sequence = hashlib.sha256()
    for a, b in zip(legacy["rows"], ready["rows"], strict=True):
        for field in ("key", "offsets", "tx_sha256"):
            require(a[field] == b[field], f"different transaction sequence: {basis}/{a['key']}/{field}")
        tx_sequence.update(f"{','.join(map(str, a['key']))} {a['tx_sha256']}\n".encode("ascii"))
        for group in GROUPS:
            ac, aw, ar, bs, rs, askew = a["counts"][group]
            require((ac - bs - rs, aw, ar, 0, 0, askew) == b["counts"][group],
                    f"paired difference not explained by response holds: {basis}/{a['key']}/{group}")
        delta.append(a["counts"]["total"][0] - b["counts"]["total"][0])

    policies = {}
    for mode, run in zip(record.POLICIES, (legacy, ready), strict=True):
        phases = {}
        for pi, phase in enumerate(PHASES):
            values = [row["counts"]["total"][0] for row in run["rows"] if row["key"][2] == pi]
            phases[phase] = {"n": len(values), "p50": quantiles(values)["p50"], "max": max(values)}
        policies[mode] = {
            "capture_sha256": run["capture_sha256"],
            "log_sha256": run["capture"]["log_sha256"],
            "stages": {group: dict(zip(FIELDS, values, strict=True)) for group, values in run["totals"].items()},
            "window_cycles": quantiles([row["counts"]["total"][0] for row in run["rows"]]),
            "phase_window_cycles": phases,
            "bus_with_probes": run["bus"],
        }
    # Attribute actual high-cycle windows rather than adding unrelated stage p99s.
    threshold = policies["ready_high"]["window_cycles"]["p99"]
    tail = [row for row in ready["rows"] if row["counts"]["total"][0] >= threshold]
    tail_cycles = {group: sum(row["counts"][group][0] for row in tail) for group in GROUPS}
    return {
        "basis": basis, "shots": prior["shots"], "matched_windows": prior["matched_windows"],
        "occupancy_checks_per_replay": prior["occupancy_checks"],
        "phase_window_counts": dict(Counter(case["phase"] for case in direct["cases"])),
        "closed_loop_summary_per_replay": direct["summary"],
        "paired_window_cycle_delta": quantiles(delta),
        "paired_transaction_sequence_sha256": tx_sequence.hexdigest(),
        "ready_high_tail": {
            "threshold_cycles": threshold, "windows_at_or_above_threshold": len(tail),
            "phase_window_counts": dict(Counter(PHASES[row["key"][2]] for row in tail)),
            "stage_cycle_sums": tail_cycles,
        },
        "generated_endpoint_rtl_sha256": legacy["capture"]["generated_endpoint_rtl_sha256"],
        "compiled_model_archive_sha256": legacy["capture"]["compiled_model_archive_sha256"],
        "direct_and_paired_raw_sha256": legacy["capture"]["raw_sha256"],
        "simulator_binary_sha256": legacy["capture"]["simulator_binary_sha256"],
        "warmup_completed_writes_reads": list(legacy["warmup_transactions"]),
        "policies": policies,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=pilot.ROOT / "results")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    rows = [compare_basis(args.artifact_dir, basis) for basis in pilot.FROZEN]
    payload = {
        "schema": "b2_b7_p023_d6_axi_cycle_profile_evidence_v1",
        "scope": pilot.SCOPE,
        "classification": "bounded_paired_axi_lite32_rtl_simulation_cycle_attribution",
        "source_commit": pilot.SOURCE_COMMIT,
        "prior_evidence_sha256": pilot.file_sha(record.PILOT_EVIDENCE),
        "simulator_seed": record.SEED,
        "audit_tool_sha256": pilot.file_sha(Path(__file__)),
        "quantile_method": "nearest rank: ceil(n * percentile / 100), 1-indexed, within basis",
        "paired_windows": sum(row["matched_windows"] for row in rows),
        "basis_rows": rows,
        "acceptance": {
            "paired_cycle_attribution": True, "full_axi_denominator": False, "multi_context_or_cdc": False,
            "fpga": False, "p99_le_1us": False, "miss_rate_le_1pct": False, "full_b2": False,
            "scalable_p023": False, "b7_resource_credit": 0,
        },
    }
    payload["evidence_id"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    destination = args.artifact_dir / f"{record.PREFIX}_evidence_v1.json"
    if args.write:
        pilot.dump_new(destination, payload)
    else:
        require(pilot.read(destination) == payload, "saved evidence does not replay")
    print(f"{payload['evidence_id']} paired_windows={payload['paired_windows']}")


if __name__ == "__main__":
    main()
