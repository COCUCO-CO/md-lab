# Phase 5 — Research-grade 5-HT2A project

## Purpose

Transform the validated tutorial pipeline into a hypothesis-driven GPCR simulation. This phase cannot be scientifically reduced to a universal automatic recipe: receptor state, construct, ligand, protonation, missing regions, membrane composition, and replicas are part of the scientific question.

The agent must automate mechanics but must not silently make biological decisions.

## Required research question

Write one falsifiable question before selecting a structure. Examples:

- How does ligand A alter the intracellular TM6–TM3 distance distribution relative to ligand B?
- Which receptor–ligand contacts differ consistently across independent replicas?
- Does a specific protonation microstate change the stability of a known activation microswitch?

Do not use “simulate 5-HT2A and see what happens” as the research question.

## Mandatory decision record

Copy `docs/templates/DECISION_RECORD.md` to:

```text
state/decisions/DR-005-5HT2A.md
```

Record and obtain human approval for every item in `configs/profiles.yaml:phase5.required_decisions`.

## Structure selection protocol

1. Search RCSB and OPM for relevant 5-HT2A structures.
2. Match receptor functional state to the research question.
3. Inspect experimental method, resolution, engineered mutations, fusion proteins, stabilizing antibodies, G proteins, unresolved regions, and ligand identity.
4. Decide whether to retain the full signaling complex or isolate the receptor.
5. Use OPM/PPM orientation or a validated membrane-building workflow.
6. Preserve the original coordinate file and validation report.
7. Create a table of all differences between experimental construct and desired biological construct.

A structure with fewer missing residues is not automatically the correct functional state.

## Receptor preparation checklist

- verify chain and residue numbering against canonical sequence;
- identify engineered mutations and thermostabilizing substitutions;
- identify unresolved N/C termini and intracellular/extracellular loops;
- inspect conserved disulfide bonds;
- inspect sodium/allosteric site components;
- list crystal/cryo-EM waters near ligand and conserved motifs;
- assign histidine states explicitly;
- evaluate acidic/basic residues in buried networks;
- document protonation tool outputs and manual overrides;
- define palmitoylation or other covalent modifications if relevant;
- inspect steric clashes after removing fusion partners.

Loop modeling longer than five residues requires an ensemble or at least sensitivity analysis, not one unquestioned model.

## Ligand preparation checklist

- obtain chemically explicit identity from primary source;
- define stereoisomer, tautomer, and formal charge;
- choose protonation state(s) at the modeled pH;
- verify atom mapping to the experimental pose;
- generate parameters with an explicitly versioned force field;
- inspect assigned charges and unusual parameters;
- retain a 2D depiction and canonical isomeric SMILES in the manifest;
- consider multiple plausible microstates as separate systems.

## Membrane and solvent

The default starting point is a simple POPC/cholesterol or plasma-membrane-inspired composition only if it is justified. A homogeneous POPC system is easier to interpret but less biologically realistic. Record:

- leaflet compositions;
- cholesterol fraction;
- ionic strength;
- pH assumption;
- temperature (often 310 K for human receptor studies, but justify it);
- box size and minimum protein-image separation.

## Equilibration protocol

Use staged restraints rather than immediately releasing a newly built GPCR system:

1. minimization with protein and ligand heavy atoms restrained;
2. short NVT relaxation;
3. membrane NPT with strong protein/ligand restraints;
4. several stages of decreasing backbone/side-chain/ligand restraints;
5. unrestrained pre-production;
6. production only after membrane and receptor sanity gates pass.

Do not copy equilibration durations blindly. Record the criterion used to decide each stage was adequate.

## Replicas

Minimum: three independent production replicas with distinct initial velocities and documented seeds. More may be necessary. Replicas must share the same prepared model and Hamiltonian unless the experiment intentionally varies one factor.

## GPCR observables

Pre-register the primary observables before examining production results. Candidate observables include:

- TM3–TM6 intracellular distance;
- DRY motif interactions;
- NPxxY motif geometry;
- PIF transmission switch;
- ligand–Asp3.32 interaction;
- water-network occupancy;
- sodium-site hydration/coordination;
- helix tilt and kink angles;
- ligand contact fingerprints;
- intracellular cavity volume;
- G-protein interface contacts when present.

Residue numbering must state both sequence numbering and Ballesteros–Weinstein/GPCRdb numbering where available.

