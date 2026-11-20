#!/usr/bin/env python3
"""Verify exact scientific replay of the Kaggle-inspired QEC reference run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRIMARY = ROOT / "results/B2_B7_P023_kaggle_inspired_acceptance_v1.json"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_kaggle_inspired_acceptance_replay_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def without_timing(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "timing"}


def item(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", type=Path, default=DEFAULT_PRIMARY)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    primary = read(args.primary)
    replay = read(args.replay)
    p_rows = {row["memory_basis"]: row for row in primary["strict_reference_rows"]}
    r_rows = {row["memory_basis"]: row for row in replay["strict_reference_rows"]}
    checks = [
        item("schema", primary["schema_version"] == replay["schema_version"], primary["schema_version"]),
        item("decision", primary["decision"] == replay["decision"], primary["decision"]),
        item("scope", primary["scope"] == replay["scope"], "Exact scope matches."),
        item("sources", primary["official_sources"] == replay["official_sources"], "Official source contracts match."),
        item("protocol", primary["protocol_binding"] == replay["protocol_binding"], primary["protocol_binding"]["sha256"]),
        item("generator", primary["generator"] == replay["generator"], primary["generator"]["sha256"]),
        item("environment", primary["execution_environment"] == replay["execution_environment"], str(primary["execution_environment"])),
        item("experiment", primary["strict_reference_experiment"] == replay["strict_reference_experiment"], "Strict experiment matches."),
        item("previous_regrade", primary["previous_3838_shot_regrade"] == replay["previous_3838_shot_regrade"], "Prior regrade matches."),
        item("basis_set", list(p_rows) == list(r_rows) == ["x", "z"], str(list(p_rows))),
        item("scientific_rows", all(without_timing(p_rows[basis]) == without_timing(r_rows[basis]) for basis in p_rows), "All non-timing row fields match exactly."),
        item("chunk_manifests", all(p_rows[basis]["chunk_digests"] == r_rows[basis]["chunk_digests"] for basis in p_rows), "All 800 chunk digests match exactly."),
        item("trace_hashes", all(p_rows[basis]["sample_prediction_trace_sha256"] == r_rows[basis]["sample_prediction_trace_sha256"] and p_rows[basis]["failure_vector_sha256"] == r_rows[basis]["failure_vector_sha256"] for basis in p_rows), "Trace and failure hashes match."),
        item("failure_counts", all(p_rows[basis]["logical_failures"] == r_rows[basis]["logical_failures"] for basis in p_rows), "Failure counts match."),
        item("strict_bounds", all(p_rows[basis]["clopper_pearson_upper_delta_2m128"] == r_rows[basis]["clopper_pearson_upper_delta_2m128"] for basis in p_rows), "Strict bounds match."),
        item("reference_gate", primary["reference_gate"] == replay["reference_gate"], "Reference gate matches."),
        item("readiness", primary["readiness"] == replay["readiness"], "Readiness boundary matches."),
        item("formal_checks", primary["formal_checks"] == replay["formal_checks"], "Producer checks match."),
        item("summary", primary["summary"] == replay["summary"], str(primary["summary"])),
        item("claim_boundary", primary["claim_boundary"] == replay["claim_boundary"], "Claim boundary matches."),
        item("run_id", primary["run_id"] == replay["run_id"], primary["run_id"]),
        item("timing_positive", all(all(row["timing"][key] > 0 for key in ["build_seconds", "sample_seconds", "decode_seconds", "total_seconds"]) for row in list(p_rows.values()) + list(r_rows.values())), "Timing is positive in both runs."),
    ]
    failed = [value for value in checks if not value["passed"]]
    output = {
        "schema_version": "b2_b7_p023_kaggle_inspired_acceptance_replay_v1",
        "as_of_date": primary["as_of_date"],
        "scope": primary["scope"],
        "status": "exact_strict_reference_replay_passed" if not failed else "exact_strict_reference_replay_failed",
        "run_id": primary["run_id"],
        "primary_result_sha256": sha(args.primary),
        "replay_result_sha256": sha(args.replay),
        "checks": checks,
        "summary": {
            "checks_passed": sum(value["passed"] for value in checks),
            "checks_total": len(checks),
            "checks_failed": len(failed),
            "exact_scientific_rows": sum(without_timing(p_rows[basis]) == without_timing(r_rows[basis]) for basis in p_rows),
            "basis_count": len(p_rows),
        },
        "timing_boundary": "Wall-clock timing may vary; challenge hashes, samples, predictions, failures, confidence bounds, cost, score, and claim boundaries must match exactly.",
        "failure_names": [value["name"] for value in failed],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], sort_keys=True))
    if failed:
        raise SystemExit(f"replay failed: {output['failure_names']}")


if __name__ == "__main__":
    main()
