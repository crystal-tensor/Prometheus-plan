#!/usr/bin/env python3
"""Audit staged #023 receipts without giving incomplete cohorts acceptance credit."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics

import p023_streamed_memory_v1 as run


Z = statistics.NormalDist().inv_cdf(0.975)


def check(ok: bool, label: str) -> None:
    if not ok:
        raise AssertionError(label)


def load(path: Path) -> dict:
    return json.loads(path.read_bytes())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson_upper(k: int, n: int) -> float:
    # Invert the score test instead of using the recorder's closed form.
    if k == n:
        return 1.0
    f = k / n
    a, b = f, 1.0
    for _ in range(70):
        m = (a + b) / 2
        if (m - f) * math.sqrt(n / (m * (1 - m))) > Z:
            b = m
        else:
            a = m
    return (a + b) / 2


def bits(r: dict, field: str, n: int) -> int:
    data = bytes.fromhex(r[field + "_le_hex"])
    value = int.from_bytes(data, "little")
    check(len(data) == math.ceil(n / 8) and value.bit_length() <= n, "invalid bit vector")
    return value


def tally(r: dict, n: int) -> int:
    failed = bits(r, "failures", n)
    check(failed == bits(r, "truth", n) ^ bits(r, "correction", n), "failure vector differs")
    check(len(bytes.fromhex(r["sample_sha256"])) == 32, "invalid sample digest")
    return failed.bit_count()


def check_controls(directory: Path, p: dict) -> list:
    out = []
    for d in p["distances"]:
        for b in p["qualification"]["bases"]:
            file = directory / f"P023_stream_controls_d{d}_{b}.json"
            a = load(file)
            check((a["distance"], a["basis"]) == (d, b) and
                  a["coordinate_lines_checked"] == d*d - 1 and
                  a["deterministic_circuit_bursts_checked"] == 3 and
                  set(a["arms"]) == set(p["qualification"]["arms"]), "controls incomplete")
            for c in a["arms"].values():
                r = c["same_fault_replay"]
                check(r["shots"] == p["control_shots"] and
                      len(bytes.fromhex(r["monolithic_sample_sha256"])) == 32 and
                      r["physical_nonzero_cut_batches"] > 0 and
                      r["correction_nonzero_cut_batches"] > 0, "unexercised seam")
                check({j["mutation"] for j in c["negative_controls"]} ==
                      {"drop_physical_spill", "drop_correction_spill"} and
                      all(j["rejected_by"].startswith("trajectory stitch dropped parity")
                          for j in c["negative_controls"]), "missing negative controls")
                tally(r, p["control_shots"])
            out.append({"receipt": file.name, "sha256": digest(file)})
    return out


def source_models(p: dict, d: int, b: str, r: int, arm: str):
    c, f = run.fold(d, b, r, p["noise"])
    check(c.num_measurements == r*(d*d-1) + d*d and c.num_detectors == r*(d*d-1),
          "not a continuous circuit with one final data measurement")
    check(f.count == r // 2 - 2, "unknown folded layout")
    m = run.stressed(f, d, p["burst_probability"]) if arm != "nominal" else f
    models = {"circuit_sha256": run.sha(str(c).encode()),
              "decoder_dem_sha256": run.sha(str(f.model).encode()),
              "sampling_dem_sha256": run.sha(str(m.model).encode())}
    parts = run.partition(f, p["chunk_loop_periods"])
    max_width = max(part.core + (min(nxt.core, d*f.step) if nxt else 0)
                    for part, nxt in zip(parts, parts[1:] + [None], strict=True))
    check(sum(part.core for part in parts) == c.num_detectors, "coverage of detector frames")
    return models, len(parts), max_width


def seed(raw: tuple) -> int:
    return int.from_bytes(hashlib.sha256(repr(raw).encode()).digest()[:8], "little")


def do_audit(directory: Path, freeze: str, salt: str) -> dict:
    p = run.load_protocol()
    q = p["qualification"]
    full_n = q["shards"] * q["shots_per_shard"]
    check(full_n == q["prespecified_total_shots"], "wrong total")
    target = q["failure_target"]
    cap = math.floor(full_n * target - Z * math.sqrt(full_n * target * (1 - target)))
    check(wilson_upper(cap, full_n) <= target < wilson_upper(cap+1, full_n), "cutoff")
    row_matrix = []
    seen = set()
    qualified_names = set()
    available = {j.name for j in directory.glob("P023_stream_d*_shard*.json")
                 if j.stat().st_size > 0}
    for d in p["distances"]:
        for r in q["horizons"]:
            for b in q["bases"]:
                for arm in q["arms"]:
                    stem = f"P023_stream_d{d}_{b}_{arm}_r{r}"
                    rows = []
                    missing = []
                    nbad = nshots = timer = sampler = 0
                    timings = []
                    models, windows, max_graph = source_models(p, d, b, r, arm)
                    for i in range(q["shards"]):
                        leaf = f"{stem}_shard{i:02}.json"
                        file = directory / leaf
                        if leaf not in available:
                            missing.append(i)
                            continue
                        qualified_names.add(leaf)
                        item = load(file)
                        rec, t = item["receipt"], item["timings"]
                        check(rec["schema"] == "p023_streamed_memory_shard_v1" and
                              (rec["distance"], rec["basis"], rec["arm"], rec["rounds"], rec["shard"],
                               rec["freeze"], rec["salt"], rec["mode"]) ==
                              (d, b, arm, r, i, freeze, salt, "qualification"), f"wrong cell: {leaf}")
                        check(all(rec[k] == v for k, v in models.items()), f"wrong models: {leaf}")
                        check(rec["seed"] == seed((freeze, salt, d, b, arm, r, i)) and
                              rec["seed"] not in seen, f"wrong/reused seed: {leaf}")
                        seen.add(rec["seed"])
                        shot = q["shots_per_shard"]
                        check((rec["shots"], rec["windows"], rec["max_graph_detectors"],
                               rec["active_qubits"]) == (shot, windows, max_graph, 2*d*d-1),
                              f"wrong shapes: {leaf}")
                        check(all(0 < rec[k] < windows for k in
                                  ("physical_nonzero_cut_batches", "correction_nonzero_cut_batches")),
                              f"missing active boundaries: {leaf}")
                        check(0 < t["batch_window_p99_ns"] <= t["max_window_ns"] <= t["decode_ns"]
                              and t["sample_ns"] > 0, f"wrong timing: {leaf}")
                        nshots += shot
                        nbad += tally(rec, shot)
                        timer += t["decode_ns"]
                        sampler += t["sample_ns"]
                        timings.append(t["batch_window_p99_ns"])
                        rows.append({"receipt": leaf, "sha256": digest(file)})
                    is_full = not missing
                    pass_gate = is_full and nbad <= cap
                    decision = (
                        "pass" if pass_gate else "cannot_pass_even_if_remaining_shots_succeed"
                        if nbad > cap else "not_yet_measured" if not rows else "incomplete_no_credit"
                    )
                    e = {"distance": d, "basis": b, "arm": arm, "rounds": r,
                         "qualified": pass_gate, "status": decision,
                         "shots": nshots, "failures": nbad,
                         "wilson_95_upper": wilson_upper(nbad, nshots) if is_full else None,
                         "selector": {"missing_shards": missing, "used_shards": rows},
                         "row_rounds_simulated": r*nshots,
                         "windows_per_shot": windows, "max_graph_detectors": max_graph,
                         "host_timings": None if not rows else {
                             "total_sampler_seconds": sampler / 1e9,
                             "total_decoder_stitch_seconds": timer / 1e9,
                             "decode_rounds_per_second_sum_of_shard_seconds": r*nshots*1e9 / timer,
                             "min_of_shard_batch_window_p99_ms": min(timings) / 1e6,
                             "max_of_shard_batch_window_p99_ms": max(timings) / 1e6,
                             "batch_size": q["shots_per_shard"],
                         }}
                    row_matrix.append(e)

    check(available == qualified_names, "unexpected qualification shard files")
    pilots = []
    for file in sorted(directory.glob("P023_stream_timing_*.json")):
        z = load(file)
        d, b, r, arm = (z[k] for k in ("distance", "basis", "rounds", "arm"))
        check(z["schema"] == "p023_streamed_timing_v1" and not z["counts_toward_acceptance"] and
              d in p["distances"] and b in q["bases"] and r in q["horizons"] and arm in q["arms"] and
              (z["freeze"], z["salt"]) == (freeze, salt), f"invalid timing pilot: {file.name}")
        models, windows, max_graph = source_models(p, d, b, r, arm)
        check(all(z[k] == v for k, v in models.items()), "timing source binding")
        rec, t = z["receipt"], z["timings"]
        check((rec["shots"], rec["windows"], rec["max_graph_detectors"], rec["seed"]) ==
              (1, windows, max_graph, seed(("unbatched-timing-only", freeze, salt, d, b, arm, r))) and
              rec["seed"] not in seen, "timing stream reuses or has wrong sample")
        seen.add(rec["seed"])
        tally(rec, 1)
        pilots.append({"receipt": file.name, "sha256": digest(file), "distance": d, "basis": b,
                       "rounds": r, "arm": arm, "windows": windows, "max_graph_detectors": max_graph,
                       "p99_compute_ms": t["batch_window_p99_ns"]/1e6,
                       "host_decode_stitch_seconds": t["decode_ns"]/1e9,
                       "host_sampling_seconds": t["sample_ns"]/1e9})

    passed = [d for d in p["distances"] if all(row["qualified"] for row in row_matrix
                                               if row["distance"] == d)]
    return {
        "schema": "p023_streamed_checkpoint_v1", "freeze": freeze, "salt": salt,
        "protocol_sha256": digest(run.PROTOCOL), "audit_sha256": digest(Path(__file__)),
        "controls": check_controls(directory, p), "complete_direct_rows": sum(
            row["wilson_95_upper"] is not None for row in row_matrix),
        "planned_shots": full_n, "max_failed_shots": cap,
        "rows": row_matrix, "unbatched_timing_only": pilots,
        "both_horizons_bases_and_arms_pass_distance": passed,
        "claim_boundary": {"hardware": False, "full_b2": False, "b7_resource_credit": 0,
                           "batch_window_timing_is_not_controller_response": True},
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact-dir", type=Path, required=True)
    p.add_argument("--freeze", required=True)
    p.add_argument("--salt", required=True)
    p.add_argument("--git", default="git")
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    run.check_freeze(a.freeze, a.git)
    r = do_audit(a.artifact_dir, a.freeze, a.salt)
    if a.out:
        with a.out.open("x") as f:
            json.dump(r, f, indent=2, sort_keys=True)
            f.write("\n")
    for e in r["rows"]:
        print(f"d{e['distance']:2} {e['basis'].upper()} {e['arm']:15} {e['rounds']:7} "
              f"{e['failures']:3}/{e['shots']:4} {e['status']}")
    print(f"full rows={r['complete_direct_rows']} cap={r['max_failed_shots']} timing-only="
          f"{len(r['unbatched_timing_only'])} qualified distances="
          f"{r['both_horizons_bases_and_arms_pass_distance']}")


if __name__ == "__main__":
    main()
