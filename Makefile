.PHONY: help watch build clean
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

help:
	@echo "$(BLUE)VoxKit - Dev Commands$(RESET)"
	@echo "======================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-15s$(RESET) %s\n", $$1, $$2}'

watch: ## Watch for file changes and restart dev server (requires entr)
	@if command -v entr >/dev/null 2>&1; then \
		echo "$(BLUE)Watching for changes... Press Ctrl+C to stop$(RESET)"; \
		find src/ -name "*.py" | entr -r uv run main.py; \
	else \
		echo "$(RED)entr not installed. Install with: brew install entr$(RESET)"; \
		echo "$(YELLOW)Falling back to single run...$(RESET)"; \
		uv run main.py; \
	fi

build: clean ## Build standalone executable for current platform
	@echo "$(BLUE)Building standalone executable...$(RESET)"
	@uv run --group installation build.py

clean: ## Clean build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(RESET)"
	@rm -rf build/ dist/ *.spec
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)Cleanup completed$(RESET)"

format: ## Format code with Ruff
	@echo "$(BLUE)Formatting code with Ruff...$(RESET)"
	uv run --only-group dev ruff format .

format-check: ## Check code formatting with Ruff
	@echo "$(BLUE)Checking code formatting with Ruff...$(RESET)"
	uv run --only-group dev ruff format --check .

lint: ## Lint code with Ruff
	@echo "$(BLUE)Linting with Ruff...$(RESET)"
	uv run --only-group dev ruff check --fix .

lint-check: ## Check linting with Ruff
	@echo "$(BLUE)Checking linting with Ruff...$(RESET)"
	uv run --only-group dev ruff check .

mypy-check: ## Run mypy for type checking
	@echo "$(BLUE)Running mypy for type checking...$(RESET)"
	uv run --only-group dev mypy .

fresh-slate: ## Remove virtual environment and lock file
	@echo "$(BLUE)Removing virtual environment and lock file...$(RESET)"
	@read -p "Are you sure you want to proceed? [y/N] " confirm && [ $${confirm} = "y" ] || [ $${confirm} = "Y" ] && rm -rf uv.lock .venv || echo "Aborted."
