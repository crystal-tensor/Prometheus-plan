#!/usr/bin/env python3
"""T-B3-024/T-B10-015k: scout remaining B3/B10 F1 row-extension blockers."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


METHOD = "b3_b10_f1_remaining_row_extension_scout_v0"
STATUS = "f1_remaining_row_extension_scout_blocked_zero_credit"
MODEL_STATUS = "remaining_three_f1_rows_identified_from_cross_molecule_pressure_but_not_acceptable"
SOURCE_TARGET_ID = "T-B3-024/T-B10-015k"
EXPECTED_PRESSURE_METHOD = "b3_cross_molecule_ucc_adapt_pressure_v0"
EXPECTED_CANDIDATE_METHOD = "b3_b10_f1_pilot_row_candidate_gate_v0"
EXPECTED_F1_ROW_COUNT = 4
PRIMARY_CANDIDATE_MOLECULE = "h2_bond_stretch"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload,
        indent=2 if pretty else None,
        sort_keys=True,
        separators=None if pretty else (",", ":"),
    )
    path.write_text(text + "\n", encoding="utf-8")


def requirement(req_id: str, passed: bool, description: str, evidence: Any) -> dict[str, Any]:
    return {
        "id": req_id,
        "passed": bool(passed),
        "description": description,
        "evidence": evidence,
    }


def extension_row(row: dict[str, Any]) -> dict[str, Any]:
    molecule = row["molecule"]
    blocked_reasons: list[str] = []
    if not row.get("full_compiled_state_covariance_computed"):
        blocked_reasons.append("full_compiled_state_covariance_not_computed")
    if int(row.get("sample_subset_term_count", 0)) < int(
        row.get("random_pauli_terms_under_compiled_state", 0)
    ):
        blocked_reasons.append("bounded_high_coefficient_subset_not_full_pauli_cover")
    if not row.get("converged_vqe_or_adapt_energy"):
        blocked_reasons.append("one_parameter_seed_not_converged_multi_parameter_state")
    if not row.get("candidate_beats_selected_ci_larger_basis_denominator"):
        blocked_reasons.append("no_same_access_denominator_win")

    artifact = {
        "extension_row_id": f"B3B10-F1-extension-scout-{molecule}",
        "molecule": molecule,
        "coordinate": row.get("coordinate"),
        "selected_ci_basis": row.get("selected_ci_basis"),
        "total_qubits": row.get("total_qubits"),
        "electrons": row.get("electrons"),
        "ansatz_model": row.get("ansatz_model"),
        "ansatz_theta": row.get("ansatz_theta"),
        "compiled_two_qubit_gates_per_preparation": row.get(
            "compiled_two_qubit_gates_per_preparation"
        ),
        "random_pauli_terms_under_compiled_state": row.get(
            "random_pauli_terms_under_compiled_state"
        ),
        "source_hf_qwc_group_count": row.get("source_hf_qwc_group_count"),
        "sample_subset_term_count": row.get("sample_subset_term_count"),
        "sample_subset_qwc_group_count": row.get("sample_subset_qwc_group_count"),
        "sampleable_qwc_group_count": row.get("sampleable_qwc_group_count"),
        "pilot_group_count": row.get("pilot_group_count"),
        "pilot_shots_per_group": row.get("pilot_shots_per_group"),
        "pilot_mean_relative_variance_error": row.get("pilot_mean_relative_variance_error"),
        "pilot_max_relative_variance_error": row.get("pilot_max_relative_variance_error"),
        "sampled_groups_preview_hash": canonical_hash(row.get("sampled_groups_preview", [])),
        "full_compiled_state_covariance_computed": row.get(
            "full_compiled_state_covariance_computed"
        ),
        "full_compiled_state_covariance_reason": row.get(
            "full_compiled_state_covariance_reason"
        ),
        "optimistic_cross_molecule_derivative_shot_floor_lower_bound": row.get(
            "optimistic_cross_molecule_derivative_shot_floor_lower_bound"
        ),
        "optimizer_loop_total_shots_lower_bound": row.get(
            "optimizer_loop_total_shots_lower_bound"
        ),
        "optimizer_loop_two_qubit_executions_lower_bound": row.get(
            "optimizer_loop_two_qubit_executions_lower_bound"
        ),
        "candidate_beats_selected_ci_larger_basis_denominator": row.get(
            "candidate_beats_selected_ci_larger_basis_denominator"
        ),
        "f1_extension_acceptance_ready": False,
        "blocked_reasons": blocked_reasons,
    }
    artifact["extension_row_hash"] = canonical_hash(artifact)
    return artifact


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    pressure = load_json(args.cross_molecule_pressure)
    prior = load_json(args.prior_candidate_gate)
    rows = pressure.get("rows", [])
    prior_summary = prior.get("summary", {})

    remaining_rows = [row for row in rows if row.get("molecule") != PRIMARY_CANDIDATE_MOLECULE]
    extension_rows = [extension_row(row) for row in remaining_rows]
    blocked_count = sum(1 for row in extension_rows if not row["f1_extension_acceptance_ready"])
    preview_row_count = len(extension_rows)
    accepted_candidate_count = int(prior_summary.get("candidate_row_count", 0))
    four_row_scope_known = accepted_candidate_count + preview_row_count == EXPECTED_F1_ROW_COUNT
    no_claims = (
        pressure.get("summary", {}).get("reaction_dynamics_solution_claimed") is False
        and pressure.get("summary", {}).get("quantum_advantage_claimed") is False
        and pressure.get("summary", {}).get("selected_ci_larger_basis_denominator_beaten_count") == 0
        and prior_summary.get("b10_t1_credit_allowed") is False
    )

    requirements = [
        requirement(
            "P1",
            pressure.get("method") == EXPECTED_PRESSURE_METHOD
            and not pressure.get("validation_errors"),
            "Cross-molecule pressure source is valid",
            {
                "method": pressure.get("method"),
                "validation_error_count": len(pressure.get("validation_errors", [])),
                "source_file_hash": file_hash(args.cross_molecule_pressure),
            },
        ),
        requirement(
            "P2",
            prior.get("method") == EXPECTED_CANDIDATE_METHOD
            and prior_summary.get("candidate_row_count") == 1
            and prior_summary.get("validation_error_count") == 0,
            "Prior H2 F1 pilot candidate remains valid",
            {
                "method": prior.get("method"),
                "candidate_row_count": prior_summary.get("candidate_row_count"),
                "candidate_row_hash": prior_summary.get("candidate_row_hash"),
            },
        ),
        requirement(
            "P3",
            len(rows) == EXPECTED_F1_ROW_COUNT and four_row_scope_known,
            "Four row-aligned molecules are identified across prior candidate and pressure scout",
            {
                "pressure_row_count": len(rows),
                "prior_candidate_count": accepted_candidate_count,
                "remaining_extension_row_count": preview_row_count,
            },
        ),
        requirement(
            "P4",
            preview_row_count == 3
            and {row["molecule"] for row in extension_rows}
            == {"lih_bond_stretch", "h2o_symmetric_oh_stretch", "n2_bond_stretch"},
            "Remaining LiH/H2O/N2 extension rows are enumerated",
            {"remaining_molecules": [row["molecule"] for row in extension_rows]},
        ),
        requirement(
            "P5",
            all(int(row.get("pilot_group_count") or 0) > 0 for row in extension_rows),
            "Each remaining row has sampled pressure preview evidence",
            {
                "pilot_group_counts": {
                    row["molecule"]: row["pilot_group_count"] for row in extension_rows
                },
                "pilot_max_relative_variance_errors": {
                    row["molecule"]: row["pilot_max_relative_variance_error"]
                    for row in extension_rows
                },
            },
        ),
        requirement(
            "P6",
            all(int(row.get("optimizer_loop_total_shots_lower_bound") or 0) > 0 for row in extension_rows),
            "Each remaining row keeps optimizer-loop cost pressure charged",
            {
                "optimizer_loop_total_shots_lower_bounds": {
                    row["molecule"]: row["optimizer_loop_total_shots_lower_bound"]
                    for row in extension_rows
                },
                "max_optimizer_loop_total_shots_lower_bound": pressure.get("summary", {}).get(
                    "max_optimizer_loop_total_shots_lower_bound"
                ),
            },
        ),
        requirement(
            "P7",
            no_claims,
            "No reaction-dynamics, denominator-win, quantum-advantage, or B10 credit claim is made",
            {
                "selected_ci_larger_basis_denominator_beaten_count": pressure.get("summary", {}).get(
                    "selected_ci_larger_basis_denominator_beaten_count"
                ),
                "reaction_dynamics_solution_claimed": pressure.get("summary", {}).get(
                    "reaction_dynamics_solution_claimed"
                ),
                "quantum_advantage_claimed": pressure.get("summary", {}).get(
                    "quantum_advantage_claimed"
                ),
                "b10_t1_credit_allowed": prior_summary.get("b10_t1_credit_allowed"),
            },
        ),
        requirement(
            "P8",
            all(row["f1_extension_acceptance_ready"] for row in extension_rows),
            "Remaining rows satisfy F1 full-covariance acceptance requirements",
            {
                "blocked_extension_row_count": blocked_count,
                "blocked_reasons_by_row": {
                    row["molecule"]: row["blocked_reasons"] for row in extension_rows
                },
            },
        ),
        requirement(
            "P9",
            accepted_candidate_count + sum(
                1 for row in extension_rows if row["f1_extension_acceptance_ready"]
            )
            == EXPECTED_F1_ROW_COUNT,
            "F1 has four acceptable row candidates",
            {
                "acceptable_candidate_count": accepted_candidate_count
                + sum(1 for row in extension_rows if row["f1_extension_acceptance_ready"]),
                "required_f1_row_count": EXPECTED_F1_ROW_COUNT,
            },
        ),
        requirement(
            "P10",
            False,
            "Four-row F1 artifact is submitted and accepted",
            {
                "submitted_f1_artifact_exists": False,
                "accepted_full_covariance_row_count": 0,
            },
        ),
    ]
    failed = [item["id"] for item in requirements if not item["passed"]]
    validation_errors: list[str] = []
    if failed != ["P8", "P9", "P10"]:
        validation_errors.append(f"unexpected_failed_requirement_ids:{failed}")
    if blocked_count != 3:
        validation_errors.append(f"unexpected_blocked_extension_row_count:{blocked_count}")

    summary = {
        "prior_candidate_row_count": accepted_candidate_count,
        "remaining_extension_row_count": preview_row_count,
        "blocked_extension_row_count": blocked_count,
        "required_f1_row_count": EXPECTED_F1_ROW_COUNT,
        "acceptable_f1_row_count": accepted_candidate_count,
        "missing_acceptable_f1_row_count": EXPECTED_F1_ROW_COUNT - accepted_candidate_count,
        "extension_scout_hash": canonical_hash(extension_rows),
        "requirements_passed": len(requirements) - len(failed),
        "requirements_failed": len(failed),
        "failed_requirement_ids": failed,
        "max_remaining_row_pilot_relative_variance_error": max(
            row["pilot_max_relative_variance_error"] for row in extension_rows
        ),
        "max_optimizer_loop_total_shots_lower_bound": pressure.get("summary", {}).get(
            "max_optimizer_loop_total_shots_lower_bound"
        ),
        "max_optimizer_loop_two_qubit_executions_lower_bound": pressure.get("summary", {}).get(
            "max_optimizer_loop_two_qubit_executions_lower_bound"
        ),
        "accepted_full_covariance_row_count": 0,
        "denominator_win_count": 0,
        "b3_reopen_ready": False,
        "b10_t1_credit_allowed": False,
        "quantum_advantage_claimed": False,
        "reaction_dynamics_solution_claimed": False,
        "bqp_separation_claimed": False,
        "validation_error_count": len(validation_errors),
    }

    return {
        "benchmark_id": "B3_B10",
        "problem_ids": ["B3", "B10"],
        "source_target_id": SOURCE_TARGET_ID,
        "title": "B3/B10 F1 Remaining Row Extension Scout",
        "version": "0.1",
        "last_updated": args.last_updated,
        "status": STATUS,
        "method": METHOD,
        "model_status": MODEL_STATUS,
        "source_cross_molecule_pressure": str(args.cross_molecule_pressure),
        "source_prior_candidate_gate": str(args.prior_candidate_gate),
        "extension_rows": extension_rows,
        "requirements": requirements,
        "summary": summary,
        "claim_boundary": {
            "what_is_supported": (
                "The remaining LiH, H2O, and N2 row-extension targets are identified from "
                "cross-molecule pressure evidence, with sampled preview and optimizer-cost ledgers."
            ),
            "what_is_not_supported": (
                "The remaining rows are not acceptable F1 rows because they use bounded subset "
                "pressure rather than full compiled-state covariance, are not converged "
                "multi-parameter states, and do not beat same-access denominators."
            ),
            "next_gate": (
                "For each remaining molecule, compute full compiled-state covariance over the full "
                "QWC cover, preserve replay hashes, then resubmit the four-row F1 artifact."
            ),
        },
        "validation_errors": validation_errors,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# B3/B10 F1 Remaining Row Extension Scout",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Extension scout hash: `{summary['extension_scout_hash']}`",
        "",
        "## Result",
        "",
        (
            "The scout identifies the three remaining F1 row-extension targets from the "
            "cross-molecule pressure run. It passes "
            f"{summary['requirements_passed']}/"
            f"{summary['requirements_passed'] + summary['requirements_failed']} requirements "
            f"and intentionally fails {summary['failed_requirement_ids']} because the LiH/H2O/N2 "
            "rows are bounded pressure previews, not acceptable full compiled-state covariance rows."
        ),
        "",
        "## Remaining Rows",
        "",
        "| molecule | pilot groups | max rel err | optimizer shots lower bound | blocked reasons |",
        "|---|---:|---:|---:|---|",
    ]
    for row in payload["extension_rows"]:
        lines.append(
            "| "
            f"{row['molecule']} | {row['pilot_group_count']} | "
            f"{row['pilot_max_relative_variance_error']} | "
            f"{row['optimizer_loop_total_shots_lower_bound']} | "
            f"{', '.join(row['blocked_reasons'])} |"
        )
    lines.extend(
        [
            "",
            "## Requirement Results",
            "",
        ]
    )
    for req in payload["requirements"]:
        status = "PASS" if req["passed"] else "FAIL"
        lines.append(f"- `{req['id']}` {status}: {req['description']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            "",
            "This scout does not claim a reaction-dynamics solution, quantum advantage, B3 reopen credit, B10-T1 credit, or BQP separation.",
            "",
            "## Validation",
            "",
            f"- validation_error_count: `{summary['validation_error_count']}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cross-molecule-pressure",
        type=Path,
        default=Path("results/B3_cross_molecule_ucc_adapt_pressure_v0.json"),
    )
    parser.add_argument(
        "--prior-candidate-gate",
        type=Path,
        default=Path("results/B3_B10_F1_pilot_row_candidate_gate_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B3_B10_F1_remaining_row_extension_scout_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B3_B10_F1_remaining_row_extension_scout.md"),
    )
    parser.add_argument("--last-updated", default="2026-07-03")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args)
    write_json(args.json_output, payload, args.pretty)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "extension_scout_hash": payload["summary"]["extension_scout_hash"],
                "requirements_passed": payload["summary"]["requirements_passed"],
                "requirements_failed": payload["summary"]["requirements_failed"],
                "failed_requirement_ids": payload["summary"]["failed_requirement_ids"],
                "blocked_extension_row_count": payload["summary"]["blocked_extension_row_count"],
                "validation_error_count": payload["summary"]["validation_error_count"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if payload["validation_errors"]:
        raise SystemExit("B3/B10 F1 remaining row extension scout validation failed")


if __name__ == "__main__":
    main()
