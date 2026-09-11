# Phases 6 and 7 — Replicas, statistics, enhanced sampling, and ML

These phases currently define scientific requirements but do not yet have
runnable Makefile targets or implementation scripts. Phase 6 begins only after
the approved Phase 5 research replicas are complete. Phase 7 begins only after
Phase 6 identifies a specific slow coordinate or sampling limitation.

## Phase 6: ensemble reasoning

### Unit of evidence

A trajectory frame is not an independent replicate. The primary units are independent simulations or independent experimental systems. Time correlation reduces effective sample size.

### Required workflow

1. run at least three independent replicas;
2. analyze each replica separately before pooling;
3. plot every time series by replica;
4. estimate autocorrelation time where feasible;
5. report effective sample size;
6. compare distributions, not only means;
7. use block averaging or bootstrap at the trajectory-block/replica level;
8. disclose failed or excluded replicas with reasons;
9. evaluate sensitivity to alignment, cutoff, and analysis definition;
10. avoid selecting only the “best-looking” trajectory.

### Convergence diagnostics

No single convergence test is definitive. Use multiple views:

- cumulative means and confidence intervals;
- first-half vs second-half distributions;
- replica overlap in chosen collective variables;
- implied timescales for Markov models;
- stationarity checks;
- cluster/state occupancy by replica;
- transition counts and connectivity.

### Reporting uncertainty

State whether uncertainty reflects frame variability, block variability, or between-replica variability. Between-replica uncertainty is generally the most relevant for reproducibility.

## Phase 7: advanced sampling

Enhanced sampling is introduced only after a conventional baseline is validated and a specific slow coordinate/problem is identified.

Possible methods:

- umbrella sampling for a defined reaction coordinate;
- metadynamics for selected collective variables;
- replica exchange for temperature/Hamiltonian exploration;
- weighted ensemble for rare transitions;
- alchemical free energy for relative/absolute binding questions.

Each method requires method-specific convergence and bias-reweighting checks. Do not infer free energies from raw biased histograms.

## TICA and Markov state models

A valid MSM workflow includes:

- feature definition justified physically;
- train/validation split by trajectories, not random frames;
- TICA lag-time sensitivity;
- clustering sensitivity;
- implied-timescale plots;
- Chapman–Kolmogorov validation where applicable;
- connected-state handling;
- uncertainty across replicas/bootstrap samples.

## Machine learning integration

For graph autoencoders, latent ODEs, or neural dynamics:

1. define atom/residue representation and units;
2. preserve periodic/angular geometry correctly;
3. split by trajectory/replica/ligand to prevent leakage;
4. compare against simple baselines such as PCA/TICA;
5. reconstruct physically meaningful observables, not only latent loss;
6. report out-of-distribution behavior;
7. do not treat generated trajectories as force-field MD unless they obey a validated dynamical model;
8. validate kinetic quantities separately from structural reconstruction.

For the user's 5-HT2A graph-VAE work, the MD pipeline should export immutable topology, frame times, replica labels, ligand labels, and preprocessing hashes so ML datasets remain traceable to physical simulations.
