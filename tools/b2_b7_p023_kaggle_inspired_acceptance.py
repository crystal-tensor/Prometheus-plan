#!/usr/bin/env python3
"""Run the Kaggle-inspired strict reference gate for #021/B7, #022/B2, #023."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import scipy
from scipy.stats import beta
import stim


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_kaggle_inspired_acceptance_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_kaggle_inspired_acceptance_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_kaggle_inspired_acceptance_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_kaggle_inspired_acceptance_discussion_v1.md"
Z95 = 1.959963984540054
DELTA = 2.0 ** -128


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_path(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def wilson(failures: int, shots: int) -> tuple[float, float]:
    p = failures / shots
    denominator = 1.0 + Z95 * Z95 / shots
    center = (p + Z95 * Z95 / (2.0 * shots)) / denominator
    radius = Z95 * math.sqrt((p * (1.0 - p) + Z95 * Z95 / (4.0 * shots)) / shots) / denominator
    return max(0.0, center - radius), min(1.0, center + radius)


def clopper_pearson_upper(failures: int, shots: int) -> float:
    if failures >= shots:
        return 1.0
    return float(beta.isf(DELTA, failures + 1, shots - failures))


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def build_circuit(basis: str, experiment: dict[str, Any]) -> stim.Circuit:
    noise = experiment["noise_parameters"]
    return stim.Circuit.generated(
        f"surface_code:rotated_memory_{basis}",
        distance=experiment["distance"],
        rounds=experiment["rounds"],
        after_clifford_depolarization=noise["after_clifford_depolarization"],
        before_round_data_depolarization=noise["before_round_data_depolarization"],
        before_measure_flip_probability=noise["before_measure_flip_probability"],
        after_reset_flip_probability=noise["after_reset_flip_probability"],
    )


def challenge_seed(salt: str, circuit_bytes: bytes) -> tuple[int, str]:
    challenge_hash = hashlib.sha256(salt.encode() + b"\x00" + circuit_bytes).digest()
    return int.from_bytes(challenge_hash[:8], "big") & ((1 << 63) - 1), challenge_hash.hex()


def run_basis(basis: str, experiment: dict[str, Any]) -> dict[str, Any]:
    circuit = build_circuit(basis, experiment)
    circuit_bytes = str(circuit).encode()
    seed, challenge_hash = challenge_seed(experiment["challenge_salt"], circuit_bytes)
    started_build = time.perf_counter()
    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(dem)
    sampler = circuit.compile_detector_sampler(seed=seed)
    build_seconds = time.perf_counter() - started_build
    shots = experiment["shots_per_basis"]
    chunk_size = experiment["shot_chunk_size"]
    trace_hasher = hashlib.sha256()
    failure_hasher = hashlib.sha256()
    chunks = []
    failures_total = 0
    sample_seconds = 0.0
    decode_seconds = 0.0
    for index, offset in enumerate(range(0, shots, chunk_size)):
        chunk_shots = min(chunk_size, shots - offset)
        started = time.perf_counter()
        detectors, observables = sampler.sample(
            chunk_shots,
            separate_observables=True,
            bit_packed=True,
        )
        sample_seconds += time.perf_counter() - started
        started = time.perf_counter()
        predictions = matching.decode_batch(
            detectors,
            bit_packed_shots=True,
            bit_packed_predictions=True,
        )
        decode_seconds += time.perf_counter() - started
        if predictions.shape != observables.shape:
            raise ValueError("prediction and observable shapes differ")
        failures = np.any(np.bitwise_xor(predictions, observables) != 0, axis=1).astype(np.uint8)
        failures_total += int(np.count_nonzero(failures))
        header = {
            "basis": basis,
            "chunk_index": index,
            "detector_shape": list(detectors.shape),
            "observable_shape": list(observables.shape),
            "prediction_shape": list(predictions.shape),
            "shot_offset": offset,
            "shots": chunk_shots,
        }
        payload = (
            compact(header)
            + b"\x00"
            + detectors.tobytes(order="C")
            + observables.tobytes(order="C")
            + predictions.tobytes(order="C")
        )
        chunk_sha = digest_bytes(payload)
        trace_hasher.update(payload)
        failure_hasher.update(compact({"shot_offset": offset, "shots": chunk_shots}))
        failure_hasher.update(b"\x00")
        failure_hasher.update(failures.tobytes(order="C"))
        chunks.append({**header, "sha256": chunk_sha})
    low95, high95 = wilson(failures_total, shots)
    strict_upper = clopper_pearson_upper(failures_total, shots)
    target = experiment["target_total_logical_failure"]
    total_seconds = build_seconds + sample_seconds + decode_seconds
    return {
        "memory_basis": basis,
        "distance": experiment["distance"],
        "rounds": experiment["rounds"],
        "physical_error": experiment["physical_error"],
        "shots": shots,
        "seed": seed,
        "challenge_hash_sha256": challenge_hash,
        "physical_qubits_in_stim_circuit": circuit.num_qubits,
        "detectors": circuit.num_detectors,
        "observables": circuit.num_observables,
        "matching_nodes": matching.num_nodes,
        "matching_edges": matching.num_edges,
        "logical_failures": failures_total,
        "logical_error_rate": failures_total / shots,
        "wilson_95_low": low95,
        "wilson_95_high": high95,
        "clopper_pearson_upper_delta_2m128": strict_upper,
        "target_total_logical_failure": target,
        "legacy_wilson_pass": high95 <= target,
        "strict_verification_pass": strict_upper <= target,
        "per_basis_physical_qubit_round_cost": circuit.num_qubits * experiment["rounds"],
        "circuit_sha256": digest_bytes(circuit_bytes),
        "detector_error_model_sha256": digest_bytes(str(dem).encode()),
        "sample_prediction_trace_sha256": trace_hasher.hexdigest(),
        "failure_vector_sha256": failure_hasher.hexdigest(),
        "chunk_digests": chunks,
        "timing": {
            "build_seconds": build_seconds,
            "sample_seconds": sample_seconds,
            "decode_seconds": decode_seconds,
            "total_seconds": total_seconds,
            "decode_seconds_per_shot": decode_seconds / shots,
            "decoded_memory_rounds_per_second": shots * experiment["rounds"] / decode_seconds,
        },
    }


def previous_strict_regrade(previous: dict[str, Any], target: float) -> list[dict[str, Any]]:
    rows = [row for row in previous["configurations"] if row["distance"] == 7]
    return [
        {
            "memory_basis": row["memory_basis"],
            "shots": row["shots"],
            "logical_failures": row["logical_failures"],
            "wilson_95_high": row["wilson_95_high"],
            "wilson_95_pass": row["wilson_95_high"] <= target,
            "clopper_pearson_upper_delta_2m128": clopper_pearson_upper(row["logical_failures"], row["shots"]),
            "strict_verification_pass": clopper_pearson_upper(row["logical_failures"], row["shots"]) <= target,
        }
        for row in rows
    ]


def build_result(protocol: dict[str, Any], protocol_path: Path) -> dict[str, Any]:
    if protocol["scope"]["included_catalog_problem_ids"] != [21, 22, 23]:
        raise ValueError("scope mismatch")
    bound_inputs = {}
    for name in ["direct_1k_protocol", "direct_1k_result", "direct_1k_generator"]:
        binding = protocol["frozen_inputs"][name]
        path = ROOT / binding["path"]
        if digest_path(path) != binding["sha256"]:
            raise ValueError(f"hash mismatch: {name}")
        bound_inputs[name] = {"path": binding["path"], "sha256": binding["sha256"]}
    previous = read(ROOT / protocol["frozen_inputs"]["direct_1k_result"]["path"])
    if previous["decision"] != protocol["frozen_inputs"]["direct_1k_result"]["required_decision"]:
        raise ValueError("previous decision mismatch")
    freeze_commit = protocol["frozen_inputs"]["artifact_freeze_commit"]
    frozen_commit_bindings = {}
    for name in ["direct_1k_protocol", "direct_1k_result", "direct_1k_generator"]:
        binding = protocol["frozen_inputs"][name]
        frozen_bytes = subprocess.check_output(
            ["git", "show", f"{freeze_commit}:{binding['path']}"],
            cwd=ROOT,
        )
        frozen_commit_bindings[name] = {
            "path": binding["path"],
            "sha256": digest_bytes(frozen_bytes),
            "matches_protocol_binding": digest_bytes(frozen_bytes) == binding["sha256"],
        }
    versions = {
        "python": platform.python_version(),
        "stim": stim.__version__,
        "pymatching": pymatching.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    if versions != protocol["strict_reference_experiment"]["toolchain"]:
        raise ValueError(f"toolchain mismatch: {versions}")
    experiment = protocol["strict_reference_experiment"]
    previous_regrade = previous_strict_regrade(previous, experiment["target_total_logical_failure"])
    rows = [run_basis(basis, experiment) for basis in experiment["memory_bases"]]
    by_basis = {row["memory_basis"]: row for row in rows}
    both_strict = all(row["strict_verification_pass"] for row in rows)
    costs = {basis: by_basis[basis]["per_basis_physical_qubit_round_cost"] for basis in ["x", "z"]}
    normalized_score = 1.0 if both_strict else 0.0
    zero_failure_floor = math.ceil(
        math.log(DELTA) / math.log(1.0 - experiment["target_total_logical_failure"])
    )
    checks = [
        check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23] and protocol["scope"]["included_tracks"] == ["B2", "B7"], "Exact scope."),
        check("input_hashes", len(bound_inputs) == 3, "Three frozen inputs verified."),
        check("artifact_freeze", all(value["matches_protocol_binding"] for value in frozen_commit_bindings.values()), freeze_commit),
        check("toolchain", versions == experiment["toolchain"], str(versions)),
        check("adoption_boundary", "verifier_first_score_second" in protocol["adoption_map"]["adopted"] and len(protocol["adoption_map"]["not_copied"]) == 3, "Adopted and non-copied rules are explicit."),
        check("basis_set", [row["memory_basis"] for row in rows] == ["x", "z"], "Both bases in frozen order."),
        check("direct_horizon", all(row["rounds"] == 1000 for row in rows), "Both rows directly execute 1,000 rounds."),
        check("shot_count", all(row["shots"] == 102400 for row in rows), "102,400 challenge shots per basis."),
        check("seed_binding", all(row["seed"] == challenge_seed(experiment["challenge_salt"], str(build_circuit(row["memory_basis"], experiment)).encode())[0] for row in rows), "Seeds reproduce from salt and circuit bytes."),
        check("challenge_hash_binding", all(row["challenge_hash_sha256"] == challenge_seed(experiment["challenge_salt"], str(build_circuit(row["memory_basis"], experiment)).encode())[1] for row in rows), "Challenge hashes reproduce."),
        check("prior_circuit_identity", all(row["circuit_sha256"] == next(old["circuit_sha256"] for old in previous["configurations"] if old["memory_basis"] == row["memory_basis"] and old["distance"] == 7) for row in rows), "Strict run uses the frozen distance-7 circuits."),
        check("failure_arithmetic", all(row["logical_error_rate"] == row["logical_failures"] / row["shots"] for row in rows), "Failure rates reproduce."),
        check("wilson_recomputed", all(math.isclose(row["wilson_95_high"], wilson(row["logical_failures"], row["shots"])[1], abs_tol=1e-15, rel_tol=0) for row in rows), "Wilson comparison bounds reproduce."),
        check("strict_cp_recomputed", all(math.isclose(row["clopper_pearson_upper_delta_2m128"], clopper_pearson_upper(row["logical_failures"], row["shots"]), abs_tol=1e-15, rel_tol=0) for row in rows), "Strict Clopper-Pearson bounds reproduce."),
        check("strict_flags", all(row["strict_verification_pass"] == (row["clopper_pearson_upper_delta_2m128"] <= row["target_total_logical_failure"]) for row in rows), "Strict pass flags reproduce."),
        check("previous_regrade", all(row["wilson_95_pass"] and not row["strict_verification_pass"] for row in previous_regrade), "The 3,838-shot staging result passes Wilson but fails the strict gate."),
        check("zero_failure_floor", zero_failure_floor == 8828, f"Zero-failure floor: {zero_failure_floor}."),
        check("chunk_coverage", all(sum(chunk["shots"] for chunk in row["chunk_digests"]) == row["shots"] and len(row["chunk_digests"]) == 400 for row in rows), "400 ordered chunks cover each basis."),
        check("trace_hashes", all(all(len(row[key]) == 64 for key in ["circuit_sha256", "detector_error_model_sha256", "sample_prediction_trace_sha256", "failure_vector_sha256"]) for row in rows), "All primary trace bindings are SHA-256 shaped."),
        check("cost_arithmetic", all(row["per_basis_physical_qubit_round_cost"] == row["physical_qubits_in_stim_circuit"] * row["rounds"] for row in rows), "Per-basis Q*H costs reproduce."),
        check("cost_symmetry", costs["x"] == costs["z"], str(costs)),
        check("normalized_score", normalized_score == (1.0 if both_strict else 0.0), f"Reference score: {normalized_score}."),
        check("timing_recorded", all(all(row["timing"][key] > 0 for key in ["build_seconds", "sample_seconds", "decode_seconds", "total_seconds", "decode_seconds_per_shot", "decoded_memory_rounds_per_second"]) for row in rows), "Local timing is recorded but not promoted."),
        check("downstream_closed", not protocol["claim_boundary"]["scalable_quantum_memory_claimed"] and not protocol["claim_boundary"]["b2_low_overhead_improvement_claimed"] and not protocol["claim_boundary"]["b7_resource_credit_claimed"], "Downstream claims remain false."),
    ]
    failed = [value for value in checks if not value["passed"]]
    if failed:
        raise RuntimeError(f"formal checks failed: {[value['name'] for value in failed]}")
    decision = (
        "kaggle_inspired_strict_1k_reference_verified_p023_b2_b7_credit_closed"
        if both_strict
        else "kaggle_inspired_strict_1k_reference_failed_p023_b2_b7_credit_closed"
    )
    trace_identity = [
        {key: row[key] for key in ["memory_basis", "challenge_hash_sha256", "sample_prediction_trace_sha256", "failure_vector_sha256"]}
        for row in rows
    ]
    run_id = digest_bytes(compact({"protocol": digest_path(protocol_path), "traces": trace_identity, "versions": versions}))
    return {
        "schema_version": "b2_b7_p023_kaggle_inspired_acceptance_result_v1",
        "as_of_date": protocol["as_of_date"],
        "status": "kaggle_inspired_qec_acceptance_reference",
        "decision": decision,
        "scope": protocol["scope"],
        "question": protocol["question"],
        "official_sources": protocol["official_sources"],
        "protocol_binding": {
            "path": str(protocol_path.relative_to(ROOT)),
            "sha256": digest_path(protocol_path),
            "bound_inputs": bound_inputs,
            "artifact_freeze_commit": freeze_commit,
            "frozen_commit_bindings": frozen_commit_bindings,
        },
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": digest_path(Path(__file__).resolve()),
        },
        "execution_environment": {**versions, "system": platform.system(), "machine": platform.machine()},
        "run_id": run_id,
        "adoption_map": protocol["adoption_map"],
        "strict_reference_experiment": experiment,
        "previous_3838_shot_regrade": previous_regrade,
        "strict_reference_rows": rows,
        "reference_gate": {
            "both_bases_strict_pass": both_strict,
            "reference_cost_by_basis": costs,
            "reference_pair_cost": sum(costs.values()),
            "normalized_reference_score": normalized_score,
            "zero_failure_minimum_shots_at_1pct_delta_2m128": zero_failure_floor,
        },
        "candidate_acceptance_contract": protocol["qec_cost_and_score"],
        "promotion_ladder": protocol["promotion_ladder"],
        "readiness": {
            "strict_1k_reference_verified": both_strict,
            "b2_candidate_score_available": False,
            "b2_low_overhead_credit_ready": False,
            "p023_scalable_memory_ready": False,
            "million_round_direct_evidence": False,
            "drift_correlation_stress_passed": False,
            "b7_memory_credit_ready": False,
            "b7_resource_credit": 0,
        },
        "formal_checks": checks,
        "summary": {
            "checks_passed": len(checks),
            "checks_total": len(checks),
            "checks_failed": 0,
            "shots_per_basis": experiment["shots_per_basis"],
            "total_shots": sum(row["shots"] for row in rows),
            "total_logical_failures": sum(row["logical_failures"] for row in rows),
            "both_bases_strict_pass": both_strict,
            "normalized_reference_score": normalized_score,
        },
        "claim_boundary": protocol["claim_boundary"],
        "next_gate": "Freeze a same-condition candidate code/schedule/decoder artifact before revealing its acceptance salt; score it only after both bases pass the strict gate, require Score_QEC>=1.25 with no per-basis regression, and keep #023/B7 closed until million-round and drift/correlation evidence exists.",
    }


def render_report(result: dict[str, Any]) -> str:
    rows = result["strict_reference_rows"]
    old = result["previous_3838_shot_regrade"]
    gate = result["reference_gate"]
    lines = [
        "# B2/B7/#023 Kaggle-Inspired QEC Acceptance Standard v1",
        "",
        f"Last updated: {result['as_of_date']}",
        "",
        f"Status: **{result['decision']}**",
        "",
        "## What is our standard, and what is the baseline?",
        "",
        "The standard is verifier-first and cost-second. A QEC candidate receives no resource score unless both X and Z memories pass the same horizon, noise, decoder, and confidence contract. Only verified candidates are compared with a fixed reference by physical-qubit-round cost.",
        "",
        "The current reference is the frozen distance-7 rotated-surface-code memory at physical error 0.001, exactly 1,000 rounds, Stim 1.16.0, and PyMatching 2.4.0. Its per-basis operational proxy is `Q×H = 118×1,000 = 118,000` physical-qubit-rounds. Once strictly verified it is normalized to score 1.0; a future candidate must reach a geometric X/Z score of at least 1.25 with neither basis regressing.",
        "",
        "## Why the prior pass was downgraded",
        "",
        "The earlier 3,838-shot packet used a two-sided 95% Wilson bound. Under the competition-inspired one-sided Clopper–Pearson bound at confidence `1-2^-128`, it is not accepted:",
        "",
        "| basis | failures/shots | Wilson 95% upper | strict CP upper | Wilson pass | strict pass |",
        "|---|---:|---:|---:|---|---|",
    ]
    for row in old:
        lines.append(
            f"| {row['memory_basis']} | {row['logical_failures']}/{row['shots']} | {row['wilson_95_high']:.6g} | "
            f"{row['clopper_pearson_upper_delta_2m128']:.6g} | {row['wilson_95_pass']} | {row['strict_verification_pass']} |"
        )
    lines.extend([
        "",
        "This is not a contradiction: 95% exploration and `1-2^-128` acceptance answer different questions. The former guides where to spend shots; the latter decides whether a result can become the comparison baseline.",
        "",
        "## Strict 102,400-shot reference run",
        "",
        "| basis | seed | failures/shots | observed pL | strict CP upper | target | strict pass | Q×H |",
        "|---|---:|---:|---:|---:|---:|---|---:|",
    ])
    for row in rows:
        lines.append(
            f"| {row['memory_basis']} | {row['seed']} | {row['logical_failures']}/{row['shots']} | "
            f"{row['logical_error_rate']:.6g} | {row['clopper_pearson_upper_delta_2m128']:.6g} | "
            f"{row['target_total_logical_failure']:.4g} | {row['strict_verification_pass']} | {row['per_basis_physical_qubit_round_cost']:,} |"
        )
    lines.extend([
        "",
        f"Both bases strict-pass: **{gate['both_bases_strict_pass']}**. Normalized reference score: **{gate['normalized_reference_score']}**. Pair cost: **{gate['reference_pair_cost']:,} physical-qubit-rounds**.",
        "",
        "## What was adopted from Google’s competition",
        "",
        "- correctness verification before any cost score;",
        "- fixed reference-cost / candidate-cost improvement ratios;",
        "- geometric mean across the mandatory X and Z tasks;",
        "- one-sided Clopper–Pearson upper bounds at `1-2^-128`;",
        "- artifact-hash-derived challenge seeds and immutable replay manifests;",
        "- zero score when any correctness or evidence gate fails.",
        "",
        "## What was deliberately not copied",
        "",
        "The competition's Toffoli formulas price application circuits, not physical logical memory. Its DQI repetition factor is also inapplicable: a bad DQI output can be rejected and rerun, but a failed memory instance has already lost the unknown quantum state. For memory, reliability is therefore a hard veto, not a purchasable repetition penalty.",
        "",
        "## Claim boundary",
        "",
        "This is an adaptation of evaluation principles, not an official Kaggle metric implementation or competition submission. It does not claim a new code, threshold, scalable or million-round memory, hardware performance, production decoding, B2 low-overhead improvement, B7 resource credit, or quantum advantage.",
        "",
        "## Next gate",
        "",
        result["next_gate"],
        "",
        f"Formal checks: `{result['summary']['checks_passed']}/{result['summary']['checks_total']}`.",
        "",
        "Sources: [official Kaggle evaluation](https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation/overview/evaluation); [official companion paper](https://arxiv.org/abs/2610.23832).",
        "",
    ])
    return "\n".join(lines)


def render_discussion(result: dict[str, Any]) -> str:
    rows = {row["memory_basis"]: row for row in result["strict_reference_rows"]}
    return f"""Should a result that passes at 95% confidence lose its pass when the verifier becomes competition-grade?

