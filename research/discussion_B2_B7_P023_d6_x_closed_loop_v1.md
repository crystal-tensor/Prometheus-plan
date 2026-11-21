# Should a streaming quantum decoder reproduce a canonical correction—or only a correct trajectory?

Our first 127-shot RTL replay failed in an unexpected way: every syndrome was corrected and every logical bit agreed, but 21 per-window correction vectors differed from the frozen software trajectory. Those differences were not inert; they changed detector state committed by the next window, so we refused to count the block.

We then ran the first counterexample in closed loop. At shot 15/window 59, RTL again chose the alternative valid correction. That changed window 60 from 14 defects and 7 selectors to 12 defects and 6 selectors. The next RTL correction cleared the commit residual, the trajectories reconverged, and the complete shot ended with zero detector residual and the correct logical frame. A calibration shot plus the counterexample pass all 328 windows and 3,254 occupancy checks.

The heuristic question is: **for streaming QEC, is canonical tie-breaking part of correctness, or should the contract be zero committed residuals and the correct final logical frame under the decoder's own state trajectory?** Canonicalization makes cross-implementation replay simpler. Closed-loop testing permits legitimate matching degeneracy but exposes real temporal behavior.

We now count 10/1,024 distinct frozen X shots, not the rejected 127-shot block. The next falsifier is the remaining X corpus through the closed-loop route. Z, AXI, FPGA, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 credit remain open.
