#!/usr/bin/env python3
"""Deterministic replay of the independent online-window audit."""

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
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_online_window_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_online_window_v1.json"
DEFAULT_AUDIT = ROOT / "results/B2_B7_P023_d6_online_window_audit_v1.json"
DEFAULT_REPLAY = ROOT / "results/B2_B7_P023_d6_online_window_replay_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


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
        default=ROOT / "tools/b2_b7_p023_d6_online_window_audit.py",
    )
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    args = parser.parse_args()

    protocol = read(args.protocol)
    result = read(args.result)
    audit = read(args.audit)
    expected_audit_bytes = args.audit.read_bytes()
    with tempfile.TemporaryDirectory(prefix="qec-online-window-replay-") as temp_dir:
        replay_audit_path = Path(temp_dir) / "audit.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(args.auditor),
                "--protocol",
                str(args.protocol),
                "--result",
                str(args.result),
                "--audit",
                str(replay_audit_path),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        replay_bytes = replay_audit_path.read_bytes() if replay_audit_path.exists() else b""

    checks = [
        check("scope", protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact QEC scope."),
        check("result_binding", audit["source_result"]["sha256"] == sha_path(args.result), sha_path(args.result)),
        check("audit_binding", sha_bytes(expected_audit_bytes) == sha_path(args.audit), sha_path(args.audit)),
        check("auditor_binding", audit["auditor"]["sha256"] == sha_path(args.auditor), sha_path(args.auditor)),
        check("subprocess_exit", completed.returncode == 0, f"returncode={completed.returncode}"),
        check("audit_recreated", bool(replay_bytes), f"bytes={len(replay_bytes)}"),
        check("audit_bytes_exact", replay_bytes == expected_audit_bytes, sha_bytes(replay_bytes) if replay_bytes else "missing"),
        check("audit_checks", audit["summary"]["checks_passed"] == 18 and audit["summary"]["checks_failed"] == 0, "18/18 independent checks."),
        check("chunk_replay", audit["summary"]["source_chunks_replayed"] == 8, "8/8 source chunks."),
        check("prediction_replay", audit["summary"]["online_arms_replayed"] == 4 and audit["summary"]["prediction_rows_replayed"] == 4096, "Four arms and 4,096 rows."),
        check("negative_verdict", audit["summary"]["online_correlated_host_proxy_pass"] is False and result["verdict"]["online_correlated_host_proxy_pass"] is False, result["decision"]),
        check("hard_boundaries", audit["summary"]["hardware_decoder_deadline_passed"] is False and audit["summary"]["full_b2_credit_ready"] is False and audit["summary"]["p023_scalable_memory_ready"] is False and audit["summary"]["b7_resource_credit"] == 0, "No downstream credit."),
    ]
    output: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_online_window_replay_v1",
        "as_of_date": protocol["as_of_date"],
        "scope": protocol["scope"],
        "source_result": {
            "path": str(args.result.resolve().relative_to(ROOT)),
            "sha256": sha_path(args.result),
        },
        "source_audit": {
            "path": str(args.audit.resolve().relative_to(ROOT)),
            "sha256": sha_path(args.audit),
            "audit_id": audit["audit_id"],
        },
        "auditor": {
            "path": str(args.auditor.resolve().relative_to(ROOT)),
            "sha256": sha_path(args.auditor),
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
        "replayed_audit_sha256": sha_bytes(replay_bytes) if replay_bytes else None,
        "audit_bytes_exact": replay_bytes == expected_audit_bytes,
        "checks": checks,
        "summary": {
            "checks_passed": sum(item["passed"] for item in checks),
            "checks_failed": sum(not item["passed"] for item in checks),
            "audit_bytes_exact": replay_bytes == expected_audit_bytes,
            "source_chunks_replayed": audit["summary"]["source_chunks_replayed"],
            "online_arms_replayed": audit["summary"]["online_arms_replayed"],
            "prediction_rows_replayed": audit["summary"]["prediction_rows_replayed"],
            "online_correlated_host_proxy_pass": False,
            "hardware_decoder_deadline_passed": False,
            "full_b2_credit_ready": False,
            "p023_scalable_memory_ready": False,
            "b7_resource_credit": 0,
        },
    }
    if output["summary"]["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"deterministic replay failed: {failed}")
    output["replay_id"] = sha_bytes(
        compact(
            {
                "source_result": output["source_result"],
                "source_audit": output["source_audit"],
                "replayed_audit_sha256": output["replayed_audit_sha256"],
                "summary": output["summary"],
            }
        )
    )
    args.replay.write_text(canonical(output), encoding="utf-8")
    print(canonical(output["summary"]), end="")


if __name__ == "__main__":
    main()
