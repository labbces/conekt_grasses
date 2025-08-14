from flask import url_for
from conekt import db

from conekt.models.relationships.sequence_family import SequenceFamilyAssociation
from conekt.models.relationships.sequence_sequence_ecc import SequenceSequenceECCAssociation
from conekt.models.gene_families import GeneFamily
from conekt.models.sequences import Sequence

from utils.jaccard import jaccard
from utils.benchmark import benchmark

import random
import json
import re
import sys
from sqlalchemy import and_

from collections import defaultdict

SQL_COLLATION = 'NOCASE' if db.engine.name == 'sqlite' else ''


class ExpressionNetworkMethod(db.Model):
    __tablename__ = 'expression_network_methods'
    id = db.Column(db.Integer, primary_key=True)
    species_id = db.Column(db.Integer, db.ForeignKey('species.id'), index=True)
    description = db.Column(db.Text)
    edge_type = db.Column(db.Enum("rank", "weight", name='edge_type'))
    probe_count = db.Column(db.Integer)

    hrr_cutoff = db.Column(db.Integer)
    pcc_cutoff = db.Column(db.Float)
    enable_second_level = db.Column(db.SmallInteger)

    probes = db.relationship('ExpressionNetwork',
                             backref=db.backref('method', lazy='joined'),
                             lazy='dynamic',
                             cascade="all, delete-orphan",
                             passive_deletes=True)

    clustering_methods = db.relationship('CoexpressionClusteringMethod',
                                         backref='network_method',
                                         lazy='dynamic',
                                         cascade='all, delete-orphan',
                                         passive_deletes=True)

    def __init__(self, species_id, description, edge_type="rank"):
        self.species_id = species_id
        self.description = description
        self.edge_type = edge_type
        self.enable_second_level = False

    def __repr__(self):
        return str(self.id) + ". " + self.description + ' [' + str(self.species) + ']'


