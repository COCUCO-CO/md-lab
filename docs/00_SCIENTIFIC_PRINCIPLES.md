# Scientific principles and mental model

## 1. What molecular dynamics computes

Classical molecular dynamics represents atoms as particles and advances their positions and velocities by numerically integrating Newton's equations of motion:

```text
m_i d²r_i/dt² = F_i = -∂U/∂r_i
```

The potential energy `U` is defined by a force field. A typical biomolecular force field contains bonded terms (bonds, angles, torsions) and nonbonded terms (electrostatics and van der Waals interactions). The simulation does not “discover chemistry” outside the force field's model. Standard fixed-topology force fields do not break or form covalent bonds.

## 2. Force field, water model, and chemical identity

A simulation is only defined when all of the following are specified consistently:

- atom identities and connectivity;
- formal charges and protonation states;
- stereochemistry and tautomeric state;
- force-field parameter set;
- compatible water and ion parameters;
- thermodynamic ensemble and integration algorithm.

A PDB coordinate file is not sufficient chemical information for a small molecule. It often lacks bond order, formal charge, hydrogens, and stereochemical detail. Phases involving ligands therefore require a chemically explicit SDF or equivalent source.

## 3. Time step and constraints

The time step is the interval between numerical updates. Fast bond vibrations involving hydrogens limit an unconstrained all-atom simulation to a very small time step. This project constrains hydrogen-involving bonds and uses 2 fs as the conservative baseline. Do not switch to 4 fs or hydrogen-mass repartitioning until the baseline protocol passes and the change is separately validated.

## 4. Ensembles

- **NVE:** particle number, volume, and total energy are nominally conserved. Useful for checking integrator energy drift.
- **NVT:** particle number, volume, and temperature are controlled. A thermostat exchanges energy with the system.
- **NPT:** particle number, pressure, and temperature are controlled. A barostat changes the box dimensions.

Instantaneous temperature and pressure fluctuate. The relevant question is whether their distribution and time average are consistent with the target over an appropriate interval.

## 5. Periodic boundary conditions and PME

Periodic boundary conditions tile the simulation box infinitely. They reduce surface artifacts but create imaging issues in trajectories. Particle Mesh Ewald (PME) treats long-range electrostatics in periodic systems. Analysis must reconstruct whole molecules and align structures before interpreting RMSD or distances.

## 6. Minimization, equilibration, production

- **Energy minimization** removes severe clashes; it is not physical time evolution.
- **Equilibration** lets temperature, density, solvent, ions, lipids, and restrained solute relax toward the target conditions.
- **Production** collects the trajectory intended for analysis after restraints have been removed, unless a specific restrained experiment is being performed.

A production trajectory should never start directly from an unrelaxed downloaded structure.

## 7. Randomness and replicas

Thermostats and initial velocities use random numbers. A random seed makes one run reproducible but does not make it representative. Independent replicas use distinct documented seeds and are the basic unit for uncertainty estimation.

## 8. What common metrics do and do not mean

- **RMSD:** geometric deviation after a specified alignment. It is sensitive to atom selection and reference.
- **RMSF:** time-dependent positional fluctuation after alignment. It is not a direct experimental B-factor.
- **Radius of gyration:** compactness of a selected group.
- **SASA:** solvent-accessible surface area under a specified probe/model.
- **Hydrogen bonds/contacts:** operational definitions with chosen distance/angle cutoffs.
- **RDF:** radial distribution relative to an ideal gas at the same density.

No single metric establishes equilibration, convergence, or biological validity.

## 9. Tutorial vs research evidence

The quick profile answers: “Does the pipeline run correctly?”

The teaching profile answers: “Can I see and understand the expected numerical and structural behavior?”

A research profile asks a hypothesis-specific question and normally requires multiple replicas, longer trajectories, sensitivity analysis, uncertainty estimates, and comparison with independent evidence.

## 10. Units used in this project

OpenMM commonly uses:

- distance: nanometer (nm);
- time: picosecond (ps);
- energy: kJ/mol;
- temperature: kelvin (K);
- pressure: bar;
- mass: dalton;
- charge: elementary charge.

Useful conversions:

```text
1 nm = 10 Å
1 ns = 1000 ps
1 fs = 0.001 ps
500,000 steps × 2 fs = 1 ns
```
