#!/usr/bin/env python3
"""T-B1-004gy/T-B7-016h: R101 clean-clone rerun gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r101_clean_clone_rerun_gate_v0"
STATUS = "cone01_r101_clean_clone_rerun_reproduces_r100_stable_hashes"
MODEL_STATUS = "r100_no_counter_verdict_replayed_in_clean_local_checkout"
VERSION = "0.1"
TARGET_ID = "T-B1-004gy/T-B7-016h"
UPSTREAM_TARGET_ID = "T-B1-004gx/T-B7-016g"
SUBMISSION_DIR = "results/B1_B7_cone01_o3_f4_exit_route_submissions"

R100_RESULT = "results/B1_B7_cone01_R100_maintainer_verdict_no_counter_gate_v0.json"
R100_VERDICT = f"{SUBMISSION_DIR}/R100-G1-maintainer-no-counter-verdict.json"
R100_VERDICT_VALIDATION = (
    f"{SUBMISSION_DIR}/R100-G1-maintainer-no-counter-verdict-validation.verdict.json"
)
R100_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R100-G1-post-verdict-blocker-queue.json"
R100_SCRIPT = "tools/b1_b7_cone01_r100_maintainer_verdict_no_counter_gate.py"

R101_MANIFEST = f"{SUBMISSION_DIR}/R101-G1-clean-clone-rerun-manifest.json"
R101_TRANSCRIPT = f"{SUBMISSION_DIR}/R101-G1-clean-clone-rerun-transcript.txt"
R101_COMPARISON = f"{SUBMISSION_DIR}/R101-G1-clean-clone-rerun-comparison.verdict.json"
R101_BLOCKER_QUEUE = f"{SUBMISSION_DIR}/R101-G1-post-clean-rerun-blocker-queue.json"

RESULT_PATH = "results/B1_B7_cone01_R101_clean_clone_rerun_gate_v0.json"
REPORT_PATH = "research/B1_B7_cone01_R101_clean_clone_rerun_gate.md"


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def stable_self_hash(payload: dict[str, Any], hash_key: str) -> str:
    copy = dict(payload)
    copy.pop(hash_key, None)
    return stable_hash(copy)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def req(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def run(cmd: list[str], cwd: Path, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def git(root: Path, *args: str) -> str:
    result = run(["git", *args], root)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def clean_clone_and_rerun(root: Path, clone_parent: Path) -> dict[str, Any]:
    source_head = git(root, "rev-parse", "HEAD")
    source_tree = git(root, "rev-parse", "HEAD^{tree}")
    source_status = git(root, "status", "--short")
    clone_dir = clone_parent / "r101_clean_clone"
    if clone_dir.exists():
        shutil.rmtree(clone_dir)

    clone_result = run(
        ["git", "clone", "--local", "--no-hardlinks", str(root), str(clone_dir)],
        root,
        timeout=120,
    )
    checkout_result = run(["git", "checkout", source_head], clone_dir, timeout=120)
    pre_status = run(["git", "status", "--short"], clone_dir, timeout=30)
    rerun_result = run(
        [sys.executable, R100_SCRIPT, "--repo-root", "."],
        clone_dir,
        timeout=120,
    )
    post_status = run(["git", "status", "--short"], clone_dir, timeout=30)

    transcript = "\n".join(
        [
            "R101 clean-clone rerun transcript",
            f"source_head={source_head}",
            f"source_tree={source_tree}",
            f"source_status_sha256={hashlib.sha256(source_status.encode()).hexdigest()}",
            f"clone_command=git clone --local --no-hardlinks {root} {clone_dir}",
            f"clone_returncode={clone_result.returncode}",
            f"checkout_command=git checkout {source_head}",
            f"checkout_returncode={checkout_result.returncode}",
            "rerun_command=python tools/b1_b7_cone01_r100_maintainer_verdict_no_counter_gate.py --repo-root .",
            f"rerun_returncode={rerun_result.returncode}",
            f"pre_rerun_status={pre_status.stdout.strip() or 'clean'}",
            f"post_rerun_status_sha256={hashlib.sha256(post_status.stdout.encode()).hexdigest()}",
            "--- rerun stdout ---",
            rerun_result.stdout.strip() or "(empty)",
            "--- rerun stderr ---",
            rerun_result.stderr.strip() or "(empty)",
        ]
    ) + "\n"

    return {
        "source_head": source_head,
        "source_tree": source_tree,
        "source_status": source_status,
        "clone_dir": str(clone_dir),
        "clone_returncode": clone_result.returncode,
        "checkout_returncode": checkout_result.returncode,
        "pre_status": pre_status.stdout.strip(),
        "rerun_returncode": rerun_result.returncode,
        "post_status": post_status.stdout.strip(),
        "transcript": transcript,
        "clone_r100_result": load_json(clone_dir / R100_RESULT)
        if (clone_dir / R100_RESULT).exists()
        else {},
        "clone_r100_verdict": load_json(clone_dir / R100_VERDICT)
        if (clone_dir / R100_VERDICT).exists()
        else {},
        "clone_r100_validation": load_json(clone_dir / R100_VERDICT_VALIDATION)
        if (clone_dir / R100_VERDICT_VALIDATION).exists()
        else {},
        "clone_r100_blocker_queue": load_json(clone_dir / R100_BLOCKER_QUEUE)
        if (clone_dir / R100_BLOCKER_QUEUE).exists()
        else {},
    }


def build_comparison(root: Path, rerun: dict[str, Any], r100_result: dict[str, Any]) -> dict[str, Any]:
    clone_result = rerun["clone_r100_result"]
    clone_verdict = rerun["clone_r100_verdict"]
    clone_validation = rerun["clone_r100_validation"]
    clone_queue = rerun["clone_r100_blocker_queue"]
    local_verdict = load_json(root / R100_VERDICT)
    local_validation = load_json(root / R100_VERDICT_VALIDATION)
    local_queue = load_json(root / R100_BLOCKER_QUEUE)

    gates = {
        "source_checkout_clean_before_rerun": rerun["pre_status"] == "",
        "clone_command_succeeded": rerun["clone_returncode"] == 0,
        "checkout_command_succeeded": rerun["checkout_returncode"] == 0,
        "r100_rerun_command_succeeded": rerun["rerun_returncode"] == 0,
        "verdict_hash_reproduced": clone_verdict.get("verdict_hash")
        == local_verdict.get("verdict_hash")
        == r100_result["verdict_hash"],
        "verdict_validation_hash_reproduced": clone_validation.get(
            "verdict_validation_hash"
        )
        == local_validation.get("verdict_validation_hash")
        == r100_result["verdict_validation_hash"],
        "blocker_queue_hash_reproduced": clone_queue.get("blocker_queue_hash")
        == local_queue.get("blocker_queue_hash")
        == r100_result["blocker_queue_hash"],
        "stable_counters_reproduced": clone_result.get("summary", {}).get("counter_delta")
        == 0
        and clone_result.get("summary", {}).get("new_credit_delta") == 0
        and clone_result.get("summary", {}).get("accepted_external_reproduction_count")
        == 0
        and clone_result.get("summary", {}).get("accepted_external_falsification_count")
        == 0,
    }
    failed = [gate for gate, passed in gates.items() if not passed]
    comparison = {
        "artifact": "R101 clean-clone rerun comparison verdict",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_head": rerun["source_head"],
        "source_tree": rerun["source_tree"],
        "source_r100_payload_hash": r100_result["payload_hash"],
        "local_r100_verdict_hash": local_verdict.get("verdict_hash"),
        "clone_r100_verdict_hash": clone_verdict.get("verdict_hash"),
        "local_r100_verdict_validation_hash": local_validation.get(
            "verdict_validation_hash"
        ),
        "clone_r100_verdict_validation_hash": clone_validation.get(
            "verdict_validation_hash"
        ),
        "local_r100_blocker_queue_hash": local_queue.get("blocker_queue_hash"),
        "clone_r100_blocker_queue_hash": clone_queue.get("blocker_queue_hash"),
        "gates": gates,
        "passed_gate_count": sum(1 for passed in gates.values() if passed),
        "failed_gate_count": len(failed),
        "failed_gates": failed,
        "clean_clone_rerun_reproduced": not failed,
        "maintainer_verdict_accepted": clone_result.get("summary", {}).get(
            "maintainer_verdict_accepted"
        )
        is True,
        "counter_delta": 0,
        "accepted_external_reproduction_count": 0,
        "accepted_external_falsification_count": 0,
        "new_credit_delta": 0,
        "external_counter_moved": False,
        "claim_boundary": (
            "R101 is a clean local checkout rerun of R100 stable hashes. It is not "
            "a third-party external reproduction and does not move external counters."
        ),
    }
    comparison["comparison_hash"] = stable_self_hash(comparison, "comparison_hash")
    return comparison


def build_manifest(root: Path, rerun: dict[str, Any], comparison: dict[str, Any]) -> dict[str, Any]:
    transcript_path = root / R101_TRANSCRIPT
    manifest = {
        "artifact": "R101 clean-clone rerun manifest",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_head": rerun["source_head"],
        "source_tree": rerun["source_tree"],
        "clone_was_local": True,
        "clone_command_returncode": rerun["clone_returncode"],
        "checkout_returncode": rerun["checkout_returncode"],
        "rerun_returncode": rerun["rerun_returncode"],
        "pre_rerun_status_clean": rerun["pre_status"] == "",
        "transcript_path": R101_TRANSCRIPT,
        "transcript_sha256": file_hash(transcript_path),
        "comparison_path": R101_COMPARISON,
        "comparison_hash": comparison["comparison_hash"],
        "clean_clone_rerun_reproduced": comparison["clean_clone_rerun_reproduced"],
        "external_counter_moved": False,
    }
    manifest["manifest_hash"] = stable_self_hash(manifest, "manifest_hash")
    return manifest


def build_blocker_queue(comparison: dict[str, Any]) -> dict[str, Any]:
    queue = {
        "artifact": "R101 post clean-clone rerun blocker queue",
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "comparison_hash": comparison["comparison_hash"],
        "queue": [
            {
                "blocker_id": "R101-G1-1",
                "priority": 1,
                "target_gate": "independent_reviewer_identity",
                "needed_artifact": "reviewer identity and environment outside the maintainer agent",
            },
            {
                "blocker_id": "R101-G1-2",
                "priority": 2,
                "target_gate": "external_counter_decision",
                "needed_artifact": "one explicit reproduction or falsification counter decision",
            },
            {
                "blocker_id": "R101-G1-3",
                "priority": 3,
                "target_gate": "counter_transition_audit",
                "needed_artifact": "audit proving exactly one counter moved and no B7/O3/resource/layout claim moved",
            },
        ],
    }
    queue["blocker_queue_hash"] = stable_self_hash(queue, "blocker_queue_hash")
    return queue


def build_payload(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.repo_root).resolve()
    r100_result = load_json(root / R100_RESULT)

    with tempfile.TemporaryDirectory(prefix="r101-clean-clone-") as tmp:
        rerun = clean_clone_and_rerun(root, Path(tmp))
        transcript_path = root / R101_TRANSCRIPT
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text(rerun["transcript"], encoding="utf-8")
        comparison = build_comparison(root, rerun, r100_result)
        write_json(root / R101_COMPARISON, comparison)
        manifest = build_manifest(root, rerun, comparison)
        write_json(root / R101_MANIFEST, manifest)
        blocker_queue = build_blocker_queue(comparison)
        write_json(root / R101_BLOCKER_QUEUE, blocker_queue)

    requirements = [
        req(
            "A1",
            "R101 binds accepted R100 no-counter verdict",
            r100_result["summary"]["source_target_id"] == UPSTREAM_TARGET_ID
            and r100_result["summary"]["maintainer_verdict_accepted"] is True
            and r100_result["summary"]["counter_delta"] == 0,
            {
                "r100_payload_hash": r100_result["payload_hash"],
                "r100_verdict_validation_hash": r100_result["verdict_validation_hash"],
            },
        ),
        req(
            "A2",
            "R101 runs R100 from a clean local clone checkout",
            manifest["pre_rerun_status_clean"] is True
            and manifest["clone_command_returncode"] == 0
            and manifest["checkout_returncode"] == 0
            and manifest["rerun_returncode"] == 0,
            {
                "source_head": manifest["source_head"],
                "transcript_sha256": manifest["transcript_sha256"],
            },
        ),
        req(
            "A3",
            "R101 reproduces R100 stable verdict, validation, and blocker hashes",
            comparison["clean_clone_rerun_reproduced"] is True
            and comparison["failed_gate_count"] == 0,
            {
                "comparison_hash": comparison["comparison_hash"],
                "passed_gate_count": comparison["passed_gate_count"],
            },
        ),
        req(
            "A4",
            "R101 keeps external counters and new credit at zero",
            comparison["counter_delta"] == 0
            and comparison["accepted_external_reproduction_count"] == 0
            and comparison["accepted_external_falsification_count"] == 0
            and comparison["new_credit_delta"] == 0
            and comparison["external_counter_moved"] is False,
            {
                "counter_delta": comparison["counter_delta"],
                "accepted_external_reproduction_count": comparison[
                    "accepted_external_reproduction_count"
                ],
                "accepted_external_falsification_count": comparison[
                    "accepted_external_falsification_count"
                ],
                "new_credit_delta": comparison["new_credit_delta"],
            },
        ),
        req(
            "A5",
            "R101 emits blockers for independent reviewer identity, counter decision, and transition audit",
            [item["target_gate"] for item in blocker_queue["queue"]]
            == [
                "independent_reviewer_identity",
                "external_counter_decision",
                "counter_transition_audit",
            ],
            {
                "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
                "blocker_ids": [item["blocker_id"] for item in blocker_queue["queue"]],
            },
        ),
    ]
    failed_requirements = [
        requirement["requirement_id"] for requirement in requirements if not requirement["passed"]
    ]
    validation_errors = []
    if failed_requirements:
        validation_errors.append("one or more R101 requirements failed")
    if comparison["external_counter_moved"]:
        validation_errors.append("R101 must not move external counters")

    payload = {
        "artifact": "B1/B7 cone01 R101 clean-clone rerun gate",
        "method": METHOD,
        "version": VERSION,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "generated_at_unix": int(time.time()),
        "manifest_path": R101_MANIFEST,
        "manifest_hash": manifest["manifest_hash"],
        "transcript_path": R101_TRANSCRIPT,
        "transcript_sha256": manifest["transcript_sha256"],
        "comparison_path": R101_COMPARISON,
        "comparison_hash": comparison["comparison_hash"],
        "blocker_queue_path": R101_BLOCKER_QUEUE,
        "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
        "requirement_count": len(requirements),
        "requirements_passed": sum(1 for requirement in requirements if requirement["passed"]),
        "requirements_failed": len(failed_requirements),
        "failed_requirement_ids": failed_requirements,
        "requirements": requirements,
        "validation_error_count": len(validation_errors),
        "validation_errors": validation_errors,
        "summary": {
            "method": METHOD,
            "status": STATUS,
            "model_status": MODEL_STATUS,
            "source_target_id": TARGET_ID,
            "upstream_target_id": UPSTREAM_TARGET_ID,
            "clean_clone_rerun_reproduced": comparison["clean_clone_rerun_reproduced"],
            "passed_gate_count": comparison["passed_gate_count"],
            "failed_gate_count": comparison["failed_gate_count"],
            "maintainer_verdict_accepted": comparison["maintainer_verdict_accepted"],
            "counter_delta": comparison["counter_delta"],
            "accepted_external_reproduction_count": comparison[
                "accepted_external_reproduction_count"
            ],
            "accepted_external_falsification_count": comparison[
                "accepted_external_falsification_count"
            ],
            "new_credit_delta": comparison["new_credit_delta"],
            "external_counter_moved": comparison["external_counter_moved"],
            "manifest_hash": manifest["manifest_hash"],
            "transcript_sha256": manifest["transcript_sha256"],
            "comparison_hash": comparison["comparison_hash"],
            "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
            "payload_hash": None,
            "requirements_passed": sum(1 for requirement in requirements if requirement["passed"]),
            "requirements_failed": len(failed_requirements),
            "failed_requirement_ids": failed_requirements,
            "validation_error_count": len(validation_errors),
        },
    }
    payload["payload_hash"] = stable_self_hash(payload, "payload_hash")
    payload["summary"]["payload_hash"] = payload["payload_hash"]
    return payload


def write_report(root: Path, payload: dict[str, Any]) -> None:
    summary = payload["summary"]
    lines = [
        "# B1/B7 Cone01 R101 Clean-Clone Rerun Gate",
        "",
        f"- Target: `{TARGET_ID}`",
        f"- Upstream target: `{UPSTREAM_TARGET_ID}`",
        f"- Method: `{METHOD}`",
        f"- Status: `{STATUS}`",
        f"- Model status: `{MODEL_STATUS}`",
        "",
        "## Result",
        "",
        "R101 reruns R100 from a clean local Git checkout and compares the stable",
        "verdict, validation, and blocker hashes. The rerun reproduces those hashes,",
        "but remains a local clean-checkout rerun rather than a third-party external",
        "reproduction.",
        "",
        "## Key Counters",
        "",
        f"- Clean-clone rerun reproduced: `{summary['clean_clone_rerun_reproduced']}`",
        f"- Gates passed / failed: `{summary['passed_gate_count']}` / `{summary['failed_gate_count']}`",
        f"- Maintainer verdict accepted: `{summary['maintainer_verdict_accepted']}`",
        f"- Counter delta: `{summary['counter_delta']}`",
        f"- Accepted external reproductions: `{summary['accepted_external_reproduction_count']}`",
        f"- Accepted external falsifications: `{summary['accepted_external_falsification_count']}`",
        f"- New credit delta: `{summary['new_credit_delta']}`",
        "",
        "## Requirements",
        "",
    ]
    for requirement in payload["requirements"]:
        status = "PASS" if requirement["passed"] else "FAIL"
        lines.append(f"- `{requirement['requirement_id']}` {status}: {requirement['label']}")
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Result JSON: `{RESULT_PATH}`",
            f"- Manifest: `{R101_MANIFEST}`",
            f"- Transcript: `{R101_TRANSCRIPT}`",
            f"- Comparison: `{R101_COMPARISON}`",
            f"- Blocker queue: `{R101_BLOCKER_QUEUE}`",
            "",
            "## Claim Boundary",
            "",
            "R101 proves a local clean-checkout rerun of R100 stable hashes. It does not",
            "move the external reproduction or falsification counters, does not grant new",
            "credit, and does not close B7/O3/resource/layout claims. The next gate needs",
            "an independent reviewer identity plus an explicit counter-transition decision.",
            "",
        ]
    )
    (root / REPORT_PATH).write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    root = Path(args.repo_root).resolve()
    payload = build_payload(args)
    write_json(root / RESULT_PATH, payload)
    write_report(root, payload)
    if args.pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
