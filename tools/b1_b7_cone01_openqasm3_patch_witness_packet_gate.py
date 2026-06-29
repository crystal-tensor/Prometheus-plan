#!/usr/bin/env python3
"""Build a compact OpenQASM 3 patch witness packet from the source map."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
RESEARCH = ROOT / "research"

METHOD = "b1_b7_cone01_openqasm3_patch_witness_packet_gate_v0"
STATUS = "cone01_openqasm3_patch_witness_packet_passed_without_b7_resource_credit"
MODEL_STATUS = "openqasm3_patch_witness_packet_is_reviewable_without_b7_credit"

SOURCE_MAP_PATH = RESULTS / "B1_B7_cone01_openqasm3_source_map_gate_v0.json"
PATCH_PATH = RESULTS / "B1_B7_cone01_composable_patch_certificate_gate_v0.json"
LIFT_PATH = RESULTS / "B1_B7_cone01_openqasm3_composable_patch_lift_gate_v0.json"
NONOVERLAP_PATH = RESULTS / "B1_B7_cone01_nonoverlap_patch_subset_gate_v0.json"
BOUNDED_PATCH_PATH = RESULTS / "B1_B7_cone01_bounded_replacement_patch_gate_v0.json"
QASM2_PATH = RESULTS / "B1_B7_cone01_qasm2_candidate_rewrite_gate" / "gcm_h6_line268_line1381_candidate.qasm"
QASM3_PATH = (
    RESULTS
    / "B1_B7_cone01_openqasm3_candidate_export_gate"
    / "gcm_h6_line268_line1381_candidate_openqasm3.qasm"
)
OUT_JSON = RESULTS / "B1_B7_cone01_openqasm3_patch_witness_packet_gate_v0.json"
OUT_MD = RESEARCH / "B1_B7_cone01_openqasm3_patch_witness_packet_gate.md"


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(read_text(path))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def json_hash(rows: object) -> str:
    material = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return sha256_text(material)


def line_slice(lines: list[str], start: int, end: int) -> list[str]:
    return lines[start - 1 : end]


def source_map_by_line(source_map: list[dict]) -> dict[int, dict]:
    return {int(row["qasm2_line_number"]): row for row in source_map}


def context_map_rows(source_map: list[dict], start: int, end: int) -> list[dict]:
    rows = [
        row
        for row in source_map
        if start <= int(row["qasm2_line_number"]) <= end
    ]
    return [
        {
            "instruction_index": row["instruction_index"],
            "operation": row["operation"],
            "qasm2_line_number": row["qasm2_line_number"],
            "openqasm3_line_number": row["openqasm3_line_number"],
            "normalized_instruction_sha256": row["normalized_instruction_sha256"],
        }
        for row in rows
    ]


def require(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def build_witness(
    row: dict,
    disposition: str,
    source_map: list[dict],
    qasm2_lines: list[str],
    qasm3_lines: list[str],
    selected_certificate_by_line: dict[int, dict],
    overlap_blockers_by_line: dict[int, dict],
) -> dict:
    line_number = int(row["candidate_line_number"])
    start = int(row["window_start_line"])
    end = int(row["window_end_line"])
    mapped = source_map_by_line(source_map)[line_number]
    context_rows = context_map_rows(source_map, start, end)
    certificate = selected_certificate_by_line.get(line_number, {})
    qasm2_window = "\n".join(line_slice(qasm2_lines, start, end)) + "\n"
    qasm3_window = "\n".join(line_slice(qasm3_lines, start, end)) + "\n"
    return {
        "candidate_line_number": line_number,
        "disposition": disposition,
        "repair_gate_id": row.get("repair_gate_id"),
        "support_qubits": row.get("support_qubits"),
        "source_window": {"start_line": start, "end_line": end, "line_count": end - start + 1},
        "source_map_instruction_index": mapped["instruction_index"],
        "openqasm3_line_number": mapped["openqasm3_line_number"],
        "operation": mapped["operation"],
        "normalized_instruction_sha256": mapped["normalized_instruction_sha256"],
        "source_window_qasm2_sha256": sha256_text(qasm2_window),
        "source_window_openqasm3_sha256": sha256_text(qasm3_window),
        "source_window_source_map_row_count": len(context_rows),
        "source_window_source_map_sha256": json_hash(context_rows),
        "qasm3_patch_line_count": row.get("qasm3_patch_line_count"),
        "qasm3_patch_snippet_sha256": json_hash(row.get("qasm3_patch_snippet", [])),
        "source_cnot_count": row.get("source_cnot_count"),
        "replacement_cnot_count": row.get("replacement_cnot_count"),
        "candidate_cnot_reduction": row.get("candidate_cnot_reduction"),
        "replacement_off_pi_over_four_parameter_count": row.get(
            "replacement_off_pi_over_four_parameter_count"
        ),
        "bounded_patch_exact_pass": row.get("bounded_patch_exact_pass"),
        "bounded_patch_residual_norm": row.get("bounded_patch_residual_norm"),
        "bounded_patch_max_abs_entry_error": row.get("bounded_patch_max_abs_entry_error"),
        "local_unitary_certificate_passed": certificate.get(
            "local_unitary_certificate_passed", False
        ),
        "accepted_as_selected_nonoverlap_patch": disposition == "selected_nonoverlap",
        "overlap_blocker": overlap_blockers_by_line.get(line_number),
    }


def main() -> None:
    source_map_payload = load_json(SOURCE_MAP_PATH)
    patch_payload = load_json(PATCH_PATH)
    lift_payload = load_json(LIFT_PATH)
    nonoverlap_payload = load_json(NONOVERLAP_PATH)
    bounded_patch_payload = load_json(BOUNDED_PATCH_PATH)
    qasm2_lines = read_text(QASM2_PATH).splitlines()
    qasm3_lines = read_text(QASM3_PATH).splitlines()

    source_map_summary = source_map_payload.get("summary", {})
    patch_summary = patch_payload.get("summary", {})
    lift_summary = lift_payload.get("summary", {})
    nonoverlap_summary = nonoverlap_payload.get("summary", {})
    bounded_patch_summary = bounded_patch_payload.get("summary", {})
    source_map = source_map_payload.get("source_map", [])
    selected_rows = nonoverlap_payload.get("selected_nonoverlap_patch_rows", [])
    dropped_rows = nonoverlap_payload.get("dropped_overlap_patch_rows", [])
    selected_certificate_by_line = {
        int(row["candidate_line_number"]): row
        for row in patch_summary.get("row_certificates", [])
    }
    overlap_blockers_by_line = {}
    for pair in bounded_patch_summary.get("overlapping_patch_window_pairs", []):
        left = int(pair["left_candidate_line_number"])
        right = int(pair["right_candidate_line_number"])
        overlap_blockers_by_line[left] = {
            "blocked_by_candidate_line_number": right,
            "overlap_start_line": pair["overlap_start_line"],
            "overlap_end_line": pair["overlap_end_line"],
            "overlap_line_count": pair["overlap_line_count"],
        }

    witness_rows = [
        build_witness(
            row,
            "selected_nonoverlap",
            source_map,
            qasm2_lines,
            qasm3_lines,
            selected_certificate_by_line,
            overlap_blockers_by_line,
        )
        for row in selected_rows
    ] + [
        build_witness(
            row,
            "dropped_overlap",
            source_map,
            qasm2_lines,
            qasm3_lines,
            selected_certificate_by_line,
            overlap_blockers_by_line,
        )
        for row in dropped_rows
    ]
    witness_rows = sorted(witness_rows, key=lambda row: row["candidate_line_number"])
    witness_packet_sha = json_hash(witness_rows)
    selected_witnesses = [
        row for row in witness_rows if row["disposition"] == "selected_nonoverlap"
    ]
    dropped_witnesses = [
        row for row in witness_rows if row["disposition"] == "dropped_overlap"
    ]

    errors: list[str] = []
    require(
        errors,
        source_map_payload.get("status")
        == "cone01_openqasm3_source_map_passed_without_b7_resource_credit",
        "source-map gate status changed",
    )
    require(
        errors,
        lift_payload.get("status")
        == "cone01_openqasm3_composable_patch_lift_passed_without_b7_resource_credit",
        "OpenQASM 3 patch-lift status changed",
    )
    require(
        errors,
        patch_payload.get("status")
        == "cone01_composable_patch_certificate_passed_without_b7_resource_credit",
        "composable patch certificate status changed",
    )
    require(
        errors,
        nonoverlap_payload.get("status")
        == "cone01_nonoverlap_bounded_patch_subset_not_full_circuit_replay",
        "non-overlap subset status changed",
    )
    require(errors, len(source_map) == 1878, "source-map row count changed")
    require(errors, len(qasm2_lines) == 1884, "QASM2 line count changed")
    require(errors, len(qasm3_lines) == 1884, "OpenQASM 3 line count changed")
    require(errors, patch_summary.get("selected_line_numbers") == [268, 1381], "selected lines changed")
    require(errors, patch_summary.get("dropped_overlap_candidate_line_numbers") == [1378], "dropped overlap lines changed")
    require(errors, len(witness_rows) == 3, "witness row count changed")
    require(errors, [row["candidate_line_number"] for row in witness_rows] == [268, 1378, 1381], "witness line order changed")
    require(errors, [row["source_map_instruction_index"] for row in witness_rows] == [263, 1372, 1375], "witness instruction indices changed")
    require(errors, [row["openqasm3_line_number"] for row in witness_rows] == [268, 1378, 1381], "witness OpenQASM 3 line numbers changed")
    require(errors, len(selected_witnesses) == 2, "selected witness count changed")
    require(errors, len(dropped_witnesses) == 1, "dropped witness count changed")
    require(errors, all(row["local_unitary_certificate_passed"] for row in selected_witnesses), "selected local-unitary certificates not all passed")
    require(errors, dropped_witnesses[0]["overlap_blocker"] is not None, "dropped witness missing overlap blocker")
    require(errors, max(row["bounded_patch_residual_norm"] for row in witness_rows) <= 1e-10, "bounded residual too large")
    require(errors, max(row["bounded_patch_max_abs_entry_error"] for row in witness_rows) <= 1e-10, "bounded entry error too large")
    require(errors, source_map_summary.get("raw_line_delta_count") == 0, "source-map raw-line drift changed")
    require(errors, lift_summary.get("normalized_stream_sha256") == source_map_summary.get("normalized_stream_sha256"), "lift/source-map stream hash mismatch")

    passed = not errors
    summary = {
        "source_openqasm3_source_map_gate": rel(SOURCE_MAP_PATH),
        "source_composable_patch_certificate": rel(PATCH_PATH),
        "source_openqasm3_composable_patch_lift_gate": rel(LIFT_PATH),
        "source_nonoverlap_patch_subset_gate": rel(NONOVERLAP_PATH),
        "source_bounded_replacement_patch_gate": rel(BOUNDED_PATCH_PATH),
        "qasm2_candidate_path": rel(QASM2_PATH),
        "openqasm3_candidate_path": rel(QASM3_PATH),
        "normalized_instruction_count": source_map_summary.get("normalized_instruction_count"),
        "normalized_stream_sha256": source_map_summary.get("normalized_stream_sha256"),
        "source_map_sha256": source_map_summary.get("source_map_sha256"),
        "raw_line_delta_count": source_map_summary.get("raw_line_delta_count"),
        "witness_row_count": len(witness_rows),
        "selected_witness_count": len(selected_witnesses),
        "dropped_overlap_witness_count": len(dropped_witnesses),
        "witness_candidate_line_numbers": [row["candidate_line_number"] for row in witness_rows],
        "witness_instruction_indices": [row["source_map_instruction_index"] for row in witness_rows],
        "witness_openqasm3_line_numbers": [row["openqasm3_line_number"] for row in witness_rows],
        "witness_packet_sha256": witness_packet_sha,
        "selected_candidate_cnot_reduction": patch_summary.get("selected_candidate_cnot_reduction"),
        "lost_candidate_cnot_reduction_due_to_overlap": patch_summary.get(
            "lost_candidate_cnot_reduction_due_to_overlap"
        ),
        "max_witness_residual_norm": max(row["bounded_patch_residual_norm"] for row in witness_rows),
        "max_witness_entry_error": max(row["bounded_patch_max_abs_entry_error"] for row in witness_rows),
        "selected_replacement_off_pi_over_four_parameter_count": patch_summary.get(
            "selected_replacement_off_pi_over_four_parameter_count"
        ),
        "patch_witness_packet_passed": passed,
        "accepted_project_local_openqasm3_patch_witness_packet_count": 1 if passed else 0,
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
        "status": STATUS if passed else "cone01_openqasm3_patch_witness_packet_failed",
        "model_status": MODEL_STATUS if passed else "openqasm3_patch_witness_packet_rejected",
        "workload": "qasmbench_medium_exact/gcm_h6.qasm",
        "claim_boundary": {
            "supported_claim": (
                "The OpenQASM 3 source-map evidence has been reduced into a compact "
                "three-row patch witness packet for candidate lines 268, 1378, and 1381. "
                "The packet records selected versus dropped-overlap disposition, source "
                "windows, OpenQASM 3 line mapping, context hashes, local certificate "
                "status, residuals, and resource-boundary counters."
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
        "witness_rows": witness_rows,
        "validation_errors": errors,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    if errors:
        raise SystemExit("OpenQASM3 patch witness packet gate failed: " + "; ".join(errors))


def render_markdown(payload: dict) -> str:
    summary = payload["summary"]
    claims = payload["claim_boundary"]
    rows = payload["witness_rows"]
    lines = [
        "# B1/B7 cone_01 OpenQASM 3 Patch Witness Packet Gate",
        "",
        f"- Method: `{payload['method']}`",
        f"- Status: `{payload['status']}`",
        f"- Model status: `{payload['model_status']}`",
        f"- Workload: `{payload['workload']}`",
        f"- Supported claim: {claims['supported_claim']}",
        "",
        "## Inputs",
        "",
        f"- Source-map gate: `{summary['source_openqasm3_source_map_gate']}`",
        f"- Composable patch certificate: `{summary['source_composable_patch_certificate']}`",
        f"- OpenQASM 3 patch lift: `{summary['source_openqasm3_composable_patch_lift_gate']}`",
        f"- Non-overlap subset gate: `{summary['source_nonoverlap_patch_subset_gate']}`",
        f"- Bounded replacement patch gate: `{summary['source_bounded_replacement_patch_gate']}`",
        f"- QASM2 / OpenQASM 3 candidates: `{summary['qasm2_candidate_path']}` / `{summary['openqasm3_candidate_path']}`",
        "",
        "## Packet Summary",
        "",
        f"- Normalized instruction count / stream hash: {summary['normalized_instruction_count']} / `{summary['normalized_stream_sha256']}`",
        f"- Source-map hash / raw-line drift count: `{summary['source_map_sha256']}` / {summary['raw_line_delta_count']}",
        f"- Witness rows / selected / dropped-overlap: {summary['witness_row_count']} / {summary['selected_witness_count']} / {summary['dropped_overlap_witness_count']}",
        f"- Witness candidate lines: {summary['witness_candidate_line_numbers']}",
        f"- Witness instruction indices: {summary['witness_instruction_indices']}",
        f"- Witness packet hash: `{summary['witness_packet_sha256']}`",
        f"- Selected CNOT delta / lost overlap delta: {summary['selected_candidate_cnot_reduction']} / {summary['lost_candidate_cnot_reduction_due_to_overlap']}",
        f"- Max witness residual / entry error: {summary['max_witness_residual_norm']} / {summary['max_witness_entry_error']}",
        f"- Accepted occurrence / proxy-T reduction / B7 claim: {summary['accepted_occurrence_removal']} / {summary['accepted_proxy_t_reduction']} / {summary['b7_ledger_improvement_claimed']}",
        "",
        "## Witness Rows",
        "",
        "| Line | Disposition | Instruction | Operation | Window | Support | Repair | CNOT delta | Off-grid local U3 | Residual | Entry error |",
        "| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        window = row["source_window"]
        lines.append(
            "| {line} | {disposition} | {idx} | {operation} | {start}-{end} | {support} | {repair} | {delta} | {offgrid} | {residual} | {entry} |".format(
                line=row["candidate_line_number"],
                disposition=row["disposition"],
                idx=row["source_map_instruction_index"],
                operation=row["operation"],
                start=window["start_line"],
                end=window["end_line"],
                support=row["support_qubits"],
                repair=row["repair_gate_id"],
                delta=row["candidate_cnot_reduction"],
                offgrid=row["replacement_off_pi_over_four_parameter_count"],
                residual=row["bounded_patch_residual_norm"],
                entry=row["bounded_patch_max_abs_entry_error"],
            )
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
        ]
    )
    for claim in claims["unsupported_claims"]:
        lines.append(f"- {claim}")
    lines.extend(
        [
            "",
            "## Validation",
            "",
            f"- Patch witness packet passed: {summary['patch_witness_packet_passed']}",
            f"- Validation errors: {summary['validation_error_count']}",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
