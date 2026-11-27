#!/usr/bin/env python3
"""Blind comparison of a joint ternary decoder and its exact hard marginal."""

import argparse
from itertools import product
import json
from pathlib import Path
import subprocess

import numpy as np
from scipy.stats import binomtest

import b7_qutech_ternary_same_shot_v1 as v1


SPEC = Path("benchmarks/B7_qutech_ternary_likelihood_v2.json")
PUBLISHED_V1 = Path("results/B7_qutech_ternary_same_shot_v1")
DATA, ACC = v1.DATA, v1.ACC
DATA_BITS, ACC_BITS = v1.DATA_BITS, v1.ACC_BITS
SYND, PARITY = v1.SYND, v1.LOGIC.astype(bool)
LITTLE = np.array([1, 2])
TOUCH = np.array([[False, False, False], [True, True, False],
                  [False, True, True], [True, True, True]])
CHANGE = DATA_BITS[:, None, :] != DATA_BITS[None, :, :]
POLICIES = ("binary_fit", "matched_marginal", "ternary_aligned", "ternary_shuffled")


def prep(table, state):
    anc, flag, terminal = v1.normalize(table, state)
    r = anc.shape[1]
    bits = np.array(list(map(int, f"{state:03b}")))
    ideal = np.zeros(r, dtype=np.intp)
    ideal[::2] = (bits[:-1] ^ bits[1:]) @ LITTLE
    return (anc @ LITTLE) ^ ideal, flag @ LITTLE, np.tile(ideal, (len(anc), 1)), terminal


class Joint:
    def __init__(self, parameters):
        pd, pm, r0, r1, qt = parameters
        flip = np.where(TOUCH, qt, pd)[:, None, None, :]
        self.transition = np.where(CHANGE, flip, 1-flip).prod(axis=-1)
        self.readout = v1.kernel(pm)
        latent = ACC_BITS[np.bitwise_xor.outer(ACC,ACC)][:, None, None, :, :]
        b = ACC_BITS[None, :, None, None, :]
        f = ACC_BITS[None, None, :, None, :]
        r = np.where(latent == 1, r1, r0)
        binary = np.where(latent == b, 1-pm, pm)
        extra = np.where(b == 1, np.where(f == 1, r, 1-r), f == 0)
        self.emit = (binary*extra).prod(axis=-1)  # ideal, hard pair, flag pair, accumulator
        v1.check(np.allclose(self.emit.sum(axis=(1,2)), 1), "unnormalized emission")

    def filter(self, hard, flags, ideal):
        n, rounds = hard.shape
        z = np.zeros(n)
        if flags is None:
            p = np.zeros((n,4,4,8))
            p[:,0,0,0] = 1.
            for t in range(rounds):
                advance = (p[:,0] @ self.transition[0] + p[:,1] @ self.transition[1] +
                           p[:,2] @ self.transition[2] + p[:,3] @ self.transition[3])
                p = advance[:,None,v1.ACC_SOURCE,DATA] * self.emit[ideal[:,t],hard[:,t],:,:,None]
                scale = p.sum(axis=(1,2,3))
                p /= scale[:,None,None,None]
                z += np.log(scale)
            terminal = p.sum(axis=(1,2))
        else:
            v1.check(np.all(flags & ~hard == 0), "flag outside the binary-one supports")
            p = np.zeros((n,4,8))
            p[:,0,0] = 1.
            fprev = np.zeros(n, dtype=np.intp)
            for t in range(rounds):
                advance = np.empty_like(p)
                for f in ACC:
                    select = fprev == f
                    advance[select] = p[select] @ self.transition[f]
                p = advance[:,v1.ACC_SOURCE,DATA] * self.emit[ideal[:,t],hard[:,t],flags[:,t],:,None]
                scale = p.sum(axis=(1,2))
                p /= scale[:,None,None]
                z += np.log(scale)
                fprev = flags[:,t]
            terminal = p.sum(axis=1)
        return terminal @ self.readout, z


