#!/usr/bin/env python3
"""T-B1-004hh/T-B7-016q: R110 live public dereference probe gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any


METHOD = "b1_b7_cone01_r110_live_public_dereference_probe_gate_v0"
STATUS = "cone01_r110_live_public_dereference_probe_rejected_not_nonce_bound"
MODEL_STATUS = "r109_public_urls_live_probed_but_not_accepted_as_material_evidence"
TARGET_ID = "T-B1-004hh/T-B7-016q"
UPSTREAM_TARGET_ID = "T-B1-004hg/T-B7-016p"
VERSION = "0.1"

CONTRACT_PATH = (
    "results/B1_B7_cone01_o3_f4_exit_route_submissions/"
    "R109-G1-public-artifact-dereference-contract/"
    "public-artifact-dereference-contract.json"
)
URL_ONLY_PATH = (
    "results/B1_B7_cone01_o3_f4_exit_route_submissions/"
    "R109-G1-public-artifact-dereference-contract/"
    "url-only-public-artifact-negative-control.json"
)
OUT_DIR = (
    "results/B1_B7_cone01_o3_f4_exit_route_submissions/"
    "R110-G1-live-public-dereference-probe"
)
RESULT_PATH = "results/B1_B7_cone01_R110_live_public_dereference_probe_gate_v0.json"
REPORT_PATH = "research/B1_B7_cone01_R110_live_public_dereference_probe_gate.md"
STDOUT_PATH = f"{OUT_DIR}/R110-live-public-dereference-probe.stdout.txt"
VERDICT_PATH = f"{OUT_DIR}/live-public-dereference-probe.verdict.json"
BLOCKER_QUEUE_PATH = f"{OUT_DIR}/post-live-public-dereference-probe-blocker-queue.json"


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_public_url(role: str, url: str, nonce: str, timeout: float) -> dict[str, Any]:
    started = time.time()
    transcript: dict[str, Any] = {
        "role": role,
        "url": url,
        "attempted_at_unix": int(started),
        "timeout_seconds": timeout,
        "auth_used": False,
        "live_public_fetch_attempted": True,
        "live_public_fetch_completed": False,
        "status_code": None,
        "final_url": None,
        "response_header_keys": [],
        "body_prefix_sha256": None,
        "body_prefix_text": "",
        "body_prefix_byte_count": 0,
        "contains_challenge_nonce": False,
        "requested_url_bound": False,
        "error_type": None,
        "error": None,
        "elapsed_ms": None,
    }
    marker_code = "__R110_HTTP_CODE:"
    marker_final = "__R110_FINAL_URL:"
    try:
        completed = subprocess.run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--location",
                "--max-time",
                str(int(timeout)),
                "--user-agent",
                "Prometheus-plan-R110-public-dereference-probe/0.1",
                "--write-out",
                f"\n{marker_code}%{{http_code}}\n{marker_final}%{{url_effective}}\n",
                url,
            ],
            check=False,
            capture_output=True,
            text=False,
            timeout=timeout + 5,
        )
        combined = completed.stdout + completed.stderr
        text = combined.decode("utf-8", errors="replace")
        status_code = None
        final_url = None
        body_text = text
        if marker_code in text:
            body_text, rest = text.split(marker_code, 1)
            status_line = rest.splitlines()[0].strip()
            if status_line.isdigit():
                status_code = int(status_line)
        if marker_final in text:
            final_url = text.split(marker_final, 1)[1].splitlines()[0].strip()
        body_bytes = body_text.encode("utf-8", errors="replace")[:8192]
        transcript.update(
            {
                "curl_returncode": completed.returncode,
                "live_public_fetch_completed": completed.returncode == 0 and status_code is not None,
                "status_code": status_code,
                "final_url": final_url,
                "body_prefix_sha256": hashlib.sha256(body_bytes).hexdigest(),
                "body_prefix_text": body_text[:500],
                "body_prefix_byte_count": len(body_bytes),
                "contains_challenge_nonce": nonce in body_text,
                "requested_url_bound": bool(final_url and final_url.startswith(url)),
            }
        )
        if completed.returncode != 0:
            transcript["error_type"] = "CurlError"
            transcript["error"] = text[-500:]
    except subprocess.TimeoutExpired as exc:
        transcript.update({"error_type": type(exc).__name__, "error": str(exc)})
    finally:
        transcript["elapsed_ms"] = round((time.time() - started) * 1000, 3)
    transcript["transcript_hash"] = stable_hash(transcript)
    return transcript


def build_report(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    return f"""# B1/B7 Cone01 R110 Live Public Dereference Probe Gate

## Summary

