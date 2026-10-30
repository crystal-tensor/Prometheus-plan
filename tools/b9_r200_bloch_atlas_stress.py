#!/usr/bin/env python3
"""Preregister and execute the B9 R200 finite projective Bloch-atlas stress.

R200 replaces a one-parameter meridian with a finite exact set of rational
projective parity axes. Gauge-equivalent directed frames remain engineering
sentinels and are not double-counted as scientific acceptance rows. Frozen
holdouts remain inaccessible until a public commit hash-binds this tool and
its contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from collections import defaultdict
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any

import b9_r199_ay_meridian_stress as previous


EXPERIMENT_ID = "B9-R200-finite-projective-rational-bloch-atlas-stress"
METHOD = "b9_r200_bloch_atlas_stress_v1"
VERSION = "0.1.0"
LAST_UPDATED = "2026-10-31"
STATUS_ACCEPTED = "checked_finite_projective_rational_bloch_atlas_boundary"
STATUS_REJECTED = "finite_projective_rational_bloch_atlas_boundary_rejected"

CONTRACT_PATH = Path("benchmarks/B9_R200_bloch_atlas_contract_v0.json")
EXPECTED_CONTRACT_SHA256 = "a1208296eeaf56ed7bf51ed740b51931b7e1067cdb53d2e5e6e0d931aca356c0"
RESULT_PATH = Path("results/B9_R200_bloch_atlas_stress_v1.json")
REPORT_PATH = Path("research/B9_R200_bloch_atlas_stress.md")

ENGINEERING_COUPLING = Fraction(13, 32)
FROZEN_HOLDOUT_COUPLINGS = (Fraction(109, 128), Fraction(113, 128))
GRID_SIZES = (6, 8, 10)
ATLAS_BOUND = 2
ATLAS_EXPECTED_COUNT = 82
DIRECTED_AXIS_EXPECTED_COUNT = 62
PROJECTIVE_AXIS_EXPECTED_COUNT = 31
DIRECTED_OVERLAP_EXPECTED_COUNT = 20
ATLAS_EXPECTED_SHA256 = "b168b38442f85cd7a485e6e1ea2332fab1fa994e7c13956c405384e31f59cd47"
PROJECTIVE_CATALOG_EXPECTED_SHA256 = "f64e2e63f922d691bdeef5fdf58b2e90207afe3b775d55dafc713e19b7705a2f"
MODULAR_PRIMES = (1_000_003, 1_000_033)
BASIS_SELECTION_PRIME = MODULAR_PRIMES[0]
AUDIT_PRIMES = (1_000_037, 1_000_081)

base = previous.base
Axis = base.Axis
Operator = base.Operator

AXIS_A: Axis = {"X": Fraction(-4, 5), "Z": Fraction(3, 5)}

PREVIOUSLY_OBSERVED_COUPLINGS = (
    set(previous.PREVIOUSLY_OBSERVED_COUPLINGS)
    | set(previous.FROZEN_HOLDOUT_COUPLINGS)
)

TRUE_CLAIMS = [
    "r200_contract_publicly_frozen_before_acceptance_execution",
    "r200_holdout_couplings_unseen_before_protocol_freeze",
    "declared_finite_projective_rational_atlas_has_no_extra_quadratic_majorana_charge_at_n6_n8_n10",
    "atlas_overlap_and_projective_gauge_subspaces_match_at_n4",
    "zero_coupling_field_axis_control_recovers_extra_exact_charges",
    "r199_candidate_survives_declared_r200_finite_projective_grid_adversary",
]

FALSE_CLAIMS = [
    "continuous_two_dimensional_bloch_sphere_exclusion",
    "all_bloch_sphere_frame_exclusion",
    "irrational_axis_exclusion",
    "all_bloch_sphere_fermionization_exclusion",
    "nonlinear_frame_mixture_exclusion",
    "higher_order_majorana_charge_exclusion",
    "nonlocal_duality_exclusion",
    "interacting_integrability_exclusion",
    "complete_integrability_exclusion",
    "nonintegrability_theorem",
    "quantum_chaos_theorem",
    "spectral_hardness_theorem",
    "quantum_pcp_theorem",
    "nlts_theorem",
    "bqp_separation",
    "hardware_relevance",
    "solved_frontier",
]


def fraction_text(value: Fraction) -> str:
    return previous.fraction_text(value)


def canonical_hash(value: Any) -> str:
    return previous.canonical_hash(value)


def vector(axis: Axis) -> tuple[Fraction, Fraction, Fraction]:
    return tuple(axis.get(pauli, Fraction(0)) for pauli in "XYZ")  # type: ignore[return-value]


def dot(
    left: tuple[Fraction, Fraction, Fraction],
    right: tuple[Fraction, Fraction, Fraction],
) -> Fraction:
    return sum((a * b for a, b in zip(left, right)), Fraction(0))


def cross(
    left: tuple[Fraction, Fraction, Fraction],
    right: tuple[Fraction, Fraction, Fraction],
) -> tuple[Fraction, Fraction, Fraction]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def axis_from_vector(values: tuple[Fraction, Fraction, Fraction]) -> Axis:
    return {
        pauli: value for pauli, value in zip("XYZ", values) if value
    }


def negate(values: tuple[Fraction, Fraction, Fraction]) -> tuple[Fraction, Fraction, Fraction]:
    return tuple(-value for value in values)  # type: ignore[return-value]


def north_frame(a: int, b: int, c: int) -> dict[str, Axis]:
    denominator = a * a + b * b + c * c
    p = (
        Fraction(2 * a * c, denominator),
        Fraction(2 * b * c, denominator),
        Fraction(c * c - a * a - b * b, denominator),
    )
    q = (
        Fraction(c * c - a * a + b * b, denominator),
        Fraction(-2 * a * b, denominator),
        Fraction(-2 * a * c, denominator),
    )
    r = (
        Fraction(-2 * a * b, denominator),
        Fraction(c * c + a * a - b * b, denominator),
        Fraction(-2 * b * c, denominator),
    )
    return {"P": axis_from_vector(p), "Q": axis_from_vector(q), "R": axis_from_vector(r)}


def atlas_frame(chart: str, a: int, b: int, c: int) -> dict[str, Axis]:
    frame = north_frame(a, b, c)
    if chart == "north":
        return frame
    if chart != "south":
        raise ValueError(f"unknown atlas chart: {chart}")
    return {
        "P": axis_from_vector(negate(vector(frame["P"]))),
        "Q": frame["Q"],
        "R": axis_from_vector(negate(vector(frame["R"]))),
    }


def serialize_axis(axis: Axis) -> dict[str, str]:
    return {pauli: fraction_text(axis[pauli]) for pauli in sorted(axis)}


def catalog_entry(chart: str, index: int, a: int, b: int, c: int) -> dict[str, Any]:
    frame = atlas_frame(chart, a, b, c)
    prefix = "n" if chart == "north" else "s"
    return {
        "frame_id": f"{prefix}_{index:03d}",
        "chart": chart,
        "parameters": {"a": a, "b": b, "c": c},
        "axes": {label: serialize_axis(frame[label]) for label in ("P", "Q", "R")},
    }


def primitive_parameters() -> list[tuple[int, int, int]]:
    triples = []
    for c in range(1, ATLAS_BOUND + 1):
        for a in range(-ATLAS_BOUND, ATLAS_BOUND + 1):
            for b in range(-ATLAS_BOUND, ATLAS_BOUND + 1):
                if math.gcd(math.gcd(abs(a), abs(b)), c) != 1:
                    continue
                triples.append((a, b, c))
    return triples


def atlas_catalog() -> list[dict[str, Any]]:
    triples = primitive_parameters()
    rows = []
    for chart in ("north", "south"):
        for index, (a, b, c) in enumerate(triples):
            rows.append(catalog_entry(chart, index, a, b, c))
    return rows


def projective_catalog(
    catalog: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Choose one deterministic representative for each parity-axis line."""

    source = atlas_catalog() if catalog is None else catalog
    groups: dict[
        tuple[Fraction, Fraction, Fraction], list[dict[str, Any]]
    ] = defaultdict(list)
    for entry in source:
        groups[projective_axis_key(entry_frame(entry)["P"])].append(entry)

    rows = []
    for index, (key, entries) in enumerate(sorted(groups.items())):
        representative = min(entries, key=lambda item: item["frame_id"])
        rows.append(
            {
                **representative,
                "projective_axis_id": f"rp2_{index:03d}",
                "projective_axis": [fraction_text(value) for value in key],
                "gauge_equivalent_frame_ids": sorted(
                    entry["frame_id"] for entry in entries
                ),
            }
        )
    return rows


