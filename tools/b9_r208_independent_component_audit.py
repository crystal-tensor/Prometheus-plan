#!/usr/bin/env python3
"""Independently audit R208 by eliminating the complete R207 radical chart."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import b9_r202_modular_ideal_preflight as r202


METHOD = "b9_r208_independent_radical_component_std_audit_v1"
VERSION = "0.1.0"
PRIMES = (1_000_003, 536_870_723)
BRIDGE_RESULTS = {
    1_000_003: Path("results/B9_R208_seventh_minor_mod1000003_v0.json"),
    536_870_723: Path("results/B9_R208_seventh_minor_mod536870723_v0.json"),
}
BEGIN = "__R208_AUDIT_BEGIN__"
END = "__R208_AUDIT_END__"


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


def script(terms: list[list[Any]], prime: int) -> str:
    q = r202.polynomial_text(terms, prime)
    return "\n".join(
        [
            f"ring r={prime},(a,b,c),dp;",
            f"poly q={q};",
            "ideal K=169*a2+407*c2,169*b2-576*c2,c-1;",
            "ideal GK=std(K);",
            "ideal E=K,q;",
            "ideal GE=std(E);",
            f'print("{BEGIN}");',
            "print(size(GK));",
            "print(string(reduce(1,GK)));",
            "print(vdim(GK));",
            "print(size(GE));",
            "print(string(reduce(1,GE)));",
            "print(vdim(GE));",
            "int i;",
            "for(i=1;i<=size(GE);i++){print(string(deg(GE[i]))+\",\"+string(size(GE[i])));}",
            f'print("{END}");',
            "quit;",
            "",
        ]
    )


def parse(stdout: str) -> dict[str, Any]:
    if BEGIN not in stdout or END not in stdout:
        raise ValueError("missing Singular audit markers")
    rows = [
        row.strip()
        for row in stdout.split(BEGIN, 1)[1].split(END, 1)[0].splitlines()
        if row.strip()
    ]
    if len(rows) < 6:
        raise ValueError("incomplete Singular audit summary")
    excluded_basis_size = int(rows[3])
    basis_rows = []
    for row in rows[6:]:
        degree, term_count = row.split(",", 1)
        basis_rows.append(
            {"total_degree": int(degree), "term_count": int(term_count)}
        )
    if len(basis_rows) != excluded_basis_size:
        raise ValueError("excluded-basis summary length mismatch")
    return {
        "radical_basis_size": int(rows[0]),
        "radical_unit_membership_remainder": rows[1],
        "radical_vector_space_dimension": int(rows[2]),
        "excluded_basis_size": excluded_basis_size,
        "excluded_unit_membership_remainder": rows[4],
        "excluded_vector_space_dimension": int(rows[5]),
        "excluded_basis_degree_term_rows": basis_rows,
        "excluded_basis_summary_sha256": canonical_hash(basis_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/B9_R208_independent_component_audit_v0.json"),
    )
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    singular = shutil.which("Singular")
    if singular is None:
        raise RuntimeError("Singular executable not found")

    r207_path = root / "results/B9_R207_off_slice_component_rank_v0.json"
    r207 = json.loads(r207_path.read_text())
    if (
        not payload_hash_valid(r207)
        or r207.get("checked") is not True
        or r207.get("two_prime_radical_equality_supported") is not True
        or r207.get("candidate_radical_generators")
        != ["169*a^2+407*c^2", "169*b^2-576*c^2", "2*u*c^2-1"]
        or r207.get("candidate_point_count_over_algebraic_closure") != 4
    ):
        raise ValueError("R207 radical source is not accepted")

    rows = []
    bridge_hashes: dict[str, str] = {}
    support_hashes = []
    for prime in PRIMES:
        path = root / BRIDGE_RESULTS[prime]
        bridge = json.loads(path.read_text())
        if (
            not payload_hash_valid(bridge)
            or bridge.get("method")
            != "b9_r208_r207_cross_branch_seventh_minor_bridge_v1"
            or bridge.get("characteristic") != prime
            or bridge.get("new_minor_index") != 6
            or bridge.get("exact_D44_division_verified") is not True
            or bridge.get("checked") is not True
        ):
            raise ValueError(f"R208 bridge source is not accepted at {prime}")
        terms = bridge["quotient_canonical_terms"]
        support_hashes.append(canonical_hash([term[0] for term in terms]))
        singular_input = script(terms, prime)
        completed = subprocess.run(
            [singular, "-q"],
            input=singular_input,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"Singular std audit failed at {prime}: {completed.stderr[-2000:]}"
            )
        row = {
            "prime": prime,
            "algorithm": "std",
            "singular_input_sha256": hashlib.sha256(
                singular_input.encode()
            ).hexdigest(),
            "stdout_sha256": hashlib.sha256(completed.stdout.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(completed.stderr.encode()).hexdigest(),
            **parse(completed.stdout),
        }
        row["radical_nonunit_before_seventh_minor"] = (
            row["radical_unit_membership_remainder"] == "1"
            and row["radical_vector_space_dimension"] == 4
        )
        row["radical_plus_seventh_minor_is_unit"] = (
            row["excluded_basis_size"] == 1
            and row["excluded_unit_membership_remainder"] == "0"
            and row["excluded_vector_space_dimension"] == 0
        )
        row["checked"] = (
            row["radical_nonunit_before_seventh_minor"]
            and row["radical_plus_seventh_minor_is_unit"]
        )
        rows.append(row)
        bridge_hashes[str(prime)] = sha256_file(path)
    if len(set(support_hashes)) != 1:
        raise ValueError("R208 quotient support differs across audit primes")

    all_checked = all(row["checked"] for row in rows)
    stable = {
        "method": METHOD,
        "version": VERSION,
        "scope": "public_R207_radical_plus_R208_seventh_quotient_std_audit_only",
        "primes": list(PRIMES),
        "algorithm": "std",
        "radical_generators": [
            "169*a^2+407*c^2",
            "169*b^2-576*c^2",
            "c-1",
        ],
        "radical_vector_space_dimensions": [
            row["radical_vector_space_dimension"] for row in rows
        ],
        "excluded_vector_space_dimensions": [
            row["excluded_vector_space_dimension"] for row in rows
        ],
        "radical_plus_seventh_minor_unit_prime_count": sum(
            row["radical_plus_seventh_minor_is_unit"] for row in rows
        ),
        "independent_radical_route_supports_unit_ideal": all_checked,
        "rational_nullstellensatz_certificate_verified": False,
        "characteristic_zero_rank_theorem_verified": False,
        "frozen_holdouts_executed": False,
        "scientific_promotion_accepted": False,
        "new_credit_delta": 0,
    }
    result = {
        **stable,
        "audit_tool_sha256": sha256_file(Path(__file__)),
        "source_r207_result_sha256": sha256_file(r207_path),
        "source_bridge_result_sha256": bridge_hashes,
        "seventh_minor_support_sha256": support_hashes[0],
        "singular_path": singular,
        "singular_version": subprocess.check_output(
            [singular, "--version"], text=True
        ).splitlines()[0],
        "prime_rows": rows,
        "stable_audit_payload": stable,
        "stable_audit_sha256": canonical_hash(stable),
        "claim_boundary": (
            "The independent std route eliminates the complete R207 radical "
            "chart at two finite-field primes. It does not produce a QQ "
            "Nullstellensatz certificate, a characteristic-zero global-rank "
            "theorem, a Quantum PCP or NLTS theorem, hardware evidence, or "
            "new credit."
        ),
        "checked": all_checked,
    }
    payload = dict(result)
    result["payload_sha256"] = canonical_hash(payload)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "checked": result["checked"],
                "radical_dimensions": stable["radical_vector_space_dimensions"],
                "excluded_dimensions": stable["excluded_vector_space_dimensions"],
                "unit_prime_count": stable[
                    "radical_plus_seventh_minor_unit_prime_count"
                ],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
