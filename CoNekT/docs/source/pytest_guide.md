# Pytest Testing Guide - CoNekT Grasses

This guide provides practical instructions for creating and developing tests in CoNekT Grasses using pytest.

For test execution, setup, and running commands, see [Running Tests](run_tests.md).

## How to Create New Tests

### 1. Understanding Test Types

**Unit Tests** (`@pytest.mark.unit`):
- Test individual functions or small components in isolation
- Fast execution (< 1 second each)  
- No database or external dependencies
- Example: Testing utility functions, data transformations

**Integration Tests** (`@pytest.mark.integration`):
- Test interaction between multiple components
- May use database or external services
- Slower execution (1-10 seconds each)
- Example: Testing data loading pipelines, API integrations

**Website Tests** (`@pytest.mark.website`):
- Test web routes, views, and user interactions
- Use Flask test client to simulate HTTP requests
- Test both successful and error responses
- Example: Testing if routes return correct status codes and content

**Database Tests** (`@pytest.mark.db`):
- Test database operations and data persistence
- Use test database with clean fixtures
- Test CRUD operations and complex queries
- Example: Testing model creation, relationships, data integrity

### 2. Basic Test Structure

Create or edit files in [tests/](../../tests/):

```python
import pytest
import json

class TestMyFunctionality:
    """Tests for my new functionality."""
    
    @pytest.mark.unit
    def test_utility_function(self):
        """Test a utility function (no dependencies)."""
        from conekt.utils.sequence import translate_dna
        result = translate_dna("ATG")
        assert result == "M"
    
    @pytest.mark.website
    def test_basic_route(self, client):
        """Test if route responds correctly."""
        response = client.get("/my_route")
        assert response.status_code == 200
        assert b"expected_text" in response.data
    
    @pytest.mark.db
    def test_with_database_data(self, client, test_species):
        """Test functionality using database data."""
        response = client.get(f"/species/{test_species.id}")
        assert response.status_code == 200
        assert test_species.name.encode() in response.data
    
    @pytest.mark.integration 
    def test_data_pipeline(self, database, test_sequences):
        """Test complete data processing pipeline."""
        from conekt.scripts.build import process_sequences
        
        # Process test data
        result = process_sequences(test_sequences)
        
        # Verify results in database
        assert database.session.query(ProcessedSequence).count() > 0
        processed = database.session.query(ProcessedSequence).first()
        assert processed.status == 'completed'
```

### 3. Choosing the Right Test Type

**When to use Unit Tests:**
- Testing utility functions (sequence parsing, data validation)
- Testing model methods (calculations, formatting)
- Testing business logic without external dependencies
- When you need fast feedback during development

**When to use Website Tests:**
- Testing route responses and status codes
- Testing template rendering and content
- Testing form submissions and validation
- Testing authentication and authorization

**When to use Database Tests:**
- Testing model creation and relationships  
- Testing complex database queries
- Testing data integrity constraints
- Testing data loading and migration scripts

**When to use Integration Tests:**
- Testing complete workflows (data import → processing → export)
- Testing API interactions between components
- Testing system behavior with real-like scenarios
- Testing performance of complex operations

### 4. Using Existing Fixtures

**Available fixtures** (defined in [tests/conftest.py](../../tests/conftest.py)):

| Fixture | Description | Usage |
|---------|-------------|-------|
| `client` | Flask client for route testing | `def test_route(self, client)` |
| `database` | Clean database for each test | `def test_db(self, database)` |
| `test_species` | Test species | `def test_species_func(self, test_species)` |
| `test_sequences` | Test sequences | `def test_seq_func(self, test_sequences)` |
| `full_test_data` | Complete test data set | `def test_full(self, full_test_data)` |

### 5. Adding Markers and Organization

Use markers to categorize your tests:

```python
@pytest.mark.unit           # Fast unit test
@pytest.mark.website        # Web route test
@pytest.mark.db             # Database test
@pytest.mark.slow           # Time-consuming test
@pytest.mark.integration    # Integration test
def test_my_functionality(self, client):
    # your test here
    pass
```

**Test File Organization:**
- `tests/unit_test.py` - Unit tests for utilities and models
- `tests/website_test.py` - Web route and view tests (existing)
- `tests/build_test.py` - Data loading and build tests (existing)
- `tests/integration_test.py` - Integration and workflow tests

## Creating Synthetic Data for Tests

### 1. Test Data Structure

Synthetic data is stored in [tests/data/](../../tests/data/):

```
tests/data/
├── test_sequences.fasta        # FASTA test sequences
├── test_te_classes.txt         # Transposable element classes
├── test_tedistills.txt         # TEdistill data
└── README_test_data.md         # Data documentation
```

