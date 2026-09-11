# Learning log

The agent appends one section after each passed profile.

Required headings:

- What was simulated?
- What physical model was used?
- What did each major parameter control?
- Which plots were generated?
- What did the plots show directly?
- Which conclusions are not justified?
- Questions for the human learner

## Phase 0 — quick — 2026-07-26

### What was simulated?

No molecular-dynamics trajectory was produced. Phase 0 validated the isolated
software environment and compared OpenMM force calculations across the
Reference, CPU, CUDA, and OpenCL platforms.

### What physical model was used?

OpenMM's installation test used its internal validation system only to check
numerical agreement between compute platforms. It was not a scientific model
of a system studied by this curriculum.

### What did each major parameter control?

- NVIDIA driver 595.84 provided a PTX-compatible driver for the environment's
  CUDA/NVRTC 12.9 runtime.
- OpenMM 8.5.2 provided the simulation kernels.
- The CUDA platform used the RTX 4090 (compute capability 8.9, 24,564 MiB
  VRAM); Reference, CPU, and OpenCL provided comparison calculations.

### Which plots were generated?

None. Phase 0 generated environment exports and `state/doctor.json`.

### What did the plots show directly?

There were no plots. The numerical report showed successful force evaluation
on all four OpenMM platforms. The median Reference-versus-CUDA force
difference was `6.74406e-06`, within OpenMM's tolerance.

### Which conclusions are not justified?

This check does not measure production performance, trajectory stability,
convergence, sampling quality, or biological significance.

### Questions for the human learner

- Why can an older driver expose a CUDA platform yet fail when NVRTC compiles
  PTX for it?
- Why is agreement with the Reference platform more informative than merely
  detecting the GPU?

## Phase 1 — quick — 2026-07-26

### What was simulated?

A periodic fluid of 256 argon-like particles was run for 20 ps in NVT followed
by 20 ps in NVE. The quick profile validated the simulation and analysis
pipeline rather than thermodynamic convergence.

### What physical model was used?

Particles interacted through a Lennard-Jones potential with `sigma=0.34 nm`
and `epsilon=0.997 kJ/mol`. The cubic box used reduced number density 0.80, a
1.0 nm periodic cutoff, switching from 0.9 nm, and a long-range dispersion
correction.

### What did each major parameter control?

- The 120 K target set the intended NVT kinetic-energy scale.
- The Langevin friction of 1/ps controlled thermostat coupling.
- The 2 fs timestep set the numerical integration interval.
- NVE removed thermostat energy exchange for the drift measurement.
- Seed 20260810 fixed the quick-profile initial velocities reproducibly.

### Which plots were generated?

NVT temperature, NVE energy components, fitted NVE energy drift, radial
distribution function, cumulative particle-displacement distribution, and a
final periodic-box snapshot. An interactive 100-frame HTML viewer was also
generated.

### What did the plots show directly?

The NVT mean temperature was 118.053 K, 1.622% below the 120 K target.
Potential and kinetic energy exchanged in NVE while the fitted total-energy
drift was `0.000131942 kJ/mol/ns/particle`. The strongest first-neighbor RDF
peak was `g(r)=2.647` at 0.365 nm, followed by damped pair correlations. The
median cumulative particle displacement was 0.427 nm and the wrapped final
snapshot retained a filled periodic box without visible voids or explosions.

### Which conclusions are not justified?

The quick trajectory does not establish experimental argon properties,
thermodynamic convergence, a diffusion coefficient, or the behavior of a
macroscopic liquid. Apparent boundary jumps are coordinate wrapping, not
physical discontinuities.

### Questions for the human learner

- Why does the thermostat permit NVT total energy to change while the NVE
  continuation should conserve total energy?
- What do the first RDF peak and the approach of `g(r)` toward one say about
  short-range order versus long-range correlation?

## Phase 1 — teaching — 2026-07-26

### What was simulated?

The same 256-particle periodic Lennard-Jones fluid was extended to 200 ps NVT
and 200 ps NVE with the teaching seed 20260811.

### What physical model was used?

The Hamiltonian, density, cutoff, switching region, and long-range dispersion
correction were unchanged from the validated quick baseline.

### What did each major parameter control?

The longer 200 ps intervals increased the number of observed fluctuations and
particle displacements without changing the 120 K target, 2 fs timestep, or
1/ps Langevin coupling used in NVT.

### Which plots were generated?

