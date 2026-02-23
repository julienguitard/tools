.PHONY: setup run dry-run clean

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
	@echo "Done. Edit .env with your OPENAI_API_KEY, then:"
	@echo "  make dry-run FOLDER=/path/to/papers"
	@echo "  make run     FOLDER=/path/to/papers"

# -- Run ------------------------------------------------------------------

FOLDER ?= .

dry-run: setup
	@set -a && . ./.env && set +a && \
	$(PYTHON) -m rename_papers $(FOLDER) --dry-run

run: setup
	@set -a && . ./.env && set +a && \
	$(PYTHON) -m rename_papers $(FOLDER)

# -- Housekeeping ---------------------------------------------------------

clean:
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} +
