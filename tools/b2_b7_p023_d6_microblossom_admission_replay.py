#!/usr/bin/env python3
"""Deterministic producer-and-auditor replay for 8-bit graph admission."""

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
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_admission_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_admission_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_microblossom_admission_v1.md"
DEFAULT_DISCUSSION = (
    ROOT / "research/B2_B7_P023_d6_microblossom_admission_discussion_v1.md"
)
DEFAULT_AUDIT = (
    ROOT / "results/B2_B7_P023_d6_microblossom_admission_audit_v1.json"
)
DEFAULT_REPLAY = (
    ROOT / "results/B2_B7_P023_d6_microblossom_admission_replay_v1.json"
)
DEFAULT_PRODUCER = ROOT / "tools/b2_b7_p023_d6_microblossom_admission.py"
DEFAULT_AUDITOR = ROOT / "tools/b2_b7_p023_d6_microblossom_admission_audit.py"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


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
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--producer", type=Path, default=DEFAULT_PRODUCER)
    parser.add_argument("--auditor", type=Path, default=DEFAULT_AUDITOR)
    parser.add_argument("--replay", type=Path, default=DEFAULT_REPLAY)
    args = parser.parse_args()

    protocol = read(args.protocol)
    result = read(args.result)
    audit = read(args.audit)
    expected = {
        "result": args.result.read_bytes(),
        "report": args.report.read_bytes(),
        "discussion": args.discussion.read_bytes(),
        "audit": args.audit.read_bytes(),
    }

    with tempfile.TemporaryDirectory(prefix="qec-microblossom-replay-") as temp:
        folder = Path(temp)
        generated = {
            "result": folder / "result.json",
            "report": folder / "report.md",
            "discussion": folder / "discussion.md",
            "audit": folder / "audit.json",
        }
        producer = subprocess.run(
            [
                sys.executable,
                str(args.producer),
                "--protocol",
                str(args.protocol),
                "--output",
                str(generated["result"]),
                "--report",
                str(generated["report"]),
                "--discussion-output",
                str(generated["discussion"]),
                "--public-freeze-commit",
                result["public_freeze"]["commit"],
                "--discussion-number",
                str(result["public_freeze"]["discussion_number"]),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        auditor = subprocess.run(
            [
                sys.executable,
                str(args.auditor),
                "--protocol",
                str(args.protocol),
                "--result",
                str(args.result),
                "--output",
                str(generated["audit"]),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        recreated = {
            name: path.read_bytes() if path.exists() else b""
            for name, path in generated.items()
        }

    evidence_source = {key: value for key, value in result.items() if key != "evidence_id"}
    audit_source = {key: value for key, value in audit.items() if key != "audit_id"}
    byte_equality = {
        name: recreated[name] == expected[name] for name in expected
    }
    checks = [
        check(
            "scope",
            protocol["scope"]["included_catalog_problem_ids"] == [21, 22, 23],
            "Exact QEC scope.",
        ),
        check(
            "freeze_binding",
            len(result["public_freeze"]["commit"]) == 40
            and result["public_freeze"]["discussion_number"] == 337,
            f"{result['public_freeze']['commit']} / Discussion #337",
        ),
        check(
            "protocol_binding",
            result["protocol_binding"]["sha256"] == file_digest(args.protocol),
            file_digest(args.protocol),
        ),
        check(
            "producer_binding",
            result["protocol_binding"]["runner_sha256"]
            == file_digest(args.producer),
            file_digest(args.producer),
        ),
        check(
            "audit_result_binding",
            audit["source_result_sha256"] == file_digest(args.result),
            audit["source_result_sha256"],
        ),
        check(
            "auditor_independence",
            audit["producer_imported"] is False,
            "The auditor does not import the admission producer.",
        ),
        check(
            "evidence_id",
            digest(compact(evidence_source)) == result["evidence_id"],
            result["evidence_id"],
        ),
        check(
            "audit_id",
            digest(compact(audit_source)) == audit["audit_id"],
            audit["audit_id"],
        ),
        check(
            "producer_exit",
            producer.returncode == 0,
            f"returncode={producer.returncode}",
        ),
        check(
            "auditor_exit",
            auditor.returncode == 0,
            f"returncode={auditor.returncode}",
        ),
        check(
            "result_bytes_exact",
            byte_equality["result"],
            digest(recreated["result"]) if recreated["result"] else "missing",
        ),
        check(
            "report_bytes_exact",
            byte_equality["report"],
            digest(recreated["report"]) if recreated["report"] else "missing",
        ),
        check(
            "discussion_bytes_exact",
            byte_equality["discussion"],
            digest(recreated["discussion"])
            if recreated["discussion"]
            else "missing",
        ),
        check(
            "audit_bytes_exact",
            byte_equality["audit"],
            digest(recreated["audit"]) if recreated["audit"] else "missing",
        ),
        check(
            "formal_checks",
            result["summary"]["checks_passed"] == 17
            and result["summary"]["checks_failed"] == 0
            and audit["summary"]["checks_passed"] == 20
            and audit["summary"]["checks_failed"] == 0,
            "17/17 producer and 20/20 independent audit checks.",
        ),
        check(
            "classification",
            result["classification"]
            == "eight_bit_semantic_admission_pass_hardware_execution_unmeasured",
            result["classification"],
        ),
        check(
            "hard_boundaries",
            not result["verdict"]["hardware_decoder_deadline_passed"]
            and not result["verdict"]["full_b2_credit_ready"]
            and not result["verdict"]["p023_scalable_memory_ready"]
            and result["verdict"]["b7_resource_credit"] == 0,
            "No hardware or downstream credit.",
        ),
    ]
    output: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_microblossom_admission_replay_v1",
        "as_of_date": protocol["as_of_date"],
        "scope": protocol["scope"],
        "public_freeze": result["public_freeze"],
        "source_artifacts": {
            "protocol": {
                "path": str(args.protocol.resolve().relative_to(ROOT)),
                "sha256": file_digest(args.protocol),
            },
            "result": {
                "path": str(args.result.resolve().relative_to(ROOT)),
                "sha256": file_digest(args.result),
                "evidence_id": result["evidence_id"],
            },
            "report": {
                "path": str(args.report.resolve().relative_to(ROOT)),
                "sha256": file_digest(args.report),
            },
            "discussion": {
                "path": str(args.discussion.resolve().relative_to(ROOT)),
                "sha256": file_digest(args.discussion),
            },
            "audit": {
                "path": str(args.audit.resolve().relative_to(ROOT)),
                "sha256": file_digest(args.audit),
                "audit_id": audit["audit_id"],
            },
            "producer": {
                "path": str(args.producer.resolve().relative_to(ROOT)),
                "sha256": file_digest(args.producer),
            },
            "auditor": {
                "path": str(args.auditor.resolve().relative_to(ROOT)),
                "sha256": file_digest(args.auditor),
            },
        },
        "replay_environment": {
            "python": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
        },
        "subprocesses": {
            "producer": {
                "returncode": producer.returncode,
                "stdout": producer.stdout,
                "stderr": producer.stderr,
            },
            "auditor": {
                "returncode": auditor.returncode,
                "stdout": auditor.stdout,
                "stderr": auditor.stderr,
            },
        },
        "recreated_sha256": {
            name: digest(value) if value else None
            for name, value in recreated.items()
        },
        "byte_equality": byte_equality,
        "checks": checks,
        "summary": {
            "checks_total": len(checks),
            "checks_passed": sum(item["passed"] for item in checks),
            "checks_failed": sum(not item["passed"] for item in checks),
            "all_artifact_bytes_exact": all(byte_equality.values()),
            "semantic_veto_pass": result["verdict"]["semantic_veto_pass"],
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
                "public_freeze": output["public_freeze"],
                "source_artifacts": output["source_artifacts"],
                "recreated_sha256": output["recreated_sha256"],
                "summary": output["summary"],
            }
        )
    )
    args.replay.parent.mkdir(parents=True, exist_ok=True)
    args.replay.write_text(canonical(output), encoding="utf-8")
    print(
        canonical(
            {
                "replay_id": output["replay_id"],
                "summary": output["summary"],
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
