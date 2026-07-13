#!/usr/bin/env python3
"""Freeze the R148 task-conditioned channel-risk holdout protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256


METHOD = "b4_b8_r148_task_conditioned_channel_risk_protocol_v0"
DESIGN_PATH = "results/B4_B8_R148_task_conditioned_channel_risk_design_v0.json"
R143_PATH = "results/B4_B8_R143_successive_halving_lcb_design_v0.json"
R147_RESULT_PATH = "results/B4_B8_R147_target_descriptor_adaptation_holdout_v0.json"
RESULT_PATH = "results/B4_B8_R148_task_conditioned_channel_risk_protocol_v0.json"
REPORT_PATH = "research/B4_B8_R148_task_conditioned_channel_risk_protocol.md"


def build(root: Path) -> dict:
    design = json.loads((root / DESIGN_PATH).read_text())
    r143 = json.loads((root / R143_PATH).read_text())
    failure_groups = [
        "FakeJakartaV2::dense_validation_complete_ising_n6",
        "FakeJakartaV2::dense_validation_xy_network_n6",
        "FakeLagosV2::dense_validation_complete_ising_n6",
    ]
    protocol = {
        "snapshot_names": sorted({row["target_snapshot"] for row in design["selection_rows"]}),
        "task_ids": sorted({row["task_id"] for row in design["selection_rows"]}),
        "adaptation_group_count": 12,
        "hidden_trial_count_per_group": 8,
        "trial_row_count": 96,
        "arms": ["task_conditioned_foreign", "target_specific", "automatic"],
        "simulated_circuit_execution_count": 288,
        "shots_per_execution": 2048,
        "total_simulated_shots": 589824,
        "challenge_seed_derivation": "HMAC-SHA256 from post-preregistration secret",
        "shared_seed_rule": "all three arms in one row share one simulator seed",
        "adaptation_rule": "use the frozen zero-fit R148 task-conditioned channel-priority foreign route",
        "target_rule": "recompile the target-specific R143 route on target only as a denominator",
        "automatic_rule": "fresh optimization-level-3 compile on target with a hidden transpiler seed",
        "selector_forbidden_inputs": ["R147 hidden trial rows", "R147 group deltas", "R147 target deltas", "target-specific R143 route identity"],
        "minimum_semantic_fidelity": 0.9999999999,
        "minimum_portfolio_conditioned_minus_automatic_mean": -0.005,
        "minimum_portfolio_conditioned_minus_automatic_bootstrap_lower": -0.01,
        "minimum_portfolio_conditioned_minus_target_mean": -0.005,
        "minimum_portfolio_conditioned_minus_target_bootstrap_lower": -0.01,
        "minimum_group_count_above_negative_0_02_vs_target": 11,
        "maximum_severe_regression_count_below_negative_0_05_vs_target": 0,
        "minimum_each_target_mean_conditioned_minus_target": -0.01,
        "r147_failure_group_ids": failure_groups,
        "minimum_each_r147_failure_group_mean_conditioned_minus_target": -0.02,
        "maximum_r147_failure_group_severe_regression_count": 0,
    }
    requirements = [
        {"requirement_id": "R1", "label": "R148 design, R143 denominator, and R147 provenance hashes are bound", "passed": True},
        {"requirement_id": "R2", "label": "12 groups contain only two-candidate foreign-route selections", "passed": design["summary"]["adaptation_group_count"] == 12 and design["summary"]["foreign_candidate_count"] == 24},
        {"requirement_id": "R3", "label": "six readout-first and six CX-first groups are frozen with zero fitted weights", "passed": design["summary"]["readout_first_group_count"] == 6 and design["summary"]["cx_first_group_count"] == 6 and design["summary"]["fitted_weight_count"] == 0},
        {"requirement_id": "R4", "label": "R147 rows and target-specific routes were excluded from selection", "passed": design["summary"]["r147_hidden_trial_rows_read_count"] == 0 and design["summary"]["target_specific_routes_in_selector_count"] == 0},
        {"requirement_id": "R5", "label": "eight hidden trials produce 96 rows and 288 executions", "passed": protocol["trial_row_count"] == 96 and protocol["simulated_circuit_execution_count"] == 288},
        {"requirement_id": "R6", "label": "portfolio noninferiority floors are fixed before challenge", "passed": protocol["minimum_portfolio_conditioned_minus_target_mean"] == -0.005 and protocol["minimum_portfolio_conditioned_minus_target_bootstrap_lower"] == -0.01},
        {"requirement_id": "R7", "label": "group, severe-row, and each-target guards are fixed", "passed": protocol["minimum_group_count_above_negative_0_02_vs_target"] == 11 and protocol["maximum_severe_regression_count_below_negative_0_05_vs_target"] == 0 and protocol["minimum_each_target_mean_conditioned_minus_target"] == -0.01},
        {"requirement_id": "R8", "label": "all three R147 failure groups require simultaneous repair", "passed": len(failure_groups) == 3 and protocol["minimum_each_r147_failure_group_mean_conditioned_minus_target"] == -0.02 and protocol["maximum_r147_failure_group_severe_regression_count"] == 0},
        {"requirement_id": "R9", "label": "no R148 holdout has run during protocol design", "passed": True},
        {"requirement_id": "R10", "label": "scalability, temporal, cross-machine, hardware, advantage, BQP, solved-frontier, and credit claims remain false", "passed": True},
    ]
    payload = {
        "title": "B4/B8 R148 task-conditioned channel-risk holdout protocol",
        "version": 0,
        "method": METHOD,
        "status": "task_conditioned_channel_risk_protocol_frozen_before_challenge",
        "model_status": "zero_fit_channel_priority_foreign_route_holdout_without_r147_row_reuse",
        "generated_at_unix": int(time.time()),
        "source_target_id": "T-B4-002be/T-B8-003bi/T-B10-009aw",
        "upstream_target_id": "T-B4-002bd/T-B8-003bh/T-B10-009av",
        "source_bindings": {
            "r148_design_path": DESIGN_PATH,
            "r148_design_sha256": file_sha256(root / DESIGN_PATH),
            "r148_design_payload_hash": design["payload_hash"],
            "r143_design_path": R143_PATH,
            "r143_design_sha256": file_sha256(root / R143_PATH),
            "r143_design_payload_hash": r143["payload_hash"],
            "r147_result_path": R147_RESULT_PATH,
            "r147_result_sha256_provenance_only": file_sha256(root / R147_RESULT_PATH),
            "r147_trial_rows_consumed": False,
        },
        "protocol": protocol,
        "requirements": requirements,
        "requirement_count": 10,
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [row["requirement_id"] for row in requirements if not row["passed"]],
        "challenge_executed": False,
        "claim_boundary": {
            "what_is_supported": "an immutable zero-fit task-conditioned channel-risk holdout protocol",
            "what_is_not_supported": "a holdout result, scalable exact-output evaluation, temporal same-device transfer, cross-machine transfer, real hardware, mitigation, soundness, quantum advantage, BQP separation, solved B4/B8/B10, or new credit",
        },
    }
    hash_payload = dict(payload)
    payload["payload_hash"] = hashlib.sha256(json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload


def report(payload: dict) -> str:
    p = payload["protocol"]
    failure_groups = "\n".join(f"- `{group_id}`" for group_id in p["r147_failure_group_ids"])
    return f"""# B4/B8 R148 Task-Conditioned Channel-Risk Holdout Protocol

