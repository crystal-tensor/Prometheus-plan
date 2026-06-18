#!/usr/bin/env python3
"""Audit the public-spoofer boundary of the B4/B8 OpenQASM 3 packet."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any


METHOD = "b4_b8_openqasm3_packet_public_spoofer_gate_v0"
STATUS = "public_qasm_packet_spoofer_boundary_not_protocol_soundness"
MODEL_STATUS = "public_packet_stabilizer_emulation_guardrail_not_hardware_execution"
VERSION = "0.1"
SOURCE_METHOD = "b4_b8_openqasm3_randomized_measurement_packet_v0"


QUBIT_RE = re.compile(r"^qubit\[(\d+)\]\s+q;$")
CBIT_RE = re.compile(r"^bit\[(\d+)\]\s+c;$")
X_RE = re.compile(r"^x\s+q\[(\d+)\];$")
CX_RE = re.compile(r"^cx\s+q\[(\d+)\],\s*q\[(\d+)\];$")
MEASURE_RE = re.compile(r"^c\[(\d+)\]\s*=\s*measure\s+q\[(\d+)\];$")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_public_qasm3_deterministic_subset(qasm_text: str) -> dict[str, Any]:
    qubit_count: int | None = None
    classical_bit_count: int | None = None
    qubits: list[int] | None = None
    classical_bits: list[int | None] | None = None
    unsupported: list[str] = []
    operation_counts = {"x": 0, "cx": 0, "measure": 0}
    measured_pairs: list[dict[str, int]] = []

    for raw_line in qasm_text.splitlines():
        line = raw_line.strip()
        if not line or line == 'include "stdgates.inc";' or line == "OPENQASM 3.0;":
            continue
        if match := QUBIT_RE.match(line):
            qubit_count = int(match.group(1))
            qubits = [0] * qubit_count
            continue
        if match := CBIT_RE.match(line):
            classical_bit_count = int(match.group(1))
            classical_bits = [None] * classical_bit_count
            continue
        if match := X_RE.match(line):
            if qubits is None:
                unsupported.append(f"x before qubit declaration: {line}")
                continue
            idx = int(match.group(1))
            qubits[idx] ^= 1
            operation_counts["x"] += 1
            continue
        if match := CX_RE.match(line):
            if qubits is None:
                unsupported.append(f"cx before qubit declaration: {line}")
                continue
            control = int(match.group(1))
            target = int(match.group(2))
            qubits[target] ^= qubits[control]
            operation_counts["cx"] += 1
            continue
        if match := MEASURE_RE.match(line):
            if qubits is None or classical_bits is None:
                unsupported.append(f"measure before declarations: {line}")
                continue
            classical = int(match.group(1))
            qubit = int(match.group(2))
            classical_bits[classical] = qubits[qubit]
            measured_pairs.append({"classical_bit": classical, "qubit": qubit, "value": qubits[qubit]})
            operation_counts["measure"] += 1
            continue
        unsupported.append(line)

    if qubit_count is None:
        unsupported.append("missing qubit declaration")
    if classical_bit_count is None:
        unsupported.append("missing classical bit declaration")
    if classical_bits is None:
        predicted_bits: list[int] = []
    else:
        predicted_bits = [int(bit) if bit is not None else -1 for bit in classical_bits]
        if any(bit is None for bit in classical_bits):
            unsupported.append("not all classical bits are measured")

    return {
        "qubit_count": qubit_count,
        "classical_bit_count": classical_bit_count,
        "operation_counts": operation_counts,
        "measured_pairs": measured_pairs,
        "unsupported_lines": unsupported,
        "deterministic_subset_supported": not unsupported,
        "predicted_classical_bits": predicted_bits,
        "predicted_memory": "".join(str(bit) for bit in reversed(predicted_bits)) if predicted_bits else "",
    }


def build_gate(source_packet: Path) -> dict[str, Any]:
    started = time.time()
    packet = read_json(source_packet)
    rows: list[dict[str, Any]] = []
    exact_match_count = 0
    unsupported_file_count = 0
    deterministic_classical_file_count = 0

    for circuit in packet.get("circuits", []):
        qasm_path = Path(circuit["path"])
        qasm_text = qasm_path.read_text(encoding="utf-8")
        parsed = parse_public_qasm3_deterministic_subset(qasm_text)
        unsupported = parsed["unsupported_lines"]
        if unsupported:
            unsupported_file_count += 1
        op_counts = parsed["operation_counts"]
        deterministic_classical = (
            parsed["deterministic_subset_supported"]
            and op_counts["measure"] == circuit.get("measure_count")
            and op_counts["cx"] == circuit.get("cnot_count")
            and op_counts["x"] == circuit.get("x_count")
        )
        if deterministic_classical:
            deterministic_classical_file_count += 1
        expected_match = deterministic_classical
        if expected_match:
            exact_match_count += 1
        rows.append(
            {
                "task_id": circuit["task_id"],
                "refresh_mode": circuit["refresh_mode"],
                "packet_index": circuit["packet_index"],
                "path": circuit["path"],
                "total_qubits": circuit["total_qubits"],
                "classical_bits": circuit["classical_bits"],
                "operation_counts_match_packet_metadata": deterministic_classical,
                "unsupported_line_count": len(unsupported),
                "unsupported_lines": unsupported[:5],
                "public_deterministic_emulator_exact_match": expected_match,
                "predicted_memory": parsed["predicted_memory"],
                "predicted_bit_weight": int(sum(parsed["predicted_classical_bits"])),
            }
        )

    packet_circuit_count = len(packet.get("circuits", []))
    prediction_success_rate = exact_match_count / packet_circuit_count if packet_circuit_count else 0.0
    report = {
        "benchmark_id": "B4_B8",
        "problem_ids": [16, 30, 11],
        "title": "B4/B8 OpenQASM 3 public-packet spoofer boundary",
        "version": VERSION,
        "last_updated": time.strftime("%Y-%m-%d"),
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "method": METHOD,
        "source_method": SOURCE_METHOD,
        "source_packet_result": str(source_packet),
        "source_packet_status": packet.get("status"),
        "packet_circuit_count": packet_circuit_count,
        "parsed_circuit_count": len(rows),
        "deterministic_classical_file_count": deterministic_classical_file_count,
        "unsupported_file_count": unsupported_file_count,
        "public_qasm_structure_exposes_verifier_circuit": True,
        "public_qasm_contains_private_challenge_material": True,
        "public_stabilizer_emulator_exact_match_count": exact_match_count,
        "public_stabilizer_emulator_prediction_success_rate": prediction_success_rate,
        "public_packet_spoofer_acceptance_rate": prediction_success_rate,
        "public_packet_contract_soundness_rejected": prediction_success_rate >= 1.0,
        "late_bound_private_challenges_required": True,
        "real_backend_or_hardware_execution_still_required": True,
        "hardware_execution_performed": False,
        "real_backend_properties_used": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "sampling_hardness_proved": False,
        "cryptographic_soundness_proved": False,
        "protocol_soundness_proved": False,
        "rows": rows,
        "claim_boundary": {
            "what_is_supported": (
                "The current OpenQASM 3 packet is a public executable circuit artifact. "
                "For this generated deterministic X/CX/measure subset, a public parser/emulator can "
                "predict every measurement transcript from the packet text."
            ),
            "what_is_not_supported": (
                "This does not attack a private interactive protocol, does not use real backend "
                "properties, does not execute hardware, and does not prove or disprove quantum advantage."
            ),
            "next_gate": (
                "Late-bind private challenge flips/masks after circuit publication, replace public packet "
                "tests with backend/hardware execution, or attack a protocol transcript whose private "
                "challenge material is not embedded in public QASM."
            ),
        },
        "runtime_seconds": round(time.time() - started, 6),
    }
    report["validation_errors"] = validate_report(report)
    return report


def validate_report(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if report.get("status") != STATUS:
        errors.append("status mismatch")
    if report.get("method") != METHOD:
        errors.append("method mismatch")
    if report.get("source_method") != SOURCE_METHOD:
        errors.append("source method mismatch")
    if report.get("packet_circuit_count") != 36:
        errors.append("source packet should contain 36 circuits")
    if report.get("parsed_circuit_count") != report.get("packet_circuit_count"):
        errors.append("parsed circuit count must equal packet circuit count")
    if report.get("unsupported_file_count") != 0:
        errors.append("all packet QASM files should be inside the deterministic parsed subset")
    if report.get("deterministic_classical_file_count") != report.get("packet_circuit_count"):
        errors.append("all current packet files should be deterministic X/CX/measure circuits")
    if report.get("public_stabilizer_emulator_prediction_success_rate") != 1.0:
        errors.append("public packet emulator should exactly predict the current packet transcripts")
    if report.get("public_packet_contract_soundness_rejected") is not True:
        errors.append("public packet contract soundness should be rejected as a protocol claim")
    if report.get("late_bound_private_challenges_required") is not True:
        errors.append("late-bound private challenges should be required")
    if report.get("hardware_execution_performed") is not False:
        errors.append("must not claim hardware execution")
    for field in [
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
        "# B4/B8 OpenQASM 3 Public-Packet Spoofer Boundary v0.1",
        "",
        f"Last updated: {report['last_updated']}",
        "",
        f"Status: **{report['status']}**",
        "",
        "## Summary",
        "",
        f"- Source packet: `{report['source_packet_result']}`",
        f"- Packet circuits parsed: {report['parsed_circuit_count']} / {report['packet_circuit_count']}",
        f"- Deterministic X/CX/measure files: {report['deterministic_classical_file_count']}",
        f"- Unsupported QASM files: {report['unsupported_file_count']}",
        f"- Public emulator exact matches: {report['public_stabilizer_emulator_exact_match_count']}",
        f"- Public emulator prediction success rate: {report['public_stabilizer_emulator_prediction_success_rate']:.3f}",
        f"- Public packet spoofer acceptance rate: {report['public_packet_spoofer_acceptance_rate']:.3f}",
        "",
        "## Interpretation",
        "",
        (
            "The OpenQASM 3 packet is useful as a reproducible executable circuit artifact, "
            "but it is not itself a sound public verification protocol. The generated packet "
            "contains deterministic X/CX/measure verifier circuits. A parser that reads the public "
            "QASM can emulate the transcript exactly for all packet files."
        ),
        "",
        "This rejects a public-packet soundness claim and turns the next gate into a protocol-design requirement: "
        "private challenge material must be late-bound, or the packet must be used inside real backend/hardware "
        "execution where the public text is not the entire verification transcript.",
        "",
        "## Claim Boundary",
        "",
        "- Not hardware execution.",
        "- Not real backend properties.",
        "- Not cryptographic soundness.",
        "- Not sampling hardness.",
        "- Not quantum advantage.",
        "- Not BQP separation.",
        "- Not an attack on a private interactive protocol.",
        "",
        "## Next Gate",
        "",
        (
            "Build a late-bound challenge packet where verifier masks or challenge flips are not embedded "
            "in public QASM, or run the packet under real backend/hardware conditions and attack the resulting "
            "transcripts with stronger learned/generative spoofers."
        ),
        "",
        "## Validation",
        "",
        f"- Validation errors: {len(report['validation_errors'])}",
    ]
    if report["validation_errors"]:
        lines.extend([f"  - {error}" for error in report["validation_errors"]])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-packet",
        type=Path,
        default=Path("results/B4_B8_openqasm3_randomized_measurement_packet_v0.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("results/B4_B8_openqasm3_packet_public_spoofer_gate_v0.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("research/B4_B8_openqasm3_packet_public_spoofer_gate.md"),
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    report = build_gate(args.source_packet)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_output.write_text(markdown(report), encoding="utf-8")
    if args.pretty:
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "packet_circuit_count": report["packet_circuit_count"],
                    "prediction_success_rate": report["public_stabilizer_emulator_prediction_success_rate"],
                    "public_packet_contract_soundness_rejected": report[
                        "public_packet_contract_soundness_rejected"
                    ],
                    "validation_error_count": len(report["validation_errors"]),
                },
                indent=2,
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
