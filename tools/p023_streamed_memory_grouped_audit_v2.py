#!/usr/bin/env python3
"""Audit grouped qualification receipts against the unchanged #023 gate."""

import argparse
import json
import math
from pathlib import Path

import p023_streamed_memory_audit_v1 as old
import p023_streamed_memory_grouped_v2 as run


def audit(directory: Path, freeze: str, salt: str, git: str):
    old.check(len(bytes.fromhex(salt)) == 32, "invalid public salt")
    p, local, admission, kernel = run.config(freeze, git)
    d = local["distance"]
    q = p["qualification"]
    shots = q["shots_per_shard"]
    n_full = q["shards"] * shots
    old.check(n_full == q["prespecified_total_shots"], "wrong shot plan")
    limit = q["failure_target"]
    cap = math.floor(n_full * limit - old.Z * math.sqrt(n_full * limit * (1 - limit)))
    old.check(old.wilson_upper(cap, n_full) <= limit < old.wilson_upper(cap+1, n_full),
              "wrong score-test cutoff")
    available = {f.name for f in directory.glob("P023_grouped_*_shard*.json")}
    seen, used = set(), set()
    rows = []
    for r in q["horizons"]:
        for b in q["bases"]:
            for arm in q["arms"]:
                mid, windows, width = old.source_models(p, d, b, r, arm)
                totals = {"failures": 0, "shots": 0, "sample_ns": 0, "decode_ns": 0}
                shards = []
                window_ns = []
                missing = []
                for i in range(q["shards"]):
                    name = run.filename(b, arm, r, i)
                    if name not in available:
                        missing.append(i)
                        continue
                    path = directory / name
                    value = old.load(path)
                    x, t = value["receipt"], value["timings"]
                    old.check((x["schema"], x["freeze"], x["salt"], x["distance"], x["basis"],
                               x["arm"], x["rounds"], x["shard"]) ==
                              (run.SCHEMA, freeze, salt, d, b, arm, r, i), f"wrong cell {name}")
                    old.check(x["kernel_sha256"] == kernel and x["admission"] == admission,
                              f"unknown sampler {name}")
                    old.check(all(x[key] == v for key, v in mid.items()), f"wrong models {name}")
                    seed = old.seed(("grouped-qualification-v2", freeze, salt, d, b, arm, r, i))
                    old.check(seed == x["seed"] and seed not in seen, f"invalid seed {name}")
                    seen.add(seed)
                    old.check((x["shots"], x["windows"], x["max_graph_detectors"],
                               x["active_qubits"]) == (shots, windows, width, 2*d*d-1),
                              f"wrong execution shape {name}")
                    old.check(0 < x["physical_nonzero_cut_batches"] < windows and
                              0 < x["correction_nonzero_cut_batches"] < windows,
                              f"trajectory did not exercise carries {name}")
                    old.check(0 < t["batch_window_p99_ns"] <= t["max_window_ns"] <= t["decode_ns"]
                              and t["sample_ns"] > 0, f"bad timing {name}")
                    totals["failures"] += old.tally(x, shots)
                    totals["shots"] += shots
                    for k in ("sample_ns", "decode_ns"):
                        totals[k] += t[k]
                    window_ns.append(t["batch_window_p99_ns"])
                    used.add(name)
                    shards.append({"file": name, "sha256": old.digest(path)})
                is_full = not missing
                ok = is_full and totals["failures"] <= cap
                state = ("pass" if ok else "futility" if totals["failures"] > cap else
                         "partial_no_credit" if shards else "not_yet_measured")
                exposure = r * totals["shots"]
                entry = {"distance": d, "basis": b, "arm": arm, "rounds": r,
                         "rows": shards, "missing_shards": missing, "status": state,
                         "complete": is_full, "qualified": ok, **totals,
                         "shot_rounds": exposure,
                         "wilson_95_upper": old.wilson_upper(totals["failures"], totals["shots"])
                         if is_full else None}
                if shards:
                    entry["host_decoder_rounds_per_second"] = exposure * 1e9 / totals["decode_ns"]
                    entry["min_shard_p99_batch_window_ns"] = min(window_ns)
                    entry["max_shard_p99_batch_window_ns"] = max(window_ns)
                rows.append(entry)
    old.check(used == available, "unrecognized shard file")
    return {"schema": "p023_grouped_qualification_audit_v2", "freeze": freeze, "salt": salt,
            "qual_protocol_sha256": old.digest(run.PATH), "kernel_sha256": kernel,
            "audit_source_sha256": old.digest(Path(__file__)), "admission": admission,
            "rows": rows, "expected_shots_per_cell": n_full, "maximum_failures": cap,
            "complete_cells": sum(row["complete"] for row in rows),
            "qualifies_both_horizons_bases_arms": all(row["qualified"] for row in rows),
            "no_cross_version_pooling": True,
            "claim_boundary": {"hardware": False, "full_b2": False, "b7_resource_credit": 0}}


