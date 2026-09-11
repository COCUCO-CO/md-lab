# Decision record: Periodic positional restraints in Phase 4

- ID: DR-005
- Date (UTC): 2026-07-27
- Status: APPROVED
- Research question: How should the existing positional-restraint schedule be evaluated for a periodically wrapped membrane system?
- Decision owner: Codex execution scientist
- Reviewer: Project owner, through authorization to correct the Phase 4 implementation carefully

## Context

Run `phase04_quick_20260727T043039Z_nogit` failed with a NaN during the first
NVT stage. Force-group decomposition of the preserved `system.xml` and
`system.pdb` showed that CUDA evaluated the Cartesian `CustomExternalForce`
restraint at approximately +3.013 billion kJ/mol. All physical force groups
together were near -0.974 million kJ/mol, and the largest actual covalent bond
was 0.2074 nm.

The OPM-oriented protein has coordinates on both sides of the coordinate
origin. CUDA may represent a particle in a periodically equivalent image while
the stored Cartesian reference remains in the original image. The old
expression `(x-x0)^2+(y-y0)^2+(z-z0)^2` therefore applied box-length
displacements to atoms that had not physically moved.

The same audit also found that the shared helper selected every non-water heavy
atom in a membrane system, including POPC. The Phase 4 protocol specifies
protein-heavy-atom restraints, not lipid restraints.

## Options considered

### Option A

Keep the approved force constants and schedule, but evaluate displacement with
OpenMM `periodicdistance(x,y,z,x0,y0,z0)` and select only standard-protein heavy
atoms when `membrane=True`.

### Option B

Keep the Cartesian expression or lower/remove the restraints. The first choice
reproduces the diagnosed CUDA artifact; the second changes a scientific
protocol parameter merely to avoid a failure.

## Decision

Use Option A. The restraint strength, schedule, temperature, timestep, and all
other physical settings remain unchanged.

## Consequences and sensitivity analysis

The restraint becomes invariant to the periodic image used internally by the
platform. Phase 2 and Phase 3 also use periodic solvent boxes and benefit from
the corrected distance definition without changing their already completed
results. Phase 4 analysis must derive covalent bonds from OpenMM's parsed
topology, not MDTraj's PDB bond inference, because repeated solvent residue
identifiers in this large PDB can create spurious MDTraj display bonds.

## Files/configuration affected

- `src/mdlab/openmm_utils.py`
- `src/mdlab/biomolecular.py`
- `scripts/phase4_analyze.py`
- `tests/test_openmm_utils.py`

## Approval

- Human approval name/date: Project owner, careful-continuation authorization,
  2026-07-27
- Agent implementation commit/run ID: no Git repository; first conforming
  Phase 4 quick run after the preserved NaN run
