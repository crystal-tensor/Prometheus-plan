#!/usr/bin/env python3
"""Fit readout error without logical labels, then test frozen and recalibrated decoders."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import re
import subprocess
import time
from pathlib import Path

import numpy as np
import pymatching
import scipy
import stim

import b2_b7_p023_d6_correlated_strict_acceptance as prior


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "benchmarks/B2_B7_P023_readout_recalibration_v1.json"
STEM = "B2_B7_P023_readout_recalibration"
PARAMETER = "before_measure_flip_probability"
DESIGNS = ("reference", "candidate")
BASES = ("x", "z")


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def read(p: Path) -> dict:
    return json.loads(p.read_bytes())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def dump_new(path: Path, result: dict) -> None:
    with path.open("x", encoding="utf-8") as out:
        json.dump(result, out, indent=2, sort_keys=True)
        out.write("\n")


def read_protocol() -> dict:
    p = read(PROTOCOL)
    for path, expected in p["input_sha256"].items():
        require(file_sha(ROOT / path) == expected, f"legacy input changed: {path}")
    return p


def with_readout(execution: dict, probability: float, basis: str) -> stim.Circuit:
    settings = copy.deepcopy(execution)
    settings["noise_parameters"][PARAMETER] = probability
    return prior.build_circuit(basis, settings)


def readout_diff(a: stim.Circuit, b: stim.Circuit, p: float, q: float) -> dict:
    require(a.without_noise() == b.without_noise(), "schedule or detector semantics changed")
    old, new = list(a.flattened()), list(b.flattened())
    require(len(old) == len(new), "unexpected number of fault instructions")
    groups, sites = 0, 0
    for i, (x, y) in enumerate(zip(old, new, strict=True)):
        if x == y:
            continue
        measurement = old[i + 1]
        require(measurement.name in ("M", "MX", "MR") and
                x.name == y.name == ("Z_ERROR" if measurement.name == "MX" else "X_ERROR") and
                x.targets_copy() == y.targets_copy() == measurement.targets_copy() and
                x.gate_args_copy() == [p] and y.gate_args_copy() == [q], "non-readout instruction changed")
        groups += 1
        sites += len(x.targets_copy())
    require(groups == 1001 and sites == a.num_measurements, "not exactly one readout-noise site per measurement")
    return {"changed_readout_groups": groups, "changed_readout_sites": sites}


def case(protocol: dict, design: str, basis: str) -> tuple:
    settings = protocol[design]
    execution = read(ROOT / settings["protocol"])[settings["execution_key"]]
    archived = next(r for r in read(ROOT / settings["result"])[settings["rows_key"]] if r["memory_basis"] == basis)
    require(archived["strict_verification_pass"] is True, "nominal archived comparator did not pass")
    noise = protocol["mismatch"]
    p, q = noise["nominal"], noise["heldout_stress"]
    require(execution["distance"] == settings["distance"] and execution["rounds"] == 1000 and
            set(execution["noise_parameters"].values()) == {p} and noise["all_other_noise_parameters"] == p,
            "original horizon or nominal noise changed")
    for field, val in {"python": platform.python_version(), "stim": stim.__version__,
                       "pymatching": pymatching.__version__, "numpy": np.__version__, "scipy": scipy.__version__}.items():
        require(execution["toolchain"][field] == val, f"toolchain drift: {field}")
    nominal = prior.build_circuit(basis, execution)
    nominal_dim = len(prior.active_ids(nominal))
    nominal_dem = nominal.detector_error_model(decompose_errors=True)
    require(nominal_dim == settings["active_qubits"] and
            sha(str(nominal).encode()) == archived[settings["circuit_sha_key"]] and
            sha(str(nominal_dem).encode()) == archived["detector_error_model_sha256"], "baseline circuit/DEM changed")
    stress = with_readout(execution, q, basis)
    delta = readout_diff(nominal, stress, p, q)
    return execution, archived, nominal, nominal_dem, stress, delta


def parity_moments(circuit: stim.Circuit) -> np.ndarray:
    """Use E[(-1)^D] = product(1 - 2p) for the DEM's independent error mechanisms."""
    logs = [0.0] * circuit.num_detectors
    for instruction in circuit.detector_error_model(decompose_errors=False).flattened():
        if instruction.type != "error":
            continue
        p, = instruction.args_copy()
        require(0 <= p < 0.5, "parity model requires positive signs")
        term = math.log1p(-2 * p)
        for target in instruction.targets_copy():
            if target.is_relative_detector_id():
                logs[target.val] += term
    return np.exp(np.asarray(logs))


