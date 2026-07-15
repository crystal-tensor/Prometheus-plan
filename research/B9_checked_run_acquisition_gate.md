# B9 Checked-Run Acquisition Gate

Status: **checked_run_acquisition_passed_interface_transcript_recorded**

## Summary

- Method: `b9_checked_run_acquisition_gate_v0`
- Acquisition requirements passed/failed: 7 / 0
- Failed acquisition requirement IDs: []
- Lean 4 available: True
- Lake available: True
- Release host reachable: True
- Local toolchain cache present: True
- Checked transcript present: True

## Requirement Results

- A1 [PASS]: Offline proof bundle remains valid and hashable
- A2 [PASS]: Pinned Lean toolchain declaration is present
- A3 [PASS]: Real Lean 4 executable is available without triggering an acquisition timeout
- A4 [PASS]: Lake executable is available without triggering an acquisition timeout
- A5 [PASS]: Pinned Lean toolchain can be acquired or is already cached
- A6 [PASS]: Checked Lean module transcript is present
- A7 [PASS]: Forbidden B9 theorem and Quantum PCP claims remain false

## Toolchain Probe

- Lean probes: `[{"available": true, "command": ["~/.elan/bin/lean", "--version"], "executable": "~/.elan/bin/lean", "returncode": 0, "runtime_seconds": 0.02759099006652832, "stderr": "", "stdout": "Lean (version 4.12.0, arm64-apple-darwin23.6.0, commit dc2533473114, Release)", "timed_out": false}, {"available": true, "command": ["~/.elan/bin/lean", "--version"], "executable": "~/.elan/bin/lean", "returncode": 0, "runtime_seconds": 0.026246070861816406, "stderr": "", "stdout": "Lean (version 4.12.0, arm64-apple-darwin23.6.0, commit dc2533473114, Release)", "timed_out": false}]`
- Lake probes: `[{"available": true, "command": ["~/.elan/bin/lake", "--version"], "executable": "~/.elan/bin/lake", "returncode": 0, "runtime_seconds": 0.027293920516967773, "stderr": "", "stdout": "Lake version 5.0.0-dc25334 (Lean version 4.12.0)", "timed_out": false}, {"available": true, "command": ["~/.elan/bin/lake", "--version"], "executable": "~/.elan/bin/lake", "returncode": 0, "runtime_seconds": 0.02795696258544922, "stderr": "", "stdout": "Lake version 5.0.0-dc25334 (Lean version 4.12.0)", "timed_out": false}]`
- Elan probes: `[{"available": true, "command": ["~/.elan/bin/elan", "--version"], "executable": "~/.elan/bin/elan", "returncode": 0, "runtime_seconds": 0.00863194465637207, "stderr": "", "stdout": "elan 4.2.3 (b6cec7e10 2026-06-08)", "timed_out": false}, {"available": true, "command": ["~/.elan/bin/elan", "--version"], "executable": "~/.elan/bin/elan", "returncode": 0, "runtime_seconds": 0.00872492790222168, "stderr": "", "stdout": "elan 4.2.3 (b6cec7e10 2026-06-08)", "timed_out": false}]`
- Release host probe: `{"error": null, "host": "release.lean-lang.org", "port": 443, "reachable": true, "runtime_seconds": 0.020704030990600586}`

## Claim Boundary

- Supported: The pinned Lean 4.12.0/Lake environment is available and the indexed B9 theorem interface has a recorded zero-returncode Lean/Lake transcript.
- Not supported: No proof-assistant checked theorem, Quantum PCP proof, NLTS theorem, or global gap-amplification impossibility theorem is established.
- Next gate: Bind the checked transcript to the priority, provenance, replay, and acceptance packets, then formalize the open-boundary Hamiltonian construction and its all-n lemmas.
- proof_assistant_checked: True
- formal_theorem_proved: False
- explicit_not_quantum_pcp_proof: True

## Validation

- validation_error_count: 0
