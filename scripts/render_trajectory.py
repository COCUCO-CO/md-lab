#!/usr/bin/env python
# ruff: noqa: E402
from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import mdtraj as md

from mdlab.core import latest_run, read_json


def center_periodic_components(trajectory: md.Trajectory) -> None:
    if trajectory.unitcell_lengths is None:
        raise RuntimeError("Cannot center components without unit-cell lengths")
    groups: list[list[int]] = []
    for chain in trajectory.topology.chains:
        protein_atoms = [
            atom.index
            for residue in chain.residues
            if residue.is_protein
            for atom in residue.atoms
        ]
        if protein_atoms:
            groups.append(protein_atoms)
    for residue in trajectory.topology.residues:
        if not residue.is_protein:
            groups.append([atom.index for atom in residue.atoms])
    for frame in range(trajectory.n_frames):
        box = trajectory.unitcell_lengths[frame]
        for indices in groups:
            center = trajectory.xyz[frame, indices, :].mean(axis=0)
            centered_image = center - box * (center / box).round()
            trajectory.xyz[frame, indices, :] += centered_image - center


def choose_files(run: Path, phase: int) -> tuple[Path, Path, str]:
    if phase == 1:
        return run / "simulation" / "nvt.dcd", run / "prepared" / "initial.pdb", "all"
    traj = run / "simulation" / "production.dcd"
    top = run / "prepared" / "system.pdb"
    selection = {
        2: "protein",
        3: "protein or resname BNZ",
        4: "protein",
    }[phase]
    return traj, top, selection


