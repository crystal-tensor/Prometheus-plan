# B9 R201 Second Incremental CRT Shard Replay

- Date: `2026-10-31`
- Track: `B9`
- Status: `two planned prime shards complete; bounded CRT incomplete`
- New determinant artifacts: `8/56`
- Completed additional primes: `2/14`
- Bounded CRT integer reconstruction complete: `false`
- Characteristic-zero `D^44` divisibility verified: `false`
- Frozen holdouts executed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

Can a second planned CRT shard preserve every matrix, support, and coefficient-slot invariant without tempting us to treat a 107-bit residue as a 427-bit integer proof?

## Four New Determinants

The second added prime in the frozen plan is `536,870,879`. All four public `37x37` determinants complete exactly over `GF(536,870,879)`:

| Minor | Total degree | Terms | Artifact SHA-256 |
| --- | ---: | ---: | --- |
| 0 | 184 | 8,649 | `3bd259c6d9ffeb3255d76ebdccde4814b46037d1ccb48eb8803b877c8581c4af` |
| 1 | 184 | 4,468 | `256932177f40634241b65fe76522bc4a0cd3f8f938035c52e88803b14565dbd5` |
| 2 | 184 | 4,770 | `5459e77794f7e38c5ca44c7e693e149a33bd66debfdd5b43b5216a5b90b51a89` |
| 3 | 184 | 2,760 | `5f9591180b570f137d887695c94b02035625bd46c8e39ffe37e7fcdbc3cdbc53` |

Every artifact preserves its frozen row-set hash, source-matrix hash, candidate-label hash, bridge-tool hash, degree, term count, and zero-credit boundary.

## Independent Matrix Replay

`tools/b9_r201_crt_shard_replay.py` loads all 16 determinant artifacts now available across

```text
1,000,003
536,870,723
536,870,909
536,870,879
```

For every artifact it rebuilds the frozen matrix at five public deterministic points, computes the `37x37` determinant with project-owned modular Gaussian elimination, evaluates the stored polynomial independently, and compares the two values.

All `80/80` matrix-determinant point replays match. Artifact binding errors are zero.

## Partial CRT State

The four-prime modulus is

```text
154,742,904,286,161,782,771,953,694,404,859
```

with bit length `107`. For every minor, the verifier walks the complete `17,205`-slot homogeneous degree-184 lattice, treats omitted modular terms as zero, computes a symmetric partial CRT residue, and reduces that residue back modulo every source prime.

| Minor | Support terms | Slot-prime round trips | Partial residue hash |
| --- | ---: | ---: | --- |
| 0 | 8,649 | 68,820/68,820 | `59c094dda70e69ecc407ba3433ac61b49f86c40a751690eaadf37866755c72e0` |
| 1 | 4,468 | 68,820/68,820 | `c0d419736be42898e8d9c329c678b02073f149b7b69eafed84c9d766e67a79db` |
| 2 | 4,770 | 68,820/68,820 | `f6b2cf2c46521329087e4abd130cee7deb2590d8bdeeaf1b7000c7d1dd8a999c` |
| 3 | 2,760 | 68,820/68,820 | `d64fc6cf87eef6a01a437c5669d098c0ea8426035ee692d16a5ec41236b24bf1` |

All four monomial supports match across all four primes. Aggregate coefficient-slot round trips pass `275,280/275,280`.

## Why This Is Not Yet Integer Reconstruction

The proved uniqueness threshold has 427 bits. The current modulus has only 107 bits, so many different bounded and unbounded integers can share the same four residues. The symmetric values hashed above are partial CRT representatives, not verified characteristic-zero coefficients.

The execution ledger is now:

```text
completed new primes:      2/14
completed new artifacts:   8/56
remaining new primes:     12
remaining new artifacts:  48
```

## Claim Boundary

This result verifies the first two modular execution shards and their partial CRT round trips. It does not uniquely reconstruct an integer coefficient, verify a characteristic-zero determinant, prove `D^44` divisibility, compute a characteristic-zero gcd, emit the ideal-membership certificate, open either frozen coupling, establish Quantum PCP or NLTS, separate BQP, claim hardware evidence, promote the science result, or add credit.

## Next Gate

Compute the four minors at planned prime `536,870,869`, rerun the full point and slot-roundtrip audit, and advance the ledger to `12/56` artifacts only if every binding and replay remains exact.
