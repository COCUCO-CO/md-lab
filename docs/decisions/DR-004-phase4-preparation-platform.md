# Decision record: Phase 4 membrane-builder platform

- ID: DR-004
- Date (UTC): 2026-07-27
- Status: APPROVED
- Research question: Which OpenMM platform should execute the deterministic internal `addMembrane()` relaxation?
- Decision owner: Codex execution scientist
- Reviewer: Project owner, through authorization to continue Phase 4 carefully

## Context

Run `phase04_quick_20260727T041240Z_nogit` spent more than 15 minutes in the
scalar Reference-platform membrane relaxation while continuously using one CPU
core. It produced no prepared system and was interrupted in a controlled
fashion. No molecular error or traceback occurred.

The membrane builder accepts an explicit platform but not context property
arguments. Its internal Langevin integrator also defaults to an automatically
chosen random seed unless it is wrapped by the project script.

## Options considered

### Option A

Use the CPU platform with 8 fixed threads, deterministic forces enabled, and
the resolved Phase 4 seed explicitly assigned to the builder's internal
Langevin integrator. Record all three values in the preparation audit.

### Option B

Continue using the scalar Reference platform. It is deterministic but its
observed preparation time is impractical for both quick and teaching runs.

## Decision

Use Option A. This changes only the computational backend of the internal
membrane-patch relaxation. It does not change coordinates selected for input,
composition, force fields, temperature, timestep, restraints, simulation
platform, or validation thresholds.

## Consequences and sensitivity analysis

Preparation is reproducible for the fixed CPU thread count, deterministic
force mode, and seed. The production simulation remains on CUDA mixed
precision as specified. The interrupted Reference run is preserved with its
manifest and failure diagnosis.

## Files/configuration affected

- `configs/profiles.yaml`: `phase4.preparation_platform`,
  `phase4.preparation_cpu_threads`, and
  `phase4.preparation_deterministic_forces`
- `scripts/phase4_run.py`

## Approval

- Human approval name/date: Project owner, careful-continuation authorization,
  2026-07-27
- Agent implementation commit/run ID: no Git repository; first conforming
  Phase 4 quick run after the preserved interrupted attempt
