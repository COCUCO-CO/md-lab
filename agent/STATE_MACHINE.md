# Agent state machine

The authoritative state is `state/progress.json`, managed by `scripts/labctl.py`.

## States

- `NOT_STARTED`
- `PREFLIGHT_RUNNING`
- `PREFLIGHT_FAILED`
- `READY`
- `SIMULATION_RUNNING`
- `SIMULATION_FAILED`
- `ANALYSIS_RUNNING`
- `ANALYSIS_FAILED`
- `GATE_FAILED`
- `PASS_QUICK`
- `PASS_TEACHING`
- `AWAITING_HUMAN_DECISION`
- `APPROVED_FOR_RESEARCH`
- `COMPLETE`

## Transition rules

```text
NOT_STARTED -> PREFLIGHT_RUNNING
PREFLIGHT_RUNNING -> PREFLIGHT_FAILED | READY
READY -> SIMULATION_RUNNING
SIMULATION_RUNNING -> SIMULATION_FAILED | ANALYSIS_RUNNING
ANALYSIS_RUNNING -> ANALYSIS_FAILED | GATE_FAILED | PASS_QUICK | PASS_TEACHING
PASS_QUICK -> READY(teaching)
PASS_TEACHING -> COMPLETE, except Phase 5
Phase 5 PASS_TEACHING -> AWAITING_HUMAN_DECISION
AWAITING_HUMAN_DECISION -> APPROVED_FOR_RESEARCH only with signed decision record
```

A failed state never transitions by editing JSON. Start a new run after a documented correction.

## Run identifiers

Use:

```text
phaseNN_<profile>_<UTC YYYYMMDDTHHMMSSZ>_<git-short-sha-or-nogit>
```

The launcher creates this automatically.

## Gate semantics

- `PASS` means every mandatory numerical and structural criterion passed.
- `WARN` may coexist with `PASS` only for explicitly non-blocking teaching observations.
- `FAIL` blocks later phases.
- Missing data is a failure, not a pass.

## Recovery

A production job interrupted by power loss may resume only if:

- configuration hash matches;
- topology and System XML hashes match;
- checkpoint can be loaded;
- last trajectory frame time is consistent with the log;
- the restart is recorded in `manifest.json`.
