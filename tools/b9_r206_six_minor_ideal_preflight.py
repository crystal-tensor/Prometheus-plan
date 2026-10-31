#!/usr/bin/env python3
"""Classify the R206 six-minor saturated ideal over two finite fields."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import b9_r202_modular_ideal_preflight as r202
import b9_r204_expanded_ideal_preflight as r204


METHOD = "b9_r206_six_minor_modular_saturated_ideal_preflight_v1"
VERSION = "0.1.0"
DEFAULT_PRIMES = (1_000_003, 536_870_723)
BEGIN = "__R206_BEGIN__"
END = "__R206_END__"
R204_RESULTS = {
    1_000_003: Path("results/B9_R204_added_minor_mod1000003_v0.json"),
    536_870_723: Path("results/B9_R204_added_minor_mod536870723_v0.json"),
}
R206_RESULTS = {
    1_000_003: Path("results/B9_R206_sixth_minor_mod1000003_v0.json"),
    536_870_723: Path("results/B9_R206_sixth_minor_mod536870723_v0.json"),
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


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor <= math.isqrt(value):
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def append_classification(
    lines: list[str], label: str, ideal_expression: str, algorithm: str
) -> None:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", label)
    lines.extend(
        [
            f"ideal I_{safe}={ideal_expression};",
            f"ideal G_{safe}={algorithm}(I_{safe});",
            f'print("{BEGIN}{safe}");',
            f"print(size(G_{safe}));",
            f"print(string(reduce(1,G_{safe})));",
            "int i;",
            f"for(i=1;i<=size(G_{safe});i++)"
            f'{{print(string(deg(G_{safe}[i]))+","+'
            f'string(size(G_{safe}[i])));}}',
            f'print("{END}{safe}");',
        ]
    )


def parse_classification(stdout: str, label: str) -> dict[str, Any]:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", label)
    begin = f"{BEGIN}{safe}"
    end = f"{END}{safe}"
    if begin not in stdout or end not in stdout:
        raise ValueError(f"missing Singular markers for {label}")
    rows = [
        row.strip()
        for row in stdout.split(begin, 1)[1].split(end, 1)[0].splitlines()
        if row.strip()
    ]
    if len(rows) < 2:
        raise ValueError(f"incomplete Singular summary for {label}")
    basis_size = int(rows[0])
    basis_rows = []
    for row in rows[2:]:
        degree_text, term_count_text = row.split(",", 1)
        basis_rows.append(
            {"total_degree": int(degree_text), "term_count": int(term_count_text)}
        )
    if len(basis_rows) != basis_size:
        raise ValueError(f"basis summary length mismatch for {label}")
    return {
        "basis_size": basis_size,
        "unit_membership_remainder": rows[1],
        "basis_degree_term_rows": basis_rows,
        "basis_summary_sha256": canonical_hash(basis_rows),
        "unit_ideal_detected": rows[1] == "0",
    }


def singular_script(
    old_quotients: list[list[list[Any]]],
    fifth_quotient: list[list[Any]],
    sixth_quotient: list[list[Any]],
    prime: int,
    algorithm: str,
) -> str:
    all_quotients = [*old_quotients, fifth_quotient, sixth_quotient]
    lines = [f"ring r={prime},(u,a,b,c),dp;"]
    for index, terms in enumerate(all_quotients):
        lines.append(f"poly q{index}={r202.polynomial_text(terms, prime)};")
    saturation = "1-u*(a2+b2+c2)"
    append_classification(lines, "unit_control", f"a,b,c,{saturation}", algorithm)
    lines.append("kill i;")
    append_classification(lines, "nonunit_control", f"a,b,{saturation}", algorithm)
    lines.append("kill i;")
    append_classification(
        lines,
        "expanded_engineering",
        f"q0,q1,q2,q3,q4,q5,{saturation}",
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
            "poly normalized_h=h/leadcoef(h);",
            f'print("{BEGIN}slice");',
            "print(deg(normalized_h));",
            "print(size(normalized_h));",
            "print(string(normalized_h-1));",
            f'print("{END}slice");',
            "quit;",
            "",
        ]
    )
    return "\n".join(lines)


def parse_slice(stdout: str) -> dict[str, Any]:
    begin = f"{BEGIN}slice"
    end = f"{END}slice"
    if begin not in stdout or end not in stdout:
        raise ValueError("missing Singular slice markers")
    rows = [
        row.strip()
        for row in stdout.split(begin, 1)[1].split(end, 1)[0].splitlines()
        if row.strip()
    ]
    if len(rows) != 3:
        raise ValueError("incomplete Singular slice summary")
    return {
        "gcd_total_degree": int(rows[0]),
        "gcd_term_count": int(rows[1]),
        "normalized_gcd_is_one": rows[2] == "0",
    }


def run_prime(
    singular: str,
    old_quotients: list[list[list[Any]]],
    fifth_quotient: list[list[Any]],
    sixth_quotient: list[list[Any]],
    prime: int,
    timeout_seconds: int,
    max_memory_mib: int,
    algorithm: str,
) -> dict[str, Any]:
    script = singular_script(
        old_quotients, fifth_quotient, sixth_quotient, prime, algorithm
    )
    started = time.monotonic()
    maximum_rss_kib = 0
    termination_reason = "completed"
    with (
        tempfile.TemporaryFile(mode="w+") as stdout_file,
        tempfile.TemporaryFile(mode="w+") as stderr_file,
    ):
        process = subprocess.Popen(
            [singular, "-q"],
            stdin=subprocess.PIPE,
            stdout=stdout_file,
            stderr=stderr_file,
            text=True,
        )
        if process.stdin is None:
            raise RuntimeError("Singular stdin pipe is unavailable")
        process.stdin.write(script)
        process.stdin.close()
        while process.poll() is None:
            elapsed = time.monotonic() - started
            maximum_rss_kib = max(
                maximum_rss_kib, r202.resident_set_kib(process.pid)
            )
            if elapsed >= timeout_seconds:
                termination_reason = "timeout"
                process.kill()
                break
            if maximum_rss_kib > max_memory_mib * 1024:
                termination_reason = "memory_limit"
                process.kill()
                break
            time.sleep(1.0)
        returncode = process.wait()
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read()
        stderr = stderr_file.read()
    elapsed = time.monotonic() - started
    record: dict[str, Any] = {
        "prime": prime,
        "termination_reason": termination_reason,
        "timed_out": termination_reason == "timeout",
        "memory_limit_exceeded": termination_reason == "memory_limit",
        "timeout_seconds": timeout_seconds,
        "max_memory_mib": max_memory_mib,
        "memory_limit_mode": "RSS_watchdog",
        "algorithm": algorithm,
        "elapsed_seconds": round(elapsed, 6),
        "maximum_rss_kib_observed": maximum_rss_kib,
        "returncode": returncode,
        "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
    }
    if termination_reason != "completed" or returncode != 0:
        record.update(
            {
                "controls_checked": False,
                "expanded_engineering_classified": False,
                "slice_classified": False,
                "stderr_tail": stderr[-2000:],
                "checked": False,
            }
        )
        return record
    try:
        unit_control = parse_classification(stdout, "unit_control")
        nonunit_control = parse_classification(stdout, "nonunit_control")
        expanded = parse_classification(stdout, "expanded_engineering")
        slice_row = parse_slice(stdout)
    except (ValueError, IndexError) as exc:
        record.update(
            {
                "controls_checked": False,
                "expanded_engineering_classified": False,
                "slice_classified": False,
                "parse_error": str(exc),
                "checked": False,
            }
        )
        return record
    controls_checked = (
        unit_control["unit_ideal_detected"]
        and not nonunit_control["unit_ideal_detected"]
    )
    slice_checked = (
        slice_row["gcd_total_degree"] == 0
        and slice_row["gcd_term_count"] == 1
        and slice_row["normalized_gcd_is_one"]
    )
    record.update(
        {
            "unit_control": unit_control,
            "nonunit_control": nonunit_control,
            "expanded_engineering": expanded,
            "slice": slice_row,
            "controls_checked": controls_checked,
            "expanded_engineering_classified": True,
            "slice_classified": True,
            "checked": controls_checked and slice_checked,
        }
    )
    return record


def validate_bridge(
    root: Path, prime: int, bridge_tool_hash: str
) -> tuple[dict[str, Any], str]:
    path = root / R206_RESULTS[prime]
    result = json.loads(path.read_text())
    support = [row[0] for row in result.get("quotient_canonical_terms", [])]
    if (
        not payload_hash_valid(result)
        or result.get("method")
        != "b9_r206_r205_selected_rows_sixth_minor_bridge_v1"
        or result.get("version") != "0.1.0"
        or result.get("characteristic") != prime
        or result.get("new_minor_index") != 5
        or result.get("bridge_tool_sha256") != bridge_tool_hash
        or result.get("D_exponent") != 44
        or result.get("determinant_total_degree") != 184
        or result.get("determinant_term_count") != 6555
        or result.get("quotient_total_degree") != 96
        or result.get("quotient_term_count") != 1363
        or result.get("exact_D44_division_verified") is not True
        or result.get("factorization_validated") is not True
        or result.get("scaled_recomposition_validated") is not True
        or result.get("five_minor_slice_gcd_degree") != 6
        or result.get("five_minor_slice_gcd_matches_R204_sextic") is not True
        or result.get("slice_quotient_gcd_with_R204_sextic_degree") != 0
        or result.get("R204_sextic_excluded_mod_prime") is not True
        or result.get("positive_nonzero_replay_count") != 2
        or len(result.get("point_replays", [])) != 4
        or not all(
            row.get("determinant_replay_match") is True
            and row.get("D_power_recomposition_match") is True
            and (
                row.get("require_nonzero") is not True
                or row.get("quotient_nonzero") is True
            )
            for row in result.get("point_replays", [])
        )
        or result.get(
            "combined_R204_fifth_plus_R206_sixth_excludes_known_b_zero_components"
        )
        is not True
        or result.get("frozen_holdouts_executed") is not False
        or result.get("scientific_promotion_accepted") is not False
        or result.get("new_credit_delta") != 0
        or result.get("checked") is not True
    ):
        raise ValueError(f"R206 sixth-minor artifact failed validation at {prime}")
    return result, canonical_hash(support)


def build_result(
    root: Path,
    primes: list[int],
    timeout_seconds: int,
    max_memory_mib: int,
    algorithm: str,
) -> dict[str, Any]:
    singular = shutil.which("Singular")
    if singular is None:
        raise RuntimeError("Singular executable not found")
    if set(primes) != set(DEFAULT_PRIMES):
        raise ValueError("R206 requires exactly the two R204 classification primes")
    source_paths = {
        "r201": root / "results/B9_R201_integer_reconstruction_v0.json",
        "r204_preflight": root / "results/B9_R204_expanded_ideal_preflight_v0.json",
        "r205": root / "results/B9_R205_sextic_full_matrix_rank_v0.json",
        "bridge_tool": root / "tools/b9_r206_sixth_minor_bridge.py",
        "r204_preflight_tool": root / "tools/b9_r204_expanded_ideal_preflight.py",
    }
    r201 = json.loads(source_paths["r201"].read_text())
    r204_preflight = json.loads(source_paths["r204_preflight"].read_text())
    r205 = json.loads(source_paths["r205"].read_text())
    if (
        r201.get("checked") is not True
        or len(r201.get("rows", [])) != 4
        or not payload_hash_valid(r204_preflight)
        or r204_preflight.get("checked") is not True
        or r204_preflight.get("expanded_slice_gcd_total_degree") != 6
        or not payload_hash_valid(r205)
        or r205.get("checked") is not True
        or r205.get("sextic_component_is_full_rank_selected_minor_artifact")
        is not True
    ):
        raise ValueError("R201/R204/R205 source chain is not accepted")

    bridge_hash = sha256_file(source_paths["bridge_tool"])
    sixth: dict[int, dict[str, Any]] = {}
    support_hashes = []
    for prime in primes:
        sixth[prime], support_hash = validate_bridge(root, prime, bridge_hash)
        support_hashes.append(support_hash)
    if len(set(support_hashes)) != 1:
        raise ValueError("R206 quotient monomial support differs across primes")

    rows = r201["rows"]
    old_quotients = [r202.primitive_quotient_terms(row) for row in rows]
    fifth = {
        prime: json.loads((root / R204_RESULTS[prime]).read_text())
        for prime in primes
    }
    prime_rows = [
        run_prime(
            singular,
            old_quotients,
            fifth[prime]["quotient_canonical_terms"],
            sixth[prime]["quotient_canonical_terms"],
            prime,
            timeout_seconds,
            max_memory_mib,
            algorithm,
        )
        for prime in primes
    ]
    classified = [
        row for row in prime_rows if row.get("expanded_engineering_classified")
    ]
    unit_rows = [
        row
        for row in classified
        if row["expanded_engineering"]["unit_ideal_detected"] is True
    ]
    nonunit_rows = [
        row
        for row in classified
        if row["expanded_engineering"]["unit_ideal_detected"] is False
    ]
    all_checked = all(row.get("checked") is True for row in prime_rows)
    stable = {
        "source_sha256": {
            label: sha256_file(path) for label, path in source_paths.items()
        },
        "fifth_minor_result_sha256": {
            str(prime): sha256_file(root / R204_RESULTS[prime]) for prime in primes
        },
        "sixth_minor_result_sha256": {
            str(prime): sha256_file(root / R206_RESULTS[prime]) for prime in primes
        },
        "sixth_minor_support_sha256": support_hashes[0],
        "saturation_equation": "1-u*(a^2+b^2+c^2)",
        "coefficient_domain": "finite_fields_only",
        "monomial_order": "dp(u,a,b,c)",
        "standard_basis_algorithm": algorithm,
        "prime_rows": [
            {
                "prime": row["prime"],
                "controls_checked": row.get("controls_checked"),
                "expanded_basis_size": row.get("expanded_engineering", {}).get(
                    "basis_size"
                ),
                "expanded_unit_membership_remainder": row.get(
                    "expanded_engineering", {}
                ).get("unit_membership_remainder"),
                "expanded_unit_ideal_detected": row.get(
                    "expanded_engineering", {}
                ).get("unit_ideal_detected"),
                "expanded_basis_summary_sha256": row.get(
                    "expanded_engineering", {}
                ).get("basis_summary_sha256"),
                "slice": row.get("slice"),
                "stdout_sha256": row.get("stdout_sha256"),
            }
            for row in prime_rows
        ],
    }
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R201_to_R206_six_minor_modular_preflight_only",
        "coupling": "13/32",
        "n": 4,
        "source_sha256": stable["source_sha256"],
        "fifth_minor_result_sha256": stable["fifth_minor_result_sha256"],
        "sixth_minor_result_sha256": stable["sixth_minor_result_sha256"],
        "sixth_minor_support_sha256": support_hashes[0],
        "old_minor_count": 5,
        "expanded_minor_count": 6,
        "determinant_total_degree": 184,
        "determinant_term_count": 6555,
        "D_exponent": 44,
        "new_quotient_total_degree": 96,
        "new_quotient_term_count": 1363,
        "old_slice_gcd_total_degree": 6,
        "expanded_slice_gcd_total_degree": 0,
        "expanded_slice_gcd_term_count": 1,
        "all_known_b_zero_components_excluded": all(
            row.get("slice", {}).get("normalized_gcd_is_one") is True
            for row in prime_rows
        ),
        "saturation_equation": stable["saturation_equation"],
        "coefficient_domain": stable["coefficient_domain"],
        "monomial_order": stable["monomial_order"],
        "standard_basis_algorithm": algorithm,
        "singular_path": singular,
        "singular_version": subprocess.check_output(
            [singular, "--version"], text=True
        ).splitlines()[0],
        "primes": primes,
        "per_prime_timeout_seconds": timeout_seconds,
        "per_prime_max_memory_mib": max_memory_mib,
        "memory_limit_mode": "RSS_watchdog",
        "prime_rows": prime_rows,
        "classified_prime_count": len(classified),
        "unit_ideal_prime_count": len(unit_rows),
        "nonunit_ideal_prime_count": len(nonunit_rows),
        "all_classified_primes_detect_unit_ideal": bool(classified)
        and len(unit_rows) == len(classified),
        "all_classified_primes_detect_nonunit_ideal": bool(classified)
        and len(nonunit_rows) == len(classified),
        "six_minor_unit_certificate_route_supported": bool(classified)
        and len(unit_rows) == len(classified),
        "preflight_conclusion": (
            "two_prime_unit_preflight_after_sixth_minor"
            if len(unit_rows) == len(prime_rows)
            else "two_prime_nonunit_outside_b_zero_after_sixth_minor"
            if len(nonunit_rows) == len(prime_rows)
            else "mixed_or_incomplete_modular_classification"
        ),
        "stable_classification_payload": stable,
        "stable_classification_sha256": canonical_hash(stable),
        "execution_complete": len(classified) == len(prime_rows),
        "modular_preflight_checked": all_checked,
        "rational_nullstellensatz_certificate_verified": False,
        "ideal_membership_certificate_verified": False,
        "isolated_presource_replay_complete": False,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "claim_boundary": (
            "The sixth selected minor removes the residual b=0 sextic when "
            "combined with the fifth minor. Two finite-field saturated-ideal "
            "classifications are a route-selection preflight, not a QQ "
            "Nullstellensatz certificate or a global scientific theorem."
        ),
        "checked": all_checked,
    }
    result["payload_sha256"] = canonical_hash(result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--primes", default=",".join(str(value) for value in DEFAULT_PRIMES)
    )
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--max-memory-mib", type=int, default=8192)
    parser.add_argument("--algorithm", choices=("std", "slimgb"), default="slimgb")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    primes = [int(value) for value in args.primes.split(",") if value.strip()]
    if not primes or any(not is_prime(value) for value in primes):
        raise ValueError("--primes must contain comma-separated positive primes")
    if args.timeout_seconds < 1 or args.max_memory_mib < 256:
        raise ValueError("invalid timeout or memory limit")
    root = Path(__file__).resolve().parents[1]
    result = build_result(
        root,
        primes,
        args.timeout_seconds,
        args.max_memory_mib,
        args.algorithm,
    )
    output = args.output if args.output.is_absolute() else root / args.output
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "checked": result["checked"],
                "execution_complete": result["execution_complete"],
                "classified_prime_count": result["classified_prime_count"],
                "unit_ideal_prime_count": result["unit_ideal_prime_count"],
                "nonunit_ideal_prime_count": result["nonunit_ideal_prime_count"],
                "expanded_slice_gcd_total_degree": result[
                    "expanded_slice_gcd_total_degree"
                ],
                "new_credit_delta": result["new_credit_delta"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
