# Command checklist for the agent and human learner

Run commands from the repository root.

## Phase 0

```bash
make bootstrap
make doctor
make test
make status
```

`make bootstrap` installs micromamba under `.tools/` if it is absent, creates the
environment at `.venv/conda`, runs `pip check` and OpenMM's installation test, and
exports `state/environment-explicit.txt` plus `state/environment-solved.yml`.
`make doctor` writes `state/doctor.json` with `checks.cuda_available`,
`checks.openmm_test_pass`, `checks.nvidia_visible`, `checks.enough_ram_hint`, the
OpenMM platform list, and the package versions; the target exits non-zero if any
check is false. Read `state/doctor.json`. Do not continue unless every mandatory
check passes.

`make test` runs `pytest -q` from the repository root. Keep the repository root
clean of other Python projects: a root `pytest` run also collects the isolated
`chemagent/tests` suite (its own `make test`) and, when the ignored `5ht2a_md`
campaign tree is present in this working directory, its tests too, which import
packages the laboratory environment does not provide. Scope the laboratory suite
explicitly when that happens:

```bash
.venv/conda/bin/python -m pytest tests -q
```

Because the conda environment records its own absolute prefix, moving this
directory makes the generated `bin/*` shebangs point at the old path; re-run
`make bootstrap` after a move.

## Phase 1

```bash
make phase1 PROFILE=quick
make phase1-analysis PROFILE=quick
make phase1-view PROFILE=quick
```

Open the latest `outputs/phase01/.../REPORT.md`, `gate.json`, figures, and `visualization/viewer.html`.

Only after `PASS`:

```bash
make phase1 PROFILE=teaching
make phase1-analysis PROFILE=teaching
make phase1-view PROFILE=teaching
```

## Phase 2

```bash
make phase2 PROFILE=quick
make phase2-analysis PROFILE=quick
make phase2-view PROFILE=quick
```

Inspect `prepared/system.pdb`, `prepared/preparation_audit.json`, thermodynamics, structural plots, and viewer.

Only after `PASS`, repeat with `PROFILE=teaching`.

## Phase 3

```bash
make phase3 PROFILE=quick
make phase3-analysis PROFILE=quick
make phase3-view PROFILE=quick
```

Read the ligand chemical identity audit before interpreting the trajectory. Only after `PASS`, repeat with `PROFILE=teaching`.

## Phase 4

```bash
make phase4 PROFILE=quick
make phase4-analysis PROFILE=quick
make phase4-view PROFILE=quick
```

Phase 4 analysis is a two-stage gate. Generate the metrics and static figures
first, inspect the membrane edge-on and top-down, record
`analysis/visual_inspection.json`, then run the analysis target again to
finalize:

```bash
.venv/conda/bin/python scripts/phase4_analyze.py --profile quick --figures-only
```

Only after `PASS`, repeat with `PROFILE=teaching`.

## Phase 5

The approved design already exists in
`state/decisions/DR-005-5HT2A.md` and is implemented by
`scripts/phase5_run.py`/`scripts/phase5_analyze.py` for the two matched
conditions (`lsd`, `lisuride`). Run the mechanical tutorial gates:

```bash
make phase5 PROFILE=quick
make phase5-analysis PROFILE=quick
make phase5-view PROFILE=quick
```

Phase 5 analysis is also two-stage: generate and inspect first, then finalize.

```bash
.venv/conda/bin/python scripts/phase5_analyze.py --profile quick --figures-only
# inspect both systems, then write analysis/visual_inspection.json
make phase5-analysis PROFILE=quick
```

Only after the quick gate is `PASS` repeat with `PROFILE=teaching`. A passing
teaching gate leaves Phase 5 in `AWAITING_HUMAN_DECISION` (the Makefile sets it),
never `PASS_TEACHING`.

Research production is deliberately not a command. It requires the separate
pre-production human gate:

```text
state/decisions/DR-005-R1-PREPRODUCTION.md   (status: PROPOSED)
```

## Phases 6 and 7

No targets exist. Their requirements are in
`docs/07_PHASE6_7_REPLICAS_ADVANCED.md`; they begin only after the Phase 5
research replicas (phase 6) and a validated specific sampling problem (phase 7).

## Chemistry research agent subproject

Run from `chemagent/`, with its own environment for training work:

```bash
cd chemagent
make validate
make audit
make test
make preflight
make build-example-index
make search-example
```

See `chemagent/README.md`.

## 5-HT2A campaign GUI

`gui/` in this repository is a reference snapshot; the runnable GUI lives in the
separate `5ht2a_md` repository. Start it from that repository root, as recorded in
`gui/README.md`.

## Gate inspection

```bash
cat outputs/phaseNN/<latest-run>/gate.json
cat outputs/phaseNN/<latest-run>/REPORT.md
```

Phase 5 stores its gate per condition, so read the whole file:

```bash
.venv/conda/bin/python -c "import json,sys; print(json.dumps(json.load(open(sys.argv[1])), indent=2))" outputs/phase05/<latest-run>/gate.json
```

A process exit code of zero is not sufficient. The `gate.json` status must be `PASS`.
