#!/usr/bin/env python3
"""Reconstruct published Willow binary traces; audit separate calibration sources."""

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import subprocess
import zipfile

import h5py
import numpy as np
import pymatching
import stim


REPO = Path(__file__).resolve().parents[1]
PROTOCOL = REPO / "benchmarks/B7_B2_willow_d6_source_replay_v1.json"
INTAKE = REPO / "tools/b7_public_qec_zip_intake_v1.py"


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def sha(x):
    return hashlib.sha256(x).hexdigest()


def json_read(path):
    return json.loads(path.read_bytes())


def frozen(freeze, git):
    for path in (PROTOCOL, Path(__file__).resolve(), INTAKE):
        ref = subprocess.check_output([git, "show", f"{freeze}:{path.relative_to(REPO)}"], cwd=REPO)
        require(ref == path.read_bytes(), "experiment code no longer matches freeze")


def b8(raw, n, k):
    width = (k+7)//8
    require(k > 0 and len(raw) == n*width, "packed dimensions differ")
    arr = np.frombuffer(raw, dtype=np.uint8).reshape(n, width)
    require(not k % 8 or not np.any(arr[:, -1] >> (k % 8)), "nonzero padding")
    return arr


def willow(directory, receipt_path, basis, p):
    expect = p["selection"]
    n = expect["shots_per_basis"]
    q = json_read(receipt_path)
    prefix = f"stability_paper_data/memory/{expect['patch']}/{basis}/r{expect['rounds']:03}/"
    masks = {x["archive_name"]: x for x in q["selected_members"]}
    rels = {
        "ideal": "circuit_ideal.stim", "noisy": "circuit_noisy_si1000.stim",
        "metadata": "metadata.json", "measurement": "measurements.b8", "sweep": "sweep_bits.b8",
        "detection": "detection_events.b8", "truth": "obs_flips_actual.b8",
        "prior": "decoding_results/sparse_blossom_with_si1000_prior/error_model.dem",
        "publisher": "decoding_results/sparse_blossom_with_si1000_prior/obs_flips_predicted.b8",
    }
    require(set(masks) == {prefix + file for file in rels.values()}, "unselected inputs")
    data = {}
    for key, file in rels.items():
        val = (directory / Path(file).name).read_bytes()
        require(sha(val) == masks[prefix+file]["sha256"] and
                len(val) == masks[prefix+file]["uncompressed_bytes"], "source member changed")
        data[key] = val
    metadata = json.loads(data["metadata"])
    require((metadata["experiment_type"], metadata["patch"], metadata["basis"],
             metadata["distance"], metadata["rounds"], metadata["shots"]) ==
            (expect["experiment_type"], expect["patch"], basis, expect["distance"],
             expect["rounds"], n), "wrong calibration population")
    c = stim.Circuit(data["ideal"].decode())
    model = stim.DetectorErrorModel(data["prior"].decode())
    require(c.num_detectors == model.num_detectors and c.num_observables == model.num_observables == 1,
            "published prior graph size differs")
    m = b8(data["measurement"], n, c.num_measurements)
    sweep = b8(data["sweep"], n, c.num_sweep_bits)
    golden_det = b8(data["detection"], n, c.num_detectors)
    golden_obs = b8(data["truth"], n, c.num_observables)
    golden_pred = b8(data["publisher"], n, c.num_observables)
    converter = c.compile_m2d_converter()
    det, truth = converter.convert(measurements=m, sweep_bits=sweep, bit_packed=True,
                                   separate_observables=True)
    require(np.array_equal(det, golden_det) and np.array_equal(truth, golden_obs), "raw replay mismatch")
    bad_d, bad_l = converter.convert(measurements=m, sweep_bits=np.zeros_like(sweep),
                                     bit_packed=True, separate_observables=True)
    broken = int(np.count_nonzero(np.any(bad_d != det, axis=1) | np.any(bad_l != truth, axis=1)))
    require(broken > 0, "misalignment control did not change symptoms or truth")
    try:
        b8(data["measurement"], n-1, c.num_measurements)
    except ValueError as exc:
        require(str(exc) == "packed dimensions differ", "error in shot-count mutation")
    else:
        raise AssertionError("wrong shot count accepted")

    pred = {}
    for name, corr in (("independent", False), ("correlated", True)):
        mate = pymatching.Matching.from_detector_error_model(model, enable_correlations=corr)
        pred[name] = mate.decode_batch(det, bit_packed_shots=True, bit_packed_predictions=True,
                                       enable_correlations=corr)
        require(pred[name].shape == truth.shape, "wrong logical output shape")
    f = {name: x[:, 0] != truth[:, 0] for name, x in pred.items()}
    return {
        "basis": basis, "shots": n, "distance": metadata["distance"],
        "rounds": metadata["rounds"], "source_patch": metadata["patch"],
        "metadata_keys": sorted(metadata),
        "source_acquisition_time_in_metadata": any("time" in k.lower() or "date" in k.lower()
                                                   for k in metadata),
        "qubits_in_source_coordinates": len(metadata["qubit_coords"]),
        "measurement_bits": c.num_measurements, "sweep_bits": c.num_sweep_bits,
        "detector_bits": c.num_detectors, "logical_bits": c.num_observables,
        "range_receipt_sha256": sha(receipt_path.read_bytes()),
        "source_hashes": {k: sha(v) for k, v in data.items()},
        "raw_detector_and_truth_exact_rows": n,
        "zero_sweep_changed_rows": broken, "wrong_shot_count_rejected": True,
        "publisher_logical_failures": int(np.count_nonzero(golden_pred != truth)),
        "mwpm_logical_failures": {name: int(np.count_nonzero(val)) for name, val in f.items()},
        "correlated_prediction_disagreement_with_publisher_rows":
            int(np.count_nonzero(pred["correlated"] != golden_pred)),
        "paired_correlated_recovered": int(np.count_nonzero(f["independent"] & ~f["correlated"])),
        "paired_correlated_new_failure": int(np.count_nonzero(~f["independent"] & f["correlated"])),
        "mwpm_prediction_sha256": {k: sha(x.tobytes()) for k, x in pred.items()},
        "independently_calibrated_leakage_flags": False,
    }


