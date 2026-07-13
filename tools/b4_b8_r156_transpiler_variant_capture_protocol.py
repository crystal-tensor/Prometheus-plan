#!/usr/bin/env python3
"""Freeze the R156 pass-level capture for the R155 transpiler transient."""

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


METHOD = "b4_b8_r156_transpiler_variant_capture_protocol_v0"
R155_RESULT_PATH = "results/B4_B8_R155_execution_mode_attribution_v0.json"
R155_CLASSIFICATION_PATH = (
    "results/B4_B8_R155_execution_mode_attribution/classification.json"
)
R155_COMPARISON_PATH = (
    "results/B4_B8_R155_execution_mode_attribution/comparison_matrix.json"
)
R155_PROTOCOL_PATH = "results/B4_B8_R155_execution_mode_attribution_protocol_v0.json"
R155_CONTRACT_PATH = "benchmarks/B4_B8_R155_execution_mode_attribution_contract_v0.json"
R153_TRIALS_PATH = (
    "results/B4_B8_R153_independent_seed_replication_holdout/three_arm_trial_rows.json"
)
RESULT_PATH = "results/B4_B8_R156_transpiler_variant_capture_protocol_v0.json"
REPORT_PATH = "research/B4_B8_R156_transpiler_variant_capture_protocol.md"
CONTRACT_PATH = "benchmarks/B4_B8_R156_transpiler_variant_capture_contract_v0.json"


def canonical_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def source_binding(root: Path, path: str, payload: dict | None = None) -> dict:
    binding = {"path": path, "sha256": file_sha256(root / path)}
    if payload is not None and "payload_hash" in payload:
        binding["payload_hash"] = payload["payload_hash"]
    return binding


def deterministic_environment() -> dict[str, str]:
    return {
        "PYTHONHASHSEED": "0",
        "RAYON_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "QISKIT_PARALLEL": "FALSE",
    }


