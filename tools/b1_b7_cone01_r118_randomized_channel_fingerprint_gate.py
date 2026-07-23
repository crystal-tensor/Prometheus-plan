#!/usr/bin/env python3
"""T-B1-004hp/T-B7-016y: stress the R116 candidate with independent fingerprints."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from pathlib import Path

import numpy as np

import b1_b7_cone01_r117_independent_numpy_replay_gate as r117


METHOD = "b1_b7_cone01_r118_randomized_channel_fingerprint_gate_v0"
STATUS = "cone01_r118_randomized_channel_fingerprint_160_probe_accepted"
MODEL_STATUS = "independent_numpy_fingerprint_passes_cross_type_probes_negative_control_detected"
TARGET_ID = "T-B1-004hp/T-B7-016y"
UPSTREAM_TARGET_ID = "T-B1-004ho/T-B7-016x"
SOURCE_PATH = "benchmarks/qasmbench_medium_exact/gcm_h6.qasm"
CANDIDATE_PATH = "results/B1_B7_cone01_R116_measurement_detached_exact_2q_gate/measurement_detached_candidate.qasm"
R116_RESULT_PATH = "results/B1_B7_cone01_R116_measurement_detached_exact_2q_gate_v0.json"
OUT_DIR = "results/B1_B7_cone01_R118_randomized_channel_fingerprint_gate"
RESULT_PATH = "results/B1_B7_cone01_R118_randomized_channel_fingerprint_gate_v0.json"
REPORT_PATH = "research/B1_B7_cone01_R118_randomized_channel_fingerprint_gate.md"
PROBE_SEED = 118
PROBE_TOLERANCE = 1e-9


def stable_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_probe_set(qubit_count: int) -> list[tuple[str, np.ndarray]]:
    dimension = 1 << qubit_count
    rng = np.random.default_rng(PROBE_SEED)
    probes: list[tuple[str, np.ndarray]] = []

    # Cover basis, Haar-like, product, and entangled families with one seed.
    for index in range(32):
        state = np.zeros(dimension, dtype=np.complex128)
        state[index * 257 % dimension] = 1.0
        probes.append((f"basis_{index}", state))
    for index in range(64):
        state = rng.normal(size=dimension) + 1j * rng.normal(size=dimension)
        probes.append((f"haar_{index}", state / np.linalg.norm(state)))
    for index in range(32):
        state = np.array([1.0 + 0j], dtype=np.complex128)
        for _ in range(qubit_count):
            theta = rng.uniform(0, math.pi)
            phase = rng.uniform(-math.pi, math.pi)
            local = np.array([math.cos(theta / 2), np.exp(1j * phase) * math.sin(theta / 2)], dtype=np.complex128)
            state = np.kron(state, local)
        probes.append((f"product_{index}", state / np.linalg.norm(state)))
    for index in range(16):
        state = np.zeros(dimension, dtype=np.complex128)
        phase = np.exp(1j * rng.uniform(-math.pi, math.pi))
        state[0] = 1 / math.sqrt(2)
        state[dimension - 1] = phase / math.sqrt(2)
        probes.append((f"ghz_endpoint_{index}", state))
    for index in range(16):
        state = rng.normal(size=dimension) + 1j * rng.normal(size=dimension)
        state[0] += 3.0
        probes.append((f"biased_{index}", state / np.linalg.norm(state)))
    return probes


def fingerprint(source: Path, candidate: Path, probes: list[tuple[str, np.ndarray]]) -> list[dict]:
    rows = []
    for name, initial in probes:
        source_state, _, _ = r117.simulate(source, initial)
        candidate_state, _, _ = r117.simulate(candidate, initial)
        value = r117.fidelity(source_state, candidate_state)
        rows.append({"name": name, "fidelity": value, "fidelity_deficit": max(0.0, 1.0 - value)})
    return rows


def report(payload: dict) -> str:
    summary = payload["summary"]
    requirements = "\n".join(
        f"- `{item['requirement_id']}` {'PASS' if item['passed'] else 'FAIL'}: {item['label']}"
        for item in payload["requirements"]
    )
    return f"""# B1/B7 Cone01 R118 Randomized Channel Fingerprint Gate

## Summary

- Target: `{TARGET_ID}`
- Upstream target: `{UPSTREAM_TARGET_ID}`
- Method: `{METHOD}`
- Status: `{STATUS}`
- Source/Candidate CX: `{summary['source_two_qubit_gate_count']} -> {summary['candidate_two_qubit_gate_count']}`
- Probe families: `{summary['probe_family_counts']}`
- Candidate probes: `{summary['probe_passed']}/{summary['probe_count']}`
- Maximum fidelity deficit: `{summary['max_fidelity_deficit']}`
- Negative-control failures: `{summary['negative_control_failed']}/{summary['negative_control_count']}`
- B7 credit: `{summary['b7_credit_delta']}`

