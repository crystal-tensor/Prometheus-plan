#!/usr/bin/env python3
"""T-B1-004hi/T-B7-016r: R111 independent-origin materiality gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse
from typing import Any


METHOD = "b1_b7_cone01_r111_independent_origin_materiality_gate_v0"
STATUS = "cone01_r111_public_fetch_passed_independent_origin_rejected"
MODEL_STATUS = "public_fetchability_is_not_independent_materiality"
TARGET_ID = "T-B1-004hi/T-B7-016r"
UPSTREAM_TARGET_ID = "T-B1-004hh/T-B7-016q"
VERSION = "0.1"

CONTRACT_PATH = (
    "results/B1_B7_cone01_o3_f4_exit_route_submissions/"
    "R109-G1-public-artifact-dereference-contract/"
    "public-artifact-dereference-contract.json"
)
MANIFEST_PATH = (
    "results/B1_B7_cone01_o3_f4_exit_route_submissions/"
    "R111-G1-independent-origin-materiality/"
    "r111-public-materiality-negative-control.json"
)
OUT_DIR = (
    "results/B1_B7_cone01_o3_f4_exit_route_submissions/"
    "R111-G1-independent-origin-materiality"
)
RESULT_PATH = "results/B1_B7_cone01_R111_independent_origin_materiality_gate_v0.json"
REPORT_PATH = "research/B1_B7_cone01_R111_independent_origin_materiality_gate.md"
VERDICT_PATH = f"{OUT_DIR}/independent-origin-materiality.verdict.json"
BLOCKER_QUEUE_PATH = f"{OUT_DIR}/post-independent-origin-materiality-blocker-queue.json"
STDOUT_PATH = f"{OUT_DIR}/R111-independent-origin-materiality.stdout.txt"


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch(role: str, url: str, nonce: str, timeout: float) -> dict[str, Any]:
    started = time.time()
    marker_code = "__R111_HTTP_CODE:"
    marker_final = "__R111_FINAL_URL:"
    transcript: dict[str, Any] = {
        "role": role,
        "url": url,
        "auth_used": False,
        "live_public_fetch_attempted": True,
        "live_public_fetch_completed": False,
        "status_code": None,
        "final_url": None,
        "body_prefix_text": "",
        "body_prefix_sha256": None,
        "contains_challenge_nonce": False,
        "requested_url_bound": False,
        "elapsed_ms": None,
        "error_type": None,
        "error": None,
    }
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
                "Prometheus-plan-R111-independent-origin-materiality/0.1",
                "--write-out",
                f"\n{marker_code}%{{http_code}}\n{marker_final}%{{url_effective}}\n",
                url,
            ],
            capture_output=True,
            check=False,
            timeout=timeout + 5,
        )
        text = (completed.stdout + completed.stderr).decode("utf-8", errors="replace")
        body = text
        status_code = None
        final_url = None
        if marker_code in text:
            body, rest = text.split(marker_code, 1)
            status_line = rest.splitlines()[0].strip()
            if status_line.isdigit():
                status_code = int(status_line)
        if marker_final in text:
            final_url = text.split(marker_final, 1)[1].splitlines()[0].strip()
        prefix = body.encode("utf-8", errors="replace")[:8192]
        transcript.update(
            {
                "curl_returncode": completed.returncode,
                "live_public_fetch_completed": completed.returncode == 0 and status_code is not None,
                "status_code": status_code,
                "final_url": final_url,
                "body_prefix_text": body[:500],
                "body_prefix_sha256": hashlib.sha256(prefix).hexdigest(),
                "contains_challenge_nonce": nonce in body,
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


def report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    rows = "\n".join(
        f"- `{item['requirement_id']}` {'PASS' if item['passed'] else 'FAIL'}: {item['label']}"
        for item in payload["requirements"]
    )
    return f"""# B1/B7 Cone01 R111 Independent-Origin Materiality Gate

## Summary

- Target: `{TARGET_ID}`
- Upstream target: `{UPSTREAM_TARGET_ID}`
- Method: `{METHOD}`
- Status: `{STATUS}`
- Model status: `{MODEL_STATUS}`
- Requirements: `{payload['requirements_passed']}/{payload['requirement_count']}`
- Live public fetches: `{summary['live_public_fetch_count']}`
- HTTP 2xx fetches: `{summary['http_2xx_fetch_count']}`
- Nonce-bound transcripts: `{summary['nonce_bound_transcript_count']}`
- Requested-url-bound transcripts: `{summary['requested_url_bound_count']}`
- Same-repository origins: `{summary['same_repository_origin_count']}`
- Materiality accepted: `{summary['materiality_accepted']}`
- Counter delta: `{summary['counter_delta']}`