The same six static figures as quick were regenerated over the longer time
range, together with a 100-frame downsampled VMD/HTML visualization.

### What did the plots show directly?

The NVT mean was 119.563 K, 0.364% below target. The NVE drift was
`0.0000481208 kJ/mol/ns/particle`. The first RDF peak remained at 0.365 nm
with height 2.638. Median cumulative displacement increased to 1.428 nm, as
expected for the longer observation window, while the wrapped box remained
filled without visible explosions or vacuum gaps.

### Which conclusions are not justified?

The teaching trajectory still does not establish thermodynamic convergence,
experimental transport properties, or a rigorously estimated diffusion
coefficient. Its single deterministic realization provides no replica-level
uncertainty.

### Questions for the human learner

- Why did the fitted drift estimate decrease when the observation window
  became longer?
- Which additional analysis and replicas would be needed before estimating a
  diffusion coefficient?

## Phase 2 — quick — 2026-07-26

### What was simulated?

Ubiquitin (PDB 1UBQ, 76 residues) was prepared at pH 7 and simulated in an
explicit periodic water box. After minimization, restrained NVT/NPT
equilibration, and restraint release, the quick profile produced 100 ps of
unrestrained NPT production on CUDA.

### What physical model was used?

The protein used Amber ff19SB and the solvent used the OPC force field with
compatible Na+/Cl- parameters at 0.15 M. The deterministic prepared system
contained 22,637 particles, 5,344 waters, 15 Na+, and 15 Cl- in an initial
5.6898 nm cubic box.

### What did each major parameter control?

- The 300 K target and 1/ps Langevin friction controlled thermal coupling.
- The 1 bar Monte Carlo barostat allowed the periodic box to relax in NPT.
- The 2 fs timestep, HBond constraints, and rigid water controlled integration.
- The 1.0 nm nonbonded cutoff and PME treated short- and long-range interactions.
- Seed 20260910 controlled preparation and dynamics; hydrogen placement used
  the deterministic Reference platform before production used CUDA mixed
  precision.

### Which plots were generated?

Temperature, density, potential energy, box volume, aligned Cα RMSD,
per-residue Cα RMSF, radius of gyration, protein SASA, Cα contact occupancy,
and an aligned first/final Cα overlay. HTML and local VMD viewers were also
generated; VMD loaded all 50 frames.

### What did the plots show directly?

Production averaged 301.18 K and 1.0233 g/mL. Maximum aligned Cα RMSD was
0.0997 nm, mean radius of gyration was 1.1724 nm, and maximum covalent-bond
length was 0.1927 nm. The contact map retained the expected compact topology,
with larger RMSF near the C terminus over this short window. CUDA performance
was 757.7 ns/day for the 100 ps production segment.

### Which conclusions are not justified?

Flat or small RMSD does not establish protein stability, equilibrium, or a
biological mechanism. The 100 ps quick trajectory is a pipeline sanity check;
it is too short for converged conformational populations or meaningful
biological inference.

### Questions for the human learner

- Why must RMSD be interpreted together with its atom selection, alignment,
  and reference frame?
- Why can density be a useful NPT check while instantaneous pressure remains
  extremely noisy for a box of this size?

## Phase 2 — teaching — 2026-07-26

### What was simulated?

The validated ubiquitin/OPC/NaCl system was extended through 100 ps NVT,
three 200 ps restrained NPT segments, and 2 ns of unrestrained NPT production
using the teaching seed 20260911.

### What physical model was used?

Amber ff19SB, OPC water, 0.15 M NaCl, PME electrostatics, HBond constraints,
and the 300 K/1 bar ensemble choices were unchanged from quick. The
seed-specific deterministic preparation contained 22,383 particles, 5,281
waters, 14 Na+, and 14 Cl-.

### What did each major parameter control?

The teaching profile lengthened equilibration and production while preserving
the validated 2 fs timestep, 1/ps Langevin coupling, 1.0 nm cutoff, restraint
schedule, and validation thresholds. Coordinates were written every 10 ps,
giving 200 production frames.

### Which plots were generated?

The same ten thermodynamic, structural, contact, and geometry plots as quick
were generated over the teaching trajectory. The HTML viewer and local VMD
viewer were regenerated; the VMD representation loaded 100 evenly sampled
frames from the 200-frame production trajectory.

### What did the plots show directly?

