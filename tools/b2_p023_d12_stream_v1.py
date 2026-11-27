#!/usr/bin/env python3
"""An even-distance stream retaining both the unaligned guard and physical tail."""

from __future__ import annotations

from collections import Counter
import hashlib
import math
import time

import numpy as np
import stim

import p023_streamed_memory_v1 as v1


def nbytes(n: int) -> int:
    return (n + 7) // 8


def bounded_geometry(d: int, basis: str):
    c = stim.Circuit.generated(f"surface_code:rotated_memory_{basis}", rounds=8, distance=d)
    xy = c.get_final_qubit_coordinates()
    coords = c.get_detector_coordinates()
    by_time = Counter(int(x[2]) for x in coords.values())
    q = d * d - 1
    head = by_time[0]
    v1.require(set(by_time) == set(range(9)) and by_time[8] == head
               and all(by_time[t] == q for t in range(1, 8)), "unrecognized switch-on/off geometry")
    active = set()
    edges = set()
    for op in c.flattened():
        if op.name == "CX":
            targets = [t.value for t in op.targets_copy()]
            for a, b in zip(targets[::2], targets[1::2], strict=True):
                v1.require(tuple(abs(x-y) for x, y in zip(xy[a], xy[b], strict=True)) == (1, 1),
                           "nonlocal coupling")
                active.update((a, b))
                edges.add(tuple(sorted((a, b))))
    v1.require(active == set(xy) and len(active) == 2*d*d-1, "active ledger mismatch")
    return {"round0_detectors": head, "round8_detectors": by_time[8], "bulk_detectors": q,
            "active_qubits": len(active), "used_nearest_neighbor_couplings": len(edges),
            "ticks_per_round": c.num_ticks // 8,
            "all_cx_local": True}, c, coords


def generate(d: int, b: str, rounds: int, noise: dict) -> tuple[stim.Circuit, v1.Fold, dict]:
    geo, _, _ = bounded_geometry(d, b)
    c = stim.Circuit.generated(f"surface_code:rotated_memory_{b}", rounds=rounds, distance=d, **noise)
    dem = c.detector_error_model(decompose_errors=True)
    i, = [i for i, x in enumerate(dem) if isinstance(x, stim.DemRepeatBlock)]
    a, block, z = dem[:i], dem[i], dem[i+1:]
    body = block.body_copy()
    p = v1.shift(body)
    q = geo["bulk_detectors"]
    expected = (rounds - 1)*q + 2*geo["round0_detectors"]
    v1.require(v1.shift(a) == 0 and p == 2*q and block.repeat_count == rounds//2-2,
               "unexpected folding stride or length")
    v1.require(a + body * block.repeat_count + z == dem and
               dem.num_detectors == c.num_detectors == expected, "fault coverage")
    v1.require(c.num_ticks == rounds * geo["ticks_per_round"] and
               c.num_measurements == rounds*q + d*d and
               c.num_observables == dem.num_observables == 1, "not an entire memory trajectory")
    return c, v1.Fold(a, body, z, block.repeat_count, p, dem), geo


def paired_readout(f: v1.Fold, geo: dict, p: float) -> v1.Fold:
    q = geo["bulk_detectors"]
    start = geo["round0_detectors"] + q  # Bulk detector layer t=2.
    st = stim.DetectorErrorModel()
    det = stim.DemTarget.relative_detector_id
    for j in range(q):
        st.append("error", p, [det(start+j), det(start+j+2*q)])
    body = st + f.body
    model = f.head + body * f.count + f.tail
    v1.require(model.num_detectors == f.model.num_detectors
               and model.num_errors == f.model.num_errors + q*f.count, "wrong burst model")
    return v1.Fold(f.head, body, f.tail, f.count, f.step, model)


def partition(f: v1.Fold, chunk_periods: int) -> list[v1.Chunk]:
    count, remainder = divmod(f.count, chunk_periods)
    span = f.step * chunk_periods
    v1.require(count >= 3 and span % 8 == 0, "internal cuts must be byte-aligned")
    block = f.body * chunk_periods
    final = f.body * remainder + f.tail
    last = f.model.num_detectors - count*span
    pieces = [v1.Chunk("head", span, f.head + block)]
    pieces += [v1.Chunk("bulk", span, block)] * (count - 1)
    pieces.append(v1.Chunk("tail", last, final))
    v1.require(final.num_detectors == last and sum(x.core for x in pieces) == f.model.num_detectors
               and sum(x.model.num_errors for x in pieces) == f.model.num_errors, "fault layout lost coverage")
    v1.require(all(x.core <= x.model.num_detectors <= x.core + y.core
                   for x, y in zip(pieces[:-1], pieces[1:], strict=True)),
               "fault spans more than two blocks")
    return pieces


