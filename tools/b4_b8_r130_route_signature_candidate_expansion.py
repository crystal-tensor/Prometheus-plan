#!/usr/bin/env python3
"""T-B4-002ae/T-B8-003ai: expand layouts by route-signature diversity."""

from __future__ import annotations

import argparse
import itertools
import json
import math
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from b4_b8_r119_private_observable_bundle_gate import build_bundle_tasks
from b4_b8_r121_private_bundle_shot_sweep import basis_circuit, stable_hash, write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r127_calibration_aware_layout_design import (
    SNAPSHOT_CLASSES,
    logical_two_qubit_edges,
    static_layout_objective,
)
from b4_b8_r128_transpiler_loop_layout_ranking import (
    OPTIMIZATION_LEVEL,
    aggregate,
    package_version,
)
from b4_b8_r129_seed_robust_layout_ranking import compile_rows, paired_summary


METHOD = "b4_b8_r130_route_signature_candidate_expansion_v0"
STATUS = "route_signature_candidate_expansion_boundary"
MODEL_STATUS = "static_top10_expanded_with_route_signature_champions"
TARGET_ID = "T-B4-002ae/T-B8-003ai/T-B10-009w"
UPSTREAM_TARGET_ID = "T-B4-002ad/T-B8-003ah/T-B10-009v"
R125_RESULT_PATH = "results/B4_B8_R125_historical_snapshot_replay_v0.json"
R129_RESULT_PATH = "results/B4_B8_R129_seed_robust_layout_ranking_v0.json"
RESULT_PATH = "results/B4_B8_R130_route_signature_candidate_expansion_v0.json"
REPORT_PATH = "research/B4_B8_R130_route_signature_candidate_expansion.md"
OUT_DIR = "results/B4_B8_R130_route_signature_candidate_expansion"
TRAIN_SEEDS = tuple(range(13001, 13009))
VALIDATION_SEEDS = tuple(range(13051, 13061))
STATIC_TOP_K = 10
RETAINED_PER_GROUP = 52
EXPECTED_GROUPS = 6


def route_signature(
    row: dict[str, Any], mapping: tuple[int, ...], physical_qubits: int
) -> tuple[Any, ...]:
    edge_counts: Counter[tuple[int, int]] = Counter()
    for step in row["routed_steps"]:
        edge_counts[tuple(step["physical_edge"])] += step["multiplicity_proxy"]
    excluded = tuple(sorted(set(range(physical_qubits)) - set(mapping)))
    return (
        row["routed_step_count_proxy"],
        excluded,
        tuple(sorted((source, target, count) for (source, target), count in edge_counts.items())),
    )


def signature_id(signature: tuple[Any, ...]) -> str:
    return stable_hash(signature)[:16]


