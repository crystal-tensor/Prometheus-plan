#!/usr/bin/env python3
"""Restricted phase-removal gate for the B1/B7 gcm_h6 cone_01 target.

T-B1-004b found enough pair-local single-arbitrary windows in cone_01.  This
tool tests a deliberately narrow next hypothesis: can those windows remove the
single arbitrary RY by deletion or by a local Z-phase replacement while keeping
the same two-CNOT envelope?  Passing this test would still require replayable
certificates before any resource claim.  Failing it narrows T-B1-004 toward a
broader two-qubit synthesis proof instead of simple phase absorption.
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from b1_b7_gcm_h6_cone_feasibility_gate import (
    classify_rotations,
    parse_qasm,
    read_json,
    target_cone_signatures,
)


METHOD = "b1_b7_cone01_phase_removal_gate_v0"
STATUS = "cone01_phase_removal_restricted_negative_gate"
MODEL_STATUS = "restricted_two_cnot_phase_replacement_search_not_semantic_certificate"
VERSION = "0.1"
EXACT_TOLERANCE = 1e-8
FIXED_PHASES = {
    "remove": None,
    "0": 0.0,
    "pi/4": math.pi / 4.0,
    "-pi/4": -math.pi / 4.0,
    "pi/2": math.pi / 2.0,
    "-pi/2": -math.pi / 2.0,
    "3*pi/4": 3.0 * math.pi / 4.0,
    "-3*pi/4": -3.0 * math.pi / 4.0,
    "pi": math.pi,
    "-pi": -math.pi,
}


def write_json(path: Path, payload: dict, pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2 if pretty else None, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_eval_angle(expr: str) -> float:
    allowed = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.Constant,
        ast.Name,
        ast.Load,
    )
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError(expr)
        if isinstance(node, ast.Name) and node.id != "pi":
            raise ValueError(expr)
    return float(eval(compile(tree, "<angle>", "eval"), {"__builtins__": {}}, {"pi": math.pi}))


def angle_from_params(params: str) -> float:
    return safe_eval_angle(params.strip())


def rz(theta: float) -> np.ndarray:
    return np.array([[np.exp(-0.5j * theta), 0.0], [0.0, np.exp(0.5j * theta)]], dtype=complex)


def ry(theta: float) -> np.ndarray:
    c = math.cos(theta / 2.0)
    s = math.sin(theta / 2.0)
    return np.array([[c, -s], [s, c]], dtype=complex)


def rx(theta: float) -> np.ndarray:
    c = math.cos(theta / 2.0)
    s = math.sin(theta / 2.0)
    return np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)


I2 = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)


def single_on(local_index: int, matrix: np.ndarray) -> np.ndarray:
    return np.kron(matrix, I2) if local_index == 0 else np.kron(I2, matrix)


def cx_on(control: int, target: int) -> np.ndarray:
    unitary = np.zeros((4, 4), dtype=complex)
    for basis in range(4):
        bits = [(basis >> 1) & 1, basis & 1]
        out = bits[:]
        if bits[control]:
            out[target] ^= 1
        out_index = (out[0] << 1) | out[1]
        unitary[out_index, basis] = 1.0
    return unitary


def op_unitary(op: dict, local_qubits: list[int]) -> np.ndarray:
    local = {qubit: idx for idx, qubit in enumerate(local_qubits)}
    gate = op["gate"]
    if gate == "cx":
        return cx_on(local[op["qubits"][0]], local[op["qubits"][1]])
    if gate in {"rz", "ry", "rx"}:
        theta = angle_from_params(op["params"])
        matrix = {"rz": rz, "ry": ry, "rx": rx}[gate](theta)
        return single_on(local[op["qubits"][0]], matrix)
    raise ValueError(f"unsupported pair-local op for cone_01 gate: {op['text']}")


def phase_align(candidate: np.ndarray, target: np.ndarray) -> np.ndarray:
    overlap = np.trace(np.conjugate(target.T) @ candidate)
    if abs(overlap) <= 1e-15:
        return candidate
    return candidate * np.exp(-1j * np.angle(overlap))


def residual_vector(candidate: np.ndarray, target: np.ndarray) -> np.ndarray:
    diff = phase_align(candidate, target) - target
    return np.concatenate([diff.real.ravel(), diff.imag.ravel()])


def residual_norm(candidate: np.ndarray, target: np.ndarray) -> float:
    return float(np.linalg.norm(residual_vector(candidate, target)))


def unitary_for_ops(ops: list[dict], local_qubits: list[int]) -> np.ndarray:
    total = np.eye(4, dtype=complex)
    for op in ops:
        total = op_unitary(op, local_qubits) @ total
    return total


def replace_arbitrary_op(window: list[dict], op_index: int, replacement: float | None) -> list[dict]:
    output = []
    for op in window:
        if op["op_index"] != op_index:
            output.append(op)
        elif replacement is not None:
            clone = dict(op)
            clone["gate"] = "rz"
            clone["params"] = f"{replacement:.17g}"
            clone["text"] = f"rz({replacement:.17g}) q[{op['qubits'][0]}];"
            output.append(clone)
    return output


def optimize_continuous_rz(window: list[dict], row: dict, local_qubits: list[int], target: np.ndarray) -> dict:
    seeds = [0.0, math.pi / 4.0, -math.pi / 4.0, math.pi / 2.0, -math.pi / 2.0, math.pi, angle_from_params(row["params"])]

    def objective(values: np.ndarray) -> np.ndarray:
        candidate = unitary_for_ops(replace_arbitrary_op(window, row["op_index"], float(values[0])), local_qubits)
        return residual_vector(candidate, target)

    best = None
    for seed in seeds:
        result = least_squares(
            objective,
            np.array([seed], dtype=float),
            method="trf",
            ftol=1e-13,
            xtol=1e-13,
            gtol=1e-13,
            max_nfev=2000,
        )
        residual = float(np.linalg.norm(result.fun))
        if best is None or residual < best["residual_norm"]:
            best = {
                "replacement_angle": float(result.x[0]),
                "residual_norm": residual,
                "max_abs_entry_error": float(
                    np.max(
                        np.abs(
                            phase_align(
                                unitary_for_ops(
                                    replace_arbitrary_op(window, row["op_index"], float(result.x[0])), local_qubits
                                ),
                                target,
                            )
                            - target
                        )
                    )
                ),
                "optimizer_success": bool(result.success),
                "optimizer_nfev": int(result.nfev),
            }
    assert best is not None
    return best


def target_rows(args: argparse.Namespace) -> tuple[list[dict], list[dict]]:
    selector = read_json(args.selector)
    feasibility = read_json(args.feasibility)
    ops = parse_qasm(args.qasm)
    signatures = target_cone_signatures(selector)
    target_signature = None
    for signature, cone_id in signatures.items():
        if cone_id == args.cone_id:
            target_signature = signature
            break
    if target_signature is None:
        raise ValueError(f"missing target cone {args.cone_id}")
    rows = [
        row
        for row in classify_rotations(ops)
        if row["cone_signature"] == target_signature and row["pair_local_single_arbitrary_window"]
    ]
    expected = feasibility.get("summary", {}).get("leading_feasible_pair_local_single_window_count")
    if expected is not None and len(rows) != expected:
        raise ValueError(f"expected {expected} {args.cone_id} windows, found {len(rows)}")
    return ops, rows


def analyze_window(ops: list[dict], row: dict) -> dict:
    partner = row["previous_cx_partner"]
    local_qubits = [partner, row["qubit"]]
    window = ops[row["previous_cx_index"] : row["next_cx_index"] + 1]
    target = unitary_for_ops(window, local_qubits)
    fixed_results = {}
    for label, angle in FIXED_PHASES.items():
        candidate_ops = replace_arbitrary_op(window, row["op_index"], angle)
        fixed_results[label] = residual_norm(unitary_for_ops(candidate_ops, local_qubits), target)
    best_fixed_label, best_fixed_residual = min(fixed_results.items(), key=lambda item: item[1])
    continuous = optimize_continuous_rz(window, row, local_qubits, target)
    return {
        "line_number": row["line_number"],
        "op_index": row["op_index"],
        "qubit": row["qubit"],
        "partner": partner,
        "arbitrary_gate": row["gate"],
        "arbitrary_params": row["params"],
        "previous_cx_line": row["previous_cx_line"],
        "next_cx_line": row["next_cx_line"],
        "window_operation_count": len(window),
        "window_text": [op["text"] for op in window],
        "remove_only_residual_norm": fixed_results["remove"],
        "best_fixed_phase_label": best_fixed_label,
        "best_fixed_phase_residual_norm": best_fixed_residual,
        "continuous_rz_replacement_angle": continuous["replacement_angle"],
        "continuous_rz_residual_norm": continuous["residual_norm"],
        "continuous_rz_max_abs_entry_error": continuous["max_abs_entry_error"],
        "continuous_rz_optimizer_success": continuous["optimizer_success"],
        "continuous_rz_optimizer_nfev": continuous["optimizer_nfev"],
        "passes_remove_only_exact_gate": fixed_results["remove"] <= EXACT_TOLERANCE,
        "passes_fixed_phase_exact_gate": best_fixed_residual <= EXACT_TOLERANCE,
        "passes_continuous_rz_exact_gate": continuous["residual_norm"] <= EXACT_TOLERANCE,
    }


def build_payload(args: argparse.Namespace) -> dict:
    ops, rows = target_rows(args)
    analyses = [analyze_window(ops, row) for row in rows]
    continuous_sorted = sorted(analyses, key=lambda item: item["continuous_rz_residual_norm"])
    fixed_sorted = sorted(analyses, key=lambda item: item["best_fixed_phase_residual_norm"])
    summary = {
        "target_cone_id": args.cone_id,
        "candidate_window_count": len(analyses),
        "required_exact_windows_for_b7_target": args.required_windows,
        "remove_only_exact_pass_count": sum(1 for row in analyses if row["passes_remove_only_exact_gate"]),
        "fixed_phase_exact_pass_count": sum(1 for row in analyses if row["passes_fixed_phase_exact_gate"]),
        "continuous_rz_exact_pass_count": sum(1 for row in analyses if row["passes_continuous_rz_exact_gate"]),
        "best_continuous_rz_residual_norm": continuous_sorted[0]["continuous_rz_residual_norm"] if analyses else None,
        "median_continuous_rz_residual_norm": float(np.median([row["continuous_rz_residual_norm"] for row in analyses]))
        if analyses
        else None,
        "best_fixed_phase_residual_norm": fixed_sorted[0]["best_fixed_phase_residual_norm"] if analyses else None,
        "exact_tolerance": EXACT_TOLERANCE,
        "restricted_gate_clears_b7_target": False,
        "rewrite_claimed": False,
        "resource_saving_claimed": False,
        "semantic_certificate_claimed": False,
        "obstruction_theorem_claimed": False,
    }
    summary["restricted_gate_clears_b7_target"] = (
        summary["continuous_rz_exact_pass_count"] >= args.required_windows
    )
    payload = {
        "benchmark_id": "B1",
        "problem_id": 25,
        "linked_b7_problem_id": 21,
        "title": "B1/B7 cone_01 restricted phase-removal gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "method": METHOD,
        "source_qasm": str(args.qasm),
        "source_selector": str(args.selector),
        "source_feasibility_gate": str(args.feasibility),
        "workload": "qasmbench_medium_exact/gcm_h6.qasm",
        "summary": summary,
        "top_windows_by_continuous_rz_residual": continuous_sorted[: args.report_limit],
        "top_windows_by_fixed_phase_residual": fixed_sorted[: args.report_limit],
        "claim_boundary": {
            "rewrite_claimed": False,
            "resource_saving_claimed": False,
            "semantic_certificate_claimed": False,
            "obstruction_theorem_claimed": False,
            "physical_layout_claimed": False,
            "supported_claim": (
                "The restricted same-envelope phase-only replacement/deletion route does not clear "
                "the cone_01 target under the exact numerical tolerance."
            ),
            "unsupported_claims": [
                "No local rewrite certificate is produced.",
                "No global obstruction theorem is proved.",
                "No B7 FT ledger improvement is counted.",
            ],
            "next_gate": (
                "Use broader two-qubit synthesis, KAK/Clifford scaffolds, or a constructive "
                "certificate that can remove at least 30 cone_01 arbitrary rotations."
            ),
        },
    }
    errors = validate(payload)
    payload["summary"]["validation_error_count"] = len(errors)
    payload["validation_errors"] = errors
    return payload


def validate(payload: dict) -> list[str]:
    errors = []
    summary = payload["summary"]
    if payload.get("method") != METHOD:
        errors.append("method mismatch")
    if payload.get("status") != STATUS:
        errors.append("status mismatch")
    if summary["candidate_window_count"] < summary["required_exact_windows_for_b7_target"]:
        errors.append("candidate windows should cover the B7 occurrence target")
    if summary["restricted_gate_clears_b7_target"]:
        errors.append("restricted phase-only gate unexpectedly clears B7 target; review claim boundary")
    if summary["continuous_rz_exact_pass_count"] != 0:
        errors.append("continuous RZ replacement should not pass exact gate for current cone_01 windows")
    for field in [
        "rewrite_claimed",
        "resource_saving_claimed",
        "semantic_certificate_claimed",
        "obstruction_theorem_claimed",
    ]:
        if summary.get(field) is not False:
            errors.append(f"{field} must be false")
    return errors


def markdown_report(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# B1/B7 cone_01 Restricted Phase-Removal Gate",
        "",
        f"- Status: `{payload['status']}`",
        f"- Workload: `{payload['workload']}`",
        f"- Target cone: `{summary['target_cone_id']}`",
        f"- Candidate windows: {summary['candidate_window_count']}",
        f"- Required exact windows for B7 one-sided target: {summary['required_exact_windows_for_b7_target']}",
        f"- Remove-only exact pass count: {summary['remove_only_exact_pass_count']}",
        f"- Fixed Z-phase exact pass count: {summary['fixed_phase_exact_pass_count']}",
        f"- Continuous RZ exact pass count: {summary['continuous_rz_exact_pass_count']}",
        f"- Best continuous-RZ residual: {summary['best_continuous_rz_residual_norm']}",
        f"- Median continuous-RZ residual: {summary['median_continuous_rz_residual_norm']}",
        f"- Best fixed-phase residual: {summary['best_fixed_phase_residual_norm']}",
        f"- Restricted gate clears B7 target: {summary['restricted_gate_clears_b7_target']}",
        f"- Validation errors: {summary['validation_error_count']}",
        "",
        "## Interpretation",
        "",
        "The simple route fails: deleting the only arbitrary RY in a cone_01 window,",
        "or replacing it with a local Z phase inside the same two-CNOT envelope, does",
        "not produce an exact same-envelope rewrite. This is a restricted numerical",
        "gate, not a global lower bound. T-B1-004 now needs broader two-qubit",
        "synthesis, a KAK/Clifford scaffold, or another certificate-bearing rewrite.",
        "",
        "## Claim Boundary",
        "",
        f"- Rewrite claimed: {payload['claim_boundary']['rewrite_claimed']}",
        f"- Resource saving claimed: {payload['claim_boundary']['resource_saving_claimed']}",
        f"- Semantic certificate claimed: {payload['claim_boundary']['semantic_certificate_claimed']}",
        f"- Obstruction theorem claimed: {payload['claim_boundary']['obstruction_theorem_claimed']}",
        "",
        "## Best Continuous-RZ Attempts",
        "",
        "| line | qubit | partner | theta | residual | replacement angle |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["top_windows_by_continuous_rz_residual"]:
        lines.append(
            f"| {row['line_number']} | {row['qubit']} | {row['partner']} | "
            f"{row['arbitrary_params']} | {row['continuous_rz_residual_norm']} | "
            f"{row['continuous_rz_replacement_angle']} |"
        )
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qasm", type=Path, default=Path("results/b1_u3_phase_factored_optimizer/qasmbench_medium_exact/gcm_h6.qasm"))
    parser.add_argument("--selector", type=Path, default=Path("results/B1_B7_gcm_h6_target_selector_v0.json"))
    parser.add_argument("--feasibility", type=Path, default=Path("results/B1_B7_gcm_h6_cone_feasibility_gate_v0.json"))
    parser.add_argument("--result", type=Path, default=Path("results/B1_B7_cone01_phase_removal_gate_v0.json"))
    parser.add_argument("--markdown", type=Path, default=Path("research/B1_B7_cone01_phase_removal_gate.md"))
    parser.add_argument("--cone-id", default="cone_01")
    parser.add_argument("--required-windows", type=int, default=30)
    parser.add_argument("--report-limit", type=int, default=12)
    parser.add_argument("--last-updated", default="2026-06-18")
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    payload = build_payload(args)
    write_json(args.result, payload, args.pretty)
    write_text(args.markdown, markdown_report(payload))
    print(f"wrote {args.result}")
    print(f"wrote {args.markdown}")
    if payload["validation_errors"]:
        print(json.dumps(payload["validation_errors"], indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
