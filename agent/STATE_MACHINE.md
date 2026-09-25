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

## Who writes which state

`state/progress.json` contains the keys `0`…`7`; phases 5-7 also carry a
`research` profile. The only writers are `scripts/labctl.py` and the Phase 5
launchers (which shell out to it):

| Writer | States it writes |
|---|---|
| `scripts/phase5_run.py` | `PREFLIGHT_RUNNING` on start, then `READY` (preflight passed), `SIMULATION_RUNNING`, and on failure `PREFLIGHT_FAILED` or `SIMULATION_FAILED` |
| `scripts/phase5_analyze.py` | `ANALYSIS_RUNNING`, then `GATE_FAILED` (and exit 1) or `ANALYSIS_FAILED` on an analysis error |
| `make phaseN-analysis` via `labctl complete` | `PASS_QUICK`/`PASS_TEACHING`, chosen from the profile |
| `make phase5-analysis PROFILE=teaching` | overrides the above with `AWAITING_HUMAN_DECISION` |
| `labctl set <phase> <profile> <STATE>` | any state; the human/agent escape hatch, e.g. Phase 0 bookkeeping or `research: NOT_STARTED` |

Phases 1-4 have no in-script progress writes: their gate outcome is in the run's
`gate.json`, and the analysis target records it through `labctl complete`.

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
