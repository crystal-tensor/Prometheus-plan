#!/usr/bin/env python3
"""T-B4-002c/T-B8-003g noise-modeled transcript bridge for B4/B8.

This consumes the verifier-private challenge protocol model and adds a bounded
transcript-noise/leakage cascade. It is not hardware execution and not a
protocol-soundness proof.
"""

import argparse
import json
import time
from pathlib import Path


METHOD = "b4_b8_verifier_private_challenge_noise_bridge_v0"
STATUS = "private_challenge_noise_transcript_bridge_not_hardware"
SOURCE_METHOD = "b4_b8_verifier_private_challenge_protocol_v0"

NOISE_PROFILES = {
    "ideal": 0.0,
    "mild": 0.01,
    "stressed": 0.03,
    "backend_like": 0.0703125,
}

MODE_ERROR_MULTIPLIERS = {
    "no_refresh": 1.0,
    "challenge_refresh": 0.75,
    "refresh_plus_rotation": 0.5,
}

LEAKAGE_PROFILES = {
    "no_leak": 0,
    "support_only_public_structure": 0,
    "one_private_bit_leak": 1,
    "three_private_bit_leak": 3,
    "full_private_material_leak": 4,
}


def _round(value):
    return round(float(value), 12)


def adversary_acceptance(private_bits, known_bits, bit_error):
    known = min(known_bits, private_bits)
    unknown = private_bits - known
    return ((1.0 - bit_error) ** known) * (0.5**unknown)


def build(protocol_json):
    protocol = json.loads(Path(protocol_json).read_text())
    if protocol.get("method") != SOURCE_METHOD:
        raise ValueError(f"expected source method {SOURCE_METHOD}, got {protocol.get('method')}")
    rows = protocol.get("protocol_rows", [])
    private_bits = int(protocol.get("private_predicate_bit_count", 4))
    transcript_rows = []
    for row in rows:
        mode = row["mode"]
        mode_multiplier = MODE_ERROR_MULTIPLIERS[mode]
        for noise_name, base_error in NOISE_PROFILES.items():
            effective_error = base_error * mode_multiplier
            honest_acceptance = (1.0 - effective_error) ** private_bits
            for leakage_name, known_bits in LEAKAGE_PROFILES.items():
                acceptance = adversary_acceptance(private_bits, known_bits, effective_error)
                transcript_rows.append(
                    {
                        "protocol_idx": row["idx"],
                        "task": row["task"],
                        "mode": mode,
                        "noise_profile": noise_name,
                        "base_predicate_bit_error": _round(base_error),
                        "effective_predicate_bit_error": _round(effective_error),
                        "leakage_profile": leakage_name,
                        "known_private_bits": known_bits,
                        "honest_acceptance": _round(honest_acceptance),
                        "adversary_acceptance": _round(acceptance),
                    }
                )

    by_mode_noise = {}
    for mode in MODE_ERROR_MULTIPLIERS:
        for noise_name in NOISE_PROFILES:
            subset = [
                row
                for row in transcript_rows
                if row["mode"] == mode
                and row["noise_profile"] == noise_name
                and row["leakage_profile"] == "no_leak"
            ]
            by_mode_noise[f"{mode}|{noise_name}"] = {
                "honest_acceptance": subset[0]["honest_acceptance"],
                "no_leak_acceptance": subset[0]["adversary_acceptance"],
            }

    backend_no_refresh = by_mode_noise["no_refresh|backend_like"]["honest_acceptance"]
    backend_challenge = by_mode_noise["challenge_refresh|backend_like"]["honest_acceptance"]
    backend_rotation = by_mode_noise["refresh_plus_rotation|backend_like"]["honest_acceptance"]
    max_no_leak = max(
        row["adversary_acceptance"]
        for row in transcript_rows
        if row["leakage_profile"] == "no_leak"
    )
    max_three_leak = max(
        row["adversary_acceptance"]
        for row in transcript_rows
        if row["leakage_profile"] == "three_private_bit_leak"
    )
    max_full_leak = max(
        row["adversary_acceptance"]
        for row in transcript_rows
        if row["leakage_profile"] == "full_private_material_leak"
    )

    gate_results = {
        "G1_source_protocol_rows_present": len(rows) == 36,
        "G2_transcript_cases_present": len(transcript_rows) == 720,
        "G3_backend_like_refresh_modes_keep_honest_ge_0p8": min(backend_challenge, backend_rotation) >= 0.8,
        "G4_backend_like_no_refresh_honest_fails_0p8": backend_no_refresh < 0.8,
        "G5_no_leak_acceptance_stays_at_guessing_floor": max_no_leak == 0.0625,
        "G6_three_bit_leakage_remains_high_risk": max_three_leak >= 0.45,
        "G7_full_private_material_leakage_breaks_gate": max_full_leak >= 0.99,
        "G8_no_hardware_or_soundness_claim": True,
    }
    validation_errors = []
    if not all(gate_results.values()):
        validation_errors.append("one or more transcript bridge gates failed")

    return {
        "benchmark": "B4/B8",
        "benchmark_id": "B4_B8",
        "method": METHOD,
        "source_method": SOURCE_METHOD,
        "status": STATUS,
        "model_status": "noise_modeled_transcript_bridge_not_hardware",
        "protocol": protocol.get("protocol"),
        "protocol_row_count": len(rows),
        "transcript_case_count": len(transcript_rows),
        "noise_profile_count": len(NOISE_PROFILES),
        "leakage_profile_count": len(LEAKAGE_PROFILES),
        "private_predicate_bit_count": private_bits,
        "backend_like_no_refresh_honest_acceptance": backend_no_refresh,
        "backend_like_challenge_refresh_honest_acceptance": backend_challenge,
        "backend_like_refresh_plus_rotation_honest_acceptance": backend_rotation,
        "max_no_leak_adversary_acceptance": _round(max_no_leak),
        "max_three_private_bit_leak_acceptance": _round(max_three_leak),
        "max_full_private_material_leak_acceptance": _round(max_full_leak),
        "backend_like_refresh_modes_pass_honest_threshold": min(backend_challenge, backend_rotation) >= 0.8,
        "backend_like_no_refresh_fails_honest_threshold": backend_no_refresh < 0.8,
        "full_private_material_leakage_breaks_protocol": max_full_leak >= 0.99,
        "hardware_execution_performed": False,
        "real_backend_properties_used": False,
        "quantum_advantage_claimed": False,
        "bqp_separation_claimed": False,
        "sampling_hardness_proved": False,
        "cryptographic_soundness_proved": False,
        "protocol_soundness_proved": False,
        "acceptance_gate_count": len(gate_results),
        "passed_gate_count": sum(1 for passed in gate_results.values() if passed),
        "failed_gate_count": sum(1 for passed in gate_results.values() if not passed),
        "gate_results": gate_results,
        "mode_noise_summary": by_mode_noise,
        "transcript_rows": transcript_rows,
        "validation_errors": validation_errors,
        "validation_error_count": len(validation_errors),
        "timestamp": time.time(),
    }