def moment_model(execution: dict, basis: str, nominal: stim.Circuit, stress: stim.Circuit, protocol: dict) -> tuple:
    zero = with_readout(execution, 0.0, basis)
    zero_moments = parity_moments(zero)
    arities = np.array([len(ins.targets_copy()) for ins in nominal.flattened() if ins.name == "DETECTOR"])
    require(arities.size == nominal.num_detectors and np.all(arities >= 1), "unexpected measurement arities")
    noise = protocol["mismatch"]
    for circuit, p in ((nominal, noise["nominal"]), (stress, noise["heldout_stress"])):
        require(np.allclose(zero_moments * (1 - 2 * p)**arities, parity_moments(circuit), rtol=0.0, atol=1e-12),
                "readout response does not agree with the independently recomputed error-model marginals")
    weights = np.bincount(arities, weights=zero_moments)
    return weights, np.bincount(arities)


def expected_rate(p: float, weights: np.ndarray, n: int) -> float:
    return (1 - float(np.dot(weights, (1 - 2 * p)**np.arange(weights.size))) / n) / 2


def fit_readout(ones: int, trials: int, detector_count: int, weights: np.ndarray, fit: dict) -> float:
    """No circuit outcomes or true stress parameter enter this procedure."""
    rate = ones / trials
    lo, hi = fit["probability_bracket"]
    require(expected_rate(lo, weights, detector_count) < rate < expected_rate(hi, weights, detector_count),
            "detector rate outside the declared one-parameter calibration family")
    for _ in range(fit["bisection_iterations"]):
        mid = (lo + hi) / 2
        if expected_rate(mid, weights, detector_count) < rate:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def fingerprint(circuit: stim.Circuit) -> str:
    return sha(str(circuit).encode())


def challenge(commit: str, salt: str, role: str, design: str, basis: str, circuit: stim.Circuit) -> dict:
    canonical = str(prior.coordinate_canonical(circuit)).encode()
    payload = f"AH-B2-READOUT-v1|freeze={commit}|{salt}|{role}|{design}|{basis}".encode()
    challenge_hex = sha(payload + b"\x00" + canonical)
    return {"role": role, "sha256": challenge_hex, "seed": int(challenge_hex[:16], 16) & ((1 << 63) - 1)}


def bound_paths(git: str, freeze: str) -> dict:
    require(re.fullmatch(r"[0-9a-f]{40}", freeze) is not None, "need the pre-sampling freeze commit")
    frozen = {}
    paths = (PROTOCOL, Path(__file__).resolve())
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        committed = subprocess.check_output([git, "show", f"{freeze}:{rel}"], cwd=ROOT)
        require(committed == path.read_bytes(), f"source drift since freeze: {rel}")
        frozen[rel] = sha(committed)
    return frozen


