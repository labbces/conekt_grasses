#!/usr/bin/env python3

import argparse

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from collections import defaultdict


parser = argparse.ArgumentParser(description='Add GO results to the database')
parser.add_argument('--cazyme_tsv', type=str, metavar='species_cazymes.tsv',
                    dest='cazyme_file',
                    help='The TSV file with CAZymes results',
                    required=True)
parser.add_argument('--species_code', type=str, metavar='Svi',
                    dest='species_code',
                    help='The CoNekT Grasses species code',
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


def add_cazyme_from_tab(filename, species_code, engine):
    gene_hash = {}
    cazyme_hash = {}

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
        stmt = select(CAZYme)
        all_cazyme = conn.execute(stmt).all()

    for sequence in all_sequences:
        gene_hash[sequence.name] = sequence

    for term in all_cazyme:
        cazyme_hash[term.family] = term

    associations = []

    gene_cazyme = defaultdict(list)

    with open(filename, "r") as f:
        for line in f:
            term, hmm_length, gene, query_length, e_value, start, end = line.strip().split('\t')
            term = term.replace('.hmm', '')
            if gene in gene_hash.keys():
                current_sequence = gene_hash[gene]
                if term in cazyme_hash.keys():
                    current_term = cazyme_hash[term]
                    association = {
                        "sequence_id": current_sequence.id,
                        "cazyme_id": current_term.id,
                        "hmm_length": hmm_length,
                        "query_length": query_length,
                        "e_value": e_value,
                        "query_start": start,
                        "query_end": end,
                        }
                    associations.append(association)

                    if term not in gene_cazyme[gene]:
                        gene_cazyme[gene].append(term)
                        session.add(SequenceCAZYmeAssociation(**association))

                else:
                    print(term, "not found in the database.")
            else:
                print("Gene", gene, "not found in the database.")

            if len(associations) > 400:
                session.commit()
                associations = []

    session.commit()

cazyme_tsv = args.cazyme_file
sps_code = args.species_code
db_admin = args.db_admin
db_name = args.db_name

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

# Reflect an existing database into a new model
Base = automap_base()

Base.prepare(engine, reflect=True)

Species = Base.classes.species
Sequence = Base.classes.sequences
CAZYme = Base.classes.cazyme
SequenceCAZYmeAssociation = Base.classes.sequence_cazyme

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

# Run function to add interproscan results for species
add_cazyme_from_tab(cazyme_tsv, sps_code, engine)

session.close()