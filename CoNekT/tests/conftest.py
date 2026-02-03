"""
Pytest fixture configuration for CoNekT application tests.

This file contains fixtures shared by all tests.
"""
import os
import sys
import tempfile
import json
import pytest

# Add CoNekT directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from conekt import create_app, db
from . import config
from conekt.models.species import Species
from conekt.models.sequences import Sequence
from conekt.models.interpro import Interpro
from conekt.models.go import GO
from conekt.models.gene_families import GeneFamily, GeneFamilyMethod
from conekt.models.expression.profiles import ExpressionProfile
from conekt.models.expression.coexpression_clusters import (
    CoexpressionCluster,
    CoexpressionClusteringMethod,
)
from conekt.models.expression.networks import (
    ExpressionNetwork,
    ExpressionNetworkMethod,
)
from conekt.models.relationships.sequence_sequence_ecc import (
    SequenceSequenceECCAssociation,
)
from conekt.models.relationships.sequence_cluster import (
    SequenceCoexpressionClusterAssociation,
)
from conekt.models.expression.specificity import ExpressionSpecificityMethod
from conekt.models.clades import Clade
from conekt.models.te_classes import TEClass, TEClassMethod
from conekt.models.tedistills import TEdistill, TEdistillMethod
from conekt.models.cazyme import CAZYme
from conekt.models.relationships.sequence_te_class import SequenceTEClassAssociation
from conekt.models.relationships.sequence_tedistill import SequenceTEdistillAssociation
from conekt.models.relationships.sequence_cazyme import SequenceCAZYmeAssociation


@pytest.fixture(scope='session')
def app():
    """
    Creates the Flask application with test configuration.
    
    This fixture is created once per test session.
    """
    app = create_app(config)
    
    yield app


@pytest.fixture(scope='session')
def _db(app):
    """
    Creates the test database.
    
    This fixture is created once per test session.
    """
    with app.app_context():
        # Remove all old tables
        db.session.remove()
        db.drop_all()
        
        # Create all tables
        db.create_all()
        yield db
        # Remove all tables after tests
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def database(app, _db):
    """
    Provides a clean database session for each test.
    
    This fixture is executed before each test function.
    """
    with app.app_context():
        yield _db
        
        # Clean session after each test
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            try:
                _db.session.execute(f"DELETE FROM {table.name}")
            except Exception:
                pass
        _db.session.commit()


