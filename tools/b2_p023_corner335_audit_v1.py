#!/usr/bin/env python3
"""Recount the independent 335-qubit shot receipts against the fixed d15 denominator."""

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path

import b2_p023_corner335_gate_v1 as candidate
import b2_p023_corner335_stream_v1 as corner
import b2_p023_d12_stream_v1 as even
import p023_streamed_memory_audit_v1 as plain
import p023_streamed_memory_grouped_audit_v2 as reference


def build(directory, freeze, salt, git):
    spec, base, pinned, _, kernel = candidate.config(git)
    r = reference.audit(candidate.v1.ROOT / spec["reference_directory"],
                        spec["reference_freeze"], pinned["salt"], git)
    check = plain.check
    check(r["qualifies_both_horizons_bases_arms"] and r["rows"] == pinned["rows"],
          "reference does not reconstruct from its raw files")
    q = base["qualification"]
    controls = candidate.freeze_check(spec, q, freeze, git)
    total = q["prespecified_total_shots"]
    target = q["failure_target"]
    cap = math.floor(total*target - plain.Z*math.sqrt(total*target*(1-target)))
    check(plain.wilson_upper(cap, total) <= target < plain.wilson_upper(cap+1, total)
          and cap == pinned["maximum_failures"] and len(bytes.fromhex(salt)) == 32
          and salt != pinned["salt"], "shared or changed acceptance gate")
    names = {x.name for x in directory.glob("B2_corner335_*_shard*.json")}
    used, seeds = set(), set()
    rows = []
    for rounds in q["horizons"]:
        for b in q["bases"]:
            for arm in q["arms"]:
                c, n, m, geom, hashes = corner.model(b, arm, rounds, base)
                parts = even.partition(m, spec["commit_periods"])
                guard = spec["guard_periods"]*n.step
                width = max(a.core + (min(x.core, guard) if x else 0)
                            for a, x in zip(parts, parts[1:] + [None], strict=True))
                shots = bad = decode = sampler = 0
                p99, sources = [], []
                for i in range(q["shards"]):
                    leaf = candidate.filename(b, arm, rounds, i)
                    if leaf not in names:
                        continue
                    path = directory / leaf
                    x = plain.load(path)
                    row, timing = x["receipt"], x["timing"]
                    check((row["schema"], row["freeze"], row["salt"], row["basis"], row["arm"],
                           row["rounds"], row["shard"], row["shots"]) ==
                          (candidate.SCHEMA, freeze, salt, b, arm, rounds, i, q["shots_per_shard"]),
                          "wrong fixed comparison cell")
                    key = plain.seed(("B2-corner335-v1", freeze, salt, b, arm, rounds, i))
                    check(row["seed"] == key and key not in seeds, "repeated seed")
                    seeds.add(key)
                    check(all(row[k] == v for k, v in hashes.items()) and row["geometry"] == geom
                          and row["kernel_sha256"] == kernel and row["controls"] == controls
                          and row["reference_checkpoint_sha256"] == spec["reference_checkpoint_sha256"],
                          "wrong circuit, kernel or provenance")
                    check(row["num_detectors"] == c.num_detectors and row["windows"] == len(parts)
                          and row["max_graph_detectors"] == width and
                          all(0 < row[k] < len(parts) for k in ("physical_nonzero_cut_batches",
                                                               "correction_nonzero_cut_batches")),
                          "incomplete continuous trajectory")
                    check(0 < timing["batch_window_p99_ns"] <= timing["decode_ns"]
                          and timing["sample_ns"] > 0, "bad compute timings")
                    shots += row["shots"]
                    bad += plain.tally(row, row["shots"])
                    decode += timing["decode_ns"]
                    sampler += timing["sample_ns"]
                    p99.append(timing["batch_window_p99_ns"])
                    used.add(leaf)
                    sources.append({"file": leaf, "sha256": plain.digest(path)})
                complete = shots == total
                pass_ = complete and bad <= cap
                rows.append({"basis": b, "arm": arm, "rounds": rounds, "shots": shots,
                             "failures": bad, "complete": complete, "passes": pass_,
                             "futile": bad > cap, "wilson_upper": plain.wilson_upper(bad, shots) if complete else None,
                             "sampler_ns": sampler, "decoder_ns": decode,
                             "batch_window_p99_ns_range": [min(p99), max(p99)] if p99 else None,
                             "decoder_shot_rounds_per_second": shots*rounds*1e9/decode if shots else None,
                             "source_files": sources})
    check(used == names, "unexpected file in candidate cohort")
    delta = 1 - Fraction(335, 449)
    score = all(row["passes"] for row in rows) and delta >= Fraction(1, 4)
    return {"schema": "b2_corner335_same_condition_audit_v1", "candidate_freeze": freeze,
            "candidate_salt": salt, "controls": controls, "rows": rows,
            "reference_qualifies": True, "reference_checkpoint_sha256": spec["reference_checkpoint_sha256"],
            "candidate_active_qubits": 335, "reference_active_qubits": 449,
            "potential_reduction": float(delta), "comparable_simulation_credit": score,
            "credited_reduction": float(delta) if score else None,
            "b7_resource_credit": 0, "hardware": False, "max_failures": cap}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact-dir", type=Path, required=True)
    p.add_argument("--freeze", required=True)
    p.add_argument("--salt", required=True)
    p.add_argument("--git", default="git")
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    r = build(a.artifact_dir, a.freeze, a.salt, a.git)
    if a.out:
        with a.out.open("x") as f:
            json.dump(r, f, sort_keys=True, indent=2)
            f.write("\n")
    for e in r["rows"]:
        print(e["basis"], e["arm"], e["rounds"], f"{e['failures']}/{e['shots']}",
              "pass" if e["passes"] else "futile" if e["futile"] else "not complete")
    print("Comparable B2 simulation credit", r["comparable_simulation_credit"])


if __name__ == "__main__":
    main()