Production averaged 300.33 K and 1.0239 g/mL. Maximum aligned Cα RMSD was
0.1546 nm, mean radius of gyration was 1.1755 nm, and maximum covalent-bond
length was 0.1928 nm. The C terminus had the largest RMSF, while the contact
map remained consistent with a compact ubiquitin fold over this trajectory.
CUDA production performance was 778.1 ns/day.

### Which conclusions are not justified?

Two nanoseconds and one deterministic realization do not demonstrate
thermodynamic convergence, folding stability, equilibrium populations, or a
biological mechanism. The larger terminal RMSF is an observation over this
window, not evidence of a general functional role.

### Questions for the human learner

- Why is terminal RMSF often larger even when the folded core remains compact?
- What replicas and convergence diagnostics would be needed before comparing
  conformational populations quantitatively?

## Phase 3 — quick — 2026-07-27

### What was simulated?

The resolved portion of T4 lysozyme L99A from PDB 181L was simulated with one
benzene molecule in its crystallographic cavity. ASN163–LEU164 remained
unbuilt, while HED, source chlorides, and bulk crystallographic water were
removed before controlled resolvation. The quick profile produced 200 ps of
unrestrained NPT production.

### What physical model was used?

Protein parameters came from Amber ff19SB, benzene from OpenFF 2.2.1 with
AM1-BCC charges, and solvent/ions from OPC-compatible parameters at 0.15 M.
The immutable CCD SDF established BNZ as neutral C6H6 with six aromatic bonds,
no stereocenters, and an explicit C1–H1 through C6–H6 graph.

### What did each major parameter control?

- Seed 20261010 fixed hydrogen placement, solvation, ions, and dynamics.
- Reference-platform hydrogen placement made preparation reproducible; CUDA
  mixed precision ran the dynamics.
- The 300 K/1 bar ensemble, 2 fs timestep, HBond constraints, 1.0 nm cutoff,
  and staged restraint release matched the validated biomolecular workflow.
- A 0.45 nm heavy-atom cutoff defined residue contact occupancy.

### Which plots were generated?

Temperature, density, protein Cα RMSD, aligned ligand heavy-atom RMSD, true
mass-weighted ligand COM displacement, minimum ligand–protein distance, contact
occupancies, three binding-site snapshots, and a 2D identity image from the
CCD SDF. The HTML/VMD complex viewers were also generated; VMD loaded all 100
frames with separate protein and BNZ representations.

### What did the plots show directly?

Production averaged 300.34 K and 1.0258 g/mL. Maximum protein Cα RMSD was
0.1186 nm, maximum ligand RMSD was 0.2926 nm, maximum ligand COM displacement
was 0.1098 nm, and minimum ligand–protein heavy-atom distance was 0.3089 nm.
The expected hydrophobic cavity residues dominated the 0.45 nm contact
occupancies. Maximum covalent-bond length was 0.1919 nm, and CUDA performance
was 482.5 ns/day.

### Which conclusions are not justified?

Retention of benzene near the crystallographic pose over 200 ps does not prove
binding affinity, equilibrium occupancy, or a biological mechanism. The
contact frequencies are descriptive for this one short deterministic
trajectory and are not converged probabilities.

### Questions for the human learner

- Why must ligand bond order and formal charge come from the CCD SDF rather
  than from PDB coordinates and `CONECT` records alone?
- Why can a low ligand COM displacement coexist with a larger atom-wise RMSD
  for a symmetric aromatic ligand?

## Phase 3 — teaching — 2026-07-27

### What was simulated?

The validated T4 lysozyme L99A–benzene complex was extended through 700 ps of
staged equilibration and 5 ns of unrestrained NPT production using teaching
seed 20261011.

### What physical model was used?

The ff19SB/OpenFF 2.2.1/OPC model, AM1-BCC ligand charges, 0.15 M salt, and
source-structure preparation policy were unchanged from quick. An independent
preparation reproduced the 44,889-particle system PDB exactly by SHA-256.

### What did each major parameter control?

The teaching profile lengthened production to 2.5 million 2 fs steps and wrote
coordinates every 10 ps, yielding 500 frames. The ligand RMSD threshold
remained 0.80 nm for teaching; it was not bypassed or relaxed.

### Which plots were generated?

The same nine thermodynamic, motion, contact, snapshot, and ligand-identity
figures as quick were regenerated over 5 ns. The local VMD viewer loaded 100
evenly sampled frames from the 500-frame trajectory with separate protein and
BNZ representations.

### What did the plots show directly?

