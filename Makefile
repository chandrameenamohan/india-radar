.PHONY: check lint typecheck unit e2e clean

VENV := .venv
PY   := $(VENV)/bin/python
BIN  := $(VENV)/bin

# The gate. One definition of "green" -- the Stop hook, the pre-commit hook and
# ralph.sh all call this and nothing else. Cheapest layer first, stop on failure.
check: lint typecheck unit e2e
	@echo ""
	@echo "GATE GREEN"

lint:
	@echo "==> lint"
	@$(BIN)/ruff check .

typecheck:
	@echo "==> typecheck"
	@$(BIN)/mypy src/ --ignore-missing-imports

unit:
	@echo "==> unit"
	@$(BIN)/pytest tests/ -q

# e2e drives the real site via gstack browse. Local only -- CI has no browse
# binary. See VERIFICATION.md "Why e2e is local-only".
e2e:
	@echo "==> e2e"
	@bash scripts/e2e.sh

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
