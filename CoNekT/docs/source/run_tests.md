# Running Tests - CoNekT Grasses

This document provides basic information on how to execute tests in CoNekT Grasses.

## Overview

CoNekT Grasses uses **pytest** as testing framework with complete coverage of system functionalities. For detailed information about creating tests, fixtures, and synthetic data, see the [Pytest Testing Guide](pytest_guide.md).

## Quick Test Execution

### Prerequisites

1. **Active Virtual Environment**:
   ```bash
   cd /path/to/CoNekT
   source bin/activate
   ```

2. **Test Database Configured**:
   ```bash
   mysql -u root -p
   > CREATE DATABASE test_conekt_grasses;
   > GRANT ALL PRIVILEGES ON test_conekt_grasses.* TO 'your_user'@'localhost';
   ```

3. **Test Dependencies** (already in requirements.txt):
   ```bash
   pip install -r requirements.txt
   ```

### Run All Tests

```bash
# Run all tests
python -m pytest

# With code coverage
python -m pytest --cov=conekt --cov-report=html

# Only fast tests (exclude tests marked as 'slow')
python -m pytest -m "not slow"
```

### Run Specific Tests

```bash
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
| `tests/conftest.py` | Shared fixtures | - |
| `tests/config.py` | Test configuration | - |

## Configuration Files

### pytest.ini
**Location**: `tests/pytest.ini`
- Defines test directories and discovery patterns
- Configures custom markers
- Establishes default execution options

### Test Database Configuration
**File**: `tests/config.py`
- Isolated configuration for test environment
- Connection string: `test_conekt_grasses` database
- CSRF disabled, DEBUG enabled

## Expected Results

### Current Test Status
- **Total**: 127 tests
- **Passing**: 113 website tests + 14 build tests
- **Skipped**: 12 tests (specific configuration required)

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
mysql -u root -p -e "SHOW DATABASES LIKE 'test_conekt_grasses';"
```

**Import Errors**:
```bash
# Make sure you're in the correct directory
cd /path/to/CoNekT
export PYTHONPATH=$PWD:$PYTHONPATH
```

**Test Failures**:
```bash
# See error details
python -m pytest -v --tb=long

# Stop on first error
python -m pytest -x
```

## Next Steps

For detailed information about:
- **Creating new tests**
- **Using fixtures and synthetic data**
- **Understanding test structure**
- **Adding test data**

See the complete **[Pytest Testing Guide](pytest_guide.md)**.