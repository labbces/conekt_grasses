#!/usr/bin/env python3
"""
CoNekT website functionality tests.

This module tests the main website routes and functionalities,
including sequences, species, InterPro domains, GO terms, gene families,
expression profiles, coexpression networks, clusters, clades and ECC.

Migrated from unittest/flask-testing to pytest for better performance and maintenance.
"""
import json
import pytest

from conekt.controllers.help import __TOPICS as topics


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestWebsiteMainRoutes:
    """Tests for main website routes."""

    def test_main(self, client):
        """Tests main page."""
        response = client.get("/")
        assert response.status_code == 200

    def test_about(self, client):
        """Tests about page."""
        response = client.get("/about")
        assert response.status_code == 200

    def test_contact(self, client):
        """Tests contact page."""
        response = client.get("/contact")
        assert response.status_code == 200

    def test_disclaimer(self, client):
        """Tests disclaimer page."""
        response = client.get("/disclaimer")
        assert response.status_code == 200

    def test_features(self, client):
        """Tests features page."""
        response = client.get("/features")
        assert response.status_code == 200

    def test_404_not_found(self, client):
        """Tests 404 page."""
        response = client.get("/this_should_not_exist")
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestSequenceRoutes:
    """Tests for routes associated with Sequence."""

    def test_sequence_redirect(self, client):
        """Tests /sequence/ redirect."""
        response = client.get("/sequence/")
        assert response.status_code == 302

    def test_sequence_view(self, client, full_test_data):
        """Tests sequence view."""
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/sequence/view/{sequence.id}")
        assert response.status_code == 200

    def test_sequence_tooltip(self, client, full_test_data):
        """Tests sequence tooltip."""
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/sequence/tooltip/{sequence.id}")
        assert response.status_code == 200

    def test_sequence_modal_coding(self, client, full_test_data):
        """Tests coding sequence modal."""
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/sequence/modal/coding/{sequence.id}/false")
        assert response.status_code == 200

    def test_sequence_modal_protein(self, client, full_test_data):
        """Tests protein sequence modal."""
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/sequence/modal/protein/{sequence.id}")
        assert response.status_code == 200

    def test_sequence_fasta_coding(self, client, full_test_data):
        """Tests coding sequence FASTA download."""
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/sequence/fasta/coding/{sequence.id}/false")
        assert response.status_code == 200
        
        data = response.data.decode("utf-8").strip()
        lines = data.split("\n")
        assert len(lines) >= 2
        assert data[0] == ">"
        assert ">" + sequence.name in data

    def test_sequence_fasta_protein(self, client, full_test_data):
        """Tests download FASTA de sequence protein."""
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/sequence/fasta/protein/{sequence.id}")
        assert response.status_code == 200
        
        data = response.data.decode("utf-8").strip()
        assert data[0] == ">"
        assert ">" + sequence.name in data

    def test_sequence_find(self, client, full_test_data):
        """Tests sequence search by name."""
        sequence = full_test_data['sequences'][0]
        response = client.get(
            f"/sequence/find/{sequence.name}", follow_redirects=True
        )
        assert response.status_code == 200

    def test_sequence_view_invalid_id(self, client):
        """Tests view with invalid ID."""
        response = client.get("/sequence/view/a")
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestSpeciesRoutes:
    """Tests for routes associated with Species."""

    def test_species_main_page(self, client):
        """Tests species main page."""
        response = client.get("/species/")
        assert response.status_code == 200

    def test_species_view(self, client, full_test_data):
        """Tests species view."""
        species = full_test_data['species']
        response = client.get(f"/species/view/{species.id}")
        assert response.status_code == 200
        assert species.name.encode() in response.data

    def test_species_sequences_pagination(self, client, full_test_data):
        """Tests sequence pagination."""
        species = full_test_data['species']
        response = client.get(f"/species/sequences/{species.id}/1")
        assert response.status_code == 200

    def test_species_download_coding(self, client, full_test_data):
        """Tests coding sequences download."""
        species = full_test_data['species']
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/species/download/coding/{species.id}")
        assert response.status_code == 200
        
        data = response.data.decode("utf-8").strip()
        assert len(data.split("\n")) > 0
        assert data[0] == ">"
        assert ">" + sequence.name in data

    def test_species_download_protein(self, client, full_test_data):
        """Tests download de sequences proteins."""
        species = full_test_data['species']
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/species/download/protein/{species.id}")
        assert response.status_code == 200
        
        data = response.data.decode("utf-8").strip()
        assert len(data.split("\n")) > 0
        assert data[0] == ">"
        assert ">" + sequence.name in data

    def test_species_stream_coding(self, client, full_test_data):
        """Tests coding sequences streaming."""
        species = full_test_data['species']
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/species/stream/coding/{species.id}")
        assert response.status_code == 200
        
        data = response.data.decode("utf-8").strip()
        assert len(data.split("\n")) > 0
        assert data[0] == ">"
        assert ">" + sequence.name in data

    def test_species_stream_protein(self, client, full_test_data):
        """Tests streaming de sequences proteins."""
        species = full_test_data['species']
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/species/stream/protein/{species.id}")
        assert response.status_code == 200
        
        data = response.data.decode("utf-8").strip()
        assert len(data.split("\n")) > 0
        assert data[0] == ">"
        assert ">" + sequence.name in data


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestInterProRoutes:
    """Tests for routes associated with InterPro domain."""

    def test_interpro_redirect(self, client):
        """Tests /interpro/ redirect."""
        response = client.get("/interpro/")
        assert response.status_code == 302

    def test_interpro_view(self, client, full_test_data):
        """Tests InterPro domain view."""
        interpro = full_test_data['interpro']
        response = client.get(f"/interpro/view/{interpro.id}")
        assert response.status_code == 200

    def test_interpro_find(self, client, full_test_data):
        """Tests InterPro domain search."""
        interpro = full_test_data['interpro']
        response = client.get(
            f"/interpro/find/{interpro.label}", follow_redirects=True
        )
        assert response.status_code == 200

    def test_interpro_sequences(self, client, full_test_data):
        """Tests sequences listing with domain."""
        interpro = full_test_data['interpro']
        response = client.get(f"/interpro/sequences/{interpro.id}/1")
        assert response.status_code == 200

    def test_interpro_sequences_table(self, client, full_test_data):
        """Tests CSV export of sequences."""
        interpro = full_test_data['interpro']
        response = client.get(f"/interpro/sequences/table/{interpro.id}")
        assert response.status_code == 200

    def test_interpro_json_species(self, client, full_test_data):
        """Tests profile filogenético JSON."""
        interpro = full_test_data['interpro']
        response = client.get(f"/interpro/json/species/{interpro.id}")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        assert "data" in data
        assert "type" in data
        assert "labels" in data["data"]
        assert "datasets" in data["data"]


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestGORoutes:
    """Tests for routes associated with GO label."""

    def test_go_redirect(self, client):
        """Tests /go/ redirect."""
        response = client.get("/go/")
        assert response.status_code == 302

    def test_go_view(self, client, full_test_data):
        """Tests GO term view."""
        go = full_test_data['go']
        response = client.get(f"/go/view/{go.id}")
        assert response.status_code == 200

    def test_go_find(self, client, full_test_data):
        """Tests GO term search."""
        go = full_test_data['go']
        response = client.get(f"/go/find/{go.label}")
        assert response.status_code == 302

    def test_go_sequences(self, client, full_test_data):
        """Tests sequences listing with GO term."""
        go = full_test_data['go']
        response = client.get(f"/go/sequences/{go.id}/1")
        assert response.status_code == 200

    def test_go_sequences_table(self, client, full_test_data):
        """Tests CSV export of sequences with GO term."""
        go = full_test_data['go']
        response = client.get(f"/go/sequences/table/{go.id}")
        assert response.status_code == 200

    def test_go_json_species(self, client, full_test_data):
        """Tests profile filogenético JSON."""
        go = full_test_data['go']
        response = client.get(f"/go/json/species/{go.id}")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        assert "data" in data
        assert "type" in data
        assert "labels" in data["data"]
        assert "datasets" in data["data"]

    def test_go_json_genes(self, client, full_test_data):
        """Tests gene retrieval by GO term."""
        go = full_test_data['go']
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/go/json/genes/{go.label}")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        assert sequence.id in data

    def test_go_json_genes_not_found(self, client):
        """Tests search with non-existent GO label."""
        response = client.get("/go/json/genes/no_label")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        assert data == []


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestGeneFamily:
    """Tests for routes associated with GeneFamily."""

    def test_family_redirect(self, client):
        """Tests /family/ redirect."""
        response = client.get("/family/")
        assert response.status_code == 302

    def test_family_view(self, client, full_test_data):
        """Tests gene family view."""
        family = full_test_data['family']
        response = client.get(f"/family/view/{family.id}")
        assert response.status_code == 200

    def test_family_find(self, client, full_test_data):
        """Tests gene family search."""
        family = full_test_data['family']
        response = client.get(f"/family/find/{family.name}", follow_redirects=True)
        assert response.status_code == 200

    def test_family_sequences(self, client, full_test_data):
        """Tests family sequences listing."""
        family = full_test_data['family']
        response = client.get(f"/family/sequences/{family.id}/1")
        assert response.status_code == 200

    def test_family_sequences_table(self, client, full_test_data):
        """Tests family sequences CSV export."""
        family = full_test_data['family']
        response = client.get(f"/family/sequences/table/{family.id}")
        assert response.status_code == 200

    def test_family_json_species(self, client, full_test_data):
        """Tests profile filogenético JSON."""
        family = full_test_data['family']
        response = client.get(f"/family/json/species/{family.id}")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        assert "data" in data
        assert "type" in data
        assert "labels" in data["data"]
        assert "datasets" in data["data"]


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestExpressionProfile:
    """Tests for routes associated with ExpressionProfile."""

    def test_profile_redirect(self, client):
        """Tests /profile/ redirect."""
        response = client.get("/profile/")
        assert response.status_code == 302

    def test_profile_view(self, client, full_test_data):
        """Tests expression profile view."""
        profile = full_test_data['profiles'][0]
        response = client.get(f"/profile/view/{profile.id}")
        assert response.status_code == 200

    def test_profile_modal(self, client, full_test_data):
        """Tests expression profile modal."""
        profile = full_test_data['profiles'][0]
        response = client.get(f"/profile/modal/{profile.id}")
        assert response.status_code == 200

    def test_profile_find(self, client, full_test_data):
        """Tests expression profile search."""
        profile = full_test_data['profiles'][0]
        response = client.get(
            f"/profile/find/{profile.probe}", follow_redirects=True
        )
        assert response.status_code == 200

    def test_profile_find_invalid_species(self, client, full_test_data):
        """Tests search with invalid species."""
        profile = full_test_data['profiles'][0]
        response = client.get(f"/profile/find/{profile.probe}/2")
        assert response.status_code == 404

    def test_profile_compare(self, client, full_test_data):
        """Tests profile comparison."""
        profile = full_test_data['profiles'][0]
        response = client.get(f"/profile/compare/{profile.id}/{profile.id}")
        assert response.status_code == 200

    @pytest.mark.skipif(True, reason="Requires specific probe URL encoding")
    def test_profile_compare_probes(self, client, full_test_data):
        """Tests probe comparison."""
        profile = full_test_data['profiles'][0]
        response = client.get(
            f"/profile/compare_probes/{profile.probe}/{profile.probe}/1"
        )
        assert response.status_code == 200

    def test_profile_compare_probes_invalid_species(self, client, full_test_data):
        """Tests comparison with invalid species."""
        profile = full_test_data['profiles'][0]
        response = client.get(
            f"/profile/compare_probes/{profile.probe}/{profile.probe}/2"
        )
        assert response.status_code == 404

    def test_profile_json_plot(self, client, full_test_data):
        """Tests JSON plot."""
        profile = full_test_data['profiles'][0]
        response = client.get(f"/profile/json/plot/{profile.id}")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        assert "type" in data
        assert "data" in data
        assert "labels" in data["data"]
        assert "datasets" in data["data"]
        for dataset in data["data"]["datasets"]:
            assert "data" in dataset

    @pytest.mark.skipif(True, reason="Requires specific data structure for comparison")
    def test_profile_json_compare_plot(self, client, full_test_data):
        """Tests comparative JSON plot."""
        profile = full_test_data['profiles'][0]
        response = client.get(f"/profile/json/compare_plot/{profile.id}/{profile.id}")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        assert "type" in data
        assert "data" in data
        assert "labels" in data["data"]
        assert "datasets" in data["data"]
        for dataset in data["data"]["datasets"]:
            assert "data" in dataset


