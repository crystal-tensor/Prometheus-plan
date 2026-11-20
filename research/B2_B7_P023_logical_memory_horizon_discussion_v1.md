If a logical qubit survives seven correction rounds, when—exactly—may we call it scalable memory?

The new #021/B7 · #022/B2 · #023 gate gives an intentionally uncomfortable answer: **not after seven rounds, and not by extrapolation alone**.

Our local B2 packet has 30 reproducible Stim/PyMatching configurations with 3,000 shots each, but each experiment spans only 3, 5, or 7 rounds. We now separate four claims that are often collapsed:

1. short-memory simulator calibration;
2. stationary-model lifetime projection;
3. directly observed logical-memory horizon; and
4. B7 architecture resource credit.

Only the third can activate #023, and only a same-condition low-overhead comparison plus the existing calibrated-evidence gate can carry it into B7.

The statistical floor is already sobering. With zero observed failures, a two-sided Wilson 95% upper bound needs 381 direct-horizon shots to clear a 1% total-failure target. At one million rounds, the smallest current distance-3 circuit therefore implies at least **19,812,000,000 physical-qubit-cycles across X and Z**—before decoder, reset, leakage, drift, or layout overhead.

Three primary-source denominators make the question concrete: Willow reports below-threshold memory and million-cycle operation while still finding correlated-error floors; a qLDPC protocol projects far lower multi-logical-qubit overhead under an explicit noise model; and an October 2026 IBM cloud-hardware preprint reports distance suppression whose advantage weakens in longer memories.

So what should be the minimum honest definition of “scalable quantum memory”?

- Must both X and Z survive the same horizon?
- Is 1,000 rounds enough for activation, or only a staging gate to one million?
- Should decoder throughput, calibration drift, and correlated bursts be hard vetoes?
- When may a model projection enter an architecture ledger, if ever?

Useful contributions are falsifiable: propose a tighter horizon, a defensible confidence rule, a source-backed public trace dataset, a same-condition surface-code/qLDPC denominator, or a reason the current gate is too weak or too strong.

Current decision: **short-memory calibration only; #023 readiness false; B2 claim credit false; B7 memory-derived resource credit zero.** Formal checks: 17/17.
