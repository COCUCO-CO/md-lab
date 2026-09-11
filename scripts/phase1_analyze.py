#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import matplotlib.pyplot as plt
import mdtraj as md
import numpy as np
import pandas as pd
from scipy.signal import find_peaks

from mdlab.core import finish_manifest, latest_run, read_json, resolve_config, write_json


def find_col(df: pd.DataFrame, token: str) -> str:
    for col in df.columns:
        if token.lower() in col.lower():
            return col
    raise KeyError(f"Column containing {token!r} not found: {list(df.columns)}")


def passes_maximum(value: float, maximum: float) -> bool:
    return bool(value <= maximum)


def cumulative_displacement_magnitudes(
    xyz_nm: np.ndarray, box_lengths_nm: np.ndarray
) -> np.ndarray:
    increments = np.diff(xyz_nm, axis=0)
    boxes = box_lengths_nm[1:, np.newaxis, :]
    increments -= boxes * np.round(increments / boxes)
    return np.linalg.norm(increments.sum(axis=0), axis=1)


def save_plot(path: Path) -> None:
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["quick", "teaching"], default="quick")
    args = parser.parse_args()
    cfg = resolve_config(1, args.profile)
    run = latest_run(1, args.profile)
    figures = run / "figures"
    analysis = run / "analysis"
    figures.mkdir(exist_ok=True)
    analysis.mkdir(exist_ok=True)

    nvt = pd.read_csv(run / "simulation" / "nvt.csv")
    nve = pd.read_csv(run / "simulation" / "nve.csv")
    time_nvt = find_col(nvt, "Time")
    time_nve = find_col(nve, "Time")
    temp_col = find_col(nvt, "Temperature")
    total_nve_col = find_col(nve, "Total Energy")

    plt.figure(figsize=(8, 4.5))
    plt.plot(nvt[time_nvt], nvt[temp_col], label="NVT")
    plt.axhline(cfg["temperature_kelvin"], linestyle="--", label="target")
    plt.xlabel("Time (ps)")
    plt.ylabel("Temperature (K)")
    plt.title("Phase 1: NVT temperature")
    plt.legend()
    save_plot(figures / "temperature.png")

    plt.figure(figsize=(8, 4.5))
    for token in ["Potential Energy", "Kinetic Energy", "Total Energy"]:
        col = find_col(nve, token)
        plt.plot(nve[time_nve], nve[col], label=token)
    plt.xlabel("Time (ps)")
    plt.ylabel("Energy (kJ/mol)")
    plt.title("Phase 1: NVE energies")
    plt.legend()
    save_plot(figures / "nve_energies.png")

    x = nve[time_nve].to_numpy(dtype=float)
    y = nve[total_nve_col].to_numpy(dtype=float)
    slope_ps, intercept = np.polyfit(x, y, 1)
    drift = abs(slope_ps) * 1000.0 / float(cfg["particles"])
    plt.figure(figsize=(8, 4.5))
    plt.plot(x, y, label="total energy")
    plt.plot(x, slope_ps * x + intercept, linestyle="--", label=f"linear drift={drift:.4g} kJ/mol/ns/particle")
    plt.xlabel("Time (ps)")
    plt.ylabel("Total energy (kJ/mol)")
    plt.title("Phase 1: NVE energy drift")
    plt.legend()
    save_plot(figures / "nve_drift.png")

    traj = md.load(str(run / "simulation" / "nvt.dcd"), top=str(run / "prepared" / "initial.pdb"))
    pairs = np.array(list(combinations(range(traj.n_atoms), 2)), dtype=int)
    rmax = min(float(cfg["cutoff_nm"]), float(np.min(traj.unitcell_lengths)) / 2.0)
    r, g = md.compute_rdf(traj, pairs, r_range=(0.0, rmax), bin_width=0.01, periodic=True)
    mask = r > 0.25
    peaks, _ = find_peaks(g[mask])
    if len(peaks):
        peak_idx = np.where(mask)[0][peaks[np.argmax(g[mask][peaks])]]
        first_peak = float(g[peak_idx])
        first_peak_r = float(r[peak_idx])
    else:
        first_peak = float("nan")
        first_peak_r = float("nan")
    pd.DataFrame({"r_nm": r, "g_r": g}).to_csv(analysis / "rdf.csv", index=False)
    plt.figure(figsize=(8, 4.5))
    plt.plot(r, g)
    plt.axhline(1.0, linestyle="--")
    plt.xlabel("r (nm)")
    plt.ylabel("g(r)")
    plt.title("Phase 1: radial distribution function")
    save_plot(figures / "rdf.png")

    displacements = cumulative_displacement_magnitudes(traj.xyz, traj.unitcell_lengths)
    pd.DataFrame(
        {"particle": np.arange(traj.n_atoms), "displacement_nm": displacements}
    ).to_csv(analysis / "particle_displacements.csv", index=False)
    plt.figure(figsize=(8, 4.5))
    plt.hist(displacements, bins=20)
    plt.xlabel("Cumulative displacement (nm)")
    plt.ylabel("Particle count")
    plt.title("Phase 1: particle displacement distribution")
    save_plot(figures / "particle_displacements.png")

    final_positions = traj.xyz[-1]
    box_lengths = traj.unitcell_lengths[-1]
    fig = plt.figure(figsize=(7, 7))
    ax = fig.add_subplot(111, projection="3d")
    ax.scatter(
        final_positions[:, 0],
        final_positions[:, 1],
        final_positions[:, 2],
        s=18,
        alpha=0.8,
    )
    corners = np.array(
        [
            [x, y, z]
            for x in (0.0, box_lengths[0])
            for y in (0.0, box_lengths[1])
            for z in (0.0, box_lengths[2])
        ]
    )
    for start, end in combinations(corners, 2):
        if np.count_nonzero(start != end) == 1:
            ax.plot(*zip(start, end), color="black", linewidth=0.8)
    ax.set(
        xlabel="x (nm)",
        ylabel="y (nm)",
        zlabel="z (nm)",
        title="Phase 1: final NVT box snapshot",
    )
    ax.set_box_aspect(box_lengths)
    fig.tight_layout()
    fig.savefig(figures / "box_snapshot.png", dpi=180)
    plt.close(fig)

    mean_temp = float(nvt[temp_col].mean())
    temp_rel = abs(mean_temp - float(cfg["temperature_kelvin"])) / float(cfg["temperature_kelvin"])
    finite = bool(np.isfinite(nvt.select_dtypes(include=[np.number]).to_numpy()).all() and np.isfinite(nve.select_dtypes(include=[np.number]).to_numpy()).all())
    checks = {
        "finite_values": finite,
        "temperature_relative_error": temp_rel,
        "temperature_pass": passes_maximum(
            temp_rel, float(cfg["gates"]["max_temperature_relative_error"])
        ),
        "nve_drift_kj_mol_ns_per_particle": drift,
        "nve_drift_pass": passes_maximum(
            drift, float(cfg["gates"]["max_nve_energy_drift_kj_mol_ns_per_particle"])
        ),
        "rdf_first_peak_height": first_peak,
        "rdf_first_peak_r_nm": first_peak_r,
        "rdf_pass": bool(np.isfinite(first_peak) and cfg["gates"]["rdf_first_peak_min"] <= first_peak <= cfg["gates"]["rdf_first_peak_max"]),
        "trajectory_frames": traj.n_frames,
        "trajectory_atoms": traj.n_atoms,
        "atom_count_pass": traj.n_atoms == int(cfg["particles"]),
        "median_particle_displacement_nm": float(np.median(displacements)),
        "max_particle_displacement_nm": float(np.max(displacements)),
    }
    status = "PASS" if all(v for k, v in checks.items() if k.endswith("_pass")) and finite else "FAIL"
    gate = {"phase": 1, "profile": args.profile, "status": status, "checks": checks}
    write_json(run / "gate.json", gate)
    (analysis / "summary.json").write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")

    report = f"""# Phase 1 report — {args.profile}

## Objective
Validate integration, periodic boundaries, thermostat behavior, NVE energy conservation, and liquid structure in a Lennard-Jones fluid.

## Results

- Mean NVT temperature: {mean_temp:.3f} K; target {cfg['temperature_kelvin']} K; relative error {temp_rel:.3%}.
- NVE linear energy drift: {drift:.6g} kJ/mol/ns/particle.
- RDF strongest first-neighbor peak: g(r)={first_peak:.3f} at r={first_peak_r:.3f} nm.
- Median cumulative particle displacement: {np.median(displacements):.3f} nm; maximum {np.max(displacements):.3f} nm.
- Frames analyzed: {traj.n_frames}; particles: {traj.n_atoms}.

## Figures

- `temperature.png`: instantaneous NVT temperature and the 120 K target.
- `nve_energies.png`: potential, kinetic, and total energy exchange in NVE.
- `nve_drift.png`: total-energy fluctuations and the fitted drift.
- `rdf.png`: pair structure as a function of separation.
- `particle_displacements.png`: cumulative minimum-image displacements.
- `box_snapshot.png`: final wrapped NVT coordinates and periodic box.

## Interpretation

Temperature fluctuates because it is an instantaneous kinetic estimator for a finite system. The Langevin thermostat exchanges energy with the particles, so total energy is not expected to remain constant during NVT. The NVE continuation removes thermostat exchange and is used to quantify numerical drift. The RDF peak shows preferred neighbor separation in the liquid; g(r) approaching one at longer range indicates loss of pair correlation. A particle that crosses a periodic boundary is wrapped to the opposite face, so a viewer can show an apparent jump even though its physical motion is continuous.

## Limitations

This is an argon-like pedagogical model with a cutoff treatment, not a high-accuracy experimental argon calculation. The tutorial-length trajectory tests the {args.profile} workflow rather than thermodynamic convergence.

## Gate

**{status}**
"""
    (run / "REPORT.md").write_text(report, encoding="utf-8")
    finish_manifest(run, "ANALYSIS_COMPLETE" if status == "PASS" else "GATE_FAILED", {"gate": status})
    print(json.dumps(gate, indent=2))
    if status != "PASS":
        raise SystemExit("Phase 1 gate failed")


if __name__ == "__main__":
    main()
