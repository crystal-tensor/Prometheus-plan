#!/usr/bin/env python3
"""Replay selected frozen trajectories three ways without resampling their faults."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import subprocess

import numpy as np
import stim

import b2_p023_d12_gate_v1 as b2
import b2_p023_d12_stream_v1 as even
import p023_grouped_sampler_v1 as g
import p023_streamed_memory_grouped_v2 as v2
import p023_streamed_memory_v1 as v1


PROTOCOL = v1.ROOT / "benchmarks/P023_B2_stress_counterfactual_v1.json"
ARM = "paired-readout"
BRANCH = ("observed_nominal_decoder", "same_faults_without_pairs", "observed_pair_aware_decoder")


def paired_mask(nominal_chunk, stress_chunk, nominal, stressed, d, probability):
    v1.require(nominal_chunk.kind == stress_chunk.kind, "chunk type diverges")
    q = d*d-1
    v1.require(stressed.body[q:] == nominal.body and nominal.head == stressed.head
               and nominal.tail == stressed.tail, "background models differ")
    starts = []
    for op in stressed.body[:q]:
        p, = op.args_copy()
        ts = op.targets_copy()
        v1.require(op.type == "error" and p == probability and len(ts) == 2
                   and all(t.is_relative_detector_id() for t in ts)
                   and ts[1].val-ts[0].val == 2*q, "not a paired readout mechanism")
        starts.append(ts[0].val)
    v1.require(starts == list(range(starts[0], starts[0]+q)), "pair sites not all covered")
    pre = nominal.head.num_errors if stress_chunk.kind == "head" else 0
    post = nominal.tail.num_errors if stress_chunk.kind == "tail" else 0
    periods, remainder = divmod(stress_chunk.model.num_errors-pre-post, stressed.body.num_errors)
    v1.require(remainder == 0 and nominal_chunk.model.num_errors ==
               pre+periods*nominal.body.num_errors+post, "error indexes do not align")
    mask = np.zeros(stress_chunk.model.num_errors, dtype=bool)
    for i in range(periods):
        offset = pre+i*stressed.body.num_errors
        mask[offset:offset+q] = True
    v1.require(mask.sum() == stress_chunk.model.num_errors-nominal_chunk.model.num_errors,
               "removed more than the added noise")
    return mask


class Project:
    def __init__(self, prepared, fn, original_size, indices, seed, removed):
        self.layout, self.fn, self.original_size = prepared["layout"], fn, original_size
        self.groups = prepared["groups"]
        self.indices = indices
        self.columns = np.asarray([i//8 for i in indices], np.intp)
        self.shifts = np.asarray([i%8 for i in indices], np.uint8)
        self.rng = stim.FlipSimulator(batch_size=1, seed=seed)
        self.removed = removed

    def sample(self, shots, *, bit_packed=True, return_errors=False):
        k = len(self.indices)
        v1.require(shots == 3*k and bit_packed and not return_errors, "invalid projection mode")
        m = self.layout
        det = np.zeros((shots, m.width), np.uint8)
        obs = np.zeros((shots, 1), np.uint8)
        for p, ids, drop in self.groups:
            bits = self.rng.generate_bernoulli_samples(len(ids)*self.original_size, p=p, bit_packed=True)
            sel = (bits.reshape(len(ids), self.original_size//8)[:, self.columns] >> self.shifts) & 1
            without = sel.copy()
            if np.any(drop):
                self.removed[:] += sel[drop].sum(axis=0, dtype=np.int64)
                without[drop] = 0
            combined = np.packbits(np.concatenate((sel, without, sel), axis=1), bitorder="little")
            self.fn(combined, len(ids)*shots, shots, ids, m.offsets, m.targets, det, m.width, obs)
        return det, obs, None


class Segment:
    def __init__(self, model, mask, fn, size, indices, removed):
        self.model, self.mask, self.fn = model, mask, fn
        self.size, self.indices, self.removed = size, indices, removed
        self.prepared = None

    def compile_sampler(self, *, seed):
        if self.prepared is None:
            v = g.Mechanisms(self.model)
            self.prepared = {"layout": v, "groups": [(p, ids, self.mask[ids]) for p, ids in v.groups]}
        return Project(self.prepared, self.fn, self.size, self.indices, seed, self.removed)


class Match:
    def __init__(self, old, aware, guard, k, timeline):
        self.old, self.aware, self.guard, self.k, self.timeline = old, aware, guard, k, timeline

    def decode_batch(self, syndromes, **kw):
        k, guard = self.k, self.guard
        a = self.old.decode_batch(syndromes[:2*k], **kw)
        b = self.aware.decode_batch(syndromes[2*k:], **kw)
        joined = np.concatenate((a, b), axis=0)
        values = (joined[:, guard//8] >> (guard % 8)) & 1
        self.timeline.append(values.copy())
        if len(self.timeline) % 2048 == 0:
            print(f"replayed windows: {len(self.timeline)}", flush=True)
        return joined


def expected_bits(record, kind, indices):
    raw = bytes.fromhex(record[kind+"_le_hex"])
    v1.require(len(raw)*8 == record["shots"], "expected receipt has different packed width")
    return np.unpackbits(np.frombuffer(raw, np.uint8), bitorder="little")[indices]


def get_models(d, basis, rounds, p, base):
    if d == 12:
        c, nominal, stress, _, _ = b2.model(d, basis, ARM, rounds, base)
        parts = even.partition
        stream = lambda a, b: even.Stream(a, b, p["commit_periods"], p["guard_periods"])
    else:
        c, nominal = v1.fold(d, basis, rounds, base["noise"])
        stress = v1.stressed(nominal, d, base["burst_probability"])
        parts = v1.partition
        stream = lambda a, b: v1.Stream(a, b, p["commit_periods"], p["guard_periods"])
    a, b = (parts(x, p["commit_periods"]) for x in (nominal, stress))
    v1.require(len(a) == len(b), "more chunks after adding the stress")
    masks = {}
    for part0, part1 in zip(a, b, strict=True):
        if part1.kind not in masks:
            masks[part1.kind] = paired_mask(part0, part1, nominal, stress, d, base["burst_probability"])
    return c, nominal, stress, b, masks, stream


def exact_control(d, basis, p, base, fn):
    _, _, _, parts, masks, _ = get_models(d, basis, 1000, p, base)
    indices = [0, 63, 64, 127]
    tested = {}
    for part in parts:
        if part.kind in tested:
            continue
        removed = np.zeros(len(indices), np.int64)
        mask = masks[part.kind]
        seed = v1.seed_for("counterfactual-selection-unit-test", d, basis, part.kind)
        seg = Segment(part.model, mask, fn, 128, indices, removed)
        selector = seg.compile_sampler(seed=seed)
        whole = g.Sampler(seg.prepared["layout"], fn, seed)
        for _ in range(2):
            det, truth, flags = whole.sample(128, bit_packed=True, return_errors=True)
            masked = np.unpackbits(flags[indices], axis=1, count=part.model.num_errors, bitorder="little")
            masked[:, mask] = 0
            oracle, truth2, _ = part.model.compile_sampler(seed=0).sample(
                len(indices), bit_packed=True,
                recorded_errors_to_replay=np.packbits(masked, axis=1, bitorder="little"))
            x, y, _ = selector.sample(3*len(indices))
            v1.require(np.array_equal(x[:4], det[indices]) and np.array_equal(x[4:8], oracle)
                       and np.array_equal(x[8:], det[indices]) and
                       np.array_equal(y, np.concatenate((truth[indices], truth2, truth[indices]))),
                       "selective projection does not equal the ordinary sampler or Stim replay")
        tested[part.kind] = {"calls": 2, "selected_original_positions": indices,
                             "removed_events": removed.tolist()}
    return tested


def run_case(p, spec, directory, kernel, git):
    path = directory/spec["file"]
    original = path.read_bytes()
    v1.require(v1.sha(original) == spec["sha256"], "source is not the predeclared receipt")
    src = json.loads(original)["receipt"]
    d, b, shard = (spec[k] for k in ("distance", "basis", "shard"))
    r, n = p["rounds"], src["shots"]
    v1.require((src["distance"], src["basis"], src["arm"], src["shard"], src["rounds"], n) ==
               (d, b, ARM, shard, r, 128), "wrong cohort record")
    ksha = v1.sha(kernel.read_bytes())
    v1.require(ksha == src["kernel_sha256"], "different native kernel")
    if d == 12:
        bspec, base, _, _ = b2.setup(git, ksha)
        b2.freeze_check(src["freeze"], git, bspec, base)
        seed = b2.shard_seed(src["freeze"], src["salt"], b, ARM, r, shard)
    else:
        base, _, _, _ = v2.config(src["freeze"], git, ksha)
        seed = v2.planned_seed(src["freeze"], src["salt"], b, ARM, r, shard)
    v1.require(seed == src["seed"], "not the original salted stream")
    c, orig, stress, parts, masks, make_stream = get_models(d, b, r, p, base)
    v1.require(v1.sha(str(c).encode()) == src["circuit_sha256"] and
               v1.sha(str(orig.model).encode()) == src["decoder_dem_sha256"] and
               v1.sha(str(stress.model).encode()) == src["sampling_dem_sha256"], "wrong model identity")
    flags = expected_bits(src, "failures", list(range(n)))
    failed = np.flatnonzero(flags).tolist()
    v1.require(len(failed) == spec["source_failures"], "source failure count diverges")
    chosen = failed + [int(np.flatnonzero(flags == 0)[0])]
    k = len(chosen)
    fn = g.kernel(kernel)
    controls = exact_control(d, b, p, base, fn)
    print(f"d{d} {b}: exact sampler/replay controls passed, replaying {k} frozen shots", flush=True)
    primary, aware = make_stream(stress, orig), make_stream(stress, stress)
    v1.require(len(primary.windows) == len(aware.windows) == src["windows"], "different window count")
    timeline = []
    both = []
    for (m, guard), (plus, guard2) in zip(primary.windows, aware.windows, strict=True):
        v1.require(guard == guard2 and m.num_detectors == plus.num_detectors
                   and m.num_fault_ids == plus.num_fault_ids, "aware graph changed window interface")
        both.append((Match(m, plus, guard, k, timeline), guard))
    primary.windows = both
    removed = np.zeros(k, np.int64)
    bank = {}
    for part in parts:
        if part.kind not in bank:
            bank[part.kind] = Segment(part.model, masks[part.kind], fn, n, chosen, removed)
    primary.parts = [replace(part, model=bank[part.kind]) for part in parts]
    observed, times = primary.decode(3*k, seed)
    trace = np.asarray(timeline, np.uint8)
    v1.require(len(timeline) == src["windows"] and min(removed) > 0, "full intervention not exercised")

    def values(key):
        raw = bytes.fromhex(observed[key+"_le_hex"])
        return np.unpackbits(np.frombuffer(raw, np.uint8), bitorder="little",
                             count=3*k).reshape(3, k)

    truth, corr, newfail = map(values, ("truth", "correction", "failures"))
    for tag, vector in (("truth", truth), ("correction", corr), ("failures", newfail)):
        v1.require(np.array_equal(vector[0], expected_bits(src, tag, chosen)),
                   f"factual {tag} differs from original")
    v1.require(np.all(truth == truth[0]) and np.array_equal(truth ^ corr, newfail)
               and np.array_equal(np.bitwise_xor.reduce(trace, axis=0), corr.flatten()),
               "the three logical frames do not reconcile")
    per_shot = []
    for j, shot in enumerate(chosen):
        lines = {}
        for lane, tag in enumerate(BRANCH):
            diff = np.flatnonzero(trace[:, k*lane+j] != trace[:, j])
            lines[tag] = {"truth": int(truth[lane, j]), "correction": int(corr[lane, j]),
                          "failed": bool(newfail[lane, j]), "changed_commit_windows": len(diff),
                          "first_changed_window_zero_based": int(diff[0]) if len(diff) else None}
        per_shot.append({"source_shot_zero_based": shot, "original_failure": bool(flags[shot]),
                         "paired_faults_removed": int(removed[j]), "branches": lines})
    return {"selection": spec, "kernel_sha256": ksha, "rounds": r, "original_shard_seed": seed,
            "factual_replay_validated": True, "qualification_credit": False,
            "unit_controls": controls, "traces": per_shot,
            "window_commits_sha256": v1.sha(trace.tobytes()), "timings": times}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case", required=True)
    ap.add_argument("--source-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--kernel", type=Path, required=True)
    ap.add_argument("--freeze", required=True)
    ap.add_argument("--git", default="git")
    a = ap.parse_args()
    source = Path(__file__).resolve()
    for path in (PROTOCOL, source):
        frozen = subprocess.check_output([a.git, "show", f"{a.freeze}:{path.relative_to(v1.ROOT)}"],
                                         cwd=v1.ROOT)
        v1.require(frozen == path.read_bytes(), "not running the frozen diagnostic")
    v1.require(not a.out.exists(), "diagnostic already exists")
    p = v2.read(PROTOCOL)
    answer = run_case(p, p["cases"][a.case], a.source_dir, a.kernel, a.git)
    answer |= {"schema": p["schema"], "experiment_freeze": a.freeze,
               "protocol_sha256": v1.sha(PROTOCOL.read_bytes())}
    v2.atomic_save(a.out, answer)
    print(json.dumps([r["branches"] for r in answer["traces"]]), flush=True)


if __name__ == "__main__":
    main()
