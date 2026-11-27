#!/usr/bin/env python3
"""Replay exact fault flags; challenge both temporal carries and burst geometry."""

import argparse
import json
from pathlib import Path

import numpy as np
import stim

import p023_streamed_memory_v1 as s


def check_burst_geometry(d: int, basis: str, f: s.Fold) -> dict:
    c = stim.Circuit.generated(f"surface_code:rotated_memory_{basis}", distance=d, rounds=8)
    coords = c.get_detector_coordinates()
    qcoords = c.get_final_qubit_coordinates()
    q = d*d - 1
    first = 3*q//2
    n = 0
    for j in range(q):
        a, b, z = (coords[first + j + k*q] for k in range(3))
        s.require(a[:2] == b[:2] == z[:2] and (a[2], b[2], z[2]) == (2, 3, 4),
                  "burst detector labels not on same two-round trajectory")
    for j in (0, q//2, q-1):
        coord = coords[first+j][:2]
        check_qubit, = (k for k, v in qcoords.items() if v == coord)
        actual = stim.Circuit()
        mr = 0
        for op in c.flattened():
            if op.name == "MR":
                if mr in (2, 3):
                    s.require(check_qubit in [t.value for t in op.targets_copy()],
                              "burst check qubit not measured")
                    actual.append("X_ERROR", [check_qubit], 1.0)
                mr += 1
            actual.append(op)
        ds, obs = actual.compile_detector_sampler(seed=234).sample(1, separate_observables=True)
        s.require(np.flatnonzero(ds[0]).tolist() == [first+j, first+2*q+j]
                  and not bool(obs[0, 0]), "injected circuit burst has different symptoms")
        n += 1
    s.require(f.step == 2*q, "wrong bulk temporal step for bursts")
    return {"coordinate_lines_checked": q, "deterministic_circuit_bursts_checked": n}


def verify(a: argparse.Namespace, p: dict) -> dict:
    c, f = s.fold(a.distance, a.basis, p["control_rounds"], p["noise"])
    physical_checks = check_burst_geometry(a.distance, a.basis, f)
    result = {"distance": a.distance, "basis": a.basis, **physical_checks, "arms": {}}
    for arm in p["qualification"]["arms"]:
        sampling = f if arm == "nominal" else s.stressed(f, a.distance, p["burst_probability"])
        shots, key = p["control_shots"], p["control_seed"]
        streamer = s.Stream(sampling, f, p["chunk_loop_periods"], a.distance, verify=True)
        row, _ = streamer.decode(shots, key)
        s.require(row["correction_nonzero_cut_batches"] and row["physical_nonzero_cut_batches"],
                  "negative controls unexercised")
        bad = []
        # One challenged cut of each kind is sufficient; both scenarios still
        # sample the exact same faults as the passing control.
        for name in ("drop_physical_spill", "drop_correction_spill"):
            try:
                streamer.decode(shots, key, **{name: True})
            except ValueError as e:
                s.require(str(e).startswith("trajectory stitch dropped parity"), str(e))
                bad.append({"mutation": name, "rejected_by": str(e)})
            else:
                raise AssertionError(f"invalid stream not rejected: {name}")
        result["arms"][arm] = {"same_fault_replay": row, "negative_controls": bad,
                               "circuit_sha256": s.sha(str(c).encode())}
        print(f"pass d{a.distance} {a.basis} {arm}: whole DEM replay and both bad seams", flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distance", type=int, required=True)
    parser.add_argument("--basis", required=True, choices=["x", "z"])
    parser.add_argument("--out", required=True, type=Path)
    a = parser.parse_args()
    s.require(not a.out.exists(), "don't overwrite controls receipt")
    p = s.load_protocol()
    s.require(a.distance in p["distances"], "unknown distance")
    r = verify(a, p)
    with a.out.open("x") as fp:
        json.dump(r, fp, indent=2, sort_keys=True)
        fp.write("\n")


if __name__ == "__main__":
    main()
