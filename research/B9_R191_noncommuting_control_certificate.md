# B9 R191 Noncommuting Integrable Negative Control

## Verdict

- Status: `checked_noncommuting_integrable_negative_control`
- Requirements: `12/12`
- Protocol hash: `8ab88e880d797cd8aa39a804599325e0d641211531dfd201725b8dfca2442b6c`
- Payload hash: `dda7655cae660522f543ea6ca5e4be625df4e2c9d90ed1ed58d9f29c1bdc8c91`
- Transcript hash: `cc800919aeef50a287518177ffbae80f539f039356637593a5d9d2be241c5715`
- Lean module warnings: `0`
- New credit delta: `0`

## Exact Local Control

The local block is `A = -X + (3/4)Z`. Lean and an independent rational
calculation agree that `[1,2]` and `[2,-1]` are exact eigenvectors with
eigenvalues `-5/4` and `+5/4`. The commutator `[X,A]` is nonzero, and the
nonzero diagonal entries prove that `A` is not any scalar multiple of `X`.

## Independent Product Replay

| n | dimension | gap | width | normalized gap | spectrum error | site blocks commute | checked |
|---:|---:|---:|---:|---:|---:|:---:|:---:|
| 4 | 16 | 5/2 | 10 | 1/4 | 3.553e-15 | True | True |
| 5 | 32 | 5/2 | 25/2 | 1/5 | 4.441e-15 | True | True |
| 6 | 64 | 5/2 | 15 | 1/6 | 8.882e-15 | True | True |
| 7 | 128 | 5/2 | 35/2 | 1/7 | 1.776e-14 | True | True |

The finite oracle builds exact rational bit-action matrices. NumPy is used
only to compare the complete ordered Hermitian eigenspectrum. Although the
global `X` and `Z` sums do not commute, regrouping them as one tilted block
per site exposes a pairwise-commuting tensor-product structure.

## Supported

- Lean checks the exact local eigenpairs, local spectrum, Hermiticity, noncommutation with X, and non-scalar-X boundary.
- Independent n=4,5,6,7 product spectra match (5/4)(2k-n) with binomial multiplicities.
- The raw gap is 5/2, width is 5n/2, and normalized gap remains 1/n.
- The X and Z pieces do not commute, but regrouping by disjoint sites exposes pairwise-commuting local blocks.
- Exact cluster-phase conjugation produces the cluster-stabilizer Hamiltonian plus the same longitudinal Z field.

## Not Supported

- The all-n product spectrum is independently replayed at finite sizes but is not yet formalized as a Lean tensor-product theorem.
- This is a negative control showing that noncommutation alone does not imply hardness; overlapping noncommuting terms remain untested.
- No spectral-hardness theorem, hardware execution, Quantum PCP theorem, NLTS theorem, BQP separation, solved frontier, or new credit is supported.

## Next Gate

Formalize the all-`n` tensor-product spectrum in Lean, then introduce the
smallest overlapping noncommuting term that destroys the disjoint-site block
decomposition. Any next claim must retain explicit locality, spectrum,
denominator, and no-credit boundaries.
