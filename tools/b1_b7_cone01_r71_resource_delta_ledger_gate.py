#!/usr/bin/env python3
"""T-B1-004fu/T-B7-015d: full-circuit resource delta ledger boundary.

R70 proves that the OpenQASM 3 candidate replays and has six fewer CNOTs.
This gate applies the pinned fault-tolerant rotation-family ledger to the same
source/candidate pair.  It deliberately separates a structural CNOT signal
from a system-resource win: a candidate must not be promoted when its logical
T count or depth regresses.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any


TOOL_DIR = Path(__file__).resolve().parent
if str(TOOL_DIR) not in sys.path:
    sys.path.insert(0, str(TOOL_DIR))

from b7_ft_synthesis_ledger import qasm_ft_resources


METHOD = "b1_b7_cone01_r71_resource_delta_ledger_gate_v0"
STATUS = "cone01_r71_structural_cnot_gain_resource_regression_boundary"
MODEL_STATUS = "r70_semantic_replay_candidate_has_cnot_gain_but_ft_resource_regression"
VERSION = "0.1"
TARGET_ID = "T-B1-004fu/T-B7-015d"
UPSTREAM_TARGET_ID = "T-B1-004ft/T-B7-015c"
R70_RESULT = "results/B1_B7_cone01_R70_machine_check_replay_prefill_gate_v0.json"
R70_PREFILL = (
    "results/B1_B7_cone01_o3_f4_exit_route_submissions/"
    "R70-R1-line1381-prefill-machine-check-replay.json"
)


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def relative(root: Path, path: Path) -> str:
    return str(path.relative_to(root))


def requirement(requirement_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def build_payload(root: Path) -> dict[str, Any]:
    started = time.time()
    r70_path = root / R70_RESULT
    prefill_path = root / R70_PREFILL
    r70 = load_json(r70_path)
    prefill = load_json(prefill_path)
    source_path = root / prefill["source_openqasm3_path"]
    candidate_path = root / prefill["candidate_openqasm3_path"]

    cost_args = SimpleNamespace(
        pi_over_4_t_cost=1,
        pi_over_8_t_cost=4,
        arbitrary_rotation_t_cost=20,
        unknown_rotation_t_cost=20,
    )
    source = qasm_ft_resources(source_path, cost_args)
    candidate = qasm_ft_resources(candidate_path, cost_args)
    source_hash = file_hash(source_path)
    candidate_hash = file_hash(candidate_path)
    r70_summary = r70["summary"]

    deltas = {
        "source_minus_candidate_cx": source["gate_counts"].get("cx", 0)
        - candidate["gate_counts"].get("cx", 0),
        "source_minus_candidate_logical_t_count": source["logical_t_count_ledger"]
        - candidate["logical_t_count_ledger"],
        "source_minus_candidate_logical_t_depth": source["logical_t_depth_ledger"]
        - candidate["logical_t_depth_ledger"],
        "source_minus_candidate_operation_count": source["operation_count_scanned"]
        - candidate["operation_count_scanned"],
    }
    accepted_proxy_t_reduction = max(0, deltas["source_minus_candidate_logical_t_count"])
    accepted_occurrence_removal = 0
    requirements = [
        requirement(
            "R1",
            "R70 machine-check replay completed with zero failed requirements",
            r70_summary["machine_check_replay_passed"] is True
            and r70_summary["requirements_failed"] == 0
            and r70_summary["r70_prefilled_field_count"] == 29,
            {
                "machine_check_replay_passed": r70_summary["machine_check_replay_passed"],
                "requirements_failed": r70_summary["requirements_failed"],
                "r70_prefilled_field_count": r70_summary["r70_prefilled_field_count"],
            },
        ),
        requirement(
            "R2",
            "R70 source and candidate OpenQASM 3 hashes still match",
            source_path.is_file()
            and candidate_path.is_file()
            and source_hash == prefill["source_openqasm3_sha256"]
            and candidate_hash == prefill["candidate_openqasm3_sha256"],
            {
                "source_hash_matches": source_hash == prefill["source_openqasm3_sha256"],
                "candidate_hash_matches": candidate_hash == prefill["candidate_openqasm3_sha256"],
            },
        ),
        requirement(
            "R3",
            "The pinned FT rotation-family cost model is explicit",
            cost_args.pi_over_4_t_cost == 1
            and cost_args.pi_over_8_t_cost == 4
            and cost_args.arbitrary_rotation_t_cost == 20
            and cost_args.unknown_rotation_t_cost == 20,
            {
                "pi_over_4_t_cost": cost_args.pi_over_4_t_cost,
                "pi_over_8_t_cost": cost_args.pi_over_8_t_cost,
                "arbitrary_rotation_t_cost": cost_args.arbitrary_rotation_t_cost,
                "unknown_rotation_t_cost": cost_args.unknown_rotation_t_cost,
            },
        ),
        requirement(
            "R4",
            "Both OpenQASM 3 artifacts parse into the same supported ledger schema",
            source["operation_count_scanned"] > 0
            and candidate["operation_count_scanned"] > 0
            and source["rotation_component_count"] > 0
            and candidate["rotation_component_count"] > 0,
            {
                "source_operation_count": source["operation_count_scanned"],
                "candidate_operation_count": candidate["operation_count_scanned"],
                "source_rotation_components": source["rotation_component_count"],
                "candidate_rotation_components": candidate["rotation_component_count"],
            },
        ),
        requirement(
            "R5",
            "The candidate retains the structural CNOT reduction",
            deltas["source_minus_candidate_cx"] == 6
            and r70_summary["cx_delta_source_minus_candidate"] == 6,
            {
                "source_cx": source["gate_counts"].get("cx", 0),
                "candidate_cx": candidate["gate_counts"].get("cx", 0),
                "cx_delta": deltas["source_minus_candidate_cx"],
            },
        ),
        requirement(
            "R6",
            "The candidate does not claim a positive logical-T-count reduction",
            deltas["source_minus_candidate_logical_t_count"] < 0
            and accepted_proxy_t_reduction == 0,
            {
                "source_logical_t_count": source["logical_t_count_ledger"],
                "candidate_logical_t_count": candidate["logical_t_count_ledger"],
                "logical_t_count_delta": deltas["source_minus_candidate_logical_t_count"],
                "accepted_proxy_t_reduction": accepted_proxy_t_reduction,
            },
        ),
        requirement(
            "R7",
            "The candidate does not claim a positive logical-T-depth reduction",
            deltas["source_minus_candidate_logical_t_depth"] < 0,
            {
                "source_logical_t_depth": source["logical_t_depth_ledger"],
                "candidate_logical_t_depth": candidate["logical_t_depth_ledger"],
                "logical_t_depth_delta": deltas["source_minus_candidate_logical_t_depth"],
            },
        ),
        requirement(
            "R8",
            "R67 acceptance and B7 credit remain blocked after the negative ledger",
            prefill["accepted_exit_route_count"] == 0
            and prefill["occurrence_removal_delta"] == accepted_occurrence_removal
            and prefill["proxy_t_reduction_delta"] == 0
            and r70_summary["b7_credit_delta"] == 0,
            {
                "accepted_exit_route_count": prefill["accepted_exit_route_count"],
                "accepted_occurrence_removal": accepted_occurrence_removal,
                "accepted_proxy_t_reduction": prefill["proxy_t_reduction_delta"],
                "b7_credit_delta": r70_summary["b7_credit_delta"],
            },
        ),
    ]

    summary = {
        "requirement_count": len(requirements),
        "requirements_passed": sum(1 for item in requirements if item["passed"]),
        "requirements_failed": sum(1 for item in requirements if not item["passed"]),
        "source_openqasm3_path": relative(root, source_path),
        "candidate_openqasm3_path": relative(root, candidate_path),
        "source_openqasm3_sha256": source_hash,
        "candidate_openqasm3_sha256": candidate_hash,
        "source_operation_counts": source["gate_counts"],
        "candidate_operation_counts": candidate["gate_counts"],
        "source_ft_resources": source,
        "candidate_ft_resources": candidate,
        "resource_deltas": deltas,
        "accepted_occurrence_removal": accepted_occurrence_removal,
        "accepted_proxy_t_reduction": accepted_proxy_t_reduction,
        "accepted_exit_route_count": 0,
        "b7_credit_delta": 0,
        "structural_cnot_gain": deltas["source_minus_candidate_cx"] > 0,
        "full_circuit_ft_resource_regression": deltas["source_minus_candidate_logical_t_count"] < 0
        and deltas["source_minus_candidate_logical_t_depth"] < 0,
        "negative_boundary_passed": all(item["passed"] for item in requirements),
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "o3_closed": False,
        "reroute_allowed": False,
        "runtime_seconds": round(time.time() - started, 6),
    }
    payload: dict[str, Any] = {
        "benchmark_id": "B1",
        "linked_problem_id": 21,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "version": VERSION,
        "target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_r70_result": relative(root, r70_path),
        "source_r70_result_sha256": file_hash(r70_path),
        "source_r70_prefill": relative(root, prefill_path),
        "source_r70_prefill_sha256": file_hash(prefill_path),
        "requirements": requirements,
        "summary": summary,
        "claim_boundary": {
            "supported_claim": (
                "The R70 candidate has a six-CNOT structural gain, but under the pinned "
                "fault-tolerant rotation-family ledger it increases logical T count and "
                "logical T depth. The structural gain is therefore not a B7 resource win."
            ),
            "unsupported_claims": [
                "This does not accept an R67 exit route.",
                "This does not provide positive occurrence-removal or proxy-T reduction.",
                "This is not a physical-device layout or calibrated backend result.",
                "This does not close O3, permit reroute, or solve B1/B7.",
            ],
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
        },
    }
    payload["payload_hash"] = stable_hash(payload)
    return payload


def markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    delta = summary["resource_deltas"]
    lines = [
        "# B1/B7 Cone01 R71 Resource Delta Ledger Boundary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Upstream: `{payload['upstream_target_id']}`",
        "",
        "## Result",
        "",
        f"- Requirements: `{summary['requirements_passed']}/{summary['requirement_count']}`",
        f"- Structural CNOT delta: `{delta['source_minus_candidate_cx']}`",
        f"- Logical T-count delta (source minus candidate): `{delta['source_minus_candidate_logical_t_count']}`",
        f"- Logical T-depth delta (source minus candidate): `{delta['source_minus_candidate_logical_t_depth']}`",
        f"- Operation-count delta (source minus candidate): `{delta['source_minus_candidate_operation_count']}`",
        f"- Source/candidate logical T ledger: `{summary['source_ft_resources']['logical_t_count_ledger']} -> {summary['candidate_ft_resources']['logical_t_count_ledger']}`",
        f"- Source/candidate logical T depth: `{summary['source_ft_resources']['logical_t_depth_ledger']} -> {summary['candidate_ft_resources']['logical_t_depth_ledger']}`",
        f"- Accepted occurrence removal / proxy-T reduction: `{summary['accepted_occurrence_removal']}` / `{summary['accepted_proxy_t_reduction']}`",
        f"- B7 credit: `{summary['b7_credit_delta']}`",
        "",
        "## Interpretation",
        "",
        "The R70 candidate is semantically replayable and removes six structural CNOTs, but it adds arbitrary and exact non-Clifford rotation work. Under the pinned FT proxy ledger, the candidate moves from 6245 to 6835 logical T units and from 964 to 1018 logical T-depth units. This is a negative resource boundary, not a solution claim.",
        "",
        "## Next Gate",
        "",
        "A future accepted route must preserve semantic replay while reducing the full-circuit FT ledger, or must provide a stronger exact absorption/decomposition certificate that removes the added rotation burden. CNOT-only improvement is insufficient for R67/B7 promotion.",
        "",
        "## Claim Boundary",
        "",
        "- R71 does not accept an exit route, occurrence removal, proxy-T reduction, reroute, O3 closure, or B7 credit.",
        "- The FT synthesis ledger is a transparent proxy, not a physical layout or calibrated hardware result.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B1_B7_cone01_R71_resource_delta_ledger_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B1_B7_cone01_R71_resource_delta_ledger_gate.md"),
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    root = args.repo_root.resolve()
    payload = build_payload(root)
    json_output = args.json_output if args.json_output.is_absolute() else root / args.json_output
    markdown_output = (
        args.markdown_output
        if args.markdown_output.is_absolute()
        else root / args.markdown_output
    )
    write_json(json_output, payload)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(markdown(payload), encoding="utf-8")
    if args.pretty:
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "requirements_passed": payload["summary"]["requirements_passed"],
                    "requirements_failed": payload["summary"]["requirements_failed"],
                    "resource_deltas": payload["summary"]["resource_deltas"],
                    "accepted_occurrence_removal": payload["summary"]["accepted_occurrence_removal"],
                    "accepted_proxy_t_reduction": payload["summary"]["accepted_proxy_t_reduction"],
                    "b7_credit_delta": payload["summary"]["b7_credit_delta"],
                    "payload_hash": payload["payload_hash"],
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