### 2. Creating New Test Data

**Example: Creating data for a new functionality**

1. **Create data file**:
```bash
# tests/data/test_my_functionality.txt
# Description: Data to test my functionality
# Format: ID	Name	Description	Value
FUNC_001	FunctionA	First function	100
FUNC_002	FunctionB	Second function	200
```

2. **Create fixture to load data**:
```python
# In tests/conftest.py
@pytest.fixture
def test_my_functionality(database):
    """Load test data for my functionality."""
    data_file = 'tests/data/test_my_functionality.txt'
    
    with open(data_file, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.strip().split('\t')
            obj = MyFunctionality(parts[0], parts[1], parts[2], int(parts[3]))
            database.session.add(obj)
    
    database.session.commit()
    return MyFunctionality.query.all()
```

### 3. Supported Data Types

| Type | Format | Example |
|------|--------|---------|
| Sequences | FASTA | `test_sequences.fasta` |
| Tabular data | TSV | `test_te_classes.txt` |
| Hierarchies | Nested TSV | `test_ontology.txt` |
| Relations | TSV with IDs | `test_associations.txt` |

### 4. Step by Step Guide for Adding Test Data

**To create test data for new functionality:**

1. **Identify data type needed** (sequences, annotations, hierarchies)
2. **Create data file** in `tests/data/` following established formats
3. **Document format** with comments at file beginning
4. **Create fixture** in `conftest.py` to load data
5. **Use fixture** in your tests

## Fixtures and Test Data System

### Understanding the Fixture System

**Main file**: [tests/conftest.py](../../tests/conftest.py)
- Contains all fixtures shared between tests
- Manages test database lifecycle  
- Provides synthetic data consistently
- Makes fixtures automatically available to all tests

**How fixtures work:**
1. **Automatic injection**: Just add fixture name as parameter to your test function
2. **Dependency resolution**: Fixtures can depend on other fixtures
3. **Scope management**: Control when fixtures are created and destroyed
4. **Data isolation**: Each test gets clean, predictable data

### Fixture Scopes

1. **Session**: Created once per test session
   - `app` - Flask application configured for tests
   - `_db` - Database instance

2. **Function**: Created for each test (default)
   - `database` - Clean database for each test
   - `client` - HTTP client for route tests

### Creating Your Own Fixtures

**Simple fixture example:**
```python
@pytest.fixture
def my_test_data():
    """Simple data fixture."""
    return {"key": "value", "number": 42}

def test_using_simple_fixture(my_test_data):
    assert my_test_data["key"] == "value"
```

**Database fixture example:**
```python
@pytest.fixture
def my_new_fixture(database, test_species):
    """Create specific data for my test."""
    obj = MyModel()
    obj.species_id = test_species.id
    obj.name = 'Test Object'
    database.session.add(obj)
    database.session.commit()
    return obj

def test_with_my_fixture(my_new_fixture):
    assert my_new_fixture.name == 'Test Object'
```

**Complex fixture with multiple objects:**
```python
@pytest.fixture 
def complex_test_scenario(database, test_species):
    """Create a complete test scenario."""
    # Create multiple related objects
    sequence = Sequence(name="TEST_SEQ", species_id=test_species.id)
    go_term = GO(label="GO:0008150", name="biological_process")
    
    database.session.add(sequence)
    database.session.add(go_term) 
    
    # Create relationship
    sequence.go_labels.append(go_term)
    database.session.commit()
    
    return {
        'sequence': sequence,
        'go_term': go_term,
        'species': test_species
    }
```

## Configuration Files and Test System

### pytest.ini
**Location**: [tests/pytest.ini](../../tests/pytest.ini)

**What it is**: Main pytest configuration file that controls how tests are executed.

**What it does**: 
- Defines where tests are located (`testpaths`)
- Configures test discovery patterns (file names, classes, functions)
- Defines custom markers for categorization
- Establishes default execution options

**How it's useful in development**: Allows running pytest from anywhere in project with consistent behavior.

### conftest.py
**Location**: [tests/conftest.py](../../tests/conftest.py)

**What it is**: Special pytest file containing shared fixtures.

**What it does**: 
- Configures Flask application for tests
- Manages test database lifecycle
- Provides synthetic data through fixtures
- Makes fixtures automatically available to all tests

**How it's useful in development**: Avoids code duplication between tests and ensures consistent environment.

### config.py
**Location**: [tests/config.py](../../tests/config.py)

**What it is**: Test-specific configuration.

**What it does**: 
- Test database connection string
- Disables CSRF to facilitate testing
- Configures DEBUG mode and other test options
- Isolates test configuration from production configuration

**How it's useful in development**: Allows testing without affecting production data and with test-optimized configurations.