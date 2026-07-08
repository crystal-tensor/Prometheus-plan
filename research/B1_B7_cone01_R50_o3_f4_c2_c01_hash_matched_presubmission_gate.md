# B1/B7 Cone01 R50 O3-F4 C2 C01 Hash-Matched Pre-Submission Gate

- Target: `T-B1-004ez/T-B7-014i`
- Upstream target: `T-B1-004ey/T-B7-014h`
- Method: `b1_b7_cone01_r50_o3_f4_c2_c01_hash_matched_presubmission_gate_v0`
- Status: `cone01_r50_o3_f4_c2_c01_hash_matched_presubmission_rejected_on_source_backed_flags`
- Selected challenge: `O3-F4-C01`
- Presubmission row hash: `3f7be50125146f8d4c68fd83f3d7526a25960e89b9584416e8fa6b5f2068059f`
- Evaluation hash: `da44c636972d9d407d1ed066e207813c405358c75cb97e8dcdf5f1db8ed7a50f`

## Result

R50 passes 8/8 requirements by closing the C01 file/hash surface while keeping the row rejected on source-backed flags.

## Rejection Surface

- R49 baseline file-hash failures: `8`
- R50 file-hash failures: `0`
- Empty production keys: `2`
- Flag failures: `3`
- Accepted source-backed rows: `0`
- Source-backed replay: `False`
- Same-unitary certificate: `False`
- Smoke-only blocker: `True`

## Requirement Results

- `S1` PASS: R49 baseline is clean and still rejects the placeholder template
- `S2` PASS: R50 emits a row with every R48/R49 required key present
- `S3` PASS: R50 closes the file/hash surface for C01
- `S4` PASS: R50 narrows R49 rejection from missing files to source-backed flags
- `S5` PASS: R50 remains rejected and does not accept a source-backed row
- `S6` PASS: R50 preserves witness schema and zero-credit boundary tokens
- `S7` PASS: R50 signature artifact is explicitly a blocker note, not a certificate
- `S8` PASS: R50 claims no C2, O3, reroute, B7, STV, C3-C7, or resource progress

## Claim Boundary

- Supported: R50 binds the existing C01 evidence files into a hash-matched pre-submission row and proves the file/hash layer can be closed without accepting C2.
- Not supported: R50 does not provide source-backed replay, a real same-unitary certificate, a verifier signature, C2 acceptance, O3 closure, reroute permission, or B7/STV credit.
- Next gate: Replace the smoke witness, dry-run verifier, and signature blocker with source-backed replay evidence and a real same-unitary verifier; then rerun R49 and R47.

- validation_error_count: `0`