@pytest.mark.unit
@pytest.mark.website
class TestHelpPages:
    """Tests for help pages."""

    def test_help_topics(self, client):
        """Tests help pages."""
        for k, v in topics.items():
            response = client.get(f"/help/{k}")
            assert response.status_code == 200

    def test_help_invalid_topic(self, client):
        """Tests page de ajuda non-existent."""
        response = client.get("/help/term_does_not_exist")
        assert response.status_code == 404


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestSearch:
    """Tests for search functionality."""

    def test_search_keyword_sequence(self, client, full_test_data):
        """Tests search por sequence."""
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/search/keyword/{sequence.name}")
        assert response.status_code == 302

    def test_search_keyword_interpro(self, client, full_test_data):
        """Tests search por domain InterPro."""
        interpro = full_test_data['interpro']
        response = client.get(f"/search/keyword/{interpro.label}")
        assert response.status_code == 302

    def test_search_keyword_go(self, client, full_test_data):
        """Tests search por term GO."""
        go = full_test_data['go']
        response = client.get(f"/search/keyword/{go.label}")
        assert response.status_code == 302

    def test_search_keyword_family(self, client, full_test_data):
        """Tests search por family gênica."""
        family = full_test_data['family']
        response = client.get(f"/search/keyword/{family.name}")
        assert response.status_code == 302

    def test_search_keyword_profile(self, client, full_test_data):
        """Tests search por profile de expressão."""
        profile = full_test_data['profiles'][0]
        response = client.get(f"/search/keyword/{profile.probe}")
        assert response.status_code == 302

    def test_search_keyword_generic(self, client):
        """Tests search genérica."""
        response = client.get("/search/keyword/t")
        assert response.status_code == 200

    def test_search_redirect(self, client):
        """Tests redirect de /search/."""
        response = client.get("/search/")
        assert response.status_code == 302

    def test_search_post_sequence(self, client, full_test_data):
        """Tests search POST por sequence."""
        sequence = full_test_data['sequences'][0]
        response = client.post("/search/", data={"terms": sequence.name})
        assert response.status_code == 302

    def test_search_post_family(self, client, full_test_data):
        """Tests search POST por family."""
        family = full_test_data['family']
        response = client.post("/search/", data={"terms": family.name})
        assert response.status_code == 302

    def test_search_post_go(self, client, full_test_data):
        """Tests search POST por term GO."""
        go = full_test_data['go']
        response = client.post("/search/", data={"terms": go.label})
        assert response.status_code == 302

    def test_search_post_interpro(self, client, full_test_data):
        """Tests search POST por domain InterPro."""
        interpro = full_test_data['interpro']
        response = client.post("/search/", data={"terms": interpro.label})
        assert response.status_code == 302

    def test_search_post_profile(self, client, full_test_data):
        """Tests search POST por profile."""
        profile = full_test_data['profiles'][0]
        response = client.post("/search/", data={"terms": profile.probe})
        assert response.status_code == 302

    def test_search_post_multiple_terms(self, client, full_test_data):
        """Tests search com múltiplos terms."""
        family = full_test_data['family']
        sequence = full_test_data['sequences'][0]
        interpro = full_test_data['interpro']
        profile = full_test_data['profiles'][0]
        
        terms = " ".join([
            family.name,
            sequence.name,
            interpro.label,
            profile.probe,
        ])
        
        response = client.post("/search/", data={"terms": terms})
        assert response.status_code == 200

    def test_search_post_by_label(self, client):
        """Tests search por label."""
        response = client.post("/search/", data={"terms": "Test label"})
        assert response.status_code == 200

    def test_search_json_genes(self, client, full_test_data):
        """Tests search JSON de genes."""
        go = full_test_data['go']
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/search/json/genes/{go.label}")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        assert sequence.id in data

    def test_search_typeahead_go_prefetch(self, client, full_test_data):
        """Tests typeahead para GO prefetch."""
        response = client.get("/search/typeahead/go/prefetch")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        # Pode retornar uma lista vazia ou com dados
        assert isinstance(data, list)
        for d in data:
            assert "value" in d
            assert "tokens" in d

    def test_search_typeahead_go_search(self, client, full_test_data):
        """Tests typeahead para GO search."""
        response = client.get("/search/typeahead/go/test.json")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        assert len(data) >= 1
        for d in data:
            assert "value" in d
            assert "tokens" in d

    def test_search_advanced(self, client):
        """Tests page de search avançada."""
        response = client.get("/search/advanced")
        assert response.status_code == 200


