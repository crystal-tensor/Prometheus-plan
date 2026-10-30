# B9 R201 Ninth Incremental CRT Shard Replay

- Date: `2026-10-31`
- Track: `B9`
- Status: `nine planned prime shards complete; bounded CRT incomplete`
- New determinant artifacts: `36/56`
- Completed additional primes: `9/14`
- Bounded CRT integer reconstruction complete: `false`
- Characteristic-zero `D^44` divisibility verified: `false`
- Frozen holdouts executed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

When eleven exact prime worlds agree, what error can still survive them all?

## Four New Determinants

The ninth added prime in the frozen plan is `536,870,791`. All four public
`37x37` determinants complete exactly over `GF(536,870,791)`:

| Minor | Total degree | Terms | Artifact SHA-256 |
| --- | ---: | ---: | --- |
| 0 | 184 | 8,649 | `1923d57768db69fec3a15c8cb290a0cd5595b3e69ad8897cdea397c132e728ff` |
| 1 | 184 | 4,468 | `4481afc6efc76ca2e07a33d7a3a5d4528b04c6249fad19b0c78865113f0a39a5` |
| 2 | 184 | 4,770 | `fd3bafdc797ab507f1116337248bc4adc57c2ee756cdc342e05931b7310921b2` |
| 3 | 184 | 2,760 | `0991e46aefeb1dfa1f2dabef958c655aea74dcbcfb2be350f8f13e8d29d1baa2` |

Every artifact preserves its frozen row-set hash, source-matrix hash,
candidate-label hash, bridge-tool hash, degree, term count, and zero-credit
boundary.

## Independent Matrix Replay

`tools/b9_r201_crt_shard_replay.py` loads all 44 determinant artifacts now
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
```

For every artifact it rebuilds the frozen matrix at five public deterministic
points, computes the `37x37` determinant with project-owned modular Gaussian
elimination, evaluates the stored polynomial independently, and compares the
two values.

All `220/220` matrix-determinant point replays match. Artifact binding errors
are zero.

## Partial CRT State

The eleven-prime modulus is

```text
1,989,295,978,876,335,436,236,635,129,448,193,062,848,946,245,037,596,892,127,411,701,755,604,012,176,804,025,112,665,855,269
```

with bit length `310`. For every minor, the verifier walks the complete
`17,205`-slot homogeneous degree-184 lattice, treats omitted modular terms as
zero, computes a symmetric partial CRT residue, and reduces that residue back
modulo every source prime.

| Minor | Support terms | Slot-prime round trips | Partial residue hash |
| --- | ---: | ---: | --- |
| 0 | 8,649 | 189,255/189,255 | `a5b03bfcdbdbb85b2b3d6de0fe1e5c2237a6bbc109a09285c086c89248b3850e` |
| 1 | 4,468 | 189,255/189,255 | `19f0ebbdfab6495ac0ac22ac9b897197cf1caed2690f954cf6d26519504103b6` |
| 2 | 4,770 | 189,255/189,255 | `be26aa18d457cac31aeb5377e2e048d190325600a9f7447c89f13a2d3a91470d` |
| 3 | 2,760 | 189,255/189,255 | `ff43773999bf35766538e8faf35d2ecaac21d3620a6d05fb8c77aaed7f9b1bf2` |

All four monomial supports match across all eleven primes. Aggregate coefficient-slot round trips pass `757,020/757,020`.

## Why This Is Not Yet Integer Reconstruction

The proved uniqueness threshold has 427 bits; the current modulus has only 310 bits, so many different bounded and unbounded integers can share the same eleven residues. The symmetric values hashed above are partial CRT representatives, not verified characteristic-zero coefficients.

The execution ledger is now:

```text
completed new primes:      9/14
completed new artifacts:  36/56
remaining new primes:      5
remaining new artifacts:  20
```

## Claim Boundary

This result verifies the first nine modular execution shards and their partial
CRT round trips. It does not uniquely reconstruct an integer coefficient,
verify a characteristic-zero determinant, prove `D^44` divisibility, compute
a characteristic-zero gcd, emit the ideal-membership certificate, open either
frozen coupling, establish Quantum PCP or NLTS, separate BQP, claim
quantum-hardware evidence, promote the science result, or add credit.

## Next Gate

Compute the four minors at planned prime `536,870,779`, rerun the full point
and slot-roundtrip audit, and advance the ledger to `40/56` artifacts only if
every binding and replay remains exact.
