.PHONY: check check-fast lint typecheck unit worker e2e clean

VENV := .venv
PY   := $(VENV)/bin/python
BIN  := $(VENV)/bin

# The gate. One definition of "green" -- the Stop hook, the pre-commit hook and
# ralph.sh all call this and nothing else. Cheapest layer first, stop on failure.
check: lint typecheck unit worker e2e
	@echo ""
	@echo "GATE GREEN"

# The fast gate: everything except e2e. Used by the pre-commit hook, because a
# pre-commit that takes 20s is a pre-commit people learn to bypass with --no-verify,
# and a bypassed gate is worse than a fast one. The FULL gate (incl. e2e) is
# enforced by the Stop hook, which is what actually guards the Ralph loop.
check-fast: lint typecheck unit worker
	@echo ""
	@echo "FAST GATE GREEN (e2e not run -- full gate is 'make check')"

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
# The Worker's own tests. Node's stdlib runner, no framework and no npm install:
# `auth.mjs` is deliberately dependency-free so it runs identically here and in
# the Workers runtime -- which is what lets the gate attack it on a machine where
# workerd will not start (wrangler warns below macOS 13.5).
worker:
	@echo "==> worker"
	@if command -v node >/dev/null 2>&1; then \
		out=$$(node --test 'worker/*.test.mjs' 2>&1); status=$$?; \
		echo "$$out" | tail -8; \
		[ $$status -eq 0 ] || { echo "$$out" | grep -E '^not ok|error:|expected:|actual:'; exit 1; }; \
	else \
		echo "SKIP: node not found; worker tests cannot run here"; \
	fi

e2e:
	@echo "==> e2e"
	@bash scripts/e2e.sh

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
