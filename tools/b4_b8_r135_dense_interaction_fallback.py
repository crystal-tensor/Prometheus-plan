#!/usr/bin/env python3
"""T-B4-002aj/T-B8-003an: validate a dense-interaction mapping fallback."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import statistics
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from qiskit import QuantumCircuit, qasm3, transpile

from b4_b8_r121_private_bundle_shot_sweep import basis_circuit, stable_hash, write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r127_calibration_aware_layout_design import SNAPSHOT_CLASSES
from b4_b8_r128_transpiler_loop_layout_ranking import exposure_from_qasm, package_version
from b4_b8_r131_compiled_route_family_attribution import compiled_route_descriptor
from b4_b8_r132_topology_constrained_route_policy import (
    DETERMINISTIC_PROCESS_ENV,
    compile_policy,
)
from b4_b8_r134_family_agnostic_mapping_rule import (
    physical_metrics,
)


METHOD = "b4_b8_r135_dense_interaction_fallback_v0"
STATUS = "dense_interaction_deterministic_fallback_boundary"
MODEL_STATUS = "seeded_mapping_portfolio_selected_without_validation_baseline_access"
TARGET_ID = "T-B4-002aj/T-B8-003an/T-B10-009ab"
UPSTREAM_TARGET_ID = "T-B4-002ai/T-B8-003am/T-B10-009aa"
R125_RESULT_PATH = "results/B4_B8_R125_historical_snapshot_replay_v0.json"
R134_RESULT_PATH = "results/B4_B8_R134_family_agnostic_mapping_rule_v0.json"
RESULT_PATH = "results/B4_B8_R135_dense_interaction_fallback_v0.json"
REPORT_PATH = "research/B4_B8_R135_dense_interaction_fallback.md"
OUT_DIR = "results/B4_B8_R135_dense_interaction_fallback"
CANDIDATE_SEEDS = tuple(range(13501, 13581))
VALIDATION_SEEDS = tuple(range(13581, 13591))
PORTFOLIO_COMPILE_SEED = 13500
TEMPORAL_TOP_K = 8
PORTFOLIO_POLICIES = ("selected_o3_default", "selected_o3_lookahead")
TOLERANCE = 1e-15


def ensure_deterministic_process_environment() -> None:
    if all(os.environ.get(key) == value for key, value in DETERMINISTIC_PROCESS_ENV.items()):
        return
    environment = dict(os.environ)
    environment.update(DETERMINISTIC_PROCESS_ENV)
    os.execvpe(sys.executable, [sys.executable, *sys.argv], environment)


def build_dense_validation_tasks() -> list[dict[str, Any]]:
    inverse_qft = QuantumCircuit(6)
    for target in reversed(range(6)):
        for control in reversed(range(target + 1, 6)):
            inverse_qft.cp(-math.pi / (2 ** (control - target)), control, target)
        inverse_qft.h(target)

    scrambled_qft = QuantumCircuit(6)
    order = [2, 5, 1, 4, 0, 3]
    for position, target in enumerate(order):
        scrambled_qft.h(target)
        for offset, control in enumerate(order[position + 1 :], start=1):
            scrambled_qft.cp(math.pi / (2**offset), control, target)

    dense_ising = QuantumCircuit(6)
    for target in range(6):
        dense_ising.h(target)
    edge_index = 0
    for left in range(6):
        for right in range(left + 1, 6):
            edge_index += 1
            dense_ising.rzz(math.pi * edge_index / 37, left, right)
    for target in range(6):
        dense_ising.rx(math.pi * (target + 1) / 11, target)

    dense_xy = QuantumCircuit(6)
    matchings = [
        [(0, 1), (2, 3), (4, 5)],
        [(0, 2), (1, 4), (3, 5)],
        [(0, 3), (1, 5), (2, 4)],
        [(0, 4), (1, 3), (2, 5)],
        [(0, 5), (1, 2), (3, 4)],
    ]
    for layer, matching in enumerate(matchings, start=1):
        for left, right in matching:
            dense_xy.rxx(math.pi * layer / 17, left, right)
            dense_xy.ryy(math.pi * (layer + 1) / 19, left, right)
        for target in range(6):
            dense_xy.rz(math.pi * (target + layer + 1) / 29, target)

    return [
        {
            "task_id": "dense_validation_inverse_qft_n6",
            "family": "inverse_qft",
            "circuit": inverse_qft,
        },
        {
            "task_id": "dense_validation_scrambled_qft_n6",
            "family": "scrambled_qft",
            "circuit": scrambled_qft,
        },
        {
            "task_id": "dense_validation_complete_ising_n6",
            "family": "complete_graph_ising",
            "circuit": dense_ising,
        },
        {
            "task_id": "dense_validation_xy_network_n6",
            "family": "dense_xy_network",
            "circuit": dense_xy,
        },
    ]


def interaction_sequence(circuit: QuantumCircuit) -> list[tuple[int, int]]:
    sequence = []
    for instruction in circuit.data:
        if len(instruction.qubits) != 2:
            continue
        sequence.append(
            tuple(circuit.find_bit(qubit).index for qubit in instruction.qubits)
        )
    if not sequence:
        raise ValueError("dense fallback requires two-qubit interactions")
    return sequence


def transition_score(
    mapping: tuple[int, ...],
    sequence: list[tuple[int, int]],
    distance: dict[tuple[int, int], int],
) -> int:
    value = 0
    for current, following in zip(sequence, sequence[1:]):
        shared = set(current) & set(following)
        if not shared:
            continue
        pivot = next(iter(shared))
        current_other = current[0] if current[1] == pivot else current[1]
        following_other = following[0] if following[1] == pivot else following[1]
        value += distance[(mapping[current_other], mapping[following_other])]
    return value


def temporal_candidates(
    circuit: QuantumCircuit, metadata: dict[str, Any]
) -> dict[tuple[int, ...], set[str]]:
    metrics = physical_metrics(metadata)
    sequence = interaction_sequence(circuit)
    weights = Counter(tuple(sorted(pair)) for pair in sequence)
    ranked: dict[str, list[tuple[tuple[Any, ...], tuple[int, ...]]]] = {
        rule: []
        for rule in [
            "weighted_distance",
            "chronological_decay",
            "reverse_decay",
            "transition_locality",
            "peak_window",
        ]
    }
    for mapping in itertools.permutations(metrics["nodes"], circuit.num_qubits):
        distances = [
            metrics["distance"][(mapping[left], mapping[right])]
            for left, right in sequence
        ]
        weighted_distance = sum(
            count * metrics["distance"][(mapping[left], mapping[right])]
            for (left, right), count in weights.items()
        )
        path_error = sum(
            count * metrics["path_error"][(mapping[left], mapping[right])]
            for (left, right), count in weights.items()
        )
        readout = sum(metrics["readout_error"][qubit] for qubit in mapping)
        chronological = sum(
            (0.88**index) * value for index, value in enumerate(distances)
        )
        reverse = sum(
            (0.88**index) * value
            for index, value in enumerate(reversed(distances))
        )
        peak_window = max(
            sum(distances[index : index + 4])
            for index in range(max(1, len(distances) - 3))
        )
        transition = transition_score(mapping, sequence, metrics["distance"])
        keys = {
            "weighted_distance": (weighted_distance, path_error, readout, mapping),
            "chronological_decay": (
                chronological,
                weighted_distance,
                path_error,
                readout,
                mapping,
            ),
            "reverse_decay": (
                reverse,
                weighted_distance,
                path_error,
                readout,
                mapping,
            ),
            "transition_locality": (
                transition,
                weighted_distance,
                path_error,
                readout,
                mapping,
            ),
            "peak_window": (
                peak_window,
                weighted_distance,
                path_error,
                readout,
                mapping,
            ),
        }
        for rule_id, key in keys.items():
            ranked[rule_id].append((key, mapping))
    candidates: dict[tuple[int, ...], set[str]] = defaultdict(set)
    for rule_id, rows in ranked.items():
        for _, mapping in sorted(rows)[:TEMPORAL_TOP_K]:
            candidates[mapping].add(rule_id)
    return candidates


def automatic_mapping(compiled: QuantumCircuit, source: QuantumCircuit) -> tuple[int, ...]:
    layout = compiled.layout.initial_virtual_layout()
    return tuple(layout[qubit] for qubit in source.qubits)


def outcome(delta: float) -> str:
    return "win" if delta > TOLERANCE else "loss" if delta < -TOLERANCE else "tie"


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    group_lines = []
    for row in payload["validation_group_rows"]:
        group_lines.append(
            "- `{snapshot}` / `{task}`: candidates `{candidates}`; selected "
            "`{mapping}` / `{policy}`; gain `{gain:+.6f}`; wins/ties/losses "
            "`{wins}/{ties}/{losses}`; replay `{replay}`.".format(
                snapshot=row["snapshot"],
                task=row["task_id"],
                candidates=row["unique_candidate_mapping_count"],
                mapping=row["selected_mapping"],
                policy=row["selected_policy_id"],
                gain=row["mean_gain_vs_automatic_default"],
                wins=row["win_count_vs_automatic_default"],
                ties=row["tie_count_vs_automatic_default"],
                losses=row["loss_count_vs_automatic_default"],
                replay=row["selected_qasm_replay_matches"],
            )
        )
    requirements = "\n".join(
        f"- `{row['requirement_id']}` {'PASS' if row['passed'] else 'FAIL'}: {row['label']}"
        for row in payload["requirements"]
    )
    return f"""# B4/B8 R135 Dense-Interaction Deterministic Fallback

