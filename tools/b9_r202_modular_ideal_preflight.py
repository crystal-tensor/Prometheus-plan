#!/usr/bin/env python3
"""Probe the R201 quotient ideal over finite fields without claiming a Q certificate."""

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


METHOD = "b9_r202_modular_saturated_ideal_preflight_v2"
VERSION = "0.3.0"
DEFAULT_PRIMES = (1_000_003, 536_870_723)
BEGIN = "__R202_BEGIN__"
END = "__R202_END__"


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_prime(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    limit = math.isqrt(value)
    divisor = 3
    while divisor <= limit:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def monomial_text(exponents: list[int]) -> str:
    factors = []
    for variable, exponent in zip(("a", "b", "c"), exponents):
        if exponent == 1:
            factors.append(variable)
        elif exponent > 1:
            factors.append(f"{variable}{exponent}")
    return "*".join(factors) or "1"


def polynomial_text(terms: list[list[Any]], prime: int) -> str:
    pieces = []
    for raw_exponents, raw_coefficient in terms:
        coefficient = int(raw_coefficient) % prime
        if coefficient == 0:
            continue
        monomial = monomial_text([int(value) for value in raw_exponents])
        if monomial == "1":
            pieces.append(str(coefficient))
        elif coefficient == 1:
            pieces.append(monomial)
        else:
            pieces.append(f"{coefficient}*{monomial}")
    return "+".join(pieces) or "0"


def primitive_quotient_terms(row: dict[str, Any]) -> list[list[Any]]:
    terms = row.get("quotient_canonical_terms", [])
    content = int(row.get("quotient_integer_content", 0))
    if not terms or content == 0:
        raise ValueError("source quotient terms or integer content are missing")
    primitive_terms = []
    for raw_exponents, raw_coefficient in terms:
        coefficient = int(raw_coefficient)
        if coefficient % content:
            raise ValueError("source quotient coefficient is not divisible by content")
        primitive_terms.append(
            [
                [int(value) for value in raw_exponents],
                str(coefficient // content),
            ]
        )
    if canonical_hash(primitive_terms) != row.get(
        "primitive_quotient_canonical_terms_sha256"
    ):
        raise ValueError("source primitive quotient hash mismatch")
    return primitive_terms


def resident_set_kib(pid: int) -> int:
    completed = subprocess.run(
        ["ps", "-o", "rss=", "-p", str(pid)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    try:
        return int(completed.stdout.strip())
    except ValueError:
        return 0


def append_classification(
    lines: list[str],
    label: str,
    ideal_expression: str,
    algorithm: str,
) -> None:
    safe_label = re.sub(r"[^A-Za-z0-9_-]", "_", label)
    lines.extend(
        [
            f"ideal I_{safe_label}={ideal_expression};",
            f"ideal G_{safe_label}={algorithm}(I_{safe_label});",
            f'print("{BEGIN}{safe_label}");',
            f"print(size(G_{safe_label}));",
            f"print(string(reduce(1,G_{safe_label})));",
            "int i;",
            f"for(i=1;i<=size(G_{safe_label});i++)"
            f'{{print(string(deg(G_{safe_label}[i]))+","+'
            f'string(size(G_{safe_label}[i])));}}',
            f'print("{END}{safe_label}");',
        ]
    )


def singular_script(
    quotients: list[list[list[Any]]],
    prime: int,
    algorithm: str,
) -> str:
    lines = [
        f"ring r={prime},(u,a,b,c),dp;",
    ]
    for index, terms in enumerate(quotients):
        lines.append(f"poly q{index}={polynomial_text(terms, prime)};")
    saturation = "1-u*(a2+b2+c2)"
    append_classification(lines, "unit_control", f"a,b,c,{saturation}", algorithm)
    lines.append("kill i;")
    append_classification(lines, "nonunit_control", f"a,b,{saturation}", algorithm)
    lines.append("kill i;")
    append_classification(
        lines,
        "engineering",
        f"q0,q1,q2,q3,{saturation}",
        algorithm,
    )
    lines.extend(["quit;", ""])
    return "\n".join(lines)


def parse_classification(stdout: str, label: str) -> dict[str, Any]:
    safe_label = re.sub(r"[^A-Za-z0-9_-]", "_", label)
    begin = f"{BEGIN}{safe_label}"
    end = f"{END}{safe_label}"
    if begin not in stdout or end not in stdout:
        raise ValueError(f"missing Singular markers for {label}")
    body = stdout.split(begin, 1)[1].split(end, 1)[0]
    rows = [line.strip() for line in body.splitlines() if line.strip()]
    if len(rows) < 2:
        raise ValueError(f"incomplete Singular summary for {label}")
    basis_size = int(rows[0])
    unit_remainder = rows[1]
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
        "unit_membership_remainder": unit_remainder,
        "basis_degree_term_rows": basis_rows,
        "basis_summary_sha256": canonical_hash(basis_rows),
        "unit_ideal_detected": unit_remainder == "0",
    }


def run_prime(
    singular: str,
    quotients: list[list[list[Any]]],
    prime: int,
    timeout_seconds: int,
    max_memory_mib: int,
    algorithm: str,
) -> dict[str, Any]:
    script = singular_script(quotients, prime, algorithm)
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
            maximum_rss_kib = max(maximum_rss_kib, resident_set_kib(process.pid))
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
        maximum_rss_kib = max(maximum_rss_kib, resident_set_kib(process.pid))
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read()
        stderr = stderr_file.read()

    elapsed = time.monotonic() - started
    if termination_reason != "completed":
        try:
            unit_control = parse_classification(stdout, "unit_control")
            nonunit_control = parse_classification(stdout, "nonunit_control")
            controls_checked = (
                unit_control["unit_ideal_detected"]
                and not nonunit_control["unit_ideal_detected"]
            )
        except (ValueError, IndexError):
            unit_control = None
            nonunit_control = None
            controls_checked = False
        return {
            "prime": prime,
            "timed_out": termination_reason == "timeout",
            "memory_limit_exceeded": termination_reason == "memory_limit",
            "termination_reason": termination_reason,
            "timeout_seconds": timeout_seconds,
            "max_memory_mib": max_memory_mib,
            "memory_limit_mode": "RSS_watchdog",
            "algorithm": algorithm,
            "elapsed_seconds": round(elapsed, 6),
            "maximum_rss_kib_observed": maximum_rss_kib,
            "stdout_sha256": hashlib.sha256(stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr.encode()).hexdigest(),
            "unit_control": unit_control,
            "nonunit_control": nonunit_control,
            "controls_checked": controls_checked,
            "engineering_classified": False,
            "checked": False,
        }
    record: dict[str, Any] = {
        "prime": prime,
        "timed_out": False,
        "memory_limit_exceeded": False,
        "termination_reason": termination_reason,
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
    if returncode != 0:
        record.update(
            {
                "controls_checked": False,
                "engineering_classified": False,
                "stderr_tail": stderr[-2000:],
                "checked": False,
            }
        )
        return record
    try:
        unit_control = parse_classification(stdout, "unit_control")
        nonunit_control = parse_classification(stdout, "nonunit_control")
        engineering = parse_classification(stdout, "engineering")
    except (ValueError, IndexError) as exc:
        record.update(
            {
                "controls_checked": False,
                "engineering_classified": False,
                "parse_error": str(exc),
                "checked": False,
            }
        )
        return record
    controls_checked = (
        unit_control["unit_ideal_detected"]
        and not nonunit_control["unit_ideal_detected"]
    )
    record.update(
        {
            "unit_control": unit_control,
            "nonunit_control": nonunit_control,
            "engineering": engineering,
            "controls_checked": controls_checked,
            "engineering_classified": True,
            "checked": controls_checked,
        }
    )
    return record


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
    source_path = root / "results/B9_R201_integer_reconstruction_v0.json"
    source = json.loads(source_path.read_text())
    if source.get("checked") is not True:
        raise ValueError("source integer reconstruction is not checked")
    rows = source.get("rows", [])
    if len(rows) != 4:
        raise ValueError("source integer reconstruction must contain four rows")
    raw_quotients = [row.get("quotient_canonical_terms", []) for row in rows]
    raw_quotient_hashes = [canonical_hash(terms) for terms in raw_quotients]
    declared_raw_hashes = [
        row.get("quotient_canonical_terms_sha256") for row in rows
    ]
    if raw_quotient_hashes != declared_raw_hashes:
        raise ValueError("source quotient payload hash mismatch")
    quotients = [primitive_quotient_terms(row) for row in rows]
    quotient_hashes = [canonical_hash(terms) for terms in quotients]
    prime_rows = [
        run_prime(
            singular,
            quotients,
            prime,
            timeout_seconds,
            max_memory_mib,
            algorithm,
        )
        for prime in primes
    ]
    classified_rows = [row for row in prime_rows if row.get("engineering_classified")]
    unit_rows = [
        row
        for row in classified_rows
        if row.get("engineering", {}).get("unit_ideal_detected") is True
    ]
    all_checked = all(row.get("checked") is True for row in prime_rows)
    execution_complete = len(classified_rows) == len(prime_rows)
    nonunit_rows = [
        row
        for row in classified_rows
        if row.get("engineering", {}).get("unit_ideal_detected") is False
    ]
    stable_classification = {
        "source_integer_reconstruction_sha256": sha256_file(source_path),
        "source_primitive_quotient_sha256": quotient_hashes,
        "generator_normalization": "primitive_integer_quotients; QQ units removed",
        "saturation_equation": "1-u*(a^2+b^2+c^2)",
        "coefficient_domain": "finite_fields_only",
        "monomial_order": "dp(u,a,b,c)",
        "standard_basis_algorithm": algorithm,
        "singular_version": subprocess.check_output(
            [singular, "--version"], text=True
        ).splitlines()[0],
        "prime_rows": [
            {
                "prime": row["prime"],
                "controls_checked": row.get("controls_checked"),
                "unit_control_detected": row.get("unit_control", {}).get(
                    "unit_ideal_detected"
                ),
                "nonunit_control_detected": row.get("nonunit_control", {}).get(
                    "unit_ideal_detected"
                ),
                "engineering_basis_size": row.get("engineering", {}).get(
                    "basis_size"
                ),
                "engineering_unit_membership_remainder": row.get(
                    "engineering", {}
                ).get("unit_membership_remainder"),
                "engineering_unit_ideal_detected": row.get("engineering", {}).get(
                    "unit_ideal_detected"
                ),
                "engineering_basis_summary_sha256": row.get(
                    "engineering", {}
                ).get("basis_summary_sha256"),
                "stdout_sha256": row.get("stdout_sha256"),
            }
            for row in prime_rows
        ],
    }
    result = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R201_modular_preflight_only",
        "coupling": "13/32",
        "n": 4,
        "source_integer_reconstruction": "results/B9_R201_integer_reconstruction_v0.json",
        "source_integer_reconstruction_sha256": sha256_file(source_path),
        "source_quotient_integer_contents": [
            row["quotient_integer_content"] for row in rows
        ],
        "source_raw_quotient_sha256": raw_quotient_hashes,
        "source_quotient_term_counts": [len(terms) for terms in quotients],
        "source_primitive_quotient_sha256": quotient_hashes,
        "generator_normalization": "primitive_integer_quotients; QQ units removed",
        "saturation_equation": "1-u*(a^2+b^2+c^2)",
        "coefficient_domain": "finite_fields_only",
        "monomial_order": "dp(u,a,b,c)",
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
        "classified_prime_count": len(classified_rows),
        "unit_ideal_prime_count": len(unit_rows),
        "nonunit_ideal_prime_count": len(nonunit_rows),
        "all_classified_primes_detect_unit_ideal": bool(classified_rows)
        and len(unit_rows) == len(classified_rows),
        "all_classified_primes_detect_nonunit_ideal": bool(classified_rows)
        and len(nonunit_rows) == len(classified_rows),
        "four_minor_unit_certificate_route_supported": bool(classified_rows)
        and len(unit_rows) == len(classified_rows),
        "preflight_conclusion": (
            "two_prime_nonunit_counterevidence_to_four_minor_unit_certificate"
            if len(nonunit_rows) == len(prime_rows)
            else "mixed_or_incomplete_modular_classification"
        ),
        "stable_classification_payload": stable_classification,
        "stable_classification_sha256": canonical_hash(stable_classification),
        "execution_complete": execution_complete,
        "modular_preflight_checked": all_checked,
        "rational_nullstellensatz_certificate_verified": False,
        "ideal_membership_certificate_verified": False,
        "isolated_presource_replay_complete": False,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
        "claim_boundary": (
            "The two finite-field nonunit classifications are counterevidence to a "
            "unit certificate from these four minors, but they do not prove a rational "
            "or real projective common zero, a rank drop in the full source matrix, or "
            "failure over QQ. They do not open frozen holdouts or support promotion."
        ),
        "checked": all_checked,
    }
    result["payload_sha256"] = canonical_hash(result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--primes",
        default=",".join(str(value) for value in DEFAULT_PRIMES),
    )
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--max-memory-mib", type=int, default=8192)
    parser.add_argument("--algorithm", choices=("std", "slimgb"), default="slimgb")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    primes = [int(value) for value in args.primes.split(",") if value.strip()]
    if not primes or any(not is_prime(value) for value in primes):
        raise ValueError("--primes must contain comma-separated positive primes")
    if args.timeout_seconds < 1:
        raise ValueError("--timeout-seconds must be positive")
    if args.max_memory_mib < 256:
        raise ValueError("--max-memory-mib must be at least 256")
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
                "frozen_holdouts_executed": result["frozen_holdouts_executed"],
                "new_credit_delta": result["new_credit_delta"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
