#!/usr/bin/env python3
"""Freeze the R183 unused-tail initialization ablation before execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


METHOD = "b4_b8_r183_prefix_initialization_ablation_protocol_v0"
PROTOCOL_PATH = "results/B4_B8_R183_prefix_initialization_ablation_protocol_v0.json"
CONTRACT_PATH = "benchmarks/B4_B8_R183_prefix_initialization_ablation_contract_v0.json"
REPORT_PATH = "research/B4_B8_R183_prefix_initialization_ablation_protocol.md"
SOURCE_PATHS = [
    "results/B4_B8_R182_score_cost_attribution_protocol_v0.json",
    "benchmarks/B4_B8_R182_score_cost_attribution_execution_contract_v0.json",
    "results/B4_B8_R182_score_cost_attribution_v0.json",
    "results/B4_B8_R182_independent_cost_oracle_v0.json",
    "results/B4_B8_R182_score_cost_attribution_bundle_v0.json",
    "research/source_lineage/Qiskit_2_4_1_R182_score_cost_attribution.patch",
    "research/source_lineage/Qiskit_2_4_1_R182_score_cost_linux_x86_64_build_manifest.json",
]
REQUIRED_EXECUTION_ARTIFACTS = [
    "research/source_lineage/Qiskit_2_4_1_R183_prefix_initialization_ablation.patch",
    "tools/b4_b8_r183_prefix_init_replay.py",
    "tools/b4_b8_r183_independent_oracle.py",
    "tools/b4_b8_r183_linux_x86_64_build.py",
    "tools/b4_b8_r183_linux_x86_64_bundle.py",
    ".github/workflows/r183-prefix-initialization-ablation-linux-x86-64.yml",
]
EXPECTED_R182_PAYLOADS = {
    SOURCE_PATHS[2]: "de7cbb2dacf90e2134764f63ae44355f87ecfe9b4416b8d0af7d2ca662a5e10b",
    SOURCE_PATHS[3]: "ab88bd4f3dbb372ab7ff752a7ca86d4f33f5b3409d09407e1523f032c579188f",
    SOURCE_PATHS[4]: "11cfa8d82b291f313d33d84bc35d30bdbd66fb34332cc71297db8d8f7d2e7faf",
}


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


def validate_payload(payload: dict[str, Any], label: str) -> str:
    body = dict(payload)
    observed = body.pop("payload_hash", None)
    if not observed or observed != canonical_hash(body):
        raise ValueError(f"R183 {label} payload hash mismatch")
    return str(observed)


def source_binding(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise ValueError(f"R183 source binding is missing: {relative}")
    output: dict[str, Any] = {"path": relative, "sha256": file_sha256(path)}
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        for field in ("payload_hash", "manifest_hash"):
            if field in payload:
                output[field] = payload[field]
    return output


def report(protocol: dict[str, Any], contract: dict[str, Any]) -> str:
    counts = protocol["frozen_workload"]
    return "\n".join(
        [
            "# B4/B8/B10 R183 Prefix-Initialization Ablation Protocol",
            "",
            "- Status: `preregistered_design_unopened`",
            f"- Protocol payload hash: `{protocol['payload_hash']}`",
            f"- Design contract payload hash: `{contract['payload_hash']}`",
            "- Scientific execution: unopened",
            "",
            "## Heuristic Question",
            "",
            protocol["research_question"],
            "",
            "## Frozen Pairing",
            "",
            f"The design keeps the same `{counts['storage_limb_width']}`-limb score object and the same active-prefix arithmetic, then changes only whether the unused destination suffix is initialized. Each of `{counts['workload_cell_count']}` cells runs `{counts['measured_pairs_per_cell']}` same-process AB/BA pairs with equal order balance.",
            "",
            "## Decision Boundary",
            "",
            "The candidate must preserve every mapping and every non-initialization counter. A material initialization-write reduction with a paired median timing ratio above 0.90 rejects unused-tail initialization as the dominant source-bound explanation. A ratio at or below 0.90 supports contribution under this frozen implementation, not causal completeness or a production remedy.",
            "",
            "## Claim Boundary",
            "",
            "This is a preregistered classical compiler micro-ablation. It is not an upstream Qiskit patch, production remedy, hardware result, quantum advantage, BQP separation, solved B4/B8/B10 frontier, or new credit.",
            "",
        ]
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    for relative in (PROTOCOL_PATH, CONTRACT_PATH, REPORT_PATH):
        if (root / relative).exists():
            raise ValueError(f"R183 output already exists: {relative}")

    for relative, expected in EXPECTED_R182_PAYLOADS.items():
        payload = json.loads((root / relative).read_text(encoding="utf-8"))
        if validate_payload(payload, relative) != expected:
            raise ValueError(f"R183 accepted R182 boundary changed: {relative}")

    protocol: dict[str, Any] = {
        "title": "B4/B8/B10 R183 prefix-initialization micro-ablation protocol",
        "version": 0,
        "method": METHOD,
        "status": "preregistered_design_unopened",
        "source_target_id": "T-B4-002dv/T-B8-003dz/T-B10-009dl-r183-prefix-initialization-ablation",
        "upstream_target_id": "T-B4-002dq/T-B8-003du/T-B10-009dg-r182-cost-attribution",
        "research_question": "R182 cut arithmetic-limb visits by 52.1362% but improved the median end-to-end time by only about 1.25%. Is initializing the unused suffix of the fixed-width exact-score destination the missing dominant cost, or is the remaining time elsewhere in object copies and VF2 control flow?",
        "source_result_payload_hashes": EXPECTED_R182_PAYLOADS,
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
        "frozen_arms": {
            "baseline": "rust_active_limb_exact_full_width_initialized",
            "candidate": "rust_active_limb_exact_prefix_initialized",
        },
        "frozen_workload": {
            "standard_dataset_profile_cells": 9,
            "small_gap_policy_cells": 4,
            "workload_cell_count": 13,
            "worker_count": 13,
            "storage_limb_width": 34,
            "warmups_per_arm_per_cell": 8,
            "measured_pairs_per_cell": 32,
            "ab_pairs_per_cell": 16,
            "ba_pairs_per_cell": 16,
            "measured_pair_count": 416,
            "timing_call_count": 832,
            "counter_probe_call_count": 832,
            "warmup_call_count": 208,
            "total_qiskit_function_call_count": 1872,
        },
        "required_counter_keys": [
            "leaf_construction_count",
            "destination_initialized_limb_count",
            "full_width_destination_count",
            "arithmetic_limb_visit_count",
            "comparison_limb_visit_count",
            "carry_extension_count",
            "maximum_used_limb_count",
        ],
        "non_initialization_counter_keys": [
            "leaf_construction_count",
            "arithmetic_limb_visit_count",
            "comparison_limb_visit_count",
            "carry_extension_count",
            "maximum_used_limb_count",
        ],
        "frozen_hypotheses": [
            {
                "hypothesis_id": "H1-isolated-initialization-write",
                "statement": "The candidate removes full-width destination initialization while preserving storage width, mapping outcomes, and every non-initialization counter.",
                "minimum_initialized_limb_write_reduction_fraction": 0.40,
                "required_candidate_full_width_destination_count": 0,
            },
            {
                "hypothesis_id": "H2-unused-tail-dominance",
                "statement": "Unused-tail initialization is a dominant source-bound cost only if the candidate/baseline paired median elapsed ratio is at most 0.90 after H1 passes.",
                "maximum_candidate_to_baseline_paired_median_ratio": 0.90,
            },
            {
                "hypothesis_id": "H3-workload-heterogeneity",
                "statement": "The result reports all 13 cells and equal AB/BA order counts rather than promoting an aggregate-only timing claim.",
                "required_cell_count": 13,
                "required_ab_pairs_per_cell": 16,
                "required_ba_pairs_per_cell": 16,
            },
        ],
        "acceptance_requirements": [
            "P1 all accepted R182 payloads and source bindings validate",
            "P2 the public Discussion and design commit predate every R183 build and worker",
            "P3 a second-stage execution contract hash-binds the patch, runner, oracle, build, bundle, and workflow",
            "P4 cargo format, check, R180/R182/R183 tests, release build, ELF validation, and isolated import smoke pass",
            "P5 baseline and candidate timing/probe mappings equal the frozen expected mapping for every pair",
            "P6 all seven counters are present, nonnegative, and deterministic by arm and subcell",
            "P7 all five non-initialization counters agree exactly between arms for every pair",
            "P8 all 13 cells contain 32 measured pairs, 16 AB and 16 BA orders, plus 8 warmups per arm",
            "P9 H1, H2, and H3 follow the frozen thresholds without relaxation",
            "P10 a stdlib-only oracle recomputes hashes, counts, paired ratios, and classifications",
            "P11 simulation execution count and quantum shot count remain zero",
            "P12 production remedy, hardware, advantage, BQP, solved-frontier, and new-credit fields remain false or zero",
        ],
        "claim_boundary": {
            "initialization_dominance_claimed_before_execution": False,
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
        "contract_id": "B4-B8-R183-prefix-initialization-design-contract-v0",
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
            "results/B4_B8_R183_prefix_initialization_ablation_v0.json",
            "results/B4_B8_R183_independent_oracle_v0.json",
            "results/B4_B8_R183_prefix_initialization_bundle_v0.json",
            "research/B4_B8_R183_prefix_initialization_ablation.md",
            "research/B4_B8_R183_independent_oracle.md",
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
                "measured_pair_count": protocol["frozen_workload"][
                    "measured_pair_count"
                ],
                "total_qiskit_function_call_count": protocol["frozen_workload"][
                    "total_qiskit_function_call_count"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