def run(protocol: dict, args: argparse.Namespace) -> dict:
    frozen = bound_paths(args.git, args.freeze)
    require(re.fullmatch(r"[0-9a-f]{64}", args.salt) is not None, "need a fresh 32-byte challenge salt")
    design, basis = args.design, args.basis
    accept, fit = protocol["acceptance"], protocol["calibration"]
    execution, archived, nominal, nominal_dem, stress, delta = case(protocol, design, basis)
    weights, counts = moment_model(execution, basis, nominal, stress, protocol)
    scores = {}
    for role in (fit["calibration_sampling_role"], fit["holdout_sampling_role"]):
        scores[role] = challenge(args.freeze, args.salt, role, design, basis, stress)
    teach, test = (scores[fit[role]] for role in ("calibration_sampling_role", "holdout_sampling_role"))
    require(teach["seed"] != test["seed"], "calibration/holdout seeds collided")
    n_teach = fit["shots_per_design_and_basis"]
    n_detectors = stress.num_detectors
    train_detectors = stress.compile_detector_sampler(seed=teach["seed"]).sample(n_teach, bit_packed=True)
    require(train_detectors.shape == (n_teach, (n_detectors + 7) // 8), "unexpected calibration record shape")
    teach_digest = sha(train_detectors.tobytes())
    seen = np.unpackbits(train_detectors, axis=1, count=n_detectors, bitorder="little")
    ones, n_trials = int(seen.sum()), n_teach * n_detectors
    inferred = fit_readout(ones, n_trials, n_detectors, weights, fit)
    del seen, train_detectors
    recal_dem = with_readout(execution, inferred, basis).detector_error_model(decompose_errors=True)
    dem_by_policy = {"frozen": nominal_dem, "recalibrated": recal_dem}
    correlated = protocol[design]["enable_correlations"]
    matchers = {name: pymatching.Matching.from_detector_error_model(dem, enable_correlations=correlated)
                for name, dem in dem_by_policy.items()}
    # Both graphs are already fixed. Only now construct the holdout stream.
    print(f"{design}/{basis}: fit p={inferred:.9f} from {n_teach} calibration shots; starting holdout", flush=True)
    sampler = stress.compile_detector_sampler(seed=test["seed"])
    n, block = accept["heldout_shots_per_design_and_basis"], accept["chunk_shots"]
    require(n == 102400 and n % block == 0 and block % 8 == 0, "invalid heldout denominator/chunking")
    packed = {name: bytearray() for name in matchers}
    chunks = []
    started = time.perf_counter()
    for offset in range(0, n, block):
        detectors, observables = sampler.sample(block, separate_observables=True, bit_packed=True)
        trace = {"offset": offset, "shots": block, "sample_sha256": sha(detectors.tobytes() + observables.tobytes()),
                 "predictions_sha256": {}}
        for name, matcher in matchers.items():
            prediction = matcher.decode_batch(detectors, bit_packed_shots=True, bit_packed_predictions=True,
                                              enable_correlations=correlated)
            require(prediction.shape == observables.shape == (block, 1), "prediction/observable shape drift")
            trace["predictions_sha256"][name] = sha(prediction.tobytes())
            packed[name].extend(np.packbits((prediction != observables).ravel(), bitorder="little").tobytes())
        chunks.append(trace)
        if (offset + block) % 16384 == 0:
            print(f"{design}/{basis}: {offset+block}/{n} heldout (counts hidden until complete)", flush=True)
    elapsed = time.perf_counter() - started
    require(bound_paths(args.git, args.freeze) == frozen and read_protocol() == protocol, "source changed mid-run")
    return {
        "schema": "b2_b7_p023_readout_recalibration_run_v1",
        "design": design, "basis": basis, "freeze_commit": args.freeze, "challenge_salt": args.salt,
        "frozen_files_sha256": frozen, "legacy_inputs_sha256": protocol["input_sha256"],
        "distance": execution["distance"], "rounds": execution["rounds"], "active_qubits": protocol[design]["active_qubits"],
        "enable_correlations": correlated, "detectors": n_detectors,
        "nominal_circuit_sha256": fingerprint(nominal), "stress_circuit_sha256": fingerprint(stress),
        "readout_diff": delta, "archived_nominal_failures_not_a_control_arm": archived["logical_failures"],
        "calibration": teach | {
            "shots": n_teach, "detector_bits": n_trials, "detector_ones": ones, "detector_record_sha256": teach_digest,
            "arity_counts": counts.tolist(), "no_readout_parity_weight_sums": weights.tolist(),
            "estimated_readout_probability": inferred,
        },
        "decode_graph_sha256": {name: sha(str(dem).encode()) for name, dem in dem_by_policy.items()},
        "holdout": test | {"shots": n, "chunks": chunks, "elapsed_s_diagnostic_only": elapsed,
                           "failure_bitset_hex_little_endian": {name: vec.hex() for name, vec in packed.items()}},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", choices=DESIGNS, required=True)
    parser.add_argument("--basis", choices=BASES, required=True)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--freeze")
    parser.add_argument("--salt")
    parser.add_argument("--artifact-dir", type=Path)
    parser.add_argument("--git", default="git")
    args = parser.parse_args()
    p = read_protocol()
    if args.preflight:
        execution, _, nominal, _, stress, diff = case(p, args.design, args.basis)
        weights, counts = moment_model(execution, args.basis, nominal, stress, p)
        print(f"{args.design}/{args.basis} structural check: {diff}, arity counts={counts.tolist()}, "
              f"no samples drawn, predicted rate={expected_rate(p['mismatch']['heldout_stress'], weights, stress.num_detectors):.8f}")
        return
    require(args.freeze and args.salt and args.artifact_dir is not None, "run starts only after a freeze and a fresh salt")
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    out = args.artifact_dir / f"{STEM}_{args.design}_{args.basis}_raw_v1.json"
    require(not out.exists(), f"refusing to replace {out}")
    dump_new(out, run(p, args))
    print(f"recorded {out}", flush=True)


if __name__ == "__main__":
    main()