@pytest.fixture
def client(app, _db):
    """
    Provides a Flask test client.
    
    This fixture can be used to make HTTP test requests.
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """
    Provides a CLI runner for testing Flask commands.
    """
    return app.test_cli_runner()


@pytest.fixture
def test_species(database):
    """
    Creates a test species in the database.
    """
    species = Species('tst', 'Unittest species')
    species.sequence_count = 0
    species.non_coding_seq_count = 0
    species.te_count = 0
    species.network_count = 0
    species.profile_count = 0
    database.session.add(species)
    database.session.commit()
    return species


@pytest.fixture
def test_sequence(database, test_species):
    """
    Creates a test sequence associated with the test species.
    """
    sequence = Sequence(
        test_species.id,
        'TEST_SEQ_01',
        'ATG',
        description='test sequence'
    )
    database.session.add(sequence)
    database.session.commit()
    return sequence


@pytest.fixture
def test_interpro(database):
    """
    Creates a test InterPro domain.
    """
    interpro = Interpro('IPR_TEST', 'Test label')
    database.session.add(interpro)
    database.session.commit()
    return interpro


@pytest.fixture
def test_go(database):
    """
    Creates a test GO term.
    """
    go = GO('GO:TEST', 'test_process', 'biological_process', 'Test label', 0, None, None)
    database.session.add(go)
    database.session.commit()
    return go


@pytest.fixture
def test_gene_family(database):
    """
    Creates a test gene family with associated method.
    """
    method = GeneFamilyMethod('test_gf_method')
    database.session.add(method)
    database.session.commit()
    
    family = GeneFamily('test_gf')
    family.method_id = method.id
    database.session.add(family)
    database.session.commit()
    
    return family


@pytest.fixture
def test_te_class_method(database):
    """
    Creates a test TE classification method.
    """
    method = TEClassMethod('test_te_class_method')
    database.session.add(method)
    database.session.commit()
    return method


@pytest.fixture
def test_te_class(database, test_te_class_method):
    """
    Creates a test TE class.
    """
    te_class = TEClass('TEST_TE_CLASS_01')
    te_class.method_id = test_te_class_method.id
    te_class.level1 = 'Class I'
    te_class.level2 = 'LTR'
    te_class.level3 = 'Copia'
    database.session.add(te_class)
    database.session.commit()
    return te_class


@pytest.fixture
def test_tedistill_method(database):
    """
    Creates a test TEdistill method.
    """
    method = TEdistillMethod('test_tedistill_method')
    database.session.add(method)
    database.session.commit()
    return method


@pytest.fixture
def test_tedistill(database, test_tedistill_method):
    """
    Creates a test TEdistill.
    """
    tedistill = TEdistill('TEST_TEDISTILL_01')
    tedistill.method_id = test_tedistill_method.id
    tedistill.representative_sequence = 'ATGCGATCGATCGATCGATCGATCGATCG'
    tedistill.original_name = 'TED_ORIG_001'
    database.session.add(tedistill)
    database.session.commit()
    return tedistill


@pytest.fixture
def test_cazyme(database, test_species, test_sequence):
    """
    Creates a test CAZyme with associated sequences.
    """
    cazyme = CAZYme('GH1', 'Glycoside Hydrolase', 'beta-glucosidase')
    cazyme.description = 'Test CAZyme family GH1'
    database.session.add(cazyme)
    database.session.commit()
    
    # Associate sequence with CAZyme
    assoc = SequenceCAZYmeAssociation(
        sequence_id=test_sequence.id,
        cazyme_id=cazyme.id,
        hmm_length=100,
        query_length=300,
        e_value='1e-10',
        query_start=1,
        query_end=300
    )
    database.session.add(assoc)
    database.session.commit()
    
    return cazyme


@pytest.fixture
def full_test_data(database, test_species, test_sequence, test_interpro, test_go, test_gene_family):
    """
    Creates a complete set of interrelated test data.
    
    This fixture is useful for integration tests that need multiple related objects.
    """
    # Associate data with sequence
    test_sequence.families.append(test_gene_family)
    test_sequence.interpro_domains.append(test_interpro)
    test_sequence.go_labels.append(test_go)
    
    # Create more sequences
    test_sequence2 = Sequence(
        test_species.id,
        'TEST_SEQ_02',
        'ATG',
        description='test sequence 2'
    )
    test_sequence3 = Sequence(
        test_species.id,
        'TEST_SEQ_03',
        'ATG',
        description='test sequence 3'
    )
    test_sequence3.type = 'TE'
    
    # Create additional TE sequences for specific tests
    test_te_sequence = Sequence(
        test_species.id,
        'TEST_TE_SEQ_01',
        'ATGCGATCGATCGATCGATCGATCGATCGTAG',
        description='test TE sequence 1'
    )
    test_te_sequence.type = 'TE'
    
    test_te_sequence2 = Sequence(
        test_species.id,
        'TEST_TE_SEQ_02',
        'ATGAAACCCGGGTTTAAACCCGGGTAG',
        description='test TE sequence 2'
    )
    test_te_sequence2.type = 'TE'
    
    database.session.add_all([test_sequence2, test_sequence3, test_te_sequence, test_te_sequence2])
    database.session.commit()
    
    # Create method and TE classes
    te_class_method = TEClassMethod('test_te_class_method')
    database.session.add(te_class_method)
    database.session.commit()
    
    te_class1 = TEClass('TEST_TE_CLASS_01')
    te_class1.method_id = te_class_method.id
    te_class1.level1 = 'Class I'
    te_class1.level2 = 'LTR'
    te_class1.level3 = 'Copia'
    
    te_class2 = TEClass('TEST_TE_CLASS_02')
    te_class2.method_id = te_class_method.id
    te_class2.level1 = 'Class II'
    te_class2.level2 = 'DNA'
    te_class2.level3 = 'MULE'
    
    database.session.add_all([te_class1, te_class2])
    database.session.commit()
    
    # Associate TEs with classes
    te_assoc1 = SequenceTEClassAssociation()
    te_assoc1.sequence_id = test_te_sequence.id
    te_assoc1.te_class_id = te_class1.id
    
    te_assoc2 = SequenceTEClassAssociation()
    te_assoc2.sequence_id = test_te_sequence2.id
    te_assoc2.te_class_id = te_class2.id
    
    database.session.add_all([te_assoc1, te_assoc2])
    database.session.commit()
    
    # Create method and TEdistills
    tedistill_method = TEdistillMethod('test_tedistill_method')
    database.session.add(tedistill_method)
    database.session.commit()
    
    tedistill1 = TEdistill('TEST_TEDISTILL_01')
    tedistill1.method_id = tedistill_method.id
    tedistill1.representative_sequence = 'ATGCGATCGATCGATCGATCGATCGATCG'
    tedistill1.original_name = 'TED_ORIG_001'
    
    tedistill2 = TEdistill('TEST_TEDISTILL_02')
    tedistill2.method_id = tedistill_method.id
    tedistill2.representative_sequence = 'ATGAAACCCGGGTTTAAACCCGGG'
    tedistill2.original_name = 'TED_ORIG_002'
    
    database.session.add_all([tedistill1, tedistill2])
    database.session.commit()
    
    # Associate sequences with TEdistills
    ted_assoc1 = SequenceTEdistillAssociation()
    ted_assoc1.sequence_id = test_te_sequence.id
    ted_assoc1.tedistill_id = tedistill1.id
    
    ted_assoc2 = SequenceTEdistillAssociation()
    ted_assoc2.sequence_id = test_te_sequence2.id
    ted_assoc2.tedistill_id = tedistill2.id
    
    database.session.add_all([ted_assoc1, ted_assoc2])
    database.session.commit()
    
    # Associate TEdistills with TEClasses
    tedistill1.te_classes.append(te_class1)
    tedistill2.te_classes.append(te_class2)
    database.session.commit()
    
    # Create expression profiles
    profile_data = json.dumps({
        "data": {
            "tpm": {
                "Tissue 01": 29.0,
                "Tissue 02": 49000.0
            },
            "annotation": {
                "Tissue 01": "seedling - hypocotyl 17d",
                "Tissue 02": "root 21d"
            },
            "po_anatomy_class": {
                "Tissue 01": "Tissue 01",
                "Tissue 02": "Tissue 02"
            },
            "lit_doi": {
                "Tissue 01": "doi1",
                "Tissue 02": "doi2"
            }
        },
        "order": ["Tissue 01", "Tissue 02"]
    })
    
    test_profile = ExpressionProfile(
        'test_probe',
        test_sequence.id,
        profile_data
    )
    test_profile.species_id = test_species.id
    
    profile_data2 = json.dumps({
        "data": {
            "tpm": {
                "Tissue 01": 49.0,
                "Tissue 02": 49.0
            },
            "annotation": {
                "Tissue 01": "seedling - hypocotyl 17d",
                "Tissue 02": "root 21d"
            },
            "po_anatomy_class": {
                "Tissue 01": "Tissue 01",
                "Tissue 02": "Tissue 02"
            },
            "lit_doi": {
                "Tissue 01": "doi1",
                "Tissue 02": "doi2"
            }
        },
        "order": ["Tissue 01", "Tissue 02"]
    })
    
    test_profile2 = ExpressionProfile(
        'test_probe2',
        test_sequence2.id,
        profile_data2
    )
    test_profile2.species_id = test_species.id
    
    database.session.add_all([test_profile, test_profile2])
    database.session.commit()
    
    # Create expression network method
    network_method = ExpressionNetworkMethod(
        test_species.id,
        'Test network method'
    )
    network_method.pcc_cutoff = 0.0
    network_method.hrr_cutoff = 100
    network_method.enable_second_level = 0
    database.session.add(network_method)
    database.session.commit()
    
    # Create expression networks
    test_network = ExpressionNetwork(
        test_profile.probe,
        test_sequence.id,
        f'[{{"gene_name": "TEST_SEQ_02", "gene_id": {test_sequence2.id}, "probe_name": "test_probe2", "link_score": 0, "hrr":0}}]',
        network_method.id
    )
    
    test_network2 = ExpressionNetwork(
        test_profile2.probe,
        test_sequence2.id,
        f'[{{"gene_name": "TEST_SEQ_01", "gene_id": {test_sequence.id}, "probe_name": "test_probe", "link_score": 0, "hrr":0}}]',
        network_method.id
    )
    
    database.session.add_all([test_network, test_network2])
    database.session.commit()
    
    # Create clustering method
    cluster_method = CoexpressionClusteringMethod()
    cluster_method.network_method_id = network_method.id
    cluster_method.method = 'test clustering method'
    database.session.add(cluster_method)
    database.session.commit()
    
    # Create cluster
    cluster = CoexpressionCluster()
    cluster.method_id = cluster_method.id
    cluster.name = 'TEST_COEXP_CLUSTER'
    database.session.add(cluster)
    database.session.commit()
    
    # Associate sequences with cluster
    assoc1 = SequenceCoexpressionClusterAssociation()
    assoc1.probe = test_profile.probe
    assoc1.sequence_id = test_sequence.id
    assoc1.coexpression_cluster_id = cluster.id
    
    assoc2 = SequenceCoexpressionClusterAssociation()
    assoc2.probe = test_profile2.probe
    assoc2.sequence_id = test_sequence2.id
    assoc2.coexpression_cluster_id = cluster.id
    
    database.session.add_all([assoc1, assoc2])
    database.session.commit()
    
    # Create clade
    clade = Clade('test', ['tst'], '(test:0.01);')
    database.session.add(clade)
    database.session.commit()
    
    clade.families.append(test_gene_family)
    clade.interpro.append(test_interpro)
    database.session.commit()
    
    # Create ECC
    ecc = SequenceSequenceECCAssociation()
    ecc.query_id = test_sequence.id
    ecc.target_id = test_sequence2.id
    ecc.gene_family_method_id = test_gene_family.method_id
    ecc.query_network_method_id = network_method.id
    ecc.target_network_method_id = network_method.id
    ecc.ecc = 0.5
    ecc.p_value = 0.05
    ecc.corrected_p_value = 0.05
    database.session.add(ecc)
    database.session.commit()
    
    # Calculate specificity (requires more complex data)
    # ExpressionSpecificityMethod.calculate_specificities(
    #     test_species.id,
    #     'Specificity description'
    # )
    
    # Update counters
    test_species.update_counts()
    
    # Create CAZyme
    cazyme = CAZYme('GH1', 'Glycoside Hydrolase', 'beta-glucosidase')
    cazyme.description = 'Test CAZyme family GH1'
    database.session.add(cazyme)
    database.session.commit()
    
    # Associate sequences with CAZyme
    cazyme_assoc1 = SequenceCAZYmeAssociation(
        sequence_id=test_sequence.id,
        cazyme_id=cazyme.id,
        hmm_length=100,
        query_length=300,
        e_value='1e-10',
        query_start=1,
        query_end=300
    )
    
    cazyme_assoc2 = SequenceCAZYmeAssociation(
        sequence_id=test_sequence2.id,
        cazyme_id=cazyme.id,
        hmm_length=100,
        query_length=280,
        e_value='1e-8',
        query_start=1,
        query_end=280
    )
    
    database.session.add_all([cazyme_assoc1, cazyme_assoc2])
    database.session.commit()
    
    # Create Sequence Ontology terms
    from conekt.models.sequence_ontology import SequenceOntology
    from conekt.models.relationships.te_class_so import TEClassSOAssociation
    
    so_term1 = SequenceOntology(
        so_id='SO:0000657',
        name='repeat_region',
        description='A region of the genome containing one or more repeat elements.',
        namespace='sequence_feature',
        alias='repeat_region'
    )
    
    so_term2 = SequenceOntology(
        so_id='SO:0000182', 
        name='DNA_transposon',
        description='A DNA transposon.',
        namespace='sequence_feature',
        alias='Class_II,DNA_transposon'
    )
    
    database.session.add_all([so_term1, so_term2])
    database.session.commit()
    
    # Associate SO terms with TE classes
    so_assoc1 = TEClassSOAssociation(
        te_class_id=te_class1.id,
        sequence_ontology_id=so_term1.id,
        evidence_code='IEA',
        confidence=1.0,
        source='test_data'
    )
    
    so_assoc2 = TEClassSOAssociation(
        te_class_id=te_class2.id,
        sequence_ontology_id=so_term2.id,
        evidence_code='IEA',
        confidence=1.0,
        source='test_data'
    )
    
    database.session.add_all([so_assoc1, so_assoc2])
    database.session.commit()

    return {
        'species': test_species,
        'sequences': [test_sequence, test_sequence2, test_sequence3],
        'te_sequences': [test_te_sequence, test_te_sequence2],
        'interpro': test_interpro,
        'go': test_go,
        'family': test_gene_family,
        'profiles': [test_profile, test_profile2],
        'te_class_method': te_class_method,
        'te_classes': [te_class1, te_class2],
        'tedistill_method': tedistill_method,
        'tedistills': [tedistill1, tedistill2],
        'cazyme': cazyme,
        'sequence_ontologies': [so_term1, so_term2],
        'networks': [test_network, test_network2],
        'cluster_method': cluster_method,
        'cluster': cluster,
        'clade': clade,
        'ecc': ecc
    }


@pytest.fixture
def authenticated_client(client, admin_user):
    """
    Provides an authenticated client as administrator.
    
    Useful for testing routes that require authentication.
    """
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user.id
        sess['_fresh'] = True
    
    return client


def pytest_configure(config):
    """
    Configuration executed before tests begin.
    """
    # Register custom markers
    config.addinivalue_line(
        "markers", "unit: Mark a test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: Mark a test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: Mark tests that take more time"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modifies collected test items.
    
    Adds automatic markers based on conditions.
    """
    from tests.config import LOGIN_ENABLED, BLAST_ENABLED
    
    skip_login = pytest.mark.skip(reason="LOGIN is not enabled")
    skip_blast = pytest.mark.skip(reason="BLAST is not enabled")
    
    for item in items:
        # Skip tests that require LOGIN if it is not enabled
        if "login_required" in item.keywords and not LOGIN_ENABLED:
            item.add_marker(skip_login)
        
        # Skip tests that require BLAST if it is not enabled
        if "blast" in item.keywords and not BLAST_ENABLED:
            item.add_marker(skip_blast)
