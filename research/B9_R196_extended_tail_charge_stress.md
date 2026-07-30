# B9 R196 Extended Tail Conserved-Charge Stress

## Verdict

- Status: `checked_extended_tail_charge_boundary`
- Requirements: `15/15`
- Contract hash: `afc5a721320ccf2a73291b961e6c3c28e5029ebe9e783ef54ccda2d48223e668`
- Protocol hash: `8f20eb86bd4e68950a699a0ebcd8bfaa0e4a4b9607b3a10731a123ce3ed54f8f`
- Payload hash: `0116a213e9d49bf5bc57b1e43069644f79b15932c8608bc56075bacbfc10ff0c`
- Scientific promotion accepted: `false`
- New credit delta: `0`

## Public Pre-Execution Boundary

- The v0.1.0 positive-control wording error was publicly corrected before any frozen-holdout acceptance row executed.
- Frozen holdouts remain `J=73/128` and `J=77/128`; the engineering-only `J=13/32` probe contributes zero decisions.

## Complete Position-Dependent Range Six At n=10

- Exact-nullity-two rows: `2/2`.
- Candidate columns per row: `16384`; output basis size: `27647`.

## Translation-Summed Range Eight

- Frozen row: `J=73/128`, `n=10`.
- Candidate columns: `49153`; complete parent basis: `163840`; output basis: `253951`.
- Exact modular nullities: `{'1000003': 2, '1000033': 2}`.
- This is one finite eight-shell certificate, not a range-nine or complete quasi-local exclusion.

## Independent Boundary Corrections Through Range Four

- Exact-nullity-two rows: `4/4`.
- Candidate columns per row: `3457`.
- Both holdouts are tested at `n=9,10`; size-dependent, interacting, and nonlocal boundary structures remain open.

## Positive Controls

- At `J=0`, every family contains three explicit linearly independent exact kernels.
- The translation-summed extra witness is the adjacent tilted-field product sum; complete and boundary families use a position-resolved tilted field.

## Supported

- r196_contract_publicly_frozen_before_acceptance_execution
- r196_holdout_couplings_unseen_before_protocol_freeze
- complete_range_six_n10_nullity_two_on_two_holdout_rows
- translation_summed_range_eight_nullity_two_on_one_holdout_row
- range_six_boundary_range_four_nullity_two_on_four_holdout_rows
- explicit_zero_coupling_witnesses_detect_extra_conserved_charges
- r195_candidate_survives_declared_r196_finite_ansatz_adversaries

## Not Supported

- all_coupling_theorem
- all_size_theorem
- range_nine_or_longer_tail_exclusion
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

Attack range-nine or adaptive quasi-local tails, explicitly
size-dependent/nonlocal boundary structures, nonlocal dualities,
nonstandard fermionizations, interacting-integrability
candidates, and larger sparse spectra. R196 narrows three finite
ansatz families; it does not prove nonintegrability, quantum
chaos, spectral hardness, Quantum PCP, NLTS, or BQP.
