.PHONY: setup run dry-run clean

SQL_ROOT ?= ../../src/databases/tables

# -- Setup ----------------------------------------------------------------

setup:
	@echo "No dependencies — stdlib only."
	@test -f ./.env || cp ./.env.example ./.env

# -- Run ------------------------------------------------------------------

run: setup
	python3 -m generate_data_diagram --sql-root $(SQL_ROOT)

dry-run: setup
	python3 -m generate_data_diagram --sql-root $(SQL_ROOT) --dry-run

# -- Housekeeping ---------------------------------------------------------

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
