#!/usr/bin/env python3
"""T-B4-002af/T-B8-003aj: attribute R130 outcomes to exact route families."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from qiskit import qasm3, transpile

from b4_b8_r119_private_observable_bundle_gate import build_bundle_tasks
from b4_b8_r121_private_bundle_shot_sweep import basis_circuit, stable_hash, write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r127_calibration_aware_layout_design import SNAPSHOT_CLASSES
from b4_b8_r128_transpiler_loop_layout_ranking import (
    OPTIMIZATION_LEVEL,
    exposure_from_qasm,
    package_version,
)


METHOD = "b4_b8_r131_compiled_route_family_attribution_v0"
STATUS = "compiled_route_family_attribution_boundary"
MODEL_STATUS = "r130_seed_outcomes_attributed_to_exact_cx_route_families"
TARGET_ID = "T-B4-002af/T-B8-003aj/T-B10-009x"
UPSTREAM_TARGET_ID = "T-B4-002ae/T-B8-003ai/T-B10-009w"
R125_RESULT_PATH = "results/B4_B8_R125_historical_snapshot_replay_v0.json"
R130_RESULT_PATH = "results/B4_B8_R130_route_signature_candidate_expansion_v0.json"
RESULT_PATH = "results/B4_B8_R131_compiled_route_family_attribution_v0.json"
REPORT_PATH = "research/B4_B8_R131_compiled_route_family_attribution.md"
OUT_DIR = "results/B4_B8_R131_compiled_route_family_attribution"
EXPECTED_SEEDS = tuple(range(13051, 13061))
DETERMINISTIC_PROCESS_ENV = {
    "PYTHONHASHSEED": "0",
    "RAYON_NUM_THREADS": "1",
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "QISKIT_PARALLEL": "FALSE",
}


def ensure_deterministic_process_hash_seed() -> None:
    if all(os.environ.get(key) == value for key, value in DETERMINISTIC_PROCESS_ENV.items()):
        return
    environment = dict(os.environ)
    environment.update(DETERMINISTIC_PROCESS_ENV)
    os.execvpe(sys.executable, [sys.executable, *sys.argv], environment)


def compiled_route_descriptor(
    circuit: Any, exposure: dict[str, Any]
) -> dict[str, Any]:
    cx_sequence = []
    for instruction in circuit.data:
        name = instruction.operation.name
        if name == "cx":
            cx_sequence.append(
                [circuit.find_bit(qubit).index for qubit in instruction.qubits]
            )
    edge_counts = Counter(tuple(edge) for edge in cx_sequence)
    family_payload = {
        "directed_edge_multiplicity": [
            [source, target, count]
            for (source, target), count in sorted(edge_counts.items())
        ],
        "cx_occurrence_count": len(cx_sequence),
        "combined_any_error_proxy": exposure["combined_any_error_proxy"],
    }
    return {
        "route_family_id": stable_hash(family_payload)[:20],
        "cx_occurrence_count": len(cx_sequence),
        "directed_edge_multiplicity": [
            [source, target, count]
            for (source, target), count in sorted(edge_counts.items())
        ],
        "combined_any_error_proxy": exposure["combined_any_error_proxy"],
        "family_semantics": "cx_edge_multiset_and_exposure_equivalence_class",
    }


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = []
    for row in payload["group_attribution_rows"]:
        lines.append(
            "- `{snapshot}` / `{task}`: selected/default route-exposure classes "
            "`{selected}/{default}`; family pairs `{pairs}`; selected invariant "
            "`{selected_invariant}`; default switches `{default_switches}`; "
            "wins/ties/losses `{wins}/{ties}/{losses}`; outcome-varying default "
            "families `{varying}`; baseline-switch attribution `{attributed}`.".format(
                snapshot=row["snapshot"],
                task=row["task_id"],
                selected=row["selected_unique_route_family_count"],
                default=row["default_unique_route_family_count"],
                pairs=row["route_family_pair_count"],
                selected_invariant=row["selected_route_family_seed_invariant"],
                default_switches=row["default_route_family_switches_across_seeds"],
                wins=row["selected_win_count"],
                ties=row["selected_tie_count"],
                losses=row["selected_loss_count"],
                varying=row["default_families_with_mixed_outcomes"],
                attributed=row["outcome_instability_attributed_to_default_family_switching"],
            )
        )
    requirements = "\n".join(
        f"- `{row['requirement_id']}` {'PASS' if row['passed'] else 'FAIL'}: {row['label']}"
        for row in payload["requirements"]
    )
    return f"""# B4/B8 R131 Compiled Route-Family Attribution

