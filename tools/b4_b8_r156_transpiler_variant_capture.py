#!/usr/bin/env python3
"""Execute the preregistered R156 pass-level transpiler variant capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import uuid
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from qiskit import qasm3, transpile
from qiskit.converters import dag_to_circuit
from qiskit.transpiler import AnalysisPass, TransformationPass

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r121_private_bundle_shot_sweep import basis_circuit
from b4_b8_r126_calibration_attribution_ledger import file_sha256
from b4_b8_r128_transpiler_loop_layout_ranking import package_version
from b4_b8_r135_dense_interaction_fallback import build_dense_validation_tasks
from b4_b8_r153_independent_seed_replication_holdout import TARGET_CLASSES
from b4_b8_r154_deterministic_automatic_replay import canonical_hash, qasm_hash


METHOD = "b4_b8_r156_transpiler_variant_capture_v0"
CONTRACT_PATH = "benchmarks/B4_B8_R156_transpiler_variant_capture_contract_v0.json"
CONTRACT_SHA256 = "04911bf4f81e568b67380990f2a8b3e18fe6ed50930d258fa12cd99996bbaf76"
PROTOCOL_PATH = "results/B4_B8_R156_transpiler_variant_capture_protocol_v0.json"
PROTOCOL_PAYLOAD_HASH = "e01668bdcb20dacf6cfb47e8c5cadfce16ccd7a19f2dea5f3ef0f1a9565d1aed"
PREREGISTRATION_COMMIT = "571733ae65e54093c1268466db2d462cdb5b679d"
PREREGISTRATION_DISCUSSION = "https://github.com/crystal-tensor/Prometheus-plan/discussions/174"
PREREGISTRATION_CREATED_AT = "2026-07-13T14:39:17Z"
R155_RESULT_PATH = "results/B4_B8_R155_execution_mode_attribution_v0.json"
R155_CLASSIFICATION_PATH = "results/B4_B8_R155_execution_mode_attribution/classification.json"
R155_COMPARISON_PATH = "results/B4_B8_R155_execution_mode_attribution/comparison_matrix.json"
R155_PROTOCOL_PATH = "results/B4_B8_R155_execution_mode_attribution_protocol_v0.json"
R155_CONTRACT_PATH = "benchmarks/B4_B8_R155_execution_mode_attribution_contract_v0.json"
R153_TRIALS_PATH = "results/B4_B8_R153_independent_seed_replication_holdout/three_arm_trial_rows.json"
OUT_DIR = "results/B4_B8_R156_transpiler_variant_capture"
VARIANT_SUMMARY_PATH = f"{OUT_DIR}/variant_summary.json"
PASS_DIVERGENCE_PATH = f"{OUT_DIR}/pass_divergence.json"
GATE_DIFF_PATH = f"{OUT_DIR}/gate_level_diff.json"
TRANSCRIPT_PATH = f"{OUT_DIR}/verifier_transcript.json"
RESULT_PATH = "results/B4_B8_R156_transpiler_variant_capture_v0.json"
REPORT_PATH = "research/B4_B8_R156_transpiler_variant_capture.md"
REQUIRED_TRACE_FIELDS = [
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
]


def utc_timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


def condition(
    condition_id: str,
    label: str,
    value: Any,
    threshold: Any,
    passed: bool,
) -> dict[str, Any]:
    return {
        "condition_id": condition_id,
        "label": label,
        "value": value,
        "threshold": threshold,
        "passed": passed,
    }


def process_paths(process_index: int) -> tuple[str, str, str]:
    stem = f"{OUT_DIR}/process_{process_index:02d}"
    return f"{stem}_trace.json", f"{stem}_manifest.json", f"{stem}_final.qasm"


def clean_repr(value: Any) -> str:
    text = repr(value)
    text = re.sub(r"0x[0-9a-fA-F]+", "0xADDR", text)
    return text[:4096]


def bounded_value(value: Any, depth: int = 0) -> Any:
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        return value if value == value and abs(value) != float("inf") else str(value)
    if depth >= 5:
        return {"type": type(value).__name__, "repr": clean_repr(value)}
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda item: clean_repr(item[0]))
        return {
            "type": type(value).__name__,
            "item_count": len(items),
            "items": [
                [bounded_value(key, depth + 1), bounded_value(item, depth + 1)]
                for key, item in items[:256]
            ],
            "truncated": len(items) > 256,
        }
    if isinstance(value, (list, tuple)):
        return {
            "type": type(value).__name__,
            "item_count": len(value),
            "items": [bounded_value(item, depth + 1) for item in value[:256]],
            "truncated": len(value) > 256,
        }
    if isinstance(value, (set, frozenset)):
        items = sorted(value, key=clean_repr)
        return {
            "type": type(value).__name__,
            "item_count": len(items),
            "items": [bounded_value(item, depth + 1) for item in items[:256]],
            "truncated": len(items) > 256,
        }
    if hasattr(value, "get_virtual_bits") and hasattr(value, "get_physical_bits"):
        virtual = sorted(
            [[clean_repr(bit), physical] for bit, physical in value.get_virtual_bits().items()],
            key=lambda row: row[0],
        )
        physical = sorted(
            [[index, clean_repr(bit)] for index, bit in value.get_physical_bits().items()],
            key=lambda row: row[0],
        )
        return {
            "type": type(value).__name__,
            "virtual_bits": virtual,
            "physical_bits": physical,
        }
    if hasattr(value, "tolist"):
        try:
            return bounded_value(value.tolist(), depth + 1)
        except Exception:
            pass
    if hasattr(value, "to_dict"):
        try:
            return bounded_value(value.to_dict(), depth + 1)
        except Exception:
            pass
    return {
        "type": f"{type(value).__module__}.{type(value).__name__}",
        "repr": clean_repr(value),
    }


def summarize_property_set(property_set: Any) -> tuple[dict, str]:
    summary = {
        str(key): bounded_value(value)
        for key, value in sorted(property_set.items(), key=lambda item: str(item[0]))
    }
    return summary, canonical_hash(summary)


def pass_kind(pass_: Any) -> str:
    kinds = []
    if isinstance(pass_, AnalysisPass):
        kinds.append("analysis")
    if isinstance(pass_, TransformationPass):
        kinds.append("transformation")
    return "+".join(kinds) if kinds else "generic"


def circuit_shape(circuit: Any) -> dict[str, Any]:
    return {
        "circuit_size": circuit.size(),
        "circuit_depth": circuit.depth(),
        "operation_counts": {
            str(key): int(value)
            for key, value in sorted(circuit.count_ops().items())
        },
    }


def actual_environment(protocol: dict) -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "qiskit": package_version("qiskit"),
        "qiskit_aer": package_version("qiskit-aer"),
        "qiskit_ibm_runtime": package_version("qiskit-ibm-runtime"),
        "process_environment": {
            key: os.environ.get(key) for key in protocol["process_environment"]
        },
    }


def validate_bindings(root: Path, contract: dict, protocol_payload: dict) -> None:
    if file_sha256(root / CONTRACT_PATH) != CONTRACT_SHA256:
        raise ValueError("R156 contract hash mismatch")
    if protocol_payload.get("payload_hash") != PROTOCOL_PAYLOAD_HASH:
        raise ValueError("R156 protocol payload hash mismatch")
    if contract.get("contract_id") != "B4-B8-R156-transpiler-variant-capture-contract-v0":
        raise ValueError("R156 contract identity mismatch")
    if contract.get("contract_status") != "public_preregistration_execution_unopened":
        raise ValueError("R156 contract status mismatch")
    if contract.get("target_id") != "T-B4-002bt/T-B8-003bx/T-B10-009bl":
        raise ValueError("R156 target binding mismatch")
    bindings = contract["source_bindings"]
    if bindings["protocol_payload_hash"] != PROTOCOL_PAYLOAD_HASH:
        raise ValueError("R156 protocol payload binding mismatch")
    if bindings["protocol_sha256"] != file_sha256(root / PROTOCOL_PATH):
        raise ValueError("R156 protocol file binding mismatch")
    for binding_id, binding in bindings.items():
        if binding_id in {"protocol_path", "protocol_payload_hash", "protocol_sha256"}:
            continue
        path = root / binding["path"]
        if not path.exists() or file_sha256(path) != binding["sha256"]:
            raise ValueError(f"R156 source binding mismatch: {binding_id}")
        if "payload_hash" in binding:
            payload = json.loads(path.read_text())
            if payload.get("payload_hash") != binding["payload_hash"]:
                raise ValueError(f"R156 source payload mismatch: {binding_id}")


def verify_process_environment(protocol: dict) -> None:
    actual = {key: os.environ.get(key) for key in protocol["process_environment"]}
    if actual != protocol["process_environment"]:
        raise ValueError(f"R156 process environment mismatch: {actual}")


def build_logical_circuit(protocol: dict) -> Any:
    task = next(
        row
        for row in build_dense_validation_tasks()
        if row["task_id"] == protocol["task_id"]
    )
    return basis_circuit(
        task["circuit"], tuple("Z" for _ in range(task["circuit"].num_qubits))
    )


def execute_worker(
    root: Path,
    process_index: int,
    protocol_payload: dict,
) -> dict:
    protocol = protocol_payload["protocol"]
    verify_process_environment(protocol)
    trace_rel, manifest_rel, qasm_rel = process_paths(process_index)
    trace_path = root / trace_rel
    manifest_path = root / manifest_rel
    qasm_path = root / qasm_rel
    if trace_path.exists() or manifest_path.exists() or qasm_path.exists():
        raise ValueError(f"R156 worker evidence already exists: {process_index}")
    backend = TARGET_CLASSES[protocol["snapshot_name"]]()
    logical = build_logical_circuit(protocol)
    trace_rows: list[dict[str, Any]] = []

    def callback(**kwargs: Any) -> None:
        circuit = dag_to_circuit(kwargs["dag"])
        qasm_text = qasm3.dumps(circuit)
        property_summary, property_hash = summarize_property_set(kwargs["property_set"])
        row = {
            "count": int(kwargs["count"]),
            "pass_name": type(kwargs["pass_"]).__name__,
            "pass_module": type(kwargs["pass_"]).__module__,
            "pass_kind": pass_kind(kwargs["pass_"]),
            "elapsed_seconds": float(kwargs["time"]),
            "circuit_qasm_sha256": hashlib.sha256(qasm_text.encode()).hexdigest(),
            **circuit_shape(circuit),
            "property_set_keys": sorted(str(key) for key in kwargs["property_set"]),
            "property_set_summary_sha256": property_hash,
            "property_set_summary": property_summary,
        }
        row["trace_row_payload_hash"] = canonical_hash(row)
        trace_rows.append(row)

    started_at = int(time.time())
    started_perf = time.perf_counter()
    automatic = transpile(
        logical,
        backend=backend,
        optimization_level=protocol["optimization_level"],
        seed_transpiler=protocol["transpiler_seed"],
        callback=callback,
        num_processes=1,
    )
    elapsed = time.perf_counter() - started_perf
    final_qasm = qasm3.dumps(automatic)
    qasm_path.parent.mkdir(parents=True, exist_ok=True)
    qasm_path.write_text(final_qasm, encoding="utf-8")
    write_json(trace_path, trace_rows)
    shape = circuit_shape(automatic)
    manifest = {
        "process_index": process_index,
        "process_instance_uuid": str(uuid.uuid4()),
        "process_id": os.getpid(),
        "started_at_unix": started_at,
        "elapsed_seconds": elapsed,
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "preregistration_discussion": PREREGISTRATION_DISCUSSION,
        "contract_sha256": CONTRACT_SHA256,
        "protocol_payload_hash": PROTOCOL_PAYLOAD_HASH,
        "environment": actual_environment(protocol),
        "snapshot_name": protocol["snapshot_name"],
        "task_id": protocol["task_id"],
        "trial": protocol["trial"],
        "transpiler_seed": protocol["transpiler_seed"],
        "optimization_level": protocol["optimization_level"],
        "trace_path": trace_rel,
        "trace_sha256": file_sha256(trace_path),
        "trace_row_count": len(trace_rows),
        "pass_sequence_sha256": canonical_hash(
            [
                [row["count"], row["pass_module"], row["pass_name"], row["pass_kind"]]
                for row in trace_rows
            ]
        ),
        "final_qasm_path": qasm_rel,
        "final_qasm_sha256": hashlib.sha256(final_qasm.encode()).hexdigest(),
        "final_qasm_file_sha256": file_sha256(qasm_path),
        **shape,
        "simulation_execution_count": 0,
        "total_simulated_shots": 0,
    }
    manifest["manifest_payload_hash"] = canonical_hash(manifest)
    write_json(manifest_path, manifest)
    return manifest


def operation_signature(circuit: Any) -> list[dict[str, Any]]:
    rows = []
    for index, instruction in enumerate(circuit.data):
        operation = instruction.operation
        row = {
            "index": index,
            "name": operation.name,
            "qubits": [circuit.find_bit(bit).index for bit in instruction.qubits],
            "clbits": [circuit.find_bit(bit).index for bit in instruction.clbits],
            "params": [clean_repr(param) for param in operation.params],
        }
        row["signature"] = canonical_hash(row)
        rows.append(row)
    return rows


def gate_diff(root: Path, variant_rows: list[dict]) -> dict:
    representatives = []
    for variant in variant_rows:
        circuit = qasm3.load(root / variant["representative_final_qasm_path"])
        representatives.append(
            {
                "final_qasm_sha256": variant["final_qasm_sha256"],
                "representative_process_index": variant["representative_process_index"],
                "representative_final_qasm_path": variant[
                    "representative_final_qasm_path"
                ],
                "operations": operation_signature(circuit),
            }
        )
    comparisons = []
    for left_index in range(len(representatives)):
        for right_index in range(left_index + 1, len(representatives)):
            left = representatives[left_index]
            right = representatives[right_index]
            left_signatures = [row["signature"] for row in left["operations"]]
            right_signatures = [row["signature"] for row in right["operations"]]
            matcher = SequenceMatcher(a=left_signatures, b=right_signatures, autojunk=False)
            diff_rows = []
            for tag, i1, i2, j1, j2 in matcher.get_opcodes():
                if tag == "equal":
                    continue
                diff_rows.append(
                    {
                        "tag": tag,
                        "left_range": [i1, i2],
                        "right_range": [j1, j2],
                        "left_operations": left["operations"][i1:i2],
                        "right_operations": right["operations"][j1:j2],
                    }
                )
            comparisons.append(
                {
                    "left_final_qasm_sha256": left["final_qasm_sha256"],
                    "right_final_qasm_sha256": right["final_qasm_sha256"],
                    "left_operation_count": len(left["operations"]),
                    "right_operation_count": len(right["operations"]),
                    "diff_hunk_count": len(diff_rows),
                    "diff_rows": diff_rows,
                }
            )
    payload = {
        "representative_count": len(representatives),
        "comparison_count": len(comparisons),
        "representatives": [
            {key: value for key, value in row.items() if key != "operations"}
            for row in representatives
        ],
        "comparisons": comparisons,
    }
    payload["gate_level_diff_payload_hash"] = canonical_hash(payload)
    return payload


def trace_signature(row: dict) -> list[Any]:
    return [row["count"], row["pass_module"], row["pass_name"], row["pass_kind"]]


def build_divergence(
    manifests: list[dict],
    traces: dict[int, list[dict]],
    variant_rows: list[dict],
) -> dict:
    process_indices_by_variant = {
        row["final_qasm_sha256"]: row["process_indices"] for row in variant_rows
    }
    all_sequences = {
        canonical_hash([trace_signature(row) for row in traces[index]])
        for index in traces
    }
    pair_rows = []
    first_circuit_candidates = []
    first_property_candidates = []
    for left_index in range(len(variant_rows)):
        for right_index in range(left_index + 1, len(variant_rows)):
            left_variant = variant_rows[left_index]["final_qasm_sha256"]
            right_variant = variant_rows[right_index]["final_qasm_sha256"]
            left_process = process_indices_by_variant[left_variant][0]
            right_process = process_indices_by_variant[right_variant][0]
            left_trace = traces[left_process]
            right_trace = traces[right_process]
            aligned = (
                len(left_trace) == len(right_trace)
                and [trace_signature(row) for row in left_trace]
                == [trace_signature(row) for row in right_trace]
            )
            first_circuit = None
            first_property = None
            if aligned:
                for left_row, right_row in zip(left_trace, right_trace):
                    if first_circuit is None and left_row["circuit_qasm_sha256"] != right_row["circuit_qasm_sha256"]:
                        first_circuit = {
                            "count": left_row["count"],
                            "pass_name": left_row["pass_name"],
                            "pass_module": left_row["pass_module"],
                            "left_circuit_qasm_sha256": left_row["circuit_qasm_sha256"],
                            "right_circuit_qasm_sha256": right_row["circuit_qasm_sha256"],
                        }
                    if first_property is None and left_row["property_set_summary_sha256"] != right_row["property_set_summary_sha256"]:
                        first_property = {
                            "count": left_row["count"],
                            "pass_name": left_row["pass_name"],
                            "pass_module": left_row["pass_module"],
                            "left_property_set_summary_sha256": left_row[
                                "property_set_summary_sha256"
                            ],
                            "right_property_set_summary_sha256": right_row[
                                "property_set_summary_sha256"
                            ],
                        }
                    if first_circuit is not None and first_property is not None:
                        break
            if first_circuit:
                first_circuit_candidates.append(first_circuit)
            if first_property:
                first_property_candidates.append(first_property)
            pair_rows.append(
                {
                    "left_final_qasm_sha256": left_variant,
                    "right_final_qasm_sha256": right_variant,
                    "left_process_index": left_process,
                    "right_process_index": right_process,
                    "pass_sequences_aligned": aligned,
                    "first_circuit_divergence": first_circuit,
                    "first_property_divergence": first_property,
                }
            )
    first_circuit = (
        min(first_circuit_candidates, key=lambda row: row["count"])
        if first_circuit_candidates
        else None
    )
    first_property = (
        min(first_property_candidates, key=lambda row: row["count"])
        if first_property_candidates
        else None
    )
    payload = {
        "process_count": len(manifests),
        "final_variant_count": len(variant_rows),
        "pass_sequence_variant_count": len(all_sequences),
        "all_pass_sequences_identical": len(all_sequences) == 1,
        "variant_pair_comparison_count": len(pair_rows),
        "all_variant_pair_pass_sequences_aligned": all(
            row["pass_sequences_aligned"] for row in pair_rows
        ),
        "first_circuit_divergence": first_circuit,
        "first_property_divergence": first_property,
        "variant_pair_rows": pair_rows,
    }
    payload["pass_divergence_payload_hash"] = canonical_hash(payload)
    return payload


def aggregate(root: Path, protocol_payload: dict, contract: dict) -> dict:
    protocol = protocol_payload["protocol"]
    manifests = []
    traces: dict[int, list[dict]] = {}
    process_artifacts = []
    preregistration_timestamp = utc_timestamp(PREREGISTRATION_CREATED_AT)
    for process_index in range(protocol["process_count"]):
        trace_rel, manifest_rel, qasm_rel = process_paths(process_index)
        trace_path = root / trace_rel
        manifest_path = root / manifest_rel
        qasm_path = root / qasm_rel
        if not trace_path.exists() or not manifest_path.exists() or not qasm_path.exists():
            raise ValueError(f"R156 process artifact missing: {process_index}")
        trace_rows = json.loads(trace_path.read_text())
        manifest = json.loads(manifest_path.read_text())
        if manifest["trace_sha256"] != file_sha256(trace_path):
            raise ValueError(f"R156 trace hash mismatch: {process_index}")
        if manifest["final_qasm_file_sha256"] != file_sha256(qasm_path):
            raise ValueError(f"R156 final QASM hash mismatch: {process_index}")
        manifests.append(manifest)
        traces[process_index] = trace_rows
        process_artifacts.append(
            {
                "process_index": process_index,
                "manifest_path": manifest_rel,
                "manifest_sha256": file_sha256(manifest_path),
                "trace_path": trace_rel,
                "trace_sha256": file_sha256(trace_path),
                "final_qasm_path": qasm_rel,
                "final_qasm_sha256": file_sha256(qasm_path),
            }
        )
    variant_counts = Counter(row["final_qasm_sha256"] for row in manifests)
    known_hashes = set(protocol["r155_expected_variant_hashes"])
    variant_rows = []
    for final_hash, count in sorted(variant_counts.items()):
        process_indices = [
            row["process_index"]
            for row in manifests
            if row["final_qasm_sha256"] == final_hash
        ]
        representative_index = process_indices[0]
        representative_manifest = manifests[representative_index]
        variant_rows.append(
            {
                "final_qasm_sha256": final_hash,
                "process_count": count,
                "process_indices": process_indices,
                "known_r155_variant": final_hash in known_hashes,
                "representative_process_index": representative_index,
                "representative_final_qasm_path": representative_manifest[
                    "final_qasm_path"
                ],
                "circuit_size": representative_manifest["circuit_size"],
                "circuit_depth": representative_manifest["circuit_depth"],
                "operation_counts": representative_manifest["operation_counts"],
            }
        )
    variant_summary = {
        "process_count": len(manifests),
        "final_variant_count": len(variant_rows),
        "known_r155_variant_count_observed": sum(
            row["known_r155_variant"] for row in variant_rows
        ),
        "unknown_variant_count_observed": sum(
            not row["known_r155_variant"] for row in variant_rows
        ),
        "known_r155_variants_reproduced": known_hashes.issubset(variant_counts),
        "single_variant_nonreproduction": len(variant_rows) == 1,
        "variant_rows": variant_rows,
        "process_artifacts": process_artifacts,
    }
    variant_summary["variant_summary_payload_hash"] = canonical_hash(variant_summary)
    divergence = build_divergence(manifests, traces, variant_rows)
    diff = gate_diff(root, variant_rows)
    write_json(root / VARIANT_SUMMARY_PATH, variant_summary)
    write_json(root / PASS_DIVERGENCE_PATH, divergence)
    write_json(root / GATE_DIFF_PATH, diff)
    process_ids = {row["process_id"] for row in manifests}
    process_uuids = {row["process_instance_uuid"] for row in manifests}
    all_trace_rows = [row for trace in traces.values() for row in trace]
    trace_fields_complete = all(
        all(field in row for field in REQUIRED_TRACE_FIELDS) for row in all_trace_rows
    )
    all_processes_after_preregistration = all(
        row["started_at_unix"] >= preregistration_timestamp for row in manifests
    )
    all_environments_match = all(
        row["environment"]["process_environment"] == protocol["process_environment"]
        and row["environment"]["qiskit"] == protocol["frozen_software"]["qiskit"]
        for row in manifests
    )
    all_source_fields_match = all(
        row["snapshot_name"] == protocol["snapshot_name"]
        and row["trial"] == protocol["trial"]
        and row["transpiler_seed"] == protocol["transpiler_seed"]
        and row["optimization_level"] == protocol["optimization_level"]
        for row in manifests
    )
    multi_variant = len(variant_rows) > 1
    divergence_complete = (
        not multi_variant
        or (
            divergence["all_variant_pair_pass_sequences_aligned"]
            and divergence["first_circuit_divergence"] is not None
        )
    )
    diff_complete = not multi_variant or diff["comparison_count"] > 0
    summary = {
        "process_count": len(manifests),
        "process_id_count": len(process_ids),
        "process_instance_uuid_count": len(process_uuids),
        "process_started_after_preregistration_count": sum(
            row["started_at_unix"] >= preregistration_timestamp for row in manifests
        ),
        "compilation_count": len(manifests),
        "callback_trace_count": len(manifests),
        "callback_trace_row_count": len(all_trace_rows),
        "minimum_trace_row_count": min(len(trace) for trace in traces.values()),
        "maximum_trace_row_count": max(len(trace) for trace in traces.values()),
        "final_variant_count": len(variant_rows),
        "known_r155_variant_count_observed": variant_summary[
            "known_r155_variant_count_observed"
        ],
        "unknown_variant_count_observed": variant_summary[
            "unknown_variant_count_observed"
        ],
        "known_r155_variants_reproduced": variant_summary[
            "known_r155_variants_reproduced"
        ],
        "single_variant_nonreproduction": variant_summary[
            "single_variant_nonreproduction"
        ],
        "pass_sequence_variant_count": divergence["pass_sequence_variant_count"],
        "all_pass_sequences_identical": divergence["all_pass_sequences_identical"],
        "first_circuit_divergence_count": (
            divergence["first_circuit_divergence"]["count"]
            if divergence["first_circuit_divergence"]
            else None
        ),
        "first_circuit_divergence_pass": (
            divergence["first_circuit_divergence"]["pass_name"]
            if divergence["first_circuit_divergence"]
            else None
        ),
        "first_property_divergence_count": (
            divergence["first_property_divergence"]["count"]
            if divergence["first_property_divergence"]
            else None
        ),
        "first_property_divergence_pass": (
            divergence["first_property_divergence"]["pass_name"]
            if divergence["first_property_divergence"]
            else None
        ),
        "gate_level_diff_comparison_count": diff["comparison_count"],
        "simulation_execution_count": 0,
        "total_simulated_shots": 0,
        "new_hidden_seed_count": 0,
        "candidate_selection_performed": False,
        "route_change_performed": False,
        "sampling_performed": False,
        "compiler_mechanism_claimed": False,
        "qiskit_bug_claimed": False,
        "hardware_execution_claimed": False,
        "temporal_transfer_claimed": False,
        "real_device_transfer_claimed": False,
        "general_route_generation_advantage_claimed": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "solved_frontier_claimed": False,
        "new_credit_delta": 0,
    }
    acceptance = [
        condition("A1", "contract, protocol, R155 evidence, and sources remain exact", True, True, True),
        condition("A2", "32 distinct post-preregistration processes compile once", [summary["process_count"], summary["process_id_count"], summary["process_instance_uuid_count"], summary["process_started_after_preregistration_count"]], [32, 32, 32, 32], summary["process_count"] == summary["process_id_count"] == summary["process_instance_uuid_count"] == summary["process_started_after_preregistration_count"] == 32),
        condition("A3", "all traces, final QASM files, environments, and identities are complete", [summary["callback_trace_count"], len(process_artifacts), all_environments_match, all_source_fields_match], [32, 32, True, True], summary["callback_trace_count"] == len(process_artifacts) == 32 and all_environments_match and all_source_fields_match),
        condition("A4", "all callback rows preserve the frozen fields", trace_fields_complete, True, trace_fields_complete and len(all_trace_rows) > 0),
        condition("A5", "all final hashes are retained and classified", sum(row["process_count"] for row in variant_rows), 32, sum(row["process_count"] for row in variant_rows) == 32),
        condition("A6", "pass sequences and aligned hashes are compared", [divergence["variant_pair_comparison_count"], divergence["pass_sequence_variant_count"]], [max(0, len(variant_rows) * (len(variant_rows) - 1) // 2), 1], divergence["variant_pair_comparison_count"] == max(0, len(variant_rows) * (len(variant_rows) - 1) // 2) and divergence["pass_sequence_variant_count"] >= 1),
        condition("A7", "multiple variants receive a structured gate-level diff", diff_complete, True, diff_complete),
        condition("A8", "first observed divergence is emitted when identifiable", divergence_complete, True, divergence_complete),
        condition("A9", "all process artifacts and aggregate bindings are complete", len(process_artifacts), 32, len(process_artifacts) == 32),
        condition("A10", "new seeds, selection, routes, sampling, mechanism, and forbidden claims remain false", 0, 0, True),
    ]
    requirements = [
        {"requirement_id": "P1", "label": "public preregistration precedes all processes", "passed": all_processes_after_preregistration},
        {"requirement_id": "P2", "label": "contract, protocol, R155 evidence, and source hashes are bound", "passed": True},
        {"requirement_id": "P3", "label": "all 32 processes are independently identified", "passed": len(process_ids) == len(process_uuids) == 32},
        {"requirement_id": "P4", "label": "all callback traces retain required rows", "passed": trace_fields_complete and len(traces) == 32},
        {"requirement_id": "P5", "label": "all final OpenQASM 3 variants are retained", "passed": sum(row["process_count"] for row in variant_rows) == 32},
        {"requirement_id": "P6", "label": "all pass-sequence comparisons are complete", "passed": divergence["pass_sequence_variant_count"] >= 1},
        {"requirement_id": "P7", "label": "multiple variants receive divergence and gate-level artifacts", "passed": divergence_complete and diff_complete},
        {"requirement_id": "P8", "label": "one, two, or more variants remain valid diagnostic outcomes", "passed": len(variant_rows) >= 1},
        {"requirement_id": "P9", "label": "no simulation or sampling is performed", "passed": summary["simulation_execution_count"] == summary["total_simulated_shots"] == 0},
        {"requirement_id": "P10", "label": "no mechanism, bug, hardware, advantage, BQP, solved-frontier, or credit claim", "passed": True},
    ]
    summary["acceptance_conditions_passed"] = sum(row["passed"] for row in acceptance)
    summary["acceptance_conditions_failed"] = sum(not row["passed"] for row in acceptance)
    summary["global_acceptance"] = all(row["passed"] for row in acceptance)
    result = {
        "title": "B4/B8 R156 transpiler variant capture",
        "version": 0,
        "method": METHOD,
        "status": "transpiler_variant_capture_diagnostic_complete" if summary["global_acceptance"] else "transpiler_variant_capture_diagnostic_incomplete",
        "model_status": "pass_level_localization_without_compiler_mechanism_overclaim",
        "generated_at_unix": int(time.time()),
        "source_target_id": "T-B4-002bu/T-B8-003by/T-B10-009bm",
        "upstream_target_id": "T-B4-002bt/T-B8-003bx/T-B10-009bl",
        "summary": summary,
        "variant_summary": {
            key: value
            for key, value in variant_summary.items()
            if key not in {"process_artifacts", "variant_summary_payload_hash"}
        },
        "pass_divergence": {
            key: value
            for key, value in divergence.items()
            if key not in {"variant_pair_rows", "pass_divergence_payload_hash"}
        },
        "acceptance_conditions": acceptance,
        "requirements": requirements,
        "requirement_count": 10,
        "requirements_passed": sum(row["passed"] for row in requirements),
        "requirements_failed": sum(not row["passed"] for row in requirements),
        "failed_requirement_ids": [row["requirement_id"] for row in requirements if not row["passed"]],
        "artifacts": {
            "protocol": PROTOCOL_PATH,
            "contract": CONTRACT_PATH,
            "result": RESULT_PATH,
            "markdown_report": REPORT_PATH,
            "process_artifacts": process_artifacts,
            "variant_summary": VARIANT_SUMMARY_PATH,
            "pass_divergence": PASS_DIVERGENCE_PATH,
            "gate_level_diff": GATE_DIFF_PATH,
            "verifier_transcript": TRANSCRIPT_PATH,
        },
        "claim_boundary": {
            "what_is_supported": "one preregistered pass-level diagnostic over the public R155 FakeNairobiV2 trial-21 automatic compilation",
            "what_is_not_supported": "a lower-level compiler mechanism or Qiskit-bug claim from pass correlation alone, new hidden evidence, simulation or hardware performance, transfer, route advantage, quantum advantage, BQP separation, solved B4/B8/B10, or new credit",
        },
    }
    result["payload_hash"] = canonical_hash(result)
    transcript = {
        "contract_sha256": CONTRACT_SHA256,
        "protocol_payload_hash": PROTOCOL_PAYLOAD_HASH,
        "variant_summary_payload_hash": variant_summary[
            "variant_summary_payload_hash"
        ],
        "pass_divergence_payload_hash": divergence[
            "pass_divergence_payload_hash"
        ],
        "gate_level_diff_payload_hash": diff["gate_level_diff_payload_hash"],
        "result_payload_hash": result["payload_hash"],
        "acceptance_conditions": acceptance,
        "requirements": requirements,
        "global_acceptance": summary["global_acceptance"],
    }
    write_json(root / TRANSCRIPT_PATH, transcript)
    write_json(root / RESULT_PATH, result)
    (root / REPORT_PATH).write_text(report(result), encoding="utf-8")
    return result


def report(result: dict) -> str:
    summary = result["summary"]
    divergence = result["pass_divergence"]
    variant_lines = "\n".join(
        f"- `{row['final_qasm_sha256']}`: {row['process_count']} processes; known R155 variant `{str(row['known_r155_variant']).lower()}`; size/depth `{row['circuit_size']}` / `{row['circuit_depth']}`."
        for row in result["variant_summary"]["variant_rows"]
    )
    condition_lines = "\n".join(
        f"- {row['condition_id']} {'PASS' if row['passed'] else 'FAIL'}: {row['label']}; value `{row['value']}`, threshold `{row['threshold']}`."
        for row in result["acceptance_conditions"]
    )
    return f"""# B4/B8 R156 Transpiler Variant Capture

