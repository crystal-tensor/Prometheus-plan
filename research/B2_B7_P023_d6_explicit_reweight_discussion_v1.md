# When an 8-bit input becomes a 24-bit decoder, which width should hardware actually prove?

The previous experiment correctly showed that quantizing detector-error probabilities did not change its frozen software answers. Source audit then exposed a stricter hardware question: PyMatching silently rescales non-integral merged and implied weights into a much wider internal integer range, while the pinned Micro Blossom RTL has only a reserved dynamic-load opcode and a TODO/commented write path.

This fresh test removes that ambiguity. Every base edge and every correlation-conditioned replacement is injected explicitly on one even-integer grid. X/Z candidate frames agree with the high-precision online reference on `1024/1024` and `1024/1024` fresh shots; online reference equals full block on `1024/1024` and `1024/1024`.

The actual stored range is X `144..264` and Z `142..264` for base edges, with implied weights ending at `164`. That makes the honest width 9 bits, not 8. The p99 number of actually lowered X/Z edges is `103/103`, or `2163/2163` raw bits at 12-bit index + 9-bit weight.

Heuristic question: should the next architecture spend bandwidth shipping those replacements, or regenerate them beside resident edge registers from a compact causal-edge broadcast? More sharply: what is the smallest RTL change that makes the reserved load instruction real without lengthening the exact-matching critical path?

The boundary matters: this is a pinned software semantic bridge, not Micro Blossom RTL execution. Until the missing write path exists and p99 cycles are measured, the one-microsecond deadline, full B2, scalable #023 memory, and B7 resource credit remain closed.

Evidence ID: `002e8453ae7beff8f89f7e5740c0ab9b6b04d8052248ee015be3e30c9f01951e`.