class ExpressionNetwork(db.Model):
    __tablename__ = 'expression_networks'
    id = db.Column(db.Integer, primary_key=True)
    probe = db.Column(db.String(80, collation=SQL_COLLATION), index=True)
    sequence_id = db.Column(db.Integer, db.ForeignKey('sequences.id', ondelete='CASCADE'), index=True)
    network = db.Column(db.Text)
    method_id = db.Column(db.Integer, db.ForeignKey('expression_network_methods.id', ondelete='CASCADE'), index=True)

    def __init__(self, probe, sequence_id, network, method_id):
        self.probe = probe
        self.sequence_id = sequence_id
        self.network = network
        self.method_id = method_id

    @property
    def neighbors_count(self):
        """
        Returns the number of neighors the current gene has

        :return: int, number of neighbors
        """
        data = json.loads(self.network)

        return len(data)

    @property
    def neighbors_table(self):
        """
        Returns a tab delimited representation of the current gene's neighbors

        :return:
        """
        data = json.loads(self.network)
        output = [["Sequence", "Description", "Alias", "PCC", "hrr"]]

        # Pull in descriptions and aliases
        sequence_ids = [d["gene_id"] for d in data if "gene_id" in d.keys() and d["gene_id"] is not None]
        sequences = {s.id: s for s in Sequence.query.filter(Sequence.id.in_(sequence_ids))}

        for d in data:
            try:
                description, alias = "", ""

                if d["gene_id"] in sequences.keys():
                    description = sequences[d["gene_id"]].description
                    alias = sequences[d["gene_id"]].aliases
                    description = description if description is not None else ""
                    alias = alias if alias is not None else ""

                output.append([d["gene_name"], description, alias, str(d["link_pcc"]), str(d["hrr"])])
            except Exception as e:
                print(e)

        return '\n'.join(['\t'.join(l) for l in output])

    @staticmethod
    def get_neighborhood(probe, depth=0):
        """
        Get the coexpression neighborhood for a specific probe

        :param probe: internal ID of the probe
        :param depth: how many steps away from the query you wish to expand the network
        :return: dict with nodes and edges
        """
        node = ExpressionNetwork.query.get(probe)
        links = json.loads(node.network)

        method_id = node.method_id
        edge_type = node.method.edge_type

        # add the initial node
        nodes = [{"id": node.probe,
                  "name": node.probe,
                  "probe_id": node.id,
                  "gene_id": int(node.sequence_id) if node.sequence_id is not None else None,
                  "gene_name": node.sequence.name if node.sequence_id is not None else node.probe,
                  "node_type": "query",
                  "depth": 0}]
        edges = []

        # lists necessary for doing deeper searches
        additional_nodes = []
        existing_edges = []
        existing_nodes = [node.probe]

        # add direct neighbors of the gene of interest

        for link in links:
            nodes.append(ExpressionNetwork.__process_link(link, depth=0))
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
                          "edge_type": edge_type})
            additional_nodes.append(link["probe_name"])
            existing_edges.append([node.probe, link["probe_name"]])
            existing_edges.append([link["probe_name"], node.probe])
            existing_nodes.append(link["probe_name"])

        # iterate n times to add deeper links
        if len(additional_nodes) > 0:
            for i in range(1, depth+1):
                new_nodes = ExpressionNetwork.\
                    query.filter(and_(ExpressionNetwork.probe.in_(additional_nodes),
                                      ExpressionNetwork.method_id == method_id))
                next_nodes = []

                for new_node in new_nodes:
                    new_links = json.loads(new_node.network)

                    for link in new_links:
                        if link["probe_name"] not in existing_nodes:
                            nodes.append(ExpressionNetwork.__process_link(link, depth=depth))
                            existing_nodes.append(link["probe_name"])
                            next_nodes.append(link["probe_name"])

                        if [new_node.probe, link["probe_name"]] not in existing_edges:
                            edges.append({"source": new_node.probe,
                                          "target": link["probe_name"],
                                          "profile_comparison":
                                              url_for('expression_profile.expression_profile_compare_probes',
                                                      probe_a=new_node.probe,
                                                      probe_b=link["probe_name"],
                                                      species_id=node.method.species.id),
                                          "depth": i,
                                          "link_score": link["link_score"],
                                          "link_pcc": link["link_pcc"] if "link_pcc" in link.keys() else None,
                                          "hrr": link["hrr"] if "hrr" in link.keys() else None,
                                          "edge_type": edge_type})
                            existing_edges.append([new_node.probe, link["probe_name"]])
                            existing_edges.append([link["probe_name"], new_node.probe])

                additional_nodes = next_nodes

        # Add links between the last set of nodes added
        new_nodes = []
        if len(additional_nodes) > 0:
            new_nodes = ExpressionNetwork.query.filter(and_(ExpressionNetwork.probe.in_(additional_nodes),
                                                            ExpressionNetwork.method_id == method_id))

        for new_node in new_nodes:
            new_links = json.loads(new_node.network)
            for link in new_links:
                if link["probe_name"] in existing_nodes:
                    if [new_node.probe, link["probe_name"]] not in existing_edges:
                        edges.append({"source": new_node.probe,
                                      "target": link["probe_name"],
                                      "profile_comparison":
                                          url_for('expression_profile.expression_profile_compare_probes',
                                                  probe_a=new_node.probe,
                                                  probe_b=link["probe_name"],
                                                  species_id=node.method.species.id),
                                      "depth": depth+1,
                                      "link_score": link["link_score"],
                                      "link_pcc": link["link_pcc"] if "link_pcc" in link.keys() else None,
                                      "hrr": link["hrr"] if "hrr" in link.keys() else None,
                                      "edge_type": edge_type})
                        existing_edges.append([new_node.probe, link["probe_name"]])
                        existing_edges.append([link["probe_name"], new_node.probe])

        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def get_custom_network(method_id, probes):
        """
        Return a network dict for a certain set of probes/sequences. Only returns the selected nodes and connections
        between them (if any)

        :param method_id: network method to extract information from
        :param probes: list of probe/sequence names
        :return: network dict
        """
        nodes = []
        edges = []

        probes = ExpressionNetwork.query.filter(ExpressionNetwork.method_id == method_id).\
            filter(ExpressionNetwork.probe.in_(probes)).all()

        valid_nodes = []

        for p in probes:
            node = {"id": p.probe,
                    "name": p.probe,
                    "probe_id": p.id,
                    "gene_id": int(p.sequence_id) if p.sequence_id is not None else None,
                    "gene_name": p.sequence.name if p.sequence_id is not None else p.probe,
                    "node_type": "query",
                    "depth": 0}

            valid_nodes.append(p.probe)
            nodes.append(node)

        existing_edges = []

        for p in probes:
            source = p.probe
            neighborhood = json.loads(p.network)
            for n in neighborhood:
                if n["probe_name"] in valid_nodes:
                    if [source, n["probe_name"]] not in existing_edges:
                        edges.append({"source": source,
                                      "target": n["probe_name"],
                                      "profile_comparison":
                                          url_for('expression_profile.expression_profile_compare_probes',
                                                  probe_a=source,
                                                  probe_b=n["probe_name"],
                                                  species_id=p.method.species.id),
                                      "depth": 0,
                                      "link_score": n["link_score"],
                                      "link_pcc": n["link_pcc"] if "link_pcc" in n.keys() else None,
                                      "hrr": n["hrr"] if "hrr" in n.keys() else None,
                                      "edge_type": p.method.edge_type})
                        existing_edges.append([source, n["probe_name"]])
                        existing_edges.append([n["probe_name"], source])

        return {"nodes": nodes, "edges": edges}

    @staticmethod
    def __process_link(linked_probe, depth):
        """
        Internal function that processes a linked probe (from the ExpressionNetwork.network field) to a data entry
        compatible with cytoscape.js

        :param linked_probe: hash with information from ExpressionNetwork.network field
        :return: a hash formatted for use as a node with cytoscape.js
        """
        if linked_probe["gene_id"] is not None:
            return {"id": linked_probe["probe_name"],
                    "name": linked_probe["probe_name"],
                    "gene_id": linked_probe["gene_id"],
                    "gene_name": linked_probe["gene_name"],
                    "node_type": "linked",
                    "depth": depth}
        else:
            return {"id": linked_probe["probe_name"],
                    "name": linked_probe["probe_name"],
                    "gene_id": None,
                    "gene_name": linked_probe["probe_name"],
                    "node_type": "linked",
                    "depth": depth}
