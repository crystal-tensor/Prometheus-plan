#!/usr/bin/env python3
"""Freeze a correlation-aware decoder route before any stochastic QEC shot."""

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

import b2_b7_p023_d6_candidate_freeze as base


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_correlated_decoder_freeze_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_correlated_decoder_freeze_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_correlated_decoder_freeze_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_d6_correlated_decoder_freeze_discussion_v1.md"


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


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def decomposition_inventory(dem: stim.DetectorErrorModel) -> dict[str, int]:
    error_instructions = 0
    decomposed_hyperedge_instructions = 0
    decomposed_components = 0
    max_detectors_per_component = 0
    components_with_observable = 0
    for instruction in dem.flattened():
        if instruction.type != "error":
            continue
        error_instructions += 1
        groups: list[list[stim.DemTarget]] = [[]]
        for target in instruction.targets_copy():
            if target.is_separator():
                groups.append([])
            else:
                groups[-1].append(target)
        if len(groups) > 1:
            decomposed_hyperedge_instructions += 1
            decomposed_components += len(groups)
        for group in groups:
            detector_count = sum(target.is_relative_detector_id() for target in group)
            observable_count = sum(target.is_logical_observable_id() for target in group)
            max_detectors_per_component = max(max_detectors_per_component, detector_count)
            components_with_observable += int(observable_count > 0)
    return {
        "error_instructions": error_instructions,
        "decomposed_hyperedge_instructions": decomposed_hyperedge_instructions,
        "decomposed_components": decomposed_components,
        "max_detectors_per_component": max_detectors_per_component,
        "components_with_observable": components_with_observable,
    }


def zero_syndrome_sanity(
    matching: pymatching.Matching,
    detector_count: int,
) -> dict[str, Any]:
    packed = np.zeros((1, math.ceil(detector_count / 8)), dtype=np.uint8)
    prediction = matching.decode_batch(
        packed,
        bit_packed_shots=True,
        bit_packed_predictions=True,
        enable_correlations=True,
    )
    return {
        "input_shape": list(packed.shape),
        "prediction_shape": list(prediction.shape),
        "prediction_sha256": digest_bytes(prediction.tobytes(order="C")),
        "prediction_nonzero_bytes": int(np.count_nonzero(prediction)),
    }


