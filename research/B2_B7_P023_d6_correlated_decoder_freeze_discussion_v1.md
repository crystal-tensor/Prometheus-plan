Can correlations rescue a cheaper quantum memory after ordinary matching says no?

The 71-active-qubit distance-6 memory lost its first strict trial: independent MWPM could not keep either X or Z below the 1% ceiling. The tempting response is to rerun until luck changes. We are taking a falsifiable route instead—freeze a genuinely different decoder before it sees any new sample.

The circuit and physics are unchanged. PyMatching's two-pass correlated mode is the sole change. This is not a cosmetic switch: the frozen X and Z DEMs contain **540,061** and **540,040** decomposed-hyperedge instructions, respectively, which the second matching pass can use for correlation-aware reweighting.

The reward, if both bases strictly pass, is still **97/71 = 1.3662×** physical-memory improvement. If either fails, the accepted score is zero.

At this public-freeze stage:

- correlated-decoder stochastic shots: 0
- observed correlated-route failures: none
- acceptance salt and seeds: absent
- full B2, #023, and B7 credit: closed

Questions worth arguing about before execution:

- Is exploiting decomposed Y-error correlations a fair decoder improvement, or does it hide classical complexity that should be priced explicitly?
- Should a slower decoder be allowed to buy a 26-qubit reduction if it still meets a declared real-time deadline?
- If the strict result still fails, does that falsify the decoder route—or the entire 71-qubit target under this noise model?
- What runtime metric would make physical-qubit savings and classical decoding cost genuinely comparable?

Next, and only after publication: reveal a commit-bound salt and run exactly 102,400 X plus 102,400 Z shots under the frozen correlated decoder.
