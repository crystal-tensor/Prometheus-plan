#!/usr/bin/env python3
"""Exact replay of the deterministic distance-6 candidate freeze packet."""

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
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_candidate_freeze_v1.json"
DEFAULT_GENERATOR = ROOT / "tools/b2_b7_p023_d6_candidate_freeze.py"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_candidate_freeze_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_candidate_freeze_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_d6_candidate_freeze_discussion_v1.md"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_candidate_freeze_replay_v1.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def replay(protocol: Path, generator: Path, result: Path, report: Path, discussion: Path) -> dict[str, Any]:
    expected = load(result)
    checks: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="qec-d6-freeze-") as temp:
        folder = Path(temp)
        result2 = folder / "result.json"
        report2 = folder / "report.md"
        discussion2 = folder / "discussion.md"
        process = subprocess.run(
            [
                sys.executable,
                str(generator),
                "--protocol",
                str(protocol),
                "--output",
                str(result2),
                "--report",
                str(report2),
                "--discussion",
                str(discussion2),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        checks.append(check("producer_exit", process.returncode == 0, process.stdout.strip() if process.returncode == 0 else process.stderr.strip()))
        if process.returncode:
            raise ValueError(process.stderr)
        actual = load(result2)
        checks.append(check("result_bytes", result2.read_bytes() == result.read_bytes(), sha(result2)))
        checks.append(check("report_bytes", report2.read_bytes() == report.read_bytes(), sha(report2)))
        checks.append(check("discussion_bytes", discussion2.read_bytes() == discussion.read_bytes(), sha(discussion2)))
        checks.append(check("schema", actual["schema_version"] == expected["schema_version"], actual["schema_version"]))
        checks.append(check("scope", actual["scope"] == expected["scope"], "Exact scope."))
        checks.append(check("protocol", actual["protocol_binding"] == expected["protocol_binding"], actual["protocol_binding"]["sha256"]))
        checks.append(check("frozen_inputs", actual["frozen_inputs_current"] == expected["frozen_inputs_current"] and actual["frozen_inputs_at_commit"] == expected["frozen_inputs_at_commit"], "Exact frozen bindings."))
        checks.append(check("generator", actual["generator"] == expected["generator"] and actual["generator"]["sha256"] == sha(generator), actual["generator"]["sha256"]))
        checks.append(check("environment", actual["execution_environment"] == expected["execution_environment"], str(actual["execution_environment"])))
        checks.append(check("candidate", actual["candidate"] == expected["candidate"], actual["candidate"]["candidate_id"]))
        checks.append(check("candidate_rows", actual["candidate_rows"] == expected["candidate_rows"], "Both structural rows are exact."))
        checks.append(check("conditional_score", actual["conditional_resource_score"] == expected["conditional_resource_score"], str(actual["conditional_resource_score"]["composite_score_if_both_bases_verify"])))
        checks.append(check("no_outcome", all(row["stochastic_shots"] == 0 and row["logical_failures_observed"] is None and row["acceptance_seed"] is None for row in actual["candidate_rows"]), "No outcome appeared during replay."))
        checks.append(check("readiness", actual["readiness"] == expected["readiness"], str(actual["readiness"])))
        checks.append(check("formal_checks", actual["formal_checks"] == expected["formal_checks"], f"{actual['summary']['checks_passed']}/{actual['summary']['checks_total']}"))
        checks.append(check("summary", actual["summary"] == expected["summary"], str(actual["summary"])))
        checks.append(check("decision", actual["decision"] == expected["decision"], actual["decision"]))
        checks.append(check("run_id", actual["run_id"] == expected["run_id"], actual["run_id"]))
        replay_hashes = {
            "result_sha256": sha(result2),
            "report_sha256": sha(report2),
            "discussion_sha256": sha(discussion2),
        }
    summary = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "exact_structural_rows": 2 if all(item["passed"] for item in checks) else 0,
        "stochastic_shots": 0,
    }
    output = {
        "schema_version": "b2_b7_p023_d6_candidate_freeze_replay_audit_v1",
        "source": {
            "protocol": {"path": str(protocol.relative_to(ROOT)), "sha256": sha(protocol)},
            "generator": {"path": str(generator.relative_to(ROOT)), "sha256": sha(generator)},
            "result": {"path": str(result.relative_to(ROOT)), "sha256": sha(result)},
            "report": {"path": str(report.relative_to(ROOT)), "sha256": sha(report)},
            "discussion": {"path": str(discussion.relative_to(ROOT)), "sha256": sha(discussion)},
        },
        "replay_hashes": replay_hashes,
        "checks": checks,
        "summary": summary,
    }
    if summary["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"freeze replay failed: {failed}")
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
