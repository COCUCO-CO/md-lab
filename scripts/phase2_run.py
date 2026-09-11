#!/usr/bin/env python
from __future__ import annotations

import argparse
from collections import Counter
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import openmm
from openmm import app, unit
from pdbfixer import PDBFixer

from mdlab.biomolecular import (
    ION_NAMES,
    STANDARD_AA,
    WATER_NAMES,
    create_forcefield,
    run_staged_simulation,
    topology_summary,
)
from mdlab.core import create_run, download, read_json, resolve_config, write_json


def source_record_audit(path: Path) -> dict:
    alternate_locations: Counter[str] = Counter()
    heterogens: Counter[str] = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        record = line[:6].strip()
        if record not in {"ATOM", "HETATM"}:
            continue
        alternate_location = line[16:17].strip()
        if alternate_location:
            alternate_locations[alternate_location] += 1
        if record == "HETATM":
            heterogens[line[17:20].strip()] += 1
    return {
        "alternate_location_atom_counts": dict(sorted(alternate_locations.items())),
        "heterogen_atom_counts": dict(sorted(heterogens.items())),
    }


def disulfide_bonds(topology: app.Topology) -> list[dict[str, str]]:
    bonds = []
    for first, second in topology.bonds():
        if first.name == second.name == "SG" and {
            first.residue.name,
            second.residue.name,
        } <= {"CYS", "CYX"}:
            bonds.append(
                {
                    "first": f"{first.residue.chain.id}:{first.residue.id}:{first.residue.name}",
                    "second": f"{second.residue.chain.id}:{second.residue.id}:{second.residue.name}",
                }
            )
    return bonds


def total_charge_e(forcefield: app.ForceField, topology: app.Topology) -> int:
    system = forcefield.createSystem(topology, nonbondedMethod=app.NoCutoff, constraints=None)
    nonbonded = next(
        force for force in system.getForces() if isinstance(force, openmm.NonbondedForce)
    )
    charge = sum(
        nonbonded.getParticleParameters(index)[0].value_in_unit(unit.elementary_charge)
        for index in range(nonbonded.getNumParticles())
    )
    rounded = round(charge)
    if abs(charge - rounded) > 1e-4:
        raise RuntimeError(f"Prepared protein has nonintegral total charge: {charge}")
    return int(rounded)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["quick", "teaching"], default="quick")
    args = parser.parse_args()
    cfg = resolve_config(2, args.profile)
    random.seed(int(cfg["seed"]))
    run = create_run(2, args.profile, cfg)

    input_path = ROOT / "inputs" / "phase02" / f"{cfg['pdb_id']}.pdb"
    provenance = download(cfg["source_url"], input_path)
    source_records = source_record_audit(input_path)
    manifest = read_json(run / "manifest.json")
    manifest["inputs"]["pdb"] = provenance
    write_json(run / "manifest.json", manifest)

    fixer = PDBFixer(filename=str(input_path))
    fixer.platform = openmm.Platform.getPlatformByName("Reference")
    original = topology_summary(fixer.topology)
    fixer.findMissingResidues()
    missing_residues = {str(k): v for k, v in fixer.missingResidues.items()}
    if missing_residues:
        raise RuntimeError(f"Tutorial 1UBQ unexpectedly reports missing residues: {missing_residues}")
    fixer.findNonstandardResidues()
    nonstandard = [(r.name, r.id, replacement) for r, replacement in fixer.nonstandardResidues]
    if nonstandard:
        raise RuntimeError(f"Tutorial 1UBQ unexpectedly contains nonstandard residues: {nonstandard}")
    fixer.removeHeterogens(keepWater=False)
    fixer.findMissingAtoms()
    missing_atoms = {
        f"{res.chain.id}:{res.id}:{res.name}": [a.name for a in atoms]
        for res, atoms in fixer.missingAtoms.items()
    }
    fixer.addMissingAtoms(seed=int(cfg["seed"]))
    fixer.addMissingHydrogens(float(cfg["ph"]))

    forcefield = create_forcefield(cfg)
    charge_before_ions = total_charge_e(forcefield, fixer.topology)
    disulfides = disulfide_bonds(fixer.topology)
    modeller = app.Modeller(fixer.topology, fixer.positions)
    modeller.addSolvent(
        forcefield,
        model=str(cfg["water_model"]),
        padding=float(cfg["padding_nm"]) * unit.nanometer,
        ionicStrength=float(cfg["ionic_strength_molar"]) * unit.molar,
        positiveIon=str(cfg["positive_ion"]),
        negativeIon=str(cfg["negative_ion"]),
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
    retained_heterogens = {
        name: count
        for name, count in residue_counts.items()
        if name not in STANDARD_AA | WATER_NAMES | ION_NAMES
    }
    with (run / "prepared" / "system.pdb").open("w", encoding="utf-8") as handle:
        app.PDBFile.writeFile(modeller.topology, modeller.positions, handle, keepIds=True)
    write_json(run / "prepared" / "preparation_audit.json", {
        "pdb_id": cfg["pdb_id"],
        "preparation_seed": int(cfg["seed"]),
        "hydrogen_placement_platform": "Reference",
        "ph": cfg["ph"],
        "original_topology": original,
        "missing_residues": missing_residues,
        "nonstandard_residues": nonstandard,
        "missing_atoms_added": missing_atoms,
        "alternate_locations": source_records["alternate_location_atom_counts"],
        "original_heterogen_atoms": source_records["heterogen_atom_counts"],
        "heterogen_policy": "remove all crystallographic heterogens and waters for controlled tutorial",
        "retained_heterogens": retained_heterogens,
        "disulfide_bonds": disulfides,
        "total_charge_before_ions_e": charge_before_ions,
        "total_charge_method": "sum of force-field partial charges after adding pH 7 hydrogens",
        "prepared_topology": prepared,
        "water_molecules": water_count,
        "ion_residue_counts": ion_counts,
        "periodic_box_vectors_nm": box_vectors_nm,
        "periodic_box_lengths_nm": box_lengths_nm,
        "forcefields": [cfg["protein_forcefield"], cfg["water_forcefield"]],
        "water_model": cfg["water_model"],
        "ionic_strength_molar": cfg["ionic_strength_molar"],
    })
    run_staged_simulation(run, modeller.topology, modeller.positions, forcefield, cfg, membrane=False)
    print(run)


if __name__ == "__main__":
    main()
