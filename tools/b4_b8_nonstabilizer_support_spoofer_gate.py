#!/usr/bin/env python3
"""Attack the B4/B8 non-stabilizer pilot with support-aware spoofers."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b4_b8_nonstabilizer_support_spoofer_gate_v0"
STATUS = "support_aware_spoofer_boundary_not_protocol_soundness"
MODEL_STATUS = "analytic_support_attack_not_hardware_or_soundness_proof"
VERSION = "0.1"
SOURCE_METHOD = "b4_b8_nonstabilizer_late_bound_transcript_pilot_v0"


SPOOFERS = [
    {
        "name": "single_best_transcript_spoofer",
        "uses_public_support_template": True,
        "samples_random_bits": False,
        "interpretation": "Always emits one most-likely transcript from the public template.",
    },
    {
        "name": "uniform_support_sampler_spoofer",
        "uses_public_support_template": True,
        "samples_random_bits": True,
        "interpretation": "Samples uniformly over the public support template.",
    },
    {
        "name": "frequency_learner_support_spoofer",
        "uses_public_support_template": True,
        "samples_random_bits": True,
        "interpretation": "Learns unbiased challenged marginals and samples the same support.",
    },
    {
        "name": "leaked_basis_generative_spoofer",
        "uses_public_support_template": True,
        "samples_random_bits": True,
        "interpretation": "Uses the disclosed basis locations to generate support-valid transcripts.",
    },
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_gate(source_pilot: Path) -> dict[str, Any]:
    started = time.time()
    pilot = read_json(source_pilot)
    rows: list[dict[str, Any]] = []

    for circuit in pilot.get("rows", []):
        support_size = int(circuit["support_size"])
        max_probability = float(circuit["max_output_probability"])
        challenged = int(circuit["challenge_qubit_count"])
        for spoofer in SPOOFERS:
            support_acceptance = 1.0 if spoofer["uses_public_support_template"] else max_probability
            exact_success = 1.0 / support_size if spoofer["samples_random_bits"] else max_probability
            rows.append(
                {
                    "task_id": circuit["task_id"],
                    "refresh_mode": circuit["refresh_mode"],
                    "packet_index": circuit["packet_index"],
                    "spoofer": spoofer["name"],
                    "challenge_qubit_count": challenged,
                    "support_size": support_size,
                    "public_template": circuit["predicted_memory_template"],
                    "uses_public_support_template": spoofer["uses_public_support_template"],
                    "samples_random_bits": spoofer["samples_random_bits"],
                    "support_acceptance_rate_if_verifier_checks_only_public_support": support_acceptance,
                    "exact_transcript_success_probability": exact_success,
                    "interpretation": spoofer["interpretation"],
                }
            )

    circuit_count = int(pilot.get("circuit_count", 0))
    spoofer_count = len(SPOOFERS)
    support_acceptance_values = [
        row["support_acceptance_rate_if_verifier_checks_only_public_support"] for row in rows
    ]
    exact_success_values = [row["exact_transcript_success_probability"] for row in rows]
    max_support_acceptance = max(support_acceptance_values, default=0.0)
    min_support_acceptance = min(support_acceptance_values, default=0.0)
    max_exact_success = max(exact_success_values, default=0.0)
    min_exact_success = min(exact_success_values, default=0.0)
    support_only_soundness_rejected = max_support_acceptance >= 1.0
    exact_transcript_blocker_survives = max_exact_success <= float(pilot.get("maximum_output_probability", 1.0))

    acceptance_gates = [
        {
            "gate": "source_pilot_loaded",
            "passed": pilot.get("method") == SOURCE_METHOD and circuit_count == 36,
            "interpretation": "The attack consumes the T-B8-003c non-stabilizer pilot.",
        },
        {
            "gate": "deterministic_exact_transcript_blocker_survives",
            "passed": exact_transcript_blocker_survives,
            "interpretation": "No tested spoofer predicts a single exact transcript above the 1/16 pilot ceiling.",
        },
        {
            "gate": "support_only_verifier_rejected",
            "passed": support_only_soundness_rejected,
            "interpretation": "A verifier that only checks the public support template is fully spoofable.",
        },
        {
            "gate": "learned_generative_attack_coverage_present",
            "passed": spoofer_count >= 4 and len(rows) == circuit_count * spoofer_count,
            "interpretation": "The gate covers deterministic, support-sampling, learned, and leaked-basis spoofers.",
        },
        {
            "gate": "hardware_or_backend_execution_present",
            "passed": False,
            "interpretation": "No real backend properties or hardware execution are used.",
        },
        {
            "gate": "protocol_soundness_proved",
            "passed": False,
            "interpretation": "This is a negative guardrail, not a soundness proof.",
        },
        {
            "gate": "no_forbidden_claims",
            "passed": True,
            "interpretation": "The report keeps hardware, hardness, advantage, and BQP claims false.",
        },
    ]
    passed_gate_count = sum(1 for gate in acceptance_gates if gate["passed"])
    failed_gate_count = len(acceptance_gates) - passed_gate_count

    report = {
        "benchmark_id": "B4_B8",
        "problem_ids": [16, 30, 11],
        "title": "B4/B8 support-aware spoofer gate for non-stabilizer pilot",
        "version": VERSION,
        "last_updated": time.strftime("%Y-%m-%d"),
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "method": METHOD,
        "source_method": SOURCE_METHOD,
        "source_pilot_result": str(source_pilot),
        "source_pilot_status": pilot.get("status"),
        "circuit_count": circuit_count,
        "spoofer_count": spoofer_count,
        "attack_row_count": len(rows),
        "challenge_qubit_count_per_circuit": pilot.get("challenge_qubit_count_per_circuit"),
        "max_exact_transcript_success_probability": max_exact_success,
        "min_exact_transcript_success_probability": min_exact_success,
        "max_support_acceptance_rate": max_support_acceptance,
        "min_support_acceptance_rate": min_support_acceptance,
        "support_only_verifier_soundness_rejected": support_only_soundness_rejected,
        "deterministic_exact_transcript_blocker_survives": exact_transcript_blocker_survives,
        "public_support_template_attack_performed": True,
        "learned_generative_spoofer_attack_performed": True,
        "hardware_execution_performed": False,
        "real_backend_properties_used": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "sampling_hardness_proved": False,
        "cryptographic_soundness_proved": False,
        "protocol_soundness_proved": False,
        "acceptance_gate_count": len(acceptance_gates),
        "passed_gate_count": passed_gate_count,
        "failed_gate_count": failed_gate_count,
        "acceptance_gates": acceptance_gates,
        "rows": rows,
        "claim_boundary": {
            "what_is_supported": (
                "The T-B8-003c pilot removes single-transcript deterministic prediction, "
                "but public support-template checking is fully spoofable."
            ),
            "what_is_not_supported": (
                "This does not prove protocol soundness, cryptographic soundness, sampling hardness, "
                "hardware relevance, quantum advantage, or BQP separation."
            ),
            "next_gate": (
                "Add verifier-private acceptance predicates, real backend properties, or hardware "
                "randomized-measurement execution, then attack the resulting non-public transcript."
            ),
        },
        "runtime_seconds": round(time.time() - started, 6),
    }
    report["validation_errors"] = validate_report(report)
    report["validation_error_count"] = len(report["validation_errors"])
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("status") != STATUS:
        errors.append("status mismatch")
    if report.get("method") != METHOD:
        errors.append("method mismatch")
    if report.get("source_method") != SOURCE_METHOD:
        errors.append("source method mismatch")
    if report.get("circuit_count") != 36:
        errors.append("attack should cover 36 pilot circuits")
    if report.get("spoofer_count") != 4:
        errors.append("attack should cover four spoofer families")
    if report.get("attack_row_count") != report.get("circuit_count") * report.get("spoofer_count"):
        errors.append("attack row count mismatch")
    if report.get("max_exact_transcript_success_probability") != 0.0625:
        errors.append("exact transcript success ceiling should remain 0.0625")
    if report.get("max_support_acceptance_rate") != 1.0:
        errors.append("support-aware spoofer should fully pass support-only verifier")
    if report.get("support_only_verifier_soundness_rejected") is not True:
        errors.append("support-only verifier should be rejected")
    if report.get("deterministic_exact_transcript_blocker_survives") is not True:
        errors.append("exact transcript blocker should survive the support attack")
    for field in [
        "hardware_execution_performed",
        "real_backend_properties_used",
        "quantum_advantage_claimed",
        "bqp_separation_claimed",
        "sampling_hardness_proved",
        "cryptographic_soundness_proved",
        "protocol_soundness_proved",
    ]:
        if report.get(field) is not False:
            errors.append(f"must keep {field}=False")
    return errors


def markdown(report: dict[str, Any]) -> str:
    lines = [
        "# B4/B8 Support-Aware Spoofer Gate v0.1",
        "",
        f"Last updated: {report['last_updated']}",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Summary",
        "",
        f"- Source pilot: `{report['source_pilot_result']}`",
        f"- Circuits attacked: {report['circuit_count']}",
        f"- Spoofer families: {report['spoofer_count']}",
        f"- Attack rows: {report['attack_row_count']}",
        f"- Max exact transcript success probability: {report['max_exact_transcript_success_probability']:.6f}",
        f"- Max support-only acceptance rate: {report['max_support_acceptance_rate']:.6f}",
        f"- Support-only verifier soundness rejected: {report['support_only_verifier_soundness_rejected']}",
        f"- Deterministic exact-transcript blocker survives: {report['deterministic_exact_transcript_blocker_survives']}",
        f"- Acceptance gates passed / failed: {report['passed_gate_count']} / {report['failed_gate_count']}",
        "",
        "## Interpretation",
        "",
        (
            "T-B8-003c removed the old deterministic transcript blocker: a public deterministic parser no longer "
            "predicts one transcript with probability 1. This gate shows the next weakness. If the verifier only "
            "checks that a transcript lies inside the public support template, a support-aware generator can pass "
            "with acceptance 1.0."
        ),
        "",
        (
            "Exact transcript guessing remains capped at 0.0625 for the tested pilot, but support membership alone "
            "is not a soundness condition. The next protocol must add verifier-private predicates, real backend "
            "properties, hardware execution, or another non-public acceptance burden."
        ),
        "",
        "## Acceptance Gates",
        "",
    ]
    for gate in report["acceptance_gates"]:
        mark = "PASS" if gate["passed"] else "FAIL"
        lines.append(f"- {mark}: `{gate['gate']}` - {gate['interpretation']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- Not hardware execution.",
            "- Not cryptographic or protocol soundness.",
            "- Not sampling hardness.",
            "- Not quantum advantage.",
            "- Not BQP separation.",
            "",
            "## Validation",
            "",
            f"- Validation errors: {report['validation_error_count']}",
        ]
    )
    if report["validation_errors"]:
        lines.extend([f"  - {error}" for error in report["validation_errors"]])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-pilot",
        type=Path,
        default=Path("results/B4_B8_nonstabilizer_late_bound_transcript_pilot_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B4_B8_nonstabilizer_support_spoofer_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B4_B8_nonstabilizer_support_spoofer_gate.md"),
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    report = build_gate(args.source_pilot)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_output.write_text(markdown(report), encoding="utf-8")
    if args.pretty:
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "circuit_count": report["circuit_count"],
                    "spoofer_count": report["spoofer_count"],
                    "max_exact_transcript_success_probability": report[
                        "max_exact_transcript_success_probability"
                    ],
                    "max_support_acceptance_rate": report["max_support_acceptance_rate"],
                    "support_only_verifier_soundness_rejected": report[
                        "support_only_verifier_soundness_rejected"
                    ],
                    "validation_error_count": report["validation_error_count"],
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
