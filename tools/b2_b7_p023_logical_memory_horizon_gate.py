#!/usr/bin/env python3
"""Build the frozen #021/B7, #022/B2, #023 logical-memory horizon gate."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK = ROOT / "benchmarks/B2_B7_P023_logical_memory_horizon_gate_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_logical_memory_horizon_gate_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_logical_memory_horizon_gate_v1.md"
DEFAULT_DISCUSSION = ROOT / "research/B2_B7_P023_logical_memory_horizon_discussion_v1.md"
DEFAULT_SOURCE_DIR = ROOT / "results/B2_B7_P023_logical_memory_horizon_source_v1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def rounded(value: float, digits: int = 12) -> float:
    return round(float(value), digits)


def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def normalize_text(value: str) -> str:
    return "\n".join(line.rstrip() for line in value.replace("\r\n", "\n").splitlines()).strip() + "\n"


def write_deterministic_gzip(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            zipped.write(text.encode("utf-8"))


def read_gzip(path: Path) -> str:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return handle.read()


def capture_sources(benchmark: dict[str, Any], source_dir: Path, offline: bool) -> list[dict[str, Any]]:
    captures = []
    for source in benchmark["external_evidence"]:
        path = source_dir / f"{source['id']}.txt.gz"
        if path.exists():
            text = read_gzip(path)
        elif offline:
            raise FileNotFoundError(f"offline capture missing: {path}")
        else:
            request = urllib.request.Request(
                source["capture_url"], headers={"User-Agent": "Prometheus-plan-QEC-horizon-gate/1.0"}
            )
            with urllib.request.urlopen(request, timeout=90) as response:
                text = normalize_text(response.read().decode("utf-8", errors="replace"))
            write_deterministic_gzip(path, text)
        folded = " ".join(text.lower().split())
        fragments = {
            fragment: fragment.lower() in folded
            for fragment in source["required_fragments"]
        }
        captures.append(
            {
                "id": source["id"],
                "origin_url": source["origin_url"],
                "capture_url": source["capture_url"],
                "evidence_class": source["evidence_class"],
                "path": str(path.relative_to(ROOT)),
                "sha256_uncompressed_text": sha256_bytes(text.encode("utf-8")),
                "byte_count_uncompressed": len(text.encode("utf-8")),
                "required_fragment_matches": fragments,
                "all_required_fragments_present": all(fragments.values()),
                "capture_boundary": "normalized text relay of official-origin page; not raw publisher byte identity",
            }
        )
    manifest = {
        "schema_version": "b2_b7_p023_logical_memory_horizon_source_v1",
        "as_of_date": benchmark["as_of_date"],
        "captures": captures,
    }
    (source_dir / "capture_manifest.json").write_text(canonical(manifest), encoding="utf-8")
    return captures


def wilson_upper(failures: int, shots: int, z: float) -> float:
    proportion = failures / shots
    denominator = 1.0 + z * z / shots
    center = proportion + z * z / (2.0 * shots)
    radius = z * math.sqrt(proportion * (1.0 - proportion) / shots + z * z / (4.0 * shots * shots))
    return (center + radius) / denominator


def per_cycle_from_total(total_probability: float, rounds: int) -> float:
    bounded = min(0.5, max(0.0, total_probability))
    return 0.5 * (1.0 - (1.0 - 2.0 * bounded) ** (1.0 / rounds))


def total_from_per_cycle(per_cycle_probability: float, rounds: int) -> float:
    bounded = min(0.5, max(0.0, per_cycle_probability))
    return 0.5 * (1.0 - (1.0 - 2.0 * bounded) ** rounds)


def minimum_zero_failure_shots(target: float, z: float) -> int:
    estimate = math.ceil(z * z * (1.0 - target) / target)
    while wilson_upper(0, estimate, z) > target:
        estimate += 1
    while estimate > 1 and wilson_upper(0, estimate - 1, z) <= target:
        estimate -= 1
    return estimate


def build_result(benchmark_path: Path, source_dir: Path, offline: bool) -> dict[str, Any]:
    benchmark = read_json(benchmark_path)
    inputs = {}
    for name, contract in benchmark["inputs"].items():
        path = ROOT / contract["path"]
        inputs[name] = {"contract": contract, "path": path, "value": read_json(path), "sha256": sha256_path(path)}
    captures = capture_sources(benchmark, source_dir, offline)
    baseline = inputs["b2_memory_baseline"]["value"]
    horizons = benchmark["horizon_contract"]["memory_round_horizons"]
    targets = benchmark["horizon_contract"]["total_logical_failure_targets"]
    z = 1.959963984540054
    projections = []
    for row in sorted(
        baseline["results"],
        key=lambda item: (item["memory_basis"], item["physical_error"], item["distance"]),
    ):
        recomputed_upper = wilson_upper(row["logical_failures"], row["shots"], z)
        per_cycle_upper = per_cycle_from_total(recomputed_upper, row["rounds"])
        for horizon in horizons:
            projected_upper = total_from_per_cycle(per_cycle_upper, horizon)
            projections.append(
                {
                    "memory_basis": row["memory_basis"],
                    "physical_error": row["physical_error"],
                    "distance": row["distance"],
                    "physical_qubits": row["physical_qubits_in_stim_circuit"],
                    "source_rounds": row["rounds"],
                    "source_shots": row["shots"],
                    "source_failures": row["logical_failures"],
                    "source_wilson_95_high": rounded(row["wilson_95_high"]),
                    "recomputed_wilson_95_high": rounded(recomputed_upper),
                    "stationary_per_cycle_upper": rounded(per_cycle_upper),
                    "horizon_rounds": horizon,
                    "direct_horizon_evidence": row["rounds"] >= horizon,
                    "projected_total_failure_upper": rounded(projected_upper),
                    "projection_only": row["rounds"] < horizon,
                    "target_results": {
                        str(target): {
                            "projected_pass": projected_upper <= target,
                            "direct_pass": row["rounds"] >= horizon and recomputed_upper <= target,
                        }
                        for target in targets
                    },
                }
            )
    paired = []
    for horizon in horizons:
        for target in targets:
            groups: dict[tuple[float, int], list[dict[str, Any]]] = {}
            for row in projections:
                if row["horizon_rounds"] == horizon:
                    groups.setdefault((row["physical_error"], row["distance"]), []).append(row)
            for (physical_error, distance), rows in sorted(groups.items()):
                by_basis = {row["memory_basis"]: row for row in rows}
                paired.append(
                    {
                        "physical_error": physical_error,
                        "distance": distance,
                        "horizon_rounds": horizon,
                        "target_total_failure": target,
                        "basis_rows_present": sorted(by_basis),
                        "both_bases_direct_pass": set(by_basis) == {"x", "z"}
                        and all(by_basis[b]["target_results"][str(target)]["direct_pass"] for b in ("x", "z")),
                        "both_bases_projected_pass": set(by_basis) == {"x", "z"}
                        and all(by_basis[b]["target_results"][str(target)]["projected_pass"] for b in ("x", "z")),
                        "credit": "direct" if set(by_basis) == {"x", "z"} and all(by_basis[b]["target_results"][str(target)]["direct_pass"] for b in ("x", "z")) else "none",
                    }
                )
    distance_qubits = {
        row["distance"]: row["physical_qubits_in_stim_circuit"]
        for row in baseline["results"]
    }
    resolution = []
    for target in targets:
        shots = minimum_zero_failure_shots(target, z)
        for horizon in horizons:
            for distance, qubits in sorted(distance_qubits.items()):
                resolution.append(
                    {
                        "target_total_failure": target,
                        "horizon_rounds": horizon,
                        "distance": distance,
                        "physical_qubits": qubits,
                        "minimum_zero_failure_direct_shots": shots,
                        "minimum_qubit_cycles_per_basis": shots * horizon * qubits,
                        "minimum_qubit_cycles_both_bases": 2 * shots * horizon * qubits,
                        "planning_only": True,
                    }
                )
    b7_credit = inputs["b7_calibrated_credit_gate"]["value"]
    direct_1000 = any(
        row["both_bases_direct_pass"] and row["horizon_rounds"] == 1000 and row["target_total_failure"] == 0.01
        for row in paired
    )
    direct_million = any(
        row["both_bases_direct_pass"] and row["horizon_rounds"] == 1000000 and row["target_total_failure"] == 0.01
        for row in paired
    )
    p023_ready = direct_1000 and direct_million
    b2_credit_ready = False
    b7_credit_ready = p023_ready and b2_credit_ready and bool(
        b7_credit.get("claim_boundary", {}).get("b2_calibrated_credit_allowed", False)
    )
    checks = [
        check("scope_exact", benchmark["scope"]["included_catalog_problem_ids"] == [21, 22, 23] and benchmark["scope"]["included_tracks"] == ["B2", "B7"], "Only #021/B7, #022/B2, and #023 are included."),
        check("input_hashes", all(item["sha256"] == item["contract"]["sha256"] for item in inputs.values()), "All four upstream files match the frozen hashes."),
        check("input_statuses", all(item["value"].get("status") == item["contract"]["required_status"] for item in inputs.values()), "All upstream statuses match the contract."),
        check("external_capture_count", len(captures) == 3, f"Captured {len(captures)} external primary-source pages."),
        check("external_semantics", all(row["all_required_fragments_present"] for row in captures), "All frozen source fragments are present."),
        check("baseline_rows", len(baseline["results"]) == 30, f"Baseline rows: {len(baseline['results'])}."),
        check("baseline_axes", {row["distance"] for row in baseline["results"]} == {3, 5, 7} and {row["memory_basis"] for row in baseline["results"]} == {"x", "z"}, "Distances 3/5/7 and both bases are present."),
        check("wilson_reproduction", all(abs(row["source_wilson_95_high"] - row["recomputed_wilson_95_high"]) <= 1e-12 for row in projections), "All Wilson upper bounds reproduce."),
        check("projection_roundtrip", all(abs(total_from_per_cycle(per_cycle_from_total(x, r), r) - x) <= 1e-12 for x, r in [(0.0, 3), (0.001, 5), (0.01, 7), (0.1, 11)]), "Parity-flip projection roundtrip passes."),
        check("projection_count", len(projections) == 120, f"Projection rows: {len(projections)}."),
        check("direct_horizon_absent", not any(row["direct_horizon_evidence"] for row in projections), "No source row directly reaches the minimum 10-round horizon."),
        check("paired_direct_credit_zero", not any(row["both_bases_direct_pass"] for row in paired), "No paired-basis direct horizon earns credit."),
        check("resolution_targets", {row["minimum_zero_failure_direct_shots"] for row in resolution if row["target_total_failure"] == 0.01} == {381} and {row["minimum_zero_failure_direct_shots"] for row in resolution if row["target_total_failure"] == 0.001} == {3838}, "Wilson zero-failure shot floors are 381 and 3,838."),
        check("p023_closed", not p023_ready, "#023 scalable-memory gate remains closed."),
        check("b2_credit_closed", not b2_credit_ready, "B2 low-overhead credit remains closed."),
        check("b7_credit_closed", not b7_credit_ready, "B7 memory-derived resource credit remains zero."),
        check("claim_boundary", not any(benchmark["claim_boundary"][key] for key in ["new_code_claimed", "threshold_claimed", "scalable_quantum_memory_claimed", "hardware_result_claimed", "production_decoder_claimed", "b7_resource_credit_claimed", "quantum_advantage_claimed"]), "All forbidden claims remain false."),
    ]
    passed = sum(row["passed"] for row in checks)
    decision = "logical_memory_horizon_gate_ready_short_memory_calibration_only_p023_b2_b7_credit_closed"
    return {
        "schema_version": benchmark["schema_version"],
        "as_of_date": benchmark["as_of_date"],
        "scope": benchmark["scope"],
        "question": benchmark["question"],
        "decision": decision,
        "source": {
            name: {"path": str(item["path"].relative_to(ROOT)), "sha256": item["sha256"], "status": item["value"].get("status")}
            for name, item in inputs.items()
        },
        "external_evidence_captures": captures,
        "evidence_ladder": [
            {"level": "local_simulator_calibration", "source": "B2 Stim/PyMatching baseline", "credit": "short-memory calibration only"},
            {"level": "hardware_memory_denominator", "source": "Willow and IBM primary reports", "credit": "external denominator only; not locally reproduced"},
            {"level": "low_overhead_protocol_denominator", "source": "qLDPC Nature protocol", "credit": "external protocol/simulation denominator only"},
            {"level": "scalable_memory_acceptance", "source": "frozen P023 direct-horizon gate", "credit": "closed"},
            {"level": "B7 resource credit", "source": "B2/B7 calibrated dependency gate", "credit": "zero"},
        ],
        "internal_baseline": {
            "configuration_count": len(baseline["results"]),
            "shots_per_configuration": baseline["shots_per_configuration"],
            "source_rounds": sorted({row["rounds"] for row in baseline["results"]}),
            "distances": sorted({row["distance"] for row in baseline["results"]}),
            "memory_bases": sorted({row["memory_basis"] for row in baseline["results"]}),
            "direct_horizon_max_rounds": max(row["rounds"] for row in baseline["results"]),
        },
        "horizon_contract": benchmark["horizon_contract"],
        "row_projections": projections,
        "paired_basis_gates": paired,
        "statistical_resolution_planning": resolution,
        "readiness": {
            "p023_scalable_memory_ready": p023_ready,
            "b2_low_overhead_credit_ready": b2_credit_ready,
            "b7_memory_credit_ready": b7_credit_ready,
            "b7_resource_credit_from_this_gate": 0,
            "minimum_missing_evidence": [
                "direct X and Z memory runs at 1,000 and 1,000,000 rounds",
                "same-condition candidate-code versus surface-code volume comparison",
                "decoder throughput/latency and drift/correlation stress",
                "calibrated or real-hardware replay accepted by the existing B7 credit gate"
            ],
        },
        "formal_checks": checks,
        "summary": {"checks_total": len(checks), "checks_passed": passed, "checks_failed": len(checks) - passed},
        "claim_boundary": benchmark["claim_boundary"],
    }


def render_report(result: dict[str, Any]) -> str:
    r10 = [row for row in result["paired_basis_gates"] if row["horizon_rounds"] == 10 and row["target_total_failure"] == 0.01]
    projected10 = sum(row["both_bases_projected_pass"] for row in r10)
    direct10 = sum(row["both_bases_direct_pass"] for row in r10)
    million_d3 = next(row for row in result["statistical_resolution_planning"] if row["target_total_failure"] == 0.01 and row["horizon_rounds"] == 1000000 and row["distance"] == 3)
    lines = [
        "# #021/B7 · #022/B2 · #023 Logical-Memory Horizon Gate v1",
        "",
        f"**Decision:** `{result['decision']}`.",
        "",
        "## Can seven rounds of memory justify the word scalable?",
        "",
        "No. The local B2 baseline contains 30 Stim/PyMatching configurations, 3,000 shots each, and only 3, 5, or 7 correction rounds. This packet preserves those rows as useful short-memory calibration, but gives them zero direct evidence at the frozen 10, 100, 1,000, and 1,000,000-round horizons.",
        "",
        "The stationary independent-flip projection is calculated only to expose how quickly a short-run upper bound compounds. It cannot upgrade a projection into observed lifetime evidence, and it earns no #023, B2, or B7 credit.",
        "",
        "## Evidence ladder",
        "",
        "| Level | Evidence | Credit |",
        "|---|---|---|",
    ]
    for row in result["evidence_ladder"]:
        lines.append(f"| {row['level']} | {row['source']} | {row['credit']} |")
    lines += [
        "",
        "## Frozen horizon result",
        "",
        f"At the shortest requested horizon (10 rounds, total failure target 1%), `{projected10}` paired X/Z settings pass only the diagnostic projection and `{direct10}` pass direct evidence. All longer direct horizons also have zero passes because the longest local source run is seven rounds.",
        "",
        "| Requirement | Result |",
        "|---|---|",
        "| Direct X and Z evidence at 1,000 rounds | fail |",
        "| Direct X and Z evidence at 1,000,000 rounds | fail |",
        "| Same-condition candidate-code gain >=25% | not executed |",
        "| Decoder timing plus drift/correlation stress | absent locally |",
        "| Existing B7 calibrated-credit gate | closed |",
        "| #023 scalable-memory readiness | false |",
        "| B2 low-overhead claim credit | false |",
        "| B7 memory-derived resource credit | 0 |",
        "",
        "## How expensive is honest resolution?",
        "",
        "A zero-failure direct experiment needs at least 381 shots before a two-sided Wilson 95% upper bound alone falls below 1%; a 0.1% target needs 3,838. At one million rounds, even the distance-3 local circuit (26 physical qubits) therefore implies at least "
        f"`{million_d3['minimum_qubit_cycles_per_basis']:,}` physical-qubit-cycles per basis, or `{million_d3['minimum_qubit_cycles_both_bases']:,}` across X and Z, before decoder, reset, drift, leakage, or layout overhead is added.",
        "",
        "This is a planning lower bound, not a hardware runtime forecast.",
        "",
        "## Why the external denominators matter",
        "",
        "The Willow hardware report supplies a below-threshold surface-code memory, real-time decoding, and runs up to one million cycles, while also exposing correlated-error floors. The 2024 qLDPC protocol supplies a low-overhead multi-logical-qubit memory target under an explicit circuit-noise assumption. The October 2026 IBM preprint reports cloud-hardware distance suppression but also a weakening distance advantage in longer memories. These are denominator classes, not interchangeable rows and not local reproductions.",
        "",
        "## Next falsifier",
        "",
        "Build one source-bound memory-run manifest that records basis, distance, physical qubits, exact rounds, shots, failures, decoder, latency/throughput, calibration window, drift/leakage treatment, and immutable trace hashes. The next executable gate must first reproduce both X and Z at 1,000 rounds; only then may a 1,000,000-round plan or a candidate-code overhead comparison be opened.",
        "",
        "## Reproducibility and claim boundary",
        "",
        f"Formal checks pass `{result['summary']['checks_passed']}/{result['summary']['checks_total']}` over four hash-bound local inputs and three normalized text captures. The captures preserve official-origin semantics through a text relay but make no raw-publisher-byte identity claim.",
        "",
        "No new code, threshold, scalable-memory result, hardware result, production decoder, B7 resource credit, or quantum-advantage claim is made.",
        "",
        "## Primary sources",
        "",
        "- [Quantum error correction below the surface code threshold](https://www.nature.com/articles/s41586-024-08449-y)",
        "- [High-threshold and low-overhead fault-tolerant quantum memory](https://www.nature.com/articles/s41586-024-07107-7)",
        "- [Logical error suppression on a cloud-accessible IBM processor](https://arxiv.org/abs/2610.23840)",
        "",
    ]
    return "\n".join(lines)


def render_discussion(result: dict[str, Any]) -> str:
    million_d3 = next(row for row in result["statistical_resolution_planning"] if row["target_total_failure"] == 0.01 and row["horizon_rounds"] == 1000000 and row["distance"] == 3)
    return f"""If a logical qubit survives seven correction rounds, when—exactly—may we call it scalable memory?

