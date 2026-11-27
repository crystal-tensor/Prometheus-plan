#!/usr/bin/env python3
"""Replay the packed obstacle register on the frozen X/Z AXI cohorts."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import b2_b7_p023_d6_axi_cycle_record_v1 as cycle
import b2_b7_p023_d6_axi_lite_replay_v1 as pilot

ROOT = pilot.ROOT
PREFIX = "B2_B7_P023_d6_axi_packed_status"
PATCH = ROOT / "tools/microblossom/d6_phase_axi_packed_status_v1.patch"
NEGATIVE = ROOT / "tools/microblossom/d6_phase_axi_packed_status_negative_control_v1.patch"
FIXTURE = ROOT / "tools/microblossom/D6PhaseAxiSmoke.scala"
BASELINE_EVIDENCE = ROOT / f"results/{cycle.PREFIX}_evidence_v1.json"
SEED = cycle.SEED
POLICY = "ready_high"
BAD_R = "RVALID/RDATA/RRESP changed during a stall"
MODES = ("packed", "split")


def paths(folder: Path, basis: str, mode: str) -> dict[str, Path]:
    return {name: folder / f"{PREFIX}_{basis}_{mode}_{name}_v1.{ext}"
            for name, ext in (("raw", "json"), ("run", "log"), ("capture", "json"))}


def smoke_paths(folder: Path) -> dict[str, Path]:
    return {name: folder / f"{PREFIX}_smoke_{name}_v1.{ext}"
            for name, ext in (("positive", "log"), ("negative", "log"), ("capture", "json"))}


def sources(basis: str | None) -> dict[str, str]:
    paths = (PATCH, NEGATIVE, FIXTURE, cycle.TIMING_PATCH, cycle.TIMING_SCALA,
             BASELINE_EVIDENCE, Path(__file__).resolve())
    base = cycle.sources(basis) if basis else {
        str(path.relative_to(ROOT)): pilot.file_sha(path)
        for path in (pilot.BASE_PATCH, pilot.HOST_PATCH, *pilot.SCALA)
    }
    return base | {str(path.relative_to(ROOT)): pilot.file_sha(path) for path in paths}


def apply(tree: Path, git: str, patch: Path) -> None:
    for args in ([git, "apply", "--check", str(patch)], [git, "apply", str(patch)]):
        subprocess.run(args, cwd=tree, check=True)


def prepare(args: argparse.Namespace) -> Path:
    tree = pilot.prepare(args.archive.resolve(), args.build_parent.resolve(), args.git)
    apply(tree, args.git, cycle.TIMING_PATCH)
    destination = tree / "src/fpga/microblossom"
    for source in (cycle.TIMING_SCALA, FIXTURE):
        shutil.copy2(source, destination / source.name)
    apply(tree, args.git, PATCH)
    return tree


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_smoke(args: argparse.Namespace, tree: Path, env: dict[str, str]) -> None:
    out = smoke_paths(args.artifact_dir)
    pilot.require(not any(path.exists() for path in out.values()), "refusing to overwrite smoke receipts")
    command = ["sbt", "-batch"]
    env.pop("MICROBLOSSOM_AXI_TIMING_POLICY", None)
    manifest = sources(None)
    started = utc()
    positive = command + ["runMain microblossom.D6PhaseAxiSmoke split",
                          "runMain microblossom.D6PhaseAxiSmoke packed"]
    negative = command + ["runMain microblossom.D6PhaseAxiSmoke packed"]
    with out["positive"].open("x", encoding="utf-8") as output:
        good = subprocess.run(positive, cwd=tree, env=env, stdout=output, stderr=subprocess.STDOUT).returncode
    log = out["positive"].read_text(encoding="utf-8")
    pilot.require(good == 0 and "AXI_PACKED_STATUS_PROBE_PASS old=" in log and not pilot.BAD_RUNTIME.search(log),
                  f"positive smoke failed; see {out['positive']}")
    print("split/packed Icarus smoke passed; running the deliberately unlatched variant", flush=True)
    apply(tree, args.git, NEGATIVE)
    with out["negative"].open("x", encoding="utf-8") as output:
        bad = subprocess.run(negative, cwd=tree, env=env, stdout=output, stderr=subprocess.STDOUT).returncode
    log = out["negative"].read_text(encoding="utf-8")
    pilot.require(bad != 0 and BAD_R in log and "AXI_PACKED_STATUS_PROBE_PASS" not in log,
                  f"negative control not rejected by the held-R check; see {out['negative']}")
    pilot.require(sources(None) == manifest, "smoke source manifest changed")
    simulator = subprocess.run(["iverilog", "-V"], env=env, text=True, check=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.splitlines()[0]
    capture = {
        "schema": "b2_b7_p023_d6_axi_packed_status_smoke_capture_v1", "scope": pilot.SCOPE,
        "started_utc": started, "finished_utc": utc(), "source_commit": pilot.SOURCE_COMMIT,
        "source_archive_sha256": pilot.ARCHIVE_SHA, "sources_sha256": manifest,
        "simulator_version": simulator, "simulator_seed": SEED,
        "positive_command": positive, "negative_command": negative,
        "positive_exit_code": good, "negative_exit_code": bad,
        "positive_log_sha256": pilot.file_sha(out["positive"]), "negative_log_sha256": pilot.file_sha(out["negative"]),
    }
    pilot.dump_new(out["capture"], capture)
    print(f"held-R test detected the live-data mutation: {out['capture']}", flush=True)


def run_workload(args: argparse.Namespace, tree: Path, env: dict[str, str]) -> None:
    basis = args.basis
    mode = args.mode
    out = paths(args.artifact_dir, basis, mode)
    ref = cycle.prior_basis(basis)
    pilot.require(not any(path.exists() for path in out.values()), "refusing to overwrite replay receipts")
    manifest = sources(basis)
    prefix = args.verilator_prefix.resolve()
    env.update({
        "MICROBLOSSOM_PHASE_SIMULATOR": "verilator", "MICROBLOSSOM_PHASE_TRANSPORT": "axi_lite32",
        "MICROBLOSSOM_AXI_TIMING_POLICY": POLICY, "MICROBLOSSOM_AXI_OBSTACLE_STATUS": mode,
        "VERILATOR_ROOT": str(prefix / "share/verilator"),
        "PATH": os.pathsep.join((str(prefix / "bin"), env["PATH"])),
    })
    if args.cargo_target_dir is not None:
        env["CARGO_TARGET_DIR"] = str(args.cargo_target_dir.resolve())
    version = subprocess.check_output([str(prefix / "bin/verilator"), "--version"], env=env, text=True).strip()
    pilot.require(version.startswith("Verilator 5.040 2025-08-30"), f"wrong Verilator: {version}")
    workspace = tree / "simWorkspace/dualHost"
    if args.cache_from is not None:
        pilot.require(args.cache_from.name == ".cache" and args.cache_from.is_dir(), "invalid cache path")
        shutil.copytree(args.cache_from, workspace / ".cache")
    sim = workspace / f"d6_{basis}_phase_primal_dual_full_corpus_shard"
    rtl = sim / "rtl/D6PhaseAxiEndpoint.v"
    compiled = sim / "verilator/VD6PhaseAxiEndpoint__ALL.a"
    incl = pilot.inputs(basis)
    command = ["cargo", "run", "--locked", "--release", "--jobs", str(args.jobs), "--bin", pilot.BIN, "--",
               str(incl["base"]), str(incl["pilot"]), str(out["raw"]), str(args.selector_python.resolve()),
               str(incl["selector"])]
    print(f"[{basis}/{mode}] launch", flush=True)
    started = utc()
    rtl_sha = model_sha = None
    with out["run"].open("x", encoding="utf-8", buffering=1) as log:
        with subprocess.Popen(command, cwd=tree / "src/cpu/blossom", env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
            assert proc.stdout is not None
            for line in proc.stdout:
                log.write(line)
                if "Verilator compilation started" in line and rtl.is_file():
                    rtl_sha = pilot.file_sha(rtl)
                if f"Start D6PhaseAxiEndpoint hosted simulation with seed {SEED}" in line and compiled.is_file():
                    model_sha = pilot.file_sha(compiled)
                if ("[Progress]" in line or "CLOSED_LOOP_SHOT" in line or "AXI_CYCLE_PROFILE" in line or
                        "Found cached verilator binaries" in line or pilot.BAD_RUNTIME.search(line)):
                    print(f"[{basis}/{mode}] {line.rstrip()}", flush=True)
            status = proc.wait()
    capture = {
        "schema": "b2_b7_p023_d6_axi_packed_status_capture_v1", "scope": pilot.SCOPE, "basis": basis,
        "obstacle_status": mode, "timing_policy": POLICY, "started_utc": started, "finished_utc": utc(),
        "exit_code": status, "source_commit": pilot.SOURCE_COMMIT, "source_archive_sha256": pilot.ARCHIVE_SHA,
        "command": command, "simulator_version": version,
        "simulator_binary_sha256": pilot.file_sha(prefix / "bin/verilator_bin"), "simulator_seed": SEED,
        "generated_endpoint_rtl_sha256": rtl_sha, "compiled_model_archive_sha256": model_sha,
        "sources_sha256": manifest, "raw_sha256": pilot.file_sha(out["raw"]) if out["raw"].is_file() else None,
        "log_sha256": pilot.file_sha(out["run"]),
    }
    pilot.dump_new(out["capture"], capture)
    log = out["run"].read_text(encoding="utf-8")
    pilot.require(status == 0 and not pilot.BAD_RUNTIME.search(log), "runtime failed")
    pilot.require(rtl_sha is not None and rtl_sha != ref["generated_endpoint_rtl_sha256"] and model_sha is not None,
                  "new endpoint or compiled model receipt missing")
    pilot.require(capture["raw_sha256"] == ref["direct_raw_sha256"], "closed-loop result changed")
    pilot.require(log.count(f"AXI_CYCLE_WINDOW mode={POLICY} ") == ref["matched_windows"] and
                  log.count(f"AXI_CYCLE_PROFILE mode={POLICY} ") == 1, "missing workload telemetry")
    pilot.require(sources(basis) == manifest, "inputs changed during replay")
    print(f"[{basis}/{mode}] unchanged raw output; {ref['matched_windows']} new cycle rows", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    task = parser.add_mutually_exclusive_group(required=True)
    task.add_argument("--smoke", action="store_true")
    task.add_argument("--basis", choices=pilot.FROZEN)
    parser.add_argument("--mode", choices=MODES, default="packed")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--build-parent", type=Path, required=True)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--verilator-prefix", type=Path)
    parser.add_argument("--selector-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--cargo-target-dir", type=Path)
    parser.add_argument("--cache-from", type=Path)
    parser.add_argument("--git", default="git")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    pilot.require(args.smoke or (args.verilator_prefix is not None and args.jobs > 0), "invalid replay options")
    args.artifact_dir = args.artifact_dir.resolve()
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    java_home = args.java_home.resolve()
    env = os.environ | {"JAVA_HOME": str(java_home),
                        "PATH": os.pathsep.join((str(java_home / "bin"), os.environ["PATH"]))}
    tree = prepare(args)
    if args.smoke:
        run_smoke(args, tree, env)
    else:
        run_workload(args, tree, env)


if __name__ == "__main__":
    main()
