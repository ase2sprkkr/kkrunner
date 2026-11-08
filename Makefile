PYTHON ?= python
SPHINXOPTS ?= -W --keep-going

.PHONY: docs docs-test

docs:
	$(PYTHON) -m sphinx -M html docs build/docs $(SPHINXOPTS)

docs-test:
	$(PYTHON) -m sphinx -M doctest docs build/docs $(SPHINXOPTS)
