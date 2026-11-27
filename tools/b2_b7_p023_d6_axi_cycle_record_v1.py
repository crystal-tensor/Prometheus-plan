#!/usr/bin/env python3
"""Capture a paired timing replay without modifying any accepted AXI pilot input or RTL."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import b2_b7_p023_d6_axi_lite_replay_v1 as pilot

ROOT = pilot.ROOT
PREFIX = "B2_B7_P023_d6_axi_cycle_profile"
TIMING_PATCH = ROOT / "tools/microblossom/d6_phase_axi_cycle_profile_v1.patch"
TIMING_SCALA = ROOT / "tools/microblossom/D6PhaseAxiCycleTiming.scala"
PILOT_EVIDENCE = ROOT / "results/B2_B7_P023_d6_axi_lite32_pilot_evidence_v1.json"
POLICIES = ("legacy_hold", "ready_high")
SEED = 20261127


def paths(folder: Path, basis: str, policy: str) -> dict[str, Path]:
    prefix = f"{PREFIX}_{basis}_{policy}"
    return {kind: folder / f"{prefix}_{kind}_v1.{ext}"
            for kind, ext in (("raw", "json"), ("capture", "json"), ("run", "log"))}


def prior_basis(basis: str) -> dict:
    return next(row for row in pilot.read(PILOT_EVIDENCE)["basis_rows"] if row["basis"] == basis)


def sources(basis: str) -> dict[str, str]:
    return pilot.source_hashes(basis) | {
        str(path.relative_to(ROOT)): pilot.file_sha(path)
        for path in (TIMING_PATCH, TIMING_SCALA, PILOT_EVIDENCE, Path(__file__).resolve())
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--basis", choices=pilot.FROZEN, required=True)
    parser.add_argument("--policies", choices=POLICIES, nargs="+", default=list(POLICIES))
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--build-parent", type=Path, required=True)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--verilator-prefix", type=Path, required=True)
    parser.add_argument("--selector-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--cargo-target-dir", type=Path)
    parser.add_argument("--cache-from", type=Path, help="optional local SpinalHDL Verilator cache")
    parser.add_argument("--git", default="git")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    basis = args.basis
    ref = prior_basis(basis)
    folder = args.artifact_dir.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    pilot.require(len(set(args.policies)) == len(args.policies) and args.jobs > 0, "invalid options")
    for policy in args.policies:
        for path in paths(folder, basis, policy).values():
            pilot.require(not path.exists(), f"refusing to overwrite {path}")
    prefix = args.verilator_prefix.resolve()
    environment = os.environ.copy()
    environment.update({
        "MICROBLOSSOM_PHASE_SIMULATOR": "verilator",
        "MICROBLOSSOM_PHASE_TRANSPORT": "axi_lite32",
        "JAVA_HOME": str(args.java_home.resolve()),
        "VERILATOR_ROOT": str(prefix / "share/verilator"),
        "PATH": os.pathsep.join((str(prefix / "bin"), str(args.java_home.resolve() / "bin"),
                                os.environ["PATH"])),
    })
    if args.cargo_target_dir is not None:
        environment["CARGO_TARGET_DIR"] = str(args.cargo_target_dir.resolve())
    version = subprocess.check_output([str(prefix / "bin/verilator"), "--version"],
                                      env=environment, text=True).strip()
    pilot.require(version.startswith("Verilator 5.040 2025-08-30"), f"wrong Verilator: {version}")
    tree = pilot.prepare(args.archive.resolve(), args.build_parent.resolve(), args.git)
    for command in ([args.git, "apply", "--check", str(TIMING_PATCH)], [args.git, "apply", str(TIMING_PATCH)]):
        subprocess.run(command, cwd=tree, check=True)
    shutil.copy2(TIMING_SCALA, tree / "src/fpga/microblossom" / TIMING_SCALA.name)
    workspace = tree / "simWorkspace/dualHost"
    if args.cache_from is not None:
        pilot.require(args.cache_from.name == ".cache" and args.cache_from.is_dir(), "invalid cache path")
        shutil.copytree(args.cache_from, workspace / ".cache")
    manifest = sources(basis)
    incl = pilot.inputs(basis)
    rust_dir = tree / "src/cpu/blossom"
    sim = workspace / f"d6_{basis}_phase_primal_dual_full_corpus_shard"
    rtl = sim / "rtl/D6PhaseAxiEndpoint.v"
    compiled_model = sim / "verilator/VD6PhaseAxiEndpoint__ALL.a"
    for policy in args.policies:
        env = environment | {"MICROBLOSSOM_AXI_TIMING_POLICY": policy}
        out = paths(folder, basis, policy)
        command = [
            "cargo", "run", "--locked", "--release", "--jobs", str(args.jobs), "--bin", pilot.BIN, "--",
            str(incl["base"]), str(incl["pilot"]), str(out["raw"]), str(args.selector_python.resolve()),
            str(incl["selector"]),
        ]
        print(f"[{basis}/{policy}] launch", flush=True)
        started = datetime.now(timezone.utc).isoformat()
        rtl_sha = None
        compiled_sha = None
        cache_hit = False
        with out["run"].open("x", encoding="utf-8", buffering=1) as log:
            with subprocess.Popen(command, cwd=rust_dir, env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
                assert proc.stdout is not None
                for line in proc.stdout:
                    log.write(line)
                    if "Verilator compilation started" in line and rtl.is_file():
                        rtl_sha = pilot.file_sha(rtl)
                    if "Found cached verilator binaries" in line:
                        cache_hit = True
                    if f"Start D6PhaseAxiEndpoint hosted simulation with seed {SEED}" in line:
                        if compiled_model.is_file():
                            compiled_sha = pilot.file_sha(compiled_model)
                    if ("[Progress]" in line or "CLOSED_LOOP_SHOT" in line or "AXI_CYCLE_PROFILE" in line
                            or "Found cached verilator binaries" in line or pilot.BAD_RUNTIME.search(line)):
                        print(f"[{basis}/{policy}] {line.rstrip()}", flush=True)
                status = proc.wait()
        capture = {
            "schema": "b2_b7_p023_d6_axi_cycle_profile_capture_v1",
            "scope": pilot.SCOPE,
            "basis": basis,
            "policy": policy,
            "started_utc": started,
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "exit_code": status,
            "source_commit": pilot.SOURCE_COMMIT,
            "source_archive_sha256": pilot.file_sha(args.archive),
            "command": command,
            "simulator_version": version,
            "simulator_binary_sha256": pilot.file_sha(prefix / "bin/verilator_bin"),
            "simulator_seed": SEED,
            "generated_endpoint_rtl_sha256": rtl_sha,
            "compiled_model_archive_sha256": compiled_sha,
            "verilator_cache_hit": cache_hit,
            "sources_sha256": manifest,
            "raw_sha256": pilot.file_sha(out["raw"]) if out["raw"].is_file() else None,
            "log_sha256": pilot.file_sha(out["run"]),
        }
        pilot.dump_new(out["capture"], capture)
        log = out["run"].read_text(encoding="utf-8")
        pilot.require(status == 0 and pilot.BAD_RUNTIME.search(log) is None, "runtime failed")
        pilot.require(rtl_sha == ref["generated_endpoint_rtl_sha256"], "RTL not byte-identical to pilot")
        pilot.require(compiled_sha is not None, "compiled model receipt missing")
        pilot.require(capture["raw_sha256"] == ref["direct_raw_sha256"], "closed-loop result changed")
        pilot.require(log.count(f"AXI_CYCLE_WINDOW mode={policy} ") == ref["matched_windows"]
                      and log.count(f"AXI_CYCLE_PROFILE mode={policy} ") == 1, "missing workload telemetry")
        pilot.require(sources(basis) == manifest, "inputs changed during replay")
        print(f"[{basis}/{policy}] unchanged RTL and output; {ref['matched_windows']} cycle rows", flush=True)


if __name__ == "__main__":
    main()
