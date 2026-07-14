#!/usr/bin/env python3
"""Apply the public R160 support rule to the immutable execution artifacts."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r154_deterministic_automatic_replay import canonical_hash


PROTOCOL_PATH = "results/B4_B8_R160_deterministic_error_map_remediation_protocol_v0.json"
CONTRACT_PATH = "benchmarks/B4_B8_R160_deterministic_error_map_remediation_contract_v0.json"
RAW_RESULT_PATH = "results/B4_B8_R160_deterministic_error_map_remediation_v0.json"
PROFILE_SUMMARY_PATH = "results/B4_B8_R160_deterministic_error_map_remediation/profile_summary.json"
CASE_ANALYSIS_PATH = "results/B4_B8_R160_deterministic_error_map_remediation/case_analysis.json"
OUT_PATH = "results/B4_B8_R160_deterministic_error_map_remediation_adjudication_v0.json"
REPORT_PATH = "research/B4_B8_R160_deterministic_error_map_remediation_adjudication.md"


def validate_payload(payload: dict[str, Any], key: str, label: str) -> str:
    body = dict(payload)
    payload_hash = body.pop(key, None)
    if payload_hash != canonical_hash(body):
        raise ValueError(f"R160 adjudication {label} payload mismatch")
    return payload_hash


def build(root: Path) -> dict[str, Any]:
    protocol = json.loads((root / PROTOCOL_PATH).read_text())
    contract = json.loads((root / CONTRACT_PATH).read_text())
    raw_result = json.loads((root / RAW_RESULT_PATH).read_text())
    profile_summary = json.loads((root / PROFILE_SUMMARY_PATH).read_text())
    case_analysis = json.loads((root / CASE_ANALYSIS_PATH).read_text())
    protocol_hash = validate_payload(protocol, "payload_hash", "protocol")
    contract_hash = validate_payload(contract, "payload_hash", "contract")
    result_hash = validate_payload(raw_result, "payload_hash", "raw result")
    profile_hash = validate_payload(
        profile_summary, "profile_summary_payload_hash", "profile summary"
    )
    case_hash = validate_payload(
        case_analysis, "case_analysis_payload_hash", "case analysis"
    )
    expected_hashes = {
        "protocol": "ac6831519b4e977c67bb8ed0b7be9a1557d97db46454b9422f5cfa0e820e47b5",
        "contract": "8f164e093ae6ee4d9be76884c9e7f1b9c3509822365412b086765962aa5438c3",
        "raw_result": "950c426711df1fcc9d744febadec21ad06b81e3884412c391f61d2a994f18c50",
        "profile_summary": "5763fada8be2d0e49374c1a8459dffd6ce89c7052da9505e285747cf9ba4932b",
        "case_analysis": "1cd2c353e5545c1a2a84c8ef1ac41a2eff4783696f4ee5a372df5a8c92a9dcb7",
    }
    observed_hashes = {
        "protocol": protocol_hash,
        "contract": contract_hash,
        "raw_result": result_hash,
        "profile_summary": profile_hash,
        "case_analysis": case_hash,
    }
    if observed_hashes != expected_hashes:
        raise ValueError("R160 adjudication source payload binding mismatch")
    failing_rows = []
    process_ids = set()
    all_replay_hashes_valid = True
    process_artifacts = raw_result["artifacts"]["process_artifacts"]
    for artifact in process_artifacts:
        path = root / artifact["path"]
        if file_sha256(path) != artifact["sha256"]:
            raise ValueError(f"R160 adjudication worker file mismatch: {artifact['path']}")
        worker = json.loads(path.read_text())
        worker_hash = validate_payload(worker, "manifest_payload_hash", artifact["path"])
        if worker_hash != artifact["manifest_payload_hash"]:
            raise ValueError(f"R160 adjudication worker binding mismatch: {artifact['path']}")
        process_ids.add(worker["process_instance_uuid"])
        for replay in worker["replay_rows"]:
            replay_hash = replay["replay_payload_hash"]
            body = {key: value for key, value in replay.items() if key != "replay_payload_hash"}
            if replay_hash != canonical_hash(body):
                all_replay_hashes_valid = False
            if not replay["within_exact_oracle_minimizers"]:
                failing_rows.append(
                    {
                        "mode": worker["profile_id"],
                        "replica": worker["replica"],
                        "case_id": replay["case_id"],
                        "replay_index": replay["replay_index"],
                        "selected_vector": replay["mapping_vector"],
                    }
                )
    case_by_id = {row["case_id"]: row for row in case_analysis["case_rows"]}
    failures_by_case = Counter(row["case_id"] for row in failing_rows)
    failures_by_mode = Counter(row["mode"] for row in failing_rows)
    failure_case_rows = []
    for case_id, count in sorted(failures_by_case.items()):
        case = case_by_id[case_id]
        exact_vectors = {
            tuple(vector)
            for mode in case["mode_rows"]
            for vector in mode["oracle"]["minimizer_vectors"]
        }
        selected_vectors = {
            tuple(row["selected_vector"])
            for row in failing_rows
            if row["case_id"] == case_id
        }
        failure_case_rows.append(
            {
                "case_id": case_id,
                "key": case["key"],
                "ulp_shift": case["ulp_shift"],
                "minimum_cross_mode_gap": case["minimum_cross_mode_gap"],
                "margin_protected": case["margin_protected"],
                "failing_replay_count": count,
                "selected_vectors": [list(row) for row in sorted(selected_vectors)],
                "exact_oracle_vectors": [list(row) for row in sorted(exact_vectors)],
            }
        )
    summary = raw_result["summary"]
    frozen_support_conditions = [
        {
            "condition_id": "S1",
            "label": "all four modes select one stable tied vector",
            "passed": summary["tie_baseline_all_modes_stable"]
            and summary["tie_baseline_cross_mode_agreement"],
        },
        {
            "condition_id": "S2",
            "label": "at least one margin-protected non-tied case exists",
            "passed": summary["margin_protected_case_count"] > 0,
        },
        {
            "condition_id": "S3",
            "label": "zero margin-protected failures occur",
            "passed": summary["margin_protected_failure_count"] == 0,
        },
        {
            "condition_id": "S4",
            "label": "every replay belongs to its exact rational oracle minimizer set",
            "passed": len(failing_rows) == 0
            and summary["all_replays_within_exact_oracle"] is True,
        },
        {
            "condition_id": "S5",
            "label": "all replay, worker, and source payloads validate",
            "passed": all_replay_hashes_valid
            and len(process_ids) == 16
            and len(process_artifacts) == 16,
        },
    ]
    support_rule_passed = all(row["passed"] for row in frozen_support_conditions)
    audited_classification = (
        "deterministic_external_map_remediation_supported"
        if support_rule_passed
        else "tie_stabilized_but_non_tied_guardrail_failed"
    )
    payload = {
        "title": "B4/B8 R160 deterministic ErrorMap remediation adjudication",
        "version": 0,
        "method": "b4_b8_r160_deterministic_error_map_remediation_adjudication_v0",
        "status": "frozen_support_rule_adjudication_complete",
        "model_status": "raw_execution_valid_executor_classification_overruled_by_public_support_rule",
        "source_target_id": "T-B4-002cd/T-B8-003ch/T-B10-009bv",
        "upstream_target_id": "T-B4-002cc/T-B8-003cg/T-B10-009bu",
        "source_bindings": {
            "protocol": {"path": PROTOCOL_PATH, "payload_hash": protocol_hash, "sha256": file_sha256(root / PROTOCOL_PATH)},
            "contract": {"path": CONTRACT_PATH, "payload_hash": contract_hash, "sha256": file_sha256(root / CONTRACT_PATH)},
            "raw_result": {"path": RAW_RESULT_PATH, "payload_hash": result_hash, "sha256": file_sha256(root / RAW_RESULT_PATH)},
            "profile_summary": {"path": PROFILE_SUMMARY_PATH, "payload_hash": profile_hash, "sha256": file_sha256(root / PROFILE_SUMMARY_PATH)},
            "case_analysis": {"path": CASE_ANALYSIS_PATH, "payload_hash": case_hash, "sha256": file_sha256(root / CASE_ANALYSIS_PATH)},
        },
        "executor_reported_classification": summary["classification"],
        "audited_classification": audited_classification,
        "executor_classification_overruled": summary["classification"] != audited_classification,
        "support_rule_passed": support_rule_passed,
        "frozen_support_conditions": frozen_support_conditions,
        "raw_execution_integrity_passed": all_replay_hashes_valid
        and len(process_ids) == 16,
        "direct_replay_count": summary["direct_replay_count"],
        "exact_oracle_pass_count": summary["direct_replay_count"] - len(failing_rows),
        "exact_oracle_failure_count": len(failing_rows),
        "exact_oracle_failure_case_count": len(failures_by_case),
        "exact_oracle_failures_by_mode": dict(sorted(failures_by_mode.items())),
        "failure_case_rows": failure_case_rows,
        "tie_baseline_selected_vector": summary["tie_baseline_selected_vector"],
        "margin_protected_case_count": summary["margin_protected_case_count"],
        "margin_protected_failure_count": summary["margin_protected_failure_count"],
        "post_execution_adjudication_preregistered": False,
        "source_patch_performed": False,
        "simulation_execution_count": 0,
        "total_simulated_shots": 0,
        "confirmed_qiskit_bug_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "solved_frontier_claimed": False,
        "new_credit_delta": 0,
        "claim_boundary": {
            "what_is_supported": "the immutable R160 matrix stabilizes the exact tie and preserves all twelve margin-protected rows, but misses the exact optimum in seven sub-threshold near-tie cases",
            "what_is_not_supported": "complete remediation, an accepted upstream patch, confirmed Qiskit bug, cross-platform theorem, hardware result, route advantage, quantum advantage, BQP separation, solved B4/B8/B10, or new credit",
        },
    }
    payload["payload_hash"] = canonical_hash(payload)
    return payload


def write_report(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# B4/B8 R160 Deterministic ErrorMap Remediation Adjudication",
        "",
        f"- Status: `{payload['status']}`",
        f"- Executor classification: `{payload['executor_reported_classification']}`",
        f"- Audited classification: `{payload['audited_classification']}`",
        f"- Frozen support rule passed: `{payload['support_rule_passed']}`",
        f"- Direct replays / exact-oracle pass / fail: `{payload['direct_replay_count']}` / `{payload['exact_oracle_pass_count']}` / `{payload['exact_oracle_failure_count']}`",
        f"- Failure cases: `{payload['exact_oracle_failure_case_count']}`",
        f"- Margin-protected cases / failures: `{payload['margin_protected_case_count']}` / `{payload['margin_protected_failure_count']}`",
        f"- Tie baseline selected vector: `{payload['tie_baseline_selected_vector']}`",
        f"- Raw execution integrity passed: `{payload['raw_execution_integrity_passed']}`",
        f"- Post-execution adjudication preregistered: `{payload['post_execution_adjudication_preregistered']}`",
        "",
        "## Frozen Support Conditions",
        "",
        "| Condition | Passed | Meaning |",
        "|---|---|---|",
    ]
    for row in payload["frozen_support_conditions"]:
        lines.append(
            f"| `{row['condition_id']}` | `{row['passed']}` | {row['label']} |"
        )
    lines.extend(
        [
            "",
            "## Exact-Oracle Failures",
            "",
            "| Case | Key | ULP shift | Gap | Failing calls | Selected | Exact optimum |",
            "|---|---|---:|---:|---:|---|---|",
        ]
    )
    for row in payload["failure_case_rows"]:
        lines.append(
            f"| `{row['case_id']}` | `{row['key']}` | {row['ulp_shift']} | {row['minimum_cross_mode_gap']:.17g} | {row['failing_replay_count']} | `{row['selected_vectors']}` | `{row['exact_oracle_vectors']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The raw execution is internally valid, but its positive executor classification omitted the public rule requiring every replay to belong to its exact-oracle minimum set. Exactly 224 calls across seven 1-8 ULP near-tie cases deterministically return mapping A while the exact rational oracle prefers mapping B. All twelve cases above the frozen `1e-16` protection margin pass. The evidence therefore supports deterministic tie stabilization and a bounded margin guardrail, but rejects complete remediation under the published support rule.",
            "",
            "## Claim Boundary",
            "",
            "This post-execution adjudication was not separately preregistered; it applies the already public R160 support rule to immutable artifacts. It does not claim a complete fix, accepted upstream patch, confirmed Qiskit bug, cross-platform theorem, hardware relevance, route advantage, quantum advantage, BQP separation, solved B4/B8/B10, or new research credit.",
            "",
        ]
    )
    path.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Adjudicate R160 against its public support rule."
    )
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    outputs = [root / OUT_PATH, root / REPORT_PATH]
    if any(path.exists() for path in outputs):
        raise ValueError("R160 adjudication evidence already exists; refusing to overwrite")
    payload = build(root)
    write_json(root / OUT_PATH, payload)
    write_report(root / REPORT_PATH, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "executor_classification": payload[
                    "executor_reported_classification"
                ],
                "audited_classification": payload["audited_classification"],
                "support_rule_passed": payload["support_rule_passed"],
                "exact_oracle_failure_count": payload[
                    "exact_oracle_failure_count"
                ],
                "exact_oracle_failure_case_count": payload[
                    "exact_oracle_failure_case_count"
                ],
                "payload_hash": payload["payload_hash"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
