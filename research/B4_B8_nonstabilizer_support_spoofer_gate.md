# B4/B8 Support-Aware Spoofer Gate v0.1

Last updated: 2026-06-18

Status: **support_aware_spoofer_boundary_not_protocol_soundness**

## Summary

- Source pilot: `results/B4_B8_nonstabilizer_late_bound_transcript_pilot_v0.json`
- Circuits attacked: 36
- Spoofer families: 4
- Attack rows: 144
- Max exact transcript success probability: 0.062500
- Max support-only acceptance rate: 1.000000
- Support-only verifier soundness rejected: True
- Deterministic exact-transcript blocker survives: True
- Acceptance gates passed / failed: 5 / 2

## Interpretation

T-B8-003c removed the old deterministic transcript blocker: a public deterministic parser no longer predicts one transcript with probability 1. This gate shows the next weakness. If the verifier only checks that a transcript lies inside the public support template, a support-aware generator can pass with acceptance 1.0.

Exact transcript guessing remains capped at 0.0625 for the tested pilot, but support membership alone is not a soundness condition. The next protocol must add verifier-private predicates, real backend properties, hardware execution, or another non-public acceptance burden.

## Acceptance Gates

- PASS: `source_pilot_loaded` - The attack consumes the T-B8-003c non-stabilizer pilot.
- PASS: `deterministic_exact_transcript_blocker_survives` - No tested spoofer predicts a single exact transcript above the 1/16 pilot ceiling.
- PASS: `support_only_verifier_rejected` - A verifier that only checks the public support template is fully spoofable.
- PASS: `learned_generative_attack_coverage_present` - The gate covers deterministic, support-sampling, learned, and leaked-basis spoofers.
- FAIL: `hardware_or_backend_execution_present` - No real backend properties or hardware execution are used.
- FAIL: `protocol_soundness_proved` - This is a negative guardrail, not a soundness proof.
- PASS: `no_forbidden_claims` - The report keeps hardware, hardness, advantage, and BQP claims false.

## Claim Boundary

- Not hardware execution.
- Not cryptographic or protocol soundness.
- Not sampling hardness.
- Not quantum advantage.
- Not BQP separation.

## Validation

- Validation errors: 0