## Result

- Diagnostic recompilations: `{summary['diagnostic_compilation_count']}`
- Python hash seed: `{summary['python_hash_seed']}`
- Selected QASM replay matches: `{summary['selected_qasm_replay_match_count']}` / `60`
- Selected route-exposure families: `{summary['selected_unique_route_family_count']}`
- Automatic-layout route-exposure families: `{summary['default_unique_route_family_count']}`
- Groups with selected family invariant: `{summary['selected_family_invariant_group_count']}` / `6`
- Groups with automatic family switching: `{summary['default_family_switching_group_count']}` / `6`
- Groups whose outcome instability is attributed to automatic-family switching: `{summary['default_switch_attribution_group_count']}` / `6`
- Diagnostic rows matching R130 deltas: `{summary['r130_delta_replay_match_count']}` / `60`
- Acceptance or selection performed: `False`
- New credit delta: `0`

## Per-Group Evidence

{chr(10).join(lines)}

A route-exposure family binds the directed physical CX-edge multiset, CX count,
and compiled combined exposure. Cross-process QA found that exact ordered CX
sequences and measurement maps can drift even with the same transpiler seed;
R131 therefore does not claim exact ordered-route reproducibility. It recompiles
the selected and automatic layouts on the already-used R130 validation seeds,
without opening a new seed block, tuning a selector, or running the verifier holdout.

## Requirements

{requirements}

## Claim Boundary

