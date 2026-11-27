#!/usr/bin/env python3
"""Audit the sealed paired holdout, including an independent confidence decision."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import numpy as np
import pymatching
from scipy.optimize import brentq
from scipy.stats import beta, binom, binomtest

import b2_b7_p023_readout_recalibration_v1 as run


POLICIES = ("frozen", "recalibrated")
require = run.require


def digest(value: str) -> bool:
    return bool(re.fullmatch(r"[a-f0-9]{64}", value))


def upper(failures: int, shots: int, log2_delta: int) -> float:
    return 1.0 if failures == shots else float(beta.isf(2.0**log2_delta, failures + 1, shots - failures))


def audit_case(p: dict, path: Path, design: str, basis: str, git: str) -> dict:
    row = run.read(path)
    a, fitting = p["acceptance"], p["calibration"]
    require(row["schema"] == "b2_b7_p023_readout_recalibration_run_v1" and
            row["design"] == design and row["basis"] == basis and row["rounds"] == a["rounds"] and
            row["active_qubits"] == p[design]["active_qubits"] and row["distance"] == p[design]["distance"] and
            row["legacy_inputs_sha256"] == p["input_sha256"] and
            row["frozen_files_sha256"] == run.bound_paths(git, row["freeze_commit"]) and digest(row["challenge_salt"]),
            "run not bound to frozen design or code")
    execution, old, nominal, nominal_dem, stress, delta = run.case(p, design, basis)
    require(row["nominal_circuit_sha256"] == run.fingerprint(nominal) and
            row["stress_circuit_sha256"] == run.fingerprint(stress) and row["readout_diff"] == delta and
            row["enable_correlations"] == p[design]["enable_correlations"] and
            row["archived_nominal_failures_not_a_control_arm"] == old["logical_failures"],
            "circuit or readout challenge changed")
    n_det = stress.num_detectors
    teach = row["calibration"]
    test = row["holdout"]
    for chunk, role in ((teach, "calibration_sampling_role"), (test, "holdout_sampling_role")):
        expected = run.challenge(row["freeze_commit"], row["challenge_salt"], fitting[role], design, basis, stress)
        require({k: chunk[k] for k in expected} == expected, f"bad {role} seed binding")
    require(teach["seed"] != test["seed"] and row["detectors"] == n_det and
            teach["shots"] == fitting["shots_per_design_and_basis"] and
            teach["detector_bits"] == teach["shots"] * n_det, "invalid calibration denominator")
    packed_teach = stress.compile_detector_sampler(seed=teach["seed"]).sample(teach["shots"], bit_packed=True)
    observed = int(np.unpackbits(packed_teach, axis=1, count=n_det, bitorder="little").sum())
    require(run.sha(packed_teach.tobytes()) == teach["detector_record_sha256"] and observed == teach["detector_ones"],
            "the independent calibration replay differs")
    weights, counts = run.moment_model(execution, basis, nominal, stress, p)
    require(counts.tolist() == teach["arity_counts"] and weights.tolist() == teach["no_readout_parity_weight_sums"],
            "calibration model drift")
    observed_rate = observed / teach["detector_bits"]
    def residual(q: float) -> float:
        mean_parity = math.fsum(float(w) * (1 - 2 * q)**i for i, w in enumerate(weights)) / n_det
        return (1 - mean_parity) / 2 - observed_rate
    estimate = float(brentq(residual, *fitting["probability_bracket"], xtol=1e-15))
    recorded = teach["estimated_readout_probability"]
    require(abs(estimate - recorded) < 1e-13, "independent fit does not match")
    recal_dem = run.with_readout(execution, recorded, basis).detector_error_model(decompose_errors=True)
    dems = {"frozen": nominal_dem, "recalibrated": recal_dem}
    require(row["decode_graph_sha256"] == {name: run.sha(str(dem).encode()) for name, dem in dems.items()},
            "decoder graph was altered after calibration")

    n, block = a["heldout_shots_per_design_and_basis"], a["chunk_shots"]
    chunks = test["chunks"]
    require(test["shots"] == n and [c["offset"] for c in chunks] == list(range(0, n, block)) and
            all(c["shots"] == block and digest(c["sample_sha256"]) and set(c["predictions_sha256"]) == set(POLICIES)
                and all(digest(d) for d in c["predictions_sha256"].values()) for c in chunks), "holdout chunks incomplete")
    masks = {name: bytes.fromhex(test["failure_bitset_hex_little_endian"][name]) for name in POLICIES}
    require(all(len(d) == n // 8 for d in masks.values()), "missing heldout shot bits")
    det, obs = stress.compile_detector_sampler(seed=test["seed"]).sample(block, separate_observables=True, bit_packed=True)
    require(run.sha(det.tobytes() + obs.tobytes()) == chunks[0]["sample_sha256"], "first holdout chunk drift")
    mode_rows, as_ints = {}, {}
    for name in POLICIES:
        corr = p[design]["enable_correlations"]
        decoder = pymatching.Matching.from_detector_error_model(dems[name], enable_correlations=corr)
        prediction = decoder.decode_batch(det, bit_packed_shots=True, bit_packed_predictions=True, enable_correlations=corr)
        require(run.sha(prediction.tobytes()) == chunks[0]["predictions_sha256"][name] and
                np.packbits((prediction != obs).ravel(), bitorder="little").tobytes() == masks[name][:block//8],
                f"{name}: first holdout predictions/failure bits drift")
        value = int.from_bytes(masks[name], "little")
        as_ints[name] = value
        failures = value.bit_count()
        limit, log2_delta = a["maximum_cp_upper"], a["one_sided_delta_log2"]
        bound = upper(failures, n, log2_delta)
        independent = float(binom.logcdf(failures, n, limit)) <= log2_delta * math.log(2)
        require(independent == (bound <= limit), "beta inversion and binomial-tail acceptance differ")
        mode_rows[name] = {"failures": failures, "cp_upper": bound, "passes": independent}
    f, r = as_ints["frozen"], as_ints["recalibrated"]
    recovered, harmed = (f & ~r).bit_count(), (r & ~f).bit_count()
    require(mode_rows["frozen"]["failures"] - mode_rows["recalibrated"]["failures"] == recovered - harmed,
            "paired failure counts do not reconcile")
    return {
        "design": design, "basis": basis, "active_qubits": row["active_qubits"], "shots": n,
        "freeze_commit": row["freeze_commit"], "challenge_salt": row["challenge_salt"],
        "calibration_seed": teach["seed"], "holdout_seed": test["seed"], "estimated_readout_probability": recorded,
        "calibration_shots": teach["shots"], "counts": mode_rows,
        "archived_nominal_failures_not_a_control_arm": old["logical_failures"],
        "paired_recovered": recovered, "paired_harmed": harmed,
        "paired_p_two_sided_exploratory": binomtest(recovered, recovered + harmed).pvalue if recovered + harmed else 1.0,
        "raw_artifact_sha256": run.file_sha(path),
    }


def evaluate(p: dict, rows: list[dict]) -> dict:
    a = p["acceptance"]
    policies = {}
    for policy in POLICIES:
        qualified = {
            d: all(next(r for r in rows if (r["design"], r["basis"]) == (d, b))["counts"][policy]["passes"]
                   for b in run.BASES)
            for d in run.DESIGNS
        }
        r_cost = p["reference"]["active_qubits"] * a["rounds"]
        c_cost = p["candidate"]["active_qubits"] * a["rounds"]
        score = r_cost / c_cost if all(qualified.values()) else 0.0
        policies[policy] = {"both_bases_by_design": qualified, "scored_cost_ratio": score,
                            "relative_resource_gate": score >= a["score_threshold_if_both_designs_pass"]}
    f, r = (policies[k] for k in POLICIES)
    rescue = r["relative_resource_gate"] and not f["both_bases_by_design"]["candidate"] and f["both_bases_by_design"]["reference"]
    if rescue:
        decision = "retain_71_only_with_recalibration_in_this_stress"
    elif f["relative_resource_gate"]:
        decision = "retain_71_in_this_stress_calibration_not_needed_to_pass"
    elif r["relative_resource_gate"]:
        decision = "retain_71_with_recalibration_in_this_stress_without_qualified_frozen_comparator"
    elif f["both_bases_by_design"]["reference"] or r["both_bases_by_design"]["reference"]:
        decision = "retain_97_for_this_stress_do_not_promote_71"
    else:
        decision = "no_qualified_reference_no_relative_resource_conclusion"
    return {"policies": policies, "calibration_rescue": rescue, "decision": decision}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, default=run.ROOT / "results")
    parser.add_argument("--git", default="git")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    p = run.read_protocol()
    rows = [audit_case(p, args.artifact_dir / f"{run.STEM}_{d}_{b}_raw_v1.json", d, b, args.git)
            for d in run.DESIGNS for b in run.BASES]
    require(len({r["freeze_commit"] for r in rows}) == len({r["challenge_salt"] for r in rows}) == 1 and
            len({r[k] for r in rows for k in ("calibration_seed", "holdout_seed")}) == 8,
            "freeze/seed separation does not reconcile across designs")
    n = p["acceptance"]["heldout_shots_per_design_and_basis"]
    alpha_log = p["acceptance"]["one_sided_delta_log2"] * math.log(2)
    limit = p["acceptance"]["maximum_cp_upper"]
    lo, hi = 0, n
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if float(binom.logcdf(mid, n, limit)) <= alpha_log:
            lo = mid
        else:
            hi = mid
    e = {
        "schema": "b2_b7_p023_readout_recalibration_evidence_v1", "scope": p["scope"],
        "protocol_sha256": run.file_sha(run.PROTOCOL),
        "audit_tool_sha256": run.file_sha(Path(__file__)),
        "freeze_commit": rows[0]["freeze_commit"], "challenge_salt": rows[0]["challenge_salt"],
        "mismatch": p["mismatch"], "strict_maximum_failed_shots_per_basis": lo,
        "rows": rows, "decision": evaluate(p, rows),
        "audit_scope": "calibration streams fully regenerated; first heldout chunk reproduced; all archived holdout bits counted",
        "claim_boundary": {"full_b2": False, "calibrated_device": False, "scalable_023": False, "b7_resource_credit": 0,
                           "hardware_deadline": False, "temporal_correlation_stress": False},
    }
    e["evidence_id"] = run.sha(json.dumps(e, sort_keys=True, separators=(",", ":")).encode())
    file = args.artifact_dir / f"{run.STEM}_evidence_v1.json"
    if args.write:
        run.dump_new(file, e)
    else:
        require(run.read(file) == e, "saved evidence does not replay")
    print(e["evidence_id"], e["decision"])
    for r in rows:
        print(r["design"], r["basis"], f"p_est={r['estimated_readout_probability']:.9g}", r["counts"],
              f"paired_recovered={r['paired_recovered']} paired_harmed={r['paired_harmed']}",
              f"exploratory_p={r['paired_p_two_sided_exploratory']:.4g}")


if __name__ == "__main__":
    main()
