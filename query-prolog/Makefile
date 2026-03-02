.PHONY: setup run clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# -- Setup ----------------------------------------------------------------

setup: $(VENV)/bin/activate

$(VENV)/bin/activate: requirements.txt
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@test -f .env || cp .env.example .env
	@echo ""
	@echo "Done. Edit .env with your AI keys (optional), then:"
	@echo "  make run FILE=family.pl"

# -- Run ------------------------------------------------------------------

FILE ?= family.pl

run: setup
	@set -a && . ../.env && set +a && \
	$(PYTHON) -m query_prolog $(FILE)

# -- Housekeeping ---------------------------------------------------------

clean:
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} +
