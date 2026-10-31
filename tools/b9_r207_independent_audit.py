#!/usr/bin/env python3
"""Independently audit R207 quadratic-field maximal-minor certificates."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any


METHOD = "b9_r207_independent_regular_representation_audit_v1"
VERSION = "0.1.0"
DEFAULT_SOURCE = Path("results/B9_R207_off_slice_component_rank_v0.json")


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_hash_valid(result: dict[str, Any]) -> bool:
    payload = dict(result)
    expected = payload.pop("payload_sha256", None)
    return expected is not None and canonical_hash(payload) == expected


def fraction_mod(raw: str, prime: int) -> int:
    value = Fraction(raw)
    return (
        value.numerator
        * pow(value.denominator % prime, prime - 2, prime)
        % prime
    )


def regular_matrix(square: list, prime: int) -> list[list[int]]:
    size = len(square)
    if size == 0 or any(len(row) != size for row in square):
        raise ValueError("selected payload is not square")
    output = [[0] * (2 * size) for _ in range(2 * size)]
    for row_index, row in enumerate(square):
        for column_index, payload in enumerate(row):
            if not isinstance(payload, list) or len(payload) != 2:
                raise ValueError("quadratic entry must contain x and y")
            x = fraction_mod(payload[0], prime)
            y = fraction_mod(payload[1], prime)
            output[2 * row_index][2 * column_index] = x
            output[2 * row_index][2 * column_index + 1] = -407 * y % prime
            output[2 * row_index + 1][2 * column_index] = y
            output[2 * row_index + 1][2 * column_index + 1] = x
    return output


def determinant_mod(matrix: list[list[int]], prime: int) -> int:
    rows = [list(row) for row in matrix]
    determinant = 1
    for column in range(len(rows)):
        pivot = next(
            (
                row_index
                for row_index in range(column, len(rows))
                if rows[row_index][column] % prime
            ),
            None,
        )
        if pivot is None:
            return 0
        if pivot != column:
            rows[column], rows[pivot] = rows[pivot], rows[column]
            determinant = -determinant % prime
        pivot_value = rows[column][column] % prime
        determinant = determinant * pivot_value % prime
        inverse = pow(pivot_value, prime - 2, prime)
        for row_index in range(column + 1, len(rows)):
            if not rows[row_index][column] % prime:
                continue
            factor = rows[row_index][column] * inverse % prime
            for entry_index in range(column, len(rows)):
                rows[row_index][entry_index] = (
                    rows[row_index][entry_index]
                    - factor * rows[column][entry_index]
                ) % prime
    return determinant


def audit_square(
    square: list,
    prime_replays: list[dict[str, Any]],
    expected_hash: str,
) -> dict[str, Any]:
    if canonical_hash(square) != expected_hash:
        raise ValueError("selected submatrix hash mismatch")
    rows = []
    for replay in prime_replays:
        prime = int(replay["prime"])
        x, y = (int(value) for value in replay["determinant_residue_x_y"])
        expected_norm = (x * x + 407 * y * y) % prime
        regular_determinant = determinant_mod(regular_matrix(square, prime), prime)
        rows.append(
            {
                "prime": prime,
                "main_determinant_residue_x_y": [x, y],
                "expected_norm_residue": expected_norm,
                "regular_representation_determinant_residue": regular_determinant,
                "regular_determinant_sha256": hashlib.sha256(
                    str(regular_determinant).encode()
                ).hexdigest(),
                "norm_match": regular_determinant == expected_norm,
                "independent_nonzero": regular_determinant != 0,
            }
        )
    return {
        "selected_submatrix_sha256": expected_hash,
        "regular_representation_shape": [2 * len(square), 2 * len(square)],
        "prime_replays": rows,
        "checked": all(
            row["norm_match"] and row["independent_nonzero"] for row in rows
        ),
    }


def build_result(root: Path, source_path: Path) -> dict[str, Any]:
    source = json.loads(source_path.read_text())
    if (
        not payload_hash_valid(source)
        or source.get("method")
        != "b9_r207_off_slice_component_full_rank_classification_v1"
        or source.get("checked") is not True
        or source.get("all_four_candidate_points_full_rank_in_both_representations")
        is not True
        or source.get("one_existing_selected_minor_excludes_both_b_sign_branches")
        is not True
    ):
        raise ValueError("R207 source artifact is not accepted")
    certificate_rows = []
    for row in source["representation_certificates"]:
        audit = audit_square(
            row["exact_selected_submatrix"],
            row["prime_replays"],
            row["exact_selected_submatrix_sha256"],
        )
        certificate_rows.append(
            {
                "representation": row["representation"],
                "b_sign": row["b_sign"],
                **audit,
            }
        )
    cross_rows = []
    for row in source["cross_branch_minor_replays"]:
        audit = audit_square(
            row["exact_target_submatrix"],
            row["prime_replays"],
            row["target_square_sha256"],
        )
        cross_rows.append(
            {
                "representation": row["representation"],
                "source_b_sign": row["source_b_sign"],
                "target_b_sign": row["target_b_sign"],
                **audit,
            }
        )
    checked = bool(
        len(certificate_rows) == 4
        and len(cross_rows) == 4
        and all(row["checked"] for row in certificate_rows)
        and all(row["checked"] for row in cross_rows)
    )
    stable = {
        "source_result_sha256": sha256_file(source_path),
        "certificate_rows": certificate_rows,
        "cross_branch_rows": cross_rows,
    }
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R207_quadratic_determinant_arithmetic_audit_only",
        "source_result": str(source_path.relative_to(root)),
        "source_result_sha256": stable["source_result_sha256"],
        "source_payload_sha256": source["payload_sha256"],
        "arithmetic_route": (
            "74x74_GF(p)_regular_representation_without_importing_R207_field_code"
        ),
        "quadratic_relation": "s^2=-407",
        "norm_formula": "Norm(x+y*s)=x^2+407*y^2",
        "certificate_rows": certificate_rows,
        "cross_branch_rows": cross_rows,
        "all_main_maximal_minors_independently_nonzero": all(
            row["checked"] for row in certificate_rows
        ),
        "all_cross_branch_maximal_minors_independently_nonzero": all(
            row["checked"] for row in cross_rows
        ),
        "main_module_imported": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "claim_boundary": (
            "This audit independently checks the committed quadratic-field determinant "
            "payloads through regular representations. It does not independently rebuild "
            "the physical matrices or prove a characteristic-zero unit ideal."
        ),
        "python_version": platform.python_version(),
        "stable_audit_payload": stable,
        "stable_audit_sha256": canonical_hash(stable),
        "checked": checked,
    }
    result["payload_sha256"] = canonical_hash(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = args.source if args.source.is_absolute() else root / args.source
    output = args.output if args.output.is_absolute() else root / args.output
    result = build_result(root, source)
    output.write_text(
        json.dumps(result, indent=2 if args.pretty else None, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "checked": result["checked"],
                "main_minor_count": len(result["certificate_rows"]),
                "cross_branch_minor_count": len(result["cross_branch_rows"]),
                "new_credit_delta": result["new_credit_delta"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
