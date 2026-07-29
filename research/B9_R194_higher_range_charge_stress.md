# B9 R194 Higher-Range Conserved-Charge Stress

## Verdict

- Status: `checked_higher_range_local_charge_boundary`
- Requirements: `14/14`
- Protocol hash: `9e2ad9df2022b6b34eada972666c0b6403aaef9ff217c8ba73cbc5c3130e6f4a`
- Payload hash: `6349353aa3ff0f9abd2ab6967f9c5fb75a6237cc85c85c17f256e2039c62eb35`
- Scientific promotion accepted: `false`
- New credit delta: `0`

## Preregistration Boundary

`J=13/32` was observed only while measuring sparse-elimination cost.
It is disclosed as an engineering probe and contributes zero
scientific acceptance decisions. R194 acceptance uses only the newly
frozen `23/64`, `27/64`, `31/64`, and `35/64` couplings.

## Complete Position-Dependent Range Five

- Exact-nullity-two rows: `12/12`.
- Sizes: `8, 9, 10`; every position-dependent Pauli word with minimal contiguous support span at most five is included.

## Complete Position-Dependent Range Six Challenge

- Coupling and size: `J=31/64`, `n=8`.
- Candidate columns: `10240`.
- Output rows: `15871`.
- Exact modular nullities: `{'1000003': 2, '1000033': 2}`.
- Identity/H kernels and two-prime rank certify exact nullity two inside this complete finite-size range-six ansatz.

## Six-Shell Translation-Summed Proxy

- Exact-nullity-two rows: `12/12`.
- The basis contains identity plus the open-chain translation sum of every Pauli density through range six.
- This is a finite six-shell truncation only. A quasi-local charge with a nonzero tail beyond range six can evade it.

## Positive Controls

- `J=0` complete range-five nullity: `798`.
- `J=0` translation-summed range-six nullity: `673`.
- Both controls expose more than identity and H, so the adversaries detect known extra conserved structure.

## Supported

- engineering_probe_excluded_from_acceptance
- frozen_holdout_couplings_recorded_before_execution
- complete_range_five_nullity_two_on_frozen_holdouts
- complete_range_six_challenge_nullity_two
- translation_summed_range_six_nullity_two_on_frozen_holdouts
- zero_coupling_controls_detect_extra_conserved_charges
- r193_candidate_survives_declared_higher_range_adversaries

## Not Supported

- all_coupling_theorem
- all_size_theorem
- complete_quasi_local_charge_exclusion
- site_dependent_nonlocal_duality_exclusion
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

Extend the complete position-dependent range-six certificate
beyond one size/coupling, then test range-seven/eight tails,
site-dependent or nonlocal dualities, nonstandard
fermionizations, and larger sparse spectra. R194 narrows the
integrability escape surface; it does not prove nonintegrability,
quantum chaos, spectral hardness, Quantum PCP, NLTS, or BQP.
