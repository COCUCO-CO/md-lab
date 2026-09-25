# Phase 0 — Workstation, environment, and GPU validation

## Learning goals

Understand which parts of the computer perform the calculation, verify that OpenMM sees the RTX 4090 through CUDA, record the exact software environment, and establish a baseline performance/health report.

## Inputs

- Ubuntu/Linux workstation.
- NVIDIA driver visible through `nvidia-smi`.
- Internet access for pip packages.
- This repository in a writable local filesystem with sufficient space.

## Procedure

### Step 0.1 — Inspect, do not modify, the machine

Run:

```bash
nvidia-smi
lscpu
free -h
df -h .
```

Record GPU model, driver version, VRAM, CPU model, RAM, and free disk. A trajectory can consume substantial storage; keep at least 100 GB free before later phases.

### Step 0.2 — Create the isolated environment

```bash
make bootstrap
```

`scripts/bootstrap.sh` installs micromamba into `.tools/` when it is not already
on `PATH`, then creates (or updates) the conda environment at `.venv/conda` from
`environment.yml`, runs `python -m pip check`, runs `python -m
openmm.testInstallation`, and exports `state/environment-explicit.txt` (explicit
package URLs) and `state/environment-solved.yml` (solver-resolved recipe) under
`state/`. Every `make` target runs through
`micromamba run -p <repo>/.venv/conda`, so no activation step is required.

The agent must not install packages globally and must not use `sudo`.

Because conda records the absolute prefix it was created for, moving this
repository directory breaks the generated `bin/*` shebangs (`bad interpreter:
…/old/path/.venv/conda/bin/python3.12`). Re-run `make bootstrap` in the new
location; do not patch the shebangs by hand.

### Step 0.3 — Run the project doctor

```bash
make doctor
```

Inspect:

```text
state/doctor.json
state/environment-explicit.txt
state/environment-solved.yml
```

`scripts/doctor.py` writes `hardware` (logical CPU count, hostname, platform, and
the `nvidia-smi` rows for name, driver version, total memory, and compute
capability), `openmm_platforms` with each platform's relative speed,
`openmm_version`, `openmm_test` (return code plus captured stdout/stderr of
`openmm.testInstallation`), `packages` (installed versions of `openmm`,
`openmmforcefields`, `openff-toolkit`, `pdbfixer`, `MDAnalysis`, `mdtraj`,
`numpy`), and the boolean `checks` map that makes the target pass or fail:

- `checks.nvidia_visible` — `nvidia-smi` produced output;
- `checks.cuda_available` — OpenMM lists a `CUDA` platform;
- `checks.openmm_test_pass` — OpenMM's installation test exited zero;
- `checks.enough_ram_hint` — a placeholder that the human must interpret by
  reading `hardware` and `free -h`; the script cannot measure it.

Compare `packages` against `environment.yml` by eye: `pip check` (run by
bootstrap, not by the doctor) only proves dependency compatibility, not that the
pinned scientific versions were kept. `make doctor` exits non-zero when any
`checks` entry is false.

### Step 0.4 — Run repository tests

```bash
make test
```

This runs `pytest -q` from the repository root. The laboratory suite is
`tests/`; `chemagent/` has its own `make test`, and the ignored `5ht2a_md`
campaign keeps its own tests. If a root `pytest` run collects those trees it will
report import errors for packages the laboratory environment deliberately does not
install, which is not a laboratory failure. Scope the laboratory suite when that
happens:

```bash
.venv/conda/bin/python -m pytest tests -q
```

All laboratory tests must pass before Phase 1.

### Step 0.5 — Record the phase gate

Phase 0 creates no run directory and no `gate.json`; `state/doctor.json` plus the
two environment exports are its evidence, together with the appended Phase 0 entry
in `state/LEARNING_LOG.md`. Record the outcome with the progress manager, which is
the only supported writer of `state/progress.json`:

```bash
python scripts/labctl.py complete 0 quick
python scripts/labctl.py set 0 teaching NOT_STARTED
```

The gate fails if CUDA is absent, the numerical installation test fails, the tests
fail, or the environment cannot be reproduced.

## What the hardware does

- RTX 4090: evaluates the dominant force kernels and integration work.
- CPU: file I/O, preparation, some PME/coordination work, analysis, and feeding the GPU.
- RAM: stores prepared systems and analysis arrays; 128 GB is ample for this curriculum.
- Disk: stores trajectories; output frequency often matters more for storage than atom count alone.

## Expected result

OpenMM should list `CUDA` as an available platform. The exact performance is system-dependent; Phase 2 records ns/day for a biomolecular system.

## Stop conditions

Stop immediately on:

- driver/library mismatch;
- CUDA platform missing;
- OpenMM force disagreement outside tolerance;
- package solver conflict;
- insufficient disk space;
- GPU hardware errors in system logs.