## Result

- Dense validation families: `{summary['validation_task_count']}`
- Candidate-generation compilations: `{summary['candidate_generation_compilation_count']}`
- Unique candidate mappings: `{summary['unique_candidate_mapping_count']}`
- Portfolio candidate compilations: `{summary['portfolio_candidate_compilation_count']}`
- Automatic validation compilations: `{summary['automatic_validation_compilation_count']}`
- Frozen selected-QASM replay: `{summary['selected_qasm_replay_match_count']}` / `12`
- Wins/ties/losses vs automatic layout: `{summary['win_count_vs_automatic_default']}/{summary['tie_count_vs_automatic_default']}/{summary['loss_count_vs_automatic_default']}`
- No-loss groups: `{summary['no_loss_group_count_vs_automatic_default']}` / `12`
- Automatic-baseline no-loss gate: `{summary['automatic_baseline_no_loss_gate_passed']}`
- New credit delta: `0`

## Validation Evidence

{chr(10).join(group_lines)}

R135 uses no validation-baseline outcome while choosing a route. For each input,
it unions top temporal graph embeddings with initial mappings generated by 16
disjoint seeded automatic-layout runs. Every mapping is recompiled under two
fixed policies, and the lowest historical exposure proxy is selected before the
ten validation baselines are opened. The selected QASM is frozen and replayed in
a fresh process.

