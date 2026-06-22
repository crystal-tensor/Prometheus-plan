#!/usr/bin/env python3
"""Lift the cone_01 composable patch certificate onto the OpenQASM 3 artifact."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RESEARCH = ROOT / "research"

METHOD = "b1_b7_cone01_openqasm3_composable_patch_lift_gate_v0"
STATUS = "cone01_openqasm3_composable_patch_lift_passed_without_b7_resource_credit"
MODEL_STATUS = (
    "openqasm3_candidate_inherits_composable_patch_certificate_via_structural_roundtrip_"
    "without_b7_credit"
)

PATCH_PATH = RESULTS / "B1_B7_cone01_composable_patch_certificate_gate_v0.json"
ROUNDTRIP_PATH = RESULTS / "B1_B7_cone01_openqasm3_structural_roundtrip_gate_v0.json"
SPAN_PATH = RESULTS / "B1_B7_cone01_openqasm3_linear_span_replay_certificate_gate_v0.json"
OUT_JSON = RESULTS / "B1_B7_cone01_openqasm3_composable_patch_lift_gate_v0.json"
OUT_MD = RESEARCH / "B1_B7_cone01_openqasm3_composable_patch_lift_gate.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def main() -> None:
    patch = load_json(PATCH_PATH)
    roundtrip = load_json(ROUNDTRIP_PATH)
    span = load_json(SPAN_PATH)

    patch_summary = patch.get("summary", {})
    roundtrip_summary = roundtrip.get("summary", {})
    span_summary = span.get("summary", {})

    errors: list[str] = []

    require(
        errors,
        patch.get("status") == "cone01_composable_patch_certificate_passed_without_b7_resource_credit",
        "source QASM2 composable patch certificate did not pass",
    )
    require(errors, patch_summary.get("selected_line_numbers") == [268, 1381], "selected lines changed")
    require(errors, patch_summary.get("dropped_overlap_candidate_line_numbers") == [1378], "dropped overlap lines changed")
    require(errors, patch_summary.get("selected_patch_count") == 2, "selected patch count changed")
    require(errors, patch_summary.get("all_selected_windows_nonoverlap") is True, "selected windows overlap")
    require(
        errors,
        patch_summary.get("all_local_unitary_certificates_passed") is True,
        "local-unitary certificates did not pass",
    )
    require(
        errors,
        float(patch_summary.get("max_selected_patch_residual_norm", 1.0)) <= 1e-10,
        "selected patch residual too large",
    )
    require(
        errors,
        float(patch_summary.get("max_selected_patch_entry_error", 1.0)) <= 1e-10,
        "selected patch entry error too large",
    )
    require(errors, patch_summary.get("local_u3_resource_pricing_accepted") is False, "local-U3 pricing unexpectedly accepted")
    require(errors, patch_summary.get("b7_ledger_improvement_claimed") is False, "B7 ledger credit unexpectedly claimed")

    require(
        errors,
        roundtrip.get("status") == "cone01_openqasm3_structural_roundtrip_matches_legacy_candidate",
        "OpenQASM3 structural roundtrip did not pass",
    )
    require(errors, roundtrip_summary.get("normalized_streams_match") is True, "normalized streams do not match")
    require(errors, roundtrip_summary.get("stream_mismatch_count") == 0, "structural stream mismatches exist")
    require(errors, roundtrip_summary.get("stream_length_delta") == 0, "structural stream length changed")
    require(errors, roundtrip_summary.get("operation_counts_match") is True, "operation counts changed")
    require(errors, roundtrip_summary.get("normalized_instruction_count") == 1878, "instruction count changed")
    require(
        errors,
        roundtrip_summary.get("qasm2_candidate_path") == patch_summary.get("candidate_qasm"),
        "roundtrip QASM2 input is not the certified QASM2 candidate",
    )

    require(
        errors,
        span.get("status") == "cone01_openqasm3_linear_span_replay_certificate_passed_not_full_unitary",
        "OpenQASM3 finite-span replay certificate did not pass",
    )
    require(errors, span_summary.get("project_local_openqasm3_parser_passed") is True, "project-local parser did not pass")
    require(
        errors,
        span_summary.get("finite_openqasm3_linear_span_certificate_passed") is True,
        "finite OpenQASM3 linear-span certificate did not pass",
    )
    require(
        errors,
        span_summary.get("openqasm3_candidate_path") == roundtrip_summary.get("openqasm3_candidate_path"),
        "finite-span OpenQASM3 path is not the structural roundtrip OpenQASM3 artifact",
    )
    require(
        errors,
        float(span_summary.get("linear_span_error_spectral_norm", 1.0)) <= 1e-10,
        "OpenQASM3 finite-span spectral error too large",
    )

    passed = not errors
    summary = {
        "source_composable_patch_method": patch.get("method"),
        "source_composable_patch_status": patch.get("status"),
        "source_structural_roundtrip_method": roundtrip.get("method"),
        "source_openqasm3_linear_span_method": span.get("method"),
        "qasm2_candidate_path": roundtrip_summary.get("qasm2_candidate_path"),
        "openqasm3_candidate_path": roundtrip_summary.get("openqasm3_candidate_path"),
        "normalized_streams_match": roundtrip_summary.get("normalized_streams_match"),
        "stream_mismatch_count": roundtrip_summary.get("stream_mismatch_count"),
        "stream_length_delta": roundtrip_summary.get("stream_length_delta"),
        "normalized_instruction_count": roundtrip_summary.get("normalized_instruction_count"),
        "normalized_stream_sha256": roundtrip_summary.get("normalized_stream_sha256"),
        "selected_patch_count": patch_summary.get("selected_patch_count"),
        "selected_line_numbers": patch_summary.get("selected_line_numbers"),
        "dropped_overlap_candidate_line_numbers": patch_summary.get("dropped_overlap_candidate_line_numbers"),
        "all_selected_windows_nonoverlap": patch_summary.get("all_selected_windows_nonoverlap"),
        "all_local_unitary_certificates_passed": patch_summary.get("all_local_unitary_certificates_passed"),
        "max_selected_patch_residual_norm": patch_summary.get("max_selected_patch_residual_norm"),
        "max_selected_patch_entry_error": patch_summary.get("max_selected_patch_entry_error"),
        "source_cnot_count": patch_summary.get("source_cnot_count"),
        "openqasm3_cnot_count": span_summary.get("openqasm3_cnot_count"),
        "openqasm3_cnot_delta": span_summary.get("openqasm3_cnot_delta"),
        "selected_replacement_off_pi_over_four_parameter_count": patch_summary.get(
            "selected_replacement_off_pi_over_four_parameter_count"
        ),
        "finite_openqasm3_linear_span_certificate_passed": span_summary.get(
            "finite_openqasm3_linear_span_certificate_passed"
        ),
        "openqasm3_certified_input_subspace_dimension": span_summary.get(
            "certified_input_subspace_dimension"
        ),
        "openqasm3_full_input_space_dimension": span_summary.get("full_input_space_dimension"),
        "openqasm3_linear_span_error_spectral_norm": span_summary.get(
            "linear_span_error_spectral_norm"
        ),
        "project_local_openqasm3_parser_passed": span_summary.get(
            "project_local_openqasm3_parser_passed"
        ),
        "openqasm3_composable_patch_lift_passed": passed,
        "accepted_project_local_openqasm3_composable_patch_lift_count": 1 if passed else 0,
        "accepted_qiskit_loader_parse_artifact_count": 0,
        "accepted_symbolic_unitary_equivalence_count": 0,
        "accepted_local_u3_pricing_certificate_count": 0,
        "accepted_occurrence_removal": 0,
        "accepted_proxy_t_reduction": 0,
        "missing_occurrences_after_gate": 30,
        "missing_proxy_t_after_gate": 600,
        "qiskit_loader_parse_claimed": False,
        "symbolic_unitary_equivalence_claimed": False,
        "arbitrary_input_equivalence_claimed": False,
        "full_hilbert_space_certificate_claimed": False,
        "local_u3_pricing_accepted": False,
        "resource_saving_claimed": False,
        "b7_ledger_improvement_claimed": False,
        "validation_error_count": len(errors),
    }
    payload = {
        "benchmark_id": "B1",
        "linked_b7_problem_id": 21,
        "method": METHOD,
        "status": STATUS if passed else "cone01_openqasm3_composable_patch_lift_failed",
        "model_status": MODEL_STATUS if passed else "openqasm3_composable_patch_lift_rejected",
        "workload": "qasmbench_medium_exact/gcm_h6.qasm",
        "source_composable_patch_certificate": str(PATCH_PATH.relative_to(ROOT)),
        "source_openqasm3_structural_roundtrip_gate": str(ROUNDTRIP_PATH.relative_to(ROOT)),
        "source_openqasm3_linear_span_replay_certificate": str(SPAN_PATH.relative_to(ROOT)),
        "claim_boundary": {
            "supported_claim": (
                "The project-local OpenQASM 3 candidate inherits the selected line-268 and "
                "line-1381 composable local-unitary patch certificate because the OpenQASM 2 "
                "candidate and OpenQASM 3 artifact normalize to the same instruction stream, "
                "and the OpenQASM 3 branch already has a finite-span replay certificate."
            ),
            "qiskit_loader_parse_claimed": False,
            "symbolic_unitary_equivalence_claimed": False,
            "arbitrary_input_equivalence_claimed": False,
            "full_hilbert_space_certificate_claimed": False,
            "local_u3_pricing_accepted": False,
            "resource_saving_claimed": False,
            "b7_ledger_improvement_claimed": False,
            "unsupported_claims": [
                "This is not a Qiskit OpenQASM 3 loader parse.",
                "This is not a symbolic exact full-circuit unitary proof.",
                "This is not arbitrary-input or full-Hilbert-space coverage.",
                "This does not recover the dropped line-1378 overlap delta.",
                "This does not price or eliminate the remaining line-1381 off-grid local-U3 parameters.",
                "This does not improve the B7 resource ledger.",
            ],
        },
        "summary": summary,
        "validation_errors": errors,
    }

    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    if errors:
        raise SystemExit("OpenQASM3 composable patch lift gate failed: " + "; ".join(errors))


def render_markdown(payload: dict) -> str:
    summary = payload["summary"]
    claims = payload["claim_boundary"]
    return "\n".join(
        [
            "# B1/B7 cone_01 OpenQASM 3 Composable Patch Lift Gate",
            "",
            f"- Method: `{payload['method']}`",
            f"- Status: `{payload['status']}`",
            f"- Model status: `{payload['model_status']}`",
            f"- Workload: `{payload['workload']}`",
            f"- QASM2 candidate: `{summary['qasm2_candidate_path']}`",
            f"- OpenQASM 3 artifact: `{summary['openqasm3_candidate_path']}`",
            "",
            "## Evidence",
            "",
            f"- Normalized stream match / mismatches / length delta: {summary['normalized_streams_match']} / {summary['stream_mismatch_count']} / {summary['stream_length_delta']}",
            f"- Normalized instruction count / SHA-256: {summary['normalized_instruction_count']} / `{summary['normalized_stream_sha256']}`",
            f"- Selected patches / lines / dropped overlap lines: {summary['selected_patch_count']} / {summary['selected_line_numbers']} / {summary['dropped_overlap_candidate_line_numbers']}",
            f"- Non-overlap / local-unitary certificates: {summary['all_selected_windows_nonoverlap']} / {summary['all_local_unitary_certificates_passed']}",
            f"- Max selected patch residual / entry error: {summary['max_selected_patch_residual_norm']} / {summary['max_selected_patch_entry_error']}",
            f"- OpenQASM 3 finite-span certificate / subspace: {summary['finite_openqasm3_linear_span_certificate_passed']} / {summary['openqasm3_certified_input_subspace_dimension']} of {summary['openqasm3_full_input_space_dimension']}",
            f"- OpenQASM 3 linear-span spectral error: {summary['openqasm3_linear_span_error_spectral_norm']}",
            f"- Source / OpenQASM 3 CNOT count / delta: {summary['source_cnot_count']} / {summary['openqasm3_cnot_count']} / {summary['openqasm3_cnot_delta']}",
            "",
            "## Claim Boundary",
            "",
            claims["supported_claim"],
            "",
            "Unsupported claims:",
            "",
            *[f"- {item}" for item in claims["unsupported_claims"]],
            "",
            "## Next Gates",
            "",
            "- Replace project-local parsing with an independent OpenQASM 3 loader-backed replay.",
            "- Upgrade finite-span evidence toward symbolic or full-space local-unitary proof pressure.",
            "- Price the line-1381 off-grid local-U3 parameters under an honest fault-tolerant ledger before any B7 credit.",
            "",
        ]
    )


if __name__ == "__main__":
    main()
