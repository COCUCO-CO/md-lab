#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import mdtraj as md
import numpy as np
import pandas as pd
from rdkit import Chem
from rdkit.Chem import Draw

from mdlab.analysis_utils import trajectory_times_from_log
from mdlab.core import finish_manifest, latest_run, read_json, resolve_config, write_json


def col(df: pd.DataFrame, token: str) -> str:
    for c in df.columns:
        if token.lower() in c.lower():
            return c
    raise KeyError(token)


def save(path: Path) -> None:
    plt.tight_layout(); plt.savefig(path, dpi=180); plt.close()


def binding_site_snapshots(
    traj: md.Trajectory,
    ligand_heavy: np.ndarray,
    protein_heavy: np.ndarray,
    times_ps: np.ndarray,
    path: Path,
    cutoff_nm: float = 0.6,
) -> dict:
    pairs = np.array(
        [(int(ligand), int(protein)) for ligand in ligand_heavy for protein in protein_heavy],
        dtype=int,
    )
    initial_distances = md.compute_distances(
        traj[0],
        pairs,
        periodic=False,
    ).reshape(len(ligand_heavy), len(protein_heavy))
    contacting_protein = protein_heavy[np.any(initial_distances < cutoff_nm, axis=0)]
    residue_indices = {
        traj.topology.atom(int(atom_index)).residue.index
        for atom_index in contacting_protein
    }
    if not residue_indices:
        raise RuntimeError(f"No binding-site residues found within {cutoff_nm} nm of the ligand")

    site_atoms = np.array(
        [
            atom.index
            for residue in traj.topology.residues
            if residue.index in residue_indices
            for atom in residue.atoms
            if atom.element is not None and atom.element.symbol != "H"
        ],
        dtype=int,
    )
    site_atom_set = set(site_atoms)
    ligand_atom_set = set(ligand_heavy)
    site_bonds = [
        (first.index, second.index)
        for first, second in traj.topology.bonds
        if first.index in site_atom_set and second.index in site_atom_set
    ]
    ligand_bonds = [
        (first.index, second.index)
        for first, second in traj.topology.bonds
        if first.index in ligand_atom_set and second.index in ligand_atom_set
    ]
    selected_frames = sorted({0, traj.n_frames // 2, traj.n_frames - 1})
    shown_atoms = np.concatenate((site_atoms, ligand_heavy))
    shown_coordinates = traj.xyz[selected_frames][:, shown_atoms, :].reshape(-1, 3)
    lower = shown_coordinates.min(axis=0)
    upper = shown_coordinates.max(axis=0)
    center = (lower + upper) / 2.0
    half_width = max(float(np.max(upper - lower)) / 2.0 + 0.1, 0.5)

    figure = plt.figure(figsize=(6.5 * len(selected_frames), 6))
    for panel, frame_index in enumerate(selected_frames, start=1):
        axis = figure.add_subplot(1, len(selected_frames), panel, projection="3d")
        xyz = traj.xyz[frame_index]
        axis.scatter(
            xyz[site_atoms, 0],
            xyz[site_atoms, 1],
            xyz[site_atoms, 2],
            s=18,
            color="#7f7f7f",
            alpha=0.75,
            label="site heavy atoms",
        )
        axis.scatter(
            xyz[ligand_heavy, 0],
            xyz[ligand_heavy, 1],
            xyz[ligand_heavy, 2],
            s=70,
            color="#ff7f0e",
            edgecolor="black",
            label="BNZ carbon",
        )
        for first, second in site_bonds:
            axis.plot(
                xyz[[first, second], 0],
                xyz[[first, second], 1],
                xyz[[first, second], 2],
                color="#8c8c8c",
                linewidth=1.2,
                alpha=0.65,
            )
        for first, second in ligand_bonds:
            axis.plot(
                xyz[[first, second], 0],
                xyz[[first, second], 1],
                xyz[[first, second], 2],
                color="#d95f02",
                linewidth=3.0,
            )
        for residue in traj.topology.residues:
            if residue.index not in residue_indices:
                continue
            ca_atoms = [atom.index for atom in residue.atoms if atom.name == "CA"]
            if ca_atoms:
                position = xyz[ca_atoms[0]]
                axis.text(*position, str(residue), fontsize=7)
        axis.set(
            xlim=(center[0] - half_width, center[0] + half_width),
            ylim=(center[1] - half_width, center[1] + half_width),
            zlim=(center[2] - half_width, center[2] + half_width),
            xlabel="x (nm)",
            ylabel="y (nm)",
            zlabel="z (nm)",
            title=f"Frame {frame_index} — {times_ps[frame_index]:.1f} ps",
        )
        axis.set_box_aspect((1, 1, 1))
        if panel == 1:
            axis.legend(loc="upper left", fontsize=7)
    figure.suptitle(f"BNZ binding-site snapshots (<{cutoff_nm:.2f} nm in first frame)")
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
    return {
        "binding_site_residue_count": len(residue_indices),
        "binding_site_residues": [
            str(residue)
            for residue in traj.topology.residues
            if residue.index in residue_indices
        ],
        "snapshot_frame_indices": selected_frames,
        "snapshot_times_ps": [float(times_ps[index]) for index in selected_frames],
        "site_cutoff_nm": cutoff_nm,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["quick", "teaching"], default="quick")
    args = parser.parse_args()
    cfg = resolve_config(3, args.profile)
    run = latest_run(3, args.profile)
    fig, ana = run / "figures", run / "analysis"
    fig.mkdir(exist_ok=True); ana.mkdir(exist_ok=True)

    audit = read_json(run / "prepared" / "preparation_audit.json")
    performance = read_json(run / "simulation" / "performance.json")
    log = pd.read_csv(run / "simulation" / "production.csv")
    time_col = col(log, "Time")
    temp_col = col(log, "Temperature")
    den_col = col(log, "Density")
    traj = md.load(
        str(run / "simulation" / "production.dcd"),
        top=str(run / "prepared" / "system.pdb"),
    )
    times = trajectory_times_from_log(log, time_col, traj.n_frames)
    traj.image_molecules(inplace=True)
    ca = traj.topology.select("protein and name CA")
    lig_all = traj.topology.select(f"resname {cfg['ligand_resname']}")
    lig_heavy = traj.topology.select(
        f"resname {cfg['ligand_resname']} and not element H"
    )
    protein_heavy = traj.topology.select("protein and not element H")
    if not len(ca) or not len(lig_all) or not len(lig_heavy):
        raise RuntimeError("Missing protein C-alpha or ligand atoms")
    traj.superpose(traj, 0, atom_indices=ca)

    protein_rmsd = md.rmsd(traj, traj, 0, atom_indices=ca)
    ligand_delta = (
        traj.xyz[:, lig_heavy, :]
        - traj.xyz[0, lig_heavy, :][None, :, :]
    )
    ligand_rmsd = np.sqrt(
        np.mean(np.sum(ligand_delta**2, axis=2), axis=1)
    )
    ligand_masses = np.array(
        [traj.topology.atom(int(index)).element.mass for index in lig_all],
        dtype=float,
    )
    ligand_com = np.average(
        traj.xyz[:, lig_all, :],
        axis=1,
        weights=ligand_masses,
    )
    ligand_com_displacement = np.linalg.norm(
        ligand_com - ligand_com[0],
        axis=1,
    )

    pairs = np.array(
        [
            (int(ligand), int(protein))
            for ligand in lig_heavy
            for protein in protein_heavy
        ],
        dtype=int,
    )
    distances = md.compute_distances(
        traj,
        pairs,
        periodic=False,
    ).reshape(traj.n_frames, len(lig_heavy), len(protein_heavy))
    min_distance = distances.min(axis=(1, 2))

    contact_cutoff_nm = 0.45
    residue_contacts = []
    for residue in traj.topology.residues:
        if not residue.is_protein:
            continue
        atoms = [
            atom.index
            for atom in residue.atoms
            if atom.element is not None and atom.element.symbol != "H"
        ]
        if not atoms:
            continue
        residue_pairs = np.array(
            [
                (int(ligand), int(protein))
                for ligand in lig_heavy
                for protein in atoms
            ],
            dtype=int,
        )
        residue_distances = md.compute_distances(
            traj,
            residue_pairs,
            periodic=False,
        )
        occupancy = float(
            (residue_distances.min(axis=1) < contact_cutoff_nm).mean()
        )
        residue_contacts.append(
            {
                "residue": str(residue),
                "residue_index": residue.index,
                "contact_occupancy_lt_0.45nm": occupancy,
            }
        )
    contacts = pd.DataFrame(residue_contacts).sort_values(
        "contact_occupancy_lt_0.45nm",
        ascending=False,
    )
    contacts_path = ana / "contact_occupancy.csv"
    contacts.to_csv(contacts_path, index=False)
    pd.DataFrame(
        {
            "time_ps": times,
            "protein_ca_rmsd_nm": protein_rmsd,
            "ligand_aligned_rmsd_nm": ligand_rmsd,
            "ligand_com_displacement_nm": ligand_com_displacement,
            "min_ligand_protein_distance_nm": min_distance,
        }
    ).to_csv(ana / "timeseries.csv", index=False)

    plt.figure(figsize=(8, 4.5))
    plt.plot(log[time_col], log[temp_col])
    plt.axhline(cfg["temperature_kelvin"], linestyle="--")
    plt.xlabel("Time (ps)")
    plt.ylabel("Temperature (K)")
    plt.title("Phase 3 production temperature")
    save(fig / "temperature.png")
    plt.figure(figsize=(8, 4.5))
    plt.plot(log[time_col], log[den_col])
    plt.xlabel("Time (ps)")
    plt.ylabel("Density (g/mL)")
    plt.title("Phase 3 production density")
    save(fig / "density.png")

    for values, ylabel, title, filename in [
        (
            protein_rmsd,
            "Cα RMSD (nm)",
            "Protein RMSD after alignment",
            "protein_rmsd.png",
        ),
        (
            ligand_rmsd,
            "Ligand RMSD (nm)",
            "Ligand heavy-atom RMSD after protein alignment",
            "ligand_rmsd.png",
        ),
        (
            ligand_com_displacement,
            "COM displacement (nm)",
            "Ligand center-of-mass displacement",
            "ligand_com.png",
        ),
        (
            min_distance,
            "Minimum distance (nm)",
            "Ligand–protein minimum heavy-atom distance",
            "minimum_distance.png",
        ),
    ]:
        plt.figure(figsize=(8, 4.5))
        plt.plot(times, values)
        plt.xlabel("Time (ps)")
        plt.ylabel(ylabel)
        plt.title(title)
        save(fig / filename)
    top_contacts = contacts.head(15).sort_values(
        "contact_occupancy_lt_0.45nm"
    )
    plt.figure(figsize=(8, 5))
    plt.barh(
        top_contacts["residue"],
        top_contacts["contact_occupancy_lt_0.45nm"],
    )
    plt.xlabel(f"Contact occupancy (<{contact_cutoff_nm:.2f} nm)")
    plt.title("Top ligand contact residues")
    save(fig / "contact_occupancy.png")

    snapshot_path = fig / "binding_site_snapshots.png"
    snapshot_metadata = binding_site_snapshots(
        traj,
        lig_heavy,
        protein_heavy,
        times,
        snapshot_path,
    )
    write_json(ana / "binding_site_snapshots.json", snapshot_metadata)

    ligand_sdf = ROOT / "inputs" / "phase03" / f"{cfg['ligand_resname']}_ideal.sdf"
    rd_mol = Chem.SDMolSupplier(str(ligand_sdf), removeHs=False)[0]
    if rd_mol is None:
        raise RuntimeError("RDKit could not parse ligand SDF for the identity figure")
    identity_path = fig / "ligand_identity_2d.png"
    identity_image = Draw.MolToImage(
        Chem.RemoveHs(rd_mol),
        size=(700, 500),
        legend=(
            f"{audit['ligand']['name']} — {audit['ligand']['formula']} — "
            f"charge {audit['ligand']['formal_charge']}"
        ),
    )
    identity_image.save(identity_path)

    bond_pairs = np.array(
        [
            [first.index, second.index]
            for first, second in traj.topology.bonds
        ],
        dtype=int,
    )
    bond_lengths = md.compute_distances(
        traj,
        bond_pairs,
        periodic=False,
    )
    max_bond_nm = float(np.max(bond_lengths))
    mean_temp = float(log[temp_col].mean())
    mean_density = float(log[den_col].mean())
    max_protein_rmsd = float(np.max(protein_rmsd))
    max_ligand_rmsd = float(np.max(ligand_rmsd))
    max_ligand_com = float(np.max(ligand_com_displacement))
    expected_rows = int(
        round(float(cfg["production_ps"]) / float(cfg["output_stride_ps"]))
    )
    ligand_audit = audit["ligand"]
    chemical_identity_pass = bool(
        ligand_audit["name"] == cfg["ligand_resname"]
        and ligand_audit["formula"] == "C6H6"
        and ligand_audit["formal_charge"] == int(cfg["ligand_formal_charge"])
        and ligand_audit["sdf_atoms_including_hydrogen"] == 12
        and ligand_audit["sdf_atoms_excluding_hydrogen"] == 6
        and ligand_audit["aromatic_bonds"] == 6
        and ligand_audit["stereocenters"] == []
        and ligand_audit["mapping_one_to_one"]
        and not ligand_audit["mapping_ambiguous"]
        and ligand_audit["assigned_forcefield_version"]
        == cfg["small_molecule_forcefield"]
    )
    parameterization_pass = bool(
        audit["parameterization"]["status"] == "PASS"
        and audit["parameterization"]["unassigned_parameter_exception"] is None
        and audit["parameterization"]["parameterized_particles"] == traj.n_atoms
    )
    checks = {
        "finite_values_pass": bool(
            np.isfinite(traj.xyz).all()
            and np.isfinite(
                log.select_dtypes(include=[np.number]).to_numpy()
            ).all()
            and np.isfinite(protein_rmsd).all()
            and np.isfinite(ligand_rmsd).all()
            and np.isfinite(ligand_com_displacement).all()
        ),
        "chemical_identity_audit_pass": chemical_identity_pass,
        "all_atoms_parameterized_pass": parameterization_pass,
        "mean_temperature_K": mean_temp,
        "temperature_pass": bool(
            abs(mean_temp - cfg["temperature_kelvin"])
            / cfg["temperature_kelvin"]
            <= cfg["gates"]["max_temperature_relative_error"]
        ),
        "mean_density_g_ml": mean_density,
        "density_pass": bool(
            cfg["gates"]["density_g_ml_min"]
            <= mean_density
            <= cfg["gates"]["density_g_ml_max"]
        ),
        "max_protein_ca_rmsd_nm": max_protein_rmsd,
        "protein_rmsd_pass": bool(
            max_protein_rmsd
            <= cfg["gates"]["max_protein_ca_rmsd_nm"]
        ),
        "max_ligand_aligned_rmsd_nm": max_ligand_rmsd,
        "ligand_rmsd_pass": bool(
            max_ligand_rmsd
            <= cfg["gates"]["max_ligand_aligned_rmsd_nm_quick"]
        ),
        "max_ligand_com_displacement_nm": max_ligand_com,
        "ligand_com_pass": bool(
            max_ligand_com
            <= cfg["gates"]["max_ligand_com_distance_from_initial_nm"]
        ),
        "minimum_ligand_protein_distance_nm": float(np.min(min_distance)),
        "max_covalent_bond_nm": max_bond_nm,
        "bond_geometry_pass": bool(
            max_bond_nm <= cfg["gates"]["max_unphysical_bond_nm"]
        ),
        "thermodynamic_rows": len(log),
        "expected_thermodynamic_rows": expected_rows,
        "thermodynamic_rows_pass": bool(len(log) == expected_rows),
        "trajectory_frames": traj.n_frames,
        "trajectory_readable_pass": bool(
            traj.n_frames == expected_rows and traj.n_atoms > 0
        ),
        "contact_occupancy_generated_pass": bool(
            len(contacts) > 0 and contacts_path.stat().st_size > 0
        ),
        "binding_site_snapshots_generated_pass": bool(
            snapshot_path.exists() and snapshot_path.stat().st_size > 0
        ),
        "ligand_identity_image_generated_pass": bool(
            identity_path.exists() and identity_path.stat().st_size > 0
        ),
    }
    status = (
        "PASS"
        if all(value for key, value in checks.items() if key.endswith("_pass"))
        else "FAIL"
    )
    write_json(
        run / "gate.json",
        {"phase": 3, "profile": args.profile, "status": status, "checks": checks},
    )
    (run / "REPORT.md").write_text(f"""# Phase 3 report — {args.profile}

## Objective
Parameterize and simulate the T4 lysozyme L99A–benzene complex using independent coordinate and chemical-identity sources.

## Chemical identity

- Ligand: {ligand_audit["name"]} (`{ligand_audit["resname"]}`), formula {ligand_audit["formula"]}, formal charge {ligand_audit["formal_charge"]}.
- CCD SDF atoms: {ligand_audit["sdf_atoms_including_hydrogen"]} with hydrogens and {ligand_audit["sdf_atoms_excluding_hydrogen"]} heavy atoms.
- Aromatic bonds: {ligand_audit["aromatic_bonds"]}; stereocenters: {len(ligand_audit["stereocenters"])}.
- PDB-to-SDF mapping: one-to-one by CCD atom order and bond graph.
- Assigned small-molecule force field: `{ligand_audit["assigned_forcefield_version"]}`.
- Unassigned-parameter exception: none.

## Quantitative results

- Mean temperature: {mean_temp:.2f} K.
- Mean density: {mean_density:.4f} g/mL.
- Maximum protein Cα RMSD: {max_protein_rmsd:.4f} nm.
- Maximum ligand RMSD after protein alignment: {max_ligand_rmsd:.4f} nm.
- Maximum ligand COM displacement: {max_ligand_com:.4f} nm.
- Minimum ligand–protein heavy-atom distance: {float(np.min(min_distance)):.4f} nm.
- Maximum covalent-bond length: {max_bond_nm:.4f} nm.
- Frames analyzed: {traj.n_frames}.
- CUDA production performance: {performance["production_ns_per_day"]:.1f} ns/day.

## Figures

- Thermodynamics: `temperature.png` and `density.png`.
- Motion: `protein_rmsd.png`, `ligand_rmsd.png`, `ligand_com.png`, and `minimum_distance.png`.
- Contacts: `contact_occupancy.png` uses a {contact_cutoff_nm:.2f} nm heavy-atom cutoff.
- Binding site: `binding_site_snapshots.png` shows beginning, middle, and end.
- Identity: `ligand_identity_2d.png` is generated from the immutable CCD SDF.

## Interpretation limits

Ligand pose retention in this tutorial-length trajectory is a setup sanity
check, not a binding-affinity measurement. Ligand movement would require
inspection of preparation, protonation, force-field limitations, equilibration,
and alternative poses; it would not by itself prove poor binding.

## Gate
**{status}**
""", encoding="utf-8")
    finish_manifest(
        run,
        "ANALYSIS_COMPLETE" if status == "PASS" else "GATE_FAILED",
        {"gate": status},
    )
    print(json.dumps({"status": status, "checks": checks}, indent=2))
    if status != "PASS":
        raise SystemExit("Phase 3 gate failed")


if __name__ == "__main__": main()
