#!/usr/bin/env python3
"""Capture the pinned Verilator closed-loop Z pilot and its acceptance metadata."""

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
    "assertion failed",
    "unaccessible signal",
    "panicked at",
    "modulenotfounderror",
)
KNOWN_WARNINGS = (
    "signals were pruned",
    "variable length arrays in c++ are a clang extension",
    "warnings generated.",
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
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--selector-server", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--verilator-bin", type=Path, required=True)
    parser.add_argument("--verilator-root", type=Path, required=True)
    args = parser.parse_args()

    pilot = json.loads(args.pilot.read_text(encoding="utf-8"))
    expected_cases = len(pilot["shots"]) * len(pilot["windows"])
    command = [
        "cargo",
        "run",
        "--release",
        "--bin",
        "d6_z_phase_primal_dual_closed_loop",
        "--",
        str(args.base_input.resolve()),
        str(args.pilot.resolve()),
        str(args.output.resolve()),
        str(args.python.resolve()),
        str(args.selector_server.resolve()),
    ]
    environment = os.environ.copy()
    environment["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
    environment["PATH"] = (
        str(args.verilator_bin)
        + ":/opt/homebrew/opt/openjdk@17/bin:/opt/homebrew/bin:"
        + environment["PATH"]
    )
    environment["VERILATOR_ROOT"] = str(args.verilator_root)
    environment["RUST_BACKTRACE"] = "1"
    environment["MICROBLOSSOM_PHASE_SIMULATOR"] = "verilator"
    simulator_version = subprocess.run(
        [str(args.verilator_bin / "verilator"), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    python_version = subprocess.run(
        [str(args.python), "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

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
    accepted = all((
        exit_code == 0,
        summary.get("cases") == expected_cases,
        summary.get("all_syndromes_valid") is True,
        summary.get("commit_residual_failures") == 0,
        summary.get("final_residual_failures") == 0,
        summary.get("final_frame_failures") == 0,
        summary.get("accepted_closed_loop_gate") is True,
        occupancy.get("all_clear") is True,
        occupancy.get("checks") == occupancy.get("expected_checks"),
        result.get("pilot_evidence_id") == pilot["evidence_id"],
        not forbidden_hits,
        not unexpected_warnings,
    ))
    elapsed = (finished - started).total_seconds()
    metadata = {
        "schema": "b2_b7_p023_d6_z_closed_loop_capture_v1",
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "elapsed_seconds": elapsed,
        "elapsed_seconds_per_case": elapsed / expected_cases,
        "command": command,
        "exit_code": exit_code,
        "simulator": "verilator",
        "simulator_version": simulator_version,
        "python_version": python_version,
        "source_archive_sha256": sha256(args.source_archive),
        "source_patch_sha256": sha256(args.source_patch),
        "base_input_sha256": sha256(args.base_input),
        "pilot_sha256": sha256(args.pilot),
        "selector_server_sha256": sha256(args.selector_server),
        "output_sha256": sha256(args.output) if args.output.exists() else None,
        "log_sha256": sha256(args.log),
        "forbidden_hits": forbidden_hits,
        "known_warning_lines": [
            line for line in warning_lines if any(known in line for known in KNOWN_WARNINGS)
        ],
        "unexpected_warning_lines": unexpected_warnings,
        "result_summary": summary,
        "occupancy_audit": occupancy,
        "accepted_z_closed_loop_real_rtl_gate": accepted,
    }
    args.metadata.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    print(json.dumps(metadata, sort_keys=True))
    if not accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