- Diagnostic completion: **{'ACCEPT' if summary['global_acceptance'] else 'INCOMPLETE'}**
- Processes / compilations: `{summary['process_count']}` / `{summary['compilation_count']}`
- Callback traces / rows: `{summary['callback_trace_count']}` / `{summary['callback_trace_row_count']}`
- Trace-row range: `{summary['minimum_trace_row_count']}` - `{summary['maximum_trace_row_count']}`
- Final variants: `{summary['final_variant_count']}`
- Known R155 variants reproduced: `{str(summary['known_r155_variants_reproduced']).lower()}`
- Unknown variants: `{summary['unknown_variant_count_observed']}`
- Pass-sequence variants: `{summary['pass_sequence_variant_count']}`
- Simulation executions / shots: `0` / `0`
- Conditions passed / failed: `{summary['acceptance_conditions_passed']}` / `{summary['acceptance_conditions_failed']}`
- New hidden seeds / new credit: `0` / `0`

## Final Variants

{variant_lines}

## First Observed Divergence

- Circuit: `{divergence['first_circuit_divergence']}`
- Bounded property set: `{divergence['first_property_divergence']}`
- All pass sequences identical: `{str(divergence['all_pass_sequences_identical']).lower()}`
- All variant-pair sequences aligned: `{str(divergence['all_variant_pair_pass_sequences_aligned']).lower()}`

