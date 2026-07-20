#!/usr/bin/env python3
"""Run the preregistered R185 windowed-exact-score micro-ablation."""

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


METHOD = "b4_b8_r185_macos_arm64_replication_replay_v0"
PROTOCOL_PATH = "results/B4_B8_R185_macos_arm64_replication_protocol_v0.json"
DESIGN_CONTRACT_PATH = (
    "benchmarks/B4_B8_R185_macos_arm64_replication_contract_v0.json"
)
CONTRACT_PATH = "benchmarks/B4_B8_R185_macos_arm64_replication_execution_contract_v0.json"
R181_PROTOCOL_PATH = "results/B4_B8_R181_active_limb_protocol_v0.json"
BINARY_PATH = (
    "research/source_lineage/Qiskit_2_4_1_R185_window_exact_pyext.arm64-darwin.so"
)
BUILD_MANIFEST_PATH = "research/source_lineage/Qiskit_2_4_1_R185_window_exact_macos_arm64_build_manifest.json"
OUT_DIR = "results/B4_B8_R185_macos_arm64_replication_replay"
RESULT_PATH = "results/B4_B8_R185_macos_arm64_replication_v0.json"
REPORT_PATH = "research/B4_B8_R185_macos_arm64_replication.md"
R184_PROTOCOL_PATH = "results/B4_B8_R184_window_exact_score_protocol_v0.json"
R184_RESULT_PATH = "results/B4_B8_R184_window_exact_score_v0.json"
R184_ORACLE_PATH = "results/B4_B8_R184_independent_oracle_v0.json"
R184_BUILD_PATH = "research/source_lineage/Qiskit_2_4_1_R184_window_exact_linux_x86_64_build_manifest.json"
ARMS = {
    "baseline": {
        "policy": "rust_biguint_exact_retained_binary64",
        "timing": "vf2_layout_pass_average_exact_score",
    },
    "reference": {
        "policy": "rust_prefix_initialized_34_limb_exact",
        "timing": "vf2_layout_pass_average_prefix_initialized_exact_score",
    },
    "candidate": {
        "policy": "rust_windowed_4_limb_exact_with_biguint_fallback",
        "timing": "vf2_layout_pass_average_window_exact_score",
        "probe": "vf2_layout_pass_average_window_exact_score_r184_cost_traced",
    },
}
ARM_ORDERS = [
    ["baseline", "reference", "candidate"],
    ["baseline", "candidate", "reference"],
    ["reference", "baseline", "candidate"],
    ["reference", "candidate", "baseline"],
    ["candidate", "baseline", "reference"],
    ["candidate", "reference", "baseline"],
]
COUNTER_KEYS = [
    "leaf_construction_count",
    "window_combine_count",
    "window_compare_count",
    "compact_result_count",
    "fallback_transition_count",
    "wide_combine_count",
    "maximum_window_limb_count",
    "score_object_size_bytes",
]


