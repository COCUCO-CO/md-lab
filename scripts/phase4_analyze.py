#!/usr/bin/env python
from __future__ import annotations

import argparse
from itertools import combinations
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

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
    "hydrophobic_region_overlaps_lipid_tails_pass",
    "domains_hydrated_pass",
    "no_lipid_tail_through_protein_core_pass",
    "no_large_vacuum_gap_pass",
    "leaflets_continuous_pass",
    "oligomer_intact_pass",
    "membrane_normal_z_pass",
]


def col(dataframe: pd.DataFrame, token: str) -> str:
    for column in dataframe.columns:
        if token.lower() in column.lower():
            return column
    raise KeyError(f"Missing column {token!r}: {list(dataframe.columns)}")


def save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def minimum_image(delta: np.ndarray, lengths: np.ndarray) -> np.ndarray:
    return delta - lengths * np.round(delta / lengths)


def periodic_center(values: np.ndarray, length: float) -> float:
    angles = 2.0 * np.pi * np.asarray(values, dtype=float) / float(length)
    sine = float(np.mean(np.sin(angles)))
    cosine = float(np.mean(np.cos(angles)))
    if abs(sine) < 1e-12 and abs(cosine) < 1e-12:
        raise RuntimeError("Periodic center is undefined for this distribution")
    return float(np.arctan2(sine, cosine) * length / (2.0 * np.pi))


def chain_ca_groups(topology: md.Topology) -> list[np.ndarray]:
    groups = []
    for chain in topology.chains:
        indices = [
            atom.index
            for residue in chain.residues
            if residue.is_protein
            for atom in residue.atoms
            if atom.name == "CA"
        ]
        if indices:
            groups.append(np.asarray(indices, dtype=int))
    return groups


def protein_rmsd_and_oligomer_distances(
    trajectory: md.Trajectory,
    chain_groups: list[np.ndarray],
) -> tuple[np.ndarray, np.ndarray, float]:
    if len(chain_groups) != 4:
        raise RuntimeError(
            f"Expected four protein chains, found {len(chain_groups)}"
        )
    ca = np.concatenate(chain_groups)
    global_to_local = {
        int(global_index): local_index
        for local_index, global_index in enumerate(ca)
    }
    local_groups = [
        np.asarray(
            [global_to_local[int(index)] for index in group],
            dtype=int,
        )
        for group in chain_groups
    ]
    xyz = trajectory.xyz[:, ca, :].copy()
    lengths = trajectory.unitcell_lengths
    pair_indices = list(combinations(range(len(chain_groups)), 2))
    pair_distances = np.empty(
        (trajectory.n_frames, len(pair_indices)),
        dtype=float,
    )
    for frame in range(trajectory.n_frames):
        centers = np.asarray(
            [
                np.mean(trajectory.xyz[frame, group, :], axis=0)
                for group in chain_groups
            ]
        )
        anchor = centers[0]
        for group_index, group in enumerate(local_groups[1:], start=1):
            displacement = minimum_image(
                centers[group_index] - anchor,
                lengths[frame],
            )
            target = anchor + displacement
            xyz[frame, group, :] += target - centers[group_index]
        for pair_position, (first, second) in enumerate(pair_indices):
            displacement = minimum_image(
                centers[second] - centers[first],
                lengths[frame],
            )
            pair_distances[frame, pair_position] = np.linalg.norm(
                displacement
            )
    ca_trajectory = trajectory.atom_slice(ca)
    ca_trajectory.xyz = xyz
    ca_trajectory.superpose(ca_trajectory, 0)
    rmsd = md.rmsd(ca_trajectory, ca_trajectory, 0)
    max_distance_change = float(
        np.max(np.abs(pair_distances - pair_distances[0]))
    )
    return rmsd, pair_distances, max_distance_change


