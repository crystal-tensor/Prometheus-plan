#!/usr/bin/env python3
"""Design a seed-robust mapping rule using a noisy lower confidence bound."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

from b4_b8_r119_private_observable_bundle_gate import stable_hash, write_json
from b4_b8_r121_private_bundle_shot_sweep import basis_circuit
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r127_calibration_aware_layout_design import SNAPSHOT_CLASSES
from b4_b8_r132_topology_constrained_route_policy import (
    DETERMINISTIC_PROCESS_ENV,
    compile_policy,
)
from b4_b8_r135_dense_interaction_fallback import build_dense_validation_tasks
from b4_b8_r138_postcommit_statistical_challenge import (
    exact_distribution,
    hellinger_fidelity,
    probability_from_counts,
)
from b4_b8_r139_lagos_ising_channel_attribution import (
    exact_compiled_classical_distribution,
)
from b4_b8_r141_hashed_output_sketch_design import candidate_identity


METHOD = "b4_b8_r142_seed_robust_lcb_mapping_design_v0"
STATUS = "seed_robust_lower_confidence_bound_mapping_frozen_before_holdout"
MODEL_STATUS = "r141_sketch_shortlist_ranked_on_disjoint_noisy_design_seeds"
TARGET_ID = "T-B4-002as/T-B8-003aw/T-B10-009ak"
UPSTREAM_TARGET_ID = "T-B4-002ar/T-B8-003av/T-B10-009aj"
R136_RESULT_PATH = "results/B4_B8_R136_route_realization_margin_v0.json"
R140_RESULT_PATH = "results/B4_B8_R140_output_aware_mapping_design_v0.json"
R141_DESIGN_PATH = "results/B4_B8_R141_hashed_output_sketch_design_v0.json"
RESULT_PATH = "results/B4_B8_R142_seed_robust_lcb_mapping_design_v0.json"
REPORT_PATH = "research/B4_B8_R142_seed_robust_lcb_mapping_design.md"
OUT_DIR = "results/B4_B8_R142_seed_robust_lcb_mapping_design"

SHORTLIST_UNIQUE_QASM_COUNT = 8
DESIGN_SEEDS = list(range(14201, 14217))
SHOTS = 2048
LCB_Z = 1.96


def ensure_deterministic_process_environment() -> None:
    if all(os.environ.get(key) == value for key, value in DETERMINISTIC_PROCESS_ENV.items()):
        return
    environment = dict(os.environ)
    environment.update(DETERMINISTIC_PROCESS_ENV)
    os.execvpe(sys.executable, [sys.executable, *sys.argv], environment)


def shortlist(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda row: (
            row["hashed_output_sketch_score"],
            row["hashed_output_sketch_readout_fidelity"],
            -row["cx_any_error_proxy"],
            -row["cx_occurrence_count"],
            row["policy_id"],
            tuple(row["mapping"]),
            -row["realization_seed"],
        ),
        reverse=True,
    )
    selected = []
    qasm_hashes = set()
    for row in ordered:
        if row["qasm_hash"] in qasm_hashes:
            continue
        qasm_hashes.add(row["qasm_hash"])
        selected.append(row)
        if len(selected) == SHORTLIST_UNIQUE_QASM_COUNT:
            break
    return selected


def mean_standard_error_lcb(values: list[float]) -> tuple[float, float, float]:
    mean = statistics.mean(values)
    standard_error = statistics.stdev(values) / math.sqrt(len(values))
    return mean, standard_error, mean - LCB_Z * standard_error


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    groups = "\n".join(
        f"- `{row['snapshot']}` / `{row['task_id']}`: selected mapping "
        f"`{row['selected_mapping']}`, mean/LCB vs automatic "
        f"`{row['selected_mean_delta_vs_automatic']:+.8f}` / "
        f"`{row['selected_lcb_delta_vs_automatic']:+.8f}`, wins "
        f"`{row['selected_win_count_vs_automatic']} / 16`, changed from R140 "
        f"`{row['selection_changed_from_r140']}`."
        for row in payload["group_rows"]
    )
    requirements = "\n".join(
        f"- `{row['requirement_id']}` {'PASS' if row['passed'] else 'FAIL'}: {row['label']}"
        for row in payload["requirements"]
    )
    return f"""# B4/B8 R142 Seed-Robust LCB Mapping Design

