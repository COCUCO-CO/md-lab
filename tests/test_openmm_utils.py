from pathlib import Path
import sys

import openmm
from openmm import app, unit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mdlab.openmm_utils import add_positional_restraints


def test_positional_restraint_uses_periodic_distance():
    topology = app.Topology()
    chain = topology.addChain()
    residue = topology.addResidue("ALA", chain)
    topology.addAtom("CA", app.element.carbon, residue)
    system = openmm.System()
    system.addParticle(12.0)
    positions = [openmm.Vec3(-0.1, 0.0, 0.0)] * unit.nanometer

    force = add_positional_restraints(
        system,
        topology,
        positions,
        [0],
        1000.0,
    )

    assert (
        force.getEnergyFunction()
        == "0.5*k*periodicdistance(x,y,z,x0,y0,z0)^2"
    )