def build(root: Path) -> tuple[dict, dict]:
    payloads = {
        "r155_result": json.loads((root / R155_RESULT_PATH).read_text()),
        "r155_classification": json.loads(
            (root / R155_CLASSIFICATION_PATH).read_text()
        ),
        "r155_comparison": json.loads((root / R155_COMPARISON_PATH).read_text()),
        "r155_protocol": json.loads((root / R155_PROTOCOL_PATH).read_text()),
    }
    r153_trials = json.loads((root / R153_TRIALS_PATH).read_text())
    source_row = next(
        row
        for row in r153_trials
        if row["target_snapshot"] == "FakeNairobiV2" and row["trial"] == 21
    )
    source_paths = {
        "r155_result": R155_RESULT_PATH,
        "r155_classification": R155_CLASSIFICATION_PATH,
        "r155_comparison": R155_COMPARISON_PATH,
        "r155_protocol": R155_PROTOCOL_PATH,
        "r155_contract": R155_CONTRACT_PATH,
        "r153_trials": R153_TRIALS_PATH,
    }
    source_bindings = {
        key: source_binding(root, path, payloads.get(key))
        for key, path in source_paths.items()
    }
    protocol = {
        "research_question": (
            "At which named Qiskit pass does the seeded FakeNairobiV2 trial-21 "
            "automatic compilation first split into the R155 OpenQASM 3 variants?"
        ),
        "snapshot_name": "FakeNairobiV2",
        "task_id": source_row["task_id"],
        "trial": 21,
        "block_index": source_row["block_index"],
        "trial_in_block": source_row["trial_in_block"],
        "transpiler_seed": source_row["transpiler_seed"],
        "optimization_level": 3,
        "process_count": 32,
        "compilation_count_per_process": 1,
        "total_compilation_count": 32,
        "simulation_execution_count": 0,
        "total_simulated_shots": 0,
        "process_environment": deterministic_environment(),
        "process_rule": (
            "each compilation executes in a distinct operating-system process "
            "after public preregistration"
        ),
        "capture_rule": (
            "record every callback pass row, normalized circuit hash and shape, "
            "bounded property-set summary, final OpenQASM 3, process identity, and runtime"
        ),
        "callback_fields": [
            "count",
            "pass_name",
            "pass_module",
            "pass_kind",
            "elapsed_seconds",
            "circuit_qasm_sha256",
            "circuit_size",
            "circuit_depth",
            "operation_counts",
            "property_set_keys",
            "property_set_summary_sha256",
        ],
        "full_final_qasm_retained_per_process": True,
        "r155_expected_variant_hashes": payloads["r155_classification"][
            "automatic_qasm_variant_hashes"
        ],
        "r155_expected_variant_count": payloads["r155_classification"][
            "automatic_qasm_variant_count"
        ],
        "r155_unique_mismatch_key": payloads["r155_classification"][
            "unique_within_profile_mismatch_keys"
        ][0],
        "classification_rule": {
            "known_variants_reproduced": (
                "both R155 final OpenQASM 3 hashes occur in the 32 immutable processes"
            ),
            "new_variant_observed": (
                "any final OpenQASM 3 hash falls outside the two R155 hashes"
            ),
            "first_circuit_divergence": (
                "first aligned callback count whose circuit hash differs across final-variant classes"
            ),
            "first_property_divergence": (
                "first aligned callback count whose bounded property-set summary differs"
            ),
            "single_variant_nonreproduction": (
                "all 32 final OpenQASM 3 hashes are identical"
            ),
        },
        "diagnostic_completion_rule": (
            "completion requires all 32 processes and all comparison artifacts; "
            "one, two, or more final variants are retained without exclusion"
        ),
        "official_qiskit_transpiler_reference": (
            "https://qiskit.qotlabs.org/docs/api/qiskit/transpiler"
        ),
        "official_qiskit_callback_reference": (
            "https://qiskit.qotlabs.org/docs/api/qiskit/compiler"
        ),
        "frozen_software": {
            "python": platform.python_version(),
            "qiskit": package_version("qiskit"),
            "qiskit_aer": package_version("qiskit-aer"),
            "qiskit_ibm_runtime": package_version("qiskit-ibm-runtime"),
        },
        "new_hidden_seed_count": 0,
        "candidate_selection_performed": False,
        "route_change_performed": False,
        "sampling_performed": False,
    }
    requirements = [
        {
            "requirement_id": "R1",
            "label": "R155 result, classification, comparison, protocol, and contract are hash-bound",
            "passed": payloads["r155_result"]["summary"]["global_acceptance"] is True,
        },
        {
            "requirement_id": "R2",
            "label": "the sole R155 mismatch row and its public seed are frozen",
            "passed": (
                protocol["r155_unique_mismatch_key"] == ["FakeNairobiV2", 21]
                and protocol["transpiler_seed"] == 105203961
            ),
        },
        {
            "requirement_id": "R3",
            "label": "32 distinct process compilations are fixed before execution",
            "passed": protocol["process_count"] == protocol["total_compilation_count"] == 32,
        },
        {
            "requirement_id": "R4",
            "label": "every pass callback and final OpenQASM 3 artifact is retained",
            "passed": (
                len(protocol["callback_fields"]) == 11
                and protocol["full_final_qasm_retained_per_process"] is True
            ),
        },
        {
            "requirement_id": "R5",
            "label": "the two R155 final circuit hashes are fixed as known classes",
            "passed": (
                len(protocol["r155_expected_variant_hashes"]) == 2
                and protocol["r155_expected_variant_count"] == 2
            ),
        },
        {
            "requirement_id": "R6",
            "label": "circuit and property-set divergence rules are frozen",
            "passed": len(protocol["classification_rule"]) == 5,
        },
        {
            "requirement_id": "R7",
            "label": "diagnostic completion does not depend on reproducing two variants",
            "passed": "one, two, or more" in protocol["diagnostic_completion_rule"],
        },
        {
            "requirement_id": "R8",
            "label": "software, seed, optimization level, and one-thread environment are frozen",
            "passed": (
                all(protocol["frozen_software"].values())
                and protocol["optimization_level"] == 3
                and set(protocol["process_environment"].values())
                == {"0", "1", "FALSE"}
            ),
        },
        {
            "requirement_id": "R9",
            "label": "no hidden seed, selection, route change, simulation, or sampling is introduced",
            "passed": (
                protocol["new_hidden_seed_count"] == 0
                and protocol["candidate_selection_performed"] is False
                and protocol["route_change_performed"] is False
                and protocol["sampling_performed"] is False
                and protocol["total_simulated_shots"] == 0
            ),
        },
        {
            "requirement_id": "R10",
            "label": "pass localization is separated from mechanism and scientific-credit claims",
            "passed": True,
        },
    ]
    claim_boundary = {
        "what_is_supported": (
            "an immutable pass-level diagnostic of the public R155 FakeNairobiV2 "
            "trial-21 automatic-compilation transient"
        ),
        "what_is_not_supported": (
            "a compiler mechanism claim from pass correlation alone, proof of a Qiskit bug, "
            "new hidden statistical evidence, simulation or hardware performance, temporal or "
            "real-device transfer, route advantage, quantum advantage, BQP separation, solved "
            "B4/B8/B10, or new credit"
        ),
    }
    payload = {
        "title": "B4/B8 R156 transpiler variant-capture protocol",
        "version": 0,
        "method": METHOD,
        "status": "transpiler_variant_capture_protocol_frozen_before_execution",
        "model_status": "single_public_row_pass_trace_diagnostic_unopened",
        "generated_at_unix": int(time.time()),
        "source_target_id": "T-B4-002bt/T-B8-003bx/T-B10-009bl",
        "upstream_target_id": "T-B4-002bs/T-B8-003bw/T-B10-009bk",
        "source_bindings": source_bindings,
        "protocol": protocol,
        "requirements": requirements,
        "requirement_count": 10,
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [
            row["requirement_id"] for row in requirements if not row["passed"]
        ],
        "execution_started": False,
        "claim_boundary": claim_boundary,
    }
    payload["payload_hash"] = canonical_hash(payload)
    contract = {
        "contract_id": "B4-B8-R156-transpiler-variant-capture-contract-v0",
        "contract_status": "public_preregistration_execution_unopened",
        "target_id": payload["source_target_id"],
        "upstream_target_id": payload["upstream_target_id"],
        "research_question": protocol["research_question"],
        "source_bindings": {
            "protocol_path": RESULT_PATH,
            "protocol_payload_hash": payload["payload_hash"],
            "protocol_sha256": None,
            **source_bindings,
        },
        "execution_protocol": protocol,
        "acceptance_conditions": [
            {"condition_id": "A1", "condition": "contract, protocol, R155 evidence, and source hashes remain exact"},
            {"condition_id": "A2", "condition": "32 distinct post-preregistration operating-system processes each compile the frozen row once"},
            {"condition_id": "A3", "condition": "every process emits a complete callback trace, final OpenQASM 3 file, environment, and identity manifest"},
            {"condition_id": "A4", "condition": "every callback row records the frozen pass, circuit, timing, shape, and bounded property-set fields"},
            {"condition_id": "A5", "condition": "all final hashes are retained and classified as known R155, new, or single-variant evidence"},
            {"condition_id": "A6", "condition": "all pass sequences and aligned circuit/property hashes are compared across final-variant classes"},
            {"condition_id": "A7", "condition": "if multiple variants occur, representative final QASM artifacts receive a structured gate-level diff"},
            {"condition_id": "A8", "condition": "the first observed circuit and property-set divergence rows are emitted when identifiable"},
            {"condition_id": "A9", "condition": "all raw process artifacts, comparisons, classifications, and transcript bindings are complete and replayable"},
            {"condition_id": "A10", "condition": "no hidden seed, selection, route change, sampling, mechanism, hardware, transfer, advantage, BQP, solved-frontier, or credit claim occurs"},
        ],
        "claim_boundary": claim_boundary,
    }
    return payload, contract