def entry_frame(entry: dict[str, Any]) -> dict[str, Axis]:
    params = entry["parameters"]
    return atlas_frame(
        entry["chart"], int(params["a"]), int(params["b"]), int(params["c"])
    )


def axis_key(axis: Axis) -> tuple[Fraction, Fraction, Fraction]:
    return vector(axis)


def projective_axis_key(axis: Axis) -> tuple[Fraction, Fraction, Fraction]:
    point = axis_key(axis)
    return min(point, negate(point))


def catalog_shape(catalog: list[dict[str, Any]]) -> dict[str, int]:
    directed_groups: dict[tuple[Fraction, Fraction, Fraction], list[dict[str, Any]]] = defaultdict(list)
    projective_groups: dict[tuple[Fraction, Fraction, Fraction], list[dict[str, Any]]] = defaultdict(list)
    for entry in catalog:
        p_axis = entry_frame(entry)["P"]
        directed_groups[axis_key(p_axis)].append(entry)
        projective_groups[projective_axis_key(p_axis)].append(entry)
    return {
        "atlas_row_count": len(catalog),
        "north_row_count": sum(entry["chart"] == "north" for entry in catalog),
        "south_row_count": sum(entry["chart"] == "south" for entry in catalog),
        "directed_axis_count": len(directed_groups),
        "projective_axis_count": len(projective_groups),
        "directed_overlap_count": sum(
            {entry["chart"] for entry in entries} == {"north", "south"}
            for entries in directed_groups.values()
        ),
    }


