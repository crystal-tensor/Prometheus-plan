#!/usr/bin/env python3
"""T-B4-002ad/T-B8-003ah: validate seed-robust layout ranking on unseen seeds."""

from __future__ import annotations

import argparse
import json
import math
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from qiskit import qasm3, transpile

from b4_b8_r119_private_observable_bundle_gate import build_bundle_tasks
from b4_b8_r121_private_bundle_shot_sweep import basis_circuit, stable_hash, write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r128_transpiler_loop_layout_ranking import (
    OPTIMIZATION_LEVEL,
    SNAPSHOT_CLASSES,
    aggregate,
    exposure_from_qasm,
    package_version,
)


METHOD = "b4_b8_r129_seed_robust_layout_ranking_v0"
STATUS = "unseen_transpiler_seed_robustness_boundary"
MODEL_STATUS = "r128_mean_selector_replaced_by_lower_tail_training_objective"
TARGET_ID = "T-B4-002ad/T-B8-003ah/T-B10-009v"
UPSTREAM_TARGET_ID = "T-B4-002ac/T-B8-003ag/T-B10-009u"
R125_RESULT_PATH = "results/B4_B8_R125_historical_snapshot_replay_v0.json"
R127_RESULT_PATH = "results/B4_B8_R127_calibration_aware_layout_design_v0.json"
R128_RESULT_PATH = "results/B4_B8_R128_transpiler_loop_layout_ranking_v0.json"
RESULT_PATH = "results/B4_B8_R129_seed_robust_layout_ranking_v0.json"
REPORT_PATH = "research/B4_B8_R129_seed_robust_layout_ranking.md"
OUT_DIR = "results/B4_B8_R129_seed_robust_layout_ranking"
TRAIN_SEEDS = tuple(range(12901, 12909))
VALIDATION_SEEDS = tuple(range(12951, 12961))
LOWER_QUANTILE = 0.20
EXPECTED_GROUPS = 6
EXPECTED_CANDIDATES_PER_GROUP = 10


def quantile(values: list[float]) -> float:
    return float(np.quantile(values, LOWER_QUANTILE, method="linear"))


def paired_summary(
    candidate_rows: list[dict[str, Any]], default_rows: list[dict[str, Any]]
) -> dict[str, Any]:
    default_by_seed = {row["seed"]: row for row in default_rows}
    deltas = [
        default_by_seed[row["seed"]]["combined_any_error_proxy"]
        - row["combined_any_error_proxy"]
        for row in candidate_rows
    ]
    return {
        "mean_exposure_delta_vs_default": float(np.mean(deltas)),
        "minimum_exposure_delta_vs_default": min(deltas),
        "maximum_exposure_delta_vs_default": max(deltas),
        "lower_quantile_exposure_delta_vs_default": quantile(deltas),
        "seed_win_count_vs_default": sum(delta > 0.0 for delta in deltas),
        "seed_tie_count_vs_default": sum(abs(delta) <= 1e-15 for delta in deltas),
        "seed_loss_count_vs_default": sum(delta < 0.0 for delta in deltas),
        "paired_delta_rows": [
            {
                "seed": row["seed"],
                "candidate_combined_any_error_proxy": row[
                    "combined_any_error_proxy"
                ],
                "default_combined_any_error_proxy": default_by_seed[row["seed"]][
                    "combined_any_error_proxy"
                ],
                "exposure_delta_vs_default": default_by_seed[row["seed"]][
                    "combined_any_error_proxy"
                ]
                - row["combined_any_error_proxy"],
            }
            for row in candidate_rows
        ],
    }


