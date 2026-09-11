from pathlib import Path
import sys

import numpy as np
import mdtraj as md

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.phase4_analyze import minimum_image, periodic_center
from scripts.render_trajectory import center_periodic_components


def test_minimum_image_wraps_across_periodic_boundary():
    displacement = np.array([8.5, -8.5, 0.5])
    lengths = np.array([10.0, 10.0, 10.0])

    wrapped = minimum_image(displacement, lengths)

    np.testing.assert_allclose(wrapped, [-1.5, 1.5, 0.5])


def test_periodic_center_handles_values_straddling_box_boundary():
    values = np.array([9.8, 9.9, 0.1, 0.2])

    center = periodic_center(values, 10.0)

    assert min(abs(center), abs(center - 10.0)) < 1e-12


def test_viewer_centers_separate_periodic_protein_chains():
    topology = md.Topology()
    first_chain = topology.add_chain()
    first_residue = topology.add_residue("ALA", first_chain)
    topology.add_atom("CA", md.element.carbon, first_residue)
    second_chain = topology.add_chain()
    second_residue = topology.add_residue("ALA", second_chain)
    topology.add_atom("CA", md.element.carbon, second_residue)
    trajectory = md.Trajectory(
        xyz=np.array([[[1.0, 0.0, 0.0], [9.0, 0.0, 0.0]]]),
        topology=topology,
        unitcell_lengths=np.array([[10.0, 10.0, 10.0]]),
        unitcell_angles=np.array([[90.0, 90.0, 90.0]]),
    )

    center_periodic_components(trajectory)

    np.testing.assert_allclose(
        trajectory.xyz[0, :, 0],
        [1.0, -1.0],
    )
