# B6 Backend Replay Scout

Status: **backend_replay_candidate_built_missing_observables**

## Summary

- Method: `b6_backend_replay_scout_v0`
- Selected variant: `physics_risk_adjusted_v0`
- Requirements passed / failed: 6 / 2
- Failed requirement IDs: R7, R8
- Source table hash: `ce134d0a5d295af982b77be0a8a43e90ea19e828af20cc80ac3f20b7664d2fdc`
- Replay formula hash: `e23239648dd11aa8e0db8ecdeb5824506a5a379c9ba2777965c3aafa5d5d8230`
- Replay table hash: `c44099194d0bc04d74cd3c4c4e068bf51a9e114d11c6e0b5e3890786cda5b8de`
- Selected post-split AP: 1.0
- Family-prior AP: 0.4901360544217687
- Negative controls in top-k: 2
- DFT rows / B5 rows: 0 / 0

## Requirement Results

- R1 [PASS]: source descriptor table exists
- R2 [PASS]: validation rescue source exists
- R3 [PASS]: row scope is preserved
- R4 [PASS]: selected variant is replayed with a pinned formula hash
- R5 [PASS]: replayed AP matches validation rescue scout
- R6 [PASS]: replayed score beats family prior and keeps negative controls
- R7 [FAIL]: DFT observable channel exists
- R8 [FAIL]: B5-computed observable channel exists

## Claim Boundary

- Supported: The validation-rescue score is replayed deterministically from the existing source table with stable hashes.
- Not supported: No external crystallographic backend, DFT observable, B5 observable, material discovery, or mechanism solution is established.
- Next gate: Attach real DFT and B5 observable rows or keep B6 demoted to validation-rescue evidence.
