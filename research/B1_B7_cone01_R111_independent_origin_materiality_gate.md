# B1/B7 Cone01 R111 Independent-Origin Materiality Gate

## Summary

- Target: `T-B1-004hi/T-B7-016r`
- Upstream target: `T-B1-004hh/T-B7-016q`
- Method: `b1_b7_cone01_r111_independent_origin_materiality_gate_v0`
- Status: `cone01_r111_public_fetch_passed_independent_origin_rejected`
- Model status: `public_fetchability_is_not_independent_materiality`
- Requirements: `8/8`
- Live public fetches: `3`
- HTTP 2xx fetches: `3`
- Nonce-bound transcripts: `3`
- Requested-url-bound transcripts: `3`
- Same-repository origins: `3`
- Materiality accepted: `False`
- Counter delta: `0`

R111 performs a real unauthenticated dereference against public files that are
reachable and nonce-bearing. It then rejects them as material external evidence
because the origin is the same repository and the fixtures are self-attested or
synthetic. A live `2xx` response is therefore necessary but not sufficient.

## Requirements

- `P1` PASS: R111 binds the R109 contract and immutable source commit
- `P2` PASS: R111 attempts unauthenticated public fetches for all three roles
- `P3` PASS: R111 records live HTTP 2xx nonce-bound requested-url-bound transcripts
- `P4` PASS: R111 identifies same-repository public origins
- `P5` PASS: R111 rejects self-attested or synthetic public materiality
- `P6` PASS: R111 keeps counters and new credit at zero
- `P7` PASS: R111 emits a four-item independent-origin blocker queue
- `P8` PASS: R111 states the public-fetchability claim boundary

## Claim Boundary

R111 supports a stronger negative result: public fetchability does not establish
independent materiality. It does not accept an external reproduction, move a
counter, or grant B7/O3/resource/layout credit.

## Artifacts

- Result JSON: `results/B1_B7_cone01_R111_independent_origin_materiality_gate_v0.json`
- Verdict: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R111-G1-independent-origin-materiality/independent-origin-materiality.verdict.json`
- Blocker queue: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R111-G1-independent-origin-materiality/post-independent-origin-materiality-blocker-queue.json`
- Stdout: `results/B1_B7_cone01_o3_f4_exit_route_submissions/R111-G1-independent-origin-materiality/R111-independent-origin-materiality.stdout.txt`
