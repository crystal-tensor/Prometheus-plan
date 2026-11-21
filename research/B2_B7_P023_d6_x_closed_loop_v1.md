# Closed-loop X RTL: resolving the first degenerate-correction counterexample

Date: 2026-11-21  
Scope: #021/B7, #022/B2, #023 only

## Question

When a syndrome admits multiple valid corrections, can a streaming RTL decoder remain correct without reproducing one canonical per-window matching?

## Why the test changed

The rejected 127-shot open-loop trial found 21 windows whose RTL correction differed from the frozen software correction even though the syndrome and logical observable were correct. All 41 delta detector bits were committed in the following window. Therefore the next defect set had to be derived from the RTL correction actually returned, not replayed from a different software trajectory.

The correctness threshold did not become weaker. The new closed-loop gate requires the actual trajectory to maintain:

- a syndrome-valid matching at every window;
- zero residual on every committed detector set;
- zero final detector residual;
- the accepted final logical frame.

## Closed-loop route

The v9 host keeps one persistent Verilator 5.040 DistributedDual instance and one persistent frozen PyMatching selector service. For each window it:

1. loads raw arrivals from the hash-bound X corpus;
2. XORs them with the correction state returned by previous RTL windows;
3. derives selectors for that actual syndrome using the original frozen first-pass algorithm;
4. runs the phase-aware Rust-primal plus RTL-dual path;
5. writes the returned detector and observable corrections into persistent state;
6. checks the current commit residual before advancing.

The selector service is part of the correctness host, not a hardware-latency claim. Its exact source hash is bound in capture metadata.

## Calibration and counterexample shots

Two complete shots were frozen before execution:

- shot 0, the existing cross-backend calibration shot;
- shot 15, which contains the first noncanonical correction at window 59.

Formal result:

- complete windows: 328/328;
- syndrome-valid windows: 328/328;
- occupancy checks clear: 3,254/3,254;
- commit residual failures: 0;
- final residual failures: 0;
- final logical-frame failures: 0;
- maximum iterations: 18;
- total iterations: 1,906;
- forbidden errors: 0;
- unexpected warnings: 0.

Shot 0 reproduces the earlier Verilator result edge-for-edge, correction-for-correction, and iteration-for-iteration.

## What happens at shot 15

At window 59, RTL selects a syndrome-valid correction that differs from the software trajectory on two overlapping detector bits. The open-loop replay would feed window 60 a 14-defect syndrome with 7 selectors. The closed-loop route instead derives the syndrome from the actual correction and feeds window 60:

- 12 defects;
- 6 selectors;
- a different complete correction;
- zero commit residual.

After window 60 the trajectories reconverge. Shot 15 finishes all 164 windows with zero final residual and final logical frame `1`, matching the accepted reference.

This is evidence that canonical per-window correction equality is not the correct semantic contract for a streaming decoder. State-feedback residuals and the final logical frame are stricter about sequential correctness while permitting legitimate matching degeneracy.

## Updated denominator

Shot 15 is newly accepted. The tested X denominator is now:

- 10 distinct shots: 0–8 and 15;
- 1,640/167,936 cases;
- 1,014 shots and 166,296 cases remaining.

The rejected 127-shot open-loop block is still not counted.

## Claim boundary

This closes the first matching-degeneracy counterexample and validates a two-shot closed-loop host. It does not establish full X, any Z result, AXI integration, FPGA timing/resources, measured hardware latency, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, or B7 resource credit.

Machine evidence ID: `06a37cc1d9345554cec548351dbc09aa99f347651d27d8fe78c30ffda0dcefbb` (24/24 checks).
