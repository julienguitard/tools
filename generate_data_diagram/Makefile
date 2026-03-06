.PHONY: run dry-run clean

SQL_ROOT ?= ../../src/databases/tables

# -- Run ------------------------------------------------------------------

run:
	python3 generate_data_diagram/generate.py --sql-root $(SQL_ROOT)

dry-run:
	python3 generate_data_diagram/generate.py --sql-root $(SQL_ROOT) --dry-run

# -- Housekeeping ---------------------------------------------------------

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