For #021/B7 · #022/B2 · #023, our answer is now **yes—and that downgrade is a feature**.

Google Quantum AI's verifiable-compilation competition follows a sharp pattern: verify first, score second; compare against a fixed baseline; combine task improvements geometrically; and make approximation error visible through a confidence bound. We adapted those principles to QEC memory without copying the circuit-specific Toffoli formulas.

The immediate consequence is uncomfortable. Our earlier distance-7, 1,000-round result passed a 1% target under a 95% Wilson upper bound. Regrading the same 13/3,838 X failures and 14/3,838 Z failures with a one-sided Clopper–Pearson bound at `1-2^-128` raises the upper bounds to about 3.32% and 3.39%. The exploratory pass is therefore **not** a strict acceptance pass.

We then froze that artifact, derived fresh challenge seeds from the circuit hashes, and ran 102,400 shots per basis. The strict results are:

- X: {rows['x']['logical_failures']:,}/102,400 failures; strict upper {rows['x']['clopper_pearson_upper_delta_2m128']:.6g}; pass={rows['x']['strict_verification_pass']}.
- Z: {rows['z']['logical_failures']:,}/102,400 failures; strict upper {rows['z']['clopper_pearson_upper_delta_2m128']:.6g}; pass={rows['z']['strict_verification_pass']}.

