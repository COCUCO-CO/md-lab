# Book ingestion policy

Books are useful for coherent explanations but are usually the highest-risk
copyright source in the project. Buying or possessing a PDF does not grant the
right to use it for training or retrieval.

For every requested book, record:

- exact title, authors, edition, year and ISBN;
- source of the local copy;
- rightsholder and license;
- whether the license explicitly covers ML training, local RAG, redistribution
  and derived adapter weights;
- written permission or license evidence URL;
- SHA-256 of the exact edition;
- allowed purpose: retrieval, training, evaluation or none;
- required attribution and deletion/expiry conditions.

Commercial textbooks in `configs/books.toml` are a desired-content list only.
They remain disabled. A rights-approved book should be added to
`configs/sources.toml` as a new, immutable edition-specific source before its
file is registered.

Open licenses still require review for additional terms. For example, the
current OpenStax Chemistry 2e page combines a Creative Commons license with an
explicit prohibition on LLM ingestion without permission, so this project does
not ingest it.

When permission is unavailable, use the book only as a human reading list and
replace its role with compatible primary literature, official software manuals
or original project-authored teaching material.

