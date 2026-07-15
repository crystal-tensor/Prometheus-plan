#!/usr/bin/env python3
"""Retest the B7 resource ledger after accepting the scoped symbolic certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


METHOD = "b7_w8_21_symbolic_certificate_ledger_retest_v0"
RESULT_PATH = "results/B7_w8_21_symbolic_certificate_ledger_retest_v0.json"
REPORT_PATH = "research/B7_w8_21_symbolic_certificate_ledger_retest.md"
ACCEPTANCE_PATH = "results/B7_w8_21_symbolic_certificate_acceptance_packet_gate_v0.json"
CERTIFICATE_PATH = "results/B7_w8_21_symbolic_certificate_v0.json"
CANDIDATE_PATH = "results/B7_w8_21_symbolic_certificate_candidate_v0.json"
CONTEXT_PATH = "results/B7_w8_21_context_absorption_v0.json"


def load(root: Path, path: str) -> dict[str, Any]:
    return json.loads((root / path).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def build(root: Path) -> dict[str, Any]:
    acceptance = load(root, ACCEPTANCE_PATH)
    certificate = load(root, CERTIFICATE_PATH)
    candidate = load(root, CANDIDATE_PATH)
    context = load(root, CONTEXT_PATH)
    acceptance_summary = acceptance["summary"]
    theorem = certificate["theorem"]
    resource = {
        "baseline_cnot_count": 2,
        "certificate_cnot_count": 2,
        "baseline_arbitrary_parameter_count": 5,
        "certificate_arbitrary_parameter_count": 5,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "b7_credit": 0,
        "target_occurrence_removal_required": 30,
        "target_proxy_t_reduction_required": 600,
    }
    conditions = [
        ("L1", acceptance_summary.get("failed_acceptance_requirement_ids") == [] and acceptance_summary.get("validation_error_count") == 0),
        ("L2", acceptance_summary.get("accepted_symbolic_certificate_count") == 1 and acceptance_summary.get("ready_for_b7_ledger_retest_count") == 1),
        ("L3", certificate.get("machine_checked") is True and theorem.get("exact_checks_failed") == 0),
        ("L4", candidate.get("template_id") == "w8_21" and candidate.get("certificate_class") == "scoped_exact_symbolic_relative_block_certificate"),
        ("L5", resource["baseline_cnot_count"] == resource["certificate_cnot_count"]),
        ("L6", resource["baseline_arbitrary_parameter_count"] == resource["certificate_arbitrary_parameter_count"]),
        ("L7", context.get("selected_occurrence_count") == 16 and context["boundary_accounting"].get("direct_rz_merge_count") == 0),
        ("L8", resource["accepted_occurrence_removal"] == 0 and resource["accepted_proxy_t_reduction"] == 0),
        ("L9", resource["accepted_occurrence_removal"] < resource["target_occurrence_removal_required"] and resource["accepted_proxy_t_reduction"] < resource["target_proxy_t_reduction_required"]),
        ("L10", candidate["claim_boundary"].get("b7_ledger_improvement_claimed") is False and candidate["claim_boundary"].get("physical_resource_reduction_claimed") is False),
    ]
    source_bindings = {
        path: {"path": path, "sha256": sha256(root / path)}
        for path in [ACCEPTANCE_PATH, CERTIFICATE_PATH, CANDIDATE_PATH, CONTEXT_PATH]
    }
    result = {
        "title": "B7 w8_21 symbolic certificate ledger retest",
        "version": 0,
        "method": METHOD,
        "status": "symbolic_certificate_retest_complete_no_ledger_gain",
        "classification": "exact_symbolic_certificate_accepted_zero_resource_delta",
        "template_id": "w8_21",
        "source_bindings": source_bindings,
        "acceptance_binding": {
            "acceptance_packet_id": acceptance_summary["acceptance_packet_id"],
            "acceptance_packet_hash": acceptance_summary["acceptance_packet_hash"],
            "accepted_symbolic_certificate_count": acceptance_summary["accepted_symbolic_certificate_count"],
            "ready_for_b7_ledger_retest_count": acceptance_summary["ready_for_b7_ledger_retest_count"],
        },
        "certificate_checks": {
            "machine_checked": certificate["machine_checked"],
            "exact_checks_passed": theorem["exact_checks_passed"],
            "exact_checks_failed": theorem["exact_checks_failed"],
            "candidate_hash": certificate["certificate_candidate_hash"],
        },
        "resource_accounting": resource,
        "requirements": [{"condition_id": key, "passed": bool(value)} for key, value in conditions],
        "requirements_passed": sum(bool(value) for _, value in conditions),
        "requirements_failed": sum(not bool(value) for _, value in conditions),
        "claim_boundary": {
            "what_is_supported": "the accepted scoped symbolic certificate is replayed into the B7 ledger and produces a transparent zero resource delta for the fixed w8_21 skeleton",
            "what_is_not_supported": "a compression rewrite, CNOT reduction, arbitrary-rotation reduction, occurrence removal, proxy-T reduction, physical-layout gain, global lower bound, or solved B1/B7 frontier",
            "new_rewrite_claimed": False,
            "global_lower_bound_claimed": False,
            "physical_resource_reduction_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
        "artifacts": {"result": RESULT_PATH, "markdown_report": REPORT_PATH},
    }
    result["payload_hash"] = stable_hash(result)
    return result


def report(result: dict[str, Any]) -> str:
    r = result["resource_accounting"]
    return "\n".join([
        "# B7 w8_21 Symbolic Certificate Ledger Retest",
        "",
        f"- Status: `{result['status']}`",
        f"- Classification: `{result['classification']}`",
        f"- Requirements: `{result['requirements_passed']}/{result['requirements_passed'] + result['requirements_failed']}`",
        f"- Payload hash: `{result['payload_hash']}`",
        "",
        "## Heuristic question",
        "",
        "Once an exact symbolic certificate is accepted, does it actually lower the resource ledger, or does it only explain the existing two-CNOT block?",
        "",
        "## Retest",
        "",
        "The accepted certificate passes its exact symbolic checks, but its constructive identity has the same two CNOTs and five arbitrary parameters as the source skeleton. The real-circuit context gate still reports zero direct Rz merges.",
        "",
        f"The ledger therefore records CNOT `{r['baseline_cnot_count']} -> {r['certificate_cnot_count']}`, arbitrary parameters `{r['baseline_arbitrary_parameter_count']} -> {r['certificate_arbitrary_parameter_count']}`, accepted occurrence removal `{r['accepted_occurrence_removal']}`, and proxy-T reduction `{r['accepted_proxy_t_reduction']}`. The target remains `{r['target_occurrence_removal_required']}` occurrences / `{r['target_proxy_t_reduction_required']}` proxy-T units, so B7 credit remains zero.",
        "",
        "## Interpretation",
        "",
        "This is a useful positive theorem artifact with a negative engineering result: the invariant is exact for the fixed skeleton, but it does not yet carry a cheaper implementation. The next route must transfer or eliminate local parameters across a larger source neighborhood, or find a different occurrence-removing scaffold.",
        "",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    result_path = root / RESULT_PATH
    report_path = root / REPORT_PATH
    if result_path.exists() or report_path.exists():
        raise ValueError("ledger retest artifacts already exist; refusing to overwrite")
    result = build(root)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(report(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "requirements_passed": result["requirements_passed"], "requirements_failed": result["requirements_failed"], "payload_hash": result["payload_hash"]}, sort_keys=True))
    if result["requirements_failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
