from __future__ import annotations

from pathlib import Path
from typing import Any

import openmm
from openmm import app, unit

from .core import Timer, finish_manifest, openmm_platform, write_json
from .openmm_utils import add_positional_restraints, interval_steps, serialize_system, steps_for_ps, write_state_and_pdb

STANDARD_AA = {
    "ALA", "ARG", "ASN", "ASP", "CYS", "GLN", "GLU", "GLY", "HIS", "ILE",
    "LEU", "LYS", "MET", "PHE", "PRO", "SER", "THR", "TRP", "TYR", "VAL",
    "HID", "HIE", "HIP", "CYX", "ASH", "GLH", "LYN",
}
WATER_NAMES = {"HOH", "WAT", "SOL"}
ION_NAMES = {"NA", "CL", "Na+", "Cl-", "K", "CA", "MG"}


def topology_summary(topology: app.Topology) -> dict[str, Any]:
    residues = list(topology.residues())
    atoms = list(topology.atoms())
    counts: dict[str, int] = {}
    for residue in residues:
        counts[residue.name] = counts.get(residue.name, 0) + 1
    chains = []
    for chain in topology.chains():
        chain_residues = list(chain.residues())
        chains.append({
            "id": chain.id,
            "residue_count": len(chain_residues),
            "first": chain_residues[0].id if chain_residues else None,
            "last": chain_residues[-1].id if chain_residues else None,
        })
    return {
        "atoms": len(atoms),
        "residues": len(residues),
        "chains": chains,
        "residue_counts": counts,
        "bonds": sum(1 for _ in topology.bonds()),
    }


def heavy_indices(topology: app.Topology, include_ligand: bool = True) -> list[int]:
    indices: list[int] = []
    for atom in topology.atoms():
        if atom.element is None or atom.element.symbol == "H":
            continue
        if atom.residue.name in WATER_NAMES | ION_NAMES:
            continue
        if atom.residue.name in STANDARD_AA or include_ligand:
            indices.append(atom.index)
    return indices


def create_forcefield(cfg: dict[str, Any], include_lipid: bool = False) -> app.ForceField:
    files = [cfg["protein_forcefield"]]
    if include_lipid:
        files.append(cfg["lipid_forcefield"])
    files.append(cfg["water_forcefield"])
    return app.ForceField(*files)


def create_system(forcefield: app.ForceField, topology: app.Topology, cfg: dict[str, Any]) -> openmm.System:
    constraints = app.HBonds if cfg.get("constraints") == "HBonds" else None
    system = forcefield.createSystem(
        topology,
        nonbondedMethod=app.PME,
        nonbondedCutoff=float(cfg["nonbonded_cutoff_nm"]) * unit.nanometer,
        constraints=constraints,
        rigidWater=bool(cfg["rigid_water"]),
        removeCMMotion=bool(cfg["remove_cm_motion"]),
        ewaldErrorTolerance=float(cfg["ewald_error_tolerance"]),
    )
    return system


def state_reporter(path: Path, interval: int, total_steps: int) -> app.StateDataReporter:
    return app.StateDataReporter(
        str(path), interval, step=True, time=True, potentialEnergy=True, kineticEnergy=True,
        totalEnergy=True, temperature=True, volume=True, density=True, speed=True,
        elapsedTime=True, remainingTime=True, totalSteps=total_steps, separator=","
    )