Production averaged 300.36 K and 1.0265 g/mL. Maximum protein Cα RMSD was
0.1193 nm, ligand RMSD 0.2997 nm, and mass-weighted ligand COM displacement
0.1326 nm. The minimum ligand–protein distance was 0.3070 nm and maximum
covalent-bond length was 0.1943 nm. Contact occupancies remained concentrated
in the crystallographic hydrophobic cavity. CUDA performance was 495.7 ns/day.

### Which conclusions are not justified?

Five nanoseconds still do not establish binding free energy, residence time,
equilibrium pose populations, or a biological mechanism. The rapid switching
in atom-wise benzene RMSD is compatible with symmetry-related reorientation
while COM displacement stays small, but that explanation is descriptive and
not a quantified kinetic model.

### Questions for the human learner

- How would a symmetry-corrected ligand RMSD differ from the fixed atom-mapped
  RMSD shown here?
- Which enhanced-sampling or free-energy protocol would be needed to make a
  quantitative binding claim?

## Phase 4 — quick — 2026-07-27

### What was simulated?

The official OPM-oriented bovine AQP1 biological tetramer was embedded in a
homogeneous POPC bilayer. Under approved decision `DR-002`, all 371 source
waters were retained while 12 BNG detergent residues and 2418 OPM dummy
markers were removed. The quick profile produced 200 ps of unrestrained
membrane-NPT production after staged equilibration.

### What physical model was used?

Amber ff19SB described the four 249-residue protein chains, Lipid21 described
448 POPC molecules, and Amber-compatible TIP3P plus 0.15 M NaCl described
solvent and ions. The membrane normal was Z. A Monte Carlo membrane barostat
used isotropic XY and independent Z scaling at 300 K and 1 bar.

### What did each major parameter control?

- Seed 20261110 controlled hydrogen placement, the deterministic CPU membrane
  relaxation, ion selection, and CUDA dynamics.
- The internal membrane builder used CPU with fixed deterministic settings;
  CUDA mixed precision ran minimization, equilibration, and production.
- The unchanged restraint schedule acted on 7,412 protein heavy atoms using a
  periodic-distance expression, avoiding periodic-image artifacts.
- A 0.45 nm cylinder around each transmembrane subunit center provided an
  operational pore-water count. It is a visualization/occupancy definition,
  not a permeation model.

### Which plots were generated?

Thermodynamics, box lengths, XY area, area per lipid, phosphorus-to-phosphorus
thickness, periodically reassembled tetramer Cα RMSD, phosphorus/water Z
density, retained-water occupancy, three protein/lipid/water cross-sections,
and a top view. The HTML viewer reassembles periodic subunit images; the local
VMD viewer loaded 13 sampled frames from the full 145,658-atom DCD and applied
periodic fragment centering.

### What did the plots show directly?

Production averaged 300.29 K. Mean area per lipid was 0.7591 nm² and mean
phosphorus thickness was 3.9751 nm. The two leaflets contained 224 POPC each.
Maximum aligned tetramer Cα RMSD was 0.1160 nm, maximum inter-subunit centroid
distance change was 0.0712 nm, and maximum covalent-bond length was 0.1950 nm.
There were on average 196.13 retained source waters in the OPM hydrophobic
core and 27.65 in the four operational pore cylinders. Cross-sections showed
continuous leaflets and hydrated outer slabs without a visible vacuum gap.
CUDA production performance was 160.0 ns/day.

### Which conclusions are not justified?

The 200 ps trajectory validates construction and file/analysis integrity. It
does not establish membrane equilibration, area-per-lipid convergence, AQP1
water permeability, a conduction rate, or a biological transport mechanism.
The operational pore counts are descriptive and cannot be interpreted as
transport events.

### Questions for the human learner

- Why must a noncovalent tetramer be reassembled across periodic images before
  computing RMSD or presenting an interactive trajectory?
- Why can a continuous water-density profile support a no-vacuum construction
  check without establishing an equilibrated membrane?

## Phase 4 — teaching — 2026-07-27

### What was simulated?

An independent teaching-seed preparation of the approved OPM AQP1 tetramer
produced a 145,628-particle POPC/TIP3P/0.15 M NaCl system. It retained all 371
source waters, contained 448 POPC molecules split 224/224 between leaflets,
and ran 5 ns of unrestrained membrane-NPT production after 1.6 ns of staged
equilibration.

### What physical model was used?

