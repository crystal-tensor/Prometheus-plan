# B4/B8 Real-Backend Transcript Replay-Validation Manifest Gate

Status: `real_backend_transcript_replay_validation_manifest_open_missing_artifact`

## Summary

- Method: `b4_b8_real_backend_transcript_replay_validation_manifest_gate_v0`
- Manifest: `B4B8-M6-real-backend-transcript-replay-validation-manifest`
- Provenance manifest: `B4B8-M6-real-backend-transcript-provenance-manifest`
- Provider packet: `B4B8-M6-provider-session-manifest`
- Transcript packet: `B4B8-M6-real-backend-transcript-rows`
- Provenance manifest hash: `14b967e992826390fca8a33aec1662e3b8f40eee03922b879917f9a677f8815a`
- Manifest hash: `b1b0852d41796aef61c4d27ce1e4c469e50941f84e0fcba924fb012d6b8a00bd`
- Requirements passed/failed: `6` / `3`
- Failed requirement IDs: `['P6', 'P7', 'P8']`
- Required key / production key / evidence file count: `18` / `13` / `13`
- Holdout row count: `160`
- No-leak / full-leak accepts per 160: `16` / `40`
- Real-backend transcript rows: `0`
- Provider manifest accepted: `False`
- Submitted manifest exists: `False`
- validation_error_count: `0`

## Replay-Validation Manifest Packet

- Submission path: `results/B4_B8_real_backend_transcript_replay_validation_manifest_submissions/B4B8-M6-real-backend-transcript-replay-validation-manifest.json`
- Provider packet hash: `2a8779ab19f55f9dcf88ef6af26c5c3d33e9043f603060b5da07a49d93b25072`
- Provenance manifest hash: `14b967e992826390fca8a33aec1662e3b8f40eee03922b879917f9a677f8815a`

Required evidence files:

- accepted_transcript_provenance_manifest
- backend_properties_replay_manifest
- runnable_circuit_replay_manifest
- job_metadata_replay_manifest
- raw_counts_replay_manifest
- postprocess_replay_manifest
- shot_allocation_replay_ledger
- private_predicate_commitment_replay_note
- hashing_and_redaction_replay_manifest
- leakage_blind_margin_replay_table
- full_leak_margin_replay_table
- spoofer_attack_replay_table
- claim_boundary_note

Acceptance predicates:

- manifest_id equals B4B8-M6-real-backend-transcript-replay-validation-manifest
- provenance_manifest_id equals B4B8-M6-real-backend-transcript-provenance-manifest
- provider_packet_id and transcript_packet_id match the source gates
- provider_packet_hash and provenance_manifest_hash match the accepted source gates
- backend properties, runnable circuits, job metadata, raw counts, postprocess, shot allocation, private predicate commitment, and redaction replays are hash-bound
- leakage-blind margin, full-leak margin, and spoofer attack replay tables are hash-bound
- source evidence files are present and replay_hashes bind provenance, provider, and transcript identifiers
- claim_boundary forbids protocol soundness, quantum advantage, sampling hardness, cryptographic soundness, and BQP separation claims

## Requirement Results

- P1 [PASS]: Transcript provenance manifest gate remains valid and blocked only on P6/P7/P8
- P2 [PASS]: Replay manifest is bound to provider, provenance, and transcript packets
- P3 [PASS]: Replay manifest packet carries locked replay schema and evidence classes
- P4 [PASS]: Locked margin budgets and zero transcript rows are preserved
- P5 [PASS]: Current state has no accepted provider manifest, transcript row, or soundness credit
- P6 [FAIL]: Transcript replay-validation manifest artifact has been submitted
- P7 [FAIL]: Submitted replay manifest satisfies the locked transcript replay schema
- P8 [FAIL]: Submitted replay manifest is source-backed, manifest-bound, replay-bound, and claim-boundary-bound
- P9 [PASS]: Forbidden soundness, advantage, and BQP claims remain false

## Claim Boundary

- Supported: The B4/B8 real-backend transcript route now has a replay-validation manifest packet that must bind backend, circuit, job, counts, postprocess, shot, predicate, redaction, margin, and spoofer replay evidence before transcript rows count.
- Not supported: No replay-validation manifest, transcript provenance manifest, provider manifest, or real-backend transcript row has been submitted or accepted; no protocol soundness, quantum advantage, sampling hardness, cryptographic soundness, or BQP separation claim is supported.
- Next gate: Submit results/B4_B8_real_backend_transcript_replay_validation_manifest_submissions/B4B8-M6-real-backend-transcript-replay-validation-manifest.json, then real-backend transcript rows, before rerunning the B4/B8 real-backend margin gate.
- protocol_soundness_proved: False
- cryptographic_soundness_proved: False
- sampling_hardness_proved: False
- quantum_advantage_claimed: False
- bqp_separation_claimed: False

## Validation

- validation_error_count: 0
