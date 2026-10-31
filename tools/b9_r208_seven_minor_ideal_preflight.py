#!/usr/bin/env python3
"""Classify the R208 seven-minor saturated ideal over two finite fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import b9_r202_modular_ideal_preflight as r202
import b9_r206_six_minor_ideal_preflight as r206


METHOD = "b9_r208_seven_minor_modular_saturated_ideal_preflight_v1"
VERSION = "0.1.0"
PRIMES = (1_000_003, 536_870_723)
R204_RESULTS = {
    1_000_003: Path("results/B9_R204_added_minor_mod1000003_v0.json"),
    536_870_723: Path("results/B9_R204_added_minor_mod536870723_v0.json"),
}
R206_RESULTS = {
    1_000_003: Path("results/B9_R206_sixth_minor_mod1000003_v0.json"),
    536_870_723: Path("results/B9_R206_sixth_minor_mod536870723_v0.json"),
}
R208_RESULTS = {
    1_000_003: Path("results/B9_R208_seventh_minor_mod1000003_v0.json"),
    536_870_723: Path("results/B9_R208_seventh_minor_mod536870723_v0.json"),
}


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


def singular_script(
    quotients: list[list[list[Any]]], prime: int, algorithm: str
) -> str:
    lines = [f"ring r={prime},(u,a,b,c),dp;"]
    for index, terms in enumerate(quotients):
        lines.append(f"poly q{index}={r202.polynomial_text(terms, prime)};")
    saturation = "1-u*(a2+b2+c2)"
    r206.append_classification(
        lines, "unit_control", f"a,b,c,{saturation}", algorithm
    )
    lines.append("kill i;")
    r206.append_classification(
        lines, "nonunit_control", f"a,b,{saturation}", algorithm
    )
    lines.append("kill i;")
    r206.append_classification(
        lines,
        "seven_minor_engineering",
        f"q0,q1,q2,q3,q4,q5,q6,{saturation}",
        algorithm,
    )
    lines.append("kill i;")
    r206.append_classification(
        lines,
        "r207_four_point_chart",
        "169*a2+407,169*b2-576,subst(q6,c,1)",
        algorithm,
    )
    lines.extend(
        [
            "kill i;",
            "poly h=subst(q0,b,0);",
            "h=gcd(h,subst(q1,b,0));",
            "h=gcd(h,subst(q2,b,0));",
            "h=gcd(h,subst(q3,b,0));",
            "h=gcd(h,subst(q4,b,0));",
            "h=gcd(h,subst(q5,b,0));",
            "h=gcd(h,subst(q6,b,0));",
            "poly normalized_h=h/leadcoef(h);",
            f'print("{r206.BEGIN}slice");',
            "print(deg(normalized_h));",
            "print(size(normalized_h));",
            "print(string(normalized_h-1));",
            f'print("{r206.END}slice");',
            "quit;",
            "",
        ]
    )
    return "\n".join(lines)


def run_prime(
    singular: str,
    quotients: list[list[list[Any]]],
    prime: int,
    algorithm: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    script = singular_script(quotients, prime, algorithm)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            [singular, "-q"],
            input=script,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "prime": prime,
            "algorithm": algorithm,
            "timed_out": True,
            "elapsed_seconds": round(time.monotonic() - started, 6),
            "stdout_sha256": hashlib.sha256((exc.stdout or "").encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256((exc.stderr or "").encode()).hexdigest(),
            "checked": False,
        }
    elapsed = time.monotonic() - started
    row: dict[str, Any] = {
        "prime": prime,
        "algorithm": algorithm,
        "timed_out": False,
        "elapsed_seconds": round(elapsed, 6),
        "returncode": completed.returncode,
        "singular_input_sha256": hashlib.sha256(script.encode()).hexdigest(),
        "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
    }
    if completed.returncode != 0:
        row.update({"stderr_tail": completed.stderr[-2000:], "checked": False})
        return row
    try:
        unit_control = r206.parse_classification(completed.stdout, "unit_control")
        nonunit_control = r206.parse_classification(
            completed.stdout, "nonunit_control"
        )
        seven_minor = r206.parse_classification(
            completed.stdout, "seven_minor_engineering"
        )
        component = r206.parse_classification(
            completed.stdout, "r207_four_point_chart"
        )
        slice_row = r206.parse_slice(completed.stdout)
    except (ValueError, IndexError) as exc:
        row.update({"parse_error": str(exc), "checked": False})
        return row
    controls_checked = (
        unit_control["unit_ideal_detected"]
        and not nonunit_control["unit_ideal_detected"]
    )
    slice_checked = (
        slice_row["gcd_total_degree"] == 0
        and slice_row["gcd_term_count"] == 1
        and slice_row["normalized_gcd_is_one"]
    )
    row.update(
        {
            "unit_control": unit_control,
            "nonunit_control": nonunit_control,
            "seven_minor_engineering": seven_minor,
            "r207_four_point_chart": component,
            "slice": slice_row,
            "controls_checked": controls_checked,
            "slice_checked": slice_checked,
            "checked": controls_checked and slice_checked,
        }
    )
    return row


def validate_bridge(
    root: Path,
    prime: int,
    bridge_hash: str,
    r207_row_hash: str,
) -> tuple[dict[str, Any], str]:
    path = root / R208_RESULTS[prime]
    result = json.loads(path.read_text())
    support = [row[0] for row in result.get("quotient_canonical_terms", [])]
    if (
        not payload_hash_valid(result)
        or result.get("method")
        != "b9_r208_r207_cross_branch_seventh_minor_bridge_v1"
        or result.get("version") != VERSION
        or result.get("characteristic") != prime
        or result.get("new_minor_index") != 6
        or result.get("bridge_tool_sha256") != bridge_hash
        or result.get("row_words_sha256") != r207_row_hash
        or result.get("D_exponent") != 44
        or result.get("determinant_total_degree") != 184
        or result.get("determinant_term_count") != 5309
        or result.get("quotient_total_degree") != 96
        or result.get("quotient_term_count") != 821
        or result.get("exact_D44_division_verified") is not True
        or result.get("factorization_validated") is not True
        or result.get("scaled_recomposition_validated") is not True
        or len(result.get("point_replays", [])) != 4
        or not all(
            row.get("determinant_replay_match") is True
            and row.get("D_power_recomposition_match") is True
            for row in result.get("point_replays", [])
        )
        or result.get("frozen_holdouts_executed") is not False
        or result.get("scientific_promotion_accepted") is not False
        or result.get("new_credit_delta") != 0
        or result.get("checked") is not True
    ):
        raise ValueError(f"R208 seventh-minor artifact failed validation at {prime}")
    return result, canonical_hash(support)


def build_result(
    root: Path, algorithm: str, timeout_seconds: int
) -> dict[str, Any]:
    singular = shutil.which("Singular")
    if singular is None:
        raise RuntimeError("Singular executable not found")
    source_paths = {
        "r201": root / "results/B9_R201_integer_reconstruction_v0.json",
        "r206_preflight": root / "results/B9_R206_six_minor_ideal_preflight_v0.json",
        "r207": root / "results/B9_R207_off_slice_component_rank_v0.json",
        "bridge_tool": root / "tools/b9_r208_seventh_minor_bridge.py",
        "r206_preflight_tool": root / "tools/b9_r206_six_minor_ideal_preflight.py",
    }
    r201 = json.loads(source_paths["r201"].read_text())
    r206_preflight = json.loads(source_paths["r206_preflight"].read_text())
    r207 = json.loads(source_paths["r207"].read_text())
    if (
        r201.get("checked") is not True
        or len(r201.get("rows", [])) != 4
        or not payload_hash_valid(r206_preflight)
        or r206_preflight.get("checked") is not True
        or r206_preflight.get("expanded_minor_count") != 6
        or not payload_hash_valid(r207)
        or r207.get("checked") is not True
        or r207.get("one_existing_selected_minor_excludes_both_b_sign_branches")
        is not True
    ):
        raise ValueError("R201/R206/R207 source chain is not accepted")
    pauli_rows = [
        row
        for row in r207["representation_certificates"]
        if row.get("representation") == "independent_sparse_Pauli_word_matrix"
        and row.get("b_sign") == 1
    ]
    if len(pauli_rows) != 1:
        raise ValueError("R207 cross-branch Pauli row certificate is ambiguous")

    bridge_hash = sha256_file(source_paths["bridge_tool"])
    seventh: dict[int, dict[str, Any]] = {}
    support_hashes = []
    for prime in PRIMES:
        seventh[prime], support_hash = validate_bridge(
            root, prime, bridge_hash, pauli_rows[0]["selected_rows_sha256"]
        )
        support_hashes.append(support_hash)
    if len(set(support_hashes)) != 1:
        raise ValueError("R208 quotient monomial support differs across primes")

    old_quotients = [
        r202.primitive_quotient_terms(row) for row in r201["rows"]
    ]
    fifth = {
        prime: json.loads((root / R204_RESULTS[prime]).read_text()) for prime in PRIMES
    }
    sixth = {
        prime: json.loads((root / R206_RESULTS[prime]).read_text()) for prime in PRIMES
    }
    prime_rows = []
    for prime in PRIMES:
        quotients = [
            *old_quotients,
            fifth[prime]["quotient_canonical_terms"],
            sixth[prime]["quotient_canonical_terms"],
            seventh[prime]["quotient_canonical_terms"],
        ]
        prime_rows.append(
            run_prime(singular, quotients, prime, algorithm, timeout_seconds)
        )

    all_checked = all(row.get("checked") is True for row in prime_rows)
    unit_rows = [
        row
        for row in prime_rows
        if row.get("seven_minor_engineering", {}).get("unit_ideal_detected") is True
    ]
    nonunit_rows = [
        row
        for row in prime_rows
        if row.get("seven_minor_engineering", {}).get("unit_ideal_detected") is False
    ]
    component_unit_rows = [
        row
        for row in prime_rows
        if row.get("r207_four_point_chart", {}).get("unit_ideal_detected") is True
    ]
    stable = {
        "source_sha256": {
            label: sha256_file(path) for label, path in source_paths.items()
        },
        "fifth_minor_result_sha256": {
            str(prime): sha256_file(root / R204_RESULTS[prime]) for prime in PRIMES
        },
        "sixth_minor_result_sha256": {
            str(prime): sha256_file(root / R206_RESULTS[prime]) for prime in PRIMES
        },
        "seventh_minor_result_sha256": {
            str(prime): sha256_file(root / R208_RESULTS[prime]) for prime in PRIMES
        },
        "seventh_minor_support_sha256": support_hashes[0],
        "standard_basis_algorithm": algorithm,
        "prime_rows": [
            {
                "prime": row["prime"],
                "seven_minor_unit": row.get("seven_minor_engineering", {}).get(
                    "unit_ideal_detected"
                ),
                "seven_minor_basis_sha256": row.get(
                    "seven_minor_engineering", {}
                ).get("basis_summary_sha256"),
                "r207_component_unit": row.get(
                    "r207_four_point_chart", {}
                ).get("unit_ideal_detected"),
                "slice": row.get("slice"),
                "stdout_sha256": row.get("stdout_sha256"),
            }
            for row in prime_rows
        ],
    }
    result: dict[str, Any] = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R201_to_R208_seven_minor_modular_preflight_only",
        "coupling": "13/32",
        "n": 4,
        **{key: value for key, value in stable.items() if key != "prime_rows"},
        "old_minor_count": 6,
        "expanded_minor_count": 7,
        "new_determinant_total_degree": 184,
        "new_determinant_term_count": 5309,
        "new_quotient_total_degree": 96,
        "new_quotient_term_count": 821,
        "saturation_equation": "1-u*(a^2+b^2+c^2)",
        "r207_component_chart_equations": [
            "169*a^2+407",
            "169*b^2-576",
            "c-1",
        ],
        "coefficient_domain": "finite_fields_only",
        "monomial_order": "dp(u,a,b,c)",
        "standard_basis_algorithm": algorithm,
        "singular_path": singular,
        "singular_version": subprocess.check_output(
            [singular, "--version"], text=True
        ).splitlines()[0],
        "primes": list(PRIMES),
        "per_prime_timeout_seconds": timeout_seconds,
        "prime_rows": prime_rows,
        "classified_prime_count": sum(
            "seven_minor_engineering" in row for row in prime_rows
        ),
        "unit_ideal_prime_count": len(unit_rows),
        "nonunit_ideal_prime_count": len(nonunit_rows),
        "r207_component_excluded_prime_count": len(component_unit_rows),
        "all_classified_primes_detect_unit_ideal": len(unit_rows) == len(PRIMES),
        "all_classified_primes_detect_nonunit_ideal": len(nonunit_rows)
        == len(PRIMES),
        "r207_four_point_component_excluded_in_both_primes": len(
            component_unit_rows
        )
        == len(PRIMES),
        "preflight_conclusion": (
            "two_prime_unit_preflight_after_seventh_minor"
            if len(unit_rows) == len(PRIMES)
            else "two_prime_nonunit_after_seventh_minor"
            if len(nonunit_rows) == len(PRIMES)
            else "mixed_or_incomplete_modular_classification"
        ),
        "stable_classification_payload": stable,
        "stable_classification_sha256": canonical_hash(stable),
        "execution_complete": all(
            "seven_minor_engineering" in row for row in prime_rows
        ),
        "modular_preflight_checked": all_checked,
        "rational_nullstellensatz_certificate_verified": False,
        "characteristic_zero_rank_theorem_verified": False,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "claim_boundary": (
            "A two-prime finite-field saturated-ideal classification is a "
            "route-selection preflight. It is not a rational Nullstellensatz "
            "certificate, a characteristic-zero global rank theorem, a "
            "Quantum PCP result, or B9/B10 credit."
        ),
        "checked": all_checked,
    }
    result["payload_sha256"] = canonical_hash(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--algorithm", choices=("std", "slimgb"), default="slimgb")
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = build_result(root, args.algorithm, args.timeout_seconds)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "algorithm": result["standard_basis_algorithm"],
                "checked": result["checked"],
                "preflight_conclusion": result["preflight_conclusion"],
                "unit_ideal_prime_count": result["unit_ideal_prime_count"],
                "r207_component_excluded_prime_count": result[
                    "r207_component_excluded_prime_count"
                ],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
