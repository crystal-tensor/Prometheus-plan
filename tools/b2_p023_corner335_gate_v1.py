#!/usr/bin/env python3
"""Run the compact 335-qubit circuit on the same fixed gate as d15."""

import argparse
import json
from pathlib import Path
import subprocess

import stim

import b2_corner_shortening_preflight_v1 as pre
import b2_p023_corner335_stream_v1 as corner
import b2_p023_d12_stream_v1 as even
import p023_grouped_sampler_v1 as g
import p023_streamed_memory_grouped_v2 as v2
import p023_streamed_memory_v1 as v1


PATH = v1.ROOT / "benchmarks/B2_P023_corner335_same_condition_v1.json"
CODE = (PATH, Path(__file__).resolve(), Path(corner.__file__).resolve())
SCHEMA = "b2_p023_corner335_qualification_shard_v1"


def config(git, kernel_sha=None):
    s = v2.read(PATH)
    source = v1.ROOT / s["reference_directory"] / "checkpoint.json"
    original = v1.ROOT / "benchmarks/B2_B7_P023_logical_memory_horizon_gate_v1.json"
    proof = v1.ROOT / "results/P023_B2_stress_counterfactual_v1/corner_checked.json"
    for path, key in ((source, "reference_checkpoint_sha256"), (original, "original_gate_sha256"),
                      (proof, "corner_preflight_sha256")):
        v1.require(v1.sha(path.read_bytes()) == s[key], f"changed {key}")
    reference = v2.read(source)
    v1.require(reference["qualifies_both_horizons_bases_arms"] and
               reference["freeze"] == s["reference_freeze"], "no qualified denominator")
    base, _, _, k = v2.config(s["reference_freeze"], git, kernel_sha)
    v1.require(base["chunk_loop_periods"] == s["commit_periods"] == 64 and s["guard_periods"] == 15,
               "not the reference memory decoder")
    return s, base, reference, v2.read(proof), k


def controls(s, base, proof, basis, arm, fn):
    c, _ = corner.circuit(basis, 15, base["noise"])
    old = stim.Circuit.generated(f"surface_code:rotated_memory_{basis}", distance=13, rounds=15,
                                 **base["noise"]).flattened()
    f = c.flattened()
    v1.require(f == pre.project(old, *corner.sites(basis)) and
               v1.sha(str(f).encode()) == proof["arms"][basis]["fix_corner_x"]["circuit_sha256"],
               "compact circuit not identical to the checked projection")
    phases = corner.confirm_phases(basis)
    a, n, m, geo, short = corner.model(basis, arm, 1000, base)
    b, _, full, _, long = corner.model(basis, arm, 1_000_000, base)
    s0 = even.Stream(m, n, s["commit_periods"], s["guard_periods"], verify=True)
    g.install(s0, fn)
    shots, seed = s["controls_per_cell"], v1.seed_for("corner-control-v1", basis, arm)
    result, _ = s0.decode(shots, seed)
    v1.require(result["physical_nonzero_cut_batches"] > 0 and result["correction_nonzero_cut_batches"] > 0,
               "control did not exercise the seams")
    bad = []
    for name in ("drop_physical_spill", "drop_correction_spill", "truncate_terminal_byte"):
        try:
            s0.decode(shots, seed, **{name: True})
        except ValueError as e:
            v1.require(str(e) == ("terminal detector byte was truncated" if name.startswith("truncate")
                                 else "trajectory stitch dropped parity"), "unexpected rejection")
            bad.append(name)
        else:
            raise AssertionError(name)
    return {"basis": basis, "arm": arm, "controls_source_sha": {p.name:v1.sha(p.read_bytes()) for p in CODE},
            "compact_matches_unrolled": True, "monolithic_sample_sha256": result["monolithic_sample_sha256"],
            "negative_controls": bad, "stress_phase_checks": phases, "geometry": geo,
            "short": short | {"ticks": a.num_ticks, "detectors": a.num_detectors},
            "long": long | {"ticks": b.num_ticks, "detectors": b.num_detectors,
                            "compiled_plan_windows": len(even.partition(full, s["commit_periods"]))},
            "qualification_credit": False}


def freeze_check(s, q, commit, git):
    paths = list(CODE)
    evidence = []
    for b in q["bases"]:
        for arm in q["arms"]:
            p = v1.ROOT / s["controls_dir"] / f"B2_corner335_control_{b}_{arm}.json"
            d = v2.read(p)
            v1.require(d["basis"] == b and d["arm"] == arm and d["compact_matches_unrolled"]
                       and d["monolithic_sample_sha256"] and len(d["negative_controls"]) == 3
                       and not d["qualification_credit"]
                       and d["controls_source_sha"] == {p.name:v1.sha(p.read_bytes()) for p in CODE},
                       "unverified control")
            paths.append(p)
            evidence.append({"file": p.name, "sha256": v1.sha(p.read_bytes())})
    for p in paths:
        frozen = subprocess.check_output([git, "show", f"{commit}:{p.relative_to(v1.ROOT)}"], cwd=v1.ROOT)
        v1.require(frozen == p.read_bytes(), f"not frozen: {p.name}")
    return evidence