def frame_algebra_checks(catalog: list[dict[str, Any]]) -> dict[str, Any]:
    failures = []
    for entry in catalog:
        frame = entry_frame(entry)
        p, q, r = (vector(frame[label]) for label in ("P", "Q", "R"))
        checked = bool(
            dot(p, p) == 1
            and dot(q, q) == 1
            and dot(r, r) == 1
            and dot(p, q) == 0
            and dot(q, r) == 0
            and dot(r, p) == 0
            and cross(q, r) == p
            and cross(r, p) == q
            and cross(p, q) == r
        )
        if not checked:
            failures.append(entry["frame_id"])
    return {
        "row_count": len(catalog),
        "pass_count": len(catalog) - len(failures),
        "failures": failures,
        "checked": not failures,
    }


@cache
def frame_pool(
    n: int, chart: str, a: int, b: int, c: int
) -> tuple[tuple[str, Operator], ...]:
    frame = atlas_frame(chart, a, b, c)
    gamma_labels = [
        (site, endpoint) for site in range(n) for endpoint in ("Q", "R")
    ]
    entries: list[tuple[str, Operator]] = []
    for site, endpoint in gamma_labels:
        entries.append(
            (
                f"gamma:{site}:{endpoint}",
                base.gamma_fraction(n, frame, site, endpoint),
            )
        )
    for left_index, (left_site, left_endpoint) in enumerate(gamma_labels):
        for right_site, right_endpoint in gamma_labels[left_index + 1 :]:
            entries.append(
                (
                    f"bilinear:{left_site}:{left_endpoint}:{right_site}:{right_endpoint}",
                    base.bilinear_fraction(
                        n,
                        frame,
                        left_site,
                        left_endpoint,
                        right_site,
                        right_endpoint,
                    ),
                )
            )
    entries.append(
        (
            "parity",
            base.expand_fraction_axes(n, {site: frame["P"] for site in range(n)}),
        )
    )
    return tuple(entries)


def entry_pool(n: int, entry: dict[str, Any]) -> tuple[tuple[str, Operator], ...]:
    params = entry["parameters"]
    return frame_pool(
        n,
        entry["chart"],
        int(params["a"]),
        int(params["b"]),
        int(params["c"]),
    )