R111 performs a real unauthenticated dereference against public files that are
reachable and nonce-bearing. It then rejects them as material external evidence
because the origin is the same repository and the fixtures are self-attested or
synthetic. A live `2xx` response is therefore necessary but not sufficient.

## Requirements

{rows}

## Claim Boundary

R111 supports a stronger negative result: public fetchability does not establish
independent materiality. It does not accept an external reproduction, move a
counter, or grant B7/O3/resource/layout credit.

## Artifacts

- Result JSON: `{RESULT_PATH}`
- Verdict: `{VERDICT_PATH}`
- Blocker queue: `{BLOCKER_QUEUE_PATH}`
- Stdout: `{STDOUT_PATH}`
"""


def run(root: Path, timeout: float) -> dict[str, Any]:
    root = root.resolve()
    contract = json.loads((root / CONTRACT_PATH).read_text(encoding="utf-8"))
    manifest = json.loads((root / MANIFEST_PATH).read_text(encoding="utf-8"))
    nonce = manifest["challenge_nonce"]
    repository_owner = manifest["repository_owner"]
    repository_name = manifest["repository_name"]
    transcripts: dict[str, dict[str, Any]] = {}
    transcript_paths: dict[str, str] = {}
    for role, url in manifest["urls"].items():
        transcript = fetch(role, url, nonce, timeout)
        path = root / OUT_DIR / f"{role}.live-http-transcript.json"
        write_json(path, transcript)
        transcripts[role] = transcript
        transcript_paths[role] = str(path.relative_to(root))

    http_2xx = [
        role
        for role, item in transcripts.items()
        if isinstance(item.get("status_code"), int) and 200 <= item["status_code"] < 300
    ]
    live = [role for role, item in transcripts.items() if item["live_public_fetch_completed"]]
    nonce_bound = [role for role, item in transcripts.items() if item["contains_challenge_nonce"]]
    requested_bound = [role for role, item in transcripts.items() if item["requested_url_bound"]]
    same_repository = []
    external_origin = []
    for role, url in manifest["urls"].items():
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        same = parsed.netloc == "raw.githubusercontent.com" and len(parts) >= 2 and parts[0] == repository_owner and parts[1] == repository_name
        (same_repository if same else external_origin).append(role)
    synthetic_markers = [
        marker
        for marker in manifest["synthetic_markers"]
        if any(marker in item["body_prefix_text"] for item in transcripts.values())
    ]
    all_public_fields = (
        len(live) == 3
        and len(http_2xx) == 3
        and len(nonce_bound) == 3
        and len(requested_bound) == 3
    )
    materiality_accepted = (
        all_public_fields
        and not same_repository
        and not synthetic_markers
        and manifest["reviewer_independent"]
        and manifest["external_origin_attested"]
    )
    blockers = []
    if same_repository:
        blockers.append("all public URLs resolve to the project repository rather than an independent origin")
    if synthetic_markers:
        blockers.append("public bodies retain synthetic or negative-control markers")
    if not manifest["reviewer_independent"]:
        blockers.append("reviewer independence is not externally attested")
    if not manifest["external_origin_attested"]:
        blockers.append("external-origin attestation is absent")
    verdict = {
        "artifact": "R111 independent-origin materiality verdict",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "method": METHOD,
        "source_contract_hash": contract["contract_hash"],
        "immutable_commit_sha": manifest["immutable_commit_sha"],
        "transcript_paths": transcript_paths,
        "live_public_fetch_roles": live,
        "http_2xx_roles": http_2xx,
        "nonce_bound_roles": nonce_bound,
        "requested_url_bound_roles": requested_bound,
        "same_repository_origin_roles": same_repository,
        "external_origin_roles": external_origin,
        "synthetic_markers": synthetic_markers,
        "materiality_accepted": materiality_accepted,
        "counter_transition_accepted": False,
        "counter_delta": 0,
        "new_credit_delta": 0,
    }
    verdict["verdict_hash"] = stable_hash(verdict)
    write_json(root / VERDICT_PATH, verdict)
    blocker_queue = {
        "artifact": "R111 post-independent-origin-materiality blocker queue",
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "blockers": [
            {"blocker_id": "R111-B1", "priority": 1, "needed_artifact": "independent reviewer identity and public key outside the project repository"},
            {"blocker_id": "R111-B2", "priority": 2, "needed_artifact": "third-party CI run or attested execution service outside the project repository"},
            {"blocker_id": "R111-B3", "priority": 3, "needed_artifact": "artifact host and transcript with external-origin attestation"},
            {"blocker_id": "R111-B4", "priority": 4, "needed_artifact": "rerun R109/R110 and the single-counter audit after all three independent sources are live"},
        ],
        "observed_blockers": blockers,
        "counter_transition_accepted": False,
        "counter_delta": 0,
        "new_credit_delta": 0,
    }
    blocker_queue["blocker_queue_hash"] = stable_hash(blocker_queue)
    write_json(root / BLOCKER_QUEUE_PATH, blocker_queue)
    requirements = [
        {"requirement_id": "P1", "label": "R111 binds the R109 contract and immutable source commit", "passed": contract["contract_hash"] == manifest["source_contract_hash"] and len(manifest["immutable_commit_sha"]) == 40, "evidence": {"contract_hash": contract["contract_hash"], "source_contract_hash": manifest["source_contract_hash"], "immutable_commit_sha": manifest["immutable_commit_sha"]}},
        {"requirement_id": "P2", "label": "R111 attempts unauthenticated public fetches for all three roles", "passed": len(transcripts) == 3 and all(item["live_public_fetch_attempted"] for item in transcripts.values()), "evidence": {"roles": sorted(transcripts)}},
        {"requirement_id": "P3", "label": "R111 records live HTTP 2xx nonce-bound requested-url-bound transcripts", "passed": all_public_fields, "evidence": {"live": live, "http_2xx": http_2xx, "nonce_bound": nonce_bound, "requested_url_bound": requested_bound}},
        {"requirement_id": "P4", "label": "R111 identifies same-repository public origins", "passed": len(same_repository) == 3 and not external_origin, "evidence": {"same_repository": same_repository, "external_origin": external_origin}},
        {"requirement_id": "P5", "label": "R111 rejects self-attested or synthetic public materiality", "passed": not materiality_accepted and len(blockers) >= 2, "evidence": {"synthetic_markers": synthetic_markers, "blockers": blockers}},
        {"requirement_id": "P6", "label": "R111 keeps counters and new credit at zero", "passed": verdict["counter_delta"] == 0 and verdict["new_credit_delta"] == 0, "evidence": {"counter_delta": 0, "new_credit_delta": 0}},
        {"requirement_id": "P7", "label": "R111 emits a four-item independent-origin blocker queue", "passed": len(blocker_queue["blockers"]) == 4, "evidence": {"blocker_queue_hash": blocker_queue["blocker_queue_hash"]}},
        {"requirement_id": "P8", "label": "R111 states the public-fetchability claim boundary", "passed": True, "evidence": {"model_status": MODEL_STATUS}},
    ]
    failed = [item["requirement_id"] for item in requirements if not item["passed"]]
    summary = {
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "fetch_attempt_count": len(transcripts),
        "live_public_fetch_count": len(live),
        "http_2xx_fetch_count": len(http_2xx),
        "nonce_bound_transcript_count": len(nonce_bound),
        "requested_url_bound_count": len(requested_bound),
        "same_repository_origin_count": len(same_repository),
        "materiality_accepted": materiality_accepted,
        "counter_transition_accepted": False,
        "counter_delta": 0,
        "new_credit_delta": 0,
        "verdict_hash": verdict["verdict_hash"],
        "blocker_queue_hash": blocker_queue["blocker_queue_hash"],
        "requirements_passed": len(requirements) - len(failed),
        "requirements_failed": len(failed),
        "failed_requirement_ids": failed,
    }
    payload = {
        "title": "B1/B7 cone01 R111 independent-origin materiality gate",
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
        "artifacts": {"verdict": VERDICT_PATH, "blocker_queue": BLOCKER_QUEUE_PATH, "stdout": STDOUT_PATH, **{f"{role}_transcript": path for role, path in transcript_paths.items()}},
        "claim_boundary": {"what_is_supported": "Public raw files were fetched live with HTTP 2xx, nonce binding, and requested-url binding, but they are same-repository self-attested material.", "what_is_not_supported": "No independent material evidence, external reproduction, or B7 credit is accepted.", "next_gate": "Supply independent reviewer key, third-party CI transcript, and externally attested artifact transcript, then rerun R109/R110 and the single-counter audit."},
    }
    payload["payload_hash"] = stable_hash(payload)
    write_json(root / RESULT_PATH, payload)
    (root / REPORT_PATH).write_text(report(payload), encoding="utf-8")
    stdout = {"method": METHOD, "source_target_id": TARGET_ID, "requirements_passed": payload["requirements_passed"], "requirements_failed": payload["requirements_failed"], "materiality_accepted": materiality_accepted, "counter_delta": 0, "new_credit_delta": 0, "payload_hash": payload["payload_hash"]}
    write_json(root / STDOUT_PATH, stdout)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    print(json.dumps(run(Path(args.repo_root), args.timeout), sort_keys=True))


if __name__ == "__main__":
    main()
