# Phase 3 — Protein–ligand complex

## Purpose

Introduce the most failure-prone part of routine biomolecular setup: small-molecule chemical identity and parameterization.

## Tutorial system

- PDB entry: `181L`.
- Protein: T4 lysozyme L99A.
- Ligand residue: benzene (`BNZ`).
- Ligand chemical source: RCSB Chemical Component Dictionary SDF.
- Protein force field: Amber ff19SB.
- Ligand force field: explicitly named OpenFF `openff-2.2.1` through `SMIRNOFFTemplateGenerator`.
- Solvent: OPC water with compatible ions.

Benzene is chosen because its charge, aromaticity, and stereochemistry are unambiguous. This is a training system, not a claim about binding affinity.

The two unresolved C-terminal residues reported for 181L (ASN 163 and LEU
164) are left unresolved; this tutorial does not reconstruct terminal
coordinates. The preparation retains BNZ but removes the non-target HED
additive, the two source chloride ions, and crystallographic bulk water before
controlled resolvation. In the source structure, the nearest crystallographic
water oxygen is 0.817 nm from BNZ and the RCSB AC4 binding-site record does not
name a site water.

## Chemical identity audit

Before adding parameters, the agent must report:

- ligand name and residue name;
- source SDF hash;
- atom count with and without hydrogens;
- elemental formula;
- formal charge;
- aromatic bonds;
- stereocenters, if any;
- whether PDB ligand atoms map one-to-one onto the chemical template;
- assigned force-field version;
- any unassigned parameter exception.

The run must stop if formal charge differs from the configured value or if atom mapping is ambiguous.

## Procedure

### Step 3.1 — Acquire independent coordinate and chemistry sources

The PDB supplies experimental complex coordinates. The CCD SDF supplies bond orders and formal charge. The script records both sources and hashes.

### Step 3.2 — Prepare and parameterize

```bash
make phase3 PROFILE=quick
```

The script:

1. downloads the PDB and ligand SDF;
2. loads the ligand as an OpenFF molecule;
3. validates charge, aromaticity, and atom mapping;
4. leaves unresolved terminal residues unbuilt and repairs resolved standard
   protein atoms without deleting the ligand;
5. registers the explicit SMIRNOFF template generator;
6. removes source HED, chloride ions, and bulk water, then adds protein and
   ligand hydrogens deterministically using the combined force field and an
   explicit BNZ C1–H1 through C6–H6 definition validated against the CCD SDF;
7. solvates and adds ions;
8. verifies every residue is parameterized;
9. minimizes and equilibrates with heavy-atom restraints;
10. runs unrestrained production;
11. records template/force-field metadata and serialized system.

### Step 3.3 — Analyze and visualize

```bash
make phase3-analysis PROFILE=quick
make phase3-view PROFILE=quick
```

Required outputs:

- protein Cα RMSD;
- ligand heavy-atom RMSD after protein alignment;
- ligand center-of-mass displacement from its initial binding-site position;
- minimum ligand–protein distance;
- contact occupancy by residue using a documented cutoff;
- binding-site snapshots at beginning, middle, and end;
- 2D ligand identity image and 3D interactive complex.

### Step 3.4 — Interpretation limits

Ligand remaining near its crystallographic pose during a short trajectory does not prove affinity. Ligand movement does not automatically prove poor binding; it may reflect preparation, protonation, force-field limitations, insufficient equilibration, or a real alternative pose. Binding free energy requires a dedicated, validated methodology.

### Step 3.5 — Gate

The gate requires:

- chemical identity audit passes;
- all atoms receive parameters;
- no NaN or constraint error;
- temperature and density pass;
- protein geometry remains sane;
- maximum covalent-bond length does not exceed the established 0.25 nm
  tutorial sanity threshold;
- ligand RMSD/COM do not exceed broad tutorial sanity bounds;
- contacts and visualization files are generated.

A failed ligand-position gate triggers inspection; it must not be “fixed” by adding hidden restraints to production.
