# B9 R190 Complete Spectrum Formula Certificate

## Verdict

- Status: `checked_all_n_spectrum_formula_multiplicity_gap_width_complete_restricted_negative_boundary`
- Requirements: `14/14`
- Protocol hash: `ed258a84d49073f113a4d9e771c983ea6e99b22e94e3dc14e3182c6dca9d719a`
- Payload hash: `9611e00d228143627d2d146177b9c4dddcda7a72d7d8f106b5aace072db0f9db`
- Transcript hash: `9983640b9732ccb939a0a42f85df1f3fa75393fcfceaba7bb0cbe760b2eb720c`
- Lean module warnings: `0`
- New credit delta: `0`

## Formal Result

The pinned Lean 4.12.0 module constructs a complete Walsh eigenbasis for the
independent `-sum X_i` chain and an exact diagonal cluster-phase conjugation
to the open-chain cluster-stabilizer Hamiltonian. Every label of Hamming
weight `k` has energy `2k-n`; label/support equivalence proves multiplicity
`choose(n,k)`. Ground energy, first excitation, raw gap, top energy, width,
and normalized gap are therefore `-n`, `2-n`, `2`, `n`, `2n`, and `1/n`.

## Independent Replay

| n | dimension | gap | width | normalized gap | spectrum error | checked |
|---:|---:|---:|---:|---:|---:|---|
| 4 | 16 | 2 | 8 | 1/4 | 1.776e-15 | True |
| 5 | 32 | 2 | 10 | 1/5 | 2.220e-15 | True |
| 6 | 64 | 2 | 12 | 1/6 | 6.826e-15 | True |

The independent path builds integer bit-action matrices, exact Walsh Gram
matrices, exact cluster-phase conjugates, and all cluster eigenvectors without
using Lean output. NumPy is used only to compare the complete ordered finite
eigenspectrum.

## Supported

- Lean constructs an invertible all-n Walsh eigenbasis for the X chain.
- Lean proves exact cluster-phase conjugation from the X chain to the open-chain cluster Hamiltonian.
- Lean proves every eigenvalue is 2k-n and weight k has exactly choose(n,k) labels.
- Lean derives ground energy -n, first excited energy 2-n, gap 2, top energy n, width 2n, and normalized gap 1/n.
- Lean reconnects these operator-derived values to the R187 27/20 uniform-reweight rejection.
- Independent n=4,5,6 integer-matrix, Walsh, eigenvector, eigenspectrum, and multiplicity replays pass.

## Not Supported

- This solves one exactly diagonalizable commuting stabilizer family, not arbitrary local Hamiltonians.
- The 27/20 result rejects only global uniform rescaling as normalized-gap amplification; it is not a global no-go theorem.
- No quantum hardware execution, Quantum PCP theorem, NLTS theorem, BQP separation, solved frontier, or new credit is supported.

## Next Gate

Use the exact solvable family as a control, then seek a restricted
noncommuting perturbation whose normalized gap behavior cannot be reduced to
uniform scaling. Any next theorem must preserve explicit locality, state its
perturbation regime, and retain the same hardware/Quantum-PCP claim boundary.
