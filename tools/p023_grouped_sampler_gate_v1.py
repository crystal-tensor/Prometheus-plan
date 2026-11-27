#!/usr/bin/env python3
"""Compare warm performance and exact same-fault replay on the real d15 streams."""

import argparse
import json
from pathlib import Path
import statistics
import time

import numpy as np

import p023_grouped_sampler_v1 as grouped
import p023_streamed_memory_v1 as v1


GATE = v1.ROOT / "benchmarks/P023_grouped_sampler_gate_v1.json"


def two_schedulers(a, b, n):
    timings = {name: [] for name in ("baseline", "grouped")}
    for i in range(n):
        order = (("baseline", a), ("grouped", b))
        for key, f in (reversed(order) if i % 2 else order):
            timings[key].append(f())
    return timings


def verify(a, f, sample, kernel, fold_params, p):
    c = p["same_fault_controls"]
    stream = v1.Stream(sample, f, *fold_params, verify=True)
    grouped.install(stream, kernel)
    r, _ = stream.decode(c["shots"], v1.seed_for(c["seed"], a.basis, a.arm))
    v1.require(r["physical_nonzero_cut_batches"] > 0 and r["correction_nonzero_cut_batches"] > 0,
               "no exercised dependency across a cut")
    bad = []
    for name in ("drop_physical_spill", "drop_correction_spill"):
        try:
            stream.decode(c["shots"], v1.seed_for(c["seed"], a.basis, a.arm), **{name: True})
        except ValueError as e:
            v1.require(str(e).startswith("trajectory stitch dropped parity"), "unexpected error")
            bad.append({"mutation": name, "message": str(e)})
        else:
            raise AssertionError(f"missing rejection: {name}")
    return {k: r[k] for k in ("shots", "windows", "max_graph_detectors",
                              "monolithic_sample_sha256", "physical_nonzero_cut_batches",
                              "correction_nonzero_cut_batches")} | {"negative_controls": bad}


def measure(a, f, sample, kernel, fold_params, p):
    perf = p["performance"]
    shots = perf["shots"]
    key = v1.seed_for(perf["seed"], a.basis, a.arm)
    dem = v1.partition(sample, fold_params[0])[1].model
    a0 = dem.compile_sampler(seed=key)
    layout = grouped.Mechanisms(dem)
    a1 = grouped.Sampler(layout, kernel, key)
    a0.sample(shots, bit_packed=True)
    a1.sample(shots, bit_packed=True)

    def one(fn):
        start = time.perf_counter_ns()
        ds, o, _ = fn.sample(shots, bit_packed=True)
        elapsed = time.perf_counter_ns() - start
        v1.require(ds.shape == (shots, layout.width) and o.shape == (shots, 1),
                   "samplers do not produce corresponding shapes")
        return elapsed

    steady = two_schedulers(lambda: one(a0), lambda: one(a1), perf["steady_repeats_after_warmup"])
    plain = v1.Stream(sample, f, *fold_params)
    fast = v1.Stream(sample, f, *fold_params)
    grouped.install(fast, kernel)
    for stream in (plain, fast):
        stream.decode(shots, key)

    def work(stream):
        _, timing = stream.decode(shots, key)
        return [timing["sample_ns"], timing["decode_ns"]]

    pipeline = two_schedulers(lambda: work(plain), lambda: work(fast),
                              perf["pipeline_repeats_after_warmup"])
    sr = statistics.median(steady["grouped"]) / statistics.median(steady["baseline"])
    pr = (statistics.median(map(sum, pipeline["grouped"])) /
          statistics.median(map(sum, pipeline["baseline"])))
    # Read the original probabilities from Stim again with a different
    # enumeration to catch any reindexing or accidental weight combination.
    probs = np.fromiter((op.args_copy()[0] for op in dem.flattened() if op.type == "error"),
                        dtype=np.float64, count=dem.num_errors)
    coverage = np.zeros(dem.num_errors, dtype=np.uint8)
    for weight, ids in layout.groups:
        v1.require(np.all(probs[ids] == weight) and np.unique(ids).size == ids.size,
                   "changed probability or duplicated index")
        coverage[ids] += 1
    v1.require(np.all(coverage == 1), "probability classification not a partition")
    return {"mechanisms_per_steady_segment": dem.num_errors,
            "exact_probability_classes": len(layout.groups), "shots": shots,
            "steady_samples_ns": steady, "pipeline_sample_and_decode_ns": pipeline,
            "median_sampler_ratio": sr, "median_pipeline_ratio": pr,
            "speed_gate_passed": sr <= perf["require_grouped_to_baseline_sampler_ratio_at_most"]
            and pr <= perf["require_grouped_to_baseline_pipeline_ratio_at_most"]}


def main():
    q = argparse.ArgumentParser(description=__doc__)
    q.add_argument("--basis", choices=["x", "z"], required=True)
    q.add_argument("--arm", choices=["nominal", "paired-readout"], required=True)
    q.add_argument("--kernel", type=Path, required=True)
    q.add_argument("--out", type=Path, required=True)
    a = q.parse_args()
    p = json.loads(GATE.read_bytes())
    base = v1.load_protocol()
    v1.require(not a.out.exists(), "performance receipt must be new")
    d = p["distance"]
    _, f = v1.fold(d, a.basis, p["performance"]["rounds"], base["noise"])
    sample = v1.stressed(f, d, base["burst_probability"]) if a.arm == "paired-readout" else f
    k = grouped.kernel(a.kernel)
    params = (base["chunk_loop_periods"], d)
    control = verify(a, f, sample, k, params, p)
    print(f"{a.basis.upper()} {a.arm}: same-fault replay and both broken seams verified", flush=True)
    speed = measure(a, f, sample, k, params, p)
    o = {"schema": p["schema"], "distance": d, "basis": a.basis, "arm": a.arm,
         "gate_sha256": v1.sha(GATE.read_bytes()), "kernel_sha256": v1.sha(a.kernel.read_bytes()),
         "sampling_model_sha256": v1.sha(str(sample.model).encode()),
         "code_sha256": {path.name: v1.sha(path.read_bytes()) for path in
                         (Path(__file__), grouped.SOURCE, Path(grouped.__file__))},
         "controls": control, "performance": speed, "counts_toward_memory_gate": False}
    with a.out.open("x") as f_out:
        json.dump(o, f_out, indent=2, sort_keys=True)
        f_out.write("\n")
    print(f"{a.basis.upper()} {a.arm} sampler ratio {speed['median_sampler_ratio']:.4f}; "
          f"pipeline ratio {speed['median_pipeline_ratio']:.4f}; "
          f"accepted {speed['speed_gate_passed']}", flush=True)


if __name__ == "__main__":
    main()
