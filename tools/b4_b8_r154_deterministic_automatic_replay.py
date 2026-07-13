#!/usr/bin/env python3
"""Run one fail-closed R154 reference or replay process."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from qiskit import qasm3, transpile
from qiskit_aer import AerSimulator

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r121_private_bundle_shot_sweep import basis_circuit
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r128_transpiler_loop_layout_ranking import package_version
from b4_b8_r132_topology_constrained_route_policy import DETERMINISTIC_PROCESS_ENV, compile_policy
from b4_b8_r135_dense_interaction_fallback import build_dense_validation_tasks
from b4_b8_r138_postcommit_statistical_challenge import exact_distribution, hellinger_fidelity, paired_bootstrap, probability_from_counts
from b4_b8_r139_lagos_ising_channel_attribution import exact_compiled_classical_distribution
from b4_b8_r153_independent_seed_replication_holdout import TARGET_CLASSES, derive_seed


METHOD = "b4_b8_r154_deterministic_automatic_replay_v0"
CONTRACT_PATH = "benchmarks/B4_B8_R154_deterministic_automatic_replay_contract_v0.json"
CONTRACT_SHA256 = "1ef1f7bec268f84a863bc46b786f4a2c3d92e4be93318ba1a399c4e582a17162"
PROTOCOL_PATH = "results/B4_B8_R154_deterministic_automatic_replay_protocol_v0.json"
PROTOCOL_PAYLOAD_HASH = "a035707430c3074baef53e6a3d20eaf88defae4d0a5194a7f967348dd62a49b8"
PREREGISTRATION_COMMIT = "07a9503f78e87eae446443647a27e0efd83cf256"
PREREGISTRATION_DISCUSSION = "https://github.com/crystal-tensor/Prometheus-plan/discussions/170"
PREREGISTRATION_CREATED_AT = "2026-07-13T13:11:35Z"
R153_RESULT_PATH = "results/B4_B8_R153_independent_seed_replication_holdout_v0.json"
R153_TRIALS_PATH = "results/B4_B8_R153_independent_seed_replication_holdout/three_arm_trial_rows.json"
R153_REVEAL_PATH = "results/B4_B8_R153_independent_seed_replication_holdout/challenge_reveal.json"
R153_PROTOCOL_PATH = "results/B4_B8_R153_independent_seed_replication_protocol_v0.json"
R153_CONTRACT_PATH = "benchmarks/B4_B8_R153_independent_seed_replication_contract_v0.json"
R152_DESIGN_PATH = "results/B4_B8_R152_edge_signature_expansion_design_v0.json"
R150_DESIGN_PATH = "results/B4_B8_R150_unseen_backend_candidate_generation_design_v0.json"
RESULT_PATH = "results/B4_B8_R154_deterministic_automatic_replay_v0.json"
REPORT_PATH = "research/B4_B8_R154_deterministic_automatic_replay.md"
OUT_DIR = "results/B4_B8_R154_deterministic_automatic_replay"
REFERENCE_ROWS_PATH = f"{OUT_DIR}/reference_rows.json"
REFERENCE_MANIFEST_PATH = f"{OUT_DIR}/reference_manifest.json"
REPLAY_ROWS_PATH = f"{OUT_DIR}/replay_rows.json"
REPLAY_MANIFEST_PATH = f"{OUT_DIR}/replay_manifest.json"
COMPARISON_PATH = f"{OUT_DIR}/comparison.json"
TRANSCRIPT_PATH = f"{OUT_DIR}/verifier_transcript.json"
AER_OPTIONS = {
    "max_parallel_threads": 1,
    "max_parallel_experiments": 1,
    "max_parallel_shots": 1,
}
CORE_R153_FIELDS = [
    "target_snapshot",
    "task_id",
    "trial",
    "block_index",
    "trial_in_block",
    "transpiler_seed",
    "simulator_seed",
    "repaired_fidelity",
    "denominator_fidelity",
    "automatic_fidelity",
    "repaired_minus_automatic",
    "repaired_minus_denominator",
]


def ensure_environment() -> None:
    if all(os.environ.get(key) == value for key, value in DETERMINISTIC_PROCESS_ENV.items()):
        return
    environment = dict(os.environ)
    environment.update(DETERMINISTIC_PROCESS_ENV)
    os.execvpe(sys.executable, [sys.executable, *sys.argv], environment)


def utc_timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def qasm_hash(circuit: Any) -> str:
    return hashlib.sha256(qasm3.dumps(circuit).encode()).hexdigest()


def condition(condition_id: str, label: str, value: Any, threshold: Any, passed: bool) -> dict[str, Any]:
    return {
        "condition_id": condition_id,
        "label": label,
        "value": value,
        "threshold": threshold,
        "passed": passed,
    }


def target_descriptor(backend: Any) -> dict[str, Any]:
    target = backend.target
    coupling = target.build_coupling_map()
    instruction_rows = []
    for operation in sorted(target.operation_names):
        for qargs, properties in sorted(
            target[operation].items(), key=lambda item: str(item[0])
        ):
            instruction_rows.append({
                "operation": operation,
                "qargs": None if qargs is None else list(qargs),
                "duration": None if properties is None else properties.duration,
                "error": None if properties is None else properties.error,
            })
    descriptor = {
        "backend_name": backend.name,
        "num_qubits": backend.num_qubits,
        "operation_names": sorted(target.operation_names),
        "coupling_edges": [] if coupling is None else sorted([list(edge) for edge in coupling.get_edges()]),
        "dt": target.dt,
        "instruction_rows": instruction_rows,
    }
    return {"descriptor": descriptor, "descriptor_hash": canonical_hash(descriptor)}


def actual_environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "qiskit": package_version("qiskit"),
        "qiskit_aer": package_version("qiskit-aer"),
        "qiskit_ibm_runtime": package_version("qiskit-ibm-runtime"),
        "deterministic_process_environment": {
            key: os.environ.get(key) for key in DETERMINISTIC_PROCESS_ENV
        },
        "aer_simulator_options": AER_OPTIONS,
    }


def validate_bindings(root: Path, contract: dict, protocol_payload: dict) -> None:
    if file_sha256(root / CONTRACT_PATH) != CONTRACT_SHA256:
        raise ValueError("R154 contract hash mismatch")
    if protocol_payload.get("payload_hash") != PROTOCOL_PAYLOAD_HASH:
        raise ValueError("R154 protocol payload hash mismatch")
    bindings = contract["source_bindings"]
    if bindings["protocol_payload_hash"] != PROTOCOL_PAYLOAD_HASH:
        raise ValueError("R154 contract protocol payload binding mismatch")
    if bindings["protocol_sha256"] != file_sha256(root / PROTOCOL_PATH):
        raise ValueError("R154 contract protocol file binding mismatch")
    if contract.get("contract_id") != "B4-B8-R154-deterministic-automatic-replay-contract-v0" or contract.get("contract_status") != "public_preregistration_execution_unopened":
        raise ValueError("R154 contract identity or status mismatch")
    if contract.get("target_id") != "T-B4-002bp/T-B8-003bt/T-B10-009bh" or protocol_payload.get("source_target_id") != contract.get("target_id"):
        raise ValueError("R154 target binding mismatch")
    paths = {
        "r153_result": R153_RESULT_PATH,
        "r153_trials": R153_TRIALS_PATH,
        "r153_reveal": R153_REVEAL_PATH,
        "r153_protocol": R153_PROTOCOL_PATH,
        "r153_contract": R153_CONTRACT_PATH,
        "r152_design": R152_DESIGN_PATH,
        "r150_design": R150_DESIGN_PATH,
    }
    for binding_id, path in paths.items():
        if bindings[binding_id]["path"] != path or bindings[binding_id]["sha256"] != file_sha256(root / path):
            raise ValueError(f"R154 source binding mismatch: {binding_id}")
        if "payload_hash" in bindings[binding_id]:
            payload = json.loads((root / path).read_text())
            if bindings[binding_id]["payload_hash"] != payload["payload_hash"]:
                raise ValueError(f"R154 source payload binding mismatch: {binding_id}")


def summarize(rows: list[dict], compiled_rows: list[dict], protocol: dict, secret: bytes) -> tuple[dict, list[dict], list[dict], list[dict]]:
    group_rows = []
    for target_name in protocol["snapshot_names"]:
        target_rows = [row for row in rows if row["target_snapshot"] == target_name]
        group_rows.append({
            "target_snapshot": target_name,
            "row_count": len(target_rows),
            "mean_repaired_minus_automatic": statistics.mean(row["repaired_minus_automatic"] for row in target_rows),
            "mean_repaired_minus_denominator": statistics.mean(row["repaired_minus_denominator"] for row in target_rows),
            "minimum_repaired_minus_denominator": min(row["repaired_minus_denominator"] for row in target_rows),
            "repaired_win_count_vs_denominator": sum(row["repaired_minus_denominator"] > 0 for row in target_rows),
            "severe_regression_count": sum(row["repaired_minus_denominator"] < -0.05 for row in target_rows),
        })
    block_rows = []
    backend_spreads = []
    for target_name in protocol["snapshot_names"]:
        target_blocks = []
        for block_index in range(4):
            target_rows = [row for row in rows if row["target_snapshot"] == target_name and row["block_index"] == block_index]
            block_row = {
                "target_snapshot": target_name,
                "block_index": block_index,
                "row_count": len(target_rows),
                "mean_repaired_minus_denominator": statistics.mean(row["repaired_minus_denominator"] for row in target_rows),
                "minimum_repaired_minus_denominator": min(row["repaired_minus_denominator"] for row in target_rows),
            }
            block_rows.append(block_row)
            target_blocks.append(block_row)
        block_means = [row["mean_repaired_minus_denominator"] for row in target_blocks]
        backend_spreads.append(max(block_means) - min(block_means))
    auto_deltas = [row["repaired_minus_automatic"] for row in rows]
    denominator_deltas = [row["repaired_minus_denominator"] for row in rows]
    bootstrap_auto = paired_bootstrap(auto_deltas, derive_seed(secret, "portfolio", 0, "bootstrap-auto"), 10000)
    bootstrap_denominator = paired_bootstrap(denominator_deltas, derive_seed(secret, "portfolio", 0, "bootstrap-denominator"), 10000)
    semantic_values = [value for row in compiled_rows for value in [row["repaired_semantic_fidelity"], row["denominator_semantic_fidelity"]]]
    summary = {
        "portfolio_group_count": len(group_rows),
        "trial_row_count": len(rows),
        "simulated_circuit_execution_count": len(rows) * 3,
        "total_simulated_shots": len(rows) * 3 * protocol["shots_per_execution"],
        "portfolio_mean_repaired_minus_automatic": statistics.mean(auto_deltas),
        "portfolio_repaired_minus_automatic_bootstrap_95_lower": bootstrap_auto["lower_95"],
        "portfolio_mean_repaired_minus_denominator": statistics.mean(denominator_deltas),
        "portfolio_repaired_minus_denominator_bootstrap_95_lower": bootstrap_denominator["lower_95"],
        "groups_with_mean_repaired_minus_denominator_at_least_negative_0_02": sum(row["mean_repaired_minus_denominator"] >= -0.02 for row in group_rows),
        "independent_block_count": len(block_rows),
        "blocks_with_mean_repaired_minus_denominator_at_least_negative_0_03": sum(row["mean_repaired_minus_denominator"] >= -0.03 for row in block_rows),
        "maximum_within_backend_block_mean_spread": max(backend_spreads),
        "severe_repaired_minus_denominator_regression_count_below_negative_0_05": sum(value < -0.05 for value in denominator_deltas),
        "minimum_semantic_fidelity": min(semantic_values),
        "semantic_fidelity_pass_count": sum(value >= 0.9999999999 for value in semantic_values),
    }
    conditions = [
        condition("A1", "source bindings remain exact", True, True, True),
        condition("A2", "groups, rows, executions, and blocks", [summary["portfolio_group_count"], summary["trial_row_count"], summary["simulated_circuit_execution_count"], summary["independent_block_count"]], [3, 96, 288, 12], summary["portfolio_group_count"] == 3 and summary["trial_row_count"] == 96 and summary["simulated_circuit_execution_count"] == 288 and summary["independent_block_count"] == 12),
        condition("A3", "all fixed routes retain semantics", [summary["semantic_fidelity_pass_count"], summary["minimum_semantic_fidelity"]], [6, 0.9999999999], summary["semantic_fidelity_pass_count"] == 6),
        condition("A4", "portfolio repaired versus automatic", [summary["portfolio_mean_repaired_minus_automatic"], summary["portfolio_repaired_minus_automatic_bootstrap_95_lower"]], [-0.005, -0.01], summary["portfolio_mean_repaired_minus_automatic"] >= -0.005 and summary["portfolio_repaired_minus_automatic_bootstrap_95_lower"] >= -0.01),
        condition("A5", "portfolio repaired versus denominator", [summary["portfolio_mean_repaired_minus_denominator"], summary["portfolio_repaired_minus_denominator_bootstrap_95_lower"]], [-0.005, -0.015], summary["portfolio_mean_repaired_minus_denominator"] >= -0.005 and summary["portfolio_repaired_minus_denominator_bootstrap_95_lower"] >= -0.015),
        condition("A6", "all backend means clear negative 0.02", summary["groups_with_mean_repaired_minus_denominator_at_least_negative_0_02"], 3, summary["groups_with_mean_repaired_minus_denominator_at_least_negative_0_02"] == 3),
        condition("A7", "severe regressions below negative 0.05", summary["severe_repaired_minus_denominator_regression_count_below_negative_0_05"], 0, summary["severe_repaired_minus_denominator_regression_count_below_negative_0_05"] == 0),
        condition("A8", "Casablanca and block stability", [next(row["mean_repaired_minus_denominator"] for row in group_rows if row["target_snapshot"] == "FakeCasablancaV2"), summary["blocks_with_mean_repaired_minus_denominator_at_least_negative_0_03"], summary["maximum_within_backend_block_mean_spread"]], [-0.02, 10, 0.08], next(row["mean_repaired_minus_denominator"] for row in group_rows if row["target_snapshot"] == "FakeCasablancaV2") >= -0.02 and summary["blocks_with_mean_repaired_minus_denominator_at_least_negative_0_03"] >= 10 and summary["maximum_within_backend_block_mean_spread"] <= 0.08),
        condition("A9", "all public R153 seed rows execute", len(rows), 96, len(rows) == 96),
        condition("A10", "forbidden claims remain false", 0, 0, True),
    ]
    return summary, group_rows, block_rows, conditions


def execute_pass(root: Path, pass_id: str, protocol_payload: dict) -> tuple[list[dict], dict]:
    protocol = protocol_payload["protocol"]
    r153_rows = json.loads((root / R153_TRIALS_PATH).read_text())
    reveal = json.loads((root / R153_REVEAL_PATH).read_text())
    design = json.loads((root / R152_DESIGN_PATH).read_text())
    r150_design = json.loads((root / R150_DESIGN_PATH).read_text())
    task = next(row for row in build_dense_validation_tasks() if row["task_id"] == protocol["task_id"])
    logical = basis_circuit(task["circuit"], tuple("Z" for _ in range(task["circuit"].num_qubits)))
    ideal = exact_distribution(task["circuit"])
    selected_path = root / design["summary"]["selected_circuit_path"]
    source_target_rows = {row["target_snapshot"]: row for row in r150_design["target_rows"]}
    source_rows = {(row["target_snapshot"], row["trial"]): row for row in r153_rows}
    rows = []
    compiled_rows = []
    descriptor_rows = []
    route_rows = []
    actual_simulator_options = []
    for target_name in protocol["snapshot_names"]:
        backend = TARGET_CLASSES[target_name]()
        simulator = AerSimulator.from_backend(backend)
        simulator.set_options(**AER_OPTIONS)
        actual_simulator_options.append({key: getattr(simulator.options, key) for key in AER_OPTIONS})
        descriptor = target_descriptor(backend)
        descriptor_rows.append({"target_snapshot": target_name, **descriptor})
        selected = source_target_rows[target_name]
        if target_name == "FakeCasablancaV2":
            repaired = qasm3.load(selected_path)
        else:
            repaired = compile_policy(logical, backend, selected["selected_mapping"], selected["selected_policy_id"], selected["selected_realization_seed"])
        denominator = qasm3.load(root / selected["denominator_circuit_path"])
        repaired_hash = qasm_hash(repaired)
        denominator_hash = qasm_hash(denominator)
        route_rows.append({
            "target_snapshot": target_name,
            "repaired_qasm_sha256": repaired_hash,
            "denominator_qasm_sha256": denominator_hash,
        })
        compiled_rows.append({
            "target_snapshot": target_name,
            "repaired_qasm_sha256": repaired_hash,
            "denominator_qasm_sha256": denominator_hash,
            "repaired_semantic_fidelity": hellinger_fidelity(ideal, exact_compiled_classical_distribution(repaired)),
            "denominator_semantic_fidelity": hellinger_fidelity(ideal, exact_compiled_classical_distribution(denominator)),
        })
        for trial in range(32):
            source = source_rows[(target_name, trial)]
            automatic = transpile(logical, backend=backend, optimization_level=3, seed_transpiler=source["transpiler_seed"])
            circuits = {"repaired": repaired, "denominator": denominator, "automatic": automatic}
            counts_by_arm = {}
            count_hashes = {}
            fidelities = {}
            for arm, circuit in circuits.items():
                counts = simulator.run(circuit, shots=protocol["shots_per_execution"], seed_simulator=source["simulator_seed"]).result().get_counts()
                canonical_counts = {str(key): int(value) for key, value in sorted(counts.items())}
                counts_by_arm[arm] = canonical_counts
                count_hashes[arm] = canonical_hash(canonical_counts)
                observed = probability_from_counts(canonical_counts, protocol["shots_per_execution"], task["circuit"].num_qubits)
                fidelities[arm] = hellinger_fidelity(ideal, observed)
            row = {
                "target_snapshot": target_name,
                "task_id": protocol["task_id"],
                "trial": trial,
                "block_index": source["block_index"],
                "trial_in_block": source["trial_in_block"],
                "transpiler_seed": source["transpiler_seed"],
                "simulator_seed": source["simulator_seed"],
                "repaired_qasm_sha256": repaired_hash,
                "denominator_qasm_sha256": denominator_hash,
                "automatic_qasm_sha256": qasm_hash(automatic),
                "arm_counts": counts_by_arm,
                "arm_counts_sha256": count_hashes,
                "repaired_fidelity": fidelities["repaired"],
                "denominator_fidelity": fidelities["denominator"],
                "automatic_fidelity": fidelities["automatic"],
                "repaired_minus_automatic": fidelities["repaired"] - fidelities["automatic"],
                "repaired_minus_denominator": fidelities["repaired"] - fidelities["denominator"],
            }
            row["scientific_row_sha256"] = canonical_hash(row)
            rows.append(row)
    secret = bytes.fromhex(reveal["challenge_secret_hex"])
    summary, group_rows, block_rows, r153_conditions = summarize(rows, compiled_rows, protocol, secret)
    environment = actual_environment()
    manifest = {
        "pass_id": pass_id,
        "process_instance_uuid": str(uuid.uuid4()),
        "process_id": os.getpid(),
        "started_at_unix": int(time.time()),
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "preregistration_discussion": PREREGISTRATION_DISCUSSION,
        "contract_sha256": CONTRACT_SHA256,
        "environment": environment,
        "simulator_option_rows": actual_simulator_options,
        "target_descriptor_rows": descriptor_rows,
        "fixed_route_rows": route_rows,
        "compiled_route_rows": compiled_rows,
        "summary": summary,
        "group_rows": group_rows,
        "block_rows": block_rows,
        "r153_acceptance_conditions": r153_conditions,
        "row_count": len(rows),
        "circuit_execution_count": len(rows) * 3,
        "total_simulated_shots": len(rows) * 3 * protocol["shots_per_execution"],
    }
    manifest["manifest_payload_hash"] = canonical_hash(manifest)
    return rows, manifest


def compare_passes(root: Path, reference_rows: list[dict], replay_rows: list[dict], reference_manifest: dict, replay_manifest: dict) -> dict:
    source_rows = json.loads((root / R153_TRIALS_PATH).read_text())
    r153_result = json.loads((root / R153_RESULT_PATH).read_text())
    reference_by_key = {(row["target_snapshot"], row["trial"]): row for row in reference_rows}
    replay_by_key = {(row["target_snapshot"], row["trial"]): row for row in replay_rows}
    source_by_key = {(row["target_snapshot"], row["trial"]): row for row in source_rows}
    keys = sorted(reference_by_key)
    automatic_matches = 0
    count_matches = 0
    row_matches = 0
    source_core_matches = 0
    mismatch_rows = []
    for key in keys:
        reference = reference_by_key[key]
        replay = replay_by_key.get(key)
        if replay is None:
            mismatch_rows.append({"key": list(key), "missing_replay_row": True})
            continue
        automatic_match = reference["automatic_qasm_sha256"] == replay["automatic_qasm_sha256"]
        automatic_matches += automatic_match
        arm_matches = {arm: reference["arm_counts_sha256"][arm] == replay["arm_counts_sha256"][arm] for arm in ["repaired", "denominator", "automatic"]}
        count_matches += sum(arm_matches.values())
        row_match = reference["scientific_row_sha256"] == replay["scientific_row_sha256"]
        row_matches += row_match
        source = source_by_key[key]
        source_core_matches += all(reference[field] == source[field] for field in CORE_R153_FIELDS)
        if not automatic_match or not all(arm_matches.values()) or not row_match:
            mismatch_rows.append({
                "key": list(key),
                "automatic_qasm_match": automatic_match,
                "arm_count_matches": arm_matches,
                "scientific_row_match": row_match,
            })
    reference_targets = {row["target_snapshot"]: row["descriptor_hash"] for row in reference_manifest["target_descriptor_rows"]}
    replay_targets = {row["target_snapshot"]: row["descriptor_hash"] for row in replay_manifest["target_descriptor_rows"]}
    reference_routes = {(row["target_snapshot"], arm): row[f"{arm}_qasm_sha256"] for row in reference_manifest["fixed_route_rows"] for arm in ["repaired", "denominator"]}
    replay_routes = {(row["target_snapshot"], arm): row[f"{arm}_qasm_sha256"] for row in replay_manifest["fixed_route_rows"] for arm in ["repaired", "denominator"]}
    target_matches = sum(reference_targets[key] == replay_targets.get(key) for key in reference_targets)
    route_matches = sum(reference_routes[key] == replay_routes.get(key) for key in reference_routes)
    source_conditions = {row["condition_id"]: row["passed"] for row in r153_result["acceptance_conditions"]}
    reference_conditions = {row["condition_id"]: row["passed"] for row in reference_manifest["r153_acceptance_conditions"]}
    replay_conditions = {row["condition_id"]: row["passed"] for row in replay_manifest["r153_acceptance_conditions"]}
    acceptance_matches = sum(source_conditions[key] == reference_conditions.get(key) == replay_conditions.get(key) for key in source_conditions)
    expected_environment = json.loads((root / PROTOCOL_PATH).read_text())["protocol"]["execution_environment"]
    environment_matches = reference_manifest["environment"] == expected_environment and replay_manifest["environment"] == expected_environment
    simulator_options_match = all(row == AER_OPTIONS for row in reference_manifest["simulator_option_rows"] + replay_manifest["simulator_option_rows"])
    process_instances_distinct = reference_manifest["process_instance_uuid"] != replay_manifest["process_instance_uuid"] and reference_manifest["process_id"] != replay_manifest["process_id"]
    total_mismatches = (
        (96 - automatic_matches)
        + (288 - count_matches)
        + (96 - row_matches)
        + (3 - target_matches)
        + (6 - route_matches)
        + (10 - acceptance_matches)
        + (0 if environment_matches else 1)
        + (0 if simulator_options_match else 1)
        + (0 if process_instances_distinct else 1)
    )
    comparison = {
        "automatic_qasm_hash_match_count": automatic_matches,
        "arm_counts_hash_match_count": count_matches,
        "scientific_row_hash_match_count": row_matches,
        "backend_target_hash_match_count": target_matches,
        "fixed_route_hash_match_count": route_matches,
        "r153_acceptance_condition_match_count": acceptance_matches,
        "reference_core_row_match_count_vs_r153_stored_rows": source_core_matches,
        "environment_matches_frozen_protocol": environment_matches,
        "simulator_options_match_frozen_protocol": simulator_options_match,
        "process_instances_distinct": process_instances_distinct,
        "total_replay_mismatch_count": total_mismatches,
        "mismatch_row_count": len(mismatch_rows),
        "mismatch_rows": mismatch_rows,
        "reference_rows_sha256": file_sha256(root / REFERENCE_ROWS_PATH),
        "replay_rows_sha256": file_sha256(root / REPLAY_ROWS_PATH),
        "reference_manifest_sha256": file_sha256(root / REFERENCE_MANIFEST_PATH),
        "replay_manifest_sha256": file_sha256(root / REPLAY_MANIFEST_PATH),
    }
    comparison["comparison_payload_hash"] = canonical_hash(comparison)
    return comparison


def report(payload: dict) -> str:
    s = payload["summary"]
    verdict = "ACCEPT" if s["global_acceptance"] else "REJECT"
    conditions = "\n".join(
        f"- {row['condition_id']} {'PASS' if row['passed'] else 'FAIL'}: {row['label']}; value `{row['value']}`, threshold `{row['threshold']}`."
        for row in payload["acceptance_conditions"]
    )
    return f"""# B4/B8 R154 Deterministic Automatic Replay

