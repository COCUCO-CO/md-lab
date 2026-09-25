# Phase 4 — Aquaporin-1 in a POPC membrane

## Purpose

Learn how a membrane system differs from a soluble protein: orientation relative to the bilayer, lipid packing, asymmetric box relaxation, membrane-specific barostatting, and membrane observables.

## Tutorial system

- Protein: bovine aquaporin-1, PDB `1J4N`, biological tetramer.
- Orientation source: OPM (Orientations of Proteins in Membranes).
- Membrane: homogeneous POPC.
- Protein force field: Amber ff19SB.
- Lipid force field: Amber Lipid21.
- Water/ions: Amber-compatible TIP3P and 0.15 M NaCl.
- Membrane normal: Z axis.

The OPM file may contain dummy membrane-boundary atoms. They are orientation markers, not physical particles, and must be removed before parameterization while retaining the oriented protein coordinates.

OpenMM's bundled POPC membrane patch labels POPC residues as `POP` in the
prepared PDB. Reports distinguish the chemical lipid type (`POPC`) from that
topology residue name.

Decision record `DR-002` requires retaining all 371 source `HOH` residues.
The 12 detergent `BNG` residues and 2418 `DUM` membrane markers are removed.
The crystallographic `CRYST1` unit cell is recorded but not reused as the
simulation box; `Modeller.addMembrane()` constructs the periodic membrane box
from the oriented solute and configured padding.

## Why orientation matters

A membrane builder assumes the protein is positioned relative to a bilayer. Arbitrarily using the RCSB coordinate frame can place hydrophobic helices in water or polar domains inside the bilayer. The script downloads the OPM-oriented structure, records its source, removes nonphysical boundary markers, and verifies the transmembrane axis visually.

## Procedure

### Step 4.1 — Preflight the biological assembly

The agent must report:

- number of protein chains;
- whether the expected tetramer is present;
- missing residues/atoms;
- membrane-normal axis;
- approximate hydrophobic thickness from OPM metadata;
- any bound waters or non-protein components;
- whether the input is the asymmetric unit or biological assembly.

Do not continue with a monomer if the selected tutorial protocol expects the tetramer.

### Step 4.2 — Build the membrane system

```bash
make phase4 PROFILE=quick
```

The script:

1. retrieves the OPM-oriented PDB through the official asset link;
2. removes membrane-boundary dummy atoms and `BNG`, retaining all source waters
   under `DR-002`;
3. repairs only unambiguous standard-residue atoms;
4. adds hydrogens at pH 7.0;
5. calls OpenMM `Modeller.addMembrane()` using POPC, water, ions, a deterministic
   preparation seed, and the fixed CPU settings recorded in `DR-004`;
6. records lipid counts per leaflet, source and added waters, ions, box vectors,
   parameterization status, and inter-component heavy-atom distances;
7. applies protein-heavy-atom restraints;
8. minimizes;
9. runs short fixed-volume relaxation;
10. switches to `MonteCarloMembraneBarostat` with isotropic XY scaling and free Z scaling;
11. reduces restraints in stages;
12. runs unrestrained membrane production.

### Step 4.3 — Mandatory visual checks

Before interpreting any numbers, inspect views along Z and in the membrane plane:

- hydrophobic transmembrane region overlaps lipid tails;
- extracellular/cytoplasmic domains are hydrated;
- no lipid tail crosses the protein core unnaturally;
- no large vacuum gap exists;
- leaflets are continuous;
- protein oligomer is intact;
- the periodic box is oriented with membrane normal along Z.

### Step 4.4 — Analyze

```bash
make phase4-analysis PROFILE=quick
make phase4-view PROFILE=quick
```

Required plots:

- temperature and energy;
- box X, Y, and Z lengths;
- XY area;
- approximate area per lipid;
- phosphate-to-phosphate membrane thickness;
- protein Cα RMSD;
- lipid phosphorus Z-density;
- water oxygen Z-density;
- protein/lipid/water cross-section snapshots.
- retained-source and all-water occupancy in the membrane core and operational
  pore cylinders.

Static cross-sections are generated before the gate is finalized. The
analysis script runs in two stages: `python scripts/phase4_analyze.py --profile
<profile> --figures-only` writes the metrics, `preliminary_metrics.json`, and the
static figures and stops with `FIGURES_READY_FOR_VISUAL_INSPECTION`; the reviewer
then records all mandatory visual checks in `analysis/visual_inspection.json`
with exactly these keys, all set from direct inspection:

```text
hydrophobic_region_overlaps_lipid_tails_pass
domains_hydrated_pass
no_lipid_tail_through_protein_core_pass
no_large_vacuum_gap_pass
leaflets_continuous_pass
oligomer_intact_pass
membrane_normal_z_pass
```

The final analysis run reads that file; a missing record or a missing key is a
hard error, and missing visual evidence is never treated as a pass.

### Step 4.5 — Understand membrane metrics

Area per lipid is computed from XY box area divided by the number of lipids in one leaflet. It is only meaningful when leaflet counts and lipid identity are correct. Membrane thickness is estimated from the separation of phosphorus density peaks; it is model- and definition-dependent.

Short membrane runs primarily validate system construction. Lipid packing and protein-lipid adaptation may require far longer than the tutorial profile.

### Step 4.6 — Gate

The gate requires:

- expected tetramer and topology;
- no NaN/constraint errors;
- continuous bilayer by visual and density checks;
- approximate area per lipid and thickness within deliberately broad POPC sanity ranges;
- no major protein disassembly;
- no persistent vacuum gap;
- all 371 approved source waters retained and separately identifiable;
- no gross covalent or inter-component geometry failure under `DR-003`;
- all analysis outputs readable.
