# Architecture and scientific boundaries

## System roles

The system is an agent with five independently testable components.

1. **Language orchestrator.** ChemDFM-R-14B interprets the question, chooses
   retrieval collections and tools, and explains results with citations.
2. **Evidence layer.** Separate indexes hold literature text, reactions,
   compounds, assays, quantum calculations, structures and simulation reports.
3. **Scientific tools.** Deterministic or specialist programs perform molecular
   validation, reaction mapping, retrosynthesis search, electronic-structure
   calculations and molecular dynamics.
4. **Verifiers.** A forward reaction model, RDKit checks, unit validation,
   applicability-domain checks and source entailment challenge a proposal.
5. **Governance.** License, provenance, benchmark isolation, hazards and human
   review are gates, not prompt suggestions.

## Why one monolithic fine-tune is rejected

- Literature and databases change faster than adapters can be retrained.
- Quantum/MD data are tensors and trajectories, not useful prose tokens.
- Numerical prediction needs specialist models with held-out scaffold/system
  evaluation and calibrated uncertainty.
- A language model cannot establish clinical efficacy, convergence or reaction
  feasibility by assertion.
- Mixing all domains at equal weight causes negative transfer and obscures data
  provenance.

The first adapter is therefore multi-task but behaviour-focused. If evaluation
shows interference, later adapters may specialize in synthesis, quantum/tools
and biophysical simulation while sharing the same retrieval layer.

## Output contract

Every substantive answer should distinguish:

- observed or published evidence;
- a calculation performed by a named tool and configuration;
- a model prediction with uncertainty and applicability domain;
- a diagnostic hypothesis;
- unresolved uncertainty.

Reaction routes add atom-mapped reaction identifiers, source precedents,
forward-check status, stereochemical checks and hazards. Quantum answers add
software, version, charge, multiplicity, geometry hash, method, basis, units and
convergence criteria. MD answers add topology/system hashes, force field,
ensemble, timestep, cutoffs, constraints, seeds and trajectory interval.

## Storage progression

The pilot uses SQLite FTS5 for transparent lexical retrieval. Production should
move to PostgreSQL with the RDKit cartridge plus a vector index, while keeping
document, reaction, molecule, property and trajectory stores separate. Changing
the index must not change the immutable source manifests.

