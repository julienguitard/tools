.PHONY: setup run clean

# -- Setup ----------------------------------------------------------------

setup:
	@echo "No dependencies — stdlib only."
	@test -f ./.env || cp ./.env.example ./.env

# -- Run ------------------------------------------------------------------

run:
	python3 -m play_with_lambda

# -- Housekeeping ---------------------------------------------------------

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