def report(payload: dict, contract_sha256: str) -> str:
    protocol = payload["protocol"]
    return f"""# B4/B8 R156 Transpiler Variant-Capture Protocol

- Frozen row: `{protocol['snapshot_name']}` / trial `{protocol['trial']}`
- Task / transpiler seed: `{protocol['task_id']}` / `{protocol['transpiler_seed']}`
- Independent processes / compilations: `{protocol['process_count']}` / `{protocol['total_compilation_count']}`
- Simulation executions / shots: `0` / `0`
- Expected R155 final-QASM variants: `{protocol['r155_expected_variant_count']}`
- Full callback traces and final OpenQASM 3 retained: `true`
- New hidden seeds / selection / route changes: `0` / `false` / `false`
- Contract SHA-256: `{contract_sha256}`
- Execution started: `false`

## Frozen Diagnostic

R156 runs only the public R155 mismatch row. Each compilation gets a fresh
operating-system process under the same one-thread environment, Qiskit version,
optimization level, target snapshot, and transpiler seed. The callback records
the circuit hash and a bounded property-set summary after every pass, while the
final OpenQASM 3 artifact is retained for structured comparison.

Diagnostic completion does not require two variants. One, two, or more final
hashes must be retained without post-hoc exclusion. A first divergent pass is
an observed localization boundary, not proof that the named pass or its
implementation is the lower-level cause. This unopened protocol makes no
hardware, transfer, route-advantage, quantum-advantage, BQP, solved-frontier,
or research-credit claim.
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
    print(
        json.dumps(
            {"protocol": payload["protocol"], "contract_sha256": contract_sha256},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
