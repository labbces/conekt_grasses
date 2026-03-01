#!/usr/bin/env python3

import getpass
import argparse
#import psutil

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select, and_
import math

from log_functions import *

parser = argparse.ArgumentParser(description='Add interproscan results to the database')
parser.add_argument('--interproscan_tsv', type=str, metavar='species_interproscan.tsv',
                    dest='interproscan_file',
                    help='The TSV file from InterProScan results',
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

class InterproDomainParser:
    def __init__(self):
        self.annotation = {}

    def read_interproscan(self, filename):
        with open(filename, "r") as f:
            for line in f:
                parts = line.split('\t')
                if len(parts) > 11:
                    gene = parts[0]
                    domain = {"id": parts[11],
                              "ipr_source_db": parts[3],
                              "start": int(parts[6]),
                              "stop": int(parts[7])}

                    if gene not in self.annotation.keys():
                        self.annotation[gene] = []

                    if domain not in self.annotation[gene]:
                        self.annotation[gene].append(domain)


# def print_memory_usage():
#     # Get memory usage statistics
#     memory = psutil.virtual_memory()

#     # Print memory usage
#     print(f"Total Memory: {memory.total / (1024.0 ** 3):.2f} GB")
#     print(f"Available Memory: {memory.available / (1024.0 ** 3):.2f} GB")
#     print(f"Used Memory: {memory.used / (1024.0 ** 3):.2f} GB")
#     print(f"Memory Usage Percentage: {memory.percent}%\n")

def add_interpro_from_interproscan(filename, species_code, engine):
    """
    Adds annotation from InterProScan Output (TSV format) to the database

    :param filename: Path to the annotation file
    :param species_code: CoNekT Grasses species code
    :return:
    """
    
    logger.info("______________________________________________________________________")
    logger.info(f"➡️  Adding InterProScan annotations for species '{species_code}'.")

    # Check if species exists in the database
    try:
        logger.debug(f"Searching species '{species_code}' in database")
        with engine.connect() as conn:
            stmt = select([Species.__table__]).where(Species.__table__.c.code == species_code)
            species = conn.execute(stmt).fetchone()
    except Exception as e:
        print_log_error(logger, f"Error while querying species '{species_code}': {e}")
        exit(1)

    if not species:
        print_log_error(logger, f"Species '{species_code}' not found in the database.")
        exit(1)
    else:
        species_id = species.id
        logger.debug(f"✅ Species '{species_code}' found (ID: {species_id})")


    try:
        logger.debug(f"Reading InterProScan file: {filename}")
        interpro_parser = InterproDomainParser()
        interpro_parser.read_interproscan(filename)
        total_entries = len(interpro_parser.annotation)
    except Exception as e:
        print_log_error(logger, f"Error while reading InterProScan file '{filename}': {e}")
        exit(1)

    logger.debug(f"Found {total_entries} entries in the file.")

    gene_hash = {}
    domain_hash = {}

    logger.debug(f"Loading sequences and InterPro data to create hash maps")
    try:
        with engine.connect() as conn:
            stmt = select([Sequence.__table__]).where(
            and_(
                Sequence.__table__.c.species_id == species_id,
                Sequence.__table__.c.type == 'protein_coding'
            )
        )
            all_sequences = conn.execute(stmt).fetchall()
        logger.debug(f"{len(all_sequences)} sequences loaded for species '{species_code}'.")
    except Exception as e:
        print_log_error(logger, f"Error while retrieving sequences for species '{species_code}': {e}")
        exit(1)
    
    
    try:
        with engine.connect() as conn:
            stmt = select([Interpro.__table__]) 
            result = conn.execute(stmt)
            all_domains = result.fetchall() 
        logger.debug(f"{len(all_domains)} InterPro domains loaded from database.")
    except Exception as e:
        print_log_error(logger, f"Error while retrieving InterPro domains: {e}")
        exit(1)


    for sequence in all_sequences:
        gene_hash[sequence.name] = sequence

    for domain in all_domains:
        domain_hash[domain.label] = domain

    logger.debug("Hash maps for sequences and domains created.")
    logger.debug(f"Inserting InterPro annotations for {species_code} in database")

    new_domains = []
    notFoundGenes = 0
    notFoundDomains = 0
    count = 0
        
    try:
        for gene, domains in interpro_parser.annotation.items():
            if gene not in gene_hash:
                notFoundGenes += 1
                #logger.warning(f"⚠️  Gene '{gene}' not found in database.")
                continue

            current_sequence = gene_hash[gene]
            for domain in domains:
                if domain["id"] not in domain_hash:
                    notFoundDomains += 1
                    #logger.warning(f"⚠️  Domain '{domain['id']}' not found in database.")
                    continue

                current_domain = domain_hash[domain["id"]]

                new_domain = {
                    "sequence_id": current_sequence.id,
                    "interpro_id": current_domain.id,
                    "ipr_source_db": domain["ipr_source_db"],
                    "start": domain["start"],
                    "stop": domain["stop"]
                }

                new_domains.append(new_domain)
                count+=1

                if count % 50000 == 0:
                    logger.debug(f"{count} domains processed and committed...")

                try:
                    new_domain_obj = SequenceInterproAssociation(**new_domain)
                    session.add(new_domain_obj)
                except Exception as e:
                    logger.error(f"Failed to create SequenceInterproAssociation for domain '{domain['id']}': {e}")


            # Commit in batches to save memory
            if len(new_domains) > 400:
                try:
                    session.commit()
                    #print_memory_usage()
                    new_domains.clear()
                except Exception as e:
                    session.rollback()
                    print_log_error(logger, f"Failed to commit batch for species '{species_code}': {e}")
                    exit(1)

            

            
            

        # Final commit
        try:
            session.commit()
            logger.debug(f"✅ All {count} InterPro annotations for species '{species_code}' committed successfully.")

            if notFoundGenes > 0:
                logger.warning(f"⚠️ {notFoundGenes} genes listed in the '{species_code}' InterProScan file were not found in the 'sequence' table of your database.")

            if notFoundDomains > 0:
                logger.warning(f"⚠️ {notFoundDomains} domains listed in the f'{species_code}' InterProScan file were not found in the 'interpro' table of your database.")

            #print_memory_usage()
        except Exception as e:
            session.rollback()
            print_log_error(logger, f"Failed to commit final domains for species '{species_code}': {e}")
            exit(1)

    except Exception as e:
        session.rollback()
        print_log_error(logger, f"Unexpected error while processing InterProScan annotations: {e}")
        exit(1)

try:
    thisFileName = os.path.basename(__file__)
    #log variables
    log_dir = args.log_dir  #log dir path
    log_file_name = "functional_annotation"   #log file names
    db_verbose = str2bool(args.db_verbose)
    py_verbose = str2bool(args.py_verbose)
    first_run = str2bool(args.first_run)

    logger = setup_logger(log_dir=log_dir, base_filename=log_file_name, DBverbose=db_verbose, PYverbose=py_verbose, overwrite_logs=first_run)

    interproscan_tsv = args.interproscan_file
    sps_code = args.species_code
    db_admin = args.db_admin
    db_name = args.db_name

    create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

    engine = create_engine(create_engine_string, echo=db_verbose)

    # Reflect an existing database into a new model
    Base = automap_base()

    Base.prepare(engine, reflect=True)

    Species = Base.classes.species
    Sequence = Base.classes.sequences
    SequenceInterproAssociation = Base.classes.sequence_interpro
    Interpro = Base.classes.interpro

    # Create a Session
    Session = sessionmaker(bind=engine)
    session = Session()

    # Run function to add interproscan results for species
    add_interpro_from_interproscan(interproscan_tsv, sps_code, engine)

    session.close()

except Exception as e:
    print_log_error(logger, e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
    exit(1)


logger.info(f" ---- ✅ SUCCESS: All operations for '{sps_code}' from {thisFileName} finished without errors! ✅ ---- ")