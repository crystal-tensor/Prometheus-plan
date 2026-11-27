#!/usr/bin/env python3
"""Structural preflight for two 335-qubit corner shortenings; no logical shots."""

import argparse
import hashlib
import json
from pathlib import Path

import stim


NOISE = dict(after_clifford_depolarization=.001, before_round_data_depolarization=.001,
             before_measure_flip_probability=.001, after_reset_flip_probability=.001)
MEASURE = {"MR", "M", "MX"}
PAIR = {"CX", "DEPOLARIZE2"}
SINGLE = {"QUBIT_COORDS", "R", "RX", "H", "DEPOLARIZE1", "X_ERROR", "Z_ERROR"} | MEASURE


def check(ok, label):
    if not ok:
        raise AssertionError(label)


def geometry(c):
    labels = c.get_final_qubit_coordinates()
    final = [x for x in c if x.name in MEASURE][-1]
    data = {t.value for t in final.targets_copy()}
    x_checks, z_checks, couplings = {}, {}, set()
    for op in c:
        if op.name != "CX":
            continue
        targets = [x.value for x in op.targets_copy()]
        for u, v in zip(targets[::2], targets[1::2], strict=True):
            check((u in data) != (v in data), "not a CSS ancilla/data pair")
            check(tuple(abs(a-b) for a, b in zip(labels[u], labels[v], strict=True)) == (1, 1),
                  "nonlocal coupling")
            couplings.add((u, v))
            if u in data:
                z_checks.setdefault(v, set()).add(u)
            else:
                x_checks.setdefault(u, set()).add(v)
    check(not (set(x_checks) & set(z_checks)) and
          data | set(x_checks) | set(z_checks) == set(labels), "physical ledger mismatch")
    return labels, data, x_checks, z_checks, couplings


def rank(rows):
    pivots = {}
    for values in rows:
        b = sum(1 << x for x in values)
        while b:
            p = b.bit_length()
            if p not in pivots:
                pivots[p] = b
                break
            b ^= pivots[p]
    return len(pivots)


def css(c):
    labels, data, x, z, _ = geometry(c)
    check(not any(len(s & t) % 2 for s in x.values() for t in z.values()), "checks anticommute")
    rx, rz = rank(x.values()), rank(z.values())
    check(rx == len(x) and rz == len(z) and len(data) == rx + rz + 1,
          "does not encode exactly one logical qubit with independent checks")
    return {"active_qubits": len(labels), "data": len(data), "x_checks": rx, "z_checks": rz}


def project(c, dropped_data, dropped_check):
    dropped = {dropped_data, dropped_check}
    out = stim.Circuit()
    records = []
    next_rec = 0
    for op in c:
        name = op.name
        t = op.targets_copy()
        args = op.gate_args_copy()
        if name in ("DETECTOR", "OBSERVABLE_INCLUDE"):
            check(all(x.is_measurement_record_target and x.value < 0 for x in t), "unexpected record syntax")
            sites = [records[x.value] for x in t]
            removed_check = any(q == dropped_check for q, _ in sites)
            check(name != "OBSERVABLE_INCLUDE" or all(idx is not None for _, idx in sites),
                  "chosen corner intersects the fixed logical observable")
            if removed_check:
                continue
            new = [stim.target_rec(idx-next_rec) for _, idx in sites if idx is not None]
            check(new, "empty surviving parity check")
            out.append(name, new, args)
        elif name in ("TICK", "SHIFT_COORDS"):
            out.append(op)
        elif name in PAIR:
            new = [x for pair in zip(t[::2], t[1::2], strict=True)
                   if all(x.value not in dropped for x in pair) for x in pair]
            if new:
                out.append(name, new, args)
        else:
            check(name in SINGLE and all(x.is_qubit_target for x in t), f"unreviewed instruction: {name}")
            if name in MEASURE:
                for x in t:
                    use = x.value not in dropped
                    records.append((x.value, next_rec if use else None))
                    next_rec += use
            new = [x for x in t if x.value not in dropped]
            if new:
                out.append(name, new, args)
    return out