def filename(b, arm, rounds, i):
    return f"B2_corner335_{b}_{arm}_r{rounds}_shard{i:02}.json"


def key(freeze, salt, b, arm, r, i):
    return v1.seed_for("B2-corner335-v1", freeze, salt, b, arm, r, i)


def count(directory, freeze, salt, b, arm, r, q):
    n = bad = 0
    for i in range(q["shards"]):
        p = directory / filename(b, arm, r, i)
        if p.exists():
            row = v2.read(p)["receipt"]
            v1.require((row["schema"], row["freeze"], row["salt"], row["basis"], row["arm"],
                        row["rounds"], row["shard"], row["shots"]) ==
                       (SCHEMA, freeze, salt, b, arm, r, i, q["shots_per_shard"]), "mixed streams")
            n += row["shots"]
            bad += v1.num_failures(row)
    return n, bad


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", required=True, choices=["control","qualification"])
    p.add_argument("--basis", required=True, choices=["x","z"])
    p.add_argument("--arm", required=True, choices=["nominal","paired-readout"])
    p.add_argument("--rounds", type=int, default=1000)
    p.add_argument("--shards", type=int, nargs="+")
    p.add_argument("--kernel", required=True, type=Path)
    p.add_argument("--artifact-dir", required=True, type=Path)
    p.add_argument("--freeze")
    p.add_argument("--salt")
    p.add_argument("--git", default="git")
    a = p.parse_args()
    s, base, ref, proof, ksh = config(a.git, v1.sha(a.kernel.read_bytes()))
    fn = g.kernel(a.kernel)
    if a.mode == "control":
        name = f"B2_corner335_control_{a.basis}_{a.arm}.json"
        v1.require(not (a.artifact_dir/name).exists(), "control already exists")
        v2.atomic_save(a.artifact_dir/name, controls(s, base, proof, a.basis, a.arm, fn))
        print(f"{a.basis} {a.arm}: compact, monolithic and negative seam checks passed", flush=True)
        return
    q = base["qualification"]
    v1.require(a.freeze and a.salt and len(bytes.fromhex(a.salt)) == 32
               and a.salt != ref["salt"] and a.rounds in q["horizons"] and a.shards
               and len(set(a.shards)) == len(a.shards) and all(0 <= i < q["shards"] for i in a.shards),
               "invalid independent cohort")
    proof = freeze_check(s, q, a.freeze, a.git)
    cap = v1.planned_cap(q["prespecified_total_shots"], q["failure_target"])
    if a.rounds == 1_000_000:
        for b in q["bases"]:
            for arm in q["arms"]:
                n, bad = count(a.artifact_dir, a.freeze, a.salt, b, arm, 1000, q)
                v1.require(n == q["prespecified_total_shots"] and bad <= cap, "short gate not closed")
    c, n, m, geo, hashes = corner.model(a.basis, a.arm, a.rounds, base)
    stream = even.Stream(m, n, s["commit_periods"], s["guard_periods"])
    g.install(stream, fn)
    tick = [0]
    stream.windows = [(v2.Meter(g, tick, len(stream.windows)), guard) for g, guard in stream.windows]
    print(f"335 {a.basis} {a.arm} rounds={a.rounds}, {len(stream.windows)} windows", flush=True)
    for i in a.shards:
        out = a.artifact_dir / filename(a.basis, a.arm, a.rounds, i)
        v1.require(not out.exists(), "shot shard already exists")
        _, bad = count(a.artifact_dir, a.freeze, a.salt, a.basis, a.arm, a.rounds, q)
        if bad > cap:
            print(f"futility: not starting shard {i}", flush=True)
            return
        tick[0] = 0
        receipt, timing = stream.decode(q["shots_per_shard"], key(a.freeze, a.salt, a.basis, a.arm, a.rounds, i))
        v1.require(tick[0] == len(stream.windows), "incomplete trajectory")
        receipt |= {"schema": SCHEMA, "freeze": a.freeze, "salt": a.salt, "basis": a.basis,
                    "arm": a.arm, "rounds": a.rounds, "shard": i, "geometry": geo,
                    "num_detectors": c.num_detectors, "controls": proof, "kernel_sha256": ksh,
                    "reference_checkpoint_sha256": s["reference_checkpoint_sha256"], **hashes}
        v2.atomic_save(out, {"receipt": receipt, "timing": timing})
        print(f"shard {i}: {v1.num_failures(receipt)}/{q['shots_per_shard']} failures", flush=True)


if __name__ == "__main__":
    main()