def audit_timings(directory: Path, freeze: str, salt: str, git: str):
    p, local, admission, kernel = run.config(freeze, git)
    d, r, arm = local["distance"], 1_000_000, "nominal"
    compared = []
    baseline_freezes = set()
    for b in p["qualification"]["bases"]:
        files = {"baseline": directory / f"P023_stream_timing_d15_{b}_nominal_r1000000.json",
                 "grouped": directory / f"P023_grouped_timing_d15_{b}.json"}
        model, windows, width = old.source_models(p, d, b, r, arm)
        values = {}
        seeds = set()
        for key, path in files.items():
            entry = old.load(path)
            old.check(not entry["counts_toward_acceptance"]
                      and (entry["distance"], entry["basis"], entry["arm"], entry["rounds"]) ==
                      (d, b, arm, r), "wrong timing cell")
            old.check(all(entry[k] == v for k, v in model.items()), "different timing model")
            if key == "grouped":
                old.check(entry["schema"] == "p023_grouped_timing_v1" and
                          (entry["freeze"], entry["salt"], entry["kernel_sha256"], entry["admission"]) ==
                          (freeze, salt, kernel, admission), "wrong grouped timing source")
                seed = old.seed(("timing-only-grouped", freeze, salt, d, b, r))
            else:
                old.check(entry["schema"] == "p023_streamed_timing_v1", "wrong v1 timing source")
                baseline_freezes.add((entry["freeze"], entry["salt"]))
                seed = old.seed(("unbatched-timing-only", entry["freeze"], entry["salt"], d, b, arm, r))
            s, t = entry["receipt"], entry["timings"]
            old.check((s["seed"], s["shots"], s["windows"], s["max_graph_detectors"]) ==
                      (seed, 1, windows, width) and seed not in seeds, "wrong timing shape or seed")
            seeds.add(seed)
            old.tally(s, 1)
            old.check(0 < t["batch_window_p99_ns"] <= t["max_window_ns"] <= t["decode_ns"]
                      and t["sample_ns"] > 0, "wrong timing record")
            values[key] = {"raw_file": path.name, "raw_sha256": old.digest(path),
                           "sampler_seconds": t["sample_ns"]/1e9,
                           "decode_stitch_seconds": t["decode_ns"]/1e9,
                           "p99_window_compute_ms": t["batch_window_p99_ns"]/1e6,
                           "sampler_plus_decode_seconds": (t["sample_ns"] + t["decode_ns"])/1e9}
        compared.append({"basis": b, "rounds": r, "windows": windows, "values": values})
    old.check(len(baseline_freezes) == 1, "inconsistent original timing runs")
    (baseline_freeze, baseline_salt), = baseline_freezes
    old.check(len(bytes.fromhex(baseline_salt)) == 32 and baseline_salt != salt,
              "baseline timing salt")
    run.v1.check_freeze(baseline_freeze, git)
    return {"included_in_qualification": False, "same_circuit_and_models": True,
            "notes": "Separate single trajectories and host loads; not an isolated batch or hardware benchmark.",
            "rows": compared}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--salt", required=True)
    parser.add_argument("--git", default="git")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--timing-dir", type=Path)
    a = parser.parse_args()
    r = audit(a.artifact_dir, a.freeze, a.salt, a.git)
    if a.timing_dir:
        r["unbatched_timing_only"] = audit_timings(a.timing_dir, a.freeze, a.salt, a.git)
    if a.out:
        with a.out.open("x") as f:
            json.dump(r, f, indent=2, sort_keys=True)
            f.write("\n")
    for x in r["rows"]:
        print(f"{x['basis'].upper()} {x['arm']:15} {x['rounds']:7}: "
              f"{x['failures']}/{x['shots']} {x['status']}")
    print(f"complete cells {r['complete_cells']}, gate passed "
          f"{r['qualifies_both_horizons_bases_arms']}")


if __name__ == "__main__":
    main()
