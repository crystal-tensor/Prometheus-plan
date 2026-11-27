#!/usr/bin/env python3
"""Group equal DEM probabilities; preserve each independent flag and joint target set."""

from __future__ import annotations

from array import array
import ctypes
from dataclasses import replace
import math
from pathlib import Path
import subprocess
import sys

import numpy as np
import stim

from p023_streamed_memory_v1 import require


SOURCE = Path(__file__).with_name("p023_grouped_fault_scatter_v1.cc")
OBS = 2**32 - 1
U8 = np.ctypeslib.ndpointer(dtype=np.uint8, flags="C_CONTIGUOUS")
U32 = np.ctypeslib.ndpointer(dtype=np.uint32, flags="C_CONTIGUOUS")


def compile_kernel(compiler: str, build_dir: Path) -> tuple[Path, str]:
    require(build_dir.is_dir(), "compiler needs an existing scratch directory")
    output = build_dir / "p023_grouped_fault_scatter_v1.so"
    require(not output.exists(), "refuse to replace an existing binary")
    platform_flags = []
    if sys.platform == "darwin":
        sdk = subprocess.check_output(["/usr/bin/xcrun", "--sdk", "macosx", "--show-sdk-path"],
                                      text=True).strip()
        platform_flags = ["-isysroot", sdk, "-isystem", str(Path(sdk) / "usr/include/c++/v1")]
    subprocess.run([compiler, *platform_flags, "-std=c++17", "-O3", "-shared", "-fPIC", "-Wall",
                    "-Wextra", "-Werror", str(SOURCE), "-o", str(output)], check=True)
    version = subprocess.check_output([compiler, "--version"], text=True).splitlines()[0]
    return output, version


def kernel(path: Path):
    require(sys.byteorder == "little", "little-endian flags and native data required")
    lib = ctypes.CDLL(str(path.resolve()))
    fn = lib.p023_scatter_group_v1
    fn.argtypes = [U8, ctypes.c_size_t, ctypes.c_size_t, U32, U32, U32,
                   U8, ctypes.c_size_t, U8]
    fn.restype = None
    return fn


class Mechanisms:
    """Read one bounded segment, retaining original error order for replay."""

    def __init__(self, model: stim.DetectorErrorModel):
        self.num_errors = model.num_errors
        num_detectors = model.num_detectors
        self.width = (num_detectors + 7)//8
        require(0 < num_detectors < OBS and model.num_observables == 1
                and 0 < self.num_errors < OBS, "unsupported DEM shape")
        offsets, targets = array("I", [0]), array("I")
        by_p: dict[float, array] = {}
        i = 0
        for op in model.flattened():
            if op.type != "error":
                continue
            p, = op.args_copy()
            require(math.isfinite(p) and 0 <= p <= 1, "bad error probability")
            by_p.setdefault(p, array("I")).append(i)
            for target in op.targets_copy():
                if target.is_separator():
                    continue  # A separator describes decomposition, not a separate draw.
                if target.is_relative_detector_id():
                    require(0 <= target.val < num_detectors, "bad detector")
                    targets.append(target.val)
                else:
                    require(target.is_logical_observable_id() and target.val == 0,
                            "unexpected logical target")
                    targets.append(OBS)
            require(len(targets) < OBS, "offset not representable")
            offsets.append(len(targets))
            i += 1
        require(i == self.num_errors, "grouped compiler did not account for every mechanism")
        self.groups = [(p, np.asarray(ids, dtype=np.uint32)) for p, ids in sorted(by_p.items())]
        self.offsets = np.asarray(offsets, dtype=np.uint32)
        self.targets = np.asarray(targets, dtype=np.uint32)


class Sampler:
    def __init__(self, mechanism: Mechanisms, fn, seed: int):
        self.shape = mechanism
        self.fn = fn
        # The Stim API supplies independent Bernoulli flags; no Pauli-frame
        # simulator is being used as a different physical noise model.
        self.rng = stim.FlipSimulator(batch_size=1, seed=seed)

    def sample(self, shots: int, *, bit_packed: bool = True, return_errors: bool = False,
               recorded_errors_to_replay: np.ndarray | None = None):
        require(shots > 0 and bit_packed, "only packed detector output is supported")
        m = self.shape
        ds = np.zeros((shots, m.width), np.uint8)
        obs = np.zeros((shots, 1), np.uint8)
        errors = np.zeros((shots, m.num_errors), np.uint8) if return_errors else None
        if recorded_errors_to_replay is not None:
            require(recorded_errors_to_replay.shape == (shots, m.num_errors)
                    and recorded_errors_to_replay.dtype == np.bool_, "bad recorded error flags")
        for p, ids in m.groups:
            count = int(ids.size) * shots
            if recorded_errors_to_replay is None:
                flags = self.rng.generate_bernoulli_samples(count, p=p, bit_packed=True)
            else:
                flags = np.packbits(recorded_errors_to_replay[:, ids].T, bitorder="little")
            require(flags.dtype == np.uint8 and flags.shape == ((count+7)//8,), "bad packed flags")
            self.fn(flags, count, shots, ids, m.offsets, m.targets, ds, m.width, obs)
            if errors is not None:
                errors[:, ids] = np.unpackbits(flags, bitorder="little", count=count).reshape(
                    ids.size, shots).T
        return ds, obs, (None if errors is None else np.packbits(errors, axis=1, bitorder="little"))


class GroupedSegment:
    """Only wraps compile_sampler; the decoder stays byte-identical to v1."""

    def __init__(self, dem: stim.DetectorErrorModel, fn):
        self.dem, self.fn, self._mechanisms = dem, fn, None
        self.num_errors = dem.num_errors

    def compile_sampler(self, *, seed):
        if self._mechanisms is None:
            self._mechanisms = Mechanisms(self.dem)
        return Sampler(self._mechanisms, self.fn, seed)


def install(stream, fn) -> None:
    bank = {}
    for part in stream.parts:
        if part.kind not in bank:
            bank[part.kind] = GroupedSegment(part.model, fn)
    stream.parts = [replace(part, model=bank[part.kind]) for part in stream.parts]
