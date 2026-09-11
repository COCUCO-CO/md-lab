# Operating rules for the chemistry research agent

These rules supplement the repository-level `AGENTS.md`. The molecular-dynamics
state machine remains authoritative for `mdlab`; work here must not advance or
modify its phases.

1. Never download or ingest a source until its registry entry and license have
   passed the governance gate.
2. Record URL, access time, version, SHA-256, license evidence and source record
   identifier for every local artifact.
3. Never treat access to a book, paper or database as permission to train on it.
4. Never put benchmark test records in training data.
5. Keep observed, extracted, calculated and predicted values distinct.
6. Preserve charge, stereochemistry, isotopes, units, method, basis set,
   thermodynamic ensemble and simulation conditions.
7. Never invent a yield, condition, numerical result or citation.
8. Quantum calculations, molecular dynamics and cheminformatics tools must
   return machine-readable provenance. The LLM is not a numerical oracle.
9. Do not run laboratory equipment or production simulations autonomously.
10. Procedural content for chemical weapons, energetic materials, highly toxic
    agents or illegal drugs is excluded from generative training and output.
    Hazard knowledge may remain available for recognition and screening.
11. A model suggestion is a hypothesis. Experimental or simulation claims need
    independent validation and expert review.
12. Training runs are immutable and must record configuration, code snapshot,
    model revision, data manifest hash, environment, hardware and random seed.

