#!/usr/bin/env python3
"""Direct qualification with the admitted probability-grouped DEM sampler."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time

import p023_grouped_sampler_v1 as grouped
import p023_streamed_memory_v1 as v1


PATH = v1.ROOT / "benchmarks/P023_streamed_memory_grouped_v2.json"
SCHEMA = "p023_stream_grouped_shard_v2"


def read(p: Path):
    return json.loads(p.read_bytes())


def performance_pass(item: dict, perf: dict):
    speed = item["performance"]
    stable = speed["steady_samples_ns"]
    whole = speed["pipeline_sample_and_decode_ns"]
    v1.require(speed["shots"] == perf["shots"], "wrong benchmark batch size")
    for key in ("baseline", "grouped"):
        v1.require(len(stable[key]) == perf["steady_repeats_after_warmup"]
                   and len(whole[key]) == perf["pipeline_repeats_after_warmup"]
                   and all(t > 0 for t in stable[key])
                   and all(len(x) == 2 and min(x) > 0 for x in whole[key]), "bad performance samples")
    sr = statistics.median(stable["grouped"]) / statistics.median(stable["baseline"])
    pr = statistics.median(map(sum, whole["grouped"])) / statistics.median(map(sum, whole["baseline"]))
    v1.require(abs(sr - speed["median_sampler_ratio"]) < 1e-12 and
               abs(pr - speed["median_pipeline_ratio"]) < 1e-12, "ratios don't recompute")
    return sr <= perf["require_grouped_to_baseline_sampler_ratio_at_most"] and +        pr <= perf["require_grouped_to_baseline_pipeline_ratio_at_most"]


def config(freeze: str, git: str, kernel_sha: str | None = None):
    base = v1.load_protocol()
    protocol = read(PATH)
    q = base["qualification"]
    evidence = []
    paths = [PATH] + [v1.ROOT / f for f in protocol["source_files"]]
    admission_path = v1.ROOT / protocol["admission_protocol"]
    admission = read(admission_path)
    sha_set = set()
    for b in q["bases"]:
        for arm in q["arms"]:
            name = f"P023_grouped_gate_d15_{b}_{arm}.json"
            path = v1.ROOT / protocol["admission_directory"] / name
            rec = read(path)
            v1.require((rec["distance"], rec["basis"], rec["arm"], rec["schema"]) ==
                       (protocol["distance"], b, arm, admission["schema"])
                       and not rec["counts_toward_memory_gate"], "wrong admission cell")
            v1.require(rec["gate_sha256"] == v1.sha(admission_path.read_bytes()) and
                       rec["performance"]["speed_gate_passed"] and
                       performance_pass(rec, admission["performance"]), "sampler not admitted")
            controls = rec["controls"]
            v1.require(controls["shots"] == admission["same_fault_controls"]["shots"]
                       and len(bytes.fromhex(controls["monolithic_sample_sha256"])) == 32
                       and controls["physical_nonzero_cut_batches"] > 0
                       and controls["correction_nonzero_cut_batches"] > 0
                       and {m["mutation"] for m in controls["negative_controls"]} ==
                       {"drop_correction_spill", "drop_physical_spill"}
                       and all(m["message"].startswith("trajectory stitch dropped parity")
                               for m in controls["negative_controls"]), "missing exact-fault controls")
            for src, expected in rec["code_sha256"].items():
                v1.require(v1.sha((v1.ROOT / "tools" / src).read_bytes()) == expected,
                           "admission code changed")
            sha_set.add(rec["kernel_sha256"])
            paths.append(path)
            evidence.append({"file": name, "sha256": v1.sha(path.read_bytes())})
    v1.require(len(sha_set) == 1 and (kernel_sha is None or kernel_sha in sha_set),
               "worker did not use the admitted native binary")
    for path in paths:
        archived = subprocess.check_output(
            [git, "show", f"{freeze}:{path.relative_to(v1.ROOT)}"], cwd=v1.ROOT)
        v1.require(archived == path.read_bytes(), f"not frozen: {path.name}")
    return base, protocol, evidence, sha_set.pop()


def filename(basis: str, arm: str, rounds: int, shard: int) -> str:
    return f"P023_grouped_d15_{basis}_{arm}_r{rounds}_shard{shard:02}.json"


def planned_seed(freeze: str, salt: str, b: str, arm: str, r: int, i: int) -> int:
    return v1.seed_for("grouped-qualification-v2", freeze, salt, 15, b, arm, r, i)


def pending_blocked(directory: Path, a: argparse.Namespace, q: dict) -> bool:
    cap = v1.planned_cap(q["prespecified_total_shots"], q["failure_target"])
    total = 0
    for i in range(q["shards"]):
        path = directory / filename(a.basis, a.arm, a.rounds, i)
        if path.exists():
            r = read(path)["receipt"]
            v1.require((r["freeze"], r["salt"], r["schema"], r["shard"]) ==
                       (a.freeze, a.salt, SCHEMA, i), "mixed or invalid run directory")
            total += v1.num_failures(r)
    return total > cap


class Meter:
    def __init__(self, matching, shared_counter, total):
        self.matching = matching
        self.shared_counter = shared_counter
        self.total = total

    def decode_batch(self, *args, **kwargs):
        out = self.matching.decode_batch(*args, **kwargs)
        self.shared_counter[0] += 1
        if self.shared_counter[0] % 1024 == 0:
            print(f"matching windows completed {self.shared_counter[0]}/{self.total}", flush=True)
        return out


def atomic_save(dest: Path, payload: dict):
    with tempfile.NamedTemporaryFile("w", dir=dest.parent, prefix=".qec-shard-") as tmp:
        json.dump(payload, tmp, indent=2, sort_keys=True)
        tmp.write("\n")
        tmp.flush()
        os.link(tmp.name, dest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis", choices=["x", "z"], required=True)
    parser.add_argument("--arm", choices=["nominal", "paired-readout"], required=True)
    parser.add_argument("--rounds", type=int, required=True)
    parser.add_argument("--shards", type=int, nargs="+", required=True)
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--salt", required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--git", default="git")
    a = parser.parse_args()
    v1.require(len(bytes.fromhex(a.salt)) == 32 and a.artifact_dir.is_dir(), "invalid inputs")
    admit = v1.sha(a.kernel.read_bytes())
    base, protocol, evidence, ksha = config(a.freeze, a.git, admit)
    q = base["qualification"]
    v1.require(a.rounds in q["horizons"] and len(set(a.shards)) == len(a.shards)
               and all(0 <= i < q["shards"] for i in a.shards), "not a qualification cell")
    d = protocol["distance"]
    c, f = v1.fold(d, a.basis, a.rounds, base["noise"])
    m = v1.stressed(f, d, base["burst_probability"]) if a.arm == "paired-readout" else f
    model_ids = {"circuit_sha256": v1.sha(str(c).encode()),
                 "sampling_dem_sha256": v1.sha(str(m.model).encode()),
                 "decoder_dem_sha256": v1.sha(str(f.model).encode())}
    start = time.perf_counter()
    stream = v1.Stream(m, f, base["chunk_loop_periods"], d)
    grouped.install(stream, grouped.kernel(a.kernel))
    tick = [0]
    stream.windows = [(Meter(g, tick, len(stream.windows)), guard) for g, guard in stream.windows]
    print(f"ready d{d} {a.basis} {a.arm} r={a.rounds}: windows={len(stream.windows)} "
          f"compile_s={time.perf_counter()-start:.3f}", flush=True)
    for i in a.shards:
        dest = a.artifact_dir / filename(a.basis, a.arm, a.rounds, i)
        v1.require(not dest.exists(), f"receipt exists: {dest}")
        if pending_blocked(a.artifact_dir, a, q):
            print(f"futility: not starting shard {i}", flush=True)
            return
        tick[0] = 0
        key = planned_seed(a.freeze, a.salt, a.basis, a.arm, a.rounds, i)
        print(f"started qualification shard {i}", flush=True)
        record, timings = stream.decode(q["shots_per_shard"], key)
        v1.require(tick[0] == len(stream.windows), "incomplete trajectory")
        record |= {"schema": SCHEMA, "distance": d, "basis": a.basis, "arm": a.arm,
                   "rounds": a.rounds, "shard": i, "freeze": a.freeze, "salt": a.salt,
                   "kernel_sha256": ksha, "admission": evidence, "active_qubits": 2*d*d-1,
                   "platform": platform.platform(), **model_ids}
        atomic_save(dest, {"receipt": record, "timings": timings})
        print(f"shard {i}: {record['shots']} complete shots, failures {v1.num_failures(record)}, "
              f"sampler_s={timings['sample_ns']/1e9:.3f} decoder_s={timings['decode_ns']/1e9:.3f}",
              flush=True)


if __name__ == "__main__":
    main()
