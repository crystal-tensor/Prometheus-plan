# B9 R187 Nonzero-Scale Derived Certificate

Last updated: 2026-07-27

Status: **checked_derived_algebraic_certificate_complete_all_n_hamiltonian_open**

## Question

Can the B9 uniform-reweight rejection survive after removing the
conclusion-shaped `hRatio` assumption?

## Result

- Requirements: `10/10`
- `hRatio` assumption removed: `True`
- Restricted checked algebraic theorem: `True`
- Module warnings: `0`
- Protocol hash: `02eb72cbfd33da8a35bb9424114dfcaed54aca507255207282974d8e837e2cc8`
- Module hash: `2c759095ccd90d65d3ab19e6d5ee12abb9062b0104baabeacb3aff7bd653b6e3`
- Transcript hash: `e00f06e295fa0c4e41955e78263de54656ed06fc4ae8e9e83a4700735c85bcac`
- Payload hash: `af9bc4a9aeee7bb17d0c01e79e0a264730ef47b0dcd3ae34f0fe78601855bd7e`

Lean now derives normalized-gap invariance and spectral-width-ratio invariance
from the nonzero `27/20` scale. It separately derives raw-gap amplification from
`27/20 > 1` and a positive source gap. The final checked theorem combines these
facts with locality preservation and rejects improvement of the computed
normalized gap.

## Claim Boundary

This closes one algebraic hypothesis-injection gap. It does not formalize the
open-boundary cluster-stabilizer Hamiltonian for every `n >= 4`, connect the
finite JSON rows to a generated formal object, prove Quantum PCP or NLTS,
establish a global gap-amplification no-go theorem, separate BQP, or solve B9.
`new_credit_delta` remains `0`.

## Next Gate

Define the open-boundary Hamiltonian family and support sets in Lean, prove the
all-`n` locality and uniform-reweight identities, and instantiate this checked
algebraic certificate from that construction rather than from abstract
`SpectralSummary` inputs.
