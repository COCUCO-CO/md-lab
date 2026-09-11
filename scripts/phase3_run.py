#!/usr/bin/env python
from __future__ import annotations

import argparse
from collections import Counter
import math
import random
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import openmm
from openmm import app, unit
from openff.toolkit import Molecule
from openmmforcefields.generators import SMIRNOFFTemplateGenerator
from pdbfixer import PDBFixer
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

from mdlab.biomolecular import (
    ION_NAMES,
    STANDARD_AA,
    WATER_NAMES,
    create_system,
    run_staged_simulation,
    topology_summary,
)
from mdlab.core import (
    create_run,
    download,
    read_json,
    resolve_config,
    sha256_file,
    write_json,
)


def source_record_audit(path: Path) -> dict:
    alternate_locations: Counter[str] = Counter()
    heterogen_atoms: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        record = line[:6].strip()
        if record not in {"ATOM", "HETATM"}:
            continue
        alternate_location = line[16:17].strip()
        if alternate_location:
            alternate_locations[alternate_location] += 1
        if record == "HETATM":
            heterogen_atoms[line[17:20].strip()] += 1
    return {
        "alternate_location_atom_counts": dict(sorted(alternate_locations.items())),
        "heterogen_atom_counts": dict(sorted(heterogen_atoms.items())),
    }


def validate_benzene_mapping(
    rd_mol: Chem.Mol,
    ligand_residue: app.Topology.Residue,
    topology: app.Topology,
) -> list[dict[str, int | str]]:
    sdf_heavy = [atom for atom in rd_mol.GetAtoms() if atom.GetSymbol() != "H"]
    pdb_atoms = list(ligand_residue.atoms())
    if len(pdb_atoms) != len(sdf_heavy):
        raise RuntimeError(
            f"BNZ atom mapping mismatch: PDB has {len(pdb_atoms)} atoms and "
            f"the SDF has {len(sdf_heavy)} heavy atoms"
        )

    mapping: list[dict[str, int | str]] = []
    pdb_to_sdf: dict[str, int] = {}
    for position, (pdb_atom, sdf_atom) in enumerate(zip(pdb_atoms, sdf_heavy), start=1):
        expected_name = f"{sdf_atom.GetSymbol().upper()}{position}"
        pdb_symbol = pdb_atom.element.symbol.upper() if pdb_atom.element is not None else None
        if pdb_atom.name != expected_name or pdb_symbol != sdf_atom.GetSymbol().upper():
            raise RuntimeError(
                "Ambiguous BNZ atom mapping: PDB atom names/elements do not "
                "match the CCD SDF heavy-atom order"
            )
        pdb_to_sdf[pdb_atom.name] = sdf_atom.GetIdx()
        mapping.append(
            {
                "pdb_atom_name": pdb_atom.name,
                "element": pdb_symbol,
                "sdf_atom_index": sdf_atom.GetIdx() + 1,
            }
        )

    pdb_atom_set = set(pdb_atoms)
    pdb_edges = {
        tuple(sorted((pdb_to_sdf[first.name], pdb_to_sdf[second.name])))
        for first, second in topology.bonds()
        if first in pdb_atom_set and second in pdb_atom_set
    }
    sdf_heavy_indices = {atom.GetIdx() for atom in sdf_heavy}
    sdf_edges = {
        tuple(sorted((bond.GetBeginAtomIdx(), bond.GetEndAtomIdx())))
        for bond in rd_mol.GetBonds()
        if bond.GetBeginAtomIdx() in sdf_heavy_indices
        and bond.GetEndAtomIdx() in sdf_heavy_indices
    }
    if pdb_edges != sdf_edges:
        raise RuntimeError(
            f"BNZ bond-graph mismatch between PDB and CCD SDF: "
            f"PDB={sorted(pdb_edges)}, SDF={sorted(sdf_edges)}"
        )
    return mapping


