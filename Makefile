.PHONY: help
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

setup: ## Install dependencies and setup pre-commit hooks
	@echo "$(BLUE)Installing dependencies with uv sync...$(RESET)"
	uv sync
	@echo "$(BLUE)Installing pre-commit hooks...$(RESET)"
	uv run pre-commit install
	@echo "$(GREEN)Setup completed successfully!$(RESET)"

watch: ## Watch for file changes and restart dev server (requires entr)
	@if command -v entr >/dev/null 2>&1; then \
		echo "$(BLUE)Watching for changes... Press Ctrl+C to stop$(RESET)"; \
		find src/ -name "*.py" | entr -r uv run main.py; \
	else \
		echo "$(RED)entr not installed. Install with: brew install entr$(RESET)"; \
		echo "$(YELLOW)Falling back to single run...$(RESET)"; \
		uv run main.py; \
	fi

dev: ## Run the development server
	@echo "$(BLUE)Starting development server...$(RESET)"
	uv run main.py

build: clean ## Build standalone executable for current platform
	@echo "$(BLUE)Building VoxKit for macOS...$(RESET)"
	uv run --group installation python build.py build --entry main.py --name VoxKit --icon ./assets/voxkit.icns --windowed

build-info: ## Show information about the built app
	@echo "$(BLUE)Checking build output...$(RESET)"
	@if [ -d "dist/VoxKit" ]; then \
		echo "$(GREEN)Found: dist/VoxKit/$(RESET)"; \
		ls -lh dist/VoxKit/; \
		echo ""; \
		echo "$(BLUE)Checking executable...$(RESET)"; \
		file dist/VoxKit/VoxKit; \
		echo ""; \
		echo "$(BLUE)Checking library dependencies...$(RESET)"; \
		otool -L dist/VoxKit/VoxKit | head -10; \
	else \
		echo "$(RED)dist/VoxKit not found. Run 'make build' first.$(RESET)"; \
	fi

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

run-tests: ## Run all tests (unit + GUI)
	uv run pytest tests/

test-coverage: ## Run tests with detailed coverage report for core modules
	@echo "$(BLUE)Running tests with coverage (core modules only)...$(RESET)"
	uv run pytest --cov=voxkit --cov-report=term-missing --cov-report=html tests/
	@echo "$(GREEN)Coverage report generated in htmlcov/index.html$(RESET)"

test-coverage-all: ## Show coverage including excluded modules (for comparison)
	@echo "$(BLUE)Running tests to see ALL coverage (including excluded modules)...$(RESET)"
	@echo "$(YELLOW)Note: Run 'pytest --cov=voxkit tests/' directly to bypass omit config$(RESET)"
	@echo "$(YELLOW)This make target shows the same focused coverage as test-coverage$(RESET)"
	uv run pytest --cov=voxkit --cov-report=term-missing tests/
	@echo ""
	@echo "$(YELLOW)To see truly unfiltered coverage, temporarily edit pyproject.toml's omit list$(RESET)"

generate-coverage-badge: ## Generate coverage badge (focused on core modules)
	@echo "$(BLUE)Generating coverage badge...$(RESET)"
	uv run pytest --cov=voxkit --cov-report=term tests/
	uv run coverage-badge -o coverage.svg -f
	@echo "$(GREEN)Coverage badge updated: coverage.svg$(RESET)"

generate-documentation: ## Generate API documentation
	uv run --group docs pdoc -o docs src/voxkit
