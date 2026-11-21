#!/usr/bin/env python3
"""Capture a pinned real-RTL X full-corpus shard run and its acceptance metadata."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


FORBIDDEN = (
    "[error]",
    "cannot set a vertex to defect",
    "assertion failed",
    "unaccessible signal",
    "panicked at",
)
KNOWN_WARNINGS = (
    "signals were pruned",
    "value 'z' at position 0 is neither '0' or '1'. value set to '0'",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--source-archive", type=Path, required=True)
    parser.add_argument("--source-patch", type=Path, required=True)
    parser.add_argument("--base-input", type=Path, required=True)
    parser.add_argument("--shard", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()

    shard = json.loads(args.shard.read_text(encoding="utf-8"))
    expected_cases = int(shard["shots"]) * int(shard["windows_per_shot"])
    command = [
        "cargo",
        "run",
        "--release",
        "--bin",
        "d6_x_phase_primal_dual_shard",
        "--",
        str(args.base_input.resolve()),
        str(args.shard.resolve()),
        str(args.output.resolve()),
    ]
    environment = os.environ.copy()
    environment["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
    environment["PATH"] = "/opt/homebrew/opt/openjdk@17/bin:/opt/homebrew/bin:" + environment["PATH"]
    environment["RUST_BACKTRACE"] = "1"

    started = dt.datetime.now(dt.timezone.utc)
    process = subprocess.Popen(
        command,
        cwd=args.source_dir / "src/cpu/blossom",
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    captured: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        captured.append(line)
        sys.stdout.write(line)
        sys.stdout.flush()
    exit_code = process.wait()
    finished = dt.datetime.now(dt.timezone.utc)
    args.log.write_text("".join(captured), encoding="utf-8")

    lower_lines = [line.lower() for line in captured]
    forbidden_hits = [
        line.strip() for line in lower_lines if any(marker in line for marker in FORBIDDEN)
    ]
    warning_lines = [line.strip() for line in lower_lines if "warning" in line]
    unexpected_warnings = [
        line for line in warning_lines if not any(known in line for known in KNOWN_WARNINGS)
    ]
    result = json.loads(args.output.read_text()) if args.output.exists() else {}
    summary = result.get("summary", {})
    occupancy = result.get("occupancy_audit", {})
    accepted = all(
        (
            exit_code == 0,
            summary.get("cases") == expected_cases,
            summary.get("all_syndromes_valid") is True,
            summary.get("all_corrections_equal") is True,
            occupancy.get("all_clear") is True,
            occupancy.get("checks") == occupancy.get("expected_checks"),
            result.get("shard_evidence_id") == shard["evidence_id"],
            not forbidden_hits,
            not unexpected_warnings,
        )
    )
    elapsed = (finished - started).total_seconds()
    metadata = {
        "schema": "b2_b7_p023_d6_x_full_corpus_shard_capture_v1",
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "elapsed_seconds": elapsed,
        "elapsed_seconds_per_case": elapsed / expected_cases,
        "command": command,
        "exit_code": exit_code,
        "source_archive_sha256": sha256(args.source_archive),
        "source_patch_sha256": sha256(args.source_patch),
        "base_input_sha256": sha256(args.base_input),
        "shard_sha256": sha256(args.shard),
        "output_sha256": sha256(args.output) if args.output.exists() else None,
        "log_sha256": sha256(args.log),
        "forbidden_hits": forbidden_hits,
        "known_warning_lines": [
            line for line in warning_lines if any(known in line for known in KNOWN_WARNINGS)
        ],
        "unexpected_warning_lines": unexpected_warnings,
        "result_summary": summary,
        "occupancy_audit": occupancy,
        "accepted_x_shard_real_rtl_gate": accepted,
    }
    args.metadata.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps(metadata, sort_keys=True))
    if not accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
