#!/usr/bin/env python3
"""Direct surface-code memory with bounded DEM-sampling and matching windows."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
import pymatching
import stim


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "benchmarks/P023_streamed_memory_v1.json"
Z95 = 1.959963984540054


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise ValueError(msg)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def seed_for(*parts: object) -> int:
    return int.from_bytes(hashlib.sha256(repr(parts).encode()).digest()[:8], "little")


def shift(model: stim.DetectorErrorModel) -> int:
    return sum(i.targets_copy()[0] for i in model if i.type == "shift_detectors")


@dataclass(frozen=True)
class Fold:
    head: stim.DetectorErrorModel
    body: stim.DetectorErrorModel
    tail: stim.DetectorErrorModel
    count: int
    step: int
    model: stim.DetectorErrorModel


def fold(d: int, basis: str, rounds: int, noise: dict[str, float]) -> tuple[stim.Circuit, Fold]:
    circuit = stim.Circuit.generated(
        f"surface_code:rotated_memory_{basis}", distance=d, rounds=rounds, **noise)
    dem = circuit.detector_error_model(decompose_errors=True)
    loops = [i for i, op in enumerate(dem) if isinstance(op, stim.DemRepeatBlock)]
    require(len(loops) == 1, "exactly one folded detector loop required")
    i, = loops
    a, block, z = dem[:i], dem[i], dem[i + 1:]
    b = block.body_copy()
    require(all(not isinstance(op, stim.DemRepeatBlock) for op in b), "nested body")
    step = shift(b)
    require(shift(a) == 0 and step == 2 * (d * d - 1) and step % 8 == 0,
            "unexpected detector offsets")
    require(a + b * block.repeat_count + z == dem, "folded representation changed")
    require(dem.num_detectors == (d * d - 1) * rounds == circuit.num_detectors,
            "unexpected detector count")
    require(dem.num_observables == circuit.num_observables == 1, "one logical frame required")
    return circuit, Fold(a, b, z, block.repeat_count, step, dem)


def stressed(f: Fold, d: int, p: float) -> Fold:
    """One independent two-consecutive-measurement-flip mechanism per check and period."""
    q = d * d - 1
    det = stim.DemTarget.relative_detector_id
    extra = stim.DetectorErrorModel()
    for j in range(q):
        first = 3 * q // 2 + j
        extra.append("error", p, [det(first), det(first + 2 * q)])
    b = extra + f.body
    m = f.head + b * f.count + f.tail
    require(m.num_detectors == f.model.num_detectors and
            m.num_errors == f.model.num_errors + q * f.count, "burst alignment")
    return Fold(f.head, b, f.tail, f.count, f.step, m)


@dataclass(frozen=True)
class Chunk:
    kind: str
    core: int
    model: stim.DetectorErrorModel


def partition(f: Fold, repeats: int) -> list[Chunk]:
    whole, rest = divmod(f.count, repeats)
    require(whole >= 3, "must exercise initial, repeat, and terminal windows")
    core = f.step * repeats
    block = f.body * repeats
    last_core = f.model.num_detectors - whole * core
    tail = f.body * rest + f.tail
    parts = [Chunk("head", core, f.head + block)]
    parts += [Chunk("bulk", core, block)] * (whole - 1)
    parts.append(Chunk("tail", last_core, tail))
    require(all(c.core % 8 == 0 and c.core > 0 for c in parts), "unaligned core")
    require(all(core <= c.model.num_detectors <= 2 * core for c in parts[:-1])
            and tail.num_detectors == last_core, "unsupported spill length")
    require(sum(c.model.num_errors for c in parts) == f.model.num_errors,
            "fault mechanisms were lost or duplicated")
    require(parts[0].model.num_detectors - core <= core and
            parts[-2].model.num_detectors - core <= last_core, "spill beyond following chunk")
    return parts


def window_graph(
    prev: Chunk | None, cur: Chunk, nxt: Chunk | None, requested_guard: int, verify: bool
) -> tuple[pymatching.Matching, int]:
    guard = min(nxt.core, requested_guard) if nxt else 0
    # Include all mechanisms from the immediately preceding chunk. A fault
    # anchored there can have both endpoints on the current side of the cut.
    offset = prev.core if prev else 0
    src = (prev.model + cur.model) if prev else cur.model
    if nxt:
        src = src + nxt.model
    base = pymatching.Matching.from_detector_error_model(src)
    m = pymatching.Matching()
    core_stop = cur.core
    stop = core_stop + guard
    for u, v, data in base.edges():
        if v is not None and v < u:
            u, v = v, u
        u -= offset
        v = v - offset if v is not None else None
        if u < 0 or u >= stop:
            continue
        faults = set()
        committed = u < core_stop
        if v is not None and v >= stop:
            require(nxt is not None and not committed,
                    "guard too short or edge beyond real temporal endpoint")
            v = None  # Virtual future boundary. This edge cannot commit.
        if committed:
            if 0 in data["fault_ids"]:
                faults.add(guard)
            if v is not None and v >= core_stop:
                faults.add(v - core_stop)
            if verify:
                faults.add(guard + 8 + u)
                if v is not None and v < core_stop:
                    faults.add(guard + 8 + v)
        attrs = {"fault_ids": faults, "weight": data["weight"],
                 "merge_strategy": "smallest-weight"}
        if v is None:
            m.add_boundary_edge(u, **attrs)
        else:
            m.add_edge(u, v, **attrs)
    m.ensure_num_fault_ids(guard + 8 + (core_stop if verify else 0))
    require(m.num_detectors == stop, "projection lost a detector index")
    return m, guard


class Stream:
    def __init__(self, sampling: Fold, nominal: Fold, repeats: int, guard: int, verify=False):
        self.parts = partition(sampling, repeats)
        self.nominal = partition(nominal, repeats)
        self.sampling = sampling
        self.verify = verify
        require([c.core for c in self.parts] == [c.core for c in self.nominal],
                "sampling and matching have different layouts")
        bank = {}
        self.windows = []
        for i, cur in enumerate(self.nominal):
            prev = self.nominal[i - 1] if i else None
            nxt = self.nominal[i + 1] if i + 1 < len(self.nominal) else None
            key = (prev.kind if prev else None, cur.kind, nxt.kind if nxt else None)
            if key not in bank:
                bank[key] = window_graph(prev, cur, nxt, guard * nominal.step, verify)
            self.windows.append(bank[key])
        self.graph_types = len(bank)
        self.max_graph_detectors = max(m.num_detectors for m, _ in bank.values())

    def decode(self, shots: int, key: int, *, drop_physical_spill: bool = False,
               drop_correction_spill: bool = False) -> tuple[dict, dict]:
        samplers = {}
        physical = np.zeros(shots, dtype=np.uint8)
        frame = np.zeros_like(physical)
        h = hashlib.sha256()
        latencies = []
        timings = {"sample_ns": 0, "decode_ns": 0}
        if self.verify:
            all_raw = np.zeros((shots, self.sampling.model.num_detectors // 8), dtype=np.uint8)
            all_errors = []
            offsets = np.cumsum([0] + [c.core // 8 for c in self.parts])
            expected_carry = np.zeros((shots, 0), dtype=np.uint8)

        def sample(i):
            c = self.parts[i]
            if c.kind not in samplers:
                samplers[c.kind] = c.model.compile_sampler(seed=seed_for(key, c.kind))
            t0 = time.perf_counter_ns()
            a, o, e = samplers[c.kind].sample(shots, bit_packed=True, return_errors=self.verify)
            timings["sample_ns"] += time.perf_counter_ns() - t0
            physical[:] ^= o[:, 0]
            h.update(a.tobytes())
            h.update(o.tobytes())
            if self.verify:
                all_raw[:, offsets[i]:offsets[i] + a.shape[1]] ^= a
                all_errors.append(np.unpackbits(e, axis=1, count=c.model.num_errors, bitorder="little"))
            return a

        active = sample(0)
        correction_cut_count, physical_cut_count = 0, 0
        for i, (part, (m, guard)) in enumerate(zip(self.parts, self.windows, strict=True)):
            c, g = part.core // 8, guard // 8
            nxt = sample(i + 1) if i + 1 < len(self.parts) else None
            t0 = time.perf_counter_ns()
            if nxt is not None:
                spill = active[:, c:]
                physical_cut_count += bool(np.any(spill))
                if not drop_physical_spill:
                    nxt[:, :spill.shape[1]] ^= spill
                syn = np.concatenate((active[:, :c], nxt[:, :g]), axis=1)
            else:
                syn = active[:, :c]
            if self.verify:
                expected = all_raw[:, offsets[i]:offsets[i + 1]].copy()
                expected[:, :expected_carry.shape[1]] ^= expected_carry
                require(np.array_equal(syn[:, :c], expected),
                        f"trajectory stitch dropped parity at window {i}")
            out = m.decode_batch(syn, bit_packed_shots=True, bit_packed_predictions=True)
            if self.verify:
                require(np.array_equal(out[:, g + 1:], syn[:, :c]),
                        f"correction parity did not clear committed detectors at window {i}")
                expected_carry = out[:, :g].copy()
            frame ^= out[:, g] & 1
            if nxt is not None:
                correction_cut_count += bool(np.any(out[:, :g]))
                if not drop_correction_spill:
                    nxt[:, :g] ^= out[:, :g]
            timing = time.perf_counter_ns() - t0
            latencies.append(timing)
            timings["decode_ns"] += timing
            if self.verify:
                h.update(out.tobytes())
            active = nxt
        failed = frame ^ physical
        receipt = {
            "shots": shots, "seed": key, "windows": len(self.parts),
            "graph_types": self.graph_types, "max_graph_detectors": self.max_graph_detectors,
            "sample_sha256": h.hexdigest(),
            "failures_le_hex": np.packbits(failed, bitorder="little").tobytes().hex(),
            "truth_le_hex": np.packbits(physical, bitorder="little").tobytes().hex(),
            "correction_le_hex": np.packbits(frame, bitorder="little").tobytes().hex(),
            "physical_nonzero_cut_batches": physical_cut_count,
            "correction_nonzero_cut_batches": correction_cut_count,
        }
        if self.verify:
            errors = np.packbits(np.concatenate(all_errors, axis=1), axis=1, bitorder="little")
            raw, obs, _ = self.sampling.model.compile_sampler().sample(
                shots, bit_packed=True, recorded_errors_to_replay=errors)
            require(np.array_equal(all_raw, raw) and np.array_equal(physical, obs[:, 0]),
                    "chunk DEM samples failed identical-fault monolithic replay")
            receipt["monolithic_sample_sha256"] = sha(raw.tobytes() + obs.tobytes())
        timings["batch_window_p99_ns"] = sorted(latencies)[math.ceil(len(latencies) * .99) - 1]
        timings["max_window_ns"] = max(latencies)
        return receipt, timings


def upper(k: int, n: int) -> float:
    f = k / n
    z2 = Z95 ** 2
    return (f + z2 / (2*n) + Z95 * math.sqrt((f*(1-f) + z2/(4*n))/n))/(1 + z2/n)


def planned_cap(n: int, target: float) -> int:
    return max((k for k in range(n + 1) if upper(k, n) <= target), default=-1)


def num_failures(row: dict) -> int:
    return int.from_bytes(bytes.fromhex(row["failures_le_hex"]), "little").bit_count()


def load_protocol() -> dict:
    p = json.loads(PROTOCOL.read_text())
    require({k: v for k, v in p["toolchain"].items()} == {
        "Python": platform.python_version(), "Stim": stim.__version__,
        "PyMatching": pymatching.__version__, "NumPy": np.__version__,
    }, "toolchain changed")
    for file, digest in p["source_sha256"].items():
        require(sha((ROOT / file).read_bytes()) == digest, f"source changed: {file}")
    require(p["noise"] == json.loads((ROOT / p["noise_source"]).read_text())
            ["experiment_contract"]["noise_parameters"], "changed physical noise")
    return p


def check_freeze(freeze: str, git: str) -> None:
    for file in (PROTOCOL, Path(__file__).resolve()):
        archived = subprocess.check_output(
            [git, "show", f"{freeze}:{file.relative_to(ROOT)}"], cwd=ROOT)
        require(archived == file.read_bytes(), f"not the frozen bytes: {file.name}")


def main() -> None:
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--distance", type=int, required=True)
    args.add_argument("--basis", choices=["x", "z"], required=True)
    args.add_argument("--arm", choices=["nominal", "paired-readout"], default="nominal")
    args.add_argument("--rounds", type=int, default=1000)
    args.add_argument("--mode", choices=["control", "qualification"], required=True)
    args.add_argument("--shard", type=int)
    args.add_argument("--freeze")
    args.add_argument("--salt")
    args.add_argument("--git", default="git")
    args.add_argument("--artifact-dir", type=Path)
    a = args.parse_args()
    p = load_protocol()
    require(a.distance in p["distances"], "not a declared candidate")
    q = p["qualification"]
    if a.mode == "qualification":
        require(a.rounds in q["horizons"] and a.freeze and a.salt and
                len(bytes.fromhex(a.salt)) == 32 and a.artifact_dir and
                a.shard is not None and 0 <= a.shard < q["shards"],
                "invalid qualification run")
        check_freeze(a.freeze, a.git)
        shots = q["shots_per_shard"]
        key = seed_for(a.freeze, a.salt, a.distance, a.basis, a.arm, a.rounds, a.shard)
        dest = a.artifact_dir / (f"P023_stream_d{a.distance}_{a.basis}_{a.arm}"
                                 f"_r{a.rounds}_shard{a.shard:02}.json")
        require(not dest.exists(), f"receipt exists: {dest}")
    else:
        require(a.rounds == p["control_rounds"], "controls must use the declared horizon")
        shots, key = p["control_shots"], p["control_seed"]
    c, f = fold(a.distance, a.basis, a.rounds, p["noise"])
    m = stressed(f, a.distance, p["burst_probability"]) if a.arm == "paired-readout" else f
    t0 = time.perf_counter()
    streamer = Stream(m, f, p["chunk_loop_periods"], a.distance, a.mode == "control")
    print(f"ready d={a.distance} {a.basis} {a.arm} rounds={a.rounds} windows="
          f"{len(streamer.parts)} max_graph_detectors={streamer.max_graph_detectors} "
          f"compile_s={time.perf_counter()-t0:.3f}", flush=True)
    row, timings = streamer.decode(shots, key)
    row |= {
        "schema": "p023_streamed_memory_shard_v1", "distance": a.distance, "basis": a.basis,
        "arm": a.arm, "rounds": a.rounds, "active_qubits": 2 * a.distance ** 2 - 1,
        "circuit_sha256": sha(str(c).encode()), "sampling_dem_sha256": sha(str(m.model).encode()),
        "decoder_dem_sha256": sha(str(f.model).encode()), "mode": a.mode, "shard": a.shard,
        "freeze": a.freeze, "salt": a.salt, "platform": platform.platform(),
    }
    if a.mode == "qualification":
        with dest.open("x") as fp:
            json.dump({"receipt": row, "timings": timings}, fp, sort_keys=True, indent=2)
            fp.write("\n")
    print(f"done shots={shots} rounds={a.rounds} failures={num_failures(row)} "
          f"physical_cuts={row['physical_nonzero_cut_batches']} "
          f"correction_cuts={row['correction_nonzero_cut_batches']} "
          f"sample_s={timings['sample_ns']/1e9:.3f} decode_s={timings['decode_ns']/1e9:.3f}",
          flush=True)


if __name__ == "__main__":
    main()
