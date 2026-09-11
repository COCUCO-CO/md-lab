# Phase 5 source and candidate audit

- Date (UTC): 2026-07-27
- Status: COMPLETE FOR DECISION REVIEW
- Target: human 5-HT2A receptor
- Scope: structure selection evidence only; no prepared model or simulation has been started

## Candidate comparison

| Candidate | Functional state | Ligand | Method / resolution | Construct issue | Assessment |
|---|---|---|---|---|---|
| 6A94 | Inactive | Zotepine, antagonist | X-ray, 2.90 Å | BRIL fusion and six mutations | Useful inactive reference, but not construct-matched to an active structure |
| 6WHA | Active, Gq/11 complex | 25-CN-NBOH, agonist | Cryo-EM, 3.36 Å | Five-chain assembly with mini-Gq, Gβ, Gγ and scFv16; receptor is chimeric | Biologically relevant active complex, but a comparison to 6A94 would confound ligand, state, method, construct and partners |
| 7WC6 | Inactive | Lysergide (LSD), agonist | X-ray, 2.60 Å | BRIL fusion and three mutations | Recommended half of a matched ligand comparison |
| 7WC7 | Inactive | Lisuride, agonist | X-ray, 2.60 Å | Same BRIL fusion and same three mutations as 7WC6 | Recommended half of a matched ligand comparison |

Sources:

- RCSB 7WC6: <https://www.rcsb.org/structure/7WC6>
- RCSB 7WC7: <https://www.rcsb.org/structure/7WC7>
- GPCRdb 7WC6: <https://gpcrdb.org/structure/7WC6>
- GPCRdb 7WC7: <https://gpcrdb.org/structure/7WC7>
- GPCRdb interaction tables: <https://gpcrdb.org/interaction/7WC6> and <https://gpcrdb.org/interaction/7WC7>
- RCSB 6A94: <https://www.rcsb.org/structure/6A94>
- RCSB 6WHA: <https://www.rcsb.org/structure/6WHA>

## Why 7WC6 and 7WC7 are the least-confounded pair

Observation from deposited coordinates:

- Both entries have the same 376-residue deposited engineered sequence.
- Both contain the same engineered substitutions: S162K, M164W and S372N.
- Both contain BRIL in place of receptor residues 266-312.
- Their 274 common resolved receptor C-alpha atoms superpose at 0.376 Å RMSD.
- Both report the same two disulfides: C148-C227 and C349-C353.
- Both are 2.60 Å X-ray structures from the same publication and experimental series.

The intended comparison therefore changes the bound ligand while keeping the receptor scaffold, functional-state classification and simulation Hamiltonian matched. It does not test activation, psychedelic action or signaling bias.

## Deposited-coordinate audit

| Feature | 7WC6 | 7WC7 |
|---|---:|---:|
| Modeled polymer residues | 355 / 376 | 358 / 376 |
| Missing N-terminal construct residues | 67-73 | 67-70 |
| Missing receptor ICL2 | 181-187 | 181-187 |
| Missing BRIL linker | 1061-1065, GSGSG | 1061-1065, GSGSG |
| Missing C-terminal construct residues | 402-403 | 402-403 |
| Engineered substitutions | S162K, M164W, S372N | S162K, M164W, S372N |
| Waters | 2 | 7 |
| Cholesterol (CLR) | 1 | 1 |
| Monoolein fragments (OLC) | 4 | 5 |
| Magnesium | 1 | 1 |
| Pentaethylene glycol (1PE) | 1 | 1 |
| Di(hydroxyethyl)ether (PEG) | 3 | 3 |

The closest deposited water oxygen is 10.82 Å from LSD and 10.57 Å from lisuride. None of the deposited waters is a direct ligand-contact water under a 5 Å criterion.

## Chemically explicit ligand audit

The ligand bond orders and stereochemistry were read from RCSB CCD SDF files, not inferred from PDB coordinates.

| Entry | CCD | Neutral CCD formula | Proposed bound-state site | Initial D155 contact |
|---|---|---|---|---:|
| 7WC6 | 7LD | C20H25N3O | N2 protonated, total charge +1 | 2.61 Å |
| 7WC7 | H8G | C20H26N4O | NAX protonated, total charge +1 | 2.65 Å |

