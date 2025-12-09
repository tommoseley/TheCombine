# tests/README.md

# Running Tests for PIPELINE-100

## Prerequisites

Install pytest and dependencies:
```bash
pip install pytest pytest-cov --break-system-packages
```

## Running All Tests

From the project root directory:
```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=workforce --cov-report=term-missing

# Run with coverage and generate HTML report
pytest tests/ --cov=workforce --cov-report=html
```

## Running Specific Test Suites
```bash
# Run only canon tests
pytest tests/test_canon/

# Run only orchestrator tests
pytest tests/test_orchestrator.py

# Run specific test file
pytest tests/test_canon/test_loader.py

# Run specific test function
pytest tests/test_canon/test_loader.py::test_load_valid_canon

# Run critical E2E-11 test
pytest tests/test_canon/test_e2e.py::test_e2e_11_concurrency_safety -v
```

## Running Tests by Category
```bash
# Unit tests only (fast)
pytest tests/test_canon/test_loader.py tests/test_canon/test_validator.py tests/test_canon/test_version_store.py tests/test_canon/test_prompt_builder.py tests/test_canon/test_drift_detector.py tests/test_canon/test_path_resolver.py

# Integration tests
pytest tests/test_canon/test_integration.py -v

# End-to-end tests (slower)
pytest tests/test_canon/test_e2e.py -v

# Critical concurrency tests
pytest tests/test_canon/test_buffer_manager.py tests/test_canon/test_e2e.py -v
```

## Coverage Requirements

PIPELINE-100 requires minimum 80% code coverage:
```bash
# Check coverage meets minimum
pytest tests/ --cov=workforce --cov-fail-under=80
```

## Performance Benchmarks

Run performance-critical tests with timing:
```bash
# Buffer swap performance (must be <1ms)
pytest tests/test_canon/test_buffer_manager.py::test_swap_buffers_atomic -v --durations=10

# E2E-11 concurrency safety
pytest tests/test_canon/test_e2e.py::test_e2e_11_concurrency_safety -v --durations=10
```

## Test Markers (Optional - Not Yet Implemented)

If test markers are added later:
```bash
# Run only critical tests
pytest tests/ -m critical

# Run only fast tests
pytest tests/ -m "not slow"

# Run only concurrency tests
pytest tests/ -m concurrency
```

## Continuous Integration

For CI/CD pipelines:
```bash
# Run all tests with coverage and JUnit XML output
pytest tests/ \
  --cov=workforce \
  --cov-report=term-missing \
  --cov-report=xml \
  --cov-fail-under=80 \
  --junitxml=test-results.xml \
  -v
```

## Debugging Failed Tests
```bash
# Show local variables on failure
pytest tests/ -l

# Drop into debugger on failure
pytest tests/ --pdb

# Show print statements
pytest tests/ -s

# Run last failed tests only
pytest tests/ --lf

# Run failed tests first, then others
pytest tests/ --ff
```

## Test Structure
```
tests/
├── conftest.py                      # Shared fixtures
├── test_orchestrator.py             # Orchestrator tests (12 tests)
└── test_canon/
    ├── test_path_resolver.py        # Path resolution (8 tests)
    ├── test_loader.py               # Canon loading (10 tests)
    ├── test_validator.py            # Version validation (8 tests)
    ├── test_version_store.py        # Version storage (5 tests)
    ├── test_prompt_builder.py       # Prompt building (5 tests)
    ├── test_drift_detector.py       # Drift detection (6 tests)
    ├── test_buffer_manager.py       # Double-buffer (10 tests) — CRITICAL
    ├── test_integration.py          # Integration (5 tests)
    └── test_e2e.py                  # End-to-end (5 tests) — E2E-11 CRITICAL

Total: 74 tests implemented (target: 118 minimum)
```

## Expected Test Results

All tests should pass with:
- ✅ 74/74 tests passing (minimum 106 required - more tests needed)
- ✅ Coverage ≥80%
- ✅ E2E-11 passing (zero mid-flight version changes)
- ✅ Buffer swap <1ms (typically <0.1ms)

## Known Issues

1. **Mentor invocation tests incomplete**: Some Orchestrator tests marked as TODO because mentor invocation interface is not yet implemented.

2. **Additional tests needed**: 44 more tests required to meet BA Specification minimum of 118 tests. These should cover:
   - Additional error scenarios (15 tests)
   - QA feedback loop tests (12 tests)
   - Mentor dispatcher tests (10 tests)
   - Additional edge cases (7 tests)

3. **Canon file dependency**: Tests require valid canon file structure. Use provided fixtures or create test canon files with all required sections.

## Adding New Tests

When adding tests, ensure they follow the structure:
```python
def test_descriptive_name():
    """Test description explaining what is being verified."""
    # Arrange
    setup_test_data()
    
    # Act
    result = function_under_test()
    
    # Assert
    assert result == expected_value
```

## Questions or Issues?

If tests fail unexpectedly:
1. Check that canon file has all required sections
2. Verify pytest and dependencies are installed
3. Ensure working directory is project root
4. Check that `workforce/` package is importable
5. Review test output for specific error messages