def pore_occupancy(
    trajectory: md.Trajectory,
    water_oxygens: np.ndarray,
    source_water_oxygens: np.ndarray,
    chain_groups: list[np.ndarray],
    membrane_centers_z: np.ndarray,
    half_thickness_nm: float,
    pore_radius_nm: float,
) -> dict[str, np.ndarray]:
    lengths = trajectory.unitcell_lengths
    source_set = set(int(index) for index in source_water_oxygens)
    source_positions = np.asarray(
        [
            position
            for position, index in enumerate(water_oxygens)
            if int(index) in source_set
        ],
        dtype=int,
    )
    if len(source_positions) != len(source_water_oxygens):
        raise RuntimeError(
            "Source-water oxygen indices are not a subset of water oxygens"
        )
    all_core = np.zeros(trajectory.n_frames, dtype=int)
    source_core = np.zeros(trajectory.n_frames, dtype=int)
    all_pore = np.zeros(trajectory.n_frames, dtype=int)
    source_pore = np.zeros(trajectory.n_frames, dtype=int)
    for frame in range(trajectory.n_frames):
        box = lengths[frame]
        water_xyz = trajectory.xyz[frame, water_oxygens, :]
        water_z = minimum_image(
            water_xyz[:, 2] - membrane_centers_z[frame],
            box[2],
        )
        core = np.abs(water_z) <= half_thickness_nm
        all_core[frame] = int(np.sum(core))
        source_core[frame] = int(np.sum(core[source_positions]))

        centers_xy = []
        for group in chain_groups:
            group_z = minimum_image(
                trajectory.xyz[frame, group, 2]
                - membrane_centers_z[frame],
                box[2],
            )
            transmembrane = group[np.abs(group_z) <= half_thickness_nm]
            if len(transmembrane) < 5:
                transmembrane = group
            centers_xy.append(
                [
                    periodic_center(
                        trajectory.xyz[frame, transmembrane, 0],
                        box[0],
                    ),
                    periodic_center(
                        trajectory.xyz[frame, transmembrane, 1],
                        box[1],
                    ),
                ]
            )
        in_pore = np.zeros(len(water_oxygens), dtype=bool)
        for center_x, center_y in centers_xy:
            dx = minimum_image(water_xyz[:, 0] - center_x, box[0])
            dy = minimum_image(water_xyz[:, 1] - center_y, box[1])
            in_pore |= (
                core
                & (dx * dx + dy * dy <= pore_radius_nm * pore_radius_nm)
            )
        all_pore[frame] = int(np.sum(in_pore))
        source_pore[frame] = int(np.sum(in_pore[source_positions]))
    return {
        "all_water_core_count": all_core,
        "source_water_core_count": source_core,
        "all_water_operational_pore_count": all_pore,
        "source_water_operational_pore_count": source_pore,
    }


def maximum_covalent_bond_nm(
    trajectory: md.Trajectory,
    bond_pairs: np.ndarray,
    chunk_size: int = 20,
) -> float:
    if len(bond_pairs) == 0:
        raise RuntimeError("Prepared trajectory topology contains no bonds")
    maximum = 0.0
    for start in range(0, trajectory.n_frames, chunk_size):
        distances = md.compute_distances(
            trajectory[start : start + chunk_size],
            bond_pairs,
            periodic=True,
        )
        maximum = max(maximum, float(np.max(distances)))
    return maximum


