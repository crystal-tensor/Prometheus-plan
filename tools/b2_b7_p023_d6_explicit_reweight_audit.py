#!/usr/bin/env python3
"""Independent protocol adjudication for the explicit-reweight holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "benchmarks/B2_B7_P023_d6_explicit_reweight_v1.json"
DEFAULT_RESULT = ROOT / "results/B2_B7_P023_d6_explicit_reweight_v1.json"
DEFAULT_OUTPUT = ROOT / "results/B2_B7_P023_d6_explicit_reweight_audit_v1.json"
DEFAULT_REPORT = ROOT / "research/B2_B7_P023_d6_explicit_reweight_adjudication_v1.md"
DEFAULT_DISCUSSION = (
    ROOT / "research/B2_B7_P023_d6_explicit_reweight_adjudication_discussion_v1.md"
)


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compact(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_path(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def git_blob(commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def seed_for(commit: str, discussion: int, namespace: str, basis: str) -> int:
    digest = hashlib.sha256(
        f"{commit}:{discussion}:{namespace}:{basis}".encode()
    ).digest()
    return int.from_bytes(digest[:8], "little")


def audit_check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def build_audit(
    protocol: dict[str, Any],
    result: dict[str, Any],
    protocol_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    freeze = result["public_freeze"]
    commit = freeze["commit"]
    discussion = int(freeze["discussion_number"])
    namespace = protocol["fresh_holdout_contract"]["seed_namespace"]
    expected_windows = int(protocol["fresh_holdout_contract"]["shots_per_basis"]) * 164
    rows = {row["basis"]: row for row in result["basis_rows"]}
    corpora = {row["basis"]: row for row in result["corpora"]}
    deficits: dict[str, Any] = {}
    final_frame_gate = True
    residual_gate = True
    window_gate = True
    width_gate = True
    for basis in ("x", "z"):
        row = rows[basis]
        structural = row["structural"]
        deficits[basis] = {
            "window_observations": expected_windows,
            "window_syndrome_mismatches": expected_windows
            - row["window_syndromes_equal"],
            "window_output_mismatches": expected_windows - row["window_outputs_equal"],
            "candidate_final_frame_mismatches": row["shots"]
            - row["candidate_prediction_rows_equal_reference_online"],
            "reference_full_block_mismatches": row["shots"]
            - row["reference_online_prediction_rows_equal_full_block"],
        }
        final_frame_gate &= bool(
            row["candidate_prediction_rows_equal_reference_online"] == row["shots"]
            and row["reference_online_prediction_rows_equal_full_block"]
            == row["shots"]
            and row["candidate_prediction_rows_equal_full_block"] == row["shots"]
        )
        residual_gate &= bool(
            row["reference_commit_residual_failures"] == 0
            and row["candidate_commit_residual_failures"] == 0
            and row["reference_final_residual_failure_shots"] == 0
            and row["candidate_final_residual_failure_shots"] == 0
        )
        window_gate &= bool(
            row["window_syndromes_equal"] == expected_windows
            and row["window_outputs_equal"] == expected_windows
        )
        width_gate &= bool(
            structural["base_even_weights_all_even"]
            and structural["base_even_weight_bits"] <= 9
            and structural["implied_even_weight_max"] <= 511
        )
    semantic_veto_pass = final_frame_gate and residual_gate and window_gate
    if not semantic_veto_pass:
        adjudicated = "fresh_holdout_explicit_reweight_semantic_regression"
    elif not width_gate:
        adjudicated = "nine_bit_even_representation_failure"
    else:
        adjudicated = (
            "nine_bit_explicit_reweight_semantic_pass_hardware_write_path_absent"
        )
    producer = result["classification"]
    patch_path = protocol["adapter_contract"]["patch"]["path"]
    runner_path = result["protocol_binding"]["runner_path"]
    protocol_rel = str(protocol_path.resolve().relative_to(ROOT))
    result_sha = sha_path(result_path)
    checks = [
        audit_check("scope", result["scope"]["included_catalog_problem_ids"] == [21, 22, 23], "Exact #021/#022/#023 scope."),
        audit_check("freeze_commit", len(commit) == 40 and discussion == 339, f"{commit} / Discussion {discussion}."),
        audit_check("protocol_commit_binding", sha_bytes(git_blob(commit, protocol_rel)) == sha_path(protocol_path), "Protocol bytes match public freeze."),
        audit_check("runner_commit_binding", sha_bytes(git_blob(commit, runner_path)) == result["protocol_binding"]["runner_sha256"], "Runner bytes match public freeze."),
        audit_check("patch_commit_binding", sha_bytes(git_blob(commit, patch_path)) == protocol["adapter_contract"]["patch"]["sha256"], "Adapter patch bytes match public freeze."),
        audit_check("result_hash", len(result_sha) == 64, result_sha),
        audit_check("basis_rows", sorted(rows) == ["x", "z"], "Both bases are present."),
        audit_check("corpus_rows", sorted(corpora) == ["x", "z"], "Both fresh corpora are present."),
        audit_check("seed_x", corpora["x"]["seed"] == seed_for(commit, discussion, namespace, "x"), str(corpora["x"]["seed"])),
        audit_check("seed_z", corpora["z"]["seed"] == seed_for(commit, discussion, namespace, "z"), str(corpora["z"]["seed"])),
        audit_check("fresh_shots", all(rows[basis]["shots"] == 1024 for basis in ("x", "z")), "1,024 fresh shots per basis."),
        audit_check("final_frame_gate_recomputed", final_frame_gate, "All 2,048 final candidate/reference/full-block rows agree."),
        audit_check("residual_gate_recomputed", residual_gate, "All commit and final residual counts are zero."),
        audit_check("width_gate_recomputed", width_gate, "Every stored base and implied weight fits unsigned nine-bit even representation."),
        audit_check("window_veto_is_false", not window_gate, f"X syndrome/output mismatches {deficits['x']['window_syndrome_mismatches']}/{deficits['x']['window_output_mismatches']}; Z {deficits['z']['window_syndrome_mismatches']}/{deficits['z']['window_output_mismatches']}."),
        audit_check("semantic_veto_is_false", not semantic_veto_pass, "Frozen all-window equality requirement fails."),
        audit_check("adjudicated_classification", adjudicated == protocol["classification_rule"]["order"][0], adjudicated),
        audit_check("producer_misclassification_detected", producer != adjudicated, f"producer={producer}; adjudicated={adjudicated}"),
        audit_check("hardware_boundary", not result["verdict"]["hardware_decoder_deadline_passed"] and not result["verdict"]["full_b2_credit_ready"] and not result["verdict"]["p023_scalable_memory_ready"] and result["verdict"]["b7_resource_credit"] == 0, "Hardware/downstream credit remains false/zero."),
    ]
    audit: dict[str, Any] = {
        "schema_version": "b2_b7_p023_d6_explicit_reweight_audit_v1",
        "scope": result["scope"],
        "protocol": {"path": protocol_rel, "sha256": sha_path(protocol_path)},
        "result": {"path": str(result_path.resolve().relative_to(ROOT)), "sha256": result_sha},
        "public_freeze": freeze,
        "producer_classification": producer,
        "adjudicated_classification": adjudicated,
        "producer_classification_accepted": False,
        "producer_formal_check_bug": "semantic_pass omitted the protocol's window_syndromes_and_outputs_equal requirement",
        "recomputed_gates": {
            "final_frame_gate_pass": final_frame_gate,
            "residual_gate_pass": residual_gate,
            "window_exactness_gate_pass": window_gate,
            "nine_bit_width_gate_pass": width_gate,
            "semantic_veto_pass": semantic_veto_pass,
        },
        "window_deficits": deficits,
        "claim_boundary": {
            "micro_blossom_dynamic_weight_write_path_implemented": False,
            "hardware_decoder_deadline_passed": False,
            "full_b2_credit_ready": False,
            "p023_scalable_memory_ready": False,
            "b7_resource_credit": 0,
        },
        "checks": checks,
        "summary": {
            "checks_total": len(checks),
            "checks_passed": sum(item["passed"] for item in checks),
            "checks_failed": sum(not item["passed"] for item in checks),
            "producer_classification_accepted": False,
            "adjudicated_semantic_veto_pass": False,
        },
    }
    audit["audit_id"] = sha_bytes(compact(audit))
    if audit["summary"]["checks_failed"]:
        failed = [item["name"] for item in checks if not item["passed"]]
        raise ValueError(f"audit integrity checks failed: {failed}")
    return audit


def render_report(audit: dict[str, Any]) -> str:
    x = audit["window_deficits"]["x"]
    z = audit["window_deficits"]["z"]
    return "\n".join(
        [
            "# B2/B7/#023 explicit 9-bit reweight adjudication v1",
            "",
            "## Decision",
            "",
            f"Accepted classification: `{audit['adjudicated_classification']}`.",
            "",
            f"The producer emitted `{audit['producer_classification']}`, but that label is rejected. Its `semantic_pass` implementation omitted the frozen all-window equality clause.",
            "",
            "## What passed",
            "",
            "All 2,048 final candidate frames equal the high-precision online and full-block references. Every commit and final residual count is zero. All base and implied stored weights are even and fit unsigned nine-bit storage.",
            "",
            "## What failed",
            "",
            f"X has `{x['window_syndrome_mismatches']}` syndrome and `{x['window_output_mismatches']}` output mismatches among `{x['window_observations']}` windows. Z has `{z['window_syndrome_mismatches']}` syndrome and `{z['window_output_mismatches']}` output mismatches. The frozen protocol requires zero in all four cells, so the semantic veto fails.",
            "",
            "## Claim boundary and next gate",
            "",
            "The 9-bit representation is not admitted for the strict window-exact route. No Micro Blossom dynamic-write RTL, cycle, FPGA, p99, full B2, scalable #023, or B7 credit is supported. A wider-grid candidate may be selected only as a disclosed post-outcome diagnostic and must face a new public freeze and new seeds.",
            "",
            f"Independent audit checks: `{audit['summary']['checks_passed']}/{audit['summary']['checks_total']}`. Audit ID: `{audit['audit_id']}`.",
            "",
        ]
    )


def render_discussion(audit: dict[str, Any]) -> str:
    x = audit["window_deficits"]["x"]
    z = audit["window_deficits"]["z"]
    return "\n".join(
        [
            "# If final frames agree, may a real-time decoder disagree 58 times on the way?",
            "",
            "The 9-bit explicit-weight holdout produced a tempting outcome: all 2,048 final X/Z frames agree with the high-precision online and full-block references, and every commit/final residual is zero.",
            "",
            f"But the preregistered contract was stricter. X contains `{x['window_syndrome_mismatches']}` syndrome and `{x['window_output_mismatches']}` window-output mismatches; Z contains `{z['window_syndrome_mismatches']}` and `{z['window_output_mismatches']}`. That is 58 different window corrections even though the final memories resynchronize.",
            "",
            "The frozen runner accidentally omitted this clause from its `semantic_pass` calculation and printed a pass label. An independent adjudicator caught the conflict, rejects the producer label, and applies the first frozen classification: `fresh_holdout_explicit_reweight_semantic_regression`.",
            "",
            "Heuristic question: for a streaming fault-tolerant controller, is final-frame equality enough, or must every committed correction be identical so downstream timing and causal state remain substitutable? If the latter—as this protocol assumed—how much extra precision is the cheapest way to eliminate the 58 transient disagreements?",
            "",
            "No hardware claim survives this veto. A wider candidate must be selected transparently on the now-observed corpus, frozen publicly, and tested on new seeds before any RTL work or B2/#023/B7 credit.",
            "",
            f"Audit ID: `{audit['audit_id']}`.",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--discussion-output", type=Path, default=DEFAULT_DISCUSSION)
    args = parser.parse_args()
    audit = build_audit(
        read(args.protocol), read(args.result), args.protocol, args.result
    )
    args.output.write_text(canonical(audit), encoding="utf-8")
    args.report.write_text(render_report(audit), encoding="utf-8")
    args.discussion_output.write_text(render_discussion(audit), encoding="utf-8")
    print(
        canonical(
            {
                "adjudicated_classification": audit["adjudicated_classification"],
                "audit_id": audit["audit_id"],
                "summary": audit["summary"],
            }
        ),
        end="",
    )


if __name__ == "__main__":
    main()