def validate_hash_field(payload: dict[str, Any], field: str, label: str) -> str:
    body = dict(payload)
    observed = body.pop(field, None)
    if not observed or observed != canonical_hash(body):
        raise ValueError(f"R185 {label} hash mismatch")
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
        != "b4_b8_r185_macos_arm64_replication_protocol_v0"
    ):
        raise ValueError("R185 protocol identity mismatch")
    if (
        design.get("contract_id")
        != "B4-B8-R185-macos-arm64-replication-design-contract-v0"
    ):
        raise ValueError("R185 design contract identity mismatch")
    if (
        contract.get("contract_id")
        != "B4-B8-R185-macos-arm64-replication-execution-contract-v0"
    ):
        raise ValueError("R185 execution contract identity mismatch")
    if contract.get("execution_started") is not False:
        raise ValueError("R185 execution contract is not unopened")
    if contract.get("protocol_payload_hash") != protocol_hash:
        raise ValueError("R185 protocol binding mismatch")
    if contract.get("design_contract_payload_hash") != design_hash:
        raise ValueError("R185 design contract binding mismatch")
    for section in ("source_bindings", "tool_bindings"):
        for binding in contract[section].values():
            path = root / binding["path"]
            if not path.is_file() or file_sha256(path) != binding["sha256"]:
                raise ValueError(f"R185 binding mismatch: {binding['path']}")
    generator = contract["contract_generator_binding"]
    generator_path = root / generator["path"]
    if (
        not generator_path.is_file()
        or file_sha256(generator_path) != generator["sha256"]
    ):
        raise ValueError("R185 execution-contract generator binding mismatch")
    if require_unopened:
        for relative in contract["result_paths_must_be_absent"]:
            if (root / relative).exists():
                raise ValueError(f"R185 evidence existed before execution: {relative}")
    if require_build:
        for relative in contract["build_output_paths_created_before_replay"]:
            if not (root / relative).exists():
                raise ValueError(f"R185 required build output is missing: {relative}")


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
        raise ValueError("R185 runtime commit does not match HEAD")
    if (
        observed["discussion"] != public["discussion"]
        or observed["created_at"] != public["created_at"]
    ):
        raise ValueError("R185 runtime public preregistration mismatch")
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
        raise ValueError("R185 runtime commit predates the public design commit")
    remote_main = subprocess.check_output(
        ["git", "ls-remote", "origin", "refs/heads/main"], cwd=root, text=True
    ).split()[0]
    if remote_main != current_commit:
        raise ValueError("R185 runtime commit is not the current public main")
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
        raise ValueError(f"R185 probe returned {len(values)} counters")
    counters = {key: int(value) for key, value in zip(COUNTER_KEYS, values)}
    if any(value < 0 for value in counters.values()):
        raise ValueError("R185 probe returned a negative counter")
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
        raise ValueError("R185 worker identity is outside the frozen matrix")
    path = root / worker_path(cell_id)
    if path.exists():
        raise ValueError(f"R185 worker already exists: {path}")
    binary = imported_binary()
    if file_sha256(binary) != file_sha256(root / BINARY_PATH):
        raise ValueError("R185 worker imported the wrong accelerator")
    cell = cells[cell_id]
    prepared = (
        prepare_standard(root, r181, cell)
        if cell["kind"] == "standard"
        else prepare_small_gap(root, r181, cell)
    )
    functions = {
        arm: getattr(vf2_module, definition["timing"])
        for arm, definition in ARMS.items()
    }
    candidate_probe = getattr(vf2_module, ARMS["candidate"]["probe"])
    units = prepared["work_units"]
    counts = protocol["frozen_workload"]
    started_at = int(time.time())
    warmup_matches = {arm: 0 for arm in ARMS}
    for warmup_index in range(counts["warmups_per_arm_per_cell"]):
        unit = units[warmup_index % len(units)]
        order = ARM_ORDERS[warmup_index % len(ARM_ORDERS)]
        for arm in order:
            vector = run_vf2(
                functions[arm],
                prepared["dag"],
                prepared["target"],
                unit["error_map"],
            )
            warmup_matches[arm] += int(vector == unit["expected"])

    rows = []
    for triplet_index in range(counts["measured_triplets_per_cell"]):
        unit = units[triplet_index % len(units)]
        order = ARM_ORDERS[triplet_index % len(ARM_ORDERS)]
        arm_rows: dict[str, dict[str, Any]] = {}
        for arm in order:
            started = time.perf_counter_ns()
            timing_vector = run_vf2(
                functions[arm],
                prepared["dag"],
                prepared["target"],
                unit["error_map"],
            )
            arm_rows[arm] = {
                "policy": ARMS[arm]["policy"],
                "timing_mapping_vector": timing_vector,
                "elapsed_nanoseconds": time.perf_counter_ns() - started,
            }
        probe_vector, counters = run_probe(
            candidate_probe,
            prepared["dag"],
            prepared["target"],
            unit["error_map"],
        )
        for arm in ARMS:
            arm_rows[arm]["timing_matches_expected"] = (
                arm_rows[arm]["timing_mapping_vector"] == unit["expected"]
            )
        arm_rows["candidate"].update(
            {
                "probe_mapping_vector": probe_vector,
                "probe_matches_expected": probe_vector == unit["expected"],
                "timing_probe_mapping_match": arm_rows["candidate"][
                    "timing_mapping_vector"
                ]
                == probe_vector,
                "cost_counters": counters,
            }
        )
        row: dict[str, Any] = {
            "cell_id": cell_id,
            "subcell_id": unit["subcell_id"],
            "kind": cell["kind"],
            "triplet_index": triplet_index,
            "case_id": unit["case_id"],
            "execution_order": order,
            "expected_mapping_vector": unit["expected"],
            "arms": arm_rows,
            "cross_arm_timing_mapping_match": all(
                arm_rows[arm]["timing_mapping_vector"]
                == arm_rows["baseline"]["timing_mapping_vector"]
                for arm in ARMS
            ),
            "candidate_probe_matches_timing": arm_rows["candidate"]
            ["timing_probe_mapping_match"],
            "candidate_to_baseline_elapsed_ratio": arm_rows["candidate"][
                "elapsed_nanoseconds"
            ]
            / arm_rows["baseline"]["elapsed_nanoseconds"],
            "candidate_to_reference_elapsed_ratio": arm_rows["candidate"][
                "elapsed_nanoseconds"
            ]
            / arm_rows["reference"]["elapsed_nanoseconds"],
            "timing_call_count": 3,
            "counter_probe_call_count": 1,
            "simulation_execution_count": 0,
            "total_simulated_shots": 0,
        }
        if "error_map_descriptor_hash" in unit:
            row["error_map_descriptor_hash"] = unit["error_map_descriptor_hash"]
            row["exact_minimum_gap_ulp_ratio"] = unit["exact_minimum_gap_ulp_ratio"]
        row["row_hash"] = canonical_hash(row)
        rows.append(row)

    manifest = {
        "title": "R185 windowed exact-score isolated triplet worker",
        "version": 0,
        "method": METHOD,
        "status": "isolated_triplet_worker_complete",
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
        "measurement_triplet_order_rule": "all_six_permutations_repeated_six_times_then_window_probe",
        "warmup_call_count": counts["warmups_per_arm_per_cell"] * len(ARMS),
        "warmup_matches_expected": warmup_matches,
        "recorded_triplet_count": len(rows),
        "timing_call_count": sum(row["timing_call_count"] for row in rows),
        "counter_probe_call_count": sum(
            row["counter_probe_call_count"] for row in rows
        ),
        "arm_order_counts": {
            ">".join(order): sum(row["execution_order"] == order for row in rows)
            for order in ARM_ORDERS
        },
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
        raise ValueError("R185 cannot locate the installed Qiskit package")
    source = Path(next(iter(spec.submodule_search_locations))).resolve()
    binary_hash = file_sha256(root / BINARY_PATH)
    overlay = Path("/tmp") / f"prometheus-r185-overlay-{binary_hash[:16]}"
    if overlay.exists():
        shutil.rmtree(overlay)
    package = overlay / "qiskit"
    shutil.copytree(source, package)
    for candidate in package.glob("_accelerate*"):
        if not candidate.is_file():
            continue
        candidate.unlink()
    installed = package / "_accelerate.abi3.so"
    shutil.copy2(root / BINARY_PATH, installed)
    if file_sha256(installed) != binary_hash:
        raise ValueError("R185 overlay accelerator copy mismatch")
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
            f"R185 worker failed: {cell_id}\n{completed.stdout}\n{completed.stderr}"
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
        arm_times = {
            arm: [row["arms"][arm]["elapsed_nanoseconds"] for row in selected]
            for arm in ARMS
        }
        reference_ratios = [
            row["candidate_to_reference_elapsed_ratio"] for row in selected
        ]
        baseline_ratios = [
            row["candidate_to_baseline_elapsed_ratio"] for row in selected
        ]
        summary = {
            "cell": manifest["cell"],
            "measured_triplet_count": len(selected),
            "arm_order_counts": manifest["arm_order_counts"],
            "arm_median_elapsed_nanoseconds": {
                arm: statistics.median(values) for arm, values in arm_times.items()
            },
            "median_paired_candidate_to_reference_ratio": statistics.median(
                reference_ratios
            ),
            "median_paired_candidate_to_baseline_ratio": statistics.median(
                baseline_ratios
            ),
            "candidate_faster_than_reference_triplet_count": sum(
                ratio < 1.0 for ratio in reference_ratios
            ),
            "candidate_faster_than_baseline_triplet_count": sum(
                ratio < 1.0 for ratio in baseline_ratios
            ),
            "maximum_window_limb_count": max(
                row["arms"]["candidate"]["cost_counters"][
                    "maximum_window_limb_count"
                ]
                for row in selected
            ),
            "fallback_transition_count": sum(
                row["arms"]["candidate"]["cost_counters"][
                    "fallback_transition_count"
                ]
                for row in selected
            ),
            "wide_combine_count": sum(
                row["arms"]["candidate"]["cost_counters"]["wide_combine_count"]
                for row in selected
            ),
            "score_object_size_bytes": max(
                row["arms"]["candidate"]["cost_counters"][
                    "score_object_size_bytes"
                ]
                for row in selected
            ),
        }
        summary["cell_summary_hash"] = canonical_hash(summary)
        cell_summaries.append(summary)

    mappings_pass = all(
        row["cross_arm_timing_mapping_match"]
        and all(
            row["arms"][arm]["timing_matches_expected"]
            for arm in ARMS
        )
        and row["arms"]["candidate"]["probe_matches_expected"]
        and row["candidate_probe_matches_timing"]
        for row in rows
    )
    h1_supported = mappings_pass
    h2_rule = protocol["frozen_hypotheses"][1]
    maximum_window_limbs = max(
        row["arms"]["candidate"]["cost_counters"]["maximum_window_limb_count"]
        for row in rows
    )
    maximum_object_size = max(
        row["arms"]["candidate"]["cost_counters"]["score_object_size_bytes"]
        for row in rows
    )
    fallback_transitions = sum(
        row["arms"]["candidate"]["cost_counters"]["fallback_transition_count"]
        for row in rows
    )
    wide_combines = sum(
        row["arms"]["candidate"]["cost_counters"]["wide_combine_count"]
        for row in rows
    )
    h2_supported = (
        maximum_window_limbs <= h2_rule["maximum_window_limb_count"]
        and maximum_object_size <= h2_rule["maximum_score_object_size_bytes"]
        and fallback_transitions == 0
        and wide_combines == 0
    )
    reference_ratio = statistics.median(
        row["candidate_to_reference_elapsed_ratio"] for row in rows
    )
    baseline_ratio = statistics.median(
        row["candidate_to_baseline_elapsed_ratio"] for row in rows
    )
    h3_rule = protocol["frozen_hypotheses"][2]
    h3_speed = (
        reference_ratio
        <= h3_rule["maximum_candidate_to_reference_paired_median_ratio"]
    )
    h4_rule = protocol["frozen_hypotheses"][3]
    order_coverage = (
        len(cell_summaries) == h4_rule["required_cell_count"]
        and all(
            set(summary["arm_order_counts"])
            == {">".join(order) for order in ARM_ORDERS}
            and all(
                count == h4_rule["required_count_per_order_per_cell"]
                for count in summary["arm_order_counts"].values()
            )
            for summary in cell_summaries
        )
    )
    h4_speed = (
        baseline_ratio <= h4_rule["maximum_candidate_to_baseline_paired_median_ratio"]
    )
    classifications = {
        "H1-exact-integrity": {
            "classification": "all_timing_and_probe_mappings_exact"
            if h1_supported
            else "mapping_integrity_failed",
            "supported_under_frozen_rule": h1_supported,
            "mapping_integrity_passed": mappings_pass,
        },
        "H2-compact-common-path": {
            "classification": "compact_path_observed_without_fallback"
            if h2_supported
            else "compactness_or_fallback_gate_failed",
            "supported_under_frozen_rule": h2_supported,
            "maximum_window_limb_count": maximum_window_limbs,
            "maximum_score_object_size_bytes": maximum_object_size,
            "fallback_transition_count": fallback_transitions,
            "wide_combine_count": wide_combines,
        },
        "H3-representation-speedup": {
            "classification": "window_materially_faster_than_prefix_reference"
            if h1_supported and h2_supported and h3_speed
            else (
                "window_not_materially_faster_than_prefix_reference"
                if h1_supported and h2_supported
                else "inconclusive_integrity_or_compactness_gate_failed"
            ),
            "supported_under_frozen_rule": h1_supported and h2_supported and h3_speed,
            "median_paired_candidate_to_reference_ratio": reference_ratio,
            "speed_threshold": h3_rule[
                "maximum_candidate_to_reference_paired_median_ratio"
            ],
            "candidate_faster_cell_count": sum(
                summary["median_paired_candidate_to_reference_ratio"] < 1.0
                for summary in cell_summaries
            ),
        },
        "H4-biguint-competitiveness": {
            "classification": "window_competitive_with_biguint"
            if h1_supported and h2_supported and h4_speed and order_coverage
            else (
                "window_slower_than_biguint"
                if h1_supported and h2_supported and order_coverage
                else "inconclusive_integrity_compactness_or_coverage_gate_failed"
            ),
            "supported_under_frozen_rule": h1_supported
            and h2_supported
            and h4_speed
            and order_coverage,
            "median_paired_candidate_to_baseline_ratio": baseline_ratio,
            "competitiveness_threshold": h4_rule[
                "maximum_candidate_to_baseline_paired_median_ratio"
            ],
            "reported_cell_count": len(cell_summaries),
            "candidate_faster_cell_count": sum(
                summary["median_paired_candidate_to_baseline_ratio"] < 1.0
                for summary in cell_summaries
            ),
            "order_coverage_passed": order_coverage,
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
    r184_protocol = json.loads((root / R184_PROTOCOL_PATH).read_text(encoding="utf-8"))
    r184_result = json.loads((root / R184_RESULT_PATH).read_text(encoding="utf-8"))
    r184_oracle = json.loads((root / R184_ORACLE_PATH).read_text(encoding="utf-8"))
    r184_build = json.loads((root / R184_BUILD_PATH).read_text(encoding="utf-8"))
    for label, payload in (
        ("R184 protocol", r184_protocol),
        ("R184 result", r184_result),
        ("R184 oracle", r184_oracle),
        ("R184 build", r184_build),
    ):
        validate_hash_field(payload, "payload_hash", label)
    h5_rule = protocol["frozen_hypotheses"][4]
    linux_supported = all(
        r184_result.get("hypothesis_classifications", {})
        .get(hypothesis_id, {})
        .get("supported_under_frozen_rule")
        is True
        for hypothesis_id in h5_rule["required_supported_hypothesis_ids"]
    )
    macos_supported = all(
        classifications[hypothesis_id]["supported_under_frozen_rule"] is True
        for hypothesis_id in h5_rule["required_supported_hypothesis_ids"]
    )
    identical_patch = (
        r184_build.get("patch", {}).get("sha256")
        == build.get("patch", {}).get("sha256")
        == file_sha256(root / "research/source_lineage/Qiskit_2_4_1_R184_window_exact_score.patch")
    )
    linux_workload = r184_protocol.get("frozen_workload", {})
    macos_workload = protocol.get("frozen_workload", {})
    workload_keys = (
        "workload_cell_count",
        "worker_count",
        "arm_order_permutation_count",
        "repetitions_per_order_per_cell",
        "measured_triplets_per_cell",
        "measured_triplet_count",
        "timing_call_count",
        "counter_probe_call_count",
        "warmup_call_count",
        "total_qiskit_function_call_count",
    )
    identical_workload = all(
        linux_workload.get(key) == macos_workload.get(key) for key in workload_keys
    )
    linux_hypotheses = r184_protocol.get("frozen_hypotheses", [])[:4]
    macos_hypotheses = protocol.get("frozen_hypotheses", [])[:4]
    identical_thresholds = linux_hypotheses == macos_hypotheses
    h5_supported = (
        r184_result.get("payload_hash")
        == h5_rule["required_linux_result_payload_hash"]
        and r184_oracle.get("payload_hash")
        == h5_rule["required_linux_oracle_payload_hash"]
        and r184_oracle.get("requirements_passed") == 12
        and r184_oracle.get("requirements_failed") == 0
        and linux_supported
        and macos_supported
        and identical_patch
        and identical_workload
        and identical_thresholds
    )
    classifications["H5-cross-architecture-transfer"] = {
        "classification": "linux_x86_64_and_macos_arm64_both_support_H1_through_H4"
        if h5_supported
        else "cross_architecture_transfer_gate_failed",
        "supported_under_frozen_rule": h5_supported,
        "linux_H1_through_H4_supported": linux_supported,
        "macos_H1_through_H4_supported": macos_supported,
        "identical_patch": identical_patch,
        "identical_workload": identical_workload,
        "identical_thresholds": identical_thresholds,
        "linux_result_payload_hash": r184_result.get("payload_hash"),
        "linux_oracle_payload_hash": r184_oracle.get("payload_hash"),
    }
    counter_vectors: dict[tuple[str, str], set[tuple[int, ...]]] = defaultdict(set)
    for row in rows:
        key = (row["cell_id"], row["subcell_id"])
        counter_vectors[key].add(
            tuple(
                row["arms"]["candidate"]["cost_counters"][name]
                for name in COUNTER_KEYS
            )
        )
    deterministic_count = sum(len(values) == 1 for values in counter_vectors.values())
    counts = protocol["frozen_workload"]
    public_epoch = int(
        datetime.fromisoformat(
            preregistration["created_at"].replace("Z", "+00:00")
        ).timestamp()
    )
    build_started_epoch = int(
        datetime.fromisoformat(
            build["public_runner_attestation"]["build_started_at"]
        ).timestamp()
    )
    mappings_pass = classifications["H1-exact-integrity"][
        "mapping_integrity_passed"
    ]
    counters_complete = all(
        set(row["arms"]["candidate"]["cost_counters"]) == set(COUNTER_KEYS)
        and all(
            isinstance(value, int) and value >= 0
            for value in row["arms"]["candidate"]["cost_counters"].values()
        )
        for row in rows
    )
    requirements = {
        "P1": True,
        "P2": build_started_epoch > public_epoch
        and all(manifest["started_at_unix"] > public_epoch for manifest in manifests),
        "P3": True,
        "P4": (
            build.get("status")
            == "macos_arm64_pyext_built_and_imported_after_preregistration"
            and build.get("preregistration") == preregistration
            and build.get("accelerator", {}).get("sha256")
            == file_sha256(root / BINARY_PATH)
            and build.get("platform", {}).get("system") == "Darwin"
            and build.get("platform", {}).get("machine") == "arm64"
        ),
        "P5": mappings_pass,
        "P6": counters_complete and deterministic_count == len(counter_vectors),
        "P7": classifications["H2-compact-common-path"][
            "supported_under_frozen_rule"
        ],
        "P8": (
            len(manifests) == counts["worker_count"]
            and len(rows) == counts["measured_triplet_count"]
            and sum(manifest["warmup_call_count"] for manifest in manifests)
            == counts["warmup_call_count"]
            and all(
                manifest["recorded_triplet_count"]
                == counts["measured_triplets_per_cell"]
                for manifest in manifests
            )
            and all(
                set(manifest["arm_order_counts"])
                == {">".join(order) for order in ARM_ORDERS}
                and all(
                    count == counts["repetitions_per_order_per_cell"]
                    for count in manifest["arm_order_counts"].values()
                )
                for manifest in manifests
            )
        ),
        "P9": set(classifications)
        == {
            "H1-exact-integrity",
            "H2-compact-common-path",
            "H3-representation-speedup",
            "H4-biguint-competitiveness",
            "H5-cross-architecture-transfer",
        }
        and all(
            row["supported_under_frozen_rule"]
            for row in classifications.values()
        ),
        "P10": False,
        "P11": (
            build.get("public_runner_attestation", {}).get("mode")
            == "clean_public_main_local_runner"
            and build.get("public_runner_attestation", {}).get("runner_commit")
            == preregistration["commit"]
            and build.get("public_runner_attestation", {}).get(
                "remote_main_at_build_start"
            )
            == preregistration["commit"]
            and build.get("public_runner_attestation", {}).get(
                "clean_worktree_before_build"
            )
            is True
        ),
        "P12": all(
            row["simulation_execution_count"] == 0 and row["total_simulated_shots"] == 0
            for row in rows
        ),
        "P13": all(
            result is False
            for result in (
                protocol["claim_boundary"]["universal_architecture_performance_claimed"],
                protocol["claim_boundary"]["production_qiskit_remedy_claimed"],
                protocol["claim_boundary"]["hardware_result_claimed"],
                protocol["claim_boundary"]["quantum_advantage_claimed"],
                protocol["claim_boundary"]["bqp_separation_claimed"],
                protocol["claim_boundary"]["solved_frontier_claimed"],
            )
        )
        and protocol["claim_boundary"]["new_credit_delta"] == 0,
    }
    summary = {
        "worker_count": len(manifests),
        "expected_worker_count": counts["worker_count"],
        "workload_cell_count": len(cell_summaries),
        "recorded_triplet_count": len(rows),
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
        "mapping_integrity_triplet_count": sum(
            row["cross_arm_timing_mapping_match"]
            and all(
                row["arms"][arm]["timing_matches_expected"]
                for arm in ARMS
            )
            and row["arms"]["candidate"]["probe_matches_expected"]
            and row["candidate_probe_matches_timing"]
            for row in rows
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
        "title": "B4/B8/B10 R185 macOS arm64 exact-score replication",
        "version": 0,
        "method": METHOD,
        "status": "macos_arm64_replication_complete_independent_oracle_pending",
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
    h1 = result["hypothesis_classifications"]["H1-exact-integrity"]
    h2 = result["hypothesis_classifications"]["H2-compact-common-path"]
    h3 = result["hypothesis_classifications"]["H3-representation-speedup"]
    h4 = result["hypothesis_classifications"]["H4-biguint-competitiveness"]
    h5 = result["hypothesis_classifications"]["H5-cross-architecture-transfer"]
    lines = [
        "# B4/B8/B10 R185 Windowed Exact-Score Experiment",
        "",
        f"- Status: `{result['status']}`",
        f"- Result payload hash: `{result['payload_hash']}`",
        f"- Requirements: `{result['requirements_passed']}/13` passed; P10 awaits the independent oracle",
        "",
        "## Three-Arm Measurement",
        "",
        f"R185 completed `{summary['recorded_triplet_count']}` same-process BigUint/prefix/window triplets across `{summary['worker_count']}` isolated workers and `{summary['workload_cell_count']}` cells. All three timing arms plus the separate window probe preserve the expected mapping on `{summary['mapping_integrity_triplet_count']}/{summary['recorded_triplet_count']}` triplets.",
        "",
        "## Frozen Classifications",
        "",
        f"- H1: `{h1['classification']}`; mapping integrity `{h1['mapping_integrity_passed']}`.",
        f"- H2: `{h2['classification']}`; maximum compact limbs `{h2['maximum_window_limb_count']}`, object size `{h2['maximum_score_object_size_bytes']}` bytes, fallback transitions `{h2['fallback_transition_count']}`, wide combines `{h2['wide_combine_count']}`.",
        f"- H3: `{h3['classification']}`; paired window/prefix median ratio `{h3['median_paired_candidate_to_reference_ratio']:.6f}` against the frozen `0.90` threshold.",
        f"- H4: `{h4['classification']}`; paired window/BigUint median ratio `{h4['median_paired_candidate_to_baseline_ratio']:.6f}` against the frozen `1.00` threshold; all-order coverage `{h4['order_coverage_passed']}`.",
        f"- H5: `{h5['classification']}`; Linux H1-H4 `{h5['linux_H1_through_H4_supported']}`, macOS H1-H4 `{h5['macos_H1_through_H4_supported']}`, identical patch/workload/thresholds `{h5['identical_patch']}/{h5['identical_workload']}/{h5['identical_thresholds']}`.",
        "",
        "## Claim Boundary",
        "",
        "P10 remains pending until the stdlib-only oracle independently recomputes every artifact hash, mapping outcome, counter boundary, paired ratio, workload count, and H1-H5 classification. This experiment does not establish a universal platform theorem, full-domain performance theorem, production Qiskit remedy, hardware behavior, quantum advantage, BQP separation, a solved frontier, or new credit.",
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
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("R185 replay requires macOS arm64")
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
