# Corpus plan

## Domain coverage

The corpus catalogue tracks: organic synthesis and mechanisms; medicinal
chemistry and chemical biology; biochemistry; thermodynamics and kinetics;
statistical mechanics; quantum chemistry and electronic structure; molecular
dynamics and enhanced sampling; spectroscopy and analytical chemistry;
inorganic, organometallic and coordination chemistry; catalysis and
electrochemistry; solid-state and materials chemistry; polymers and surfaces;
supramolecular and photochemistry; safety, metrology and scientific computing.

“All current chemistry” is a retrieval objective, not a fine-tuning claim.

## Data lanes

### Reactions

Use versioned USPTO-Lowe, ORD and Rhea records for training. Preserve incomplete
reaction flags rather than deleting every unbalanced patent record. Retain ORD
failed outcomes. Reserve CHORISO, PaRoutes and USPTO-50K for evaluation and
deduplicate their products/reaction hashes against all training inputs.

### Literature

Ingest only article-level approved licenses. Store JATS sections separately and
keep DOI/PMCID, section, paragraph and license. Crossref metadata does not grant
rights to publisher abstracts. Retrieval chunks must never lose citations.

### Medicinal chemistry

Keep assay values structured with units, relation operators, target confidence,
assay type and source. Do not flatten `>10000 nM` into `10000`. Never interpret
an in-vitro activity value as human efficacy.

### Quantum chemistry and materials

SPICE and OC25 are approved starting points. Geometries, forces, energies,
charges, theory levels and periodic cells stay in native structured formats.
Generate LLM examples only for tool selection, input explanation, result
interpretation, unit checking and provenance. QCArchive, Materials Project and
other collections remain disabled until each exact dataset's terms are audited.

### Molecular dynamics

Use curated methods documentation and machine-readable reports. Do not tokenize
trajectories. Simulation questions should invoke analysis tools and retrieve
the exact run manifest. Tutorial trajectories cannot support mechanistic or
convergence claims.

## Proposed full SFT mix after the pilot

| Records | Capability |
|---:|---|
| 100,000 | SMolInstruct train tasks after decontamination |
| 100,000 | reaction outcome prediction |
| 100,000 | single-step retrosynthesis |
| 60,000 | conditions, reagent roles and procedure structuring |
| 40,000 | structures, nomenclature and functional groups |
| 40,000 | grounded drug/target/ADMET tool use |
| 25,000 | quantum chemistry and materials tool use |
| 15,000 | MD/statistical-mechanics tool use and interpretation |
| 40,000 | cited literature questions |
| 20,000 | uncertainty, safety and abstention |

This is a target allocation, not permission to synthesize examples. Every row
must pass the registry and record gates. Start with a representative 25k-50k
pilot and scale only after held-out improvement.

## Splitting and contamination

Production splits are hierarchical:

1. keep benchmark sources entirely outside training;
2. reserve post-cutoff patents/articles for temporal testing;
3. group patent applications and grants by family;
4. group all records from a DOI/document;
5. group medicinal-chemistry target series and close scaffolds;
6. group quantum conformers by parent molecule/system;
7. group MD frames by trajectory and prepared system.

Random row splits are forbidden for final evaluation.

