#!/usr/bin/env python3
"""Build the immutable R146 cross-snapshot transfer contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256


PROTOCOL_PATH = "results/B4_B8_R146_cross_snapshot_transfer_protocol_v0.json"
CONTRACT_PATH = "benchmarks/B4_B8_R146_cross_snapshot_transfer_contract_v0.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    protocol = json.loads((root / PROTOCOL_PATH).read_text())
    contract = {
        "contract_id": "B4-B8-R146-cross-snapshot-transfer-contract-v0",
        "contract_status": "public_preregistration_challenge_unopened",
        "target_id": "T-B4-002bb/T-B8-003bf/T-B10-009at",
        "upstream_target_id": protocol["source_target_id"],
        "research_question": "Can every R143 route transfer to both other fake-backend calibration snapshots without material portfolio or target-specific regression?",
        "source_bindings": {
            "protocol_path": PROTOCOL_PATH,
            "protocol_sha256": file_sha256(root / PROTOCOL_PATH),
            "protocol_payload_hash": protocol["payload_hash"],
            **protocol["source_bindings"],
        },
        "challenge_protocol": protocol["protocol"],
        "acceptance_conditions": [
            {"condition_id": "A1", "condition": "protocol, route identities, task builder, and source hashes remain exact"},
            {"condition_id": "A2", "condition": "24 transfer groups produce 192 three-arm rows and 576 executions"},
            {"condition_id": "A3", "condition": "all transferred and target-specific compiled routes retain semantic fidelity at least 0.9999999999"},
            {"condition_id": "A4", "condition": "portfolio transfer-automatic mean is at least -0.005 and bootstrap lower is at least -0.01"},
            {"condition_id": "A5", "condition": "portfolio transfer-target mean is at least -0.005 and bootstrap lower is at least -0.01"},
            {"condition_id": "A6", "condition": "at least 20 of 24 groups have mean transfer-target delta at least -0.02"},
            {"condition_id": "A7", "condition": "zero rows have transfer-target regression below -0.05"},
            {"condition_id": "A8", "condition": "each target snapshot has mean transfer-target delta at least -0.01"},
            {"condition_id": "A9", "condition": "challenge commitment, hidden seeds, row hashes, reveal, and transcript replay"},
            {"condition_id": "A10", "condition": "temporal calibration, cross-machine, hardware, advantage, BQP, solved-frontier, and credit claims remain false"},
        ],
        "phase_protocol": [
            "commit a fresh secret after public preregistration",
            "derive hidden transpiler, simulator, and bootstrap seeds",
            "compile both frozen route identities on each target snapshot",
            "execute all three arms with one shared simulator seed per row",
            "write 192 rows before secret reveal",
            "reveal and verify the acceptance transcript",
        ],
        "claim_boundary": {
            "positive_result_requires_all_conditions": True,
            "what_is_not_supported_even_if_accepted": "temporal same-device calibration transfer, cross-machine transfer, real hardware, mitigation, protocol soundness, quantum advantage, BQP separation, or solved B4/B8/B10",
        },
    }
    output = root / CONTRACT_PATH
    write_json(output, contract)
    print(file_sha256(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
