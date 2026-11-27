#!/usr/bin/env python3
"""Test real same-shot ancilla class-2 flags with a fixed exact Bayesian decoder."""

import argparse
import hashlib
from itertools import product
import json
from pathlib import Path
import subprocess

import numpy as np
from scipy.stats import binomtest


SPEC = Path("benchmarks/B7_qutech_ternary_same_shot_v1.json")
DATA = np.arange(8)
ACC = np.arange(4)
DATA_BITS = (DATA[:, None] >> np.arange(3)) & 1
ACC_BITS = (ACC[:, None] >> np.arange(2)) & 1
SYND = (DATA_BITS[:, 0] ^ DATA_BITS[:, 1]) | ((DATA_BITS[:, 1] ^ DATA_BITS[:, 2]) << 1)
LOGIC = DATA_BITS.sum(axis=-1) % 2
DIST = np.count_nonzero(DATA_BITS[:, None] != DATA_BITS[None, :], axis=-1)
ACC_SOURCE = ACC[:, None] ^ SYND[None, :]


def check(condition, desc):
    if not condition:
        raise ValueError(desc)


def digest(x):
    return hashlib.sha256(x).hexdigest()


def read(root, spec, split, level):
    path = root / f"{split}_{level}.json"
    proof = json.loads(path.read_bytes())
    s, ex = spec["source"], spec["experiment"]
    check(proof["inventory_sha256"] == s["inventory_sha256"] and
          len(proof["selected_members"]) == 8, "wrong public archive or selected members")
    files = {e["archive_name"]:e for e in proof["selected_members"]}
    cases = []
    for state in ex["prepared_bitstrings_as_integer"]:
        name = f'{ex["mode"]}_round_{ex["rounds"]}_leak_{level}_state_{state}.txt'
        raw = (root / split / str(level) / name).read_bytes()
        check(digest(raw) == files[f'{s["prefix"]}/{split}/{name}']["sha256"],
              f"member mismatch {split}/{name}")
        table = np.loadtxt(raw.splitlines(), dtype=np.int64, ndmin=2, delimiter="\t")
        check(table.shape[1] == ex["rounds"]*2 + 3 and table.shape[0] >= 512
              and np.all((0 <= table) & (table <= 2)), f"invalid ternary rows in {name}")
        cases.append(table.astype(np.uint8))
    return cases, digest(path.read_bytes()), sorted(e["sha256"] for e in files.values())


def normalize(table, state):
    prepared = np.array(list(map(int, f"{state:03b}")), np.uint8)
    r = (table.shape[1] - 3) // 2
    base = prepared[:-1] ^ prepared[1:]
    ideal = np.zeros((r, 2), np.uint8)
    ideal[::2] = base                       # measured ancillas were not reset between cycles
    observations = table[:, :-3].reshape(-1, 2, r).swapaxes(1, 2)
    anc = (observations != 0) ^ ideal[None, :, :]
    term = (table[:, -3:] != 0) ^ (prepared ^ ((r - 1) % 2))  # provider's data echo
    return anc, observations == 2, term @ (1 << np.arange(3))


def kernel(p):
    return p**DIST * (1-p)**(3-DIST)


def posterior(anc, mask, pd, pm):
    p = np.zeros((len(anc), 4, 8))
    p[:, 0, 0] = 1
    travel, readout = kernel(pd), kernel(pm)
    logscale = np.zeros(len(anc))
    for i in range(anc.shape[1]):
        p = (p @ travel)[:, ACC_SOURCE, DATA]
        target = anc[:, i, None, :] == ACC_BITS[None, :, :]
        likelihood = np.where(mask[:, i, None, :], 1, np.where(target, 1-pm, pm)).prod(axis=-1)
        p *= likelihood[:, :, None]
        scale = p.sum(axis=(1, 2))
        logscale += np.log(scale)
        p /= scale[:, None, None]
    return p.sum(axis=1) @ readout, logscale


def infer(p, terminal_syndromes):
    permitted = terminal_syndromes[:, None] == SYND[None, :]
    return (p * permitted * LOGIC).sum(axis=1) > (p * permitted * (1-LOGIC)).sum(axis=1)


def validate():
    samples = np.array([[[1, 0], [1, 1]], [[0, 0], [0, 1]]], dtype=bool)
    masks = np.array([[[1, 0], [0, 0]], [[0, 0], [0, 1]]], dtype=bool)
    pd, pm = .19, .13
    transition = kernel(pd)
    reference = np.zeros((2, 8))
    for row, (read, mask) in enumerate(zip(samples, masks, strict=True)):
        for first, last in product(DATA, repeat=2):
            outcome = [ACC_BITS[SYND[first]], ACC_BITS[SYND[first] ^ SYND[last]]]
            likelihood = np.where(mask, 1, np.where(read == outcome, 1-pm, pm)).prod()
            reference[row, last] += transition[0, first]*transition[first,last]*likelihood
    p, z = posterior(samples, masks, pd, pm)
    check(np.allclose(p * np.exp(z[:,None]), reference @ kernel(pm), atol=1e-14, rtol=0),
          "vectorized posterior differs from exact path enumeration")
    check(np.array_equal(SYND, SYND[DATA ^ 7]) and np.all(LOGIC != LOGIC[DATA ^ 7]),
          "terminal syndrome accidentally identifies the logical bit")