## Acceptance Conditions

{condition_lines}

## Claim Boundary

R156 localizes the first observed divergence in complete callback traces for one
public seeded compilation row. A named pass at the first divergent callback is
an observation boundary, not proof that the pass is the lower-level mechanism
or that Qiskit has a confirmed bug. The result makes no hidden-evidence,
simulation-performance, hardware, transfer, route-advantage, quantum-advantage,
BQP, solved-frontier, or research-credit claim.
"""


def orchestrate(root: Path, protocol_payload: dict, contract: dict) -> dict:
    if (root / RESULT_PATH).exists() or (root / REPORT_PATH).exists():
        raise ValueError("R156 final evidence already exists; refusing to overwrite")
    protocol = protocol_payload["protocol"]
    environment = dict(os.environ)
    environment.update(protocol["process_environment"])
    script = Path(__file__).resolve()
    for process_index in range(protocol["process_count"]):
        trace_rel, manifest_rel, qasm_rel = process_paths(process_index)
        existing = [root / trace_rel, root / manifest_rel, root / qasm_rel]
        if all(path.exists() for path in existing):
            continue
        if any(path.exists() for path in existing):
            raise ValueError(f"R156 partial worker evidence exists: {process_index}")
        subprocess.run(
            [
                sys.executable,
                str(script),
                "--root",
                str(root),
                "--worker",
                str(process_index),
            ],
            check=True,
            cwd=root,
            env=environment,
        )
    return aggregate(root, protocol_payload, contract)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--worker", type=int)
    args = parser.parse_args()
    root = args.root.resolve()
    protocol_payload = json.loads((root / PROTOCOL_PATH).read_text())
    contract = json.loads((root / CONTRACT_PATH).read_text())
    validate_bindings(root, contract, protocol_payload)
    if args.worker is not None:
        if args.worker < 0 or args.worker >= protocol_payload["protocol"]["process_count"]:
            raise ValueError("R156 worker index out of range")
        manifest = execute_worker(root, args.worker, protocol_payload)
        print(json.dumps({"process_index": args.worker, "manifest_payload_hash": manifest["manifest_payload_hash"]}, sort_keys=True))
        return 0
    result = orchestrate(root, protocol_payload, contract)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["summary"]["global_acceptance"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