def render_phase5(run: Path, profile: str, max_frames: int) -> None:
    config = read_json(run / "manifest.json")
    condition_outputs = config.get("outputs", {}).get("conditions", {})
    if not condition_outputs:
        raise RuntimeError("Phase 5 manifest has no completed condition outputs")
    ligand_resnames = {"lsd": "7LD", "lisuride": "H8G"}
    for condition_name, ligand_resname in ligand_resnames.items():
        condition_dir = run / "systems" / condition_name
        traj_path = condition_dir / "simulation" / "production.dcd"
        top_path = condition_dir / "prepared" / "system.pdb"
        full_traj = md.load(str(traj_path), top=str(top_path))
        base_indices = set(
            int(index)
            for index in full_traj.topology.select(
                "(protein or resname POP) and not element H"
            )
        )
        ligand_indices = {
            atom.index
            for residue in full_traj.topology.residues
            if residue.name == ligand_resname
            for atom in residue.atoms
            if atom.element is not None and atom.element.symbol != "H"
        }
        atom_indices = sorted(base_indices | ligand_indices)
        if len(atom_indices) == 0:
            raise RuntimeError(
                f"Phase 5 viewer selection is empty for {condition_name}"
            )
        trajectory = full_traj.atom_slice(atom_indices)
        frame_cap = min(max_frames, 12)
        stride = max(1, full_traj.n_frames // frame_cap)
        trajectory = trajectory[::stride]
        center_periodic_components(trajectory)
        output = condition_dir / "visualization"
        output.mkdir(exist_ok=True)
        multimodel_path = output / "trajectory_multimodel.pdb"
        trajectory.save_pdb(str(multimodel_path))
        pdb_text = multimodel_path.read_text(encoding="utf-8")
        html_text = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Phase 5 {html.escape(condition_name)}</title>
<script src='https://3Dmol.org/build/3Dmol-min.js'></script></head>
<body style='margin:0'><div id='viewer' style='width:100vw;height:92vh;position:relative'></div>
<div style='padding:8px;font-family:sans-serif'>Phase 5 {html.escape(condition_name)}, profile {html.escape(profile)}. Frames: {trajectory.n_frames}. Protein: rainbow cartoon; ligand: green sticks/spheres; POPC phosphorus: orange spheres. Drag to rotate, scroll to zoom, right-drag to translate.</div>
<script>
const pdb = {pdb_text!r};
const viewer = $3Dmol.createViewer('viewer', {{backgroundColor:'white'}});
viewer.addModelsAsFrames(pdb, 'pdb');
viewer.setStyle({{}},{{}});
viewer.setStyle({{resn:['ALA','ARG','ASN','ASP','CYS','GLN','GLU','GLY','HIS','HID','HIE','HIP','ILE','LEU','LYS','MET','PHE','PRO','SER','THR','TRP','TYR','VAL']}},{{cartoon:{{color:'spectrum',opacity:1.0}}}});
viewer.setStyle({{resn:'{ligand_resname}'}},{{stick:{{radius:0.24,color:'green'}},sphere:{{scale:0.26}}}});
viewer.setStyle({{resn:'POP'}},{{line:{{color:'lightgray',opacity:0.12}}}});
viewer.setStyle({{resn:'POP',atom:'P'}},{{sphere:{{scale:0.32,color:'orange'}}}});
viewer.setStyle({{resi:['155','227','229','239','343']}},{{stick:{{radius:0.12}}}});
viewer.addUnitCell();
viewer.zoomTo({{resn:'{ligand_resname}'}});
viewer.zoom(0.30);
viewer.animate({{loop:'forward',interval:100}});
viewer.render();
</script></body></html>"""
        html_path = output / "viewer.html"
        html_path.write_text(html_text, encoding="utf-8")
        vmd_commands = [
            f"set topology_path {{{top_path.resolve()}}}",
            f"set trajectory_path {{{traj_path.resolve()}}}",
            "mol new $topology_path type pdb waitfor all",
            (
                "mol addfile $trajectory_path type dcd first 0 last -1 "
                f"step {stride} waitfor all"
            ),
            "animate delete beg 0 end 0 top",
            f"mol rename top {{MD Lab Phase 5 {condition_name} {profile}}}",
            "mol delrep 0 top",
            "mol representation NewCartoon 0.3 12.0 4.1",
            "mol color ResID",
            "mol selection {protein}",
            "mol material Opaque",
            "mol addrep top",
            "mol representation Licorice 0.24 12.0 12.0",
            "mol color ColorID 7",
            f"mol selection {{resname {ligand_resname}}}",
            "mol material Opaque",
            "mol addrep top",
            "mol representation Licorice 0.12 12.0 12.0",
            "mol color Name",
            "mol selection {protein and resid 155 227 229 239 343}",
            "mol material Opaque",
            "mol addrep top",
            "mol representation Lines 1.0",
            "mol color Name",
            "mol selection {resname POP}",
            "mol material Transparent",
            "mol addrep top",
            "mol representation VDW 0.42 12.0",
            "mol color ColorID 3",
            "mol selection {resname POP and name P}",
            "mol material Opaque",
            "mol addrep top",
            "color Display Background white",
            "axes location Off",
            "display projection Orthographic",
            "display resetview",
            "if {[catch {package require pbctools} pbc_error]} {",
            '    puts "Warning: pbctools unavailable: $pbc_error"',
            "} else {",
            "    pbc wrap -all -compound fragment -center com -centersel {protein}",
            "    pbc box -on -center origin -color black -width 2",
            "}",
            "animate style Loop",
            "animate speed 0.5",
            "animate goto 0",
            (
                'puts "Loaded [molinfo top get numframes] frames and '
                '[molinfo top get numatoms] atoms"'
            ),
        ]
        vmd_path = output / "viewer.vmd"
        vmd_path.write_text("\n".join(vmd_commands) + "\n", encoding="utf-8")
        print(html_path)
        print(vmd_path)
    top_level = run / "visualization"
    top_level.mkdir(exist_ok=True)
    index_path = top_level / "index.html"
    index_path.write_text(
        f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Phase 5 viewer index</title>
<style>
body {{font-family:system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 20px}}
.card {{border:1px solid #ccc;border-radius:12px;padding:20px;margin:18px 0}}
a {{font-size:1.15rem}}
code {{background:#f4f4f4;padding:2px 5px}}
</style></head><body>
<h1>Phase 5 — {html.escape(profile)}</h1>
<p>Choose one matched 5-HT2A–BRIL condition. Each viewer contains 13 sampled
frames and has a local VMD script beside it.</p>
<div class='card'><h2>LSD / 7WC6</h2>
<a href='../systems/lsd/visualization/viewer.html'>Open interactive 3Dmol viewer</a>
<p>Local VMD: <code>systems/lsd/visualization/viewer.vmd</code></p></div>
<div class='card'><h2>Lisuride / 7WC7</h2>
<a href='../systems/lisuride/visualization/viewer.html'>Open interactive 3Dmol viewer</a>
<p>Local VMD: <code>systems/lisuride/visualization/viewer.vmd</code></p></div>
</body></html>""",
        encoding="utf-8",
    )
    print(index_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4, 5],
        required=True,
    )
    parser.add_argument("--profile", choices=["quick", "teaching"], default="quick")
    parser.add_argument("--max-frames", type=int, default=100)
    args = parser.parse_args()
    run = latest_run(args.phase, args.profile)
    if args.phase == 5:
        render_phase5(run, args.profile, args.max_frames)
        return
    traj_path, top_path, selection = choose_files(run, args.phase)
    if not traj_path.exists() or not top_path.exists():
        raise FileNotFoundError(f"Missing trajectory/topology: {traj_path}, {top_path}")
    full_traj = md.load(str(traj_path), top=str(top_path))
    full_frame_count = full_traj.n_frames
    source_water_oxygen_indices: list[int] = []
    lipid_resname = "POP"
    if args.phase == 4:
        audit = read_json(run / "prepared" / "preparation_audit.json")
        lipid_resname = str(audit["lipid_resname"])
        source_water_oxygen_indices = [
            int(index)
            for index in audit["retained_source_water_oxygen_indices"]
        ]
        source_residues = {
            full_traj.topology.atom(index).residue.index
            for index in source_water_oxygen_indices
        }
        source_water_atoms = [
            atom.index
            for residue in full_traj.topology.residues
            if residue.index in source_residues
            for atom in residue.atoms
        ]
        base_atoms = full_traj.topology.select(
            f"(protein or resname {lipid_resname}) and not element H"
        )
        atom_indices = sorted(
            set(int(index) for index in base_atoms)
            | set(source_water_atoms)
        )
    else:
        atom_indices = full_traj.topology.select(selection)
    if len(atom_indices) == 0:
        raise RuntimeError(f"Selection returned no atoms: {selection}")
    traj = full_traj.atom_slice(atom_indices)
    frame_cap = min(args.max_frames, 12) if args.phase == 4 else args.max_frames
    stride = max(1, full_frame_count // frame_cap)
    traj = traj[::stride]
    if args.phase == 4:
        center_periodic_components(traj)
    out_dir = run / "visualization"
    out_dir.mkdir(exist_ok=True)
    pdb_path = out_dir / "trajectory_multimodel.pdb"
    traj.save_pdb(str(pdb_path))
    pdb_text = pdb_path.read_text(encoding="utf-8")
    if traj.unitcell_lengths is None or traj.unitcell_angles is None:
        raise RuntimeError("Periodic box information is required for visualization")
    cell = [
        *(10.0 * traj.unitcell_lengths[0]),
        *traj.unitcell_angles[0],
    ]
    vmd_cell = " ".join(f"{value:.6f}" for value in cell)

    style = "{sphere:{scale:0.45}}" if args.phase == 1 else "{cartoon:{color:'spectrum'},stick:{radius:0.15}}"
    if args.phase == 3:
        style_commands = "viewer.setStyle({protein:true},{cartoon:{color:'spectrum'}}); viewer.setStyle({resn:'BNZ'},{stick:{radius:0.22},sphere:{scale:0.25}});"
    elif args.phase == 4:
        protein_resnames = [
            "ALA",
            "ARG",
            "ASN",
            "ASP",
            "CYS",
            "GLN",
            "GLU",
            "GLY",
            "HIS",
            "ILE",
            "LEU",
            "LYS",
            "MET",
            "PHE",
            "PRO",
            "SER",
            "THR",
            "TRP",
            "TYR",
            "VAL",
        ]
        protein_selection = ",".join(
            f"'{name}'" for name in protein_resnames
        )
        style_commands = (
            "viewer.setStyle({},{}); "
            f"viewer.setStyle({{resn:[{protein_selection}]}},"
            "{cartoon:{color:'spectrum',opacity:1.0}}); "
            f"viewer.setStyle({{resn:'{lipid_resname}'}},"
            "{line:{color:'lightgray',opacity:0.12}}); "
            f"viewer.setStyle({{resn:'{lipid_resname}',atom:'P'}},"
            "{sphere:{scale:0.30,color:'orange'}}); "
            "viewer.setStyle({resn:'HOH',atom:'O'},"
            "{sphere:{scale:0.22,color:'deepskyblue'}});"
        )
    else:
        style_commands = f"viewer.setStyle({{}},{style});"
    box_command = (
        "viewer.addUnitCell();" if args.phase in {1, 4} else ""
    )

    html_text = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>MD Learning Lab Phase {args.phase}</title>
<script src='https://3Dmol.org/build/3Dmol-min.js'></script></head>
<body style='margin:0'><div id='viewer' style='width:100vw;height:92vh;position:relative'></div>
<div style='padding:8px;font-family:sans-serif'>Phase {args.phase}, profile {html.escape(args.profile)}. Frames: {traj.n_frames}. Drag to rotate; scroll to zoom; right-drag to translate. For a fully local viewer, run <code>vmd -e viewer.vmd</code> from this directory.</div>
<script>
const pdb = {pdb_text!r};
const viewer = $3Dmol.createViewer('viewer', {{backgroundColor:'white'}});
viewer.addModelsAsFrames(pdb, 'pdb');
{style_commands}
{box_command}
viewer.zoomTo();
viewer.zoom(1.5);
viewer.animate({{loop:'forward',interval:100}});
viewer.render();
</script></body></html>"""
    html_path = out_dir / "viewer.html"
    html_path.write_text(html_text, encoding="utf-8")

    vmd_representations = {
        1: [
            "mol representation VDW 0.45 12.0",
            "mol color Element",
            "mol selection {all}",
            "mol material Opaque",
            "mol addrep top",
        ],
        2: [
            "mol representation NewCartoon 0.3 12.0 4.1",
            "mol color Structure",
            "mol selection {protein}",
            "mol material Opaque",
            "mol addrep top",
        ],
        3: [
            "mol representation NewCartoon 0.3 12.0 4.1",
            "mol color Structure",
            "mol selection {protein}",
            "mol material Opaque",
            "mol addrep top",
            "mol representation Licorice 0.2 12.0 12.0",
            "mol color Element",
            "mol selection {resname BNZ}",
            "mol material Opaque",
            "mol addrep top",
        ],
        4: [
            "mol representation NewCartoon 0.3 12.0 4.1",
            "mol color Structure",
            "mol selection {protein}",
            "mol material Opaque",
            "mol addrep top",
            "mol representation Lines 1.0",
            "mol color Name",
            f"mol selection {{resname {lipid_resname}}}",
            "mol material Transparent",
            "mol addrep top",
            "mol representation VDW 0.35 12.0",
            "mol color ColorID 0",
            f"mol selection {{index {' '.join(str(index) for index in source_water_oxygen_indices)}}}",
            "mol material Opaque",
            "mol addrep top",
            "mol representation VDW 0.45 12.0",
            "mol color ColorID 3",
            f"mol selection {{resname {lipid_resname} and name P}}",
            "mol material Opaque",
            "mol addrep top",
        ],
    }[args.phase]
    if args.phase == 4:
        vmd_commands = [
            f"set topology_path {{{top_path.resolve()}}}",
            f"set trajectory_path {{{traj_path.resolve()}}}",
            "mol new $topology_path type pdb waitfor all",
            (
                "mol addfile $trajectory_path type dcd first 0 last -1 "
                f"step {stride} waitfor all"
            ),
            "animate delete beg 0 end 0 top",
            f"mol rename top {{MD Learning Lab Phase {args.phase} {args.profile}}}",
            "mol delrep 0 top",
            *vmd_representations,
            "color Display Background white",
            "axes location Off",
            "display projection Orthographic",
            "display resetview",
            "if {[catch {package require pbctools} pbc_error]} {",
            '    puts "Warning: pbctools unavailable: $pbc_error"',
            "} else {",
            "    pbc wrap -all -compound fragment -center origin",
            "    pbc box -on -center origin -color black -width 2",
            "}",
            "animate style Loop",
            "animate speed 0.5",
            "animate goto 0",
            (
                'puts "Loaded [molinfo top get numframes] frames and '
                '[molinfo top get numatoms] atoms from the full DCD"'
            ),
        ]
    else:
        vmd_commands = [
            f"set script_dir {{{out_dir.resolve()}}}",
            "if {![file exists [file join $script_dir trajectory_multimodel.pdb]]} {",
            "    set script_dir [pwd]",
            "}",
            "mol new [file join $script_dir trajectory_multimodel.pdb] type pdb waitfor all",
            f"mol rename top {{MD Learning Lab Phase {args.phase} {args.profile}}}",
            "mol delrep 0 top",
            *vmd_representations,
            "color Display Background white",
            "axes location Off",
            "display projection Orthographic",
            "display resetview",
            "if {[catch {package require pbctools} pbc_error]} {",
            '    puts "Warning: pbctools unavailable: $pbc_error"',
            "} else {",
            f"    pbc set {{{vmd_cell}}} -all",
            "    pbc box -on -color black -width 2",
            "}",
            "animate style Loop",
            "animate speed 0.5",
            "animate goto 0",
            'puts "Loaded [molinfo top get numframes] frames and [molinfo top get numatoms] atoms"',
        ]
    vmd_path = out_dir / "viewer.vmd"
    vmd_path.write_text("\n".join(vmd_commands) + "\n", encoding="utf-8")
    print(html_path)
    print(vmd_path)


if __name__ == "__main__":
    main()
