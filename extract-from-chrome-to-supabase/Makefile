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
	@echo "Done. Edit .env with your keys, then:"
	@echo "  make run"

# -- Run ------------------------------------------------------------------

run: setup
	@set -a && . ./.env && set +a && \
	$(PYTHON) -m extract_from_chrome_to_supabase

# -- Housekeeping ---------------------------------------------------------

clean:
	rm -rf $(VENV)
	find . -type d -name __pycache__ -exec rm -rf {} +
