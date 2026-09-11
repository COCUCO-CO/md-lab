# Reproducibility and reporting

## Minimum reproducibility package

For every reported simulation, preserve:

- original source files and hashes;
- prepared coordinates and topology;
- force-field names and versions;
- ligand identity and parameterization report;
- protonation decisions;
- box composition;
- integrator, thermostat, barostat, timestep, constraints, cutoffs, PME tolerance;
- equilibration schedule and restraints;
- random seeds;
- software environment export;
- hardware/driver information;
- run logs and checkpoints;
- analysis scripts and exact selections;
- excluded data and failed runs;
- figures generated from scripts.

## REPORT.md structure

Every phase report must contain:

1. Objective.
2. Input provenance.
3. System composition.
4. Hamiltonian and simulation settings.
5. Preparation decisions.
6. Equilibration protocol.
7. Production protocol.
8. Performance.
9. Validation results.
10. Figures and their interpretation.
11. Limitations.
12. Gate outcome.
13. Next permitted action.

## Provenance table

Use a table with:

```text
file | source | downloaded UTC | SHA-256 | role
```

## Scientific language

Prefer:

- “The production mean temperature was X ± Y K over Z ps.”
- “After Cα alignment, RMSD ranged from ...”
- “Across three replicas, contact occupancy was ...”

Avoid:

- “The simulation proved the protein is stable.”
- “The ligand binds strongly because it stayed in the pocket.”
- “The system converged” without a defined diagnostic.

## Archiving

For sharing, create a compact artifact containing configs, manifests, prepared topology/coordinates, analysis tables, figures, reports, and a downsampled trajectory. Full trajectories may be archived separately due to size. Never omit the exact analysis scripts.
