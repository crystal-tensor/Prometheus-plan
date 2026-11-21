# When two RTL simulators agree byte-for-byte, is backend speed still only an engineering detail?

The first complete frozen X shot now has two independent hosted RTL executions: Icarus 13.0 and Verilator 5.040. Their complete output JSON files have the same SHA-256, `aca01e62…a153`—not just the same pass/fail summary. Every syndrome, selected subgraph edge, correction bit, occupancy check, and iteration count serialized identically across all 164 consecutive opening/steady/closing windows.

That equivalence changes the practical experiment. The same shot's simulation body falls from 439.70 seconds to 7.38 seconds, a 59.56× reduction. A persistent eight-shot run then passes another 1,312/1,312 windows in 57.55 seconds of simulation body. We have now tested 9/1,024 frozen X shots, or 1,476/167,936 cases, without changing the corpus or acceptance rule.

The heuristic question is: **once two simulators produce byte-identical evidence on the calibration shot, what additional cross-backend sampling is enough before the faster backend should carry the rest of a frozen correctness campaign?** Should we periodically insert Icarus audit shots, or is a hash-identical full-shot calibration plus immutable source/corpus binding sufficient?

The boundary remains deliberately strict. This is software simulation, not hardware latency; Z, AXI, FPGA timing/resources, `p99 <= 1 us`, miss `<= 1%`, full B2, scalable #023, and B7 credit all remain open. The immediate falsifier is the unchanged remaining 1,015-shot X run.
