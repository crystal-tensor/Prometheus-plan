#!/usr/bin/env python3
"""Neighborhood/commutation gate for B1/B7 cone_01 carrier absorption.

T-B1-004x showed that carrier-angle matches in the native optimized gcm_h6
rotation inventory are partial and not line-local. This gate asks the next
local question: are any same-target inventory matches close enough to the
source occurrences, and do they have a simple target-qubit two-qubit blocker
between the match and the nearest source line?

This is still not an absorption certificate. A neighborhood match is only a
candidate for a future replayable rewrite. The current evidence covers at most
one residual pattern in a small neighborhood and leaves accepted B7 reduction
at zero.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from b1_b7_cone01_carrier_absorption_inventory_gate import (
    INVENTORY_QASM_PATH,
    LEDGER_PATH,
    PACKET_PATH,
    PROXY_T_PER_OCCURRENCE,
    REQUIRED_OCCURRENCE_REMOVALS,
    compact_matches,
    display_path,
    load_json,
    parse_rotation_inventory,
    same_abs_angle,
    write_json,
    write_text,
)


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_GATE_PATH = ROOT / "results" / "B1_B7_cone01_carrier_absorption_inventory_gate_v0.json"
JSON_OUT = ROOT / "results" / "B1_B7_cone01_carrier_neighborhood_commutation_gate_v0.json"
MD_OUT = ROOT / "research" / "B1_B7_cone01_carrier_neighborhood_commutation_gate.md"

METHOD = "b1_b7_cone01_carrier_neighborhood_commutation_gate_v0"
STATUS = "cone01_carrier_neighborhood_commutation_negative_gate"
MODEL_STATUS = "nearby_inventory_matches_do_not_cover_all_carriers_or_accept_absorption"
NEIGHBORHOOD_RADII = (4, 8, 16)
CX_RE = re.compile(r"^cx q\[(\d+)\],q\[(\d+)\];$")


def parse_qasm_lines(path: Path) -> dict[int, str]:
    return {idx: line.strip() for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)}


def cx_qubits(line: str) -> set[int]:
    match = CX_RE.match(line.strip())
    if not match:
        return set()
    return {int(match.group(1)), int(match.group(2))}


def segment_blockers(
    qasm_lines: dict[int, str],
    start_line: int,
    end_line: int,
    target_qubits: set[int],
) -> list[dict[str, Any]]:
    lower = min(start_line, end_line) + 1
    upper = max(start_line, end_line)
    blockers = []
    for line_number in range(lower, upper):
        qubits = cx_qubits(qasm_lines.get(line_number, ""))
        if qubits and qubits.intersection(target_qubits):
            blockers.append(
                {
                    "line_number": line_number,
                    "text": qasm_lines[line_number],
                    "qubits": sorted(qubits),
                }
            )
    return blockers


def nearest_source(match_line: int, source_lines: list[int]) -> tuple[int, int]:
    nearest = min(source_lines, key=lambda line: (abs(line - match_line), line))
    return nearest, abs(match_line - nearest)


def analyze_row(
    ledger_row: dict[str, Any],
    packet: dict[str, Any],
    inventory_rows: list[dict[str, Any]],
    qasm_lines: dict[int, str],
) -> dict[str, Any]:
    angle = float(ledger_row["carrier_angle"])
    targets = set(int(q) for q in packet["target_qubits"])
    source_lines = [int(line) for line in packet["line_numbers"]]
    same_target_matches = [
        row
        for row in inventory_rows
        if int(row["qubit"]) in targets and same_abs_angle(float(row["angle"]), angle)
    ]

    candidate_rows = []
    for match in same_target_matches:
        source_line, distance = nearest_source(int(match["line_number"]), source_lines)
        blockers = segment_blockers(qasm_lines, int(match["line_number"]), source_line, targets)
        candidate_rows.append(
            {
                **compact_matches([match], limit=1)[0],
                "nearest_source_line": source_line,
                "source_distance": distance,
                "target_two_qubit_blocker_count": len(blockers),
                "target_two_qubit_blockers": blockers[:4],
                "target_blocker_free": len(blockers) == 0,
            }
        )
    candidate_rows.sort(
        key=lambda row: (
            int(row["source_distance"]),
            int(row["target_two_qubit_blocker_count"]),
            int(row["line_number"]),
        )
    )
    nearest = candidate_rows[0] if candidate_rows else None
    radius_counts = {
        f"same_target_within_{radius}_line_count": sum(
            1 for row in candidate_rows if int(row["source_distance"]) <= radius
        )
        for radius in NEIGHBORHOOD_RADII
    }
    radius_blocker_free_counts = {
        f"blocker_free_within_{radius}_line_count": sum(
            1
            for row in candidate_rows
            if int(row["source_distance"]) <= radius and bool(row["target_blocker_free"])
        )
        for radius in NEIGHBORHOOD_RADII
    }
    accepted_occurrence_removal = 0
    return {
        "pattern_id": ledger_row["pattern_id"],
        "occurrence_count": int(ledger_row["occurrence_count"]),
        "carrier_signature": ledger_row["carrier_signature"],
        "carrier_angle": angle,
        "target_qubits": sorted(targets),
        "source_line_numbers": source_lines,
        "same_target_inventory_match_count": len(candidate_rows),
        "nearest_same_target_distance": None if nearest is None else nearest["source_distance"],
        "nearest_same_target_match": nearest,
        **radius_counts,
        **radius_blocker_free_counts,
        "has_radius_4_candidate": radius_counts["same_target_within_4_line_count"] > 0,
        "has_radius_8_candidate": radius_counts["same_target_within_8_line_count"] > 0,
        "has_radius_16_candidate": radius_counts["same_target_within_16_line_count"] > 0,
        "has_blocker_free_radius_16_candidate": (
            radius_blocker_free_counts["blocker_free_within_16_line_count"] > 0
        ),
        "accepted_neighborhood_absorption_certificate": False,
        "accepted_occurrence_removal": accepted_occurrence_removal,
        "accepted_proxy_t_reduction": accepted_occurrence_removal * PROXY_T_PER_OCCURRENCE,
        "sample_neighborhood_candidates": candidate_rows[:6],
        "claim_boundary": (
            "A nearby same-target inventory match is a search hint only; it is not an "
            "adjacency, commutation, replay, semantic, or B7 resource certificate."
        ),
    }


def build_payload() -> dict[str, Any]:
    ledger = load_json(LEDGER_PATH)
    inventory_gate = load_json(INVENTORY_GATE_PATH)
    packets = {row["pattern_id"]: row for row in load_json(PACKET_PATH)["pattern_packets"]}
    inventory_rows = parse_rotation_inventory(INVENTORY_QASM_PATH)
    qasm_lines = parse_qasm_lines(INVENTORY_QASM_PATH)
    rows = [
        analyze_row(row, packets[row["pattern_id"]], inventory_rows, qasm_lines)
        for row in ledger.get("carrier_ledger_rows", [])
    ]
    accepted_removed = sum(row["accepted_occurrence_removal"] for row in rows)
    summary = {
        "source_method": ledger.get("method"),
        "source_status": ledger.get("status"),
        "source_inventory_method": inventory_gate.get("method"),
        "source_inventory_status": inventory_gate.get("status"),
        "inventory_qasm": display_path(INVENTORY_QASM_PATH),
        "pattern_group_count": len(rows),
        "covered_invariant_flat_occurrence_count": sum(row["occurrence_count"] for row in rows),
        "carrier_signature_count": len({row["carrier_signature"] for row in rows}),
        "same_target_inventory_match_pattern_count": sum(
            1 for row in rows if row["same_target_inventory_match_count"] > 0
        ),
        "radius_4_candidate_pattern_count": sum(1 for row in rows if row["has_radius_4_candidate"]),
        "radius_8_candidate_pattern_count": sum(1 for row in rows if row["has_radius_8_candidate"]),
        "radius_16_candidate_pattern_count": sum(1 for row in rows if row["has_radius_16_candidate"]),
        "blocker_free_radius_16_candidate_pattern_count": sum(
            1 for row in rows if row["has_blocker_free_radius_16_candidate"]
        ),
        "patterns_without_same_target_inventory_match": [
            row["pattern_id"] for row in rows if row["same_target_inventory_match_count"] == 0
        ],
        "patterns_without_radius_16_candidate": [
            row["pattern_id"] for row in rows if not row["has_radius_16_candidate"]
        ],
        "patterns_without_blocker_free_radius_16_candidate": [
            row["pattern_id"] for row in rows if not row["has_blocker_free_radius_16_candidate"]
        ],
        "all_patterns_have_radius_16_candidate": all(row["has_radius_16_candidate"] for row in rows),
        "all_patterns_have_blocker_free_radius_16_candidate": all(
            row["has_blocker_free_radius_16_candidate"] for row in rows
        ),
        "accepted_neighborhood_absorption_certificate_count": 0,
        "accepted_occurrence_removal": accepted_removed,
        "accepted_proxy_t_reduction": accepted_removed * PROXY_T_PER_OCCURRENCE,
        "missing_occurrences_after_gate": max(0, REQUIRED_OCCURRENCE_REMOVALS - accepted_removed),
        "missing_proxy_t_after_gate": max(0, REQUIRED_OCCURRENCE_REMOVALS - accepted_removed)
        * PROXY_T_PER_OCCURRENCE,
        "neighborhood_absorption_certificate_claimed": False,
        "commutation_certificate_claimed": False,
        "carrier_ledger_reduction_claimed": False,
        "rewrite_claimed": False,
        "semantic_certificate_claimed": False,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "validation_error_count": None,
    }
    payload = {
        "benchmark_id": "B1",
        "problem_id": 25,
        "linked_b7_problem_id": 21,
        "title": "B1/B7 cone_01 carrier neighborhood commutation gate",
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "method": METHOD,
        "source_result": display_path(LEDGER_PATH),
        "source_inventory_result": display_path(INVENTORY_GATE_PATH),
        "source_method": ledger.get("method"),
        "source_inventory_method": inventory_gate.get("method"),
        "workload": ledger.get("workload", "qasmbench_medium_exact/gcm_h6.qasm"),
        "summary": summary,
        "carrier_neighborhood_rows": rows,
        "claim_boundary": {
            "neighborhood_absorption_certificate_claimed": False,
            "commutation_certificate_claimed": False,
            "carrier_ledger_reduction_claimed": False,
            "rewrite_claimed": False,
            "semantic_certificate_claimed": False,
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "supported_claim": (
                "Only one carrier pattern has a same-target inventory match within 16 lines; "
                "the carrier neighborhood evidence does not cover all three residual packets."
            ),
            "unsupported_claims": [
                "A nearby match is not an absorption certificate.",
                "No commutation or semantic replay certificate is produced.",
                "No carrier occurrence is removed from the accepted B7 ledger.",
            ],
        },
    }
    errors = validate(payload)
    payload["summary"]["validation_error_count"] = len(errors)
    payload["validation_errors"] = errors
    return payload


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = payload["summary"]
    claims = payload["claim_boundary"]
    if payload.get("method") != METHOD:
        errors.append("method_mismatch")
    if payload.get("status") != STATUS:
        errors.append("status_mismatch")
    if payload.get("source_method") != "b1_b7_cone01_single_carrier_ledger_gate_v0":
        errors.append("source_method_mismatch")
    if payload.get("source_inventory_method") != "b1_b7_cone01_carrier_absorption_inventory_gate_v0":
        errors.append("source_inventory_method_mismatch")
    expected = {
        "pattern_group_count": 3,
        "covered_invariant_flat_occurrence_count": 11,
        "carrier_signature_count": 3,
        "same_target_inventory_match_pattern_count": 2,
        "radius_4_candidate_pattern_count": 0,
        "radius_8_candidate_pattern_count": 1,
        "radius_16_candidate_pattern_count": 1,
        "blocker_free_radius_16_candidate_pattern_count": 1,
        "accepted_neighborhood_absorption_certificate_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": 30,
        "missing_proxy_t_after_gate": 600,
    }
    for field, value in expected.items():
        if summary.get(field) != value:
            errors.append(f"{field}_mismatch")
    if summary.get("patterns_without_same_target_inventory_match") != ["flat_pattern_02"]:
        errors.append("patterns_without_same_target_inventory_match_mismatch")
    if summary.get("patterns_without_radius_16_candidate") != ["flat_pattern_02", "flat_pattern_03"]:
        errors.append("patterns_without_radius_16_candidate_mismatch")
    if summary.get("patterns_without_blocker_free_radius_16_candidate") != [
        "flat_pattern_02",
        "flat_pattern_03",
    ]:
        errors.append("patterns_without_blocker_free_radius_16_candidate_mismatch")
    if summary.get("all_patterns_have_radius_16_candidate") is not False:
        errors.append("radius_16_must_not_cover_all_patterns")
    if summary.get("all_patterns_have_blocker_free_radius_16_candidate") is not False:
        errors.append("blocker_free_radius_16_must_not_cover_all_patterns")
    expected_distances = {
        "flat_pattern_01": 8,
        "flat_pattern_02": None,
        "flat_pattern_03": 99,
    }
    for row in payload.get("carrier_neighborhood_rows", []):
        pattern_id = row.get("pattern_id")
        if row.get("nearest_same_target_distance") != expected_distances.get(pattern_id):
            errors.append(f"{pattern_id}_nearest_distance_mismatch")
        if row.get("accepted_neighborhood_absorption_certificate") is not False:
            errors.append(f"{pattern_id}_accepted_neighborhood_certificate_must_be_false")
        if row.get("accepted_occurrence_removal") != 0:
            errors.append(f"{pattern_id}_accepted_removal_must_be_zero")
    for field in [
        "neighborhood_absorption_certificate_claimed",
        "commutation_certificate_claimed",
        "carrier_ledger_reduction_claimed",
        "rewrite_claimed",
        "semantic_certificate_claimed",
        "resource_saving_claimed",
        "b7_ledger_improvement_claimed",
    ]:
        if summary.get(field) is not False:
            errors.append(f"{field}_must_remain_false")
        if claims.get(field) is not False:
            errors.append(f"claim_boundary_{field}_must_remain_false")
    return errors


def markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone_01 Carrier Neighborhood Commutation Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This artifact consumes T-B1-004x and checks whether same-target carrier inventory matches are local enough to motivate an absorption certificate.",
        "",
        "## Summary",
        "",
        f"- Pattern groups / covered occurrences: `{summary['pattern_group_count']}` / `{summary['covered_invariant_flat_occurrence_count']}`",
        f"- Same-target inventory-match patterns: `{summary['same_target_inventory_match_pattern_count']}` / `{summary['pattern_group_count']}`",
        f"- Radius 4 / 8 / 16 candidate patterns: `{summary['radius_4_candidate_pattern_count']}` / `{summary['radius_8_candidate_pattern_count']}` / `{summary['radius_16_candidate_pattern_count']}`",
        f"- Blocker-free radius-16 candidate patterns: `{summary['blocker_free_radius_16_candidate_pattern_count']}`",
        f"- Patterns without radius-16 candidate: `{', '.join(summary['patterns_without_radius_16_candidate'])}`",
        f"- Accepted occurrence/proxy-T reduction: `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        f"- Validation errors: `{summary['validation_error_count']}`",
        "",
        "## Rows",
        "",
        "| Pattern | Occurrences | Same-target matches | Nearest distance | Radius 16 | Blocker-free radius 16 | Accepted reduction |",
        "|---|---:|---:|---:|---|---|---:|",
    ]
    for row in payload["carrier_neighborhood_rows"]:
        lines.append(
            f"| {row['pattern_id']} | {row['occurrence_count']} | "
            f"{row['same_target_inventory_match_count']} | {row['nearest_same_target_distance']} | "
            f"{row['has_radius_16_candidate']} | {row['has_blocker_free_radius_16_candidate']} | "
            f"{row['accepted_proxy_t_reduction']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- Nearby same-target inventory matches are search hints only.",
            "- The gate does not prove adjacency, commutation, or semantic replay.",
            "- Only `flat_pattern_01` has a radius-16 same-target neighborhood candidate.",
            "- No neighborhood absorption certificate or B7 ledger improvement is claimed.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=MD_OUT)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    payload = build_payload()
    write_json(args.json_out, payload, args.pretty)
    write_text(args.md_out, markdown(payload))
    print(json.dumps(payload["summary"], indent=2 if args.pretty else None, sort_keys=True))


if __name__ == "__main__":
    main()
