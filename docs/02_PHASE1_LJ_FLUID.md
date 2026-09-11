# Phase 1 — Lennard-Jones fluid

## Purpose

This phase isolates the numerical heart of molecular dynamics before introducing biomolecular complexity. It simulates 256 argon-like particles in a periodic box using the Lennard-Jones potential.

## Model

```text
U(r) = 4 ε [(σ/r)^12 - (σ/r)^6]
```

- `σ`: distance at which the potential crosses zero.
- `ε`: depth of the attractive well.
- short distances: strong repulsion;
- intermediate distances: attraction;
- long distances: interaction approaches zero.

The configured parameters are pedagogical argon-like values, not a complete experimental argon model.

## Procedure

### Step 1.1 — Preflight

Read `configs/profiles.yaml`, section `phase1`. Confirm:

- 256 particles;
- periodic cubic box;
- reduced number density 0.80;
- 120 K target temperature;
- 2 fs time step;
- shifted/smoothed cutoff region and long-range dispersion correction.

Run:

```bash
make phase1 PROFILE=quick
```

The script:

1. creates an FCC lattice without overlaps;
2. builds the OpenMM `System`;
3. assigns particle masses;
4. creates a periodic Lennard-Jones force;
5. minimizes geometry;
6. assigns Maxwell-Boltzmann velocities with the recorded seed;
7. runs NVT with a Langevin thermostat;
8. saves the final NVT state;
9. switches to NVE from that state;
10. records DCD trajectories, CSV thermodynamics, checkpoints, System XML, and PDB snapshots.

### Step 1.2 — Analyze

```bash
make phase1-analysis PROFILE=quick
```

Generated figures:

- temperature vs time;
- potential, kinetic, and total energy vs time;
- NVE energy drift with fitted slope;
- radial distribution function `g(r)`;
- particle displacement distribution;
- box snapshot.

### Step 1.3 — Visualize

```bash
make phase1-view PROFILE=quick
```

Open the generated HTML under the run's `visualization/` directory. Rotate the box and play the trajectory. Observe local ordering without a fixed lattice.

### Step 1.4 — Explain the plots

The agent must write in `REPORT.md`:

- why temperature fluctuates in NVT;
- why total energy is not conserved under a thermostat;
- why NVE is used for the drift check;
- why `g(r)` tends toward 1 at large distance;
- what the first RDF peak means physically;
- why particles may appear to jump across box edges.

### Step 1.5 — Gate

The automated gate checks:

- all coordinates and energies are finite;
- mean NVT temperature is within the configured relative tolerance;
- NVE energy drift per particle is below threshold;
- RDF has a plausible first-neighbor peak;
- trajectory and topology atom counts agree.

A passing quick run allows:

```bash
make phase1 PROFILE=teaching
make phase1-analysis PROFILE=teaching
make phase1-view PROFILE=teaching
```

## Experiments after the baseline passes

Change one parameter at a time in a copied configuration and create a decision note:

- halve/double the time step and compare NVE drift;
- vary temperature and compare RDF;
- vary density and inspect local structure;
- compare NVE and NVT energy behavior.

Never replace the baseline configuration.
