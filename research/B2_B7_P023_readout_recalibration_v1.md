# #022/B2 decision: keep 71 qubits without readout recalibration in this stress

Date: 2026-11-27

The 71-active-qubit distance-6 memory passed the original 1,000-round X and Z error gate with its **unchanged** decoder under a predeclared 25% increase in the measurement-flip probability. A label-free recalibrator was implemented and tested, but did not improve the acceptance decision: it recovered three Z failures while adding two net X failures. Retain the 71-qubit circuit and its frozen decoder for this modeled condition; do not add the recalibrator to the accepted path on this evidence.

## What was changed and what stayed fixed

We regenerated the frozen d6 correlated-matching candidate and the d7 independent-matching reference and checked their circuit and decoder error-model hashes against the prior receipts. In the sampler only, the independent error probability immediately before measurement rises from 0.100% to 0.125%. No gate schedule or other noise rate changes. [Google's below-threshold surface-code experiment](https://pmc.ncbi.nlm.nih.gov/articles/PMC11864966/) reports periodic calibration of readout and frequency; this motivates separating readout from the other channels, but does not determine the magnitude or validate this synthetic model. The [public hardware traces](https://zenodo.org/records/13273331) are not traces of these two frozen schedules.

The replacement decoder path takes 256 independent calibration shots per design and basis. If detector \(i\) involves \(k_i\) measurements, its expected parity sign is \(a_i(1-2p)^{k_i}\), where \(a_i\) is the expected sign with no measurement flips and the other channels held fixed. The fitter inverts the mean of these expectations using only aggregate detector counts. It sees neither logical labels nor the injected probability. For each arm we rebuild the decoder error model once at its estimate and lock it before any holdout decoding. The frozen and recalibrated policies decode the same holdout shots within each design/basis; different design/basis pairs use different streams.

The [protocol](../benchmarks/B2_B7_P023_readout_recalibration_v1.json), data bindings and runner were frozen in local commit `527fa3d692cd16f688ca150fa7e1c180fbfdb793` before drawing the challenge salt and sampling. This was a local freeze, not a publicly timestamped preregistration. The estimate and decision rule were not revised after sampling.

## Acceptance result

Each row has 102,400 fresh shots of 1,000 rounds. Each basis must meet the one-sided exact Clopper–Pearson upper bound of 1%, at tail probability \(2^{-128}\); 636 failures pass, 637 fail. Compare qubit-rounds only after both X and Z pass for both designs with a given policy.

| Design | Basis | Fitted readout flip | Frozen failures / upper bound | Recalibrated failures / upper bound | Failures recovered / introduced |
| --- | --- | ---: | ---: | ---: | ---: |
| d7, 97 qubits | X | 0.12470% | 325 / 0.6057% | 325 / 0.6057% | 1 / 1 |
| d7, 97 qubits | Z | 0.12408% | 283 / 0.5497% | 278 / 0.5430% | 8 / 3 |
| d6, 71 qubits | X | 0.12354% | 518 / 0.8533% | 520 / 0.8558% | 5 / 7 |
| d6, 71 qubits | Z | 0.11644% | 446 / 0.7625% | 443 / 0.7587% | 3 / 0 |

Both policies meet the two-basis gate for both designs, so the tested cost goes from 97,000 to 71,000 active-qubit-rounds (26.8% lower; 1.3662× reference/candidate, above the original 1.25× gate). The recalibrator changed individual decisions, but the paired differences are small and this trial shows neither an acceptance rescue nor a consistent improvement across bases. The previously archived nominal-condition counts were not drawn from the same shot stream and do not measure an effect of increasing measurement noise.

## Audit and reproduce

The [joint evidence](../results/B2_B7_P023_readout_recalibration_evidence_v1.json) binds the four [d7 X](../results/B2_B7_P023_readout_recalibration_reference_x_raw_v1.json), [d7 Z](../results/B2_B7_P023_readout_recalibration_reference_z_raw_v1.json), [d6 X](../results/B2_B7_P023_readout_recalibration_candidate_x_raw_v1.json), and [d6 Z](../results/B2_B7_P023_readout_recalibration_candidate_z_raw_v1.json) receipts. The separate [auditor](../tools/b2_b7_p023_readout_recalibration_audit_v1.py) recounts all archived holdout failure bits, reproduces the first holdout chunk of each row with both decoders, regenerates the calibration and checks the fit with a separate solver, and checks the exact cutoff by the binomial CDF. Evidence ID: `3fd6b59647b82c3e307eec5cbf43e41681b895a617b32127278b14e206b3baf3`.

Use a clone with full history, Python 3.12.6, Stim 1.16.0, PyMatching 2.4.0, NumPy 2.4.6 and SciPy 1.17.1. The first command checks the archived evidence; the loop regenerates all four holdout receipts in a new directory.

```sh
export OPENBLAS_NUM_THREADS=1
python3 -B tools/b2_b7_p023_readout_recalibration_audit_v1.py
qec_replay_dir=$(mktemp -d)
for qec_design in reference candidate; do
  for qec_basis in x z; do
    python3 -B tools/b2_b7_p023_readout_recalibration_v1.py \
      --design "$qec_design" --basis "$qec_basis" \
      --freeze 527fa3d692cd16f688ca150fa7e1c180fbfdb793 \
      --salt 1b685d21f723196f148c6b6eb8b71d0d8ae44334e7aa169c27130be07dc90887 \
      --artifact-dir "$qec_replay_dir"
  done
done
python3 -B tools/b2_b7_p023_readout_recalibration_audit_v1.py --artifact-dir "$qec_replay_dir" --write
```

This result does not establish temporal correlation resilience, calibrated-device error rates, a controller deadline, full #022/B2, #021/B7 resource credit, or scalable #023. The 120-qubit/depth-7,000 question is outside acceptance. The next experiment should target a remaining acceptance gate, not tune this perturbation after seeing its outcome.
