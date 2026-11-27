#!/usr/bin/env python3
"""Compile the X-protected corner circuit as one continuous finite-history loop."""

from collections import Counter

import stim

import b2_corner_shortening_preflight_v1 as pre
import b2_p023_d12_stream_v1 as even
import p023_streamed_memory_v1 as v1


def sites(basis):
    c = stim.Circuit.generated(f"surface_code:rotated_memory_{basis}", distance=13, rounds=4).flattened()
    coords, data, _, zs, _ = pre.geometry(c)
    corner, = (q for q in data if coords[q] == [25.0, 25.0])
    check, = (i for i, s in zs.items() if corner in s)
    v1.require(coords[check] == [24.0, 24.0], "not the structurally checked X-protected corner")
    return corner, check


def previous_lookback(block):
    """How many source measurement positions can a block address before it begins?"""
    meas = need = 0
    for op in block:
        if op.name in pre.MEASURE:
            meas += len(op.targets_copy())
        elif op.name in ("DETECTOR", "OBSERVABLE_INCLUDE"):
            for t in op.targets_copy():
                v1.require(t.is_measurement_record_target and t.value < 0, "unexpected record target")
                need = max(need, -t.value-meas)
    return need


class Projector:
    def __init__(self, corner, check):
        self.dropped = {corner, check}
        self.check = check
        self.records = []
        self.kept = 0

    def signature(self, depth):
        v1.require(depth <= len(self.records), "prefix cannot supply the required record history")
        return tuple((q, None if idx is None else idx-self.kept)
                     for q, idx in self.records[len(self.records)-depth:])

    def block(self, source):
        out = stim.Circuit()
        for op in source:
            name, targets, args = op.name, op.targets_copy(), op.gate_args_copy()
            if name in ("DETECTOR", "OBSERVABLE_INCLUDE"):
                v1.require(all(t.is_measurement_record_target and -len(self.records) <= t.value < 0
                               for t in targets), "invalid record address")
                refs = [self.records[t.value] for t in targets]
                if name == "OBSERVABLE_INCLUDE":
                    v1.require(all(i is not None for _, i in refs), "corner changed the logical readout")
                if any(q == self.check for q, _ in refs):
                    continue
                kept = [stim.target_rec(i-self.kept) for _, i in refs if i is not None]
                v1.require(bool(kept), "empty surviving detector")
                out.append(name, kept, args)
            elif name in ("TICK", "SHIFT_COORDS"):
                out.append(op)
            elif name in pre.PAIR:
                left = [t for pair in zip(targets[::2], targets[1::2], strict=True)
                        if all(t.value not in self.dropped for t in pair) for t in pair]
                if left:
                    out.append(name, left, args)
            else:
                v1.require(name in pre.SINGLE and all(t.is_qubit_target for t in targets),
                           f"unreviewed circuit operation: {name}")
                if name in pre.MEASURE:
                    for t in targets:
                        good = t.value not in self.dropped
                        self.records.append((t.value, self.kept if good else None))
                        self.kept += good
                left = [t for t in targets if t.value not in self.dropped]
                if left:
                    out.append(name, left, args)
        return out


def circuit(basis, rounds, noise):
    source = stim.Circuit.generated(f"surface_code:rotated_memory_{basis}", distance=13,
                                    rounds=rounds, **noise)
    i, = [j for j, x in enumerate(source) if isinstance(x, stim.CircuitRepeatBlock)]
    initial, loop, closing = source[:i], source[i], source[i+1:]
    body = loop.body_copy()
    v1.require(loop.repeat_count == rounds-1, "unexpected source schedule")
    # Only this inherited history can influence a rewrite of either block.
    need = max(previous_lookback(body), previous_lookback(closing))
    projector = Projector(*sites(basis))
    open_ = projector.block(initial)
    before = projector.signature(need)
    projected_body = projector.block(body)
    v1.require(projector.signature(need) == before, "record history is not a loop invariant")
    v1.require(projector.block(body) == projected_body and projector.signature(need) == before,
               "second period not identical to the first")
    tail = projector.block(closing)
    c = open_ + projected_body * loop.repeat_count + tail
    v1.require(c.num_measurements == rounds*167 + 168 and c.num_ticks == 7*rounds
               and c.num_observables == 1, "changed physical code volume or horizon")
    return c, need


def model(basis, arm, rounds, base):
    c, needed = circuit(basis, rounds, base["noise"])
    m = 84 if basis == "x" else 83
    q = 167
    geo = {"round0_detectors": m, "bulk_detectors": q, "active_qubits": 335,
           "history_dependency_measurements": needed, "ticks_per_round": 7}
    dem = c.detector_error_model(decompose_errors=True)
    i, = [j for j, x in enumerate(dem) if isinstance(x, stim.DemRepeatBlock)]
    a, loop, z = dem[:i], dem[i], dem[i+1:]
    body = loop.body_copy()
    period = v1.shift(body)
    v1.require(v1.shift(a) == 0 and period == 2*q and loop.repeat_count == rounds//2-2
               and a + body * loop.repeat_count + z == dem, "not the reference's paired-readout clock")
    v1.require(dem.num_detectors == c.num_detectors == (rounds-1)*q + 2*m
               and dem.num_observables == 1, "wrong circuit or DEM boundary")
    nominal = v1.Fold(a, body, z, loop.repeat_count, period, dem)
    sampling = (even.paired_readout(nominal, geo, base["burst_probability"])
                if arm == "paired-readout" else nominal)
    keys = {"circuit_sha256": v1.sha(str(c).encode()), "decoder_dem_sha256": v1.sha(str(dem).encode()),
            "sampling_dem_sha256": v1.sha(str(sampling.model).encode())}
    return c, nominal, sampling, geo, keys


def confirm_phases(basis):
    # This compares all 167 detector coordinate lines against the declared
    # stress shape, then confirms three representative matches physically.
    c, _ = circuit(basis, 15, {})
    coord = c.get_detector_coordinates()
    n = Counter(int(x[2]) for x in coord.values())
    m = 84 if basis == "x" else 83
    q = 167
    v1.require(n[0] == n[15] == m and all(n[t] == q for t in range(1, 15)),
               "unstable detector phase sizes")
    first = m+q
    xy = c.get_final_qubit_coordinates()
    for j in range(q):
        a, b, z = (coord[first+j+s*q] for s in range(3))
        v1.require(a[:2] == b[:2] == z[:2] and (a[2], b[2], z[2]) == (2, 3, 4),
                   "wrong paired-readout alignment")
    for j in (0, q//2, q-1):
        physical, = [k for k, loc in xy.items() if loc == coord[first+j][:2]]
        det_circuit = stim.Circuit()
        t = 0
        for op in c.flattened():
            if op.name == "MR":
                if t in (2, 3):
                    v1.require(physical in [x.value for x in op.targets_copy()], "wrong ancilla phase")
                    det_circuit.append("X_ERROR", [physical], 1)
                t += 1
            det_circuit.append(op)
        d, l = det_circuit.compile_detector_sampler(seed=141).sample(1, separate_observables=True)
        actual = d[0].nonzero()[0].tolist()
        v1.require(actual == [first+j, first+2*q+j] and not l[0, 0], "wrong stress witness")
    return {"bulk_coordinate_lines": q, "physical_pair_witnesses": 3}
