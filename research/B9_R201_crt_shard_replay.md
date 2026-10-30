# B9 R201 Fifth Incremental CRT Shard Replay

- Date: `2026-10-31`
- Track: `B9`
- Status: `five planned prime shards complete; bounded CRT incomplete`
- New determinant artifacts: `20/56`
- Completed additional primes: `5/14`
- Bounded CRT integer reconstruction complete: `false`
- Characteristic-zero `D^44` divisibility verified: `false`
- Frozen holdouts executed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

Can seven agreeing finite fields still leave the integer answer fundamentally undetermined?

## Four New Determinants

The fifth added prime in the frozen plan is `536,870,839`. All four public `37x37` determinants complete exactly over `GF(536,870,839)`:

| Minor | Total degree | Terms | Artifact SHA-256 |
| --- | ---: | ---: | --- |
| 0 | 184 | 8,649 | `0f71427dd9f3d22b82329c05f4127ee3ce2d5fe7ba2eedb8c0575c13b5ded86f` |
| 1 | 184 | 4,468 | `7989922fdc3f4ec81ef616d9e79c9029cf54da9960c5f351916886c6050bc6dd` |
| 2 | 184 | 4,770 | `de855c8f3266434c7eae4bf39f2a075559f40fc3c345300d70e6c0af22e1c154` |
| 3 | 184 | 2,760 | `691a6bab643d97e154deede737d0e0ed0f40a9b614e81739cfa4ebe18a74bf03` |

Every artifact preserves its frozen row-set hash, source-matrix hash, candidate-label hash, bridge-tool hash, degree, term count, and zero-credit boundary.

## Independent Matrix Replay

`tools/b9_r201_crt_shard_replay.py` loads all 28 determinant artifacts now available across

```text
1,000,003
536,870,723
536,870,909
536,870,879
536,870,869
536,870,849
536,870,839
```

For every artifact it rebuilds the frozen matrix at five public deterministic points, computes the `37x37` determinant with project-owned modular Gaussian elimination, evaluates the stored polynomial independently, and compares the two values.

All `140/140` matrix-determinant point replays match. Artifact binding errors are zero.

## Partial CRT State

The seven-prime modulus is

```text
23,945,296,642,706,601,392,761,695,517,859,754,715,840,417,791,845,725,530,481
```

with bit length `194`. For every minor, the verifier walks the complete `17,205`-slot homogeneous degree-184 lattice, treats omitted modular terms as zero, computes a symmetric partial CRT residue, and reduces that residue back modulo every source prime.

| Minor | Support terms | Slot-prime round trips | Partial residue hash |
| --- | ---: | ---: | --- |
| 0 | 8,649 | 120,435/120,435 | `aea814c41b72f979f0e7950aec23c6d7764f6447b709b7c9d775ffe064370f86` |
| 1 | 4,468 | 120,435/120,435 | `1d3c0386cbe43289cb5cfa6298b2b0725e34191bf2a74bc25ac315b324a17104` |
| 2 | 4,770 | 120,435/120,435 | `5159a0ff250cf50bc0d866efa63583ba26c8fbfbcb0b8f67d778f73a21082849` |
| 3 | 2,760 | 120,435/120,435 | `b3be2acb2acd6de7f46e92c62b26c855509585fa645a589e4de47fd89cd43560` |

All four monomial supports match across all seven primes. Aggregate coefficient-slot round trips pass `481,740/481,740`.

## Why This Is Not Yet Integer Reconstruction

The proved uniqueness threshold has 427 bits. The current modulus has only 194 bits, so many different bounded and unbounded integers can share the same seven residues. The symmetric values hashed above are partial CRT representatives, not verified characteristic-zero coefficients.

The execution ledger is now:

```text
completed new primes:      5/14
completed new artifacts:  20/56
remaining new primes:      9
remaining new artifacts:  36
```

## Claim Boundary

This result verifies the first five modular execution shards and their partial CRT round trips. It does not uniquely reconstruct an integer coefficient, verify a characteristic-zero determinant, prove `D^44` divisibility, compute a characteristic-zero gcd, emit the ideal-membership certificate, open either frozen coupling, establish Quantum PCP or NLTS, separate BQP, claim hardware evidence, promote the science result, or add credit.

## Next Gate

Compute the four minors at planned prime `536,870,837`, rerun the full point and slot-roundtrip audit, and advance the ledger to `24/56` artifacts only if every binding and replay remains exact.
