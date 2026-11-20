#!/usr/bin/env python3
"""Audit the compact accepted-corpus batch trace and its boundary examples."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRACE = ROOT / "results/B2_B7_P023_d6_microblossom_batch_trace_v1.json"


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def require(condition: bool, label: str, checks: list[dict[str, Any]]) -> None:
    checks.append({"label": label, "pass": bool(condition)})
    if not condition:
        raise AssertionError(label)


def audit_example(
    label: str,
    record: dict[str, Any],
    image: dict[str, Any],
    expected_count: int,
    checks: list[dict[str, Any]],
) -> None:
    meta = image["qec_image_metadata"]
    edges = image["weighted_edges"]
    selected = record["selected_edge_indices"]
    updates = record["updates"]
    require(record["reset_before_batch"] is True, f"{label}: reset", checks)
    require(len(record["syndrome_sha256"]) == 64, f"{label}: syndrome hash", checks)
    require(len(record["prediction_sha256"]) == 64, f"{label}: prediction hash", checks)
    require(len(selected) == len(set(selected)), f"{label}: unique selected", checks)
    require(all(isinstance(value, int) and 0 <= value < len(edges) for value in selected),
            f"{label}: selected range", checks)
    require(len(updates) == expected_count, f"{label}: boundary count", checks)
    require(len({row[0] for row in updates}) == len(updates),
            f"{label}: unique update targets", checks)
    rules = {
        row["source_edge_index"]: row["targets"]
        for row in meta["correlation_rules"]
    }
    base = {
        row["edge_index"]: row["base_half_weight"]
        for row in meta["fault_ids_and_weights_by_edge"]
    }
    keys = {
        row["edge_index"]: tuple(row["key"])
        for row in meta["fault_ids_and_weights_by_edge"]
    }
    replacements: dict[int, int] = {}
    for source in selected:
        for target in rules.get(source, []):
            edge_index = target["target_edge_index"]
            weight = target["replacement_hardware_weight"]
            current = replacements.get(edge_index, base[edge_index])
            if weight < current:
                replacements[edge_index] = weight
    expected = [
        [edge_index, replacements[edge_index]]
        for edge_index in sorted(replacements, key=lambda index: keys[index])
    ]
    require(updates == expected, f"{label}: rule-table aggregation", checks)
    require(all(0 <= edge_index < len(edges) and 0 <= weight < base[edge_index]
                for edge_index, weight in updates), f"{label}: strict lowering", checks)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    args = parser.parse_args()
    trace = json.loads(args.trace.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []
    evidence = copy.deepcopy(trace)
    evidence_id = evidence.pop("evidence_id")
    require(sha_bytes(compact(evidence)) == evidence_id, "evidence id", checks)
    require(trace["scope"] == ["021/B7", "022/B2", "023"], "strict scope", checks)
    source_path = ROOT / trace["source_result"]
    manifest_path = ROOT / trace["image_manifest"]
    require(sha_path(source_path) == trace["source_result_sha256"], "source hash", checks)
    require(sha_path(manifest_path) == trace["image_manifest_sha256"], "manifest hash", checks)
    source = json.loads(source_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["evidence_id"] == trace["image_evidence_id"], "image evidence id", checks)
    require(trace["fresh_stochastic_samples_observed"] == 0, "zero fresh samples", checks)
    source_rows = {row["basis"]: row for row in source["basis_rows"]}
    corpora = {row["basis"]: row for row in source["corpora"]}
    manifest_rows = {(row["basis"], row["phase"]): row for row in manifest["images"]}
    require({row["basis"] for row in trace["basis_rows"]} == {"x", "z"},
            "X/Z rows", checks)
    for row in trace["basis_rows"]:
        basis = row["basis"]
        require(row["shots"] == 1024 and row["windows_per_shot"] == 164 and
                row["window_batches"] == 167936, f"{basis}: coverage", checks)
        require(row["corpus_sha256"] == corpora[basis]["corpus_sha256"],
                f"{basis}: corpus hash", checks)
        require(row["candidate_prediction_sha256"] ==
                source_rows[basis]["candidate_prediction_sha256"],
                f"{basis}: prediction hash", checks)
        require(row["hardware_update_edges"] ==
                source_rows[basis]["controller_payload"]["actually_lowered_replacement_edges"],
                f"{basis}: accepted update distribution", checks)
        require(row["commit_residual_failures"] == 0 and
                row["final_residual_failure_shots"] == 0,
                f"{basis}: residuals", checks)
        require(len(row["trace_sha256"]) == 64 and
                len(row["update_batch_occurrence_sha256"]) == 64,
                f"{basis}: trace digests", checks)
        phase_observations = {
            phase: int(dist["observations"])
            for phase, dist in row["phase_hardware_update_edges"].items()
        }
        require(phase_observations == {"opening": 1024, "steady": 165888, "closing": 1024},
                f"{basis}: phase coverage", checks)
        distribution = row["hardware_update_edges"]
        expected_labels = {"zero", "p50", "p99", "maximum"}
        require(set(row["representative_batches"]) == expected_labels,
                f"{basis}: representative labels", checks)
        counts = {
            "zero": 0,
            "p50": int(distribution["p50"]),
            "p99": int(distribution["p99"]),
            "maximum": int(distribution["maximum"]),
        }
        for boundary, record in row["representative_batches"].items():
            phase = record["phase"]
            require(phase == ("opening" if record["window"] == 0 else
                              "closing" if record["window"] == 163 else "steady"),
                    f"{basis}/{boundary}: phase index", checks)
            image_path = ROOT / manifest_rows[(basis, phase)]["path"]
            image = json.loads(image_path.read_text(encoding="utf-8"))
            audit_example(
                f"{basis}/{boundary}", record, image, counts[boundary], checks
            )
        bus = row["hardware_update_bus_bits"]
        require(bus["p99"] == distribution["p99"] * 32 and
                bus["maximum"] == distribution["maximum"] * 32,
                f"{basis}: bus-bit accounting", checks)
    acceptance = trace["acceptance"]
    require(acceptance["rtl_batch_replay_completed"] is False and
            acceptance["rtl_corrections_compared"] is False,
            "no RTL replay overclaim", checks)
    require(acceptance["p99_le_1us"] is False and
            acceptance["miss_rate_le_1pct"] is False,
            "no timing overclaim", checks)
    require(acceptance["full_b2"] is False and
            acceptance["scalable_p023"] is False and
            acceptance["b7_resource_credit"] == 0,
            "downstream credit closed", checks)
    print(json.dumps({
        "classification": "accepted_batch_trace_audit_pass",
        "evidence_id": evidence_id,
        "checks_passed": sum(row["pass"] for row in checks),
        "checks_total": len(checks),
        "checks": checks,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