R118 uses the independent NumPy gate engine, not Qiskit compilation, to
fingerprint the R116 source/candidate pair over basis, Haar-like, product,
endpoint-entangled, and biased input states. A deliberately modified candidate
is required to fail the same harness, preventing a vacuous all-pass result.

This is stronger finite numerical evidence, not a symbolic or formal proof of
arbitrary-input unitary equality. It does not establish mid-circuit
measurement semantics, hardware layout improvement, T-resource reduction, or
B7 credit.

## Requirements

{requirements}

## Claim Boundary

Supported: R116 survives a 160-probe cross-type independent NumPy channel
fingerprint and the negative control is detected. Not supported: an exact
arbitrary-input theorem, hardware evidence, T-resource reduction, or B7
ledger credit.
"""


def run_gate(root: Path) -> dict:
    root = root.resolve()
    source = root / SOURCE_PATH
    candidate = root / CANDIDATE_PATH
    r116 = json.loads((root / R116_RESULT_PATH).read_text(encoding="utf-8"))
    if r116.get("status") != "cone01_r116_measurement_detached_exact_2q_accepted_finite_probe":
        raise ValueError("R118 requires the accepted R116 result")
    out = root / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    source_qregs, source_ops = r117.parse_qasm(source)
    candidate_qregs, candidate_ops = r117.parse_qasm(candidate)
    if sum(source_qregs.values()) != sum(candidate_qregs.values()):
        raise ValueError("source and candidate qubit counts differ")
    probes = make_probe_set(sum(source_qregs.values()))
    rows = fingerprint(source, candidate, probes)
    probe_payload = {
        "engine": "numpy_independent_statevector_v0",
        "seed": PROBE_SEED,
        "probe_count": len(rows),
        "probe_tolerance": PROBE_TOLERANCE,
        "family_counts": {family: sum(row["name"].startswith(family) for row in rows) for family in ["basis", "haar", "product", "ghz_endpoint", "biased"]},
        "passed": sum(row["fidelity_deficit"] <= PROBE_TOLERANCE for row in rows),
        "failed": sum(row["fidelity_deficit"] > PROBE_TOLERANCE for row in rows),
        "max_fidelity_deficit": max(row["fidelity_deficit"] for row in rows),
        "rows": rows,
    }
    probe_path = out / "channel_fingerprint.json"
    write_json(probe_path, probe_payload)

    negative_path = out / "negative_control_candidate.qasm"
    negative_text = candidate.read_text(encoding="utf-8").replace("measure q[0] -> c[0];", "x q[0];\nmeasure q[0] -> c[0];", 1)
    negative_path.write_text(negative_text, encoding="utf-8")
    negative_probes = probes[:16]
    negative_rows = fingerprint(source, negative_path, negative_probes)
    negative_payload = {
        "engine": "numpy_independent_statevector_v0",
        "control": "inserted x q[0] immediately before terminal measurement",
        "probe_count": len(negative_rows),
        "failed": sum(row["fidelity_deficit"] > PROBE_TOLERANCE for row in negative_rows),
        "max_fidelity_deficit": max(row["fidelity_deficit"] for row in negative_rows),
        "rows": negative_rows,
    }
    negative_result_path = out / "negative_control.json"
    write_json(negative_result_path, negative_payload)
    source_lines = r117.measurement_lines(source)
    candidate_lines = r117.measurement_lines(candidate)
    source_cx = sum(op["gate"] == "cx" for op in source_ops)
    candidate_cx = sum(op["gate"] == "cx" for op in candidate_ops)
    summary = {
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "engine": "numpy_independent_statevector_v0",
        "source_two_qubit_gate_count": source_cx,
        "candidate_two_qubit_gate_count": candidate_cx,
        "two_qubit_gate_delta": candidate_cx - source_cx,
        "two_qubit_reduction_pct": (source_cx - candidate_cx) / source_cx * 100 if source_cx else 0,
        "probe_count": probe_payload["probe_count"],
        "probe_passed": probe_payload["passed"],
        "probe_failed": probe_payload["failed"],
        "probe_family_counts": probe_payload["family_counts"],
        "max_fidelity_deficit": probe_payload["max_fidelity_deficit"],
        "negative_control_count": negative_payload["probe_count"],
        "negative_control_failed": negative_payload["failed"],
        "negative_control_max_fidelity_deficit": negative_payload["max_fidelity_deficit"],
        "measurement_map_preserved": source_lines == candidate_lines and bool(source_lines),
        "b7_credit_delta": 0,
        "counter_delta": 0,
        "new_credit_delta": 0,
    }
    requirements = [
        {"requirement_id": "P1", "label": "accepted R116 artifact is the input", "passed": True, "evidence": {"r116_status": r116["status"]}},
        {"requirement_id": "P2", "label": "independent NumPy engine is used without Qiskit compilation", "passed": True, "evidence": {"engine": summary["engine"], "qiskit_compiler_called": False}},
        {"requirement_id": "P3", "label": "candidate has a nonzero two-qubit reduction", "passed": summary["two_qubit_gate_delta"] < 0, "evidence": {"source": source_cx, "candidate": candidate_cx}},
        {"requirement_id": "P4", "label": "cross-type probe set has the declared 160 rows", "passed": summary["probe_count"] == 160 and sum(summary["probe_family_counts"].values()) == 160, "evidence": {"count": summary["probe_count"], "families": summary["probe_family_counts"]}},
        {"requirement_id": "P5", "label": "all candidate fingerprint probes pass", "passed": summary["probe_passed"] == summary["probe_count"] and summary["probe_failed"] == 0, "evidence": {"passed": summary["probe_passed"], "failed": summary["probe_failed"]}},
        {"requirement_id": "P6", "label": "candidate fingerprint stays within tolerance", "passed": summary["max_fidelity_deficit"] <= PROBE_TOLERANCE, "evidence": {"max_deficit": summary["max_fidelity_deficit"], "tolerance": PROBE_TOLERANCE}},
        {"requirement_id": "P7", "label": "negative control is detected by the same harness", "passed": summary["negative_control_failed"] > 0, "evidence": {"failed": summary["negative_control_failed"], "count": summary["negative_control_count"]}},
        {"requirement_id": "P8", "label": "source terminal measurement map is preserved", "passed": summary["measurement_map_preserved"], "evidence": {"source": source_lines, "candidate": candidate_lines}},
        {"requirement_id": "P9", "label": "fingerprint and negative-control artifacts are materialized", "passed": probe_path.exists() and negative_result_path.exists(), "evidence": {"fingerprint": str(probe_path.relative_to(root)), "negative_control": str(negative_result_path.relative_to(root))}},
        {"requirement_id": "P10", "label": "B7 credit remains zero", "passed": summary["b7_credit_delta"] == 0, "evidence": {"b7_credit_delta": 0}},
        {"requirement_id": "P11", "label": "claim boundary excludes formal arbitrary-input proof", "passed": True, "evidence": {"model_status": MODEL_STATUS}},
        {"requirement_id": "P12", "label": "source and candidate have the same qubit count", "passed": sum(source_qregs.values()) == sum(candidate_qregs.values()), "evidence": {"source": sum(source_qregs.values()), "candidate": sum(candidate_qregs.values())}},
    ]
    failed = [item["requirement_id"] for item in requirements if not item["passed"]]
    payload = {
        "title": "B1/B7 cone01 R118 randomized channel fingerprint gate",
        "version": "0.1",
        "generated_at_unix": int(time.time()),
        "method": METHOD,
        "status": STATUS if not failed else "cone01_r118_randomized_channel_fingerprint_failed",
        "model_status": MODEL_STATUS,
        "source_target_id": TARGET_ID,
        "upstream_target_id": UPSTREAM_TARGET_ID,
        "source_path": SOURCE_PATH,
        "candidate_path": CANDIDATE_PATH,
        "requirements": requirements,
        "requirement_count": len(requirements),
        "requirements_passed": len(requirements) - len(failed),
        "requirements_failed": len(failed),
        "summary": summary,
        "artifacts": {"channel_fingerprint": str(probe_path.relative_to(root)), "negative_control": str(negative_result_path.relative_to(root)), "r116_result": R116_RESULT_PATH},
        "claim_boundary": {"what_is_supported": "R116 survives a 160-probe cross-type independent NumPy channel fingerprint and the same harness detects an inserted-X negative control.", "what_is_not_supported": "Exact arbitrary-input unitary proof, mid-circuit measurement semantics, hardware layout improvement, T-resource reduction, or B7 credit.", "next_gate": "Obtain a symbolic/compositional certificate or an externally generated compiler candidate before any broader B1/B7 promotion."},
    }
    payload["payload_hash"] = stable_hash(payload)
    write_json(root / RESULT_PATH, payload)
    (root / REPORT_PATH).write_text(report(payload), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    payload = run_gate(Path(args.repo_root))
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    if payload["requirements_failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