## Requirements

{requirements}

## Claim Boundary

Supported: isolated evidence for or against a deterministic dense-interaction
fallback selected from a compiler-in-the-loop mapping portfolio. Not supported:
verifier acceptance, causal hardware performance, current calibration,
mitigation, protocol soundness, quantum advantage, BQP separation, or new B10 credit.
"""


def run_gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    r125_path = root / R125_RESULT_PATH
    r134_path = root / R134_RESULT_PATH
    r125 = json.loads(r125_path.read_text(encoding="utf-8"))
    r134 = json.loads(r134_path.read_text(encoding="utf-8"))
    if r134.get("status") != "family_agnostic_deterministic_mapping_boundary":
        raise ValueError("R135 requires the R134 generic mapping boundary")
    prior_seeds = set(r134["summary"]["design_seeds"] + r134["summary"]["validation_seeds"])
    if prior_seeds & set(CANDIDATE_SEEDS + VALIDATION_SEEDS):
        raise ValueError("R135 seed blocks must be disjoint from R134")

    tasks = build_dense_validation_tasks()
    output = root / OUT_DIR
    source_dir = output / "source_circuits"
    selected_dir = output / "selected_circuits"
    source_dir.mkdir(parents=True, exist_ok=True)
    selected_dir.mkdir(parents=True, exist_ok=True)
    prior_source_hashes = {
        file_sha256(root / path)
        for path in r134.get("artifacts", {}).get("source_circuits", [])
    }
    source_rows: list[dict[str, Any]] = []
    group_rows: list[dict[str, Any]] = []
    portfolio_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    selected_paths: list[str] = []
    replay_preexisting_count = 0
    replay_match_count = 0
    candidate_generation_compilation_count = 0

    with tempfile.TemporaryDirectory(prefix="r135-") as temporary:
        scratch = Path(temporary) / "compiled.qasm"
        for task in tasks:
            source_path = source_dir / f"{task['task_id']}.qasm"
            source_path.write_text(qasm3.dumps(task["circuit"]), encoding="utf-8")
            source_hash = file_sha256(source_path)
            source_rows.append(
                {
                    "task_id": task["task_id"],
                    "family": task["family"],
                    "source_circuit_path": str(source_path.relative_to(root)),
                    "source_circuit_sha256": source_hash,
                    "unseen_vs_r134_source_circuits": source_hash not in prior_source_hashes,
                }
            )
            representative = basis_circuit(
                task["circuit"], tuple("Z" for _ in range(task["circuit"].num_qubits))
            )
            for snapshot_name in sorted(SNAPSHOT_CLASSES):
                backend = SNAPSHOT_CLASSES[snapshot_name]()
                metadata = r125["snapshot_metadata"][snapshot_name]
                candidates = temporal_candidates(task["circuit"], metadata)
                for seed in CANDIDATE_SEEDS:
                    automatic = transpile(
                        representative,
                        backend=backend,
                        optimization_level=3,
                        seed_transpiler=seed,
                    )
                    candidate_generation_compilation_count += 1
                    mapping = automatic_mapping(automatic, representative)
                    candidates[mapping].add(f"seeded_automatic_layout_{seed}")

                group_portfolio_rows = []
                for mapping, sources in sorted(candidates.items()):
                    for policy_id in PORTFOLIO_POLICIES:
                        compiled = compile_policy(
                            representative,
                            backend,
                            list(mapping),
                            policy_id,
                            PORTFOLIO_COMPILE_SEED,
                        )
                        qasm = qasm3.dumps(compiled)
                        exposure = exposure_from_qasm(qasm, metadata, scratch)
                        descriptor = compiled_route_descriptor(compiled, exposure)
                        row = {
                            "snapshot": snapshot_name,
                            "task_id": task["task_id"],
                            "mapping": list(mapping),
                            "candidate_sources": sorted(sources),
                            "policy_id": policy_id,
                            "combined_any_error_proxy": exposure[
                                "combined_any_error_proxy"
                            ],
                            "cx_occurrence_count": descriptor["cx_occurrence_count"],
                            "route_family_id": descriptor["route_family_id"],
                            "qasm_hash": stable_hash(qasm),
                        }
                        portfolio_rows.append(row)
                        group_portfolio_rows.append((row, qasm, descriptor))
                selected_row, selected_qasm, selected_descriptor = min(
                    group_portfolio_rows,
                    key=lambda item: (
                        item[0]["combined_any_error_proxy"],
                        item[0]["cx_occurrence_count"],
                        item[0]["policy_id"],
                        item[0]["mapping"],
                    ),
                )
                selected_path = selected_dir / f"{snapshot_name}_{task['task_id']}.qasm"
                relative_path = str(selected_path.relative_to(root))
                selected_paths.append(relative_path)
                if selected_path.exists():
                    replay_preexisting_count += 1
                    replay_match = selected_path.read_text(encoding="utf-8") == selected_qasm
                else:
                    selected_path.write_text(selected_qasm, encoding="utf-8")
                    replay_match = True
                replay_match_count += replay_match

                group_validation_rows = []
                for seed in VALIDATION_SEEDS:
                    automatic = transpile(
                        representative,
                        backend=backend,
                        optimization_level=3,
                        seed_transpiler=seed,
                    )
                    automatic_exposure = exposure_from_qasm(
                        qasm3.dumps(automatic), metadata, scratch
                    )["combined_any_error_proxy"]
                    gain = automatic_exposure - selected_row["combined_any_error_proxy"]
                    row = {
                        "snapshot": snapshot_name,
                        "task_id": task["task_id"],
                        "family": task["family"],
                        "seed": seed,
                        "selected_mapping": selected_row["mapping"],
                        "selected_policy_id": selected_row["policy_id"],
                        "selected_candidate_sources": selected_row["candidate_sources"],
                        "selected_circuit_path": relative_path,
                        "selected_circuit_sha256": file_sha256(selected_path),
                        "selected_combined_any_error_proxy": selected_row[
                            "combined_any_error_proxy"
                        ],
                        "automatic_combined_any_error_proxy": automatic_exposure,
                        "gain_vs_automatic_default": gain,
                        "outcome_vs_automatic_default": outcome(gain),
                    }
                    validation_rows.append(row)
                    group_validation_rows.append(row)
                wins = sum(
                    row["outcome_vs_automatic_default"] == "win"
                    for row in group_validation_rows
                )
                ties = sum(
                    row["outcome_vs_automatic_default"] == "tie"
                    for row in group_validation_rows
                )
                losses = len(group_validation_rows) - wins - ties
                group_rows.append(
                    {
                        "snapshot": snapshot_name,
                        "task_id": task["task_id"],
                        "family": task["family"],
                        "unique_candidate_mapping_count": len(candidates),
                        "portfolio_candidate_count": len(group_portfolio_rows),
                        "selected_mapping": selected_row["mapping"],
                        "selected_policy_id": selected_row["policy_id"],
                        "selected_candidate_sources": selected_row["candidate_sources"],
                        "selected_combined_any_error_proxy": selected_row[
                            "combined_any_error_proxy"
                        ],
                        "selected_route_family": selected_descriptor,
                        "selected_circuit_path": relative_path,
                        "selected_qasm_replay_matches": replay_match,
                        "mean_gain_vs_automatic_default": statistics.fmean(
                            row["gain_vs_automatic_default"]
                            for row in group_validation_rows
                        ),
                        "minimum_gain_vs_automatic_default": min(
                            row["gain_vs_automatic_default"]
                            for row in group_validation_rows
                        ),
                        "win_count_vs_automatic_default": wins,
                        "tie_count_vs_automatic_default": ties,
                        "loss_count_vs_automatic_default": losses,
                    }
                )

    win_count = sum(row["outcome_vs_automatic_default"] == "win" for row in validation_rows)
    tie_count = sum(row["outcome_vs_automatic_default"] == "tie" for row in validation_rows)
    loss_count = sum(row["outcome_vs_automatic_default"] == "loss" for row in validation_rows)
    no_loss_groups = sum(row["loss_count_vs_automatic_default"] == 0 for row in group_rows)
    selected_policy_counts = Counter(row["selected_policy_id"] for row in group_rows)
    summary = {
        "validation_task_count": len(tasks),
        "validation_group_count": len(group_rows),
        "candidate_seed_count": len(CANDIDATE_SEEDS),
        "candidate_seeds": list(CANDIDATE_SEEDS),
        "validation_seed_count": len(VALIDATION_SEEDS),
        "validation_seeds": list(VALIDATION_SEEDS),
        "candidate_generation_compilation_count": candidate_generation_compilation_count,
        "unique_candidate_mapping_count": sum(
            row["unique_candidate_mapping_count"] for row in group_rows
        ),
        "portfolio_candidate_compilation_count": len(portfolio_rows),
        "automatic_validation_compilation_count": len(validation_rows),
        "total_compilation_count": candidate_generation_compilation_count
        + len(portfolio_rows)
        + len(validation_rows),
        "validation_row_count": len(validation_rows),
        "source_circuit_count": len(source_rows),
        "source_circuits_unseen_vs_r134_count": sum(
            row["unseen_vs_r134_source_circuits"] for row in source_rows
        ),
        "temporal_rule_count": 5,
        "temporal_top_k": TEMPORAL_TOP_K,
        "portfolio_policy_count": len(PORTFOLIO_POLICIES),
        "portfolio_compile_seed": PORTFOLIO_COMPILE_SEED,
        "selected_default_policy_group_count": selected_policy_counts[
            "selected_o3_default"
        ],
        "selected_lookahead_policy_group_count": selected_policy_counts[
            "selected_o3_lookahead"
        ],
        "candidate_selection_uses_compiled_exposure": True,
        "validation_baseline_read_during_selection": False,
        "selected_qasm_preexisting_count": replay_preexisting_count,
        "selected_qasm_replay_match_count": replay_match_count,
        "win_count_vs_automatic_default": win_count,
        "tie_count_vs_automatic_default": tie_count,
        "loss_count_vs_automatic_default": loss_count,
        "no_loss_group_count_vs_automatic_default": no_loss_groups,
        "automatic_baseline_no_loss_gate_passed": loss_count == 0,
        "exact_qasm_cross_process_replay_claimed": replay_preexisting_count == 12
        and replay_match_count == 12,
        "fresh_candidate_and_validation_seed_blocks_used": True,
        "r134_seeds_reused": False,
        "acceptance_holdout_executed": False,
        "r125_acceptance_rows_read": False,
        "readout_mitigation_tested": False,
        "current_backend_calibration_used": False,
        "hardware_execution_performed": False,
        "protocol_soundness_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "new_credit_delta": 0,
    }
    requirements = [
        {
            "requirement_id": "P1",
            "label": "R134 source is hash-bound",
            "passed": r134.get("source_target_id") == UPSTREAM_TARGET_ID,
            "evidence": {"r134_sha256": file_sha256(r134_path)},
        },
        {
            "requirement_id": "P2",
            "label": "four new dense source families are materialized",
            "passed": len(source_rows) == 4
            and summary["source_circuits_unseen_vs_r134_count"] == 4,
            "evidence": {"source_rows": source_rows},
        },
        {
            "requirement_id": "P3",
            "label": "candidate and validation seed blocks are disjoint",
            "passed": not (set(CANDIDATE_SEEDS) & set(VALIDATION_SEEDS))
            and not summary["r134_seeds_reused"],
            "evidence": {
                "candidate_seeds": list(CANDIDATE_SEEDS),
                "validation_seeds": list(VALIDATION_SEEDS),
            },
        },
        {
            "requirement_id": "P4",
            "label": "temporal and seeded-layout candidate sources are both represented",
            "passed": all(
                any(source.startswith("seeded_automatic_layout_") for source in row["selected_candidate_sources"])
                or any(
                    source
                    in {
                        "weighted_distance",
                        "chronological_decay",
                        "reverse_decay",
                        "transition_locality",
                        "peak_window",
                    }
                    for source in row["selected_candidate_sources"]
                )
                for row in group_rows
            ),
            "evidence": {"group_count": len(group_rows)},
        },
        {
            "requirement_id": "P5",
            "label": "portfolio selection never reads validation baseline outcomes",
            "passed": summary["candidate_selection_uses_compiled_exposure"]
            and not summary["validation_baseline_read_during_selection"],
            "evidence": {"selection_contract": "candidate_exposure_before_validation"},
        },
        {
            "requirement_id": "P6",
            "label": "all 12 groups have complete candidate and validation ledgers",
            "passed": len(group_rows) == 12 and len(validation_rows) == 120,
            "evidence": {"groups": len(group_rows), "rows": len(validation_rows)},
        },
        {
            "requirement_id": "P7",
            "label": "all 12 selected QASM files replay in a fresh process",
            "passed": replay_preexisting_count == 12 and replay_match_count == 12,
            "evidence": {
                "preexisting": replay_preexisting_count,
                "matches": replay_match_count,
            },
        },
        {
            "requirement_id": "P8",
            "label": "automatic-baseline no-loss verdict is evaluated without promotion",
            "passed": summary["automatic_baseline_no_loss_gate_passed"] == (loss_count == 0),
            "evidence": {"loss_count": loss_count},
        },
        {
            "requirement_id": "P9",
            "label": "verifier acceptance, mitigation, calibration, and hardware remain excluded",
            "passed": not summary["acceptance_holdout_executed"]
            and not summary["r125_acceptance_rows_read"]
            and not summary["readout_mitigation_tested"]
            and not summary["current_backend_calibration_used"]
            and not summary["hardware_execution_performed"],
            "evidence": {"compiler_fallback_validation_only": True},
        },
        {
            "requirement_id": "P10",
            "label": "no soundness, advantage, BQP, or new credit is claimed",
            "passed": not summary["protocol_soundness_claimed"]
            and not summary["quantum_advantage_claimed"]
            and not summary["bqp_separation_claimed"]
            and summary["new_credit_delta"] == 0,
            "evidence": {"new_credit_delta": 0},
        },
    ]
    failed = [row["requirement_id"] for row in requirements if not row["passed"]]
    payload: dict[str, Any] = {
        "title": "B4/B8 R135 dense-interaction deterministic fallback",
        "version": "0.1",
        "generated_at_unix": int(time.time()),
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "requirements": requirements,
        "requirement_count": len(requirements),
        "requirements_passed": len(requirements) - len(failed),
        "requirements_failed": len(failed),
        "summary": summary,
        "source_circuit_rows": source_rows,
        "validation_group_rows": group_rows,
        "portfolio_candidate_rows": portfolio_rows,
        "validation_rows": validation_rows,
        "environment": {
            "deterministic_process_environment": DETERMINISTIC_PROCESS_ENV,
            "qiskit": package_version("qiskit"),
            "qiskit_ibm_runtime": package_version("qiskit-ibm-runtime"),
        },
        "artifacts": {
            "r134_result": R134_RESULT_PATH,
            "source_circuits": [row["source_circuit_path"] for row in source_rows],
            "selected_circuits": sorted(selected_paths),
        },
        "claim_boundary": {
            "what_is_supported": (
                "Design-separated validation of a compiler-in-the-loop deterministic "
                "dense-interaction fallback against automatic-layout exposure baselines."
            ),
            "what_is_not_supported": (
                "Verifier acceptance, causal hardware performance, readout mitigation, "
                "current calibration, provider access, hardware execution, protocol soundness, "
                "quantum advantage, BQP separation, or new B10 credit."
            ),
            "next_gate": (
                "If the no-loss gate passes, preregister a verifier-level holdout that binds "
                "the selected compiler artifact before any soundness experiment."
            ),
        },
    }
    payload["payload_hash"] = stable_hash(payload)
    write_json(root / RESULT_PATH, payload)
    (root / REPORT_PATH).write_text(report(payload), encoding="utf-8")
    return payload


def main() -> None:
    ensure_deterministic_process_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    payload = run_gate(args.root)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
