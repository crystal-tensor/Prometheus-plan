#!/usr/bin/env python3
"""Independently verify R183 using only committed JSON and the stdlib."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


METHOD = "b4_b8_r183_independent_prefix_initialization_oracle_v0"
PROTOCOL_PATH = "results/B4_B8_R183_prefix_initialization_ablation_protocol_v0.json"
DESIGN_CONTRACT_PATH = (
    "benchmarks/B4_B8_R183_prefix_initialization_ablation_contract_v0.json"
)
CONTRACT_PATH = "benchmarks/B4_B8_R183_prefix_initialization_execution_contract_v0.json"
RESULT_PATH = "results/B4_B8_R183_prefix_initialization_ablation_v0.json"
WORKER_DIR = "results/B4_B8_R183_prefix_initialization_replay"
BUILD_MANIFEST_PATH = "research/source_lineage/Qiskit_2_4_1_R183_prefix_init_linux_x86_64_build_manifest.json"
BINARY_PATH = (
    "research/source_lineage/Qiskit_2_4_1_R183_prefix_init_pyext.x86_64-linux-gnu.so"
)
OUTPUT_PATH = "results/B4_B8_R183_independent_oracle_v0.json"
REPORT_PATH = "research/B4_B8_R183_independent_oracle.md"
ARMS = ["baseline", "candidate"]
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


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_hash_field(payload: dict[str, Any], field: str, label: str) -> str:
    body = dict(payload)
    observed = body.pop(field, None)
    if not observed or observed != canonical_hash(body):
        raise ValueError(f"R183 independent oracle {label} hash mismatch")
    return str(observed)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def recompute(
    protocol: dict[str, Any],
    manifests: list[dict[str, Any]],
) -> dict[str, Any]:
    rows = [row for manifest in manifests for row in manifest["replay_rows"]]
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
        all(
            row["arms"]["baseline"]["cost_counters"][key]
            == row["arms"]["candidate"]["cost_counters"][key]
            for key in NON_INITIALIZATION_COUNTER_KEYS
        )
        and row["non_initialization_counters_equal"]
        for row in rows
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
            "classification": (
                "isolated_initialization_write_reduction_passed"
                if h1_supported
                else "isolation_gate_failed"
            ),
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
            "classification": (
                "all_cells_and_orders_reported"
                if h3_supported
                else "coverage_or_order_balance_failed"
            ),
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
    counter_vectors: dict[tuple[str, str, str], set[tuple[int, ...]]] = defaultdict(set)
    for row in rows:
        for arm in ARMS:
            key = (row["cell_id"], row["subcell_id"], arm)
            counter_vectors[key].add(
                tuple(row["arms"][arm]["cost_counters"][name] for name in COUNTER_KEYS)
            )
    counts = protocol["frozen_workload"]
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
        "counter_determinism_pass_count": sum(
            len(values) == 1 for values in counter_vectors.values()
        ),
        "requirements_passed": 11,
        "requirements_failed": 1,
        "pending_requirement": "P10 independent oracle",
        "simulation_execution_count": 0,
        "total_simulated_shots": 0,
    }
    count_checks = {
        "worker_count": len(manifests) == counts["worker_count"],
        "pair_count": len(rows) == counts["measured_pair_count"],
        "timing_call_count": summary["timing_call_count"]
        == counts["timing_call_count"],
        "probe_call_count": summary["counter_probe_call_count"]
        == counts["counter_probe_call_count"],
        "warmup_call_count": summary["warmup_call_count"]
        == counts["warmup_call_count"],
        "total_call_count": summary["total_qiskit_function_call_count"]
        == counts["total_qiskit_function_call_count"],
        "order_balance": all(
            manifest["ab_pair_count"] == counts["ab_pairs_per_cell"]
            and manifest["ba_pair_count"] == counts["ba_pairs_per_cell"]
            for manifest in manifests
        ),
    }
    return {
        "rows": rows,
        "cell_summaries": cell_summaries,
        "hypothesis_classifications": classifications,
        "summary": summary,
        "count_checks": count_checks,
        "counter_vectors": counter_vectors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--preregistration-commit", required=True)
    parser.add_argument("--preregistration-discussion", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if (root / OUTPUT_PATH).exists() or (root / REPORT_PATH).exists():
        raise ValueError("R183 independent oracle output already exists")
    protocol = json.loads((root / PROTOCOL_PATH).read_text(encoding="utf-8"))
    design = json.loads((root / DESIGN_CONTRACT_PATH).read_text(encoding="utf-8"))
    contract = json.loads((root / CONTRACT_PATH).read_text(encoding="utf-8"))
    result = json.loads((root / RESULT_PATH).read_text(encoding="utf-8"))
    build = json.loads((root / BUILD_MANIFEST_PATH).read_text(encoding="utf-8"))
    protocol_hash = validate_hash_field(protocol, "payload_hash", "protocol")
    design_hash = validate_hash_field(design, "payload_hash", "design contract")
    contract_hash = validate_hash_field(contract, "payload_hash", "execution contract")
    result_hash = validate_hash_field(result, "payload_hash", "result")
    build_hash = validate_hash_field(build, "payload_hash", "build manifest")
    runtime_preregistration = {
        "commit": args.preregistration_commit,
        "discussion": args.preregistration_discussion,
        "created_at": contract["public_preregistration"]["created_at"],
    }
    if runtime_preregistration != result.get("preregistration"):
        raise ValueError("R183 oracle/result preregistration mismatch")
    if build.get("preregistration") != runtime_preregistration:
        raise ValueError("R183 oracle/build preregistration mismatch")
    if build.get("github_actions", {}).get("sha") != args.preregistration_commit:
        raise ValueError("R183 oracle GitHub Actions SHA mismatch")
    if (
        not build.get("github_actions", {})
        .get("run_url", "")
        .startswith("https://github.com/crystal-tensor/Prometheus-plan/actions/runs/")
    ):
        raise ValueError("R183 oracle public run URL mismatch")
    if build.get("accelerator", {}).get("sha256") != file_sha256(root / BINARY_PATH):
        raise ValueError("R183 oracle accelerator hash mismatch")
    if result.get("build_manifest_payload_hash") != build_hash:
        raise ValueError("R183 oracle result/build payload mismatch")
    for section in ("source_bindings", "tool_bindings"):
        for binding in contract[section].values():
            path = root / binding["path"]
            if not path.is_file() or file_sha256(path) != binding["sha256"]:
                raise ValueError(f"R183 oracle binding mismatch: {binding['path']}")
    generator = contract["contract_generator_binding"]
    generator_path = root / generator["path"]
    if (
        not generator_path.is_file()
        or file_sha256(generator_path) != generator["sha256"]
    ):
        raise ValueError("R183 oracle execution-contract generator binding mismatch")

    manifests = []
    worker_artifacts = []
    worker_hash_passes = 0
    row_hash_passes = 0
    for path in sorted((root / WORKER_DIR).glob("*.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        validate_hash_field(manifest, "manifest_hash", f"worker {path.name}")
        worker_hash_passes += 1
        for row in manifest["replay_rows"]:
            validate_hash_field(row, "row_hash", f"row {path.name}")
            row_hash_passes += 1
        manifests.append(manifest)
        worker_artifacts.append(
            {
                "path": str(path.relative_to(root)),
                "sha256": file_sha256(path),
                "manifest_hash": manifest["manifest_hash"],
            }
        )
    recomputed = recompute(protocol, manifests)
    rows = recomputed["rows"]
    mapping_integrity = all(
        row["cross_arm_timing_mapping_match"]
        and row["cross_arm_probe_mapping_match"]
        and all(
            row["arms"][arm]["timing_mapping_vector"] == row["expected_mapping_vector"]
            and row["arms"][arm]["probe_mapping_vector"]
            == row["expected_mapping_vector"]
            for arm in ARMS
        )
        for row in rows
    )
    counter_integrity = all(
        set(row["arms"][arm]["cost_counters"]) == set(COUNTER_KEYS)
        and all(
            isinstance(value, int) and value >= 0
            for value in row["arms"][arm]["cost_counters"].values()
        )
        for row in rows
        for arm in ARMS
    )
    non_initialization_equality = all(
        all(
            row["arms"]["baseline"]["cost_counters"][key]
            == row["arms"]["candidate"]["cost_counters"][key]
            for key in NON_INITIALIZATION_COUNTER_KEYS
        )
        for row in rows
    )
    result_matches = {
        "protocol_hash": result["protocol_payload_hash"] == protocol_hash,
        "design_hash": result["design_contract_payload_hash"] == design_hash,
        "contract_hash": result["contract_payload_hash"] == contract_hash,
        "cell_summaries": result["cell_summaries"] == recomputed["cell_summaries"],
        "classifications": result["hypothesis_classifications"]
        == recomputed["hypothesis_classifications"],
        "summary": result["summary"] == recomputed["summary"],
        "worker_artifacts": result["worker_artifacts"] == worker_artifacts,
        "preregistration": result["preregistration"] == runtime_preregistration,
        "build_manifest": result["build_manifest_payload_hash"] == build_hash,
        "claim_boundary": all(
            result[field] is False
            for field in (
                "hardware_result_claimed",
                "quantum_advantage_claimed",
                "bqp_separation_claimed",
                "solved_frontier_claimed",
                "production_qiskit_remedy_claimed",
                "causal_bottleneck_claimed",
            )
        )
        and result["new_credit_delta"] == 0,
    }
    requirements = {
        "P1": protocol_hash == contract["protocol_payload_hash"]
        and design_hash == contract["design_contract_payload_hash"],
        "P2": all(
            manifest["preregistration"] == runtime_preregistration
            for manifest in manifests
        ),
        "P3": contract.get("execution_tooling_bound") is True,
        "P4": result_matches["build_manifest"],
        "P5": mapping_integrity,
        "P6": counter_integrity
        and recomputed["summary"]["counter_determinism_group_count"]
        == recomputed["summary"]["counter_determinism_pass_count"],
        "P7": non_initialization_equality,
        "P8": all(recomputed["count_checks"].values()),
        "P9": all(result_matches.values()),
        "P10": True,
        "P11": all(
            row["simulation_execution_count"] == 0 and row["total_simulated_shots"] == 0
            for row in rows
        ),
        "P12": result_matches["claim_boundary"],
    }
    oracle = {
        "title": "B4/B8/B10 R183 independent prefix-initialization oracle",
        "version": 0,
        "method": METHOD,
        "status": (
            "independent_oracle_complete"
            if all(requirements.values())
            else "independent_oracle_rejected"
        ),
        "source_result_path": RESULT_PATH,
        "source_result_payload_hash": result_hash,
        "protocol_payload_hash": protocol_hash,
        "design_contract_payload_hash": design_hash,
        "contract_payload_hash": contract_hash,
        "worker_manifest_hash_pass_count": worker_hash_passes,
        "row_hash_pass_count": row_hash_passes,
        "mapping_integrity_passed": mapping_integrity,
        "counter_integrity_passed": counter_integrity,
        "non_initialization_counter_equality_passed": non_initialization_equality,
        "count_checks": recomputed["count_checks"],
        "result_matches": result_matches,
        "recomputed_summary": recomputed["summary"],
        "recomputed_hypothesis_classifications": recomputed[
            "hypothesis_classifications"
        ],
        "requirements": requirements,
        "requirements_passed": sum(requirements.values()),
        "requirements_failed": sum(not value for value in requirements.values()),
        "simulation_execution_count": 0,
        "total_simulated_shots": 0,
        "hardware_result_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "solved_frontier_claimed": False,
        "production_qiskit_remedy_claimed": False,
        "causal_bottleneck_claimed": False,
        "new_credit_delta": 0,
    }
    oracle["payload_hash"] = canonical_hash(oracle)
    write_json(root / OUTPUT_PATH, oracle)
    lines = [
        "# B4/B8/B10 R183 Independent Prefix-Initialization Oracle",
        "",
        f"- Status: `{oracle['status']}`",
        f"- Payload hash: `{oracle['payload_hash']}`",
        f"- Requirements: `{oracle['requirements_passed']}/12`",
        "",
        "## Independent Recalculation",
        "",
        f"The stdlib-only oracle validates `{worker_hash_passes}` worker manifests and `{row_hash_passes}` paired-row hashes, then recomputes mapping integrity, seven-counter completeness, five-counter cross-arm equality, initialized-write reduction, paired timing ratios, workload counts, and all three frozen classifications without importing Qiskit or the R183 executor.",
        "",
        "## Claim Boundary",
        "",
        "This validates the committed source-bound micro-ablation under the frozen rules. It does not establish complete causality, accept an upstream Qiskit remedy, establish hardware behavior, demonstrate quantum advantage, separate BQP, solve a frontier, or grant new credit.",
        "",
    ]
    (root / REPORT_PATH).write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(oracle, indent=2, sort_keys=True))
    return 0 if all(requirements.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
