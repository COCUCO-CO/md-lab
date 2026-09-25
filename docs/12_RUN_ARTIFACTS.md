# Run artifacts and machine-readable contracts

This page is the normative description of what a run directory must contain and
of the machine-readable files that the gates write. It is derived from
`src/mdlab/core.py`, `src/mdlab/biomolecular.py`, and the `scripts/phase*.py`
launchers. `README.md` states the completion criterion in prose; this document
states the exact file names and fields.

## Run identifiers

`mdlab.core.run_id` builds every run directory name as:

```text
outputs/phaseNN/phaseNN_<profile>_<UTC YYYYMMDDTHHMMSSZ>_<git-short-sha|nogit>
```

`latest_run(phase, profile)` resolves "the newest run of this phase and profile"
by lexical sort, so the timestamp makes the newest directory sort last. A failed
run is never overwritten: the next launch creates a new identifier.

`<git-short-sha>` is `nogit` when `git rev-parse` fails, for example when the
tree was copied without its `.git` directory.

## Directories created by every launcher

`mdlab.core.create_run` creates, for each run:

```text
prepared/       immutable-ready coordinates, topology, audit JSON, System XML
simulation/     trajectories, thermodynamic CSV logs, checkpoints, final states
analysis/       CSV/JSON tables produced by the analysis script
figures/        static PNG figures
visualization/  interactive HTML viewers and VMD scripts
logs/           empty; the operator tees shell output here (see below)
resolved_config.yaml   the fully resolved configuration for this run
manifest.json   provenance record, opened with status RUNNING
```

`resolved_config.yaml` is hashed into `manifest.json` as
`resolved_config_sha256`. Phases 4 and 5 additionally write `FAILURE.md` in the
run root when the launcher raises, and record the exception type and message in
`manifest.json`.

`logs/` is created empty. The launchers create the run directory themselves and
print its path as their last line, and the Makefile targets do not redirect
output, so the operator records the launcher output explicitly and files it in
that run, for example:

```bash
make phase5 PROFILE=quick 2>&1 | tee /tmp/make_phase5.log
mv /tmp/make_phase5.log outputs/phase05/<run-id>/logs/make_phase5.log
```

Phase 5's accepted runs follow exactly this convention
(`make_phase5.log`, `phase5_analysis_figures_only.log`,
`phase5_analysis_final.log`, `phase5_view.log`).

## `manifest.json`

Written by `mdlab.core.base_manifest`, closed by `finish_manifest`:

| Field | Meaning |
|---|---|
| `schema_version` | currently `1` |
| `phase`, `profile` | phase number and `quick`/`teaching` |
| `start_utc`, `end_utc` | ISO-8601 UTC, second resolution, `Z` suffix |
| `status` | see the state list below |
| `cwd`, `command`, `python`, `host`, `platform`, `machine`, `processor` | execution context |
| `git_sha`, `git_status` | short HEAD SHA and `git status --porcelain` output |
| `inputs` | map of downloaded input name to its provenance record |
| `outputs` | produced artifacts; Phase 5 stores `outputs.conditions` per condition |
| `restarts` | reserved list for documented checkpoint restarts |

`status` values used by the code: `RUNNING` (on creation), `SIMULATION_COMPLETE`,
`SIMULATION_FAILED`, `PREFLIGHT_FAILED`, `ANALYSIS_COMPLETE`, `GATE_FAILED`.
These are run-manifest statuses; they are separate from the phase/profile states
in `state/progress.json` described in `../agent/STATE_MACHINE.md`.

## Input provenance

`mdlab.core.download` writes, next to every downloaded file,
`<file>.provenance.json` with `url`, `downloaded_utc`, `path`, `bytes`, and
`sha256`. A re-run reuses an existing input only when its sidecar matches the
requested URL and the recomputed SHA-256; otherwise it raises
`Immutable input provenance mismatch` instead of silently re-downloading.

## `gate.json`

Phases 1 to 4 write:

```json
{ "phase": 1, "profile": "quick", "status": "PASS", "checks": { "...": true } }
```

Phase 5 writes the same top-level keys plus a per-condition breakdown:

