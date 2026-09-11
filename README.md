# MD Learning Lab

A staged, reproducible, GPU-accelerated molecular-dynamics curriculum and project scaffold for a Linux workstation with an NVIDIA RTX 4090, Intel i9-13900K, and 128 GB RAM.

The repository also contains an isolated [chemistry research agent](chemagent/README.md) subproject for provenance-gated chemical corpora, retrieval, scientific tools, and two-GPU QLoRA. It does not alter this laboratory's phase state or simulation parameters.

This repository is designed to be operated by a local coding agent/LLM under human supervision. It is not a collection of isolated commands: it is a stateful scientific workflow with explicit inputs, outputs, validation gates, logs, figures, and decision records.

## Read this first

1. Give the agent the entire project directory.
2. Tell it to read `AGENTS.md` completely before executing anything.
3. The agent must run phases in numerical order and must not bypass a failed gate.
4. Start with the **quick** profile. Only after the quick gate passes should the agent run the **teaching** profile.
5. Short tutorial trajectories validate software and teach concepts; they do **not** establish biological conclusions.

## Curriculum map

| Phase | System | Main concepts | Default gate |
|---|---|---|---|
| 0 | Workstation and software | CUDA, OpenMM, reproducibility, benchmarking | GPU and numerical validation pass |
| 1 | Lennard-Jones argon-like fluid | forces, integration, ensembles, PBC, thermostat, RDF | stable NVT and acceptable NVE drift |
| 2 | Ubiquitin in explicit water | force fields, solvation, minimization, NVT/NPT, RMSD/RMSF | no NaN, stable thermodynamics, sane structure |
| 3 | T4 lysozyme L99A + benzene | ligand identity, parameterization, contacts, ligand stability | chemical identity audit and stable complex |
| 4 | Aquaporin-1 in POPC | orientation, bilayers, membrane barostat, thickness/APL | bilayer integrity and stable protein |
| 5 | 5-HT2A research project | GPCR-specific preparation, protonation, ligand states, replicas | signed scientific decision record |
| 6 | Replicas and statistics | seeds, convergence, uncertainty, ensemble comparison | replicate agreement/uncertainty reported |
| 7 | Advanced sampling and ML | TICA/MSM, enhanced sampling, graph/latent models | method-specific validation only |

## One-command entry points

```bash
make help
make bootstrap
make doctor
make phase1 PROFILE=quick
make phase1-analysis PROFILE=quick
make phase1-view PROFILE=quick
```

The same naming pattern is used for later phases. Run `make help` for the exact targets.

## Profiles

- `quick`: pipeline validation, deliberately short; usually minutes.
- `teaching`: long enough to inspect meaningful behavior; usually tens of minutes to hours.
- `research`: a template for serious work, often multiple long replicas. It is intentionally not launched automatically.

All numerical settings are in `configs/profiles.yaml`. Every run copies its resolved configuration to the output directory and records hashes, package versions, hardware, git status, command line, random seed, and wall-clock metrics.

## Required reading order

1. `AGENTS.md`
2. `agent/STATE_MACHINE.md`
3. `docs/00_SCIENTIFIC_PRINCIPLES.md`
4. The document for the current phase
5. `docs/08_VISUALIZATION.md`
6. `docs/09_VALIDATION_TROUBLESHOOTING.md`
7. `docs/10_REPRODUCIBILITY_REPORTING.md`

## Directory contract

```text
inputs/       immutable downloaded or researcher-provided inputs
outputs/      generated trajectories, states, logs, reports, and figures
artifacts/    compact exports intended for sharing
configs/      version-controlled parameters
src/mdlab/    reusable Python package
scripts/      executable phase entry points
state/        agent progress and machine-readable gates
notebooks/    optional explanatory notebooks; scripts remain authoritative
docs/         scientific and operational documentation
```

Never edit a file under `inputs/` in place. Derived structures go under the relevant `outputs/<phase>/<run_id>/prepared/` directory.

## Scientific scope and limits

This project teaches and validates classical all-atom molecular dynamics. A successful run means that the numerical workflow behaved as specified. It does not prove that a force field is exact, that a trajectory is converged, or that a biological mechanism has been established. Research claims require independent replicas, uncertainty estimates, sensitivity analysis, and comparison with experiment or prior validated calculations.

## Primary software choices

- OpenMM 8.5.2 for simulation.
- OpenMM Force Fields 0.16.0 for explicit small-molecule template generation.
- OpenFF Toolkit 0.18.1 with the explicitly named `openff-2.2.1` small-molecule force field in Phase 3.
- MDAnalysis and MDTraj for analysis.
- py3Dmol for standalone interactive HTML views.
- Create envirnonments with conda but always install packages with pip, never install anything with conda or conda forge.
- Always check if the system CUDA works for the needed packages and try to use that, do not install another CUDA version in the system or break anything working, you can install packages and CUDA versions only in the conda mdlab environment

The exact solved environment on the target workstation is exported after bootstrap. If the solver cannot satisfy the pinned environment, the agent must stop and report the conflict rather than silently changing scientific dependencies.

## Completion criterion

The project is complete only when each executed phase contains:

- `manifest.json`
- resolved configuration
- immutable input hashes
- simulation logs
- checkpoint/state files
- analysis tables
- figures
- interactive HTML visualization
- `REPORT.md`
- `gate.json` with `PASS` or `FAIL`

The agent must never mark a phase complete based only on the process exiting with code zero.
