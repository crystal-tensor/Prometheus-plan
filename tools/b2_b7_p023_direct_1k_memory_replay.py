#!/usr/bin/env python3
"""Compare two frozen executions of the direct 1,000-round memory packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRIMARY = ROOT / "results/B2_B7_P023_direct_1k_memory_v1.json"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_direct_1k_memory_replay_audit_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def item(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def strip_timing(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "timing"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", type=Path, default=DEFAULT_PRIMARY)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    primary = read(args.primary)
    replay = read(args.replay)
    p_rows = primary["configurations"]
    r_rows = replay["configurations"]
    p_by_id = {row["configuration_id"]: row for row in p_rows}
    r_by_id = {row["configuration_id"]: row for row in r_rows}
    trace_fields = [
        "circuit_sha256",
        "detector_error_model_sha256",
        "sample_prediction_trace_sha256",
        "failure_vector_sha256",
    ]
    checks = [
        item("schema", primary["schema_version"] == replay["schema_version"], primary["schema_version"]),
        item("decision", primary["decision"] == replay["decision"], primary["decision"]),
        item("scope", primary["scope"] == replay["scope"], "Exact scope matches."),
        item("protocol_binding", primary["protocol_binding"] == replay["protocol_binding"], primary["protocol_binding"]["benchmark_sha256"]),
        item("generator_binding", primary["generator"] == replay["generator"], primary["generator"]["sha256"]),
        item("execution_environment", primary["execution_environment"] == replay["execution_environment"], str(primary["execution_environment"])),
        item("experiment_contract", primary["experiment_contract"] == replay["experiment_contract"], "Frozen experiment contracts match."),
        item("configuration_ids", list(p_by_id) == list(r_by_id), str(list(p_by_id))),
        item("scientific_rows", all(strip_timing(p_by_id[key]) == strip_timing(r_by_id[key]) for key in p_by_id), "All non-timing row fields match exactly."),
        item("trace_bindings", all(all(p_by_id[key][field] == r_by_id[key][field] for field in trace_fields) for key in p_by_id), "All four trace bindings match in all six rows."),
        item("logical_failures", all(p_by_id[key]["logical_failures"] == r_by_id[key]["logical_failures"] for key in p_by_id), "Per-configuration failures match exactly."),
        item("chunk_manifests", all(p_by_id[key]["chunk_digests"] == r_by_id[key]["chunk_digests"] for key in p_by_id), "All ordered chunk digests match exactly."),
        item("paired_gates", primary["paired_basis_gates"] == replay["paired_basis_gates"], "All paired-basis gates match exactly."),
        item("readiness", primary["readiness"] == replay["readiness"], "All readiness flags match exactly."),
        item("trace_policy", primary["trace_binding"] == replay["trace_binding"], "Trace policy matches."),
        item("formal_checks", primary["formal_checks"] == replay["formal_checks"], "Producer formal checks match exactly."),
        item("summary", primary["summary"] == replay["summary"], str(primary["summary"])),
        item("claim_boundary", primary["claim_boundary"] == replay["claim_boundary"], "Claim boundary matches exactly."),
        item("run_id", primary["run_id"] == replay["run_id"], primary["run_id"]),
        item("timing_positive", all(all(row["timing"][key] > 0 for key in ["build_seconds", "sample_seconds", "decode_seconds", "total_seconds"]) for row in p_rows + r_rows), "Both executions contain positive timing observations."),
    ]
    failed = [value for value in checks if not value["passed"]]
    output = {
        "schema_version": "b2_b7_p023_direct_1k_memory_replay_audit_v1",
        "as_of_date": primary["as_of_date"],
        "scope": primary["scope"],
        "status": "exact_scientific_replay_passed" if not failed else "exact_scientific_replay_failed",
        "primary_result_sha256": digest(args.primary),
        "replay_result_sha256": digest(args.replay),
        "run_id": primary["run_id"],
        "checks": checks,
        "summary": {
            "checks_passed": sum(value["passed"] for value in checks),
            "checks_total": len(checks),
            "checks_failed": len(failed),
            "exact_scientific_rows": sum(strip_timing(p_by_id[key]) == strip_timing(r_by_id[key]) for key in p_by_id),
            "configuration_count": len(p_by_id),
        },
        "timing_boundary": "Wall-clock timing is intentionally measured rather than replay-identical; all scientific inputs, traces, failures, confidence gates, and claim boundaries must match exactly.",
        "failure_names": [value["name"] for value in failed],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], sort_keys=True))
    if failed:
        raise SystemExit(f"replay audit failed: {output['failure_names']}")


if __name__ == "__main__":
    main()
