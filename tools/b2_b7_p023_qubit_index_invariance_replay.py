#!/usr/bin/env python3
"""Exact replay audit for the QEC qubit-index invariance packet."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_qubit_index_invariance_v1.json"
DEFAULT_GENERATOR = ROOT / "tools/b2_b7_p023_qubit_index_invariance.py"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_qubit_index_invariance_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_qubit_index_invariance_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_qubit_index_invariance_discussion_v1.md"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_qubit_index_invariance_replay_v1.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def replay(
    protocol_path: Path,
    generator_path: Path,
    result_path: Path,
    report_path: Path,
    discussion_path: Path,
) -> dict[str, Any]:
    expected = load(result_path)
    checks: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="qec-index-invariance-") as temp:
        root = Path(temp)
        replay_result_path = root / "result.json"
        replay_report_path = root / "report.md"
        replay_discussion_path = root / "discussion.md"
        process = subprocess.run(
            [
                sys.executable,
                str(generator_path),
                "--protocol",
                str(protocol_path),
                "--output",
                str(replay_result_path),
                "--report",
                str(replay_report_path),
                "--discussion",
                str(replay_discussion_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        checks.append(check("producer_exit", process.returncode == 0, process.stdout.strip() if process.returncode == 0 else process.stderr.strip()))
        if process.returncode != 0:
            raise ValueError(f"producer replay failed: {process.stderr}")
        actual = load(replay_result_path)
        checks.append(check("result_bytes", replay_result_path.read_bytes() == result_path.read_bytes(), digest(replay_result_path)))
        checks.append(check("report_bytes", replay_report_path.read_bytes() == report_path.read_bytes(), digest(replay_report_path)))
        checks.append(check("discussion_bytes", replay_discussion_path.read_bytes() == discussion_path.read_bytes(), digest(replay_discussion_path)))
        checks.append(check("schema", actual["schema_version"] == expected["schema_version"], actual["schema_version"]))
        checks.append(check("scope", actual["scope"] == expected["scope"], "Exact scope."))
        checks.append(check("protocol_binding", actual["protocol_binding"] == expected["protocol_binding"], actual["protocol_binding"]["sha256"]))
        checks.append(check("frozen_inputs", actual["frozen_inputs_current"] == expected["frozen_inputs_current"] and actual["frozen_inputs_at_commit"] == expected["frozen_inputs_at_commit"], "Frozen bindings are exact."))
        checks.append(check("generator_binding", actual["generator"] == expected["generator"] and actual["generator"]["sha256"] == digest(generator_path), actual["generator"]["sha256"]))
        checks.append(check("environment", actual["execution_environment"] == expected["execution_environment"], str(actual["execution_environment"])))
        checks.append(check("basis_rows", actual["basis_rows"] == expected["basis_rows"], "Both scientific rows are exact."))
        checks.append(check("reference_regrade", actual["reference_regrade"] == expected["reference_regrade"], str(actual["reference_regrade"]["corrected_active_qubit_cost_by_basis"])))
        checks.append(check("adversarial_score", actual["adversarial_relabel_candidate"] == expected["adversarial_relabel_candidate"], str(actual["adversarial_relabel_candidate"]["index_invariant_composite_score"])))
        checks.append(check("readiness", actual["readiness"] == expected["readiness"], str(actual["readiness"])))
        checks.append(check("formal_checks", actual["formal_checks"] == expected["formal_checks"], f"{actual['summary']['checks_passed']}/{actual['summary']['checks_total']}"))
        checks.append(check("summary", actual["summary"] == expected["summary"], str(actual["summary"])))
        checks.append(check("decision", actual["decision"] == expected["decision"], actual["decision"]))
        checks.append(check("run_id", actual["run_id"] == expected["run_id"], actual["run_id"]))
        replay_hashes = {
            "result_sha256": digest(replay_result_path),
            "report_sha256": digest(replay_report_path),
            "discussion_sha256": digest(replay_discussion_path),
        }

    summary = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "exact_scientific_rows": 2 if all(item["passed"] for item in checks) else 0,
    }
    output = {
        "schema_version": "b2_b7_p023_qubit_index_invariance_replay_audit_v1",
        "source": {
            "protocol": {"path": str(protocol_path.relative_to(ROOT)), "sha256": digest(protocol_path)},
            "generator": {"path": str(generator_path.relative_to(ROOT)), "sha256": digest(generator_path)},
            "result": {"path": str(result_path.relative_to(ROOT)), "sha256": digest(result_path)},
            "report": {"path": str(report_path.relative_to(ROOT)), "sha256": digest(report_path)},
            "discussion": {"path": str(discussion_path.relative_to(ROOT)), "sha256": digest(discussion_path)},
        },
        "replay_hashes": replay_hashes,
        "checks": checks,
        "summary": summary,
    }
    if summary["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"exact replay failed: {failed}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--generator", type=Path, default=DEFAULT_GENERATOR)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = replay(args.protocol, args.generator, args.result, args.report, args.discussion)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
