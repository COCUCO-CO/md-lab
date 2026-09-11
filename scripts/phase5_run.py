#!/usr/bin/env python
# ruff: noqa: E402
from __future__ import annotations

import argparse
from collections import Counter
import csv
import math
import os
from pathlib import Path
import random
import subprocess
import sys
from typing import Any
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mdlab-mpl-cache")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/mdlab-cache")

from Bio.PDB.MMCIF2Dict import MMCIF2Dict
import numpy as np
import openmm
from openff.toolkit import Molecule
from openff.units import unit as off_unit
from openmm import app, unit
from openmm.app import modeller as modeller_module
from openmmforcefields.generators import SMIRNOFFTemplateGenerator
from pdbfixer import PDBFixer
from rdkit import Chem
from rdkit.Chem import AllChem, Draw, rdMolDescriptors
from scipy.spatial import cKDTree

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
    finish_manifest,
    read_json,
    resolve_config,
    sha256_file,
    utc_now,
    write_json,
)


IONIZABLE_NAMES = {"ASP", "GLU", "HIS", "LYS", "ARG"}
EXPECTED_DISULFIDES = {frozenset((148, 227)), frozenset((349, 353))}


def set_progress(profile: str, state: str) -> None:
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "labctl.py"),
            "set",
            "5",
            profile,
            state,
        ],
        check=True,
    )


def validate_decision_record(path: Path, required_decisions: list[str]) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if "- Status: APPROVED" not in text:
        raise RuntimeError(f"Phase 5 decision record is not approved: {path}")
    if "- Human approval name/date:" not in text or "- Approval statement:" not in text:
        raise RuntimeError("Approved decision record lacks reviewer evidence")
    missing = [key for key in required_decisions if f"`{key}`" not in text]
    if missing:
        raise RuntimeError(f"Decision record lacks required decisions: {missing}")
    return {
        "path": str(path.relative_to(ROOT)),
        "sha256": sha256_file(path),
        "status": "APPROVED",
    }


def verified_input_record(path: Path) -> dict[str, Any]:
    provenance_path = path.with_name(f"{path.name}.provenance.json")
    if not path.exists() or not provenance_path.exists():
        raise FileNotFoundError(f"Immutable input or provenance is missing: {path}")
    provenance = read_json(provenance_path)
    actual_hash = sha256_file(path)
    if provenance["sha256"] != actual_hash:
        raise RuntimeError(f"Immutable input hash mismatch: {path}")
    if int(provenance["bytes"]) != path.stat().st_size:
        raise RuntimeError(f"Immutable input size mismatch: {path}")
    return provenance


def source_record_audit(path: Path) -> dict[str, Any]:
    alternate_locations: Counter[str] = Counter()
    heterogen_residues: Counter[str] = Counter()
    heterogen_keys: set[tuple[str, str, str]] = set()
    ssbond_records: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        record = line[:6].strip()
        if record in {"ATOM", "HETATM"}:
            alternate_location = line[16:17].strip()
            if alternate_location:
                alternate_locations[alternate_location] += 1
            if record == "HETATM":
                key = (
                    line[21:22].strip(),
                    line[22:26].strip(),
                    line[17:20].strip(),
                )
                if key not in heterogen_keys:
                    heterogen_keys.add(key)
                    heterogen_residues[key[2]] += 1
        elif record == "SSBOND":
            ssbond_records.append(line.rstrip())
    return {
        "alternate_location_atom_counts": dict(sorted(alternate_locations.items())),
        "heterogen_residue_counts": dict(sorted(heterogen_residues.items())),
        "ssbond_records": ssbond_records,
    }


def cif_component_atom_records(cif_path: Path, resname: str) -> list[dict[str, str]]:
    data = MMCIF2Dict(str(cif_path))
    records = [
        {"name": name, "element": element}
        for component, name, element in zip(
            data["_chem_comp_atom.comp_id"],
            data["_chem_comp_atom.atom_id"],
            data["_chem_comp_atom.type_symbol"],
        )
        if component == resname
    ]
    if not records:
        raise RuntimeError(f"No _chem_comp_atom records for {resname} in {cif_path}")
    return records


def protonate_ligand(
    sdf_path: Path,
    cif_path: Path,
    resname: str,
    protonation_atom: str,
) -> tuple[Chem.Mol, list[str], list[dict[str, str]]]:
    molecule = Chem.MolFromMolFile(str(sdf_path), removeHs=False, sanitize=True)
    if molecule is None:
        raise RuntimeError(f"RDKit could not parse {sdf_path}")
    records = cif_component_atom_records(cif_path, resname)
    if len(records) != molecule.GetNumAtoms():
        raise RuntimeError(
            f"{resname} CCD atom count mismatch: CIF={len(records)}, "
            f"SDF={molecule.GetNumAtoms()}"
        )
    for index, (record, atom) in enumerate(zip(records, molecule.GetAtoms())):
        if record["element"].upper() != atom.GetSymbol().upper():
            raise RuntimeError(
                f"{resname} CIF/SDF element mismatch at atom {index + 1}"
            )
    names = [record["name"] for record in records]
    if len(names) != len(set(names)) or protonation_atom not in names:
        raise RuntimeError(f"Invalid CCD atom-name mapping for {resname}")

    site_index = names.index(protonation_atom)
    editable = Chem.RWMol(molecule)
    site = editable.GetAtomWithIdx(site_index)
    if site.GetAtomicNum() != 7 or site.GetDegree() != 3:
        raise RuntimeError(
            f"Approved protonation site {resname}:{protonation_atom} "
            "is not a three-coordinate nitrogen"
        )
    site.SetFormalCharge(1)
    site.SetNoImplicit(False)
    protonated_core = editable.GetMol()
    Chem.SanitizeMol(protonated_core)
    protonated = Chem.AddHs(
        protonated_core,
        addCoords=True,
        onlyOnAtoms=[site_index],
    )
    if protonated.GetNumAtoms() != molecule.GetNumAtoms() + 1:
        raise RuntimeError(f"Protonating {resname} did not add exactly one atom")
    extra_name = "HP"
    if extra_name in names:
        raise RuntimeError(f"Generated hydrogen name collides in {resname}")
    names.append(extra_name)
    if Chem.GetFormalCharge(protonated) != 1:
        raise RuntimeError(f"Protonated {resname} does not have formal charge +1")
    proton_neighbors = [
        neighbor.GetIdx()
        for neighbor in protonated.GetAtomWithIdx(site_index).GetNeighbors()
        if neighbor.GetAtomicNum() == 1
    ]
    if len(proton_neighbors) != 1 or proton_neighbors[0] != protonated.GetNumAtoms() - 1:
        raise RuntimeError(f"Generated proton mapping is ambiguous for {resname}")
    return protonated, names, records


