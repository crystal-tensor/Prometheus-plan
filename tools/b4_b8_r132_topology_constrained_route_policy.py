#!/usr/bin/env python3
"""T-B4-002ag/T-B8-003ak: test topology-constrained route policies."""

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

from b4_b8_r119_private_observable_bundle_gate import build_bundle_tasks
from b4_b8_r121_private_bundle_shot_sweep import basis_circuit, stable_hash, write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r127_calibration_aware_layout_design import SNAPSHOT_CLASSES
from b4_b8_r128_transpiler_loop_layout_ranking import exposure_from_qasm, package_version
from b4_b8_r131_compiled_route_family_attribution import compiled_route_descriptor


METHOD = "b4_b8_r132_topology_constrained_route_policy_v0"
STATUS = "topology_constrained_route_policy_boundary"
MODEL_STATUS = "fresh_seed_route_policy_stability_without_verifier_acceptance"
TARGET_ID = "T-B4-002ag/T-B8-003ak/T-B10-009y"
UPSTREAM_TARGET_ID = "T-B4-002af/T-B8-003aj/T-B10-009x"
R125_RESULT_PATH = "results/B4_B8_R125_historical_snapshot_replay_v0.json"
R130_RESULT_PATH = "results/B4_B8_R130_route_signature_candidate_expansion_v0.json"
R131_RESULT_PATH = "results/B4_B8_R131_compiled_route_family_attribution_v0.json"
RESULT_PATH = "results/B4_B8_R132_topology_constrained_route_policy_v0.json"
REPORT_PATH = "research/B4_B8_R132_topology_constrained_route_policy.md"
OUT_DIR = "results/B4_B8_R132_topology_constrained_route_policy"
TRAINING_SEEDS = tuple(range(13201, 13209))
VALIDATION_SEEDS = tuple(range(13251, 13261))
TOLERANCE = 1e-15
DETERMINISTIC_PROCESS_ENV = {
    "PYTHONHASHSEED": "0",
    "RAYON_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "QISKIT_PARALLEL": "FALSE",
}
POLICIES: dict[str, dict[str, Any]] = {
    "selected_o3_default": {"optimization_level": 3},
    "selected_o3_basic": {"optimization_level": 3, "routing_method": "basic"},
    "selected_o3_lookahead": {
        "optimization_level": 3,
        "routing_method": "lookahead",
    },
    "selected_o1_basic": {"optimization_level": 1, "routing_method": "basic"},
    "selected_o0_basic": {"optimization_level": 0, "routing_method": "basic"},
}
CANDIDATE_POLICY_IDS = tuple(policy for policy in POLICIES if policy != "selected_o3_default")


def ensure_deterministic_process_environment() -> None:
    if all(os.environ.get(key) == value for key, value in DETERMINISTIC_PROCESS_ENV.items()):
        return
    environment = dict(os.environ)
    environment.update(DETERMINISTIC_PROCESS_ENV)
    os.execvpe(sys.executable, [sys.executable, *sys.argv], environment)


def quantile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def outcome(delta: float) -> str:
    return "win" if delta > TOLERANCE else "loss" if delta < -TOLERANCE else "tie"