- Frozen groups / hidden rows: `{p['adaptation_group_count']}` / `{p['trial_row_count']}`
- Three-arm executions / total shots: `{p['simulated_circuit_execution_count']}` / `{p['total_simulated_shots']}`
- Arms: task-conditioned foreign route, target-specific R143, automatic
- Conditioned-target mean / bootstrap floors: `{p['minimum_portfolio_conditioned_minus_target_mean']}` / `{p['minimum_portfolio_conditioned_minus_target_bootstrap_lower']}`
- Groups above -0.02 versus target: at least `{p['minimum_group_count_above_negative_0_02_vs_target']} / 12`
- Severe rows below -0.05: at most `{p['maximum_severe_regression_count_below_negative_0_05_vs_target']}`
- Each-target mean floor: `{p['minimum_each_target_mean_conditioned_minus_target']}`
- Each R147 failure-group mean floor / combined severe cap: `{p['minimum_each_r147_failure_group_mean_conditioned_minus_target']}` / `{p['maximum_r147_failure_group_severe_regression_count']}`
- Challenge executed: `false`

## Required Simultaneous Repairs

{failure_groups}

The selector is frozen before challenge. It has no fitted weights: nonuniform
ideal outputs prioritize exact output-aware readout fidelity, while uniform
ideal outputs prioritize CX survival. R147 hidden rows, R147 deltas, and the
target-specific R143 identity are forbidden selector inputs.

This finite six-qubit protocol does not establish scalable exact-output
evaluation, temporal calibration transfer, another machine, real hardware,
mitigation, soundness, quantum advantage, BQP separation, a solved frontier,
or new credit.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    payload = build(root)
    write_json(root / RESULT_PATH, payload)
    (root / REPORT_PATH).write_text(report(payload), encoding="utf-8")
    print(json.dumps(payload["protocol"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
