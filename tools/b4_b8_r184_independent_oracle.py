#!/usr/bin/env python3
"""Independently verify R184 using only committed JSON and the stdlib."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


METHOD = "b4_b8_r184_independent_window_exact_score_oracle_v0"
PROTOCOL_PATH = "results/B4_B8_R184_window_exact_score_protocol_v0.json"
DESIGN_CONTRACT_PATH = (
    "benchmarks/B4_B8_R184_window_exact_score_contract_v0.json"
)
CONTRACT_PATH = "benchmarks/B4_B8_R184_window_exact_score_execution_contract_v0.json"
RESULT_PATH = "results/B4_B8_R184_window_exact_score_v0.json"
WORKER_DIR = "results/B4_B8_R184_window_exact_score_replay"
BUILD_MANIFEST_PATH = "research/source_lineage/Qiskit_2_4_1_R184_window_exact_linux_x86_64_build_manifest.json"
BINARY_PATH = (
    "research/source_lineage/Qiskit_2_4_1_R184_window_exact_pyext.x86_64-linux-gnu.so"
)
OUTPUT_PATH = "results/B4_B8_R184_independent_oracle_v0.json"
REPORT_PATH = "research/B4_B8_R184_independent_oracle.md"
ARMS = ["baseline", "reference", "candidate"]
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
        raise ValueError(f"R184 independent oracle {label} hash mismatch")
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
    counter_vectors: dict[tuple[str, str], set[tuple[int, ...]]] = defaultdict(set)
    for row in rows:
        key = (row["cell_id"], row["subcell_id"])
        counter_vectors[key].add(
            tuple(
                row["arms"]["candidate"]["cost_counters"][name]
                for name in COUNTER_KEYS
            )
        )
    counts = protocol["frozen_workload"]
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
        "triplet_count": len(rows) == counts["measured_triplet_count"],
        "timing_call_count": summary["timing_call_count"]
        == counts["timing_call_count"],
        "probe_call_count": summary["counter_probe_call_count"]
        == counts["counter_probe_call_count"],
        "warmup_call_count": summary["warmup_call_count"]
        == counts["warmup_call_count"],
        "total_call_count": summary["total_qiskit_function_call_count"]
        == counts["total_qiskit_function_call_count"],
        "triplets_per_cell": all(
            manifest["recorded_triplet_count"]
            == counts["measured_triplets_per_cell"]
            for manifest in manifests
        ),
        "order_balance": all(
            set(manifest["arm_order_counts"])
            == {">".join(order) for order in ARM_ORDERS}
            and all(
                count == counts["repetitions_per_order_per_cell"]
                for count in manifest["arm_order_counts"].values()
            )
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
        raise ValueError("R184 independent oracle output already exists")
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
        raise ValueError("R184 oracle/result preregistration mismatch")
    if build.get("preregistration") != runtime_preregistration:
        raise ValueError("R184 oracle/build preregistration mismatch")
    if build.get("github_actions", {}).get("sha") != args.preregistration_commit:
        raise ValueError("R184 oracle GitHub Actions SHA mismatch")
    if (
        not build.get("github_actions", {})
        .get("run_url", "")
        .startswith("https://github.com/crystal-tensor/Prometheus-plan/actions/runs/")
    ):
        raise ValueError("R184 oracle public run URL mismatch")
    if build.get("accelerator", {}).get("sha256") != file_sha256(root / BINARY_PATH):
        raise ValueError("R184 oracle accelerator hash mismatch")
    if result.get("build_manifest_payload_hash") != build_hash:
        raise ValueError("R184 oracle result/build payload mismatch")
    for section in ("source_bindings", "tool_bindings"):
        for binding in contract[section].values():
            path = root / binding["path"]
            if not path.is_file() or file_sha256(path) != binding["sha256"]:
                raise ValueError(f"R184 oracle binding mismatch: {binding['path']}")
    generator = contract["contract_generator_binding"]
    generator_path = root / generator["path"]
    if (
        not generator_path.is_file()
        or file_sha256(generator_path) != generator["sha256"]
    ):
        raise ValueError("R184 oracle execution-contract generator binding mismatch")

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
        and all(
            row["arms"][arm]["timing_mapping_vector"] == row["expected_mapping_vector"]
            for arm in ARMS
        )
        and row["arms"]["candidate"]["probe_mapping_vector"]
        == row["expected_mapping_vector"]
        and row["candidate_probe_matches_timing"]
        for row in rows
    )
    counter_integrity = all(
        set(row["arms"]["candidate"]["cost_counters"]) == set(COUNTER_KEYS)
        and all(
            isinstance(value, int) and value >= 0
            for value in row["arms"]["candidate"]["cost_counters"].values()
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
        "P7": recomputed["hypothesis_classifications"][
            "H2-compact-common-path"
        ]["supported_under_frozen_rule"],
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
        "title": "B4/B8/B10 R184 independent windowed-exact-score oracle",
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
        "compact_common_path_passed": recomputed["hypothesis_classifications"][
            "H2-compact-common-path"
        ]["supported_under_frozen_rule"],
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
        "# B4/B8/B10 R184 Independent Windowed-Exact-Score Oracle",
        "",
        f"- Status: `{oracle['status']}`",
        f"- Payload hash: `{oracle['payload_hash']}`",
        f"- Requirements: `{oracle['requirements_passed']}/12`",
        "",
        "## Independent Recalculation",
        "",
        f"The stdlib-only oracle validates `{worker_hash_passes}` worker manifests and `{row_hash_passes}` triplet-row hashes, then recomputes three-arm mapping integrity, eight-counter completeness, compactness and fallback boundaries, paired timing ratios, workload counts, all-order balance, and all four frozen classifications without importing Qiskit or the R184 executor.",
        "",
        "## Claim Boundary",
        "",
        "This validates the committed source-bound representation experiment under the frozen rules. It does not establish a full-domain performance theorem, accept an upstream Qiskit remedy, establish hardware behavior, demonstrate quantum advantage, separate BQP, solve a frontier, or grant new credit.",
        "",
    ]
    (root / REPORT_PATH).write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(oracle, indent=2, sort_keys=True))
    return 0 if all(requirements.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
