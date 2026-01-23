# Complete Pytest Guide - CoNekT Grasses

## Index

1. [Initial Configuration](#initial-configuration)
2. [Test Structure](#test-structure)
3. [How to Create New Tests](#how-to-create-new-tests)
4. [Fixtures and Test Data](#fixtures-and-test-data)
5. [Creating Synthetic Data](#creating-synthetic-data)
6. [How to Execute Tests](#how-to-execute-tests)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

## Initial Configuration

### `pytest.ini` File

Located in the project root: `/CoNekT/pytest.ini`

```ini
[pytest]
# Directory where tests are located
testpaths = tests

# Test file patterns
python_files = *_test.py test_*.py
python_classes = Test*
python_functions = test_*

# Default options when running pytest
addopts = 
    -v                      # Verbose (shows each test)
    --tb=short             # Short traceback on errors
    --strict-markers       # Fail on unregistered markers
    --cov=conekt           # Code coverage
    --cov-report=term-missing  # Shows uncovered lines
    --cov-report=html      # Generate HTML report
    -p no:warnings         # Disable verbose warnings

# Custom markers
markers =
    unit: Unit tests
    integration: Integration tests
    website: Web route tests
    db: Tests that use database
    slow: Tests that take longer
    blast: Tests that require BLAST
    login_required: Tests that require login

# Coverage configurations
[coverage:run]
omit = 
    */tests/*
    */migrations/*
    */venv/*
    */bin/*
```

### `tests/config.py` File

Specific configuration for tests:

```python
import os
import tempfile

# Test database configuration
SQLALCHEMY_DATABASE_URI = 'mysql://username:password@localhost/test_conekt_grasses'
TESTING = True
WTF_CSRF_ENABLED = False
SECRET_KEY = 'test-secret-key'

# Optional features
LOGIN_ENABLED = False
BLAST_ENABLED = False

# Test configurations
DEBUG = True
ASSETS_DEBUG = True
```

### Required Dependencies

Add to `requirements.txt`:

```
pytest>=7.4.0
pytest-flask>=1.2.0
pytest-cov>=4.0.0
pytest-xdist>=3.3.0  # For parallel tests
pytest-mock>=3.11.0
```

Install:

```bash
cd /path/to/CoNekT
source bin/activate
pip install pytest pytest-flask pytest-cov pytest-xdist pytest-mock
```

## Test Structure

### `conftest.py` File

Shared fixtures central:

```python
"""
Fixtures shared by all tests.
"""
import pytest
from conekt import create_app, db
from . import config

@pytest.fixture(scope='session')
def app():
    """Creates Flask app for tests (once per session)."""
    app = create_app(config)
    yield app

@pytest.fixture(scope='session')
def _db(app):
    """Creates test database (once per session)."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield db
        db.drop_all()

@pytest.fixture(scope='function')
def database(app, _db):
    """Clean database for each test."""
    with app.app_context():
        yield _db
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            try:
                _db.session.execute(f"DELETE FROM {table.name}")
            except Exception:
                pass
        _db.session.commit()

@pytest.fixture
def client(app, _db):
    """Flask test client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """CLI runner for tests."""
    return app.test_cli_runner()
```

## How to Create New Tests

### Basic Test Structure

```python
import pytest
import json

@pytest.mark.unit
@pytest.mark.website
class TestMyFeature:
    """Tests for my feature."""
    
    def test_simple_example(self, client):
        """Tests basic functionality."""
        # Arrange (prepare)
        url = "/my_route"
        
        # Act (execute)
        response = client.get(url)
        
        # Assert (verify)
        assert response.status_code == 200
        assert b"expected text" in response.data
    
    def test_with_data(self, client, full_test_data):
        """Tests with database data."""
        # Use fixture data
        sequence = full_test_data['sequences'][0]
        
        response = client.get(f"/sequence/view/{sequence.id}")
        
        assert response.status_code == 200
        assert sequence.name.encode() in response.data
    
    def test_json_response(self, client, test_species):
        """Tests JSON response."""
        response = client.get(f"/api/species/{test_species.id}")
        
        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        
        assert "name" in data
        assert data["name"] == test_species.name
```

### Markers

Use markers to categorize tests:

```python
@pytest.mark.unit           # Unit test
@pytest.mark.integration    # Integration test
@pytest.mark.website        # Web route test
@pytest.mark.db             # Uses database
@pytest.mark.slow           # Slow test
@pytest.mark.skipif(True, reason="Reason")  # Skip test
```

### Parametrized Tests

To test multiple cases:

```python
@pytest.mark.parametrize("input,expected", [
    ("atg", "M"),
    ("atgtag", "M*"),
    ("atgaaatag", "MK*"),
])
def test_translate(input, expected):
    """Tests DNA to protein translation."""
    from utils.sequence import translate
    assert translate(input) == expected
```

## Fixtures and Test Data

### Types of Fixtures

#### Session-scoped (once per session)
```python
@pytest.fixture(scope='session')
def app():
    """Created once, used in all tests."""
    return create_app(config)
```

#### Function-scoped (default, once per test)
```python
@pytest.fixture
def test_sequence(database, test_species):
    """Created and destroyed for each test."""
    sequence = Sequence()
    sequence.species_id = test_species.id
    sequence.name = 'TEST_SEQ_001'
    sequence.description = 'Test sequence'
    sequence.coding_sequence = 'ATGCGATAG'
    sequence.type = 'protein_coding'
    database.session.add(sequence)
    database.session.commit()
    return sequence
```

### Creating a New Fixture

**Example: Fixture for TEClass**

```python
from conekt.models.te_classes import TEClass, TEClassMethod

@pytest.fixture
def test_te_class_method(database):
    """Creates TE classification method."""
    method = TEClassMethod('test_method')
    database.session.add(method)
    database.session.commit()
    return method

@pytest.fixture
def test_te_class(database, test_te_class_method):
    """Creates TE class for tests."""
    te_class = TEClass('TEST_TE_CLASS_01')
    te_class.method_id = test_te_class_method.id
    te_class.level1 = 'Class I'
    te_class.level2 = 'LTR'
    te_class.level3 = 'Copia'
    database.session.add(te_class)
    database.session.commit()
    return te_class
```

### Complete Integration Fixture

```python
@pytest.fixture
def full_test_data(database, test_species):
    """Creates complete set of related data."""
    # Create sequence
    sequence = Sequence(...)
    database.session.add(sequence)
    
    # Create GO term
    go = GO(...)
    database.session.add(go)
    
    # Associate
    sequence.go_labels.append(go)
    database.session.commit()
    
    return {
        'species': test_species,
        'sequence': sequence,
        'go': go
    }
```

## Creating Synthetic Data

### Data File Structure

**File: `tests/data/test_te_classes.txt`**

```
# Comments start with #
# Format: ID	Level1	Level2	Level3	Description
TE_CLASS_001	Class I	LTR	Copia	Long Terminal Repeat retrotransposon
TE_CLASS_002	Class I	LTR	Gypsy	Gypsy retrotransposon
TE_CLASS_003	Class II	DNA	MULE	Mutator-like element
```

**FASTA File: `tests/data/test_sequences.fasta`**

```
>TEST_SEQ_001 Description here
ATGCGATCGATCGATCGATCGATCG
ATCGATCGATCGATCGATCGATCGA
TAG
>TEST_SEQ_002 Another sequence
ATGAAACCCGGGTTTAAACCCGGGTAG
```

### Types of Required Data

| Type | File | Format | Usage |
|------|---------|---------|-----|
| Sequences | `.fasta` | Standard FASTA | Nucleotide/protein sequences |
| Annotations | `.txt` | Tab-delimited | Relations between entities |
| Hierarchies | `.txt` | Tab-delimited | Ontologies, classifications |
| Metadata | `.txt` | Tab-delimited | Descriptive information |

### Synthetic Data Template

```python
# To create new data type:

# 1. Create file in tests/data/
"""
tests/data/test_my_data.txt
"""

# 2. Define format
"""
# Description of data
# Format: Column1	Column2	Column3
ID_001	Value1	Value2
ID_002	Value3	Value4
"""

# 3. Create fixture to load
@pytest.fixture
def my_data(database):
    """Loads my test data."""
    data_file = 'tests/data/test_my_data.txt'
    
    with open(data_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split('\t')
            # Process and create objects
            obj = MyModel(parts[0], parts[1], parts[2])
            database.session.add(obj)
    
    database.session.commit()
    return MyModel.query.all()
```

## How to Execute Tests

### Basic Commands

```bash
# Activate virtual environment
cd /path/to/CoNekT
source bin/activate

# Run ALL tests
python -m pytest

# Run specific file
python -m pytest tests/website_test.py

# Run specific class
python -m pytest tests/website_test.py::TestTEClassRoutes

# Run specific test
python -m pytest tests/website_test.py::TestTEClassRoutes::test_te_class_view

# Run with verbose
python -m pytest -v

# Run and stop on first error
python -m pytest -x

# Run tests that failed previously
python -m pytest --lf
```

### Filters by Markers

```bash
# Only unit tests
python -m pytest -m unit

# Only website tests
python -m pytest -m website

# Only slow tests
python -m pytest -m slow

# Exclude slow tests
python -m pytest -m "not slow"

# Combine markers
python -m pytest -m "unit and website"
```

### Reports and Coverage

```bash
# With code coverage
python -m pytest --cov=conekt --cov-report=html

# View HTML report
firefox htmlcov/index.html

# With detailed report
python -m pytest -v --tb=long

# Summary only
python -m pytest -q

# Show prints
python -m pytest -s
```

### Parallel Tests

```bash
# Run with 4 parallel processes
python -m pytest -n 4

# Automatic (based on CPU cores)
python -m pytest -n auto
```

### Useful Scripts

**Create: `run_tests.sh`**

```bash
#!/bin/bash
# Script to run tests

cd "$(dirname "$0")"
source bin/activate

echo "🧪 Running CoNekT tests..."

# Run tests
python -m pytest tests/ -v --tb=short \
    --cov=conekt \
    --cov-report=term-missing \
    --cov-report=html

# Check result
if [ $? -eq 0 ]; then
    echo "All tests passed!"
else
    echo "Some tests failed!"
    exit 1
fi
```

Make executable:
```bash
chmod +x run_tests.sh
./run_tests.sh
```

## Best Practices

### Naming

**GOOD:**
```python
def test_sequence_view_returns_200(self, client, test_sequence):
    """Tests that sequence view returns status 200."""
    
def test_te_class_json_contains_species_data(self, client, test_te_class):
    """Verifies that JSON contains species distribution data."""
```

**BAD:**
```python
def test1(self, client):
    """Test."""
    
def test_stuff(self, client, data):
    """Test some stuff."""
```

### AAA Structure (Arrange-Act-Assert)

```python
def test_example(self, client, test_data):
    """Tests functionality X."""
    
    # Arrange - Prepare data and context
    sequence = test_data['sequence']
    expected_name = sequence.name
    
    # Act - Execute action
    response = client.get(f"/sequence/view/{sequence.id}")
    
    # Assert - Verify result
    assert response.status_code == 200
    assert expected_name.encode() in response.data
```

### One Concept Per Test

**GOOD:**
```python
def test_sequence_view_returns_success_code(self, client, test_sequence):
    """Tests status code."""
    response = client.get(f"/sequence/view/{test_sequence.id}")
    assert response.status_code == 200

def test_sequence_view_contains_name(self, client, test_sequence):
    """Tests presence of name."""
    response = client.get(f"/sequence/view/{test_sequence.id}")
    assert test_sequence.name.encode() in response.data
```

**BAD:**
```python
def test_sequence_view(self, client, test_sequence):
    """Tests everything about view."""
    response = client.get(f"/sequence/view/{test_sequence.id}")
    assert response.status_code == 200
    assert test_sequence.name.encode() in response.data
    assert b"description" in response.data
    assert b"species" in response.data
    # ... 10 more asserts
```

### Independent Tests

```python
# GOOD - Each test creates its data
def test_create_sequence(self, database):
    seq = Sequence(...)
    database.session.add(seq)
    database.session.commit()
    assert seq.id is not None

def test_delete_sequence(self, database):
    seq = Sequence(...)
    database.session.add(seq)
    database.session.commit()
    database.session.delete(seq)
    database.session.commit()
    assert Sequence.query.get(seq.id) is None

# BAD - Dependency between tests
def test_create_sequence(self, database):
    self.seq = Sequence(...)  # Stores in self
    database.session.add(self.seq)
    
def test_delete_sequence(self, database):
    database.session.delete(self.seq)  # Depends on previous test
```

### When to Use Skip

```python
@pytest.mark.skipif(True, reason="Requires specific data not available")
def test_complex_feature(self, client):
    """Test that requires complex setup."""
    pass

@pytest.mark.skipif(True, reason="Bug in controller: issue #123")
def test_buggy_route(self, client):
    """Test for functionality with known bug."""
    pass
```

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check if MySQL/MariaDB is running
sudo systemctl status mysql

# Verify test database exists
mysql -u root -p
> SHOW DATABASES;
> USE test_conekt_grasses;
```

#### Import Errors
```bash
# Make sure you're in the right directory
cd /path/to/CoNekT

# Activate virtual environment
source bin/activate

# Check PYTHONPATH
export PYTHONPATH=$PWD:$PYTHONPATH
```

#### Fixture Not Found
```python
# Make sure fixture is defined in conftest.py
# or imported properly
from .conftest import my_fixture
```

#### Slow Tests
```bash
# Run only fast tests
python -m pytest -m "not slow"

# Use parallel execution
python -m pytest -n auto
```

### Debug Mode

```bash
# Run with maximum verbosity
python -m pytest -vvv

# Show local variables in traceback
python -m pytest --tb=long

# Drop into debugger on failures
python -m pytest --pdb

# Show print statements
python -m pytest -s
```

### Performance Tips

1. **Use session-scoped fixtures** for expensive setup
2. **Group related tests** in classes
3. **Use parametrized tests** for multiple cases
4. **Skip slow tests** during development
5. **Use parallel execution** for large test suites 