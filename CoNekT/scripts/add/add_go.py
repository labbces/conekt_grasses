#!/usr/bin/env python3

import argparse

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from collections import defaultdict

parser = argparse.ArgumentParser(description='Add GO results to the database')
parser.add_argument('--go_tsv', type=str, metavar='species_go.tsv',
                    dest='go_file',
                    help='The TSV file from InterProScan results',
                    required=True)
parser.add_argument('--species_code', type=str, metavar='Svi',
                    dest='species_code',
                    help='The CoNekT Grasses species code',
                    required=True)
parser.add_argument('--annotation_source', type=str, metavar='GOs from InterProScan',
                    dest='annot_source',
                    help='Source for the GO annotation (e.g., GOs can come from InterProScan results)',
                    required=True)
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

def add_go_from_tab(filename, species_code, engine, source="Source not provided"):
    gene_hash = {}
    go_hash = {}

    # Check if species exists in the database
    with engine.connect() as conn:
        stmt = select(Species).where(Species.__table__.c.code == species_code)
        species = conn.execute(stmt).first()

    if not species:
        print(f"Species ({species_code}) not found in the database.")
        exit(1)
    else:
        species_id = species.id

    with engine.connect() as conn:
            stmt = select(Sequence).where(Sequence.__table__.c.species_id == species_id,\
                                          Sequence.__table__.c.type == 'protein_coding')
            all_sequences = conn.execute(stmt).all()
    
    with engine.connect() as conn:
            stmt = select(GO)
            all_go = conn.execute(stmt).all()

    for sequence in all_sequences:
        gene_hash[sequence.name] = sequence

    for term in all_go:
        go_hash[term.label] = term

    associations = []

    gene_go = defaultdict(list)

    with open(filename, "r") as f:
        for line in f:
            gene, term, evidence = line.strip().split('\t')
            if gene in gene_hash.keys():
                current_sequence = gene_hash[gene]
                if term in go_hash.keys():
                    current_term = go_hash[term]
                    association = {
                        "sequence_id": current_sequence.id,
                        "go_id": current_term.id,
                        "evidence": evidence,
                        "source": source}
                    associations.append(association)
                    session.add(SequenceGOAssociation(**association))

                    if term not in gene_go[gene]:
                        gene_go[gene].append(term)

                else:
                    print(term, "not found in the database.")
            else:
                print("Gene", gene, "not found in the database.")

            if len(associations) > 400:
                session.commit()
                associations = []
        
    session.commit()

    # Add extended GOs
    for gene, terms in gene_go.items():
        if gene in gene_hash.keys():
            current_sequence = gene_hash[gene]
            new_terms = []
            current_terms = []

            for term in terms:
                if term not in current_terms:
                    current_terms.append(term)

            for term in terms:
                if term in go_hash.keys():
                    extended_terms = go_hash[term].extended_go.split(";")
                    for extended_term in extended_terms:
                        if extended_term not in current_terms and extended_term not in new_terms:
                            new_terms.append(extended_term)

            for new_term in new_terms:
                if new_term in go_hash.keys():
                    current_term = go_hash[new_term]
                    association = {
                        "sequence_id": current_sequence.id,
                        "go_id": current_term.id,
                        "evidence": None,
                        "source": "Extended"}
                    associations.append(association)
                    session.add(SequenceGOAssociation(**association))

                if len(associations) > 400:
                    session.commit()
                    associations = []

    session.commit()

go_tsv = args.go_file
sps_code = args.species_code
annotation_source = args.annot_source
db_admin = args.db_admin
db_name = args.db_name

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

# Reflect an existing database into a new model
Base = automap_base()

Base.prepare(engine, reflect=True)

Species = Base.classes.species
Sequence = Base.classes.sequences
GO = Base.classes.go
SequenceGOAssociation = Base.classes.sequence_go

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

# Run function to add interproscan results for species
add_go_from_tab(go_tsv, sps_code, engine, source=annotation_source)

session.close()