def atlas_subspace_sentinels(catalog: list[dict[str, Any]], n: int = 4) -> dict[str, Any]:
    directed_groups: dict[tuple[Fraction, Fraction, Fraction], list[dict[str, Any]]] = defaultdict(list)
    projective_groups: dict[tuple[Fraction, Fraction, Fraction], list[dict[str, Any]]] = defaultdict(list)
    for entry in catalog:
        p_axis = entry_frame(entry)["P"]
        directed_groups[axis_key(p_axis)].append(entry)
        projective_groups[projective_axis_key(p_axis)].append(entry)

    directed_rows = []
    for point, entries in sorted(directed_groups.items()):
        if {entry["chart"] for entry in entries} != {"north", "south"}:
            continue
        pools = [[operator for _, operator in entry_pool(n, entry)] for entry in entries]
        column_count = len(pools[0])
        ranks = [base.operator_column_rank(pool, BASIS_SELECTION_PRIME) for pool in pools]
        union_rank = base.operator_column_rank(
            [operator for pool in pools for operator in pool], BASIS_SELECTION_PRIME
        )
        directed_rows.append(
            {
                "axis": [fraction_text(value) for value in point],
                "frame_ids": [entry["frame_id"] for entry in entries],
                "individual_ranks": ranks,
                "union_rank": union_rank,
                "column_count": column_count,
                "checked": all(rank == column_count for rank in ranks)
                and union_rank == column_count,
            }
        )

    projective_rows = []
    for point, entries in sorted(projective_groups.items()):
        pools = [[operator for _, operator in entry_pool(n, entry)] for entry in entries]
        column_count = len(pools[0])
        ranks = [base.operator_column_rank(pool, BASIS_SELECTION_PRIME) for pool in pools]
        union_rank = base.operator_column_rank(
            [operator for pool in pools for operator in pool], BASIS_SELECTION_PRIME
        )
        projective_rows.append(
            {
                "axis": [fraction_text(value) for value in point],
                "frame_ids": [entry["frame_id"] for entry in entries],
                "individual_ranks": ranks,
                "union_rank": union_rank,
                "column_count": column_count,
                "checked": all(rank == column_count for rank in ranks)
                and union_rank == column_count,
            }
        )
    return {
        "n": n,
        "directed_overlap_rows": directed_rows,
        "directed_overlap_count": len(directed_rows),
        "directed_overlap_pass_count": sum(row["checked"] for row in directed_rows),
        "projective_rows": projective_rows,
        "projective_count": len(projective_rows),
        "projective_pass_count": sum(row["checked"] for row in projective_rows),
        "checked": all(row["checked"] for row in directed_rows + projective_rows),
    }


def atlas_frame_row(
    n: int,
    coupling: Fraction,
    entry: dict[str, Any],
    primes: tuple[int, ...] = MODULAR_PRIMES,
) -> dict[str, Any]:
    pool = list(entry_pool(n, entry))
    labels = [label for label, _ in pool]
    operators = [operator for _, operator in pool]
    hamiltonian = base.hamiltonian_operator(n, coupling)
    raw_columns = [
        base.commutator_integer(hamiltonian, operator) for operator in operators
    ]
    output_words = sorted({word for column in raw_columns for word in column})
    output_index = {word: index for index, word in enumerate(output_words)}
    columns = [
        {output_index[word]: coefficient for word, coefficient in column.items()}
        for column in raw_columns
    ]
    operator_ranks = {
        str(prime): base.operator_column_rank(operators, prime) for prime in primes
    }
    ranks = {
        str(prime): base.modular_sparse_rank(columns, prime) for prime in primes
    }
    matrix_payload = {
        "labels": labels,
        "output_basis": output_words,
        "triples": [
            (output_words[row], column_index, coefficient)
            for column_index, column in enumerate(columns)
            for row, coefficient in sorted(column.items())
        ],
    }
    operator_payload = {
        "labels": labels,
        "operators": [sorted(operator.items()) for operator in operators],
    }
    column_count = len(columns)
    row: dict[str, Any] = {
        "frame_id": entry["frame_id"],
        "chart": entry["chart"],
        "parameters": entry["parameters"],
        "axes": entry["axes"],
        "coupling": fraction_text(coupling),
        "n": n,
        "candidate_column_count": column_count,
        "operator_basis_pauli_nonzero_count": sum(
            len(operator) for operator in operators
        ),
        "operator_basis_sha256": canonical_hash(operator_payload),
        "operator_basis_modular_ranks": operator_ranks,
        "output_basis_size": len(output_words),
        "commutator_nonzero_count": sum(len(column) for column in columns),
        "commutator_matrix_sha256": canonical_hash(matrix_payload),
        "modular_primes": list(primes),
        "modular_ranks": ranks,
        "modular_nullities": {
            str(prime): column_count - ranks[str(prime)] for prime in primes
        },
        "operator_basis_independent": all(
            rank == column_count for rank in operator_ranks.values()
        ),
        "commutator_full_column_rank": all(
            rank == column_count for rank in ranks.values()
        ),
    }
    if "projective_axis_id" in entry:
        row["projective_axis_id"] = entry["projective_axis_id"]
        row["projective_axis"] = entry["projective_axis"]
        row["gauge_equivalent_frame_ids"] = entry[
            "gauge_equivalent_frame_ids"
        ]
    row["checked"] = bool(
        row["operator_basis_independent"]
        and (
            row["commutator_full_column_rank"]
            if coupling != 0
            else all(rank < column_count for rank in ranks.values())
        )
    )
    frame = entry_frame(entry)
    if coupling == 0 and frame["P"] == AXIS_A:
        witnesses = [
            base.expand_fraction_axes(n, {site: AXIS_A}) for site in range(n)
        ]
        commutators = [
            base.commutator_integer(hamiltonian, witness) for witness in witnesses
        ]
        basis_rank = base.operator_column_rank(operators, BASIS_SELECTION_PRIME)
        in_span = [
            base.operator_column_rank(
                [*operators, witness], BASIS_SELECTION_PRIME
            )
            == basis_rank
            for witness in witnesses
        ]
        row["onsite_axis_a_witness_count"] = len(witnesses)
        row["onsite_axis_a_commutes_count"] = sum(
            not item for item in commutators
        )
        row["onsite_axis_a_in_span_count"] = sum(in_span)
        row["onsite_axis_a_witnesses_checked"] = bool(
            all(not item for item in commutators) and all(in_span)
        )
    return row


