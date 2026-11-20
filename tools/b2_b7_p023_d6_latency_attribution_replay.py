#!/usr/bin/env python3
"""Deterministic subprocess replay of the latency-attribution audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_latency_attribution_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_latency_attribution_v1.json"
DEFAULT_AUDIT = ROOT / "results/B2_B7_P023_d6_latency_attribution_audit_v1.json"
DEFAULT_REPLAY = ROOT / "results/B2_B7_P023_d6_latency_attribution_replay_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_digest(path: Path) -> str:
    return digest(path.read_bytes())


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument(
        "--auditor",
        type=Path,
        default=ROOT / "tools/b2_b7_p023_d6_latency_attribution_audit.py",
    )
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    args = parser.parse_args()
    protocol = read(args.protocol)
    result = read(args.result)
    audit = read(args.audit)
    expected = args.audit.read_bytes()
    with tempfile.TemporaryDirectory(prefix="qec-latency-attribution-replay-") as temp:
        recreated_path = Path(temp) / "audit.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(args.auditor),
                "--protocol",
                str(args.protocol),
                "--result",
                str(args.result),
                "--audit",
                str(recreated_path),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        recreated = recreated_path.read_bytes() if recreated_path.exists() else b""
    checks = [
        check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact QEC scope."),
        check("result_binding", audit["source_result"]["sha256"] == file_digest(args.result), file_digest(args.result)),
        check("auditor_binding", audit["auditor"]["sha256"] == file_digest(args.auditor), file_digest(args.auditor)),
        check("subprocess_exit", completed.returncode == 0, f"returncode={completed.returncode}"),
        check("audit_recreated", bool(recreated), f"bytes={len(recreated)}"),
        check("audit_bytes_exact", recreated == expected, digest(recreated) if recreated else "missing"),
        check("audit_checks", audit["summary"]["checks_passed"] == 19 and audit["summary"]["checks_failed"] == 0, "19/19 independent checks."),
        check("corpus_replay", audit["summary"]["source_chunks_replayed"] == 8, "8/8 chunks."),
        check("prediction_replay", audit["summary"]["direct_prediction_rows_replayed"] == 2048 and audit["summary"]["sync_timed_prediction_rows_replayed"] == 256, "2,304 prediction rows."),
        check("timing_replay", audit["summary"]["raw_timing_vectors_replayed"] == 22, "22 raw timing vectors."),
        check("classification", audit["summary"]["classification"] == result["classification"] == "matching_kernel_tail_bottleneck", result["classification"]),
        check("hard_boundaries", audit["summary"]["hardware_decoder_deadline_passed"] is False and audit["summary"]["full_b2_credit_ready"] is False and audit["summary"]["p023_scalable_memory_ready"] is False and audit["summary"]["b7_resource_credit"] == 0, "No downstream credit."),
    ]
    output: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_latency_attribution_replay_v1",
        "as_of_date": protocol["as_of_date"],
        "scope": protocol["scope"],
        "source_result": {
            "path": str(args.result.resolve().relative_to(ROOT)),
            "sha256": file_digest(args.result),
        },
        "source_audit": {
            "path": str(args.audit.resolve().relative_to(ROOT)),
            "sha256": file_digest(args.audit),
            "audit_id": audit["audit_id"],
        },
        "auditor": {
            "path": str(args.auditor.resolve().relative_to(ROOT)),
            "sha256": file_digest(args.auditor),
        },
        "replay_environment": {
            "python": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "subprocess": {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
        "recreated_audit_sha256": digest(recreated) if recreated else None,
        "audit_bytes_exact": recreated == expected,
        "checks": checks,
        "summary": {
            "checks_passed": sum(item["passed"] for item in checks),
            "checks_failed": sum(not item["passed"] for item in checks),
            "audit_bytes_exact": recreated == expected,
            "source_chunks_replayed": audit["summary"]["source_chunks_replayed"],
            "direct_prediction_rows_replayed": audit["summary"]["direct_prediction_rows_replayed"],
            "sync_timed_prediction_rows_replayed": audit["summary"]["sync_timed_prediction_rows_replayed"],
            "raw_timing_vectors_replayed": audit["summary"]["raw_timing_vectors_replayed"],
            "classification": audit["summary"]["classification"],
            "semantic_veto_pass": audit["summary"]["semantic_veto_pass"],
            "hardware_decoder_deadline_passed": False,
            "full_b2_credit_ready": False,
            "p023_scalable_memory_ready": False,
            "b7_resource_credit": 0,
        },
    }
    if output["summary"]["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"deterministic replay failed: {failed}")
    output["replay_id"] = digest(
        compact(
            {
                "source_result": output["source_result"],
                "source_audit": output["source_audit"],
                "recreated_audit_sha256": output["recreated_audit_sha256"],
                "summary": output["summary"],
            }
        )
    )
    args.replay.write_text(canonical(output), encoding="utf-8")
    print(canonical(output["summary"]), end="")


if __name__ == "__main__":
    main()
