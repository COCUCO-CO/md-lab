# Project manifest

## Entry documents

- `README.md` — project overview and phase map.
- `AGENTS.md` — binding rules for the local LLM agent.
- `agent/START_PROMPT.md` — ready-to-paste initial prompt.
- `agent/STATE_MACHINE.md` — allowed execution states and gates.

## Environment and orchestration

- `environment.yml` — pinned primary scientific packages.
- `Makefile` — supported user/agent commands.
- `scripts/bootstrap.sh` — isolated micromamba installation and environment export.
- `scripts/doctor.py` — GPU/OpenMM/package health report.
- `scripts/labctl.py` — progress-state manager.

## Simulation implementation

- `scripts/phase1_run.py` / `phase1_analyze.py` — Lennard-Jones fluid.
- `scripts/phase2_run.py` / `phase2_analyze.py` — ubiquitin in explicit solvent.
- `scripts/phase3_run.py` / `phase3_analyze.py` — T4 lysozyme–benzene complex.
- `scripts/phase4_run.py` / `phase4_analyze.py` — aquaporin-1 in POPC.
- `scripts/render_trajectory.py` — standalone HTML trajectory viewer.
- `src/mdlab/` — reusable provenance, OpenMM, and staged-simulation helpers.

## Scientific documentation

- `docs/00` through `docs/11` — theory, phase protocols, visualization, troubleshooting, reproducibility, and commands.
- `docs/GLOSSARY.md` — terminology.
- `docs/REFERENCES.md` — official documentation and primary references.
- `docs/templates/DECISION_RECORD.md` — mandatory human-review record.

## State and outputs

- `state/progress.json` — machine-readable progress.
- `state/LEARNING_LOG.md` — pedagogical record after each passed phase.
- `inputs/` — immutable downloaded sources.
- `outputs/` — complete run directories.
- `artifacts/` — compact exports for sharing.