Supported: post-hoc attribution of R130 compiler-seed outcomes to reproducible
route-exposure equivalence classes with byte-level selected-QASM replay. Not supported: causal
hardware claims, new selector acceptance, verifier holdout performance, readout
mitigation, current calibration, provider access, hardware execution, protocol
soundness, quantum advantage, BQP separation, or new B10 credit.
"""


def run_gate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    r125_path = root / R125_RESULT_PATH
    r130_path = root / R130_RESULT_PATH
    r125 = json.loads(r125_path.read_text(encoding="utf-8"))
    r130 = json.loads(r130_path.read_text(encoding="utf-8"))
    if r130.get("status") != "route_signature_candidate_expansion_boundary":
        raise ValueError("R131 requires the R130 route-signature boundary")
    if tuple(r130["summary"].get("validation_seeds", [])) != EXPECTED_SEEDS:
        raise ValueError("R131 requires the exact R130 validation seed block")

    output = root / OUT_DIR
    default_dir = output / "default_circuits"
    default_dir.mkdir(parents=True, exist_ok=True)

    tasks = {task["task_id"]: task for task in build_bundle_tasks()}
    selected_by_group = {
        (row["snapshot"], row["task_id"]): row
        for row in r130["selected_layout_rows"]
    }
    seed_rows = []
    default_files = []
    selected_qasm_match_count = 0
    delta_match_count = 0
    with tempfile.TemporaryDirectory(prefix="r131-") as temporary:
        scratch = Path(temporary) / "compiled.qasm"
        for snapshot_name, task_id in sorted(selected_by_group):
            backend = SNAPSHOT_CLASSES[snapshot_name]()
            metadata = r125["snapshot_metadata"][snapshot_name]
            source = selected_by_group[(snapshot_name, task_id)]
            task = tasks[task_id]
            representative = basis_circuit(
                task["circuit"],
                tuple("Z" for _ in range(task["circuit"].num_qubits)),
            )
            stored_delta_by_seed = {
                row["seed"]: row["exposure_delta_vs_default"]
                for row in source["validation_paired_summary"]["paired_delta_rows"]
            }
            stored_path_by_seed = {
                int(Path(path).stem.rsplit("_", 1)[1]): root / path
                for path in source["validation_circuit_paths"]
            }
            for seed in EXPECTED_SEEDS:
                selected_compiled = transpile(
                    representative,
                    backend=backend,
                    initial_layout=source["selected_mapping"],
                    optimization_level=OPTIMIZATION_LEVEL,
                    seed_transpiler=seed,
                )
                default_compiled = transpile(
                    representative,
                    backend=backend,
                    optimization_level=OPTIMIZATION_LEVEL,
                    seed_transpiler=seed,
                )
                selected_qasm = qasm3.dumps(selected_compiled)
                default_qasm = qasm3.dumps(default_compiled)
                stored_path = stored_path_by_seed[seed]
                selected_match = stable_hash(selected_qasm) == stable_hash(
                    stored_path.read_text(encoding="utf-8")
                )
                selected_qasm_match_count += selected_match
                default_path = (
                    default_dir / f"{snapshot_name}_{task_id}_seed_{seed}.qasm"
                )
                if not default_path.exists():
                    default_path.write_text(default_qasm, encoding="utf-8")
                default_relative = str(default_path.relative_to(root))
                default_files.append(default_relative)
                selected_exposure = exposure_from_qasm(
                    selected_qasm, metadata, scratch
                )
                default_exposure = exposure_from_qasm(default_qasm, metadata, scratch)
                delta = (
                    default_exposure["combined_any_error_proxy"]
                    - selected_exposure["combined_any_error_proxy"]
                )
                delta_match = abs(delta - stored_delta_by_seed[seed]) <= 1e-15
                delta_match_count += delta_match
                selected_family = compiled_route_descriptor(
                    selected_compiled, selected_exposure
                )
                default_family = compiled_route_descriptor(
                    default_compiled, default_exposure
                )
                outcome = "win" if delta > 1e-15 else "loss" if delta < -1e-15 else "tie"
                seed_rows.append(
                    {
                        "snapshot": snapshot_name,
                        "task_id": task_id,
                        "seed": seed,
                        "selected_mapping": source["selected_mapping"],
                        "selected_circuit_path": str(stored_path.relative_to(root)),
                        "selected_circuit_sha256": file_sha256(stored_path),
                        "selected_qasm_replay_matches": selected_match,
                        "default_circuit_path": default_relative,
                        "default_circuit_sha256": file_sha256(default_path),
                        "selected_route_family": selected_family,
                        "default_route_family": default_family,
                        "same_exact_route_family": selected_family["route_family_id"]
                        == default_family["route_family_id"],
                        "selected_combined_any_error_proxy": selected_exposure[
                            "combined_any_error_proxy"
                        ],
                        "default_combined_any_error_proxy": default_exposure[
                            "combined_any_error_proxy"
                        ],
                        "exposure_delta_vs_default": delta,
                        "r130_exposure_delta": stored_delta_by_seed[seed],
                        "r130_delta_replay_matches": delta_match,
                        "outcome": outcome,
                    }
                )

    group_rows = []
    for key in sorted(selected_by_group):
        rows = [row for row in seed_rows if (row["snapshot"], row["task_id"]) == key]
        selected_families = {
            row["selected_route_family"]["route_family_id"] for row in rows
        }
        default_families = {
            row["default_route_family"]["route_family_id"] for row in rows
        }
        family_pairs = {
            (
                row["selected_route_family"]["route_family_id"],
                row["default_route_family"]["route_family_id"],
            )
            for row in rows
        }
        outcomes_by_default: dict[str, set[str]] = defaultdict(set)
        seeds_by_default: dict[str, list[int]] = defaultdict(list)
        for row in rows:
            family = row["default_route_family"]["route_family_id"]
            outcomes_by_default[family].add(row["outcome"])
            seeds_by_default[family].append(row["seed"])
        outcomes = {row["outcome"] for row in rows}
        selected_invariant = len(selected_families) == 1
        default_switches = len(default_families) > 1
        attribution = selected_invariant and default_switches and len(outcomes) > 1
        group_rows.append(
            {
                "snapshot": key[0],
                "task_id": key[1],
                "selected_unique_route_family_count": len(selected_families),
                "default_unique_route_family_count": len(default_families),
                "route_family_pair_count": len(family_pairs),
                "selected_route_family_ids": sorted(selected_families),
                "default_route_family_ids": sorted(default_families),
                "selected_route_family_seed_invariant": selected_invariant,
                "default_route_family_switches_across_seeds": default_switches,
                "selected_win_count": sum(row["outcome"] == "win" for row in rows),
                "selected_tie_count": sum(row["outcome"] == "tie" for row in rows),
                "selected_loss_count": sum(row["outcome"] == "loss" for row in rows),
                "default_families_with_mixed_outcomes": sum(
                    len(values) > 1 for values in outcomes_by_default.values()
                ),
                "outcome_instability_attributed_to_default_family_switching": attribution,
                "default_family_outcome_ledger": [
                    {
                        "route_family_id": family,
                        "seeds": seeds_by_default[family],
                        "outcomes": sorted(outcomes_by_default[family]),
                    }
                    for family in sorted(default_families)
                ],
            }
        )

    summary = {
        "snapshot_count": len(SNAPSHOT_CLASSES),
        "task_count": len(tasks),
        "seed_count_per_group": len(EXPECTED_SEEDS),
        "diagnostic_compilation_count": len(seed_rows) * 2,
        "python_hash_seed": int(os.environ["PYTHONHASHSEED"]),
        "deterministic_process_hash_seed_enforced": True,
        "deterministic_process_environment_enforced": True,
        "native_thread_count": 1,
        "seed_row_count": len(seed_rows),
        "selected_qasm_replay_match_count": selected_qasm_match_count,
        "r130_delta_replay_match_count": delta_match_count,
        "selected_unique_route_family_count": sum(
            row["selected_unique_route_family_count"] for row in group_rows
        ),
        "default_unique_route_family_count": sum(
            row["default_unique_route_family_count"] for row in group_rows
        ),
        "route_family_pair_count": sum(
            row["route_family_pair_count"] for row in group_rows
        ),
        "selected_family_invariant_group_count": sum(
            row["selected_route_family_seed_invariant"] for row in group_rows
        ),
        "default_family_switching_group_count": sum(
            row["default_route_family_switches_across_seeds"] for row in group_rows
        ),
        "default_switch_attribution_group_count": sum(
            row["outcome_instability_attributed_to_default_family_switching"]
            for row in group_rows
        ),
        "selected_win_count": sum(row["outcome"] == "win" for row in seed_rows),
        "selected_tie_count": sum(row["outcome"] == "tie" for row in seed_rows),
        "selected_loss_count": sum(row["outcome"] == "loss" for row in seed_rows),
        "route_family_semantics": "cx_edge_multiset_and_exposure_equivalence_class",
        "exact_ordered_route_reproducibility_claimed": False,
        "default_qasm_artifacts_are_frozen_observations": True,
        "r130_validation_seeds_reused_for_diagnostic": True,
        "new_seed_block_opened": False,
        "selection_or_acceptance_performed": False,
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
            "label": "R130 source is hash-bound and its exact seed block is reused",
            "passed": tuple(r130["summary"]["validation_seeds"]) == EXPECTED_SEEDS,
            "evidence": {"r130_sha256": file_sha256(r130_path)},
        },
        {
            "requirement_id": "P2",
            "label": "process hash seed is fixed and both layouts are recompiled for all rows",
            "passed": summary["python_hash_seed"] == 0
            and summary["deterministic_process_hash_seed_enforced"]
            and summary["deterministic_process_environment_enforced"]
            and summary["native_thread_count"] == 1
            and summary["diagnostic_compilation_count"] == 120,
            "evidence": {
                "python_hash_seed": summary["python_hash_seed"],
                "diagnostic_compilation_count": 120,
            },
        },
        {
            "requirement_id": "P3",
            "label": "all selected recompilations byte-match stored R130 QASM",
            "passed": selected_qasm_match_count == 60,
            "evidence": {"selected_qasm_replay_match_count": selected_qasm_match_count},
        },
        {
            "requirement_id": "P4",
            "label": "all exposure deltas match the R130 ledger",
            "passed": delta_match_count == 60,
            "evidence": {"r130_delta_replay_match_count": delta_match_count},
        },
        {
            "requirement_id": "P5",
            "label": "route-exposure families bind CX edge multisets and compiled exposure",
            "passed": all(
                row["selected_route_family"]["directed_edge_multiplicity"]
                and row["selected_route_family"]["family_semantics"]
                == "cx_edge_multiset_and_exposure_equivalence_class"
                for row in seed_rows
            ),
            "evidence": {"seed_row_count": len(seed_rows)},
        },
        {
            "requirement_id": "P6",
            "label": "every group has a complete ten-seed route-family ledger",
            "passed": len(group_rows) == 6
            and all(
                row["selected_win_count"]
                + row["selected_tie_count"]
                + row["selected_loss_count"]
                == 10
                for row in group_rows
            ),
            "evidence": {"group_count": len(group_rows)},
        },
        {
            "requirement_id": "P7",
            "label": "all 60 automatic-layout QASM observations are frozen",
            "passed": len(default_files) == 60,
            "evidence": {"default_circuit_count": len(default_files)},
        },
        {
            "requirement_id": "P8",
            "label": "diagnostic reuse opens no new seed block and performs no selection",
            "passed": summary["r130_validation_seeds_reused_for_diagnostic"]
            and not summary["new_seed_block_opened"]
            and not summary["selection_or_acceptance_performed"],
            "evidence": {"diagnostic_only": True},
        },
        {
            "requirement_id": "P9",
            "label": "verifier holdout, mitigation, current calibration, and hardware remain excluded",
            "passed": not summary["acceptance_holdout_executed"]
            and not summary["r125_acceptance_rows_read"]
            and not summary["readout_mitigation_tested"]
            and not summary["current_backend_calibration_used"]
            and not summary["hardware_execution_performed"],
            "evidence": {"compiler_diagnostic_only": True},
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
        "title": "B4/B8 R131 compiled route-exposure family attribution",
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
        "group_attribution_rows": group_rows,
        "seed_attribution_rows": seed_rows,
        "environment": {
            "python_hash_seed": int(os.environ["PYTHONHASHSEED"]),
            "deterministic_process_environment": DETERMINISTIC_PROCESS_ENV,
            "qiskit": package_version("qiskit"),
            "qiskit_ibm_runtime": package_version("qiskit-ibm-runtime"),
        },
        "artifacts": {
            "r130_result": R130_RESULT_PATH,
            "r130_selected_circuits": sorted(
                path
                for row in selected_by_group.values()
                for path in row["validation_circuit_paths"]
            ),
            "default_circuits": sorted(default_files),
        },
        "claim_boundary": {
            "what_is_supported": (
                "Post-hoc compiled route-exposure family attribution with selected-QASM "
                "and exposure-delta replay against R130."
            ),
            "what_is_not_supported": (
                "Causal hardware claims, new selector acceptance, verifier holdout performance, "
                "readout mitigation, current calibration, provider access, hardware execution, "
                "protocol soundness, quantum advantage, BQP separation, or new B10 credit."
            ),
            "next_gate": (
                "Use the route-exposure family ledger to formulate topology-specific constraints "
                "without reusing R130 diagnostic seeds for acceptance."
            ),
        },
    }
    payload["payload_hash"] = stable_hash(payload)
    write_json(root / RESULT_PATH, payload)
    (root / REPORT_PATH).write_text(report(payload), encoding="utf-8")
    return payload


def main() -> None:
    ensure_deterministic_process_hash_seed()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    payload = run_gate(args.root)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
