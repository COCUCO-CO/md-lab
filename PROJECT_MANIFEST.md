# Project manifest

Repository map: every tracked area, what it is for, and who writes it. The
machine-readable run contract lives in `docs/12_RUN_ARTIFACTS.md`; the
documentation index lives in `docs/README.md`.

## Entry documents

- `README.md` — project overview, phase map, entry points, directory contract, scope limits.
- `AGENTS.md` — binding rules for the local LLM agent.
- `agent/START_PROMPT.md` — ready-to-paste initial prompt.
- `agent/STATE_MACHINE.md` — allowed execution states, transitions, gate semantics, recovery.
- `docs/README.md` — documentation index and reading order.
- `CITATION.cff`, `LICENSE` (MIT) — citation and license.

## Environment and orchestration

- `environment.yml` — pinned primary scientific packages (micromamba/conda channel set, one pip package).
- `pyproject.toml` — `md-learning-lab` package metadata (`src/` layout, Python >= 3.12).
- `Makefile` — supported user/agent commands; every run target executes through
  `micromamba run -p .venv/conda`, `PROFILE ?= quick`.
- `scripts/bootstrap.sh` — local micromamba install, environment solve, `pip check`,
  OpenMM installation test, environment exports.
- `scripts/doctor.py` — GPU/OpenMM/package health report into `state/doctor.json`.
- `scripts/labctl.py` — the only writer of `state/progress.json`
  (`status`, `set`, `complete`).

## Simulation implementation

- `scripts/phase1_run.py` / `phase1_analyze.py` — Lennard-Jones argon-like fluid (NVT + NVE, RDF).
- `scripts/phase2_run.py` / `phase2_analyze.py` — ubiquitin in explicit OPC water.
- `scripts/phase3_run.py` / `phase3_analyze.py` — T4 lysozyme L99A + benzene, OpenFF ligand templates.
- `scripts/phase4_run.py` / `phase4_analyze.py` — aquaporin-1 tetramer in a POPC bilayer.
- `scripts/phase5_run.py` / `phase5_analyze.py` — matched 5-HT2A–BRIL LSD/lisuride
  systems, two conditions per run, two-stage gate with a mandatory visual-inspection
  record, progress-state updates.
- `scripts/render_trajectory.py` — HTML (3Dmol.js) and VMD viewers for phases 1-5.
- `src/mdlab/core.py` — provenance, manifests, hashing, download with sidecars,
  config resolution, seeds, hardware/package snapshots, OpenMM platform selection.
- `src/mdlab/biomolecular.py` — force-field/system construction and the staged
  minimization → NVT → staged NPT → (pre-production) → production runner.
- `src/mdlab/openmm_utils.py` — step/interval conversion, periodic positional
  restraints, reporters, state/PDB writing, System serialization.
- `src/mdlab/analysis_utils.py` — frame/time alignment guard for thermodynamic logs.

## Configuration

- `configs/profiles.yaml` — `project_defaults` plus `phase1`…`phase5` blocks with
  `quick`/`teaching` profiles and gate thresholds; Phase 5 also carries the
  conditions, required decisions, and minimum replica count.
- `configs/BNZ_hydrogens.xml` — pinned benzene hydrogen definition used by Phase 3.

## Scientific documentation

- `docs/00_SCIENTIFIC_PRINCIPLES.md` — theory and mental model.
- `docs/01…07_*.md` — Phase 0 to Phase 7 protocols (`07` is requirements only).
- `docs/08_VISUALIZATION.md` — mandatory visual checks and generated viewers.
- `docs/09_VALIDATION_TROUBLESHOOTING.md` — diagnosis playbooks.
- `docs/10_REPRODUCIBILITY_REPORTING.md` — provenance, report structure, archiving.
- `docs/11_COMMAND_CHECKLIST.md` — command sequence per phase, including the
  isolated subprojects.
