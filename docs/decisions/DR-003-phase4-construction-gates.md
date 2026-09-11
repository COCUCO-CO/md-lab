# Decision record: Phase 4 construction sanity gates

- ID: DR-003
- Date (UTC): 2026-07-27
- Status: APPROVED
- Research question: Which broad numerical checks should distinguish an obviously broken membrane build from a usable tutorial starting point?
- Decision owner: Codex execution scientist
- Reviewer: Project owner, through authorization to continue Phase 4 carefully

## Context

The Phase 4 specification requires detection of impossible clashes, broken
covalent geometry, leaflet discontinuity, oligomer disassembly, and persistent
vacuum gaps, but the resolved configuration did not quantify those checks.
These are pipeline sanity gates, not claims that a tutorial membrane is
equilibrated.

## Options considered

### Option A

Use deliberately broad failure thresholds: no inter-component heavy-atom
distance below 0.10 nm in the prepared build; no covalent bond above 0.25 nm;
upper/lower POPC counts differing by more than one; no change above 1.0 nm in
any inter-subunit C-alpha centroid distance; and at least 10 water oxygens in
each outer solvent slab in every saved frame.

These values detect gross construction failures while leaving ordinary
membrane relaxation well inside the accepted range.

### Option B

Leave the requirements qualitative. This would make the quick gate depend on
an undocumented visual judgment and would not be reproducible.

## Decision

Use Option A together with the existing broad POPC area-per-lipid, bilayer
thickness, temperature, and protein RMSD ranges. A separate signed visual
inspection record remains mandatory; numerical proxies do not replace it.

## Consequences and sensitivity analysis

Passing these checks only supports that the system is mechanically readable
and suitable for the tutorial. It does not establish membrane equilibration,
water permeability, or a biological transport mechanism. A failure is
diagnosed from the preserved run and is never repaired by relaxing a threshold
solely to obtain a pass.

## Files/configuration affected

- `configs/profiles.yaml`: Phase 4 construction gate keys
- `docs/05_PHASE4_MEMBRANE.md`
- `scripts/phase4_run.py`
- `scripts/phase4_analyze.py`

## Approval

- Human approval name/date: Project owner, continuation authorization in chat,
  2026-07-27
- Agent implementation commit/run ID: no Git repository; identified by the
  first conforming Phase 4 quick manifest
