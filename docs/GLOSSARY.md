# Glossary

**Barostat** — Algorithm that changes periodic box dimensions to sample a target pressure or membrane mechanical condition.

**Checkpoint** — Binary state used to resume the same OpenMM simulation on compatible software/hardware. It is not a portable replacement for coordinates plus serialized state.

**Constraint** — Exact geometric condition, commonly fixing bonds involving hydrogen to permit a larger integration step.

**DCD** — Binary trajectory format containing coordinates and box information but not a complete chemical topology.

**Ensemble** — Probability distribution sampled under specified conserved or controlled quantities, such as NVE, NVT, or NPT.

**Force field** — Mathematical potential and parameter set used to calculate forces from coordinates.

**Integrator** — Numerical algorithm that advances positions and velocities through time.

**Ligand microstate** — A specific combination of protonation, tautomer, stereochemical, and formal-charge state.

**NVE/NVT/NPT** — Ensembles controlling particle number N plus energy E, temperature T, volume V, or pressure P.

**OPM** — Orientations of Proteins in Membranes database, providing membrane-oriented coordinates.

**PBC** — Periodic boundary conditions.

**PME** — Particle Mesh Ewald method for periodic long-range electrostatics.

**Production** — Post-equilibration trajectory intended for analysis under the final protocol.

**RDF** — Radial distribution function, pair density relative to an ideal gas at the same bulk density.

**Replica** — Independently initialized simulation of the same model/protocol, normally with a different random seed.

**Restraint** — Added energetic penalty that biases coordinates toward a reference; unlike a constraint, deviations remain possible.

**RMSD/RMSF** — Root-mean-square deviation/fluctuation under a stated atom selection and alignment.

**Topology** — Atoms, residues, chains, bonds, and related chemical organization required to interpret coordinates.
