#!/usr/bin/env python3
"""Build the immutable R142 seed-robust LCB mapping holdout contract."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256


TARGET_ID = "T-B4-002at/T-B8-003ax/T-B10-009al"
DESIGN_PATH = "results/B4_B8_R142_seed_robust_lcb_mapping_design_v0.json"
R141_HOLDOUT_PATH = "results/B4_B8_R141_hashed_output_sketch_holdout_v0.json"
R140_DESIGN_PATH = "results/B4_B8_R140_output_aware_mapping_design_v0.json"
CONTRACT_PATH = "benchmarks/B4_B8_R142_seed_robust_lcb_mapping_holdout_contract_v0.json"


def load(root: Path, relative: str) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def build_contract(root: Path) -> dict[str, Any]:
    design = load(root, DESIGN_PATH)
    r141_holdout = load(root, R141_HOLDOUT_PATH)
    r140 = load(root, R140_DESIGN_PATH)
    artifacts = [
        {
            "artifact_id": f"{row['snapshot']}::{row['task_id']}",
            "path": row["selected_circuit_path"],
            "sha256": row["selected_circuit_sha256"],
        }
        for row in design["group_rows"]
    ]
    shortlist_identity = [
        {
            "snapshot": row["snapshot"],
            "task_id": row["task_id"],
            "mapping": row["mapping"],
            "policy_id": row["policy_id"],
            "realization_seed": row["realization_seed"],
            "design_qasm_stable_hash": row["design_qasm_stable_hash"],
        }
        for row in design["design_rows"]
    ]
    return {
        "contract_id": "B4-B8-R142-seed-robust-lcb-mapping-holdout-v0",
        "contract_status": "public_preregistration_execution_unopened",
        "target_id": TARGET_ID,
        "upstream_target_id": design["source_target_id"],
        "research_question": "Does lower-confidence-bound route selection repair the fresh-seed Lagos reversal without buying portfolio regressions?",
        "source_bindings": {
            "r142_design_path": DESIGN_PATH,
            "r142_design_sha256": file_sha256(root / DESIGN_PATH),
            "r142_design_payload_hash": design["payload_hash"],
            "r141_holdout_path": R141_HOLDOUT_PATH,
            "r141_holdout_sha256": file_sha256(root / R141_HOLDOUT_PATH),
            "r141_holdout_payload_hash": r141_holdout["payload_hash"],
            "r140_design_path": R140_DESIGN_PATH,
            "r140_design_sha256": file_sha256(root / R140_DESIGN_PATH),
            "r140_design_payload_hash": r140["payload_hash"],
            "shortlist_identity_sha256": hashlib.sha256(
                json.dumps(shortlist_identity, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        },
        "algorithm_lock": {
            "shortlist_unique_qasm_count_per_group": 8,
            "shortlist_source": "R141 hashed-output-sketch score",
            "design_seed_count": 16,
            "design_shots_per_execution": 2048,
            "lcb_formula": "mean_delta_vs_automatic-1.96*standard_error",
            "r141_holdout_rows_visible_to_design_selector": 0,
        },
        "artifact_bindings": artifacts,
        "challenge_design": {
            "backend_task_group_count": 12,
            "hidden_trial_count_per_group": 8,
            "paired_trial_row_count": 96,
            "arms": ["r142_lcb", "r140_exact", "automatic"],
            "simulated_circuit_execution_count": 288,
            "shots_per_circuit": 4096,
            "total_simulated_shots": 1179648,
            "shared_simulator_seed_within_three_arm_row": True,
            "hidden_transpiler_and_simulator_seeds_derived_after_preregistration": True,
            "bootstrap_resample_count": 10000,
        },
        "acceptance_conditions": [
            {"condition_id": "A1", "condition": "all design, shortlist, and selected-QASM bindings remain exact"},
            {"condition_id": "A2", "condition": "all 96 rows contain complete R142, R140, and automatic arms"},
            {"condition_id": "A3", "condition": "Lagos R142-minus-automatic mean noisy fidelity is nonnegative"},
            {"condition_id": "A4", "condition": "Lagos R142 wins at least 4 of 8 hidden rows against automatic"},
            {"condition_id": "A5", "condition": "Lagos R142-minus-R140 mean noisy fidelity is at least +0.005"},
            {"condition_id": "A6", "condition": "portfolio R142-minus-automatic bootstrap 95% lower bound is at least -0.005"},
            {"condition_id": "A7", "condition": "portfolio R142-minus-R140 mean noisy fidelity is at least -0.002"},
            {"condition_id": "A8", "condition": "at least 11 of 12 groups have mean R142-minus-R140 at least -0.01"},
            {"condition_id": "A9", "condition": "all phase artifacts replay and work equals 288 executions and 1,179,648 shots"},
            {"condition_id": "A10", "condition": "production efficiency, hardware, soundness, advantage, BQP, and new-credit claims remain false"},
        ],
        "phase_protocol": [
            "commit a fresh secret after this contract is public",
            "derive hidden transpiler, simulator, and bootstrap seeds",
            "write all 96 three-arm rows before revealing the secret",
            "reveal the secret and replay every row and verdict",
        ],
        "claim_boundary": {
            "positive_result_requires_all_conditions": True,
            "what_is_not_supported_even_if_accepted": "efficient production selection, current calibration, real hardware, mitigation, independent custody, protocol soundness, quantum advantage, BQP separation, or solved B4/B8/B10",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or root / CONTRACT_PATH
    write_json(output, build_contract(root))
    print(file_sha256(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