def run_staged_simulation(
    run_dir: Path,
    topology: app.Topology,
    positions,
    forcefield: app.ForceField,
    cfg: dict[str, Any],
    membrane: bool = False,
    restraint_indices: list[int] | None = None,
    finish_run_manifest: bool = True,
) -> None:
    system = create_system(forcefield, topology, cfg)
    if restraint_indices is None:
        restraint_indices = heavy_indices(
            topology,
            include_ligand=not membrane,
        )
    add_positional_restraints(
        system, topology, positions, restraint_indices,
        float(cfg["npt_restraint_schedule_kj_mol_nm2"][0]),
    )
    if membrane:
        barostat = openmm.MonteCarloMembraneBarostat(
            float(cfg["pressure_bar"]) * unit.bar,
            float(cfg["membrane_surface_tension_bar_nm"]) * unit.bar * unit.nanometer,
            float(cfg["temperature_kelvin"]) * unit.kelvin,
            openmm.MonteCarloMembraneBarostat.XYIsotropic,
            openmm.MonteCarloMembraneBarostat.ZFree,
            25,
        )
    else:
        barostat = openmm.MonteCarloBarostat(
            float(cfg["pressure_bar"]) * unit.bar,
            float(cfg["temperature_kelvin"]) * unit.kelvin,
            25,
        )
    barostat.setRandomNumberSeed(int(cfg["seed"]) + 17)
    barostat.setFrequency(0)
    system.addForce(barostat)
    serialize_system(system, run_dir / "prepared" / "system.xml")

    platform_obj, properties, available = openmm_platform(cfg["platform"], cfg["cuda_precision"])
    integrator = openmm.LangevinMiddleIntegrator(
        float(cfg["temperature_kelvin"]) * unit.kelvin,
        float(cfg["friction_per_ps"]) / unit.picosecond,
        float(cfg["timestep_fs"]) * unit.femtosecond,
    )
    integrator.setRandomNumberSeed(int(cfg["seed"]))
    simulation = app.Simulation(topology, system, integrator, platform_obj, properties)
    simulation.context.setPositions(positions)

    initial = simulation.context.getState(getEnergy=True)
    initial_energy = initial.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
    simulation.minimizeEnergy(maxIterations=int(cfg["minimization_max_iterations"]))
    minimized = simulation.context.getState(getEnergy=True, getPositions=True)
    minimized_energy = minimized.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
    with (run_dir / "prepared" / "minimized.pdb").open("w", encoding="utf-8") as handle:
        app.PDBFile.writeFile(topology, minimized.getPositions(), handle, keepIds=True)
    write_json(run_dir / "simulation" / "minimization.json", {
        "initial_potential_kj_mol": initial_energy,
        "minimized_potential_kj_mol": minimized_energy,
        "max_iterations": int(cfg["minimization_max_iterations"]),
    })
    simulation.context.setVelocitiesToTemperature(float(cfg["temperature_kelvin"]) * unit.kelvin, int(cfg["seed"]))

    dt_fs = float(cfg["timestep_fs"])
    nvt_steps = steps_for_ps(float(cfg["nvt_ps"]), dt_fs)
    eq_interval = interval_steps(min(float(cfg["output_stride_ps"]), max(0.2, float(cfg["nvt_ps"]) / 20.0)), dt_fs)
    simulation.reporters = [state_reporter(run_dir / "simulation" / "equil_nvt.csv", eq_interval, nvt_steps)]
    with Timer() as t_nvt:
        simulation.step(nvt_steps)
    write_state_and_pdb(simulation, run_dir / "simulation", "equil_nvt_final")

    barostat.setFrequency(25)
    simulation.context.reinitialize(preserveState=True)
    npt_segment_steps = steps_for_ps(float(cfg["npt_segment_ps"]), dt_fs)
    npt_times = []
    for i, k in enumerate(cfg["npt_restraint_schedule_kj_mol_nm2"], start=1):
        simulation.context.setParameter("k", float(k))
        simulation.reporters = [
            state_reporter(
                run_dir / "simulation" / f"equil_npt_{i:02d}.csv",
                eq_interval,
                simulation.currentStep + npt_segment_steps,
            )
        ]
        with Timer() as timer:
            simulation.step(npt_segment_steps)
        npt_times.append(timer.elapsed_seconds)
        write_state_and_pdb(simulation, run_dir / "simulation", f"equil_npt_{i:02d}_final")

    simulation.context.setParameter("k", 0.0)
    preproduction_wall_seconds = None
    preproduction_ps = float(cfg.get("preproduction_ps", 0.0))
    if preproduction_ps > 0.0:
        preproduction_steps = steps_for_ps(preproduction_ps, dt_fs)
        simulation.reporters = [
            state_reporter(
                run_dir / "simulation" / "equil_unrestrained.csv",
                eq_interval,
                simulation.currentStep + preproduction_steps,
            )
        ]
        with Timer() as t_preproduction:
            simulation.step(preproduction_steps)
        preproduction_wall_seconds = t_preproduction.elapsed_seconds
        write_state_and_pdb(
            simulation,
            run_dir / "simulation",
            "equil_unrestrained_final",
        )

    production_steps = steps_for_ps(float(cfg["production_ps"]), dt_fs)
    output_interval = interval_steps(float(cfg["output_stride_ps"]), dt_fs)
    checkpoint_interval = interval_steps(float(cfg["checkpoint_stride_ps"]), dt_fs)
    simulation.reporters = [
        app.DCDReporter(str(run_dir / "simulation" / "production.dcd"), output_interval, enforcePeriodicBox=True),
        state_reporter(
            run_dir / "simulation" / "production.csv",
            output_interval,
            simulation.currentStep + production_steps,
        ),
        app.CheckpointReporter(str(run_dir / "simulation" / "production.chk"), checkpoint_interval),
    ]
    with Timer() as t_prod:
        simulation.step(production_steps)
    write_state_and_pdb(simulation, run_dir / "simulation", "production_final")

    ns_day = (float(cfg["production_ps"]) / 1000.0) / (t_prod.elapsed_seconds / 86400.0)
    write_json(run_dir / "simulation" / "performance.json", {
        "available_platforms": available,
        "selected_platform": cfg["platform"],
        "cuda_precision": cfg["cuda_precision"],
        "nvt_wall_seconds": t_nvt.elapsed_seconds,
        "npt_segment_wall_seconds": npt_times,
        "preproduction_wall_seconds": preproduction_wall_seconds,
        "production_wall_seconds": t_prod.elapsed_seconds,
        "production_ns_per_day": ns_day,
        "production_steps": production_steps,
        "restraint_atom_count": len(restraint_indices),
        "membrane_barostat": membrane,
    })
    if finish_run_manifest:
        finish_manifest(run_dir, "SIMULATION_COMPLETE")
