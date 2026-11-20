#!/usr/bin/env python3
"""Independent standard-library audit for the logical-memory horizon packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_logical_memory_horizon_gate_v1.json"
DEFAULT_BASELINE = ROOT / "results/B2_stim_surface_code_memory_baseline_v0.json"
DEFAULT_AUDIT = ROOT / "results/B2_B7_P023_logical_memory_horizon_audit_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def wilson_zero(shots: int, z: float) -> float:
    return z * z / (shots + z * z)


def minimum_shots(target: float, z: float) -> int:
    n = 1
    while wilson_zero(n, z) > target:
        n += 1
    return n


def item(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    args = parser.parse_args()
    result = read(args.result)
    baseline = read(args.baseline)
    z = 1.959963984540054
    projections = result["row_projections"]
    paired = result["paired_basis_gates"]
    resolution = result["statistical_resolution_planning"]
    rows_by_key = {
        (row["memory_basis"], row["physical_error"], row["distance"]): row
        for row in baseline["results"]
    }
    checks = [
        item("scope", result["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact catalog scope."),
        item("decision", result["decision"].endswith("p023_b2_b7_credit_closed"), result["decision"]),
        item("baseline_row_count", len(rows_by_key) == 30, f"Rows: {len(rows_by_key)}."),
        item("projection_row_count", len(projections) == 120, f"Rows: {len(projections)}."),
        item("projection_source_join", all((row["memory_basis"], row["physical_error"], row["distance"]) in rows_by_key for row in projections), "Every projection joins to a baseline row."),
        item("source_rounds_match", all(row["source_rounds"] == rows_by_key[(row["memory_basis"], row["physical_error"], row["distance"])]["rounds"] for row in projections), "All source rounds match."),
        item("horizon_set", {row["horizon_rounds"] for row in projections} == {10, 100, 1000, 1000000}, "Four frozen horizons."),
        item("no_direct_projection", not any(row["direct_horizon_evidence"] for row in projections), "No source experiment reaches ten rounds."),
        item("paired_count", len(paired) == 3 * 5 * 4 * 2, f"Rows: {len(paired)}."),
        item("paired_basis_presence", all(row["basis_rows_present"] == ["x", "z"] for row in paired), "Both basis rows are present for every group."),
        item("paired_direct_zero", not any(row["both_bases_direct_pass"] for row in paired), "No direct pair passes."),
        item("zero_failure_1pct", minimum_shots(0.01, z) == 381, f"Minimum: {minimum_shots(0.01, z)}."),
        item("zero_failure_0p1pct", minimum_shots(0.001, z) == 3838, f"Minimum: {minimum_shots(0.001, z)}."),
        item("resolution_count", len(resolution) == 2 * 4 * 3, f"Rows: {len(resolution)}."),
        item("resolution_arithmetic", all(row["minimum_qubit_cycles_both_bases"] == 2 * row["minimum_zero_failure_direct_shots"] * row["horizon_rounds"] * row["physical_qubits"] for row in resolution), "All qubit-cycle products reproduce."),
        item("capture_count", len(result["external_evidence_captures"]) == 3, "Three external denominator captures."),
        item("capture_semantics", all(row["all_required_fragments_present"] for row in result["external_evidence_captures"]), "All source semantic sentinels pass."),
        item("readiness_false", not any([result["readiness"]["p023_scalable_memory_ready"], result["readiness"]["b2_low_overhead_credit_ready"], result["readiness"]["b7_memory_credit_ready"]]), "All three readiness flags remain false."),
        item("b7_credit_zero", result["readiness"]["b7_resource_credit_from_this_gate"] == 0, "No B7 credit."),
        item("formal_checks_passed", result["summary"]["checks_failed"] == 0 and all(row["passed"] for row in result["formal_checks"]), "Producer checks all pass."),
        item("claim_boundary", not any(result["claim_boundary"][key] for key in ["new_code_claimed", "threshold_claimed", "scalable_quantum_memory_claimed", "hardware_result_claimed", "production_decoder_claimed", "b7_resource_credit_claimed", "quantum_advantage_claimed"]), "Forbidden claims remain false."),
    ]
    audit = {
        "schema_version": "b2_b7_p023_logical_memory_horizon_audit_v1",
        "as_of_date": result["as_of_date"],
        "source": {"result_path": str(args.result.relative_to(ROOT)), "result_sha256": sha(args.result), "baseline_path": str(args.baseline.relative_to(ROOT)), "baseline_sha256": sha(args.baseline)},
        "audit_checks": checks,
        "summary": {"checks_total": len(checks), "checks_passed": sum(row["passed"] for row in checks), "checks_failed": sum(not row["passed"] for row in checks)},
        "decision": result["decision"],
    }
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit["summary"], sort_keys=True))
    if audit["summary"]["checks_failed"]:
        raise SystemExit("independent audit failed")


if __name__ == "__main__":
    main()