The ff19SB/Lipid21/TIP3P model, 300 K/1 bar conditions, membrane-specific
barostat, 2 fs timestep, HBond constraints, 1.0 nm cutoff, and restraint
schedule were unchanged from quick. Teaching seed 20261111 controlled the
independent preparation and dynamics.

### What did each major parameter control?

The longer profile used 100 ps NVT, three 500 ps restrained NPT stages, and
2.5 million production steps. Coordinates were stored every 10 ps for 500
frames. The operational 0.45 nm pore cylinders tracked water identity and
occupancy but did not define permeation events.

### Which plots were generated?

The same ten thermodynamic, box, membrane, protein, water-identity, density,
cross-section, and top-view figures as quick were generated over 5 ns. The
HTML and VMD viewers each used 13 evenly sampled, periodically reassembled
frames; VMD read the full 145,628-atom topology and DCD.

### What did the plots show directly?

Production averaged 300.28 K. Mean area per lipid was 0.7756 nm² and mean
phosphorus thickness was 3.9092 nm. Maximum tetramer Cα RMSD after periodic
reassembly/alignment was 0.1773 nm; maximum inter-subunit centroid-distance
change was 0.0888 nm; maximum covalent bond was 0.1947 nm. Both outer solvent
slabs remained populated and the time-averaged outer water density had no
empty bin. Retained-source core-water count decreased over the trajectory
while total operational pore-cylinder occupancy averaged 76.55 waters,
showing source-water identity exchange. CUDA performance was 187.8 ns/day.

### Which conclusions are not justified?

Five nanoseconds and one teaching realization do not establish POPC
equilibration, converged AQP1 dynamics, water permeability, transport
kinetics, or a biological mechanism. The decrease in source-water identity is
not itself a crossing count, because individual periodic trajectories and pore
entry/exit events were not defined or statistically analyzed.

### Questions for the human learner

- Why does tracking water identity answer a different question from measuring
  instantaneous pore occupancy?
- What trajectory unwrapping, event definition, replicas, and uncertainty
  estimates would be required before reporting a water permeation rate?

## Phase 5 — quick — 2026-07-27

### What was simulated?

The approved matched inactive 5-HT2A–BRIL pair was prepared from 7WC6/LSD and
7WC7/lisuride. Each condition contained the same 367-residue engineered
construct, modeled ICL2 residues 181–187, the modeled BRIL linker 1061–1065,
484 POPC molecules, TIP3P water and 0.15 M NaCl. The quick profile produced
200 ps of unrestrained production after restrained minimization, NVT, four
decreasing-restraint membrane-NPT stages and unrestrained preproduction.

### What physical model was used?

Amber ff19SB described receptor/BRIL, Lipid21 described POPC, and OpenFF Sage
2.2.1 with AmberTools AM1-BCC described the approved `+1` ligand microstates.
Both systems used PME, a 1.0 nm cutoff, HBond constraints, a 2 fs timestep,
310 K and a semi-isotropic 1 bar membrane barostat. Both experimental
structures were aligned independently to the same OPM 7WC5 transmembrane
reference.

### What did each major parameter control?

- The common loop seed built the same approved ICL2 conformer block in both
  conditions.
- A deterministic single-thread local minimization repaired modeled-region
  stereochemistry/clashes while restraining every other heavy atom at
  10000 kJ mol-1 nm-2.
- The production restraint schedule acted on protein and ligand heavy atoms,
  then released them completely for preproduction and production.
- The 0.45 nm primary contact cutoff and 0.35 nm D155 diagnostic cutoff were
  pre-registered before trajectory analysis and were not adjusted.

### Which plots and viewers were generated?

Each condition generated thermodynamic/RMSD dashboards, contact-distance
plots, membrane area/thickness plots and a final cross-section. Both 13-frame
3Dmol HTML viewers rendered successfully in headless Chrome. VMD 2.0.0a4
loaded the full 209,812-atom LSD and 208,597-atom lisuride systems and all 13
sampled frames with protein, ligand, contact-residue and membrane
representations.

### What did the plots show directly?

