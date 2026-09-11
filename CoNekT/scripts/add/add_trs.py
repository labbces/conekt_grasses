#!/usr/bin/env python3

# Uses CoNekT virtual environment (python3.8)

import getpass
import argparse
import os
import sys
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select


from log_functions import *   # logging utilities


parser = argparse.ArgumentParser(description='Add transcription factors and their associations to the database')
parser.add_argument('--tr_families', type=str, metavar='tr_families.txt',
                    dest='tr_families_file',
                    help='The TXT file with TR families and descriptions',
                    required=False)
parser.add_argument('--tr_associations', type=str, metavar='tr_associations.txt',
                    dest='tr_associations_file',
                    help='The TXT file with gene-to-TR associations',
                    required=False)
parser.add_argument('--species_code', type=str, metavar='Svi',
                    dest='species_code',
                    help='The CoNekT Grasses species code',
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
parser.add_argument('--logdir', type=str, metavar='Log directory',
                    dest='log_dir',
                    help='The directory containing temporary populate logs',
                    required=False)
parser.add_argument('--db_verbose', type=str, metavar='Database verbose',
                    dest='db_verbose',
                    help='Enable database verbose logging (true/false)',
                    required=False,
                    default="false")
parser.add_argument('--py_verbose', type=str, metavar='Python script verbose',
                    dest='py_verbose',
                    help='Enable python verbose logging (true/false)',
                    required=False,
                    default="true")
parser.add_argument('--first_run', type=str, metavar='Flag indicating first execution of the file',
                    dest='first_run',
                    help='Controls log file opening type',
                    required=False,
                    default="true")

args = parser.parse_args()
db_password = args.db_password if args.db_password else getpass.getpass("Enter the database password: ")


def add_tr_families(filename):
    """
    Populates transcription_regulator table with families and descriptions from a TXT file.
    """
    logger.info(f"📂 Adding TR families from {filename}")
    try:
        session.query(TranscriptionRegulator).delete()
        session.commit()
        logger.debug("✅ Cleared transcription_regulator table.")
    except Exception as e:
        session.rollback()
        print_log_error(logger, e)

    try:
        with open(filename, 'r') as fin:
            i = 0
            for line in fin:
                parts = line.strip().split(':',1)
                if len(parts) == 2:
                    family, type_domains = parts[0], parts[1]
                    parts2 = type_domains.strip().split(';')
                    type = parts2[0].strip()
                    tr = TranscriptionRegulator(family=family, type=type)
                    session.add(tr)
                    i += 1
                if i > 0 and i % 40 == 0:
                    session.commit()
        session.commit()
        logger.info(f"✅ Added {i} TR families.")
    except Exception as e:
        session.rollback()
        print_log_error(logger, e)


def add_tr_associations(filename, species_code):
    logger.info(f"📂 Adding TR associations from {filename} for species {species_code}")

    with engine.connect() as conn:
        stmt = select([Species]).where(Species.code == species_code)
        species = conn.execute(stmt).first()

    if not species:
        logger.warning(f"⚠️ Species ({species_code}) not found in the database.")
        exit(1)
    species_id = species.id

    # Load sequences
    with engine.connect() as conn:
        stmt = select([Sequence]).where((Sequence.species_id == species_id) & (Sequence.type == 'protein_coding'))
        all_sequences = conn.execute(stmt).fetchall()
        logger.info(f"✅ Found {len(all_sequences)} sequences for species {species_code}.")

    # Load TRs
    with engine.connect() as conn:
        stmt = select([TranscriptionRegulator])
        all_trs = conn.execute(stmt).fetchall()

    gene_hash = {s.name: s for s in all_sequences}
    tr_hash = {tr.family: tr for tr in all_trs}
    associations = []

    existing_tr_associations = set()
    existing_domain_associations = set()

    with engine.connect() as conn:
        stmt = select([SequenceTRAssociation.sequence_id, SequenceTRAssociation.tr_id])
        result = conn.execute(stmt)
        for row in result:
            existing_tr_associations.add((row.sequence_id, row.tr_id))

        stmt2 = select([SequenceTRDomainAssociation.sequence_id,
                        SequenceTRDomainAssociation.domain,
                        SequenceTRDomainAssociation.query_start,
                        SequenceTRDomainAssociation.query_end])
        result2 = conn.execute(stmt2)
        for row in result2:
            existing_domain_associations.add((row.sequence_id, row.domain, row.query_start, row.query_end))

    try:
        with open(filename, "r") as f:
            header = f.readline()  # skip header
            for line in f:
                parts = line.strip().split('\t')
                if len(parts) < 3:
                    logger.warning(f"Skipping malformed line: {line.strip()}")
                    continue

                gene = parts[0].rsplit('.', 1)[0] if '.p' in parts[0] else parts[0]
                family = parts[1]
                type = parts[2]

                domain = parts[3] if len(parts) > 3 else None
                query_start = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else None
                query_end = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else None

                if gene not in gene_hash:
                    logger.warning(f"Gene {gene} not found in the database.")
                    continue

                # Handle missing or orphan families
                if family not in tr_hash:
                    logger.info(f"Adding missing TR family as 'Orphans': {family}")
                    if "Orphans" not in tr_hash:
                        # Add Orphans TR type to the DB if needed
                        orphan_tr = TranscriptionRegulator(family="Orphans", type="Orphans")
                        session.add(orphan_tr)
                        session.flush()  # Get ID
                        tr_hash["Orphans"] = orphan_tr
                    current_tr = tr_hash["Orphans"]
                else:
                    current_tr = tr_hash[family]

                current_sequence = gene_hash[gene]
                key = (current_sequence.id, current_tr.id)

                if key not in existing_tr_associations:
                    logger.debug(f"➕ Adding TR association: {gene} -> {current_tr.family}")
                    association = SequenceTRAssociation(
                        sequence_id=current_sequence.id,
                        tr_id=current_tr.id
                    )
                    session.add(association)
                    existing_tr_associations.add(key)
                    associations.append(key)

                # Add domain association only if domain and coordinates are available
                if domain and query_start is not None and query_end is not None:
                    key2 = (current_sequence.id, domain, query_start, query_end)
                    if key2 not in existing_domain_associations:
                        logger.debug(f"➕ Adding domain association: {gene} -> {domain}")
                        domain_association = SequenceTRDomainAssociation(
                            sequence_id=current_sequence.id,
                            domain=domain,
                            query_start=query_start,
                            query_end=query_end
                        )
                        session.add(domain_association)
                        existing_domain_associations.add(key2)
                        associations.append(key2)
                else:
                    logger.debug(f"ℹ️ No domain info for gene {gene} — skipping domain association")

                if len(associations) > 400:
                    session.commit()
                    associations = []

        session.commit()
        logger.info("✅ TR associations added successfully.")
    except Exception as e:
        session.rollback()
        print_log_error(logger, e)


try:
    thisFileName = os.path.basename(__file__)
    first_run = str2bool(args.first_run)
    log_dir = args.log_dir
    log_file_name = "add_trs"
    db_verbose = str2bool(args.db_verbose)
    py_verbose = str2bool(args.py_verbose)
    logger = setup_logger(log_dir=log_dir, base_filename=log_file_name,
                          DBverbose=db_verbose, PYverbose=py_verbose, overwrite_logs=first_run)

    create_engine_string = f"mysql+pymysql://{args.db_admin}:{db_password}@localhost/{args.db_name}"
    engine = create_engine(create_engine_string, echo=db_verbose)

    Base = automap_base()
    Base.prepare(engine, reflect=True)

    Species = Base.classes.species
    Sequence = Base.classes.sequences
    TranscriptionRegulator = Base.classes.transcription_regulator
    SequenceTRAssociation = Base.classes.sequence_tr
    SequenceTRDomainAssociation = Base.classes.sequence_tr_domain

    Session = sessionmaker(bind=engine)
    session = Session()

    if args.tr_families_file:
        add_tr_families(args.tr_families_file)
    if args.tr_associations_file:
        add_tr_associations(args.tr_associations_file, args.species_code)

    session.close()

except Exception as e:
    print_log_error(logger, e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. ❌ ---- ")
    exit(1)

if args.species_code:
    logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} for species '{args.species_code}' finished successfully! ✅ ---- ")
else:
    logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} finished successfully! ✅ ---- ")
