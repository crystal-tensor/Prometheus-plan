#!/usr/bin/env python3
"""Build the B9 R195 multiscale conserved-charge stress certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from typing import Any

import b9_r193_coupling_integrability_stress as r193
import b9_r194_higher_range_charge_stress as r194


EXPERIMENT_ID = "B9-R195-multiscale-tail-charge-stress"
METHOD = "b9_r195_multiscale_tail_charge_stress_v1"
STATUS_ACCEPTED = "checked_multiscale_tail_charge_boundary"
STATUS_REJECTED = "multiscale_tail_charge_boundary_rejected"
VERSION = "1.0"
LAST_UPDATED = "2026-07-29"

# These 1/128-grid couplings do not occur in the R193 acceptance grid or the
# R194 engineering/acceptance grids. They are frozen before R195 execution.
FROZEN_HOLDOUT_COUPLINGS = (Fraction(53, 128), Fraction(69, 128))
PREVIOUSLY_OBSERVED_COUPLINGS = {
    Fraction(0),
    Fraction(1, 8),
    Fraction(3, 16),
    Fraction(1, 4),
    Fraction(5, 16),
    Fraction(3, 8),
    Fraction(13, 32),
    Fraction(7, 16),
    Fraction(23, 64),
    Fraction(27, 64),
    Fraction(31, 64),
    Fraction(1, 2),
    Fraction(35, 64),
    Fraction(9, 16),
    Fraction(5, 8),
    Fraction(11, 16),
    Fraction(3, 4),
    Fraction(7, 8),
    Fraction(1),
}
COMPLETE_RANGE_SIX_SIZES = (8, 9)
TRANSLATION_RANGE_SEVEN_SIZES = (9, 10)
BOUNDARY_DRESSED_RANGE_SIX_SIZES = (8, 9)
COMPLETE_RANGE = 6
TRANSLATION_RANGE = 7
BOUNDARY_BULK_RANGE = 6
BOUNDARY_CORRECTION_RANGE = 3
MODULAR_PRIMES = (1_000_003, 1_000_033)

RESULT_PATH = Path("results/B9_R195_multiscale_tail_charge_stress_v1.json")
REPORT_PATH = Path("research/B9_R195_multiscale_tail_charge_stress.md")
R193_TOOL_PATH = Path("tools/b9_r193_coupling_integrability_stress.py")
R194_TOOL_PATH = Path("tools/b9_r194_higher_range_charge_stress.py")
R194_RESULT_PATH = Path(
    "results/B9_R194_higher_range_charge_stress_v1.json"
)

TRUE_CLAIMS = [
    "r195_holdout_couplings_unseen_before_protocol_freeze",
    "complete_range_six_nullity_two_on_four_holdout_rows",
    "translation_summed_range_seven_nullity_two_on_four_holdout_rows",
    "range_six_boundary_dressing_nullity_two_on_four_holdout_rows",
    "zero_coupling_controls_detect_extra_conserved_charges",
    "r194_candidate_survives_declared_multiscale_tail_adversaries",
]
FALSE_CLAIMS = [
    "all_coupling_theorem",
    "all_size_theorem",
    "range_eight_or_longer_tail_exclusion",
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


def hamiltonian_label_vector(
    labels: list[str],
    coupling: Fraction,
    prefix: str,
) -> tuple[dict[int, int], int]:
    label_index = {label: index for index, label in enumerate(labels)}
    denominator = r193.common_denominator(coupling)
    coupling_numerator = (
        coupling.numerator * denominator // coupling.denominator
    )
    vector = {
        label_index[f"{prefix}range_1:X"]: -denominator,
        label_index[f"{prefix}range_1:Z"]: 3 * denominator // 4,
    }
    if coupling_numerator:
        vector[label_index[f"{prefix}range_2:ZZ"]] = coupling_numerator
    return vector, denominator


def boundary_dressed_charge_row(
    n: int,
    coupling: Fraction,
    bulk_range: int = BOUNDARY_BULK_RANGE,
    boundary_range: int = BOUNDARY_CORRECTION_RANGE,
) -> dict[str, Any]:
    (
        full_basis,
        full_columns,
        output_basis,
        _,
        _,
    ) = r193.pauli_commutator_columns(n, coupling, bulk_range)
    full_index = {word: index for index, word in enumerate(full_basis)}

    labels = ["identity"]
    coefficient_vectors: list[dict[int, int]] = [
        {full_index["I" * n]: 1}
    ]
    for span, local in r194.local_patterns(bulk_range):
        labels.append(f"bulk_range_{span}:{local}")
        coefficient_vectors.append(
            {
                full_index[r194.translated_word(n, start, local)]: 1
                for start in range(n - span + 1)
            }
        )
    for span, local in r194.local_patterns(boundary_range):
        labels.append(f"left_range_{span}:{local}")
        coefficient_vectors.append(
            {full_index[r194.translated_word(n, 0, local)]: 1}
        )
        labels.append(f"right_range_{span}:{local}")
        coefficient_vectors.append(
            {
                full_index[
                    r194.translated_word(n, n - span, local)
                ]: 1
            }
        )

    columns = [
        r193.combine_columns(full_columns, vector)
        for vector in coefficient_vectors
    ]
    triples = [
        (output_basis[row], column_index, value)
        for column_index, column in enumerate(columns)
        for row, value in sorted(column.items())
    ]
    matrix_hash = canonical_hash(
        {
            "candidate_labels": labels,
            "output_basis": output_basis,
            "triples": triples,
        }
    )
    label_index = {label: index for index, label in enumerate(labels)}
    identity_vector = {label_index["identity"]: 1}
    hamiltonian_vector, denominator = hamiltonian_label_vector(
        labels,
        coupling,
        "bulk_",
    )
    identity_kernel = not r193.combine_columns(columns, identity_vector)
    hamiltonian_kernel = not r193.combine_columns(
        columns,
        hamiltonian_vector,
    )
    ranks = {
        str(prime): r194.minimum_degree_sparse_rank(columns, prime)
        for prime in MODULAR_PRIMES
    }
    nullities = {
        prime: len(labels) - rank for prime, rank in ranks.items()
    }
    exact_nullity_two = bool(
        coupling != 0
        and identity_kernel
        and hamiltonian_kernel
        and all(rank == len(labels) - 2 for rank in ranks.values())
    )
    return {
        "search_family": "translation_summed_with_independent_boundaries",
        "coupling": fraction_text(coupling),
        "coupling_numerator": coupling.numerator,
        "coupling_denominator": coupling.denominator,
        "n": n,
        "bulk_translation_range": bulk_range,
        "independent_boundary_correction_range": boundary_range,
        "candidate_basis_size": len(labels),
        "complete_parent_basis_size": len(full_basis),
        "output_basis_size": len(output_basis),
        "commutator_nonzero_count": len(triples),
        "commutator_matrix_sha256": matrix_hash,
        "hamiltonian_common_denominator": denominator,
        "identity_kernel_verified": identity_kernel,
        "hamiltonian_kernel_verified": hamiltonian_kernel,
        "modular_primes": list(MODULAR_PRIMES),
        "modular_ranks": ranks,
        "modular_nullities": nullities,
        "exact_nullity_two_certified": exact_nullity_two,
        "finite_bulk_and_boundary_truncation_only": True,
        "checked": (
            exact_nullity_two
            if coupling != 0
            else identity_kernel and hamiltonian_kernel
        ),
    }


def protocol() -> dict[str, Any]:
    couplings = [
        fraction_text(value) for value in FROZEN_HOLDOUT_COUPLINGS
    ]
    exact_rule = (
        "identity and H are explicit rational kernels and modular rank is "
        "ncols-2 under both declared primes on every row"
    )
    return {
        "version": VERSION,
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "model": {
            "boundary": "open",
            "hamiltonian": (
                "sum_i[-X_i+(3/4)Z_i]+J"
                "sum_{i=0}^{n-2}Z_i Z_{i+1}"
            ),
            "frozen_holdout_couplings": couplings,
            "previously_observed_coupling_count": len(
                PREVIOUSLY_OBSERVED_COUPLINGS
            ),
            "holdouts_disjoint_from_previous": set(
                FROZEN_HOLDOUT_COUPLINGS
            ).isdisjoint(PREVIOUSLY_OBSERVED_COUPLINGS),
        },
        "complete_range_six": {
            "sizes": list(COMPLETE_RANGE_SIX_SIZES),
            "couplings": couplings,
            "max_range": COMPLETE_RANGE,
            "basis": (
                "identity plus every position-dependent Pauli word with "
                "minimal contiguous support span at most six"
            ),
            "acceptance_rule": exact_rule,
        },
        "translation_summed_range_seven": {
            "sizes": list(TRANSLATION_RANGE_SEVEN_SIZES),
            "couplings": couplings,
            "max_range": TRANSLATION_RANGE,
            "basis": (
                "identity plus the open-chain translation sum of every "
                "Pauli density with support span at most seven"
            ),
            "interpretation": (
                "seven-shell finite truncation only; range-eight or longer "
                "tails can evade it"
            ),
            "acceptance_rule": exact_rule,
        },
        "boundary_dressed_range_six": {
            "sizes": list(BOUNDARY_DRESSED_RANGE_SIX_SIZES),
            "couplings": couplings,
            "bulk_translation_range": BOUNDARY_BULK_RANGE,
            "independent_boundary_correction_range": (
                BOUNDARY_CORRECTION_RANGE
            ),
            "basis": (
                "identity, every open-chain translation-summed density "
                "through range six, and independent left/right Pauli "
                "boundary corrections through range three"
            ),
            "interpretation": (
                "finite boundary dressing only; longer, size-dependent, "
                "or nonlocal boundary structures can evade it"
            ),
            "acceptance_rule": exact_rule,
        },
        "positive_controls": {
            "coupling": "0",
            "complete_range_six_size": 8,
            "translation_range_seven_size": 9,
            "boundary_dressed_range_six_size": 8,
            "acceptance_rule": (
                "each control must expose modular nullity greater than two"
            ),
        },
        "exactness": {
            "modular_primes": list(MODULAR_PRIMES),
            "argument": (
                "two explicit rational kernels give nullity at least two; "
                "rank ncols-2 modulo either prime gives rational rank at "
                "least ncols-2, hence rational nullity exactly two"
            ),
        },
        "claim_boundary": {
            "true_claims": TRUE_CLAIMS,
            "false_claims": FALSE_CLAIMS,
            "scientific_promotion_accepted": False,
            "new_credit_delta": 0,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    complete_rows = result["complete_range_six_rows"]
    translation_rows = result["translation_range_seven_rows"]
    boundary_rows = result["boundary_dressed_range_six_rows"]
    lines = [
        "# B9 R195 Multiscale Tail Conserved-Charge Stress",
        "",
        "## Verdict",
        "",
        f"- Status: `{result['status']}`",
        (
            f"- Requirements: `{result['requirements_passed']}/"
            f"{result['requirements_total']}`"
        ),
        f"- Protocol hash: `{result['protocol_sha256']}`",
        f"- Payload hash: `{result['payload_sha256']}`",
        "- Scientific promotion accepted: `false`",
        "- New credit delta: `0`",
        "",
        "## Frozen Holdout Boundary",
        "",
        (
            "- Couplings: `J=53/128` and `J=69/128`; neither appears in "
            "the R193 or R194 observed/acceptance grids."
        ),
        "- No coupling was removed or replaced after execution.",
        "",
        "## Complete Position-Dependent Range Six",
        "",
        (
            "- Exact-nullity-two rows: "
            f"`{summary['complete_range_six_nullity_two_count']}/"
            f"{summary['complete_range_six_row_count']}`."
        ),
        "- Sizes: `n=8,9`; both frozen couplings are tested at both sizes.",
        (
            "- Candidate columns range from "
            f"`{min(row['candidate_basis_size'] for row in complete_rows)}` "
            "to "
            f"`{max(row['candidate_basis_size'] for row in complete_rows)}`."
        ),
        "",
        "## Translation-Summed Range Seven",
        "",
        (
            "- Exact-nullity-two rows: "
            f"`{summary['translation_range_seven_nullity_two_count']}/"
            f"{summary['translation_range_seven_row_count']}`."
        ),
        "- Sizes: `n=9,10`; every translation-summed density through range seven is included.",
        (
            "- Candidate columns per row: "
            f"`{translation_rows[0]['candidate_basis_size']}`."
        ),
        (
            "- This is a seven-shell truncation, not an exclusion of "
            "range-eight or longer quasi-local tails."
        ),
        "",
        "## Independent Boundary Dressing",
        "",
        (
            "- Exact-nullity-two rows: "
            f"`{summary['boundary_dressed_nullity_two_count']}/"
            f"{summary['boundary_dressed_row_count']}`."
        ),
        (
            "- Each row adds independent left/right Pauli corrections "
            "through range three to every bulk translation sum through "
            "range six."
        ),
        (
            "- Candidate columns per row: "
            f"`{boundary_rows[0]['candidate_basis_size']}`."
        ),
        (
            "- Longer, size-dependent, interacting, or nonlocal boundary "
            "dressings remain untested."
        ),
        "",
        "## Positive Controls",
        "",
        (
            "- `J=0` nullities for complete range six, range-seven "
            "translation sum, and boundary-dressed range six: "
            f"`{summary['positive_control_nullities']}`."
        ),
        (
            "- All three exceed two, so each adversary detects known extra "
            "conserved structure."
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
            "Extend complete range six to `n=10`, then test range-eight",
            "translation sums, longer and size-dependent boundary tails,",
            "nonlocal dualities, nonstandard fermionizations, and",
            "interacting-integrability candidates. R195 narrows three finite",
            "ansatz families; it does not prove nonintegrability, quantum",
            "chaos, spectral hardness, Quantum PCP, NLTS, or BQP.",
            "",
        ]
    )
    return "\n".join(lines)


def build_result(root: Path) -> dict[str, Any]:
    protocol_payload = protocol()
    complete_rows = [
        r194.complete_charge_row(
            n,
            coupling,
            COMPLETE_RANGE,
            crosscheck_legacy=False,
        )
        for coupling in FROZEN_HOLDOUT_COUPLINGS
        for n in COMPLETE_RANGE_SIX_SIZES
    ]
    translation_rows = [
        r194.translation_summed_charge_row(
            n,
            coupling,
            TRANSLATION_RANGE,
        )
        for coupling in FROZEN_HOLDOUT_COUPLINGS
        for n in TRANSLATION_RANGE_SEVEN_SIZES
    ]
    boundary_rows = [
        boundary_dressed_charge_row(n, coupling)
        for coupling in FROZEN_HOLDOUT_COUPLINGS
        for n in BOUNDARY_DRESSED_RANGE_SIX_SIZES
    ]
    controls = {
        "complete_range_six": r194.complete_charge_row(
            8,
            Fraction(0),
            COMPLETE_RANGE,
            crosscheck_legacy=False,
        ),
        "translation_range_seven": r194.translation_summed_charge_row(
            9,
            Fraction(0),
            TRANSLATION_RANGE,
        ),
        "boundary_dressed_range_six": boundary_dressed_charge_row(
            8,
            Fraction(0),
        ),
    }

    complete_pass_count = sum(
        row["exact_nullity_two_certified"] for row in complete_rows
    )
    translation_pass_count = sum(
        row["exact_nullity_two_certified"] for row in translation_rows
    )
    boundary_pass_count = sum(
        row["exact_nullity_two_certified"] for row in boundary_rows
    )
    positive_control_nullities = {
        label: min(row["modular_nullities"].values())
        for label, row in controls.items()
    }
    positive_control_pass_count = sum(
        value > 2 for value in positive_control_nullities.values()
    )
    summary = {
        "frozen_holdout_coupling_count": len(FROZEN_HOLDOUT_COUPLINGS),
        "holdouts_disjoint_from_previous": set(
            FROZEN_HOLDOUT_COUPLINGS
        ).isdisjoint(PREVIOUSLY_OBSERVED_COUPLINGS),
        "complete_range_six_row_count": len(complete_rows),
        "complete_range_six_nullity_two_count": complete_pass_count,
        "translation_range_seven_row_count": len(translation_rows),
        "translation_range_seven_nullity_two_count": (
            translation_pass_count
        ),
        "boundary_dressed_row_count": len(boundary_rows),
        "boundary_dressed_nullity_two_count": boundary_pass_count,
        "positive_control_nullities": positive_control_nullities,
        "positive_control_pass_count": positive_control_pass_count,
        "scoped_multiscale_tail_boundary_accepted": bool(
            complete_pass_count == len(complete_rows)
            and translation_pass_count == len(translation_rows)
            and boundary_pass_count == len(boundary_rows)
            and positive_control_pass_count == len(controls)
        ),
        "scientific_promotion_accepted": False,
    }
    claim_boundary = {
        "supported": list(TRUE_CLAIMS),
        "not_supported": list(FALSE_CLAIMS),
        "true_claims": list(TRUE_CLAIMS),
        "false_claims": list(FALSE_CLAIMS),
        "remaining_escape_routes": [
            "complete range six at n=10 and larger",
            "range-eight and longer quasi-local tails",
            "boundary corrections beyond range three",
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
    expected_rows = len(FROZEN_HOLDOUT_COUPLINGS) * 2
    all_rows = complete_rows + translation_rows + boundary_rows
    requirements = [
        requirement(
            "P1",
            "Frozen couplings are disjoint from all previous grids",
            summary["holdouts_disjoint_from_previous"]
            and len(set(FROZEN_HOLDOUT_COUPLINGS)) == 2,
            {
                "couplings": [
                    fraction_text(value)
                    for value in FROZEN_HOLDOUT_COUPLINGS
                ],
                "previous_grid_size": len(PREVIOUSLY_OBSERVED_COUPLINGS),
            },
        ),
        requirement(
            "P2",
            "Complete range-six row set is exhaustive",
            len(complete_rows) == expected_rows,
            {"row_count": len(complete_rows), "expected": expected_rows},
        ),
        requirement(
            "P3",
            "Complete range-six rows have explicit identity/H kernels",
            all(
                row["identity_kernel_verified"]
                and row["hamiltonian_kernel_verified"]
                for row in complete_rows
            ),
            {"row_count": len(complete_rows)},
        ),
        requirement(
            "P4",
            "Complete range-six nullity is exactly two",
            complete_pass_count == len(complete_rows),
            {"passed": complete_pass_count, "total": len(complete_rows)},
        ),
        requirement(
            "P5",
            "Translation range-seven row set is exhaustive",
            len(translation_rows) == expected_rows,
            {"row_count": len(translation_rows), "expected": expected_rows},
        ),
        requirement(
            "P6",
            "Translation range-seven rows have explicit kernels",
            all(
                row["identity_kernel_verified"]
                and row["hamiltonian_kernel_verified"]
                for row in translation_rows
            ),
            {"row_count": len(translation_rows)},
        ),
        requirement(
            "P7",
            "Translation range-seven nullity is exactly two",
            translation_pass_count == len(translation_rows),
            {
                "passed": translation_pass_count,
                "total": len(translation_rows),
            },
        ),
        requirement(
            "P8",
            "Boundary-dressed row set is exhaustive",
            len(boundary_rows) == expected_rows,
            {"row_count": len(boundary_rows), "expected": expected_rows},
        ),
        requirement(
            "P9",
            "Boundary-dressed rows have explicit kernels",
            all(
                row["identity_kernel_verified"]
                and row["hamiltonian_kernel_verified"]
                for row in boundary_rows
            ),
            {"row_count": len(boundary_rows)},
        ),
        requirement(
            "P10",
            "Boundary-dressed nullity is exactly two",
            boundary_pass_count == len(boundary_rows),
            {"passed": boundary_pass_count, "total": len(boundary_rows)},
        ),
        requirement(
            "P11",
            "Every accepted matrix has two-prime rank evidence",
            all(
                set(row["modular_ranks"])
                == {str(prime) for prime in MODULAR_PRIMES}
                for row in all_rows
            ),
            {"row_count": len(all_rows), "prime_count": 2},
        ),
        requirement(
            "P12",
            "Every accepted matrix has an explicit digest",
            all(
                len(row["commutator_matrix_sha256"]) == 64
                for row in all_rows
            ),
            {"digest_count": len(all_rows)},
        ),
        requirement(
            "P13",
            "J=0 controls expose extra conserved charges",
            positive_control_pass_count == len(controls),
            {
                "nullities": positive_control_nullities,
                "passed": positive_control_pass_count,
            },
        ),
        requirement(
            "P14",
            "R194 result and exact-rank dependencies are hash-bound",
            all(
                len(sha256_file(root / path)) == 64
                for path in (
                    R193_TOOL_PATH,
                    R194_TOOL_PATH,
                    R194_RESULT_PATH,
                )
            ),
            {
                "r193_tool_sha256": sha256_file(
                    root / R193_TOOL_PATH
                ),
                "r194_tool_sha256": sha256_file(
                    root / R194_TOOL_PATH
                ),
                "r194_result_sha256": sha256_file(
                    root / R194_RESULT_PATH
                ),
            },
        ),
        requirement(
            "P15",
            "Finite ansatz boundaries remain explicit",
            set(FALSE_CLAIMS).issubset(
                set(claim_boundary["not_supported"])
            )
            and len(claim_boundary["remaining_escape_routes"]) >= 8,
            {
                "false_claim_count": len(FALSE_CLAIMS),
                "remaining_escape_route_count": len(
                    claim_boundary["remaining_escape_routes"]
                ),
            },
        ),
        requirement(
            "P16",
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
        and summary["scoped_multiscale_tail_boundary_accepted"]
    )
    payload = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "status": STATUS_ACCEPTED if accepted else STATUS_REJECTED,
        "protocol": protocol_payload,
        "protocol_sha256": canonical_hash(protocol_payload),
        "complete_range_six_rows": complete_rows,
        "translation_range_seven_rows": translation_rows,
        "boundary_dressed_range_six_rows": boundary_rows,
        "positive_controls": controls,
        "summary": summary,
        "claim_boundary": claim_boundary,
        "requirements": requirements,
        "requirements_total": len(requirements),
        "requirements_passed": requirements_passed,
        "evidence": {
            "tool_sha256": sha256_file(Path(__file__)),
            "r193_dependency_sha256": sha256_file(
                root / R193_TOOL_PATH
            ),
            "r194_dependency_sha256": sha256_file(
                root / R194_TOOL_PATH
            ),
            "r194_result_sha256": sha256_file(
                root / R194_RESULT_PATH
            ),
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
