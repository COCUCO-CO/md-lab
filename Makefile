SHELL := /bin/bash
ROOT := $(CURDIR)
MAMBA := $(shell command -v micromamba 2>/dev/null || echo $(ROOT)/.tools/micromamba)
ENV_PREFIX := $(ROOT)/.venv/conda
RUN := $(MAMBA) run -p $(ENV_PREFIX)
PROFILE ?= quick

.PHONY: help bootstrap doctor status test phase1 phase1-analysis phase1-view phase2 phase2-analysis phase2-view phase3 phase3-analysis phase3-view phase4 phase4-analysis phase4-view phase5 phase5-analysis phase5-view

help:
	@echo "Targets:"
	@echo "  make bootstrap"
	@echo "  make doctor"
	@echo "  make status"
	@echo "  make test"
	@echo "  make phase1 PROFILE=quick|teaching"
	@echo "  make phase1-analysis PROFILE=quick|teaching"
	@echo "  make phase1-view PROFILE=quick|teaching"
	@echo "  make phase2 ... phase5 with the same suffix pattern"
	@echo "Never run teaching before the quick gate passes."

bootstrap:
	bash scripts/bootstrap.sh

doctor:
	$(RUN) python scripts/doctor.py

status:
	$(RUN) python scripts/labctl.py status

test:
	$(RUN) pytest -q

phase1:
	$(RUN) python scripts/phase1_run.py --profile $(PROFILE)

phase1-analysis:
	$(RUN) python scripts/phase1_analyze.py --profile $(PROFILE)
	$(RUN) python scripts/labctl.py complete 1 $(PROFILE)

phase1-view:
	$(RUN) python scripts/render_trajectory.py --phase 1 --profile $(PROFILE)

phase2:
	$(RUN) python scripts/phase2_run.py --profile $(PROFILE)

phase2-analysis:
	$(RUN) python scripts/phase2_analyze.py --profile $(PROFILE)
	$(RUN) python scripts/labctl.py complete 2 $(PROFILE)

phase2-view:
	$(RUN) python scripts/render_trajectory.py --phase 2 --profile $(PROFILE)

phase3:
	$(RUN) python scripts/phase3_run.py --profile $(PROFILE)

phase3-analysis:
	$(RUN) python scripts/phase3_analyze.py --profile $(PROFILE)
	$(RUN) python scripts/labctl.py complete 3 $(PROFILE)

phase3-view:
	$(RUN) python scripts/render_trajectory.py --phase 3 --profile $(PROFILE)

phase4:
	$(RUN) python scripts/phase4_run.py --profile $(PROFILE)

phase4-analysis:
	$(RUN) python scripts/phase4_analyze.py --profile $(PROFILE)
	$(RUN) python scripts/labctl.py complete 4 $(PROFILE)

phase4-view:
	$(RUN) python scripts/render_trajectory.py --phase 4 --profile $(PROFILE)

phase5:
	$(RUN) python scripts/phase5_run.py --profile $(PROFILE)

phase5-analysis:
	$(RUN) python scripts/phase5_analyze.py --profile $(PROFILE)
	$(RUN) python scripts/labctl.py complete 5 $(PROFILE)
	@if [ "$(PROFILE)" = "teaching" ]; then \
		$(RUN) python scripts/labctl.py set 5 teaching AWAITING_HUMAN_DECISION; \
	fi

phase5-view:
	$(RUN) python scripts/render_trajectory.py --phase 5 --profile $(PROFILE)
