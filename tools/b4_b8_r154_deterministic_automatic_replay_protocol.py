#!/usr/bin/env python3
"""Freeze a fail-closed deterministic replay of the R153 execution surface."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r128_transpiler_loop_layout_ranking import package_version
from b4_b8_r132_topology_constrained_route_policy import DETERMINISTIC_PROCESS_ENV


METHOD = "b4_b8_r154_deterministic_automatic_replay_protocol_v0"
R153_RESULT_PATH = "results/B4_B8_R153_independent_seed_replication_holdout_v0.json"
R153_TRIALS_PATH = "results/B4_B8_R153_independent_seed_replication_holdout/three_arm_trial_rows.json"
R153_REVEAL_PATH = "results/B4_B8_R153_independent_seed_replication_holdout/challenge_reveal.json"
R153_PROTOCOL_PATH = "results/B4_B8_R153_independent_seed_replication_protocol_v0.json"
R153_CONTRACT_PATH = "benchmarks/B4_B8_R153_independent_seed_replication_contract_v0.json"
R152_DESIGN_PATH = "results/B4_B8_R152_edge_signature_expansion_design_v0.json"
R150_DESIGN_PATH = "results/B4_B8_R150_unseen_backend_candidate_generation_design_v0.json"
RESULT_PATH = "results/B4_B8_R154_deterministic_automatic_replay_protocol_v0.json"
REPORT_PATH = "research/B4_B8_R154_deterministic_automatic_replay_protocol.md"
CONTRACT_PATH = "benchmarks/B4_B8_R154_deterministic_automatic_replay_contract_v0.json"


def payload_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def source_binding(root: Path, path: str, payload: dict | None = None) -> dict:
    binding = {"path": path, "sha256": file_sha256(root / path)}
    if payload is not None:
        binding["payload_hash"] = payload["payload_hash"]
    return binding


def build(root: Path) -> tuple[dict, dict]:
    r153_result = json.loads((root / R153_RESULT_PATH).read_text())
    r153_protocol = json.loads((root / R153_PROTOCOL_PATH).read_text())
    r152_design = json.loads((root / R152_DESIGN_PATH).read_text())
    r150_design = json.loads((root / R150_DESIGN_PATH).read_text())
    r153_trials = json.loads((root / R153_TRIALS_PATH).read_text())
    r153_reveal = json.loads((root / R153_REVEAL_PATH).read_text())
    execution_environment = {
        "python": platform.python_version(),
        "qiskit": package_version("qiskit"),
        "qiskit_aer": package_version("qiskit-aer"),
        "qiskit_ibm_runtime": package_version("qiskit-ibm-runtime"),
        "deterministic_process_environment": DETERMINISTIC_PROCESS_ENV,
        "aer_simulator_options": {
            "max_parallel_threads": 1,
            "max_parallel_experiments": 1,
            "max_parallel_shots": 1,
        },
    }
    protocol = {
        "snapshot_names": ["FakeCasablancaV2", "FakeNairobiV2", "FakePerth"],
        "task_id": "dense_validation_xy_network_n6",
        "source_trial_row_count": 96,
        "process_pass_count": 2,
        "row_count_per_pass": 96,
        "circuit_execution_count_per_pass": 288,
        "total_circuit_execution_count": 576,
        "shots_per_execution": 2048,
        "total_simulated_shots": 1179648,
        "seed_rule": "replay the publicly revealed R153 transpiler and simulator seeds without deriving new hidden seeds",
        "process_rule": "reference and replay passes execute in separate operating-system processes after public preregistration",
        "automatic_rule": "fresh optimization-level-3 compile from each frozen R153 transpiler seed",
        "qasm_rule": "SHA-256 of UTF-8 qiskit.qasm3.dumps output for every automatic circuit",
        "counts_rule": "SHA-256 of canonical sorted outcome-count JSON for all three arms in every row",
        "row_rule": "SHA-256 of canonical scientific row JSON excluding process labels and timestamps",
        "target_descriptor_rule": "SHA-256 of canonical backend name, qubit count, operation names, coupling edges, dt, and instruction-property rows",
        "automatic_qasm_hash_match_required": 96,
        "arm_counts_hash_match_required": 288,
        "scientific_row_hash_match_required": 96,
        "backend_target_hash_match_required": 3,
        "fixed_route_hash_match_required": 6,
        "r153_acceptance_condition_match_required": 10,
        "maximum_replay_mismatch_count": 0,
        "new_hidden_seed_count": 0,
        "candidate_selection_performed": False,
        "route_change_performed": False,
        "execution_environment": execution_environment,
    }
    source_bindings = {
        "r153_result": source_binding(root, R153_RESULT_PATH, r153_result),
        "r153_trials": source_binding(root, R153_TRIALS_PATH),
        "r153_reveal": source_binding(root, R153_REVEAL_PATH),
        "r153_protocol": source_binding(root, R153_PROTOCOL_PATH, r153_protocol),
        "r153_contract": source_binding(root, R153_CONTRACT_PATH),
        "r152_design": source_binding(root, R152_DESIGN_PATH, r152_design),
        "r150_design": source_binding(root, R150_DESIGN_PATH, r150_design),
    }
    requirements = [
        {"requirement_id": "R1", "label": "accepted R153 result and all route sources are hash-bound", "passed": r153_result["summary"]["global_acceptance"] is True},
        {"requirement_id": "R2", "label": "the exact 96 public R153 seed rows and reveal are hash-bound", "passed": len(r153_trials) == 96 and r153_reveal["commitment_matches"] is True},
        {"requirement_id": "R3", "label": "two independent process passes execute the same 96 rows", "passed": protocol["process_pass_count"] == 2 and protocol["row_count_per_pass"] == 96},
        {"requirement_id": "R4", "label": "all 96 automatic QASM hashes must match", "passed": protocol["automatic_qasm_hash_match_required"] == 96},
        {"requirement_id": "R5", "label": "all 288 arm-count hashes and 96 scientific-row hashes must match", "passed": protocol["arm_counts_hash_match_required"] == 288 and protocol["scientific_row_hash_match_required"] == 96},
        {"requirement_id": "R6", "label": "all backend-target and fixed-route hashes must match", "passed": protocol["backend_target_hash_match_required"] == 3 and protocol["fixed_route_hash_match_required"] == 6},
        {"requirement_id": "R7", "label": "Aer parallelism is frozen to one thread, experiment, and shot worker", "passed": set(execution_environment["aer_simulator_options"].values()) == {1}},
        {"requirement_id": "R8", "label": "Python, Qiskit, Aer, runtime, and deterministic environment are frozen", "passed": all(execution_environment[key] for key in ["python", "qiskit", "qiskit_aer", "qiskit_ibm_runtime"])},
        {"requirement_id": "R9", "label": "no new hidden seed, candidate selection, or route change occurs", "passed": protocol["new_hidden_seed_count"] == 0 and protocol["candidate_selection_performed"] is False and protocol["route_change_performed"] is False},
        {"requirement_id": "R10", "label": "hardware, temporal, real-device, general-generation, advantage, BQP, solved-frontier, and credit claims remain false", "passed": True},
    ]
    payload = {
        "title": "B4/B8 R154 deterministic automatic replay protocol",
        "version": 0,
        "method": METHOD,
        "status": "deterministic_automatic_replay_protocol_frozen_before_execution",
        "model_status": "r153_execution_reproducibility_caveat_under_fail_closed_serial_replay",
        "generated_at_unix": int(time.time()),
        "source_target_id": "T-B4-002bp/T-B8-003bt/T-B10-009bh",
        "upstream_target_id": "T-B4-002bo/T-B8-003bs/T-B10-009bg",
        "source_bindings": source_bindings,
        "protocol": protocol,
        "requirements": requirements,
        "requirement_count": 10,
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [row["requirement_id"] for row in requirements if not row["passed"]],
        "execution_started": False,
        "claim_boundary": {
            "what_is_supported": "an immutable fail-closed test of whether the R153 execution surface can replay byte-stably under serial Aer controls",
            "what_is_not_supported": "new statistical evidence, closure of the caveat before execution, causal proof, temporal or real-device transfer, hardware performance, general route-generation advantage, quantum advantage, BQP separation, solved B4/B8/B10, or new credit",
        },
    }
    payload["payload_hash"] = payload_hash(payload)
    contract = {
        "contract_id": "B4-B8-R154-deterministic-automatic-replay-contract-v0",
        "contract_status": "public_preregistration_execution_unopened",
        "target_id": payload["source_target_id"],
        "upstream_target_id": payload["upstream_target_id"],
        "research_question": "Can the R153 execution surface reproduce every automatic circuit, count vector, and scientific row across two independent serial processes?",
        "source_bindings": {
            "protocol_path": RESULT_PATH,
            "protocol_payload_hash": payload["payload_hash"],
            "protocol_sha256": None,
            **source_bindings,
        },
        "execution_protocol": protocol,
        "acceptance_conditions": [
            {"condition_id": "A1", "condition": "contract, protocol, R153 result, seeds, routes, and source hashes remain exact"},
            {"condition_id": "A2", "condition": "two separate processes each execute 96 rows, 288 circuits, and 589,824 shots"},
            {"condition_id": "A3", "condition": "automatic OpenQASM 3 hashes match 96/96"},
            {"condition_id": "A4", "condition": "repaired and denominator route hashes match 6/6 across processes"},
            {"condition_id": "A5", "condition": "canonical arm-count hashes match 288/288"},
            {"condition_id": "A6", "condition": "canonical scientific-row hashes match 96/96"},
            {"condition_id": "A7", "condition": "backend-target descriptor hashes match 3/3"},
            {"condition_id": "A8", "condition": "serial Aer options, software versions, and deterministic process environment remain exact"},
            {"condition_id": "A9", "condition": "all ten R153 acceptance decisions reproduce and total mismatch count is zero"},
            {"condition_id": "A10", "condition": "new evidence, hardware, transfer, general generation, advantage, BQP, solved-frontier, and credit claims remain false"},
        ],
        "claim_boundary": payload["claim_boundary"],
    }
    return payload, contract


def report(payload: dict, contract_sha256: str) -> str:
    p = payload["protocol"]
    e = p["execution_environment"]
    return f"""# B4/B8 R154 Deterministic Automatic Replay Protocol

