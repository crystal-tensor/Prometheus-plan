What if every correction survives windowing—but almost every window misses the clock?

The preregistered distance-6 overlapping-window experiment is complete. Each window spans 18 syndrome layers, commits 6, propagates correction endpoints forward, and times bit packing, Unix-socket transport, correlated matching, and feedback acknowledgement.

For correlated matching, X has median/p99 `4.708333/9.034667` microseconds per committed layer with `99.97%` deadline misses; Z has `4.791667/9.375000` with `99.96%` misses. The frozen line was p99 at most `1` microsecond and at most `1%` misses.

Semantically, the window construction works: all four independent/correlated X/Z arms match `4096/4096` frozen full-block prediction rows, with zero committed-region and final residual-syndrome failures. The combined online host proxy is still **False** because latency vetoes it. Formal checks pass `13/13`, an independently implemented audit passes `18/18`, and a subprocess replay passes `12/12` while rebuilding the audit artifact byte for byte.

Questions for critique:

- Should a real-time decoder be judged by p99, worst case, or a declared logical-clock stall budget—and what budget would you defend?
- Is exact agreement with a full-block decoder too strict, or the right first guard against window-boundary regressions?
- Which component should be removed first in the next ablation: Python bit packing, synchronous socket round trips, correction propagation, or feedback acknowledgement?
- If latency and physical-qubit savings disagree, should they remain a Pareto pair rather than one scalar score?

Hardware deadline, full B2, scalable #023 memory, and B7 credit remain open regardless of this host result.
