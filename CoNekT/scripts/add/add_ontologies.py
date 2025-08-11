#!/usr/bin/env python3

import getpass
import argparse
import os

import sys
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import delete

from log_functions import *

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
parser.add_argument('--logdir', type=str, metavar='Log diretory',
                    dest='log_dir',
                    help='The directory containing temporary populate logs',
                    required=False)
parser.add_argument('--db_verbose', type=str, metavar='Database verbose',
                    dest='db_verbose',
                    help='Enable databaseverbose logging (true/false)',
                    required=False,
                    default="false")
parser.add_argument('--py_verbose', type=str, metavar='Python script verbose',
                    dest='py_verbose',
                    help='Enable python verbose logging (true/false)',
                    required=False,
                    default="true")

args = parser.parse_args()

if args.db_password:
    db_password = args.db_password
else:
    db_password = getpass.getpass("Enter the database password: ")





def add_tabular_peco(filename, empty=True, compressed=False):

    logger.info("______________________________________________________________________")
    logger.info("➡️  Adding Plant Experimental Conditions Ontology (PECO) data:")

    # If required empty the table first
    file_size = os.stat(filename).st_size
    if empty and file_size > 0:
        try:
            # If required empty the table first
            logger.debug("Cleaning 'plant_experimental_conditions_ontology' table...")
            with engine.connect() as conn:
                stmt = delete(PlantExperimentalConditionsOntology)
                conn.execute(stmt)
            logger.debug("✅  Table cleaned successfully.")
        except Exception as e:
            print_log_error(logger, f"Error while cleaning 'plant_experimental_conditions_ontology' table: {e}")
            exit(1)

    logger.debug(f"Reading PECO file: {filename}")
    with open(filename, 'r') as fin:
        _ = fin.readline()
        i = 0
        try:
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
                if i % 500 == 0:
                    logger.debug(f"{i} entries processed and committed...")
                        
            session.commit()
            logger.info(f"✅  All {i} entries added to table 'peco' successfully!")
        except Exception as e:
            session.rollback()
            print_log_error(logger, f"Failed while inserting Peco entry number {i + 1}: {e}")
            exit(1)

def add_tabular_po(filename, empty=True, compressed=False):

    logger.info("______________________________________________________________________")
    logger.info("➡️  Adding Plant Ontology data:")

    # If required empty the table first
    file_size = os.stat(filename).st_size
    if empty and file_size > 0:
        try:
            # If required empty the table first
            logger.debug("Cleaning 'plant_ontology' table...")
            with engine.connect() as conn:
                stmt = delete(PlantOntology)
                conn.execute(stmt)
            logger.debug("✅  Table cleaned successfully.")
        except Exception as e:
            print_log_error(logger, f"Error while cleaning 'plant_ontology' table: {e}")
            exit(1)

    logger.debug(f"Reading Plant Ontology file: {filename}")
    with open(filename, 'r') as fin:
        i = 0

        try:
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
                
                if i % 500 == 0:
                    logger.debug(f"{i} entries processed and committed...")

            session.commit()
            logger.info(f"✅  All {i} entries added to table 'plant_ontology' successfully!")
        
        except Exception as e:
            session.rollback()
            print_log_error(logger, f"Failed while inserting Plant Ontology entry number {i + 1}: {e}")
            exit(1)



try:

    thisFileName = os.path.basename(__file__)
    #log variables
    log_dir = args.log_dir  #log dir path
    log_file_name = "ontologies"   #log file names
    db_verbose = str2bool(args.db_verbose)
    py_verbose = str2bool(args.py_verbose)
    logger = setup_logger(log_dir=log_dir, base_filename=log_file_name, DBverbose=db_verbose, PYverbose=py_verbose)

    db_admin = args.db_admin
    db_name = args.db_name

    create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

    engine = create_engine(create_engine_string, echo=db_verbose)

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
        print_log_error(logger, "Must add at least one type of ontology file (e.g., --plant_ontology)")
        exit(1)

    session.close()

except Exception as e:
    print_log_error(logger, e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
    exit(1)



logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} finished without errors! ✅ ---- ")