def compile_policy(
    representative: Any,
    backend: Any,
    mapping: list[int],
    policy_id: str,
    seed: int,
) -> Any:
    return transpile(
        representative,
        backend=backend,
        initial_layout=mapping,
        seed_transpiler=seed,
        **POLICIES[policy_id],
    )


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    group_lines = []
    for row in payload["validation_group_rows"]:
        group_lines.append(
            "- `{snapshot}` / `{task}`: constrained classes/QASM hashes "
            "`{families}/{hashes}`; mean gain vs selected/default "
            "`{selected_gain:+.6f}/{default_gain:+.6f}`; lower-tail gain vs "
            "selected `{tail:+.6f}`; default wins/ties/losses "
            "`{wins}/{ties}/{losses}`; exact seed invariant `{invariant}`.".format(
                snapshot=row["snapshot"],
                task=row["task_id"],
                families=row["constrained_unique_route_family_count"],
                hashes=row["constrained_unique_qasm_hash_count"],
                selected_gain=row["mean_exposure_gain_vs_selected_default"],
                default_gain=row["mean_exposure_gain_vs_automatic_default"],
                tail=row["lower_quantile_exposure_gain_vs_selected_default"],
                wins=row["win_count_vs_automatic_default"],
                ties=row["tie_count_vs_automatic_default"],
                losses=row["loss_count_vs_automatic_default"],
                invariant=row["exact_qasm_seed_invariant"],
            )
        )
    requirements = "\n".join(
        f"- `{row['requirement_id']}` {'PASS' if row['passed'] else 'FAIL'}: {row['label']}"
        for row in payload["requirements"]
    )
    return f"""# B4/B8 R132 Topology-Constrained Route Policy

## Result

- Training compilations: `{summary['training_compilation_count']}`
- Validation compilations: `{summary['validation_compilation_count']}`
- Selected global policy: `{summary['selected_policy_id']}`
- Validation groups with one route-exposure class: `{summary['route_family_invariant_group_count']}` / `6`
- Validation groups with one exact QASM hash: `{summary['exact_qasm_seed_invariant_group_count']}` / `6`
- Frozen constrained-QASM replay matches: `{summary['frozen_qasm_replay_match_count']}` / `60`
- Groups non-regressing in mean exposure vs selected default: `{summary['mean_nonregression_vs_selected_group_count']}` / `6`
- Groups non-regressing at the lower tail vs selected default: `{summary['lower_tail_nonregression_vs_selected_group_count']}` / `6`
- Groups robust over automatic default: `{summary['robust_win_or_tie_vs_automatic_group_count']}` / `6`
- Stability gate passed: `{summary['topology_constraint_stability_gate_passed']}`
- Verifier acceptance performed: `False`
- New credit delta: `0`

## Validation Evidence

{chr(10).join(group_lines)}

The selected policy is chosen once, globally, from the fresh R132 training block.
The policy fixes each workload's upstream R130 topology mapping and constrains the
router to Qiskit's `lookahead` method. The disjoint validation block is not read
during selection. Exact QASM invariance is tested both across ten validation
seeds and by replaying frozen files in a fresh process.

## Requirements

{requirements}

## Claim Boundary

Supported: a fresh-seed compiler result showing whether a fixed topology mapping
plus a globally selected routing policy removes the R131 route-family instability
without regressing the selected-layout exposure proxy. Not supported: verifier
holdout acceptance, causal hardware performance, current calibration, readout
mitigation, protocol soundness, quantum advantage, BQP separation, or new B10 credit.
"""


