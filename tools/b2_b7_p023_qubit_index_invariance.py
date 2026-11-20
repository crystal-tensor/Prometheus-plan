#!/usr/bin/env python3
"""Audit qubit-index invariance of the #021/B7, #022/B2, #023 QEC score."""

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
import stim


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_qubit_index_invariance_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_qubit_index_invariance_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_qubit_index_invariance_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_qubit_index_invariance_discussion_v1.md"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_path(path: Path) -> str:
    return digest_bytes(path.read_bytes())


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


def qubit_value(target: stim.GateTarget) -> int | None:
    if (
        target.is_qubit_target
        or target.is_inverted_result_target
        or target.is_x_target
        or target.is_y_target
        or target.is_z_target
    ):
        return target.value
    return None


def active_qubit_ids(circuit: stim.Circuit) -> list[int]:
    active: set[int] = set()

    def visit(block: stim.Circuit) -> None:
        for item in block:
            if isinstance(item, stim.CircuitRepeatBlock):
                visit(item.body_copy())
                continue
            if item.name == "QUBIT_COORDS":
                continue
            for target in item.targets_copy():
                value = qubit_value(target)
                if value is not None:
                    active.add(value)

    visit(circuit)
    return sorted(active)


def remap_target(target: stim.GateTarget, mapping: dict[int, int]) -> int | stim.GateTarget:
    if target.is_x_target:
        return stim.target_x(mapping[target.value])
    if target.is_y_target:
        return stim.target_y(mapping[target.value])
    if target.is_z_target:
        return stim.target_z(mapping[target.value])
    if target.is_inverted_result_target:
        return stim.target_inv(mapping[target.value])
    if target.is_qubit_target:
        return mapping[target.value]
    return target


def remap_circuit(circuit: stim.Circuit, mapping: dict[int, int]) -> stim.Circuit:
    out = stim.Circuit()
    for item in circuit:
        if isinstance(item, stim.CircuitRepeatBlock):
            out.append(stim.CircuitRepeatBlock(item.repeat_count, remap_circuit(item.body_copy(), mapping)))
            continue
        targets = [remap_target(target, mapping) for target in item.targets_copy()]
        out.append(item.name, targets, item.gate_args_copy())
    return out


def compact_circuit(circuit: stim.Circuit) -> tuple[stim.Circuit, dict[int, int]]:
    active = active_qubit_ids(circuit)
    mapping = {old: new for new, old in enumerate(active)}
    return remap_circuit(circuit, mapping), mapping


def qubit_coordinates(circuit: stim.Circuit) -> dict[int, tuple[float, ...]]:
    coordinates: dict[int, tuple[float, ...]] = {}

    def visit(block: stim.Circuit) -> None:
        for item in block:
            if isinstance(item, stim.CircuitRepeatBlock):
                visit(item.body_copy())
                continue
            if item.name != "QUBIT_COORDS":
                continue
            targets = [target.value for target in item.targets_copy() if target.is_qubit_target]
            if len(targets) != 1:
                raise ValueError("QUBIT_COORDS must bind exactly one qubit")
            coordinates[targets[0]] = tuple(item.gate_args_copy())

    visit(circuit)
    return coordinates


def coordinate_canonical_circuit(circuit: stim.Circuit) -> tuple[stim.Circuit, dict[int, int]]:
    active = active_qubit_ids(circuit)
    coordinates = qubit_coordinates(circuit)
    if any(qubit not in coordinates for qubit in active):
        raise ValueError("every active qubit must have a QUBIT_COORDS binding")
    active_coordinates = [coordinates[qubit] for qubit in active]
    if len(set(active_coordinates)) != len(active_coordinates):
        raise ValueError("active QUBIT_COORDS bindings must be unique")
    ordered = sorted(active, key=lambda qubit: coordinates[qubit])
    mapping = {old: new for new, old in enumerate(ordered)}
    return remap_circuit(circuit, mapping), mapping


def challenge_seed(salt: str, circuit_bytes: bytes) -> tuple[int, str]:
    value = hashlib.sha256(salt.encode() + b"\x00" + circuit_bytes).digest()
    return int.from_bytes(value[:8], "big") & ((1 << 63) - 1), value.hex()


