#!/usr/bin/env python3
"""Post-result integration gate for the B9 R200 evidence chain."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any


EXPERIMENT_ID = "B9-R200-post-result-integrated-adjudication"
METHOD = "b9_r200_integrated_adjudication_v1"
VERSION = "0.1.0"
PREREGISTRATION_COMMIT = "ccc8f69dbba15390b96918eb55282122cfbaf824"
EXPECTED_CONTRACT_SHA256 = "a1208296eeaf56ed7bf51ed740b51931b7e1067cdb53d2e5e6e0d931aca356c0"
EXPECTED_ATLAS_SHA256 = "b168b38442f85cd7a485e6e1ea2332fab1fa994e7c13956c405384e31f59cd47"
EXPECTED_PROJECTIVE_SHA256 = "f64e2e63f922d691bdeef5fdf58b2e90207afe3b775d55dafc713e19b7705a2f"
EXPECTED_GRID_KEYS_SHA256 = "29e7360a5411dad01aa7e96a8920be46cd05444e5fdc88b56d3ba621a6a11cdd"
EXPECTED_MAIN_PAYLOAD_SHA256 = "e96959bd881d88a114bd5f80ff4dfdac2a5623473cc398594746b5c6d4f4da9e"
EXPECTED_MAIN_PROTOCOL_SHA256 = "c0e26511769afbd95b3bd75a2ab859b9d3e384af1afb057252f31a94173b28ba"
FROZEN_COUPLINGS = ("109/128", "113/128")
GRID_SIZES = (6, 8, 10)
MAIN_PRIMES = (1_000_003, 1_000_033)
AUDIT_PRIMES = (1_000_037, 1_000_081)
PROJECTIVE_IDS = tuple(f"rp2_{index:03d}" for index in range(31))
METADATA_FIELDS = (
    "frame_id",
    "chart",
    "parameters",
    "axes",
    "projective_axis",
    "gauge_equivalent_frame_ids",
)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        capture_output=True,
        text=True,
    )


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


def prime_checked(value: int) -> bool:
    if value < 2:
        return False
    for divisor in range(2, math.isqrt(value) + 1):
        if value % divisor == 0:
            return False
    return True


def vector(axis: dict[str, str]) -> tuple[Fraction, Fraction, Fraction]:
    return tuple(Fraction(axis.get(label, "0")) for label in "XYZ")  # type: ignore[return-value]


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


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def atlas_metadata_checks(main: dict[str, Any]) -> dict[str, Any]:
    atlas = main.get("atlas_catalog", [])
    projective = main.get("projective_catalog", [])
    atlas_ids = {row.get("frame_id") for row in atlas}
    failures: list[str] = []
    opposite_representative_count = 0
    for row in projective:
        row_id = row.get("projective_axis_id", "missing")
        axes = row.get("axes", {})
        try:
            p, q, r = (vector(axes[label]) for label in ("P", "Q", "R"))
            algebra_ok = bool(
                dot(p, p) == 1
                and dot(q, q) == 1
                and dot(r, r) == 1
                and dot(p, q) == 0
                and dot(q, r) == 0
                and dot(r, p) == 0
                and cross(q, r) == p
            )
            canonical_axis = min(p, tuple(-value for value in p))
            recorded_axis = tuple(Fraction(value) for value in row["projective_axis"])
            gauge_ids = row["gauge_equivalent_frame_ids"]
            params = row["parameters"]
            parameter_ok = bool(
                row["chart"] in {"north", "south"}
                and params["c"] in {1, 2}
                and -2 <= params["a"] <= 2
                and -2 <= params["b"] <= 2
                and math.gcd(math.gcd(abs(params["a"]), abs(params["b"])), params["c"]) == 1
            )
            if p != canonical_axis:
                opposite_representative_count += 1
            if not (
                algebra_ok
                and recorded_axis == canonical_axis
                and row["frame_id"] in gauge_ids
                and set(gauge_ids).issubset(atlas_ids)
                and parameter_ok
            ):
                failures.append(row_id)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            failures.append(row_id)
    return {
        "atlas_row_count": len(atlas),
        "atlas_sha256": canonical_hash(atlas),
        "projective_row_count": len(projective),
        "projective_sha256": canonical_hash(projective),
        "opposite_representative_count": opposite_representative_count,
        "failure_count": len(failures),
        "failures": failures,
        "checked": bool(
            len(atlas) == 82
            and len(atlas_ids) == 82
            and len(projective) == 31
            and canonical_hash(atlas) == EXPECTED_ATLAS_SHA256
            and canonical_hash(projective) == EXPECTED_PROJECTIVE_SHA256
            and not failures
        ),
    }


def expected_grid_keys() -> list[list[Any]]:
    return [
        [coupling, n, projective_id]
        for coupling in FROZEN_COUPLINGS
        for n in GRID_SIZES
        for projective_id in PROJECTIVE_IDS
    ]


def grid_checks(main: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    projective = {
        row["projective_axis_id"]: row for row in main.get("projective_catalog", [])
    }
    main_rows = main.get("grid_rows", [])
    main_by_key: dict[tuple[str, int, str], dict[str, Any]] = {}
    duplicate_count = 0
    metadata_failures: list[list[Any]] = []
    for row in main_rows:
        key = (row.get("coupling"), row.get("n"), row.get("projective_axis_id"))
        if key in main_by_key:
            duplicate_count += 1
        main_by_key[key] = row
        catalog_row = projective.get(row.get("projective_axis_id"))
        if catalog_row is None or any(
            row.get(field) != catalog_row.get(field) for field in METADATA_FIELDS
        ):
            metadata_failures.append(list(key))
    expected = {tuple(key) for key in expected_grid_keys()}
    missing = sorted(expected - set(main_by_key))
    extra = sorted(set(main_by_key) - expected)
    audit_rows = {
        (row["coupling"], row["n"], row["projective_axis_id"]): row
        for row in audit.get("rebuilt_rows", [])
    }
    cross_failures: list[list[Any]] = []
    for key in sorted(expected & set(main_by_key) & set(audit_rows)):
        left = main_by_key[key]
        right = audit_rows[key]
        if any(
            left.get(field) != right.get(field)
            for field in (
                "candidate_column_count",
                "operator_basis_sha256",
                "commutator_matrix_sha256",
            )
        ):
            cross_failures.append(list(key))
    return {
        "expected_grid_keys_sha256": canonical_hash(expected_grid_keys()),
        "main_row_count": len(main_rows),
        "unique_main_row_count": len(main_by_key),
        "audit_row_count": len(audit_rows),
        "missing_count": len(missing),
        "extra_count": len(extra),
        "duplicate_count": duplicate_count,
        "metadata_failure_count": len(metadata_failures),
        "cross_implementation_failure_count": len(cross_failures),
        "missing": missing,
        "extra": extra,
        "metadata_failures": metadata_failures,
        "cross_implementation_failures": cross_failures,
        "checked": bool(
            canonical_hash(expected_grid_keys()) == EXPECTED_GRID_KEYS_SHA256
            and len(main_rows) == 186
            and len(audit_rows) == 186
            and not missing
            and not extra
            and duplicate_count == 0
            and not metadata_failures
            and not cross_failures
        ),
    }


def public_history(root: Path) -> dict[str, Any]:
    remote_url = run_git(root, "remote", "get-url", "origin").stdout.strip()
    fetch = run_git(root, "fetch", "--quiet", "origin", "main", check=False)
    remote_main = run_git(root, "rev-parse", "refs/remotes/origin/main").stdout.strip()
    ancestor = run_git(
        root,
        "merge-base",
        "--is-ancestor",
        PREREGISTRATION_COMMIT,
        remote_main,
        check=False,
    ).returncode == 0
    return {
        "remote_url": remote_url,
        "fetch_returncode": fetch.returncode,
        "remote_main_commit": remote_main,
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "preregistration_is_ancestor_of_remote_main": ancestor,
        "expected_repository": "crystal-tensor/Prometheus-plan",
        "checked": bool(
            fetch.returncode == 0
            and "crystal-tensor/Prometheus-plan" in remote_url
            and ancestor
        ),
    }


def build_result(
    root: Path,
    main_path: Path,
    audit_path: Path,
    contract_path: Path,
) -> dict[str, Any]:
    main = json.loads(main_path.read_text(encoding="utf-8"))
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    main_copy = dict(main)
    recorded_main_payload = main_copy.pop("payload_sha256", None)
    main_round_trip = canonical_hash(main_copy)
    metadata = atlas_metadata_checks(main)
    grid = grid_checks(main, audit)
    history = public_history(root)
    control = main.get("positive_control", {})
    control_checked = bool(
        control.get("checked")
        and control.get("candidate_column_count") == 79
        and set(control.get("operator_basis_modular_ranks", {}).values()) == {79}
        and set(control.get("modular_ranks", {}).values()) == {42}
        and set(control.get("modular_nullities", {}).values()) == {37}
        and control.get("onsite_axis_a_witness_count") == 6
        and control.get("onsite_axis_a_commutes_count") == 6
        and control.get("onsite_axis_a_in_span_count") == 6
    )
    forbidden = contract["claim_boundary"]["forbidden"]
    claims_checked = bool(
        main.get("claims", {}).get("scientific_promotion_accepted") is False
        and main.get("claims", {}).get("new_credit_delta") == 0
        and all(main.get("claims", {}).get(claim) is False for claim in forbidden)
    )
    audit_checked = bool(
        audit.get("status") == "pass"
        and audit.get("error_count") == 0
        and audit.get("errors") == []
        and audit.get("rebuilt_row_count") == 186
        and audit.get("third_and_fourth_prime_full_rank_grid_count") == 186
        and audit.get("grid_shape")
        == {"missing_count": 0, "extra_count": 0, "duplicate_count": 0}
        and audit.get("source_result", {}).get("payload_round_trip_verified") is True
        and audit.get("pre_source_seal", {}).get("expected_grid_keys_sha256")
        == EXPECTED_GRID_KEYS_SHA256
        and audit.get("pre_source_seal", {}).get("anti_circularity", {}).get("checked")
        is True
    )
    runtime_versions = {
        "python": sys.version.split()[0],
        "sympy": importlib.metadata.version("sympy"),
    }
    requirements = [
        requirement(
            "A1",
            "The main result survives canonical JSON round-trip verification",
            bool(
                recorded_main_payload == EXPECTED_MAIN_PAYLOAD_SHA256
                and main_round_trip == EXPECTED_MAIN_PAYLOAD_SHA256
                and canonical_hash(main.get("protocol")) == EXPECTED_MAIN_PROTOCOL_SHA256
                and main.get("protocol_hash") == EXPECTED_MAIN_PROTOCOL_SHA256
            ),
            {
                "recorded_payload_sha256": recorded_main_payload,
                "round_trip_sha256": main_round_trip,
                "recorded_protocol_sha256": main.get("protocol_hash"),
            },
        ),
        requirement(
            "A2",
            "The published contract and protocol retain their frozen digests",
            bool(
                file_hash(contract_path) == EXPECTED_CONTRACT_SHA256
                and main.get("protocol", {}).get("contract", {}).get("sha256")
                == EXPECTED_CONTRACT_SHA256
            ),
            {
                "contract_sha256": file_hash(contract_path),
                "expected_contract_sha256": EXPECTED_CONTRACT_SHA256,
            },
        ),
        requirement(
            "A3",
            "The preregistration commit is present in the fetched public main history",
            history["checked"],
            history,
        ),
        requirement(
            "A4",
            "Atlas and projective metadata pass exact algebra and gauge checks",
            metadata["checked"],
            metadata,
        ),
        requirement(
            "A5",
            "All 186 grid rows have exact keys, metadata, and cross-implementation hashes",
            grid["checked"],
            grid,
        ),
        requirement(
            "A6",
            "The frozen independent dual-prime audit passes without errors",
            audit_checked,
            {
                "status": audit.get("status"),
                "rebuilt_row_count": audit.get("rebuilt_row_count"),
                "full_rank_row_count": audit.get("third_and_fourth_prime_full_rank_grid_count"),
                "grid_shape": audit.get("grid_shape"),
                "error_count": audit.get("error_count"),
            },
        ),
        requirement(
            "A7",
            "The positive control recovers the declared ranks and six onsite charges",
            control_checked,
            {
                "operator_ranks": control.get("operator_basis_modular_ranks"),
                "commutator_ranks": control.get("modular_ranks"),
                "nullities": control.get("modular_nullities"),
                "onsite_witness_count": control.get("onsite_axis_a_witness_count"),
            },
        ),
        requirement(
            "A8",
            "Every main gate passes while broad scientific promotion remains disabled",
            bool(
                len(main.get("requirements", [])) == 13
                and all(item.get("passed") for item in main.get("requirements", []))
                and claims_checked
            ),
            {
                "main_requirement_pass_count": sum(
                    bool(item.get("passed")) for item in main.get("requirements", [])
                ),
                "main_requirement_count": len(main.get("requirements", [])),
                "forbidden_claim_count": len(forbidden),
                "scientific_promotion_accepted": main.get("claims", {}).get("scientific_promotion_accepted"),
                "new_credit_delta": main.get("claims", {}).get("new_credit_delta"),
            },
        ),
        requirement(
            "A9",
            "All four modular rank fields use distinct verified primes",
            bool(
                set(MAIN_PRIMES).isdisjoint(AUDIT_PRIMES)
                and all(prime_checked(value) for value in MAIN_PRIMES + AUDIT_PRIMES)
            ),
            {"main_primes": list(MAIN_PRIMES), "audit_primes": list(AUDIT_PRIMES)},
        ),
        requirement(
            "A10",
            "The required Python and SymPy runtime versions are recorded",
            bool(
                set(contract["code_freeze"]["runtime_versions_recorded"])
                == set(runtime_versions)
                and all(runtime_versions.values())
            ),
            runtime_versions,
        ),
    ]
    all_passed = all(item["passed"] for item in requirements)
    result: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "method": METHOD,
        "version": VERSION,
        "adjudication_type": "post_result_integration_gate_not_preregistered",
        "status": (
            "independently_reproduced_finite_projective_rational_atlas_boundary"
            if all_passed
            else "r200_integrated_adjudication_failed"
        ),
        "source_artifacts": {
            "main_result": str(main_path.relative_to(root)),
            "main_result_file_sha256": file_hash(main_path),
            "main_payload_sha256": recorded_main_payload,
            "independent_audit": str(audit_path.relative_to(root)),
            "independent_audit_file_sha256": file_hash(audit_path),
            "contract": str(contract_path.relative_to(root)),
            "contract_sha256": file_hash(contract_path),
        },
        "public_history": history,
        "runtime_versions": runtime_versions,
        "summary": {
            "main_full_rank_rows": main.get("summary", {}).get("grid_pass_count"),
            "independent_full_rank_rows": audit.get("third_and_fourth_prime_full_rank_grid_count"),
            "projective_axis_count": metadata["projective_row_count"],
            "opposite_representative_count": metadata["opposite_representative_count"],
            "requirement_pass_count": sum(item["passed"] for item in requirements),
            "requirement_count": len(requirements),
            "independent_error_count": audit.get("error_count"),
        },
        "requirements": requirements,
        "claim_boundary": {
            "accepted": [
                "finite_31_axis_projective_catalog_full_rank_at_n6_n8_n10_for_two_frozen_couplings",
                "independent_dual_prime_reproduction_of_all_186_declared_rows",
            ] if all_passed else [],
            "not_established": forbidden,
            "continuous_two_parameter_certificate": False,
            "shared_catalog_formula_risk_eliminated": False,
            "gauge_equivalence_proved_for_all_sizes_and_primes": False,
            "scientific_promotion_accepted": False,
            "new_credit_delta": 0,
        },
        "next_gate": (
            "Build an exact continuous two-parameter projective-patch certificate at n=4, "
            "then promote to n=5 only after the n=4 complex or real projective rank-drop set is resolved."
        ),
    }
    result["payload_sha256"] = canonical_hash(result)
    return result


def render_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    return "\n".join(
        [
            "# B9 R200 Integrated Adjudication",
            "",
            f"- Status: `{result['status']}`",
            f"- Main full-rank rows: `{summary['main_full_rank_rows']}/186`",
            f"- Independent full-rank rows: `{summary['independent_full_rank_rows']}/186`",
            f"- Integrated requirements: `{summary['requirement_pass_count']}/{summary['requirement_count']}`",
            f"- Independent errors: `{summary['independent_error_count']}`",
            f"- Payload SHA256: `{result['payload_sha256']}`",
            "- Scientific promotion: `false`",
            "- New credit delta: `0`",
            "",
            "## What Is Supported",
            "",
            "Two frozen couplings, three finite sizes, and 31 exact projective parity axes produce "
            "186/186 full-column-rank rows in the main implementation. A non-importing sparse "
            "symplectic implementation independently rebuilds all 186 rows under two additional "
            "primes with zero missing, extra, duplicate, hash-mismatch, or rank-failure rows.",
            "",
            "## Why This Does Not Require Quantum Hardware",
            "",
            "R200 is an exact algebraic obstruction test on a declared finite operator family. "
            "Its rank statements are classical symbolic and modular-linear-algebra claims. "
            "A full-column-rank witness modulo a prime proves full column rank over the underlying "
            "integer or rational matrix. Quantum hardware would be required for device behavior, "
            "noise, calibration, sampling advantage, or hardware-relevance claims, none of which "
            "R200 makes.",
            "",
            "## Residual Risk",
            "",
            "The main and independent implementations use separate Pauli representations, but "
            "they share the declared atlas formulas. The finite gauge sentinels do not prove a "
            "global continuous frame theorem. R200 therefore does not exclude irrational axes, "
            "nonlinear frame mixtures, higher-order Majorana charges, nonlocal dualities, or "
            "interacting integrability.",
            "",
            "## Next Gate",
            "",
            result["next_gate"],
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--main-result", type=Path, default=Path("results/B9_R200_bloch_atlas_stress_v1.json"))
    parser.add_argument("--independent-audit", type=Path, default=Path("results/B9_R200_independent_audit_v1.json"))
    parser.add_argument("--contract", type=Path, default=Path("benchmarks/B9_R200_bloch_atlas_contract_v0.json"))
    parser.add_argument("--output", type=Path, default=Path("results/B9_R200_integrated_adjudication_v1.json"))
    parser.add_argument("--report", type=Path, default=Path("research/B9_R200_integrated_adjudication.md"))
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    resolve = lambda path: path if path.is_absolute() else root / path
    result = build_result(
        root,
        resolve(args.main_result),
        resolve(args.independent_audit),
        resolve(args.contract),
    )
    output = resolve(args.output)
    report = resolve(args.report)
    output.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2 if args.pretty else None, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report.write_text(render_report(result), encoding="utf-8")
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if all(item["passed"] for item in result["requirements"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