## Gate before research production

The human must approve:

- decision record;
- prepared structure visualization;
- protonation table;
- ligand identity report;
- system composition report;
- equilibration plots;
- pre-registered observables;
- replica seeds and planned lengths;
- storage estimate and checkpoint policy.

Only then may `research` production begin.

## Approved local project

`state/decisions/DR-005-5HT2A.md` approves Option A: the matched inactive
5-HT2A–BRIL structures 7WC6/LSD and 7WC7/lisuride. Both ligands use their
chemically explicit CCD SDF graphs and approved `+1` protonation states. Both
systems are aligned to OPM 7WC5 and built in the same POPC/TIP3P environment.

The tutorial profiles are mechanical gates only:

```bash
make phase5 PROFILE=quick
make phase5-analysis PROFILE=quick
make phase5-view PROFILE=quick
```

Analysis is finalized in two steps. First generate the numerical/static
inspection package with:

```bash
python scripts/phase5_analyze.py --profile quick --figures-only
```

Inspect both systems in the static figures, HTML viewer and VMD, then record
`analysis/visual_inspection.json` and rerun the normal analysis target. The
record must contain, for each of `lsd` and `lisuride`, the keys
`binding_pose_present_pass`, `membrane_embedded_pass`, `no_obvious_clash_pass`,
`bilayer_continuous_pass`, and `solvent_both_sides_pass`, plus the inspected
evidence files; see `12_RUN_ARTIFACTS.md`. A passing `quick` gate is mandatory
before using `PROFILE=teaching`.

## Run layout and gate composition

One Phase 5 run builds and simulates both approved conditions side by side under
the same Hamiltonian, membrane, and restraint schedule. Per condition the launcher
creates `systems/<condition>/prepared|simulation|analysis|figures|visualization`,
so `prepared/system.pdb`, `prepared/protonation_table.json`,
`prepared/ligand_identity.json`, the AM1-BCC charge table, and the
production trajectory exist twice, and `analysis/metrics.json` and
`analysis/checks.json` are per condition. The run root keeps `gate.json`,
`REPORT.md`, `analysis/contact_comparison.json` (the pre-registered differential
contact comparison), `analysis/preliminary_metrics.json`, and the reviewer
evidence. The full file contract is in `12_RUN_ARTIFACTS.md`.

Each condition is gated by 24 numerical, structural, chemical, and visual checks
(included here so a reviewer can audit the gate without reading the script):
finite values; approved construct (367 polymer residues, zero retained source
waters, exactly the condition ligand as retained heterogen); loop validation;
ligand chemistry (approved formal charge and AM1-BCC sum of exactly +1); all atoms
parameterized; membrane barostat present; barostat pressure; temperature;
density-driven membrane thickness; area per lipid; leaflet balance; outer-solvent
coverage; bond geometry; prepared inter-component geometry; protein transmembrane
Cα RMSD; ligand aligned RMSD; ligand center-of-mass displacement; thermodynamic
and equilibration row counts; trajectory and checkpoint readability;
unrestrained pre-production; required figures; and the visual-inspection record.

Structure-selection evidence for the approved pair is recorded in
`state/decisions/PHASE5_SOURCE_AUDIT.md` (candidate comparison, construct
features, ligand formulas and protonation atoms, OPM orientation source, and the
SHA-256 of every immutable input).

The `research` profile remains unavailable until the separate pre-production
human gate approves the prepared visualizations, protonation and ligand
reports, system composition, equilibration plots, replica plan, measured
storage/runtime estimate and checkpoint policy.

## Current local gate status

- Accepted quick run: `phase05_quick_20260727T182343Z_nogit`, `PASS`.
- Accepted teaching run: `phase05_teaching_20260727T184752Z_nogit`, `PASS`
  with 24/24 checks per condition.
- Authoritative state: `AWAITING_HUMAN_DECISION`; research is `NOT_STARTED`.
- Proposed research gate:
  `state/decisions/DR-005-R1-PREPRODUCTION.md`.
- Measured budget:
  `outputs/phase05/phase05_teaching_20260727T184752Z_nogit/analysis/research_budget.json`.

The proposed gate recommends a fixed 10 ns unrestrained preproduction for
every research replica because teaching area-per-lipid and P–P thickness still
trend over 5 ns. This would not change the 100 ns research production length,
pre-registered observables, cutoffs or falsification rule.
