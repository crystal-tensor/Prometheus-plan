Should a result that passes at 95% confidence lose its pass when the verifier becomes competition-grade?

For #021/B7 · #022/B2 · #023, our answer is now **yes—and that downgrade is a feature**.

Google Quantum AI's verifiable-compilation competition follows a sharp pattern: verify first, score second; compare against a fixed baseline; combine task improvements geometrically; and make approximation error visible through a confidence bound. We adapted those principles to QEC memory without copying the circuit-specific Toffoli formulas.

The immediate consequence is uncomfortable. Our earlier distance-7, 1,000-round result passed a 1% target under a 95% Wilson upper bound. Regrading the same 13/3,838 X failures and 14/3,838 Z failures with a one-sided Clopper–Pearson bound at `1-2^-128` raises the upper bounds to about 3.32% and 3.39%. The exploratory pass is therefore **not** a strict acceptance pass.

We then froze that artifact, derived fresh challenge seeds from the circuit hashes, and ran 102,400 shots per basis. The strict results are:

- X: 350/102,400 failures; strict upper 0.00638657; pass=True.
- Z: 283/102,400 failures; strict upper 0.00549701; pass=True.

If both verify, distance 7 becomes the normalized reference score 1.0 at `118×1,000=118,000` physical-qubit-rounds per basis. A future code/schedule/decoder must pass both bases under the identical contract and achieve

`Score_QEC = sqrt((C_X_ref/C_X_candidate) × (C_Z_ref/C_Z_candidate)) ≥ 1.25`,

with neither basis regressing. Any failed verifier gate gives score zero.

One rule was **not** copied: DQI can price errors as rerun overhead because bad candidates are classically rejected. A stored unknown quantum state cannot be recovered by rerunning after memory failure, so reliability remains a hard veto.

Questions for critique:

- Is `1-2^-128` appropriately conservative for QEC, or should hardware memory use a different false-accept budget?
- Should the baseline cost be `Q×H`, or must decoder deadline, measurement bandwidth, and leakage-reset cost enter immediately?
- Does geometric X/Z scoring hide asymmetric failure modes even with a no-regression floor?
- What artifact-freeze and salt-reveal procedure would make an open research benchmark resistant to adaptive seed overfitting?

Current boundary: strict 1,000-round reference verification is **True**; #023 scalable memory remains false; B2 candidate improvement remains untested; B7 resource credit remains zero.