def sample_packet(circuit: stim.Circuit, seed: int, shots: int) -> dict[str, Any]:
    dem = circuit.detector_error_model(decompose_errors=True)
    matching = pymatching.Matching.from_detector_error_model(dem)
    detectors, observables = circuit.compile_detector_sampler(seed=seed).sample(
        shots,
        separate_observables=True,
        bit_packed=True,
    )
    predictions = matching.decode_batch(
        detectors,
        bit_packed_shots=True,
        bit_packed_predictions=True,
    )
    if predictions.shape != observables.shape:
        raise ValueError("prediction and observable shapes differ")
    failures = np.any(np.bitwise_xor(predictions, observables) != 0, axis=1).astype(np.uint8)
    header = {
        "detector_shape": list(detectors.shape),
        "observable_shape": list(observables.shape),
        "prediction_shape": list(predictions.shape),
        "shots": shots,
    }
    trace = (
        compact_json(header)
        + b"\x00"
        + detectors.tobytes(order="C")
        + observables.tobytes(order="C")
        + predictions.tobytes(order="C")
    )
    return {
        **header,
        "logical_failures": int(np.count_nonzero(failures)),
        "detectors_sha256": digest_bytes(detectors.tobytes(order="C")),
        "observables_sha256": digest_bytes(observables.tobytes(order="C")),
        "predictions_sha256": digest_bytes(predictions.tobytes(order="C")),
        "failure_vector_sha256": digest_bytes(failures.tobytes(order="C")),
        "trace_sha256": digest_bytes(trace),
    }


