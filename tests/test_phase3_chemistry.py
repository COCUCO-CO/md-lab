from pathlib import Path
import sys

from openmm import app
from rdkit import Chem

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.phase3_run import (
    validate_benzene_hydrogen_definition,
    validate_benzene_mapping,
)


def test_benzene_mapping_matches_ccd_atom_order_and_ring_graph():
    molecule = Chem.AddHs(Chem.MolFromSmiles("c1ccccc1"))
    topology = app.Topology()
    chain = topology.addChain("A")
    residue = topology.addResidue("BNZ", chain, "400")
    atoms = [
        topology.addAtom(f"C{index}", app.element.carbon, residue)
        for index in range(1, 7)
    ]
    for first, second in zip(atoms, atoms[1:] + atoms[:1]):
        topology.addBond(first, second)

    mapping = validate_benzene_mapping(molecule, residue, topology)

    assert [entry["pdb_atom_name"] for entry in mapping] == [
        "C1",
        "C2",
        "C3",
        "C4",
        "C5",
        "C6",
    ]
    assert [entry["sdf_atom_index"] for entry in mapping] == [1, 2, 3, 4, 5, 6]


def test_benzene_hydrogen_definition_matches_sdf_graph():
    molecule = Chem.AddHs(Chem.MolFromSmiles("c1ccccc1"))

    mapping = validate_benzene_hydrogen_definition(
        molecule,
        ROOT / "configs" / "BNZ_hydrogens.xml",
    )

    assert mapping == {
        "H1": "C1",
        "H2": "C2",
        "H3": "C3",
        "H4": "C4",
        "H5": "C5",
        "H6": "C6",
    }
