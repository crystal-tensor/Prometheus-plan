#!/usr/bin/env python3
"""Independently audit the Kaggle-inspired strict QEC reference gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pymatching
import scipy
from scipy.optimize import brentq
from scipy.stats import binom
import stim


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_kaggle_inspired_acceptance_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_kaggle_inspired_acceptance_v1.json"
DEFAULT_AUDIT = ROOT / "results/B2_B7_P023_kaggle_inspired_acceptance_audit_v1.json"
DELTA = 2.0 ** -128


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def item(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def independent_cp_upper(failures: int, shots: int) -> float:
    if failures >= shots:
        return 1.0
    log_delta = math.log(DELTA)
    lower = failures / shots
    return float(
        brentq(
            lambda probability: binom.logcdf(failures, shots, probability) - log_delta,
            lower,
            1.0 - 1e-15,
            xtol=1e-14,
            rtol=1e-14,
        )
    )


def circuit_for(basis: str, experiment: dict[str, Any]) -> stim.Circuit:
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


def seed_for(salt: str, circuit: stim.Circuit) -> tuple[int, str]:
    hashed = hashlib.sha256(salt.encode() + b"\x00" + str(circuit).encode()).digest()
    return int.from_bytes(hashed[:8], "big") & ((1 << 63) - 1), hashed.hex()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()
    protocol = read(args.protocol)
    result = read(args.result)
    experiment = protocol["strict_reference_experiment"]
    rows = result["strict_reference_rows"]
    versions = {
        "python": platform.python_version(),
        "stim": stim.__version__,
        "pymatching": pymatching.__version__,
        "numpy": np.__version__,
        "scipy": scipy.__version__,
    }
    regenerated = []
    for row in rows:
        circuit = circuit_for(row["memory_basis"], experiment)
        dem = circuit.detector_error_model(decompose_errors=True)
        matching = pymatching.Matching.from_detector_error_model(dem)
        seed, challenge_hash = seed_for(experiment["challenge_salt"], circuit)
        regenerated.append(
            {
                "row": row,
                "circuit_sha256": sha(str(circuit).encode()),
                "dem_sha256": sha(str(dem).encode()),
                "seed": seed,
                "challenge_hash": challenge_hash,
                "qubits": circuit.num_qubits,
                "detectors": circuit.num_detectors,
                "observables": circuit.num_observables,
                "matching_nodes": matching.num_nodes,
                "matching_edges": matching.num_edges,
            }
        )
    freeze_commit = protocol["frozen_inputs"]["artifact_freeze_commit"]
    frozen_hashes = {}
    for name in ["direct_1k_protocol", "direct_1k_result", "direct_1k_generator"]:
        binding = protocol["frozen_inputs"][name]
        frozen_hashes[name] = sha(
            subprocess.check_output(
                ["git", "show", f"{freeze_commit}:{binding['path']}"],
                cwd=ROOT,
            )
        )
    independent_bounds = {
        row["memory_basis"]: independent_cp_upper(row["logical_failures"], row["shots"])
        for row in rows
    }
    target = experiment["target_total_logical_failure"]
    strict_pass = all(value <= target for value in independent_bounds.values())
    costs = {
        row["memory_basis"]: row["physical_qubits_in_stim_circuit"] * row["rounds"]
        for row in rows
    }
    expected_score = 1.0 if strict_pass else 0.0
    old_rows = result["previous_3838_shot_regrade"]
    zero_floor = math.ceil(math.log(DELTA) / math.log(1.0 - target))
    checks = [
        item("scope", result["scope"] == protocol["scope"] and result["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact scope."),
        item("protocol_hash", result["protocol_binding"]["sha256"] == file_sha(args.protocol), file_sha(args.protocol)),
        item("current_input_hashes", all(file_sha(ROOT / value["path"]) == value["sha256"] for name, value in protocol["frozen_inputs"].items() if isinstance(value, dict)), "All current frozen inputs match."),
        item("commit_input_hashes", all(frozen_hashes[name] == protocol["frozen_inputs"][name]["sha256"] for name in frozen_hashes), f"Freeze commit: {freeze_commit}."),
        item("recorded_commit_bindings", all(value["matches_protocol_binding"] for value in result["protocol_binding"]["frozen_commit_bindings"].values()), "All recorded commit bindings pass."),
        item("generator_hash", file_sha(ROOT / result["generator"]["path"]) == result["generator"]["sha256"], result["generator"]["sha256"]),
        item("toolchain", versions == experiment["toolchain"], str(versions)),
        item("official_source_classes", [value["source_class"] for value in result["official_sources"]] == ["official_competition_evaluation", "official_companion_preprint"], "Two official sources."),
        item("adoption_boundary", result["adoption_map"] == protocol["adoption_map"] and len(result["adoption_map"]["not_copied"]) == 3, "Adopted and rejected transfers are explicit."),
        item("basis_rows", [row["memory_basis"] for row in rows] == ["x", "z"], "X and Z are both present."),
        item("direct_exposure", all(row["rounds"] == 1000 and row["shots"] == 102400 for row in rows), "Exactly 102,400 direct 1,000-round shots per basis."),
        item("regenerated_circuits", all(value["circuit_sha256"] == value["row"]["circuit_sha256"] for value in regenerated), "Circuit hashes reproduce."),
        item("regenerated_dems", all(value["dem_sha256"] == value["row"]["detector_error_model_sha256"] for value in regenerated), "DEM hashes reproduce."),
        item("regenerated_seeds", all(value["seed"] == value["row"]["seed"] and value["challenge_hash"] == value["row"]["challenge_hash_sha256"] for value in regenerated), "Salted circuit-hash seeds reproduce."),
        item("regenerated_dimensions", all(value["qubits"] == value["row"]["physical_qubits_in_stim_circuit"] and value["detectors"] == value["row"]["detectors"] and value["observables"] == value["row"]["observables"] and value["matching_nodes"] == value["row"]["matching_nodes"] and value["matching_edges"] == value["row"]["matching_edges"] for value in regenerated), "Circuit and matching dimensions reproduce."),
        item("failure_arithmetic", all(row["logical_error_rate"] == row["logical_failures"] / row["shots"] for row in rows), "Observed rates reproduce."),
        item("independent_cp_bounds", all(math.isclose(row["clopper_pearson_upper_delta_2m128"], independent_bounds[row["memory_basis"]], abs_tol=2e-13, rel_tol=0) for row in rows), str(independent_bounds)),
        item("strict_flags", all(row["strict_verification_pass"] == (independent_bounds[row["memory_basis"]] <= target) for row in rows), "Strict flags reproduce."),
        item("strict_pair_gate", result["reference_gate"]["both_bases_strict_pass"] == strict_pass, f"Both pass: {strict_pass}."),
        item("previous_regrade", all(row["wilson_95_pass"] and not row["strict_verification_pass"] for row in old_rows), "The old 3,838-shot packet is exploratory only."),
        item("zero_failure_floor", zero_floor == result["reference_gate"]["zero_failure_minimum_shots_at_1pct_delta_2m128"] == 8828, f"Floor: {zero_floor}."),
        item("chunk_coverage", all(len(row["chunk_digests"]) == 400 and sum(chunk["shots"] for chunk in row["chunk_digests"]) == row["shots"] for row in rows), "400 chunks per basis."),
        item("chunk_shapes", all(all(chunk["detector_shape"] == [chunk["shots"], math.ceil(row["detectors"] / 8)] and chunk["observable_shape"] == [chunk["shots"], 1] and chunk["prediction_shape"] == [chunk["shots"], 1] for chunk in row["chunk_digests"]) for row in rows), "All packed shapes reproduce."),
        item("hash_shapes", all(all(len(row[key]) == 64 for key in ["challenge_hash_sha256", "circuit_sha256", "detector_error_model_sha256", "sample_prediction_trace_sha256", "failure_vector_sha256"]) for row in rows), "All primary hashes are SHA-256 shaped."),
        item("costs", result["reference_gate"]["reference_cost_by_basis"] == costs and result["reference_gate"]["reference_pair_cost"] == sum(costs.values()), str(costs)),
        item("score", result["reference_gate"]["normalized_reference_score"] == expected_score and result["summary"]["normalized_reference_score"] == expected_score, f"Score: {expected_score}."),
        item("summary", result["summary"]["total_shots"] == sum(row["shots"] for row in rows) and result["summary"]["total_logical_failures"] == sum(row["logical_failures"] for row in rows), "Summary totals reproduce."),
        item("readiness_boundary", result["readiness"]["strict_1k_reference_verified"] == strict_pass and not result["readiness"]["b2_low_overhead_credit_ready"] and not result["readiness"]["p023_scalable_memory_ready"] and not result["readiness"]["b7_memory_credit_ready"] and result["readiness"]["b7_resource_credit"] == 0, "Only the strict reference is promoted."),
        item("claim_boundary", result["claim_boundary"] == protocol["claim_boundary"] and not result["claim_boundary"]["official_kaggle_metric_reimplemented_claimed"] and not result["claim_boundary"]["kaggle_competition_submission_claimed"], "No official-metric or competition claim."),
        item("producer_checks", result["summary"]["checks_failed"] == 0 and all(value["passed"] for value in result["formal_checks"]), f"Producer: {result['summary']['checks_passed']}/{result['summary']['checks_total']}.")
    ]
    failed = [value for value in checks if not value["passed"]]
    output = {
        "schema_version": "b2_b7_p023_kaggle_inspired_acceptance_audit_v1",
        "as_of_date": result["as_of_date"],
        "scope": result["scope"],
        "status": "independent_kaggle_inspired_qec_audit_passed" if not failed else "independent_kaggle_inspired_qec_audit_failed",
        "audited_run_id": result["run_id"],
        "independent_cp_method": "solve log BinomialCDF(k;n,p)=log(2^-128) with Brent root finding, independent of the producer beta inverse-survival path",
        "independent_cp_upper_by_basis": independent_bounds,
        "checks": checks,
        "summary": {
            "checks_passed": sum(value["passed"] for value in checks),
            "checks_total": len(checks),
            "checks_failed": len(failed),
        },
        "failure_names": [value["name"] for value in failed],
    }
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], sort_keys=True))
    if failed:
        raise SystemExit(f"audit failed: {output['failure_names']}")


if __name__ == "__main__":
    main()