- `docs/12_RUN_ARTIFACTS.md` — run directory, manifest, gate, and report contract.
- `docs/GLOSSARY.md` — terminology.
- `docs/REFERENCES.md` — official documentation and primary references.
- `docs/templates/DECISION_RECORD.md` — mandatory human-review record template.
- `docs/decisions/DR-001…DR-005` — approved laboratory protocol decisions.

## Tests

- `tests/test_core.py` — profile resolution, step conversion, pinned scientific versions, immutable download reuse.
- `tests/test_openmm_utils.py`, `tests/test_analysis_utils.py` — periodic restraints, frame/time alignment.
- `tests/test_phase1_analysis.py`, `tests/test_phase2_analysis.py` — drift/displacement, SASA selection.
- `tests/test_phase3_chemistry.py` — benzene CCD mapping and pinned hydrogen definition.
- `tests/test_phase4_membrane.py` — minimum-image/periodic-centring maths.
- `tests/test_phase5_5ht2a.py` — Phase 5 protocol resolution, decision-record completeness, ligand protonation chemistry.
- Run them with `make test`, scoped with
  `python -m pytest tests -q` when other Python trees are present (see
  `docs/01_PHASE0_ENVIRONMENT.md`).

## State, outputs, and evidence

- `state/progress.json` — machine-readable phase/profile state.
- `state/doctor.json`, `state/environment-explicit.txt`, `state/environment-solved.yml` — Phase 0 evidence.
- `state/LEARNING_LOG.md` — pedagogical record appended after each passed profile.
- `state/decisions/` — Phase 5 research governance: `DR-005-5HT2A.md` (approved),
  `DR-005-R1-PREPRODUCTION.md` (proposed), `PHASE5_SOURCE_AUDIT.md` (evidence).
- `state/snapshots/` — frozen JSON snapshots of accepted pre-production runs.
- `inputs/` — immutable downloaded sources with `.provenance.json` sidecars (git-ignored content).
- `outputs/` — complete run directories (git-ignored content).
- `artifacts/` — compact exports for sharing (git-ignored content).

## Isolated subprojects and snapshots

- `chemagent/` — chemistry research agent: own `README.md`, `Makefile`,
  `pyproject.toml`, `src/chemagent/`, `tests/`, `configs/`, `docs/`
  (`ARCHITECTURE`, `CORPUS_PLAN`, `BOOKS`, `EVALUATION`, `ROADMAP`, `STATUS`), and
  git-ignored `data/`+`models/`+`runs/` stores. It is tested with
  `chemagent$ make test` and does not share the laboratory's phase state.
- `gui/` — reference snapshot of the separate 5-HT2A campaign GUI; see
  `gui/README.md`.
- `notebooks/` — reserved for explanatory notebooks; scripts remain authoritative.
- `cache/`, `systems/`, `5ht2a_mm/` — campaign working areas. They track no files
  today; `systems/` and `5ht2a_mm/` contain only empty campaign subdirectories
  (`systems/HTR2A_INACTIVE_RIS_NO_G_EXP_POSE_SITENA_C36_2026A_B001/manual/`,
  `5ht2a_mm/decisions/_templates/`), and `cache/` is empty.
- `planes/g4-multi-campaign/` — multi-step implementation plans and progress notes.
- `DONE`, `handback.txt`, `P06_handback.md` — hand-back notes written by the
  separate 5-HT2A campaign workstream (they reference campaign phases P04-P10 and
  its own GUI files), kept at the repository root for continuity. They are not
  laboratory phase records: laboratory evidence lives in `outputs/`, `state/`, and
  the two decision directories.
- `FILE_SHA256SUMS.txt` — SHA-256 manifest over the repository tree
  (`tail -n +3 FILE_SHA256SUMS.txt | sha256sum -c -`). It is a point-in-time
  record from the initial import, so it does not cover files added afterwards;
  regenerate it when a tamper-evident snapshot of the tree is required.
- `5ht2a_md/` — the production 5-HT2A GROMACS/CHARMM-GUI campaign: a nested git
  repository with its own remote, plan, pipeline, GUI, and tests. Listed in
  `.gitignore`; not built, documented, or tested by this repository's targets.
