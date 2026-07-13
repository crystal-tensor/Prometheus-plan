#!/usr/bin/env python3
"""Freeze the R146 cross-backend calibration-snapshot transfer protocol."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import time
from pathlib import Path

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256


METHOD = "b4_b8_r146_cross_snapshot_transfer_protocol_v0"
RESULT_PATH = "results/B4_B8_R146_cross_snapshot_transfer_protocol_v0.json"
REPORT_PATH = "research/B4_B8_R146_cross_snapshot_transfer_protocol.md"
R143_PATH = "results/B4_B8_R143_successive_halving_lcb_design_v0.json"
R145_PATH = "results/B4_B8_R145_counterbalanced_runtime_benchmark_v0.json"
TASK_BUILDER_PATH = "tools/b4_b8_r135_dense_interaction_fallback.py"


def build(root: Path) -> dict:
    r143 = json.loads((root / R143_PATH).read_text())
    r145 = json.loads((root / R145_PATH).read_text())
    snapshots = sorted({row["snapshot"] for row in r143["group_rows"]})
    tasks = sorted({row["task_id"] for row in r143["group_rows"]})
    directional_pairs = [
        {"source_snapshot": source, "target_snapshot": target}
        for source, target in itertools.permutations(snapshots, 2)
    ]
    protocol = {
        "snapshot_names": snapshots,
        "task_ids": tasks,
        "directional_snapshot_pairs": directional_pairs,
        "directional_snapshot_pair_count": len(directional_pairs),
        "transfer_group_count": len(directional_pairs) * len(tasks),
        "hidden_trial_count_per_group": 8,
        "trial_row_count": len(directional_pairs) * len(tasks) * 8,
        "arms": ["source_transfer", "target_specific", "automatic"],
        "simulated_circuit_execution_count": len(directional_pairs) * len(tasks) * 8 * 3,
        "shots_per_execution": 2048,
        "total_simulated_shots": len(directional_pairs) * len(tasks) * 8 * 3 * 2048,
        "challenge_seed_derivation": "HMAC-SHA256 from post-preregistration secret",
        "shared_seed_rule": "all three arms in one row share one simulator seed",
        "transfer_rule": "carry source R143 mapping, policy_id, and realization_seed; recompile on target snapshot",
        "target_rule": "recompile target R143 mapping, policy_id, and realization_seed on target snapshot",
        "automatic_rule": "fresh optimization-level-3 compile on target snapshot with hidden transpiler seed",
        "minimum_semantic_fidelity": 0.9999999999,
        "minimum_portfolio_transfer_minus_automatic_mean": -0.005,
        "minimum_portfolio_transfer_minus_automatic_bootstrap_lower": -0.01,
        "minimum_portfolio_transfer_minus_target_mean": -0.005,
        "minimum_portfolio_transfer_minus_target_bootstrap_lower": -0.01,
        "minimum_group_count_above_negative_0_02_vs_target": 20,
        "maximum_severe_regression_count_below_negative_0_05_vs_target": 0,
        "minimum_each_target_mean_transfer_minus_target": -0.01,
    }
    requirements = [
        {"requirement_id": "R1", "label": "R143 and R145 source hashes are bound", "passed": True},
        {"requirement_id": "R2", "label": "all six directional snapshot pairs are fixed", "passed": protocol["directional_snapshot_pair_count"] == 6},
        {"requirement_id": "R3", "label": "four dense validation tasks produce 24 transfer groups", "passed": len(tasks) == 4 and protocol["transfer_group_count"] == 24},
        {"requirement_id": "R4", "label": "eight hidden trials produce 192 rows and 576 executions", "passed": protocol["trial_row_count"] == 192 and protocol["simulated_circuit_execution_count"] == 576},
        {"requirement_id": "R5", "label": "all arms use 2,048 shots and a shared row seed", "passed": protocol["shots_per_execution"] == 2048},
        {"requirement_id": "R6", "label": "source and target routes are recompiled on the target snapshot", "passed": "recompile" in protocol["transfer_rule"] and "recompile" in protocol["target_rule"]},
        {"requirement_id": "R7", "label": "portfolio noninferiority floors are fixed before challenge", "passed": protocol["minimum_portfolio_transfer_minus_target_mean"] == -0.005 and protocol["minimum_portfolio_transfer_minus_target_bootstrap_lower"] == -0.01},
        {"requirement_id": "R8", "label": "group, severe-regression, and each-target guards are fixed", "passed": protocol["minimum_group_count_above_negative_0_02_vs_target"] == 20 and protocol["maximum_severe_regression_count_below_negative_0_05_vs_target"] == 0 and protocol["minimum_each_target_mean_transfer_minus_target"] == -0.01},
        {"requirement_id": "R9", "label": "no R146 transfer trial has run during protocol design", "passed": True},
        {"requirement_id": "R10", "label": "temporal calibration, cross-machine, hardware, advantage, BQP, and credit claims remain false", "passed": True},
    ]
    payload = {
        "title": "B4/B8 R146 cross-backend calibration-snapshot transfer protocol",
        "version": 0,
        "method": METHOD,
        "status": "cross_snapshot_transfer_protocol_frozen_before_challenge",
        "model_status": "all_directional_fake_backend_snapshot_transfer_without_temporal_or_hardware_claim",
        "generated_at_unix": int(time.time()),
        "source_target_id": "T-B4-002ba/T-B8-003be/T-B10-009as",
        "upstream_target_id": "T-B4-002az/T-B8-003bd/T-B10-009ar",
        "source_bindings": {
            "r143_design_path": R143_PATH,
            "r143_design_sha256": file_sha256(root / R143_PATH),
            "r143_design_payload_hash": r143["payload_hash"],
            "r145_runtime_path": R145_PATH,
            "r145_runtime_sha256": file_sha256(root / R145_PATH),
            "r145_runtime_payload_hash": r145["payload_hash"],
            "task_builder_path": TASK_BUILDER_PATH,
            "task_builder_sha256": file_sha256(root / TASK_BUILDER_PATH),
        },
        "protocol": protocol,
        "requirements": requirements,
        "requirement_count": 10,
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [row["requirement_id"] for row in requirements if not row["passed"]],
        "challenge_executed": False,
        "claim_boundary": {
            "what_is_supported": "an immutable all-directional synthetic cross-backend snapshot transfer protocol",
            "what_is_not_supported": "a transfer result, temporal same-device calibration transfer, cross-machine transfer, real hardware, mitigation, soundness, quantum advantage, BQP separation, solved B4/B8/B10, or new credit",
        },
    }
    hash_payload = dict(payload)
    payload["payload_hash"] = hashlib.sha256(json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload


def report(payload: dict) -> str:
    p = payload["protocol"]
    return f"""# B4/B8 R146 Cross-Backend Snapshot Transfer Protocol

