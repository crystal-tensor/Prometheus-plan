#!/usr/bin/env python3
"""Audit the bounded Micro Blossom dynamic-weight RTL evidence packet."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_dynamic_weight_rtl_v1.json"
PATCH = ROOT / "tools/patches/micro_blossom_a3530d9_dynamic_weight_sideband.patch"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    result = json.loads(RESULT.read_text())
    checks = {
        "schema": result["schema"] == "b2_b7_p023_d6_microblossom_dynamic_weight_rtl_v1",
        "scope": result["scope"] == ["021/B7", "022/B2", "023"],
        "source_pin": result["external_source"]["commit"] == "a3530d9e58ff790dafc93d56c9a2769ceac84731",
        "patch_hash": sha256(PATCH) == result["patch"]["sha256"],
        "patch_apply": result["patch"]["clean_apply_dry_run"] is True,
        "semantic_opcode": result["protocol"]["semantic_opcode"] == "LoadWeightsExternal",
        "packed_width": result["protocol"]["edge_index_bits"] == 15 and result["protocol"]["weight_bits_max"] == 16,
        "ordering": "race guard" in result["protocol"]["ordering"],
        "bare_opcode_rejected": result["protocol"]["bare_opcode_rejected"] is True,
        "tests": (result["verification"]["tests_run"], result["verification"]["tests_passed"], result["verification"]["tests_failed"]) == (3, 3, 0),
        "target_isolation": result["verification"]["target_edge_changed"] is True and result["verification"]["adjacent_edge_unchanged"] is True,
        "reset": result["verification"]["reset_recovered_frozen_base"] is True,
        "rtl_present": result["acceptance"]["dynamic_write_path_present"] is True and result["acceptance"]["generated_rtl_simulated"] is True,
        "d6_boundary": result["acceptance"]["six_bound_d6_graph_rule_images_generated"] is False and result["acceptance"]["fresh_xz_exact_corrections_replayed_in_rtl"] is False,
        "timing_boundary": result["acceptance"]["batch_p99_cycles_measured"] is False and result["acceptance"]["p99_le_1us"] is False,
        "credit_boundary": result["acceptance"]["full_b2"] is False and result["acceptance"]["scalable_p023"] is False and result["acceptance"]["b7_resource_credit"] == 0,
    }
    failed = [name for name, passed in checks.items() if not passed]
    output = {"checks": checks, "passed": len(checks) - len(failed), "total": len(checks), "failed": failed}
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