Mean temperatures were 310.40 K for LSD and 310.28 K for lisuride. Mean areas
per lipid were 0.6789 and 0.6857 nm²; mean phosphorus thicknesses were 3.8092
and 3.7862 nm. Maximum transmembrane Cα RMSD was 0.0695/0.0836 nm, maximum
aligned ligand RMSD 0.1638/0.1663 nm, and maximum covalent bond
0.2157/0.2136 nm. The cationic ligand nitrogen remained within 0.35 nm of
D155 in every stored frame. The short-run ECL2 contact occupancy was 1.0 for
both conditions; deep-contact occupancy was 1.0 for LSD and 0.86 for
lisuride. CUDA performance was 117.7–120.0 ns/day.

### Which conclusions are not justified?

The 200 ps quick trajectories establish mechanical construction,
parameterization, checkpoint, visualization and analysis integrity only. They
do not establish equilibration, convergence, differential-contact
reproducibility, receptor activation, signaling bias, psychedelic action or a
biological mechanism. The pre-registered directional hypothesis remains
reserved for independent research replicas stratified by ICL2 conformer.

### Questions for the human learner

- Why must a noncovalently bound ligand be moved to the receptor's nearest
  periodic image before aligned RMSD and contact calculations?
- Which aspects of the Phase 5 teaching run can support a production-readiness
  gate without supporting the research hypothesis itself?

## Phase 5 — teaching — 2026-07-27

### What was simulated?

The approved matched inactive 5-HT2A–BRIL pair was rebuilt independently for
the teaching profile. The LSD/7WC6 system contained 214,179 particles, 484
POPC and 47,719 waters; the lisuride/7WC7 system contained 211,869 particles,
482 POPC and 47,039 waters. Each completed 100 ps NVT, four 500 ps
decreasing-restraint membrane-NPT stages, 500 ps unrestrained preproduction,
and 5 ns unrestrained production.

### What physical model was used?

The approved ff19SB/Lipid21/TIP3P/OpenFF 2.2.1 AM1-BCC Hamiltonian, ligand
formal charges of +1, 310 K, 1 bar membrane coupling, PME, 1.0 nm cutoff,
HBond constraints, 2 fs timestep and pH 7.4 protonation assumptions were
unchanged from quick. Serialized-system inspection found zero virtual sites
and an effective `NonbondedForce` ligand charge of exactly +1 e in both
systems.

### Which plots and viewers were generated?

Each condition generated a production temperature/energy/RMSD dashboard,
pre-registered contact distances, membrane area/thickness traces and a final
receptor/ligand/membrane cross-section. The 3Dmol HTML viewers rendered in
Chrome with 13 sampled frames and an adjusted ligand-centered zoom that shows
the complete receptor. VMD 2.0.0a4 loaded 13 sampled frames from each full DCD
with 214,179 LSD-system atoms and 211,869 lisuride-system atoms.

### What did the generated data show directly?

Mean temperatures were 310.28 K for LSD and 310.35 K for lisuride. Mean area
per lipid was 0.6647/0.6726 nm² and mean phosphorus thickness was
3.9132/3.8684 nm. Maximum transmembrane C-alpha RMSD was 0.0916/0.0877 nm;
maximum aligned ligand RMSD was 0.1405/0.1372 nm. The D155 anchor was present
in every stored frame. Short-run ECL2 contact occupancy was 0.988/0.996 and
deep-contact occupancy was 0.994/0.998. Both leaflets remained balanced and
the outer solvent slabs stayed populated. CUDA production performance was
119.18/118.58 ns/day. All 23 mandatory checks passed for each condition.

The area-per-lipid traces decreased and the P-P thickness traces increased
over the 5 ns window. They remained inside the mechanical gate, but these
trends are evidence that a convergence claim would be inappropriate.

### What implementation issue was found?

The OpenMM reporter received a relative segment length where its ETA field
expects an absolute final step. The displayed remaining time wrapped after the
global step exceeded that value, while `simulation.step`, the 500 frames,
physical time, checkpoints and forces remained correct. Future reporters now
use `simulation.currentStep + segment_steps`; the active run's display-only
issue is documented in `analysis/TELEMETRY_NOTE.md`.

### Which conclusions are not justified?

One 5 ns teaching realization per ligand does not establish membrane
equilibration, convergence, reproducible differential contacts, activation,
signaling bias, psychedelic action or any biological mechanism. In
particular, the teaching contact differences are far below the pre-registered
0.20 research effect threshold and cannot be pooled as research replicas.

### Questions for the human learner

- Why can every mechanical gate pass while the membrane traces still prevent
  a convergence claim?
- Why must the six planned research trajectories be analyzed as independent
  replicas and stratified by ICL2 conformer rather than extending this
  teaching trajectory?
