# B4/B8 Real-Backend Transcript Provenance Manifest Gate

Status: `real_backend_transcript_provenance_manifest_open_missing_artifact`

## Summary

- Method: `b4_b8_real_backend_transcript_provenance_manifest_gate_v0`
- Manifest: `B4B8-M6-real-backend-transcript-provenance-manifest`
- Provider packet: `B4B8-M6-provider-session-manifest`
- Transcript packet: `B4B8-M6-real-backend-transcript-rows`
- Manifest hash: `14b967e992826390fca8a33aec1662e3b8f40eee03922b879917f9a677f8815a`
- Requirements passed/failed: `6` / `3`
- Failed requirement IDs: `['P6', 'P7', 'P8']`
- Required key / production key / evidence file count: `14` / `9` / `10`
- Holdout row count: `160`
- No-leak / full-leak accepts per 160: `16` / `40`
- Real-backend transcript rows: `0`
- Provider manifest accepted: `False`
- Submitted manifest exists: `False`
- validation_error_count: `0`

## Provenance Manifest Packet

- Submission path: `results/B4_B8_real_backend_transcript_provenance_manifest_submissions/B4B8-M6-real-backend-transcript-provenance-manifest.json`
- Provider packet hash: `2a8779ab19f55f9dcf88ef6af26c5c3d33e9043f603060b5da07a49d93b25072`

Required evidence files:

- accepted_provider_session_manifest
- backend_properties_snapshot
- runnable_circuit_manifest
- hashed_backend_job_metadata
- raw_counts_artifact_manifest
- postprocess_script_manifest
- private_predicate_commitment_manifest
- shot_allocation_or_job_plan
- hashing_and_redaction_manifest
- claim_boundary_note

Acceptance predicates:

- manifest_id equals B4B8-M6-real-backend-transcript-provenance-manifest
- provider_packet_id equals B4B8-M6-provider-session-manifest
- transcript_packet_id equals B4B8-M6-real-backend-transcript-rows
- provider_manifest_hash matches the accepted provider/session manifest packet hash
- backend properties, runnable circuit, job metadata, raw counts, postprocess, shot allocation, private predicate commitment, and redaction hashes are present
- replay_hashes bind provider_packet_id, transcript_packet_id, and provider_packet_hash
- source evidence files are present and hash-bound
- claim_boundary forbids protocol soundness, quantum advantage, sampling hardness, cryptographic soundness, and BQP separation claims

## Requirement Results

- P1 [PASS]: Provider manifest gate remains valid and blocked only on P6/P7/P8
- P2 [PASS]: Transcript provenance manifest is bound to the provider and transcript packets
- P3 [PASS]: Manifest packet carries locked provenance schema and evidence file classes
- P4 [PASS]: Locked margin budgets and zero transcript rows are preserved
- P5 [PASS]: Current state has no accepted provider manifest, transcript row, or soundness credit
- P6 [FAIL]: Transcript provenance manifest artifact has been submitted
- P7 [FAIL]: Submitted manifest satisfies the locked transcript provenance schema
- P8 [FAIL]: Submitted manifest is source-backed, packet-bound, and replay-hash-bound
- P9 [PASS]: Forbidden soundness, advantage, and BQP claims remain false

## Claim Boundary

- Supported: The B4/B8 real-backend transcript route now has a provenance manifest packet that must bind accepted provider/session evidence, backend properties, runnable circuit, job metadata, raw counts, postprocess, shot allocation, private-predicate commitment, and redaction hashes.
- Not supported: No transcript provenance manifest, provider manifest, or real-backend transcript row has been submitted or accepted; no protocol soundness, quantum advantage, sampling hardness, cryptographic soundness, or BQP separation claim is supported.
- Next gate: Submit results/B4_B8_real_backend_transcript_provenance_manifest_submissions/B4B8-M6-real-backend-transcript-provenance-manifest.json, then the real-backend transcript rows, before rerunning the B4/B8 real-backend margin gate.
- protocol_soundness_proved: False
- cryptographic_soundness_proved: False
- sampling_hardness_proved: False
- quantum_advantage_claimed: False
- bqp_separation_claimed: False

## Validation

- validation_error_count: 0
