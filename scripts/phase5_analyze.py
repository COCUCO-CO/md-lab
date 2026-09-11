#!/usr/bin/env python
# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MPLCONFIGDIR", "/tmp/mdlab-mpl-cache")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/mdlab-cache")

import matplotlib.pyplot as plt
import mdtraj as md
import numpy as np
import openmm
from openmm import app, unit
import pandas as pd

from mdlab.analysis_utils import trajectory_times_from_log
from mdlab.core import (
    finish_manifest,
    latest_run,
    openmm_platform,
    read_json,
    resolve_config,
    write_json,
)


VISUAL_CHECKS = [
    "binding_pose_present_pass",
    "membrane_embedded_pass",
    "no_obvious_clash_pass",
    "bilayer_continuous_pass",
    "solvent_both_sides_pass",
]


def set_progress(profile: str, state: str) -> None:
    import subprocess

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


def col(dataframe: pd.DataFrame, token: str) -> str:
    for column in dataframe.columns:
        if token.lower() in column.lower():
            return column
    raise KeyError(f"Missing column {token!r}: {list(dataframe.columns)}")


def minimum_image(delta: np.ndarray, lengths: np.ndarray) -> np.ndarray:
    return delta - lengths * np.round(delta / lengths)


def periodic_center(values: np.ndarray, length: float) -> float:
    angles = 2.0 * np.pi * np.asarray(values, dtype=float) / float(length)
    return float(
        np.arctan2(np.mean(np.sin(angles)), np.mean(np.cos(angles)))
        * length
        / (2.0 * np.pi)
    )


def save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def equilibration_logs(
    condition_dir: Path,
) -> list[tuple[str, pd.DataFrame]]:
    stages = [
        ("NVT", "equil_nvt.csv"),
        ("NPT 1000", "equil_npt_01.csv"),
        ("NPT 500", "equil_npt_02.csv"),
        ("NPT 100", "equil_npt_03.csv"),
        ("NPT 10", "equil_npt_04.csv"),
        ("Unrestrained", "equil_unrestrained.csv"),
    ]
    return [
        (label, pd.read_csv(condition_dir / "simulation" / filename))
        for label, filename in stages
    ]


def equilibration_dashboard(
    condition_name: str,
    logs: list[tuple[str, pd.DataFrame]],
    temperature_kelvin: float,
    path: Path,
) -> None:
    figure, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for label, dataframe in logs:
        times = dataframe[col(dataframe, "Time")]
        axes[0].plot(
            times,
            dataframe[col(dataframe, "Temperature")],
            label=label,
        )
        axes[1].plot(
            times,
            dataframe[col(dataframe, "Density")],
            label=label,
        )
    axes[0].axhline(
        temperature_kelvin,
        color="black",
        linestyle="--",
        linewidth=1,
        label="target",
    )
    axes[0].set_ylabel("Temperature (K)")
    axes[0].legend(ncol=4, fontsize=7)
    axes[1].set(
        xlabel="Cumulative simulation time (ps)",
        ylabel="Density (g/mL)",
    )
    figure.suptitle(f"{condition_name}: staged equilibration")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def select_residue_atoms(
    topology: md.Topology,
    residue_id: int,
    names: set[str] | None = None,
    heavy_only: bool = True,
) -> np.ndarray:
    result = [
        atom.index
        for residue in topology.residues
        if residue.is_protein and residue.resSeq == residue_id
        for atom in residue.atoms
        if (not heavy_only or atom.element.symbol != "H")
        and (names is None or atom.name in names)
    ]
    if not result:
        raise RuntimeError(f"No atoms selected for protein residue {residue_id}")
    return np.asarray(result, dtype=int)


def resname_atom_indices(
    topology: md.Topology,
    resname: str,
    atom_name: str | None = None,
    heavy_only: bool = False,
) -> np.ndarray:
    return np.asarray(
        [
            atom.index
            for residue in topology.residues
            if residue.name == resname
            for atom in residue.atoms
            if (atom_name is None or atom.name == atom_name)
            and (
                not heavy_only
                or atom.element is None
                or atom.element.symbol != "H"
            )
        ],
        dtype=int,
    )


def reimage_component_near_anchor(
    trajectory: md.Trajectory,
    component_indices: np.ndarray,
    anchor_indices: np.ndarray,
) -> np.ndarray:
    if trajectory.unitcell_lengths is None:
        raise RuntimeError("Periodic component reimaging requires box lengths")
    translations = np.zeros((trajectory.n_frames, 3), dtype=float)
    for frame in range(trajectory.n_frames):
        component_center = np.mean(
            trajectory.xyz[frame, component_indices], axis=0
        )
        anchor_center = np.mean(
            trajectory.xyz[frame, anchor_indices], axis=0
        )
        box = trajectory.unitcell_lengths[frame]
        translation = -box * np.round(
            (component_center - anchor_center) / box
        )
        trajectory.xyz[frame, component_indices] += translation
        translations[frame] = translation
    return translations


