# B2/B7/#023 8-bit Micro Blossom admission v1

## Question

Can an 8-bit fixed-point, correlation-preserving window graph pass a fresh exact-semantic holdout and expose a bounded controller update payload before any Micro Blossom latency or resource credit is claimed?

## Fresh semantic veto

| basis | candidate = online reference | online reference = full block | window corrections equal | q range | affected edges p99 | update payload p99 (bits) |
|---|---:|---:|---:|---:|---:|---:|
| X | 1024/1024 | 1024/1024 | 167836/167936 | 86-154 | 102 | 2040 |
| Z | 1024/1024 | 1024/1024 | 167844/167936 | 82-154 | 103 | 2060 |

## Decision

Classification: `eight_bit_semantic_admission_pass_hardware_execution_unmeasured`.

Semantic veto: `True`. Eight-bit graph admission: `True`. Hardware deadline: `false`.

The admitted object is an integer graph and control-payload contract, not generated RTL, cycle-accurate execution, FPGA timing, LUT/BRAM evidence, or a hardware decoder. Full B2, scalable #023, and B7 credit remain closed.

## Verification

Formal checks: `17/17`. Evidence ID: `a9b7b679114d47ed4996020bd1bfc719229608fafb05800895537dbfb2709f49`.

## Next gate

Generate the six admitted static graph images, implement on-chip parallel correlation reweighting, and measure exact correction equality plus p99 cycles before any hardware or downstream credit.
