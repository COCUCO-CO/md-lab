from __future__ import annotations

from pathlib import Path
from typing import Iterable

import openmm
from openmm import app, unit


def steps_for_ps(duration_ps: float, timestep_fs: float) -> int:
    steps = int(round(duration_ps * 1000.0 / timestep_fs))
    if steps <= 0:
        raise ValueError("Duration must produce at least one integration step")
    return steps


def interval_steps(stride_ps: float, timestep_fs: float) -> int:
    return max(1, int(round(stride_ps * 1000.0 / timestep_fs)))


def add_positional_restraints(
    system: openmm.System,
    topology: app.Topology,
    positions,
    atom_indices: Iterable[int],
    initial_k_kj_mol_nm2: float,
) -> openmm.CustomExternalForce:
    force = openmm.CustomExternalForce(
        "0.5*k*periodicdistance(x,y,z,x0,y0,z0)^2"
    )
    force.addGlobalParameter("k", initial_k_kj_mol_nm2 * unit.kilojoule_per_mole / unit.nanometer**2)
    for name in ("x0", "y0", "z0"):
        force.addPerParticleParameter(name)
    for idx in atom_indices:
        p = positions[idx].value_in_unit(unit.nanometer)
        force.addParticle(int(idx), [float(p[0]), float(p[1]), float(p[2])])
    system.addForce(force)
    return force


def protein_heavy_indices(topology: app.Topology) -> list[int]:
    indices: list[int] = []
    for atom in topology.atoms():
        if atom.residue.name in {"HOH", "WAT", "NA", "CL", "Na+", "Cl-"}:
            continue
        if atom.element is not None and atom.element.symbol != "H":
            # Treat standard amino acids as protein; ligand selection is handled separately where needed.
            if atom.residue.name in app.PDBFile._residueNameReplacements or len(atom.residue.name) == 3:
                indices.append(atom.index)
    return indices


def standard_reporters(
    simulation: app.Simulation,
    directory: Path,
    prefix: str,
    timestep_fs: float,
    output_stride_ps: float,
    checkpoint_stride_ps: float,
    total_steps: int,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    interval = interval_steps(output_stride_ps, timestep_fs)
    checkpoint_interval = interval_steps(checkpoint_stride_ps, timestep_fs)
    simulation.reporters.append(app.DCDReporter(str(directory / f"{prefix}.dcd"), interval, enforcePeriodicBox=True))
    simulation.reporters.append(
        app.StateDataReporter(
            str(directory / f"{prefix}.csv"),
            interval,
            step=True,
            time=True,
            potentialEnergy=True,
            kineticEnergy=True,
            totalEnergy=True,
            temperature=True,
            volume=True,
            density=True,
            speed=True,
            elapsedTime=True,
            remainingTime=True,
            totalSteps=total_steps,
            separator=",",
        )
    )
    simulation.reporters.append(app.CheckpointReporter(str(directory / f"{prefix}.chk"), checkpoint_interval))


def write_state_and_pdb(simulation: app.Simulation, directory: Path, prefix: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    state = simulation.context.getState(getPositions=True, getVelocities=True, getEnergy=True, enforcePeriodicBox=True)
    simulation.saveState(str(directory / f"{prefix}.xml"))
    with (directory / f"{prefix}.pdb").open("w", encoding="utf-8") as handle:
        app.PDBFile.writeFile(simulation.topology, state.getPositions(), handle, keepIds=True)


def serialize_system(system: openmm.System, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(openmm.XmlSerializer.serialize(system), encoding="utf-8")