def minimum_distance_series(
    trajectory: md.Trajectory,
    first_indices: np.ndarray,
    second_indices: np.ndarray,
) -> np.ndarray:
    delta = (
        trajectory.xyz[:, first_indices, None, :]
        - trajectory.xyz[:, None, second_indices, :]
    )
    return np.min(np.linalg.norm(delta, axis=-1), axis=(1, 2))


def maximum_covalent_bond_nm(
    trajectory: md.Trajectory,
    bond_pairs: np.ndarray,
    chunk_size: int = 20,
) -> float:
    if len(bond_pairs) == 0:
        raise RuntimeError("Prepared topology contains no bonds")
    maximum = 0.0
    for start in range(0, trajectory.n_frames, chunk_size):
        distances = md.compute_distances(
            trajectory[start : start + chunk_size],
            bond_pairs,
            periodic=True,
        )
        maximum = max(maximum, float(np.max(distances)))
    return maximum


def checkpoint_audit(
    condition_dir: Path,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    pdb = app.PDBFile(str(condition_dir / "prepared" / "system.pdb"))
    system = openmm.XmlSerializer.deserialize(
        (condition_dir / "prepared" / "system.xml").read_text(encoding="utf-8")
    )
    membrane_barostats = [
        force
        for force in system.getForces()
        if isinstance(force, openmm.MonteCarloMembraneBarostat)
    ]
    if len(membrane_barostats) != 1:
        raise RuntimeError("Serialized Phase 5 system lacks one membrane barostat")
    barostat_pressure = membrane_barostats[0].getDefaultPressure().value_in_unit(
        unit.bar
    )
    integrator = openmm.LangevinMiddleIntegrator(
        float(cfg["temperature_kelvin"]) * unit.kelvin,
        float(cfg["friction_per_ps"]) / unit.picosecond,
        float(cfg["timestep_fs"]) * unit.femtosecond,
    )
    platform, properties, _ = openmm_platform(
        str(cfg["platform"]),
        str(cfg["cuda_precision"]),
    )
    simulation = app.Simulation(
        pdb.topology,
        system,
        integrator,
        platform,
        properties,
    )
    simulation.loadCheckpoint(
        str(condition_dir / "simulation" / "production.chk")
    )
    state = simulation.context.getState(
        getPositions=True,
        getEnergy=True,
    )
    positions = state.getPositions(asNumpy=True).value_in_unit(unit.nanometer)
    result = {
        "checkpoint_readable_pass": bool(
            np.isfinite(positions).all()
            and np.isfinite(
                state.getPotentialEnergy().value_in_unit(unit.kilojoule_per_mole)
            )
        ),
        "checkpoint_time_ps": float(
            state.getTime().value_in_unit(unit.picosecond)
        ),
        "membrane_barostat_present_pass": True,
        "barostat_pressure_bar": float(barostat_pressure),
        "barostat_pressure_pass": bool(
            abs(float(barostat_pressure) - float(cfg["pressure_bar"])) < 1e-8
        ),
    }
    del simulation
    del integrator
    return result


def cross_section_figure(
    trajectory: md.Trajectory,
    frame: int,
    protein_heavy: np.ndarray,
    ligand_heavy: np.ndarray,
    lipid_heavy: np.ndarray,
    phosphorus: np.ndarray,
    water_oxygen: np.ndarray,
    membrane_center_z: float,
    path: Path,
) -> None:
    box = trajectory.unitcell_lengths[frame]
    protein_center_x = periodic_center(
        trajectory.xyz[frame, protein_heavy, 0], box[0]
    )
    protein_center_y = periodic_center(
        trajectory.xyz[frame, protein_heavy, 1], box[1]
    )

    def relative(indices: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        xyz = trajectory.xyz[frame, indices]
        return (
            minimum_image(xyz[:, 0] - protein_center_x, box[0]),
            minimum_image(xyz[:, 1] - protein_center_y, box[1]),
            minimum_image(xyz[:, 2] - membrane_center_z, box[2]),
        )

    plt.figure(figsize=(8, 6))
    for indices, color, size, label, alpha in [
        (water_oxygen, "#3182bd", 4, "water O", 0.25),
        (lipid_heavy, "#969696", 3, "POPC heavy", 0.18),
        (phosphorus, "#f16913", 20, "POPC P", 0.75),
        (protein_heavy, "#cb181d", 5, "protein heavy", 0.45),
        (ligand_heavy, "#31a354", 35, "ligand heavy", 0.95),
    ]:
        x, y, z = relative(indices)
        mask = np.abs(y) <= 0.6
        plt.scatter(x[mask], z[mask], s=size, color=color, alpha=alpha, label=label)
    plt.xlim(-box[0] / 2.0, box[0] / 2.0)
    plt.ylim(-box[2] / 2.0, box[2] / 2.0)
    plt.xlabel("x relative to receptor center (nm)")
    plt.ylabel("z relative to membrane center (nm)")
    plt.title("Final receptor/ligand/membrane cross-section (|y| ≤ 0.6 nm)")
    plt.legend(fontsize=7)
    save(path)


def analyze_condition(
    condition_name: str,
    condition: dict[str, Any],
    cfg: dict[str, Any],
    run: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    condition_dir = run / "systems" / condition_name
    figures = condition_dir / "figures"
    analysis = condition_dir / "analysis"
    figures.mkdir(exist_ok=True)
    analysis.mkdir(exist_ok=True)
    audit = read_json(condition_dir / "prepared" / "preparation_audit.json")
    performance = read_json(condition_dir / "simulation" / "performance.json")
    log = pd.read_csv(condition_dir / "simulation" / "production.csv")
    staged_equilibration = equilibration_logs(condition_dir)
    unrestrained_log = staged_equilibration[-1][1]
    equilibration_dashboard(
        condition_name,
        staged_equilibration,
        float(cfg["temperature_kelvin"]),
        figures / "equilibration_dashboard.png",
    )
    time_column = col(log, "Time")
    temperature_column = col(log, "Temperature")
    potential_column = col(log, "Potential Energy")
    total_energy_column = col(log, "Total Energy")
    trajectory = md.load(
        str(condition_dir / "simulation" / "production.dcd"),
        top=str(condition_dir / "prepared" / "system.pdb"),
    )
    if trajectory.unitcell_lengths is None or trajectory.unitcell_angles is None:
        raise RuntimeError(f"{condition_name} trajectory lacks periodic box data")
    if not np.allclose(trajectory.unitcell_angles, 90.0, atol=1e-3):
        raise RuntimeError("Phase 5 analysis requires an orthorhombic box")
    times = trajectory_times_from_log(log, time_column, trajectory.n_frames)
    trajectory.make_molecules_whole(inplace=True)

    tm_ids = {
        residue_id
        for start, end in cfg["transmembrane_alignment_ranges"]
        for residue_id in range(int(start), int(end) + 1)
    }
    tm_ca = np.asarray(
        [
            atom.index
            for residue in trajectory.topology.residues
            if residue.is_protein and residue.resSeq in tm_ids
            for atom in residue.atoms
            if atom.name == "CA"
        ],
        dtype=int,
    )
    ligand_heavy = resname_atom_indices(
        trajectory.topology,
        str(condition["ligand_resname"]),
        heavy_only=True,
    )
    ligand_all = resname_atom_indices(
        trajectory.topology,
        str(condition["ligand_resname"]),
    )
    protein_heavy = trajectory.topology.select("protein and not element H")
    lipid_heavy = trajectory.topology.select(
        f"resname {cfg['lipid_resname']} and not element H"
    )
    phosphorus = trajectory.topology.select(
        f"resname {cfg['lipid_resname']} and name P"
    )
    water_oxygen = trajectory.topology.select("water and name O")
    ligand_n = resname_atom_indices(
        trajectory.topology,
        str(condition["ligand_resname"]),
        atom_name=str(condition["ligand_protonation_atom"]),
    )
    if (
        len(tm_ca) < 150
        or len(ligand_heavy) == 0
        or len(ligand_n) != 1
        or len(phosphorus) < 20
        or len(water_oxygen) == 0
    ):
        raise RuntimeError(f"Required Phase 5 selections failed for {condition_name}")

    ligand_image_translations = reimage_component_near_anchor(
        trajectory,
        ligand_all,
        protein_heavy,
    )
    aligned = trajectory[:]
    aligned.superpose(aligned, 0, atom_indices=tm_ca, ref_atom_indices=tm_ca)
    tm_delta = aligned.xyz[:, tm_ca] - aligned.xyz[0, tm_ca]
    tm_rmsd = np.sqrt(np.mean(np.sum(tm_delta * tm_delta, axis=2), axis=1))
    ligand_delta = aligned.xyz[:, ligand_heavy] - aligned.xyz[0, ligand_heavy]
    ligand_rmsd = np.sqrt(
        np.mean(np.sum(ligand_delta * ligand_delta, axis=2), axis=1)
    )
    ligand_com = np.mean(aligned.xyz[:, ligand_heavy], axis=1)
    ligand_com_distance = np.linalg.norm(ligand_com - ligand_com[0], axis=1)

    d155 = select_residue_atoms(
        aligned.topology, 155, names={"OD1", "OD2"}
    )
    c227 = select_residue_atoms(aligned.topology, 227)
    l229 = select_residue_atoms(aligned.topology, 229)
    s239 = select_residue_atoms(aligned.topology, 239)
    n343 = select_residue_atoms(aligned.topology, 343)
    anchor_distance = minimum_distance_series(aligned, ligand_n, d155)
    c227_distance = minimum_distance_series(aligned, ligand_heavy, c227)
    l229_distance = minimum_distance_series(aligned, ligand_heavy, l229)
    s239_distance = minimum_distance_series(aligned, ligand_heavy, s239)
    n343_distance = minimum_distance_series(aligned, ligand_heavy, n343)
    ecl2_distance = np.minimum(c227_distance, l229_distance)
    deep_distance = np.minimum(s239_distance, n343_distance)

    lengths = trajectory.unitcell_lengths
    membrane_centers = np.asarray(
        [
            periodic_center(
                trajectory.xyz[frame, phosphorus, 2],
                lengths[frame, 2],
            )
            for frame in range(trajectory.n_frames)
        ]
    )
    phosphorus_z = np.asarray(
        [
            minimum_image(
                trajectory.xyz[frame, phosphorus, 2] - membrane_centers[frame],
                lengths[frame, 2],
            )
            for frame in range(trajectory.n_frames)
        ]
    )
    upper_mask = phosphorus_z[0] >= 0.0
    lower_mask = ~upper_mask
    upper_count = int(np.sum(upper_mask))
    lower_count = int(np.sum(lower_mask))
    if upper_count == 0 or lower_count == 0:
        raise RuntimeError("Could not identify both Phase 5 membrane leaflets")
    upper_z = np.mean(phosphorus_z[:, upper_mask], axis=1)
    lower_z = np.mean(phosphorus_z[:, lower_mask], axis=1)
    thickness = upper_z - lower_z
    area_per_lipid = (
        lengths[:, 0]
        * lengths[:, 1]
        / ((upper_count + lower_count) / 2.0)
    )
    water_z = np.asarray(
        [
            minimum_image(
                trajectory.xyz[frame, water_oxygen, 2] - membrane_centers[frame],
                lengths[frame, 2],
            )
            for frame in range(trajectory.n_frames)
        ]
    )
    solvent_margin_nm = 0.35
    upper_outer_water = np.sum(
        water_z > (upper_z + solvent_margin_nm)[:, None], axis=1
    )
    lower_outer_water = np.sum(
        water_z < (lower_z - solvent_margin_nm)[:, None], axis=1
    )

    openmm_topology = app.PDBFile(
        str(condition_dir / "prepared" / "system.pdb")
    ).topology
    bond_pairs = np.asarray(
        [
            [first.index, second.index]
            for first, second in openmm_topology.bonds()
        ],
        dtype=int,
    )
    max_bond = maximum_covalent_bond_nm(trajectory, bond_pairs)
    timeseries = pd.DataFrame(
        {
            "time_ps": times,
            "tm_ca_rmsd_nm": tm_rmsd,
            "ligand_aligned_rmsd_nm": ligand_rmsd,
            "ligand_com_distance_from_initial_nm": ligand_com_distance,
            "ligand_n_d155_carboxylate_nm": anchor_distance,
            "ligand_c227_nm": c227_distance,
            "ligand_l229_nm": l229_distance,
            "ecl2_contact_distance_nm": ecl2_distance,
            "ligand_s239_nm": s239_distance,
            "ligand_n343_nm": n343_distance,
            "deep_contact_distance_nm": deep_distance,
            "area_per_lipid_nm2": area_per_lipid,
            "phosphate_thickness_nm": thickness,
            "upper_outer_water_oxygen_count": upper_outer_water,
            "lower_outer_water_oxygen_count": lower_outer_water,
            "box_x_nm": lengths[:, 0],
            "box_y_nm": lengths[:, 1],
            "box_z_nm": lengths[:, 2],
        }
    )
    timeseries.to_csv(analysis / "timeseries.csv", index=False)

    figure, axes = plt.subplots(3, 1, figsize=(9, 9), sharex=True)
    axes[0].plot(log[time_column], log[temperature_column])
    axes[0].axhline(cfg["temperature_kelvin"], color="black", linestyle="--")
    axes[0].set_ylabel("Temperature (K)")
    axes[1].plot(log[time_column], log[potential_column], label="potential")
    axes[1].plot(log[time_column], log[total_energy_column], label="total")
    axes[1].set_ylabel("Energy (kJ/mol)")
    axes[1].legend()
    axes[2].plot(times, tm_rmsd, label="TM Cα RMSD")
    axes[2].plot(times, ligand_rmsd, label="ligand aligned RMSD")
    axes[2].set(xlabel="Time (ps)", ylabel="RMSD (nm)")
    axes[2].legend()
    figure.suptitle(f"{condition_name}: production sanity metrics")
    figure.tight_layout()
    figure.savefig(figures / "production_dashboard.png", dpi=180)
    plt.close(figure)

    plt.figure(figsize=(9, 5))
    plt.plot(times, anchor_distance, label="cationic N–D155")
    plt.plot(times, ecl2_distance, label="min(C227,L229)")
    plt.plot(times, deep_distance, label="min(S239,N343)")
    plt.axhline(
        cfg["d155_anchor_cutoff_nm"],
        color="black",
        linestyle=":",
        label="D155 diagnostic cutoff",
    )
    plt.axhline(
        cfg["ligand_contact_cutoff_nm"],
        color="gray",
        linestyle="--",
        label="contact cutoff",
    )
    plt.xlabel("Time (ps)")
    plt.ylabel("Minimum heavy-atom distance (nm)")
    plt.title(f"{condition_name}: pre-registered contact distances")
    plt.legend()
    save(figures / "contact_distances.png")

    figure, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    axes[0].plot(times, area_per_lipid)
    axes[0].axhspan(
        cfg["gates"]["area_per_lipid_nm2_min"],
        cfg["gates"]["area_per_lipid_nm2_max"],
        alpha=0.15,
    )
    axes[0].set_ylabel("Area/lipid (nm²)")
    axes[1].plot(times, thickness)
    axes[1].axhspan(
        cfg["gates"]["membrane_thickness_nm_min"],
        cfg["gates"]["membrane_thickness_nm_max"],
        alpha=0.15,
    )
    axes[1].set(xlabel="Time (ps)", ylabel="P–P thickness (nm)")
    figure.suptitle(f"{condition_name}: membrane sanity metrics")
    figure.tight_layout()
    figure.savefig(figures / "membrane_metrics.png", dpi=180)
    plt.close(figure)
    cross_section_figure(
        trajectory,
        trajectory.n_frames - 1,
        protein_heavy,
        ligand_heavy,
        lipid_heavy,
        phosphorus,
        water_oxygen,
        membrane_centers[-1],
        figures / "final_cross_section.png",
    )

    mean_temperature = float(log[temperature_column].mean())
    mean_area = float(np.mean(area_per_lipid))
    mean_thickness = float(np.mean(thickness))
    expected_rows = int(
        round(float(cfg["production_ps"]) / float(cfg["output_stride_ps"]))
    )
    equilibration_stride_ps = min(
        float(cfg["output_stride_ps"]),
        max(0.2, float(cfg["nvt_ps"]) / 20.0),
    )
    expected_nvt_rows = int(
        round(float(cfg["nvt_ps"]) / equilibration_stride_ps)
    )
    expected_npt_rows = int(
        round(float(cfg["npt_segment_ps"]) / equilibration_stride_ps)
    )
    expected_preproduction_rows = int(
        round(
            float(cfg["preproduction_ps"]) / equilibration_stride_ps
        )
    )
    contact_cutoff = float(cfg["ligand_contact_cutoff_nm"])
    anchor_cutoff = float(cfg["d155_anchor_cutoff_nm"])
    checkpoint = checkpoint_audit(condition_dir, cfg)
    required_figures = [
        "equilibration_dashboard.png",
        "production_dashboard.png",
        "contact_distances.png",
        "membrane_metrics.png",
        "final_cross_section.png",
    ]
    checks = {
        "finite_values_pass": bool(
            np.isfinite(trajectory.xyz).all()
            and np.isfinite(log.select_dtypes(include=[np.number]).to_numpy()).all()
            and all(
                np.isfinite(
                    dataframe.select_dtypes(include=[np.number]).to_numpy()
                ).all()
                for _, dataframe in staged_equilibration
            )
            and np.isfinite(timeseries.to_numpy()).all()
        ),
        "approved_construct_pass": bool(
            audit["polymer_residue_count"] == 367
            and audit["retained_source_waters"] == 0
            and audit["retained_source_heterogens"]
            == {condition["ligand_resname"]: 1}
        ),
        "loop_validation_pass": bool(
            audit["loop_gates"]["topology_and_sequence_pass"]
            and audit["loop_gates"]["chirality"]["pass"]
            and audit["loop_gates"][
                "minimum_nonbonded_heavy_atom_distance_nm"
            ]
            >= cfg["gates"]["minimum_loop_nonbonded_heavy_atom_distance_nm"]
            and audit["loop_gates"]["maximum_covalent_bond_nm"]
            <= cfg["gates"]["max_loop_covalent_bond_nm"]
        ),
        "ligand_chemistry_pass": bool(
            audit["ligand"]["formal_charge"]
            == condition["ligand_formal_charge"]
            and abs(audit["ligand"]["am1bcc_charge_sum_e"] - 1.0) < 1e-6
        ),
        "all_atoms_parameterized_pass": bool(
            audit["parameterization"]["status"] == "PASS"
            and audit["parameterization"]["parameterized_particles"]
            == trajectory.n_atoms
        ),
        "prepared_intercomponent_geometry_pass": bool(
            audit["minimum_intercomponent_heavy_atom_distance_nm"]
            >= cfg["gates"]["minimum_intercomponent_heavy_atom_distance_nm"]
        ),
        "temperature_pass": bool(
            abs(mean_temperature - cfg["temperature_kelvin"])
            / cfg["temperature_kelvin"]
            <= cfg["gates"]["max_temperature_relative_error"]
        ),
        "area_per_lipid_pass": bool(
            cfg["gates"]["area_per_lipid_nm2_min"]
            <= mean_area
            <= cfg["gates"]["area_per_lipid_nm2_max"]
        ),
        "thickness_pass": bool(
            cfg["gates"]["membrane_thickness_nm_min"]
            <= mean_thickness
            <= cfg["gates"]["membrane_thickness_nm_max"]
        ),
        "tm_rmsd_pass": bool(
            float(np.max(tm_rmsd))
            <= cfg["gates"]["max_receptor_tm_ca_rmsd_nm"]
        ),
        "ligand_rmsd_pass": bool(
            float(np.max(ligand_rmsd))
            <= cfg["gates"]["max_ligand_aligned_rmsd_nm"]
        ),
        "ligand_com_pass": bool(
            float(np.max(ligand_com_distance))
            <= cfg["gates"]["max_ligand_com_distance_from_initial_nm"]
        ),
        "leaflet_balance_pass": bool(
            abs(upper_count - lower_count)
            <= cfg["gates"]["max_leaflet_count_difference"]
        ),
        "outer_solvent_coverage_pass": bool(
            np.min(upper_outer_water)
            >= cfg["gates"]["minimum_outer_slab_water_oxygens"]
            and np.min(lower_outer_water)
            >= cfg["gates"]["minimum_outer_slab_water_oxygens"]
        ),
        "bond_geometry_pass": bool(
            max_bond <= cfg["gates"]["max_unphysical_bond_nm"]
        ),
        "thermodynamic_rows_pass": bool(len(log) == expected_rows),
        "trajectory_readable_pass": bool(
            trajectory.n_frames == expected_rows and trajectory.n_atoms > 0
        ),
        "unrestrained_preproduction_pass": bool(
            len(unrestrained_log) == expected_preproduction_rows
        ),
        "equilibration_rows_pass": bool(
            len(staged_equilibration[0][1]) == expected_nvt_rows
            and all(
                len(dataframe) == expected_npt_rows
                for _, dataframe in staged_equilibration[1:5]
            )
            and len(unrestrained_log) == expected_preproduction_rows
        ),
        "required_figures_generated_pass": all(
            (figures / filename).exists()
            and (figures / filename).stat().st_size > 0
            for filename in required_figures
        ),
        **checkpoint,
    }
    metrics = {
        "mean_temperature_K": mean_temperature,
        "mean_area_per_lipid_nm2": mean_area,
        "mean_membrane_thickness_nm": mean_thickness,
        "max_tm_ca_rmsd_nm": float(np.max(tm_rmsd)),
        "max_ligand_aligned_rmsd_nm": float(np.max(ligand_rmsd)),
        "max_ligand_com_distance_from_initial_nm": float(
            np.max(ligand_com_distance)
        ),
        "max_covalent_bond_nm": max_bond,
        "lipid_count_upper_leaflet": upper_count,
        "lipid_count_lower_leaflet": lower_count,
        "minimum_upper_outer_water_oxygen_count": int(
            np.min(upper_outer_water)
        ),
        "minimum_lower_outer_water_oxygen_count": int(
            np.min(lower_outer_water)
        ),
        "trajectory_frames": trajectory.n_frames,
        "thermodynamic_rows": len(log),
        "equilibration_rows": {
            label: len(dataframe)
            for label, dataframe in staged_equilibration
        },
        "ecl2_contact_occupancy": float(np.mean(ecl2_distance <= contact_cutoff)),
        "deep_contact_occupancy": float(np.mean(deep_distance <= contact_cutoff)),
        "d155_anchor_occupancy": float(np.mean(anchor_distance <= anchor_cutoff)),
        "mean_d155_anchor_distance_nm": float(np.mean(anchor_distance)),
        "production_ns_per_day": float(performance["production_ns_per_day"]),
        "maximum_ligand_periodic_image_translation_nm": float(
            np.max(np.linalg.norm(ligand_image_translations, axis=1))
        ),
    }
    write_json(analysis / "metrics.json", metrics)
    write_json(analysis / "checks.json", checks)
    return metrics, checks


def finalize(
    args: argparse.Namespace,
    cfg: dict[str, Any],
    run: Path,
    metrics: dict[str, dict[str, Any]],
    checks: dict[str, dict[str, Any]],
) -> None:
    if args.figures_only:
        write_json(
            run / "analysis" / "preliminary_metrics.json",
            {"status": "FIGURES_READY_FOR_VISUAL_INSPECTION", "conditions": metrics},
        )
        print(
            json.dumps(
                {
                    "status": "FIGURES_READY_FOR_VISUAL_INSPECTION",
                    "conditions": metrics,
                },
                indent=2,
            )
        )
        return

    visual_path = run / "analysis" / "visual_inspection.json"
    if not visual_path.exists():
        raise RuntimeError(
            "Mandatory Phase 5 visual inspection is missing. Generate figures "
            "with --figures-only, inspect both systems and record "
            "analysis/visual_inspection.json."
        )
    visual = read_json(visual_path)
    visual_conditions = visual.get("conditions", {})
    visual_pass = {}
    for condition_name in cfg["conditions"]:
        record = visual_conditions.get(condition_name, {})
        missing = [key for key in VISUAL_CHECKS if key not in record]
        if missing:
            raise RuntimeError(
                f"Visual record for {condition_name} lacks checks: {missing}"
            )
        passed = all(bool(record[key]) for key in VISUAL_CHECKS)
        visual_pass[condition_name] = passed
        checks[condition_name]["visual_inspection_pass"] = passed

    condition_status = {
        condition_name: (
            "PASS"
            if all(
                bool(value)
                for key, value in condition_checks.items()
                if key.endswith("_pass")
            )
            else "FAIL"
        )
        for condition_name, condition_checks in checks.items()
    }
    status = (
        "PASS"
        if all(value == "PASS" for value in condition_status.values())
        else "FAIL"
    )
    write_json(
        run / "gate.json",
        {
            "phase": 5,
            "profile": args.profile,
            "status": status,
            "condition_status": condition_status,
            "conditions": checks,
        },
    )
    comparison = {
        "ecl2_contact_occupancy_lisuride_minus_lsd": (
            metrics["lisuride"]["ecl2_contact_occupancy"]
            - metrics["lsd"]["ecl2_contact_occupancy"]
        ),
        "deep_contact_occupancy_lsd_minus_lisuride": (
            metrics["lsd"]["deep_contact_occupancy"]
            - metrics["lisuride"]["deep_contact_occupancy"]
        ),
        "interpretation": (
            "Mechanical tutorial-profile observation only; not a research "
            "replica result and not evidence for biological mechanism."
        ),
    }
    write_json(run / "analysis" / "contact_comparison.json", comparison)
    report = f"""# Phase 5 report — {args.profile}

## Scope

This is a mechanical `{args.profile}` gate for the approved matched inactive
7WC6/7WC7 5-HT2A–BRIL systems. It is not a convergence analysis and is not
interpreted as evidence for activation, signaling, psychedelic action or a
biological mechanism.

## Preparation observations

- Both conditions contain the approved 367-residue engineered polymer,
  including modeled ICL2 181–187 and BRIL linker 1061–1065.
- Source waters and crystallization/LCP heterogens were removed; only the
  experimental ligand pose was retained.
- Ligands were built from CCD SDF chemical graphs, protonated at the approved
  nitrogen and assigned OpenFF 2.2.1/AM1-BCC parameters with net charge +1.
- Both systems use ff19SB, Lipid21 POPC, TIP3P, 0.15 M NaCl, 310 K and 1 bar.

## Production observations

| Metric | LSD / 7WC6 | Lisuride / 7WC7 |
|---|---:|---:|
| Mean temperature (K) | {metrics["lsd"]["mean_temperature_K"]:.2f} | {metrics["lisuride"]["mean_temperature_K"]:.2f} |
| Mean area/lipid (nm²) | {metrics["lsd"]["mean_area_per_lipid_nm2"]:.4f} | {metrics["lisuride"]["mean_area_per_lipid_nm2"]:.4f} |
| Mean P–P thickness (nm) | {metrics["lsd"]["mean_membrane_thickness_nm"]:.4f} | {metrics["lisuride"]["mean_membrane_thickness_nm"]:.4f} |
| Max TM Cα RMSD (nm) | {metrics["lsd"]["max_tm_ca_rmsd_nm"]:.4f} | {metrics["lisuride"]["max_tm_ca_rmsd_nm"]:.4f} |
| Max ligand aligned RMSD (nm) | {metrics["lsd"]["max_ligand_aligned_rmsd_nm"]:.4f} | {metrics["lisuride"]["max_ligand_aligned_rmsd_nm"]:.4f} |
| D155 anchor occupancy | {metrics["lsd"]["d155_anchor_occupancy"]:.3f} | {metrics["lisuride"]["d155_anchor_occupancy"]:.3f} |
| ECL2 contact occupancy | {metrics["lsd"]["ecl2_contact_occupancy"]:.3f} | {metrics["lisuride"]["ecl2_contact_occupancy"]:.3f} |
| Deep contact occupancy | {metrics["lsd"]["deep_contact_occupancy"]:.3f} | {metrics["lisuride"]["deep_contact_occupancy"]:.3f} |
| Performance (ns/day) | {metrics["lsd"]["production_ns_per_day"]:.1f} | {metrics["lisuride"]["production_ns_per_day"]:.1f} |

The contact occupancies above are reported as short-run diagnostics only. The
pre-registered directional hypothesis is reserved for the three approved
research replicas per condition and must also be stratified by ICL2 conformer.

## Gate

Overall status: **{status}**. Per-condition status: {condition_status}.
The signed visual-inspection record is `analysis/visual_inspection.json`.
"""
    (run / "REPORT.md").write_text(report, encoding="utf-8")
    (run / "prepared" / "README.md").write_text(
        "# Phase 5 prepared systems\n\n"
        "- [LSD preparation](../systems/lsd/prepared/)\n"
        "- [Lisuride preparation](../systems/lisuride/prepared/)\n",
        encoding="utf-8",
    )
    (run / "simulation" / "README.md").write_text(
        "# Phase 5 simulations\n\n"
        "- [LSD simulation](../systems/lsd/simulation/)\n"
        "- [Lisuride simulation](../systems/lisuride/simulation/)\n",
        encoding="utf-8",
    )
    (run / "figures" / "README.md").write_text(
        "# Phase 5 figures\n\n"
        "- [LSD figures](../systems/lsd/figures/)\n"
        "- [Lisuride figures](../systems/lisuride/figures/)\n"
        "- [Visual-inspection montage](../analysis/visual_inspection_montage.png)\n",
        encoding="utf-8",
    )
    research_links = ""
    if args.profile == "teaching":
        research_links = (
            "- [Research runtime/storage budget](analysis/research_budget.json)\n"
            "- [Proposed research gate]"
            "(../../../state/decisions/DR-005-R1-PREPRODUCTION.md)\n"
        )
    (run / "RUN_INDEX.md").write_text(
        f"# Phase 5 {args.profile} output index\n\n"
        "- [Report](REPORT.md)\n"
        "- [Gate](gate.json)\n"
        "- [Static visual-inspection montage](analysis/visual_inspection_montage.png)\n"
        "- [Equilibration montage](analysis/equilibration_montage.png)\n"
        "- [LSD prepared system](systems/lsd/prepared/)\n"
        "- [LSD simulation](systems/lsd/simulation/)\n"
        "- [LSD figures](systems/lsd/figures/)\n"
        "- [LSD interactive viewer](systems/lsd/visualization/viewer.html)\n"
        "- [Lisuride prepared system](systems/lisuride/prepared/)\n"
        "- [Lisuride simulation](systems/lisuride/simulation/)\n"
        "- [Lisuride figures](systems/lisuride/figures/)\n"
        "- [Lisuride interactive viewer](systems/lisuride/visualization/viewer.html)\n"
        "- [Viewer index](visualization/index.html)\n"
        f"{research_links}",
        encoding="utf-8",
    )
    finish_manifest(
        run,
        "ANALYSIS_COMPLETE" if status == "PASS" else "GATE_FAILED",
        {
            "gate_status": status,
            "analysis_outputs": {
                "report": "REPORT.md",
                "gate": "gate.json",
                "contact_comparison": "analysis/contact_comparison.json",
            },
        },
    )
    if status != "PASS":
        set_progress(args.profile, "GATE_FAILED")
        raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=["quick", "teaching"],
        default="quick",
    )
    parser.add_argument("--figures-only", action="store_true")
    args = parser.parse_args()
    cfg = resolve_config(5, args.profile)
    run = latest_run(5, args.profile)
    (run / "analysis").mkdir(exist_ok=True)
    set_progress(args.profile, "ANALYSIS_RUNNING")
    try:
        metrics = {}
        checks = {}
        for condition_name, condition in cfg["conditions"].items():
            condition_cfg = dict(cfg)
            condition_cfg.update(condition)
            condition_metrics, condition_checks = analyze_condition(
                condition_name,
                condition,
                condition_cfg,
                run,
            )
            metrics[condition_name] = condition_metrics
            checks[condition_name] = condition_checks
        finalize(args, cfg, run, metrics, checks)
    except SystemExit:
        raise
    except Exception as error:
        set_progress(args.profile, "ANALYSIS_FAILED")
        (run / "ANALYSIS_FAILURE.md").write_text(
            "# Phase 5 analysis failure\n\n"
            f"First reported exception: `{type(error).__name__}: {error}`\n",
            encoding="utf-8",
        )
        finish_manifest(
            run,
            "ANALYSIS_FAILED",
            {
                "analysis_error_type": type(error).__name__,
                "analysis_error": str(error),
            },
        )
        raise


if __name__ == "__main__":
    main()
