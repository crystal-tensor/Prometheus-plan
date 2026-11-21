#!/usr/bin/env python3
"""Independently audit the complete-shot X real-RTL calibration evidence."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks/B2_B7_P023_d6_x_phase_primal_dual_input_v1.json"
SHARD = ROOT / "benchmarks/B2_B7_P023_d6_x_full_corpus_shard_0000_v1.json"
RAW = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_rtl_v1.json"
CAPTURE = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_capture_v1.json"
LOG = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_capture_v1.log"
PATCH = ROOT / "tools/microblossom/d6_x_phase_primal_dual_full_corpus_shard_v7.patch"
EVIDENCE = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_evidence_v1.json"
OUTPUT = ROOT / "results/B2_B7_P023_d6_x_full_corpus_shard_0000_audit_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_id(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("evidence_id", None)
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def main() -> None:
    base = read(BASE)
    shard = read(SHARD)
    raw = read(RAW)
    capture = read(CAPTURE)
    evidence = read(EVIDENCE)
    rows = raw["cases"]
    checks: list[dict[str, Any]] = []

    def check(name: str, condition: bool) -> None:
        checks.append({"name": name, "pass": bool(condition)})

    check("base evidence binding", shard["base_input_evidence_id"] == base["evidence_id"])
    check("capture base hash", capture["base_input_sha256"] == sha256(BASE))
    check("capture shard hash", capture["shard_sha256"] == sha256(SHARD))
    check("capture patch hash", capture["source_patch_sha256"] == sha256(PATCH))
    check("capture output hash", capture["output_sha256"] == sha256(RAW))
    check("capture log hash", capture["log_sha256"] == sha256(LOG))
    check("shard schema", shard["schema"] == "b2_b7_p023_d6_x_full_corpus_shard_v1")
    check("frozen basis", shard["basis"] == "x")
    check("one complete shot", shard["shots"] == 1 and shard["windows_per_shot"] == 164)
    check("shot interval", shard["shot_start"] == 0 and shard["shot_end"] == 1)
    check("shard case cardinality", len(shard["cases"]) == 164)
    check("no accepted residual failure", shard["commit_residual_failures"] == 0 and shard["final_residual_failures"] == 0)
    check("raw shard binding", raw["shard_evidence_id"] == shard["evidence_id"])
    check("raw case sequence binding", raw["case_sequence_sha256"] == shard["case_sequence_sha256"])
    check("raw case cardinality", len(rows) == 164)
    check("window order", [row["window"] for row in rows] == list(range(164)))
    check("single shot order", all(row["shot"] == 0 for row in rows))
    expected_phases = ["opening"] + ["steady"] * 162 + ["closing"]
    check("phase order", [row["phase"] for row in rows] == expected_phases)
    check("phase indices", [row["phase_index"] for row in rows] == [0] + [1] * 162 + [2])
    check("per-case syndrome gate", all(row["syndrome_valid"] for row in rows))
    check("per-case correction gate", all(row["correction_equal"] for row in rows))
    check("summary syndrome gate", raw["summary"]["all_syndromes_valid"] is True)
    check("summary correction gate", raw["summary"]["all_corrections_equal"] is True)
    check("defect count", sum(row["defects"] for row in rows) == raw["summary"]["total_defects"] == 1648)
    check("selector count", sum(row["selectors"] for row in rows) == raw["summary"]["total_selectors"] == 918)
    check("iteration maximum", max(row["iterations"] for row in rows) == raw["summary"]["max_iterations"] == 15)
    check("iteration total", sum(row["iterations"] for row in rows) == raw["summary"]["total_iterations"] == 946)
    occupancy = raw["occupancy_audit"]
    check("occupancy cardinality", occupancy["checks"] == occupancy["expected_checks"] == 1648)
    check("occupancy clear", occupancy["all_clear"] is True)
    check("capture exit", capture["exit_code"] == 0)
    check("capture forbidden list", capture["forbidden_hits"] == [])
    check("capture unexpected warnings", capture["unexpected_warning_lines"] == [])
    check("capture accepted", capture["accepted_x_shard_real_rtl_gate"] is True)
    check("evidence canonical id", evidence["evidence_id"] == canonical_id(evidence))
    check("evidence classification", evidence["classification"] == "x_complete_shot_0000_real_rtl_calibration_pass")
    acceptance = evidence["acceptance"]
    check("narrow shot credit", acceptance["complete_shot_0000_real_rtl"] is True)
    check("full X credit withheld", acceptance["all_accepted_x_corpus_end_to_end"] is False)
    check("Z credit withheld", acceptance["z_basis_phase_bank_switching"] is False)
    check("hardware timing credit withheld", acceptance["p99_le_1us"] is False and acceptance["miss_rate_le_1pct"] is False)
    check("project credit withheld", acceptance["full_b2"] is False and acceptance["scalable_p023"] is False and acceptance["b7_resource_credit"] == 0)

    passed = sum(row["pass"] for row in checks)
    payload = {
        "schema": "b2_b7_p023_d6_x_full_corpus_shard_0000_audit_v1",
        "date": "2026-11-21",
        "scope": ["021/B7", "022/B2", "023"],
        "checks": checks,
        "summary": {
            "passed": passed,
            "total": len(checks),
            "all_pass": passed == len(checks),
        },
    }
    OUTPUT.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload["summary"], sort_keys=True))
    if passed != len(checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
