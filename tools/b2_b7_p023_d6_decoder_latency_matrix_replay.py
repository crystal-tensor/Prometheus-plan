#!/usr/bin/env python3
"""Exact deterministic replay for the distance-6 decoder latency matrix."""

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
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_decoder_latency_matrix_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_decoder_latency_matrix_v1.json"
DEFAULT_AUDITOR = ROOT / "tools/b2_b7_p023_d6_decoder_latency_matrix_audit.py"
DEFAULT_AUDIT = ROOT / "results/B2_B7_P023_d6_decoder_latency_matrix_audit_v1.json"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_decoder_latency_matrix_replay_v1.json"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def replay(
    protocol: Path,
    result: Path,
    auditor: Path,
    audit_path: Path,
) -> dict[str, Any]:
    expected_audit = load(audit_path)
    source_result = load(result)
    checks: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="qec-d6-latency-replay-") as folder_name:
        replay_path = Path(folder_name) / "audit.json"
        process = subprocess.run(
            [
                sys.executable,
                str(auditor),
                "--protocol",
                str(protocol),
                "--result",
                str(result),
                "--output",
                str(replay_path),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        checks.append(check("auditor_exit", process.returncode == 0, process.stdout.strip() if process.returncode == 0 else process.stderr.strip()))
        if process.returncode:
            raise ValueError(process.stderr)
        actual_audit = load(replay_path)
        checks.append(check("audit_bytes", replay_path.read_bytes() == audit_path.read_bytes(), sha(replay_path)))
        checks.append(check("schema", actual_audit["schema_version"] == expected_audit["schema_version"], actual_audit["schema_version"]))
        checks.append(check("source_result", actual_audit["source_result"] == expected_audit["source_result"] and actual_audit["source_result"]["sha256"] == sha(result), actual_audit["source_result"]["sha256"]))
        checks.append(check("auditor", actual_audit["auditor"] == expected_audit["auditor"] and actual_audit["auditor"]["sha256"] == sha(auditor), actual_audit["auditor"]["sha256"]))
        checks.append(check("input_hashes", actual_audit["input_hashes"] == expected_audit["input_hashes"], "All frozen input hashes exact."))
        checks.append(check("corpora", actual_audit["reconstructed"]["corpora"] == expected_audit["reconstructed"]["corpora"], "Both corpus reconstructions exact."))
        checks.append(check("prediction_rows", actual_audit["reconstructed"]["prediction_rows"] == expected_audit["reconstructed"]["prediction_rows"], "All 20 prediction rows exact."))
        checks.append(check("source_chunks", actual_audit["summary"]["exact_source_chunks"] == expected_audit["summary"]["exact_source_chunks"] == 8, "Eight source chunks exact."))
        checks.append(check("prediction_count", actual_audit["summary"]["exact_prediction_rows"] == expected_audit["summary"]["exact_prediction_rows"] == 20, "Twenty prediction rows exact."))
        checks.append(check("checks", actual_audit["checks"] == expected_audit["checks"] and actual_audit["summary"]["checks_failed"] == 0, f"{actual_audit['summary']['checks_passed']}/{actual_audit['summary']['checks_total']}"))
        checks.append(check("proxy_verdict", actual_audit["summary"]["software_batch1_backlog_proxy_pass"] == source_result["verdict"]["software_batch1_backlog_proxy_pass"], str(source_result["verdict"]["software_batch1_backlog_proxy_pass"])))
        checks.append(check("hardware_boundary", not actual_audit["summary"]["hardware_decoder_deadline_passed"] and not source_result["verdict"]["hardware_decoder_deadline_passed"] and not source_result["verdict"]["full_b2_credit_ready"] and not source_result["verdict"]["p023_scalable_memory_ready"] and source_result["verdict"]["b7_resource_credit"] == 0, "Hardware/full-credit gates remain closed."))
        replay_hash = sha(replay_path)
    summary = {
        "checks_total": len(checks),
        "checks_passed": sum(item["passed"] for item in checks),
        "checks_failed": sum(not item["passed"] for item in checks),
        "exact_source_chunks": 8 if all(item["passed"] for item in checks) else 0,
        "exact_prediction_rows": 20 if all(item["passed"] for item in checks) else 0,
        "audit_bytes_exact": all(item["passed"] for item in checks),
    }
    output = {
        "schema_version": "b2_b7_p023_d6_decoder_latency_matrix_replay_v1",
        "source": {
            "protocol": {"path": str(protocol.relative_to(ROOT)), "sha256": sha(protocol)},
            "result": {"path": str(result.relative_to(ROOT)), "sha256": sha(result)},
            "auditor": {"path": str(auditor.relative_to(ROOT)), "sha256": sha(auditor)},
            "audit": {"path": str(audit_path.relative_to(ROOT)), "sha256": sha(audit_path)},
        },
        "replayed_audit_sha256": replay_hash,
        "checks": checks,
        "summary": summary,
    }
    if summary["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"latency replay failed: {failed}")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--auditor", type=Path, default=DEFAULT_AUDITOR)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = replay(args.protocol, args.result, args.auditor, args.audit)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