def expanded_candidates(
    backend: Any, logical_edges: list[tuple[int, int]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ranked = []
    for mapping in itertools.permutations(
        range(backend.num_qubits), len({q for edge in logical_edges for q in edge})
    ):
        row = static_layout_objective(backend, mapping, logical_edges)
        signature = route_signature(row, mapping, backend.num_qubits)
        ranked.append(
            {
                **row,
                "mapping": list(mapping),
                "route_signature_id": signature_id(signature),
                "route_signature": {
                    "routed_step_count_proxy": signature[0],
                    "excluded_physical_qubits": list(signature[1]),
                    "directed_edge_multiplicity": [list(item) for item in signature[2]],
                },
            }
        )
    ranked.sort(
        key=lambda row: (row["static_combined_any_error_proxy"], row["mapping"])
    )
    for rank, row in enumerate(ranked, start=1):
        row["static_rank"] = rank

    champions = {}
    for row in ranked:
        champions.setdefault(row["route_signature_id"], row)
    champion_rows = sorted(
        champions.values(),
        key=lambda row: (
            row["routed_step_count_proxy"],
            row["static_combined_any_error_proxy"],
            row["mapping"],
        ),
    )
    selected = []
    selected_mappings = set()

    def add(row: dict[str, Any], source: str) -> None:
        key = tuple(row["mapping"])
        if key in selected_mappings or len(selected) >= RETAINED_PER_GROUP:
            return
        selected_mappings.add(key)
        selected.append({**row, "retention_source": source})

    for row in ranked[:STATIC_TOP_K]:
        add(row, "static_top10")
    for row in champion_rows:
        add(row, "route_signature_champion")
    for row in ranked:
        add(row, "static_fill_after_signature_coverage")

    if len(selected) != RETAINED_PER_GROUP:
        raise ValueError("route-signature expansion did not retain 52 candidates")
    retained_signatures = {row["route_signature_id"] for row in selected}
    summary = {
        "enumerated_mapping_count": len(ranked),
        "available_route_signature_count": len(champions),
        "retained_candidate_count": len(selected),
        "retained_unique_route_signature_count": len(retained_signatures),
        "static_top10_retained_count": sum(
            row["retention_source"] == "static_top10" for row in selected
        ),
        "route_signature_champion_retained_count": sum(
            row["retention_source"] == "route_signature_champion" for row in selected
        ),
        "static_fill_retained_count": sum(
            row["retention_source"] == "static_fill_after_signature_coverage"
            for row in selected
        ),
        "all_available_signatures_covered": len(retained_signatures) == len(champions),
    }
    return selected, summary


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = []
    for row in payload["selected_layout_rows"]:
        validation = row["validation_paired_summary"]
        reference = row["r129_reference_validation_paired_summary"]
        lines.append(
            "- `{snapshot}` / `{task}`: selected static rank `{rank}` from "
            "`{source}`, signature `{signature}`; unseen lower-20%/mean/wins "
            "`{q:.4f}` / `{mean:.4f}` / `{wins}/10`; R129 unseen mean/wins "
            "`{ref_mean:.4f}` / `{ref_wins}/10`; selector changed `{changed}`.".format(
                snapshot=row["snapshot"],
                task=row["task_id"],
                rank=row["selected_static_rank"],
                source=row["selected_retention_source"],
                signature=row["selected_route_signature_id"],
                q=validation["lower_quantile_exposure_delta_vs_default"],
                mean=validation["mean_exposure_delta_vs_default"],
                wins=validation["seed_win_count_vs_default"],
                ref_mean=reference["mean_exposure_delta_vs_default"],
                ref_wins=reference["seed_win_count_vs_default"],
                changed=row["selector_changed_from_r129"],
            )
        )
    requirements = "\n".join(
        f"- `{row['requirement_id']}` {'PASS' if row['passed'] else 'FAIL'}: {row['label']}"
        for row in payload["requirements"]
    )
    return f"""# B4/B8 R130 Route-Signature Candidate Expansion

## Result

- Enumerated mappings: `{summary['enumerated_mapping_count']}`
- Available route signatures: `{summary['available_route_signature_count']}`
- Retained candidates: `{summary['retained_candidate_count']}`
- Retained unique signatures: `{summary['retained_unique_route_signature_count']}`
- Candidate training compilations: `{summary['candidate_training_compilation_count']}`
- Total same-condition compilations: `{summary['total_compilation_count']}`
- Selectors changed from R129: `{summary['selector_changed_from_r129_count']}` / `6`
- Groups with positive unseen lower-20% delta: `{summary['positive_validation_lower_quantile_count']}` / `6`
- Groups winning at least 8/10 unseen seeds: `{summary['eight_of_ten_validation_win_count']}` / `6`
- Route-expansion unseen-seed gate passed: `{summary['route_expansion_gate_passed']}`
- Acceptance holdout executed: `False`
- New credit delta: `0`

## Per-Group Evidence

{chr(10).join(lines)}

R130 enumerates every injective six-to-seven mapping. It retains the static
Top-10, then the best mapping from each route signature ordered by proxy route
length and static exposure, then uses static fill only when fewer than 50 rows
remain. A signature binds routed directed-edge multiplicities, proxy route
steps, and the excluded physical qubit. The 52 retained rows per group are
trained on eight new seeds; ten disjoint seeds are opened only after selection.

## Gate

Every group must have positive unseen mean and lower-20% exposure deltas and
win at least eight of ten unseen seeds. This remains compiler-design validation,
not the verifier acceptance holdout or evidence of protocol soundness.

## Requirements

{requirements}

## Claim Boundary

Supported: deterministic route-signature expansion and disjoint-seed validation
over frozen historical snapshots. Not supported: verifier holdout performance,
readout mitigation, current calibration, provider access, hardware execution,
protocol soundness, quantum advantage, BQP separation, or new B10 credit.
"""


def run_gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    r125_path = root / R125_RESULT_PATH
    r129_path = root / R129_RESULT_PATH
    r125 = json.loads(r125_path.read_text(encoding="utf-8"))
    r129 = json.loads(r129_path.read_text(encoding="utf-8"))
    if r129.get("status") != "unseen_transpiler_seed_robustness_boundary":
        raise ValueError("R130 requires the R129 unseen-seed boundary")
    if set(TRAIN_SEEDS) & set(VALIDATION_SEEDS):
        raise ValueError("R130 training and validation seeds must be disjoint")

    output = root / OUT_DIR
    circuits_dir = output / "validation_circuits"
    circuits_dir.mkdir(parents=True, exist_ok=True)
    for old in circuits_dir.glob("*.qasm"):
        old.unlink()

    tasks = {task["task_id"]: task for task in build_bundle_tasks()}
    r129_selected = {
        (row["snapshot"], row["task_id"]): row for row in r129["selected_layout_rows"]
    }
    candidate_training_rows = []
    group_expansion_rows = []
    selected_rows = []
    circuit_files = []
    candidate_training_compilations = 0
    training_default_compilations = 0
    validation_selected_compilations = 0
    validation_default_compilations = 0
    validation_reference_compilations = 0
    with tempfile.TemporaryDirectory(prefix="r130-") as temporary:
        scratch = Path(temporary) / "compiled.qasm"
        for snapshot_name in sorted(SNAPSHOT_CLASSES):
            backend = SNAPSHOT_CLASSES[snapshot_name]()
            metadata = r125["snapshot_metadata"][snapshot_name]
            for task_id in sorted(tasks):
                task = tasks[task_id]
                logical_edges = logical_two_qubit_edges(task)
                retained, expansion = expanded_candidates(backend, logical_edges)
                expansion_row = {
                    "snapshot": snapshot_name,
                    "task_id": task_id,
                    **expansion,
                }
                group_expansion_rows.append(expansion_row)
                representative = basis_circuit(
                    task["circuit"],
                    tuple("Z" for _ in range(task["circuit"].num_qubits)),
                )
                training_default_rows, _ = compile_rows(
                    representative, backend, metadata, TRAIN_SEEDS, scratch, None
                )
                training_default_compilations += len(training_default_rows)
                group_rows = []
                for candidate in retained:
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
                        "mapping": candidate["mapping"],
                        "static_rank": candidate["static_rank"],
                        "retention_source": candidate["retention_source"],
                        "route_signature_id": candidate["route_signature_id"],
                        "route_signature": candidate["route_signature"],
                        "candidate_aggregate": aggregate(candidate_rows),
                        "default_aggregate": aggregate(training_default_rows),
                        "paired_summary": paired,
                    }
                    group_rows.append(row)
                    candidate_training_rows.append(row)
                selected = min(
                    group_rows,
                    key=lambda row: (
                        -row["paired_summary"][
                            "lower_quantile_exposure_delta_vs_default"
                        ],
                        -row["paired_summary"]["seed_win_count_vs_default"],
                        -row["paired_summary"]["mean_exposure_delta_vs_default"],
                        row["candidate_aggregate"][
                            "maximum_combined_any_error_proxy"
                        ],
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
                reference_mapping = r129_selected[(snapshot_name, task_id)][
                    "selected_mapping"
                ]
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
                        "selected_retention_source": selected["retention_source"],
                        "selected_route_signature_id": selected["route_signature_id"],
                        "selected_route_signature": selected["route_signature"],
                        "r129_reference_mapping": reference_mapping,
                        "selector_changed_from_r129": selected["mapping"]
                        != reference_mapping,
                        "training_paired_summary": selected["paired_summary"],
                        "validation_candidate_aggregate": aggregate(
                            validation_selected_rows
                        ),
                        "validation_default_aggregate": aggregate(
                            validation_default_rows
                        ),
                        "validation_paired_summary": validation_paired,
                        "r129_reference_validation_aggregate": aggregate(
                            validation_reference_rows
                        ),
                        "r129_reference_validation_paired_summary": reference_paired,
                        "validation_mean_improvement_over_r129_selector": (
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
    route_expansion_gate = all(
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
        "enumerated_mapping_count": sum(
            row["enumerated_mapping_count"] for row in group_expansion_rows
        ),
        "available_route_signature_count": sum(
            row["available_route_signature_count"] for row in group_expansion_rows
        ),
        "retained_candidate_count": sum(
            row["retained_candidate_count"] for row in group_expansion_rows
        ),
        "retained_unique_route_signature_count": sum(
            row["retained_unique_route_signature_count"]
            for row in group_expansion_rows
        ),
        "candidate_training_compilation_count": candidate_training_compilations,
        "training_default_compilation_count": training_default_compilations,
        "validation_selected_compilation_count": validation_selected_compilations,
        "validation_default_compilation_count": validation_default_compilations,
        "validation_reference_compilation_count": validation_reference_compilations,
        "total_compilation_count": total_compilations,
        "selector_changed_from_r129_count": sum(
            row["selector_changed_from_r129"] for row in selected_rows
        ),
        "selected_from_expansion_count": sum(
            row["selected_static_rank"] > STATIC_TOP_K for row in selected_rows
        ),
        "positive_validation_mean_count": positive_mean_count,
        "positive_validation_lower_quantile_count": positive_quantile_count,
        "eight_of_ten_validation_win_count": eight_of_ten_count,
        "validation_improvement_over_r129_selector_count": sum(
            row["validation_mean_improvement_over_r129_selector"] > 1e-15
            for row in selected_rows
        ),
        "route_expansion_gate_passed": route_expansion_gate,
        "training_seed_count": len(TRAIN_SEEDS),
        "validation_seed_count": len(VALIDATION_SEEDS),
        "training_seeds": list(TRAIN_SEEDS),
        "validation_seeds": list(VALIDATION_SEEDS),
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
            "label": "R129 source is hash-bound before candidate expansion",
            "passed": len(r129.get("selected_layout_rows", [])) == 6,
            "evidence": {"r129_sha256": file_sha256(r129_path)},
        },
        {
            "requirement_id": "P2",
            "label": "all 30,240 injective mappings are enumerated",
            "passed": summary["enumerated_mapping_count"] == 30240,
            "evidence": {"enumerated_mapping_count": summary["enumerated_mapping_count"]},
        },
        {
            "requirement_id": "P3",
            "label": "52 candidates are retained per snapshot/task group",
            "passed": summary["retained_candidate_count"] == 312,
            "evidence": {"retained_candidate_count": summary["retained_candidate_count"]},
        },
        {
            "requirement_id": "P4",
            "label": "route signatures bind route steps, excluded qubit, and edge multiplicity",
            "passed": all(
                row["retained_unique_route_signature_count"] >= 42
                for row in group_expansion_rows
            ),
            "evidence": {
                "minimum_retained_unique_signatures": min(
                    row["retained_unique_route_signature_count"]
                    for row in group_expansion_rows
                )
            },
        },
        {
            "requirement_id": "P5",
            "label": "all expanded candidates are compiled on eight training seeds",
            "passed": candidate_training_compilations == 312 * 8,
            "evidence": {
                "candidate_training_compilation_count": candidate_training_compilations
            },
        },
        {
            "requirement_id": "P6",
            "label": "ten disjoint validation seeds cover selected, default, and R129 layouts",
            "passed": not (set(TRAIN_SEEDS) & set(VALIDATION_SEEDS))
            and validation_selected_compilations == 60
            and validation_default_compilations == 60
            and validation_reference_compilations == 60,
            "evidence": {"validation_compilation_count": 180},
        },
        {
            "requirement_id": "P7",
            "label": "all 60 validation QASM artifacts preserve measurement order",
            "passed": len(circuit_files) == 60
            and all(
                row["all_validation_measurement_maps_preserve_logical_order"]
                for row in selected_rows
            ),
            "evidence": {"validation_circuit_count": len(circuit_files)},
        },
        {
            "requirement_id": "P8",
            "label": "route-expansion gate is evaluated on all six groups",
            "passed": len(selected_rows) == EXPECTED_GROUPS
            and all(
                math.isfinite(
                    row["validation_paired_summary"][
                        "lower_quantile_exposure_delta_vs_default"
                    ]
                )
                for row in selected_rows
            ),
            "evidence": {"route_expansion_gate_passed": route_expansion_gate},
        },
        {
            "requirement_id": "P9",
            "label": "verifier holdout, current calibration, and hardware remain excluded",
            "passed": not summary["acceptance_holdout_executed"]
            and not summary["r125_acceptance_rows_read"]
            and not summary["readout_mitigation_tested"]
            and not summary["current_backend_calibration_used"]
            and not summary["hardware_execution_performed"],
            "evidence": {"compiler_design_validation_only": True},
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
        "title": "B4/B8 R130 route-signature candidate expansion",
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
        "group_expansion_rows": group_expansion_rows,
        "selected_layout_rows": selected_rows,
        "candidate_training_rows": candidate_training_rows,
        "environment": {
            "qiskit": package_version("qiskit"),
            "qiskit_ibm_runtime": package_version("qiskit-ibm-runtime"),
            "numpy": package_version("numpy"),
        },
        "artifacts": {
            "r129_result": R129_RESULT_PATH,
            "validation_circuits": sorted(circuit_files),
        },
        "claim_boundary": {
            "what_is_supported": (
                "Route-signature-diverse candidate expansion and disjoint-seed compiler "
                "validation over frozen historical snapshots."
            ),
            "what_is_not_supported": (
                "Verifier holdout performance, readout mitigation, current calibration, "
                "provider access, hardware execution, protocol soundness, quantum advantage, "
                "BQP separation, or new B10 credit."
            ),
            "next_gate": (
                "If route-signature expansion remains non-robust, isolate exact compiled "
                "route families and formulate topology-specific candidate constraints."
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
