def test_report_confirm_launches_202(tmp_path, monkeypatch) -> None:
    from pathlib import Path
    from fastapi.testclient import TestClient
    from gui.backend import config
    from gui.backend.jobs import JobRunner
    from gui.backend.main import app

    (tmp_path / "systems" / "test_system").mkdir(parents=True)
    (tmp_path / "scripts").mkdir(parents=True)
    (tmp_path / "scripts" / "28_bundle_report.py").write_text("#\n")
    monkeypatch.setattr(config, "PROJ", tmp_path)

    called: dict = {}

    def mock_launch(self, job_id, argv, **kwargs):
        called["job_id"] = job_id
        called["argv"] = argv
        called["kind"] = kwargs.get("kind")
        called["extra_env"] = kwargs.get("extra_env")
        return {"job_id": job_id, "state": "running"}

    monkeypatch.setattr(JobRunner, "launch", mock_launch)
    r = TestClient(app).post(
        "/api/analysis/report",
        json={"confirm": True, "system_id": "test_system"},
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["job_id"] == "report_test_system"
    assert "--system-dir" in body["argv"]
    assert Path(body["argv"][body["argv"].index("--system-dir") + 1]).name == "test_system"
    assert called["kind"] == "analysis"
    assert called["extra_env"] == {"MPLBACKEND": "Agg", "LC_NUMERIC": "C"}