- Target: `{payload["source_target_id"]}`
- Upstream target: `{payload["upstream_target_id"]}`
- Method: `{payload["method"]}`
- Status: `{payload["status"]}`
- Requirements: `{payload["requirements_passed"]}/{payload["requirement_count"]}`
- Public fetch attempts: `{s["fetch_attempt_count"]}`
- Completed public fetches: `{s["completed_fetch_count"]}`
- HTTP 2xx fetches: `{s["http_2xx_fetch_count"]}`
- Nonce-bound transcripts: `{s["nonce_bound_transcript_count"]}`
- Requested-url-bound transcripts: `{s["requested_url_bound_count"]}`
- Dereference packet accepted: `{s["dereference_packet_accepted"]}`
- Counter transition accepted: `{s["counter_transition_accepted"]}`
- Counter delta: `{s["counter_delta"]}`
- New credit delta: `{s["new_credit_delta"]}`

R110 probes the public-looking URLs from the R109 URL-only negative control with
unauthenticated HTTP GET requests. The probe records live transcripts, but does
not accept them as material evidence because the required transcript set is not
both HTTP-successful and challenge-nonce-bound.

## Requirements

""" + "\n".join(
        f"- `{r['requirement_id']}` {'PASS' if r['passed'] else 'FAIL'}: {r['label']}"
        for r in payload["requirements"]
    ) + f"""

## Artifacts

- Result JSON: `{RESULT_PATH}`
- Probe verdict: `{VERDICT_PATH}`
- Blocker queue: `{BLOCKER_QUEUE_PATH}`
- Stdout: `{STDOUT_PATH}`

## Claim Boundary

