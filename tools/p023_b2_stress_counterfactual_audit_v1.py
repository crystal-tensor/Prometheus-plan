#!/usr/bin/env python3
"""Independently recount selected replays and ensure none score a qualification row."""

import argparse
import copy
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = "benchmarks/P023_B2_stress_counterfactual_v1.json"
OBSERVED = "observed_nominal_decoder"
REMOVED = "same_faults_without_pairs"
AWARE = "observed_pair_aware_decoder"


def check(ok, message):
    if not ok:
        raise AssertionError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def bit(record, name, i):
    data = bytes.fromhex(record[name+"_le_hex"])
    check(len(data) == record["shots"]//8, "wrong number of packed bits")
    return (int.from_bytes(data, byteorder="little") >> i) & 1


def audit(artifact, git):
    protocol_bytes = (ROOT / PROTOCOL).read_bytes()
    p = json.loads(protocol_bytes)
    by_case = []
    for case, spec in p["cases"].items():
        raw = (artifact / "source" / spec["file"]).read_bytes()
        observed = json.loads(raw)["receipt"]
        check(digest(raw) == spec["sha256"] and observed["shots"] == 128
              and observed["windows"] == 7813 and observed["rounds"] == p["rounds"],
              "wrong source record")
        result = (artifact / f"{case}.json").read_bytes()
        d = json.loads(result)
        frozen = subprocess.check_output([git, "show", f"{d['experiment_freeze']}:{PROTOCOL}"], cwd=ROOT)
        started = json.loads(frozen)
        late = digest(frozen) != d["protocol_sha256"]
        if late:
            # v1 recorded the protocol digest at close. The only admitted
            # mid-run correction affected the other, not this, case.
            revised = copy.deepcopy(started)
            from_sha = revised["cases"]["d12_z"]["sha256"]
            to_sha = p["cases"]["d12_z"]["sha256"]
            revised["cases"]["d12_z"]["sha256"] = to_sha
            check(case != "d12_z" and revised == p and from_sha != to_sha
                  and digest(protocol_bytes) == d["protocol_sha256"], "unexplained manifest drift")
        check(started["cases"][case] == spec == d["selection"], "wrong freeze or case")
        check(d["factual_replay_validated"] and not d["qualification_credit"]
              and d["kernel_sha256"] == observed["kernel_sha256"]
              and d["original_shard_seed"] == observed["seed"], "ineligible replay")
        check(set(d["unit_controls"]) == {"head", "bulk", "tail"}
              and all(x["calls"] == 2 and sum(x["removed_events"]) > 0
                      for x in d["unit_controls"].values()), "incomplete independent oracle checks")
        failed = [i for i in range(128) if bit(observed, "failures", i)]
        check(len(failed) == spec["source_failures"], "original count changed")
        controls = min(i for i in range(128) if i not in failed)
        selected = failed + [controls]
        check([x["source_shot_zero_based"] for x in d["traces"]] == selected, "selection changed")
        recovered = {key: [] for key in (REMOVED, AWARE)}
        new = {key: [] for key in (REMOVED, AWARE)}
        for i, shot in zip(selected, d["traces"], strict=True):
            check(shot["original_failure"] == bool(bit(observed, "failures", i))
                  and shot["paired_faults_removed"] > 0, "intervention not exercised")
            old = shot["branches"][OBSERVED]
            for key in ("truth", "correction"):
                check(old[key] == bit(observed, key, i), "factual replay does not match archived bits")
            for key, row in shot["branches"].items():
                check(row["truth"] == old["truth"] and row["failed"] ==
                      bool(row["truth"] ^ row["correction"]), "logical parity mismatch")
                n = row["changed_commit_windows"]
                first = row["first_changed_window_zero_based"]
                check(0 <= n <= observed["windows"] and n % 2 == old["correction"] ^ row["correction"]
                      and ((n == 0 and first is None) or (n > 0 and 0 <= first < observed["windows"])),
                      "window and final parity do not reconcile")
                if key != OBSERVED and old["failed"] and not row["failed"]:
                    recovered[key].append(i)
                if key != OBSERVED and not old["failed"] and row["failed"]:
                    new[key].append(i)
        by_case.append({"case": case, "source_sha256": digest(raw), "result_sha256": digest(result),
                        "frozen_protocol_sha256": digest(frozen),
                        "receipt_protocol_sha256": d["protocol_sha256"],
                        "late_digest_due_to_unrelated_input_checksum": late,
                        "original_failed_indices": failed, "original_success_control": controls,
                        "recovered_indices": recovered, "new_failure_control_indices": new})
    return {"schema": "p023_b2_stress_counterfactual_audit_v1", "selected_only": True,
            "qualification_credit": False, "auditor_sha256": digest(Path(__file__).read_bytes()),
            "cases": by_case, "observed_failures_replayed": sum(len(x["original_failed_indices"])
                                                               for x in by_case),
            "total_recovered_selected_failures": {
                key: sum(len(x["recovered_indices"][key]) for x in by_case) for key in (REMOVED, AWARE)
            }, "total_new_failures_in_success_controls": {
                key: sum(len(x["new_failure_control_indices"][key]) for x in by_case)
                for key in (REMOVED, AWARE)}}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact-dir", type=Path, required=True)
    p.add_argument("--git", default="git")
    p.add_argument("--out", type=Path)
    a = p.parse_args()
    data = audit(a.artifact_dir, a.git)
    s = json.dumps(data, indent=2, sort_keys=True)+"\n"
    if a.out:
        with a.out.open("x") as f:
            f.write(s)
    print(s, end="")


if __name__ == "__main__":
    main()
