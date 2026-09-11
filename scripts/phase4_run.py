#!/usr/bin/env python
from __future__ import annotations

import argparse
from collections import Counter
import math
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import openmm
from openmm import app, unit
from openmm.app import modeller as modeller_module
from pdbfixer import PDBFixer
from scipy.spatial import cKDTree

from mdlab.biomolecular import (
    ION_NAMES,
    STANDARD_AA,
    WATER_NAMES,
    create_forcefield,
    create_system,
    run_staged_simulation,
    topology_summary,
)
from mdlab.core import (
    create_run,
    download,
    finish_manifest,
    read_json,
    resolve_config,
    write_json,
)


def source_record_audit(path: Path) -> dict[str, Any]:
    alternate_locations: Counter[str] = Counter()
    heterogen_atoms: Counter[str] = Counter()
    ssbond_records: list[str] = []
    cryst1_record = None
    opm_half_thickness_angstrom = None
    for line in path.read_text(encoding="utf-8").splitlines():
        record = line[:6].strip()
        if record in {"ATOM", "HETATM"}:
            alternate_location = line[16:17].strip()
            if alternate_location:
                alternate_locations[alternate_location] += 1
            if record == "HETATM":
                heterogen_atoms[line[17:20].strip()] += 1
        elif record == "SSBOND":
            ssbond_records.append(line.rstrip())
        elif record == "CRYST1":
            cryst1_record = line.rstrip()
        elif (
            line.startswith("REMARK")
            and "1/2 of bilayer thickness:" in line
        ):
            opm_half_thickness_angstrom = float(line.rsplit(":", 1)[1])
    return {
        "alternate_location_atom_counts": dict(
            sorted(alternate_locations.items())
        ),
        "heterogen_atom_counts": dict(sorted(heterogen_atoms.items())),
        "ssbond_records": ssbond_records,
        "cryst1_record": cryst1_record,
        "opm_half_thickness_angstrom": opm_half_thickness_angstrom,
    }


def protein_chain_summary(topology: app.Topology) -> list[dict[str, Any]]:
    result = []
    for chain in topology.chains():
        residues = [
            residue
            for residue in chain.residues()
            if residue.name in STANDARD_AA
        ]
        if residues:
            result.append(
                {
                    "chain_id": chain.id,
                    "residue_count": len(residues),
                    "first_residue": f"{residues[0].name}{residues[0].id}",
                    "last_residue": f"{residues[-1].name}{residues[-1].id}",
                }
            )
    return result


def disulfide_bonds(topology: app.Topology) -> list[dict[str, str]]:
    result = []
    for first, second in topology.bonds():
        if first.name == second.name == "SG":
            result.append(
                {
                    "first": (
                        f"{first.residue.chain.id}:"
                        f"{first.residue.id}:{first.residue.name}"
                    ),
                    "second": (
                        f"{second.residue.chain.id}:"
                        f"{second.residue.id}:{second.residue.name}"
                    ),
                }
            )
    return result


def total_charge_e(
    forcefield: app.ForceField,
    topology: app.Topology,
) -> int:
    system = forcefield.createSystem(
        topology,
        nonbondedMethod=app.NoCutoff,
        constraints=None,
    )
    nonbonded = next(
        force
        for force in system.getForces()
        if isinstance(force, openmm.NonbondedForce)
    )
    charge = sum(
        nonbonded.getParticleParameters(index)[0].value_in_unit(
            unit.elementary_charge
        )
        for index in range(nonbonded.getNumParticles())
    )
    rounded = round(charge)
    if abs(charge - rounded) > 1e-4:
        raise RuntimeError(
            f"Protein/source-water system has nonintegral charge: {charge}"
        )
    return int(rounded)


