# 5-HT2A campaign GUI — reference snapshot

This directory is **not** a runnable application. It is a read-only snapshot of a
few files from the 5-HT2A MD operator interface, which lives in its own git
repository (remote `tjdmrtz/htr2a-risperidone-md`, checked out in this workspace as
the ignored `../5ht2a_md/` directory) and has its own
`gui/README.md`, backend, frontend, and test suite.

It is kept here so that the MD laboratory can read the campaign's MD vocabulary
and viewer code without cloning the campaign repository. Nothing in this directory
is imported by `scripts/`, `src/mdlab/`, `tests/`, or the root `Makefile`.

## Tracked snapshot files

| File | Content |
|---|---|
| `backend/glossary.py` | `GLOSSARY`: 15 plain-language definitions for campaign terms (stage, replica, segment, lineage, branch, gate, plateau, autocorrelation time, effective samples, area per lipid, ionic lock, site sodium, barostat, offload, reap) |
| `frontend/js/charts.js` | one helper: `initChart()` over `Plotly.newPlot`, static plot mode when the user prefers reduced motion |
| `frontend/js/export.js` | export panel; calls `/api/analysis/report` and reads `/api/errors` |
| `frontend/js/glossary.js` | renders the `#glossary` panel. In this snapshot it imports a sibling `./glossary.js` data module that is not included, so it is a fragment, not a working module |
| `frontend/js/runview.js` | run view; polls `/api/jobs` and `/api/evidence` and opens the `/api/events` event stream |
| `tests/contract/test_report_bundle.py` | contract test for `POST /api/analysis/report` |

The snapshot is a subset and drifts from its source; the campaign repository is
authoritative for every one of these files.

## Running the real interface

Run it from the campaign repository root, with that repository on `PYTHONPATH`,
using the Anaconda `base` environment (FastAPI/uvicorn). Do not install FastAPI or
uvicorn into this repository's `.venv/conda`; that environment is pinned for the
OpenMM stack:

```bash
cd <path-to>/5ht2a_md
PYTHONPATH=$PWD uvicorn gui.backend.main:app --reload
# then open http://127.0.0.1:8000/
```

The campaign's own test entry point (from its repository root) is:

```bash
PYTHONPATH=$PWD python -m pytest gui/tests/unit gui/tests/contract gui/tests/integration -q --tb=short
```

`gui/tests/contract/test_report_bundle.py` in this snapshot imports
`gui.backend.config`, `gui.backend.jobs`, and `gui.backend.main`, which exist only
in that tree, so it can only run with `PYTHONPATH` set to the campaign repository.
Killing the interface does not kill a simulation: campaign runs are launched
detached and re-attached on the next start (`5ht2a_md/gui/README.md` is the
authoritative run/test guide, including the browser-test suite).
