#!/usr/bin/env python3
"""Measure an unbatched, full-length trajectory; never award acceptance credit."""

import argparse
import json
from pathlib import Path
import time

import p023_streamed_memory_v1 as s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--distance", required=True, type=int)
    ap.add_argument("--basis", required=True, choices=["x", "z"])
    ap.add_argument("--arm", required=True, choices=["nominal", "paired-readout"])
    ap.add_argument("--rounds", type=int, default=1_000_000)
    ap.add_argument("--freeze", required=True)
    ap.add_argument("--salt", required=True)
    ap.add_argument("--git", default="git")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    p = s.load_protocol()
    s.check_freeze(a.freeze, a.git)
    s.require(a.distance in p["distances"] and a.rounds in p["qualification"]["horizons"]
              and len(bytes.fromhex(a.salt)) == 32 and not a.out.exists(), "invalid timing run")
    c, f = s.fold(a.distance, a.basis, a.rounds, p["noise"])
    m = s.stressed(f, a.distance, p["burst_probability"]) if a.arm == "paired-readout" else f
    seed = s.seed_for("unbatched-timing-only", a.freeze, a.salt, a.distance, a.basis, a.arm, a.rounds)
    start = time.perf_counter_ns()
    streamer = s.Stream(m, f, p["chunk_loop_periods"], a.distance)
    build_ns = time.perf_counter_ns() - start
    print(f"timing-only d{a.distance} {a.basis} {a.arm}, windows={len(streamer.parts)}", flush=True)
    data, timing = streamer.decode(1, seed)
    r = {
        "schema": "p023_streamed_timing_v1",
        "counts_toward_acceptance": False,
        "freeze": a.freeze, "salt": a.salt, "distance": a.distance,
        "basis": a.basis, "arm": a.arm, "rounds": a.rounds,
        "circuit_sha256": s.sha(str(c).encode()), "sampling_dem_sha256": s.sha(str(m.model).encode()),
        "decoder_dem_sha256": s.sha(str(f.model).encode()), "receipt": data,
        "build_ns": build_ns, "timings": timing,
        "guard_rounds_excluded_from_wall_latency": 2 * a.distance,
    }
    with a.out.open("x") as fp:
        json.dump(r, fp, indent=2, sort_keys=True)
        fp.write("\n")
    print(f"completed {a.rounds} decoded rounds, seed={seed} "
          f"sampler_s={timing['sample_ns']/1e9:.3f} decoder_s={timing['decode_ns']/1e9:.3f}", flush=True)


if __name__ == "__main__":
    main()
