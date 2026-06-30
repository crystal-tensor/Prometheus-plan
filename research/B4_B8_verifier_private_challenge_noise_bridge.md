# B4/B8 Verifier-Private Challenge Noise Bridge

- Gate: T-B4-002c / T-B8-003g
- Method: `b4_b8_verifier_private_challenge_noise_bridge_v0`
- Status: `private_challenge_noise_transcript_bridge_not_hardware`
- Transcript cases: 720
- Gates passed: 8 / 8

## Result

| Metric | Value |
| --- | ---: |
| backend-like no-refresh honest acceptance | 0.747047070414 |
| backend-like challenge-refresh honest acceptance | 0.805169120213 |
| backend-like refresh-plus-rotation honest acceptance | 0.866618491942 |
| max no-leak adversary acceptance | 0.0625 |
| max three-private-bit leakage acceptance | 0.5 |
| max full-private-material leakage acceptance | 1.0 |

## Interpretation

The bridge keeps the formal private challenge protocol at model level. Under the backend-like predicate-bit error profile, no-refresh honest acceptance falls below the 0.8 gate, while challenge-refresh and refresh-plus-rotation stay above it. No-leak adversaries remain at the 1/16 guessing floor, but full private-material leakage still breaks the gate.

## Claim Boundary

- This is a noise-modeled transcript bridge, not hardware execution.
- It does not use real backend properties.
- It does not prove cryptographic or protocol soundness.
- It does not claim quantum advantage or BQP separation.