def render_markdown(payload):
    return "\n".join(
        [
            "# B4/B8 Verifier-Private Challenge Noise Bridge",
            "",
            "- Gate: T-B4-002c / T-B8-003g",
            f"- Method: `{payload['method']}`",
            f"- Status: `{payload['status']}`",
            f"- Transcript cases: {payload['transcript_case_count']}",
            f"- Gates passed: {payload['passed_gate_count']} / {payload['acceptance_gate_count']}",
            "",
            "## Result",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| backend-like no-refresh honest acceptance | {payload['backend_like_no_refresh_honest_acceptance']} |",
            f"| backend-like challenge-refresh honest acceptance | {payload['backend_like_challenge_refresh_honest_acceptance']} |",
            f"| backend-like refresh-plus-rotation honest acceptance | {payload['backend_like_refresh_plus_rotation_honest_acceptance']} |",
            f"| max no-leak adversary acceptance | {payload['max_no_leak_adversary_acceptance']} |",
            f"| max three-private-bit leakage acceptance | {payload['max_three_private_bit_leak_acceptance']} |",
            f"| max full-private-material leakage acceptance | {payload['max_full_private_material_leak_acceptance']} |",
            "",
            "## Interpretation",
            "",
            "The bridge keeps the formal private challenge protocol at model level. Under the backend-like predicate-bit error profile, no-refresh honest acceptance falls below the 0.8 gate, while challenge-refresh and refresh-plus-rotation stay above it. No-leak adversaries remain at the 1/16 guessing floor, but full private-material leakage still breaks the gate.",
            "",
            "## Claim Boundary",
            "",
            "- This is a noise-modeled transcript bridge, not hardware execution.",
            "- It does not use real backend properties.",
            "- It does not prove cryptographic or protocol soundness.",
            "- It does not claim quantum advantage or BQP separation.",
            "",
        ]
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protocol-json",
        type=Path,
        default=Path("results/B4_B8_verifier_private_challenge_protocol_v0.json"),
    )
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--md-out", type=Path, required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    payload = build(args.protocol_json)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.md_out.write_text(render_markdown(payload), encoding="utf-8")
    print(json.dumps(payload if args.pretty else {
        "status": payload["status"],
        "transcript_case_count": payload["transcript_case_count"],
        "passed_gate_count": payload["passed_gate_count"],
        "failed_gate_count": payload["failed_gate_count"],
        "backend_like_no_refresh_honest_acceptance": payload["backend_like_no_refresh_honest_acceptance"],
        "backend_like_refresh_plus_rotation_honest_acceptance": payload["backend_like_refresh_plus_rotation_honest_acceptance"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
