# ruff: noqa: E402
from pathlib import Path
import sys

import numpy as np
import mdtraj as md
from rdkit import Chem

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from mdlab.core import resolve_config
from scripts.phase5_analyze import (
    reimage_component_near_anchor,
    resname_atom_indices,
)
from scripts.phase5_run import (
    hydrogen_parent_mapping,
    protonate_ligand,
    rotation_between_vectors,
    transmembrane_residue_ids,
    validate_decision_record,
)


def test_phase5_quick_protocol_is_fully_resolved():
    config = resolve_config(5, "quick")

    assert config["temperature_kelvin"] == 310.0
    assert config["production_ps"] == 200.0
    assert config["preproduction_ps"] == 20.0
    assert config["npt_restraint_schedule_kj_mol_nm2"] == [
        1000.0,
        500.0,
        100.0,
        10.0,
    ]
    assert config["conditions"]["lsd"]["seed_offset"] == 0
    assert config["conditions"]["lisuride"]["seed_offset"] == 10
    assert config["loop_relaxation_restraint_k_kj_mol_nm2"] == 10000.0
    assert config["loop_relaxation_max_iterations"] == 5000
    assert config["loop_relaxation_cpu_threads"] == 1


def test_phase5_decision_record_is_approved_and_complete():
    config = resolve_config(5, "quick")
    decision = validate_decision_record(
        ROOT / config["decision_record"],
        config["required_decisions"],
    )

    assert decision["status"] == "APPROVED"
    assert len(decision["sha256"]) == 64


def test_lsd_protonation_uses_ccd_graph_and_approved_nitrogen():
    molecule, names, records = protonate_ligand(
        ROOT / "inputs/phase05/candidates/7WC6/7LD_ideal.sdf",
        ROOT / "inputs/phase05/candidates/7WC6/7WC6.cif",
        "7LD",
        "N2",
    )

    assert Chem.GetFormalCharge(molecule) == 1
    assert molecule.GetNumAtoms() == 50
    assert len(records) == 49
    assert names[-1] == "HP"
    assert hydrogen_parent_mapping(molecule, names)["HP"] == "N2"


def test_lisuride_protonation_uses_ccd_graph_and_approved_nitrogen():
    molecule, names, records = protonate_ligand(
        ROOT / "inputs/phase05/candidates/7WC7/H8G_ideal.sdf",
        ROOT / "inputs/phase05/candidates/7WC7/7WC7.cif",
        "H8G",
        "NAX",
    )

    assert Chem.GetFormalCharge(molecule) == 1
    assert molecule.GetNumAtoms() == 52
    assert len(records) == 51
    assert names[-1] == "HP"
    assert hydrogen_parent_mapping(molecule, names)["HP"] == "NAX"


def test_transmembrane_alignment_selection_is_deterministic():
    config = resolve_config(5, "quick")
    residue_ids = transmembrane_residue_ids(
        config["transmembrane_alignment_ranges"]
    )

    assert len(residue_ids) == 170
    assert len(set(residue_ids)) == 170
    assert residue_ids[0] == 75
    assert residue_ids[-1] == 383


def test_chirality_repair_rotation_maps_source_vector_to_target():
    source = np.array([1.0, 0.0, 0.0])
    target = np.array([0.0, 0.0, 1.0])

    rotation = rotation_between_vectors(source, target)

    np.testing.assert_allclose(rotation @ source, target, atol=1e-12)
    np.testing.assert_allclose(rotation.T @ rotation, np.eye(3), atol=1e-12)
    np.testing.assert_allclose(np.linalg.det(rotation), 1.0, atol=1e-12)


def test_numeric_leading_ligand_resname_is_selected_without_dsl():
    topology = md.Topology()
    chain = topology.add_chain()
    residue = topology.add_residue("7LD", chain, resSeq=1205)
    topology.add_atom("N2", md.element.nitrogen, residue)
    topology.add_atom("HP", md.element.hydrogen, residue)

    heavy = resname_atom_indices(topology, "7LD", heavy_only=True)
    cationic_n = resname_atom_indices(topology, "7LD", atom_name="N2")

    np.testing.assert_array_equal(heavy, [0])
    np.testing.assert_array_equal(cationic_n, [0])


def test_periodic_ligand_image_is_moved_next_to_protein():
    topology = md.Topology()
    protein_chain = topology.add_chain()
    protein = topology.add_residue("ALA", protein_chain)
    topology.add_atom("CA", md.element.carbon, protein)
    ligand_chain = topology.add_chain()
    ligand = topology.add_residue("7LD", ligand_chain)
    topology.add_atom("N2", md.element.nitrogen, ligand)
    trajectory = md.Trajectory(
        xyz=np.array([[[0.2, 0.0, 0.0], [9.8, 0.0, 0.0]]]),
        topology=topology,
        unitcell_lengths=np.array([[10.0, 10.0, 10.0]]),
        unitcell_angles=np.array([[90.0, 90.0, 90.0]]),
    )

    translation = reimage_component_near_anchor(
        trajectory,
        np.array([1]),
        np.array([0]),
    )

    np.testing.assert_allclose(translation, [[-10.0, 0.0, 0.0]])
    np.testing.assert_allclose(
        trajectory.xyz[0, 1],
        [-0.2, 0.0, 0.0],
        atol=1e-6,
    )
