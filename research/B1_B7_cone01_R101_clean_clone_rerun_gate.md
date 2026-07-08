# B1/B7 Cone01 R101 Clean-Clone Rerun Gate

- Target: `T-B1-004gy/T-B7-016h`
- Upstream target: `T-B1-004gx/T-B7-016g`
- Method: `b1_b7_cone01_r101_clean_clone_rerun_gate_v0`
- Status: `cone01_r101_clean_clone_rerun_reproduces_r100_stable_hashes`
- Model status: `r100_no_counter_verdict_replayed_in_clean_local_checkout`

## Result

R101 reruns R100 from a clean local Git checkout and compares the stable
verdict, validation, and blocker hashes. The rerun reproduces those hashes,
but remains a local clean-checkout rerun rather than a third-party external
reproduction.

## Key Counters

- Clean-clone rerun reproduced: `True`
- Gates passed / failed: `8` / `0`
- Maintainer verdict accepted: `True`
- Counter delta: `0`
- Accepted external reproductions: `0`
- Accepted external falsifications: `0`
- New credit delta: `0`

## Requirements

- `A1` PASS: R101 binds accepted R100 no-counter verdict
- `A2` PASS: R101 runs R100 from a clean local clone checkout
- `A3` PASS: R101 reproduces R100 stable verdict, validation, and blocker hashes
- `A4` PASS: R101 keeps external counters and new credit at zero
- `A5` PASS: R101 emits blockers for independent reviewer identity, counter decision, and transition audit

## Artifacts

- Result JSON: `results/B1_B7_cone01_R101_clean_clone_rerun_gate_v0.json`
- Manifest: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R101-G1-clean-clone-rerun-manifest.json`
- Transcript: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R101-G1-clean-clone-rerun-transcript.txt`
- Comparison: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R101-G1-clean-clone-rerun-comparison.verdict.json`
- Blocker queue: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R101-G1-post-clean-rerun-blocker-queue.json`

## Claim Boundary

R101 proves a local clean-checkout rerun of R100 stable hashes. It does not
move the external reproduction or falsification counters, does not grant new
credit, and does not close B7/O3/resource/layout claims. The next gate needs
an independent reviewer identity plus an explicit counter-transition decision.
