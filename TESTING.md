# Testing Strategy & Coverage

## Overview

This document explains VoxKit's testing approach and how test coverage is measured to provide meaningful metrics about code quality and test rigor.

## Current Coverage

The raw coverage percentage previously reported (~36%) was misleading because it included modules that are:
- **Difficult to test**: GUI components requiring PyQt6 event loops and user interactions
- **Impractical to test**: OS-level integrations, hardware dependencies, external tool wrappers
- **Low-value to test**: Simple glue code, configuration files, build scripts

With the refined coverage measurement focusing on testable business logic, coverage metrics now accurately reflect the quality of tests for **core, testable components**.

---

## Coverage Philosophy

Our testing strategy follows these principles:

1. **Focus on Business Logic**: Prioritize testing core algorithms, data models, and logic
2. **Pragmatic Testing**: Don't force tests where they provide little value
3. **Meaningful Metrics**: Coverage % should reflect actual test quality, not vanity numbers
4. **Maintainable Tests**: Tests should be reliable, fast, and easy to maintain

---

## Module Classification

### 🟢 Testable & Tested (Core Business Logic)

These modules contain testable business logic and should maintain high coverage:

| Module | Lines | Description | Coverage Target |
|--------|-------|-------------|-----------------|
| **storage/** | 1,689 | Data persistence, CRUD operations | 80-90% |
| **config/** | 391 | Configuration management | 70-80% |
| **analyzers/** | 339 | Dataset analysis logic | 70-80% |
| **engines/base.py** | ~200 | Engine abstraction layer | 70-80% |

**Why These Matter:**
- Central to application functionality
- Pure Python logic without heavy dependencies
- High risk if broken (data loss, corruption)
- Easy to test with unit tests

### 🟡 Partially Testable (Integration-Heavy)

These modules can be tested but require more complex setup:

| Module | Lines | Description | Approach |
|--------|-------|-------------|----------|
| **engines/*_engine.py** | ~876 | External tool wrappers | Integration tests, mocks for external calls |
| **services/** | 131 | Service layer integrations | Mock subprocess calls |

**Testing Strategy:**
- Focus on input validation and error handling
- Mock external dependencies (subprocess, file I/O)
- Integration tests with test fixtures
- Currently **excluded** from coverage to avoid misleading metrics

### 🔴 Difficult/Low-Value to Test (GUI & System-Dependent)

These modules are excluded from coverage reporting:

| Module | Lines | Reason for Exclusion |
|--------|-------|---------------------|
| **gui/** | 7,406 | PyQt6 UI code - requires complex GUI test harness, prone to flakiness |
| **build.py** | ~200 | Build/deployment script - tested manually during releases |
| **main.py** | ~50 | Application entry point - integration tested manually |

**Why Excluded:**
- **GUI Components**: Require QApplication, event loops, X server/display; tests are slow and brittle
- **Build Scripts**: One-time use, manually verified during release process
- **Entry Points**: Thin wrappers around initialization, manually tested

---

## Coverage Configuration

Coverage exclusions are configured in `pyproject.toml`:

```toml
[tool.coverage.run]
omit = [
    "src/voxkit/engines/*_engine.py",    # External tool integrations
    "src/voxkit/gui/**/*.py",             # PyQt6 UI components
    "src/voxkit/services/*.py",           # Service integrations
    "build.py",                           # Build scripts
    "main.py",                            # Entry point
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    # ... additional patterns
]
```

---

## Running Tests

### Run All Tests
```bash
make run-tests
```

### Generate Coverage Report
```bash
make generate-coverage-badge
```

This will:
1. Run tests on **core business logic only** (storage, config, analyzers)
2. Generate coverage report showing meaningful coverage percentage
3. Update the coverage badge in the repository

### Understanding Coverage Reports

The coverage report shows:
- **Covered Modules**: storage/, config/, analyzers/, engines/base.py
- **Excluded Modules**: gui/, engines/*_engine.py, services/, build scripts

A coverage of **70-85% on measured modules** indicates:
- High-quality tests for business logic
- Good protection against regressions
- Confidence in core functionality

---

## Improving Coverage

### Priority Areas for New Tests

1. **Storage Layer** (highest priority)
   - Dataset CRUD operations
   - Model management
   - Alignment tracking
   - Data validation and schema enforcement

2. **Configuration** (medium priority)
   - Settings validation
   - Config file parsing
   - Default value handling

3. **Analyzers** (medium priority)
   - Dataset analysis algorithms
   - Summary generation
   - Error handling

### Testing Guidelines

- **Unit Tests**: For pure logic, data transformations, algorithms
- **Integration Tests**: For database operations, file I/O with temp directories
- **Mocking**: Use mocks for external dependencies (subprocess, network calls)
- **Fixtures**: Leverage pytest fixtures for common test data

### Example: Testing Storage Module

```python
# tests/storage/test_datasets.py
from pathlib import Path
from voxkit.storage.datasets import DatasetManager

def test_dataset_registration(tmp_path):
    """Test dataset registration with valid data."""
    manager = DatasetManager(storage_root=tmp_path)
    dataset_id = manager.register_dataset(
        name="Test Dataset",
        path="/path/to/dataset",
    )
    assert dataset_id is not None
    assert manager.get_dataset(dataset_id).name == "Test Dataset"
```

---

## When NOT to Write Tests

It's acceptable to skip tests for:

1. **Trivial Code**: Simple getters/setters, straightforward property accessors
2. **GUI Glue Code**: Button click handlers that just call business logic (test the logic instead)
3. **External Tool Wrappers**: Subprocess calls to external binaries (test the wrapper logic, not the tool)
4. **Build/Deployment Scripts**: One-off scripts tested manually

---

## Continuous Integration

Our CI pipeline runs:
1. **Unit Tests**: All tests in `tests/` directory
2. **Linting**: Ruff for code quality
3. **Type Checking**: mypy for type safety
4. **Coverage Report**: Generated and displayed in PR checks

---

## FAQ

**Q: Why is the coverage percentage lower than I expected?**

A: The coverage metric excludes GUI and integration code. Focus on improving tests for storage, config, and analyzers modules where coverage has the most value.

**Q: Should I write tests for GUI components?**

A: Generally no, unless testing critical business logic embedded in GUI code (extract it to a testable module instead). If GUI testing is needed, use pytest-qt with fixtures, but expect slower, more brittle tests.

**Q: How do I test code that calls external tools?**

A: Mock the subprocess calls using `unittest.mock.patch` or `pytest-mock`. Test the input preparation, output parsing, and error handling, not the external tool itself.

**Q: What's the coverage target for the codebase?**

A: Aim for **70-85% coverage on measured modules** (storage, config, analyzers). This indicates solid testing without diminishing returns from testing trivial code.

---

## References

- [pytest documentation](https://docs.pytest.org/)
- [coverage.py documentation](https://coverage.readthedocs.io/)
- [pytest-qt for GUI testing](https://pytest-qt.readthedocs.io/)
- [unittest.mock for mocking](https://docs.python.org/3/library/unittest.mock.html)
