Phase P06 complete

Files created/changed:
- gui/backend/analysis.py: plot_argv() extracted; plateau JSON resolved via PROJ/SYSTEM_ID + reconstruct_lineage (no hardcoded paths); analysis_argv honors stage, no "18_run_production" as argv[0]
- gui/backend/routes/analysis.py: run_plots calls plot_argv(...); runner.launch with extra_env; HTTP 202
- gui/tests/contract/test_plots_invoke_scripts.py: deleted restore(); uses monkeypatch.setattr; calls plot_argv() only (no POST/JobRunner)
- HOW_TO_IMPLEMENT.md: §18 P06 completion entry

Test results:
- 124 passed, 0 failed (unit + contract + integration)
- All P06 verification checks pass