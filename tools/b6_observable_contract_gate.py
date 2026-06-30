#!/usr/bin/env python3
"""B6/T-B6-005e observable contract gate.

This gate consumes the B6 backend replay scout and turns its remaining R7/R8
observable blockers into concrete DFT/B5 packet schemas. It does not fabricate
DFT or B5 rows and does not promote B6 to a materials-discovery claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


METHOD = "b6_observable_contract_gate_v0"
STATUS = "observable_contract_open_missing_dft_b5_rows"
MODEL_STATUS = "backend_replay_ready_for_observable_packets_but_no_observable_rows"
FAILED_IDS = ["O5", "O6"]
REQUIRED_DFT_KEYS = [
    "material_id",
    "structure_ref",
    "functional",
    "pseudopotential_or_basis",
    "kpoint_density",
    "energy_per_atom_ev",
    "fermi_level_ev",
    "density_of_states_at_fermi",
    "magnetic_moment_mu_b",
    "relaxation_status",
    "calculation_hash",
]
REQUIRED_B5_KEYS = [
    "material_id",
    "effective_model",
    "orbital_basis",
    "interaction_u_ev",
    "hopping_t_ev",
    "filling",
    "response_observable",
    "response_value",
    "denominator_method",
    "solver_trace_hash",
    "same_access_cost_units",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def requirement(req_id: str, label: str, passed: bool, evidence: dict[str, Any]) -> dict[str, Any]:
    return {
        "requirement_id": req_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def build_payload(root: Path) -> dict[str, Any]:
    replay = load_json(root / "results/B6_backend_replay_scout_v0.json")
    source_hash = replay.get("source_table_hash")
    formula_hash = replay.get("replay_formula_hash")
    replay_hash = replay.get("replay_table_hash")
    dft_schema_hash = stable_hash(REQUIRED_DFT_KEYS)
    b5_schema_hash = stable_hash(REQUIRED_B5_KEYS)
    packets = [
        {
            "packet_id": "B6-O1-dft-row-schema",
            "title": "Submit DFT observable rows",
            "required_keys": REQUIRED_DFT_KEYS,
            "acceptance": [
                "at least one row for each ranked material promoted by the replay",
                "calculation_hash must bind structure, method, and numerical settings",
                "units and relaxation status must be explicit",
            ],
        },
        {
            "packet_id": "B6-O2-b5-row-schema",
            "title": "Submit B5-computed observable rows",
            "required_keys": REQUIRED_B5_KEYS,
            "acceptance": [
                "rows must name the effective model and orbital basis",
                "same-access cost units must be recorded",
                "solver_trace_hash must bind the response computation",
            ],
        },
        {
            "packet_id": "B6-O3-hash-preservation",
            "title": "Preserve replay hashes",
            "required_hashes": {
                "source_table_hash": source_hash,
                "replay_formula_hash": formula_hash,
                "replay_table_hash": replay_hash,
            },
            "acceptance": [
                "observable PRs must not silently change the replay table",
                "any row-scope change requires a new replay artifact and audit",
            ],
        },
        {
            "packet_id": "B6-O4-join-key-audit",
            "title": "Join observables to replayed materials",
            "required_keys": ["material_id"],
            "acceptance": [
                "every observable row joins to a replay material_id",
                "duplicate material_id rows must explain method or setting differences",
            ],
        },
        {
            "packet_id": "B6-O5-claim-boundary-audit",
            "title": "Prevent observable rows from becoming premature discovery claims",
            "required_claims": [
                "material_discovery_claimed=false",
                "mechanism_solved=false",
                "solution_claimed=false",
            ],
            "acceptance": [
                "DFT/B5 rows can promote evidence gates only after audit",
                "ranked candidates remain hypotheses until external validation exists",
            ],
        },
    ]
    requirements = [
        requirement(
            "O1",
            "backend replay source exists",
            replay.get("method") == "b6_backend_replay_scout_v0",
            {"method": replay.get("method"), "status": replay.get("status")},
        ),
        requirement(
            "O2",
            "replay hashes are preserved",
            bool(source_hash and formula_hash and replay_hash),
            {
                "source_table_hash": source_hash,
                "replay_formula_hash": formula_hash,
                "replay_table_hash": replay_hash,
            },
        ),
        requirement(
            "O3",
            "DFT row schema is declared",
            len(REQUIRED_DFT_KEYS) == 11,
            {"dft_schema_hash": dft_schema_hash, "required_dft_key_count": len(REQUIRED_DFT_KEYS)},
        ),
        requirement(
            "O4",
            "B5 row schema is declared",
            len(REQUIRED_B5_KEYS) == 11,
            {"b5_schema_hash": b5_schema_hash, "required_b5_key_count": len(REQUIRED_B5_KEYS)},
        ),
        requirement(
            "O5",
            "DFT observable rows exist",
            False,
            {"dft_observable_rows": replay.get("dft_observable_rows", 0)},
        ),
        requirement(
            "O6",
            "B5-computed observable rows exist",
            False,
            {"b5_computed_observable_rows": replay.get("b5_computed_observable_rows", 0)},
        ),
    ]
    failed = [row for row in requirements if not row["passed"]]
    return {
        "benchmark_id": "B6",
        "method": METHOD,
        "status": STATUS,
        "model_status": MODEL_STATUS,
        "source_backend_replay_status": replay.get("status"),
        "selected_variant": replay.get("selected_variant"),
        "source_table_hash": source_hash,
        "replay_formula_hash": formula_hash,
        "replay_table_hash": replay_hash,
        "dft_schema_hash": dft_schema_hash,
        "b5_schema_hash": b5_schema_hash,
        "observable_packet_count": len(packets),
        "observable_packets": packets,
        "observable_contract_requirement_count": len(requirements),
        "observable_contract_requirements_passed": len(requirements) - len(failed),
        "observable_contract_requirements_failed": len(failed),
        "failed_observable_contract_requirement_ids": [row["requirement_id"] for row in failed],
        "required_dft_key_count": len(REQUIRED_DFT_KEYS),
        "required_b5_key_count": len(REQUIRED_B5_KEYS),
        "dft_observable_rows": 0,
        "b5_computed_observable_rows": 0,
        "requirements": requirements,
        "claims": {
            "observable_contract_built": True,
            "dft_observable_claimed": False,
            "b5_computed_observable_claimed": False,
            "material_discovery_claimed": False,
            "mechanism_solved": False,
            "solution_claimed": False,
        },
        "claim_boundary": {
            "what_is_supported": "Observable packet schemas and hash-preservation requirements are now explicit.",
            "what_is_not_supported": "No DFT or B5 observable rows exist yet, and no material discovery or mechanism solution is claimed.",
            "next_gate": "Submit DFT and B5 rows that satisfy the declared schemas and preserve replay hashes.",
        },
        "validation_errors": [],
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# B6 Observable Contract Gate",
        "",
        f"Status: **{payload['status']}**",
        "",
        "## Summary",
        "",
        f"- Method: `{payload['method']}`",
        f"- Requirements passed / failed: {payload['observable_contract_requirements_passed']} / {payload['observable_contract_requirements_failed']}",
        f"- Failed requirement IDs: {', '.join(payload['failed_observable_contract_requirement_ids'])}",
        f"- Observable packets: {payload['observable_packet_count']}",
        f"- DFT schema hash: `{payload['dft_schema_hash']}`",
        f"- B5 schema hash: `{payload['b5_schema_hash']}`",
        f"- DFT rows / B5 rows: {payload['dft_observable_rows']} / {payload['b5_computed_observable_rows']}",
        "",
        "## Packets",
        "",
    ]
    for packet in payload["observable_packets"]:
        lines.append(f"- {packet['packet_id']}: {packet['title']}")
    lines.extend(["", "## Requirement Results", ""])
    for row in payload["requirements"]:
        mark = "PASS" if row["passed"] else "FAIL"
        lines.append(f"- {row['requirement_id']} [{mark}]: {row['label']}")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            f"- Supported: {payload['claim_boundary']['what_is_supported']}",
            f"- Not supported: {payload['claim_boundary']['what_is_not_supported']}",
            f"- Next gate: {payload['claim_boundary']['next_gate']}",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path, default=Path("results/B6_observable_contract_gate_v0.json"))
    parser.add_argument("--markdown-output", type=Path, default=Path("research/B6_observable_contract_gate.md"))
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    payload = build_payload(root)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(payload, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_markdown(payload, args.markdown_output)
    print(payload["status"])
    print(
        payload["observable_contract_requirements_passed"],
        payload["observable_contract_requirements_failed"],
        payload["failed_observable_contract_requirement_ids"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
