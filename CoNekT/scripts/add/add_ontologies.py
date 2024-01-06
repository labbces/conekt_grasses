#!/usr/bin/env python3

import argparse
import os

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import delete

# Create arguments
parser = argparse.ArgumentParser(description='Add ontology data to the database')
parser.add_argument('--plant_ontology', type=str, metavar='plant_ontology.txt',
                    dest='po_file',
                    help='The plant ontology file from Plant Ontology',
                    required=False)
parser.add_argument('--plant_e_c_ontology', type=str, metavar='peco.txt',
                    dest='peco_file',
                    help='The plant experimental condition ontology file',
                    required=False)
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


def add_tabular_peco(filename, empty=True, compressed=False):

    # If required empty the table first
    file_size = os.stat(filename).st_size
    if empty and file_size > 0:
        # If required empty the table first
        with engine.connect() as conn:
            stmt = delete(PlantExperimentalConditionsOntology)
            conn.execute(stmt)
            conn.commit()

    with open(filename, 'r') as fin:
        _ = fin.readline()
        i = 0
        for line in fin:
            if line.startswith('PECO:'):
                parts = line.strip().split('\t')
                if len(parts) == 3:
                    peco_id, peco_name, peco_defn = parts[0], parts[1], parts[2]
                    peco = PlantExperimentalConditionsOntology(peco_term=peco_id, peco_class=peco_name, peco_annotation=peco_defn)
                    session.add(peco)
                    i += 1
            if i % 40 == 0:
            # commit to the db frequently to allow WHOOSHEE's indexing function to work without timing out
                session.commit()
        session.commit()

def add_tabular_po(filename, empty=True, compressed=False):

    # If required empty the table first
    file_size = os.stat(filename).st_size
    if empty and file_size > 0:
        # If required empty the table first
        with engine.connect() as conn:
            stmt = delete(PlantOntology)
            conn.execute(stmt)
            conn.commit()

    with open(filename, 'r') as fin:
        i = 0
        for line in fin:
            if line.startswith('PO:'):
                parts = line.strip().split('\t')
                if len(parts) == 6:
                    po_id, po_name, po_defn = parts[0], parts[1], parts[2]
                    po = PlantOntology(po_term=po_id, po_class=po_name, po_annotation=po_defn)
                    session.add(po)
                    i += 1
            if i % 40 == 0:
            # commit to the db frequently to allow WHOOSHEE's indexing function to work without timing out
                session.commit()
        session.commit()

db_admin = args.db_admin
db_name = args.db_name

create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

engine = create_engine(create_engine_string, echo=True)

# Reflect an existing database into a new model
Base = automap_base()

Base.prepare(engine, reflect=True)

PlantExperimentalConditionsOntology = Base.classes.plant_experimental_conditions_ontology
PlantOntology = Base.classes.plant_ontology

# Create a Session
Session = sessionmaker(bind=engine)
session = Session()

peco_file = args.peco_file
po_file = args.po_file

ontology_data_count = 0

if peco_file:
    ontology_data_count+=1
    add_tabular_peco(peco_file)

if po_file:
    ontology_data_count+=1
    add_tabular_po(po_file)

if ontology_data_count == 0:
    print("Must add at least one type of ontology data (e.g., --plant_ontology)\
          to the database!")
    exit(1)

session.close()