Proposed protonated isomeric SMILES:

- LSD: `CCN(CC)C(=O)[C@@H]1C=C2c3cccc4[nH]cc(c34)C[C@H]2[NH+](C)C1`
- Lisuride: `CCN(CC)C(=O)N[C@H]1C=C2c3cccc4[nH]cc(c34)C[C@H]2[NH+](C)C1`

The neutral CCD files have zero formal charge. Protonation is therefore an explicit scientific change requiring approval. Experimental pKa values near 7.8 and the deposited charge-assisted interaction with D155 support, but do not uniquely prove, the proposed bound cationic microstates.

## Pre-registered structural observation behind the question

GPCRdb reports:

- Lisuride-specific deposited contacts with ECL2 residues C227 (45.50x50) and L229 (45.52x52).
- LSD-specific deposited contacts with S239 (5.43x44) and N343 (6.55x55).
- A charge-assisted ligand interaction with D155 (3.32x32) in both structures.

These observations define the hypothesis before any trajectory is examined.

## OPM orientation source

OPM provides 7WC5, the psilocin-bound member of the same isomorphous construct series, with:

- seven transmembrane helices;
- hydrophobic thickness 32.2 Å;
- tilt 10 degrees;
- N terminus on the extracellular side.

7WC6 and 7WC7 will be backbone-aligned to this common OPM orientation. No OPM-oriented coordinate file was found for either selected entry.

Sources:

- OPM record: <https://opm.phar.umich.edu/proteins/8701>
- Local immutable coordinate: `inputs/phase05/orientation/7WC5_opm.pdb`
- Local immutable metadata: `inputs/phase05/orientation/7WC5_opm_metadata.json`

## Immutable local sources

| File | SHA-256 |
|---|---|
| `inputs/phase05/candidates/7WC6/7WC6.cif` | `8d6e1461c9a370c953596d8c03ba5afbfde2b6cb66d77c4252cc8ac08f95fe15` |
| `inputs/phase05/candidates/7WC6/7WC6.pdb` | `773af2d51b2e32543a54740130140573702306fd82063bba270e111e68bea233` |
| `inputs/phase05/candidates/7WC6/7wc6_full_validation.pdf` | `b9cdc6fc3c492308e695dfd161b4cbc281873a400653cc925a3ef39d08bdb6b0` |
| `inputs/phase05/candidates/7WC6/7LD_ideal.sdf` | `c94d44461e9f65ee9d85694860b3d5c67333f0a060ff86421f1093eec517a9cb` |
| `inputs/phase05/candidates/7WC7/7WC7.cif` | `edda39fdf1f8f170c2da0ad4dcf15f83b2c9c3dba42947ef857d214327b3c07a` |
| `inputs/phase05/candidates/7WC7/7WC7.pdb` | `cad75d13c26f3c76b6def9657689b3eb830dffb84b4d666b645a57fc91d81eac` |
| `inputs/phase05/candidates/7WC7/7wc7_full_validation.pdf` | `fa1b69dba2eb41946763e262ac38c3c66f533c979e4169eea45236da3b5a1246` |
| `inputs/phase05/candidates/7WC7/H8G_ideal.sdf` | `cecec53cb7fe16d5308c930166eff5395d85ba880c6e2475f9668c5314665a28` |
| `inputs/phase05/orientation/7WC5_opm.pdb` | `93716ed37a82d116a4d0aebfb0b7df0164035b91b3b870a1b2d42fb652d43711` |
| `inputs/phase05/orientation/7WC5_opm_metadata.json` | `d90e86daf1094c2026603d8afbde94702bc52ddc7262436cb9041f23000f24ed` |

Every file has a neighboring `.provenance.json` containing its URL, UTC retrieval time, byte count and SHA-256. The first 7WC6 CIF download wrote the immutable file before a relative-path validation error; its sidecar was reconstructed immediately from the source URL, file modification time converted to UTC, byte count and actual SHA-256. The coordinate file itself was not modified.

