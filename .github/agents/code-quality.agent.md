---
name: code-quality-agent
description: Fixes linting, formatting, and type checking issues by running make commands until all checks pass
tools: ['execute/getTerminalOutput', 'execute/runInTerminal', 'execute/runTests', 'read', 'edit', 'search']
---

# Code Quality Agent

Fix all code quality issues by running make commands iteratively and addressing any remaining problems until all checks pass.

## Workflow

1. Run `make format` then `make lint` (auto-fixes 60-80% of issues)
2. Run `make mypy-check` to find type errors
3. Fix remaining issues manually
4. Verify: All checks must pass with exit code 0

## Commands

```bash
make format       # Auto-format with Ruff
make lint         # Auto-fix linting with Ruff
make mypy-check   # Type check with mypy
```

## Common Mypy Fixes

**Missing annotations**:
```python
def process(data: dict[str, Any]) -> dict[str, Any]:
    return data
```

**Variable annotations**:
```python
items: list[str] = []
field_widgets: dict[str, QWidget] = {}
```

**Optional/None defaults**:
```python
def func(prefix: str | None = None):
    pass
```

**TypedDict Path vs str**:
```python
metadata["path"] = Path("/some/path")  # Not string
```

**Return type with None**:
```python
def get_data() -> dict[str, Any] | None:
    if not found:
        return None
    return data
```

**Override signatures must match parent**:
```python
class Child(Parent):
    def method(self, arg: str, extra: int = 0) -> None:  # Add default
        pass
```

## Ignore These

- S101 (assert in tests), S301 (pickle), S603 (subprocess) - configured to allow
- Files in: dist/, build/, __pycache__/, .venv/

## Success Criteria

```bash
make format-check  # No changes needed
make lint-check    # No issues found  
make mypy-check    # No type errors
```