def validate_benzene_hydrogen_definition(
    rd_mol: Chem.Mol,
    definition_path: Path,
) -> dict[str, str]:
    sdf_heavy = [atom for atom in rd_mol.GetAtoms() if atom.GetSymbol() != "H"]
    heavy_positions = {
        atom.GetIdx(): position
        for position, atom in enumerate(sdf_heavy, start=1)
    }
    sdf_hydrogen_parents: dict[str, str] = {}
    sdf_hydrogens = [atom for atom in rd_mol.GetAtoms() if atom.GetSymbol() == "H"]
    for position, hydrogen in enumerate(sdf_hydrogens, start=1):
        neighbors = list(hydrogen.GetNeighbors())
        if len(neighbors) != 1 or neighbors[0].GetIdx() not in heavy_positions:
            raise RuntimeError("CCD SDF contains an invalid BNZ hydrogen attachment")
        parent = neighbors[0]
        sdf_hydrogen_parents[f"H{position}"] = (
            f"{parent.GetSymbol().upper()}{heavy_positions[parent.GetIdx()]}"
        )

    root = ET.parse(definition_path).getroot()
    residues = [
        residue
        for residue in root.findall("Residue")
        if residue.attrib.get("name") == "BNZ"
    ]
    if len(residues) != 1:
        raise RuntimeError("BNZ hydrogen definition must contain exactly one BNZ residue")
    definition_parents = {
        hydrogen.attrib["name"]: hydrogen.attrib["parent"]
        for hydrogen in residues[0].findall("H")
    }
    if definition_parents != sdf_hydrogen_parents:
        raise RuntimeError(
            "BNZ hydrogen definition does not match the immutable CCD SDF: "
            f"definition={definition_parents}, SDF={sdf_hydrogen_parents}"
        )
    return definition_parents


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["quick", "teaching"], default="quick")
    args = parser.parse_args()
    cfg = resolve_config(3, args.profile)
    random.seed(int(cfg["seed"]))
    run = create_run(3, args.profile, cfg)

    pdb_path = ROOT / "inputs" / "phase03" / f"{cfg['pdb_id']}.pdb"
    sdf_path = ROOT / "inputs" / "phase03" / f"{cfg['ligand_resname']}_ideal.sdf"
    pdb_prov = download(cfg["source_url"], pdb_path)
    sdf_prov = download(cfg["ligand_sdf_url"], sdf_path)
    source_records = source_record_audit(pdb_path)
    manifest = read_json(run / "manifest.json")
    manifest["inputs"].update({"pdb": pdb_prov, "ligand_sdf": sdf_prov})
    write_json(run / "manifest.json", manifest)

    rd_mol = Chem.SDMolSupplier(str(sdf_path), removeHs=False)[0]
    if rd_mol is None:
        raise RuntimeError("RDKit could not parse ligand SDF")
    formal_charge = sum(atom.GetFormalCharge() for atom in rd_mol.GetAtoms())
    if formal_charge != int(cfg["ligand_formal_charge"]):
        raise RuntimeError(f"Ligand formal charge {formal_charge} != configured {cfg['ligand_formal_charge']}")
    stereocenters = Chem.FindMolChiralCenters(
        rd_mol,
        includeUnassigned=True,
        useLegacyImplementation=False,
    )
    ligand = Molecule.from_rdkit(
        rd_mol,
        allow_undefined_stereo=False,
        hydrogens_are_explicit=True,
    )
    hydrogen_definition_path = ROOT / "configs" / "BNZ_hydrogens.xml"
    hydrogen_parent_mapping = validate_benzene_hydrogen_definition(
        rd_mol,
        hydrogen_definition_path,
    )
    app.Modeller.loadHydrogenDefinitions(str(hydrogen_definition_path))

    fixer = PDBFixer(filename=str(pdb_path))
    reference_platform = openmm.Platform.getPlatformByName("Reference")
    fixer.platform = reference_platform
    original = topology_summary(fixer.topology)
    fixer.findMissingResidues()
    missing_residues = {str(key): value for key, value in fixer.missingResidues.items()}
    expected_unresolved_terminal = {"(0, 162)": ["ASN", "LEU"]}
    if missing_residues != expected_unresolved_terminal:
        raise RuntimeError(f"Unexpected missing residues require review: {missing_residues}")
    fixer.missingResidues = {}
    fixer.findNonstandardResidues()
    nonstandard = [
        (residue.chain.id, residue.id, residue.name, replacement)
        for residue, replacement in fixer.nonstandardResidues
    ]
    if nonstandard:
        raise RuntimeError(f"Unexpected nonstandard protein residues: {nonstandard}")
    fixer.findMissingAtoms()
    fixer.missingAtoms = {r: atoms for r, atoms in fixer.missingAtoms.items() if r.name in STANDARD_AA}
    fixer.missingTerminals = {r: atoms for r, atoms in fixer.missingTerminals.items() if r.name in STANDARD_AA}
    missing_atoms = {f"{r.chain.id}:{r.id}:{r.name}": [a.name for a in atoms] for r, atoms in fixer.missingAtoms.items()}
    fixer.addMissingAtoms(seed=int(cfg["seed"]))

    modeller = app.Modeller(fixer.topology, fixer.positions)
    delete_residues = [
        residue
        for residue in modeller.topology.residues()
        if residue.name not in STANDARD_AA | {cfg["ligand_resname"]}
    ]
    removed_residues = dict(sorted(Counter(residue.name for residue in delete_residues).items()))
    modeller.delete(delete_residues)
    ligand_residues = [r for r in modeller.topology.residues() if r.name == cfg["ligand_resname"]]
    if len(ligand_residues) != 1:
        raise RuntimeError(f"Expected one {cfg['ligand_resname']} residue, found {len(ligand_residues)}")
    ligand_atoms = list(ligand_residues[0].atoms())
    ligand_atom_set = set(ligand_atoms)
    ligand_bonds = [
        (first.name, second.name)
        for first, second in modeller.topology.bonds()
        if first in ligand_atom_set and second in ligand_atom_set
    ]
    if len(ligand_bonds) == 0:
        raise RuntimeError("PDB ligand has no bond graph. Do not infer chemistry from coordinates automatically.")
    atom_mapping = validate_benzene_mapping(rd_mol, ligand_residues[0], modeller.topology)

    forcefield = app.ForceField(cfg["protein_forcefield"], cfg["water_forcefield"])
    generator = SMIRNOFFTemplateGenerator(molecules=[ligand], forcefield=cfg["small_molecule_forcefield"])
    forcefield.registerTemplateGenerator(generator.generator)
    modeller.addHydrogens(
        forcefield,
        pH=float(cfg["ph"]),
        platform=reference_platform,
    )
    prepared_ligand_residues = [
        residue
        for residue in modeller.topology.residues()
        if residue.name == cfg["ligand_resname"]
    ]
    if len(prepared_ligand_residues) != 1:
        raise RuntimeError("BNZ residue was lost during hydrogen addition")
    prepared_ligand_atoms = set(prepared_ligand_residues[0].atoms())
    actual_hydrogen_parents = {}
    for first, second in modeller.topology.bonds():
        if first not in prepared_ligand_atoms or second not in prepared_ligand_atoms:
            continue
        if first.element == app.element.hydrogen:
            actual_hydrogen_parents[first.name] = second.name
        elif second.element == app.element.hydrogen:
            actual_hydrogen_parents[second.name] = first.name
    if actual_hydrogen_parents != hydrogen_parent_mapping:
        raise RuntimeError(
            "Hydrogenated BNZ does not match the SDF-validated definition: "
            f"{actual_hydrogen_parents}"
        )
    modeller.addSolvent(
        forcefield,
        model=str(cfg["water_model"]),
        padding=float(cfg["padding_nm"]) * unit.nanometer,
        ionicStrength=float(cfg["ionic_strength_molar"]) * unit.molar,
        positiveIon="Na+",
        negativeIon="Cl-",
        neutralize=True,
    )
    prepared = topology_summary(modeller.topology)
    residue_counts = prepared["residue_counts"]
    water_count = sum(residue_counts.get(name, 0) for name in WATER_NAMES)
    ion_counts = {
        name: count
        for name, count in residue_counts.items()
        if name in ION_NAMES and count
    }
    box_vectors = modeller.topology.getPeriodicBoxVectors()
    box_vectors_nm = [
        list(vector.value_in_unit(unit.nanometer)) for vector in box_vectors
    ]
    box_lengths_nm = [
        math.sqrt(sum(component**2 for component in vector))
        for vector in box_vectors_nm
    ]
    with (run / "prepared" / "system.pdb").open("w", encoding="utf-8") as handle:
        app.PDBFile.writeFile(modeller.topology, modeller.positions, handle, keepIds=True)

    audit = {
        "pdb_id": cfg["pdb_id"],
        "preparation_seed": int(cfg["seed"]),
        "hydrogen_placement_platform": "Reference",
        "original_topology": original,
        "alternate_locations": source_records["alternate_location_atom_counts"],
        "original_heterogen_atoms": source_records["heterogen_atom_counts"],
        "missing_residues_left_unbuilt": missing_residues,
        "nonstandard_residues": nonstandard,
        "missing_atoms_added": missing_atoms,
        "removed_source_residues": removed_residues,
        "retained_source_heterogens": {cfg["ligand_resname"]: 1},
        "ligand": {
            "name": rd_mol.GetProp("_Name") if rd_mol.HasProp("_Name") else cfg["ligand_resname"],
            "resname": cfg["ligand_resname"],
            "sdf_sha256": sdf_prov["sha256"],
            "formula": rdMolDescriptors.CalcMolFormula(rd_mol),
            "formal_charge": formal_charge,
            "configured_formal_charge": int(cfg["ligand_formal_charge"]),
            "sdf_atoms_including_hydrogen": rd_mol.GetNumAtoms(),
            "sdf_atoms_excluding_hydrogen": sum(
                atom.GetSymbol() != "H" for atom in rd_mol.GetAtoms()
            ),
            "sdf_bonds": rd_mol.GetNumBonds(),
            "aromatic_bonds": sum(1 for b in rd_mol.GetBonds() if b.GetIsAromatic()),
            "stereocenters": [
                {"sdf_atom_index": index + 1, "assignment": assignment}
                for index, assignment in stereocenters
            ],
            "pdb_heavy_atoms": len(ligand_atoms),
            "pdb_ligand_bonds": ligand_bonds,
            "mapping_one_to_one": True,
            "mapping_ambiguous": False,
            "mapping_basis": "PDB atom names/elements match CCD SDF heavy-atom order and bond graph",
            "atom_mapping": atom_mapping,
            "hydrogen_parent_mapping": hydrogen_parent_mapping,
            "hydrogen_definition_path": str(
                hydrogen_definition_path.relative_to(ROOT)
            ),
            "hydrogen_definition_sha256": sha256_file(
                hydrogen_definition_path
            ),
            "assigned_forcefield_version": cfg["small_molecule_forcefield"],
        },
        "prepared_topology": prepared,
        "water_molecules": water_count,
        "ion_residue_counts": ion_counts,
        "periodic_box_vectors_nm": box_vectors_nm,
        "periodic_box_lengths_nm": box_lengths_nm,
        "forcefields": [cfg["protein_forcefield"], cfg["water_forcefield"], cfg["small_molecule_forcefield"]],
    }
    try:
        parameterized_system = create_system(forcefield, modeller.topology, cfg)
    except Exception as exc:
        audit["parameterization"] = {
            "status": "FAIL",
            "unassigned_parameter_exception": repr(exc),
        }
        write_json(run / "prepared" / "preparation_audit.json", audit)
        raise
    audit["parameterization"] = {
        "status": "PASS",
        "unassigned_parameter_exception": None,
        "parameterized_particles": parameterized_system.getNumParticles(),
        "force_count": parameterized_system.getNumForces(),
    }
    write_json(run / "prepared" / "preparation_audit.json", audit)
    run_staged_simulation(run, modeller.topology, modeller.positions, forcefield, cfg, membrane=False)
    print(run)


if __name__ == "__main__":
    main()
