# Phase 2 — Ubiquitin in explicit water

## Purpose

Move from generic particles to a complete biomolecular workflow: structure acquisition, chemical preparation, force-field assignment, solvation, ions, minimization, restrained equilibration, unrestrained production, structural analysis, and visualization.

## Tutorial system

- PDB entry: `1UBQ`.
- Solute: ubiquitin, a small 76-residue protein.
- Protein force field: Amber ff19SB as distributed with OpenMM.
- Water/ions: OPC model and its compatible ion parameters.
- Salt: 0.15 M NaCl after neutralization.
- pH used for automatic hydrogen placement: 7.0.

The source PDB is preserved unchanged and hashed.

## Preparation audit

Before simulation, the script and agent must report:

- chains and residue ranges;
- alternate locations;
- nonstandard residues;
- missing residues reported by the structure;
- missing heavy atoms;
- disulfide bonds;
- retained and removed heterogens;
- total formal system charge before ions;
- number of waters and ions after solvation;
- periodic box dimensions.

Any missing internal loop longer than five residues requires human review. Do not build it automatically.

## Procedure

### Step 2.1 — Run quick preparation and simulation

```bash
make phase2 PROFILE=quick
```

The script performs:

1. download `1UBQ.pdb` to immutable `inputs/phase02/`;
2. hash and record the source;
3. inspect and repair standard-residue heavy atoms;
4. remove crystallographic bulk water for this controlled tutorial;
5. add hydrogens at pH 7.0;
6. create a periodic OPC water box with 1.0 nm padding;
7. neutralize and add NaCl to 0.15 M;
8. create the PME system with HBond constraints and rigid water;
9. add protein-heavy-atom positional restraints;
10. minimize;
11. perform NVT heating/thermalization at fixed volume;
12. perform NPT density relaxation through decreasing restraints;
13. remove restraints and run unrestrained NPT production;
14. save checkpoints, states, trajectory, logs, snapshots, and System XML.

### Step 2.2 — Inspect the prepared structure before trusting the run

Open the prepared PDB in the standalone viewer or another molecular viewer. Check:

- protein is centered and chemically intact;
- no atom is visibly isolated;
- water fills the periodic box;
- no ion overlaps the protein;
- termini and side-chain hydrogens appear plausible;
- box dimensions are sensible.

The visualization check is mandatory even when minimization succeeds.

### Step 2.3 — Analyze

```bash
make phase2-analysis PROFILE=quick
make phase2-view PROFILE=quick
```

Required analyses:

- temperature, potential energy, density, and volume;
- Cα RMSD after Cα alignment;
- per-residue Cα RMSF after alignment;
- radius of gyration;
- solvent-accessible surface area;
- secondary-structure proxy or backbone contact map;
- first vs final structure overlay;
- performance in ns/day.

### Step 2.4 — Interpret correctly

The agent must explain:

- RMSD depends on alignment and reference;
- an early RMSD rise can be relaxation from a crystal environment;
- density should be assessed after NPT begins, not during NVT;
- pressure is noisy in a small box and instantaneous pressure is not a stability criterion;
- a short trajectory cannot establish protein stability or equilibrium.

### Step 2.5 — Gate

Mandatory conditions include:

- no NaN or constraint error;
- thermodynamic log has expected number of rows;
- mean production temperature within tolerance;
- mean density within configured range;
- Cα RMSD below the broad tutorial sanity threshold;
- no obvious broken covalent geometry;
- all output files readable.

After quick passes, run teaching. The teaching profile is still too short for many biological claims; its main goal is a clearer trajectory and more interpretable statistics.
