# B1/B7 Cone01 R2 Line-1378 Overlap Recovery Packet Gate

- Target: `T-B1-004dd/T-B7-012m`
- Method: `b1_b7_cone01_r2_line1378_overlap_recovery_packet_gate_v0`
- Status: `cone01_r2_line1378_overlap_recovery_packet_open_missing_artifact`
- R2 packet: `B1-B7-cone01-R2-line1378-overlap-recovery`
- R2 packet hash: `12192c2786939bfb78a8ec88f1233d7693bf89e8afe52bca91cc3fec88d05a0f`
- Triage hash: `475137115d142f24ae7d2e747ce5d6f8e9a6020eb8cb42deb5cee005bd734e0b`
- Acceptance packet hash: `e456ff08d70cb89cdb0b8093dd1527ce50ba3e5891e517688465939c2db75420`

## Result

The R2 line-1378 overlap recovery gate passes 6/9 requirements and intentionally fails ['P6', 'P7', 'P8'] because no source-backed R2 recovery artifact has been submitted.

## Locked R2 Packet

- Submission path: `results/B1_B7_cone01_r2_line1378_overlap_recovery_submissions/B1-B7-cone01-R2-line1378-overlap-recovery.json`
- Required keys: `18`
- Production required keys: `9`
- Evidence file classes: `9`

Required evidence files:

- line1378_overlap_recovery_manifest
- merged_line1378_line1381_region_rewrite_artifact
- merged_region_replay_or_symbolic_equivalence_certificate
- overlap_additivity_source_bound
- no_double_counting_ledger
- resource_delta_ledger
- qiskit_loader_seeded_replay_reference
- acceptance_packet_link_note
- claim_boundary_note

Acceptance predicates:

- packet_id equals B1-B7-cone01-R2-line1378-overlap-recovery
- triage_hash and acceptance_packet_hash match the locked source gates
- line1378 and line1381 windows are bound exactly to the overlap-additivity source facts
- a merged line1378/line1381 region rewrite artifact exists
- merged-region replay or symbolic equivalence is supplied
- line1378_delta_recovered is true with recovered_cnot_delta equal to 3
- no_double_counting_ledger_hash proves the line1378 delta is not counted on top of a contained line1381 window
- claim_boundary forbids resource-saving and B7-credit claims before the resource-escape acceptance packet accepts the route

## Evidence Boundary

- Selected lines before recovery: `[268, 1381]`
- Dropped overlap line before recovery: `[1378]`
- line1378 window / line1381 window / union window: `[1369, 1377]` / `[1369, 1379]` / `[1369, 1379]`
- line1378 candidate CNOT delta: `3`
- line1378 delta recovered before / after this gate: `False` / `False`
- Submitted R2 artifact exists: `False`
- Accepted exit routes / occurrence removal / proxy-T reduction: `0` / `0` / `0`
- B7 credit delta / STV credit: `0` / `0`

## Requirement Results

- `P1` PASS: Post-boundary triage is current and exposes R2 as ready
- `P2` PASS: Resource-escape acceptance packet remains open on missing submitted evidence
- `P3` PASS: Overlap-additivity source proves line1378 is dropped and unrecovered
- `P4` PASS: Seeded resource boundary still lists line1378 recovery as a failed blocker
- `P5` PASS: R2 packet schema and evidence classes are locked
- `P6` FAIL: R2 line-1378 recovery artifact has been submitted
- `P7` FAIL: Submitted R2 artifact satisfies the locked schema
- `P8` FAIL: Submitted R2 artifact is source-backed, overlap-bound, recovery-valid, and claim-boundary-bound
- `P9` PASS: Forbidden B1/B7 resource and ledger claims remain false

## Claim Boundary

- Supported: R2 now has a source-bound packet schema for recovering the dropped line-1378 overlap delta without double-counting the contained line-1381 window.
- Not supported: No R2 artifact, merged-region rewrite, line-1378 recovery, accepted exit route, occurrence removal, proxy-T reduction, B7 ledger credit, or resource saving is supported.
- Next gate: Submit B1-B7-cone01-R2-line1378-overlap-recovery with a source-backed merged line1378/line1381 region rewrite, replay or symbolic equivalence, no-double-counting ledger, resource-delta ledger, and claim boundary.

This packet gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, or a solved B1/B7 problem.

## Validation

- validation_error_count: `0`
