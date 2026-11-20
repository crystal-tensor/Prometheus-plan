# B2/B7/#023 explicit 9-bit correlation reweight v1

## Question

Can the complete correlated online decoder, including every second-pass implied weight, be represented explicitly by one unsigned 9-bit even-integer grid without changing any fresh X/Z logical answer?

## Fresh semantic veto

| basis | candidate = online reference | online reference = full block | window outputs equal | base even range | implied even range | replacements p99 | payload p99 (bits) |
|---|---:|---:|---:|---:|---:|---:|---:|
| X | 1024/1024 | 1024/1024 | 167912/167936 | 144-264 | 0-164 | 103 | 2163 |
| Z | 1024/1024 | 1024/1024 | 167902/167936 | 142-264 | 0-164 | 103 | 2163 |

## Correction to the prior admission result

The prior result remains valid as an 8-bit detector-error input-probability experiment, but it did not constrain PyMatching's merged base edges or internally derived implied weights to 8 bits. PyMatching rescaled those non-integral weights into its wide internal integer domain. Its 12+8-bit controller payload was therefore diagnostic, not a realized candidate encoding, and is superseded here by an explicit 12+9-bit replacement payload.

## Decision

Classification: `nine_bit_explicit_reweight_semantic_pass_hardware_write_path_absent`.

The admitted object is an explicit integer software graph plus rewrite table. The pinned Micro Blossom source still reserves an opcode while leaving the dynamic edge-weight write path unimplemented; no generated RTL, cycle, FPGA, timing, LUT/BRAM, full B2, #023, or B7 credit follows.

## Verification

Formal checks: `16/16`. Evidence ID: `002e8453ae7beff8f89f7e5740c0ab9b6b04d8052248ee015be3e30c9f01951e`.

## Next gate

Implement the missing Micro Blossom dynamic-weight register/write path, generate the six bound graph/rule images, and measure exact correction equality plus p99 cycles before hardware credit.
