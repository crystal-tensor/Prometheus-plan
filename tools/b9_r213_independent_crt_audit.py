#!/usr/bin/env python3
"""Independently audit the fifth completed R209 CRT prime shard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import b9_r210_independent_crt_audit as prefix_audit


VERSION = "0.1.0"
METHOD = "b9_r213_independent_prefix_matrix_and_sympy_CRT_audit_v1"
REPLAY_PATH = Path("results/B9_R213_crt_shard5_replay_v0.json")


def analyze(root: Path) -> dict:
    # The R210 implementation is prefix-generic. Keep it immutable and bind this
    # entry point to the R213 replay artifact before executing the full audit.
    prefix_audit.VERSION = VERSION
    prefix_audit.METHOD = METHOD
    prefix_audit.REPLAY_PATH = REPLAY_PATH
    result = prefix_audit.analyze(root)
    result["scope"] = "public_R213_independent_completed_prefix_audit_only"

    stable_payload = dict(result)
    stable_payload.pop("stable_payload_sha256", None)
    stable_payload.pop("payload_sha256", None)
    result["stable_payload_sha256"] = prefix_audit.prior.canonical_hash(
        stable_payload
    )
    payload_without_hash = dict(result)
    payload_without_hash.pop("payload_sha256", None)
    result["payload_sha256"] = prefix_audit.prior.canonical_hash(
        payload_without_hash
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    result = analyze(root)
    output = args.output if args.output.is_absolute() else root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "output": str(output),
                "checked": result["checked"],
                "completed_new_primes": len(result["new_primes"]),
                "matrix_replays": result["matrix_replay_count"],
                "matrix_matches": result["matrix_replay_match_count"],
                "D44_matches": result["D44_recomposition_match_count"],
                "CRT_roundtrips": result[
                    "total_independent_CRT_roundtrip_check_count"
                ],
                "new_credit_delta": result["new_credit_delta"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["checked"] else 1


if __name__ == "__main__":
    sys.exit(main())
