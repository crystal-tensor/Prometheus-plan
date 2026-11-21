#!/usr/bin/env python3
"""Persistent frozen PyMatching selector service for closed-loop RTL pilots."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import b2_b7_p023_d6_explicit_reweight_v2 as accepted  # noqa: E402
import b2_b7_p023_d6_microblossom_batch_trace_v1 as trace  # noqa: E402


PLAN = ROOT / "benchmarks/B2_B7_P023_d6_microblossom_phase_superset_plan_v1.json"


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def bits_from_hex(value: str, count: int) -> np.ndarray:
    number = int(value, 16) if value else 0
    return np.fromiter(((number >> bit) & 1 for bit in range(count)), dtype=np.uint8)


def main() -> None:
    source = read(accepted.DEFAULT_RESULT)
    scale = int(source["candidate_contract"]["half_weight_scale"])
    _, compiled, windows, _ = accepted.compile_basis("x", scale)
    plan = read(PLAN)
    x_plan = next(row for row in plan["basis_plans"] if row["basis"] == "x")
    phase_rows = {
        phase: next(row for row in x_plan["phases"] if row["phase"] == phase)
        for phase in ("opening", "steady", "closing")
    }
    print(json.dumps({"ready": True, "windows": len(windows)}), flush=True)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            window_index = int(request["window"])
            if not 0 <= window_index < len(windows):
                raise ValueError("window out of range")
            phase = "opening" if window_index == 0 else "closing" if window_index == 163 else "steady"
            count = len(compiled.windows[window_index].detection_detectors)
            syndrome = bits_from_hex(request["syndrome_hex"], count)
            selected_local, _ = trace.replacement_batch(windows[window_index], syndrome)
            local_to_superset = phase_rows[phase]["local_to_superset_edge"]
            response = {
                "window": window_index,
                "phase": phase,
                "defects": int(np.count_nonzero(syndrome)),
                "selectors": [local_to_superset[index] for index in selected_local],
            }
        except Exception as exc:  # the Rust caller treats any error response as fatal
            response = {"error": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(response, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
