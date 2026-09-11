# Command checklist for the agent and human learner

Run commands from the repository root.

## Phase 0

```bash
make bootstrap
make doctor
make test
make status
```

Read `state/doctor.json`. Do not continue unless every mandatory check passes.

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

Inspect membrane edge-on and top-down. Only after `PASS`, repeat with `PROFILE=teaching`.

## Phase 5

Do not run research production from an automatic command. First complete and approve:

```text
state/decisions/DR-005-5HT2A.md
```

Then implement the approved system as a new version-controlled config and scripts derived from validated Phase 3 and Phase 4 components.

## Gate inspection

```bash
cat outputs/phaseNN/<latest-run>/gate.json
cat outputs/phaseNN/<latest-run>/REPORT.md
```

A process exit code of zero is not sufficient. The `gate.json` status must be `PASS`.
