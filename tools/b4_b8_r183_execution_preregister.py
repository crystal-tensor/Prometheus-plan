#!/usr/bin/env python3
"""Bind R183 execution tooling after the public design Discussion exists."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


PROTOCOL_PATH = "results/B4_B8_R183_prefix_initialization_ablation_protocol_v0.json"
DESIGN_CONTRACT_PATH = (
    "benchmarks/B4_B8_R183_prefix_initialization_ablation_contract_v0.json"
)
R181_PROTOCOL_PATH = "results/B4_B8_R181_active_limb_protocol_v0.json"
OUTPUT_PATH = "benchmarks/B4_B8_R183_prefix_initialization_execution_contract_v0.json"
REPORT_PATH = "research/B4_B8_R183_prefix_initialization_execution_contract.md"
TOOL_PATHS = [
    "research/source_lineage/Qiskit_2_4_1_R183_prefix_initialization_ablation.patch",
    "tools/b4_b8_r183_prefix_init_replay.py",
    "tools/b4_b8_r183_independent_oracle.py",
    "tools/b4_b8_r183_linux_x86_64_build.py",
    "tools/b4_b8_r183_linux_x86_64_bundle.py",
    ".github/workflows/r183-prefix-initialization-ablation-linux-x86-64.yml",
]
DIRECT_SOURCE_PATHS = [
    PROTOCOL_PATH,
    DESIGN_CONTRACT_PATH,
    R181_PROTOCOL_PATH,
    "results/B4_B8_R182_score_cost_attribution_v0.json",
    "results/B4_B8_R182_independent_cost_oracle_v0.json",
    "results/B4_B8_R182_score_cost_attribution_bundle_v0.json",
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
    "destination_initialized_limb_count": "Number of destination u64 limbs explicitly initialized by leaf construction, identity, and combine.",
    "full_width_destination_count": "Number of score destinations whose constructor or combine initializes all 34 limbs.",
    "arithmetic_limb_visit_count": "Active numerical limbs visited by score addition.",
    "comparison_limb_visit_count": "Active numerical limbs inspected before score comparison resolves.",
    "carry_extension_count": "Number of additions whose result uses more limbs than both operands.",
    "maximum_used_limb_count": "Maximum numerical limb length observed during the probe.",
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
        raise ValueError(f"R183 {label} payload hash mismatch")
    return str(observed)


def binding(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise ValueError(f"R183 execution binding is missing: {relative}")
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
    counts = contract["measurement_pair_contract"]
    return "\n".join(
        [
            "# B4/B8/B10 R183 Execution Contract",
            "",
            "- Status: `execution_tooling_bound_unopened`",
            f"- Contract payload hash: `{contract['payload_hash']}`",
            f"- Tool bindings: `{len(contract['tool_bindings'])}`",
            f"- Source bindings: `{len(contract['source_bindings'])}`",
            f"- Public design commit: `{contract['public_preregistration']['public_design_commit']}`",
            f"- Public Discussion: {contract['public_preregistration']['discussion']}",
            "- Scientific execution: unopened",
            "",
            "## Same-Process Pairing",
            "",
            f"The frozen matrix contains `{counts['measured_pair_count']}` AB/BA pairs in `{counts['expected_worker_count']}` isolated workers. Every pair runs two uninstrumented timing calls and two separate probes; probe time is excluded. Equal `{counts['ab_pairs_per_cell']}`/`{counts['ba_pairs_per_cell']}` order counts are required in every cell.",
            "",
            "## Isolation Boundary",
            "",
            "Both arms retain the same 34-limb object width and active-prefix arithmetic. The candidate changes only destination initialization of the unused suffix through a MaybeUninit representation whose initialized-prefix invariant is covered by the frozen Rust test gate.",
            "",
            "## Claim Boundary",
            "",
            "The patch, runner, oracle, build, bundle, and public workflow are hash-bound. This contract is not a timing result, causal diagnosis, upstream Qiskit remedy, hardware result, quantum advantage, BQP separation, solved frontier, or new credit.",
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
    args = parser.parse_args()
    root = args.root.resolve()
    for relative in (OUTPUT_PATH, REPORT_PATH):
        if (root / relative).exists():
            raise ValueError(f"R183 execution output already exists: {relative}")
    if not args.discussion.startswith(
        "https://github.com/crystal-tensor/Prometheus-plan/discussions/"
    ):
        raise ValueError("R183 public Discussion URL is outside the project repository")
    created = datetime.fromisoformat(args.created_at.replace("Z", "+00:00"))
    if created.timestamp() >= time.time():
        raise ValueError("R183 public Discussion timestamp is not in the past")

    protocol = json.loads((root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    design = json.loads((root / DESIGN_CONTRACT_PATH).read_text(encoding="utf-8"))
    r181 = json.loads((root / R181_PROTOCOL_PATH).read_text(encoding="utf-8"))
    protocol_hash = validate_payload(protocol, "protocol")
    design_hash = validate_payload(design, "design contract")
    if design.get("protocol_payload_hash") != protocol_hash:
        raise ValueError("R183 design protocol binding mismatch")
    if set(design["required_before_execution"]) != set(TOOL_PATHS):
        raise ValueError("R183 design and execution tool lists differ")
    public_design_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=root, text=True
    ).strip():
        raise ValueError(
            "R183 execution contract must be generated from the clean public design commit"
        )

    workload_cells = cells(r181)
    counts = protocol["frozen_workload"]
    measurement_contract = {
        "arm_order_rule": "AB_on_even_pair_BA_on_odd_pair",
        "probe_order_matches_timing_order": True,
        "probe_elapsed_excluded_from_timing": True,
        "mapping_equality_required_within_and_across_arms": True,
        "non_initialization_counter_equality_required": True,
        "workload_cell_count": counts["workload_cell_count"],
        "expected_worker_count": counts["worker_count"],
        "measured_pairs_per_cell": counts["measured_pairs_per_cell"],
        "ab_pairs_per_cell": counts["ab_pairs_per_cell"],
        "ba_pairs_per_cell": counts["ba_pairs_per_cell"],
        "warmups_per_arm_per_cell": counts["warmups_per_arm_per_cell"],
        "measured_pair_count": counts["measured_pair_count"],
        "timing_call_count": counts["timing_call_count"],
        "counter_probe_call_count": counts["counter_probe_call_count"],
        "warmup_call_count": counts["warmup_call_count"],
        "total_qiskit_function_call_count": counts["total_qiskit_function_call_count"],
        "small_gap_case_schedule": "pair_index_modulo_seven_in_frozen_R181_case_order",
        "counter_determinism_group": "cell_id_arm_subcell_id",
    }
    contract: dict[str, Any] = {
        "title": "B4/B8/B10 R183 prefix-initialization execution contract",
        "version": 0,
        "contract_id": "B4-B8-R183-prefix-initialization-execution-contract-v0",
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
        "measurement_pair_contract": measurement_contract,
        "counter_definitions": COUNTER_DEFINITIONS,
        "aggregation_rules": {
            "H1_initialized_limb_write_reduction": "1_minus_candidate_total_over_baseline_total",
            "H1_non_initialization_equality": "pairwise_exact_equality_for_five_declared_counters",
            "H2_timing_ratio": "median_of_candidate_elapsed_over_baseline_elapsed_across_all_pairs",
            "H2_speed_success": "paired_median_ratio_at_most_0.90_after_H1_passes",
            "H3_coverage": "all_13_cells_with_16_AB_and_16_BA_pairs_each",
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
            root, "tools/b4_b8_r183_execution_preregister.py"
        ),
        "result_paths_must_be_absent": [
            "research/B4_B8_R183_prefix_initialization_ablation.md",
            "research/B4_B8_R183_independent_oracle.md",
            "results/B4_B8_R183_prefix_initialization_replay",
            "results/B4_B8_R183_prefix_initialization_ablation_v0.json",
            "results/B4_B8_R183_independent_oracle_v0.json",
            "results/B4_B8_R183_prefix_initialization_bundle_v0.json",
        ],
        "build_output_paths_created_before_replay": [
            "research/source_lineage/Qiskit_2_4_1_R183_prefix_init_pyext.x86_64-linux-gnu.so",
            "research/source_lineage/Qiskit_2_4_1_R183_prefix_init_linux_x86_64_build_manifest.json",
            "research/source_lineage/R183_prefix_init_linux_x86_64_build_logs",
        ],
        "claim_boundary": protocol["claim_boundary"],
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
