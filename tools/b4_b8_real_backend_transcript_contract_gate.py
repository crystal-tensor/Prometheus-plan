#!/usr/bin/env python3
"""Build the B4/B8 real-backend transcript evidence contract."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


METHOD = "b4_b8_real_backend_transcript_contract_gate_v0"
STATUS = "real_backend_transcript_contract_open_missing_hardware_evidence"
MODEL_STATUS = "readiness_blockers_decomposed_for_backend_transcript_prs"
VERSION = "0.1"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any], pretty: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        payload,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
        sort_keys=True,
    )
    path.write_text(text + "\n", encoding="utf-8")


def contract_gate(
    gate_id: str,
    label: str,
    passed: bool,
    evidence: dict[str, Any],
    acceptance_rule: str,
    pr_packet: str,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
        "acceptance_rule": acceptance_rule,
        "pr_packet": pr_packet,
    }


def build_contract_packets(source: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "packet_id": "B4B8-R5-real-backend-properties",
            "blocks_gate": "K5",
            "owner_role": "backend_calibration_agent",
            "required_artifacts": [
                "backend properties from a real device snapshot or provider export",
                "per-qubit and per-edge timing/error/readout metadata",
                "calibration timestamp, backend identifier, and provider provenance",
                "mapping from exported properties into the verifier circuit layout",
            ],
            "acceptance_rule": (
                "real_backend_properties_used must become true while preserving "
                "the current B4/B8 verifier-private transcript fields."
            ),
        },
        {
            "packet_id": "B4B8-R6-hardware-execution",
            "blocks_gate": "K6",
            "owner_role": "hardware_execution_agent",
            "required_artifacts": [
                "hardware or independently supplied execution transcript rows",
                "circuit id, shot id, refresh mode, leakage profile, and predicate outcome columns",
                "raw-to-processed transcript hash ledger",
                "explicit no-refresh, challenge-refresh, and refresh-plus-rotation coverage",
            ],
            "acceptance_rule": (
                "hardware_execution_performed must become true and the transcript "
                "schema must replay through the current fitted-spoofer evaluator."
            ),
        },
        {
            "packet_id": "B4B8-R7-leakage-separated-real-fitting",
            "blocks_gate": "K7",
            "owner_role": "spoofer_baseline_agent",
            "required_artifacts": [
                "leakage-separated train/holdout split over real transcript rows",
                "private-safe, leakage-blind, and leakage-aware fitted families",
                "fitted evaluation rows with the same 560/160 discipline or justified larger split",
                "negative-control splits that prevent private-material leakage from contaminating no-leak training",
            ],
            "acceptance_rule": (
                "leakage_separated_real_training_performed must become true and "
                "real_backend_transcript_rows must be positive."
            ),
        },
        {
            "packet_id": "B4B8-R8-leakage-blind-no-leak-margin",
            "blocks_gate": "K8",
            "owner_role": "adversary_margin_agent",
            "required_artifacts": [
                "leakage-blind no-leak fitted acceptance table",
                "same private-safe no-leak denominator table",
                "diagnostic proving no-leak acceptance stays below 0.10",
                "predicate redesign notes if leakage-blind fitting remains unsafe",
            ],
            "acceptance_rule": (
                "leakage_blind_max_no_leak_fitted_acceptance must fall from "
                f"{source['leakage_blind_max_no_leak_fitted_acceptance']} to <= 0.10."
            ),
        },
        {
            "packet_id": "B4B8-R9-full-leakage-containment",
            "blocks_gate": "K9",
            "owner_role": "protocol_boundary_agent",
            "required_artifacts": [
                "full-private-material leakage acceptance table",
                "explicit claim boundary excluding full leakage or a cryptographic protection layer",
                "challenge-material redesign evidence if full leakage remains in scope",
                "bounded leakage model with verifier-private material still hidden",
            ],
            "acceptance_rule": (
                "full-private-material leakage acceptance must be <= 0.25 or "
                "the claim boundary must explicitly exclude that leakage regime."
            ),
        },
    ]


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    started = time.time()
    source = load_json(args.readiness_result)
    claims = source["claim_boundary"]
    packets = build_contract_packets(source)
    packet_ids = [packet["packet_id"] for packet in packets]

    requirements = [
        contract_gate(
            "K1",
            "Source readiness gate is valid and fails only R5-R9",
            source.get("benchmark_id") == "B4_B8"
            and source.get("method") == "b4_b8_real_backend_transcript_readiness_gate_v0"
            and source.get("validation_error_count") == 0
            and source.get("missing_readiness_gate_ids") == ["R5", "R6", "R7", "R8", "R9"],
            {
                "source_method": source.get("method"),
                "source_status": source.get("status"),
                "source_validation_error_count": source.get("validation_error_count"),
                "missing_readiness_gate_ids": source.get("missing_readiness_gate_ids"),
            },
            "The source readiness gate must stay valid and fail only R5-R9.",
            "source-audit",
        ),
        contract_gate(
            "K2",
            "Synthetic transcript and fitted-spoofer denominators remain available",
            source["source_transcript_case_count"] == 720
            and source["train_row_count"] == 560
            and source["holdout_row_count"] == 160
            and source["fitted_evaluation_row_count"] == 640,
            {
                "source_transcript_case_count": source["source_transcript_case_count"],
                "train_row_count": source["train_row_count"],
                "holdout_row_count": source["holdout_row_count"],
                "fitted_evaluation_row_count": source["fitted_evaluation_row_count"],
            },
            "Preserve the synthetic transcript denominator while adding real rows.",
            "synthetic-control-denominator",
        ),
        contract_gate(
            "K3",
            "GenericBackendV2 bridge remains a calibrated simulator denominator",
            bool(source["qiskit_generic_backend_v2_used"])
            and source["backend_calibrated_aer_circuit_count"] == 5760
            and bool(source["backend_calibrated_noise_parameters_instantiated"]),
            {
                "qiskit_generic_backend_v2_used": source["qiskit_generic_backend_v2_used"],
                "backend_calibrated_aer_circuit_count": source[
                    "backend_calibrated_aer_circuit_count"
                ],
                "backend_calibrated_noise_parameters_instantiated": source[
                    "backend_calibrated_noise_parameters_instantiated"
                ],
            },
            "Keep this simulated denominator, but do not treat it as real backend evidence.",
            "generic-backend-control",
        ),
        contract_gate(
            "K4",
            "PR packets exist for every failed real-backend readiness gate",
            [packet["blocks_gate"] for packet in packets] == ["K5", "K6", "K7", "K8", "K9"],
            {"contract_packet_count": len(packets), "contract_packet_ids": packet_ids},
            "Every failed readiness gate must map to a concrete PR packet.",
            "packet-index",
        ),
        contract_gate(
            "K5",
            "Real backend properties packet has been satisfied",
            bool(source["real_backend_properties_used"]),
            {"source_gate": "R5", "real_backend_properties_used": source["real_backend_properties_used"]},
            "Attach real backend properties with provenance and layout mapping.",
            "B4B8-R5-real-backend-properties",
        ),
        contract_gate(
            "K6",
            "Hardware execution packet has been satisfied",
            bool(source["hardware_execution_performed"]),
            {"source_gate": "R6", "hardware_execution_performed": source["hardware_execution_performed"]},
            "Submit hardware or independent execution transcript rows.",
            "B4B8-R6-hardware-execution",
        ),
        contract_gate(
            "K7",
            "Leakage-separated real fitting packet has been satisfied",
            bool(source["leakage_separated_real_training_performed"])
            and source["real_backend_transcript_rows"] > 0,
            {
                "source_gate": "R7",
                "real_backend_transcript_rows": source["real_backend_transcript_rows"],
                "leakage_separated_real_training_performed": source[
                    "leakage_separated_real_training_performed"
                ],
            },
            "Train and hold out leakage-separated spoofers on real transcript rows.",
            "B4B8-R7-leakage-separated-real-fitting",
        ),
        contract_gate(
            "K8",
            "Leakage-blind no-leak margin packet has been satisfied",
            float(source["leakage_blind_max_no_leak_fitted_acceptance"]) <= 0.10,
            {
                "source_gate": "R8",
                "leakage_blind_max_no_leak_fitted_acceptance": source[
                    "leakage_blind_max_no_leak_fitted_acceptance"
                ],
                "required_max_acceptance": 0.10,
            },
            "Keep leakage-blind no-leak fitted acceptance <= 0.10.",
            "B4B8-R8-leakage-blind-no-leak-margin",
        ),
        contract_gate(
            "K9",
            "Full-private-material leakage packet has been satisfied",
            float(source["leakage_aware_max_full_private_material_leak_fitted_acceptance"])
            <= 0.25,
            {
                "source_gate": "R9",
                "leakage_aware_max_full_private_material_leak_fitted_acceptance": source[
                    "leakage_aware_max_full_private_material_leak_fitted_acceptance"
                ],
                "required_max_acceptance": 0.25,
            },
            "Bound full-private-material leakage or move it outside the claim boundary.",
            "B4B8-R9-full-leakage-containment",
        ),
        contract_gate(
            "K10",
            "Forbidden advantage and soundness claims remain absent",
            not any(
                bool(claims[key])
                for key in [
                    "protocol_soundness_proved",
                    "cryptographic_soundness_proved",
                    "sampling_hardness_proved",
                    "quantum_advantage_claimed",
                    "bqp_separation_claimed",
                ]
            ),
            {
                "protocol_soundness_proved": claims["protocol_soundness_proved"],
                "cryptographic_soundness_proved": claims["cryptographic_soundness_proved"],
                "sampling_hardness_proved": claims["sampling_hardness_proved"],
                "quantum_advantage_claimed": claims["quantum_advantage_claimed"],
                "bqp_separation_claimed": claims["bqp_separation_claimed"],
            },
            "Do not promote B4/B8 until K5-K9 pass under replayable evidence.",
            "claim-boundary",
        ),
    ]

    passed = sum(1 for item in requirements if item["passed"])
    failed = len(requirements) - passed
    failed_ids = [item["gate_id"] for item in requirements if not item["passed"]]

    payload = {
        "benchmark": "B4/B8",
        "benchmark_id": "B4_B8",
        "title": "B4/B8 real-backend transcript contract gate",
        "version": VERSION,
        "last_updated": args.last_updated,
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_readiness_method": source["method"],
        "source_readiness_status": source["status"],
        "source_missing_readiness_gate_ids": source["missing_readiness_gate_ids"],
        "source_transcript_case_count": source["source_transcript_case_count"],
        "train_row_count": source["train_row_count"],
        "holdout_row_count": source["holdout_row_count"],
        "fitted_evaluation_row_count": source["fitted_evaluation_row_count"],
        "backend_calibrated_aer_circuit_count": source[
            "backend_calibrated_aer_circuit_count"
        ],
        "qiskit_generic_backend_v2_used": source["qiskit_generic_backend_v2_used"],
        "backend_calibrated_noise_parameters_instantiated": source[
            "backend_calibrated_noise_parameters_instantiated"
        ],
        "private_safe_max_no_leak_fitted_acceptance": source[
            "private_safe_max_no_leak_fitted_acceptance"
        ],
        "leakage_blind_max_no_leak_fitted_acceptance": source[
            "leakage_blind_max_no_leak_fitted_acceptance"
        ],
        "leakage_aware_max_full_private_material_leak_fitted_acceptance": source[
            "leakage_aware_max_full_private_material_leak_fitted_acceptance"
        ],
        "real_backend_properties_required": True,
        "hardware_execution_required": True,
        "leakage_separated_real_training_required": True,
        "leakage_blind_no_leak_margin_required": True,
        "full_private_material_leakage_containment_required": True,
        "real_backend_properties_used": source["real_backend_properties_used"],
        "hardware_execution_performed": source["hardware_execution_performed"],
        "real_backend_transcript_rows": source["real_backend_transcript_rows"],
        "leakage_separated_real_training_performed": source[
            "leakage_separated_real_training_performed"
        ],
        "contract_requirement_count": len(requirements),
        "passed_contract_requirement_count": passed,
        "failed_contract_requirement_count": failed,
        "failed_contract_requirement_ids": failed_ids,
        "contract_packet_count": len(packets),
        "contract_packet_ids": packet_ids,
        "real_backend_transcript_readiness": False,
        "protocol_soundness_proved": False,
        "cryptographic_soundness_proved": False,
        "sampling_hardness_proved": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "data_contract_ready_for_prs": True,
        "contract_requirements": requirements,
        "contract_packets": packets,
        "claim_boundary": {
            "real_backend_transcript_contract_built": True,
            "real_backend_transcript_readiness": False,
            "protocol_soundness_proved": False,
            "cryptographic_soundness_proved": False,
            "sampling_hardness_proved": False,
            "quantum_advantage_claimed": False,
            "bqp_separation_claimed": False,
            "hardware_execution_performed": False,
            "real_backend_properties_used": False,
            "what_is_supported": (
                "B4/B8 now has five explicit PR packets for real backend "
                "properties, hardware execution transcripts, leakage-separated "
                "real fitting, leakage-blind no-leak margin, and full-leakage containment."
            ),
            "what_is_not_supported": (
                "No real backend transcript readiness, protocol soundness, "
                "sampling hardness, quantum advantage, or BQP separation is established."
            ),
        },
        "elapsed_seconds": time.time() - started,
    }
    payload["validation_errors"] = validate(payload)
    payload["validation_error_count"] = len(payload["validation_errors"])
    return payload


def validate(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload["source_missing_readiness_gate_ids"] != ["R5", "R6", "R7", "R8", "R9"]:
        errors.append("source missing readiness gates must remain R5-R9")
    if payload["source_transcript_case_count"] != 720:
        errors.append("expected 720 source transcript cases")
    if payload["train_row_count"] != 560 or payload["holdout_row_count"] != 160:
        errors.append("expected 560/160 train/holdout split")
    if payload["fitted_evaluation_row_count"] != 640:
        errors.append("expected 640 fitted evaluation rows")
    if payload["backend_calibrated_aer_circuit_count"] != 5760:
        errors.append("expected 5760 backend-calibrated Aer circuits")
    if payload["contract_requirement_count"] != 10:
        errors.append("expected ten contract requirements")
    if payload["passed_contract_requirement_count"] != 5:
        errors.append("current contract should pass five requirements")
    if payload["failed_contract_requirement_count"] != 5:
        errors.append("current contract should fail five requirements")
    if payload["failed_contract_requirement_ids"] != ["K5", "K6", "K7", "K8", "K9"]:
        errors.append("current failed contract ids should be K5-K9")
    if payload["contract_packet_count"] != 5:
        errors.append("expected five contract packets")
    if payload["private_safe_max_no_leak_fitted_acceptance"] != 0.0625:
        errors.append("expected private-safe no-leak acceptance 0.0625")
    if payload["leakage_blind_max_no_leak_fitted_acceptance"] != 0.35:
        errors.append("expected leakage-blind no-leak acceptance 0.35")
    if payload["leakage_aware_max_full_private_material_leak_fitted_acceptance"] != 1.0:
        errors.append("expected full-private-material leakage acceptance 1.0")
    for key in [
        "real_backend_properties_required",
        "hardware_execution_required",
        "leakage_separated_real_training_required",
        "leakage_blind_no_leak_margin_required",
        "full_private_material_leakage_containment_required",
        "qiskit_generic_backend_v2_used",
        "backend_calibrated_noise_parameters_instantiated",
        "data_contract_ready_for_prs",
    ]:
        if payload.get(key) is not True:
            errors.append(f"{key} must be true")
    for key in [
        "real_backend_properties_used",
        "hardware_execution_performed",
        "leakage_separated_real_training_performed",
        "real_backend_transcript_readiness",
        "protocol_soundness_proved",
        "cryptographic_soundness_proved",
        "sampling_hardness_proved",
        "quantum_advantage_claimed",
        "bqp_separation_claimed",
    ]:
        if payload.get(key) is not False:
            errors.append(f"{key} must remain false")
    if payload["real_backend_transcript_rows"] != 0:
        errors.append("real backend transcript rows must remain 0")
    claims = payload["claim_boundary"]
    if claims.get("real_backend_transcript_contract_built") is not True:
        errors.append("claim boundary must disclose contract construction")
    for key in [
        "real_backend_transcript_readiness",
        "protocol_soundness_proved",
        "cryptographic_soundness_proved",
        "sampling_hardness_proved",
        "quantum_advantage_claimed",
        "bqp_separation_claimed",
        "hardware_execution_performed",
        "real_backend_properties_used",
    ]:
        if claims.get(key) is not False:
            errors.append(f"claim boundary must keep {key}=False")
    return errors


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# B4/B8 Real-Backend Transcript Contract Gate v0.1",
        "",
        f"Status: **{payload['status']}**",
        "",
        "## Summary",
        "",
        f"- Method: {payload['method']}",
        f"- Model status: {payload['model_status']}",
        f"- Source readiness method: {payload['source_readiness_method']}",
        f"- Source missing readiness gates: {', '.join(payload['source_missing_readiness_gate_ids'])}",
        f"- Source transcript / train / holdout / eval rows: {payload['source_transcript_case_count']} / {payload['train_row_count']} / {payload['holdout_row_count']} / {payload['fitted_evaluation_row_count']}",
        f"- Backend-calibrated Aer circuit count: {payload['backend_calibrated_aer_circuit_count']}",
        f"- Private-safe / leakage-blind / full-leak fitted acceptance: {payload['private_safe_max_no_leak_fitted_acceptance']} / {payload['leakage_blind_max_no_leak_fitted_acceptance']} / {payload['leakage_aware_max_full_private_material_leak_fitted_acceptance']}",
        f"- Contract requirements passed / failed: {payload['passed_contract_requirement_count']} / {payload['failed_contract_requirement_count']}",
        f"- Failed contract requirement ids: {', '.join(payload['failed_contract_requirement_ids'])}",
        f"- Contract packets: {', '.join(payload['contract_packet_ids'])}",
        f"- Real backend transcript rows: {payload['real_backend_transcript_rows']}",
        f"- Real backend transcript readiness: {payload['real_backend_transcript_readiness']}",
        f"- Validation errors: {payload['validation_errors']}",
        "",
        "## Contract Requirements",
        "",
        "| gate | passed | label | PR packet | acceptance rule |",
        "|---|---:|---|---|---|",
    ]
    for item in payload["contract_requirements"]:
        lines.append(
            f"| {item['gate_id']} | {item['passed']} | {item['label']} | "
            f"{item['pr_packet']} | {item['acceptance_rule']} |"
        )
    lines.extend(["", "## PR Packets", ""])
    for packet in payload["contract_packets"]:
        lines.extend(
            [
                f"### {packet['packet_id']}",
                "",
                f"- Blocks gate: {packet['blocks_gate']}",
                f"- Owner role: {packet['owner_role']}",
                f"- Acceptance rule: {packet['acceptance_rule']}",
                "- Required artifacts:",
            ]
        )
        for artifact in packet["required_artifacts"]:
            lines.append(f"  - {artifact}")
        lines.append("")
    lines.extend(["## Claim Boundary", ""])
    for key, value in payload["claim_boundary"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            "A future B4/B8 PR must satisfy K5-K9 together: real backend",
            "properties, hardware or independently supplied transcripts,",
            "leakage-separated fitting, leakage-blind no-leak acceptance below",
            "0.10, and full-leakage containment. Until then this remains a",
            "real-backend handoff contract, not protocol soundness or advantage.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--readiness-result",
        type=Path,
        default=Path("results/B4_B8_real_backend_transcript_readiness_gate_v0.json"),
    )
    parser.add_argument("--last-updated", default="2026-07-01")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B4_B8_real_backend_transcript_contract_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B4_B8_real_backend_transcript_contract_gate.md"),
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    payload = build_report(args)
    write_json(args.json_output, payload, args.pretty)
    write_markdown(payload, args.markdown_output)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "method": payload["method"],
                "passed_contract_requirement_count": payload[
                    "passed_contract_requirement_count"
                ],
                "failed_contract_requirement_count": payload[
                    "failed_contract_requirement_count"
                ],
                "failed_contract_requirement_ids": payload[
                    "failed_contract_requirement_ids"
                ],
                "contract_packet_count": payload["contract_packet_count"],
                "real_backend_transcript_rows": payload[
                    "real_backend_transcript_rows"
                ],
                "validation_errors": payload["validation_errors"],
            },
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