def shuffle(hard, flags):
    shifted = np.zeros_like(flags)
    for t in range(hard.shape[1]):
        for bit in LITTLE:
            ids = np.flatnonzero(hard[:,t] & bit)
            shifted[ids,t] |= np.roll(flags[ids,t] & bit, len(ids)//2)
    return shifted


def validate():
    v1.validate()
    params = (.12,.09,.31,.57,.26)
    pd, pm, r0, r1, qt = params
    model = Joint(params)
    hard, ideal, known = np.array([[3, 2]]), np.array([[1, 0]]), np.array([[1,2]])
    for observed in (known, None):
        expected = np.zeros(8)
        for e1,e2,f1,f2 in product(range(8),range(8),range(4),range(4)):
            if observed is not None and (f1,f2) != (1,2):
                continue
            prob = 1.
            a, prev, fprev = 0, 0, 0
            for t,(end,flag) in enumerate(((e1,f1),(e2,f2))):
                a ^= SYND[end]
                for bit in range(3):
                    p = qt if any((fprev>>j)&1 and bit in (j,j+1) for j in range(2)) else pd
                    prob *= p if ((prev^end)>>bit)&1 else 1-p
                for j in range(2):
                    true = ((a ^ ideal[0,t]) >> j) & 1
                    bit = (hard[0,t] >> j) & 1
                    mark = (flag >> j) & 1
                    r = r1 if true else r0
                    prob *= (1-pm if bit == true else pm) * ((r if mark else 1-r) if bit else 1-mark)
                prev, fprev = end, flag
            for out in DATA:
                d = (int(out) ^ e2).bit_count()
                expected[out] += prob * pm**d * (1-pm)**(3-d)
        answer,z = model.filter(hard,observed,ideal)
        v1.check(np.allclose(answer[0]*np.exp(z[0]),expected,atol=1e-14,rtol=0),
                 "exact trajectory enumeration disagrees")
    neutral = Joint((pd,pm,r0,r0,pd))
    v1.check(np.allclose(neutral.filter(hard,known,ideal)[0],neutral.filter(hard,None,ideal)[0],
                         atol=1e-14,rtol=0), "uninformative flags affected inferred parity")
    wrong = shuffle(np.tile(hard, (4,1)), np.array([[3,2],[2,0],[0,2],[1,0]]))
    v1.check(np.all(wrong & ~hard == 0) and
             np.array_equal((wrong[...,None]&LITTLE != 0).sum(axis=0), [[2,2],[0,2]]),
             "placebo changed binary support or flag counts")


def fit(cases, d):
    raw = [prep(x[np.linspace(0,len(x)-1,d["train_rows_per_preparation"],dtype=int)],i)
           for i,x in enumerate(cases)]
    hard, flags, ideal, end = (np.concatenate(x) for x in zip(*raw, strict=True))
    truth = np.arange(len(end)),end

    def score(p,z):
        return float(np.mean(z + np.log(p[truth])))

    def rank(params):
        return score(*Joint(params).filter(hard,flags,ideal))

    params = np.array(d["start"],float)
    limits = np.array(d["bounds"])
    best = rank(params)
    for step in d["steps"]:
        for i in range(len(params)):
            logit = np.log(params[i]/(1-params[i]))
            center = params.copy()
            for sign in (-1,1):
                candidate = center.copy()
                candidate[i] = np.clip(1/(1+np.exp(-(logit+sign*step))),*limits[i])
                value = rank(candidate)
                if value > best:
                    best,params = value,candidate
    normalized = ((hard ^ ideal)[...,None] & LITTLE) != 0
    scores = [(score(*v1.posterior(normalized,np.zeros_like(normalized),pd,pm)), pd,pm)
              for pd,pm in product(d["binary_grid"]["data_flip"], d["binary_grid"]["readout_flip"])]
    b,pd,pm = max(scores)
    return {"joint":params.tolist(),"joint_logprob":best,
            "binary_fit":[pd,pm],"binary_logprob":b,"training_rows":len(end)}


def evaluate(cases, fitted):
    joint = Joint(fitted["joint"])
    decisions = {k:[] for k in (*POLICIES,"truth")}
    counts, flags_count = [],0
    for state,x in enumerate(cases):
        hard, flag, ideal, terminal = prep(x,state)
        placebo = shuffle(hard,flag)
        v1.check(np.array_equal((placebo[...,None]&LITTLE != 0).sum(axis=0),
                                (flag[...,None]&LITTLE != 0).sum(axis=0)), "altered flag count")
        counts.append(len(x))
        flags_count += int(np.count_nonzero(flag.any(axis=1)))
        for i in range(0,len(x),768):
            sl = slice(i,i+768)
            h,f,a,last = hard[sl],flag[sl],ideal[sl],terminal[sl]
            observed = ((h ^ a)[...,None] & LITTLE) != 0
            decisions["truth"].append(PARITY[last])
            outputs = [v1.posterior(observed,np.zeros_like(observed),*fitted["binary_fit"]),
                       joint.filter(h,None,a),joint.filter(h,f,a),joint.filter(h,placebo[sl],a)]
            for label,(p,_) in zip(POLICIES,outputs,strict=True):
                decisions[label].append(v1.infer(p,SYND[last]))
    decisions = {k:np.concatenate(v) for k,v in decisions.items()}
    packed = {k:np.packbits(v,bitorder="little").tobytes().hex() for k,v in decisions.items()}
    masks = {k:decisions[k]!=decisions["truth"] for k in POLICIES}
    totals = {k:int(v.sum()) for k,v in masks.items()}
    new = masks["ternary_aligned"]
    paired = {}
    for key,old in masks.items():
        if key == "ternary_aligned":
            continue
        rescue,harm = int((old&~new).sum()),int((~old&new).sum())
        paired[key] = {"rescued":rescue,"harmed":harm,"change":harm-rescue,
                       "one_sided_p":float(binomtest(rescue,rescue+harm,.5,alternative="greater").pvalue)
                       if rescue+harm else 1.}
    return {"test_shots":len(new),"shots_by_preparation":counts,"ancilla_flagged_shots":flags_count,
            "failures":totals,"aligned_vs":paired,
            "passes_public_diagnostic":all(paired[k]["one_sided_p"] <= .0125 for k in POLICIES[:2])
            and totals["ternary_aligned"] < totals["ternary_shuffled"]}, packed


def write(path,item):
    with path.open("x") as f:
        json.dump(item,f,indent=2,sort_keys=True)
        f.write("\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact-dir",required=True,type=Path)
    p.add_argument("--out-dir",required=True,type=Path)
    p.add_argument("--freeze",required=True)
    p.add_argument("--git",default="git")
    a = p.parse_args()
    for path in (SPEC,Path("tools")/Path(__file__).name,Path("tools")/Path(v1.__file__).name,
                 Path("tools/b7_public_qec_zip_intake_v1.py"),Path("tools/b7_qutech_likelihood_intake_v2.py")):
        v1.check(subprocess.check_output([a.git,"show",f"{a.freeze}:{path}"])==path.read_bytes(),
                 f"not frozen: {path}")
    validate()
    spec = json.loads(SPEC.read_bytes())
    seen = {x["sha256"] for path in PUBLISHED_V1.glob("*_?.json")
            for x in json.loads(path.read_bytes())["selected_members"]}
    v1.check(len(seen)==32, "missing v1 disclosure boundary")
    result = {"schema":"b7_qutech_ternary_likelihood_result_v2","freeze":a.freeze,"rows":[],
              "claim_boundary":spec["claim_boundary"]}
    for level in spec["experiment"]["injection_levels_as_named_by_provider"]:
        train,tr,htrain = v1.read(a.artifact_dir,spec,"train",level)
        fitted = fit(train,spec["decoder"])
        print(f"level {level}: training locked on {fitted['training_rows']} shots",flush=True)
        test,te,htest = v1.read(a.artifact_dir,spec,"test",level)
        all_hashes = set(htrain+htest)
        v1.check(len(all_hashes)==16 and seen.isdisjoint(all_hashes),"repeated or previously scored member")
        seen.update(all_hashes)
        row,bits = evaluate(test,fitted)
        bits_path = a.out_dir/f"predictions_{level}.json"
        write(bits_path, {"bit_order":"little","shots":row["test_shots"],"prediction_hex":bits})
        result["rows"].append(row | {"injection_level":level,"fit":fitted,
            "train_receipt_sha256":tr,"test_receipt_sha256":te,
            "prediction_file_sha256":v1.digest(bits_path.read_bytes())})
        print(f"level {level}: {row['test_shots']} {row['failures']} {row['passes_public_diagnostic']}",flush=True)
    write(a.out_dir/"score.json", result)


if __name__ == "__main__":
    main()
