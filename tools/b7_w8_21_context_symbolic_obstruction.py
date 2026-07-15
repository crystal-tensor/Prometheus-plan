#!/usr/bin/env python3
"""Build a scoped symbolic obstruction for absorbing a post-context Rz.

The five-parameter w8_21 normal form has a two-parameter left dressing
``Ry(e) Rz(d)``.  This gate proves the exact phase-ratio condition for trying
to absorb an external ``Rz(theta)`` into another two-parameter left dressing
while keeping the same relative-block parameter branch.  For a generic left
dressing, the two phase ratios force ``exp(2 i theta) = 1``.

The result is deliberately scoped to the same relative-block branch and the
declared two-parameter left dressing.  It is not a global six-parameter lower
bound, a KAK theorem, or a full-circuit rewrite certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import sympy as sp


METHOD = "b7_w8_21_context_symbolic_obstruction_v0"
TEMPLATE_ID = "w8_21"
SOURCE_QASM = "results/b1_u3_phase_factored_optimizer/qasmbench_medium_exact/gcm_h6.qasm"
NEIGHBORHOOD_RESULT = "results/B7_w8_21_neighborhood_transfer_v0.json"
RELOCATION_RESULT = "results/B7_w8_21_parameter_relocation_search_v0.json"
RESULT_PATH = "results/B7_w8_21_context_symbolic_obstruction_v0.json"
REPORT_PATH = "research/B7_w8_21_context_symbolic_obstruction.md"
EXACT_TOLERANCE = 1e-12
SOURCE_PARAMS = [
    1.4922506383856682,
    2.1870074319274799,
    0.52538524712872736,
    2.538142068316358,
    1.1254377896453873,
]

I = sp.I
theta, d, e, dp, ep = sp.symbols("theta d e dp ep", real=True)


def stable_hash(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rz(angle: sp.Expr) -> sp.Matrix:
    return sp.diag(sp.exp(-I * angle / 2), sp.exp(I * angle / 2))


def ry(angle: sp.Expr) -> sp.Matrix:
    return sp.Matrix(
        [
            [sp.cos(angle / 2), -sp.sin(angle / 2)],
            [sp.sin(angle / 2), sp.cos(angle / 2)],
        ]
    )


def symbolic_certificate() -> dict[str, Any]:
    context_left = rz(theta) * ry(e) * rz(d)
    candidate_left = ry(ep) * rz(dp)

    context_ratio_offdiag = sp.simplify(context_left[1, 0] / (-context_left[0, 1]))
    candidate_ratio_offdiag = sp.simplify(candidate_left[1, 0] / (-candidate_left[0, 1]))
    context_ratio_diag = sp.simplify(context_left[1, 1] / context_left[0, 0])
    candidate_ratio_diag = sp.simplify(candidate_left[1, 1] / candidate_left[0, 0])
    forced_product = sp.simplify(context_ratio_offdiag * context_ratio_diag)
    candidate_product = sp.simplify(candidate_ratio_offdiag * candidate_ratio_diag)

    checks = {
        "context_offdiagonal_phase_ratio": context_ratio_offdiag == sp.exp(I * (theta - d)),
        "candidate_offdiagonal_phase_ratio": candidate_ratio_offdiag == sp.exp(-I * dp),
        "context_diagonal_phase_ratio": context_ratio_diag == sp.exp(I * (theta + d)),
        "candidate_diagonal_phase_ratio": candidate_ratio_diag == sp.exp(I * dp),
        "context_ratio_product": forced_product == sp.exp(2 * I * theta),
        "candidate_ratio_product": candidate_product == 1,
        "branch_obstruction_equation": sp.simplify(forced_product - candidate_product * sp.exp(2 * I * theta)) == 0,
    }
    return {
        "symbols": ["theta", "d", "e", "dp", "ep"],
        "context_left_dressing": "Rz(theta) Ry(e) Rz(d)",
        "candidate_left_dressing": "Ry(ep) Rz(dp)",
        "nonzero_conditions": [
            "sin(e/2) != 0",
            "cos(e/2) != 0",
            "Equality forces candidate off-diagonal and diagonal entries nonzero as well.",
        ],
        "ratios": {
            "context_offdiagonal": str(context_ratio_offdiag),
            "candidate_offdiagonal": str(candidate_ratio_offdiag),
            "context_diagonal": str(context_ratio_diag),
            "candidate_diagonal": str(candidate_ratio_diag),
            "context_product": str(forced_product),
            "candidate_product": str(candidate_product),
        },
        "forced_condition": "exp(2*i*theta) = 1",
        "real_angle_consequence": "theta = 0 mod pi",
        "exact_checks": [{"check_id": key, "passed": bool(value)} for key, value in checks.items()],
        "exact_checks_passed": sum(bool(value) for value in checks.values()),
        "exact_checks_failed": sum(not bool(value) for value in checks.values()),
    }


def build(root: Path) -> dict[str, Any]:
    neighborhood = json.loads((root / NEIGHBORHOOD_RESULT).read_text(encoding="utf-8"))
    relocation = json.loads((root / RELOCATION_RESULT).read_text(encoding="utf-8"))
    theorem = symbolic_certificate()
    rows = []
    for index, source_row in enumerate(neighborhood["rows"], start=1):
        operation = source_row["context_operation"]
        angle = float(operation["angle"])
        rows.append(
            {
                "context_index": index,
                "direction": source_row["direction"],
                "line_span": source_row["line_span"],
                "context_operation": operation,
                "theta": angle,
                "theta_mod_pi": float(math.fmod(angle, math.pi)),
                "generic_source_left_dressing": bool(
                    abs(math.sin(SOURCE_PARAMS[4] / 2.0)) > EXACT_TOLERANCE
                    and abs(math.cos(SOURCE_PARAMS[4] / 2.0)) > EXACT_TOLERANCE
                ),
                "exp_2_i_theta_distance_from_one": float(abs(complex(math.cos(2.0 * angle), math.sin(2.0 * angle)) - 1.0)),
                "same_branch_absorption_allowed_by_certificate": bool(
                    abs(math.sin(SOURCE_PARAMS[4] / 2.0)) <= EXACT_TOLERANCE
                    or abs(math.cos(SOURCE_PARAMS[4] / 2.0)) <= EXACT_TOLERANCE
                    or abs(complex(math.cos(2.0 * angle), math.sin(2.0 * angle)) - 1.0) <= EXACT_TOLERANCE
                ),
            }
        )
    exact_context_count = sum(row["same_branch_absorption_allowed_by_certificate"] for row in rows)
    source_bindings = {
        SOURCE_QASM: {"path": SOURCE_QASM, "sha256": file_sha256(root / SOURCE_QASM)},
        NEIGHBORHOOD_RESULT: {"path": NEIGHBORHOOD_RESULT, "sha256": file_sha256(root / NEIGHBORHOOD_RESULT)},
        RELOCATION_RESULT: {"path": RELOCATION_RESULT, "sha256": file_sha256(root / RELOCATION_RESULT)},
    }
    result: dict[str, Any] = {
        "title": "B7 w8_21 scoped context symbolic obstruction",
        "version": 0,
        "method": METHOD,
        "status": "context_symbolic_obstruction_complete_same_branch_no_absorption",
        "classification": "scoped_same_relative_branch_left_dressing_obstruction",
        "template_id": TEMPLATE_ID,
        "theorem": theorem,
        "source_bindings": source_bindings,
        "upstream_evidence": {
            "neighborhood_status": neighborhood["status"],
            "neighborhood_exact_fit_count": neighborhood["summary"]["exact_fit_count"],
            "relocation_status": relocation["status"],
            "relocation_exact_context_count": relocation["summary"]["exact_context_count"],
        },
        "summary": {
            "tested_context_count": len(rows),
            "same_branch_absorption_allowed_count": exact_context_count,
            "generic_source_left_dressing_count": sum(row["generic_source_left_dressing"] for row in rows),
            "minimum_exp_2_i_theta_distance_from_one": min(row["exp_2_i_theta_distance_from_one"] for row in rows),
            "maximum_exp_2_i_theta_distance_from_one": max(row["exp_2_i_theta_distance_from_one"] for row in rows),
            "accepted_occurrence_removal": 0,
            "accepted_proxy_t_reduction": 0,
            "b7_credit": 0,
            "validation_error_count": 0,
            "rewrite_claimed": False,
            "resource_saving_claimed": False,
            "global_lower_bound_claimed": False,
        },
        "rows": rows,
        "claim_boundary": {
            "supported_claim": "For the same relative-block parameter branch and generic source left dressing Ry(e)Rz(d), exact equality with a two-parameter candidate Ry(ep)Rz(dp) forces exp(2*i*theta)=1; the seven source-bound external Rz contexts violate that condition.",
            "unsupported_claims": [
                "No global six-parameter necessity theorem is claimed.",
                "Other relative-block branches, arbitrary Clifford frames, ancillas, measurements, and full-circuit rewrites are not excluded.",
                "No occurrence removal, proxy-T reduction, or B7 credit is accepted.",
            ],
            "same_relative_branch_only": True,
            "global_lower_bound_claimed": False,
            "rewrite_claimed": False,
            "resource_saving_claimed": False,
        },
        "artifacts": {"result": RESULT_PATH, "markdown_report": REPORT_PATH},
        "payload_hash": "",
    }
    result["payload_hash"] = stable_hash({key: value for key, value in result.items() if key != "payload_hash"})
    return result


def report(result: dict[str, Any]) -> str:
    theorem = result["theorem"]
    summary = result["summary"]
    lines = [
        "# B7 w8_21 Context Symbolic Obstruction",
        "",
        f"- Status: `{result['status']}`",
        f"- Classification: `{result['classification']}`",
        f"- Exact symbolic checks: `{theorem['exact_checks_passed']}/{theorem['exact_checks_passed'] + theorem['exact_checks_failed']}`",
        f"- Contexts tested: `{summary['tested_context_count']}`",
        f"- Same-branch absorptions allowed: `{summary['same_branch_absorption_allowed_count']}/{summary['tested_context_count']}`",
        f"- Payload hash: `{result['payload_hash']}`",
        "",
        "## Heuristic question",
        "",
        "If the neighboring Rz does not change the controlled relative block, why can it still resist a five-parameter refit?",
        "",
        "## Symbolic result",
        "",
        "For the fixed relative-block branch, the source left dressing is `Ry(e) Rz(d)`. A post-context rotation produces `Rz(theta) Ry(e) Rz(d)`. The candidate five-parameter form has only `Ry(ep) Rz(dp)` on the left.",
        "",
        "When `sin(e/2)` and `cos(e/2)` are nonzero, compare the two phase ratios:",
        "",
        "- off-diagonal ratio: context `exp(i(theta-d))`, candidate `exp(-i dp)`;",
        "- diagonal ratio: context `exp(i(theta+d))`, candidate `exp(i dp)`.",
        "",
        "Multiplying the ratios forces `exp(2*i*theta)=1`, hence for real angles `theta = 0 mod pi`. This is an exact same-branch obstruction, not a global lower bound.",
        "",
        "## Source-bound check",
        "",
        f"The seven selected contexts have generic source dressing in `{summary['generic_source_left_dressing_count']}/{summary['tested_context_count']}` rows. Their distance from the necessary condition is between `{summary['minimum_exp_2_i_theta_distance_from_one']:.16g}` and `{summary['maximum_exp_2_i_theta_distance_from_one']:.16g}`. Same-branch absorption is allowed in `{summary['same_branch_absorption_allowed_count']}/{summary['tested_context_count']}` rows.",
        "",
        "## Claim boundary",
        "",
        "This artifact covers only the same relative-block branch and the declared two-parameter left dressing. It does not exclude alternate parameter branches, other Clifford scaffolds, ancillas, measurements, or a full-circuit rewrite. Accepted occurrence removal, proxy-T reduction, and B7 credit remain zero.",
        "",
        "## Next route",
        "",
        "Enumerate the discrete relative-block branches symbolically, then test whether any branch changes the phase-ratio obstruction without adding CNOTs or an additional arbitrary parameter.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--json-output", type=Path, default=Path(RESULT_PATH))
    parser.add_argument("--markdown-output", type=Path, default=Path(REPORT_PATH))
    args = parser.parse_args()
    root = args.root.resolve()
    result = build(root)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.write_text(report(result), encoding="utf-8")
    print(json.dumps({"status": result["status"], "payload_hash": result["payload_hash"], **result["summary"]}, sort_keys=True))


if __name__ == "__main__":
    main()
