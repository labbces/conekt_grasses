#!/usr/bin/env python3


import getpass
import argparse

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from collections import defaultdict
from log_functions import *



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

# if args.db_password:
#     db_password = args.db_password
# else:
#     db_password = input("Enter the database password: ")

if args.db_password:
    db_password = args.db_password
else:
    db_password = getpass.getpass("Enter the database password: ")


from sqlalchemy.orm import sessionmaker
from collections import defaultdict

def add_cazyme_from_tab(filename, species_code, engine):

    logger.info("______________________________________________________________________")
    logger.info(f"➡️  Adding CAZyme data for '{species_code}':")

    gene_hash = {}
    cazyme_hash = {}

    # Criar a sessão
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check if species exists in the database
        logger.debug(f"Searching species '{species_code}' in database")
        species = session.query(Species).filter(Species.code == species_code).first()

        if not species:
            print_log_error(logger, f"Species ({species_code}) not found in the database.")
            exit(1)
        else:
            species_id = species.id
            logger.debug(f"✅ Species '{species_code}' found (ID: {species_id})")


        logger.debug(f"Getting protein coding sequences for '{species_code}'")
        all_sequences = session.query(Sequence).filter(
            Sequence.species_id == species_id,
            Sequence.type == 'protein_coding'
        ).all()

        logger.debug(f"Getting CAZyme data")
        all_cazyme = session.query(CAZYme).all()

        for sequence in all_sequences:
            gene_hash[sequence.name] = sequence

        for term in all_cazyme:
            cazyme_hash[term.family] = term

        associations = []
        gene_cazyme = defaultdict(list)

        added = 0
        notFoundGene = 0
        notFoundCazyme = 0

        logger.debug(f"Reading CAZyme file: {filename}")
        with open(filename, "r") as f:
            for line in f:
                try:
                    term, hmm_length, gene, query_length, e_value, start, end = line.strip().split('\t')
                except ValueError:
                    logger.warning(f"⚠️  Invalid line format skipped: {line.strip()}")
                    continue

                term = term.replace('.hmm', '')

                if gene in gene_hash:
                    current_sequence = gene_hash[gene]

                    if term in cazyme_hash:
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
                            added += 1
                    else:
                        #logger.warning(f"⚠️  CAZyme term '{term}' not found in database.")
                        notFoundCazyme += 1
                else:
                    #logger.warning(f"⚠️  Gene '{gene}' not found in database.")
                    notFoundGene += 1

                if len(associations) > 400:
                    try:
                        session.commit()
                        associations.clear()
                    except Exception as e:
                        session.rollback()
                        print_log_error(logger, f"Failed to commit CAZyme batch: {e}")
                        exit(1)

                if added % 1000 == 0:
                    logger.debug(f"{added} entries processed and committed...")

        if associations:
            try:
                session.commit()

                logger.debug(f"✅ {added} CAZyme entries for species '{species_code}' committed successfully.")

                if notFoundGene > 0:
                    logger.warning(f"⚠️  {notFoundGene} sequences listed in the '{species_code}' CAZyme file were not found in the 'sequence' table of your database.")
                
                if notFoundCazyme > 0:
                    logger.warning(f"⚠️  {notFoundCazyme}  CAZyme terms listed in the '{species_code}' CAZyme file were not found in the 'cazyme' table of your database.")

            except Exception as e:
                session.rollback()
                print_log_error(logger, f"Failed to commit final CAZyme associations: {e}")
                exit(1)

    except Exception as e:
        print_log_error(logger, f"Unexpected error in add_cazyme_from_tab: {e}")
        session.rollback()
        exit(1)

    finally:
        session.close()


try:

    thisFileName = os.path.basename(__file__)
    #log variables
    log_dir = args.log_dir  #log dir path
    log_file_name = "cazymes"   #log file names
    db_verbose = str2bool(args.db_verbose)
    py_verbose = str2bool(args.py_verbose)
    first_run = str2bool(args.first_run)
    
    logger = setup_logger(log_dir=log_dir, base_filename=log_file_name, DBverbose=db_verbose, PYverbose=py_verbose, overwrite_logs=first_run)


    cazyme_tsv = args.cazyme_file
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
    CAZYme = Base.classes.cazyme
    SequenceCAZYmeAssociation = Base.classes.sequence_cazyme

    # Create a Session
    Session = sessionmaker(bind=engine)
    session = Session()

    # Run function to add interproscan results for species
    add_cazyme_from_tab(cazyme_tsv, sps_code, engine)

    session.close()

except Exception as e:
    print_log_error(logger, e)
    logger.info(f" ---- An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ---- ")
    exit(1)


logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} for '{sps_code}' finished without errors! ✅ ---- ")