#!/usr/bin/env python3
"""CNOT-parity clearance gate for B1/B7 cone_01 carrier blockers.

T-B1-004ab showed that the blocked source-aligned carrier candidates do not
share one reusable blocker motif. This gate asks a narrower semantic question:
can any source-aligned blocker stack be cleared by cheap CNOT parity or adjacent
duplicate-CNOT cancellation before doing broader two-qubit synthesis?

The current answer is negative. One candidate has even CNOT parity if all
interleaved gates are ignored, but repeated CNOTs are separated by target-qubit
single-qubit gates. The other two candidates have odd blocker parity. No
occurrence-removing rewrite or B7 resource saving is accepted.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from b1_b7_cone01_carrier_absorption_inventory_gate import (
    INVENTORY_QASM_PATH,
    PROXY_T_PER_OCCURRENCE,
    REQUIRED_OCCURRENCE_REMOVALS,
    display_path,
    load_json,
    write_json,
    write_text,
)


ROOT = Path(__file__).resolve().parents[1]
BLOCKER_STACK_GATE_PATH = ROOT / "results" / "B1_B7_cone01_carrier_blocker_stack_gate_v0.json"
JSON_OUT = ROOT / "results" / "B1_B7_cone01_carrier_blocker_parity_gate_v0.json"
MD_OUT = ROOT / "research" / "B1_B7_cone01_carrier_blocker_parity_gate.md"

METHOD = "b1_b7_cone01_carrier_blocker_parity_gate_v0"
STATUS = "cone01_carrier_blocker_parity_negative_gate"
MODEL_STATUS = "blocker_stacks_do_not_admit_cheap_cnot_parity_clearance"

SINGLE_QUBIT_RE = re.compile(r"^(?:u3|rz|rx|ry|u1|u2|u)\([^)]*\) q\[(\d+)\];$")
CX_RE = re.compile(r"^cx q\[(\d+)\],q\[(\d+)\];$")


def parse_qasm_lines(path: Path) -> dict[int, str]:
    return {idx: line.strip() for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)}


def single_qubit_target_op(line: str, qubits: set[int]) -> bool:
    match = SINGLE_QUBIT_RE.match(line.strip())
    return bool(match and int(match.group(1)) in qubits)


def target_touching_cx(line: str, qubits: set[int]) -> bool:
    match = CX_RE.match(line.strip())
    if not match:
        return False
    return bool({int(match.group(1)), int(match.group(2))}.intersection(qubits))


def interleaving_stats(
    qasm_lines: dict[int, str],
    left_line: int,
    right_line: int,
    edge_qubits: set[int],
    target_qubits: set[int],
) -> dict[str, Any]:
    between = range(min(left_line, right_line) + 1, max(left_line, right_line))
    target_single_lines = []
    target_touching_cx_lines = []
    nonempty_lines = []
    for line_number in between:
        text = qasm_lines.get(line_number, "")
        if not text:
            continue
        nonempty_lines.append(line_number)
        if single_qubit_target_op(text, edge_qubits):
            target_single_lines.append(line_number)
        if target_touching_cx(text, target_qubits):
            target_touching_cx_lines.append(line_number)
    return {
        "line_span": [min(left_line, right_line), max(left_line, right_line)],
        "intervening_line_count": len(nonempty_lines),
        "target_single_qubit_line_count": len(target_single_lines),
        "target_touching_cx_line_count": len(target_touching_cx_lines),
        "target_single_qubit_lines": target_single_lines,
        "target_touching_cx_lines": target_touching_cx_lines,
        "clean_for_adjacent_cnot_cancel": not target_single_lines and not target_touching_cx_lines,
    }


def analyze_candidate(
    candidate: dict[str, Any],
    qasm_lines: dict[int, str],
    target_qubits: set[int],
) -> dict[str, Any]:
    blockers = candidate.get("target_cx_blockers", [])
    edge_counts = Counter(blocker["edge_signature"] for blocker in blockers)
    odd_edges = sorted(edge for edge, count in edge_counts.items() if count % 2)
    repeated_pairs = []
    clean_pairs = []
    blocked_pairs = []
    for left, right in zip(blockers, blockers[1:]):
        if left["edge_signature"] != right["edge_signature"]:
            continue
        edge_qubits = set(left["qubits"])
        stats = interleaving_stats(
            qasm_lines=qasm_lines,
            left_line=int(left["line_number"]),
            right_line=int(right["line_number"]),
            edge_qubits=edge_qubits,
            target_qubits=target_qubits,
        )
        pair = {
            "edge_signature": left["edge_signature"],
            "left_blocker_line": int(left["line_number"]),
            "right_blocker_line": int(right["line_number"]),
            **stats,
        }
        repeated_pairs.append(pair)
        if pair["clean_for_adjacent_cnot_cancel"]:
            clean_pairs.append(pair)
        else:
            blocked_pairs.append(pair)

    cnot_only_parity_identity = not odd_edges and bool(blockers)
    accepted = cnot_only_parity_identity and len(clean_pairs) >= len(blockers) // 2
    if accepted:
        rejection_reason = "accepted"
    elif cnot_only_parity_identity:
        rejection_reason = "cnot-only parity is even but repeated blockers are separated by target-qubit operations"
    else:
        rejection_reason = "blocker CNOT parity has odd edge counts"
    return {
        "candidate_line_number": int(candidate["candidate_line_number"]),
        "candidate_qubit": int(candidate["candidate_qubit"]),
        "nearest_source_line": int(candidate["nearest_source_line"]),
        "source_distance": int(candidate["source_distance"]),
        "stack_length": len(blockers),
        "edge_counts": dict(sorted(edge_counts.items())),
        "odd_parity_edge_signatures": odd_edges,
        "cnot_only_parity_identity": cnot_only_parity_identity,
        "repeated_same_edge_pair_count": len(repeated_pairs),
        "clean_adjacent_cnot_cancel_pair_count": len(clean_pairs),
        "blocked_repeated_pair_count": len(blocked_pairs),
        "target_single_qubit_between_repeated_pair_count": sum(
            pair["target_single_qubit_line_count"] for pair in repeated_pairs
        ),
        "target_touching_cx_between_repeated_pair_count": sum(
            pair["target_touching_cx_line_count"] for pair in repeated_pairs
        ),
        "repeated_same_edge_pairs": repeated_pairs,
        "parity_clearance_accepted": accepted,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "rejection_reason": rejection_reason,
    }


def analyze_row(row: dict[str, Any], qasm_lines: dict[int, str]) -> dict[str, Any]:
    target_qubits = set(int(q) for q in row["target_qubits"])
    candidate_rows = [
        analyze_candidate(candidate, qasm_lines, target_qubits)
        for candidate in row.get("source_aligned_candidates", [])
    ]
    return {
        "pattern_id": row["pattern_id"],
        "occurrence_count": int(row["occurrence_count"]),
        "target_qubits": sorted(target_qubits),
        "parity_candidate_count": len(candidate_rows),
        "cnot_only_parity_identity_candidate_count": sum(
            1 for candidate in candidate_rows if candidate["cnot_only_parity_identity"]
        ),
        "odd_cnot_parity_candidate_count": sum(
            1 for candidate in candidate_rows if candidate["odd_parity_edge_signatures"]
        ),
        "repeated_same_edge_pair_count": sum(
            candidate["repeated_same_edge_pair_count"] for candidate in candidate_rows
        ),
        "clean_adjacent_cnot_cancel_pair_count": sum(
            candidate["clean_adjacent_cnot_cancel_pair_count"] for candidate in candidate_rows
        ),
        "target_single_qubit_between_repeated_pair_count": sum(
            candidate["target_single_qubit_between_repeated_pair_count"] for candidate in candidate_rows
        ),
        "accepted_parity_clearance_count": sum(
            1 for candidate in candidate_rows if candidate["parity_clearance_accepted"]
        ),
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "parity_candidates": candidate_rows,
        "claim_boundary": (
            "CNOT parity grouping is a cheap-clearance diagnostic only; it is not a "
            "semantic CNOT-stack rewrite, replay certificate, or B7 resource certificate."
        ),
    }


def build_payload() -> dict[str, Any]:
    source = load_json(BLOCKER_STACK_GATE_PATH)
    qasm_lines = parse_qasm_lines(INVENTORY_QASM_PATH)
    rows = [analyze_row(row, qasm_lines) for row in source.get("carrier_blocker_stack_rows", [])]
    candidates = [candidate for row in rows for candidate in row["parity_candidates"]]
    accepted_removed = sum(row["accepted_occurrence_removal"] for row in rows)
    summary = {
        "source_method": source.get("method"),
        "source_status": source.get("status"),
        "inventory_qasm": display_path(INVENTORY_QASM_PATH),
        "pattern_group_count": len(rows),
        "covered_invariant_flat_occurrence_count": sum(row["occurrence_count"] for row in rows),
        "source_aligned_candidate_count": source.get("summary", {}).get("source_aligned_candidate_count"),
        "parity_candidate_count": len(candidates),
        "cnot_only_parity_identity_candidate_count": sum(
            1 for candidate in candidates if candidate["cnot_only_parity_identity"]
        ),
        "odd_cnot_parity_candidate_count": sum(
            1 for candidate in candidates if candidate["odd_parity_edge_signatures"]
        ),
        "repeated_same_edge_pair_count": sum(
            candidate["repeated_same_edge_pair_count"] for candidate in candidates
        ),
        "clean_adjacent_cnot_cancel_pair_count": sum(
            candidate["clean_adjacent_cnot_cancel_pair_count"] for candidate in candidates
        ),
        "target_single_qubit_between_repeated_pair_count": sum(
            candidate["target_single_qubit_between_repeated_pair_count"] for candidate in candidates
        ),
        "target_touching_cx_between_repeated_pair_count": sum(
            candidate["target_touching_cx_between_repeated_pair_count"] for candidate in candidates
        ),
        "cnot_only_parity_identity_but_interleaved_candidate_count": sum(
            1
            for candidate in candidates
            if candidate["cnot_only_parity_identity"]
            and candidate["target_single_qubit_between_repeated_pair_count"] > 0
        ),
        "accepted_parity_clearance_count": sum(
            1 for candidate in candidates if candidate["parity_clearance_accepted"]
        ),
        "parity_clearance_gate_passed": False,
        "accepted_occurrence_removal": accepted_removed,
        "accepted_proxy_t_reduction": accepted_removed * PROXY_T_PER_OCCURRENCE,
        "missing_occurrences_after_gate": max(0, REQUIRED_OCCURRENCE_REMOVALS - accepted_removed),
        "missing_proxy_t_after_gate": max(0, REQUIRED_OCCURRENCE_REMOVALS - accepted_removed)
        * PROXY_T_PER_OCCURRENCE,
        "cnot_parity_rewrite_claimed": False,
        "semantic_certificate_claimed": False,
        "rewrite_claimed": False,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "validation_error_count": None,
    }
    payload = {
        "benchmark_id": "B1",
        "problem_id": 25,
        "linked_b7_problem_id": 21,
        "title": "B1/B7 cone_01 carrier blocker CNOT parity gate",
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "method": METHOD,
        "source_result": display_path(BLOCKER_STACK_GATE_PATH),
        "source_method": source.get("method"),
        "workload": source.get("workload", "qasmbench_medium_exact/gcm_h6.qasm"),
        "summary": summary,
        "carrier_blocker_parity_rows": rows,
        "claim_boundary": {
            "cnot_parity_rewrite_claimed": False,
            "semantic_certificate_claimed": False,
            "rewrite_claimed": False,
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "supported_claim": (
                "The current source-aligned blocker stacks do not admit cheap CNOT parity "
                "or adjacent-duplicate clearance."
            ),
            "unsupported_claims": [
                "No CNOT-stack semantic rewrite is produced.",
                "No replay certificate is produced.",
                "No occurrence is removed from the B7 ledger.",
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
    expected = {
        "pattern_group_count": 3,
        "covered_invariant_flat_occurrence_count": 11,
        "source_aligned_candidate_count": 3,
        "parity_candidate_count": 3,
        "cnot_only_parity_identity_candidate_count": 1,
        "odd_cnot_parity_candidate_count": 2,
        "clean_adjacent_cnot_cancel_pair_count": 0,
        "cnot_only_parity_identity_but_interleaved_candidate_count": 1,
        "accepted_parity_clearance_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": 30,
        "missing_proxy_t_after_gate": 600,
    }
    if payload.get("method") != METHOD:
        errors.append("method_mismatch")
    if payload.get("status") != STATUS:
        errors.append("status_mismatch")
    if payload.get("source_method") != "b1_b7_cone01_carrier_blocker_stack_gate_v0":
        errors.append("source_method_mismatch")
    for field, value in expected.items():
        if summary.get(field) != value:
            errors.append(f"{field}_mismatch")
    if summary.get("repeated_same_edge_pair_count", 0) <= 0:
        errors.append("repeated_same_edge_pair_count_must_be_positive")
    if summary.get("target_single_qubit_between_repeated_pair_count", 0) <= 0:
        errors.append("target_single_qubit_between_repeated_pair_count_must_be_positive")
    for field in [
        "parity_clearance_gate_passed",
        "cnot_parity_rewrite_claimed",
        "semantic_certificate_claimed",
        "rewrite_claimed",
        "resource_saving_claimed",
        "b7_ledger_improvement_claimed",
    ]:
        if summary.get(field) is not False:
            errors.append(f"{field}_must_remain_false")
    for field in [
        "cnot_parity_rewrite_claimed",
        "semantic_certificate_claimed",
        "rewrite_claimed",
        "resource_saving_claimed",
        "b7_ledger_improvement_claimed",
    ]:
        if payload["claim_boundary"].get(field) is not False:
            errors.append(f"claim_boundary_{field}_must_remain_false")
    for row in payload.get("carrier_blocker_parity_rows", []):
        if row.get("accepted_occurrence_removal") != 0:
            errors.append(f"{row.get('pattern_id')}_accepted_removal_must_be_zero")
        for candidate in row.get("parity_candidates", []):
            if candidate.get("parity_clearance_accepted"):
                errors.append(f"{row.get('pattern_id')}_{candidate.get('candidate_line_number')}_accepted")
    return errors


def markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone_01 Carrier Blocker CNOT Parity Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This artifact consumes T-B1-004aa/T-B1-004ab and checks whether the blocked source-aligned carrier stacks can be cleared by cheap CNOT parity or adjacent duplicate-CNOT cancellation.",
        "",
        "## Summary",
        "",
        f"- Parity candidates: `{summary['parity_candidate_count']}`",
        f"- CNOT-only parity identity candidates: `{summary['cnot_only_parity_identity_candidate_count']}`",
        f"- Odd CNOT parity candidates: `{summary['odd_cnot_parity_candidate_count']}`",
        f"- Repeated same-edge blocker pairs: `{summary['repeated_same_edge_pair_count']}`",
        f"- Clean adjacent CNOT cancel pairs: `{summary['clean_adjacent_cnot_cancel_pair_count']}`",
        f"- Target single-qubit ops between repeated pairs: `{summary['target_single_qubit_between_repeated_pair_count']}`",
        f"- CNOT-only parity identity but interleaved candidates: `{summary['cnot_only_parity_identity_but_interleaved_candidate_count']}`",
        f"- Parity clearance gate passed: `{summary['parity_clearance_gate_passed']}`",
        f"- Accepted occurrence/proxy-T reduction: `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        f"- Validation errors: `{summary['validation_error_count']}`",
        "",
        "## Candidate Rows",
        "",
        "| Pattern | Candidate line | Edge counts | CNOT-only parity identity | Clean cancel pairs | Rejection |",
        "|---|---:|---|---:|---:|---|",
    ]
    for row in payload["carrier_blocker_parity_rows"]:
        for candidate in row["parity_candidates"]:
            lines.append(
                "| "
                f"{row['pattern_id']} | "
                f"{candidate['candidate_line_number']} | "
                f"`{candidate['edge_counts']}` | "
                f"{candidate['cnot_only_parity_identity']} | "
                f"{candidate['clean_adjacent_cnot_cancel_pair_count']} | "
                f"{candidate['rejection_reason']} |"
            )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This is a negative cheap-clearance gate. It does not prove that no semantic CNOT-stack rewrite exists. It only rejects the cheap route where repeated blocker CNOTs can be removed by parity or adjacent duplicate cancellation without handling the intervening target-qubit operations.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=JSON_OUT)
    parser.add_argument("--md-out", type=Path, default=MD_OUT)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    payload = build_payload()
    write_json(args.json_out, payload, args.pretty)
    write_text(args.md_out, markdown(payload))
    if args.pretty:
        print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    if payload["validation_errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
