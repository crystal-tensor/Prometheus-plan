#!/usr/bin/env python3
"""Freeze the R184 windowed exact-score experiment before execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


METHOD = "b4_b8_r184_window_exact_score_protocol_v0"
PROTOCOL_PATH = "results/B4_B8_R184_window_exact_score_protocol_v0.json"
CONTRACT_PATH = "benchmarks/B4_B8_R184_window_exact_score_contract_v0.json"
REPORT_PATH = "research/B4_B8_R184_window_exact_score_protocol.md"
SOURCE_PATHS = [
    "results/B4_B8_R183_prefix_initialization_ablation_protocol_v0.json",
    "benchmarks/B4_B8_R183_prefix_initialization_execution_contract_v0.json",
    "results/B4_B8_R183_prefix_initialization_ablation_v0.json",
    "results/B4_B8_R183_independent_oracle_v0.json",
    "results/B4_B8_R183_prefix_initialization_bundle_v0.json",
    "research/source_lineage/Qiskit_2_4_1_R183_prefix_initialization_ablation.patch",
    "research/source_lineage/Qiskit_2_4_1_R183_prefix_init_linux_x86_64_build_manifest.json",
]
REQUIRED_EXECUTION_ARTIFACTS = [
    "research/source_lineage/Qiskit_2_4_1_R184_window_exact_score.patch",
    "tools/b4_b8_r184_window_exact_replay.py",
    "tools/b4_b8_r184_independent_oracle.py",
    "tools/b4_b8_r184_linux_x86_64_build.py",
    "tools/b4_b8_r184_linux_x86_64_bundle.py",
    ".github/workflows/r184-windowed-exact-score-linux-x86-64.yml",
]
EXPECTED_R183_PAYLOADS = {
    SOURCE_PATHS[2]: "ecb901a7375013fdd8f58727227fe7e80d38c89570d646011790ddfa29bd0c84",
    SOURCE_PATHS[3]: "4b1a6d2a43e7011a96567ffe2839dadca04e02a84e29ff090ecc37f24c598360",
    SOURCE_PATHS[4]: "8a4b23726c8733248e039b90a776b040aab14976f229ddec145a0ddd4bb91f4d",
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
        raise ValueError(f"R184 {label} payload hash mismatch")
    return str(observed)


def source_binding(root: Path, relative: str) -> dict[str, Any]:
    path = root / relative
    if not path.is_file():
        raise ValueError(f"R184 source binding is missing: {relative}")
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
            "# B4/B8/B10 R184 Windowed Exact-Score Protocol",
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
            "## Frozen Three-Arm Pairing",
            "",
            f"The matrix contains `{counts['measured_triplet_count']}` same-process BigUint/prefix/window triplets: each of `{counts['workload_cell_count']}` cells runs `{counts['measured_triplets_per_cell']}` triplets. All six arm orders appear `{counts['repetitions_per_order_per_cell']}` times per cell, so scheduler position is balanced before any timing is observed.",
            "",
            "## Decision Boundary",
            "",
            "The window must preserve every expected mapping, stay at four compact limbs or fewer, remain at 64 bytes or fewer, and avoid fallback on the frozen workload. A median window/prefix ratio at or below 0.90 supports a representation-level speed gain; a median window/BigUint ratio at or below 1.00 establishes competitiveness with the exact dynamic denominator.",
            "",
            "## Claim Boundary",
            "",
            "This is a preregistered classical compiler representation experiment. It is not an upstream Qiskit patch, a full-domain performance theorem, production remedy, hardware result, quantum advantage, BQP separation, solved B4/B8/B10 frontier, or new credit.",
            "",
        ]
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    for relative in (PROTOCOL_PATH, CONTRACT_PATH, REPORT_PATH):
        if (root / relative).exists():
            raise ValueError(f"R184 output already exists: {relative}")

    for relative, expected in EXPECTED_R183_PAYLOADS.items():
        payload = json.loads((root / relative).read_text(encoding="utf-8"))
        if validate_payload(payload, relative) != expected:
            raise ValueError(f"R184 accepted R183 boundary changed: {relative}")

    protocol: dict[str, Any] = {
        "title": "B4/B8/B10 R184 windowed exact-score protocol",
        "version": 0,
        "method": METHOD,
        "status": "preregistered_design_unopened",
        "source_target_id": "T-B4-002dy/T-B8-003ec/T-B10-009do-r184-windowed-exact-score-protocol",
        "upstream_target_id": "T-B4-002dw/T-B8-003ea/T-B10-009dm-r183-result",
        "research_question": "R183 removed 62.6724% of initialized limb writes yet reached only a 0.984288x paired median ratio. Can an exact score become materially faster by carrying only a four-limb exponent window, while falling back losslessly to BigUint whenever the exact span is wider?",
        "source_result_payload_hashes": EXPECTED_R183_PAYLOADS,
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
            "baseline": "rust_biguint_exact_retained_binary64",
            "reference": "rust_prefix_initialized_34_limb_exact",
            "candidate": "rust_windowed_4_limb_exact_with_biguint_fallback",
        },
        "frozen_workload": {
            "standard_dataset_profile_cells": 9,
            "small_gap_policy_cells": 4,
            "workload_cell_count": 13,
            "worker_count": 13,
            "candidate_compact_limb_capacity": 4,
            "candidate_maximum_object_size_bytes": 64,
            "arm_order_permutation_count": 6,
            "repetitions_per_order_per_cell": 6,
            "warmups_per_arm_per_cell": 9,
            "measured_triplets_per_cell": 36,
            "measured_triplet_count": 468,
            "timing_call_count": 1404,
            "counter_probe_call_count": 468,
            "warmup_call_count": 351,
            "total_qiskit_function_call_count": 2223,
        },
        "required_counter_keys": [
            "leaf_construction_count",
            "window_combine_count",
            "window_compare_count",
            "compact_result_count",
            "fallback_transition_count",
            "wide_combine_count",
            "maximum_window_limb_count",
            "score_object_size_bytes",
        ],
        "frozen_hypotheses": [
            {
                "hypothesis_id": "H1-exact-integrity",
                "statement": "BigUint, prefix, window timing, and window probe mappings equal the frozen expected mapping in every triplet.",
            },
            {
                "hypothesis_id": "H2-compact-common-path",
                "statement": "The window representation stays within four limbs and 64 bytes, with zero fallback transitions and zero wide combines on the frozen workload.",
                "maximum_window_limb_count": 4,
                "maximum_score_object_size_bytes": 64,
            },
            {
                "hypothesis_id": "H3-representation-speedup",
                "statement": "The window candidate has an aggregate paired median elapsed ratio at most 0.90 against the prefix-initialized exact reference after H1 and H2 pass.",
                "maximum_candidate_to_reference_paired_median_ratio": 0.90,
            },
            {
                "hypothesis_id": "H4-biguint-competitiveness",
                "statement": "The window candidate has an aggregate paired median elapsed ratio at most 1.00 against the BigUint exact denominator after H1 and H2 pass.",
                "maximum_candidate_to_baseline_paired_median_ratio": 1.00,
                "required_cell_count": 13,
                "required_count_per_order_per_cell": 6,
            },
        ],
        "acceptance_requirements": [
            "P1 all accepted R183 payloads and source bindings validate",
            "P2 the public Discussion and design commit predate every R184 build and worker",
            "P3 a second-stage execution contract hash-binds the patch, runner, oracle, build, bundle, and workflow",
            "P4 cargo format, check, R180/R182/R183/R184 tests, release build, ELF validation, and isolated import smoke pass",
            "P5 all three timing mappings and the candidate probe mapping equal the expected mapping for every triplet",
            "P6 all eight candidate counters are present, nonnegative, and deterministic by subcell",
            "P7 candidate compactness, fallback, and object-size fields follow H2 without relaxation",
            "P8 all 13 cells contain 36 triplets, six of every arm order, plus 9 warmups per arm",
            "P9 H1 through H4 follow the frozen thresholds without relaxation",
            "P10 a stdlib-only oracle recomputes hashes, counts, paired ratios, and classifications",
            "P11 simulation execution count and quantum shot count remain zero",
            "P12 production remedy, hardware, advantage, BQP, solved-frontier, and new-credit fields remain false or zero",
        ],
        "claim_boundary": {
            "representation_speedup_claimed_before_execution": False,
            "full_domain_compactness_claimed": False,
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
        "contract_id": "B4-B8-R184-windowed-exact-score-design-contract-v0",
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
            "results/B4_B8_R184_window_exact_score_v0.json",
            "results/B4_B8_R184_independent_oracle_v0.json",
            "results/B4_B8_R184_window_exact_score_bundle_v0.json",
            "research/B4_B8_R184_window_exact_score.md",
            "research/B4_B8_R184_independent_oracle.md",
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
                "measured_triplet_count": protocol["frozen_workload"][
                    "measured_triplet_count"
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