class Stream:
    """Use the original matching-graph rule with exactly 30 rounds of look-ahead."""

    def __init__(self, sampling: v1.Fold, nominal: v1.Fold, chunk_periods: int,
                 guard_periods: int, verify: bool = False):
        self.sampling = sampling
        self.verify = verify
        self.parts = partition(sampling, chunk_periods)
        layout = partition(nominal, chunk_periods)
        v1.require([c.core for c in self.parts] == [c.core for c in layout], "different layouts")
        self.windows = []
        cache = {}
        for i, cur in enumerate(layout):
            p = layout[i-1] if i else None
            n = layout[i+1] if i+1 < len(layout) else None
            key = (p.kind if p else None, cur.kind, n.kind if n else None)
            if key not in cache:
                cache[key] = v1.window_graph(p, cur, n, guard_periods*nominal.step, verify)
            self.windows.append(cache[key])
        self.graph_types = len(cache)
        self.max_graph_detectors = max(m.num_detectors for m, _ in cache.values())

    def decode(self, shots, seed, *, drop_physical_spill=False,
               drop_correction_spill=False, truncate_terminal_byte=False):
        samplers = {}
        physical = np.zeros(shots, np.uint8)
        frame = np.zeros_like(physical)
        latencies = []
        t = {"sample_ns": 0, "decode_ns": 0}
        h = hashlib.sha256()
        if self.verify:
            total_bytes = nbytes(self.sampling.model.num_detectors)
            whole_raw = np.zeros((shots, total_bytes), np.uint8)
            faults = []
            offsets = np.cumsum([0] + [nbytes(c.core) for c in self.parts])
            expected_carry = np.zeros((shots, 0), np.uint8)
            v1.require(offsets[-1] == total_bytes, "packed tail was lost")

        def sample(i):
            part = self.parts[i]
            if part.kind not in samplers:
                samplers[part.kind] = part.model.compile_sampler(seed=v1.seed_for(seed, part.kind))
            start = time.perf_counter_ns()
            y, o, e = samplers[part.kind].sample(shots, bit_packed=True, return_errors=self.verify)
            t["sample_ns"] += time.perf_counter_ns()-start
            physical[:] ^= o[:, 0]
            h.update(y.tobytes())
            h.update(o.tobytes())
            if self.verify:
                whole_raw[:, offsets[i]:offsets[i]+y.shape[1]] ^= y
                faults.append(np.unpackbits(e, axis=1, count=part.model.num_errors, bitorder="little"))
            return y

        active = sample(0)
        phys_cuts = corr_cuts = 0
        for i, (part, (m, guard)) in enumerate(zip(self.parts, self.windows, strict=True)):
            c, g, bit = nbytes(part.core), nbytes(guard), guard % 8
            nxt = sample(i+1) if i+1 < len(self.parts) else None
            start = time.perf_counter_ns()
            if nxt is not None:
                spill = active[:, c:]
                phys_cuts += bool(np.any(spill))
                if not drop_physical_spill:
                    nxt[:, :spill.shape[1]] ^= spill
                syn = np.concatenate((active[:, :c], nxt[:, :g]), axis=1)
                if bit:
                    syn[:, -1] &= (1 << bit)-1
            else:
                syn = active[:, :c-1] if truncate_terminal_byte and part.core % 8 else active[:, :c]
                v1.require(syn.shape[1] == c, "terminal detector byte was truncated")
            if self.verify:
                expected = whole_raw[:, offsets[i]:offsets[i+1]].copy()
                expected[:, :expected_carry.shape[1]] ^= expected_carry
                v1.require(np.array_equal(expected, syn[:, :c]), "trajectory stitch dropped parity")
            out = m.decode_batch(syn, bit_packed_shots=True, bit_packed_predictions=True)
            frame ^= (out[:, guard//8] >> bit) & 1
            carry = out[:, :g].copy()
            if bit:
                carry[:, -1] &= (1 << bit)-1
            if self.verify:
                checked = np.unpackbits(out, axis=1, bitorder="little")[:, guard+8:guard+8+part.core]
                v1.require(np.array_equal(np.packbits(checked, axis=1, bitorder="little"),
                                          syn[:, :c]), "committed correction parity differs")
                expected_carry = carry
                h.update(out.tobytes())
            if nxt is not None:
                corr_cuts += bool(np.any(carry))
                if not drop_correction_spill:
                    nxt[:, :g] ^= carry
            ns = time.perf_counter_ns()-start
            latencies.append(ns)
            t["decode_ns"] += ns
            active = nxt
        record = {"shots": shots, "seed": seed, "windows": len(self.parts),
                  "max_graph_detectors": self.max_graph_detectors, "graph_types": self.graph_types,
                  "sample_sha256": h.hexdigest(),
                  "physical_nonzero_cut_batches": phys_cuts, "correction_nonzero_cut_batches": corr_cuts}
        for name, data in (("truth", physical), ("correction", frame), ("failures", physical ^ frame)):
            record[name+"_le_hex"] = np.packbits(data, bitorder="little").tobytes().hex()
        if self.verify:
            bits = np.packbits(np.concatenate(faults, axis=1), axis=1, bitorder="little")
            raw, obs, _ = self.sampling.model.compile_sampler().sample(
                shots, bit_packed=True, recorded_errors_to_replay=bits)
            v1.require(np.array_equal(whole_raw, raw) and np.array_equal(physical, obs[:, 0]),
                       "chunks differ from whole DEM")
            record["monolithic_sample_sha256"] = v1.sha(raw.tobytes()+obs.tobytes())
        t["batch_window_p99_ns"] = sorted(latencies)[math.ceil(.99*len(latencies))-1]
        t["max_window_ns"] = max(latencies)
        return record, t