def cross_section_snapshots(
    trajectory: md.Trajectory,
    times_ps: np.ndarray,
    membrane_centers_z: np.ndarray,
    protein_heavy: np.ndarray,
    protein_ca: np.ndarray,
    lipid_heavy: np.ndarray,
    lipid_phosphorus: np.ndarray,
    water_oxygens: np.ndarray,
    half_width_nm: float,
    path: Path,
) -> dict[str, Any]:
    frames = sorted({0, trajectory.n_frames // 2, trajectory.n_frames - 1})
    figure, axes = plt.subplots(
        1,
        len(frames),
        figsize=(6.4 * len(frames), 6.0),
        sharex=True,
        sharey=True,
    )
    lengths = trajectory.unitcell_lengths
    phosphorus_set = set(int(index) for index in lipid_phosphorus)
    lipid_tail = np.asarray(
        [
            int(index)
            for index in lipid_heavy
            if int(index) not in phosphorus_set
        ],
        dtype=int,
    )
    for axis, frame in zip(np.atleast_1d(axes), frames):
        box = lengths[frame]
        center_x = periodic_center(
            trajectory.xyz[frame, protein_ca, 0],
            box[0],
        )
        center_y = periodic_center(
            trajectory.xyz[frame, protein_ca, 1],
            box[1],
        )

        def relative(indices: np.ndarray) -> tuple[np.ndarray, ...]:
            xyz = trajectory.xyz[frame, indices, :]
            return (
                minimum_image(xyz[:, 0] - center_x, box[0]),
                minimum_image(xyz[:, 1] - center_y, box[1]),
                minimum_image(
                    xyz[:, 2] - membrane_centers_z[frame],
                    box[2],
                ),
            )

        water_x, water_y, water_z = relative(water_oxygens)
        tail_x, tail_y, tail_z = relative(lipid_tail)
        phosphorus_x, phosphorus_y, phosphorus_z = relative(
            lipid_phosphorus
        )
        protein_x, protein_y, protein_z = relative(protein_heavy)
        water_slice = np.abs(water_y) <= half_width_nm
        tail_slice = np.abs(tail_y) <= half_width_nm
        phosphorus_slice = np.abs(phosphorus_y) <= half_width_nm
        protein_slice = np.abs(protein_y) <= half_width_nm
        axis.scatter(
            water_x[water_slice],
            water_z[water_slice],
            s=5,
            color="#2b8cbe",
            alpha=0.35,
            label="water O",
        )
        axis.scatter(
            tail_x[tail_slice],
            tail_z[tail_slice],
            s=4,
            color="#737373",
            alpha=0.28,
            label="lipid heavy",
        )
        axis.scatter(
            phosphorus_x[phosphorus_slice],
            phosphorus_z[phosphorus_slice],
            s=28,
            color="#fdae6b",
            edgecolor="#7f2704",
            linewidth=0.4,
            label="lipid P",
        )
        axis.scatter(
            protein_x[protein_slice],
            protein_z[protein_slice],
            s=7,
            color="#de2d26",
            alpha=0.65,
            label="protein heavy",
        )
        axis.set(
            xlim=(-box[0] / 2.0, box[0] / 2.0),
            ylim=(-box[2] / 2.0, box[2] / 2.0),
            xlabel="x relative to protein center (nm)",
            title=f"{times_ps[frame]:.1f} ps",
        )
        axis.axhline(0.0, color="black", linewidth=0.6, alpha=0.5)
    axes = np.atleast_1d(axes)
    axes[0].set_ylabel("z relative to membrane center (nm)")
    axes[0].legend(loc="upper right", fontsize=7)
    figure.suptitle(
        "AQP1/POPC/water cross-sections "
        f"(|y| ≤ {half_width_nm:.2f} nm)"
    )
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return {
        "frame_indices": frames,
        "times_ps": [float(times_ps[index]) for index in frames],
        "slice_half_width_nm": float(half_width_nm),
    }


def top_view_snapshot(
    trajectory: md.Trajectory,
    frame: int,
    membrane_center_z: float,
    protein_heavy: np.ndarray,
    protein_ca: np.ndarray,
    lipid_phosphorus: np.ndarray,
    source_water_oxygens: np.ndarray,
    half_thickness_nm: float,
    path: Path,
) -> None:
    box = trajectory.unitcell_lengths[frame]
    center_x = periodic_center(
        trajectory.xyz[frame, protein_ca, 0],
        box[0],
    )
    center_y = periodic_center(
        trajectory.xyz[frame, protein_ca, 1],
        box[1],
    )

    def xy(indices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        xyz = trajectory.xyz[frame, indices, :]
        return (
            minimum_image(xyz[:, 0] - center_x, box[0]),
            minimum_image(xyz[:, 1] - center_y, box[1]),
        )

    protein_x, protein_y = xy(protein_heavy)
    phosphorus_x, phosphorus_y = xy(lipid_phosphorus)
    source_x, source_y = xy(source_water_oxygens)
    source_z = minimum_image(
        trajectory.xyz[frame, source_water_oxygens, 2]
        - membrane_center_z,
        box[2],
    )
    source_core = np.abs(source_z) <= half_thickness_nm
    plt.figure(figsize=(7, 7))
    plt.scatter(
        phosphorus_x,
        phosphorus_y,
        s=22,
        color="#fdae6b",
        alpha=0.7,
        label="POPC P",
    )
    plt.scatter(
        protein_x,
        protein_y,
        s=5,
        color="#de2d26",
        alpha=0.45,
        label="protein heavy",
    )
    plt.scatter(
        source_x[source_core],
        source_y[source_core],
        s=28,
        color="#2b8cbe",
        edgecolor="black",
        linewidth=0.4,
        label="retained source water O in core",
    )
    plt.xlim(-box[0] / 2.0, box[0] / 2.0)
    plt.ylim(-box[1] / 2.0, box[1] / 2.0)
    plt.gca().set_aspect("equal", adjustable="box")
    plt.xlabel("x relative to protein center (nm)")
    plt.ylabel("y relative to protein center (nm)")
    plt.title("Final AQP1/POPC top view along Z")
    plt.legend(loc="upper right", fontsize=8)
    save(path)


def validate_checkpoint(
    run: Path,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    pdb = app.PDBFile(str(run / "prepared" / "system.pdb"))
    system = openmm.XmlSerializer.deserialize(
        (run / "prepared" / "system.xml").read_text(encoding="utf-8")
    )
    integrator = openmm.LangevinMiddleIntegrator(
        float(cfg["temperature_kelvin"]) * unit.kelvin,
        float(cfg["friction_per_ps"]) / unit.picosecond,
        float(cfg["timestep_fs"]) * unit.femtosecond,
    )
    platform, properties, _ = openmm_platform(
        cfg["platform"],
        cfg["cuda_precision"],
    )
    simulation = app.Simulation(
        pdb.topology,
        system,
        integrator,
        platform,
        properties,
    )
    simulation.loadCheckpoint(
        str(run / "simulation" / "production.chk")
    )
    state = simulation.context.getState(
        getPositions=True,
        getEnergy=True,
    )
    positions = state.getPositions(asNumpy=True).value_in_unit(
        unit.nanometer
    )
    result = {
        "checkpoint_readable_pass": bool(
            np.isfinite(positions).all()
            and np.isfinite(
                state.getPotentialEnergy().value_in_unit(
                    unit.kilojoule_per_mole
                )
            )
        ),
        "checkpoint_time_ps": float(
            state.getTime().value_in_unit(unit.picosecond)
        ),
    }
    del simulation
    del integrator
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile",
        choices=["quick", "teaching"],
        default="quick",
    )
    parser.add_argument(
        "--figures-only",
        action="store_true",
        help=(
            "Generate metrics and static figures before recording the "
            "mandatory visual inspection; do not finalize the gate."
        ),
    )
    args = parser.parse_args()
    cfg = resolve_config(4, args.profile)
    run = latest_run(4, args.profile)
    figures = run / "figures"
    analysis = run / "analysis"
    figures.mkdir(exist_ok=True)
    analysis.mkdir(exist_ok=True)

    audit = read_json(run / "prepared" / "preparation_audit.json")
    performance = read_json(run / "simulation" / "performance.json")
    log = pd.read_csv(run / "simulation" / "production.csv")
    time_col = col(log, "Time")
    temperature_col = col(log, "Temperature")
    potential_col = col(log, "Potential Energy")
    total_energy_col = col(log, "Total Energy")
    trajectory = md.load(
        str(run / "simulation" / "production.dcd"),
        top=str(run / "prepared" / "system.pdb"),
    )
    openmm_topology = app.PDBFile(
        str(run / "prepared" / "system.pdb")
    ).topology
    bond_pairs = np.asarray(
        [
            [first.index, second.index]
            for first, second in openmm_topology.bonds()
        ],
        dtype=int,
    )
    if (
        trajectory.unitcell_lengths is None
        or trajectory.unitcell_angles is None
    ):
        raise RuntimeError("Phase 4 trajectory lacks periodic unit-cell data")
    if not np.allclose(
        trajectory.unitcell_angles,
        90.0,
        atol=1e-3,
    ):
        raise RuntimeError("Phase 4 analysis requires an orthorhombic box")
    times = trajectory_times_from_log(
        log,
        time_col,
        trajectory.n_frames,
    )

    lipid_resname = str(audit["lipid_resname"])
    protein_ca = trajectory.topology.select("protein and name CA")
    protein_heavy = trajectory.topology.select(
        "protein and not element H"
    )
    lipid_phosphorus = trajectory.topology.select(
        f"resname {lipid_resname} and name P"
    )
    lipid_heavy = trajectory.topology.select(
        f"resname {lipid_resname} and not element H"
    )
    water_oxygens = trajectory.topology.select("water and name O")
    source_water_oxygens = np.asarray(
        audit["retained_source_water_oxygen_indices"],
        dtype=int,
    )
    if (
        len(protein_ca) == 0
        or len(lipid_phosphorus) < 20
        or len(water_oxygens) == 0
    ):
        raise RuntimeError(
            "Missing protein C-alpha, lipid phosphorus, or water oxygen atoms"
        )
    if np.max(source_water_oxygens) >= trajectory.n_atoms:
        raise RuntimeError("Source-water indices exceed trajectory topology")
    for index in source_water_oxygens:
        atom = trajectory.topology.atom(int(index))
        if not atom.residue.is_water or atom.name != "O":
            raise RuntimeError(
                f"Source-water index {index} is not a water oxygen"
            )

    lengths = trajectory.unitcell_lengths
    membrane_centers_z = np.asarray(
        [
            periodic_center(
                trajectory.xyz[frame, lipid_phosphorus, 2],
                lengths[frame, 2],
            )
            for frame in range(trajectory.n_frames)
        ]
    )
    phosphorus_relative_z = np.asarray(
        [
            minimum_image(
                trajectory.xyz[frame, lipid_phosphorus, 2]
                - membrane_centers_z[frame],
                lengths[frame, 2],
            )
            for frame in range(trajectory.n_frames)
        ]
    )
    upper_mask = phosphorus_relative_z[0] >= 0.0
    lower_mask = ~upper_mask
    upper_count = int(np.sum(upper_mask))
    lower_count = int(np.sum(lower_mask))
    if upper_count == 0 or lower_count == 0:
        raise RuntimeError("Could not identify both POPC leaflets")
    upper_phosphorus_z = np.mean(
        phosphorus_relative_z[:, upper_mask],
        axis=1,
    )
    lower_phosphorus_z = np.mean(
        phosphorus_relative_z[:, lower_mask],
        axis=1,
    )
    thickness = upper_phosphorus_z - lower_phosphorus_z
    area = lengths[:, 0] * lengths[:, 1]
    mean_lipids_per_leaflet = (upper_count + lower_count) / 2.0
    area_per_lipid = area / mean_lipids_per_leaflet
    water_relative_z = np.asarray(
        [
            minimum_image(
                trajectory.xyz[frame, water_oxygens, 2]
                - membrane_centers_z[frame],
                lengths[frame, 2],
            )
            for frame in range(trajectory.n_frames)
        ]
    )

    chain_groups = chain_ca_groups(trajectory.topology)
    protein_rmsd, oligomer_distances, max_oligomer_change = (
        protein_rmsd_and_oligomer_distances(
            trajectory,
            chain_groups,
        )
    )
    occupancy = pore_occupancy(
        trajectory,
        water_oxygens,
        source_water_oxygens,
        chain_groups,
        membrane_centers_z,
        float(cfg["opm_hydrophobic_thickness_nm"]) / 2.0,
        float(cfg["pore_radius_nm"]),
    )

    solvent_margin_nm = 0.35
    upper_outer_counts = np.sum(
        water_relative_z
        > (upper_phosphorus_z + solvent_margin_nm)[:, None],
        axis=1,
    )
    lower_outer_counts = np.sum(
        water_relative_z
        < (lower_phosphorus_z - solvent_margin_nm)[:, None],
        axis=1,
    )

    timeseries = pd.DataFrame(
        {
            "time_ps": times,
            "box_x_nm": lengths[:, 0],
            "box_y_nm": lengths[:, 1],
            "box_z_nm": lengths[:, 2],
            "xy_area_nm2": area,
            "area_per_lipid_nm2": area_per_lipid,
            "phosphate_thickness_nm": thickness,
            "protein_ca_rmsd_nm": protein_rmsd,
            "upper_outer_water_oxygen_count": upper_outer_counts,
            "lower_outer_water_oxygen_count": lower_outer_counts,
            **occupancy,
        }
    )
    timeseries.to_csv(
        analysis / "membrane_timeseries.csv",
        index=False,
    )
    pd.DataFrame(
        oligomer_distances,
        columns=[
            f"chain_pair_{first + 1}_{second + 1}_ca_centroid_nm"
            for first, second in combinations(range(4), 2)
        ],
    ).assign(time_ps=times).to_csv(
        analysis / "oligomer_distances.csv",
        index=False,
    )

    figure, axes = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    axes[0].plot(log[time_col], log[temperature_col])
    axes[0].axhline(
        cfg["temperature_kelvin"],
        linestyle="--",
        color="black",
    )
    axes[0].set_ylabel("Temperature (K)")
    axes[0].set_title("Phase 4 production thermodynamics")
    axes[1].plot(
        log[time_col],
        log[potential_col],
        label="potential",
    )
    axes[1].plot(
        log[time_col],
        log[total_energy_col],
        label="total",
        alpha=0.8,
    )
    axes[1].set(
        xlabel="Time (ps)",
        ylabel="Energy (kJ/mol)",
    )
    axes[1].legend()
    figure.tight_layout()
    figure.savefig(figures / "thermodynamics.png", dpi=180)
    plt.close(figure)

    plt.figure(figsize=(8, 4.5))
    plt.plot(times, lengths[:, 0], label="X")
    plt.plot(times, lengths[:, 1], label="Y")
    plt.plot(times, lengths[:, 2], label="Z")
    plt.xlabel("Time (ps)")
    plt.ylabel("Box length (nm)")
    plt.title("Membrane box dimensions")
    plt.legend()
    save(figures / "box_lengths.png")

    plt.figure(figsize=(8, 4.5))
    plt.plot(times, area)
    plt.xlabel("Time (ps)")
    plt.ylabel("XY area (nm²)")
    plt.title("Membrane XY area")
    save(figures / "xy_area.png")

    plt.figure(figsize=(8, 4.5))
    plt.plot(times, area_per_lipid)
    plt.axhspan(
        cfg["gates"]["area_per_lipid_nm2_min"],
        cfg["gates"]["area_per_lipid_nm2_max"],
        alpha=0.15,
    )
    plt.xlabel("Time (ps)")
    plt.ylabel("Area per lipid (nm²)")
    plt.title(
        "Approximate POPC area per lipid "
        f"({upper_count}/{lower_count} per leaflet)"
    )
    save(figures / "area_per_lipid.png")

    plt.figure(figsize=(8, 4.5))
    plt.plot(times, thickness)
    plt.axhspan(
        cfg["gates"]["membrane_thickness_nm_min"],
        cfg["gates"]["membrane_thickness_nm_max"],
        alpha=0.15,
    )
    plt.xlabel("Time (ps)")
    plt.ylabel("P–P thickness (nm)")
    plt.title("Approximate membrane thickness")
    save(figures / "membrane_thickness.png")

    plt.figure(figsize=(8, 4.5))
    plt.plot(times, protein_rmsd)
    plt.xlabel("Time (ps)")
    plt.ylabel("Cα RMSD (nm)")
    plt.title("AQP1 tetramer Cα RMSD after periodic reassembly/alignment")
    save(figures / "protein_rmsd.png")

    half_box = float(np.min(lengths[:, 2]) / 2.0)
    bins = np.linspace(-half_box, half_box, 151)
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    bin_width = float(bins[1] - bins[0])
    phosphorus_histogram, _ = np.histogram(
        phosphorus_relative_z.ravel(),
        bins=bins,
    )
    water_histogram, _ = np.histogram(
        water_relative_z.ravel(),
        bins=bins,
    )
    normalization = (
        trajectory.n_frames * float(np.mean(area)) * bin_width
    )
    phosphorus_density = phosphorus_histogram / normalization
    water_density = water_histogram / normalization
    pd.DataFrame(
        {
            "z_relative_nm": bin_centers,
            "lipid_phosphorus_number_density_nm-3": phosphorus_density,
            "water_oxygen_number_density_nm-3": water_density,
        }
    ).to_csv(analysis / "z_density.csv", index=False)
    plt.figure(figsize=(8, 4.5))
    plt.plot(
        bin_centers,
        phosphorus_density,
        label="lipid P",
    )
    plt.plot(
        bin_centers,
        water_density,
        label="water O",
    )
    plt.xlabel("z relative to membrane center (nm)")
    plt.ylabel("Number density (nm⁻³)")
    plt.title("Membrane component Z profiles")
    plt.legend()
    save(figures / "z_density.png")

    plt.figure(figsize=(8, 4.8))
    plt.plot(
        times,
        occupancy["source_water_core_count"],
        label="source water in core",
    )
    plt.plot(
        times,
        occupancy["source_water_operational_pore_count"],
        label="source water in pore cylinders",
    )
    plt.plot(
        times,
        occupancy["all_water_operational_pore_count"],
        label="all water in pore cylinders",
        alpha=0.75,
    )
    plt.xlabel("Time (ps)")
    plt.ylabel("Water oxygen count")
    plt.title(
        "Retained-water occupancy "
        f"(operational pore radius {cfg['pore_radius_nm']:.2f} nm)"
    )
    plt.legend()
    save(figures / "source_water_occupancy.png")

    cross_section_metadata = cross_section_snapshots(
        trajectory,
        times,
        membrane_centers_z,
        protein_heavy,
        protein_ca,
        lipid_heavy,
        lipid_phosphorus,
        water_oxygens,
        float(cfg["cross_section_half_width_nm"]),
        figures / "cross_section_snapshots.png",
    )
    write_json(
        analysis / "cross_section_snapshots.json",
        cross_section_metadata,
    )
    top_view_snapshot(
        trajectory,
        trajectory.n_frames - 1,
        membrane_centers_z[-1],
        protein_heavy,
        protein_ca,
        lipid_phosphorus,
        source_water_oxygens,
        float(cfg["opm_hydrophobic_thickness_nm"]) / 2.0,
        figures / "top_view_snapshot.png",
    )

    solvent_density_mask = (
        (
            bin_centers
            > float(np.mean(upper_phosphorus_z)) + solvent_margin_nm
        )
        | (
            bin_centers
            < float(np.mean(lower_phosphorus_z)) - solvent_margin_nm
        )
    )
    if not np.any(solvent_density_mask):
        raise RuntimeError("No outer solvent bins available for vacuum check")
    minimum_outer_water_density = float(
        np.min(water_density[solvent_density_mask])
    )
    max_bond_nm = maximum_covalent_bond_nm(
        trajectory,
        bond_pairs,
    )
    mean_temperature = float(log[temperature_col].mean())
    mean_area_per_lipid = float(np.mean(area_per_lipid))
    mean_thickness = float(np.mean(thickness))
    max_protein_rmsd = float(np.max(protein_rmsd))
    expected_rows = int(
        round(
            float(cfg["production_ps"])
            / float(cfg["output_stride_ps"])
        )
    )

    preliminary = {
        "mean_temperature_K": mean_temperature,
        "mean_area_per_lipid_nm2": mean_area_per_lipid,
        "mean_membrane_thickness_nm": mean_thickness,
        "max_protein_ca_rmsd_nm": max_protein_rmsd,
        "max_oligomer_ca_centroid_distance_change_nm": (
            max_oligomer_change
        ),
        "max_covalent_bond_nm": max_bond_nm,
        "lipid_count_upper_leaflet": upper_count,
        "lipid_count_lower_leaflet": lower_count,
        "minimum_upper_outer_water_oxygen_count": int(
            np.min(upper_outer_counts)
        ),
        "minimum_lower_outer_water_oxygen_count": int(
            np.min(lower_outer_counts)
        ),
        "minimum_outer_water_number_density_nm-3": (
            minimum_outer_water_density
        ),
        "mean_source_water_core_count": float(
            np.mean(occupancy["source_water_core_count"])
        ),
        "mean_source_water_operational_pore_count": float(
            np.mean(occupancy["source_water_operational_pore_count"])
        ),
        "mean_all_water_operational_pore_count": float(
            np.mean(occupancy["all_water_operational_pore_count"])
        ),
        "trajectory_frames": trajectory.n_frames,
        "thermodynamic_rows": len(log),
    }
    write_json(analysis / "preliminary_metrics.json", preliminary)
    if args.figures_only:
        print(
            json.dumps(
                {
                    "status": "FIGURES_READY_FOR_VISUAL_INSPECTION",
                    **preliminary,
                },
                indent=2,
            )
        )
        return

    visual_path = analysis / "visual_inspection.json"
    if not visual_path.exists():
        raise RuntimeError(
            "Mandatory Phase 4 visual inspection is missing. Run with "
            "--figures-only, inspect the static figures/VMD view, and "
            "create analysis/visual_inspection.json before finalizing."
        )
    visual = read_json(visual_path)
    missing_visual = [
        key for key in VISUAL_CHECKS if key not in visual
    ]
    if missing_visual:
        raise RuntimeError(
            f"Visual inspection record lacks checks: {missing_visual}"
        )
    checkpoint = validate_checkpoint(run, cfg)
    required_figures = [
        "thermodynamics.png",
        "box_lengths.png",
        "xy_area.png",
        "area_per_lipid.png",
        "membrane_thickness.png",
        "protein_rmsd.png",
        "z_density.png",
        "source_water_occupancy.png",
        "cross_section_snapshots.png",
        "top_view_snapshot.png",
    ]
    figures_pass = all(
        (figures / filename).exists()
        and (figures / filename).stat().st_size > 0
        for filename in required_figures
    )
    finite_values = bool(
        np.isfinite(trajectory.xyz).all()
        and np.isfinite(
            log.select_dtypes(include=[np.number]).to_numpy()
        ).all()
        and np.isfinite(timeseries.to_numpy()).all()
    )
    prepared_chains = audit["prepared_protein_chains"]
    expected_tetramer = bool(
        len(prepared_chains) == int(cfg["expected_protein_chains"])
        and all(
            chain["residue_count"]
            == int(cfg["expected_residues_per_chain"])
            for chain in prepared_chains
        )
    )
    source_waters_retained = bool(
        audit["water_molecules_source"]
        == int(cfg["expected_source_waters"])
        and len(source_water_oxygens)
        == int(cfg["expected_source_waters"])
        and len(set(int(index) for index in source_water_oxygens))
        == int(cfg["expected_source_waters"])
    )
    parameterization_pass = bool(
        audit["parameterization"]["status"] == "PASS"
        and audit["parameterization"]["unassigned_parameter_exception"]
        is None
        and audit["parameterization"]["parameterized_particles"]
        == trajectory.n_atoms
    )
    threshold_outer_water = int(
        cfg["gates"]["minimum_outer_slab_water_oxygens"]
    )
    checks = {
        "finite_values_pass": finite_values,
        "expected_tetramer_pass": expected_tetramer,
        "source_waters_retained_pass": source_waters_retained,
        "all_atoms_parameterized_pass": parameterization_pass,
        "prepared_minimum_intercomponent_heavy_atom_distance_nm": (
            audit["minimum_intercomponent_heavy_atom_distance_nm"]
        ),
        "prepared_intercomponent_geometry_pass": bool(
            audit["minimum_intercomponent_heavy_atom_distance_nm"]
            >= cfg["gates"][
                "minimum_intercomponent_heavy_atom_distance_nm"
            ]
        ),
        "mean_temperature_K": mean_temperature,
        "temperature_pass": bool(
            abs(mean_temperature - cfg["temperature_kelvin"])
            / cfg["temperature_kelvin"]
            <= cfg["gates"]["max_temperature_relative_error"]
        ),
        "mean_area_per_lipid_nm2": mean_area_per_lipid,
        "area_per_lipid_pass": bool(
            cfg["gates"]["area_per_lipid_nm2_min"]
            <= mean_area_per_lipid
            <= cfg["gates"]["area_per_lipid_nm2_max"]
        ),
        "mean_membrane_thickness_nm": mean_thickness,
        "thickness_pass": bool(
            cfg["gates"]["membrane_thickness_nm_min"]
            <= mean_thickness
            <= cfg["gates"]["membrane_thickness_nm_max"]
        ),
        "max_protein_ca_rmsd_nm": max_protein_rmsd,
        "protein_rmsd_pass": bool(
            max_protein_rmsd
            <= cfg["gates"]["max_protein_ca_rmsd_nm"]
        ),
        "max_oligomer_ca_centroid_distance_change_nm": (
            max_oligomer_change
        ),
        "oligomer_integrity_pass": bool(
            max_oligomer_change
            <= cfg["gates"][
                "max_oligomer_ca_centroid_distance_change_nm"
            ]
        ),
        "lipid_count_upper_leaflet": upper_count,
        "lipid_count_lower_leaflet": lower_count,
        "leaflet_balance_pass": bool(
            abs(upper_count - lower_count)
            <= cfg["gates"]["max_leaflet_count_difference"]
        ),
        "minimum_upper_outer_water_oxygen_count": int(
            np.min(upper_outer_counts)
        ),
        "minimum_lower_outer_water_oxygen_count": int(
            np.min(lower_outer_counts)
        ),
        "outer_solvent_coverage_pass": bool(
            np.min(upper_outer_counts) >= threshold_outer_water
            and np.min(lower_outer_counts) >= threshold_outer_water
        ),
        "minimum_outer_water_number_density_nm-3": (
            minimum_outer_water_density
        ),
        "no_persistent_vacuum_density_pass": bool(
            minimum_outer_water_density > 0.0
        ),
        "max_covalent_bond_nm": max_bond_nm,
        "bond_geometry_pass": bool(
            max_bond_nm <= cfg["gates"]["max_unphysical_bond_nm"]
        ),
        "thermodynamic_rows": len(log),
        "expected_thermodynamic_rows": expected_rows,
        "thermodynamic_rows_pass": bool(len(log) == expected_rows),
        "trajectory_frames": trajectory.n_frames,
        "trajectory_readable_pass": bool(
            trajectory.n_frames == expected_rows
            and trajectory.n_atoms > 0
        ),
        **checkpoint,
        "required_figures_generated_pass": figures_pass,
        "visual_inspection_pass": bool(
            all(bool(visual[key]) for key in VISUAL_CHECKS)
        ),
    }
    status = (
        "PASS"
        if all(
            bool(value)
            for key, value in checks.items()
            if key.endswith("_pass")
        )
        else "FAIL"
    )
    write_json(
        run / "gate.json",
        {
            "phase": 4,
            "profile": args.profile,
            "status": status,
            "checks": checks,
        },
    )
    report = f"""# Phase 4 report — {args.profile}

## Objective

Build and simulate the official OPM-oriented AQP1 tetramer in a homogeneous
POPC bilayer while retaining all 371 source waters approved in `DR-002`.

## Preparation observations

- Protein assembly: {len(prepared_chains)} chains, {prepared_chains[0]["residue_count"]} residues per chain.
- POPC topology residue name: `{lipid_resname}`; leaflets: {upper_count} upper and {lower_count} lower.
- Waters: {audit["water_molecules_source"]} retained source and {audit["water_molecules_added"]} added.
- Ions: {audit["ion_residue_counts"]}.
- Prepared atoms: {trajectory.n_atoms}; all were assigned force-field parameters.
- Minimum audited inter-component heavy-atom distance: {audit["minimum_intercomponent_heavy_atom_distance_nm"]:.4f} nm.

## Production observations

- Mean temperature: {mean_temperature:.2f} K.
- Mean approximate area per lipid: {mean_area_per_lipid:.4f} nm².
- Mean phosphorus-to-phosphorus thickness: {mean_thickness:.4f} nm.
- Maximum protein Cα RMSD after periodic tetramer reassembly/alignment: {max_protein_rmsd:.4f} nm.
- Maximum change in an inter-subunit Cα-centroid distance: {max_oligomer_change:.4f} nm.
- Maximum covalent-bond length: {max_bond_nm:.4f} nm.
- Mean retained-source waters in the OPM hydrophobic core: {np.mean(occupancy["source_water_core_count"]):.2f}.
- Mean retained-source waters in the four operational pore cylinders: {np.mean(occupancy["source_water_operational_pore_count"]):.2f}.
- Mean all-water occupancy in those cylinders: {np.mean(occupancy["all_water_operational_pore_count"]):.2f}.
- CUDA production performance: {performance["production_ns_per_day"]:.1f} ns/day.

## Visual inspection

Reviewer: {visual.get("reviewer", "not recorded")}. The signed record is
`analysis/visual_inspection.json`. Cross-sections and the top view were used to
check bilayer continuity, hydration, lipid placement, tetramer integrity,
vacuum gaps, and the Z membrane normal.

## Interpretation limits

Area per lipid, phosphorus-peak thickness, and pore-cylinder occupancy are
operational definitions with broad construction-sanity ranges. The
{args.profile} trajectory validates the prepared tutorial system; it does not
demonstrate membrane equilibration, water permeability, or a biological
transport mechanism.

## Gate

**{status}**
"""
    (run / "REPORT.md").write_text(report, encoding="utf-8")
    finish_manifest(
        run,
        "ANALYSIS_COMPLETE" if status == "PASS" else "GATE_FAILED",
        {"gate": status},
    )
    print(json.dumps({"status": status, "checks": checks}, indent=2))
    if status != "PASS":
        raise SystemExit("Phase 4 gate failed")


if __name__ == "__main__":
    main()