- Preregistered verdict: **{verdict}**
- Automatic QASM matches: `{s['automatic_qasm_hash_match_count']} / 96`
- Arm-count matches: `{s['arm_counts_hash_match_count']} / 288`
- Scientific-row matches: `{s['scientific_row_hash_match_count']} / 96`
- Backend-target / fixed-route matches: `{s['backend_target_hash_match_count']} / 3` / `{s['fixed_route_hash_match_count']} / 6`
- R153 acceptance-decision matches: `{s['r153_acceptance_condition_match_count']} / 10`
- Stored R153 core-row matches under serial controls: `{s['reference_core_row_match_count_vs_r153_stored_rows']} / 96`
- Total replay mismatches: `{s['total_replay_mismatch_count']}`
- Separate process instances: `{str(s['process_instances_distinct']).lower()}`
- Serial environment / simulator options: `{str(s['environment_matches_frozen_protocol']).lower()}` / `{str(s['simulator_options_match_frozen_protocol']).lower()}`
- Conditions passed / failed: `{s['acceptance_conditions_passed']}` / `{s['acceptance_conditions_failed']}`
- New hidden seeds / new credit: `0` / `0`

## Acceptance Conditions

{conditions}

## Claim Boundary

An ACCEPT closes only the serial-control replacement replay gate. It does not
prove that the original R153 default-parallel path is deterministic and adds no
new hidden statistical evidence. It does not support causal repair, temporal or
real-device transfer, hardware performance, general route-generation
advantage, quantum advantage, BQP separation, solved B4/B8/B10, or new credit.
"""


def finalize(root: Path, protocol_payload: dict, reference_rows: list[dict], replay_rows: list[dict], reference_manifest: dict, replay_manifest: dict) -> dict:
    comparison = compare_passes(root, reference_rows, replay_rows, reference_manifest, replay_manifest)
    write_json(root / COMPARISON_PATH, comparison)
    c = comparison
    conditions = [
        condition("A1", "contract, protocol, R153 result, seeds, routes, and sources remain exact", True, True, True),
        condition("A2", "two separate processes each execute 96 rows and 288 circuits", [reference_manifest["row_count"], replay_manifest["row_count"], reference_manifest["circuit_execution_count"], replay_manifest["circuit_execution_count"], c["process_instances_distinct"]], [96, 96, 288, 288, True], reference_manifest["row_count"] == replay_manifest["row_count"] == 96 and reference_manifest["circuit_execution_count"] == replay_manifest["circuit_execution_count"] == 288 and c["process_instances_distinct"]),
        condition("A3", "automatic OpenQASM 3 hashes", c["automatic_qasm_hash_match_count"], 96, c["automatic_qasm_hash_match_count"] == 96),
        condition("A4", "fixed repaired and denominator route hashes", c["fixed_route_hash_match_count"], 6, c["fixed_route_hash_match_count"] == 6),
        condition("A5", "canonical arm-count hashes", c["arm_counts_hash_match_count"], 288, c["arm_counts_hash_match_count"] == 288),
        condition("A6", "canonical scientific-row hashes", c["scientific_row_hash_match_count"], 96, c["scientific_row_hash_match_count"] == 96),
        condition("A7", "backend-target descriptor hashes", c["backend_target_hash_match_count"], 3, c["backend_target_hash_match_count"] == 3),
        condition("A8", "serial environment and simulator options", [c["environment_matches_frozen_protocol"], c["simulator_options_match_frozen_protocol"]], [True, True], c["environment_matches_frozen_protocol"] and c["simulator_options_match_frozen_protocol"]),
        condition("A9", "R153 decisions reproduce and total mismatch count is zero", [c["r153_acceptance_condition_match_count"], c["total_replay_mismatch_count"]], [10, 0], c["r153_acceptance_condition_match_count"] == 10 and c["total_replay_mismatch_count"] == 0),
        condition("A10", "new evidence and forbidden claims remain false", 0, 0, True),
    ]
    global_acceptance = all(row["passed"] for row in conditions)
    summary = {
        **{key: value for key, value in comparison.items() if key not in ["mismatch_rows", "comparison_payload_hash"]},
        "reference_process_started_at_unix": reference_manifest["started_at_unix"],
        "replay_process_started_at_unix": replay_manifest["started_at_unix"],
        "acceptance_conditions_passed": sum(row["passed"] for row in conditions),
        "acceptance_conditions_failed": sum(not row["passed"] for row in conditions),
        "failed_acceptance_condition_ids": [row["condition_id"] for row in conditions if not row["passed"]],
        "global_acceptance": global_acceptance,
        "new_hidden_seed_count": 0,
        "candidate_selection_performed": False,
        "route_change_performed": False,
        "r153_original_default_parallel_caveat_closed": False,
        "serial_control_replay_caveat_closed": global_acceptance,
        "hardware_execution_claimed": False,
        "temporal_transfer_claimed": False,
        "real_device_transfer_claimed": False,
        "general_route_generation_advantage_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "solved_frontier_claimed": False,
        "new_credit_delta": 0,
    }
    requirements = [
        {"requirement_id": "P1", "label": "public preregistration precedes both processes", "passed": reference_manifest["started_at_unix"] > utc_timestamp(PREREGISTRATION_CREATED_AT) and replay_manifest["started_at_unix"] > utc_timestamp(PREREGISTRATION_CREATED_AT)},
        {"requirement_id": "P2", "label": "contract, protocol, R153 evidence, routes, and seeds are hash-bound", "passed": True},
        {"requirement_id": "P3", "label": "reference and replay use distinct process identities", "passed": c["process_instances_distinct"]},
        {"requirement_id": "P4", "label": "all automatic QASM hashes match", "passed": c["automatic_qasm_hash_match_count"] == 96},
        {"requirement_id": "P5", "label": "all arm-count and scientific-row hashes match", "passed": c["arm_counts_hash_match_count"] == 288 and c["scientific_row_hash_match_count"] == 96},
        {"requirement_id": "P6", "label": "all target and fixed-route hashes match", "passed": c["backend_target_hash_match_count"] == 3 and c["fixed_route_hash_match_count"] == 6},
        {"requirement_id": "P7", "label": "serial environment and simulator controls match", "passed": c["environment_matches_frozen_protocol"] and c["simulator_options_match_frozen_protocol"]},
        {"requirement_id": "P8", "label": "all R153 acceptance decisions reproduce", "passed": c["r153_acceptance_condition_match_count"] == 10},
        {"requirement_id": "P9", "label": "comparison transcript records zero or explicit mismatches", "passed": c["mismatch_row_count"] == len(comparison["mismatch_rows"])},
        {"requirement_id": "P10", "label": "no new evidence, selection, route change, forbidden claim, or credit", "passed": summary["new_hidden_seed_count"] == 0 and summary["candidate_selection_performed"] is False and summary["route_change_performed"] is False and summary["new_credit_delta"] == 0},
    ]
    payload = {
        "title": "B4/B8 R154 deterministic automatic replay",
        "version": 0,
        "method": METHOD,
        "status": "deterministic_automatic_replay_preregistered_acceptance" if global_acceptance else "deterministic_automatic_replay_preregistered_rejection",
        "model_status": "serial_control_replacement_replay_with_original_default_parallel_caveat_open",
        "generated_at_unix": int(time.time()),
        "source_target_id": "T-B4-002bq/T-B8-003bu/T-B10-009bi",
        "upstream_target_id": "T-B4-002bp/T-B8-003bt/T-B10-009bh",
        "summary": summary,
        "acceptance_conditions": conditions,
        "requirements": requirements,
        "requirement_count": 10,
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [row["requirement_id"] for row in requirements if not row["passed"]],
        "artifacts": {
            "contract": CONTRACT_PATH,
            "protocol": PROTOCOL_PATH,
            "reference_rows": REFERENCE_ROWS_PATH,
            "reference_manifest": REFERENCE_MANIFEST_PATH,
            "replay_rows": REPLAY_ROWS_PATH,
            "replay_manifest": REPLAY_MANIFEST_PATH,
            "comparison": COMPARISON_PATH,
            "verifier_transcript": TRANSCRIPT_PATH,
            "result": RESULT_PATH,
            "markdown_report": REPORT_PATH,
        },
        "claim_boundary": {
            "what_is_supported": "one fail-closed byte-stable replay verdict for the R153 execution surface under newly frozen serial Aer controls",
            "what_is_not_supported": "determinism of the original default-parallel R153 path, new hidden statistical evidence, causal repair, temporal or real-device transfer, hardware performance, general route-generation advantage, quantum advantage, BQP separation, solved B4/B8/B10, or new credit",
        },
    }
    payload["payload_hash"] = canonical_hash(payload)
    transcript = {
        "contract_sha256": CONTRACT_SHA256,
        "protocol_payload_hash": PROTOCOL_PAYLOAD_HASH,
        "comparison_payload_hash": comparison["comparison_payload_hash"],
        "acceptance_conditions": conditions,
        "requirements": requirements,
        "global_acceptance": global_acceptance,
        "result_payload_hash": payload["payload_hash"],
    }
    write_json(root / TRANSCRIPT_PATH, transcript)
    write_json(root / RESULT_PATH, payload)
    (root / REPORT_PATH).write_text(report(payload), encoding="utf-8")
    return payload


def run(root: Path) -> dict:
    root = root.resolve()
    if int(time.time()) <= utc_timestamp(PREREGISTRATION_CREATED_AT):
        raise ValueError("R154 execution must start after public preregistration")
    contract = json.loads((root / CONTRACT_PATH).read_text())
    protocol_payload = json.loads((root / PROTOCOL_PATH).read_text())
    validate_bindings(root, contract, protocol_payload)
    if actual_environment() != protocol_payload["protocol"]["execution_environment"]:
        raise ValueError("R154 execution environment differs from frozen protocol")
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    reference_rows_path = root / REFERENCE_ROWS_PATH
    reference_manifest_path = root / REFERENCE_MANIFEST_PATH
    replay_rows_path = root / REPLAY_ROWS_PATH
    replay_manifest_path = root / REPLAY_MANIFEST_PATH
    if not reference_rows_path.exists() and not reference_manifest_path.exists():
        rows, manifest = execute_pass(root, "reference", protocol_payload)
        write_json(reference_rows_path, rows)
        write_json(reference_manifest_path, manifest)
        return {
            "status": "reference_process_recorded_replay_pending",
            "row_count": len(rows),
            "circuit_execution_count": manifest["circuit_execution_count"],
            "reference_rows_sha256": file_sha256(reference_rows_path),
            "reference_manifest_sha256": file_sha256(reference_manifest_path),
        }
    if reference_rows_path.exists() != reference_manifest_path.exists():
        raise ValueError("R154 reference phase is incomplete")
    if replay_rows_path.exists() or replay_manifest_path.exists() or (root / RESULT_PATH).exists():
        raise ValueError("R154 replay phase already exists; refusing to overwrite evidence")
    rows, manifest = execute_pass(root, "replay", protocol_payload)
    write_json(replay_rows_path, rows)
    write_json(replay_manifest_path, manifest)
    reference_rows = json.loads(reference_rows_path.read_text())
    reference_manifest = json.loads(reference_manifest_path.read_text())
    return finalize(root, protocol_payload, reference_rows, rows, reference_manifest, manifest)


def main() -> int:
    ensure_environment()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = run(args.root)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
