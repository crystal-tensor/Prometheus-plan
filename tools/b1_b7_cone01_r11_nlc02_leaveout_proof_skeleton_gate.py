#!/usr/bin/env python3
"""T-B1-004dm/T-B7-012v: R11 NL-C02 leave-out proof-skeleton gate."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r11_nlc02_leaveout_proof_skeleton_gate_v0"
STATUS = "cone01_r11_nlc02_leaveout_proof_skeleton_ready_unchecked"
MODEL_STATUS = "nlc02_leaveout_domain_harness_ready_but_not_checked_lemma"
VERSION = "0.1"
TARGET_ID = "T-B1-004dm/T-B7-012v"
SKELETON_ID = "B1-B7-cone01-R11-NL-C02-leaveout-proof-skeleton"
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


def row_list_name(size: int) -> str:
    names = {
        1: "line1381_leave_one_out_parameter_rows",
        2: "line1381_leave_two_out_parameter_rows",
        3: "line1381_leave_three_out_parameter_rows",
        4: "line1381_leave_four_out_parameter_rows",
        5: "line1381_leave_five_out_parameter_rows",
    }
    return names[size]


def summary_row_count_key(size: int) -> str:
    names = {
        1: "leave_one_out_row_count",
        2: "leave_two_out_row_count",
        3: "leave_three_out_row_count",
        4: "leave_four_out_row_count",
        5: "leave_five_out_row_count",
    }
    return names[size]


def summary_pass_count_key(size: int) -> str:
    names = {
        1: "leave_one_out_exact_pass_count",
        2: "leave_two_out_exact_pass_count",
        3: "leave_three_out_exact_pass_count",
        4: "leave_four_out_exact_pass_count",
        5: "leave_five_out_exact_pass_count",
    }
    return names[size]


def summary_fail_count_key(size: int) -> str:
    names = {
        1: "leave_one_out_exact_fail_count",
        2: "leave_two_out_exact_fail_count",
        3: "leave_three_out_exact_fail_count",
        4: "leave_four_out_exact_fail_count",
        5: "leave_five_out_exact_fail_count",
    }
    return names[size]


def fixed_indices(row: dict[str, Any]) -> list[int]:
    if "fixed_parameter_indices" in row:
        return [int(v) for v in row["fixed_parameter_indices"]]
    if "all_grid_fixed_parameter_indices" in row:
        return [int(v) for v in row["all_grid_fixed_parameter_indices"]]
    return [int(row["fixed_parameter_index"])]


def residual_norm(row: dict[str, Any]) -> float:
    if "residual_norm" in row:
        return float(row["residual_norm"])
    return float(row["all_grid_residual_ratio_to_exact_tolerance"]) * 1e-8


def normalize_rows(leave_paths: list[Path], leave_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for size, (path, payload) in enumerate(zip(leave_paths, leave_payloads), start=1):
        for row in payload[row_list_name(size)]:
            indices = fixed_indices(row)
            rows.append(
                {
                    "source_path": str(path),
                    "subset_size": size,
                    "fixed_parameter_indices": indices,
                    "subset_key": ",".join(str(v) for v in indices),
                    "exact_pass": bool(row["exact_pass"]) if "exact_pass" in row else False,
                    "optimizer_success": bool(row.get("optimizer_success", True)),
                    "residual_norm": residual_norm(row),
                }
            )
    return sorted(rows, key=lambda row: (row["subset_size"], row["fixed_parameter_indices"]))


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    r10 = load_json(args.r10_registry)
    r10s = r10["summary"]
    leave_paths = [
        args.leave_one,
        args.leave_two,
        args.leave_three,
        args.leave_four,
        args.leave_five,
    ]
    leave_payloads = [load_json(path) for path in leave_paths]
    leave_summaries = [payload["summary"] for payload in leave_payloads]

    candidates = r10["negative_lemma_candidate_registry"]["candidate_negative_lemmas"]
    nlc02 = next((row for row in candidates if row["candidate_id"] == CANDIDATE_ID), None)
    if nlc02 is None:
        raise SystemExit("R10 registry does not contain NL-C02")

    parameter_domain = leave_summaries[0]["current_off_grid_parameter_indices"]
    expected_subsets = {
        ",".join(str(v) for v in combo)
        for size in range(1, 6)
        for combo in itertools.combinations(parameter_domain, size)
    }
    normalized_rows = normalize_rows(leave_paths, leave_payloads)
    observed_subsets = {row["subset_key"] for row in normalized_rows}
    exact_pass_rows = [row for row in normalized_rows if row["exact_pass"]]
    min_residual = min(row["residual_norm"] for row in normalized_rows)
    max_residual = max(row["residual_norm"] for row in normalized_rows)
    exact_tolerances = {summary["exact_tolerance"] for summary in leave_summaries}
    validation_counts = [summary["validation_error_count"] for summary in leave_summaries]

    proof_skeleton = {
        "skeleton_id": SKELETON_ID,
        "source_target_id": TARGET_ID,
        "candidate_id": CANDIDATE_ID,
        "candidate_title": nlc02["title"],
        "candidate_source_registry_hash": r10s["registry_hash"],
        "candidate_source_r9_pressure_hash": r10s["r9_pressure_hash"],
        "covered_parameter_domain": parameter_domain,
        "covered_subset_count": len(expected_subsets),
        "observed_subset_count": len(observed_subsets),
        "row_table_hash": stable_hash(normalized_rows),
        "source_hashes": {
            "r10_registry": file_hash(args.r10_registry),
            "leave_one": file_hash(args.leave_one),
            "leave_two": file_hash(args.leave_two),
            "leave_three": file_hash(args.leave_three),
            "leave_four": file_hash(args.leave_four),
            "leave_five": file_hash(args.leave_five),
        },
        "lemma_statement_candidate": (
            "Under the current R1 line1381 five-parameter off-grid domain, declared tolerance, "
            "and leave-out optimizer model, no nonempty subset of the five parameters can be snapped "
            "to the pi/4 grid while preserving an exact replay."
        ),
        "machine_checked_facts": [
            "all 31 nonempty subsets are present",
            "all 31 rows have exact_pass=false",
            "all five leave-out gates use the same exact_tolerance",
            "all five leave-out gates report validation_error_count=0",
            "the minimum residual norm remains above exact_tolerance",
        ],
        "open_proof_obligations": [
            {
                "obligation_id": "O1",
                "title": "Optimizer completeness boundary",
                "needed_for_checked_lemma": True,
                "description": (
                    "Prove that each leave-out optimization search is complete for the declared "
                    "parameterization, or explicitly downgrade the lemma to a search-domain lemma."
                ),
            },
            {
                "obligation_id": "O2",
                "title": "Tolerance-to-exactness bridge",
                "needed_for_checked_lemma": True,
                "description": (
                    "Justify that residual_norm > exact_tolerance excludes exact replay in the "
                    "accepted arithmetic model."
                ),
            },
            {
                "obligation_id": "O3",
                "title": "Parameterization invariance",
                "needed_for_checked_lemma": True,
                "description": (
                    "Show that no equivalent reparameterization of the same local unitary falls "
                    "outside the leave-out table while still clearing Route A."
                ),
            },
            {
                "obligation_id": "O4",
                "title": "Source-domain binding",
                "needed_for_checked_lemma": True,
                "description": (
                    "Bind the five-parameter domain to the R7/R8/R9 source hashes and rule out "
                    "accidental drift in line1381 indexing."
                ),
            },
        ],
        "falsification_harness": [
            {
                "test_id": "F1",
                "description": "Find an observed subset row with exact_pass=true.",
                "current_result": len(exact_pass_rows) == 0,
            },
            {
                "test_id": "F2",
                "description": "Find a missing nonempty subset of the five-parameter domain.",
                "current_result": observed_subsets == expected_subsets,
            },
            {
                "test_id": "F3",
                "description": "Find any leave-out gate with validation_error_count > 0.",
                "current_result": all(count == 0 for count in validation_counts),
            },
            {
                "test_id": "F4",
                "description": "Find inconsistent exact_tolerance values across leave-out gates.",
                "current_result": len(exact_tolerances) == 1,
            },
            {
                "test_id": "F5",
                "description": "Find residual_norm <= exact_tolerance in any normalized row.",
                "current_result": min_residual > next(iter(exact_tolerances)),
            },
        ],
        "claim_decision": {
            "checked_negative_lemma_present": False,
            "candidate_proof_skeleton_ready": True,
            "falsification_harness_ready": True,
            "reroute_allowed": False,
            "why": (
                "The finite row coverage is machine-checked, but O1-O4 remain open, so this is a "
                "proof skeleton and falsification harness, not a checked negative lemma."
            ),
        },
    }
    proof_skeleton["skeleton_hash"] = stable_hash(proof_skeleton)

    total_row_count = sum(summary[summary_row_count_key(size)] for size, summary in enumerate(leave_summaries, start=1))
    total_pass_count = sum(summary[summary_pass_count_key(size)] for size, summary in enumerate(leave_summaries, start=1))
    total_fail_count = sum(summary[summary_fail_count_key(size)] for size, summary in enumerate(leave_summaries, start=1))
    missing_subsets = sorted(expected_subsets - observed_subsets)
    extra_subsets = sorted(observed_subsets - expected_subsets)

    requirements = [
        requirement(
            "S1",
            "R10 registry contains NL-C02 and remains validation-clean",
            r10.get("method") == "b1_b7_cone01_r10_r1_negative_lemma_candidate_registry_gate_v0"
            and r10s.get("validation_error_count") == 0
            and nlc02 is not None,
            {
                "r10_method": r10.get("method"),
                "r10_validation_error_count": r10s.get("validation_error_count"),
                "candidate_id": CANDIDATE_ID,
            },
        ),
        requirement(
            "S2",
            "All five leave-out source gates are validation-clean",
            all(count == 0 for count in validation_counts),
            {"validation_error_counts": validation_counts},
        ),
        requirement(
            "S3",
            "The five-parameter domain is stable across leave-out gates",
            all(summary["current_off_grid_parameter_indices"] == parameter_domain for summary in leave_summaries)
            and len(parameter_domain) == 5,
            {"parameter_domain": parameter_domain},
        ),
        requirement(
            "S4",
            "All 31 nonempty leave-out subsets are covered exactly once",
            len(expected_subsets) == 31
            and len(observed_subsets) == 31
            and observed_subsets == expected_subsets
            and total_row_count == 31,
            {
                "expected_subset_count": len(expected_subsets),
                "observed_subset_count": len(observed_subsets),
                "total_row_count": total_row_count,
                "missing_subsets": missing_subsets,
                "extra_subsets": extra_subsets,
            },
        ),
        requirement(
            "S5",
            "All leave-out exact passes remain zero",
            total_pass_count == 0 and total_fail_count == 31 and len(exact_pass_rows) == 0,
            {
                "total_pass_count": total_pass_count,
                "total_fail_count": total_fail_count,
                "exact_pass_row_count": len(exact_pass_rows),
            },
        ),
        requirement(
            "S6",
            "Exact tolerance is consistent and every residual remains above tolerance",
            len(exact_tolerances) == 1 and min_residual > next(iter(exact_tolerances)),
            {
                "exact_tolerances": sorted(exact_tolerances),
                "min_residual_norm": min_residual,
                "max_residual_norm": max_residual,
            },
        ),
        requirement(
            "S7",
            "Proof skeleton records all four open obligations",
            len(proof_skeleton["open_proof_obligations"]) == 4
            and all(row["needed_for_checked_lemma"] for row in proof_skeleton["open_proof_obligations"]),
            {"open_obligation_count": len(proof_skeleton["open_proof_obligations"])},
        ),
        requirement(
            "S8",
            "Falsification harness records five executable checks",
            len(proof_skeleton["falsification_harness"]) == 5
            and all(row["current_result"] is True for row in proof_skeleton["falsification_harness"]),
            {"falsification_check_count": len(proof_skeleton["falsification_harness"])},
        ),
        requirement(
            "S9",
            "All source files are hash-bound",
            all(value for value in proof_skeleton["source_hashes"].values())
            and bool(proof_skeleton["row_table_hash"]),
            {"source_hash_count": len(proof_skeleton["source_hashes"])},
        ),
        requirement(
            "S10",
            "Skeleton is not upgraded into a checked lemma or reroute",
            proof_skeleton["claim_decision"]["checked_negative_lemma_present"] is False
            and proof_skeleton["claim_decision"]["reroute_allowed"] is False,
            proof_skeleton["claim_decision"],
        ),
    ]

    passed = sum(row["passed"] for row in requirements)
    failed_ids = [row["requirement_id"] for row in requirements if not row["passed"]]
    validation_errors: list[str] = []
    if failed_ids:
        validation_errors.append(f"unexpected R11 proof-skeleton failures: {failed_ids}")

    summary = {
        "skeleton_id": SKELETON_ID,
        "skeleton_hash": proof_skeleton["skeleton_hash"],
        "row_table_hash": proof_skeleton["row_table_hash"],
        "source_r10_registry_hash": r10s.get("registry_hash"),
        "source_r9_pressure_hash": r10s.get("r9_pressure_hash"),
        "candidate_id": CANDIDATE_ID,
        "covered_parameter_count": len(parameter_domain),
        "expected_subset_count": len(expected_subsets),
        "observed_subset_count": len(observed_subsets),
        "leave_out_row_count": total_row_count,
        "leave_out_exact_pass_count": total_pass_count,
        "leave_out_exact_fail_count": total_fail_count,
        "open_proof_obligation_count": len(proof_skeleton["open_proof_obligations"]),
        "falsification_check_count": len(proof_skeleton["falsification_harness"]),
        "min_residual_norm": min_residual,
        "max_residual_norm": max_residual,
        "exact_tolerance": next(iter(exact_tolerances)) if len(exact_tolerances) == 1 else None,
        "checked_negative_lemma_present": False,
        "candidate_proof_skeleton_ready": True,
        "falsification_harness_ready": True,
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
        "title": "B1/B7 Cone01 R11 NL-C02 Leave-Out Proof-Skeleton Gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "summary": summary,
        "nlc02_leaveout_proof_skeleton": proof_skeleton,
        "normalized_leaveout_rows": normalized_rows,
        "requirements": requirements,
        "claim_boundary": {
            "what_is_supported": (
                "R11 proves the finite leave-out row coverage and creates a falsification harness "
                "for NL-C02 under the current search-domain evidence."
            ),
            "what_is_not_supported": (
                "R11 is not a checked negative lemma. Optimizer completeness, tolerance-to-exactness, "
                "parameterization invariance, and source-domain binding remain open proof obligations. "
                "No R5 reroute, R1 solution, occurrence removal, proxy-T reduction, B7 credit, resource "
                "saving, or impossibility theorem is supported."
            ),
            "next_gate": (
                "Close O1-O4 or falsify NL-C02 with an exact leave-out pass, missing subset, validation "
                "error, tolerance inconsistency, or residual below tolerance."
            ),
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "validation_errors": validation_errors,
        "runtime_seconds": round(time.time() - started, 6),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    skeleton = payload["nlc02_leaveout_proof_skeleton"]
    lines = [
        f"# {payload['title']}",
        "",
        f"- Target: `{payload['source_target_id']}`",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Candidate: `{s['candidate_id']}`",
        f"- Skeleton hash: `{s['skeleton_hash']}`",
        f"- Row-table hash: `{s['row_table_hash']}`",
        f"- R10 registry hash: `{s['source_r10_registry_hash']}`",
        "",
        "## Result",
        "",
        (
            f"The R11 NL-C02 proof-skeleton gate passes {s['requirements_passed']}/{s['requirement_count']} "
            "requirements. It machine-checks the finite leave-out coverage and creates a falsification "
            "harness, but it does not claim a checked negative lemma."
        ),
        "",
        "## Machine-Checked Facts",
        "",
    ]
    for fact in skeleton["machine_checked_facts"]:
        lines.append(f"- {fact}")
    lines.extend(
        [
            "",
            "## Coverage",
            "",
            f"- Covered parameter count: `{s['covered_parameter_count']}`",
            f"- Expected / observed nonempty subsets: `{s['expected_subset_count']}` / `{s['observed_subset_count']}`",
            f"- Leave-out rows / exact passes / exact failures: `{s['leave_out_row_count']}` / `{s['leave_out_exact_pass_count']}` / `{s['leave_out_exact_fail_count']}`",
            f"- Exact tolerance: `{s['exact_tolerance']}`",
            f"- Residual norm range: `{s['min_residual_norm']}` to `{s['max_residual_norm']}`",
            "",
            "## Open Proof Obligations",
            "",
        ]
    )
    for row in skeleton["open_proof_obligations"]:
        lines.append(f"- `{row['obligation_id']}` {row['title']}: {row['description']}")
    lines.extend(
        [
            "",
            "## Falsification Harness",
            "",
        ]
    )
    for row in skeleton["falsification_harness"]:
        lines.append(f"- `{row['test_id']}` {row['description']} Current pass: `{row['current_result']}`")
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- Checked negative lemma present: `{s['checked_negative_lemma_present']}`",
            f"- Candidate proof skeleton ready: `{s['candidate_proof_skeleton_ready']}`",
            f"- Falsification harness ready: `{s['falsification_harness_ready']}`",
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
            "This proof-skeleton gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, a checked impossibility theorem, an R5 reroute, or a solved B1/B7 problem.",
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
        "--r10-registry",
        type=Path,
        default=Path("results/B1_B7_cone01_R10_r1_negative_lemma_candidate_registry_gate_v0.json"),
    )
    parser.add_argument(
        "--leave-one",
        type=Path,
        default=Path("results/B1_B7_cone01_line1381_leave_one_out_parameter_gate_v0.json"),
    )
    parser.add_argument(
        "--leave-two",
        type=Path,
        default=Path("results/B1_B7_cone01_line1381_leave_two_out_parameter_gate_v0.json"),
    )
    parser.add_argument(
        "--leave-three",
        type=Path,
        default=Path("results/B1_B7_cone01_line1381_leave_three_out_parameter_gate_v0.json"),
    )
    parser.add_argument(
        "--leave-four",
        type=Path,
        default=Path("results/B1_B7_cone01_line1381_leave_four_out_parameter_gate_v0.json"),
    )
    parser.add_argument(
        "--leave-five",
        type=Path,
        default=Path("results/B1_B7_cone01_line1381_leave_five_out_parameter_gate_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_R11_nlc02_leaveout_proof_skeleton_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_R11_nlc02_leaveout_proof_skeleton_gate.md"),
    )
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
                "skeleton_hash": payload["summary"]["skeleton_hash"],
                "row_table_hash": payload["summary"]["row_table_hash"],
                "leave_out_row_count": payload["summary"]["leave_out_row_count"],
                "leave_out_exact_pass_count": payload["summary"]["leave_out_exact_pass_count"],
                "open_proof_obligation_count": payload["summary"]["open_proof_obligation_count"],
                "falsification_check_count": payload["summary"]["falsification_check_count"],
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
        raise SystemExit("B1/B7 R11 NL-C02 proof-skeleton gate validation failed")


if __name__ == "__main__":
    main()
