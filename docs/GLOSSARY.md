# Glossary

**AM1-BCC** — Semiempirical partial-charge model (HF/AM1 charges with bond-charge corrections) used for small molecules parameterized in the Open Force Field SMIRNOFF format (configs set `partial_charge_method: am1bcc`).

**Area per lipid (APL)** — Average membrane area occupied by one lipid. This project estimates it as XY box area divided by the lipid count in one leaflet, so it is only meaningful when leaflet counts and lipid identity are correct.

**Ballesteros–Weinstein numbering** — Conserved GPCR numbering in which the reference residue of each helix is x.50 (for example Asp3.32, Arg3.50, Pro5.50, Asn7.49, Ile3.36/Pro5.50/Phe6.44). Report both sequence numbering and this numbering for receptor residues.

**Barostat** — Algorithm that changes periodic box dimensions to sample a target pressure or membrane mechanical condition. Phases 2 and 3 use `MonteCarloBarostat`; Phases 4 and 5 use `MonteCarloMembraneBarostat` with XY-isotropic scaling and free Z scaling.

**BRIL** — Bril/thermostabilised apocytochrome b562 RIL fusion partner engineered into the GPCR construct. It is a crystallographic aid, not part of the biological receptor, and each retained fusion partner is a documented Phase 5 decision.

**CCD / ideal SDF** — RCSB Chemical Component Dictionary and its ideal-coordinate SDF for a ligand residue name. It supplies bond orders, aromaticity, formal charge, and element ordering that a PDB coordinate file does not.

**Checkpoint** — Binary state used to resume the same OpenMM simulation on compatible software/hardware. It is not a portable replacement for coordinates plus serialized state.

**Constraint** — Exact geometric condition, commonly fixing bonds involving hydrogen to permit a larger integration step.

**DCD** — Binary trajectory format containing coordinates and box information but not a complete chemical topology.

**DRY motif** — The conserved Asp3.49-Arg3.50-Tyr3.51 (Asp-Arg-Tyr) class-A GPCR microswitch at the cytoplasmic end of TM3; the Arg3.50–Glu6.30 ion pair across helices 3 and 6 is the associated inactive-state ionic lock.

**ECL2 / ICL2 / TM** — Extracellular loop 2, intracellular loop 2, and transmembrane helix. Loop modeling and transmembrane alignment ranges are explicit Phase 5 decisions.

**Ensemble** — Probability distribution sampled under specified conserved or controlled quantities, such as NVE, NVT, or NPT.

**Force field** — Mathematical potential and parameter set used to calculate forces from coordinates.

**Integrator** — Numerical algorithm that advances positions and velocities through time.

**Ligand microstate** — A specific combination of protonation, tautomer, stereochemical, and formal-charge state.

**NPxxY motif** — Conserved TM7 microswitch (Asn7.49-x-x-Tyr7.53) whose conformation reports on the active/inactive receptor state.

**NVE/NVT/NPT** — Ensembles controlling particle number N plus energy E, temperature T, volume V, or pressure P.

**OPM** — Orientations of Proteins in Membranes database, providing membrane-oriented coordinates.

**PBC** — Periodic boundary conditions.

**PDBFixer** — OpenMM structure-repair tool used by the phase launchers to add missing heavy atoms and standard-residue hydrogens and to enumerate nonstandard residues.

**PIF transmission switch** — The conserved Pro/IIle/Phe (Pro5.50, Ile3.36, Phe6.44) microswitch cluster in the receptor core that couples ligand binding to TM6 movement.

**PME** — Particle Mesh Ewald method for periodic long-range electrostatics.

**Production** — Post-equilibration trajectory intended for analysis under the final protocol.

**Radius of gyration** — Mass-weighted compactness of the selected group; a scalar summary of global contraction, not a folding free energy.

**RDF** — Radial distribution function, pair density relative to an ideal gas at the same bulk density.

**Replica** — Independently initialized simulation of the same model/protocol, normally with a different random seed.

**Restraint** — Added energetic penalty that biases coordinates toward a reference; unlike a constraint, deviations remain possible.

**RMSD/RMSF** — Root-mean-square deviation/fluctuation under a stated atom selection and alignment.

**SASA** — Solvent-accessible surface area for a stated selection and probe model; in this project computed on the protein with OPC virtual-site atoms excluded.

**Seed** — Integer that makes a run's random choices (initial velocities, Monte Carlo barostat, hydrogen building) reproducible. Seeds are derived from `project_defaults.seed_base` per phase and profile; a seed makes a run repeatable, not representative.

**SMIRNOFF / `SMIRNOFFTemplateGenerator`** — Open Force Field small-molecule parameter format and the OpenMM force-field plug-in that supplies ligand templates. The generator must be explicitly registered and the force field named by version (`openff-2.2.1`).

**Source waters** — Crystallographic waters present in a downloaded structure. Their fate is an explicit decision: the Phase 2 and Phase 3 tutorials remove them, Phase 4 retains all 371 of 1J4N under `docs/decisions/DR-002-phase4-source-waters.md`, and Phase 5 retains none.

**TICA / MSM** — Time-structure based Independent Components Analysis and Markov state models: a projection into slow collective variables, and a discrete-state kinetic model built from those features. Both require feature justification, lag-time and clustering sensitivity, and train/validation splits by trajectory (`07_PHASE6_7_REPLICAS_ADVANCED.md`).

**Topology** — Atoms, residues, chains, bonds, and related chemical organization required to interpret coordinates.

**Water model** — The rigid three- or four-site solvent template used consistently with the protein force field and its ion parameters: OPC in Phases 2 and 3, TIP3P in Phases 4 and 5.