If both verify, distance 7 becomes the normalized reference score 1.0 at `118×1,000=118,000` physical-qubit-rounds per basis. A future code/schedule/decoder must pass both bases under the identical contract and achieve

`Score_QEC = sqrt((C_X_ref/C_X_candidate) × (C_Z_ref/C_Z_candidate)) ≥ 1.25`,

with neither basis regressing. Any failed verifier gate gives score zero.

One rule was **not** copied: DQI can price errors as rerun overhead because bad candidates are classically rejected. A stored unknown quantum state cannot be recovered by rerunning after memory failure, so reliability remains a hard veto.

Questions for critique:

- Is `1-2^-128` appropriately conservative for QEC, or should hardware memory use a different false-accept budget?
- Should the baseline cost be `Q×H`, or must decoder deadline, measurement bandwidth, and leakage-reset cost enter immediately?
- Does geometric X/Z scoring hide asymmetric failure modes even with a no-regression floor?
- What artifact-freeze and salt-reveal procedure would make an open research benchmark resistant to adaptive seed overfitting?

Current boundary: strict 1,000-round reference verification is **{result['reference_gate']['both_bases_strict_pass']}**; #023 scalable memory remains false; B2 candidate improvement remains untested; B7 resource credit remains zero.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    args = parser.parse_args()
    result = build_result(read(args.protocol), args.protocol)
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(canonical(result), encoding="utf-8")
    args.report.write_text(render_report(result), encoding="utf-8")
    args.discussion.write_text(render_discussion(result), encoding="utf-8")
    print(canonical({"decision": result["decision"], "run_id": result["run_id"], **result["summary"]}), end="")


if __name__ == "__main__":
    main()
