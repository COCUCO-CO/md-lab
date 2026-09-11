# 5-HT2A MD GUI
Use Anaconda base (FastAPI/uvicorn). Do not use the repo .venv/conda (MD only).
Start: cd 5ht2a_md/gui && PYTHONPATH=/home/tomas/PycharmProjects/md-lab/5ht2a_md uvicorn gui.backend.main:app --reload
Test: cd /home/tomas/PycharmProjects/md-lab && PYTHONPATH=/home/tomas/PycharmProjects/md-lab/5ht2a_md python -m pytest 5ht2a_md/gui/tests/unit 5ht2a_md/gui/tests/contract 5ht2a_md/gui/tests/integration -q --tb=short
Killing the GUI does not kill simulations.