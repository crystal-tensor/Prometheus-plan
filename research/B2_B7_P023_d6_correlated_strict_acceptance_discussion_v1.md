Can a smarter decoder buy 26 qubits—and who should pay for its latency?

The 71-qubit correlated-decoder candidate survived both strict basis gates.

After public preregistration in Discussion #325, we revealed the freeze-bound salt and ran 102,400 fresh shots per basis at 1,000 rounds. X recorded 539/102400 failures with strict upper 0.008795; Z recorded 443/102400 with strict upper 0.007587.

The resource ratio is 97/71 = 1.3662×. Following a Kaggle-style correctness veto, the accepted physical-memory score is **1.3662** and the physical-memory gate is **True**.

Questions for critique:

- Is the 1% total-memory failure target meaningful enough for algorithmic workloads?
- Should decoder wall time be multiplied into the cost, constrained by a hard deadline, or reported as a separate Pareto axis?
- Is exploiting decomposed Y-error correlation a fair algorithmic gain when the circuit and physical noise are unchanged?
- Which mismatch, leakage, burst-noise, and decoder-deadline stress should precede any full B2 or #023 claim?
- If this route failed, what genuinely different ≤77-qubit route should be frozen next; if it passed, what is the strongest falsifier?

Current boundary: physical-memory gate=True; full B2=false; #023 scalable memory=false; B7 resource credit=0.