```json
{ "phase": 5, "profile": "quick", "status": "PASS",
  "condition_status": { "lsd": "PASS", "lisuride": "PASS" },
  "conditions": { "lsd": { "...": true }, "lisuride": { "...": true } } }
```

Every `checks` entry whose name ends in `_pass` is a gate condition; the other
keys report the underlying numbers. Phase 1 and Phase 2 also carry a
`finite_values` flag (not suffixed `_pass`) that the status formula conjoins in
addition to the `_pass` keys. Phase 5 gates each condition by 24 `*_pass` checks
and reports `condition_status`; the run `status` is `PASS` only when every
condition is `PASS`. Every analysis script exits non-zero when its gate is `FAIL`
(`phase5_analyze.py` exits 1), so a failed gate also breaks a shell pipeline.

## Per-phase artifacts

### Phase 1 — Lennard-Jones fluid

- `prepared/`: `system.xml`, `initial.pdb`
- `simulation/`: `nvt.dcd|csv|chk`, `nvt_final.pdb|.xml`, `nve.dcd|csv|chk`,
  `nve_final.pdb|.xml`, `performance.json`
- `analysis/`: `rdf.csv`, `particle_displacements.csv`, `summary.json`
- `figures/`: `temperature.png`, `nve_energies.png`, `nve_drift.png`, `rdf.png`,
  `particle_displacements.png`, `box_snapshot.png`

### Phases 2, 3, 4 — staged biomolecular runs

`mdlab.biomolecular.run_staged_simulation` writes into `prepared/`:
`system.xml`, `minimized.pdb`, and (from the phase script) `system.pdb`,
`preparation_audit.json`; into `simulation/`: `minimization.json`,
`equil_nvt.csv` + `equil_nvt_final.pdb|.xml`,
`equil_npt_<NN>.csv` + `equil_npt_<NN>_final.pdb|.xml` for each restraint
window, `production.dcd`, `production.csv`, `production.chk`,
`production_final.pdb|.xml`, `performance.json`. Phase 5 inserts an
`equil_unrestrained.*` pre-production block between the last restraint window
and production.

Analysis artifacts by phase:

- Phase 2 `analysis/`: `timeseries.csv`, `rmsf.csv`, `ca_contact_occupancy.csv`;
  `figures/`: `temperature.png`, `density.png`, `potential_energy.png`,
  `volume.png`, `ca_rmsd.png`, `ca_rmsf.png`, `radius_gyration.png`, `sasa.png`,
  `ca_contact_map.png`, `ca_first_final_overlay.png`.
- Phase 3 `analysis/`: `contact_occupancy.csv`, `timeseries.csv`,
  `binding_site_snapshots.json`; `figures/`: `temperature.png`, `density.png`,
  `protein_rmsd.png`, `ligand_rmsd.png`, `ligand_com.png`,
  `minimum_distance.png`, `contact_occupancy.png`,
  `binding_site_snapshots.png`, `ligand_identity_2d.png`.
- Phase 4 `analysis/`: `membrane_timeseries.csv`, `oligomer_distances.csv`,
  `z_density.csv`, `cross_section_snapshots.json`, `preliminary_metrics.json`,
  plus the reviewer-authored `visual_inspection.json`; `figures/`: `thermodynamics.png`,
  `box_lengths.png`, `xy_area.png`, `area_per_lipid.png`,
  `membrane_thickness.png`, `protein_rmsd.png`, `z_density.png`,
  `cross_section_snapshots.png`, `top_view_snapshot.png`,
  `source_water_occupancy.png`.

Phase 3 also reads the pinned ligand hydrogen definition
`configs/BNZ_hydrogens.xml`; Phase 4 records lipid counts per leaflet, retained
source waters, ions, box vectors, and inter-component minimum distances in
`prepared/preparation_audit.json`.

### Phase 5 — two matched conditions in one run

A Phase 5 run keeps shared bookkeeping at the run root and one full system tree
per condition:

