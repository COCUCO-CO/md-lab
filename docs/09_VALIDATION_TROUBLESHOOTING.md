# Validation and troubleshooting

## General diagnostic order

1. Find the first warning/error in the log.
2. Verify input hashes and file completeness.
3. Verify topology and coordinate atom counts.
4. Verify units.
5. Verify all residues and atoms have parameters.
6. Inspect the prepared structure visually.
7. Inspect minimization energy and maximum force.
8. Test a shorter time step only as a diagnosis, not a hidden permanent fix.
9. Reproduce on CPU/Reference for a tiny case if a GPU-specific issue is suspected.
10. Preserve the failed run and create a new run ID.

## NaN coordinates or energy

Likely causes:

- atom overlap or missing minimization;
- incorrect ligand chemistry/parameters;
- too-large time step;
- inconsistent constraints;
- bad periodic box;
- loading a state into a nonidentical System;
- numerical overflow after an extreme force.

Actions:

- inspect the last finite frame;
- calculate minimum interatomic distances;
- rerun minimization with detailed force checks;
- test 1 fs for diagnosis;
- verify system XML/config hashes;
- do not simply increase minimization iterations without locating the clash.

## Constraint failure

- identify the atoms/residue in the error if available;
- inspect topology and masses;
- check whether ligand templates added duplicate/missing bonds;
- verify water model and constraints are compatible;
- test a smaller time step;
- never disable constraints silently.

## Missing force-field template

- print residue name, atom names, elements, bonds, and external bonds;
- standardize terminal naming deliberately;
- ensure the correct water/ion XML belongs to the force-field family;
- for ligand, verify explicit chemical identity and registered template generator;
- do not rename atoms randomly until a template matches.

## Density outside range

- ensure analysis uses production NPT frames only;
- confirm barostat is active and correct;
- inspect box volume evolution;
- verify water model and temperature;
- check vacuum gaps and molecule imaging;
- extend equilibration if the trend has not plateaued, documenting the criterion.

## Large RMSD

Before declaring instability:

- make molecules whole under PBC;
- align using the intended atom selection;
- inspect domain motion versus unfolding;
- compare Cα, backbone, and domain-specific RMSD;
- check whether the starting crystal structure relaxed;
- inspect secondary structure and contacts;
- compare replicas.

## Ligand leaves binding site

- confirm protein alignment before ligand RMSD;
- confirm ligand atom mapping and formal charge;
- inspect protonation and tautomer;
- inspect missing structural waters/ions;
- inspect clashes introduced during hydrogenation;
- check whether the experimental pose depends on crystal contacts or partner proteins;
- do not add unreported production restraints to force retention.

## Membrane abnormalities

- verify input orientation and Z normal;
- confirm compatible lipid/water force fields;
- verify membrane barostat modes;
- inspect leaflet lipid counts;
- inspect protein insertion depth;
- extend restrained equilibration if packing is still adapting;
- distinguish trajectory imaging artifacts from physical defects.

## Performance unexpectedly low

- confirm CUDA platform and GPU utilization;
- reduce excessive trajectory write frequency;
- ensure output is on local SSD, not slow network storage;
- check CPU oversubscription and other GPU processes;
- compare mixed vs single precision only in a controlled benchmark;
- record ns/day after warm-up, not from the first few seconds.