def add_membrane_with_seed(
    modeller: app.Modeller,
    forcefield: app.ForceField,
    cfg: dict[str, Any],
) -> None:
    original_integrator = modeller_module.LangevinIntegrator
    platform = openmm.Platform.getPlatformByName(
        str(cfg["preparation_platform"])
    )
    original_platform_defaults = {
        name: platform.getPropertyDefaultValue(name)
        for name in platform.getPropertyNames()
    }
    if platform.getName() == "CPU":
        platform.setPropertyDefaultValue(
            "Threads",
            str(int(cfg["preparation_cpu_threads"])),
        )
        platform.setPropertyDefaultValue(
            "DeterministicForces",
            (
                "true"
                if bool(cfg["preparation_deterministic_forces"])
                else "false"
            ),
        )

    def seeded_integrator(*args, **kwargs):
        integrator = original_integrator(*args, **kwargs)
        integrator.setRandomNumberSeed(int(cfg["seed"]))
        return integrator

    modeller_module.LangevinIntegrator = seeded_integrator
    try:
        modeller.addMembrane(
            forcefield,
            lipidType=str(cfg["lipid_type"]),
            membraneCenterZ=0.0 * unit.nanometer,
            minimumPadding=float(cfg["minimum_padding_nm"]) * unit.nanometer,
            positiveIon=str(cfg["positive_ion"]),
            negativeIon=str(cfg["negative_ion"]),
            ionicStrength=float(cfg["ionic_strength_molar"]) * unit.molar,
            neutralize=True,
            platform=platform,
        )
    finally:
        modeller_module.LangevinIntegrator = original_integrator
        for name, value in original_platform_defaults.items():
            platform.setPropertyDefaultValue(name, value)


def periodic_box_lengths_nm(topology: app.Topology) -> tuple[list, list]:
    vectors = topology.getPeriodicBoxVectors()
    if vectors is None:
        raise RuntimeError("Membrane builder did not create periodic box vectors")
    vectors_nm = [
        list(vector.value_in_unit(unit.nanometer)) for vector in vectors
    ]
    matrix = np.asarray(vectors_nm, dtype=float)
    off_diagonal = matrix - np.diag(np.diag(matrix))
    if not np.allclose(off_diagonal, 0.0, atol=1e-8):
        raise RuntimeError(
            f"Expected an orthorhombic membrane box, found {vectors_nm}"
        )
    lengths = [
        math.sqrt(sum(component**2 for component in vector))
        for vector in vectors_nm
    ]
    return vectors_nm, lengths


def minimum_periodic_distance_nm(
    positions_nm: np.ndarray,
    first_indices: list[int],
    second_indices: list[int],
    box_lengths_nm: list[float],
) -> float:
    if not first_indices or not second_indices:
        raise RuntimeError("Cannot measure distance between empty components")
    box = np.asarray(box_lengths_nm, dtype=float)
    first = np.mod(positions_nm[first_indices], box)
    second = np.mod(positions_nm[second_indices], box)
    distances, _ = cKDTree(second, boxsize=box).query(first, k=1)
    return float(np.min(distances))


