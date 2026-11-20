# When exact streaming equivalence costs seven more bits, is that a decoder fix or a hardware warning?

The public 9-bit experiment ended with identical final X/Z frames but 58 transient output disagreements, so the strict streaming veto failed. Post-outcome route selection then found a principled power-of-two scale whose already-public corpus has zero syndrome and output disagreements; this fresh holdout asks whether that observation generalizes.

This fresh test removes that ambiguity. Every base edge and every correlation-conditioned replacement is injected explicitly on one even-integer grid. X/Z candidate frames agree with the high-precision online reference on `1024/1024` and `1024/1024` fresh shots; online reference equals full block on `1024/1024` and `1024/1024`.

The strict streaming comparison is X `0` syndrome and `0` output mismatches, and Z `0` syndrome and `0` output mismatches. Semantic veto: `pass`.

The actual stored range is X `18348..33706` and Z `18068..33706` for base edges, with implied weights ending at `20966`. The p99 number of actually lowered X/Z edges is `102/103`, or `2856/2884` raw bits at 12-bit index + 16-bit weight.

Heuristic question: if exact transient equivalence needs 16-bit weights while 9-bit weights recover the same final logical frame, should hardware pay the wider bandwidth, or should the interface expose a weaker—but explicitly justified—contract? What experiment would distinguish harmless resynchronization from a future feedback failure?

The boundary matters: this is a pinned software semantic bridge, not Micro Blossom RTL execution. Until the missing write path exists and p99 cycles are measured, the one-microsecond deadline, full B2, scalable #023 memory, and B7 resource credit remain closed.

Evidence ID: `0f5c788a433bab8ba41b84b29e8b8964bbc75d7a1a0a14dddf64bd998ad73107`.
