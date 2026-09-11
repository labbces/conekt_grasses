#!/usr/bin/env python3

import getpass
import argparse
import os
import operator

from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select

from log_functions import *

from utils.fasta import Fasta

parser = argparse.ArgumentParser(description='Add TEdistill sequences and per-species associations to the database')
parser.add_argument('--sequences', type=str, metavar='TEdistill fasta',
                    dest='sequences_file',
                    help='The fasta file with TEdistill consense sequences (e.g., distilledTE.flTE.iter56.fa). Header format: >NAME#TE_CLASS',
                    required=True)
parser.add_argument('--species_dir', type=str, metavar='Species data directory',
                    dest='species_dir',
                    help='Directory containing per-species subdirectories. Each species subdir may contain a {code}_te_copies.fa_transcript_to_gene_map.tsv file with TE-copy -> TEdistill associations.',
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

args = parser.parse_args()

db_password = args.db_password if args.db_password else getpass.getpass("Enter the database password: ")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_te_class(te_class_name):
    """Look up a TE class by its `name` column. Returns its id or None."""
    with engine.connect() as conn:
        stmt = select(TEClass.__table__.c).where(TEClass.name == te_class_name)
        te_class = conn.execute(stmt).first()
    return te_class.id if te_class else None


# ---------------------------------------------------------------------------
# Step 1 — Create the TEdistillMethod (global, once)
# ---------------------------------------------------------------------------

def add_tedistill_method(description, engine):
    """Create a new TEdistillMethod entry. Aborts if one with the same description exists."""
    logger.info("______________________________________________________________________")
    logger.info(f"➡️  Adding TEdistillMethod: {description}")

    with engine.connect() as conn:
        logger.debug(f"🔍 Checking if TEdistillMethod '{description}' already exists...")
        stmt = select([TEdistillMethod]).where(TEdistillMethod.__table__.c.method == description)
        existing = conn.execute(stmt).first()
        if existing:
            print_log_error(logger, f"TEdistill method '{description}' already exists in the database")
            exit(1)

    try:
        logger.debug(f"📝 Inserting new TEdistillMethod: {description}")
        session.add(TEdistillMethod(method=description))
        session.commit()
        logger.debug("✅ TEdistillMethod committed successfully.")
    except Exception as e:
        session.rollback()
        print_log_error(logger, e)
        exit(1)


# ---------------------------------------------------------------------------
# Step 2 — Insert all TEdistill consense sequences from the fasta (global, once)
# ---------------------------------------------------------------------------

def add_tedistill_sequences(sequences_file, method):
    """
    Read the TEdistill fasta and create one TEdistill row per sequence, plus its
    TEdistillTEClassAssociation. Each header is expected as `>NAME#TE_CLASS`.
    """
    logger.info("______________________________________________________________________")
    logger.info(f"➡️  Loading TEdistill sequences from: {sequences_file}")

    fasta_data = Fasta()
    fasta_data.readfile(sequences_file)
    total = len(fasta_data.sequences)
    logger.debug(f"✅ Parsed {total} sequences from FASTA.")

    count = 0
    try:
        for line, sequence in sorted(fasta_data.sequences.items(), key=operator.itemgetter(0)):
            # Expected format: NAME#TE_CLASS  (the '>' is already stripped by Fasta)
            parts = line.split('#')
            if len(parts) != 2:
                logger.warning(f"⚠️ Skipping malformed FASTA header: {line!r}")
                continue
            name, te_class_name = parts
            name = name.strip('>').strip()
            te_class_name = te_class_name.strip()

            te_class_id = get_te_class(te_class_name)
            if not te_class_id:
                print_log_error(logger, f"TE class '{te_class_name}' not found in database (header: {line!r})")
                session.rollback()
                exit(1)

            # Mangle the displayed name the same way the original script did:
            # `TE_00003625` (method.id=1) -> `TE_01_00003625`
            new_tedistill = TEdistill(
                name=name.replace('TE', 'TE_%02d' % method.id, 1),
                original_name=name,
                method_id=method.id,
                representative_sequence=sequence,
            )
            session.add(new_tedistill)
            session.flush()  # need the auto-generated id for the join row below

            session.add(TEdistillTEClassAssociation(
                tedistill_id=new_tedistill.id,
                te_class_id=te_class_id,
            ))

            count += 1
            if count % 400 == 0:
                try:
                    session.commit()
                    logger.debug(f"📦 Committed batch ({count}/{total} TEdistills)...")
                except Exception as e:
                    session.rollback()
                    print_log_error(logger, f"Failed to commit TEdistill batch at {count}: {e}")
                    exit(1)

        session.commit()
        logger.info(f"✅ All {count} TEdistill sequences committed successfully.")
    except Exception as e:
        session.rollback()
        print_log_error(logger, f"Error while adding TEdistill sequences: {e}")
        exit(1)


# ---------------------------------------------------------------------------
# Step 3 — For each species, read its mapping file and create associations
# ---------------------------------------------------------------------------

def add_associations_for_species(species_code, mapping_file, method):
    """
    Read a per-species `*_te_copies.fa_transcript_to_gene_map.tsv` file and create
    SequenceTEdistillAssociation rows linking each TE copy to its TEdistill.

    File format (TAB-separated, one association per line):
        TE_00005587_copy0001|Chr10A:27159-28679|-<TAB>TE_00005587
        ^----------- TE copy (col1) ----------^      ^- TEdistill (col2)

    The TE-copy name is normalized by splitting on '|' and taking the first piece,
    to match how add_species.py stores TE sequence names.
    """
    logger.info("______________________________________________________________________")
    logger.info(f"➡️  Adding TEdistill associations for species '{species_code}' from '{mapping_file}'")

    # --- Resolve species -----------------------------------------------------
    with engine.connect() as conn:
        stmt = select([Species.__table__]).where(Species.__table__.c.code == species_code)
        species = conn.execute(stmt).first()

    if not species:
        logger.warning(f"⚠️ Species '{species_code}' not found in database. Skipping.")
        return 0
    species_id = species.id
    logger.debug(f"✅ Species '{species_code}' found (ID: {species_id})")

    # --- Hash this species' TE sequences ------------------------------------
    with engine.connect() as conn:
        stmt = select([Sequence.__table__.c.name, Sequence.__table__.c.id]).where(
            (Sequence.__table__.c.species_id == species_id) &
            (Sequence.__table__.c.type == 'TE')
        )
        te_seqs = conn.execute(stmt).fetchall()

    if not te_seqs:
        logger.warning(f"⚠️ No TE sequences in DB for species '{species_code}'. Skipping associations.")
        return 0

    te_seq_hash = {s.name: s.id for s in te_seqs}
    logger.debug(f"✅ Loaded {len(te_seq_hash)} TE sequences for '{species_code}'.")

    # --- Hash TEdistills (by original_name, which is what the mapping uses) -
    with engine.connect() as conn:
        stmt = select([TEdistill.__table__.c.original_name, TEdistill.__table__.c.id]).where(
            TEdistill.__table__.c.method_id == method.id
        )
        tedistills = conn.execute(stmt).fetchall()

    if not tedistills:
        print_log_error(logger, f"No TEdistills loaded for method id {method.id}. Did step 2 run?")
        exit(1)

    tedistill_hash = {t.original_name: t.id for t in tedistills}
    logger.debug(f"✅ Loaded {len(tedistill_hash)} TEdistills.")

    # --- Stream through the mapping file ------------------------------------
    not_found_te = 0
    not_found_tedistill = 0
    malformed = 0
    added = 0
    batch_count = 0

    try:
        with open(mapping_file, 'r') as fin:
            for line_num, line in enumerate(fin, 1):
                line = line.rstrip('\n')
                if not line.strip():
                    continue
                parts = line.split('\t')
                if len(parts) < 2:
                    malformed += 1
                    if malformed <= 5:
                        logger.warning(f"⚠️ Malformed line {line_num} in '{mapping_file}': {line!r}")
                    continue

                te_copy_raw = parts[0].strip()
                tedistill_name = parts[1].strip()

                # Normalize TE copy name to match how add_species.py stored it
                te_copy_name = te_copy_raw.split('|')[0]

                te_copy_id = te_seq_hash.get(te_copy_name)
                if te_copy_id is None:
                    not_found_te += 1
                    continue

                tedistill_id = tedistill_hash.get(tedistill_name)
                if tedistill_id is None:
                    not_found_tedistill += 1
                    continue

                session.add(SequenceTEdistillAssociation(
                    sequence_id=te_copy_id,
                    tedistill_id=tedistill_id,
                ))
                added += 1
                batch_count += 1

                if batch_count >= 400:
                    try:
                        session.commit()
                        batch_count = 0
                    except Exception as e:
                        session.rollback()
                        print_log_error(logger, f"Failed to commit associations batch for '{species_code}': {e}")
                        exit(1)

                if added % 50000 == 0:
                    logger.debug(f"📦 {added} associations processed for '{species_code}'...")

        # Final flush
        session.commit()

        logger.info(f"✅ Added {added} TEdistill associations for '{species_code}'.")
        if not_found_te > 0:
            logger.warning(f"⚠️ {not_found_te} TE copies in '{species_code}' mapping were not found in the 'sequences' table.")
        if not_found_tedistill > 0:
            logger.warning(f"⚠️ {not_found_tedistill} TEdistill references in '{species_code}' mapping were not found in the 'tedistills' table.")
        if malformed > 0:
            logger.warning(f"⚠️ {malformed} malformed lines in '{species_code}' mapping were skipped.")
        return added

    except Exception as e:
        session.rollback()
        print_log_error(logger, f"Error processing mapping file '{mapping_file}': {e}")
        exit(1)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def add_tedistills_from_species_dir(sequences_file, species_dir, description, engine):
    """
    End-to-end: create the method, load all TEdistill sequences, then walk the
    species table and process whatever mapping files are present on disk.
    """
    try:
        # Step 1: method
        add_tedistill_method(description, engine)

        with engine.connect() as conn:
            stmt = select([TEdistillMethod.__table__]).where(TEdistillMethod.method == description)
            method = conn.execute(stmt).first()
        logger.debug(f"✅ Using TEdistillMethod ID {method.id}.")

        # Step 2: sequences
        add_tedistill_sequences(sequences_file, method)

        # Step 3: per-species associations
        with engine.connect() as conn:
            stmt = select([Species.__table__.c.code])
            species_codes = sorted(row.code for row in conn.execute(stmt).fetchall())

        logger.info("______________________________________________________________________")
        logger.info(f"📋 Found {len(species_codes)} species in DB: {species_codes}")

        processed = 0
        skipped_no_file = []
        for code in species_codes:
            mapping_file = os.path.join(
                species_dir, code, f"{code}_te_copies.fa_transcript_to_gene_map.tsv"
            )
            if os.path.exists(mapping_file):
                add_associations_for_species(code, mapping_file, method)
                processed += 1
            else:
                skipped_no_file.append(code)
                logger.info(f"ℹ️  No mapping file for '{code}' at '{mapping_file}'. Skipping.")

        logger.info("______________________________________________________________________")
        logger.info(f"📊 Summary: processed {processed}/{len(species_codes)} species.")
        if skipped_no_file:
            logger.info(f"   ↳ Skipped (no mapping file): {skipped_no_file}")

    except Exception as e:
        print_log_error(logger, f'Error while adding tedistills: {e}')
        raise


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

try:
    thisFileName = os.path.basename(__file__)
    log_dir = args.log_dir
    log_file_name = "tedistills"
    db_verbose = str2bool(args.db_verbose)
    py_verbose = str2bool(args.py_verbose)
    logger = setup_logger(log_dir=log_dir, base_filename=log_file_name,
                          DBverbose=db_verbose, PYverbose=py_verbose)

    create_engine_string = f"mysql+pymysql://{args.db_admin}:{db_password}@localhost/{args.db_name}"
    engine = create_engine(create_engine_string, echo=db_verbose)

    Base = automap_base()
    Base.prepare(engine, reflect=True)

    TEdistillMethod = Base.classes.tedistill_methods
    TEdistill = Base.classes.tedistills
    Species = Base.classes.species
    Sequence = Base.classes.sequences
    TEClass = Base.classes.te_classes
    SequenceTEdistillAssociation = Base.classes.sequence_tedistill
    TEdistillTEClassAssociation = Base.classes.tedistill_te_class

    Session = sessionmaker(bind=engine)
    session = Session()

    add_tedistills_from_species_dir(
        args.sequences_file,
        args.species_dir,
        args.description,
        engine,
    )

    session.close()

except Exception as e:
    print_log_error(logger, e)
    logger.info(f" ---- ❌ An error occurred while executing {thisFileName}. Please fix the issue and rerun the script. ❌ ---- ")
    exit(1)

logger.info(f" ---- ✅ SUCCESS: All operations from {thisFileName} finished without errors! ✅ ---- ")