# Running Tests - CoNekT Grasses

This document provides basic information on how to execute tests in CoNekT Grasses.

## Overview

CoNekT Grasses uses **pytest** as testing framework with complete coverage of system functionalities. For detailed information about creating tests, fixtures, and synthetic data, see the [Pytest Testing Guide](pytest_guide.md).

## Quick Test Execution

### Prerequisites

1. **Active Virtual Environment**:
   ```bash
   # Navigate to project and activate environment
   cd /path/to/conekt_grasses
   source CoNekT/bin/activate
   
   # For direct pytest execution, enter CoNekT directory
   cd CoNekT
   ```

2. **Test Database Configured**:
   ```bash
   mysql -u root -p
   
   CREATE DATABASE conekt_grasses_db_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
   
   GRANT INDEX, CREATE, DROP, SELECT, UPDATE, DELETE, ALTER, EXECUTE, INSERT on conekt_grasses_db_test.* TO 'conekt_grasses_admin'@'localhost'

   GRANT FILE on *.* TO 'conekt_grasses_admin'@'localhost'

   FLUSH PRIVILEGES
   ```

3. **Test Dependencies** (already in requirements.txt):
   ```bash
   pip install -r requirements.txt
   ```

### Run All Tests

**Important**: When using pytest directly (not via `run_tests.sh`), you must be in the `CoNekT` directory:

```bash
# Navigate to CoNekT directory first
cd CoNekT

# Run all tests
python -m pytest

# With code coverage
python -m pytest --cov=conekt --cov-report=html

# Only fast tests (exclude tests marked as 'slow')
python -m pytest -m "not slow"
```

### Run Specific Tests

```bash
# Make sure you're in CoNekT directory
cd CoNekT

# Web route tests
python -m pytest -m website

# Database tests
python -m pytest -m db  

# Unit tests
python -m pytest -m unit

# Specific file
python -m pytest tests/website_test.py

# Specific test
python -m pytest tests/website_test.py::TestTERoutes::test_te_view
```

## Using the run_tests.sh Script

### Overview

The project includes a comprehensive test execution script located at the **root of the repository**: `run_tests.sh`. This script provides a user-friendly interface for running pytest with various options and automatic environment setup.

**Why it's in the root**: The script is placed at the repository root to:
- Provide easy access from any location in the project
- Automatically configure the correct project paths and Python environment
- Serve as the main entry point for running tests in CI/CD pipelines
- Handle virtual environment activation and dependency verification

### Basic Usage

```bash
# Navigate to project root
# Make script executable (first time only)
chmod +x run_tests.sh

# Run all tests
./run_tests.sh

# Show help and available options
./run_tests.sh --help
```

### Common Commands

```bash
# Unit tests only
./run_tests.sh --unit

# Website tests only
./run_tests.sh -m website

# Tests with coverage report
./run_tests.sh --cov

# Parallel execution (faster)
./run_tests.sh -n 4

# Stop on first failure
./run_tests.sh --exitfirst

# Run only failed tests from last run
./run_tests.sh --failed

# Verbose output
./run_tests.sh --verbose

# Run specific test by keyword
./run_tests.sh -k "test_sequence"
```

### Script Features

- **Automatic Environment Detection**: Checks for active virtual environment
- **Dependency Verification**: Ensures pytest and required packages are installed
- **Colored Output**: User-friendly colored terminal messages
- **Path Configuration**: Automatically sets PYTHONPATH correctly
- **Multiple Options**: Supports all pytest options with convenient shortcuts
- **Error Handling**: Provides clear error messages and suggestions
- **Results Management**: Automatically saves all logs and reports in `tests/results/`
- **Timestamped Output**: All files include timestamp for historical tracking

### Advanced Usage Examples

```bash
# Complex marker combinations
./run_tests.sh -m "unit and website and not slow"

# Generate HTML report
./run_tests.sh --html

# Debug mode (stops at failures)
./run_tests.sh --pdb

# Show available test markers
./run_tests.sh --markers

# List tests without running them
./run_tests.sh --collect-only
```

## Viewing Test Results

### Saved Results Location
All test execution results are automatically saved in the `tests/results/` directory with timestamped filenames.

### Types of Results Generated

