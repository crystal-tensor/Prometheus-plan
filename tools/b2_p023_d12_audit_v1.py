#!/usr/bin/env python3
"""Compare d12 to the bound d15 reference without pooling cohorts."""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
import math
from pathlib import Path

import b2_p023_d12_gate_v1 as candidate
import b2_p023_d12_stream_v1 as stream
import p023_streamed_memory_audit_v1 as v1_audit
import p023_streamed_memory_grouped_audit_v2 as ref_audit


def build(directory, ref_dir, freeze, salt, ref_salt, git):
    spec, base, _, kernel = candidate.setup(git)
    controls = candidate.freeze_check(freeze, git, spec, base)
    p = base["qualification"]
    full_n, target = p["prespecified_total_shots"], p["failure_target"]
    cap = math.floor(full_n*target - v1_audit.Z*math.sqrt(full_n*target*(1-target)))
    check = v1_audit.check
    check(v1_audit.wilson_upper(cap, full_n) <= target < v1_audit.wilson_upper(cap+1, full_n),
          "wrong cutoff")
    check(len(bytes.fromhex(salt)) == len(bytes.fromhex(ref_salt)) == 32 and salt != ref_salt,
          "candidate and reference must be independent")
    ref = ref_audit.audit(ref_dir, spec["reference_sampler_freeze"], ref_salt, git)
    available = {x.name for x in directory.glob("B2_d12_*_shard*.json")}
    covered, seeds = set(), set()
    d, d_ref = spec["candidate_distance"], spec["reference_distance"]
    cand_q = ref_q = None
    rows = []
    for rounds in p["horizons"]:
        for b in p["bases"]:
            for arm in p["arms"]:
                c, nominal, sampling, geo, ids = candidate.model(d, b, arm, rounds, base)
                rc, _, _, rg, source_ref = candidate.model(d_ref, b, arm, rounds, base)
                known_ref, _, _ = v1_audit.source_models(base, d_ref, b, rounds, arm)
                check(known_ref == source_ref, "even-stream interpretation changed reference hashes")
                check(c.num_ticks == rc.num_ticks and
                      geo["all_cx_local"] and rg["all_cx_local"], "not comparable geometry or ticks")
                check(cand_q is None or (cand_q, ref_q) ==
                      (geo["active_qubits"], rg["active_qubits"]), "qubit ledger is not stable")
                cand_q, ref_q = geo["active_qubits"], rg["active_qubits"]
                parts = stream.partition(sampling, spec["commit_periods"])
                guard = spec["child_guard_periods"]*nominal.step
                width = max(a.core + (min(z.core, guard) if z else 0)
                            for a, z in zip(parts, parts[1:] + [None], strict=True))
                n = k = duration = 0
                receipts = []
                for i in range(p["shards"]):
                    name = candidate.filename(b, arm, rounds, i)
                    if name not in available:
                        continue
                    leaf = directory / name
                    pair = v1_audit.load(leaf)
                    x, t = pair["receipt"], pair["timings"]
                    check((x["schema"], x["freeze"], x["salt"], x["basis"], x["arm"], x["rounds"],
                           x["shard"], x["distance"]) ==
                          (candidate.SCHEMA, freeze, salt, b, arm, rounds, i, d), "wrong candidate cell")
                    check(all(x[k] == v for k, v in ids.items())
                          and x["kernel_sha256"] == kernel and x["controls"] == controls and x["geometry"] == geo,
                          "unmatched circuit, kernel or geometry")
                    key = v1_audit.seed(("B2-d12-same-noise-v1", freeze, salt, d, b, arm, rounds, i))
                    check(key == x["seed"] and key not in seeds, "reused or invalid seed")
                    seeds.add(key)
                    shots = p["shots_per_shard"]
                    check((x["shots"], x["windows"], x["max_graph_detectors"], x["detector_count"]) ==
                          (shots, len(parts), width, c.num_detectors), "wrong detector coverage")
                    check(all(0 < x[t] < len(parts) for t in
                              ("physical_nonzero_cut_batches", "correction_nonzero_cut_batches")),
                          "unexercised boundary")
                    check(0 < t["batch_window_p99_ns"] <= t["max_window_ns"] <= t["decode_ns"]
                          and t["sample_ns"] > 0, "bad timing")
                    n += shots
                    k += v1_audit.tally(x, shots)
                    duration += t["sample_ns"] + t["decode_ns"]
                    covered.add(name)
                    receipts.append({"file": name, "sha256": v1_audit.digest(leaf)})
                ok = n == full_n and k <= cap
                rows.append({"basis": b, "arm": arm, "rounds": rounds, "shots": n, "failures": k,
                             "acceptance_credit": ok,
                             "futile_for_frozen_size": k > cap, "file_count": len(receipts),
                             "wilson_95_upper": v1_audit.wilson_upper(k, n) if n == full_n else None,
                             "detectors": c.num_detectors, "max_window_detectors": width,
                             "core_rounds": 2*spec["commit_periods"], "guard_rounds": 2*spec["child_guard_periods"],
                             "host_sample_decode_seconds": duration/1e9,
                             "receipts": receipts})
    check(covered == available, "unexpected candidate files")
    ratio = Fraction(ref_q, cand_q)
    reduction = 1-Fraction(cand_q, ref_q)
    cand_passes = all(r["acceptance_credit"] for r in rows)
    ref_passes = ref["qualifies_both_horizons_bases_arms"]
    permitted = (cand_passes and ref_passes and reduction >=
                 Fraction(str(spec["minimum_physical_qubit_round_reduction"])))
    return {"schema": "b2_p023_d12_audit_v1", "candidate_freeze": freeze, "salt": salt,
            "reference_freeze": ref["freeze"], "reference_salt": ref_salt,
            "maximum_failures_per_1024": cap, "comparison_has_no_pooled_shots": True,
            "potential_resources_not_credit": {
                "qubits_ratio_exact": f"{ratio.numerator}/{ratio.denominator}",
                "reduction": float(reduction),
                "d12_million_round_qubit_rounds": cand_q*1_000_000,
                "d15_million_round_qubit_rounds": ref_q*1_000_000},
            "b2_same_condition_simulator_credit": permitted,
            "b2_credit_gate_reduction": float(reduction) if permitted else None,
            "b7_resource_credit": 0, "calibrated_hardware": False,
            "controls": controls, "candidate_rows": rows, "reference_rows": ref["rows"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--salt", required=True)
    parser.add_argument("--reference-salt", required=True)
    parser.add_argument("--git", default="git")
    parser.add_argument("--out", type=Path)
    a = parser.parse_args()
    r = build(a.artifact_dir, a.reference_dir, a.freeze, a.salt, a.reference_salt, a.git)
    if a.out:
        with a.out.open("x") as f:
            json.dump(r, f, sort_keys=True, indent=2)
            f.write("\n")
    for tag, rows in (("d12", r["candidate_rows"]), ("d15", r["reference_rows"])):
        for row in rows:
            n = row["shots"]
            upper = row["wilson_95_upper"]
            print(f"{tag} {row['basis'].upper()} {row['arm']:15} {row['rounds']:7}: "
                  + (f"{row['failures']}/{n}" if n else "not measured")
                  + (f" full bound={upper:.6f}" if upper is not None else " (no qualification)"))
    print("B2 comparable simulator credit", r["b2_same_condition_simulator_credit"])


if __name__ == "__main__":
    main()