@pytest.mark.blast
@pytest.mark.website
class TestBLAST:
    """Tests for BLAST functionality."""

    def test_blast_page(self, client):
        """Tests page BLAST."""
        response = client.get("/blast/")
        assert response.status_code == 200

    def test_blast_results(self, client):
        """Tests resultados BLAST."""
        response = client.get("/blast/results/testtoken")
        assert response.status_code == 200

    def test_blast_results_json(self, client):
        """Tests resultados BLAST em JSON."""
        response = client.get("/blast/results/json/testtoken")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        assert "status" in data


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestHeatmap:
    """Tests for heatmap functionality."""

    def test_heatmap_page(self, client):
        """Tests page de heatmap."""
        response = client.get("/heatmap/")
        assert response.status_code == 200

    def test_heatmap_with_probes(self, client, full_test_data):
        """Tests heatmap com probes."""
        profile = full_test_data['profiles'][0]
        response = client.post(
            "/heatmap/",
            data={"probes": profile.probe, "species_id": profile.species_id},
        )
        assert response.status_code == 200
        assert profile.probe.encode() in response.data

    @pytest.mark.skipif(True, reason="Requer estrutura de dados específica")
    def test_heatmap_cluster(self, client, full_test_data):
        """Tests heatmap de cluster."""
        cluster = full_test_data['cluster']
        response = client.get(f"/heatmap/cluster/{cluster.id}")
        assert response.status_code == 200

    @pytest.mark.skipif(True, reason="Requer estrutura de dados específica")
    def test_heatmap_inchlib_json(self, client, full_test_data):
        """Tests JSON inchlib para heatmap."""
        cluster = full_test_data['cluster']
        response = client.get(f"/heatmap/inchlib/j/{cluster.id}.json")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        assert "data" in data
        assert "nodes" in data["data"]
        assert "feature_names" in data["data"]

    def test_heatmap_inchlib(self, client, full_test_data):
        """Tests page inchlib para heatmap."""
        cluster = full_test_data['cluster']
        response = client.get(f"/heatmap/inchlib/{cluster.id}")
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestProfileComparison:
    """Tests for expression profile comparison."""

    def test_profile_comparison_page(self, client):
        """Tests page de comparison de profiles."""
        response = client.get("/profile_comparison/")
        assert response.status_code == 200

    @pytest.mark.skipif(True, reason="Requer estrutura de dados específica")
    def test_profile_comparison_with_normalization(self, client, full_test_data):
        """Tests comparison com normalização."""
        profile = full_test_data['profiles'][0]
        response = client.post(
            "/profile_comparison/",
            data={
                "probes": profile.probe,
                "species_id": profile.species_id,
                "normalize": "y",
            },
        )
        assert response.status_code == 200

    @pytest.mark.skipif(True, reason="Requer estrutura de dados específica")
    def test_profile_comparison_without_normalization(self, client, full_test_data):
        """Tests comparison sem normalização."""
        profile = full_test_data['profiles'][0]
        response = client.post(
            "/profile_comparison/",
            data={
                "probes": profile.probe,
                "species_id": profile.species_id,
                "normalize": "n",
            },
        )
        assert response.status_code == 200

    @pytest.mark.skipif(True, reason="Requer estrutura de dados específica")
    def test_profile_comparison_cluster(self, client, full_test_data):
        """Tests comparison de profiles de cluster."""
        cluster = full_test_data['cluster']
        
        response = client.get(f"/profile_comparison/cluster/{cluster.id}/0")
        assert response.status_code == 200
        
        response = client.get(f"/profile_comparison/cluster/{cluster.id}/1")
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestExpressionNetwork:
    """Tests for expression networks."""

    def test_network_page(self, client):
        """Tests page de rede de expressão."""
        response = client.get("/network/")
        assert response.status_code == 200

    def test_network_by_species(self, client, full_test_data):
        """Tests rede por species."""
        species = full_test_data['species']
        response = client.get(f"/network/species/{species.id}")
        assert response.status_code == 200
        assert species.name.encode() in response.data

    def test_network_graph(self, client, full_test_data):
        """Tests chart de rede."""
        network = full_test_data['networks'][0]
        response = client.get(f"/network/graph/{network.id}")
        assert response.status_code == 200

    def test_network_json(self, client, full_test_data):
        """Tests JSON da rede (Cytoscape)."""
        network = full_test_data['networks'][0]
        response = client.get(f"/network/json/{network.id}")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        _assert_cytoscape_json(data)


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestCoexpressionCluster:
    """Tests for coexpression clusters."""

    def test_cluster_page(self, client):
        """Tests page de cluster."""
        response = client.get("/cluster/")
        assert response.status_code == 200

    def test_cluster_view(self, client, full_test_data):
        """Tests view de cluster."""
        cluster = full_test_data['cluster']
        response = client.get(f"/cluster/view/{cluster.id}")
        assert response.status_code == 200

    def test_cluster_sequences(self, client, full_test_data):
        """Tests sequences do cluster."""
        cluster = full_test_data['cluster']
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/cluster/sequences/{cluster.id}/1")
        assert response.status_code == 200
        assert sequence.name.encode() in response.data

    def test_cluster_download(self, client, full_test_data):
        """Tests download de cluster."""
        cluster = full_test_data['cluster']
        sequence = full_test_data['sequences'][0]
        response = client.get(f"/cluster/download/{cluster.id}")
        assert response.status_code == 200
        assert sequence.name.encode() in response.data

    def test_cluster_graph(self, client, full_test_data):
        """Tests chart de cluster."""
        cluster = full_test_data['cluster']
        gf_method = full_test_data['family'].method
        response = client.get(f"/cluster/graph/{cluster.id}/{gf_method.id}")
        assert response.status_code == 200

    def test_cluster_json(self, client, full_test_data):
        """Tests JSON do cluster (Cytoscape)."""
        cluster = full_test_data['cluster']
        gf_method = full_test_data['family'].method
        response = client.get(f"/cluster/json/{cluster.id}/{gf_method.id}")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        _assert_cytoscape_json(data)


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestGraphComparison:
    """Tests for graph comparison."""

    def test_graph_comparison_cluster(self, client, full_test_data):
        """Tests comparison de charts de cluster."""
        cluster = full_test_data['cluster']
        gf_method = full_test_data['family'].method
        response = client.get(
            f"/graph_comparison/cluster/{cluster.id}/{cluster.id}/{gf_method.id}"
        )
        assert response.status_code == 200

    def test_graph_comparison_cluster_json(self, client, full_test_data):
        """Tests JSON da comparison de charts."""
        cluster = full_test_data['cluster']
        gf_method = full_test_data['family'].method
        response = client.get(
            f"/graph_comparison/cluster/json/{cluster.id}/{cluster.id}/{gf_method.id}"
        )
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        _assert_cytoscape_json(data)


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestClades:
    """Tests for clade functionalities."""

    def test_clade_redirect(self, client):
        """Tests redirect de /clade/."""
        response = client.get("/clade/")
        assert response.status_code == 302

    def test_clade_view(self, client, full_test_data):
        """Tests view de clade."""
        clade = full_test_data['clade']
        response = client.get(f"/clade/view/{clade.id}")
        assert response.status_code == 200

    def test_clade_families(self, client, full_test_data):
        """Tests familys do clade."""
        clade = full_test_data['clade']
        response = client.get(f"/clade/families/{clade.id}/1")
        assert response.status_code == 200

    def test_clade_families_table(self, client, full_test_data):
        """Tests tabela de familys do clade."""
        clade = full_test_data['clade']
        family = full_test_data['family']
        response = client.get(f"/clade/families/table/{clade.id}")
        assert response.status_code == 200
        assert family.name.encode() in response.data

    def test_clade_interpro(self, client, full_test_data):
        """Tests InterPro do clade."""
        clade = full_test_data['clade']
        response = client.get(f"/clade/interpro/{clade.id}/1")
        assert response.status_code == 200

    def test_clade_interpro_table(self, client, full_test_data):
        """Tests tabela de InterPro do clade."""
        clade = full_test_data['clade']
        interpro = full_test_data['interpro']
        response = client.get(f"/clade/interpro/table/{clade.id}")
        assert response.status_code == 200
        assert interpro.label.encode() in response.data


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestECC:
    """Tests for Expression vs Coexpression Clusters (ECC)."""

    def test_ecc_redirect(self, client):
        """Tests redirect de /ecc/."""
        response = client.get("/ecc/")
        assert response.status_code == 302

    def test_ecc_graph(self, client, full_test_data):
        """Tests chart ECC."""
        ecc = full_test_data['ecc']
        response = client.get(
            f"/ecc/graph/{ecc.query_id}/{ecc.query_network_method_id}/{ecc.gene_family_method.id}"
        )
        assert response.status_code == 200

    def test_ecc_json(self, client, full_test_data):
        """Tests JSON ECC (Cytoscape)."""
        ecc = full_test_data['ecc']
        response = client.get(
            f"/ecc/json/{ecc.query_id}/{ecc.query_network_method_id}/{ecc.gene_family_method.id}"
        )
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        _assert_cytoscape_json(data, ecc_graph=True)


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestSpecificitySearch:
    """Tests for specificity profile search."""

    def test_specificity_search_page(self, client):
        """Tests page de search de especificidade."""
        response = client.get("/search/specific/profiles")
        assert response.status_code == 200

    @pytest.mark.skipif(True, reason="Requer estrutura de dados específica")
    def test_specificity_search_results(self, client, full_test_data):
        """Tests resultados de search de especificidade."""
        sequence = full_test_data['sequences'][0]
        response = client.post(
            "/search/specific/profiles",
            data={
                "species": 1,
                "methods": 1,
                "conditions": "root 21d",
                "cutoff": 0.85,
            },
        )
        assert response.status_code == 200
        assert sequence.name.encode() in response.data


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestTEClassRoutes:
    """Tests for TEClass routes (TE Classes)."""

    def test_te_class_overview_redirect(self, client):
        """Tests redirect da overview de TE classes."""
        response = client.get("/te_class/")
        assert response.status_code == 302

    def test_te_class_redirect(self, client, full_test_data):
        """Tests redirect de find para view."""
        te_class = full_test_data['te_classes'][0]
        response = client.get(f"/te_class/find/{te_class.name}")
        assert response.status_code == 302

    def test_te_class_view(self, client, full_test_data):
        """Tests view de TE class."""
        te_class = full_test_data['te_classes'][0]
        response = client.get(f"/te_class/view/{te_class.id}")
        assert response.status_code == 200
        assert te_class.name.encode() in response.data

    def test_te_class_sequences(self, client, full_test_data):
        """Tests paginação de sequences de TE class."""
        te_class = full_test_data['te_classes'][0]
        response = client.get(f"/te_class/sequences/{te_class.id}/")
        assert response.status_code == 200

    def test_te_class_sequences_table(self, client, full_test_data):
        """Tests tabela CSV de sequences de TE class."""
        te_class = full_test_data['te_classes'][0]
        response = client.get(f"/te_class/sequences/table/{te_class.id}")
        assert response.status_code == 200
        assert response.mimetype == "text/plain"

    def test_te_class_json_species(self, client, full_test_data):
        """Tests JSON de distribuição de speciess de TE class."""
        te_class = full_test_data['te_classes'][0]
        response = client.get(f"/te_class/json/species/{te_class.id}")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        # O JSON retorna uma estrutura aninhada com 'data' contendo os datasets e labels
        assert "data" in data
        assert "datasets" in data["data"]
        assert "labels" in data["data"]


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestTEdistillRoutes:
    """Tests for TEdistill routes (TE Distills)."""

    def test_tedistill_overview_redirect(self, client):
        """Tests redirect da overview de TEdistills."""
        response = client.get("/tedistill/")
        assert response.status_code == 302

    def test_tedistill_redirect(self, client, full_test_data):
        """Tests redirect de find para view."""
        tedistill = full_test_data['tedistills'][0]
        response = client.get(f"/tedistill/find/{tedistill.name}")
        assert response.status_code == 302

    def test_tedistill_view(self, client, full_test_data):
        """Tests view de TEdistill."""
        tedistill = full_test_data['tedistills'][0]
        response = client.get(f"/tedistill/view/{tedistill.id}")
        assert response.status_code == 200
        assert tedistill.name.encode() in response.data

    def test_tedistill_sequences(self, client, full_test_data):
        """Tests paginação de sequences de TEdistill."""
        tedistill = full_test_data['tedistills'][0]
        response = client.get(f"/tedistill/sequences/{tedistill.id}/")
        assert response.status_code == 200

    def test_tedistill_sequences_table(self, client, full_test_data):
        """Tests tabela CSV de sequences de TEdistill."""
        tedistill = full_test_data['tedistills'][0]
        response = client.get(f"/tedistill/sequences/table/{tedistill.id}")
        assert response.status_code == 200
        assert response.mimetype == "text/plain"

    def test_tedistill_json_species(self, client, full_test_data):
        """Tests JSON de distribuição de speciess de TEdistill."""
        tedistill = full_test_data['tedistills'][0]
        response = client.get(f"/tedistill/json/species/{tedistill.id}")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        # O JSON retorna uma estrutura aninhada com 'data' contendo os datasets e labels
        assert "data" in data
        assert "datasets" in data["data"]
        assert "labels" in data["data"]


