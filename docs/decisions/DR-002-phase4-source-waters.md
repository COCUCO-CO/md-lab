# Decision record: Phase 4 source waters in the AQP1 channels

- ID: DR-002
- Date (UTC): 2026-07-27
- Status: APPROVED
- Research question: Should the waters present in the OPM-oriented 1J4N structure be retained when building the explicit POPC membrane system?
- Decision owner: Project owner
- Reviewer: Codex execution scientist

## Context

The official OPM-oriented 1J4N biological assembly contains four AQP1
subunits, 371 `HOH` residues, 12 detergent (`BNG`) residues, and 2418 dummy
membrane-marker (`DUM`) residues. The preparation protocol already specifies
removing `BNG` and `DUM`.

Water cannot be treated as a bulk heterogen in this structure. Using OPM's
31.8 Å hydrophobic thickness, 219 source waters lie between the membrane
boundaries at z = -1.59 and +1.59 nm. Of these, 148 are within 0.35 nm of a
protein atom. Visual inspection also shows waters inside the four channel
regions. Retaining or removing them therefore changes the initially hydrated
state of the pores and requires human approval under the project governance
rules.

## Options considered

### Option A — retain all 371 source waters (recommended)

Preserve every source `HOH`, remove only `BNG` and `DUM`, and then build the
POPC membrane and bulk solvent around the retained structure. This avoids an
arbitrary rule for deciding which observed waters are important and reduces
the risk of starting an aquaporin pore artificially dry.

The prepared membrane must still pass explicit checks for water/lipid
overlaps, leaflet packing, unintended lipid-sized holes, and pore hydration.
A failed packing check stops the phase rather than causing automatic water
deletion.

### Option B — remove all 371 source waters and resolvate

Delete every source `HOH` before membrane construction and allow the membrane
builder to add bulk solvent. This gives a uniformly rebuilt solvent
environment but can leave narrow pores incompletely hydrated and discards
resolved channel waters.

## Decision

Use Option A. Retain all 371 source `HOH` residues, remove `BNG` and `DUM`,
and construct the POPC membrane and new bulk solvent around the retained
waters. Preserve the source-water oxygen indices in the preparation audit so
their membrane-core and operational pore occupancy can be reported separately
from newly added water.

## Consequences and sensitivity analysis

This tutorial trajectory cannot establish a biological water-conduction
mechanism. If Option A is selected, analysis will report retained-water
identity and pore occupancy separately from bulk water. If Option B is
selected, the report will state that pore hydration arose only from the
rebuilt solvent configuration. In either case, any membrane-packing defect,
impossible clash, or vacuum gap fails the quick gate.

## Files/configuration affected

- `docs/05_PHASE4_MEMBRANE.md`
- `configs/profiles.yaml`
- `scripts/phase4_run.py`
- `scripts/phase4_analyze.py`
- `outputs/phase04/<run_id>/prepared/preparation_audit.json`

## Approval

- Human approval name/date: Project owner, explicit selection of Option A in
  chat, 2026-07-27
- Agent implementation commit/run ID:
