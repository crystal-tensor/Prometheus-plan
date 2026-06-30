# B2 Calibration Transfer Guardrail Gate v0.1

Status: **calibration_transfer_guardrail_failed**

## Summary

- Method: b2_calibration_transfer_guardrail_gate_v0
- Model status: hardware_like_model_has_no_calibrated_or_hardware_transfer_evidence
- Source challenge count: 3
- Source trace count: 576
- Observation profiles / profile rows: 3 / 9
- Total profile shots / holdout shots: 1728 / 864
- Best profile: conservative_hardware_like_leakage
- Best-profile model flag events: 415
- Stress-profile model flag events: 727
- Best-profile holdout baseline / injected / delta: 16 / 16 / 0
- Calibration requirements passed / failed: 6 / 3
- Missing calibration gate ids: C4, C5, C6
- Calibrated flag data used: False
- Real hardware trace used: False
- Holdout improvement gate passed: False
- Holdout non-regression gate passed: True
- Calibration transfer ready: False
- Production decoder ready: False
- Threshold claim supported: False
- Validation errors: []

## Calibration Requirements

| gate | passed | label | missing to promote |
|---|---:|---|---|
| C1 | True | Per-shot detector and observable traces are persisted | Keep the same per-shot schema for calibrated device exports. |
| C2 | True | Hardware-like model consumes detector bitstrings | Preserve detector-bitstring input when replacing the toy observation model. |
| C3 | True | Profile sweep and holdout split are present | Retain model-selection/holdout separation for real calibration sweeps. |
| C4 | False | Calibrated flag data is available | Add calibrated leakage/erasure flag observations with a confusion matrix. |
| C5 | False | Real hardware traces are available | Run the same decoder interface on real or independently calibrated hardware traces. |
| C6 | False | Holdout improvement is observed | Show strictly fewer holdout logical failures under calibrated injection. |
| C7 | True | Holdout non-regression is preserved | Maintain non-regression after replacing the model with calibrated data. |
| C8 | True | Stress profile does not introduce failures | Re-check this guardrail on real high-leakage slices. |
| C9 | True | No forbidden production or threshold claim is made | Keep B2 as a negative-boundary result until C4-C6 pass on stronger data. |

## Claim Boundary

- calibration_transfer_guardrail_built: True
- calibration_transfer_ready: False
- production_decoder_claimed: False
- threshold_claimed: False
- new_code_claimed: False
- hardware_result_claimed: False
- calibrated_device_claimed: False
- quantum_advantage_claimed: False
- what_is_supported: The current B2 pipeline has per-shot traces, detector-bitstring input, profile sweeps, holdout accounting, and non-regression under the best hardware-like model.
- what_is_not_supported: The route has no calibrated flag data, no real hardware trace, and no holdout improvement, so it cannot support a production decoder, threshold, low-overhead QEC, or hardware claim.

## Next Gate

The next B2 gate must replace the model-derived leakage observations
with calibrated flag data or real hardware traces, then show holdout
logical-failure improvement while preserving non-regression.
