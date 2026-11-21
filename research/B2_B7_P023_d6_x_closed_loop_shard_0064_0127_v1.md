# Closed-loop X RTL: 128-shot prefix closes all 21 known replay divergences

Date: 2026-11-21
Scope: #021/B7, #022/B2, #023 only

## Question

Can every correction mismatch that invalidated the 127-shot open-loop replay pass the stricter closed-loop sequential contract?

## Frozen shard

The third closed-loop extension freezes shots 64–127, adding 64 previously uncredited X shots and 10,496 consecutive windows. Combined with the earlier evidence, the accepted set is now the contiguous prefix 0–127.

The test does not require RTL to reproduce one canonical matching. It does require the actual RTL-owned trajectory to satisfy:

- a syndrome-valid matching at every window;
- zero residual on every committed detector set;
- zero final detector residual;
- the accepted final logical frame.

## Formal result

The pinned Verilator 5.040 capture passes:

- frozen shots: 64/64;
- complete windows: 10,496/10,496;
- syndrome-valid windows: 10,496/10,496;
- occupancy checks clear: 105,733/105,733;
- commit-residual failures: 0;
- final-residual failures: 0;
- final logical-frame failures: 0;
- maximum iterations: 26;
- total iterations: 61,746;
- forbidden runtime hits: 0;
- unexpected warnings: 0.

The capture exits zero after 575.08 seconds. That duration includes software and simulation overhead and is not hardware latency.

## The remaining fourteen counterexamples

The earlier open-loop falsifier identified fourteen noncanonical corrections inside shots 64–127:

| Shot | Noncanonical correction | Closed-loop response |
|---:|---:|---:|
| 73 | window 13 | window 14 |
| 74 | window 129 | window 130 |
| 75 | window 148 | window 149 |
| 99 | window 32 | window 33 |
| 102 | window 26 | window 27 |
| 106 | window 20 | window 21 |
| 108 | window 6 | window 7 |
| 111 | window 139 | window 140 |
| 115 | window 66 | window 67 |
| 116 | window 62 | window 63 |
| 118 | window 8 | window 9 |
| 119 | window 30 | window 31 |
| 121 | window 48 | window 49 |
| 127 | window 141 | window 142 |

Closed-loop execution differs from the frozen replay in exactly those fourteen response windows. Every response clears its commit residual, and every trajectory reconverges by the following window.

## Closing the open-loop falsifier set

The rejected open-loop run contained 21 complete-correction mismatches across shots 9–135. All 21 mismatch shots lie inside the now-accepted closed-loop prefix 0–127:

- first closed-loop pilot: 1 response;
- shots 25–63: 6 responses;
- shots 64–127: 14 responses;
- cumulative: 21/21.

This does not retroactively accept the open-loop run. It replaces the invalid sequential assumption with direct closed-loop evidence for every known counterexample.

## Updated denominator

The cumulative frozen X denominator is now:

- 128/1,024 distinct shots;
- 20,992/167,936 cases;
- exactly 12.5% of the X corpus;
- 896 shots and 146,944 cases remaining.

## Claim boundary

This closes the known open-loop mismatch set and establishes a passing 128-shot X prefix. It does not establish full X, any Z result, AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit.

Machine evidence ID: `773f72ac9b73a90f07ab46966a9eb7c3cbbe77f42873b0d2b6d9bb0281a6a50d` (32/32 checks).
