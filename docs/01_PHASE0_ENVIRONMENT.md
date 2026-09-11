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

The bootstrap script installs micromamba locally if needed, solves `environment.yml`, runs `pip check`, executes OpenMM's installation test, and exports both explicit and human-readable solved environments under `state/`.

The agent must not install packages globally and must not use `sudo`.

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

Mandatory checks:

- `nvidia_visible = true`;
- `cuda_available = true`;
- OpenMM installation test return code is zero;
- package versions match the intended major packages;
- no `pip check` conflicts.

### Step 0.4 — Run repository tests

```bash
make test
```

All tests must pass before Phase 1.

### Step 0.5 — Record the phase gate

Create `outputs/phase00/.../REPORT.md` or use the doctor report as the source. The gate fails if CUDA is absent, the numerical installation test fails, or the environment cannot be reproduced.

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
