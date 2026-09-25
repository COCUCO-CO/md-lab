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

## Generated viewers

`scripts/render_trajectory.py --phase N --profile P [--max-frames M]` is the
supported viewer launcher (`make phaseN-view PROFILE=quick`, N = 1..5). It
resolves the latest run of that phase and profile, extracts a solute selection
from the production (Phase 1: NVT) trajectory, and writes three files:

```text
visualization/trajectory_multimodel.pdb  downsampled solute frames + box records
visualization/viewer.html              interactive 3Dmol.js page
visualization/viewer.vmd               equivalent VMD startup script
```

Facts to know before opening a viewer:

- `viewer.html` embeds the coordinates and loads the 3Dmol.js script from
  `https://3Dmol.org/build/3Dmol-min.js`, so the page needs network access to
  that CDN. For a fully offline view run `vmd -e viewer.vmd` from the
  `visualization/` directory.
- The viewer is a visualization of a downsampled solute subset, never the
  authoritative data. The authoritative data are `simulation/production.dcd`
  (Phase 1: `nvt.dcd`) plus `prepared/system.pdb` (`initial.pdb` in Phase 1).
- `--max-frames` is a cap, not an exact count; the script thins the trajectory to
  at most that many frames and Phase 4 and Phase 5 additionally cap the viewer to
  12 frames so the HTML stays loadable. Phase 4 and Phase 5 also re-center each
  protein chain and every other residue under periodic boundaries before writing
  the multimodel PDB, so a molecule cannot span the box in the viewer.
- Phase 4 includes protein, lipid (`POP`) and the retained source waters, so the
  approved crystallographic waters can be watched inside the channel.
- Phase 5 writes one viewer per condition under
  `systems/<condition>/visualization/` and a landing page
  `visualization/index.html` that links both, and it also writes `viewer.vmd`
  scripts that read the full DCD with `pbc wrap` applied.
- `py3Dmol` is installed for notebook use (`notebooks/`); the launcher above does
  not depend on it.

In the accepted Phase 5 runs the reviewer also stored browser screenshots of both
viewers as inspection evidence
(`analysis/lsd_html_viewer.png`, `analysis/lisuride_html_viewer.png`,
`analysis/viewer_verification.json`), listed in the `evidence` array of
`analysis/visual_inspection.json`, which is a gate input
(see `12_RUN_ARTIFACTS.md` and `06_PHASE5_5HT2A_RESEARCH.md`).

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