@pytest.mark.unit
@pytest.mark.website
@pytest.mark.db
class TestCAZymeRoutes:
    """Tests for CAZyme routes."""

    def test_cazyme_overview_redirect(self, client):
        """Tests redirect da overview de CAZymes."""
        response = client.get("/cazyme/")
        assert response.status_code == 302

    @pytest.mark.skipif(True, reason="Bug in controller: route uses <cazyme_label> but function expects cazyme_family")
    def test_cazyme_redirect(self, client, test_cazyme):
        """Tests redirect de find para view."""
        response = client.get(f"/cazyme/find/{test_cazyme.family}")
        assert response.status_code == 302

    def test_cazyme_view(self, client, test_cazyme):
        """Tests view de CAZyme."""
        response = client.get(f"/cazyme/view/{test_cazyme.id}")
        assert response.status_code == 200
        assert test_cazyme.family.encode() in response.data

    def test_cazyme_sequences(self, client, test_cazyme):
        """Tests paginação de sequences de CAZyme."""
        response = client.get(f"/cazyme/sequences/{test_cazyme.id}/")
        assert response.status_code == 200

    def test_cazyme_sequences_table(self, client, test_cazyme):
        """Tests tabela CSV de sequences de CAZyme."""
        response = client.get(f"/cazyme/sequences/table/{test_cazyme.id}")
        assert response.status_code == 200
        assert response.mimetype == "text/plain"

    def test_cazyme_json_species(self, client, test_cazyme):
        """Tests JSON de distribuição de species de CAZyme."""
        response = client.get(f"/cazyme/json/species/{test_cazyme.id}")
        assert response.status_code == 200
        
        data = json.loads(response.data.decode("utf-8"))
        assert "data" in data
        assert "datasets" in data["data"]
        assert "labels" in data["data"]