def validate_pose_mapping(
    molecule: Chem.Mol,
    ccd_records: list[dict[str, str]],
    ligand_residue: app.Topology.Residue,
    topology: app.Topology,
) -> list[dict[str, Any]]:
    heavy_records = [
        (index, record)
        for index, record in enumerate(ccd_records)
        if record["element"].upper() != "H"
    ]
    pose_atoms = list(ligand_residue.atoms())
    if len(pose_atoms) != len(heavy_records):
        raise RuntimeError(
            f"{ligand_residue.name} pose/CCD heavy-atom mismatch: "
            f"{len(pose_atoms)} != {len(heavy_records)}"
        )
    mapping = []
    pose_name_to_sdf: dict[str, int] = {}
    for pose_atom, (sdf_index, record) in zip(pose_atoms, heavy_records):
        pose_element = (
            pose_atom.element.symbol.upper() if pose_atom.element is not None else None
        )
        if pose_atom.name != record["name"] or pose_element != record["element"].upper():
            raise RuntimeError(
                f"Ambiguous {ligand_residue.name} pose mapping at {pose_atom.name}"
            )
        pose_name_to_sdf[pose_atom.name] = sdf_index
        mapping.append(
            {
                "pose_atom_name": pose_atom.name,
                "element": pose_element,
                "sdf_atom_index": sdf_index + 1,
            }
        )

    pose_atom_set = set(pose_atoms)
    pose_edges = {
        tuple(sorted((pose_name_to_sdf[first.name], pose_name_to_sdf[second.name])))
        for first, second in topology.bonds()
        if first in pose_atom_set and second in pose_atom_set
    }
    heavy_indices = {index for index, _ in heavy_records}
    sdf_edges = {
        tuple(sorted((bond.GetBeginAtomIdx(), bond.GetEndAtomIdx())))
        for bond in molecule.GetBonds()
        if bond.GetBeginAtomIdx() in heavy_indices
        and bond.GetEndAtomIdx() in heavy_indices
    }
    if pose_edges != sdf_edges:
        raise RuntimeError(
            f"{ligand_residue.name} heavy-atom graph differs between pose and CCD SDF"
        )
    return mapping


def hydrogen_parent_mapping(molecule: Chem.Mol, atom_names: list[str]) -> dict[str, str]:
    if molecule.GetNumAtoms() != len(atom_names):
        raise RuntimeError("Ligand atom-name list does not match molecule")
    mapping = {}
    for atom in molecule.GetAtoms():
        if atom.GetAtomicNum() != 1:
            continue
        neighbors = list(atom.GetNeighbors())
        if len(neighbors) != 1 or neighbors[0].GetAtomicNum() == 1:
            raise RuntimeError("Ligand SDF contains an invalid hydrogen attachment")
        mapping[atom_names[atom.GetIdx()]] = atom_names[neighbors[0].GetIdx()]
    return mapping


def write_hydrogen_definitions(
    path: Path,
    resname: str,
    mapping: dict[str, str],
) -> None:
    root = ET.Element("Residues")
    residue = ET.SubElement(root, "Residue", {"name": resname})
    for hydrogen, parent in mapping.items():
        ET.SubElement(residue, "H", {"name": hydrogen, "parent": parent})
    ET.indent(root)
    ET.ElementTree(root).write(path, encoding="unicode", xml_declaration=False)


def write_ligand_outputs(
    prepared_dir: Path,
    molecule: Chem.Mol,
    atom_names: list[str],
    ligand: Molecule,
    condition: dict[str, Any],
) -> dict[str, Any]:
    resname = str(condition["ligand_resname"])
    for atom, name in zip(ligand.atoms, atom_names):
        atom.name = name
    ligand.assign_partial_charges(
        partial_charge_method=str(condition["partial_charge_method"])
    )
    charges = ligand.partial_charges.m_as(off_unit.elementary_charge)
    if abs(float(np.sum(charges)) - float(condition["ligand_formal_charge"])) > 1e-6:
        raise RuntimeError(f"{resname} AM1-BCC charges do not sum to +1")

    protonated_sdf = prepared_dir / f"{resname}_protonated_plus1.sdf"
    writer = Chem.SDWriter(str(protonated_sdf))
    molecule.SetProp("_Name", f"{condition['ligand_name']} protonated +1")
    molecule.SetProp("ATOM_NAMES", " ".join(atom_names))
    molecule.SetProp("FORMAL_CHARGE", "+1")
    writer.write(molecule)
    writer.close()

    depiction_molecule = Chem.RemoveHs(Chem.Mol(molecule))
    AllChem.Compute2DCoords(depiction_molecule)
    depiction_path = prepared_dir / f"{resname}_protonated_plus1.png"
    Draw.MolToFile(depiction_molecule, str(depiction_path), size=(900, 650))

    charge_table_path = prepared_dir / f"{resname}_am1bcc_charges.csv"
    with charge_table_path.open("w", encoding="utf-8", newline="") as handle:
        writer_csv = csv.DictWriter(
            handle,
            fieldnames=["atom_index", "atom_name", "element", "partial_charge_e"],
        )
        writer_csv.writeheader()
        for index, (atom, name, charge) in enumerate(
            zip(molecule.GetAtoms(), atom_names, charges),
            start=1,
        ):
            writer_csv.writerow(
                {
                    "atom_index": index,
                    "atom_name": name,
                    "element": atom.GetSymbol(),
                    "partial_charge_e": f"{float(charge):.10f}",
                }
            )

    identity = {
        "resname": resname,
        "name": condition["ligand_name"],
        "protonation_atom": condition["ligand_protonation_atom"],
        "formal_charge": Chem.GetFormalCharge(molecule),
        "formula": rdMolDescriptors.CalcMolFormula(molecule),
        "isomeric_smiles": Chem.MolToSmiles(molecule, isomericSmiles=True),
        "atoms_including_hydrogen": molecule.GetNumAtoms(),
        "bonds": molecule.GetNumBonds(),
        "am1bcc_charge_sum_e": float(np.sum(charges)),
        "am1bcc_charge_min_e": float(np.min(charges)),
        "am1bcc_charge_max_e": float(np.max(charges)),
        "protonated_sdf": protonated_sdf.name,
        "protonated_sdf_sha256": sha256_file(protonated_sdf),
        "depiction": depiction_path.name,
        "charge_table": charge_table_path.name,
    }
    write_json(prepared_dir / "ligand_identity.json", identity)
    return identity


