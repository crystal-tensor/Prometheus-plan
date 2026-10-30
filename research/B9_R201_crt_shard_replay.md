# B9 R201 Eighth Incremental CRT Shard Replay

- Date: `2026-10-31`
- Track: `B9`
- Status: `eight planned prime shards complete; bounded CRT incomplete`
- New determinant artifacts: `32/56`
- Completed additional primes: `8/14`
- Bounded CRT integer reconstruction complete: `false`
- Characteristic-zero `D^44` divisibility verified: `false`
- Frozen holdouts executed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

Can a tenth exact prime world expose one shared construction error?

## Four New Determinants

The eighth added prime in the frozen plan is `536,870,813`. All four public
`37x37` determinants complete exactly over `GF(536,870,813)`:

| Minor | Total degree | Terms | Artifact SHA-256 |
| --- | ---: | ---: | --- |
| 0 | 184 | 8,649 | `1530d30eef1318e72839d3f3fdaf2990844c40a6ad42a636fe00c1d070f32201` |
| 1 | 184 | 4,468 | `30d8ee9acb69b7c4b15ebdee85d62027865876a355074fe8ec7bafe4ebb0b2d8` |
| 2 | 184 | 4,770 | `da719639177f09d828d0534738bcfdbc46e6520799a9ed4d78645ac1d7d24618` |
| 3 | 184 | 2,760 | `4f65ad811e446e5fdfbd7efec203aec535bb184d9a22a7242c14b6937a2acafe` |

Every artifact preserves its frozen row-set hash, source-matrix hash,
candidate-label hash, bridge-tool hash, degree, term count, and zero-credit
boundary.

## Independent Matrix Replay

`tools/b9_r201_crt_shard_replay.py` loads all 40 determinant artifacts now
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
```

For every artifact it rebuilds the frozen matrix at five public deterministic
points, computes the `37x37` determinant with project-owned modular Gaussian
elimination, evaluates the stored polynomial independently, and compares the
two values.

All `200/200` matrix-determinant point replays match. Artifact binding errors
are zero.

## Partial CRT State

The ten-prime modulus is

```text
3,705,353,340,551,424,106,506,541,402,525,646,180,756,639,906,374,785,236,039,059,725,556,207,456,584,845,244,659
```

with bit length `281`. For every minor, the verifier walks the complete
`17,205`-slot homogeneous degree-184 lattice, treats omitted modular terms as
zero, computes a symmetric partial CRT residue, and reduces that residue back
modulo every source prime.

| Minor | Support terms | Slot-prime round trips | Partial residue hash |
| --- | ---: | ---: | --- |
| 0 | 8,649 | 172,050/172,050 | `a5b03bfcdbdbb85b2b3d6de0fe1e5c2237a6bbc109a09285c086c89248b3850e` |
| 1 | 4,468 | 172,050/172,050 | `a535b079d7a8f79257f4bf54c8865dd5020f0c94c283202661700cae30d942b5` |
| 2 | 4,770 | 172,050/172,050 | `7dec77903cd9cf8bf1df5b3275d3c29dfe132613a24b7a0af7429bf785a6c9a5` |
| 3 | 2,760 | 172,050/172,050 | `ff43773999bf35766538e8faf35d2ecaac21d3620a6d05fb8c77aaed7f9b1bf2` |

All four monomial supports match across all ten primes. Aggregate coefficient-slot round trips pass `688,200/688,200`.

## Why This Is Not Yet Integer Reconstruction

The proved uniqueness threshold has 427 bits; the current modulus has only 281 bits, so many different bounded and unbounded integers can share the same ten residues. The symmetric values hashed above are partial CRT representatives, not verified characteristic-zero coefficients.

The execution ledger is now:

```text
completed new primes:      8/14
completed new artifacts:  32/56
remaining new primes:      6
remaining new artifacts:  24
```

## Claim Boundary

This result verifies the first eight modular execution shards and their
partial CRT round trips. It does not uniquely reconstruct an integer
coefficient, verify a characteristic-zero determinant, prove `D^44`
divisibility, compute a characteristic-zero gcd, emit the ideal-membership
certificate, open either frozen coupling, establish Quantum PCP or NLTS,
separate BQP, claim quantum-hardware evidence, promote the science result, or
add credit.

## Next Gate

Compute the four minors at planned prime `536,870,791`, rerun the full point
and slot-roundtrip audit, and advance the ledger to `36/56` artifacts only if
every binding and replay remains exact.
