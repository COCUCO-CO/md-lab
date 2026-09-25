# Documentation index

This is the map of the laboratory documentation. Start with `../README.md`
(project overview) and `../AGENTS.md` (binding agent rules), then use this page
to choose the document for the task at hand.

## Reading order

| Order | Document | Read it for |
|---|---|---|
| 1 | `../AGENTS.md` | mandatory agent behavior, allowed automatic repairs, review points |
| 2 | `../agent/STATE_MACHINE.md` | legal run states, transitions, gate semantics, recovery |
| 3 | `00_SCIENTIFIC_PRINCIPLES.md` | the physical and statistical mental model |
| 4 | `01_PHASE0_ENVIRONMENT.md` | workstation, environment, GPU validation |
| 5 | the phase document (`02`…`07`) | protocol, gates, interpretation limits |
| 6 | `08_VISUALIZATION.md` | mandatory visual checks and the viewer artifacts |
| 7 | `12_RUN_ARTIFACTS.md` | run directory, `manifest.json`, `gate.json` contract |
| 8 | `09_VALIDATION_TROUBLESHOOTING.md` | diagnosis order for failures and warnings |
| 9 | `10_REPRODUCIBILITY_REPORTING.md` | provenance, reporting language, archiving |
| 10 | `11_COMMAND_CHECKLIST.md` | copy-paste command sequence per phase |
| — | `GLOSSARY.md`, `REFERENCES.md` | terminology and primary sources |

## Documents by need

| Need | Document |
|---|---|
| Understand why a metric is not proof | `00_SCIENTIFIC_PRINCIPLES.md` §8-9 |
| Units and conversions | `00_SCIENTIFIC_PRINCIPLES.md` §10 |
| Create/repair the conda environment | `01_PHASE0_ENVIRONMENT.md` |
| Lennard-Jones fluid protocol | `02_PHASE1_LJ_FLUID.md` |
| Soluble protein protocol | `03_PHASE2_PROTEIN_WATER.md` |
| Protein–ligand protocol | `04_PHASE3_PROTEIN_LIGAND.md` |
| Membrane protocol | `05_PHASE4_MEMBRANE.md` |
| GPCR research project | `06_PHASE5_5HT2A_RESEARCH.md` |
| Replicas, statistics, enhanced sampling, ML | `07_PHASE6_7_REPLICAS_ADVANCED.md` |
| Open a trajectory, write a VMD script | `08_VISUALIZATION.md` |
| A gate failed | `09_VALIDATION_TROUBLESHOOTING.md` |
| Write a report, prepare an archive | `10_REPRODUCIBILITY_REPORTING.md` |
| Know exactly which files a run must contain | `12_RUN_ARTIFACTS.md` |
| Record a human-approved scientific choice | `templates/DECISION_RECORD.md` |

## Implementation status of the documentation

- Phases 0 to 5 are implemented and gated by `scripts/` and the root `Makefile`
  (`phaseN`, `phaseN-analysis`, `phaseN-view`, N = 1..5).
- Phases 6 and 7 are requirements, not code: see
  `07_PHASE6_7_REPLICAS_ADVANCED.md`. No `phase6`/`phase7` target exists.
- Phase 5 `research` production is intentionally unimplemented until the
  human gate in `state/decisions/DR-005-R1-PREPRODUCTION.md` is approved.
- `../gui/` is a reference snapshot of the 5-HT2A campaign GUI; the GUI code and
  its tests live in the separate `5ht2a_md` repository. See `../gui/README.md`.
- `../chemagent/` is an isolated subproject with its own README, Makefile,
  configuration, tests, and documentation set.

## Decision-record namespaces

Decision records are stored in two places and the numbering is independent, so
always cite the full path when referring to a record:

| Namespace | Contents |
|---|---|
| `docs/decisions/` | approved laboratory protocol decisions: `DR-001` Phase 3 covalent-geometry gate, `DR-002` Phase 4 source waters, `DR-003` Phase 4 construction gates, `DR-004` Phase 4 preparation platform, `DR-005` periodic positional restraints |
| `state/decisions/` | Phase 5 research governance: `DR-005-5HT2A.md` (approved research design), `DR-005-R1-PREPRODUCTION.md` (proposed pre-production gate), `PHASE5_SOURCE_AUDIT.md` (structure-selection evidence) |

Note the collision: `docs/decisions/DR-005-periodic-protein-restraints.md` and
`state/decisions/DR-005-5HT2A.md` are different records that both use the ID
`DR-005`. New records must extend the numbering of their own directory
(`docs/decisions/DR-006-…` and `state/decisions/DR-006-…`), never reuse an
existing ID, and be created from `templates/DECISION_RECORD.md`.
