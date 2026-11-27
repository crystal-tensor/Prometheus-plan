#!/usr/bin/env python3
"""Replay and audit the frozen X/Z closed-loop controls through generated AXI4-Lite RTL."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SLUG = "B2_B7_P023_d6_axi_lite32_pilot"
SCOPE = ["021/B7", "022/B2", "023"]
ARCHIVE_SHA = "284f3e52ab0a3de038821d7b9063ea978c16ec0f8b3a35204f8d862f6595659b"
BASE_PATCH_SHA = "a1b1b4a2036f44039f6448d16a357ea07d1105c272644e805e9f8ebc7c5b5b27"
SOURCE_COMMIT = "a3530d9e58ff790dafc93d56c9a2769ceac84731"
BIN = "d6_z_phase_primal_dual_closed_loop"
BASE_PATCH = ROOT / "tools/microblossom/d6_z_phase_primal_dual_closed_loop_v1.patch"
HOST_PATCH = ROOT / "tools/microblossom/d6_phase_axi_lite_host_v1.patch"
SCALA = [ROOT / f"tools/microblossom/D6PhaseAxi{name}.scala" for name in ("Endpoint", "Driver")]
REPLAY_TOOL = str(Path(__file__).resolve().relative_to(ROOT))
FROZEN = {"x": ("pilot", (0, 15)), "z": ("shard_0000_0007", tuple(range(8)))}
PROBE_LINE = (
    "AXI_PHASE_PROBES_PASS held_b_queued_write=1 held_r_snapshot_swap=1 "
    "invalid_writes=6 invalid_reads=2"
)
REPORT = "AXI_PHASE_TRANSPORT_PASS "
FIELDS = (
    "aw w b ar r aw_first w_first simultaneous b_stalls r_stalls b_errors r_errors "
    "phase_writes selector_writes xor_writes snapshots vector_words obstacle_reads simulated_bus_cycles"
).split()
BAD_RUNTIME = re.compile(r"\[error\]|assertion(error| failed)|panicked at|modulenotfounderror|unaccessible signal", re.I)
START_LINE = re.compile(
    r"^CLOSED_LOOP_START shot=(\d+) window=(\d+) phase=(\w+) defects=(\d+) selectors=(\d+)$", re.M
)
SOLVED_LINE = re.compile(
    r"^CLOSED_LOOP_SOLVED shot=(\d+) window=(\d+) iterations=(\d+) commit_clear=(true|false)$", re.M
)
SHOT_LINE = re.compile(
    r"^CLOSED_LOOP_SHOT shot=(\d+) residual_clear=(true|false) frame=(\w+) expected_frame=(\w+)$", re.M
)


def require(test: bool, message: str) -> None:
    if not test:
        raise ValueError(message)


def file_sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_new(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def inputs(basis: str) -> dict[str, Path]:
    tag, _ = FROZEN[basis]
    closed_loop = f"B2_B7_P023_d6_{basis}_closed_loop_{tag}"
    return {
        "base": ROOT / f"benchmarks/B2_B7_P023_d6_{basis}_phase_primal_dual_input_v1.json",
        "pilot": ROOT / f"benchmarks/{closed_loop}_v1.json",
        "selector": ROOT / f"tools/b2_b7_p023_d6_{basis}_selector_server_v1.py",
        "direct_raw": ROOT / f"results/{closed_loop}_verilator_v1.json",
        "direct_capture": ROOT / f"results/{closed_loop}_verilator_capture_v1.json",
    }


def artifacts(folder: Path, basis: str) -> dict[str, Path]:
    prefix = folder / f"{SLUG}_{basis}"
    return {
        "raw": prefix.with_name(prefix.name + "_raw_v1.json"),
        "log": prefix.with_name(prefix.name + "_v1.log"),
        "capture": prefix.with_name(prefix.name + "_capture_v1.json"),
    }


def source_hashes(basis: str) -> dict[str, str]:
    paths = [*inputs(basis).values(), BASE_PATCH, HOST_PATCH, *SCALA, Path(__file__).resolve()]
    return {str(path.relative_to(ROOT)): file_sha(path) for path in paths}


def prepare(archive: Path, build_parent: Path, git: str) -> Path:
    require(file_sha(archive) == ARCHIVE_SHA, "Micro Blossom archive changed")
    require(file_sha(BASE_PATCH) == BASE_PATCH_SHA, "accepted core patch changed")
    tree = Path(tempfile.mkdtemp(prefix="d6-axi-", dir=build_parent)).resolve()
    print(f"AXI source tree: {tree}", flush=True)
    subprocess.run(["tar", "-xzf", str(archive), "--strip-components=1", "-C", str(tree)], check=True)
    for patch in (BASE_PATCH, HOST_PATCH):
        subprocess.run([git, "apply", "--check", str(patch)], cwd=tree, check=True)
        subprocess.run([git, "apply", str(patch)], cwd=tree, check=True)
    for origin in SCALA:
        destination = tree / "src/fpga/microblossom" / origin.name
        require(not destination.exists(), f"unexpected upstream file {origin.name}")
        shutil.copy2(origin, destination)
    return tree


def replay(args: argparse.Namespace) -> None:
    prefix = args.verilator_prefix.resolve()
    verilator = prefix / "bin/verilator"
    executable = prefix / "bin/verilator_bin"
    environment = os.environ.copy()
    environment.update({
        "MICROBLOSSOM_PHASE_SIMULATOR": "verilator",
        "MICROBLOSSOM_PHASE_TRANSPORT": "axi_lite32",
        "JAVA_HOME": str(args.java_home.resolve()),
        "VERILATOR_ROOT": str(prefix / "share/verilator"),
        "PATH": os.pathsep.join((str(verilator.parent), str(args.java_home.resolve() / "bin"), os.environ["PATH"])),
    })
    if args.cargo_target_dir is not None:
        environment["CARGO_TARGET_DIR"] = str(args.cargo_target_dir.resolve())
    version = subprocess.check_output([str(verilator), "--version"], env=environment, text=True).strip()
    require(version.startswith("Verilator 5.040 2025-08-30"), f"wrong Verilator: {version}")
    output_dir = args.artifact_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    for basis in args.bases:
        for artifact in artifacts(output_dir, basis).values():
            require(not artifact.exists(), f"refusing to overwrite {artifact}")
    tree = prepare(args.archive.resolve(), args.build_parent.resolve(), args.git)
    python = args.selector_python.resolve()
    rust_dir = tree / "src/cpu/blossom"
    for basis in args.bases:
        incl = inputs(basis)
        out = artifacts(output_dir, basis)
        command = [
            "cargo", "run", "--locked", "--release", "--jobs", str(args.jobs), "--bin", BIN, "--",
            str(incl["base"]), str(incl["pilot"]), str(out["raw"]), str(python), str(incl["selector"]),
        ]
        print(f"[{basis}] generating and running phase endpoint", flush=True)
        run_input_hashes = source_hashes(basis)
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        start = time.monotonic()
        rtl = (
            tree / "simWorkspace/dualHost" / f"d6_{basis}_phase_primal_dual_full_corpus_shard"
            / "rtl/D6PhaseAxiEndpoint.v"
        )
        rtl_sha = None
        with out["log"].open("x", encoding="utf-8", buffering=1) as log:
            with subprocess.Popen(
                command, cwd=rust_dir, env=environment, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
            ) as proc:
                assert proc.stdout is not None
                for line in proc.stdout:
                    log.write(line)
                    # The Rust driver removes its build workspace on normal exit.
                    if "Verilator compilation started" in line and rtl.is_file():
                        rtl_sha = file_sha(rtl)
                    if ("[Progress]" in line or "CLOSED_LOOP_SHOT" in line or "AXI_PHASE_" in line
                        or BAD_RUNTIME.search(line)):
                        print(f"[{basis}] {line.rstrip()}", flush=True)
                exit_code = proc.wait()
        elapsed = time.monotonic() - start
        dump_new(out["capture"], {
            "schema": "b2_b7_p023_d6_axi_lite32_capture_v1",
            "scope": SCOPE,
            "basis": basis,
            "transport": "axi_lite32",
            "started_utc": started,
            "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "host_elapsed_seconds": elapsed,
            "exit_code": exit_code,
            "command": command,
            "simulator_version": version,
            "simulator_binary_sha256": file_sha(executable),
            "source_commit": SOURCE_COMMIT,
            "source_archive_sha256": file_sha(args.archive),
            "generated_endpoint_rtl_sha256": rtl_sha,
            "input_sha256": run_input_hashes,
            "raw_sha256": file_sha(out["raw"]) if out["raw"].is_file() else None,
            "log_sha256": file_sha(out["log"]),
        })
        row = audit_basis(output_dir, basis)
        print(f"[{basis}] {row['matched_windows']} exact AXI/direct windows", flush=True)


def audit_basis(folder: Path, basis: str) -> dict[str, Any]:
    incl = inputs(basis)
    paths = artifacts(folder, basis)
    raw, capture = (read(paths[key]) for key in ("raw", "capture"))
    log = paths["log"].read_text(encoding="utf-8")
    pilot, base, direct, direct_capture = (
        read(incl[key]) for key in ("pilot", "base", "direct_raw", "direct_capture")
    )
    _, shots = FROZEN[basis]
    windows = pilot["windows"]
    count = len(shots) * len(windows)
    require(tuple(row["shot"] for row in pilot["shots"]) == shots and len(windows) == 164, "pilot changed")
    require(base["basis"] == pilot["basis"] == capture["basis"] == basis, "basis binding mismatch")
    require(capture["scope"] == SCOPE and capture["transport"] == "axi_lite32", "transport unbound")
    expected_sources = source_hashes(basis)
    expected_sources.pop(REPLAY_TOOL)
    capture_sources = dict(capture["input_sha256"])
    replay_tool_sha = capture_sources.pop(REPLAY_TOOL)
    capture_sha = file_sha(paths["capture"])
    rtl_sha = capture.get("generated_endpoint_rtl_sha256")
    observation_sha = None
    if rtl_sha is None and basis == "x":
        # The initial X runner recorded its hash after the prior cleanup. Keep that
        # receipt unchanged and bind the separately observed, pre-cleanup file.
        witness_path = folder / f"{SLUG}_x_rtl_observation_v1.json"
        witness = read(witness_path)
        require(witness["schema"] == "b2_b7_p023_d6_axi_lite32_pre_cleanup_rtl_observation_v1" and
                witness["scope"] == SCOPE and witness["basis"] == basis and
                witness["capture_sha256"] == capture_sha and
                witness["log_sha256"] == file_sha(paths["log"]), "RTL observation not tied to the X run")
        require(capture["started_utc"] < witness["observed_no_later_utc"] < capture["finished_utc"] and
                "Verilator compilation started" in log and "Successfully remove build folder" in log,
                "RTL observation not taken during this run")
        require(replay_tool_sha == witness["initial_replay_tool_sha256"], "initial replay recorder mismatch")
        rtl_sha = witness["generated_endpoint_rtl_sha256"]
        observation_sha = file_sha(witness_path)
    require(capture_sources == expected_sources, "source/input hash mismatch")
    require(capture["source_commit"] == SOURCE_COMMIT and capture["source_archive_sha256"] == ARCHIVE_SHA,
            "wrong pinned Micro Blossom source")
    require(capture["simulator_version"].startswith("Verilator 5.040 2025-08-30"), "wrong backend")
    for digest in (rtl_sha, replay_tool_sha, capture.get("simulator_binary_sha256")):
        require(re.fullmatch(r"[0-9a-f]{64}", digest or "") is not None, "RTL/recorder/simulator digest missing")
    require(capture["exit_code"] == 0 and BAD_RUNTIME.search(log) is None, "execution did not pass")
    for name in ("raw", "log"):
        require(capture[f"{name}_sha256"] == file_sha(paths[name]), f"{name} unbound")

    require(direct_capture[f"accepted_{basis}_closed_loop_real_rtl_gate"] is True, "direct run not accepted")
    require(direct_capture["output_sha256"] == file_sha(incl["direct_raw"]), "direct baseline unbound")
    for key in ("pilot", "base", "selector"):
        field = {"pilot": "pilot_sha256", "base": "base_input_sha256", "selector": "selector_server_sha256"}[key]
        require(direct_capture[field] == file_sha(incl[key]), f"not comparing the same {key}")
    require(raw["pilot_evidence_id"] == pilot["evidence_id"], "wrong executed pilot")
    require(raw["base_input_evidence_id"] == base["evidence_id"], "wrong executed input")
    require(raw["accepted_corpus_sha256"] == pilot["accepted_corpus_sha256"], "wrong frozen corpus")

    cases = raw["cases"]
    require([(row["shot"], row["window"], row["phase"]) for row in cases] ==
            [(shot, row["window"], row["phase"]) for shot in shots for row in windows],
            "missing, reordered or duplicate (shot, window, phase)")
    require(len(direct["cases"]) == count, "direct case count mismatch")
    for wrapped, reference in zip(cases, direct["cases"], strict=True):
        require(wrapped == reference, f"first AXI/direct mismatch at shot={wrapped['shot']} window={wrapped['window']}")
        require(wrapped["syndrome_valid"] is True and wrapped["commit_residual_clear"] is True,
                "failed syndrome or residual")
    require(raw == direct, "non-case baseline mismatch")
    summary = raw["summary"]
    require(summary["shots"] == len(shots) and summary["windows"] == 164 and summary["cases"] == count,
            "incorrect case denominator")
    require(summary["accepted_closed_loop_gate"] is True and summary["all_syndromes_valid"] is True,
            "closed-loop gate failed")
    require(all(summary[k] == 0 for k in ("commit_residual_failures", "final_residual_failures", "final_frame_failures")),
            "semantic failure")
    defects = sum(row["defects"] for row in cases)
    require(raw["occupancy_audit"] == {"all_clear": True, "checks": defects, "expected_checks": defects},
            "missing or failed occupancy checks")
    require(START_LINE.findall(log) ==
            [(str(row["shot"]), str(row["window"]), row["phase"], str(row["defects"]), str(row["selectors"]))
             for row in cases], "runtime starts do not match the window rows")
    require(SOLVED_LINE.findall(log) ==
            [(str(row["shot"]), str(row["window"]), str(row["iterations"]), "true") for row in cases],
            "runtime solves do not match the window rows")
    endings = SHOT_LINE.findall(log)
    require(endings == [(str(shot["shot"]), "true", shot["expected_final_frame_hex"], shot["expected_final_frame_hex"])
                         for shot in pilot["shots"]], "closing state not verified for every shot")

    lines = [line.removeprefix("[info] ") for line in log.splitlines()]
    reports = [line for line in lines if line.startswith(REPORT)]
    require(len(reports) == 1 and lines.count(PROBE_LINE) == 1, "missing or duplicate AXI probes/report")
    # The Rust start notice can precede the Scala probe output; the first solved
    # notice requires completion of the hardware commands on the host socket.
    require(log.index(PROBE_LINE) < log.index("CLOSED_LOOP_SOLVED") and
            log.rindex("CLOSED_LOOP_SHOT") < log.index(REPORT), "AXI markers not bound to the solve interval")
    tokens = reports[0].removeprefix(REPORT).split()
    names = [token.split("=", 1)[0] for token in tokens]
    require(names == FIELDS, "AXI report field mismatch")
    bus = {name: int(token.split("=", 1)[1]) for name, token in zip(names, tokens, strict=True)}
    require(bus["aw"] == bus["w"] == bus["b"] and bus["ar"] == bus["r"], "in-flight or lost transaction")
    require(bus["b"] == bus["aw_first"] + bus["w_first"] + bus["simultaneous"], "AW/W ordering count mismatch")
    require(all(bus[k] > 0 for k in ("aw_first", "w_first", "simultaneous", "b_stalls", "r_stalls", "obstacle_reads")),
            "one or more required AXI conditions unexercised")
    require(bus["b_errors"] == 6 and bus["r_errors"] == 2, "negative-control responses wrong")
    require(bus["phase_writes"] == bus["snapshots"] == count, "phase/snapshot path bypassed")
    require(bus["selector_writes"] == sum(row["selectors"] for row in cases), "selector path bypassed")
    require(bus["xor_writes"] == sum(len(row["actual_subgraph_superset_edges"]) for row in cases),
            "correction edge path bypassed")
    words_by_phase = {phase["name"]: (phase["fault_id_count"] + 31) // 32 for phase in pilot["phases"]}
    require(bus["vector_words"] == sum(words_by_phase[row["phase"]] for row in cases), "partial correction readback")
    return {
        "basis": basis,
        "shots": list(shots),
        "matched_windows": count,
        "direct_row_mismatches": 0,
        "closed_loop_summary": summary,
        "occupancy_checks": defects,
        "bus": bus,
        "capture_sha256": capture_sha,
        "replay_tool_sha256": replay_tool_sha,
        "generated_endpoint_rtl_sha256": rtl_sha,
        "rtl_observation_sha256": observation_sha,
        "raw_sha256": capture["raw_sha256"],
        "log_sha256": capture["log_sha256"],
        "direct_raw_sha256": file_sha(incl["direct_raw"]),
    }


def audit(args: argparse.Namespace) -> None:
    rows = [audit_basis(args.artifact_dir, basis) for basis in FROZEN]
    payload = {
        "schema": "b2_b7_p023_d6_axi_lite32_pilot_evidence_v1",
        "scope": SCOPE,
        "classification": "bounded_same_clock_axi_lite32_closed_loop_pilot_pass",
        "basis_rows": rows,
        "matched_windows": sum(row["matched_windows"] for row in rows),
        "acceptance": {
            "bounded_axi_lite32_xz_pilot": True,
            "full_axi_denominator": False,
            "multi_context_or_cdc": False,
            "fpga": False,
            "p99_le_1us": False,
            "miss_rate_le_1pct": False,
            "full_b2": False,
            "scalable_p023": False,
            "b7_resource_credit": 0,
        },
    }
    payload["evidence_id"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    path = args.artifact_dir / f"{SLUG}_evidence_v1.json"
    if args.write:
        dump_new(path, payload)
    elif path.is_file():
        require(read(path) == payload, "saved evidence does not replay")
    print(json.dumps(payload, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    run = subparsers.add_parser("replay")
    run.add_argument("--artifact-dir", type=Path, required=True)
    run.add_argument("--archive", type=Path, required=True)
    run.add_argument("--build-parent", type=Path, required=True)
    run.add_argument("--java-home", type=Path, required=True)
    run.add_argument("--verilator-prefix", type=Path, required=True)
    run.add_argument("--selector-python", type=Path, default=Path(sys.executable))
    run.add_argument("--cargo-target-dir", type=Path)
    run.add_argument("--git", default="git")
    run.add_argument("--jobs", type=int, default=4)
    run.add_argument("--bases", choices=FROZEN, nargs="+", default=list(FROZEN))
    verify = subparsers.add_parser("audit")
    verify.add_argument("--artifact-dir", type=Path, required=True)
    verify.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.mode == "replay":
        require(len(set(args.bases)) == len(args.bases) and args.jobs > 0, "invalid replay options")
        replay(args)
    else:
        audit(args)


if __name__ == "__main__":
    main()