```text
<run>/manifest.json            includes outputs.conditions.<condition>
<run>/resolved_config.yaml
<run>/REPORT.md, gate.json, RUN_INDEX.md
<run>/prepared/README.md       pointer page
<run>/simulation/README.md     pointer page
<run>/figures/README.md        pointer page
<run>/analysis/contact_comparison.json, preliminary_metrics.json
          (script-generated)
<run>/analysis/visual_inspection.json, research_budget.json,
          visual_inspection_montage.png, equilibration_montage.png,
          viewer_verification.json, lsd_html_viewer.png,
          lisuride_html_viewer.png, WARNINGS_REVIEW.md, TELEMETRY_NOTE.md
          (reviewer/operator records; visual_inspection.json is a gate input)
<run>/visualization/index.html links to both condition viewers
<run>/systems/lsd/       prepared/ simulation/ analysis/ figures/ visualization/
<run>/systems/lisuride/  prepared/ simulation/ analysis/ figures/ visualization/
```

Per condition, `analysis/` contains `metrics.json`, `checks.json`, and
`timeseries.csv`, `prepared/` contains `system.pdb`, `system.xml`,
`smirnoff-template-cache.json`, `preparation_audit.json`,
`protonation_table.json`, `ligand_identity.json`, `ligand_hydrogens.xml`,
`minimized.pdb`, and for the ligand residue `<RES>`:
`<RES>_protonated_plus1.sdf`, `<RES>_am1bcc_charges.csv`, and
`<RES>_protonated_plus1.png`. The five figures that the gate requires are
`equilibration_dashboard.png`, `production_dashboard.png`,
`contact_distances.png`, `membrane_metrics.png`, and `final_cross_section.png`;
the gate verifies that all five exist and are non-empty for each condition.

## Visual-inspection record

Phases 4 and 5 finalize their gate only after a reviewer writes
`analysis/visual_inspection.json`; `--figures-only` produces the figures and
metrics first and stops before the gate; a full analysis run without the record
raises `RuntimeError: Mandatory Phase N visual inspection is missing…`. The
record must contain every key listed below, and the gate turns them into
`visual_inspection_pass`.

- Phase 4, one record in `analysis/visual_inspection.json`:
  `hydrophobic_region_overlaps_lipid_tails_pass`, `domains_hydrated_pass`,
  `no_lipid_tail_through_protein_core_pass`, `no_large_vacuum_gap_pass`,
  `leaflets_continuous_pass`, `oligomer_intact_pass`, `membrane_normal_z_pass`.
- Phase 5, `conditions.<condition>` per condition: `binding_pose_present_pass`,
  `membrane_embedded_pass`, `no_obvious_clash_pass`, `bilayer_continuous_pass`,
  `solvent_both_sides_pass`. Accepted records also carry `inspector`,
  `checked_utc`, `scope`, a free-text `observation` per condition,
  `shared_observation`, the `evidence` file list, and
  `human_research_approval: false` for a mechanical tutorial gate.

## `REPORT.md`

Each analysis script generates `REPORT.md` in the run root. See
`10_REPRODUCIBILITY_REPORTING.md` for the sections each phase generates and for
what a human reviewer must add before a phase is accepted.

## Visualization artifacts

`scripts/render_trajectory.py --phase N --profile P [--max-frames M]` writes into
`visualization/`: `trajectory_multimodel.pdb` (the downsampled solute
trajectory), `viewer.html` (3Dmol.js page), and `viewer.vmd` (VMD script). Phase
5 writes the same three files inside each `systems/<condition>/visualization/`
plus the run-level `visualization/index.html`. See `08_VISUALIZATION.md`.

## Progress state

`scripts/labctl.py` is the only supported writer of `state/progress.json`:

```bash
make status                                   # print all phases/profiles
python scripts/labctl.py set <phase> <profile> <STATE>
python scripts/labctl.py complete <phase> <profile>   # PASS_QUICK / PASS_TEACHING
```

`make phaseN-analysis` calls `complete`; for Phase 5 with `PROFILE=teaching` the
Makefile then sets `AWAITING_HUMAN_DECISION` instead of `PASS_TEACHING`.
`state/snapshots/` holds frozen JSON snapshots of accepted pre-production runs.
