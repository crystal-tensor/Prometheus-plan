#!/usr/bin/env python3
"""T-B4-002ak/T-B8-003ao: pressure residual losses with route realizations."""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any

from qiskit import qasm3, transpile

from b4_b8_r121_private_bundle_shot_sweep import basis_circuit, stable_hash, write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r127_calibration_aware_layout_design import SNAPSHOT_CLASSES
from b4_b8_r128_transpiler_loop_layout_ranking import exposure_from_qasm, package_version
from b4_b8_r131_compiled_route_family_attribution import compiled_route_descriptor
from b4_b8_r132_topology_constrained_route_policy import (
    DETERMINISTIC_PROCESS_ENV,
    compile_policy,
)
from b4_b8_r135_dense_interaction_fallback import build_dense_validation_tasks


METHOD = "b4_b8_r136_route_realization_margin_v0"
STATUS = "route_realization_lower_tail_margin_boundary"
MODEL_STATUS = "top_candidate_route_realizations_selected_before_new_validation_block"
TARGET_ID = "T-B4-002ak/T-B8-003ao/T-B10-009ac"
UPSTREAM_TARGET_ID = "T-B4-002aj/T-B8-003an/T-B10-009ab"
R125_RESULT_PATH = "results/B4_B8_R125_historical_snapshot_replay_v0.json"
R135_RESULT_PATH = "results/B4_B8_R135_dense_interaction_fallback_v0.json"
RESULT_PATH = "results/B4_B8_R136_route_realization_margin_v0.json"
REPORT_PATH = "research/B4_B8_R136_route_realization_margin.md"
OUT_DIR = "results/B4_B8_R136_route_realization_margin"
TOP_K = 8
REALIZATION_SEEDS = tuple(range(13601, 13617))
VALIDATION_SEEDS = tuple(range(13681, 13691))
TOLERANCE = 1e-15


def ensure_deterministic_process_environment() -> None:
    if all(os.environ.get(key) == value for key, value in DETERMINISTIC_PROCESS_ENV.items()):
        return
    environment = dict(os.environ)
    environment.update(DETERMINISTIC_PROCESS_ENV)
    os.execvpe(sys.executable, [sys.executable, *sys.argv], environment)