def witness(c):
    e = c.shortest_graphlike_error(ignore_ungraphlike_errors=True)
    terms = set()
    for fault in e:
        for term in fault.dem_error_terms:
            t = term.dem_target
            k = ("det" if t.is_relative_detector_id() else "log", t.val)
            terms.symmetric_difference_update({k})
    check(terms == {("log", 0)}, "shortest witness has a residual detector or no logical flip")
    return len(e)


def timed_cx(c):
    tick = 0
    events = []
    for op in c:
        if op.name == "TICK":
            tick += 1
        elif op.name == "CX":
            t = [x.value for x in op.targets_copy()]
            events.extend((tick, u, v) for u, v in zip(t[::2], t[1::2], strict=True))
    return events


def result(rounds):
    arms = {}
    for basis in ("x", "z"):
        c13 = stim.Circuit.generated(f"surface_code:rotated_memory_{basis}", distance=13, rounds=rounds,
                                      **NOISE).flattened()
        c12 = stim.Circuit.generated(f"surface_code:rotated_memory_{basis}", distance=12, rounds=rounds,
                                      **NOISE).flattened()
        coords, data, xs, zs, original_cx = geometry(c13)
        corner = max(data, key=lambda q: tuple(coords[q]))
        xd, = [q for q, support in xs.items() if corner in support]
        zd, = [q for q, support in zs.items() if corner in support]
        arms[basis] = {"d12": css(c12) | {"graphlike_fault_length": witness(c12)},
                       "d13": css(c13) | {"graphlike_fault_length": witness(c13)}}
        for axis, check_id in (("fix_corner_x", zd), ("fix_corner_z", xd)):
            c = project(c13, corner, check_id)
            q, remain, rx, rz, edges = geometry(c)
            check(edges == {a for a in original_cx if corner not in a and check_id not in a}
                  and timed_cx(c) == [(s, u, v) for s, u, v in timed_cx(c13)
                                       if {corner, check_id}.isdisjoint((u, v))],
                  "a surviving coupling changed tick or order")
            expected_x = {i: s-{corner} for i, s in xs.items() if i != check_id}
            expected_z = {i: s-{corner} for i, s in zs.items() if i != check_id}
            check(rx == expected_x and rz == expected_z and remain == data-{corner},
                  "not the intended shortening")
            check(c.num_ticks == c13.num_ticks == 7*rounds and c.num_observables == 1 and len(q) == 335,
                  "space or timing did not match")
            model = c.detector_error_model(decompose_errors=True)
            check(model.num_detectors == c.num_detectors and model.num_observables == 1,
                  "unreplayable shortened detector model")
            arms[basis][axis] = css(c) | {"graphlike_fault_length": witness(c),
                "removed_data_coordinates": coords[corner], "removed_check_coordinates": coords[check_id],
                "ticks": c.num_ticks, "detectors": c.num_detectors, "retained_cx_tick_trace_exact": True,
                "circuit_sha256": hashlib.sha256(str(c).encode()).hexdigest(),
                "dem_sha256": hashlib.sha256(str(model).encode()).hexdigest()}
    return {"schema": "b2_corner_shortening_preflight_v1", "rounds_for_witness": rounds,
            "logical_shots": 0, "arms": arms, "acceptance_credit": False,
            "interpretation": "Shortest graphlike mechanisms only; not a noise-rate or horizon gate."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--rounds", type=int, default=15)
    a = p.parse_args()
    check(not a.out.exists() and 13 <= a.rounds <= 32, "wrong preflight geometry")
    with a.out.open("x") as f:
        value = result(a.rounds)
        json.dump(value, f, sort_keys=True, indent=2)
        f.write("\n")
    print(json.dumps({b: {k: a["graphlike_fault_length"] for k, a in rows.items()}
                      for b, rows in value["arms"].items()}), flush=True)


if __name__ == "__main__":
    main()
