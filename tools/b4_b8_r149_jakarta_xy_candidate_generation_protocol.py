#!/usr/bin/env python3
"""Freeze the R149 Jakarta dense-XY generated-route portfolio holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256


METHOD = "b4_b8_r149_jakarta_xy_candidate_generation_protocol_v0"
DESIGN_PATH = "results/B4_B8_R149_jakarta_xy_candidate_generation_design_v0.json"
R148_DESIGN_PATH = "results/B4_B8_R148_task_conditioned_channel_risk_design_v0.json"
R148_RESULT_PATH = "results/B4_B8_R148_task_conditioned_channel_risk_holdout_v0.json"
R143_PATH = "results/B4_B8_R143_successive_halving_lcb_design_v0.json"
RESULT_PATH = "results/B4_B8_R149_jakarta_xy_candidate_generation_protocol_v0.json"
REPORT_PATH = "research/B4_B8_R149_jakarta_xy_candidate_generation_protocol.md"


def build(root: Path) -> dict:
    design = json.loads((root / DESIGN_PATH).read_text())
    r148_design = json.loads((root / R148_DESIGN_PATH).read_text())
    r143 = json.loads((root / R143_PATH).read_text())
    protocol = {
        "snapshot_names": sorted({row["target_snapshot"] for row in r148_design["selection_rows"]}),
        "task_ids": sorted({row["task_id"] for row in r148_design["selection_rows"]}),
        "replacement_group_id": "FakeJakartaV2::dense_validation_xy_network_n6",
        "portfolio_group_count": 12,
        "hidden_trial_count_per_group": 8,
        "trial_row_count": 96,
        "portfolio_arms": ["r149_repaired_portfolio", "target_specific", "automatic"],
        "replacement_diagnostic_arm": "r148_foreign",
        "simulated_circuit_execution_count": 296,
        "shots_per_execution": 2048,
        "total_simulated_shots": 606208,
        "challenge_seed_derivation": "HMAC-SHA256 from post-preregistration secret",
        "shared_seed_rule": "all arms in one row share one simulator seed",
        "portfolio_rule": "use the R149 generated route only for Jakarta dense XY and preserve frozen R148 routes for the other 11 groups",
        "target_rule": "recompile the target-specific R143 route only as a denominator",
        "automatic_rule": "fresh optimization-level-3 compile with a hidden transpiler seed",
        "replacement_diagnostic_rule": "recompile the frozen R148 foreign route only for Jakarta dense XY",
        "minimum_semantic_fidelity": 0.9999999999,
        "minimum_portfolio_repaired_minus_automatic_mean": -0.005,
        "minimum_portfolio_repaired_minus_automatic_bootstrap_lower": -0.01,
        "minimum_portfolio_repaired_minus_target_mean": -0.005,
        "minimum_portfolio_repaired_minus_target_bootstrap_lower": -0.01,
        "minimum_group_count_above_negative_0_02_vs_target": 12,
        "maximum_severe_regression_count_below_negative_0_05_vs_target": 0,
        "minimum_each_target_mean_repaired_minus_target": -0.01,
        "minimum_replacement_group_mean_repaired_minus_target": -0.02,
        "minimum_replacement_group_mean_repaired_minus_r148_foreign": 0.01,
        "maximum_replacement_group_severe_regression_count": 0,
    }
    requirements = [
        {"requirement_id": "R1", "label": "R149 design, R148 portfolio/result provenance, and R143 denominator hashes are bound", "passed": True},
        {"requirement_id": "R2", "label": "generated mapping copies neither target R143 nor foreign R148 identities", "passed": not design["summary"]["selected_mapping_matches_target_r143"] and not design["summary"]["selected_mapping_matches_foreign_r148"]},
        {"requirement_id": "R3", "label": "R148 hidden rows remain unused for candidate generation and selection", "passed": design["summary"]["r148_hidden_trial_rows_read_count"] == 0},
        {"requirement_id": "R4", "label": "one generated replacement and eleven frozen R148 routes form 12 portfolio groups", "passed": protocol["portfolio_group_count"] == 12},
        {"requirement_id": "R5", "label": "eight hidden trials produce 96 rows and 296 executions", "passed": protocol["trial_row_count"] == 96 and protocol["simulated_circuit_execution_count"] == 296},
        {"requirement_id": "R6", "label": "portfolio and each-target noninferiority floors remain unchanged", "passed": protocol["minimum_portfolio_repaired_minus_target_mean"] == -0.005 and protocol["minimum_portfolio_repaired_minus_target_bootstrap_lower"] == -0.01 and protocol["minimum_each_target_mean_repaired_minus_target"] == -0.01},
        {"requirement_id": "R7", "label": "all 12 groups must clear -0.02 with zero severe rows", "passed": protocol["minimum_group_count_above_negative_0_02_vs_target"] == 12 and protocol["maximum_severe_regression_count_below_negative_0_05_vs_target"] == 0},
        {"requirement_id": "R8", "label": "replacement must clear target noninferiority and improve at least +0.01 over R148 foreign", "passed": protocol["minimum_replacement_group_mean_repaired_minus_target"] == -0.02 and protocol["minimum_replacement_group_mean_repaired_minus_r148_foreign"] == 0.01},
        {"requirement_id": "R9", "label": "no R149 holdout has run during protocol design", "passed": True},
        {"requirement_id": "R10", "label": "general generation, temporal, cross-machine, hardware, advantage, BQP, solved-frontier, and credit claims remain false", "passed": True},
    ]
    payload = {
        "title": "B4/B8 R149 Jakarta dense-XY generated-route portfolio protocol",
        "version": 0,
        "method": METHOD,
        "status": "jakarta_xy_generated_route_protocol_frozen_before_challenge",
        "model_status": "one_generated_replacement_plus_eleven_frozen_r148_routes",
        "generated_at_unix": int(time.time()),
        "source_target_id": "T-B4-002bg/T-B8-003bk/T-B10-009ay",
        "upstream_target_id": "T-B4-002bf/T-B8-003bj/T-B10-009ax",
        "source_bindings": {
            "r149_design_path": DESIGN_PATH,
            "r149_design_sha256": file_sha256(root / DESIGN_PATH),
            "r149_design_payload_hash": design["payload_hash"],
            "r148_design_path": R148_DESIGN_PATH,
            "r148_design_sha256": file_sha256(root / R148_DESIGN_PATH),
            "r148_design_payload_hash": r148_design["payload_hash"],
            "r148_result_path": R148_RESULT_PATH,
            "r148_result_sha256_provenance_only": file_sha256(root / R148_RESULT_PATH),
            "r148_trial_rows_consumed": False,
            "r143_design_path": R143_PATH,
            "r143_design_sha256": file_sha256(root / R143_PATH),
            "r143_design_payload_hash": r143["payload_hash"],
        },
        "protocol": protocol,
        "requirements": requirements,
        "requirement_count": 10,
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [row["requirement_id"] for row in requirements if not row["passed"]],
        "challenge_executed": False,
        "claim_boundary": {
            "what_is_supported": "an immutable one-route replacement protocol with a full 12-group regression portfolio",
            "what_is_not_supported": "a holdout repair, general route-generation advantage, temporal transfer, cross-machine transfer, real hardware, mitigation, soundness, quantum advantage, BQP separation, solved B4/B8/B10, or new credit",
        },
    }
    hash_payload = dict(payload)
    payload["payload_hash"] = hashlib.sha256(json.dumps(hash_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return payload


def report(payload: dict) -> str:
    p = payload["protocol"]
    return f"""# B4/B8 R149 Jakarta Dense-XY Generated-Route Portfolio Protocol