def execute_phase(run: Path, cfg: dict[str, Any]) -> None:
    input_path = (
        ROOT
        / "inputs"
        / "phase04"
        / f"{cfg['pdb_id']}_opm.pdb"
    )
    provenance = download(cfg["opm_pdb_url"], input_path)
    source_records = source_record_audit(input_path)
    manifest = read_json(run / "manifest.json")
    manifest["inputs"]["opm_pdb"] = provenance
    manifest["inputs"]["opm_metadata_reference"] = cfg["opm_metadata_url"]
    write_json(run / "manifest.json", manifest)

    fixer = PDBFixer(filename=str(input_path))
    fixer.platform = openmm.Platform.getPlatformByName("Reference")
    original = topology_summary(fixer.topology)
    original_chains = protein_chain_summary(fixer.topology)
    crystal_vectors = fixer.topology.getPeriodicBoxVectors()
    crystal_vectors_nm = (
        [
            list(vector.value_in_unit(unit.nanometer))
            for vector in crystal_vectors
        ]
        if crystal_vectors is not None
        else None
    )

    expected_chains = int(cfg["expected_protein_chains"])
    expected_residues = int(cfg["expected_residues_per_chain"])
    if len(original_chains) != expected_chains or any(
        chain["residue_count"] != expected_residues
        for chain in original_chains
    ):
        raise RuntimeError(
            "OPM input does not contain the expected complete AQP1 tetramer: "
            f"{original_chains}"
        )

    fixer.findMissingResidues()
    missing_residues = {
        str(key): names for key, names in fixer.missingResidues.items()
    }
    if missing_residues:
        raise RuntimeError(
            "OPM 1J4N unexpectedly reports missing residues and requires "
            f"human review: {missing_residues}"
        )
    fixer.findNonstandardResidues()
    nonstandard = [
        (residue.name, residue.id, replacement)
        for residue, replacement in fixer.nonstandardResidues
    ]
    if nonstandard:
        raise RuntimeError(
            f"Unexpected nonstandard protein residues: {nonstandard}"
        )

    fixer.removeHeterogens(keepWater=bool(cfg["retain_source_waters"]))
    topology_after_policy = topology_summary(fixer.topology)
    retained_before_repair = sum(
        topology_after_policy["residue_counts"].get(name, 0)
        for name in WATER_NAMES
    )
    if retained_before_repair != int(cfg["expected_source_waters"]):
        raise RuntimeError(
            "DR-002 source-water count mismatch: "
            f"expected {cfg['expected_source_waters']}, "
            f"found {retained_before_repair}"
        )
    unexpected_after_policy = {
        name: count
        for name, count in topology_after_policy["residue_counts"].items()
        if name not in STANDARD_AA | WATER_NAMES
    }
    if unexpected_after_policy:
        raise RuntimeError(
            "Unexpected heterogens remain after the DR-002 policy: "
            f"{unexpected_after_policy}"
        )

    # OPM's CRYST1 is a source crystal cell, not the simulation membrane box.
    fixer.topology.setPeriodicBoxVectors(None)
    fixer.findMissingAtoms()
    missing_atoms = {
        f"{residue.chain.id}:{residue.id}:{residue.name}": [
            atom.name for atom in atoms
        ]
        for residue, atoms in fixer.missingAtoms.items()
        if residue.name in STANDARD_AA
    }
    missing_terminals = {
        f"{residue.chain.id}:{residue.id}:{residue.name}": list(atoms)
        for residue, atoms in fixer.missingTerminals.items()
        if residue.name in STANDARD_AA
    }
    fixer.missingAtoms = {
        residue: atoms
        for residue, atoms in fixer.missingAtoms.items()
        if residue.name in STANDARD_AA
    }
    fixer.missingTerminals = {
        residue: atoms
        for residue, atoms in fixer.missingTerminals.items()
        if residue.name in STANDARD_AA
    }
    fixer.addMissingAtoms(seed=int(cfg["seed"]))
    fixer.addMissingHydrogens(float(cfg["ph"]))

    repaired_chains = protein_chain_summary(fixer.topology)
    source_water_oxygens = [
        atom
        for residue in fixer.topology.residues()
        if residue.name in WATER_NAMES
        for atom in residue.atoms()
        if atom.element == app.element.oxygen
    ]
    if len(source_water_oxygens) != int(cfg["expected_source_waters"]):
        raise RuntimeError(
            "Hydrogen repair changed the approved source-water count: "
            f"{len(source_water_oxygens)}"
        )
    source_water_oxygen_indices = [
        atom.index for atom in source_water_oxygens
    ]
    source_water_residues = [
        (
            f"{atom.residue.chain.id}:{atom.residue.id}:"
            f"{atom.residue.name}"
        )
        for atom in source_water_oxygens
    ]

    forcefield = create_forcefield(cfg, include_lipid=True)
    charge_before_ions = total_charge_e(forcefield, fixer.topology)
    source_disulfides = disulfide_bonds(fixer.topology)
    modeller = app.Modeller(fixer.topology, fixer.positions)
    add_membrane_with_seed(modeller, forcefield, cfg)

    prepared = topology_summary(modeller.topology)
    prepared_chains = protein_chain_summary(modeller.topology)
    if prepared_chains != repaired_chains:
        raise RuntimeError(
            "Membrane construction changed the protein chain topology"
        )
    prepared_atoms = list(modeller.topology.atoms())
    for index in source_water_oxygen_indices:
        atom = prepared_atoms[index]
        if (
            atom.residue.name not in WATER_NAMES
            or atom.element != app.element.oxygen
        ):
            raise RuntimeError(
                "Membrane construction did not preserve source-water atom "
                f"index {index}"
            )

    lipid_resname = str(cfg["lipid_resname"])
    lipid_residues = [
        residue
        for residue in modeller.topology.residues()
        if residue.name == lipid_resname
    ]
    lipid_phosphorus = []
    for residue in lipid_residues:
        phosphorus = [
            atom for atom in residue.atoms() if atom.name == "P"
        ]
        if len(phosphorus) != 1:
            raise RuntimeError(
                f"Expected one phosphorus atom in {residue}, "
                f"found {len(phosphorus)}"
            )
        lipid_phosphorus.append(phosphorus[0])
    if len(lipid_residues) < 20:
        raise RuntimeError(
            "Membrane builder produced implausible POPC count: "
            f"{len(lipid_residues)}"
        )

    positions_nm = np.asarray(
        modeller.positions.value_in_unit(unit.nanometer),
        dtype=float,
    )
    upper_lipids = sum(
        positions_nm[atom.index, 2] >= 0.0
        for atom in lipid_phosphorus
    )
    lower_lipids = len(lipid_phosphorus) - upper_lipids
    box_vectors_nm, box_lengths_nm = periodic_box_lengths_nm(
        modeller.topology
    )

    residue_counts = prepared["residue_counts"]
    water_count = sum(
        residue_counts.get(name, 0) for name in WATER_NAMES
    )
    new_water_count = water_count - int(cfg["expected_source_waters"])
    if new_water_count <= 0:
        raise RuntimeError("Membrane builder did not add bulk water")
    ion_counts = {
        name: count
        for name, count in residue_counts.items()
        if name in ION_NAMES and count
    }
    retained_heterogens = {
        name: count
        for name, count in residue_counts.items()
        if name
        not in STANDARD_AA
        | WATER_NAMES
        | ION_NAMES
        | {lipid_resname}
    }
    if retained_heterogens:
        raise RuntimeError(
            f"Unexpected prepared heterogens: {retained_heterogens}"
        )

    protein_heavy = [
        atom.index
        for atom in modeller.topology.atoms()
        if (
            atom.residue.name in STANDARD_AA
            and atom.element is not None
            and atom.element != app.element.hydrogen
        )
    ]
    lipid_heavy = [
        atom.index
        for atom in modeller.topology.atoms()
        if (
            atom.residue.name == lipid_resname
            and atom.element is not None
            and atom.element != app.element.hydrogen
        )
    ]
    all_water_oxygens = [
        atom.index
        for atom in modeller.topology.atoms()
        if (
            atom.residue.name in WATER_NAMES
            and atom.element == app.element.oxygen
        )
    ]
    source_index_set = set(source_water_oxygen_indices)
    new_water_oxygens = [
        index
        for index in all_water_oxygens
        if index not in source_index_set
    ]
    component_distances = {
        "protein_to_lipid_heavy_nm": minimum_periodic_distance_nm(
            positions_nm,
            protein_heavy,
            lipid_heavy,
            box_lengths_nm,
        ),
        "source_water_oxygen_to_lipid_heavy_nm": (
            minimum_periodic_distance_nm(
                positions_nm,
                source_water_oxygen_indices,
                lipid_heavy,
                box_lengths_nm,
            )
        ),
        "source_to_new_water_oxygen_nm": minimum_periodic_distance_nm(
            positions_nm,
            source_water_oxygen_indices,
            new_water_oxygens,
            box_lengths_nm,
        ),
    }
    minimum_intercomponent = min(component_distances.values())
    threshold = float(
        cfg["gates"]["minimum_intercomponent_heavy_atom_distance_nm"]
    )
    if minimum_intercomponent < threshold:
        raise RuntimeError(
            "Prepared membrane has an impossible inter-component heavy-atom "
            f"distance ({minimum_intercomponent:.4f} nm < {threshold:.4f} nm)"
        )

    parameterized_system = create_system(
        forcefield,
        modeller.topology,
        cfg,
    )
    parameterized_particles = parameterized_system.getNumParticles()
    if parameterized_particles != prepared["atoms"]:
        raise RuntimeError(
            "Force-field particle count does not match prepared atoms: "
            f"{parameterized_particles} != {prepared['atoms']}"
        )
    del parameterized_system

    system_path = run / "prepared" / "system.pdb"
    with system_path.open("w", encoding="utf-8") as handle:
        app.PDBFile.writeFile(
            modeller.topology,
            modeller.positions,
            handle,
            keepIds=True,
        )
    write_json(
        run / "prepared" / "preparation_audit.json",
        {
            "pdb_id": cfg["pdb_id"],
            "orientation_source": "OPM",
            "opm_download_url": cfg["opm_pdb_url"],
            "opm_metadata_reference": cfg["opm_metadata_url"],
            "opm_hydrophobic_thickness_nm": (
                2.0
                * float(source_records["opm_half_thickness_angstrom"])
                / 10.0
            ),
            "membrane_normal_axis": "Z",
            "assembly_type": (
                "OPM-oriented biological assembly; expected AQP1 tetramer"
            ),
            "preparation_seed": int(cfg["seed"]),
            "preparation_platform": cfg["preparation_platform"],
            "preparation_cpu_threads": int(
                cfg["preparation_cpu_threads"]
            ),
            "preparation_deterministic_forces": bool(
                cfg["preparation_deterministic_forces"]
            ),
            "membrane_builder_integrator_seed": int(cfg["seed"]),
            "ph": float(cfg["ph"]),
            "source_record_audit": source_records,
            "source_crystal_box_vectors_nm": crystal_vectors_nm,
            "source_crystal_box_reused": False,
            "original_topology_including_opm_markers": original,
            "original_protein_chains": original_chains,
            "missing_residues": missing_residues,
            "nonstandard_residues": nonstandard,
            "missing_atoms_added": missing_atoms,
            "missing_terminal_atoms_added": missing_terminals,
            "disulfide_bonds_from_source_topology": source_disulfides,
            "heterogen_policy": (
                "DR-002 Option A: remove DUM and BNG; retain all 371 "
                "source HOH residues"
            ),
            "approved_source_water_count": int(
                cfg["expected_source_waters"]
            ),
            "retained_source_water_residues": source_water_residues,
            "retained_source_water_oxygen_indices": (
                source_water_oxygen_indices
            ),
            "source_water_identity_reference": provenance["sha256"],
            "total_charge_before_ions_e": charge_before_ions,
            "prepared_topology": prepared,
            "prepared_protein_chains": prepared_chains,
            "lipid_type": cfg["lipid_type"],
            "lipid_resname": lipid_resname,
            "lipid_count": len(lipid_residues),
            "lipid_count_upper_leaflet": int(upper_lipids),
            "lipid_count_lower_leaflet": int(lower_lipids),
            "water_molecules_total": water_count,
            "water_molecules_source": int(cfg["expected_source_waters"]),
            "water_molecules_added": new_water_count,
            "ion_residue_counts": ion_counts,
            "periodic_box_vectors_nm": box_vectors_nm,
            "periodic_box_lengths_nm": box_lengths_nm,
            "intercomponent_minimum_heavy_atom_distances": (
                component_distances
            ),
            "minimum_intercomponent_heavy_atom_distance_nm": (
                minimum_intercomponent
            ),
            "parameterization": {
                "status": "PASS",
                "parameterized_particles": parameterized_particles,
                "unassigned_parameter_exception": None,
            },
            "forcefields": [
                cfg["protein_forcefield"],
                cfg["lipid_forcefield"],
                cfg["water_forcefield"],
            ],
            "water_model": cfg["water_model"],
            "ionic_strength_molar": cfg["ionic_strength_molar"],
        },
    )
    run_staged_simulation(
        run,
        modeller.topology,
        modeller.positions,
        forcefield,
        cfg,
        membrane=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=["quick", "teaching"],
        default="quick",
    )
    args = parser.parse_args()
    cfg = resolve_config(4, args.profile)
    random.seed(int(cfg["seed"]))
    run = create_run(4, args.profile, cfg)
    try:
        execute_phase(run, cfg)
    except Exception as error:
        (run / "FAILURE.md").write_text(
            "# Phase 4 failure\n\n"
            f"First reported exception: `{type(error).__name__}: {error}`\n",
            encoding="utf-8",
        )
        finish_manifest(
            run,
            "SIMULATION_FAILED",
            {
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        raise
    print(run)


if __name__ == "__main__":
    main()
