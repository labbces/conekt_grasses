#!/usr/bin/env python3

import getpass
import argparse

from sqlalchemy import create_engine, and_
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select
from collections import defaultdict

from log_functions import *

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

def add_go_from_tab(filename, species_code, engine, source="Source not provided"):

    logger.info("______________________________________________________________________")
    logger.info(f"➡️  Adding GO annotations for species '{species_code}' from '{filename}'.")


    gene_hash = {}
    go_hash = {}

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
        logger.debug(f"Loading '{species_code}' sequences")
        with engine.connect() as conn:
            stmt = select([Sequence.__table__]).where(
                and_(
                    Sequence.__table__.c.species_id == species_id,
                    Sequence.__table__.c.type == 'protein_coding'
                )
            )
            all_sequences = conn.execute(stmt).fetchall()
        logger.debug(f"Loaded {len(all_sequences)} sequences for species '{species_code}'.")
    except Exception as e:
        print_log_error(logger, f"Error while retrieving sequences: {e}")
        exit(1)
    
    try:
        logger.debug(f"Loading entries in GO table")
        with engine.connect() as conn:
            stmt = select([GO.__table__])
            all_go = conn.execute(stmt).fetchall()
        logger.debug(f"Loaded {len(all_go)} GO terms from database.")
    except Exception as e:
        print_log_error(logger, f"Error while retrieving GO terms: {e}")
        exit(1)

    logger.debug("Creating hash maps for sequences and GO terms")
    for sequence in all_sequences:
        gene_hash[sequence.name] = sequence

    for term in all_go:
        go_hash[term.label] = term

    logger.debug("Hash maps for sequences and GO terms created")



    associations = []
    gene_go = defaultdict(list)
    notFoundGenes = 0
    notFoundTerms = 0
    count = 0

    logger.debug(f"Reading GO file: {filename}")
    try:
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
                            "source": source,
                            "predicted": 0}
                        associations.append(association)

                        try:
                            session.add(SequenceGOAssociation(**association))
                            count+=1
                            if count % 50000 == 0:
                                logger.debug(f"{count} GO associations processed and committed...")

                        except Exception as e:
                            logger.error(f"Failed to add GO association for gene '{gene}' and term '{term}': {e}")

                        if term not in gene_go[gene]:
                            gene_go[gene].append(term)

                    else:
                        #logger.warning(f"⚠️  Term {term} not found in the database.")
                        notFoundTerms+=1
                else:
                    #logger.warning(f"⚠️  Gene {gene} not found in the database.")
                    notFoundGenes+=1

                if len(associations) > 400:
                    try:
                        count+=len(associations)
                        session.commit()
                        associations = []
                    except Exception as e:
                        session.rollback()
                        print_log_error(logger, f"Failed to commit GO associations batch: {e}")
                        exit(1)

                
            
        if associations:
            try:
                session.commit()
                logger.debug(f"✅ All {count} GO associations for species '{species_code}' committed successfully.")

                if notFoundGenes > 0:
                    logger.warning(f"⚠️  {notFoundGenes} sequences listed in the '{species_code}' GO file were not found in the 'sequence' table of your database.")
                
                if notFoundTerms > 0:
                    logger.warning(f"⚠️  {notFoundTerms}  GO terms listed in the '{species_code}' GO file were not found in the 'go' table of your database.")

            except Exception as e:
                session.rollback()
                print_log_error(logger, f"Failed to commit final GO associations: {e}")
                exit(1)

    except Exception as e:
        session.rollback()
        print_log_error(logger, f"Error while processing GO file '{filename}': {e}")
        exit(1)

    # Add extended GOs
    extendedAdded = 0
    extendedTermNotFound = 0
    extendedGeneNotFound = 0
    logger.debug(f"Adding extended GOs")

    for gene, terms in gene_go.items():
        if gene not in gene_hash:
            logger.warning(f"⚠️  Gene '{gene}' from extended GO step not found in database.")
            continue

        current_sequence = gene_hash[gene]
        new_terms = []
        current_terms = list(set(terms))  # remove duplicates

        for term in terms:
            if term in go_hash:
                extended_terms = go_hash[term].extended_go.split(";")
                for extended_term in extended_terms:
                    if extended_term not in current_terms and extended_term not in new_terms:
                        new_terms.append(extended_term)
            else:
                #logger.warning(f"⚠️  GO term '{term}' in extended GO step not found in database.")
                extendedTermNotFound += 1

        for new_term in new_terms:
            if new_term in go_hash:
                current_term = go_hash[new_term]
                association = {
                    "sequence_id": current_sequence.id,
                    "go_id": current_term.id,
                    "evidence": None,
                    "source": "Extended",
                    "predicted": 0
                }
                associations.append(association)
                try:
                    session.add(SequenceGOAssociation(**association))
                    extendedAdded += 1
                except Exception as e:
                    logger.error(f"Failed to add extended GO association for gene '{gene}' and term '{new_term}': {e}")
            else:
                #logger.warning(f"⚠️  Extended GO term '{new_term}' not found in database.")
                extendedGeneNotFound += 1

            if len(associations) >= 400:
                try:
                    session.commit()
                    associations.clear()
                except Exception as e:
                    session.rollback()
                    print_log_error(logger, f"Failed to commit extended GO batch: {e}")
                    exit(1)

            if extendedAdded % 50000 == 0:
                logger.debug(f"{extendedAdded} extended GOs processed and committed...")


    # Final commit for remaining extended GOs
    if associations:
        try:
            session.commit()
            logger.debug(f"✅ All {extendedAdded} extended GOs for species '{species_code}' committed successfully.")


            if extendedGeneNotFound > 0:
                logger.warning(f"⚠️  {extendedGeneNotFound} sequences were not found in the gene hash")

            
            if extendedTermNotFound > 0:
                logger.warning(f"⚠️  {extendedTermNotFound} terms were not found in the go hash")

        except Exception as e:
            session.rollback()
            print_log_error(logger, f"Failed to commit final extended GO associations: {e}")
            exit(1)



try:

    thisFileName = os.path.basename(__file__)
    #log variables
    log_dir = args.log_dir  #log dir path
    log_file_name = "go_annotation"   #log file names
    db_verbose = str2bool(args.db_verbose)
    py_verbose = str2bool(args.py_verbose)
    first_run = str2bool(args.first_run)
    
    logger = setup_logger(log_dir=log_dir, base_filename=log_file_name, DBverbose=db_verbose, PYverbose=py_verbose, overwrite_logs=first_run)


    go_tsv = args.go_file
    sps_code = args.species_code
    annotation_source = args.annot_source
    db_admin = args.db_admin
    db_name = args.db_name

    create_engine_string = "mysql+pymysql://"+db_admin+":"+db_password+"@localhost/"+db_name

    engine = create_engine(create_engine_string, echo=db_verbose)

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

    # Run function to add GO results for species
    add_go_from_tab(go_tsv, sps_code, engine, source=annotation_source)

    session.close()

except Exception as e:
    print_log_error(logger, e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
    exit(1)


logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} finished without errors! ✅ ---- ")