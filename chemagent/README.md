# Chemistry Research Agent

This subproject builds a local, evidence-grounded chemistry research assistant
around open-weight models. The first supported training target is
`OpenDFM/ChemDFM-R-14B` with two-GPU 4-bit QLoRA. The language model is an
orchestrator, not a replacement for reaction validation, electronic-structure
codes, molecular dynamics, property models or expert review.

Repository code follows the root MIT license. ChemDFM-R-14B and derived adapter
distribution remain subject to the checkpoint's AGPL-3.0 license and the
licenses/attribution obligations of every training source.

The repository currently implements the safe foundation needed before any
large download or GPU run:

- source and book registries with explicit training/RAG permissions;
- immutable local-file manifests with SHA-256 and license evidence;
- a strict, provenance-aware SFT record format;
- deterministic grouped pilot splits and contamination checks;
- a local SQLite FTS5 retrieval index;
- a real QLoRA training entry point with a required immutable model revision;
- offline and GPU/dependency preflights;
- tests for licensing, safety tags, manifests, splits and retrieval.

It deliberately does **not** download datasets, books or model weights by
default. Access is not permission, and a rolling model revision is not a
reproducible training input.

## Architecture

```text
question
   |
   v
ChemDFM-R-14B + QLoRA adapter
   |-- cited retrieval: papers, patents, databases, licensed books
   |-- chemistry: RDKit, RXNMapper, RetroDFM, AiZynthFinder
   |-- quantum: PySCF, Psi4, CP2K, Quantum ESPRESSO
   |-- simulation: OpenMM, GROMACS, LAMMPS
   `-- property/hazard models and structured databases
                     |
                     v
       evidence, calculations, uncertainty, abstention
```

Numerical arrays such as forces, orbitals and trajectories stay in structured
stores. The LLM learns tool selection, scientific interpretation and citation;
it must not fabricate numerical outputs.

## Quick start: no downloads or GPU needed

```bash
cd chemagent
make validate
make audit
make test
make preflight
make build-example-index
make search-example
```

The example index contains only tiny project-authored descriptions. It is not a
training corpus.

## Registering a legally usable local artifact

First approve the exact source in `configs/sources.toml`. Then:

```bash
PYTHONPATH=src python -m chemagent.cli register-local \
  --file /absolute/path/to/artifact \
  --source-id ord \
  --purpose training \
  --license CC-BY-SA-4.0 \
  --license-evidence https://github.com/Open-Reaction-Database/ord-data
```

This writes only a manifest under `data/manifests/`; it does not modify or copy
the original file. Every later stage is expected to reference that manifest.

## Curated SFT record

Input to `build-sft` is JSONL. Each line has this contract:

```json
{
  "record_id": "ord:dataset-id:reaction-id:task-v1",
  "task": "reaction_condition_extraction",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "source_ids": ["ord"],
  "license": "CC-BY-SA-4.0",
  "license_evidence": "https://github.com/Open-Reaction-Database/ord-data",
  "evidence": ["ORD dataset and reaction identifiers"],
  "attribution": "Open Reaction Database contributors",
  "split_group": "complete-document-or-reaction-family-id",
  "split": "train",
  "observation_kind": "extracted",
  "procedural": false,
  "safety_tags": []
}
```

`split` may be `train`, `validation` or `test`. If omitted, the pilot builder
uses a deterministic hash of `split_group`, so related records cannot cross
splits. Production evaluation must instead use the temporal, patent-family,
scaffold and target-series policies described in `docs/CORPUS_PLAN.md`.

```bash
PYTHONPATH=src python -m chemagent.cli build-sft \
  --input data/staged/records.jsonl \
  --output data/curated/sft
```

The builder refuses benchmark-only sources, unapproved licenses, absent
evidence, unsafe procedural records, duplicate IDs and split-group leakage.

## QLoRA pilot

1. Review the immutable Hugging Face commit already pinned in
   `configs/models/chemdfm_r_14b_qlora.toml`; update it only through a recorded
   model-adoption decision.
2. Build 25,000-50,000 audited pilot records.
3. Create a dedicated environment and install this package with its training
   dependencies: `python -m pip install -e '.[train,test]'`.
4. Run `make preflight-training`.
5. Launch from this directory:

```bash
PYTHONPATH=src accelerate launch --num_processes 2 \
  -m chemagent.train_qlora \
  --model-config configs/models/chemdfm_r_14b_qlora.toml \
  --training-config configs/training/pilot.toml
```

Training refuses an unpinned model, absent dataset files, a dirty output
directory or a dataset below the pilot gate. It writes a run manifest before
loading model weights.

## Books

`configs/books.toml` contains the initial desired advanced reading list. Those
commercial books are disabled until written permission covers the intended
training or retrieval use. OpenStax Chemistry 2e is also disabled because its
current publisher page explicitly prohibits ingestion into LLMs without
permission.

To add a book, supply its exact title, authors, edition, ISBN, intended use and
license or written permission. See `docs/BOOKS.md`.

## Scope

The domain map includes organic and medicinal chemistry, physical and quantum
chemistry, statistical mechanics, molecular dynamics, biochemistry, chemical
biology, inorganic/organometallic chemistry, catalysis, electrochemistry,
materials, polymers, spectroscopy, analytical chemistry, safety and metrology.
Breadth is provided through retrieval and tools; only high-value behaviours and
representations belong in QLoRA.

Read next:

- `docs/ARCHITECTURE.md`
- `docs/CORPUS_PLAN.md`
- `docs/BOOKS.md`
- `docs/EVALUATION.md`
- `docs/ROADMAP.md`
- `docs/STATUS.md`
