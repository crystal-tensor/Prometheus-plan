#!/usr/bin/env python3
"""Compute frozen R201 engineering minors through the Singular CLI."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

import sympy as sp

import b9_r201_projective_patch_certificate as r201


VERSION = "0.2.0"
METHOD = "b9_r201_singular_exact_minor_bridge_v2"
ENGINEERING_COUPLING = Fraction(13, 32)
BEGIN_MARKER = "R201_POLY_BEGIN"
END_MARKER = "R201_POLY_END"


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def singular_expression(expression: sp.Expr) -> str:
    return sp.sstr(sp.expand(expression)).replace("**", "^")


def engineering_row_sets() -> tuple[list[list[sp.Expr]], list[dict[str, Any]]]:
    labels, columns, output_words, matrix_hash = r201.symbolic_matrix(
        4, ENGINEERING_COUPLING
    )
    seen: set[str] = set()
    matrices: list[list[sp.Expr]] = []
    records = []
    for anchor in r201.MAIN_MINOR_ANCHORS:
        rows = r201.select_rows_at_anchor(
            columns, output_words, anchor, r201.BASIS_SELECTION_PRIME
        )
        row_hash = canonical_hash(rows)
        if len(rows) != len(columns) or row_hash in seen:
            continue
        seen.add(row_hash)
        entries = [
            columns[column]
            .get(word, sp.Poly(0, *r201.VARS, domain=sp.ZZ))
            .as_expr()
            for word in rows
            for column in range(len(columns))
        ]
        matrices.append(entries)
        records.append(
            {
                "anchor": list(anchor),
                "row_words": rows,
                "row_words_sha256": row_hash,
                "matrix_sha256": matrix_hash,
                "candidate_labels_sha256": canonical_hash(labels),
                "dimension": len(columns),
            }
        )
        if len(matrices) == r201.MAX_SELECTED_MINORS:
            break
    return matrices, records


def singular_script(entries: list[sp.Expr], dimension: int, prime: int) -> str:
    ring_characteristic = str(prime) if prime else "0"
    lines = [
        f"ring r={ring_characteristic},(a,b,c),dp;",
        f"matrix M[{dimension}][{dimension}];",
    ]
    for offset, expression in enumerate(entries):
        if expression == 0:
            continue
        row = offset // dimension + 1
        column = offset % dimension + 1
        lines.append(f"M[{row},{column}]={singular_expression(expression)};")
    lines.extend(
        [
            "poly f=det(M);",
            f'print("{BEGIN_MARKER}");',
            "print(string(f));",
            f'print("{END_MARKER}");',
            "quit;",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_singular_term(term: str) -> tuple[tuple[int, int, int], int]:
    match = re.fullmatch(
        r"([+-])(\d*)(a\d*)?(b\d*)?(c\d*)?",
        term,
    )
    if match is None:
        raise ValueError(f"unsupported Singular polynomial term: {term[:120]}")
    sign, coefficient_text, *variable_texts = match.groups()
    if not coefficient_text and not any(variable_texts):
        raise ValueError("Singular polynomial term has no coefficient or variable")
    coefficient = int(coefficient_text or "1")
    if sign == "-":
        coefficient = -coefficient
    exponents = tuple(
        0 if variable_text is None else int(variable_text[1:] or "1")
        for variable_text in variable_texts
    )
    return exponents, coefficient


def parse_polynomial(stdout: str, prime: int) -> sp.Poly:
    if BEGIN_MARKER not in stdout or END_MARKER not in stdout:
        raise RuntimeError("Singular output markers missing")
    body = stdout.split(BEGIN_MARKER, 1)[1].split(END_MARKER, 1)[0]
    compact = re.sub(r"\s+", "", body)
    if not compact:
        return sp.Poly(0, *r201.VARS, modulus=prime) if prime else sp.Poly(0, *r201.VARS, domain=sp.ZZ)
    if compact[0] not in "+-":
        compact = "+" + compact
    terms: dict[tuple[int, int, int], int] = {}
    for term in re.findall(r"[+-][^+-]+", compact):
        monomial, coefficient = parse_singular_term(term)
        terms[monomial] = terms.get(monomial, 0) + coefficient
    if prime:
        terms = {
            monomial: coefficient % prime
            for monomial, coefficient in terms.items()
            if coefficient % prime
        }
        return sp.Poly.from_dict(terms, r201.VARS, modulus=prime)
    polynomial = sp.Poly.from_dict(terms, r201.VARS, domain=sp.ZZ)
    return r201.primitive_polynomial(polynomial)


def polynomial_payload(polynomial: sp.Poly, prime: int) -> list[list[Any]]:
    if not prime:
        return r201.poly_payload(polynomial)
    return [
        [list(monomial), str(int(coefficient) % prime)]
        for monomial, coefficient in polynomial.terms()
    ]


def compute_minor(index: int, timeout_seconds: int, prime: int) -> dict[str, Any]:
    if prime and (prime < 2 or not sp.isprime(prime)):
        raise ValueError("--prime must be zero or a positive prime")
    singular = shutil.which("Singular")
    if singular is None:
        raise RuntimeError("Singular executable not found")
    matrices, records = engineering_row_sets()
    if not 0 <= index < len(matrices):
        raise ValueError(f"minor index {index} outside 0..{len(matrices) - 1}")
    record = records[index]
    script = singular_script(matrices[index], record["dimension"], prime)
    started = time.monotonic()
    completed = subprocess.run(
        [singular, "-q"],
        input=script,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
        check=False,
    )
    elapsed = time.monotonic() - started
    if completed.returncode != 0:
        raise RuntimeError(
            f"Singular failed with {completed.returncode}: {completed.stderr[-4000:]}"
        )
    polynomial = parse_polynomial(completed.stdout, prime)
    terms = polynomial_payload(polynomial, prime)
    coefficient_domain = f"GF({prime})" if prime else "QQ/ZZ primitive"
    return {
        "method": METHOD,
        "version": VERSION,
        "mode": "public_engineering_coupling_only",
        "coupling": "13/32",
        "coefficient_domain": coefficient_domain,
        "characteristic": prime,
        "n": 4,
        "minor_index": index,
        **record,
        "singular_path": singular,
        "singular_version": subprocess.check_output(
            [singular, "--version"], text=True
        ).splitlines()[0],
        "bridge_tool_sha256": sha256_file(Path(__file__).resolve()),
        "singular_input_sha256": hashlib.sha256(script.encode()).hexdigest(),
        "total_degree": polynomial.total_degree(),
        "term_count": len(terms),
        "canonical_terms": terms,
        "canonical_terms_sha256": canonical_hash(terms),
        "elapsed_seconds": round(elapsed, 6),
        "frozen_holdouts_executed": False,
        "integer_engineering_certificate_verified": False,
        "modular_bridge_validation_only": bool(prime),
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "checked": polynomial.total_degree() == 184 and bool(terms),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minor-index", type=int, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument(
        "--prime",
        type=int,
        default=0,
        help="compute exactly in GF(prime); zero requests characteristic zero",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    result = compute_minor(args.minor_index, args.timeout_seconds, args.prime)
    output = args.output if args.output.is_absolute() else root / args.output
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "minor_index": result["minor_index"],
                "coefficient_domain": result["coefficient_domain"],
                "row_words_sha256": result["row_words_sha256"],
                "total_degree": result["total_degree"],
                "term_count": result["term_count"],
                "elapsed_seconds": result["elapsed_seconds"],
                "checked": result["checked"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