def add_membrane_with_seed(
    modeller: app.Modeller,
    forcefield: app.ForceField,
    cfg: dict[str, Any],
) -> None:
    original_integrator = modeller_module.LangevinIntegrator
    platform = openmm.Platform.getPlatformByName(str(cfg["preparation_platform"]))
    original_defaults = {
        name: platform.getPropertyDefaultValue(name)
        for name in platform.getPropertyNames()
    }
    if platform.getName() == "CPU":
        platform.setPropertyDefaultValue(
            "Threads", str(int(cfg["preparation_cpu_threads"]))
        )
        platform.setPropertyDefaultValue(
            "DeterministicForces",
            "true" if bool(cfg["preparation_deterministic_forces"]) else "false",
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
        for name, value in original_defaults.items():
            platform.setPropertyDefaultValue(name, value)


def residue_by_id(topology: app.Topology, residue_id: int) -> app.Topology.Residue:
    matches = [
        residue
        for residue in topology.residues()
        if residue.name in STANDARD_AA and int(residue.id) == residue_id
    ]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one protein residue {residue_id}, found {len(matches)}")
    return matches[0]


def disulfide_pairs(topology: app.Topology) -> set[frozenset[int]]:
    pairs = set()
    for first, second in topology.bonds():
        if first.name == second.name == "SG":
            pairs.add(frozenset((int(first.residue.id), int(second.residue.id))))
    return pairs


def transmembrane_residue_ids(ranges: list[list[int]]) -> list[int]:
    return [
        residue_id
        for start, end in ranges
        for residue_id in range(int(start), int(end) + 1)
    ]


def ca_positions_by_id(
    topology: app.Topology,
    positions,
    residue_ids: list[int],
) -> dict[int, np.ndarray]:
    requested = set(residue_ids)
    positions_nm = np.asarray(positions.value_in_unit(unit.nanometer), dtype=float)
    result = {}
    for residue in topology.residues():
        if residue.name not in STANDARD_AA:
            continue
        residue_id = int(residue.id)
        if residue_id not in requested:
            continue
        ca = [atom for atom in residue.atoms() if atom.name == "CA"]
        if len(ca) == 1:
            result[residue_id] = positions_nm[ca[0].index]
    return result


def orient_to_opm(
    modeller: app.Modeller,
    opm_path: Path,
    alignment_ranges: list[list[int]],
) -> dict[str, Any]:
    opm = app.PDBFile(str(opm_path))
    residue_ids = transmembrane_residue_ids(alignment_ranges)
    moving_map = ca_positions_by_id(modeller.topology, modeller.positions, residue_ids)
    target_map = ca_positions_by_id(opm.topology, opm.positions, residue_ids)
    common = sorted(set(moving_map) & set(target_map))
    if len(common) < 150:
        raise RuntimeError(f"Too few common transmembrane C-alpha atoms: {len(common)}")
    moving = np.asarray([moving_map[key] for key in common])
    target = np.asarray([target_map[key] for key in common])
    moving_center = np.mean(moving, axis=0)
    target_center = np.mean(target, axis=0)
    covariance = (moving - moving_center).T @ (target - target_center)
    left, _, right_t = np.linalg.svd(covariance)
    rotation = right_t.T @ left.T
    if np.linalg.det(rotation) < 0:
        right_t[-1] *= -1
        rotation = right_t.T @ left.T
    transformed = (moving - moving_center) @ rotation.T + target_center
    rmsd_nm = float(np.sqrt(np.mean(np.sum((transformed - target) ** 2, axis=1))))
    all_positions = np.asarray(
        modeller.positions.value_in_unit(unit.nanometer), dtype=float
    )
    all_transformed = (all_positions - moving_center) @ rotation.T + target_center
    modeller.positions = all_transformed * unit.nanometer
    modeller.topology.setPeriodicBoxVectors(None)
    return {
        "reference": str(opm_path.relative_to(ROOT)),
        "common_transmembrane_ca_atoms": len(common),
        "residue_ids": common,
        "alignment_rmsd_nm": rmsd_nm,
        "rotation_matrix": rotation.tolist(),
        "moving_center_nm": moving_center.tolist(),
        "target_center_nm": target_center.tolist(),
        "membrane_normal_axis": "Z",
    }


def maximum_bond_length_nm(topology: app.Topology, positions) -> float:
    xyz = np.asarray(positions.value_in_unit(unit.nanometer), dtype=float)
    lengths = [
        float(np.linalg.norm(xyz[first.index] - xyz[second.index]))
        for first, second in topology.bonds()
    ]
    if not lengths:
        raise RuntimeError("Prepared topology contains no bonds")
    return max(lengths)


def loop_chirality_audit(
    topology: app.Topology,
    positions,
    chiral_residue_ids: set[int],
) -> dict[str, Any]:
    xyz = np.asarray(positions.value_in_unit(unit.nanometer), dtype=float)
    values: dict[int, float] = {}
    reference_values = []
    for residue in topology.residues():
        if residue.name not in STANDARD_AA or residue.name == "GLY":
            continue
        atoms = {atom.name: atom.index for atom in residue.atoms()}
        if not {"N", "CA", "C", "CB"} <= atoms.keys():
            continue
        ca = xyz[atoms["CA"]]
        signed = float(
            np.dot(
                np.cross(xyz[atoms["N"]] - ca, xyz[atoms["C"]] - ca),
                xyz[atoms["CB"]] - ca,
            )
        )
        if int(residue.id) in chiral_residue_ids:
            values[int(residue.id)] = signed
        else:
            reference_values.append(signed)
    if set(values) != chiral_residue_ids or not reference_values:
        raise RuntimeError("Could not evaluate every modeled ICL2 stereocenter")
    reference_sign = int(np.sign(np.median(reference_values)))
    passed = reference_sign != 0 and all(
        int(np.sign(value)) == reference_sign and abs(value) > 1e-6
        for value in values.values()
    )
    return {
        "reference_l_amino_acid_sign": reference_sign,
        "modeled_loop_signed_volumes_nm3": {
            str(key): value for key, value in sorted(values.items())
        },
        "pass": passed,
    }


def unit_vector(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm < 1e-12:
        raise RuntimeError("Cannot normalize a degenerate geometry vector")
    return vector / norm


def rotation_between_vectors(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    first = unit_vector(first)
    second = unit_vector(second)
    cross = np.cross(first, second)
    cosine = float(np.dot(first, second))
    sine = float(np.linalg.norm(cross))
    if sine < 1e-12:
        if cosine > 0.0:
            return np.eye(3)
        trial = np.asarray([1.0, 0.0, 0.0])
        if abs(first[0]) > 0.9:
            trial = np.asarray([0.0, 1.0, 0.0])
        axis = unit_vector(np.cross(first, trial))
        return -np.eye(3) + 2.0 * np.outer(axis, axis)
    cross_matrix = np.asarray(
        [
            [0.0, -cross[2], cross[1]],
            [cross[2], 0.0, -cross[0]],
            [-cross[1], cross[0], 0.0],
        ]
    )
    return (
        np.eye(3)
        + cross_matrix
        + cross_matrix @ cross_matrix * ((1.0 - cosine) / (sine * sine))
    )


def repair_modeled_l_chirality(
    topology: app.Topology,
    positions,
    chiral_residue_ids: set[int],
) -> tuple[Any, dict[str, Any]]:
    xyz = np.asarray(positions.value_in_unit(unit.nanometer), dtype=float).copy()
    reference_coefficients = []
    for residue in topology.residues():
        if (
            residue.name not in STANDARD_AA
            or residue.name == "GLY"
            or int(residue.id) in chiral_residue_ids
        ):
            continue
        atoms = {atom.name: atom.index for atom in residue.atoms()}
        if not {"N", "CA", "C", "CB"} <= atoms.keys():
            continue
        ca = xyz[atoms["CA"]]
        n_direction = unit_vector(xyz[atoms["N"]] - ca)
        c_direction = unit_vector(xyz[atoms["C"]] - ca)
        basis = [
            unit_vector(n_direction + c_direction),
            unit_vector(n_direction - c_direction),
            unit_vector(np.cross(n_direction, c_direction)),
        ]
        cb_direction = unit_vector(xyz[atoms["CB"]] - ca)
        reference_coefficients.append(
            [float(np.dot(cb_direction, axis)) for axis in basis]
        )
    if not reference_coefficients:
        raise RuntimeError("No resolved L-amino-acid geometry is available")
    target_coefficients = np.median(
        np.asarray(reference_coefficients), axis=0
    )
    target_coefficients[2] = abs(target_coefficients[2])
    target_coefficients = unit_vector(target_coefficients)
    repaired = []
    for residue in topology.residues():
        if (
            residue.name not in STANDARD_AA
            or residue.name == "GLY"
            or int(residue.id) not in chiral_residue_ids
        ):
            continue
        atoms = {atom.name: atom.index for atom in residue.atoms()}
        if not {"N", "CA", "C", "CB"} <= atoms.keys():
            raise RuntimeError(f"Cannot repair modeled residue {residue.id}")
        ca = xyz[atoms["CA"]]
        n_direction = unit_vector(xyz[atoms["N"]] - ca)
        c_direction = unit_vector(xyz[atoms["C"]] - ca)
        basis = [
            unit_vector(n_direction + c_direction),
            unit_vector(n_direction - c_direction),
            unit_vector(np.cross(n_direction, c_direction)),
        ]
        desired = unit_vector(
            sum(
                coefficient * axis
                for coefficient, axis in zip(target_coefficients, basis)
            )
        )
        rotation = rotation_between_vectors(
            xyz[atoms["CB"]] - ca,
            desired,
        )
        for atom in residue.atoms():
            if atom.name not in {"N", "CA", "C", "O", "OXT"}:
                xyz[atom.index] = ca + rotation @ (xyz[atom.index] - ca)
        repaired.append(int(residue.id))
    if set(repaired) != chiral_residue_ids:
        raise RuntimeError(
            f"Chirality repair omitted modeled residues: "
            f"{chiral_residue_ids - set(repaired)}"
        )
    return xyz * unit.nanometer, {
        "method": (
            "Rigidly rotate each modeled side chain about CA to the median "
            "resolved L-amino-acid tetrahedral direction; preserve all "
            "side-chain internal distances."
        ),
        "reference_residue_count": len(reference_coefficients),
        "target_local_basis_coefficients": target_coefficients.tolist(),
        "repaired_residue_ids": sorted(repaired),
    }


def relax_modeled_regions(
    topology: app.Topology,
    positions,
    forcefield: app.ForceField,
    modeled_residue_ids: set[int],
    cfg: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    system = forcefield.createSystem(
        topology,
        nonbondedMethod=app.CutoffNonPeriodic,
        nonbondedCutoff=float(cfg["nonbonded_cutoff_nm"]) * unit.nanometer,
        constraints=app.HBonds,
        rigidWater=True,
        removeCMMotion=True,
    )
    restraint = openmm.CustomExternalForce(
        "0.5*k*((x-x0)^2+(y-y0)^2+(z-z0)^2)"
    )
    restraint.addGlobalParameter(
        "k",
        float(cfg["loop_relaxation_restraint_k_kj_mol_nm2"])
        * unit.kilojoule_per_mole
        / unit.nanometer**2,
    )
    for name in ("x0", "y0", "z0"):
        restraint.addPerParticleParameter(name)
    restrained = []
    for atom in topology.atoms():
        if (
            atom.element is None
            or atom.element == app.element.hydrogen
            or (
                atom.residue.name in STANDARD_AA
                and int(atom.residue.id) in modeled_residue_ids
            )
        ):
            continue
        position = positions[atom.index].value_in_unit(unit.nanometer)
        restraint.addParticle(
            atom.index,
            [float(position[0]), float(position[1]), float(position[2])],
        )
        restrained.append(atom.index)
    system.addForce(restraint)
    integrator = openmm.VerletIntegrator(1.0 * unit.femtosecond)
    platform = openmm.Platform.getPlatformByName(
        str(cfg["preparation_platform"])
    )
    properties = {}
    if platform.getName() == "CPU":
        properties = {
            "Threads": str(int(cfg["loop_relaxation_cpu_threads"])),
            "DeterministicForces": (
                "true"
                if bool(cfg["preparation_deterministic_forces"])
                else "false"
            ),
        }
    simulation = app.Simulation(
        topology,
        system,
        integrator,
        platform,
        properties,
    )
    simulation.context.setPositions(positions)
    initial_state = simulation.context.getState(getEnergy=True)
    initial_energy = initial_state.getPotentialEnergy().value_in_unit(
        unit.kilojoule_per_mole
    )
    simulation.minimizeEnergy(
        tolerance=float(cfg["loop_relaxation_tolerance_kj_mol_nm"])
        * unit.kilojoule_per_mole
        / unit.nanometer,
        maxIterations=int(cfg["loop_relaxation_max_iterations"]),
    )
    final_state = simulation.context.getState(getEnergy=True, getPositions=True)
    final_energy = final_state.getPotentialEnergy().value_in_unit(
        unit.kilojoule_per_mole
    )
    final_positions = final_state.getPositions(asNumpy=True)
    del simulation
    del integrator
    return final_positions, {
        "platform": platform.getName(),
        "cpu_threads": int(cfg["loop_relaxation_cpu_threads"]),
        "nonbonded_method": "CutoffNonPeriodic",
        "nonbonded_cutoff_nm": float(cfg["nonbonded_cutoff_nm"]),
        "restraint_k_kj_mol_nm2": float(
            cfg["loop_relaxation_restraint_k_kj_mol_nm2"]
        ),
        "restrained_nonmodeled_heavy_atoms": len(restrained),
        "unrestrained_modeled_residue_ids": sorted(modeled_residue_ids),
        "tolerance_kj_mol_nm": float(
            cfg["loop_relaxation_tolerance_kj_mol_nm"]
        ),
        "max_iterations": int(cfg["loop_relaxation_max_iterations"]),
        "initial_potential_kj_mol": float(initial_energy),
        "final_potential_kj_mol": float(final_energy),
    }


def minimum_loop_nonbonded_heavy_distance_nm(
    topology: app.Topology,
    positions,
    loop_ids: set[int],
) -> float:
    xyz = np.asarray(positions.value_in_unit(unit.nanometer), dtype=float)
    atoms = list(topology.atoms())
    heavy = [
        atom
        for atom in atoms
        if atom.element is not None and atom.element != app.element.hydrogen
    ]
    loop = [atom for atom in heavy if int(atom.residue.id) in loop_ids]
    bonded = {
        frozenset((first.index, second.index)) for first, second in topology.bonds()
    }
    minimum = math.inf
    for first in loop:
        for second in heavy:
            if first.index == second.index or first.residue == second.residue:
                continue
            if frozenset((first.index, second.index)) in bonded:
                continue
            minimum = min(
                minimum,
                float(np.linalg.norm(xyz[first.index] - xyz[second.index])),
            )
    if not math.isfinite(minimum):
        raise RuntimeError("Could not calculate modeled-loop clash distance")
    return minimum


def periodic_box(topology: app.Topology) -> tuple[list[list[float]], list[float]]:
    vectors = topology.getPeriodicBoxVectors()
    if vectors is None:
        raise RuntimeError("Membrane builder did not create a periodic box")
    vectors_nm = [
        list(vector.value_in_unit(unit.nanometer)) for vector in vectors
    ]
    matrix = np.asarray(vectors_nm, dtype=float)
    if not np.allclose(matrix - np.diag(np.diag(matrix)), 0.0, atol=1e-8):
        raise RuntimeError("Phase 5 requires an orthorhombic membrane box")
    lengths = np.linalg.norm(matrix, axis=1).tolist()
    return vectors_nm, lengths


def minimum_periodic_distance_nm(
    positions_nm: np.ndarray,
    first_indices: list[int],
    second_indices: list[int],
    box_lengths_nm: list[float],
) -> float:
    if not first_indices or not second_indices:
        raise RuntimeError("Cannot measure an empty component")
    box = np.asarray(box_lengths_nm, dtype=float)
    first = np.mod(positions_nm[first_indices], box)
    second = np.mod(positions_nm[second_indices], box)
    distances, _ = cKDTree(second, boxsize=box).query(first, k=1)
    return float(np.min(distances))


def system_total_charge_e(
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
        raise RuntimeError(f"System has nonintegral charge: {charge}")
    return int(rounded)


def actual_ligand_hydrogen_mapping(
    topology: app.Topology,
    ligand_residue: app.Topology.Residue,
) -> dict[str, str]:
    atoms = set(ligand_residue.atoms())
    result = {}
    for first, second in topology.bonds():
        if first not in atoms or second not in atoms:
            continue
        if first.element == app.element.hydrogen:
            result[first.name] = second.name
        elif second.element == app.element.hydrogen:
            result[second.name] = first.name
    return result


def protonation_table(topology: app.Topology) -> list[dict[str, str]]:
    result = []
    for residue in topology.residues():
        if residue.name not in IONIZABLE_NAMES:
            continue
        atoms = {atom.name for atom in residue.atoms()}
        if residue.name == "ASP":
            state = "deprotonated (-1)"
        elif residue.name == "GLU":
            state = "deprotonated (-1)"
        elif residue.name == "LYS":
            state = "protonated (+1)"
        elif residue.name == "ARG":
            state = "protonated (+1)"
        elif "HD1" in atoms and "HE2" not in atoms:
            state = "HID (neutral delta-protonated)"
        elif "HE2" in atoms and "HD1" not in atoms:
            state = "HIE (neutral epsilon-protonated)"
        elif {"HD1", "HE2"} <= atoms:
            state = "HIP (+1)"
        else:
            raise RuntimeError(f"Could not identify histidine state at {residue.id}")
        result.append(
            {
                "chain": residue.chain.id,
                "residue_id": residue.id,
                "residue_name": residue.name,
                "state": state,
            }
        )
    return result


def prepare_condition(
    condition_name: str,
    condition: dict[str, Any],
    cfg: dict[str, Any],
    run: Path,
) -> dict[str, Any]:
    condition_dir = run / "systems" / condition_name
    for child in ["prepared", "simulation", "analysis", "figures", "visualization", "logs"]:
        (condition_dir / child).mkdir(parents=True, exist_ok=True)
    prepared_dir = condition_dir / "prepared"
    source_pdb = ROOT / str(condition["source_pdb"])
    source_cif = ROOT / str(condition["source_mmcif"])
    source_sdf = ROOT / str(condition["ligand_sdf"])
    source_audit = source_record_audit(source_pdb)

    protonated, atom_names, ccd_records = protonate_ligand(
        source_sdf,
        source_cif,
        str(condition["ligand_resname"]),
        str(condition["ligand_protonation_atom"]),
    )
    hydrogen_mapping = hydrogen_parent_mapping(protonated, atom_names)
    hydrogen_definition = prepared_dir / "ligand_hydrogens.xml"
    write_hydrogen_definitions(
        hydrogen_definition,
        str(condition["ligand_resname"]),
        hydrogen_mapping,
    )
    app.Modeller.loadHydrogenDefinitions(str(hydrogen_definition))
    ligand = Molecule.from_rdkit(
        protonated,
        allow_undefined_stereo=True,
        hydrogens_are_explicit=True,
    )
    ligand_output_cfg = dict(condition)
    ligand_output_cfg["partial_charge_method"] = cfg["partial_charge_method"]
    ligand_identity = write_ligand_outputs(
        prepared_dir,
        protonated,
        atom_names,
        ligand,
        ligand_output_cfg,
    )

    fixer = PDBFixer(filename=str(source_pdb))
    fixer.platform = openmm.Platform.getPlatformByName("Reference")
    original_topology = topology_summary(fixer.topology)
    fixer.findMissingResidues()
    reported_missing_residues = {
        str(key): value for key, value in fixer.missingResidues.items()
    }
    insertion_shift = 0 if condition["pdb_id"] == "7WC6" else 3
    fixer.missingResidues = {
        (0, 107 + insertion_shift): [
            "ILE",
            "HIS",
            "HIS",
            "SER",
            "ARG",
            "PHE",
            "ASN",
        ],
        (0, 225 + insertion_shift): ["GLY", "SER", "GLY", "SER", "GLY"],
    }
    fixer.findNonstandardResidues()
    nonstandard = [
        {
            "chain": residue.chain.id,
            "residue_id": residue.id,
            "residue_name": residue.name,
            "replacement": replacement,
        }
        for residue, replacement in fixer.nonstandardResidues
    ]
    if nonstandard:
        raise RuntimeError(f"Unexpected nonstandard residues: {nonstandard}")
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
    fixer.addMissingAtoms(seed=int(cfg["loop_seed"]))

    modeller = app.Modeller(fixer.topology, fixer.positions)
    delete_residues = []
    removed_residues: Counter[str] = Counter()
    for residue in modeller.topology.residues():
        keep = residue.name in STANDARD_AA or residue.name == condition["ligand_resname"]
        if (
            condition["pdb_id"] == "7WC7"
            and residue.name in STANDARD_AA
            and int(residue.id) in {71, 72, 73}
        ):
            keep = False
        if not keep:
            delete_residues.append(residue)
            removed_residues[residue.name] += 1
    modeller.delete(delete_residues)

    protein_residues = [
        residue
        for residue in modeller.topology.residues()
        if residue.name in STANDARD_AA
    ]
    if len(protein_residues) != 367:
        raise RuntimeError(
            f"Matched construct must contain 367 polymer residues, found "
            f"{len(protein_residues)}"
        )
    expected_icl2 = {
        residue_id: residue_name
        for residue_id, residue_name in zip(
            range(181, 188),
            ["ILE", "HIS", "HIS", "SER", "ARG", "PHE", "ASN"],
        )
    }
    actual_icl2 = {
        int(residue.id): residue.name
        for residue in protein_residues
        if 181 <= int(residue.id) <= 187
    }
    expected_linker = {
        residue_id: residue_name
        for residue_id, residue_name in zip(
            range(1061, 1066),
            ["GLY", "SER", "GLY", "SER", "GLY"],
        )
    }
    actual_linker = {
        int(residue.id): residue.name
        for residue in protein_residues
        if 1061 <= int(residue.id) <= 1065
    }
    if actual_icl2 != expected_icl2 or actual_linker != expected_linker:
        raise RuntimeError(
            f"Modeled sequence mismatch: ICL2={actual_icl2}, linker={actual_linker}"
        )
    ligand_residues = [
        residue
        for residue in modeller.topology.residues()
        if residue.name == condition["ligand_resname"]
    ]
    if len(ligand_residues) != 1:
        raise RuntimeError("Experimental ligand pose was not retained exactly once")
    pose_mapping = validate_pose_mapping(
        protonated,
        ccd_records,
        ligand_residues[0],
        modeller.topology,
    )
    if disulfide_pairs(modeller.topology) != EXPECTED_DISULFIDES:
        raise RuntimeError(
            f"Disulfide mismatch before hydrogenation: "
            f"{disulfide_pairs(modeller.topology)}"
        )

    orientation = orient_to_opm(
        modeller,
        ROOT / str(cfg["opm_reference_pdb"]),
        cfg["transmembrane_alignment_ranges"],
    )
    if orientation["alignment_rmsd_nm"] > float(
        cfg["gates"]["max_opm_alignment_rmsd_nm"]
    ):
        raise RuntimeError(f"OPM alignment gate failed: {orientation}")

    modeled_residue_ids = set(range(181, 188)) | set(range(1061, 1066))
    chiral_modeled_residue_ids = set(range(181, 188)) | {1062, 1064}
    initial_chirality = loop_chirality_audit(
        modeller.topology,
        modeller.positions,
        chiral_modeled_residue_ids,
    )
    modeller.positions, chirality_repair = repair_modeled_l_chirality(
        modeller.topology,
        modeller.positions,
        chiral_modeled_residue_ids,
    )
    repaired_chirality = loop_chirality_audit(
        modeller.topology,
        modeller.positions,
        chiral_modeled_residue_ids,
    )
    if not repaired_chirality["pass"]:
        raise RuntimeError(
            f"Modeled-region L-chirality repair failed: {repaired_chirality}"
        )

    forcefield = app.ForceField(
        cfg["protein_forcefield"],
        cfg["lipid_forcefield"],
        cfg["water_forcefield"],
    )
    generator = SMIRNOFFTemplateGenerator(
        molecules=[ligand],
        cache=str(prepared_dir / "smirnoff-template-cache.json"),
        forcefield=str(cfg["small_molecule_forcefield"]),
    )
    forcefield.registerTemplateGenerator(generator.generator)
    variants: list[str | None] = []
    variant_records = []
    for residue in modeller.topology.residues():
        variant = None
        residue_id = int(residue.id)
        if residue.name == "HIS":
            if residue_id == 165:
                variant = "HID"
            elif residue_id in {182, 183}:
                variant = "HIE"
            else:
                raise RuntimeError(f"Unapproved histidine microstate at {residue_id}")
        elif residue.name == "CYS" and residue_id in {148, 227, 349, 353}:
            variant = "CYX"
        variants.append(variant)
        if variant is not None:
            variant_records.append(
                {
                    "residue_id": residue.id,
                    "residue_name": residue.name,
                    "variant": variant,
                }
            )
    modeller.addHydrogens(
        forcefield,
        pH=float(cfg["ph"]),
        variants=variants,
        platform=openmm.Platform.getPlatformByName("Reference"),
    )
    modeller.positions, loop_relaxation = relax_modeled_regions(
        modeller.topology,
        modeller.positions,
        forcefield,
        modeled_residue_ids,
        cfg,
    )
    chirality = loop_chirality_audit(
        modeller.topology,
        modeller.positions,
        chiral_modeled_residue_ids,
    )
    loop_minimum_distance = minimum_loop_nonbonded_heavy_distance_nm(
        modeller.topology,
        modeller.positions,
        modeled_residue_ids,
    )
    post_relaxation_max_bond = maximum_bond_length_nm(
        modeller.topology, modeller.positions
    )
    if not chirality["pass"]:
        raise RuntimeError(
            f"Modeled-region chirality gate failed after relaxation: {chirality}"
        )
    if loop_minimum_distance < float(
        cfg["gates"]["minimum_loop_nonbonded_heavy_atom_distance_nm"]
    ):
        raise RuntimeError(
            f"Modeled-region clash gate failed: {loop_minimum_distance:.4f} nm"
        )
    if post_relaxation_max_bond > float(
        cfg["gates"]["max_loop_covalent_bond_nm"]
    ):
        raise RuntimeError(
            f"Modeled topology bond gate failed: "
            f"{post_relaxation_max_bond:.4f} nm"
        )
    ligand_residue = next(
        residue
        for residue in modeller.topology.residues()
        if residue.name == condition["ligand_resname"]
    )
    actual_hydrogen_mapping = actual_ligand_hydrogen_mapping(
        modeller.topology, ligand_residue
    )
    if actual_hydrogen_mapping != hydrogen_mapping:
        raise RuntimeError(
            f"Hydrogenated ligand differs from the SDF definition: "
            f"{actual_hydrogen_mapping}"
        )
    if disulfide_pairs(modeller.topology) != EXPECTED_DISULFIDES:
        raise RuntimeError("Hydrogen addition changed the approved disulfides")
    histidine_states = {
        int(row["residue_id"]): row["state"]
        for row in protonation_table(modeller.topology)
        if row["residue_name"] == "HIS"
    }
    if histidine_states != {
        165: "HID (neutral delta-protonated)",
        182: "HIE (neutral epsilon-protonated)",
        183: "HIE (neutral epsilon-protonated)",
    }:
        raise RuntimeError(f"Histidine microstate mismatch: {histidine_states}")
    n_terminal = residue_by_id(modeller.topology, 74)
    c_terminal = residue_by_id(modeller.topology, 401)
    n_terminal_hydrogens = [
        atom.name
        for atom in n_terminal.atoms()
        if atom.element == app.element.hydrogen
        and any(
            (
                first == atom and second.name == "N"
                or second == atom and first.name == "N"
            )
            for first, second in modeller.topology.bonds()
        )
    ]
    if len(n_terminal_hydrogens) != 3 or not any(
        atom.name == "OXT" for atom in c_terminal.atoms()
    ):
        raise RuntimeError("Approved charged terminal states were not built")

    charge_before_membrane = system_total_charge_e(forcefield, modeller.topology)
    add_membrane_with_seed(modeller, forcefield, cfg)
    box_vectors_nm, box_lengths_nm = periodic_box(modeller.topology)
    prepared_summary = topology_summary(modeller.topology)
    residues = list(modeller.topology.residues())
    lipid_residues = [
        residue for residue in residues if residue.name == cfg["lipid_resname"]
    ]
    water_count = sum(
        prepared_summary["residue_counts"].get(name, 0) for name in WATER_NAMES
    )
    ion_counts = {
        name: count
        for name, count in prepared_summary["residue_counts"].items()
        if name in ION_NAMES and count
    }
    positions_nm = np.asarray(
        modeller.positions.value_in_unit(unit.nanometer), dtype=float
    )
    phosphorus = [
        next(atom for atom in residue.atoms() if atom.name == "P")
        for residue in lipid_residues
    ]
    upper_lipids = sum(positions_nm[atom.index, 2] >= 0.0 for atom in phosphorus)
    lower_lipids = len(phosphorus) - upper_lipids
    protein_ligand_heavy = [
        atom.index
        for atom in modeller.topology.atoms()
        if (
            atom.residue.name in STANDARD_AA | {condition["ligand_resname"]}
            and atom.element is not None
            and atom.element != app.element.hydrogen
        )
    ]
    ligand_heavy = [
        atom.index
        for atom in modeller.topology.atoms()
        if (
            atom.residue.name == condition["ligand_resname"]
            and atom.element is not None
            and atom.element != app.element.hydrogen
        )
    ]
    loop_heavy = [
        atom.index
        for atom in modeller.topology.atoms()
        if (
            atom.residue.name in STANDARD_AA
            and int(atom.residue.id) in modeled_residue_ids
            and atom.element is not None
            and atom.element != app.element.hydrogen
        )
    ]
    lipid_heavy = [
        atom.index
        for atom in modeller.topology.atoms()
        if (
            atom.residue.name == cfg["lipid_resname"]
            and atom.element is not None
            and atom.element != app.element.hydrogen
        )
    ]
    water_oxygens = [
        atom.index
        for atom in modeller.topology.atoms()
        if atom.residue.name in WATER_NAMES and atom.element == app.element.oxygen
    ]
    component_distances = {
        "protein_ligand_to_lipid_heavy_nm": minimum_periodic_distance_nm(
            positions_nm,
            protein_ligand_heavy,
            lipid_heavy,
            box_lengths_nm,
        ),
        "ligand_to_water_oxygen_nm": minimum_periodic_distance_nm(
            positions_nm,
            ligand_heavy,
            water_oxygens,
            box_lengths_nm,
        ),
        "modeled_regions_to_lipid_heavy_nm": minimum_periodic_distance_nm(
            positions_nm,
            loop_heavy,
            lipid_heavy,
            box_lengths_nm,
        ),
    }
    minimum_intercomponent = min(component_distances.values())
    if minimum_intercomponent < float(
        cfg["gates"]["minimum_intercomponent_heavy_atom_distance_nm"]
    ):
        raise RuntimeError(
            f"Impossible prepared intercomponent distance: "
            f"{minimum_intercomponent:.4f} nm"
        )

    parameterized_system = create_system(forcefield, modeller.topology, cfg)
    if parameterized_system.getNumParticles() != prepared_summary["atoms"]:
        raise RuntimeError("Parameterized particle count differs from topology")
    charge_after_ions = system_total_charge_e(forcefield, modeller.topology)
    system_pdb = prepared_dir / "system.pdb"
    with system_pdb.open("w", encoding="utf-8") as handle:
        app.PDBFile.writeFile(
            modeller.topology, modeller.positions, handle, keepIds=True
        )
    protonation = protonation_table(modeller.topology)
    write_json(prepared_dir / "protonation_table.json", protonation)
    audit = {
        "condition": condition_name,
        "pdb_id": condition["pdb_id"],
        "decision_record": cfg["decision_record_audit"],
        "source_record_audit": source_audit,
        "original_topology": original_topology,
        "pdbfixer_reported_missing_residues": reported_missing_residues,
        "modeled_missing_residues": {
            "ICL2_181_187": cfg["modeled_icl2_sequence"],
            "BRIL_linker_1061_1065": cfg["modeled_bril_linker_sequence"],
            "conformer_index": 0,
            "loop_seed": int(cfg["loop_seed"]),
        },
        "missing_atoms_added": missing_atoms,
        "missing_terminal_atoms_added": missing_terminals,
        "nonstandard_residues": nonstandard,
        "removed_source_residues": dict(sorted(removed_residues.items())),
        "retained_source_heterogens": {condition["ligand_resname"]: 1},
        "retained_source_waters": 0,
        "polymer_residue_count": len(protein_residues),
        "orientation": orientation,
        "loop_gates": {
            "topology_and_sequence_pass": True,
            "initial_chirality": initial_chirality,
            "chirality_repair": chirality_repair,
            "chirality_after_sidechain_repair": repaired_chirality,
            "restrained_local_relaxation": loop_relaxation,
            "chirality": chirality,
            "minimum_nonbonded_heavy_atom_distance_nm": loop_minimum_distance,
            "maximum_covalent_bond_nm": post_relaxation_max_bond,
            "membrane_placement_minimum_distance_nm": component_distances[
                "modeled_regions_to_lipid_heavy_nm"
            ],
        },
        "disulfide_bonds": [sorted(pair) for pair in EXPECTED_DISULFIDES],
        "explicit_variants": variant_records,
        "protonation_table": protonation,
        "n_terminal": {
            "residue": "K74",
            "nitrogen_hydrogen_names": sorted(n_terminal_hydrogens),
            "state": "protonated (+1)",
        },
        "c_terminal": {
            "residue": "E401",
            "has_oxt": True,
            "state": "deprotonated (-1)",
        },
        "ligand": {
            **ligand_identity,
            "source_sdf_sha256": sha256_file(source_sdf),
            "pose_atom_mapping": pose_mapping,
            "hydrogen_parent_mapping": hydrogen_mapping,
            "undefined_stereochemistry": [
                (
                    f"protonated amine {condition['ligand_protonation_atom']}; "
                    "carbon stereochemistry retained from CCD SDF"
                )
            ],
        },
        "total_charge_before_membrane_and_ions_e": charge_before_membrane,
        "total_charge_after_neutralizing_ions_e": charge_after_ions,
        "prepared_topology": prepared_summary,
        "lipid_type": cfg["lipid_type"],
        "lipid_resname": cfg["lipid_resname"],
        "lipid_count": len(lipid_residues),
        "lipid_count_upper_leaflet": int(upper_lipids),
        "lipid_count_lower_leaflet": int(lower_lipids),
        "water_molecules": int(water_count),
        "ion_residue_counts": ion_counts,
        "periodic_box_vectors_nm": box_vectors_nm,
        "periodic_box_lengths_nm": box_lengths_nm,
        "intercomponent_minimum_heavy_atom_distances": component_distances,
        "minimum_intercomponent_heavy_atom_distance_nm": minimum_intercomponent,
        "parameterization": {
            "status": "PASS",
            "parameterized_particles": parameterized_system.getNumParticles(),
            "unassigned_parameter_exception": None,
            "small_molecule_forcefield": cfg["small_molecule_forcefield"],
            "partial_charge_method": cfg["partial_charge_method"],
        },
        "forcefields": [
            cfg["protein_forcefield"],
            cfg["lipid_forcefield"],
            cfg["water_forcefield"],
            cfg["small_molecule_forcefield"],
        ],
        "preparation_seed": int(cfg["seed"]),
        "loop_seed": int(cfg["loop_seed"]),
        "preparation_platform": cfg["preparation_platform"],
        "preparation_cpu_threads": int(cfg["preparation_cpu_threads"]),
        "preparation_deterministic_forces": bool(
            cfg["preparation_deterministic_forces"]
        ),
    }
    write_json(prepared_dir / "preparation_audit.json", audit)
    return {
        "condition_dir": condition_dir,
        "topology": modeller.topology,
        "positions": modeller.positions,
        "forcefield": forcefield,
        "restraint_indices": protein_ligand_heavy,
        "audit": audit,
    }


def execute_phase(run: Path, cfg: dict[str, Any]) -> None:
    decision_path = ROOT / str(cfg["decision_record"])
    decision_audit = validate_decision_record(
        decision_path,
        list(cfg["required_decisions"]),
    )
    cfg["decision_record_audit"] = decision_audit
    cfg["loop_seed"] = int(cfg["seed"])
    input_paths = {
        "opm_reference_pdb": ROOT / str(cfg["opm_reference_pdb"]),
    }
    for condition_name, condition in cfg["conditions"].items():
        for key in [
            "source_pdb",
            "source_mmcif",
            "source_validation_report",
            "ligand_sdf",
        ]:
            input_paths[f"{condition_name}_{key}"] = ROOT / str(condition[key])
    input_records = {
        name: verified_input_record(path) for name, path in input_paths.items()
    }
    opm_metadata = ROOT / "inputs" / "phase05" / "orientation" / "7WC5_opm_metadata.json"
    input_records["opm_reference_metadata"] = verified_input_record(opm_metadata)
    manifest = read_json(run / "manifest.json")
    manifest["inputs"] = input_records
    manifest["decision_record"] = decision_audit
    write_json(run / "manifest.json", manifest)

    prepared_conditions = {}
    for condition_name, condition_data in cfg["conditions"].items():
        condition_cfg = dict(cfg)
        condition_cfg.update(condition_data)
        condition_cfg["seed"] = int(cfg["seed"]) + int(condition_data["seed_offset"])
        condition_cfg["loop_seed"] = int(cfg["loop_seed"])
        prepared_conditions[condition_name] = prepare_condition(
            condition_name,
            condition_data,
            condition_cfg,
            run,
        )

    set_progress(str(cfg["profile"]), "READY")
    if cfg["profile"] == "teaching":
        snapshot_path = (
            ROOT
            / "state"
            / "snapshots"
            / f"phase5_teaching_preproduction_{utc_now().replace(':', '').replace('-', '')}.json"
        )
        write_json(
            snapshot_path,
            {
                "created_utc": utc_now(),
                "run_id": run.name,
                "resolved_config_sha256": sha256_file(run / "resolved_config.yaml"),
                "decision_record_sha256": decision_audit["sha256"],
                "prepared_system_pdb_sha256": {
                    name: sha256_file(
                        prepared["condition_dir"] / "prepared" / "system.pdb"
                    )
                    for name, prepared in prepared_conditions.items()
                },
            },
        )
    set_progress(str(cfg["profile"]), "SIMULATION_RUNNING")
    condition_outputs = {}
    for condition_name, prepared in prepared_conditions.items():
        condition_data = cfg["conditions"][condition_name]
        condition_cfg = dict(cfg)
        condition_cfg.update(condition_data)
        condition_cfg["seed"] = int(cfg["seed"]) + int(condition_data["seed_offset"])
        run_staged_simulation(
            prepared["condition_dir"],
            prepared["topology"],
            prepared["positions"],
            prepared["forcefield"],
            condition_cfg,
            membrane=True,
            restraint_indices=prepared["restraint_indices"],
            finish_run_manifest=False,
        )
        condition_outputs[condition_name] = {
            "preparation_audit": str(
                (
                    prepared["condition_dir"]
                    / "prepared"
                    / "preparation_audit.json"
                ).relative_to(run)
            ),
            "system_pdb_sha256": sha256_file(
                prepared["condition_dir"] / "prepared" / "system.pdb"
            ),
            "system_xml_sha256": sha256_file(
                prepared["condition_dir"] / "prepared" / "system.xml"
            ),
            "trajectory_sha256": sha256_file(
                prepared["condition_dir"] / "simulation" / "production.dcd"
            ),
            "checkpoint_sha256": sha256_file(
                prepared["condition_dir"] / "simulation" / "production.chk"
            ),
        }
    finish_manifest(
        run,
        "SIMULATION_COMPLETE",
        {"outputs": {"conditions": condition_outputs}},
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=["quick", "teaching"],
        default="quick",
    )
    args = parser.parse_args()
    cfg = resolve_config(5, args.profile)
    random.seed(int(cfg["seed"]))
    run = create_run(5, args.profile, cfg)
    failure_state = "PREFLIGHT_FAILED"
    set_progress(args.profile, "PREFLIGHT_RUNNING")
    try:
        execute_phase(run, cfg)
    except Exception as error:
        current = read_json(ROOT / "state" / "progress.json")["phases"]["5"][
            args.profile
        ]
        if current == "SIMULATION_RUNNING":
            failure_state = "SIMULATION_FAILED"
        set_progress(args.profile, failure_state)
        (run / "FAILURE.md").write_text(
            "# Phase 5 failure\n\n"
            f"First reported exception: `{type(error).__name__}: {error}`\n",
            encoding="utf-8",
        )
        finish_manifest(
            run,
            failure_state,
            {
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )
        raise
    print(run)


if __name__ == "__main__":
    main()
