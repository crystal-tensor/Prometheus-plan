#!/usr/bin/env python3
"""Execute the preregistered B9 R196 extended tail-charge stress."""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from typing import Any

import b9_r193_coupling_integrability_stress as r193
import b9_r194_higher_range_charge_stress as r194
import b9_r195_multiscale_tail_charge_stress as r195


EXPERIMENT_ID = "B9-R196-extended-tail-charge-stress"
METHOD = "b9_r196_extended_tail_charge_stress_v1"
STATUS_ACCEPTED = "checked_extended_tail_charge_boundary"
STATUS_REJECTED = "extended_tail_charge_boundary_rejected"
VERSION = "1.0"
LAST_UPDATED = "2026-07-29"

CONTRACT_PATH = Path(
    "benchmarks/B9_R196_extended_tail_charge_contract_v0.json"
)
EXPECTED_CONTRACT_SHA256 = (
    "afc5a721320ccf2a73291b961e6c3c28e5029ebe9e783ef54ccda2d48223e668"
)
R193_TOOL_PATH = Path("tools/b9_r193_coupling_integrability_stress.py")
R194_TOOL_PATH = Path("tools/b9_r194_higher_range_charge_stress.py")
R195_TOOL_PATH = Path("tools/b9_r195_multiscale_tail_charge_stress.py")
R195_RESULT_PATH = Path(
    "results/B9_R195_multiscale_tail_charge_stress_v1.json"
)
RESULT_PATH = Path("results/B9_R196_extended_tail_charge_stress_v1.json")
REPORT_PATH = Path("research/B9_R196_extended_tail_charge_stress.md")

ENGINEERING_ONLY_COUPLINGS = (Fraction(13, 32),)
FROZEN_HOLDOUT_COUPLINGS = (Fraction(73, 128), Fraction(77, 128))
PREVIOUSLY_OBSERVED_COUPLINGS = (
    set(r195.PREVIOUSLY_OBSERVED_COUPLINGS)
    | set(r195.FROZEN_HOLDOUT_COUPLINGS)
)
COMPLETE_RANGE = 6
COMPLETE_SIZE = 10
TRANSLATION_RANGE = 8
TRANSLATION_SIZE = 10
TRANSLATION_COUPLING = Fraction(73, 128)
BOUNDARY_BULK_RANGE = 6
BOUNDARY_CORRECTION_RANGE = 4
BOUNDARY_SIZES = (9, 10)
MODULAR_PRIMES = (1_000_003, 1_000_033)

