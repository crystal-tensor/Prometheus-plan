# Can a benchmark earn credibility by rejecting one candidate while accepting another?

Two activation gates have now become executable, and they disagree in the useful way.

- **`#049` reaction dynamics:** a fourth-order real-space propagator agrees with a grid-converged split-operator denominator on `3/3` unopened momenta. Its largest transmission error is `2.407e-06`. A deliberately weaker second-order control fails `2/3` holdouts.
- **`#050` self-assembly:** the off-target-aware search lowers the hidden off-target rate, but improves yield by only `7.03` percentage points over random search and `1.49` points over target-only search. The frozen rule requires ten points over both, so the candidate is rejected.

That contrast raises a harder question than “did the code run?”: **what kind of
negative control makes a frontier benchmark trustworthy before the model becomes
high fidelity?**

Three prompts for collaborators:

1. Is the `#049` Gaussian barrier too forgiving, and which public reactive potential
   should replace it without reopening the holdout logic?
2. Which minimum piece of cooperative kinetics must enter `#050` before a ten-point
   yield margin is scientifically meaningful?
3. Should the `#050` ten-point threshold remain fixed when off-target rate improves,
   or is a predeclared Pareto rule more honest?

The boundary is deliberate: these are numerical preflights. There is no molecular
fidelity claim, wet-lab recommendation, environmental release, or solved frontier.

Research packet: `research/P049_P050_executable_preflight_v1.md`
