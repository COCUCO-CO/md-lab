#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from itertools import combinations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import mdtraj as md
import numpy as np
import pandas as pd

from mdlab.analysis_utils import trajectory_times_from_log
from mdlab.core import finish_manifest, latest_run, read_json, resolve_config, write_json


def col(df: pd.DataFrame, token: str) -> str:
    matches = [c for c in df.columns if token.lower() in c.lower()]
    if not matches:
        raise KeyError(f"Missing column {token}: {list(df.columns)}")
    return matches[0]


def save(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def protein_sasa(traj: md.Trajectory, protein_indices: np.ndarray) -> np.ndarray:
    protein_traj = traj.atom_slice(protein_indices)
    return md.shrake_rupley(protein_traj, mode="residue").sum(axis=1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["quick", "teaching"], default="quick")
    args = parser.parse_args()
    cfg = resolve_config(2, args.profile)
    run = latest_run(2, args.profile)
    fig = run / "figures"
    ana = run / "analysis"
    fig.mkdir(exist_ok=True)
    ana.mkdir(exist_ok=True)

    log = pd.read_csv(run / "simulation" / "production.csv")
    time = col(log, "Time")
    temp = col(log, "Temperature")
    density = col(log, "Density")
    volume = col(log, "Box Volume") if any("Box Volume" in c for c in log.columns) else col(log, "Volume")
    potential = col(log, "Potential Energy")

    plt.figure(figsize=(8, 4.5)); plt.plot(log[time], log[temp]); plt.axhline(cfg["temperature_kelvin"], linestyle="--")
    plt.xlabel("Time (ps)"); plt.ylabel("Temperature (K)"); plt.title("Phase 2 production temperature"); save(fig / "temperature.png")
    plt.figure(figsize=(8, 4.5)); plt.plot(log[time], log[density]); plt.xlabel("Time (ps)"); plt.ylabel("Density (g/mL)"); plt.title("Phase 2 density"); save(fig / "density.png")
    plt.figure(figsize=(8, 4.5)); plt.plot(log[time], log[potential]); plt.xlabel("Time (ps)"); plt.ylabel("Potential energy (kJ/mol)"); plt.title("Phase 2 potential energy"); save(fig / "potential_energy.png")
    plt.figure(figsize=(8, 4.5)); plt.plot(log[time], log[volume]); plt.xlabel("Time (ps)"); plt.ylabel("Box volume (nm³)"); plt.title("Phase 2 box volume"); save(fig / "volume.png")

    traj = md.load(str(run / "simulation" / "production.dcd"), top=str(run / "prepared" / "system.pdb"))
    ca = traj.topology.select("protein and name CA")
    protein = traj.topology.select("protein")
    if len(ca) == 0:
        raise RuntimeError("No protein C-alpha atoms found")
    traj.image_molecules(inplace=True)
    traj.superpose(traj, 0, atom_indices=ca)
    rmsd = md.rmsd(traj, traj, 0, atom_indices=ca)
    rmsf = md.rmsf(traj, traj, 0, atom_indices=ca)
    rg = md.compute_rg(traj.atom_slice(protein))
    sasa = protein_sasa(traj, protein)
    times = trajectory_times_from_log(log, time, traj.n_frames)
    pd.DataFrame({"time_ps": times, "ca_rmsd_nm": rmsd, "radius_gyration_nm": rg, "sasa_nm2": sasa}).to_csv(ana / "timeseries.csv", index=False)
    residues = [traj.topology.atom(i).residue for i in ca]
    pd.DataFrame({"residue_index": [r.index for r in residues], "residue": [str(r) for r in residues], "ca_rmsf_nm": rmsf}).to_csv(ana / "rmsf.csv", index=False)

    plt.figure(figsize=(8, 4.5)); plt.plot(times, rmsd); plt.xlabel("Time (ps)"); plt.ylabel("Cα RMSD (nm)"); plt.title("Phase 2 Cα RMSD after alignment"); save(fig / "ca_rmsd.png")
    plt.figure(figsize=(8, 4.5)); plt.plot([r.index for r in residues], rmsf); plt.xlabel("Residue index"); plt.ylabel("Cα RMSF (nm)"); plt.title("Phase 2 per-residue fluctuation"); save(fig / "ca_rmsf.png")
    plt.figure(figsize=(8, 4.5)); plt.plot(times, rg); plt.xlabel("Time (ps)"); plt.ylabel("Radius of gyration (nm)"); plt.title("Phase 2 protein compactness"); save(fig / "radius_gyration.png")
    plt.figure(figsize=(8, 4.5)); plt.plot(times, sasa); plt.xlabel("Time (ps)"); plt.ylabel("Total SASA (nm²)"); plt.title("Phase 2 solvent-accessible surface"); save(fig / "sasa.png")

    ca_pairs = np.array(list(combinations(ca, 2)), dtype=int)
    ca_distances = md.compute_distances(traj, ca_pairs, periodic=False)
    contact_occupancy = np.mean(ca_distances < 0.8, axis=0)
    contact_map = np.eye(len(ca))
    ca_positions = {atom_index: position for position, atom_index in enumerate(ca)}
    for pair, occupancy in zip(ca_pairs, contact_occupancy):
        first = ca_positions[int(pair[0])]
        second = ca_positions[int(pair[1])]
        contact_map[first, second] = occupancy
        contact_map[second, first] = occupancy
    pd.DataFrame(contact_map).to_csv(ana / "ca_contact_occupancy.csv", index=False)
    plt.figure(figsize=(6.5, 5.5))
    plt.imshow(contact_map, origin="lower", vmin=0.0, vmax=1.0, cmap="viridis")
    plt.colorbar(label="Contact occupancy (<0.8 nm)")
    plt.xlabel("Cα index")
    plt.ylabel("Cα index")
    plt.title("Phase 2 Cα contact map")
    save(fig / "ca_contact_map.png")

    first_ca = traj.xyz[0, ca]
    final_ca = traj.xyz[-1, ca]
    figure = plt.figure(figsize=(7, 6))
    axis = figure.add_subplot(111, projection="3d")
    axis.plot(first_ca[:, 0], first_ca[:, 1], first_ca[:, 2], label="first")
    axis.plot(final_ca[:, 0], final_ca[:, 1], final_ca[:, 2], label="final")
    axis.set(
        xlabel="x (nm)",
        ylabel="y (nm)",
        zlabel="z (nm)",
        title="Phase 2 Cα first/final overlay",
    )
    axis.legend()
    figure.tight_layout()
    figure.savefig(fig / "ca_first_final_overlay.png", dpi=180)
    plt.close(figure)

    bond_pairs = np.array(
        [[first.index, second.index] for first, second in traj.topology.bonds],
        dtype=int,
    )
    bond_lengths = md.compute_distances(traj, bond_pairs, periodic=False)
    max_bond_nm = float(np.max(bond_lengths))
    mean_temp = float(log[temp].mean())
    mean_density = float(log[density].mean())
    max_rmsd = float(np.max(rmsd))
    threshold_rmsd = cfg["gates"]["max_ca_rmsd_nm_quick" if args.profile == "quick" else "max_ca_rmsd_nm_teaching"]
    expected_rows = int(round(float(cfg["production_ps"]) / float(cfg["output_stride_ps"])))
    finite = bool(np.isfinite(log.select_dtypes(include=[np.number]).to_numpy()).all() and np.isfinite(traj.xyz).all())
    checks = {
        "finite_values": finite,
        "mean_temperature_K": mean_temp,
        "temperature_pass": bool(abs(mean_temp-cfg["temperature_kelvin"])/cfg["temperature_kelvin"] <= cfg["gates"]["max_temperature_relative_error"]),
        "mean_density_g_ml": mean_density,
        "density_pass": bool(cfg["gates"]["density_g_ml_min"] <= mean_density <= cfg["gates"]["density_g_ml_max"]),
        "max_ca_rmsd_nm": max_rmsd,
        "rmsd_pass": bool(max_rmsd <= threshold_rmsd),
        "max_covalent_bond_nm": max_bond_nm,
        "bond_geometry_pass": bool(max_bond_nm <= cfg["gates"]["max_unphysical_bond_nm"]),
        "thermodynamic_rows": len(log),
        "expected_thermodynamic_rows": expected_rows,
        "thermodynamic_rows_pass": bool(len(log) == expected_rows),
        "trajectory_frames": traj.n_frames,
        "trajectory_readable_pass": bool(traj.n_frames > 1 and traj.n_atoms > 0),
    }
    status = "PASS" if finite and all(v for k, v in checks.items() if k.endswith("_pass")) else "FAIL"
    write_json(run / "gate.json", {"phase": 2, "profile": args.profile, "status": status, "checks": checks})
    report = f"""# Phase 2 report — {args.profile}

## Objective
Prepare and simulate ubiquitin in explicit OPC water with 0.15 M NaCl using Amber ff19SB.

## Quantitative results

- Mean production temperature: {mean_temp:.2f} K.
- Mean production density: {mean_density:.4f} g/mL.
- Maximum Cα RMSD after Cα alignment: {max_rmsd:.4f} nm.
- Mean radius of gyration: {float(np.mean(rg)):.4f} nm.
- Maximum covalent-bond length: {max_bond_nm:.4f} nm.
- Frames analyzed: {traj.n_frames}.

## Figures

- Thermodynamics: `temperature.png`, `density.png`, `potential_energy.png`, and `volume.png`.
- Structure: `ca_rmsd.png`, `ca_rmsf.png`, `radius_gyration.png`, and `sasa.png`.
- Topology: `ca_contact_map.png` uses a 0.8 nm Cα contact definition.
- Geometry: `ca_first_final_overlay.png` compares aligned first and final Cα traces.

## Interpretation

RMSD measures deviation after the stated Cα alignment and does not by itself prove folding stability. An early rise can reflect relaxation away from the crystal environment. RMSF identifies relatively mobile residues over this trajectory. Density is assessed only during NPT production. Instantaneous pressure is not used as a small-system stability test because its fluctuations are large.

## Limitations

The {args.profile} trajectory is intended for pipeline validation and teaching. It is not sufficient for a biological claim about ubiquitin equilibrium behavior.

## Gate

**{status}**
"""
    (run / "REPORT.md").write_text(report, encoding="utf-8")
    finish_manifest(run, "ANALYSIS_COMPLETE" if status == "PASS" else "GATE_FAILED", {"gate": status})
    print(json.dumps({"status": status, "checks": checks}, indent=2))
    if status != "PASS":
        raise SystemExit("Phase 2 gate failed")


if __name__ == "__main__":
    main()
