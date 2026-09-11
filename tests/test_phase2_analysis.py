from pathlib import Path
import sys

import mdtraj as md
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.phase2_analyze import protein_sasa


def test_protein_sasa_excludes_opc_virtual_sites():
    topology = md.Topology()
    chain = topology.add_chain()
    protein_residue = topology.add_residue("ALA", chain)
    topology.add_atom("CA", md.element.carbon, protein_residue)
    water_residue = topology.add_residue("HOH", chain)
    topology.add_atom("EP", md.element.virtual_site, water_residue)
    trajectory = md.Trajectory(np.zeros((1, 2, 3)), topology)

    sasa = protein_sasa(trajectory, topology.select("protein"))

    assert sasa.shape == (1,)
    assert np.isfinite(sasa).all()
