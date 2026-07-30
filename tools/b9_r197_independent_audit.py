#!/usr/bin/env python3
"""Independently reconstruct and audit every B9 R197 row.

This implementation uses sparse symplectic Pauli bit pairs. It deliberately
does not import any R193-R197 construction module.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any, Iterable


METHOD = "b9_r197_independent_symplectic_audit_v1"
VERSION = "1.0"
LAST_UPDATED = "2026-07-30"
AUDIT_PRIME = 1_000_037
BASIS_PRIME = 1_000_003

CONTRACT_PATH = Path(
    "benchmarks/B9_R197_nonstandard_fermionization_contract_v0.json"
)
RESULT_PATH = Path(
    "results/B9_R197_nonstandard_fermionization_stress_v1.json"
)
AUDIT_PATH = Path("results/B9_R197_independent_audit_v1.json")
EXPECTED_CONTRACT_SHA256 = (
    "6ab7640f7d2ab686f81c2da7519260c5950120352dc14e7f6e4b700829b6b39e"
)

Axis = dict[int, Fraction]
PauliKey = tuple[int, int]
SparseOperator = dict[PauliKey, int]

I, X, Y, Z = 0, 1, 2, 3
AXIS_X: Axis = {X: Fraction(1)}
AXIS_Y: Axis = {Y: Fraction(1)}
AXIS_Z: Axis = {Z: Fraction(1)}
AXIS_A: Axis = {X: Fraction(-4, 5), Z: Fraction(3, 5)}
AXIS_B: Axis = {X: Fraction(3, 5), Z: Fraction(4, 5)}

FRAMES: dict[str, dict[str, Axis]] = {
    "pauli_x": {"P": AXIS_X, "Q": AXIS_Y, "R": AXIS_Z},
    "pauli_y": {"P": AXIS_Y, "Q": AXIS_Z, "R": AXIS_X},
    "pauli_z": {"P": AXIS_Z, "Q": AXIS_X, "R": AXIS_Y},
    "tilted_a": {"P": AXIS_A, "Q": AXIS_B, "R": AXIS_Y},
    "tilted_b": {"P": AXIS_B, "Q": AXIS_Y, "R": AXIS_A},
}
FRAME_ORDER = tuple(FRAMES)

# phase exponent e denotes i**e.
LOCAL_PRODUCT: dict[tuple[int, int], tuple[int, int]] = {
    (I, I): (0, I),
    (I, X): (0, X),
    (I, Y): (0, Y),
    (I, Z): (0, Z),
    (X, I): (0, X),
    (Y, I): (0, Y),
    (Z, I): (0, Z),
    (X, X): (0, I),
    (Y, Y): (0, I),
    (Z, Z): (0, I),
    (X, Y): (1, Z),
    (Y, X): (3, Z),
    (Y, Z): (1, X),
    (Z, Y): (3, X),
    (Z, X): (1, Y),
    (X, Z): (3, Y),
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_hash(value: Any) -> str:
    return sha256_bytes(
        json.dumps(
            value, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def parse_fraction(value: str) -> Fraction:
    return Fraction(value)


def lcm(values: Iterable[int]) -> int:
    result = 1
    for value in values:
        result = math.lcm(result, value)
    return result


def local_code(key: PauliKey, site: int) -> int:
    x_bit = (key[0] >> site) & 1
    z_bit = (key[1] >> site) & 1
    if x_bit and z_bit:
        return Y
    if x_bit:
        return X
    if z_bit:
        return Z
    return I


def code_key(code: int, site: int) -> PauliKey:
    if code == X:
        return (1 << site, 0)
    if code == Y:
        return (1 << site, 1 << site)
    if code == Z:
        return (0, 1 << site)
    return (0, 0)


def key_word(key: PauliKey, n: int) -> str:
    chars = "IXYZ"
    return "".join(chars[local_code(key, site)] for site in range(n))


def primitive(
    value: dict[PauliKey, Fraction] | dict[PauliKey, int],
    n: int,
) -> SparseOperator:
    fractions = {
        key: Fraction(coefficient)
        for key, coefficient in value.items()
        if coefficient
    }
    if not fractions:
        return {}
    denominator = lcm(
        coefficient.denominator for coefficient in fractions.values()
    )
    integers = {
        key: int(coefficient * denominator)
        for key, coefficient in fractions.items()
    }
    divisor = 0
    for coefficient in integers.values():
        divisor = math.gcd(divisor, abs(coefficient))
    integers = {
        key: coefficient // divisor
        for key, coefficient in integers.items()
        if coefficient
    }
    first = min(integers, key=lambda key: key_word(key, n))
    if integers[first] < 0:
        integers = {
            key: -coefficient for key, coefficient in integers.items()
        }
    return dict(
        sorted(integers.items(), key=lambda item: key_word(item[0], n))
    )


def operator_word_items(
    operator: SparseOperator,
    n: int,
) -> list[tuple[str, int]]:
    return sorted(
        (
            (key_word(key, n), coefficient)
            for key, coefficient in operator.items()
        )
    )


def operator_key(
    operator: SparseOperator,
    n: int,
) -> tuple[tuple[str, int], ...]:
    return tuple(operator_word_items(operator, n))


def expand_axes(
    n: int,
    site_axes: dict[int, Axis],
    scale: int = 1,
) -> SparseOperator:
    partial: dict[PauliKey, Fraction] = {
        (0, 0): Fraction(scale)
    }
    for site in sorted(site_axes):
        updated: dict[PauliKey, Fraction] = {}
        for key, coefficient in partial.items():
            for code, local_coefficient in site_axes[site].items():
                local_key = code_key(code, site)
                output = (key[0] | local_key[0], key[1] | local_key[1])
                updated[output] = (
                    updated.get(output, Fraction(0))
                    + coefficient * local_coefficient
                )
        partial = updated
    return primitive(partial, n)


def gamma(
    n: int,
    frame: dict[str, Axis],
    site: int,
    endpoint: str,
) -> SparseOperator:
    axes = {index: frame["P"] for index in range(site)}
    axes[site] = frame[endpoint]
    return expand_axes(n, axes)


def bilinear(
    n: int,
    frame: dict[str, Axis],
    left_site: int,
    left_endpoint: str,
    right_site: int,
    right_endpoint: str,
) -> SparseOperator:
    if left_site == right_site:
        if (left_endpoint, right_endpoint) != ("Q", "R"):
            raise ValueError("invalid same-site ordering")
        return expand_axes(n, {left_site: frame["P"]}, scale=-1)
    axes: dict[int, Axis] = {}
    sign = 1
    if left_endpoint == "Q":
        axes[left_site] = frame["R"]
    else:
        axes[left_site] = frame["Q"]
        sign = -1
    for site in range(left_site + 1, right_site):
        axes[site] = frame["P"]
    axes[right_site] = frame[right_endpoint]
    return expand_axes(n, axes, scale=sign)


@cache
def frame_pool(
    n: int,
    frame_id: str,
) -> tuple[tuple[str, SparseOperator], ...]:
    frame = FRAMES[frame_id]
    gamma_labels = [
        (site, endpoint)
        for site in range(n)
        for endpoint in ("Q", "R")
    ]
    entries: list[tuple[str, SparseOperator]] = []
    for site, endpoint in gamma_labels:
        entries.append(
            (
                f"{frame_id}:gamma:{site}:{endpoint}",
                gamma(n, frame, site, endpoint),
            )
        )
    for left_index, (left_site, left_endpoint) in enumerate(gamma_labels):
        for right_site, right_endpoint in gamma_labels[left_index + 1 :]:
            entries.append(
                (
                    (
                        f"{frame_id}:bilinear:{left_site}:{left_endpoint}:"
                        f"{right_site}:{right_endpoint}"
                    ),
                    bilinear(
                        n,
                        frame,
                        left_site,
                        left_endpoint,
                        right_site,
                        right_endpoint,
                    ),
                )
            )
    parity = expand_axes(
        n, {site: frame["P"] for site in range(n)}
    )
    entries.append((f"{frame_id}:parity", parity))
    return tuple(entries)


def hamiltonian(n: int, coupling: Fraction) -> SparseOperator:
    terms: dict[PauliKey, Fraction] = {}
    for site in range(n):
        x_key = code_key(X, site)
        z_key = code_key(Z, site)
        terms[x_key] = terms.get(x_key, Fraction(0)) - 1
        terms[z_key] = terms.get(z_key, Fraction(0)) + Fraction(3, 4)
    for site in range(n - 1):
        zz_key = (0, (1 << site) | (1 << (site + 1)))
        terms[zz_key] = terms.get(zz_key, Fraction(0)) + coupling
    return primitive(terms, n)


def select_basis(
    entries: list[tuple[str, SparseOperator]],
    n: int,
    prime: int = BASIS_PRIME,
) -> list[tuple[str, SparseOperator]]:
    pivots: dict[PauliKey, dict[PauliKey, int]] = {}
    selected: list[tuple[str, SparseOperator]] = []
    for label, operator in entries:
        vector = {
            key: coefficient % prime
            for key, coefficient in operator.items()
            if coefficient % prime
        }
        while vector:
            pivot = min(vector, key=lambda key: key_word(key, n))
            if pivot not in pivots:
                inverse = pow(vector[pivot], prime - 2, prime)
                pivots[pivot] = {
                    key: (coefficient * inverse) % prime
                    for key, coefficient in vector.items()
                    if (coefficient * inverse) % prime
                }
                selected.append((label, operator))
                break
            factor = vector[pivot]
            for key, coefficient in pivots[pivot].items():
                updated = (
                    vector.get(key, 0) - factor * coefficient
                ) % prime
                if updated:
                    vector[key] = updated
                else:
                    vector.pop(key, None)
    return selected


def basis(
    n: int,
    coupling: Fraction,
    frame_ids: tuple[str, ...],
) -> list[tuple[str, SparseOperator]]:
    identity = {(0, 0): 1}
    h_value = hamiltonian(n, coupling)
    entries: list[tuple[str, SparseOperator]] = [
        ("identity", identity),
        ("hamiltonian", h_value),
    ]
    seen = {operator_key(identity, n), operator_key(h_value, n)}
    for frame_id in frame_ids:
        for label, operator in frame_pool(n, frame_id):
            key = operator_key(operator, n)
            if key not in seen:
                entries.append((label, operator))
                seen.add(key)
    selected = select_basis(entries, n)
    if [label for label, _ in selected[:2]] != [
        "identity",
        "hamiltonian",
    ]:
        raise AssertionError("basis prefix mismatch")
    return selected


def anticommutes(left: PauliKey, right: PauliKey) -> bool:
    phase = (
        (left[0] & right[1]).bit_count()
        + (left[1] & right[0]).bit_count()
    )
    return phase % 2 == 1


def multiply(
    left: PauliKey,
    right: PauliKey,
    n: int,
) -> tuple[int, PauliKey]:
    exponent = 0
    output_x = 0
    output_z = 0
    for site in range(n):
        local_exponent, output_code = LOCAL_PRODUCT[
            (local_code(left, site), local_code(right, site))
        ]
        exponent = (exponent + local_exponent) % 4
        local_key = code_key(output_code, site)
        output_x |= local_key[0]
        output_z |= local_key[1]
    return exponent, (output_x, output_z)


def commutator(
    h_value: SparseOperator,
    candidate: SparseOperator,
    n: int,
) -> SparseOperator:
    output: dict[PauliKey, Fraction] = {}
    for h_key, h_coefficient in h_value.items():
        for candidate_key, candidate_coefficient in candidate.items():
            if not anticommutes(h_key, candidate_key):
                continue
            exponent, output_key = multiply(h_key, candidate_key, n)
            if exponent == 1:
                sign = 1
            elif exponent == 3:
                sign = -1
            else:
                raise AssertionError("anticommuting phase is not imaginary")
            output[output_key] = (
                output.get(output_key, Fraction(0))
                + h_coefficient * candidate_coefficient * sign
            )
    return primitive(output, n)


def modular_rank(
    columns: list[dict[int, int]],
    prime: int,
) -> int:
    pivots: dict[int, dict[int, int]] = {}
    for column in columns:
        vector = {
            row: coefficient % prime
            for row, coefficient in column.items()
            if coefficient % prime
        }
        while vector:
            pivot = min(vector)
            if pivot not in pivots:
                inverse = pow(vector[pivot], prime - 2, prime)
                pivots[pivot] = {
                    row: (coefficient * inverse) % prime
                    for row, coefficient in vector.items()
                    if (coefficient * inverse) % prime
                }
                break
            factor = vector[pivot]
            for row, coefficient in pivots[pivot].items():
                updated = (
                    vector.get(row, 0) - factor * coefficient
                ) % prime
                if updated:
                    vector[row] = updated
                else:
                    vector.pop(row, None)
    return len(pivots)


def row_rebuild(
    n: int,
    coupling: Fraction,
    frame_ids: tuple[str, ...],
) -> dict[str, Any]:
    selected = basis(n, coupling, frame_ids)
    labels = [label for label, _ in selected]
    operators = [operator for _, operator in selected]
    h_value = operators[1]
    raw_columns = [
        commutator(h_value, operator, n) for operator in operators
    ]
    output_words = sorted(
        {
            key_word(key, n)
            for column in raw_columns
            for key in column
        }
    )
    output_index = {
        word: index for index, word in enumerate(output_words)
    }
    columns: list[dict[int, int]] = []
    for column in raw_columns:
        columns.append(
            {
                output_index[key_word(key, n)]: coefficient
                for key, coefficient in column.items()
            }
        )
    operator_hash = canonical_hash(
        {
            "labels": labels,
            "operators": [
                operator_word_items(operator, n)
                for operator in operators
            ],
        }
    )
    triples = [
        (output_words[row], column_index, coefficient)
        for column_index, column in enumerate(columns)
        for row, coefficient in sorted(column.items())
    ]
    matrix_hash = canonical_hash(
        {
            "labels": labels,
            "output_basis": output_words,
            "triples": triples,
        }
    )
    rank = modular_rank(columns, AUDIT_PRIME)
    return {
        "frame_ids": list(frame_ids),
        "coupling": str(coupling),
        "n": n,
        "raw_candidate_count": (
            2
            + sum(len(frame_pool(n, frame_id)) for frame_id in frame_ids)
        ),
        "independent_operator_basis_size": len(columns),
        "operator_basis_pauli_nonzero_count": sum(
            len(operator) for operator in operators
        ),
        "operator_basis_sha256": operator_hash,
        "output_basis_size": len(output_words),
        "commutator_nonzero_count": len(triples),
        "commutator_matrix_sha256": matrix_hash,
        "identity_kernel_verified": not columns[0],
        "hamiltonian_kernel_verified": not columns[1],
        "audit_prime": AUDIT_PRIME,
        "audit_rank": rank,
        "audit_nullity": len(columns) - rank,
    }


def in_span(
    operator: SparseOperator,
    selected: list[tuple[str, SparseOperator]],
    n: int,
) -> bool:
    return len(
        select_basis(
            list(selected) + [("__witness__", operator)],
            n,
            BASIS_PRIME,
        )
    ) == len(selected)


def control_rebuild(
    frame_ids: tuple[str, ...],
) -> dict[str, Any]:
    n = 8
    coupling = Fraction(0)
    rebuilt = row_rebuild(n, coupling, frame_ids)
    selected = basis(n, coupling, frame_ids)
    h_value = selected[1][1]
    witnesses = [
        expand_axes(n, {site: AXIS_A}) for site in range(n)
    ]
    commutes = [
        not commutator(h_value, witness, n) for witness in witnesses
    ]
    contained = [
        in_span(witness, selected, n) for witness in witnesses
    ]
    rebuilt.update(
        {
            "onsite_tilted_charge_witness_count": len(witnesses),
            "onsite_tilted_charge_commutes_count": sum(commutes),
            "onsite_tilted_charge_in_span_count": sum(contained),
            "onsite_tilted_charge_witnesses_checked": bool(
                all(commutes) and all(contained)
            ),
        }
    )
    return rebuilt


def frame_checks() -> dict[str, Any]:
    def vector(axis: Axis) -> tuple[Fraction, Fraction, Fraction]:
        return tuple(axis.get(code, Fraction(0)) for code in (X, Y, Z))  # type: ignore[return-value]

    def dot(
        left: tuple[Fraction, Fraction, Fraction],
        right: tuple[Fraction, Fraction, Fraction],
    ) -> Fraction:
        return sum(
            (a * b for a, b in zip(left, right)),
            start=Fraction(0),
        )

    def cross(
        left: tuple[Fraction, Fraction, Fraction],
        right: tuple[Fraction, Fraction, Fraction],
    ) -> tuple[Fraction, Fraction, Fraction]:
        return (
            left[1] * right[2] - left[2] * right[1],
            left[2] * right[0] - left[0] * right[2],
            left[0] * right[1] - left[1] * right[0],
        )

    rows = []
    for frame_id, frame in FRAMES.items():
        p, q, r = (
            vector(frame["P"]),
            vector(frame["Q"]),
            vector(frame["R"]),
        )
        checked = bool(
            dot(p, p) == dot(q, q) == dot(r, r) == 1
            and dot(p, q) == dot(q, r) == dot(r, p) == 0
            and cross(q, r) == p
            and cross(r, p) == q
            and cross(p, q) == r
        )
        rows.append({"frame_id": frame_id, "checked": checked})
    return {
        "rows": rows,
        "checked_frame_count": sum(row["checked"] for row in rows),
        "frame_count": len(rows),
        "checked": all(row["checked"] for row in rows),
    }


def verify_freeze(
    root: Path,
    source: dict[str, Any],
) -> dict[str, Any]:
    commit = source["public_freeze"]["preregistration_commit"]
    ancestor = (
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=root,
            check=False,
        ).returncode
        == 0
    )
    frozen = subprocess.run(
        ["git", "show", f"{commit}:{CONTRACT_PATH}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    frozen_hash = sha256_bytes(frozen)
    return {
        "preregistration_commit": commit,
        "is_ancestor": ancestor,
        "contract_sha256_at_commit": frozen_hash,
        "working_contract_sha256": sha256_file(root / CONTRACT_PATH),
        "expected_contract_sha256": EXPECTED_CONTRACT_SHA256,
        "verified": bool(
            ancestor
            and frozen_hash == EXPECTED_CONTRACT_SHA256
            and sha256_file(root / CONTRACT_PATH)
            == EXPECTED_CONTRACT_SHA256
        ),
    }


def compare_row(
    source: dict[str, Any],
    rebuilt: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    exact_fields = [
        "frame_ids",
        "coupling",
        "n",
        "raw_candidate_count",
        "independent_operator_basis_size",
        "operator_basis_pauli_nonzero_count",
        "operator_basis_sha256",
        "output_basis_size",
        "commutator_nonzero_count",
        "commutator_matrix_sha256",
        "identity_kernel_verified",
        "hamiltonian_kernel_verified",
    ]
    row_id = (
        f"J={source['coupling']},n={source['n']},"
        f"frames={','.join(source['frame_ids'])}"
    )
    for field in exact_fields:
        if source.get(field) != rebuilt.get(field):
            errors.append(f"{row_id}: {field} mismatch")
    if rebuilt["audit_nullity"] != 2:
        errors.append(
            f"{row_id}: third-prime nullity "
            f"{rebuilt['audit_nullity']} != 2"
        )
    return errors


def build_audit(root: Path) -> dict[str, Any]:
    source = json.loads((root / RESULT_PATH).read_text())
    freeze = verify_freeze(root, source)
    algebra = frame_checks()
    rebuilt_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for source_row in source["rows"]:
        rebuilt = row_rebuild(
            int(source_row["n"]),
            parse_fraction(source_row["coupling"]),
            tuple(source_row["frame_ids"]),
        )
        rebuilt_rows.append(rebuilt)
        errors.extend(compare_row(source_row, rebuilt))

    control_rows = [
        control_rebuild(("tilted_a",)),
        control_rebuild(FRAME_ORDER),
    ]
    for source_control, rebuilt in zip(
        source["positive_control_rows"], control_rows
    ):
        control_errors = compare_row(
            {
                **source_control,
                "coupling": "0",
            },
            rebuilt,
        )
        # Controls intentionally have nullity > 2.
        control_errors = [
            error
            for error in control_errors
            if "third-prime nullity" not in error
        ]
        errors.extend(control_errors)
        for field in (
            "onsite_tilted_charge_witness_count",
            "onsite_tilted_charge_commutes_count",
            "onsite_tilted_charge_in_span_count",
            "onsite_tilted_charge_witnesses_checked",
        ):
            if source_control.get(field) != rebuilt.get(field):
                errors.append(
                    f"control {rebuilt['frame_ids']}: {field} mismatch"
                )
        source_nullity = next(
            iter(source_control["modular_nullities"].values())
        )
        if rebuilt["audit_nullity"] != source_nullity:
            errors.append(
                f"control {rebuilt['frame_ids']}: third-prime nullity "
                f"{rebuilt['audit_nullity']} != source {source_nullity}"
            )

    if not freeze["verified"]:
        errors.append("public freeze verification failed")
    if not algebra["checked"]:
        errors.append("independent frame algebra verification failed")
    if source.get("status") != "checked_nonstandard_fermionization_boundary":
        errors.append("source result status is not accepted boundary")
    if source.get("requirements_passed") != source.get(
        "requirements_total"
    ):
        errors.append("source requirements are incomplete")
    if source["summary"].get("scientific_promotion_accepted") is not False:
        errors.append("scientific promotion must remain false")
    if source["summary"].get("new_credit_delta") != 0:
        errors.append("new credit delta must remain zero")

    core = {
        "source_result": {
            "path": str(RESULT_PATH),
            "sha256": sha256_file(root / RESULT_PATH),
            "payload_sha256": source["payload_sha256"],
            "protocol_sha256": source["protocol_sha256"],
        },
        "public_freeze": freeze,
        "frame_algebra": algebra,
        "audit_prime": AUDIT_PRIME,
        "row_count": len(rebuilt_rows),
        "third_prime_nullity_two_count": sum(
            row["audit_nullity"] == 2 for row in rebuilt_rows
        ),
        "row_rebuilds": rebuilt_rows,
        "positive_control_rebuilds": control_rows,
        "errors": errors,
    }
    return {
        "experiment_id": "B9-R197-independent-audit",
        "method": METHOD,
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "status": "pass" if not errors else "fail",
        "audit_prime": AUDIT_PRIME,
        "row_count": len(rebuilt_rows),
        "third_prime_nullity_two_count": core[
            "third_prime_nullity_two_count"
        ],
        "positive_control_nullities": [
            row["audit_nullity"] for row in control_rows
        ],
        "evidence_integrity_complete": not errors,
        "error_count": len(errors),
        "errors": errors,
        "source_result": core["source_result"],
        "public_freeze": freeze,
        "frame_algebra": algebra,
        "row_rebuilds": rebuilt_rows,
        "positive_control_rebuilds": control_rows,
        "payload_sha256": canonical_hash(core),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    audit = build_audit(root)
    output_path = args.json_output or root / AUDIT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            audit,
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
        + "\n"
    )
    print(
        json.dumps(
            {
                "status": audit["status"],
                "row_count": audit["row_count"],
                "third_prime_nullity_two_count": audit[
                    "third_prime_nullity_two_count"
                ],
                "positive_control_nullities": audit[
                    "positive_control_nullities"
                ],
                "error_count": audit["error_count"],
                "payload_sha256": audit["payload_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if audit["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