## Design Result

- R141 candidates read: `{summary['source_candidate_count']}`
- Unique-QASM shortlist: `{summary['shortlist_candidate_count']}` across `{summary['group_count']}` groups
- Noisy design executions / shots: `{summary['simulated_circuit_execution_count']}` / `{summary['total_simulated_shots']}`
- Groups with positive selected lower confidence bound: `{summary['positive_lcb_group_count']} / 12`
- Selections changed from R140 exact: `{summary['changed_from_r140_group_count']}`
- Lagos selected mapping: `{summary['lagos_ising_selected_mapping']}`
- Lagos mean / LCB / wins: `{summary['lagos_ising_mean_delta_vs_automatic']:+.8f}` / `{summary['lagos_ising_lcb_delta_vs_automatic']:+.8f}` / `{summary['lagos_ising_win_count_vs_automatic']} of 16`
- R141 holdout rows read during selection: `0`
- Selected OpenQASM 3 replay: `{summary['selected_qasm_replay_match_count']} / 12`
- New credit delta: `0`

R142 first uses the frozen R141 sample-sketch score to retain the eight best
unique QASM candidates per group. It then evaluates those fixed candidates and
a same-seed automatic compilation on sixteen disjoint design seeds at 2,048
shots. Selection maximizes `mean_delta - 1.96 * standard_error`, with no fitted
coefficient and no access to R141 holdout rows.

This is an intentionally expensive design denominator. It tests whether
lower-tail pressure changes the mapping choice before a fresh hidden holdout;
it is not yet an efficient production mapper.

## Group Evidence

{groups}

## Requirements

{requirements}

## Claim Boundary

