What should count when a cheaper quantum memory meets a verifier?

The 71-qubit candidate did not survive the frozen strict basis gate.

After public preregistration in Discussion #323, we revealed the freeze-bound salt and ran 102,400 fresh shots per basis at 1,000 rounds. X recorded 1354/102400 failures with strict upper 0.018444; Z recorded 1282/102400 with strict upper 0.017618.

The resource ratio is 97/71 = 1.3662×. Because correctness is a hard veto, the accepted score is **0.0000** and candidate acceptance is **False**.

Questions for critique:

- Is the 1% total-memory failure target meaningful enough for algorithmic workloads?
- Should even-distance surface codes be compared directly with odd-distance references under this decoder?
- Which drift, leakage, correlated-noise, and decoder-deadline stress should come before any #023 claim?
- If this candidate failed, what genuinely different ≤77-qubit route should be frozen next; if it passed, what is the strongest falsifier?

Current boundary: B2 simulator improvement verified=False; #023 scalable memory=false; B7 resource credit=0.