R110 is a live public dereference probe only. It does not accept an external
reproduction, does not move any counter, and does not grant B7/O3/resource or
layout credit.
"""


def run(repo_root: Path, timeout: float) -> dict[str, Any]:
    root = repo_root.resolve()
    contract = json.loads((root / CONTRACT_PATH).read_text(encoding="utf-8"))
    url_packet = json.loads((root / URL_ONLY_PATH).read_text(encoding="utf-8"))
    fields = url_packet["fields"]
    nonce = fields["challenge_nonce"]
    roles = {
        "reviewer_key": fields["reviewer_key_url"],
        "ci_run": fields["ci_run_url"],
        "artifact": fields["artifact_url"],
    }
    transcripts: dict[str, dict[str, Any]] = {}
    out_dir = root / OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    transcript_paths: dict[str, str] = {}
    for role, url in roles.items():
        transcript = fetch_public_url(role, url, nonce, timeout)
        path = out_dir / f"{role}.live-http-transcript.json"
        write_json(path, transcript)
        transcripts[role] = transcript
        transcript_paths[role] = str(path.relative_to(root))

    http_2xx = [
        role
        for role, t in transcripts.items()
        if isinstance(t.get("status_code"), int) and 200 <= t["status_code"] < 300
    ]
    nonce_bound = [role for role, t in transcripts.items() if t["contains_challenge_nonce"]]
    requested_bound = [role for role, t in transcripts.items() if t["requested_url_bound"]]
    completed = [role for role, t in transcripts.items() if t["live_public_fetch_completed"]]
    accepted = (
        len(completed) == 3
        and len(http_2xx) == 3
        and len(nonce_bound) == 3
        and len(requested_bound) == 3
    )
    verdict = {
        "artifact": "R110 live public dereference probe verdict",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "method": METHOD,
        "source_contract_hash": contract["contract_hash"],
        "source_url_only_packet_hash": url_packet["url_only_packet_hash"],
        "challenge_nonce": nonce,
        "transcript_paths": transcript_paths,
        "fetch_attempt_count": len(transcripts),
        "completed_fetch_roles": completed,
        "http_2xx_roles": http_2xx,
        "nonce_bound_roles": nonce_bound,
        "requested_url_bound_roles": requested_bound,
        "dereference_packet_accepted": accepted,
        "counter_transition_accepted": False,
        "counter_delta": 0,
        "accepted_external_reproduction_count": 0,
        "accepted_external_falsification_count": 0,
        "new_credit_delta": 0,
    }
    verdict["verdict_hash"] = stable_hash(verdict)
    write_json(root / VERDICT_PATH, verdict)
    blocker_queue = {
        "artifact": "R110 post-probe blocker queue",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "blockers": [
            {
                "blocker_id": "R110-B1",
                "priority": 1,
                "needed_artifact": "public reviewer key URL returning a live HTTP 2xx transcript bound to the R109 challenge nonce",
            },
            {
                "blocker_id": "R110-B2",
                "priority": 2,
                "needed_artifact": "public CI run URL returning a live HTTP 2xx transcript bound to the R109 challenge nonce",
            },
            {
                "blocker_id": "R110-B3",
                "priority": 3,
                "needed_artifact": "public artifact URL returning a live HTTP 2xx transcript bound to the R109 challenge nonce",
            },
            {
                "blocker_id": "R110-B4",
                "priority": 4,
                "needed_artifact": "rerun R109 and R108 after all transcripts are live, public, requested-url-bound, and nonce-bound",
            },
        ],
        "counter_transition_accepted": False,
        "counter_delta": 0,
        "new_credit_delta": 0,
    }
    blocker_queue["blocker_queue_hash"] = stable_hash(blocker_queue)
    write_json(root / BLOCKER_QUEUE_PATH, blocker_queue)
    requirements = [
        {
            "requirement_id": "P1",
            "label": "R110 binds the R109 contract and URL-only negative control",
            "passed": contract["contract_hash"] == url_packet["contract_hash"],
            "evidence": {
                "contract_hash": contract["contract_hash"],
                "url_only_packet_hash": url_packet["url_only_packet_hash"],
            },
        },
        {
            "requirement_id": "P2",
            "label": "R110 attempts unauthenticated live public HTTP fetches for all required URL roles",
            "passed": len(transcripts) == 3 and all(t["live_public_fetch_attempted"] for t in transcripts.values()),
            "evidence": {"roles": sorted(transcripts)},
        },
        {
            "requirement_id": "P3",
            "label": "R110 records hash-bound transcript files",
            "passed": all((root / p).exists() for p in transcript_paths.values()),
            "evidence": transcript_paths,
        },
        {
            "requirement_id": "P4",
            "label": "R110 refuses to accept transcripts unless all are HTTP 2xx and nonce-bound",
            "passed": not accepted,
            "evidence": {
                "http_2xx_roles": http_2xx,
                "nonce_bound_roles": nonce_bound,
                "requested_url_bound_roles": requested_bound,
            },
        },
        {
            "requirement_id": "P5",
            "label": "R110 keeps external counters and new credit at zero",
            "passed": verdict["counter_delta"] == 0 and verdict["new_credit_delta"] == 0,
            "evidence": {
                "counter_delta": verdict["counter_delta"],
                "new_credit_delta": verdict["new_credit_delta"],
            },
        },
        {
            "requirement_id": "P6",
            "label": "R110 emits a next-blocker queue for live nonce-bound public transcripts",
            "passed": len(blocker_queue["blockers"]) == 4,
            "evidence": {"blocker_queue_hash": blocker_queue["blocker_queue_hash"]},
        },
    ]
    failed = [r["requirement_id"] for r in requirements if not r["passed"]]
    summary = {
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "fetch_attempt_count": len(transcripts),
        "completed_fetch_count": len(completed),
        "http_2xx_fetch_count": len(http_2xx),
        "nonce_bound_transcript_count": len(nonce_bound),
        "requested_url_bound_count": len(requested_bound),
        "dereference_packet_accepted": accepted,
        "counter_transition_accepted": False,
        "counter_delta": 0,
        "accepted_external_reproduction_count": 0,
        "accepted_external_falsification_count": 0,
        "new_credit_delta": 0,
        "verdict_hash": verdict["verdict_hash"],
        "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
        "requirements_passed": sum(1 for r in requirements if r["passed"]),
        "requirements_failed": len(failed),
        "failed_requirement_ids": failed,
        "validation_error_count": 0,
    }
    payload = {
        "title": "B1/B7 cone01 R110 live public dereference probe gate",
        "version": VERSION,
        "generated_at_unix": int(time.time()),
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "requirement_count": len(requirements),
        "requirements_passed": summary["requirements_passed"],
        "requirements_failed": summary["requirements_failed"],
        "requirements": requirements,
        "summary": summary,
        "artifacts": {
            "verdict": VERDICT_PATH,
            "blocker_queue": BLOCKER_QUEUE_PATH,
            "stdout": STDOUT_PATH,
            **{f"{role}_transcript": path for role, path in transcript_paths.items()},
        },
        "claim_boundary": {
            "what_is_supported": "R110 attempted unauthenticated public dereference of the R109 URL-only negative-control URLs and wrote hash-bound transcripts.",
            "what_is_not_supported": "R110 does not accept the packet as live nonce-bound material evidence and does not move any counter or B7 credit.",
            "next_gate": "Provide real public HTTP 2xx transcripts for reviewer key, CI run, and artifact URLs that bind the R109 challenge nonce and requested URLs, then rerun R109/R108.",
        },
    }
    payload["payload_hash"] = stable_hash(payload)
    summary["payload_hash"] = payload["payload_hash"]
    write_json(root / RESULT_PATH, payload)
    (root / REPORT_PATH).parent.mkdir(parents=True, exist_ok=True)
    (root / REPORT_PATH).write_text(build_report(payload), encoding="utf-8")
    stdout = {
        "method": METHOD,
        "source_target_id": TARGET_ID,
        "requirements_passed": payload["requirements_passed"],
        "requirements_failed": payload["requirements_failed"],
        "dereference_packet_accepted": accepted,
        "counter_delta": 0,
        "new_credit_delta": 0,
        "payload_hash": payload["payload_hash"],
    }
    stdout_path = root / STDOUT_PATH
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.write_text(json.dumps(stdout, sort_keys=True) + "\n", encoding="utf-8")
    payload["artifacts"]["stdout_sha256"] = file_hash(stdout_path)
    payload["summary"]["stdout_sha256"] = payload["artifacts"]["stdout_sha256"]
    write_json(root / RESULT_PATH, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--timeout", type=float, default=15.0, help="Per-URL timeout")
    args = parser.parse_args()
    payload = run(Path(args.repo_root), args.timeout)
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
