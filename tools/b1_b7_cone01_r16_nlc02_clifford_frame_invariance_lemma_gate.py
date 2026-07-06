#!/usr/bin/env python3
"""T-B1-004dr/T-B7-013a: R16 NL-C02 Clifford-frame invariance lemma gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r16_nlc02_clifford_frame_invariance_lemma_gate_v0"
STATUS = "cone01_r16_nlc02_clifford_frame_invariance_sublemma_closed_o3_still_open"
MODEL_STATUS = "nlc02_clifford_frame_affine_invariance_sublemma_closed_but_o3_unclosed"
VERSION = "0.1"
TARGET_ID = "T-B1-004dr/T-B7-013a"
SCREEN_ID = "B1-B7-cone01-R16-NL-C02-clifford-frame-invariance-sublemma"
CANDIDATE_ID = "NL-C02"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def stable_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def file_hash(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def requirement(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def nearest_pi_over_four(value: float) -> tuple[int, float]:
    numerator = round(value / (math.pi / 4))
    error = abs(value - numerator * (math.pi / 4))
    return numerator, error


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    r15 = load_json(args.r15_screen)
    exact = load_json(args.exact_decomposition)
    r15s = r15["summary"]
    exacts = exact["summary"]
    exact_rows = exact["line1381_exact_decomposition_pressure_rows"]

    signs = [-1, 1]
    clifford_frame_shifts_pi_over_2 = list(range(-4, 5))
    period_shifts_2pi = [-2, -1, 0, 1, 2]
    tolerance = float(args.grid_tolerance)

    proof_rows = []
    invariant_probe_count = 0
    max_invariance_error_delta = 0.0
    best_parameter_rows = []

    for row in exact_rows:
        parameter_index = int(row["parameter_index"])
        source_value = float(row["parameter_value"])
        base_numerator, base_error = nearest_pi_over_four(source_value)
        candidate_errors = []
        for sign in signs:
            for frame_shift in clifford_frame_shifts_pi_over_2:
                for period_shift in period_shifts_2pi:
                    shifted = (
                        sign * source_value
                        + frame_shift * (math.pi / 2)
                        + period_shift * 2 * math.pi
                    )
                    numerator, error = nearest_pi_over_four(shifted)
                    delta = abs(error - base_error)
                    max_invariance_error_delta = max(max_invariance_error_delta, delta)
                    invariant_probe_count += 1
                    candidate_errors.append(error)
        min_error = min(candidate_errors)
        max_error = max(candidate_errors)
        proof_rows.append(
            {
                "parameter_index": parameter_index,
                "source_value": source_value,
                "base_nearest_pi_over_four_numerator": base_numerator,
                "base_nearest_pi_over_four_error": base_error,
                "invariant_family_min_error": min_error,
                "invariant_family_max_error": max_error,
                "family_preserves_distance": abs(max_error - min_error) <= tolerance,
                "grid_escape_possible_under_family": min_error <= tolerance,
            }
        )
        best_parameter_rows.append(
            {
                "parameter_index": parameter_index,
                "base_nearest_pi_over_four_error": base_error,
                "invariant_family_min_error": min_error,
                "grid_escape_possible_under_family": min_error <= tolerance,
            }
        )

    accepted = [row for row in proof_rows if row["grid_escape_possible_under_family"]]
    parameter_indices = sorted(row["parameter_index"] for row in proof_rows)
    min_error = min(row["invariant_family_min_error"] for row in proof_rows)
    max_error = max(row["invariant_family_max_error"] for row in proof_rows)
    all_preserve = all(row["family_preserves_distance"] for row in proof_rows)

    lemma_packet = {
        "lemma_id": SCREEN_ID,
        "source_target_id": TARGET_ID,
        "candidate_id": CANDIDATE_ID,
        "source_r15_screen": str(args.r15_screen),
        "source_exact_decomposition": str(args.exact_decomposition),
        "source_hashes": {
            "r15_screen": file_hash(args.r15_screen),
            "exact_decomposition": file_hash(args.exact_decomposition),
        },
        "source_r15_screen_hash": r15s["screen_hash"],
        "source_r15_probe_table_hash": r15s["probe_table_hash"],
        "canonical_parameter_indices": r15s["canonical_parameter_indices"],
        "invariance_statement": (
            "For G(x)=s*x+k*pi/2+2*pi*m with s in {-1,1}, k in Z, m in Z, "
            "distance from G(x) to the pi/4 lattice equals distance from x to the pi/4 lattice."
        ),
        "proof_sketch": [
            "pi/2 is 2*(pi/4), so k*pi/2 shifts by an integer number of pi/4 lattice units.",
            "2*pi is 8*(pi/4), so period shifts also preserve the pi/4 lattice.",
            "The sign flip maps the pi/4 lattice to itself and preserves absolute distance.",
            "Therefore the finite R15 Clifford-frame affine family cannot turn a non-grid parameter into a pi/4-grid parameter.",
        ],
        "signs": signs,
        "clifford_frame_shifts_pi_over_2": clifford_frame_shifts_pi_over_2,
        "period_shifts_2pi": period_shifts_2pi,
        "grid_tolerance": tolerance,
        "proof_rows": proof_rows,
        "accepted_escape_count": len(accepted),
        "decision": {
            "clifford_frame_invariance_sublemma_closed": all_preserve and len(accepted) == 0,
            "o3_closed": False,
            "checked_negative_lemma_present": False,
            "nlc02_full_lemma_ready": False,
            "reroute_allowed": False,
            "why": (
                "R16 closes only the Clifford-frame affine sublemma. O3 remains open because "
                "general local-unitary reparameterization invariance and O1 optimizer completeness are not proved."
            ),
        },
    }
    lemma_packet["proof_table_hash"] = stable_hash(proof_rows)
    lemma_packet["lemma_hash"] = stable_hash(lemma_packet)

    requirements = [
        requirement(
            "G1",
            "R15 source screen is validation-clean and contains the expected 450 probes",
            r15.get("method") == "b1_b7_cone01_r15_nlc02_clifford_frame_screen_gate_v0"
            and r15s.get("validation_error_count") == 0
            and r15s.get("probe_count") == 450
            and r15s.get("accepted_escape_count") == 0,
            {
                "r15_method": r15.get("method"),
                "r15_validation_error_count": r15s.get("validation_error_count"),
                "r15_probe_count": r15s.get("probe_count"),
                "r15_accepted_escape_count": r15s.get("accepted_escape_count"),
            },
        ),
        requirement(
            "G2",
            "Exact-decomposition source remains validation-clean with five off-grid parameters",
            exact.get("method") == "b1_b7_cone01_line1381_exact_decomposition_pressure_gate_v0"
            and exacts.get("validation_error_count") == 0
            and exacts.get("remaining_off_grid_parameter_count") == 5,
            {
                "exact_method": exact.get("method"),
                "validation_error_count": exacts.get("validation_error_count"),
                "remaining_off_grid_parameter_count": exacts.get("remaining_off_grid_parameter_count"),
            },
        ),
        requirement(
            "G3",
            "Lemma covers the R15 canonical parameter domain",
            parameter_indices == r15s["canonical_parameter_indices"],
            {
                "parameter_indices": parameter_indices,
                "canonical_parameter_indices": r15s["canonical_parameter_indices"],
            },
        ),
        requirement(
            "G4",
            "Finite verification covers the same R15 Clifford-frame affine family",
            invariant_probe_count == r15s["probe_count"]
            and signs == [-1, 1]
            and clifford_frame_shifts_pi_over_2 == list(range(-4, 5))
            and period_shifts_2pi == [-2, -1, 0, 1, 2],
            {
                "invariant_probe_count": invariant_probe_count,
                "source_r15_probe_count": r15s["probe_count"],
                "signs": signs,
                "clifford_frame_shifts_pi_over_2": clifford_frame_shifts_pi_over_2,
                "period_shifts_2pi": period_shifts_2pi,
            },
        ),
        requirement(
            "G5",
            "Distance to the pi/4 lattice is invariant across the declared family",
            all_preserve and max_invariance_error_delta <= tolerance,
            {
                "all_family_rows_preserve_distance": all_preserve,
                "max_invariance_error_delta": max_invariance_error_delta,
                "grid_tolerance": tolerance,
            },
        ),
        requirement(
            "G6",
            "No member of the closed Clifford-frame affine sublemma reaches the pi/4 grid",
            len(accepted) == 0 and min_error > tolerance,
            {
                "accepted_escape_count": len(accepted),
                "min_pi_over_four_grid_error": min_error,
                "grid_tolerance": tolerance,
            },
        ),
        requirement(
            "G7",
            "R16 preserves the R15 error envelope",
            abs(min_error - r15s["min_pi_over_four_grid_error"]) <= 1e-12
            and abs(max_error - r15s["max_pi_over_four_grid_error"]) <= 1e-12,
            {
                "r16_min_error": min_error,
                "r15_min_error": r15s["min_pi_over_four_grid_error"],
                "r16_max_error": max_error,
                "r15_max_error": r15s["max_pi_over_four_grid_error"],
            },
        ),
        requirement(
            "G8",
            "Lemma is hash-bound to R15 and exact-decomposition sources",
            all(lemma_packet["source_hashes"].values())
            and bool(lemma_packet["proof_table_hash"])
            and bool(lemma_packet["lemma_hash"]),
            {
                "source_hashes": lemma_packet["source_hashes"],
                "proof_table_hash": lemma_packet["proof_table_hash"],
                "lemma_hash": lemma_packet["lemma_hash"],
            },
        ),
        requirement(
            "G9",
            "Sublemma closure does not close full O3 or upgrade NL-C02",
            lemma_packet["decision"]["clifford_frame_invariance_sublemma_closed"] is True
            and lemma_packet["decision"]["o3_closed"] is False
            and lemma_packet["decision"]["checked_negative_lemma_present"] is False
            and lemma_packet["decision"]["reroute_allowed"] is False,
            lemma_packet["decision"],
        ),
        requirement(
            "G10",
            "Lemma preserves zero resource and B7 credit claims",
            True,
            {
                "accepted_route_count": 0,
                "accepted_occurrence_removal": 0,
                "accepted_proxy_t_reduction": 0,
                "b7_credit_delta": 0,
                "b7_space_time_volume_credit": 0,
                "resource_saving_claimed": False,
                "b7_ledger_improvement_claimed": False,
            },
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids:
        validation_errors.append(f"unexpected R16 invariance lemma failures: {failed_ids}")

    summary = {
        "lemma_id": SCREEN_ID,
        "lemma_hash": lemma_packet["lemma_hash"],
        "proof_table_hash": lemma_packet["proof_table_hash"],
        "source_r15_screen_hash": r15s["screen_hash"],
        "source_r15_probe_table_hash": r15s["probe_table_hash"],
        "candidate_id": CANDIDATE_ID,
        "canonical_parameter_indices": r15s["canonical_parameter_indices"],
        "sign_count": len(signs),
        "clifford_frame_shift_count": len(clifford_frame_shifts_pi_over_2),
        "period_shift_count": len(period_shifts_2pi),
        "invariant_probe_count": invariant_probe_count,
        "proof_row_count": len(proof_rows),
        "accepted_escape_count": len(accepted),
        "min_pi_over_four_grid_error": min_error,
        "max_pi_over_four_grid_error": max_error,
        "max_invariance_error_delta": max_invariance_error_delta,
        "grid_tolerance": tolerance,
        "clifford_frame_invariance_sublemma_closed": lemma_packet["decision"][
            "clifford_frame_invariance_sublemma_closed"
        ],
        "o3_closed": False,
        "remaining_open_obligations": ["O1", "O3"],
        "remaining_open_obligation_count": 2,
        "checked_negative_lemma_present": False,
        "nlc02_full_lemma_ready": False,
        "reroute_allowed": False,
        "accepted_route_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "b7_credit_delta": 0,
        "b7_space_time_volume_credit": 0,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "requirement_count": len(requirements),
        "requirements_passed": passed,
        "requirements_failed": len(requirements) - passed,
        "failed_requirement_ids": failed_ids,
        "validation_error_count": len(validation_errors),
    }

    return {
        "benchmark_id": "B1",
        "linked_benchmark_id": "B7",
        "source_target_id": TARGET_ID,
        "title": "B1/B7 Cone01 R16 NL-C02 Clifford-Frame Invariance Lemma Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "summary": summary,
        "nlc02_clifford_frame_invariance_lemma_packet": lemma_packet,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "R16 proves the declared Clifford-frame affine family preserves distance to the pi/4 lattice "
                "over the R13-bound five-parameter domain, so the R15 450-probe negative result is promoted "
                "to a closed sublemma."
            ),
            "what_is_not_supported": (
                "R16 does not prove arbitrary local-unitary reparameterization invariance and does not close "
                "full O3. NL-C02 is still not a checked negative lemma. No R5 reroute, R1 solution, occurrence "
                "removal, proxy-T reduction, B7 credit, resource saving, or impossibility theorem is supported."
            ),
            "next_gate": (
                "Expand O3 beyond Clifford-frame affine invariance to a general local-unitary equivalence "
                "argument, or close O1 optimizer completeness; alternatively falsify the sublemma by finding "
                "an in-family transform that changes pi/4 lattice distance."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    packet = payload["nlc02_clifford_frame_invariance_lemma_packet"]
    lines = [
        f"# {payload['title']}",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Candidate: `{s['candidate_id']}`",
        f"- Lemma hash: `{s['lemma_hash']}`",
        f"- Proof-table hash: `{s['proof_table_hash']}`",
        "",
        "## Result",
        "",
        (
            f"The R16 Clifford-frame invariance lemma gate passes {s['requirements_passed']}/{s['requirement_count']} "
            "requirements. It closes the Clifford-frame affine sublemma used by R15, but O3 remains open."
        ),
        "",
        "## Invariance Statement",
        "",
        packet["invariance_statement"],
        "",
        "## Proof Sketch",
        "",
    ]
    for item in packet["proof_sketch"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Scope",
            "",
            f"- Parameters: `{s['canonical_parameter_indices']}`",
            f"- Signs: `{packet['signs']}`",
            f"- Clifford-frame shifts in pi/2 units: `{packet['clifford_frame_shifts_pi_over_2']}`",
            f"- Period shifts: `{packet['period_shifts_2pi']}`",
            f"- Invariant probe count: `{s['invariant_probe_count']}`",
            f"- Proof rows: `{s['proof_row_count']}`",
            f"- Accepted escape count: `{s['accepted_escape_count']}`",
            f"- Grid tolerance: `{s['grid_tolerance']}`",
            f"- Error range: `{s['min_pi_over_four_grid_error']}` to `{s['max_pi_over_four_grid_error']}`",
            f"- Max invariance error delta: `{s['max_invariance_error_delta']}`",
            "",
            "## Decision",
            "",
            f"- Clifford-frame invariance sublemma closed: `{s['clifford_frame_invariance_sublemma_closed']}`",
            f"- O3 closed: `{s['o3_closed']}`",
            f"- Remaining open obligations: `{s['remaining_open_obligations']}`",
            f"- Checked negative lemma present: `{s['checked_negative_lemma_present']}`",
            f"- Reroute allowed: `{s['reroute_allowed']}`",
            "",
            "## Requirement Results",
            "",
        ]
    )
    for row in payload["requirements"]:
        marker = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- `{row['requirement_id']}` {marker}: {row['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            "",
            "This lemma gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a checked impossibility theorem, an R5 reroute, or a solved B1/B7 problem.",
            "",
            "## Validation",
            "",
            f"- validation_error_count: `{s['validation_error_count']}`",
        ]
    )
    for error in payload["validation_errors"]:
        lines.append(f"- {error}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--r15-screen",
        type=Path,
        default=Path("results/B1_B7_cone01_R15_nlc02_clifford_frame_screen_gate_v0.json"),
    )
    parser.add_argument(
        "--exact-decomposition",
        type=Path,
        default=Path("results/B1_B7_cone01_line1381_exact_decomposition_pressure_gate_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_R16_nlc02_clifford_frame_invariance_lemma_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_R16_nlc02_clifford_frame_invariance_lemma_gate.md"),
    )
    parser.add_argument("--grid-tolerance", type=float, default=1e-8)
    parser.add_argument("--last-updated", default="2026-07-06")
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
                "lemma_hash": payload["summary"]["lemma_hash"],
                "proof_table_hash": payload["summary"]["proof_table_hash"],
                "invariant_probe_count": payload["summary"]["invariant_probe_count"],
                "accepted_escape_count": payload["summary"]["accepted_escape_count"],
                "min_pi_over_four_grid_error": payload["summary"]["min_pi_over_four_grid_error"],
                "max_invariance_error_delta": payload["summary"]["max_invariance_error_delta"],
                "clifford_frame_invariance_sublemma_closed": payload["summary"][
                    "clifford_frame_invariance_sublemma_closed"
                ],
                "o3_closed": payload["summary"]["o3_closed"],
                "remaining_open_obligations": payload["summary"]["remaining_open_obligations"],
                "reroute_allowed": payload["summary"]["reroute_allowed"],
                "requirements_passed": payload["summary"]["requirements_passed"],
                "requirements_failed": payload["summary"]["requirements_failed"],
                "validation_error_count": payload["summary"]["validation_error_count"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    if payload["validation_errors"]:
        raise SystemExit("B1/B7 R16 Clifford-frame invariance lemma gate validation failed")


if __name__ == "__main__":
    main()
