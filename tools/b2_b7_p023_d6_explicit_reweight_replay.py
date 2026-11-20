#!/usr/bin/env python3
"""Fresh-subprocess replay for the frozen explicit-reweight producer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_explicit_reweight_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_explicit_reweight_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_d6_explicit_reweight_discussion_v1.md"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_explicit_reweight_replay_v1.json"
RUNNER = ROOT / "tools/b2_b7_p023_d6_explicit_reweight.py"
PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_explicit_reweight_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def build_replay() -> dict[str, Any]:
    expected = read(DEFAULT_RESULT)
    commit = expected["public_freeze"]["commit"]
    discussion = int(expected["public_freeze"]["discussion_number"])
    with tempfile.TemporaryDirectory(prefix="explicit-reweight-replay-") as temp:
        temp_dir = Path(temp)
        replay_result = temp_dir / "result.json"
        replay_report = temp_dir / "report.md"
        replay_discussion = temp_dir / "discussion.md"
        completed = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--protocol",
                str(PROTOCOL),
                "--output",
                str(replay_result),
                "--report",
                str(replay_report),
                "--discussion-output",
                str(replay_discussion),
                "--public-freeze-commit",
                commit,
                "--discussion-number",
                str(discussion),
            ],
            cwd=ROOT,
            env=os.environ.copy(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        replay = read(replay_result) if replay_result.exists() else {}
        byte_rows = []
        for name, produced, canonical_path in (
            ("result", replay_result, DEFAULT_RESULT),
            ("report", replay_report, DEFAULT_REPORT),
            ("discussion", replay_discussion, DEFAULT_DISCUSSION),
        ):
            produced_bytes = produced.read_bytes() if produced.exists() else b""
            expected_bytes = canonical_path.read_bytes()
            byte_rows.append(
                {
                    "name": name,
                    "produced_sha256": sha_bytes(produced_bytes),
                    "expected_sha256": sha_bytes(expected_bytes),
                    "byte_equal": produced_bytes == expected_bytes,
                }
            )
    expected_windows = 1024 * 164
    replay_window_gate = bool(
        replay
        and all(
            row["window_syndromes_equal"] == expected_windows
            and row["window_outputs_equal"] == expected_windows
            for row in replay["basis_rows"]
        )
    )
    adjudicated = (
        "nine_bit_explicit_reweight_semantic_pass_hardware_write_path_absent"
        if replay_window_gate
        else "fresh_holdout_explicit_reweight_semantic_regression"
    )
    checks = [
        check("subprocess_exit", completed.returncode == 0, f"exit={completed.returncode}"),
        check("result_exists", bool(replay), "Replay result was emitted."),
        check("result_bytes", byte_rows[0]["byte_equal"], byte_rows[0]["produced_sha256"]),
        check("report_bytes", byte_rows[1]["byte_equal"], byte_rows[1]["produced_sha256"]),
        check("discussion_bytes", byte_rows[2]["byte_equal"], byte_rows[2]["produced_sha256"]),
        check("freeze_commit", replay.get("public_freeze", {}).get("commit") == commit, commit),
        check("discussion_number", replay.get("public_freeze", {}).get("discussion_number") == discussion, str(discussion)),
        check("corpus_hashes", replay.get("corpora") == expected["corpora"], "Fresh seeds and corpus hashes reproduce."),
        check("basis_rows", replay.get("basis_rows") == expected["basis_rows"], "All decoded rows and payload summaries reproduce."),
        check("producer_classification", replay.get("classification") == expected["classification"], expected["classification"]),
        check("window_veto_replayed", not replay_window_gate, "All-window exactness fails again."),
        check("adjudication_replayed", adjudicated == "fresh_holdout_explicit_reweight_semantic_regression", adjudicated),
        check("hard_boundary", replay.get("verdict", {}).get("hardware_decoder_deadline_passed") is False and replay.get("verdict", {}).get("b7_resource_credit") == 0, "No hardware/B7 credit."),
    ]
    result: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_explicit_reweight_replay_v1",
        "producer_subprocess_exit": completed.returncode,
        "producer_stdout_sha256": sha_bytes(completed.stdout.encode()),
        "byte_rows": byte_rows,
        "replayed_producer_classification": replay.get("classification"),
        "replayed_adjudicated_classification": adjudicated,
        "replayed_window_exactness_gate_pass": replay_window_gate,
        "checks": checks,
        "summary": {
            "checks_total": len(checks),
            "checks_passed": sum(item["passed"] for item in checks),
            "checks_failed": sum(not item["passed"] for item in checks),
            "all_producer_artifact_bytes_equal": all(
                row["byte_equal"] for row in byte_rows
            ),
            "adjudicated_semantic_veto_pass": False,
        },
    }
    result["replay_id"] = sha_bytes(compact(result))
    if result["summary"]["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"replay checks failed: {failed}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build_replay()
    args.output.write_text(canonical(result), encoding="utf-8")
    print(
        canonical(
            {
                "replayed_adjudicated_classification": result[
                    "replayed_adjudicated_classification"
                ],
                "replay_id": result["replay_id"],
                "summary": result["summary"],
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
