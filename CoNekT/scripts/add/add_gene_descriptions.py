#!/usr/bin/env python3

import argparse
import psutil
import sys
import gzip
import operator

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select, update

from crossref.restful import Works

parser = argparse.ArgumentParser(description='Add gene descriptions for species in the database')
parser.add_argument('--species_code', type=str, metavar='Svi',
                    dest='species_code',
                    help='The CoNekt Grasses species code',
                    required=True)
parser.add_argument('--gene_descriptions', type=str, metavar='gene_descriptions.tsv',
                    dest='gene_desc_file',
                    help='The TSV file with gene descriptions',
                    required=True)
parser.add_argument('--db_admin', type=str, metavar='DB admin',
                    dest='db_admin',
                    help='The database admin user',
                    required=True)
parser.add_argument('--db_name', type=str, metavar='DB name',
                    dest='db_name',
                    help='The database name',
                    required=True)

args = parser.parse_args()

db_password = input("Enter the database password: ")


def add_descriptions(filename, species_code, engine):
    
    with engine.connect() as conn:
            stmt = select(Species).where(Species.__table__.c.code == species_code)
            species = conn.execute(stmt).first()

    # species is not in the DB yet, add it
    if not species:
        print(f'Species {species_code} not found in DB')
        exit(1)

    with engine.connect() as conn:
        stmt = select(Sequence).where(Sequence.__table__.c.type == 'protein_coding', Sequence.__table__.c.species_id == species.id)
        all_sequences = conn.execute(stmt).all()

    seq_dict = {}

    for s in all_sequences:
        seq_dict[s.name] = s

    with open(filename, "r") as f_in:
        for i, line in enumerate(f_in):
            name, description = line.strip().split('\t')
                        
            if name in seq_dict.keys():
                with engine.connect() as conn:
                    stmt = update(Sequence).where(Sequence.__table__.c.id == seq_dict[name].id).values(description=description)
                    conn.execute(stmt)
                    conn.commit()

db_admin = args.db_admin
db_name = args.db_name

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

# Reflect an existing database into a new model
Base = automap_base()

Base.prepare(engine, reflect=True)

Species = Base.classes.species
Sequence = Base.classes.sequences

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

gene_descriptions_file = args.gene_desc_file
species_code = args.species_code

# Loop over gene description file and add to DB
add_descriptions(gene_descriptions_file, species_code, engine)

session.close()