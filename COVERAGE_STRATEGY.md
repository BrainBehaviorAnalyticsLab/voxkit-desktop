# Coverage Strategy Summary

## Quick Reference

### What We Measure
✅ **Storage layer** (1,689 lines) - Data persistence & CRUD  
✅ **Config modules** (391 lines) - Configuration management  
✅ **Analyzers** (339 lines) - Dataset analysis logic  
✅ **Engine base** (~200 lines) - Engine abstraction  

### What We Exclude
❌ **GUI components** (7,406 lines) - PyQt6 UI, difficult to test  
❌ **Engine implementations** (~876 lines) - External tool wrappers  
❌ **Services** (131 lines) - Subprocess/system integrations  
❌ **Build scripts** - Manually tested during releases  

## Coverage Targets

| Module | Target Coverage | Priority |
|--------|----------------|----------|
| storage/ | 80-90% | 🔴 Critical |
| config/ | 70-80% | 🟡 High |
| analyzers/ | 70-80% | 🟡 High |
| engines/base.py | 70-80% | 🟡 High |

## Commands

```bash
# Run tests with focused coverage (core modules only)
make test-coverage

# Generate coverage badge
make generate-coverage-badge

# Run tests with ALL modules for comparison (note: will show lower %)
make test-coverage-all
```

## Why This Approach?

**Before:** 36% coverage (misleading - includes untestable GUI code)  
**After:** Focused coverage on testable business logic only  

This provides **meaningful metrics** that reflect actual test quality for core functionality.

## More Information

See [TESTING.md](./TESTING.md) for detailed testing strategy and guidelines.
