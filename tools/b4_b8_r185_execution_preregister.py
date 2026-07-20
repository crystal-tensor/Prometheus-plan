#!/usr/bin/env python3
"""Bind R185 execution tooling after the public design Discussion exists."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


PROTOCOL_PATH = "results/B4_B8_R185_macos_arm64_replication_protocol_v0.json"
DESIGN_CONTRACT_PATH = (
    "benchmarks/B4_B8_R185_macos_arm64_replication_contract_v0.json"
)
R181_PROTOCOL_PATH = "results/B4_B8_R181_active_limb_protocol_v0.json"
OUTPUT_PATH = "benchmarks/B4_B8_R185_macos_arm64_replication_execution_contract_v0.json"
REPORT_PATH = "research/B4_B8_R185_macos_arm64_replication_execution_contract.md"
TOOL_PATHS = [
    "research/source_lineage/Qiskit_2_4_1_R184_window_exact_score.patch",
    "tools/b4_b8_r185_macos_arm64_replay.py",
    "tools/b4_b8_r185_independent_oracle.py",
    "tools/b4_b8_r185_macos_arm64_build.py",
    "tools/b4_b8_r185_macos_arm64_bundle.py",
]
DIRECT_SOURCE_PATHS = [
    PROTOCOL_PATH,
    DESIGN_CONTRACT_PATH,
    R181_PROTOCOL_PATH,
    "results/B4_B8_R184_window_exact_score_protocol_v0.json",
    "results/B4_B8_R184_window_exact_score_v0.json",
    "results/B4_B8_R184_independent_oracle_v0.json",
    "results/B4_B8_R184_window_exact_score_bundle_v0.json",
    "research/source_lineage/Qiskit_2_4_1_R184_window_exact_linux_x86_64_build_manifest.json",
    "results/B4_B8_R183_prefix_initialization_ablation_v0.json",
    "results/B4_B8_R183_independent_oracle_v0.json",
    "results/B4_B8_R183_prefix_initialization_bundle_v0.json",
    "tools/b4_b8_r182_score_cost_attribution_replay.py",
    "tools/b4_b8_r181_active_limb_replay.py",
    "tools/b4_b8_r119_private_observable_bundle_gate.py",
    "tools/b4_b8_r126_calibration_attribution_ledger.py",
    "tools/b4_b8_r153_independent_seed_replication_holdout.py",
    "tools/b4_b8_r154_deterministic_automatic_replay.py",
    "tools/b4_b8_r160_deterministic_error_map_remediation.py",
]
COUNTER_DEFINITIONS = {
    "leaf_construction_count": "Number of retained-binary64 score leaves constructed by the instrumented score type.",
    "window_combine_count": "Number of exact score combinations performed by the window representation.",
    "window_compare_count": "Number of exact score comparisons performed by the window representation.",
    "compact_result_count": "Number of constructed, identity, or combined scores represented by the four-limb compact variant.",
    "fallback_transition_count": "Number of compact-to-BigUint transitions caused by an exact span or carry exceeding four limbs.",
    "wide_combine_count": "Number of combinations that received at least one BigUint-backed input.",
    "maximum_window_limb_count": "Maximum compact limb count observed during the candidate probe.",
    "score_object_size_bytes": "Rust size_of value for the complete window/fallback score enum.",
    "elapsed_nanoseconds": "Wall-clock nanoseconds for the uninstrumented arm call; counter-probe time is excluded.",
}


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_payload(payload: dict[str, Any], label: str) -> str:
    body = dict(payload)
    observed = body.pop("payload_hash", None)
    if not observed or observed != canonical_hash(body):
        raise ValueError(f"R185 {label} payload hash mismatch")
    return str(observed)


def binding(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise ValueError(f"R185 execution binding is missing: {relative}")
    output: dict[str, Any] = {"path": relative, "sha256": file_sha256(path)}
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        for field in ("payload_hash", "manifest_hash"):
            if field in payload:
                output[field] = payload[field]
    return output


def cells(r181: dict[str, Any]) -> list[dict[str, Any]]:
    output = []
    for dataset in r181["datasets"]:
        for profile in r181["standard_profiles"]:
            output.append(
                {
                    "cell_id": f"standard__{dataset['dataset_id']}__{profile}",
                    "kind": "standard",
                    "dataset_id": dataset["dataset_id"],
                    "profile_id": profile,
                }
            )
    for mode in r181["small_gap_modes"]:
        output.append(
            {"cell_id": f"small-gap__{mode}", "kind": "small-gap", "mode": mode}
        )
    return output


def report(contract: dict[str, Any]) -> str:
    counts = contract["measurement_triplet_contract"]
    return "\n".join(
        [
            "# B4/B8/B10 R185 Execution Contract",
            "",
            "- Status: `execution_tooling_bound_unopened`",
            f"- Contract payload hash: `{contract['payload_hash']}`",
            f"- Tool bindings: `{len(contract['tool_bindings'])}`",
            f"- Source bindings: `{len(contract['source_bindings'])}`",
            f"- Public design commit: `{contract['public_preregistration']['public_design_commit']}`",
            f"- Public Discussion: {contract['public_preregistration']['discussion']}",
            "- Scientific execution: unopened",
            "",
            "## Same-Process Triplets",
            "",
            f"The frozen matrix contains `{counts['measured_triplet_count']}` BigUint/prefix/window triplets in `{counts['expected_worker_count']}` isolated workers. Every triplet runs three uninstrumented timing calls and one separate window probe; probe time is excluded. All six arm orders occur `{counts['repetitions_per_order_per_cell']}` times per cell.",
            "",
            "## Isolation Boundary",
            "",
            "The BigUint arm is the exact dynamic denominator, the 34-limb prefix arm is the latest fixed-width reference, and the candidate stores an exact four-limb window plus a global offset. Any wider exact sum falls back to BigUint; no truncation or approximate comparison is allowed.",
            "",
            "## Claim Boundary",
            "",
            "The unchanged patch, local Darwin arm64 runner, oracle, build, and bundle are hash-bound. The later build must run from a clean commit already published as remote main. This contract is not a timing result, universal platform theorem, full-domain performance theorem, upstream Qiskit remedy, hardware result, quantum advantage, BQP separation, solved frontier, or new credit.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--discussion", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--public-design-commit", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    for relative in (OUTPUT_PATH, REPORT_PATH):
        if (root / relative).exists():
            raise ValueError(f"R185 execution output already exists: {relative}")
    if not args.discussion.startswith(
        "https://github.com/crystal-tensor/Prometheus-plan/discussions/"
    ):
        raise ValueError("R185 public Discussion URL is outside the project repository")
    created = datetime.fromisoformat(args.created_at.replace("Z", "+00:00"))
    if created.timestamp() >= time.time():
        raise ValueError("R185 public Discussion timestamp is not in the past")

    protocol = json.loads((root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    design = json.loads((root / DESIGN_CONTRACT_PATH).read_text(encoding="utf-8"))
    r181 = json.loads((root / R181_PROTOCOL_PATH).read_text(encoding="utf-8"))
    protocol_hash = validate_payload(protocol, "protocol")
    design_hash = validate_payload(design, "design contract")
    if design.get("protocol_payload_hash") != protocol_hash:
        raise ValueError("R185 design protocol binding mismatch")
    if set(design["required_before_execution"]) != set(TOOL_PATHS):
        raise ValueError("R185 design and execution tool lists differ")
    public_design_commit = args.public_design_commit
    current_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    if current_commit != public_design_commit:
        raise ValueError("R185 execution tooling must branch from the public design commit")
    remote_main = subprocess.check_output(
        ["git", "ls-remote", "origin", "refs/heads/main"], cwd=root, text=True
    ).split()[0]
    if remote_main != public_design_commit:
        raise ValueError("R185 public design commit is not remote main")
    design_epoch = int(
        subprocess.check_output(
            ["git", "show", "-s", "--format=%ct", public_design_commit],
            cwd=root,
            text=True,
        ).strip()
    )
    if design_epoch >= int(created.timestamp()):
        raise ValueError("R185 public Discussion must postdate the design commit")

    workload_cells = cells(r181)
    counts = protocol["frozen_workload"]
    measurement_contract = {
        "arm_order_rule": "all_six_permutations_repeated_six_times_per_cell",
        "probe_arm": "candidate",
        "probe_elapsed_excluded_from_timing": True,
        "mapping_equality_required_within_and_across_arms": True,
        "workload_cell_count": counts["workload_cell_count"],
        "expected_worker_count": counts["worker_count"],
        "arm_order_permutation_count": counts["arm_order_permutation_count"],
        "repetitions_per_order_per_cell": counts[
            "repetitions_per_order_per_cell"
        ],
        "measured_triplets_per_cell": counts["measured_triplets_per_cell"],
        "warmups_per_arm_per_cell": counts["warmups_per_arm_per_cell"],
        "measured_triplet_count": counts["measured_triplet_count"],
        "timing_call_count": counts["timing_call_count"],
        "counter_probe_call_count": counts["counter_probe_call_count"],
        "warmup_call_count": counts["warmup_call_count"],
        "total_qiskit_function_call_count": counts["total_qiskit_function_call_count"],
        "small_gap_case_schedule": "triplet_index_modulo_seven_in_frozen_R181_case_order",
        "counter_determinism_group": "cell_id_subcell_id_candidate",
    }
    contract: dict[str, Any] = {
        "title": "B4/B8/B10 R185 windowed-exact-score execution contract",
        "version": 0,
        "contract_id": "B4-B8-R185-macos-arm64-replication-execution-contract-v0",
        "status": "execution_tooling_bound_unopened",
        "execution_tooling_bound": True,
        "execution_started": False,
        "scientific_measurement_started": False,
        "protocol_path": PROTOCOL_PATH,
        "protocol_payload_hash": protocol_hash,
        "design_contract_path": DESIGN_CONTRACT_PATH,
        "design_contract_payload_hash": design_hash,
        "public_preregistration": {
            "discussion": args.discussion,
            "created_at": args.created_at,
            "public_design_commit": public_design_commit,
        },
        "platform_contract": protocol["platform_contract"],
        "process_environment": r181["process_environment"],
        "arms": protocol["frozen_arms"],
        "workload_matrix": {
            "cells": workload_cells,
            "cell_count": len(workload_cells),
            "small_gap_cases": r181["small_gap_cases"],
        },
        "measurement_triplet_contract": measurement_contract,
        "counter_definitions": COUNTER_DEFINITIONS,
        "aggregation_rules": {
            "H1_exact_integrity": "all_three_timing_mappings_and_window_probe_equal_expected",
            "H2_compactness": "maximum_four_limbs_and_64_bytes_with_zero_fallback_or_wide_combines",
            "H3_timing_ratio": "median_of_candidate_elapsed_over_reference_elapsed_across_all_triplets",
            "H3_speed_success": "paired_median_ratio_at_most_0.90_after_H1_and_H2_pass",
            "H4_timing_ratio": "median_of_candidate_elapsed_over_baseline_elapsed_across_all_triplets",
            "H4_competitiveness": "paired_median_ratio_at_most_1.00_after_H1_and_H2_pass",
            "H5_cross_architecture_transfer": "committed_linux_and_new_macos_results_both_support_H1_through_H4_under_identical_patch_workload_and_thresholds",
            "order_coverage": "all_13_cells_with_six_repetitions_of_each_of_six_orders",
        },
        "source_bindings": {
            f"source_{index:03d}": binding(root, relative)
            for index, relative in enumerate(DIRECT_SOURCE_PATHS, start=1)
        },
        "tool_bindings": {
            f"tool_{index:02d}": binding(root, relative)
            for index, relative in enumerate(TOOL_PATHS, start=1)
        },
        "contract_generator_binding": binding(
            root, "tools/b4_b8_r185_execution_preregister.py"
        ),
        "result_paths_must_be_absent": [
            "research/B4_B8_R185_macos_arm64_replication.md",
            "research/B4_B8_R185_independent_oracle.md",
            "results/B4_B8_R185_macos_arm64_replication_replay",
            "results/B4_B8_R185_macos_arm64_replication_v0.json",
            "results/B4_B8_R185_independent_oracle_v0.json",
            "results/B4_B8_R185_macos_arm64_replication_bundle_v0.json",
        ],
        "build_output_paths_created_before_replay": [
            "research/source_lineage/Qiskit_2_4_1_R185_window_exact_pyext.arm64-darwin.so",
            "research/source_lineage/Qiskit_2_4_1_R185_window_exact_macos_arm64_build_manifest.json",
            "research/source_lineage/R185_window_exact_macos_arm64_build_logs",
        ],
        "claim_boundary": protocol["claim_boundary"],
        "generation_attestation": {
            "head_at_generation": current_commit,
            "remote_main_at_generation": remote_main,
            "design_predates_discussion": True,
            "scientific_execution_started": False,
        },
    }
    contract["payload_hash"] = canonical_hash(contract)
    path = root / OUTPUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / REPORT_PATH).write_text(report(contract), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": contract["status"],
                "payload_hash": contract["payload_hash"],
                "source_binding_count": len(contract["source_bindings"]),
                "tool_binding_count": len(contract["tool_bindings"]),
                "public_design_commit": public_design_commit,
                **measurement_contract,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
