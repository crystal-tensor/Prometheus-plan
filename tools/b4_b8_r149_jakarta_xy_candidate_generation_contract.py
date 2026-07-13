#!/usr/bin/env python3
"""Build the immutable R149 Jakarta dense-XY generated-route contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from b4_b8_r119_private_observable_bundle_gate import write_json
from b4_b8_r126_calibration_attribution_ledger import file_sha256


PROTOCOL_PATH = "results/B4_B8_R149_jakarta_xy_candidate_generation_protocol_v0.json"
CONTRACT_PATH = "benchmarks/B4_B8_R149_jakarta_xy_candidate_generation_contract_v0.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    protocol = json.loads((root / PROTOCOL_PATH).read_text())
    contract = {
        "contract_id": "B4-B8-R149-jakarta-xy-candidate-generation-contract-v0",
        "contract_status": "public_preregistration_challenge_unopened",
        "target_id": "T-B4-002bh/T-B8-003bl/T-B10-009az",
        "upstream_target_id": protocol["source_target_id"],
        "research_question": "Can a newly generated Jakarta dense-XY route close the sole R148 gap without copying frozen identities or regressing the other 11 groups?",
        "source_bindings": {
            "protocol_path": PROTOCOL_PATH,
            "protocol_sha256": file_sha256(root / PROTOCOL_PATH),
            "protocol_payload_hash": protocol["payload_hash"],
            **protocol["source_bindings"],
        },
        "challenge_protocol": protocol["protocol"],
        "acceptance_conditions": [
            {"condition_id": "A1", "condition": "protocol, generated route, frozen portfolio routes, and all source hashes remain exact"},
            {"condition_id": "A2", "condition": "12 groups produce 96 rows, 296 executions, and the extra R148 arm appears only on the replacement group"},
            {"condition_id": "A3", "condition": "all repaired-portfolio and target-specific routes retain semantic fidelity at least 0.9999999999"},
            {"condition_id": "A4", "condition": "portfolio repaired-automatic mean is at least -0.005 and bootstrap lower is at least -0.01"},
            {"condition_id": "A5", "condition": "portfolio repaired-target mean is at least -0.005 and bootstrap lower is at least -0.01"},
            {"condition_id": "A6", "condition": "all 12 groups have mean repaired-target delta at least -0.02"},
            {"condition_id": "A7", "condition": "zero rows have repaired-target regression below -0.05"},
            {"condition_id": "A8", "condition": "each target mean is at least -0.01; replacement mean versus target is at least -0.02 and versus R148 foreign is at least +0.01 with zero severe rows"},
            {"condition_id": "A9", "condition": "challenge commitment, hidden seeds, row hashes, reveal, and transcript replay"},
            {"condition_id": "A10", "condition": "general generation, temporal, cross-machine, hardware, advantage, BQP, solved-frontier, and credit claims remain false"},
        ],
        "phase_protocol": [
            "commit a fresh secret after public preregistration",
            "derive hidden transpiler, simulator, and bootstrap seeds",
            "replay one generated replacement plus eleven frozen R148 routes",
            "execute target and automatic denominators plus the replacement-only R148 diagnostic arm",
            "write 96 rows before secret reveal",
            "reveal and verify the acceptance transcript",
        ],
        "claim_boundary": {
            "positive_result_requires_all_conditions": True,
            "what_is_not_supported_even_if_accepted": "general route-generation advantage, temporal same-device transfer, cross-machine transfer, real hardware, mitigation, protocol soundness, quantum advantage, BQP separation, or solved B4/B8/B10",
        },
    }
    output = root / CONTRACT_PATH
    write_json(output, contract)
    print(file_sha256(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