def choose(cases, spec):
    train = [normalize(x[np.linspace(0,len(x)-1,512,dtype=int)], i) for i,x in enumerate(cases)]
    anc, mask, data = (np.concatenate(x) for x in zip(*train, strict=True))
    ranks = []
    for pd, pm in product(spec["data_flip_grid"], spec["measurement_flip_grid"]):
        p, z = posterior(anc, np.zeros_like(mask), pd, pm)
        ranks.append((float(np.mean(z+np.log(p[np.arange(len(data)), data]))), pd, pm))
    score, pd, pm = max(ranks)
    return {"data_flip":pd, "measurement_flip":pm, "joint_training_log_likelihood_per_shot":score}


def evaluate(cases, fit):
    names = ("hard", "aligned_ternary_mask", "one_round_cyclic_shift")
    tracks = {k: [] for k in names}
    truth, flags, termflags, cell_counts = [], [], [], []
    for state, data in enumerate(cases):
        anc, mask, term = normalize(data, state)
        cell_counts.append(len(term))
        truth.append(LOGIC[term].astype(bool))
        flags.append(mask.any(axis=(1,2)))
        termflags.append((data[:,-3:] == 2).any(axis=1))
        for name, flags_in in zip(names, (np.zeros_like(mask), mask, np.roll(mask,1,axis=1)), strict=True):
            for i in range(0,len(term),768):
                sl = slice(i,i+768)
                p, _ = posterior(anc[sl], flags_in[sl], fit["data_flip"], fit["measurement_flip"])
                tracks[name].append(infer(p, SYND[term[sl]]))
    truth, flags, termflags = map(np.concatenate, (truth,flags,termflags))
    predictions = {k:np.concatenate(v) for k,v in tracks.items()}
    baseline = predictions[names[0]] != truth
    out = {}
    for name, pred in predictions.items():
        candidate = pred != truth
        recover = int((baseline & ~candidate).sum())
        harm = int((~baseline & candidate).sum())
        check(not ((pred != predictions["hard"]) & ~flags).any(),
              "masked policy changed a shot that had no ancilla flag")
        out[name] = {"failures":int(candidate.sum()), "recover":recover, "harm":harm,
                     "one_sided_p_for_improvement":float(binomtest(recover,recover+harm,.5,
                                                                 alternative="greater").pvalue) if recover+harm else 1.,
                     "prediction_packbits_sha256":digest(np.packbits(pred,bitorder="little").tobytes())}
    return {"shots":len(truth), "shots_by_state":cell_counts, "ancilla_flagged_shots":int(flags.sum()),
            "terminal_flagged_shots_not_given_to_decoder":int(termflags.sum()), "policies":out,
            "logical_label_packbits_sha256":digest(np.packbits(truth,bitorder="little").tobytes())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", required=True, type=Path)
    parser.add_argument("--freeze", required=True)
    parser.add_argument("--git", default="git")
    parser.add_argument("--out", required=True, type=Path)
    a = parser.parse_args()
    paths = [SPEC, Path("tools") / Path(__file__).name, Path("tools/b7_public_qec_zip_intake_v1.py")]
    for path in paths:
        check(subprocess.check_output([a.git,"show",f"{a.freeze}:{path}"]) == path.read_bytes(),
              f"source not frozen: {path}")
    validate()
    spec = json.loads(SPEC.read_bytes())
    report = {"schema":"b7_qutech_ternary_same_shot_result_v1","freeze":a.freeze,
              "claim_boundary":spec["claim_boundary"],"rows":[]}
    hashes = set()
    for level in spec["experiment"]["injection_levels_as_named_by_provider"]:
        train, train_proof, train_hashes = read(a.artifact_dir,spec,"train",level)
        fit = choose(train, spec["decoder"])
        test, test_proof, test_hashes = read(a.artifact_dir,spec,"test",level)
        all_hashes = train_hashes + test_hashes
        check(len(set(all_hashes)) == 16 and hashes.isdisjoint(all_hashes), "reused archive member")
        hashes.update(all_hashes)
        row = evaluate(test,fit)
        print(level, row["shots"], {p:r["failures"] for p,r in row["policies"].items()}, flush=True)
        report["rows"].append(row | {"injection_level":level,"fit":fit,
                                     "train_receipt_sha256":train_proof,"test_receipt_sha256":test_proof})
    with a.out.open("x") as f:
        json.dump(report,f,sort_keys=True,indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
