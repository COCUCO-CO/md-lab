# Primary references and official documentation

Accessed 2026-07-10; the added Phase 5 entries and data-endpoint links were
re-verified on 2026-09-25, and every structure citation below was copied from the
RCSB entry record (journal, volume, pages, DOI) and cross-checked in PubMed. When
citing work built on this scaffold, cite the software, force fields, and structure
databases below (see `../CITATION.cff`).

## OpenMM

- OpenMM User's Manual and Theory Guide: https://docs.openmm.org/latest/userguide/
- Getting Started and installation test: https://docs.openmm.org/latest/userguide/application/01_getting_started.html
- Running simulations and bundled force fields: https://docs.openmm.org/latest/userguide/application/02_running_sims.html
- Model building, solvation, and membranes: https://docs.openmm.org/latest/userguide/application/03_model_building_editing.html
- Modeller API (`addSolvent`, `addHydrogens`, `addMembrane`): https://docs.openmm.org/latest/api-python/generated/openmm.app.modeller.Modeller.html
- OpenMM releases; 8.5.2 is the pinned project release: https://github.com/openmm/openmm/releases

Recommended software citation:

- Eastman P. et al. OpenMM 8: Molecular Dynamics Simulation with Machine Learning Potentials. *J. Phys. Chem. B* (2024), and the citation guidance in the installed OpenMM manual.

## Structure preparation

- PDBFixer official repository and capabilities: https://github.com/openmm/pdbfixer
- RCSB Protein Data Bank: https://www.rcsb.org/
- RCSB ligand (Chemical Component Dictionary) ideal-coordinate downloads, used for
  ligand bond orders and formal charge: `https://files.rcsb.org/ligands/download/<RES>_ideal.sdf`
- RCSB full validation reports, preserved by the Phase 5 source audit:
  `https://files.rcsb.org/validation/view/<pdbid>_full_validation.pdf` (lower-case PDB ID)
- wwPDB validation and archive information: https://www.wwpdb.org/

## Small-molecule force fields

- OpenFF Toolkit documentation: https://docs.openforcefield.org/projects/toolkit/en/stable/
- OpenFF examples: https://docs.openforcefield.org/examples
- OpenFF FAQ on why PDB alone is insufficient for ligand chemical identity: https://docs.openforcefield.org/faq
- SMIRNOFF specification: https://docs.openforcefield.org/projects/toolkit/en/topology/users/smirnoff.html
- OpenMM Force Fields releases; 0.16.0 requires explicit force-field selection and OpenMM >=8.5.1: https://github.com/openmm/openmmforcefields/releases

## Analysis and visualization

- MDAnalysis documentation: https://docs.mdanalysis.org/stable/
- MDAnalysis user guide and examples: https://userguide.mdanalysis.org/
- MDTraj official repository/documentation: https://github.com/mdtraj/mdtraj
- NGL/visualization project: https://nglviewer.org/
- py3Dmol repository: https://github.com/3dmol/3Dmol.js

## Membrane systems

- OPM database: https://opm.phar.umich.edu/
- OPM oriented-coordinate asset download used by Phase 4: `https://biomembhub.org/shared/opm-assets/pdb/<pdbid>.pdb`
- OPM orientation metadata API used by Phase 4: `https://opm-back.cc.lehigh.edu/opm-backend/primary_structures/pdbid/<pdbid>`
- OpenMM `addMembrane` documentation: https://docs.openmm.org/latest/api-python/generated/openmm.app.modeller.Modeller.html
- CHARMM-GUI Membrane Builder tutorial: https://www.charmm-gui.org/tutorial/membrane
- Jo S. et al. CHARMM-GUI Membrane Builder for mixed bilayers and complex biological membrane systems. *PLoS ONE* (2009).
- Wu E.L. et al. CHARMM-GUI Membrane Builder toward realistic biological membrane simulations. *J. Comput. Chem.* (2014).
- Smith D.J. et al. Simulation best practices for lipid membranes. *Living Journal of Computational Molecular Science* / associated open article.

## Tutorial and research structures

- `1UBQ` (Phase 2): ubiquitin. https://www.rcsb.org/structure/1UBQ
  - Vijay-Kumar S. et al. Structure of ubiquitin refined at 1.8 Å resolution.
    *J. Mol. Biol.* (1987) 194:531-544, DOI 10.1016/0022-2836(87)90679-6.
- `181L` (Phase 3): T4 lysozyme L99A complex containing benzene.
  https://www.rcsb.org/structure/181L
  - Morton A. et al. Specificity of ligand binding in a buried nonpolar cavity of
    T4 lysozyme: linkage of dynamics and structural plasticity.
    *Biochemistry* (1995) 34:8576-8588, DOI 10.1021/bi00027a007.
- `BNZ` (Phase 3): benzene, RCSB Chemical Component Dictionary ideal SDF.
  https://files.rcsb.org/ligands/download/BNZ_ideal.sdf
- `1J4N` (Phase 4): bovine aquaporin-1 tetramer; the oriented coordinates come
  from OPM. https://www.rcsb.org/structure/1J4N
  - Sui H. et al. Structural basis of water-specific transport through the AQP1
    water channel. *Nature* (2001) 414:872-878, DOI 10.1038/414872a, PMID 11780053.

## Approved Phase 5 structures

Selection is a human decision, recorded in `state/decisions/DR-005-5HT2A.md`, with
the candidate evidence in `state/decisions/PHASE5_SOURCE_AUDIT.md`. Both ligands
are simulated at `+1` protonation, and the receptor is oriented to OPM `7WC5`.

- `7WC5` — 5-HT2A–BRIL with psilocin; orientation source.
  https://www.rcsb.org/structure/7WC5 , OPM record https://opm.phar.umich.edu/proteins/8701
- `7WC6` — 5-HT2A–BRIL with lysergide (LSD, ligand `7LD`), X-ray 2.60 Å.
  https://www.rcsb.org/structure/7WC6 , https://gpcrdb.org/structure/7WC6
- `7WC7` — 5-HT2A–BRIL with lisuride (ligand `H8G`), X-ray 2.60 Å.
  https://www.rcsb.org/structure/7WC7 , https://gpcrdb.org/structure/7WC7
- Ligand CCD ideal SDFs: https://files.rcsb.org/ligands/download/7LD_ideal.sdf
  and https://files.rcsb.org/ligands/download/H8G_ideal.sdf
- Primary citation for the 7WC4–7WC9 series: Cao D. et al. Structure-based
  discovery of nonhallucinogenic psychedelic analogs. *Science* (2022)
  375:403-411, DOI 10.1126/science.abl8615, PMID 35084960.
- GPCRdb (numbering, interactions, ligand pages): https://gpcrdb.org/

## Other 5-HT2A examples for future decision-making

Do not select these automatically; match the structure to the research question.

- `6A94`: 5-HT2A bound to zotepine (inactive-state series with risperidone,
  `6A95`). https://www.rcsb.org/structure/6A94
  - Kimura K.T. et al. Structures of the 5-HT2A receptor in complex with the
    antipsychotics risperidone and zotepine.
    *Nat. Struct. Mol. Biol.* (2019) 26:121-128, DOI 10.1038/s41594-018-0180-z,
    PMID 30723326.
- `6WHA`: active 5-HT2A bound to 25-CN-NBOH in a mini-Gq signaling complex.
  https://www.rcsb.org/structure/6WHA
  - Kim K. et al. Structure of a hallucinogen-activated Gq-coupled 5-HT2A serotonin
    receptor. *Cell* (2020) 182:1574-1588, DOI 10.1016/j.cell.2020.08.024.
