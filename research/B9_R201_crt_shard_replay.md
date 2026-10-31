# B9 R201 Twelfth Incremental CRT Shard Replay

- Date: `2026-10-31`
- Track: `B9`
- Status: `twelve planned prime shards complete; bounded CRT incomplete`
- New determinant artifacts: `48/56`
- Completed additional primes: `12/14`
- Bounded CRT integer reconstruction complete: `false`
- Characteristic-zero `D^44` divisibility verified: `false`
- Frozen holdouts executed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

What does a 397-bit modular certificate still fail to certify?

## Four New Determinants

The twelfth added prime in the frozen plan is `536,870,743`. All four public
`37x37` determinants complete exactly over `GF(536,870,743)`:

| Minor | Total degree | Terms | Artifact SHA-256 |
| --- | ---: | ---: | --- |
| 0 | 184 | 8,649 | `6a50534318a972c848385a4f983fcbde82b3cb00a419be4e3fb0b8a23bce98c7` |
| 1 | 184 | 4,468 | `5149559e8f122cb8a3a67b9726825f528b52a10669c107c37a06e4e583a7289d` |
| 2 | 184 | 4,770 | `343bb16c331f185cf085a21624e88ee011e3feb1d7688ed7ba29337d2b2bf295` |
| 3 | 184 | 2,760 | `1f6a384a84a5fe0371c9aa88a76fe242a02fd606a0ddd923eea8c38a61c05b57` |

Every artifact preserves its frozen row-set hash, source-matrix hash,
candidate-label hash, bridge-tool hash, degree, term count, and zero-credit
boundary.

## Independent Matrix Replay

`tools/b9_r201_crt_shard_replay.py` loads all 56 determinant artifacts now
available across

```text
1,000,003
536,870,723
536,870,909
536,870,879
536,870,869
536,870,849
536,870,839
536,870,837
536,870,819
536,870,813
536,870,791
536,870,779
536,870,767
536,870,743
```

For every artifact it rebuilds the frozen matrix at five public deterministic
points, computes the `37x37` determinant with project-owned modular Gaussian
elimination, evaluates the stored polynomial independently, and compares the
two values.

All `280/280` matrix-determinant point replays match. Artifact binding errors
are zero.

## Partial CRT State

The fourteen-prime modulus is

```text
307,828,386,481,262,099,184,937,518,886,461,844,137,659,868,881,310,668,588,689,315,445,859,409,378,454,044,228,525,695,175,684,495,226,754,765,384,757,908,431
```

with bit length `397`. For every minor, the verifier walks the complete
`17,205`-slot homogeneous degree-184 lattice, treats omitted modular terms as
zero, computes a symmetric partial CRT residue, and reduces that residue back
modulo every source prime.

| Minor | Support terms | Slot-prime round trips | Partial residue hash |
| --- | ---: | ---: | --- |
| 0 | 8,649 | 240,870/240,870 | `a5b03bfcdbdbb85b2b3d6de0fe1e5c2237a6bbc109a09285c086c89248b3850e` |
| 1 | 4,468 | 240,870/240,870 | `19f0ebbdfab6495ac0ac22ac9b897197cf1caed2690f954cf6d26519504103b6` |
| 2 | 4,770 | 240,870/240,870 | `be26aa18d457cac31aeb5377e2e048d190325600a9f7447c89f13a2d3a91470d` |
| 3 | 2,760 | 240,870/240,870 | `ff43773999bf35766538e8faf35d2ecaac21d3620a6d05fb8c77aaed7f9b1bf2` |

All four monomial supports match across all fourteen primes. Aggregate coefficient-slot round trips pass `963,480/963,480`.

## Why This Is Not Yet Integer Reconstruction

The proved uniqueness threshold has 427 bits; the current modulus has only 397 bits, so many different bounded and unbounded integers can share the same fourteen residues. The symmetric values hashed above are partial CRT representatives, not verified characteristic-zero coefficients.

The execution ledger is now:

```text
completed new primes:      12/14
completed new artifacts:  48/56
remaining new primes:      2
remaining new artifacts:  8
```

## Claim Boundary

This result verifies the first twelve modular execution shards and their
partial CRT round trips. It does not uniquely reconstruct an integer
coefficient, verify a characteristic-zero determinant, prove `D^44`
divisibility, compute a characteristic-zero gcd, emit the ideal-membership
certificate, open either frozen coupling, establish Quantum PCP or NLTS,
separate BQP, claim quantum-hardware evidence, promote the science result, or
add credit.

## Next Gate

Compute the four minors at planned prime `536,870,729`, rerun the full point
and slot-roundtrip audit, and advance the ledger to `52/56` artifacts only if
every binding and replay remains exact.