- Process passes / rows per pass: `{p['process_pass_count']}` / `{p['row_count_per_pass']}`
- Executions / total shots: `{p['total_circuit_execution_count']}` / `{p['total_simulated_shots']}`
- Required automatic QASM / counts / row hash matches: `{p['automatic_qasm_hash_match_required']}` / `{p['arm_counts_hash_match_required']}` / `{p['scientific_row_hash_match_required']}`
- Required backend-target / fixed-route matches: `{p['backend_target_hash_match_required']}` / `{p['fixed_route_hash_match_required']}`
- New hidden seeds / selection / route changes: `0` / `false` / `false`
- Serial Aer options: `{json.dumps(e['aer_simulator_options'], sort_keys=True)}`
- Python / Qiskit / Aer / runtime: `{e['python']}` / `{e['qiskit']}` / `{e['qiskit_aer']}` / `{e['qiskit_ibm_runtime']}`
- Contract SHA-256: `{contract_sha256}`
- Execution started: `false`

R154 reuses the public R153 seed rows. A reference pass and a replay pass must
run in separate operating-system processes. Every automatic circuit is exported
as OpenQASM 3 and hashed; every arm count vector, scientific row, backend target,
and fixed route is independently hashed. Any mismatch rejects the gate.

This protocol creates no new hidden statistical evidence and does not close the
R153 replay caveat before execution. It does not support hardware performance,
temporal or real-device transfer, general route-generation advantage, quantum
advantage, BQP separation, a solved frontier, or new credit.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    payload, contract = build(root)
    write_json(root / RESULT_PATH, payload)
    contract["source_bindings"]["protocol_sha256"] = file_sha256(root / RESULT_PATH)
    write_json(root / CONTRACT_PATH, contract)
    contract_sha256 = file_sha256(root / CONTRACT_PATH)
    (root / REPORT_PATH).write_text(report(payload, contract_sha256), encoding="utf-8")
    print(json.dumps({"protocol": payload["protocol"], "contract_sha256": contract_sha256}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
