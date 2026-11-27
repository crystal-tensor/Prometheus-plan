#!/usr/bin/env python3
"""Control and run the byte-unaligned d12 challenger under the original memory gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import subprocess

import numpy as np
import stim

import b2_p023_d12_stream_v1 as stream
import p023_grouped_sampler_v1 as grouped
import p023_streamed_memory_grouped_v2 as v2
import p023_streamed_memory_v1 as v1


PATH = v1.ROOT / "benchmarks/B2_P023_d12_same_condition_v1.json"
SCHEMA = "b2_p023_d12_shard_v1"
SOURCE = Path(__file__).resolve()


def setup(git, kernel_sha=None):
    p = v2.read(PATH)
    for name, digest in p["source_hashes"].items():
        v1.require(v1.sha((v1.ROOT / name).read_bytes()) == digest, f"changed original gate: {name}")
    base, v2_protocol, admission, kernel = v2.config(p["reference_sampler_freeze"], git, kernel_sha)
    v1.require(p["reference_distance"] == v2_protocol["distance"]
               and p["child_guard_periods"] == v2_protocol["distance"]
               and p["commit_periods"] == base["chunk_loop_periods"], "not the frozen decoder")
    return p, base, admission, kernel


def freeze_check(freeze, git, p, base):
    paths = [PATH, SOURCE, Path(stream.__file__).resolve()]
    controls = []
    d = p["candidate_distance"]
    for b in base["qualification"]["bases"]:
        for arm in base["qualification"]["arms"]:
            path = v1.ROOT / p["controls"]["directory"] / f"B2_d12_control_{b}_{arm}.json"
            r = v2.read(path)
            v1.require((r["distance"], r["basis"], r["arm"]) == (d, b, arm)
                       and r["status"] == "validated_not_qualification" and
                       r["d15_bit_exact_same_seed"] and r["qubit_round_ratio"] > 1.33
                       and len(r["d12_negative_controls"]) == 3
                       and r["d12_same_fault"]["monolithic_sample_sha256"], "missing controls")
            for file in (PATH, SOURCE, Path(stream.__file__).resolve()):
                v1.require(r["controls_source_sha256"][file.name] == v1.sha(file.read_bytes()),
                           "controlled code changed")
            controls.append({"file": path.name, "sha256": v1.sha(path.read_bytes())})
            paths.append(path)
    for path in paths:
        archived = subprocess.check_output(
            [git, "show", f"{freeze}:{path.relative_to(v1.ROOT)}"], cwd=v1.ROOT)
        v1.require(archived == path.read_bytes(), f"not frozen: {path.name}")
    return controls


def stress_test_geometry(d, b):
    geo, c, coords = stream.bounded_geometry(d, b)
    q, start = geo["bulk_detectors"], geo["round0_detectors"] + geo["bulk_detectors"]
    xy = c.get_final_qubit_coordinates()
    for j in range(q):
        a, mid, z = (coords[start+j+k*q] for k in range(3))
        v1.require(a[:2] == mid[:2] == z[:2] and [a[2], mid[2], z[2]] == [2, 3, 4],
                   "wrong paired readout targets")
    for j in (0, q//2, q-1):
        loc = coords[start+j][:2]
        k, = [k for k, r in xy.items() if r == loc]
        circuit = stim.Circuit()
        t = 0
        for op in c.flattened():
            if op.name == "MR":
                if t in (2, 3):
                    v1.require(k in [t.value for t in op.targets_copy()], "wrong readout target")
                    circuit.append("X_ERROR", [k], 1)
                t += 1
            circuit.append(op)
        ds, obs = circuit.compile_detector_sampler(seed=432).sample(1, separate_observables=True)
        v1.require(np.flatnonzero(ds[0]).tolist() == [start+j, start+2*q+j] and not obs[0, 0],
                   "physical paired readout did not match the sampled syndrome")
    return {"bulk_lines": q, "deterministic_physical_checks": 3}


def model(d, b, arm, r, base):
    c, nominal, geo = stream.generate(d, b, r, base["noise"])
    actual = (stream.paired_readout(nominal, geo, base["burst_probability"])
              if arm == "paired-readout" else nominal)
    ids = {"circuit_sha256": v1.sha(str(c).encode()),
           "decoder_dem_sha256": v1.sha(str(nominal.model).encode()),
           "sampling_dem_sha256": v1.sha(str(actual.model).encode())}
    return c, nominal, actual, geo, ids


def verify(p, base, b, arm, k):
    spec = p["controls"]
    d, ref, r, shots = p["candidate_distance"], p["reference_distance"], spec["rounds"], spec["shots"]
    seed = v1.seed_for(spec["seed"], b, arm)
    a = (p["commit_periods"], p["child_guard_periods"])
    c, f, m, g, cand_ids = model(d, b, arm, r, base)
    rc, rf, rm, rg, ref_ids = model(ref, b, arm, r, base)
    original_c, ff = v1.fold(ref, b, r, base["noise"])
    original_m = v1.stressed(ff, ref, base["burst_probability"]) if arm == "paired-readout" else ff
    v1.require(original_c == rc and ff.model == rf.model and original_m.model == rm.model,
               "reference DEM drift")
    original = v1.Stream(original_m, ff, *a, verify=True)
    same = stream.Stream(rm, rf, *a, verify=True)
    candidate = stream.Stream(m, f, *a, verify=True)
    for s in (original, same, candidate):
        grouped.install(s, k)
    expected, _ = original.decode(shots, seed)
    observed, _ = same.decode(shots, seed)
    v1.require(observed == expected, "aligned d15 outputs changed")
    data, _ = candidate.decode(shots, seed)
    v1.require(data["physical_nonzero_cut_batches"] and data["correction_nonzero_cut_batches"],
               "unexercised boundary")
    broken = []
    for key, msg in (("drop_physical_spill", "trajectory stitch dropped parity"),
                     ("drop_correction_spill", "trajectory stitch dropped parity"),
                     ("truncate_terminal_byte", "terminal detector byte was truncated")):
        try:
            candidate.decode(shots, seed, **{key: True})
        except ValueError as e:
            v1.require(str(e) == msg, "different failure for the negative control")
            broken.append({"mutation": key, "rejected_for": str(e)})
        else:
            raise AssertionError(key)
    v1.require(g["ticks_per_round"] == rg["ticks_per_round"] == 7
               and g["all_cx_local"] and rg["all_cx_local"], "not same-condition connectivity or cycles")
    reduction = 1 - g["active_qubits"]/rg["active_qubits"]
    v1.require(reduction >= p["minimum_physical_qubit_round_reduction"], "insufficient resource delta")
    return {"schema": "b2_p023_d12_control_v1", "status": "validated_not_qualification",
            "distance": d, "basis": b, "arm": arm, "rounds": r,
            "controls_source_sha256": {file.name: v1.sha(file.read_bytes()) for file in
                                       (PATH, SOURCE, Path(stream.__file__).resolve())},
            "d15_bit_exact_same_seed": True, "d15_geometry": rg, "d12_geometry": g,
            "d12_detector_count": c.num_detectors, "d12_terminal_bits": candidate.parts[-1].core,
            "d12_same_fault": data, "d12_negative_controls": broken,
            "d12_stress_geometry": stress_test_geometry(d, b),
            "d15_models": ref_ids, "d12_models": cand_ids, "qubit_round_reduction": reduction,
            "qubit_round_ratio": rg["active_qubits"]/g["active_qubits"]}


def filename(b, arm, rounds, shard):
    return f"B2_d12_{b}_{arm}_r{rounds}_shard{shard:02}.json"


def shard_seed(freeze, salt, b, arm, rounds, i):
    return v1.seed_for("B2-d12-same-noise-v1", freeze, salt, 12, b, arm, rounds, i)


def counts(directory, freeze, salt, b, arm, rounds, q):
    shots = bad = 0
    for i in range(q["shards"]):
        file = directory / filename(b, arm, rounds, i)
        if file.exists():
            x = v2.read(file)["receipt"]
            v1.require((x["schema"], x["freeze"], x["salt"], x["basis"], x["arm"], x["rounds"],
                        x["shard"], x["shots"]) ==
                       (SCHEMA, freeze, salt, b, arm, rounds, i, q["shots_per_shard"]), "mixed receipts")
            shots += x["shots"]
            bad += v1.num_failures(x)
    return shots, bad


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=["control", "qualification"])
    parser.add_argument("--basis", required=True, choices=["x", "z"])
    parser.add_argument("--arm", required=True, choices=["nominal", "paired-readout"])
    parser.add_argument("--kernel", required=True, type=Path)
    parser.add_argument("--artifact-dir", required=True, type=Path)
    parser.add_argument("--git", default="git")
    parser.add_argument("--freeze")
    parser.add_argument("--salt")
    parser.add_argument("--rounds", type=int, default=1000)
    parser.add_argument("--shards", type=int, nargs="+")
    a = parser.parse_args()
    v1.require(a.artifact_dir.is_dir(), "missing output directory")
    p, base, _, ksha = setup(a.git, v1.sha(a.kernel.read_bytes()))
    k = grouped.kernel(a.kernel)
    if a.mode == "control":
        out = a.artifact_dir / f"B2_d12_control_{a.basis}_{a.arm}.json"
        v1.require(not out.exists(), "control already written")
        r = verify(p, base, a.basis, a.arm, k)
        v2.atomic_save(out, r)
        print(f"{a.basis} {a.arm} exact d15 and d12 replay; terminal and both seam faults rejected", flush=True)
        return

    q = base["qualification"]
    v1.require(a.freeze and a.salt and len(bytes.fromhex(a.salt)) == 32 and
               a.rounds in q["horizons"] and a.shards and len(a.shards) == len(set(a.shards)) and
               all(0 <= i < q["shards"] for i in a.shards), "invalid qualification inputs")
    controls = freeze_check(a.freeze, a.git, p, base)
    cap = v1.planned_cap(q["prespecified_total_shots"], q["failure_target"])
    if a.rounds == 1_000_000:
        for b in q["bases"]:
            for arm in q["arms"]:
                n, bad = counts(a.artifact_dir, a.freeze, a.salt, b, arm, 1000, q)
                v1.require(n == q["prespecified_total_shots"] and bad <= cap, "short gate not closed")
    d = p["candidate_distance"]
    c, nominal, sample, geo, ids = model(d, a.basis, a.arm, a.rounds, base)
    s = stream.Stream(sample, nominal, p["commit_periods"], p["child_guard_periods"])
    grouped.install(s, k)
    tick = [0]
    s.windows = [(v2.Meter(g, tick, len(s.windows)), guard) for g, guard in s.windows]
    print(f"d{d} {a.basis} {a.arm} rounds={a.rounds}, {len(s.windows)} windows", flush=True)
    for i in a.shards:
        path = a.artifact_dir / filename(a.basis, a.arm, a.rounds, i)
        v1.require(not path.exists(), "qualification shard already exists")
        _, bad = counts(a.artifact_dir, a.freeze, a.salt, a.basis, a.arm, a.rounds, q)
        if bad > cap:
            print(f"futility: not starting shard {i}", flush=True)
            return
        tick[0] = 0
        key = shard_seed(a.freeze, a.salt, a.basis, a.arm, a.rounds, i)
        r, timings = s.decode(q["shots_per_shard"], key)
        v1.require(tick[0] == len(s.windows), "incomplete trajectory")
        r |= {"schema": SCHEMA, "distance": d, "basis": a.basis, "arm": a.arm, "rounds": a.rounds,
              "shard": i, "freeze": a.freeze, "salt": a.salt, "kernel_sha256": ksha,
              "detector_count": c.num_detectors, "controls": controls, "geometry": geo,
              "platform": platform.platform(), **ids}
        v2.atomic_save(path, {"receipt": r, "timings": timings})
        print(f"shard {i} complete, failures={v1.num_failures(r)}", flush=True)


if __name__ == "__main__":
    main()