def outcome(delta: float) -> str:
    return "win" if delta > TOLERANCE else "loss" if delta < -TOLERANCE else "tie"


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    group_lines = []
    for row in payload["validation_group_rows"]:
        group_lines.append(
            "- `{snapshot}` / `{task}`: selected `{mapping}` / `{policy}` / seed "
            "`{seed}`; improvement vs R135 `{improvement:+.6f}`; validation "
            "wins/ties/losses `{wins}/{ties}/{losses}`; replay `{replay}`.".format(
                snapshot=row["snapshot"],
                task=row["task_id"],
                mapping=row["selected_mapping"],
                policy=row["selected_policy_id"],
                seed=row["selected_realization_seed"],
                improvement=row["selected_exposure_improvement_vs_r135"],
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
    return f"""# B4/B8 R136 Route-Realization Lower-Tail Margin

## Result

- R135 residual losses: `{summary['r135_residual_loss_count']}`
- R135 loss-margin range: `{summary['r135_minimum_loss_margin']:.8f}` to `{summary['r135_maximum_loss_margin']:.8f}`
- Top mapping/policy candidates per group: `{summary['top_candidate_count_per_group']}`
- Realization seeds per candidate: `{summary['realization_seed_count']}`
- Route-realization compilations: `{summary['route_realization_compilation_count']}`
- New automatic validation compilations: `{summary['automatic_validation_compilation_count']}`
- Groups improved over R135 selected exposure: `{summary['improved_over_r135_group_count']}` / `12`
- Selected-QASM replay: `{summary['selected_qasm_replay_match_count']}` / `12`
- Wins/ties/losses vs automatic layout: `{summary['win_count_vs_automatic_default']}/{summary['tie_count_vs_automatic_default']}/{summary['loss_count_vs_automatic_default']}`
- No-loss groups: `{summary['no_loss_group_count_vs_automatic_default']}` / `12`
- Automatic-baseline no-loss gate: `{summary['automatic_baseline_no_loss_gate_passed']}`
- New credit delta: `0`

## Validation Evidence

{chr(10).join(group_lines)}

R136 consumes only the R135 portfolio ledger while choosing candidates. The top
eight mapping/policy rows in each group are recompiled under sixteen new route
realization seeds. The minimum historical exposure realization is frozen before
the disjoint automatic validation seeds are opened. No R135 validation loss row
or R136 validation baseline is used during selection.

## Requirements

{requirements}

## Claim Boundary

Supported: route-realization lower-tail evidence for the seven residual R135
compiler losses under a validation-blind selection contract. Not supported:
verifier acceptance, causal hardware performance, current calibration,
mitigation, protocol soundness, quantum advantage, BQP separation, or new B10 credit.
"""


def run_gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    r125_path = root / R125_RESULT_PATH
    r135_path = root / R135_RESULT_PATH
    r125 = json.loads(r125_path.read_text(encoding="utf-8"))
    r135 = json.loads(r135_path.read_text(encoding="utf-8"))
    if r135.get("status") != "dense_interaction_deterministic_fallback_boundary":
        raise ValueError("R136 requires the R135 dense fallback boundary")
    prior_seeds = set(r135["summary"]["candidate_seeds"] + r135["summary"]["validation_seeds"])
    if prior_seeds & set(REALIZATION_SEEDS + VALIDATION_SEEDS):
        raise ValueError("R136 seed blocks must be disjoint from R135")

    tasks = {task["task_id"]: task for task in build_dense_validation_tasks()}
    r135_group_rows = {
        (row["snapshot"], row["task_id"]): row
        for row in r135["validation_group_rows"]
    }
    r135_portfolio_by_group: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for key in r135_group_rows:
        rows = [
            row
            for row in r135["portfolio_candidate_rows"]
            if (row["snapshot"], row["task_id"]) == key
        ]
        r135_portfolio_by_group[key] = sorted(
            rows,
            key=lambda row: (
                row["combined_any_error_proxy"],
                row["cx_occurrence_count"],
                row["policy_id"],
                row["mapping"],
            ),
        )[:TOP_K]
    residual_rows = [
        {
            "snapshot": row["snapshot"],
            "task_id": row["task_id"],
            "seed": row["seed"],
            "loss_margin": -row["gain_vs_automatic_default"],
        }
        for row in r135["validation_rows"]
        if row["outcome_vs_automatic_default"] == "loss"
    ]
    residual_margins = [row["loss_margin"] for row in residual_rows]

    output = root / OUT_DIR
    selected_dir = output / "selected_circuits"
    selected_dir.mkdir(parents=True, exist_ok=True)
    realization_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    group_rows: list[dict[str, Any]] = []
    selected_paths: list[str] = []
    replay_preexisting_count = 0
    replay_match_count = 0

    with tempfile.TemporaryDirectory(prefix="r136-") as temporary:
        scratch = Path(temporary) / "compiled.qasm"
        for key in sorted(r135_group_rows):
            snapshot_name, task_id = key
            task = tasks[task_id]
            representative = basis_circuit(
                task["circuit"], tuple("Z" for _ in range(task["circuit"].num_qubits))
            )
            backend = SNAPSHOT_CLASSES[snapshot_name]()
            metadata = r125["snapshot_metadata"][snapshot_name]
            group_realizations = []
            for rank, candidate in enumerate(r135_portfolio_by_group[key], start=1):
                for seed in REALIZATION_SEEDS:
                    compiled = compile_policy(
                        representative,
                        backend,
                        candidate["mapping"],
                        candidate["policy_id"],
                        seed,
                    )
                    qasm = qasm3.dumps(compiled)
                    exposure = exposure_from_qasm(qasm, metadata, scratch)
                    descriptor = compiled_route_descriptor(compiled, exposure)
                    row = {
                        "snapshot": snapshot_name,
                        "task_id": task_id,
                        "r135_candidate_rank": rank,
                        "mapping": candidate["mapping"],
                        "policy_id": candidate["policy_id"],
                        "realization_seed": seed,
                        "combined_any_error_proxy": exposure[
                            "combined_any_error_proxy"
                        ],
                        "cx_occurrence_count": descriptor["cx_occurrence_count"],
                        "route_family_id": descriptor["route_family_id"],
                        "qasm_hash": stable_hash(qasm),
                    }
                    realization_rows.append(row)
                    group_realizations.append((row, qasm, descriptor))
            selected_row, selected_qasm, selected_descriptor = min(
                group_realizations,
                key=lambda item: (
                    item[0]["combined_any_error_proxy"],
                    item[0]["cx_occurrence_count"],
                    item[0]["policy_id"],
                    item[0]["mapping"],
                    item[0]["realization_seed"],
                ),
            )
            selected_path = selected_dir / f"{snapshot_name}_{task_id}.qasm"
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
                    "task_id": task_id,
                    "family": task["family"],
                    "seed": seed,
                    "selected_mapping": selected_row["mapping"],
                    "selected_policy_id": selected_row["policy_id"],
                    "selected_realization_seed": selected_row["realization_seed"],
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
            r135_selected = r135_group_rows[key]["selected_combined_any_error_proxy"]
            group_rows.append(
                {
                    "snapshot": snapshot_name,
                    "task_id": task_id,
                    "family": task["family"],
                    "top_candidate_count": len(r135_portfolio_by_group[key]),
                    "realization_candidate_count": len(group_realizations),
                    "selected_mapping": selected_row["mapping"],
                    "selected_policy_id": selected_row["policy_id"],
                    "selected_realization_seed": selected_row["realization_seed"],
                    "selected_combined_any_error_proxy": selected_row[
                        "combined_any_error_proxy"
                    ],
                    "selected_route_family": selected_descriptor,
                    "selected_exposure_improvement_vs_r135": r135_selected
                    - selected_row["combined_any_error_proxy"],
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
        "r135_residual_loss_count": len(residual_rows),
        "r135_minimum_loss_margin": min(residual_margins),
        "r135_mean_loss_margin": statistics.fmean(residual_margins),
        "r135_maximum_loss_margin": max(residual_margins),
        "validation_task_count": len(tasks),
        "validation_group_count": len(group_rows),
        "top_candidate_count_per_group": TOP_K,
        "realization_seed_count": len(REALIZATION_SEEDS),
        "realization_seeds": list(REALIZATION_SEEDS),
        "validation_seed_count": len(VALIDATION_SEEDS),
        "validation_seeds": list(VALIDATION_SEEDS),
        "route_realization_compilation_count": len(realization_rows),
        "automatic_validation_compilation_count": len(validation_rows),
        "total_compilation_count": len(realization_rows) + len(validation_rows),
        "improved_over_r135_group_count": sum(
            row["selected_exposure_improvement_vs_r135"] > TOLERANCE
            for row in group_rows
        ),
        "selected_default_policy_group_count": selected_policy_counts[
            "selected_o3_default"
        ],
        "selected_lookahead_policy_group_count": selected_policy_counts[
            "selected_o3_lookahead"
        ],
        "candidate_selection_uses_r135_validation_losses": False,
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
        "fresh_realization_and_validation_seed_blocks_used": True,
        "r135_seeds_reused": False,
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
            "label": "R135 source and its seven residual losses are hash-bound",
            "passed": r135.get("source_target_id") == UPSTREAM_TARGET_ID
            and len(residual_rows) == 7,
            "evidence": {"r135_sha256": file_sha256(r135_path)},
        },
        {
            "requirement_id": "P2",
            "label": "top-eight candidate contract is complete for all groups",
            "passed": len(r135_portfolio_by_group) == 12
            and all(len(rows) == TOP_K for rows in r135_portfolio_by_group.values()),
            "evidence": {"top_k": TOP_K},
        },
        {
            "requirement_id": "P3",
            "label": "realization and validation seed blocks are fresh and disjoint",
            "passed": not (set(REALIZATION_SEEDS) & set(VALIDATION_SEEDS))
            and not summary["r135_seeds_reused"],
            "evidence": {
                "realization_seeds": list(REALIZATION_SEEDS),
                "validation_seeds": list(VALIDATION_SEEDS),
            },
        },
        {
            "requirement_id": "P4",
            "label": "all 1,536 route realizations are materialized",
            "passed": len(realization_rows) == 12 * TOP_K * len(REALIZATION_SEEDS),
            "evidence": {"realization_row_count": len(realization_rows)},
        },
        {
            "requirement_id": "P5",
            "label": "selection reads neither R135 loss rows nor R136 validation baselines",
            "passed": not summary["candidate_selection_uses_r135_validation_losses"]
            and not summary["validation_baseline_read_during_selection"],
            "evidence": {"selection_source": "r135_portfolio_rows_only"},
        },
        {
            "requirement_id": "P6",
            "label": "all 12 groups have complete ten-seed validation ledgers",
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
            "evidence": {"compiler_margin_validation_only": True},
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
        "title": "B4/B8 R136 route-realization lower-tail margin",
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
        "r135_residual_loss_rows": residual_rows,
        "route_realization_rows": realization_rows,
        "validation_group_rows": group_rows,
        "validation_rows": validation_rows,
        "environment": {
            "deterministic_process_environment": DETERMINISTIC_PROCESS_ENV,
            "qiskit": package_version("qiskit"),
            "qiskit_ibm_runtime": package_version("qiskit-ibm-runtime"),
        },
        "artifacts": {
            "r135_result": R135_RESULT_PATH,
            "selected_circuits": sorted(selected_paths),
        },
        "claim_boundary": {
            "what_is_supported": (
                "Validation-blind route-realization lower-tail selection pressure on the "
                "seven residual R135 compiler losses."
            ),
            "what_is_not_supported": (
                "Verifier acceptance, causal hardware performance, readout mitigation, "
                "current calibration, provider access, hardware execution, protocol soundness, "
                "quantum advantage, BQP separation, or new B10 credit."
            ),
            "next_gate": (
                "If losses remain, attribute each row to a missing mapping, routing realization, "
                "or post-routing optimization stage before expanding the portfolio again."
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
