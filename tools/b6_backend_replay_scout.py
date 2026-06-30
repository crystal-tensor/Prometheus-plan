#!/usr/bin/env python3
"""B6/T-B6-005d backend replay scout.

This artifact turns the T-B6-005c validation-rescue candidate into a repo-local
deterministic replay. It replays the selected physics-risk score from the
source materials table, records input hashes, and keeps DFT/B5 observable gates
closed. It is not a material-discovery or mechanism claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


METHOD = "b6_backend_replay_scout_v0"
STATUS = "backend_replay_candidate_built_missing_observables"
MODEL_STATUS = "repo_local_validation_rescue_replay_built_but_dft_b5_observables_missing"
SELECTED_VARIANT = "physics_risk_adjusted_v0"
FAILED_IDS = ["R7", "R8"]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def high_tc(row: dict[str, Any], threshold: float) -> bool:
    return float(row.get("tc_k", 0.0)) >= threshold


def replay_score(row: dict[str, Any]) -> float:
    return (
        float(row.get("physics_descriptor_score", 0.0))
        - 0.15 * float(row.get("disorder_risk", 0.0))
        - 0.15 * float(row.get("competing_order", 0.0))
    )


def average_precision_at_k(
    rows: list[dict[str, Any]],
    score_key: str,
    k: int,
    threshold: float,
) -> float:
    ranked = sorted(rows, key=lambda item: (item[score_key], item["material_id"]), reverse=True)[:k]
    hits = 0
    precisions: list[float] = []
    for idx, row in enumerate(ranked, start=1):
        if high_tc(row, threshold):
            hits += 1
            precisions.append(hits / idx)
    positives = sum(1 for row in rows if high_tc(row, threshold))
    if positives == 0:
        return 0.0
    return sum(precisions) / min(positives, k)


def top_rows(rows: list[dict[str, Any]], score_key: str, k: int, threshold: float) -> list[dict[str, Any]]:
    keep = [
        "material_id",
        "formula",
        "family",
        "discovery_year",
        "tc_k",
        "pressure_gpa",
        "high_tc_label",
        score_key,
    ]
    ranked = sorted(rows, key=lambda item: (item[score_key], item["material_id"]), reverse=True)[:k]
    out: list[dict[str, Any]] = []
    for rank, row in enumerate(ranked, start=1):
        item = {"rank": rank}
        for key in keep:
            item[key] = row.get(key)
        item["is_negative_control"] = bool(row.get("is_negative_control", False)) or not high_tc(
            row, threshold
        )
        out.append(item)
    return out


def requirement(req_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": req_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def build_payload(root: Path) -> dict[str, Any]:
    source_path = root / "results/B6_crystallographic_descriptor_screen_v0.json"
    rescue_path = root / "results/B6_validation_rescue_scout_v0.json"
    source = load_json(source_path)
    rescue = load_json(rescue_path)
    threshold = float(source.get("high_tc_threshold_k", 30.0))
    top_k = int(source.get("top_k", 12))
    source_rows = list(source.get("materials_table", []))
    replay_rows = []
    for row in source_rows:
        replay_row = dict(row)
        replay_row[SELECTED_VARIANT] = replay_score(replay_row)
        replay_rows.append(replay_row)
    post_rows = [row for row in replay_rows if row.get("time_split") == "post_split"]
    top_all = top_rows(replay_rows, SELECTED_VARIANT, top_k, threshold)
    top_post = top_rows(post_rows, SELECTED_VARIANT, top_k, threshold)
    selected_ap = average_precision_at_k(post_rows, SELECTED_VARIANT, top_k, threshold)
    family_prior_ap = float(source.get("metrics", {}).get("post_split_family_prior_ap", 0.0))
    negative_controls_in_top_k = sum(row["is_negative_control"] for row in top_all)
    replay_table_hash = stable_hash(
        [
            {
                "material_id": row["material_id"],
                SELECTED_VARIANT: row[SELECTED_VARIANT],
            }
            for row in replay_rows
        ]
    )
    source_table_hash = stable_hash(source_rows)
    replay_formula_hash = stable_hash(
        {
            "variant": SELECTED_VARIANT,
            "formula": "physics_descriptor_score - 0.15*disorder_risk - 0.15*competing_order",
            "tie_break": "score_then_material_id_desc",
        }
    )

    requirements = [
        requirement(
            "R1",
            "source descriptor table exists",
            source.get("method") == "b6_crystallographic_descriptor_screen_v0",
            {"method": source.get("method"), "source_table_hash": source_table_hash},
        ),
        requirement(
            "R2",
            "validation rescue source exists",
            rescue.get("method") == "b6_validation_rescue_scout_v0"
            and rescue.get("selected_variant") == SELECTED_VARIANT,
            {"method": rescue.get("method"), "selected_variant": rescue.get("selected_variant")},
        ),
        requirement(
            "R3",
            "row scope is preserved",
            len(replay_rows) == 56
            and len({row.get("family") for row in replay_rows}) == 28
            and int(source.get("negative_control_count", 0)) == 18,
            {
                "record_count": len(replay_rows),
                "family_count": len({row.get("family") for row in replay_rows}),
                "negative_control_count": source.get("negative_control_count"),
            },
        ),
        requirement(
            "R4",
            "selected variant is replayed with a pinned formula hash",
            replay_formula_hash == "e23239648dd11aa8e0db8ecdeb5824506a5a379c9ba2777965c3aafa5d5d8230",
            {"replay_formula_hash": replay_formula_hash, "replay_table_hash": replay_table_hash},
        ),
        requirement(
            "R5",
            "replayed AP matches validation rescue scout",
            selected_ap == rescue.get("selected_post_split_ap") == 1.0,
            {"replayed_post_split_ap": selected_ap, "rescue_post_split_ap": rescue.get("selected_post_split_ap")},
        ),
        requirement(
            "R6",
            "replayed score beats family prior and keeps negative controls",
            selected_ap > family_prior_ap and negative_controls_in_top_k == 2,
            {
                "family_prior_ap": family_prior_ap,
                "negative_controls_in_top_k": negative_controls_in_top_k,
            },
        ),
        requirement(
            "R7",
            "DFT observable channel exists",
            False,
            {"dft_observable_rows": 0},
        ),
        requirement(
            "R8",
            "B5-computed observable channel exists",
            False,
            {"b5_computed_observable_rows": 0},
        ),
    ]
    failed = [row for row in requirements if not row["passed"]]

    return {
        "benchmark_id": "B6",
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_descriptor_status": source.get("status"),
        "source_validation_rescue_status": rescue.get("status"),
        "selected_variant": SELECTED_VARIANT,
        "source_table_hash": source_table_hash,
        "replay_formula_hash": replay_formula_hash,
        "replay_table_hash": replay_table_hash,
        "record_count": len(replay_rows),
        "family_count": len({row.get("family") for row in replay_rows}),
        "negative_control_count": source.get("negative_control_count"),
        "post_split_record_count": len(post_rows),
        "top_k": top_k,
        "selected_negative_controls_in_top_k": negative_controls_in_top_k,
        "selected_post_split_ap": selected_ap,
        "post_split_family_prior_ap": family_prior_ap,
        "selected_beats_family_prior": selected_ap > family_prior_ap,
        "dft_observable_rows": 0,
        "b5_computed_observable_rows": 0,
        "requirements": requirements,
        "backend_replay_requirement_count": len(requirements),
        "backend_replay_requirements_passed": len(requirements) - len(failed),
        "backend_replay_requirements_failed": len(failed),
        "failed_backend_replay_requirement_ids": [row["requirement_id"] for row in failed],
        "top_all_rows": top_all,
        "top_post_rows": top_post,
        "claims": {
            "backend_replay_built": True,
            "pinned_external_crystallographic_backend_claimed": False,
            "source_screen_rewritten": False,
            "dft_observable_claimed": False,
            "b5_computed_observable_claimed": False,
            "material_discovery_claimed": False,
            "mechanism_solved": False,
            "solution_claimed": False,
        },
        "claim_boundary": {
            "what_is_supported": "The validation-rescue score is replayed deterministically from the existing source table with stable hashes.",
            "what_is_not_supported": "No external crystallographic backend, DFT observable, B5 observable, material discovery, or mechanism solution is established.",
            "next_gate": "Attach real DFT and B5 observable rows or keep B6 demoted to validation-rescue evidence.",
        },
        "validation_errors": [],
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# B6 Backend Replay Scout",
        "",
        f"Status: **{payload['status']}**",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Selected variant: `{payload['selected_variant']}`",
        f"- Requirements passed / failed: {payload['backend_replay_requirements_passed']} / {payload['backend_replay_requirements_failed']}",
        f"- Failed requirement IDs: {', '.join(payload['failed_backend_replay_requirement_ids'])}",
        f"- Source table hash: `{payload['source_table_hash']}`",
        f"- Replay formula hash: `{payload['replay_formula_hash']}`",
        f"- Replay table hash: `{payload['replay_table_hash']}`",
        f"- Selected post-split AP: {payload['selected_post_split_ap']}",
        f"- Family-prior AP: {payload['post_split_family_prior_ap']}",
        f"- Negative controls in top-k: {payload['selected_negative_controls_in_top_k']}",
        f"- DFT rows / B5 rows: {payload['dft_observable_rows']} / {payload['b5_computed_observable_rows']}",
        "",
        "## Requirement Results",
        "",
    ]
    for row in payload["requirements"]:
        mark = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- {row['requirement_id']} [{mark}]: {row['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, default=Path("results/B6_backend_replay_scout_v0.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("research/B6_backend_replay_scout.md"))
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    payload = build_payload(root)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_markdown(payload, args.markdown_output)
    print(payload["status"])
    print(
        payload["backend_replay_requirements_passed"],
        payload["backend_replay_requirements_failed"],
        payload["failed_backend_replay_requirement_ids"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