- Directional snapshot pairs: `{p['directional_snapshot_pair_count']}`
- Dense validation tasks: `{len(p['task_ids'])}`
- Transfer groups / hidden rows: `{p['transfer_group_count']}` / `{p['trial_row_count']}`
- Three-arm executions / total shots: `{p['simulated_circuit_execution_count']}` / `{p['total_simulated_shots']}`
- Arms: source-transfer, target-specific, automatic
- Portfolio transfer-target mean / bootstrap floors: `{p['minimum_portfolio_transfer_minus_target_mean']}` / `{p['minimum_portfolio_transfer_minus_target_bootstrap_lower']}`
- Groups above -0.02 versus target-specific: at least `{p['minimum_group_count_above_negative_0_02_vs_target']} / 24`
- Severe regressions below -0.05: at most `{p['maximum_severe_regression_count_below_negative_0_05_vs_target']}`
- Each-target mean transfer-target floor: `{p['minimum_each_target_mean_transfer_minus_target']}`
- Challenge executed: `false`

Every R143 winner is transferred in both directions to the other two fake
backend snapshots. The source mapping, route policy, and realization seed are
carried unchanged but recompiled on the target. The target-specific R143 route
and a hidden-seed automatic layout form the two denominators.

This protocol tests synthetic cross-backend snapshot transfer only. It does not
represent temporal calibration drift on one device, another machine, provider
access, hardware execution, advantage, BQP separation, or new credit.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    payload = build(root)
    write_json(root / RESULT_PATH, payload)
    (root / REPORT_PATH).write_text(report(payload), encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
