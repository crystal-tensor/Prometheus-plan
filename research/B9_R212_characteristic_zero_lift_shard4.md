# B9 R212 Characteristic-Zero Lift: Fourth CRT Shard

## Question

When do hundreds of thousands of exact modular checks become an integer
theorem, rather than a larger checkpoint?

## Result

R212 completes minors 4, 5, and 6 at the fourth planned prime `536870849`.
Together with the two classification primes and the R209-R211 shards, the
partial reconstruction now spans six pairwise-coprime fields.

| Quantity | R212 result |
|---|---:|
| completed planned primes | `4/14` |
| completed new determinant artifacts | `12/42` |
| remaining new determinant artifacts | `30` |
| combined modulus | `44601596703050957462716084525238582972915796217879` |
| combined modulus bit length | `165` |
| worst uniqueness threshold | `428` bits |
| primary CRT round trips | `309690/309690` |
| independent CRT round trips | `309690/309690` |
| independent matrix replays | `48/48` |
| independent `D^44` recompositions | `48/48` |

The modulus grows by another 29 bits, but it remains below the proved
428-bit threshold. The partial symmetric representatives therefore remain
non-promotable.

## Fourth Prime Shard

The new field preserves the determinant and quotient supports seen in the
first three shards:

| Minor | Determinant terms | Degree-96 quotient terms | Modular division |
|---:|---:|---:|---|
| 4 / R204 | 5,997 | 1,113 | exact `D^44` |
| 5 / R206 | 6,555 | 1,363 | exact `D^44` |
| 6 / R208 | 5,309 | 821 | exact `D^44` |

Every artifact also replays the four frozen public matrix points and verifies
the quotient recomposition at those points.

## Independent Audit

The independent path validates the exact artifact grid for all six primes,
then rebuilds every completed new-prime matrix with custom modular Gaussian
elimination. It imports none of the primary CRT state when recombining the
17,205 homogeneous coefficient slots with `sympy.ntheory.modular.crt`.

All `48/48` matrix values and `48/48` `D^44` recompositions match. Both CRT
implementations pass `309690/309690` residue round trips and agree on every
nonzero count, maximum symmetric residue, and partial payload hash.

Adversarial overlay tests additionally reject a changed determinant
coefficient and a missing frozen replay point through the immutable artifact
grid binding.

## Claim Boundary

This is a fourth exact modular shard and an independently replayed partial CRT
state. It is not an integer reconstruction, characteristic-zero `D^44`
certificate, rational Nullstellensatz identity, global-rank theorem, Quantum
PCP or NLTS result, quantum-hardware result, scientific promotion, or new
credit. The frozen `J=127/128,131/128` holdouts remain sealed.

## Next Gate

Compute minors 4, 5, and 6 at the fifth planned prime `536870839`. Rerun both
CRT implementations over seven total primes, preserve the full artifact-grid
and frozen-point checks, and continue to reject promotion until the combined
modulus exceeds twice every proved coefficient bound.