def build_result(protocol: dict[str, Any], protocol_path: Path) -> dict[str, Any]:
    if protocol["scope"]["included_catalog_problem_ids"] != [21, 22, 23]:
        raise ValueError("scope mismatch")
    freeze_commit = protocol["frozen_inputs"]["artifact_freeze_commit"]
    current_bindings: dict[str, Any] = {}
    commit_bindings: dict[str, Any] = {}
    for name, binding in protocol["frozen_inputs"].items():
        if name == "artifact_freeze_commit":
            continue
        path = ROOT / binding["path"]
        current_sha = digest_path(path)
        if current_sha != binding["sha256"]:
            raise ValueError(f"current frozen input mismatch: {name}")
        commit_bytes = subprocess.check_output(
            ["git", "show", f"{freeze_commit}:{binding['path']}"],
            cwd=ROOT,
        )
        commit_sha = digest_bytes(commit_bytes)
        if commit_sha != binding["sha256"]:
            raise ValueError(f"commit frozen input mismatch: {name}")
        current_bindings[name] = {"path": binding["path"], "sha256": current_sha}
        commit_bindings[name] = {
            "path": binding["path"],
            "sha256": commit_sha,
            "matches": True,
        }

    metric = read(ROOT / protocol["frozen_inputs"]["index_invariance_result"]["path"])
    reference = read(ROOT / protocol["frozen_inputs"]["strict_reference_result"]["path"])
    rejected = read(
        ROOT / protocol["frozen_inputs"]["independent_decoder_rejection_result"]["path"]
    )
    if metric["decision"] != protocol["frozen_inputs"]["index_invariance_result"]["required_decision"]:
        raise ValueError("metric decision mismatch")
    if reference["decision"] != protocol["frozen_inputs"]["strict_reference_result"]["required_decision"]:
        raise ValueError("reference decision mismatch")
    if rejected["decision"] != protocol["frozen_inputs"]["independent_decoder_rejection_result"]["required_decision"]:
        raise ValueError("rejected-route decision mismatch")

    prior_rows = {row["memory_basis"]: row for row in rejected["candidate_rows"]}
    candidate = protocol["candidate"]
    rows: list[dict[str, Any]] = []
    for basis in candidate["memory_bases"]:
        circuit = base.build_circuit(basis, candidate)
        canonical_circuit, mapping = base.coordinate_canonical(circuit)
        dem = circuit.detector_error_model(decompose_errors=True)
        matching = pymatching.Matching.from_detector_error_model(
            dem,
            enable_correlations=True,
        )
        active = base.active_ids(circuit)
        coords = base.coordinates(circuit)
        inventory = decomposition_inventory(dem)
        zero_sanity = zero_syndrome_sanity(matching, circuit.num_detectors)
        previous = prior_rows[basis]
        row = {
            "memory_basis": basis,
            "distance": candidate["distance"],
            "rounds": candidate["rounds"],
            "physical_error": candidate["physical_error"],
            "index_span_qubits": circuit.num_qubits,
            "active_operational_qubits": len(active),
            "unused_index_slots": circuit.num_qubits - len(active),
            "active_ids_sha256": digest_bytes(compact(active)),
            "coordinate_count": len(coords),
            "unique_coordinate_count": len(set(coords.values())),
            "coordinate_mapping_sha256": digest_bytes(compact(mapping)),
            "raw_circuit_sha256": digest_bytes(str(circuit).encode()),
            "coordinate_canonical_circuit_sha256": digest_bytes(
                str(canonical_circuit).encode()
            ),
            "detector_error_model_sha256": digest_bytes(str(dem).encode()),
            "circuit_exactly_matches_rejected_route": (
                digest_bytes(str(circuit).encode()) == previous["raw_circuit_sha256"]
            ),
            "canonical_circuit_exactly_matches_rejected_route": (
                digest_bytes(str(canonical_circuit).encode())
                == previous["coordinate_canonical_circuit_sha256"]
            ),
            "detector_error_model_exactly_matches_rejected_route": (
                digest_bytes(str(dem).encode())
                == previous["detector_error_model_sha256"]
            ),
            "detectors": circuit.num_detectors,
            "observables": circuit.num_observables,
            "matching_nodes": matching.num_nodes,
            "matching_edges": matching.num_edges,
            "matching_fault_ids": matching.num_fault_ids,
            "correlations_enabled_at_construction": True,
            "correlations_required_at_decode": True,
            "decomposition_inventory": inventory,
            "zero_syndrome_sanity": zero_sanity,
            "cost_active_qubit_rounds": len(active) * candidate["rounds"],
            "conditional_basis_improvement": 97000 / (len(active) * candidate["rounds"]),
            "stochastic_shots": 0,
            "logical_failures_observed": None,
            "acceptance_seed": None,
            "strict_verification_pass": None,
        }
        rows.append(row)

    conditional_score = math.sqrt(
        math.prod(row["conditional_basis_improvement"] for row in rows)
    )
    result: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_correlated_decoder_freeze_result_v1",
        "as_of_date": protocol["as_of_date"],
        "question": protocol["question"],
        "scope": protocol["scope"],
        "protocol_binding": {
            "path": str(protocol_path.relative_to(ROOT)),
            "sha256": digest_path(protocol_path),
        },
        "frozen_inputs_current": current_bindings,
        "frozen_inputs_at_commit": {
            "commit": freeze_commit,
            "bindings": commit_bindings,
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
        "selection_rule": candidate["selection_rule"],
        "prior_independent_decoder_result": {
            "decision": rejected["decision"],
            "accepted_score": rejected["score"]["accepted_composite_score"],
            "both_bases_strict_pass": rejected["score"]["both_bases_strict_pass"],
            "known_before_new_route_selection": True,
            "correlated_route_outcomes_known": False,
        },
        "candidate": candidate,
        "candidate_rows": rows,
        "conditional_resource_score": {
            "reference_cost_per_basis": 97000,
            "candidate_cost_per_basis": 71000,
            "basis_improvement": {
                row["memory_basis"]: row["conditional_basis_improvement"] for row in rows
            },
            "composite_score_if_both_bases_verify": conditional_score,
            "acceptance_threshold": 1.25,
            "resource_threshold_cleared_conditionally": conditional_score >= 1.25,
            "correctness_gate_pending": True,
            "accepted_score_before_correctness": 0,
        },
        "post_freeze_acceptance_contract": protocol["post_freeze_acceptance_contract"],
        "pre_outcome_integrity": protocol["pre_outcome_integrity"],
        "readiness": {
            "candidate_structure_frozen": True,
            "candidate_public_freeze_commit_pending": True,
            "acceptance_salt_revealed": False,
            "candidate_correctness_tested": False,
            "candidate_accepted": False,
            "b2_physical_memory_gate_verified": False,
            "b2_full_credit": False,
            "p023_scalable_memory_verified": False,
            "b7_resource_credit": 0,
        },
        "claim_boundary": protocol["claim_boundary"],
        "decision": "d6_two_pass_correlated_decoder_structurally_frozen_before_salt_no_outcome_b2_p023_b7_credit_closed",
        "next_gate": "Commit and publicly discuss this exact no-outcome packet, bind the public freeze commit and discussion into a new salt, then execute exactly 102,400 correlated-decoder shots per basis without changing the route or thresholds.",
    }

    checks: list[dict[str, Any]] = []
    checks.append(check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23] and protocol["scope"]["included_tracks"] == ["B2", "B7"], "Exact scope."))
    checks.append(check("frozen_current", len(current_bindings) == 5, "Five frozen inputs match."))
    checks.append(check("frozen_commit", all(binding["matches"] for binding in commit_bindings.values()), freeze_commit))
    checks.append(check("metric_decision", metric["decision"] == protocol["frozen_inputs"]["index_invariance_result"]["required_decision"], metric["decision"]))
    checks.append(check("strict_reference", reference["reference_gate"]["both_bases_strict_pass"], "Strict distance-7 reference passed both bases."))
    checks.append(check("prior_route_rejected", not rejected["score"]["both_bases_strict_pass"] and rejected["score"]["accepted_composite_score"] == 0, rejected["decision"]))
    checks.append(check("candidate_bases", [row["memory_basis"] for row in rows] == ["x", "z"], "X and Z are frozen."))
    checks.append(check("candidate_geometry", all(row["distance"] == 6 and row["rounds"] == 1000 for row in rows), "Distance 6, exactly 1,000 rounds."))
    checks.append(check("active_qubits", all(row["active_operational_qubits"] == 71 for row in rows), "71 active operational qubits per basis."))
    checks.append(check("candidate_cost", all(row["cost_active_qubit_rounds"] == 71000 for row in rows), "71,000 active-qubit-rounds per basis."))
    checks.append(check("only_decoder_changed", all(row["circuit_exactly_matches_rejected_route"] and row["canonical_circuit_exactly_matches_rejected_route"] and row["detector_error_model_exactly_matches_rejected_route"] for row in rows), "Circuit and DEM bytes exactly match the rejected route."))
    checks.append(check("correlations_enabled", all(row["correlations_enabled_at_construction"] and row["correlations_required_at_decode"] for row in rows), "Correlation-aware construction and decoding are frozen."))
    checks.append(check("decomposable_hyperedges_exist", all(row["decomposition_inventory"]["decomposed_hyperedge_instructions"] > 0 for row in rows), str([row["decomposition_inventory"]["decomposed_hyperedge_instructions"] for row in rows])))
    checks.append(check("graphlike_components", all(row["decomposition_inventory"]["max_detectors_per_component"] <= 2 for row in rows), "Every suggested component is graphlike."))
    checks.append(check("zero_syndrome_api", all(row["zero_syndrome_sanity"]["prediction_nonzero_bytes"] == 0 for row in rows), "All-zero syndromes decode to all-zero predictions."))
    checks.append(check("conditional_score", abs(conditional_score - 97 / 71) < 1e-15 and conditional_score >= 1.25, str(conditional_score)))
    checks.append(check("no_shots", all(row["stochastic_shots"] == 0 for row in rows) and protocol["pre_outcome_integrity"]["candidate_stochastic_shots_before_freeze"] == 0, "No stochastic candidate shots."))
    checks.append(check("no_outcome", all(row["logical_failures_observed"] is None and row["strict_verification_pass"] is None for row in rows), "No correlated-route outcome observed."))
    checks.append(check("no_seed", all(row["acceptance_seed"] is None for row in rows) and not protocol["post_freeze_acceptance_contract"]["seed_present_in_freeze_packet"], "No acceptance seed."))
    checks.append(check("no_salt", not protocol["post_freeze_acceptance_contract"]["salt_present_in_freeze_packet"], "No acceptance salt."))
    checks.append(check("zero_pre_correctness_score", result["conditional_resource_score"]["accepted_score_before_correctness"] == 0, "Score remains zero before correctness."))
    checks.append(check("candidate_unaccepted", not result["readiness"]["candidate_accepted"] and not result["readiness"]["b2_physical_memory_gate_verified"] and not result["readiness"]["b2_full_credit"], "Candidate and B2 gates remain unaccepted."))
    checks.append(check("downstream_closed", not result["readiness"]["p023_scalable_memory_verified"] and result["readiness"]["b7_resource_credit"] == 0, "#023 and B7 remain closed."))
    checks.append(check("claim_boundary", not any(protocol["claim_boundary"].values()), "No positive claim before execution."))
    result["formal_checks"] = checks
    result["summary"] = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "candidate_active_qubits": 71,
        "candidate_cost_per_basis": 71000,
        "conditional_score": conditional_score,
        "decomposed_hyperedge_instructions": {
            row["memory_basis"]: row["decomposition_inventory"]["decomposed_hyperedge_instructions"] for row in rows
        },
        "stochastic_shots_before_freeze": 0,
        "candidate_correctness_tested": False,
        "candidate_accepted": False,
    }
    result["run_id"] = digest_bytes(compact({key: value for key, value in result.items() if key != "run_id"}))
    if result["summary"]["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"correlated-decoder freeze checks failed: {failed}")
    return result


def build_report(result: dict[str, Any]) -> str:
    x, z = result["candidate_rows"]
    score = result["conditional_resource_score"]["composite_score_if_both_bases_verify"]
    return "\n".join(
        [
            "# B2/B7/#023 Distance-6 Correlated-Decoder Freeze v1",
            "",
            f"As of {result['as_of_date']}. Scope is exactly #021/B7, #022/B2, and #023.",
            "",
            "## Heuristic question",
            "",
            "Can correlations rescue a 1.366× cheaper memory that independent matching rejected? This packet freezes the decoder change before the correlated route sees one stochastic syndrome.",
            "",
            "## One change, publicly frozen",
            "",
            "The distance-6 circuit, 71 active qubits, 1,000-round horizon, physical error 0.001, four circuit-level noise channels, DEM, 1% target, and `1-2^-128` confidence contract are byte-for-byte unchanged. The only candidate change is enabling PyMatching 2.4.0 two-pass correlated matching at graph construction and decoding.",
            "",
            "| basis | decomposed hyperedge instructions | components | max detectors/component | matching nodes | matching edges | stochastic shots |",
            "|---|---:|---:|---:|---:|---:|---:|",
            f"| X | {x['decomposition_inventory']['decomposed_hyperedge_instructions']:,} | {x['decomposition_inventory']['decomposed_components']:,} | {x['decomposition_inventory']['max_detectors_per_component']} | {x['matching_nodes']:,} | {x['matching_edges']:,} | 0 |",
            f"| Z | {z['decomposition_inventory']['decomposed_hyperedge_instructions']:,} | {z['decomposition_inventory']['decomposed_components']:,} | {z['decomposition_inventory']['max_detectors_per_component']} | {z['matching_nodes']:,} | {z['matching_edges']:,} | 0 |",
            "",
            "Stim's suggested decompositions preserve correlation groups with separators; PyMatching's two-pass mode can use those groups when reweighting its second matching pass. Their presence makes the decoder route structurally non-vacuous, but says nothing yet about its logical failure rate.",
            "",
            f"If—and only if—both X and Z pass after the public freeze, the physical-memory score is `97/71 = {score:.9f}`. Before correctness, the accepted score remains 0.",
            "",
            "## What is deliberately absent",
            "",
            "- stochastic correlated-decoder shots: 0",
            "- correlated-route logical failures: none observed",
            "- acceptance salt or seed: absent",
            "- candidate pass/fail decision: absent",
            "- hardware decoder deadline or production-runtime claim: absent",
            "",
            "The all-zero syndrome API sanity check is deterministic and contains no sampled detector or logical outcome.",
            "",
            "## Post-freeze gate",
            "",
            "After this exact packet is committed and publicly discussed, a new salt will be bound to that publication. Exactly 102,400 shots per basis will be decoded with correlations enabled. Both strict upper bounds must be at most 1%; otherwise the score is zero. Same-host batch timing will be reported but cannot stand in for a hardware deadline.",
            "",
            "## Claim boundary",
            "",
            "This is a no-outcome decoder preregistration. It is not an accepted B2 improvement, scalable #023 memory, hardware result, production decoder, threshold result, or B7 resource credit.",
            "",
            f"Formal checks: **{result['summary']['checks_passed']}/{result['summary']['checks_total']}**. Run ID: `{result['run_id']}`.",
            "",
            "Structural references: [PyMatching correlation-aware decoding](https://github.com/oscarhiggott/PyMatching/blob/master/src/pymatching/matching.py); [Stim detector-error-model separators](https://github.com/quantumlib/Stim/blob/main/doc/file_format_dem_detector_error_model.md).",
            "",
        ]
    )


def build_discussion(result: dict[str, Any]) -> str:
    x, z = result["candidate_rows"]
    score = result["conditional_resource_score"]["composite_score_if_both_bases_verify"]
    return "\n".join(
        [
            "Can correlations rescue a cheaper quantum memory after ordinary matching says no?",
            "",
            "The 71-active-qubit distance-6 memory lost its first strict trial: independent MWPM could not keep either X or Z below the 1% ceiling. The tempting response is to rerun until luck changes. We are taking a falsifiable route instead—freeze a genuinely different decoder before it sees any new sample.",
            "",
            "The circuit and physics are unchanged. PyMatching's two-pass correlated mode is the sole change. This is not a cosmetic switch: the frozen X and Z DEMs contain **{:,.0f}** and **{:,.0f}** decomposed-hyperedge instructions, respectively, which the second matching pass can use for correlation-aware reweighting.".format(x["decomposition_inventory"]["decomposed_hyperedge_instructions"], z["decomposition_inventory"]["decomposed_hyperedge_instructions"]),
            "",
            f"The reward, if both bases strictly pass, is still **97/71 = {score:.4f}×** physical-memory improvement. If either fails, the accepted score is zero.",
            "",
            "At this public-freeze stage:",
            "",
            "- correlated-decoder stochastic shots: 0",
            "- observed correlated-route failures: none",
            "- acceptance salt and seeds: absent",
            "- full B2, #023, and B7 credit: closed",
            "",
            "Questions worth arguing about before execution:",
            "",
            "- Is exploiting decomposed Y-error correlations a fair decoder improvement, or does it hide classical complexity that should be priced explicitly?",
            "- Should a slower decoder be allowed to buy a 26-qubit reduction if it still meets a declared real-time deadline?",
            "- If the strict result still fails, does that falsify the decoder route—or the entire 71-qubit target under this noise model?",
            "- What runtime metric would make physical-qubit savings and classical decoding cost genuinely comparable?",
            "",
            "Next, and only after publication: reveal a commit-bound salt and run exactly 102,400 X plus 102,400 Z shots under the frozen correlated decoder.",
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
    result = build_result(read(args.protocol), args.protocol)
    args.output.write_text(canonical(result), encoding="utf-8")
    args.report.write_text(build_report(result), encoding="utf-8")
    args.discussion.write_text(build_discussion(result), encoding="utf-8")
    print(canonical(result["summary"]).strip())


if __name__ == "__main__":
    main()
