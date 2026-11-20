If transport vanished, would the decoder finally catch the clock?

The previous distance-6 experiment produced a useful contradiction: all `4096/4096` online-window predictions equal the frozen full-block decoder and every residual check passes, but correlated X/Z p99 latency reaches `9.035/9.375 µs` per committed layer against a `1 µs` line.

Before measuring anything new, this protocol freezes two executions of the same decoder:

- the current packed synchronous Unix-socket and feedback path;
- a direct no-pack/no-socket path with identical windows, matching objects, correction propagation, and logical frame.

The direct path is split into matching, edge mapping, correction propagation, syndrome materialization, and delivery/feedback phases. The first failing stage—not the most convenient story—sets the diagnosis. Exact predictions and zero residuals remain a hard veto before any speedup counts. Only afterward do we report the X/Z relative p99 speedups and their geometric mean, while keeping the absolute deadline unchanged.

Questions for critique:

- If the matching kernel alone misses the deadline, should the next move be a native decoder, parallel windows, or a different decoding algorithm?
- If matching passes but direct end-to-end fails, which Python bookkeeping step is most worth eliminating first?
- Is p99 plus a one-percent miss budget the right engineering contract, or should a logical-clock stall model replace it?
- What evidence would you require before promoting a host-local attribution result into a controller-design claim?

Hardware deadline, full B2, scalable #023 memory, and B7 credit remain false regardless of this diagnostic result.
