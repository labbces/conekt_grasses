"""
Configuração de fixtures do pytest para os testes da aplicação CoNekT.

Este arquivo contém fixtures compartilhadas por todos os testes.
"""
import os
import sys
import tempfile
import json
import pytest

# Adiciona o diretório CoNekT ao path
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
from conekt.models.tr import TranscriptionRegulator
from conekt.models.relationships.sequence_tr import SequenceTRAssociation
from conekt.models.relationships.sequence_tr_domain import SequenceTRDomainAssociation


@pytest.fixture(scope='session')
def app():
    """
    Cria a aplicação Flask com configuração de teste.
    
    Esta fixture é criada uma vez por sessão de teste.
    """
    app = create_app(config)
    
    yield app


@pytest.fixture(scope='session')
def _db(app):
    """
    Cria o banco de dados de teste.
    
    Esta fixture é criada uma vez por sessão de teste.
    """
    with app.app_context():
        # Remove todas as tabelas antigas
        db.session.remove()
        db.drop_all()
        
        # Cria todas as tabelas
        db.create_all()
        yield db
        # Remove todas as tabelas após os testes
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def database(app, _db):
    """
    Fornece uma sessão de banco de dados limpa para cada teste.
    
    Esta fixture é executada antes de cada função de teste.
    """
    with app.app_context():
        yield _db
        
        # Limpa a sessão após cada teste
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
    Fornece um cliente de teste Flask.
    
    Esta fixture pode ser usada para fazer requisições HTTP de teste.
    """
    return app.test_client()


@pytest.fixture
def runner(app):
    """
    Fornece um runner CLI para testar comandos Flask.
    """
    return app.test_cli_runner()


@pytest.fixture
def test_species(database):
    """
    Cria uma espécie de teste no banco de dados.
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
    Cria uma sequência de teste associada à espécie de teste.
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
    Cria um domínio InterPro de teste.
    """
    interpro = Interpro('IPR_TEST', 'Test label')
    database.session.add(interpro)
    database.session.commit()
    return interpro


@pytest.fixture
def test_go(database):
    """
    Cria um termo GO de teste.
    """
    go = GO('GO:TEST', 'test_process', 'biological_process', 'Test label', 0, None, None)
    database.session.add(go)
    database.session.commit()
    return go


@pytest.fixture
def test_gene_family(database):
    """
    Cria uma família gênica de teste com método associado.
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
    Cria um método de classificação de TE de teste.
    """
    method = TEClassMethod('test_te_class_method')
    database.session.add(method)
    database.session.commit()
    return method


@pytest.fixture
def test_te_class(database, test_te_class_method):
    """
    Cria uma classe de TE de teste.
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
    Cria um método de TEdistill de teste.
    """
    method = TEdistillMethod('test_tedistill_method')
    database.session.add(method)
    database.session.commit()
    return method


@pytest.fixture
def test_tedistill(database, test_tedistill_method):
    """
    Cria um TEdistill de teste.
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
    Cria um CAZyme de teste com sequências associadas.
    """
    cazyme = CAZYme('GH1', 'Glycoside Hydrolase', 'beta-glucosidase')
    cazyme.description = 'Test CAZyme family GH1'
    database.session.add(cazyme)
    database.session.commit()
    
    # Associa a sequência ao CAZyme
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
def test_tr(database):
    """Cria um Transcription Regulator de teste."""
    tr = TranscriptionRegulator(
        family="bZIP",
        type="TFF",
        description="Basic leucine zipper TF"
    )
    database.session.add(tr)
    database.session.commit()
    return tr

@pytest.fixture
def test_sequence_tr(database, test_sequence, test_tr):
    """Associa uma sequência a um TR."""
    assoc = SequenceTRAssociation(
        sequence_id=test_sequence.id,
        tr_id=test_tr.id,
        query_start=100,
        query_end=200
    )
    database.session.add(assoc)
    database.session.commit()
    return assoc

@pytest.fixture
def test_sequence_tr_domain(database, test_sequence):
    """Cria domínio TR associado à sequência."""
    domain = SequenceTRDomainAssociation(
        sequence_id=test_sequence.id,
        domain="bZIP_1",
        query_start=120,
        query_end=190
    )
    database.session.add(domain)
    database.session.commit()
    return domain

@pytest.fixture
def full_test_data(database, test_species, test_sequence, test_interpro, test_go, test_gene_family):
    """
    Cria um conjunto completo de dados de teste inter-relacionados.
    
    Esta fixture é útil para testes de integração que precisam de múltiplos objetos relacionados.
    """
    # Associa dados à sequência
    test_sequence.families.append(test_gene_family)
    test_sequence.interpro_domains.append(test_interpro)
    test_sequence.go_labels.append(test_go)
    
    # Cria mais sequências
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
    
    # Cria sequências de TE adicionais para testes específicos
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
    
    # Cria método e classes de TE
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
    
    # Associa TEs às classes
    te_assoc1 = SequenceTEClassAssociation()
    te_assoc1.sequence_id = test_te_sequence.id
    te_assoc1.te_class_id = te_class1.id
    
    te_assoc2 = SequenceTEClassAssociation()
    te_assoc2.sequence_id = test_te_sequence2.id
    te_assoc2.te_class_id = te_class2.id
    
    database.session.add_all([te_assoc1, te_assoc2])
    database.session.commit()
    
    # Cria método e TEdistills
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
    
    # Associa sequências aos TEdistills
    ted_assoc1 = SequenceTEdistillAssociation()
    ted_assoc1.sequence_id = test_te_sequence.id
    ted_assoc1.tedistill_id = tedistill1.id
    
    ted_assoc2 = SequenceTEdistillAssociation()
    ted_assoc2.sequence_id = test_te_sequence2.id
    ted_assoc2.tedistill_id = tedistill2.id
    
    database.session.add_all([ted_assoc1, ted_assoc2])
    database.session.commit()
    
    # Associa TEdistills a TEClasses
    tedistill1.te_classes.append(te_class1)
    tedistill2.te_classes.append(te_class2)
    database.session.commit()
    
    # Cria perfis de expressão
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
    
    # Cria método de rede de expressão
    network_method = ExpressionNetworkMethod(
        test_species.id,
        'Test network method'
    )
    network_method.pcc_cutoff = 0.0
    network_method.hrr_cutoff = 100
    network_method.enable_second_level = 0
    database.session.add(network_method)
    database.session.commit()
    
    # Cria redes de expressão
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
    # Mapeia gene_name -> Sequence
    seq_by_name = {
        s.name: s for s in [test_sequence, test_sequence2, test_sequence3]
    }

    # Dados equivalentes ao test_tr.txt
    tr_test_data = [
        ("Sevir.3G017300.1.p", "ABI3VP1", "TFF", "B3", 295, 390),
        ("Sevir.6G217800.1.p", "AP2-EREBP", "TFF", "AP2", 35, 78),
        ("Sevir.9G197900.1.p", "SET", "OTR", "SET", 228, 517),
        ("Sevir.5G326450.1.p", "bZIP", "TFF", "bZIP_1", 147, 192),
        ("Sevir.5G326450.1.p", "bZIP", "TFF", "bZIP_2", 145, 194),
        ("Sevir.5G326450.1.p", "bZIP", "TFF", "bZIP_Maf", 140, 202),
    ]

    tr_by_family = {}

    for gene, family, tr_type, domain, qstart, qend in tr_test_data:
        # cria TR se não existir
        if family not in tr_by_family:
            tr = TranscriptionRegulator(
                family=family,
                type=tr_type,
                description=f"{family} transcription regulator"
            )
            database.session.add(tr)
            database.session.commit()
            tr_by_family[family] = tr
        else:
            tr = tr_by_family[family]

        # usa TEST_SEQ_01 como gene "mock"
        seq = test_sequence

        # associação TR ↔ Sequence
        tr_assoc = SequenceTRAssociation(
            sequence_id=seq.id,
            tr_id=tr.id,
            query_start=qstart,
            query_end=qend
        )
        database.session.add(tr_assoc)
        database.session.commit()

        # associação de domínio
        domain_assoc = SequenceTRDomainAssociation(
            sequence_id=seq.id,
            domain=domain,
            query_start=qstart,
            query_end=qend
        )
        database.session.add(domain_assoc)

    database.session.commit()
    
    # Cria método de clustering
    cluster_method = CoexpressionClusteringMethod()
    cluster_method.network_method_id = network_method.id
    cluster_method.method = 'test clustering method'
    database.session.add(cluster_method)
    database.session.commit()
    
    # Cria cluster
    cluster = CoexpressionCluster()
    cluster.method_id = cluster_method.id
    cluster.name = 'TEST_COEXP_CLUSTER'
    database.session.add(cluster)
    database.session.commit()
    
    # Associa sequências ao cluster
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
    
    # Cria clade
    clade = Clade('test', ['tst'], '(test:0.01);')
    database.session.add(clade)
    database.session.commit()
    
    clade.families.append(test_gene_family)
    clade.interpro.append(test_interpro)
    database.session.commit()
    
    # Cria ECC
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
    
    # Calcula especificidade (requer dados mais complexos)
    # ExpressionSpecificityMethod.calculate_specificities(
    #     test_species.id,
    #     'Specificity description'
    # )
    
    # Atualiza contadores
    test_species.update_counts()
    
    # Cria CAZyme
    cazyme = CAZYme('GH1', 'Glycoside Hydrolase', 'beta-glucosidase')
    cazyme.description = 'Test CAZyme family GH1'
    database.session.add(cazyme)
    database.session.commit()
    
    # Associa sequências ao CAZyme
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
        'networks': [test_network, test_network2],
        'cluster_method': cluster_method,
        'cluster': cluster,
        'clade': clade,
        'ecc': ecc,
        'trs': list(tr_by_family.values())
    }


@pytest.fixture
def authenticated_client(client, admin_user):
    """
    Fornece um cliente autenticado como administrador.
    
    Útil para testar rotas que requerem autenticação.
    """
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user.id
        sess['_fresh'] = True
    
    return client


def pytest_configure(config):
    """
    Configuração executada antes dos testes começarem.
    """
    # Registra marcadores personalizados
    config.addinivalue_line(
        "markers", "unit: Marca um teste como teste unitário"
    )
    config.addinivalue_line(
        "markers", "integration: Marca um teste como teste de integração"
    )
    config.addinivalue_line(
        "markers", "slow: Marca testes que demoram mais tempo"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modifica itens de teste coletados.
    
    Adiciona marcadores automáticos baseados em condições.
    """
    from tests.config import LOGIN_ENABLED, BLAST_ENABLED
    
    skip_login = pytest.mark.skip(reason="LOGIN não está habilitado")
    skip_blast = pytest.mark.skip(reason="BLAST não está habilitado")
    
    for item in items:
        # Pula testes que requerem LOGIN se não estiver habilitado
        if "login_required" in item.keywords and not LOGIN_ENABLED:
            item.add_marker(skip_login)
        
        # Pula testes que requerem BLAST se não estiver habilitado
        if "blast" in item.keywords and not BLAST_ENABLED:
            item.add_marker(skip_blast)
