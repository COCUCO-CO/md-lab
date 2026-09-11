# Evaluation gates

Compare the untouched base model, the QLoRA adapter and each specialist tool.

## Chemistry and reactions

- valid and stereochemically preserved structures;
- forward top-k accuracy and atom conservation;
- retrosynthesis top-k, diversity and forward round-trip validity;
- condition/reagent/solvent/catalyst extraction F1;
- temporal and CHORISO out-of-distribution performance;
- PaRoutes multistep solved rate, route diversity and search cost.

## Quantum chemistry and molecular simulation

- method/tool selection on expert-written cases;
- valid input generation without silently selected charge, multiplicity,
  protonation, force field, ensemble or numerical thresholds;
- unit and dimensional-analysis accuracy;
- exact provenance recovery for computed results;
- correct recognition of nonconvergence, SCF failure, NaN, constraint failure,
  insufficient replicas and insufficient trajectory length;
- no mechanistic conclusion from tutorial-length trajectories.

## Retrieval and trust

- citation precision and source-support rate;
- recall on known-answer evidence sets;
- exact distinction between observed, calculated and predicted claims;
- calibrated abstention when evidence is absent or contradictory;
- license and benchmark leakage remain zero.

## Human review

Two independent domain experts should blindly review a preregistered sample of
reaction, quantum, MD and medicinal-chemistry answers. Novel routes or research
claims are never promoted based only on automatic metrics.

