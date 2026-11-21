#!/usr/bin/env python3
"""Build a replayable, normalized patch for the phase-aware RTL experiment."""

from __future__ import annotations

import argparse
import difflib
import hashlib
from pathlib import Path


FILES = (
    "src/fpga/microblossom/DualConfig.scala",
    "src/fpga/microblossom/types/BroadcastMessage.scala",
    "src/fpga/microblossom/modules/DistributedDual.scala",
    "src/fpga/microblossom/modules/Edge.scala",
    "src/fpga/microblossom/modules/Vertex.scala",
    "src/fpga/microblossom/modules/MicroBlossomLooper.scala",
    "src/fpga/microblossom/DualHost.scala",
    "src/cpu/blossom/Cargo.toml",
    "src/cpu/blossom/src/dual_module_scala.rs",
    "src/cpu/blossom/src/dual_module_comb.rs",
    "src/cpu/blossom/src/mwpm_solver.rs",
    "src/cpu/blossom/src/bin/d6_x_phase_primal_dual.rs",
    "src/cpu/blossom/src/bin/d6_x_phase_primal_dual_comb.rs",
)


def lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--modified", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    chunks: list[str] = []
    changed: list[str] = []
    for relative in FILES:
        before_path = args.original / relative
        after_path = args.modified / relative
        before = lines(before_path)
        after = lines(after_path)
        if before == after:
            continue
        changed.append(relative)
        chunks.extend(
            difflib.unified_diff(
                before,
                after,
                fromfile=f"a/{relative}" if before_path.exists() else "/dev/null",
                tofile=f"b/{relative}",
                n=3,
            )
        )

    payload = "".join(chunks)
    if not payload:
        raise SystemExit("no selected source changes")
    args.output.write_text(payload, encoding="utf-8")
    digest = hashlib.sha256(payload.encode()).hexdigest()
    print(f"files={len(changed)} sha256={digest}")
    for relative in changed:
        print(relative)


if __name__ == "__main__":
    main()
