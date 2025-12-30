.PHONY: install test test-all lint format type-check coverage clean docs docs-clean help

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

type-check:  ## Run mypy type checker
	mypy meshiphi

coverage:  ## Generate coverage report (terminal and HTML)
	pytest --cov=meshiphi --cov-report=term-missing --cov-report=html --cov-report=xml -m "not slow"
	@echo "\nCoverage report generated. Open htmlcov/index.html to view the HTML report."

clean:  ## Clean build artifacts and cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf docs/_build/
	rm -rf docs/html/
	find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "Clean complete."

docs:  ## Build documentation
	cd docs && sphinx-build -b html source _build/html
	@echo "Documentation built in docs/_build/html/"

docs-clean:  ## Clean documentation build artifacts
	rm -rf docs/_build/
	rm -rf docs/html/
	rm -rf docs/build/.doctrees/
	@echo "Documentation build artifacts cleaned."
