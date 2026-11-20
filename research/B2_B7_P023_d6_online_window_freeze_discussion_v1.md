Can a decoder be real time if its tail misses the next syndrome?

The 71-qubit distance-6 memory candidate clears strict X/Z correctness and an offline batch-1 throughput proxy. But neither result answers the online question: what happens when only a finite syndrome window exists, old corrections must be committed, and their boundary effects must be handed to the future?

Before observing any new outcome, this protocol freezes sequential overlapping recovery at a `3d=18`-layer window and `d=6`-layer commit stride. The primary arm preserves PyMatching's two-pass correlations inside each window, propagates committed correction endpoints forward, and must exactly match all 1,024 frozen full-block predictions in both bases.

The timed response includes bit packing, a Unix-socket kernel path, decoding and commit propagation, plus reverse logical-frame acknowledgement. Passing requires p99 at or below 1 microsecond per committed layer, at most 1% deadline misses, exact prediction equality, and zero residual syndrome.

Questions before the clock starts:

- Is exact agreement with a full-block decoder the right first semantic guard, or should equal logical-error confidence be enough?
- Should real time mean p99, worst case, or a declared probability of stalling the logical clock?
- Is `3d` with a `2d` look-ahead buffer a fair first window, or what adversarial boundary pattern would falsify it?
- Which part should be moved to real hardware first: detector transport, matching, or feedback acknowledgement?

Zero stochastic shots and zero online-window outcomes have been observed. A pass will still be only a host-local proxy; hardware deadline, full B2, scalable #023 memory, and B7 credit remain closed.
