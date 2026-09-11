#!/usr/bin/env python3

import getpass
import argparse
import os
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

from log_functions import *

parser = argparse.ArgumentParser(description='Add gene families to the database')
parser.add_argument('--orthogroups', type=str, metavar='Orthogroups.txt',
                    dest='orthogroups_file',
                    help='The Orthogroups.txt file from OrthoFinder',
                    required=True)
parser.add_argument('--description', type=str, metavar='Description',
                    dest='description',
                    help='Description of the method as it should appear in CoNekT',
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
                    help='Enable database verbose logging (true/false)',
                    required=False,
                    default="false")
parser.add_argument('--py_verbose', type=str, metavar='Python script verbose',
                    dest='py_verbose',
                    help='Enable python verbose logging (true/false)',
                    required=False,
                    default="true")

args = parser.parse_args()

db_password = args.db_password if args.db_password else getpass.getpass("Enter the database password: ")


def add_family_method(description):
    """
    Add a new GeneFamilyMethod to the database.
    """
    logger.info(f"Adding GeneFamilyMethod: {description}")

    with engine.connect() as conn:
        logger.debug(f"🔍 Checking if GeneFamilyMethod '{description}' already exists...")
        stmt = select([GeneFamilyMethod]).where(GeneFamilyMethod.__table__.c.method == description)
        result = conn.execute(stmt).fetchone()

        if result:
            logger.warning(f"⚠️ Gene family method '{description}' already exists in the database")
            exit(1)

    try:
        logger.debug(f"📝 Inserting new GeneFamilyMethod: {description}")
        session.add(GeneFamilyMethod(method=description))
        session.commit()
        logger.debug("✅ GeneFamilyMethod committed successfully.")
    except Exception as e:
        session.rollback()
        print_log_error(logger, e)
        exit(1)


def add_families(families, family_members):
    """
    Adds gene families and their member sequences to the database.
    """
    logger.debug(f"🧩 Adding {len(families)} gene families...")

    for i, f in enumerate(families):
        session.add(f)
        if i > 0 and i % 400 == 0:
            logger.debug(f"📦 Committing batch of {i} families...")
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                print_log_error(logger, e)
                exit(1)

    try:
        session.commit()
        logger.debug("✅ All families committed successfully.")
    except Exception as e:
        session.rollback()
        print_log_error(logger, e)
        exit(1)

    for i, f in enumerate(families):
        logger.debug(f"🔗 Linking sequences to family {f.name} (ID pending DB)...")
        with engine.connect() as conn:
            stmt = select([Sequence]).where(Sequence.__table__.c.id.in_(list(family_members[f.name])))
            family_sequences = conn.execute(stmt).fetchall()
            logger.debug(f"   ↳ Found {len(family_sequences)} sequences for family {f.name}")

        for member in family_sequences:
            association = SequenceFamilyAssociation(sequence_id=member.id, gene_family_id=f.id)
            session.add(association)

            if i > 0 and i % 400 == 0:
                logger.debug(f"📦 Committing batch of {i} associations...")
                try:
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print_log_error(logger, e)
                    exit(1)

        del family_sequences

    try:
        session.commit()
        logger.debug("✅ All sequence-family associations committed successfully.")
    except Exception as e:
        session.rollback()
        print_log_error(logger, e)
        exit(1)


def add_families_from_orthofinder(filename, description):
    """
    Add gene families from OrthoFinder output file.
    """
    try:
        logger.info(f"📂 Processing OrthoFinder file: {filename}")
        add_family_method(description)

        with engine.connect() as conn:
            stmt = select([GeneFamilyMethod]).where(GeneFamilyMethod.__table__.c.method == description)
            method = conn.execute(stmt).fetchone()
            logger.debug(f"✅ Using GeneFamilyMethod ID {method.id} for families.")

        gene_hash = {}
        logger.debug("🔍 Loading protein coding sequences from DB...")
        with engine.connect() as conn:
            stmt = select([Sequence.__table__.c.name, Sequence.__table__.c.id]).where(Sequence.__table__.c.type == 'protein_coding')
            all_sequences = conn.execute(stmt).fetchall()
            logger.debug(f"✅ Loaded {len(all_sequences)} protein coding sequences.")

        for sequence in all_sequences:
            gene_hash[sequence.name.lower()] = sequence
        del all_sequences

        families = set()
        family_members = defaultdict(set)

        logger.debug(f"📖 Reading orthogroups from {filename}...")
        with open(filename, "r") as f_in:
            line_count = 0
            for line in f_in:
                line_count += 1
                if len(families) >= 2000:
                    logger.debug(f"📦 Reached 2000 families, committing batch...")
                    add_families(families, family_members)
                    families = set()
                    family_members = defaultdict(set)

                orthofinder_id, *parts = line.strip().split()
                orthofinder_id = orthofinder_id.rstrip(':')

                new_family = GeneFamily(name=orthofinder_id.replace('OG', f'OG_%02d_' % method.id))
                new_family.original_name = orthofinder_id
                new_family.method_id = method.id
                families.add(new_family)

                for p in parts:
                    if p.lower() in gene_hash:
                        family_members[new_family.name].add(gene_hash[p.lower()][1])
                        del gene_hash[p.lower()]

                if line_count % 5000 == 0:
                    logger.info(f"📊 Processed {line_count} lines from OrthoFinder file...")

        logger.debug(f"📦 Final batch commit with {len(families)} families...")
        add_families(families, family_members)
        logger.info(f"✅ Finished processing {line_count} lines from OrthoFinder file.")

    except Exception as e:
        print_log_error(logger, f'❌ Error while adding families from orthofinder: {e}')




try:
    thisFileName = os.path.basename(__file__)
    log_dir = args.log_dir
    log_file_name = "gene_families"
    db_verbose = str2bool(args.db_verbose)
    py_verbose = str2bool(args.py_verbose)
    logger = setup_logger(log_dir=log_dir, base_filename=log_file_name, DBverbose=db_verbose, PYverbose=py_verbose)

    create_engine_string = f"mysql+pymysql://{args.db_admin}:{db_password}@localhost/{args.db_name}"
    engine = create_engine(create_engine_string, echo=db_verbose)

    Base = automap_base()
    Base.prepare(engine, reflect=True)

    GeneFamilyMethod = Base.classes.gene_family_methods
    GeneFamily = Base.classes.gene_families
    Sequence = Base.classes.sequences
    SequenceFamilyAssociation = Base.classes.sequence_family

    Session = sessionmaker(bind=engine)
    session = Session()

    add_families_from_orthofinder(args.orthogroups_file, args.description)

    session.close()

except Exception as e:
    print_log_error(logger, e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
    exit(1)

logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} finished without errors! ✅ ---- ")
