#!/usr/bin/env python3
"""Freeze the R182 exact-score cost-attribution design before instrumentation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


METHOD = "b4_b8_r182_score_cost_attribution_protocol_v0"
PROTOCOL_PATH = "results/B4_B8_R182_score_cost_attribution_protocol_v0.json"
CONTRACT_PATH = "benchmarks/B4_B8_R182_score_cost_attribution_contract_v0.json"
REPORT_PATH = "research/B4_B8_R182_score_cost_attribution_protocol.md"
SOURCE_PATHS = [
    "results/B4_B8_R181_active_limb_protocol_v0.json",
    "benchmarks/B4_B8_R181_active_limb_contract_v0.json",
    "results/B4_B8_R181_active_limb_replay_v0.json",
    "results/B4_B8_R181_independent_active_limb_oracle_v0.json",
    "results/B4_B8_R181_active_limb_bundle_manifest_v0.json",
    "research/source_lineage/Qiskit_2_4_1_R180_active_limb_superaccumulator.patch",
    "research/source_lineage/Qiskit_2_4_1_R181_active_limb_linux_x86_64_build_manifest.json",
]
REQUIRED_EXECUTION_ARTIFACTS = [
    "research/source_lineage/Qiskit_2_4_1_R182_score_cost_attribution.patch",
    "tools/b4_b8_r182_score_cost_attribution_replay.py",
    "tools/b4_b8_r182_independent_cost_oracle.py",
    "tools/b4_b8_r182_linux_x86_64_build.py",
    "tools/b4_b8_r182_linux_x86_64_bundle.py",
    ".github/workflows/r182-score-cost-attribution-linux-x86-64.yml",
]


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def source_binding(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise ValueError(f"R182 source binding is missing: {relative}")
    binding: dict[str, Any] = {"path": relative, "sha256": file_sha256(path)}
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        for field in ("payload_hash", "manifest_hash"):
            if field in payload:
                binding[field] = payload[field]
    return binding


def report(protocol: dict[str, Any], contract: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# B4/B8/B10 R182 Exact-Score Cost-Attribution Protocol",
            "",
            "- Status: `preregistered_design_unopened`",
            f"- Protocol payload hash: `{protocol['payload_hash']}`",
            f"- Contract payload hash: `{contract['payload_hash']}`",
            "- Scientific execution: unopened",
            "- Execution tooling: deliberately unbound at this design gate",
            "",
            "## Heuristic Question",
            "",
            protocol["research_question"],
            "",
            "## Frozen Attribution Channels",
            "",
            "R182 separates retained-binary64 leaf construction, destination initialization, arithmetic limb visits, comparison limb visits, carry extension, and BigUint heap activity. The instrumented path must preserve every selected mapping before any cost classification is accepted.",
            "",
            "## Decision Boundary",
            "",
            "The experiment may identify a source-bound cost pressure, reject the proposed attribution, or remain inconclusive. It may not promote a counter correlation into a causal compiler remedy. Execution remains blocked until the patch, runner, oracle, build tool, bundle tool, and public workflow are hash-bound in a second-stage execution contract.",
            "",
            "## Claim Boundary",
            "",
            "This is a preregistered classical compiler cost-attribution design. It is not an upstream Qiskit patch, production remedy, hardware result, quantum advantage, BQP separation, solved B4/B8/B10 frontier, or new credit.",
            "",
        ]
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    for relative in (PROTOCOL_PATH, CONTRACT_PATH, REPORT_PATH):
        if (root / relative).exists():
            raise ValueError(f"R182 output already exists: {relative}")

    r181_result = json.loads(
        (root / SOURCE_PATHS[2]).read_text(encoding="utf-8")
    )
    r181_oracle = json.loads(
        (root / SOURCE_PATHS[3]).read_text(encoding="utf-8")
    )
    r181_bundle = json.loads(
        (root / SOURCE_PATHS[4]).read_text(encoding="utf-8")
    )
    expected_sources = {
        "result": "7a5f055dae4184e01e5c8bb8a18de7b9d09cde8db6b2415b24cb6c1ab9a0b38f",
        "oracle": "a1de6b1b1eb57353bbf3968a2c8232ae6c41d8ee8ca4b398b7992a6b24d9d388",
        "bundle": "34fc5330e263950dfd5ed1401c2a3ea532389014d555ad578d85feb5081e7fcf",
    }
    observed_sources = {
        "result": r181_result.get("payload_hash"),
        "oracle": r181_oracle.get("payload_hash"),
        "bundle": r181_bundle.get("payload_hash"),
    }
    if observed_sources != expected_sources:
        raise ValueError("R182 source R181 payloads do not match the accepted boundary")

    protocol: dict[str, Any] = {
        "title": "B4/B8/B10 R182 exact-score cost-attribution protocol",
        "version": 0,
        "method": METHOD,
        "status": "preregistered_design_unopened",
        "source_target_id": "T-B4-002dq/T-B8-003du/T-B10-009dg-r182-cost-attribution-protocol",
        "upstream_target_id": "T-B4-002dp/T-B8-003dt/T-B10-009df-r181-independent-oracle",
        "research_question": "R181 reduced full-width arithmetic scans but missed both frozen speed gates. Are full-array destination initialization, retained-binary64 construction, comparison work, carry propagation, or BigUint heap behavior the dominant source-bound cost pressures?",
        "source_result_payload_hashes": expected_sources,
        "platform_contract": {
            "runner": "github_hosted_ubuntu_24_04",
            "system": "Linux",
            "machine": "x86_64",
            "python": "3.12",
            "qiskit": "2.4.1",
            "source_commit": "0fd015a22b84c9082173597a5d2304dc0aaec08c",
            "workflow_dispatch_only": True,
            "requires_public_discussion_before_execution": True,
        },
        "frozen_policies": [
            "rust_biguint_exact_retained_binary64",
            "rust_fixed_exact_retained_binary64",
            "rust_active_limb_exact_retained_binary64",
        ],
        "frozen_workload_cells": {
            "standard_dataset_profile_cells": 9,
            "small_gap_policy_cells": 4,
            "total_cells_per_exact_policy": 13,
            "measured_replays_per_cell": 32,
            "warmups_per_cell": 8,
            "exact_policy_measured_call_count": 1248,
            "exact_policy_warmup_call_count": 312,
        },
        "required_cost_channels": [
            "leaf_construction_count",
            "destination_zeroed_limb_count",
            "arithmetic_limb_visit_count",
            "comparison_limb_visit_count",
            "carry_extension_count",
            "maximum_used_limb_count",
            "biguint_heap_allocation_count",
            "biguint_heap_allocated_bytes",
            "elapsed_nanoseconds",
        ],
        "frozen_hypotheses": [
            {
                "hypothesis_id": "H1-full-destination-initialization",
                "statement": "Active-limb arithmetic visits fall materially below fixed-34 while destination zero-initialization remains full-width and the end-to-end speed gain remains below ten percent.",
                "minimum_arithmetic_visit_reduction_fraction": 0.25,
                "maximum_end_to_end_active_to_fixed_ratio_for_speed_success": 0.90,
                "allowed_classification": "full_width_initialization_or_common_cost_pressure_consistent_not_causal",
            },
            {
                "hypothesis_id": "H2-biguint-heap-cost",
                "statement": "BigUint heap activity explains the active-limb loss only if allocation pressure is positive and cell-level allocation pressure covaries with the active-to-BigUint timing gap under the frozen rule.",
                "minimum_spearman_rank_correlation": 0.60,
                "allowed_classification": "biguint_heap_pressure_supported_or_rejected",
            },
            {
                "hypothesis_id": "H3-candidate-shape",
                "statement": "Any cost diagnosis must report results by all 13 workload cells; an aggregate-only explanation is rejected.",
                "required_cell_coverage": 13,
                "allowed_classification": "cell_heterogeneity_reported",
            },
        ],
        "acceptance_requirements": [
            "P1 all R181 source payloads and Qiskit source bindings validate",
            "P2 the public Discussion predates every R182 build and measured worker",
            "P3 the second-stage contract hash-binds the instrumentation patch, build, executor, oracle, bundle tool, and workflow",
            "P4 cargo format, check, tests, release build, ELF validation, and isolated import smoke pass",
            "P5 every instrumented policy preserves the frozen selected mapping for every measured replay",
            "P6 every required counter is present, nonnegative, and internally reconciled",
            "P7 repeated deterministic counter vectors agree within each cell and policy",
            "P8 all 13 workload cells have 32 measurements and 8 warmups per exact policy",
            "P9 the H1, H2, and H3 classifications follow the frozen thresholds without threshold relaxation",
            "P10 an executor-free oracle recomputes hashes, counts, ratios, correlations, and classifications",
            "P11 simulation execution count and quantum shot count remain zero",
            "P12 production remedy, hardware, advantage, BQP, solved-frontier, and new-credit fields remain false or zero",
        ],
        "claim_boundary": {
            "cost_attribution_claimed_before_execution": False,
            "causal_bottleneck_claimed": False,
            "upstream_patch_accepted": False,
            "production_qiskit_remedy_claimed": False,
            "hardware_result_claimed": False,
            "quantum_advantage_claimed": False,
            "bqp_separation_claimed": False,
            "solved_frontier_claimed": False,
            "new_credit_delta": 0,
        },
    }
    protocol["payload_hash"] = canonical_hash(protocol)
    write_json(root / PROTOCOL_PATH, protocol)

    tool_path = Path(__file__).resolve()
    contract: dict[str, Any] = {
        "contract_id": "B4-B8-R182-score-cost-attribution-design-contract-v0",
        "status": "design_frozen_execution_tooling_unbound",
        "execution_started": False,
        "execution_tooling_bound": False,
        "protocol_path": PROTOCOL_PATH,
        "protocol_payload_hash": protocol["payload_hash"],
        "source_bindings": {
            f"source_{index:02d}": source_binding(root, relative)
            for index, relative in enumerate(SOURCE_PATHS, start=1)
        },
        "design_tool_binding": {
            "path": str(tool_path.relative_to(root)),
            "sha256": file_sha256(tool_path),
        },
        "required_before_execution": REQUIRED_EXECUTION_ARTIFACTS,
        "required_before_execution_count": len(REQUIRED_EXECUTION_ARTIFACTS),
        "planned_result_paths": [
            "results/B4_B8_R182_score_cost_attribution_v0.json",
            "results/B4_B8_R182_independent_cost_oracle_v0.json",
            "results/B4_B8_R182_score_cost_attribution_bundle_v0.json",
            "research/B4_B8_R182_score_cost_attribution.md",
            "research/B4_B8_R182_independent_cost_oracle.md",
        ],
    }
    contract["payload_hash"] = canonical_hash(contract)
    write_json(root / CONTRACT_PATH, contract)
    (root / REPORT_PATH).write_text(report(protocol, contract), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": protocol["status"],
                "protocol_payload_hash": protocol["payload_hash"],
                "contract_payload_hash": contract["payload_hash"],
                "required_cost_channel_count": len(
                    protocol["required_cost_channels"]
                ),
                "required_before_execution_count": contract[
                    "required_before_execution_count"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
