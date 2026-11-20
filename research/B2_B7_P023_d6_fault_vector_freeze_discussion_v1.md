What if the decoder returned the correction instead of the path?

The last experiment made the interface narrower and gained `1.156×` geometrically, yet the C++ correlated matcher still crossed the one-microsecond line. This preregistration asks a different interface question without changing a single graph edge or weight.

Instead of returning selected edges and reconstructing their effects in Python, every committed component now labels the detector and observable bits it would flip. PyMatching's supported public `Matching.decode` call returns that parity vector directly, and vectorized XOR applies it.

The deterministic scan already verifies graph equality in all `328/328` X/Z windows. The output representation needs only `40,870/40,868` total bits across the windows, with at most `789/788` in any one graph. No nonzero candidate prediction or timing has been observed.

Questions for critique:

- Is correction-bit fault-ID encoding a stable enough output ABI for a maintained decoder path?
- If public decode still owns the tail, does that falsify interface tuning as the main route?
- Which graph invariant beyond endpoints, weights, probabilities, and correlation groups should be frozen?
- Can a controller consume the parity vector directly without recreating a Python-style propagation layer?

Candidate X/Z must reproduce all `2,048` frozen predictions and every residual invariant before any relative speedup counts. Shot batching is forbidden, the one-microsecond line remains absolute, and hardware deadline, full B2, scalable #023 memory, and B7 credit remain false.