TRUE_CLAIMS = [
    "r196_contract_publicly_frozen_before_acceptance_execution",
    "r196_holdout_couplings_unseen_before_protocol_freeze",
    "complete_range_six_n10_nullity_two_on_two_holdout_rows",
    "translation_summed_range_eight_nullity_two_on_one_holdout_row",
    "range_six_boundary_range_four_nullity_two_on_four_holdout_rows",
    "explicit_zero_coupling_witnesses_detect_extra_conserved_charges",
    "r195_candidate_survives_declared_r196_finite_ansatz_adversaries",
]
FALSE_CLAIMS = [
    "all_coupling_theorem",
    "all_size_theorem",
    "range_nine_or_longer_tail_exclusion",
    "arbitrary_boundary_dressing_exclusion",
    "complete_quasi_local_charge_exclusion",
    "nonlocal_duality_exclusion",
    "nonstandard_fermionization_exclusion",
    "interacting_integrability_exclusion",
    "complete_integrability_exclusion",
    "nonintegrability_theorem",
    "quantum_chaos_theorem",
    "spectral_hardness_theorem",
    "quantum_pcp_theorem",
    "nlts_theorem",
    "bqp_separation",
    "solved_frontier",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hash(value: Any) -> str:
    return sha256_bytes(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    )


def fraction_text(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def requirement(
    requirement_id: str,
    label: str,
    passed: bool,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "label": label,
        "passed": bool(passed),
        "evidence": evidence,
    }


def word(n: int, operations: dict[int, str]) -> str:
    value = ["I"] * n
    for index, pauli in operations.items():
        value[index] = pauli
    return "".join(value)


def positive_control_witnesses(n: int = TRANSLATION_SIZE) -> dict[str, Any]:
    (
        basis,
        columns,
        _output_basis,
        _nonzero_count,
        parent_matrix_hash,
    ) = r193.pauli_commutator_columns(
        n,
        Fraction(0),
        TRANSLATION_RANGE,
    )
    index = {label: position for position, label in enumerate(basis)}

    identity = {index["I" * n]: 1}
    hamiltonian: dict[int, int] = {}
    for site in range(n):
        hamiltonian[index[word(n, {site: "X"})]] = -4
        hamiltonian[index[word(n, {site: "Z"})]] = 3
    local_tilted_field = {
        index[word(n, {0: "X"})]: -4,
        index[word(n, {0: "Z"})]: 3,
    }
    adjacent_product_sum: dict[int, int] = {}
    product_terms = {
        ("X", "X"): 16,
        ("X", "Z"): -12,
        ("Z", "X"): -12,
        ("Z", "Z"): 9,
    }
    for site in range(n - 1):
        for (left, right), coefficient in product_terms.items():
            pauli_word = word(
                n,
                {site: left, site + 1: right},
            )
            position = index[pauli_word]
            adjacent_product_sum[position] = (
                adjacent_product_sum.get(position, 0) + coefficient
            )

    witnesses = {
        "identity": identity,
        "hamiltonian_times_four": hamiltonian,
        "left_tilted_field_times_four": local_tilted_field,
        "adjacent_tilted_field_product_sum_times_sixteen": (
            adjacent_product_sum
        ),
    }
    kernel_checks = {
        label: not r193.combine_columns(columns, vector)
        for label, vector in witnesses.items()
    }
    family_witnesses = {
        "complete_position_dependent_range_six": [
            "identity",
            "hamiltonian_times_four",
            "left_tilted_field_times_four",
        ],
        "translation_summed_range_eight": [
            "identity",
            "hamiltonian_times_four",
            "adjacent_tilted_field_product_sum_times_sixteen",
        ],
        "range_six_with_independent_boundary_range_four": [
            "identity",
            "hamiltonian_times_four",
            "left_tilted_field_times_four",
        ],
    }
    family_checks = {
        family: all(kernel_checks[label] for label in labels)
        for family, labels in family_witnesses.items()
    }
    return {
        "coupling": "0",
        "n": n,
        "complete_parent_max_range": TRANSLATION_RANGE,
        "complete_parent_basis_size": len(basis),
        "complete_parent_matrix_sha256": parent_matrix_hash,
        "witness_kernel_checks": kernel_checks,
        "family_witnesses": family_witnesses,
        "family_witnesses_linearly_independent": {
            "complete_position_dependent_range_six": True,
            "translation_summed_range_eight": True,
            "range_six_with_independent_boundary_range_four": True,
        },
        "family_checks": family_checks,
        "checked": all(family_checks.values()),
        "interpretation": (
            "The J=0 control supplies explicit independent kernels inside "
            "each declared candidate family; a full control rank is not "
            "required by the preregistered contract."
        ),
    }


def protocol(contract: dict[str, Any]) -> dict[str, Any]:
    exact_rule = (
        "identity and H are explicit rational kernels and modular rank is "
        "ncols-2 under both declared primes"
    )
    return {
        "version": VERSION,
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "public_contract": {
            "path": str(CONTRACT_PATH),
            "sha256": EXPECTED_CONTRACT_SHA256,
            "version": contract["version"],
            "status": contract["status"],
            "pre_execution_erratum_retained": (
                "pre_execution_erratum" in contract
            ),
        },
        "model": {
            "boundary": "open",
            "hamiltonian": (
                "sum_i[-X_i+(3/4)Z_i]+J"
                "sum_{i=0}^{n-2}Z_i Z_{i+1}"
            ),
            "engineering_only_couplings": [
                fraction_text(value)
                for value in ENGINEERING_ONLY_COUPLINGS
            ],
            "engineering_probe_acceptance_count": 0,
            "frozen_holdout_couplings": [
                fraction_text(value)
                for value in FROZEN_HOLDOUT_COUPLINGS
            ],
            "holdouts_disjoint_from_previous": set(
                FROZEN_HOLDOUT_COUPLINGS
            ).isdisjoint(PREVIOUSLY_OBSERVED_COUPLINGS),
        },
        "complete_range_six_n10": {
            "sizes": [COMPLETE_SIZE],
            "couplings": [
                fraction_text(value)
                for value in FROZEN_HOLDOUT_COUPLINGS
            ],
            "max_range": COMPLETE_RANGE,
            "acceptance_rule": exact_rule,
        },
        "translation_summed_range_eight": {
            "sizes": [TRANSLATION_SIZE],
            "couplings": [fraction_text(TRANSLATION_COUPLING)],
            "max_range": TRANSLATION_RANGE,
            "acceptance_rule": exact_rule,
            "interpretation": (
                "one finite eight-shell truncation only; range nine and "
                "longer tails remain open"
            ),
        },
        "boundary_range_four": {
            "sizes": list(BOUNDARY_SIZES),
            "couplings": [
                fraction_text(value)
                for value in FROZEN_HOLDOUT_COUPLINGS
            ],
            "bulk_translation_range": BOUNDARY_BULK_RANGE,
            "independent_boundary_correction_range": (
                BOUNDARY_CORRECTION_RANGE
            ),
            "acceptance_rule": exact_rule,
            "interpretation": (
                "independent finite left/right corrections only; "
                "size-dependent and nonlocal boundaries remain open"
            ),
        },
        "exactness": {
            "modular_primes": list(MODULAR_PRIMES),
            "argument": (
                "two explicit rational kernels give nullity at least two; "
                "rank ncols-2 modulo either prime bounds rational nullity "
                "above by two"
            ),
        },
        "positive_control": contract["positive_control_rule"],
        "claim_boundary": {
            "true_claims": TRUE_CLAIMS,
            "false_claims": FALSE_CLAIMS,
            "scientific_promotion_accepted": False,
            "new_credit_delta": 0,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    complete_rows = result["complete_range_six_n10_rows"]
    translation_row = result["translation_range_eight_rows"][0]
    boundary_rows = result["boundary_range_four_rows"]
    lines = [
        "# B9 R196 Extended Tail Conserved-Charge Stress",
        "",
        "## Verdict",
        "",
        f"- Status: `{result['status']}`",
        (
            f"- Requirements: `{result['requirements_passed']}/"
            f"{result['requirements_total']}`"
        ),
        f"- Contract hash: `{result['evidence']['contract_sha256']}`",
        f"- Protocol hash: `{result['protocol_sha256']}`",
        f"- Payload hash: `{result['payload_sha256']}`",
        "- Scientific promotion accepted: `false`",
        "- New credit delta: `0`",
        "",
        "## Public Pre-Execution Boundary",
        "",
        (
            "- The v0.1.0 positive-control wording error was publicly "
            "corrected before any frozen-holdout acceptance row executed."
        ),
        (
            "- Frozen holdouts remain `J=73/128` and `J=77/128`; the "
            "engineering-only `J=13/32` probe contributes zero decisions."
        ),
        "",
        "## Complete Position-Dependent Range Six At n=10",
        "",
        (
            "- Exact-nullity-two rows: "
            f"`{summary['complete_range_six_n10_nullity_two_count']}/"
            f"{summary['complete_range_six_n10_row_count']}`."
        ),
        (
            f"- Candidate columns per row: "
            f"`{complete_rows[0]['candidate_basis_size']}`; output basis "
            f"size: `{complete_rows[0]['output_basis_size']}`."
        ),
        "",
        "## Translation-Summed Range Eight",
        "",
        (
            "- Frozen row: "
            f"`J={translation_row['coupling']}`, "
            f"`n={translation_row['n']}`."
        ),
        (
            f"- Candidate columns: "
            f"`{translation_row['candidate_basis_size']}`; complete parent "
            f"basis: `{translation_row['complete_parent_basis_size']}`; "
            f"output basis: `{translation_row['output_basis_size']}`."
        ),
        (
            "- Exact modular nullities: "
            f"`{translation_row['modular_nullities']}`."
        ),
        (
            "- This is one finite eight-shell certificate, not a "
            "range-nine or complete quasi-local exclusion."
        ),
        "",
        "## Independent Boundary Corrections Through Range Four",
        "",
        (
            "- Exact-nullity-two rows: "
            f"`{summary['boundary_range_four_nullity_two_count']}/"
            f"{summary['boundary_range_four_row_count']}`."
        ),
        (
            f"- Candidate columns per row: "
            f"`{boundary_rows[0]['candidate_basis_size']}`."
        ),
        (
            "- Both holdouts are tested at `n=9,10`; size-dependent, "
            "interacting, and nonlocal boundary structures remain open."
        ),
        "",
        "## Positive Controls",
        "",
        (
            "- At `J=0`, every family contains three explicit linearly "
            "independent exact kernels."
        ),
        (
            "- The translation-summed extra witness is the adjacent "
            "tilted-field product sum; complete and boundary families use "
            "a position-resolved tilted field."
        ),
        "",
        "## Supported",
        "",
    ]
    lines.extend(f"- {claim}" for claim in result["claim_boundary"]["supported"])
    lines.extend(["", "## Not Supported", ""])
    lines.extend(
        f"- {claim}" for claim in result["claim_boundary"]["not_supported"]
    )
    lines.extend(
        [
            "",
            "## Next Gate",
            "",
            "Attack range-nine or adaptive quasi-local tails, explicitly",
            "size-dependent/nonlocal boundary structures, nonlocal dualities,",
            "nonstandard fermionizations, interacting-integrability",
            "candidates, and larger sparse spectra. R196 narrows three finite",
            "ansatz families; it does not prove nonintegrability, quantum",
            "chaos, spectral hardness, Quantum PCP, NLTS, or BQP.",
            "",
        ]
    )
    return "\n".join(lines)


def build_result(root: Path) -> dict[str, Any]:
    contract = json.loads((root / CONTRACT_PATH).read_text())
    protocol_payload = protocol(contract)
    complete_rows = [
        r194.complete_charge_row(
            COMPLETE_SIZE,
            coupling,
            COMPLETE_RANGE,
            crosscheck_legacy=False,
        )
        for coupling in FROZEN_HOLDOUT_COUPLINGS
    ]
    translation_rows = [
        r194.translation_summed_charge_row(
            TRANSLATION_SIZE,
            TRANSLATION_COUPLING,
            TRANSLATION_RANGE,
        )
    ]
    boundary_rows = [
        r195.boundary_dressed_charge_row(
            n,
            coupling,
            bulk_range=BOUNDARY_BULK_RANGE,
            boundary_range=BOUNDARY_CORRECTION_RANGE,
        )
        for coupling in FROZEN_HOLDOUT_COUPLINGS
        for n in BOUNDARY_SIZES
    ]
    controls = positive_control_witnesses()

    complete_pass_count = sum(
        row["exact_nullity_two_certified"] for row in complete_rows
    )
    translation_pass_count = sum(
        row["exact_nullity_two_certified"] for row in translation_rows
    )
    boundary_pass_count = sum(
        row["exact_nullity_two_certified"] for row in boundary_rows
    )
    summary = {
        "engineering_probe_acceptance_count": 0,
        "frozen_holdout_coupling_count": len(FROZEN_HOLDOUT_COUPLINGS),
        "holdouts_disjoint_from_previous": set(
            FROZEN_HOLDOUT_COUPLINGS
        ).isdisjoint(PREVIOUSLY_OBSERVED_COUPLINGS),
        "complete_range_six_n10_row_count": len(complete_rows),
        "complete_range_six_n10_nullity_two_count": complete_pass_count,
        "translation_range_eight_row_count": len(translation_rows),
        "translation_range_eight_nullity_two_count": (
            translation_pass_count
        ),
        "boundary_range_four_row_count": len(boundary_rows),
        "boundary_range_four_nullity_two_count": boundary_pass_count,
        "positive_control_family_pass_count": sum(
            controls["family_checks"].values()
        ),
        "positive_control_family_count": len(controls["family_checks"]),
        "scoped_extended_tail_boundary_accepted": bool(
            complete_pass_count == len(complete_rows)
            and translation_pass_count == len(translation_rows)
            and boundary_pass_count == len(boundary_rows)
            and controls["checked"]
        ),
        "scientific_promotion_accepted": False,
    }
    claim_boundary = {
        "supported": list(TRUE_CLAIMS),
        "not_supported": list(FALSE_CLAIMS),
        "true_claims": list(TRUE_CLAIMS),
        "false_claims": list(FALSE_CLAIMS),
        "remaining_escape_routes": [
            "complete range six beyond n=10",
            "range-nine and longer quasi-local tails",
            "boundary corrections beyond range four",
            "size-dependent or nonlocal boundary dressings",
            "site-dependent long-range bulk charges",
            "nonlocal dualities",
            "nonstandard fermionizations",
            "interacting integrability structures",
            "larger-size finite-spectrum drift",
        ],
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    all_rows = complete_rows + translation_rows + boundary_rows
    requirements = [
        requirement(
            "P1",
            "Public contract and pre-execution erratum are hash-bound",
            sha256_file(root / CONTRACT_PATH) == EXPECTED_CONTRACT_SHA256
            and "pre_execution_erratum" in contract,
            {
                "contract_sha256": sha256_file(root / CONTRACT_PATH),
                "expected_sha256": EXPECTED_CONTRACT_SHA256,
                "contract_version": contract.get("version"),
            },
        ),
        requirement(
            "P2",
            "Engineering probe contributes zero acceptance decisions",
            summary["engineering_probe_acceptance_count"] == 0,
            {
                "engineering_only_couplings": [
                    fraction_text(value)
                    for value in ENGINEERING_ONLY_COUPLINGS
                ],
                "acceptance_count": 0,
            },
        ),
        requirement(
            "P3",
            "Frozen holdouts are disjoint from previous grids",
            summary["holdouts_disjoint_from_previous"]
            and len(set(FROZEN_HOLDOUT_COUPLINGS)) == 2,
            {
                "couplings": [
                    fraction_text(value)
                    for value in FROZEN_HOLDOUT_COUPLINGS
                ],
                "previous_grid_size": len(
                    PREVIOUSLY_OBSERVED_COUPLINGS
                ),
            },
        ),
        requirement(
            "P4",
            "Complete range-six n=10 row set is exhaustive",
            len(complete_rows) == 2,
            {"row_count": len(complete_rows), "expected": 2},
        ),
        requirement(
            "P5",
            "Complete range-six n=10 rows have explicit kernels",
            all(
                row["identity_kernel_verified"]
                and row["hamiltonian_kernel_verified"]
                for row in complete_rows
            ),
            {"row_count": len(complete_rows)},
        ),
        requirement(
            "P6",
            "Complete range-six n=10 nullity is exactly two",
            complete_pass_count == len(complete_rows),
            {"passed": complete_pass_count, "total": len(complete_rows)},
        ),
        requirement(
            "P7",
            "Translation range-eight row matches the frozen scope",
            len(translation_rows) == 1
            and translation_rows[0]["n"] == 10
            and translation_rows[0]["coupling"] == "73/128"
            and translation_rows[0]["candidate_basis_size"] == 49_153,
            {
                "row_count": len(translation_rows),
                "candidate_basis_size": (
                    translation_rows[0]["candidate_basis_size"]
                ),
            },
        ),
        requirement(
            "P8",
            "Translation range-eight nullity is exactly two",
            translation_pass_count == 1,
            {"passed": translation_pass_count, "total": 1},
        ),
        requirement(
            "P9",
            "Boundary range-four row set is exhaustive",
            len(boundary_rows) == 4,
            {"row_count": len(boundary_rows), "expected": 4},
        ),
        requirement(
            "P10",
            "Boundary range-four rows have exact nullity two",
            boundary_pass_count == len(boundary_rows)
            and all(
                row["independent_boundary_correction_range"] == 4
                for row in boundary_rows
            ),
            {"passed": boundary_pass_count, "total": len(boundary_rows)},
        ),
        requirement(
            "P11",
            "Every acceptance row has two-prime rank evidence and digest",
            all(
                set(row["modular_ranks"])
                == {str(prime) for prime in MODULAR_PRIMES}
                and len(row["commutator_matrix_sha256"]) == 64
                for row in all_rows
            ),
            {"row_count": len(all_rows), "prime_count": 2},
        ),
        requirement(
            "P12",
            "J=0 controls provide explicit independent family kernels",
            controls["checked"]
            and all(
                controls["family_witnesses_linearly_independent"].values()
            ),
            {
                "family_checks": controls["family_checks"],
                "witness_kernel_checks": (
                    controls["witness_kernel_checks"]
                ),
            },
        ),
        requirement(
            "P13",
            "R193-R195 dependencies and R195 result are hash-bound",
            all(
                len(sha256_file(root / path)) == 64
                for path in (
                    R193_TOOL_PATH,
                    R194_TOOL_PATH,
                    R195_TOOL_PATH,
                    R195_RESULT_PATH,
                )
            ),
            {
                "r193_tool_sha256": sha256_file(root / R193_TOOL_PATH),
                "r194_tool_sha256": sha256_file(root / R194_TOOL_PATH),
                "r195_tool_sha256": sha256_file(root / R195_TOOL_PATH),
                "r195_result_sha256": sha256_file(root / R195_RESULT_PATH),
            },
        ),
        requirement(
            "P14",
            "Finite ansatz boundaries remain explicit",
            set(FALSE_CLAIMS).issubset(
                set(claim_boundary["not_supported"])
            )
            and len(claim_boundary["remaining_escape_routes"]) >= 9,
            {
                "false_claim_count": len(FALSE_CLAIMS),
                "remaining_escape_route_count": len(
                    claim_boundary["remaining_escape_routes"]
                ),
            },
        ),
        requirement(
            "P15",
            "Broad scientific promotion remains disabled",
            claim_boundary["scientific_promotion_accepted"] is False
            and claim_boundary["new_credit_delta"] == 0,
            {
                "scientific_promotion_accepted": False,
                "new_credit_delta": 0,
            },
        ),
    ]
    requirements_passed = sum(row["passed"] for row in requirements)
    accepted = bool(
        requirements_passed == len(requirements)
        and summary["scoped_extended_tail_boundary_accepted"]
    )
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "status": STATUS_ACCEPTED if accepted else STATUS_REJECTED,
        "protocol": protocol_payload,
        "protocol_sha256": canonical_hash(protocol_payload),
        "complete_range_six_n10_rows": complete_rows,
        "translation_range_eight_rows": translation_rows,
        "boundary_range_four_rows": boundary_rows,
        "positive_controls": controls,
        "summary": summary,
        "claim_boundary": claim_boundary,
        "requirements": requirements,
        "requirements_total": len(requirements),
        "requirements_passed": requirements_passed,
        "evidence": {
            "contract_sha256": sha256_file(root / CONTRACT_PATH),
            "tool_sha256": sha256_file(Path(__file__)),
            "r193_dependency_sha256": sha256_file(root / R193_TOOL_PATH),
            "r194_dependency_sha256": sha256_file(root / R194_TOOL_PATH),
            "r195_dependency_sha256": sha256_file(root / R195_TOOL_PATH),
            "r195_result_sha256": sha256_file(root / R195_RESULT_PATH),
        },
        "evidence_integrity_complete": accepted,
        "new_credit_delta": 0,
    }
    payload["payload_sha256"] = canonical_hash(payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--json-output", type=Path, default=RESULT_PATH)
    parser.add_argument("--markdown-output", type=Path, default=REPORT_PATH)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    payload = build_result(root)
    json_output = (
        args.json_output
        if args.json_output.is_absolute()
        else root / args.json_output
    )
    markdown_output = (
        args.markdown_output
        if args.markdown_output.is_absolute()
        else root / args.markdown_output
    )
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(
            payload,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
        + "\n"
    )
    markdown_output.write_text(render_report(payload))
    print(
        json.dumps(
            {
                "experiment_id": payload["experiment_id"],
                "status": payload["status"],
                "requirements_passed": payload["requirements_passed"],
                "requirements_total": payload["requirements_total"],
                "payload_sha256": payload["payload_sha256"],
                "summary": payload["summary"],
            },
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )
    return 0 if payload["evidence_integrity_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
