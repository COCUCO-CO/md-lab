# Decision record: Phase 3 covalent-geometry sanity gate

- ID: DR-001
- Date (UTC): 2026-07-26
- Status: APPROVED
- Research question: Which broad tutorial threshold should Phase 3 use to detect obviously broken covalent geometry?
- Decision owner: Codex execution scientist
- Reviewer: Project owner, through authorization to make the necessary specification changes

## Context

The Phase 3 protocol already requires protein geometry to remain sane, but the
resolved configuration did not assign a quantitative gate. A numeric criterion
is needed so that this requirement cannot be passed by visual judgment alone.
This is a broad pipeline-failure check, not a structural-quality claim.

## Options considered

### Option A

Reuse the 0.25 nm maximum covalent-bond threshold already established for
Phase 2. This keeps the tutorial gates consistent and catches clearly broken
bond geometry while leaving ordinary constrained and unconstrained bond
fluctuations well below the limit.

### Option B

Leave Phase 3 without a numeric geometry gate. This avoids adding a configured
value but does not satisfy the protocol's required geometry check
reproducibly.

## Decision

Use `0.25 nm` as the maximum covalent-bond sanity threshold in Phase 3, exactly
matching Phase 2.

## Consequences and sensitivity analysis

Passing this threshold means only that no covalent bond is grossly elongated.
It does not validate local stereochemistry, ligand pose, or force-field
accuracy. Any failure stops the phase for structure inspection; the threshold
must not be relaxed merely to obtain a pass.

## Files/configuration affected

- `configs/profiles.yaml`: `phase3.gates.max_unphysical_bond_nm`
- `docs/04_PHASE3_PROTEIN_LIGAND.md`
- `scripts/phase3_analyze.py`

## Approval

- Human approval name/date: Project owner, task authorization in chat,
  2026-07-26
- Agent implementation commit/run ID: no Git repository; first conforming
  Phase 3 quick run will be identified by its manifest.