def compile_rows(
    representative: Any,
    backend: Any,
    metadata: dict[str, Any],
    seeds: tuple[int, ...],
    scratch: Path,
    mapping: list[int] | None,
) -> tuple[list[dict[str, Any]], dict[int, str]]:
    rows = []
    qasm_by_seed = {}
    for seed in seeds:
        compiled = transpile(
            representative,
            backend=backend,
            initial_layout=mapping,
            optimization_level=OPTIMIZATION_LEVEL,
            seed_transpiler=seed,
        )
        qasm = qasm3.dumps(compiled)
        qasm_by_seed[seed] = qasm
        exposure = exposure_from_qasm(qasm, metadata, scratch)
        rows.append(
            {
                "seed": seed,
                "combined_any_error_proxy": exposure["combined_any_error_proxy"],
                "readout_any_error_proxy": exposure["readout_any_error_proxy"],
                "cx_any_error_proxy": exposure["cx_any_error_proxy"],
                "cx_occurrence_count": exposure["cx_occurrence_count"],
                "measurement_map_preserves_logical_order": exposure[
                    "measurement_map_preserves_logical_order"
                ],
            }
        )
    return rows, qasm_by_seed


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = []
    for row in payload["selected_layout_rows"]:
        train = row["training_paired_summary"]
        valid = row["validation_paired_summary"]
        reference = row["r128_reference_validation_paired_summary"]
        rows.append(
            "- `{snapshot}` / `{task}`: robust static rank `{rank}` mapping `{mapping}`; "
            "train lower-20%/wins `{train_q:.4f}` / `{train_wins}/8`; unseen "
            "lower-20%/mean/wins `{valid_q:.4f}` / `{valid_mean:.4f}` / "
            "`{valid_wins}/10`; R128 unseen mean/wins `{ref_mean:.4f}` / "
            "`{ref_wins}/10`; selector changed `{changed}`.".format(
                snapshot=row["snapshot"],
                task=row["task_id"],
                rank=row["selected_static_rank"],
                mapping=row["selected_mapping"],
                train_q=train["lower_quantile_exposure_delta_vs_default"],
                train_wins=train["seed_win_count_vs_default"],
                valid_q=valid["lower_quantile_exposure_delta_vs_default"],
                valid_mean=valid["mean_exposure_delta_vs_default"],
                valid_wins=valid["seed_win_count_vs_default"],
                ref_mean=reference["mean_exposure_delta_vs_default"],
                ref_wins=reference["seed_win_count_vs_default"],
                changed=row["selector_changed_from_r128"],
            )
        )
    requirements = "\n".join(
        f"- `{row['requirement_id']}` {'PASS' if row['passed'] else 'FAIL'}: {row['label']}"
        for row in payload["requirements"]
    )
    return f"""# B4/B8 R129 Seed-Robust Layout Ranking

## Result

- Training seeds: `{summary['training_seed_count']}`
- Unseen validation seeds: `{summary['validation_seed_count']}`
- Candidate training compilations: `{summary['candidate_training_compilation_count']}`
- Total same-condition compilations: `{summary['total_compilation_count']}`
- Selectors changed from R128: `{summary['selector_changed_from_r128_count']}` / `6`
- Groups with positive unseen mean delta: `{summary['positive_validation_mean_count']}` / `6`
- Groups with positive unseen lower-20% delta: `{summary['positive_validation_lower_quantile_count']}` / `6`
- Groups winning at least 8/10 unseen seeds: `{summary['eight_of_ten_validation_win_count']}` / `6`
- Robust unseen-seed gate passed: `{summary['robust_unseen_seed_gate_passed']}`
- Acceptance holdout executed: `False`
- New credit delta: `0`

## Per-Group Evidence

{chr(10).join(rows)}

The selector is fit only on eight declared training seeds. It maximizes the
20th-percentile paired exposure gain over automatic layout, then training wins,
mean gain, candidate worst exposure, mean CX count, static rank, and mapping.
Ten disjoint validation seeds are compiled only after selection. The R128
mean selector is replayed on the same validation seeds as a frozen reference.

## Gate

Every group must have positive unseen mean and lower-20% exposure deltas and
win at least eight of ten unseen seeds. This is a compiler-design validation
gate, not the R125 verifier acceptance holdout. Passing it would authorize a
separate preregistration step; it would not itself create B4, B8, or B10 credit.

## Requirements

{requirements}

## Claim Boundary

Supported: a deterministic train/validation test of lower-tail transpiler-seed
layout ranking over the 60 predeclared R127 candidates. Not supported: verifier
holdout performance, readout mitigation, current calibration, provider access,
hardware execution, protocol soundness, quantum advantage, BQP separation, or
new B10 credit.
"""


