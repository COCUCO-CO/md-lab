# Primary references and official documentation

Accessed 2026-07-10 unless otherwise stated.

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
- OpenMM `addMembrane` documentation: https://docs.openmm.org/latest/api-python/generated/openmm.app.modeller.Modeller.html
- CHARMM-GUI Membrane Builder tutorial: https://www.charmm-gui.org/tutorial/membrane
- Jo S. et al. CHARMM-GUI Membrane Builder for mixed bilayers and complex biological membrane systems. *PLoS ONE* (2009).
- Wu E.L. et al. CHARMM-GUI Membrane Builder toward realistic biological membrane simulations. *J. Comput. Chem.* (2014).
- Smith D.J. et al. Simulation best practices for lipid membranes. *Living Journal of Computational Molecular Science* / associated open article.

## Tutorial structures

- `1UBQ`: ubiquitin, RCSB PDB.
- `181L`: T4 lysozyme L99A complex containing benzene, RCSB PDB.
- `BNZ`: RCSB Chemical Component Dictionary entry and ideal SDF.
- `1J4N`: aquaporin-1 tetramer, RCSB PDB and OPM-oriented coordinate entry.

## 5-HT2A examples for future decision-making

Do not select these automatically; match the structure to the research question.

- `6A94`: inactive-state 5-HT2A structure listed by OPM.
- `6WHA`: active 5-HT2A bound to 25-CN-NBOH in a signaling complex, RCSB PDB.
- Kim K. et al. Structure of a hallucinogen-activated Gq-coupled 5-HT2A serotonin receptor. *Cell* (2020).
