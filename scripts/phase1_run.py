#!/usr/bin/env python
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import openmm
from openmm import app, unit

from mdlab.core import Timer, create_run, finish_manifest, openmm_platform, resolve_config, write_json
from mdlab.openmm_utils import interval_steps, serialize_system, steps_for_ps, write_state_and_pdb


def fcc_positions(n_cells: int, box_length_nm: float) -> np.ndarray:
    basis = np.array([[0, 0, 0], [0, 0.5, 0.5], [0.5, 0, 0.5], [0.5, 0.5, 0]], dtype=float)
    coords = []
    a = box_length_nm / n_cells
    for i in range(n_cells):
        for j in range(n_cells):
            for k in range(n_cells):
                origin = np.array([i, j, k], dtype=float)
                for b in basis:
                    coords.append((origin + b) * a)
    return np.asarray(coords)


def build_topology(n_particles: int, box_length_nm: float) -> app.Topology:
    topology = app.Topology()
    chain = topology.addChain("A")
    argon = app.Element.getBySymbol("Ar")
    for i in range(n_particles):
        residue = topology.addResidue("AR", chain, id=str(i + 1))
        topology.addAtom("AR", argon, residue)
    vec = openmm.Vec3(box_length_nm, box_length_nm, box_length_nm) * unit.nanometer
    topology.setPeriodicBoxVectors((openmm.Vec3(box_length_nm, 0, 0), openmm.Vec3(0, box_length_nm, 0), openmm.Vec3(0, 0, box_length_nm)) * unit.nanometer)
    return topology


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["quick", "teaching"], default="quick")
    args = parser.parse_args()
    cfg = resolve_config(1, args.profile)
    run_dir = create_run(1, args.profile, cfg)

    n = int(cfg["particles"])
    n_cells = round((n / 4) ** (1 / 3))
    if 4 * n_cells**3 != n:
        raise ValueError("Particle count must be 4*n_cells^3 for the FCC builder")
    sigma = float(cfg["sigma_nm"])
    rho_star = float(cfg["reduced_density"])
    box_length = (n * sigma**3 / rho_star) ** (1 / 3)
    positions_nm = fcc_positions(n_cells, box_length)
    topology = build_topology(n, box_length)

    system = openmm.System()
    for _ in range(n):
        system.addParticle(float(cfg["particle_mass_da"]) * unit.dalton)
    system.setDefaultPeriodicBoxVectors(
        openmm.Vec3(box_length, 0, 0) * unit.nanometer,
        openmm.Vec3(0, box_length, 0) * unit.nanometer,
        openmm.Vec3(0, 0, box_length) * unit.nanometer,
    )
    expression = "4*epsilon*((sigma/r)^12-(sigma/r)^6)"
    force = openmm.CustomNonbondedForce(expression)
    force.addGlobalParameter("sigma", sigma * unit.nanometer)
    force.addGlobalParameter("epsilon", float(cfg["epsilon_kj_mol"]) * unit.kilojoule_per_mole)
    cutoff = min(float(cfg["cutoff_nm"]), 0.49 * box_length)
    switch = min(float(cfg["switch_nm"]), cutoff - 0.05)
    force.setNonbondedMethod(openmm.CustomNonbondedForce.CutoffPeriodic)
    force.setCutoffDistance(cutoff * unit.nanometer)
    force.setUseSwitchingFunction(True)
    force.setSwitchingDistance(switch * unit.nanometer)
    force.setUseLongRangeCorrection(True)
    for _ in range(n):
        force.addParticle([])
    system.addForce(force)
    system.addForce(openmm.CMMotionRemover())
    serialize_system(system, run_dir / "prepared" / "system.xml")

    with (run_dir / "prepared" / "initial.pdb").open("w", encoding="utf-8") as handle:
        app.PDBFile.writeFile(topology, positions_nm * unit.nanometer, handle)

    platform_obj, properties, available = openmm_platform(cfg["platform"], cfg["cuda_precision"])
    integrator = openmm.LangevinMiddleIntegrator(
        float(cfg["temperature_kelvin"]) * unit.kelvin,
        float(cfg["friction_per_ps"]) / unit.picosecond,
        float(cfg["timestep_fs"]) * unit.femtosecond,
    )
    integrator.setRandomNumberSeed(int(cfg["seed"]))
    simulation = app.Simulation(topology, system, integrator, platform_obj, properties)
    simulation.context.setPositions(positions_nm * unit.nanometer)
    simulation.minimizeEnergy(maxIterations=500)
    simulation.context.setVelocitiesToTemperature(float(cfg["temperature_kelvin"]) * unit.kelvin, int(cfg["seed"]))

    nvt_steps = steps_for_ps(float(cfg["nvt_ps"]), float(cfg["timestep_fs"]))
    stride = interval_steps(float(cfg["output_stride_ps"]), float(cfg["timestep_fs"]))
    simulation.reporters = [
        app.DCDReporter(str(run_dir / "simulation" / "nvt.dcd"), stride, enforcePeriodicBox=True),
        app.StateDataReporter(
            str(run_dir / "simulation" / "nvt.csv"), stride, step=True, time=True,
            potentialEnergy=True, kineticEnergy=True, totalEnergy=True, temperature=True,
            volume=True, speed=True, separator=","
        ),
        app.CheckpointReporter(str(run_dir / "simulation" / "nvt.chk"), max(stride, nvt_steps // 5)),
    ]
    with Timer() as timer_nvt:
        simulation.step(nvt_steps)
    write_state_and_pdb(simulation, run_dir / "simulation", "nvt_final")

    # NVE starts from the equilibrated NVT state with an identical Hamiltonian.
    state = simulation.context.getState(getPositions=True, getVelocities=True, enforcePeriodicBox=True)
    nve_integrator = openmm.VerletIntegrator(float(cfg["timestep_fs"]) * unit.femtosecond)
    nve = app.Simulation(topology, system, nve_integrator, platform_obj, properties)
    nve.context.setState(state)
    nve_steps = steps_for_ps(float(cfg["nve_ps"]), float(cfg["timestep_fs"]))
    nve.reporters = [
        app.DCDReporter(str(run_dir / "simulation" / "nve.dcd"), stride, enforcePeriodicBox=True),
        app.StateDataReporter(
            str(run_dir / "simulation" / "nve.csv"), stride, step=True, time=True,
            potentialEnergy=True, kineticEnergy=True, totalEnergy=True, temperature=True,
            volume=True, speed=True, separator=","
        ),
        app.CheckpointReporter(str(run_dir / "simulation" / "nve.chk"), max(stride, nve_steps // 5)),
    ]
    with Timer() as timer_nve:
        nve.step(nve_steps)
    write_state_and_pdb(nve, run_dir / "simulation", "nve_final")

    write_json(run_dir / "simulation" / "performance.json", {
        "available_platforms": available,
        "selected_platform": cfg["platform"],
        "cuda_precision": cfg["cuda_precision"],
        "nvt_wall_seconds": timer_nvt.elapsed_seconds,
        "nve_wall_seconds": timer_nve.elapsed_seconds,
        "nvt_ns_per_day": (float(cfg["nvt_ps"]) / 1000.0) / (timer_nvt.elapsed_seconds / 86400.0),
        "nve_ns_per_day": (float(cfg["nve_ps"]) / 1000.0) / (timer_nve.elapsed_seconds / 86400.0),
        "box_length_nm": box_length,
        "cutoff_nm": cutoff,
        "switch_nm": switch,
    })
    finish_manifest(run_dir, "SIMULATION_COMPLETE")
    print(run_dir)


if __name__ == "__main__":
    main()