def run_gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    r125_path = root / R125_RESULT_PATH
    r127_path = root / R127_RESULT_PATH
    r128_path = root / R128_RESULT_PATH
    r125 = json.loads(r125_path.read_text(encoding="utf-8"))
    r127 = json.loads(r127_path.read_text(encoding="utf-8"))
    r128 = json.loads(r128_path.read_text(encoding="utf-8"))
    if r128.get("status") != "transpiler_loop_layout_ranking_boundary":
        raise ValueError("R129 requires the R128 transpiler-loop boundary")
    if set(TRAIN_SEEDS) & set(VALIDATION_SEEDS):
        raise ValueError("training and validation seed blocks must be disjoint")

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in r127["top_layout_rows"]:
        grouped[(row["snapshot"], row["task_id"])].append(row)
    if len(grouped) != EXPECTED_GROUPS or any(
        len(rows) != EXPECTED_CANDIDATES_PER_GROUP for rows in grouped.values()
    ):
        raise ValueError("R127 candidate groups are incomplete")
    r128_selected = {
        (row["snapshot"], row["task_id"]): row for row in r128["selected_layout_rows"]
    }

    output = root / OUT_DIR
    circuits_dir = output / "validation_circuits"
    circuits_dir.mkdir(parents=True, exist_ok=True)
    for old in circuits_dir.glob("*.qasm"):
        old.unlink()

    tasks = {task["task_id"]: task for task in build_bundle_tasks()}
    candidate_training_rows = []
    selected_rows = []
    circuit_files = []
    candidate_training_compilations = 0
    training_default_compilations = 0
    validation_selected_compilations = 0
    validation_default_compilations = 0
    validation_reference_compilations = 0
    with tempfile.TemporaryDirectory(prefix="r129-") as temporary:
        scratch = Path(temporary) / "compiled.qasm"
        for snapshot_name, task_id in sorted(grouped):
            backend = SNAPSHOT_CLASSES[snapshot_name]()
            metadata = r125["snapshot_metadata"][snapshot_name]
            representative = basis_circuit(
                tasks[task_id]["circuit"],
                tuple("Z" for _ in range(tasks[task_id]["circuit"].num_qubits)),
            )
            training_default_rows, _ = compile_rows(
                representative, backend, metadata, TRAIN_SEEDS, scratch, None
            )
            training_default_compilations += len(training_default_rows)
            group_rows = []
            for candidate in sorted(grouped[(snapshot_name, task_id)], key=lambda row: row["rank"]):
                candidate_rows, _ = compile_rows(
                    representative,
                    backend,
                    metadata,
                    TRAIN_SEEDS,
                    scratch,
                    candidate["mapping"],
                )
                candidate_training_compilations += len(candidate_rows)
                paired = paired_summary(candidate_rows, training_default_rows)
                row = {
                    "snapshot": snapshot_name,
                    "task_id": task_id,
                    "static_rank": candidate["rank"],
                    "mapping": candidate["mapping"],
                    "candidate_aggregate": aggregate(candidate_rows),
                    "default_aggregate": aggregate(training_default_rows),
                    "paired_summary": paired,
                }
                group_rows.append(row)
                candidate_training_rows.append(row)
            selected = min(
                group_rows,
                key=lambda row: (
                    -row["paired_summary"]["lower_quantile_exposure_delta_vs_default"],
                    -row["paired_summary"]["seed_win_count_vs_default"],
                    -row["paired_summary"]["mean_exposure_delta_vs_default"],
                    row["candidate_aggregate"]["maximum_combined_any_error_proxy"],
                    row["candidate_aggregate"]["mean_cx_occurrence_count"],
                    row["static_rank"],
                    row["mapping"],
                ),
            )

            validation_default_rows, _ = compile_rows(
                representative, backend, metadata, VALIDATION_SEEDS, scratch, None
            )
            validation_default_compilations += len(validation_default_rows)
            validation_selected_rows, selected_qasm = compile_rows(
                representative,
                backend,
                metadata,
                VALIDATION_SEEDS,
                scratch,
                selected["mapping"],
            )
            validation_selected_compilations += len(validation_selected_rows)
            reference_mapping = r128_selected[(snapshot_name, task_id)]["selected_mapping"]
            validation_reference_rows, _ = compile_rows(
                representative,
                backend,
                metadata,
                VALIDATION_SEEDS,
                scratch,
                reference_mapping,
            )
            validation_reference_compilations += len(validation_reference_rows)
            selected_paths = []
            for seed in VALIDATION_SEEDS:
                path = circuits_dir / f"{snapshot_name}_{task_id}_seed_{seed}.qasm"
                path.write_text(selected_qasm[seed], encoding="utf-8")
                relative = str(path.relative_to(root))
                selected_paths.append(relative)
                circuit_files.append(relative)
            validation_paired = paired_summary(
                validation_selected_rows, validation_default_rows
            )
            reference_paired = paired_summary(
                validation_reference_rows, validation_default_rows
            )
            selected_rows.append(
                {
                    "snapshot": snapshot_name,
                    "snapshot_sha256": metadata["sha256"],
                    "task_id": task_id,
                    "selected_mapping": selected["mapping"],
                    "selected_static_rank": selected["static_rank"],
                    "r128_reference_mapping": reference_mapping,
                    "selector_changed_from_r128": selected["mapping"] != reference_mapping,
                    "training_candidate_aggregate": selected["candidate_aggregate"],
                    "training_default_aggregate": selected["default_aggregate"],
                    "training_paired_summary": selected["paired_summary"],
                    "validation_candidate_aggregate": aggregate(validation_selected_rows),
                    "validation_default_aggregate": aggregate(validation_default_rows),
                    "validation_paired_summary": validation_paired,
                    "r128_reference_validation_aggregate": aggregate(
                        validation_reference_rows
                    ),
                    "r128_reference_validation_paired_summary": reference_paired,
                    "validation_mean_exposure_improvement_over_r128_selector": (
                        aggregate(validation_reference_rows)[
                            "mean_combined_any_error_proxy"
                        ]
                        - aggregate(validation_selected_rows)[
                            "mean_combined_any_error_proxy"
                        ]
                    ),
                    "all_validation_measurement_maps_preserve_logical_order": all(
                        row["measurement_map_preserves_logical_order"]
                        for row in validation_selected_rows
                    ),
                    "validation_circuit_paths": selected_paths,
                    "validation_circuit_sha256": {
                        path: file_sha256(root / path) for path in selected_paths
                    },
                }
            )

    positive_mean_count = sum(
        row["validation_paired_summary"]["mean_exposure_delta_vs_default"] > 0.0
        for row in selected_rows
    )
    positive_quantile_count = sum(
        row["validation_paired_summary"][
            "lower_quantile_exposure_delta_vs_default"
        ]
        > 0.0
        for row in selected_rows
    )
    eight_of_ten_count = sum(
        row["validation_paired_summary"]["seed_win_count_vs_default"] >= 8
        for row in selected_rows
    )
    robust_gate = all(
        row["validation_paired_summary"]["mean_exposure_delta_vs_default"] > 0.0
        and row["validation_paired_summary"][
            "lower_quantile_exposure_delta_vs_default"
        ]
        > 0.0
        and row["validation_paired_summary"]["seed_win_count_vs_default"] >= 8
        for row in selected_rows
    )
    total_compilations = (
        candidate_training_compilations
        + training_default_compilations
        + validation_selected_compilations
        + validation_default_compilations
        + validation_reference_compilations
    )
    summary = {
        "snapshot_count": len(SNAPSHOT_CLASSES),
        "task_count": len(tasks),
        "candidate_count": len(candidate_training_rows),
        "training_seed_count": len(TRAIN_SEEDS),
        "validation_seed_count": len(VALIDATION_SEEDS),
        "candidate_training_compilation_count": candidate_training_compilations,
        "training_default_compilation_count": training_default_compilations,
        "validation_selected_compilation_count": validation_selected_compilations,
        "validation_default_compilation_count": validation_default_compilations,
        "validation_reference_compilation_count": validation_reference_compilations,
        "total_compilation_count": total_compilations,
        "selector_changed_from_r128_count": sum(
            row["selector_changed_from_r128"] for row in selected_rows
        ),
        "positive_validation_mean_count": positive_mean_count,
        "positive_validation_lower_quantile_count": positive_quantile_count,
        "eight_of_ten_validation_win_count": eight_of_ten_count,
        "validation_improvement_over_r128_selector_count": sum(
            row["validation_mean_exposure_improvement_over_r128_selector"] > 1e-15
            for row in selected_rows
        ),
        "robust_unseen_seed_gate_passed": robust_gate,
        "training_seeds": list(TRAIN_SEEDS),
        "validation_seeds": list(VALIDATION_SEEDS),
        "lower_quantile": LOWER_QUANTILE,
        "optimization_level": OPTIMIZATION_LEVEL,
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
            "label": "R127 and R128 sources are hash-bound before R129 selection",
            "passed": len(candidate_training_rows) == 60,
            "evidence": {
                "r127_sha256": file_sha256(r127_path),
                "r128_sha256": file_sha256(r128_path),
            },
        },
        {
            "requirement_id": "P2",
            "label": "training and unseen validation transpiler seeds are disjoint",
            "passed": not (set(TRAIN_SEEDS) & set(VALIDATION_SEEDS)),
            "evidence": {
                "training_seeds": list(TRAIN_SEEDS),
                "validation_seeds": list(VALIDATION_SEEDS),
            },
        },
        {
            "requirement_id": "P3",
            "label": "all 60 retained candidates are trained on all eight training seeds",
            "passed": candidate_training_compilations == 60 * 8,
            "evidence": {
                "candidate_training_compilation_count": candidate_training_compilations
            },
        },
        {
            "requirement_id": "P4",
            "label": "selection uses lower-tail paired gain before mean exposure",
            "passed": len(selected_rows) == EXPECTED_GROUPS,
            "evidence": {
                "selection_order": [
                    "lower_quantile_gain",
                    "win_count",
                    "mean_gain",
                    "worst_candidate_exposure",
                    "mean_cx_count",
                    "static_rank",
                    "mapping",
                ]
            },
        },
        {
            "requirement_id": "P5",
            "label": "ten unseen seeds are evaluated for selected, default, and R128 layouts",
            "passed": validation_selected_compilations == 60
            and validation_default_compilations == 60
            and validation_reference_compilations == 60,
            "evidence": {"validation_compilation_count": 180},
        },
        {
            "requirement_id": "P6",
            "label": "all 60 selected validation QASM artifacts preserve measurement order",
            "passed": len(circuit_files) == 60
            and all(
                row["all_validation_measurement_maps_preserve_logical_order"]
                for row in selected_rows
            ),
            "evidence": {"validation_circuit_count": len(circuit_files)},
        },
        {
            "requirement_id": "P7",
            "label": "the robust unseen-seed gate is evaluated on all six groups",
            "passed": all(
                math.isfinite(
                    row["validation_paired_summary"][
                        "lower_quantile_exposure_delta_vs_default"
                    ]
                )
                for row in selected_rows
            ),
            "evidence": {"robust_unseen_seed_gate_passed": robust_gate},
        },
        {
            "requirement_id": "P8",
            "label": "R125 acceptance rows, verifier holdout, and mitigation remain excluded",
            "passed": not summary["r125_acceptance_rows_read"]
            and not summary["acceptance_holdout_executed"]
            and not summary["readout_mitigation_tested"],
            "evidence": {"compiler_design_validation_only": True},
        },
        {
            "requirement_id": "P9",
            "label": "historical snapshots remain separate from current and hardware evidence",
            "passed": not summary["current_backend_calibration_used"]
            and not summary["hardware_execution_performed"],
            "evidence": {"evidence_class": "historical_snapshot_seed_validation"},
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
        "title": "B4/B8 R129 seed-robust layout ranking",
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
        "selected_layout_rows": selected_rows,
        "candidate_training_rows": candidate_training_rows,
        "environment": {
            "qiskit": package_version("qiskit"),
            "qiskit_ibm_runtime": package_version("qiskit-ibm-runtime"),
            "numpy": package_version("numpy"),
        },
        "artifacts": {
            "r127_result": R127_RESULT_PATH,
            "r128_result": R128_RESULT_PATH,
            "validation_circuits": sorted(circuit_files),
        },
        "claim_boundary": {
            "what_is_supported": (
                "Disjoint-seed validation of lower-tail transpiler layout ranking over "
                "the 60 predeclared R127 candidates on frozen snapshots."
            ),
            "what_is_not_supported": (
                "Verifier holdout performance, readout mitigation, current calibration, "
                "provider access, hardware execution, protocol soundness, quantum advantage, "
                "BQP separation, or new B10 credit."
            ),
            "next_gate": (
                "If unseen-seed robustness fails, diagnose group-level route variance and "
                "expand the candidate objective without opening the verifier holdout."
            ),
        },
    }
    payload["payload_hash"] = stable_hash(payload)
    write_json(root / RESULT_PATH, payload)
    (root / REPORT_PATH).write_text(report(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    payload = run_gate(args.root)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
