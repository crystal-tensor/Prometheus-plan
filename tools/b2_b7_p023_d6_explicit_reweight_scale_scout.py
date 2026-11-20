#!/usr/bin/env python3
"""Post-outcome fixed-point scale scout for B2/B7/#023.

This diagnostic deliberately reuses the already-public v1 holdout.  It can
select a later preregistered candidate, but it is never acceptance evidence.
Progress goes to stderr so stdout remains one canonical JSON document.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import numpy as np

import b2_b7_p023_d6_explicit_reweight as explicit


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "results/B2_B7_P023_d6_explicit_reweight_v1.json"


def scout_basis(
    source: dict[str, Any], basis: str, half_weight_scale: int
) -> dict[str, Any]:
    corpus = next(row for row in source["corpora"] if row["basis"] == basis)
    source_row = next(row for row in source["basis_rows"] if row["basis"] == basis)
    shots = int(corpus["shots"])
    circuit, compiled, windows, structural = explicit.compile_basis(
        basis, half_weight_scale
    )
    if not structural["explicit_rule_adapter_active"]:
        raise RuntimeError(
            "pinned explicit-rule adapter is required; refusing fallback execution"
        )
    sampler = circuit.compile_detector_sampler(seed=int(corpus["seed"]))
    detectors_packed, observables_packed = sampler.sample(
        shots, separate_observables=True, bit_packed=True
    )
    corpus_header = {
        "basis": basis,
        "shots": shots,
        "seed": int(corpus["seed"]),
        "seed_digest_sha256": corpus["seed_digest_sha256"],
        "detector_shape": list(detectors_packed.shape),
        "observable_shape": list(observables_packed.shape),
    }
    reproduced_corpus_sha256 = explicit.sha_bytes(
        explicit.compact(corpus_header)
        + b"\x00"
        + detectors_packed.tobytes(order="C")
        + observables_packed.tobytes(order="C")
    )
    if reproduced_corpus_sha256 != corpus["corpus_sha256"]:
        raise ValueError(f"public {basis} corpus did not reproduce")
    raw_syndromes = np.unpackbits(
        detectors_packed,
        axis=1,
        count=circuit.num_detectors,
        bitorder="little",
    ).astype(np.uint8, copy=False)
    equal_frames = 0
    window_outputs_equal = 0
    window_syndromes_equal = 0
    reference_commit_failures = 0
    candidate_commit_failures = 0
    reference_final_failures = 0
    candidate_final_failures = 0
    for shot_index, syndrome in enumerate(raw_syndromes):
        row = explicit.decode_online_pair(compiled, windows, syndrome)
        equal_frames += int(
            np.array_equal(row["reference_frame"], row["candidate_frame"])
        )
        window_outputs_equal += int(row["window_outputs_equal"])
        window_syndromes_equal += int(row["window_syndromes_equal"])
        reference_commit_failures += int(row["reference_commit_failures"])
        candidate_commit_failures += int(row["candidate_commit_failures"])
        reference_final_failures += int(row["reference_final_residual_weight"] > 0)
        candidate_final_failures += int(row["candidate_final_residual_weight"] > 0)
        if (shot_index + 1) % 128 == 0:
            print(
                f"{basis}: scale {half_weight_scale} "
                f"{shot_index + 1}/{shots}",
                file=sys.stderr,
                flush=True,
            )
    observations = shots * len(windows)
    exact = bool(
        equal_frames == shots
        and window_outputs_equal == observations
        and window_syndromes_equal == observations
        and reference_commit_failures == 0
        and candidate_commit_failures == 0
        and reference_final_failures == 0
        and candidate_final_failures == 0
    )
    return {
        "basis": basis,
        "shots": shots,
        "source_public_corpus_sha256": corpus["corpus_sha256"],
        "reproduced_public_corpus_sha256": reproduced_corpus_sha256,
        "source_scale_16_window_syndrome_mismatches": (
            int(source_row["window_observations"])
            - int(source_row["window_syndromes_equal"])
        ),
        "source_scale_16_window_output_mismatches": (
            int(source_row["window_observations"])
            - int(source_row["window_outputs_equal"])
        ),
        "candidate_frames_equal_reference": equal_frames,
        "window_observations": observations,
        "window_syndromes_equal": window_syndromes_equal,
        "window_syndrome_mismatches": observations - window_syndromes_equal,
        "window_outputs_equal": window_outputs_equal,
        "window_output_mismatches": observations - window_outputs_equal,
        "reference_commit_failures": reference_commit_failures,
        "candidate_commit_failures": candidate_commit_failures,
        "reference_final_failure_shots": reference_final_failures,
        "candidate_final_failure_shots": candidate_final_failures,
        "strict_observed_corpus_equality": exact,
        "structural": structural,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--half-weight-scale", type=int, required=True)
    parser.add_argument("--basis", choices=("x", "z", "both"), default="both")
    args = parser.parse_args()
    if args.half_weight_scale <= 0:
        raise SystemExit("--half-weight-scale must be positive")
    source = explicit.read(args.source)
    bases = ["x", "z"] if args.basis == "both" else [args.basis]
    rows = [scout_basis(source, basis, args.half_weight_scale) for basis in bases]
    result = {
        "schema_version": "b2_b7_p023_d6_explicit_reweight_scale_scout_v1",
        "scope": source["scope"],
        "source_result": {
            "path": str(args.source.resolve().relative_to(ROOT)),
            "sha256": explicit.sha_path(args.source),
            "evidence_id": source["evidence_id"],
            "public_freeze": source["public_freeze"],
        },
        "epistemic_status": (
            "post-outcome route selection on an already-public failed holdout; "
            "not preregistered acceptance evidence"
        ),
        "half_weight_scale": args.half_weight_scale,
        "stored_even_weight_scale": 2 * args.half_weight_scale,
        "rows": rows,
        "strict_observed_corpus_equality": all(
            row["strict_observed_corpus_equality"] for row in rows
        ),
        "next_evidence_rule": (
            "Any selected scale must be frozen in a new public commit and "
            "Discussion before deriving new X/Z seeds."
        ),
    }
    result["evidence_id"] = explicit.sha_bytes(explicit.compact(result))
    print(explicit.canonical(result), end="")


if __name__ == "__main__":
    main()
