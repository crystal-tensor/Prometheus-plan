# If nine bits recover the final answer, why should hardware pay for sixteen?

The last public holdout produced a deceptively comfortable ending: every X/Z final frame agreed and every residual vanished. Yet the streaming decoder disagreed `58` times on intermediate outputs, so the preregistered exact-window contract correctly rejected it.

Post-outcome diagnostics on that already-public corpus reveal a precision cliff. Nine- and ten-bit grids never remove every transient disagreement. A 15-bit power-of-two scale leaves Z with one syndrome and two output mismatches; the next power of two, requiring 16-bit stored weights, clears all `335,872` X/Z window observations. That is route selection, not acceptance evidence.

The new freeze therefore asks a sharper question with untouched seeds: does the 16-bit boundary generalize to `1024` new 1,000-round shots in each basis when every syndrome, output, final frame, and residual must match exactly?

Heuristic question: if a narrow decoder always resynchronizes to the correct final logical frame, is exact transient equality the right hardware interface—or is it protecting us from a future feedback failure that this memory experiment cannot expose? What adversarial circuit or control-flow test would settle that without simply weakening the gate after seeing the answer?

Even a semantic pass does not make this hardware. Pinned Micro Blossom still lacks a functional dynamic-weight write path, and no RTL cycles, FPGA timing, p99 latency, full B2, scalable #023, or B7 resource credit is claimed.