def build_result(protocol: dict[str, Any], protocol_path: Path) -> dict[str, Any]:
    scope = protocol["scope"]
    if scope["included_catalog_problem_ids"] != [21, 22, 23]:
        raise ValueError("scope mismatch")

    frozen_current: dict[str, Any] = {}
    frozen_commit: dict[str, Any] = {}
    freeze_commit = protocol["frozen_inputs"]["artifact_freeze_commit"]
    for name in ("strict_protocol", "strict_result", "strict_generator"):
        binding = protocol["frozen_inputs"][name]
        path = ROOT / binding["path"]
        current_sha = digest_path(path)
        if current_sha != binding["sha256"]:
            raise ValueError(f"current frozen-input hash mismatch: {name}")
        commit_bytes = subprocess.check_output(
            ["git", "show", f"{freeze_commit}:{binding['path']}"],
            cwd=ROOT,
        )
        commit_sha = digest_bytes(commit_bytes)
        if commit_sha != binding["sha256"]:
            raise ValueError(f"commit frozen-input hash mismatch: {name}")
        frozen_current[name] = {"path": binding["path"], "sha256": current_sha}
        frozen_commit[name] = {
            "path": binding["path"],
            "sha256": commit_sha,
            "matches_protocol_binding": True,
        }

    strict_result = read(ROOT / protocol["frozen_inputs"]["strict_result"]["path"])
    required_decision = protocol["frozen_inputs"]["strict_result"]["required_decision"]
    if strict_result["decision"] != required_decision:
        raise ValueError("strict result decision mismatch")
    if not strict_result["reference_gate"]["both_bases_strict_pass"]:
        raise ValueError("strict reference did not pass both bases")

    experiment = strict_result["strict_reference_experiment"]
    strict_rows = {row["memory_basis"]: row for row in strict_result["strict_reference_rows"]}
    audit = protocol["adversarial_audit"]
    salt = protocol["challenge_binding_v2"]["audit_salt"]
    rows: list[dict[str, Any]] = []
    for basis in audit["bases"]:
        original = build_circuit(basis, experiment)
        compacted, mapping = compact_circuit(original)
        canonical_original, canonical_original_mapping = coordinate_canonical_circuit(original)
        canonical_compacted, canonical_compacted_mapping = coordinate_canonical_circuit(compacted)
        original_bytes = str(original).encode()
        compacted_bytes = str(compacted).encode()
        canonical_original_bytes = str(canonical_original).encode()
        canonical_compacted_bytes = str(canonical_compacted).encode()
        original_dem_bytes = str(original.detector_error_model(decompose_errors=True)).encode()
        compacted_dem_bytes = str(compacted.detector_error_model(decompose_errors=True)).encode()
        original_packet = sample_packet(original, audit["audit_seed"], audit["audit_shots_per_basis"])
        compacted_packet = sample_packet(compacted, audit["audit_seed"], audit["audit_shots_per_basis"])
        raw_original_seed, raw_original_challenge = challenge_seed(salt, original_bytes)
        raw_compacted_seed, raw_compacted_challenge = challenge_seed(salt, compacted_bytes)
        canonical_original_seed, canonical_original_challenge = challenge_seed(salt, canonical_original_bytes)
        canonical_compacted_seed, canonical_compacted_challenge = challenge_seed(salt, canonical_compacted_bytes)
        active_original = active_qubit_ids(original)
        active_compacted = active_qubit_ids(compacted)
        rounds = experiment["rounds"]
        old_cost = original.num_qubits * rounds
        corrected_cost = len(active_original) * rounds
        strict_row = strict_rows[basis]
        rows.append(
            {
                "memory_basis": basis,
                "original_index_span_qubits": original.num_qubits,
                "original_active_operational_qubits": len(active_original),
                "original_unused_index_slots": original.num_qubits - len(active_original),
                "original_active_ids_sha256": digest_bytes(compact_json(active_original)),
                "compacted_index_span_qubits": compacted.num_qubits,
                "compacted_active_operational_qubits": len(active_compacted),
                "compaction_mapping_sha256": digest_bytes(compact_json(mapping)),
                "coordinate_canonicalization": {
                    "all_active_qubits_bound": len(qubit_coordinates(original)) == len(active_original),
                    "unique_active_coordinates": len(set(qubit_coordinates(original).values())) == len(active_original),
                    "original_mapping_sha256": digest_bytes(compact_json(canonical_original_mapping)),
                    "compacted_mapping_sha256": digest_bytes(compact_json(canonical_compacted_mapping)),
                },
                "raw_circuit_sha256": {
                    "original": digest_bytes(original_bytes),
                    "compacted": digest_bytes(compacted_bytes),
                    "equal": original_bytes == compacted_bytes,
                },
                "canonical_circuit_sha256": {
                    "original": digest_bytes(canonical_original_bytes),
                    "compacted": digest_bytes(canonical_compacted_bytes),
                    "equal": canonical_original_bytes == canonical_compacted_bytes,
                },
                "detector_error_model_sha256": {
                    "original": digest_bytes(original_dem_bytes),
                    "compacted": digest_bytes(compacted_dem_bytes),
                    "equal": original_dem_bytes == compacted_dem_bytes,
                },
                "fixed_seed_semantic_replay": {
                    "seed": audit["audit_seed"],
                    "shots": audit["audit_shots_per_basis"],
                    "original": original_packet,
                    "compacted": compacted_packet,
                    "detectors_equal": original_packet["detectors_sha256"] == compacted_packet["detectors_sha256"],
                    "observables_equal": original_packet["observables_sha256"] == compacted_packet["observables_sha256"],
                    "predictions_equal": original_packet["predictions_sha256"] == compacted_packet["predictions_sha256"],
                    "failure_vectors_equal": original_packet["failure_vector_sha256"] == compacted_packet["failure_vector_sha256"],
                    "traces_equal": original_packet["trace_sha256"] == compacted_packet["trace_sha256"],
                },
                "challenge_binding_audit": {
                    "raw_original_seed": raw_original_seed,
                    "raw_compacted_seed": raw_compacted_seed,
                    "raw_original_challenge_sha256": raw_original_challenge,
                    "raw_compacted_challenge_sha256": raw_compacted_challenge,
                    "raw_seeds_equal": raw_original_seed == raw_compacted_seed,
                    "canonical_original_seed": canonical_original_seed,
                    "canonical_compacted_seed": canonical_compacted_seed,
                    "canonical_original_challenge_sha256": canonical_original_challenge,
                    "canonical_compacted_challenge_sha256": canonical_compacted_challenge,
                    "canonical_seeds_equal": canonical_original_seed == canonical_compacted_seed,
                },
                "cost_regrade": {
                    "memory_rounds": rounds,
                    "old_index_span_cost": old_cost,
                    "corrected_active_qubit_cost": corrected_cost,
                    "old_over_corrected_factor": old_cost / corrected_cost,
                    "index_only_naive_improvement": old_cost / (compacted.num_qubits * rounds),
                    "index_invariant_improvement": corrected_cost / (len(active_compacted) * rounds),
                },
                "strict_correctness_evidence_unchanged": {
                    "frozen_raw_circuit_sha256_matches": strict_row["circuit_sha256"] == digest_bytes(original_bytes),
                    "frozen_dem_sha256_matches": strict_row["detector_error_model_sha256"] == digest_bytes(original_dem_bytes),
                    "logical_failures": strict_row["logical_failures"],
                    "shots": strict_row["shots"],
                    "clopper_pearson_upper_delta_2m128": strict_row["clopper_pearson_upper_delta_2m128"],
                    "strict_verification_pass": strict_row["strict_verification_pass"],
                },
            }
        )

    reference_costs = {
        row["memory_basis"]: row["cost_regrade"]["corrected_active_qubit_cost"] for row in rows
    }
    old_reference_costs = {
        row["memory_basis"]: row["cost_regrade"]["old_index_span_cost"] for row in rows
    }
    invariant_scores = [row["cost_regrade"]["index_invariant_improvement"] for row in rows]
    naive_scores = [row["cost_regrade"]["index_only_naive_improvement"] for row in rows]
    invariant_composite = math.sqrt(math.prod(invariant_scores))
    naive_composite = math.sqrt(math.prod(naive_scores))
    symmetric_max_cost = min(reference_costs.values()) / 1.25
    symmetric_max_qubits = math.floor(symmetric_max_cost / experiment["rounds"])

    result: dict[str, Any] = {
        "schema_version": "b2_b7_p023_qubit_index_invariance_result_v1",
        "as_of_date": protocol["as_of_date"],
        "question": protocol["question"],
        "scope": scope,
        "protocol_binding": {
            "path": str(protocol_path.relative_to(ROOT)),
            "sha256": digest_path(protocol_path),
        },
        "frozen_inputs_current": frozen_current,
        "frozen_inputs_at_commit": {
            "commit": freeze_commit,
            "bindings": frozen_commit,
        },
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": digest_path(Path(__file__).resolve()),
        },
        "execution_environment": {
            "python": platform.python_version(),
            "stim": stim.__version__,
            "pymatching": pymatching.__version__,
            "numpy": np.__version__,
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "resource_metric_v2": protocol["resource_metric_v2"],
        "challenge_binding_v2": protocol["challenge_binding_v2"],
        "audit_contract": audit,
        "basis_rows": rows,
        "reference_regrade": {
            "old_index_span_cost_by_basis": old_reference_costs,
            "corrected_active_qubit_cost_by_basis": reference_costs,
            "old_pair_cost": sum(old_reference_costs.values()),
            "corrected_pair_cost": sum(reference_costs.values()),
            "normalized_reference_score": 1.0,
            "symmetric_candidate_score_threshold": 1.25,
            "symmetric_candidate_max_cost_per_basis": symmetric_max_cost,
            "symmetric_candidate_max_active_qubits_at_1000_rounds": symmetric_max_qubits,
        },
        "adversarial_relabel_candidate": {
            "semantically_identical": True,
            "naive_label_sensitive_composite_score": naive_composite,
            "index_invariant_composite_score": invariant_composite,
            "accepted_as_b2_improvement": False,
            "reason": "only identifier density changed; the distinct operational-qubit set and all verified behavior are unchanged",
        },
        "readiness": {
            "strict_1k_reference_correctness_remains_verified": True,
            "resource_baseline_v1_label_sensitive": True,
            "resource_baseline_v2_index_invariant": True,
            "b2_candidate_improvement_verified": False,
            "p023_scalable_memory_verified": False,
            "b7_resource_credit": 0,
        },
        "claim_boundary": protocol["claim_boundary"],
        "decision": "qubit_index_loophole_closed_reference_regraded_to_97_active_qubits_b2_p023_b7_credit_closed",
        "next_gate": "Freeze and strictly verify a same-condition candidate before salt reveal; a symmetric 1,000-round candidate needs at most 77 active operational qubits to reach Score_QEC>=1.25.",
    }

    checks: list[dict[str, Any]] = []
    checks.append(check("scope", scope["included_catalog_problem_ids"] == [21, 22, 23] and scope["included_tracks"] == ["B2", "B7"], "Exact scope."))
    checks.append(check("frozen_current", len(frozen_current) == 3, "All frozen inputs match current bytes."))
    checks.append(check("frozen_commit", all(x["matches_protocol_binding"] for x in frozen_commit.values()), f"Freeze commit: {freeze_commit}."))
    checks.append(check("strict_decision", strict_result["decision"] == required_decision, required_decision))
    checks.append(check("strict_pair_gate", strict_result["reference_gate"]["both_bases_strict_pass"], "Frozen strict X/Z reference remains verified."))
    checks.append(check("basis_set", [row["memory_basis"] for row in rows] == ["x", "z"], "X and Z rows are present."))
    checks.append(check("raw_circuit_bindings", all(row["strict_correctness_evidence_unchanged"]["frozen_raw_circuit_sha256_matches"] for row in rows), "Regenerated raw circuits match the strict packet."))
    checks.append(check("dem_bindings", all(row["strict_correctness_evidence_unchanged"]["frozen_dem_sha256_matches"] for row in rows), "Regenerated DEMs match the strict packet."))
    checks.append(check("index_span", all(row["original_index_span_qubits"] == 118 for row in rows), "Stim index span is 118 in both bases."))
    checks.append(check("active_qubits", all(row["original_active_operational_qubits"] == 97 for row in rows), "Exactly 97 operational qubits in both bases."))
    checks.append(check("index_holes", all(row["original_unused_index_slots"] == 21 for row in rows), "There are 21 unused identifier slots."))
    checks.append(check("compact_span", all(row["compacted_index_span_qubits"] == 97 for row in rows), "Compaction reduces only the identifier span to 97."))
    checks.append(check("active_count_invariant", all(row["compacted_active_operational_qubits"] == row["original_active_operational_qubits"] for row in rows), "Operational qubit count is invariant."))
    checks.append(check("raw_bytes_change", all(not row["raw_circuit_sha256"]["equal"] for row in rows), "Raw circuit bytes change under relabeling."))
    checks.append(check("canonical_bytes_equal", all(row["coordinate_canonicalization"]["all_active_qubits_bound"] and row["coordinate_canonicalization"]["unique_active_coordinates"] and row["canonical_circuit_sha256"]["equal"] for row in rows), "Unique coordinate-canonical circuit bytes are identical."))
    checks.append(check("dem_exact", all(row["detector_error_model_sha256"]["equal"] for row in rows), "DEMs are byte-identical."))
    checks.append(check("detectors_exact", all(row["fixed_seed_semantic_replay"]["detectors_equal"] for row in rows), "Fixed-seed detector samples are exact."))
    checks.append(check("observables_exact", all(row["fixed_seed_semantic_replay"]["observables_equal"] for row in rows), "Fixed-seed observables are exact."))
    checks.append(check("predictions_exact", all(row["fixed_seed_semantic_replay"]["predictions_equal"] for row in rows), "MWPM predictions are exact."))
    checks.append(check("failures_exact", all(row["fixed_seed_semantic_replay"]["failure_vectors_equal"] for row in rows), "Logical failure vectors are exact."))
    checks.append(check("trace_exact", all(row["fixed_seed_semantic_replay"]["traces_equal"] for row in rows), "Complete semantic traces are exact."))
    checks.append(check("raw_seed_sensitive", all(not row["challenge_binding_audit"]["raw_seeds_equal"] for row in rows), "Raw-byte challenge seeds change under relabeling."))
    checks.append(check("canonical_seed_invariant", all(row["challenge_binding_audit"]["canonical_seeds_equal"] for row in rows), "Canonical challenge seeds are invariant."))
    checks.append(check("cost_regrade", reference_costs == {"x": 97000, "z": 97000}, str(reference_costs)))
    checks.append(check("pair_cost_regrade", result["reference_regrade"]["corrected_pair_cost"] == 194000, "Pair cost is 194,000 active-qubit-rounds."))
    checks.append(check("naive_gaming_score", all(abs(x - 118 / 97) < 1e-15 for x in naive_scores), f"Naive score: {naive_composite}."))
    checks.append(check("invariant_relabel_score", invariant_composite == 1.0, "Index-only candidate scores 1.0."))
    checks.append(check("candidate_boundary", result["reference_regrade"]["symmetric_candidate_max_active_qubits_at_1000_rounds"] == 77, "Symmetric threshold is at most 77 active qubits."))
    checks.append(check("readiness_boundary", not result["readiness"]["b2_candidate_improvement_verified"] and not result["readiness"]["p023_scalable_memory_verified"] and result["readiness"]["b7_resource_credit"] == 0, "B2/#023/B7 remain closed."))
    checks.append(check("claim_boundary", not any(protocol["claim_boundary"][key] for key in ["new_code_claimed", "b2_low_overhead_improvement_claimed", "scalable_quantum_memory_claimed", "b7_resource_credit_claimed", "hardware_result_claimed", "official_kaggle_metric_claimed"]), "No out-of-scope claim."))
    result["formal_checks"] = checks
    result["summary"] = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "index_span_qubits": 118,
        "active_operational_qubits": 97,
        "unused_index_slots": 21,
        "corrected_cost_per_basis": 97000,
        "corrected_pair_cost": 194000,
        "index_only_naive_score": naive_composite,
        "index_only_invariant_score": invariant_composite,
    }
    result["run_id"] = digest_bytes(compact_json({k: v for k, v in result.items() if k != "run_id"}))
    if result["summary"]["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"formal checks failed: {failed}")
    return result


def build_report(result: dict[str, Any]) -> str:
    x, z = result["basis_rows"]
    reference = result["reference_regrade"]
    adversary = result["adversarial_relabel_candidate"]
    return "\n".join(
        [
            "# B2/B7/#023 Qubit-Index Invariance Audit v1",
            "",
            f"As of {result['as_of_date']}. Scope is exactly #021/B7, #022/B2, and #023.",
            "",
            "## Heuristic question",
            "",
            "If the physical circuit is unchanged, should replacing sparse qubit identifiers with 0..96 earn a resource improvement? The answer must be no; otherwise the score rewards serialization rather than hardware.",
            "",
            "## Finding",
            "",
            "The strict distance-7 Stim circuits report `num_qubits=118`, but only 97 distinct qubit identifiers occur in operational instructions. The other 21 positions are holes in the identifier span. Therefore the previous `118×1,000` resource proxy was label-sensitive and is regraded; its correctness evidence is unchanged.",
            "",
            "| basis | index span | active operational qubits | holes | old cost | corrected cost | canonical circuit | DEM | 8,192-shot replay |",
            "|---|---:|---:|---:|---:|---:|---|---|---|",
            f"| X | {x['original_index_span_qubits']} | {x['original_active_operational_qubits']} | {x['original_unused_index_slots']} | {x['cost_regrade']['old_index_span_cost']:,} | {x['cost_regrade']['corrected_active_qubit_cost']:,} | exact | exact | exact |",
            f"| Z | {z['original_index_span_qubits']} | {z['original_active_operational_qubits']} | {z['original_unused_index_slots']} | {z['cost_regrade']['old_index_span_cost']:,} | {z['cost_regrade']['corrected_active_qubit_cost']:,} | exact | exact | exact |",
            "",
            "Compaction changes raw circuit bytes and raw-byte-derived seeds, but the canonical compact circuit, detector error model, fixed-seed detector/observable samples, MWPM predictions, and failure vectors are exact matches in both bases.",
            "",
            "## Corrected baseline",
            "",
            f"The verified reference is now `Q_active×H = 97×1,000 = {reference['corrected_active_qubit_cost_by_basis']['x']:,}` active-qubit-rounds per basis and {reference['corrected_pair_cost']:,} for the X/Z pair. Its normalized score remains 1.0.",
            "",
            f"A relabeled copy would appear to score {adversary['naive_label_sensitive_composite_score']:.9f} under the old label-sensitive count, but correctly scores {adversary['index_invariant_composite_score']:.1f} and earns no B2 improvement under v2.",
            "",
            "For a symmetric 1,000-round candidate, `Score_QEC>=1.25` now requires at most 77 active operational qubits, plus strict X/Z correctness and no weakened assumptions.",
            "",
            "## Verifier rule v2",
            "",
            "1. Count distinct qubits targeted by operational instructions; ignore QUBIT_COORDS-only identifiers.",
            "2. Canonically order active qubits by unique QUBIT_COORDS tuples before resource hashing and challenge binding; reject missing or duplicate bindings.",
            "3. Treat `circuit.num_qubits` only as an index-span diagnostic.",
            "4. Give index-only transformations score 1.0, never resource credit.",
            "5. Keep correctness as a hard gate before the corrected cost score.",
            "",
            "## Claim boundary",
            "",
            "This corrects the resource baseline; it does not change the strict 1,000-round logical-error result. It does not establish a new code, B2 improvement, scalable #023 memory, hardware performance, or B7 credit.",
            "",
            f"Formal checks: **{result['summary']['checks_passed']}/{result['summary']['checks_total']}**. Run ID: `{result['run_id']}`.",
            "",
            "## Next falsifier",
            "",
            result["next_gate"],
            "",
        ]
    )


def build_discussion(result: dict[str, Any]) -> str:
    score = result["adversarial_relabel_candidate"]["naive_label_sensitive_composite_score"]
    return "\n".join(
        [
            "Can renaming qubits count as a quantum-error-correction breakthrough?",
            "",
            "Our verifier just caught a resource-accounting trap in #021/B7 · #022/B2 · #023.",
            "",
            "The verified distance-7 memory circuit has `num_qubits=118`, but only 97 identifiers are used by operational instructions. Twenty-one slots are merely holes in Stim's index space. Compacting those labels to 0..96 leaves the detector error model, 8,192 fixed-seed samples per basis, MWPM predictions, and logical failure vectors exactly unchanged.",
            "",
            f"A naive `num_qubits×rounds` score would award this no-op a **{score:.4f}× improvement**. That is not hardware progress; it is a serialization artifact.",
            "",
            "We therefore regraded the fixed reference from 118,000 to **97,000 active-qubit-rounds per basis**, retained normalized score 1.0, and changed future challenge binding to a canonical compact circuit. Under the 1.25 acceptance threshold, a symmetric 1,000-round candidate now needs at most 77 active operational qubits and must still pass strict X and Z correctness.",
            "",
            "Questions for critique:",
            "",
            "- Is distinct operational-qubit count sufficient, or should the next metric use peak simultaneously live qubits?",
            "- Should layout area and inactive coupler sites count even when no gate targets them?",
            "- Which other compiler metadata can create resource-score loopholes without changing physics?",
            "- Can a candidate with ≤77 active qubits pass the same 1,000-round, `1-2^-128` X/Z gate?",
            "",
            "Current boundary: strict correctness remains verified; no B2 candidate improvement exists; #023 scalable memory remains false; B7 resource credit remains zero.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--output", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    protocol = read(args.protocol)
    result = build_result(protocol, args.protocol)
    args.output.write_text(canonical(result), encoding="utf-8")
    args.report.write_text(build_report(result), encoding="utf-8")
    args.discussion.write_text(build_discussion(result), encoding="utf-8")
    print(canonical(result["summary"]).strip())


if __name__ == "__main__":
    main()
