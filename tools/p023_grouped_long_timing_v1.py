#!/usr/bin/env python3
"""Record complete unbatched million-round timings, outside qualification."""

import argparse
from pathlib import Path
import time

import p023_grouped_sampler_v1 as grouped
import p023_streamed_memory_grouped_v2 as v2
import p023_streamed_memory_v1 as v1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis", required=True, choices=["x", "z"])
    parser.add_argument("--kernel", required=True, type=Path)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--salt", required=True)
    parser.add_argument("--git", default="git")
    parser.add_argument("--out", required=True, type=Path)
    a = parser.parse_args()
    v1.require(len(bytes.fromhex(a.salt)) == 32 and not a.out.exists(), "invalid timing run")
    base, p, admission, ksha = v2.config(a.freeze, a.git, v1.sha(a.kernel.read_bytes()))
    d, rounds = p["distance"], 1_000_000
    c, f = v1.fold(d, a.basis, rounds, base["noise"])
    start = time.perf_counter_ns()
    stream = v1.Stream(f, f, base["chunk_loop_periods"], d)
    grouped.install(stream, grouped.kernel(a.kernel))
    wall_setup = time.perf_counter_ns() - start
    tick = [0]
    stream.windows = [(v2.Meter(g, tick, len(stream.windows)), guard) for g, guard in stream.windows]
    seed = v1.seed_for("timing-only-grouped", a.freeze, a.salt, d, a.basis, rounds)
    print(f"timing-only d{d} {a.basis} windows={len(stream.windows)}", flush=True)
    r, t = stream.decode(1, seed)
    v1.require(tick[0] == len(stream.windows), "timing run stopped before real endpoint")
    out = {"schema": "p023_grouped_timing_v1", "counts_toward_acceptance": False,
           "distance": d, "rounds": rounds, "basis": a.basis, "arm": "nominal",
           "kernel_sha256": ksha, "freeze": a.freeze, "salt": a.salt, "admission": admission,
           "circuit_sha256": v1.sha(str(c).encode()),
           "sampling_dem_sha256": v1.sha(str(f.model).encode()),
           "decoder_dem_sha256": v1.sha(str(f.model).encode()),
           "receipt": r, "timings": t, "guard_rounds_excluded_from_wall_latency": 2*d,
           "setup_graph_ns": wall_setup}
    v2.atomic_save(a.out, out)
    print(f"complete {rounds} rounds, sampler={t['sample_ns']/1e9:.3f}s, "
          f"decoder={t['decode_ns']/1e9:.3f}s", flush=True)


if __name__ == "__main__":
    main()