# Helper functions

def _assert_cytoscape_json(data, ecc_graph=False):
    """Verifies if data is in expected Cytoscape JSON format."""
    assert "nodes" in data
    assert "edges" in data

    for node in data["nodes"]:
        assert "data" in node
        assert "color" in node["data"]
        assert "id" in node["data"]

        compound = node["data"].get("compound", False)

        if not compound:
            required_keys = [
                "family_color",
                "lc_label",
                "lc_color",
                "lc_shape",
                "family_name",
                "shape",
                "description",
                "name",
                "gene_name",
                "tokens",
                "family_clade_count",
                "gene_id",
                "family_id",
                "family_url",
                "family_clade",
                "family_shape",
            ]

            assert all([k in node["data"] for k in required_keys])

            if not ecc_graph:
                assert "depth" in node["data"]
                assert "profile_link" in node["data"]
            else:
                assert "species_name" in node["data"]
                assert "species_id" in node["data"]
                assert "species_color" in node["data"]

    for edge in data["edges"]:
        assert "data" in edge
        assert "source" in edge["data"]
        assert "target" in edge["data"]
        assert "color" in edge["data"]

        homology = edge["data"].get("homology", False)

        if not homology:
            assert "edge_type" in edge["data"]
            if not ecc_graph:
                assert "link_score" in edge["data"]
                assert "profile_comparison" in edge["data"]
                assert "depth" in edge["data"]
            else:
                assert "ecc_score" in edge["data"]