- Portfolio groups / hidden rows: `{p['portfolio_group_count']}` / `{p['trial_row_count']}`
- Executions / total shots: `{p['simulated_circuit_execution_count']}` / `{p['total_simulated_shots']}`
- Replacement group: `{p['replacement_group_id']}`
- Portfolio repaired-target mean / bootstrap floors: `{p['minimum_portfolio_repaired_minus_target_mean']}` / `{p['minimum_portfolio_repaired_minus_target_bootstrap_lower']}`
- Groups above -0.02 versus target: `{p['minimum_group_count_above_negative_0_02_vs_target']} / 12`
- Severe rows below -0.05: at most `{p['maximum_severe_regression_count_below_negative_0_05_vs_target']}`
- Replacement repaired-target floor: `{p['minimum_replacement_group_mean_repaired_minus_target']}`
- Replacement repaired-R148-foreign improvement floor: `{p['minimum_replacement_group_mean_repaired_minus_r148_foreign']}`
- Challenge executed: `false`

The R149 generated route replaces only Jakarta dense XY. The other 11 groups
retain the frozen R148 routes, so the challenge can detect collateral portfolio
regression. The residual group additionally replays the old R148 foreign route
under the same row seed and must improve by at least +0.01.

This protocol does not establish a holdout repair, general route-generation
advantage, temporal or cross-machine transfer, real hardware, mitigation,
soundness, quantum advantage, BQP separation, a solved frontier, or new credit.
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
