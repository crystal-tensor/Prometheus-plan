# B9 R197 Nonstandard Fermionization Stress

## Verdict

- Status: `checked_nonstandard_fermionization_boundary`
- Requirements: `11/11`
- Protocol hash: `19605d12028bc0205512904edb0ceac2f9cc50d548b1a5d80c15499b2343ee6d`
- Payload hash: `ae331194b20b5308be38dd4a6967783a209f194963dc7cf291f1c876cf9dbe06`
- Public preregistration commit: `ab944728d8bbc590b745b9a4682ca31b4f9ee83f`
- Scientific promotion accepted: `false`
- New credit delta: `0`

## Heuristic Question

Can the apparent R196 nonintegrable candidate become a free fermion after changing the Jordan-Wigner parity axis?

## Frozen Frame Sweep

- Single-frame exact-nullity-two rows: `30/30`.
- Five-frame union exact-nullity-two rows: `6/6`.
- Frames: standard `X`, `Y`, `Z`; tilted field-aligned `A=(-4X+3Z)/5`; and orthogonal tilted `B=(3X+4Z)/5`.
- Each family contains all Majorana-linear operators, all quadratic Hermitian bilinears, full parity, identity, and H.

## Positive Control

- At `J=0,n=8`, tilted-A and all-frame union nullities are `[{'1000003': 66, '1000033': 66}, {'1000003': 91, '1000033': 91}]`.

## Supported

- r197_contract_publicly_frozen_before_acceptance_execution
- r197_holdout_couplings_unseen_before_protocol_freeze
- declared_single_frame_quadratic_majorana_plus_h_families_have_nullity_two
- declared_five_frame_union_plus_h_family_has_nullity_two
- zero_coupling_tilted_frame_controls_recover_extra_exact_charges
- r196_candidate_survives_declared_r197_finite_fermionization_adversary

## Not Supported

- all_frame_fermionization_exclusion
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
- hardware_relevance
- solved_frontier

## Next Gate

Audit every row with an independent symplectic-bit implementation and a third prime. Then attack continuous frames, higher-than-quadratic Majorana charges, explicit Kramers-Wannier dualities, or range-nine adaptive tails.
