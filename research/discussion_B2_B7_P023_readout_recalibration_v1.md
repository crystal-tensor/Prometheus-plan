# When is it worth teaching a surface-code decoder that its noise model is wrong?

We raised the simulated readout-flip probability by 25% but left the decoder thinking nothing had changed. The 71-qubit memory still passed the strict 1,000-round X/Z gate. A second decoder estimated the new readout rate from just 256 independent syndrome histories, without logical answers. It got close to the injected rate, but on the same 102,400 held-out shots per basis it changed X failures from 518 to 520 and Z from 446 to 443. We are keeping the simpler decoder for this condition.

**What could we read from syndrome histories alone that would tell us when a frozen decoder actually needs to be updated?** Would you test detector time autocorrelation, groups of simultaneous readout errors, or another observable? If you know of a trace or a compact noise model that separates those cases at the same marginal error rate, we'd like to try a test with the same X/Z pass rule and a held-out stream fixed before looking at outcomes.

[Protocol, failure counts and reproduction instructions](https://github.com/crystal-tensor/Prometheus-plan/blob/main/research/B2_B7_P023_readout_recalibration_v1.md)
