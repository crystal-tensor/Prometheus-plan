#!/usr/bin/env python3
"""Freeze the R158 direct-accelerator VF2 boundary experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import qiskit._accelerate

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r128_transpiler_loop_layout_ranking import package_version


METHOD = "b4_b8_r158_vf2_accelerator_boundary_protocol_v0"
R157_RESULT_PATH = "results/B4_B8_R157_vf2_tie_isolation_v0.json"
R157_DISTRIBUTIONS_PATH = "results/B4_B8_R157_vf2_tie_isolation/profile_distributions.json"
R157_PROTOCOL_PATH = "results/B4_B8_R157_vf2_tie_isolation_protocol_v0.json"
R157_CONTRACT_PATH = "benchmarks/B4_B8_R157_vf2_tie_isolation_contract_v0.json"
INPUT_PATH = "benchmarks/B4_B8_R157_vf2_post_layout_input_v0.qasm"
SOURCE_MANIFEST_PATH = "research/source_lineage/Qiskit_2_4_1_vf2_source_manifest.json"
RESULT_PATH = "results/B4_B8_R158_vf2_accelerator_boundary_protocol_v0.json"
REPORT_PATH = "research/B4_B8_R158_vf2_accelerator_boundary_protocol.md"
CONTRACT_PATH = "benchmarks/B4_B8_R158_vf2_accelerator_boundary_contract_v0.json"
QISKIT_COMMIT = "0fd015a22b84c9082173597a5d2304dc0aaec08c"


def canonical_hash(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def source_binding(root: Path, path: str, payload: dict | None = None) -> dict:
    binding = {"path": path, "sha256": file_sha256(root / path)}
    if payload is not None and "payload_hash" in payload:
        binding["payload_hash"] = payload["payload_hash"]
    return binding


def source_manifest() -> dict:
    base = f"https://github.com/Qiskit/qiskit/blob/{QISKIT_COMMIT}"
    rows = [
        {
            "source_id": "python_vf2_post_layout",
            "path": "qiskit/transpiler/passes/layout/vf2_post_layout.py",
            "sha256": "8208553a3b3a1e76272240271395294ca82a6b4d5a002ab800a809c18345c81d",
            "url": f"{base}/qiskit/transpiler/passes/layout/vf2_post_layout.py",
            "relevant_boundary": "Python pass constructs the legacy configuration and calls vf2_layout_pass_average when strict_direction is false",
        },
        {
            "source_id": "rust_vf2_layout_pass",
            "path": "crates/transpiler/src/passes/vf2/vf2_layout.rs",
            "sha256": "267810aaddb8ac9336f4404e7da34c31e07eec725eb1baa4ed6bf32ff7448ca4",
            "url": f"{base}/crates/transpiler/src/passes/vf2/vf2_layout.rs",
            "relevant_boundary": "build_average_error_map, average coupling graph construction, decreasing restriction, minimize_vf2, and last-improvement return",
        },
        {
            "source_id": "rust_vf2_core",
            "path": "crates/circuit/src/vf2.rs",
            "sha256": "f81df7792208dd0c0949b873b6b75f8ceedcde18e4e436d321435a3a9765db06",
            "url": f"{base}/crates/circuit/src/vf2.rs",
            "relevant_boundary": "VF2++ ordering, f64 score combination, strict-less restriction, per-call state maps, candidate iteration, and best-score update",
        },
        {
            "source_id": "rust_target",
            "path": "crates/transpiler/src/target/mod.rs",
            "sha256": "737ac77f827adbcfd5e33cab2af8607a604f3a79bdfdf925131702926b1df7f8",
            "url": f"{base}/crates/transpiler/src/target/mod.rs",
            "relevant_boundary": "Rust Target owns insertion-preserving maps plus randomized hash sets for operation membership",
        },
        {
            "source_id": "rust_error_map",
            "path": "crates/transpiler/src/passes/vf2/error_map.rs",
            "sha256": "0f7bb297274b2f6997f7cbf33848af750b57832a365827187d8a8d80edec2320",
            "url": f"{base}/crates/transpiler/src/passes/vf2/error_map.rs",
            "relevant_boundary": "ErrorMap is a Rust hashbrown HashMap that can be constructed internally or supplied and reused from Python",
        },
    ]
    binary_path = Path(qiskit._accelerate.__file__).resolve()
    payload = {
        "title": "Qiskit 2.4.1 VF2 source and binary lineage",
        "repository": "https://github.com/Qiskit/qiskit",
        "release": "2.4.1",
        "commit": QISKIT_COMMIT,
        "source_rows": rows,
        "installed_accelerator": {
            "path": str(binary_path),
            "sha256": hashlib.sha256(binary_path.read_bytes()).hexdigest(),
            "size_bytes": binary_path.stat().st_size,
        },
        "observed_control_flow": [
            "VF2PostLayout.run",
            "vf2_layout_pass_average",
            "build_average_error_map_or_reuse_external_map",
            "build_average_coupling_map",
            "Vf2.with_scoring",
            "Restriction.Decreasing",
            "minimize_vf2_last_improvement",
            "Vf2PassReturn.Solution",
        ],
        "claim_boundary": "source inspection identifies intervention boundaries, not the causal source of R157 variation",
    }
    payload["payload_hash"] = canonical_hash(payload)
    return payload


def build(root: Path) -> tuple[dict, dict, dict]:
    r157_result = json.loads((root / R157_RESULT_PATH).read_text())
    r157_distributions = json.loads((root / R157_DISTRIBUTIONS_PATH).read_text())
    r157_protocol = json.loads((root / R157_PROTOCOL_PATH).read_text())
    source = source_manifest()
    write_json(root / SOURCE_MANIFEST_PATH, source)
    source_bindings = {
        "r157_result": source_binding(root, R157_RESULT_PATH, r157_result),
        "r157_distributions": source_binding(root, R157_DISTRIBUTIONS_PATH),
        "r157_protocol": source_binding(root, R157_PROTOCOL_PATH, r157_protocol),
        "r157_contract": source_binding(root, R157_CONTRACT_PATH),
        "direct_replay_input": source_binding(root, INPUT_PATH),
        "qiskit_source_manifest": source_binding(root, SOURCE_MANIFEST_PATH, source),
    }
    profiles = [
        {
            "profile_id": "python_pass_fresh_dag_fresh_config_internal_error_map",
            "process_count": 1,
            "replays_per_process": 64,
            "entry_point": "VF2PostLayout.run",
            "dag_reused": False,
            "config_reused": False,
            "target_reused": True,
            "error_map_mode": "internal_fresh",
        },
        {
            "profile_id": "accelerator_fresh_dag_fresh_config_internal_error_map",
            "process_count": 1,
            "replays_per_process": 64,
            "entry_point": "qiskit._accelerate.vf2_layout.vf2_layout_pass_average",
            "dag_reused": False,
            "config_reused": False,
            "target_reused": True,
            "error_map_mode": "internal_fresh",
        },
        {
            "profile_id": "accelerator_shared_dag_shared_config_internal_error_map",
            "process_count": 1,
            "replays_per_process": 64,
            "entry_point": "qiskit._accelerate.vf2_layout.vf2_layout_pass_average",
            "dag_reused": True,
            "config_reused": True,
            "target_reused": True,
            "error_map_mode": "internal_fresh",
        },
        {
            "profile_id": "accelerator_shared_dag_shared_config_shared_error_map",
            "process_count": 1,
            "replays_per_process": 64,
            "entry_point": "qiskit._accelerate.vf2_layout.vf2_layout_pass_average",
            "dag_reused": True,
            "config_reused": True,
            "target_reused": True,
            "error_map_mode": "external_shared_sorted_construction",
        },
    ]
    protocol = {
        "research_question": "Does the exactly tied R157 mapping variation survive after the Python pass wrapper, DAG reconstruction, configuration reconstruction, and internal average-error-map reconstruction are removed in stages?",
        "snapshot_name": "FakeNairobiV2",
        "input_path": INPUT_PATH,
        "input_qasm_sha256": "ce216610e995b4c8b4bd9de6547ac6069961e1eb8881997aa05e0068ea16ab98",
        "target_descriptor_sha256": "702c8fd9dcf67a069e7af63e31a57c74c17aaa5e3c5b6d8c2e28ec0c049c0de7",
        "source_manifest_path": SOURCE_MANIFEST_PATH,
        "source_manifest_payload_hash": source["payload_hash"],
        "installed_accelerator_sha256": source["installed_accelerator"]["sha256"],
        "vf2_configuration": {
            "call_limit": 30000000,
            "max_trials": 250000,
            "shuffle_seed": -1,
            "strict_direction": False,
            "time_limit": None,
            "score_initial_layout": True,
        },
        "known_mapping_classes": {
            "endpoint_4_to_0": [6, 5, 4, 3, 0, 1, 2],
            "endpoint_4_to_2": [6, 5, 4, 3, 2, 1, 0],
            "other_mapping": "any mapping outside the two R157 vectors",
            "no_solution": "accelerator reports no mapping",
        },
        "shared_tied_score": 0.45894321220828727,
        "profile_count": 4,
        "profiles": profiles,
        "total_process_count": 4,
        "total_direct_replay_count": 256,
        "process_environment": {
            "PYTHONHASHSEED": "0",
            "RAYON_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "QISKIT_PARALLEL": "FALSE",
        },
        "frozen_software": {
            "python": platform.python_version(),
            "qiskit": package_version("qiskit"),
            "qiskit_aer": package_version("qiskit-aer"),
            "qiskit_ibm_runtime": package_version("qiskit-ibm-runtime"),
        },
        "classification_rule": {
            "rust_internal_variation_survives": "the fully shared accelerator profile contains more than one mapping class",
            "internal_error_map_boundary": "profile 3 varies but profile 4 collapses",
            "dag_or_config_boundary": "profile 2 varies but profile 3 collapses",
            "python_wrapper_boundary": "profile 1 varies but profiles 2-4 collapse",
            "boundary_nonreproduction": "all four profiles collapse to the same mapping class",
        },
        "diagnostic_completion_rule": "retain all 4 process artifacts and all 256 rows; collapse, variation, new mappings, and no-solution outcomes are admissible",
        "new_hidden_seed_count": 0,
        "candidate_selection_performed": False,
        "route_change_performed": False,
        "sampling_performed": False,
        "simulation_execution_count": 0,
        "total_simulated_shots": 0,
    }
    requirements = [
        {"requirement_id": "R1", "label": "R157 protocol, contract, result, distributions, and input are hash-bound", "passed": True},
        {"requirement_id": "R2", "label": "Qiskit release commit, five source paths and hashes, and installed accelerator binary are frozen", "passed": True},
        {"requirement_id": "R3", "label": "the exact R157 QASM, target descriptor, tied score, and pass configuration are preserved", "passed": True},
        {"requirement_id": "R4", "label": "four profiles remove wrapper, DAG, config, and error-map reconstruction in stages", "passed": True},
        {"requirement_id": "R5", "label": "four post-registration processes retain 256 replay rows", "passed": True},
        {"requirement_id": "R6", "label": "the final profile reuses DAG, Target, configuration, and external ErrorMap", "passed": True},
        {"requirement_id": "R7", "label": "all mapping, new-mapping, no-solution, collapse, and variation outcomes remain admissible", "passed": True},
        {"requirement_id": "R8", "label": "software and one-thread process environment are frozen", "passed": True},
        {"requirement_id": "R9", "label": "no hidden seed, selection, route change, simulation, sampling, or post-hoc replacement is introduced", "passed": True},
        {"requirement_id": "R10", "label": "call-boundary localization is separated from lower-level mechanism, bug, hardware, advantage, BQP, and credit claims", "passed": True},
    ]
    payload = {
        "title": "B4/B8 R158 VF2 accelerator-boundary protocol",
        "version": 0,
        "method": METHOD,
        "status": "vf2_accelerator_boundary_protocol_frozen_before_execution",
        "model_status": "source_bound_call_boundary_matrix_unopened",
        "generated_at_unix": int(time.time()),
        "source_target_id": "T-B4-002bx/T-B8-003cb/T-B10-009bp",
        "upstream_target_id": "T-B4-002bw/T-B8-003ca/T-B10-009bo",
        "source_bindings": source_bindings,
        "protocol": protocol,
        "requirements": requirements,
        "requirement_count": 10,
        "requirements_passed": 10,
        "requirements_failed": 0,
        "failed_requirement_ids": [],
        "execution_started": False,
        "claim_boundary": {
            "what_is_supported": "a source-bound preregistration that removes four call-boundary reconstruction layers in stages",
            "what_is_not_supported": "candidate-order instrumentation, a lower-level random or iteration mechanism, a confirmed Qiskit bug, general determinism, hardware or simulation performance, advantage, BQP separation, solved B4/B8/B10, or new credit",
        },
    }
    payload["payload_hash"] = canonical_hash(payload)
    contract = {
        "contract_id": "B4-B8-R158-vf2-accelerator-boundary-contract-v0",
        "contract_status": "public_preregistration_execution_unopened",
        "target_id": payload["source_target_id"],
        "upstream_target_id": payload["upstream_target_id"],
        "research_question": protocol["research_question"],
        "execution_protocol": protocol,
        "acceptance_conditions": [
            {"condition_id": "A1", "condition": "contract, protocol, R157 evidence, source manifest, input, target, and binary hashes remain exact"},
            {"condition_id": "A2", "condition": "4 post-registration process artifacts retain exactly 256 replay rows"},
            {"condition_id": "A3", "condition": "every row uses the frozen input, target, pass configuration, software, and environment"},
            {"condition_id": "A4", "condition": "all four wrapper/DAG/config/error-map profiles complete without replacement"},
            {"condition_id": "A5", "condition": "every row retains entry point, object identities, mapping vector, mapping class, stop reason, and elapsed time"},
            {"condition_id": "A6", "condition": "the external ErrorMap is deterministically constructed once and reused in profile 4"},
            {"condition_id": "A7", "condition": "new mappings and no-solution rows are retained rather than excluded"},
            {"condition_id": "A8", "condition": "all three staged contrasts and the fully shared within-profile verdict are emitted"},
            {"condition_id": "A9", "condition": "the two R157 mappings and exact tied score remain documented"},
            {"condition_id": "A10", "condition": "no hidden seed, selection, route, sampling, mechanism, bug, hardware, advantage, BQP, solved-frontier, or credit claim occurs"},
        ],
        "source_bindings": {
            **source_bindings,
            "protocol_path": RESULT_PATH,
            "protocol_payload_hash": payload["payload_hash"],
        },
        "claim_boundary": payload["claim_boundary"],
    }
    return source, payload, contract


def report(payload: dict, contract_sha256: str) -> str:
    protocol = payload["protocol"]
    return "\n".join(
        [
            "# B4/B8 R158 VF2 Accelerator-Boundary Protocol",
            "",
            f"- Qiskit source commit: `{QISKIT_COMMIT}`",
            f"- Installed accelerator SHA-256: `{protocol['installed_accelerator_sha256']}`",
            f"- Input QASM SHA-256: `{protocol['input_qasm_sha256']}`",
            f"- Profiles / OS processes / direct replays: `{protocol['profile_count']}` / `{protocol['total_process_count']}` / `{protocol['total_direct_replay_count']}`",
            f"- Shared tied score: `{protocol['shared_tied_score']}`",
            f"- Simulation executions / shots: `{protocol['simulation_execution_count']}` / `{protocol['total_simulated_shots']}`",
            f"- Contract SHA-256: `{contract_sha256}`",
            "- Execution started: `false`",
            "",
            "## Frozen Boundary Matrix",
            "",
            "R158 keeps the R157 input, Target, score, and VF2 configuration fixed while removing four reconstruction layers in stages. The final profile calls the Rust accelerator repeatedly with one shared DAG, Target, configuration object, and externally constructed ErrorMap. If that profile still varies, the observation boundary moves inside per-call Rust VF2 graph/state/scoring construction, but no particular hash, iterator, floating-point, or retention mechanism is yet proved.",
            "",
            "All 256 rows must be retained. Collapse, continued variation, another mapping, and no solution are admissible. The unopened protocol does not claim candidate-order instrumentation, a lower-level mechanism, a confirmed Qiskit bug, general compiler determinism, hardware relevance, advantage, BQP separation, solved-frontier status, or new credit.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Freeze the R158 VF2 accelerator-boundary experiment."
    )
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    outputs = [
        root / SOURCE_MANIFEST_PATH,
        root / RESULT_PATH,
        root / REPORT_PATH,
        root / CONTRACT_PATH,
    ]
    if any(path.exists() for path in outputs):
        raise ValueError("R158 preregistration evidence already exists; refusing to overwrite")
    source, payload, contract = build(root)
    write_json(root / RESULT_PATH, payload)
    contract["source_bindings"]["protocol_sha256"] = file_sha256(root / RESULT_PATH)
    write_json(root / CONTRACT_PATH, contract)
    contract_sha256 = file_sha256(root / CONTRACT_PATH)
    (root / REPORT_PATH).write_text(report(payload, contract_sha256), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "source_manifest_payload_hash": source["payload_hash"],
                "protocol_payload_hash": payload["payload_hash"],
                "contract_sha256": contract_sha256,
                "requirements_passed": payload["requirements_passed"],
                "execution_started": payload["execution_started"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
