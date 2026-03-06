# Root Makefile — sets up all tools in the monorepo
#
# Tools with a venv (have requirements.txt):
VENV_TOOLS := rename-papers extract-from-chrome-to-supabase query-prolog
# Stdlib-only tools (no venv needed):
ALL_TOOLS := $(VENV_TOOLS) generate_data_diagram

.PHONY: setup clean $(ALL_TOOLS)

# -- Setup ----------------------------------------------------------------

setup: $(VENV_TOOLS)

$(VENV_TOOLS):
	@echo "── Setting up $@ ──"
	$(MAKE) -C $@ setup

# -- Housekeeping ---------------------------------------------------------

clean:
	@for tool in $(ALL_TOOLS); do \
		echo "── Cleaning $$tool ──"; \
		$(MAKE) -C $$tool clean; \
	done
