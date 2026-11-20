#!/usr/bin/env python3
"""Audit six-image RTL-generation evidence and optionally hash local RTL."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results/B2_B7_P023_d6_microblossom_images_rtl_generation_v1.json"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def check(condition: bool, label: str, checks: list[dict[str, object]]) -> None:
    checks.append({"label": label, "pass": bool(condition)})
    if not condition:
        raise AssertionError(label)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=RESULT)
    parser.add_argument("--rtl-root", type=Path)
    args = parser.parse_args()
    result = json.loads(args.result.read_text(encoding="utf-8"))
    manifest_path = ROOT / result["source"]["image_manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    checks: list[dict[str, object]] = []
    check(sha(manifest_path) == result["source"]["image_manifest_sha256"],
          "manifest hash", checks)
    check(manifest["evidence_id"] == result["source"]["image_evidence_id"],
          "manifest evidence id", checks)
    check(result["scope"] == ["021/B7", "022/B2", "023"], "strict scope", checks)
    check(result["normalization"]["accepted_even_weight_max"] ==
          2 * result["normalization"]["hardware_weight_max"],
          "exact factor-two maximum", checks)
    check(result["normalization"]["rounding_or_clamping"] is False,
          "no rounding or clamping", checks)
    check(result["normalization"]["maximum_vertex_growth_after"] <= 65535,
          "16-bit accumulated-growth bound", checks)
    check(result["verification"]["fresh_stochastic_samples_observed"] == 0,
          "zero fresh samples", checks)
    check(result["verification"]["direct_load_sanity_checks_passed"] == 6,
          "six direct loads", checks)
    check(result["verification"]["generated_axi4_dynamic_weight_rtl_passed"] == 6,
          "six RTL generations", checks)
    check(result["verification"]["independent_iverilog_full_compile"] == "pass",
          "largest independent compile", checks)
    generated = result["generated_rtl"]
    check(len(generated) == 6, "six RTL rows", checks)
    manifest_rows = {(row["basis"], row["phase"]): row for row in manifest["images"]}
    generated_rows = {(row["basis"], row["phase"]): row for row in generated}
    check(set(generated_rows) == set(manifest_rows), "basis-phase coverage", checks)
    check(all(generated_rows[key]["input_image_sha256"] == manifest_rows[key]["file_sha256"]
              for key in generated_rows), "input image hashes", checks)
    check(all(row["rtl_bytes"] > 0 and len(row["rtl_sha256"]) == 64
              for row in generated), "RTL sizes and hashes", checks)
    acceptance = result["acceptance"]
    check(acceptance["fresh_xz_exact_corrections_replayed_in_rtl"] is False,
          "no correction-replay overclaim", checks)
    check(acceptance["p99_le_1us"] is False and acceptance["miss_rate_le_1pct"] is False,
          "no deadline overclaim", checks)
    check(acceptance["full_b2"] is False and acceptance["scalable_p023"] is False and
          acceptance["b7_resource_credit"] == 0, "downstream credit closed", checks)
    if args.rtl_root is not None:
        for row in generated:
            name = f"{row['basis']}_{row['phase']}"
            rtl = args.rtl_root / name / "MicroBlossomBus.v"
            check(rtl.is_file(), f"{name} local RTL exists", checks)
            check(rtl.stat().st_size == row["rtl_bytes"], f"{name} local RTL bytes", checks)
            check(sha(rtl) == row["rtl_sha256"], f"{name} local RTL hash", checks)
    print(json.dumps({
        "classification": "six_image_rtl_generation_audit_pass",
        "checks_passed": sum(row["pass"] for row in checks),
        "checks_total": len(checks),
        "rtl_files_rehashed": args.rtl_root is not None,
        "checks": checks,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
