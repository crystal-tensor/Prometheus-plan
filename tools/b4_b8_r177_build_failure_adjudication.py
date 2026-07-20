#!/usr/bin/env python3
"""Seal the public R177 build-discovery failure without scientific credit."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


RUN_ID = 29753174310
JOB_ID = 88388737719
ARTIFACT_ID = 8465795642
RUN_URL = "https://github.com/crystal-tensor/Prometheus-plan/actions/runs/29753174310"
DISCUSSION_URL = "https://github.com/crystal-tensor/Prometheus-plan/discussions/266"
PREREGISTRATION_COMMIT = "7a4045fe7a368ef8e5d091f4dcccd738445137d9"
PROTOCOL_PATH = "results/B4_B8_R177_linux_x86_64_protocol_v0.json"
CONTRACT_PATH = "benchmarks/B4_B8_R177_linux_x86_64_contract_v0.json"
LOG_DIR = "research/source_lineage/R177_linux_x86_64_build_logs"
RESULT_PATH = "results/B4_B8_R177_linux_x86_64_build_failure_v0.json"
REPORT_PATH = "research/B4_B8_R177_linux_x86_64_build_failure.md"


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_hash(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    observed = payload.pop("payload_hash", None)
    expected = canonical_hash(payload)
    if observed != expected:
        raise ValueError(f"payload hash mismatch: {path}")
    return str(observed)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    output = root / RESULT_PATH
    report = root / REPORT_PATH
    if output.exists() or report.exists():
        raise ValueError("R177 failure adjudication already exists")
    protocol_hash = payload_hash(root / PROTOCOL_PATH)
    contract_hash = payload_hash(root / CONTRACT_PATH)
    log_root = root / LOG_DIR
    logs = [
        {
            "path": str(path.relative_to(root)),
            "sha256": file_sha256(path),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(log_root.glob("*.txt"))
    ]
    if len(logs) != 22:
        raise ValueError(f"R177 expected 22 downloaded log files, found {len(logs)}")
    release_stderr = (log_root / "11_cargo_release.stderr.txt").read_text(
        encoding="utf-8"
    )
    if (
        "Finished `release` profile [optimized]" not in release_stderr
        or "Compiling qiskit-pyext v2.4.1" not in release_stderr
    ):
        raise ValueError("R177 release-success evidence missing")
    result = {
        "title": "B4/B8/B10 R177 Linux x86-64 build failure adjudication",
        "version": 0,
        "method": "b4_b8_r177_build_failure_adjudication_v0",
        "status": "build_artifact_discovery_failed_before_scientific_replay",
        "source_target_id": ("T-B4-002dd/T-B8-003dh/T-B10-009ct-r177-build-failure"),
        "upstream_target_id": "T-B4-002dc/T-B8-003dg/T-B10-009cs-r177-protocol",
        "public_preregistration": {
            "commit": PREREGISTRATION_COMMIT,
            "discussion": DISCUSSION_URL,
            "created_at": "2026-07-20T14:57:48Z",
            "protocol_payload_hash": protocol_hash,
            "contract_payload_hash": contract_hash,
        },
        "github_actions": {
            "run_id": RUN_ID,
            "job_id": JOB_ID,
            "artifact_id": ARTIFACT_ID,
            "run_url": RUN_URL,
            "conclusion": "failure",
        },
        "completed_build_gates": [
            "official Qiskit source checkout",
            "R176 patch applicability and application",
            "patched-source hash verification",
            "cargo fmt --check",
            "cargo check for qiskit-transpiler",
            "three R176 fixed-accumulator unit tests",
            "git diff --check",
            "release build of qiskit-pyext",
        ],
        "failure": {
            "stage": "post_build_artifact_discovery",
            "observed_exception": (
                "ValueError: R177 expected one release accelerator, found []"
            ),
            "root_cause": (
                "the wrapper searched for libqiskit_accelerate.so even though "
                "crates/pyext/Cargo.toml names the cdylib qiskit_pyext"
            ),
            "scientific_matrix_started": False,
            "worker_count_started": 0,
            "recorded_call_count": 0,
            "warmup_call_count": 0,
            "oracle_started": False,
        },
        "downloaded_log_count": len(logs),
        "downloaded_logs": logs,
        "next_gate": (
            "freeze a new protocol that derives the qiskit_pyext artifact name "
            "from source metadata and verifies both ELF identity and Python import"
        ),
        "hardware_result_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "solved_frontier_claimed": False,
        "new_credit_delta": 0,
    }
    result["payload_hash"] = canonical_hash(result)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report.write_text(
        "\n".join(
            [
                "# B4/B8/B10 R177 Linux x86-64 Build Failure",
                "",
                f"- Public run: `{RUN_URL}`",
                f"- Result hash: `{result['payload_hash']}`",
                "- Status: `build_artifact_discovery_failed_before_scientific_replay`",
                "",
                "## What Passed",
                "",
                "The official source checkout, patch binding, patched-source hashes, cargo format/check/test gates, git diff check, and optimized `qiskit-pyext` release build completed successfully on Ubuntu x86-64.",
                "",
                "## What Failed",
                "",
                "The post-build wrapper searched for `libqiskit_accelerate.so`. Qiskit 2.4.1 declares the Python extension library as `qiskit_pyext`, so the successful build produced a differently named artifact and the wrapper rejected the run.",
                "",
                "## Claim Boundary",
                "",
                "No worker, warmup, recorded call, independent oracle, simulation, or hardware execution started. R177 therefore says nothing positive or negative about the cross-platform scientific result. It records a reproducible build-integration defect and grants no B4, B8, B10, hardware, advantage, or solved-frontier credit.",
                "",
                "## Next Gate",
                "",
                result["next_gate"].capitalize() + ".",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"status": result["status"], "payload_hash": result["payload_hash"]},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
