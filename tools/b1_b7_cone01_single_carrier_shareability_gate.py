#!/usr/bin/env python3
"""Shareability gate for B1/B7 cone_01 single-carrier packets.

T-B1-004u found one-carrier exact packets and T-B1-004v showed that the
current occurrence ledger treats them as replacement, not removal. This gate
asks the next accounting question: can the carriers be merged into shared
carrier objects that are strong enough to clear the B7 target?

The answer is still negative for the current evidence. The three residual
packets use three distinct carrier signatures. Within-pattern reuse gives an
optimistic 160 proxy-T signal, but no cross-pattern carrier coalescence exists,
the accepted ledger remains zero, and even accepting all carrier signatures
would cover only 11 of the 30 required occurrence removals.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = ROOT / "results" / "B1_B7_cone01_single_carrier_ledger_gate_v0.json"
JSON_OUT = ROOT / "results" / "B1_B7_cone01_single_carrier_shareability_gate_v0.json"
MD_OUT = ROOT / "research" / "B1_B7_cone01_single_carrier_shareability_gate.md"

METHOD = "b1_b7_cone01_single_carrier_shareability_gate_v0"
STATUS = "cone01_single_carrier_shareability_negative_gate"
MODEL_STATUS = "distinct_carrier_signatures_do_not_coalesce_into_accepted_resource_model"
PROXY_T_PER_OCCURRENCE = 20
REQUIRED_OCCURRENCE_REMOVALS = 30


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def markdown_cell(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|")


def object_key(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row["carrier_source"]),
            str(row["carrier_coefficient"]),
            str(row["carrier_axis"]),
            str(row["carrier_local_role"]),
            str(row["carrier_side"]),
            str(row["left_pair_label"]),
            str(row["right_pair_label"]),
            f"{float(row['carrier_angle']):.12g}",
        ]
    )


def relaxed_key(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row["carrier_source"]),
            str(row["carrier_axis"]),
            str(row["carrier_local_role"]),
        ]
    )


def build_payload() -> dict[str, Any]:
    ledger = load_json(LEDGER_PATH)
    ledger_summary = ledger.get("summary", {})
    rows = ledger.get("carrier_ledger_rows", [])

    by_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_relaxed: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_signature[object_key(row)].append(row)
        by_relaxed[relaxed_key(row)].append(row)

    share_rows = []
    for signature, members in sorted(by_signature.items()):
        occurrence_count = sum(int(member["occurrence_count"]) for member in members)
        pattern_ids = [str(member["pattern_id"]) for member in members]
        line_model_originals = sum(int(member["line_model_original_arbitrary_occurrences"]) for member in members)
        optimistic_saved = max(0, occurrence_count - 1)
        share_rows.append(
            {
                "carrier_signature": signature,
                "pattern_ids": pattern_ids,
                "pattern_count": len(pattern_ids),
                "occurrence_count": occurrence_count,
                "line_model_original_arbitrary_occurrences": line_model_originals,
                "optimistic_shared_object_count": 1,
                "optimistic_duplicate_occurrences": optimistic_saved,
                "optimistic_proxy_t_reuse": optimistic_saved * PROXY_T_PER_OCCURRENCE,
                "cross_pattern_coalescence": len(pattern_ids) > 1,
                "accepted_occurrence_removal": 0,
                "accepted_proxy_t_reduction": 0,
            }
        )

    relaxed_rows = []
    for key, members in sorted(by_relaxed.items()):
        signatures = sorted({object_key(member) for member in members})
        occurrence_count = sum(int(member["occurrence_count"]) for member in members)
        relaxed_rows.append(
            {
                "relaxed_key": key,
                "signature_count": len(signatures),
                "pattern_count": len({str(member["pattern_id"]) for member in members}),
                "occurrence_count": occurrence_count,
                "can_merge_without_angle_or_wrapper_change": len(signatures) == 1,
            }
        )

    signature_counts = Counter(object_key(row) for row in rows)
    largest_signature_occurrences = max((row["occurrence_count"] for row in share_rows), default=0)
    cross_pattern_shareable_signatures = sum(1 for row in share_rows if row["cross_pattern_coalescence"])
    optimistic_proxy_t_reuse = sum(row["optimistic_proxy_t_reuse"] for row in share_rows)
    accepted_removed = 0
    missing_after_gate = REQUIRED_OCCURRENCE_REMOVALS - accepted_removed
    max_if_all_shared_objects_accepted = sum(row["occurrence_count"] for row in share_rows)
    missing_if_all_shared_objects_accepted = max(0, REQUIRED_OCCURRENCE_REMOVALS - max_if_all_shared_objects_accepted)

    summary = {
        "source_method": ledger.get("method"),
        "source_status": ledger.get("status"),
        "source_exact_packet_count": ledger_summary.get("source_exact_packet_count"),
        "source_unique_carrier_signature_count": ledger_summary.get("unique_carrier_signature_count"),
        "pattern_group_count": len(rows),
        "covered_invariant_flat_occurrence_count": ledger_summary.get("covered_invariant_flat_occurrence_count"),
        "shareable_carrier_object_count": len(share_rows),
        "unique_carrier_signature_count": len(signature_counts),
        "cross_pattern_shareable_signature_count": cross_pattern_shareable_signatures,
        "largest_signature_occurrence_count": largest_signature_occurrences,
        "all_carriers_share_one_signature": len(signature_counts) == 1,
        "all_carriers_share_relaxed_source_axis_role": len(relaxed_rows) == 1,
        "relaxed_group_count": len(relaxed_rows),
        "optimistic_shared_object_count": len(share_rows),
        "optimistic_duplicate_occurrences": sum(row["optimistic_duplicate_occurrences"] for row in share_rows),
        "optimistic_proxy_t_reuse": optimistic_proxy_t_reuse,
        "optimistic_shareability_clears_proxy_t_target": optimistic_proxy_t_reuse >= REQUIRED_OCCURRENCE_REMOVALS * PROXY_T_PER_OCCURRENCE,
        "max_occurrence_removal_if_all_shared_objects_accepted": max_if_all_shared_objects_accepted,
        "all_shared_objects_accepted_clears_b7_target": max_if_all_shared_objects_accepted >= REQUIRED_OCCURRENCE_REMOVALS,
        "missing_occurrences_if_all_shared_objects_accepted": missing_if_all_shared_objects_accepted,
        "missing_proxy_t_if_all_shared_objects_accepted": missing_if_all_shared_objects_accepted * PROXY_T_PER_OCCURRENCE,
        "accepted_occurrence_removal": accepted_removed,
        "accepted_proxy_t_reduction": accepted_removed * PROXY_T_PER_OCCURRENCE,
        "missing_occurrences_after_gate": missing_after_gate,
        "missing_proxy_t_after_gate": missing_after_gate * PROXY_T_PER_OCCURRENCE,
        "single_carrier_exact_packet_found": ledger_summary.get("single_carrier_exact_packet_found"),
        "carrier_shareability_certificate_claimed": False,
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
        "title": "B1/B7 cone_01 single-carrier shareability gate",
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "method": METHOD,
        "source_result": display_path(LEDGER_PATH),
        "source_method": ledger.get("method"),
        "workload": ledger.get("workload", "qasmbench_medium_exact/gcm_h6.qasm"),
        "summary": summary,
        "carrier_shareability_rows": share_rows,
        "relaxed_shareability_rows": relaxed_rows,
        "claim_boundary": {
            "single_carrier_exact_packet_found": ledger_summary.get("single_carrier_exact_packet_found"),
            "carrier_shareability_certificate_claimed": False,
            "carrier_ledger_reduction_claimed": False,
            "rewrite_claimed": False,
            "semantic_certificate_claimed": False,
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "supported_claim": (
                "The current exact carrier packets split into three distinct carrier signatures; "
                "within-pattern reuse is an optimistic signal only and no accepted B7 reduction follows."
            ),
            "unsupported_claims": [
                "This does not provide a shared physical carrier object.",
                "This does not merge the three residual pattern groups into one carrier signature.",
                "This is not an occurrence-removing rewrite certificate.",
                "This is not a B7 resource saving.",
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
    expected = {
        "source_exact_packet_count": 3,
        "source_unique_carrier_signature_count": 3,
        "pattern_group_count": 3,
        "covered_invariant_flat_occurrence_count": 11,
        "shareable_carrier_object_count": 3,
        "unique_carrier_signature_count": 3,
        "cross_pattern_shareable_signature_count": 0,
        "largest_signature_occurrence_count": 8,
        "optimistic_shared_object_count": 3,
        "optimistic_duplicate_occurrences": 8,
        "optimistic_proxy_t_reuse": 160,
        "max_occurrence_removal_if_all_shared_objects_accepted": 11,
        "missing_occurrences_if_all_shared_objects_accepted": 19,
        "missing_proxy_t_if_all_shared_objects_accepted": 380,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": 30,
        "missing_proxy_t_after_gate": 600,
    }
    for field, value in expected.items():
        if summary.get(field) != value:
            errors.append(f"{field}_mismatch")
    if summary.get("all_carriers_share_one_signature") is not False:
        errors.append("carriers_must_not_share_one_signature")
    if summary.get("optimistic_shareability_clears_proxy_t_target") is not False:
        errors.append("optimistic_shareability_must_not_clear_target")
    if summary.get("all_shared_objects_accepted_clears_b7_target") is not False:
        errors.append("shared_objects_must_not_clear_b7_target")
    for field in [
        "carrier_shareability_certificate_claimed",
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
        "# B1/B7 Cone_01 Single-Carrier Shareability Gate",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This artifact consumes T-B1-004v and checks whether the exact carrier packets can be shared or coalesced into countable B7 resource objects.",
        "",
        "## Summary",
        "",
        f"- Source exact packets / covered occurrences: `{summary['source_exact_packet_count']}` / `{summary['covered_invariant_flat_occurrence_count']}`",
        f"- Carrier signatures / shareable objects: `{summary['unique_carrier_signature_count']}` / `{summary['shareable_carrier_object_count']}`",
        f"- Cross-pattern shareable signatures: `{summary['cross_pattern_shareable_signature_count']}`",
        f"- Largest signature occurrence count: `{summary['largest_signature_occurrence_count']}`",
        f"- Optimistic duplicate occurrences / proxy-T reuse: `{summary['optimistic_duplicate_occurrences']}` / `{summary['optimistic_proxy_t_reuse']}`",
        f"- All shared objects accepted clears B7 target: `{summary['all_shared_objects_accepted_clears_b7_target']}`",
        f"- Missing occurrences if all shared objects accepted: `{summary['missing_occurrences_if_all_shared_objects_accepted']}`",
        f"- Accepted occurrence/proxy-T reduction: `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        f"- Validation errors: `{summary['validation_error_count']}`",
        "",
        "## Shareability Rows",
        "",
        "| Carrier object | Patterns | Occurrences | Cross-pattern | Optimistic reuse | Accepted reduction |",
        "|---|---|---:|---|---:|---:|",
    ]
    for row in payload["carrier_shareability_rows"]:
        lines.append(
            "| "
            + f"`{markdown_cell(row['carrier_signature'])}`"
            + " | "
            + markdown_cell(", ".join(row["pattern_ids"]))
            + f" | {row['occurrence_count']} | {row['cross_pattern_coalescence']} | "
            + f"{row['optimistic_proxy_t_reuse']} | {row['accepted_proxy_t_reduction']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- The carrier packets remain exact packets from T-B1-004u.",
            "- They split into three distinct carrier signatures, with no cross-pattern coalescence under the current signature model.",
            "- Optimistic within-pattern reuse is 160 proxy-T, below the 600 proxy-T B7 target and not accepted by the current ledger.",
            "- Even accepting all three carrier objects would cover only 11 occurrences and still miss by 19.",
            "- No rewrite, semantic certificate, physical cost model, or B7 ledger improvement is claimed.",
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
