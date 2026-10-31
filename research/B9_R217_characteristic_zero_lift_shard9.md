# B9 R217 Characteristic-Zero Lift: Ninth CRT Shard

## Question

Can five remaining primes close a 118-bit proof gap without moving the rules?

## Result

R217 completes minors 4, 5, and 6 at the ninth planned prime `536870791`.
Together with the two classification primes and the R209-R216 shards, the
partial reconstruction now spans eleven pairwise-coprime fields.

| Quantity | R217 result |
|---|---:|
| completed planned primes | `9/14` |
| completed new determinant artifacts | `27/42` |
| remaining new determinant artifacts | `15` |
| combined modulus | `1989295978876335436236635129448193062848946245037596892127411701755604012176804025112665855269` |
| combined modulus bit length | `310` |
| worst uniqueness threshold | `428` bits |
| remaining worst-case bit gap | `118` bits |
| primary CRT round trips | `567765/567765` |
| independent CRT round trips | `567765/567765` |
| independent matrix replays | `108/108` |
| independent `D^44` recompositions | `108/108` |

The modulus gains another 29 bits. The five remaining planned primes are large
enough in aggregate to cross the current worst-case threshold, but the
acceptance rules remain fixed: no partial symmetric residue is promoted before
the modulus exceeds twice every proved coefficient bound.

## Ninth Prime Shard

The new field preserves the determinant and quotient supports seen in the
first eight shards:

| Minor | Determinant terms | Degree-96 quotient terms | Modular division |
|---:|---:|---:|---|
| 4 / R204 | 5,997 | 1,113 | exact `D^44` |
| 5 / R206 | 6,555 | 1,363 | exact `D^44` |
| 6 / R208 | 5,309 | 821 | exact `D^44` |

Every artifact also replays the four frozen public matrix points and verifies
the quotient recomposition at those points.

## Independent Audit

The independent path validates the exact artifact grid for all eleven primes,
then rebuilds every completed new-prime matrix with custom modular Gaussian
elimination. It imports none of the primary CRT state when recombining the
17,205 homogeneous coefficient slots with `sympy.ntheory.modular.crt`.

All `108/108` matrix values and `108/108` `D^44` recompositions match. Both CRT
implementations pass `567765/567765` residue round trips and agree on every
nonzero count, maximum symmetric residue, and partial payload hash.

Adversarial overlay tests additionally reject a changed determinant
coefficient and a missing frozen replay point through the immutable artifact
grid binding.

## Claim Boundary

This is a ninth exact modular shard and an independently replayed partial CRT
state. It is not an integer reconstruction, characteristic-zero `D^44`
certificate, rational Nullstellensatz identity, global-rank theorem, Quantum
PCP or NLTS result, quantum-hardware result, scientific promotion, or new
credit. The frozen `J=127/128,131/128` holdouts remain sealed.

## Next Gate

Compute minors 4, 5, and 6 at the tenth planned prime `536870779`. Rerun both
CRT implementations over twelve total primes, preserve the full artifact-grid
and frozen-point checks, and continue to reject promotion until the combined
modulus exceeds twice every proved coefficient bound.
