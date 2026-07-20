#!/usr/bin/env python3
"""Run the preregistered R183 prefix-initialization micro-ablation."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r154_deterministic_automatic_replay import canonical_hash, target_descriptor
from b4_b8_r181_active_limb_replay import (
    actual_environment,
    imported_binary,
    mapping_vector,
    new_config,
)
from b4_b8_r182_score_cost_attribution_replay import (
    cell_definitions,
    prepare_small_gap,
    prepare_standard,
)


METHOD = "b4_b8_r183_prefix_initialization_ablation_replay_v0"
PROTOCOL_PATH = "results/B4_B8_R183_prefix_initialization_ablation_protocol_v0.json"
DESIGN_CONTRACT_PATH = (
    "benchmarks/B4_B8_R183_prefix_initialization_ablation_contract_v0.json"
)
CONTRACT_PATH = "benchmarks/B4_B8_R183_prefix_initialization_execution_contract_v0.json"
R181_PROTOCOL_PATH = "results/B4_B8_R181_active_limb_protocol_v0.json"
BINARY_PATH = (
    "research/source_lineage/Qiskit_2_4_1_R183_prefix_init_pyext.x86_64-linux-gnu.so"
)
BUILD_MANIFEST_PATH = "research/source_lineage/Qiskit_2_4_1_R183_prefix_init_linux_x86_64_build_manifest.json"
OUT_DIR = "results/B4_B8_R183_prefix_initialization_replay"
RESULT_PATH = "results/B4_B8_R183_prefix_initialization_ablation_v0.json"
REPORT_PATH = "research/B4_B8_R183_prefix_initialization_ablation.md"
ARMS = {
    "baseline": {
        "policy": "rust_active_limb_exact_full_width_initialized",
        "timing": "vf2_layout_pass_average_active_fixed_exact_score",
        "probe": "vf2_layout_pass_average_active_fixed_exact_score_r183_cost_traced",
    },
    "candidate": {
        "policy": "rust_active_limb_exact_prefix_initialized",
        "timing": "vf2_layout_pass_average_prefix_initialized_exact_score",
        "probe": "vf2_layout_pass_average_prefix_initialized_exact_score_r183_cost_traced",
    },
}
COUNTER_KEYS = [
    "leaf_construction_count",
    "destination_initialized_limb_count",
    "full_width_destination_count",
    "arithmetic_limb_visit_count",
    "comparison_limb_visit_count",
    "carry_extension_count",
    "maximum_used_limb_count",
]
NON_INITIALIZATION_COUNTER_KEYS = [
    "leaf_construction_count",
    "arithmetic_limb_visit_count",
    "comparison_limb_visit_count",
    "carry_extension_count",
    "maximum_used_limb_count",
]


def validate_hash_field(payload: dict[str, Any], field: str, label: str) -> str:
    body = dict(payload)
    observed = body.pop(field, None)
    if not observed or observed != canonical_hash(body):
        raise ValueError(f"R183 {label} hash mismatch")
    return str(observed)


def validate_contract(
    root: Path,
    protocol: dict[str, Any],
    design: dict[str, Any],
    contract: dict[str, Any],
    *,
    require_unopened: bool,
    require_build: bool,
) -> None:
    protocol_hash = validate_hash_field(protocol, "payload_hash", "protocol")
    design_hash = validate_hash_field(design, "payload_hash", "design contract")
    validate_hash_field(contract, "payload_hash", "execution contract")
    if (
        protocol.get("method")
        != "b4_b8_r183_prefix_initialization_ablation_protocol_v0"
    ):
        raise ValueError("R183 protocol identity mismatch")
    if (
        design.get("contract_id")
        != "B4-B8-R183-prefix-initialization-design-contract-v0"
    ):
        raise ValueError("R183 design contract identity mismatch")
    if (
        contract.get("contract_id")
        != "B4-B8-R183-prefix-initialization-execution-contract-v0"
    ):
        raise ValueError("R183 execution contract identity mismatch")
    if contract.get("execution_started") is not False:
        raise ValueError("R183 execution contract is not unopened")
    if contract.get("protocol_payload_hash") != protocol_hash:
        raise ValueError("R183 protocol binding mismatch")
    if contract.get("design_contract_payload_hash") != design_hash:
        raise ValueError("R183 design contract binding mismatch")
    for section in ("source_bindings", "tool_bindings"):
        for binding in contract[section].values():
            path = root / binding["path"]
            if not path.is_file() or file_sha256(path) != binding["sha256"]:
                raise ValueError(f"R183 binding mismatch: {binding['path']}")
    generator = contract["contract_generator_binding"]
    generator_path = root / generator["path"]
    if (
        not generator_path.is_file()
        or file_sha256(generator_path) != generator["sha256"]
    ):
        raise ValueError("R183 execution-contract generator binding mismatch")
    if require_unopened:
        for relative in contract["result_paths_must_be_absent"]:
            if (root / relative).exists():
                raise ValueError(f"R183 evidence existed before execution: {relative}")
    if require_build:
        for relative in contract["build_output_paths_created_before_replay"]:
            if not (root / relative).exists():
                raise ValueError(f"R183 required build output is missing: {relative}")


def runtime_preregistration(
    root: Path, args: argparse.Namespace, contract: dict[str, Any]
) -> dict[str, str]:
    public = contract["public_preregistration"]
    current_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    observed = {
        "commit": args.preregistration_commit,
        "discussion": args.preregistration_discussion,
        "created_at": args.preregistration_created_at,
    }
    if current_commit != observed["commit"]:
        raise ValueError("R183 runtime commit does not match HEAD")
    if (
        observed["discussion"] != public["discussion"]
        or observed["created_at"] != public["created_at"]
    ):
        raise ValueError("R183 runtime public preregistration mismatch")
    ancestor = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            public["public_design_commit"],
            current_commit,
        ],
        cwd=root,
        check=False,
    )
    if ancestor.returncode != 0:
        raise ValueError("R183 runtime commit predates the public design commit")
    return observed


def run_vf2(function: Any, dag: Any, target: Any, error_map: Any) -> list[int] | None:
    output = function(
        dag,
        target,
        new_config(),
        strict_direction=False,
        avg_error_map=error_map,
    )
    return mapping_vector(output.new_mapping(), target.num_qubits)


def run_probe(
    function: Any, dag: Any, target: Any, error_map: Any
) -> tuple[list[int] | None, dict[str, int]]:
    output, values = function(
        dag,
        target,
        new_config(),
        strict_direction=False,
        avg_error_map=error_map,
    )
    if len(values) != len(COUNTER_KEYS):
        raise ValueError(f"R183 probe returned {len(values)} counters")
    counters = {key: int(value) for key, value in zip(COUNTER_KEYS, values)}
    if any(value < 0 for value in counters.values()):
        raise ValueError("R183 probe returned a negative counter")
    return mapping_vector(output.new_mapping(), target.num_qubits), counters


def worker_path(cell_id: str) -> str:
    return f"{OUT_DIR}/{cell_id}.json"


def execute_worker(
    root: Path,
    protocol: dict[str, Any],
    design: dict[str, Any],
    contract: dict[str, Any],
    r181: dict[str, Any],
    cell_id: str,
    preregistration: dict[str, str],
) -> dict[str, Any]:
    from qiskit._accelerate import vf2_layout as vf2_module

    cells = {row["cell_id"]: row for row in cell_definitions(r181)}
    if cell_id not in cells:
        raise ValueError("R183 worker identity is outside the frozen matrix")
    path = root / worker_path(cell_id)
    if path.exists():
        raise ValueError(f"R183 worker already exists: {path}")
    binary = imported_binary()
    if file_sha256(binary) != file_sha256(root / BINARY_PATH):
        raise ValueError("R183 worker imported the wrong accelerator")
    cell = cells[cell_id]
    prepared = (
        prepare_standard(root, r181, cell)
        if cell["kind"] == "standard"
        else prepare_small_gap(root, r181, cell)
    )
    functions = {
        arm: {
            "timing": getattr(vf2_module, definition["timing"]),
            "probe": getattr(vf2_module, definition["probe"]),
        }
        for arm, definition in ARMS.items()
    }
    units = prepared["work_units"]
    counts = protocol["frozen_workload"]
    started_at = int(time.time())
    warmup_matches = {arm: 0 for arm in ARMS}
    for warmup_index in range(counts["warmups_per_arm_per_cell"]):
        unit = units[warmup_index % len(units)]
        order = (
            ["baseline", "candidate"]
            if warmup_index % 2 == 0
            else ["candidate", "baseline"]
        )
        for arm in order:
            vector = run_vf2(
                functions[arm]["timing"],
                prepared["dag"],
                prepared["target"],
                unit["error_map"],
            )
            warmup_matches[arm] += int(vector == unit["expected"])

    rows = []
    for pair_index in range(counts["measured_pairs_per_cell"]):
        unit = units[pair_index % len(units)]
        order = (
            ["baseline", "candidate"]
            if pair_index % 2 == 0
            else ["candidate", "baseline"]
        )
        arm_rows: dict[str, dict[str, Any]] = {}
        for arm in order:
            started = time.perf_counter_ns()
            timing_vector = run_vf2(
                functions[arm]["timing"],
                prepared["dag"],
                prepared["target"],
                unit["error_map"],
            )
            arm_rows[arm] = {
                "policy": ARMS[arm]["policy"],
                "timing_mapping_vector": timing_vector,
                "elapsed_nanoseconds": time.perf_counter_ns() - started,
            }
        for arm in order:
            probe_vector, counters = run_probe(
                functions[arm]["probe"],
                prepared["dag"],
                prepared["target"],
                unit["error_map"],
            )
            arm_rows[arm].update(
                {
                    "probe_mapping_vector": probe_vector,
                    "timing_matches_expected": arm_rows[arm]["timing_mapping_vector"]
                    == unit["expected"],
                    "probe_matches_expected": probe_vector == unit["expected"],
                    "timing_probe_mapping_match": arm_rows[arm]["timing_mapping_vector"]
                    == probe_vector,
                    "cost_counters": counters,
                }
            )
        row: dict[str, Any] = {
            "cell_id": cell_id,
            "subcell_id": unit["subcell_id"],
            "kind": cell["kind"],
            "pair_index": pair_index,
            "case_id": unit["case_id"],
            "execution_order": order,
            "expected_mapping_vector": unit["expected"],
            "arms": arm_rows,
            "cross_arm_timing_mapping_match": arm_rows["baseline"][
                "timing_mapping_vector"
            ]
            == arm_rows["candidate"]["timing_mapping_vector"],
            "cross_arm_probe_mapping_match": arm_rows["baseline"][
                "probe_mapping_vector"
            ]
            == arm_rows["candidate"]["probe_mapping_vector"],
            "non_initialization_counters_equal": all(
                arm_rows["baseline"]["cost_counters"][key]
                == arm_rows["candidate"]["cost_counters"][key]
                for key in NON_INITIALIZATION_COUNTER_KEYS
            ),
            "candidate_to_baseline_elapsed_ratio": arm_rows["candidate"][
                "elapsed_nanoseconds"
            ]
            / arm_rows["baseline"]["elapsed_nanoseconds"],
            "timing_call_count": 2,
            "counter_probe_call_count": 2,
            "simulation_execution_count": 0,
            "total_simulated_shots": 0,
        }
        if "error_map_descriptor_hash" in unit:
            row["error_map_descriptor_hash"] = unit["error_map_descriptor_hash"]
            row["exact_minimum_gap_ulp_ratio"] = unit["exact_minimum_gap_ulp_ratio"]
        row["row_hash"] = canonical_hash(row)
        rows.append(row)

    manifest = {
        "title": "R183 prefix-initialization isolated paired worker",
        "version": 0,
        "method": METHOD,
        "status": "isolated_paired_worker_complete",
        "cell": cell,
        "process_id": os.getpid(),
        "process_instance_uuid": str(uuid.uuid4()),
        "started_at_unix": started_at,
        "preregistration": preregistration,
        "protocol_payload_hash": protocol["payload_hash"],
        "design_contract_payload_hash": design["payload_hash"],
        "contract_payload_hash": contract["payload_hash"],
        "environment": actual_environment(),
        "accelerator_path": str(binary),
        "accelerator_sha256": file_sha256(binary),
        "input_path": prepared["input_path"],
        "input_sha256": file_sha256(root / prepared["input_path"]),
        "source_worker_path": prepared["source_worker_path"],
        "target_descriptor_sha256": target_descriptor(prepared["backend"])[
            "descriptor_hash"
        ],
        "measurement_pair_order_rule": "AB_on_even_pair_BA_on_odd_pair_then_same_order_probes",
        "warmup_call_count": counts["warmups_per_arm_per_cell"] * len(ARMS),
        "warmup_matches_expected": warmup_matches,
        "recorded_pair_count": len(rows),
        "timing_call_count": sum(row["timing_call_count"] for row in rows),
        "counter_probe_call_count": sum(
            row["counter_probe_call_count"] for row in rows
        ),
        "ab_pair_count": sum(
            row["execution_order"] == ["baseline", "candidate"] for row in rows
        ),
        "ba_pair_count": sum(
            row["execution_order"] == ["candidate", "baseline"] for row in rows
        ),
        "replay_rows": rows,
        "simulation_execution_count": 0,
        "total_simulated_shots": 0,
    }
    manifest["manifest_hash"] = canonical_hash(manifest)
    write_json(path, manifest)
    return manifest


def prepare_overlay(root: Path) -> Path:
    spec = importlib.util.find_spec("qiskit")
    if spec is None or not spec.submodule_search_locations:
        raise ValueError("R183 cannot locate the installed Qiskit package")
    source = Path(next(iter(spec.submodule_search_locations))).resolve()
    binary_hash = file_sha256(root / BINARY_PATH)
    overlay = Path("/tmp") / f"prometheus-r183-overlay-{binary_hash[:16]}"
    if overlay.exists():
        shutil.rmtree(overlay)
    package = overlay / "qiskit"
    shutil.copytree(source, package)
    for candidate in package.glob("_accelerate*.so"):
        candidate.unlink()
    installed = package / "_accelerate.abi3.so"
    shutil.copy2(root / BINARY_PATH, installed)
    if file_sha256(installed) != binary_hash:
        raise ValueError("R183 overlay accelerator copy mismatch")
    return overlay


def launch_worker(
    root: Path,
    overlay: Path,
    cell_id: str,
    preregistration: dict[str, str],
    process_environment: dict[str, str],
) -> None:
    environment = dict(os.environ)
    environment.update(process_environment)
    environment["PYTHONPATH"] = os.pathsep.join(
        [str(overlay), str(root / "tools"), environment.get("PYTHONPATH", "")]
    )
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--root",
        str(root),
        "--worker-cell",
        cell_id,
        "--preregistration-commit",
        preregistration["commit"],
        "--preregistration-discussion",
        preregistration["discussion"],
        "--preregistration-created-at",
        preregistration["created_at"],
    ]
    completed = subprocess.run(
        command,
        cwd=root,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"R183 worker failed: {cell_id}\n{completed.stdout}\n{completed.stderr}"
        )


def validate_worker(manifest: dict[str, Any], path: Path) -> None:
    validate_hash_field(manifest, "manifest_hash", f"worker {path.name}")
    for row in manifest["replay_rows"]:
        validate_hash_field(row, "row_hash", f"row {path.name}")


def classify(
    protocol: dict[str, Any],
    manifests: list[dict[str, Any]],
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cell_summaries = []
    for manifest in sorted(manifests, key=lambda item: item["cell"]["cell_id"]):
        selected = manifest["replay_rows"]
        baseline_times = [
            row["arms"]["baseline"]["elapsed_nanoseconds"] for row in selected
        ]
        candidate_times = [
            row["arms"]["candidate"]["elapsed_nanoseconds"] for row in selected
        ]
        ratios = [row["candidate_to_baseline_elapsed_ratio"] for row in selected]
        summary = {
            "cell": manifest["cell"],
            "measured_pair_count": len(selected),
            "ab_pair_count": manifest["ab_pair_count"],
            "ba_pair_count": manifest["ba_pair_count"],
            "baseline_median_elapsed_nanoseconds": statistics.median(baseline_times),
            "candidate_median_elapsed_nanoseconds": statistics.median(candidate_times),
            "median_paired_candidate_to_baseline_ratio": statistics.median(ratios),
            "candidate_faster_pair_count": sum(ratio < 1.0 for ratio in ratios),
            "baseline_initialized_limb_count": sum(
                row["arms"]["baseline"]["cost_counters"][
                    "destination_initialized_limb_count"
                ]
                for row in selected
            ),
            "candidate_initialized_limb_count": sum(
                row["arms"]["candidate"]["cost_counters"][
                    "destination_initialized_limb_count"
                ]
                for row in selected
            ),
        }
        summary["cell_summary_hash"] = canonical_hash(summary)
        cell_summaries.append(summary)

    baseline_initialized = sum(
        row["arms"]["baseline"]["cost_counters"]["destination_initialized_limb_count"]
        for row in rows
    )
    candidate_initialized = sum(
        row["arms"]["candidate"]["cost_counters"]["destination_initialized_limb_count"]
        for row in rows
    )
    write_reduction = 1.0 - candidate_initialized / baseline_initialized
    mappings_pass = all(
        row["cross_arm_timing_mapping_match"]
        and row["cross_arm_probe_mapping_match"]
        and all(
            row["arms"][arm]["timing_matches_expected"]
            and row["arms"][arm]["probe_matches_expected"]
            and row["arms"][arm]["timing_probe_mapping_match"]
            for arm in ARMS
        )
        for row in rows
    )
    non_initialization_equal = all(
        row["non_initialization_counters_equal"] for row in rows
    )
    baseline_full_width_positive = all(
        row["arms"]["baseline"]["cost_counters"]["full_width_destination_count"] > 0
        for row in rows
    )
    candidate_full_width_zero = all(
        row["arms"]["candidate"]["cost_counters"]["full_width_destination_count"] == 0
        for row in rows
    )
    h1_rule = protocol["frozen_hypotheses"][0]
    h1_supported = (
        mappings_pass
        and non_initialization_equal
        and baseline_full_width_positive
        and candidate_full_width_zero
        and write_reduction
        >= h1_rule["minimum_initialized_limb_write_reduction_fraction"]
    )
    paired_ratio = statistics.median(
        row["candidate_to_baseline_elapsed_ratio"] for row in rows
    )
    h2_rule = protocol["frozen_hypotheses"][1]
    speed_success = (
        paired_ratio <= h2_rule["maximum_candidate_to_baseline_paired_median_ratio"]
    )
    if not h1_supported:
        h2_classification = "inconclusive_isolation_gate_failed"
    elif speed_success:
        h2_classification = "unused_tail_initialization_supported_as_source_bound_contributor_not_causal"
    else:
        h2_classification = (
            "unused_tail_initialization_rejected_as_dominant_source_bound_cost"
        )
    h3_rule = protocol["frozen_hypotheses"][2]
    h3_supported = (
        len(cell_summaries) == h3_rule["required_cell_count"]
        and all(
            summary["ab_pair_count"] == h3_rule["required_ab_pairs_per_cell"]
            for summary in cell_summaries
        )
        and all(
            summary["ba_pair_count"] == h3_rule["required_ba_pairs_per_cell"]
            for summary in cell_summaries
        )
    )
    classifications = {
        "H1-isolated-initialization-write": {
            "classification": "isolated_initialization_write_reduction_passed"
            if h1_supported
            else "isolation_gate_failed",
            "supported_under_frozen_rule": h1_supported,
            "initialized_limb_write_reduction_fraction": write_reduction,
            "baseline_initialized_limb_count": baseline_initialized,
            "candidate_initialized_limb_count": candidate_initialized,
            "mapping_integrity_passed": mappings_pass,
            "non_initialization_counters_equal": non_initialization_equal,
            "baseline_full_width_destination_positive_all_pairs": baseline_full_width_positive,
            "candidate_full_width_destination_zero_all_pairs": candidate_full_width_zero,
        },
        "H2-unused-tail-dominance": {
            "classification": h2_classification,
            "supported_under_frozen_rule": h1_supported and speed_success,
            "median_paired_candidate_to_baseline_ratio": paired_ratio,
            "speed_threshold": h2_rule[
                "maximum_candidate_to_baseline_paired_median_ratio"
            ],
        },
        "H3-workload-heterogeneity": {
            "classification": "all_cells_and_orders_reported"
            if h3_supported
            else "coverage_or_order_balance_failed",
            "supported_under_frozen_rule": h3_supported,
            "reported_cell_count": len(cell_summaries),
            "candidate_faster_cell_count": sum(
                summary["median_paired_candidate_to_baseline_ratio"] < 1.0
                for summary in cell_summaries
            ),
            "candidate_speed_success_cell_count": sum(
                summary["median_paired_candidate_to_baseline_ratio"]
                <= h2_rule["maximum_candidate_to_baseline_paired_median_ratio"]
                for summary in cell_summaries
            ),
        },
    }
    return cell_summaries, classifications


def aggregate(
    root: Path,
    protocol: dict[str, Any],
    design: dict[str, Any],
    contract: dict[str, Any],
    preregistration: dict[str, str],
) -> dict[str, Any]:
    build = json.loads((root / BUILD_MANIFEST_PATH).read_text(encoding="utf-8"))
    validate_hash_field(build, "payload_hash", "build manifest")
    manifests = []
    artifacts = []
    for path in sorted((root / OUT_DIR).glob("*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        validate_worker(manifest, path)
        manifests.append(manifest)
        artifacts.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": file_sha256(path),
                "manifest_hash": manifest["manifest_hash"],
            }
        )
    rows = [row for manifest in manifests for row in manifest["replay_rows"]]
    cell_summaries, classifications = classify(protocol, manifests, rows)
    counter_vectors: dict[tuple[str, str, str], set[tuple[int, ...]]] = defaultdict(set)
    for row in rows:
        for arm in ARMS:
            key = (row["cell_id"], row["subcell_id"], arm)
            counter_vectors[key].add(
                tuple(row["arms"][arm]["cost_counters"][name] for name in COUNTER_KEYS)
            )
    deterministic_count = sum(len(values) == 1 for values in counter_vectors.values())
    counts = protocol["frozen_workload"]
    public_epoch = int(
        datetime.fromisoformat(
            preregistration["created_at"].replace("Z", "+00:00")
        ).timestamp()
    )
    mappings_pass = classifications["H1-isolated-initialization-write"][
        "mapping_integrity_passed"
    ]
    counters_complete = all(
        set(row["arms"][arm]["cost_counters"]) == set(COUNTER_KEYS)
        and all(
            isinstance(value, int) and value >= 0
            for value in row["arms"][arm]["cost_counters"].values()
        )
        for row in rows
        for arm in ARMS
    )
    requirements = {
        "P1": True,
        "P2": all(manifest["started_at_unix"] > public_epoch for manifest in manifests),
        "P3": True,
        "P4": (
            build.get("status")
            == "linux_x86_64_pyext_built_and_imported_after_preregistration"
            and build.get("preregistration") == preregistration
            and build.get("accelerator", {}).get("sha256")
            == file_sha256(root / BINARY_PATH)
            and build.get("github_actions", {}).get("sha") == preregistration["commit"]
            and build.get("github_actions", {})
            .get("run_url", "")
            .startswith(
                "https://github.com/crystal-tensor/Prometheus-plan/actions/runs/"
            )
        ),
        "P5": mappings_pass,
        "P6": counters_complete and deterministic_count == len(counter_vectors),
        "P7": classifications["H1-isolated-initialization-write"][
            "non_initialization_counters_equal"
        ],
        "P8": (
            len(manifests) == counts["worker_count"]
            and len(rows) == counts["measured_pair_count"]
            and sum(manifest["warmup_call_count"] for manifest in manifests)
            == counts["warmup_call_count"]
            and all(
                manifest["recorded_pair_count"] == counts["measured_pairs_per_cell"]
                for manifest in manifests
            )
            and all(
                manifest["ab_pair_count"] == counts["ab_pairs_per_cell"]
                for manifest in manifests
            )
            and all(
                manifest["ba_pair_count"] == counts["ba_pairs_per_cell"]
                for manifest in manifests
            )
        ),
        "P9": set(classifications)
        == {
            "H1-isolated-initialization-write",
            "H2-unused-tail-dominance",
            "H3-workload-heterogeneity",
        },
        "P10": False,
        "P11": all(
            row["simulation_execution_count"] == 0 and row["total_simulated_shots"] == 0
            for row in rows
        ),
        "P12": True,
    }
    summary = {
        "worker_count": len(manifests),
        "expected_worker_count": counts["worker_count"],
        "workload_cell_count": len(cell_summaries),
        "recorded_pair_count": len(rows),
        "timing_call_count": sum(row["timing_call_count"] for row in rows),
        "counter_probe_call_count": sum(
            row["counter_probe_call_count"] for row in rows
        ),
        "warmup_call_count": sum(
            manifest["warmup_call_count"] for manifest in manifests
        ),
        "total_qiskit_function_call_count": sum(
            row["timing_call_count"] + row["counter_probe_call_count"] for row in rows
        )
        + sum(manifest["warmup_call_count"] for manifest in manifests),
        "mapping_integrity_pair_count": sum(
            row["cross_arm_timing_mapping_match"]
            and row["cross_arm_probe_mapping_match"]
            and all(
                row["arms"][arm]["timing_matches_expected"]
                and row["arms"][arm]["probe_matches_expected"]
                for arm in ARMS
            )
            for row in rows
        ),
        "non_initialization_counter_equal_pair_count": sum(
            row["non_initialization_counters_equal"] for row in rows
        ),
        "counter_determinism_group_count": len(counter_vectors),
        "counter_determinism_pass_count": deterministic_count,
        "requirements_passed": sum(requirements.values()),
        "requirements_failed": sum(not value for value in requirements.values()),
        "pending_requirement": "P10 independent oracle",
        "simulation_execution_count": 0,
        "total_simulated_shots": 0,
    }
    result = {
        "title": "B4/B8/B10 R183 prefix-initialization micro-ablation",
        "version": 0,
        "method": METHOD,
        "status": "prefix_initialization_ablation_complete_independent_oracle_pending",
        "preregistration": preregistration,
        "protocol_path": PROTOCOL_PATH,
        "protocol_payload_hash": protocol["payload_hash"],
        "design_contract_path": DESIGN_CONTRACT_PATH,
        "design_contract_payload_hash": design["payload_hash"],
        "contract_path": CONTRACT_PATH,
        "contract_payload_hash": contract["payload_hash"],
        "build_manifest_path": BUILD_MANIFEST_PATH,
        "build_manifest_payload_hash": build["payload_hash"],
        "counter_keys": COUNTER_KEYS,
        "non_initialization_counter_keys": NON_INITIALIZATION_COUNTER_KEYS,
        "cell_summaries": cell_summaries,
        "hypothesis_classifications": classifications,
        "requirements": requirements,
        "requirements_passed": summary["requirements_passed"],
        "requirements_failed": summary["requirements_failed"],
        "summary": summary,
        "worker_artifacts": artifacts,
        "hardware_result_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "solved_frontier_claimed": False,
        "production_qiskit_remedy_claimed": False,
        "causal_bottleneck_claimed": False,
        "new_credit_delta": 0,
    }
    result["payload_hash"] = canonical_hash(result)
    write_json(root / RESULT_PATH, result)
    write_report(root, result)
    return result


def write_report(root: Path, result: dict[str, Any]) -> None:
    summary = result["summary"]
    h1 = result["hypothesis_classifications"]["H1-isolated-initialization-write"]
    h2 = result["hypothesis_classifications"]["H2-unused-tail-dominance"]
    h3 = result["hypothesis_classifications"]["H3-workload-heterogeneity"]
    lines = [
        "# B4/B8/B10 R183 Prefix-Initialization Micro-Ablation",
        "",
        f"- Status: `{result['status']}`",
        f"- Result payload hash: `{result['payload_hash']}`",
        f"- Requirements: `{result['requirements_passed']}/12` passed; P10 awaits the independent oracle",
        "",
        "## Paired Measurement",
        "",
        f"R183 completed `{summary['recorded_pair_count']}` same-process AB/BA pairs across `{summary['worker_count']}` isolated workers and `{summary['workload_cell_count']}` cells. Both arms preserve the expected mapping on `{summary['mapping_integrity_pair_count']}/{summary['recorded_pair_count']}` pairs, and all five non-initialization counters agree on `{summary['non_initialization_counter_equal_pair_count']}/{summary['recorded_pair_count']}` pairs.",
        "",
        "## Frozen Classifications",
        "",
        f"- H1: `{h1['classification']}`; initialized-limb write reduction `{h1['initialized_limb_write_reduction_fraction']:.6f}`.",
        f"- H2: `{h2['classification']}`; paired candidate/baseline median ratio `{h2['median_paired_candidate_to_baseline_ratio']:.6f}` against the frozen `0.90` threshold.",
        f"- H3: `{h3['classification']}`; candidate is faster in `{h3['candidate_faster_cell_count']}/{h3['reported_cell_count']}` cell medians and clears the speed threshold in `{h3['candidate_speed_success_cell_count']}` cells.",
        "",
        "## Claim Boundary",
        "",
        "P10 remains pending until the stdlib-only oracle independently recomputes every artifact hash, mapping outcome, counter equality, paired ratio, workload count, and frozen classification. This micro-ablation does not establish a production Qiskit remedy, complete causal attribution, hardware behavior, quantum advantage, BQP separation, a solved frontier, or new credit.",
        "",
    ]
    (root / REPORT_PATH).write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--preregistration-commit", required=True)
    parser.add_argument("--preregistration-discussion", required=True)
    parser.add_argument("--preregistration-created-at", required=True)
    parser.add_argument("--worker-cell")
    args = parser.parse_args()
    root = args.root.resolve()
    protocol = json.loads((root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    design = json.loads((root / DESIGN_CONTRACT_PATH).read_text(encoding="utf-8"))
    contract = json.loads((root / CONTRACT_PATH).read_text(encoding="utf-8"))
    r181 = json.loads((root / R181_PROTOCOL_PATH).read_text(encoding="utf-8"))
    preregistration = runtime_preregistration(root, args, contract)
    validate_contract(
        root,
        protocol,
        design,
        contract,
        require_unopened=not bool(args.worker_cell),
        require_build=True,
    )
    if args.worker_cell:
        execute_worker(
            root,
            protocol,
            design,
            contract,
            r181,
            str(args.worker_cell),
            preregistration,
        )
        return 0
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "amd64"}:
        raise ValueError("R183 replay requires Linux x86-64")
    overlay = prepare_overlay(root)
    for cell in cell_definitions(r181):
        launch_worker(
            root,
            overlay,
            cell["cell_id"],
            preregistration,
            contract["process_environment"],
        )
    result = aggregate(root, protocol, design, contract, preregistration)
    print(
        json.dumps(
            {
                "status": result["status"],
                "payload_hash": result["payload_hash"],
                "requirements_passed": result["requirements_passed"],
                "requirements_failed": result["requirements_failed"],
                "summary": result["summary"],
                "hypothesis_classifications": result["hypothesis_classifications"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
