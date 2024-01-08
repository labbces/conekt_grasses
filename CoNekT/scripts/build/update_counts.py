#!/usr/bin/env python3

import argparse

from sqlalchemy import create_engine, func
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

from sqlalchemy.sql import select, update

# Create arguments
parser = argparse.ArgumentParser(description='Update all counts in the CoNekT Grasses database')
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

def update_coexpression_cluster_count(engine):
    """
    To avoid long counts the number of clusters per method can be precalculated and stored in the database
    using this function.
    """
    with engine.connect() as conn:
        stmt = select(CoexpressionClusteringMethod)
        methods = conn.execute(stmt).all()

    for m in methods:
        with engine.connect() as conn:
            stmt = select(CoexpressionCluster).where(CoexpressionCluster.__table__.c.method_id == m.id)
            m_clusters_count = conn.execute(stmt).rowcount
            stmt = update(CoexpressionClusteringMethod).where(CoexpressionClusteringMethod.__table__.c.id == m.id).values(cluster_count=m_clusters_count)
            conn.execute(stmt)
            conn.commit()

def update_network_count(engine):
        """
        To avoid long count queries the number of networks for each method can be precalculated and stored in the
        database using this function
        """

        with engine.connect() as conn:
            stmt = select(ExpressionNetworkMethod)
            methods = conn.execute(stmt).all()

        for m in methods:
            with engine.connect() as conn:
                stmt = select(ExpressionNetwork).where(ExpressionNetwork.__table__.c.method_id == m.id)
                m_probes_count = conn.execute(stmt).rowcount
                stmt = update(ExpressionNetworkMethod).where(ExpressionNetworkMethod.__table__.c.id == m.id).values(probe_count=m_probes_count)
                conn.execute(stmt)
                conn.commit()

def update_gene_family_count(engine):
        """
        To avoid long count queries, the number of families for a given method can be precalculated and stored in
        the database using this function.
        """
        with engine.connect() as conn:
            stmt = select(GeneFamilyMethod)
            methods = conn.execute(stmt).all()
        
        for m in methods:
            with engine.connect() as conn:
                stmt = select(GeneFamily).where(GeneFamily.__table__.c.method_id == m.id)
                m_family_count = conn.execute(stmt).rowcount
                stmt = update(GeneFamilyMethod).where(GeneFamilyMethod.__table__.c.id == m.id).values(family_count=m_family_count)
                conn.execute(stmt)
                conn.commit()

def update_species_counts(engine):
    """
    To avoid long counts the number of sequences, profiles and networks can be precalculated and stored in the
    database using this function.
    """

    with engine.connect() as conn:
            stmt = select(Species)
            species = conn.execute(stmt).all()

    for s in species:
        with engine.connect() as conn:
            stmt = select(Sequence).where(Sequence.__table__.c.species_id == s.id, Sequence.type=='protein_coding')
            s_sequences_count = conn.execute(stmt).rowcount
            stmt = update(Species).where(Species.__table__.c.id == s.id).values(sequence_count=s_sequences_count)
            conn.execute(stmt)
            conn.commit()
        with engine.connect() as conn:
            stmt = select(ExpressionProfile).where(ExpressionProfile.__table__.c.species_id == s.id)
            s_profiles_count = conn.execute(stmt).rowcount
            stmt = update(Species).where(Species.__table__.c.id == s.id).values(profile_count=s_profiles_count)
            conn.execute(stmt)
            conn.commit()
        with engine.connect() as conn:
            stmt = select(ExpressionNetworkMethod).where(ExpressionNetworkMethod.__table__.c.species_id == s.id)
            s_network_count = conn.execute(stmt).rowcount
            stmt = update(Species).where(Species.__table__.c.id == s.id).values(network_count=s_network_count)
            conn.execute(stmt)
            conn.commit()

def update_counts(engine):
    """
    Updates pre-computed counts in the database.

    """

    update_coexpression_cluster_count(engine)
    update_network_count(engine)
    update_gene_family_count(engine)
    update_species_counts(engine)
    #TODO: implement GO.update_species_counts()

db_admin = args.db_admin
db_name = args.db_name

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

# Reflect an existing database into a new model
Base = automap_base()

# Use the engine to reflect the database
Base.prepare(engine, reflect=True)

Sequence = Base.classes.sequences
CoexpressionClusteringMethod = Base.classes.coexpression_clustering_methods
CoexpressionCluster = Base.classes.coexpression_clusters
ExpressionNetwork = Base.classes.expression_networks
ExpressionNetworkMethod = Base.classes.expression_network_methods
ExpressionProfile = Base.classes.expression_profiles
GeneFamily = Base.classes.gene_families
GeneFamilyMethod = Base.classes.gene_family_methods
Species = Base.classes.species
GO = Base.classes.go

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

# Run the function to update counts in DB
update_counts(engine)

session.close()