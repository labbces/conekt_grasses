#!/usr/bin/env python3

import argparse
from sqlalchemy import create_engine, func
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select, update

parser = argparse.ArgumentParser(description='Update all counts in the CoNekT Grasses database')
parser.add_argument('--db_admin', required=True)
parser.add_argument('--db_name', required=True)
parser.add_argument('--db_password', required=False)

args = parser.parse_args()

if args.db_password:
    db_password = args.db_password
else:
    db_password = input("Enter the database password: ")

def update_coexpression_cluster_count(engine):
    with engine.connect() as conn:
        methods = conn.execute(select(CoexpressionClusteringMethod.id)).fetchall()
        for (method_id,) in methods:
            count = conn.execute(
                select(func.count(CoexpressionCluster.id))
                .where(CoexpressionCluster.method_id == method_id)
            ).scalar()
            conn.execute(
                update(CoexpressionClusteringMethod)
                .where(CoexpressionClusteringMethod.id == method_id)
                .values(cluster_count=count)
            )
            conn.commit()

def update_network_count(engine):
    with engine.connect() as conn:
        methods = conn.execute(select(ExpressionNetworkMethod.id)).fetchall()
        for (method_id,) in methods:
            count = conn.execute(
                select(func.count(ExpressionNetwork.id))
                .where(ExpressionNetwork.method_id == method_id)
            ).scalar()
            conn.execute(
                update(ExpressionNetworkMethod)
                .where(ExpressionNetworkMethod.id == method_id)
                .values(probe_count=count)
            )
            conn.commit()

def update_gene_family_count(engine):
    with engine.connect() as conn:
        methods = conn.execute(select(GeneFamilyMethod.id)).fetchall()
        for (method_id,) in methods:
            count = conn.execute(
                select(func.count(GeneFamily.id))
                .where(GeneFamily.method_id == method_id)
            ).scalar()
            conn.execute(
                update(GeneFamilyMethod)
                .where(GeneFamilyMethod.id == method_id)
                .values(family_count=count)
            )
            conn.commit()

def update_species_counts(engine):
    with engine.connect() as conn:
        species_ids = conn.execute(select(Species.id)).fetchall()
        for (species_id,) in species_ids:
            # Contagem de sequências
            seq_count = conn.execute(
                select(func.count(Sequence.id))
                .where(Sequence.species_id == species_id, Sequence.type == 'protein_coding')
            ).scalar()
            
            # Contagem de perfis
            profile_count = conn.execute(
                select(func.count(ExpressionProfile.id))
                .where(ExpressionProfile.species_id == species_id)
            ).scalar()
            
            # Contagem de redes
            network_count = conn.execute(
                select(func.count(ExpressionNetworkMethod.id))
                .where(ExpressionNetworkMethod.species_id == species_id)
            ).scalar()
            
            # Atualizar tudo de uma vez
            conn.execute(
                update(Species)
                .where(Species.id == species_id)
                .values(
                    sequence_count=seq_count,
                    profile_count=profile_count,
                    network_count=network_count
                )
            )
            conn.commit()

def update_counts(engine):
    print("Updating coexpression cluster counts...")
    update_coexpression_cluster_count(engine)
    
    print("Updating network counts...")
    update_network_count(engine)
    
    print("Updating gene family counts...")
    update_gene_family_count(engine)
    
    print("Updating species counts...")
    update_species_counts(engine)
    
    print("✅ All counts updated successfully!")

# Setup DB
db_admin = args.db_admin
db_name = args.db_name
engine = create_engine(f"mysql+pymysql://{db_admin}:{db_password}@localhost/{db_name}", echo=False)
Base = automap_base()
Base.prepare(engine, reflect=True)

# Classes
Sequence = Base.classes.sequences
CoexpressionClusteringMethod = Base.classes.coexpression_clustering_methods
CoexpressionCluster = Base.classes.coexpression_clusters
ExpressionNetwork = Base.classes.expression_networks
ExpressionNetworkMethod = Base.classes.expression_network_methods
ExpressionProfile = Base.classes.expression_profiles
GeneFamily = Base.classes.gene_families
GeneFamilyMethod = Base.classes.gene_family_methods
Species = Base.classes.species

# Run
update_counts(engine)
