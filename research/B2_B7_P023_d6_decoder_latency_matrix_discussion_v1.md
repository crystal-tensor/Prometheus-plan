Does 4x slower still count as real time when the machine gives you 1 microsecond per round?

The preregistered batch-size matrix is complete. The correlation-aware distance-6 decoder's batch-1 software backlog proxy is **True** under the declared 1 microsecond/round line.

At batch 1, X uses 0.520854 us/round and Z uses 0.515826 us/round. At batch 256, they use 0.513660 and 0.512572 us/round.

The physical result is unchanged: 71 active qubits passed both strict correctness gates for a 1.3662x physical-memory score. But this matrix is still offline and excludes the communication/control path, so hardware deadline, full B2, #023, and B7 remain open.

Questions for critique:

- Is 1 microsecond per round the right platform-neutral backlog line, or should each hardware family declare its own cycle budget?
- Should the physical-qubit saving and classical decoder cost remain a Pareto pair instead of being collapsed into one arbitrary scalar?
- Is batch-1 full-block decoding informative enough, or must only online O(d) sliding-window latency count?
- What tail-latency percentile and communication/control budget should be mandatory before calling a decoder real time?

Current boundary: software proxy only; hardware deadline=false; full B2=false; #023=false; B7 credit=0.
