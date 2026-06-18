#!/usr/bin/env python3
"""Build a B5 canonical-DMRG readiness gate from existing tensor references."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b5_canonical_dmrg_readiness_gate_v0"
STATUS = "canonical_dmrg_readiness_gate_failed_not_production_dmrg"
MODEL_STATUS = "cross_reference_readiness_gate_not_solver"
VERSION = "0.1"
FIXED_SECTOR_NORM_THRESHOLD = 0.01


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def bool_gate(gate_id: str, label: str, passed: bool, evidence: dict[str, Any], required_next_step: str) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
        "required_next_step": required_next_step,
    }


def build_payload(
    two_site_path: Path,
    variational_path: Path,
    seeded_path: Path,
    non_oracle_path: Path,
) -> dict[str, Any]:
    started = time.time()
    two_site = load_json(two_site_path)
    variational = load_json(variational_path)
    seeded = load_json(seeded_path)
    non_oracle = load_json(non_oracle_path)

    two_summary = two_site["summary"]
    var_summary = variational["summary"]
    seeded_summary = seeded["summary"]
    non_oracle_summary = non_oracle["summary"]

    instance_count = int(two_summary["instance_count"])
    if int(var_summary["instance_count"]) != instance_count or int(seeded_summary["instance_count"]) != instance_count:
        raise ValueError("B5 tensor references must cover the same instance count")

    two_mean = float(two_summary["selected_mean_relative_response_error"])
    var_mean = float(var_summary["selected_mean_relative_response_error"])
    seeded_mean = float(seeded_summary["selected_mean_relative_response_error"])
    non_oracle_mean = float(non_oracle_summary["selected_mean_relative_response_error"])
    two_max = float(two_summary["selected_max_relative_response_error"])
    var_max = float(var_summary["selected_max_relative_response_error"])
    seeded_max = float(seeded_summary["selected_max_relative_response_error"])
    two_norm = float(two_summary["selected_min_fixed_sector_norm_before_normalization"])
    var_norm = float(var_summary["selected_min_fixed_sector_norm_before_normalization"])
    seeded_norm = float(seeded_summary["selected_min_fixed_sector_norm_before_normalization"])

    two_rows_beating_seeded = int(two_summary["two_site_dmrg_rows_beating_seeded_mps_pressure_reference"])
    var_rows_beating_seeded = int(var_summary["variational_mps_rows_beating_seeded_mps_pressure_reference"])
    two_rows_beating_als = int(two_summary["two_site_dmrg_rows_beating_variational_mps_als_reference"])

    exact_seeded_reference_is_strongest = seeded_mean < var_mean and seeded_mean < two_mean and seeded_mean < non_oracle_mean
    prototype_fixed_sector_norms_pass = two_norm >= FIXED_SECTOR_NORM_THRESHOLD and var_norm >= FIXED_SECTOR_NORM_THRESHOLD

    gates = [
        bool_gate(
            "G1",
            "Canonical left/right environments are present",
            bool(two_summary.get("canonical_environment_production_dmrg")),
            {"two_site_canonical_environment_production_dmrg": two_summary.get("canonical_environment_production_dmrg")},
            "Implement canonical-center sweeps with stored left/right environments and orthonormal residual checks.",
        ),
        bool_gate(
            "G2",
            "Production DMRG is available",
            bool(two_summary.get("production_dmrg")) or bool(var_summary.get("production_dmrg")),
            {
                "two_site_production_dmrg": two_summary.get("production_dmrg"),
                "variational_production_dmrg": var_summary.get("production_dmrg"),
            },
            "Replace prototype optimizers with a mature finite-system DMRG/MPS solver and convergence ledger.",
        ),
        bool_gate(
            "G3",
            "Non-seeded tensor references beat the seeded pressure reference",
            two_rows_beating_seeded > 0 or var_rows_beating_seeded > 0,
            {
                "two_site_rows_beating_seeded_mps_pressure_reference": two_rows_beating_seeded,
                "variational_mps_rows_beating_seeded_mps_pressure_reference": var_rows_beating_seeded,
            },
            "Produce non-exact-state-seeded tensor rows that beat the seeded MPS pressure reference under the same D5 observables.",
        ),
        bool_gate(
            "G4",
            "Two-site prototype improves mean response error over one-site ALS",
            two_mean < var_mean,
            {
                "two_site_mean_relative_response_error": two_mean,
                "variational_mps_als_mean_relative_response_error": var_mean,
                "two_site_rows_beating_variational_mps_als_reference": two_rows_beating_als,
            },
            "Improve the two-site update or demote it behind the stronger one-site ALS pressure reference.",
        ),
        bool_gate(
            "G5",
            "Prototype fixed-sector norms are stable before normalization",
            prototype_fixed_sector_norms_pass,
            {
                "threshold": FIXED_SECTOR_NORM_THRESHOLD,
                "two_site_min_fixed_sector_norm_before_normalization": two_norm,
                "variational_min_fixed_sector_norm_before_normalization": var_norm,
                "seeded_min_fixed_sector_norm_before_normalization": seeded_norm,
            },
            "Add canonical gauges and sector-aware initialization so selected states do not rely on tiny fixed-sector projection norms.",
        ),
        bool_gate(
            "G6",
            "Best non-seeded max response error is within seeded pressure max error",
            min(two_max, var_max) <= seeded_max,
            {
                "two_site_max_relative_response_error": two_max,
                "variational_mps_als_max_relative_response_error": var_max,
                "seeded_mps_pressure_max_relative_response_error": seeded_max,
            },
            "Close the worst-row gap to the exact-state-seeded pressure reference before claiming a mature tensor denominator.",
        ),
        bool_gate(
            "G7",
            "Same-access quantum response kernel exists",
            False,
            {
                "quantum_response_win_claimed": False,
                "same_access_response_oracle_available": False,
            },
            "If pursuing a quantum route, add state-preparation, mixing, measurement, and confidence costs on the same rows.",
        ),
        bool_gate(
            "G8",
            "Full cost accounting is ready for B10 same-access comparison",
            False,
            {
                "optimizer_loop_costs": "missing",
                "tensor_environment_costs": "missing",
                "quantum_measurement_costs": "missing",
            },
            "Add wall-clock, matvec, sweep, memory, shot, and optimizer-loop costs before feeding a positive B10 route.",
        ),
    ]

    passed_gate_count = sum(1 for gate in gates if gate["passed"])
    failed_gate_count = len(gates) - passed_gate_count

    summary = {
        "instance_count": instance_count,
        "readiness_gate_count": len(gates),
        "passed_gate_count": passed_gate_count,
        "failed_gate_count": failed_gate_count,
        "mature_canonical_dmrg_ready": False,
        "production_dmrg": False,
        "canonical_environment_production_dmrg": False,
        "quantum_response_win_claimed": False,
        "accuracy_per_resource_win_claimed": False,
        "same_access_positive_route_claimed": False,
        "fixed_sector_norm_threshold": FIXED_SECTOR_NORM_THRESHOLD,
        "two_site_mean_relative_response_error": two_mean,
        "two_site_max_relative_response_error": two_max,
        "variational_mps_als_mean_relative_response_error": var_mean,
        "variational_mps_als_max_relative_response_error": var_max,
        "seeded_mps_pressure_mean_relative_response_error": seeded_mean,
        "seeded_mps_pressure_max_relative_response_error": seeded_max,
        "non_oracle_embedding_mean_relative_response_error": non_oracle_mean,
        "two_site_rows_beating_variational_mps_als_reference": two_rows_beating_als,
        "two_site_rows_beating_seeded_mps_pressure_reference": two_rows_beating_seeded,
        "variational_mps_rows_beating_seeded_mps_pressure_reference": var_rows_beating_seeded,
        "two_site_min_fixed_sector_norm_before_normalization": two_norm,
        "variational_min_fixed_sector_norm_before_normalization": var_norm,
        "seeded_min_fixed_sector_norm_before_normalization": seeded_norm,
        "exact_state_seeded_reference_is_strongest": exact_seeded_reference_is_strongest,
        "prototype_fixed_sector_norms_pass": prototype_fixed_sector_norms_pass,
        "validation_error_count": 0,
    }

    validation_errors: list[str] = []
    if passed_gate_count != 0:
        validation_errors.append("readiness gate unexpectedly passed at least one production-readiness condition")
    if failed_gate_count != len(gates):
        validation_errors.append("all readiness gates are expected to fail for the current prototype portfolio")
    if not exact_seeded_reference_is_strongest:
        validation_errors.append("seeded pressure reference should remain strongest among current response means")
    if two_rows_beating_seeded != 0 or var_rows_beating_seeded != 0:
        validation_errors.append("non-seeded prototypes unexpectedly beat seeded pressure reference")
    if bool(two_summary.get("production_dmrg")) or bool(var_summary.get("production_dmrg")):
        validation_errors.append("upstream prototypes unexpectedly claim production DMRG")
    if bool(two_summary.get("quantum_response_win_claimed")) or bool(var_summary.get("quantum_response_win_claimed")):
        validation_errors.append("upstream prototypes unexpectedly claim quantum response win")
    summary["validation_error_count"] = len(validation_errors)

    return {
        "benchmark_id": "B5",
        "problem_id": 38,
        "title": "B5 canonical DMRG readiness gate",
        "version": VERSION,
        "last_updated": time.strftime("%Y-%m-%d"),
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "dependency_two_site_dmrg_result": str(two_site_path),
        "dependency_variational_mps_als_result": str(variational_path),
        "dependency_seeded_mps_pressure_result": str(seeded_path),
        "dependency_non_oracle_embedding_result": str(non_oracle_path),
        "summary": summary,
        "readiness_gates": gates,
        "claim_boundary": {
            "what_is_supported": (
                "A cross-reference readiness audit over the current B5 tensor and embedding pressure references."
            ),
            "what_is_not_supported": (
                "This is not a production DMRG implementation, not a canonical-environment solver, not a quantum "
                "response kernel, not a same-access positive B10 route, and not an accuracy-per-resource win."
            ),
            "next_gate": (
                "Implement mature canonical-environment DMRG/MPS with convergence and cost ledgers, or provide a "
                "same-access response oracle with full state-preparation and measurement costs."
            ),
            "mature_canonical_dmrg_ready": False,
            "production_dmrg": False,
            "canonical_environment_production_dmrg": False,
            "quantum_response_win_claimed": False,
            "accuracy_per_resource_win_claimed": False,
            "same_access_positive_route_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# B5 Canonical DMRG Readiness Gate v0.1",
        "",
        f"Last updated: {payload['last_updated']}",
        "",
        f"Status: **{payload['status']}**",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Model status: `{payload['model_status']}`",
        f"- Instances: {summary['instance_count']}",
        f"- Readiness gates passed/failed: {summary['passed_gate_count']} / {summary['failed_gate_count']}",
        f"- Two-site mean/max response error: {fmt(summary['two_site_mean_relative_response_error'])} / {fmt(summary['two_site_max_relative_response_error'])}",
        f"- Variational MPS/ALS mean/max response error: {fmt(summary['variational_mps_als_mean_relative_response_error'])} / {fmt(summary['variational_mps_als_max_relative_response_error'])}",
        f"- Seeded MPS pressure mean/max response error: {fmt(summary['seeded_mps_pressure_mean_relative_response_error'])} / {fmt(summary['seeded_mps_pressure_max_relative_response_error'])}",
        f"- Rows beating seeded MPS pressure, two-site / ALS: {summary['two_site_rows_beating_seeded_mps_pressure_reference']} / {summary['variational_mps_rows_beating_seeded_mps_pressure_reference']}",
        f"- Mature canonical DMRG ready: {summary['mature_canonical_dmrg_ready']}",
        f"- Validation errors: {summary['validation_error_count']}",
        "",
        "## Readiness Gates",
        "",
        "| Gate | Passed | Evidence | Required next step |",
        "|---|---:|---|---|",
    ]
    for gate in payload["readiness_gates"]:
        evidence = "; ".join(f"{key}={fmt(value)}" for key, value in gate["evidence"].items())
        lines.append(
            f"| {gate['gate_id']}: {gate['label']} | {gate['passed']} | {evidence} | {gate['required_next_step']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The current B5 tensor portfolio is useful as a pressure ladder, but it is not ready to be promoted to a mature canonical-DMRG denominator.",
            "The exact-state-seeded MPS pressure reference remains strongest by response error, while both non-seeded prototypes have zero rows beating it.",
            "This gate therefore closes T-B5-005 as a readiness audit and opens the next implementation task: build an actual canonical-environment solver or a same-access response oracle with full costs.",
            "",
            "## Claim Boundary",
            "",
        ]
    )
    for key, value in payload["claim_boundary"].items():
        lines.append(f"- {key}: {value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--two-site", type=Path, default=Path("results/B5_two_site_dmrg_response_reference_v0.json"))
    parser.add_argument("--variational", type=Path, default=Path("results/B5_variational_mps_als_response_reference_v0.json"))
    parser.add_argument("--seeded", type=Path, default=Path("results/B5_mps_truncation_response_reference_v0.json"))
    parser.add_argument("--non-oracle", type=Path, default=Path("results/B5_non_oracle_response_embedding_baseline_v0.json"))
    parser.add_argument("--json-output", type=Path, default=Path("results/B5_canonical_dmrg_readiness_gate_v0.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("research/B5_canonical_dmrg_readiness_gate.md"))
    args = parser.parse_args()

    payload = build_payload(args.two_site, args.variational, args.seeded, args.non_oracle)
    write_json(args.json_output, payload)
    write_markdown(args.markdown_output, payload)
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
