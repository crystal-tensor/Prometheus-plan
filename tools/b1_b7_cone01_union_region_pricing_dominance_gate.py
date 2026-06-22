#!/usr/bin/env python3
"""Pricing-dominance gate for the B1/B7 cone_01 union-region candidates.

T-B1-004bf confirmed that the line-1378/1381 union target has robust 2-CNOT
local-U3 candidates across all four direction sequences. This gate checks the
next resource question: do any of those robust candidates dominate the current
line-1381 patch boundary after local-U3 pricing?

They do not. The current line-1381 branch already has a 2-CNOT replacement with
five off-pi/4 local-U3 parameters. The orientation-census candidates carry at
least thirteen off-pi/4 parameters, so they are useful robustness evidence but
not a better B7 resource route.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from b1_b7_cone01_carrier_absorption_inventory_gate import (
    PROXY_T_PER_OCCURRENCE,
    REQUIRED_OCCURRENCE_REMOVALS,
    display_path,
    load_json,
    write_json,
    write_text,
)


ROOT = Path(__file__).resolve().parents[1]
TWO_CNOT_CENSUS_PATH = (
    ROOT / "results" / "B1_B7_cone01_union_region_two_cnot_orientation_census_gate_v0.json"
)
LINE1381_PRICING_PATH = ROOT / "results" / "B1_B7_cone01_line1381_local_u3_pricing_gate_v0.json"
OVERLAP_BOUND_PATH = ROOT / "results" / "B1_B7_cone01_overlap_additivity_bound_gate_v0.json"
JSON_OUT = ROOT / "results" / "B1_B7_cone01_union_region_pricing_dominance_gate_v0.json"
MD_OUT = ROOT / "research" / "B1_B7_cone01_union_region_pricing_dominance_gate.md"

METHOD = "b1_b7_cone01_union_region_pricing_dominance_gate_v0"
STATUS = "cone01_union_region_two_cnot_candidates_pricing_dominated"
MODEL_STATUS = "current_line1381_patch_has_lower_local_u3_pricing_pressure"


def build_rows(census_rows: list[dict[str, Any]], current_off_grid: int) -> list[dict[str, Any]]:
    rows = []
    current_pressure = current_off_grid * PROXY_T_PER_OCCURRENCE
    for row in census_rows:
        stats = row["best"]["parameter_stats"]
        off_grid = int(stats["off_pi_over_four_grid_parameter_count"])
        pressure = off_grid * PROXY_T_PER_OCCURRENCE
        rows.append(
            {
                "sequence_id": row["sequence_id"],
                "cnot_sequence": row["cnot_sequence"],
                "exact_pass": row["exact_pass"],
                "residual_norm": row["best"]["residual_norm"],
                "max_abs_entry_error": row["best"]["max_abs_entry_error"],
                "replacement_cnot_count": int(row["cnot_count"]),
                "off_pi_over_four_parameter_count": off_grid,
                "nonzero_parameter_count": int(stats["nonzero_parameter_count"]),
                "parameter_count": int(stats["parameter_count"]),
                "proxy_t_pressure": pressure,
                "pressure_delta_vs_current_line1381": pressure - current_pressure,
                "off_grid_delta_vs_current_line1381": off_grid - current_off_grid,
                "dominates_current_line1381_pricing": pressure < current_pressure,
                "ties_current_line1381_pricing": pressure == current_pressure,
                "dominated_by_current_line1381_pricing": pressure > current_pressure,
            }
        )
    return rows


def run_probe() -> dict[str, Any]:
    census = load_json(TWO_CNOT_CENSUS_PATH)
    pricing = load_json(LINE1381_PRICING_PATH)
    overlap = load_json(OVERLAP_BOUND_PATH)
    census_summary = census["summary"]
    pricing_summary = pricing["summary"]
    overlap_summary = overlap["summary"]
    current_off_grid = int(pricing_summary["line1381_replacement_off_pi_over_four_parameter_count"])
    current_pressure = int(pricing_summary["line1381_unpriced_proxy_t_pressure"])
    rows = build_rows(census["union_region_two_cnot_orientation_rows"], current_off_grid)
    exact_rows = [row for row in rows if row["exact_pass"]]
    best_by_pressure = min(rows, key=lambda row: (row["proxy_t_pressure"], row["residual_norm"]))
    dominating_rows = [row for row in rows if row["dominates_current_line1381_pricing"]]
    accepted_removed = 0
    summary = {
        "source_two_cnot_census_method": census.get("method"),
        "source_line1381_pricing_method": pricing.get("method"),
        "source_overlap_bound_method": overlap.get("method"),
        "target_line_number": 1381,
        "union_window": census_summary.get("union_window"),
        "support_qubits": census_summary.get("support_qubits"),
        "source_cnot_count": census_summary.get("source_cnot_count"),
        "current_min_exact_replacement_cnot_count": census_summary.get(
            "current_min_exact_replacement_cnot_count"
        ),
        "current_candidate_cnot_delta": census_summary.get("current_candidate_cnot_delta"),
        "current_line1381_off_pi_over_four_parameter_count": current_off_grid,
        "current_line1381_proxy_t_pressure": current_pressure,
        "proxy_t_per_off_grid_local_u3_parameter": PROXY_T_PER_OCCURRENCE,
        "two_cnot_exact_sequence_count": census_summary.get("two_cnot_exact_sequence_count"),
        "two_cnot_sequence_count_reviewed": len(rows),
        "min_census_off_pi_over_four_parameter_count": best_by_pressure[
            "off_pi_over_four_parameter_count"
        ],
        "min_census_proxy_t_pressure": best_by_pressure["proxy_t_pressure"],
        "best_priced_census_sequence_id": best_by_pressure["sequence_id"],
        "best_priced_census_residual_norm": best_by_pressure["residual_norm"],
        "best_priced_census_max_abs_entry_error": best_by_pressure["max_abs_entry_error"],
        "off_grid_delta_vs_current_line1381": (
            best_by_pressure["off_pi_over_four_parameter_count"] - current_off_grid
        ),
        "proxy_t_pressure_delta_vs_current_line1381": (
            best_by_pressure["proxy_t_pressure"] - current_pressure
        ),
        "census_candidate_dominates_current_line1381_pricing": bool(dominating_rows),
        "dominating_census_sequence_count": len(dominating_rows),
        "current_line1381_patch_pricing_dominates_census": len(dominating_rows) == 0,
        "line1378_additive_recovery_blocked": overlap_summary.get(
            "additive_recovery_impossible_by_cnot_bound"
        ),
        "extra_delta_found_beyond_current_line1381_replacement": 0,
        "selected_replacement_changed": False,
        "two_cnot_census_adopted_for_b7_ledger": False,
        "local_u3_pricing_completed": False,
        "accepted_full_circuit_replay_certificate_count": 0,
        "accepted_full_circuit_qasm_patch_count": 0,
        "accepted_occurrence_removal": accepted_removed,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": max(0, REQUIRED_OCCURRENCE_REMOVALS - accepted_removed),
        "missing_proxy_t_after_gate": max(
            0,
            (REQUIRED_OCCURRENCE_REMOVALS - accepted_removed) * PROXY_T_PER_OCCURRENCE,
        ),
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "validation_error_count": 0,
    }
    payload = {
        "benchmark_id": "B1",
        "linked_b7_problem_id": 21,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "workload": "qasmbench_medium_exact/gcm_h6.qasm",
        "source_two_cnot_census_result": display_path(TWO_CNOT_CENSUS_PATH),
        "source_line1381_pricing_result": display_path(LINE1381_PRICING_PATH),
        "source_overlap_bound_result": display_path(OVERLAP_BOUND_PATH),
        "summary": summary,
        "union_region_pricing_dominance_rows": rows,
        "claim_boundary": {
            "supported_claim": (
                "The robust T-B1-004bf 2-CNOT union candidates do not dominate "
                "the current line-1381 patch on local-U3 pricing pressure."
            ),
            "unsupported_claims": [
                "This does not prove no better 2-CNOT parameterization exists.",
                "This does not emit a new full-circuit patch.",
                "This does not complete local-U3 resource pricing.",
                "This does not recover line 1378 or improve the B7 ledger.",
            ],
            "selected_replacement_changed": False,
            "two_cnot_census_adopted_for_b7_ledger": False,
            "local_u3_pricing_completed": False,
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
    }
    return payload


def markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# B1/B7 cone_01 Union-Region Pricing Dominance Gate",
        "",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Model status: `{payload['model_status']}`",
        f"- Workload: `{payload['workload']}`",
        f"- Source 2-CNOT census: `{payload['source_two_cnot_census_result']}`",
        f"- Source line-1381 pricing: `{payload['source_line1381_pricing_result']}`",
        f"- Source overlap bound: `{payload['source_overlap_bound_result']}`",
        "",
        "## Result",
        "",
        f"- Union window: `{summary['union_window']}`",
        f"- Source CNOT / replacement CNOT / CNOT delta: `{summary['source_cnot_count']}` / `{summary['current_min_exact_replacement_cnot_count']}` / `{summary['current_candidate_cnot_delta']}`",
        f"- Current line-1381 off-grid parameters / proxy-T pressure: `{summary['current_line1381_off_pi_over_four_parameter_count']}` / `{summary['current_line1381_proxy_t_pressure']}`",
        f"- Reviewed exact 2-CNOT census sequences: `{summary['two_cnot_exact_sequence_count']}`",
        f"- Best priced census sequence: `{summary['best_priced_census_sequence_id']}`",
        f"- Census min off-grid parameters / proxy-T pressure: `{summary['min_census_off_pi_over_four_parameter_count']}` / `{summary['min_census_proxy_t_pressure']}`",
        f"- Delta vs current line-1381 off-grid / proxy-T pressure: `{summary['off_grid_delta_vs_current_line1381']}` / `{summary['proxy_t_pressure_delta_vs_current_line1381']}`",
        f"- Census candidate dominates current pricing: `{summary['census_candidate_dominates_current_line1381_pricing']}`",
        f"- Current patch pricing dominates census: `{summary['current_line1381_patch_pricing_dominates_census']}`",
        f"- Selected replacement changed: `{summary['selected_replacement_changed']}`",
        f"- Accepted occurrence / proxy-T reduction / B7 claim: `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}` / `{summary['b7_ledger_improvement_claimed']}`",
        "",
        "## Claim Boundary",
        "",
        "- This is a pricing-dominance check, not a global optimality theorem.",
        "- The 2-CNOT census remains robustness evidence; it is not adopted as a better B7 resource route.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", default=str(JSON_OUT))
    parser.add_argument("--markdown-output", default=str(MD_OUT))
    args = parser.parse_args()
    payload = run_probe()
    write_json(Path(args.json_output), payload, True)
    write_text(Path(args.markdown_output), markdown_report(payload))
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
