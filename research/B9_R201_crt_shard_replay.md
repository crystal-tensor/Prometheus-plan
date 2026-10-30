# B9 R201 First Incremental CRT Shard Replay

- Date: `2026-10-31`
- Track: `B9`
- Status: `first planned prime shard complete; bounded CRT incomplete`
- New determinant artifacts: `4/56`
- Completed additional primes: `1/14`
- Bounded CRT integer reconstruction complete: `false`
- Characteristic-zero `D^44` divisibility verified: `false`
- Frozen holdouts executed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

Can the first planned CRT shard survive independent matrix replay and coefficient-slot round trips before its residues are mistaken for integer coefficients?

## Four New Determinants

The first added prime in the frozen plan is `536,870,909`. All four public `37x37` determinants complete exactly over `GF(536,870,909)`:

| Minor | Total degree | Terms | Artifact SHA-256 |
| --- | ---: | ---: | --- |
| 0 | 184 | 8,649 | `4be45712c2a8f060fc4f0395a8da24cce99c516e394f0c19226494321f6b690c` |
| 1 | 184 | 4,468 | `949fce6c4d6190b6b3726bc8c740e1dddb6025a80186713ba805f5670923cc24` |
| 2 | 184 | 4,770 | `b204cb2e02ee5d6885acca4e8aa8c016b8bc80ce774ed2cc52f57405c7920d2f` |
| 3 | 184 | 2,760 | `e04dc6934f5a4baa1d6ba56eb520a3208a834563c5ee212f0a1eacc32ce16ee1` |

Every artifact preserves its frozen row-set hash, source-matrix hash, candidate-label hash, bridge-tool hash, degree, term count, and zero-credit boundary.

## Independent Matrix Replay

`tools/b9_r201_crt_shard_replay.py` loads all 12 determinant artifacts now available across

```text
1,000,003
536,870,723
536,870,909
```

For every artifact it rebuilds the frozen matrix at five public deterministic points, computes the `37x37` determinant with project-owned modular Gaussian elimination, evaluates the stored polynomial independently, and compares the two values.

All `60/60` matrix-determinant point replays match. Artifact binding errors are zero.

## Partial CRT State

The three-prime modulus is

```text
288,231,137,763,316,424,491,621
```

with bit length `78`. For every minor, the verifier walks the complete `17,205`-slot homogeneous degree-184 lattice, treats omitted modular terms as zero, computes a symmetric partial CRT residue, and reduces that residue back modulo every source prime.

| Minor | Support terms | Slot-prime round trips | Partial residue hash |
| --- | ---: | ---: | --- |
| 0 | 8,649 | 51,615/51,615 | `b967d2021bea0fad1019f2274054b268e1550b81db05bbf9c37d9998c985a10f` |
| 1 | 4,468 | 51,615/51,615 | `1e8e250a9885709bc5bff300777c44fd66b4ae4fa05dfdabcdf7e37b74f47bbb` |
| 2 | 4,770 | 51,615/51,615 | `6b7a4dfaa1b0e54e914f1dac8f57c3e04fd4d6115a9cb45090d5f73042329faa` |
| 3 | 2,760 | 51,615/51,615 | `840024588abfa532c9a0eaae31a93a23467c97ce7a298aaa8f2c13bc6ab83cb8` |

All four monomial supports match across all three primes. Aggregate coefficient-slot round trips pass `206,460/206,460`.

## Why This Is Not Yet Integer Reconstruction

The proved uniqueness threshold has 427 bits. The current modulus has only 78 bits, so many different bounded and unbounded integers can share the same three residues. The symmetric values hashed above are partial CRT representatives, not verified characteristic-zero coefficients.

The execution ledger is now:

```text
completed new primes:      1/14
completed new artifacts:   4/56
remaining new primes:     13
remaining new artifacts:  52
```

## Claim Boundary

This result verifies the first modular execution shard and its partial CRT round trips. It does not uniquely reconstruct an integer coefficient, verify a characteristic-zero determinant, prove `D^44` divisibility, compute a characteristic-zero gcd, emit the ideal-membership certificate, open either frozen coupling, establish Quantum PCP or NLTS, separate BQP, claim hardware evidence, promote the science result, or add credit.

## Next Gate

Compute the four minors at planned prime `536,870,879`, rerun the full point and slot-roundtrip audit, and advance the ledger to `8/56` artifacts only if every binding and replay remains exact.
