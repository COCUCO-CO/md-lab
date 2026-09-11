# Roadmap

## M0 — Governance and local skeleton (implemented)

Success: configuration audit and unit tests pass; no network access is required;
unlicensed books, per-record sources and benchmarks are rejected by default.

## M1 — Source adapters

Implement one source at a time: ORD, USPTO-Lowe, Rhea, ChEBI, ChEMBL, SPICE and
OC25. Each adapter needs fixture tests, release/checksum manifests, native-unit
preservation, deterministic normalization and a license evidence snapshot.

## M2 — Retrieval pilot

Index a small licensed corpus. Evaluate citation recall and source support
before adding embeddings. Add PostgreSQL/RDKit only after the transparent
SQLite baseline is measured.

## M3 — 25k-50k QLoRA pilot

Pin the model commit, build leakage-free splits, record base-model metrics,
train one epoch, and compare. Stop if chemistry or general reasoning regresses.

## M4 — Scientific tool agent

Add typed, sandboxed adapters for RDKit/RXNMapper, retrosynthesis, PySCF/Psi4,
OpenMM/GROMACS and analysis. Every tool call records exact inputs, versions,
units, outputs and failure state. Mutating scientific decisions require human
approval.

## M5 — Full corpus and preference training

Scale only sources that improved held-out results. Build verified preference
pairs for citation, error detection and abstention. Avoid online RL until the
offline evaluation and two-GPU cost are understood.

## M6 — Research release

Publish model/data cards, license obligations, excluded sources, benchmark
results, safety evaluation, known failure modes and reproducible run manifests.