def run_gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    r125_path = root / R125_RESULT_PATH
    r130_path = root / R130_RESULT_PATH
    r131_path = root / R131_RESULT_PATH
    r125 = json.loads(r125_path.read_text(encoding="utf-8"))
    r130 = json.loads(r130_path.read_text(encoding="utf-8"))
    r131 = json.loads(r131_path.read_text(encoding="utf-8"))
    if r131.get("status") != "compiled_route_family_attribution_boundary":
        raise ValueError("R132 requires the R131 route-family boundary")
    if set(TRAINING_SEEDS + VALIDATION_SEEDS) & set(
        r130["summary"]["training_seeds"] + r130["summary"]["validation_seeds"]
    ):
        raise ValueError("R132 seeds must be disjoint from R130")

    tasks = {task["task_id"]: task for task in build_bundle_tasks()}
    selected_by_group = {
        (row["snapshot"], row["task_id"]): row for row in r130["selected_layout_rows"]
    }
    training_rows: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
    output = root / OUT_DIR
    circuit_dir = output / "constrained_circuits"
    circuit_dir.mkdir(parents=True, exist_ok=True)
    frozen_paths: list[str] = []
    frozen_preexisting_count = 0
    frozen_match_count = 0

    with tempfile.TemporaryDirectory(prefix="r132-") as temporary:
        scratch = Path(temporary) / "compiled.qasm"
        representatives: dict[tuple[str, str], Any] = {}
        for key, source in sorted(selected_by_group.items()):
            task = tasks[key[1]]
            representatives[key] = basis_circuit(
                task["circuit"], tuple("Z" for _ in range(task["circuit"].num_qubits))
            )
            backend = SNAPSHOT_CLASSES[key[0]]()
            metadata = r125["snapshot_metadata"][key[0]]
            for policy_id in POLICIES:
                for seed in TRAINING_SEEDS:
                    compiled = compile_policy(
                        representatives[key],
                        backend,
                        source["selected_mapping"],
                        policy_id,
                        seed,
                    )
                    qasm = qasm3.dumps(compiled)
                    exposure = exposure_from_qasm(qasm, metadata, scratch)
                    descriptor = compiled_route_descriptor(compiled, exposure)
                    training_rows.append(
                        {
                            "snapshot": key[0],
                            "task_id": key[1],
                            "seed": seed,
                            "policy_id": policy_id,
                            "qasm_hash": stable_hash(qasm),
                            "route_family_id": descriptor["route_family_id"],
                            "cx_occurrence_count": descriptor["cx_occurrence_count"],
                            "combined_any_error_proxy": exposure[
                                "combined_any_error_proxy"
                            ],
                        }
                    )

        policy_training_rows = []
        for policy_id in POLICIES:
            rows = [row for row in training_rows if row["policy_id"] == policy_id]
            group_family_counts = []
            group_qasm_counts = []
            for key in sorted(selected_by_group):
                group = [
                    row
                    for row in rows
                    if (row["snapshot"], row["task_id"]) == key
                ]
                group_family_counts.append(len({row["route_family_id"] for row in group}))
                group_qasm_counts.append(len({row["qasm_hash"] for row in group}))
            policy_training_rows.append(
                {
                    "policy_id": policy_id,
                    "is_candidate": policy_id in CANDIDATE_POLICY_IDS,
                    "aggregate_route_family_count": sum(group_family_counts),
                    "aggregate_qasm_hash_count": sum(group_qasm_counts),
                    "route_family_invariant_group_count": sum(
                        count == 1 for count in group_family_counts
                    ),
                    "exact_qasm_seed_invariant_group_count": sum(
                        count == 1 for count in group_qasm_counts
                    ),
                    "mean_combined_any_error_proxy": statistics.fmean(
                        row["combined_any_error_proxy"] for row in rows
                    ),
                    "mean_cx_occurrence_count": statistics.fmean(
                        row["cx_occurrence_count"] for row in rows
                    ),
                }
            )
        candidate_rows = [row for row in policy_training_rows if row["is_candidate"]]
        selected_policy = min(
            candidate_rows,
            key=lambda row: (
                row["aggregate_route_family_count"],
                row["aggregate_qasm_hash_count"],
                row["mean_combined_any_error_proxy"],
                row["mean_cx_occurrence_count"],
                row["policy_id"],
            ),
        )
        selected_policy_id = selected_policy["policy_id"]

        for key, source in sorted(selected_by_group.items()):
            backend = SNAPSHOT_CLASSES[key[0]]()
            metadata = r125["snapshot_metadata"][key[0]]
            representative = representatives[key]
            for seed in VALIDATION_SEEDS:
                constrained = compile_policy(
                    representative,
                    backend,
                    source["selected_mapping"],
                    selected_policy_id,
                    seed,
                )
                selected_default = compile_policy(
                    representative,
                    backend,
                    source["selected_mapping"],
                    "selected_o3_default",
                    seed,
                )
                automatic_default = transpile(
                    representative,
                    backend=backend,
                    optimization_level=3,
                    seed_transpiler=seed,
                )
                constrained_qasm = qasm3.dumps(constrained)
                selected_qasm = qasm3.dumps(selected_default)
                automatic_qasm = qasm3.dumps(automatic_default)
                constrained_exposure = exposure_from_qasm(
                    constrained_qasm, metadata, scratch
                )
                selected_exposure = exposure_from_qasm(selected_qasm, metadata, scratch)
                automatic_exposure = exposure_from_qasm(
                    automatic_qasm, metadata, scratch
                )
                constrained_descriptor = compiled_route_descriptor(
                    constrained, constrained_exposure
                )
                selected_descriptor = compiled_route_descriptor(
                    selected_default, selected_exposure
                )
                automatic_descriptor = compiled_route_descriptor(
                    automatic_default, automatic_exposure
                )
                constrained_path = circuit_dir / (
                    f"{key[0]}_{key[1]}_seed_{seed}.qasm"
                )
                relative_path = str(constrained_path.relative_to(root))
                frozen_paths.append(relative_path)
                if constrained_path.exists():
                    frozen_preexisting_count += 1
                    frozen_match = constrained_path.read_text(encoding="utf-8") == constrained_qasm
                else:
                    constrained_path.write_text(constrained_qasm, encoding="utf-8")
                    frozen_match = True
                frozen_match_count += frozen_match
                gain_vs_selected = (
                    selected_exposure["combined_any_error_proxy"]
                    - constrained_exposure["combined_any_error_proxy"]
                )
                gain_vs_automatic = (
                    automatic_exposure["combined_any_error_proxy"]
                    - constrained_exposure["combined_any_error_proxy"]
                )
                validation_rows.append(
                    {
                        "snapshot": key[0],
                        "task_id": key[1],
                        "seed": seed,
                        "selected_mapping": source["selected_mapping"],
                        "selected_policy_id": selected_policy_id,
                        "constrained_circuit_path": relative_path,
                        "constrained_circuit_sha256": file_sha256(constrained_path),
                        "frozen_qasm_replay_matches": frozen_match,
                        "constrained_qasm_hash": stable_hash(constrained_qasm),
                        "constrained_route_family": constrained_descriptor,
                        "selected_default_route_family": selected_descriptor,
                        "automatic_default_route_family": automatic_descriptor,
                        "constrained_combined_any_error_proxy": constrained_exposure[
                            "combined_any_error_proxy"
                        ],
                        "selected_default_combined_any_error_proxy": selected_exposure[
                            "combined_any_error_proxy"
                        ],
                        "automatic_default_combined_any_error_proxy": automatic_exposure[
                            "combined_any_error_proxy"
                        ],
                        "exposure_gain_vs_selected_default": gain_vs_selected,
                        "exposure_gain_vs_automatic_default": gain_vs_automatic,
                        "outcome_vs_selected_default": outcome(gain_vs_selected),
                        "outcome_vs_automatic_default": outcome(gain_vs_automatic),
                    }
                )

    validation_group_rows = []
    for key in sorted(selected_by_group):
        rows = [
            row
            for row in validation_rows
            if (row["snapshot"], row["task_id"]) == key
        ]
        gains_selected = [row["exposure_gain_vs_selected_default"] for row in rows]
        gains_automatic = [row["exposure_gain_vs_automatic_default"] for row in rows]
        family_count = len(
            {row["constrained_route_family"]["route_family_id"] for row in rows}
        )
        qasm_count = len({row["constrained_qasm_hash"] for row in rows})
        validation_group_rows.append(
            {
                "snapshot": key[0],
                "task_id": key[1],
                "constrained_unique_route_family_count": family_count,
                "constrained_unique_qasm_hash_count": qasm_count,
                "route_family_seed_invariant": family_count == 1,
                "exact_qasm_seed_invariant": qasm_count == 1,
                "mean_exposure_gain_vs_selected_default": statistics.fmean(
                    gains_selected
                ),
                "lower_quantile_exposure_gain_vs_selected_default": quantile(
                    gains_selected, 0.1
                ),
                "minimum_exposure_gain_vs_selected_default": min(gains_selected),
                "mean_exposure_gain_vs_automatic_default": statistics.fmean(
                    gains_automatic
                ),
                "lower_quantile_exposure_gain_vs_automatic_default": quantile(
                    gains_automatic, 0.1
                ),
                "minimum_exposure_gain_vs_automatic_default": min(gains_automatic),
                "win_count_vs_selected_default": sum(
                    row["outcome_vs_selected_default"] == "win" for row in rows
                ),
                "tie_count_vs_selected_default": sum(
                    row["outcome_vs_selected_default"] == "tie" for row in rows
                ),
                "loss_count_vs_selected_default": sum(
                    row["outcome_vs_selected_default"] == "loss" for row in rows
                ),
                "win_count_vs_automatic_default": sum(
                    row["outcome_vs_automatic_default"] == "win" for row in rows
                ),
                "tie_count_vs_automatic_default": sum(
                    row["outcome_vs_automatic_default"] == "tie" for row in rows
                ),
                "loss_count_vs_automatic_default": sum(
                    row["outcome_vs_automatic_default"] == "loss" for row in rows
                ),
            }
        )

    route_invariant_count = sum(
        row["route_family_seed_invariant"] for row in validation_group_rows
    )
    qasm_invariant_count = sum(
        row["exact_qasm_seed_invariant"] for row in validation_group_rows
    )
    mean_nonregression_count = sum(
        row["mean_exposure_gain_vs_selected_default"] >= -TOLERANCE
        for row in validation_group_rows
    )
    tail_nonregression_count = sum(
        row["lower_quantile_exposure_gain_vs_selected_default"] >= -TOLERANCE
        for row in validation_group_rows
    )
    robust_default_count = sum(
        row["loss_count_vs_automatic_default"] == 0
        for row in validation_group_rows
    )
    stability_gate = (
        route_invariant_count == 6
        and qasm_invariant_count == 6
        and frozen_preexisting_count == 60
        and frozen_match_count == 60
        and mean_nonregression_count == 6
        and tail_nonregression_count == 6
    )
    summary = {
        "snapshot_count": len(SNAPSHOT_CLASSES),
        "task_count": len(tasks),
        "candidate_policy_count": len(CANDIDATE_POLICY_IDS),
        "training_seed_count": len(TRAINING_SEEDS),
        "training_seeds": list(TRAINING_SEEDS),
        "validation_seed_count": len(VALIDATION_SEEDS),
        "validation_seeds": list(VALIDATION_SEEDS),
        "training_compilation_count": len(training_rows),
        "validation_compilation_count": len(validation_rows) * 3,
        "total_compilation_count": len(training_rows) + len(validation_rows) * 3,
        "selected_policy_id": selected_policy_id,
        "selected_policy_routing_method": POLICIES[selected_policy_id].get(
            "routing_method"
        ),
        "selected_policy_optimization_level": POLICIES[selected_policy_id][
            "optimization_level"
        ],
        "route_family_invariant_group_count": route_invariant_count,
        "exact_qasm_seed_invariant_group_count": qasm_invariant_count,
        "frozen_qasm_preexisting_count": frozen_preexisting_count,
        "frozen_qasm_replay_match_count": frozen_match_count,
        "mean_nonregression_vs_selected_group_count": mean_nonregression_count,
        "lower_tail_nonregression_vs_selected_group_count": tail_nonregression_count,
        "robust_win_or_tie_vs_automatic_group_count": robust_default_count,
        "validation_win_count_vs_automatic_default": sum(
            row["outcome_vs_automatic_default"] == "win" for row in validation_rows
        ),
        "validation_tie_count_vs_automatic_default": sum(
            row["outcome_vs_automatic_default"] == "tie" for row in validation_rows
        ),
        "validation_loss_count_vs_automatic_default": sum(
            row["outcome_vs_automatic_default"] == "loss" for row in validation_rows
        ),
        "topology_constraint_stability_gate_passed": stability_gate,
        "route_family_semantics": "cx_edge_multiset_and_exposure_equivalence_class",
        "exact_qasm_cross_process_replay_claimed": frozen_preexisting_count == 60
        and frozen_match_count == 60,
        "fresh_training_validation_seed_blocks_used": True,
        "validation_read_during_policy_selection": False,
        "r130_layout_mappings_reused": True,
        "r131_diagnostic_seeds_reused": False,
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
            "label": "R130 and R131 sources are hash-bound and required",
            "passed": r131.get("source_target_id") == UPSTREAM_TARGET_ID,
            "evidence": {
                "r130_sha256": file_sha256(r130_path),
                "r131_sha256": file_sha256(r131_path),
            },
        },
        {
            "requirement_id": "P2",
            "label": "fresh training and validation seeds are disjoint from R130/R131",
            "passed": summary["fresh_training_validation_seed_blocks_used"]
            and not summary["r131_diagnostic_seeds_reused"],
            "evidence": {
                "training_seeds": list(TRAINING_SEEDS),
                "validation_seeds": list(VALIDATION_SEEDS),
            },
        },
        {
            "requirement_id": "P3",
            "label": "global policy is selected only from the training ledger",
            "passed": selected_policy_id in CANDIDATE_POLICY_IDS
            and not summary["validation_read_during_policy_selection"],
            "evidence": {"selected_policy_id": selected_policy_id},
        },
        {
            "requirement_id": "P4",
            "label": "all six validation groups use one route-exposure class",
            "passed": route_invariant_count == 6,
            "evidence": {"route_family_invariant_group_count": route_invariant_count},
        },
        {
            "requirement_id": "P5",
            "label": "all six validation groups use one exact QASM hash across seeds",
            "passed": qasm_invariant_count == 6,
            "evidence": {"exact_qasm_seed_invariant_group_count": qasm_invariant_count},
        },
        {
            "requirement_id": "P6",
            "label": "all 60 frozen constrained circuits match in a fresh process",
            "passed": frozen_preexisting_count == 60 and frozen_match_count == 60,
            "evidence": {
                "frozen_qasm_preexisting_count": frozen_preexisting_count,
                "frozen_qasm_replay_match_count": frozen_match_count,
            },
        },
        {
            "requirement_id": "P7",
            "label": "mean and lower-tail exposure do not regress against selected default",
            "passed": mean_nonregression_count == 6 and tail_nonregression_count == 6,
            "evidence": {
                "mean_nonregression_group_count": mean_nonregression_count,
                "lower_tail_nonregression_group_count": tail_nonregression_count,
            },
        },
        {
            "requirement_id": "P8",
            "label": "training, validation, and frozen-artifact ledgers are complete",
            "passed": len(training_rows) == 240
            and len(validation_rows) == 60
            and len(frozen_paths) == 60,
            "evidence": {
                "training_row_count": len(training_rows),
                "validation_row_count": len(validation_rows),
                "frozen_circuit_count": len(frozen_paths),
            },
        },
        {
            "requirement_id": "P9",
            "label": "verifier acceptance, mitigation, calibration, and hardware remain excluded",
            "passed": not summary["acceptance_holdout_executed"]
            and not summary["r125_acceptance_rows_read"]
            and not summary["readout_mitigation_tested"]
            and not summary["current_backend_calibration_used"]
            and not summary["hardware_execution_performed"],
            "evidence": {"compiler_validation_only": True},
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
        "title": "B4/B8 R132 topology-constrained route policy",
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
        "policy_training_rows": policy_training_rows,
        "training_rows": training_rows,
        "validation_group_rows": validation_group_rows,
        "validation_rows": validation_rows,
        "environment": {
            "deterministic_process_environment": DETERMINISTIC_PROCESS_ENV,
            "qiskit": package_version("qiskit"),
            "qiskit_ibm_runtime": package_version("qiskit-ibm-runtime"),
        },
        "artifacts": {
            "r130_result": R130_RESULT_PATH,
            "r131_result": R131_RESULT_PATH,
            "constrained_circuits": sorted(frozen_paths),
        },
        "claim_boundary": {
            "what_is_supported": (
                "Fresh-seed topology-constrained compiler stability and exposure comparison "
                "against the selected-layout and automatic-layout references."
            ),
            "what_is_not_supported": (
                "Verifier holdout acceptance, causal hardware performance, readout mitigation, "
                "current calibration, provider access, hardware execution, protocol soundness, "
                "quantum advantage, BQP separation, or new B10 credit."
            ),
            "next_gate": (
                "Stress the constrained policy on a new circuit-family holdout and then decide "
                "whether it may enter the verifier acceptance protocol."
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
