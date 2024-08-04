#!/usr/bin/env python3

import argparse
import json

from math import log2
from utils_scripts.enrichment import hypergeo_sf, fdr_correction

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.sql import delete, select
from sqlalchemy.orm import joinedload

# Create arguments
parser = argparse.ArgumentParser(description='Compute GO enrichment for all clusters in the database.')
parser.add_argument('--db_admin', type=str, metavar='DB admin',
                    dest='db_admin',
                    help='The database admin user',
                    required=True)
parser.add_argument('--db_name', type=str, metavar='DB name',
                    dest='db_name',
                    help='The database name',
                    required=True)
parser.add_argument('--db_password', type=str, metavar='DB password',
                    dest='db_password',
                    help='The database password',
                    required=False)

args = parser.parse_args()

if args.db_password:
    db_password = args.db_password
else:
    db_password = input("Enter the database password: ")


def __calculate_enrichment(engine, cluster, all_species_db, all_network_methods_db, all_clustering_methods_db, go_species_counts_dict):
        """
        Initial implementation to calculate GO enrichment for a single cluster
        """
        
        clustering_method = [n for n in all_clustering_methods_db if n.id == cluster.method_id][0]
        network_method = [n for n in all_network_methods_db if n.id == clustering_method.network_method_id][0]
        
        species = [s for s in all_species_db if s.id == network_method.species_id][0]
        species_id = species.id
        gene_count = species.sequence_count

        with engine.connect() as conn:
            stmt = select(SequenceCoexpressionClusterAssociation.__table__.c.sequence_id)\
                        .where(SequenceCoexpressionClusterAssociation.__table__.c.coexpression_cluster_id == cluster.id).distinct()
            sequences_cluster = conn.execute(stmt).all()

        with engine.connect() as conn:
            stmt = select(SequenceGOAssociation.__table__.c.sequence_id,
                  SequenceGOAssociation.__table__.c.go_id).\
                    where(SequenceGOAssociation.sequence_id.in_([s.sequence_id for s in sequences_cluster]),
                          SequenceGOAssociation.predicted == 0).\
                    group_by(SequenceGOAssociation.sequence_id, SequenceGOAssociation.go_id)
            associations = conn.execute(stmt).all()

        go_data = {}

        for a in associations:
            if a.go_id not in go_data.keys():
                go_data[a.go_id] = {}
                go_data[a.go_id]["total_count"] = go_species_counts_dict[a.go_id][species_id]
                go_data[a.go_id]["cluster_count"] = 1
            else:
                go_data[a.go_id]["cluster_count"] += 1

        p_values = []
        for go_id in go_data:
            p_values.append(hypergeo_sf(go_data[go_id]['cluster_count'],
                                        len(sequences_cluster),
                                        go_data[go_id]['total_count'],
                                        gene_count))

        corrected_p_values = fdr_correction(p_values)

        for i, go_id in enumerate(go_data):
            enrichment = ClusterGOEnrichment()
            enrichment.cluster_id = cluster.id
            enrichment.go_id = go_id

            enrichment.cluster_count = go_data[go_id]['cluster_count']
            enrichment.cluster_size = len(sequences_cluster)
            enrichment.go_count = go_data[go_id]['total_count']
            enrichment.go_size = gene_count

            enrichment.enrichment = log2((go_data[go_id]['cluster_count']/len(sequences_cluster))/(go_data[go_id]['total_count']/gene_count))
            enrichment.p_value = p_values[i]
            enrichment.corrected_p_value = corrected_p_values[i]

            session.add(enrichment)

        try:
            session.commit()
        except Exception as e:
            session.rollback()
            print(e)


def calculate_enrichment(engine, all_species_db, all_network_methods_db, all_clustering_methods_db, go_species_counts_dict, empty=True):
    """
    Static method to calculate the enrichment for all cluster in the database

    :param empty: empty table cluster_go_enrichment first
    """

    if empty:
        # If required empty the table first
        with engine.connect() as conn:
            stmt = delete(ClusterGOEnrichment)
            conn.execute(stmt)
            conn.commit()

    # Getting all clusters from the database
    with engine.connect() as conn:
        stmt = select(CoexpressionCluster)
        clusters = conn.execute(stmt).all()

    for i, cluster in enumerate(clusters):
        __calculate_enrichment(engine, cluster, all_species_db, all_network_methods_db, all_clustering_methods_db, go_species_counts_dict)

db_admin = args.db_admin
db_name = args.db_name

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True, poolclass=NullPool)

# Reflect an existing database into a new model
Base = automap_base()

# Use the engine to reflect the database
Base.prepare(engine, reflect=True)

Sequence = Base.classes.sequences
Species = Base.classes.species
ExpressionNetworkMethod = Base.classes.expression_network_methods
ClusterGOEnrichment = Base.classes.cluster_go_enrichment
CoexpressionClusteringMethod = Base.classes.coexpression_clustering_methods
CoexpressionCluster = Base.classes.coexpression_clusters
SequenceCoexpressionClusterAssociation = Base.classes.sequence_coexpression_cluster
SequenceGOAssociation = Base.classes.sequence_go
GO = Base.classes.go

# Getting all species from the database
with engine.connect() as conn:
    stmt = select(Species)
    all_species_db = conn.execute(stmt).all()

# Building dictionary with associations between species IDs and GO counts
go_species_counts_dict = {}

with engine.connect() as conn:
    stmt = select(GO.__table__.c.id,
                  GO.__table__.c.species_counts)
    all_gos = conn.execute(stmt).all()

for go in all_gos:
    go_species_counts_dict[go.id] = {}
    for sp in all_species_db:
        if go.species_counts:
            print(go.id, sp.id, json.loads(go.species_counts))
            if str(sp.id) in json.loads(go.species_counts).keys():
                go_species_counts_dict[go.id][sp.id] = json.loads(go.species_counts)[str(sp.id)]

# Getting all co-expression network methods from the database
with engine.connect() as conn:
    stmt = select(ExpressionNetworkMethod)
    all_network_methods_db = conn.execute(stmt).all()

# Getting all co-expression clustering methods from the database
with engine.connect() as conn:
    stmt = select(CoexpressionClusteringMethod)
    all_clustering_methods_db = conn.execute(stmt).all()

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

# Run the function to compute GO enrichment for all clusters
calculate_enrichment(engine, all_species_db, all_network_methods_db, all_clustering_methods_db, go_species_counts_dict)

session.close()