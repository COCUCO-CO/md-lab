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

Each analysis script writes `REPORT.md` in the run root. The generated sections
are:

| Phase | Generated sections |
|---|---|
| 1 | Objective, Results, Figures, Interpretation, Limitations, Gate |
| 2 | Objective, Quantitative results, Figures, Interpretation, Limitations, Gate |
| 3 | Objective, Chemical identity, Quantitative results, Figures, Interpretation limits, Gate |
| 4 | Objective, Preparation observations, Production observations, Visual inspection, Interpretation limits, Gate |
| 5 | Scope, Preparation observations, Production observations, Gate (plus per-condition `analysis/metrics.json`, `analysis/checks.json`, and the run-level `analysis/contact_comparison.json`) |

Those sections are generated from the run's own numbers. A human-accepted run
adds the parts a script cannot know, and the completed report must therefore also
state:

1. input provenance (sources, URLs, hashes) and system composition;
2. the Hamiltonian and simulation settings actually resolved, citing
   `resolved_config.yaml` and its hash;
3. the preparation and equilibration decisions taken, each pointing to a decision
   record when it was a scientific choice;
4. performance (`simulation/performance.json`, ns/day after warm-up);
5. every figure with its analysis definition and interpretation limit;
6. the gate outcome and the next permitted action.

For Phase 5 the accepted teaching report is a mechanical record, not research
acceptance; the human research approval lives in `state/decisions/`.

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

For sharing, create a compact artifact under `artifacts/` containing configs, manifests, prepared topology/coordinates, analysis tables, figures, reports, and a downsampled trajectory (`visualization/trajectory_multimodel.pdb`). Full trajectories may be archived separately due to size; `*.xtc`, `*.dcd`, `*.cpt`, and `*.tpr` files are git-ignored by design, so the run's hashes and configs are what make them verifiable. Never omit the exact analysis scripts.

The exact per-phase file inventory is specified in `12_RUN_ARTIFACTS.md`; check a
new run against it before archiving.