The new #021/B7 · #022/B2 · #023 gate gives an intentionally uncomfortable answer: **not after seven rounds, and not by extrapolation alone**.

Our local B2 packet has 30 reproducible Stim/PyMatching configurations with 3,000 shots each, but each experiment spans only 3, 5, or 7 rounds. We now separate four claims that are often collapsed:

1. short-memory simulator calibration;
2. stationary-model lifetime projection;
3. directly observed logical-memory horizon; and
4. B7 architecture resource credit.

Only the third can activate #023, and only a same-condition low-overhead comparison plus the existing calibrated-evidence gate can carry it into B7.

The statistical floor is already sobering. With zero observed failures, a two-sided Wilson 95% upper bound needs 381 direct-horizon shots to clear a 1% total-failure target. At one million rounds, the smallest current distance-3 circuit therefore implies at least **{million_d3['minimum_qubit_cycles_both_bases']:,} physical-qubit-cycles across X and Z**—before decoder, reset, leakage, drift, or layout overhead.

Three primary-source denominators make the question concrete: Willow reports below-threshold memory and million-cycle operation while still finding correlated-error floors; a qLDPC protocol projects far lower multi-logical-qubit overhead under an explicit noise model; and an October 2026 IBM cloud-hardware preprint reports distance suppression whose advantage weakens in longer memories.

So what should be the minimum honest definition of “scalable quantum memory”?

- Must both X and Z survive the same horizon?
- Is 1,000 rounds enough for activation, or only a staging gate to one million?
- Should decoder throughput, calibration drift, and correlated bursts be hard vetoes?
- When may a model projection enter an architecture ledger, if ever?

Useful contributions are falsifiable: propose a tighter horizon, a defensible confidence rule, a source-backed public trace dataset, a same-condition surface-code/qLDPC denominator, or a reason the current gate is too weak or too strong.

Current decision: **short-memory calibration only; #023 readiness false; B2 claim credit false; B7 memory-derived resource credit zero.** Formal checks: {result['summary']['checks_passed']}/{result['summary']['checks_total']}.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion", type=Path, default=DEFAULT_DISCUSSION)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    result = build_result(args.benchmark, args.source_dir, args.offline)
    if result["summary"]["checks_failed"]:
        failed = [row["name"] for row in result["formal_checks"] if not row["passed"]]
        raise SystemExit(f"formal checks failed: {failed}")
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(canonical(result), encoding="utf-8")
    args.report.write_text(render_report(result), encoding="utf-8")
    args.discussion.write_text(render_discussion(result), encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    print(result["decision"])


if __name__ == "__main__":
    main()
