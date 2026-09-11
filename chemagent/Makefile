SHELL := /bin/bash
PYTHON ?= $(if $(wildcard ../.venv/conda/bin/python),../.venv/conda/bin/python,python3)
export PYTHONPATH := $(CURDIR)/src

.PHONY: help validate audit test preflight preflight-training build-example-index search-example

help:
	@echo "Targets:"
	@echo "  make validate             Validate model, source, book and policy registries"
	@echo "  make audit                Print the source and book permission audit"
	@echo "  make test                 Run dependency-free unit tests"
	@echo "  make preflight            Run the offline governance preflight"
	@echo "  make preflight-training   Check GPUs and optional training dependencies"
	@echo "  make build-example-index  Build the tiny, non-training example RAG index"
	@echo "  make search-example       Query the example RAG index"

validate:
	$(PYTHON) -m chemagent.cli validate-config

audit:
	$(PYTHON) -m chemagent.cli audit

test:
	$(PYTHON) -m unittest discover -s tests -v

preflight:
	$(PYTHON) -m chemagent.cli preflight --level governance

preflight-training:
	$(PYTHON) -m chemagent.cli preflight --level training

build-example-index: data/indexes/example.sqlite

data/indexes/example.sqlite: examples/retrieval_documents.jsonl
	$(PYTHON) -m chemagent.cli build-index --input examples/retrieval_documents.jsonl --output data/indexes/example.sqlite

search-example:
	$(PYTHON) -m chemagent.cli search --index data/indexes/example.sqlite --query "molecular dynamics evidence"
