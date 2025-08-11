import json

from flask import url_for
from sqlalchemy.orm import joinedload, undefer

from conekt import db
from conekt.models.expression.networks import ExpressionNetwork
from conekt.models.gene_families import GeneFamily
from conekt.models.interpro import Interpro
from conekt.models.go import GO
from conekt.models.cazyme import CAZYme
from conekt.models.expression.profiles import ExpressionProfile


class CoexpressionClusteringMethod(db.Model):
    __tablename__ = 'coexpression_clustering_methods'
    id = db.Column(db.Integer, primary_key=True)
    network_method_id = db.Column(db.Integer, db.ForeignKey('expression_network_methods.id', ondelete='CASCADE'), index=True)
    method = db.Column(db.Text)
    cluster_count = db.Column(db.Integer)

    clusters = db.relationship('CoexpressionCluster',
                               backref=db.backref('method', lazy='joined'),
                               lazy='dynamic',
                               cascade="all, delete-orphan",
                               passive_deletes=True)


class CoexpressionCluster(db.Model):
    __tablename__ = 'coexpression_clusters'
    id = db.Column(db.Integer, primary_key=True)
    method_id = db.Column(db.Integer, db.ForeignKey('coexpression_clustering_methods.id', ondelete='CASCADE'))
    name = db.Column(db.String(50), index=True)

    # Other properties
    # sequences defined in Sequence
    # sequence_associations defined in SequenceCoexpressionClusterAssociation'
    # go_enrichment defined in ClusterGOEnrichment
    # clade_enrichment defined in ClusterCladeEnrichment

    @staticmethod
    def get_cluster(cluster_id):
        """
        Returns the network for a whole cluster (reporting edges only between members of the cluster !)

        :param cluster_id: internal ID of the cluster
        :return network for the selected cluster (dict with nodes and edges)
        """
        cluster = CoexpressionCluster.query.get(cluster_id)

        probes = [member.probe for member in cluster.sequence_associations.all()]

        network = cluster.method.network_method.probes.\
            options(joinedload('sequence').load_only('name')).\
            filter(ExpressionNetwork.probe.in_(probes)).all()

        nodes = []
        edges = []

        existing_edges = []

        for node in network:
            nodes.append({"id": node.probe,
                          "name": node.probe,
                          "gene_id": int(node.sequence_id) if node.sequence_id is not None else None,
                          "gene_name": node.sequence.name if node.sequence_id is not None else node.probe,
                          "depth": 0})

            links = json.loads(node.network)

            for link in links:
                # only add links that are in the cluster !
                if link["probe_name"] in probes and [node.probe, link["probe_name"]] not in existing_edges:
                    edges.append({"source": node.probe,
                                  "target": link["probe_name"],
                                  "profile_comparison":
                                      url_for('expression_profile.expression_profile_compare_probes',
                                              probe_a=node.probe,
                                              probe_b=link["probe_name"],
                                              species_id=node.method.species.id),
                                  "depth": 0,
                                  "link_score": link["link_score"],
                                  "link_pcc": link["link_pcc"] if "link_pcc" in link.keys() else None,
                                  "hrr": link["hrr"] if "hrr" in link.keys() else None,
                                  "edge_type": cluster.method.network_method.edge_type})
                    existing_edges.append([node.probe, link["probe_name"]])
                    existing_edges.append([link["probe_name"], node.probe])

        return {"nodes": nodes, "edges": edges}

    @property
    def profiles(self):
        """
        Returns a list with all expression profiles of cluster members
        :return: list of all profiles
        """

        sequence_subquery = self.sequences.subquery()

        profiles = ExpressionProfile.query.\
            options(undefer('profile')).\
            join(sequence_subquery, ExpressionProfile.sequence_id == sequence_subquery.c.id).all()

        return profiles

    @property
    def interpro_stats(self):
        """
        Get InterPro statistics for the current cluster

        :return: Interpro statistics
        """
        sequence_ids = [s.id for s in self.sequences.all()]

        return Interpro.sequence_stats(sequence_ids)

    @property
    def go_stats(self):
        """
        Get GO statistics for the current cluster

        :return: GO statistics
        """
        sequence_ids = [s.id for s in self.sequences.all()]

        return GO.sequence_stats(sequence_ids)

    @property
    def cazyme_stats(self):
        """
        Get CAZYme statistics for the current cluster

        :return: CAZYme statistics
        """
        sequence_ids = [s.id for s in self.sequences.all()]

        return CAZYme.sequence_stats(sequence_ids)

    @property
    def family_stats(self):
        """
        Get gene family statistics for the current cluster

        :return: gene family statistics
        """
        sequence_ids = [s.id for s in self.sequences.all()]

        return GeneFamily.sequence_stats(sequence_ids)
