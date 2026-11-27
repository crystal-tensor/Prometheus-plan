#!/usr/bin/env python3
"""Record explicit read-to-query AXI replays, with separate bus stress controls."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import b2_b7_p023_d6_axi_lite_replay_v1 as pilot
import b2_b7_p023_d6_axi_packed_status_record_v1 as packed

ROOT = pilot.ROOT
PREFIX = "B2_B7_P023_d6_axi_fused_query"
PATCH = ROOT / "tools/microblossom/d6_phase_axi_fused_query_v1.patch"
CONTROLS = {
    "duplicate": ("fused command without a fresh AR or duplicate execution"),
    "early_r": ("fused R became valid before the core capture"),
}
BASELINE = ROOT / f"results/{packed.PREFIX}_evidence_v1.json"
POLICY, SEED = packed.POLICY, packed.SEED
require = pilot.require


def paths(folder: Path, basis: str) -> dict[str, Path]:
    return {name: folder / f"{PREFIX}_{basis}_{name}_v1.{extension}" for name, extension in
            (("run", "log"), ("raw", "json"), ("capture", "json"))}


def control_patch(name: str) -> Path:
    return ROOT / f"tools/microblossom/d6_phase_axi_fused_query_{name}_control_v1.patch"


def smoke_paths(folder: Path) -> dict[str, Path]:
    return {name: folder / f"{PREFIX}_smoke_{name}_v1.{extension}" for name, extension in
            (("capture", "json"), ("positive", "log"), *((name, "log") for name in CONTROLS))}


def sources(basis: str | None) -> dict[str, str]:
    files = [PATCH, BASELINE, Path(__file__).resolve()]
    if basis is None:
        files += [control_patch(name) for name in CONTROLS]
    else:
        files += [packed.paths(ROOT / "results", basis, "packed")["capture"]]
    return packed.sources(basis) | {str(path.relative_to(ROOT)): pilot.file_sha(path) for path in files}


def run_smoke(tree: Path, args: argparse.Namespace, env: dict[str, str]) -> None:
    out = smoke_paths(args.artifact_dir)
    require(not any(p.exists() for p in out.values()), "refusing to overwrite smoke receipts")
    env.pop("MICROBLOSSOM_AXI_TIMING_POLICY", None)
    input_hashes = sources(None)
    start = packed.utc()
    base = ["sbt", "-batch"]
    commands = {
        "positive": base + [f"runMain microblossom.D6PhaseAxiSmoke {mode}" for mode in ("split", "packed", "fused")],
        **{name: base + ["runMain microblossom.D6PhaseAxiSmoke fused"] for name in CONTROLS},
    }
    statuses = {}
    for name, command in commands.items():
        if name != "positive":
            packed.apply(tree, args.git, control_patch(name))
        with out[name].open("x", encoding="utf-8") as log:
            statuses[name] = subprocess.run(command, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
        text = out[name].read_text(encoding="utf-8")
        if name == "positive":
            require(statuses[name] == 0 and "AXI_FUSED_EXEC_PASS " in text and not pilot.BAD_RUNTIME.search(text),
                    f"positive smoke failed; see {out[name]}")
        else:
            require(statuses[name] != 0 and CONTROLS[name] in text and "AXI_FUSED_EXEC_PASS " not in text,
                    f"{name} mutation did not fail the intended invariant; see {out[name]}")
            patch = str(control_patch(name))
            subprocess.run([args.git, "apply", "--reverse", "--check", patch], cwd=tree, check=True)
            subprocess.run([args.git, "apply", "--reverse", patch], cwd=tree, check=True)
        print(f"smoke {name}: expected outcome", flush=True)
    require(input_hashes == sources(None), "smoke source manifest changed")
    version = subprocess.run(["iverilog", "-V"], env=env, text=True, check=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.splitlines()[0]
    pilot.dump_new(out["capture"], {
        "schema": "b2_b7_p023_d6_axi_fused_query_smoke_capture_v1", "scope": pilot.SCOPE, "seed": SEED,
        "source_commit": pilot.SOURCE_COMMIT, "source_archive_sha256": pilot.ARCHIVE_SHA, "simulator": version,
        "commands": commands, "exit_codes": statuses, "started_utc": start, "finished_utc": packed.utc(),
        "sources_sha256": input_hashes, "log_sha256": {name: pilot.file_sha(out[name]) for name in statuses},
    })


def run_replay(tree: Path, args: argparse.Namespace, env: dict[str, str]) -> None:
    basis = args.basis
    out = paths(args.artifact_dir, basis)
    require(not any(p.exists() for p in out.values()), "refusing to overwrite replay receipts")
    ref = packed.cycle.prior_basis(basis)
    input_hashes = sources(basis)
    prefix = args.verilator_prefix.resolve()
    env.update({
        "MICROBLOSSOM_PHASE_SIMULATOR": "verilator", "MICROBLOSSOM_PHASE_TRANSPORT": "axi_lite32",
        "MICROBLOSSOM_AXI_TIMING_POLICY": POLICY, "MICROBLOSSOM_AXI_OBSTACLE_STATUS": "fused",
        "VERILATOR_ROOT": str(prefix / "share/verilator"), "PATH": os.pathsep.join((str(prefix / "bin"), env["PATH"])),
    })
    if args.cargo_target_dir is not None:
        env["CARGO_TARGET_DIR"] = str(args.cargo_target_dir.resolve())
    simulator = subprocess.check_output([str(prefix / "bin/verilator"), "--version"], env=env, text=True).strip()
    require(simulator.startswith("Verilator 5.040 2025-08-30"), "wrong simulator")
    workspace = tree / "simWorkspace/dualHost"
    if args.cache_from is not None:
        require(args.cache_from.name == ".cache" and args.cache_from.is_dir(), "invalid cache path")
        shutil.copytree(args.cache_from, workspace / ".cache")
    sim = workspace / f"d6_{basis}_phase_primal_dual_full_corpus_shard"
    rtl = sim / "rtl/D6PhaseAxiEndpoint.v"
    model = sim / "verilator/VD6PhaseAxiEndpoint__ALL.a"
    incl = pilot.inputs(basis)
    command = ["cargo", "run", "--locked", "--release", "--jobs", str(args.jobs), "--bin", pilot.BIN, "--",
               str(incl["base"]), str(incl["pilot"]), str(out["raw"]), str(args.selector_python.resolve()),
               str(incl["selector"])]
    start = packed.utc()
    rtl_sha = model_sha = None
    print(f"[{basis}/fused] launch", flush=True)
    with out["run"].open("x", encoding="utf-8", buffering=1) as log:
        with subprocess.Popen(command, cwd=tree / "src/cpu/blossom", env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
            assert proc.stdout is not None
            for line in proc.stdout:
                log.write(line)
                if "Verilator compilation started" in line and rtl.is_file():
                    rtl_sha = pilot.file_sha(rtl)
                if f"Start D6PhaseAxiEndpoint hosted simulation with seed {SEED}" in line and model.is_file():
                    model_sha = pilot.file_sha(model)
                if any(marker in line for marker in ("[Progress]", "CLOSED_LOOP_SHOT", "AXI_CYCLE_PROFILE",
                                                     "AXI_FUSED_EXEC_PASS")) or pilot.BAD_RUNTIME.search(line):
                    print(f"[{basis}/fused] {line.rstrip()}", flush=True)
            status = proc.wait()
    capture = {
        "schema": "b2_b7_p023_d6_axi_fused_query_capture_v1", "scope": pilot.SCOPE, "basis": basis,
        "mode": "fused", "timing_policy": POLICY, "command": command, "simulator_version": simulator,
        "simulator_binary_sha256": pilot.file_sha(prefix / "bin/verilator_bin"), "simulator_seed": SEED,
        "source_commit": pilot.SOURCE_COMMIT, "source_archive_sha256": pilot.ARCHIVE_SHA, "exit_code": status,
        "started_utc": start, "finished_utc": packed.utc(), "sources_sha256": input_hashes,
        "generated_endpoint_rtl_sha256": rtl_sha, "compiled_model_archive_sha256": model_sha,
        "raw_sha256": pilot.file_sha(out["raw"]) if out["raw"].is_file() else None, "log_sha256": pilot.file_sha(out["run"]),
    }
    pilot.dump_new(out["capture"], capture)
    log = out["run"].read_text(encoding="utf-8")
    require(status == 0 and rtl_sha and model_sha and not pilot.BAD_RUNTIME.search(log), "replay did not pass")
    require(capture["raw_sha256"] == ref["direct_raw_sha256"] and sources(basis) == input_hashes, "replay drift")
    require(log.count(f"AXI_CYCLE_WINDOW mode={POLICY} ") == ref["matched_windows"] and
            log.count("AXI_FUSED_EXEC_PASS ") == 1 and log.count("AXI_CYCLE_PROFILE ") == 1, "telemetry missing")
    print(f"[{basis}/fused] unchanged raw output, {ref['matched_windows']} windows recorded", flush=True)


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    task = cli.add_mutually_exclusive_group(required=True)
    task.add_argument("--basis", choices=pilot.FROZEN)
    task.add_argument("--smoke", action="store_true")
    for name in ("artifact-dir", "archive", "build-parent", "java-home"):
        cli.add_argument(f"--{name}", type=Path, required=True)
    for name in ("verilator-prefix", "cargo-target-dir", "cache-from"):
        cli.add_argument(f"--{name}", type=Path)
    cli.add_argument("--selector-python", type=Path, default=Path(sys.executable))
    cli.add_argument("--git", default="git")
    cli.add_argument("--jobs", type=int, default=4)
    args = cli.parse_args()
    require(args.smoke or (args.verilator_prefix is not None and args.jobs > 0), "invalid replay options")
    args.artifact_dir = args.artifact_dir.resolve()
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    tree = packed.prepare(args)
    packed.apply(tree, args.git, PATCH)
    jdk = args.java_home.resolve()
    env = os.environ | {"JAVA_HOME": str(jdk), "PATH": os.pathsep.join((str(jdk / "bin"), os.environ["PATH"]))}
    (run_smoke if args.smoke else run_replay)(tree, args, env)


if __name__ == "__main__":
    main()