**Log Files** (Always created):
```bash
# Complete execution log with all output
tests/results/pytest-log_20260223_105845.txt
```

**HTML Reports** (with `--html`):
```bash
# Interactive test report
tests/results/pytest-report_20260223_105845.html
```

**XML Reports** (with `--xml`):
```bash
# JUnit XML for CI/CD integration
tests/results/pytest-report_20260223_105845.xml
```

**Coverage Reports** (with `--cov`):
```bash
# Interactive HTML coverage
tests/results/htmlcov_20260223_105845/index.html
```

### Accessing Results

```bash
# View latest log in terminal
cat CoNekT/tests/results/pytest-log_*.txt | tail -50

# Open latest HTML report in browser
firefox CoNekT/tests/results/pytest-report_*.html

# Open latest coverage report
firefox CoNekT/tests/results/htmlcov_*/index.html

# List all saved results
ls -la CoNekT/tests/results/
```

## Test Categories

The system uses **pytest markers** to categorize tests:

| Marker | Description | Count |
|--------|-------------|-------|
| `website` | Web routes and views tests | 113 |
| `db` | Tests requiring database | 127 |
| `unit` | Fast unit tests | 50+ |
| `integration` | Integration tests | 30+ |
| `slow` | Time-consuming tests | 15+ |

## Test Files

| File | Purpose | Tests |
|------|---------|-------|
| `tests/website_test.py` | Web route tests | 113 |
| `tests/build_test.py` | Data loading tests | 14 |
| `tests/conf_test.py` | Shared fixtures | - |
| `tests/config.py` | Test configuration | - |
| `tests/results/` | Test results and logs | - |

## Configuration Files

### pytest.ini
**Location**: `CoNekT/pytest.ini`
- Defines test directories and discovery patterns
- Configures custom markers
- Establishes default execution options
- Controls test collection to avoid external packages

### Test Database Configuration
**File**: `tests/config.py`
- Isolated configuration for test environment
- Connection string: `conekt_grasses_db_test` database
- CSRF disabled, DEBUG enabled

### Test Results Directory
**Location**: `tests/results/`
- **Automatic Creation**: Created by run_tests.sh during execution
- **Timestamped Files**: All results include timestamp (YYYYMMDD_HHMMSS)
- **Logs**: Complete execution logs saved as `pytest-log_[timestamp].txt`
- **Reports**: HTML and XML reports when using `--html` or `--xml` options
- **Coverage**: HTML coverage reports when using `--cov` option
- **Git Ignored**: Results directory is excluded from version control

## Expected Results

### Current Test Status
- **Total**: 127 tests
- **Passing**: 113 website tests + 14 build tests
- **Skipped**: 12 tests (specific configuration required)

### Test Results Storage
- **Location**: All results saved in `tests/results/` with timestamps
- **Logs**: Complete execution output in `pytest-log_[timestamp].txt`
- **Reports**: HTML/XML reports when requested with `--html`/`--xml`
- **Coverage**: Interactive HTML coverage reports with `--cov`
- **Automatic**: Results created automatically by `run_tests.sh`

### Coverage
- **Web Routes**: All main routes tested
- **Data Loading**: All build functions tested
- **Models**: TEs, CAZymes, Expression, Networks, Ontologies
- **APIs**: JSON responses and endpoints

## Troubleshooting

### Common Issues

**Database Connection Error**:
```bash
# Check if MySQL is running
sudo systemctl status mysql

# Verify test database exists
mysql -u root -p -e "SHOW DATABASES LIKE 'conekt_grasses_db_test';"
```

**Import Errors**:
```bash
# Make sure you're in the CoNekT directory for pytest
cd CoNekT
export PYTHONPATH=$PWD:$PYTHONPATH

# Or use the run_tests.sh script from project root
cd ..
./run_tests.sh
```

**Test Failures**:
```bash
# From CoNekT directory - See error details
python -m pytest -v --tb=long

# From CoNekT directory - Stop on first error
python -m pytest -x

# Or use the script from project root
cd ..
./run_tests.sh --verbose --exitfirst
```

## Next Steps

For detailed information about:
- **Creating new tests**
- **Using fixtures and synthetic data**
- **Understanding test structure**
- **Adding test data**

See the complete **[Pytest Testing Guide](pytest_guide.md)**.