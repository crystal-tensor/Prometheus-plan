#!/usr/bin/env python3
"""Independent preregistered audit for the B9 R200 finite atlas.

The audit uses a sparse symplectic-bit Pauli implementation and does not
import R193-R200 code.  It seals the expected projective catalog and grid
before reading the source result.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
from collections import defaultdict
from fractions import Fraction
from functools import cache
from pathlib import Path
from typing import Any, Iterable


EXPERIMENT_ID = "B9-R200-independent-projective-atlas-audit"
METHOD = "b9_r200_independent_symplectic_projective_atlas_audit_v1"
VERSION = "0.1.0"
SOURCE_RESULT = Path("results/B9_R200_bloch_atlas_stress_v1.json")
AUDIT_RESULT = Path("results/B9_R200_independent_audit_v1.json")
SEAL_RESULT = Path("results/B9_R200_independent_audit_seal_v0.json")
EXPECTED_CONTRACT_SHA256 = "a1208296eeaf56ed7bf51ed740b51931b7e1067cdb53d2e5e6e0d931aca356c0"
EXPECTED_ATLAS_SHA256 = (
    "b168b38442f85cd7a485e6e1ea2332fab1fa994e7c13956c405384e31f59cd47"
)
EXPECTED_PROJECTIVE_SHA256 = (
    "f64e2e63f922d691bdeef5fdf58b2e90207afe3b775d55dafc713e19b7705a2f"
)
FROZEN_COUPLINGS = (Fraction(109, 128), Fraction(113, 128))
GRID_SIZES = (6, 8, 10)
AUDIT_PRIMES = (1_000_037, 1_000_081)
ATLAS_BOUND = 2
I, X, Y, Z = 0, 1, 2, 3
PauliKey = tuple[int, int]
Operator = dict[PauliKey, int]
Axis = dict[int, Fraction]
FORBIDDEN_IMPORT_PREFIXES = tuple(f"b9_r{index}" for index in range(193, 201))
FORBIDDEN_IMPORT_MODULES = {"importlib", "runpy", "pickle", "marshal", "socket", "subprocess"}
FORBIDDEN_CALLS = {"exec", "eval", "compile", "__import__"}
SOURCE_FIELDS_CONSUMED_FOR_REBUILD: tuple[str, ...] = ()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def lcm(values: Iterable[int]) -> int:
    result = 1
    for value in values:
        result = math.lcm(result, value)
    return result


def code_key(code: int, site: int) -> PauliKey:
    if code == X:
        return 1 << site, 0
    if code == Y:
        return 1 << site, 1 << site
    if code == Z:
        return 0, 1 << site
    return 0, 0


def local_code(key: PauliKey, site: int) -> int:
    x_bit = (key[0] >> site) & 1
    z_bit = (key[1] >> site) & 1
    return Y if x_bit and z_bit else X if x_bit else Z if z_bit else I


def key_word(key: PauliKey, n: int) -> str:
    return "".join("IXYZ"[local_code(key, site)] for site in range(n))


def pauli_product(left: PauliKey, right: PauliKey) -> tuple[int, PauliKey]:
    output = left[0] ^ right[0], left[1] ^ right[1]
    exponent = (
        (left[0] & left[1]).bit_count()
        + (right[0] & right[1]).bit_count()
        + 2 * (left[1] & right[0]).bit_count()
        - (output[0] & output[1]).bit_count()
    ) % 4
    return exponent, output


def primitive(value: dict[PauliKey, Fraction], n: int) -> Operator:
    clean = {key: Fraction(coefficient) for key, coefficient in value.items() if coefficient}
    if not clean:
        return {}
    denominator = lcm(coefficient.denominator for coefficient in clean.values())
    integers = {key: int(coefficient * denominator) for key, coefficient in clean.items()}
    divisor = 0
    for coefficient in integers.values():
        divisor = math.gcd(divisor, abs(coefficient))
    integers = {key: coefficient // divisor for key, coefficient in integers.items() if coefficient}
    first = min(integers, key=lambda key: key_word(key, n))
    if integers[first] < 0:
        integers = {key: -coefficient for key, coefficient in integers.items()}
    return dict(sorted(integers.items(), key=lambda item: key_word(item[0], n)))


def axis_from_vector(values: tuple[Fraction, Fraction, Fraction]) -> Axis:
    return {code: value for code, value in zip((X, Y, Z), values) if value}


def north_frame(a: int, b: int, c: int) -> dict[str, Axis]:
    denominator = a * a + b * b + c * c
    return {
        "P": axis_from_vector((Fraction(2 * a * c, denominator), Fraction(2 * b * c, denominator), Fraction(c * c - a * a - b * b, denominator))),
        "Q": axis_from_vector((Fraction(c * c - a * a + b * b, denominator), Fraction(-2 * a * b, denominator), Fraction(-2 * a * c, denominator))),
        "R": axis_from_vector((Fraction(-2 * a * b, denominator), Fraction(c * c + a * a - b * b, denominator), Fraction(-2 * b * c, denominator))),
    }


def negate_axis(axis: Axis) -> Axis:
    return {code: -value for code, value in axis.items()}


def frame(chart: str, a: int, b: int, c: int) -> dict[str, Axis]:
    value = north_frame(a, b, c)
    if chart == "north":
        return value
    return {"P": negate_axis(value["P"]), "Q": value["Q"], "R": negate_axis(value["R"])}


def vector(axis: Axis) -> tuple[Fraction, Fraction, Fraction]:
    return tuple(axis.get(code, Fraction(0)) for code in (X, Y, Z))  # type: ignore[return-value]


def serialize_axis(axis: Axis) -> dict[str, str]:
    return {"XYZ"[code - 1]: fraction_text(value) for code, value in sorted(axis.items())}


def projective_key(axis: Axis) -> tuple[Fraction, Fraction, Fraction]:
    point = vector(axis)
    opposite = tuple(-value for value in point)
    return min(point, opposite)


def primitive_parameters() -> list[tuple[int, int, int]]:
    rows = []
    for c in range(1, ATLAS_BOUND + 1):
        for a in range(-ATLAS_BOUND, ATLAS_BOUND + 1):
            for b in range(-ATLAS_BOUND, ATLAS_BOUND + 1):
                if math.gcd(math.gcd(abs(a), abs(b)), c) == 1:
                    rows.append((a, b, c))
    return rows


def atlas_catalog() -> list[dict[str, Any]]:
    rows = []
    triples = primitive_parameters()
    for chart in ("north", "south"):
        prefix = chart[0]
        for index, (a, b, c) in enumerate(triples):
            value = frame(chart, a, b, c)
            rows.append({
                "frame_id": f"{prefix}_{index:03d}",
                "chart": chart,
                "parameters": {"a": a, "b": b, "c": c},
                "axes": {label: serialize_axis(value[label]) for label in ("P", "Q", "R")},
            })
    return rows


def entry_frame(entry: dict[str, Any]) -> dict[str, Axis]:
    params = entry["parameters"]
    return frame(entry["chart"], params["a"], params["b"], params["c"])


def projective_catalog(catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Fraction, Fraction, Fraction], list[dict[str, Any]]] = defaultdict(list)
    for entry in catalog:
        groups[projective_key(entry_frame(entry)["P"])].append(entry)
    rows = []
    for index, (key, entries) in enumerate(sorted(groups.items())):
        representative = min(entries, key=lambda item: item["frame_id"])
        rows.append({
            **representative,
            "projective_axis_id": f"rp2_{index:03d}",
            "projective_axis": [fraction_text(value) for value in key],
            "gauge_equivalent_frame_ids": sorted(item["frame_id"] for item in entries),
        })
    return rows


def expand_axes(n: int, site_axes: dict[int, Axis], scale: int = 1) -> Operator:
    partial: dict[PauliKey, Fraction] = {(0, 0): Fraction(scale)}
    for site in sorted(site_axes):
        updated: dict[PauliKey, Fraction] = {}
        for key, coefficient in partial.items():
            for code, local_coefficient in site_axes[site].items():
                local = code_key(code, site)
                output = key[0] | local[0], key[1] | local[1]
                updated[output] = updated.get(output, Fraction(0)) + coefficient * local_coefficient
        partial = updated
    return primitive(partial, n)


def gamma(n: int, value: dict[str, Axis], site: int, endpoint: str) -> Operator:
    axes = {index: value["P"] for index in range(site)}
    axes[site] = value[endpoint]
    return expand_axes(n, axes)


def bilinear(n: int, value: dict[str, Axis], left_site: int, left_endpoint: str, right_site: int, right_endpoint: str) -> Operator:
    if left_site == right_site:
        return expand_axes(n, {left_site: value["P"]}, scale=-1)
    axes: dict[int, Axis] = {}
    sign = 1
    if left_endpoint == "Q":
        axes[left_site] = value["R"]
    else:
        axes[left_site] = value["Q"]
        sign = -1
    for site in range(left_site + 1, right_site):
        axes[site] = value["P"]
    axes[right_site] = value[right_endpoint]
    return expand_axes(n, axes, scale=sign)


@cache
def pool(n: int, chart: str, a: int, b: int, c: int) -> tuple[tuple[str, Operator], ...]:
    value = frame(chart, a, b, c)
    labels = [(site, endpoint) for site in range(n) for endpoint in ("Q", "R")]
    entries = [(f"gamma:{site}:{endpoint}", gamma(n, value, site, endpoint)) for site, endpoint in labels]
    for left_index, (left_site, left_endpoint) in enumerate(labels):
        for right_site, right_endpoint in labels[left_index + 1:]:
            entries.append((
                f"bilinear:{left_site}:{left_endpoint}:{right_site}:{right_endpoint}",
                bilinear(n, value, left_site, left_endpoint, right_site, right_endpoint),
            ))
    entries.append(("parity", expand_axes(n, {site: value["P"] for site in range(n)})))
    return tuple(entries)


def hamiltonian(n: int, coupling: Fraction) -> Operator:
    terms: dict[PauliKey, Fraction] = {}
    for site in range(n):
        terms[code_key(X, site)] = Fraction(-1)
        terms[code_key(Z, site)] = Fraction(3, 4)
    for site in range(n - 1):
        key = (0, (1 << site) | (1 << (site + 1)))
        terms[key] = terms.get(key, Fraction(0)) + coupling
    return primitive(terms, n)


def anticommutes(left: PauliKey, right: PauliKey) -> bool:
    return ((left[0] & right[1]).bit_count() + (left[1] & right[0]).bit_count()) % 2 == 1


def commutator(h_value: Operator, candidate: Operator, n: int) -> Operator:
    output: dict[PauliKey, Fraction] = {}
    for h_key, h_coefficient in h_value.items():
        for candidate_key, candidate_coefficient in candidate.items():
            if not anticommutes(h_key, candidate_key):
                continue
            exponent, output_key = pauli_product(h_key, candidate_key)
            sign = 1 if exponent == 1 else -1
            output[output_key] = output.get(output_key, Fraction(0)) + h_coefficient * candidate_coefficient * sign
    return primitive(output, n)


def sparse_rank(columns: list[dict[int, int]], prime: int) -> int:
    pivots: dict[int, dict[int, int]] = {}
    for column in columns:
        value = {row: coefficient % prime for row, coefficient in column.items() if coefficient % prime}
        while value:
            pivot = min(value)
            if pivot not in pivots:
                inverse = pow(value[pivot], prime - 2, prime)
                pivots[pivot] = {row: coefficient * inverse % prime for row, coefficient in value.items() if coefficient * inverse % prime}
                break
            factor = value[pivot]
            for row, coefficient in pivots[pivot].items():
                updated = (value.get(row, 0) - factor * coefficient) % prime
                if updated:
                    value[row] = updated
                else:
                    value.pop(row, None)
    return len(pivots)


def operator_rank(operators: list[Operator], n: int, prime: int) -> int:
    words = sorted({key_word(key, n) for operator in operators for key in operator})
    index = {word: row for row, word in enumerate(words)}
    columns = [{index[key_word(key, n)]: coefficient for key, coefficient in operator.items()} for operator in operators]
    return sparse_rank(columns, prime)


def rebuild_row(entry: dict[str, Any], coupling: Fraction, n: int) -> dict[str, Any]:
    params = entry["parameters"]
    entries = list(pool(n, entry["chart"], params["a"], params["b"], params["c"]))
    labels = [label for label, _ in entries]
    operators = [operator for _, operator in entries]
    columns_raw = [commutator(hamiltonian(n, coupling), operator, n) for operator in operators]
    output_words = sorted({key_word(key, n) for column in columns_raw for key in column})
    output_index = {word: index for index, word in enumerate(output_words)}
    columns = [{output_index[key_word(key, n)]: coefficient for key, coefficient in column.items()} for column in columns_raw]
    operator_payload = {
        "labels": labels,
        "operators": [[(key_word(key, n), coefficient) for key, coefficient in operator.items()] for operator in operators],
    }
    matrix_payload = {
        "labels": labels,
        "output_basis": output_words,
        "triples": [(output_words[row], column_index, coefficient) for column_index, column in enumerate(columns) for row, coefficient in sorted(column.items())],
    }
    column_count = len(columns)
    operator_ranks = {str(prime): operator_rank(operators, n, prime) for prime in AUDIT_PRIMES}
    ranks = {str(prime): sparse_rank(columns, prime) for prime in AUDIT_PRIMES}
    return {
        "coupling": fraction_text(coupling),
        "n": n,
        "projective_axis_id": entry["projective_axis_id"],
        "candidate_column_count": column_count,
        "operator_basis_sha256": canonical_hash(operator_payload),
        "commutator_matrix_sha256": canonical_hash(matrix_payload),
        "operator_basis_modular_ranks": operator_ranks,
        "modular_ranks": ranks,
        "full_rank": all(rank == column_count for rank in operator_ranks.values()) and all(rank == column_count for rank in ranks.values()),
    }


def static_anti_circularity() -> dict[str, Any]:
    source = Path(__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports: list[str] = []
    calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            calls.append(node.func.id)
    forbidden_imports = sorted(name for name in imports if name in FORBIDDEN_IMPORT_MODULES or name.startswith(FORBIDDEN_IMPORT_PREFIXES))
    forbidden_calls = sorted(name for name in calls if name in FORBIDDEN_CALLS)
    return {
        "checked": not forbidden_imports and not forbidden_calls,
        "forbidden_imports": forbidden_imports,
        "forbidden_calls": forbidden_calls,
        "source_fields_consumed_for_rebuild": list(SOURCE_FIELDS_CONSUMED_FOR_REBUILD),
    }


def seal_summary() -> dict[str, Any]:
    catalog = atlas_catalog()
    projective = projective_catalog(catalog)
    keys = [
        [fraction_text(coupling), n, entry["projective_axis_id"]]
        for coupling in FROZEN_COUPLINGS
        for n in GRID_SIZES
        for entry in projective
    ]
    return {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "mode": "pre_source_seal",
        "atlas_row_count": len(catalog),
        "atlas_sha256": canonical_hash(catalog),
        "projective_axis_count": len(projective),
        "projective_catalog_sha256": canonical_hash(projective),
        "expected_grid_row_count": len(keys),
        "expected_grid_keys_sha256": canonical_hash(keys),
        "audit_primes": list(AUDIT_PRIMES),
        "anti_circularity": static_anti_circularity(),
        "source_result_read": False,
    }


def audit_source(source_path: Path) -> dict[str, Any]:
    seal = seal_summary()
    catalog = atlas_catalog()
    projective = projective_catalog(catalog)
    expected = {
        (fraction_text(coupling), n, entry["projective_axis_id"]): entry
        for coupling in FROZEN_COUPLINGS
        for n in GRID_SIZES
        for entry in projective
    }
    source = json.loads(source_path.read_text(encoding="utf-8"))
    source_rows = {
        (row["coupling"], row["n"], row["projective_axis_id"]): row
        for row in source.get("grid_rows", [])
    }
    missing = sorted(set(expected) - set(source_rows))
    extra = sorted(set(source_rows) - set(expected))
    duplicate_count = len(source.get("grid_rows", [])) - len(source_rows)
    rebuilt_rows = []
    errors = []
    for key in sorted(expected):
        if key not in source_rows:
            continue
        coupling = Fraction(key[0])
        rebuilt = rebuild_row(expected[key], coupling, key[1])
        observed = source_rows[key]
        rebuilt_rows.append(rebuilt)
        for field in ("candidate_column_count", "operator_basis_sha256", "commutator_matrix_sha256"):
            if rebuilt[field] != observed.get(field):
                errors.append(f"{key}: {field} mismatch")
        if not rebuilt["full_rank"]:
            errors.append(f"{key}: audit-prime rank failure")
    payload_copy = dict(source)
    recorded_payload = payload_copy.pop("payload_sha256", None)
    payload_verified = canonical_hash(payload_copy) == recorded_payload
    if not payload_verified:
        errors.append("source payload hash mismatch after JSON round trip")
    if missing or extra or duplicate_count:
        errors.append("source grid key set mismatch")
    if seal["atlas_sha256"] != EXPECTED_ATLAS_SHA256:
        errors.append("atlas digest mismatch")
    if seal["projective_catalog_sha256"] != EXPECTED_PROJECTIVE_SHA256:
        errors.append("projective catalog digest mismatch")
    if not seal["anti_circularity"]["checked"]:
        errors.append("anti-circularity scan failed")
    return {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "status": "pass" if not errors else "fail",
        "pre_source_seal": seal,
        "source_result": {
            "path": str(source_path),
            "payload_sha256": recorded_payload,
            "payload_round_trip_verified": payload_verified,
        },
        "grid_shape": {
            "missing_count": len(missing),
            "extra_count": len(extra),
            "duplicate_count": duplicate_count,
        },
        "rebuilt_row_count": len(rebuilt_rows),
        "third_and_fourth_prime_full_rank_grid_count": sum(row["full_rank"] for row in rebuilt_rows),
        "rebuilt_rows": rebuilt_rows,
        "error_count": len(errors),
        "errors": errors,
        "source_fields_consumed_for_rebuild": list(SOURCE_FIELDS_CONSUMED_FOR_REBUILD),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--seal-summary", action="store_true")
    modes.add_argument("--audit-result", action="store_true")
    parser.add_argument("--source", type=Path, default=SOURCE_RESULT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = seal_summary() if args.seal_summary else audit_source(args.source)
    output = args.output or (SEAL_RESULT if args.seal_summary else AUDIT_RESULT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result.get("status", "pass") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
