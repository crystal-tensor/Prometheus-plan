#!/usr/bin/env python3
"""Logical layout/routing scaffold for B1/B7 cone_01 shared-theta objects.

This gate consumes the shared-theta replay verifier and assigns each shared
object to a simple logical anchor on the source QASM qubit line.  It enumerates
which replayed occurrences consume each shared object and the logical route
from the anchor to each consumer qubit.  This is CM-04 scaffolding only: it is
not a physical layout, factory model, semantic rewrite, or B7 resource claim.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median
from typing import Any


METHOD = "b1_b7_cone01_shared_theta_layout_routing_gate_v0"
STATUS = "cone01_shared_theta_logical_layout_routing_scaffold"
MODEL_STATUS = "logical_layout_routing_scaffold_not_physical_layout"
VERSION = "0.1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def display_path(path: Path) -> str:
    root = Path(__file__).resolve().parents[1]
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(root))
    except ValueError:
        return str(path)


def line_path(anchor: int, consumer: int) -> list[int]:
    step = 1 if consumer >= anchor else -1
    return list(range(anchor, consumer + step, step))


def choose_anchor(qubits: list[int]) -> int:
    counts = Counter(qubits)
    med = median(qubits)
    return min(counts, key=lambda qubit: (-counts[qubit], abs(qubit - med), qubit))


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    replay = read_json(args.replay_verifier_gate)
    replay_summary = replay["summary"]
    route_rows = []
    total_route_hops = 0
    max_route_hops = 0
    missing_route_count = 0
    object_count_with_anchor = 0
    occurrence_count_with_route = 0
    line_qubits: set[int] = set()

    for replay_row in replay["object_replay_rows"]:
        replayed = [row for row in replay_row["replayed_lines"] if row.get("qasm_line_found") is True]
        qubits = [int(row["qubit"]) for row in replayed]
        if not qubits:
            missing_route_count += int(replay_row["covered_line_count"])
            route_rows.append(
                {
                    "object_id": replay_row["object_id"],
                    "logical_anchor_qubit": None,
                    "route_packet_count": 0,
                    "layout_route_complete": False,
                    "route_packets": [],
                }
            )
            continue

        anchor = choose_anchor(qubits)
        object_count_with_anchor += 1
        packets = []
        object_total_hops = 0
        object_max_hops = 0
        for row in replayed:
            consumer = int(row["qubit"])
            path = line_path(anchor, consumer)
            hops = max(0, len(path) - 1)
            total_route_hops += hops
            object_total_hops += hops
            max_route_hops = max(max_route_hops, hops)
            object_max_hops = max(object_max_hops, hops)
            occurrence_count_with_route += 1
            line_qubits.update(path)
            packets.append(
                {
                    "line_number": int(row["line_number"]),
                    "consumer_qubit": consumer,
                    "logical_anchor_qubit": anchor,
                    "logical_line_path": path,
                    "logical_hop_count": hops,
                    "canonical_theta_matches_object": row["canonical_theta_matches_object"],
                }
            )

        route_rows.append(
            {
                "object_id": replay_row["object_id"],
                "canonical_theta": replay_row["canonical_theta"],
                "logical_anchor_qubit": anchor,
                "consumer_qubit_count": len(set(qubits)),
                "route_packet_count": len(packets),
                "total_logical_hop_count": object_total_hops,
                "max_logical_hop_count": object_max_hops,
                "layout_route_complete": len(packets) == int(replay_row["covered_line_count"]),
                "physical_layout_assigned": False,
                "factory_amortization_model_present": False,
                "route_packets": packets,
            }
        )

    layout_gate_passed = (
        replay_summary["shared_theta_replay_gate_passed"] is True
        and object_count_with_anchor == int(replay_summary["shared_synthesis_object_count"])
        and occurrence_count_with_route == int(replay_summary["replayed_occurrence_count"])
        and missing_route_count == 0
        and all(row.get("layout_route_complete") is True for row in route_rows)
    )

    payload = {
        "benchmark_id": "B1",
        "problem_id": 25,
        "linked_b7_problem_id": 21,
        "title": "B1/B7 cone_01 shared-theta logical layout/routing scaffold",
        "version": VERSION,
        "last_updated": args.last_updated,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "method": METHOD,
        "source_shared_theta_replay_verifier_gate": display_path(args.replay_verifier_gate),
        "workload": "qasmbench_medium_exact/gcm_h6.qasm",
        "summary": {
            "candidate_window_count": int(replay_summary["candidate_window_count"]),
            "shared_synthesis_object_count": int(replay_summary["shared_synthesis_object_count"]),
            "replay_verified_object_count": int(replay_summary["replay_verified_object_count"]),
            "replayed_occurrence_count": int(replay_summary["replayed_occurrence_count"]),
            "layout_routed_object_count": object_count_with_anchor,
            "layout_routed_occurrence_count": occurrence_count_with_route,
            "logical_anchor_object_count": object_count_with_anchor,
            "logical_route_packet_count": occurrence_count_with_route,
            "logical_line_topology_qubit_count": len(line_qubits),
            "total_logical_hop_count": total_route_hops,
            "max_logical_hop_count": max_route_hops,
            "missing_route_count": missing_route_count,
            "layout_routing_gate_passed": layout_gate_passed,
            "physical_layout_claimed": False,
            "factory_amortization_model_present": False,
            "shared_error_budget_present": False,
            "semantic_rewrite_verified": False,
            "semantic_certificate_claimed": False,
            "occurrence_ledger_removed_occurrences": 0,
            "occurrence_ledger_proxy_t_reduction": 0,
            "cost_model_accepted": False,
            "rewrite_claimed": False,
            "resource_saving_claimed": False,
            "physical_resource_reduction_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "validation_error_count": None,
        },
        "layout_route_rows": route_rows,
        "claim_boundary": {
            "cost_model_accepted": False,
            "physical_layout_claimed": False,
            "semantic_rewrite_verified": False,
            "rewrite_claimed": False,
            "resource_saving_claimed": False,
            "semantic_certificate_claimed": False,
            "physical_resource_reduction_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "supported_claim": (
                "Each replay-verified shared-theta object now has an explicit logical anchor "
                "and a replayed occurrence-to-anchor route packet under a source-QASM line "
                "topology scaffold."
            ),
            "unsupported_claims": [
                "No physical device layout is claimed.",
                "No factory-amortization or error-budget model is supplied.",
                "No occurrence-removing semantic rewrite is verified.",
                "No B7 ledger reduction is counted.",
            ],
            "next_gate": (
                "Use this as CM-04 logical routing evidence, then build CM-05 factory "
                "amortization and CM-06 shared-error budget evidence before any physical "
                "theta-sharing cost model can be accepted."
            ),
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
        errors.append("method mismatch")
    if payload.get("status") != STATUS:
        errors.append("status mismatch")
    if payload.get("model_status") != MODEL_STATUS:
        errors.append("model_status mismatch")
    if summary["candidate_window_count"] != 35:
        errors.append("expected 35 candidate windows")
    if summary["shared_synthesis_object_count"] != 4:
        errors.append("expected 4 shared synthesis objects")
    if summary["replay_verified_object_count"] != 4:
        errors.append("expected 4 replay-verified shared objects")
    if summary["replayed_occurrence_count"] != 35:
        errors.append("expected 35 replayed occurrences")
    if summary["layout_routed_object_count"] != 4:
        errors.append("expected routes for all 4 objects")
    if summary["layout_routed_occurrence_count"] != 35:
        errors.append("expected routes for all 35 occurrences")
    if summary["logical_route_packet_count"] != 35:
        errors.append("expected 35 logical route packets")
    if summary["missing_route_count"] != 0:
        errors.append("missing route packets must be zero")
    if summary["layout_routing_gate_passed"] is not True:
        errors.append("layout/routing scaffold should pass")
    if summary["logical_line_topology_qubit_count"] <= 0:
        errors.append("logical topology must include at least one qubit")
    if summary["max_logical_hop_count"] <= 0:
        errors.append("expected nonzero logical route pressure")
    for field in [
        "physical_layout_claimed",
        "factory_amortization_model_present",
        "shared_error_budget_present",
        "semantic_rewrite_verified",
        "semantic_certificate_claimed",
        "cost_model_accepted",
        "rewrite_claimed",
        "resource_saving_claimed",
        "physical_resource_reduction_claimed",
        "b7_ledger_improvement_claimed",
    ]:
        if summary.get(field) is not False:
            errors.append(f"{field} must remain false in summary")
        if field in claims and claims.get(field) is not False:
            errors.append(f"{field} must remain false in claim boundary")
    if summary["occurrence_ledger_removed_occurrences"] != 0:
        errors.append("occurrence ledger removals must remain zero")
    if summary["occurrence_ledger_proxy_t_reduction"] != 0:
        errors.append("occurrence ledger proxy-T reduction must remain zero")
    for row in payload["layout_route_rows"]:
        if row.get("layout_route_complete") is not True:
            errors.append(f"{row.get('object_id')} route is incomplete")
        if row.get("physical_layout_assigned") is not False:
            errors.append(f"{row.get('object_id')} must not claim physical layout")
        if row.get("factory_amortization_model_present") is not False:
            errors.append(f"{row.get('object_id')} must not claim factory model")
    return errors


def markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone_01 Shared-Theta Logical Layout/Routing Scaffold",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This artifact gives the replay-verified shared-theta objects an explicit "
        "logical routing scaffold. It assigns one logical anchor qubit per shared "
        "object and enumerates route packets from that anchor to each consuming "
        "source-QASM occurrence.",
        "",
        "It is not a physical layout, not a factory-amortization model, not a "
        "semantic rewrite certificate, and not a B7 resource-saving claim.",
        "",
        "## Summary",
        "",
        f"- Candidate windows: `{summary['candidate_window_count']}`",
        f"- Shared objects: `{summary['shared_synthesis_object_count']}`",
        f"- Replay-verified objects: `{summary['replay_verified_object_count']}`",
        f"- Replayed occurrences: `{summary['replayed_occurrence_count']}`",
        f"- Layout-routed objects: `{summary['layout_routed_object_count']}`",
        f"- Layout-routed occurrences: `{summary['layout_routed_occurrence_count']}`",
        f"- Logical route packets: `{summary['logical_route_packet_count']}`",
        f"- Logical line-topology qubits touched: `{summary['logical_line_topology_qubit_count']}`",
        f"- Total logical hops: `{summary['total_logical_hop_count']}`",
        f"- Max logical hops: `{summary['max_logical_hop_count']}`",
        f"- Missing route packets: `{summary['missing_route_count']}`",
        f"- Layout/routing gate passed: `{summary['layout_routing_gate_passed']}`",
        f"- Physical layout claimed: `{summary['physical_layout_claimed']}`",
        f"- Cost model accepted: `{summary['cost_model_accepted']}`",
        f"- B7 ledger improvement claimed: `{summary['b7_ledger_improvement_claimed']}`",
        f"- Validation errors: `{summary['validation_error_count']}`",
        "",
        "## Object Routes",
        "",
        "| object | anchor qubit | route packets | total logical hops | max logical hops | complete |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in payload["layout_route_rows"]:
        lines.append(
            f"| {row['object_id']} | `{row['logical_anchor_qubit']}` | `{row['route_packet_count']}` | "
            f"`{row['total_logical_hop_count']}` | `{row['max_logical_hop_count']}` | "
            f"`{row['layout_route_complete']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "CM-04 now has explicit logical route packets for every replay-verified "
            "shared-theta occurrence. This is still weaker than a physical layout: "
            "it does not allocate device qubits, schedule movement, model distillation "
            "factories, or price correlated synthesis error. The cost model must remain "
            "unaccepted until later gates supply that evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--replay-verifier-gate",
        type=Path,
        default=root / "results" / "B1_B7_cone01_shared_theta_replay_verifier_gate_v0.json",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=root / "results" / "B1_B7_cone01_shared_theta_layout_routing_gate_v0.json",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=root / "research" / "B1_B7_cone01_shared_theta_layout_routing_gate.md",
    )
    parser.add_argument("--last-updated", default="2026-06-18")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    write_text(args.markdown_output, markdown(payload))
    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"Wrote {args.json_output}")
        print(f"Wrote {args.markdown_output}")


if __name__ == "__main__":
    main()
