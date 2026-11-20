# B2/B7/#023 explicit 16-bit correlation reweight v2

## Question

Can a preregistered unsigned 16-bit even-weight decoder, selected only after the public 9-bit regression, reproduce every fresh X/Z window syndrome, window output, final frame, and residual exactly?

## Fresh semantic veto

| basis | candidate = online reference | online reference = full block | window outputs equal | base even range | implied even range | replacements p99 | payload p99 (bits) |
|---|---:|---:|---:|---:|---:|---:|---:|
| X | 1024/1024 | 1024/1024 | 167936/167936 | 18348-33706 | 0-20966 | 102 | 2856 |
| Z | 1024/1024 | 1024/1024 | 167936/167936 | 18068-33706 | 0-20966 | 103 | 2884 |

## Correction to the prior admission result

The public v1 producer label is rejected because its semantic_pass omitted the frozen all-window syndrome/output equality clause. V1 remains valid evidence that 9-bit weights preserve all final frames and residuals, but its 12 syndrome and 24 output mismatches in X plus 17 syndrome and 34 output mismatches in Z fail strict streaming substitutability.

## Decision

Classification: `sixteen_bit_explicit_reweight_semantic_pass_hardware_write_path_absent`.

The semantic veto admits an explicit integer software graph plus rewrite table. The pinned Micro Blossom source still reserves an opcode while leaving the dynamic edge-weight write path unimplemented; no generated RTL, cycle, FPGA, timing, LUT/BRAM, full B2, #023, or B7 credit follows.

## Verification

Formal checks: `16/16`. Evidence ID: `0f5c788a433bab8ba41b84b29e8b8964bbc75d7a1a0a14dddf64bd998ad73107`.

## Next gate

Implement the missing Micro Blossom dynamic-weight register/write path, generate the six bound graph/rule images, and measure exact correction equality plus p99 cycles before hardware credit.
