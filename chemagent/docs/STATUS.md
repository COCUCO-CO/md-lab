# Implementation status — 2026-08-29

## Completed

- isolated subproject created without changing the MD laboratory state;
- ChemDFM-R-14B pinned to Hugging Face revision
  `d428014430af2a303687b1cd33c073d84bd20f0b`;
- two-GPU NF4/BF16 QLoRA configuration and executable trainer;
- source, book, license, safety and benchmark registries;
- immutable local artifact manifest command;
- provenance-gated SFT builder with grouped splits;
- SQLite FTS5 retrieval baseline and grounded prompt construction;
- quantum chemistry, materials, retrosynthesis and MD tool catalogue;
- corpus, evaluation, book and architecture documentation;
- nine offline tests and Ruff validation passing.

## Observed environment state

- governance preflight: PASS;
- Python: 3.12.13 in the repository environment;
- free filesystem space visible to the preflight: 393.9 GiB;
- CUDA device access is not visible from the current sandbox;
- Torch is present; Accelerate, BitsAndBytes, Datasets, PEFT, Safetensors and
  Transformers are not installed in the selected environment;
- the curated 25k-50k pilot dataset has not been built;
- no model weights or external corpora have been downloaded.

## Next controlled milestone

1. Confirm exact book editions and training/RAG rights.
2. Confirm that the real host shell exposes both RTX 3090 cards.
3. Install optional training packages in a dedicated environment without
   changing the system CUDA installation.
4. Implement and test the ORD, USPTO-Lowe, Rhea and SMolInstruct adapters.
5. Download only versioned pilot slices, recording checksum and license
   evidence; do not attempt the full OC25 or literature corpus initially.
6. Build a balanced 25k-50k pilot and establish untouched-base metrics.
7. Download the pinned 29.6 GB checkpoint and run a 100-step memory/throughput
   smoke test before a full epoch.

The current blockers are intentional scientific and reproducibility gates, not
failed implementation steps.

