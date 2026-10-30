# B9 R201 Sixth Incremental CRT Shard Replay

- Date: `2026-10-31`
- Track: `B9`
- Status: `six planned prime shards complete; bounded CRT incomplete`
- New determinant artifacts: `24/56`
- Completed additional primes: `6/14`
- Bounded CRT integer reconstruction complete: `false`
- Characteristic-zero `D^44` divisibility verified: `false`
- Frozen holdouts executed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

When does repeated exact agreement become a reason for confidence, and when does it become complacency?

## Four New Determinants

The sixth added prime in the frozen plan is `536,870,837`. All four public `37x37` determinants complete exactly over `GF(536,870,837)`:

| Minor | Total degree | Terms | Artifact SHA-256 |
| --- | ---: | ---: | --- |
| 0 | 184 | 8,649 | `d4fb75d8abe43420b0a3adc3a0bedb05d53f735f4878e35e66291973fab1bfcd` |
| 1 | 184 | 4,468 | `ac4cb3c6eab59364f4165d4ae35af230ad8e7900162b4c96bd0952978a75cb46` |
| 2 | 184 | 4,770 | `aef463088b8ef650e17f3c0acf5f1fdde88be8bd451f48e1eee21b4cf363fdbf` |
| 3 | 184 | 2,760 | `90c59f3e0fc006c6bc97766255a6d840981ded8b2d6c1ec8efb324f24eaecf81` |

Every artifact preserves its frozen row-set hash, source-matrix hash, candidate-label hash, bridge-tool hash, degree, term count, and zero-credit boundary.

## Independent Matrix Replay

`tools/b9_r201_crt_shard_replay.py` loads all 32 determinant artifacts now available across

```text
1,000,003
536,870,723
536,870,909
536,870,879
536,870,869
536,870,849
536,870,839
536,870,837
```

For every artifact it rebuilds the frozen matrix at five public deterministic points, computes the `37x37` determinant with project-owned modular Gaussian elimination, evaluates the stored polynomial independently, and compares the two values.

All `160/160` matrix-determinant point replays match. Artifact binding errors are zero.

## Partial CRT State

The eight-prime modulus is

```text
12,855,531,450,783,183,035,157,337,214,212,514,962,907,942,258,337,906,440,421,603,482,597
```

with bit length `223`. For every minor, the verifier walks the complete `17,205`-slot homogeneous degree-184 lattice, treats omitted modular terms as zero, computes a symmetric partial CRT residue, and reduces that residue back modulo every source prime.

| Minor | Support terms | Slot-prime round trips | Partial residue hash |
| --- | ---: | ---: | --- |
| 0 | 8,649 | 137,640/137,640 | `12b97bb5bb34e8170c82c62245661717dd4c56dcd519fbce18176ac70a06960f` |
| 1 | 4,468 | 137,640/137,640 | `f2dfd75110d23cb8c21563ad98b36ab010ffba9a6380f8e078e732a8cec079a0` |
| 2 | 4,770 | 137,640/137,640 | `ebef8367c28d4011728daebf3baffe9bdb49f2412bbf7903cd39b00f0eb0db51` |
| 3 | 2,760 | 137,640/137,640 | `97704e6dca8a8faf802aae2c63c1502f8cf22a724feca2d9e69d6999bc3dea3f` |

All four monomial supports match across all eight primes. Aggregate coefficient-slot round trips pass `550,560/550,560`.

## Why This Is Not Yet Integer Reconstruction

The proved uniqueness threshold has 427 bits. The current modulus has only 223 bits, so many different bounded and unbounded integers can share the same eight residues. The symmetric values hashed above are partial CRT representatives, not verified characteristic-zero coefficients.

The execution ledger is now:

```text
completed new primes:      6/14
completed new artifacts:  24/56
remaining new primes:      8
remaining new artifacts:  32
```

## Claim Boundary

This result verifies the first six modular execution shards and their partial CRT round trips. It does not uniquely reconstruct an integer coefficient, verify a characteristic-zero determinant, prove `D^44` divisibility, compute a characteristic-zero gcd, emit the ideal-membership certificate, open either frozen coupling, establish Quantum PCP or NLTS, separate BQP, claim hardware evidence, promote the science result, or add credit.

## Next Gate

Compute the four minors at planned prime `536,870,819`, rerun the full point and slot-roundtrip audit, and advance the ledger to `28/56` artifacts only if every binding and replay remains exact.
