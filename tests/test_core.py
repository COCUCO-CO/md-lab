from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import mdlab.core
from mdlab.core import download, load_profiles, resolve_config
from mdlab.openmm_utils import interval_steps, steps_for_ps


def test_profiles_have_all_tutorial_phases():
    profiles = load_profiles()
    for phase in range(1, 6):
        assert f"phase{phase}" in profiles


def test_time_step_conversion():
    assert steps_for_ps(1.0, 2.0) == 500
    assert interval_steps(10.0, 2.0) == 5000


def test_phase2_quick_resolution():
    cfg = resolve_config(2, "quick")
    assert cfg["pdb_id"] == "1UBQ"
    assert cfg["seed"] == 20260910
    assert cfg["production_ps"] == 100.0


def test_scientific_versions_are_explicit():
    text = (ROOT / "environment.yml").read_text()
    assert "openmm=8.5.2" in text
    assert "openmmforcefields=0.16.0" in text
    assert "openff-toolkit=0.18.1" in text


def test_download_reuses_verified_immutable_input(tmp_path, monkeypatch):
    class Response:
        content = b"immutable structure"

        @staticmethod
        def raise_for_status():
            return None

    calls = 0

    def first_get(url, timeout):
        nonlocal calls
        calls += 1
        return Response()

    monkeypatch.setattr(mdlab.core, "ROOT", tmp_path)
    monkeypatch.setattr("requests.get", first_get)
    destination = tmp_path / "inputs" / "structure.pdb"

    first = download("https://example.test/structure.pdb", destination)
    second = download("https://example.test/structure.pdb", destination)

    assert calls == 1
    assert first == second
    assert destination.read_bytes() == Response.content
