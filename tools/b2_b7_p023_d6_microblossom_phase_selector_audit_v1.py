#!/usr/bin/env python3
"""Audit opening/closing resident-selector RTL replay evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_phase_selector_rtl_v1.json"
BATCH = re.compile(
    r"PHASE_SELECTOR_BATCH_PASS basis=(x|z) phase=(opening|closing) "
    r"boundary=(maximum|p50|p99|zero) selectors=(\d+) updates=(\d+) "
    r"checked_edges=(\d+) axi_write_span_slow_cycles=(\d+)"
)
ARTIFACT = re.compile(
    r"PHASE_RTL_ARTIFACT basis=(x|z) phase=(opening|closing) "
    r"verilog_bytes=(\d+) verilog_sha256=([0-9a-f]{64}) "
    r"vvp_bytes=(\d+) vvp_sha256=([0-9a-f]{64})"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def require(condition: bool, label: str, checks: list[dict[str, Any]]) -> None:
    checks.append({"label": label, "pass": bool(condition)})
    if not condition:
        raise AssertionError(label)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    args = parser.parse_args()
    result = json.loads(args.result.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    without_id = dict(result)
    evidence_id = without_id.pop("evidence_id")
    require(
        evidence_id == hashlib.sha256(compact(without_id)).hexdigest(),
        "canonical evidence id",
        checks,
    )
    require(result["scope"] == ["021/B7", "022/B2", "023"], "strict scope", checks)

    source = result["source"]
    for key in ("phase_batch_trace", "simulation_transcript", "simulation_harness"):
        path = ROOT / source[key]
        require(path.is_file(), f"{key}: exists", checks)
        require(sha(path) == source[f"{key}_sha256"], f"{key}: hash", checks)
    implementation = result["implementation"]
    for key in ("prerequisite_dynamic_weight_patch", "resident_selector_patch"):
        path = ROOT / implementation[key]
        require(path.is_file(), f"{key}: exists", checks)
        require(sha(path) == implementation[f"{key}_sha256"], f"{key}: hash", checks)
    require(
        implementation["prerequisite_dynamic_weight_patch_sha256"]
        == "990beb9fc86329960a6eef88b9f88b601f5807f0e2ae2abd71acc0d3671e27d5",
        "published dynamic patch unchanged",
        checks,
    )
    require(
        implementation["resident_selector_patch_sha256"]
        == "cd2f7a819a7fea699f07c504d5ae5c88dfe447dbe3b9515ebd580aec4c55b511",
        "published selector patch unchanged",
        checks,
    )

    harness = (ROOT / source["simulation_harness"]).read_text(encoding="utf-8")
    require("driver.write_64(0x4000" in harness, "harness selector window", checks)
    require(
        "math.min(reconstructed(targetEdgeIndex), replacementWeight)" in harness,
        "harness independent min reconstruction",
        checks,
    )

    transcript = (ROOT / source["simulation_transcript"]).read_text(encoding="utf-8")
    measured = {
        (basis, phase, boundary): {
            "selectors": int(selectors),
            "updates": int(updates),
            "edges": int(edges),
            "cycles": int(cycles),
        }
        for basis, phase, boundary, selectors, updates, edges, cycles
        in BATCH.findall(transcript)
    }
    artifacts = {
        (basis, phase): {
            "generated_verilog_bytes": int(verilog_bytes),
            "generated_verilog_sha256": verilog_sha,
            "generated_vvp_bytes": int(vvp_bytes),
            "generated_vvp_sha256": vvp_sha,
        }
        for basis, phase, verilog_bytes, verilog_sha, vvp_bytes, vvp_sha
        in ARTIFACT.findall(transcript)
    }
    require(len(measured) == 16, "sixteen unique transcript rows", checks)
    require(len(artifacts) == 4, "four unique artifact rows", checks)
    require("mismatches=0" in transcript and "simulation=PASS" in transcript,
            "transcript pass boundary", checks)

    trace = json.loads((ROOT / source["phase_batch_trace"]).read_text(encoding="utf-8"))
    require(
        trace["evidence_id"] == source["phase_batch_trace_evidence_id"],
        "phase trace evidence binding",
        checks,
    )
    require(trace["fresh_stochastic_samples_observed"] == 0,
            "zero fresh stochastic samples", checks)
    require(
        trace["acceptance"]["accepted_corpus_hashes_reproduced"]
        and trace["acceptance"]["accepted_candidate_prediction_hashes_reproduced"],
        "accepted corpus and predictions reproduced",
        checks,
    )
    trace_rows = {row["basis"]: row for row in trace["basis_rows"]}
    result_rows = {
        (row["basis"], row["phase"]): row
        for row in result["rtl_generation"]["phase_rows"]
    }
    require(len(result_rows) == 4, "four unique result phase rows", checks)

    total_checks = 0
    p99_projection: dict[str, int] = {}
    p99_representative: dict[str, int] = {}
    for basis in ("x", "z"):
        phases = {row["phase"]: row for row in trace_rows[basis]["phases"]}
        for phase in ("opening", "closing"):
            key = (basis, phase)
            row = result_rows[key]
            image_path = ROOT / row["image"]
            require(image_path.is_file(), f"{basis}/{phase}: image exists", checks)
            require(sha(image_path) == row["image_sha256"],
                    f"{basis}/{phase}: image hash", checks)
            image = json.loads(image_path.read_text(encoding="utf-8"))
            metadata = image["qec_image_metadata"]
            require(
                metadata["basis"] == basis and metadata["phase"] == phase,
                f"{basis}/{phase}: image identity",
                checks,
            )
            rules: dict[int, list[tuple[int, int]]] = {}
            active = 0
            all_even = True
            all_exact = True
            for source_row in metadata["correlation_rules"]:
                source_index = int(source_row["source_edge_index"])
                for target in source_row["targets"]:
                    even = int(target["replacement_even_weight"])
                    half = int(target["replacement_half_weight"])
                    hardware = int(target["replacement_hardware_weight"])
                    all_even = all_even and even % 2 == 0
                    all_exact = all_exact and even // 2 == half == hardware
                    if target["lowers_base"]:
                        active += 1
                        rules.setdefault(source_index, []).append(
                            (int(target["target_edge_index"]), hardware)
                        )
            require(all_even and all_exact,
                    f"{basis}/{phase}: exact rule normalization", checks)
            require(active == int(metadata["active_lowering_rules"]) == row["active_resident_rules"],
                    f"{basis}/{phase}: active rule count", checks)
            require(len(image["weighted_edges"]) == row["graph_edges"],
                    f"{basis}/{phase}: graph edge count", checks)
            base = [int(edge["w"]) for edge in image["weighted_edges"]]
            phase_trace = phases[phase]
            result_reps = {
                rep["boundary"]: rep for rep in row["representative_replay"]
            }
            for boundary in ("zero", "p50", "p99", "maximum"):
                record = phase_trace["representative_batches"][boundary]
                expected = {int(edge): int(weight) for edge, weight in record["updates"]}
                reconstructed = list(base)
                for source_index in record["selected_edge_indices"]:
                    for target_index, replacement in rules.get(int(source_index), []):
                        reconstructed[target_index] = min(
                            reconstructed[target_index], replacement
                        )
                reconstructed_updates = {
                    index: weight
                    for index, weight in enumerate(reconstructed)
                    if weight != base[index]
                }
                require(
                    reconstructed_updates == expected,
                    f"{basis}/{phase}/{boundary}: independent reconstruction",
                    checks,
                )
                observed = measured[(basis, phase, boundary)]
                result_rep = result_reps[boundary]
                require(
                    observed["selectors"]
                    == len(record["selected_edge_indices"])
                    == result_rep["selected_source_edges"],
                    f"{basis}/{phase}/{boundary}: selectors",
                    checks,
                )
                require(
                    observed["updates"] == len(expected)
                    == result_rep["expected_weight_updates"],
                    f"{basis}/{phase}/{boundary}: updates",
                    checks,
                )
                require(
                    observed["edges"] == len(base) == result_rep["checked_edges"],
                    f"{basis}/{phase}/{boundary}: edge coverage",
                    checks,
                )
                require(
                    observed["cycles"] == 2 * observed["selectors"]
                    == result_rep["axi_write_span_slow_cycles"],
                    f"{basis}/{phase}/{boundary}: cycle span",
                    checks,
                )
                require(result_rep["pass"] is True,
                        f"{basis}/{phase}/{boundary}: pass flag", checks)
                total_checks += observed["edges"]
            require(
                all(row[name] == value for name, value in artifacts[key].items()),
                f"{basis}/{phase}: artifact binding",
                checks,
            )
            label = f"{basis}_{phase}"
            p99_projection[label] = int(phase_trace["selected_source_edges"]["p99"]) * 2
            p99_representative[label] = measured[(basis, phase, "p99")]["cycles"]

    replay = result["representative_rtl_replay"]
    require(
        replay["phase_images"] == 4
        and replay["batches_run"] == replay["batches_passed"] == 16
        and replay["batches_failed"] == 0,
        "all phase replay batches pass",
        checks,
    )
    require(
        replay["full_edge_state_checks"]
        == replay["full_edge_state_checks_passed"]
        == total_checks == 53008
        and replay["mismatches"] == 0,
        "full phase edge-state coverage",
        checks,
    )
    transport = result["transport"]
    require(transport["measured_slow_cycles_per_selector_command"] == 2,
            "two-cycle selector contract", checks)
    require(
        transport["representative_p99_slow_cycles"] == p99_representative,
        "representative p99 binding",
        checks,
    )
    require(
        transport["accepted_distribution_p99_update_only_slow_cycles"]
        == p99_projection
        == {"x_opening": 26, "x_closing": 30, "z_opening": 26, "z_closing": 32},
        "accepted distribution p99 projection",
        checks,
    )
    require(
        transport["distribution_cycle_classification"]
        == "projected_from_all_4096_accepted_phase_batches_not_full_rtl_replay",
        "projection boundary",
        checks,
    )

    acceptance = result["acceptance"]
    require(
        acceptance["opening_closing_representative_edge_state_rtl_replay"] is True,
        "phase representative correctness credit",
        checks,
    )
    require(
        acceptance["runtime_phase_switching_implemented"] is False
        and acceptance["all_accepted_phase_batches_replayed_in_rtl"] is False
        and acceptance["rtl_corrections_compared"] is False,
        "integration scope boundary",
        checks,
    )
    require(
        acceptance["fpga_fmax_measured"] is False
        and acceptance["lut_bram_measured"] is False
        and acceptance["full_update_plus_decode_p99_cycles_measured"] is False
        and acceptance["p99_le_1us"] is False
        and acceptance["miss_rate_le_1pct"] is False,
        "timing and resource boundary",
        checks,
    )
    require(
        acceptance["full_b2"] is False
        and acceptance["scalable_p023"] is False
        and acceptance["b7_resource_credit"] == 0,
        "downstream credit closed",
        checks,
    )

    print(json.dumps({
        "classification": "phase_selector_rtl_evidence_audit_pass",
        "checks_passed": sum(row["pass"] for row in checks),
        "checks_total": len(checks),
        "checks": checks,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
