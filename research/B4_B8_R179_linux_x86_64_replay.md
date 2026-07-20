# B4/B8/B10 R179 Linux x86-64 Replay

- Status: `linux_x86_64_fixed_superaccumulator_rejected_on_frozen_matrix`
- Frozen matrix requirements: `15/16`
- Platform requirements: `2/2`
- Payload hash: `7fec1de65dfe4655afff70ef600a14d1a26f7904ec00c1a6184d948a2de83274`

## Research Question

Does the R176 exact-selection and performance result survive an independently built Ubuntu x86-64 accelerator?

## Result

The Linux matrix executes `3024` direct Qiskit calls, including `2400` recorded calls and `624` warmups across `39` isolated processes. Source, BigUint, and fixed policies match `800/800`, `800/800`, and `800/800`; BigUint and fixed agree on `800/800` mappings.

## Performance

Aggregate BigUint/source is `1.906728`; fixed/source is `2.152808`; fixed/BigUint is `1.129059`. The worst fixed/source cell is `2.459848` and the worst fixed/source process-RSS ratio is `1.001142`.

## Platform Evidence

All `39/39` worker manifests report Linux x86-64. The accelerator SHA-256 is `0469ab075ef40a841da017e2b9cebeac5fe2c1ac8fc95b77c99dc773ea3ff054` and the build-manifest payload hash is `19ef9e3ef5d8068eb7a3319374b94bea18b8f6021d13dd94c0f4cadd4a35b3ea`.

## Claim Boundary

This supports one independently built Ubuntu x86-64 replay of the frozen R176 matrix. It is not an upstream-accepted or production Qiskit patch, a confirmed Qiskit bug, broad graph-scale evidence, hardware evidence, quantum advantage, BQP separation, solved B4/B8/B10, or new credit.
