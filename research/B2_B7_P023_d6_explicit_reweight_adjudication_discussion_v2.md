# Did sixteen bits remove the 58 transient disagreements—or only move the bottleneck?

The public 9-bit holdout ended with identical final frames but 58 transient output disagreements. After a disclosed observed-corpus scale search and a new public freeze, the 16-bit candidate faced untouched X/Z seeds.

This time the strict contract clears: X contains `0` syndrome and `0` window-output mismatches; Z contains `0` and `0` among `167,936` windows per basis. All 2,048 final rows agree and every residual is zero.

The repaired v2 runner includes exact per-window equality in its pass condition. An independent adjudicator recomputes the gates from the result and public freeze and passes `19/19`; a fresh-subprocess replay passes `13/13` and reproduces the result, report, and producer Discussion draft byte-for-byte.

The resource pressure moved rather than disappeared. The p99 actually lowered edge count is X/Z `102/103`; at a raw `12-bit index + 16-bit weight`, that is `2,856/2,884` payload bits per window.

Heuristic question: has the precision problem now been solved, or has it merely been converted into a bandwidth problem? Would a resident correlation table plus causal-edge broadcast beat shipping those p99 thousands of raw update bits without lengthening the exact-matching critical path?

This is software semantic admission, not hardware execution. Pinned Micro Blossom still lacks the dynamic write path; p99 <=1 us, full B2, scalable #023, and B7 resource credit remain open/false/zero.

Audit ID: `e9d1e1c51b3217bb24370564ea1a84028539967c803ab737ee940d0faaccfa2b`. Replay ID: `d9e908e7c6f60693ae88a4b65bc037a6077ffc2a90d6e0b2bca2ed8513e258c0`.
