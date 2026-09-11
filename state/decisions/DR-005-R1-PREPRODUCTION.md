# Decision record: Phase 5 research pre-production gate

- ID: DR-005-R1
- Date (UTC): 2026-07-27
- Status: PROPOSED
- Research question: Do the deposited differential LSD/lisuride contacts persist across three matched inactive 5-HT2A–BRIL ICL2-conformer blocks?
- Decision owner: local execution agent
- Reviewer: Tomas

## Context

The accepted teaching run
`outputs/phase05/phase05_teaching_20260727T184752Z_nogit` passed 24/24
mechanical checks for each ligand. This satisfies the tutorial gate but does
not authorize research production.

Both teaching trajectories show a gradual decrease in area per lipid and
increase in P–P thickness during the 5 ns production window. All values remain
inside the declared physical sanity ranges, but the trends make a convergence
claim inappropriate and motivate an explicit human choice about research
equilibration.

The original 20 GB / 2–4 day estimate in DR-005 was preliminary. Measured
trajectory size and RTX 4090 performance replace it below.

## Evidence reviewed

- Teaching report and gate:
  `outputs/phase05/phase05_teaching_20260727T184752Z_nogit/REPORT.md` and
  `gate.json`.
- Prepared-system viewers:
  `visualization/index.html`, plus the per-condition HTML and VMD scripts.
- Visual evidence:
  `analysis/visual_inspection_montage.png`,
  `analysis/equilibration_montage.png`,
  `analysis/lsd_html_viewer.png`, and
  `analysis/lisuride_html_viewer.png`.
- Protonation tables:
  `systems/lsd/prepared/protonation_table.json` and
  `systems/lisuride/prepared/protonation_table.json`.
- Ligand identity and charge reports:
  each condition's `prepared/ligand_identity.json`,
  protonated SDF, depiction, and AM1-BCC charge CSV.
- System composition:
  each condition's `prepared/preparation_audit.json`.
- Equilibration data:
  `equil_nvt.csv`, four `equil_npt_*.csv` files,
  `equil_unrestrained.csv`, and `figures/equilibration_dashboard.png` for each
  condition.
- Runtime/storage calculation:
  `analysis/research_budget.json`.
- Warning and visual-tool audits:
  `analysis/WARNINGS_REVIEW.md`,
  `analysis/TELEMETRY_NOTE.md`, and
  `analysis/viewer_verification.json`.

## Fixed research design

The following elements remain as approved in DR-005 and are not reopened by
this gate:

- matched inactive 7WC6/LSD and 7WC7/lisuride engineered 5-HT2A–BRIL systems;
- ff19SB/Lipid21/TIP3P/OpenFF 2.2.1 AM1-BCC Hamiltonian;
- approved ligand and receptor protonation states;
- three paired ICL2-conformer blocks;
- 100 ns production per replica, three replicas per ligand, 600 ns aggregate;
- 50 ps trajectory stride and 1 ns checkpoint stride;
- pre-registered 0.45 nm ECL2/deep-contact definitions and falsification rule;
- research dynamics seeds LSD `20262210`–`20262212` and lisuride
  `20262220`–`20262222`;
- no mechanistic, activation, signaling-bias or psychedelic-action claim.

The proposed common loop seeds are `20262310`, `20262311`, and `20262312`.
For block `i`, the same loop seed and conformer index must be used for LSD and
lisuride. Conformers are accepted only by the existing structural gates and
never selected from ligand-contact results.

## Options considered

### Plan 1 — preserve the teaching equilibration length

For every independent research replica, run 100 ps NVT, four 500 ps restrained
NPT stages, 500 ps unrestrained preproduction, then 100 ns production.

Advantages:

- exactly preserves the already approved teaching timing;
- estimated serial runtime is 5.18 days on the measured RTX 4090.

Limitation:

- research production would begin after 2.6 ns total dynamics even though the
  teaching membrane observables continue to trend over the next 5 ns.

### Plan 2 — fixed 10 ns unrestrained preproduction (recommended)

For every independent research replica, run the unchanged 100 ps NVT and four
500 ps restrained NPT stages, then 10 ns unrestrained preproduction before
starting a separate 100 ns production trajectory.

Advantages:

- gives each independently prepared membrane/receptor system an additional
  fixed relaxation interval before any primary contact frame is counted;
- applies prospectively and identically to all six replicas;
- leaves the 100 ns production length, observables, cutoffs and falsification
  rule unchanged;
- adds negligible trajectory storage because preproduction writes state logs
  and final state files, not the production DCD.

Limitations:

- increases estimated serial runtime to 5.66 days;
- still does not guarantee convergence; convergence diagnostics remain
  mandatory and a non-converged result must be reported as inconclusive.

## Proposed decision

Approve Plan 2. Reserve six uninterrupted GPU-days and 40 GB of disk. Implement
the research profile only after approval, then perform a configuration
preflight and structural gate for every conformer/condition before any 100 ns
production segment.

Measured basis:

- LSD: 119.178 ns/day and 2,570,229 DCD bytes/frame.
- Lisuride: 118.580 ns/day and 2,542,509 DCD bytes/frame.
- Six planned DCD files: approximately 30.676 GB.
- Estimated total including duplicated systems, final states, checkpoints,
  logs and analysis: approximately 34.389 GB.
- Required reservation: 40 GB; free disk at calculation: 146 GB.

## Checkpoint and recovery policy

- Write one overwritten binary checkpoint per replica every 1 ns.
- A power interruption loses at most approximately 12.2 minutes of GPU work at
  the measured speed.
- Resume only when resolved configuration, topology and System XML hashes
  match; the checkpoint loads with finite energy/positions; and the final DCD
  time agrees with the state log.
- Append every restart to the run manifest. Never overwrite a failed or
  configuration-mismatched run.
- Run replicas sequentially on the single RTX 4090; do not share the GPU among
  simultaneous production jobs.

## Consequences and sensitivity analysis

- The three loop conformers are paired sensitivity blocks, not three
  exchangeable coordinate replicas.
- Primary results must be reported per block and pooled. A direction that
  reverses in any block is inconclusive under DR-005.
- Teaching contact occupancies are excluded from research statistics.
- Area/lipid, thickness, TM RMSD, ligand RMSD/COM, finite energies, solvent
  coverage and bond geometry remain mechanical controls.
- Any failed replica gate stops the sequence; thresholds and cutoffs are not
  adjusted to rescue the hypothesis.

## Files/configuration affected after approval

- `configs/profiles.yaml` Phase 5 research profile;
- `scripts/phase5_run.py` replica/conformer orchestration and safe restart;
- `scripts/phase5_analyze.py` replica-level and blocked aggregate analysis;
- `scripts/render_trajectory.py` research viewer selection;
- `Makefile` Phase 5 research targets;
- `tests/test_phase5_5ht2a.py`;
- generated research runs under `outputs/phase05/`.

Original files under `inputs/phase05/` remain immutable.

## Approval

- Human approval name/date: pending
- Approval statement: pending; use `apruebo DR-005-R1 Plan 2` or explicitly
  select Plan 1 instead.
- Agent implementation commit/run ID: pending; repository has no Git metadata.
