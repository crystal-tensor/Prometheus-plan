# B9 R201 Exact Source-Dense Representation Binding

- Date: `2026-10-31`
- Track: `B9`
- Status: `exact source-dense matrix representation binding verified`
- Engineering characteristic-zero minors verified: `false`
- Ideal-membership certificate verified: `false`
- Frozen holdouts executed: `false`
- Readiness blocker closed: `false`
- Scientific promotion: `false`
- New credit: `0`

## Question

Can a `238x37` Pauli-coordinate matrix and a `256x37` dense Hermitian-coordinate matrix be proved to encode the same projective rank problem rather than merely agreeing at a few anchors?

## Exact Binding

`tools/b9_r201_representation_binding.py` reconstructs both public engineering representations at `n=4`, `J=13/32`. It extends the source matrix with its 18 identically zero Pauli rows, independently builds the complete 256-coordinate Hermitian map, and checks every candidate and commutator column as an exact polynomial matrix.

Let `T` map full real Pauli coefficients to Hermitian upper-triangle real coordinates, and let `Lambda` be diagonal with the declared powers of `D=a^2+b^2+c^2`. The certificate verifies

```text
C_dense = T * C_source * Lambda
M_dense = -2 * T * M_source * Lambda
```

for all `37/37` candidate columns and all `37/37` commutator columns. The minus sign comes from the opposite primitive Hamiltonian normalization, and the factor two comes from the source commutator convention.

The relative `D` exponents are:

- exponent `0`: 8 gamma columns plus parity, 9 columns total;
- exponent `1`: 13 bilinears with left endpoint 0;
- exponent `3`: 9 bilinears with left endpoint 1;
- exponent `5`: 5 bilinears with left endpoint 2;
- exponent `7`: 1 bilinear with left endpoint 3.

Their sum is `72`.

## Coordinate Inverse

The certificate constructs the complete `256x256` integer coordinate transform `T` and an integer inverse numerator `R`:

- `T` nonzeros: `2,176`;
- `R` nonzeros: `2,176`;
- `T` hash: `d7e4c0bd184c41a1fb4bd65091c03e9e97582678877ae2edaf16302e356a76d7`;
- `R` hash: `94f3a6461841ab405abcfe679f0f06b7e3ca832a031dc22c2dd02ef96607c0fd`;
- exact checks: `T*R = 16I` and `R*T = 16I`;
- Pauli-matrix coordinate roundtrips: `256/256`.

The map is invertible over `QQ`, `RR`, and odd-prime finite fields. Characteristic two is excluded. The projective column scaling also requires `D != 0`.

## Minor Consequence

For any 37-row Hermitian-coordinate selector `E`, the exact column binding implies

```text
det(E*M_dense) = (-2)^37 * D^72 * det(E*T*M_source_full)
```

The four audit-owned dense minor row hashes remain frozen. This identity prevents a degree-184 source minor from being mislabeled as a direct-gamma dense minor: the two are linked by a known nonzero projective factor, but they are not the same polynomial.

## Adversarial Checks

Five mutations are rejected:

1. dropping the commutator minus sign;
2. dropping the commutator factor two;
3. incrementing one bilinear `D` exponent;
4. reversing the `upper_im` coordinate sign;
5. reversing Kronecker site order.

The source and dense candidate-label hash is `8641091b90145c6d05a2c0f754232a8dc78e0c1b93004678b9895cabed0b1e65`. The independently rebuilt dense coefficient tensor hash is `48370c7d01167fbd734dad2ccc941f312254b268299a48a21265c4c7e43a4e42`, matching the pre-source manifest exactly.

## Remaining Gates

1. Lift the four frozen engineering minors with coefficient-bounded CRT and independent modular replay.
2. Emit the real `J=13/32` ideal-membership certificate.
3. Bind those emitted certificate generators to the frozen dense minors.
4. Run pre-source holdout reconstruction in an isolated filesystem without the main result path.
5. Publish a new readiness commit before changing execution permission.

This closes the source-dense matrix representation binding only. It does not verify a characteristic-zero engineering minor, certify an ideal, open `J=127/128` or `J=131/128`, exclude higher-order charges or nonlocal dualities, prove interacting nonintegrability, establish Quantum PCP or NLTS, separate BQP, claim hardware relevance, solve the frontier, promote the result, or add credit.
