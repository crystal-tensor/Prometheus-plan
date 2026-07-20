#!/usr/bin/env python3
"""Separate R179 evidence integrity from the preserved source rejection."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SOURCE_PATH = "results/B4_B8_R179_linux_x86_64_replay_v0.json"
ORACLE_PATH = "results/B4_B8_R179_independent_linux_x86_64_oracle_v0.json"
RESULT_PATH = (
    "results/B4_B8_R179_independent_linux_x86_64_oracle_adjudication_v0.json"
)
REPORT_PATH = (
    "research/B4_B8_R179_independent_linux_x86_64_oracle_adjudication.md"
)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def payload_ok(payload: dict[str, Any]) -> bool:
    body = dict(payload)
    return body.pop("payload_hash", None) == canonical_hash(body)


def failed_requirements(payload: dict[str, Any]) -> list[str]:
    return [
        str(row["requirement_id"])
        for row in payload.get("requirements", [])
        if row.get("passed") is not True
    ]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    root = args.root.resolve()
    source = json.loads((root / SOURCE_PATH).read_text(encoding="utf-8"))
    oracle = json.loads((root / ORACLE_PATH).read_text(encoding="utf-8"))
    source_summary = source["summary"]
    oracle_summary = oracle["summary"]
    source_failed = failed_requirements(source)
    oracle_failed = failed_requirements(oracle)

    forbidden = (
        "production_qiskit_remedy_claimed",
        "confirmed_qiskit_bug_claimed",
        "hardware_result_claimed",
        "quantum_advantage_claimed",
        "bqp_separation_claimed",
        "solved_frontier_claimed",
        "upstream_patch_accepted",
    )
    requirements = [
        ("A1", payload_ok(source) and payload_ok(oracle)),
        (
            "A2",
            source.get("status")
            == "linux_x86_64_fixed_superaccumulator_rejected_on_frozen_matrix"
            and source.get("requirements_passed") == 15
            and source.get("requirements_failed") == 1
            and source_failed == ["P13"],
        ),
        (
            "A3",
            oracle.get("status") == "independent_linux_x86_64_oracle_failed"
            and oracle.get("requirements_passed") == 11
            and oracle.get("requirements_failed") == 1
            and oracle_failed == ["P10"],
        ),
        (
            "A4",
            oracle.get("source_result_payload_hash") == source.get("payload_hash")
            and oracle.get("upstream_target_id") == source.get("source_target_id"),
        ),
        (
            "A5",
            oracle_summary.get("worker_hashes_valid") == 39
            and oracle_summary.get("worker_artifacts_match") == 39
            and oracle_summary.get("row_hashes_valid") == 2400
            and oracle_summary.get("case_hashes_valid") == 84,
        ),
        (
            "A6",
            oracle_summary.get("standard_outcomes_reproduced") == 1728
            and oracle_summary.get("small_gap_outcomes_reproduced") == 672
            and oracle_summary.get("small_gap_oracle_payload_matches") == 84,
        ),
        (
            "A7",
            oracle_summary.get("summary_matches") is True
            and source_summary.get("aggregate_fixed_to_biguint_median_time_ratio")
            > 0.90,
        ),
        (
            "A8",
            oracle.get("platform_audit", {}).get("requirements_passed") == 3
            and oracle.get("platform_audit", {}).get("requirements_failed") == 0
            and oracle_summary.get("linux_x86_64_worker_count") == 39,
        ),
        (
            "A9",
            oracle_summary.get("qiskit_imported") is False
            and oracle_summary.get("r179_executor_imported") is False
            and oracle_summary.get("qiskit_calls_performed") == 0
            and oracle_summary.get("simulation_execution_count") == 0
            and oracle_summary.get("total_simulated_shots") == 0,
        ),
        (
            "A10",
            all(source_summary.get(field) is False for field in forbidden)
            and all(oracle_summary.get(field) is False for field in forbidden)
            and source_summary.get("new_credit_delta") == 0
            and oracle_summary.get("new_credit_delta") == 0,
        ),
    ]
    passed = all(value for _, value in requirements)
    result = {
        "title": "B4/B8/B10 R179 independent Linux oracle adjudication",
        "version": 0,
        "method": "b4_b8_r179_independent_linux_oracle_adjudication_v0",
        "status": (
            "evidence_integrity_complete_source_performance_rejection_preserved"
            if passed
            else "oracle_adjudication_failed"
        ),
        "classification": (
            "independent_reproduction_with_preserved_preregistered_rejection"
            if passed
            else "incomplete"
        ),
        "source_target_id": (
            "T-B4-002dl/T-B8-003dp/T-B10-009db-r179-oracle-adjudication"
        ),
        "upstream_target_id": oracle["source_target_id"],
        "source_result_payload_hash": source["payload_hash"],
        "source_oracle_payload_hash": oracle["payload_hash"],
        "source_failed_requirements": source_failed,
        "oracle_failed_requirements": oracle_failed,
        "requirements": [
            {"requirement_id": key, "passed": value} for key, value in requirements
        ],
        "requirements_passed": sum(value for _, value in requirements),
        "requirements_failed": sum(not value for _, value in requirements),
        "summary": {
            "evidence_integrity_complete": passed,
            "source_acceptance_preserved": False,
            "source_performance_rejection_preserved": source_failed == ["P13"],
            "independent_source_rejection_preserved": oracle_failed == ["P10"],
            "worker_hashes_valid": oracle_summary["worker_hashes_valid"],
            "row_hashes_valid": oracle_summary["row_hashes_valid"],
            "case_hashes_valid": oracle_summary["case_hashes_valid"],
            "standard_outcomes_reproduced": oracle_summary[
                "standard_outcomes_reproduced"
            ],
            "small_gap_outcomes_reproduced": oracle_summary[
                "small_gap_outcomes_reproduced"
            ],
            "aggregate_fixed_to_biguint_median_time_ratio": source_summary[
                "aggregate_fixed_to_biguint_median_time_ratio"
            ],
            "qiskit_imported": False,
            "r179_executor_imported": False,
            "qiskit_calls_performed": 0,
            "simulation_execution_count": 0,
            "total_simulated_shots": 0,
            "hardware_result_claimed": False,
            "quantum_advantage_claimed": False,
            "bqp_separation_claimed": False,
            "solved_frontier_claimed": False,
            "new_credit_delta": 0,
        },
        "public_recovery_run": {
            "discussion": (
                "https://github.com/crystal-tensor/Prometheus-plan/discussions/269"
            ),
            "github_actions_run_url": (
                "https://github.com/crystal-tensor/Prometheus-plan/actions/runs/29758790587"
            ),
            "artifact_digest": (
                "7603ae32ccb23f7b7637ccf1cd0c8a66ac78fa1572c4b73c9c07c37c7ba5ea57"
            ),
        },
        "claim_boundary": {
            "what_is_supported": (
                "a Qiskit-free and executor-free standard-library reproduction of "
                "the complete committed R179 Linux evidence, with the frozen source "
                "performance rejection preserved"
            ),
            "what_is_not_supported": (
                "source acceptance, a production or upstream Qiskit remedy, broad "
                "performance, hardware relevance, quantum advantage, BQP separation, "
                "solved B4/B8/B10, or new credit"
            ),
        },
        "artifacts": {
            "source_result": SOURCE_PATH,
            "source_oracle": ORACLE_PATH,
            "result": RESULT_PATH,
            "report": REPORT_PATH,
        },
    }
    result["payload_hash"] = canonical_hash(result)
    write_json(root / RESULT_PATH, result)
    report = "\n".join(
        [
            "# B4/B8/B10 R179 Independent Linux Oracle Adjudication",
            "",
            f"- Status: `{result['status']}`",
            f"- Requirements: `{result['requirements_passed']}/10`",
            f"- Payload hash: `{result['payload_hash']}`",
            "",
            "## Why The Oracle Says Failed",
            "",
            "The independent oracle passes every evidence-integrity recomputation but "
            "fails P10 because the frozen source result is rejected at P13. This is "
            "the expected behavior: the oracle must not promote a source result that "
            "missed its preregistered performance target.",
            "",
            "## Independent Evidence",
            "",
            "Without importing Qiskit or the R179 executor, the oracle validates "
            "`39/39` worker hashes, `2400/2400` row hashes, and `84/84` case "
            "hashes. It reproduces `1728/1728` standard outcomes and `672/672` "
            "small-gap outcomes, along with timing, memory, and platform bindings.",
            "",
            "## Preserved Rejection",
            "",
            "The fixed/BigUint aggregate median ratio remains `1.129059`, above the "
            "frozen `0.90` ceiling. Evidence integrity is complete; source acceptance "
            "remains false. No threshold is changed.",
            "",
            "## Claim Boundary",
            "",
            "This supports one independent reconstruction of the committed Linux "
            "evidence. It does not establish a production or upstream Qiskit remedy, "
            "broad performance, quantum-hardware behavior, quantum advantage, BQP "
            "separation, solved B4/B8/B10, or new credit.",
            "",
        ]
    )
    (root / REPORT_PATH).write_text(report, encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
