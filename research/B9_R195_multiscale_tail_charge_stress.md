# B9 R195 Multiscale Tail Conserved-Charge Stress

## Verdict

- Status: `checked_multiscale_tail_charge_boundary`
- Requirements: `16/16`
- Protocol hash: `a03648ca52fba89b66f2ffaf065a69cfe8db22299a3aa82eb55f963721a05fb5`
- Payload hash: `8d40e36ee574326cf6650ab686a8430ee824d24fd929cd5a49d7c1cdb9b95f9e`
- Scientific promotion accepted: `false`
- New credit delta: `0`

## Frozen Holdout Boundary

- Couplings: `J=53/128` and `J=69/128`; neither appears in the R193 or R194 observed/acceptance grids.
- No coupling was removed or replaced after execution.

## Complete Position-Dependent Range Six

- Exact-nullity-two rows: `4/4`.
- Sizes: `n=8,9`; both frozen couplings are tested at both sizes.
- Candidate columns range from `10240` to `13312`.

## Translation-Summed Range Seven

- Exact-nullity-two rows: `4/4`.
- Sizes: `n=9,10`; every translation-summed density through range seven is included.
- Candidate columns per row: `12289`.
- This is a seven-shell truncation, not an exclusion of range-eight or longer quasi-local tails.

## Independent Boundary Dressing

- Exact-nullity-two rows: `4/4`.
- Each row adds independent left/right Pauli corrections through range three to every bulk translation sum through range six.
- Candidate columns per row: `3169`.
- Longer, size-dependent, interacting, or nonlocal boundary dressings remain untested.

## Positive Controls

- `J=0` nullities for complete range six, range-seven translation sum, and boundary-dressed range six: `{'complete_range_six': 2268, 'translation_range_seven': 2509, 'boundary_dressed_range_six': 701}`.
- All three exceed two, so each adversary detects known extra conserved structure.

## Supported

- r195_holdout_couplings_unseen_before_protocol_freeze
- complete_range_six_nullity_two_on_four_holdout_rows
- translation_summed_range_seven_nullity_two_on_four_holdout_rows
- range_six_boundary_dressing_nullity_two_on_four_holdout_rows
- zero_coupling_controls_detect_extra_conserved_charges
- r194_candidate_survives_declared_multiscale_tail_adversaries

## Not Supported

- all_coupling_theorem
- all_size_theorem
- range_eight_or_longer_tail_exclusion
- arbitrary_boundary_dressing_exclusion
- complete_quasi_local_charge_exclusion
- nonlocal_duality_exclusion
- nonstandard_fermionization_exclusion
- interacting_integrability_exclusion
- complete_integrability_exclusion
- nonintegrability_theorem
- quantum_chaos_theorem
- spectral_hardness_theorem
- quantum_pcp_theorem
- nlts_theorem
- bqp_separation
- solved_frontier

## Next Gate

Extend complete range six to `n=10`, then test range-eight
translation sums, longer and size-dependent boundary tails,
nonlocal dualities, nonstandard fermionizations, and
interacting-integrability candidates. R195 narrows three finite
ansatz families; it does not prove nonintegrability, quantum
chaos, spectral hardness, Quantum PCP, NLTS, or BQP.
