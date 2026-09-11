# Visualization guide

Visualization is a required validation method, not decoration.

## Standard views for every phase

1. initial prepared structure;
2. final structure;
3. aligned overlay of initial and final solute;
4. trajectory animation with solvent hidden;
5. trajectory animation with selected environment visible;
6. orthogonal box views;
7. plots synchronized to physical time, not frame index alone.

## Phase-specific views

### Phase 1

- particles as spheres;
- periodic box outline;
- color or size fixed across frames;
- optional displacement trails for a small subset.

### Phase 2

- protein cartoon plus side chains near unusual geometry;
- solvent box as translucent or hidden;
- ions as spheres;
- RMSF mapped onto structure;
- first/final overlay.

### Phase 3

- protein cartoon;
- ligand sticks/spheres with element colors;
- residues within 0.5 nm of ligand;
- hydrogen bonds/contact lines using documented definitions;
- beginning/middle/end binding-site panels.

### Phase 4/5

- membrane viewed both edge-on and top-down;
- lipid headgroups and tails separately;
- water slab and ions optionally visible;
- protein surface colored by hydrophobicity only if the scale is documented;
- membrane density profiles beside representative snapshots.

## Standalone HTML

`render_trajectory.py` creates a self-contained or locally loadable py3Dmol HTML viewer from a downsampled solute trajectory. It is intended for easy inspection in Chrome. The authoritative trajectory remains DCD/XTC plus topology; the HTML is a derived visualization.

## Plot standards

Every static plot must include:

- descriptive title;
- labeled axes with units;
- legend where multiple traces exist;
- physical time on X axis;
- no misleading truncated scale unless explicitly marked;
- replica identity when applicable;
- analysis definition in caption/report.

Do not smooth away instability. If a rolling average is shown, also show raw data and state the window.

## Visual failure examples

Stop and diagnose if you see:

- protein bonds spanning the box due to imaging;
- atoms exploding away from the system;
- vacuum gaps in an intended liquid system;
- water inside hydrophobic membrane tails in large persistent cavities not expected biologically;
- lipids crossing protein helices;
- ligand disconnected or with wrong geometry;
- missing chains or an unintended asymmetric unit;
- severe overlap not resolved by minimization.
