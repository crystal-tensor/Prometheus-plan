# B1/B7 Cone01 R3 Occurrence-Certificate Batch Gate

- Target: `T-B1-004de/T-B7-012n`
- Method: `b1_b7_cone01_r3_occurrence_certificate_batch_gate_v0`
- Status: `cone01_r3_occurrence_certificate_batch_open_missing_artifact`
- R3 packet: `B1-B7-cone01-R3-thirty-occurrence-certificates`
- R3 packet hash: `c71e65798d03679ae367bf70efce8730a704b08aa6f28dd5cdc10d940cbfb268`
- Triage hash: `475137115d142f24ae7d2e747ce5d6f8e9a6020eb8cb42deb5cee005bd734e0b`
- Acceptance packet hash: `e456ff08d70cb89cdb0b8093dd1527ce50ba3e5891e517688465939c2db75420`
- Resource threshold hash: `22fbb35211b0a145a6c0c59086ebea04118aabcd341dcd77a6044c26a298fdc4`

## Result

The R3 occurrence-certificate batch gate passes 6/9 requirements and intentionally fails ['P6', 'P7', 'P8'] because no source-backed 30-certificate artifact has been submitted.

## Locked R3 Packet

- Submission path: `results/B1_B7_cone01_r3_occurrence_certificate_batch_submissions/B1-B7-cone01-R3-thirty-occurrence-certificates.json`
- Required keys: `19`
- Production required keys: `12`
- Evidence file classes: `10`
- Required occurrence removal: `30`
- Required proxy-T reduction: `600`

Required evidence files:

- certificate_batch_manifest
- thirty_occurrence_certificate_files
- certificate_replay_bundle
- full_circuit_or_local_equivalence_replay
- resource_delta_ledger
- b7_ledger_replay
- no_double_counting_ledger
- source_lineage_map
- failure_mode_coverage_note
- claim_boundary_note

Acceptance predicates:

- packet_id equals B1-B7-cone01-R3-thirty-occurrence-certificates
- triage_hash, acceptance_packet_hash, and resource_threshold_hash match the locked source gates
- certificate_count is exactly 30 or greater and every certificate has a stable hash
- accepted_occurrence_removal is at least 30
- proxy_t_reduction is at least 600 under the B7 occurrence ledger
- certificate replay bundle and full-circuit or local-equivalence replay are supplied
- resource_delta_ledger_hash, b7_ledger_replay_hash, and no_double_counting_ledger_hash are present
- claim_boundary forbids resource-saving and B7-credit claims before the resource-escape acceptance packet accepts the route

## Evidence Boundary

- Submitted R3 artifact exists: `False`
- Accepted exit routes / occurrence removal / proxy-T reduction: `0` / `0` / `0`
- B7 credit delta / STV credit: `0` / `0`

## Requirement Results

- `P1` PASS: Post-boundary triage is current and exposes R3 as ready
- `P2` PASS: Resource-escape acceptance packet remains open on missing submitted evidence
- `P3` PASS: Seeded resource boundary still requires 30 occurrence removals and 600 proxy-T
- `P4` PASS: R3 threshold hash is locked to 30 removals and 600 proxy-T
- `P5` PASS: R3 packet schema and evidence classes are locked
- `P6` FAIL: R3 occurrence-certificate batch artifact has been submitted
- `P7` FAIL: Submitted R3 artifact satisfies the locked schema
- `P8` FAIL: Submitted R3 artifact is source-backed, threshold-valid, replay-bound, ledger-bound, and claim-boundary-bound
- `P9` PASS: Forbidden B1/B7 resource and ledger claims remain false

## Claim Boundary

- Supported: R3 now has a source-bound packet schema for a 30-certificate occurrence-removal batch with a 600 proxy-T B7 ledger threshold.
- Not supported: No R3 artifact, occurrence-removing certificate batch, accepted exit route, proxy-T reduction, B7 ledger credit, or resource saving is supported.
- Next gate: Submit B1-B7-cone01-R3-thirty-occurrence-certificates with 30 stable certificate hashes, replay evidence, B7 ledger replay, no-double-counting ledger, resource ledger, and claim boundary.

This packet gate does not claim resource saving, occurrence removal, proxy-T reduction, B7 ledger improvement, FT resource credit, or a solved B1/B7 problem.

## Validation

- validation_error_count: `0`