Supported: a frozen portfolio of lower-confidence-bound mapping choices from a
disjoint synthetic design block. Not supported: hidden-seed acceptance,
efficient production selection, current calibration, real hardware,
mitigation, soundness, quantum advantage, BQP separation, solved B4/B8/B10, or
new credit.
"""


def run_gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    started_at = int(time.time())
    r141 = json.loads((root / R141_DESIGN_PATH).read_text(encoding="utf-8"))
    r140 = json.loads((root / R140_RESULT_PATH).read_text(encoding="utf-8"))
    r136 = json.loads((root / R136_RESULT_PATH).read_text(encoding="utf-8"))
    tasks = {task["task_id"]: task for task in build_dense_validation_tasks()}
    candidate_groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in r141["candidate_rows"]:
        candidate_groups.setdefault((row["snapshot"], row["task_id"]), []).append(row)
    r141_groups = {
        (row["snapshot"], row["task_id"]): row for row in r141["group_rows"]
    }
    r140_groups = {
        (row["snapshot"], row["task_id"]): row for row in r140["group_rows"]
    }
    r136_groups = {
        (row["snapshot"], row["task_id"]): row
        for row in r136["validation_group_rows"]
    }
    output = root / OUT_DIR
    selected_dir = output / "selected_circuits"
    selected_dir.mkdir(parents=True, exist_ok=True)
    design_rows: list[dict[str, Any]] = []
    group_rows: list[dict[str, Any]] = []
    selected_preexisting = 0
    selected_replay_matches = 0

    for key in sorted(candidate_groups):
        snapshot_name, task_id = key
        task = tasks[task_id]
        backend = SNAPSHOT_CLASSES[snapshot_name]()
        simulator = AerSimulator.from_backend(backend)
        logical = basis_circuit(
            task["circuit"], tuple("Z" for _ in range(task["circuit"].num_qubits))
        )
        ideal = exact_distribution(task["circuit"])
        candidates = shortlist(candidate_groups[key])
        if len(candidates) != SHORTLIST_UNIQUE_QASM_COUNT:
            raise ValueError(f"R142 incomplete unique-QASM shortlist for {key}")

        source_artifacts: dict[tuple[Any, ...], str] = {}
        r141_group = r141_groups[key]
        source_artifacts[
            (
                tuple(r141_group["selected_mapping"]),
                r141_group["selected_policy_id"],
                r141_group["selected_realization_seed"],
            )
        ] = r141_group["selected_circuit_path"]
        r140_group = r140_groups[key]
        source_artifacts[
            (
                tuple(r140_group["new_selected_mapping"]),
                r140_group["new_selected_policy_id"],
                r140_group["new_selected_realization_seed"],
            )
        ] = r140_group["selected_circuit_path"]
        r136_group = r136_groups[key]
        source_artifacts[
            (
                tuple(r136_group["selected_mapping"]),
                r136_group["selected_policy_id"],
                r136_group["selected_realization_seed"],
            )
        ] = r136_group["selected_circuit_path"]

        compiled_candidates = []
        for candidate in candidates:
            identity = candidate_identity(candidate)
            if identity in source_artifacts:
                qasm = (root / source_artifacts[identity]).read_text(encoding="utf-8")
                circuit = qasm3.loads(qasm)
            else:
                circuit = compile_policy(
                    logical,
                    backend,
                    candidate["mapping"],
                    candidate["policy_id"],
                    candidate["realization_seed"],
                )
                qasm = qasm3.dumps(circuit)
            semantic_fidelity = hellinger_fidelity(
                ideal, exact_compiled_classical_distribution(circuit)
            )
            compiled_candidates.append((candidate, circuit, qasm, semantic_fidelity))

        automatic_fidelities = {}
        automatic_circuits = {}
        for seed in DESIGN_SEEDS:
            automatic = transpile(
                logical,
                backend=backend,
                optimization_level=3,
                seed_transpiler=seed,
            )
            simulator_seed = seed + 1420000
            counts = simulator.run(
                automatic, shots=SHOTS, seed_simulator=simulator_seed
            ).result().get_counts()
            automatic_fidelities[seed] = hellinger_fidelity(
                ideal,
                probability_from_counts(
                    counts, SHOTS, task["circuit"].num_qubits
                ),
            )
            automatic_circuits[seed] = automatic

        scored_candidates = []
        for rank, (candidate, circuit, qasm, semantic_fidelity) in enumerate(
            compiled_candidates, 1
        ):
            deltas = []
            fidelities = []
            for seed in DESIGN_SEEDS:
                simulator_seed = seed + 1420000
                counts = simulator.run(
                    circuit, shots=SHOTS, seed_simulator=simulator_seed
                ).result().get_counts()
                fidelity = hellinger_fidelity(
                    ideal,
                    probability_from_counts(
                        counts, SHOTS, task["circuit"].num_qubits
                    ),
                )
                fidelities.append(fidelity)
                deltas.append(fidelity - automatic_fidelities[seed])
            mean_delta, standard_error, lcb = mean_standard_error_lcb(deltas)
            row = {
                "snapshot": snapshot_name,
                "task_id": task_id,
                "shortlist_rank": rank,
                "mapping": candidate["mapping"],
                "policy_id": candidate["policy_id"],
                "realization_seed": candidate["realization_seed"],
                "source_qasm_hash": candidate["qasm_hash"],
                "design_qasm_stable_hash": stable_hash(qasm),
                "source_artifact_reused": candidate_identity(candidate)
                in source_artifacts,
                "semantic_fidelity": semantic_fidelity,
                "sketch_score": candidate["hashed_output_sketch_score"],
                "mean_fidelity": statistics.mean(fidelities),
                "mean_delta_vs_automatic": mean_delta,
                "standard_error_delta_vs_automatic": standard_error,
                "lcb_delta_vs_automatic": lcb,
                "minimum_delta_vs_automatic": min(deltas),
                "win_count_vs_automatic": sum(delta > 0 for delta in deltas),
                "design_deltas_vs_automatic": deltas,
            }
            design_rows.append(row)
            scored_candidates.append((row, qasm))
        selected, selected_qasm = max(
            scored_candidates,
            key=lambda item: (
                item[0]["lcb_delta_vs_automatic"],
                item[0]["mean_delta_vs_automatic"],
                item[0]["minimum_delta_vs_automatic"],
                item[0]["sketch_score"],
                item[0]["policy_id"],
                tuple(item[0]["mapping"]),
                -item[0]["realization_seed"],
            ),
        )
        selected_path = selected_dir / f"{snapshot_name}_{task_id}.qasm"
        if selected_path.exists():
            selected_preexisting += 1
            replay_match = selected_path.read_text(encoding="utf-8") == selected_qasm
        else:
            selected_path.write_text(selected_qasm, encoding="utf-8")
            replay_match = True
        selected_replay_matches += replay_match
        r140_identity = (
            tuple(r140_group["new_selected_mapping"]),
            r140_group["new_selected_policy_id"],
            r140_group["new_selected_realization_seed"],
        )
        selected_identity = (
            tuple(selected["mapping"]),
            selected["policy_id"],
            selected["realization_seed"],
        )
        group_rows.append(
            {
                "snapshot": snapshot_name,
                "task_id": task_id,
                "shortlist_candidate_count": len(scored_candidates),
                "selected_shortlist_rank": selected["shortlist_rank"],
                "selected_mapping": selected["mapping"],
                "selected_policy_id": selected["policy_id"],
                "selected_realization_seed": selected["realization_seed"],
                "selected_mean_delta_vs_automatic": selected[
                    "mean_delta_vs_automatic"
                ],
                "selected_standard_error_delta_vs_automatic": selected[
                    "standard_error_delta_vs_automatic"
                ],
                "selected_lcb_delta_vs_automatic": selected[
                    "lcb_delta_vs_automatic"
                ],
                "selected_minimum_delta_vs_automatic": selected[
                    "minimum_delta_vs_automatic"
                ],
                "selected_win_count_vs_automatic": selected[
                    "win_count_vs_automatic"
                ],
                "selection_changed_from_r140": selected_identity != r140_identity,
                "selected_circuit_path": str(selected_path.relative_to(root)),
                "selected_circuit_sha256": file_sha256(selected_path),
                "selected_qasm_replay_matches": replay_match,
            }
        )

    lagos = next(
        row
        for row in group_rows
        if row["snapshot"] == "FakeLagosV2"
        and row["task_id"] == "dense_validation_complete_ising_n6"
    )
    summary = {
        "source_candidate_count": len(r141["candidate_rows"]),
        "group_count": len(group_rows),
        "shortlist_unique_qasm_count_per_group": SHORTLIST_UNIQUE_QASM_COUNT,
        "shortlist_candidate_count": len(design_rows),
        "design_seed_count": len(DESIGN_SEEDS),
        "design_seeds": DESIGN_SEEDS,
        "shots_per_execution": SHOTS,
        "lcb_z": LCB_Z,
        "simulated_circuit_execution_count": len(group_rows)
        * len(DESIGN_SEEDS)
        * (SHORTLIST_UNIQUE_QASM_COUNT + 1),
        "total_simulated_shots": len(group_rows)
        * len(DESIGN_SEEDS)
        * (SHORTLIST_UNIQUE_QASM_COUNT + 1)
        * SHOTS,
        "positive_lcb_group_count": sum(
            row["selected_lcb_delta_vs_automatic"] > 0 for row in group_rows
        ),
        "changed_from_r140_group_count": sum(
            row["selection_changed_from_r140"] for row in group_rows
        ),
        "minimum_selected_semantic_fidelity": min(
            row["semantic_fidelity"] for row in design_rows
        ),
        "selected_qasm_preexisting_count": selected_preexisting,
        "selected_qasm_replay_match_count": selected_replay_matches,
        "lagos_ising_selected_mapping": lagos["selected_mapping"],
        "lagos_ising_selected_policy_id": lagos["selected_policy_id"],
        "lagos_ising_selected_realization_seed": lagos["selected_realization_seed"],
        "lagos_ising_mean_delta_vs_automatic": lagos[
            "selected_mean_delta_vs_automatic"
        ],
        "lagos_ising_lcb_delta_vs_automatic": lagos[
            "selected_lcb_delta_vs_automatic"
        ],
        "lagos_ising_win_count_vs_automatic": lagos[
            "selected_win_count_vs_automatic"
        ],
        "r141_holdout_rows_read_during_selection": 0,
        "hidden_holdout_executed": False,
        "efficient_production_mapper_claimed": False,
        "hardware_execution_performed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "new_credit_delta": 0,
    }
    requirements = [
        {"requirement_id": "R1", "label": "all 1,536 R141 design candidates are available before shortlisting", "passed": summary["source_candidate_count"] == 1536},
        {"requirement_id": "R2", "label": "each group has eight unique-QASM shortlist candidates", "passed": summary["shortlist_candidate_count"] == 96},
        {"requirement_id": "R3", "label": "sixteen fixed design seeds and 2,048 shots are disclosed", "passed": summary["design_seed_count"] == 16 and summary["shots_per_execution"] == 2048},
        {"requirement_id": "R4", "label": "1,728 executions and 3,538,944 shots are fully disclosed", "passed": summary["simulated_circuit_execution_count"] == 1728 and summary["total_simulated_shots"] == 3538944},
        {"requirement_id": "R5", "label": "Lagos selected lower confidence bound is positive", "passed": summary["lagos_ising_lcb_delta_vs_automatic"] > 0},
        {"requirement_id": "R6", "label": "Lagos selected route wins at least twelve of sixteen design rows", "passed": summary["lagos_ising_win_count_vs_automatic"] >= 12},
        {"requirement_id": "R7", "label": "all shortlisted circuits retain exact semantic fidelity", "passed": summary["minimum_selected_semantic_fidelity"] >= 1 - 1e-12},
        {"requirement_id": "R8", "label": "all twelve selected OpenQASM 3 files replay", "passed": selected_replay_matches == 12},
        {"requirement_id": "R9", "label": "R141 hidden holdout rows remain unread and no hidden R142 holdout runs", "passed": summary["r141_holdout_rows_read_during_selection"] == 0 and not summary["hidden_holdout_executed"]},
        {"requirement_id": "R10", "label": "production efficiency, hardware, advantage, BQP, and credit claims remain false", "passed": not any([summary["efficient_production_mapper_claimed"], summary["hardware_execution_performed"], summary["quantum_advantage_claimed"], summary["bqp_separation_claimed"], summary["new_credit_delta"]])},
    ]
    payload = {
        "title": "B4/B8 R142 seed-robust LCB mapping design",
        "version": 0,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "generated_at_unix": started_at,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "summary": summary,
        "group_rows": group_rows,
        "design_rows": design_rows,
        "requirements": requirements,
        "requirement_count": len(requirements),
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [row["requirement_id"] for row in requirements if not row["passed"]],
        "artifacts": {
            "r136_result": R136_RESULT_PATH,
            "r140_design_result": R140_RESULT_PATH,
            "r141_design_result": R141_DESIGN_PATH,
            "selected_circuit_directory": str(selected_dir.relative_to(root)),
            "result": RESULT_PATH,
            "markdown_report": REPORT_PATH,
        },
        "claim_boundary": {
            "what_is_supported": "disjoint-design-seed lower-confidence-bound mapping choices and their frozen QASM artifacts",
            "what_is_not_supported": "hidden-seed acceptance, efficient production selection, current calibration, hardware, mitigation, soundness, quantum advantage, BQP separation, solved B4/B8/B10, or new credit",
        },
    }
    hash_payload = dict(payload)
    payload["payload_hash"] = hashlib.sha256(
        json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    ensure_deterministic_process_environment()
    root = args.root.resolve()
    payload = run_gate(root)
    output = args.output or root / RESULT_PATH
    markdown = args.report or root / REPORT_PATH
    write_json(output, payload)
    markdown.parent.mkdir(parents=True, exist_ok=True)
    markdown.write_text(report(payload), encoding="utf-8")
    print(json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if payload["requirements_failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
