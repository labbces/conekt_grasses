#!/usr/bin/env python3

import getpass
import argparse
import os
import sys
import logging

#import psutil

from sqlalchemy import create_engine, and_
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
parser.add_argument('--first_run', type=str, metavar='Flag indicating first execution of the file',
                    dest='first_run',
                    help='Controls log file openning type',
                    required=False,
                    default="true")

args = parser.parse_args()

if args.db_password:
    db_password = args.db_password
else:
    db_password = getpass.getpass("Enter the database password: ")



def setup_logger(log_dir="logs_populate", base_filename="functional data", DBverbose=False, PYverbose=True, overwrite_logs=False):
    """
    Sets up the application's logging system with support for both file and console output.

    Creates a logger with separate handlers for info and error messages, writing them to 
    distinct files and displaying them in the console. Also allows enabling or disabling 
    SQLAlchemy engine log propagation.

    :param log_dir: Directory where the log files will be saved (default: "logs_populate")
    :param base_filename: Base name for the generated log files (default: "functional data")
    :param DBverbose: If True, enables SQLAlchemy engine logs to propagate to the console (default: False)
    :return: Configured logger object
    """

    # Set SQLAlchemy logger level
    sqla_logger = logging.getLogger('sqlalchemy.engine')
    sqla_logger.setLevel(logging.INFO)
    sqla_logger.propagate = DBverbose 

    #creates log dir
    os.makedirs(log_dir, exist_ok=True)

    # defines openning type for log files
    mode = 'w' if overwrite_logs else 'a'

    logger = logging.getLogger()
    level = logging.DEBUG if PYverbose else logging.INFO
    logger.setLevel(level)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    log_file_base = os.path.join(log_dir, base_filename)
    stdout_log_path = f"{log_file_base}.o.log"
    stderr_log_path = f"{log_file_base}.e.log"

    # File handlers
    file_info_handler = logging.FileHandler(stdout_log_path, mode=mode, encoding='utf-8')
    file_info_handler.setLevel(level)
    file_info_handler.setFormatter(formatter)

    file_error_handler = logging.FileHandler(stderr_log_path, mode=mode, encoding='utf-8')
    file_error_handler.setLevel(logging.ERROR)
    file_error_handler.setFormatter(formatter)

    # Handlers para console
    console_info_handler = logging.StreamHandler(sys.stdout)
    console_info_handler.setLevel(level)
    console_info_handler.setFormatter(formatter)

    console_error_handler = logging.StreamHandler(sys.stderr)
    console_error_handler.setLevel(logging.ERROR)
    console_error_handler.setFormatter(formatter)

    if not logger.hasHandlers():
        logger.addHandler(file_info_handler)
        logger.addHandler(file_error_handler)
        logger.addHandler(console_info_handler)
        logger.addHandler(console_error_handler)

    return logger


def print_log_error(message):
    """
    Logs an error message and a follow-up instruction to abort the operation.
    :param message: Error message to log
    """
    logger.error(f'❌ {message}')
    logger.error("OPERATION ABORTED. Fix the issue and run the script again.")


def str2bool(v):
    """
    Converts a string or value to a boolean.
    :param v: The input value to convert to boolean
    :return: Boolean value (True or False)
    """
    if isinstance(v, bool):
        return v
    val = str(v).strip().lower()
    if val in ('yes', 'true', 't', '1'):
        return True
    elif val in ('no', 'false', 'f', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError(f'Boolean value expected, got "{v}"')



def add_descriptions(filename, species_code, engine):

    logger.info("______________________________________________________________________")
    logger.info(f"➡️  Adding Gene Descriptions for species '{species_code}':")
    
    try:
        with engine.connect() as conn:
                stmt = select([Species.__table__]).where(Species.__table__.c.code == species_code)
                result = conn.execute(stmt)
                species = result.fetchone()
    except Exception as e:
        print_log_error(f"Error while querying species '{species_code}': {e}")
        exit(1)

    # species is not in the DB yet, add it
    if not species:
        print_log_error(f"Species '{species_code}' not found in database.")
        exit(1)

    try:
        with engine.connect() as conn:
            stmt = select([Sequence.__table__]).where(
                and_(
                    Sequence.__table__.c.type == 'protein_coding',
                    Sequence.__table__.c.species_id == species['id']
                )
            )
            result = conn.execute(stmt)
            all_sequences = result.fetchall()
    except Exception as e:
        print_log_error(f"Error while retrieving sequences for species '{species_code}': {e}")
        exit(1)

    seq_dict = {}

    for s in all_sequences:
        seq_dict[s['name']] = s

    try:
        with open(filename, "r") as f_in:
            notFound = 0
            for i, line in enumerate(f_in):
                try:
                    name, description = line.strip().split('\t')
                except ValueError as ve:
                    logger.warning(f"⚠️  Line {i} in '{filename}' is malformed: '{line.strip()}'. Skipping.")
                    continue
                
                
                if name in seq_dict.keys():
                    try:
                        with engine.connect() as conn:
                            stmt = Sequence.__table__.update().where(
                                Sequence.__table__.c.id == seq_dict[name]['id']  
                            ).values(description=description)
                            conn.execute(stmt)
                            conn.execute("COMMIT")  

                            if i % 10000 == 0:
                                logger.debug(f"{i} sequence descriptions updated...")
                            
                    except Exception as e:
                        logger.error(f"Failed to update description for sequence '{name}': {e}")
                else:
                    #logger.warning(f"⚠️  Sequence '{name}' not found in database.")
                    notFound+=1
            
            logger.info(f"✅  {i - notFound} gene descriptions updated successfully.")
            if notFound > 0:
                logger.warning(f"⚠️  {notFound} sequences in '{species_code}' gene description file were not found in database.")
    except Exception as e:
        print_log_error(f"Error while processing file '{filename}': {e}")
        exit(1)

try:

    thisFileName = os.path.basename(__file__)
    #log variables
    log_dir = args.log_dir  #log dir path
    log_file_name = "gene_descriptions"   #log file names
    db_verbose = str2bool(args.db_verbose)
    py_verbose = str2bool(args.py_verbose)
    first_run = str2bool(args.first_run)

    logger = setup_logger(log_dir=log_dir, base_filename=log_file_name, DBverbose=db_verbose, PYverbose=py_verbose, overwrite_logs=first_run)

    db_admin = args.db_admin
    db_name = args.db_name

    create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

    engine = create_engine(create_engine_string, echo=db_verbose)

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

except Exception as e:
    print_log_error(e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
    exit(1)


logger.info(f" ---- ✅ SUCCESS: All operations for '{species_code}' from {thisFileName} finished without errors! ✅ ---- ")

