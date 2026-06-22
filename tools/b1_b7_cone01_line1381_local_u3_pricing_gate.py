#!/usr/bin/env python3
"""Line-1381 local-U3 pricing boundary gate for the B1/B7 cone_01 candidate.

T-B1-004bb accepts one tolerance-bounded semantic patch artifact for the
non-overlap line-268 plus line-1381 QASM2 candidate, but B7 still rejects the
route as a resource improvement. This gate prices the remaining blocker:
line 1381 keeps five off-pi/4 local-U3 parameters, and line 1378 was dropped
from the composable patch set.

The result is a quantified negative boundary. It is not an occurrence-removing
certificate and does not improve the B7 ledger.
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
COMPOSABLE_PATCH_PATH = (
    ROOT / "results" / "B1_B7_cone01_composable_patch_certificate_gate_v0.json"
)
NONOVERLAP_PATH = ROOT / "results" / "B1_B7_cone01_nonoverlap_patch_subset_gate_v0.json"
JSON_OUT = ROOT / "results" / "B1_B7_cone01_line1381_local_u3_pricing_gate_v0.json"
MD_OUT = ROOT / "research" / "B1_B7_cone01_line1381_local_u3_pricing_gate.md"

METHOD = "b1_b7_cone01_line1381_local_u3_pricing_gate_v0"
STATUS = "cone01_line1381_local_u3_pricing_boundary_no_b7_credit"
MODEL_STATUS = "semantic_patch_certificate_blocked_by_unpriced_local_u3_and_dropped_line1378"


def selected_rows_by_line(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {int(row["candidate_line_number"]): row for row in rows}


def run_probe() -> dict[str, Any]:
    patch_payload = load_json(COMPOSABLE_PATCH_PATH)
    nonoverlap_payload = load_json(NONOVERLAP_PATH)
    patch_summary = patch_payload.get("summary", {})
    rows = selected_rows_by_line(patch_summary.get("row_certificates", []))
    line1381 = rows.get(1381, {})
    line268 = rows.get(268, {})
    dropped_lines = [
        int(value)
        for value in patch_summary.get("dropped_overlap_candidate_line_numbers", [])
    ]
    line1381_off_grid = int(line1381.get("replacement_off_pi_over_four_parameter_count", 0))
    line268_off_grid = int(line268.get("replacement_off_pi_over_four_parameter_count", 0))
    selected_off_grid = int(
        patch_summary.get("selected_replacement_off_pi_over_four_parameter_count", 0)
    )
    line1381_proxy_t_pressure = line1381_off_grid * PROXY_T_PER_OCCURRENCE
    selected_proxy_t_pressure = selected_off_grid * PROXY_T_PER_OCCURRENCE
    selected_candidate_cnot_reduction = int(patch_summary.get("selected_candidate_cnot_reduction", 0))
    lost_delta = int(patch_summary.get("lost_candidate_cnot_reduction_due_to_overlap", 0))
    total_possible_delta_if_dropped_recovered = selected_candidate_cnot_reduction + lost_delta
    semantic_patch_passed = (
        patch_summary.get("tolerance_bounded_full_circuit_semantic_certificate_passed") is True
    )
    local_u3_pricing_boundary_passed = (
        semantic_patch_passed
        and line1381_off_grid == 5
        and line1381_proxy_t_pressure == 100
        and 1378 in dropped_lines
        and selected_candidate_cnot_reduction == 6
    )
    accepted_removed = 0
    summary = {
        "source_composable_patch_method": patch_payload.get("method"),
        "source_nonoverlap_subset_method": nonoverlap_payload.get("method"),
        "tolerance_bounded_semantic_patch_certificate_passed": semantic_patch_passed,
        "selected_line_numbers": patch_summary.get("selected_line_numbers"),
        "dropped_overlap_candidate_line_numbers": dropped_lines,
        "line1378_delta_recovered": False,
        "lost_candidate_cnot_reduction_due_to_overlap": lost_delta,
        "selected_candidate_cnot_reduction": selected_candidate_cnot_reduction,
        "total_possible_cnot_delta_if_line1378_recovered": total_possible_delta_if_dropped_recovered,
        "line268_replacement_off_pi_over_four_parameter_count": line268_off_grid,
        "line1381_replacement_off_pi_over_four_parameter_count": line1381_off_grid,
        "selected_replacement_off_pi_over_four_parameter_count": selected_off_grid,
        "proxy_t_per_off_grid_local_u3_parameter": PROXY_T_PER_OCCURRENCE,
        "line1381_unpriced_proxy_t_pressure": line1381_proxy_t_pressure,
        "selected_unpriced_proxy_t_pressure": selected_proxy_t_pressure,
        "selected_proxy_t_pressure_minus_cnot_delta_proxy": (
            selected_proxy_t_pressure - selected_candidate_cnot_reduction * PROXY_T_PER_OCCURRENCE
        ),
        "local_u3_pricing_boundary_passed": local_u3_pricing_boundary_passed,
        "local_u3_resource_pricing_accepted": False,
        "line1381_off_grid_parameters_eliminated": False,
        "line1381_off_grid_parameters_absorbed": False,
        "line1381_off_grid_parameters_symbolically_decomposed": False,
        "accepted_full_circuit_replay_certificate_count": patch_summary.get(
            "accepted_full_circuit_replay_certificate_count"
        ),
        "accepted_full_circuit_qasm_patch_count": patch_summary.get(
            "accepted_full_circuit_qasm_patch_count"
        ),
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
        "source_composable_patch_result": display_path(COMPOSABLE_PATCH_PATH),
        "source_nonoverlap_subset_result": display_path(NONOVERLAP_PATH),
        "summary": summary,
        "claim_boundary": {
            "supported_claim": (
                "The T-B1-004bb semantic patch certificate is now resource-priced "
                "at the remaining line-1381 local-U3 boundary: five off-grid "
                "parameters create 100 proxy-T pressure units under the project ledger."
            ),
            "unsupported_claims": [
                "This does not eliminate, absorb, or symbolically decompose the line-1381 parameters.",
                "This does not recover the dropped line-1378 CNOT delta.",
                "This is not an accepted B7 occurrence-removing certificate.",
                "This does not improve the B7 ledger.",
            ],
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "local_u3_resource_pricing_accepted": False,
            "line1378_delta_recovered": False,
        },
    }
    return payload


def markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# B1/B7 cone_01 Line-1381 Local-U3 Pricing Boundary Gate",
        "",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Model status: `{payload['model_status']}`",
        f"- Workload: `{payload['workload']}`",
        f"- Source composable patch: `{payload['source_composable_patch_result']}`",
        f"- Source non-overlap subset: `{payload['source_nonoverlap_subset_result']}`",
        "",
        "## Result",
        "",
        f"- Semantic patch certificate passed: `{summary['tolerance_bounded_semantic_patch_certificate_passed']}`",
        f"- Selected lines: `{summary['selected_line_numbers']}`",
        f"- Dropped overlap lines: `{summary['dropped_overlap_candidate_line_numbers']}`",
        f"- Selected CNOT delta: `{summary['selected_candidate_cnot_reduction']}`",
        f"- Lost CNOT delta from line 1378: `{summary['lost_candidate_cnot_reduction_due_to_overlap']}`",
        f"- Line-1381 off-grid local-U3 parameters: `{summary['line1381_replacement_off_pi_over_four_parameter_count']}`",
        f"- Line-1381 unpriced proxy-T pressure: `{summary['line1381_unpriced_proxy_t_pressure']}`",
        f"- Selected unpriced proxy-T pressure: `{summary['selected_unpriced_proxy_t_pressure']}`",
        f"- Local-U3 pricing boundary passed: `{summary['local_u3_pricing_boundary_passed']}`",
        f"- Local-U3 resource pricing accepted: `{summary['local_u3_resource_pricing_accepted']}`",
        f"- Accepted occurrence / proxy-T reduction: `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        "",
        "## Claim Boundary",
        "",
        "- This is a resource-pricing boundary, not a resource win.",
        "- B7 ledger improvement remains 0 until line 1381 is priced/eliminated/absorbed and line 1378 is recovered or replaced by another occurrence-removing route.",
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