def positive_control_entry(catalog: list[dict[str, Any]]) -> dict[str, Any]:
    matches = [
        entry
        for entry in catalog
        if entry["chart"] == "north" and entry_frame(entry)["P"] == AXIS_A
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one north-chart field-axis row, found {len(matches)}")
    return matches[0]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def verify_public_freeze(root: Path, preregistration_commit: str) -> dict[str, Any]:
    if not preregistration_commit:
        raise ValueError("--preregistration-commit is required for frozen holdouts")
    commit = subprocess.run(
        ["git", "rev-parse", f"{preregistration_commit}^{{commit}}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=root,
        check=False,
    ).returncode == 0
    frozen_bytes = subprocess.run(
        ["git", "show", f"{commit}:{CONTRACT_PATH}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    frozen_hash = sha256_bytes(frozen_bytes)
    current_hash = sha256_file(root / CONTRACT_PATH)
    contract = json.loads((root / CONTRACT_PATH).read_text())
    code_files = []
    for relative_path in contract["code_freeze"]["paths"]:
        frozen_file = subprocess.run(
            ["git", "show", f"{commit}:{relative_path}"],
            cwd=root,
            check=True,
            capture_output=True,
        ).stdout
        current_file = (root / relative_path).read_bytes()
        code_files.append(
            {
                "path": relative_path,
                "preregistration_sha256": sha256_bytes(frozen_file),
                "current_sha256": sha256_bytes(current_file),
                "matches": frozen_file == current_file,
            }
        )
    return {
        "preregistration_commit": commit,
        "is_ancestor_of_execution_head": ancestor,
        "contract_sha256_at_preregistration_commit": frozen_hash,
        "expected_contract_sha256": EXPECTED_CONTRACT_SHA256,
        "current_contract_sha256": current_hash,
        "code_files": code_files,
        "code_freeze_verified": all(item["matches"] for item in code_files),
        "runtime_versions": {"python": sys.version.split()[0]},
        "verified": bool(
            ancestor
            and frozen_hash == EXPECTED_CONTRACT_SHA256
            and current_hash == EXPECTED_CONTRACT_SHA256
            and all(item["matches"] for item in code_files)
        ),
    }


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


def protocol(contract: dict[str, Any]) -> dict[str, Any]:
    catalog = atlas_catalog()
    projective = projective_catalog(catalog)
    shape = catalog_shape(catalog)
    sentinels = atlas_subspace_sentinels(catalog)
    return {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "contract": {
            "path": str(CONTRACT_PATH),
            "sha256": EXPECTED_CONTRACT_SHA256,
            "version": contract["version"],
            "status": contract["status"],
        },
        "atlas": contract["atlas"],
        "atlas_catalog": {
            "bound": ATLAS_BOUND,
            **shape,
            "sha256": canonical_hash(catalog),
        },
        "projective_catalog": {
            "row_count": len(projective),
            "sha256": canonical_hash(projective),
        },
        "frame_algebra": frame_algebra_checks(catalog),
        "subspace_sentinels": sentinels,
        "frozen_holdouts": [
            fraction_text(value) for value in FROZEN_HOLDOUT_COUPLINGS
        ],
        "grid_sizes": list(GRID_SIZES),
        "grid_row_count": len(FROZEN_HOLDOUT_COUPLINGS)
        * len(GRID_SIZES)
        * len(projective),
        "modular_primes": list(MODULAR_PRIMES),
        "independent_audit_primes": list(AUDIT_PRIMES),
        "positive_control": contract["positive_control"],
        "claim_boundary": {
            "true_claims": TRUE_CLAIMS,
            "false_claims": FALSE_CLAIMS,
            "scientific_promotion_accepted": False,
            "new_credit_delta": 0,
        },
    }


def build_engineering_probe(root: Path) -> dict[str, Any]:
    contract = json.loads((root / CONTRACT_PATH).read_text())
    catalog = atlas_catalog()
    projective = projective_catalog(catalog)
    control_entry = positive_control_entry(catalog)
    samples = projective[:4]
    return {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "mode": "engineering_probe_only",
        "engineering_coupling": fraction_text(ENGINEERING_COUPLING),
        "acceptance_count": 0,
        "protocol": protocol(contract),
        "grid_probe_rows": [
            atlas_frame_row(6, ENGINEERING_COUPLING, entry) for entry in samples
        ],
        "positive_control": atlas_frame_row(6, Fraction(0), control_entry),
        "frozen_holdouts_executed": False,
    }


def build_result(root: Path, preregistration_commit: str) -> dict[str, Any]:
    contract = json.loads((root / CONTRACT_PATH).read_text())
    freeze = verify_public_freeze(root, preregistration_commit)
    if not freeze["verified"]:
        raise RuntimeError("public preregistration freeze verification failed")
    catalog = atlas_catalog()
    projective = projective_catalog(catalog)
    protocol_payload = protocol(contract)
    grid_rows = [
        atlas_frame_row(n, coupling, entry)
        for coupling in FROZEN_HOLDOUT_COUPLINGS
        for n in GRID_SIZES
        for entry in projective
    ]
    control = atlas_frame_row(6, Fraction(0), positive_control_entry(catalog))
    grid_pass_count = sum(row["checked"] for row in grid_rows)
    shape = catalog_shape(catalog)
    sentinels = protocol_payload["subspace_sentinels"]
    expected_column_counts = {6: 79, 8: 137, 10: 211}
    observed_column_counts: dict[int, set[int]] = defaultdict(set)
    for row in grid_rows:
        observed_column_counts[row["n"]].add(row["candidate_column_count"])
    column_counts_checked = all(
        observed_column_counts[n] == {expected}
        for n, expected in expected_column_counts.items()
    )
    catalog_hash = canonical_hash(catalog)
    projective_catalog_hash = canonical_hash(projective)
    requirements = [
        requirement("P1", "Public commit hash-binds the R200 contract and code", freeze["verified"], freeze),
        requirement(
            "P2",
            "Frozen holdouts are disjoint from every earlier coupling grid",
            set(FROZEN_HOLDOUT_COUPLINGS).isdisjoint(PREVIOUSLY_OBSERVED_COUPLINGS),
            {
                "holdouts": [fraction_text(value) for value in FROZEN_HOLDOUT_COUPLINGS],
                "previous_count": len(PREVIOUSLY_OBSERVED_COUPLINGS),
            },
        ),
        requirement(
            "P3",
            "Engineering work contributes zero frozen decisions",
            bool(
                ENGINEERING_COUPLING in PREVIOUSLY_OBSERVED_COUPLINGS
                and ENGINEERING_COUPLING not in FROZEN_HOLDOUT_COUPLINGS
                and contract["engineering_probe"]["acceptance_count"] == 0
                and contract["engineering_probe"]["sample_row_count"] == 4
            ),
            {
                "acceptance_count": contract["engineering_probe"][
                    "acceptance_count"
                ],
                "sample_row_count": contract["engineering_probe"][
                    "sample_row_count"
                ],
                "coupling": fraction_text(ENGINEERING_COUPLING),
            },
        ),
        requirement(
            "P4",
            "Every atlas frame is exactly right-handed and orthonormal",
            protocol_payload["frame_algebra"]["checked"],
            protocol_payload["frame_algebra"],
        ),
        requirement(
            "P5",
            "The gauge-sentinel atlas has the frozen shape and digest",
            bool(
                shape["atlas_row_count"] == ATLAS_EXPECTED_COUNT
                and shape["directed_axis_count"] == DIRECTED_AXIS_EXPECTED_COUNT
                and shape["projective_axis_count"] == PROJECTIVE_AXIS_EXPECTED_COUNT
                and shape["directed_overlap_count"] == DIRECTED_OVERLAP_EXPECTED_COUNT
                and catalog_hash == ATLAS_EXPECTED_SHA256
            ),
            {**shape, "sha256": catalog_hash, "expected_sha256": ATLAS_EXPECTED_SHA256},
        ),
        requirement(
            "P6",
            "All atlas-overlap and projective-axis candidate subspaces agree at n=4",
            bool(
                sentinels["checked"]
                and sentinels["directed_overlap_pass_count"] == DIRECTED_OVERLAP_EXPECTED_COUNT
                and sentinels["projective_pass_count"] == PROJECTIVE_AXIS_EXPECTED_COUNT
            ),
            {
                "directed_overlap_pass_count": sentinels["directed_overlap_pass_count"],
                "projective_pass_count": sentinels["projective_pass_count"],
            },
        ),
        requirement(
            "P7",
            "The scientific catalog has exactly 31 unique projective axes",
            bool(
                len(projective) == PROJECTIVE_AXIS_EXPECTED_COUNT
                and projective_catalog_hash
                == PROJECTIVE_CATALOG_EXPECTED_SHA256
            ),
            {
                "row_count": len(projective),
                "sha256": projective_catalog_hash,
                "expected_sha256": PROJECTIVE_CATALOG_EXPECTED_SHA256,
            },
        ),
        requirement(
            "P8",
            "The complete candidate family has the frozen column counts",
            column_counts_checked,
            {
                "expected": {
                    str(n): expected
                    for n, expected in expected_column_counts.items()
                },
                "observed": {str(n): sorted(values) for n, values in observed_column_counts.items()},
            },
        ),
        requirement(
            "P9",
            "All 186 frozen projective-axis rows execute",
            len(grid_rows) == 186,
            {"actual": len(grid_rows), "expected": 186},
        ),
        requirement(
            "P10",
            "Every frozen projective-axis operator pool and commutator matrix has full column rank",
            grid_pass_count == len(grid_rows),
            {"passed": grid_pass_count, "total": len(grid_rows)},
        ),
        requirement(
            "P11",
            "The field-axis control recovers the exact ranks and six onsite charges",
            bool(
                control["checked"]
                and control["candidate_column_count"] == 79
                and all(rank == 79 for rank in control["operator_basis_modular_ranks"].values())
                and all(rank == 42 for rank in control["modular_ranks"].values())
                and all(nullity == 37 for nullity in control["modular_nullities"].values())
                and control.get("onsite_axis_a_witnesses_checked")
                and control.get("onsite_axis_a_commutes_count") == 6
                and control.get("onsite_axis_a_in_span_count") == 6
            ),
            {
                "frame_id": control["frame_id"],
                "operator_ranks": control["operator_basis_modular_ranks"],
                "commutator_ranks": control["modular_ranks"],
                "nullities": control["modular_nullities"],
            },
        ),
        requirement(
            "P12",
            "Every forbidden broad claim remains false",
            bool(
                contract["claim_boundary"]["scientific_promotion_accepted"]
                is False
                and contract["claim_boundary"]["new_credit_delta"] == 0
                and set(contract["claim_boundary"]["forbidden"])
                == set(FALSE_CLAIMS)
            ),
            {
                "false_claim_count": len(FALSE_CLAIMS),
                "new_credit_delta": 0,
            },
        ),
        requirement(
            "P13",
            "All declared R200 main-executor gates pass",
            bool(
                freeze["verified"]
                and protocol_payload["frame_algebra"]["checked"]
                and sentinels["checked"]
                and len(projective) == PROJECTIVE_AXIS_EXPECTED_COUNT
                and projective_catalog_hash
                == PROJECTIVE_CATALOG_EXPECTED_SHA256
                and column_counts_checked
                and grid_pass_count == 186
                and control["checked"]
            ),
            {
                "grid_pass_count": grid_pass_count,
                "sentinels_passed": sentinels["checked"],
                "positive_control_passed": control["checked"],
            },
        ),
    ]
    all_passed = all(item["passed"] for item in requirements)
    result: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "status": STATUS_ACCEPTED if all_passed else STATUS_REJECTED,
        "public_freeze": freeze,
        "protocol": protocol_payload,
        "atlas_catalog": catalog,
        "projective_catalog": projective,
        "grid_rows": grid_rows,
        "positive_control": control,
        "summary": {
            **shape,
            "projective_acceptance_row_count": len(projective),
            "projective_catalog_sha256": projective_catalog_hash,
            "grid_row_count": len(grid_rows),
            "grid_pass_count": grid_pass_count,
            "largest_candidate_column_count": max(row["candidate_column_count"] for row in grid_rows),
            "largest_commutator_nonzero_count": max(row["commutator_nonzero_count"] for row in grid_rows),
            "positive_control_nullities": control["modular_nullities"],
            "requirement_pass_count": sum(item["passed"] for item in requirements),
            "requirement_count": len(requirements),
        },
        "requirements": requirements,
        "claims": {
            **{claim: all_passed for claim in TRUE_CLAIMS},
            **{claim: False for claim in FALSE_CLAIMS},
            "scientific_promotion_accepted": False,
            "new_credit_delta": 0,
        },
    }
    result["protocol_hash"] = canonical_hash(protocol_payload)
    result["payload_sha256"] = canonical_hash(result)
    return result


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    return "\n".join(
        [
            "# B9 R200 Finite Projective Rational Bloch Atlas Stress",
            "",
            f"- Status: `{result['status']}`",
            f"- Protocol hash: `{result['protocol_hash']}`",
            f"- Payload hash: `{result['payload_sha256']}`",
            f"- Public preregistration commit: `{result['public_freeze']['preregistration_commit']}`",
            f"- Atlas rows: `{summary['atlas_row_count']}`",
            f"- Directed/projective axes: `{summary['directed_axis_count']}/{summary['projective_axis_count']}`",
            f"- Frozen grid rows: `{summary['grid_pass_count']}/{summary['grid_row_count']}`",
            f"- Requirements: `{summary['requirement_pass_count']}/{summary['requirement_count']}`",
            "- Scientific promotion: `false`",
            "- New credit delta: `0`",
            "",
            "## Research Question",
            "",
            "Does the R193 candidate expose an exact quadratic-Majorana charge on a finite two-dimensional rational projective grid after surviving the R198 and R199 one-dimensional charts?",
            "",
            "## Claim Boundary",
            "",
            "R200 closes only the publicly frozen finite rational projective-axis catalog. It does not prove a continuous two-dimensional Bloch-sphere exclusion, cover irrational axes, nonlinear frame mixtures, higher-order charges, nonlocal dualities, interacting integrability, larger-size drift, nonintegrability, chaos, hardness, Quantum PCP, NLTS, BQP, hardware, or a solved frontier.",
            "",
        ]
    )


def catalog_summary() -> dict[str, Any]:
    catalog = atlas_catalog()
    projective = projective_catalog(catalog)
    return {
        **catalog_shape(catalog),
        "sha256": canonical_hash(catalog),
        "projective_catalog_count": len(projective),
        "projective_catalog_sha256": canonical_hash(projective),
        "frame_algebra": frame_algebra_checks(catalog),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--catalog-summary", action="store_true")
    modes.add_argument("--engineering-probe", action="store_true")
    modes.add_argument("--execute-frozen-holdouts", action="store_true")
    parser.add_argument("--preregistration-commit", default="")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if args.catalog_summary:
        result = catalog_summary()
    elif args.engineering_probe:
        result = build_engineering_probe(root)
    else:
        result = build_result(root, args.preregistration_commit)
    if not args.catalog_summary:
        output_path = args.output if args.output.is_absolute() else root / args.output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2 if args.pretty else None, sort_keys=True) + "\n"
        )
        if args.execute_frozen_holdouts:
            report_path = args.report if args.report.is_absolute() else root / args.report
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(render_report(result))
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    if args.execute_frozen_holdouts:
        return 0 if all(item["passed"] for item in result.get("requirements", [])) else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