def sycamore(path, spec):
    content = path.read_bytes()
    require(hashlib.md5(content).hexdigest() == spec["md5"], "bad calibration archive digest")
    outputs = []
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        for name in sorted(z.namelist()):
            raw = z.read(name)
            rows = csv.reader(io.StringIO(raw.decode()))
            head = [re.fullmatch(r"Amplitude ([IQ]) qubit(\d+) state=(\d+)", x) for x in next(rows)]
            require(all(head) and len(head) == 8, "not an eight-column cloud record")
            labels = [x.groups() for x in head]
            qubit, = set(q for _, q, _ in labels)
            v = np.asarray(list(rows), dtype=float)
            require(v.ndim == 2 and v.shape[1] == 8 and np.isfinite(v).all(), "invalid IQ values")
            cut = len(v)//2
            x = [v[:, [labels.index((axis, qubit, str(i))) for axis in ("I","Q")]]
                 for i in range(4)]
            params = []
            for cloud in x:
                train = cloud[:cut]
                cov = np.cov(train.T) + 1e-6*np.eye(2)
                params.append((train.mean(axis=0), np.linalg.inv(cov), np.linalg.slogdet(cov)[1]))
            cm = []
            for cloud in x:
                test = cloud[cut:]
                score = []
                for mean, inv, logdet in params:
                    off = test-mean
                    score.append(np.einsum("ij,jk,ik->i", off, inv, off) + logdet)
                label = np.argmin(np.stack(score, axis=1), axis=1)
                cm.append(np.bincount(label, minlength=4).tolist())
            outputs.append({"part": name, "qubit": int(qubit), "source_sha256": sha(raw),
                            "train_shots_per_prepared_state": cut, "test_shots_per_prepared_state": len(v)-cut,
                            "prepared_by_predicted_state_confusion": cm,
                            "false_flags_on_prepared_0_1": sum(sum(row[2:]) for row in cm[:2]),
                            "missed_flags_on_prepared_2_3": sum(sum(row[:2]) for row in cm[2:])})
    return {"archive_sha256": sha(content), "independent_calibration_only": True, "parts": outputs}


def ankaa(path, spec):
    raw = path.read_bytes()
    require(hashlib.md5(raw).hexdigest() == spec["md5"], "bad Ankaa-2 source digest")
    with h5py.File(path, "r") as h:
        g = h["reference_data/measurement_fidelity"]
        require(set(g) == {"zeros", "ones"}, "unexpected prepared classes")
        cm = []
        for key in ("zeros", "ones"):
            a = g[key]["result/hard_measurements/50"][()]
            require(a.ndim == 2 and a.shape[1] == 1 and np.all(a <= 1), "not binary assignments")
            cm.append(np.bincount(a[:, 0], minlength=2).tolist())
        return {"archive_sha256": sha(raw), "qubit": 50,
                "acquisition_session_utc": h["session_data/utc_time"][()].decode(),
                "prepared_by_assigned_binary_confusion": cm, "prepared_leakage_labels": False}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--freeze", required=True)
    ap.add_argument("--git", default="git")
    a = ap.parse_args()
    require(not a.out.exists(), "do not overwrite a receipt")
    frozen(a.freeze, a.git)
    p = json_read(PROTOCOL)
    root = a.input
    datasets = [willow(root/f"d6{b.lower()}", root/f"willow_d6{b.lower()}_range.json", b, p)
                for b in p["selection"]["bases"]]
    val = {"schema": p["schema"], "freeze": a.freeze,
           "protocol_sha256": sha(PROTOCOL.read_bytes()),
           "toolchain": {"Python": platform.python_version(), "stim": stim.__version__,
                         "pymatching": pymatching.__version__, "numpy": np.__version__,
                         "h5py": h5py.__version__},
           "primary_datasets": datasets,
           "separate_calibration": {
               "sycamore": sycamore(root/"readout_clouds.zip", p["separate_calibration"]["sycamore"]),
               "ankaa": ankaa(root/"fast_feedback_raw_data.h5", p["separate_calibration"]["ankaa"]),
           },
           "bounds": {"willow_binary_hardware_trace_reconstructed": True,
                      "same_acquisition_ternary_flags_and_confusion_join": False,
                      "original_matched_flag_replay_K5_accepted": False,
                      "original_strict_calibrated_holdout_K6_accepted": False,
                      "b7_resource_credit": 0}}
    with a.out.open("x") as f:
        json.dump(val, f, sort_keys=True, indent=2)
        f.write("\n")
    for d in datasets:
        print(d["basis"], d["shots"], d["mwpm_logical_failures"],
              "published baseline disagreement", d["correlated_prediction_disagreement_with_publisher_rows"],
              "bad sweep changed", d["zero_sweep_changed_rows"], flush=True)


if __name__ == "__main__":
    main()
