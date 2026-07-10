# B1/B7 Cone01 R110 Live Public Dereference Probe Gate

## Summary

- Target: `T-B1-004hh/T-B7-016q`
- Upstream target: `T-B1-004hg/T-B7-016p`
- Method: `b1_b7_cone01_r110_live_public_dereference_probe_gate_v0`
- Status: `cone01_r110_live_public_dereference_probe_rejected_not_nonce_bound`
- Requirements: `6/6`
- Public fetch attempts: `3`
- Completed public fetches: `2`
- HTTP 2xx fetches: `0`
- Nonce-bound transcripts: `0`
- Requested-url-bound transcripts: `3`
- Dereference packet accepted: `False`
- Counter transition accepted: `False`
- Counter delta: `0`
- New credit delta: `0`

R110 probes the public-looking URLs from the R109 URL-only negative control with
unauthenticated HTTP GET requests. The probe records live transcripts, but does
not accept them as material evidence because the required transcript set is not
both HTTP-successful and challenge-nonce-bound.

## Requirements

- `P1` PASS: R110 binds the R109 contract and URL-only negative control
- `P2` PASS: R110 attempts unauthenticated live public HTTP fetches for all required URL roles
- `P3` PASS: R110 records hash-bound transcript files
- `P4` PASS: R110 refuses to accept transcripts unless all are HTTP 2xx and nonce-bound
- `P5` PASS: R110 keeps external counters and new credit at zero
- `P6` PASS: R110 emits a next-blocker queue for live nonce-bound public transcripts

## Artifacts

- Result JSON: `results/B1_B7_cone01_R110_live_public_dereference_probe_gate_v0.json`
- Probe verdict: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R110-G1-live-public-dereference-probe/live-public-dereference-probe.verdict.json`
- Blocker queue: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R110-G1-live-public-dereference-probe/post-live-public-dereference-probe-blocker-queue.json`
- Stdout: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R110-G1-live-public-dereference-probe/R110-live-public-dereference-probe.stdout.txt`

## Claim Boundary

R110 is a live public dereference probe only. It does not accept an external
reproduction, does not move any counter, and does not grant B7/O3/resource or
layout credit.
